"""
optimizer.py
============
The agent's decision engine.

Given a campaign's recent performance and a set of goals, it proposes a list of
concrete `Action`s (adjust budget, change bid, pause, etc.) — each with a plain
-English rationale and a confidence score. The agent (agent.py) decides whether
to apply them automatically or hold them for human approval.

This is deliberately a transparent rules engine rather than an opaque model:
in ad ops you need to be able to explain *why* a budget moved. The same Action
objects could equally be produced by an LLM reasoning step — the downstream
apply/guardrail logic doesn't care where they came from.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from platforms import Campaign, Performance


Kind = Literal["increase_budget", "decrease_budget", "pause", "set_target_cpa", "no_change"]


def _usd(v: float) -> str:
    return f"${v:,.2f}"


@dataclass
class Action:
    campaign_id: str
    campaign_name: str
    kind: Kind
    rationale: str
    confidence: float                 # 0..1
    current: float | str | None = None
    proposed: float | str | None = None

    def describe(self) -> str:
        if self.kind == "no_change":
            return f"[hold ] {self.campaign_name}: {self.rationale}"
        arrow = f"{self.current} → {self.proposed}"
        return (f"[{self.kind:>15}] {self.campaign_name}: {arrow}  "
                f"({self.confidence:.0%}) — {self.rationale}")


@dataclass
class Goals:
    """Campaign-level targets the optimizer steers toward."""
    target_cpa: float = 30.0        # max acceptable cost per acquisition (USD)
    target_roas: float = 3.0        # min acceptable revenue / cost
    min_conversions: float = 5.0    # below this, metrics are too noisy to trust
    max_budget_step: float = 0.25   # cap a single budget move at ±25%
    max_daily_budget: float = 500.0
    min_daily_budget: float = 10.0


def _clamp_budget(current: float, proposed: float, goals: Goals) -> float:
    lo = current * (1 - goals.max_budget_step)
    hi = current * (1 + goals.max_budget_step)
    proposed = max(lo, min(hi, proposed))
    proposed = max(goals.min_daily_budget, min(goals.max_daily_budget, proposed))
    return round(proposed, 2)


def evaluate(campaign: Campaign, perf: Performance, goals: Goals) -> Action:
    """Return the single best action for one campaign.

    Rule precedence (first match wins):
      0. Awareness objective                       -> hold (different KPI)
      1. High spend + zero conversions             -> pause (needs approval)
         ⚠ This rule OVERRIDES low-signal hold — burning money with no results
         should not be left running even if signal is weak.
      2. Catastrophic CPA + poor ROAS (w/ signal)  -> pause (needs approval)
      3. Strong ROAS + low CPA (w/ signal)         -> scale winner
      4. CPA materially over target (w/ signal)    -> trim overspender
      5. CPA drifting over target (w/ signal)      -> recenter bid / target CPA
         Demonstrated by "Search — Nonbrand" campaign in mock data.
      6. Low signal / too new                      -> hold
      7. Otherwise                                 -> hold steady
    """
    name = campaign.name
    cpa = perf.cpa
    roas = perf.roas
    enough = perf.conversions >= goals.min_conversions
    # "High spend" = has burned at least ~2 target-CPAs' worth (and a $50 floor).
    high_spend = perf.cost >= max(50.0, 2 * goals.target_cpa)

    # 0) Awareness campaigns aren't judged on CPA/ROAS — different KPI entirely.
    if campaign.objective == "awareness":
        return Action(campaign.id, name, "no_change", confidence=0.6,
                      rationale="Awareness objective — steering by reach/CPM, "
                                "outside this conversion optimizer's scope.")

    # 1) Money-loser: real spend, zero conversions → pause. This takes
    #    precedence over the low-signal hold (zero conv is *also* low signal,
    #    but high spend with nothing to show should not be left running).
    if perf.conversions == 0 and high_spend:
        return Action(campaign.id, name, "pause", confidence=0.85,
                      current="enabled", proposed="paused",
                      rationale=f"Spent {_usd(perf.cost)} over {perf.window_days}d with "
                                f"zero conversions. Treat as a money-loser — pause and "
                                f"rework before it spends more.")

    # 2) Bleeding money: CPA far over target AND poor ROAS → pause.
    if enough and cpa > goals.target_cpa * 1.75 and roas < goals.target_roas * 0.5:
        return Action(campaign.id, name, "pause", confidence=0.85,
                      current="enabled", proposed="paused",
                      rationale=f"CPA {_usd(cpa)} is {cpa/goals.target_cpa:.1f}× target "
                                f"and ROAS {roas:.1f} is far below {goals.target_roas:.1f}. "
                                f"Pause and rework before it spends more.")

    # 3) Winner: efficient AND profitable → scale up.
    if enough and cpa < goals.target_cpa * 0.85 and roas > goals.target_roas:
        proposed = _clamp_budget(campaign.daily_budget,
                                 campaign.daily_budget * 1.25, goals)
        if proposed > campaign.daily_budget:
            return Action(campaign.id, name, "increase_budget", confidence=0.8,
                          current=campaign.daily_budget, proposed=proposed,
                          rationale=f"CPA {_usd(cpa)} beats target and ROAS {roas:.1f} "
                                    f"is healthy. Scale to capture more volume.")

    # 4) Overspending the target: CPA materially over → cut budget.
    if enough and cpa > goals.target_cpa * 1.20:
        proposed = _clamp_budget(campaign.daily_budget,
                                 campaign.daily_budget * 0.80, goals)
        return Action(campaign.id, name, "decrease_budget", confidence=0.7,
                      current=campaign.daily_budget, proposed=proposed,
                      rationale=f"CPA {_usd(cpa)} is above the {_usd(goals.target_cpa)} "
                                f"target. Trim spend to protect efficiency.")

    # 5) Drifting tCPA: CPA has drifted significantly from the campaign's
    #    target_cpa setting, but not badly enough to trigger trim/pause.
    #    Recenter the bid target instead of cutting budget.
    if (enough and campaign.bid_strategy == "target_cpa" and campaign.target_cpa):
        drift = abs(cpa - campaign.target_cpa) / campaign.target_cpa
        # Only act if drift is material (>20%) and CPA isn't catastrophically high
        # (catastrophic CPA would have triggered pause in rule 2)
        if drift > 0.20 and cpa < goals.target_cpa * 1.75:
            new_tcpa = round((campaign.target_cpa + cpa) / 2, 2)
            return Action(campaign.id, name, "set_target_cpa", confidence=0.6,
                          current=campaign.target_cpa, proposed=new_tcpa,
                          rationale=f"Realised CPA {_usd(cpa)} has drifted "
                                    f"{drift:.0%} from the tCPA {_usd(campaign.target_cpa)} "
                                    f"setting. Recentre the target rather than cut spend.")

    # 6) Not enough signal yet → don't act on noise.
    if not enough:
        return Action(campaign.id, name, "no_change", confidence=0.5,
                      rationale=f"Only {perf.conversions:.1f} conv in "
                                f"{perf.window_days}d (< {goals.min_conversions:.0f}); "
                                f"too little signal to adjust.")

    # 7) Everything in band.
    return Action(campaign.id, name, "no_change", confidence=0.7,
                  rationale=f"CPA {_usd(cpa)} and ROAS {roas:.1f} are within the target "
                            f"band. Holding steady.")

"""
agent.py
========
The orchestration loop — the "agent brain".

Responsibilities:
  1. PERCEIVE  — pull campaigns and recent performance from the platform layer.
  2. DECIDE    — ask the optimizer for an action per campaign.
  3. GUARD     — apply safety guardrails (auto-apply vs. needs-approval).
  4. ACT       — apply approved changes back through the platform layer.
  5. REPORT    — emit a structured run report.

The loop is platform-agnostic: it only talks to the `AdPlatform` protocol, so
pointing it at a live MCP server is a one-line swap in `run.py`.

Autonomy levels
---------------
  "dry_run"  : decide + report, never write.            (safest)
  "assist"   : auto-apply only low-risk moves; queue the rest for a human.
  "auto"     : apply everything that clears the guardrails.

Guardrails (always on)
  - Pausing a campaign is NEVER auto-applied — always needs human approval.
  - A single budget change may not exceed ±25% (enforced in the optimizer too).
  - Total daily budget across the account may not increase more than `max_account_increase`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from platforms import MockAdPlatform, Campaign, Performance
from optimizer import Action, Goals, evaluate
from creative import generate_copy, CreativeSet

Autonomy = Literal["dry_run", "assist", "auto"]


@dataclass
class Decision:
    action: Action
    perf: Performance
    applied: bool
    needs_approval: bool
    note: str = ""


@dataclass
class RunReport:
    autonomy: Autonomy
    decisions: list[Decision] = field(default_factory=list)
    new_campaign: Campaign | None = None
    creatives: list[CreativeSet] = field(default_factory=list)

    @property
    def applied(self) -> list[Decision]:
        return [d for d in self.decisions if d.applied]

    @property
    def pending(self) -> list[Decision]:
        return [d for d in self.decisions if d.needs_approval and not d.applied]


class AdAgent:
    def __init__(self, platform: MockAdPlatform, goals: Goals | None = None,
                 autonomy: Autonomy = "assist", max_account_increase: float = 0.20) -> None:
        self.platform = platform
        self.goals = goals or Goals()
        self.autonomy = autonomy
        self.max_account_increase = max_account_increase

    # ---- guardrails ------------------------------------------------------ #
    def _is_low_risk(self, action: Action) -> bool:
        # Spend-reducing and small tuning moves are low risk. Pausing and
        # budget increases are higher risk.
        if action.kind in ("decrease_budget", "set_target_cpa"):
            return True
        if action.kind == "increase_budget" and action.confidence >= 0.75:
            return True
        return False

    def _approve(self, action: Action) -> tuple[bool, bool, str]:
        """Return (apply_now, needs_approval, note) for the current autonomy."""
        if action.kind == "no_change":
            return False, False, "no change"
        if action.kind == "pause":
            # Hard rule: a human always confirms a pause.
            return False, True, "pause requires human approval"
        if self.autonomy == "dry_run":
            return False, True, "dry-run: not applied"
        if self.autonomy == "auto":
            return True, False, "auto-applied"
        # assist
        if self._is_low_risk(action):
            return True, False, "auto-applied (low risk)"
        return False, True, "queued for approval"

    # ---- main loop ------------------------------------------------------- #
    def optimize(self, window_days: int = 14) -> RunReport:
        report = RunReport(autonomy=self.autonomy)
        account_budget_before = sum(c.daily_budget for c in self.platform.get_campaigns())
        proposed_increase = 0.0

        for c in self.platform.get_campaigns():
            perf = self.platform.get_performance(c.id, window_days=window_days)
            action = evaluate(c, perf, self.goals)
            apply_now, needs_approval, note = self._approve(action)

            # Account-level budget ceiling guardrail.
            if apply_now and action.kind == "increase_budget":
                delta = float(action.proposed) - float(action.current)  # type: ignore[arg-type]
                if (proposed_increase + delta) / account_budget_before > self.max_account_increase:
                    apply_now, needs_approval = False, True
                    note = "account budget ceiling hit — queued for approval"
                else:
                    proposed_increase += delta

            if apply_now:
                self._apply(action)

            report.decisions.append(
                Decision(action=action, perf=perf, applied=apply_now,
                         needs_approval=needs_approval, note=note))
        return report

    def _apply(self, action: Action) -> None:
        if action.kind in ("increase_budget", "decrease_budget"):
            self.platform.update_budget(action.campaign_id, float(action.proposed))  # type: ignore[arg-type]
        elif action.kind == "set_target_cpa":
            self.platform.update_bid(action.campaign_id, target_cpa=float(action.proposed))  # type: ignore[arg-type]
        elif action.kind == "pause":
            self.platform.set_status(action.campaign_id, "paused")

    # ---- campaign launch ------------------------------------------------- #
    def launch_from_brief(self, *, product: str, audience: str, value_props: list[str],
                          platform: str, objective: str, daily_budget: float,
                          target_cpa: float | None = None) -> tuple[Campaign, CreativeSet]:
        """Draft a brand-new campaign + creative from a one-line brief.
        New campaigns are created PAUSED so a human reviews before spend."""
        bid_strategy = "target_cpa" if target_cpa else "max_conversions"
        campaign = self.platform.create_campaign(
            name=f"{product} — {audience}", platform=platform, objective=objective,
            daily_budget=daily_budget, bid_strategy=bid_strategy, target_cpa=target_cpa)
        creative = generate_copy(product=product, audience=audience,
                                 value_props=value_props, platform=platform)
        return campaign, creative

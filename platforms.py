"""
platforms.py
============
Cross-platform ad data layer.

This module is the *seam* between the agent and the outside world. Today it
serves realistic MOCK data so the whole agent runs offline with zero API keys.
To go live, replace `MockAdPlatform` with a real MCP client — every method maps
1:1 onto a tool exposed by the MCP servers catalogued in
https://github.com/jshorwitz/awesome-agentic-advertising :

    get_campaigns()    -> Synter `list_campaigns` / Google Ads GAQL query
    get_performance()  -> Synter `get_performance` / Meta insights
    update_budget()    -> Synter `update_campaign_budget` / Pipeboard
    update_bid()       -> platform bid-strategy tool
    create_campaign()  -> Synter `create_campaign`

Keeping every platform call behind this interface means the agent brain
(agent.py), the optimizer, and the creative generator never change when you
swap mock data for a live MCP connection.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from datetime import date, timedelta
from typing import Any


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass
class Campaign:
    id: str
    name: str
    platform: str          # google | meta | linkedin
    objective: str         # conversions | traffic | awareness | leads
    status: str            # enabled | paused
    daily_budget: float    # USD
    bid_strategy: str       # max_conversions | target_cpa | manual_cpc
    target_cpa: float | None  # USD, None when not a tCPA strategy


@dataclass
class DailyStat:
    day: str
    impressions: int
    clicks: int
    cost: float
    conversions: float
    revenue: float


@dataclass
class Performance:
    campaign_id: str
    window_days: int
    impressions: int
    clicks: int
    cost: float
    conversions: float
    revenue: float
    daily: list[DailyStat] = field(default_factory=list)

    # ---- derived metrics ------------------------------------------------- #
    @property
    def ctr(self) -> float:
        return self.clicks / self.impressions if self.impressions else 0.0

    @property
    def cpc(self) -> float:
        return self.cost / self.clicks if self.clicks else 0.0

    @property
    def cvr(self) -> float:
        return self.conversions / self.clicks if self.clicks else 0.0

    @property
    def cpa(self) -> float:
        return self.cost / self.conversions if self.conversions else float("inf")

    @property
    def roas(self) -> float:
        return self.revenue / self.cost if self.cost else 0.0


# --------------------------------------------------------------------------- #
# Mock platform
# --------------------------------------------------------------------------- #
# Each seed defines the "true" underlying economics of a campaign. The mock
# generator adds day-to-day noise on top so the optimizer has something real
# to react to.
_SEED_CAMPAIGNS: list[dict[str, Any]] = [
    # platform, name, objective, status, budget, bid, tcpa, true_cvr, true_cpc, aov
    dict(platform="google",  name="Search — Brand",            objective="conversions", status="enabled",
         daily_budget=40,  bid_strategy="target_cpa",      target_cpa=18, _cvr=0.085, _cpc=0.95, _aov=120),
    dict(platform="google",  name="Search — Competitor",      objective="conversions", status="enabled",
         daily_budget=60,  bid_strategy="max_conversions", target_cpa=None, _cvr=0.022, _cpc=2.40, _aov=120),
    dict(platform="google",  name="Performance Max — Catalog", objective="conversions", status="enabled",
         daily_budget=120, bid_strategy="target_cpa",      target_cpa=32, _cvr=0.031, _cpc=0.70, _aov=140),
    dict(platform="meta",    name="Prospecting — Lookalike 1%", objective="conversions", status="enabled",
         daily_budget=150, bid_strategy="max_conversions", target_cpa=None, _cvr=0.018, _cpc=0.85, _aov=95),
    dict(platform="meta",    name="Retargeting — 30d Site",    objective="conversions", status="enabled",
         daily_budget=50,  bid_strategy="max_conversions", target_cpa=None, _cvr=0.061, _cpc=0.65, _aov=110),
    dict(platform="meta",    name="Awareness — Reels Video",   objective="awareness",   status="enabled",
         daily_budget=80,  bid_strategy="max_conversions", target_cpa=None, _cvr=0.004, _cpc=0.30, _aov=90),
    dict(platform="linkedin", name="Leads — VP Marketing ABM", objective="leads",       status="enabled",
         daily_budget=90,  bid_strategy="manual_cpc",      target_cpa=None, _cvr=0.012, _cpc=8.50, _aov=900),
    # Nonbrand search whose realised CPA has drifted above its tCPA setting, but
    # not badly enough to trim/pause → exercises the "recenter target CPA" path.
    dict(platform="google",  name="Search — Nonbrand",         objective="conversions", status="enabled",
         daily_budget=70,  bid_strategy="target_cpa",      target_cpa=22, _cvr=0.050, _cpc=1.50, _aov=115),
    # High-spend campaign returning zero conversions → exercises the money-loser
    # pause rule that overrides the low-signal hold.
    dict(platform="meta",    name="Prospecting — Broad (new creative)", objective="conversions", status="enabled",
         daily_budget=70,  bid_strategy="max_conversions", target_cpa=None, _cvr=0.0,   _cpc=0.90, _aov=100),
]


class MockAdPlatform:
    """In-memory stand-in for a live cross-platform ad MCP server."""

    def __init__(self, seed: int = 7) -> None:
        self._rng = random.Random(seed)
        self._campaigns: dict[str, Campaign] = {}
        self._econ: dict[str, dict[str, float]] = {}   # hidden "true" economics
        # Per-run performance cache: a campaign's stats are generated once and
        # reused, so the terminal audit and the HTML report (and any repeated
        # query) always show the *same* snapshot for a run. Fixed seed makes the
        # whole run reproducible across invocations too.
        # ⚠ CRITICAL: This cache ensures deterministic reporting — terminal output
        # and HTML report always display identical numbers within a single run.
        self._perf_cache: dict[tuple[str, int], Performance] = {}
        self._next_id = 1000
        for spec in _SEED_CAMPAIGNS:
            self._install(spec)

    # ---- internal -------------------------------------------------------- #
    def _install(self, spec: dict[str, Any]) -> str:
        cid = f"c{self._next_id}"
        self._next_id += 1
        self._campaigns[cid] = Campaign(
            id=cid,
            name=spec["name"],
            platform=spec["platform"],
            objective=spec["objective"],
            status=spec["status"],
            daily_budget=float(spec["daily_budget"]),
            bid_strategy=spec["bid_strategy"],
            target_cpa=spec["target_cpa"],
        )
        self._econ[cid] = dict(cvr=spec["_cvr"], cpc=spec["_cpc"], aov=spec["_aov"])
        return cid

    # ---- read tools ------------------------------------------------------ #
    def get_campaigns(self, platform: str | None = None) -> list[Campaign]:
        out = list(self._campaigns.values())
        if platform:
            out = [c for c in out if c.platform == platform]
        return out

    def get_performance(self, campaign_id: str, window_days: int = 14) -> Performance:
        cache_key = (campaign_id, window_days)
        if cache_key in self._perf_cache:
            return self._perf_cache[cache_key]
        c = self._campaigns[campaign_id]
        econ = self._econ[campaign_id]
        daily: list[DailyStat] = []
        tot = dict(impr=0, clk=0, cost=0.0, conv=0.0, rev=0.0)
        for i in range(window_days):
            day = (date.today() - timedelta(days=window_days - i)).isoformat()
            # Budget caps spend; noise simulates auction variance.
            spend = c.daily_budget * self._rng.uniform(0.80, 1.0)
            if c.status == "paused":
                spend = 0.0
            cpc = max(0.05, econ["cpc"] * self._rng.uniform(0.85, 1.20))
            clicks = int(spend / cpc)
            ctr = self._rng.uniform(0.02, 0.09)
            impressions = int(clicks / ctr) if ctr else 0
            cvr = max(0.0, econ["cvr"] * self._rng.uniform(0.70, 1.30))
            conversions = round(clicks * cvr, 2)
            revenue = round(conversions * econ["aov"] * self._rng.uniform(0.9, 1.1), 2)
            cost = round(clicks * cpc, 2)
            daily.append(DailyStat(day, impressions, clicks, cost, conversions, revenue))
            tot["impr"] += impressions
            tot["clk"] += clicks
            tot["cost"] += cost
            tot["conv"] += conversions
            tot["rev"] += revenue
        perf = Performance(
            campaign_id=campaign_id,
            window_days=window_days,
            impressions=tot["impr"],
            clicks=tot["clk"],
            cost=round(tot["cost"], 2),
            conversions=round(tot["conv"], 2),
            revenue=round(tot["rev"], 2),
            daily=daily,
        )
        self._perf_cache[cache_key] = perf
        return perf

    # ---- write tools ----------------------------------------------------- #
    def update_budget(self, campaign_id: str, daily_budget: float) -> Campaign:
        self._campaigns[campaign_id].daily_budget = round(float(daily_budget), 2)
        return self._campaigns[campaign_id]

    def update_bid(self, campaign_id: str, *, bid_strategy: str | None = None,
                   target_cpa: float | None = None) -> Campaign:
        c = self._campaigns[campaign_id]
        if bid_strategy is not None:
            c.bid_strategy = bid_strategy
        if target_cpa is not None:
            c.target_cpa = round(float(target_cpa), 2)
        return c

    def set_status(self, campaign_id: str, status: str) -> Campaign:
        self._campaigns[campaign_id].status = status
        return self._campaigns[campaign_id]

    def create_campaign(self, *, name: str, platform: str, objective: str,
                        daily_budget: float, bid_strategy: str = "max_conversions",
                        target_cpa: float | None = None) -> Campaign:
        # New campaigns start paused so a human reviews before they spend.
        spec = dict(platform=platform, name=name, objective=objective, status="paused",
                    daily_budget=daily_budget, bid_strategy=bid_strategy, target_cpa=target_cpa,
                    _cvr=0.02, _cpc=1.0, _aov=110)
        cid = self._install(spec)
        return self._campaigns[cid]


def campaign_to_dict(c: Campaign) -> dict[str, Any]:
    return asdict(c)

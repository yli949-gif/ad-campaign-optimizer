#!/usr/bin/env python3
"""
run.py
======
End-to-end demo of the ad agent. Runs fully offline on mock data.

    python run.py                  # default: 'assist' autonomy
    python run.py --autonomy auto
    python run.py --autonomy dry_run
    python run.py --window 7

What it shows:
  1. The agent audits every campaign and proposes optimization actions.
  2. Low-risk moves are auto-applied; risky ones (pauses, big increases) are
     queued for human approval.
  3. The agent drafts a brand-new campaign + ad copy from a one-line brief.

Swap mock → live: replace `MockAdPlatform()` with your MCP client (see README).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from platforms import MockAdPlatform
from optimizer import Goals
from agent import AdAgent, RunReport
from creative import generate_copy
from report import build_html_report


C = dict(  # tiny ANSI palette
    b="\033[1m", dim="\033[2m", g="\033[32m", y="\033[33m", r="\033[31m",
    c="\033[36m", x="\033[0m",
)


def _money(v: float) -> str:
    return f"${v:,.2f}"


def print_audit(report: RunReport, platforms_by_id: dict[str, str]) -> None:
    print(f"\n{C['b']}━━ CAMPAIGN AUDIT ({report.autonomy} mode) "
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C['x']}")
    header = f"{'Campaign':28} {'Plat':9} {'Spend':>9} {'Conv':>6} {'CPA':>8} {'ROAS':>6}"
    print(f"{C['dim']}{header}{C['x']}")
    for d in sorted(report.decisions, key=lambda x: x.perf.cost, reverse=True):
        p = d.perf
        cpa = "—" if p.conversions == 0 else _money(p.cpa)
        name = d.action.campaign_name[:27]
        plat = platforms_by_id.get(d.action.campaign_id, "")
        print(f"{name:28} {plat:9} {_money(p.cost):>9} {p.conversions:>6.1f} "
              f"{cpa:>8} {p.roas:>6.1f}")


def print_actions(report: RunReport) -> None:
    print(f"\n{C['b']}━━ AGENT DECISIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C['x']}")
    applied = report.applied
    pending = report.pending
    holds = [d for d in report.decisions if d.action.kind == "no_change"]

    if applied:
        print(f"\n{C['g']}✓ Applied automatically ({len(applied)}){C['x']}")
        for d in applied:
            print(f"  {C['g']}•{C['x']} {d.action.describe()}")
    if pending:
        print(f"\n{C['y']}⏸ Needs your approval ({len(pending)}){C['x']}")
        for d in pending:
            print(f"  {C['y']}•{C['x']} {d.action.describe()}")
            print(f"      {C['dim']}{d.note}{C['x']}")
    if holds:
        print(f"\n{C['dim']}— Holding steady ({len(holds)}){C['x']}")
        for d in holds:
            print(f"  {C['dim']}• {d.action.campaign_name}: {d.action.rationale}{C['x']}")


def print_launch(agent: AdAgent):
    print(f"\n{C['b']}━━ NEW CAMPAIGN FROM BRIEF ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C['x']}")
    brief = dict(product="AuroraSleep Mattress", audience="back-pain sufferers",
                 value_props=["Doctor-designed support", "100-night trial"],
                 platform="meta", objective="conversions", daily_budget=75, target_cpa=28)
    print(f"{C['dim']}Brief: launch '{brief['product']}' to {brief['audience']} "
          f"on {brief['platform']} at {_money(brief['daily_budget'])}/day, "
          f"tCPA {_money(brief['target_cpa'])}{C['x']}")
    campaign, creative = agent.launch_from_brief(**brief)

    # Draft copy for all three platforms for the report (terminal shows meta).
    creatives = [
        generate_copy(product=brief["product"], audience=brief["audience"],
                      value_props=brief["value_props"], platform=plat)
        for plat in ("google", "meta", "linkedin")
    ]

    print(f"\n  {C['c']}Created{C['x']} {campaign.name}  "
          f"[{campaign.platform} · {campaign.objective} · {campaign.status.upper()}]")
    print(f"  Budget {_money(campaign.daily_budget)}/day · {campaign.bid_strategy} "
          f"· tCPA {_money(campaign.target_cpa or 0)}")
    print(f"  {C['dim']}(ad copy drafted for Google, Meta & LinkedIn — see report; "
          f"Meta shown below){C['x']}")
    for label, value in creative.named_fields():
        print(f"  {C['b']}{label}{C['x']}: {value}  {C['dim']}({len(value)} chars){C['x']}")
    print(f"  {C['b']}Image prompt{C['x']}")
    print(f"    {C['dim']}{creative.image_prompt}{C['x']}")
    issues = creative.validate()
    status = f"{C['g']}passes platform limits{C['x']}" if not issues else f"{C['r']}{issues}{C['x']}"
    print(f"  Validation: {status}")
    print(f"\n  {C['y']}⏸ Campaign is PAUSED — review and enable when ready.{C['x']}")
    return campaign, creatives


def main() -> None:
    ap = argparse.ArgumentParser(description="Agentic advertising demo")
    ap.add_argument("--autonomy", choices=["dry_run", "assist", "auto"], default="assist")
    ap.add_argument("--window", type=int, default=14, help="performance lookback in days")
    args = ap.parse_args()

    platform = MockAdPlatform()
    goals = Goals(target_cpa=30, target_roas=3.0)
    agent = AdAgent(platform, goals=goals, autonomy=args.autonomy)

    print(f"{C['b']}{C['c']}AGENTIC ADVERTISING — demo run{C['x']}")
    print(f"{C['dim']}Goals: CPA ≤ {_money(goals.target_cpa)} · "
          f"ROAS ≥ {goals.target_roas:.1f} · lookback {args.window}d{C['x']}")

    platforms_by_id = {c.id: c.platform for c in platform.get_campaigns()}
    budgets_before = {c.id: c.daily_budget for c in platform.get_campaigns()}
    report = agent.optimize(window_days=args.window)
    print_audit(report, platforms_by_id)
    print_actions(report)
    new_campaign, new_creatives = print_launch(agent)

    report_path = build_html_report(
        report=report, goals=goals, platforms_by_id=platforms_by_id,
        budgets_before=budgets_before, new_campaign=new_campaign,
        new_creatives=new_creatives,
        out_path=Path(__file__).parent / "reports" / "latest_report.html")

    print(f"\n{C['b']}━━ SUMMARY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C['x']}")
    print(f"  {len(report.applied)} change(s) applied · "
          f"{len(report.pending)} awaiting approval · 1 campaign drafted")
    print(f"  {C['dim']}Re-run with --autonomy auto to apply approvals, or "
          f"--autonomy dry_run to preview only.{C['x']}")
    # Exact, greppable line (relative path) per spec:
    print(f"\n{C['b']}{C['c']}Report generated: reports/latest_report.html{C['x']}\n")


if __name__ == "__main__":
    main()

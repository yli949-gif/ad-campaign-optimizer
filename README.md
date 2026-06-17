# Agentic Advertising Agent

An autonomous advertising agent that audits campaigns, optimizes budgets and bids, and drafts new campaigns + ad creative from a one-line brief. Built from the patterns and tools in [awesome-agentic-advertising](https://github.com/jshorwitz/awesome-agentic-advertising).

It runs **fully offline on realistic mock data** — no API keys, no installs — so you can see exactly how the agent reasons before connecting it to a live ad account. Every external call sits behind one swappable interface, so going live is a small, contained change.

## Quick start

```bash
cd ad-agent
python3 run.py                    # 'assist' mode: auto-apply low-risk, queue the rest
python3 run.py --autonomy assist  # same as default
python3 run.py --autonomy auto    # apply everything that clears the guardrails
python3 run.py --autonomy dry_run # preview only, never writes
python3 run.py --window 7         # use a 7-day performance lookback
```

Requires Python 3.10+. No third-party packages for the demo. Each run prints a
terminal summary **and** writes a business-style report to
`reports/latest_report.html` — open it in any browser. Mock data is generated
from a fixed seed, so the terminal and the report always show the **same
numbers**, and runs are reproducible.

## What it does each run

1. **Perceives** — pulls every campaign and its recent performance (spend, conversions, CPA, ROAS).
2. **Decides** — the optimizer proposes one action per campaign, each with a plain-English rationale and a confidence score: scale winners, trim overspenders, pause money-losers, recentre drifting target-CPA bids, or hold steady.
3. **Guards** — safety rails decide what is safe to auto-apply versus what a human must approve.
4. **Acts** — applies approved changes back through the platform layer.
5. **Drafts** — builds a brand-new campaign and platform-shaped ad copy from a one-line brief, created **paused** for review: Google RSA (headlines + descriptions), Meta (primary text, headline, CTA), and LinkedIn (intro text, headline, description), plus an image prompt for a creative model.
6. **Reports** — writes `reports/latest_report.html` for a business stakeholder.

The optimizer applies one rule per campaign, in strict precedence: high-spend with zero conversions → pause (this overrides the low-signal hold); strong ROAS + low CPA → scale; CPA materially over target → trim; CPA drifting over target → recentre the target CPA; too little signal → hold; otherwise hold steady.

### The business report

`reports/latest_report.html` is plain HTML/CSS (no framework, no dependencies) and includes: run metadata (autonomy mode, lookback window), an account summary (spend, revenue, conversions, average CPA, average ROAS), an **estimated** efficiency opportunity (spend identified above the CPA target and the daily budget the agent **proposes** to reallocate — carefully worded because the data is simulated), the campaign audit, recommended actions grouped by **auto-applied / needs approval / blocked by guardrail / preview-only / hold**, a dedicated **human approval queue**, the guardrails summary, the new campaign draft, a "how this connects to live MCP later" section, and an explicit limitations section.

## Safety guardrails

The agent is designed to never quietly burn budget:

- **Pausing a campaign always needs human approval** — even in fully autonomous mode.
- **Single budget moves are capped at ±25%** so nothing swings wildly in one step.
- **Account-level budget increases are capped** (default +20% total) to prevent runaway spend.
- **New campaigns launch paused** so a person enables them deliberately.
- **Low-signal campaigns are left alone** — the agent won't act on a handful of noisy conversions.

Autonomy is a dial: `dry_run` (preview), `assist` (auto-apply only low-risk moves), `auto` (apply everything that clears the rails).

## How it's structured

| File | Role |
|------|------|
| `platforms.py` | The **seam** to the outside world. Today: mock cross-platform data. Swap for a live MCP client to go live. |
| `optimizer.py` | The decision engine — transparent rules that turn performance into actions. |
| `creative.py` | Ad-copy and image-prompt generation with per-platform named fields and character limits. |
| `agent.py` | The orchestration loop + guardrails + autonomy levels. |
| `report.py` | Renders the business-style `reports/latest_report.html`. |
| `run.py` | Runnable end-to-end demo: terminal output + report. |
| `reports/latest_report.html` | Generated each run (overwritten). |

The agent brain only ever talks to the platform interface, so none of the optimization or creative logic changes when you connect a real account.

## Going live — connecting real ad platforms

The mock layer mirrors the tools exposed by the MCP servers in the awesome list. To run against real accounts, replace `MockAdPlatform` in `run.py` with an MCP client and map these methods onto real tools:

| Agent method | Live MCP tool (examples from the awesome list) |
|--------------|------------------------------------------------|
| `get_campaigns()` | Synter Media `list_campaigns` · Google Ads MCP GAQL query |
| `get_performance()` | Synter `get_performance` · Meta/Pipeboard insights |
| `update_budget()` | Synter `update_campaign_budget` · Pipeboard |
| `update_bid()` | platform bid-strategy tool |
| `create_campaign()` | Synter `create_campaign` |
| creative image prompt | Imagen 4 · Flux · Runway · Veo (text-to-image/video) |

When hardening for production:
- **Wire conversion tracking** (Google Conversion API, Meta CAPI, etc.) so the performance the agent reads reflects real revenue.
- **Keep `dry_run` as the default** for the first few weeks and review the agent's proposals before granting `assist`/`auto`.

## Limitations

This is an **offline MVP on mock campaign data**. It is not connected to any live ad account, uses no API keys, and reflects no real spend or performance. Figures such as "estimated wasted spend identified" and "potential budget reallocation" are illustrative indications, not promised savings. Decisions come from simple, transparent rules rather than a learned model. It is **designed for future MCP integration** but is **not production-ready** and should not be treated as a system that can safely modify real ad accounts today.

## Recommended next steps

1. **Wire one real read-only MCP server** (e.g. the official Google Ads MCP) behind the existing `platforms.py` interface and run in `dry_run` to compare the agent's proposals against a live account — no writes, low risk.
2. **Add an LLM reasoning step** that proposes or sanity-checks the optimizer's `Action` objects; the guardrail and apply logic stay unchanged regardless of where actions originate.

## Note on the source repo

`awesome-agentic-advertising` is a *curated list*, not a codebase — it catalogues MCP servers, protocols (MCP, AdCP, A2A), creative models, and agent frameworks. This project turns that catalogue into a working agent skeleton you can actually run and then point at the real tools it references.

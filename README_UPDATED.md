# Campaign Optimizer - Agentic Advertising MVP

**Status**: ✅ All features implemented and verified  
**Last Updated**: 2026-06-16

---

## Quick Start

```bash
# Run the optimizer (assist mode - default)
python run.py

# Preview only (no changes applied)
python run.py --autonomy dry_run

# Fully autonomous (apply all approved changes)
python run.py --autonomy auto

# Custom lookback window
python run.py --window 7

# Run comprehensive feature tests
python test_all_features.py
```

**View Results**: Open `reports/latest_report.html` in your browser

---

## What This Does

An AI-powered campaign optimization agent that:

1. **Audits** all active campaigns against performance goals
2. **Decides** what action to take for each campaign (scale, trim, pause, hold, recenter)
3. **Applies** low-risk changes automatically
4. **Queues** high-impact changes for human approval
5. **Drafts** new campaigns with platform-specific ad copy
6. **Reports** everything in a business-friendly HTML report

**Everything runs offline on mock data** - no API keys, no live accounts.

---

## Key Features

### ✅ Intelligent Decision Engine
- **Rule-based optimizer** with explicit precedence (see `optimizer.py`)
- **7 decision rules**: awareness hold → money-loser pause → catastrophic pause → scale winner → trim overspender → recenter drifting CPA → low-signal hold → steady state
- **Safety guardrails**: pause always needs approval, budget changes capped at ±25%, account ceiling on auto-increases

### ✅ Multi-Platform Support
- **Google Ads**: Search, Performance Max, Display
- **Meta**: Facebook, Instagram (Prospecting, Retargeting, Awareness)
- **LinkedIn**: Lead generation, ABM
- **Creative copy** auto-generated for each platform with correct field names

### ✅ Autonomy Modes
- `dry_run`: Preview only, no changes applied
- `assist`: Auto-apply low-risk moves, queue high-impact for approval (default)
- `auto`: Apply everything that clears guardrails

### ✅ Business-Ready Reporting
- **HTML report** with account summary, efficiency opportunities, action recommendations
- **Hold / No Action group**: Always visible, shows what agent chose NOT to change
- **Human Approval Queue**: Dedicated table of actions awaiting sign-off
- **Creative drafts**: All three platforms (Google, Meta, LinkedIn) with character limits validated

### ✅ Deterministic & Testable
- **Fixed seed** for reproducible runs
- **Performance cache** ensures terminal and HTML show identical numbers
- **Test suite** validates all 6 core features (run `python test_all_features.py`)

---

## Example Output

```
CAMPAIGN AUDIT (assist mode)
Campaign                     Plat          Spend   Conv      CPA   ROAS
Prospecting — Lookalike 1%   meta      $1,875.06   42.0   $44.70    2.2
Search — Nonbrand            google      $880.12   27.1   $32.44    3.6
Prospecting — Broad (new cr  meta        $863.26    0.0        —    0.0

AGENT DECISIONS

✓ Applied automatically (5)
  • [increase_budget] Search — Brand: 40.0 → 50.0
  • [set_target_cpa] Search — Nonbrand: 22 → 27.22 (CPA drifted 47%)
  • [decrease_budget] Prospecting — Lookalike 1%: 150.0 → 120.0

⏸ Needs your approval (2)
  • [pause] Prospecting — Broad: Spent $863.26 with zero conversions
  • [pause] Search — Competitor: CPA 3.5× target, ROAS far below goal

— Holding steady (2)
  • Awareness — Reels Video: Different KPI (reach/CPM)
  • Leads — VP Marketing ABM: Too little signal (< 5 conversions)

Report generated: reports/latest_report.html
```

---

## Architecture

```
run.py              # Entry point, orchestrates full workflow
├── platforms.py    # Mock ad platform (swap for live MCP client here)
├── optimizer.py    # Decision engine with 7 rules
├── agent.py        # Orchestration loop (perceive → decide → guard → act)
├── creative.py     # Platform-specific ad copy generation
└── report.py       # HTML report generator (business-friendly)
```

**The Seam**: All platform calls go through `platforms.py`. To go live, replace `MockAdPlatform()` with a real MCP client - everything else stays the same.

---

## Rule Precedence (Optimizer)

1. **Awareness objective** → hold (different KPI)
2. **High spend + zero conversions** → pause ⚠️ *overrides low-signal hold*
3. **Catastrophic CPA + poor ROAS** → pause
4. **Strong ROAS + low CPA** → scale winner
5. **CPA materially over target** → trim overspender
6. **CPA drifting from tCPA setting** → recenter bid/target
7. **Low signal / too new** → hold
8. **Otherwise** → hold steady

See `optimizer.py` for full logic with thresholds.

---

## Guardrails (Always On)

- **Pause requires approval**: Human always confirms, even in auto mode
- **Budget moves capped**: Single change ≤ ±25%
- **Account budget ceiling**: Total auto-increases ≤ +20%
- **New campaigns start paused**: Draft waits for human review
- **Low-signal campaigns left alone**: Won't act on < 5 conversions

---

## Creative Field Names

### Meta
- Primary text (125 char)
- Headline (40 char)
- Call to action

### LinkedIn
- Intro text (150 char)
- Headline (70 char)
- Description (100 char)

### Google RSA
- Headlines 1-5 (30 char each)
- Descriptions 1-3 (90 char each)

All validated against platform limits. See `creative.py`.

---

## Test Suite

Run `python test_all_features.py` to validate:

1. ✅ Rule precedence (high spend + zero conv > low signal)
2. ✅ Recenter-CPA path (demonstrated by "Search — Nonbrand")
3. ✅ Deterministic performance (cache consistency)
4. ✅ Creative field names (platform-specific)
5. ✅ Hold / No Action group visibility
6. ✅ Human Approval Queue functionality

Expected: `6/6 tests passed`

---

## Going Live (Future MCP Integration)

To connect to real ad platforms:

1. Replace `MockAdPlatform()` in `run.py` with your MCP client
2. Map methods:
   - `get_campaigns()` → Synter `list_campaigns` / Google Ads GAQL
   - `get_performance()` → Synter `get_performance` / Meta Insights
   - `update_budget()` → Synter `update_campaign_budget`
   - `update_bid()` → Platform bid-strategy tools
   - `create_campaign()` → Synter `create_campaign`

No other files need changes. See `platforms.py` header for MCP tool mapping.

---

## Limitations (MVP Scope)

- ✅ Offline mock data only (no live API connections)
- ✅ Not production-ready (demonstration MVP)
- ✅ Transparent rules, not learned model
- ✅ No guaranteed savings (illustrative estimates)
- ✅ Manual MCP integration required

These are **by design** for a demo-able MVP.

---

## Documentation

- `CHANGES_SUMMARY.md` - What was changed and why
- `VERIFICATION_REPORT.md` - Detailed feature verification
- `test_all_features.py` - Comprehensive test suite

---

## Questions?

- Rule precedence: See `optimizer.py` comments
- HTML report sections: See `report.py`
- Mock data: See `platforms.py` _SEED_CAMPAIGNS
- Creative generation: See `creative.py`

Built with ❤️ for agentic advertising workflows.

"""
report.py
=========
Business-style HTML report generator.

Turns a `RunReport` (from agent.py) into a clean, self-contained HTML page a
marketing or business stakeholder can read — no terminal, no jargon dumps.
Standard library only; the CSS/HTML is inlined so the file opens anywhere with
no network or build step.

IMPORTANT — language discipline:
This MVP runs on SIMULATED data. Every figure in the report is therefore an
*illustrative estimate*, and the wording throughout says so. Nothing here should
be read as a real account result.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from optimizer import Goals
from agent import RunReport, Decision
from creative import CreativeSet


# --------------------------------------------------------------------------- #
# Categorisation of decisions for the "grouped by status" section
# --------------------------------------------------------------------------- #
def _category(d: Decision) -> str:
    note = d.note.lower()
    if d.applied:
        return "auto_applied"
    if "ceiling" in note or "guardrail" in note:
        return "blocked"
    if "dry-run" in note:
        return "dry_run"
    if d.needs_approval:
        return "needs_approval"
    return "hold"


CATEGORY_META = {
    "auto_applied":   ("Auto-applied", "These low-risk changes were applied automatically.", "ok"),
    "needs_approval": ("Needs your approval", "Higher-impact moves held for a human to confirm.", "warn"),
    "blocked":        ("Blocked by guardrail", "Proposed, but a safety limit stopped auto-apply.", "block"),
    "dry_run":        ("Preview only (dry-run)", "Nothing was written — this was a preview run.", "muted"),
    # Hold group: campaigns with acceptable performance, insufficient signal, or outside optimizer scope (awareness campaigns).
    # Always visible — never hidden — so you can see what the agent chose NOT to change and why.
    "hold":           ("Hold / No action", "Intentionally left unchanged — see the reason on each.", "muted"),
}

# Why each kind of action needs a human (for the approval-queue section).
_APPROVAL_REASON = {
    "pause": "Pausing a campaign always requires human approval, even in auto mode.",
}
_APPROVAL_DEFAULT = "Higher-impact change held for human confirmation."


# --------------------------------------------------------------------------- #
# Money / metric helpers
# --------------------------------------------------------------------------- #
def _money(v: float) -> str:
    return f"${v:,.2f}"


def _money0(v: float) -> str:
    return f"${v:,.0f}"


@dataclass
class Summary:
    spend: float
    revenue: float
    conversions: float
    avg_cpa: float
    avg_roas: float
    reallocatable_daily: float
    overspend_vs_target: float


def _summarise(report: RunReport, goals: Goals,
               budgets_before: dict[str, float]) -> Summary:
    spend = sum(d.perf.cost for d in report.decisions)
    revenue = sum(d.perf.revenue for d in report.decisions)
    conv = sum(d.perf.conversions for d in report.decisions)
    avg_cpa = spend / conv if conv else 0.0
    avg_roas = revenue / spend if spend else 0.0

    # Reallocatable daily budget = budget freed by trims + paused campaigns.
    reallocatable = 0.0
    overspend = 0.0
    for d in report.decisions:
        a = d.action
        if a.kind == "decrease_budget" and isinstance(a.proposed, (int, float)):
            reallocatable += float(a.current) - float(a.proposed)  # type: ignore[arg-type]
        elif a.kind == "pause":
            reallocatable += budgets_before.get(a.campaign_id, 0.0)
        # Spend above what the CPA target implies, on conversion campaigns.
        if d.perf.conversions > 0 and d.perf.cpa > goals.target_cpa:
            overspend += d.perf.cost - d.perf.conversions * goals.target_cpa

    return Summary(spend, revenue, conv, avg_cpa, avg_roas,
                   round(reallocatable, 2), round(max(0.0, overspend), 2))


# --------------------------------------------------------------------------- #
# HTML building blocks
# --------------------------------------------------------------------------- #
_CSS = """
:root{
  --bg:#f5f6f8; --card:#ffffff; --ink:#1d2433; --muted:#6b7280; --line:#e6e8ec;
  --brand:#3b5bdb; --ok:#15803d; --okbg:#e7f6ec; --warn:#b45309; --warnbg:#fdf3e3;
  --block:#9333ea; --blockbg:#f5ecfd; --bad:#b91c1c; --good:#15803d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.wrap{max-width:920px;margin:0 auto;padding:32px 20px 64px;}
.head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;
  border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:8px;}
h1{font-size:24px;margin:0;letter-spacing:-.2px;}
h2{font-size:17px;margin:36px 0 12px;letter-spacing:-.1px;}
.sub{color:var(--muted);font-size:13px;margin-top:4px;}
.banner{background:#fff8e1;border:1px solid #f3e2a8;color:#7a5b00;
  border-radius:10px;padding:10px 14px;font-size:13px;margin:18px 0 4px;}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-top:6px;}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;}
.card .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.4px;}
.card .val{font-size:22px;font-weight:650;margin-top:6px;letter-spacing:-.3px;}
.card .val.good{color:var(--good)} .card .val.bad{color:var(--bad)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;
  padding:16px 18px;margin-top:12px;}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.kpi{font-size:28px;font-weight:700;letter-spacing:-.4px;}
.kpi.warn{color:var(--warn)}
table{width:100%;border-collapse:collapse;margin-top:6px;font-size:14px;}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);}
th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.3px;}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;}
.pill.google{background:#e8f0fe;color:#1a56db} .pill.meta{background:#e7ecff;color:#3b39d6}
.pill.linkedin{background:#e3f0f7;color:#0a66c2}
.group{border-radius:12px;border:1px solid var(--line);overflow:hidden;margin-top:14px;}
.group>.gh{padding:11px 16px;font-weight:650;display:flex;align-items:center;gap:10px;}
.gh.ok{background:var(--okbg);color:var(--ok)} .gh.warn{background:var(--warnbg);color:var(--warn)}
.gh.block{background:var(--blockbg);color:var(--block)} .gh.muted{background:#eef0f3;color:var(--muted)}
.gh .count{margin-left:auto;font-weight:600;font-size:13px;opacity:.8}
.gh .hint{font-weight:400;font-size:12px;color:var(--muted)}
.act{padding:12px 16px;border-top:1px solid var(--line);}
.act:first-of-type{border-top:none}
.act .top{display:flex;justify-content:space-between;gap:12px;align-items:baseline;}
.act .name{font-weight:600}
.act .move{font-variant-numeric:tabular-nums;color:var(--ink);font-size:13px;
  background:#f1f3f6;border-radius:6px;padding:1px 8px;}
.act .why{color:var(--muted);font-size:13px;margin-top:4px;}
.conf{font-size:12px;color:var(--muted);white-space:nowrap}
.bar{display:inline-block;width:46px;height:6px;border-radius:4px;background:#e6e8ec;
  vertical-align:middle;margin-left:6px;overflow:hidden}
.bar>span{display:block;height:100%;background:var(--brand)}
.rails{list-style:none;padding:0;margin:6px 0 0;}
.rails li{padding:8px 0;border-bottom:1px solid var(--line);font-size:14px;}
.rails li:last-child{border-bottom:none}
.rails b{color:var(--ink)}
.creative{margin-top:12px}
.creative .ch{display:flex;align-items:center;gap:10px;margin-bottom:6px;font-weight:600}
.chips{display:flex;flex-direction:column;gap:5px}
.chips .h{background:#f1f3f6;border-radius:6px;padding:6px 10px;font-size:13px;}
.cf{display:flex;gap:10px;align-items:baseline}
.cflabel{min-width:104px;color:var(--muted);font-size:12px;text-transform:uppercase;
  letter-spacing:.3px;flex:0 0 104px;padding-top:6px}
.cf .h{flex:1}
.whyrow td{border-bottom:1px solid var(--line);padding-top:0;padding-bottom:10px}
.whyrow .why{color:var(--muted);font-size:13px}
.mcp{counter-reset:step}
.mcp .row{display:flex;gap:12px;padding:9px 0;border-bottom:1px solid var(--line)}
.mcp .row:last-child{border-bottom:none}
.mcp .k{font-weight:600;min-width:190px}
.mcp .v{color:var(--muted);font-size:14px}
.foot{color:var(--muted);font-size:12px;margin-top:34px;border-top:1px solid var(--line);padding-top:14px}
code{background:#eef0f3;border-radius:5px;padding:1px 5px;font-size:13px}
"""


def _esc(s) -> str:
    return html.escape(str(s))


def _confidence_bar(conf: float) -> str:
    pct = int(round(conf * 100))
    return f'<span class="conf">{pct}%<span class="bar"><span style="width:{pct}%"></span></span></span>'


def _audit_rows(report: RunReport, platforms_by_id: dict[str, str],
                goals: Goals) -> str:
    rows = []
    for d in sorted(report.decisions, key=lambda x: x.perf.cost, reverse=True):
        p = d.perf
        plat = platforms_by_id.get(d.action.campaign_id, "")
        cpa_txt = "—" if p.conversions == 0 else _money(p.cpa)
        cpa_cls = "bad" if (p.conversions and p.cpa > goals.target_cpa) else "good"
        roas_cls = "good" if p.roas >= goals.target_roas else "bad"
        rows.append(
            f"<tr><td>{_esc(d.action.campaign_name)}</td>"
            f"<td><span class='pill {plat}'>{_esc(plat)}</span></td>"
            f"<td class='num'>{_money(p.cost)}</td>"
            f"<td class='num'>{p.conversions:.1f}</td>"
            f"<td class='num' style='color:var(--{cpa_cls})'>{cpa_txt}</td>"
            f"<td class='num' style='color:var(--{roas_cls})'>{p.roas:.1f}×</td></tr>")
    return "\n".join(rows)


def _action_groups(report: RunReport) -> str:
    buckets: dict[str, list[Decision]] = {k: [] for k in CATEGORY_META}
    for d in report.decisions:
        cat = _category(d)            # no_change decisions fall into "hold"
        if cat in buckets:
            buckets[cat].append(d)

    out = []
    for cat, (title, hint, cls) in CATEGORY_META.items():
        items = buckets[cat]
        if not items:
            continue
        rows = []
        for d in items:
            a = d.action
            move = ""
            if a.current is not None and a.proposed is not None:
                cur = _money(a.current) if isinstance(a.current, (int, float)) else _esc(a.current)
                prop = _money(a.proposed) if isinstance(a.proposed, (int, float)) else _esc(a.proposed)
                move = f"<span class='move'>{cur} → {prop}</span>"
            rows.append(
                f"<div class='act'><div class='top'>"
                f"<span class='name'>{_esc(a.campaign_name)}</span>"
                f"<span>{move} {_confidence_bar(a.confidence)}</span></div>"
                f"<div class='why'>{_esc(a.rationale)}</div></div>")
        out.append(
            f"<div class='group'><div class='gh {cls}'>{title}"
            f"<span class='hint'>{hint}</span>"
            f"<span class='count'>{len(items)}</span></div>{''.join(rows)}</div>")
    return "\n".join(out) or "<p class='sub'>No actions this run.</p>"


def _approval_queue(report: RunReport, platforms_by_id: dict[str, str]) -> str:
    """Dedicated table of every action awaiting human sign-off."""
    pending = [d for d in report.decisions if d.needs_approval and not d.applied]
    if not pending:
        return ("<div class='panel'><div class='sub'>Nothing is waiting on you — "
                "no actions required human approval this run.</div></div>")
    rows = []
    for d in pending:
        a = d.action
        plat = platforms_by_id.get(a.campaign_id, "")
        rec = a.kind.replace("_", " ")
        if a.current is not None and a.proposed is not None:
            cur = _money(a.current) if isinstance(a.current, (int, float)) else _esc(a.current)
            prop = _money(a.proposed) if isinstance(a.proposed, (int, float)) else _esc(a.proposed)
            rec = f"{rec} <span class='move'>{cur} → {prop}</span>"
        why = _APPROVAL_REASON.get(a.kind)
        if not why:
            why = d.note if d.note and "approval" in d.note.lower() else _APPROVAL_DEFAULT
        rows.append(
            f"<tr><td>{_esc(a.campaign_name)}</td>"
            f"<td><span class='pill {plat}'>{_esc(plat)}</span></td>"
            f"<td>{rec}</td>"
            f"<td class='num'>{a.confidence:.0%}</td>"
            f"<td class='why'>{_esc(why)}</td></tr>"
            f"<tr class='whyrow'><td colspan='5' class='why'>↳ {_esc(a.rationale)}</td></tr>")
    return (f"<div class='panel'><table>"
            f"<thead><tr><th>Campaign</th><th>Platform</th><th>Recommendation</th>"
            f"<th class='num'>Conf.</th><th>Why approval is required</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def _creative_block(cs: CreativeSet) -> str:
    plat = cs.platform
    rows = []
    for label, value in cs.named_fields():
        if not value:
            continue
        rows.append(f"<div class='cf'><span class='cflabel'>{_esc(label)}</span>"
                    f"<span class='h'>{_esc(value)}</span></div>")
    ok = not cs.validate()
    badge = ("<span style='color:var(--good);font-size:12px'>✓ within limits</span>"
             if ok else "<span style='color:var(--bad);font-size:12px'>⚠ over limit</span>")
    return (f"<div class='creative'><div class='ch'>"
            f"<span class='pill {plat}'>{_esc(plat)}</span> {badge}</div>"
            f"<div class='chips'>{''.join(rows)}</div></div>")


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #
def build_html_report(*, report: RunReport, goals: Goals,
                      platforms_by_id: dict[str, str],
                      budgets_before: dict[str, float],
                      new_campaign, new_creatives: list[CreativeSet],
                      out_path: str | Path) -> Path:
    s = _summarise(report, goals, budgets_before)
    now = datetime.now().strftime("%b %d, %Y · %H:%M")

    roas_cls = "good" if s.avg_roas >= goals.target_roas else "bad"
    cpa_cls = "good" if s.avg_cpa <= goals.target_cpa else "bad"

    cards = f"""
    <div class="cards">
      <div class="card"><div class="label">Total spend</div><div class="val">{_money0(s.spend)}</div></div>
      <div class="card"><div class="label">Revenue</div><div class="val">{_money0(s.revenue)}</div></div>
      <div class="card"><div class="label">Conversions</div><div class="val">{s.conversions:.0f}</div></div>
      <div class="card"><div class="label">Avg CPA</div><div class="val {cpa_cls}">{_money(s.avg_cpa)}</div></div>
      <div class="card"><div class="label">Avg ROAS</div><div class="val {roas_cls}">{s.avg_roas:.1f}×</div></div>
    </div>"""

    window = report.decisions[0].perf.window_days if report.decisions else 0
    audit = _audit_rows(report, platforms_by_id, goals)
    groups = _action_groups(report)
    approval_queue = _approval_queue(report, platforms_by_id)
    creatives_html = "".join(_creative_block(c) for c in new_creatives)

    nc_name = _esc(getattr(new_campaign, "name", "—"))
    nc_budget = _money(getattr(new_campaign, "daily_budget", 0))
    nc_tcpa = getattr(new_campaign, "target_cpa", None)
    nc_tcpa_txt = _money(nc_tcpa) if nc_tcpa else "n/a"

    n_applied = len(report.applied)
    n_pending = len(report.pending)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agentic Advertising — Run Report</title>
<style>{_CSS}</style></head>
<body><div class="wrap">

  <div class="head">
    <div>
      <h1>Agentic Advertising — Run Report</h1>
      <div class="sub">Autonomy mode: <b>{_esc(report.autonomy)}</b> &nbsp;·&nbsp;
        Lookback: <b>{window} days</b> &nbsp;·&nbsp; Generated {now}</div>
    </div>
    <div class="sub">Goals: CPA ≤ {_money0(goals.target_cpa)} · ROAS ≥ {goals.target_roas:.1f}×</div>
  </div>

  <div class="banner">⚠ <b>Illustrative MVP.</b> All figures below are generated from
  <b>simulated data</b> for demonstration. They are estimates that show how the agent
  reasons — not results from a real ad account.</div>

  <h2>Account summary</h2>
  {cards}

  <h2>Efficiency opportunity <span class="sub">(estimated, illustrative)</span></h2>
  <div class="panel two">
    <div>
      <div class="sub">Spend above CPA target on under-performing campaigns</div>
      <div class="kpi warn">~{_money0(s.overspend_vs_target)}</div>
      <div class="sub">Estimated portion of spend that exceeded the {_money0(goals.target_cpa)}
      CPA goal over this window. A rough indication of where efficiency could improve —
      not a guaranteed saving.</div>
    </div>
    <div>
      <div class="sub">Daily budget the agent proposes to reallocate</div>
      <div class="kpi">~{_money0(s.reallocatable_daily)}<span class="sub" style="font-size:14px">/day</span></div>
      <div class="sub">Freed by trimming over-target campaigns and flagging the worst
      performer to pause. Intended to move toward better-performing campaigns.</div>
    </div>
  </div>

  <h2>Campaign audit</h2>
  <div class="panel">
  <table>
    <thead><tr><th>Campaign</th><th>Platform</th><th class="num">Spend</th>
    <th class="num">Conv.</th><th class="num">CPA</th><th class="num">ROAS</th></tr></thead>
    <tbody>{audit}</tbody>
  </table>
  </div>

  <h2>Recommended actions <span class="sub">({n_applied} applied · {n_pending} awaiting approval)</span></h2>
  {groups}

  <h2>Safety guardrails in force</h2>
  <div class="panel"><ul class="rails">
    <li><b>Pausing always needs human approval</b> — even in fully autonomous mode, the agent never pauses a campaign on its own.</li>
    <li><b>Single budget moves capped at ±25%</b> — no campaign's budget can swing more than a quarter in one run.</li>
    <li><b>Account budget ceiling</b> — total automatic budget increases are capped (≈+20%) to prevent runaway spend; anything beyond is held for approval.</li>
    <li><b>New campaigns launch paused</b> — drafted creative and settings wait for a person to enable them.</li>
    <li><b>Low-signal campaigns left alone</b> — the agent won't act on too few conversions to read reliably.</li>
  </ul></div>

  <h2>Human approval queue <span class="sub">— actions waiting on a person</span></h2>
  {approval_queue}

  <h2>New campaign draft <span class="sub">— created paused for review</span></h2>
  <div class="panel">
    <div><b>{nc_name}</b> &nbsp;<span class="pill meta">meta</span></div>
    <div class="sub">Budget {nc_budget}/day · target CPA {nc_tcpa_txt} ·
      status <b style="color:var(--warn)">PAUSED</b></div>
    <div class="sub" style="margin-top:8px">Ad copy drafted for all three platforms,
      each shaped to its own character limits:</div>
    {creatives_html}
  </div>

  <h2>Designed for future MCP integration <span class="sub">— how this connects to live ad platforms later</span></h2>
  <div class="panel mcp">
    <div class="row"><div class="k">Today</div><div class="v">Runs fully offline on simulated data — no API keys, no installs.</div></div>
    <div class="row"><div class="k">The seam</div><div class="v">Every platform call goes through one interface (<code>platforms.py</code>). Swapping mock for live is a single, contained change.</div></div>
    <div class="row"><div class="k">Read tools</div><div class="v"><code>get_campaigns</code> / <code>get_performance</code> map onto Synter Media, the official Google Ads MCP, or Meta/Pipeboard.</div></div>
    <div class="row"><div class="k">Write tools</div><div class="v"><code>update_budget</code> / <code>update_bid</code> / <code>create_campaign</code> map onto the same MCP servers' write actions.</div></div>
    <div class="row"><div class="k">Creative</div><div class="v">The image prompts route to Imagen 4, Flux, or Runway via a text-to-image tool.</div></div>
    <div class="row"><div class="k">Recommended rollout</div><div class="v">Keep <code>dry_run</code> as default for the first weeks, review proposals, then grant <code>assist</code> and finally <code>auto</code>.</div></div>
  </div>

  <h2>Limitations</h2>
  <div class="panel"><ul class="rails">
    <li><b>Offline mock data.</b> Every number here is simulated for demonstration. It is not connected to any live ad account and reflects no real spend or performance.</li>
    <li><b>Not production-ready.</b> This is an MVP that shows the agentic workflow and safety model — it is designed for, but not yet wired to, live MCP integrations.</li>
    <li><b>No guaranteed outcomes.</b> "Estimated wasted spend" and "potential reallocation" are illustrative indications, not promised savings.</li>
    <li><b>Transparent rules, not a learned model.</b> Decisions come from simple, explainable rules; a real deployment would validate them against live results before granting autonomy.</li>
  </ul></div>

  <div class="foot">Generated by the Agentic Advertising MVP · offline demo · simulated data.
  Source patterns: github.com/jshorwitz/awesome-agentic-advertising</div>

</div></body></html>"""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out

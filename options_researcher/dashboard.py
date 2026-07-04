"""options_researcher/dashboard.py -- M7 game-style dashboard.

assemble() gathers real project state (the book, the facts ledger, report
files, and a handful of underlying closes) into one plain dict. render()
turns that dict into a single self-contained HTML string (dark, game-styled,
inline <style> only -- no network calls, no external assets, no JS
frameworks). Neither function mutates positions, the ledger, or reports;
neither makes a network call.

Every assemble() argument can be injected for tests; when omitted, the real
project state is loaded:
  book      -> options_researcher.portfolio.analyze()
  facts     -> research.facts.read_facts()
  reports   -> sorted(glob("reports/*.md"))
  closes    -> last ~60 closes per config.UNIVERSE symbol via
               data.underlying_closes.load_closes(sym, start, end,
               allow_oos=True) (display only -- never feeds a verdict)

render(data) is pure string templating over the dict assemble() returns. It
does no file I/O; Task 3's CLI is responsible for writing the result to
disk.
"""
from __future__ import annotations

import html as _html
import os
from datetime import datetime as _datetime
from datetime import timezone
from glob import glob

OUTPUT_PATH = os.path.join(".tmp", "dashboard", "index.html")

# One entry per major fact tag seen in `ledger/facts.log` (see
# `grep -o '\t[A-Z_0-9]*' ledger/facts.log | sort -u`). Routine/negative
# operational noise (BLIND_CACHE, BLIND_CACHE_INVALIDATED, CACHE_GAP,
# SMOKE_TEST, THETADATA_AUTH, SIZING_BOUNDARY_ARTIFACT, MEASURED_*,
# STRIKE_GRID_REALITY, SINGLE_NAME_DIAGNOSTICS) is deliberately left out of
# the achievement map -- those are day-to-day plumbing/negative findings,
# not milestones worth a celebration tile. Flavor text is short, upbeat,
# and beginner-friendly per the plan.
ACHIEVEMENTS = {
    "CEG_CACHE_COMPLETE": (
        "Data Hoarder", "Cached every CEG chain since it started trading"),
    "PIVOT_4NAME_SCOPE": (
        "New Game+", "Re-scoped the whole project to the 4-name thesis"),
    "UNDERLYING_CLOSES_YAHOO": (
        "Free Data Achieved", "$0.0000 vs official closes -- for free"),
    "UNDERLYING_CLOSES_PARITY": (
        "MacGyver Data", "Built a close price series out of your own option chains"),
    "H4_PAPER_WINDOW_SEEDED": (
        "Party Assembled", "The book went live with real seeded positions"),
    "H4_BUCKET_AMENDMENT": (
        "Full Loadout", "LEAPS slot filled -- the forward paper window is fully seeded"),
    "H4_EVIDENCE_BACKTEST": (
        "Field Report", "Ran the combined evidence backtest across the whole book"),
    "H5_REGISTERED": (
        "New Quest", "Sector Income Core registered -- the next hypothesis is live"),
    "H1_REGISTERED": (
        "First Blood", "First hypothesis registered end-to-end"),
    "H1_SCOPE_DECISION": (
        "Rules Locked In", "Froze the H1 scope before looking at any results"),
    "WIDTH_SWEEP_COMPLETE": (
        "Swept the Board", "Finished the full width sweep, no peeking"),
    "SPIKE_OFFLINE_BACKTEST": (
        "Engine Test", "Proved the offline backtest engine actually runs"),
    "HARNESS_SMOKE": (
        "Smoke Signal", "Smoke-tested the harness on real cached data"),
    "OWNER_DECISION": (
        "The Buck Stops Here", "Made the call on an OOS reveal, on the record"),
    "STUDY_A": ("Study Hall: A", "Ran the IV-vs-realized study"),
    "STUDY_B": ("Study Hall: B", "Ran the earnings-move study"),
    "STUDY_C": ("Study Hall: C", "Ran the covered-call study"),
    "STUDY_D": ("Study Hall: D", "Ran the LEAPS study"),
    "STUDY_E": ("Study Hall: E", "Ran the short-put/vertical study"),
}


def _achievement_tag(line: str) -> str | None:
    """Extract the fact tag from a `<iso-timestamp>\\t<TAG> <rest>` line."""
    try:
        _, rest = line.split("\t", 1)
    except ValueError:
        # Lenient by design (not fail-loud): read_facts() only guarantees
        # non-blank lines from ledger/facts.log, a log this module doesn't
        # own exclusively, so a hand-edited/malformed line here should be
        # skipped rather than crash the dashboard.
        return None
    return rest.split(" ", 1)[0] if rest else None


def _default_book() -> dict:
    from options_researcher.portfolio import analyze
    return analyze()


def _default_facts() -> list[str]:
    from research.facts import read_facts
    return read_facts()


def _default_reports() -> list[str]:
    return sorted(glob("reports/*.md"))


def _default_closes() -> dict[str, list[float]]:
    import config
    from data.underlying_closes import load_closes

    out: dict[str, list[float]] = {}
    for sym in config.UNIVERSE:
        series = load_closes(sym, config.BACKTEST_START, config.BACKTEST_END,
                             allow_oos=True)
        out[sym] = [float(v) for v in series.iloc[-60:]]
    return out


def assemble(*, book: dict | None = None, facts: list[str] | None = None,
            reports: list[str] | None = None,
            closes: dict[str, list[float]] | None = None) -> dict:
    """Gather book, achievements, reports, and sparkline data into one dict.

    Every argument defaults to loading the real project state; pass any of
    them explicitly (e.g. from a test fixture) to override. Read-only,
    no network calls, no HTML/rendering logic (that's Task 2).
    """
    if book is None:
        book = _default_book()
    if facts is None:
        facts = _default_facts()
    if reports is None:
        reports = _default_reports()
    if closes is None:
        closes = _default_closes()

    achievements = []
    for line in facts:
        tag = _achievement_tag(line)
        if tag in ACHIEVEMENTS:
            title, flavor = ACHIEVEMENTS[tag]
            achievements.append({"key": tag, "title": title, "flavor": flavor})

    return {
        "book": book.get("marks", []),
        "bucket_issues": book.get("bucket_issues", []),
        "coverage_issues": book.get("coverage_issues", []),
        "achievements": achievements,
        "reports": list(reports),
        "sparklines": dict(closes),
    }


# --------------------------------------------------------------------------
# render() -- HTML templating (Task 2). Pure string building: no file I/O,
# no network, no JS framework. Every dynamic string that came from `data`
# (as opposed to a hardcoded template literal below) is passed through
# html.escape before it lands in the output.
# --------------------------------------------------------------------------

_PARTY = [
    # (symbol, accent color, role line)
    ("MSFT", "#4da3ff", "The Tank — LEAPS core"),
    ("AMZN", "#ff9900", "Bench — returns with covered calls"),
    ("VST", "#ffd23f", "Dual-class — CSP + tactical"),
    ("CEG", "#7CFC9B", "Reserve — LEAPS slot 2"),
]

_QUEST_LOG_COMPLETED = [
    "M1", "M2", "M3", "M4", "M5", "M6", "seeded window",
]
_QUEST_LOG_ACTIVE = "Survive 2 quarters of forward window"
_QUEST_LOG_LOCKED = "Dashboard v2 (live sparkline history)"

_GRAVEYARD = [
    "H1 $2-wide (FAIL)",
    "H2 $5-wide (FAIL)",
    "IV-rank premium selling (Study A)",
    "$5 bull put spreads (Study E, 8/8 ~$0)",
]

# Flag prefix -> (pill label, background color). Matched with str.startswith
# because real flags carry suffixes, e.g. "ROLL_DUE(dte<=90)",
# "ASSIGNMENT_WATCH(|close-K|<=2%)", "EARNINGS_2026-08-01".
_FLAG_STYLES = [
    ("ROLL_DUE", "#caa53d"),          # amber
    ("ASSIGNMENT_WATCH", "#ff5470"),  # red
    ("EARNINGS", "#a06cd5"),          # purple
    ("QUOTE_MISSING", "#6b7280"),     # grey
]


def _esc(value) -> str:
    return _html.escape(str(value))


def _flag_style(flag: str) -> str:
    for prefix, color in _FLAG_STYLES:
        if flag.startswith(prefix):
            return color
    return "#6b7280"


def _flag_pills(flags: list[str]) -> str:
    if not flags:
        return ""
    pills = []
    for flag in flags:
        color = _flag_style(flag)
        pills.append(
            f'<span class="pill" style="background:{color}">{_esc(flag)}</span>'
        )
    return "".join(pills)


def _sparkline_svg(symbol: str, closes: list[float], color: str) -> str:
    """Inline <polyline> sparkline, up to the last 60 closes, normalized
    into a 120x28 viewBox. No closes -> an empty (flat) placeholder line
    so the card layout doesn't break."""
    width, height = 120, 28
    pts = [float(v) for v in closes[-60:]]
    if not pts:
        points = f"0,{height / 2} {width},{height / 2}"
    elif len(pts) == 1:
        points = f"0,{height / 2} {width},{height / 2}"
    else:
        lo, hi = min(pts), max(pts)
        span = hi - lo
        n = len(pts)
        coords = []
        for i, v in enumerate(pts):
            x = (i / (n - 1)) * width
            y = (height - 2) - ((v - lo) / span * (height - 4)) if span else height / 2
            coords.append(f"{x:.2f},{y:.2f}")
        points = " ".join(coords)
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'class="sparkline" aria-label="{_esc(symbol)} sparkline">'
        f'<polyline points="{points}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" /></svg>'
    )


def _party_card(symbol: str, color: str, role: str, sparklines: dict,
                marks: list[dict]) -> str:
    closes = sparklines.get(symbol, [])
    badges = []
    for m in marks:
        if m.get("symbol") != symbol:
            continue
        pnl = m.get("pnl", 0.0) or 0.0
        badge_color = "#2fd27d" if pnl >= 0 else "#ff5470"
        sign = "+" if pnl >= 0 else ""
        badges.append(
            f'<span class="pnl-badge" style="color:{badge_color}">'
            f'{sign}{pnl:,.2f}</span>'
        )
    badges_html = "".join(badges) if badges else '<span class="pnl-none">no open marks</span>'
    return f"""
    <div class="party-card" style="border-color:{color}">
      <div class="party-name" style="color:{color}">{_esc(symbol)}</div>
      <div class="party-role">{_esc(role)}</div>
      {_sparkline_svg(symbol, closes, color)}
      <div class="party-badges">{badges_html}</div>
    </div>"""


def _book_rows(marks: list[dict]) -> str:
    if not marks:
        return '<tr><td colspan="8" class="empty">No open marks.</td></tr>'
    rows = []
    for m in marks:
        pnl = m.get("pnl", 0.0) or 0.0
        pnl_color = "#2fd27d" if pnl >= 0 else "#ff5470"
        sign = "+" if pnl >= 0 else ""
        flags = m.get("flags", []) or []
        rows.append(f"""
      <tr>
        <td>{_esc(m.get("id", ""))}</td>
        <td>{_esc(m.get("structure", ""))}</td>
        <td>{_esc(m.get("symbol", ""))}</td>
        <td>{_esc(m.get("strike", ""))}</td>
        <td>{_esc(m.get("expiration", ""))}</td>
        <td>{_esc(m.get("dte", ""))}</td>
        <td>{_esc(m.get("mark", ""))}</td>
        <td style="color:{pnl_color}">{sign}{_esc(f"{pnl:,.2f}")}</td>
        <td>{_flag_pills(flags)}</td>
      </tr>""")
    return "".join(rows)


def _bucket_banner(bucket_issues: list[str]) -> str:
    if not bucket_issues:
        return '<div class="banner banner-green">ALL BUCKETS GREEN</div>'
    items = "".join(f"<li>{_esc(issue)}</li>" for issue in bucket_issues)
    return f'<div class="banner banner-red"><ul>{items}</ul></div>'


def _quest_log() -> str:
    completed = "".join(
        f'<li class="quest-done">✓ <s>{_esc(q)}</s></li>'
        for q in _QUEST_LOG_COMPLETED
    )
    active = f'<li class="quest-active">{_esc(_QUEST_LOG_ACTIVE)}</li>'
    locked = f'<li class="quest-locked">\U0001F512 {_esc(_QUEST_LOG_LOCKED)}</li>'
    return f'<ol class="quest-log">{completed}{active}{locked}</ol>'


def _achievements_grid(achievements: list[dict]) -> str:
    if not achievements:
        tiles = '<div class="empty">No achievements unlocked yet.</div>'
    else:
        tiles = "".join(f"""
      <div class="ach-tile">
        <div class="ach-title">{_esc(a.get("title", ""))}</div>
        <div class="ach-flavor">{_esc(a.get("flavor", ""))}</div>
      </div>""" for a in achievements)
    graveyard = "".join(f"<li>{_esc(kill)}</li>" for kill in _GRAVEYARD)
    return f"""
    <div class="ach-grid">{tiles}</div>
    <div class="graveyard">
      <div class="graveyard-title">Graveyard</div>
      <ul>{graveyard}</ul>
    </div>"""


def _reports_list(reports: list[str]) -> str:
    if not reports:
        return '<div class="empty">No reports yet.</div>'
    items = "".join(f"<li>{_esc(r)}</li>" for r in reports)
    return f"<ul>{items}</ul>"


def render(data: dict) -> str:
    """Render the assemble() dict into a single self-contained HTML string.

    Pure string templating: no file I/O, no network calls, no external
    assets (fonts/CDN/JS frameworks). Every value pulled from `data` is
    escaped with html.escape before being embedded.
    """
    marks = data.get("book", [])
    bucket_issues = data.get("bucket_issues", [])
    achievements = data.get("achievements", [])
    reports = data.get("reports", [])
    sparklines = data.get("sparklines", {})

    as_of = _datetime.now(timezone.utc).date().isoformat()
    party_cards = "".join(
        _party_card(symbol, color, role, sparklines, marks)
        for symbol, color, role in _PARTY
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MISSION CONTROL</title>
<style>
  :root {{
    color-scheme: dark;
  }}
  body {{
    background: #0b0e17;
    color: #e6e9f2;
    font-family: ui-monospace, Menlo, monospace;
    margin: 0;
    padding: 24px;
  }}
  h1, h2 {{
    font-family: ui-monospace, Menlo, monospace;
    letter-spacing: 0.08em;
  }}
  .panel {{
    background: #141a2a;
    border: 1px solid #2a3350;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
  }}
  .header-sub {{
    color: #9aa4c0;
    font-size: 0.9em;
  }}
  .party-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }}
  .party-card {{
    background: #141a2a;
    border: 1px solid #2a3350;
    border-left: 3px solid;
    border-radius: 12px;
    padding: 12px;
    min-width: 180px;
    flex: 1;
  }}
  .party-name {{
    font-weight: bold;
    font-size: 1.2em;
  }}
  .party-role {{
    color: #9aa4c0;
    font-size: 0.85em;
    margin-bottom: 8px;
  }}
  .sparkline {{
    display: block;
    margin: 6px 0;
  }}
  .party-badges {{
    margin-top: 6px;
  }}
  .pnl-badge {{
    font-weight: bold;
    margin-right: 6px;
  }}
  .pnl-none {{
    color: #6b7280;
    font-size: 0.85em;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px solid #2a3350;
    font-size: 0.9em;
  }}
  .pill {{
    display: inline-block;
    color: #0b0e17;
    border-radius: 999px;
    padding: 2px 8px;
    margin-right: 4px;
    font-size: 0.75em;
    font-weight: bold;
  }}
  .banner {{
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
  }}
  .banner-green {{
    background: #163d2c;
    color: #2fd27d;
    font-weight: bold;
  }}
  .banner-red {{
    background: #3d1620;
    color: #ff5470;
    font-weight: bold;
  }}
  .quest-log {{
    padding-left: 20px;
  }}
  .quest-done {{
    color: #6b7280;
  }}
  .quest-active {{
    color: #ffd23f;
    font-weight: bold;
  }}
  .quest-locked {{
    color: #4b5270;
  }}
  .ach-grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }}
  .ach-tile {{
    background: #1b2338;
    border: 1px solid #2a3350;
    border-radius: 10px;
    padding: 10px 14px;
    min-width: 160px;
  }}
  .ach-title {{
    font-weight: bold;
    color: #ffd23f;
  }}
  .ach-flavor {{
    color: #9aa4c0;
    font-size: 0.85em;
    margin-top: 4px;
  }}
  .graveyard {{
    margin-top: 16px;
    color: #6b7280;
  }}
  .graveyard-title {{
    font-weight: bold;
    color: #ff5470;
    margin-bottom: 6px;
  }}
  .empty {{
    color: #6b7280;
    font-style: italic;
  }}
</style>
</head>
<body>

<div class="panel">
  <h1>MISSION CONTROL</h1>
  <div class="header-sub">H4 FORWARD WINDOW &mdash; as of {_esc(as_of)}</div>
</div>

<div class="panel">
  <h2>PARTY</h2>
  <div class="party-row">{party_cards}
  </div>
</div>

<div class="panel">
  <h2>BOOK</h2>
  {_bucket_banner(bucket_issues)}
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Structure</th><th>Symbol</th><th>Strike</th>
        <th>Expiration</th><th>DTE</th><th>Mark</th><th>P&amp;L</th><th>Flags</th>
      </tr>
    </thead>
    <tbody>
      {_book_rows(marks)}
    </tbody>
  </table>
</div>

<div class="panel">
  <h2>QUEST LOG</h2>
  {_quest_log()}
</div>

<div class="panel">
  <h2>ACHIEVEMENTS</h2>
  {_achievements_grid(achievements)}
</div>

<div class="panel">
  <h2>REPORTS</h2>
  {_reports_list(reports)}
</div>

</body>
</html>
"""


def main(**assemble_kwargs) -> str:
    """Assemble real (or injected, for tests) project state, render it, and
    write it to OUTPUT_PATH. Read-only over project data; the only write is
    the dashboard HTML file itself. Returns the written path."""
    data = assemble(**assemble_kwargs)
    out_html = render(data)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(out_html)
    abs_path = os.path.abspath(OUTPUT_PATH)
    print(f"wrote {abs_path}")
    print("open it in your browser to see mission control")
    return abs_path


if __name__ == "__main__":
    main()

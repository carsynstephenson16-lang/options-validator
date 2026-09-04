"""options_researcher/dashboard.py -- scanner/watchlist dashboard.

assemble() gathers real project state (recorded options if any, the facts
ledger, report files, and a handful of underlying closes) into one plain dict.
render() turns that dict into a single self-contained HTML string (dark,
game-styled, inline <style> only -- no network calls, no external assets, no
JS frameworks). Neither function mutates positions, the ledger, or reports;
neither makes a network call.

Every assemble() argument can be injected for tests; when omitted, the real
project state is loaded:
  book      -> options_researcher.portfolio.analyze()
  facts     -> research.facts.read_facts()
  reports   -> sorted(glob("reports/*.md"))
  closes    -> last ~60 closes per config.UNIVERSE symbol via
               data.underlying_closes.load_closes(sym, start, end,
               allow_oos=True) (display only -- never feeds a verdict)
  triggers  -> {symbol: "OBSERVE"/"DATA_GAP"} from entry_watch._gather()
               (H5's entry trigger is RETIRED, ledger seq 29; these are
               observations -- display only, never a verdict; tolerant of
               load failure, falls back to {} so the dashboard still renders)

render(data) is pure string templating over the dict assemble() returns. It
does no file I/O; Task 3's CLI is responsible for writing the result to
disk.
"""

from __future__ import annotations

import html as _html
import os
import sys
from datetime import datetime as _datetime
from datetime import timezone
from glob import glob
from zoneinfo import ZoneInfo

import pandas as pd

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
    "CEG_CACHE_COMPLETE": ("Data Hoarder", "Cached every CEG chain since it started trading"),
    "PIVOT_4NAME_SCOPE": ("New Game+", "Re-scoped the whole project to the 4-name thesis"),
    "UNDERLYING_CLOSES_YAHOO": ("Free Data Achieved", "$0.0000 vs official closes -- for free"),
    "UNDERLYING_CLOSES_PARITY": (
        "MacGyver Data",
        "Built a close price series out of your own option chains",
    ),
    "H4_PAPER_WINDOW_SEEDED": ("Historical Seed", "Old paper rows were seeded, then later cleared"),
    "H4_BUCKET_AMENDMENT": ("Budget Amended", "Sizing room changed; not a live position"),
    "H4_EVIDENCE_BACKTEST": ("Field Report", "Ran historical evidence; not the current book"),
    "H5_REGISTERED": ("Scanner Online", "Sector Income Core registered as the candidate rubric"),
    "H5_SCANNER_RESET": ("Clean Slate", "Current state reset to scanner-first: no options open"),
    "H1_REGISTERED": ("First Blood", "First hypothesis registered end-to-end"),
    "H1_SCOPE_DECISION": ("Rules Locked In", "Froze the H1 scope before looking at any results"),
    "WIDTH_SWEEP_COMPLETE": ("Swept the Board", "Finished the full width sweep, no peeking"),
    "SPIKE_OFFLINE_BACKTEST": ("Engine Test", "Proved the offline backtest engine actually runs"),
    "HARNESS_SMOKE": ("Smoke Signal", "Smoke-tested the harness on real cached data"),
    "OWNER_DECISION": ("The Buck Stops Here", "Made the call on an OOS reveal, on the record"),
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


def _ny_build_date(today: str | None = None) -> str:
    """Return the injected or current New York build date as an ISO string."""
    return today or _datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def _default_closes(*, today: str | None = None) -> dict[str, list[float]]:
    import config
    from data.underlying_closes import load_closes

    end = _ny_build_date(today)
    out: dict[str, list[float]] = {}
    for sym in config.UNIVERSE:
        series = load_closes(sym, config.BACKTEST_START, end, allow_oos=True)
        out[sym] = [float(v) for v in series.iloc[-60:]]
    return out


def _default_data_as_of(*, today: str | None = None) -> str:
    """The page's honest "data as-of" date: the EARLIEST last-cached-close
    date across config.UNIVERSE (never today's wall clock). Taking the
    earliest, not the freshest, symbol's last date means a stale name can
    never be hidden behind a fresher one -- the banner must say the stale
    date. A symbol with no cached series at all is skipped, not treated as
    "no data" for the whole page; "unknown" only fires when every symbol is
    unreadable."""
    import config
    from data.underlying_closes import load_closes

    end = _ny_build_date(today)
    dates: list[str] = []
    for sym in config.UNIVERSE:
        try:
            series = load_closes(sym, config.BACKTEST_START, end, allow_oos=True)
        except OSError:
            continue
        if len(series):
            dates.append(str(series.index[-1]))
    return min(dates) if dates else "unknown"


def assemble(
    *,
    book: dict | None = None,
    facts: list[str] | None = None,
    reports: list[str] | None = None,
    closes: dict[str, list[float]] | None = None,
    triggers: dict[str, str] | None = None,
    data_as_of: str | None = None,
    h7_window: dict | None = None,
    holdings: pd.DataFrame | None = None,
    h7_authority: dict | None = None,
) -> dict:
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
    if data_as_of is None:
        data_as_of = _default_data_as_of()
    if triggers is None:
        try:
            from options_researcher.entry_watch import _gather

            triggers = {r["symbol"]: r["verdict"] for r in _gather()}
        except (OSError, KeyError, ValueError, ImportError) as e:
            # Expected data-gap failures only; anything else must crash
            # loudly rather than render a silently-empty trigger panel.
            print(f"WARN entry-watch unavailable, trigger panel empty: {e}", file=sys.stderr)
            triggers = {}
    if h7_window is None:
        try:
            from options_researcher.h7_window_status import window_status

            h7_window = window_status()
        except Exception as exc:
            # Presentation boundary: the rest of mission control must remain
            # visible, while this panel shows the exact status failure.
            h7_window = {
                "ok": False,
                "detail": f"window status unavailable: {exc}",
            }
    if h7_authority is None:
        from data.ritual_authority import (
            CURRENT_AUTHORITY,
            RitualAuthority,
            evaluate_full_ritual,
        )

        readiness = evaluate_full_ritual(
            RitualAuthority(
                h7_active=CURRENT_AUTHORITY.h7_active,
                exact_session_source_active=True,
                ritual_data_phase_active=True,
            )
        )
        h7_authority = {
            "h7_active": CURRENT_AUTHORITY.h7_active,
            "blockers": list(readiness.blockers),
        }
    if holdings is None:
        try:
            from options_researcher.portfolio import load_holdings

            holdings = load_holdings()
        except (OSError, TypeError, ValueError) as exc:
            print(f"WARN holdings.csv unreadable: {exc}", file=sys.stderr)
            holdings = None

    party_roles = {
        "MSFT": "Watch — LEAPS depth",
        "AMZN": "Watch — income candidates",
        "CEG": "Watch — power-side candidate",
    }
    if holdings is None:
        party_roles["VST"] = "Held — shares UNKNOWN (holdings.csv unreadable)"
    else:
        vst_rows = holdings[holdings["symbol"] == "VST"]
        if vst_rows.empty:
            print("WARN no holdings.csv row for VST", file=sys.stderr)
            party_roles["VST"] = "Held — shares UNKNOWN (no holdings.csv row for VST)"
        else:
            shares = int(vst_rows["shares"].sum())
            mark_count = sum(mark.get("symbol") == "VST" for mark in book.get("marks", []))
            if mark_count == 0:
                mark_text = "no options"
            else:
                suffix = "mark" if mark_count == 1 else "marks"
                mark_text = f"{mark_count} open option {suffix}"
            party_roles["VST"] = f"Held — {shares} shares, {mark_text}"

    achievements_by_tag = {}
    for line in facts:
        tag = _achievement_tag(line)
        if tag in ACHIEVEMENTS:
            if tag not in achievements_by_tag:
                title, flavor = ACHIEVEMENTS[tag]
                achievements_by_tag[tag] = {
                    "key": tag,
                    "title": title,
                    "flavor": flavor,
                    "count": 0,
                }
            achievements_by_tag[tag]["count"] += 1
    achievements = list(achievements_by_tag.values())

    return {
        "book": book.get("marks", []),
        "bucket_issues": book.get("bucket_issues", []),
        "coverage_issues": book.get("coverage_issues", []),
        "achievements": achievements,
        "reports": list(reports),
        "sparklines": dict(closes),
        "triggers": dict(triggers),
        "data_as_of": data_as_of,
        "h7_window": h7_window,
        "h7_authority": h7_authority,
        "party_roles": party_roles,
    }


# --------------------------------------------------------------------------
# render() -- HTML templating (Task 2). Pure string building: no file I/O,
# no network, no JS framework. Every dynamic string that came from `data`
# (as opposed to a hardcoded template literal below) is passed through
# html.escape before it lands in the output.
# --------------------------------------------------------------------------

_PARTY = [
    # (symbol, accent color)
    ("MSFT", "#4da3ff"),
    ("AMZN", "#ff9900"),
    ("VST", "#ffd23f"),
    ("CEG", "#7CFC9B"),
]

_ROLE_UNAVAILABLE = "ROLE UNAVAILABLE (assemble() supplied no party_roles)"

_QUEST_LOG_COMPLETED = [
    "M1",
    "M2",
    "M3",
    "M4",
    "M5",
    "M6",
    "scanner dashboard",
]
_QUEST_LOG_ACTIVE = "Find an attractive candidate, then record it intentionally"
_QUEST_LOG_LOCKED = "Forward paper window starts after first tracked option"

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
    ("ROLL_DUE", "#caa53d"),  # amber
    ("ASSIGNMENT_WATCH", "#ff5470"),  # red
    ("EARNINGS", "#a06cd5"),  # purple
    ("QUOTE_MISSING", "#6b7280"),  # grey
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
        pills.append(f'<span class="pill" style="background:{color}">{_esc(flag)}</span>')
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


def _party_card(
    symbol: str,
    color: str,
    role: str,
    sparklines: dict,
    marks: list[dict],
    trigger: str | None = None,
) -> str:
    closes = sparklines.get(symbol, [])
    badges = []
    for m in marks:
        if m.get("symbol") != symbol:
            continue
        pnl = m.get("pnl", 0.0) or 0.0
        badge_color = "#2fd27d" if pnl >= 0 else "#ff5470"
        sign = "+" if pnl >= 0 else ""
        badges.append(
            f'<span class="pnl-badge" style="color:{badge_color}">{sign}{pnl:,.2f}</span>'
        )
    badges_html = "".join(badges) if badges else '<span class="pnl-none">no open marks</span>'
    trigger_html = ""
    if trigger:
        t_color = "#ff5470" if trigger == "FIRE" else "#caa53d"
        trigger_html = (
            f'<div class="party-trigger" style="color:{t_color}">TRIGGER: {_esc(trigger)}</div>'
        )
    return f"""
    <div class="party-card" style="border-color:{color}">
      <div class="party-name" style="color:{color}">{_esc(symbol)}</div>
      <div class="party-role">{_esc(role)}</div>
      {trigger_html}
      {_sparkline_svg(symbol, closes, color)}
      <div class="party-badges">{badges_html}</div>
    </div>"""


def _book_rows(marks: list[dict]) -> str:
    if not marks:
        return '<tr><td colspan="9" class="empty">No open options recorded.</td></tr>'
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
        <td>{_esc(m.get("mark") if m.get("mark") is not None else "n/a")}</td>
        <td style="color:{pnl_color}">{sign}{_esc(f"{pnl:,.2f}")}</td>
        <td>{_flag_pills(flags)}</td>
      </tr>""")
    return "".join(rows)


def _bucket_banner(bucket_issues: list[str]) -> str:
    if not bucket_issues:
        return '<div class="banner banner-green">RECORDED OPTION RULES GREEN</div>'
    items = "".join(f"<li>{_esc(issue)}</li>" for issue in bucket_issues)
    return f'<div class="banner banner-red"><ul>{items}</ul></div>'


def _quest_log() -> str:
    completed = "".join(
        f'<li class="quest-done">✓ <s>{_esc(q)}</s></li>' for q in _QUEST_LOG_COMPLETED
    )
    active = f'<li class="quest-active">{_esc(_QUEST_LOG_ACTIVE)}</li>'
    locked = f'<li class="quest-locked">\U0001f512 {_esc(_QUEST_LOG_LOCKED)}</li>'
    return f'<ol class="quest-log">{completed}{active}{locked}</ol>'


def _achievements_grid(achievements: list[dict]) -> str:
    if not achievements:
        tiles = '<div class="empty">No achievements unlocked yet.</div>'
    else:
        tiles = "".join(
            f"""
      <div class="ach-tile">
        <div class="ach-title">{_esc(a.get("title", ""))}{f" ×{a.get('count')}" if a.get("count", 1) > 1 else ""}</div>
        <div class="ach-flavor">{_esc(a.get("flavor", ""))}</div>
      </div>"""
            for a in achievements
        )
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


def _h7_window_panel(window: dict, *, h7_authority: dict | None = None) -> str:
    """Render the read-only H7 operating summary as a standalone panel."""
    if not window.get("ok"):
        return (
            '<div style="border:1px solid #a33;padding:12px;margin:12px 0">'
            f"<b>H7 FORWARD WINDOW</b> &mdash; UNAVAILABLE: "
            f"{_esc(window.get('detail', 'unknown error'))}</div>"
        )
    if not isinstance(h7_authority, dict):
        h7_authority = {}
    if h7_authority.get("h7_active") is not True:
        blockers = h7_authority.get("blockers", [])
        blocker = (
            blockers[0]
            if isinstance(blockers, list) and len(blockers) == 1
            else "H7 BLOCKER TEXT UNAVAILABLE (ritual_authority contract changed)"
        )
        return (
            '<div style="border:1px solid #6ab;padding:12px;margin:12px 0">'
            "<b>H7 FORWARD WINDOW — PAUSED (H7 authority not granted)</b><br>"
            f"{_esc(blocker)}<br>"
            "registered window (paused; scores nothing while paused): "
            f"sessions: {_esc(window['sessions_elapsed'])}/{_esc(window['total_sessions'])} elapsed "
            f"({_esc(window['sessions_remaining'])} left) &middot; "
            f"entries taken: {_esc(window['entries_taken'])}<br>"
            f"universe: {_esc(len(window['included']))} in / {_esc(len(window['excluded']))} out &middot; "
            f"session {_esc(window['receipts']['evaluation_session'])} receipts: "
            f"health {'OK' if window['receipts']['source_health_present'] else 'MISSING'}, "
            f"gate {_esc(window['receipts']['data_gate_verdict'] or ('present' if window['receipts']['data_gate_present'] else 'MISSING'))}"
            "</div>"
        )
    receipts = window["receipts"]
    gate = receipts["data_gate_verdict"] or (
        "present" if receipts["data_gate_present"] else "MISSING"
    )
    return (
        '<div style="border:1px solid #6ab;padding:12px;margin:12px 0">'
        f"<b>H7 FORWARD WINDOW</b> (live, scores once {_esc(window['end'])})<br>"
        f"sessions: {_esc(window['sessions_elapsed'])}/{_esc(window['total_sessions'])} elapsed "
        f"({_esc(window['sessions_remaining'])} left) &middot; entries taken: {_esc(window['entries_taken'])}<br>"
        f"universe: {_esc(len(window['included']))} in / {_esc(len(window['excluded']))} out &middot; "
        f"session {_esc(receipts['evaluation_session'])} receipts: "
        f"health {'OK' if receipts['source_health_present'] else 'MISSING'}, gate {_esc(gate)}</div>"
    )


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
    triggers = data.get("triggers", {})
    data_as_of = data.get("data_as_of") or "unknown"
    h7_window = data.get(
        "h7_window",
        {"ok": False, "detail": "window status missing from dashboard data"},
    )
    h7_authority = data.get("h7_authority")
    # Presentation boundary: a data dict without party roles must say so on
    # the card, never fall back to a role that could misstate a held position
    # (the DR-1 defect by another route); same house pattern as h7_window.
    party_roles = data.get("party_roles", {})

    as_of = _datetime.now(timezone.utc).date().isoformat()
    party_cards = "".join(
        _party_card(
            symbol,
            color,
            party_roles.get(symbol, _ROLE_UNAVAILABLE),
            sparklines,
            marks,
            trigger=triggers.get(symbol),
        )
        for symbol, color in _PARTY
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
    padding: 0;
  }}
  h1, h2 {{
    font-family: ui-monospace, Menlo, monospace;
    letter-spacing: 0.08em;
  }}
  .data-asof-banner {{
    background: #ffce00;
    color: #1a1300;
    font-weight: 900;
    text-align: center;
    padding: 12px 16px;
    font-size: 1.05em;
    letter-spacing: 0.01em;
    border-bottom: 4px solid #ff5470;
    position: sticky;
    top: 0;
    z-index: 100;
  }}
  .page-body {{
    padding: 24px;
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
  .party-trigger {{
    font-size: 0.8em;
    font-weight: bold;
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

<div class="data-asof-banner">DATA AS-OF {_esc(data_as_of)} CLOSE &mdash; quotes move intraday; verify live quotes in your broker before acting. Research only &mdash; not investment advice.</div>

<div class="page-body">

<div class="panel">
  <h1>MISSION CONTROL</h1>
  <div class="header-sub">SCANNER MODE &mdash; as of {_esc(as_of)}</div>
</div>

{_h7_window_panel(h7_window, h7_authority=h7_authority)}

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
    # tmp + os.replace so a mid-write crash can never leave a truncated page
    # over the last good one (same convention as h7_data_gate receipts).
    tmp_path = f"{OUTPUT_PATH}.{os.getpid()}.tmp"
    with open(tmp_path, "w") as f:
        f.write(out_html)
    os.replace(tmp_path, OUTPUT_PATH)
    abs_path = os.path.abspath(OUTPUT_PATH)
    print(f"wrote {abs_path}")
    print("open it in your browser to see mission control")
    return abs_path


if __name__ == "__main__":
    main()

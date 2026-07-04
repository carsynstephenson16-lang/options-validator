"""options_researcher/dashboard.py -- M7 game-style dashboard, data layer.

assemble() gathers real project state (the book, the facts ledger, report
files, and a handful of underlying closes) into one plain dict. It does NOT
render HTML -- that is Task 2's job (options_researcher.dashboard.render).
This module is read-only over research data: it never mutates positions,
the ledger, or reports, and it makes no network calls (closes come from the
local parquet cache via data.underlying_closes.load_closes).

Every argument can be injected for tests; when omitted, the real project
state is loaded:
  book      -> options_researcher.portfolio.analyze()
  facts     -> research.facts.read_facts()
  reports   -> sorted(glob("reports/*.md"))
  closes    -> last ~60 closes per config.UNIVERSE symbol via
               data.underlying_closes.load_closes(sym, start, end,
               allow_oos=True) (display only -- never feeds a verdict)
"""
from __future__ import annotations

from glob import glob

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
        series = load_closes(sym, "2018-01-01", config.BACKTEST_END,
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

"""H7 source health -- is earnings provenance ALIVE for every watched name?

Roadmap Stage 1 (docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md):
per-symbol reporting over the v3 GATING store ONLY. For each name the
watcher evaluates: the newest gating assertion (class/status/source type),
days to the next expected report, and two flags -- MISSING (no live future
schedule: the owner's refresh work-list) and STALE (only post-report grace
coverage left and it lapses within H7_SOURCE_HEALTH_WARN_SESSIONS XNYS
sessions: the gate is ABOUT to start failing closed). Unhealthy is
gate-UNKNOWN or STALE; BANNED stays healthy (an informed pre-report ban).
Exit 1 when any name is unhealthy, 2 when the store is unreadable (fail
closed). READ-ONLY: this module never mutates any store -- refreshing is
tools/h7_refresh_earnings.py, owner-in-the-loop.

Run:
    uv run python -m options_researcher.h7_source_health [--as-of YYYY-MM-DD]

Live runs use now-UTC as the information cutoff; --as-of D replays with the
cutoff at the close of the last completed session before D (exact watcher
replay semantics -- no lookahead).
"""

from __future__ import annotations

from datetime import date, timedelta

import config
from options_researcher.h7_earnings import (
    GATE_UNKNOWN,
    GATING_EVENT_CLASS,
    assertions_view,
    earnings_gate,
    load_assertions,
    next_report,
)

FLAG_MISSING = "MISSING"   # no live future schedule assertion
FLAG_STALE = "STALE"       # only grace coverage left, lapsing within N sessions


def watch_universe() -> list[str]:
    """Exactly the names the watcher evaluates (h7_watch.main)."""
    return [s for s in config.H7_WATCHLIST + config.H7_CORE_LONG_ONLY
            if s not in config.H7_EXCLUDED]


def _sessions_between(start: date, end: date) -> int:
    """XNYS sessions strictly after `start`, up to and including `end`."""
    from data.cache_runner import trading_days

    if end < start:
        return 0
    days = trading_days(start.isoformat(), end.isoformat())
    return len([d for d in days if d > start.isoformat()])


def _asserted_date(a: dict) -> date:
    """The date an assertion asserts (h7_earnings._report_date semantics):
    occurred_date for realized reports, expected_date for schedules."""
    d = a.get("occurred_date") if a["status"] == "occurred" else None
    return d or a["expected_date"]


def symbol_health(symbol: str, on: date, assertions: list[dict], *,
                  known_as_of, warn_sessions: int) -> dict:
    """Health of one name's earnings provenance at `known_as_of`, for
    decisions on `on`. Pure observability over the typed gate primitives;
    adds NO gate semantics of its own."""
    sym = symbol.upper()
    view = [a for a in assertions_view(assertions, known_as_of)
            if a["symbol"] == sym
            and a.get("event_class") == GATING_EVENT_CLASS]
    gate, gate_reason = earnings_gate(sym, on, assertions,
                                      known_as_of=known_as_of)
    newest = max(view, key=lambda a: a["known_as_of_utc"], default=None)
    upcoming = next_report(sym, on, assertions, known_as_of=known_as_of)

    live_future = [a for a in view
                   if a["status"] in ("estimated", "confirmed")
                   and a["expected_date"] is not None
                   and a["expected_date"] >= on]
    grace = timedelta(days=config.H7_EARNINGS_POST_REPORT_GRACE_D)
    occurred_recent = [_asserted_date(a) for a in view
                       if a["status"] == "occurred"
                       and timedelta(0) <= (on - _asserted_date(a)) <= grace]

    grace_end = grace_sessions_left = None
    if live_future:
        coverage = "schedule"
    elif occurred_recent:
        coverage = "grace"
        grace_end = max(occurred_recent) + grace
        grace_sessions_left = _sessions_between(on, grace_end)
    else:
        coverage = "none"

    flags = []
    if coverage != "schedule":
        flags.append(FLAG_MISSING)
    if coverage == "grace" and grace_sessions_left <= warn_sessions:
        flags.append(FLAG_STALE)

    return {
        "symbol": sym,
        "gate": gate,
        "gate_reason": gate_reason,
        "newest_record_id": newest.get("record_id") if newest else None,
        "newest_known_as_of": newest["known_as_of_utc"] if newest else None,
        "event_class": newest["event_class"] if newest else None,
        "status": newest["status"] if newest else None,
        "source_type": newest.get("source_type") if newest else None,
        "next_report": upcoming,
        "days_to_report": (upcoming - on).days if upcoming else None,
        "coverage": coverage,
        "grace_end": grace_end,
        "grace_sessions_left": grace_sessions_left,
        "flags": flags,
        "healthy": gate != GATE_UNKNOWN and FLAG_STALE not in flags,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    from datetime import datetime
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(
        description="H7 source health over the v3 gating store (read-only; "
                    "exits non-zero when any watched name's earnings "
                    "provenance is unhealthy)")
    parser.add_argument(
        "--as-of",
        help="evaluate for this date with the information cutoff at the "
             "close of the last completed session before it (default: "
             "today America/New_York, cutoff now)")
    args = parser.parse_args(argv)

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    on = date.fromisoformat(args.as_of) if args.as_of else ny_today
    if on > ny_today:
        print(f"--as-of {on} is in the future; refusing.")
        return 2
    if args.as_of:
        from data.cache_runner import session_close_utc
        from options_researcher.h7_watch import evaluation_session

        known_as_of = session_close_utc(evaluation_session(on).isoformat())
    else:
        known_as_of = datetime.now(ZoneInfo("UTC"))

    try:
        assertions = load_assertions()
    except Exception as e:  # fail closed: cannot verify provenance at all
        print(f"H7 SOURCE-HEALTH ERROR -- gating store unreadable (fail "
              f"closed): {type(e).__name__}: {e}")
        return 2

    warn = config.H7_SOURCE_HEALTH_WARN_SESSIONS
    names = watch_universe()
    print(f"H7 SOURCE HEALTH on={on.isoformat()} "
          f"known_as_of={known_as_of.isoformat()} warn<={warn} sessions "
          f"(v3 gating store; read-only)")
    unhealthy = 0
    for symbol in names:
        h = symbol_health(symbol, on, assertions,
                          known_as_of=known_as_of, warn_sessions=warn)
        flags = ",".join(h["flags"]) if h["flags"] else "-"
        newest = (f"{h['newest_record_id']} {h['status']}/{h['source_type']} "
                  f"known {h['newest_known_as_of'].date().isoformat()}"
                  if h["newest_record_id"] else "NO GATING ASSERTIONS")
        due = (f"report in {h['days_to_report']}d "
               f"({h['next_report'].isoformat()})"
               if h["next_report"] else "next report UNKNOWN")
        runway = (f", grace ends {h['grace_end'].isoformat()} "
                  f"({h['grace_sessions_left']} sessions left)"
                  if h["coverage"] == "grace" else "")
        verdict = "ok" if h["healthy"] else "UNHEALTHY"
        print(f"{h['symbol']:>5}: {verdict:>9} gate={h['gate']} [{flags}] "
              f"{due}{runway} | newest: {newest}")
        if not h["healthy"]:
            unhealthy += 1
    print(f"summary: {len(names) - unhealthy}/{len(names)} healthy; "
          f"exit {'1 (unhealthy names above)' if unhealthy else '0'}")
    return 1 if unhealthy else 0


if __name__ == "__main__":
    raise SystemExit(main())

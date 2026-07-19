"""H7 source health -- is earnings provenance ALIVE for every watched name?

Roadmap Stage 1 (docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md):
per-symbol reporting over the v3 GATING store ONLY. For each name the
watcher evaluates: the newest gating assertion (class/status/source type),
days to the next expected report, and two flags -- MISSING (no live future
schedule: the owner's refresh work-list) and STALE (only post-report grace
coverage left and it lapses within H7_SOURCE_HEALTH_WARN_SESSIONS XNYS
sessions: the gate is ABOUT to start failing closed). Unhealthy is
gate-UNKNOWN or STALE; BANNED stays healthy (an informed pre-report ban).
Aggregator estimates retained in the append-only store are diagnostic-only
under amendment v1.4 and are invisible to this health/gating view.
Exit 1 when any name is unhealthy, 2 when the store is unreadable (fail
closed). The source stores remain read-only; the command writes only an
immutable evidence receipt. Refreshing is tools/h7_refresh_earnings.py,
owner-in-the-loop.

Run:
    uv run python -m options_researcher.h7_source_health [--as-of YYYY-MM-DD]

Live runs evaluate today's source coverage with now-UTC as the information
cutoff. --as-of D replays the watcher's last completed session before D and
uses that same session for both the gate date and its close cutoff (no
lookahead and no calendar-date/session mismatch).
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import config
from options_researcher.h7_earnings import (
    GATE_UNKNOWN,
    earnings_gate,
    h7_gating_view,
    load_assertions,
    next_report,
    report_date,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import config_hash, diagnostic_source_hash
from research.receipts import input_files, make_receipt, write_immutable_receipt

FLAG_MISSING = "MISSING"   # no live future schedule assertion
FLAG_STALE = "STALE"       # only grace coverage left, lapsing within N sessions


def _sessions_between(start: date, end: date) -> int:
    """XNYS sessions strictly after `start`, up to and including `end`."""
    from data.cache_runner import trading_days

    if end < start:
        return 0
    days = trading_days(start.isoformat(), end.isoformat())
    return len([d for d in days if d > start.isoformat()])


def symbol_health(symbol: str, on: date, assertions: list[dict], *,
                  known_as_of: datetime, warn_sessions: int) -> dict:
    """Health of one name's earnings provenance at `known_as_of`, for
    decisions on `on`. Pure observability over the typed gate primitives;
    adds NO gate semantics of its own."""
    sym = symbol.upper()
    view = [a for a in h7_gating_view(assertions, known_as_of)
            if a["symbol"] == sym]
    gate, gate_reason = earnings_gate(sym, on, assertions,
                                      known_as_of=known_as_of)
    newest = max(view, key=lambda a: a["known_as_of_utc"], default=None)
    upcoming = next_report(sym, on, assertions, known_as_of=known_as_of)

    live_future = [a for a in view
                   if a["status"] in ("estimated", "confirmed")
                   and a["expected_date"] is not None
                   and a["expected_date"] >= on]
    grace = timedelta(days=config.H7_EARNINGS_POST_REPORT_GRACE_D)
    occurred_recent = [report_date(a) for a in view
                       if a["status"] == "occurred"
                       and timedelta(0) <= (on - report_date(a)) <= grace]

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
    if (coverage == "grace" and grace_sessions_left is not None
            and grace_sessions_left <= warn_sessions):
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


def evaluate_health(*, requested_on: date, on: date, known_as_of: datetime,
                    assertions: list[dict], names=None) -> dict:
    """Build the deterministic health result used by CLI and receipts."""
    names = list(watch_universe() if names is None else names)
    warn = config.H7_SOURCE_HEALTH_WARN_SESSIONS
    rows = [symbol_health(symbol, on, assertions,
                          known_as_of=known_as_of, warn_sessions=warn)
            for symbol in names]
    unhealthy = [row["symbol"] for row in rows if not row["healthy"]]
    return {
        "evaluation_session": on.isoformat(),
        "requested_run_date": requested_on.isoformat(),
        "known_as_of_utc": known_as_of.isoformat(),
        "scope": scope_identity(names),
        "healthy_count": len(rows) - len(unhealthy),
        "unhealthy_count": len(unhealthy),
        "unhealthy_symbols": unhealthy,
        "activation_ready": not unhealthy,
        "symbols": {row["symbol"]: row for row in rows},
    }


def build_receipt(result: dict) -> dict:
    """Bind source health to both assertion stores and source identity."""
    from options_researcher.h7_earnings import ASSERTIONS_PATH, RAW_ASSERTIONS_PATH

    return make_receipt("source_health", {
        **result,
        "input_files": input_files({
            "gating_assertions": ASSERTIONS_PATH,
            "raw_assertions": RAW_ASSERTIONS_PATH,
        }),
        "config_hash": config_hash(),
        "source_hash": diagnostic_source_hash(),
    })


def main(argv: list[str] | None = None) -> int:
    import argparse
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
    parser.add_argument("--write-receipt", default=None,
                        help="immutable source-health receipt path")
    args = parser.parse_args(argv)

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        requested_on = date.fromisoformat(args.as_of) if args.as_of else ny_today
    except ValueError:
        print(f"--as-of {args.as_of!r} is not YYYY-MM-DD; refusing.")
        return 2
    if requested_on > ny_today:
        print(f"--as-of {requested_on} is in the future; refusing.")
        return 2
    if args.as_of:
        from data.cache_runner import session_close_utc
        from options_researcher.h7_watch import evaluation_session

        try:
            on = evaluation_session(requested_on)
            known_as_of = session_close_utc(on.isoformat())
        except (IndexError, ValueError) as exc:
            print(f"--as-of {requested_on} has no valid prior XNYS session "
                  f"cutoff ({exc}); refusing.")
            return 2
    else:
        on = requested_on
        known_as_of = datetime.now(ZoneInfo("UTC"))

    try:
        assertions = load_assertions()
    except (OSError, ValueError, csv.Error) as e:
        # Fail closed on the store's documented I/O/validation failures while
        # allowing programming defects to surface instead of masquerading as
        # bad provenance.
        print(f"H7 SOURCE-HEALTH ERROR -- gating store unreadable (fail "
              f"closed): {type(e).__name__}: {e}")
        return 2

    names = watch_universe()
    result = evaluate_health(requested_on=requested_on, on=on,
                             known_as_of=known_as_of, assertions=assertions,
                             names=names)
    warn = config.H7_SOURCE_HEALTH_WARN_SESSIONS
    replay = (f" requested_as_of={requested_on.isoformat()}"
              if args.as_of else "")
    print(f"H7 SOURCE HEALTH on={on.isoformat()}{replay} "
          f"known_as_of={known_as_of.isoformat()} warn<={warn} sessions "
          f"(v3 gating store; read-only)")
    for symbol in names:
        h = result["symbols"][symbol]
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
    receipt = build_receipt(result)
    receipt_path = (Path(args.write_receipt) if args.write_receipt else
                    Path("reports/h7_receipts") /
                    result["scope"]["scope_id"] / "source_health" /
                    f"{result['evaluation_session']}.json")
    try:
        write_immutable_receipt(receipt, receipt_path)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"H7 SOURCE-HEALTH ERROR -- cannot write receipt: "
              f"{type(exc).__name__}: {exc}")
        return 2
    unhealthy = result["unhealthy_count"]
    print(f"summary: {result['healthy_count']}/{len(names)} healthy; "
          f"receipt={receipt_path}; "
          f"exit {'1 (unhealthy names above)' if unhealthy else '0'}")
    return 1 if unhealthy else 0


if __name__ == "__main__":
    raise SystemExit(main())

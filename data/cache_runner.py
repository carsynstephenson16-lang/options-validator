"""
data/cache_runner.py -- paid-month cache runner.

The one-month plan: subscribe to ThetaData Options Standard for exactly one
month -> run `python data/cache_runner.py --in-sample` to smoke-test and cache
every in-sample EOD chain -> run `python data/cache_runner.py --oos-blind` to
blind-cache the OOS holdout -> cancel the subscription. Everything this
harness will ever need lives on disk after that month; no data path in this
repo should require a live subscription again.

Two windows, two integrity postures:
  - IN-SAMPLE (config.BACKTEST_START .. config.IN_SAMPLE_END): fetched through
    get_eod_chain, which reads and returns real values -- fine, because
    in-sample data is what the harness is allowed to look at freely.
  - OOS HOLDOUT (config.IN_SAMPLE_END, config.BACKTEST_END]: fetched ONLY
    through blind_cache_chain, which writes the parquet to disk but returns
    safe metadata only (no prices, greeks, or aggregates thereof) and appends
    its own auditable BLIND_CACHE fact on every call. cache_oos_blind() in
    this module NEVER calls get_eod_chain and NEVER passes allow_oos anywhere
    -- caching the OOS holdout during the paid month must not become a
    stealth look at it. Reading those cached values later still goes through
    get_eod_chain's OOS reveal gate (allow_oos=True), exactly as before.

EOD GAPS guardrail (.cursorrules): ThetaData can miss an EOD mark even when
intraday quotes exist for a name/day (non-trading day, EOD gap, or a day
outside the account's history window all surface the same way -- the fetch
functions raise RuntimeError with "returned no rows" in the message). The
rule is SKIP and log, never substitute: this runner catches exactly that
RuntimeError, appends a CACHE_GAP fact recording the symbol/date, and moves
on. Any other exception is not a gap -- it propagates and stops the run.

Rough scale: ~1258 in-sample trading days x 5 symbols =~ 6290 fetch tasks;
~880 OOS trading days x 5 symbols =~ 4400 blind-cache tasks. Both runs are
resumable -- an already-cached symbol/day (_cache_path(...).exists()) is
skipped without hitting the network, so a killed/rerun job just picks up
where it left off.

Run from the repo root:
    python data/cache_runner.py --dry-run     # counts only, no network, no facts
    python data/cache_runner.py --in-sample   # cache every in-sample EOD chain
    python data/cache_runner.py --oos-blind   # blind-cache the OOS holdout
"""
from __future__ import annotations

import os
import sys
import time

import grpc  # hard dependency of thetadata; import is offline-safe

# Repo root on sys.path so `python data/cache_runner.py ...` (run from the
# repo root, per the docstring above) can import top-level packages -- same
# shim analysis/feasibility.py and analysis/power_check.py use.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from data import thetadata_adapter  # noqa: E402
from data.thetadata_adapter import _cache_path, blind_cache_chain, get_eod_chain  # noqa: E402
from research import facts  # noqa: E402

_GAP_MESSAGE_TOKEN = "returned no rows"
_PROGRESS_EVERY = 250

# Transport-retry policy (observed live 2026-07-03: a multi-hour sequential
# run died at ~3,890 calls with UNAVAILABLE 'Stream removed (Socket closed)').
# Retry ONLY transport/session-shaped gRPC codes, with a client reset (fresh
# auth + channel) and exponential backoff; entitlement problems
# (PERMISSION_DENIED) and everything non-gRPC propagate untouched.
_RETRYABLE_GRPC_CODES = frozenset({
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.UNKNOWN,
    grpc.StatusCode.DEADLINE_EXCEEDED,
    grpc.StatusCode.INTERNAL,
    grpc.StatusCode.UNAUTHENTICATED,      # expired session -> re-auth fixes it
    grpc.StatusCode.RESOURCE_EXHAUSTED,   # rate limit -> backoff helps
})
_RETRY_MAX = 5            # retries per task after the first attempt
_RETRY_BASE_SLEEP_S = 5   # 5, 10, 20, 40, 80s
_sleep = time.sleep       # seam so tests never really sleep


def _fetch_with_transport_retry(fetch_one, symbol: str, day: str):
    """Run one task with bounded recovery from transport-level gRPC failures.
    Gap RuntimeErrors and non-retryable errors pass straight through."""
    for attempt in range(_RETRY_MAX + 1):
        try:
            return fetch_one(symbol, day)
        except grpc.RpcError as exc:
            code = exc.code() if callable(getattr(exc, "code", None)) else None
            if code not in _RETRYABLE_GRPC_CODES or attempt == _RETRY_MAX:
                raise
            wait = _RETRY_BASE_SLEEP_S * (2 ** attempt)
            print(f"transport retry {attempt + 1}/{_RETRY_MAX} for {symbol} @ "
                  f"{day}: {getattr(code, 'name', 'unknown')} -- resetting "
                  f"client, sleeping {wait}s", flush=True)
            thetadata_adapter._reset_client()
            _sleep(wait)


def trading_days(start: str, end: str) -> list[str]:
    """ISO date strings of XNYS trading days in [start, end], inclusive."""
    import pandas_market_calendars as mcal

    schedule = mcal.get_calendar("XNYS").schedule(start_date=start, end_date=end)
    return [ts.date().isoformat() for ts in schedule.index]


def _is_gap_error(exc: RuntimeError) -> bool:
    return _GAP_MESSAGE_TOKEN in str(exc)


def _run_window(days: list[str], symbols: list[str], fetch_one, ledger_dir: str) -> dict:
    """Shared fetch loop for both windows: skip-if-cached, fetch-or-gap,
    progress print, exact counts. `fetch_one(symbol, day)` does the real work
    for one symbol/day and is the only thing that differs between the two
    public functions below."""
    counts = {"fetched": 0, "skipped_cached": 0, "gaps": 0}
    processed = 0

    for day in days:
        for symbol in symbols:
            if _cache_path(symbol, day).exists():
                counts["skipped_cached"] += 1
            else:
                try:
                    _fetch_with_transport_retry(fetch_one, symbol, day)
                except RuntimeError as exc:
                    if not _is_gap_error(exc):
                        raise
                    facts.append_fact(
                        f"CACHE_GAP symbol={symbol} date={day} reason=empty_fetch",
                        base_dir=ledger_dir,
                    )
                    counts["gaps"] += 1
                else:
                    counts["fetched"] += 1

            processed += 1
            if processed % _PROGRESS_EVERY == 0:
                total = len(days) * len(symbols)
                print(
                    f"progress: {processed}/{total} fetched={counts['fetched']} "
                    f"cached={counts['skipped_cached']} gaps={counts['gaps']}"
                )

    return {
        "fetched": counts["fetched"],
        "skipped_cached": counts["skipped_cached"],
        "gaps": counts["gaps"],
        "total_days": len(days),
        "symbols": len(symbols),
    }


def cache_in_sample(symbols=None, *, ledger_dir: str = "ledger") -> dict:
    """Cache every in-sample EOD chain (config.BACKTEST_START ..
    config.IN_SAMPLE_END) for `symbols` (defaults to config.UNIVERSE)."""
    symbols = list(config.UNIVERSE) if symbols is None else list(symbols)
    days = trading_days(config.BACKTEST_START, config.IN_SAMPLE_END)

    def fetch_one(symbol, day):
        get_eod_chain(symbol, day)

    return _run_window(days, symbols, fetch_one, ledger_dir)


def cache_oos_blind(symbols=None, *, ledger_dir: str = "ledger") -> dict:
    """Blind-cache the OOS holdout (config.IN_SAMPLE_END, config.BACKTEST_END]
    for `symbols` (defaults to config.UNIVERSE). Values never surface here --
    see the module docstring. Never calls get_eod_chain."""
    symbols = list(config.UNIVERSE) if symbols is None else list(symbols)
    days = [
        d for d in trading_days(config.IN_SAMPLE_END, config.BACKTEST_END)
        if d > config.IN_SAMPLE_END
    ]

    def fetch_one(symbol, day):
        blind_cache_chain(symbol, day, ledger_dir=ledger_dir)

    return _run_window(days, symbols, fetch_one, ledger_dir)


def dry_run() -> dict:
    """Report task counts for both windows with NO network access and NO
    facts writes: trading-day count, symbol count, total symbol-day fetch
    tasks, and how many are already cached."""
    symbols = list(config.UNIVERSE)

    in_sample_days = trading_days(config.BACKTEST_START, config.IN_SAMPLE_END)
    oos_days = [
        d for d in trading_days(config.IN_SAMPLE_END, config.BACKTEST_END)
        if d > config.IN_SAMPLE_END
    ]

    def summarize(days):
        total_tasks = len(days) * len(symbols)
        already_cached = sum(
            1 for day in days for symbol in symbols
            if _cache_path(symbol, day).exists()
        )
        return {
            "trading_days": len(days),
            "symbols": len(symbols),
            "total_tasks": total_tasks,
            "already_cached": already_cached,
        }

    return {
        "in_sample": summarize(in_sample_days),
        "oos_blind": summarize(oos_days),
    }


def _print_dry_run(summary: dict) -> None:
    for window_name, window in (("IN-SAMPLE", summary["in_sample"]),
                                 ("OOS-BLIND", summary["oos_blind"])):
        print(f"{window_name}: {window['trading_days']} trading days x "
              f"{window['symbols']} symbols = {window['total_tasks']} tasks "
              f"({window['already_cached']} already cached)")


def main(argv=None) -> None:
    argv = sys.argv[1:] if argv is None else argv

    if "--dry-run" in argv:
        summary = dry_run()
        _print_dry_run(summary)
        print(summary)
    elif "--in-sample" in argv:
        summary = cache_in_sample()
        print(summary)
    elif "--oos-blind" in argv:
        summary = cache_oos_blind()
        print(summary)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()

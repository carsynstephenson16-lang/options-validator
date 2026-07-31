"""data/recent_topup.py -- keep forward-paper chain caches current.

The one-month paid-cache plan (data/cache_runner.py) filled history through
config.BACKTEST_END. The H5 forward window then advances in real time, so new
EOD chains must be topped up as sessions pass. This module answers "which
recent trading days are missing?" (pure, tested here) and blind-caches them
via the same integrity-safe path cache_runner uses.

INTEGRITY: recent days are fetched by EXPLICIT DATE through blind_cache_chain
(writes parquet, surfaces no values, logs a BLIND_CACHE fact) -- config
boundaries (BACKTEST_END, IN_SAMPLE_END) are NEVER moved to admit them. Today
is always excluded: its EOD report is not finalized until the next session
(ThetaData refuses current-day bulk EOD), and substituting an intraday snapshot
would violate the EOD-gaps guardrail.

ORCHESTRATOR-ONLY network path: run_topup / the CLI are executed by the
controlling session after review, exactly like data/underlying_closes.
fetch_underlying_eod. Tests cover only the pure day-selection and audit logic.

Run from the repo root:
    python data/recent_topup.py --dry-run
    python data/recent_topup.py --scope h7 --dry-run
    python data/recent_topup.py --scope display-extra --dry-run
    python data/recent_topup.py --scope h7 --refresh-closes
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from data import thetadata_adapter  # noqa: E402

# Strategy-selectable moneyness band (|delta|). Deep-ITM (|delta|~1) contracts
# carry benign IV=0 solver artifacts and far-OTM tails carry wide spreads; the
# H5 income lanes (CSP / covered call / PMCC) select inside this band, so audit
# BLOCKs gate on it while everything else is a warning.
SELECTABLE_ABS_DELTA = (0.15, 0.85)
MAX_IV = 5.0  # 500%


def scope_symbols(scope: str) -> list[str]:
    """Return a canonical, owner-scoped top-up universe.

    The default/core scope preserves the original four-name H5 behavior.
    H7 and the display-only extras are explicit because each is a larger paid-
    data operation and must never happen merely because a caller omitted an
    argument. The display-extra scope does not amend or extend H7.
    """
    if scope == "core":
        return list(config.UNIVERSE)
    if scope == "h7":
        from options_researcher.h7_scope import watch_universe

        return list(dict.fromkeys(watch_universe()))
    if scope == "display-extra":
        return list(config.ATTRACTIVENESS_EXTRA_NAMES)
    raise ValueError(f"unknown top-up scope: {scope!r}")


def refresh_closes(symbols, *, today: str, ledger_dir: str = "ledger", fetch_fn=None) -> dict:
    """Refresh independent Yahoo closes for exactly the selected scope.

    This is an explicit network path used by the owner-run cancellation
    workflow. It never runs during ``--dry-run`` and is injectable so tests
    remain offline.
    """
    if fetch_fn is None:
        from data.underlying_closes import fetch_underlying_eod_yahoo

        fetch_fn = fetch_underlying_eod_yahoo
    result = {symbol: fetch_fn(symbol) for symbol in symbols}
    from research import facts

    facts.append_fact(
        f"DATA_PULL {today}: Yahoo closes refresh for forward scope "
        f"({'/'.join(symbols)}); same-day partial rows excluded by fetcher.",
        base_dir=ledger_dir,
    )
    return result


def topup_days(last_cached: str, today: str, *, trading_days_fn=None) -> list[str]:
    """ISO trading days to fetch: strictly after `last_cached` and strictly
    before `today` (today excluded -- its EOD is not final). Holidays and
    weekends drop out via the XNYS calendar."""
    if trading_days_fn is None:
        from data.cache_runner import trading_days as trading_days_fn
    return [d for d in trading_days_fn(last_cached, today) if last_cached < d < today]


def latest_cached_date(symbols, *, cache_dir=None) -> str | None:
    """Legacy file-presence inventory.

    This helper remains for read-only historical diagnostics. Operational
    freshness must use :func:`latest_complete_session`, which also verifies
    the content-bound acquisition fact.

    The cohort's last file-present trading day = the MIN over symbols of
    each symbol's newest cached chain date. None if any symbol has no cache
    (so a never-cached name is never silently skipped). ISO dates sort
    lexicographically, so string max/min is correct."""
    cache_dir = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    per_symbol_latest = []
    for symbol in symbols:
        dates = [p.stem[len(symbol) + 1:] for p in cache_dir.glob(f"{symbol}_*.parquet")]
        if not dates:
            return None
        per_symbol_latest.append(max(dates))
    return min(per_symbol_latest) if per_symbol_latest else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def latest_complete_session(
    symbols,
    *,
    cache_dir=None,
    facts_path: Path | str = Path("ledger/facts.log"),
) -> str | None:
    """Latest cohort session with a file and matching canonical fact.

    The result is the newest session in the intersection of all per-symbol
    content-bound sessions. Taking the minimum of each symbol's newest session
    is insufficient: another symbol can have a gap on that exact date.
    Orphaned or mismatched newer files are ignored here and become explicit
    tasks in ``run_topup``; the publisher then refuses them unless a reviewed
    recovery manifest or durable pending attestation exists.
    """
    from data.cache_provenance import load_blind_cache_facts

    cache = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    facts_by_key = load_blind_cache_facts(Path(facts_path))
    per_symbol_paths: dict[str, dict[str, Path]] = {}
    for symbol in symbols:
        paths: dict[str, Path] = {}
        for path in cache.glob(f"{symbol}_*.parquet"):
            session = path.stem[len(symbol) + 1:]
            paths[session] = path
        if not paths:
            return None
        per_symbol_paths[symbol] = paths
    if not per_symbol_paths:
        return None
    common = set.intersection(
        *(set(paths) for paths in per_symbol_paths.values())
    )
    for session in sorted(common, reverse=True):
        if all(
            (fact := facts_by_key.get((symbol, session))) is not None
            and fact["sha256"] == _sha256(per_symbol_paths[symbol][session])
            for symbol in symbols
        ):
            return session
    return None


def verify_cohort_provenance(
    symbols,
    session: str,
    *,
    cache_dir=None,
    facts_path: Path | str = Path("ledger/facts.log"),
) -> dict:
    """Fail closed unless every symbol has matching session bytes and fact."""
    from data.cache_provenance import load_blind_cache_facts

    cache = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    facts_by_key = load_blind_cache_facts(Path(facts_path))
    errors: list[str] = []
    identities: dict[str, str] = {}
    for symbol in symbols:
        path = cache / f"{symbol}_{session}.parquet"
        if not path.is_file():
            errors.append(f"{symbol}@{session}: missing cache file {path}")
            continue
        sha256 = _sha256(path)
        fact = facts_by_key.get((symbol, session))
        if fact is None:
            errors.append(f"{symbol}@{session}: missing BLIND_CACHE fact")
        elif fact["sha256"] != sha256:
            errors.append(
                f"{symbol}@{session}: BLIND_CACHE sha256 mismatch "
                f"fact={fact['sha256']} file={sha256}"
            )
        else:
            identities[symbol] = f"{symbol}:{session}:{sha256}"
    if errors:
        raise RuntimeError(
            "cohort provenance preflight failed:\n- " + "\n- ".join(errors)
        )
    return {
        "session": session,
        "symbols": list(symbols),
        "identities": identities,
        "status": "VERIFIED",
    }


def repair_from_manifest(
    manifest_path: Path | str,
    *,
    symbols,
    as_of: str,
    ledger_dir: str = "ledger",
) -> dict:
    """Network-free, all-or-nothing preflight for an approved orphan repair."""
    path = Path(manifest_path)
    payload = json.loads(path.read_text())
    if payload.get("schema") != "cache_recovery/v1":
        raise ValueError("repair manifest schema must be cache_recovery/v1")
    review = payload.get("review")
    if (
        not isinstance(review, dict)
        or review.get("status") != "approved_for_operational_recovery"
    ):
        raise ValueError(
            "repair manifest must be reviewed and approved for operational recovery"
        )
    manifest_session = payload.get("session", payload.get("evaluation_session"))
    if manifest_session != as_of:
        raise ValueError(
            f"repair manifest session {manifest_session!r} != {as_of!r}"
        )
    expected_symbols = list(symbols)
    raw_entries = payload.get("entries", payload.get("files"))
    if not isinstance(raw_entries, list) or len(raw_entries) != len(expected_symbols):
        raise ValueError("repair manifest must contain exactly one entry per symbol")
    manifest_symbols = payload.get("symbols")
    if manifest_symbols is None:
        manifest_symbols = [
            entry.get("symbol") for entry in raw_entries
            if isinstance(entry, dict)
        ]
    if manifest_symbols != expected_symbols:
        raise ValueError("repair manifest symbols do not match selected scope/order")
    entries = {entry.get("symbol"): entry for entry in raw_entries
               if isinstance(entry, dict)}
    if set(entries) != set(expected_symbols):
        raise ValueError("repair manifest entry symbols do not match selected scope")
    parquet_schema = payload.get("parquet_schema")
    declared_schema_columns = (
        parquet_schema.get("columns")
        if isinstance(parquet_schema, dict)
        else None
    )
    if declared_schema_columns is not None and not isinstance(
        declared_schema_columns, list
    ):
        raise ValueError("repair manifest parquet_schema.columns must be a list")

    preflight: dict[str, dict] = {}
    mtimes: dict[str, int] = {}
    for symbol in expected_symbols:
        entry = entries[symbol]
        expected_path = thetadata_adapter._cache_path(symbol, as_of)
        if Path(entry.get("path", "")).resolve() != expected_path.resolve():
            raise ValueError(f"{symbol}: repair manifest path is not canonical")
        if not expected_path.is_file():
            raise FileNotFoundError(f"{symbol}: missing cache file {expected_path}")
        actual_sha = _sha256(expected_path)
        if actual_sha != entry.get("sha256"):
            raise RuntimeError(
                f"{symbol}: repair manifest sha256 mismatch "
                f"expected={entry.get('sha256')} actual={actual_sha}"
            )
        rows, columns = thetadata_adapter._parquet_metadata_without_values(
            expected_path
        )
        declared_columns = entry.get("columns")
        columns_match = (
            len(columns) == declared_columns
            if isinstance(declared_columns, int)
            else columns == declared_columns
        )
        if declared_schema_columns is not None:
            columns_match = columns_match and columns == declared_schema_columns
        stat = expected_path.stat()
        size_match = (
            entry.get("size_bytes") is None
            or entry.get("size_bytes") == stat.st_size
        )
        mtime_match = (
            entry.get("mtime_ns") is None
            or entry.get("mtime_ns") == stat.st_mtime_ns
        )
        if (
            rows != entry.get("rows")
            or not columns_match
            or not size_match
            or not mtime_match
        ):
            raise RuntimeError(f"{symbol}: repair manifest parquet metadata mismatch")
        mtimes[symbol] = stat.st_mtime_ns
        preflight[symbol] = entry

    results = []
    for symbol in expected_symbols:
        result = thetadata_adapter.blind_cache_chain(
            symbol,
            as_of,
            ledger_dir=ledger_dir,
            approved_sha256=preflight[symbol]["sha256"],
        )
        if result["already_cached"] is not True:
            raise RuntimeError(f"{symbol}: repair unexpectedly used fetch path")
        if result["attestation_status"] not in {
            "REPAIRED_ATTESTATION", "VERIFIED_NOOP"
        }:
            raise RuntimeError(
                f"{symbol}: unexpected repair status "
                f"{result['attestation_status']}"
            )
        cache_path = thetadata_adapter._cache_path(symbol, as_of)
        if cache_path.stat().st_mtime_ns != mtimes[symbol]:
            raise RuntimeError(f"{symbol}: repair changed cache mtime")
        results.append(result)

    verified = verify_cohort_provenance(
        expected_symbols,
        as_of,
        facts_path=Path(ledger_dir) / "facts.log",
    )
    return {
        "schema": "cache_recovery_result/v1",
        "manifest": str(path),
        "session": as_of,
        "results": results,
        "verification": verified,
    }


# --------------------------------------------------------------------------
# Offline audit of a freshly-cached day (structural + sanity subset of the
# options-data-audit checks that a single EOD chain can answer -- the
# underlying-vs-independent check #13 needs a separate source and is not run
# here). BLOCK gates on defects that touch a STRATEGY-SELECTABLE contract
# (liquid AND inside the moneyness band); anything filtered by the liquidity
# gate or outside the band is a warning, never a block.
# --------------------------------------------------------------------------

def _liquid_mask(df):
    mid = (df["bid"] + df["ask"]) / 2.0
    ok = (df["open_interest"] >= config.MIN_OPEN_INTEREST) & (df["bid"] >= 0) \
        & (df["ask"] > 0) & (df["ask"] >= df["bid"]) & (mid > 0)
    spread = (df["ask"] - df["bid"]) / mid.where(mid > 0, 1.0)
    return ok & (spread <= config.MAX_SPREAD_PCT)


def audit_chain(df) -> dict:
    """Audit one day's option chain. Returns
    {verdict, block, warn, rows, selectable}. verdict is BLOCK if any defect
    touches a selectable contract, else PASS WITH WARNINGS if any warning,
    else PASS."""
    liquid = _liquid_mask(df)
    selectable = liquid & df["delta"].abs().between(*SELECTABLE_ABS_DELTA)
    bad_iv = (df["iv"] <= 0) | (df["iv"] > MAX_IV) | df["iv"].isna()
    bad_greek = (df["delta"].abs() > 1.0) | (df["gamma"] < 0) | (df["vega"] < 0)
    negative = (df["bid"] < 0) | (df["ask"] < 0) | (df["open_interest"] < 0)
    crossed = df["bid"] > df["ask"]
    dup = df.duplicated(subset=["expiration", "strike", "right"], keep=False)

    block, warn = [], []
    n = int(bad_iv[selectable].sum())
    if n:
        block.append(f"IV<=0/>500%/NaN on {n} selectable contracts")
    n = int(bad_greek[selectable].sum())
    if n:
        block.append(f"greek out of range on {n} selectable contracts")
    n = int(dup[selectable].sum())
    if n:
        block.append(f"duplicate (expiry,strike,right) on {n} selectable contracts")

    n = int((bad_iv & ~selectable).sum())
    if n:
        warn.append(f"IV<=0/>500%/NaN on {n} non-selectable rows (deep-ITM/far-OTM)")
    n = int(negative.sum())
    if n:
        warn.append(f"{n} rows with negative bid/ask/OI (liquidity gate filters them)")
    n = int(crossed.sum())
    if n:
        warn.append(f"{n} crossed-market rows (liquidity gate filters them)")
    n = int(dup.sum())
    if n and not int(dup[selectable].sum()):
        warn.append(f"{n} duplicate rows, none selectable")

    verdict = "BLOCK" if block else ("PASS WITH WARNINGS" if warn else "PASS")
    return {"verdict": verdict, "block": block, "warn": warn,
            "rows": len(df), "selectable": int(selectable.sum())}


def audit_day(symbol: str, date: str, *, cache_dir=None) -> dict:
    """Read a freshly-cached day's parquet and audit it. Thin I/O wrapper over
    audit_chain (the verdict logic is unit-tested there)."""
    import pandas as pd
    cache_dir = Path(thetadata_adapter.CACHE_DIR if cache_dir is None else cache_dir)
    df = pd.read_parquet(cache_dir / f"{symbol}_{date}.parquet")
    return {"symbol": symbol, "date": date, **audit_chain(df)}


# --------------------------------------------------------------------------
# Orchestrator: pull + audit. Network path, run by the controlling session
# after review (see module docstring). Not unit-tested -- mirrors
# data/underlying_closes.fetch_underlying_eod.
# --------------------------------------------------------------------------

def run_topup(
    symbols=None,
    *,
    today=None,
    ledger_dir: str = "ledger",
    dry_run: bool = False,
    do_audit: bool = True,
    trading_days_fn=None,
    manifest_path: Path | None = None,
) -> dict:
    import datetime as _dt
    from zoneinfo import ZoneInfo as _ZoneInfo

    from data.cache_runner import _run_window
    from data.thetadata_adapter import blind_cache_chain
    from research import facts

    symbols = list(config.UNIVERSE) if symbols is None else list(symbols)
    today = today or _dt.datetime.now(_ZoneInfo("America/New_York")).date().isoformat()

    facts_path = Path(ledger_dir) / "facts.log"
    last = latest_complete_session(symbols, facts_path=facts_path)
    if last is None:
        raise RuntimeError(
            "at least one symbol has no cache session with matching BLIND_CACHE "
            "provenance -- run the provenance preflight/approved recovery before "
            "topping up recent days.")
    days = topup_days(last, today, trading_days_fn=trading_days_fn)

    print(f"last complete (cohort): {last}   today (excluded): {today}")
    print(f"missing recent trading days: {days or '(none -- cache is current)'}")
    if dry_run:
        return {"last_cached": last, "today": today, "days": days, "dry_run": dry_run}
    if not days:
        verified = verify_cohort_provenance(
            symbols,
            last,
            facts_path=facts_path,
        )
        return {
            "last_cached": last,
            "today": today,
            "days": days,
            "dry_run": False,
            "provenance": verified,
        }

    def fetch_one(symbol, day):
        return blind_cache_chain(symbol, day, ledger_dir=ledger_dir)

    summary = _run_window(
        days,
        symbols,
        fetch_one,
        ledger_dir,
        inspect_existing=True,
        manifest_path=manifest_path,
    )
    summary.update({"last_cached": last, "today": today, "days": days,
                    "dry_run": False})
    print(
        f"pull: fetched={summary['fetched']} repaired={summary['repaired']} "
        f"verified={summary['verified']} gaps={summary['gaps']}"
    )

    if days:
        verify_cohort_provenance(
            symbols,
            days[-1],
            facts_path=facts_path,
        )

    verdicts = {}
    if do_audit:
        worst = "PASS"
        rank = {"PASS": 0, "PASS WITH WARNINGS": 1, "BLOCK": 2}
        for day in days:
            for symbol in symbols:
                if not thetadata_adapter._cache_path(symbol, day).exists():
                    continue  # gap day -- nothing cached to audit
                a = audit_day(symbol, day)
                verdicts[f"{symbol} {day}"] = a["verdict"]
                if rank[a["verdict"]] > rank[worst]:
                    worst = a["verdict"]
                mark = {"PASS": "ok", "PASS WITH WARNINGS": "warn", "BLOCK": "BLOCK"}
                print(f"  audit {symbol} {day}: {mark[a['verdict']]} "
                      f"(rows={a['rows']} selectable={a['selectable']})"
                      + ("" if not a["block"] else f" -> {a['block']}"))
        summary["audit_verdict"] = worst
        print(f"audit overall: {worst}")

    facts.append_fact(
        f"DATA_PULL_TOPUP {today}: recent-days chain top-up "
        f"({'/'.join(symbols)}) days={days} fetched={summary['fetched']} "
        f"repaired={summary['repaired']} verified={summary['verified']} "
        f"gaps={summary['gaps']} audit={summary.get('audit_verdict', 'skipped')}. "
        "Blind-cache path, no reveal; config boundaries unchanged; today excluded "
        "(EOD not final).",
        base_dir=ledger_dir,
    )
    return summary


def main(argv=None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Top up recent EOD chains for the "
                                "selected forward scope (blind cache + audit).")
    p.add_argument("--scope", choices=("core", "h7", "display-extra"),
                   default="core",
                   help="core = existing four-name H5 scope (default); "
                        "h7 = exact 15-name H7 forward scope; display-extra = "
                        "explicit NBIS/AMAT/CLSK display-only scope")
    p.add_argument("--dry-run", action="store_true",
                   help="list missing recent days and exit (no network)")
    p.add_argument("--no-audit", action="store_true",
                   help="skip the post-pull offline audit")
    p.add_argument("--refresh-closes", action="store_true",
                   help="also refresh independent Yahoo closes for the exact "
                        "selected scope (network; ignored during --dry-run)")
    p.add_argument("--as-of",
                   help="exact completed session for --repair-manifest")
    p.add_argument("--repair-manifest", type=Path,
                   help="reviewed cache_recovery/v1 manifest; network-free")
    args = p.parse_args(argv)
    symbols = scope_symbols(args.scope)
    if args.repair_manifest:
        if not args.as_of:
            p.error("--repair-manifest requires --as-of YYYY-MM-DD")
        if args.dry_run or args.refresh_closes:
            p.error("--repair-manifest cannot be combined with network options")
        result = repair_from_manifest(
            args.repair_manifest,
            symbols=symbols,
            as_of=args.as_of,
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    if args.as_of:
        p.error("--as-of is only valid with --repair-manifest")
    result = run_topup(
        symbols=symbols,
        dry_run=args.dry_run,
        do_audit=not args.no_audit,
        manifest_path=Path("reports/cache_runs")
        / f"recent_topup_{args.scope}.json",
    )
    if (args.refresh_closes and not args.dry_run
            and result.get("audit_verdict") != "BLOCK"):
        closes = refresh_closes(symbols, today=result["today"])
        print(f"closes: refreshed {len(closes)}/{len(symbols)} symbols")
    return 2 if result.get("audit_verdict") == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())

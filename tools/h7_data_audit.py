"""tools/h7_data_audit.py -- formal, content-addressed, fail-closed audit of
the full H7 backtest window (7b-2 C2, owner decision 2026-07-10).

The earlier 7,147-day fetch-time scan was a provenance PREFLIGHT; this is the
complete audit. It enumerates its expected manifest INDEPENDENTLY (XNYS
sessions x H7_BACKTEST_SYMBOLS minus the reviewed registry in
data/audit_exceptions.py) and reports expected / present / missing /
excluded / duplicate counts. Nothing is cleaned or silently excluded: every
session is accounted, every defect counted.

BLOCK-level dimensions (any occurrence -> verdict BLOCK, fail closed):
  * unreadable or schema-invalid chain parquet
  * duplicate (expiration, strike, right) rows inside a day
  * missing non-excepted session (also breaks next-session fill coverage)
  * missing raw close for a chain session (close/chain misalignment)
  * adjusted-close continuity break (|1-day adjusted return| > 50%) --
    split-registry sanity
  * same-NY-session fetch provenance (intraday snapshot stored as EOD),
    from BLIND_CACHE ledger timestamps with file-mtime fallback
  * causal earnings coverage: any session whose typed gate is UNKNOWN at
    that session's information cutoff
WARN-level dimensions (counted, reported, never cleaned):
  * crossed (bid > ask) and one-sided books (the liquidity gates filter
    them at trade construction; their existence is a data fact)
  * expirations already past the session date (stale rows)
  * expirations falling on non-session calendar days (holiday expirations,
    e.g. Good-Friday-adjusted monthlies)
  * rows with unusable delta among two-sided quotes
  * missing calls or missing puts on a day (H7 needs both rights)

The receipt binds the exact manifest, exclusions, per-file sha256 map,
finding counts, audit implementation version, git code sha, and the frozen
config hash. --verify recomputes every file hash: any mutation of an
audited input invalidates the receipt.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data.audit_exceptions import H7_AUDIT_EXCEPTIONS, excluded
from research.hashing import canonical_json, config_hash, sha256_file, sha256_hex

AUDIT_VERSION = "h7-data-audit/1"
CHAIN_DIR = Path(".cache/chains")
CLOSES_DIR = Path(".cache/underlying")
RECEIPT_PATH = Path("reports/h7_audit/receipt.json")
CHAIN_COLUMNS = ["expiration", "strike", "right", "bid", "ask",
                 "open_interest", "iv", "delta", "gamma", "theta", "vega"]
NY = ZoneInfo("America/New_York")
_BLIND_RE = re.compile(r"^(\S+)\tBLIND_CACHE symbol=(\S+) date=(\S+) ")


def expected_manifest(symbols=None, start=None, end=None,
                      sessions=None) -> dict:
    """{symbol: {"expected": [...], "excluded": {day: kind}}} enumerated
    independently of what is on disk."""
    from data.cache_runner import trading_days
    symbols = list(symbols or config.H7_BACKTEST_SYMBOLS)
    start = start or config.H7_BACKTEST_START
    end = end or config.H7_BACKTEST_END
    sessions = sessions if sessions is not None else trading_days(start, end)
    out: dict = {}
    for sym in symbols:
        exp, exc = [], {}
        for day in sessions:
            entry = excluded(sym, day)
            if entry is None:
                exp.append(day)
            else:
                exc[day] = entry["kind"]
        out[sym] = {"expected": exp, "excluded": exc}
    return out


def fetch_times_from_ledger(facts_path=Path("ledger/facts.log")) -> dict:
    """{(symbol, day): fetch datetime} from BLIND_CACHE fact lines."""
    times: dict = {}
    if not facts_path.exists():
        return times
    with facts_path.open() as f:
        for line in f:
            m = _BLIND_RE.match(line)
            if m:
                times[(m.group(2), m.group(3))] = datetime.fromisoformat(
                    m.group(1))
    return times


def audit_day(symbol: str, day: str, frame: pd.DataFrame,
              session_set: set, raw_close_days: set) -> dict:
    """Per-day defect counts. Never mutates or filters the frame."""
    d: dict = {"rows": len(frame)}
    if list(frame.columns) != CHAIN_COLUMNS:
        d["schema_invalid"] = 1
        return d
    dup = frame.duplicated(subset=["expiration", "strike", "right"]).sum()
    if dup:
        d["duplicate_rows"] = int(dup)
    two_sided = (frame["bid"] > 0) & (frame["ask"] > 0)
    d["crossed_books"] = int((frame["bid"] > frame["ask"]).sum())
    d["one_sided_books"] = int((~two_sided).sum())
    exp = frame["expiration"].astype(str)
    bad_exp = 0
    stale_exp = 0
    holiday_exp = 0
    for e in exp.unique():
        try:
            ed = Date.fromisoformat(e)
        except ValueError:
            bad_exp += 1
            continue
        if e < day:
            stale_exp += 1
        elif (session_set and ed.weekday() < 5 and e not in session_set
                and e <= max(session_set)):
            holiday_exp += 1
    if bad_exp:
        d["unparseable_expirations"] = bad_exp
    if stale_exp:
        d["stale_expirations"] = stale_exp
    if holiday_exp:
        d["holiday_expirations"] = holiday_exp
    d["unusable_delta_two_sided"] = int(
        (two_sided & (~frame["delta"].abs().between(1e-6, 1.0))).sum())
    rights = set(frame["right"].unique())
    if "C" not in rights:
        d["missing_calls"] = 1
    if "P" not in rights:
        d["missing_puts"] = 1
    if day not in raw_close_days:
        d["missing_raw_close"] = 1
    return d


def continuity_breaks(symbol: str, sessions: list[str]) -> list[dict]:
    """Adjusted-close continuity: any |1-day return| > 50% inside the
    window is a split-registry or data defect (the four registered split
    boundaries must be seamless AFTER adjustment)."""
    from data.underlying_closes import load_closes_adjusted
    if not sessions:
        return []
    adj = load_closes_adjusted(symbol, sessions[0], sessions[-1],
                               allow_oos=True)
    rets = adj.pct_change().dropna()
    breaks = rets[rets.abs() > 0.50]
    return [{"symbol": symbol, "day": str(idx), "adjusted_return": float(r)}
            for idx, r in breaks.items()]


def run_audit(symbols=None, start=None, end=None, *, chain_dir=CHAIN_DIR,
              closes_dir=CLOSES_DIR, sessions=None, assertions=None,
              fetch_times=None, known_as_of_fn=None,
              progress=False) -> dict:
    from options_researcher.h7_earnings import (
        GATE_UNKNOWN,
        earnings_gate,
        load_assertions,
    )
    manifest = expected_manifest(symbols, start, end, sessions=sessions)
    if assertions is None:
        assertions = load_assertions()
    if fetch_times is None:
        fetch_times = fetch_times_from_ledger()
    if known_as_of_fn is None:
        def known_as_of_fn(iso):
            d = Date.fromisoformat(iso)
            return datetime(d.year, d.month, d.day, 23, 59, 59,
                            tzinfo=ZoneInfo("UTC"))

    counts = {"expected": 0, "present": 0, "missing": 0, "excluded": 0,
              "duplicate_files": 0}
    warn: dict = {}
    block: dict = {}
    missing_days: dict = {}
    contaminated: list = []
    unknown_gate: dict = {}
    file_hashes: dict = {}

    for sym, m in manifest.items():
        session_set = set(m["expected"]) | set(m["excluded"])
        counts["expected"] += len(m["expected"])
        counts["excluded"] += len(m["excluded"])
        closes_path = closes_dir / f"{sym}.parquet"
        raw_close_days = (
            set(pd.read_parquet(closes_path, columns=["date"])["date"])
            if closes_path.exists() else set())
        sym_missing = []
        for day in m["expected"]:
            path = chain_dir / f"{sym}_{day}.parquet"
            if not path.exists():
                sym_missing.append(day)
                continue
            counts["present"] += 1
            file_hashes[f"{sym}_{day}"] = sha256_file(path)
            try:
                frame = pd.read_parquet(path)
            except Exception:
                block["unreadable_files"] = block.get("unreadable_files", 0) + 1
                continue
            d = audit_day(sym, day, frame, session_set, raw_close_days)
            for key in ("schema_invalid", "duplicate_rows",
                        "missing_raw_close"):
                if d.get(key):
                    block[key] = block.get(key, 0) + d[key]
            for key in ("crossed_books", "one_sided_books",
                        "unparseable_expirations", "stale_expirations",
                        "holiday_expirations", "unusable_delta_two_sided",
                        "missing_calls", "missing_puts"):
                if d.get(key):
                    warn[key] = warn.get(key, 0) + d[key]
            # EOD fetch provenance: ledger timestamp, else file mtime
            fetched = fetch_times.get((sym, day))
            if fetched is None:
                fetched = datetime.fromtimestamp(path.stat().st_mtime,
                                                 tz=ZoneInfo("UTC"))
            fetched_ny = fetched.astimezone(NY)
            if fetched_ny.date().isoformat() == day and fetched_ny.hour < 18:
                contaminated.append({"symbol": sym, "day": day,
                                     "fetched": fetched_ny.isoformat()})
            # causal earnings coverage at the session's information cutoff
            gate, _ = earnings_gate(sym, Date.fromisoformat(day), assertions,
                                    known_as_of=known_as_of_fn(day))
            if gate == GATE_UNKNOWN:
                unknown_gate[sym] = unknown_gate.get(sym, 0) + 1
        if sym_missing:
            missing_days[sym] = sym_missing
            counts["missing"] += len(sym_missing)
        if progress:
            print(f"  {sym}: {len(m['expected'])} expected, "
                  f"{len(sym_missing)} missing, "
                  f"{len(m['excluded'])} excluded")
        # continuity runs over the FULL expected range (cheap: one series)
        breaks = continuity_breaks(sym, m["expected"])
        if breaks:
            block["adjusted_continuity_breaks"] = (
                block.get("adjusted_continuity_breaks", 0) + len(breaks))
            warn.setdefault("continuity_detail", []).extend(breaks[:10])

    if missing_days:
        block["missing_sessions"] = counts["missing"]
    if contaminated:
        block["intraday_fetch_contamination"] = len(contaminated)
    if unknown_gate:
        block["earnings_gate_unknown_sessions"] = sum(unknown_gate.values())

    report = {
        "audit_version": AUDIT_VERSION,
        "window": {"start": start or config.H7_BACKTEST_START,
                   "end": end or config.H7_BACKTEST_END},
        "symbols": list(manifest),
        "counts": counts,
        "block_findings": block,
        "warn_findings": warn,
        "missing_days": missing_days,
        "contaminated_days": contaminated,
        "earnings_unknown_by_symbol": unknown_gate,
        "exceptions_registry": list(H7_AUDIT_EXCEPTIONS),
        "verdict": "BLOCK" if block else "PASS",
    }
    report["files_hash"] = sha256_hex(canonical_json(file_hashes))
    report["file_hashes"] = file_hashes
    return report


def write_receipt(report: dict, path: Path = RECEIPT_PATH) -> str:
    """Bind the report to the code/config surfaces and persist it. Returns
    the receipt hash (over everything except the bulky per-file map, which
    is itself bound through files_hash)."""
    import subprocess
    code_sha = subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
    receipt = dict(report)
    receipt["code_sha"] = code_sha
    receipt["config_hash"] = config_hash()
    hashable = {k: v for k, v in receipt.items() if k != "file_hashes"}
    receipt["receipt_hash"] = sha256_hex(canonical_json(hashable))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=1, sort_keys=True))
    return receipt["receipt_hash"]


def verify_receipt(path: Path = RECEIPT_PATH, chain_dir=CHAIN_DIR) -> bool:
    """Recompute every bound file hash; any input mutation invalidates."""
    receipt = json.loads(path.read_text())
    hashable = {k: v for k, v in receipt.items()
                if k not in ("file_hashes", "receipt_hash")}
    if sha256_hex(canonical_json(hashable)) != receipt["receipt_hash"]:
        return False
    for key, digest in receipt["file_hashes"].items():
        p = chain_dir / f"{key}.parquet"
        if not p.exists() or sha256_file(p) != digest:
            return False
    if sha256_hex(canonical_json(receipt["file_hashes"])) != receipt["files_hash"]:
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true",
                        help="verify the committed receipt instead of auditing")
    args = parser.parse_args(argv)
    if args.verify:
        ok = verify_receipt()
        print("receipt VALID" if ok else "receipt INVALID (inputs mutated?)")
        return 0 if ok else 2
    print(f"H7 full-window data audit ({AUDIT_VERSION}) -- "
          f"{config.H7_BACKTEST_START}..{config.H7_BACKTEST_END}, "
          f"{len(config.H7_BACKTEST_SYMBOLS)} symbols")
    report = run_audit(progress=True)
    receipt_hash = write_receipt(report)
    c = report["counts"]
    print(f"expected={c['expected']} present={c['present']} "
          f"missing={c['missing']} excluded={c['excluded']}")
    print(f"block findings: {report['block_findings']}")
    print(f"warn findings: "
          f"{ {k: v for k, v in report['warn_findings'].items() if k != 'continuity_detail'} }")
    print(f"earnings-gate UNKNOWN sessions by symbol: "
          f"{report['earnings_unknown_by_symbol']}")
    print(f"VERDICT: {report['verdict']}")
    print(f"receipt: {RECEIPT_PATH} ({receipt_hash})")
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

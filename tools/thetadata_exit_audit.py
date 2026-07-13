"""Read-only, content-addressed audit for ThetaData subscription exit.

This is the forward-cache counterpart to the immutable historical manifest.
It audits every selected symbol/session after ``config.BACKTEST_END`` without
fetching data, binds the exact chain bytes and independent close files, and can
write or verify a deterministic receipt. It never authorizes H7 Stage 8.

Examples:
    uv run python tools/thetadata_exit_audit.py --scope h7 --as-of 2026-07-29
    uv run python tools/thetadata_exit_audit.py --scope h7 --as-of 2026-07-29 --write
    uv run python tools/thetadata_exit_audit.py --verify reports/thetadata_exit/2026-07-28.json
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from data.cache_runner import trading_days  # noqa: E402
from data.recent_topup import audit_chain, scope_symbols  # noqa: E402
from data.thetadata_adapter import validate_chain_schema  # noqa: E402
from data.underlying_closes import parity_spot_from_chain  # noqa: E402
from options_researcher.chains import is_monthly, third_friday  # noqa: E402
from options_researcher.h7_signals import lane_admission  # noqa: E402
from research.hashing import canonical_json, sha256_file, sha256_hex  # noqa: E402

AUDIT_VERSION = "thetadata-exit-audit/1"
DEFAULT_CHAIN_DIR = Path(".cache/chains")
DEFAULT_CLOSE_DIR = Path(".cache/underlying")
DEFAULT_FACTS_PATH = Path("ledger/facts.log")
DEFAULT_REPORTS_DIR = Path("reports/thetadata_exit")
DEFAULT_START = (date.fromisoformat(config.BACKTEST_END) + timedelta(days=1)).isoformat()
NY = ZoneInfo("America/New_York")
EOD_REPORT_READY_ET = time(17, 15)
PARITY_WARN_DRIFT = 0.005
PARITY_BLOCK_DRIFT = 0.01
QUALITY_WIDE_SPREAD = 0.20
_BLIND_RE = re.compile(
    r"^(\S+)\tBLIND_CACHE symbol=(\S+) date=(\S+) rows=\S+ sha256=(\S+)"
)
SOURCE_PATHS = (
    "config.py",
    "data/cache_runner.py",
    "data/recent_topup.py",
    "data/thetadata_adapter.py",
    "data/underlying_closes.py",
    "options_researcher/chains.py",
    "options_researcher/h7_scope.py",
    "options_researcher/h7_signals.py",
    "research/hashing.py",
    "tools/thetadata_exit_audit.py",
)


def fetch_facts(path: Path = DEFAULT_FACTS_PATH) -> dict[tuple[str, str], dict]:
    """Return the latest content-bound BLIND_CACHE fact per symbol/session."""
    out: dict[tuple[str, str], dict] = {}
    if not path.exists():
        return out
    with path.open() as handle:
        for line in handle:
            match = _BLIND_RE.match(line)
            if match:
                out[(match.group(2), match.group(3))] = {
                    "fetched": datetime.fromisoformat(match.group(1)),
                    "sha256": match.group(4),
                }
    return out


def source_identity() -> dict:
    """Bind receipts to an exact commit and exact audit/config source surface.

    Unrelated worktree paths do not change this audit's behavior and therefore
    do not invalidate its receipt. Stage 8 independently retains its broader
    clean-code/config gate.
    """
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    status = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *SOURCE_PATHS,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_paths": list(SOURCE_PATHS),
        "dirty": bool(status.stdout.strip()) or status.returncode != 0,
        "dirty_paths": sorted(line[3:] for line in status.stdout.splitlines()),
    }


def _finding(check: int | str, symbol: str, session: str, detail: str) -> dict:
    return {"check": check, "symbol": symbol, "session": session, "detail": detail}


def _raw_close(path: Path, session: str) -> float:
    frame = pd.read_parquet(path)
    if not {"date", "close"}.issubset(frame.columns):
        raise ValueError("close store missing date/close columns")
    rows = frame[frame["date"].astype(str) == session]
    if len(rows) != 1:
        raise ValueError(f"expected one close row, found {len(rows)}")
    try:
        close_values = cast(pd.Series, rows["close"])
        value = float(close_values.iloc[0])
    except (TypeError, ValueError) as exc:
        raise ValueError("close is not numeric") from exc
    if not math.isfinite(value):
        raise ValueError("close is non-finite")
    return value


def _monthly_quality(
    symbol: str, session: str, frame: pd.DataFrame, spot: float
) -> tuple[list[dict], list[dict]]:
    """Checks 2/3/7/8/14 on the exact contracts H7 can consider."""
    blocks: list[dict] = []
    warnings: list[dict] = []
    today = date.fromisoformat(session)
    parsed = pd.Series(
        pd.to_datetime(frame["expiration"], errors="coerce").dt.date,
        index=frame.index,
    )
    if parsed.isna().any():
        blocks.append(_finding(14, symbol, session, "unparseable expiration"))
        return blocks, warnings

    expiration_sessions = set(
        trading_days(min(parsed).isoformat(), max(parsed).isoformat())
    )
    non_session_expirations = sorted(
        {value.isoformat() for value in parsed if value.isoformat() not in expiration_sessions}
    )
    if non_session_expirations:
        blocks.append(
            _finding(
                14,
                symbol,
                session,
                f"weekend/holiday expirations: {non_session_expirations[:5]}",
            )
        )

    mid = (frame["bid"] + frame["ask"]) / 2.0
    dte: pd.Series = parsed.map(lambda value: (value - today).days)
    ntm = frame["strike"].between(
        (1 - config.H7_NTM_BAND) * spot,
        (1 + config.H7_NTM_BAND) * spot,
    )
    oi_ok = frame["open_interest"] >= config.MIN_OPEN_INTEREST
    monthly = parsed.map(is_monthly)

    zero_bid = ntm & monthly & dte.between(30, 120) & oi_ok & (frame["bid"] == 0) & (frame["ask"] > 0)
    if zero_bid.any():
        warnings.append(
            _finding(7, symbol, session, f"{int(zero_bid.sum())} near-money rows have zero bid")
        )
    relative_spread = (frame["ask"] - frame["bid"]) / mid.where(mid > 0)
    too_wide = ntm & monthly & dte.between(30, 120) & oi_ok & (relative_spread > QUALITY_WIDE_SPREAD)
    if too_wide.any():
        warnings.append(
            _finding(8, symbol, session, f"{int(too_wide.sum())} near-money rows exceed 20% of mid")
        )

    lane_specs: list[tuple[str, str, tuple[int, int]]] = [
        ("long-call", "C", config.H7_LONG_DTE_BAND)
    ]
    if symbol not in config.H7_CORE_LONG_ONLY:
        lane_specs.append(("short-put", "P", config.H7C_DTE_BAND))
    for lane, right, band in lane_specs:
        expected_monthlies: list[date] = []
        cursor = date(today.year, today.month, 1)
        horizon = today + timedelta(days=band[1])
        while cursor <= horizon:
            friday = third_friday(cursor.year, cursor.month)
            candidates = trading_days((friday - timedelta(days=3)).isoformat(), friday.isoformat())
            listed = date.fromisoformat(candidates[-1]) if candidates else friday
            if band[0] <= (listed - today).days <= band[1]:
                expected_monthlies.append(listed)
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)

        relevant = cast(
            pd.DataFrame,
            frame.loc[(frame["right"] == right) & monthly & dte.between(*band)],
        )
        present_monthlies = set(parsed[relevant.index])
        missing_monthlies = [value for value in expected_monthlies if value not in present_monthlies]
        if expected_monthlies and relevant.empty:
            blocks.append(
                _finding(
                    2,
                    symbol,
                    session,
                    f"no listed {lane} monthly in {band} DTE; calendar candidates "
                    f"were {[value.isoformat() for value in expected_monthlies]}",
                )
            )
        elif missing_monthlies:
            warnings.append(
                _finding(
                    2,
                    symbol,
                    session,
                    f"calendar monthlies not listed (another usable monthly exists): "
                    f"{[value.isoformat() for value in missing_monthlies]}",
                )
            )
        if not expected_monthlies:
            continue
        if relevant.empty:
            continue
        near = relevant[relevant["strike"].between(
            (1 - config.H7_NTM_BAND) * spot,
            (1 + config.H7_NTM_BAND) * spot,
        )]
        if near.empty:
            blocks.append(_finding(3, symbol, session, f"no near-money {lane} strikes"))
            continue
        admitted, count = lane_admission(
            frame, spot=spot, today=today, dte_band=band, right=right
        )
        if not admitted:
            warnings.append(
                _finding(
                    "H7_ADMISSION",
                    symbol,
                    session,
                    f"{lane} has {count}/{config.H7_ADMIT_MIN_CONTRACTS} liquid NTM contracts",
                )
            )
    return blocks, warnings


def audit_symbol_session(
    symbol: str,
    session: str,
    *,
    chain_dir: Path,
    close_dir: Path,
    facts: dict[tuple[str, str], dict],
) -> dict:
    """Run all fourteen data-audit checks for one symbol/session."""
    chain_path = chain_dir / f"{symbol}_{session}.parquet"
    close_path = close_dir / f"{symbol}.parquet"
    blocks: list[dict] = []
    warnings: list[dict] = []
    hashes: dict[str, str] = {}

    if not chain_path.exists():
        blocks.append(_finding(1, symbol, session, "chain file missing"))
        return {"blocks": blocks, "warnings": warnings, "hashes": hashes}
    if not close_path.exists():
        blocks.append(_finding(13, symbol, session, "independent close file missing"))
        return {"blocks": blocks, "warnings": warnings, "hashes": hashes}

    hashes[str(chain_path)] = sha256_file(chain_path)
    hashes[str(close_path)] = sha256_file(close_path)
    try:
        frame = pd.read_parquet(chain_path)
        validate_chain_schema(frame)
        if frame.empty:
            raise ValueError("chain is empty")
        spot = _raw_close(close_path, session)
    except Exception as exc:
        blocks.append(
            _finding("SCHEMA", symbol, session, f"{type(exc).__name__}: {exc}")
        )
        return {"blocks": blocks, "warnings": warnings, "hashes": hashes}

    duplicated = int(frame.duplicated(["expiration", "strike", "right"]).sum())
    if duplicated:
        blocks.append(_finding(12, symbol, session, f"{duplicated} duplicate contracts"))
    negative = int(((frame["bid"] < 0) | (frame["ask"] < 0) | (frame["open_interest"] < 0)).sum())
    if negative:
        blocks.append(_finding(5, symbol, session, f"{negative} rows have negative bid/ask/OI"))
    crossed = int((frame["bid"] > frame["ask"]).sum())
    if crossed:
        blocks.append(_finding(6, symbol, session, f"{crossed} crossed markets"))

    base = audit_chain(frame)
    for detail in base["block"]:
        blocks.append(_finding("10/11", symbol, session, detail))
    for detail in base["warn"]:
        warnings.append(_finding("10/11", symbol, session, detail))

    monthly_blocks, monthly_warnings = _monthly_quality(symbol, session, frame, spot)
    blocks.extend(monthly_blocks)
    warnings.extend(monthly_warnings)

    parity = parity_spot_from_chain(frame, session)
    if pd.isna(parity):
        blocks.append(_finding(13, symbol, session, "put-call parity spot unavailable"))
    else:
        drift = abs(float(parity) / spot - 1.0)
        detail = f"parity={parity:.6f} close={spot:.6f} drift={drift:.4%}"
        if drift > PARITY_BLOCK_DRIFT:
            blocks.append(_finding(13, symbol, session, detail))
        elif drift > PARITY_WARN_DRIFT:
            warnings.append(_finding(13, symbol, session, detail))

    fact = facts.get((symbol, session))
    if fact is None:
        blocks.append(_finding(9, symbol, session, "missing BLIND_CACHE provenance fact"))
    else:
        if fact["sha256"] != hashes[str(chain_path)]:
            blocks.append(_finding(9, symbol, session, "BLIND_CACHE sha256 mismatch"))
        fetched = fact["fetched"].astimezone(NY)
        ready = datetime.combine(date.fromisoformat(session), EOD_REPORT_READY_ET, tzinfo=NY)
        if fetched < ready:
            blocks.append(
                _finding(9, symbol, session, f"fetched before EOD report ready: {fetched.isoformat()}")
            )

    return {"blocks": blocks, "warnings": warnings, "hashes": hashes}


def run_audit(
    *,
    symbols: list[str],
    start: str,
    end: str,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    close_dir: Path = DEFAULT_CLOSE_DIR,
    facts: dict[tuple[str, str], dict] | None = None,
    sessions: list[str] | None = None,
    identity: dict | None = None,
) -> dict:
    """Audit a complete forward window. No fetch or store function is called."""
    sessions = list(sessions) if sessions is not None else trading_days(start, end)
    facts = fetch_facts() if facts is None else facts
    identity = source_identity() if identity is None else identity
    blocks: list[dict] = []
    warnings: list[dict] = []
    hashes: dict[str, str] = {}

    for session in sessions:
        for symbol in symbols:
            result = audit_symbol_session(
                symbol,
                session,
                chain_dir=Path(chain_dir),
                close_dir=Path(close_dir),
                facts=facts,
            )
            blocks.extend(result["blocks"])
            warnings.extend(result["warnings"])
            hashes.update(result["hashes"])

    if identity.get("dirty"):
        blocks.append(
            _finding(
                "IDENTITY",
                "REPO",
                end,
                f"dirty code/config identity: {identity.get('dirty_paths', [])}",
            )
        )
    verdict = "BLOCK" if blocks else ("PASS WITH WARNINGS" if warnings else "PASS")
    report = {
        "audit_version": AUDIT_VERSION,
        "scope": symbols,
        "window": {"start": start, "end": end},
        "sessions": sessions,
        "source_identity": identity,
        "counts": {
            "symbols": len(symbols),
            "sessions": len(sessions),
            "expected_symbol_sessions": len(symbols) * len(sessions),
            "blocks": len(blocks),
            "warnings": len(warnings),
        },
        "blocks": blocks,
        "warnings": warnings,
        "file_hashes": dict(sorted(hashes.items())),
        "verdict": verdict,
    }
    report["file_hashes_hash"] = sha256_hex(canonical_json(report["file_hashes"]))
    hashable = {key: value for key, value in report.items() if key != "file_hashes"}
    report["receipt_hash"] = sha256_hex(canonical_json(hashable))
    return report


def write_receipt(report: dict, reports_dir: Path = DEFAULT_REPORTS_DIR) -> Path:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{report['window']['end']}.json"
    payload = json.dumps(report, indent=1, sort_keys=True) + "\n"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload)
    os.replace(tmp, path)
    return path


def verify_receipt(
    path: Path,
    *,
    chain_dir=DEFAULT_CHAIN_DIR,
    close_dir=DEFAULT_CLOSE_DIR,
    facts: dict[tuple[str, str], dict] | None = None,
    sessions: list[str] | None = None,
    identity: dict | None = None,
) -> tuple[bool, list[str]]:
    expected = json.loads(Path(path).read_text())
    actual = run_audit(
        symbols=list(expected["scope"]),
        start=expected["window"]["start"],
        end=expected["window"]["end"],
        chain_dir=Path(chain_dir),
        close_dir=Path(close_dir),
        facts=facts,
        sessions=sessions,
        identity=identity,
    )
    failures = [
        key
        for key in sorted(set(expected) | set(actual))
        if canonical_json(expected.get(key)) != canonical_json(actual.get(key))
    ]
    return not failures, failures


def _last_completed_session(as_of: str) -> str:
    requested = date.fromisoformat(as_of)
    prior = [day for day in trading_days(DEFAULT_START, as_of) if day < requested.isoformat()]
    if not prior:
        raise ValueError(f"no completed XNYS session before {as_of}")
    return prior[-1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(__doc__ or "ThetaData exit audit").splitlines()[0]
    )
    parser.add_argument("--scope", choices=("core", "h7"), default="h7")
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--chain-dir", default=str(DEFAULT_CHAIN_DIR))
    parser.add_argument("--close-dir", default=str(DEFAULT_CLOSE_DIR))
    parser.add_argument("--reports-dir", default=str(DEFAULT_REPORTS_DIR))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.verify:
            ok, failures = verify_receipt(
                args.verify, chain_dir=Path(args.chain_dir), close_dir=Path(args.close_dir)
            )
            print("receipt VALID" if ok else f"receipt INVALID: {failures}")
            return 0 if ok else 2
        end = _last_completed_session(args.as_of)
        report = run_audit(
            symbols=scope_symbols(args.scope),
            start=args.start,
            end=end,
            chain_dir=Path(args.chain_dir),
            close_dir=Path(args.close_dir),
        )
    except (OSError, ValueError) as exc:
        print(f"THETADATA EXIT AUDIT ERROR -- {type(exc).__name__}: {exc}")
        return 2

    counts = report["counts"]
    print(
        f"ThetaData exit audit {report['window']['start']}..{end} "
        f"symbols={counts['symbols']} sessions={counts['sessions']} "
        f"blocks={counts['blocks']} warnings={counts['warnings']}"
    )
    for finding in report["blocks"][:20]:
        print(f"  BLOCK check {finding['check']} {finding['symbol']} {finding['session']}: {finding['detail']}")
    for finding in report["warnings"][:20]:
        print(f"  WARN check {finding['check']} {finding['symbol']} {finding['session']}: {finding['detail']}")
    print(f"VERDICT: {report['verdict']}")
    if args.write:
        if report["verdict"] == "BLOCK":
            print("receipt not written: BLOCK verdict")
        else:
            print(f"receipt: {write_receipt(report, Path(args.reports_dir))}")
    return 2 if report["verdict"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())

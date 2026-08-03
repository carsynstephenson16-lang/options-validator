"""Read-only full audit of the parked future-ticker EOD-chain capture.

The capture is deliberately non-canonical. This tool verifies every expected
partition and receipt, runs every content check supported by the stored bytes,
and records unavailable checks as blockers rather than promoting incomplete
evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.atomic_io import atomic_text_write  # noqa: E402
from data.cache_schema import CHAIN_COLUMNS_V1, CHAIN_V2_CAPTURE_FIELDS  # noqa: E402
from data.recent_topup import audit_chain  # noqa: E402
from research.hashing import canonical_json, sha256_file, sha256_hex  # noqa: E402
from tools import thetadata_exit_audit as base_audit  # noqa: E402

AUDIT_SCHEMA = "future-ticker-full-data-audit/v1"
CAPTURE_SCHEMA = "future_ticker_eod_capture_summary_v1"
PARTITION_SCHEMA = "future_ticker_eod_capture_v1"
SOURCE_PATHS = (
    "data/cache_schema.py",
    "data/recent_topup.py",
    "tools/future_ticker_data_audit.py",
    "tools/thetadata_exit_audit.py",
)


def _finding(check: int | str, symbol: str, session: str, detail: str) -> dict:
    return {"check": check, "symbol": symbol, "session": session, "detail": detail}


def _source_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    hashes = {relative: sha256_file(root / relative) for relative in SOURCE_PATHS}
    return {
        "source_paths": list(SOURCE_PATHS),
        "source_hashes": hashes,
        "source_hashes_hash": sha256_hex(canonical_json(hashes)),
        "dirty": bool(status),
        "dirty_paths": sorted(line[3:] for line in status.splitlines()),
    }


def _load_json(path: Path) -> dict:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("JSON root is not an object")
    return value


def run_audit(
    capture_dir: Path,
    close_dir: Path,
    *,
    symbols: list[str] | None = None,
    sessions: list[str] | None = None,
    identity: dict | None = None,
) -> dict:
    capture_dir = Path(capture_dir).resolve()
    close_dir = Path(close_dir).resolve()
    summary_path = capture_dir / "capture_summary.json"
    blocks: list[dict] = []
    warnings: list[dict] = []
    try:
        summary = _load_json(summary_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        summary = {}
        blocks.append(_finding("PROVENANCE", "ALL", "ALL", f"capture summary unreadable: {exc}"))

    chosen_symbols = list(symbols if symbols is not None else summary.get("symbols", []))
    if sessions is None:
        from data.cache_runner import trading_days

        start = str(summary.get("start_session", ""))
        end = str(summary.get("end_session", ""))
        chosen_sessions = trading_days(start, end) if start and end else []
    else:
        chosen_sessions = list(sessions)
    end_session = chosen_sessions[-1] if chosen_sessions else "ALL"

    if summary.get("schema") != CAPTURE_SCHEMA:
        blocks.append(_finding("PROVENANCE", "ALL", end_session, "capture summary schema mismatch"))
    storage = summary.get("storage", {})
    if not (
        isinstance(storage, dict)
        and storage.get("canonical_chain_cache_touched") is False
        and storage.get("parked_display_only") is True
        and storage.get("verdict_eligible") is False
    ):
        blocks.append(_finding("SCOPE", "ALL", end_session, "parked-storage boundary invalid"))
    capture_source = summary.get("source", {})
    if not isinstance(capture_source, dict) or capture_source.get("worktree_dirty") is not False:
        blocks.append(
            _finding(
                "PROVENANCE",
                "ALL",
                end_session,
                "capture was produced from a dirty worktree",
            )
        )
    if summary.get("errors") or summary.get("results", {}).get("errors") not in {0, None}:
        blocks.append(_finding(1, "ALL", end_session, "capture summary contains errors"))

    source_identity = _source_identity() if identity is None else identity
    if source_identity.get("dirty"):
        blocks.append(
            _finding(
                "IDENTITY",
                "ALL",
                end_session,
                f"audit source is dirty: {source_identity.get('dirty_paths', [])}",
            )
        )

    expected = {(symbol, session) for symbol in chosen_symbols for session in chosen_sessions}
    actual = {
        (path.parents[1].name, path.parent.name)
        for path in (capture_dir / "raw").glob("*/*/chain.parquet")
    }
    for symbol, session in sorted(expected - actual):
        blocks.append(_finding(1, symbol, session, "expected chain partition missing"))
    for symbol, session in sorted(actual - expected):
        blocks.append(_finding(1, symbol, session, "unexpected chain partition"))

    file_hashes: dict[str, str] = {}
    hash_verified = 0
    row_count = 0
    schema_v1 = 0
    schema_v2 = 0
    closes_missing_reported: set[str] = set()
    for symbol, session in sorted(expected & actual):
        partition_dir = capture_dir / "raw" / symbol / session
        chain_path = partition_dir / "chain.parquet"
        receipt_path = partition_dir / "receipt.json"
        digest = sha256_file(chain_path)
        file_hashes[str(chain_path)] = digest
        try:
            receipt = _load_json(receipt_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            receipt = {}
            blocks.append(_finding(1, symbol, session, f"partition receipt unreadable: {exc}"))
        receipt_valid = (
            receipt.get("schema") == PARTITION_SCHEMA
            and receipt.get("status") in {"CAPTURED", "EXISTING"}
            and receipt.get("symbol") == symbol
            and receipt.get("session") == session
            and receipt.get("parked_display_only") is True
            and receipt.get("verdict_eligible") is False
            and receipt.get("parquet", {}).get("sha256") == digest
        )
        if not receipt_valid:
            blocks.append(_finding(1, symbol, session, "partition receipt/hash mismatch"))
        else:
            hash_verified += 1
        try:
            frame = pd.read_parquet(chain_path)
        except (OSError, ValueError) as exc:
            blocks.append(_finding(1, symbol, session, f"partition unreadable: {exc}"))
            continue
        row_count += len(frame)
        if receipt.get("rows") != len(frame):
            blocks.append(_finding(1, symbol, session, "receipt row count mismatch"))
        missing_v1 = [column for column in CHAIN_COLUMNS_V1 if column not in frame.columns]
        if missing_v1:
            blocks.append(_finding("SCHEMA", symbol, session, f"missing columns: {missing_v1}"))
            continue
        if all(column in frame.columns for column in CHAIN_V2_CAPTURE_FIELDS):
            schema_v2 += 1
        else:
            schema_v1 += 1
        if frame.empty:
            blocks.append(_finding(1, symbol, session, "chain partition is empty"))
            continue
        duplicate = int(frame.duplicated(["expiration", "strike", "right"]).sum())
        if duplicate:
            blocks.append(_finding(12, symbol, session, f"{duplicate} duplicate contracts"))
        missing_quotes = int(frame[["bid", "ask"]].isna().any(axis=1).sum())
        if missing_quotes:
            blocks.append(_finding(4, symbol, session, f"{missing_quotes} missing bid/ask rows"))
        negative = int(
            ((frame["bid"] < 0) | (frame["ask"] < 0) | (frame["open_interest"] < 0)).sum()
        )
        if negative:
            blocks.append(_finding(5, symbol, session, f"{negative} negative bid/ask/OI rows"))
        crossed = int((frame["bid"] > frame["ask"]).sum())
        if crossed:
            blocks.append(_finding(6, symbol, session, f"{crossed} crossed markets"))
        parsed_expiration = pd.to_datetime(frame["expiration"], errors="coerce")
        if parsed_expiration.isna().any():
            blocks.append(_finding(14, symbol, session, "unparseable expiration"))
        rights = set(frame["right"].dropna().astype(str))
        if not rights.issubset({"C", "P"}) or not {"C", "P"}.issubset(rights):
            blocks.append(_finding(14, symbol, session, f"invalid or incomplete rights: {rights}"))
        content = audit_chain(frame)
        for detail in content["block"]:
            blocks.append(_finding("10/11", symbol, session, detail))
        for detail in content["warn"]:
            warnings.append(_finding("10/11", symbol, session, detail))

        close_path = close_dir / f"{symbol}.parquet"
        if not close_path.is_file():
            if symbol not in closes_missing_reported:
                blocks.append(_finding(13, symbol, session, "independent close file missing"))
                closes_missing_reported.add(symbol)
            continue
        try:
            spot = base_audit._raw_close(close_path, session)
        except (KeyError, OSError, TypeError, ValueError) as exc:
            blocks.append(_finding(13, symbol, session, f"independent close unavailable: {exc}"))
            continue
        monthly_blocks, monthly_warnings = base_audit._monthly_quality(symbol, session, frame, spot)
        blocks.extend(monthly_blocks)
        warnings.extend(monthly_warnings)
        parity = base_audit.parity_spot_from_chain(frame, session)
        if pd.isna(parity):
            warnings.append(_finding(13, symbol, session, "diagnostic put-call parity unavailable"))
        else:
            drift = abs(float(parity) / spot - 1.0)
            if drift > base_audit.PARITY_WARN_DRIFT:
                warnings.append(
                    _finding(
                        13,
                        symbol,
                        session,
                        f"diagnostic parity drift={drift:.4%}; rates/dividends not modeled",
                    )
                )

    if schema_v1:
        blocks.append(
            _finding(
                9,
                "ALL",
                end_session,
                f"{schema_v1} partitions are schema v1 and retain no provider timestamps",
            )
        )
    # The capture retained normalized joins and per-partition receipts, not
    # the two raw provider response frames, so join/drop behavior cannot be
    # independently replayed even when all normalized hashes match.
    blocks.append(
        _finding(
            "PROVENANCE",
            "ALL",
            end_session,
            "raw Greeks and open-interest response frames were not retained for replay",
        )
    )
    verdict = "BLOCK" if blocks else ("PASS WITH WARNINGS" if warnings else "PASS")
    report = {
        "schema": AUDIT_SCHEMA,
        "capture_namespace": str(capture_dir),
        "independent_close_namespace": str(close_dir),
        "symbols": chosen_symbols,
        "sessions": chosen_sessions,
        "capture_summary_sha256": sha256_file(summary_path) if summary_path.is_file() else None,
        "source_identity": source_identity,
        "counts": {
            "expected_partitions": len(expected),
            "present_partitions": len(expected & actual),
            "hash_verified_partitions": hash_verified,
            "rows": row_count,
            "schema_v1_partitions": schema_v1,
            "schema_v2_partitions": schema_v2,
            "blocks": len(blocks),
            "warnings": len(warnings),
        },
        "file_hashes": dict(sorted(file_hashes.items())),
        "file_hashes_hash": sha256_hex(canonical_json(dict(sorted(file_hashes.items())))),
        "blocks": blocks,
        "warnings": warnings,
        "verdict": verdict,
        "promotion_eligible": False,
    }
    report["receipt_hash"] = sha256_hex(canonical_json(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--close-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_audit(args.capture_dir, args.close_dir)
    atomic_text_write(json.dumps(report, sort_keys=True, indent=2) + "\n", args.report)
    print(
        f"future-ticker audit: {report['verdict']} "
        f"partitions={report['counts']['present_partitions']} "
        f"blocks={len(report['blocks'])} warnings={len(report['warnings'])}"
    )
    return 0 if report["verdict"] != "BLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())

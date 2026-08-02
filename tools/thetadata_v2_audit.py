"""Read-only, full fourteen-check audit for the OD-1 schema-v2 namespace."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import cast
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.atomic_io import atomic_text_write  # noqa: E402
from data.cache_runner import trading_days  # noqa: E402
from research.hashing import canonical_json, sha256_file, sha256_hex  # noqa: E402
from tools import thetadata_exit_audit as base_audit  # noqa: E402
from tools.thetadata_v2_backfill import (  # noqa: E402
    END_SESSION,
    EXPECTED_SESSIONS,
    SCOPE_ID,
    START_SESSION,
    SYMBOLS,
    _attestation_path,
    _raw_path,
)

AUDIT_SCHEMA = "thetadata-v2-full-audit/v1"
DEFAULT_QUARANTINE_PATH = Path("data/v2_partition_quarantine.json")
NY = ZoneInfo("America/New_York")
SOURCE_PATHS = (
    *base_audit.SOURCE_PATHS,
    "data/atomic_io.py",
    "data/cache_schema.py",
    "data/v2_partition_quarantine.json",
    "options_researcher/h7_data_gate.py",
    "options_researcher/h7_synthetic_proof.py",
    "options_researcher/h9_census.py",
    "tools/thetadata_v2_audit.py",
    "tools/thetadata_v2_backfill.py",
)


def _load_quarantines(
    output_dir: Path,
    sessions: list[str],
    quarantine_path: Path,
) -> tuple[dict[tuple[str, str], dict], list[dict]]:
    """Validate exact-byte partitions excluded from every verdict path."""
    blocks: list[dict] = []
    quarantine_path = Path(quarantine_path)
    if not quarantine_path.is_file():
        return {}, [
            {
                "check": "QUARANTINE",
                "symbol": "ALL",
                "session": END_SESSION,
                "detail": f"quarantine registry missing: {quarantine_path}",
            }
        ]
    try:
        payload = json.loads(quarantine_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [
            {
                "check": "QUARANTINE",
                "symbol": "ALL",
                "session": END_SESSION,
                "detail": f"{type(exc).__name__}: {exc}",
            }
        ]
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != "v2-partition-quarantine/v1"
        or payload.get("scope_id") != SCOPE_ID
        or not isinstance(payload.get("entries"), list)
    ):
        return {}, [
            {
                "check": "QUARANTINE",
                "symbol": "ALL",
                "session": END_SESSION,
                "detail": "invalid quarantine registry schema, scope, or entries",
            }
        ]

    selected = {(symbol, session) for symbol in SYMBOLS for session in sessions}
    quarantines: dict[tuple[str, str], dict] = {}
    for index, entry in enumerate(payload["entries"]):
        if not isinstance(entry, dict):
            blocks.append(
                {
                    "check": "QUARANTINE",
                    "symbol": "ALL",
                    "session": END_SESSION,
                    "detail": f"entry {index} is not an object",
                }
            )
            continue
        symbol = entry.get("symbol")
        session = entry.get("session")
        key = (symbol, session)
        if key not in selected:
            continue
        digest = entry.get("sha256")
        size = entry.get("size")
        checks = entry.get("checks")
        reason = entry.get("reason")
        problems = []
        if key in quarantines:
            problems.append("duplicate symbol/session")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            problems.append("invalid sha256")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            problems.append("invalid size")
        if not isinstance(checks, list) or not checks:
            problems.append("checks must be a non-empty list")
        if not isinstance(reason, str) or not reason.strip():
            problems.append("reason must be non-empty")
        path = output_dir / f"{symbol}_{session}.parquet"
        if not path.is_file():
            problems.append("partition missing")
        elif isinstance(size, int) and path.stat().st_size != size:
            problems.append("size mismatch")
        elif isinstance(digest, str) and sha256_file(path) != digest:
            problems.append("sha256 mismatch")
        if problems:
            blocks.append(
                {
                    "check": "QUARANTINE",
                    "symbol": symbol,
                    "session": session,
                    "detail": f"entry {index}: {', '.join(problems)}",
                }
            )
            continue
        quarantines[key] = {
            "symbol": symbol,
            "session": session,
            "sha256": digest,
            "size": size,
            "checks": checks,
            "reason": reason.strip(),
        }
    return dict(sorted(quarantines.items())), blocks


def _source_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.run(
        ("git", "log", "-1", "--format=%H", "--", *SOURCE_PATHS),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all", "--", *SOURCE_PATHS),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source_hashes = {relative: sha256_file(root / relative) for relative in SOURCE_PATHS}
    return {
        "git_source_commit": source_commit,
        "source_paths": list(SOURCE_PATHS),
        "source_hashes": source_hashes,
        "source_hashes_hash": sha256_hex(canonical_json(source_hashes)),
        "dirty": bool(status),
        "dirty_paths": sorted(line[3:] for line in status.splitlines()),
    }


def _load_provenance(
    output_dir: Path, sessions: list[str]
) -> tuple[dict[tuple[str, str], dict], dict[str, str], list[dict]]:
    facts: dict[tuple[str, str], dict] = {}
    raw_hashes: dict[str, str] = {}
    blocks: list[dict] = []
    for session in sessions:
        for symbol in SYMBOLS:
            attestation_path = _attestation_path(output_dir, symbol, session)
            if not attestation_path.is_file():
                blocks.append(
                    {
                        "check": "PROVENANCE",
                        "symbol": symbol,
                        "session": session,
                        "detail": "complete schema-v2 attestation missing",
                    }
                )
                continue
            try:
                item = json.loads(attestation_path.read_text())
                if item.get("status") != "COMPLETE" or item.get("scope_id") != SCOPE_ID:
                    raise ValueError("attestation status/scope mismatch")
                facts[(symbol, session)] = {
                    "fetched": datetime.fromisoformat(item["captured_at_utc"]),
                    "sha256": item["sha256"],
                }
                for name, endpoint in (
                    ("raw_greeks_eod", "greeks_eod"),
                    ("raw_open_interest", "open_interest"),
                ):
                    path = _raw_path(output_dir, endpoint, symbol, session)
                    declared = item["artifacts"][name]
                    digest = sha256_file(path)
                    if declared["sha256"] != digest:
                        raise ValueError(f"{name} hash mismatch")
                    raw_hashes[str(path)] = digest
            except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                blocks.append(
                    {
                        "check": "PROVENANCE",
                        "symbol": symbol,
                        "session": session,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
    return facts, dict(sorted(raw_hashes.items())), blocks


def _v2_specific_checks(
    output_dir: Path, close_dir: Path, sessions: list[str]
) -> tuple[list[dict], list[dict]]:
    """Checks v2 timestamps, provider spot parity, and any raw volume field."""
    blocks: list[dict] = []
    warnings: list[dict] = []
    volume_seen = False
    for session in sessions:
        for symbol in SYMBOLS:
            chain_path = output_dir / f"{symbol}_{session}.parquet"
            close_path = close_dir / f"{symbol}.parquet"
            raw_path = _raw_path(output_dir, "greeks_eod", symbol, session)
            if not chain_path.is_file():
                continue
            try:
                frame = pd.read_parquet(
                    chain_path,
                    columns=[
                        "bid",
                        "ask",
                        "timestamp",
                        "underlying_timestamp",
                        "underlying_price",
                    ],
                )
                missing_mask = cast(pd.Series, frame[["bid", "ask"]].isna().any(axis=1))
                missing_quotes = int(missing_mask.sum())
                if missing_quotes:
                    blocks.append(
                        {
                            "check": 4,
                            "symbol": symbol,
                            "session": session,
                            "detail": f"{missing_quotes} rows have missing bid or ask",
                        }
                    )
                option_times = pd.to_datetime(frame["timestamp"], utc=True).dt.tz_convert(NY)
                underlying_times = pd.to_datetime(
                    frame["underlying_timestamp"], utc=True
                ).dt.tz_convert(NY)
                if not option_times.dt.date.astype(str).eq(session).all():
                    blocks.append(
                        {
                            "check": 9,
                            "symbol": symbol,
                            "session": session,
                            "detail": "option last-trade timestamp falls outside session date",
                        }
                    )
                # The bulk EOD-Greeks endpoint is generated at 17:15 ET, but
                # its ``timestamp`` field is the last option-trade time (and
                # may be 00:00 for a contract with no trade), not the report's
                # creation time.  ThetaData's legacy schema exposes no
                # creation timestamp here.  Reject only an impossible value
                # after the report-generation window.
                option_minutes = option_times.dt.hour * 60 + option_times.dt.minute
                if (option_minutes > 17 * 60 + 30).any():
                    blocks.append(
                        {
                            "check": 9,
                            "symbol": symbol,
                            "session": session,
                            "detail": "option last-trade timestamp is after 17:30 ET",
                        }
                    )
                if not underlying_times.dt.date.astype(str).eq(session).all():
                    blocks.append(
                        {
                            "check": 9,
                            "symbol": symbol,
                            "session": session,
                            "detail": "underlying timestamp falls outside session date",
                        }
                    )
                if close_path.is_file():
                    close = base_audit._raw_close(close_path, session)
                    provider_spot = float(frame["underlying_price"].median())
                    drift = abs(provider_spot / close - 1.0)
                    if drift > 0.005:
                        blocks.append(
                            {
                                "check": 13,
                                "symbol": symbol,
                                "session": session,
                                "detail": (
                                    f"provider underlying={provider_spot:.6f} independent "
                                    f"close={close:.6f} drift={drift:.4%}"
                                ),
                            }
                        )
                if raw_path.is_file():
                    raw = pd.read_parquet(raw_path)
                    volume_columns = [
                        name
                        for name in raw.columns
                        if str(name).lower() in {"volume", "trade_volume"}
                    ]
                    for column in volume_columns:
                        volume_seen = True
                        volume = cast(pd.Series, pd.to_numeric(raw[column], errors="coerce"))
                        negative = int(cast(pd.Series, volume < 0).sum())
                        if negative:
                            blocks.append(
                                {
                                    "check": 5,
                                    "symbol": symbol,
                                    "session": session,
                                    "detail": f"{negative} raw rows have negative {column}",
                                }
                            )
            except (KeyError, OSError, TypeError, ValueError) as exc:
                blocks.append(
                    {
                        "check": "V2_SPECIFIC",
                        "symbol": symbol,
                        "session": session,
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
    if not volume_seen:
        warnings.append(
            {
                "check": 5,
                "symbol": "ALL",
                "session": END_SESSION,
                "detail": "selected EOD Greeks endpoint exposed no volume field; volume check unavailable",
            }
        )
    return blocks, warnings


def run_full_audit(
    output_dir: Path,
    close_dir: Path,
    *,
    identity: dict | None = None,
    quarantine_path: Path = DEFAULT_QUARANTINE_PATH,
) -> dict:
    sessions = trading_days(START_SESSION, END_SESSION)
    if len(sessions) != EXPECTED_SESSIONS:
        raise ValueError(
            f"calendar drift: expected {EXPECTED_SESSIONS} sessions, found {len(sessions)}"
        )
    facts, raw_hashes, provenance_blocks = _load_provenance(output_dir, sessions)
    v2_blocks, v2_warnings = _v2_specific_checks(output_dir, close_dir, sessions)
    quarantines, quarantine_blocks = _load_quarantines(
        output_dir,
        sessions,
        quarantine_path,
    )
    base = base_audit.run_audit(
        symbols=list(SYMBOLS),
        start=START_SESSION,
        end=END_SESSION,
        chain_dir=output_dir,
        close_dir=close_dir,
        facts=facts,
        sessions=sessions,
        identity=_source_identity() if identity is None else identity,
        parity_mode="diagnostic",
    )
    effective_base_blocks = []
    quarantined_findings = []
    for finding in base["blocks"]:
        entry = quarantines.get((finding.get("symbol"), finding.get("session")))
        if entry is not None and finding.get("check") in entry["checks"]:
            quarantined_findings.append({**finding, "quarantine_reason": entry["reason"]})
        else:
            effective_base_blocks.append(finding)
    quarantine_warnings = [
        {
            "check": "QUARANTINE",
            "symbol": entry["symbol"],
            "session": entry["session"],
            "detail": f"partition excluded from verdict use: {entry['reason']}",
        }
        for entry in quarantines.values()
    ]
    blocks = [
        *provenance_blocks,
        *v2_blocks,
        *quarantine_blocks,
        *effective_base_blocks,
    ]
    warnings = [*v2_warnings, *base["warnings"], *quarantine_warnings]
    verdict = "BLOCK" if blocks else ("PASS WITH WARNINGS" if warnings else "PASS")
    report = {
        "schema": AUDIT_SCHEMA,
        "scope_id": SCOPE_ID,
        "output_namespace": str(output_dir.resolve()),
        "independent_close_namespace": str(close_dir.resolve()),
        "symbols": list(SYMBOLS),
        "window": {"start": START_SESSION, "end": END_SESSION},
        "sessions": sessions,
        "base_fourteen_check_audit": base,
        "quarantine_path": str(Path(quarantine_path)),
        "quarantine_sha256": (
            sha256_file(Path(quarantine_path)) if Path(quarantine_path).is_file() else None
        ),
        "quarantined_partitions": list(quarantines.values()),
        "quarantined_findings": quarantined_findings,
        "raw_file_hashes": raw_hashes,
        "raw_file_hashes_hash": sha256_hex(canonical_json(raw_hashes)),
        "blocks": blocks,
        "warnings": warnings,
        "verdict": verdict,
    }
    report["receipt_hash"] = sha256_hex(canonical_json(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--close-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run_full_audit(args.output_dir.resolve(), args.close_dir.resolve())
    atomic_text_write(json.dumps(report, sort_keys=True, indent=2) + "\n", args.report)
    print(
        f"OD1 v2 audit: {report['verdict']} "
        f"blocks={len(report['blocks'])} warnings={len(report['warnings'])}"
    )
    return 0 if report["verdict"] != "BLOCK" else 2


if __name__ == "__main__":
    raise SystemExit(main())

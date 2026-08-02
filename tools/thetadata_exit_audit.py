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
import contextlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, cast
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from data.cache_provenance import load_blind_cache_facts  # noqa: E402
from data.cache_runner import trading_days  # noqa: E402
from data.recent_topup import audit_chain, scope_symbols  # noqa: E402
from data.thetadata_adapter import validate_chain_schema  # noqa: E402
from data.underlying_closes import parity_spot_from_chain  # noqa: E402
from options_researcher.chains import is_monthly, third_friday  # noqa: E402
from options_researcher.h7_signals import lane_admission  # noqa: E402
from research.hashing import canonical_json, sha256_file, sha256_hex  # noqa: E402
from tools.cache_manifest import verify_manifest  # noqa: E402

AUDIT_VERSION = "thetadata-exit-audit/1"
READINESS_VERSION = "thetadata-offline-intelligence-readiness/1"
FLOW_READINESS_VERSION = "options-flow-readiness/1"
DEFAULT_CHAIN_DIR = Path(".cache/chains")
DEFAULT_CLOSE_DIR = Path(".cache/underlying")
DEFAULT_FACTS_PATH = Path("ledger/facts.log")
DEFAULT_REPORTS_DIR = Path("reports/thetadata_exit")
DEFAULT_MANIFEST_PATH = Path("data/chain_cache_manifest.txt")
DEFAULT_CLASSIFICATION_PATH = Path("data/cache_file_classifications.json")
DEFAULT_FLOW_DIR = Path(".cache/options_flow")
DEFAULT_FLOW_REPORTS_DIR = Path("reports/options_flow")
DEFAULT_START = (date.fromisoformat(config.BACKTEST_END) + timedelta(days=1)).isoformat()
NY = ZoneInfo("America/New_York")
EOD_REPORT_READY_ET = time(17, 15)
PARITY_WARN_DRIFT = 0.005
PARITY_BLOCK_DRIFT = 0.01
QUALITY_WIDE_SPREAD = 0.20
REQUIRED_EOD_FIELDS = (
    "expiration",
    "strike",
    "right",
    "bid",
    "ask",
    "open_interest",
    "iv",
    "delta",
    "gamma",
    "theta",
    "vega",
)
CACHE_FILE_RE = re.compile(r"^(?P<symbol>[A-Z0-9.-]+)_(?P<session>\d{4}-\d{2}-\d{2})\.parquet$")
SOURCE_PATHS = (
    "config.py",
    "data/cache_provenance.py",
    "data/cache_runner.py",
    "data/cache_file_classifications.json",
    "data/recent_topup.py",
    "data/thetadata_adapter.py",
    "data/underlying_closes.py",
    "options_researcher/chains.py",
    "options_researcher/h7_scope.py",
    "options_researcher/h7_signals.py",
    "research/hashing.py",
    "tools/thetadata_exit_audit.py",
)
READINESS_SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            *SOURCE_PATHS,
            "data/options_flow/audit.py",
            "data/pandas_feed.py",
            "data/provider_policy.py",
            "data/schwab_adapter.py",
            "options_researcher/entry_watch.py",
            "options_researcher/features.py",
            "options_researcher/h6_watch.py",
            "options_researcher/h7_data_gate.py",
            "options_researcher/h8_watch.py",
            "options_researcher/studies/long_call_carry.py",
            "tools/cache_manifest.py",
            "tools/options_flow_audit.py",
        )
    )
)

CONSUMER_MAP = (
    {
        "consumer": "H5",
        "path": "options_researcher/entry_watch.py",
        "required": "exact-session chain, close, and IV-rank feature row",
        "replay_probe": "long_call_carry._leaps_candidate on manifested in-sample chain",
        "cutoff": "exact-session; missing input is DATA_GAP",
        "authority": "registered alert; replay emits no FIRE",
    },
    {
        "consumer": "H6",
        "path": "options_researcher/h6_watch.py",
        "required": "exact-session chain plus manifest-bound feature inputs",
        "replay_probe": "h6_watch._validated_chain",
        "cutoff": "exact-session; no latest fallback",
        "authority": "registered paper lane; replay emits no decision",
    },
    {
        "consumer": "H7",
        "path": "options_researcher/h7_data_gate.py",
        "required": "exact-session chain and independent close",
        "replay_probe": "h7_data_gate._evaluate_chain",
        "cutoff": "exact-session with reason-coded NO_GO",
        "authority": "registered forward lane; replay cannot authorize Stage 8",
    },
    {
        "consumer": "H8",
        "path": "options_researcher/h8_watch.py",
        "required": "exact-session chain plus manifest-bound feature inputs",
        "replay_probe": "h8_watch._validated_chain",
        "cutoff": "exact-session; no latest fallback",
        "authority": "registered paper lane; replay emits no decision",
    },
    {
        "consumer": "features",
        "path": "options_researcher/features.py",
        "required": "cached chain and same-session close",
        "replay_probe": "features.build_daily_features",
        "cutoff": "bounded caller-supplied sessions; gaps remain absent",
        "authority": "descriptive only",
    },
    {
        "consumer": "backtest feed",
        "path": "data/pandas_feed.py",
        "required": "cached EOD chain",
        "replay_probe": "pandas_feed.load_cached_chains",
        "cutoff": "manifested in-sample session only in Q9 replay",
        "authority": "structural replay only; no backtest is run",
    },
    {
        "consumer": "options flow",
        "path": "data/options_flow/* and options_researcher/flow/*",
        "required": "real trades, strict-prior NBBO, prior-known OI, and context",
        "replay_probe": "none: real .cache/options_flow input is absent",
        "cutoff": "no synthetic substitution",
        "authority": "NOT AUDITED / DATA-GATED",
    },
)


def fetch_facts(path: Path = DEFAULT_FACTS_PATH) -> dict[tuple[str, str], dict]:
    """Return the latest content-bound BLIND_CACHE fact per symbol/session."""
    return load_blind_cache_facts(path)


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


def readiness_source_identity(paths: tuple[str, ...] = READINESS_SOURCE_PATHS) -> dict:
    """Bind Q9 to exact source bytes, including uncommitted code under test."""
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
        capture_output=True,
        text=True,
        check=False,
    )
    missing = [path for path in paths if not Path(path).is_file()]
    hashes = {path: sha256_file(Path(path)) for path in paths if Path(path).is_file()}
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "source_paths": list(paths),
        "source_hashes": dict(sorted(hashes.items())),
        "missing_source_paths": missing,
        "dirty": bool(status.stdout.strip()) or status.returncode != 0,
        "dirty_paths": sorted(line[3:] for line in status.stdout.splitlines()),
    }


def _signed(payload: dict) -> dict:
    signed = dict(payload)
    signed["receipt_hash"] = sha256_hex(canonical_json(signed))
    return signed


def _strict_manifest(path: Path) -> tuple[dict[str, tuple[str, int]], list[str]]:
    """Parse every manifest line without silently overwriting malformed input."""
    records: dict[str, tuple[str, int]] = {}
    problems: list[str] = []
    try:
        lines = Path(path).read_text().splitlines()
    except OSError as exc:
        return {}, [f"MANIFEST_READ {type(exc).__name__}: {exc}"]
    for number, line in enumerate(lines, 1):
        parts = line.split("  ", 2)
        if len(parts) != 3:
            problems.append(f"MANIFEST_LINE {number}: expected sha256, size, name")
            continue
        digest, raw_size, name = parts
        line_problems: list[str] = []
        try:
            size = int(raw_size)
        except ValueError:
            problems.append(f"MANIFEST_LINE {number}: non-integer size")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            line_problems.append(f"MANIFEST_LINE {number}: invalid sha256")
        if size < 0:
            line_problems.append(f"MANIFEST_LINE {number}: negative size")
        if not name or Path(name).name != name:
            line_problems.append(f"MANIFEST_LINE {number}: name must be a basename")
        if name in records:
            line_problems.append(f"MANIFEST_LINE {number}: duplicate name {name}")
        if line_problems:
            problems.extend(line_problems)
            continue
        records[name] = (digest, size)
    return records, problems


def _validated_cache_classifications(
    *,
    classification_path: Path | None,
    chain_dir: Path,
    manifest: dict[str, tuple[str, int]],
    parquet_paths: list[Path],
) -> tuple[dict[str, dict], list[str]]:
    """Return exact-byte nested files approved as noncanonical alternates.

    A registry entry is only active when the nested file exists and its size
    and SHA-256 match. Missing entries are harmless because these files are not
    required inputs. Unknown or mutated nested files remain in the canonical
    scan and therefore fail closed.
    """
    if classification_path is None:
        return {}, []
    classification_path = Path(classification_path)
    if not classification_path.is_file():
        return {}, [f"CLASSIFICATION_REGISTRY missing: {classification_path}"]
    try:
        payload = json.loads(classification_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"CLASSIFICATION_REGISTRY {type(exc).__name__}: {exc}"]
    if not isinstance(payload, dict) or payload.get("schema") != "cache-file-classifications/v1":
        return {}, ["CLASSIFICATION_REGISTRY invalid schema"]
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return {}, ["CLASSIFICATION_REGISTRY entries must be a list"]

    observed = {path.relative_to(chain_dir).as_posix(): path for path in parquet_paths}
    validated: dict[str, dict] = {}
    problems: list[str] = []
    seen: set[str] = set()
    required = {
        "path",
        "sha256",
        "size",
        "classification",
        "canonical_path",
        "reason",
    }
    for index, entry in enumerate(entries):
        label = f"CLASSIFICATION_ENTRY[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{label} must be an object")
            continue
        missing = sorted(required - set(entry))
        if missing:
            problems.append(f"{label} missing fields: {missing}")
            continue
        relative = entry["path"]
        if not isinstance(relative, str):
            problems.append(f"{label} path must be a string")
            continue
        pure = PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or "\\" in relative
            or len(pure.parts) < 2
            or pure.as_posix() != relative
        ):
            problems.append(f"{label} path must be a normalized nested relative path: {relative}")
            continue
        if relative in seen:
            problems.append(f"{label} duplicates path: {relative}")
            continue
        seen.add(relative)
        if entry["classification"] != "NONCANONICAL_ALTERNATE_SNAPSHOT":
            problems.append(f"{label} invalid classification: {entry['classification']}")
            continue
        digest = entry["sha256"]
        size = entry["size"]
        canonical = entry["canonical_path"]
        reason = entry["reason"]
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            problems.append(f"{label} invalid sha256")
            continue
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            problems.append(f"{label} invalid size")
            continue
        if (
            not isinstance(canonical, str)
            or PurePosixPath(canonical).name != canonical
            or CACHE_FILE_RE.fullmatch(canonical) is None
        ):
            problems.append(f"{label} invalid canonical_path: {canonical}")
            continue
        if not isinstance(reason, str) or not reason.strip():
            problems.append(f"{label} reason must be non-empty")
            continue

        path = observed.get(relative)
        if path is None:
            continue
        entry_problems = []
        if canonical not in manifest or not (chain_dir / canonical).is_file():
            entry_problems.append(f"canonical file is not manifested and present: {canonical}")
        if path.stat().st_size != size:
            entry_problems.append(f"size mismatch for {relative}")
        actual_digest = sha256_file(path)
        if actual_digest != digest:
            entry_problems.append(f"sha256 mismatch for {relative}")
        if path.name != canonical:
            entry_problems.append(
                f"alternate filename {path.name} does not match canonical filename {canonical}"
            )
        if entry_problems:
            problems.extend(f"{label} {problem}" for problem in entry_problems)
            continue
        validated[relative] = {
            "path": relative,
            "sha256": actual_digest,
            "size": size,
            "classification": entry["classification"],
            "canonical_path": canonical,
            "reason": reason.strip(),
        }
    return dict(sorted(validated.items())), problems


def _cache_stat_snapshot(chain_dir: Path) -> dict:
    rows = []
    for path in sorted(
        (candidate for candidate in Path(chain_dir).rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(chain_dir).as_posix(),
    ):
        stat = path.stat()
        rows.append(
            {
                "path": path.relative_to(chain_dir).as_posix(),
                "size": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    return {
        "file_count": len(rows),
        "stat_hash": sha256_hex(canonical_json(rows)),
    }


def _parquet_metadata(path: Path) -> dict:
    """Read schema, row counts, and null statistics without value pages."""
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    fields = [
        {
            "name": field.name,
            "type": str(field.type),
            "nullable": bool(field.nullable),
        }
        for field in parquet.schema_arrow
    ]
    column_index = {name: index for index, name in enumerate(parquet.schema_arrow.names)}
    null_counts: dict[str, int | None] = {}
    for name in REQUIRED_EOD_FIELDS:
        if name not in column_index:
            continue
        total = 0
        known = True
        for row_group_index in range(parquet.metadata.num_row_groups):
            column = parquet.metadata.row_group(row_group_index).column(column_index[name])
            statistics = column.statistics
            if statistics is None or statistics.null_count is None:
                known = False
                break
            total += int(statistics.null_count)
        null_counts[name] = total if known else None
    return {
        "rows": int(parquet.metadata.num_rows),
        "fields": fields,
        "field_names": list(parquet.schema_arrow.names),
        "null_counts": null_counts,
    }


def _unmanifested_provenance(
    *,
    names: list[str],
    chain_dir: Path,
    facts_path: Path,
    file_hashes: dict[str, dict],
) -> tuple[dict[str, dict], list[str]]:
    """Link every top-level extra to its exact fact and attestation evidence."""
    if not names:
        return {}, []
    problems: list[str] = []
    try:
        facts = fetch_facts(facts_path)
    except (OSError, ValueError) as exc:
        facts = {}
        problems.append(f"FACTS_READ {type(exc).__name__}: {exc}")
    records: dict[str, dict] = {}
    for name in names:
        match = CACHE_FILE_RE.fullmatch(name)
        if match is None:
            problems.append(f"PROVENANCE malformed top-level extra: {name}")
            continue
        symbol, session = match.group("symbol"), match.group("session")
        actual_sha = file_hashes[name]["sha256"]
        fact = facts.get((symbol, session))
        fact_sha = fact.get("sha256") if fact is not None else None
        fetched = fact.get("fetched") if fact is not None else None
        attestation_path = chain_dir / ".attestations" / f"{Path(name).stem}.json"
        attestation = None
        attestation_error = None
        if attestation_path.is_file():
            try:
                candidate = json.loads(attestation_path.read_text())
                if not isinstance(candidate, dict):
                    raise ValueError("attestation root is not an object")
                attestation = candidate
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                attestation_error = f"{type(exc).__name__}: {exc}"
                problems.append(f"ATTESTATION {name}: {attestation_error}")
        attestation_sha = attestation.get("sha256") if attestation is not None else None
        attestation_matches = (
            attestation is not None
            and attestation.get("symbol") == symbol
            and attestation.get("date") == session
            and attestation.get("status") == "COMPLETE"
            and attestation_sha == actual_sha
        )
        if attestation is not None and not attestation_matches:
            problems.append(f"ATTESTATION {name}: content does not match chain identity")
        fact_matches = fact_sha == actual_sha if fact_sha is not None else False
        if fact is not None and not fact_matches:
            problems.append(f"FACT {name}: sha256 does not match chain bytes")
        records[name] = {
            "chain_sha256": actual_sha,
            "fact_present": fact is not None,
            "fact_sha256": fact_sha,
            "fact_sha_matches": fact_matches,
            "fact_fetched_at": fetched.isoformat() if fetched is not None else None,
            "attestation_path": (
                attestation_path.relative_to(chain_dir).as_posix()
                if attestation_path.is_file()
                else None
            ),
            "attestation_file_sha256": (
                sha256_file(attestation_path) if attestation_path.is_file() else None
            ),
            "attestation_chain_sha256": attestation_sha,
            "attestation_matches": attestation_matches,
            "attestation_error": attestation_error,
            "status": (
                "FACT_AND_ATTESTATION"
                if fact_matches and attestation_matches
                else (
                    "FACT_ONLY"
                    if fact_matches
                    else ("ATTESTATION_ONLY" if attestation_matches else "UNBOUND")
                )
            ),
        }
    return records, problems


def inventory_cache(
    *,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    facts_path: Path = DEFAULT_FACTS_PATH,
    classification_path: Path | None = DEFAULT_CLASSIFICATION_PATH,
) -> dict:
    """Build a deterministic, metadata-only inventory of the immutable cache."""
    chain_dir = Path(chain_dir)
    manifest_path = Path(manifest_path)
    manifest, manifest_parse_problems = _strict_manifest(manifest_path)
    manifest_problems = list(manifest_parse_problems)
    if not chain_dir.is_dir():
        manifest_problems.append(f"CACHE_DIR missing: {chain_dir}")
    elif not manifest_parse_problems:
        try:
            manifest_problems.extend(verify_manifest(str(chain_dir), str(manifest_path)))
        except (OSError, ValueError) as exc:
            manifest_problems.append(f"MANIFEST_VERIFY {type(exc).__name__}: {exc}")

    all_files = (
        sorted(
            (path for path in chain_dir.rglob("*") if path.is_file()),
            key=lambda candidate: candidate.relative_to(chain_dir).as_posix(),
        )
        if chain_dir.is_dir()
        else []
    )
    all_parquet_paths = [path for path in all_files if path.suffix == ".parquet"]
    classifications, classification_problems = _validated_cache_classifications(
        classification_path=classification_path,
        chain_dir=chain_dir,
        manifest=manifest,
        parquet_paths=all_parquet_paths,
    )
    paths = [
        path
        for path in all_parquet_paths
        if path.relative_to(chain_dir).as_posix() not in classifications
    ]
    sidecar_paths = [path for path in all_files if path.suffix != ".parquet"]
    malformed_files: list[str] = []
    nested_files: list[str] = []
    unreadable_files: list[str] = []
    zero_row_files: list[str] = []
    schema_issues: list[dict] = []
    null_issues: list[dict] = []
    unknown_null_statistics: list[dict] = []
    keys: dict[tuple[str, str], list[str]] = defaultdict(list)
    symbol_sessions: dict[str, set[str]] = defaultdict(set)
    schema_counts: dict[str, int] = defaultdict(int)
    total_nulls = {field: 0 for field in REQUIRED_EOD_FIELDS}
    total_rows = 0
    top_level_rows = 0
    nested_rows = 0

    for path in paths:
        relative = path.relative_to(chain_dir).as_posix()
        if path.parent != chain_dir:
            nested_files.append(relative)
        match = CACHE_FILE_RE.fullmatch(path.name)
        if match is None:
            malformed_files.append(relative)
        else:
            symbol = match.group("symbol")
            session = match.group("session")
            try:
                date.fromisoformat(session)
            except ValueError:
                malformed_files.append(relative)
            else:
                keys[(symbol, session)].append(relative)
                symbol_sessions[symbol].add(session)
        try:
            metadata = _parquet_metadata(path)
        except Exception as exc:
            unreadable_files.append(f"{relative}: {type(exc).__name__}: {exc}")
            continue
        total_rows += metadata["rows"]
        if path.parent == chain_dir:
            top_level_rows += metadata["rows"]
        else:
            nested_rows += metadata["rows"]
        if metadata["rows"] == 0:
            zero_row_files.append(relative)
        schema_key = canonical_json(metadata["fields"])
        schema_counts[schema_key] += 1
        field_names = metadata["field_names"]
        missing = sorted(set(REQUIRED_EOD_FIELDS) - set(field_names))
        unexpected = sorted(set(field_names) - set(REQUIRED_EOD_FIELDS))
        if missing or unexpected:
            schema_issues.append({"path": relative, "missing": missing, "unexpected": unexpected})
        for field in REQUIRED_EOD_FIELDS:
            if field not in metadata["null_counts"]:
                continue
            count = metadata["null_counts"][field]
            if count is None:
                unknown_null_statistics.append({"path": relative, "field": field})
            else:
                total_nulls[field] += count
                if count:
                    null_issues.append({"path": relative, "field": field, "null_count": count})

    duplicate_keys = [
        {"symbol": symbol, "session": session, "paths": sorted(key_paths)}
        for (symbol, session), key_paths in sorted(keys.items())
        if len(key_paths) > 1
    ]
    coverage: dict[str, dict] = {}
    for symbol, observed_set in sorted(symbol_sessions.items()):
        observed = sorted(observed_set)
        expected = trading_days(observed[0], observed[-1])
        missing_sessions = sorted(set(expected) - observed_set)
        coverage[symbol] = {
            "first_session": observed[0],
            "last_session": observed[-1],
            "observed_sessions": len(observed),
            "exchange_sessions_in_span": len(expected),
            "missing_session_count": len(missing_sessions),
            "missing_session_examples": missing_sessions[:20],
        }

    actual_relatives = {path.relative_to(chain_dir).as_posix() for path in paths}
    unmanifested = sorted(
        relative for relative in actual_relatives if relative not in manifest or "/" in relative
    )
    unmanifested_hashes = {
        relative: {
            "sha256": sha256_file(chain_dir / relative),
            "size": (chain_dir / relative).stat().st_size,
        }
        for relative in unmanifested
    }
    top_level_extras = sorted(
        path.name for path in paths if path.parent == chain_dir and path.name not in manifest
    )
    provenance, provenance_problems = _unmanifested_provenance(
        names=top_level_extras,
        chain_dir=chain_dir,
        facts_path=Path(facts_path),
        file_hashes=unmanifested_hashes,
    )
    sidecar_hashes = {
        path.relative_to(chain_dir).as_posix(): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sidecar_paths
    }
    provenance_status_counts: dict[str, int] = defaultdict(int)
    for record in provenance.values():
        provenance_status_counts[record["status"]] += 1
    coverage_warnings = [
        {
            "check": 1,
            "symbol": symbol,
            "detail": (
                f"{record['missing_session_count']} exchange sessions are absent "
                "inside the filename span; no continuous scope was declared"
            ),
            "examples": record["missing_session_examples"],
        }
        for symbol, record in coverage.items()
        if record["missing_session_count"]
    ]
    block_reasons = {
        "manifest_problems": manifest_problems,
        "nested_files": nested_files,
        "malformed_files": sorted(set(malformed_files)),
        "duplicate_symbol_sessions": duplicate_keys,
        "unreadable_files": unreadable_files,
        "zero_row_files": zero_row_files,
        "schema_variants": (
            []
            if len(schema_counts) <= 1
            else [
                {
                    "schema_hash": sha256_hex(schema),
                    "file_count": count,
                }
                for schema, count in sorted(schema_counts.items())
            ]
        ),
        "schema_issues": schema_issues,
        "null_issues": null_issues,
        "unknown_null_statistics": unknown_null_statistics,
        "provenance_mismatches": provenance_problems,
        "classification_problems": classification_problems,
    }
    blocked = any(block_reasons.values())
    return {
        "scan_mode": "PARQUET_METADATA_ONLY_NO_VALUE_PAGES",
        "chain_dir": str(chain_dir),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path) if manifest_path.is_file() else None,
        "manifest_entry_count": len(manifest),
        "counts": {
            "all_cache_files": len(all_files),
            "all_parquet_files": len(all_parquet_paths),
            "parquet_files": len(paths),
            "classified_noncanonical_parquet_files": len(classifications),
            "top_level_parquet_files": sum(path.parent == chain_dir for path in paths),
            "nested_parquet_files": len(nested_files),
            "symbols": len(symbol_sessions),
            "rows": total_rows,
            "top_level_rows": top_level_rows,
            "nested_rows": nested_rows,
            "schema_variants": len(schema_counts),
            "sidecar_files": len(sidecar_paths),
        },
        "required_fields": list(REQUIRED_EOD_FIELDS),
        "data_audited": {
            "tickers": sorted(symbol_sessions),
            "first_session": min(
                (record["first_session"] for record in coverage.values()), default=None
            ),
            "last_session": max(
                (record["last_session"] for record in coverage.values()), default=None
            ),
            "rows": total_rows,
        },
        "schema_counts": dict(sorted(schema_counts.items())),
        "null_counts": total_nulls,
        "coverage": coverage,
        "warnings": coverage_warnings,
        "unmanifested_file_hashes": unmanifested_hashes,
        "unmanifested_provenance": provenance,
        "unmanifested_provenance_status_counts": dict(sorted(provenance_status_counts.items())),
        "sidecar_file_hashes": sidecar_hashes,
        "classification_path": str(classification_path) if classification_path else None,
        "classification_sha256": (
            sha256_file(Path(classification_path))
            if classification_path and Path(classification_path).is_file()
            else None
        ),
        "classified_noncanonical_files": list(classifications.values()),
        "findings": block_reasons,
        "limitations": [
            "metadata proves structure and recorded null counts, not economic quote quality",
            "coverage spans are filename evidence and do not prove whole-OPRA completeness",
            "EOD v1 has no trade volume or intraday quote timestamp fields to audit",
            "only the replay sample receives value-level liquidity and Greek checks",
            "post-IN_SAMPLE_END value pages were not opened",
        ],
        "verdict": "BLOCK" if blocked else "PASS",
    }


def _select_replay_case(
    manifest: dict[str, tuple[str, int]],
    *,
    chain_dir: Path,
    close_dir: Path,
) -> tuple[str, str]:
    """Choose the newest manifested in-sample core row with an independent close."""
    core = set(config.H5_ENTRY_TRIGGERS)
    candidates: list[tuple[str, str]] = []
    for name in manifest:
        match = CACHE_FILE_RE.fullmatch(name)
        if match is None:
            continue
        symbol, session = match.group("symbol"), match.group("session")
        if symbol not in core or session > config.IN_SAMPLE_END:
            continue
        if not (chain_dir / name).is_file() or not (close_dir / f"{symbol}.parquet").is_file():
            continue
        candidates.append((session, symbol))
    if not candidates:
        raise ValueError("no manifested in-sample core chain has an independent close")
    session, symbol = max(candidates)
    return symbol, session


def _blocked_call(name: str, calls: dict[str, int]) -> Callable:
    def blocked(*_args, **_kwargs):
        calls[name] += 1
        raise AssertionError(f"offline replay attempted blocked surface: {name}")

    return blocked


def run_network_disabled_replay(
    *,
    symbol: str,
    session: str,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    close_dir: Path = DEFAULT_CLOSE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict:
    """Exercise representative consumers with network and cache writes trapped."""
    from data import pandas_feed, schwab_adapter, thetadata_adapter
    from data.options_flow import adapter as flow_adapter
    from options_researcher import features, h6_watch, h7_data_gate, h8_watch
    from options_researcher.studies import long_call_carry

    chain_dir = Path(chain_dir)
    close_dir = Path(close_dir)
    manifest_path = Path(manifest_path)
    symbol = symbol.strip().upper()
    session = date.fromisoformat(session).isoformat()
    if session > config.IN_SAMPLE_END:
        raise ValueError(f"replay session {session} exceeds IN_SAMPLE_END={config.IN_SAMPLE_END}")
    manifest, parse_problems = _strict_manifest(manifest_path)
    name = f"{symbol}_{session}.parquet"
    chain_path = chain_dir / name
    close_path = close_dir / f"{symbol}.parquet"
    preflight_blocks = list(parse_problems)
    if name not in manifest:
        preflight_blocks.append(f"replay input is unmanifested: {name}")
    if not chain_path.is_file():
        preflight_blocks.append(f"replay chain missing: {chain_path}")
    if not close_path.is_file():
        preflight_blocks.append(f"replay close missing: {close_path}")
    if chain_path.is_file() and name in manifest:
        expected_digest, expected_size = manifest[name]
        if chain_path.stat().st_size != expected_size:
            preflight_blocks.append(f"replay chain size mismatch: {name}")
        elif sha256_file(chain_path) != expected_digest:
            preflight_blocks.append(f"replay chain sha256 mismatch: {name}")
    if preflight_blocks:
        return {
            "mode": "NETWORK_AND_CACHE_WRITES_BLOCKED",
            "symbol": symbol,
            "session": session,
            "checks": [],
            "sentinel_calls": {},
            "cache_before": _cache_stat_snapshot(chain_dir),
            "cache_after": None,
            "blocks": preflight_blocks,
            "verdict": "BLOCK",
        }

    before = _cache_stat_snapshot(chain_dir)
    before_chain_hash = sha256_file(chain_path)
    before_manifest_problems = verify_manifest(str(chain_dir), str(manifest_path))
    calls = {
        "raw_socket_connect": 0,
        "urllib_urlopen": 0,
        "requests_transport": 0,
        "thetadata_client": 0,
        "thetadata_fetch": 0,
        "schwab_client": 0,
        "options_flow_client": 0,
        "cache_writer": 0,
    }
    checks: list[dict] = []
    errors: list[str] = []

    def check(name: str, action: Callable[[], dict]) -> None:
        try:
            detail = action()
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
        else:
            checks.append({"consumer": name, "status": "PASS", **detail})

    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(thetadata_adapter, "CACHE_DIR", chain_dir))
        stack.enter_context(
            mock.patch.object(
                socket.socket,
                "connect",
                side_effect=_blocked_call("raw_socket_connect", calls),
            )
        )
        stack.enter_context(
            mock.patch.object(
                urllib.request,
                "urlopen",
                side_effect=_blocked_call("urllib_urlopen", calls),
            )
        )
        try:
            import requests
        except ImportError:
            calls.pop("requests_transport")
        else:
            stack.enter_context(
                mock.patch.object(
                    requests.sessions.Session,
                    "request",
                    side_effect=_blocked_call("requests_transport", calls),
                )
            )
        for module, attribute, call_name in (
            (thetadata_adapter, "_client", "thetadata_client"),
            (thetadata_adapter, "_fetch_merged_chain", "thetadata_fetch"),
            (schwab_adapter, "_client", "schwab_client"),
            (flow_adapter, "default_client", "options_flow_client"),
            (thetadata_adapter, "atomic_parquet_write", "cache_writer"),
        ):
            stack.enter_context(
                mock.patch.object(
                    module,
                    attribute,
                    side_effect=_blocked_call(call_name, calls),
                )
            )

        loaded: dict[str, pd.DataFrame] = {}

        def adapter_read() -> dict:
            frame = thetadata_adapter.load_cached_chain(symbol, session, cache_dir=chain_dir)
            loaded["chain"] = frame
            return {"rows": len(frame), "source": str(chain_path)}

        check("cache-only adapter", adapter_read)

        def backtest_read() -> dict:
            chains = pandas_feed.load_cached_chains(symbol, session, session)
            return {"sessions_loaded": sorted(chains), "rows": sum(map(len, chains.values()))}

        check("backtest feed", backtest_read)

        def feature_read() -> dict:
            frame = loaded.get("chain")
            if frame is None:
                frame = thetadata_adapter.load_cached_chain(symbol, session, cache_dir=chain_dir)
            close = _raw_close(close_path, session)
            derived = features.build_daily_features(
                symbol,
                session,
                session,
                closes=pd.Series([close], index=[session], dtype=float),
                chains={session: frame},
                earnings=[],
            )
            return {"rows": len(derived), "emitted_verdict": False}

        check("features", feature_read)

        def h5_read() -> dict:
            frame = loaded.get("chain")
            if frame is None:
                frame = pd.read_parquet(chain_path)
            candidate = long_call_carry._leaps_candidate(
                frame, date.fromisoformat(session), config.H4_THESIS_DELTA
            )
            return {"candidate_present": candidate is not None, "emitted_fire": False}

        check("H5", h5_read)

        def h6_read() -> dict:
            frame = loaded.get("chain")
            if frame is None:
                frame = pd.read_parquet(chain_path)
            return {"validated_rows": len(h6_watch._validated_chain(frame)), "decision": None}

        check("H6", h6_read)

        def h7_read() -> dict:
            record, codes = h7_data_gate._evaluate_chain(symbol, session, chain_dir)
            return {
                "rows": record["row_count"],
                "reason_codes": codes,
                "stage8_authorized": False,
            }

        check("H7", h7_read)

        def h8_read() -> dict:
            frame = loaded.get("chain")
            if frame is None:
                frame = pd.read_parquet(chain_path)
            return {"validated_rows": len(h8_watch._validated_chain(frame)), "decision": None}

        check("H8", h8_read)

    after = _cache_stat_snapshot(chain_dir)
    after_chain_hash = sha256_file(chain_path)
    after_manifest_problems = verify_manifest(str(chain_dir), str(manifest_path))
    if any(calls.values()):
        errors.append(f"blocked surface calls observed: {calls}")
    if before != after or before_chain_hash != after_chain_hash:
        errors.append("cache stat/content identity changed during replay")
    if before_manifest_problems != after_manifest_problems:
        errors.append("manifest verification result changed during replay")
    return {
        "mode": "NETWORK_AND_CACHE_WRITES_BLOCKED",
        "symbol": symbol,
        "session": session,
        "chain_sha256_before": before_chain_hash,
        "chain_sha256_after": after_chain_hash,
        "manifest_problems_before": before_manifest_problems,
        "manifest_problems_after": after_manifest_problems,
        "checks": checks,
        "sentinel_calls": calls,
        "cache_before": before,
        "cache_after": after,
        "blocks": errors,
        "verdict": "BLOCK" if errors else "PASS",
    }


def build_flow_readiness(
    *,
    created_at_utc: str,
    flow_dir: Path = DEFAULT_FLOW_DIR,
    source_identity_record: dict | None = None,
) -> dict:
    """Produce the separate, non-empirical options-flow readiness report."""
    flow_dir = Path(flow_dir)
    files = (
        sorted(
            (path for path in flow_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(flow_dir).as_posix(),
        )
        if flow_dir.is_dir()
        else []
    )
    hashes = {
        path.relative_to(flow_dir).as_posix(): {
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in files
    }
    blockers = []
    if not flow_dir.exists():
        blockers.append("real raw dataset absent: .cache/options_flow does not exist")
    elif not files:
        blockers.append("real raw dataset absent: .cache/options_flow is empty")
    else:
        blockers.append("real input exists but has not received the required full audit")
    blockers.extend(
        (
            "data rights and entitlement provenance are not established",
            "decision-grade sample size is not established",
            "holdout and verdict use are not preregistered",
        )
    )
    return _signed(
        {
            "flow_readiness_version": FLOW_READINESS_VERSION,
            "created_at_utc": created_at_utc,
            "flow_dir": str(flow_dir),
            "flow_dir_exists": flow_dir.is_dir(),
            "raw_file_count": len(files),
            "raw_file_hashes": hashes,
            "real_empirical_sample_size": 0 if not files else None,
            "fixture_evidence_only": True,
            "source_identity": source_identity_record
            if source_identity_record is not None
            else readiness_source_identity(),
            "blockers": blockers,
            "status": "NOT AUDITED / DATA-GATED",
            "empirical_opinion": None,
            "provider_call": False,
        }
    )


def run_readiness(
    *,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    close_dir: Path = DEFAULT_CLOSE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    flow_dir: Path = DEFAULT_FLOW_DIR,
    replay_symbol: str | None = None,
    replay_session: str | None = None,
    created_at_utc: str | None = None,
    identity: dict | None = None,
) -> dict:
    """Run Q9 inventory, replay, and flow gates without provider or raw writes."""
    created = created_at_utc or datetime.now(timezone.utc).isoformat()
    identity = readiness_source_identity() if identity is None else identity
    inventory = inventory_cache(chain_dir=chain_dir, manifest_path=manifest_path)
    manifest, _problems = _strict_manifest(manifest_path)
    if (replay_symbol is None) != (replay_session is None):
        raise ValueError("replay_symbol and replay_session must be provided together")
    if replay_symbol is None or replay_session is None:
        replay_symbol, replay_session = _select_replay_case(
            manifest, chain_dir=Path(chain_dir), close_dir=Path(close_dir)
        )
    replay = run_network_disabled_replay(
        symbol=replay_symbol,
        session=replay_session,
        chain_dir=chain_dir,
        close_dir=close_dir,
        manifest_path=manifest_path,
    )
    flow = build_flow_readiness(
        created_at_utc=created,
        flow_dir=flow_dir,
        source_identity_record=identity,
    )
    blocks = []
    if inventory["verdict"] != "PASS":
        blocks.append("cache inventory is BLOCK")
    if replay["verdict"] != "PASS":
        blocks.append("network-disabled replay is BLOCK")
    if identity.get("dirty"):
        blocks.append(f"source identity is dirty: {identity.get('dirty_paths', [])}")
    if identity.get("missing_source_paths"):
        blocks.append(f"source identity is incomplete: {identity['missing_source_paths']}")
    verdict = "BLOCK" if blocks else "PASS"
    return _signed(
        {
            "readiness_version": READINESS_VERSION,
            "created_at_utc": created,
            "goal": "offline EOD intelligence readiness without provider calls or flow fabrication",
            "source_identity": identity,
            "inventory": inventory,
            "replay": replay,
            "consumer_map": list(CONSUMER_MAP),
            "flow_readiness_receipt_hash": flow["receipt_hash"],
            "flow_status": flow["status"],
            "blocks": blocks,
            "verdict": verdict,
            "ledger_note": (
                f"{READINESS_VERSION}: {verdict}; "
                f"parquet_files={inventory['counts']['parquet_files']}; "
                f"replay={replay['verdict']}; flow={flow['status']}; NOT APPENDED"
            ),
            "provider_call": False,
            "raw_cache_mutation": False,
            "verdict_use": False,
        }
    )


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

    expiration_sessions = set(trading_days(min(parsed).isoformat(), max(parsed).isoformat()))
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

    zero_bid = (
        ntm & monthly & dte.between(30, 120) & oi_ok & (frame["bid"] == 0) & (frame["ask"] > 0)
    )
    if zero_bid.any():
        warnings.append(
            _finding(7, symbol, session, f"{int(zero_bid.sum())} near-money rows have zero bid")
        )
    relative_spread = (frame["ask"] - frame["bid"]) / mid.where(mid > 0)
    too_wide = (
        ntm & monthly & dte.between(30, 120) & oi_ok & (relative_spread > QUALITY_WIDE_SPREAD)
    )
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
        missing_monthlies = [
            value for value in expected_monthlies if value not in present_monthlies
        ]
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
        near = relevant[
            relevant["strike"].between(
                (1 - config.H7_NTM_BAND) * spot,
                (1 + config.H7_NTM_BAND) * spot,
            )
        ]
        if near.empty:
            blocks.append(_finding(3, symbol, session, f"no near-money {lane} strikes"))
            continue
        admitted, count = lane_admission(frame, spot=spot, today=today, dte_band=band, right=right)
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
        blocks.append(_finding("SCHEMA", symbol, session, f"{type(exc).__name__}: {exc}"))
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
                _finding(
                    9, symbol, session, f"fetched before EOD report ready: {fetched.isoformat()}"
                )
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


def _write_json_report(report: dict, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=1, sort_keys=True, allow_nan=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload)
    os.replace(temporary, path)
    return path


def write_readiness_receipt(report: dict, reports_dir: Path = DEFAULT_REPORTS_DIR) -> Path:
    report_day = str(report["created_at_utc"])[:10]
    return _write_json_report(
        report, Path(reports_dir) / f"{report_day}-q9-offline-intelligence.json"
    )


def write_flow_readiness_report(report: dict, reports_dir: Path = DEFAULT_FLOW_REPORTS_DIR) -> Path:
    report_day = str(report["created_at_utc"])[:10]
    return _write_json_report(report, Path(reports_dir) / f"{report_day}-q9-flow-readiness.json")


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


def verify_readiness_receipt(
    path: Path,
    *,
    chain_dir: Path = DEFAULT_CHAIN_DIR,
    close_dir: Path = DEFAULT_CLOSE_DIR,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    flow_dir: Path = DEFAULT_FLOW_DIR,
    identity: dict | None = None,
) -> tuple[bool, list[str]]:
    expected = json.loads(Path(path).read_text())
    replay = expected["replay"]
    actual = run_readiness(
        chain_dir=chain_dir,
        close_dir=close_dir,
        manifest_path=manifest_path,
        flow_dir=flow_dir,
        replay_symbol=replay["symbol"],
        replay_session=replay["session"],
        created_at_utc=expected["created_at_utc"],
        identity=identity,
    )
    failures = [
        key
        for key in sorted(set(expected) | set(actual))
        if canonical_json(expected.get(key)) != canonical_json(actual.get(key))
    ]
    return not failures, failures


def verify_flow_readiness_report(
    path: Path,
    *,
    flow_dir: Path = DEFAULT_FLOW_DIR,
    identity: dict | None = None,
) -> tuple[bool, list[str]]:
    expected = json.loads(Path(path).read_text())
    actual = build_flow_readiness(
        created_at_utc=expected["created_at_utc"],
        flow_dir=flow_dir,
        source_identity_record=identity,
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
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--flow-dir", default=str(DEFAULT_FLOW_DIR))
    parser.add_argument("--flow-reports-dir", default=str(DEFAULT_FLOW_REPORTS_DIR))
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="run the Q9 metadata inventory, offline replay, and flow readiness gate",
    )
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)

    try:
        if args.verify:
            expected = json.loads(args.verify.read_text())
            if "readiness_version" in expected:
                ok, failures = verify_readiness_receipt(
                    args.verify,
                    chain_dir=Path(args.chain_dir),
                    close_dir=Path(args.close_dir),
                    manifest_path=Path(args.manifest),
                    flow_dir=Path(args.flow_dir),
                )
            elif "flow_readiness_version" in expected:
                ok, failures = verify_flow_readiness_report(
                    args.verify, flow_dir=Path(args.flow_dir)
                )
            else:
                ok, failures = verify_receipt(
                    args.verify,
                    chain_dir=Path(args.chain_dir),
                    close_dir=Path(args.close_dir),
                )
            print("receipt VALID" if ok else f"receipt INVALID: {failures}")
            return 0 if ok else 2
        if args.readiness:
            report = run_readiness(
                chain_dir=Path(args.chain_dir),
                close_dir=Path(args.close_dir),
                manifest_path=Path(args.manifest),
                flow_dir=Path(args.flow_dir),
            )
            inventory = report["inventory"]
            counts = inventory["counts"]
            print(
                "Offline Intelligence readiness "
                f"files={counts['parquet_files']} rows={counts['rows']} "
                f"symbols={counts['symbols']} replay={report['replay']['verdict']}"
            )
            print(f"FLOW STATUS: {report['flow_status']}")
            print(f"VERDICT: {report['verdict']}")
            for blocker in report["blocks"]:
                print(f"  BLOCK: {blocker}")
            if args.write:
                flow = build_flow_readiness(
                    created_at_utc=report["created_at_utc"],
                    flow_dir=Path(args.flow_dir),
                    source_identity_record=report["source_identity"],
                )
                if flow["receipt_hash"] != report["flow_readiness_receipt_hash"]:
                    raise ValueError("flow readiness hash changed before write")
                print(
                    f"readiness receipt: {write_readiness_receipt(report, Path(args.reports_dir))}"
                )
                print(
                    f"flow report: {write_flow_readiness_report(flow, Path(args.flow_reports_dir))}"
                )
            return 2 if report["verdict"] == "BLOCK" else 0
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
        print(
            f"  BLOCK check {finding['check']} {finding['symbol']} {finding['session']}: {finding['detail']}"
        )
    for finding in report["warnings"][:20]:
        print(
            f"  WARN check {finding['check']} {finding['symbol']} {finding['session']}: {finding['detail']}"
        )
    print(f"VERDICT: {report['verdict']}")
    if args.write:
        if report["verdict"] == "BLOCK":
            print("receipt not written: BLOCK verdict")
        else:
            print(f"receipt: {write_receipt(report, Path(args.reports_dir))}")
    return 2 if report["verdict"] == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Preserved resumable ThetaData schema-v2 backfill for completed OD-1.

The completed owner-approved scope is frozen here for reproducibility. Dry-run
remains available, but provider execution now fails through the global
ThetaData acquisition policy before credentials, clients, or output mutation.
The immutable v1 ``.cache/chains`` directory is always refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import provider_policy, thetadata_adapter  # noqa: E402
from data.atomic_io import (  # noqa: E402
    atomic_text_write,
    publish_staged_file,
    stage_parquet_write,
)
from data.cache_runner import _fetch_with_transport_retry, trading_days  # noqa: E402
from data.cache_schema import CHAIN_SCHEMA_VERSION_V2, chain_schema_metadata  # noqa: E402
from data.recent_topup import audit_chain  # noqa: E402
from tools.cache_manifest import verify_manifest, write_manifest  # noqa: E402

SCOPE_ID = "od1-v2-2026-08-01"
SYMBOLS = (
    "NVDA",
    "PLTR",
    "AMZN",
    "BE",
    "UBER",
    "AVGO",
    "IREN",
    "HIMS",
    "CRWV",
    "TEM",
    "NOW",
    "SMCI",
    "AMD",
    "USAR",
    "ET",
    "VST",
    "CEG",
    "MSFT",
)
START_SESSION = "2025-07-25"
END_SESSION = "2026-07-31"
EXPECTED_SESSIONS = 256
CALLS_PER_PARTITION = 2
ENDPOINTS = (
    "option_history_greeks_eod",
    "option_history_open_interest",
)
BASE_PROVIDER_CALLS = len(SYMBOLS) * EXPECTED_SESSIONS * CALLS_PER_PARTITION
MAX_PROVIDER_CALLS = 9500
APPROVAL_TOKEN = "OD1-V2-9500-APPROVED"
OWNER_DECISION_PAYLOAD_SHA256 = "638246205afc741d8fb5c2986caea5d24012aea742c0a4f984a30328e4fadd9e"
PULL_APPROVAL_PAYLOAD_SHA256 = "139382a426125369f2e7ded12c4d323668e4dce0241a098b34af6413dea61352"
PREDECESSOR_SCOPE_SHA256 = "ed5fbcdb42000ce1ca872bb98f5a4561f328a81d0f38f7cdbabf3697a6106dff"
PREDECESSOR_RESERVATION_ENTRIES = 217
PREDECESSOR_RESERVED_PROVIDER_CALLS = 434
PREDECESSOR_COMPLETED_PARTITIONS = 180
PREDECESSOR_RESERVATION_PREFIX_SHA256 = (
    "837d1b485efd519307e6378b26875c6ba940a4679786a6aad5962979c07b471a"
)
PREDECESSOR_EXCESS_RESERVATIONS = (
    PREDECESSOR_RESERVED_PROVIDER_CALLS - PREDECESSOR_COMPLETED_PARTITIONS * CALLS_PER_PARTITION
)
MINIMUM_TOTAL_RESERVATIONS_TO_COMPLETE = BASE_PROVIDER_CALLS + PREDECESSOR_EXCESS_RESERVATIONS
SCHEMA = "thetadata-v2-backfill/v1"
ATTESTATION_SCHEMA = "thetadata-v2-partition-attestation/v1"
SCOPE_AMENDMENT_SCHEMA = "thetadata-v2-scope-amendment/v1"
MIN_FREE_BYTES = 10 * 1024**3
SOURCE_PATHS = (
    "config.py",
    "data/atomic_io.py",
    "data/cache_runner.py",
    "data/cache_schema.py",
    "data/provider_policy.py",
    "data/recent_topup.py",
    "data/thetadata_adapter.py",
    "tools/cache_manifest.py",
    "tools/thetadata_v2_backfill.py",
)


class BackfillRefused(RuntimeError):
    """A safety or provenance condition refused the backfill."""


class CallBudget:
    """Durable total ceiling covering retries and process restarts."""

    def __init__(self, maximum: int, journal_path: Path, run_id: str) -> None:
        self.maximum = maximum
        self.journal_path = journal_path
        self.run_id = run_id
        self._lock = threading.Lock()
        self.reserved = self._load_reserved()

    def _load_reserved(self) -> int:
        if not self.journal_path.exists():
            return 0
        total = 0
        for line_number, line in enumerate(self.journal_path.read_text().splitlines(), start=1):
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BackfillRefused(
                    f"malformed call reservation journal line {line_number}"
                ) from exc
            if item.get("schema") != "thetadata-call-reservation/v1":
                raise BackfillRefused(f"invalid call reservation journal line {line_number}")
            if item.get("scope_id") != SCOPE_ID:
                raise BackfillRefused(f"reservation scope mismatch on line {line_number}")
            calls = item.get("reserved_calls")
            if calls != CALLS_PER_PARTITION:
                raise BackfillRefused(f"invalid call reservation count on line {line_number}")
            total += calls
        if total > self.maximum:
            raise BackfillRefused(
                f"existing provider-call reservations {total} exceed ceiling {self.maximum}"
            )
        return total

    def reserve_partition_attempt(self, symbol: str, session: str) -> None:
        with self._lock:
            proposed = self.reserved + CALLS_PER_PARTITION
            if proposed > self.maximum:
                raise BackfillRefused(
                    f"provider-call ceiling reached: {proposed} would exceed {self.maximum}"
                )
            entry = {
                "schema": "thetadata-call-reservation/v1",
                "reservation_id": str(uuid.uuid4()),
                "run_id": self.run_id,
                "scope_id": SCOPE_ID,
                "symbol": symbol,
                "session": session,
                "reserved_calls": CALLS_PER_PARTITION,
                "reserved_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            self.journal_path.parent.mkdir(parents=True, exist_ok=True)
            with self.journal_path.open("a") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.reserved = proposed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha() -> str:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _source_identity() -> dict:
    root = Path(__file__).resolve().parents[1]
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise BackfillRefused("execution requires a clean isolated source worktree")
    return {
        "commit": _git_sha(),
        "source_files": {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in SOURCE_PATHS
        },
        "python": platform.python_version(),
        "pandas": package_version("pandas"),
        "pyarrow": package_version("pyarrow"),
        "thetadata": package_version("thetadata"),
    }


@contextmanager
def _execution_lock(output_dir: Path):
    import fcntl

    lock_path = output_dir / "_meta" / "execution.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BackfillRefused("another OD-1 downloader process is already running") from exc
        yield


def _check_disk_space(output_dir: Path) -> int:
    ancestor = output_dir
    while not ancestor.exists():
        ancestor = ancestor.parent
    free = shutil.disk_usage(ancestor).free
    if free < MIN_FREE_BYTES:
        raise BackfillRefused(
            f"only {free / 1024**3:.1f} GiB free; require at least "
            f"{MIN_FREE_BYTES / 1024**3:.0f} GiB before capture"
        )
    return free


def _verify_predecessor_reservations(journal_path: Path) -> None:
    """Bind the expanded ceiling to every reservation spent before expansion."""
    if not journal_path.is_file():
        raise BackfillRefused("predecessor reservation journal is missing")
    lines = journal_path.read_bytes().splitlines(keepends=True)
    if len(lines) < PREDECESSOR_RESERVATION_ENTRIES:
        raise BackfillRefused("predecessor reservation journal was truncated")
    prefix = b"".join(lines[:PREDECESSOR_RESERVATION_ENTRIES])
    if hashlib.sha256(prefix).hexdigest() != PREDECESSOR_RESERVATION_PREFIX_SHA256:
        raise BackfillRefused("predecessor reservation journal prefix mismatch")
    reserved = 0
    try:
        for raw in lines[:PREDECESSOR_RESERVATION_ENTRIES]:
            item = json.loads(raw)
            if item.get("reserved_calls") != CALLS_PER_PARTITION:
                raise ValueError("reservation width mismatch")
            reserved += item["reserved_calls"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise BackfillRefused("predecessor reservation journal is malformed") from exc
    if reserved != PREDECESSOR_RESERVED_PROVIDER_CALLS:
        raise BackfillRefused("predecessor reservation total mismatch")


def _bind_scope_record(meta_dir: Path, scope_record: dict) -> bool:
    """Preserve the original scope and append one exact expanded-scope amendment."""
    scope_path = meta_dir / "scope.json"
    amendment_path = meta_dir / "scope_amendment.json"
    if not scope_path.exists():
        if amendment_path.exists():
            raise BackfillRefused("scope amendment exists without a base scope")
        atomic_text_write(json.dumps(scope_record, sort_keys=True, indent=2) + "\n", scope_path)
        return False
    if _read_json(scope_path) == scope_record:
        if amendment_path.exists():
            raise BackfillRefused("unexpected scope amendment beside current base scope")
        return False
    if _sha256(scope_path) != PREDECESSOR_SCOPE_SHA256:
        raise BackfillRefused("existing namespace scope/source identity does not match")
    amendment = {
        "schema": SCOPE_AMENDMENT_SCHEMA,
        "predecessor_scope_sha256": PREDECESSOR_SCOPE_SHA256,
        "predecessor_reservation_prefix_sha256": PREDECESSOR_RESERVATION_PREFIX_SHA256,
        "predecessor_reserved_provider_calls": PREDECESSOR_RESERVED_PROVIDER_CALLS,
        "expanded_scope_record": scope_record,
    }
    if amendment_path.exists():
        if _read_json(amendment_path) != amendment:
            raise BackfillRefused("existing scope amendment does not match")
    else:
        atomic_text_write(
            json.dumps(amendment, sort_keys=True, indent=2) + "\n",
            amendment_path,
        )
    return True


def _preflight_existing_namespace(
    output_dir: Path, tasks: list[tuple[str, str]], *, code_sha: str
) -> None:
    """Refuse all unknown/partial prior state before any provider future starts."""
    expected_artifacts = set()
    expected_receipts = set()
    for symbol, session in tasks:
        expected_artifacts.update(
            {
                _partition_path(output_dir, symbol, session),
                _raw_path(output_dir, "greeks_eod", symbol, session),
                _raw_path(output_dir, "open_interest", symbol, session),
            }
        )
        expected_receipts.update(
            {
                _attestation_path(output_dir, symbol, session),
                _gap_path(output_dir, symbol, session),
                _schema_block_path(output_dir, symbol, session),
            }
        )
    orphan_temps = [path for path in output_dir.rglob(".*.tmp") if path.is_file()]
    if orphan_temps:
        raise BackfillRefused(f"orphaned staging files require review: {orphan_temps[:3]}")
    unknown_parquet = [
        path for path in output_dir.rglob("*.parquet") if path not in expected_artifacts
    ]
    if unknown_parquet:
        raise BackfillRefused(f"unknown parquet files in v2 namespace: {unknown_parquet[:3]}")
    receipt_roots = (
        output_dir / "_meta" / "attestations",
        output_dir / "_meta" / "gaps",
        output_dir / "_meta" / "schema_blocks",
    )
    unknown_receipts = [
        path
        for root in receipt_roots
        if root.exists()
        for path in root.rglob("*.json")
        if path not in expected_receipts
    ]
    if unknown_receipts:
        raise BackfillRefused(f"unknown receipts in v2 namespace: {unknown_receipts[:3]}")
    for symbol, session in tasks:
        candidates = (
            _partition_path(output_dir, symbol, session),
            _raw_path(output_dir, "greeks_eod", symbol, session),
            _raw_path(output_dir, "open_interest", symbol, session),
            _attestation_path(output_dir, symbol, session),
            _gap_path(output_dir, symbol, session),
            _schema_block_path(output_dir, symbol, session),
        )
        if any(path.exists() for path in candidates):
            _capture_one(output_dir, symbol, session, code_sha=code_sha)


def scope_plan() -> dict:
    sessions = trading_days(START_SESSION, END_SESSION)
    if len(sessions) != EXPECTED_SESSIONS:
        raise BackfillRefused(
            f"scope calendar drift: expected {EXPECTED_SESSIONS} sessions, found {len(sessions)}"
        )
    partitions = len(SYMBOLS) * len(sessions)
    return {
        "schema": SCHEMA,
        "scope_id": SCOPE_ID,
        "symbols": list(SYMBOLS),
        "start_session": sessions[0],
        "end_session": sessions[-1],
        "session_count": len(sessions),
        "partition_count": partitions,
        "endpoints": list(ENDPOINTS),
        "calls_per_partition": CALLS_PER_PARTITION,
        "base_provider_calls": partitions * CALLS_PER_PARTITION,
        "maximum_provider_calls_including_retries": MAX_PROVIDER_CALLS,
        "predecessor_reserved_provider_calls": PREDECESSOR_RESERVED_PROVIDER_CALLS,
        "minimum_total_reservations_to_complete": MINIMUM_TOTAL_RESERVATIONS_TO_COMPLETE,
        "approval_token": APPROVAL_TOKEN,
        "provider_call": False,
    }


def pull_approval_payload(output_dir: Path) -> str:
    return (
        "OD1_V2_EXPANDED_PULL_APPROVAL 2026-08-01. OWNER APPROVAL: continue and "
        "expand the resumable side-by-side ThetaData schema-v2 pull for symbols "
        f"{','.join(SYMBOLS)} over {EXPECTED_SESSIONS} XNYS sessions {START_SESSION} through "
        f"{END_SESSION} using endpoints {' and '.join(ENDPOINTS)}. Base call count "
        f"{BASE_PROVIDER_CALLS:,}. The exact predecessor journal has already reserved "
        f"{PREDECESSOR_RESERVED_PROVIDER_CALLS:,} calls, including "
        f"{PREDECESSOR_EXCESS_RESERVATIONS:,} beyond its completed-partition base; minimum "
        f"total reservations to complete is {MINIMUM_TOTAL_RESERVATIONS_TO_COMPLETE:,}. Hard "
        f"ceiling {MAX_PROVIDER_CALLS:,} provider-call reservations across all prior and future "
        "retries and process restarts. Persist both untouched provider "
        "response tables and the normalized schema-v2 table as compressed Parquet. "
        f"Destination {output_dir.resolve()} only; never overwrite .cache/chains. Capture "
        "provenance and run a capture-time audit on every normalized partition; stop on "
        "scope, entitlement, schema, budget, or provenance deviation. A separate full "
        "fourteen-check read-only audit is required before any verdict use. No result, "
        "verdict, backtest, or live-trading authority."
    )


def _verify_owner_facts(facts_log: Path, output_dir: Path) -> dict[str, str]:
    payloads = [
        line.split("\t", 1)[1] for line in facts_log.read_text().splitlines() if "\t" in line
    ]
    decisions = [
        value
        for value in payloads
        if hashlib.sha256(value.encode()).hexdigest() == OWNER_DECISION_PAYLOAD_SHA256
    ]
    approval = pull_approval_payload(output_dir)
    approvals = [value for value in payloads if value == approval]
    if len(decisions) != 1:
        raise BackfillRefused("exactly one superseding OD-1 owner decision fact is required")
    if len(approvals) != 1:
        raise BackfillRefused("exactly one exact OD-1 pull approval fact is required")
    return {
        "owner_decision_payload_sha256": OWNER_DECISION_PAYLOAD_SHA256,
        "pull_approval_payload_sha256": hashlib.sha256(approval.encode()).hexdigest(),
    }


def _safe_output_dir(value: Path, *, v1_dir: Path) -> Path:
    output = value.expanduser().resolve()
    immutable_v1 = v1_dir.expanduser().resolve()
    if output == immutable_v1 or immutable_v1 in output.parents:
        raise BackfillRefused(
            f"v2 output may not equal or live inside immutable v1 cache {immutable_v1}"
        )
    if output in immutable_v1.parents:
        raise BackfillRefused("v2 output may not be an ancestor of the v1 cache")
    return output


def _attestation_path(output_dir: Path, symbol: str, session: str) -> Path:
    return output_dir / "_meta" / "attestations" / f"{symbol}_{session}.json"


def _gap_path(output_dir: Path, symbol: str, session: str) -> Path:
    return output_dir / "_meta" / "gaps" / f"{symbol}_{session}.json"


def _schema_block_path(output_dir: Path, symbol: str, session: str) -> Path:
    return output_dir / "_meta" / "schema_blocks" / f"{symbol}_{session}.json"


def _partition_path(output_dir: Path, symbol: str, session: str) -> Path:
    return output_dir / f"{symbol}_{session}.parquet"


def _raw_path(output_dir: Path, endpoint: str, symbol: str, session: str) -> Path:
    return output_dir / "raw" / endpoint / symbol / f"{session}.parquet"


def _relative(output_dir: Path, path: Path) -> str:
    return str(path.resolve().relative_to(output_dir.resolve()))


def _artifact_metadata(output_dir: Path, path: Path) -> dict:
    rows, columns = _partition_metadata(path)
    return {
        "path": _relative(output_dir, path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "rows": rows,
        "columns": columns,
    }


def _write_artifact_manifest(output_dir: Path) -> tuple[Path, int]:
    """Bind every immutable data/provenance artifact, excluding mutable run logs."""
    manifest_path = output_dir / "_meta" / "artifact_manifest.jsonl"
    excluded = {
        manifest_path,
        output_dir / "_meta" / "execution.lock",
    }
    paths = []
    for path in output_dir.rglob("*"):
        if not path.is_file() or path in excluded or "runs" in path.relative_to(output_dir).parts:
            continue
        paths.append(path)
    rows = [
        {
            "path": _relative(output_dir, path),
            "sha256": _sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(paths)
    ]
    atomic_text_write(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        manifest_path,
    )
    return manifest_path, len(rows)


def _verify_artifact_manifest(output_dir: Path, manifest_path: Path) -> list[str]:
    problems = []
    seen = set()
    for line_number, line in enumerate(manifest_path.read_text().splitlines(), start=1):
        item = json.loads(line)
        relative = item.get("path")
        if not isinstance(relative, str) or relative in seen:
            problems.append(f"line {line_number}: invalid or duplicate path")
            continue
        seen.add(relative)
        path = output_dir / relative
        if not path.is_file():
            problems.append(f"MISSING {relative}")
        elif path.stat().st_size != item.get("size_bytes") or _sha256(path) != item.get("sha256"):
            problems.append(f"MISMATCH {relative}")
    return problems


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BackfillRefused(f"malformed provenance artifact {path}") from exc
    if not isinstance(value, dict):
        raise BackfillRefused(f"malformed provenance artifact {path}")
    return value


def _store_raw_schema_block(
    output_dir: Path,
    symbol: str,
    session: str,
    raw_greeks,
    raw_open_interest,
    *,
    code_sha: str,
    error: Exception,
) -> None:
    """Preserve irreplaceable provider frames even when normalization refuses them."""
    paths = (
        (_raw_path(output_dir, "greeks_eod", symbol, session), raw_greeks),
        (_raw_path(output_dir, "open_interest", symbol, session), raw_open_interest),
    )
    for path, frame in paths:
        if path.exists():
            raise BackfillRefused(f"refusing overwrite of schema-blocked raw artifact {path}")
        staged = stage_parquet_write(frame, path, compression="zstd", index=True)
        publish_staged_file(staged, path)
    receipt = {
        "schema": "thetadata-v2-schema-block/v1",
        "scope_id": SCOPE_ID,
        "symbol": symbol,
        "session": session,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_code_sha": code_sha,
        "error_type": type(error).__name__,
        "error": str(error),
        "raw_artifacts": {
            "greeks_eod": _artifact_metadata(output_dir, paths[0][0]),
            "open_interest": _artifact_metadata(output_dir, paths[1][0]),
        },
    }
    atomic_text_write(
        json.dumps(receipt, sort_keys=True, indent=2) + "\n",
        _schema_block_path(output_dir, symbol, session),
    )


def _partition_metadata(path: Path) -> tuple[int, list[str]]:
    return thetadata_adapter._parquet_metadata_without_values(path)


def _complete_payload(
    *,
    output_dir: Path,
    symbol: str,
    session: str,
    path: Path,
    captured_at_utc: str,
    code_sha: str,
    audit: dict,
    raw_greeks_path: Path,
    raw_open_interest_path: Path,
) -> dict:
    rows, columns = _partition_metadata(path)
    metadata = chain_schema_metadata(columns)
    if metadata.schema_version != CHAIN_SCHEMA_VERSION_V2:
        raise BackfillRefused(f"{path} is not a complete schema-v2 partition")
    return {
        "schema": ATTESTATION_SCHEMA,
        "status": "COMPLETE",
        "scope_id": SCOPE_ID,
        "symbol": symbol,
        "session": session,
        "path": _relative(output_dir, path),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
        "rows": rows,
        "columns": columns,
        "schema_version": metadata.schema_version,
        "usage": metadata.usage,
        "provider": "ThetaData",
        "endpoints": list(ENDPOINTS),
        "captured_at_utc": captured_at_utc,
        "subscription_end_owner_stated": "2026-08-02",
        "thetadata_client_version": package_version("thetadata"),
        "source_code_sha": code_sha,
        "owner_decision_payload_sha256": OWNER_DECISION_PAYLOAD_SHA256,
        "output_namespace": str(output_dir),
        "artifacts": {
            "normalized_v2": _artifact_metadata(output_dir, path),
            "raw_greeks_eod": _artifact_metadata(output_dir, raw_greeks_path),
            "raw_open_interest": _artifact_metadata(output_dir, raw_open_interest_path),
        },
        "audit": audit,
    }


def _verify_existing(output_dir: Path, symbol: str, session: str, *, code_sha: str) -> dict:
    path = _partition_path(output_dir, symbol, session)
    raw_greeks_path = _raw_path(output_dir, "greeks_eod", symbol, session)
    raw_open_interest_path = _raw_path(output_dir, "open_interest", symbol, session)
    attestation_path = _attestation_path(output_dir, symbol, session)
    if not attestation_path.is_file():
        raise BackfillRefused(f"orphaned v2 partition refuses resume: {path} has no attestation")
    attestation = _read_json(attestation_path)
    if attestation.get("status") == "PENDING_PUBLISH":
        publish = attestation.get("publish")
        if not isinstance(publish, list) or len(publish) != 3:
            raise BackfillRefused(f"malformed pending publish transaction for {path}")
        for item in publish:
            final = output_dir / str(item.get("path"))
            staged = output_dir / str(item.get("staged_path"))
            expected = item.get("sha256")
            if final.exists():
                if expected != _sha256(final):
                    raise BackfillRefused(f"pending transaction hash mismatch for {final}")
                continue
            if not staged.exists() or expected != _sha256(staged):
                raise BackfillRefused(f"pending transaction is not recoverable for {final}")
            publish_staged_file(staged, final)
        import pandas as pd

        chain = thetadata_adapter.validate_chain_schema(pd.read_parquet(path))
        audit = audit_chain(chain)
        complete = _complete_payload(
            output_dir=output_dir,
            symbol=symbol,
            session=session,
            path=path,
            captured_at_utc=str(attestation["captured_at_utc"]),
            code_sha=str(attestation.get("source_code_sha") or code_sha),
            audit=audit,
            raw_greeks_path=raw_greeks_path,
            raw_open_interest_path=raw_open_interest_path,
        )
        atomic_text_write(
            json.dumps(complete, sort_keys=True, indent=2) + "\n",
            attestation_path,
        )
        return {"status": "RECOVERED", "audit": audit}
    expected = {
        "schema": ATTESTATION_SCHEMA,
        "status": "COMPLETE",
        "scope_id": SCOPE_ID,
        "symbol": symbol,
        "session": session,
        "path": _relative(output_dir, path),
        "sha256": _sha256(path),
    }
    for key, value in expected.items():
        if attestation.get(key) != value:
            raise BackfillRefused(f"attestation mismatch for {path}: {key}")
    rows, columns = _partition_metadata(path)
    if attestation.get("rows") != rows or attestation.get("columns") != columns:
        raise BackfillRefused(f"attestation parquet metadata mismatch for {path}")
    if chain_schema_metadata(columns).schema_version != CHAIN_SCHEMA_VERSION_V2:
        raise BackfillRefused(f"existing partition is not schema v2: {path}")
    artifacts = attestation.get("artifacts")
    expected_artifacts = {
        "normalized_v2": path,
        "raw_greeks_eod": raw_greeks_path,
        "raw_open_interest": raw_open_interest_path,
    }
    if not isinstance(artifacts, dict):
        raise BackfillRefused(f"attestation has no raw artifact inventory for {path}")
    for name, artifact_path in expected_artifacts.items():
        declared = artifacts.get(name)
        if not isinstance(declared, dict) or not artifact_path.is_file():
            raise BackfillRefused(f"missing attested artifact {name} for {path}")
        if declared.get("path") != _relative(output_dir, artifact_path):
            raise BackfillRefused(f"artifact path mismatch for {name} at {path}")
        if declared.get("sha256") != _sha256(artifact_path):
            raise BackfillRefused(f"artifact hash mismatch for {name} at {path}")
    return {"status": "VERIFIED", "audit": attestation.get("audit", {})}


def _capture_one(
    output_dir: Path,
    symbol: str,
    session: str,
    *,
    code_sha: str,
    call_budget: CallBudget | None = None,
) -> dict:
    path = _partition_path(output_dir, symbol, session)
    attestation_path = _attestation_path(output_dir, symbol, session)
    gap_path = _gap_path(output_dir, symbol, session)
    schema_block_path = _schema_block_path(output_dir, symbol, session)
    raw_greeks_path = _raw_path(output_dir, "greeks_eod", symbol, session)
    raw_open_interest_path = _raw_path(output_dir, "open_interest", symbol, session)
    if schema_block_path.exists():
        block = _read_json(schema_block_path)
        if (
            block.get("schema") != "thetadata-v2-schema-block/v1"
            or block.get("scope_id") != SCOPE_ID
            or block.get("symbol") != symbol
            or block.get("session") != session
        ):
            raise BackfillRefused(f"malformed schema-block receipt {schema_block_path}")
        for name, artifact_path in (
            ("greeks_eod", raw_greeks_path),
            ("open_interest", raw_open_interest_path),
        ):
            declared = block.get("raw_artifacts", {}).get(name, {})
            if not artifact_path.is_file() or declared.get("sha256") != _sha256(artifact_path):
                raise BackfillRefused(f"schema-blocked raw artifact mismatch for {name}")
        raise BackfillRefused(
            f"prior provider schema deviation requires review for {symbol}@{session}"
        )
    if gap_path.exists():
        if (
            attestation_path.exists()
            or path.exists()
            or raw_greeks_path.exists()
            or raw_open_interest_path.exists()
        ):
            raise BackfillRefused(
                f"gap receipt conflicts with partition artifacts for {symbol}@{session}"
            )
        gap = _read_json(gap_path)
        if (
            gap.get("schema") != "thetadata-v2-gap/v1"
            or gap.get("scope_id") != SCOPE_ID
            or gap.get("symbol") != symbol
            or gap.get("session") != session
        ):
            raise BackfillRefused(f"malformed gap receipt {gap_path}")
        return {"status": "GAP_VERIFIED", "audit": {"verdict": "BLOCK"}}
    if attestation_path.exists():
        return _verify_existing(output_dir, symbol, session, code_sha=code_sha)
    if path.exists() or raw_greeks_path.exists() or raw_open_interest_path.exists():
        raise BackfillRefused(f"orphaned partition artifacts refuse fetch for {symbol}@{session}")

    def fetch_with_budget(fetch_symbol: str, fetch_session: str):
        if call_budget is not None:
            call_budget.reserve_partition_attempt(fetch_symbol, fetch_session)
        return thetadata_adapter._fetch_raw(fetch_symbol, fetch_session)

    fetched = _fetch_with_transport_retry(fetch_with_budget, symbol, session)
    if fetched is None:
        raise BackfillRefused(f"provider returned no result for {symbol}@{session}")
    raw_greeks, raw_open_interest = fetched
    try:
        normalized_greeks = thetadata_adapter._normalize_contract_keys(raw_greeks, "greeks")
        chain = thetadata_adapter._merge_chain_frames(raw_greeks, raw_open_interest)
        if chain.empty:
            raise ValueError("greeks and open-interest reports share no contract keys")
        dropped = len(normalized_greeks) - len(chain)
        chain = thetadata_adapter.validate_chain_schema(chain)
        chain = chain.sort_values(["expiration", "strike", "right"], kind="stable").reset_index(
            drop=True
        )
        metadata = chain_schema_metadata(chain.columns)
        if metadata.schema_version != CHAIN_SCHEMA_VERSION_V2:
            raise ValueError("provider result is not schema v2")
    except (KeyError, TypeError, ValueError) as exc:
        _store_raw_schema_block(
            output_dir,
            symbol,
            session,
            raw_greeks,
            raw_open_interest,
            code_sha=code_sha,
            error=exc,
        )
        raise BackfillRefused(
            f"provider schema deviation for {symbol}@{session}; raw frames preserved"
        ) from exc
    audit = audit_chain(chain)
    captured_at = datetime.now(timezone.utc).isoformat()
    frames_and_paths = (
        (raw_greeks, raw_greeks_path, True),
        (raw_open_interest, raw_open_interest_path, True),
        (chain, path, False),
    )
    staged_files: list[tuple[Path, Path]] = []
    try:
        for frame, destination, preserve_index in frames_and_paths:
            staged_files.append(
                (
                    stage_parquet_write(
                        frame,
                        destination,
                        compression="zstd",
                        index=preserve_index,
                    ),
                    destination,
                )
            )
    except BaseException:
        for staged, _ in staged_files:
            staged.unlink(missing_ok=True)
        raise
    pending = {
        "schema": ATTESTATION_SCHEMA,
        "status": "PENDING_PUBLISH",
        "scope_id": SCOPE_ID,
        "symbol": symbol,
        "session": session,
        "captured_at_utc": captured_at,
        "source_code_sha": code_sha,
        "publish": [
            {
                "path": _relative(output_dir, destination),
                "staged_path": _relative(output_dir, staged),
                "sha256": _sha256(staged),
            }
            for staged, destination in staged_files
        ],
    }
    atomic_text_write(
        json.dumps(pending, sort_keys=True, indent=2) + "\n",
        attestation_path,
    )
    for staged, destination in staged_files:
        if destination.exists():
            raise BackfillRefused(f"refusing overwrite of partition artifact {destination}")
        publish_staged_file(staged, destination)
    complete = _complete_payload(
        output_dir=output_dir,
        symbol=symbol,
        session=session,
        path=path,
        captured_at_utc=captured_at,
        code_sha=code_sha,
        audit={**audit, "dropped_without_open_interest": dropped},
        raw_greeks_path=raw_greeks_path,
        raw_open_interest_path=raw_open_interest_path,
    )
    atomic_text_write(
        json.dumps(complete, sort_keys=True, indent=2) + "\n",
        attestation_path,
    )
    return {"status": "FETCHED", "audit": complete["audit"]}


def execute(output_dir: Path, *, workers: int, owner_facts: dict[str, str]) -> dict:
    plan = scope_plan()
    sessions = trading_days(START_SESSION, END_SESSION)
    free_bytes_before = _check_disk_space(output_dir)
    source_identity = _source_identity()
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = output_dir / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    code_sha = str(source_identity["commit"])
    scope_record = {
        **plan,
        "output_namespace": str(output_dir),
        "owner_facts": owner_facts,
        "source_identity": source_identity,
        "storage": {
            "normalized": "schema-v2 zstd parquet",
            "raw_greeks_eod": "provider frame zstd parquet",
            "raw_open_interest": "provider frame zstd parquet",
            "existing_v1_mutated": False,
        },
    }
    tasks = [(symbol, session) for symbol in SYMBOLS for session in sessions]
    scope_path = meta_dir / "scope.json"
    predecessor_scope = scope_path.exists() and _sha256(scope_path) == PREDECESSOR_SCOPE_SHA256
    if predecessor_scope:
        _verify_predecessor_reservations(meta_dir / "call_reservations.jsonl")
    _preflight_existing_namespace(output_dir, tasks, code_sha=code_sha)
    continued_from_predecessor = _bind_scope_record(meta_dir, scope_record)
    if continued_from_predecessor != predecessor_scope:
        raise BackfillRefused("scope continuation state changed during preflight")
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4()}"
    journal_path = meta_dir / "call_reservations.jsonl"
    call_budget = CallBudget(MAX_PROVIDER_CALLS, journal_path, run_id)
    state = {
        **plan,
        "provider_call": True,
        "status": "RUNNING",
        "source_code_sha": code_sha,
        "source_identity": source_identity,
        "run_id": run_id,
        "output_namespace": str(output_dir),
        "owner_facts": owner_facts,
        "reserved_provider_calls": 0,
        "free_bytes_before": free_bytes_before,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "FETCHED": 0,
            "VERIFIED": 0,
            "RECOVERED": 0,
            "GAP": 0,
            "GAP_VERIFIED": 0,
        },
        "audit_blocks": 0,
    }
    run_path = meta_dir / "runs" / f"{run_id}.json"
    atomic_text_write(json.dumps(state, sort_keys=True, indent=2) + "\n", run_path)

    executor = ThreadPoolExecutor(max_workers=workers)
    futures = {
        executor.submit(
            _capture_one,
            output_dir,
            symbol,
            session,
            code_sha=code_sha,
            call_budget=call_budget,
        ): (
            symbol,
            session,
        )
        for symbol, session in tasks
    }
    try:
        for completed, future in enumerate(as_completed(futures), start=1):
            symbol, session = futures[future]
            try:
                result = future.result()
            except RuntimeError as exc:
                if "returned no rows" not in str(exc):
                    raise
                state["counts"]["GAP"] += 1
                state["audit_blocks"] += 1
                gap = {
                    "schema": "thetadata-v2-gap/v1",
                    "scope_id": SCOPE_ID,
                    "symbol": symbol,
                    "session": session,
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "source_code_sha": code_sha,
                    "error": str(exc),
                }
                atomic_text_write(
                    json.dumps(gap, sort_keys=True, indent=2) + "\n",
                    _gap_path(output_dir, symbol, session),
                )
            else:
                state["counts"][result["status"]] += 1
                if result.get("audit", {}).get("verdict") == "BLOCK":
                    state["audit_blocks"] += 1
            if completed % 10 == 0 or completed == len(tasks):
                state["reserved_provider_calls"] = call_budget.reserved
                atomic_text_write(
                    json.dumps(state, sort_keys=True, indent=2) + "\n",
                    run_path,
                )
                print(
                    f"progress {completed}/{len(tasks)} counts={state['counts']} "
                    f"audit_blocks={state['audit_blocks']}",
                    flush=True,
                )
    except BaseException:
        state["status"] = "FAILED"
        atomic_text_write(json.dumps(state, sort_keys=True, indent=2) + "\n", run_path)
        for future in futures:
            future.cancel()
        raise
    finally:
        executor.shutdown(wait=True, cancel_futures=True)

    manifest_path = meta_dir / "chain_manifest.txt"
    write_manifest(str(output_dir), str(manifest_path))
    problems = verify_manifest(str(output_dir), str(manifest_path))
    if problems:
        raise BackfillRefused(f"generated v2 manifest failed verification: {problems[:3]}")
    artifact_manifest_path, artifact_count = _write_artifact_manifest(output_dir)
    artifact_problems = _verify_artifact_manifest(output_dir, artifact_manifest_path)
    if artifact_problems:
        raise BackfillRefused(
            f"generated artifact manifest failed verification: {artifact_problems[:3]}"
        )
    state["status"] = "COMPLETE_WITH_AUDIT_BLOCKS" if state["audit_blocks"] else "COMPLETE"
    state["reserved_provider_calls"] = call_budget.reserved
    state["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    state["free_bytes_after"] = shutil.disk_usage(output_dir).free
    state["manifest_path"] = str(manifest_path)
    state["manifest_sha256"] = _sha256(manifest_path)
    state["artifact_manifest_path"] = str(artifact_manifest_path)
    state["artifact_manifest_sha256"] = _sha256(artifact_manifest_path)
    state["artifact_manifest_entries"] = artifact_count
    atomic_text_write(json.dumps(state, sort_keys=True, indent=2) + "\n", run_path)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approval-token")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--v1-dir", type=Path)
    parser.add_argument("--facts-log", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    plan = scope_plan()
    if not args.execute:
        print(json.dumps(plan, sort_keys=True, indent=2))
        return 0
    provider_policy.require_thetadata_acquisition("completed OD-1 v2 backfill rerun")
    if args.approval_token != APPROVAL_TOKEN:
        raise BackfillRefused(f"provider execution requires exact approval token {APPROVAL_TOKEN}")
    if args.output_dir is None:
        raise BackfillRefused("--output-dir is required for provider execution")
    if args.v1_dir is None:
        raise BackfillRefused("--v1-dir is required for provider execution")
    if args.facts_log is None or not args.facts_log.is_file():
        raise BackfillRefused("--facts-log must name the canonical facts ledger")
    if args.env_file is None or not args.env_file.is_file():
        raise BackfillRefused("--env-file must name an existing local credential file")
    if not 1 <= args.workers <= 8:
        raise BackfillRefused("--workers must be between 1 and 8")
    output_dir = _safe_output_dir(args.output_dir, v1_dir=args.v1_dir)
    owner_facts = _verify_owner_facts(args.facts_log, output_dir)
    print(pull_approval_payload(output_dir))
    print(json.dumps({**plan, "output_namespace": str(output_dir)}, sort_keys=True))
    from dotenv import load_dotenv

    load_dotenv(args.env_file, override=False)
    with _execution_lock(output_dir):
        result = execute(output_dir, workers=args.workers, owner_facts=owner_facts)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

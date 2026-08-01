"""Resumable, side-by-side ThetaData schema-v2 backfill for OD-1.

The owner-approved universe is frozen here.  Dry-run is the default and never
loads credentials or constructs a provider client.  Execution requires the
exact approval token printed by dry-run and writes only to a caller-supplied
v2 directory; the immutable v1 ``.cache/chains`` directory is always refused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from importlib.metadata import version as package_version
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data import thetadata_adapter  # noqa: E402
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
SYMBOLS = ("NVDA", "PLTR", "AMZN", "BE", "UBER", "AVGO", "IREN", "HIMS")
START_SESSION = "2025-07-25"
END_SESSION = "2026-07-27"
EXPECTED_SESSIONS = 252
CALLS_PER_PARTITION = 2
ENDPOINTS = (
    "option_history_greeks_eod",
    "option_history_open_interest",
)
BASE_PROVIDER_CALLS = len(SYMBOLS) * EXPECTED_SESSIONS * CALLS_PER_PARTITION
MAX_PROVIDER_CALLS = 4100
APPROVAL_TOKEN = "OD1-V2-4100-APPROVED"
OWNER_DECISION_PAYLOAD_SHA256 = "638246205afc741d8fb5c2986caea5d24012aea742c0a4f984a30328e4fadd9e"
SCHEMA = "thetadata-v2-backfill/v1"
ATTESTATION_SCHEMA = "thetadata-v2-partition-attestation/v1"


class BackfillRefused(RuntimeError):
    """A safety or provenance condition refused the backfill."""


class CallBudget:
    """Thread-safe reservation ceiling covering retries as well as first attempts."""

    def __init__(self, maximum: int) -> None:
        self.maximum = maximum
        self.reserved = 0
        self._lock = threading.Lock()

    def reserve_partition_attempt(self) -> None:
        with self._lock:
            proposed = self.reserved + CALLS_PER_PARTITION
            if proposed > self.maximum:
                raise BackfillRefused(
                    f"provider-call ceiling reached: {proposed} would exceed {self.maximum}"
                )
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
        "approval_token": APPROVAL_TOKEN,
        "provider_call": False,
    }


def pull_approval_payload(output_dir: Path) -> str:
    return (
        "OD1_V2_PULL_APPROVAL 2026-08-01. OWNER APPROVAL: execute one resumable "
        "side-by-side ThetaData schema-v2 pull for symbols "
        f"{','.join(SYMBOLS)} over {EXPECTED_SESSIONS} XNYS sessions {START_SESSION} through "
        f"{END_SESSION} using endpoints {' and '.join(ENDPOINTS)}. Base call count "
        f"{BASE_PROVIDER_CALLS:,}; hard ceiling {MAX_PROVIDER_CALLS:,} provider-call "
        f"reservations including retries. Destination {output_dir.resolve()} only; never "
        "overwrite .cache/chains. Capture provenance and audit every partition; stop on "
        "scope, entitlement, schema, budget, or provenance deviation. No result, verdict, "
        "backtest, or live-trading authority."
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


def _partition_path(output_dir: Path, symbol: str, session: str) -> Path:
    return output_dir / f"{symbol}_{session}.parquet"


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise BackfillRefused(f"malformed provenance artifact {path}") from exc
    if not isinstance(value, dict):
        raise BackfillRefused(f"malformed provenance artifact {path}")
    return value


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
        "path": str(path),
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
        "audit": audit,
    }


def _verify_existing(output_dir: Path, symbol: str, session: str, *, code_sha: str) -> dict:
    path = _partition_path(output_dir, symbol, session)
    attestation_path = _attestation_path(output_dir, symbol, session)
    if not attestation_path.is_file():
        raise BackfillRefused(f"orphaned v2 partition refuses resume: {path} has no attestation")
    attestation = _read_json(attestation_path)
    if attestation.get("status") == "PENDING_PUBLISH":
        expected = attestation.get("sha256")
        if expected != _sha256(path):
            raise BackfillRefused(f"pending attestation hash mismatch for {path}")
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
        "path": str(path),
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
    if path.exists():
        return _verify_existing(output_dir, symbol, session, code_sha=code_sha)

    def fetch_with_budget(fetch_symbol: str, fetch_session: str):
        if call_budget is not None:
            call_budget.reserve_partition_attempt()
        return thetadata_adapter._fetch_merged_chain(fetch_symbol, fetch_session)

    fetched = _fetch_with_transport_retry(fetch_with_budget, symbol, session)
    if fetched is None:
        raise BackfillRefused(f"provider returned no result for {symbol}@{session}")
    chain, dropped = fetched
    chain = thetadata_adapter.validate_chain_schema(chain)
    metadata = chain_schema_metadata(chain.columns)
    if metadata.schema_version != CHAIN_SCHEMA_VERSION_V2:
        raise BackfillRefused(f"provider result is not schema v2 for {symbol}@{session}")
    audit = audit_chain(chain)
    captured_at = datetime.now(timezone.utc).isoformat()
    staged = stage_parquet_write(chain, path)
    try:
        pending = {
            "schema": ATTESTATION_SCHEMA,
            "status": "PENDING_PUBLISH",
            "scope_id": SCOPE_ID,
            "symbol": symbol,
            "session": session,
            "path": str(path),
            "sha256": _sha256(staged),
            "captured_at_utc": captured_at,
            "source_code_sha": code_sha,
        }
        atomic_text_write(
            json.dumps(pending, sort_keys=True, indent=2) + "\n",
            _attestation_path(output_dir, symbol, session),
        )
        if path.exists():
            raise BackfillRefused(f"refusing overwrite of v2 partition {path}")
        publish_staged_file(staged, path)
    except BaseException:
        try:
            staged.unlink()
        except FileNotFoundError:
            pass
        raise
    complete = _complete_payload(
        output_dir=output_dir,
        symbol=symbol,
        session=session,
        path=path,
        captured_at_utc=captured_at,
        code_sha=code_sha,
        audit={**audit, "dropped_without_open_interest": dropped},
    )
    atomic_text_write(
        json.dumps(complete, sort_keys=True, indent=2) + "\n",
        _attestation_path(output_dir, symbol, session),
    )
    return {"status": "FETCHED", "audit": complete["audit"]}


def execute(output_dir: Path, *, workers: int, owner_facts: dict[str, str]) -> dict:
    plan = scope_plan()
    sessions = trading_days(START_SESSION, END_SESSION)
    output_dir.mkdir(parents=True, exist_ok=True)
    meta_dir = output_dir / "_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)
    code_sha = _git_sha()
    call_budget = CallBudget(MAX_PROVIDER_CALLS)
    tasks = [(symbol, session) for symbol in SYMBOLS for session in sessions]
    state = {
        **plan,
        "provider_call": True,
        "status": "RUNNING",
        "source_code_sha": code_sha,
        "output_namespace": str(output_dir),
        "owner_facts": owner_facts,
        "reserved_provider_calls": 0,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "counts": {"FETCHED": 0, "VERIFIED": 0, "RECOVERED": 0, "GAP": 0},
        "audit_blocks": 0,
    }
    run_path = meta_dir / "run.json"
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
                gap_path = meta_dir / "gaps.jsonl"
                with gap_path.open("a") as handle:
                    handle.write(json.dumps({"symbol": symbol, "session": session}) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
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
    state["status"] = "COMPLETE_WITH_AUDIT_BLOCKS" if state["audit_blocks"] else "COMPLETE"
    state["reserved_provider_calls"] = call_budget.reserved
    state["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    state["manifest_path"] = str(manifest_path)
    state["manifest_sha256"] = _sha256(manifest_path)
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
    from dotenv import load_dotenv

    load_dotenv(args.env_file, override=False)
    output_dir = _safe_output_dir(args.output_dir, v1_dir=args.v1_dir)
    owner_facts = _verify_owner_facts(args.facts_log, output_dir)
    print(pull_approval_payload(output_dir))
    print(json.dumps({**plan, "output_namespace": str(output_dir)}, sort_keys=True))
    result = execute(output_dir, workers=args.workers, owner_facts=owner_facts)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

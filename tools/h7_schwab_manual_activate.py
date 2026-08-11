"""Owner-confirmed first registration for ``h7-forward-schwab-v1``.

This CLI assembles and revalidates the official 15-name Schwab evidence chain,
then delegates the sole write to
``options_researcher.h7_schwab_window_registration.register_window_real``.
It never appends directly, never trims the universe, and never changes an
authority switch.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from data.cache_runner import session_close_utc
from options_researcher import h7_activation_guard as guard
from options_researcher import h7_schwab_data_gate as schwab_data_gate
from options_researcher import h7_schwab_window_registration as registration
from options_researcher import h7_source_health as source_health_mod
from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from research.receipts import load_receipt

CONFIRMATION = "REGISTER H7 SCHWAB FIRST WINDOW"


def _json_object(path: Path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _code_state() -> tuple[str, bool]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return head, porcelain == ""


def _source_health_by_symbol(source: dict, names: list[str]) -> dict[str, bool]:
    rows = source.get("symbols")
    if not isinstance(rows, dict):
        return {name: False for name in names}
    return {name: bool(rows.get(name, {}).get("healthy") is True) for name in names}


def _exact_source_receipt(path: Path, *, completed_session: str, names: list[str]) -> dict:
    receipt = load_receipt(path, expected_type="source_health")
    if receipt.get("evaluation_session") != completed_session:
        raise ValueError("source-health receipt does not match completed session")
    if receipt.get("scope") != scope_identity():
        raise ValueError("source-health receipt is not the official 15-name scope")
    if (
        receipt.get("activation_ready") is not True
        or receipt.get("healthy_count") != len(names)
        or receipt.get("unhealthy_symbols") != []
        or set(receipt.get("symbols", {})) != set(names)
    ):
        raise ValueError("source-health receipt is not a full 15-name pass")
    return receipt


def _package_paths(receipt: dict, names: list[str]) -> tuple[Path, Path, Path, Path, str]:
    rows = receipt.get("symbols")
    if not isinstance(rows, dict) or set(rows) != set(names):
        raise ValueError("Schwab data-gate receipt is not the official 15-name scope")
    close_dirs: set[Path] = set()
    chain_dirs: set[Path] = set()
    bindings: set[tuple[str, str, str]] = set()
    for name in names:
        row = rows.get(name)
        if not isinstance(row, dict) or row.get("verdict") != "GO":
            raise ValueError(f"Schwab data-gate receipt is not GO for {name}")
        close_path = row.get("close", {}).get("path")
        chain_path = row.get("chain", {}).get("expected_path")
        binding = row.get("chain", {}).get("audit_receipt")
        if (
            not isinstance(close_path, str)
            or not isinstance(chain_path, str)
            or not isinstance(binding, dict)
            or binding.get("valid") is not True
            or binding.get("provider") != "schwab"
            or binding.get("session_chain_convention") != registration.SESSION_CHAIN_CONVENTION
        ):
            raise ValueError(f"Schwab package binding is incomplete for {name}")
        close_dirs.add(Path(close_path).parent)
        chain_dirs.add(Path(chain_path).parent)
        manifest_path = binding.get("manifest_path")
        capture_path = binding.get("receipt_path")
        manifest_hash = binding.get("manifest_hash")
        if (
            not isinstance(manifest_path, str)
            or not manifest_path
            or not isinstance(capture_path, str)
            or not capture_path
            or not isinstance(manifest_hash, str)
            or not manifest_hash
        ):
            raise ValueError(f"Schwab package receipt paths are incomplete for {name}")
        bindings.add((manifest_path, capture_path, manifest_hash))
    if len(close_dirs) != 1 or len(chain_dirs) != 1 or len(bindings) != 1:
        raise ValueError("Schwab data-gate receipt mixes package identities")
    manifest_path, capture_path, manifest_hash = bindings.pop()
    return (
        close_dirs.pop(),
        chain_dirs.pop(),
        Path(manifest_path),
        Path(capture_path),
        manifest_hash,
    )


def _exact_data_gate_receipt(
    path: Path,
    *,
    completed_session: str,
    names: list[str],
    evaluator=schwab_data_gate.evaluate,
) -> tuple[dict, dict, str]:
    receipt = load_receipt(path, expected_type="data_gate")
    if receipt.get("evaluation_session") != completed_session:
        raise ValueError("Schwab data-gate receipt does not match completed session")
    if (
        receipt.get("scope") != scope_identity()
        or receipt.get("universe") != names
        or receipt.get("go_count") != len(names)
        or receipt.get("no_go_count") != 0
        or receipt.get("whole_universe_verdict") != "GO"
    ):
        raise ValueError("Schwab data-gate receipt is not the official 15-name scope")
    if receipt.get("evidence_mode") != schwab_data_gate.EVIDENCE_MODE:
        raise ValueError("data-gate receipt is not Schwab preclose evidence")
    close_dir, chain_dir, manifest_path, capture_path, manifest_hash = _package_paths(
        receipt, names
    )
    try:
        requested = date.fromisoformat(str(receipt.get("requested_run_date")))
    except ValueError as exc:
        raise ValueError("data-gate requested run date is malformed") from exc
    fresh = evaluator(
        requested,
        close_dir=close_dir,
        chain_dir=chain_dir,
        manifest_path=manifest_path,
        receipt_path=capture_path,
        scope=scope_identity(),
    )
    for field, value in fresh.items():
        if value != receipt.get(field):
            raise ValueError(f"Schwab data-gate evidence is stale at {field}")
    return receipt, fresh, manifest_hash


def _exact_backup_chain(
    *, backup_path: Path, backup_restore_path: Path, completed_session: str
) -> tuple[dict, dict]:
    backup = load_receipt(backup_path, expected_type="backup")
    restore = load_receipt(backup_restore_path, expected_type="backup_restore")
    if (
        backup.get("completed_session") != completed_session
        or restore.get("completed_session") != completed_session
    ):
        raise ValueError("backup evidence does not match completed session")
    snapshot = backup.get("snapshot_id")
    if (
        not isinstance(snapshot, str)
        or not snapshot
        or snapshot == "latest"
        or restore.get("snapshot_id") != snapshot
        or restore.get("snapshot") != snapshot
    ):
        raise ValueError("backup restore is not bound to the exact snapshot")
    if restore.get("backup_receipt_hash") != backup.get("receipt_hash"):
        raise ValueError("backup restore is not bound to the backup receipt")
    if restore.get("restored_inventory") != backup.get("input_files"):
        raise ValueError("backup restore inventory is not exact")
    if (
        backup.get("scope") != scope_identity()
        or restore.get("scope") != scope_identity()
        or restore.get("verification", {}).get("ok") is not True
    ):
        raise ValueError("backup restore evidence is stale or unverified")
    return backup, restore


def _require_evidence_value(evidence: dict, field: str, actual: str) -> None:
    if evidence.get(field) != actual:
        raise ValueError(f"evidence {field} does not match re-earned value")


def _make_recheck(
    *,
    source_path: Path,
    data_gate_path: Path,
    backup_path: Path,
    backup_restore_path: Path,
    completed_session: str,
    names: list[str],
    source_hash: str,
    data_gate_hash: str,
    data_gate_evaluator,
    source_health_evaluator,
    source_assertion_loader,
):
    def recheck() -> dict:
        source = _exact_source_receipt(
            source_path, completed_session=completed_session, names=names
        )
        data_receipt, fresh, _ = _exact_data_gate_receipt(
            data_gate_path,
            completed_session=completed_session,
            names=names,
            evaluator=data_gate_evaluator,
        )
        _exact_backup_chain(
            backup_path=backup_path,
            backup_restore_path=backup_restore_path,
            completed_session=completed_session,
        )
        if source["receipt_hash"] != source_hash:
            raise registration.ActivationRefused(
                "source-health receipt changed between assembly and append"
            )
        if data_receipt["receipt_hash"] != data_gate_hash:
            raise registration.ActivationRefused(
                "data-gate receipt changed between assembly and append"
            )
        on = date.fromisoformat(completed_session)
        health = source_health_evaluator(
            requested_on=on,
            on=on,
            known_as_of=session_close_utc(completed_session),
            assertions=source_assertion_loader(),
            names=names,
        )
        return {
            "source_health_all_healthy": health.get("activation_ready") is True,
            "data_gate_go": (
                fresh.get("evaluation_session") == completed_session
                and fresh.get("whole_universe_verdict") == "GO"
                and fresh.get("universe") == names
            ),
            "source_health_evidence_id": source_hash,
            "data_gate_evidence_id": data_gate_hash,
        }

    return recheck


def activate(
    *,
    owner_path: Path,
    evidence_path: Path,
    source_health_path: Path,
    data_gate_path: Path,
    backup_path: Path,
    backup_restore_path: Path,
    completed_session: str,
    confirmation: str,
    spec_path: Path,
    forward_base: Path = registration.SCHWAB_FORWARD_STORE,
    code_state=_code_state,
    data_gate_evaluator=schwab_data_gate.evaluate,
    source_health_evaluator=source_health_mod.evaluate_health,
    source_assertion_loader=source_health_mod.load_assertions,
):
    """Re-earn every input and delegate the sole seq-0 append to one door."""
    if confirmation != CONFIRMATION:
        raise ValueError(f"type exactly {CONFIRMATION!r} to register")
    names = list(scope_identity()["symbols"])
    if len(names) != 15:
        raise ValueError("official H7 scope is not exactly 15 names")
    owner = _json_object(owner_path)
    evidence = _json_object(evidence_path)
    source = _exact_source_receipt(
        source_health_path, completed_session=completed_session, names=names
    )
    data_receipt, _, manifest_hash = _exact_data_gate_receipt(
        data_gate_path,
        completed_session=completed_session,
        names=names,
        evaluator=data_gate_evaluator,
    )
    if data_receipt.get("source_health_receipt_hash") != source["receipt_hash"]:
        raise ValueError("Schwab data gate is not linked to source-health evidence")
    _, backup_restore = _exact_backup_chain(
        backup_path=backup_path,
        backup_restore_path=backup_restore_path,
        completed_session=completed_session,
    )

    spec_sha = sha256_file(Path(spec_path))
    for field, actual in (
        ("activation_spec_sha256", spec_sha),
        ("source_health_evidence_id", source["receipt_hash"]),
        ("source_health_receipt_hash", source["receipt_hash"]),
        ("data_gate_evidence_id", data_receipt["receipt_hash"]),
        ("data_gate_receipt_hash", data_receipt["receipt_hash"]),
        ("backup_restore_receipt_hash", backup_restore["receipt_hash"]),
        ("last_historical_session", completed_session),
        ("last_historical_manifest_receipt_hash", manifest_hash),
    ):
        _require_evidence_value(evidence, field, actual)

    report = guard.activation_preconditions(
        forward_base=forward_base,
        source_health_by_symbol=_source_health_by_symbol(source, names),
        universe=tuple(names),
        data_gate_result=data_receipt,
        owner_inputs=owner,
        allow_real_readonly=True,
        strict=True,
        source_health_receipt=source,
        data_gate_receipt=data_receipt,
        backup_restore_receipt=backup_restore,
        completed_session=completed_session,
        owner_fields=registration.OWNER_FIELDS,
    )
    recheck = _make_recheck(
        source_path=Path(source_health_path),
        data_gate_path=Path(data_gate_path),
        backup_path=Path(backup_path),
        backup_restore_path=Path(backup_restore_path),
        completed_session=completed_session,
        names=names,
        source_hash=source["receipt_hash"],
        data_gate_hash=data_receipt["receipt_hash"],
        data_gate_evaluator=data_gate_evaluator,
        source_health_evaluator=source_health_evaluator,
        source_assertion_loader=source_assertion_loader,
    )
    result = registration.register_window_real(
        owner=owner,
        evidence=evidence,
        guard_report=report,
        spec_sha256=spec_sha,
        spec_path=Path(spec_path),
        base_dir=forward_base,
        code_state=code_state,
        recheck_gates=recheck,
        universe_manifest=None,
    )
    if result.seq != 0:
        raise RuntimeError("registration wrote something other than the first event")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source-health-receipt", type=Path, required=True)
    parser.add_argument("--data-gate-receipt", type=Path, required=True)
    parser.add_argument("--backup-receipt", type=Path, required=True)
    parser.add_argument("--backup-restore-receipt", type=Path, required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--activation-spec", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        result = activate(
            owner_path=args.owner,
            evidence_path=args.evidence,
            source_health_path=args.source_health_receipt,
            data_gate_path=args.data_gate_receipt,
            backup_path=args.backup_receipt,
            backup_restore_path=args.backup_restore_receipt,
            completed_session=args.completed_session,
            confirmation=args.confirm,
            spec_path=args.activation_spec,
        )
    except Exception as exc:
        print(f"H7 SCHWAB REGISTRATION BLOCKED -- {type(exc).__name__}: {exc}")
        return 2
    print(f"H7 SCHWAB FIRST WINDOW REGISTERED seq={result.seq} record_hash={result.record_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Manual, owner-confirmed first H7 window registration.

This is the only command allowed to append the first real H7 event. It never
places an order and it refuses to run without an explicit confirmation token,
a valid empty real ledger, the current 15-name receipt chain, a fresh restore
receipt, owner fields, independent review evidence, and a clean source tree.
Do not run this during the repair rollout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from options_researcher import h7_activation_guard as guard
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_window_registration as registration
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_watch import validate_data_gate_receipt
from research.receipts import load_receipt

CONFIRMATION = "ACTIVATE H7 FIRST WINDOW"


def _json_object(path: Path) -> dict:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def activate(*, owner_path: Path, evidence_path: Path,
             source_health_path: Path, data_gate_path: Path,
             backup_restore_path: Path, completed_session: str,
             confirmation: str) -> ledger.AppendResult:
    if confirmation != CONFIRMATION:
        raise ValueError(f"type exactly {CONFIRMATION!r} to activate")
    owner = _json_object(owner_path)
    evidence = _json_object(evidence_path)
    source = load_receipt(source_health_path, expected_type="source_health")
    data_gate = load_receipt(data_gate_path, expected_type="data_gate")
    backup = load_receipt(backup_restore_path, expected_type="backup_restore")
    names = list(scope_identity()["symbols"])
    validated_gate = validate_data_gate_receipt(
        data_gate_path, evaluation_session=completed_session, names=names)
    if validated_gate != data_gate:
        raise ValueError("data-gate receipt changed during validation")
    if source.get("receipt_hash") != data_gate.get("source_health_receipt_hash"):
        raise ValueError("data gate is not linked to the supplied source receipt")
    if source.get("scope") != scope_identity() or source.get("activation_ready") is not True:
        raise ValueError("source health is not a complete current-scope pass")
    if backup.get("completed_session") != completed_session:
        raise ValueError("backup restore evidence is older than the completed session")

    evidence = {
        **evidence,
        "scope_id": scope_identity()["scope_id"],
        "scope_hash": scope_identity()["scope_hash"],
        "source_health_receipt_hash": source["receipt_hash"],
        "data_gate_receipt_hash": data_gate["receipt_hash"],
        "backup_restore_receipt_hash": backup["receipt_hash"],
        "source_hash": data_gate["source_hash"],
        "config_hash": data_gate["config_hash"],
    }
    report = guard.activation_preconditions(
        forward_base=REAL_FORWARD_STORE,
        source_health_by_symbol={symbol: True for symbol in names},
        universe=tuple(names), data_gate_result=data_gate,
        owner_inputs=owner, allow_real_readonly=True, strict=True,
        source_health_receipt=source, data_gate_receipt=data_gate,
        backup_restore_receipt=backup, completed_session=completed_session)
    if not report.ready:
        failed = [f"{check.name}: {check.reason}" for check in report.checks
                  if not check.ok]
        raise RuntimeError("activation blocked: " + "; ".join(failed))
    event = registration.build_window_registration_event(
        owner=owner, evidence=evidence)
    result = ledger.append_event(event, base_dir=REAL_FORWARD_STORE,
                                 expected_head=None)
    if result.seq != 0:
        raise RuntimeError("activation wrote something other than the first event")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source-health-receipt", type=Path, required=True)
    parser.add_argument("--data-gate-receipt", type=Path, required=True)
    parser.add_argument("--backup-restore-receipt", type=Path, required=True)
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        result = activate(
            owner_path=args.owner, evidence_path=args.evidence,
            source_health_path=args.source_health_receipt,
            data_gate_path=args.data_gate_receipt,
            backup_restore_path=args.backup_restore_receipt,
            completed_session=args.completed_session,
            confirmation=args.confirm)
    except Exception as exc:
        print(f"H7 ACTIVATION BLOCKED -- {type(exc).__name__}: {exc}")
        return 2
    print(f"H7 ACTIVATED FIRST WINDOW REGISTRATION seq={result.seq} "
          f"record_hash={result.record_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

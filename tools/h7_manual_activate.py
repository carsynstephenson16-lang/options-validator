"""Manual, owner-confirmed first H7 window registration.

This is the only command allowed to append the first real H7 event, and it is
NOT a second door: it assembles the owner/evidence/guard inputs and then hands
them to :func:`options_researcher.h7_window_registration.register_window_real`
-- the single guarded code path that writes ``ledger/h7_forward``. The CLI never
calls ``ledger.append_event`` itself; every refusal (guard PASS, store binding,
report freshness, HEAD/tree identity, spec-sha triple match, append-time gate
recheck, VALID-EMPTY re-verify) is re-earned inside that one door.

It refuses to run without an explicit confirmation token, a valid empty real
ledger, the current 15-name receipt chain, a fresh restore receipt, owner
fields, independent review evidence, and a clean source tree. Do not run this
during the repair rollout.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import date
from pathlib import Path

from data.cache_runner import session_close_utc
from options_researcher import h7_activation_guard as guard
from options_researcher import h7_data_gate as data_gate_mod
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_source_health as source_health_mod
from options_researcher import h7_window_registration as registration
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_watch import validate_data_gate_receipt
from research.hashing import sha256_file
from research.receipts import load_receipt

CONFIRMATION = "ACTIVATE H7 FIRST WINDOW"
DEFAULT_SPEC_PATH = (Path(__file__).resolve().parents[1] / "docs" /
                     "superpowers" / "specs" /
                     "2026-07-19-h7-stage8-activation-spec.md")


def _json_object(path: Path) -> dict:
    value = json.loads(Path(path).read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _code_state() -> tuple[str, bool]:
    """Return (git HEAD, porcelain-clean) for the current checkout. The
    real-append path treats a moved HEAD or a dirty tree as a refusal, so this
    is the append-time identity that must equal the reviewed identity."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    porcelain = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True,
                               check=True).stdout.strip()
    return head, porcelain == ""


def _source_health_by_symbol(source: dict, names: list[str]) -> dict[str, bool]:
    """The REAL per-symbol health mapping straight from the source-health
    receipt -- never a ``{s: True}`` tautology. A name absent from the receipt
    or flagged unhealthy feeds the guard as unhealthy, so the guard's
    whole-universe check fails closed."""
    symbols = source.get("symbols", {})
    return {name: bool(symbols.get(name, {}).get("healthy", False))
            for name in names}


def _make_recheck(*, source: dict, data_gate: dict, source_path: Path,
                  data_gate_path: Path, names: list[str],
                  completed_session: str):
    """Build the append-time gate recheck handed to ``register_window_real``.

    It (a) re-validates the source-health and data-gate receipts by hash
    exactly as ``activate`` did (immutable evidence binding -- a receipt that
    changed between assembly and append refuses), (b) RE-RUNS the source-health
    and whole-universe data-gate evaluation for the pinned completed session,
    and (c) returns the bools + evidence ids (the receipt hashes) that
    ``register_window_real`` cross-checks against the evidence dict."""
    source_hash = source["receipt_hash"]
    data_gate_hash = data_gate["receipt_hash"]

    def recheck() -> dict:
        # (a) immutable evidence binding: the exact receipts assembled must
        # still hash to the same content now.
        source_now = load_receipt(source_path, expected_type="source_health")
        if source_now.get("receipt_hash") != source_hash:
            raise registration.ActivationRefused(
                "source-health receipt changed between assembly and append")
        data_now = validate_data_gate_receipt(
            data_gate_path, evaluation_session=completed_session, names=names)
        if data_now.get("receipt_hash") != data_gate_hash:
            raise registration.ActivationRefused(
                "data-gate receipt changed between assembly and append")

        # (b) re-run the gates for the pinned completed session.
        on = date.fromisoformat(completed_session)
        known_as_of = session_close_utc(completed_session)
        sh = source_health_mod.evaluate_health(
            requested_on=on, on=on, known_as_of=known_as_of,
            assertions=source_health_mod.load_assertions(), names=names)
        dg = data_gate_mod.evaluate(
            date.fromisoformat(data_gate["requested_run_date"]),
            scope=scope_identity())
        data_gate_go = (dg.get("whole_universe_verdict") == "GO"
                        and dg.get("evaluation_session") == completed_session)

        return {
            "source_health_all_healthy": bool(sh.get("activation_ready")),
            "data_gate_go": bool(data_gate_go),
            "source_health_evidence_id": source_hash,
            "data_gate_evidence_id": data_gate_hash,
        }

    return recheck


def activate(*, owner_path: Path, evidence_path: Path,
             source_health_path: Path, data_gate_path: Path,
             backup_restore_path: Path, completed_session: str,
             confirmation: str, spec_path: Path = DEFAULT_SPEC_PATH,
             forward_base: Path = REAL_FORWARD_STORE,
             code_state=_code_state) -> ledger.AppendResult:
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

    # Evidence key reconciliation: register_window_real's EVIDENCE_FIELDS name
    # the gate ids ``source_health_evidence_id`` / ``data_gate_evidence_id``;
    # bind them to the receipt hashes (which the append-time recheck returns).
    evidence = {
        **evidence,
        "source_health_evidence_id": source["receipt_hash"],
        "data_gate_evidence_id": data_gate["receipt_hash"],
        "scope_id": scope_identity()["scope_id"],
        "scope_hash": scope_identity()["scope_hash"],
        "source_health_receipt_hash": source["receipt_hash"],
        "data_gate_receipt_hash": data_gate["receipt_hash"],
        "backup_restore_receipt_hash": backup["receipt_hash"],
        "source_hash": data_gate["source_hash"],
        "config_hash": data_gate["config_hash"],
    }

    # The guard's data_gate_go/scope checks read data_gate_result["universe"];
    # the data-gate RECEIPT stores per-symbol records under "symbols", not a
    # "universe" list. Re-attach the validated whole-universe name list (already
    # proven by validate_data_gate_receipt to be go_count == len(names) for the
    # official scope) so the guard can confirm whole-universe GO. Not a
    # fabrication: names is the official scope and the receipt's go_count/scope
    # were re-hashed above.
    gate_result_for_guard = {**data_gate, "universe": sorted(names)}
    report = guard.activation_preconditions(
        forward_base=forward_base,
        source_health_by_symbol=_source_health_by_symbol(source, names),
        universe=tuple(names), data_gate_result=gate_result_for_guard,
        owner_inputs=owner, allow_real_readonly=True, strict=True,
        source_health_receipt=source, data_gate_receipt=data_gate,
        backup_restore_receipt=backup, completed_session=completed_session)

    spec_sha256 = sha256_file(Path(spec_path))
    recheck_gates = _make_recheck(
        source=source, data_gate=data_gate, source_path=Path(source_health_path),
        data_gate_path=Path(data_gate_path), names=names,
        completed_session=completed_session)

    # THE ONE DOOR. All ten refusals (including a re-check that the guard report
    # is a full store-bound fresh PASS) live inside register_window_real; the CLI
    # never appends to the forward store itself.
    result = registration.register_window_real(
        owner=owner, evidence=evidence, guard_report=report,
        spec_sha256=spec_sha256, spec_path=Path(spec_path),
        base_dir=forward_base, code_state=code_state,
        recheck_gates=recheck_gates)
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
    parser.add_argument("--activation-spec", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args(argv)
    try:
        result = activate(
            owner_path=args.owner, evidence_path=args.evidence,
            source_health_path=args.source_health_receipt,
            data_gate_path=args.data_gate_receipt,
            backup_restore_path=args.backup_restore_receipt,
            completed_session=args.completed_session,
            confirmation=args.confirm, spec_path=args.activation_spec)
    except Exception as exc:
        print(f"H7 ACTIVATION BLOCKED -- {type(exc).__name__}: {exc}")
        return 2
    print(f"H7 ACTIVATED FIRST WINDOW REGISTRATION seq={result.seq} "
          f"record_hash={result.record_hash}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Owner-confirmed first registration for h7-forward-schwab-v1.

This command only assembles and revalidates evidence before delegating to
options_researcher.h7_schwab_window_registration.register_window_real. It
never appends directly, never exposes a custom store or universe argument, and
does not run the post-registration quote-age arming gate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Callable
from pathlib import Path

from options_researcher import h7_activation_guard as guard
from options_researcher import h7_data_gate
from options_researcher import h7_schwab_window_registration as registration
from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from research.receipts import load_receipt, verify_receipt

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORWARD_STORE = REPO_ROOT / registration.SCHWAB_FORWARD_STORE
CONFIRMATION = "ACTIVATE H7 SCHWAB FIRST WINDOW"

OD3_NAMESPACE_COMMITMENT = (
    "future H7 paper observations MUST USE NEW NAMESPACE "
    "h7-forward-schwab-v1. The prior registration and event remain immutable. "
    "The chosen namespace must bind provider, cache manifest, final as-of "
    "boundary, scope identity, source-health receipt, and activation date "
    "before any new observation."
)
QUOTE_AGE_COMMITMENT = (
    "the BLOCKING gate + owner-typed threshold are a binding requirement of "
    "the H7 Schwab registration arc, triggered by the registration event "
    "itself — explicitly NOT satisfied by merging PR #71's caller of "
    "h7_schwab_data_gate.evaluate()."
)
QUOTE_AGE_EVIDENCE_CITATION = (
    "worst SELECTABLE quote age 0.61–10.38 min across 7 timestamped sessions "
    "(10-min block ⇒ 1/7 NO_GO; 15/20-min ⇒ 0/7; n=7, Reviewer-measured "
    "2026-08-28, not owner-typed)."
)
STARVATION_FIELD = registration.STARVATION_PREACCEPTANCE_FIELD


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


def validate_authorization_text(value: object) -> str:
    """Require the owner-typed OD-3 selection and packet row-7 commitment."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("authorization text must be non-empty owner-typed prose")
    missing = [
        fragment
        for fragment in (
            OD3_NAMESPACE_COMMITMENT,
            QUOTE_AGE_COMMITMENT,
            QUOTE_AGE_EVIDENCE_CITATION,
        )
        if fragment not in value
    ]
    if missing:
        raise ValueError(
            "authorization text is missing exact OD-3 or quote-age "
            f"commitment content: {missing!r}"
        )
    return value


def _validate_owner(owner: dict) -> None:
    if not isinstance(owner, dict):
        raise ValueError("owner inputs must be an object")
    missing = [
        field
        for field in (*registration.OWNER_FIELDS, STARVATION_FIELD)
        if owner.get(field) in (None, "")
    ]
    if missing:
        raise ValueError(
            f"owner inputs must be typed at use time; blank: {missing}"
        )
    validate_authorization_text(
        owner["H7_STAGE8_EXPLICIT_AUTHORIZATION"]
    )


def _validate_backup(
    backup: dict, *, completed_session: str
) -> None:
    if verify_receipt(backup):
        raise ValueError("backup/restore receipt is tampered")
    if (
        backup.get("receipt_type") != "backup_restore"
        or backup.get("scope") != scope_identity()
        or backup.get("completed_session") != completed_session
        or backup.get("verification", {}).get("ok") is not True
    ):
        raise ValueError("backup/restore receipt is stale or unverified")


def _validate_receipt_chain(
    *,
    source_health_path: Path,
    data_gate_path: Path,
    backup_restore_path: Path,
    completed_session: str,
) -> tuple[dict, dict, dict]:
    source = load_receipt(
        source_health_path, expected_type="source_health"
    )
    data = load_receipt(data_gate_path, expected_type="data_gate")
    backup = load_receipt(
        backup_restore_path, expected_type="backup_restore"
    )
    expected_symbols = h7_data_gate.validate_durable_receipt(data)
    current_scope = scope_identity()
    if (
        data.get("scope") != current_scope
        or expected_symbols != list(current_scope["symbols"])
        or data.get("evaluation_session") != completed_session
        or source.get("scope") != current_scope
        or source.get("evaluation_session") != completed_session
        or source.get("receipt_hash")
        != data.get("source_health_receipt_hash")
    ):
        raise ValueError(
            "source-health/data-gate receipt chain is stale or mismatched"
        )
    embedded_source = data.get("source_health_receipt_path")
    if (
        not isinstance(embedded_source, str)
        or Path(embedded_source).resolve(strict=False)
        != Path(source_health_path).resolve(strict=False)
    ):
        raise ValueError(
            "data gate is linked to a different source-health receipt"
        )
    _validate_backup(backup, completed_session=completed_session)
    return source, data, backup


def _assemble_evidence(
    *, raw: dict, source: dict, data: dict
) -> dict:
    return {
        **raw,
        "source_health_evidence_id": source["receipt_hash"],
        "data_gate_evidence_id": data["receipt_hash"],
        "data_gate_evidence_mode": registration.h7_schwab_data_gate.EVIDENCE_MODE,
        "source_health_receipt_hash": source["receipt_hash"],
        "data_gate_receipt": data,
        "data_gate_receipt_hash": data["receipt_hash"],
        "last_historical_session": data["evaluation_session"],
        "provider_identity": "schwab-read-only/v1",
        "cache_namespace": registration.CACHE_NAMESPACE,
    }


def _included_health(source: dict) -> bool:
    symbols = source.get("symbols")
    return isinstance(symbols, dict) and all(
        symbols.get(symbol, {}).get("healthy") is True
        for symbol in registration.REGISTERED_COHORT
    )


def _included_data_go(data: dict) -> bool:
    symbols = data.get("symbols")
    return isinstance(symbols, dict) and all(
        symbols.get(symbol, {}).get("verdict") == "GO"
        for symbol in registration.REGISTERED_COHORT
    )


def _make_recheck(
    *,
    source_health_path: Path,
    data_gate_path: Path,
    backup_restore_path: Path,
    completed_session: str,
    source_hash: str,
    data_hash: str,
) -> Callable[[], dict]:
    def recheck() -> dict:
        source, data, _ = _validate_receipt_chain(
            source_health_path=source_health_path,
            data_gate_path=data_gate_path,
            backup_restore_path=backup_restore_path,
            completed_session=completed_session,
        )
        if (
            source.get("receipt_hash") != source_hash
            or data.get("receipt_hash") != data_hash
        ):
            raise registration.ActivationRefused(
                "receipt hash changed between assembly and append"
            )
        return {
            "source_health_all_healthy": _included_health(source),
            "data_gate_go": _included_data_go(data),
            "source_health_evidence_id": source_hash,
            "data_gate_evidence_id": data_hash,
        }

    return recheck


def activate(
    *,
    owner: dict,
    evidence_path: Path,
    source_health_path: Path,
    data_gate_path: Path,
    backup_restore_path: Path,
    completed_session: str,
    confirmation: str,
    spec_path: Path,
    forward_base: Path = DEFAULT_FORWARD_STORE,
    code_state: Callable[[], tuple[str, bool]] = _code_state,
    max_report_age_s: int = registration.GUARD_REPORT_MAX_AGE_S,
):
    """Revalidate every input and delegate exactly once to the real door."""
    if confirmation != CONFIRMATION:
        raise ValueError(f"type exactly {CONFIRMATION!r} to activate")
    _validate_owner(owner)
    raw_evidence = _json_object(evidence_path)
    source, data, backup = _validate_receipt_chain(
        source_health_path=Path(source_health_path),
        data_gate_path=Path(data_gate_path),
        backup_restore_path=Path(backup_restore_path),
        completed_session=completed_session,
    )
    evidence = _assemble_evidence(
        raw=raw_evidence, source=source, data=data
    )
    spec_sha256 = sha256_file(Path(spec_path))
    if evidence.get("activation_spec_sha256") != spec_sha256:
        raise ValueError(
            "activation spec hash disagrees with reviewed evidence"
        )

    # Pre-delegation validation of WP-A/B/D/F and every builder refusal.
    registration.build_window_registration_event(
        owner=owner, evidence=evidence
    )

    current_scope = scope_identity()
    report = guard.activation_preconditions(
        forward_base=forward_base,
        source_health_by_symbol={
            symbol: bool(
                source.get("symbols", {})
                .get(symbol, {})
                .get("healthy", False)
            )
            for symbol in current_scope["symbols"]
        },
        universe=tuple(current_scope["symbols"]),
        data_gate_result=data,
        owner_inputs=owner,
        allow_real_readonly=True,
        strict=True,
        source_health_receipt=source,
        data_gate_receipt=data,
        backup_restore_receipt=backup,
        completed_session=completed_session,
        included=registration.REGISTERED_COHORT,
    )
    recheck_gates = _make_recheck(
        source_health_path=Path(source_health_path),
        data_gate_path=Path(data_gate_path),
        backup_restore_path=Path(backup_restore_path),
        completed_session=completed_session,
        source_hash=source["receipt_hash"],
        data_hash=data["receipt_hash"],
    )
    result = registration.register_window_real(
        owner=owner,
        evidence=evidence,
        guard_report=report,
        spec_sha256=spec_sha256,
        spec_path=spec_path,
        base_dir=forward_base,
        code_state=code_state,
        recheck_gates=recheck_gates,
        max_report_age_s=max_report_age_s,
    )
    if result.seq != 0:
        raise RuntimeError(
            "activation wrote something other than the first event"
        )
    return result


def _owner_from_args(args: argparse.Namespace) -> dict:
    return {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": (
            args.h7_stage8_explicit_authorization
        ),
        "WINDOW_START_DECISION_SESSION": (
            args.window_start_decision_session
        ),
        "WINDOW_DECISION_SESSION_COUNT": (
            args.window_decision_session_count
        ),
        "WINDOW_END_RULE_ACKNOWLEDGED": (
            args.window_end_rule_acknowledged
        ),
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": (
            args.window_minimum_three_calendar_months_per_lane_acknowledged
        ),
        "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH": (
            args.schwab_capture_lane_verified_through
        ),
        "SCHWAB_CAPTURE_COMMITMENT_THROUGH": (
            args.schwab_capture_commitment_through
        ),
        "SCHWAB_CONFIRMATION_EVIDENCE": (
            args.schwab_confirmation_evidence
        ),
        "SESSION_CHAIN_CONVENTION": args.session_chain_convention,
        "SCHWAB_MIN_LOSSES_FOR_VERDICT": (
            args.schwab_min_losses_for_verdict
        ),
        STARVATION_FIELD: args.schwab_starvation_risk_preacceptance,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument(
        "--source-health-receipt", type=Path, required=True
    )
    parser.add_argument("--data-gate-receipt", type=Path, required=True)
    parser.add_argument(
        "--backup-restore-receipt", type=Path, required=True
    )
    parser.add_argument("--completed-session", required=True)
    parser.add_argument("--activation-spec", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument(
        "--h7-stage8-explicit-authorization", required=True
    )
    parser.add_argument("--window-start-decision-session", required=True)
    parser.add_argument(
        "--window-decision-session-count", type=int, required=True
    )
    parser.add_argument("--window-end-rule-acknowledged", required=True)
    parser.add_argument(
        "--window-minimum-three-calendar-months-per-lane-acknowledged",
        required=True,
    )
    parser.add_argument(
        "--schwab-capture-lane-verified-through", required=True
    )
    parser.add_argument(
        "--schwab-capture-commitment-through", required=True
    )
    parser.add_argument("--schwab-confirmation-evidence", required=True)
    parser.add_argument("--session-chain-convention", required=True)
    parser.add_argument(
        "--schwab-min-losses-for-verdict", type=int, required=True
    )
    parser.add_argument(
        "--schwab-starvation-risk-preacceptance", required=True
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = activate(
            owner=_owner_from_args(args),
            evidence_path=args.evidence,
            source_health_path=args.source_health_receipt,
            data_gate_path=args.data_gate_receipt,
            backup_restore_path=args.backup_restore_receipt,
            completed_session=args.completed_session,
            confirmation=args.confirm,
            spec_path=args.activation_spec,
        )
    except Exception as exc:
        print(
            "H7 SCHWAB ACTIVATION BLOCKED -- "
            f"{type(exc).__name__}: {exc}"
        )
        return 2
    print(
        "H7 SCHWAB ACTIVATED FIRST WINDOW REGISTRATION "
        f"seq={result.seq} record_hash={result.record_hash}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Registration builder for the read-only Schwab H7 restart namespace.

BUILD-ONLY; SYNTHETIC-ONLY through :func:`register_window`; INACTIVE. This
module does not expose a CLI and does not activate either authority switch.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from pathlib import Path

import config
from data.cache_runner import session_close_utc
from options_researcher import h7_data_gate, h7_schwab_data_gate
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_window_registration as old_registration
from options_researcher.h7_paper_lifecycle import ActivationBoundaryError
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_scoring_identity import (
    REGISTRATION_CONTRACT_FIELD,
    REGISTRATION_HASH_FIELD,
    STAGE456_PARAMETER_NAMES,
    build_scoring_identity,
)
from research.hashing import (
    canonical_json,
    config_hash,
    cost_model_hash,
    sha256_file,
    sha256_hex,
)

NAMESPACE = "h7-forward-schwab-v1"
SCHWAB_FORWARD_STORE = Path("ledger/h7_forward_schwab")
CACHE_NAMESPACE = ".cache/schwab_chains/"
SESSION_CHAIN_CONVENTION = "preclose_snapshot_v1"

RegistrationInputError = old_registration.RegistrationInputError
WindowRuleError = old_registration.WindowRuleError
ActivationRefused = old_registration.ActivationRefused
GUARD_REPORT_MAX_AGE_S = old_registration.GUARD_REPORT_MAX_AGE_S

OWNER_FIELDS = (
    "H7_STAGE8_EXPLICIT_AUTHORIZATION",
    "WINDOW_START_DECISION_SESSION",
    "WINDOW_DECISION_SESSION_COUNT",
    "WINDOW_END_RULE_ACKNOWLEDGED",
    "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED",
    "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH",
    "SCHWAB_CAPTURE_COMMITMENT_THROUGH",
    "SCHWAB_CONFIRMATION_EVIDENCE",
    "SESSION_CHAIN_CONVENTION",
)
EVIDENCE_FIELDS = (
    "review_evidence",
    "activation_spec_sha256",
    "code_commit",
    "source_health_evidence_id",
    "data_gate_evidence_id",
    "data_gate_evidence_mode",
    "source_health_receipt_hash",
    "data_gate_receipt",
    "data_gate_receipt_hash",
    "last_historical_session",
    "last_historical_manifest_receipt_hash",
    "provider_identity",
    "cache_namespace",
    "feasibility_receipt",
    "feasibility_receipt_hash",
    "darwin_durability_verified",
    "pre_append_state",
)
FEASIBILITY_FIELDS = (
    "receipt_kind",
    "provenance",
    "lookback_start",
    "lookback_end",
    "stack_version",
    "code_sha",
    "config_hash",
    "universe_size",
    "window_sessions",
    "symbol_days",
    "full_stack_passes",
    "base_rate",
    "expected_entries",
    "receipt_hash",
)


def _require(mapping: dict, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if mapping.get(field) in (None, ""):
            raise RegistrationInputError(
                f"{label} input {field!r} is missing/None/empty; no default "
                "may be inferred"
            )


def _canonical_date(value: object, label: str) -> str:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as exc:
        raise RegistrationInputError(f"{label} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != str(value):
        raise RegistrationInputError(f"{label} must be canonical YYYY-MM-DD")
    return parsed.isoformat()


def _validate_feasibility(receipt: dict, claimed_hash: str) -> None:
    if not isinstance(receipt, dict):
        raise RegistrationInputError("feasibility_receipt must be an object")
    _require(receipt, FEASIBILITY_FIELDS, "feasibility receipt")
    embedded_hash = receipt["receipt_hash"]
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    computed = sha256_hex(canonical_json(unhashed))
    if embedded_hash != computed or claimed_hash != computed:
        raise RegistrationInputError(
            "feasibility receipt hash mismatch; payload may have been tampered"
        )
    if receipt["receipt_kind"] != "h7_schwab_feasibility/v1":
        raise RegistrationInputError("unexpected feasibility receipt kind")
    if receipt["provenance"] != "LLM/tool-computed":
        raise RegistrationInputError("feasibility provenance must be LLM/tool-computed")
    symbol_days = int(receipt["symbol_days"])
    passes = int(receipt["full_stack_passes"])
    sessions = int(receipt["window_sessions"])
    universe_size = int(receipt["universe_size"])
    if symbol_days <= 0 or not 0 <= passes <= symbol_days:
        raise RegistrationInputError("invalid feasibility counts")
    base_rate = passes / symbol_days
    expected = base_rate * sessions * universe_size
    if not math.isclose(float(receipt["base_rate"]), base_rate, rel_tol=1e-12):
        raise RegistrationInputError("feasibility base_rate arithmetic mismatch")
    if not math.isclose(float(receipt["expected_entries"]), expected, rel_tol=1e-12):
        raise RegistrationInputError("feasibility expected_entries arithmetic mismatch")


def _validate_data_gate_receipt(
    receipt: dict,
    claimed_hash: str,
    claimed_source_health_hash: str,
    universe_manifest: dict,
    historical_session: str,
) -> None:
    if not isinstance(receipt, dict):
        raise RegistrationInputError("data-gate receipt must be an object")
    try:
        verified_symbols = h7_data_gate.validate_durable_receipt(receipt)
    except (OSError, ValueError) as exc:
        raise RegistrationInputError(
            f"data-gate receipt failed durable verification: {exc}"
        ) from exc
    if receipt.get("receipt_hash") != claimed_hash:
        raise RegistrationInputError("data-gate receipt hash mismatch")
    if receipt.get("source_health_receipt_hash") != claimed_source_health_hash:
        raise RegistrationInputError(
            "data-gate receipt source-health hash disagrees with registration evidence"
        )
    if receipt.get("evidence_mode") != h7_schwab_data_gate.EVIDENCE_MODE:
        raise RegistrationInputError("data-gate receipt is not Schwab evidence")
    if receipt.get("evaluation_session") != historical_session:
        raise RegistrationInputError(
            "data-gate receipt session disagrees with registered history"
        )
    if (
        receipt.get("whole_universe_verdict") != "GO"
        or receipt.get("go_count") != len(universe_manifest["included"])
        or receipt.get("no_go_count") != 0
    ):
        raise RegistrationInputError(
            "data-gate receipt is not a whole-universe GO"
        )
    if receipt.get("config_hash") != config_hash():
        raise RegistrationInputError(
            "data-gate receipt config_hash disagrees with registration-time config"
        )
    if receipt.get("universe") != universe_manifest["included"]:
        raise RegistrationInputError(
            "data-gate receipt universe disagrees with registration cohort"
        )
    if verified_symbols != universe_manifest["included"]:
        raise RegistrationInputError(
            "verified data-gate symbols disagree with registration cohort"
        )
    scope = receipt.get("scope")
    if not isinstance(scope, dict) or (
        scope.get("scope_id") != universe_manifest["scope_id"]
        or scope.get("scope_hash") != universe_manifest["scope_hash"]
    ):
        raise RegistrationInputError(
            "data-gate receipt scope disagrees with registration cohort"
        )
    for field in ("schwab_manifest_hash", "schwab_capture_receipt_hash"):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value
        ):
            raise RegistrationInputError(
                f"data-gate receipt lacks a valid {field} binding"
            )


def build_window_registration_event(
    *,
    owner: dict,
    evidence: dict,
    universe_manifest: dict | None = None,
) -> dict:
    """Build, but never append, the Schwab namespace registration event."""
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")
    if evidence["data_gate_evidence_mode"] != h7_schwab_data_gate.EVIDENCE_MODE:
        raise RegistrationInputError(
            "data_gate_evidence_mode must equal "
            f"{h7_schwab_data_gate.EVIDENCE_MODE!r}"
        )
    if owner["SESSION_CHAIN_CONVENTION"] != SESSION_CHAIN_CONVENTION:
        raise RegistrationInputError(
            f"SESSION_CHAIN_CONVENTION must equal {SESSION_CHAIN_CONVENTION!r}"
        )
    if evidence["cache_namespace"] != CACHE_NAMESPACE:
        raise RegistrationInputError(
            f"cache_namespace must equal {CACHE_NAMESPACE!r}"
        )

    start = _canonical_date(owner["WINDOW_START_DECISION_SESSION"], "window start")
    count = int(owner["WINDOW_DECISION_SESSION_COUNT"])
    end = old_registration.derive_window_end(start, count)
    commitment = _canonical_date(
        owner["SCHWAB_CAPTURE_COMMITMENT_THROUGH"],
        "Schwab capture commitment",
    )
    if commitment < end:
        raise WindowRuleError(
            f"Schwab capture commitment only through {commitment}, short of "
            f"window end {end}"
        )
    verified_through = _canonical_date(
        owner["SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH"],
        "Schwab capture lane verified through",
    )
    historical_session = _canonical_date(
        evidence["last_historical_session"], "last historical session"
    )
    if verified_through != historical_session:
        raise RegistrationInputError(
            "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH must equal the bound last "
            "historical session"
        )

    feasibility = evidence["feasibility_receipt"]
    _validate_feasibility(feasibility, evidence["feasibility_receipt_hash"])
    # Adversarial review 2026-08-12 (finding B3): `d77f995` removed the only
    # binding between the feasibility receipt and the code/config that
    # produced it (a since-unsatisfiable exact-HEAD code_sha check). Bind the
    # receipt to the CONFIG that would be frozen by this registration instead
    # -- config_hash() is satisfiable today (the receipt need not have been
    # measured at the exact registering commit, only against the same
    # config.py) and catches the case that matters: the entry stack or its
    # parameters changing after the base rate was measured.
    if feasibility["config_hash"] != config_hash():
        raise RegistrationInputError(
            "feasibility receipt config_hash disagrees with the registering "
            "commit's config_hash(); the base rate was measured against a "
            "different config.py and must be re-measured before registration"
        )
    if int(feasibility["window_sessions"]) != count:
        raise RegistrationInputError(
            "feasibility window_sessions disagrees with registration window"
        )

    manifest = (
        old_registration.default_universe_manifest()
        if universe_manifest is None
        else universe_manifest
    )
    old_registration._validate_universe_manifest(manifest)
    scope = scope_identity()
    if manifest.get("scope_id") != scope["scope_id"] or manifest.get(
        "scope_hash"
    ) != scope["scope_hash"]:
        raise RegistrationInputError("universe manifest is not bound to H7 scope")
    # Exact name-list equality, not just cardinality: a same-size universe
    # swap (e.g. a name added and a different name removed between
    # measurement and registration) would pass a count-only check while
    # binding the old base rate to a different cohort.
    if feasibility.get("universe") != manifest["included"]:
        raise RegistrationInputError(
            "feasibility universe disagrees with registration cohort "
            "(name-list mismatch, not just count)"
        )
    if int(feasibility["universe_size"]) != len(manifest["included"]):
        raise RegistrationInputError(
            "feasibility universe_size disagrees with registration cohort"
        )
    _validate_data_gate_receipt(
        evidence["data_gate_receipt"],
        evidence["data_gate_receipt_hash"],
        evidence["source_health_receipt_hash"],
        manifest,
        historical_session,
    )
    if evidence["data_gate_evidence_id"] != evidence["data_gate_receipt_hash"]:
        raise RegistrationInputError(
            "data_gate_evidence_id must equal the durable receipt hash"
        )
    if (
        evidence["source_health_evidence_id"]
        != evidence["source_health_receipt_hash"]
    ):
        raise RegistrationInputError(
            "source_health_evidence_id must equal the durable receipt hash"
        )

    registered_cost_hash = cost_model_hash()
    stage456_parameters = {
        name: getattr(config, name) for name in STAGE456_PARAMETER_NAMES
    }
    scorer = {
        "module": "options_researcher.h7_forward_scoring",
        "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
        "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
    }
    scoring_identity = build_scoring_identity(
        stage456_parameters=stage456_parameters,
        scorer=scorer,
        cost_model_hash_value=registered_cost_hash,
    )
    payload = {
        "namespace": NAMESPACE,
        "owner_authorization": {field: owner[field] for field in OWNER_FIELDS},
        "review_evidence": evidence["review_evidence"],
        "activation_spec_sha256": evidence["activation_spec_sha256"],
        "code_commit": evidence["code_commit"],
        "provider": {
            "identity": evidence["provider_identity"],
            "access": "read_only",
            "cache_namespace": CACHE_NAMESPACE,
            "session_chain_convention": SESSION_CHAIN_CONVENTION,
            "confirmation_evidence": owner["SCHWAB_CONFIRMATION_EVIDENCE"],
            "capture_commitment_through": commitment,
        },
        "history": {
            "last_session": historical_session,
            "manifest_receipt_hash": evidence[
                "last_historical_manifest_receipt_hash"
            ],
        },
        "window": {
            "start_decision_session": start,
            "decision_session_count": count,
            "final_decision_session": end,
            "end_rule": "inclusive count of XNYS decision sessions from start",
            "three_month_proof": (
                f"{end} >= three-calendar-month anniversary of {start}"
            ),
        },
        "cohort_rule": "decision_session in registered window (immutable key)",
        "frozen": {
            "config_hash": config_hash(),
            "cost_model_hash": registered_cost_hash,
            "stage456_parameters": stage456_parameters,
            "scorer": scorer,
            REGISTRATION_CONTRACT_FIELD: scoring_identity.contract,
            REGISTRATION_HASH_FIELD: scoring_identity.identity_hash,
            "verdict_mapping": {
                "SURVIVED": "ci_above_zero",
                "REJECTED": "ci_below_zero",
                "INCONCLUSIVE": "insufficient_or_no_edge",
            },
            "survived_disclaimer": (
                "SURVIVED is not live-trading approval, not a profitability "
                "claim, and not validation"
            ),
        },
        "gates": {
            "source_health_evidence_id": evidence["source_health_evidence_id"],
            "data_gate_evidence_id": evidence["data_gate_evidence_id"],
            "source_health_receipt_hash": evidence["source_health_receipt_hash"],
            "data_gate_receipt_hash": evidence["data_gate_receipt_hash"],
            "scope_id": scope["scope_id"],
            "scope_hash": scope["scope_hash"],
        },
        "feasibility": {
            "receipt_hash": evidence["feasibility_receipt_hash"],
            "receipt": feasibility,
        },
        "universe": manifest,
        "darwin_durability_verified": bool(evidence["darwin_durability_verified"]),
        "pre_append_state": evidence["pre_append_state"],
    }
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": f"wr:{NAMESPACE}:{start}:{count}",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc(start).isoformat(),
        "evaluation_session": start,
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": payload,
    }


def _synthetic_base(base_dir: object) -> Path:
    if base_dir is None:
        raise ActivationBoundaryError("an explicit synthetic base_dir is required")
    base = Path(base_dir)
    resolved = base.resolve(strict=False)
    real = SCHWAB_FORWARD_STORE.resolve()
    if resolved == real or real in resolved.parents:
        raise ActivationBoundaryError(
            "the real Schwab H7 store is prohibited until owner registration"
        )
    return base


def register_window(
    *,
    owner: dict,
    evidence: dict,
    base_dir: object,
    universe_manifest: dict | None = None,
    clock=None,
) -> ledger.AppendResult:
    """Append only to an explicit synthetic VALID-EMPTY store."""
    base = _synthetic_base(base_dir)
    event = build_window_registration_event(
        owner=owner, evidence=evidence, universe_manifest=universe_manifest
    )
    return ledger.append_event(event, base_dir=base, clock=clock, expected_head=None)


def register_window_real(
    *,
    owner: dict,
    evidence: dict,
    guard_report,
    spec_sha256: str,
    spec_path: object,
    base_dir: object,
    code_state,
    recheck_gates,
    universe_manifest: dict | None = None,
    clock=None,
    now=None,
    max_report_age_s: int = GUARD_REPORT_MAX_AGE_S,
) -> ledger.AppendResult:
    """Owner-gated door for the first event; callers must earn every check."""
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")

    if not guard_report.ready:
        failed = [check.name for check in guard_report.checks if not check.ok]
        raise ActivationRefused(
            f"guard report is not a full PASS (failed: {failed or 'no checks'})"
        )
    base = Path(base_dir)
    bound = str(base.resolve(strict=False))
    if guard_report.forward_base != bound:
        raise ActivationRefused(
            "guard report is bound to a different target store"
        )
    if not guard_report.code_commit or not guard_report.built_at_utc:
        raise ActivationRefused("guard report carries no fresh code/build identity")

    head_now, tree_clean = code_state()
    if not tree_clean:
        raise ActivationRefused("working tree is dirty at append time")
    if head_now != guard_report.code_commit:
        raise ActivationRefused("HEAD moved since the guard report")
    if evidence["code_commit"] != head_now:
        raise ActivationRefused("evidence code_commit disagrees with HEAD")

    sha = str(spec_sha256)
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ActivationRefused("activation spec sha must be 64 lowercase hex")
    if evidence["activation_spec_sha256"] != sha:
        raise ActivationRefused("activation spec hash disagrees with evidence")
    spec_file = Path(spec_path)
    if not spec_file.is_file():
        raise ActivationRefused("activation spec file does not exist")
    if sha256_file(spec_file) != sha:
        raise ActivationRefused("activation spec file drifted after review")

    if now is None:
        now = datetime.now(timezone.utc)
    try:
        built = datetime.fromisoformat(guard_report.built_at_utc)
    except ValueError as exc:
        raise ActivationRefused("guard report timestamp is malformed") from exc
    age = (now - built).total_seconds()
    if age < 0 or age > max_report_age_s:
        raise ActivationRefused("guard report is stale or from the future")

    gates = recheck_gates()
    if gates.get("source_health_all_healthy") is not True:
        raise ActivationRefused("source-health recheck is not all-healthy")
    if gates.get("data_gate_go") is not True:
        raise ActivationRefused("data-gate recheck is not GO")
    for key in ("source_health_evidence_id", "data_gate_evidence_id"):
        if gates.get(key) != evidence[key]:
            raise ActivationRefused(f"append-time {key} disagrees with evidence")

    verified = ledger.verify(base_dir=base)
    if not (verified.valid and verified.empty):
        raise ActivationRefused(
            "target Schwab forward store is not VALID EMPTY at append time"
        )
    event = build_window_registration_event(
        owner=owner, evidence=evidence, universe_manifest=universe_manifest
    )
    return ledger.append_event(event, base_dir=base, clock=clock, expected_head=None)

"""Registration builder for the read-only Schwab H7 restart namespace.

BUILD-ONLY; SYNTHETIC-ONLY through :func:`register_window`; INACTIVE. This
module does not expose a CLI and does not activate either authority switch.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone
from os import PathLike
from pathlib import Path

import config
from data.cache_runner import session_close_utc
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
from tools.h7_schwab_feasibility import (
    RECEIPT_KIND as FEASIBILITY_RECEIPT_KIND,
)
from tools.h7_schwab_feasibility import STACK_VERSION as FEASIBILITY_STACK_VERSION

NAMESPACE = "h7-forward-schwab-v1"
SCHWAB_FORWARD_STORE = Path("ledger/h7_forward_schwab")
CACHE_NAMESPACE = ".cache/schwab_chains/"
SESSION_CHAIN_CONVENTION = "preclose_snapshot_v1"
FEASIBILITY_OWNER_DECISION_FIELD = "H7_SCHWAB_FEASIBILITY_DECISION"
FEASIBILITY_LOOKBACK_START = "2026-04-16"
FEASIBILITY_LOOKBACK_END = "2026-07-27"
FEASIBILITY_SESSION_COUNT = 70
FEASIBILITY_TOOL_LABEL = "cached-only read-only measurement; no verdict"

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
    FEASIBILITY_OWNER_DECISION_FIELD,
)
EVIDENCE_FIELDS = (
    "review_evidence",
    "activation_spec_sha256",
    "code_commit",
    "source_health_evidence_id",
    "data_gate_evidence_id",
    "source_health_receipt_hash",
    "data_gate_receipt_hash",
    "backup_restore_receipt_hash",
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
    "lookback_sessions",
    "stack_version",
    "code_sha",
    "config_hash",
    "tool_label",
    "universe",
    "universe_size",
    "window_sessions",
    "symbol_days",
    "full_stack_passes",
    "base_rate",
    "expected_entries",
    "error_count",
    "errors",
    "receipt_hash",
)


def _require(mapping: dict, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        if mapping.get(field) in (None, ""):
            raise RegistrationInputError(
                f"{label} input {field!r} is missing/None/empty; no default may be inferred"
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
    if receipt["receipt_kind"] != FEASIBILITY_RECEIPT_KIND:
        raise RegistrationInputError("unexpected feasibility receipt kind")
    if receipt["provenance"] != "LLM/tool-computed":
        raise RegistrationInputError("feasibility provenance must be LLM/tool-computed")
    if receipt["stack_version"] != FEASIBILITY_STACK_VERSION:
        raise RegistrationInputError("unexpected feasibility stack version")
    if receipt["tool_label"] != FEASIBILITY_TOOL_LABEL:
        raise RegistrationInputError("unexpected feasibility tool identity")
    if (
        receipt["lookback_start"] != FEASIBILITY_LOOKBACK_START
        or receipt["lookback_end"] != FEASIBILITY_LOOKBACK_END
        or int(receipt["lookback_sessions"]) != FEASIBILITY_SESSION_COUNT
        or int(receipt["window_sessions"]) != FEASIBILITY_SESSION_COUNT
    ):
        raise RegistrationInputError("feasibility receipt is not the canonical v1 study window")
    if receipt["config_hash"] != config_hash():
        raise RegistrationInputError("feasibility config_hash is not current")
    if int(receipt["error_count"]) != 0 or receipt["errors"] != []:
        raise RegistrationInputError("feasibility receipt contains measurement errors")
    canonical_universe = list(scope_identity()["symbols"])
    if receipt["universe"] != canonical_universe:
        raise RegistrationInputError("feasibility universe is not the canonical ordered H7 scope")
    symbol_days = int(receipt["symbol_days"])
    passes = int(receipt["full_stack_passes"])
    sessions = int(receipt["window_sessions"])
    universe_size = int(receipt["universe_size"])
    if universe_size != len(canonical_universe):
        raise RegistrationInputError("feasibility universe_size is not the canonical H7 scope size")
    if symbol_days != FEASIBILITY_SESSION_COUNT * len(canonical_universe):
        raise RegistrationInputError("feasibility denominator is not the canonical v1 census")
    if symbol_days <= 0 or not 0 <= passes <= symbol_days:
        raise RegistrationInputError("invalid feasibility counts")
    base_rate = passes / symbol_days
    expected = base_rate * sessions * universe_size
    if not math.isclose(float(receipt["base_rate"]), base_rate, rel_tol=1e-12):
        raise RegistrationInputError("feasibility base_rate arithmetic mismatch")
    if not math.isclose(float(receipt["expected_entries"]), expected, rel_tol=1e-12):
        raise RegistrationInputError("feasibility expected_entries arithmetic mismatch")
    minimum = 2 * config.MIN_LOSSES_FOR_VERDICT
    if expected < minimum:
        raise RegistrationInputError(
            f"feasibility expected_entries {expected} is below required {minimum}"
        )


def qualifying_feasibility_owner_line(receipt_hash: str) -> str:
    """Return the exact owner line required for a qualifying v1 receipt."""
    return (
        "REJECT OLD 3/1050 STARVATION-RISK PATH; BIND "
        f"{NAMESPACE} TO QUALIFYING FEASIBILITY RECEIPT {receipt_hash}"
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
    if owner["SESSION_CHAIN_CONVENTION"] != SESSION_CHAIN_CONVENTION:
        raise RegistrationInputError(
            f"SESSION_CHAIN_CONVENTION must equal {SESSION_CHAIN_CONVENTION!r}"
        )
    if evidence["cache_namespace"] != CACHE_NAMESPACE:
        raise RegistrationInputError(f"cache_namespace must equal {CACHE_NAMESPACE!r}")

    start = _canonical_date(owner["WINDOW_START_DECISION_SESSION"], "window start")
    count = int(owner["WINDOW_DECISION_SESSION_COUNT"])
    end = old_registration.derive_window_end(start, count)
    commitment = _canonical_date(
        owner["SCHWAB_CAPTURE_COMMITMENT_THROUGH"],
        "Schwab capture commitment",
    )
    if commitment < end:
        raise WindowRuleError(
            f"Schwab capture commitment only through {commitment}, short of window end {end}"
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
            "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH must equal the bound last historical session"
        )

    feasibility = evidence["feasibility_receipt"]
    _validate_feasibility(feasibility, evidence["feasibility_receipt_hash"])
    required_owner_line = qualifying_feasibility_owner_line(evidence["feasibility_receipt_hash"])
    if owner[FEASIBILITY_OWNER_DECISION_FIELD] != required_owner_line:
        raise RegistrationInputError(
            f"{FEASIBILITY_OWNER_DECISION_FIELD} must exactly bind the "
            "qualifying v1 feasibility receipt"
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
    if (
        manifest.get("scope_id") != scope["scope_id"]
        or manifest.get("scope_hash") != scope["scope_hash"]
    ):
        raise RegistrationInputError("universe manifest is not bound to H7 scope")
    if manifest.get("included") != feasibility["universe"]:
        raise RegistrationInputError("feasibility universe disagrees with registration cohort")

    registered_cost_hash = cost_model_hash()
    stage456_parameters = {name: getattr(config, name) for name in STAGE456_PARAMETER_NAMES}
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
            "manifest_receipt_hash": evidence["last_historical_manifest_receipt_hash"],
        },
        "window": {
            "start_decision_session": start,
            "decision_session_count": count,
            "final_decision_session": end,
            "end_rule": "inclusive count of XNYS decision sessions from start",
            "three_month_proof": (f"{end} >= three-calendar-month anniversary of {start}"),
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
            "backup_restore_receipt_hash": evidence["backup_restore_receipt_hash"],
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


def _synthetic_base(base_dir: str | PathLike[str] | None) -> Path:
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
    base_dir: str | PathLike[str] | None,
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
    spec_path: str | PathLike[str],
    base_dir: str | PathLike[str],
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
        raise ActivationRefused("guard report is bound to a different target store")
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
    if gates.get("backup_restore_receipt_hash") != evidence["backup_restore_receipt_hash"]:
        raise ActivationRefused("append-time backup_restore_receipt_hash disagrees with evidence")

    verified = ledger.verify(base_dir=base)
    if not (verified.valid and verified.empty):
        raise ActivationRefused("target Schwab forward store is not VALID EMPTY at append time")
    event = build_window_registration_event(
        owner=owner, evidence=evidence, universe_manifest=universe_manifest
    )
    return ledger.append_event(event, base_dir=base, clock=clock, expected_head=None)

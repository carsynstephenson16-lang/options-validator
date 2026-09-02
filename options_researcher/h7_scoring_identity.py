"""Versioned authority identity for H7 real-store scoring.

The live scoring door must bind only the computation frozen in sequence-zero,
not every unrelated uppercase presentation/plumbing constant in ``config.py``.
Legacy registrations derive this identity from their existing frozen payload.
Future registrations persist the contract name and derived hash alongside the
same frozen fields.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass

import config
from research.hashing import canonical_json, cost_model_hash, sha256_hex

SCORING_IDENTITY_CONTRACT = "h7_scoring_identity/v1"
REGISTRATION_CONTRACT_FIELD = "scoring_identity_contract"
REGISTRATION_HASH_FIELD = "scoring_identity_hash"
FROZEN_SCORER_MODULE = "options_researcher.h7_forward_scoring"

# This is the complete Stage 4/5/6 surface persisted in the real seq-0
# registration. Contract v1 is intentionally explicit and must never silently
# grow; a changed surface requires a new versioned contract.
STAGE456_PARAMETER_NAMES = (
    "H7_FORWARD_CONTRACTS",
    "COMMISSION_PER_CONTRACT",
    "SLIPPAGE_HAIRCUT",
    "H7_LANE_PRIORITY",
    "H7_LONG_DELTA_BAND",
    "H7_LONG_DTE_BAND",
    "H7_SPREAD_LONG_DELTA",
    "H7_SPREAD_SHORT_DELTA",
    "H7_LONG_TP_PCT",
    "H7_SPREAD_TP_FRAC_MAX",
    "H7_CLOSE_AT_DTE",
    "H7_DELTA_TOLERANCE",
    "H7C_SHORT_DELTA_MAX",
    "H7C_DTE_BAND",
    "H7C_CREDIT_FLOOR_FRAC",
    "H7C_WIDTH_FRAC_OF_SPOT",
    "H7C_TP_FRAC",
    "H7C_STOP_CREDIT_MULT",
    "H7C_MAX_CONCURRENT",
    "H7C_CLOSE_AT_DTE",
    "H7C_CLOSE_BEFORE_EARNINGS",
    "H7C_TIEBREAK",
    "H7_MONTHLY_AT_RISK",
    "H7_MAX_OPEN_PER_UNDERLYING",
    "H7_ADMIT_MIN_CONTRACTS",
    "H7_ADMIT_MAX_SPREAD_PCT",
    "H7_EARNINGS_BAN_SESSIONS",
    "H7_EARNINGS_POST_REPORT_GRACE_D",
    "H7_MAX_HOLD_BUFFER_D",
    "MIN_LOSSES_FOR_VERDICT",
    "BOOTSTRAP_SAMPLES",
)

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class ScoringIdentityError(ValueError):
    """A registered or runtime scoring identity is absent or malformed."""


@dataclass(frozen=True)
class H7ScoringIdentity:
    """Canonical identity material safe to retain in a scoring capability."""

    contract: str
    canonical_surface: str
    identity_hash: str


def _positive_int(value: object, label: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ScoringIdentityError(f"{label} must be an integer >= {minimum}")
    return value


def _normalize(value: object, label: str) -> object:
    """Canonical JSON round-trip, recursively normalizing tuples to lists."""
    try:
        return json.loads(canonical_json(value))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ScoringIdentityError(f"{label} is not canonical JSON") from exc


def build_scoring_identity(
    *,
    stage456_parameters: Mapping[str, object],
    scorer: Mapping[str, object],
    cost_model_hash_value: object,
) -> H7ScoringIdentity:
    """Build contract v1 from the exact seq-0 frozen scoring surface."""
    if not isinstance(stage456_parameters, Mapping):
        raise ScoringIdentityError("stage456_parameters must be an object")
    expected_names = set(STAGE456_PARAMETER_NAMES)
    actual_names = set(stage456_parameters)
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    if missing or extra:
        raise ScoringIdentityError(
            "stage456_parameters do not match h7_scoring_identity/v1: "
            f"missing={missing!r} extra={extra!r}"
        )
    if not isinstance(scorer, Mapping):
        raise ScoringIdentityError("scorer must be an object")
    expected_scorer_keys = {
        "module",
        "bootstrap_samples",
        "min_losses_for_verdict",
    }
    actual_scorer_keys = set(scorer)
    if actual_scorer_keys != expected_scorer_keys:
        raise ScoringIdentityError(
            "scorer does not match h7_scoring_identity/v1: "
            f"missing={sorted(expected_scorer_keys - actual_scorer_keys)!r} "
            f"extra={sorted(actual_scorer_keys - expected_scorer_keys)!r}"
        )
    module = scorer.get("module")
    if not isinstance(module, str) or not module:
        raise ScoringIdentityError("scorer module must be non-empty text")
    min_losses = _positive_int(
        scorer.get("min_losses_for_verdict"),
        "scorer min_losses_for_verdict",
        allow_zero=True,
    )
    bootstrap_samples = _positive_int(scorer.get("bootstrap_samples"), "scorer bootstrap_samples")
    if stage456_parameters["MIN_LOSSES_FOR_VERDICT"] != min_losses:
        raise ScoringIdentityError("stage/scorer MIN_LOSSES_FOR_VERDICT values disagree")
    if stage456_parameters["BOOTSTRAP_SAMPLES"] != bootstrap_samples:
        raise ScoringIdentityError("stage/scorer BOOTSTRAP_SAMPLES values disagree")
    if (
        not isinstance(cost_model_hash_value, str)
        or _SHA256_HEX.fullmatch(cost_model_hash_value) is None
    ):
        raise ScoringIdentityError("cost_model_hash must be lowercase SHA-256")

    surface = {
        "contract": SCORING_IDENTITY_CONTRACT,
        "stage456_parameters": {
            name: stage456_parameters[name] for name in STAGE456_PARAMETER_NAMES
        },
        "scorer": {
            "module": module,
            "min_losses_for_verdict": min_losses,
            "bootstrap_samples": bootstrap_samples,
        },
        "cost_model_hash": cost_model_hash_value,
    }
    normalized = _normalize(surface, "scoring identity")
    canonical_surface = canonical_json(normalized)
    return H7ScoringIdentity(
        contract=SCORING_IDENTITY_CONTRACT,
        canonical_surface=canonical_surface,
        identity_hash=sha256_hex(canonical_surface),
    )


def registered_scoring_identity(
    frozen: Mapping[str, object],
) -> H7ScoringIdentity:
    """Derive and verify a legacy or future seq-0 frozen identity."""
    if not isinstance(frozen, Mapping):
        raise ScoringIdentityError("registered frozen block must be an object")
    derived = build_scoring_identity(
        stage456_parameters=frozen.get("stage456_parameters"),  # type: ignore[arg-type]
        scorer=frozen.get("scorer"),  # type: ignore[arg-type]
        cost_model_hash_value=frozen.get("cost_model_hash"),
    )
    has_contract = REGISTRATION_CONTRACT_FIELD in frozen
    has_hash = REGISTRATION_HASH_FIELD in frozen
    if has_contract != has_hash:
        raise ScoringIdentityError("registered scoring identity contract/hash must appear together")
    if has_contract:
        if frozen.get(REGISTRATION_CONTRACT_FIELD) != derived.contract:
            raise ScoringIdentityError("registered scoring identity contract is unsupported")
        if frozen.get(REGISTRATION_HASH_FIELD) != derived.identity_hash:
            raise ScoringIdentityError(
                "registered scoring identity hash disagrees with frozen fields"
            )
    return derived


def runtime_scoring_identity(
    *,
    min_losses_for_verdict: int | None,
    cost_model_hash_value: str | None = None,
) -> H7ScoringIdentity:
    """Derive the live computation identity without global config provenance.

    ``min_losses_for_verdict`` is REQUIRED and comes from the registered
    event's scorer block. Round-1 finding F3: an optional argument falling
    back to ``config.MIN_LOSSES_FOR_VERDICT`` silently reintroduces exactly
    the contradiction WP-F exists to close (a window registered at bar 7
    scored against the global bar 10), so there is no fallback -- omitting the
    argument is a TypeError and passing ``None`` is a typed refusal.
    """
    if min_losses_for_verdict is None:
        raise ScoringIdentityError(
            "runtime scoring identity requires the registered "
            "min_losses_for_verdict; there is no config fallback"
        )
    stage = {name: getattr(config, name) for name in STAGE456_PARAMETER_NAMES}
    stage["MIN_LOSSES_FOR_VERDICT"] = _positive_int(
        min_losses_for_verdict,
        "runtime min_losses_for_verdict",
        allow_zero=True,
    )
    scorer = {
        "module": FROZEN_SCORER_MODULE,
        "min_losses_for_verdict": stage["MIN_LOSSES_FOR_VERDICT"],
        "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
    }
    return build_scoring_identity(
        stage456_parameters=stage,
        scorer=scorer,
        cost_model_hash_value=(
            cost_model_hash() if cost_model_hash_value is None else cost_model_hash_value
        ),
    )

"""Stage 8 window_registration builder + synthetic-store append.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. The real first append happens only in
a future owner-authorized Stage-8 opening arc (readiness packet §5 steps
5-9) after external review -- never from this module's tests and never via
any CLI (none exists here on purpose).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import config
from data.cache_runner import session_close_utc, trading_days
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ActivationBoundaryError,
)
from research.hashing import config_hash, cost_model_hash

# The exact owner-typed inputs required before a window_registration event
# can be built. Every field is mandatory and None/"" is refused -- no default
# may be inferred for an owner-authorized, pre-commitment value.
OWNER_FIELDS = (
    "H7_STAGE8_EXPLICIT_AUTHORIZATION",
    "WINDOW_START_DECISION_SESSION",
    "WINDOW_DECISION_SESSION_COUNT",
    "WINDOW_END_RULE_ACKNOWLEDGED",
    "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED",
    "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH",
    "THETADATA_CONFIRMATION_EVIDENCE",
)
EVIDENCE_FIELDS = (
    "review_evidence",
    "activation_spec_sha256",
    "code_commit",
    "source_health_evidence_id",
    "data_gate_evidence_id",
    "darwin_durability_verified",
    "pre_append_state",
)
# The frozen Stage 4/5/6 parameter surface that a window_registration event
# commits to verbatim (in addition to config_hash/cost_model_hash, which
# already cover the full config module -- these are named explicitly so the
# payload is legible without cross-referencing config.py).
STAGE456_PARAMETER_NAMES = (
    "H7_FORWARD_CONTRACTS", "COMMISSION_PER_CONTRACT", "SLIPPAGE_HAIRCUT",
    "H7_LANE_PRIORITY", "H7_LONG_DELTA_BAND", "H7_LONG_DTE_BAND",
    "H7_SPREAD_LONG_DELTA", "H7_SPREAD_SHORT_DELTA", "H7_LONG_TP_PCT",
    "H7_SPREAD_TP_FRAC_MAX", "H7_CLOSE_AT_DTE", "H7_DELTA_TOLERANCE",
    "H7C_SHORT_DELTA_MAX", "H7C_DTE_BAND", "H7C_CREDIT_FLOOR_FRAC",
    "H7C_WIDTH_FRAC_OF_SPOT", "H7C_TP_FRAC", "H7C_STOP_CREDIT_MULT",
    "H7C_MAX_CONCURRENT", "H7C_CLOSE_AT_DTE", "H7C_CLOSE_BEFORE_EARNINGS",
    "H7C_TIEBREAK", "H7_MONTHLY_AT_RISK", "H7_MAX_OPEN_PER_UNDERLYING",
    "H7_ADMIT_MIN_CONTRACTS", "H7_ADMIT_MAX_SPREAD_PCT",
    "H7_EARNINGS_BAN_SESSIONS", "H7_EARNINGS_POST_REPORT_GRACE_D",
    "MIN_LOSSES_FOR_VERDICT", "BOOTSTRAP_SAMPLES",
)


class RegistrationInputError(ValueError):
    """An owner/evidence input is missing, None, empty, or malformed."""


class WindowRuleError(ValueError):
    """The window arithmetic violates a registered rule (three-calendar-month
    minimum, or paid ThetaData coverage not reaching the window end)."""


def _require(mapping: dict, fields: tuple, label: str) -> None:
    for field in fields:
        if mapping.get(field) in (None, ""):
            raise RegistrationInputError(
                f"{label} input {field!r} is missing/None/empty; no default "
                "may be inferred for an owner-authorized pre-commitment value")


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    days_in_month = [31, 29 if leap else 28, 31, 30, 31, 30,
                     31, 31, 30, 31, 30, 31]
    return date(year, month, min(d.day, days_in_month[month - 1]))


def derive_window_end(start_iso: str, session_count: int) -> str:
    """The final decision session of an N-session window starting at
    ``start_iso`` (inclusive of the start session). Refuses a window whose
    final session lands before the three-calendar-month anniversary of the
    start -- the registered per-lane minimum-duration rule."""
    horizon = trading_days(start_iso, "2100-01-01")[:session_count]
    if len(horizon) < session_count:
        raise WindowRuleError(
            "the XNYS trading calendar cannot supply the requested "
            f"{session_count} decision sessions from {start_iso}")
    end_iso = horizon[-1]
    anniversary = _add_months(date.fromisoformat(start_iso), 3)
    if date.fromisoformat(end_iso) < anniversary:
        raise WindowRuleError(
            f"final decision session {end_iso} precedes the three-calendar-"
            f"month anniversary {anniversary.isoformat()} of start "
            f"{start_iso}; a shorter session count is invalid -- "
            "the window must span at least three calendar months per lane")
    return end_iso


def build_window_registration_event(*, owner: dict, evidence: dict) -> dict:
    """Build (never append) the Stage-8 window_registration event. Every
    owner/evidence input is validated present; the window arithmetic is
    re-derived (never trusted from owner ack strings) and checked against
    the three-calendar-month rule and paid ThetaData coverage."""
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")

    start = owner["WINDOW_START_DECISION_SESSION"]
    count = int(owner["WINDOW_DECISION_SESSION_COUNT"])
    end = derive_window_end(start, count)

    coverage_through = str(owner["THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH"])
    if coverage_through < end:
        raise WindowRuleError(
            f"paid ThetaData daily EOD coverage confirmed only through "
            f"{coverage_through}, short of window end {end}; renew coverage "
            "before registering")

    payload = {
        "owner_authorization": {field: owner[field] for field in OWNER_FIELDS},
        "review_evidence": evidence["review_evidence"],
        "activation_spec_sha256": evidence["activation_spec_sha256"],
        "code_commit": evidence["code_commit"],
        "window": {
            "start_decision_session": start,
            "decision_session_count": count,
            "final_decision_session": end,
            "end_rule": "inclusive count of XNYS decision sessions from start",
            "three_month_proof": (
                f"{end} >= three-calendar-month anniversary of {start}"),
        },
        "cohort_rule": "decision_session in registered window (immutable key)",
        "frozen": {
            "config_hash": config_hash(),
            "cost_model_hash": cost_model_hash(),
            "stage456_parameters": {
                name: getattr(config, name) for name in STAGE456_PARAMETER_NAMES
            },
            "scorer": {
                "module": "options_researcher.h7_forward_scoring",
                "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
                "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
            },
            "verdict_mapping": {
                "SURVIVED": "ci_above_zero",
                "REJECTED": "ci_below_zero",
                "INCONCLUSIVE": "insufficient_or_no_edge",
            },
            "survived_disclaimer": (
                "SURVIVED is not live-trading approval, not a profitability "
                "claim, and not validation"),
        },
        "gates": {
            "source_health_evidence_id": evidence["source_health_evidence_id"],
            "data_gate_evidence_id": evidence["data_gate_evidence_id"],
            "scope_id": evidence.get("scope_id"),
            "scope_hash": evidence.get("scope_hash"),
            "source_health_receipt_hash": evidence.get(
                "source_health_receipt_hash"),
            "data_gate_receipt_hash": evidence.get("data_gate_receipt_hash"),
            "backup_restore_receipt_hash": evidence.get(
                "backup_restore_receipt_hash"),
            "source_hash": evidence.get("source_hash"),
            "config_hash": evidence.get("config_hash", config_hash()),
        },
        "coverage_evidence": owner["THETADATA_CONFIRMATION_EVIDENCE"],
        "darwin_durability_verified": bool(evidence["darwin_durability_verified"]),
        "pre_append_state": evidence["pre_append_state"],
    }
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": f"wr:{start}:{count}",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc(start).isoformat(),
        "evaluation_session": start,
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": payload,
    }


def _synthetic_base(base_dir) -> Path:
    if base_dir is None:
        raise ActivationBoundaryError("an explicit synthetic base_dir is required")
    base = Path(base_dir)
    resolved = base.resolve(strict=False)
    real = REAL_FORWARD_STORE.resolve()
    if resolved == real or real in resolved.parents:
        raise ActivationBoundaryError(
            "the real H7 forward store is prohibited until Stage 8 activation"
        )
    return base


def register_window(*, owner: dict, evidence: dict, base_dir,
                    clock=None) -> ledger.AppendResult:
    """Append the window_registration event as the ledger's FIRST event.
    Synthetic stores only -- refuses the real forward store and refuses a
    ledger that already has a verified tip (``expected_head=None`` demands
    an empty chain). Returns the ledger's own AppendResult unchanged:
    ``seq`` is the ledger's 0-based record position (0 for the first event
    -- one seq semantic in this codebase, not two)."""
    base = _synthetic_base(base_dir)
    event = build_window_registration_event(owner=owner, evidence=evidence)
    return ledger.append_event(event, base_dir=base, clock=clock,
                               expected_head=None)

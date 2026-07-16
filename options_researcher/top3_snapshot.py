"""Pure, paper-only Top-3 candidate snapshots.

This module deliberately does not select, score, persist, or render candidates.
It converts one already-assembled dashboard card into a serializable record with
three independent questions:

* are the date-sensitive inputs aligned to the card's chain session?
* does the structure fit its own lane-specific portfolio policy?
* what is the separate status of any qualitative research annotation?

Research status never changes ``rank_eligible``.  In particular, a cash-secured
put is not rejected by the defined-risk cap used by a tactical long call: it is
an equity-side assignment decision with an explicit capital requirement.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Mapping, Sequence

import config

ELIGIBLE = "ELIGIBLE"
WATCH = "WATCH"
PLAN_ONLY = "PLAN_ONLY"
DATA_BLOCKED = "DATA_BLOCKED"

_COVERED_CALL_LANES = frozenset({"cc", "covered_call"})
_KNOWN_RESEARCH_STATUSES = frozenset(
    {"NOT_ASSESSED", "COMPLETE", "STALE", "INSUFFICIENT"}
)


def _canonical_date(value: object) -> str | None:
    """Return a canonical ISO date, or None without coercing unknown values."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _finite_positive(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _finite_nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def candidate_id(section: Mapping[str, object], group: Mapping[str, object],
                 card: Mapping[str, object]) -> str:
    """Stable identity for one card, independent of narration or score.

    Strike is fixed to cents so an integer strike and an equivalent float share
    an ID.  The current scanner's lane key is the group ``kind``.
    """
    symbol = section.get("symbol")
    lane = group.get("kind")
    expiry = _canonical_date(card.get("expiry"))
    strike = _finite_positive(card.get("strike"))
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("candidate symbol is required")
    if not isinstance(lane, str) or not lane.strip():
        raise ValueError("candidate lane is required")
    if expiry is None:
        raise ValueError("candidate expiry must be canonical YYYY-MM-DD")
    if strike is None:
        raise ValueError("candidate strike must be a positive finite number")
    return f"{symbol.upper()}:{lane}:{expiry}:{strike:.2f}"


def integrity_status(section: Mapping[str, object]) -> dict[str, object]:
    """Classify exact chain/feature-session integrity without reading disk."""
    reasons: list[str] = []
    as_of = _canonical_date(section.get("as_of"))
    if as_of is None:
        reasons.append("SECTION_AS_OF_INVALID")

    features_as_of = _canonical_date(section.get("features_as_of"))
    if features_as_of is None:
        reasons.append("FEATURES_AS_OF_INVALID")
    elif as_of is not None and features_as_of != as_of:
        reasons.append("FEATURES_SESSION_MISMATCH")

    stale = section.get("features_stale")
    if stale is not False:
        reasons.append("FEATURES_STALE" if stale is True
                       else "FEATURES_STALENESS_UNKNOWN")

    return {
        "status": DATA_BLOCKED if reasons else ELIGIBLE,
        "reason_codes": reasons,
        "as_of": as_of,
        "features_as_of": features_as_of,
    }


def _policy(status: str, reasons: list[str], *, assignment_capital: float | None = None,
            max_loss: float | None = None) -> dict[str, object]:
    out: dict[str, object] = {"status": status, "reason_codes": reasons}
    if assignment_capital is not None:
        out["assignment_capital"] = assignment_capital
    if max_loss is not None:
        out["max_loss"] = max_loss
    return out


def lane_policy_status(section: Mapping[str, object], group: Mapping[str, object],
                       card: Mapping[str, object], *,
                       csp_open_count: int | None = None,
                       covered_shares: int | None = None,
                       leaps_held: bool | None = None,
                       assignment_capital_authorized: bool | None = None
                       ) -> dict[str, object]:
    """Apply only the existing lane-specific policy facts.

    ``csp_open_count``, ``covered_shares``, ``leaps_held``, and
    ``assignment_capital_authorized`` are explicit caller-provided portfolio
    facts. Omitting any fact needed by a lane does not fabricate a green
    result; it returns WATCH. No branch applies ``MAX_LOSS_PER_TRADE`` to a
    short put.
    """
    lane = group.get("kind")
    if not isinstance(lane, str):
        return _policy(WATCH, ["LANE_UNKNOWN"])

    if lane == "long_call":
        cost = _finite_positive(card.get("cost"))
        if cost is None:
            return _policy(WATCH, ["LONG_CALL_MAX_LOSS_UNKNOWN"])
        if cost > config.MAX_LOSS_PER_TRADE:
            return _policy(PLAN_ONLY, ["LONG_CALL_MAX_LOSS_EXCEEDS_CAP"],
                           max_loss=cost)
        return _policy(ELIGIBLE, [], max_loss=cost)

    if lane == "put":
        symbol = section.get("symbol")
        strike = _finite_positive(card.get("strike"))
        reasons: list[str] = []
        if not isinstance(symbol, str) or symbol.upper() not in config.H4_CSP_NAMES:
            reasons.append("CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES")
        if strike is None:
            reasons.append("CSP_ASSIGNMENT_CAPITAL_UNKNOWN")

        count = _finite_nonnegative_int(csp_open_count)
        if csp_open_count is None:
            reasons.append("CSP_OPEN_COUNT_UNKNOWN")
        elif count is None:
            reasons.append("CSP_OPEN_COUNT_INVALID")
        elif count >= config.H4_CSP_MAX_POSITIONS:
            reasons.append("CSP_SLOT_FULL")

        if assignment_capital_authorized is None:
            reasons.append("CSP_ASSIGNMENT_CAPITAL_UNCONFIRMED")
        elif assignment_capital_authorized is False:
            reasons.append("CSP_ASSIGNMENT_CAPITAL_NOT_AUTHORIZED")
        elif assignment_capital_authorized is not True:
            reasons.append("CSP_ASSIGNMENT_CAPITAL_AUTHORIZATION_INVALID")

        assignment_capital = strike * 100.0 if strike is not None else None
        if any(code in reasons for code in (
                "CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES", "CSP_SLOT_FULL",
                "CSP_ASSIGNMENT_CAPITAL_NOT_AUTHORIZED")):
            return _policy(PLAN_ONLY, reasons,
                           assignment_capital=assignment_capital)
        if reasons:
            return _policy(WATCH, reasons, assignment_capital=assignment_capital)
        return _policy(ELIGIBLE, [], assignment_capital=assignment_capital)

    if lane == "pmcc":
        preview = card.get("preview", group.get("preview", False))
        if preview is True:
            return _policy(PLAN_ONLY, ["PMCC_PREVIEW_REQUIRES_LEAPS"])
        if preview is not False:
            return _policy(WATCH, ["PMCC_PREVIEW_STATUS_UNKNOWN"])
        if leaps_held is None:
            return _policy(WATCH, ["PMCC_LEAPS_COVERAGE_UNKNOWN"])
        if leaps_held is False:
            return _policy(PLAN_ONLY, ["PMCC_LEAPS_NOT_HELD"])
        if leaps_held is True:
            return _policy(ELIGIBLE, [])
        return _policy(WATCH, ["PMCC_LEAPS_COVERAGE_UNKNOWN"])

    if lane in _COVERED_CALL_LANES:
        shares = _finite_nonnegative_int(covered_shares)
        if covered_shares is None:
            return _policy(WATCH, ["COVERED_CALL_COVERAGE_UNKNOWN"])
        if shares is None:
            return _policy(WATCH, ["COVERED_CALL_COVERAGE_INVALID"])
        if shares < 100:
            return _policy(PLAN_ONLY, ["COVERED_CALL_NOT_FULLY_COVERED"])
        return _policy(ELIGIBLE, [])

    return _policy(WATCH, ["LANE_POLICY_NOT_MODELED"])


def research_status(status: str = "NOT_ASSESSED", *,
                    reason_codes: Sequence[str] = ()) -> dict[str, object]:
    """Return a research annotation only; it deliberately has no score field."""
    if status not in _KNOWN_RESEARCH_STATUSES:
        return {"status": "NOT_ASSESSED",
                "reason_codes": ["RESEARCH_STATUS_INVALID"]}
    return {"status": status, "reason_codes": list(reason_codes)}


def snapshot_candidate(section: Mapping[str, object], group: Mapping[str, object],
                       card: Mapping[str, object], *,
                       csp_open_count: int | None = None,
                       covered_shares: int | None = None,
                       leaps_held: bool | None = None,
                       assignment_capital_authorized: bool | None = None,
                       research: Mapping[str, object] | None = None
                       ) -> dict[str, object]:
    """Build one immutable-in-spirit, JSON-serializable paper candidate record.

    Inputs are read only and are never mutated.  ``selection_status`` is
    determined exclusively by integrity and lane policy; qualitative research
    is copied to its own field and cannot boost or reduce rank eligibility.
    """
    integrity = integrity_status(section)
    policy = lane_policy_status(section, group, card,
                                csp_open_count=csp_open_count,
                                covered_shares=covered_shares,
                                leaps_held=leaps_held,
                                assignment_capital_authorized=
                                assignment_capital_authorized)
    if research is None:
        research_out = research_status()
    else:
        raw_status = research.get("status", "NOT_ASSESSED")
        raw_reasons = research.get("reason_codes", ())
        reasons = (raw_reasons if isinstance(raw_reasons, Sequence)
                   and not isinstance(raw_reasons, (str, bytes)) else ())
        research_out = research_status(
            raw_status if isinstance(raw_status, str) else "NOT_ASSESSED",
            reason_codes=[str(reason) for reason in reasons],
        )

    try:
        ident: str | None = candidate_id(section, group, card)
    except ValueError:
        ident = None
        raw_reasons = integrity.get("reason_codes")
        prior_reasons = (list(raw_reasons)
                         if isinstance(raw_reasons, Sequence)
                         and not isinstance(raw_reasons, (str, bytes))
                         else [])
        integrity = {
            **integrity,
            "status": DATA_BLOCKED,
            "reason_codes": [*prior_reasons, "CANDIDATE_ID_INVALID"],
        }

    selection_status = (DATA_BLOCKED if integrity["status"] == DATA_BLOCKED
                        else policy["status"])
    return {
        "candidate_id": ident,
        "symbol": section.get("symbol"),
        "lane": group.get("kind"),
        "integrity": integrity,
        "policy": policy,
        "research": research_out,
        "selection_status": selection_status,
        "rank_eligible": (integrity["status"] == ELIGIBLE
                          and policy["status"] == ELIGIBLE),
    }

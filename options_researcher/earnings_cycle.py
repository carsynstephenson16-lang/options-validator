"""options_researcher/earnings_cycle.py -- contract-cycle earnings badge.

Answers ONE presentation-layer question for the attractiveness dashboard:
does a known quarterly earnings report land inside an option's remaining
life, i.e. in (chain_date, expiry]?

This is deliberately NOT h7_earnings.earnings_gate(): the gate answers
"is entry clear ON one evaluation date" (T-minus ban windows, post-report
grace); this adapter answers a per-contract RANGE question. It reuses the
same v3 point-in-time evidence primitives (assertions_view, report_date,
GATING_EVENT_CLASS) so both read one store under one supersession rule.

Tri-state, never falsely GREEN:
- AMBER    a known (estimated/confirmed/occurred) report lies in the window
- GREEN    the earliest known upcoming report falls AFTER expiry and is
           near enough (<= EARNINGS_COVERAGE_DAYS from the chain date) that
           an unrecorded earlier quarterly report cannot hide inside the
           window (two reports inside one coverage horizon would violate
           quarterly cadence)
- UNKNOWN  anything else: no evidence, passed-only schedules, or a next
           known report too far out to rule out a missing quarter

Display layer ONLY: grades nothing, gates nothing, sizes nothing.
"""
from __future__ import annotations

from datetime import date

import config
from options_researcher.h7_earnings import (
    GATING_EVENT_CLASS,
    assertions_view,
    report_date,
)

CYCLE_AMBER = "AMBER"
CYCLE_GREEN = "GREEN"
CYCLE_UNKNOWN = "UNKNOWN"


def cycle_badge(symbol: str, chain_date: date, expiry: date,
                assertions: list[dict], *, known_as_of) -> tuple[str, str]:
    """(state, reason) with state AMBER | GREEN | UNKNOWN (see module doc)."""
    sym = symbol.upper()
    view = [a for a in assertions_view(assertions, known_as_of)
            if a["symbol"] == sym
            and a.get("event_class") == GATING_EVENT_CLASS]
    if not view:
        return CYCLE_UNKNOWN, "no earnings evidence in the v3 store"

    dated = [(report_date(a), a["status"]) for a in view]
    in_window = sorted((d, s) for d, s in dated if chain_date < d <= expiry)
    if in_window:
        d, status = in_window[0]
        return CYCLE_AMBER, (f"{status} report {d.isoformat()} inside "
                             "(chain date, expiry]")

    upcoming = [d for d, _ in dated if d > chain_date]
    if not upcoming:
        return CYCLE_UNKNOWN, ("no known upcoming report; cannot certify "
                               "the cycle clear")

    nxt = min(upcoming)  # necessarily > expiry, else it was in_window
    if (nxt - chain_date).days <= config.EARNINGS_COVERAGE_DAYS:
        return CYCLE_GREEN, (f"next known report {nxt.isoformat()} falls "
                             "after expiry")
    return CYCLE_UNKNOWN, (
        f"next known report {nxt.isoformat()} is more than "
        f"{config.EARNINGS_COVERAGE_DAYS}d out; an unrecorded earlier "
        "report could land inside the cycle")


def apply_cycle_badges(groups: list[dict], symbol: str, chain_date: date,
                       assertions: list[dict], *, known_as_of) -> None:
    """Re-grade each card's ``earnings`` badge from the v3 store, in place.

    For symbols with no curated per-symbol earnings CSV the card ladder is
    built with an empty date list (every earnings badge UNKNOWN); this pass
    re-answers the range question per card from the v3 point-in-time store
    and records the reason on the card (``earnings_cycle_reason``). Cards
    that are skipped or carry no earnings badge are left untouched.
    """
    for grp in groups:
        for card in grp.get("cards", []):
            if "skipped" in card:
                continue
            grades = card.get("grades")
            if not isinstance(grades, dict) or "earnings" not in grades:
                continue
            expiry = date.fromisoformat(str(card["expiry"]))
            state, reason = cycle_badge(symbol, chain_date, expiry,
                                        assertions, known_as_of=known_as_of)
            grades["earnings"] = state
            card["earnings_cycle_reason"] = reason

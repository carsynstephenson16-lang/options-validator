"""Gross-error detector for vendor option rows.

This module catches data glitches, never ordinary Black-Scholes-versus-vendor
model disagreement.  American no-arbitrage checks require a synchronized raw
underlying spot.  Legacy cache rows do not contain that field and therefore
return ``NOT_ASSESSED``; callers must never substitute a daily close.
"""
from __future__ import annotations

import enum
import math
from dataclasses import dataclass

import config


class Tier(enum.Enum):
    OK = "OK"
    INVALID_NO_ARB = "INVALID_NO_ARB"
    INVALID_GREEK = "INVALID_GREEK"
    INVALID_QUOTE = "INVALID_QUOTE"
    EXTREME = "EXTREME"
    NO_EUROPEAN_BS_ROOT = "no_european_bs_root"
    NOT_ASSESSED = "NOT_ASSESSED"


@dataclass(frozen=True)
class Verdict:
    tier: Tier
    reason: str


def _finite_float(value: object) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def classify_row(
    *,
    right: object,
    strike: object,
    bid: object,
    ask: object,
    iv: object,
    delta: object,
    gamma: object,
    vega: object,
    spot: object = None,
    iv_reason: str | None = None,
) -> Verdict:
    """Classify one synchronized vendor row into one disjoint outcome tier."""
    normalized_right = str(right).upper()
    if normalized_right not in {"C", "P"}:
        return Verdict(Tier.NOT_ASSESSED, "right must be C or P")
    if spot is None:
        return Verdict(Tier.NOT_ASSESSED, "missing synchronized spot")

    strike_value = _finite_float(strike)
    bid_value = _finite_float(bid)
    ask_value = _finite_float(ask)
    iv_value = _finite_float(iv)
    delta_value = _finite_float(delta)
    gamma_value = _finite_float(gamma)
    vega_value = _finite_float(vega)
    spot_value = _finite_float(spot)
    numeric = (
        strike_value,
        bid_value,
        ask_value,
        iv_value,
        delta_value,
        gamma_value,
        vega_value,
        spot_value,
    )
    if any(value is None for value in numeric):
        return Verdict(Tier.NOT_ASSESSED, "missing or non-finite vendor field")
    assert strike_value is not None
    assert bid_value is not None
    assert ask_value is not None
    assert iv_value is not None
    assert delta_value is not None
    assert gamma_value is not None
    assert vega_value is not None
    assert spot_value is not None

    if strike_value <= 0 or spot_value <= 0:
        return Verdict(Tier.NOT_ASSESSED, "strike and synchronized spot must be positive")

    if bid_value < 0 or ask_value < 0 or bid_value > ask_value:
        return Verdict(
            Tier.INVALID_QUOTE,
            f"crossed or negative quote bid={bid_value} ask={ask_value}",
        )

    epsilon = config.BS_DELTA_EPS
    if gamma_value < 0 or vega_value < 0:
        return Verdict(Tier.INVALID_GREEK, "negative gamma or vega")
    if normalized_right == "C" and not -epsilon <= delta_value <= 1.0 + epsilon:
        return Verdict(Tier.INVALID_GREEK, f"call delta {delta_value} out of range")
    if normalized_right == "P" and not -1.0 - epsilon <= delta_value <= epsilon:
        return Verdict(Tier.INVALID_GREEK, f"put delta {delta_value} out of range")

    tolerance = config.BS_NOARB_TOL
    if normalized_right == "C":
        lower = max(spot_value - strike_value, 0.0)
        upper = spot_value
    else:
        lower = max(strike_value - spot_value, 0.0)
        upper = strike_value
    if ask_value < lower - tolerance:
        return Verdict(
            Tier.INVALID_NO_ARB,
            f"ask {ask_value} below executable floor {lower}",
        )
    if bid_value > upper + tolerance:
        return Verdict(
            Tier.INVALID_NO_ARB,
            f"bid {bid_value} above executable ceiling {upper}",
        )

    if iv_reason == "no_european_bs_root":
        return Verdict(
            Tier.NO_EUROPEAN_BS_ROOT,
            "midpoint has no European Black-Scholes implied-volatility root",
        )
    if iv_reason not in {None, "solved"}:
        return Verdict(Tier.NOT_ASSESSED, f"IV inversion unavailable: {iv_reason}")

    if iv_value <= config.BS_IV_EXTREME_LOW or iv_value >= config.BS_IV_EXTREME_HIGH:
        return Verdict(
            Tier.EXTREME,
            f"iv {iv_value} outside inclusive normal band "
            f"({config.BS_IV_EXTREME_LOW}, {config.BS_IV_EXTREME_HIGH})",
        )
    return Verdict(Tier.OK, "ok")

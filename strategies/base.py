"""
strategies/base.py -- shared helpers so strategies size and cost identically.
Apples-to-apples starts here. These functions are real and correct.
"""
from __future__ import annotations
import math

import config


def risk_budget() -> float:
    """Dollars at risk allowed per trade = RISK_PER_TRADE of the options sleeve."""
    return config.RISK_SLEEVE * config.RISK_PER_TRADE


def round_trip_commission_per_spread(legs: int = 2) -> float:
    """Commission for opening and closing one multi-leg spread contract."""
    return legs * 2 * config.COMMISSION_PER_CONTRACT


def capital_at_risk_per_spread(width: float, net_credit: float) -> float:
    """Defined-risk broker margin, excluding commissions."""
    return (width - net_credit) * 100.0


def economic_max_loss_per_spread(width: float, net_credit: float) -> float:
    """Budget-fit risk = broker margin plus round-trip commissions."""
    return capital_at_risk_per_spread(width, net_credit) + round_trip_commission_per_spread()


def size_defined_risk(width: float, net_credit: float):
    """Return (contracts, economic_max_loss_per_spread) honoring the risk budget.

    Broker-defined max loss is `(width - net_credit) * 100`, but the real dollars
    lost at max loss also include round-trip commissions. Sizing gates on that
    economic max loss. Returns 0 if a single spread exceeds the budget -- the
    caller must log 'risk budget too small for this width' and skip. Impossible
    vertical credits return infinite risk so bad quotes fail closed. NEVER round
    up to 1.
    """
    if width <= 0 or net_credit <= 0 or net_credit >= width:
        return 0, float("inf")
    capital_at_risk = capital_at_risk_per_spread(width, net_credit)
    economic_max_loss = economic_max_loss_per_spread(width, net_credit)
    return max(math.floor(risk_budget() / economic_max_loss), 0), economic_max_loss


def entry_credit_conservative(short_bid, short_ask, long_bid, long_ask,
                              haircut=config.SLIPPAGE_HAIRCUT):
    """Net credit priced at the frozen conservative fill model.

    With HALF_SPREAD_COST enabled, the short leg fills at bid and the long leg
    fills at ask (crossing half the spread from mid on each leg). The haircut is
    then applied adversely on top: receive less on the short leg, pay more on the
    long leg. Commission is added separately because it is a per-contract dollar
    fee, not a price adjustment.
    """
    normalized = []
    for name, bid_raw, ask_raw in (
        ("short", short_bid, short_ask),
        ("long", long_bid, long_ask),
    ):
        try:
            bid = float(bid_raw)
            ask = float(ask_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} leg quote must be numeric") from exc
        if not (math.isfinite(bid) and math.isfinite(ask)):
            raise ValueError(f"{name} leg quote must be finite")
        if bid < 0 or ask <= 0 or ask < bid:
            raise ValueError(
                f"{name} leg quote is invalid: bid={bid_raw!r}, ask={ask_raw!r}"
            )
        normalized.append((bid, ask))

    (short_bid, short_ask), (long_bid, long_ask) = normalized
    short_mid = (short_bid + short_ask) / 2.0
    long_mid = (long_bid + long_ask) / 2.0
    short_base = short_bid if config.HALF_SPREAD_COST else short_mid
    long_base = long_ask if config.HALF_SPREAD_COST else long_mid
    short_fill = short_base * (1 - haircut)    # receive less
    long_fill = long_base * (1 + haircut)      # pay more
    return short_fill - long_fill

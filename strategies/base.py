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


def size_defined_risk(width: float, net_credit: float):
    """Return (contracts, max_loss_per_spread) honoring the risk budget.

    max loss per spread = (width - net_credit) * 100.
    contracts = floor(budget / max_loss). Returns 0 if a single spread already
    exceeds the budget -- the caller must log 'risk budget too small for this
    width' and skip. NEVER round up to 1.
    """
    max_loss = (width - net_credit) * 100.0
    if max_loss <= 0:
        return 0, max_loss
    return max(math.floor(risk_budget() / max_loss), 0), max_loss


def entry_credit_conservative(short_bid, short_ask, long_bid, long_ask,
                              haircut=config.SLIPPAGE_HAIRCUT):
    """Net credit priced at MID, then made WORSE by the haircut -- never favorable.

    Short put: you'd like to receive its mid, so the haircut makes you receive
    LESS. Long put: you'd like to pay its mid, so the haircut makes you pay MORE.
    Result is strictly below the mid-to-mid credit. Commission is added
    separately (it is a per-contract dollar fee, not a price adjustment).
    """
    short_mid = (short_bid + short_ask) / 2.0
    long_mid = (long_bid + long_ask) / 2.0
    short_fill = short_mid * (1 - haircut)     # receive less
    long_fill = long_mid * (1 + haircut)       # pay more
    return short_fill - long_fill

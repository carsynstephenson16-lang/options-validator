"""H7 lane decisions (pure). Registration f1887c9d + amendment e266770f;
revised per the 2026-07-10 adversarial review (R1/R6/R7/R8/R9/R14).

decide_lane_a/b/c: (adjusted closes, one day's chain, raw spot, budget/ban
state) -> action dict or None.

INPUT CONTRACT: `closes` is the split-ADJUSTED series
(load_closes_adjusted) -- trailing signals on raw closes fabricate crashes at
split boundaries (R1). `spot` is the RAW as-traded underlying price aligned
with the chain's raw strikes; live (post-latest-split) the two coincide.

FILLS: every leg is costed at its adverse SIDE (buy at ask, sell at bid) plus
SLIPPAGE_HAIRCUT, plus round-trip commissions -- the .cursorrules half-spread
rule; mid-based fills understated costs by up to half the quoted spread (R6).

Backtest sizing note (pre-declared): the harness runs per-symbol chunks, so
the cross-symbol H7_MONTHLY_AT_RISK sleeve is enforced per-symbol-month in
simulation. The verdict metric is expectancy-per-trade after costs, which the
cross-symbol budget does not touch; the sleeve binds live sizing.
"""

from __future__ import annotations

from datetime import date as Date

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity
from options_researcher import h7_signals as sig
from options_researcher.chains import is_monthly
from strategies.base import entry_credit_conservative

# Structural epsilon for "strictly lower strike", not a strategy number.
_MIN_STRIKE_GAP = 0.5
def _delta_band() -> float:
    """v1.2(7): the H7-specific frozen acceptance band around every
    registered delta target."""
    return float(config.H7_DELTA_TOLERANCE)


def _monthly_rows(chain: pd.DataFrame, today: Date, band: tuple[int, int],
                  right: str) -> pd.DataFrame:
    df = chain[(chain.right == right) & (chain.bid > 0) & (chain.ask > 0)].copy()
    if df.empty:
        return df
    exp = pd.to_datetime(df.expiration).dt.date
    df = df.assign(exp=exp, dte=exp.map(lambda d: (d - today).days))
    return df[df.exp.map(is_monthly) & df.dte.between(*band)]


def _nearest_expiry(df: pd.DataFrame, target_dte: int):
    if df.empty:
        return None
    return df.loc[(df.dte - target_dte).abs().idxmin(), "exp"]


def _liquid(row) -> bool:
    return bool(passes_liquidity(row.open_interest, row.bid, row.ask))


def _buy_fill(row) -> float:
    """Adverse-side buy: ask plus haircut (half-spread rule, R6)."""
    return float(row.ask) * (1 + config.SLIPPAGE_HAIRCUT)


def _sell_fill(row) -> float:
    """Adverse-side sell: bid minus haircut."""
    return float(row.bid) * (1 - config.SLIPPAGE_HAIRCUT)


def _round_trip_commission(legs: int) -> float:
    return legs * 2 * config.COMMISSION_PER_CONTRACT


def _long_action(closes: pd.Series, chain: pd.DataFrame, spot: float,
                 today: Date, month_spent: float, lane: str, stop_ref: float):
    """Shared long-lane structure selection: route by IV vs RV, then build
    either the single call or the debit spread inside the monthly expiration
    nearest the long band's midpoint. Returns an action dict or None."""
    admitted, _ = sig.lane_admission(chain, spot=spot, today=today,
                                     dte_band=config.H7_LONG_DTE_BAND, right="C")
    if not admitted:
        return None
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = sig.atm_iv_90d(chain, spot, today)
    route = sig.iv_route(iv=iv, rv=rv)
    if route not in ("call", "spread"):
        return None
    budget = config.H7_MONTHLY_AT_RISK - month_spent
    band = _monthly_rows(chain, today, config.H7_LONG_DTE_BAND, "C")
    tenor_target = (config.H7_LONG_DTE_BAND[0] + config.H7_LONG_DTE_BAND[1]) // 2
    exp = _nearest_expiry(band, tenor_target)
    if exp is None:
        return None
    legs = band[band.exp == exp]

    if route == "call":
        lo, hi = config.H7_LONG_DELTA_BAND
        cands = legs[(legs.delta >= lo) & (legs.delta <= hi)]
        if cands.empty:
            return None
        target = (lo + hi) / 2
        row = cands.loc[(cands.delta - target).abs().idxmin()]
        cost = _buy_fill(row) * 100 + _round_trip_commission(legs=1)
        if cost > budget or not _liquid(row):
            return None
        return {"lane": lane, "kind": "long_call", "expiration": str(row.exp),
                "strike": float(row.strike), "delta": float(row.delta),
                "cost": float(cost), "stop_ref": stop_ref}

    # debit spread: registered targets with the repo-standard acceptance band;
    # off-band chains are skipped, never traded off-spec (R7)
    band_w = _delta_band()
    lo_c = legs[(legs.delta - config.H7_SPREAD_LONG_DELTA).abs() <= band_w]
    hi_c = legs[(legs.delta - config.H7_SPREAD_SHORT_DELTA).abs() <= band_w]
    if lo_c.empty or hi_c.empty:
        return None
    lo_row = lo_c.loc[(lo_c.delta - config.H7_SPREAD_LONG_DELTA).abs().idxmin()]
    hi_row = hi_c.loc[(hi_c.delta - config.H7_SPREAD_SHORT_DELTA).abs().idxmin()]
    if float(lo_row.strike) + _MIN_STRIKE_GAP > float(hi_row.strike):
        return None
    debit = _buy_fill(lo_row) - _sell_fill(hi_row)
    cost = debit * 100 + _round_trip_commission(legs=2)
    if cost <= 0 or cost > budget or not (_liquid(lo_row) and _liquid(hi_row)):
        return None
    return {"lane": lane, "kind": "call_debit_spread", "expiration": str(lo_row.exp),
            "long_strike": float(lo_row.strike), "short_strike": float(hi_row.strike),
            "cost": float(cost), "stop_ref": stop_ref}


def decide_lane_a(*, closes: pd.Series, chain: pd.DataFrame, spot: float,
                  today: Date, month_spent: float, banned: bool):
    if banned or not sig.lane_a_armed(closes):
        return None
    stop_ref = sig.episode_low(closes)  # the registered signal low (R8)
    return _long_action(closes, chain, spot, today, month_spent, "a", stop_ref)


def decide_lane_b(*, closes: pd.Series, chain: pd.DataFrame, spot: float,
                  today: Date, month_spent: float, banned: bool):
    if banned or not sig.lane_b_armed(closes):
        return None
    # edge-trigger: fire only on the first day the coil conditions turn on (R14)
    if len(closes) > 1 and sig.lane_b_armed(closes.iloc[:-1]):
        return None
    stop_ref = float(closes.iloc[-config.H7B_RANGE_LOOKBACK_D:].min())  # range low
    return _long_action(closes, chain, spot, today, month_spent, "b", stop_ref)


def decide_lane_c(*, symbol: str, closes: pd.Series, chain: pd.DataFrame,
                  spot: float, today: Date, month_spent: float, banned: bool,
                  open_h7c: int):
    if symbol.upper() in config.H7_CORE_LONG_ONLY:  # H7c stays H5's book (R9)
        return None
    if banned or open_h7c >= config.H7C_MAX_CONCURRENT:
        return None
    if not sig.lane_a_armed(closes):  # c shares a's stabilization condition
        return None
    admitted, _ = sig.lane_admission(chain, spot=spot, today=today,
                                     dte_band=config.H7C_DTE_BAND, right="P")
    if not admitted:
        return None
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = sig.atm_iv_90d(chain, spot, today)
    if sig.iv_route(iv=iv, rv=rv) != "h7c":
        return None
    puts = _monthly_rows(chain, today, config.H7C_DTE_BAND, "P")
    tenor_target = (config.H7C_DTE_BAND[0] + config.H7C_DTE_BAND[1]) // 2
    exp = _nearest_expiry(puts, tenor_target)
    if exp is None:
        return None
    legs = puts[puts.exp == exp]
    floor = config.H7C_SHORT_DELTA_MAX - _delta_band()
    shorts = legs[(legs.delta.abs() <= config.H7C_SHORT_DELTA_MAX)
                  & (legs.delta.abs() >= floor)]
    if shorts.empty:
        return None
    short = shorts.loc[shorts.delta.abs().idxmax()]  # closest to 0.30 from below
    width_target = round(spot * config.H7C_WIDTH_FRAC_OF_SPOT)
    lower = legs[legs.strike <= float(short.strike) - _MIN_STRIKE_GAP]
    if lower.empty:
        return None
    lg = lower.loc[(lower.strike - (float(short.strike) - width_target)).abs().idxmin()]
    width = float(short.strike) - float(lg.strike)
    if width <= 0:
        return None
    credit = entry_credit_conservative(short.bid, short.ask, lg.bid, lg.ask)
    if credit <= 0 or credit < config.H7C_CREDIT_FLOOR_FRAC * width:
        return None
    max_loss = (width - credit) * 100 + _round_trip_commission(legs=2)
    budget = config.H7_MONTHLY_AT_RISK - month_spent
    if max_loss > budget or not (_liquid(short) and _liquid(lg)):
        return None
    return {"lane": "c", "kind": "bull_put_spread", "expiration": str(exp),
            "short_strike": float(short.strike), "long_strike": float(lg.strike),
            "short_delta": float(short.delta), "width": width,
            "credit": float(credit), "max_loss": float(max_loss),
            "dte_band": config.H7C_DTE_BAND, "stop_ref": sig.episode_low(closes)}

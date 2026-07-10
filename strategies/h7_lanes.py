"""H7 lane decisions (pure). Registration f1887c9d + amendment e266770f.

decide_lane_a/b/c: (closes, one day's chain, budget/ban state) -> action dict
or None. Fills are costed mid-or-worse + SLIPPAGE_HAIRCUT + commissions,
matching strategies/base.py conventions; execution liquidity uses the same
passes_liquidity gate as H1/H2. The Lumibot glue (separate section, added
with the runner) only translates actions into orders -- all economics live
here where they are offline-testable.

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


def _mid(row) -> float:
    return (float(row.bid) + float(row.ask)) / 2


def _long_action(closes: pd.Series, chain: pd.DataFrame, today: Date,
                 month_spent: float, lane: str, stop_ref: float):
    """Shared long-lane structure selection: route by IV vs RV, then build
    either the single call or the debit spread inside the nearest-90d
    monthly. Returns an action dict or None."""
    spot = float(closes.iloc[-1])
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
    exp = _nearest_expiry(band, 90)
    if exp is None:
        return None
    legs = band[band.exp == exp]

    if route == "call":
        lo, hi = config.H7_LONG_DELTA_BAND
        cands = legs[(legs.delta >= lo) & (legs.delta <= hi)]
        if cands.empty:
            return None
        row = cands.loc[(cands.delta - 0.60).abs().idxmin()]
        cost = _mid(row) * (1 + config.SLIPPAGE_HAIRCUT) * 100 \
            + config.COMMISSION_PER_CONTRACT
        if cost > budget or not _liquid(row):
            return None
        return {"lane": lane, "kind": "long_call", "expiration": str(row.exp),
                "strike": float(row.strike), "delta": float(row.delta),
                "cost": float(cost), "stop_ref": stop_ref}

    lo_row = legs.loc[(legs.delta - config.H7_SPREAD_LONG_DELTA).abs().idxmin()]
    hi_row = legs.loc[(legs.delta - config.H7_SPREAD_SHORT_DELTA).abs().idxmin()]
    if float(lo_row.strike) >= float(hi_row.strike):
        return None
    debit = _mid(lo_row) * (1 + config.SLIPPAGE_HAIRCUT) \
        - _mid(hi_row) * (1 - config.SLIPPAGE_HAIRCUT)
    cost = debit * 100 + 2 * config.COMMISSION_PER_CONTRACT
    if cost <= 0 or cost > budget or not (_liquid(lo_row) and _liquid(hi_row)):
        return None
    return {"lane": lane, "kind": "call_debit_spread", "expiration": str(lo_row.exp),
            "long_strike": float(lo_row.strike), "short_strike": float(hi_row.strike),
            "cost": float(cost), "stop_ref": stop_ref}


def decide_lane_a(*, closes: pd.Series, chain: pd.DataFrame, today: Date,
                  month_spent: float, banned: bool):
    if banned or not sig.lane_a_armed(closes):
        return None
    stop_ref = float(closes.iloc[-25:].min())  # the stabilization low
    return _long_action(closes, chain, today, month_spent, "a", stop_ref)


def decide_lane_b(*, closes: pd.Series, chain: pd.DataFrame, today: Date,
                  month_spent: float, banned: bool):
    if banned or not sig.lane_b_armed(closes):
        return None
    stop_ref = float(closes.iloc[-config.H7B_RANGE_LOOKBACK_D:].min())  # range low
    return _long_action(closes, chain, today, month_spent, "b", stop_ref)


def decide_lane_c(*, closes: pd.Series, chain: pd.DataFrame, today: Date,
                  month_spent: float, banned: bool, open_h7c: int):
    if banned or open_h7c >= config.H7C_MAX_CONCURRENT:
        return None
    if not sig.lane_a_armed(closes):  # c shares a's stabilization condition
        return None
    spot = float(closes.iloc[-1])
    admitted, _ = sig.lane_admission(chain, spot=spot, today=today,
                                     dte_band=config.H7C_DTE_BAND, right="P")
    if not admitted:
        return None
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = sig.atm_iv_90d(chain, spot, today)
    if sig.iv_route(iv=iv, rv=rv) != "h7c":
        return None
    puts = _monthly_rows(chain, today, config.H7C_DTE_BAND, "P")
    exp = _nearest_expiry(puts, 38)
    if exp is None:
        return None
    legs = puts[puts.exp == exp]
    shorts = legs[legs.delta.abs() <= config.H7C_SHORT_DELTA_MAX]
    if shorts.empty:
        return None
    short = shorts.loc[shorts.delta.abs().idxmax()]  # closest to 0.30 from below
    width_target = round(spot * config.H7C_WIDTH_FRAC_OF_SPOT)
    lower = legs[legs.strike <= float(short.strike) - 0.5]
    if lower.empty:
        return None
    lg = lower.loc[(lower.strike - (float(short.strike) - width_target)).abs().idxmin()]
    width = float(short.strike) - float(lg.strike)
    if width <= 0:
        return None
    credit = entry_credit_conservative(short.bid, short.ask, lg.bid, lg.ask)
    if credit <= 0 or credit < config.H7C_CREDIT_FLOOR_FRAC * width:
        return None
    max_loss = (width - credit) * 100 + 2 * 2 * config.COMMISSION_PER_CONTRACT
    budget = config.H7_MONTHLY_AT_RISK - month_spent
    if max_loss > budget or not (_liquid(short) and _liquid(lg)):
        return None
    return {"lane": "c", "kind": "bull_put_spread", "expiration": str(exp),
            "short_strike": float(short.strike), "long_strike": float(lg.strike),
            "short_delta": float(short.delta), "width": width,
            "credit": float(credit), "max_loss": float(max_loss),
            "dte_band": config.H7C_DTE_BAND, "stop_ref": float(closes.iloc[-25:].min())}

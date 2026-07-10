"""Pure H7 signal functions. Frozen numbers come from config (registration
f1887c9d...). Everything here is a function of closes and/or one day's cached
chain -- no I/O, no state -- so the watcher and the backtest cannot drift
apart.

CLOSES CONTRACT (review finding R1, 2026-07-10): every `closes` argument in
this module MUST be the split-ADJUSTED (continuous) series from
data.underlying_closes.load_closes_adjusted. Raw as-traded closes read a 5:1
split as an -80% crash and fabricate drawdowns/RV. Chain-side math (strikes,
spot, admission) uses RAW spot -- callers pass it separately."""

from __future__ import annotations

import math
from datetime import date

import pandas as pd

import config
from options_researcher.chains import is_monthly


def drawdown_pct(closes: pd.Series) -> float:
    """Drawdown of the last close from the trailing 52-week (252-session) high."""
    window = closes.iloc[-252:]
    return 1.0 - float(window.iloc[-1]) / float(window.max())


def reclaimed_20d_high(closes: pd.Series) -> bool:
    """Registration semantics (f1887c9d): fires on the FIRST close above the
    prior 20-session high per drawdown episode; the episode re-arms only
    after a fresh 20-session low. A grinding advance therefore fires exactly
    once, at its first cross, not on every incremental high."""
    n = config.H7A_RECLAIM_LOOKBACK_D
    if len(closes) < n + 2:
        return False
    prior_high = closes.shift(1).rolling(n).max()
    prior_low = closes.shift(1).rolling(n).min()
    crosses = (closes > prior_high).fillna(False)
    new_lows = (closes < prior_low).fillna(False)
    if not bool(crosses.iloc[-1]):
        return False
    last = len(closes) - 1
    rearm = -1
    for i in range(last - 1, -1, -1):
        if bool(new_lows.iloc[i]):
            rearm = i
            break
    # fire only if today's cross is the first since the last re-arm
    return not bool(crosses.iloc[rearm + 1:last].any())


def lane_a_armed(closes: pd.Series) -> bool:
    return (
        drawdown_pct(closes) >= config.H7A_DRAWDOWN_MIN
        and reclaimed_20d_high(closes)
    )


def episode_low(closes: pd.Series) -> float:
    """The drawdown episode's low: minimum close since the last fresh
    20-session-low event (the same re-arm anchor reclaimed_20d_high uses).
    This is the registered H7a stop reference ('close below signal low')."""
    n = config.H7A_RECLAIM_LOOKBACK_D
    if len(closes) < n + 2:
        return float(closes.min())
    prior_low = closes.shift(1).rolling(n).min()
    new_lows = (closes < prior_low).fillna(False)
    rearm = -1
    for i in range(len(closes) - 2, -1, -1):
        if bool(new_lows.iloc[i]):
            rearm = i
            break
    window = closes.iloc[rearm:] if rearm >= 0 else closes.iloc[-(n + 5):]
    return float(window.min())


def range_pct(closes: pd.Series, lookback: int) -> float:
    w = closes.iloc[-lookback:]
    return (float(w.max()) - float(w.min())) / float(w.iloc[-1])


def rv_annualized(closes: pd.Series, lookback: int) -> float:
    rets = closes.pct_change().dropna().iloc[-lookback:]
    return float(rets.std() * math.sqrt(252))


def rv_percentile(closes: pd.Series, window: int = 20, history: int = 252) -> float:
    """Percentile of the current `window`-day RV within its own history.
    Names with under ~6 months of usable history return 1.0 (never passes),
    per the registration's minimum-listing rule."""
    rv = closes.pct_change().rolling(window).std().dropna().iloc[-history:]
    if len(rv) < 106:  # ~6 months listed (126 sessions) minus the RV window
        return 1.0
    return float((rv <= rv.iloc[-1]).mean())


def lane_b_armed(closes: pd.Series) -> bool:
    return (
        range_pct(closes, config.H7B_RANGE_LOOKBACK_D) <= config.H7B_RANGE_MAX
        and rv_percentile(closes) <= config.H7B_RV_PCTILE_MAX
    )


def iv_route(iv: float, rv: float) -> str:
    """Route by IV vs trailing RV: 'call' | 'spread' | 'h7c' | 'none'."""
    if rv <= 0 or iv <= 0:
        return "none"
    ratio = iv / rv
    if ratio <= config.H7_IV_CHEAP_K:
        return "call"
    if ratio <= config.H7_IV_PAR_K:
        return "spread"
    if ratio >= config.H7_IV_RICH_K:
        return "h7c"
    return "none"


def atm_iv_90d(chain: pd.DataFrame, spot: float, today: date,
               dte_band: tuple[int, int] = (72, 108)) -> float:
    """The registration's IV measure: ATM call IV at THE expiration nearest
    90 DTE (+/-18d) -- pick the expiration first, then the ATM strike within
    it (review finding R2: pooling all in-band rows let a farther expiration
    win the ATM tie and shift the routing ratio). Returns 0.0 when no
    two-sided quotes exist in band -- iv_route treats that as 'none'."""
    df = chain[(chain.right == "C") & (chain.bid > 0) & (chain.ask > 0)].copy()
    if df.empty:
        return 0.0
    exp = pd.to_datetime(df.expiration).dt.date
    df = df.assign(dte=exp.map(lambda d: (d - today).days))
    df = df[df.dte.between(*dte_band)]
    if df.empty:
        return 0.0
    target = (dte_band[0] + dte_band[1]) // 2
    best_exp = df.loc[(df.dte - target).abs().idxmin(), "expiration"]
    within = df[df.expiration == best_exp]
    row = within.loc[(within.strike - spot).abs().idxmin()]
    return float(row.iv)


def lane_admission(chain: pd.DataFrame, *, spot: float, today: date,
                   dte_band: tuple[int, int], right: str = "C") -> tuple[bool, int]:
    """Admission per lane per day: >= H7_ADMIT_MIN_CONTRACTS NTM monthly
    contracts of the lane's TRADED right (calls for a/b, puts for c) inside
    the lane's DTE band with OI >= MIN_OPEN_INTEREST and spread <=
    H7_ADMIT_MAX_SPREAD_PCT. Execution gates (MAX_SPREAD_PCT, both legs) are
    checked separately at trade construction."""
    df = chain[(chain.right == right) & (chain.bid > 0) & (chain.ask > 0)].copy()
    if df.empty:
        return False, 0
    exp = pd.to_datetime(df.expiration).dt.date
    dte = exp.map(lambda d: (d - today).days)
    mid = (df.bid + df.ask) / 2
    spread = (df.ask - df.bid) / mid
    ntm = df[
        exp.map(is_monthly)
        & dte.between(*dte_band)
        & df.strike.between(0.9 * spot, 1.1 * spot)
        & (df.open_interest >= config.MIN_OPEN_INTEREST)
        & (spread <= config.H7_ADMIT_MAX_SPREAD_PCT)
    ]
    return len(ntm) >= config.H7_ADMIT_MIN_CONTRACTS, len(ntm)

"""EXP-TAIL realized return-shape display experiment.

DISPLAY-ONLY, cached-data-only, and non-verdict-bearing. This module's
skewness and excess kurtosis are pandas' bias-corrected sample moments. That
convention deliberately differs from ``metrics.sample_moments``, which uses
population moments and raw kurtosis in the strategy-PnL domain. It is also
unrelated to ``composite_signals``' implied-volatility ``skew_25d``. Those are
three distinct quantities that happen to share the word "skew".

The board builder reads only cached adjusted closes and truncates every series
to the requested as-of session. Jump classification is causal: the volatility
used to judge a return is estimated exclusively from returns before that day.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

import config
from data.underlying_closes import load_closes_adjusted

# LLM-proposed 2026-08-09; survey rank-7 convention; display-only;
# not owner-ratified.
EXP_TAIL_WINDOW = int(getattr(config, "EXP_TAIL_WINDOW", 252))
# LLM-proposed 2026-08-09; survey rank-7 convention; display-only;
# not owner-ratified.
EXP_TAIL_MIN_OBS = int(getattr(config, "EXP_TAIL_MIN_OBS", 250))
# LLM-proposed 2026-08-09; survey rank-7 convention; display-only;
# not owner-ratified.
EXP_TAIL_JUMP_SIGMA = float(getattr(config, "EXP_TAIL_JUMP_SIGMA", 3.0))
# LLM-proposed 2026-08-09; survey rank-7 convention; display-only;
# not owner-ratified.
EXP_TAIL_ALT_WINDOWS = tuple(getattr(config, "EXP_TAIL_ALT_WINDOWS", (189, 378)))

_JUMP_MIN_PERIODS = 126
_CAVEAT = "Describes past return shape only; not a forecast; a calm year hides tail risk."
_HISTORY_START = "1900-01-01"


def _blocked_card(*, asof: str, reason: str, max_asof: str | None = None, n_obs: int = 0) -> dict:
    return {
        "experiment_id": "EXP-TAIL",
        "state": "DATA_BLOCKED",
        "data_blocked": True,
        "reason": reason,
        "asof": asof,
        "max_asof": max_asof,
        "skew": None,
        "excess_kurtosis": None,
        "jump_count": None,
        "jump_rate": None,
        "window": EXP_TAIL_WINDOW,
        "n_obs": n_obs,
        "window_agreement": None,
        "caveat": _CAVEAT,
    }


def _usable_closes(closes: pd.Series, *, asof: str) -> pd.Series:
    index = pd.to_datetime(closes.index, errors="coerce")
    values = pd.to_numeric(closes, errors="coerce")
    frame = pd.DataFrame({"close": values.to_numpy()}, index=index)
    frame = frame.loc[frame.index.notna()]
    frame = frame.loc[np.isfinite(frame["close"]) & (frame["close"] > 0.0)]
    frame = frame.loc[frame.index <= pd.Timestamp(asof)]
    frame = frame.loc[~frame.index.duplicated(keep="last")].sort_index()
    return frame["close"].astype(float)


def _qualitative_moment_read(returns: pd.Series, window: int) -> tuple[int, bool]:
    sample = returns.tail(window)
    skew = float(sample.skew())
    excess_kurtosis = float(sample.kurt())
    skew_sign = -1 if skew < 0.0 else (1 if skew > 0.0 else 0)
    return skew_sign, excess_kurtosis > 1.0


def exp_tail_shape(closes: pd.Series, *, asof: str) -> dict:
    """Describe trailing realized-return shape using only data through asof."""
    usable = _usable_closes(closes, asof=asof)
    max_asof = None if usable.empty else usable.index[-1].date().isoformat()
    returns = np.log(usable).diff().replace([np.inf, -np.inf], np.nan).dropna()
    n_obs = len(returns)
    if n_obs < EXP_TAIL_MIN_OBS:
        return _blocked_card(
            asof=asof,
            max_asof=max_asof,
            n_obs=n_obs,
            reason=(f"fewer than {EXP_TAIL_MIN_OBS} usable sessions ({n_obs} available)"),
        )

    primary = returns.tail(EXP_TAIL_WINDOW)
    skew = float(primary.skew())
    excess_kurtosis = float(primary.kurt())

    sigma_before = (
        returns.shift(1).rolling(EXP_TAIL_WINDOW, min_periods=_JUMP_MIN_PERIODS).std(ddof=1)
    )
    primary_sigma = sigma_before.reindex(primary.index)
    evaluable = primary_sigma.notna()
    evaluable_days = int(evaluable.sum())
    if evaluable_days:
        jumps = primary.abs().loc[evaluable] > (EXP_TAIL_JUMP_SIGMA * primary_sigma.loc[evaluable])
        jump_count: int | None = int(jumps.sum())
        jump_rate: float | None = jump_count / evaluable_days
        reason = None
    else:
        jump_count = None
        jump_rate = None
        reason = "no evaluable jump days after 126-session causal sigma floor"

    diagnostic_windows = (*EXP_TAIL_ALT_WINDOWS[:1], EXP_TAIL_WINDOW, *EXP_TAIL_ALT_WINDOWS[1:])
    reads = [_qualitative_moment_read(returns, window) for window in diagnostic_windows]
    window_agreement = all(read == reads[0] for read in reads[1:])

    return {
        "experiment_id": "EXP-TAIL",
        "state": "OK" if window_agreement else "UNSTABLE",
        "data_blocked": False,
        "reason": reason,
        "asof": asof,
        "max_asof": max_asof,
        "skew": skew,
        "excess_kurtosis": excess_kurtosis,
        "jump_count": jump_count,
        "jump_rate": jump_rate,
        "window": EXP_TAIL_WINDOW,
        "n_obs": n_obs,
        "window_agreement": window_agreement,
        "caveat": _CAVEAT,
    }


def build_exp_tail_board(symbols: Sequence[str], *, asof: str) -> list[dict]:
    """Build one fail-visible EXP-TAIL card per symbol from cached closes."""
    cards: list[dict] = []
    for symbol in symbols:
        try:
            closes = load_closes_adjusted(symbol, _HISTORY_START, asof, allow_oos=True)
            card = exp_tail_shape(closes.loc[:asof], asof=asof)
        except Exception as exc:
            card = _blocked_card(
                asof=asof,
                reason=f"{type(exc).__name__}: {exc}",
            )
        cards.append({"symbol": symbol, **card})
    return cards

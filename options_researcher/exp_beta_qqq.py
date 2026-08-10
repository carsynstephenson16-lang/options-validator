"""Display-only rolling beta-to-QQQ experiment.

Cached closes are translated into descriptive beta, R-squared, and
half-window stability diagnostics. This module does not rank names, read
positions, persist artifacts, or make provider calls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from data.underlying_closes import load_closes_adjusted

# LLM-proposed 2026-08-09; repo convention (COMPOSITE_PCTL_WINDOW/MIN_OBS
# analog); display-only; not owner-ratified.
EXP_BETA_WINDOW = getattr(config, "EXP_BETA_WINDOW", 252)
# LLM-proposed 2026-08-09; repo convention (COMPOSITE_PCTL_WINDOW/MIN_OBS
# analog); display-only; not owner-ratified.
EXP_BETA_HALF_WINDOW = getattr(config, "EXP_BETA_HALF_WINDOW", 126)
# LLM-proposed 2026-08-09; repo convention (COMPOSITE_PCTL_WINDOW/MIN_OBS
# analog); display-only; not owner-ratified.
EXP_BETA_MIN_OBS = getattr(config, "EXP_BETA_MIN_OBS", 126)
# LLM-proposed 2026-08-09; repo convention (COMPOSITE_PCTL_WINDOW/MIN_OBS
# analog); display-only; not owner-ratified.
EXP_BETA_UNSTABLE_DELTA = getattr(config, "EXP_BETA_UNSTABLE_DELTA", 0.5)

_CAVEAT = (
    "Betas drift toward 1 in sharp selloffs; a calm-period beta "
    "understates crash co-movement. Descriptive history, not a forecast."
)


def _blocked_beta(
    reason: str,
    *,
    asof: str,
    max_asof: str | None = None,
    n_obs: int = 0,
) -> dict:
    return {
        "experiment_id": "EXP-BETA",
        "state": "DATA_BLOCKED",
        "data_blocked": True,
        "reason": reason,
        "asof": asof,
        "max_asof": max_asof,
        "beta": None,
        "r_squared": None,
        "beta_half_window": None,
        "n_obs": n_obs,
        "caveat": _CAVEAT,
    }


def _iso_date(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()


def _log_returns(closes: pd.Series, name: str) -> pd.Series:
    numeric = pd.to_numeric(closes, errors="coerce").astype(float)
    numeric = numeric.where(numeric > 0.0)
    return np.log(numeric).diff().rename(name)


def _beta(name_returns: pd.Series, bench_returns: pd.Series) -> float:
    return float(name_returns.cov(bench_returns) / bench_returns.var(ddof=1))


def exp_beta_qqq(
    closes: pd.Series,
    bench_closes: pd.Series,
    *,
    asof: str,
) -> dict:
    """Compute descriptive rolling beta diagnostics from pre-truncated closes."""
    if bench_closes.empty:
        return _blocked_beta("benchmark QQQ series unavailable", asof=asof)

    common_closes = pd.concat(
        [closes.rename("name"), bench_closes.rename("benchmark")],
        axis=1,
        join="inner",
    ).dropna()
    max_asof = None if common_closes.empty else _iso_date(common_closes.index[-1])

    paired = (
        pd.concat(
            [_log_returns(closes, "name"), _log_returns(bench_closes, "benchmark")],
            axis=1,
            join="inner",
        )
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    window = paired.tail(EXP_BETA_WINDOW)
    n_obs = len(window)
    if n_obs < EXP_BETA_MIN_OBS:
        return _blocked_beta(
            f"insufficient overlapping history (<{EXP_BETA_MIN_OBS} sessions)",
            asof=asof,
            max_asof=max_asof,
            n_obs=n_obs,
        )

    benchmark_variance = float(window["benchmark"].var(ddof=1))
    half_window = window.tail(EXP_BETA_HALF_WINDOW)
    half_benchmark_variance = float(half_window["benchmark"].var(ddof=1))
    if (
        not np.isfinite(benchmark_variance)
        or not np.isfinite(half_benchmark_variance)
        or benchmark_variance <= np.finfo(float).eps
        or half_benchmark_variance <= np.finfo(float).eps
    ):
        return _blocked_beta(
            "degenerate benchmark variance",
            asof=asof,
            max_asof=max_asof,
            n_obs=n_obs,
        )

    beta = _beta(window["name"], window["benchmark"])
    beta_half_window = _beta(half_window["name"], half_window["benchmark"])
    correlation = float(window["name"].corr(window["benchmark"]))
    unstable = (
        np.sign(beta) != np.sign(beta_half_window)
        or abs(beta - beta_half_window) > EXP_BETA_UNSTABLE_DELTA
    )
    return {
        "experiment_id": "EXP-BETA",
        "state": "UNSTABLE" if unstable else "OK",
        "data_blocked": False,
        "reason": None,
        "asof": asof,
        "max_asof": max_asof,
        "beta": beta,
        "r_squared": correlation**2,
        "beta_half_window": beta_half_window,
        "n_obs": n_obs,
        "caveat": _CAVEAT,
    }


def build_exp_beta_board(symbols: list[str], *, asof: str) -> list[dict]:
    """Build one fail-visible EXP-BETA card per symbol from cached closes."""
    try:
        benchmark = load_closes_adjusted("QQQ", config.BACKTEST_START, asof, allow_oos=True).loc[
            :asof
        ]
    except Exception as exc:
        reason = f"benchmark QQQ load failed ({exc.__class__.__name__}: {exc})"
        return [{"symbol": symbol, **_blocked_beta(reason, asof=asof)} for symbol in symbols]
    if benchmark.empty:
        return [
            {
                "symbol": symbol,
                **_blocked_beta("benchmark QQQ series unavailable", asof=asof),
            }
            for symbol in symbols
        ]

    cards: list[dict] = []
    for symbol in symbols:
        try:
            closes = load_closes_adjusted(symbol, config.BACKTEST_START, asof, allow_oos=True).loc[
                :asof
            ]
            card = exp_beta_qqq(closes, benchmark, asof=asof)
        except Exception as exc:
            card = _blocked_beta(
                f"close load failed ({exc.__class__.__name__}: {exc})",
                asof=asof,
            )
        cards.append({"symbol": symbol, **card})
    return cards

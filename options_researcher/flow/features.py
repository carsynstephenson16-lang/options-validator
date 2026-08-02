"""Small, point-in-time flow feature frame built from normalized trades."""
from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

from data.options_flow.aggregate import aggregate_flow, attach_prior_open_interest


def _prior_spike(values: pd.Series, minimum: int = 20) -> tuple[pd.Series, pd.Series]:
    log_values = np.log1p(values.astype(float))
    scores: list[float] = []
    percentiles: list[float] = []
    history: list[float] = []
    for value in log_values:
        if len(history) < minimum:
            scores.append(np.nan)
            percentiles.append(np.nan)
        else:
            prior = np.asarray(history[-60:], dtype=float)
            median = float(np.median(prior))
            mad = float(np.median(np.abs(prior - median)))
            scores.append((float(value) - median) / (1.4826 * mad) if mad else np.nan)
            percentiles.append(float((prior <= value).mean()))
        history.append(float(value))
    return pd.Series(scores, index=values.index), pd.Series(percentiles, index=values.index)


def _intraday_acceleration(trades: pd.DataFrame) -> dict[tuple[str, str], float]:
    intraday = aggregate_flow(trades, interval="30min")
    if intraday.empty:
        return {}
    output: dict[tuple[str, str], float] = {}
    for key, group in intraday.groupby(["symbol", "session"], sort=True):
        symbol, session = cast(tuple[object, object], key)
        ordered = group.sort_values("time_bin")
        prior = ordered["total_premium"].iloc[:-1]
        current = float(ordered["total_premium"].iloc[-1])
        output[(str(symbol), str(session))] = current / max(float(prior.mean()), 1.0) if not prior.empty else np.nan
    return output


def build_flow_features(
    trades: pd.DataFrame,
    open_interest: pd.DataFrame | None = None,
    *,
    underlying_prices: dict[str, float] | None = None,
    underlying_quotes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build daily display-only flow fields with prior-only unusual scores."""
    enriched = trades.copy(deep=True)
    if open_interest is not None:
        enriched = attach_prior_open_interest(enriched, open_interest)
    elif "prior_open_interest" not in enriched.columns:
        enriched["prior_open_interest"] = np.nan
    daily = aggregate_flow(
        enriched,
        interval="1D",
        underlying_prices=underlying_prices,
        underlying_quotes=underlying_quotes,
    )
    if daily.empty:
        return daily
    daily["premium_spike_score"], daily["premium_percentile"] = (np.nan, np.nan)
    for symbol, indices in daily.groupby("symbol", sort=True).groups.items():
        ordered = daily.loc[indices].sort_values("session")
        scores, percentiles = _prior_spike(ordered["total_premium"])
        daily.loc[ordered.index, "premium_spike_score"] = scores.to_numpy()
        daily.loc[ordered.index, "premium_percentile"] = percentiles.to_numpy()
    acceleration = _intraday_acceleration(enriched)
    daily["intraday_premium_acceleration"] = [
        acceleration.get((str(symbol), str(session)), np.nan)
        for symbol, session in zip(daily["symbol"], daily["session"])
    ]
    daily["baseline_status"] = np.where(
        daily["premium_percentile"].notna(), "READY", "SPARSE_BASELINE"
    )
    daily["log_total_contracts"] = np.log1p(daily["total_contracts"].astype(float))
    daily["log_unique_contracts"] = np.log1p(daily["unique_contracts"].astype(float))
    daily["direction_label"] = "AGGRESSOR_SIGNED_NOT_CUSTOMER_OR_DEALER_INTENT"
    return daily

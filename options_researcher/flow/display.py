"""Descriptive-only rendering contract for flow fields."""

from __future__ import annotations

import pandas as pd

DISPLAY_AUTHORITY = "DISPLAY_ONLY_RESEARCH_NONCAUSAL"
DISPLAY_DISCLAIMER = (
    "Historical flow fields are descriptive, observational, and noncausal; this is not "
    "a trade recommendation or evidence of customer intent or dealer positioning."
)
DISPLAY_COLUMNS = (
    "symbol",
    "session",
    "total_call_premium",
    "total_put_premium",
    "explicit_aggressor_signed_premium",
    "quote_proxy_signed_premium",
    "explicit_signed_volume_coverage",
    "proxy_signed_volume_coverage",
    "sweep_premium",
    "complex_order_share",
    "premium_percentile",
    "premium_spike_score",
    "baseline_status",
    "direction_label",
)


def descriptive_flow_view(features: pd.DataFrame) -> pd.DataFrame:
    """Return report-safe columns plus fixed noncausal display metadata."""
    missing = sorted(set(DISPLAY_COLUMNS) - set(features.columns))
    if missing:
        raise ValueError(f"flow display missing columns: {missing}")
    output = features.loc[:, DISPLAY_COLUMNS].copy()
    output["authority"] = DISPLAY_AUTHORITY
    output["disclaimer"] = DISPLAY_DISCLAIMER
    return output

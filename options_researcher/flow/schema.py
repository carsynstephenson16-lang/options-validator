"""Versioned, display-only session and analog record contracts."""
from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

SESSION_RECORD_SCHEMA = "options_flow_session_record_v2"

ACTIVITY_FIELDS = (
    "total_contracts",
    "unique_contracts",
    "call_contract_share",
    "volume_oi_ratio",
    "large_trade_concentration",
    "auction_share",
    "complex_order_share",
    "sweep_share",
)
OPTIONALITY_FIELDS = (
    "short_dte_share",
    "medium_dte_share",
    "long_dte_share",
    "volume_weighted_median_log1p_dte",
    "atm_contract_share",
    "deep_otm_contract_share",
    "moneyness_volume_coverage",
    "moneyness_source",
)
SIGNED_FIELDS = (
    "explicit_aggressor_signed_premium",
    "quote_proxy_signed_premium",
    "explicit_signed_volume_coverage",
    "proxy_signed_volume_coverage",
)
ECONOMIC_FIELDS = (
    "gross_premium_adv20",
    "gross_delta_equiv_adv20",
    "gross_gamma_1pct_adv20",
    "gross_vega_1vol_adv20",
    "greek_volume_coverage",
)

DISTANCE_FEATURES = (
    "log_total_contracts",
    "log_unique_contracts",
    "call_contract_share",
    "volume_oi_ratio",
    "large_trade_concentration",
    "auction_share",
    "complex_order_share",
    "sweep_share",
    "short_dte_share",
    "medium_dte_share",
    "volume_weighted_median_log1p_dte",
    "atm_contract_share",
    "deep_otm_contract_share",
    "gross_premium_adv20",
    "gross_delta_equiv_adv20",
)


def _clean(value: object) -> object:
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    return value


def _block(row: Mapping[str, object], fields: tuple[str, ...]) -> dict[str, object]:
    return {field: _clean(row.get(field)) for field in fields}


def build_session_record(
    row: Mapping[str, object],
    *,
    iv_context: Mapping[str, object],
    event_context: Mapping[str, object],
    data_quality: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Create the nested public record without importing scoring code."""
    missing = sorted({"symbol", "session"} - set(row))
    if missing:
        raise ValueError(f"session record missing identity fields: {missing}")
    return {
        "schema": SESSION_RECORD_SCHEMA,
        "symbol": str(row["symbol"]),
        "session": str(row["session"]),
        "activity_features": _block(row, ACTIVITY_FIELDS),
        "optionality_features": _block(row, OPTIONALITY_FIELDS),
        "signed_features": _block(row, SIGNED_FIELDS),
        "economic_intensity": _block(row, ECONOMIC_FIELDS),
        "iv_context": {key: _clean(value) for key, value in iv_context.items()},
        "event_context": {key: _clean(value) for key, value in event_context.items()},
        "data_quality": {key: _clean(value) for key, value in data_quality.items()},
        "provenance": {key: _clean(value) for key, value in provenance.items()},
        "authority": "DISPLAY_ONLY_RESEARCH_NONCAUSAL",
    }

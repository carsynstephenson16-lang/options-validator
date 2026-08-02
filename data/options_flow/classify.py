"""Confidence-based quote-relative side and trade-condition classification."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

SIDE_TOLERANCE = 0.10

# The integer IDs are provider condition identifiers, not inferred direction.
CONDITION_NAMES: Mapping[int, str] = {
    0: "REGULAR_TRADE",
    40: "CANCEL",
    41: "CANCEL_LAST",
    42: "CANCEL_OPEN",
    43: "CANCEL_ONLY",
    44: "CANCEL_STOPPED",
    95: "INTERMARKET_SWEEP",
    125: "SINGLE_LEG_AUCTION_NON_ISO",
    126: "SINGLE_LEG_AUCTION_ISO",
    127: "SINGLE_LEG_CROSS_NON_ISO",
    128: "SINGLE_LEG_CROSS_ISO",
    129: "SINGLE_LEG_FLOOR_TRADE",
    130: "MULTI_LEG_AUTO_ELECTRONIC",
    131: "MULTI_LEG_AUCTION",
    132: "MULTI_LEG_CROSS",
    133: "MULTI_LEG_FLOOR_TRADE",
    145: "BID_AGGRESSOR",
    146: "ASK_AGGRESSOR",
}


def _condition_class(condition: int) -> str:
    name = CONDITION_NAMES.get(condition)
    if name is None:
        return "UNCLASSIFIED_CONDITION"
    if "CANCEL" in name:
        return "CANCEL_OR_CORRECTION"
    if "INTERMARKET_SWEEP" in name:
        return "CONFIRMED_INTERMARKET_SWEEP"
    if "MULTI_LEG" in name:
        return "MULTI_LEG_COMPLEX"
    if "AUCTION" in name:
        return "AUCTION"
    if "CROSS" in name:
        return "CROSS"
    if "FLOOR" in name:
        return "FLOOR_TRADE"
    return "CONDITION_FLAG_ONLY"


def classify_trades(frame: pd.DataFrame) -> pd.DataFrame:
    """Add side/confidence/condition columns without asserting trader intent."""
    required = {"trade_price", "bid", "ask", "trade_condition", "size", "mid", "spread"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"classification missing columns: {missing}")
    out = frame.copy(deep=True)
    condition_values = np.asarray(
        pd.to_numeric(out["trade_condition"], errors="coerce"), dtype=float
    )
    if not bool(np.isfinite(condition_values).all()):
        raise ValueError("classification: trade condition must be finite numeric")
    if not bool(np.equal(condition_values, np.trunc(condition_values)).all()):
        raise ValueError("classification: trade condition must be integral")
    conditions = pd.Series(condition_values.astype(int), index=out.index, dtype="int64")
    out["condition_name"] = conditions.map(dict(CONDITION_NAMES)).fillna("UNCLASSIFIED_CONDITION")
    out["condition_class"] = conditions.astype(int).map(_condition_class)
    out["explicit_aggressor_side"] = "UNKNOWN"
    out.loc[conditions.eq(145), "explicit_aggressor_side"] = "BID_AGGRESSOR"
    out.loc[conditions.eq(146), "explicit_aggressor_side"] = "ASK_AGGRESSOR"
    spread = out["spread"]
    valid_quote = (out["bid"] >= 0) & (out["ask"] >= out["bid"]) & (out["mid"] > 0) & (spread > 0)
    ask_edge = out["ask"] - SIDE_TOLERANCE * spread
    bid_edge = out["bid"] + SIDE_TOLERANCE * spread
    out["side"] = "MID_UNCERTAIN"
    out.loc[valid_quote & (out["trade_price"] >= ask_edge), "side"] = "LIKELY_ASK_SIDE"
    out.loc[valid_quote & (out["trade_price"] <= bid_edge), "side"] = "LIKELY_BID_SIDE"
    outside = (
        (out["bid"] >= 0)
        & (out["ask"] >= out["bid"])
        & ((out["trade_price"] < out["bid"]) | (out["trade_price"] > out["ask"]))
    )
    out.loc[outside, "side"] = "OUTSIDE_MARKET_INVALID"
    out["confidence"] = 0.0
    out.loc[out["side"].isin(["LIKELY_ASK_SIDE", "LIKELY_BID_SIDE"]), "confidence"] = 1.0
    out.loc[out["side"] == "MID_UNCERTAIN", "confidence"] = 0.0
    out.loc[out["condition_class"] != "CONDITION_FLAG_ONLY", "confidence"] *= 0.5
    out["explicit_directional_eligible"] = out["explicit_aggressor_side"].ne("UNKNOWN") & out[
        "side"
    ].ne("OUTSIDE_MARKET_INVALID")
    out["proxy_directional_eligible"] = (
        out["side"].isin(["LIKELY_ASK_SIDE", "LIKELY_BID_SIDE"])
        & conditions.eq(0)
        & ~out["explicit_directional_eligible"]
    )
    out["directional_eligible"] = (
        out["explicit_directional_eligible"] | out["proxy_directional_eligible"]
    )
    out["aggressor_source"] = "UNKNOWN"
    out.loc[out["proxy_directional_eligible"], "aggressor_source"] = "QUOTE_ASK_BID_PROXY"
    out.loc[out["explicit_directional_eligible"], "aggressor_source"] = "EXCHANGE_EXPLICIT"
    return out

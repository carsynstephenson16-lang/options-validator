"""Deterministic daily/intraday flow aggregation."""

from __future__ import annotations

from datetime import date
from typing import cast

import numpy as np
import pandas as pd

from .classify import classify_trades


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, frame[name])


def attach_prior_open_interest(
    trades: pd.DataFrame,
    open_interest: pd.DataFrame,
) -> pd.DataFrame:
    """Join only OI that was known strictly before each matching trade."""
    keys = ["symbol", "expiration", "strike", "right"]
    trade_required = set(keys) | {"trade_timestamp"}
    missing_trades = sorted(trade_required - set(trades.columns))
    if missing_trades:
        raise ValueError(f"trades missing columns: {missing_trades}")
    required = set(keys) | {"open_interest", "oi_timestamp"}
    missing = sorted(required - set(open_interest.columns))
    if missing:
        raise ValueError(f"open interest missing columns: {missing}")
    left = trades.copy()
    left["_trade_timestamp_utc"] = pd.to_datetime(
        left["trade_timestamp"], errors="coerce", utc=True
    )
    if bool(left["_trade_timestamp_utc"].isna().any()):
        raise ValueError("trades contain malformed trade_timestamp")
    oi = open_interest.loc[:, keys + ["open_interest", "oi_timestamp"]].copy()
    oi["_oi_timestamp_utc"] = pd.to_datetime(oi["oi_timestamp"], errors="coerce", utc=True)
    if bool(oi["_oi_timestamp_utc"].isna().any()):
        raise ValueError("open interest contains malformed oi_timestamp")
    matching_timestamps = left.loc[:, keys + ["_trade_timestamp_utc"]].merge(
        oi.loc[:, keys + ["_oi_timestamp_utc"]],
        on=keys,
        how="inner",
    )
    if bool(
        matching_timestamps["_oi_timestamp_utc"]
        .ge(matching_timestamps["_trade_timestamp_utc"])
        .any()
    ):
        raise ValueError("open interest must be strictly prior to the matching trade timestamp")
    if oi.duplicated(keys).any():
        counts = oi.groupby(keys, dropna=False)["open_interest"].nunique()
        if (counts > 1).any():
            raise ValueError("conflicting open interest observations for a contract")
        oi = oi.drop_duplicates(keys)
    out = left.merge(
        oi.drop(columns="_oi_timestamp_utc"),
        on=keys,
        how="left",
        validate="many_to_one",
    ).drop(columns="_trade_timestamp_utc")
    out = out.rename(columns={"open_interest": "prior_open_interest"})
    return out


def _session_date(value: object) -> str:
    timestamp = cast(pd.Timestamp, pd.to_datetime(str(value), errors="coerce", utc=True))
    if pd.isna(timestamp):
        raise ValueError(f"invalid trade timestamp: {value!r}")
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("America/New_York").date().isoformat()


def _moneyness_log(right: str, strike: float, underlying: float | None) -> float:
    if underlying is None or not np.isfinite(underlying) or underlying <= 0:
        return np.nan
    return float(np.log(strike / underlying) if right == "C" else np.log(underlying / strike))


def _moneyness(value: float) -> str:
    if not np.isfinite(value):
        return "UNKNOWN"
    if abs(value) <= 0.02:
        return "ATM"
    return "OTM" if value > 0.02 else "ITM"


def _dte(expiration: str, session: str) -> int:
    return (date.fromisoformat(expiration) - date.fromisoformat(session)).days


def _sum(frame: pd.DataFrame, mask: pd.Series, column: str = "premium") -> float:
    return float(frame.loc[mask, column].sum())


def _weighted_median(values: pd.Series, weights: pd.Series) -> float:
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not bool(valid.any()):
        return np.nan
    ordered = pd.DataFrame(
        {"value": values.loc[valid].astype(float), "weight": weights.loc[valid].astype(float)}
    ).sort_values("value")
    threshold = float(ordered["weight"].sum()) / 2.0
    return float(ordered.loc[ordered["weight"].cumsum().ge(threshold), "value"].iloc[0])


def attach_underlying_quotes(
    trades: pd.DataFrame,
    underlying_quotes: pd.DataFrame,
) -> pd.DataFrame:
    """Attach the last underlying midpoint at or before each option trade."""
    required = {"symbol", "timestamp", "bid", "ask"}
    missing = sorted(required - set(underlying_quotes.columns))
    if missing:
        raise ValueError(f"underlying quotes missing columns: {missing}")
    left = trades.copy()
    left["_row_order"] = np.arange(len(left))
    left["trade_timestamp"] = pd.to_datetime(left["trade_timestamp"], errors="coerce", utc=True)
    right = underlying_quotes.loc[:, list(required)].copy()
    right["timestamp"] = pd.to_datetime(
        right["timestamp"], errors="coerce", utc=True, format="mixed"
    )
    right["bid"] = pd.to_numeric(right["bid"], errors="coerce")
    right["ask"] = pd.to_numeric(right["ask"], errors="coerce")
    if bool(right[["timestamp", "bid", "ask"]].isna().to_numpy().any()):
        raise ValueError("underlying quotes contain malformed rows")
    if bool((right["ask"] < right["bid"]).any()) or bool((right["bid"] < 0).any()):
        raise ValueError("underlying quotes contain invalid markets")
    right["underlying_price"] = (right["bid"] + right["ask"]) / 2.0
    right = right.rename(columns={"timestamp": "underlying_quote_timestamp"})
    merged = pd.merge_asof(
        left.sort_values("trade_timestamp"),
        right.sort_values("underlying_quote_timestamp"),
        left_on="trade_timestamp",
        right_on="underlying_quote_timestamp",
        by="symbol",
        direction="backward",
        allow_exact_matches=True,
        suffixes=("", "_underlying"),
    )
    merged["moneyness_source"] = np.where(
        merged["underlying_quote_timestamp"].notna(),
        "STRICT_PRIOR_UNDERLYING_QUOTE",
        "UNAVAILABLE",
    )
    return merged.sort_values("_row_order").drop(columns="_row_order").reset_index(drop=True)


def _signed_premium(group: pd.DataFrame, eligible: pd.Series, side_column: str) -> float:
    ask = group[side_column].isin(["LIKELY_ASK_SIDE", "ASK_AGGRESSOR"])
    bid = group[side_column].isin(["LIKELY_BID_SIDE", "BID_AGGRESSOR"])
    return (
        _sum(group, eligible & group["right"].eq("C") & ask)
        + _sum(group, eligible & group["right"].eq("P") & bid)
        - _sum(group, eligible & group["right"].eq("C") & bid)
        - _sum(group, eligible & group["right"].eq("P") & ask)
    )


def _economic_intensity(group: pd.DataFrame, valid: pd.Series) -> dict[str, float]:
    output = {
        "gross_premium_adv20": np.nan,
        "gross_delta_equiv_adv20": np.nan,
        "gross_gamma_1pct_adv20": np.nan,
        "gross_vega_1vol_adv20": np.nan,
        "greek_volume_coverage": np.nan,
    }
    simple = valid & ~group["condition_class"].isin(
        ["MULTI_LEG_COMPLEX", "AUCTION", "CROSS", "CANCEL_OR_CORRECTION"]
    )
    if "underlying_adv20_dollars" in group:
        dollar_adv_series = _column(group, "underlying_adv20_dollars")
        denominator = (
            float(dollar_adv_series.dropna().iloc[0])
            if bool(dollar_adv_series.notna().any())
            else np.nan
        )
        if np.isfinite(denominator) and denominator > 0:
            output["gross_premium_adv20"] = float(group.loc[simple, "premium"].sum()) / denominator
    greek_columns = {"delta", "gamma", "vega", "contract_multiplier", "underlying_price"}
    if not greek_columns.issubset(group.columns):
        return output
    greek_valid = simple & group.loc[:, list(greek_columns)].notna().all(axis=1)
    simple_volume = float(group.loc[simple, "size"].sum())
    coverage = float(group.loc[greek_valid, "size"].sum()) / simple_volume if simple_volume else 0.0
    output["greek_volume_coverage"] = coverage
    if coverage < 0.90:
        return output
    size = group.loc[greek_valid, "size"].astype(float)
    multiplier = group.loc[greek_valid, "contract_multiplier"].astype(float)
    if "underlying_adv20_shares" in group and bool(
        _column(group, "underlying_adv20_shares").notna().any()
    ):
        share_adv = float(_column(group, "underlying_adv20_shares").dropna().iloc[0])
        if share_adv > 0:
            output["gross_delta_equiv_adv20"] = (
                float((group.loc[greek_valid, "delta"].abs() * size * multiplier).sum()) / share_adv
            )
    dollar_adv = (
        float(group["underlying_adv20_dollars"].dropna().iloc[0])
        if "underlying_adv20_dollars" in group
        and bool(_column(group, "underlying_adv20_dollars").notna().any())
        else np.nan
    )
    if not np.isfinite(dollar_adv) or dollar_adv <= 0:
        return output
    if "gamma_unit_verified" in group and bool(group.loc[greek_valid, "gamma_unit_verified"].all()):
        spot = group.loc[greek_valid, "underlying_price"].astype(float)
        output["gross_gamma_1pct_adv20"] = (
            float(
                (
                    group.loc[greek_valid, "gamma"].abs() * spot.pow(2) * size * multiplier * 0.01
                ).sum()
            )
            / dollar_adv
        )
    if "vega_unit_verified" in group and bool(group.loc[greek_valid, "vega_unit_verified"].all()):
        output["gross_vega_1vol_adv20"] = (
            float((group.loc[greek_valid, "vega"].abs() * size * multiplier).sum()) / dollar_adv
        )
    return output


def _aggregate_group(group: pd.DataFrame, *, underlying: float | None) -> dict[str, object]:
    valid = group["side"] != "OUTSIDE_MARKET_INVALID"
    calls = valid & group["right"].eq("C")
    puts = valid & group["right"].eq("P")
    ask = group["side"].eq("LIKELY_ASK_SIDE")
    bid = group["side"].eq("LIKELY_BID_SIDE")
    total = float(group.loc[valid, "premium"].sum())
    contracts = float(group.loc[valid, "size"].sum())
    oi_rows = group.loc[
        valid,
        ["expiration", "strike", "right", "prior_open_interest"],
    ].drop_duplicates(["expiration", "strike", "right"])
    oi_denominator = float(oi_rows["prior_open_interest"].dropna().sum())
    complex_mask = group["condition_class"].eq("MULTI_LEG_COMPLEX")
    sweep_mask = group["condition_class"].eq("CONFIRMED_INTERMARKET_SWEEP")
    auction_mask = group["condition_class"].eq("AUCTION")
    large_cutoff = float(group.loc[valid, "premium"].quantile(0.95)) if valid.any() else 0.0
    repeated = (
        group.loc[valid].groupby(["expiration", "strike", "right"], dropna=False)["size"].sum()
    )
    dte_short = valid & group["dte"].lt(5)
    dte_medium = valid & group["dte"].between(5, 30, inclusive="both")
    dte_long = valid & group["dte"].gt(30)
    moneyness_known = valid & group["moneyness_log"].notna()
    result = {
        "symbol": str(group["symbol"].iloc[0]),
        "session": str(group["session"].iloc[0]),
        "time_bin": str(group["time_bin"].iloc[0]),
        "total_call_premium": _sum(group, calls),
        "total_put_premium": _sum(group, puts),
        "ask_call_premium": _sum(group, calls & ask),
        "ask_put_premium": _sum(group, puts & ask),
        "bid_call_premium": _sum(group, calls & bid),
        "bid_put_premium": _sum(group, puts & bid),
        "call_put_premium_ratio": _sum(group, calls) / (_sum(group, puts) + 1.0),
        "directional_net_premium": _signed_premium(
            group, _column(group, "proxy_directional_eligible"), "side"
        ),
        "explicit_aggressor_signed_premium": _signed_premium(
            group,
            _column(group, "explicit_directional_eligible"),
            "explicit_aggressor_side",
        ),
        "quote_proxy_signed_premium": _signed_premium(
            group, _column(group, "proxy_directional_eligible"), "side"
        ),
        "explicit_signed_volume_coverage": float(
            group.loc[group["explicit_directional_eligible"], "size"].sum()
        )
        / max(contracts, 1.0),
        "proxy_signed_volume_coverage": float(
            group.loc[group["proxy_directional_eligible"], "size"].sum()
        )
        / max(contracts, 1.0),
        "total_contracts": contracts,
        "unique_contracts": int(
            group.loc[valid, ["expiration", "strike", "right"]].drop_duplicates().shape[0]
        ),
        "call_contract_share": float(group.loc[calls, "size"].sum()) / max(contracts, 1.0),
        "volume_oi_ratio": contracts / max(oi_denominator, 1.0) if oi_denominator else np.nan,
        "sweep_premium": _sum(group, sweep_mask & valid),
        "sweep_count": int((sweep_mask & valid).sum()),
        "complex_order_share": float(group.loc[complex_mask & valid, "size"].sum())
        / max(contracts, 1.0),
        "auction_share": float(group.loc[auction_mask & valid, "size"].sum()) / max(contracts, 1.0),
        "sweep_share": float(group.loc[sweep_mask & valid, "size"].sum()) / max(contracts, 1.0),
        "large_trade_concentration": float(
            group.loc[valid & group["premium"].ge(large_cutoff), "premium"].sum()
        )
        / max(total, 1.0),
        "repeated_contract_share": float(repeated.max() if not repeated.empty else 0.0)
        / max(contracts, 1.0),
        "short_dated_premium": _sum(group, valid & group["dte"].le(30)),
        "long_dated_premium": _sum(group, valid & group["dte"].gt(30)),
        "otm_premium": _sum(group, valid & group["moneyness"].eq("OTM")),
        "atm_premium": _sum(group, valid & group["moneyness"].eq("ATM")),
        "itm_premium": _sum(group, valid & group["moneyness"].eq("ITM")),
        "total_premium": total,
        "total_valid_trades": int(valid.sum()),
        "short_dte_share": float(group.loc[dte_short, "size"].sum()) / max(contracts, 1.0),
        "medium_dte_share": float(group.loc[dte_medium, "size"].sum()) / max(contracts, 1.0),
        "long_dte_share": float(group.loc[dte_long, "size"].sum()) / max(contracts, 1.0),
        "volume_weighted_median_log1p_dte": _weighted_median(
            np.log1p(group.loc[valid, "dte"]), group.loc[valid, "size"]
        ),
        "atm_contract_share": float(
            group.loc[moneyness_known & group["moneyness_log"].abs().le(0.02), "size"].sum()
        )
        / max(float(group.loc[moneyness_known, "size"].sum()), 1.0),
        "deep_otm_contract_share": float(
            group.loc[moneyness_known & group["moneyness_log"].gt(0.10), "size"].sum()
        )
        / max(float(group.loc[moneyness_known, "size"].sum()), 1.0),
        "moneyness_volume_coverage": float(group.loc[moneyness_known, "size"].sum())
        / max(contracts, 1.0),
        "moneyness_source": (
            "STRICT_PRIOR_UNDERLYING_QUOTE"
            if group.loc[moneyness_known, "moneyness_source"]
            .eq("STRICT_PRIOR_UNDERLYING_QUOTE")
            .all()
            and bool(moneyness_known.any())
            else "SESSION_PRICE_PROXY_OR_UNAVAILABLE"
        ),
    }
    result.update(_economic_intensity(group, valid))
    return result


def aggregate_flow(
    trades: pd.DataFrame,
    *,
    interval: str = "1D",
    underlying_prices: dict[str, float] | None = None,
    underlying_quotes: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Aggregate classified trades into deterministic session/time bins."""
    if trades.empty:
        return pd.DataFrame()
    classified = classify_trades(trades) if "side" not in trades.columns else trades.copy()
    out = (
        attach_underlying_quotes(classified, underlying_quotes)
        if underlying_quotes is not None
        else classified.copy()
    )
    out["session"] = out["trade_timestamp"].map(_session_date)
    out["time_bin"] = (
        pd.to_datetime(out["trade_timestamp"], utc=True)
        .dt.tz_convert("America/New_York")
        .dt.floor(interval)
        .dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    )
    out["dte"] = [
        _dte(expiration, session) for expiration, session in zip(out["expiration"], out["session"])
    ]
    prices = underlying_prices or {}
    if "underlying_price" not in out:
        out["underlying_price"] = [prices.get(session, np.nan) for session in out["session"]]
        out["moneyness_source"] = np.where(
            out["underlying_price"].notna(), "SESSION_PRICE_PROXY", "UNAVAILABLE"
        )
    out["moneyness_log"] = [
        _moneyness_log(right, float(strike), float(underlying) if pd.notna(underlying) else None)
        for right, strike, underlying in zip(out["right"], out["strike"], out["underlying_price"])
    ]
    out["moneyness"] = out["moneyness_log"].map(_moneyness)
    rows = [
        _aggregate_group(group, underlying=prices.get(str(group["session"].iloc[0])))
        for _, group in out.groupby(["symbol", "session", "time_bin"], sort=True)
    ]
    return pd.DataFrame(rows).sort_values(["symbol", "session", "time_bin"]).reset_index(drop=True)

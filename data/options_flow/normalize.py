"""Strict normalization for immutable ThetaData flow captures."""

from __future__ import annotations

import hashlib
from datetime import date
from typing import cast

import numpy as np
import pandas as pd

RAW_TRADE_QUOTE_COLUMNS = (
    "symbol",
    "expiration",
    "strike",
    "right",
    "trade_timestamp",
    "quote_timestamp",
    "sequence",
    "trade_condition",
    "exchange",
    "size",
    "trade_price",
    "bid",
    "ask",
    "bid_size",
    "ask_size",
    "source",
    "acquisition_timestamp",
    "source_version",
)
NORMALIZED_COLUMNS = RAW_TRADE_QUOTE_COLUMNS + (
    "stable_trade_id",
    "premium",
    "mid",
    "spread",
    "relative_spread",
)
OI_COLUMNS = (
    "symbol",
    "expiration",
    "strike",
    "right",
    "oi_timestamp",
    "open_interest",
    "source",
    "acquisition_timestamp",
    "source_version",
)

_RIGHTS = {"C": "C", "CALL": "C", "P": "P", "PUT": "P"}
_NUMERIC_TRADE = (
    "strike",
    "sequence",
    "trade_condition",
    "exchange",
    "size",
    "trade_price",
    "bid",
    "ask",
    "bid_size",
    "ask_size",
)


def _require_columns(frame: pd.DataFrame, required: tuple[str, ...], context: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{context}: missing columns {missing}")


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    return cast(pd.Series, frame[name])


def _right(value: object) -> str:
    normalized = str(value).strip().upper()
    if normalized not in _RIGHTS:
        raise ValueError(f"unsupported option right: {value!r}")
    return _RIGHTS[normalized]


def _finite_numeric(frame: pd.DataFrame, columns: tuple[str, ...], context: str) -> None:
    for column in columns:
        values = pd.to_numeric(_column(frame, column), errors="coerce")
        numeric = np.asarray(values, dtype=float)
        if not bool(np.isfinite(numeric).all()):
            raise ValueError(f"{context}: non-numeric {column}")
        frame[column] = numeric


def _utc_aware_timestamps(frame: pd.DataFrame, column: str, context: str) -> pd.Series:
    raw = _column(frame, column)
    parsed: list[pd.Timestamp] = []
    for value in raw:
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{context}: malformed {column}") from exc
        if not isinstance(timestamp, pd.Timestamp):
            raise ValueError(f"{context}: malformed {column}")
        if timestamp.tzinfo is None:
            raise ValueError(
                f"{context}: timezone-naive {column}; verify the entitlement-probe gate "
                "before ingesting raw provider timestamps"
            )
        parsed.append(timestamp)
    return pd.Series(pd.to_datetime(parsed, utc=True), index=raw.index)


def _trade_id(row: pd.Series) -> str:
    identity = "|".join(
        str(row[column])
        for column in (
            "symbol",
            "expiration",
            "strike",
            "right",
            "trade_timestamp",
            "quote_timestamp",
            "sequence",
            "trade_condition",
            "exchange",
            "size",
            "trade_price",
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def normalize_trade_quotes(
    frame: pd.DataFrame,
    *,
    symbol: str,
    session: str,
    acquired_at_utc: str,
    source_version: str,
    source: str = "thetadata.option.history.trade_quote",
) -> pd.DataFrame:
    """Validate and normalize the provider response without dropping rows."""
    required = (
        "expiration",
        "strike",
        "right",
        "trade_timestamp",
        "quote_timestamp",
        "sequence",
        "condition",
        "exchange",
        "size",
        "price",
        "bid",
        "ask",
        "bid_size",
        "ask_size",
    )
    _require_columns(frame, required, "trade_quote")
    out = frame.copy(deep=True)
    out = out.rename(
        columns={
            "condition": "trade_condition",
            "price": "trade_price",
        }
    )
    out.insert(0, "symbol", symbol.upper())
    expiration = pd.to_datetime(_column(out, "expiration"), errors="coerce").dt.strftime("%Y-%m-%d")
    if bool(pd.isna(expiration).to_numpy().any()):
        raise ValueError("trade_quote: malformed expiration")
    out["expiration"] = expiration
    out["right"] = out["right"].map(_right)
    for column in ("trade_timestamp", "quote_timestamp"):
        out[column] = _utc_aware_timestamps(out, column, "trade_quote")
    _finite_numeric(out, _NUMERIC_TRADE, "trade_quote")
    if bool((_column(out, "size") <= 0).any()) or bool((_column(out, "trade_price") < 0).any()):
        raise ValueError("trade_quote: size must be positive and price non-negative")
    if bool((_column(out, "bid") < 0).any()) or bool((_column(out, "ask") < 0).any()):
        raise ValueError("trade_quote: quote prices must be non-negative")
    if bool((_column(out, "ask") < _column(out, "bid")).any()):
        raise ValueError("trade_quote: crossed quote")
    if bool((_column(out, "quote_timestamp") >= _column(out, "trade_timestamp")).any()):
        raise ValueError("trade_quote: quote timestamp must precede trade timestamp")
    if date.fromisoformat(session).weekday() > 4:
        raise ValueError("trade_quote: session must be a weekday")
    out["source"] = source
    out["acquisition_timestamp"] = acquired_at_utc
    out["source_version"] = source_version
    out["stable_trade_id"] = out.apply(_trade_id, axis=1)
    if bool(_column(out, "stable_trade_id").duplicated().any()):
        raise ValueError("trade_quote: duplicate stable trade id in provider response")
    out["premium"] = out["trade_price"] * out["size"] * 100.0
    out["mid"] = (out["bid"] + out["ask"]) / 2.0
    out["spread"] = out["ask"] - out["bid"]
    out["relative_spread"] = out["spread"].div(out["mid"].where(out["mid"] > 0))
    return out.loc[:, NORMALIZED_COLUMNS]


def normalize_open_interest(
    frame: pd.DataFrame,
    *,
    symbol: str,
    acquired_at_utc: str,
    source_version: str,
    source: str = "thetadata.option.history.open_interest",
) -> pd.DataFrame:
    """Validate prior-known OI and retain the provider's exact timestamp."""
    _require_columns(
        frame,
        ("expiration", "strike", "right", "timestamp", "open_interest"),
        "open_interest",
    )
    out = frame.copy(deep=True)
    out["symbol"] = symbol.upper()
    expiration = pd.to_datetime(_column(out, "expiration"), errors="coerce").dt.strftime("%Y-%m-%d")
    out["expiration"] = expiration
    out["right"] = out["right"].map(_right)
    out["oi_timestamp"] = _utc_aware_timestamps(out, "timestamp", "open_interest")
    out["strike"] = pd.to_numeric(_column(out, "strike"), errors="coerce")
    out["open_interest"] = pd.to_numeric(_column(out, "open_interest"), errors="coerce")
    if bool(
        pd.isna(out[["expiration", "strike", "oi_timestamp", "open_interest"]]).to_numpy().any()
    ):
        raise ValueError("open_interest: malformed row")
    if bool((_column(out, "strike") <= 0).any()) or bool((_column(out, "open_interest") < 0).any()):
        raise ValueError("open_interest: invalid strike or open interest")
    out["source"] = source
    out["acquisition_timestamp"] = acquired_at_utc
    out["source_version"] = source_version
    return out.loc[:, OI_COLUMNS]

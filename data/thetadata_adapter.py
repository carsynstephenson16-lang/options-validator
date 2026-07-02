"""
data/thetadata_adapter.py -- EOD option-chain access with local caching.

STATUS: PHASE 0. The helpers (mid_price, passes_liquidity, caching) are real and
correct. The actual ThetaData fetch is stubbed -- wire and VERIFY it against your
installed library before you trust a single fill. Do not treat the fetch path as
tested.

Note: Lumibot ships ThetaDataBacktesting natively, so inside the backtest loop
you will mostly let Lumibot pull data via get_historical_prices / get_quote
rather than calling ThetaData here. This adapter is for (a) the smoke test and
(b) the feasibility/credit-measurement step that runs OUTSIDE the Lumibot loop.
"""
from __future__ import annotations
import os
import re
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

import config  # noqa: F401  (kept for when fetch wiring needs config)

CACHE_DIR = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Schema every downstream consumer expects from a chain DataFrame:
CHAIN_COLUMNS = [
    "expiration", "strike", "right",         # right in {"P", "C"}
    "bid", "ask", "open_interest",
    "iv", "delta", "gamma", "theta", "vega",
]
NUMERIC_CHAIN_COLUMNS = [
    "strike", "bid", "ask", "open_interest",
    "iv", "delta", "gamma", "theta", "vega",
]
_SYMBOL_RE = re.compile(r"^[A-Z0-9._-]+$")


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise ValueError("symbol must be a string")
    normalized = symbol.strip().upper()
    if not normalized or not _SYMBOL_RE.fullmatch(normalized):
        raise ValueError(f"invalid symbol for cache key: {symbol!r}")
    return normalized


def _normalize_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("date must be an ISO date string")
    try:
        return Date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"date must be an ISO date string: {value!r}") from exc


def _cache_path(symbol: str, date: str) -> Path:
    return CACHE_DIR / f"{_normalize_symbol(symbol)}_{_normalize_date(date)}.parquet"


def validate_chain_schema(chain: pd.DataFrame) -> pd.DataFrame:
    """Fail before malformed cached/fetched chain data reaches strategy logic."""
    if not isinstance(chain, pd.DataFrame):
        raise ValueError("option chain must be a pandas DataFrame")
    missing = [col for col in CHAIN_COLUMNS if col not in chain.columns]
    if missing:
        raise ValueError(f"option chain missing required column(s): {missing}")
    if chain["right"].isna().any():
        raise ValueError("option chain column 'right' contains missing values")
    rights = set(chain["right"].astype(str).str.upper().unique())
    invalid_rights = rights - {"P", "C"}
    if invalid_rights:
        raise ValueError(f"option chain has invalid right values: {sorted(invalid_rights)}")
    for col in NUMERIC_CHAIN_COLUMNS:
        values = pd.to_numeric(chain[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"option chain column {col!r} contains non-finite values")
    return chain


def get_eod_chain(symbol: str, date: str) -> pd.DataFrame:
    """Return the EOD option chain for `symbol` on `date` (YYYY-MM-DD).

    PHASE 0 VERIFY:
      - Confirm your ThetaData subscription returns EOD greeks+IV for equities.
      - Wire the ThetaData request here (or route through Lumibot's ThetaData
        datasource) and map its columns onto CHAIN_COLUMNS.
      - Handle EOD gaps: ThetaData can miss EOD marks even when intraday quotes
        exist. Prefer SKIPPING the day (log it) over silently substituting an
        intraday snapshot inside an EOD backtest. (See .cursorrules.)
    """
    symbol = _normalize_symbol(symbol)
    date = _normalize_date(date)
    cached = _cache_path(symbol, date)
    if cached.exists():
        return validate_chain_schema(pd.read_parquet(cached))

    raise NotImplementedError(
        "Wire ThetaData here (Phase 0). Fetch the EOD chain, normalize to "
        "CHAIN_COLUMNS, validate_chain_schema(df), then cache with: "
        "df.to_parquet(_cache_path(symbol, date))."
    )


def mid_price(bid: float, ask: float) -> float:
    """Quote mid. Fills must be at this OR WORSE -- never the favorable side."""
    return (bid + ask) / 2.0


def passes_liquidity(open_interest: float, bid: float, ask: float) -> bool:
    """A contract must pass before it is tradeable. Check BOTH legs."""
    if open_interest < config.MIN_OPEN_INTEREST:
        return False
    if bid < 0 or ask <= 0 or ask < bid:
        return False
    mid = mid_price(bid, ask)
    if mid <= 0:
        return False
    return ((ask - bid) / mid) <= config.MAX_SPREAD_PCT

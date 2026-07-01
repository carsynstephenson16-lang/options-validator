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
from pathlib import Path

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


def _cache_path(symbol: str, date: str) -> Path:
    return CACHE_DIR / f"{symbol}_{date}.parquet"


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
    cached = _cache_path(symbol, date)
    if cached.exists():
        return pd.read_parquet(cached)

    raise NotImplementedError(
        "Wire ThetaData here (Phase 0). Fetch the EOD chain, normalize to "
        "CHAIN_COLUMNS, then cache with: df.to_parquet(_cache_path(symbol, date))."
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

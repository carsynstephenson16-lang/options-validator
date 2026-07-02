"""
data/dolthub.py -- free EOD chain source: DoltHub post-no-preference/options.

GRADE: development / cross-check ONLY -- not verdict-grade. Verified live
2026-07-01: the database is a THIN SUBSET of the real market (e.g. SPY
2022-06-15 has 140 rows across 3 expirations; the 30-45 DTE monthly can be
absent), it carries NO open interest or volume, and provenance is unaudited
community data. open_interest is therefore emitted as 0.0 so the
MIN_OPEN_INTEREST liquidity filter FAILS CLOSED on these chains -- a backtest
on DoltHub data refuses to trade rather than fabricating liquidity.

Coverage seen live: SPY 2019-02-09 .. present. No API key needed for reads.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from data.thetadata_adapter import CHAIN_COLUMNS, NUMERIC_CHAIN_COLUMNS

SQL_API = "https://www.dolthub.com/api/v1alpha1/post-no-preference/options/master"

_RIGHT_MAP = {"put": "P", "call": "C"}

# option_chain columns -> CHAIN_COLUMNS names ('vol' is DoltHub's IV column)
_COLUMN_MAP = {"vol": "iv"}


def _http_get_json(url: str, timeout: float = 60.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310 (https)
        return json.load(resp)


def chain_from_rows(rows: list[dict]) -> pd.DataFrame:
    """Map DoltHub option_chain API rows onto CHAIN_COLUMNS.

    Rows with any non-finite numeric are dropped (the strict schema validator
    would otherwise reject the whole chain for one bad quote)."""
    if not rows:
        raise ValueError("DoltHub returned no option_chain rows")
    df = pd.DataFrame(rows).rename(columns=_COLUMN_MAP)
    right = df["call_put"].astype(str).str.strip().str.lower().map(_RIGHT_MAP)
    if right.isna().any():
        bad = sorted(set(df.loc[right.isna(), "call_put"].astype(str)))
        raise ValueError(f"unknown call_put value(s) from DoltHub: {bad}")
    df["right"] = right
    df["open_interest"] = 0.0  # absent upstream: fail closed, never fabricate
    df["expiration"] = df["expiration"].astype(str)
    for col in NUMERIC_CHAIN_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    finite = np.isfinite(df[NUMERIC_CHAIN_COLUMNS].to_numpy(dtype=float)).all(axis=1)
    df = df.loc[finite]
    if df.empty:
        raise ValueError("DoltHub chain empty after dropping non-finite rows")
    return df[CHAIN_COLUMNS].reset_index(drop=True)


def fetch_eod_chain(symbol: str, date: str, http_get=None) -> pd.DataFrame:
    """Fetch one symbol-day chain via the public SQL API (no auth needed)."""
    http_get = http_get or _http_get_json
    sql = (
        "SELECT `date`, act_symbol, expiration, strike, call_put, bid, ask, "
        "vol, delta, gamma, theta, vega, rho FROM `option_chain` "
        f"WHERE `date` = '{date}' AND act_symbol = '{symbol}'"
    )
    payload = http_get(f"{SQL_API}?q={urllib.parse.quote(sql)}")
    if payload.get("query_execution_status") not in ("Success", "RowLimit"):
        raise RuntimeError(
            f"DoltHub query failed for {symbol} {date}: "
            f"{payload.get('query_execution_message', 'unknown error')}"
        )
    return chain_from_rows(payload.get("rows", []))

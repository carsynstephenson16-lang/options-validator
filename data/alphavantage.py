"""
data/alphavantage.py -- EOD chain source: Alpha Vantage HISTORICAL_OPTIONS.

GRADE: candidate verdict-grade source (full chains, all expirations, bid/ask
with sizes, volume, OPEN INTEREST, IV, greeks; history back to 2008-01-01).
REQUIRES a premium key (~$49.99/mo, cancel anytime): verified live 2026-07-01
that free keys get an "Information: premium endpoint" payload, NOT data --
which this module raises on, loudly, so a gated response can never be cached
or scored as an empty chain.

Known data wart (seen live): computed greeks/IV go nonsensical at extremes
(deep-ITM IV=4.2). Rows failing basic sanity (0 < iv < 3, |delta| <= 1) are
dropped and counted; bid/ask on dropped rows looked fine, but a contract with
unusable greeks cannot be delta-selected anyway.

Key: ALPHAVANTAGE_API_KEY from the environment (.env; run via
`uv run --env-file .env ...`). Never hardcode it.
"""
from __future__ import annotations
import json
import logging
import os
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

from data.thetadata_adapter import CHAIN_COLUMNS, NUMERIC_CHAIN_COLUMNS

QUERY_URL = "https://www.alphavantage.co/query"
_RIGHT_MAP = {"put": "P", "call": "C"}
_COLUMN_MAP = {"implied_volatility": "iv"}
_IV_SANE_MAX = 3.0

log = logging.getLogger(__name__)


def _http_get_json(url: str, timeout: float = 60.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310 (https)
        return json.load(resp)


def chain_from_payload(payload: dict) -> pd.DataFrame:
    """Map a HISTORICAL_OPTIONS payload onto CHAIN_COLUMNS.

    Raises RuntimeError on gate/limit payloads ("Information", "Note",
    "Error Message") and ValueError on empty data."""
    for key in ("Information", "Note", "Error Message"):
        if key in payload:
            raise RuntimeError(f"Alpha Vantage refused the request: {payload[key]}")
    rows = payload.get("data") or []
    if not rows:
        raise ValueError("Alpha Vantage returned no option rows")
    df = pd.DataFrame(rows).rename(columns=_COLUMN_MAP)
    right = df["type"].astype(str).str.strip().str.lower().map(_RIGHT_MAP)
    if right.isna().any():
        bad = sorted(set(df.loc[right.isna(), "type"].astype(str)))
        raise ValueError(f"unknown option type value(s) from Alpha Vantage: {bad}")
    df["right"] = right
    df["expiration"] = df["expiration"].astype(str)
    for col in NUMERIC_CHAIN_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    numeric = df[NUMERIC_CHAIN_COLUMNS].to_numpy(dtype=float)
    finite = np.isfinite(numeric).all(axis=1)
    sane = finite & (df["iv"] > 0) & (df["iv"] < _IV_SANE_MAX) & (df["delta"].abs() <= 1)
    dropped = int((~sane).sum())
    if dropped:
        log.warning("alphavantage: dropped %d/%d rows with non-finite or "
                    "insane greeks", dropped, len(df))
    df = df.loc[sane]
    if df.empty:
        raise ValueError("Alpha Vantage chain empty after sanity filtering")
    return df[CHAIN_COLUMNS].reset_index(drop=True)


def fetch_eod_chain(symbol: str, date: str, api_key: str | None = None,
                    http_get=None) -> pd.DataFrame:
    api_key = api_key or os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY not set (put it in .env and "
                           "run via `uv run --env-file .env ...`)")
    http_get = http_get or _http_get_json
    params = urllib.parse.urlencode({
        "function": "HISTORICAL_OPTIONS", "symbol": symbol,
        "date": date, "apikey": api_key,
    })
    return chain_from_payload(http_get(f"{QUERY_URL}?{params}"))

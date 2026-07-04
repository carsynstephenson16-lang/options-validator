"""data/underlying_closes.py -- direct daily underlying closes.

BLIND-PULL POLICY (mirrors the chain cache): the fetch writes the full
configured range to parquet WITHOUT displaying any value; load_closes()
refuses rows after config.IN_SAMPLE_END unless allow_oos=True. Researcher
call sites pass allow_oos=True explicitly -- a disclosed post-2022 look
(ledger/facts.log PIVOT_4NAME_SCOPE). Features and covered-call studies use
THIS series; put-call-parity spots are never a feature source.
"""
from __future__ import annotations

import os

import pandas as pd

import config
from data.thetadata_adapter import OOSDataTouchError

CACHE_DIR = os.path.join(".cache", "underlying")


def _path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol}.parquet")


def store_closes(symbol: str, frame: pd.DataFrame) -> str:
    """Persist ['date','close'] rows sorted+deduped; returns the path.
    Used by the fetch and by tests with synthetic data."""
    if list(frame.columns) != ["date", "close"]:
        raise ValueError(
            f"expected columns ['date','close'], got {list(frame.columns)}")
    out = (frame.assign(date=frame["date"].astype(str))
                .drop_duplicates(subset="date", keep="last")
                .sort_values("date")
                .reset_index(drop=True))
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _path(symbol)
    out.to_parquet(path, index=False)
    return path


def load_closes(symbol: str, start_iso: str, end_iso: str, *,
                allow_oos: bool = False) -> pd.Series:
    """Date-indexed float close Series over [start_iso, end_iso].
    Fail-closed OOS gate on the END of the requested range."""
    if not allow_oos and end_iso > config.IN_SAMPLE_END:
        raise OOSDataTouchError(
            f"load_closes({symbol}, end={end_iso}) exceeds IN_SAMPLE_END="
            f"{config.IN_SAMPLE_END} without allow_oos=True")
    df = pd.read_parquet(_path(symbol))
    s = df.set_index("date")["close"].sort_index().astype(float)
    return s.loc[start_iso:end_iso]


def rows_to_frame(rows) -> pd.DataFrame:
    """Normalize (iso_date, close) pairs from the fetch into the storage
    schema. Pure; unit-tested without network."""
    return pd.DataFrame(rows, columns=["date", "close"])


def fetch_underlying_eod(symbol: str, start_iso: str, end_iso: str) -> str:
    """One-shot BLIND pull of daily closes via the installed ThetaData
    client's stock_history_eod. Response shape verified LIVE 2026-07-04:
    columns include open/high/low/CLOSE/volume plus last-NBBO fields, no
    date index -- the trading day is last_trade (tz America/New_York).
    Writes the cache and returns the path; never prints a price.

    ORCHESTRATOR-ONLY: tests never call this; the controlling session runs
    the actual pull after review.
    """
    from datetime import date as _date

    from data.thetadata_adapter import _client

    df = _client().stock_history_eod(symbol,
                                     _date.fromisoformat(start_iso),
                                     _date.fromisoformat(end_iso))
    rows = [(ts.date().isoformat(), float(c))
            for ts, c in zip(df["last_trade"], df["close"])]
    return store_closes(symbol, rows_to_frame(rows))

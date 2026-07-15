"""data/underlying_ohlcv.py -- direct daily underlying OHLCV bars.

Daily-OHLCV sibling of underlying_closes.py. BLIND-PULL POLICY (mirrors the
chain cache and the closes cache): the fetch writes the full configured range
to parquet WITHOUT displaying any value; load_ohlcv() refuses rows after
config.IN_SAMPLE_END unless allow_oos=True. Signal math (ranges, ATR, breakout
highs) consumes load_ohlcv_adjusted(); raw strike/spot math consumes
load_ohlcv(). The split registry and adjustment_factor are REUSED from
underlying_closes -- never duplicated here -- so the two caches can never drift.

Blind: writes parquet, never prints a price. Row COUNTS may be logged; prices
and volumes never leave the cache.
"""
from __future__ import annotations

import os

import pandas as pd

import config
from data.thetadata_adapter import OOSDataTouchError
from data.underlying_closes import (
    SPLITS,
    YAHOO_CHART_URL,
    _now_ny_iso,
    adjustment_factor,
    yahoo_fetch_end,
)
from research.facts import append_fact

CACHE_DIR = os.path.join(".cache", "underlying_ohlcv")

OHLCV_COLUMNS = ["date", "open", "high", "low", "close", "volume"]

_VALUE_COLUMNS = ["open", "high", "low", "close", "volume"]
_PRICE_COLUMNS = ["open", "high", "low", "close"]

OhlcvRow = tuple[str, float, float, float, float, float]


def _path(symbol: str) -> str:
    return os.path.join(CACHE_DIR, f"{symbol}.parquet")


def store_ohlcv(symbol: str, frame: pd.DataFrame) -> str:
    """Persist OHLCV_COLUMNS rows sorted+deduped; returns the path.
    Used by the fetch and by tests with synthetic data."""
    if list(frame.columns) != OHLCV_COLUMNS:
        raise ValueError(
            f"expected columns {OHLCV_COLUMNS}, got {list(frame.columns)}")
    out = (frame.assign(date=frame["date"].astype(str))
                .drop_duplicates(subset="date", keep="last")
                .sort_values("date")
                .reset_index(drop=True))
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _path(symbol)
    out.to_parquet(path, index=False)
    return path


def load_ohlcv(symbol: str, start_iso: str, end_iso: str, *,
               allow_oos: bool = False) -> pd.DataFrame:
    """Date-indexed (str) float OHLCV frame over [start_iso, end_iso], columns
    [open, high, low, close, volume]. Fail-closed OOS gate on the END of the
    requested range.

    RAW (as-traded) values: aligned with raw option strikes, DISCONTINUOUS at
    split boundaries. Correct for strike/spot/chain math; NEVER feed these to
    trailing price signals -- a 20:1 split reads as a -95% crash. Signals use
    load_ohlcv_adjusted()."""
    if not allow_oos and end_iso > config.IN_SAMPLE_END:
        raise OOSDataTouchError(
            f"load_ohlcv({symbol}, end={end_iso}) exceeds IN_SAMPLE_END="
            f"{config.IN_SAMPLE_END} without allow_oos=True")
    df = pd.read_parquet(_path(symbol))
    out = df.set_index("date").sort_index()[_VALUE_COLUMNS].astype(float)
    return out.loc[start_iso:end_iso]


def load_ohlcv_adjusted(symbol: str, start_iso: str, end_iso: str, *,
                        allow_oos: bool = False) -> pd.DataFrame:
    """Split-CONTINUOUS OHLCV for signal computation: each row's o/h/l/c is
    divided by its date's adjustment factor and its volume is MULTIPLIED by the
    same factor (share count scales inversely to price across a split). This is
    the ONLY OHLCV series trailing price/volume signals may consume."""
    raw = load_ohlcv(symbol, start_iso, end_iso, allow_oos=allow_oos)
    if symbol not in SPLITS:
        return raw
    factors = pd.Series(
        [adjustment_factor(symbol, str(d)) for d in raw.index],
        index=raw.index, dtype=float,
    )
    out = raw.copy()
    for col in _PRICE_COLUMNS:
        out[col] = raw[col] / factors
    out["volume"] = raw["volume"] * factors
    return out


def rows_to_frame(rows: list[OhlcvRow]) -> pd.DataFrame:
    """Normalize (iso_date, o, h, l, c, v) tuples from the fetch into the
    storage schema. Pure; unit-tested without network."""
    return pd.DataFrame(rows, columns=OHLCV_COLUMNS)


def _drop_same_day_ohlcv(rows: list[OhlcvRow], today_iso: str) -> list[OhlcvRow]:
    """OHLCV analogue of underlying_closes.drop_same_day_rows (that helper
    unpacks 2-tuples): remove rows dated on/after the fetch's NY date, so a
    same-day partial bar never poisons later signal reads."""
    return [r for r in rows if r[0] < today_iso]


def yahoo_ohlcv_rows_from_payload(payload: dict) -> list[OhlcvRow]:
    """(iso_date, o, h, l, c, v) rows from a Yahoo v8 chart payload, reading
    indicators.quote[0] open/high/low/close/volume. Raises loudly (ValueError)
    on error payloads, empty result, missing/misaligned arrays, or all-null
    rows (fail closed); skips any session where any of o/h/l/c/v is None.
    o/h/l/c are Yahoo's SPLIT-adjusted values -- unsplit_ohlcv undoes that."""
    import datetime as _dt
    import zoneinfo

    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise ValueError(f"Yahoo chart error: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise ValueError("Yahoo chart returned no result")
    r = results[0]
    ts = r.get("timestamp") or []
    quote = (r.get("indicators", {}).get("quote") or [{}])[0]
    arrays = [quote.get(k) for k in _VALUE_COLUMNS]
    if not ts or any(a is None for a in arrays):
        raise ValueError("Yahoo chart payload missing OHLCV arrays")
    if any(len(a) != len(ts) for a in arrays):
        raise ValueError("Yahoo chart payload has misaligned OHLCV arrays")
    tz = zoneinfo.ZoneInfo(r.get("meta", {}).get("exchangeTimezoneName",
                                                 "America/New_York"))
    opens, highs, lows, closes, vols = arrays
    rows: list[OhlcvRow] = []
    for t, o, h, low, c, v in zip(ts, opens, highs, lows, closes, vols):
        if None in (o, h, low, c, v):
            continue
        d = _dt.datetime.fromtimestamp(t, tz).date().isoformat()
        rows.append((d, float(o), float(h), float(low), float(c), float(v)))
    if not rows:
        raise ValueError("Yahoo chart returned no non-null OHLCV rows")
    return rows


def unsplit_ohlcv(rows: list[OhlcvRow], symbol: str) -> list[OhlcvRow]:
    """Undo split adjustment so bars align with raw option strikes: pre-split
    rows get o/h/l/c MULTIPLIED by the ratio and volume DIVIDED by it."""
    out = rows
    for first_adjusted_day, ratio in SPLITS.get(symbol, []):
        out = [
            (d, o * ratio, h * ratio, low * ratio, c * ratio, v / ratio)
            if d < first_adjusted_day else (d, o, h, low, c, v)
            for d, o, h, low, c, v in out
        ]
    return out


def persist_ohlcv_rows(symbol: str, rows: list[OhlcvRow],
                       today_iso: str) -> str:
    """Post-download persistence, factored out of the network fetch so it is
    unit-testable: unsplit -> drop same-day partial bar -> store -> append a
    DESCRIPTIVE fact. `rows=` in the fact is a ROW COUNT, never a value.
    Returns the cache path only."""
    rows = _drop_same_day_ohlcv(unsplit_ohlcv(rows, symbol), today_iso)
    path = store_ohlcv(symbol, rows_to_frame(rows))
    append_fact(f"DATA_PULL_OHLCV {today_iso}: Yahoo OHLCV refresh {symbol} "
                f"rows={len(rows)} path={path}")
    return path


def fetch_underlying_ohlcv_yahoo(symbol: str) -> str:
    """Full-history RAW daily OHLCV via the free Yahoo v8 chart API (same
    provider rationale as fetch_underlying_eod_yahoo: ThetaData stock history
    and AlphaVantage full history are paid tiers; Yahoo chart works keyless).
    Split adjustment undone via the shared SPLITS registry. Blind: writes
    parquet, never prints a price.

    ORCHESTRATOR-ONLY: tests never call this; the controlling session runs the
    actual pull after review.
    """
    # Explicit epoch bounds, NOT range=max: Yahoo silently degrades 1d bars to
    # monthly on very long ranges. 2017-01-01..yahoo_fetch_end+1d keeps true
    # dailies (matches fetch_underlying_eod_yahoo exactly).
    import calendar
    import json
    import urllib.request
    from datetime import date as _date

    p1 = calendar.timegm(_date(2017, 1, 1).timetuple())
    end_iso = yahoo_fetch_end(_date.today().isoformat(), config.BACKTEST_END)
    p2 = calendar.timegm(_date.fromisoformat(end_iso).timetuple()) + 86400
    url = (YAHOO_CHART_URL.format(symbol=symbol)
           + f"?period1={p1}&period2={p2}&interval=1d")
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310 (https)
        payload = json.load(resp)
    return persist_ohlcv_rows(
        symbol, yahoo_ohlcv_rows_from_payload(payload), _now_ny_iso())

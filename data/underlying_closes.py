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
    Fail-closed OOS gate on the END of the requested range.

    RAW (as-traded) closes: aligned with raw option strikes, DISCONTINUOUS at
    split boundaries. Correct for strike/spot/chain math; NEVER feed these to
    trailing price signals (52wk high, 20d high, RV, range) -- a 5:1 split
    reads as an -80% crash. Signals use load_closes_adjusted()."""
    if not allow_oos and end_iso > config.IN_SAMPLE_END:
        raise OOSDataTouchError(
            f"load_closes({symbol}, end={end_iso}) exceeds IN_SAMPLE_END="
            f"{config.IN_SAMPLE_END} without allow_oos=True")
    df = pd.read_parquet(_path(symbol))
    s = df.set_index("date")["close"].sort_index().astype(float)
    return s.loc[start_iso:end_iso]


def adjustment_factor(symbol: str, iso_date: str) -> float:
    """raw_close = adjusted_close * factor at `iso_date`: the product of the
    ratios of all splits whose first split-adjusted day is AFTER iso_date.
    1.0 after a symbol's last split (so live spot is unchanged)."""
    factor = 1.0
    for first_adjusted_day, ratio in SPLITS.get(symbol, []):
        if iso_date < first_adjusted_day:
            factor *= ratio
    return factor


def adjusted_from_raw(raw: pd.Series, symbol: str) -> pd.Series:
    """Split-CONTINUOUS closes from a raw date-indexed series: each row is
    divided by its date's adjustment factor. This is the ONLY series trailing
    price signals may consume (h7_signals; ledger review 2026-07-10)."""
    if symbol not in SPLITS:
        return raw
    factors = pd.Series(
        [adjustment_factor(symbol, str(d)) for d in raw.index],
        index=raw.index, dtype=float,
    )
    return raw / factors


def load_closes_adjusted(symbol: str, start_iso: str, end_iso: str, *,
                         allow_oos: bool = False) -> pd.Series:
    """Split-adjusted (continuous) closes for signal computation.

    Entity floor (config.H7_SIGNAL_CLOSES_START): closes that predate the
    current operating company -- pre-SPAC-merger shell prints on the same
    ticker -- never reach a trailing signal, whatever range the caller asks
    for (ledger H7_AMENDMENT_V1_7)."""
    floor = config.H7_SIGNAL_CLOSES_START.get(symbol)
    if floor is not None and start_iso < floor:
        start_iso = floor
    return adjusted_from_raw(
        load_closes(symbol, start_iso, end_iso, allow_oos=allow_oos), symbol
    )


def rows_to_frame(rows) -> pd.DataFrame:
    """Normalize (iso_date, close) pairs from the fetch into the storage
    schema. Pure; unit-tested without network."""
    return pd.DataFrame(rows, columns=["date", "close"])


def drop_same_day_rows(rows: list[tuple[str, float]],
                       today_iso: str) -> list[tuple[str, float]]:
    """Remove rows dated on/after the fetch's NY date: a same-day 'close'
    fetched intraday is a partial print, and once stored it poisons every
    later signal read (7b-0 NO-GO remediation). Applied by BOTH fetchers."""
    return [(d, c) for d, c in rows if d < today_iso]


def _now_ny_iso() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


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
    return store_closes(
        symbol, rows_to_frame(drop_same_day_rows(rows, _now_ny_iso())))


AV_QUERY_URL = "https://www.alphavantage.co/query"


def av_rows_from_payload(payload: dict) -> list[tuple[str, float]]:
    """(iso_date, close) rows from a TIME_SERIES_DAILY payload. Raises
    loudly on gate/limit payloads so a refused response can never be cached
    as an empty series (same policy as the parked alphavantage chain
    fetcher on the data-layer branch)."""
    for k in ("Information", "Note", "Error Message"):
        if k in payload:
            raise RuntimeError(f"Alpha Vantage refused: {payload[k]}")
    series = payload.get("Time Series (Daily)") or {}
    if not series:
        raise RuntimeError("Alpha Vantage returned no daily rows")
    return [(d, float(v["4. close"])) for d, v in series.items()]


def fetch_underlying_eod_av(symbol: str) -> str:
    """Full-history UNADJUSTED daily closes via Alpha Vantage
    TIME_SERIES_DAILY (free tier; ALPHAVANTAGE_API_KEY from the env).
    Unadjusted is CORRECT for this repo: cached chains quote raw strikes,
    so raw closes stay aligned across splits (e.g. AMZN 2022 20:1).
    Provider rationale (2026-07-04): ThetaData stock history needs a paid
    STANDARD stock tier (options tier doesn't cover it; live probe: recent
    window only on FREE). Blind: writes parquet, never prints a price.

    ORCHESTRATOR-ONLY, like fetch_underlying_eod.
    """
    import json
    import urllib.parse
    import urllib.request

    key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
    if not key:
        raise RuntimeError("ALPHAVANTAGE_API_KEY missing from environment "
                           "(run via `uv run --env-file .env ...`)")
    url = AV_QUERY_URL + "?" + urllib.parse.urlencode({
        "function": "TIME_SERIES_DAILY", "symbol": symbol,
        "outputsize": "full", "apikey": key})
    with urllib.request.urlopen(url, timeout=60) as resp:  # nosec B310 (https)
        payload = json.load(resp)
    return store_closes(symbol, rows_to_frame(av_rows_from_payload(payload)))


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
# Known splits inside the data window. Yahoo's chart-API `close` is
# SPLIT-adjusted (not dividend-adjusted); this repo needs RAW closes aligned
# with raw option strikes, so pre-split rows are multiplied back. First
# split-adjusted trading day is the key; ratio multiplies earlier closes.
# Provenance: AMZN 20-for-1 split, effective first trade 2022-06-06
# (Official-source: Amazon 2022-03-09 8-K / press release; SEC EDGAR).
# NVDA 4:1 first split-adjusted trade 2021-07-20 and 10:1 2024-06-10
# (Official-source: company PRs). NOW 5:1 first split-adjusted trade
# 2025-12-18 (Official-source: SEC 8-K 2025-12-05; OCC memo #57868).
# SMCI 10:1 first split-adjusted trade 2024-10-01 (Official-source: company
# 8-K). All boundaries independently confirmed by parity-spot discontinuities
# in the local chain cache (ledger facts REPORT_ADJUDICATION 2026-07-09).
SPLITS = {
    "AMZN": [("2022-06-06", 20.0)],
    "NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)],
    "NOW": [("2025-12-18", 5.0)],
    "SMCI": [("2024-10-01", 10.0)],
}


def yahoo_rows_from_payload(payload: dict) -> list[tuple[str, float]]:
    """(iso_date, split-adjusted close) rows from a Yahoo v8 chart payload.
    Raises loudly on error payloads or empty series (fail closed)."""
    import datetime as _dt
    import zoneinfo

    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise RuntimeError(f"Yahoo chart error: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise RuntimeError("Yahoo chart returned no result")
    r = results[0]
    ts = r.get("timestamp") or []
    closes = (r.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    if not ts or len(ts) != len(closes):
        raise RuntimeError("Yahoo chart payload missing/misaligned timestamps")
    tz = zoneinfo.ZoneInfo(r.get("meta", {}).get("exchangeTimezoneName",
                                                 "America/New_York"))
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = _dt.datetime.fromtimestamp(t, tz).date().isoformat()
        rows.append((d, float(c)))
    if not rows:
        raise RuntimeError("Yahoo chart returned no non-null closes")
    return rows


def unsplit(rows: list[tuple[str, float]], symbol: str) -> list[tuple[str, float]]:
    """Undo split adjustment so closes align with raw option strikes."""
    out = rows
    for first_adjusted_day, ratio in SPLITS.get(symbol, []):
        out = [(d, c * ratio) if d < first_adjusted_day else (d, c)
               for d, c in out]
    return out


def yahoo_fetch_end(today_iso: str, backtest_end_iso: str) -> str:
    """End bound for the Yahoo closes fetch: BACKTEST_END or today, whichever
    is later. The blind cache may extend past the frozen backtest window --
    the pre-registered entry watch (H5_ENTRY_TRIGGER_PREREG) needs current
    closes -- while backtests stay bounded because load_closes gates on the
    RANGE each caller requests, not on what the cache holds."""
    return max(today_iso, backtest_end_iso)


def fetch_underlying_eod_yahoo(symbol: str) -> str:
    """Full-history RAW daily closes via the free Yahoo v8 chart API
    (provider decision 2026-07-04: ThetaData stock history and AlphaVantage
    full history are paid tiers; Stooq blocks scripts; Yahoo chart works
    keyless). Split adjustment undone via the SPLITS registry; validated
    against ThetaData FREE recent-window true closes AND the parity series
    before first use (see facts.log). Blind: never prints a price."""
    # Explicit epoch bounds, NOT range=max: Yahoo silently degrades 1d bars
    # to monthly on very long ranges (observed live 2026-07-04: range=max
    # returned 34-233 rows). 2017-01-01..BACKTEST_END+1d keeps true dailies.
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
    rows = unsplit(yahoo_rows_from_payload(payload), symbol)
    return store_closes(
        symbol, rows_to_frame(drop_same_day_rows(rows, _now_ny_iso())))


def parity_spot_from_chain(chain: pd.DataFrame, today_iso: str, *,
                           min_dte: int = 15, max_dte: int = 60,
                           n_strikes: int = 5) -> float:
    """Underlying spot inferred from put-call parity on the nearest MONTHLY
    expiry: median over the n_strikes nearest-ATM strikes of
    C_mid - P_mid + K (r=0, no dividend PV -- documented level bias well
    under 1%, measured against true closes in the validation runner).
    NaN when the day has no usable expiry or no P/C overlap (fail closed)."""
    from datetime import date as _date

    from options_researcher.chains import nearest_monthly

    today = _date.fromisoformat(today_iso)
    exp = nearest_monthly(chain, today, min_dte=min_dte, max_dte=max_dte)
    if exp is None:
        return float("nan")
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    sane = (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])
    sub = chain[(exp_dates == exp) & sane]
    calls = sub[sub["right"] == "C"].set_index("strike")
    puts = sub[sub["right"] == "P"].set_index("strike")
    ks = calls.index.intersection(puts.index)
    if len(ks) == 0:
        return float("nan")
    c_mid = (calls.loc[ks, "bid"] + calls.loc[ks, "ask"]) / 2
    p_mid = (puts.loc[ks, "bid"] + puts.loc[ks, "ask"]) / 2
    spots = c_mid - p_mid + pd.Series(ks, index=ks, dtype=float)
    rough = float(spots.median())
    nearest = spots.loc[sorted(ks, key=lambda k: abs(k - rough))[:n_strikes]]
    return float(nearest.median())


def build_parity_closes(symbol: str, start_iso: str, end_iso: str, *,
                        allow_oos: bool = False) -> str:
    """INTERIM close series derived from our own cached chains via parity
    (provider decision 2026-07-04: ThetaData stock history and AlphaVantage
    full-history both require paid tiers; Stooq blocks programmatic access).
    Validated against true recent-window closes before use; see facts.log."""
    from options_researcher.chains import load_range

    chains = load_range(symbol, start_iso, end_iso, allow_oos=allow_oos)
    rows = [(day, parity_spot_from_chain(chain, day))
            for day, chain in sorted(chains.items())]
    rows = [(d, s) for d, s in rows if pd.notna(s)]
    if not rows:
        raise RuntimeError(f"no parity spots derivable for {symbol} "
                           f"{start_iso}..{end_iso}")
    return store_closes(symbol, rows_to_frame(rows))

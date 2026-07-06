"""data/pandas_feed.py -- cached EOD chains -> Lumibot per-contract Data.

This is the OFFLINE data path proven by the 2026-07-03 spike
(docs/superpowers/2026-07-03-offline-pandas-backtesting-spike.md): Lumibot's
PandasData fills option orders from per-contract Data objects carrying
bid/ask quote columns; ThetaDataBacktesting (live terminal) is never used.

Fill-model integrity (frozen, FILL_MODEL_ID):
  * bid is widened DOWN by SLIPPAGE_HAIRCUT then FLOORED to the cent;
    ask is widened UP then CEILED. Market sells fill at bid, buys at ask
    (verified against installed lumibot 4.5.63), so an engine fill can never
    be BETTER than entry_credit_conservative -- adverse rounding, never round
    in the strategy's favor.
  * close = RAW quote mid. It is the engine's mark-to-market/settlement price
    only; the quote-first fill path means it never prices a fill while bid/ask
    exist.
  * Bars are stamped 16:00 America/New_York: lumibot ingests option marks only
    inside 09:30-16:00 sim time, and the EOD report is a 16:00 snapshot.

Contract inclusion: a put enters the feed if |delta| ever reaches
[DELTA_MIN, DELTA_MAX] inside the window; once included its FULL series is
kept (a partial series would let lumibot forward-fill stale quotes into the
gap). The band is generous plumbing, not a tunable: legs are selected from
the RAW chain, and the strategy fails loud if a selected leg has no feed
Data, so a band miss can abort a run but can never bias one.
"""
from __future__ import annotations

import math
from datetime import date as Date
from datetime import timedelta

import pandas as pd

import config
from data import thetadata_adapter

try:  # keep the module importable (and unit-testable) before lumibot exists
    from lumibot.entities import Asset, Data
except Exception:  # pragma: no cover
    Asset = Data = None  # type: ignore[assignment]

NY_TZ = "America/New_York"
BAR_HOUR = 16
# generous inclusion band for candidate legs (short ~0.30 delta, long width
# below); far-OTM lottery tickets and deep-ITM puts can never be legs
DELTA_MIN = 0.03
DELTA_MAX = 0.65

_USD = None


def _usd():
    global _USD
    if _USD is None:
        _USD = Asset(symbol="USD", asset_type="forex")
    return _USD


def option_asset(symbol: str, expiration_iso: str, strike: float):
    """The ONE canonical put-contract Asset key. The feed and the strategy must
    build byte-identical keys or orders can never fill."""
    return Asset(
        symbol=str(symbol).strip().upper(),
        asset_type=Asset.AssetType.OPTION,
        expiration=Date.fromisoformat(str(expiration_iso)),
        strike=float(strike),
        right="PUT",
    )


def load_cached_chains(symbol: str, start_iso: str, end_iso: str, *,
                       allow_oos: bool = False) -> dict[str, pd.DataFrame]:
    """Read every cached chain for `symbol` in [start_iso, end_iso] from the
    local parquet cache. The cache IS the trading calendar: a missing file is
    a non-trading day (real data gaps were CACHE_GAP-logged at cache time).
    Never fetches: on a cache hit get_eod_chain reads parquet only, and dates
    past IN_SAMPLE_END raise OOSDataTouchError unless allow_oos (holdout
    guard, enforced by the adapter even for cached files)."""
    start = Date.fromisoformat(start_iso)
    end = Date.fromisoformat(end_iso)
    chains: dict[str, pd.DataFrame] = {}
    d = start
    while d <= end:
        iso = d.isoformat()
        if thetadata_adapter._cache_path(symbol, iso).exists():
            chains[iso] = thetadata_adapter.get_eod_chain(
                symbol, iso, allow_oos=allow_oos)
        d += timedelta(days=1)
    return chains


def build_option_data(chains: dict[str, pd.DataFrame], symbol: str, *,
                      exp_max: str, haircut: float = config.SLIPPAGE_HAIRCUT,
                      delta_min: float = DELTA_MIN,
                      delta_max: float = DELTA_MAX) -> dict:
    """Per-contract Lumibot Data for every put in `chains` expiring on or
    before `exp_max` whose |delta| ever enters [delta_min, delta_max]."""
    frames = []
    for iso_day, chain in chains.items():
        puts = chain[chain["right"] == "P"]
        puts = puts[(puts["expiration"] > iso_day) & (puts["expiration"] <= exp_max)]
        if puts.empty:
            continue
        f = puts[["expiration", "strike", "bid", "ask", "delta"]].copy()
        f["day"] = iso_day
        frames.append(f)
    if not frames:
        return {}
    rows = pd.concat(frames, ignore_index=True)

    feed: dict = {}
    for (exp, strike), grp in rows.groupby(["expiration", "strike"]):
        if not grp["delta"].abs().between(delta_min, delta_max).any():
            continue
        grp = grp.sort_values("day")
        idx = pd.DatetimeIndex(
            [pd.Timestamp(f"{d} {BAR_HOUR}:00", tz=NY_TZ) for d in grp["day"]])
        bid = grp["bid"].to_numpy(dtype=float)
        ask = grp["ask"].to_numpy(dtype=float)
        df = pd.DataFrame(
            {
                "bid": [math.floor(b * (1 - haircut) * 100) / 100 for b in bid],
                "ask": [math.ceil(a * (1 + haircut) * 100) / 100 for a in ask],
                "close": (bid + ask) / 2.0,
            },
            index=idx,
        )
        asset = option_asset(symbol, str(exp), float(strike))
        feed[asset] = Data(asset, df, timestep="day", quote=_usd())
    return feed

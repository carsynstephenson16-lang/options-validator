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
# feed inclusion bands live in frozen config (7b-2R finding 5: they can
# change trade inclusion, so they participate in config_hash). Values are
# unchanged; the H1 feed stays byte-identical.
DELTA_MIN, DELTA_MAX = config.FEED_PUT_DELTA_BAND
CALL_DELTA_MIN, CALL_DELTA_MAX = config.FEED_CALL_DELTA_BAND
_RIGHT_BANDS = {"P": (DELTA_MIN, DELTA_MAX), "C": (CALL_DELTA_MIN, CALL_DELTA_MAX)}


def adverse_buy(ask, haircut: float = config.SLIPPAGE_HAIRCUT) -> float:
    """THE canonical executable BUY price (7b-2R finding 5): ask plus
    haircut, rounded UP to the cent -- exactly the price the pre-widened
    feed charges a market buy. Decide layer, T+1 revalidation, exit marks
    and P&L must all price buys through here, so no threshold can pass on
    unrounded math and then fill a cent worse in the engine."""
    return math.ceil(float(ask) * (1 + haircut) * 100) / 100


def adverse_sell(bid, haircut: float = config.SLIPPAGE_HAIRCUT) -> float:
    """Canonical executable SELL price: bid minus haircut, rounded DOWN."""
    return math.floor(float(bid) * (1 - haircut) * 100) / 100


def quote_valid(bid, ask) -> bool:
    """A usable book: finite, two-sided, uncrossed (7b-2R finding 5 --
    entry, exit lookup and marks must all reject non-finite, one-sided and
    crossed quotes; a positive crossed book previously priced exits)."""
    try:
        b, a = float(bid), float(ask)
    except (TypeError, ValueError):
        return False
    return (math.isfinite(b) and math.isfinite(a)
            and b > 0 and a > 0 and b <= a)

_USD = None


def _usd():
    global _USD
    if _USD is None:
        _USD = Asset(symbol="USD", asset_type="forex")
    return _USD


def _normalize_right(right: str) -> str:
    r = str(right).strip().upper()
    if r in ("P", "PUT"):
        return "PUT"
    if r in ("C", "CALL"):
        return "CALL"
    raise ValueError(f"unknown option right: {right!r}")


def option_asset(symbol: str, expiration_iso: str, strike: float,
                 right: str = "PUT"):
    """The ONE canonical contract Asset key. The feed and the strategy must
    build byte-identical keys or orders can never fill. `right` defaults to
    PUT so every pre-7b-1 (H1) call site is unchanged; calls and puts at the
    same (expiration, strike) are DISTINCT assets."""
    return Asset(
        symbol=str(symbol).strip().upper(),
        asset_type=Asset.AssetType.OPTION,
        expiration=Date.fromisoformat(str(expiration_iso)),
        strike=float(strike),
        right=_normalize_right(right),
    )


def load_cached_chains(symbol: str, start_iso: str, end_iso: str, *,
                       allow_oos: bool = False,
                       eligible: set[str] | None = None,
                       refused: list[str] | None = None
                       ) -> dict[str, pd.DataFrame]:
    """Read cached chains for `symbol` in [start_iso, end_iso] from the
    local parquet cache. Never fetches: on a cache hit get_eod_chain reads
    parquet only, and dates past IN_SAMPLE_END raise OOSDataTouchError
    unless allow_oos (holdout guard, enforced by the adapter even for
    cached files).

    `eligible` (7b-2R finding 2): when given, ONLY days in the set are
    loaded -- a file that exists outside it is never parsed; its day is
    appended to `refused` (caller-supplied list) so the quarantine is
    reported, not silent. The H7 runner ALWAYS passes the canonical
    data.h7_manifest eligible set; eligible=None is the legacy H1 path and
    synthetic-test path only."""
    start = Date.fromisoformat(start_iso)
    end = Date.fromisoformat(end_iso)
    chains: dict[str, pd.DataFrame] = {}
    d = start
    while d <= end:
        iso = d.isoformat()
        if thetadata_adapter._cache_path(symbol, iso).exists():
            if eligible is not None and iso not in eligible:
                if refused is not None:
                    refused.append(iso)
            else:
                chains[iso] = thetadata_adapter.get_eod_chain(
                    symbol, iso, allow_oos=allow_oos)
        d += timedelta(days=1)
    return chains


def build_option_data(chains: dict[str, pd.DataFrame], symbol: str, *,
                      exp_max: str, haircut: float = config.SLIPPAGE_HAIRCUT,
                      delta_min: float | None = None,
                      delta_max: float | None = None,
                      rights: tuple[str, ...] = ("P",)) -> dict:
    """Per-contract Lumibot Data for every contract of the requested rights
    in `chains` expiring on or before `exp_max` whose |delta| ever enters the
    right's inclusion band. Defaults (puts only, put band) reproduce the H1
    feed byte-for-byte; H7 passes rights=("C", "P")."""
    frames = []
    for iso_day, chain in chains.items():
        rows = chain[chain["right"].isin(rights)]
        rows = rows[(rows["expiration"] > iso_day) & (rows["expiration"] <= exp_max)]
        if rows.empty:
            continue
        f = rows[["expiration", "strike", "right", "bid", "ask", "delta"]].copy()
        f["day"] = iso_day
        frames.append(f)
    if not frames:
        return {}
    rows = pd.concat(frames, ignore_index=True)

    feed: dict = {}
    for (exp, strike, right), grp in rows.groupby(["expiration", "strike", "right"]):
        lo, hi = _RIGHT_BANDS[right]
        if delta_min is not None or delta_max is not None:
            lo = delta_min if delta_min is not None else lo
            hi = delta_max if delta_max is not None else hi
        if not grp["delta"].abs().between(lo, hi).any():
            continue
        grp = grp.sort_values("day")
        idx = pd.DatetimeIndex(
            [pd.Timestamp(f"{d} {BAR_HOUR}:00", tz=NY_TZ) for d in grp["day"]])
        bid = grp["bid"].to_numpy(dtype=float)
        ask = grp["ask"].to_numpy(dtype=float)
        df = pd.DataFrame(
            {
                "bid": [adverse_sell(b, haircut) for b in bid],
                "ask": [adverse_buy(a, haircut) for a in ask],
                "close": (bid + ask) / 2.0,
            },
            index=idx,
        )
        asset = option_asset(symbol, str(exp), float(strike), right=right)
        feed[asset] = Data(asset, df, timestep="day", quote=_usd())
    return feed

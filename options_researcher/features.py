"""options_researcher/features.py -- per-name daily feature frame.

One row per cached chain day: close, rv21 (annualized 21-day realized vol,
ddof=1), atm_iv (0.50-delta put on the NEAREST MONTHLY expiration, 15-60
DTE), iv_minus_rv, iv_rank (inclusive-rank percentile of atm_iv over the
trailing <=252 finite obs; NaN until 126), monthly_dte, earnings_week
(True iff an announcement date e satisfies -7 <= (e - day).days <= 1 in
BUSINESS-day terms via the -5bd..+1bd convention below).

Fail-closed: a day with no cached chain simply has no row; a day with no
in-band monthly gets NaN atm_iv. No fallbacks, no interpolation.
"""
from __future__ import annotations

import os
from datetime import date

import numpy as np
import pandas as pd

from options_researcher.chains import atm_row, nearest_monthly

RV_WINDOW = 21
PCT_WINDOW = 252
PCT_MIN_OBS = 126
EARN_BD_BEFORE = 5   # flag starts 5 business days before the announcement
EARN_BD_AFTER = 1    # ...and covers the business day after it


def _earnings_flags(index_isos, earnings: list[date]) -> pd.Series:
    days = [date.fromisoformat(d) for d in index_isos]
    flags = []
    for d in days:
        hit = False
        for e in earnings:
            lo = np.busday_offset(e.isoformat(), -EARN_BD_BEFORE, roll="backward")
            hi = np.busday_offset(e.isoformat(), EARN_BD_AFTER, roll="forward")
            if lo <= np.datetime64(d) <= hi:
                hit = True
                break
        flags.append(hit)
    return pd.Series(flags, index=index_isos)


def build_daily_features(symbol: str, start_iso: str, end_iso: str, *,
                         closes: pd.Series,
                         chains: dict[str, pd.DataFrame],
                         earnings: list[date]) -> pd.DataFrame:
    closes = closes.sort_index().astype(float)
    logret = np.log(closes).diff()
    rv = logret.rolling(RV_WINDOW).std(ddof=1) * np.sqrt(252.0)

    days = sorted(d for d in chains if start_iso <= d <= end_iso)
    atm_iv, monthly_dte = [], []
    for d in days:
        today = date.fromisoformat(d)
        exp = nearest_monthly(chains[d], today)
        if exp is None:
            atm_iv.append(float("nan")); monthly_dte.append(float("nan"))
            continue
        row = atm_row(chains[d], exp)
        iv = float(row["iv"]) if row is not None else float("nan")
        atm_iv.append(iv if iv and iv > 0 else float("nan"))
        monthly_dte.append(float((exp - today).days))

    f = pd.DataFrame(index=pd.Index(days, name="date"))
    f["close"] = closes.reindex(days)
    f["rv21"] = rv.reindex(days)
    f["atm_iv"] = atm_iv
    f["iv_minus_rv"] = f["atm_iv"] - f["rv21"]
    f["monthly_dte"] = monthly_dte

    ranks, vals = [], []
    for v in f["atm_iv"]:
        vals.append(v)
        window = [x for x in vals[-PCT_WINDOW:] if np.isfinite(x)]
        if not np.isfinite(v) or len(window) < PCT_MIN_OBS:
            ranks.append(float("nan"))
        else:
            ranks.append(float(np.mean(np.asarray(window) <= v)))
    f["iv_rank"] = ranks
    f["earnings_week"] = _earnings_flags(list(f.index), earnings)
    return f


# Attractiveness/presentation feature store. Deliberately NOT the same
# directory as h6_features.FEATURE_DIR (".tmp/research"): the H6 store is
# manifest-bound (hash-verified provenance), and a build_all() run on
# 2026-07-16 overwrote the manifested AMZN artifact when both builders
# shared one path. Keep these stores separate.
FEATURES_DIR = os.path.join(".tmp", "research", "attractiveness")


def save_features(symbol: str, frame: pd.DataFrame) -> str:
    os.makedirs(FEATURES_DIR, exist_ok=True)
    path = os.path.join(FEATURES_DIR, f"{symbol}_features.parquet")
    frame.to_parquet(path)
    return path


def load_features(symbol: str) -> pd.DataFrame:
    return pd.read_parquet(
        os.path.join(FEATURES_DIR, f"{symbol}_features.parquet"))


def build_all(end_iso: str = None, symbols: list[str] = None):
    """Build + cache feature frames for the attractiveness display universe
    (default config.ATTRACTIVENESS_UNIVERSE; pass ``symbols`` to override).
    Post-2022 reads are explicit allow_oos=True (disclosed; facts.log
    PIVOT_4NAME_SCOPE). Watchlist names have no curated per-symbol earnings
    CSV; their earnings_week flags are built from an empty list (all False)
    and the dashboard grades earnings from the v3 store instead."""
    import config
    from data.underlying_closes import load_closes
    from options_researcher.chains import load_range
    from options_researcher.earnings import load_earnings

    end_iso = end_iso or config.BACKTEST_END
    for symbol in (symbols if symbols is not None
                   else config.ATTRACTIVENESS_UNIVERSE):
        closes = load_closes(symbol, "2017-01-01", end_iso, allow_oos=True)
        chains = load_range(symbol, config.BACKTEST_START, end_iso,
                            allow_oos=True)
        try:
            earn = load_earnings(symbol)
        except FileNotFoundError:
            earn = []
        frame = build_daily_features(symbol, config.BACKTEST_START, end_iso,
                                     closes=closes, chains=chains,
                                     earnings=earn)
        path = save_features(symbol, frame)
        print(f"{symbol}: {len(frame)} rows -> {path}")


if __name__ == "__main__":
    build_all()

"""options_researcher/chains.py -- blessed monthly-expiration selection.

The monthlies finding (2026-07-04, committed): open interest on all four
universe names concentrates 85-100% in standard MONTHLY expirations, and
nearest-monthly liquidity passes the frozen gates. Every researcher module
selects expirations through THIS module; the 3rd-Friday calendar rule lives
here and nowhere else.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from data.pandas_feed import load_cached_chains
from data.thetadata_adapter import passes_liquidity


def third_friday(year: int, month: int) -> date:
    """The 3rd Friday of a month (always the 15th..21st)."""
    d = date(year, month, 15)
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def is_monthly(exp: date) -> bool:
    """Standard listed monthly: the 3rd Friday, or the Thursday immediately
    before it (exchange-holiday Fridays, e.g. Good Friday, shift the listed
    expiration to Thursday). The Thursday case needs no holiday calendar:
    listed equity options never expire on that Thursday EXCEPT via the
    holiday shift, so the adjacency test alone is sufficient on real
    chain data."""
    tf = third_friday(exp.year, exp.month)
    return exp == tf or (exp.weekday() == 3 and exp + timedelta(days=1) == tf)


def load_range(symbol: str, start_iso: str, end_iso: str, *,
               allow_oos: bool = False) -> dict[str, pd.DataFrame]:
    """Cached chains keyed by ISO day. Thin delegation -- the OOS gate stays
    in the data layer. Researcher call sites pass allow_oos=True explicitly
    (disclosed post-2022 look, facts.log PIVOT_4NAME_SCOPE)."""
    return load_cached_chains(symbol, start_iso, end_iso, allow_oos=allow_oos)


def puts_in_window(chain: pd.DataFrame, today: date,
                   min_dte: int, max_dte: int) -> pd.DataFrame:
    """Puts with sane quotes (bid>0, ask>=bid) whose DTE lies in the band.
    Adds exp_date (datetime.date) and dte (int) columns."""
    puts = chain[(chain["right"] == "P") & (chain["bid"] > 0)
                 & (chain["ask"] >= chain["bid"])].copy()
    if puts.empty:
        return puts.assign(exp_date=pd.Series(dtype=object),
                           dte=pd.Series(dtype=int))
    puts["exp_date"] = pd.to_datetime(puts["expiration"]).dt.date
    puts["dte"] = puts["exp_date"].map(lambda e: (e - today).days)
    return puts[(puts["dte"] >= min_dte) & (puts["dte"] <= max_dte)]


def nearest_monthly(chain: pd.DataFrame, today: date, *,
                    min_dte: int = 15, max_dte: int = 60):
    """Earliest MONTHLY expiration inside the DTE band, or None."""
    win = puts_in_window(chain, today, min_dte, max_dte)
    monthlies = sorted(e for e in win["exp_date"].unique() if is_monthly(e))
    return monthlies[0] if monthlies else None


def ladder_expirations(chain: pd.DataFrame, today: date,
                       buckets=None) -> list[tuple[int, date]]:
    """For each (target, lo, hi) in config.A_LADDER_BUCKETS, the available
    expiration whose DTE is nearest `target` inside [lo, hi] (weekly OR
    monthly). Buckets with no in-window expiration are omitted and logged.
    Disjoint windows mean each expiration maps to at most one bucket, so no
    dedup is needed."""
    import config
    if buckets is None:
        buckets = config.A_LADDER_BUCKETS
    exp_dates = sorted({d for d in pd.to_datetime(chain["expiration"]).dt.date})
    out: list[tuple[int, date]] = []
    for target, lo, hi in buckets:
        in_win = [e for e in exp_dates if lo <= (e - today).days <= hi]
        if not in_win:
            logging.getLogger(__name__).info(
                "ladder: no expiration in [%d,%d] DTE (target %d) as of %s",
                lo, hi, target, today)
            continue
        out.append((target, min(in_win,
                                key=lambda e: abs((e - today).days - target))))
    return out


def atm_row(chain: pd.DataFrame, expiration: date, *,
            right: str = "P", target_delta: float = 0.50):
    """Row of `right` on `expiration` with |delta| nearest target, or None."""
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    sub = chain[(chain["right"] == right) & (exp_dates == expiration)
                & (chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    if sub.empty:
        return None
    return sub.loc[(sub["delta"].abs() - target_delta).abs().idxmin()]


def liquid_strikes(chain: pd.DataFrame, expiration: date, *,
                   right: str = "P") -> int:
    """Rows of `right` on `expiration` passing the FROZEN liquidity gates
    (data.thetadata_adapter.passes_liquidity: OI floor, quote sanity,
    max spread). Never re-implements the gates."""
    exp_dates = pd.to_datetime(chain["expiration"]).dt.date
    sub = chain[(chain["right"] == right) & (exp_dates == expiration)]
    return int(sum(passes_liquidity(r.open_interest, r.bid, r.ask)
                   for r in sub.itertuples()))

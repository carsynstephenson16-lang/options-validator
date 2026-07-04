"""options_researcher/chains.py -- blessed monthly-expiration selection.

The monthlies finding (2026-07-04, committed): open interest on all four
universe names concentrates 85-100% in standard MONTHLY expirations, and
nearest-monthly liquidity passes the frozen gates. Every researcher module
selects expirations through THIS module; the 3rd-Friday calendar rule lives
here and nowhere else.
"""
from __future__ import annotations

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

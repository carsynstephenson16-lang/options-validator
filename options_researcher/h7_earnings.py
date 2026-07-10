"""Earnings calendar with Confirmed/Estimated discipline for H6/H7.

CSV: data/earnings/calendar.csv (symbol, report_date, status, source, checked).
Estimated dates are conservative: the entry ban runs from
H7_EARNINGS_BAN_SESSIONS trading sessions before the EARLIEST estimate through
the LATEST estimate (inclusive). Confirmed rows for a symbol supersede that
symbol's estimates entirely. The refresh path (crawlee) is a separate plan;
until then the CSV is maintained by hand and every row carries its source and
check date (ledger REPORT_ADJUDICATION 2026-07-09 for the seed rows).
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import config

CAL_PATH = Path("data/earnings/calendar.csv")


def load_calendar(path: Path = CAL_PATH) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            sym = row["symbol"].upper()
            d = date.fromisoformat(row["report_date"])
            rec = out.setdefault(sym, {"confirmed": [], "estimated": []})
            rec[row["status"]].append(d)
    return out


def _sessions_before(d: date, n: int) -> date:
    """Approximate n trading sessions with a calendar-day window that always
    covers them (n + weekend padding + 2). Deliberately over-wide: a ban that
    starts slightly early is conservative; one that starts late is a leak."""
    return d - timedelta(days=n + (n // 5) * 2 + 2)


def entries_banned(symbol: str, on: date, cal: dict[str, dict]) -> bool:
    rec = cal.get(symbol.upper())
    if not rec:
        return False
    dates = rec["confirmed"] or rec["estimated"]
    if not dates:
        return False
    start = _sessions_before(min(dates), config.H7_EARNINGS_BAN_SESSIONS)
    end = max(dates)  # confirmed: single governing date; estimated: latest estimate
    return start <= on <= end

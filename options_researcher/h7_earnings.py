"""Earnings calendar with Confirmed/Estimated discipline for H6/H7.

CSV: data/earnings/calendar.csv (symbol, report_date, status, source, checked).
Revised per the 2026-07-10 adversarial review (R3/R4/R5):

- Ban windows are PER REPORT, not per symbol: each confirmed report bans the
  H7_EARNINGS_BAN_SESSIONS exchange sessions before it through the report day;
  estimated dates within 14 calendar days of each other form one cluster that
  bans from the sessions before the EARLIEST estimate through the LATEST.
- A confirmed row supersedes only estimates within 14 days of it (the same
  report); a stale past confirmation cannot disable next quarter's ban (R4),
  and two quarters of history cannot collapse into a hundred-day ban (R5).
- "Sessions before" counts real XNYS sessions via the harness calendar, so
  holiday clusters cannot shorten the window (R3).
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import config
from data.cache_runner import trading_days

CAL_PATH = Path("data/earnings/calendar.csv")
_SAME_REPORT_DAYS = 14  # estimates within this many days of a confirmed date
#                         (or of each other) refer to the same report

_STATUSES = ("confirmed", "estimated")


def load_calendar(path: Path = CAL_PATH) -> dict[str, dict]:
    out: dict[str, dict] = {}
    with path.open() as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            status = (row.get("status") or "").strip().lower()
            if status not in _STATUSES:
                raise ValueError(
                    f"{path}:{i}: status must be one of {_STATUSES}, "
                    f"got {row.get('status')!r}")
            sym = row["symbol"].upper()
            d = date.fromisoformat(row["report_date"])
            rec = out.setdefault(sym, {"confirmed": [], "estimated": []})
            rec[status].append(d)
    return out


def _ban_start(report: date, n_sessions: int) -> date:
    """First banned day: the n-th exchange session before `report`."""
    sessions = trading_days(
        (report - timedelta(days=45)).isoformat(), report.isoformat())
    prior = [s for s in sessions if s < report.isoformat()]
    if len(prior) < n_sessions:
        return report - timedelta(days=45)  # degenerate: ban the whole lookback
    return date.fromisoformat(prior[-n_sessions])


def _clusters(dates: list[date]) -> list[tuple[date, date]]:
    """Group sorted dates within _SAME_REPORT_DAYS of a neighbor into
    (earliest, latest) spans -- one span per real-world report."""
    spans: list[tuple[date, date]] = []
    for d in sorted(dates):
        if spans and (d - spans[-1][1]).days <= _SAME_REPORT_DAYS:
            spans[-1] = (spans[-1][0], d)
        else:
            spans.append((d, d))
    return spans


def _ban_windows(rec: dict) -> list[tuple[date, date]]:
    n = config.H7_EARNINGS_BAN_SESSIONS
    confirmed = sorted(rec["confirmed"])
    live_estimates = [
        e for e in rec["estimated"]
        if all(abs((e - c).days) > _SAME_REPORT_DAYS for c in confirmed)
    ]
    windows = [(_ban_start(c, n), c) for c in confirmed]
    windows += [(_ban_start(lo, n), hi) for lo, hi in _clusters(live_estimates)]
    return windows


def entries_banned(symbol: str, on: date, cal: dict[str, dict]) -> bool:
    rec = cal.get(symbol.upper())
    if not rec:
        return False
    return any(start <= on <= end for start, end in _ban_windows(rec))


def earnings_covered(symbol: str, on: date, cal: dict[str, dict]) -> bool:
    """Fail-closed coverage check (7b-0). True iff the calendar plausibly
    knows the symbol's NEXT report: any date on/after `on`, or one within the
    last H7_EARNINGS_KNOWN_HORIZON_D calendar days (just reported -- the next
    report is a full quarter out, beyond the ban horizon). A symbol with no
    rows, or only stale past rows, is NOT covered: the watcher must block
    entries rather than trade blind into an unknown report date."""
    rec = cal.get(symbol.upper())
    if not rec:
        return False
    dates = rec["confirmed"] + rec["estimated"]
    horizon = timedelta(days=config.H7_EARNINGS_KNOWN_HORIZON_D)
    return any(d >= on or (on - d) <= horizon for d in dates)

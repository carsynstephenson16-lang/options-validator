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
# Estimates within this many days of a confirmed date (or of each other)
# refer to the same report. Frozen 7b-0.1 (owner decision 2026-07-10).
_SAME_REPORT_DAYS = config.H7_EARNINGS_ESTIMATE_CLUSTER_D

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


# ---------------------------------------------------------------------------
# 7b-0.1 typed gate over the point-in-time assertions store (owner decision
# 2026-07-10, ledger H7_OWNER_DECISIONS_7B01). The store is APPEND-ONLY:
# closing/superseding an estimate appends a new assertion for the same
# event_id; historical assertions are never rewritten, so any past
# information set can be reconstructed by filtering known_as_of_utc.
# ---------------------------------------------------------------------------

GATE_CLEAR = "CLEAR"
GATE_BANNED = "BANNED"
GATE_UNKNOWN = "UNKNOWN"    # always fails closed

ASSERTIONS_PATH = Path("data/earnings/assertions.csv")
_ASSERT_COLUMNS = ("symbol", "event_id", "fiscal_period", "expected_date",
                   "session_timing", "status", "source_url",
                   "known_as_of_utc", "checked_at_utc", "notes")
_ASSERT_STATUSES = ("estimated", "confirmed", "occurred")
_ASSERT_TIMINGS = ("bmo", "amc", "unknown")


def _utc(value: str, ctx: str):
    from datetime import datetime
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{ctx}: bad timestamp {value!r}") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError(f"{ctx}: timestamp must be timezone-aware: {value!r}")
    return stamp


def load_assertions(path: Path = ASSERTIONS_PATH) -> list[dict]:
    """Parse and validate the append-only assertions store. FAILS CLOSED on
    any malformed row (owner rule: conflicting/malformed/absent -> UNKNOWN is
    enforced by the gate; a malformed FILE is a raise, not a guess)."""
    rows: list[dict] = []
    last_checked = None
    with path.open() as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != _ASSERT_COLUMNS:
            raise ValueError(
                f"{path}: header {reader.fieldnames} != {_ASSERT_COLUMNS}")
        for i, row in enumerate(reader, start=2):
            ctx = f"{path}:{i}"
            status = (row["status"] or "").strip().lower()
            if status not in _ASSERT_STATUSES:
                raise ValueError(f"{ctx}: status must be one of "
                                 f"{_ASSERT_STATUSES}, got {row['status']!r}")
            timing = (row["session_timing"] or "").strip().lower()
            if timing not in _ASSERT_TIMINGS:
                raise ValueError(f"{ctx}: session_timing must be one of "
                                 f"{_ASSERT_TIMINGS}, got {row['session_timing']!r}")
            sym = (row["symbol"] or "").strip().upper()
            event_id = (row["event_id"] or "").strip()
            url = (row["source_url"] or "").strip()
            if not sym or not event_id or not url:
                raise ValueError(f"{ctx}: symbol, event_id and source_url are required")
            checked = _utc(row["checked_at_utc"], ctx)
            if last_checked is not None and checked < last_checked:
                raise ValueError(
                    f"{ctx}: checked_at_utc decreased -- the store is "
                    f"append-only; never insert or rewrite rows")
            last_checked = checked
            rows.append({
                "symbol": sym,
                "event_id": event_id,
                "fiscal_period": (row["fiscal_period"] or "").strip(),
                "expected_date": date.fromisoformat(row["expected_date"].strip()),
                "session_timing": timing,
                "status": status,
                "source_url": url,
                "known_as_of_utc": _utc(row["known_as_of_utc"], ctx),
                "checked_at_utc": checked,
                "notes": (row["notes"] or "").strip(),
            })
    return rows


def assertions_view(assertions: list[dict], known_as_of) -> list[dict]:
    """The information set at `known_as_of`: the LATEST assertion per
    event_id among those already known. Supersession is carried by identical
    event_id + increasing known_as_of_utc; nothing is ever deleted."""
    latest: dict[str, dict] = {}
    for a in assertions:
        if a["known_as_of_utc"] <= known_as_of:
            cur = latest.get(a["event_id"])
            if cur is None or a["known_as_of_utc"] >= cur["known_as_of_utc"]:
                latest[a["event_id"]] = a
    return list(latest.values())


def earnings_gate(symbol: str, on: date, assertions: list[dict], *,
                  known_as_of) -> tuple[str, str]:
    """(state, reason) with state CLEAR | BANNED | UNKNOWN.

    CLEAR requires the information set at `known_as_of` to either identify
    the next scheduled report (a live estimated/confirmed assertion dated
    on/after `on`) or PROVE a realized report (status=occurred) within the
    previous H7_EARNINGS_POST_REPORT_GRACE_D calendar days. Expired
    estimates and passed schedules grant nothing. UNKNOWN fails closed."""
    sym = symbol.upper()
    view = [a for a in assertions_view(assertions, known_as_of)
            if a["symbol"] == sym]
    if not view:
        return GATE_UNKNOWN, "no point-in-time assertions for symbol"
    future = [a for a in view
              if a["status"] in ("estimated", "confirmed")
              and a["expected_date"] >= on]
    grace = timedelta(days=config.H7_EARNINGS_POST_REPORT_GRACE_D)
    occurred_recent = [a for a in view
                       if a["status"] == "occurred"
                       and timedelta(0) <= (on - a["expected_date"]) <= grace]
    if not future and not occurred_recent:
        return GATE_UNKNOWN, ("next report unknown: no live future assertion "
                              "and no proven report within the grace window")
    rec = {
        "confirmed": [a["expected_date"] for a in view
                      if a["status"] in ("confirmed", "occurred")],
        "estimated": [a["expected_date"] for a in view
                      if a["status"] == "estimated"],
    }
    if any(start <= on <= end for start, end in _ban_windows(rec)):
        return GATE_BANNED, "inside a pre-report ban window"
    return GATE_CLEAR, "next report known or realized report within grace"


def next_report(symbol: str, on: date, assertions: list[dict], *,
                known_as_of) -> date | None:
    """Earliest known upcoming report date at `known_as_of` (any status --
    an occurred assertion dated today still ends today's session risk).
    None when the information set names nothing on/after `on`."""
    sym = symbol.upper()
    upcoming = [a["expected_date"]
                for a in assertions_view(assertions, known_as_of)
                if a["symbol"] == sym and a["expected_date"] >= on]
    return min(upcoming) if upcoming else None

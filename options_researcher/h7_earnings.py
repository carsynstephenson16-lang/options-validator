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

# v1 store: PRESERVED as historical evidence, no longer consumed (7b-2R
# finding 4 -- its label:* placeholder sources are not causal facts).
ASSERTIONS_V1_PATH = Path("data/earnings/assertions.csv")
# v2 store: RAW evidence only after 7b-2R.1 (owner decision 2026-07-11) --
# bulk SEC Item 2.02 collection lands here and is NEVER consumed by the
# gate directly. Promotion into the gating store is a separate, per-record,
# classified act.
RAW_ASSERTIONS_PATH = Path("data/earnings/assertions_v2.csv")
# v3 GATING store: the only store the strategy/watcher/audit gate reads.
ASSERTIONS_PATH = Path("data/earnings/gating_v3.csv")
_RAW_COLUMNS = ("record_id", "symbol", "event_id", "fiscal_period",
                "record_type", "status", "expected_date", "occurred_date",
                "session_timing", "source_type", "source_url",
                "known_as_of_utc", "checked_at_utc", "supersedes", "notes")
_GATING_COLUMNS = ("record_id", "symbol", "event_id", "fiscal_period",
                   "record_type", "event_class", "status", "expected_date",
                   "occurred_date", "session_timing", "source_type",
                   "source_url", "known_as_of_utc", "checked_at_utc",
                   "supersedes", "promoted_from", "notes")
_ASSERT_STATUSES = ("estimated", "confirmed", "occurred")
_ASSERT_TIMINGS = ("bmo", "amc", "unknown")
_ASSERT_RECORD_TYPES = ("assertion", "retraction")
_ASSERT_SOURCE_TYPES = ("sec_filing", "company_pr", "company_ir",
                        "exchange_notice", "aggregator")
# 7b-2R.1: an Item 2.02 filing is not automatically an earnings report.
# Only a VERIFIED actual quarterly release may start the grace window;
# preliminary results and business updates neither start grace nor erase
# the risk of a later scheduled quarterly report; unclassified rows are
# non-gating and fail closed.
EVENT_CLASSES = ("actual_quarterly_earnings", "preliminary_earnings",
                 "business_update", "other_item_202", "unclassified")
GATING_EVENT_CLASS = "actual_quarterly_earnings"

# Reason taxonomy exported for the audit's UNKNOWN split: only a
# grace-expired UNKNOWN can ever be considered PROVEN_UNKNOWN; an empty
# archive or a conflict is ALWAYS DATA_GAP (owner decision 2026-07-11).
GATE_REASON_NO_ASSERTIONS = "no gating point-in-time assertions for symbol"
GATE_REASON_GRACE_EXPIRED = ("next report unknown: no live future assertion "
                             "and no proven report within the grace window")
GATE_REASON_CONFLICT_PREFIX = "conflicting"


def _utc(value: str, ctx: str):
    from datetime import datetime
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{ctx}: bad timestamp {value!r}") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError(f"{ctx}: timestamp must be timezone-aware: {value!r}")
    return stamp


def _load_store(path: Path, columns: tuple, *, gating: bool) -> list[dict]:
    """Shared validator for the append-only stores. FAILS CLOSED on any
    malformed row (owner rule: conflicting/malformed/absent -> UNKNOWN is
    enforced by the gate; a malformed FILE is a raise, not a guess)."""
    rows: list[dict] = []
    last_checked = None
    seen_ids: set[str] = set()
    with path.open() as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != columns:
            raise ValueError(
                f"{path}: header {reader.fieldnames} != {columns}")
        for i, row in enumerate(reader, start=2):
            ctx = f"{path}:{i}"
            record_id = (row["record_id"] or "").strip()
            if not record_id or record_id in seen_ids:
                raise ValueError(f"{ctx}: record_id missing or duplicate")
            record_type = (row["record_type"] or "").strip().lower()
            if record_type not in _ASSERT_RECORD_TYPES:
                raise ValueError(f"{ctx}: record_type must be one of "
                                 f"{_ASSERT_RECORD_TYPES}")
            status = (row["status"] or "").strip().lower()
            if status not in _ASSERT_STATUSES:
                raise ValueError(f"{ctx}: status must be one of "
                                 f"{_ASSERT_STATUSES}, got {row['status']!r}")
            timing = (row["session_timing"] or "").strip().lower()
            if timing not in _ASSERT_TIMINGS:
                raise ValueError(f"{ctx}: session_timing must be one of "
                                 f"{_ASSERT_TIMINGS}, got {row['session_timing']!r}")
            source_type = (row["source_type"] or "").strip().lower()
            if source_type not in _ASSERT_SOURCE_TYPES:
                raise ValueError(f"{ctx}: source_type must be one of "
                                 f"{_ASSERT_SOURCE_TYPES}")
            sym = (row["symbol"] or "").strip().upper()
            event_id = (row["event_id"] or "").strip()
            url = (row["source_url"] or "").strip()
            if not sym or not event_id:
                raise ValueError(f"{ctx}: symbol and event_id are required")
            if not url.startswith("https://"):
                raise ValueError(
                    f"{ctx}: source_url must be an exact https:// URL "
                    f"(label:* placeholders are not causal facts): {url!r}")
            if gating:
                event_class = (row["event_class"] or "").strip().lower()
                if event_class not in EVENT_CLASSES:
                    raise ValueError(f"{ctx}: event_class must be one of "
                                     f"{EVENT_CLASSES}")
                fiscal = (row["fiscal_period"] or "").strip()
                if event_class == GATING_EVENT_CLASS and not fiscal:
                    raise ValueError(
                        f"{ctx}: a {GATING_EVENT_CLASS} record requires "
                        f"fiscal-period identity (7b-2R.1)")
            else:
                event_class = "unclassified"   # raw rows NEVER gate
            supersedes = (row["supersedes"] or "").strip()
            if supersedes and supersedes not in seen_ids:
                raise ValueError(f"{ctx}: supersedes {supersedes!r} does not "
                                 f"reference an EARLIER record_id")
            if record_type == "retraction" and not supersedes:
                raise ValueError(f"{ctx}: a retraction must name the record "
                                 f"it retracts in `supersedes`")
            expected_raw = (row["expected_date"] or "").strip()
            occurred_raw = (row["occurred_date"] or "").strip()
            if status == "occurred":
                if not occurred_raw:
                    raise ValueError(f"{ctx}: status=occurred requires "
                                     f"occurred_date")
            elif record_type == "assertion" and not expected_raw:
                raise ValueError(f"{ctx}: status={status} requires "
                                 f"expected_date")
            checked = _utc(row["checked_at_utc"], ctx)
            if last_checked is not None and checked < last_checked:
                raise ValueError(
                    f"{ctx}: checked_at_utc decreased -- the store is "
                    f"append-only; never insert or rewrite rows")
            last_checked = checked
            seen_ids.add(record_id)
            rows.append({
                "record_id": record_id,
                "symbol": sym,
                "event_id": event_id,
                "fiscal_period": (row["fiscal_period"] or "").strip(),
                "record_type": record_type,
                "event_class": event_class,
                "status": status,
                "expected_date": (date.fromisoformat(expected_raw)
                                  if expected_raw else None),
                "occurred_date": (date.fromisoformat(occurred_raw)
                                  if occurred_raw else None),
                "session_timing": timing,
                "source_type": source_type,
                "source_url": url,
                "known_as_of_utc": _utc(row["known_as_of_utc"], ctx),
                "checked_at_utc": checked,
                "supersedes": supersedes,
                "promoted_from": (row.get("promoted_from") or "").strip(),
                "notes": (row["notes"] or "").strip(),
            })
    return rows


# Fields a promoted gating row must carry over from its raw evidence record
# UNCHANGED. notes and checked_at_utc are deliberately excluded: promotion
# legitimately adds classification notes and re-checks the record.
_PROMOTION_FIELDS = ("symbol", "event_id", "fiscal_period", "status",
                     "expected_date", "occurred_date", "session_timing",
                     "source_type", "source_url", "known_as_of_utc")


def load_assertions(path: Path = ASSERTIONS_PATH,
                    raw_path: Path | None = None) -> list[dict]:
    """The v3 GATING store: the ONLY assertions the strategy, watcher and
    audit gate on. Every row carries an event_class; only
    actual_quarterly_earnings records participate in the gate, and those
    require fiscal-period identity plus an exact source URL.

    7b-2R.2 finding 4: promotion into this store is a per-record,
    classified act that must CITE its raw evidence -- nothing unpromoted
    can gate. Every assertion row's promoted_from must resolve to a record
    in the RAW evidence store (`raw_path`, default RAW_ASSERTIONS_PATH)
    and match it on every field in _PROMOTION_FIELDS. A missing, foreign,
    or mismatched promotion refuses the WHOLE store (fail closed, matching
    the loader's malformed-file posture). Retraction rows are exempt: a
    retraction corrects the gating layer itself, so it has no raw
    counterpart to cite."""
    rows = _load_store(path, _GATING_COLUMNS, gating=True)
    raw_by_id = {r["record_id"]: r
                 for r in load_raw_assertions(raw_path or RAW_ASSERTIONS_PATH)}
    for a in rows:
        if a["record_type"] != "assertion":
            continue   # retractions correct the gating layer itself
        rid = a["record_id"]
        promoted_from = a["promoted_from"]
        if not promoted_from:
            raise ValueError(
                f"{path}: gating record {rid}: promoted_from is empty -- "
                f"promotion must cite its raw evidence record; nothing "
                f"unpromoted can gate")
        source = raw_by_id.get(promoted_from)
        if source is None:
            raise ValueError(
                f"{path}: gating record {rid}: promoted_from "
                f"{promoted_from!r} is foreign -- no such record_id in the "
                f"raw evidence store")
        for field in _PROMOTION_FIELDS:
            if a[field] != source[field]:
                raise ValueError(
                    f"{path}: gating record {rid}: field {field!r} does not "
                    f"match raw evidence {promoted_from}: gating "
                    f"{a[field]!r} != raw {source[field]!r}")
    return rows


def load_raw_assertions(path: Path = RAW_ASSERTIONS_PATH) -> list[dict]:
    """The v2 RAW evidence store (bulk SEC Item 2.02 collection). Rows are
    validated but marked unclassified: they can never gate."""
    return _load_store(path, _RAW_COLUMNS, gating=False)


def _report_date(a: dict) -> date:
    """The date an assertion asserts: occurred_date for realized reports,
    expected_date for schedules."""
    d = a.get("occurred_date") if a["status"] == "occurred" else None
    return d or a["expected_date"]


def assertions_view(assertions: list[dict], known_as_of) -> list[dict]:
    """The information set at `known_as_of`: the LATEST assertion per
    (symbol, event_id) among those already known, minus records explicitly
    superseded or retracted by an in-view record. Nothing is ever deleted
    from the store; every past information set stays reconstructible.
    (7b-2R finding 4: the supersession key includes the symbol, and
    retractions/explicit supersession targets are honored.)"""
    in_view = [a for a in assertions if a["known_as_of_utc"] <= known_as_of]
    dead = {a["supersedes"] for a in in_view if a.get("supersedes")}
    latest: dict[tuple[str, str], dict] = {}
    for a in in_view:
        if a.get("record_type", "assertion") == "retraction":
            continue
        if a.get("record_id") and a["record_id"] in dead:
            continue
        key = (a["symbol"], a["event_id"])
        cur = latest.get(key)
        if cur is None or a["known_as_of_utc"] >= cur["known_as_of_utc"]:
            latest[key] = a
    return list(latest.values())


def earnings_gate(symbol: str, on: date, assertions: list[dict], *,
                  known_as_of) -> tuple[str, str]:
    """(state, reason) with state CLEAR | BANNED | UNKNOWN.

    CLEAR requires the information set at `known_as_of` to either identify
    the next scheduled report (a live estimated/confirmed assertion dated
    on/after `on`) or PROVE a realized report (status=occurred) within the
    previous H7_EARNINGS_POST_REPORT_GRACE_D calendar days. Expired
    estimates and passed schedules grant nothing. Multiple unresolved dates
    for one symbol/fiscal period are a CONFLICT -> UNKNOWN (owner decision
    2026-07-11: never silently trust either source, never just ban both).
    UNKNOWN always fails closed."""
    sym = symbol.upper()
    # 7b-2R.1: only VERIFIED actual quarterly earnings records gate.
    # Preliminary results, business updates, other Item 2.02 events and
    # unclassified rows are invisible here -- they never start grace and
    # never erase the risk of a later scheduled quarterly report.
    view = [a for a in assertions_view(assertions, known_as_of)
            if a["symbol"] == sym
            and a.get("event_class") == GATING_EVENT_CLASS]
    if not view:
        return GATE_UNKNOWN, GATE_REASON_NO_ASSERTIONS
    live = [a for a in view if a["status"] in ("estimated", "confirmed")]
    by_period: dict[str, set] = {}
    for a in live:
        if a["fiscal_period"]:
            by_period.setdefault(a["fiscal_period"], set()).add(
                a["expected_date"])
    for period, dates in sorted(by_period.items()):
        if len(dates) > 1 and max(dates) >= on:
            return GATE_UNKNOWN, (f"{GATE_REASON_CONFLICT_PREFIX} unresolved "
                                  f"schedule assertions for {period}")
    future = [a for a in live if a["expected_date"] >= on]
    grace = timedelta(days=config.H7_EARNINGS_POST_REPORT_GRACE_D)
    occurred_recent = [a for a in view
                       if a["status"] == "occurred"
                       and timedelta(0) <= (on - _report_date(a)) <= grace]
    if not future and not occurred_recent:
        return GATE_UNKNOWN, GATE_REASON_GRACE_EXPIRED
    rec = {
        "confirmed": [_report_date(a) for a in view
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
    upcoming = [_report_date(a)
                for a in assertions_view(assertions, known_as_of)
                if a["symbol"] == sym
                and a.get("event_class") == GATING_EVENT_CLASS
                and _report_date(a) >= on]
    return min(upcoming) if upcoming else None

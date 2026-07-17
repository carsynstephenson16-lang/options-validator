"""H9 event derivation — verified occurred reports -> causal session timing.

Spec: docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md §2.
The acceptance timestamp is the raw store's known_as_of_utc (8-K Item 2.02
acceptanceDateTime). Strict inequalities everywhere: a filing accepted exactly
at a session close belongs to the NEXT session's information set.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from data.cache_runner import session_close_utc, trading_days

H9_EVENT_CLASS_PATH = Path("data/earnings/h9_event_class_v1.csv")
H9_EVENT_CLASSES = ("quarterly_results", "business_update", "other_item_202")


@dataclass(frozen=True)
class H9Event:
    symbol: str
    occurred_date: date
    accepted_utc: datetime
    t_pre: str | None = None
    t_dec: str | None = None
    t_entry: str | None = None
    exclusion: str | None = None  # reason code once census runs


def resolve_timing(symbol: str, accepted_utc: datetime, *, start_iso: str,
                   end_iso: str) -> tuple[str | None, str | None, str | None]:
    """(t_pre, t_dec, t_entry) ISO dates inside [start_iso, end_iso], else None slots."""
    days = trading_days(start_iso, end_iso)
    t_pre = None
    t_dec = None
    for d in days:
        close = session_close_utc(d)
        if close < accepted_utc:
            t_pre = d
        elif close > accepted_utc:
            t_dec = d
            break
        # close == accepted_utc: not strictly before (so NOT t_pre) and not
        # strictly after (so NOT t_dec) — skip; t_pre stays the prior session
        # and t_dec resolves at the next iteration's close
    if t_dec is None:
        return (t_pre, None, None)
    later = [d for d in days if d > t_dec]
    t_entry = later[0] if later else None
    return (t_pre, t_dec, t_entry)


def load_event_classes(path: Path = H9_EVENT_CLASS_PATH) -> dict[tuple[str, str], str]:
    """(symbol, occurred_date_iso) -> event_class. Malformed rows fail loud."""
    out: dict[tuple[str, str], str] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            cls = row["event_class"]
            if cls not in H9_EVENT_CLASSES:
                raise ValueError(f"unknown event_class {cls!r} in {path}")
            if not row["evidence_url"].startswith("https://www.sec.gov"):
                raise ValueError(f"non-SEC evidence_url for {row['record_id']}")
            out[(row["symbol"], row["occurred_date"])] = cls
    return out


def derive_events(raw_rows: list[dict], *, symbols: tuple[str, ...],
                  start_iso: str | None = None, end_iso: str | None = None,
                  event_classes: dict[tuple[str, str], str] | None = None) -> list[H9Event]:
    """Occurred rows -> deduped H9Event list (earliest acceptance per report date).

    When `event_classes` is provided, an event is timed (resolve_timing runs)
    ONLY when its (symbol, occurred_date) classifies as "quarterly_results".
    A missing key is excluded as "unclassified_event"; any other class is
    excluded as "non_earnings_event". Excluded events are still returned
    (never silently dropped) but carry no t_pre/t_dec/t_entry.
    """
    import config
    start_iso = start_iso or config.H9_WINDOW[0]
    end_iso = end_iso or config.H9_WINDOW[1]
    best: dict[tuple[str, date], dict] = {}
    for row in raw_rows:
        if row.get("status") != "occurred" or row["symbol"] not in symbols:
            continue
        if row.get("occurred_date") is None or row.get("known_as_of_utc") is None:
            continue
        key = (row["symbol"], row["occurred_date"])
        if key not in best or row["known_as_of_utc"] < best[key]["known_as_of_utc"]:
            best[key] = row
    events = []
    for (symbol, occurred), row in sorted(best.items()):
        exclusion = None
        if event_classes is not None:
            cls = event_classes.get((symbol, occurred.isoformat()))
            if cls is None:
                exclusion = "unclassified_event"
            elif cls != "quarterly_results":
                exclusion = "non_earnings_event"
        if exclusion is not None:
            events.append(H9Event(symbol=symbol, occurred_date=occurred,
                                  accepted_utc=row["known_as_of_utc"],
                                  exclusion=exclusion))
            continue
        t_pre, t_dec, t_entry = resolve_timing(
            symbol, row["known_as_of_utc"], start_iso=start_iso, end_iso=end_iso)
        events.append(H9Event(symbol=symbol, occurred_date=occurred,
                              accepted_utc=row["known_as_of_utc"],
                              t_pre=t_pre, t_dec=t_dec, t_entry=t_entry))
    return events

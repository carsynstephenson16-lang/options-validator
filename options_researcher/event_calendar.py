"""Cached display-only event calendar and offline implied-move derivation.

Promotion of any output into ranking, selection, or signal authority requires
a separate owner decision, registration, and the 2026-07-24 gate.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping, cast
from urllib.parse import urlparse

from options_researcher.source_policy import BANNED_HOST_FRAGMENTS

CALENDAR_PATH = Path("data/events/macro_calendar.jsonl")
COMPLEX_MAP_PATH = Path("data/events/complex_map.json")
_KINDS = frozenset({"data_release", "fed_speech", "fomc_meeting", "symposium", "other"})
_SOURCE_KINDS = frozenset({"official_gov", "official_exchange", "company_ir"})
_VERIFICATIONS = frozenset({"fetched", "asserted"})
_REQUIRED = frozenset(
    {
        "event_id",
        "date",
        "time_et",
        "kind",
        "title",
        "source_url",
        "source_kind",
        "verification",
        "source_quote",
        "captured_at",
        "added_by",
    }
)


def _freeze(value: object) -> object:
    """Recursively freeze render context payloads before handing them to render."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Event:
    event_id: str
    date: date
    time_et: str | None
    kind: str
    title: str
    source_url: str
    source_kind: str
    verification: str
    source_quote: str
    captured_at: datetime
    added_by: str


@dataclass(frozen=True)
class EventView(Mapping[str, object]):
    """Immutable pre-render input; promotion requires owner decision, registration, and gate."""

    calendar: tuple[Event, ...]
    complex_map: Mapping[str, object]
    implied_moves: Mapping[str, Mapping[str, str]]
    failures: Mapping[str, str]

    def __getitem__(self, key: str) -> object:
        return {
            "calendar": self.calendar,
            "complex_map": self.complex_map,
            "implied_moves": self.implied_moves,
            "failures": self.failures,
        }[key]

    def __iter__(self) -> Iterator[str]:
        return iter(("calendar", "complex_map", "implied_moves", "failures"))

    def __len__(self) -> int:
        return 4

    @classmethod
    def create(
        cls,
        calendar: Iterable[Event],
        complex_map: Mapping[str, object],
        implied_moves: Mapping[str, Mapping[str, str]],
        failures: Mapping[str, str],
    ) -> "EventView":
        return cls(
            tuple(calendar),
            cast(Mapping[str, object], _freeze(complex_map)),
            MappingProxyType(
                {
                    key: cast(Mapping[str, str], _freeze(value))
                    for key, value in implied_moves.items()
                }
            ),
            MappingProxyType(dict(failures)),
        )


def _string(row: Mapping[str, object], name: str, *, allow_unknown: bool = False) -> str:
    value = row.get(name)
    if not isinstance(value, str) or (not value.strip() and not allow_unknown):
        raise ValueError(f"{name} is required")
    return value.strip()


def _parse(row: Mapping[str, object], *, where: str) -> Event:
    missing = _REQUIRED - row.keys()
    if missing:
        raise ValueError(f"{where}: missing required fields {sorted(missing)}")
    try:
        event_date = date.fromisoformat(_string(row, "date"))
    except ValueError as exc:
        raise ValueError(f"{where}: invalid date") from exc
    url = _string(row, "source_url")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise ValueError(f"{where}: invalid source URL")
    if any(fragment in host for fragment in BANNED_HOST_FRAGMENTS):
        raise ValueError(f"{where}: banned source host {host}")
    kind = _string(row, "kind")
    if kind not in _KINDS:
        raise ValueError(f"{where}: invalid kind")
    source_kind = _string(row, "source_kind")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError(f"{where}: invalid source_kind")
    verification = _string(row, "verification")
    if verification not in _VERIFICATIONS:
        raise ValueError(f"{where}: invalid verification")
    quote = _string(row, "source_quote", allow_unknown=True)
    if verification == "fetched" and not quote:
        raise ValueError(f"{where}: source_quote is required for fetched entries")
    try:
        captured = datetime.fromisoformat(_string(row, "captured_at").replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{where}: invalid captured_at") from exc
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError(f"{where}: captured_at must be timezone-aware")
    time_et = _string(row, "time_et", allow_unknown=True)
    return Event(
        _string(row, "event_id"),
        event_date,
        None if time_et == "UNKNOWN" else time_et,
        kind,
        _string(row, "title"),
        url,
        source_kind,
        verification,
        quote,
        captured.astimezone(timezone.utc),
        _string(row, "added_by"),
    )


def load_calendar(path: Path | str = CALENDAR_PATH) -> list[Event]:
    """Validate and return sorted cached macro events; absent calendar is empty."""
    source = Path(path)
    if not source.exists():
        return []
    events: list[Event] = []
    ids: set[str] = set()
    for number, line in enumerate(source.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{source}:{number}: invalid JSON") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{source}:{number}: event must be an object")
        event = _parse(raw, where=f"{source}:{number}")
        if event.event_id in ids:
            raise ValueError(f"{source}:{number}: duplicate event_id {event.event_id}")
        ids.add(event.event_id)
        events.append(event)
    return sorted(events, key=lambda item: (item.date, item.time_et or "99:99", item.event_id))


def calendar_with_fomc(calendar: Iterable[Event], fomc_dates: Iterable[date]) -> list[Event]:
    """Adapt the existing FOMC source without adding rows to the JSONL file."""
    from options_researcher.fomc import FOMC_PATH

    out = list(calendar)
    ids = {item.event_id for item in out}
    with open(FOMC_PATH, newline="") as handle:
        urls = {
            date.fromisoformat(row["date"]): row["source_url"] for row in csv.DictReader(handle)
        }
    for decision_date in fomc_dates:
        event_id = f"fomc-{decision_date.isoformat()}"
        if event_id not in ids:
            out.append(
                Event(
                    event_id,
                    decision_date,
                    None,
                    "fomc_meeting",
                    "FOMC decision",
                    urls[decision_date],
                    "official_gov",
                    "asserted",
                    "",
                    datetime(1970, 1, 1, tzinfo=timezone.utc),
                    "existing-fomc-source",
                )
            )
    return sorted(out, key=lambda item: (item.date, item.time_et or "99:99", item.event_id))


def load_complex_map(
    path: Path | str = COMPLEX_MAP_PATH, events: Iterable[Event] = ()
) -> dict[str, object]:
    """Load frozen cluster membership, rejecting maps written after applied events."""
    source = Path(path)
    if not source.exists():
        return {}
    raw = json.loads(source.read_text())
    if not isinstance(raw, dict) or not isinstance(raw.get("clusters"), dict):
        raise ValueError(f"{source}: invalid complex map")
    try:
        as_of = date.fromisoformat(str(raw["as_of"]))
    except (KeyError, ValueError) as exc:
        raise ValueError(f"{source}: invalid as_of") from exc
    for event in events:
        if as_of > event.date:
            raise ValueError(f"{source}: map as_of later than event {event.event_id}")
    for name, cluster in raw["clusters"].items():
        if not isinstance(cluster, dict) or not all(
            isinstance(cluster.get(field), list) for field in ("members", "events_propagate_from")
        ):
            raise ValueError(f"{source}: invalid cluster {name}")
    return raw


def provenance_markers(event: Event, evaluation_date: date) -> tuple[str, ...]:
    markers: list[str] = []
    if event.verification == "asserted":
        markers.append("source not yet fetched — verify before relying")
    if (evaluation_date - event.captured_at.date()).days > 30:
        markers.append("re-verify source")
    return tuple(markers)


def implied_move(
    chain: Iterable[Mapping[str, object]],
    session: str,
    spot: float | None,
    source: str | None,
    *,
    spot_timestamp: str = "",
    receipt_session: str = "",
) -> dict[str, str]:
    """Compute nearest 1–21 day ATM call+put mid / verified spot, or explain refusal."""
    if source != "schwab_preclose":
        return {"text": "UNAVAILABLE", "reason": "non-Schwab source"}
    if spot is None:
        return {
            "text": "UNAVAILABLE",
            "reason": "missing verified stock_snapshot spot" if source else "missing spot",
        }
    if (
        not isinstance(spot, (int, float))
        or isinstance(spot, bool)
        or not math.isfinite(spot)
        or spot <= 0
    ):
        return {"text": "UNAVAILABLE", "reason": "missing verified stock_snapshot spot"}
    try:
        start = date.fromisoformat(session)
    except ValueError:
        return {"text": "UNAVAILABLE", "reason": "invalid session"}
    rows = list(chain.to_dict("records")) if hasattr(chain, "to_dict") else list(chain)
    by_expiry: dict[date, list[Mapping[str, object]]] = {}
    for row in rows:
        expiry_raw = row.get("expiration", row.get("expiry"))
        try:
            expiry = date.fromisoformat(str(expiry_raw))
        except ValueError:
            continue
        if 1 <= (expiry - start).days <= 21:
            by_expiry.setdefault(expiry, []).append(row)
    if not by_expiry:
        return {"text": "UNAVAILABLE", "reason": "no expiry within 1–21 calendar days"}
    expiry = min(by_expiry)
    rows = by_expiry[expiry]
    strikes = sorted(
        {float(row["strike"]) for row in rows if isinstance(row.get("strike"), (int, float))}
    )
    if not strikes:
        return {"text": "UNAVAILABLE", "reason": "missing strikes"}
    strike = min(strikes, key=lambda value: (abs(value - float(spot)), value))
    mids: dict[str, float] = {}
    for row in rows:
        if row.get("strike") != strike:
            continue
        side = str(row.get("right", row.get("putCall", ""))).upper()
        side = "CALL" if side in {"C", "CALL"} else "PUT" if side in {"P", "PUT"} else side
        bid, ask = row.get("bid"), row.get("ask")
        if (
            isinstance(bid, (int, float))
            and isinstance(ask, (int, float))
            and not isinstance(bid, bool)
            and not isinstance(ask, bool)
            and bid >= 0
            and ask >= bid
        ):
            mids[side] = (float(bid) + float(ask)) / 2
    if "CALL" not in mids:
        return {"text": "UNAVAILABLE", "reason": "missing call quote at ATM strike"}
    if "PUT" not in mids:
        return {"text": "UNAVAILABLE", "reason": "missing put quote at ATM strike"}
    move = (mids["CALL"] + mids["PUT"]) / float(spot)
    return {
        "text": f"{move:.2%}",
        "method": "atm_straddle_mid/v1",
        "expiry": expiry.isoformat(),
        "strike": f"{strike:g}",
        "spot_source": "stock_snapshot",
        "chain_session": session,
        "capture_convention": "15:45 ET preclose",
        "intraday_receipt_session": receipt_session or session,
        "spot_timestamp": spot_timestamp or "unavailable",
    }


def _add(args: argparse.Namespace) -> int:
    row = {key: getattr(args, key) for key in _REQUIRED}
    _parse(row, where="command line")
    path = Path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        existing = load_calendar(path)
        if any(item.event_id == args.event_id for item in existing):
            raise ValueError(f"duplicate event_id {args.event_id}")
        handle.seek(0, os.SEEK_END)
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manage cached display-only event calendar")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add")
    add.add_argument("--path", default=str(CALENDAR_PATH))
    for field in _REQUIRED:
        add.add_argument("--" + field.replace("_", "-"), dest=field, required=True)
    args = parser.parse_args(argv)
    try:
        return _add(args)
    except ValueError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

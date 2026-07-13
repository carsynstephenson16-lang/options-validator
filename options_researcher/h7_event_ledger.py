"""H7 forward-roadmap Stage 3 -- append-only, hash-chained forward-event
ledger (BUILD-ONLY; INACTIVE). A dedicated chain for future H7 forward-paper
events, SEPARATE from the research experiment ledger (`research/ledger.py`
is a design pattern only -- this never touches ledger/experiments.jsonl,
ledger/HEAD, or trial_count).

Default store (NOT created during Stage 3 -- the first real event is
prohibited until Stage 8 activation):
    ledger/h7_forward/events.jsonl   append-only JSONL, one record per line
    ledger/h7_forward/HEAD           current chain tip (record_hash)

Importing or verifying an absent/empty store creates nothing.

Concurrency: appends hold an exclusive directory lock; verify/read hold a
shared lock so readers wait through the JSONL-fsync -> HEAD-replace window.
Both occurred_at_utc and recorded_at_utc require a zero UTC offset.

Public seams (the only supported surface):
    append_event(event, *, base_dir, clock=None, expected_head=...) -> AppendResult
    read_events(base_dir) -> list[StoredEvent]     (verifies first)
    verify(base_dir) -> VerifyResult               (raises on corruption)
    CLI:  python -m options_researcher.h7_event_ledger verify [--base-dir P]

Crash model (honest, not two-file-atomic): append fsyncs events.jsonl then
atomically replaces HEAD. A crash between the two leaves a stale-HEAD
mismatch that the next verify/append REFUSES. No auto-repair, no silent
truncation, no best-effort success.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from research.hashing import canonical_json, sha256_hex

_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9._:\-]+$")
_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]+$")
_SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

SCHEMA_VERSION = 1
_EVENTS_NAME = "events.jsonl"
_HEAD_NAME = "HEAD"
_ZERO_HASH = "0" * 64

EVENT_TYPES = (
    "source_health", "data_gate", "board_resolution", "lane_displaced",
    "entry_intent", "exit_intent", "owner_approval", "paper_fill",
    "skip", "data_gap",
)
LANES = ("a", "b", "c")
# The exact logical fields a caller supplies. logical_hash commits to these.
LOGICAL_FIELDS = (
    "schema_version", "event_id", "event_type", "occurred_at_utc",
    "evaluation_session", "symbol", "lane", "causes", "payload",
)
# Chain fields append_event adds. record_hash commits to everything else.
_CHAIN_FIELDS = ("seq", "recorded_at_utc", "logical_hash", "prev_hash")


class LedgerError(RuntimeError):
    """Base for every H7 forward-ledger failure."""


class EventValidationError(LedgerError):
    """The supplied logical event is invalid -- refused before any write."""


class EventConflictError(LedgerError):
    """An event_id already exists with different logical content."""


class LedgerHeadConflictError(LedgerError):
    """The verified chain tip changed after a caller derived its decision."""


class LedgerCorruptionError(LedgerError):
    """The stored chain/HEAD failed verification -- fail closed."""


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    empty: bool
    count: int
    head: str | None


@dataclass(frozen=True)
class AppendResult:
    seq: int
    record_hash: str
    appended: bool


@dataclass(frozen=True)
class StoredEvent:
    seq: int
    event_id: str
    event_type: str
    occurred_at_utc: str
    evaluation_session: str
    symbol: str | None
    lane: str | None
    causes: list[str]
    payload: dict
    recorded_at_utc: str
    logical_hash: str
    prev_hash: str
    record_hash: str


def _paths(base_dir) -> tuple[Path, Path]:
    base = Path(base_dir)
    return base / _EVENTS_NAME, base / _HEAD_NAME


def _reject_const(token):
    raise EventValidationError(f"non-finite JSON literal {token!r} not allowed")


def _parse_utc_timestamp(value, field: str) -> datetime:
    if not isinstance(value, str):
        raise EventValidationError(f"{field} must be a string")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise EventValidationError(f"{field} invalid: {exc}") from exc
    if (dt.tzinfo is None or dt.utcoffset() is None
            or dt.utcoffset() != timedelta(0)):
        raise EventValidationError(f"{field} must be UTC")
    return dt


def _validate_logical(event) -> dict:
    """Validate a caller-supplied logical event and return it as an ordered
    clean dict. Raises EventValidationError before any filesystem touch.
    Backward causal-reference existence is checked later against the store;
    here we enforce shape, types, canonical values, and no self/duplicate
    causes."""
    if isinstance(event, StoredEvent):
        event = {k: getattr(event, k) for k in LOGICAL_FIELDS}
    if not isinstance(event, dict):
        raise EventValidationError("event must be a dict or ForwardEvent")
    keys = set(event.keys())
    if keys != set(LOGICAL_FIELDS):
        raise EventValidationError(
            f"event fields must be exactly {sorted(LOGICAL_FIELDS)}; "
            f"got {sorted(keys)}")
    if event["schema_version"] != SCHEMA_VERSION:
        raise EventValidationError("schema_version must be 1")
    eid = event["event_id"]
    if not isinstance(eid, str) or not _EVENT_ID_RE.fullmatch(eid):
        raise EventValidationError("event_id must be a canonical non-empty id")
    if event["event_type"] not in EVENT_TYPES:
        raise EventValidationError(
            f"event_type must be one of {EVENT_TYPES}")
    _parse_utc_timestamp(event["occurred_at_utc"], "occurred_at_utc")
    session = event["evaluation_session"]
    if not isinstance(session, str) or not _SESSION_RE.fullmatch(session):
        raise EventValidationError("evaluation_session must be YYYY-MM-DD")
    try:
        date.fromisoformat(session)
    except ValueError as exc:
        raise EventValidationError(
            f"evaluation_session invalid: {exc}") from exc
    symbol = event["symbol"]
    if symbol is not None and (
            not isinstance(symbol, str) or symbol != symbol.upper()
            or not _SYMBOL_RE.fullmatch(symbol)):
        raise EventValidationError(
            "symbol must be a canonical uppercase ticker or null")
    if event["lane"] is not None and event["lane"] not in LANES:
        raise EventValidationError("lane must be a, b, c, or null")
    causes = event["causes"]
    if not isinstance(causes, list) or any(
            not isinstance(c, str) or not c for c in causes):
        raise EventValidationError("causes must be a list of event_id strings")
    if len(set(causes)) != len(causes):
        raise EventValidationError("causes must not contain duplicates")
    if not isinstance(event["payload"], dict):
        raise EventValidationError("payload must be a JSON object")
    ordered = {k: event[k] for k in LOGICAL_FIELDS}
    try:  # rejects NaN/Infinity and non-JSON-serializable values, no stringify
        canonical_json(ordered)
    except (ValueError, TypeError) as exc:
        raise EventValidationError(
            f"payload is not canonical-JSON serializable: {exc}") from exc
    return ordered


def _to_stored(obj: dict) -> StoredEvent:
    return StoredEvent(**{k: obj[k] for k in (
        "seq", "event_id", "event_type", "occurred_at_utc",
        "evaluation_session", "symbol", "lane", "causes", "payload",
        "recorded_at_utc", "logical_hash", "prev_hash", "record_hash")})


def _load_verified(events_path: Path, head_path: Path) -> list[StoredEvent]:
    """Full fail-closed verification; returns records ([] for absent/empty).
    Never returns partially verified records."""
    ev_exists, head_exists = events_path.exists(), head_path.exists()
    if not ev_exists and not head_exists:
        return []
    if ev_exists != head_exists:
        raise LedgerCorruptionError(
            "exactly one ledger file present -- corrupt")
    raw = events_path.read_bytes().decode("utf-8")
    if raw == "":
        raise LedgerCorruptionError("events.jsonl present but empty")
    if not raw.endswith("\n"):
        raise LedgerCorruptionError(
            "events.jsonl does not end with newline (partial write?)")
    parts = raw.split("\n")
    if parts[-1] != "":
        raise LedgerCorruptionError("trailing garbage after final record")
    lines = parts[:-1]
    expected_keys = set(LOGICAL_FIELDS) | set(_CHAIN_FIELDS) | {"record_hash"}
    records: list[StoredEvent] = []
    seen: set[str] = set()
    prev = _ZERO_HASH
    for i, line in enumerate(lines):
        if line == "":
            raise LedgerCorruptionError(f"blank line at seq {i}")
        try:
            obj = json.loads(line, parse_constant=_reject_const)
        except json.JSONDecodeError as exc:
            raise LedgerCorruptionError(
                f"invalid JSON at seq {i}: {exc}") from exc
        except EventValidationError as exc:
            raise LedgerCorruptionError(f"seq {i}: {exc}") from exc
        if not isinstance(obj, dict):
            raise LedgerCorruptionError(f"record at seq {i} is not an object")
        if set(obj.keys()) != expected_keys:
            raise LedgerCorruptionError(
                f"unexpected or missing fields at seq {i}")
        if line != canonical_json(obj):
            raise LedgerCorruptionError(f"non-canonical JSON at seq {i}")
        if obj["seq"] != i:
            raise LedgerCorruptionError(
                f"seq {obj['seq']} out of order (expected {i})")
        if obj["prev_hash"] != prev:
            raise LedgerCorruptionError(f"prev_hash break at seq {i}")
        logical = {k: obj[k] for k in LOGICAL_FIELDS}
        try:
            _validate_logical(logical)
            _parse_utc_timestamp(obj["recorded_at_utc"], "recorded_at_utc")
        except EventValidationError as exc:
            raise LedgerCorruptionError(
                f"invalid stored event at seq {i}: {exc}") from exc
        if obj["logical_hash"] != sha256_hex(canonical_json(logical)):
            raise LedgerCorruptionError(f"logical_hash mismatch at seq {i}")
        body = {k: v for k, v in obj.items() if k != "record_hash"}
        if obj["record_hash"] != sha256_hex(canonical_json(body)):
            raise LedgerCorruptionError(f"record_hash mismatch at seq {i}")
        if obj["event_id"] in seen:
            raise LedgerCorruptionError(f"duplicate event_id at seq {i}")
        for c in obj["causes"]:
            if c == obj["event_id"] or c not in seen:
                raise LedgerCorruptionError(
                    f"cause does not reference an earlier event at seq {i}")
        seen.add(obj["event_id"])
        records.append(_to_stored(obj))
        prev = obj["record_hash"]
    head_val = head_path.read_text().strip()
    if head_val != records[-1].record_hash:
        raise LedgerCorruptionError("HEAD does not match chain tip")
    return records


def _load_with_shared_lock(base_dir) -> list[StoredEvent]:
    """Verify/read under a shared directory lock so a reader cannot observe
    the intentional writer gap between events.jsonl fsync and HEAD replace.
    An absent base remains VALID EMPTY and is never created."""
    base = Path(base_dir)
    events_path, head_path = _paths(base)
    if not base.exists():
        # Linearize this read before any concurrent first append. Do not call
        # back into the filesystem after observing absence: a writer could
        # create the directory and enter its two-file commit gap in between.
        return []
    dir_fd = os.open(base, os.O_RDONLY)
    try:
        fcntl.flock(dir_fd, fcntl.LOCK_SH)
        return _load_verified(events_path, head_path)
    finally:
        fcntl.flock(dir_fd, fcntl.LOCK_UN)
        os.close(dir_fd)


def verify(base_dir) -> VerifyResult:
    """Verify the whole chain + HEAD. Both files absent -> VALID EMPTY,
    creating nothing. Any corruption raises LedgerCorruptionError."""
    records = _load_with_shared_lock(base_dir)
    if not records:
        return VerifyResult(valid=True, empty=True, count=0, head=None)
    return VerifyResult(valid=True, empty=False, count=len(records),
                        head=records[-1].record_hash)


def read_events(base_dir) -> list[StoredEvent]:
    """Return typed records ONLY after full verification (never partial)."""
    return _load_with_shared_lock(base_dir)


def _clock_iso(clock) -> str:
    dt = clock() if clock is not None else datetime.now(timezone.utc)
    if (not isinstance(dt, datetime) or dt.tzinfo is None
            or dt.utcoffset() is None or dt.utcoffset() != timedelta(0)):
        raise EventValidationError("clock must return a UTC datetime")
    return dt.isoformat()


def _write_all(fd: int, data: bytes) -> None:
    """Write every byte (POSIX permits a short os.write on a regular file)."""
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def _atomic_write_head(head_path: Path, value: str) -> None:
    tmp = head_path.with_name(head_path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        _write_all(fd, (value + "\n").encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, head_path)


_EXPECTED_HEAD_UNSET = object()


def append_event(
    event, *, base_dir, clock=None, expected_head=_EXPECTED_HEAD_UNSET
) -> AppendResult:
    """Append exactly one forward event, or return the existing record if the
    same event_id + identical logical content already exists (idempotent).
    A same event_id with different content raises EventConflictError. The
    whole read-verify-dedup-seq-append-fsync-HEAD critical section runs under
    an exclusive directory lock so concurrent writers cannot fork the chain
    or reuse a seq. When ``expected_head`` is supplied (including explicit
    ``None`` for an empty ledger), a changed verified tip refuses before
    deduplication or write so a decision derived from stale state cannot land.

    Logical field/shape validation happens BEFORE any filesystem touch (an
    invalid event creates nothing). Causal backward-reference validation
    needs the current chain, so it runs under the lock after the ledger
    directory exists; a causal refusal never creates events.jsonl or HEAD
    (an empty ledger dir verifies as VALID EMPTY)."""
    logical = _validate_logical(event)
    if expected_head is not _EXPECTED_HEAD_UNSET and not (
        expected_head is None
        or (
            isinstance(expected_head, str)
            and len(expected_head) == 64
            and all(ch in "0123456789abcdef" for ch in expected_head)
        )
    ):
        raise EventValidationError("expected_head must be None or a lowercase sha256")
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    events_path, head_path = _paths(base)
    dir_fd = os.open(base, os.O_RDONLY)
    try:
        fcntl.flock(dir_fd, fcntl.LOCK_EX)
        existing = _load_verified(events_path, head_path)  # fail closed first
        current_head = existing[-1].record_hash if existing else None
        if (
            expected_head is not _EXPECTED_HEAD_UNSET
            and expected_head != current_head
        ):
            raise LedgerHeadConflictError(
                f"ledger HEAD changed (expected {expected_head!r}, "
                f"found {current_head!r})"
            )
        logical_hash = sha256_hex(canonical_json(logical))
        by_id = {e.event_id: e for e in existing}
        prior = by_id.get(logical["event_id"])
        if prior is not None:
            if prior.logical_hash == logical_hash:
                return AppendResult(seq=prior.seq,
                                    record_hash=prior.record_hash,
                                    appended=False)
            raise EventConflictError(
                f"event_id {logical['event_id']!r} already exists with "
                "different logical content")
        known = set(by_id)
        for c in logical["causes"]:
            if c == logical["event_id"]:
                raise EventValidationError("an event cannot cause itself")
            if c not in known:
                raise EventValidationError(
                    f"cause {c!r} does not name an earlier event in this ledger")
        seq = len(existing)
        prev_hash = existing[-1].record_hash if existing else _ZERO_HASH
        record = dict(logical)
        record["seq"] = seq
        record["recorded_at_utc"] = _clock_iso(clock)
        record["logical_hash"] = logical_hash
        record["prev_hash"] = prev_hash
        record_hash = sha256_hex(canonical_json(record))
        record["record_hash"] = record_hash
        line = canonical_json(record) + "\n"
        fd = os.open(events_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            _write_all(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        _atomic_write_head(head_path, record_hash)
        os.fsync(dir_fd)
        return AppendResult(seq=seq, record_hash=record_hash, appended=True)
    finally:
        fcntl.flock(dir_fd, fcntl.LOCK_UN)
        os.close(dir_fd)


def _cli_verify(base_dir) -> int:
    try:
        res = verify(base_dir)
    except LedgerError as exc:
        print(f"INVALID -- {exc}")
        return 2
    if res.empty:
        print("VALID EMPTY")
        return 0
    print(f"VALID records={res.count} head={(res.head or '')[:12]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="H7 forward-event ledger tool (Stage 3, BUILD-ONLY). "
                    "Only `verify` is exposed; later stages call the typed "
                    "Python API to append.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="verify the chain (exit 0 valid/empty, "
                                      "2 corrupt/invalid)")
    v.add_argument("--base-dir", default="ledger/h7_forward")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if args.cmd == "verify":
        return _cli_verify(args.base_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

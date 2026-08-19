"""Append one daily H10b observation without changing the paper book.

The source receipt is immutable evidence from ``h10_watch``. This recorder
hashes it, summarizes every name, counts the separate owner-recorded book, and
appends one JSONL line per requested date. Same-date/same-hash reruns are
no-ops; same-date/different-hash reruns and malformed history fail closed.
"""

from __future__ import annotations

import csv
import fcntl
import hashlib
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

import config
from options_researcher.h10_watch import (
    BOOK_FIELDS,
    H10_BOOK_PATH,
    H10_RECEIPT_DIR,
    H10A_ADJUDICATED,
    MIXED_TIMING_CONVENTION,
)

LEGACY_OBSERVATIONS_PATH = Path("reports/h10/observations.jsonl")
H10B_OBSERVATIONS_PATH = Path("reports/h10/h10b_observations.jsonl")
_LEGACY_OBSERVATION_FIELDS = {
    "as_of",
    "receipt",
    "receipt_sha256",
    "summary",
    "open_positions",
}
_H10B_OBSERVATION_FIELDS = {
    "hypothesis",
    "as_of",
    "evaluation_session",
    "receipt",
    "receipt_sha256",
    "summary",
    "open_positions",
    "mixed_timing_convention",
}
_SUMMARY_FIELDS = {"fired", "no_signal", "skipped"}
_RECEIPT_FIELDS = {
    "as_of",
    "evaluation_session",
    "evaluations",
    "book_action_required",
}
_EVALUATION_FIELDS = {
    "symbol",
    "signals",
    "h10a_status",
    "window_status",
    "status",
    "reason",
    "admitted_contracts",
    "candidate_contract",
    "book_action_required",
    "chain_session",
    "chain_timing_convention",
}
_LEGACY_H10B_SESSIONS = {
    "2026-07-23": "2026-07-22",
    "2026-07-24": "2026-07-23",
    "2026-07-27": "2026-07-24",
    "2026-07-28": "2026-07-27",
}


class ObservationError(RuntimeError):
    """An input cannot produce a trustworthy observation."""


class ObservationLogMalformed(ObservationError):
    """Existing append-only history is malformed or internally duplicated."""


class ObservationConflict(ObservationError):
    """The requested date was already recorded from different evidence."""


def _receipt_reference(as_of: str) -> str:
    return f"reports/h10/receipts/h10_watch_{as_of}.json"


def _load_receipt(path: Path, *, as_of: str) -> tuple[dict[str, Any], str]:
    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObservationError(f"receipt unreadable: {type(exc).__name__}: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != _RECEIPT_FIELDS:
        raise ObservationError("receipt schema does not match h10_watch")
    if payload.get("as_of") != as_of:
        raise ObservationError(f"receipt as_of {payload.get('as_of')!r} does not match {as_of}")
    try:
        evaluation_session = date.fromisoformat(str(payload["evaluation_session"]))
    except ValueError as exc:
        raise ObservationError("receipt evaluation_session is not ISO date") from exc
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list):
        raise ObservationError("receipt evaluations is not a list")
    if not isinstance(payload.get("book_action_required"), bool):
        raise ObservationError("receipt book_action_required is not boolean")
    if evaluation_session.isoformat() < config.H10B_RESUME_FLOOR_SESSION:
        raise ObservationError("receipt evaluation_session is before H10b resume floor")
    return payload, hashlib.sha256(raw).hexdigest()


def _summary(receipt: dict[str, Any]) -> dict[str, Any]:
    fired: list[str] = []
    no_signal: list[str] = []
    skipped: dict[str, str] = {}
    seen: set[str] = set()
    actions: list[bool] = []
    for position, row in enumerate(receipt["evaluations"], start=1):
        if not isinstance(row, dict) or set(row) != _EVALUATION_FIELDS:
            raise ObservationError(f"receipt evaluation {position} has unexpected schema")
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ObservationError(f"receipt evaluation {position} has no symbol")
        symbol = symbol.strip().upper()
        if symbol in seen:
            raise ObservationError(f"receipt repeats symbol {symbol}")
        seen.add(symbol)
        signals = row.get("signals")
        if (
            not isinstance(signals, dict)
            or set(signals) != {"H10a", "H10b"}
            or signals.get("H10a") is not None
            or not isinstance(signals.get("H10b"), (bool, type(None)))
            or row.get("h10a_status") != H10A_ADJUDICATED
            or row.get("chain_timing_convention") != MIXED_TIMING_CONVENTION
        ):
            raise ObservationError(
                f"receipt evaluation {position} is not a post-resumption H10b row"
            )
        status = row.get("status")
        action = row.get("book_action_required")
        if type(action) is not bool:
            raise ObservationError(f"row {symbol} has invalid book_action_required")
        if status == "FIRED":
            if signals["H10b"] is not True or action is not True or row.get("reason") is not None:
                raise ObservationError(f"FIRED row {symbol} has invalid signal/action semantics")
            fired.append(symbol)
        elif status == "NO_SIGNAL":
            if signals["H10b"] is not False or action is not False or row.get("reason") is not None:
                raise ObservationError(
                    f"NO_SIGNAL row {symbol} has invalid signal/action semantics"
                )
            no_signal.append(symbol)
        elif status == "SKIPPED":
            reason = row.get("reason")
            if (
                not isinstance(reason, str)
                or not reason
                or action is not False
                or signals["H10b"] is False
            ):
                raise ObservationError(f"SKIPPED row {symbol} has invalid signal/action semantics")
            skipped[symbol] = reason
        else:
            raise ObservationError(f"row {symbol} has unknown status {status!r}")
        actions.append(action)
    if receipt["book_action_required"] != any(actions):
        raise ObservationError("receipt book_action_required does not match evaluation rows")
    return {
        "fired": sorted(fired),
        "no_signal": sorted(no_signal),
        "skipped": dict(sorted(skipped.items())),
    }


def count_open_positions(path: Path = H10_BOOK_PATH) -> int:
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != BOOK_FIELDS:
                raise ObservationError(f"book header {reader.fieldnames} != {BOOK_FIELDS}")
            count = 0
            for line_number, row in enumerate(reader, start=2):
                if not (row["id"] or "").strip():
                    raise ObservationError(f"book line {line_number} has no id")
                if not (row["exit_date"] or "").strip():
                    count += 1
    except ObservationError:
        raise
    except (OSError, KeyError, TypeError, csv.Error) as exc:
        raise ObservationError(f"book unreadable: {type(exc).__name__}: {exc}") from exc
    return count


def build_h10b_observation(*, as_of: str, receipt_path: Path, book_path: Path) -> dict[str, Any]:
    receipt, receipt_hash = _load_receipt(Path(receipt_path), as_of=as_of)
    return {
        "hypothesis": "H10b",
        "as_of": as_of,
        "evaluation_session": receipt["evaluation_session"],
        "receipt": _receipt_reference(as_of),
        "receipt_sha256": receipt_hash,
        "summary": _summary(receipt),
        "open_positions": count_open_positions(Path(book_path)),
        "mixed_timing_convention": MIXED_TIMING_CONVENTION,
    }


def _validate_legacy_existing(value: Any, *, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _LEGACY_OBSERVATION_FIELDS:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: observation schema mismatch")
    as_of = value.get("as_of")
    if not isinstance(as_of, str):
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid as_of")
    try:
        date.fromisoformat(as_of)
    except ValueError as exc:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid as_of") from exc
    receipt = value.get("receipt")
    if not isinstance(receipt, str) or not receipt:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid receipt path")
    receipt_hash = value.get("receipt_sha256")
    if not isinstance(receipt_hash, str) or re.fullmatch(r"[0-9a-f]{64}", receipt_hash) is None:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid receipt_sha256")
    summary = value.get("summary")
    if not isinstance(summary, dict) or set(summary) != _SUMMARY_FIELDS:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid summary")
    if (
        not isinstance(summary["fired"], list)
        or not isinstance(summary["no_signal"], list)
        or not isinstance(summary["skipped"], dict)
    ):
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid summary values")
    open_positions = value.get("open_positions")
    if (
        not isinstance(open_positions, int)
        or isinstance(open_positions, bool)
        or open_positions < 0
    ):
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid open_positions")
    return value


def _validate_h10b_existing(value: Any, *, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _H10B_OBSERVATION_FIELDS:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: H10b observation schema mismatch"
        )
    if value.get("hypothesis") != "H10b":
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid hypothesis")
    evaluation_session = value.get("evaluation_session")
    if not isinstance(evaluation_session, str):
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid evaluation_session")
    try:
        if date.fromisoformat(evaluation_session).isoformat() != evaluation_session:
            raise ValueError("not canonical")
    except ValueError as exc:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid evaluation_session"
        ) from exc
    if evaluation_session < config.H10B_RESUME_FLOOR_SESSION:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: pre-floor H10b observation")
    if value.get("mixed_timing_convention") != MIXED_TIMING_CONVENTION:
        raise ObservationLogMalformed(f"MALFORMED line {line_number}: invalid timing convention")
    checked = _validate_legacy_existing(
        {key: value[key] for key in _LEGACY_OBSERVATION_FIELDS},
        line_number=line_number,
    )
    return {**checked, **value}


def _append_record(
    record: dict[str, Any],
    path: Path,
    *,
    validator: Any,
) -> bool:
    """Append `record`; return False for an identical prior observation."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            existing_by_date: dict[str, dict[str, Any]] = {}
            for line_number, line in enumerate(handle, start=1):
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ObservationLogMalformed(f"MALFORMED line {line_number}: {exc}") from exc
                existing = validator(parsed, line_number=line_number)
                existing_as_of = existing["as_of"]
                if existing_as_of in existing_by_date:
                    raise ObservationLogMalformed(f"MALFORMED duplicate as_of {existing_as_of}")
                existing_by_date[existing_as_of] = existing

            prior = existing_by_date.get(record["as_of"])
            if prior is not None:
                if prior["receipt_sha256"] == record["receipt_sha256"]:
                    return False
                raise ObservationConflict(
                    f"CONFLICT as_of {record['as_of']} has receipt hash "
                    f"{prior['receipt_sha256']}, not {record['receipt_sha256']}"
                )

            encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
            handle.seek(0, os.SEEK_END)
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def append_h10b_observation(record: dict[str, Any], path: Path) -> bool:
    """Append one H10b record; legacy H10 observations are read-only history."""
    _validate_h10b_existing(record, line_number=0)
    return _append_record(record, path, validator=_validate_h10b_existing)


def _read_jsonl(path: Path, *, validator: Any) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ObservationLogMalformed(
            f"MALFORMED unreadable observation log: {type(exc).__name__}: {exc}"
        ) from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            rows.append(validator(json.loads(line), line_number=line_number))
        except json.JSONDecodeError as exc:
            raise ObservationLogMalformed(f"MALFORMED line {line_number}: {exc}") from exc
    return rows


def _verify_receipt_binding(
    *,
    root: Path,
    row: dict[str, Any],
    expected_session: str,
    source: str,
) -> None:
    as_of = row["as_of"]
    expected_reference = _receipt_reference(as_of)
    if row["receipt"] != expected_reference:
        raise ObservationLogMalformed(
            f"MALFORMED {source} H10 observation {as_of}: receipt reference mismatch"
        )
    receipt_path = root / expected_reference
    try:
        raw = receipt_path.read_bytes()
        receipt = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ObservationLogMalformed(
            f"MALFORMED {source} H10 receipt {as_of}: {type(exc).__name__}: {exc}"
        ) from exc
    if hashlib.sha256(raw).hexdigest() != row["receipt_sha256"]:
        raise ObservationLogMalformed(
            f"MALFORMED {source} H10 receipt {as_of}: receipt hash mismatch"
        )
    if (
        not isinstance(receipt, dict)
        or receipt.get("as_of") != as_of
        or receipt.get("evaluation_session") != expected_session
    ):
        raise ObservationLogMalformed(f"MALFORMED {source} H10 receipt {as_of}: session mismatch")


def read_h10b_observation_union(
    *,
    root: Path = Path("."),
    legacy_observations_path: Path = LEGACY_OBSERVATIONS_PATH,
    h10b_observations_path: Path = H10B_OBSERVATIONS_PATH,
) -> dict[str, Any]:
    """Read H10b's legacy and resumed records with the permanent session hole."""
    root = Path(root)
    legacy_rows = _read_jsonl(Path(legacy_observations_path), validator=_validate_legacy_existing)
    legacy: list[dict[str, Any]] = []
    legacy_by_run: dict[str, dict[str, Any]] = {}
    for row in legacy_rows:
        as_of = row["as_of"]
        if as_of in legacy_by_run:
            raise ObservationLogMalformed(f"MALFORMED duplicate legacy H10 run {as_of}")
        expected_session = _LEGACY_H10B_SESSIONS.get(as_of)
        if expected_session is None:
            raise ObservationLogMalformed(
                f"MALFORMED legacy H10 observation has unexpected run date {as_of}"
            )
        _verify_receipt_binding(
            root=root,
            row=row,
            expected_session=expected_session,
            source="legacy",
        )
        legacy_by_run[as_of] = row
        legacy.append(
            {
                **row,
                "hypothesis": "H10b",
                "evaluation_session": expected_session,
            }
        )
    resumed = _read_jsonl(Path(h10b_observations_path), validator=_validate_h10b_existing)
    if set(legacy_by_run) != set(_LEGACY_H10B_SESSIONS):
        missing = sorted(set(_LEGACY_H10B_SESSIONS) - set(legacy_by_run))
        unexpected = sorted(set(legacy_by_run) - set(_LEGACY_H10B_SESSIONS))
        raise ObservationLogMalformed(
            f"MALFORMED legacy H10 history is incomplete: missing={missing}, unexpected={unexpected}"
        )
    resumed_runs: set[str] = set()
    resumed_sessions: set[str] = set()
    for row in resumed:
        as_of = row["as_of"]
        evaluation_session = row["evaluation_session"]
        if as_of in resumed_runs or evaluation_session in resumed_sessions:
            raise ObservationLogMalformed(
                f"MALFORMED duplicate resumed H10 identity run={as_of} session={evaluation_session}"
            )
        _verify_receipt_binding(
            root=root,
            row=row,
            expected_session=evaluation_session,
            source="resumed",
        )
        resumed_runs.add(as_of)
        resumed_sessions.add(evaluation_session)
    legacy_sessions = {row["evaluation_session"] for row in legacy}
    if legacy_sessions & resumed_sessions:
        raise ObservationLogMalformed("MALFORMED H10 union repeats a legacy evaluation session")
    observations = sorted(
        [*legacy, *resumed], key=lambda row: (row["evaluation_session"], row["as_of"])
    )
    return {
        "observations": observations,
        "unobserved_evaluation_sessions": {
            "after_evaluation_session": "2026-07-27",
            "before_evaluation_session": config.H10B_RESUME_FLOOR_SESSION,
        },
    }


def main(
    argv: list[str] | None = None,
    *,
    receipt_path: Path | None = None,
    observations_path: Path = H10B_OBSERVATIONS_PATH,
    legacy_observations_path: Path = LEGACY_OBSERVATIONS_PATH,
    book_path: Path = H10_BOOK_PATH,
) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Append one H10 watcher observation (never writes the book)"
    )
    parser.add_argument("--as-of", required=True, help="daily run date YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        date.fromisoformat(args.as_of)
    except ValueError:
        print(f"H10 OBSERVE REFUSED -- invalid --as-of {args.as_of!r}")
        return 2

    source = (
        Path(receipt_path)
        if receipt_path is not None
        else H10_RECEIPT_DIR / f"h10_watch_{args.as_of}.json"
    )
    if Path(observations_path) == Path(legacy_observations_path):
        print("H10 OBSERVE REFUSED -- legacy observations are read-only history")
        return 2
    try:
        record = build_h10b_observation(
            as_of=args.as_of, receipt_path=source, book_path=Path(book_path)
        )
        appended = append_h10b_observation(record, Path(observations_path))
    except ObservationConflict as exc:
        print(f"H10 OBSERVE CONFLICT -- {exc}")
        return 2
    except ObservationLogMalformed as exc:
        print(f"H10 OBSERVE MALFORMED -- {exc}")
        return 2
    except (ObservationError, OSError, ValueError) as exc:
        print(f"H10 OBSERVE REFUSED -- {type(exc).__name__}: {exc}")
        return 2
    if appended:
        print(f"H10 OBSERVE appended as_of={args.as_of} to {observations_path}")
    else:
        print(f"H10 OBSERVE already recorded as_of={args.as_of} with the same receipt hash; no-op")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

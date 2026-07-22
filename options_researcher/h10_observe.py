"""Append one daily H10 watcher observation without changing the paper book.

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

from options_researcher.h10_watch import (
    BOOK_FIELDS,
    H10_BOOK_PATH,
    H10_RECEIPT_DIR,
)

OBSERVATIONS_PATH = Path("reports/h10/observations.jsonl")
_OBSERVATION_FIELDS = {
    "as_of",
    "receipt",
    "receipt_sha256",
    "summary",
    "open_positions",
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
    "status",
    "reason",
    "admitted_contracts",
    "candidate_contract",
    "book_action_required",
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
        raise ObservationError(
            f"receipt unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(payload, dict) or set(payload) != _RECEIPT_FIELDS:
        raise ObservationError("receipt schema does not match h10_watch")
    if payload.get("as_of") != as_of:
        raise ObservationError(
            f"receipt as_of {payload.get('as_of')!r} does not match {as_of}"
        )
    try:
        date.fromisoformat(str(payload["evaluation_session"]))
    except ValueError as exc:
        raise ObservationError("receipt evaluation_session is not ISO date") from exc
    evaluations = payload.get("evaluations")
    if not isinstance(evaluations, list):
        raise ObservationError("receipt evaluations is not a list")
    if not isinstance(payload.get("book_action_required"), bool):
        raise ObservationError("receipt book_action_required is not boolean")
    return payload, hashlib.sha256(raw).hexdigest()


def _summary(receipt: dict[str, Any]) -> dict[str, Any]:
    fired: list[str] = []
    no_signal: list[str] = []
    skipped: dict[str, str] = {}
    seen: set[str] = set()
    for position, row in enumerate(receipt["evaluations"], start=1):
        if not isinstance(row, dict) or set(row) != _EVALUATION_FIELDS:
            raise ObservationError(
                f"receipt evaluation {position} has unexpected schema"
            )
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            raise ObservationError(f"receipt evaluation {position} has no symbol")
        symbol = symbol.strip().upper()
        if symbol in seen:
            raise ObservationError(f"receipt repeats symbol {symbol}")
        seen.add(symbol)
        status = row.get("status")
        if status == "FIRED":
            if row.get("reason") is not None:
                raise ObservationError(f"FIRED row {symbol} has a skip reason")
            fired.append(symbol)
        elif status == "NO_SIGNAL":
            if row.get("reason") is not None:
                raise ObservationError(f"NO_SIGNAL row {symbol} has a skip reason")
            no_signal.append(symbol)
        elif status == "SKIPPED":
            reason = row.get("reason")
            if not isinstance(reason, str) or not reason:
                raise ObservationError(f"SKIPPED row {symbol} has no reason")
            skipped[symbol] = reason
        else:
            raise ObservationError(f"row {symbol} has unknown status {status!r}")
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
                raise ObservationError(
                    f"book header {reader.fieldnames} != {BOOK_FIELDS}"
                )
            count = 0
            for line_number, row in enumerate(reader, start=2):
                if not (row["id"] or "").strip():
                    raise ObservationError(f"book line {line_number} has no id")
                if not (row["exit_date"] or "").strip():
                    count += 1
    except ObservationError:
        raise
    except (OSError, KeyError, TypeError, csv.Error) as exc:
        raise ObservationError(
            f"book unreadable: {type(exc).__name__}: {exc}"
        ) from exc
    return count


def build_observation(
    *, as_of: str, receipt_path: Path, book_path: Path
) -> dict[str, Any]:
    receipt, receipt_hash = _load_receipt(Path(receipt_path), as_of=as_of)
    return {
        "as_of": as_of,
        "receipt": _receipt_reference(as_of),
        "receipt_sha256": receipt_hash,
        "summary": _summary(receipt),
        "open_positions": count_open_positions(Path(book_path)),
    }


def _validate_existing(value: Any, *, line_number: int) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _OBSERVATION_FIELDS:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: observation schema mismatch"
        )
    as_of = value.get("as_of")
    if not isinstance(as_of, str):
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid as_of"
        )
    try:
        date.fromisoformat(as_of)
    except ValueError as exc:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid as_of"
        ) from exc
    receipt = value.get("receipt")
    if not isinstance(receipt, str) or not receipt:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid receipt path"
        )
    receipt_hash = value.get("receipt_sha256")
    if not isinstance(receipt_hash, str) or re.fullmatch(
        r"[0-9a-f]{64}", receipt_hash
    ) is None:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid receipt_sha256"
        )
    summary = value.get("summary")
    if not isinstance(summary, dict) or set(summary) != _SUMMARY_FIELDS:
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid summary"
        )
    if not isinstance(summary["fired"], list) or not isinstance(
        summary["no_signal"], list
    ) or not isinstance(summary["skipped"], dict):
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid summary values"
        )
    open_positions = value.get("open_positions")
    if (
        not isinstance(open_positions, int)
        or isinstance(open_positions, bool)
        or open_positions < 0
    ):
        raise ObservationLogMalformed(
            f"MALFORMED line {line_number}: invalid open_positions"
        )
    return value


def append_observation(record: dict[str, Any], path: Path) -> bool:
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
                    raise ObservationLogMalformed(
                        f"MALFORMED line {line_number}: {exc}"
                    ) from exc
                existing = _validate_existing(parsed, line_number=line_number)
                existing_as_of = existing["as_of"]
                if existing_as_of in existing_by_date:
                    raise ObservationLogMalformed(
                        f"MALFORMED duplicate as_of {existing_as_of}"
                    )
                existing_by_date[existing_as_of] = existing

            prior = existing_by_date.get(record["as_of"])
            if prior is not None:
                if prior["receipt_sha256"] == record["receipt_sha256"]:
                    return False
                raise ObservationConflict(
                    f"CONFLICT as_of {record['as_of']} has receipt hash "
                    f"{prior['receipt_sha256']}, not {record['receipt_sha256']}"
                )

            encoded = json.dumps(
                record, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
            handle.seek(0, os.SEEK_END)
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            return True
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def main(
    argv: list[str] | None = None,
    *,
    receipt_path: Path | None = None,
    observations_path: Path = OBSERVATIONS_PATH,
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
    try:
        record = build_observation(
            as_of=args.as_of, receipt_path=source, book_path=Path(book_path)
        )
        appended = append_observation(record, Path(observations_path))
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
        print(
            f"H10 OBSERVE already recorded as_of={args.as_of} "
            "with the same receipt hash; no-op"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Load licensed ownership research as immutable display-only context.

This module deliberately has no scoring or ranking integration. The input may
annotate research views, but it cannot change a registered hypothesis, verdict,
candidate order, FIRE authority, paper book, or order path.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType

OWNERSHIP_CONTEXT_UNIVERSE = (
    "CRWV",
    "TEM",
    "PLTR",
    "NOW",
    "SMCI",
    "NVDA",
    "AMD",
    "AVGO",
    "IREN",
    "USAR",
    "ET",
    "VST",
    "CEG",
    "MSFT",
    "AMZN",
    "NBIS",
    "AMAT",
    "CLSK",
)
SCHEMA_VERSION = "ownership-context/v1"
FORBIDDEN_FIELDS = frozenset({"score", "ranking_score", "rank", "recommendation", "action"})
LANES = ("insider", "fund", "institutional")


class OwnershipContextValidationError(ValueError):
    """Raised when an ownership-context artifact violates its boundary."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class OwnershipContextSnapshot:
    """Validated immutable ownership context keyed by symbol."""

    as_of: date
    retrieved_at: datetime
    symbols: tuple[str, ...]
    rows: Mapping[str, Mapping[str, object]]
    limitations: tuple[str, ...]


def _read_payload(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OwnershipContextValidationError("input_unreadable", str(exc)) from exc
    if not isinstance(payload, dict):
        raise OwnershipContextValidationError("schema_invalid", "root must be an object")
    return payload


def _reject_forbidden_fields(value: object, *, location: str = "root") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_FIELDS:
                raise OwnershipContextValidationError(
                    "forbidden_field", f"{location}.{key} is not allowed"
                )
            _reject_forbidden_fields(nested, location=f"{location}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_forbidden_fields(nested, location=f"{location}[{index}]")


def _parse_retrieved_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise OwnershipContextValidationError(
            "retrieved_at_invalid", "retrieved_at must be an ISO timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise OwnershipContextValidationError("retrieved_at_invalid", str(exc)) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise OwnershipContextValidationError(
            "timezone_required", "retrieved_at must include a UTC offset"
        )
    return parsed


def _parse_as_of(value: object) -> date:
    if not isinstance(value, str):
        raise OwnershipContextValidationError("as_of_invalid", "as_of must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OwnershipContextValidationError("as_of_invalid", str(exc)) from exc


def _validate_rows(payload: Mapping[str, object]) -> list[dict[str, object]]:
    raw_rows = payload.get("symbols")
    if not isinstance(raw_rows, list) or not all(isinstance(row, dict) for row in raw_rows):
        raise OwnershipContextValidationError(
            "symbols_invalid", "symbols must be a list of objects"
        )
    rows: list[dict[str, object]] = raw_rows
    row_symbols = tuple(row.get("symbol") for row in rows)
    if row_symbols != OWNERSHIP_CONTEXT_UNIVERSE:
        raise OwnershipContextValidationError(
            "symbol_rows_mismatch", "symbol rows must match exact universe order"
        )
    for row in rows:
        symbol = str(row["symbol"])
        for lane_name in LANES:
            lane = row.get(lane_name)
            if not isinstance(lane, dict):
                raise OwnershipContextValidationError(
                    "lane_missing", f"{symbol}.{lane_name} must be an object"
                )
            if not isinstance(lane.get("coverage"), str):
                raise OwnershipContextValidationError(
                    "coverage_missing", f"{symbol}.{lane_name}.coverage is required"
                )
            if not isinstance(lane.get("events"), list):
                raise OwnershipContextValidationError(
                    "events_invalid", f"{symbol}.{lane_name}.events must be a list"
                )
    return rows


def _deep_freeze(value: object) -> object:
    if isinstance(value, dict):
        return _freeze_mapping(value)
    if isinstance(value, list):
        return tuple(_deep_freeze(nested) for nested in value)
    return value


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({key: _deep_freeze(nested) for key, nested in value.items()})


def load_ownership_context(path: Path) -> OwnershipContextSnapshot:
    """Validate and load a sanitized ownership-context projection.

    Failures are loud and deterministic. There is intentionally no fallback to
    an empty or success-shaped context because missing licensed data must remain
    distinguishable from an observed zero.
    """

    payload = _read_payload(path)
    _reject_forbidden_fields(payload)
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise OwnershipContextValidationError("schema_unsupported", f"expected {SCHEMA_VERSION}")
    if payload.get("display_only") is not True or payload.get("verdict_eligible") is not False:
        raise OwnershipContextValidationError(
            "display_only_required", "display_only=true and verdict_eligible=false are required"
        )
    raw_universe = payload.get("universe")
    if raw_universe != list(OWNERSHIP_CONTEXT_UNIVERSE):
        raise OwnershipContextValidationError(
            "universe_mismatch", "artifact must match the authorized 18-symbol universe"
        )
    retrieved_at = _parse_retrieved_at(payload.get("retrieved_at"))
    as_of = _parse_as_of(payload.get("as_of"))
    if as_of > retrieved_at.date():
        raise OwnershipContextValidationError(
            "as_of_after_retrieval", "as_of cannot be later than retrieved_at"
        )
    rows = _validate_rows(payload)
    raw_limitations = payload.get("limitations")
    if not isinstance(raw_limitations, list) or not all(
        isinstance(item, str) for item in raw_limitations
    ):
        raise OwnershipContextValidationError(
            "limitations_invalid", "limitations must be a list of strings"
        )
    frozen_rows: Mapping[str, Mapping[str, object]] = MappingProxyType(
        {str(row["symbol"]): _freeze_mapping(row) for row in rows}
    )
    return OwnershipContextSnapshot(
        as_of=as_of,
        retrieved_at=retrieved_at,
        symbols=OWNERSHIP_CONTEXT_UNIVERSE,
        rows=frozen_rows,
        limitations=tuple(raw_limitations),
    )

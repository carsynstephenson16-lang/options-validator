"""Read the frozen H7 forward cohort from the immutable seq-0 registration.

Read-only.  This is the sanctioned source for the names eligible for live
window entry evaluation; callers must not fall back to the mutable 15-name
operational scope when no activation record is available.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE


class CohortUnavailableError(RuntimeError):
    """The store cannot supply a valid seq-0 window-registration cohort."""


@dataclass(frozen=True)
class RegisteredCohort:
    """Names and exclusion reasons committed when the window was activated."""

    included: tuple[str, ...]
    excluded: dict[str, str]
    event_id: str
    decision_window_start: str | None = None
    decision_window_end: str | None = None


def _unavailable(base_dir: Path, detail: str) -> CohortUnavailableError:
    return CohortUnavailableError(
        f"no usable activation cohort in {base_dir}: {detail}; refusing to "
        "evaluate entries -- check this is the canonical activated checkout"
    )


def load_registered_cohort(base_dir: Path = REAL_FORWARD_STORE) -> RegisteredCohort:
    """Load the cohort frozen in the ledger's first event.

    The loader validates the serialised universe shape before returning it so a
    corrupted or non-canonical store cannot expand entry evaluation by falling
    back to the current operational watchlist.
    """
    base = Path(base_dir)
    try:
        result = ledger.verify(base)
        if result.empty:
            raise _unavailable(base, "ledger is VALID EMPTY")
        records = ledger.read_events(base)
    except CohortUnavailableError:
        raise
    except (ledger.LedgerError, OSError) as exc:
        raise _unavailable(
            base, f"ledger verification failed ({type(exc).__name__}: {exc})"
        ) from exc

    if not records:
        raise _unavailable(base, "ledger changed to empty while reading")
    first = records[0]
    if first.event_type != "window_registration":
        raise _unavailable(base, f"seq-0 event is {first.event_type!r}, not window_registration")

    try:
        universe = first.payload["universe"]
        included_raw = universe["included"]
        excluded_raw = universe["excluded"]
        window = first.payload["window"]
        window_start = window["start_decision_session"]
        window_end = window["final_decision_session"]
    except (KeyError, TypeError) as exc:
        raise _unavailable(base, f"seq-0 registration payload is malformed ({exc})") from exc

    try:
        start_day = date.fromisoformat(window_start)
        end_day = date.fromisoformat(window_end)
    except (TypeError, ValueError) as exc:
        raise _unavailable(base, "seq-0 decision-window bounds are invalid") from exc
    if (
        start_day.isoformat() != window_start
        or end_day.isoformat() != window_end
        or end_day < start_day
    ):
        raise _unavailable(base, "seq-0 decision-window bounds are invalid")

    if not isinstance(included_raw, list) or not included_raw:
        raise _unavailable(base, "seq-0 included cohort is missing or empty")
    if any(not isinstance(symbol, str) or not symbol for symbol in included_raw) or len(
        set(included_raw)
    ) != len(included_raw):
        raise _unavailable(base, "seq-0 included cohort has invalid or duplicate names")

    if not isinstance(excluded_raw, list):
        raise _unavailable(base, "seq-0 excluded cohort is not a list")
    excluded: dict[str, str] = {}
    for row in excluded_raw:
        if not isinstance(row, dict):
            raise _unavailable(base, "seq-0 excluded cohort has a non-object entry")
        symbol = row.get("symbol")
        reason = row.get("reason")
        if (
            not isinstance(symbol, str)
            or not symbol
            or not isinstance(reason, str)
            or not reason
            or symbol in excluded
        ):
            raise _unavailable(base, "seq-0 excluded cohort has invalid entries")
        excluded[symbol] = reason

    included = tuple(included_raw)
    if set(included) & set(excluded):
        raise _unavailable(base, "seq-0 cohort includes and excludes the same name")
    return RegisteredCohort(
        included=included,
        excluded=excluded,
        event_id=first.event_id,
        decision_window_start=window_start,
        decision_window_end=window_end,
    )

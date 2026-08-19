"""Read-only per-symbol evidence gathered from existing hypothesis receipts.

The dashboard is a consumer of this module, never an authority source.  The
gatherer does not run watchers, derive signals, write receipts, or fall back
from an unavailable immutable H7 cohort to a mutable config universe.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import config
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    RegisteredCohort,
    load_registered_cohort,
)
from options_researcher.h7_scope import scope_identity, watch_universe


@dataclass(frozen=True, slots=True)
class EvidenceState:
    """One verbatim state read from a receipt."""

    label: str
    state: str


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """One existing source artifact and its semantic date."""

    kind: str
    path: str
    date: str


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    """Display-only evidence for one hypothesis family and one symbol."""

    family: str
    membership: str
    family_state: str
    symbol_states: tuple[EvidenceState, ...]
    evaluation_session: str | None
    run_date: str | None
    sources: tuple[EvidenceSource, ...]
    detail: str
    expected_daily: bool
    descriptive_only: bool


@dataclass(frozen=True, slots=True)
class SymbolEvidence:
    """All hypothesis rows plus the separate descriptive intraday row."""

    symbol: str
    hypotheses: tuple[EvidenceRow, ...]
    intraday: EvidenceRow


@dataclass(frozen=True, slots=True)
class RawStateCount:
    """One exact raw receipt state and its family-level count."""

    state: str
    count: int


@dataclass(frozen=True, slots=True)
class FamilyEvidence:
    """Read-only rollup of already-gathered rows for one hypothesis family."""

    family: str
    ritual_state: str
    ritual_detail: str
    raw_state_counts: tuple[RawStateCount, ...]
    evaluation_session: str | None
    run_date: str | None
    sources: tuple[EvidenceSource, ...]
    registered_window_end: str | None
    registered_window_metadata: str | None


CohortLoader = Callable[[Path], RegisteredCohort]

_HYPOTHESIS_ORDER = ("H5", "H6", "H7", "H8", "H10a", "H10b")
_H7_LANES = ("lane_a", "lane_b", "lane_c")
_RITUAL_STATES = frozenset({"CAPTURED", "NO_SIGNAL", "REFUSED", "MISSING"})
_H6_ENTRY_STATES = frozenset({"ELIGIBLE", "BLOCKED"})
_H6_TIMING_STATES = frozenset({"UNKNOWN", "POST_REPORT", "PRE_REPORT_BANNED", "IVR_GATED"})
_H8_ENTRY_STATES = frozenset({"ENTRY-OK", "BLOCKED", "OUT_OF_WINDOW"})
_H8_WINDOW_STATES = frozenset({"UNKNOWN", "OUT_OF_WINDOW", "ESTIMATED_BLOCKED", "IN_WINDOW"})
_H10_STATES = frozenset({"FIRED", "NO_SIGNAL", "SKIPPED"})
_H10_SKIP_REASONS = frozenset(
    {
        "DATA",
        "ADMISSION",
        "NO_CONTRACT",
        "SOURCE_HEALTH",
        "EARNINGS",
        "BOOK",
        "CAP",
        "SCHWAB_CAPTURE",
    }
)
_H7_GATES = frozenset({"CLEAR", "BANNED", "UNKNOWN"})
_H7_LANE_STATES = frozenset(
    {
        "EXCLUDED",
        "POSITION-OPEN",
        "EARNINGS-UNKNOWN",
        "EARNINGS-BAN",
        "WATCH-ONLY",
        "QUIET",
        "BASKET-CAP",
        "BUDGET-SPENT",
        "NO-EXECUTABLE",
        "ENTRY-OK",
    }
)
_H7_DISPLACED_RE = re.compile(
    r"DISPLACED\((?:lane_a_takes_underlying|underlying_open|"
    r"underlying_taken|h7c_basket_cap|sleeve_exhausted)\)"
)
_INTRADAY_STATES = frozenset({"ok", "unavailable"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_H5_NAME = re.compile(r"entry_watch_(\d{4}-\d{2}-\d{2})\.txt")
_PLAIN_DATE_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})\.json")
_H10_NAME = re.compile(r"h10_watch_(\d{4}-\d{2}-\d{2})\.json")
_RITUAL_NAME = re.compile(r"capture_receipt_(\d{4}-\d{2}-\d{2})\.json")


@dataclass(frozen=True, slots=True)
class _Artifact:
    path: Path | None
    path_date: str | None
    payload: Mapping[str, object] | None
    error: str | None


@dataclass(frozen=True, slots=True)
class _RitualSummary:
    state: str
    detail: str
    evaluation_session: str | None
    run_date: str | None
    sources: tuple[EvidenceSource, ...]


def _canonical_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed.isoformat() == value else None


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _source(
    root: Path, artifact: _Artifact, *, kind: str, date_value: str | None = None
) -> tuple[EvidenceSource, ...]:
    if artifact.path is None or artifact.path_date is None:
        return ()
    return (
        EvidenceSource(
            kind=kind,
            path=_relative(root, artifact.path),
            date=date_value or artifact.path_date,
        ),
    )


def _dedupe_sources(
    *groups: tuple[EvidenceSource, ...],
) -> tuple[EvidenceSource, ...]:
    seen: set[tuple[str, str, str]] = set()
    result: list[EvidenceSource] = []
    for source in (item for group in groups for item in group):
        key = (source.kind, source.path, source.date)
        if key not in seen:
            seen.add(key)
            result.append(source)
    return tuple(result)


def _dated_candidates(
    directory: Path,
    pattern: str,
    name_pattern: re.Pattern[str],
) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for path in directory.glob(pattern):
        if not path.is_file():
            continue
        match = name_pattern.fullmatch(path.name)
        if match is None:
            continue
        iso = _canonical_date(match.group(1))
        if iso is not None:
            candidates.append((iso, path))
    return candidates


def _latest_json(
    directory: Path,
    pattern: str,
    name_pattern: re.Pattern[str] = _PLAIN_DATE_NAME,
) -> _Artifact:
    candidates = _dated_candidates(directory, pattern, name_pattern)
    if not candidates:
        return _Artifact(None, None, None, "receipt missing")
    path_date, path = max(candidates, key=lambda item: (item[0], item[1].name))
    try:
        raw = path.read_text(encoding="utf-8")
        loaded = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _Artifact(
            path,
            path_date,
            None,
            f"{type(exc).__name__}: {exc}",
        )
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        return _Artifact(path, path_date, None, "JSON root is not an object")
    return _Artifact(path, path_date, loaded, None)


def _latest_text(
    directory: Path,
    pattern: str,
    name_pattern: re.Pattern[str],
) -> tuple[_Artifact, str | None]:
    candidates = _dated_candidates(directory, pattern, name_pattern)
    if not candidates:
        return _Artifact(None, None, None, "receipt missing"), None
    path_date, path = max(candidates, key=lambda item: (item[0], item[1].name))
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return (
            _Artifact(
                path,
                path_date,
                None,
                f"{type(exc).__name__}: {exc}",
            ),
            None,
        )
    if not text.strip():
        return _Artifact(path, path_date, None, "receipt is empty"), None
    return _Artifact(path, path_date, {}, None), text


def _ritual_summary(root: Path, artifact: _Artifact, family: str) -> _RitualSummary:
    source = _source(root, artifact, kind="ritual")
    payload = artifact.payload
    if payload is None:
        return _RitualSummary(
            state="UNKNOWN",
            detail="ritual summary unavailable",
            evaluation_session=artifact.path_date,
            run_date=None,
            sources=source,
        )
    as_of = _canonical_date(payload.get("as_of"))
    run_date = _canonical_date(payload.get("run_date"))
    hypotheses = payload.get("hypotheses")
    if as_of != artifact.path_date or run_date is None or not isinstance(hypotheses, Mapping):
        return _RitualSummary(
            "UNKNOWN",
            "ritual summary malformed",
            artifact.path_date,
            None,
            source,
        )
    item = hypotheses.get(family)
    if not isinstance(item, Mapping):
        return _RitualSummary(
            "UNKNOWN",
            f"ritual summary omits {family}",
            as_of,
            run_date,
            source,
        )
    state = item.get("status")
    detail = item.get("detail")
    if not isinstance(state, str) or state not in _RITUAL_STATES or not isinstance(detail, str):
        return _RitualSummary(
            "UNKNOWN",
            f"ritual summary has malformed {family} state",
            as_of,
            run_date,
            source,
        )
    return _RitualSummary(state, detail, as_of, run_date, source)


def _family_state(
    summary: _RitualSummary, evaluation_session: str | None
) -> tuple[str, str | None]:
    if evaluation_session is None:
        return summary.state, summary.run_date
    if summary.evaluation_session == evaluation_session:
        return summary.state, summary.run_date
    return "UNKNOWN", None


def _detail(raw_detail: str, summary: _RitualSummary) -> str:
    parts = []
    if raw_detail:
        parts.append(f"raw: {raw_detail}")
    if summary.detail:
        parts.append(f"ritual: {summary.detail}")
    return "; ".join(parts)


def _unknown_raw(
    *,
    family: str,
    membership: str,
    summary: _RitualSummary,
    artifact: _Artifact,
    root: Path,
    source_kind: str,
    detail: str,
    run_date: str | None = None,
) -> EvidenceRow:
    family_state, aligned_run_date = _family_state(summary, artifact.path_date)
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=family_state,
        symbol_states=(EvidenceState("raw", "UNKNOWN"),),
        evaluation_session=artifact.path_date,
        run_date=run_date or aligned_run_date,
        sources=_dedupe_sources(
            _source(root, artifact, kind=source_kind),
            summary.sources,
        ),
        detail=detail,
        expected_daily=True,
        descriptive_only=False,
    )


def _missing_raw(
    *,
    family: str,
    membership: str,
    summary: _RitualSummary,
) -> EvidenceRow:
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=summary.state,
        symbol_states=(EvidenceState("raw", "UNKNOWN"),),
        evaluation_session=None,
        run_date=summary.run_date,
        sources=summary.sources,
        detail=f"NO RECEIPT {family} — expected daily",
        expected_daily=True,
        descriptive_only=False,
    )


def _not_tracked(family: str) -> EvidenceRow:
    return EvidenceRow(
        family=family,
        membership="not tracked",
        family_state="NOT TRACKED",
        symbol_states=(EvidenceState("scope", "NOT TRACKED"),),
        evaluation_session=None,
        run_date=None,
        sources=(),
        detail="NOT TRACKED",
        expected_daily=True,
        descriptive_only=False,
    )


def _object_rows(value: object) -> list[Mapping[str, object]] | None:
    if not isinstance(value, list):
        return None
    rows: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping) or not all(isinstance(key, str) for key in item):
            return None
        rows.append(item)
    return rows


def _one_symbol_row(rows: list[Mapping[str, object]], symbol: str) -> Mapping[str, object] | None:
    matches = [row for row in rows if row.get("symbol") == symbol]
    return matches[0] if len(matches) == 1 else None


def _h5_row(
    symbol: str,
    root: Path,
    artifact: _Artifact,
    text: str | None,
    summary: _RitualSummary,
) -> EvidenceRow:
    family = "H5"
    if symbol not in config.H5_ENTRY_TRIGGERS:
        return _not_tracked(family)
    membership = "H5 registered entry trigger"
    if artifact.path is None:
        return _missing_raw(family=family, membership=membership, summary=summary)
    if text is None or artifact.path_date is None:
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="entry_watch",
            detail="UNKNOWN — malformed newest H5 receipt",
        )
    match = re.search(
        rf"(?m)^{re.escape(symbol)}:\s+(WAIT|FIRE)\b(.*)$",
        text,
    )
    if match is None:
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="entry_watch",
            detail="UNKNOWN — newest H5 receipt omits tracked symbol",
        )
    row_detail = match.group(2).strip()
    as_of = re.search(r"\(as of (\d{4}-\d{2}-\d{2})\)", row_detail)
    if as_of is None or _canonical_date(as_of.group(1)) != artifact.path_date:
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="entry_watch",
            detail="UNKNOWN — newest H5 receipt has mismatched session",
        )
    family_state, run_date = _family_state(summary, artifact.path_date)
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=family_state,
        symbol_states=(EvidenceState("entry", match.group(1)),),
        evaluation_session=artifact.path_date,
        run_date=run_date,
        sources=_dedupe_sources(
            _source(root, artifact, kind="entry_watch"),
            summary.sources,
        ),
        detail=_detail(row_detail, summary),
        expected_daily=True,
        descriptive_only=False,
    )


def _h6_row(
    symbol: str,
    root: Path,
    artifact: _Artifact,
    summary: _RitualSummary,
) -> EvidenceRow:
    family = "H6"
    if symbol not in config.H6_NAMES:
        return _not_tracked(family)
    membership = "H6 entry scope"
    if artifact.path is None:
        return _missing_raw(family=family, membership=membership, summary=summary)
    payload = artifact.payload
    snapshot = payload.get("snapshot") if payload is not None else None
    evaluation_session = (
        _canonical_date(snapshot.get("evaluation_session"))
        if isinstance(snapshot, Mapping)
        else None
    )
    entries = _object_rows(snapshot.get("entries")) if isinstance(snapshot, Mapping) else None
    snapshot_errors = snapshot.get("errors") if isinstance(snapshot, Mapping) else None
    row = _one_symbol_row(entries, symbol) if entries is not None else None
    timing = row.get("timing") if row is not None else None
    status = row.get("status") if row is not None else None
    row_evaluation_session = (
        _canonical_date(row.get("evaluation_session")) if row is not None else None
    )
    timing_state = timing.get("state") if isinstance(timing, Mapping) else None
    timing_reason = timing.get("reason") if isinstance(timing, Mapping) else None
    reasons = row.get("reasons") if row is not None else None
    valid_reasons = isinstance(reasons, list) and all(isinstance(reason, str) for reason in reasons)
    valid_status_reasons = (status == "ELIGIBLE" and reasons == []) or (
        status == "BLOCKED" and isinstance(reasons, list) and bool(reasons)
    )
    if (
        payload is None
        or payload.get("schema") != "h6_exact_session_watch_receipt_v1"
        or evaluation_session != artifact.path_date
        or not isinstance(snapshot, Mapping)
        or snapshot.get("mode") != "FORWARD_PAPER_ONLY"
        or snapshot.get("live_orders") is not False
        or not isinstance(snapshot_errors, list)
        or not all(isinstance(error, str) for error in snapshot_errors)
        or row_evaluation_session != evaluation_session
        or not isinstance(status, str)
        or status not in _H6_ENTRY_STATES
        or not isinstance(timing_state, str)
        or timing_state not in _H6_TIMING_STATES
        or not isinstance(timing_reason, str)
        or not timing_reason
        or not valid_reasons
        or not valid_status_reasons
    ):
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="entry_watch",
            detail="UNKNOWN — malformed newest H6 entry receipt",
        )
    family_state, run_date = _family_state(summary, evaluation_session)
    assert isinstance(reasons, list)
    assert all(isinstance(reason, str) for reason in reasons)
    raw_detail = "; ".join(reasons)
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=family_state,
        symbol_states=(
            EvidenceState("entry", status),
            EvidenceState("timing", timing_state),
        ),
        evaluation_session=evaluation_session,
        run_date=run_date,
        sources=_dedupe_sources(
            _source(
                root,
                artifact,
                kind="entry_watch",
                date_value=evaluation_session,
            ),
            summary.sources,
        ),
        detail=_detail(raw_detail, summary),
        expected_daily=True,
        descriptive_only=False,
    )


def _h8_row(
    symbol: str,
    root: Path,
    artifact: _Artifact,
    summary: _RitualSummary,
) -> EvidenceRow:
    family = "H8"
    if symbol not in config.H8_NAMES:
        return _not_tracked(family)
    membership = "H8 registered scope"
    if artifact.path is None:
        return _missing_raw(family=family, membership=membership, summary=summary)
    payload = artifact.payload
    evaluation_session = (
        _canonical_date(payload.get("evaluation_session")) if payload is not None else None
    )
    entries = _object_rows(payload.get("entries")) if payload is not None else None
    errors = payload.get("errors") if payload is not None else None
    row = _one_symbol_row(entries, symbol) if entries is not None else None
    window = row.get("window") if row is not None else None
    status = row.get("status") if row is not None else None
    row_evaluation_session = (
        _canonical_date(row.get("evaluation_session")) if row is not None else None
    )
    window_state = window.get("state") if isinstance(window, Mapping) else None
    window_reason = window.get("reason") if isinstance(window, Mapping) else None
    reasons = row.get("reasons") if row is not None else None
    valid_reasons = isinstance(reasons, list) and all(isinstance(reason, str) for reason in reasons)
    valid_state_pair = (
        (status == "ENTRY-OK" and window_state == "IN_WINDOW")
        or (status == "OUT_OF_WINDOW" and window_state == "OUT_OF_WINDOW")
        or (status == "BLOCKED" and window_state in {"UNKNOWN", "ESTIMATED_BLOCKED", "IN_WINDOW"})
    )
    valid_status_reasons = (status in {"ENTRY-OK", "OUT_OF_WINDOW"} and reasons == []) or (
        status == "BLOCKED" and isinstance(reasons, list) and bool(reasons)
    )
    if (
        evaluation_session != artifact.path_date
        or payload is None
        or payload.get("mode") != "FORWARD_PAPER_ONLY"
        or payload.get("orders_enabled") is not False
        or not isinstance(errors, list)
        or not all(isinstance(error, str) for error in errors)
        or row_evaluation_session != evaluation_session
        or not isinstance(status, str)
        or status not in _H8_ENTRY_STATES
        or not isinstance(window_state, str)
        or window_state not in _H8_WINDOW_STATES
        or not isinstance(window_reason, str)
        or not window_reason
        or not valid_state_pair
        or not valid_reasons
        or not valid_status_reasons
    ):
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="entry_watch",
            detail="UNKNOWN — malformed newest H8 entry receipt",
        )
    family_state, run_date = _family_state(summary, evaluation_session)
    assert isinstance(reasons, list)
    assert all(isinstance(item, str) for item in reasons)
    raw_details = list(reasons)
    raw_details.append(window_reason)
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=family_state,
        symbol_states=(
            EvidenceState("entry", status),
            EvidenceState("window", window_state),
        ),
        evaluation_session=evaluation_session,
        run_date=run_date,
        sources=_dedupe_sources(
            _source(
                root,
                artifact,
                kind="entry_watch",
                date_value=evaluation_session,
            ),
            summary.sources,
        ),
        detail=_detail("; ".join(raw_details), summary),
        expected_daily=True,
        descriptive_only=False,
    )


def _h10_row(
    symbol: str,
    family: str,
    root: Path,
    artifact: _Artifact,
    summary: _RitualSummary,
) -> EvidenceRow:
    if symbol not in config.H7_WATCHLIST:
        return _not_tracked(family)
    membership = f"{family} registered scope"
    if artifact.path is None:
        return _missing_raw(family=family, membership=membership, summary=summary)
    payload = artifact.payload
    evaluation_session = (
        _canonical_date(payload.get("evaluation_session")) if payload is not None else None
    )
    run_date = _canonical_date(payload.get("as_of")) if payload is not None else None
    evaluations = _object_rows(payload.get("evaluations")) if payload is not None else None
    top_level_action = payload.get("book_action_required") if payload is not None else None
    valid_action_aggregate = (
        type(top_level_action) is bool
        and evaluations is not None
        and all(type(item.get("book_action_required")) is bool for item in evaluations)
        and top_level_action
        == any(item.get("book_action_required") is True for item in evaluations)
    )
    row = _one_symbol_row(evaluations, symbol) if evaluations is not None else None
    status = row.get("status") if row is not None else None
    reason = row.get("reason") if row is not None else None
    signals = row.get("signals") if row is not None else None
    h10a_status = row.get("h10a_status") if row is not None else None
    row_action = row.get("book_action_required") if row is not None else None
    signal = signals.get(family) if isinstance(signals, Mapping) else object()
    valid_signals = (
        isinstance(signals, Mapping)
        and set(signals) == {"H10a", "H10b"}
        and all(value is None or isinstance(value, bool) for value in signals.values())
    )
    valid_status_fields = (
        (
            status == "FIRED"
            and reason is None
            and row_action is True
            and isinstance(signals, Mapping)
            and any(value is True for value in signals.values())
        )
        or (
            status == "NO_SIGNAL"
            and reason is None
            and row_action is False
            and isinstance(signals, Mapping)
            and signals.get(family) is False
        )
        or (
            status == "SKIPPED"
            and isinstance(reason, str)
            and reason in _H10_SKIP_REASONS
            and row_action is False
        )
    )
    valid_h10a_adjudication = family == "H10a" and h10a_status == "ADJUDICATED" and signal is None
    if (
        payload is None
        or run_date != artifact.path_date
        or evaluation_session is None
        or not valid_action_aggregate
        or not isinstance(status, str)
        or status not in _H10_STATES
        or not valid_signals
        or not (valid_status_fields or valid_h10a_adjudication)
    ):
        return _unknown_raw(
            family=family,
            membership=membership,
            summary=summary,
            artifact=artifact,
            root=root,
            source_kind="watcher",
            detail=f"UNKNOWN — malformed newest {family} receipt",
            run_date=artifact.path_date,
        )
    family_state, ritual_run_date = _family_state(summary, evaluation_session)
    if valid_h10a_adjudication:
        return EvidenceRow(
            family=family,
            membership=membership,
            family_state=family_state,
            symbol_states=(EvidenceState("watcher", "ADJUDICATED"),),
            evaluation_session=evaluation_session,
            run_date=run_date or ritual_run_date,
            sources=_dedupe_sources(
                _source(
                    root,
                    artifact,
                    kind="watcher",
                    date_value=evaluation_session,
                ),
                summary.sources,
            ),
            detail=_detail("H10a adjudicated (H10A_RESULT)", summary),
            expected_daily=True,
            descriptive_only=False,
        )
    signal_text = json.dumps(signal)
    raw_detail = f"reason={reason}" if isinstance(reason, str) else ""
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=family_state,
        symbol_states=(
            EvidenceState("watcher", status),
            EvidenceState("signal", signal_text),
        ),
        evaluation_session=evaluation_session,
        run_date=run_date or ritual_run_date,
        sources=_dedupe_sources(
            _source(
                root,
                artifact,
                kind="watcher",
                date_value=evaluation_session,
            ),
            summary.sources,
        ),
        detail=_detail(raw_detail, summary),
        expected_daily=True,
        descriptive_only=False,
    )


def _h7_unavailable(detail: str) -> EvidenceRow:
    return EvidenceRow(
        family="H7",
        membership="BUILD-ONLY — H7 cohort unavailable",
        family_state="UNKNOWN",
        symbol_states=(
            EvidenceState("source", "UNKNOWN"),
            *(EvidenceState(lane, "UNKNOWN") for lane in _H7_LANES),
        ),
        evaluation_session=None,
        run_date=None,
        sources=(),
        detail=f"H7 UNKNOWN — BUILD-ONLY cohort unavailable: {detail}",
        expected_daily=True,
        descriptive_only=False,
    )


def _h7_row(
    symbol: str,
    root: Path,
    cohort: RegisteredCohort,
    source_artifact: _Artifact,
    watcher_artifact: _Artifact,
    summary: _RitualSummary,
) -> EvidenceRow:
    if symbol in cohort.included:
        membership = "H7 registered cohort"
    elif symbol in cohort.excluded:
        membership = f"H7 excluded {cohort.excluded[symbol]}"
    else:
        return _not_tracked("H7")

    sources = _dedupe_sources(
        _source(root, source_artifact, kind="source_health"),
        _source(root, watcher_artifact, kind="watcher"),
        summary.sources,
    )
    if source_artifact.path is None or watcher_artifact.path is None:
        return EvidenceRow(
            family="H7",
            membership=membership,
            family_state=summary.state,
            symbol_states=(
                EvidenceState("source", "UNKNOWN"),
                *(EvidenceState(lane, "UNKNOWN") for lane in _H7_LANES),
            ),
            evaluation_session=watcher_artifact.path_date,
            run_date=summary.run_date,
            sources=sources,
            detail="NO RECEIPT H7 — expected daily",
            expected_daily=True,
            descriptive_only=False,
        )

    source_payload = source_artifact.payload
    source_date = (
        _canonical_date(source_payload.get("evaluation_session"))
        if source_payload is not None
        else None
    )
    symbol_map = source_payload.get("symbols") if source_payload is not None else None
    source_row = symbol_map.get(symbol) if isinstance(symbol_map, Mapping) else None
    gate = source_row.get("gate") if isinstance(source_row, Mapping) else None
    source_valid = (
        source_payload is not None
        and source_payload.get("receipt_schema") == "h7-receipt/v1"
        and source_payload.get("receipt_type") == "source_health"
        and source_date == source_artifact.path_date
        and isinstance(gate, str)
        and gate in _H7_GATES
        and isinstance(source_row, Mapping)
        and source_row.get("symbol") == symbol
    )

    watcher_payload = watcher_artifact.payload
    watcher_date = (
        _canonical_date(watcher_payload.get("evaluation_session"))
        if watcher_payload is not None
        else None
    )
    requested_run_date = (
        _canonical_date(watcher_payload.get("requested_run_date"))
        if watcher_payload is not None
        else None
    )
    linked_source_hash = (
        watcher_payload.get("source_health_receipt_hash") if watcher_payload is not None else None
    )
    source_receipt_hash = source_payload.get("receipt_hash") if source_payload is not None else None
    watcher_rows = (
        _object_rows(watcher_payload.get("rows")) if watcher_payload is not None else None
    )
    watcher_errors = watcher_payload.get("errors") if watcher_payload is not None else None
    matching_rows = (
        [row for row in watcher_rows if row.get("symbol") == symbol]
        if watcher_rows is not None
        else []
    )
    lane_map: dict[str, str] = {}
    lane_rows_valid = True
    for row in matching_rows:
        lane = row.get("lane")
        state = row.get("state")
        if (
            not isinstance(lane, str)
            or lane not in _H7_LANES
            or not isinstance(state, str)
            or (state not in _H7_LANE_STATES and _H7_DISPLACED_RE.fullmatch(state) is None)
            or lane in lane_map
        ):
            lane_rows_valid = False
            break
        lane_map[lane] = state
    watcher_valid = (
        watcher_payload is not None
        and watcher_payload.get("receipt_schema") == "h7-receipt/v1"
        and watcher_payload.get("receipt_type") == "watcher_decision"
        and watcher_date == watcher_artifact.path_date
        and watcher_date == source_date
        and isinstance(source_receipt_hash, str)
        and _SHA256_RE.fullmatch(source_receipt_hash) is not None
        and linked_source_hash == source_receipt_hash
        and watcher_payload.get("scope") == scope_identity()
        and source_payload is not None
        and source_payload.get("scope") == scope_identity()
        and requested_run_date is not None
        and watcher_rows is not None
        and isinstance(watcher_errors, list)
        and all(isinstance(error, str) for error in watcher_errors)
        and lane_rows_valid
    )
    if not source_valid or not watcher_valid:
        family_state, run_date = _family_state(summary, watcher_artifact.path_date)
        return EvidenceRow(
            family="H7",
            membership=membership,
            family_state=family_state,
            symbol_states=(
                EvidenceState("source", "UNKNOWN"),
                *(EvidenceState(lane, "UNKNOWN") for lane in _H7_LANES),
            ),
            evaluation_session=watcher_artifact.path_date,
            run_date=requested_run_date or run_date,
            sources=sources,
            detail="UNKNOWN — malformed newest H7 receipt set",
            expected_daily=True,
            descriptive_only=False,
        )

    family_state, ritual_run_date = _family_state(summary, watcher_date)
    assert isinstance(gate, str)
    source_reason = source_row.get("gate_reason") if isinstance(source_row, Mapping) else None
    raw_detail = source_reason if isinstance(source_reason, str) else ""
    return EvidenceRow(
        family="H7",
        membership=membership,
        family_state=family_state,
        symbol_states=(
            EvidenceState("source", gate),
            *(EvidenceState(lane, lane_map.get(lane, "UNKNOWN")) for lane in _H7_LANES),
        ),
        evaluation_session=watcher_date,
        run_date=requested_run_date or ritual_run_date,
        sources=sources,
        detail=_detail(raw_detail, summary),
        expected_daily=True,
        descriptive_only=False,
    )


def _intraday_key(path: Path) -> tuple[str, str] | None:
    day = _canonical_date(path.parent.name)
    scheduled = config.INTRADAY_CAPTURE_TIMES.get(path.stem)
    if day is None or not isinstance(scheduled, str):
        return None
    try:
        datetime.strptime(scheduled, "%H:%M")
    except ValueError:
        return None
    return day, scheduled


def _latest_intraday(root: Path) -> _Artifact:
    candidates: list[tuple[tuple[str, str], Path]] = []
    directory = root / "reports" / "intraday_capture"
    for path in directory.glob("*/*.json"):
        if not path.is_file():
            continue
        key = _intraday_key(path)
        if key is not None:
            candidates.append((key, path))
    if not candidates:
        return _Artifact(None, None, None, "receipt missing")
    (day, _), path = max(candidates, key=lambda item: (item[0], item[1].name))
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _Artifact(path, day, None, f"{type(exc).__name__}: {exc}")
    if not isinstance(loaded, dict) or not all(isinstance(key, str) for key in loaded):
        return _Artifact(path, day, None, "JSON root is not an object")
    return _Artifact(path, day, loaded, None)


def _intraday_row(
    symbol: str,
    root: Path,
    artifact: _Artifact,
    capture_scope: frozenset[str],
) -> EvidenceRow:
    family = "INTRADAY"
    if symbol not in capture_scope:
        return EvidenceRow(
            family=family,
            membership="not tracked",
            family_state="NOT TRACKED",
            symbol_states=(EvidenceState("scope", "NOT TRACKED"),),
            evaluation_session=None,
            run_date=None,
            sources=(),
            detail="NOT TRACKED",
            expected_daily=False,
            descriptive_only=True,
        )
    membership = "descriptive-only capture"
    if artifact.path is None:
        return EvidenceRow(
            family=family,
            membership=membership,
            family_state="UNKNOWN",
            symbol_states=(EvidenceState("capture", "UNKNOWN"),),
            evaluation_session=None,
            run_date=None,
            sources=(),
            detail="NO RECEIPT INTRADAY",
            expected_daily=False,
            descriptive_only=True,
        )
    payload = artifact.payload
    names = payload.get("names") if payload is not None else None
    row = names.get(symbol) if isinstance(names, Mapping) else None
    row_symbol = row.get("symbol") if isinstance(row, Mapping) else None
    status = row.get("status") if isinstance(row, Mapping) else None
    universe = payload.get("universe") if payload is not None else None
    captured_at = payload.get("captured_at_et") if payload is not None else None
    session_tag = payload.get("session_tag") if payload is not None else None
    try:
        captured = datetime.fromisoformat(captured_at) if isinstance(captured_at, str) else None
    except ValueError:
        captured = None
    valid = (
        payload is not None
        and payload.get("receipt_kind") == "intraday_capture/v1"
        and session_tag == artifact.path.stem
        and payload.get("scheduled_et") == config.INTRADAY_CAPTURE_TIMES.get(artifact.path.stem)
        and isinstance(universe, list)
        and all(isinstance(item, str) for item in universe)
        and universe == list(watch_universe())
        and isinstance(names, Mapping)
        and set(names) == set(universe)
        and row_symbol == symbol
        and captured is not None
        and captured.tzinfo is not None
        and captured.date().isoformat() == artifact.path_date
        and isinstance(status, str)
        and status in _INTRADAY_STATES
    )
    source = _source(root, artifact, kind="intraday")
    if not valid:
        return EvidenceRow(
            family=family,
            membership=membership,
            family_state="UNKNOWN",
            symbol_states=(EvidenceState("capture", "UNKNOWN"),),
            evaluation_session=None,
            run_date=artifact.path_date,
            sources=source,
            detail="UNKNOWN — malformed newest intraday receipt",
            expected_daily=False,
            descriptive_only=True,
        )
    note = row.get("note") if isinstance(row, Mapping) else None
    iv_label = row.get("iv_label") if isinstance(row, Mapping) else None
    assert isinstance(status, str)
    raw_detail = note if isinstance(note, str) else (iv_label if isinstance(iv_label, str) else "")
    return EvidenceRow(
        family=family,
        membership=membership,
        family_state=status,
        symbol_states=(EvidenceState("capture", status),),
        evaluation_session=None,
        run_date=artifact.path_date,
        sources=source,
        detail=raw_detail,
        expected_daily=False,
        descriptive_only=True,
    )


def gather_hypothesis_evidence(
    symbols: Iterable[str],
    *,
    root: Path,
    cohort_loader: CohortLoader = load_registered_cohort,
) -> dict[str, SymbolEvidence]:
    """Gather immutable typed evidence rows for each requested symbol.

    Receipt selection is newest-by-semantic path date.  Once selected, a
    malformed newest artifact produces ``UNKNOWN``; it never silently borrows
    an older valid receipt.
    """

    normalized = tuple(symbol.upper() for symbol in symbols)
    if any(not symbol for symbol in normalized):
        raise ValueError("symbols must be non-empty")
    if len(set(normalized)) != len(normalized):
        raise ValueError("symbols must be unique after uppercasing")
    root = Path(root)

    ritual_artifact = _latest_json(
        root / "reports" / "ritual",
        "capture_receipt_*.json",
        _RITUAL_NAME,
    )
    summaries = {
        family: _ritual_summary(
            root,
            ritual_artifact,
            "H10" if family.startswith("H10") else family,
        )
        for family in _HYPOTHESIS_ORDER
    }
    h5_artifact, h5_text = _latest_text(
        root / "reports" / "h5",
        "entry_watch_*.txt",
        _H5_NAME,
    )
    h6_artifact = _latest_json(root / "reports" / "h6_forward", "*.json")
    h8_artifact = _latest_json(root / "reports" / "h8_forward", "*.json")
    h10_artifact = _latest_json(
        root / "reports" / "h10" / "receipts",
        "h10_watch_*.json",
        _H10_NAME,
    )
    intraday_artifact = _latest_intraday(root)

    cohort: RegisteredCohort | None
    cohort_error: str | None = None
    try:
        cohort = cohort_loader(root / "ledger" / "h7_forward")
    except CohortUnavailableError as exc:
        cohort = None
        cohort_error = str(exc)

    scope_id = str(scope_identity()["scope_id"])
    h7_base = root / "reports" / "h7_receipts" / scope_id
    source_artifact = _latest_json(h7_base / "source_health", "*.json")
    watcher_artifact = _latest_json(h7_base / "watcher", "*.json")
    capture_scope = frozenset(watch_universe())

    gathered: dict[str, SymbolEvidence] = {}
    for symbol in normalized:
        h7 = (
            _h7_row(
                symbol,
                root,
                cohort,
                source_artifact,
                watcher_artifact,
                summaries["H7"],
            )
            if cohort is not None
            else _h7_unavailable(cohort_error or "unknown cohort failure")
        )
        rows = (
            _h5_row(
                symbol,
                root,
                h5_artifact,
                h5_text,
                summaries["H5"],
            ),
            _h6_row(
                symbol,
                root,
                h6_artifact,
                summaries["H6"],
            ),
            h7,
            _h8_row(
                symbol,
                root,
                h8_artifact,
                summaries["H8"],
            ),
            _h10_row(
                symbol,
                "H10a",
                root,
                h10_artifact,
                summaries["H10a"],
            ),
            _h10_row(
                symbol,
                "H10b",
                root,
                h10_artifact,
                summaries["H10b"],
            ),
        )
        gathered[symbol] = SymbolEvidence(
            symbol=symbol,
            hypotheses=rows,
            intraday=_intraday_row(
                symbol,
                root,
                intraday_artifact,
                capture_scope,
            ),
        )
    return gathered


def summarize_hypothesis_evidence(
    evidence_by_symbol: Mapping[str, SymbolEvidence],
) -> tuple[FamilyEvidence, ...]:
    """Roll up gathered receipt rows without reading artifacts or running watchers.

    The tracker is descriptive presentation data only.  It deliberately uses
    the rows provided by :func:`gather_hypothesis_evidence` (or injected test
    fixtures) and therefore cannot select a newer receipt, mutate any ledger,
    or infer position and runtime facts that those rows do not contain.
    """
    rows_by_family: dict[str, list[EvidenceRow]] = {family: [] for family in _HYPOTHESIS_ORDER}
    for symbol in sorted(evidence_by_symbol):
        evidence = evidence_by_symbol[symbol]
        for row in evidence.hypotheses:
            if row.family in rows_by_family:
                rows_by_family[row.family].append(row)

    summaries: list[FamilyEvidence] = []
    for family in _HYPOTHESIS_ORDER:
        rows = rows_by_family[family]
        tracked_rows = [row for row in rows if row.membership != "not tracked"]
        ritual_states = {row.family_state for row in tracked_rows}
        ritual_details = {row.detail for row in tracked_rows}
        ritual_state = (
            next(iter(ritual_states))
            if len(ritual_states) == 1
            and ritual_states <= (_RITUAL_STATES | {"UNKNOWN", "NOT TRACKED"})
            else "UNKNOWN"
        )
        ritual_detail = (
            next(iter(ritual_details))
            if len(ritual_details) == 1
            else ("NO RECEIPT" if not tracked_rows else "ritual detail disagrees")
        )

        state_counts: dict[str, int] = {}
        for row in rows:
            for state in row.symbol_states:
                state_counts[state.state] = state_counts.get(state.state, 0) + 1
        raw_state_counts = (
            tuple(RawStateCount(state, state_counts[state]) for state in sorted(state_counts))
            if state_counts
            else (RawStateCount("NO RECEIPT", 0),)
        )

        evaluation_values = {row.evaluation_session for row in tracked_rows}
        run_values = {row.run_date for row in tracked_rows}
        evaluation_session = (
            next(iter(evaluation_values))
            if len(evaluation_values) == 1 and None not in evaluation_values
            else None
        )
        run_date = (
            next(iter(run_values)) if len(run_values) == 1 and None not in run_values else None
        )

        sources: list[EvidenceSource] = []
        seen_paths: set[str] = set()
        for row in rows:
            for source in row.sources:
                if source.path not in seen_paths:
                    seen_paths.add(source.path)
                    sources.append(source)

        configured_window = (
            getattr(config, f"{family.upper()}_WINDOW_END", None)
            if family in {"H10a", "H10b"}
            else None
        )
        registered_window_end = _canonical_date(configured_window)
        summaries.append(
            FamilyEvidence(
                family=family,
                ritual_state=ritual_state,
                ritual_detail=ritual_detail,
                raw_state_counts=raw_state_counts,
                evaluation_session=evaluation_session,
                run_date=run_date,
                sources=tuple(sources),
                registered_window_end=registered_window_end,
                registered_window_metadata=(
                    "registered-window metadata" if registered_window_end is not None else None
                ),
            )
        )
    return tuple(summaries)

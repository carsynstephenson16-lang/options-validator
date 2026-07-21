"""Validated, entry-only H7 forward sessions.

The registered decision date and the completed source-data date are separate
facts.  A Day T+1 operator decision may use T's immutable receipts, while its
window membership remains keyed to the registered decision date.  This module
never places orders and deliberately exposes no exit or scoring authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from data.cache_runner import session_close_utc
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    load_registered_cohort,
)
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    RealStoreSession,
    TransitionResult,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from options_researcher.h7_watch import evaluation_session, validate_data_gate_receipt
from research.receipts import load_receipt


class SessionRefused(RuntimeError):
    """The activation, receipt chain, cohort, or decision window is invalid."""


@dataclass(frozen=True)
class SessionEvidence:
    """Typed ledger results for one immutable receipt chain."""

    source_health: TransitionResult
    data_gate: TransitionResult
    symbol_source_health: TransitionResult


def _iso_session(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise SessionRefused(f"{field} must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SessionRefused(f"{field} must be canonical YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SessionRefused(f"{field} must be canonical YYYY-MM-DD")
    return value


def _refuse(detail: str, exc: Exception | None = None) -> SessionRefused:
    if exc is None:
        return SessionRefused(detail)
    return SessionRefused(f"{detail}: {type(exc).__name__}: {exc}")


def _source_symbol_map(source: dict, names: list[str]) -> dict[str, dict]:
    symbols = source.get("symbols")
    if not isinstance(symbols, dict) or set(symbols) != set(names):
        raise SessionRefused("source-health receipt does not cover the full official scope")
    if any(not isinstance(symbols[name], dict) for name in names):
        raise SessionRefused("source-health receipt has malformed symbol evidence")
    return symbols


def open_real_session(
    *,
    data_gate_receipt_path: Path,
    decision_session: str,
    source_evaluation_session: str | None = None,
    symbol: str | None = None,
    base_dir: Path = REAL_FORWARD_STORE,
) -> RealStoreSession:
    """Open a real entry session from one validated immutable receipt chain.

    ``decision_session`` is the date governed by the frozen forward window.
    ``source_evaluation_session`` is the completed cache/receipt date; omitting
    it uses the watcher-compatible preceding completed session.
    """
    decision = _iso_session(decision_session, "decision_session")
    source_evaluation = (
        evaluation_session(date.fromisoformat(decision)).isoformat()
        if source_evaluation_session is None
        else _iso_session(source_evaluation_session, "source_evaluation_session")
    )
    base = Path(base_dir)
    try:
        cohort = load_registered_cohort(base_dir=base)
    except CohortUnavailableError as exc:
        raise _refuse("activation cohort is unavailable", exc) from exc
    start = cohort.decision_window_start
    end = cohort.decision_window_end
    if start is None or end is None:
        raise SessionRefused("activation registration has no decision-window bounds")
    if not start <= decision <= end:
        raise SessionRefused(
            f"decision session {decision} is outside the registered window [{start}, {end}]"
        )

    names = watch_universe()
    gate_path = Path(data_gate_receipt_path)
    try:
        gate = validate_data_gate_receipt(
            gate_path, evaluation_session=source_evaluation, names=names
        )
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("data-gate receipt is missing, stale, or unlinked", exc) from exc
    if gate.get("whole_universe_verdict") != "GO":
        raise SessionRefused("data-gate receipt is not GO")
    source_path_value = gate.get("source_health_receipt_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        raise SessionRefused("data-gate receipt has no source-health receipt path")
    source_path = Path(source_path_value)
    try:
        source = load_receipt(source_path, expected_type="source_health")
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("linked source-health receipt is unavailable", exc) from exc
    symbols = _source_symbol_map(source, names)
    unhealthy = sorted(name for name in names if symbols[name].get("healthy") is not True)
    if unhealthy:
        raise SessionRefused(f"source-health receipt has unhealthy official names: {unhealthy}")

    if symbol is not None:
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise SessionRefused("target symbol must be canonical uppercase")
        if symbol not in cohort.included:
            raise SessionRefused(f"{symbol} is outside the frozen registered entry cohort")
        state = symbols[symbol]
        if state.get("gate") != "CLEAR" or state.get("healthy") is not True:
            raise SessionRefused(
                f"{symbol} is entry-banned by source health (gate={state.get('gate')!r})"
            )

    return RealStoreSession(
        base_dir=base,
        activation_event_id=cohort.event_id,
        decision_session=decision,
        evaluation_session=source_evaluation,
        data_gate_receipt_path=gate_path,
        source_health_receipt_path=source_path,
        data_gate_receipt_hash=str(gate["receipt_hash"]),
        source_health_receipt_hash=str(source["receipt_hash"]),
        included_symbols=cohort.included,
    )


def _append_evidence(base: Path, event: dict) -> TransitionResult:
    try:
        result = ledger.append_event(event, base_dir=base)
    except ledger.LedgerError as exc:
        raise _refuse("cannot publish receipt evidence", exc) from exc
    return TransitionResult(
        event_id=event["event_id"],
        event_type=event["event_type"],
        payload=event["payload"],
        appended=result.appended,
    )


def record_session_evidence(session: RealStoreSession, *, symbol: str) -> SessionEvidence:
    """Publish a validated receipt chain as typed, idempotent ledger evidence."""
    if not isinstance(session, RealStoreSession):
        raise SessionRefused("receipt publication requires a RealStoreSession")
    if symbol not in session.included_symbols:
        raise SessionRefused(f"{symbol} is outside the frozen registered cohort")
    names = watch_universe()
    try:
        gate = validate_data_gate_receipt(
            session.data_gate_receipt_path,
            evaluation_session=session.evaluation_session,
            names=names,
        )
        source = load_receipt(session.source_health_receipt_path, expected_type="source_health")
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("session receipt chain changed before publication", exc) from exc
    if (
        gate.get("receipt_hash") != session.data_gate_receipt_hash
        or source.get("receipt_hash") != session.source_health_receipt_hash
    ):
        raise SessionRefused("session receipt identity changed before publication")
    symbols = _source_symbol_map(source, names)
    healthy_symbols = sorted(name for name in names if symbols[name].get("healthy") is True)
    if healthy_symbols != sorted(names):
        raise SessionRefused("source-health receipt is no longer all healthy")
    if symbols[symbol].get("gate") != "CLEAR":
        raise SessionRefused(f"{symbol} is no longer entry-clear in source health")

    scope = scope_identity()
    base = Path(session.base_dir)
    occurred = session_close_utc(session.evaluation_session).isoformat()
    source_id = f"h7:source_health:{session.evaluation_session}"
    source_result = _append_evidence(
        base,
        {
            "schema_version": ledger.SCHEMA_VERSION,
            "event_id": source_id,
            "event_type": "source_health",
            "occurred_at_utc": occurred,
            "evaluation_session": session.evaluation_session,
            "symbol": None,
            "lane": None,
            "causes": [],
            "payload": {
                "scope": scope,
                "healthy_symbols": healthy_symbols,
                "receipt_hash": session.source_health_receipt_hash,
                "receipt_path": str(session.source_health_receipt_path),
            },
        },
    )
    gate_id = f"h7:data_gate:{session.evaluation_session}"
    gate_result = _append_evidence(
        base,
        {
            "schema_version": ledger.SCHEMA_VERSION,
            "event_id": gate_id,
            "event_type": "data_gate",
            "occurred_at_utc": occurred,
            "evaluation_session": session.evaluation_session,
            "symbol": None,
            "lane": None,
            "causes": [source_id],
            "payload": {
                "scope": scope,
                "whole_universe_verdict": "GO",
                "go_count": gate.get("go_count"),
                "no_go_count": gate.get("no_go_count"),
                "receipt_hash": session.data_gate_receipt_hash,
                "receipt_path": str(session.data_gate_receipt_path),
                "source_health_receipt_hash": session.source_health_receipt_hash,
                "source_health_receipt_path": str(session.source_health_receipt_path),
            },
        },
    )
    symbol_id = f"h7:source_health:{session.evaluation_session}:{symbol}"
    symbol_result = _append_evidence(
        base,
        {
            "schema_version": ledger.SCHEMA_VERSION,
            "event_id": symbol_id,
            "event_type": "source_health",
            "occurred_at_utc": occurred,
            "evaluation_session": session.evaluation_session,
            "symbol": symbol,
            "lane": None,
            "causes": [],
            "payload": {
                "scope": scope,
                "healthy": True,
                "gate": "CLEAR",
                "receipt_hash": session.source_health_receipt_hash,
                "receipt_path": str(session.source_health_receipt_path),
            },
        },
    )
    return SessionEvidence(
        source_health=source_result,
        data_gate=gate_result,
        symbol_source_health=symbol_result,
    )

"""Validated, entry-only H7 forward sessions.

The registered decision date and the completed source-data date are separate
facts.  A Day T+1 operator decision may use T's immutable receipts, while its
window membership remains keyed to the registered decision date. This module
never places orders. Its manual entry-fill command hands a newly opened paper
position to the separate receipt-bound exit authority for same-session
observation; it exposes no independent exit or scoring command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from data.cache_runner import session_close_utc
from data.underlying_closes import load_closes_adjusted
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_forward_book as forward_book
from options_researcher import h7_paper_lifecycle as lifecycle
from options_researcher.chains import load_range
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
from research.hashing import canonical_json
from research.receipts import input_file_record, load_receipt

if TYPE_CHECKING:
    from options_researcher.h7_exit_session import ExitRunReport


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


def _session_binding(
    decision_session: str,
    operation: Literal["decision", "fill"],
) -> tuple[str, str]:
    """Return the only source session and run date valid for one operation."""
    if operation == "decision":
        source = evaluation_session(date.fromisoformat(decision_session)).isoformat()
        return source, decision_session
    if operation == "fill":
        source = lifecycle._next_session(decision_session)
        return source, lifecycle._next_session(source)
    raise SessionRefused("operation must be 'decision' or 'fill'")


def _require_session_binding(session: RealStoreSession) -> None:
    lifecycle._require_real_store_session(session)
    if session.operation not in {"decision", "fill"}:
        raise SessionRefused("session operation is invalid")
    expected_source, expected_requested = _session_binding(
        session.decision_session,
        session.operation,
    )
    if session.evaluation_session != expected_source:
        raise SessionRefused(
            f"{session.operation} operation requires source session "
            f"{expected_source}, got {session.evaluation_session}"
        )
    if session.requested_run_date != expected_requested:
        raise SessionRefused(
            f"{session.operation} operation requires requested run date "
            f"{expected_requested}, got {session.requested_run_date}"
        )


def _require_operation(session: RealStoreSession, expected: str) -> None:
    _require_session_binding(session)
    if session.operation != expected:
        raise SessionRefused(f"session operation must be {expected!r}, got {session.operation!r}")


def _require_receipt_run_date(receipt: dict, expected: str, label: str) -> None:
    if receipt.get("requested_run_date") != expected:
        raise SessionRefused(
            f"{label} requested run date does not match session "
            f"({receipt.get('requested_run_date')!r} != {expected!r})"
        )


def open_real_session(
    *,
    data_gate_receipt_path: Path,
    decision_session: str,
    source_evaluation_session: str | None = None,
    symbol: str | None = None,
    base_dir: Path = REAL_FORWARD_STORE,
    operation: Literal["decision", "fill"] = "decision",
) -> RealStoreSession:
    """Open a real entry session from one validated immutable receipt chain.

    ``decision_session`` is the date governed by the frozen forward window.
    ``source_evaluation_session`` is the completed cache/receipt date; omitting
    it uses the watcher-compatible preceding completed session.
    """
    decision = _iso_session(decision_session, "decision_session")
    expected_source, requested_run_date = _session_binding(decision, operation)
    source_evaluation = (
        expected_source
        if source_evaluation_session is None
        else _iso_session(source_evaluation_session, "source_evaluation_session")
    )
    if source_evaluation != expected_source:
        raise SessionRefused(
            f"{operation} operation requires source session "
            f"{expected_source}, got {source_evaluation}"
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
    _require_receipt_run_date(gate, requested_run_date, "data-gate receipt")
    _require_receipt_run_date(source, requested_run_date, "source-health receipt")
    symbols = _source_symbol_map(source, names)
    entry_names = list(cohort.included)
    unhealthy = sorted(
        name for name in entry_names if symbols[name].get("healthy") is not True
    )
    if unhealthy:
        raise SessionRefused(
            f"source-health receipt has unhealthy registered entry names: {unhealthy}"
        )

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

    return lifecycle._issue_real_store_session(
        RealStoreSession(
            base_dir=base,
            activation_event_id=cohort.event_id,
            decision_session=decision,
            evaluation_session=source_evaluation,
            data_gate_receipt_path=gate_path,
            source_health_receipt_path=source_path,
            data_gate_receipt_hash=str(gate["receipt_hash"]),
            source_health_receipt_hash=str(source["receipt_hash"]),
            data_gate_config_hash=str(gate["config_hash"]),
            data_gate_source_hash=str(gate["source_hash"]),
            included_symbols=cohort.included,
            operation=operation,
            requested_run_date=requested_run_date,
        )
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
    _require_session_binding(session)
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
    _require_receipt_run_date(
        gate,
        session.requested_run_date,
        "data-gate receipt",
    )
    _require_receipt_run_date(
        source,
        session.requested_run_date,
        "source-health receipt",
    )
    symbols = _source_symbol_map(source, names)
    healthy_symbols = sorted(
        name for name in session.included_symbols if symbols[name].get("healthy") is True
    )
    if healthy_symbols != sorted(session.included_symbols):
        raise SessionRefused("source-health receipt is no longer healthy for the entry cohort")
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


def _receipt_input(watcher: dict, label: str) -> dict:
    """Return one unchanged watcher input binding, or refuse before a load."""
    inputs = watcher.get("input_files")
    if not isinstance(inputs, dict):
        raise SessionRefused("watcher receipt input bindings are malformed")
    stored = inputs.get(label)
    if not isinstance(stored, dict) or not isinstance(stored.get("path"), str):
        raise SessionRefused(f"watcher receipt has no {label!r} input binding")
    actual = input_file_record(Path(stored["path"]))
    if canonical_json(actual) != canonical_json(stored):
        raise SessionRefused(f"watcher input changed since decision: {label}")
    if actual.get("exists") is not True or not isinstance(actual.get("sha256"), str):
        raise SessionRefused(f"watcher input is unavailable: {label}")
    return actual


def _watcher_receipt_for_session(*, path: Path, session: RealStoreSession) -> dict:
    """Validate the receipt that produced the only eligible entry action."""
    _require_session_binding(session)
    try:
        watcher = load_receipt(Path(path), expected_type="watcher_decision")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise _refuse("watcher decision receipt is unavailable", exc) from exc
    if watcher.get("evaluation_session") != session.evaluation_session:
        raise SessionRefused("watcher decision receipt has the wrong source session")
    _require_receipt_run_date(
        watcher,
        session.requested_run_date,
        "watcher receipt",
    )
    if watcher.get("scope") != scope_identity():
        raise SessionRefused("watcher decision receipt does not cover the official scope")
    if watcher.get("data_gate_receipt_hash") != session.data_gate_receipt_hash:
        raise SessionRefused("watcher receipt is not bound to this data-gate receipt")
    if watcher.get("source_health_receipt_hash") != session.source_health_receipt_hash:
        raise SessionRefused("watcher receipt is not bound to this source-health receipt")
    if watcher.get("config_hash") != session.data_gate_config_hash:
        raise SessionRefused("watcher receipt config identity differs from data gate")
    if watcher.get("source_hash") != session.data_gate_source_hash:
        raise SessionRefused("watcher receipt source identity differs from data gate")
    inputs = watcher.get("input_files")
    if not isinstance(inputs, dict):
        raise SessionRefused("watcher decision receipt input bindings are malformed")
    for label in sorted(inputs):
        _receipt_input(watcher, label)
    return watcher


def _watcher_candidates(watcher: dict, session: RealStoreSession) -> list[dict]:
    """Recover only executable, receipt-recorded actions for the frozen cohort."""
    rows = watcher.get("rows")
    if not isinstance(rows, list):
        raise SessionRefused("watcher decision receipt rows are malformed")
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise SessionRefused("watcher decision receipt has a malformed row")
        if row.get("actionable") is not True:
            continue
        symbol = row.get("symbol")
        lane_key = row.get("lane")
        raw_action = row.get("action")
        if (
            not isinstance(symbol, str)
            or symbol not in session.included_symbols
            or not isinstance(lane_key, str)
            or not lane_key.startswith("lane_")
            or lane_key[-1] not in ledger.LANES
            or row.get("state") != "ENTRY-OK"
            or not isinstance(raw_action, str)
        ):
            raise SessionRefused("watcher receipt has an invalid actionable row")
        try:
            action = json.loads(raw_action)
        except json.JSONDecodeError as exc:
            raise _refuse("watcher receipt action is not JSON", exc) from exc
        lane = lane_key[-1]
        if not isinstance(action, dict) or action.get("lane") != lane:
            raise SessionRefused("watcher receipt action does not match its lane")
        key = (symbol, lane)
        if key in seen:
            raise SessionRefused("watcher receipt has duplicate actionable rows")
        seen.add(key)
        candidates.append(
            {
                "symbol": symbol,
                "lane": lane,
                "session": session.evaluation_session,
                "action": action,
            }
        )
    return candidates


def _receipt_identity(watcher: dict, label: str) -> str:
    record = _receipt_input(watcher, label)
    return f"sha256:{record['sha256']}"


def _load_bound_chain(watcher: dict, *, symbol: str, session: str):
    """Read the exact chain file named in a validated watcher receipt."""
    _receipt_input(watcher, f"chain:{symbol}")
    chains = load_range(symbol, session, session, allow_oos=True)
    chain = chains.get(session)
    if chain is None:
        raise SessionRefused(f"chain cache no longer supplies {symbol} for {session}")
    _receipt_input(watcher, f"chain:{symbol}")
    return chain


def _load_bound_close(watcher: dict, *, symbol: str, session: str) -> float:
    """Read the receipt-named adjusted close only when it is exact-session."""
    _receipt_input(watcher, f"close:{symbol}")
    closes = load_closes_adjusted(symbol, session, session, allow_oos=True)
    if closes.empty or str(closes.index[-1])[:10] != session:
        raise SessionRefused(f"close cache no longer supplies {symbol} for {session}")
    _receipt_input(watcher, f"close:{symbol}")
    try:
        value = float(closes.iloc[-1])
    except (TypeError, ValueError) as exc:
        raise _refuse("receipt-bound adjusted close is malformed", exc) from exc
    if value <= 0:
        raise SessionRefused("receipt-bound adjusted close is not positive")
    return value


def propose_entry(
    *, session: RealStoreSession, symbol: str, lane: str, watcher_receipt_path: Path
) -> TransitionResult:
    """Append the one receipt-derived entry intent for a board-approved action."""
    _require_operation(session, "decision")
    if lane not in ledger.LANES:
        raise SessionRefused("lane must be a, b, or c")
    if symbol not in session.included_symbols:
        raise SessionRefused(f"{symbol} is outside the frozen registered cohort")
    watcher = _watcher_receipt_for_session(path=watcher_receipt_path, session=session)
    candidates = _watcher_candidates(watcher, session)
    selected = [item for item in candidates if item["symbol"] == symbol and item["lane"] == lane]
    if len(selected) != 1:
        raise SessionRefused(
            f"watcher receipt has no unique ENTRY-OK action for {symbol} lane {lane}"
        )
    evidence = record_session_evidence(session, symbol=symbol)
    board = forward_book.record_board_resolution(
        base_dir=session,
        evaluation_session=session.evaluation_session,
        candidates=candidates,
        source_health_id=evidence.source_health.event_id,
        data_gate_id=evidence.data_gate.event_id,
    )
    chain = _load_bound_chain(watcher, symbol=symbol, session=session.evaluation_session)
    return lifecycle.record_entry_intent(
        base_dir=session,
        symbol=symbol,
        action=selected[0]["action"],
        decision_chain=chain,
        decision_session=session.evaluation_session,
        source_health_id=evidence.source_health.event_id,
        data_gate_id=evidence.data_gate.event_id,
        board_resolution_id=board.event_id,
        chain_identity=_receipt_identity(watcher, f"chain:{symbol}"),
        closes_identity=_receipt_identity(watcher, f"close:{symbol}"),
    )


def fill_entry(
    *,
    session: RealStoreSession,
    entry_intent_id: str,
    symbol: str,
    watcher_receipt_path: Path,
) -> TransitionResult:
    """Append a T+1 paper fill using the exact receipt-bound cache inputs."""
    _require_operation(session, "fill")
    if symbol not in session.included_symbols:
        raise SessionRefused(f"{symbol} is outside the frozen registered cohort")
    watcher = _watcher_receipt_for_session(path=watcher_receipt_path, session=session)
    evidence = record_session_evidence(session, symbol=symbol)
    chain = _load_bound_chain(watcher, symbol=symbol, session=session.evaluation_session)
    close = _load_bound_close(watcher, symbol=symbol, session=session.evaluation_session)
    return lifecycle.process_entry_fill(
        base_dir=session,
        entry_intent_id=entry_intent_id,
        fill_session=session.evaluation_session,
        chain=chain,
        source_health_id=evidence.symbol_source_health.event_id,
        data_gate_id=evidence.data_gate.event_id,
        chain_identity=_receipt_identity(watcher, f"chain:{symbol}"),
        closes_identity=_receipt_identity(watcher, f"close:{symbol}"),
        underlying_close=close,
    )


def fill_entry_and_observe_exit(
    *,
    session: RealStoreSession,
    entry_intent_id: str,
    symbol: str,
    watcher_receipt_path: Path,
) -> tuple[TransitionResult, ExitRunReport]:
    """Record a manual paper fill, then observe it in that same session."""
    entry = fill_entry(
        session=session,
        entry_intent_id=entry_intent_id,
        symbol=symbol,
        watcher_receipt_path=watcher_receipt_path,
    )
    from options_researcher import h7_exit_session

    try:
        exit_authority = h7_exit_session.open_real_exit_session(
            data_gate_receipt_path=session.data_gate_receipt_path,
            decision_session=session.decision_session,
            source_evaluation_session=session.evaluation_session,
            base_dir=session.base_dir,
        )
        report = h7_exit_session.monitor_real_exits(exit_authority)
    except h7_exit_session.ExitSessionRefused as exc:
        raise SessionRefused(
            "same-session exit observation refused after paper entry fill"
        ) from exc
    return entry, report


def _intent_symbol(intent_id: str) -> str:
    """Read identity only; this does not create an authority bypass."""
    events = ledger.read_events(REAL_FORWARD_STORE)
    for event in events:
        if event.event_id == intent_id and event.event_type == "entry_intent":
            if isinstance(event.symbol, str) and event.symbol:
                return event.symbol
            break
    raise SessionRefused(f"entry intent {intent_id!r} is unavailable")


def _add_session_arguments(parser) -> None:
    parser.add_argument(
        "--data-gate-receipt", required=True, help="immutable GO data-gate receipt path"
    )
    parser.add_argument(
        "--decision-session",
        required=True,
        help="registered operator decision date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--source-evaluation-session",
        default=None,
        help="completed source-data session (YYYY-MM-DD)",
    )


def main(argv: list[str] | None = None) -> int:
    """Owner-operated H7 entry path; it never sends an order or writes exits."""
    import argparse

    parser = argparse.ArgumentParser(
        description="H7 real entry ledger path (paper fills only; never orders)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="validate and display session authority")
    _add_session_arguments(status)
    status.add_argument("--symbol", default=None)
    propose = sub.add_parser("propose", help="record a watcher-derived entry intent")
    _add_session_arguments(propose)
    propose.add_argument("--symbol", required=True)
    propose.add_argument("--lane", required=True, choices=sorted(ledger.LANES))
    propose.add_argument(
        "--watcher-receipt", required=True, help="immutable watcher decision receipt path"
    )
    approve = sub.add_parser("approve", help="record one manual owner approval")
    _add_session_arguments(approve)
    approve.add_argument("--intent-id", required=True)
    approve.add_argument(
        "--owner",
        required=True,
        help="must be the authorized owner acknowledgement: carsyn",
    )
    fill = sub.add_parser("fill", help="record the planned paper entry fill")
    _add_session_arguments(fill)
    fill.add_argument("--intent-id", required=True)
    fill.add_argument(
        "--watcher-receipt",
        required=True,
        help="immutable watcher decision receipt for the fill session",
    )

    try:
        args = parser.parse_args(argv)
        symbol = args.symbol if hasattr(args, "symbol") else None
        session = open_real_session(
            data_gate_receipt_path=Path(args.data_gate_receipt),
            decision_session=args.decision_session,
            source_evaluation_session=args.source_evaluation_session,
            symbol=symbol,
            operation="fill" if args.command == "fill" else "decision",
        )
        if args.command == "status":
            print(
                f"H7 SESSION READY decision={session.decision_session} "
                f"source={session.evaluation_session} activation="
                f"{session.activation_event_id}"
            )
            return 0
        if args.command == "propose":
            result = propose_entry(
                session=session,
                symbol=args.symbol,
                lane=args.lane,
                watcher_receipt_path=Path(args.watcher_receipt),
            )
            print(f"H7 ENTRY INTENT {result.event_id} appended={result.appended}")
            return 0
        if args.command == "approve":
            if args.owner.strip().lower() != "carsyn":
                raise SessionRefused("owner acknowledgement must be exactly 'carsyn'")
            result = lifecycle.record_owner_approval(
                base_dir=session, entry_intent_id=args.intent_id
            )
            print(f"H7 OWNER APPROVAL {result.event_id} appended={result.appended}")
            return 0
        if args.command == "fill":
            intent_symbol = _intent_symbol(args.intent_id)
            # The first no-symbol open above proves the receipt chain. This
            # second door binds that same chain to the intent's frozen symbol.
            session = open_real_session(
                data_gate_receipt_path=Path(args.data_gate_receipt),
                decision_session=args.decision_session,
                source_evaluation_session=args.source_evaluation_session,
                symbol=intent_symbol,
                operation="fill",
            )
            result, exit_report = fill_entry_and_observe_exit(
                session=session,
                entry_intent_id=args.intent_id,
                symbol=intent_symbol,
                watcher_receipt_path=Path(args.watcher_receipt),
            )
            print(f"H7 PAPER FILL {result.event_id} appended={result.appended}")
            for outcome in exit_report.outcomes:
                print(
                    f"H7 SAME-SESSION EXIT {outcome.position_id} "
                    f"{outcome.action} {outcome.detail}"
                )
            if exit_report.failed:
                print(
                    "H7 PAPER FILL EXIT MONITOR REFUSED -- "
                    "paper entry requires operator attention"
                )
                return 2
            return 0
    except (
        SessionRefused,
        lifecycle.LifecycleError,
        forward_book.BookValidationError,
        ledger.LedgerError,
        OSError,
        ValueError,
    ) as exc:
        print(f"H7 SESSION REFUSED -- {type(exc).__name__}: {exc}")
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Receipt-bound real-paper H7 exit authority (BUILD-ONLY; INACTIVE).

This module creates and publishes only mechanical exit-management authority.
It never authorizes an entry, scores the window, fetches data, or places an
order.  Activation remains gated on the SPEC-required independent review and
separate owner PASS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from data.cache_runner import session_close_utc, trading_days
from data.underlying_closes import adjusted_from_raw
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_paper_lifecycle as lifecycle
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    load_registered_cohort,
)
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ExitSourceHealthState,
    RealExitSession,
    ReceiptInputBinding,
    TransitionResult,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    canonical_json,
    config_hash,
    diagnostic_source_hash,
)
from research.receipts import (
    changed_input_files,
    input_file_record,
    load_receipt,
)


class ExitSessionRefused(RuntimeError):
    """The real-exit capability or its immutable evidence failed closed."""


@dataclass(frozen=True)
class ExitEvidence:
    source_health: TransitionResult
    data_gate: TransitionResult
    symbol_source_health: TransitionResult | None


@dataclass(frozen=True)
class ExitRunOutcome:
    """One owner-visible result from a multi-position exit pass."""

    position_id: str
    symbol: str
    action: str
    events: tuple[TransitionResult, ...]
    detail: str
    failed: bool = False


@dataclass(frozen=True)
class ExitRunReport:
    """Complete pass result; partial failures remain explicit."""

    outcomes: tuple[ExitRunOutcome, ...]

    @property
    def failed(self) -> bool:
        return any(outcome.failed for outcome in self.outcomes)


def _refuse(detail: str, exc: Exception | None = None) -> ExitSessionRefused:
    if exc is None:
        return ExitSessionRefused(detail)
    return ExitSessionRefused(f"{detail}: {type(exc).__name__}: {exc}")


def _canonical_session(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ExitSessionRefused(f"{field} must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _refuse(f"{field} must be canonical YYYY-MM-DD", exc) from exc
    if parsed.isoformat() != value or trading_days(value, value) != [value]:
        raise ExitSessionRefused(f"{field} must be an XNYS session")
    return value


def _utc_now(now: datetime | None) -> datetime:
    stamp = datetime.now(timezone.utc) if now is None else now
    if (
        not isinstance(stamp, datetime)
        or stamp.tzinfo is None
        or stamp.utcoffset() != timedelta(0)
    ):
        raise ExitSessionRefused("now must be a UTC datetime")
    return stamp


def _symbol_states(source: dict, names: list[str]) -> tuple[ExitSourceHealthState, ...]:
    raw = source.get("symbols")
    if not isinstance(raw, dict) or set(raw) != set(names):
        raise ExitSessionRefused(
            "source-health receipt does not cover the full official scope"
        )
    states: list[ExitSourceHealthState] = []
    for symbol in names:
        row = raw.get(symbol)
        if not isinstance(row, dict):
            raise ExitSessionRefused("source-health symbol evidence is malformed")
        gate = row.get("gate")
        healthy = row.get("healthy")
        next_report = row.get("next_report")
        if gate not in {"CLEAR", "BANNED", "UNKNOWN"} or not isinstance(
            healthy, bool
        ):
            raise ExitSessionRefused(
                f"source-health state for {symbol} is not canonical"
            )
        if next_report is not None:
            try:
                report = date.fromisoformat(str(next_report))
            except ValueError as exc:
                raise _refuse(
                    f"source-health next report for {symbol} is invalid", exc
                ) from exc
            if report.isoformat() != next_report:
                raise ExitSessionRefused(
                    f"source-health next report for {symbol} is not canonical"
                )
        states.append(
            ExitSourceHealthState(
                symbol=symbol,
                gate=gate,
                healthy=healthy,
                next_report=next_report,
            )
        )
    return tuple(states)


def _input_bindings(gate: dict, names: list[str]) -> tuple[ReceiptInputBinding, ...]:
    raw = gate.get("input_files")
    expected_labels = {
        f"{kind}:{symbol}" for symbol in names for kind in ("chain", "close")
    }
    if not isinstance(raw, dict) or set(raw) != expected_labels:
        raise ExitSessionRefused(
            "data-gate receipt does not bind every official chain and close"
        )
    bindings: list[ReceiptInputBinding] = []
    for label in sorted(expected_labels):
        stored = raw.get(label)
        if (
            not isinstance(stored, dict)
            or not isinstance(stored.get("path"), str)
            or not isinstance(stored.get("exists"), bool)
            or (
                stored.get("sha256") is not None
                and not isinstance(stored.get("sha256"), str)
            )
        ):
            raise ExitSessionRefused(f"data-gate input binding {label!r} is malformed")
        actual = input_file_record(Path(stored["path"]))
        if canonical_json(actual) != canonical_json(stored):
            raise ExitSessionRefused(f"data-gate input changed since pass: {label}")
        bindings.append(
            ReceiptInputBinding(
                label=label,
                path=Path(stored["path"]),
                exists=bool(stored["exists"]),
                sha256=stored["sha256"],
            )
        )
    return tuple(bindings)


def _load_receipt_chain(
    *, gate_path: Path, evaluation_session: str
) -> tuple[
    dict,
    dict,
    tuple[ReceiptInputBinding, ...],
    tuple[ExitSourceHealthState, ...],
]:
    names = watch_universe()
    expected_scope = scope_identity(names)
    try:
        gate = load_receipt(Path(gate_path), expected_type="data_gate")
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("data-gate receipt is unavailable", exc) from exc
    if gate.get("evaluation_session") != evaluation_session:
        raise ExitSessionRefused("data-gate receipt has the wrong evaluation session")
    if gate.get("scope") != expected_scope:
        raise ExitSessionRefused("data-gate receipt does not cover the official scope")
    verdict = gate.get("whole_universe_verdict")
    if verdict not in {"GO", "NO_GO"}:
        raise ExitSessionRefused("data-gate receipt verdict is not canonical")
    go_count = gate.get("go_count")
    no_go_count = gate.get("no_go_count")
    if (
        not isinstance(go_count, int)
        or isinstance(go_count, bool)
        or not isinstance(no_go_count, int)
        or isinstance(no_go_count, bool)
        or go_count < 0
        or no_go_count < 0
        or go_count + no_go_count != len(names)
    ):
        raise ExitSessionRefused("data-gate receipt counts do not cover the scope")
    symbols = gate.get("symbols")
    if not isinstance(symbols, dict) or set(symbols) != set(names):
        raise ExitSessionRefused("data-gate receipt symbol results are incomplete")
    if any(
        not isinstance(symbols[name], dict)
        or symbols[name].get("verdict") not in {"GO", "NO_GO"}
        for name in names
    ):
        raise ExitSessionRefused("data-gate receipt symbol results are malformed")
    if verdict == "GO" and (
        go_count != len(names)
        or any(symbols[name].get("verdict") != "GO" for name in names)
    ):
        raise ExitSessionRefused("whole-universe GO disagrees with symbol results")
    if gate.get("config_hash") != config_hash():
        raise ExitSessionRefused("data-gate config identity is stale")
    if gate.get("source_hash") != diagnostic_source_hash():
        raise ExitSessionRefused("data-gate live source identity is stale")
    if gate.get("source_hash_contract") != DIAGNOSTIC_SOURCE_HASH_VERSION:
        raise ExitSessionRefused("data-gate source-hash contract is stale")

    source_path_value = gate.get("source_health_receipt_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        raise ExitSessionRefused("data-gate receipt has no linked source-health path")
    try:
        source = load_receipt(Path(source_path_value), expected_type="source_health")
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("linked source-health receipt is unavailable", exc) from exc
    if (
        source.get("receipt_hash") != gate.get("source_health_receipt_hash")
        or source.get("evaluation_session") != evaluation_session
        or source.get("scope") != expected_scope
    ):
        raise ExitSessionRefused("linked source-health receipt is stale or mismatched")
    if source.get("config_hash") != config_hash():
        raise ExitSessionRefused("source-health config identity is stale")
    if source.get("source_hash") != diagnostic_source_hash():
        raise ExitSessionRefused("source-health live source identity is stale")
    if source.get("source_hash_contract") != DIAGNOSTIC_SOURCE_HASH_VERSION:
        raise ExitSessionRefused("source-health source-hash contract is stale")
    changed_source = changed_input_files(source)
    if changed_source:
        raise ExitSessionRefused(
            f"source-health inputs changed since pass: {changed_source}"
        )
    bindings = _input_bindings(gate, names)
    if verdict == "GO" and any(not binding.exists for binding in bindings):
        raise ExitSessionRefused("whole-universe GO has an unavailable input binding")
    return gate, source, bindings, _symbol_states(source, names)


def _authorized_positions(
    *,
    base: Path,
    included: tuple[str, ...],
    decision_session: str,
    evaluation_session: str,
    window_start: str,
    window_end: str,
) -> tuple[str, ...]:
    positions = lifecycle._replay_positions_at_base(base)
    authorized: list[str] = []
    for position in positions:
        if position.state == "closed" or position.symbol not in included:
            continue
        opening_decision = position.entry_payload.get("decision_session")
        expiration_value = position.entry_payload.get("action", {}).get("expiration")
        if not isinstance(opening_decision, str) or not isinstance(
            expiration_value, str
        ):
            raise ExitSessionRefused("open position has incomplete decision lineage")
        try:
            expiration = date.fromisoformat(expiration_value)
        except ValueError as exc:
            raise _refuse("open position expiration is invalid", exc) from exc
        if not window_start <= opening_decision <= window_end:
            raise ExitSessionRefused("open position did not originate inside the window")
        if evaluation_session < position.entry_session:
            continue
        if date.fromisoformat(decision_session) <= expiration:
            authorized.append(position.position_id)
    if decision_session > window_end and not authorized:
        raise ExitSessionRefused(
            "post-window exit authority has no in-window open-position lineage"
        )
    return tuple(sorted(authorized))


def open_real_exit_session(
    *,
    data_gate_receipt_path: Path,
    decision_session: str,
    source_evaluation_session: str,
    base_dir: Path = REAL_FORWARD_STORE,
    now: datetime | None = None,
) -> RealExitSession:
    """Re-earn one session of receipt-bound mechanical exit authority."""
    decision = _canonical_session(decision_session, "decision_session")
    evaluation = _canonical_session(
        source_evaluation_session, "source_evaluation_session"
    )
    if evaluation > decision:
        raise ExitSessionRefused("source evaluation session follows decision session")
    if _utc_now(now) < session_close_utc(evaluation):
        raise ExitSessionRefused(
            f"source evaluation session {evaluation} has unfinished EOD"
        )
    base = Path(base_dir)
    try:
        verification = ledger.verify(base)
        events = ledger.read_events(base)
        cohort = load_registered_cohort(base_dir=base)
    except (ledger.LedgerError, CohortUnavailableError, OSError) as exc:
        raise _refuse("forward registration or hash chain is unavailable", exc) from exc
    if verification.empty or not events:
        raise ExitSessionRefused("forward ledger has no window registration")
    registration = events[0]
    if registration.event_type != "window_registration":
        raise ExitSessionRefused("forward ledger seq 0 is not window_registration")
    start = cohort.decision_window_start
    end = cohort.decision_window_end
    if start is None or end is None:
        raise ExitSessionRefused("window registration has no decision bounds")
    if decision < start:
        raise ExitSessionRefused("decision session precedes the registered window")
    universe = registration.payload.get("universe")
    scope = scope_identity()
    if (
        not isinstance(universe, dict)
        or universe.get("scope_id") != scope["scope_id"]
        or universe.get("scope_hash") != scope["scope_hash"]
    ):
        raise ExitSessionRefused("registration scope identity is stale")
    authorized = _authorized_positions(
        base=base,
        included=cohort.included,
        decision_session=decision,
        evaluation_session=evaluation,
        window_start=start,
        window_end=end,
    )
    gate, source, bindings, states = _load_receipt_chain(
        gate_path=Path(data_gate_receipt_path), evaluation_session=evaluation
    )
    return RealExitSession(
        base_dir=base,
        activation_event_id=cohort.event_id,
        registration_record_hash=registration.record_hash,
        decision_session=decision,
        evaluation_session=evaluation,
        window_start=start,
        window_end=end,
        scope_id=str(scope["scope_id"]),
        scope_hash=str(scope["scope_hash"]),
        included_symbols=cohort.included,
        authorized_position_ids=authorized,
        data_gate_receipt_path=Path(data_gate_receipt_path),
        source_health_receipt_path=Path(str(gate["source_health_receipt_path"])),
        data_gate_receipt_hash=str(gate["receipt_hash"]),
        source_health_receipt_hash=str(source["receipt_hash"]),
        data_gate_verdict=str(gate["whole_universe_verdict"]),
        data_gate_go_count=int(gate["go_count"]),
        data_gate_no_go_count=int(gate["no_go_count"]),
        data_gate_config_hash=str(gate["config_hash"]),
        data_gate_source_hash=str(gate["source_hash"]),
        source_hash_contract=str(gate["source_hash_contract"]),
        input_bindings=bindings,
        source_health_states=states,
        _authority_token=lifecycle._REAL_EXIT_AUTHORITY_TOKEN,
    )


def _assert_capability(session: RealExitSession) -> None:
    if (
        not isinstance(session, RealExitSession)
        or session._authority_token is not lifecycle._REAL_EXIT_AUTHORITY_TOKEN
    ):
        raise ExitSessionRefused(
            "real exit operation requires factory-issued RealExitSession authority"
        )


def _revalidate(session: RealExitSession) -> tuple[dict, dict]:
    _assert_capability(session)
    try:
        events = ledger.read_events(session.base_dir)
    except (ledger.LedgerError, OSError) as exc:
        raise _refuse("forward hash chain changed", exc) from exc
    if (
        not events
        or events[0].event_id != session.activation_event_id
        or events[0].record_hash != session.registration_record_hash
    ):
        raise ExitSessionRefused("window registration identity changed")
    gate, source, bindings, states = _load_receipt_chain(
        gate_path=session.data_gate_receipt_path,
        evaluation_session=session.evaluation_session,
    )
    if (
        gate.get("receipt_hash") != session.data_gate_receipt_hash
        or source.get("receipt_hash") != session.source_health_receipt_hash
        or bindings != session.input_bindings
        or states != session.source_health_states
    ):
        raise ExitSessionRefused("exit-session receipt identity changed")
    return gate, source


def source_health_state(
    session: RealExitSession, symbol: str
) -> ExitSourceHealthState:
    _assert_capability(session)
    for state in session.source_health_states:
        if state.symbol == symbol:
            return state
    raise ExitSessionRefused(f"{symbol} is outside the official receipt scope")


def _binding(session: RealExitSession, label: str) -> ReceiptInputBinding:
    _assert_capability(session)
    for binding in session.input_bindings:
        if binding.label == label:
            return binding
    raise ExitSessionRefused(f"exit session has no input binding {label!r}")


def binding_identity(session: RealExitSession, label: str) -> str:
    """Return the immutable identity used in lifecycle event payloads."""
    binding = _binding(session, label)
    return (
        f"sha256:{binding.sha256}"
        if binding.sha256 is not None
        else f"missing:{label}"
    )


def _assert_binding_unchanged(binding: ReceiptInputBinding) -> None:
    actual = input_file_record(binding.path)
    expected = {
        "path": str(binding.path),
        "exists": binding.exists,
        "sha256": binding.sha256,
    }
    if canonical_json(actual) != canonical_json(expected):
        raise ExitSessionRefused(
            f"exit input changed during use: {binding.label}"
        )


def load_bound_chain(session: RealExitSession, symbol: str) -> pd.DataFrame:
    """Load only the exact receipt-named chain, with hashes checked twice."""
    _revalidate(session)
    binding = _binding(session, f"chain:{symbol}")
    _assert_binding_unchanged(binding)
    if not binding.exists:
        return pd.DataFrame()
    try:
        chain = pd.read_parquet(binding.path)
    except (OSError, ValueError) as exc:
        raise _refuse(f"receipt-bound chain for {symbol} is unreadable", exc) from exc
    _assert_binding_unchanged(binding)
    return chain


def load_bound_close(session: RealExitSession, symbol: str) -> float | None:
    """Load the exact-session adjusted close from the receipt-named store."""
    _revalidate(session)
    binding = _binding(session, f"close:{symbol}")
    _assert_binding_unchanged(binding)
    if not binding.exists:
        return None
    try:
        frame = pd.read_parquet(binding.path)
    except (OSError, ValueError) as exc:
        raise _refuse(f"receipt-bound close for {symbol} is unreadable", exc) from exc
    if not {"date", "close"}.issubset(frame.columns):
        raise ExitSessionRefused(f"receipt-bound close for {symbol} has wrong schema")
    raw = frame.loc[
        frame["date"].astype(str) <= session.evaluation_session,
        ["date", "close"],
    ].copy()
    raw["date"] = raw["date"].astype(str)
    if raw["date"].duplicated().any():
        raise ExitSessionRefused(f"receipt-bound close for {symbol} has duplicate dates")
    close_values = raw.set_index("date")["close"].sort_index()
    series = pd.Series(
        pd.to_numeric(close_values, errors="coerce"),
        index=close_values.index,
        dtype="float64",
    )
    adjusted = adjusted_from_raw(series, symbol)
    if session.evaluation_session not in adjusted.index:
        _assert_binding_unchanged(binding)
        return None
    try:
        value = float(adjusted.loc[session.evaluation_session])
    except (TypeError, ValueError) as exc:
        raise _refuse(f"receipt-bound close for {symbol} is malformed", exc) from exc
    if not math.isfinite(value) or value <= 0:
        raise ExitSessionRefused(
            f"receipt-bound close for {symbol} is not finite and positive"
        )
    _assert_binding_unchanged(binding)
    return value


def _append_evidence(base: Path, event: dict) -> TransitionResult:
    try:
        result = ledger.append_event(event, base_dir=base)
    except ledger.LedgerError as exc:
        raise _refuse("cannot publish exit receipt evidence", exc) from exc
    return TransitionResult(
        event_id=event["event_id"],
        event_type=event["event_type"],
        payload=event["payload"],
        appended=result.appended,
    )


def record_exit_evidence(
    session: RealExitSession, *, symbol: str, include_symbol: bool
) -> ExitEvidence:
    """Publish faithful GO/NO_GO evidence before an exit transition."""
    gate, _ = _revalidate(session)
    if symbol not in session.included_symbols:
        raise ExitSessionRefused(f"{symbol} is outside the frozen registered cohort")
    state = source_health_state(session, symbol)
    scope = scope_identity()
    occurred = session_close_utc(session.evaluation_session).isoformat()
    source_id = f"h7:source_health:{session.evaluation_session}"
    healthy_symbols = sorted(
        item.symbol
        for item in session.source_health_states
        if item.symbol in session.included_symbols and item.healthy
    )
    source_result = _append_evidence(
        session.base_dir,
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
        session.base_dir,
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
                "whole_universe_verdict": gate["whole_universe_verdict"],
                "go_count": gate["go_count"],
                "no_go_count": gate["no_go_count"],
                "receipt_hash": session.data_gate_receipt_hash,
                "receipt_path": str(session.data_gate_receipt_path),
                "source_health_receipt_hash": session.source_health_receipt_hash,
                "source_health_receipt_path": str(
                    session.source_health_receipt_path
                ),
            },
        },
    )
    symbol_result: TransitionResult | None = None
    if include_symbol:
        symbol_id = f"h7:source_health:{session.evaluation_session}:{symbol}"
        symbol_result = _append_evidence(
            session.base_dir,
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
                    "healthy": state.healthy,
                    "gate": state.gate,
                    "receipt_hash": session.source_health_receipt_hash,
                    "receipt_path": str(session.source_health_receipt_path),
                },
            },
        )
    return ExitEvidence(
        source_health=source_result,
        data_gate=gate_result,
        symbol_source_health=symbol_result,
    )


_RUN_ERRORS = (
    ExitSessionRefused,
    lifecycle.LifecycleError,
    ledger.LedgerError,
    OSError,
    ValueError,
)


def _needs_earnings_evidence(
    session: RealExitSession, position: lifecycle.PaperPosition
) -> bool:
    if position.lane != "c":
        return False
    state = source_health_state(session, position.symbol)
    if state.gate == "UNKNOWN":
        return True
    if state.next_report is None:
        return False
    planned_fill = lifecycle._next_session(session.decision_session)
    after_fill = lifecycle._next_session(planned_fill)
    report = date.fromisoformat(state.next_report)
    return (
        date.fromisoformat(planned_fill) >= report
        or date.fromisoformat(after_fill) >= report
    )


def _evidence_events(evidence: ExitEvidence) -> list[TransitionResult]:
    events = [evidence.source_health, evidence.data_gate]
    if evidence.symbol_source_health is not None:
        events.append(evidence.symbol_source_health)
    return events


def monitor_real_exits(
    session: RealExitSession, *, clock=None
) -> ExitRunReport:
    """Observe every open position authorized by this receipt-bound session."""
    _revalidate(session)
    positions = [
        position
        for position in lifecycle._replay_positions_at_base(session.base_dir)
        if position.position_id in session.authorized_position_ids
        and position.state == "open"
    ]
    outcomes: list[ExitRunOutcome] = []
    for position in positions:
        published: list[TransitionResult] = []
        try:
            include_symbol = _needs_earnings_evidence(session, position)
            evidence = record_exit_evidence(
                session, symbol=position.symbol, include_symbol=include_symbol
            )
            published.extend(_evidence_events(evidence))
            state = source_health_state(session, position.symbol)
            transition = lifecycle.observe_exit(
                base_dir=session,
                position_id=position.position_id,
                evaluation_session=session.evaluation_session,
                chain=load_bound_chain(session, position.symbol),
                data_gate_id=evidence.data_gate.event_id,
                chain_identity=binding_identity(
                    session, f"chain:{position.symbol}"
                ),
                closes_identity=binding_identity(
                    session, f"close:{position.symbol}"
                ),
                underlying_close=load_bound_close(session, position.symbol),
                earnings_gate=state.gate,
                next_report=state.next_report,
                source_health_id=(
                    evidence.symbol_source_health.event_id
                    if evidence.symbol_source_health is not None
                    else None
                ),
                clock=clock,
            )
            if transition is not None:
                published.append(transition)
                detail = transition.event_type
            else:
                detail = "NO_TRIGGER"
            outcomes.append(
                ExitRunOutcome(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    action="monitor",
                    events=tuple(published),
                    detail=detail,
                )
            )
        except _RUN_ERRORS as exc:
            outcomes.append(
                ExitRunOutcome(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    action="monitor",
                    events=tuple(published),
                    detail=f"{type(exc).__name__}: {exc}",
                    failed=True,
                )
            )
    return ExitRunReport(tuple(outcomes))


def _is_due_exit(
    *,
    session: RealExitSession,
    position: lifecycle.PaperPosition,
    events: list[ledger.StoredEvent],
) -> bool:
    if position.exit_intent_id is None:
        return False
    expiration = date.fromisoformat(
        str(position.entry_payload["action"]["expiration"])
    )
    if date.fromisoformat(session.evaluation_session) >= expiration:
        return True
    intent = next(
        (event for event in events if event.event_id == position.exit_intent_id),
        None,
    )
    if intent is None or intent.event_type != "exit_intent":
        raise ExitSessionRefused(
            f"pending position {position.position_id} has no valid exit intent"
        )
    prior_gaps = [
        event
        for event in events
        if event.event_type == "data_gap"
        and event.payload.get("exit_intent_id") == position.exit_intent_id
    ]
    if prior_gaps:
        latest = str(
            prior_gaps[-1].payload.get(
                "decision_session", prior_gaps[-1].evaluation_session
            )
        )
        expected = lifecycle._next_session(latest)
    else:
        expected = str(intent.payload["planned_fill_session"])
    return session.decision_session == expected


def fill_real_exits(session: RealExitSession, *, clock=None) -> ExitRunReport:
    """Process every exit intent due or retryable on this operational session."""
    _revalidate(session)
    events = ledger.read_events(session.base_dir)
    positions = [
        position
        for position in lifecycle._replay_positions_at_base(session.base_dir)
        if position.position_id in session.authorized_position_ids
        and position.state == "pending_exit"
        and _is_due_exit(session=session, position=position, events=events)
    ]
    outcomes: list[ExitRunOutcome] = []
    for position in positions:
        published: list[TransitionResult] = []
        try:
            evidence = record_exit_evidence(
                session, symbol=position.symbol, include_symbol=False
            )
            published.extend(_evidence_events(evidence))
            if position.exit_intent_id is None:
                raise ExitSessionRefused(
                    f"pending position {position.position_id} has no exit intent"
                )
            transition = lifecycle.process_exit_fill(
                base_dir=session,
                exit_intent_id=position.exit_intent_id,
                fill_session=session.evaluation_session,
                chain=load_bound_chain(session, position.symbol),
                data_gate_id=evidence.data_gate.event_id,
                chain_identity=binding_identity(
                    session, f"chain:{position.symbol}"
                ),
                closes_identity=binding_identity(
                    session, f"close:{position.symbol}"
                ),
                underlying_close=load_bound_close(session, position.symbol),
                clock=clock,
            )
            published.append(transition)
            outcomes.append(
                ExitRunOutcome(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    action="fill",
                    events=tuple(published),
                    detail=transition.event_type,
                )
            )
        except _RUN_ERRORS as exc:
            outcomes.append(
                ExitRunOutcome(
                    position_id=position.position_id,
                    symbol=position.symbol,
                    action="fill",
                    events=tuple(published),
                    detail=f"{type(exc).__name__}: {exc}",
                    failed=True,
                )
            )
    return ExitRunReport(tuple(outcomes))


def _print_report(report: ExitRunReport, *, empty_detail: str) -> None:
    if not report.outcomes:
        print(empty_detail)
        return
    for outcome in report.outcomes:
        for event in outcome.events:
            replay = "appended" if event.appended else "replayed"
            print(
                f"H7 EXIT {outcome.position_id} {event.event_type} "
                f"{event.event_id} {replay}"
            )
        if outcome.failed:
            print(
                f"H7 EXIT ERROR {outcome.position_id} {outcome.detail}"
            )
        elif outcome.detail == "NO_TRIGGER":
            print(f"H7 EXIT {outcome.position_id} NO_TRIGGER")


def _add_session_arguments(parser) -> None:
    parser.add_argument(
        "--data-gate-receipt",
        required=True,
        help="immutable full-scope data-gate receipt path",
    )
    parser.add_argument(
        "--decision-session",
        required=True,
        help="operational XNYS decision date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--source-evaluation-session",
        required=True,
        help="completed receipt/cache session (YYYY-MM-DD)",
    )


def main(argv: list[str] | None = None) -> int:
    """Owner-visible paper-exit path; it never fetches data or places orders."""
    import argparse

    parser = argparse.ArgumentParser(
        description="H7 real-paper exit path (mechanical records only; never orders)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("status", "validate authority and write nothing"),
        ("monitor", "observe every open authorized paper position"),
        ("fill", "process every due or retryable paper exit"),
    ):
        command = sub.add_parser(name, help=help_text)
        _add_session_arguments(command)

    try:
        args = parser.parse_args(argv)
        session = open_real_exit_session(
            data_gate_receipt_path=Path(args.data_gate_receipt),
            decision_session=args.decision_session,
            source_evaluation_session=args.source_evaluation_session,
            base_dir=REAL_FORWARD_STORE,
        )
        if args.command == "status":
            print(
                f"H7 EXIT SESSION READY decision={session.decision_session} "
                f"source={session.evaluation_session} positions="
                f"{len(session.authorized_position_ids)}"
            )
            return 0
        if args.command == "monitor":
            report = monitor_real_exits(session)
            _print_report(report, empty_detail="H7 EXIT NO_OPEN_POSITIONS")
            return 2 if report.failed else 0
        report = fill_real_exits(session)
        _print_report(report, empty_detail="H7 EXIT NO_DUE_INTENTS")
        return 2 if report.failed else 0
    except _RUN_ERRORS as exc:
        print(f"H7 EXIT REFUSED -- {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

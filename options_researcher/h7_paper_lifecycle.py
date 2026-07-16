"""H7 forward-roadmap Stage 4 paper lifecycle.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE.  This module has no CLI, accepts only
an explicit injected forward-ledger directory, and unconditionally refuses
the real ``ledger/h7_forward`` store (including paths that reach it through a
symlink).  Stage 8 is the only arc that may introduce an operational path.

Stage 4 starts from a board-resolved action.  It records T entry intent,
owner approval no later than the T+1 XNYS close, and a mechanical paper fill
from T+1 EOD quotes.  All state is replayed from the verified Stage-3 event
ledger; there is no second mutable book.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import config
from data.cache_runner import session_close_utc, trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher import h7_event_ledger as event_ledger
from strategies.h7_backtest import primary_exit_reason

REAL_FORWARD_STORE = Path(__file__).resolve().parents[1] / "ledger" / "h7_forward"


class LifecycleError(RuntimeError):
    """Base class for Stage-4 lifecycle refusals."""


class ActivationBoundaryError(LifecycleError):
    """The caller attempted to use the real forward store before Stage 8."""


class LifecycleValidationError(LifecycleError):
    """A lifecycle transition violates the frozen Stage-4 contract."""


@dataclass(frozen=True)
class TransitionResult:
    event_id: str
    event_type: str
    payload: dict
    appended: bool


@dataclass(frozen=True)
class PaperPosition:
    position_id: str
    symbol: str
    lane: str
    structure: str
    state: str
    entry_event_id: str
    entry_session: str
    entry_payload: dict
    exit_intent_id: str | None = None
    exit_event_id: str | None = None


def _synthetic_base(base_dir) -> Path:
    if base_dir is None:
        raise ActivationBoundaryError("an explicit synthetic base_dir is required")
    base = Path(base_dir)
    resolved = base.resolve(strict=False)
    real = REAL_FORWARD_STORE.resolve()
    if resolved == real or real in resolved.parents:
        raise ActivationBoundaryError(
            "the real H7 forward store is prohibited until Stage 8 activation"
        )
    return base


def _next_session(session: str) -> str:
    start = date.fromisoformat(session) + timedelta(days=1)
    end = start + timedelta(days=14)
    sessions = trading_days(start.isoformat(), end.isoformat())
    if not sessions:
        raise LifecycleValidationError(f"no XNYS session follows {session}")
    return sessions[0]


def _last_session_before(day: date) -> str:
    start = day - timedelta(days=21)
    end = day - timedelta(days=1)
    sessions = trading_days(start.isoformat(), end.isoformat())
    if not sessions:
        raise LifecycleValidationError(
            f"no XNYS session strictly precedes {day.isoformat()}"
        )
    return sessions[-1]


def _report_gated_h7c_exit(
    position: PaperPosition,
    intent: event_ledger.StoredEvent,
) -> tuple[bool, date | None, str | None]:
    if position.lane != "c" or not config.H7C_CLOSE_BEFORE_EARNINGS:
        return False, None, None
    next_report = intent.payload.get("next_report")
    if next_report is None:
        return False, None, None
    report_date = date.fromisoformat(str(next_report))
    return True, report_date, _last_session_before(report_date)


def _clock_utc(clock) -> datetime:
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() != timedelta(0)
    ):
        raise LifecycleValidationError("clock must return a UTC datetime")
    return now


def _record_after_session_close(session: str, clock) -> tuple[datetime, object]:
    now = _clock_utc(clock)
    close = session_close_utc(session)
    if now < close:
        raise LifecycleValidationError(
            f"session {session} is not complete until {close.isoformat()}"
        )
    return now, lambda: now


def entry_intent_id(decision_session: str, symbol: str, lane: str) -> str:
    return f"s4.entry_intent:{decision_session}:{symbol.upper()}:{lane}"


def _approval_id(intent_id: str) -> str:
    return f"s4.owner_approval:{intent_id}"


def _entry_fill_id(intent_id: str, fill_session: str) -> str:
    return f"s4.paper_fill.open:{fill_session}:{intent_id}"


def _skip_id(intent_id: str, session: str, reason: str) -> str:
    return f"s4.skip:{session}:{reason}:{intent_id}"


def _gap_id(parent_id: str, session: str, phase: str) -> str:
    return f"s4.data_gap:{session}:{phase}:{parent_id}"


def _exit_intent_id(position_id: str, session: str) -> str:
    return f"s4.exit_intent:{session}:{position_id}"


def _exit_fill_id(exit_intent_id: str, session: str) -> str:
    return f"s4.paper_fill.close:{session}:{exit_intent_id}"


def _by_id(events: list[event_ledger.StoredEvent]) -> dict[str, event_ledger.StoredEvent]:
    return {ev.event_id: ev for ev in events}


def _require_event(
    events: list[event_ledger.StoredEvent],
    event_id: str,
    event_type: str,
    *,
    session: str | None = None,
) -> event_ledger.StoredEvent:
    found = _by_id(events).get(event_id)
    if found is None:
        raise LifecycleValidationError(f"required event {event_id!r} is missing")
    if found.event_type != event_type:
        raise LifecycleValidationError(
            f"event {event_id!r} must be {event_type}, got {found.event_type}"
        )
    if session is not None and found.evaluation_session != session:
        raise LifecycleValidationError(
            f"event {event_id!r} belongs to {found.evaluation_session}, not {session}"
        )
    return found


_EXPECTED_HEAD_UNSET = object()


def _transition(
    base: Path, event: dict, *, clock=None, expected_head=_EXPECTED_HEAD_UNSET
) -> TransitionResult:
    try:
        kwargs = {"base_dir": base, "clock": clock}
        if expected_head is not _EXPECTED_HEAD_UNSET:
            kwargs["expected_head"] = expected_head
        result = event_ledger.append_event(event, **kwargs)
    except event_ledger.EventConflictError as exc:
        raise LifecycleValidationError(
            f"conflicting rerun for {event['event_id']!r}"
        ) from exc
    except event_ledger.LedgerHeadConflictError as exc:
        raise LifecycleValidationError(
            "forward ledger changed during lifecycle capacity evaluation; rerun"
        ) from exc
    stored = _by_id(event_ledger.read_events(base))[event["event_id"]]
    return TransitionResult(
        event_id=stored.event_id,
        event_type=stored.event_type,
        payload=stored.payload,
        appended=result.appended,
    )


def _event(
    *,
    event_id: str,
    event_type: str,
    occurred_at_utc: str,
    evaluation_session: str,
    symbol: str | None,
    lane: str | None,
    causes: list[str],
    payload: dict,
) -> dict:
    return {
        "schema_version": event_ledger.SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": occurred_at_utc,
        "evaluation_session": evaluation_session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes,
        "payload": payload,
    }


def _validated_action(action: dict) -> tuple[str, str, list[dict]]:
    if not isinstance(action, dict):
        raise LifecycleValidationError("action must be a board-resolved action dict")
    lane = action.get("lane")
    kind = action.get("kind")
    if lane not in event_ledger.LANES:
        raise LifecycleValidationError("action lane must be a, b, or c")
    allowed = {
        "a": {"long_call", "call_debit_spread"},
        "b": {"long_call", "call_debit_spread"},
        "c": {"bull_put_spread"},
    }
    if kind not in allowed[lane]:
        raise LifecycleValidationError(f"structure {kind!r} is invalid for lane {lane}")
    try:
        expiration = date.fromisoformat(str(action["expiration"])).isoformat()
    except (KeyError, TypeError, ValueError) as exc:
        raise LifecycleValidationError("action expiration must be YYYY-MM-DD") from exc
    quantity = config.H7_FORWARD_CONTRACTS
    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
        raise LifecycleValidationError("H7_FORWARD_CONTRACTS must be a positive integer")

    if kind == "long_call":
        specs = [("long", action.get("strike"), "C", "buy")]
    elif kind == "call_debit_spread":
        specs = [
            ("long", action.get("long_strike"), "C", "buy"),
            ("short", action.get("short_strike"), "C", "sell"),
        ]
    else:
        specs = [
            ("short", action.get("short_strike"), "P", "sell"),
            ("long", action.get("long_strike"), "P", "buy"),
        ]
    legs: list[dict] = []
    for name, strike, right, side in specs:
        if strike is None:
            raise LifecycleValidationError(f"{name} strike must be numeric")
        try:
            strike_f = float(strike)
        except (TypeError, ValueError) as exc:
            raise LifecycleValidationError(f"{name} strike must be numeric") from exc
        if strike_f <= 0:
            raise LifecycleValidationError(f"{name} strike must be positive")
        legs.append(
            {
                "name": name,
                "expiration": expiration,
                "strike": strike_f,
                "right": right,
                "side": side,
                "quantity": quantity,
            }
        )
    return lane, kind, legs


def record_entry_intent(
    *,
    base_dir,
    symbol: str,
    action: dict,
    decision_chain,
    decision_session: str,
    source_health_id: str,
    data_gate_id: str,
    board_resolution_id: str,
    chain_identity: str,
    closes_identity: str,
    clock=None,
) -> TransitionResult:
    """Record a board-resolved T intent with frozen contract identity."""
    base = _synthetic_base(base_dir)
    _, write_clock = _record_after_session_close(decision_session, clock)
    events = event_ledger.read_events(base)
    _require_event(events, source_health_id, "source_health", session=decision_session)
    gate = _require_event(events, data_gate_id, "data_gate", session=decision_session)
    board = _require_event(
        events, board_resolution_id, "board_resolution", session=decision_session
    )
    if source_health_id not in board.causes or data_gate_id not in board.causes:
        raise LifecycleValidationError("board_resolution must cite source health and data gate")
    if gate.payload.get("whole_universe_verdict") != "GO":
        raise LifecycleValidationError("entry intent requires a GO decision-session data gate")
    if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
        raise LifecycleValidationError("symbol must be uppercase")
    if not isinstance(chain_identity, str) or not chain_identity:
        raise LifecycleValidationError("chain_identity is required")
    if not isinstance(closes_identity, str) or not closes_identity:
        raise LifecycleValidationError("closes_identity is required")
    lane, kind, legs = _validated_action(action)
    event_id = entry_intent_id(decision_session, symbol, lane)
    accepted = board.payload.get("accepted")
    if not isinstance(accepted, list) or not any(
        isinstance(item, dict)
        and item.get("symbol") == symbol
        and item.get("lane") == lane
        and event_ledger.canonical_json(item.get("action"))
        == event_ledger.canonical_json(action)
        for item in accepted
    ):
        raise LifecycleValidationError(
            "board_resolution did not accept this exact symbol/lane/action"
        )
    for prior_intent in events:
        if (
            prior_intent.event_type == "entry_intent"
            and prior_intent.symbol == symbol
            and prior_intent.lane == lane
            and prior_intent.event_id != event_id
            and _terminal_for_intent(events, prior_intent.event_id) is None
        ):
            raise LifecycleValidationError(
                f"{symbol} lane {lane} already has an unresolved entry intent"
            )
    for position in replay_positions(base_dir=base):
        if (
            position.state != "closed"
            and position.symbol == symbol
            and position.lane == lane
            and position.position_id != event_id
        ):
            raise LifecycleValidationError(
                f"{symbol} lane {lane} already has an open or pending position"
            )
    decision_rows, decision_gap = _quote_rows(decision_chain, legs)
    if decision_rows is None:
        raise LifecycleValidationError(
            f"decision chain cannot reconstruct the accepted action: {decision_gap}"
        )
    if not all(
        passes_liquidity(row.open_interest, row.bid, row.ask)
        for row in decision_rows.values()
    ):
        raise LifecycleValidationError("accepted action is not liquid in its decision chain")
    decision_legs, decision_net_debit = _entry_prices(legs, decision_rows)
    decision_cash_kind, decision_at_risk = _entry_economics(
        action, decision_net_debit, len(legs)
    )
    expected_head = _EXPECTED_HEAD_UNSET
    if isinstance(board.payload.get("book_snapshot_hash"), str):
        planned_fill_session = _next_session(decision_session)
        if board.payload.get("planned_fill_session") != planned_fill_session:
            raise LifecycleValidationError(
                "Stage-5 board reservation has the wrong planned fill session"
            )
        reserved_at_risk = action.get("max_loss", action.get("cost"))
        if (
            isinstance(reserved_at_risk, bool)
            or not isinstance(reserved_at_risk, (int, float))
            or not math.isfinite(float(reserved_at_risk))
            or float(reserved_at_risk) != decision_at_risk
        ):
            raise LifecycleValidationError(
                "entry intent risk does not match its Stage-5 board reservation"
            )
        from options_researcher.h7_forward_book import derive_book

        book = derive_book(
            base_dir=base,
            evaluation_session=planned_fill_session,
        )
        reservation_ids = {item.reservation_id for item in book.reservations}
        board_reservation_id = f"{board_resolution_id}:{symbol}:{lane}"
        if event_id not in reservation_ids and board_reservation_id not in reservation_ids:
            raise LifecycleValidationError(
                "Stage-5 board reservation is absent or already expired"
            )
        expected_head = events[-1].record_hash
    decision_commission = (
        len(legs) * config.H7_FORWARD_CONTRACTS * config.COMMISSION_PER_CONTRACT
    )
    payload = {
        "position_id": event_id,
        "decision_session": decision_session,
        "planned_fill_session": _next_session(decision_session),
        "structure": kind,
        "action": action,
        "legs": legs,
        "decision_legs": decision_legs,
        "decision_cash_kind": decision_cash_kind,
        "decision_net_debit_per_share": decision_net_debit,
        "decision_commission": decision_commission,
        "decision_at_risk": decision_at_risk,
        "slippage_haircut": config.SLIPPAGE_HAIRCUT,
        "chain_identity": chain_identity,
        "closes_identity": closes_identity,
    }
    return _transition(
        base,
        _event(
            event_id=event_id,
            event_type="entry_intent",
            occurred_at_utc=session_close_utc(decision_session).isoformat(),
            evaluation_session=decision_session,
            symbol=symbol,
            lane=lane,
            causes=[data_gate_id, board_resolution_id, source_health_id],
            payload=payload,
        ),
        clock=write_clock,
        expected_head=expected_head,
    )


def _terminal_for_intent(
    events: list[event_ledger.StoredEvent], intent_id: str
) -> event_ledger.StoredEvent | None:
    for ev in events:
        if ev.event_type in {"paper_fill", "skip"} and ev.payload.get(
            "entry_intent_id"
        ) == intent_id:
            return ev
    return None


def _terminal_for_exit_intent(
    events: list[event_ledger.StoredEvent], exit_intent_id: str
) -> event_ledger.StoredEvent | None:
    for ev in events:
        if ev.event_type == "skip" and ev.payload.get("exit_intent_id") == exit_intent_id:
            return ev
    return None


def _source_health_cause(
    events: list[event_ledger.StoredEvent], intent: event_ledger.StoredEvent
) -> str | None:
    by_id = _by_id(events)
    for cause_id in intent.causes:
        found = by_id.get(cause_id)
        if found is not None and found.event_type == "source_health":
            return cause_id
    return None


def _as_result(event: event_ledger.StoredEvent) -> TransitionResult:
    return TransitionResult(
        event_id=event.event_id,
        event_type=event.event_type,
        payload=event.payload,
        appended=False,
    )


def _validated_approval(
    events: list[event_ledger.StoredEvent], intent: event_ledger.StoredEvent
) -> event_ledger.StoredEvent | None:
    approval = _by_id(events).get(_approval_id(intent.event_id))
    if approval is None:
        return None
    fill_session = str(intent.payload["planned_fill_session"])
    cutoff = session_close_utc(fill_session)
    if approval.event_type != "owner_approval":
        raise LifecycleValidationError("deterministic approval id has the wrong event type")
    if approval.causes != [intent.event_id]:
        raise LifecycleValidationError("owner approval must cite only its entry intent")
    if approval.evaluation_session != intent.evaluation_session:
        raise LifecycleValidationError("owner approval must copy the decision session")
    if approval.symbol != intent.symbol or approval.lane != intent.lane:
        raise LifecycleValidationError("owner approval symbol/lane mismatches its intent")
    if approval.payload.get("entry_intent_id") != intent.event_id:
        raise LifecycleValidationError("owner approval payload names the wrong intent")
    if approval.payload.get("fill_session") != fill_session:
        raise LifecycleValidationError("owner approval payload names the wrong fill session")
    if approval.payload.get("approval_cutoff_utc") != cutoff.isoformat():
        raise LifecycleValidationError("owner approval payload has the wrong cutoff")
    recorded = datetime.fromisoformat(approval.recorded_at_utc)
    intent_recorded = datetime.fromisoformat(intent.recorded_at_utc)
    if recorded < intent_recorded:
        raise LifecycleValidationError("owner approval predates its entry intent")
    if recorded > cutoff:
        raise LifecycleValidationError("owner approval was recorded after the T+1 cutoff")
    return approval


def record_owner_approval(
    *, base_dir, entry_intent_id: str, clock=None
) -> TransitionResult:
    """Record approval before T+1 close; late approval mechanically skips."""
    base = _synthetic_base(base_dir)
    events = event_ledger.read_events(base)
    intent = _require_event(events, entry_intent_id, "entry_intent")
    terminal = _terminal_for_intent(events, entry_intent_id)
    if terminal is not None:
        return _as_result(terminal)
    approval_id = _approval_id(entry_intent_id)
    existing = _by_id(events).get(approval_id)
    if existing is not None:
        validated = _validated_approval(events, intent)
        if validated is None:  # pragma: no cover - guarded by existing
            raise LifecycleValidationError("approval disappeared during verification")
        return _as_result(validated)
    fill_session = intent.payload["planned_fill_session"]
    cutoff = session_close_utc(fill_session)
    now = _clock_utc(clock)
    write_clock = lambda: now
    if now > cutoff:
        reason = "approval_late"
        return _transition(
            base,
            _event(
                event_id=_skip_id(entry_intent_id, fill_session, reason),
                event_type="skip",
                occurred_at_utc=cutoff.isoformat(),
                evaluation_session=fill_session,
                symbol=intent.symbol,
                lane=intent.lane,
                causes=[entry_intent_id],
                payload={
                    "entry_intent_id": entry_intent_id,
                    "reason": reason,
                    "approval_cutoff_utc": cutoff.isoformat(),
                },
            ),
            clock=write_clock,
        )
    return _transition(
        base,
        _event(
            event_id=approval_id,
            event_type="owner_approval",
            occurred_at_utc=now.isoformat(),
            evaluation_session=intent.evaluation_session,
            symbol=intent.symbol,
            lane=intent.lane,
            causes=[entry_intent_id],
            payload={
                "entry_intent_id": entry_intent_id,
                "fill_session": fill_session,
                "approval_cutoff_utc": cutoff.isoformat(),
            },
        ),
        clock=write_clock,
    )


def _quote_rows(chain, legs: list[dict]) -> tuple[dict[str, pd.Series] | None, str | None]:
    if not isinstance(chain, pd.DataFrame) or chain.empty:
        return None, "chain_missing_or_empty"
    required = {
        "expiration", "strike", "right", "bid", "ask", "open_interest", "delta"
    }
    if not required.issubset(chain.columns):
        return None, "chain_schema_invalid"
    rows: dict[str, pd.Series] = {}
    try:
        for leg in legs:
            selected = chain[
                (chain["expiration"].astype(str) == leg["expiration"])
                & (chain["strike"].astype(float) == leg["strike"])
                & (chain["right"].astype(str).str.upper() == leg["right"])
            ]
            if len(selected) != 1:
                return None, "contract_missing_or_duplicate"
            row = selected.iloc[0]
            if not quote_valid(row.bid, row.ask):
                return None, "quote_invalid"
            if not math.isfinite(float(row.delta)):
                return None, "delta_invalid"
            rows[leg["name"]] = row
    except (AttributeError, TypeError, ValueError):
        return None, "chain_schema_invalid"
    return rows, None


def _entry_prices(legs: list[dict], rows: dict[str, pd.Series]) -> tuple[list[dict], float]:
    priced: list[dict] = []
    net_debit = 0.0
    for leg in legs:
        row = rows[leg["name"]]
        fill = adverse_buy(row.ask) if leg["side"] == "buy" else adverse_sell(row.bid)
        signed_debit = fill if leg["side"] == "buy" else -fill
        net_debit += signed_debit
        priced.append(
            {
                **leg,
                "raw_bid": float(row.bid),
                "raw_ask": float(row.ask),
                "open_interest": int(row.open_interest),
                "raw_delta": float(row.delta),
                "fill_price": fill,
            }
        )
    return priced, net_debit


def _close_prices(legs: list[dict], rows: dict[str, pd.Series]) -> tuple[list[dict], float]:
    """Price the exact frozen contracts on the opposite executable side."""
    priced: list[dict] = []
    net_credit = 0.0
    for leg in legs:
        row = rows[leg["name"]]
        close_side = "sell" if leg["side"] == "buy" else "buy"
        fill = adverse_sell(row.bid) if close_side == "sell" else adverse_buy(row.ask)
        net_credit += fill if close_side == "sell" else -fill
        priced.append(
            {
                **leg,
                "side": close_side,
                "raw_bid": float(row.bid),
                "raw_ask": float(row.ask),
                "open_interest": int(row.open_interest),
                "raw_delta": float(row.delta),
                "fill_price": fill,
            }
        )
    return priced, net_credit


def _entry_economics(action: dict, net_debit: float, leg_count: int) -> tuple[str, float]:
    kind = action["kind"]
    quantity = config.H7_FORWARD_CONTRACTS
    round_trip_commission = leg_count * 2 * config.COMMISSION_PER_CONTRACT * quantity
    if kind == "long_call":
        if net_debit <= 0:
            raise LifecycleValidationError("long-call debit must be positive")
        return "debit", net_debit * 100 * quantity + round_trip_commission
    width = float(action["short_strike"]) - float(action["long_strike"])
    if width <= 0:
        raise LifecycleValidationError("vertical width must be positive")
    if kind == "call_debit_spread":
        if not 0 < net_debit <= width:
            raise LifecycleValidationError("call-spread debit is outside (0, width]")
        return "debit", net_debit * 100 * quantity + round_trip_commission
    credit = -net_debit
    if not 0 < credit < width:
        raise LifecycleValidationError("put-spread credit is outside (0, width)")
    if credit < config.H7C_CREDIT_FLOOR_FRAC * width:
        raise LifecycleValidationError("put-spread credit is below the frozen floor")
    return "credit", (width - credit) * 100 * quantity + round_trip_commission


def _skip(
    base: Path,
    intent: event_ledger.StoredEvent,
    *,
    session: str,
    reason: str,
    causes: list[str],
    clock=None,
    details: dict | None = None,
    expected_head=_EXPECTED_HEAD_UNSET,
) -> TransitionResult:
    payload = {"entry_intent_id": intent.event_id, "reason": reason}
    if details:
        payload.update(details)
    return _transition(
        base,
        _event(
            event_id=_skip_id(intent.event_id, session, reason),
            event_type="skip",
            occurred_at_utc=session_close_utc(session).isoformat(),
            evaluation_session=session,
            symbol=intent.symbol,
            lane=intent.lane,
            causes=causes,
            payload=payload,
        ),
        clock=clock,
        expected_head=expected_head,
    )


def _exit_terminal_skip(
    base: Path,
    intent: event_ledger.StoredEvent,
    position: PaperPosition,
    *,
    session: str,
    reason: str,
    causes: list[str],
    clock=None,
    details: dict | None = None,
) -> TransitionResult:
    payload = {
        "exit_intent_id": intent.event_id,
        "position_id": position.position_id,
        "reason": reason,
    }
    if details:
        payload.update(details)
    return _transition(
        base,
        _event(
            event_id=_skip_id(intent.event_id, session, reason),
            event_type="skip",
            occurred_at_utc=session_close_utc(session).isoformat(),
            evaluation_session=session,
            symbol=position.symbol,
            lane=position.lane,
            causes=causes,
            payload=payload,
        ),
        clock=clock,
    )


def process_entry_fill(
    *,
    base_dir,
    entry_intent_id: str,
    fill_session: str,
    chain,
    source_health_id: str,
    data_gate_id: str,
    chain_identity: str,
    closes_identity: str,
    underlying_close=None,
    clock=None,
) -> TransitionResult:
    """Resolve an approved intent exactly once at its T+1 EOD quotes."""
    base = _synthetic_base(base_dir)
    events = event_ledger.read_events(base)
    intent = _require_event(events, entry_intent_id, "entry_intent")
    terminal = _terminal_for_intent(events, entry_intent_id)
    if terminal is not None and terminal.event_type == "skip":
        return _as_result(terminal)
    existing_fill = terminal if terminal is not None else None
    planned = intent.payload["planned_fill_session"]
    if fill_session != planned:
        raise LifecycleValidationError(
            f"entry fill must use T+1 session {planned}, got {fill_session}"
        )
    _, write_clock = _record_after_session_close(fill_session, clock)
    if not isinstance(chain_identity, str) or not chain_identity:
        raise LifecycleValidationError("fill chain_identity is required")
    if not isinstance(closes_identity, str) or not closes_identity:
        raise LifecycleValidationError("fill closes_identity is required")
    if underlying_close is not None and (
        isinstance(underlying_close, bool)
        or not isinstance(underlying_close, (int, float))
        or not math.isfinite(float(underlying_close))
        or float(underlying_close) <= 0
    ):
        raise LifecycleValidationError("fill underlying_close must be finite and positive")
    source = _require_event(events, source_health_id, "source_health", session=fill_session)
    gate = _require_event(events, data_gate_id, "data_gate", session=fill_session)
    approval = _validated_approval(events, intent)
    if approval is None:
        if existing_fill is not None:
            raise LifecycleValidationError("recorded entry fill lost its approval")
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="approval_missing",
            causes=[entry_intent_id],
            clock=write_clock,
        )
    for position in replay_positions(base_dir=base):
        if (
            position.state != "closed"
            and position.symbol == intent.symbol
            and position.lane == intent.lane
            and position.position_id != intent.payload["position_id"]
        ):
            raise LifecycleValidationError(
                f"{intent.symbol} lane {intent.lane} already has an open position"
            )
    if gate.payload.get("whole_universe_verdict") != "GO":
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="data_gate_no_go",
            causes=[entry_intent_id, data_gate_id],
            clock=write_clock,
        )
    if (
        source.symbol != intent.symbol
        or source.payload.get("gate") != "CLEAR"
        or source.payload.get("healthy") is not True
    ):
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="earnings_gate_at_fill",
            causes=[entry_intent_id, source_health_id],
            clock=write_clock,
        )
    action = intent.payload["action"]
    expiration = date.fromisoformat(str(action["expiration"]))
    dte = (expiration - date.fromisoformat(fill_session)).days
    band = config.H7C_DTE_BAND if intent.lane == "c" else config.H7_LONG_DTE_BAND
    if not band[0] <= dte <= band[1]:
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="dte_at_fill",
            causes=[entry_intent_id, data_gate_id],
            clock=write_clock,
        )
    legs = intent.payload["legs"]
    rows, gap_reason = _quote_rows(chain, legs)
    if rows is None:
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        gap_id = _gap_id(entry_intent_id, fill_session, "entry_fill")
        _transition(
            base,
            _event(
                event_id=gap_id,
                event_type="data_gap",
                occurred_at_utc=session_close_utc(fill_session).isoformat(),
                evaluation_session=fill_session,
                symbol=intent.symbol,
                lane=intent.lane,
                causes=[data_gate_id],
                payload={
                    "entry_intent_id": entry_intent_id,
                    "phase": "entry_fill",
                    "reason": gap_reason,
                    "chain_identity": chain_identity,
                    "closes_identity": closes_identity,
                },
            ),
            clock=write_clock,
        )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="entry_data_gap",
            causes=[entry_intent_id, gap_id],
            clock=write_clock,
        )
    if not all(
        passes_liquidity(row.open_interest, row.bid, row.ask) for row in rows.values()
    ):
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="liquidity_at_fill",
            causes=[entry_intent_id, data_gate_id],
            clock=write_clock,
        )
    priced_legs, net_debit = _entry_prices(legs, rows)
    try:
        cash_kind, at_risk = _entry_economics(action, net_debit, len(legs))
    except LifecycleValidationError:
        if existing_fill is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded entry fill"
            )
        return _skip(
            base,
            intent,
            session=fill_session,
            reason="economics_at_fill",
            causes=[entry_intent_id, data_gate_id],
            clock=write_clock,
        )
    quantity = config.H7_FORWARD_CONTRACTS
    commission = len(legs) * quantity * config.COMMISSION_PER_CONTRACT
    if underlying_close is None:
        raise LifecycleValidationError(
            "a successful entry fill requires the exact-session adjusted close"
        )
    benchmark_close = float(underlying_close)
    expected_head = _EXPECTED_HEAD_UNSET
    if existing_fill is None:
        from options_researcher.h7_forward_book import assess_entry_fill

        assessment = assess_entry_fill(
            base_dir=base,
            entry_intent_id=entry_intent_id,
            fill_session=fill_session,
            actual_at_risk=at_risk,
        )
        capacity_payload = {
            "book_snapshot_hash": assessment.snapshot_hash,
            "capacity_snapshot": assessment.capacity_snapshot,
            "projected_month_risk": assessment.projected_month_risk,
            "projected_open_h7c": assessment.projected_open_h7c,
            "projected_underlying_occupancy": (
                assessment.projected_underlying_occupancy
            ),
            "failed_constraints": list(assessment.failed_constraints),
            "limits": {
                "monthly_at_risk": config.H7_MONTHLY_AT_RISK,
                "h7c_max_concurrent": config.H7C_MAX_CONCURRENT,
                "max_open_per_underlying": config.H7_MAX_OPEN_PER_UNDERLYING,
            },
        }
        if not assessment.allowed:
            return _skip(
                base,
                intent,
                session=fill_session,
                reason="book_capacity_at_fill",
                causes=[entry_intent_id, data_gate_id],
                clock=write_clock,
                details=capacity_payload,
                expected_head=assessment.expected_head,
            )
        expected_head = assessment.expected_head
    else:
        capacity_payload = {
            key: existing_fill.payload[key]
            for key in (
                "book_snapshot_hash",
                "capacity_snapshot",
                "projected_month_risk",
                "projected_open_h7c",
                "projected_underlying_occupancy",
                "failed_constraints",
                "limits",
            )
            if key in existing_fill.payload
        }
    payload = {
        "transition": "open",
        "position_id": intent.payload["position_id"],
        "entry_intent_id": entry_intent_id,
        "owner_approval_id": approval.event_id,
        "decision_session": intent.evaluation_session,
        "fill_session": fill_session,
        "structure": intent.payload["structure"],
        "action": action,
        "legs": priced_legs,
        "cash_kind": cash_kind,
        "net_debit_per_share": net_debit,
        "commission": commission,
        "at_risk": at_risk,
        "slippage_haircut": config.SLIPPAGE_HAIRCUT,
        "chain_identity": chain_identity,
        "closes_identity": closes_identity,
        "decision_chain_identity": intent.payload["chain_identity"],
        "decision_closes_identity": intent.payload["closes_identity"],
        "underlying_close": benchmark_close,
        "underlying_close_session": fill_session,
        "underlying_close_identity": closes_identity,
        **capacity_payload,
    }
    return _transition(
        base,
        _event(
            event_id=_entry_fill_id(entry_intent_id, fill_session),
            event_type="paper_fill",
            occurred_at_utc=session_close_utc(fill_session).isoformat(),
            evaluation_session=fill_session,
            symbol=intent.symbol,
            lane=intent.lane,
            causes=[entry_intent_id, approval.event_id, source_health_id, data_gate_id],
            payload=payload,
        ),
        clock=write_clock,
        expected_head=expected_head,
    )


def _position(base: Path, position_id: str) -> PaperPosition:
    found = {p.position_id: p for p in replay_positions(base_dir=base)}.get(position_id)
    if found is None:
        raise LifecycleValidationError(f"position {position_id!r} is not open in the ledger")
    return found


def _gap_transition(
    base: Path,
    *,
    parent_id: str,
    position: PaperPosition,
    session: str,
    phase: str,
    reason: str,
    data_gate_id: str,
    chain_identity: str,
    closes_identity: str,
    exit_intent_id: str | None = None,
    clock=None,
) -> TransitionResult:
    payload = {
        "position_id": position.position_id,
        "phase": phase,
        "reason": reason,
        "chain_identity": chain_identity,
        "closes_identity": closes_identity,
    }
    if exit_intent_id is not None:
        payload["exit_intent_id"] = exit_intent_id
    return _transition(
        base,
        _event(
            event_id=_gap_id(parent_id, session, phase),
            event_type="data_gap",
            occurred_at_utc=session_close_utc(session).isoformat(),
            evaluation_session=session,
            symbol=position.symbol,
            lane=position.lane,
            causes=[data_gate_id],
            payload=payload,
        ),
        clock=clock,
    )


def observe_exit(
    *,
    base_dir,
    position_id: str,
    evaluation_session: str,
    chain,
    data_gate_id: str,
    chain_identity: str,
    closes_identity: str,
    underlying_close: float | None,
    earnings_gate: str,
    next_report: str | None,
    source_health_id: str | None,
    clock=None,
) -> TransitionResult | None:
    """Evaluate frozen exits on session S and queue a mechanical S+1 close.

    An unpriceable observation is visible as ``data_gap``.  Date-known and
    earnings exits can still fire despite missing marks; price-based exits
    never infer a mark.
    """
    base = _synthetic_base(base_dir)
    position = _position(base, position_id)
    if position.state == "closed":
        raise LifecycleValidationError("a closed position cannot emit another exit intent")
    events = event_ledger.read_events(base)
    existing_exit = next(
        (
            ev
            for ev in events
            if ev.event_type == "exit_intent"
            and ev.payload.get("position_id") == position_id
        ),
        None,
    )
    _, write_clock = _record_after_session_close(evaluation_session, clock)
    if not isinstance(chain_identity, str) or not chain_identity:
        raise LifecycleValidationError("exit chain_identity is required")
    if not isinstance(closes_identity, str) or not closes_identity:
        raise LifecycleValidationError("exit closes_identity is required")
    gate = _require_event(events, data_gate_id, "data_gate", session=evaluation_session)
    planned_fill = _next_session(evaluation_session)
    entry = position.entry_payload
    action = entry["action"]
    expiration = date.fromisoformat(str(action["expiration"]))
    if date.fromisoformat(evaluation_session) >= expiration:
        raise LifecycleValidationError(
            f"position reached expiration {expiration} without a resolved exit"
        )

    reasons: list[str] = []
    close_dte = config.H7C_CLOSE_AT_DTE if position.lane == "c" else config.H7_CLOSE_AT_DTE
    if (expiration - date.fromisoformat(planned_fill)).days <= close_dte:
        reasons.append("scheduled_dte")

    earnings_reason = False
    if position.lane == "c":
        if earnings_gate not in {"CLEAR", "BANNED", "UNKNOWN"}:
            raise LifecycleValidationError("earnings_gate is not canonical")
        if earnings_gate == "UNKNOWN":
            reasons.append("earnings_unknown")
            earnings_reason = True
        if next_report is not None:
            report = date.fromisoformat(next_report)
            after_fill = _next_session(planned_fill)
            if date.fromisoformat(planned_fill) >= report or date.fromisoformat(
                after_fill
            ) >= report:
                reasons.append("pre_earnings")
                earnings_reason = True
    if earnings_reason:
        if source_health_id is None:
            raise LifecycleValidationError("earnings exit requires source_health_id")
        source = _require_event(
            events, source_health_id, "source_health", session=evaluation_session
        )
        expected_healthy = earnings_gate != "UNKNOWN"
        if (
            source.symbol != position.symbol
            or source.payload.get("gate") != earnings_gate
            or source.payload.get("healthy") is not expected_healthy
        ):
            raise LifecycleValidationError(
                "earnings exit source-health event is inconsistent"
            )

    gap: TransitionResult | None = None
    rows: dict[str, pd.Series] | None = None
    observation: dict = {"status": "data_gate_no_go"}
    if gate.payload.get("whole_universe_verdict") != "GO":
        if existing_exit is None:
            gap = _gap_transition(
                base,
                parent_id=position.entry_event_id,
                position=position,
                session=evaluation_session,
                phase="exit_monitor",
                reason="exit_data_gate_no_go",
                data_gate_id=data_gate_id,
                chain_identity=chain_identity,
                closes_identity=closes_identity,
                clock=write_clock,
            )
    else:
        rows, gap_reason = _quote_rows(chain, entry["legs"])
        if rows is None:
            observation = {"status": "data_gap", "reason": gap_reason}
            if existing_exit is None:
                gap = _gap_transition(
                    base,
                    parent_id=position.entry_event_id,
                    position=position,
                    session=evaluation_session,
                    phase="exit_monitor",
                    reason=gap_reason or "exit_marks_missing",
                    data_gate_id=data_gate_id,
                    chain_identity=chain_identity,
                    closes_identity=closes_identity,
                    clock=write_clock,
                )
        else:
            observed_legs, net_close_credit = _close_prices(entry["legs"], rows)
            observation = {
                "status": "priced",
                "legs": observed_legs,
                "net_close_credit_per_share": net_close_credit,
            }
            entry_net_debit = float(entry["net_debit_per_share"])
            if position.structure == "long_call":
                if net_close_credit >= (1 + config.H7_LONG_TP_PCT) * entry_net_debit:
                    reasons.append("profit_target")
            elif position.structure == "call_debit_spread":
                width = float(action["short_strike"]) - float(action["long_strike"])
                if net_close_credit >= config.H7_SPREAD_TP_FRAC_MAX * width:
                    reasons.append("profit_target")
            else:
                buyback = -net_close_credit
                entry_credit = -entry_net_debit
                if buyback <= config.H7C_TP_FRAC * entry_credit:
                    reasons.append("profit_target")
                if buyback >= config.H7C_STOP_CREDIT_MULT * entry_credit:
                    reasons.append("credit_stop")

    stop_ref = float(action["stop_ref"])
    if underlying_close is not None:
        close = float(underlying_close)
        if not math.isfinite(close):
            raise LifecycleValidationError("underlying_close must be finite")
        if close < stop_ref:
            reasons.append("underlying_stop")
    if not reasons:
        if existing_exit is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded exit intent"
            )
        return gap

    ordered_reasons = [reason for reason in (
        "pre_earnings",
        "earnings_unknown",
        "scheduled_dte",
        "underlying_stop",
        "credit_stop",
        "profit_target",
    ) if reason in reasons]
    causes = [position.entry_event_id, data_gate_id]
    if earnings_reason and source_health_id is not None:
        causes.append(source_health_id)
    payload = {
        "position_id": position.position_id,
        "opening_fill_id": position.entry_event_id,
        "trigger_session": evaluation_session,
        "planned_fill_session": planned_fill,
        "trigger_reasons": ordered_reasons,
        "primary_reason": primary_exit_reason(ordered_reasons),
        "chain_identity": chain_identity,
        "closes_identity": closes_identity,
        "observation": observation,
        "underlying_close": underlying_close,
        "earnings_gate": earnings_gate,
        "next_report": next_report,
    }
    return _transition(
        base,
        _event(
            event_id=_exit_intent_id(position.position_id, evaluation_session),
            event_type="exit_intent",
            occurred_at_utc=session_close_utc(evaluation_session).isoformat(),
            evaluation_session=evaluation_session,
            symbol=position.symbol,
            lane=position.lane,
            causes=causes,
            payload=payload,
        ),
        clock=write_clock,
    )


def process_exit_fill(
    *,
    base_dir,
    exit_intent_id: str,
    fill_session: str,
    chain,
    data_gate_id: str,
    chain_identity: str,
    closes_identity: str,
    underlying_close=None,
    clock=None,
) -> TransitionResult:
    """Fill a queued exit, retrying only after a visible prior data gap."""
    base = _synthetic_base(base_dir)
    events = event_ledger.read_events(base)
    intent = _require_event(events, exit_intent_id, "exit_intent")
    position_id = str(intent.payload["position_id"])
    position = _position(base, position_id)
    terminal = _terminal_for_exit_intent(events, exit_intent_id)
    if terminal is not None:
        return _as_result(terminal)
    report_gated, report_date, cutoff_session = _report_gated_h7c_exit(position, intent)
    if report_gated and report_date is not None:
        if date.fromisoformat(fill_session) >= report_date:
            raise LifecycleValidationError(
                "report-gated H7c exit fill cannot occur on or after the scheduled report"
            )
        if (
            cutoff_session is not None
            and date.fromisoformat(fill_session) > date.fromisoformat(cutoff_session)
        ):
            raise LifecycleValidationError(
                "report-gated H7c exit cannot retry past the earnings report cutoff"
            )
    existing = next(
        (
            ev
            for ev in events
            if ev.event_type == "paper_fill"
            and ev.payload.get("transition") == "close"
            and ev.payload.get("exit_intent_id") == exit_intent_id
        ),
        None,
    )
    planned = str(intent.payload["planned_fill_session"])
    prior_gaps = [
        ev
        for ev in events
        if ev.event_type == "data_gap"
        and ev.payload.get("exit_intent_id") == exit_intent_id
    ]
    if prior_gaps:
        latest = prior_gaps[-1].evaluation_session
        expected = _next_session(latest)
        if fill_session != expected:
            raise LifecycleValidationError(
                f"exit retry must use first later session {expected}, got {fill_session}"
            )
    elif fill_session != planned:
        raise LifecycleValidationError(
            f"exit must first attempt planned session {planned}"
        )
    _, write_clock = _record_after_session_close(fill_session, clock)
    if not isinstance(chain_identity, str) or not chain_identity:
        raise LifecycleValidationError("exit-fill chain_identity is required")
    if not isinstance(closes_identity, str) or not closes_identity:
        raise LifecycleValidationError("exit-fill closes_identity is required")
    if underlying_close is not None and (
        isinstance(underlying_close, bool)
        or not isinstance(underlying_close, (int, float))
        or not math.isfinite(float(underlying_close))
        or float(underlying_close) <= 0
    ):
        raise LifecycleValidationError(
            "exit-fill underlying_close must be finite and positive"
        )
    expiration = date.fromisoformat(str(position.entry_payload["action"]["expiration"]))
    if date.fromisoformat(fill_session) >= expiration:
        raise LifecycleValidationError(
            f"exit unresolved at expiration {expiration}; failing loud"
        )
    gate = _require_event(events, data_gate_id, "data_gate", session=fill_session)

    def _maybe_terminal_at_earnings_cutoff(
        gap_reason: str,
    ) -> TransitionResult | None:
        if not report_gated or cutoff_session is None:
            return None
        if date.fromisoformat(fill_session) < date.fromisoformat(cutoff_session):
            return None
        if existing is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded exit fill"
            )
        causes = [exit_intent_id, data_gate_id]
        source_health_id = _source_health_cause(events, intent)
        if source_health_id is not None:
            causes.append(source_health_id)
        return _exit_terminal_skip(
            base,
            intent,
            position,
            session=fill_session,
            reason="exit_data_gap_at_earnings_cutoff",
            causes=causes,
            clock=write_clock,
            details={
                "gap_reason": gap_reason,
                "next_report": intent.payload.get("next_report"),
                "report_cutoff_session": cutoff_session,
            },
        )

    if gate.payload.get("whole_universe_verdict") != "GO":
        if existing is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded exit fill"
            )
        terminal_skip = _maybe_terminal_at_earnings_cutoff("exit_data_gate_no_go")
        if terminal_skip is not None:
            return terminal_skip
        return _gap_transition(
            base,
            parent_id=exit_intent_id,
            position=position,
            session=fill_session,
            phase="exit_fill",
            reason="exit_data_gate_no_go",
            data_gate_id=data_gate_id,
            chain_identity=chain_identity,
            closes_identity=closes_identity,
            exit_intent_id=exit_intent_id,
            clock=write_clock,
        )
    legs = position.entry_payload["legs"]
    rows, gap_reason = _quote_rows(chain, legs)
    if rows is None or not all(
        passes_liquidity(row.open_interest, row.bid, row.ask)
        for row in (rows or {}).values()
    ):
        if existing is not None:
            raise LifecycleValidationError(
                "conflicting rerun no longer reproduces the recorded exit fill"
            )
        terminal_skip = _maybe_terminal_at_earnings_cutoff(
            gap_reason or "exit_liquidity_at_fill"
        )
        if terminal_skip is not None:
            return terminal_skip
        return _gap_transition(
            base,
            parent_id=exit_intent_id,
            position=position,
            session=fill_session,
            phase="exit_fill",
            reason=gap_reason or "exit_liquidity_at_fill",
            data_gate_id=data_gate_id,
            chain_identity=chain_identity,
            closes_identity=closes_identity,
            exit_intent_id=exit_intent_id,
            clock=write_clock,
        )
    priced_legs, net_close_credit = _close_prices(legs, rows)
    quantity = config.H7_FORWARD_CONTRACTS
    commission = len(legs) * quantity * config.COMMISSION_PER_CONTRACT
    if underlying_close is None:
        raise LifecycleValidationError(
            "a successful exit fill requires the exact-session adjusted close"
        )
    benchmark_close = float(underlying_close)
    payload = {
        "transition": "close",
        "position_id": position.position_id,
        "opening_fill_id": position.entry_event_id,
        "exit_intent_id": exit_intent_id,
        "trigger_session": intent.evaluation_session,
        "fill_session": fill_session,
        "primary_reason": intent.payload["primary_reason"],
        "trigger_reasons": intent.payload["trigger_reasons"],
        "structure": position.structure,
        "legs": priced_legs,
        "net_close_credit_per_share": net_close_credit,
        "commission": commission,
        "slippage_haircut": config.SLIPPAGE_HAIRCUT,
        "chain_identity": chain_identity,
        "closes_identity": closes_identity,
        "underlying_close": benchmark_close,
        "underlying_close_session": fill_session,
        "underlying_close_identity": closes_identity,
    }
    return _transition(
        base,
        _event(
            event_id=_exit_fill_id(exit_intent_id, fill_session),
            event_type="paper_fill",
            occurred_at_utc=session_close_utc(fill_session).isoformat(),
            evaluation_session=fill_session,
            symbol=position.symbol,
            lane=position.lane,
            causes=[exit_intent_id, data_gate_id],
            payload=payload,
        ),
        clock=write_clock,
    )


def replay_positions(*, base_dir) -> list[PaperPosition]:
    """Project verified lifecycle events into deterministic position state."""
    base = _synthetic_base(base_dir)
    events = event_ledger.read_events(base)
    positions: dict[str, PaperPosition] = {}
    for ev in events:
        if ev.event_type == "skip":
            exit_intent_id = ev.payload.get("exit_intent_id")
            if isinstance(exit_intent_id, str):
                position_id = ev.payload.get("position_id")
                if not isinstance(position_id, str):
                    raise LifecycleValidationError(
                        "terminal exit skip is missing position_id"
                    )
                opened = positions.get(position_id)
                if opened is None or opened.state != "pending_exit":
                    raise LifecycleValidationError(
                        f"position {position_id!r} has terminal exit skip without pending exit"
                    )
                positions[position_id] = replace(
                    opened,
                    state="exit_failed",
                    exit_intent_id=exit_intent_id,
                    exit_event_id=ev.event_id,
                )
            continue
        if ev.event_type == "exit_intent":
            position_id = ev.payload.get("position_id")
            if not isinstance(position_id, str):
                raise LifecycleValidationError("exit_intent is missing position_id")
            opened = positions.get(position_id)
            if opened is None or opened.state != "open":
                raise LifecycleValidationError(
                    f"position {position_id!r} has exit intent without open state"
                )
            positions[position_id] = replace(
                opened, state="pending_exit", exit_intent_id=ev.event_id
            )
            continue
        if ev.event_type != "paper_fill":
            continue
        transition = ev.payload.get("transition")
        position_id = ev.payload.get("position_id")
        if not isinstance(position_id, str):
            raise LifecycleValidationError("paper_fill is missing position_id")
        if transition == "open":
            if position_id in positions:
                raise LifecycleValidationError(f"position {position_id!r} opens twice")
            positions[position_id] = PaperPosition(
                position_id=position_id,
                symbol=ev.symbol or "",
                lane=ev.lane or "",
                structure=str(ev.payload["structure"]),
                state="open",
                entry_event_id=ev.event_id,
                entry_session=ev.evaluation_session,
                entry_payload=ev.payload,
            )
        elif transition == "close":
            opened = positions.get(position_id)
            if opened is None or opened.state not in {"open", "pending_exit"}:
                raise LifecycleValidationError(
                    f"position {position_id!r} closes without one open fill"
                )
            positions[position_id] = replace(
                opened,
                state="closed",
                exit_intent_id=ev.payload.get("exit_intent_id"),
                exit_event_id=ev.event_id,
            )
        else:
            raise LifecycleValidationError(f"unknown paper_fill transition {transition!r}")
    return list(positions.values())

"""Stage 5 ledger-derived H7 paper-book risk accounting.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. The verified Stage-3 ledger is the
authority. The legacy CSV is a read-only reconciliation target.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
from data.cache_runner import session_close_utc, trading_days
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_board import resolve_board
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ActivationBoundaryError,
    RealStoreSession,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import canonical_json, sha256_hex


class BookValidationError(RuntimeError):
    """Ledger-derived or mirror book state is unsafe or inconsistent."""


@dataclass(frozen=True, order=True)
class BookRow:
    symbol: str
    lane: str
    opened: str
    at_risk: float
    closed: str | None
    position_id: str
    opening_fill_id: str = ""


@dataclass(frozen=True, order=True)
class Reservation:
    reservation_id: str
    symbol: str
    lane: str
    planned_fill_session: str
    decision_at_risk: float
    source_event_type: str
    decision_session: str
    accepted_action_hash: str | None = None
    board_resolution_id: str | None = None


@dataclass(frozen=True)
class BookSnapshot:
    evaluation_session: str
    risk_month: str
    rows: tuple[BookRow, ...]
    reservations: tuple[Reservation, ...]
    open_symbols: tuple[str, ...]
    open_h7c: int
    month_actual_risk: float
    month_reserved_risk: float
    sleeve_left: float
    head: str | None
    snapshot_hash: str


@dataclass(frozen=True)
class CapacityAssessment:
    allowed: bool
    failed_constraints: tuple[str, ...]
    projected_month_risk: float
    projected_open_h7c: int
    projected_underlying_occupancy: int
    expected_head: str | None
    snapshot_hash: str
    capacity_snapshot: dict


@dataclass(frozen=True)
class BoardResolutionResult:
    event_id: str
    accepted: tuple[dict, ...]
    rejected: tuple[dict, ...]
    appended: bool
    snapshot_hash: str


@dataclass(frozen=True)
class ReconciliationReport:
    verdict: str
    missing_from_mirror: tuple[tuple, ...]
    extra_in_mirror: tuple[tuple, ...]
    aggregate_mismatches: tuple[str, ...]
    pending_reservations: tuple[Reservation, ...]
    snapshot_hash: str


@dataclass(frozen=True)
class ReservationReleaseResult:
    event_id: str
    appended: bool


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


def _resolve_base(base_dir) -> Path:
    """Allow only an explicit real-session key to read/write the live book."""
    if isinstance(base_dir, RealStoreSession):
        return Path(base_dir.base_dir)
    return _synthetic_base(base_dir)


def _session(value: object, field: str = "evaluation_session") -> str:
    if not isinstance(value, str):
        raise BookValidationError(f"{field} must be YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise BookValidationError(f"{field} must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise BookValidationError(f"{field} must be canonical YYYY-MM-DD")
    return value


def _positive_number(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BookValidationError(f"{field} must be a finite positive number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise BookValidationError(f"{field} must be a finite positive number")
    return number


def _identity(row: BookRow) -> tuple:
    return (row.symbol, row.lane, row.opened, row.at_risk, row.closed or "")


def _snapshot_payload(
    session: str,
    risk_month: str,
    rows: tuple[BookRow, ...],
    reservations: tuple[Reservation, ...],
) -> dict:
    open_rows = [row for row in rows if row.closed is None]
    open_symbols = sorted(
        {row.symbol for row in open_rows} | {item.symbol for item in reservations}
    )
    open_h7c = sum(row.lane == "c" for row in open_rows) + sum(
        item.lane == "c" for item in reservations
    )
    actual = sum(row.at_risk for row in rows if row.opened.startswith(risk_month))
    reserved = sum(
        item.decision_at_risk
        for item in reservations
        if item.planned_fill_session.startswith(risk_month)
    )
    return {
        "evaluation_session": session,
        "risk_month": risk_month,
        "rows": [
            {
                "position_id": row.position_id,
                "opening_fill_id": row.opening_fill_id,
                "symbol": row.symbol,
                "lane": row.lane,
                "opened": row.opened,
                "at_risk": row.at_risk,
                "closed": row.closed,
            }
            for row in rows
        ],
        "reservations": [
            {
                "reservation_id": item.reservation_id,
                "symbol": item.symbol,
                "lane": item.lane,
                "planned_fill_session": item.planned_fill_session,
                "decision_at_risk": item.decision_at_risk,
                "source_event_type": item.source_event_type,
                "decision_session": item.decision_session,
                "accepted_action_hash": item.accepted_action_hash,
                "board_resolution_id": item.board_resolution_id,
            }
            for item in reservations
        ],
        "open_symbols": open_symbols,
        "open_h7c": open_h7c,
        "month_actual_risk": actual,
        "month_reserved_risk": reserved,
        "sleeve_left": config.H7_MONTHLY_AT_RISK - actual - reserved,
    }


def derive_book(
    *, base_dir, evaluation_session: str, risk_month: str | None = None
) -> BookSnapshot:
    """Replay verified lifecycle events through ``evaluation_session``."""
    base = _resolve_base(base_dir)
    session = _session(evaluation_session)
    month = session[:7] if risk_month is None else risk_month
    try:
        if len(month) != 7:
            raise ValueError
        date.fromisoformat(f"{month}-01")
    except (TypeError, ValueError) as exc:
        raise BookValidationError("risk_month must be canonical YYYY-MM") from exc
    events = ledger.read_events(base)
    intents: dict[str, Reservation] = {}
    intent_events: dict[str, ledger.StoredEvent] = {}
    rows: dict[str, BookRow] = {}
    exit_intents: dict[str, ledger.StoredEvent] = {}
    stage5_boards: set[str] = set()

    for event in events:
        if event.evaluation_session > session:
            continue
        if event.event_type == "board_resolution" and isinstance(
            event.payload.get("book_snapshot_hash"), str
        ):
            planned = _session(event.payload.get("planned_fill_session"), "planned_fill_session")
            if planned <= event.evaluation_session:
                raise BookValidationError("board planned fill must follow its session")
            accepted = event.payload.get("accepted")
            if not isinstance(accepted, list):
                raise BookValidationError("Stage-5 board accepted payload must be a list")
            stage5_boards.add(event.event_id)
            for item in accepted:
                if not isinstance(item, dict) or not isinstance(item.get("action"), dict):
                    raise BookValidationError("Stage-5 board has malformed acceptance")
                symbol = item.get("symbol")
                lane = item.get("lane")
                if (
                    not isinstance(symbol, str)
                    or not symbol
                    or symbol != symbol.upper()
                    or lane not in config.H7_LANE_PRIORITY
                    or item.get("session") != event.evaluation_session
                ):
                    raise BookValidationError("Stage-5 board acceptance identity is invalid")
                risk = _positive_number(
                    item["action"].get("max_loss", item["action"].get("cost")),
                    "board reservation at-risk",
                )
                reservation_id = f"{event.event_id}:{symbol}:{lane}"
                if reservation_id in intents:
                    raise BookValidationError("duplicate Stage-5 board reservation")
                intents[reservation_id] = Reservation(
                    reservation_id=reservation_id,
                    symbol=symbol,
                    lane=str(lane),
                    planned_fill_session=planned,
                    decision_at_risk=risk,
                    source_event_type="board_resolution",
                    decision_session=_session(
                        event.payload.get("decision_session", event.evaluation_session),
                        "board decision_session",
                    ),
                    accepted_action_hash=sha256_hex(canonical_json(item["action"])),
                    board_resolution_id=event.event_id,
                )
            continue
        if event.event_type == "entry_intent":
            if event.symbol is None or event.lane not in config.H7_LANE_PRIORITY:
                raise BookValidationError("entry intent has invalid symbol or lane")
            planned = _session(event.payload.get("planned_fill_session"), "planned_fill_session")
            risk = _positive_number(event.payload.get("decision_at_risk"), "decision_at_risk")
            if event.payload.get("position_id") != event.event_id:
                raise BookValidationError("entry intent position_id must equal event_id")
            if planned <= event.evaluation_session:
                raise BookValidationError("planned fill must follow the decision session")
            board_causes = stage5_boards.intersection(event.causes)
            if board_causes:
                matches = [
                    (key, item)
                    for key, item in intents.items()
                    if item.source_event_type == "board_resolution"
                    and item.board_resolution_id in board_causes
                    and item.symbol == event.symbol
                    and item.lane == event.lane
                ]
                if len(matches) != 1:
                    raise BookValidationError(
                        "entry intent does not replace exactly one board reservation"
                    )
                board_key, board_reservation = matches[0]
                action = event.payload.get("action")
                if (
                    event.payload.get("decision_session", event.evaluation_session)
                    != board_reservation.decision_session
                    or planned != board_reservation.planned_fill_session
                    or not isinstance(action, dict)
                    or sha256_hex(canonical_json(action)) != board_reservation.accepted_action_hash
                    or risk != board_reservation.decision_at_risk
                ):
                    raise BookValidationError(
                        "entry intent does not exactly match its board reservation"
                    )
                intents.pop(board_key)
            else:
                board_reservation = None
            if event.event_id in intents or event.event_id in rows:
                raise BookValidationError(f"duplicate position {event.event_id!r}")
            intents[event.event_id] = Reservation(
                reservation_id=event.event_id,
                symbol=event.symbol,
                lane=event.lane,
                planned_fill_session=planned,
                decision_at_risk=risk,
                source_event_type="entry_intent",
                decision_session=_session(
                    event.payload.get("decision_session", event.evaluation_session),
                    "entry decision_session",
                ),
                accepted_action_hash=(
                    board_reservation.accepted_action_hash
                    if board_reservation is not None
                    else None
                ),
                board_resolution_id=(
                    board_reservation.board_resolution_id if board_reservation is not None else None
                ),
            )
            intent_events[event.event_id] = event
            continue

        if (
            event.event_type == "lane_displaced"
            and event.payload.get("reason") == "intent_materialization_missing"
        ):
            reservation_id = event.payload.get("reservation_id")
            reservation = intents.get(reservation_id) if isinstance(reservation_id, str) else None
            if (
                not isinstance(reservation_id, str)
                or reservation is None
                or reservation.source_event_type != "board_resolution"
                or event.causes != [reservation.board_resolution_id]
                or event.symbol != reservation.symbol
                or event.lane != reservation.lane
                or event.evaluation_session != reservation.planned_fill_session
                or event.occurred_at_utc
                != session_close_utc(reservation.planned_fill_session).isoformat()
                or event.payload.get("planned_fill_session") != reservation.planned_fill_session
            ):
                raise BookValidationError("board reservation expiry is malformed")
            intents.pop(reservation_id)
            continue

        if event.event_type == "skip":
            intent_id = event.payload.get("entry_intent_id")
            if not isinstance(intent_id, str) or intent_id not in intents:
                raise BookValidationError("entry skip has no unresolved intent")
            if intent_id not in event.causes:
                raise BookValidationError("entry skip does not cite its intent")
            reservation = intents[intent_id]
            if (
                reservation.source_event_type != "entry_intent"
                or event.symbol != reservation.symbol
                or event.lane != reservation.lane
                or event.evaluation_session != reservation.planned_fill_session
                or not isinstance(event.payload.get("reason"), str)
                or not event.payload["reason"]
            ):
                raise BookValidationError("entry skip does not match its reservation")
            intents.pop(intent_id)
            continue

        if event.event_type == "exit_intent":
            position_id = event.payload.get("position_id")
            position = rows.get(position_id) if isinstance(position_id, str) else None
            planned = _session(
                event.payload.get("planned_fill_session"), "exit planned_fill_session"
            )
            if (
                position is None
                or position.closed is not None
                or event.symbol != position.symbol
                or event.lane != position.lane
                or event.payload.get("opening_fill_id") != position.opening_fill_id
                or position.opening_fill_id not in event.causes
                or event.payload.get("trigger_session") != event.evaluation_session
                or planned <= event.evaluation_session
                or event.event_id in exit_intents
            ):
                raise BookValidationError("exit intent is not caused by its open position")
            exit_intents[event.event_id] = event
            continue

        if event.event_type != "paper_fill":
            continue
        transition = event.payload.get("transition")
        position_id = event.payload.get("position_id")
        if not isinstance(position_id, str) or not position_id:
            raise BookValidationError("paper fill is missing position_id")
        if transition == "open":
            if event.payload.get("entry_intent_id") != position_id:
                raise BookValidationError("opening fill names the wrong entry intent")
            if position_id not in event.causes:
                raise BookValidationError("opening fill does not cite its entry intent")
            reservation = intents.pop(position_id, None)
            if reservation is None:
                raise BookValidationError(
                    f"opening fill {event.event_id!r} has no unresolved intent"
                )
            if event.symbol != reservation.symbol or event.lane != reservation.lane:
                raise BookValidationError("opening fill changes reserved symbol or lane")
            intent_event = intent_events.get(position_id)
            intent_action = intent_event.payload.get("action") if intent_event is not None else None
            opening_action = event.payload.get("action")
            intent_legs = intent_event.payload.get("legs") if intent_event is not None else None
            opening_legs = event.payload.get("legs")
            identity_keys = ("name", "expiration", "strike", "right", "side", "quantity")
            if (
                not isinstance(intent_action, dict)
                or not isinstance(opening_action, dict)
                or canonical_json(opening_action) != canonical_json(intent_action)
                or not isinstance(intent_legs, list)
                or not isinstance(opening_legs, list)
                or len(opening_legs) != len(intent_legs)
                or any(
                    not isinstance(frozen, dict)
                    or not isinstance(filled, dict)
                    or any(filled.get(key) != frozen.get(key) for key in identity_keys)
                    for frozen, filled in zip(intent_legs, opening_legs, strict=True)
                )
            ):
                raise BookValidationError(
                    "opening fill changes its entry-intent action or contracts"
                )
            opened = _session(event.evaluation_session, "opening fill session")
            payload_session = event.payload.get("fill_session")
            if (
                payload_session != opened
                or opened != reservation.planned_fill_session
                or event.payload.get("decision_session") != reservation.decision_session
            ):
                raise BookValidationError("opening fill does not match planned session")
            if position_id in rows:
                raise BookValidationError(f"position {position_id!r} opens twice")
            rows[position_id] = BookRow(
                symbol=reservation.symbol,
                lane=reservation.lane,
                opened=opened,
                at_risk=_positive_number(event.payload.get("at_risk"), "at_risk"),
                closed=None,
                position_id=position_id,
                opening_fill_id=event.event_id,
            )
        elif transition == "close":
            prior = rows.get(position_id)
            if prior is None or prior.closed is not None:
                raise BookValidationError(f"position {position_id!r} closes without one open fill")
            closed = _session(event.evaluation_session, "closing fill session")
            exit_intent_id = event.payload.get("exit_intent_id")
            exit_intent = (
                exit_intents.get(exit_intent_id) if isinstance(exit_intent_id, str) else None
            )
            if event.payload.get("fill_session") != closed:
                raise BookValidationError("closing fill payload has the wrong session")
            if (
                event.symbol != prior.symbol
                or event.lane != prior.lane
                or exit_intent is None
                or exit_intent_id not in event.causes
                or exit_intent.payload.get("position_id") != position_id
                or event.payload.get("opening_fill_id") != prior.opening_fill_id
                or closed < str(exit_intent.payload.get("planned_fill_session"))
            ):
                raise BookValidationError("closing fill changes position symbol or lane")
            if closed < prior.opened:
                raise BookValidationError("position closes before it opens")
            rows[position_id] = BookRow(
                symbol=prior.symbol,
                lane=prior.lane,
                opened=prior.opened,
                at_risk=prior.at_risk,
                closed=closed,
                position_id=prior.position_id,
                opening_fill_id=prior.opening_fill_id,
            )
        else:
            raise BookValidationError(f"unknown paper fill transition {transition!r}")

    row_key = lambda row: (
        row.symbol,
        row.lane,
        row.opened,
        row.at_risk,
        row.closed or "",
        row.position_id,
    )
    ordered_rows = tuple(sorted(rows.values(), key=row_key))
    reservations = tuple(
        sorted(
            intents.values(),
            key=lambda item: (
                item.symbol,
                item.lane,
                item.planned_fill_session,
                item.decision_at_risk,
                item.source_event_type,
                item.decision_session,
                item.reservation_id,
            ),
        )
    )
    payload = _snapshot_payload(session, month, ordered_rows, reservations)
    open_rows = [row for row in ordered_rows if row.closed is None]
    if any(
        sum(row.symbol == symbol for row in open_rows) > config.H7_MAX_OPEN_PER_UNDERLYING
        for symbol in {row.symbol for row in open_rows}
    ):
        raise BookValidationError("ledger has multiple open fills for one underlying")
    if sum(row.lane == "c" for row in open_rows) > config.H7C_MAX_CONCURRENT:
        raise BookValidationError("ledger exceeds the open lane-c basket cap")
    if payload["month_actual_risk"] > config.H7_MONTHLY_AT_RISK:
        raise BookValidationError("ledger exceeds the monthly actual-risk sleeve")
    stage5_reservations = [item for item in reservations if item.board_resolution_id is not None]
    if stage5_reservations:
        occupied_symbols = [row.symbol for row in open_rows] + [
            item.symbol for item in reservations
        ]
        if any(
            occupied_symbols.count(symbol) > config.H7_MAX_OPEN_PER_UNDERLYING
            for symbol in set(occupied_symbols)
        ):
            raise BookValidationError("Stage-5 reservations exceed underlying capacity")
        occupied_c = sum(row.lane == "c" for row in open_rows) + sum(
            item.lane == "c" for item in reservations
        )
        if occupied_c > config.H7C_MAX_CONCURRENT:
            raise BookValidationError("Stage-5 reservations exceed lane-c capacity")
        if (
            payload["month_actual_risk"] + payload["month_reserved_risk"]
            > config.H7_MONTHLY_AT_RISK
        ):
            raise BookValidationError("Stage-5 reservations exceed the monthly sleeve")
    current_head = events[-1].record_hash if events else None
    return BookSnapshot(
        evaluation_session=session,
        risk_month=month,
        rows=ordered_rows,
        reservations=reservations,
        open_symbols=tuple(payload["open_symbols"]),
        open_h7c=int(payload["open_h7c"]),
        month_actual_risk=float(payload["month_actual_risk"]),
        month_reserved_risk=float(payload["month_reserved_risk"]),
        sleeve_left=float(payload["sleeve_left"]),
        head=current_head,
        snapshot_hash=sha256_hex(canonical_json(payload)),
    )


def assess_entry_fill(
    *, base_dir, entry_intent_id: str, fill_session: str, actual_at_risk
) -> CapacityAssessment:
    """Replace one intent reservation with actual fill risk and test caps."""
    session = _session(fill_session, "fill_session")
    actual = _positive_number(actual_at_risk, "actual_at_risk")
    snapshot = derive_book(base_dir=base_dir, evaluation_session=session)
    own = next(
        (
            item
            for item in snapshot.reservations
            if item.reservation_id == entry_intent_id and item.source_event_type == "entry_intent"
        ),
        None,
    )
    if own is None:
        raise BookValidationError("entry intent has no unresolved reservation")
    if own.planned_fill_session != session:
        raise BookValidationError("entry fill session does not match reservation")

    other_reservations = tuple(
        item for item in snapshot.reservations if item.reservation_id != entry_intent_id
    )
    open_rows = tuple(row for row in snapshot.rows if row.closed is None)
    underlying_occupancy = sum(row.symbol == own.symbol for row in open_rows) + sum(
        item.symbol == own.symbol for item in other_reservations
    )
    other_c = sum(row.lane == "c" for row in open_rows) + sum(
        item.lane == "c" for item in other_reservations
    )
    projected_c = other_c + (own.lane == "c")
    month = session[:7]
    other_reserved_risk = sum(
        item.decision_at_risk
        for item in other_reservations
        if item.planned_fill_session.startswith(month)
    )
    projected_risk = snapshot.month_actual_risk + other_reserved_risk + actual
    capacity_snapshot = {
        "evaluation_session": session,
        "risk_month": month,
        "month_actual_risk": snapshot.month_actual_risk,
        "month_other_reserved_risk": other_reserved_risk,
        "sleeve_left_before_substitution": (
            config.H7_MONTHLY_AT_RISK - snapshot.month_actual_risk - other_reserved_risk
        ),
        "open_symbols_before_substitution": sorted(
            {row.symbol for row in open_rows} | {item.symbol for item in other_reservations}
        ),
        "open_h7c_before_substitution": other_c,
        "open_positions": [
            {
                "position_id": row.position_id,
                "symbol": row.symbol,
                "lane": row.lane,
                "opened": row.opened,
                "at_risk": row.at_risk,
            }
            for row in open_rows
        ],
        "other_reservations": [
            {
                "reservation_id": item.reservation_id,
                "symbol": item.symbol,
                "lane": item.lane,
                "planned_fill_session": item.planned_fill_session,
                "decision_at_risk": item.decision_at_risk,
                "source_event_type": item.source_event_type,
                "board_resolution_id": item.board_resolution_id,
            }
            for item in other_reservations
        ],
        "replaced_reservation": {
            "reservation_id": own.reservation_id,
            "symbol": own.symbol,
            "lane": own.lane,
            "planned_fill_session": own.planned_fill_session,
            "decision_at_risk": own.decision_at_risk,
            "source_event_type": own.source_event_type,
            "board_resolution_id": own.board_resolution_id,
        },
    }
    failed: list[str] = []
    if underlying_occupancy >= config.H7_MAX_OPEN_PER_UNDERLYING:
        failed.append("underlying_open_or_reserved")
    if projected_c > config.H7C_MAX_CONCURRENT:
        failed.append("h7c_basket_cap")
    if projected_risk > config.H7_MONTHLY_AT_RISK:
        failed.append("monthly_sleeve")
    return CapacityAssessment(
        allowed=not failed,
        failed_constraints=tuple(failed),
        projected_month_risk=projected_risk,
        projected_open_h7c=projected_c,
        projected_underlying_occupancy=underlying_occupancy + 1,
        expected_head=snapshot.head,
        snapshot_hash=snapshot.snapshot_hash,
        capacity_snapshot=capacity_snapshot,
    )


def _next_session(session: str) -> str:
    start = date.fromisoformat(session) + timedelta(days=1)
    sessions = trading_days(start.isoformat(), (start + timedelta(days=14)).isoformat())
    if not sessions:
        raise BookValidationError(f"no XNYS session follows {session}")
    return sessions[0]


def _board_event_id(session: str) -> str:
    return f"h7:board:{session}"


def _append_displacements(
    *,
    base: Path,
    session: str,
    board_id: str,
    rejected: list[dict],
    current_head: str | None,
    clock,
) -> str | None:
    for index, item in enumerate(rejected):
        displaced = ledger.append_event(
            {
                "schema_version": ledger.SCHEMA_VERSION,
                "event_id": (f"h7:displaced:{session}:{index}:{item['symbol']}:{item['lane']}"),
                "event_type": "lane_displaced",
                "occurred_at_utc": session_close_utc(session).isoformat(),
                "evaluation_session": session,
                "symbol": str(item["symbol"]),
                "lane": str(item["lane"]),
                "causes": [board_id],
                "payload": {"candidate": item, "reason": item["rejection"]},
            },
            base_dir=base,
            clock=clock,
            expected_head=current_head,
        )
        if displaced.appended:
            current_head = displaced.record_hash
    return current_head


def record_board_resolution(
    *,
    base_dir,
    evaluation_session: str,
    candidates: list[dict],
    source_health_id: str,
    data_gate_id: str,
    clock=None,
) -> BoardResolutionResult:
    """Resolve candidates against the ledger-derived global book."""
    base = _resolve_base(base_dir)
    session = _session(evaluation_session)
    if isinstance(base_dir, RealStoreSession):
        if base_dir.evaluation_session != session:
            raise BookValidationError(
                "RealStoreSession evaluation_session does not match board data"
            )
        decision_session = base_dir.decision_session
    else:
        decision_session = session
    events = ledger.read_events(base)
    by_id = {event.event_id: event for event in events}
    source = by_id.get(source_health_id)
    gate = by_id.get(data_gate_id)
    if source is None or source.event_type != "source_health":
        raise BookValidationError("source_health cause is missing or wrong")
    if gate is None or gate.event_type != "data_gate":
        raise BookValidationError("data_gate cause is missing or wrong")
    if source.evaluation_session != session or gate.evaluation_session != session:
        raise BookValidationError("board causes must belong to its session")
    # Receipt scope is always the full official universe. A real entry session's
    # source-health event intentionally carries only the frozen registered
    # cohort; synthetic/legacy events retain the active operational universe
    # expectation below.
    source_scope = source.payload.get("scope")
    gate_scope = gate.payload.get("scope")
    if source_scope is not None or gate_scope is not None:
        if source_scope != gate_scope or source_scope != scope_identity():
            raise BookValidationError("board causes have mismatched current scope")
        expected_symbols = (
            set(base_dir.included_symbols)
            if isinstance(base_dir, RealStoreSession)
            else set(scope_identity()["symbols"])
        )
    else:
        # Legacy synthetic rehearsals may predate the receipt contract. Keep
        # them replayable; they can never satisfy the real activation packet.
        expected_symbols = set(watch_universe()) | set(config.H7_BACKTEST_SYMBOLS)
    healthy_symbols = source.payload.get("healthy_symbols")
    if (
        not isinstance(healthy_symbols, list)
        or any(not isinstance(symbol, str) for symbol in healthy_symbols)
        or set(healthy_symbols) != expected_symbols
        or len(healthy_symbols) != len(expected_symbols)
    ):
        raise BookValidationError(
            "board resolution requires exact registered entry-cohort source health"
        )
    if gate.payload.get("whole_universe_verdict") != "GO":
        raise BookValidationError("board resolution requires a GO data gate")
    if not isinstance(candidates, list):
        raise BookValidationError("candidates must be a list")
    for item in candidates:
        if not isinstance(item, dict) or item.get("session") != session:
            raise BookValidationError("every candidate must belong to the board session")
        symbol = item.get("symbol")
        lane = item.get("lane")
        action = item.get("action")
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise BookValidationError("candidate symbol must be canonical uppercase")
        if lane not in config.H7_LANE_PRIORITY or not isinstance(action, dict):
            raise BookValidationError("candidate lane/action is invalid")
        if action.get("lane") != lane:
            raise BookValidationError("candidate action lane does not match")
        _positive_number(action.get("max_loss", action.get("cost")), "candidate at-risk")

    event_id = _board_event_id(session)
    existing_board = by_id.get(event_id)
    if existing_board is not None:
        if (
            existing_board.event_type != "board_resolution"
            or existing_board.evaluation_session != session
            or existing_board.causes != [source_health_id, data_gate_id]
            or existing_board.payload.get("decision_session", session) != decision_session
        ):
            raise BookValidationError("existing board identity or causes conflict")
        accepted = existing_board.payload.get("accepted")
        rejected = existing_board.payload.get("rejected")
        snapshot_hash = existing_board.payload.get("book_snapshot_hash")
        if (
            not isinstance(accepted, list)
            or not isinstance(rejected, list)
            or not isinstance(snapshot_hash, str)
        ):
            raise BookValidationError("existing Stage-5 board payload is malformed")
        original_rejected = [
            {key: value for key, value in item.items() if key != "rejection"}
            for item in rejected
            if isinstance(item, dict)
        ]
        supplied = sorted(canonical_json(item) for item in candidates)
        recorded = sorted(canonical_json(item) for item in [*accepted, *original_rejected])
        if len(original_rejected) != len(rejected) or supplied != recorded:
            raise BookValidationError("conflicting rerun changed board candidates")
        _append_displacements(
            base=base,
            session=session,
            board_id=event_id,
            rejected=rejected,
            current_head=events[-1].record_hash,
            clock=clock,
        )
        return BoardResolutionResult(
            event_id=event_id,
            accepted=tuple(accepted),
            rejected=tuple(rejected),
            appended=False,
            snapshot_hash=snapshot_hash,
        )

    planned_fill_session = _next_session(decision_session)
    snapshot = derive_book(
        base_dir=base_dir,
        evaluation_session=session,
        risk_month=planned_fill_session[:7],
    )
    try:
        accepted, rejected = resolve_board(
            candidates,
            open_h7c=snapshot.open_h7c,
            sleeve_left=snapshot.sleeve_left,
            open_symbols=snapshot.open_symbols,
        )
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        raise BookValidationError(f"malformed board candidate: {exc}") from exc
    accepted = sorted(
        accepted,
        key=lambda item: canonical_json(item),
    )
    rejected = sorted(
        rejected,
        key=lambda item: canonical_json(item),
    )
    payload = {
        "accepted": accepted,
        "rejected": rejected,
        "decision_session": decision_session,
        "book_snapshot_hash": snapshot.snapshot_hash,
        "planned_fill_session": planned_fill_session,
        "risk_month": snapshot.risk_month,
        "open_symbols": list(snapshot.open_symbols),
        "open_h7c": snapshot.open_h7c,
        "month_actual_risk": snapshot.month_actual_risk,
        "month_reserved_risk": snapshot.month_reserved_risk,
        "sleeve_left": snapshot.sleeve_left,
        "limits": {
            "monthly_at_risk": config.H7_MONTHLY_AT_RISK,
            "h7c_max_concurrent": config.H7C_MAX_CONCURRENT,
            "max_open_per_underlying": config.H7_MAX_OPEN_PER_UNDERLYING,
        },
        "scope": scope_identity() if source_scope is not None else None,
    }
    result = ledger.append_event(
        {
            "schema_version": ledger.SCHEMA_VERSION,
            "event_id": event_id,
            "event_type": "board_resolution",
            "occurred_at_utc": session_close_utc(decision_session).isoformat(),
            "evaluation_session": session,
            "symbol": None,
            "lane": None,
            "causes": [source_health_id, data_gate_id],
            "payload": payload,
        },
        base_dir=base,
        clock=clock,
        expected_head=snapshot.head,
    )
    current_head = result.record_hash if result.appended else ledger.verify(base).head
    _append_displacements(
        base=base,
        session=session,
        board_id=event_id,
        rejected=rejected,
        current_head=current_head,
        clock=clock,
    )
    return BoardResolutionResult(
        event_id=event_id,
        accepted=tuple(accepted),
        rejected=tuple(rejected),
        appended=result.appended,
        snapshot_hash=snapshot.snapshot_hash,
    )


def expire_unmaterialized_reservation(
    *, base_dir, board_resolution_id: str, symbol: str, lane: str, clock=None
) -> ReservationReleaseResult:
    """Release a board reservation only after its planned-fill close."""
    base = _synthetic_base(base_dir)
    if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
        raise BookValidationError("reservation symbol must be canonical uppercase")
    if lane not in config.H7_LANE_PRIORITY:
        raise BookValidationError("reservation lane is invalid")
    events = ledger.read_events(base)
    by_id = {event.event_id: event for event in events}
    board = by_id.get(board_resolution_id)
    if (
        board is None
        or board.event_type != "board_resolution"
        or not isinstance(board.payload.get("book_snapshot_hash"), str)
    ):
        raise BookValidationError("Stage-5 board reservation is missing")
    planned = _session(board.payload.get("planned_fill_session"), "planned_fill_session")
    reservation_id = f"{board_resolution_id}:{symbol}:{lane}"
    event_id = f"h7:reservation-expiry:{board_resolution_id}:{symbol}:{lane}"
    existing = by_id.get(event_id)
    if existing is not None:
        if (
            existing.event_type != "lane_displaced"
            or existing.symbol != symbol
            or existing.lane != lane
            or existing.causes != [board_resolution_id]
            or existing.evaluation_session != planned
            or existing.occurred_at_utc != session_close_utc(planned).isoformat()
            or existing.payload.get("reservation_id") != reservation_id
            or existing.payload.get("reason") != "intent_materialization_missing"
            or existing.payload.get("planned_fill_session") != planned
            or not isinstance(existing.payload.get("book_snapshot_hash"), str)
        ):
            raise BookValidationError("reservation expiry identity conflicts")
        return ReservationReleaseResult(event_id=event_id, appended=False)

    snapshot = derive_book(base_dir=base, evaluation_session=planned)
    reservation = next(
        (
            item
            for item in snapshot.reservations
            if item.reservation_id == reservation_id
            and item.source_event_type == "board_resolution"
        ),
        None,
    )
    if reservation is None:
        raise BookValidationError("board reservation already materialized or is absent")
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise BookValidationError("clock must return a UTC datetime")
    cutoff = session_close_utc(planned)
    if now < cutoff:
        raise BookValidationError("board reservation cannot expire before fill close")
    result = ledger.append_event(
        {
            "schema_version": ledger.SCHEMA_VERSION,
            "event_id": event_id,
            "event_type": "lane_displaced",
            "occurred_at_utc": cutoff.isoformat(),
            "evaluation_session": planned,
            "symbol": symbol,
            "lane": lane,
            "causes": [board_resolution_id],
            "payload": {
                "reservation_id": reservation_id,
                "reason": "intent_materialization_missing",
                "planned_fill_session": planned,
                "book_snapshot_hash": snapshot.snapshot_hash,
            },
        },
        base_dir=base,
        clock=lambda: now,
        expected_head=snapshot.head,
    )
    return ReservationReleaseResult(event_id=event_id, appended=result.appended)


_MIRROR_COLUMNS = ("symbol", "lane", "opened", "at_risk", "closed")


def _read_mirror(path: Path, session: str) -> tuple[BookRow, ...]:
    rows: list[BookRow] = []
    seen: set[tuple[str, str, str]] = set()
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != _MIRROR_COLUMNS:
                raise BookValidationError(f"mirror header {reader.fieldnames} != {_MIRROR_COLUMNS}")
            for line, raw in enumerate(reader, start=2):
                if None in raw:
                    raise BookValidationError(f"mirror line {line}: unexpected extra column")
                symbol = (raw["symbol"] or "").strip()
                lane = (raw["lane"] or "").strip().lower()
                opened = _session((raw["opened"] or "").strip(), "opened")
                closed_text = (raw["closed"] or "").strip()
                closed = _session(closed_text, "closed") if closed_text else None
                if not symbol or symbol != symbol.upper():
                    raise BookValidationError(f"mirror line {line}: invalid symbol")
                if lane not in config.H7_LANE_PRIORITY:
                    raise BookValidationError(f"mirror line {line}: invalid lane")
                if opened > session or (closed is not None and closed > session):
                    raise BookValidationError(f"mirror line {line}: future-dated row")
                if closed is not None and closed < opened:
                    raise BookValidationError(f"mirror line {line}: close before open")
                try:
                    risk = float(raw["at_risk"])
                except (TypeError, ValueError) as exc:
                    raise BookValidationError(f"mirror line {line}: invalid at_risk") from exc
                risk = _positive_number(risk, "mirror at_risk")
                key = (symbol, lane, opened)
                if key in seen:
                    raise BookValidationError(f"mirror line {line}: duplicate row")
                seen.add(key)
                rows.append(BookRow(symbol, lane, opened, risk, closed, f"mirror:{line}"))
    except BookValidationError:
        raise
    except OSError as exc:
        raise BookValidationError(f"cannot read mirror {path}: {exc}") from exc
    return tuple(
        sorted(
            rows,
            key=lambda row: (
                row.symbol,
                row.lane,
                row.opened,
                row.at_risk,
                row.closed or "",
            ),
        )
    )


def reconcile_position_mirror(
    *, base_dir, evaluation_session: str, mirror_path
) -> ReconciliationReport:
    """Compare the legacy CSV with ledger rows without modifying either."""
    session = _session(evaluation_session)
    snapshot = derive_book(base_dir=base_dir, evaluation_session=session)
    mirror_rows = _read_mirror(Path(mirror_path), session)
    ledger_identities = {_identity(row) for row in snapshot.rows}
    mirror_identities = {_identity(row) for row in mirror_rows}
    missing = tuple(sorted(ledger_identities - mirror_identities))
    extra = tuple(sorted(mirror_identities - ledger_identities))

    mirror_open = tuple(sorted({row.symbol for row in mirror_rows if row.closed is None}))
    mirror_c = sum(row.lane == "c" and row.closed is None for row in mirror_rows)
    mirror_spent = sum(row.at_risk for row in mirror_rows if row.opened.startswith(session[:7]))
    mismatches: list[str] = []
    ledger_open_from_rows = tuple(
        sorted({row.symbol for row in snapshot.rows if row.closed is None})
    )
    ledger_c_from_rows = sum(row.lane == "c" and row.closed is None for row in snapshot.rows)
    if mirror_open != ledger_open_from_rows:
        mismatches.append("open_symbols")
    if mirror_c != ledger_c_from_rows:
        mismatches.append("open_h7c")
    if mirror_spent != snapshot.month_actual_risk:
        mismatches.append("month_spent")
    verdict = "MATCH" if not missing and not extra and not mismatches else "MISMATCH"
    return ReconciliationReport(
        verdict=verdict,
        missing_from_mirror=missing,
        extra_in_mirror=extra,
        aggregate_mismatches=tuple(mismatches),
        pending_reservations=snapshot.reservations,
        snapshot_hash=snapshot.snapshot_hash,
    )

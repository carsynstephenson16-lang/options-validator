"""Stage 6 H7 forward-window scoring.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. This is a pure read over an explicit
synthetic Stage-3 ledger. It does not register a window, append an event, or
provide a CLI. Stage 8 remains the only activation gate.
"""

from __future__ import annotations

import math
import warnings
from datetime import date
from pathlib import Path

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from metrics import scoreboard
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_forward_book import derive_book
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ActivationBoundaryError,
)
from research.experiments import json_safe


class ScoringValidationError(RuntimeError):
    """A window, event, or trade field cannot support an honest score."""


class ScoringIncompleteError(ScoringValidationError):
    """An included opening fill has not reached one valid closing fill."""


VERDICTS = ("SURVIVED", "REJECTED", "INCONCLUSIVE")
ALLOWED_STRUCTURES_BY_LANE = {
    "a": frozenset({"long_call", "call_debit_spread"}),
    "b": frozenset({"long_call", "call_debit_spread"}),
    "c": frozenset({"bull_put_spread"}),
}


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


def _session(value, field: str) -> str:
    if not isinstance(value, str):
        raise ScoringValidationError(f"{field} must be canonical YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ScoringValidationError(f"{field} must be canonical YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ScoringValidationError(f"{field} must be canonical YYYY-MM-DD")
    return value


def _finite(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoringValidationError(f"{field} must be finite numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ScoringValidationError(f"{field} must be finite numeric")
    return number


def _positive(value, field: str) -> float:
    number = _finite(value, field)
    if number <= 0:
        raise ScoringValidationError(f"{field} must be positive")
    return number


def _nonnegative(value, field: str) -> float:
    number = _finite(value, field)
    if number < 0:
        raise ScoringValidationError(f"{field} must be non-negative")
    return number


def map_forward_verdict(board: dict, min_losses_for_verdict: int) -> tuple[str, str]:
    """Map the dependence-aware scoreboard to the frozen three-word result."""
    if (
        isinstance(min_losses_for_verdict, bool)
        or not isinstance(min_losses_for_verdict, int)
        or min_losses_for_verdict < 0
    ):
        raise ScoringValidationError("min_losses_for_verdict must be a non-negative integer")
    if not isinstance(board, dict):
        raise ScoringValidationError("scoreboard must be an object")
    losses = board.get("n_losses")
    if isinstance(losses, bool) or not isinstance(losses, int) or losses < 0:
        raise ScoringValidationError("scoreboard n_losses is invalid")
    raw_verdict = board.get("verdict")
    if not isinstance(raw_verdict, str):
        raise ScoringValidationError("scoreboard verdict is invalid")
    if losses < min_losses_for_verdict:
        return "INCONCLUSIVE", "insufficient_losses"
    if raw_verdict.startswith("INSUFFICIENT SAMPLE"):
        return "INCONCLUSIVE", "insufficient_cohorts"
    ci = board.get("expectancy_CI90")
    if not isinstance(ci, (list, tuple)) or len(ci) != 2:
        raise ScoringValidationError("scoreboard CI90 is invalid")
    lo = _finite(ci[0], "scoreboard CI90 lower")
    hi = _finite(ci[1], "scoreboard CI90 upper")
    if lo > hi:
        raise ScoringValidationError("scoreboard CI90 is reversed")
    if hi < 0:
        return "REJECTED", "ci_below_zero"
    if lo > 0:
        return "SURVIVED", "ci_above_zero"
    return "INCONCLUSIVE", "no_edge"


def _score_group(trades: list[dict], label: str, min_losses_for_verdict: int) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        raw = scoreboard(trades, label=label)
    verdict, reason = map_forward_verdict(raw, min_losses_for_verdict)
    safe = json_safe(raw)
    return {
        "verdict": verdict,
        "reason": reason,
        "scoreboard": safe,
        "mean_underlying_return": (
            sum(float(trade["underlying_return"]) for trade in trades) / len(trades)
            if trades
            else None
        ),
        "note": (
            "SURVIVED is not approval, validation, live authorization, or a "
            "claim of future profitability"
        ),
    }


def _fill_price(leg: dict, label: str) -> float:
    bid = _nonnegative(leg.get("raw_bid"), f"{label} raw bid")
    ask = _nonnegative(leg.get("raw_ask"), f"{label} raw ask")
    if bid > ask:
        raise ScoringValidationError(f"{label} quote is crossed")
    open_interest = leg.get("open_interest")
    if isinstance(open_interest, bool) or not isinstance(open_interest, int) or open_interest < 0:
        raise ScoringValidationError(f"{label} open interest is invalid")
    delta = _finite(leg.get("raw_delta"), f"{label} raw delta")
    if not -1 <= delta <= 1:
        raise ScoringValidationError(f"{label} raw delta is invalid")
    if not quote_valid(bid, ask) or not passes_liquidity(open_interest, bid, ask):
        raise ScoringValidationError(f"{label} quote did not pass Stage-4 liquidity")
    side = leg.get("side")
    if side == "buy":
        expected = adverse_buy(ask)
    elif side == "sell":
        expected = adverse_sell(bid)
    else:
        raise ScoringValidationError(f"{label} side is invalid")
    recorded = _nonnegative(leg.get("fill_price"), f"{label} fill price")
    if not math.isclose(recorded, expected, abs_tol=1e-9):
        raise ScoringValidationError(f"{label} fill price is not canonical")
    return recorded


def _reconstruct_economics(opening, closing, structure: str) -> tuple[float, float, float]:
    action = opening.payload.get("action")
    if not isinstance(action, dict):
        raise ScoringValidationError("opening fill has no frozen action")
    if action.get("kind") != structure or action.get("lane") != opening.lane:
        raise ScoringValidationError("opening action changes structure or lane")
    expiration = _session(action.get("expiration"), "action expiration")
    if structure == "long_call":
        expected = [("long", action.get("strike"), "C", "buy")]
    elif structure == "call_debit_spread":
        expected = [
            ("long", action.get("long_strike"), "C", "buy"),
            ("short", action.get("short_strike"), "C", "sell"),
        ]
    else:
        expected = [
            ("short", action.get("short_strike"), "P", "sell"),
            ("long", action.get("long_strike"), "P", "buy"),
        ]
    opening_legs = opening.payload.get("legs")
    closing_legs = closing.payload.get("legs")
    if not isinstance(opening_legs, list) or len(opening_legs) != len(expected):
        raise ScoringValidationError("opening fill legs do not match structure")
    if not isinstance(closing_legs, list) or len(closing_legs) != len(expected):
        raise ScoringValidationError("closing fill legs do not match opening fill")

    entry_net = 0.0
    exit_net = 0.0
    for index, (name, raw_strike, right, side) in enumerate(expected):
        strike = _positive(raw_strike, f"{name} action strike")
        opening_leg = opening_legs[index]
        closing_leg = closing_legs[index]
        if not isinstance(opening_leg, dict) or not isinstance(closing_leg, dict):
            raise ScoringValidationError("fill leg must be an object")
        identity = {
            "name": name,
            "expiration": expiration,
            "strike": strike,
            "right": right,
            "quantity": config.H7_FORWARD_CONTRACTS,
        }
        for key, value in identity.items():
            if opening_leg.get(key) != value or closing_leg.get(key) != value:
                raise ScoringValidationError("fill changes frozen contract identity")
        if opening_leg.get("side") != side:
            raise ScoringValidationError("opening fill changes frozen contract side")
        close_side = "sell" if side == "buy" else "buy"
        if closing_leg.get("side") != close_side:
            raise ScoringValidationError("closing fill is not the opposite side")
        entry_price = _fill_price(opening_leg, f"opening {name}")
        exit_price = _fill_price(closing_leg, f"closing {name}")
        entry_net += entry_price if side == "buy" else -entry_price
        exit_net += exit_price if close_side == "sell" else -exit_price

    recorded_entry = _finite(opening.payload.get("net_debit_per_share"), "entry net debit")
    recorded_exit = _finite(
        closing.payload.get("net_close_credit_per_share"), "exit net close credit"
    )
    if not math.isclose(recorded_entry, entry_net, abs_tol=1e-9):
        raise ScoringValidationError("entry net debit is inconsistent with fill legs")
    if not math.isclose(recorded_exit, exit_net, abs_tol=1e-9):
        raise ScoringValidationError("exit net credit is inconsistent with fill legs")

    quantity = config.H7_FORWARD_CONTRACTS
    round_trip_commission = len(expected) * 2 * config.COMMISSION_PER_CONTRACT * quantity
    if structure == "long_call":
        if entry_net <= 0:
            raise ScoringValidationError("long-call debit must be positive")
        expected_at_risk = entry_net * 100 * quantity + round_trip_commission
    else:
        width = _positive(action.get("short_strike"), "short strike") - _positive(
            action.get("long_strike"), "long strike"
        )
        if width <= 0:
            raise ScoringValidationError("vertical width must be positive")
        if structure == "call_debit_spread":
            if not 0 < entry_net <= width:
                raise ScoringValidationError("call-spread debit is invalid")
            expected_at_risk = entry_net * 100 * quantity + round_trip_commission
        else:
            credit = -entry_net
            if not 0 < credit < width:
                raise ScoringValidationError("put-spread credit is invalid")
            if credit < config.H7C_CREDIT_FLOOR_FRAC * width:
                raise ScoringValidationError("put-spread credit is below frozen floor")
            expected_at_risk = (width - credit) * 100 * quantity + round_trip_commission
    recorded_at_risk = _positive(opening.payload.get("at_risk"), "actual at-risk")
    if not math.isclose(recorded_at_risk, expected_at_risk, abs_tol=1e-9):
        raise ScoringValidationError("actual at-risk is inconsistent with fill legs")
    return entry_net, exit_net, recorded_at_risk


def _trade_from_fills(opening, closing) -> dict:
    position_id = opening.payload.get("position_id")
    if not isinstance(position_id, str) or not position_id:
        raise ScoringValidationError("opening fill has no position_id")
    if closing.payload.get("position_id") != position_id:
        raise ScoringValidationError("closing fill names the wrong position")
    decision = _session(opening.payload.get("decision_session"), "decision_session")
    opened = _session(opening.evaluation_session, "entry fill session")
    closed = _session(closing.evaluation_session, "exit fill session")
    if opening.payload.get("fill_session") != opened:
        raise ScoringValidationError("opening fill payload has the wrong session")
    if closing.payload.get("fill_session") != closed or closed < opened:
        raise ScoringValidationError("closing fill payload has the wrong session")
    if opening.symbol is None or opening.lane not in config.H7_LANE_PRIORITY:
        raise ScoringValidationError("opening fill has invalid symbol/lane")
    if closing.symbol != opening.symbol or closing.lane != opening.lane:
        raise ScoringValidationError("closing fill changes symbol/lane")
    for event, label in ((opening, "opening"), (closing, "closing")):
        identity = event.payload.get("closes_identity")
        if not isinstance(identity, str) or not identity:
            raise ScoringValidationError(f"{label} fill has no closes_identity")
    structure = opening.payload.get("structure")
    if structure not in ALLOWED_STRUCTURES_BY_LANE[opening.lane]:
        raise ScoringValidationError("opening fill has invalid structure")
    reason = closing.payload.get("primary_reason")
    if not isinstance(reason, str) or not reason:
        raise ScoringValidationError("closing fill has no primary_reason")

    if closing.payload.get("structure") != structure:
        raise ScoringValidationError("closing fill changes structure")
    quantity = config.H7_FORWARD_CONTRACTS
    entry_net, exit_net, at_risk = _reconstruct_economics(opening, closing, structure)
    entry_commission = _nonnegative(opening.payload.get("commission"), "entry commission")
    exit_commission = _nonnegative(closing.payload.get("commission"), "exit commission")
    expected_commission = len(opening.payload["legs"]) * quantity * config.COMMISSION_PER_CONTRACT
    if not math.isclose(entry_commission, expected_commission, abs_tol=1e-9):
        raise ScoringValidationError("entry commission does not match frozen cost")
    if not math.isclose(exit_commission, expected_commission, abs_tol=1e-9):
        raise ScoringValidationError("exit commission does not match frozen cost")
    entry_underlying = _positive(opening.payload.get("underlying_close"), "entry underlying close")
    exit_underlying = _positive(closing.payload.get("underlying_close"), "exit underlying close")
    for event, fill_session, label in (
        (opening, opened, "entry"),
        (closing, closed, "exit"),
    ):
        if event.payload.get("underlying_close_session") != fill_session:
            raise ScoringValidationError(
                f"{label} underlying close is not bound to the fill session"
            )
        if event.payload.get("underlying_close_identity") != event.payload.get("closes_identity"):
            raise ScoringValidationError(f"{label} underlying close has the wrong source identity")
    pnl = (exit_net - entry_net) * 100 * quantity - entry_commission - exit_commission
    if not math.isfinite(pnl):
        raise ScoringValidationError("reconstructed pnl is non-finite")
    return {
        "position_id": position_id,
        "entry_event_id": opening.event_id,
        "exit_event_id": closing.event_id,
        "decision_session": decision,
        "entry_date": opened,
        "exit_date": closed,
        "symbol": opening.symbol,
        "lane": opening.lane,
        "structure": structure,
        "exit_reason": reason,
        "pnl": pnl,
        "capital_at_risk": at_risk,
        "economic_max_loss": at_risk,
        "entry_commission": entry_commission,
        "exit_commission": exit_commission,
        "underlying_entry_close": entry_underlying,
        "underlying_exit_close": exit_underlying,
        "underlying_move": exit_underlying - entry_underlying,
        "underlying_return": exit_underlying / entry_underlying - 1,
    }


def score_forward_window(*, base_dir, window_start: str, window_end: str) -> dict:
    """Score every fully closed fill decided inside the inclusive window."""
    base = _synthetic_base(base_dir)
    start = _session(window_start, "window_start")
    end = _session(window_end, "window_end")
    if start > end:
        raise ScoringValidationError("window_start must not follow window_end")
    events = ledger.read_events(base)
    registrations = [event for event in events if event.event_type == "window_registration"]
    if len(registrations) != 1:
        raise ScoringValidationError("scoring requires exactly one window_registration event")
    registration = registrations[0]
    try:
        registered_window = registration.payload["window"]
        frozen = registration.payload["frozen"]
        stage_bar = frozen["stage456_parameters"]["MIN_LOSSES_FOR_VERDICT"]
        scorer_bar = frozen["scorer"]["min_losses_for_verdict"]
    except (KeyError, TypeError) as exc:
        raise ScoringValidationError("window registration loss bar is malformed") from exc
    if (
        registered_window.get("start_decision_session") != start
        or registered_window.get("final_decision_session") != end
    ):
        raise ScoringValidationError("requested scoring window disagrees with window_registration")
    if (
        isinstance(stage_bar, bool)
        or not isinstance(stage_bar, int)
        or stage_bar < 0
        or scorer_bar != stage_bar
    ):
        raise ScoringValidationError("window registration loss bar is malformed or inconsistent")
    min_losses_for_verdict = stage_bar
    as_of = max([end, *(event.evaluation_session for event in events)])
    snapshot = derive_book(base_dir=base, evaluation_session=as_of)
    unresolved = [
        reservation
        for reservation in snapshot.reservations
        if start <= reservation.decision_session <= end
    ]
    if unresolved:
        identities = ", ".join(item.reservation_id for item in unresolved)
        raise ScoringIncompleteError(f"included decisions remain unresolved: {identities}")
    rows = {row.position_id: row for row in snapshot.rows}
    openings = [
        event
        for event in events
        if event.event_type == "paper_fill" and event.payload.get("transition") == "open"
    ]
    closes: dict[str, ledger.StoredEvent] = {}
    for event in events:
        if event.event_type != "paper_fill" or event.payload.get("transition") != "close":
            continue
        position_id = event.payload.get("position_id")
        if not isinstance(position_id, str) or position_id in closes:
            raise ScoringValidationError("position has invalid or duplicate closing fill")
        closes[position_id] = event

    trades: list[dict] = []
    for opening in openings:
        decision = _session(opening.payload.get("decision_session"), "decision_session")
        if not start <= decision <= end:
            continue
        position_id = opening.payload.get("position_id")
        if not isinstance(position_id, str):
            raise ScoringValidationError("opening fill has no position_id")
        row = rows.get(position_id)
        if row is None or row.closed is None:
            raise ScoringIncompleteError(f"included position {position_id!r} is not fully closed")
        closing = closes.get(position_id)
        if closing is None:
            raise ScoringIncompleteError(f"included position {position_id!r} has no closing fill")
        trades.append(_trade_from_fills(opening, closing))
    trades.sort(
        key=lambda trade: (
            trade["entry_date"],
            trade["symbol"],
            trade["lane"],
            trade["position_id"],
        )
    )

    overall = _score_group(trades, "H7 forward paper overall", min_losses_for_verdict)
    lanes = {
        lane: _score_group(
            [trade for trade in trades if trade["lane"] == lane],
            f"H7{lane} forward paper",
            min_losses_for_verdict,
        )
        for lane in config.H7_LANE_PRIORITY
    }
    return {
        "schema_version": 1,
        "window_start": start,
        "window_end": end,
        "ledger_head": events[-1].record_hash if events else None,
        "n_trades": len(trades),
        "trades": trades,
        "overall": overall,
        "lanes": lanes,
        "frozen": {
            "min_losses_for_verdict": min_losses_for_verdict,
            "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
            "forward_contracts": config.H7_FORWARD_CONTRACTS,
            "verdicts": list(VERDICTS),
        },
    }

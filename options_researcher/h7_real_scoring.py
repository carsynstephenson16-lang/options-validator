"""Receipt-gated real-store H7 scoring wrapper (BUILD-ONLY; INACTIVE).

The registered scorer remains synthetic-only and byte-identical.  This module
validates the real ledger, invokes that scorer through a temporary injected
store for market-quote closes, values pre-registered expiration settlements
without fabricated quotes, and can publish exactly one immutable result only
after the independent-review and owner-PASS facts exist.
"""

from __future__ import annotations

import math
import tempfile
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
from data.cache_runner import session_close_utc, trading_days
from metrics import scoreboard
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_forward_scoring as frozen_scoring
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from research.experiments import json_safe
from research.hashing import (
    canonical_json,
    config_hash,
    cost_model_hash,
    sha256_file,
)
from research.receipts import (
    load_receipt,
    make_receipt,
    write_immutable_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FACTS_PATH = REPO_ROOT / "ledger" / "facts.log"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "reports" / "h7_forward_scoring"
SPEC_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-22-h7-real-exit-scoring-SPEC.md"
)
REVIEW_PASS_TAG = "H7_REAL_EXIT_SCORING_INDEPENDENT_REVIEW_PASS"
OWNER_PASS_TAG = "H7_REAL_EXIT_SCORING_OWNER_PASS"

_REAL_SCORING_AUTHORITY_TOKEN = object()


class RealScoringRefused(RuntimeError):
    """The real scoring authority, state, or immutable result failed closed."""


class RealScoringIncomplete(RealScoringRefused):
    """The registered window is not yet eligible for its one final score."""


@dataclass(frozen=True)
class RealScoringSession:
    base_dir: Path
    registration_event_id: str
    registration_record_hash: str
    window_start: str
    window_end: str
    scope_id: str
    scope_hash: str
    included: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]
    artifact_path: Path
    facts_path: Path
    spec_sha256: str
    _authority_token: object


@dataclass(frozen=True)
class ScoringFinalizeResult:
    event_id: str
    artifact_path: Path
    artifact_hash: str
    appended: bool
    result: dict


def _refuse(detail: str, exc: Exception | None = None) -> RealScoringRefused:
    if exc is None:
        return RealScoringRefused(detail)
    return RealScoringRefused(f"{detail}: {type(exc).__name__}: {exc}")


def _utc_now(now: datetime | None) -> datetime:
    stamp = datetime.now(timezone.utc) if now is None else now
    if (
        not isinstance(stamp, datetime)
        or stamp.tzinfo is None
        or stamp.utcoffset() != timedelta(0)
    ):
        raise RealScoringRefused("now must be a UTC datetime")
    return stamp


def _registration(base: Path) -> tuple[ledger.StoredEvent, list[ledger.StoredEvent]]:
    try:
        verification = ledger.verify(base)
        events = ledger.read_events(base)
    except (ledger.LedgerError, OSError) as exc:
        raise _refuse("real forward ledger is unavailable", exc) from exc
    if verification.empty or not events:
        raise RealScoringRefused("real forward ledger has no window registration")
    registration = events[0]
    if registration.event_type != "window_registration" or registration.seq != 0:
        raise RealScoringRefused("real forward ledger seq 0 is not window_registration")
    return registration, events


def _registered_identity(registration: ledger.StoredEvent) -> dict:
    payload = registration.payload
    try:
        window = payload["window"]
        start = window["start_decision_session"]
        end = window["final_decision_session"]
        frozen = payload["frozen"]
        scorer = frozen["scorer"]
        stage = frozen["stage456_parameters"]
        universe = payload["universe"]
        included = universe["included"]
        excluded = universe["excluded"]
    except (KeyError, TypeError) as exc:
        raise _refuse("window registration scoring identity is malformed", exc) from exc
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except (TypeError, ValueError) as exc:
        raise _refuse("registered scoring window is malformed", exc) from exc
    if (
        start_date.isoformat() != start
        or end_date.isoformat() != end
        or start_date > end_date
    ):
        raise RealScoringRefused("registered scoring window is not canonical")
    scope = scope_identity()
    if (
        universe.get("scope_id") != scope["scope_id"]
        or universe.get("scope_hash") != scope["scope_hash"]
        or not isinstance(included, list)
        or not included
        or len(set(included)) != len(included)
        or any(not isinstance(symbol, str) for symbol in included)
        or not isinstance(excluded, list)
    ):
        raise RealScoringRefused("registered cohort identity is stale or malformed")
    excluded_pairs: list[tuple[str, str]] = []
    for row in excluded:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("symbol"), str)
            or not isinstance(row.get("reason"), str)
        ):
            raise RealScoringRefused("registered excluded cohort is malformed")
        excluded_pairs.append((row["symbol"], row["reason"]))
    if set(included) & {symbol for symbol, _ in excluded_pairs}:
        raise RealScoringRefused("registered cohort both includes and excludes a name")
    expected = {
        "config_hash": config_hash(),
        "cost_model_hash": cost_model_hash(),
        "module": "options_researcher.h7_forward_scoring",
        "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
        "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
        "forward_contracts": config.H7_FORWARD_CONTRACTS,
    }
    actual = {
        "config_hash": frozen.get("config_hash"),
        "cost_model_hash": frozen.get("cost_model_hash"),
        "module": scorer.get("module"),
        "bootstrap_samples": scorer.get("bootstrap_samples"),
        "min_losses_for_verdict": scorer.get("min_losses_for_verdict"),
        "forward_contracts": stage.get("H7_FORWARD_CONTRACTS"),
    }
    if actual != expected:
        raise RealScoringRefused(
            f"registered scorer/config/cost identity changed: {actual!r} != {expected!r}"
        )
    return {
        "window_start": start,
        "window_end": end,
        "scope": scope,
        "included": tuple(included),
        "excluded": tuple(excluded_pairs),
    }


def open_real_scoring_session(
    *,
    base_dir: Path = REAL_FORWARD_STORE,
    facts_path: Path = DEFAULT_FACTS_PATH,
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
) -> RealScoringSession:
    """Create read authority; finalization gates are rechecked at publication."""
    base = Path(base_dir)
    registration, _ = _registration(base)
    identity = _registered_identity(registration)
    scope = identity["scope"]
    end = str(identity["window_end"])
    return RealScoringSession(
        base_dir=base,
        registration_event_id=registration.event_id,
        registration_record_hash=registration.record_hash,
        window_start=str(identity["window_start"]),
        window_end=end,
        scope_id=str(scope["scope_id"]),
        scope_hash=str(scope["scope_hash"]),
        included=identity["included"],
        excluded=identity["excluded"],
        artifact_path=Path(artifact_root) / str(scope["scope_id"]) / f"{end}.json",
        facts_path=Path(facts_path),
        spec_sha256=sha256_file(SPEC_PATH),
        _authority_token=_REAL_SCORING_AUTHORITY_TOKEN,
    )


def _revalidate(session: RealScoringSession) -> list[ledger.StoredEvent]:
    if (
        not isinstance(session, RealScoringSession)
        or session._authority_token is not _REAL_SCORING_AUTHORITY_TOKEN
    ):
        raise RealScoringRefused(
            "real scoring requires factory-issued RealScoringSession authority"
        )
    registration, events = _registration(session.base_dir)
    identity = _registered_identity(registration)
    if (
        registration.event_id != session.registration_event_id
        or registration.record_hash != session.registration_record_hash
        or identity["window_start"] != session.window_start
        or identity["window_end"] != session.window_end
        or identity["included"] != session.included
        or identity["excluded"] != session.excluded
        or sha256_file(SPEC_PATH) != session.spec_sha256
    ):
        raise RealScoringRefused("real scoring registration or spec identity changed")
    return events


def _decision(event: ledger.StoredEvent) -> str:
    value = event.payload.get("decision_session", event.evaluation_session)
    if not isinstance(value, str):
        raise RealScoringRefused(f"event {event.event_id} has no decision session")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise _refuse(f"event {event.event_id} decision session is invalid", exc) from exc
    if parsed.isoformat() != value:
        raise RealScoringRefused(
            f"event {event.event_id} decision session is not canonical"
        )
    return value


def _completed_pairs(
    session: RealScoringSession, events: list[ledger.StoredEvent]
) -> list[tuple[ledger.StoredEvent, ledger.StoredEvent]]:
    openings_by_intent: dict[str, list[ledger.StoredEvent]] = {}
    skips_by_intent: dict[str, list[ledger.StoredEvent]] = {}
    closes_by_position: dict[str, list[ledger.StoredEvent]] = {}
    for event in events:
        if event.event_type == "paper_fill":
            transition = event.payload.get("transition")
            if transition == "open":
                intent_id = event.payload.get("entry_intent_id")
                if not isinstance(intent_id, str):
                    raise RealScoringRefused("opening fill has no entry intent")
                openings_by_intent.setdefault(intent_id, []).append(event)
            elif transition == "close":
                position_id = event.payload.get("position_id")
                if not isinstance(position_id, str):
                    raise RealScoringRefused("closing fill has no position id")
                closes_by_position.setdefault(position_id, []).append(event)
        elif event.event_type == "skip":
            intent_id = event.payload.get("entry_intent_id")
            if isinstance(intent_id, str):
                skips_by_intent.setdefault(intent_id, []).append(event)

    included_intents = [
        event
        for event in events
        if event.event_type == "entry_intent"
        and session.window_start <= _decision(event) <= session.window_end
    ]
    for intent in included_intents:
        terminals = [
            *openings_by_intent.get(intent.event_id, []),
            *skips_by_intent.get(intent.event_id, []),
        ]
        if len(terminals) != 1:
            raise RealScoringIncomplete(
                f"included intent {intent.event_id!r} has {len(terminals)} terminals"
            )

    pairs: list[tuple[ledger.StoredEvent, ledger.StoredEvent]] = []
    for openings in openings_by_intent.values():
        if len(openings) != 1:
            raise RealScoringRefused("entry intent has duplicate opening fills")
        opening = openings[0]
        decision = _decision(opening)
        if not session.window_start <= decision <= session.window_end:
            continue
        if opening.symbol not in session.included:
            raise RealScoringRefused(
                f"included-window opening {opening.event_id} is outside the cohort"
            )
        position_id = opening.payload.get("position_id")
        if not isinstance(position_id, str):
            raise RealScoringRefused("opening fill has no position id")
        closes = closes_by_position.get(position_id, [])
        if len(closes) != 1:
            raise RealScoringIncomplete(
                f"included position {position_id!r} has {len(closes)} closing fills"
            )
        pairs.append((opening, closes[0]))
    pairs.sort(key=lambda pair: pair[0].seq)
    return pairs


def _copy_event(
    event: ledger.StoredEvent, causes: list[str], *, payload: dict | None = None
) -> dict:
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "occurred_at_utc": event.occurred_at_utc,
        "evaluation_session": event.evaluation_session,
        "symbol": event.symbol,
        "lane": event.lane,
        "causes": causes,
        "payload": event.payload if payload is None else payload,
    }


def _next_session(session: str) -> str:
    start = date.fromisoformat(session) + timedelta(days=1)
    end = start + timedelta(days=14)
    sessions = trading_days(start.isoformat(), end.isoformat())
    if not sessions:
        raise RealScoringRefused(f"no XNYS session follows {session}")
    return sessions[0]


def _validate_market_lineage(
    *,
    events: list[ledger.StoredEvent],
    opening: ledger.StoredEvent,
    closing: ledger.StoredEvent,
    exit_intent: ledger.StoredEvent,
) -> None:
    trigger_decision = exit_intent.payload.get("decision_session")
    close_decision = closing.payload.get("decision_session")
    if (
        not isinstance(trigger_decision, str)
        or exit_intent.payload.get("source_evaluation_session")
        != exit_intent.evaluation_session
        or not isinstance(close_decision, str)
        or closing.payload.get("source_evaluation_session")
        != closing.evaluation_session
        or closing.payload.get("fill_session") != closing.evaluation_session
    ):
        raise RealScoringRefused("market close loses decision/source session lineage")
    if (
        exit_intent.evaluation_session > trigger_decision
        or closing.evaluation_session > close_decision
    ):
        raise RealScoringRefused("market close source session follows its decision session")
    planned = exit_intent.payload.get("planned_fill_session")
    if planned != _next_session(trigger_decision):
        raise RealScoringRefused("market exit intent has the wrong planned fill session")
    exit_id = exit_intent.event_id
    gaps = [
        event
        for event in events
        if event.seq < closing.seq
        and event.event_type == "data_gap"
        and event.payload.get("exit_intent_id") == exit_id
    ]
    expected = str(planned)
    if gaps:
        latest_decision = gaps[-1].payload.get("decision_session")
        if not isinstance(latest_decision, str):
            raise RealScoringRefused("market exit retry gap has no decision session")
        expected = _next_session(latest_decision)
    if close_decision != expected:
        raise RealScoringRefused(
            f"market close decision session {close_decision} is not due session {expected}"
        )
    if (
        closing.payload.get("opening_fill_id") != opening.event_id
        or closing.payload.get("position_id") != opening.payload.get("position_id")
    ):
        raise RealScoringRefused("market close changes opening lineage")


def _frozen_market_result(
    *,
    session: RealScoringSession,
    events: list[ledger.StoredEvent],
    pairs: list[tuple[ledger.StoredEvent, ledger.StoredEvent]],
) -> dict:
    by_id = {event.event_id: event for event in events}
    market = [
        pair
        for pair in pairs
        if pair[1].payload.get("settlement_method") is None
    ]
    with tempfile.TemporaryDirectory(prefix="h7-market-score-") as raw:
        base = f"{raw}/ledger"
        write_clock = lambda: datetime(2100, 1, 1, tzinfo=timezone.utc)
        for opening, closing in market:
            intent_id = opening.payload.get("entry_intent_id")
            exit_intent_id = closing.payload.get("exit_intent_id")
            intent = by_id.get(intent_id) if isinstance(intent_id, str) else None
            exit_intent = (
                by_id.get(exit_intent_id)
                if isinstance(exit_intent_id, str)
                else None
            )
            if intent is None or intent.event_type != "entry_intent":
                raise RealScoringRefused("market opening has no entry-intent lineage")
            if exit_intent is None or exit_intent.event_type != "exit_intent":
                raise RealScoringRefused("market close has no exit-intent lineage")
            _validate_market_lineage(
                events=events,
                opening=opening,
                closing=closing,
                exit_intent=exit_intent,
            )
            injected_exit_payload = dict(exit_intent.payload)
            # The frozen synthetic scorer has one calendar and therefore
            # requires its planned-fill value to be the stored source date.
            # Real due/retry timing was checked above on the operational dates;
            # this narrow adapter changes no quote, fill, or scored date.
            injected_exit_payload["planned_fill_session"] = (
                closing.evaluation_session
            )
            for logical in (
                _copy_event(intent, []),
                _copy_event(opening, [intent.event_id]),
                _copy_event(
                    exit_intent,
                    [opening.event_id],
                    payload=injected_exit_payload,
                ),
                _copy_event(closing, [exit_intent.event_id]),
            ):
                ledger.append_event(logical, base_dir=base, clock=write_clock)
        try:
            return frozen_scoring.score_forward_window(
                base_dir=base,
                window_start=session.window_start,
                window_end=session.window_end,
            )
        except (
            frozen_scoring.ScoringValidationError,
            ledger.LedgerError,
            ValueError,
        ) as exc:
            raise _refuse("frozen market-close scoring refused", exc) from exc


def _expected_legs(action: dict, structure: str) -> list[tuple[str, float, str, str]]:
    expiration = action.get("expiration")
    if not isinstance(expiration, str):
        raise RealScoringRefused("settlement action has no expiration")
    if structure == "long_call":
        raw = [("long", action.get("strike"), "C", "buy")]
    elif structure == "call_debit_spread":
        raw = [
            ("long", action.get("long_strike"), "C", "buy"),
            ("short", action.get("short_strike"), "C", "sell"),
        ]
    elif structure == "bull_put_spread":
        raw = [
            ("short", action.get("short_strike"), "P", "sell"),
            ("long", action.get("long_strike"), "P", "buy"),
        ]
    else:
        raise RealScoringRefused("settlement opening structure is invalid")
    result: list[tuple[str, float, str, str]] = []
    for name, strike, right, side in raw:
        if (
            isinstance(strike, bool)
            or not isinstance(strike, (int, float))
            or not math.isfinite(float(strike))
            or float(strike) <= 0
        ):
            raise RealScoringRefused("settlement action strike is invalid")
        result.append((name, float(strike), right, side))
    return result


def _settlement_trade(
    opening: ledger.StoredEvent, closing: ledger.StoredEvent
) -> dict:
    structure = opening.payload.get("structure")
    action = opening.payload.get("action")
    if not isinstance(structure, str) or not isinstance(action, dict):
        raise RealScoringRefused("settlement opening action is malformed")
    if action.get("kind") != structure or action.get("lane") != opening.lane:
        raise RealScoringRefused("settlement opening action identity changed")
    expected = _expected_legs(action, structure)
    opening_legs = opening.payload.get("legs")
    closing_legs = closing.payload.get("legs")
    if (
        not isinstance(opening_legs, list)
        or not isinstance(closing_legs, list)
        or len(opening_legs) != len(expected)
        or len(closing_legs) != len(expected)
    ):
        raise RealScoringRefused("settlement legs do not match the frozen structure")
    expiration = str(action["expiration"])
    if closing.evaluation_session != expiration:
        raise RealScoringRefused("settlement close is not on contract expiration")
    if (
        closing.payload.get("source_evaluation_session")
        != closing.evaluation_session
        or closing.payload.get("decision_session") != closing.evaluation_session
        or closing.payload.get("fill_session") != closing.evaluation_session
    ):
        raise RealScoringRefused("settlement close loses decision/source session lineage")
    quantity = config.H7_FORWARD_CONTRACTS
    entry_net = 0.0
    for index, (name, strike, right, side) in enumerate(expected):
        leg = opening_legs[index]
        if not isinstance(leg, dict):
            raise RealScoringRefused("settlement opening leg is malformed")
        identity = {
            "name": name,
            "expiration": expiration,
            "strike": strike,
            "right": right,
            "side": side,
            "quantity": quantity,
        }
        if any(leg.get(key) != value for key, value in identity.items()):
            raise RealScoringRefused("settlement opening contract identity changed")
        try:
            fill = frozen_scoring._fill_price(leg, f"opening {name}")
        except frozen_scoring.ScoringValidationError as exc:
            raise _refuse("settlement opening fill is invalid", exc) from exc
        entry_net += fill if side == "buy" else -fill
    recorded_entry = opening.payload.get("net_debit_per_share")
    if not isinstance(recorded_entry, (int, float)) or not math.isclose(
        float(recorded_entry), entry_net, abs_tol=1e-9
    ):
        raise RealScoringRefused("settlement opening net debit is inconsistent")
    width = 0.0
    round_trip = len(expected) * 2 * config.COMMISSION_PER_CONTRACT * quantity
    if structure == "long_call":
        expected_risk = entry_net * 100 * quantity + round_trip
    else:
        width = float(action["short_strike"]) - float(action["long_strike"])
        if width <= 0:
            raise RealScoringRefused("settlement vertical width is invalid")
        if structure == "call_debit_spread":
            expected_risk = entry_net * 100 * quantity + round_trip
        else:
            credit = -entry_net
            expected_risk = (width - credit) * 100 * quantity + round_trip
    at_risk = opening.payload.get("at_risk")
    if not isinstance(at_risk, (int, float)) or not math.isclose(
        float(at_risk), expected_risk, abs_tol=1e-9
    ):
        raise RealScoringRefused("settlement opening at-risk is inconsistent")
    entry_commission = opening.payload.get("commission")
    expected_entry_commission = (
        len(expected) * quantity * config.COMMISSION_PER_CONTRACT
    )
    if not isinstance(entry_commission, (int, float)) or not math.isclose(
        float(entry_commission), expected_entry_commission, abs_tol=1e-9
    ):
        raise RealScoringRefused("settlement opening commission is inconsistent")

    method = closing.payload.get("settlement_method")
    underlying = closing.payload.get("underlying_close")
    if method not in {"intrinsic_at_close", "conservative_full_loss"}:
        raise RealScoringRefused("settlement method is not canonical")
    if closing.payload.get("assignment_disclosure_required") is not True:
        raise RealScoringRefused("settlement close lacks assignment disclosure")
    exit_net = 0.0
    itm_count = 0
    underlying_value: float | None = None
    if method == "intrinsic_at_close":
        if (
            isinstance(underlying, bool)
            or not isinstance(underlying, (int, float))
            or not math.isfinite(float(underlying))
            or float(underlying) <= 0
        ):
            raise RealScoringRefused("intrinsic settlement has no valid underlying close")
        underlying_value = float(underlying)
    elif underlying is not None:
        raise RealScoringRefused("conservative settlement fabricates an underlying close")
    for index, (name, strike, right, side) in enumerate(expected):
        leg = closing_legs[index]
        if not isinstance(leg, dict):
            raise RealScoringRefused("settlement closing leg is malformed")
        close_side = "sell" if side == "buy" else "buy"
        if any(
            leg.get(key) != value
            for key, value in {
                "name": name,
                "expiration": expiration,
                "strike": strike,
                "right": right,
                "opening_side": side,
                "closing_side": close_side,
                "quantity": quantity,
            }.items()
        ):
            raise RealScoringRefused("settlement closing contract identity changed")
        if underlying_value is not None:
            intrinsic = (
                max(0.0, underlying_value - strike)
                if right == "C"
                else max(0.0, strike - underlying_value)
            )
            cash = intrinsic if side == "buy" else -intrinsic
            itm = intrinsic >= 0.01
        else:
            intrinsic = None
            cash = -width if structure == "bull_put_spread" and name == "short" else 0.0
            itm = structure == "bull_put_spread"
        if (
            leg.get("intrinsic_per_share") != intrinsic
            or leg.get("in_the_money") is not itm
            or not isinstance(leg.get("settlement_cash_per_share"), (int, float))
            or not math.isclose(
                float(leg["settlement_cash_per_share"]), cash, abs_tol=1e-9
            )
        ):
            raise RealScoringRefused("settlement leg value is not canonical")
        exit_net += cash
        itm_count += int(itm)
    recorded_exit = closing.payload.get("net_close_credit_per_share")
    if not isinstance(recorded_exit, (int, float)) or not math.isclose(
        float(recorded_exit), exit_net, abs_tol=1e-9
    ):
        raise RealScoringRefused("settlement net close credit is inconsistent")
    exit_commission = closing.payload.get("commission")
    expected_exit_commission = itm_count * quantity * config.COMMISSION_PER_CONTRACT
    if not isinstance(exit_commission, (int, float)) or not math.isclose(
        float(exit_commission), expected_exit_commission, abs_tol=1e-9
    ):
        raise RealScoringRefused("settlement commission is inconsistent")
    entry_underlying = opening.payload.get("underlying_close")
    if not isinstance(entry_underlying, (int, float)) or float(entry_underlying) <= 0:
        raise RealScoringRefused("settlement opening underlying close is invalid")
    pnl = (
        (exit_net - entry_net) * 100 * quantity
        - float(entry_commission)
        - float(exit_commission)
    )
    return {
        "position_id": opening.payload["position_id"],
        "entry_event_id": opening.event_id,
        "exit_event_id": closing.event_id,
        "decision_session": _decision(opening),
        "entry_date": opening.evaluation_session,
        "exit_date": closing.evaluation_session,
        "symbol": opening.symbol,
        "lane": opening.lane,
        "structure": structure,
        "exit_reason": "expiration_settlement",
        "pnl": pnl,
        "capital_at_risk": float(at_risk),
        "economic_max_loss": float(at_risk),
        "entry_commission": float(entry_commission),
        "exit_commission": float(exit_commission),
        "underlying_entry_close": float(entry_underlying),
        "underlying_exit_close": underlying_value,
        "underlying_move": (
            underlying_value - float(entry_underlying)
            if underlying_value is not None
            else None
        ),
        "underlying_return": (
            underlying_value / float(entry_underlying) - 1
            if underlying_value is not None
            else None
        ),
        "settlement_method": method,
    }


def _union_group(trades: list[dict], label: str) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        raw = scoreboard(trades, label=label)
    verdict, reason = frozen_scoring.map_forward_verdict(raw)
    observed_returns = [
        float(trade["underlying_return"])
        for trade in trades
        if trade.get("underlying_return") is not None
    ]
    return {
        "verdict": verdict,
        "reason": reason,
        "scoreboard": json_safe(raw),
        "mean_underlying_return": (
            sum(observed_returns) / len(observed_returns)
            if observed_returns
            else None
        ),
        "note": (
            "SURVIVED is not approval, validation, live authorization, or a "
            "claim of future profitability"
        ),
    }


def _score_result(
    session: RealScoringSession,
    events: list[ledger.StoredEvent],
    input_head: str,
) -> tuple[dict, list[str]]:
    pairs = _completed_pairs(session, events)
    market = _frozen_market_result(session=session, events=events, pairs=pairs)
    settlement_trades = [
        _settlement_trade(opening, closing)
        for opening, closing in pairs
        if closing.payload.get("settlement_method") is not None
    ]
    trades = [*market["trades"], *settlement_trades]
    trades.sort(
        key=lambda trade: (
            trade["entry_date"],
            trade["symbol"],
            trade["lane"],
            trade["position_id"],
        )
    )
    overall = _union_group(trades, "H7 forward paper overall")
    lanes = {
        lane: _union_group(
            [trade for trade in trades if trade["lane"] == lane],
            f"H7{lane} forward paper",
        )
        for lane in config.H7_LANE_PRIORITY
    }
    result = {
        "schema_version": 1,
        "window_start": session.window_start,
        "window_end": session.window_end,
        "ledger_head": input_head,
        "n_trades": len(trades),
        "trades": trades,
        "overall": overall,
        "lanes": lanes,
        "frozen": market["frozen"],
        "frozen_scorer_market_only": market,
        "settlement": {
            "position_count": len(settlement_trades),
            "aggregate_pnl": sum(trade["pnl"] for trade in settlement_trades),
            "positions": [trade["position_id"] for trade in settlement_trades],
        },
    }
    causes = [session.registration_event_id]
    for opening, closing in pairs:
        causes.extend((opening.event_id, closing.event_id))
    return result, causes


def preview_real_score(
    session: RealScoringSession, *, now: datetime | None = None
) -> dict:
    """Read and compute only; never create an artifact or append an event."""
    events = _revalidate(session)
    stamp = _utc_now(now)
    if stamp < session_close_utc(session.window_end):
        raise RealScoringIncomplete(
            f"final decision session {session.window_end} has not completed"
        )
    head = events[-1].record_hash
    score_events = [event for event in events if event.event_type == "window_score"]
    if score_events:
        head = str(score_events[0].payload.get("input_ledger_head"))
    result, _ = _score_result(session, events, head)
    return result


def _require_review_passes(session: RealScoringSession) -> None:
    try:
        lines = session.facts_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise _refuse("review facts are unavailable", exc) from exc
    required = (
        (
            REVIEW_PASS_TAG,
            ("verdict=PASS", f"spec_sha256={session.spec_sha256}"),
        ),
        (
            OWNER_PASS_TAG,
            (
                "owner=carsyn",
                "verdict=PASS",
                f"spec_sha256={session.spec_sha256}",
            ),
        ),
    )
    for tag, tokens in required:
        matches = [line for line in lines if f"\t{tag}" in line]
        if not matches or any(token not in matches[-1] for token in tokens):
            raise RealScoringRefused(
                f"finalization requires current {tag} fact with {tokens!r}"
            )


def _receipt_payload(
    *,
    session: RealScoringSession,
    result: dict,
    input_head: str,
    finalized_at: str,
) -> dict:
    return {
        "evaluation_session": session.window_end,
        "scope": {"scope_id": session.scope_id, "scope_hash": session.scope_hash},
        "registration": {
            "event_id": session.registration_event_id,
            "record_hash": session.registration_record_hash,
        },
        "window": {
            "start_decision_session": session.window_start,
            "final_decision_session": session.window_end,
        },
        "input_ledger_head": input_head,
        "scorer": {
            "module": "options_researcher.h7_forward_scoring",
            "config_hash": config_hash(),
            "cost_model_hash": cost_model_hash(),
            "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
            "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
            "forward_contracts": config.H7_FORWARD_CONTRACTS,
        },
        "cohort": {
            "included": list(session.included),
            "excluded": [
                {"symbol": symbol, "reason": reason}
                for symbol, reason in session.excluded
            ],
        },
        "finalized_at_utc": finalized_at,
        "owner_acknowledgement": "carsyn",
        "spec_sha256": session.spec_sha256,
        "result": result,
        "disclosures": {
            "survived": (
                "SURVIVED is not validation, profitability, live-trading approval, "
                "or permission to change strategy rules."
            ),
            "assignment": (
                "Assumption / known limitation: paper closes use adverse quote "
                "marks and do not model early assignment or dividend-driven early "
                "exercise. Short legs in MSFT, CEG, VST, and ET may be assigned "
                "early around ex-dates; results are option-quote-marked paper results."
            ),
            "small_sample_interval": (
                "Official-source, DiCiccio & Efron 1996: the frozen 90% interval "
                "is percentile-type, first-order accurate, and can under-cover at "
                "small samples; a SURVIVED lower bound above zero must be read with "
                "that limitation."
            ),
        },
    }


def finalize_real_score(
    session: RealScoringSession,
    *,
    owner: str,
    now: datetime | None = None,
) -> ScoringFinalizeResult:
    """Publish the one artifact then its one causal window_score event."""
    if owner != "carsyn":
        raise RealScoringRefused("owner acknowledgement must be exactly 'carsyn'")
    events = _revalidate(session)
    _require_review_passes(session)
    stamp = _utc_now(now)
    if stamp < session_close_utc(session.window_end):
        raise RealScoringIncomplete(
            f"final decision session {session.window_end} has not completed"
        )
    score_events = [event for event in events if event.event_type == "window_score"]
    event_id = f"h7:window_score:{session.scope_id}:{session.window_end}"
    if len(score_events) > 1 or (
        score_events and score_events[0].event_id != event_id
    ):
        raise RealScoringRefused("forward ledger already has a different window score")
    existing_event = score_events[0] if score_events else None
    existing_receipt: dict | None = None
    if session.artifact_path.exists():
        try:
            existing_receipt = load_receipt(
                session.artifact_path, expected_type="window_score"
            )
        except (OSError, ValueError, KeyError) as exc:
            raise _refuse("existing score artifact is invalid", exc) from exc
    if existing_event is not None:
        if events[-1].event_id != existing_event.event_id:
            raise RealScoringRefused("events were appended after the one final score")
        input_head = existing_event.payload.get("input_ledger_head")
    elif existing_receipt is not None:
        input_head = existing_receipt.get("input_ledger_head")
    else:
        input_head = events[-1].record_hash
    if not isinstance(input_head, str) or len(input_head) != 64:
        raise RealScoringRefused("score input ledger head is invalid")
    current_input_head = (
        existing_event.prev_hash if existing_event is not None else events[-1].record_hash
    )
    if current_input_head != input_head:
        raise RealScoringRefused("score artifact input head no longer matches the ledger")
    result, causes = _score_result(session, events, input_head)
    finalized_at = (
        existing_receipt.get("finalized_at_utc")
        if existing_receipt is not None
        else stamp.isoformat()
    )
    if not isinstance(finalized_at, str):
        raise RealScoringRefused("existing score finalization time is invalid")
    receipt = make_receipt(
        "window_score",
        _receipt_payload(
            session=session,
            result=result,
            input_head=input_head,
            finalized_at=finalized_at,
        ),
    )
    if existing_receipt is not None and canonical_json(existing_receipt) != canonical_json(
        receipt
    ):
        raise RealScoringRefused("existing score artifact conflicts with recomputation")
    try:
        artifact_hash = write_immutable_receipt(receipt, session.artifact_path)
    except (OSError, ValueError, FileExistsError) as exc:
        raise _refuse("cannot publish immutable score artifact", exc) from exc
    event = {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": "window_score",
        "occurred_at_utc": session_close_utc(session.window_end).isoformat(),
        "evaluation_session": session.window_end,
        "symbol": None,
        "lane": None,
        "causes": causes,
        "payload": {
            "artifact_path": str(session.artifact_path),
            "artifact_hash": artifact_hash,
            "input_ledger_head": input_head,
            "trade_count": result["n_trades"],
            "overall_verdict": result["overall"]["verdict"],
            "lane_verdicts": {
                lane: result["lanes"][lane]["verdict"]
                for lane in config.H7_LANE_PRIORITY
            },
        },
    }
    if existing_event is not None:
        logical = _copy_event(existing_event, existing_event.causes)
        if canonical_json(logical) != canonical_json(event):
            raise RealScoringRefused("existing window-score event conflicts with artifact")
        appended = False
    else:
        try:
            appended = ledger.append_event(
                event,
                base_dir=session.base_dir,
                expected_head=input_head,
                clock=lambda: stamp,
            ).appended
        except ledger.LedgerError as exc:
            raise _refuse(
                "score artifact written but window-score event append refused; "
                "artifact is an orphan and retryable only at the same input head",
                exc,
            ) from exc
    return ScoringFinalizeResult(
        event_id=event_id,
        artifact_path=session.artifact_path,
        artifact_hash=artifact_hash,
        appended=appended,
        result=result,
    )


def main(argv: list[str] | None = None) -> int:
    """Read-only preview or separately review-gated one-time finalization."""
    import argparse

    parser = argparse.ArgumentParser(
        description="H7 real forward scoring (paper research only; never orders)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("preview", help="read-only computation, always labeled NOT FINAL")
    finalize = sub.add_parser("finalize", help="publish the one gated final score")
    finalize.add_argument("--owner", required=True)
    try:
        args = parser.parse_args(argv)
        session = open_real_scoring_session(
            base_dir=REAL_FORWARD_STORE,
            facts_path=DEFAULT_FACTS_PATH,
            artifact_root=DEFAULT_ARTIFACT_ROOT,
        )
        if args.command == "preview":
            try:
                result = preview_real_score(session)
            except RealScoringIncomplete as exc:
                print(f"H7 SCORE NOT FINAL -- {exc}")
                return 0
            print(
                f"H7 SCORE NOT FINAL -- trades={result['n_trades']} "
                f"verdict={result['overall']['verdict']}"
            )
            return 0
        result = finalize_real_score(session, owner=args.owner)
        replay = "appended" if result.appended else "replayed"
        print(
            f"H7 SCORE FINAL {result.event_id} {replay} "
            f"artifact={result.artifact_path} hash={result.artifact_hash}"
        )
        return 0
    except (
        RealScoringRefused,
        frozen_scoring.ScoringValidationError,
        ledger.LedgerError,
        OSError,
        ValueError,
    ) as exc:
        print(f"H7 SCORE REFUSED -- {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

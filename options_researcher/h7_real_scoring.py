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
from options_researcher.h7_scoring_identity import (
    FROZEN_SCORER_MODULE,
    ScoringIdentityError,
    registered_scoring_identity,
    runtime_scoring_identity,
)
from options_researcher.h7_watch import evaluation_session as watcher_evaluation_session
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
from strategies.h7_backtest import EXIT_PRIORITY, primary_exit_reason

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FACTS_PATH = REPO_ROOT / "ledger" / "facts.log"
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "reports" / "h7_forward_scoring"
BASE_SPEC_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-22-h7-real-exit-scoring-SPEC.md"
)
AMENDMENT_SPEC_PATH = (
    REPO_ROOT
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-07-25-h7-real-exit-scoring-amendment-v1_3.md"
)
# Compatibility name for callers that need the currently active delta document.
SPEC_PATH = AMENDMENT_SPEC_PATH
PINNED_BASE_SPEC_SHA256 = (
    "c66d0e395ecc3ae77d5c554bd978e87fa305080cb61423015da513dd29065a75"
)
AMENDMENT_FACT_TAG = "H7_EXIT_SCORING_SPEC_AMENDMENT_V1_3"
AMENDMENT_PROVENANCE = "owner-delegated standing 2026-07-25"
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
    scoring_identity_contract: str
    scoring_identity_hash: str
    scoring_identity_surface: str
    registered_config_hash: str
    artifact_path: Path
    facts_path: Path
    base_spec_sha256: str
    amendment_spec_sha256: str
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


def _config_provenance_hash(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise RealScoringRefused(f"{label} must be a lowercase SHA-256 value")
    return value


def _verified_spec_chain() -> tuple[str, str]:
    base_hash = sha256_file(BASE_SPEC_PATH)
    if base_hash != PINNED_BASE_SPEC_SHA256:
        raise RealScoringRefused(
            "base scoring SPEC changed from its amendment-pinned SHA-256"
        )
    return base_hash, sha256_file(AMENDMENT_SPEC_PATH)


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
    try:
        registered_scoring = registered_scoring_identity(frozen)
        runtime_scoring = runtime_scoring_identity(
            cost_model_hash_value=cost_model_hash()
        )
    except ScoringIdentityError as exc:
        raise _refuse("window registration scoring identity is malformed", exc) from exc
    if registered_scoring != runtime_scoring:
        raise RealScoringRefused(
            "registered scoring identity changed: "
            f"{registered_scoring.identity_hash} != "
            f"{runtime_scoring.identity_hash}"
        )
    registered_config_hash = _config_provenance_hash(
        frozen.get("config_hash"), "registered config hash provenance"
    )
    return {
        "window_start": start,
        "window_end": end,
        "scope": scope,
        "included": tuple(included),
        "excluded": tuple(excluded_pairs),
        "scoring_identity": registered_scoring,
        "registered_config_hash": registered_config_hash,
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
    scoring_identity = identity["scoring_identity"]
    base_spec_sha256, amendment_spec_sha256 = _verified_spec_chain()
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
        scoring_identity_contract=scoring_identity.contract,
        scoring_identity_hash=scoring_identity.identity_hash,
        scoring_identity_surface=scoring_identity.canonical_surface,
        registered_config_hash=identity["registered_config_hash"],
        artifact_path=Path(artifact_root) / str(scope["scope_id"]) / f"{end}.json",
        facts_path=Path(facts_path),
        base_spec_sha256=base_spec_sha256,
        amendment_spec_sha256=amendment_spec_sha256,
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
    base_spec_sha256, amendment_spec_sha256 = _verified_spec_chain()
    if (
        registration.event_id != session.registration_event_id
        or registration.record_hash != session.registration_record_hash
        or identity["window_start"] != session.window_start
        or identity["window_end"] != session.window_end
        or identity["included"] != session.included
        or identity["excluded"] != session.excluded
        or identity["scoring_identity"].contract
        != session.scoring_identity_contract
        or identity["scoring_identity"].identity_hash
        != session.scoring_identity_hash
        or identity["scoring_identity"].canonical_surface
        != session.scoring_identity_surface
        or identity["registered_config_hash"] != session.registered_config_hash
        or base_spec_sha256 != session.base_spec_sha256
        or amendment_spec_sha256 != session.amendment_spec_sha256
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


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _require_recorded_at_or_after(
    event: ledger.StoredEvent, threshold: datetime, *, detail: str
) -> datetime:
    try:
        recorded = datetime.fromisoformat(event.recorded_at_utc)
    except ValueError as exc:
        raise _refuse(f"{detail} recorded timestamp is invalid", exc) from exc
    if recorded < threshold:
        raise RealScoringRefused(f"{detail} was recorded before its evidence cutoff")
    return recorded


def _validate_global_gate(
    by_id: dict[str, ledger.StoredEvent],
    gate: ledger.StoredEvent,
    *,
    evaluation_session: str,
    require_go: bool | None,
) -> ledger.StoredEvent:
    """Validate the canonical receipt-linked whole-scope gate event."""
    scope = scope_identity()
    source_id = f"h7:source_health:{evaluation_session}"
    source = by_id.get(source_id)
    verdict = gate.payload.get("whole_universe_verdict")
    go_count = gate.payload.get("go_count")
    no_go_count = gate.payload.get("no_go_count")
    total = len(scope["symbols"])
    expected_gate_keys = {
        "scope",
        "whole_universe_verdict",
        "go_count",
        "no_go_count",
        "receipt_hash",
        "receipt_path",
        "source_health_receipt_hash",
        "source_health_receipt_path",
    }
    expected_source_keys = {
        "scope",
        "healthy_symbols",
        "receipt_hash",
        "receipt_path",
    }
    counts_valid = (
        isinstance(go_count, int)
        and not isinstance(go_count, bool)
        and isinstance(no_go_count, int)
        and not isinstance(no_go_count, bool)
        and go_count >= 0
        and no_go_count >= 0
        and go_count + no_go_count == total
    )
    verdict_valid = verdict in {"GO", "NO_GO"} and (
        (verdict == "GO" and go_count == total and no_go_count == 0)
        or (verdict == "NO_GO" and isinstance(no_go_count, int) and no_go_count > 0)
    )
    if (
        gate.event_id != f"h7:data_gate:{evaluation_session}"
        or gate.event_type != "data_gate"
        or gate.evaluation_session != evaluation_session
        or gate.symbol is not None
        or gate.lane is not None
        or gate.causes != [source_id]
        or set(gate.payload) != expected_gate_keys
        or gate.payload.get("scope") != scope
        or not counts_valid
        or not verdict_valid
        or not _nonempty_text(gate.payload.get("receipt_hash"))
        or not _nonempty_text(gate.payload.get("receipt_path"))
        or not _nonempty_text(gate.payload.get("source_health_receipt_hash"))
        or not _nonempty_text(gate.payload.get("source_health_receipt_path"))
        or source is None
        or source.event_type != "source_health"
        or source.evaluation_session != evaluation_session
        or source.symbol is not None
        or source.lane is not None
        or source.causes
        or set(source.payload) != expected_source_keys
        or source.payload.get("scope") != scope
        or source.payload.get("receipt_hash")
        != gate.payload.get("source_health_receipt_hash")
        or source.payload.get("receipt_path")
        != gate.payload.get("source_health_receipt_path")
    ):
        raise RealScoringRefused(
            f"data gate {gate.event_id} is not canonical receipt-bound evidence"
        )
    cutoff = session_close_utc(evaluation_session)
    _require_recorded_at_or_after(gate, cutoff, detail=f"data gate {gate.event_id}")
    _require_recorded_at_or_after(
        source, cutoff, detail=f"source health {source.event_id}"
    )
    healthy_symbols = source.payload.get("healthy_symbols")
    if (
        not isinstance(healthy_symbols, list)
        or len(set(healthy_symbols)) != len(healthy_symbols)
        or any(symbol not in scope["symbols"] for symbol in healthy_symbols)
    ):
        raise RealScoringRefused(
            f"source health {source.event_id} has an invalid scope payload"
        )
    try:
        gate_receipt = load_receipt(
            Path(str(gate.payload["receipt_path"])), expected_type="data_gate"
        )
        source_receipt = load_receipt(
            Path(str(source.payload["receipt_path"])), expected_type="source_health"
        )
    except (OSError, ValueError, KeyError) as exc:
        raise _refuse("scoring evidence receipt is unavailable", exc) from exc
    receipt_symbols = source_receipt.get("symbols")
    if (
        gate_receipt.get("receipt_hash") != gate.payload.get("receipt_hash")
        or gate_receipt.get("evaluation_session") != evaluation_session
        or gate_receipt.get("scope") != scope
        or gate_receipt.get("whole_universe_verdict") != verdict
        or gate_receipt.get("go_count") != go_count
        or gate_receipt.get("no_go_count") != no_go_count
        or gate_receipt.get("source_health_receipt_hash")
        != source.payload.get("receipt_hash")
        or gate_receipt.get("source_health_receipt_path")
        != source.payload.get("receipt_path")
        or source_receipt.get("receipt_hash") != source.payload.get("receipt_hash")
        or source_receipt.get("evaluation_session") != evaluation_session
        or source_receipt.get("scope") != scope
        or not isinstance(receipt_symbols, dict)
        or set(receipt_symbols) != set(scope["symbols"])
        or any(
            not isinstance(receipt_symbols.get(symbol), dict)
            or receipt_symbols[symbol].get("healthy") is not True
            for symbol in healthy_symbols
        )
    ):
        raise RealScoringRefused(
            f"data gate {gate.event_id} disagrees with its immutable receipts"
        )
    if require_go is True and verdict != "GO":
        raise RealScoringRefused(f"data gate {gate.event_id} is not GO")
    if require_go is False and verdict == "GO":
        raise RealScoringRefused(f"data gate {gate.event_id} is unexpectedly GO")
    return source


def _validate_symbol_source(
    by_id: dict[str, ledger.StoredEvent],
    source: ledger.StoredEvent,
    *,
    evaluation_session: str,
    symbol: str,
    require_clear: bool | None,
) -> dict:
    """Validate a deterministic symbol event against its global receipt event."""
    scope = scope_identity()
    global_source = by_id.get(f"h7:source_health:{evaluation_session}")
    expected_keys = {"scope", "healthy", "gate", "receipt_hash", "receipt_path"}
    gate_state = source.payload.get("gate")
    healthy = source.payload.get("healthy")
    if (
        source.event_id != f"h7:source_health:{evaluation_session}:{symbol}"
        or source.event_type != "source_health"
        or source.evaluation_session != evaluation_session
        or source.symbol != symbol
        or source.lane is not None
        or source.causes
        or set(source.payload) != expected_keys
        or source.payload.get("scope") != scope
        or gate_state not in {"CLEAR", "BANNED", "UNKNOWN"}
        or not isinstance(healthy, bool)
        or global_source is None
        or source.payload.get("receipt_hash")
        != global_source.payload.get("receipt_hash")
        or source.payload.get("receipt_path")
        != global_source.payload.get("receipt_path")
    ):
        raise RealScoringRefused(
            f"source health {source.event_id} is not canonical receipt-bound evidence"
        )
    _require_recorded_at_or_after(
        source,
        session_close_utc(evaluation_session),
        detail=f"source health {source.event_id}",
    )
    try:
        receipt = load_receipt(
            Path(str(source.payload["receipt_path"])), expected_type="source_health"
        )
        receipt_state = receipt["symbols"][symbol]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise _refuse("symbol source-health receipt is unavailable", exc) from exc
    if (
        receipt.get("receipt_hash") != source.payload.get("receipt_hash")
        or receipt.get("evaluation_session") != evaluation_session
        or receipt.get("scope") != scope
        or not isinstance(receipt_state, dict)
        or receipt_state.get("gate") != gate_state
        or receipt_state.get("healthy") is not healthy
    ):
        raise RealScoringRefused(
            f"source health {source.event_id} disagrees with its immutable receipt"
        )
    clear = gate_state == "CLEAR" and healthy is True
    if require_clear is True and not clear:
        raise RealScoringRefused(f"source health {source.event_id} is not CLEAR")
    if require_clear is False and clear:
        raise RealScoringRefused(f"source health {source.event_id} is unexpectedly CLEAR")
    return receipt_state


def _validated_approval(
    by_id: dict[str, ledger.StoredEvent], intent: ledger.StoredEvent
) -> ledger.StoredEvent | None:
    approval = by_id.get(f"s4.owner_approval:{intent.event_id}")
    if approval is None:
        return None
    fill_session = intent.payload.get("planned_fill_session")
    if not isinstance(fill_session, str):
        raise RealScoringRefused("entry intent has no planned fill session")
    cutoff = session_close_utc(fill_session)
    expected_payload = {
        "entry_intent_id": intent.event_id,
        "fill_session": fill_session,
        "approval_cutoff_utc": cutoff.isoformat(),
    }
    try:
        recorded = datetime.fromisoformat(approval.recorded_at_utc)
        intent_recorded = datetime.fromisoformat(intent.recorded_at_utc)
    except ValueError as exc:
        raise _refuse("owner approval timestamp is invalid", exc) from exc
    if (
        approval.event_type != "owner_approval"
        or approval.causes != [intent.event_id]
        or approval.evaluation_session != intent.evaluation_session
        or approval.symbol != intent.symbol
        or approval.lane != intent.lane
        or approval.payload != expected_payload
        or recorded < intent_recorded
        or recorded > cutoff
    ):
        raise RealScoringRefused(
            f"owner approval {approval.event_id} is not canonical intent evidence"
        )
    return approval


def _validate_skip_terminal(
    by_id: dict[str, ledger.StoredEvent],
    *,
    intent: ledger.StoredEvent,
    skip: ledger.StoredEvent,
) -> None:
    reason = skip.payload.get("reason")
    planned_fill = intent.payload.get("planned_fill_session")
    allowed_reasons = {
        "approval_late",
        "approval_missing",
        "data_gate_no_go",
        "earnings_gate_at_fill",
        "dte_at_fill",
        "entry_data_gap",
        "liquidity_at_fill",
        "economics_at_fill",
        "book_capacity_at_fill",
    }
    if not isinstance(planned_fill, str) or reason not in allowed_reasons:
        raise RealScoringRefused(f"skip {skip.event_id} is not a known terminal")
    cutoff = session_close_utc(planned_fill).isoformat()
    cutoff_dt = session_close_utc(planned_fill)
    if (
        skip.event_id
        != f"s4.skip:{planned_fill}:{reason}:{intent.event_id}"
        or skip.event_type != "skip"
        or skip.symbol != intent.symbol
        or skip.lane != intent.lane
        or skip.evaluation_session != planned_fill
        or skip.occurred_at_utc != cutoff
        or skip.payload.get("entry_intent_id") != intent.event_id
    ):
        raise RealScoringRefused(f"skip {skip.event_id} changes entry-intent lineage")

    base_keys = {"entry_intent_id", "reason"}
    if reason == "approval_late":
        recorded = _require_recorded_at_or_after(
            skip, cutoff_dt, detail=f"skip {skip.event_id}"
        )
        if (
            skip.causes != [intent.event_id]
            or set(skip.payload) != base_keys | {"approval_cutoff_utc"}
            or skip.payload.get("approval_cutoff_utc") != cutoff
            or _validated_approval(by_id, intent) is not None
            or recorded <= cutoff_dt
        ):
            raise RealScoringRefused(f"skip {skip.event_id} has invalid late-approval evidence")
        return

    _require_recorded_at_or_after(skip, cutoff_dt, detail=f"skip {skip.event_id}")

    gate_id = f"h7:data_gate:{planned_fill}"
    gate = by_id.get(gate_id)
    source_id = f"h7:source_health:{planned_fill}:{intent.symbol}"
    source = by_id.get(source_id)
    if gate is None or source is None:
        raise RealScoringRefused(f"skip {skip.event_id} lacks fill-session evidence")
    _validate_global_gate(
        by_id,
        gate,
        evaluation_session=planned_fill,
        require_go=False if reason == "data_gate_no_go" else True,
    )
    clear_required = (
        False
        if reason == "earnings_gate_at_fill"
        else None
        if reason in {"approval_missing", "data_gate_no_go"}
        else True
    )
    _validate_symbol_source(
        by_id,
        source,
        evaluation_session=planned_fill,
        symbol=str(intent.symbol),
        require_clear=clear_required,
    )

    approval = _validated_approval(by_id, intent)
    if reason == "approval_missing":
        if (
            skip.causes != [intent.event_id]
            or set(skip.payload) != base_keys
            or approval is not None
        ):
            raise RealScoringRefused(f"skip {skip.event_id} has invalid missing-approval evidence")
        return
    if approval is None:
        raise RealScoringRefused(f"skip {skip.event_id} lacks timely owner approval")

    if reason == "earnings_gate_at_fill":
        expected_causes = [intent.event_id, source_id]
    elif reason == "entry_data_gap":
        gap_id = f"s4.data_gap:{planned_fill}:entry_fill:{intent.event_id}"
        gap = by_id.get(gap_id)
        expected_gap_keys = {
            "entry_intent_id",
            "phase",
            "reason",
            "chain_identity",
            "closes_identity",
        }
        if (
            gap is None
            or gap.event_type != "data_gap"
            or gap.evaluation_session != planned_fill
            or gap.symbol != intent.symbol
            or gap.lane != intent.lane
            or gap.causes != [gate_id]
            or set(gap.payload) != expected_gap_keys
            or gap.payload.get("entry_intent_id") != intent.event_id
            or gap.payload.get("phase") != "entry_fill"
            or not _nonempty_text(gap.payload.get("reason"))
            or not _nonempty_text(gap.payload.get("chain_identity"))
            or not _nonempty_text(gap.payload.get("closes_identity"))
        ):
            raise RealScoringRefused(f"skip {skip.event_id} has invalid entry-gap evidence")
        expected_causes = [intent.event_id, gap_id]
    else:
        expected_causes = [intent.event_id, gate_id]

    if reason == "book_capacity_at_fill":
        expected_payload_keys = base_keys | {
            "book_snapshot_hash",
            "capacity_snapshot",
            "projected_month_risk",
            "projected_open_h7c",
            "projected_underlying_occupancy",
            "failed_constraints",
            "limits",
        }
    else:
        expected_payload_keys = base_keys
    if skip.causes != expected_causes or set(skip.payload) != expected_payload_keys:
        raise RealScoringRefused(f"skip {skip.event_id} has invalid canonical evidence")


def _completed_pairs(
    session: RealScoringSession, events: list[ledger.StoredEvent]
) -> list[tuple[ledger.StoredEvent, ledger.StoredEvent]]:
    by_id = {event.event_id: event for event in events}
    intents_by_id = {
        event.event_id: event
        for event in events
        if event.event_type == "entry_intent"
    }
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

    for intent_id, openings in openings_by_intent.items():
        intent = intents_by_id.get(intent_id)
        if intent is None:
            raise RealScoringRefused("opening fill has no entry-intent lineage")
        for opening in openings:
            if (
                intent.event_id not in opening.causes
                or opening.payload.get("position_id")
                != intent.payload.get("position_id")
                or opening.symbol != intent.symbol
                or opening.lane != intent.lane
                or _decision(opening) != _decision(intent)
            ):
                raise RealScoringRefused(
                    f"opening fill {opening.event_id} changes entry-intent lineage"
                )
            try:
                cause_events = [by_id[cause] for cause in opening.causes]
            except KeyError as exc:
                raise RealScoringRefused(
                    f"opening fill {opening.event_id} cites missing evidence"
                ) from exc
            approvals = [
                event for event in cause_events if event.event_type == "owner_approval"
            ]
            gates = [
                event for event in cause_events if event.event_type == "data_gate"
            ]
            sources = [
                event
                for event in cause_events
                if event.event_type == "source_health"
                and event.symbol == opening.symbol
            ]
            if len(approvals) != 1 or len(gates) != 1 or len(sources) != 1:
                raise RealScoringRefused(
                    f"opening fill {opening.event_id} lacks entry evidence lineage"
                )
            approval, gate, source = approvals[0], gates[0], sources[0]
            expected_causes = [
                intent.event_id,
                approval.event_id,
                source.event_id,
                gate.event_id,
            ]
            validated_approval = _validated_approval(by_id, intent)
            planned_fill = intent.payload.get("planned_fill_session")
            _validate_global_gate(
                by_id,
                gate,
                evaluation_session=opening.evaluation_session,
                require_go=True,
            )
            _validate_symbol_source(
                by_id,
                source,
                evaluation_session=opening.evaluation_session,
                symbol=str(opening.symbol),
                require_clear=True,
            )
            if (
                opening.causes != expected_causes
                or opening.payload.get("fill_session") != opening.evaluation_session
                or planned_fill != opening.evaluation_session
                or planned_fill != _next_session(_decision(intent))
                or validated_approval is not approval
            ):
                raise RealScoringRefused(
                    f"opening fill {opening.event_id} has invalid entry evidence lineage"
                )
            _require_recorded_at_or_after(
                opening,
                session_close_utc(opening.evaluation_session),
                detail=f"opening fill {opening.event_id}",
            )
    for intent_id, skips in skips_by_intent.items():
        intent = intents_by_id.get(intent_id)
        if intent is None:
            raise RealScoringRefused("skip has no entry-intent lineage")
        for skip in skips:
            _validate_skip_terminal(by_id, intent=intent, skip=skip)

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
        intent = intents_by_id[str(opening.payload["entry_intent_id"])]
        decision = _decision(intent)
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


def _validate_exit_reason_payload(exit_intent: ledger.StoredEvent) -> bool:
    reasons = exit_intent.payload.get("trigger_reasons")
    primary = exit_intent.payload.get("primary_reason")
    if (
        not isinstance(reasons, list)
        or not reasons
        or len(set(reasons)) != len(reasons)
        or reasons != [reason for reason in EXIT_PRIORITY if reason in reasons]
        or any(reason not in EXIT_PRIORITY for reason in reasons)
        or primary != primary_exit_reason(reasons)
    ):
        raise RealScoringRefused(
            f"exit intent {exit_intent.event_id} has noncanonical trigger reasons"
        )
    planned = exit_intent.payload.get("planned_fill_session")
    decision = exit_intent.payload.get("decision_session")
    if (
        not isinstance(planned, str)
        or not isinstance(decision, str)
        or planned != _next_session(decision)
    ):
        raise RealScoringRefused(
            f"exit intent {exit_intent.event_id} has the wrong planned fill session"
        )
    return any(reason in {"pre_earnings", "earnings_unknown"} for reason in reasons)


def _operational_evidence_causes(
    by_id: dict[str, ledger.StoredEvent],
    event: ledger.StoredEvent,
    *,
    lineage_id: str,
    require_gate_go: bool | None,
    earnings_dependent: bool,
) -> list[str]:
    _require_recorded_at_or_after(
        event,
        session_close_utc(event.evaluation_session),
        detail=f"operational event {event.event_id}",
    )
    try:
        cause_events = [by_id[cause] for cause in event.causes]
    except KeyError as exc:
        raise RealScoringRefused(
            f"event {event.event_id} cites missing operational evidence"
        ) from exc
    gates = [item for item in cause_events if item.event_type == "data_gate"]
    if len(gates) != 1:
        raise RealScoringRefused(
            f"event {event.event_id} lacks one data-gate cause"
        )
    gate = gates[0]
    _validate_global_gate(
        by_id,
        gate,
        evaluation_session=event.evaluation_session,
        require_go=require_gate_go,
    )
    expected = [lineage_id, gate.event_id]
    sources = [
        item
        for item in cause_events
        if item.event_type == "source_health" and item.symbol == event.symbol
    ]
    if earnings_dependent:
        if len(sources) != 1:
            raise RealScoringRefused(
                f"event {event.event_id} lacks symbol source health"
            )
        source = sources[0]
        receipt_state = _validate_symbol_source(
            by_id,
            source,
            evaluation_session=event.evaluation_session,
            symbol=str(event.symbol),
            require_clear=None,
        )
        if event.event_type == "exit_intent":
            primary = event.payload.get("primary_reason")
            reasons = event.payload.get("trigger_reasons")
            if not isinstance(reasons, list):
                raise RealScoringRefused(
                    f"exit intent {event.event_id} has invalid trigger reasons"
                )
            pre_earnings = "pre_earnings" in reasons
            next_report = receipt_state.get("next_report")
            timing_valid = True
            if pre_earnings:
                try:
                    report = date.fromisoformat(str(next_report))
                    planned = str(event.payload["planned_fill_session"])
                    after_fill = _next_session(planned)
                    timing_valid = (
                        date.fromisoformat(planned) >= report
                        or date.fromisoformat(after_fill) >= report
                    )
                except (KeyError, TypeError, ValueError):
                    timing_valid = False
            if (
                event.payload.get("earnings_gate") != receipt_state.get("gate")
                or event.payload.get("next_report")
                != next_report
                or primary not in reasons
                or (primary == "earnings_unknown" and receipt_state.get("gate") != "UNKNOWN")
                or not timing_valid
            ):
                raise RealScoringRefused(
                    f"exit intent {event.event_id} disagrees with source health"
                )
        expected.append(source.event_id)
    elif sources:
        raise RealScoringRefused(
            f"event {event.event_id} has unnecessary symbol source health"
        )
    return expected


def _validate_market_lineage(
    *,
    events: list[ledger.StoredEvent],
    opening: ledger.StoredEvent,
    closing: ledger.StoredEvent,
    exit_intent: ledger.StoredEvent,
) -> None:
    by_id = {event.event_id: event for event in events}
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
    try:
        trigger_source = watcher_evaluation_session(
            date.fromisoformat(trigger_decision)
        ).isoformat()
        close_source = watcher_evaluation_session(
            date.fromisoformat(close_decision)
        ).isoformat()
    except ValueError as exc:
        raise _refuse("market close decision/source mapping is invalid", exc) from exc
    if (
        trigger_source != exit_intent.evaluation_session
        or close_source != closing.evaluation_session
    ):
        raise RealScoringRefused("market close decision/source mapping is inconsistent")
    planned = exit_intent.payload.get("planned_fill_session")
    if planned != _next_session(trigger_decision):
        raise RealScoringRefused("market exit intent has the wrong planned fill session")
    earnings_dependent = _validate_exit_reason_payload(exit_intent)
    exit_id = exit_intent.event_id
    gaps = [
        event
        for event in events
        if event.seq < closing.seq
        and event.event_type == "data_gap"
        and event.payload.get("exit_intent_id") == exit_id
    ]
    expected = str(planned)
    for gap in gaps:
        _require_recorded_at_or_after(
            gap,
            session_close_utc(gap.evaluation_session),
            detail=f"market exit retry gap {gap.event_id}",
        )
        gap_decision = gap.payload.get("decision_session")
        gap_source = gap.payload.get("source_evaluation_session")
        expected_gate_id = f"h7:data_gate:{gap.evaluation_session}"
        expected_source_id = (
            f"h7:source_health:{gap.evaluation_session}:{opening.symbol}"
        )
        expected_causes = [exit_id, expected_gate_id]
        if earnings_dependent:
            expected_causes.append(expected_source_id)
        gate = by_id.get(expected_gate_id)
        if gate is None:
            raise RealScoringRefused("market exit retry gap has no data gate")
        require_go = gap.payload.get("reason") != "exit_data_gate_no_go"
        _validate_global_gate(
            by_id,
            gate,
            evaluation_session=gap.evaluation_session,
            require_go=require_go,
        )
        if earnings_dependent:
            source = by_id.get(expected_source_id)
            if source is None:
                raise RealScoringRefused(
                    "market exit retry gap lacks symbol source health"
                )
            _validate_symbol_source(
                by_id,
                source,
                evaluation_session=gap.evaluation_session,
                symbol=str(opening.symbol),
                require_clear=None,
            )
        try:
            mapped_source = watcher_evaluation_session(
                date.fromisoformat(str(gap_decision))
            ).isoformat()
        except ValueError as exc:
            raise _refuse("market exit retry decision session is invalid", exc) from exc
        if (
            gap.event_id
            != f"s4.data_gap:{gap.evaluation_session}:exit_fill:{exit_id}"
            or gap.symbol != opening.symbol
            or gap.lane != opening.lane
            or gap.evaluation_session != gap_source
            or gap_decision != expected
            or mapped_source != gap.evaluation_session
            or gap.causes != expected_causes
            or set(gap.payload)
            != {
                "position_id",
                "phase",
                "reason",
                "chain_identity",
                "closes_identity",
                "exit_intent_id",
                "decision_session",
                "source_evaluation_session",
            }
            or gap.payload.get("position_id")
            != opening.payload.get("position_id")
            or gap.payload.get("phase") != "exit_fill"
            or not _nonempty_text(gap.payload.get("reason"))
            or not _nonempty_text(gap.payload.get("chain_identity"))
            or not _nonempty_text(gap.payload.get("closes_identity"))
        ):
            raise RealScoringRefused("market exit retry gap is not canonical")
        expected = _next_session(str(gap_decision))
    if close_decision != expected:
        raise RealScoringRefused(
            f"market close decision session {close_decision} is not due session {expected}"
        )
    if (
        closing.payload.get("opening_fill_id") != opening.event_id
        or closing.payload.get("position_id") != opening.payload.get("position_id")
        or closing.symbol != opening.symbol
        or closing.lane != opening.lane
        or closing.payload.get("structure") != opening.payload.get("structure")
        or closing.payload.get("primary_reason")
        != exit_intent.payload.get("primary_reason")
        or closing.payload.get("trigger_reasons")
        != exit_intent.payload.get("trigger_reasons")
    ):
        raise RealScoringRefused("market close changes opening lineage")

    if exit_intent.causes != _operational_evidence_causes(
        by_id,
        exit_intent,
        lineage_id=opening.event_id,
        require_gate_go=None,
        earnings_dependent=earnings_dependent,
    ):
        raise RealScoringRefused("market exit-intent causal lineage is invalid")
    if closing.causes != _operational_evidence_causes(
        by_id,
        closing,
        lineage_id=exit_intent.event_id,
        require_gate_go=True,
        earnings_dependent=earnings_dependent,
    ):
        raise RealScoringRefused("market closing-fill causal lineage is invalid")


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


def _validate_settlement_lineage(
    *,
    events: list[ledger.StoredEvent],
    opening: ledger.StoredEvent,
    closing: ledger.StoredEvent,
    structure: str,
) -> None:
    _require_recorded_at_or_after(
        closing,
        session_close_utc(closing.evaluation_session),
        detail=f"settlement close {closing.event_id}",
    )
    if (
        closing.symbol != opening.symbol
        or closing.lane != opening.lane
        or closing.payload.get("opening_fill_id") != opening.event_id
        or closing.payload.get("position_id") != opening.payload.get("position_id")
        or closing.payload.get("structure") != structure
    ):
        raise RealScoringRefused("settlement close changes opening lineage")
    if (
        closing.payload.get("transition") != "close"
        or closing.payload.get("primary_reason") != "expiration_settlement"
        or closing.payload.get("trigger_reasons") != ["expiration_settlement"]
        or closing.payload.get("trigger_session") != closing.evaluation_session
        or closing.payload.get("fill_session") != closing.evaluation_session
        or closing.payload.get("source_evaluation_session")
        != closing.evaluation_session
    ):
        raise RealScoringRefused("settlement close loses terminal session lineage")
    close_decision = closing.payload.get("decision_session")
    if not isinstance(close_decision, str):
        raise RealScoringRefused("settlement close has no operational decision session")
    try:
        mapped = watcher_evaluation_session(
            date.fromisoformat(close_decision)
        ).isoformat()
    except ValueError as exc:
        raise _refuse("settlement decision session is invalid", exc) from exc
    if mapped != closing.evaluation_session:
        raise RealScoringRefused(
            "settlement close decision/source mapping is inconsistent"
        )
    closes_identity = closing.payload.get("closes_identity")
    if (
        not isinstance(closes_identity, str)
        or not closes_identity
        or closing.payload.get("underlying_close_session")
        != closing.evaluation_session
        or closing.payload.get("underlying_close_identity") != closes_identity
    ):
        raise RealScoringRefused("settlement close is not receipt-bound")
    opening_closes_identity = opening.payload.get("closes_identity")
    if (
        not isinstance(opening_closes_identity, str)
        or not opening_closes_identity
        or opening.payload.get("underlying_close_session")
        != opening.evaluation_session
        or opening.payload.get("underlying_close_identity")
        != opening_closes_identity
    ):
        raise RealScoringRefused("settlement opening close is not receipt-bound")

    by_id = {event.event_id: event for event in events}
    gate_causes = [
        by_id[cause]
        for cause in closing.causes
        if cause in by_id and by_id[cause].event_type == "data_gate"
    ]
    if (
        len(gate_causes) != 1
        or gate_causes[0].evaluation_session != closing.evaluation_session
    ):
        raise RealScoringRefused("settlement close has no same-session data gate")
    _validate_global_gate(
        by_id,
        gate_causes[0],
        evaluation_session=closing.evaluation_session,
        require_go=None,
    )
    expected_causes = [opening.event_id]
    exit_intent_id = closing.payload.get("exit_intent_id")
    earnings_dependent = False
    if exit_intent_id is not None:
        exit_intent = (
            by_id.get(exit_intent_id) if isinstance(exit_intent_id, str) else None
        )
        if (
            exit_intent is None
            or exit_intent.event_type != "exit_intent"
            or exit_intent.symbol != opening.symbol
            or exit_intent.lane != opening.lane
            or exit_intent.payload.get("opening_fill_id") != opening.event_id
            or exit_intent.payload.get("position_id")
            != opening.payload.get("position_id")
        ):
            raise RealScoringRefused("settlement exit-intent lineage is invalid")
        earnings_dependent = _validate_exit_reason_payload(exit_intent)
        if exit_intent.causes != _operational_evidence_causes(
            by_id,
            exit_intent,
            lineage_id=opening.event_id,
            require_gate_go=None,
            earnings_dependent=earnings_dependent,
        ):
            raise RealScoringRefused("settlement exit-intent causal lineage is invalid")
        expected_causes.append(exit_intent.event_id)
    expected_causes.append(gate_causes[0].event_id)
    source_causes = [
        by_id[cause]
        for cause in closing.causes
        if cause in by_id
        and by_id[cause].event_type == "source_health"
        and by_id[cause].symbol == opening.symbol
    ]
    if earnings_dependent:
        if (
            len(source_causes) != 1
            or source_causes[0].evaluation_session != closing.evaluation_session
        ):
            raise RealScoringRefused(
                "earnings-dependent settlement lacks same-session source health"
            )
        _validate_symbol_source(
            by_id,
            source_causes[0],
            evaluation_session=closing.evaluation_session,
            symbol=str(opening.symbol),
            require_clear=None,
        )
        expected_causes.append(source_causes[0].event_id)
    elif source_causes:
        raise RealScoringRefused(
            "non-earnings settlement has unnecessary symbol source health"
        )
    if closing.causes != expected_causes:
        raise RealScoringRefused("settlement close causal lineage is invalid")


def _settlement_trade(
    *,
    events: list[ledger.StoredEvent],
    opening: ledger.StoredEvent,
    closing: ledger.StoredEvent,
) -> dict:
    structure = opening.payload.get("structure")
    action = opening.payload.get("action")
    if not isinstance(structure, str) or not isinstance(action, dict):
        raise RealScoringRefused("settlement opening action is malformed")
    if action.get("kind") != structure or action.get("lane") != opening.lane:
        raise RealScoringRefused("settlement opening action identity changed")
    _validate_settlement_lineage(
        events=events,
        opening=opening,
        closing=closing,
        structure=structure,
    )
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
        _settlement_trade(events=events, opening=opening, closing=closing)
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
    """Check finalization readiness without computing or disclosing a result."""
    events = _revalidate(session)
    stamp = _utc_now(now)
    if stamp < session_close_utc(session.window_end):
        raise RealScoringIncomplete(
            f"final decision session {session.window_end} has not completed"
        )
    _completed_pairs(session, events)
    return {
        "status": "RESULT_WITHHELD",
        "window_complete": True,
        "result_visible": False,
    }


def _require_review_passes(session: RealScoringSession) -> None:
    try:
        lines = session.facts_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise _refuse("review facts are unavailable", exc) from exc
    spec_chain_tokens = (
        f"base_spec_sha256={session.base_spec_sha256}",
        f"amendment_spec_sha256={session.amendment_spec_sha256}",
    )
    required = (
        (
            AMENDMENT_FACT_TAG,
            (
                f"contract={session.scoring_identity_contract}",
                *spec_chain_tokens,
                f"provenance={AMENDMENT_PROVENANCE}",
            ),
        ),
        (
            REVIEW_PASS_TAG,
            (
                "verdict=PASS",
                f"spec_sha256={session.amendment_spec_sha256}",
                *spec_chain_tokens,
            ),
        ),
        (
            OWNER_PASS_TAG,
            (
                "owner=carsyn",
                "verdict=PASS",
                f"spec_sha256={session.amendment_spec_sha256}",
                *spec_chain_tokens,
            ),
        ),
    )
    for tag, tokens in required:
        matches = [
            line
            for line in lines
            if (
                (fact := line.split("\t", 1)[-1]) == tag
                or fact.startswith(f"{tag} ")
            )
        ]
        if not matches or any(token not in matches[-1] for token in tokens):
            raise RealScoringRefused(
                f"finalization requires current {tag} fact with {tokens!r}"
            )
        if tag == AMENDMENT_FACT_TAG and not matches[-1].endswith(
            f"provenance={AMENDMENT_PROVENANCE}"
        ):
            raise RealScoringRefused(
                "finalization requires the exact amendment provenance"
            )


def _runtime_config_provenance(
    session: RealScoringSession, existing_receipt: dict | None
) -> str:
    if existing_receipt is None:
        return _config_provenance_hash(
            config_hash(), "runtime config hash provenance"
        )
    provenance = existing_receipt.get("config_provenance")
    expected_keys = {
        "authority",
        "registered_config_hash",
        "runtime_config_hash",
    }
    if (
        not isinstance(provenance, dict)
        or set(provenance) != expected_keys
        or provenance.get("authority") is not False
    ):
        raise RealScoringRefused(
            "existing score config provenance is malformed or authoritative"
        )
    registered = _config_provenance_hash(
        provenance.get("registered_config_hash"),
        "existing registered config provenance",
    )
    if registered != session.registered_config_hash:
        raise RealScoringRefused(
            "existing score config provenance changed its registered hash"
        )
    return _config_provenance_hash(
        provenance.get("runtime_config_hash"),
        "existing runtime config provenance",
    )


def _receipt_payload(
    *,
    session: RealScoringSession,
    result: dict,
    input_head: str,
    finalized_at: str,
    runtime_config_hash: str,
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
            "module": FROZEN_SCORER_MODULE,
            "scoring_identity_contract": session.scoring_identity_contract,
            "scoring_identity_hash": session.scoring_identity_hash,
            "cost_model_hash": cost_model_hash(),
            "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT,
            "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
            "forward_contracts": config.H7_FORWARD_CONTRACTS,
        },
        "config_provenance": {
            "authority": False,
            "registered_config_hash": session.registered_config_hash,
            "runtime_config_hash": runtime_config_hash,
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
        "spec_sha256": session.amendment_spec_sha256,
        "spec_chain": {
            "contract": session.scoring_identity_contract,
            "base_spec_path": str(BASE_SPEC_PATH.relative_to(REPO_ROOT)),
            "base_spec_sha256": session.base_spec_sha256,
            "amendment_spec_path": str(
                AMENDMENT_SPEC_PATH.relative_to(REPO_ROOT)
            ),
            "amendment_spec_sha256": session.amendment_spec_sha256,
        },
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
    runtime_config_hash = _runtime_config_provenance(session, existing_receipt)
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
            runtime_config_hash=runtime_config_hash,
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
                preview_real_score(session)
            except RealScoringIncomplete as exc:
                print(f"H7 SCORE NOT FINAL -- {exc}")
                return 0
            print(
                "H7 SCORE NOT FINAL -- RESULT WITHHELD PENDING REVIEW AND OWNER PASS"
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

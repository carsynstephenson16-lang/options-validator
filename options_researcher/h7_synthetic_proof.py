"""Stage 7 deterministic synthetic proof of H7 roadmap Stages 1-6.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. There is intentionally no CLI. The
runner creates only disposable fixture data below an explicit empty root and
unconditionally refuses the real forward store. Stage 8 remains the only
activation gate.
"""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pandas as pd

import config
from data.cache_runner import session_close_utc
from data.cache_schema import (
    V2_SYNTHETIC_AUDIT_SCHEMA,
    validate_v2_synthetic_audit_receipt,
)
from options_researcher import h7_data_gate
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_forward_book import derive_book, record_board_resolution
from options_researcher.h7_forward_scoring import (
    ScoringIncompleteError,
    score_forward_window,
)
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ActivationBoundaryError,
    LifecycleValidationError,
    observe_exit,
    process_entry_fill,
    process_exit_fill,
    record_entry_intent,
    record_owner_approval,
)
from options_researcher.h7_scope import watch_universe
from options_researcher.h7_source_health import symbol_health
from research.hashing import canonical_json, sha256_file, sha256_hex

FIXTURE_ID = "h7-stage7-v1"
BOUNDARY = "BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE"
REQUESTED_RUN_DATE = date(2026, 7, 12)
DECISION_SESSION = "2026-07-10"
ENTRY_SESSION = "2026-07-13"
EXIT_TRIGGER_SESSION = "2026-07-14"
EXIT_SESSION = "2026-07-15"
EXPIRATION = "2026-09-18"


def _clock(iso: str):
    return lambda: datetime.fromisoformat(iso)


def _root(path) -> Path:
    if path is None:
        raise ActivationBoundaryError("an explicit synthetic fixture root is required")
    root = Path(path)
    resolved = root.resolve(strict=False)
    real = REAL_FORWARD_STORE.resolve()
    if resolved == real or real in resolved.parents:
        raise ActivationBoundaryError(
            "the real H7 forward store is prohibited until Stage 8 activation"
        )
    if root.exists() and any(root.iterdir()):
        raise ValueError("the Stage-7 fixture root must be empty")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _assertion(symbol: str) -> dict:
    known = datetime.fromisoformat("2026-07-01T12:00:00+00:00")
    return {
        "record_id": f"S7-{symbol}",
        "symbol": symbol,
        "event_id": f"{symbol}-2026Q3",
        "fiscal_period": "2026Q3",
        "event_class": "actual_quarterly_earnings",
        "record_type": "assertion",
        "status": "confirmed",
        "expected_date": date(2026, 9, 18),
        "occurred_date": None,
        "session_timing": "amc",
        "source_type": "company_pr",
        "source_url": "https://fixture.invalid/ir",
        "known_as_of_utc": known,
        "checked_at_utc": known,
        "supersedes": "",
        "promoted_from": "",
        "notes": "stage7 synthetic fixture",
    }


def _chain(*, bid: float = 4.9, ask: float = 5.0) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": EXPIRATION,
                "strike": 100.0,
                "right": "C",
                "bid": bid,
                "ask": ask,
                "open_interest": 500,
                "iv": 0.5,
                "delta": 0.62,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.10,
                "timestamp": pd.Timestamp(
                    f"{DECISION_SESSION} 17:15:00",
                    tz="America/New_York",
                ),
                "bid_size": 17,
                "bid_condition": 50,
                "ask_size": 23,
                "ask_condition": 50,
                "iv_error": 0.001,
                "underlying_timestamp": pd.Timestamp(
                    f"{DECISION_SESSION} 16:00:00",
                    tz="America/New_York",
                ),
                "underlying_price": 100.0,
                "thetadata_client_version": "1.0.9",
            }
        ]
    )


def _write_market_fixtures(root: Path) -> tuple[Path, Path]:
    closes = root / "market" / "underlying"
    chains = root / "market" / "chains"
    closes.mkdir(parents=True)
    chains.mkdir(parents=True)
    for symbol in watch_universe():
        pd.DataFrame(
            {
                "date": ["2026-07-08", "2026-07-09", DECISION_SESSION],
                "close": [98.0, 99.0, 100.0],
            }
        ).to_parquet(closes / f"{symbol}.parquet", index=False)
        _chain().to_parquet(
            chains / f"{symbol}_{DECISION_SESSION}.parquet", index=False
        )
    _write_synthetic_full_audit_receipt(chains)
    return closes, chains


def _write_synthetic_full_audit_receipt(chain_dir: Path) -> Path:
    """Write a distinct receipt that can never authorize real v2 evidence."""
    chain_dir = Path(chain_dir)
    partitions = sorted(chain_dir.glob("*_????-??-??.parquet"))
    parsed = [path.stem.rsplit("_", 1) for path in partitions]
    symbols = sorted({symbol for symbol, _session in parsed})
    sessions = sorted({session for _symbol, session in parsed})
    file_hashes = {
        str(path.resolve()): sha256_file(path)
        for path in partitions
    }
    report = {
        "schema": V2_SYNTHETIC_AUDIT_SCHEMA,
        "boundary": "SYNTHETIC-ONLY",
        "output_namespace": str(chain_dir.resolve()),
        "symbols": symbols,
        "sessions": sessions,
        "file_hashes": file_hashes,
        "file_hashes_hash": sha256_hex(canonical_json(file_hashes)),
    }
    report["receipt_hash"] = sha256_hex(canonical_json(report))
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"))
    receipt = chain_dir / "_meta" / "synthetic_audit.json"
    receipt.parent.mkdir(exist_ok=True)
    if not receipt.exists() or receipt.read_text() != payload:
        receipt.write_text(payload)
    return receipt


def _event(
    event_id: str,
    event_type: str,
    session: str,
    *,
    symbol: str | None = None,
    lane: str | None = None,
    causes: list[str] | None = None,
    payload: dict | None = None,
) -> dict:
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": session_close_utc(session).isoformat(),
        "evaluation_session": session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes or [],
        "payload": payload or {},
    }


def _append(
    base: Path,
    event_id: str,
    event_type: str,
    session: str,
    *,
    symbol: str | None = None,
    lane: str | None = None,
    causes: list[str] | None = None,
    payload: dict | None = None,
    recorded: str,
):
    return ledger.append_event(
        _event(
            event_id,
            event_type,
            session,
            symbol=symbol,
            lane=lane,
            causes=causes,
            payload=payload,
        ),
        base_dir=base,
        clock=_clock(recorded),
    )


def _action() -> dict:
    return {
        "lane": "a",
        "kind": "long_call",
        "expiration": EXPIRATION,
        "strike": 100.0,
        "delta": 0.62,
        "cost": 506.30,
        "stop_ref": 80.0,
    }


def run_synthetic_proof(root) -> dict:
    """Run the frozen Stage-7 rehearsal and return a path-free receipt."""
    base = _root(root)
    event_store = base / "forward"
    closes, chains = _write_market_fixtures(base)
    names = sorted(watch_universe())

    assertions = [_assertion(symbol) for symbol in names]
    cutoff = session_close_utc(DECISION_SESSION)
    health = [
        symbol_health(
            symbol,
            date.fromisoformat(DECISION_SESSION),
            assertions,
            known_as_of=cutoff,
            warn_sessions=config.H7_SOURCE_HEALTH_WARN_SESSIONS,
        )
        for symbol in names
    ]
    if not all(item["healthy"] for item in health):
        raise AssertionError("the Stage-1 healthy fixture did not pass")
    missing_health = symbol_health(
        names[0],
        date.fromisoformat(DECISION_SESSION),
        [row for row in assertions if row["symbol"] != names[0]],
        known_as_of=cutoff,
        warn_sessions=config.H7_SOURCE_HEALTH_WARN_SESSIONS,
    )

    gate = h7_data_gate.evaluate(
        REQUESTED_RUN_DATE,
        close_dir=closes,
        chain_dir=chains,
        _receipt_validator=validate_v2_synthetic_audit_receipt,
    )
    if gate["whole_universe_verdict"] != "GO":
        raise AssertionError("the Stage-2 complete fixture did not pass")
    missing_chain = chains / f"{names[0]}_{DECISION_SESSION}.parquet"
    held_chain = missing_chain.with_suffix(".held")
    missing_chain.rename(held_chain)
    no_go = h7_data_gate.evaluate(
        REQUESTED_RUN_DATE,
        close_dir=closes,
        chain_dir=chains,
        _receipt_validator=validate_v2_synthetic_audit_receipt,
    )
    held_chain.rename(missing_chain)
    no_refusal_events = not event_store.exists()

    source_id = "s7:source:2026-07-10"
    gate_id = "s7:gate:2026-07-10"
    _append(
        event_store,
        source_id,
        "source_health",
        DECISION_SESSION,
        payload={"healthy_symbols": names, "healthy_count": len(names)},
        recorded="2026-07-11T01:00:00+00:00",
    )
    _append(
        event_store,
        gate_id,
        "data_gate",
        DECISION_SESSION,
        causes=[source_id],
        payload={
            "whole_universe_verdict": gate["whole_universe_verdict"],
            "go_count": gate["go_count"],
        },
        recorded="2026-07-11T01:00:01+00:00",
    )

    action = _action()
    over_sleeve = {
        "lane": "b",
        "kind": "long_call",
        "expiration": EXPIRATION,
        "strike": 100.0,
        "cost": 5800.0,
    }
    board = record_board_resolution(
        base_dir=event_store,
        evaluation_session=DECISION_SESSION,
        candidates=[
            {
                "symbol": "NVDA",
                "lane": "a",
                "session": DECISION_SESSION,
                "action": action,
            },
            {
                "symbol": "PLTR",
                "lane": "b",
                "session": DECISION_SESSION,
                "action": over_sleeve,
            },
        ],
        source_health_id=source_id,
        data_gate_id=gate_id,
        clock=_clock("2026-07-11T01:00:02+00:00"),
    )
    if len(board.accepted) != 1 or len(board.rejected) != 1:
        raise AssertionError("the Stage-5 board fixture resolved unexpectedly")

    intent = record_entry_intent(
        base_dir=event_store,
        symbol="NVDA",
        action=action,
        decision_chain=_chain(),
        decision_session=DECISION_SESSION,
        source_health_id=source_id,
        data_gate_id=gate_id,
        board_resolution_id=board.event_id,
        chain_identity="sha256:stage7-decision-chain",
        closes_identity="sha256:stage7-decision-closes",
        clock=_clock("2026-07-11T01:00:03+00:00"),
    )
    record_owner_approval(
        base_dir=event_store,
        entry_intent_id=intent.event_id,
        clock=_clock("2026-07-13T18:00:00+00:00"),
    )
    fill_source_id = "s7:source:2026-07-13:NVDA"
    fill_gate_id = "s7:gate:2026-07-13"
    _append(
        event_store,
        fill_source_id,
        "source_health",
        ENTRY_SESSION,
        symbol="NVDA",
        lane="a",
        payload={"gate": "CLEAR", "healthy": True},
        recorded="2026-07-14T01:00:00+00:00",
    )
    _append(
        event_store,
        fill_gate_id,
        "data_gate",
        ENTRY_SESSION,
        payload={"whole_universe_verdict": "GO"},
        recorded="2026-07-14T01:00:01+00:00",
    )

    before_refusal = ledger.verify(event_store).count
    same_session_refused = False
    try:
        process_entry_fill(
            base_dir=event_store,
            entry_intent_id=intent.event_id,
            fill_session=DECISION_SESSION,
            chain=_chain(),
            source_health_id=fill_source_id,
            data_gate_id=fill_gate_id,
            chain_identity="sha256:stage7-fill-chain",
            closes_identity="sha256:stage7-fill-closes",
            underlying_close=100.0,
            clock=_clock("2026-07-14T01:00:02+00:00"),
        )
    except LifecycleValidationError:
        same_session_refused = ledger.verify(event_store).count == before_refusal

    missing_benchmark_refused = False
    try:
        process_entry_fill(
            base_dir=event_store,
            entry_intent_id=intent.event_id,
            fill_session=ENTRY_SESSION,
            chain=_chain(),
            source_health_id=fill_source_id,
            data_gate_id=fill_gate_id,
            chain_identity="sha256:stage7-fill-chain",
            closes_identity="sha256:stage7-fill-closes",
            clock=_clock("2026-07-14T01:00:02+00:00"),
        )
    except LifecycleValidationError:
        missing_benchmark_refused = ledger.verify(event_store).count == before_refusal

    opening = process_entry_fill(
        base_dir=event_store,
        entry_intent_id=intent.event_id,
        fill_session=ENTRY_SESSION,
        chain=_chain(),
        source_health_id=fill_source_id,
        data_gate_id=fill_gate_id,
        chain_identity="sha256:stage7-fill-chain",
        closes_identity="sha256:stage7-fill-closes",
        underlying_close=100.0,
        clock=_clock("2026-07-14T01:00:02+00:00"),
    )

    score_head = ledger.verify(event_store).head
    incomplete_score_refused = False
    try:
        score_forward_window(
            base_dir=event_store,
            window_start=DECISION_SESSION,
            window_end=DECISION_SESSION,
        )
    except ScoringIncompleteError:
        incomplete_score_refused = ledger.verify(event_store).head == score_head

    observation_gate_id = "s7:gate:2026-07-14"
    _append(
        event_store,
        observation_gate_id,
        "data_gate",
        EXIT_TRIGGER_SESSION,
        payload={"whole_universe_verdict": "GO"},
        recorded="2026-07-15T01:00:00+00:00",
    )
    exit_intent = observe_exit(
        base_dir=event_store,
        position_id=opening.payload["position_id"],
        evaluation_session=EXIT_TRIGGER_SESSION,
        chain=_chain(bid=10.5, ask=10.6),
        data_gate_id=observation_gate_id,
        chain_identity="sha256:stage7-exit-observation-chain",
        closes_identity="sha256:stage7-exit-observation-closes",
        underlying_close=110.0,
        earnings_gate="CLEAR",
        next_report=None,
        source_health_id=None,
        clock=_clock("2026-07-15T01:00:01+00:00"),
    )
    if exit_intent is None or exit_intent.event_type != "exit_intent":
        raise AssertionError("the Stage-4 exit fixture did not trigger")
    exit_gate_id = "s7:gate:2026-07-15"
    _append(
        event_store,
        exit_gate_id,
        "data_gate",
        EXIT_SESSION,
        payload={"whole_universe_verdict": "GO"},
        recorded="2026-07-16T01:00:00+00:00",
    )
    closing = process_exit_fill(
        base_dir=event_store,
        exit_intent_id=exit_intent.event_id,
        fill_session=EXIT_SESSION,
        chain=_chain(bid=9.0, ask=9.2),
        data_gate_id=exit_gate_id,
        chain_identity="sha256:stage7-exit-fill-chain",
        closes_identity="sha256:stage7-exit-fill-closes",
        underlying_close=108.0,
        clock=_clock("2026-07-16T01:00:01+00:00"),
    )

    book = derive_book(
        base_dir=event_store,
        evaluation_session=EXIT_SESSION,
        risk_month="2026-07",
    )
    before_score_head = ledger.verify(event_store).head
    scored = score_forward_window(
        base_dir=event_store,
        window_start=DECISION_SESSION,
        window_end=DECISION_SESSION,
    )
    score_read_only = ledger.verify(event_store).head == before_score_head

    verified = ledger.verify(event_store)
    tampered = base / "tampered-copy"
    shutil.copytree(event_store, tampered)
    events_path = tampered / "events.jsonl"
    text = events_path.read_text()
    events_path.write_text(text.replace('"schema_version":1', '"schema_version":2', 1))
    tamper_rejected = False
    try:
        ledger.verify(tampered)
    except ledger.LedgerError:
        tamper_rejected = True

    trade = scored["trades"][0]
    return {
        "schema_version": 1,
        "fixture_id": FIXTURE_ID,
        "boundary": BOUNDARY,
        "source_health": {"healthy": len(health), "universe": len(names)},
        "data_gate": {
            "verdict": gate["whole_universe_verdict"],
            "go_count": gate["go_count"],
            "evaluation_session": gate["evaluation_session"],
        },
        "ledger": {
            "valid": not verified.empty,
            "event_count": verified.count,
            "head": verified.head,
        },
        "lifecycle": {
            "decision_session": DECISION_SESSION,
            "entry_session": opening.payload["fill_session"],
            "exit_trigger_session": exit_intent.payload["trigger_session"],
            "exit_session": closing.payload["fill_session"],
            "entry_event_id": opening.event_id,
            "exit_event_id": closing.event_id,
        },
        "book": {
            "accepted_symbol": board.accepted[0]["symbol"],
            "rejected_symbol": board.rejected[0]["symbol"],
            "rejected_reason": board.rejected[0]["rejection"],
            "month_actual_risk_after_close": book.month_actual_risk,
            "open_symbols_after_close": list(book.open_symbols),
        },
        "scoring": {
            "n_trades": scored["n_trades"],
            "overall_verdict": scored["overall"]["verdict"],
            "lane_a_verdict": scored["lanes"]["a"]["verdict"],
            "pnl": trade["pnl"],
            "underlying_move": trade["underlying_move"],
            "ledger_head": scored["ledger_head"],
        },
        "refusals": {
            "source_health_missing": missing_health["healthy"] is False,
            "data_gate_missing_chain": (
                no_go["whole_universe_verdict"] == "NO_GO" and no_refusal_events
            ),
            "ledger_tamper": tamper_rejected,
            "same_session_entry": same_session_refused,
            "missing_entry_benchmark": missing_benchmark_refused,
            "over_sleeve_candidate": (
                board.rejected[0]["rejection"] == "sleeve_exhausted"
            ),
            "incomplete_score": incomplete_score_refused,
            "score_read_only": score_read_only,
        },
    }

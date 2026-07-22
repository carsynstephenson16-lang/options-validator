import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import config
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_exit_session as exit_session
from options_researcher import h7_paper_lifecycle as lifecycle
from options_researcher import h7_window_registration as registration
from options_researcher.h7_scope import scope_identity
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    config_hash,
)
from research.receipts import input_files, make_receipt

DECISION = "2026-07-21"
EVALUATION = "2026-07-20"
SOURCE_HASH = "c" * 64


def _clock(value: str):
    stamp = datetime.fromisoformat(value)
    return lambda: stamp


def _owner_inputs() -> dict:
    return {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "synthetic exit fixture",
        "WINDOW_START_DECISION_SESSION": "2026-07-20",
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS sessions from start",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2027-02-28",
        "THETADATA_CONFIRMATION_EVIDENCE": "synthetic fixture",
    }


def _registration_evidence() -> dict:
    return {
        "review_evidence": "synthetic fixture",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:fixture",
        "data_gate_evidence_id": "dg:fixture",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }


def _chain(*, bid: float = 10.50, ask: float = 10.60) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2027-01-15",
                "strike": 100.0,
                "right": "C",
                "bid": bid,
                "ask": ask,
                "open_interest": 500,
                "delta": 0.60,
            }
        ]
    )


def _put_chain(*, short_bid=4.9, short_ask=5.0, long_bid=2.0, long_ask=2.1):
    return pd.DataFrame(
        [
            {
                "expiration": "2027-01-15",
                "strike": 100.0,
                "right": "P",
                "bid": short_bid,
                "ask": short_ask,
                "open_interest": 500,
                "delta": -0.30,
            },
            {
                "expiration": "2027-01-15",
                "strike": 90.0,
                "right": "P",
                "bid": long_bid,
                "ask": long_ask,
                "open_interest": 500,
                "delta": -0.15,
            },
        ]
    )


class ExitSessionCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.base = self.root / "forward"
        self.scope = scope_identity()
        self.included = ("AMD",)
        excluded = [name for name in self.scope["symbols"] if name not in self.included]
        registration.register_window(
            owner=_owner_inputs(),
            evidence=_registration_evidence(),
            base_dir=self.base,
            universe_manifest={
                "scope_id": self.scope["scope_id"],
                "scope_hash": self.scope["scope_hash"],
                "included": list(self.included),
                "excluded": [
                    {"symbol": symbol, "reason": "EARNINGS-UNKNOWN"}
                    for symbol in excluded
                ],
                "trim_rule": "source_health_ready_at_pinned_session",
            },
        )
        self.registration = ledger.read_events(self.base)[0]
        self._append_open_position()
        self.source_hash = patch(
            "options_researcher.h7_exit_session.diagnostic_source_hash",
            return_value=SOURCE_HASH,
        )
        self.source_hash.start()
        self.addCleanup(self.source_hash.stop)
        self.gate_path = self._write_receipts()

    def _append_open_position(self) -> None:
        self._append_position(
            event_id="open:AMD:a",
            position_id="position:AMD:a",
            lane="a",
            structure="long_call",
            expiration="2027-01-15",
            legs=[
                {
                    "name": "long",
                    "expiration": "2027-01-15",
                    "strike": 100.0,
                    "right": "C",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": 0.60,
                    "fill_price": 5.16,
                }
            ],
        )

    def _append_position(
        self,
        *,
        event_id: str,
        position_id: str,
        lane: str,
        structure: str,
        expiration: str,
        legs: list[dict],
    ) -> None:
        action = {
            "lane": lane,
            "kind": structure,
            "expiration": expiration,
            "cost": 517.3,
            "max_loss": 517.3,
            "stop_ref": 80.0,
        }
        if structure == "long_call":
            action.update(strike=100.0, delta=0.60)
        elif structure == "bull_put_spread":
            action.update(short_strike=100.0, long_strike=90.0)
        net_debit = -2.82 if structure == "bull_put_spread" else 5.16
        ledger.append_event(
            {
                "schema_version": ledger.SCHEMA_VERSION,
                "event_id": event_id,
                "event_type": "paper_fill",
                "occurred_at_utc": f"{EVALUATION}T20:00:00+00:00",
                "evaluation_session": EVALUATION,
                "symbol": "AMD",
                "lane": lane,
                "causes": [self.registration.event_id],
                "payload": {
                    "transition": "open",
                    "position_id": position_id,
                    "entry_intent_id": f"entry:{position_id}",
                    "decision_session": "2026-07-20",
                    "fill_session": EVALUATION,
                    "structure": structure,
                    "action": action,
                    "legs": legs,
                    "cash_kind": "credit" if net_debit < 0 else "debit",
                    "net_debit_per_share": net_debit,
                    "commission": config.COMMISSION_PER_CONTRACT,
                    "at_risk": 517.3,
                    "chain_identity": "sha256:opening-chain",
                    "closes_identity": "sha256:opening-close",
                    "underlying_close": 100.0,
                    "underlying_close_session": EVALUATION,
                    "underlying_close_identity": "sha256:opening-close",
                },
            },
            base_dir=self.base,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

    def _write_receipts(
        self,
        *,
        evaluation: str = EVALUATION,
        requested: str = DECISION,
        verdict: str = "GO",
        amd_gate: str = "CLEAR",
        amd_healthy: bool = True,
        linked: bool = True,
        chain_frame: pd.DataFrame | None = None,
        close_value: float = 100.0,
        missing_close_symbol: str | None = None,
        amd_next_report: str | None = None,
    ) -> Path:
        cache = self.root / "cache"
        cache.mkdir(exist_ok=True)
        bindings: dict[str, Path] = {}
        for symbol in self.scope["symbols"]:
            close_path = cache / f"close-{symbol}-{evaluation}.parquet"
            chain_path = cache / f"chain-{symbol}-{evaluation}.parquet"
            if symbol != missing_close_symbol:
                pd.DataFrame([{"date": evaluation, "close": close_value}]).to_parquet(
                    close_path, index=False
                )
            elif close_path.exists():
                close_path.unlink()
            (chain_frame if chain_frame is not None else _chain()).to_parquet(
                chain_path, index=False
            )
            bindings[f"close:{symbol}"] = close_path
            bindings[f"chain:{symbol}"] = chain_path

        source_path = self.root / f"source-{evaluation}.json"
        states = {
            symbol: {
                "symbol": symbol,
                "healthy": amd_healthy if symbol == "AMD" else True,
                "gate": amd_gate if symbol == "AMD" else "CLEAR",
                "next_report": amd_next_report if symbol == "AMD" else None,
            }
            for symbol in self.scope["symbols"]
        }
        unhealthy = sorted(
            symbol for symbol, state in states.items() if state["healthy"] is not True
        )
        source = make_receipt(
            "source_health",
            {
                "evaluation_session": evaluation,
                "requested_run_date": requested,
                "scope": self.scope,
                "healthy_count": len(states) - len(unhealthy),
                "unhealthy_count": len(unhealthy),
                "unhealthy_symbols": unhealthy,
                "activation_ready": not unhealthy,
                "symbols": states,
                "input_files": {},
                "config_hash": config_hash(),
                "source_hash": SOURCE_HASH,
                "source_hash_contract": DIAGNOSTIC_SOURCE_HASH_VERSION,
            },
        )
        source_path.write_text(json.dumps(source), encoding="utf-8")

        gate_path = self.root / f"gate-{evaluation}.json"
        gate = make_receipt(
            "data_gate",
            {
                "evaluation_session": evaluation,
                "requested_run_date": requested,
                "scope": self.scope,
                "whole_universe_verdict": verdict,
                "go_count": len(states) if verdict == "GO" else 0,
                "no_go_count": 0 if verdict == "GO" else len(states),
                "symbols": {
                    symbol: {"symbol": symbol, "verdict": verdict}
                    for symbol in self.scope["symbols"]
                },
                "input_files": input_files(bindings),
                "source_health_receipt_hash": (
                    source["receipt_hash"] if linked else "f" * 64
                ),
                "source_health_receipt_path": str(source_path),
                "config_hash": config_hash(),
                "source_hash": SOURCE_HASH,
                "source_hash_contract": DIAGNOSTIC_SOURCE_HASH_VERSION,
            },
        )
        gate_path.write_text(json.dumps(gate), encoding="utf-8")
        return gate_path

    def open(self, **over):
        kwargs = {
            "base_dir": self.base,
            "decision_session": DECISION,
            "source_evaluation_session": EVALUATION,
            "data_gate_receipt_path": self.gate_path,
            "now": datetime(2026, 7, 22, 1, tzinfo=timezone.utc),
        }
        kwargs.update(over)
        return exit_session.open_real_exit_session(**kwargs)


class TestExitAuthority(ExitSessionCase):
    def test_factory_carries_registration_receipts_cohort_and_bindings(self):
        session = self.open()

        self.assertEqual(session.activation_event_id, self.registration.event_id)
        self.assertEqual(session.registration_record_hash, self.registration.record_hash)
        self.assertEqual(session.decision_session, DECISION)
        self.assertEqual(session.evaluation_session, EVALUATION)
        self.assertEqual(session.included_symbols, self.included)
        self.assertEqual(session.data_gate_verdict, "GO")
        self.assertEqual(len(session.input_bindings), 2 * len(self.scope["symbols"]))
        self.assertEqual(session.authorized_position_ids, ("position:AMD:a",))

    def test_factory_accepts_no_go_and_unhealthy_open_name_for_exit_management(self):
        self.gate_path = self._write_receipts(
            verdict="NO_GO", amd_gate="UNKNOWN", amd_healthy=False
        )

        session = self.open()

        self.assertEqual(session.data_gate_verdict, "NO_GO")
        state = exit_session.source_health_state(session, "AMD")
        self.assertEqual(state.gate, "UNKNOWN")
        self.assertFalse(state.healthy)

    def test_unlinked_receipt_and_changed_cache_bytes_are_refused(self):
        self.gate_path = self._write_receipts(linked=False)
        with self.assertRaises(exit_session.ExitSessionRefused):
            self.open()

        self.gate_path = self._write_receipts()
        changed = self.root / "cache" / f"chain-AMD-{EVALUATION}.parquet"
        _chain(bid=9.0, ask=9.2).to_parquet(changed, index=False)
        with self.assertRaises(exit_session.ExitSessionRefused):
            self.open()

    def test_exit_evidence_faithfully_records_no_go_and_unhealthy_symbol(self):
        self.gate_path = self._write_receipts(
            verdict="NO_GO", amd_gate="UNKNOWN", amd_healthy=False
        )
        session = self.open()

        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=True
        )

        self.assertEqual(evidence.data_gate.payload["whole_universe_verdict"], "NO_GO")
        self.assertIsNotNone(evidence.symbol_source_health)
        self.assertEqual(evidence.symbol_source_health.payload["gate"], "UNKNOWN")
        self.assertFalse(evidence.symbol_source_health.payload["healthy"])
        stored = {event.event_id: event for event in ledger.read_events(self.base)}
        self.assertIn(f"h7:data_gate:{EVALUATION}", stored)
        self.assertIn(f"h7:source_health:{EVALUATION}:AMD", stored)


class TestRealLifecycleSeam(ExitSessionCase):
    def _observe(
        self,
        *,
        position_id="position:AMD:a",
        include_symbol=False,
    ):
        session = self.open()
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=include_symbol
        )
        state = exit_session.source_health_state(session, "AMD")
        return lifecycle.observe_exit(
            base_dir=session,
            position_id=position_id,
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(session, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate=state.gate,
            next_report=state.next_report,
            source_health_id=(
                evidence.symbol_source_health.event_id
                if evidence.symbol_source_health is not None
                else None
            ),
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

    def test_forged_real_exit_session_is_refused(self):
        from dataclasses import replace

        forged = replace(self.open(), _authority_token=object())
        evidence = exit_session.record_exit_evidence(
            self.open(), symbol="AMD", include_symbol=False
        )

        with self.assertRaises(lifecycle.ActivationBoundaryError):
            lifecycle.observe_exit(
                base_dir=forged,
                position_id="position:AMD:a",
                evaluation_session=EVALUATION,
                chain=_chain(),
                data_gate_id=evidence.data_gate.event_id,
                chain_identity="sha256:exit-chain",
                closes_identity="sha256:exit-close",
                underlying_close=100.0,
                earnings_gate="CLEAR",
                next_report=None,
                source_health_id=None,
                clock=_clock("2026-07-21T01:00:00+00:00"),
            )

    def test_real_profit_target_uses_decision_date_for_t_plus_one(self):
        session = self.open()
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=False
        )

        result = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:AMD:a",
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(session, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.payload["decision_session"], DECISION)
        self.assertEqual(result.payload["source_evaluation_session"], EVALUATION)
        self.assertEqual(result.payload["planned_fill_session"], "2026-07-22")
        stored = ledger.read_events(self.base)[-1]
        self.assertEqual(stored.evaluation_session, EVALUATION)

    def test_real_no_go_records_a_causally_linked_gap(self):
        self.gate_path = self._write_receipts(verdict="NO_GO")
        session = self.open()
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=False
        )

        result = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:AMD:a",
            evaluation_session=EVALUATION,
            chain=pd.DataFrame(),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=None,
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, "data_gap")
        stored = ledger.read_events(self.base)[-1]
        self.assertIn("open:AMD:a", stored.causes)
        self.assertIn(evidence.data_gate.event_id, stored.causes)

    def test_go_priceable_no_trigger_leaves_data_gate_evidence(self):
        quiet = _chain(bid=5.0, ask=5.1)
        self.gate_path = self._write_receipts(chain_frame=quiet)
        session = self.open()
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=False
        )

        result = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:AMD:a",
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(session, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

        self.assertIsNone(result)
        types = [event.event_type for event in ledger.read_events(self.base)]
        self.assertIn("data_gate", types)
        self.assertNotIn("exit_intent", types)

    def test_real_missing_quote_records_data_gap(self):
        self.gate_path = self._write_receipts(
            chain_frame=pd.DataFrame(
                columns=[
                    "expiration",
                    "strike",
                    "right",
                    "bid",
                    "ask",
                    "open_interest",
                    "delta",
                ]
            )
        )

        result = self._observe()

        self.assertEqual(result.event_type, "data_gap")
        self.assertIn("missing", result.payload["reason"])

    def test_real_scheduled_dte_exit(self):
        self._append_position(
            event_id="open:scheduled",
            position_id="position:scheduled",
            lane="a",
            structure="long_call",
            expiration="2026-08-14",
            legs=[
                {
                    "name": "long",
                    "expiration": "2026-08-14",
                    "strike": 100.0,
                    "right": "C",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": 0.60,
                    "fill_price": 5.16,
                }
            ],
        )
        scheduled_chain = _chain(bid=5.0, ask=5.1)
        scheduled_chain["expiration"] = "2026-08-14"
        self.gate_path = self._write_receipts(chain_frame=scheduled_chain)

        result = self._observe(position_id="position:scheduled")

        self.assertEqual(result.payload["primary_reason"], "scheduled_dte")

    def test_real_underlying_stop_exit(self):
        self.gate_path = self._write_receipts(
            chain_frame=_chain(bid=5.0, ask=5.1), close_value=70.0
        )

        result = self._observe()

        self.assertEqual(result.payload["primary_reason"], "underlying_stop")

    def _append_credit_position(self) -> None:
        self._append_position(
            event_id="open:credit",
            position_id="position:credit",
            lane="c",
            structure="bull_put_spread",
            expiration="2027-01-15",
            legs=[
                {
                    "name": "short",
                    "expiration": "2027-01-15",
                    "strike": 100.0,
                    "right": "P",
                    "side": "sell",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": -0.30,
                    "fill_price": 4.95,
                },
                {
                    "name": "long",
                    "expiration": "2027-01-15",
                    "strike": 90.0,
                    "right": "P",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 2.0,
                    "raw_ask": 2.1,
                    "raw_open_interest": 500,
                    "raw_delta": -0.15,
                    "fill_price": 2.13,
                },
            ],
        )

    def test_real_credit_stop_path(self):
        self._append_credit_position()
        self.gate_path = self._write_receipts(
            chain_frame=_put_chain(short_ask=8.0, long_bid=1.0)
        )

        result = self._observe(position_id="position:credit")

        self.assertEqual(result.payload["primary_reason"], "credit_stop")

    def test_real_credit_profit_target_path(self):
        self._append_credit_position()
        self.gate_path = self._write_receipts(
            chain_frame=_put_chain(
                short_bid=0.99,
                short_ask=1.0,
                long_bid=0.1,
                long_ask=0.11,
            )
        )

        result = self._observe(position_id="position:credit")

        self.assertEqual(result.payload["primary_reason"], "profit_target")

    def test_real_pre_earnings_exit_publishes_actual_source_evidence(self):
        self._append_credit_position()
        self.gate_path = self._write_receipts(
            chain_frame=_put_chain(), amd_next_report="2026-07-22"
        )

        result = self._observe(position_id="position:credit", include_symbol=True)

        self.assertEqual(result.payload["primary_reason"], "pre_earnings")
        self.assertIn(
            f"h7:source_health:{EVALUATION}:AMD",
            ledger.read_events(self.base)[-1].causes,
        )

    def test_earnings_unknown_uses_actual_unhealthy_source_evidence(self):
        self._append_position(
            event_id="open:AMD:c",
            position_id="position:AMD:c",
            lane="c",
            structure="bull_put_spread",
            expiration="2027-01-15",
            legs=[
                {
                    "name": "short",
                    "expiration": "2027-01-15",
                    "strike": 100.0,
                    "right": "P",
                    "side": "sell",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": -0.30,
                    "fill_price": 4.95,
                },
                {
                    "name": "long",
                    "expiration": "2027-01-15",
                    "strike": 90.0,
                    "right": "P",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 2.0,
                    "raw_ask": 2.1,
                    "raw_open_interest": 500,
                    "raw_delta": -0.15,
                    "fill_price": 2.13,
                },
            ],
        )
        self.gate_path = self._write_receipts(
            amd_gate="UNKNOWN", amd_healthy=False
        )
        session = self.open()
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=True
        )

        result = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:AMD:c",
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(session, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate="UNKNOWN",
            next_report=None,
            source_health_id=evidence.symbol_source_health.event_id,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )

        self.assertEqual(result.payload["primary_reason"], "earnings_unknown")
        stored = ledger.read_events(self.base)[-1]
        self.assertIn(evidence.symbol_source_health.event_id, stored.causes)

    def test_real_fill_uses_mapped_operational_session(self):
        decision = self.open()
        decision_evidence = exit_session.record_exit_evidence(
            decision, symbol="AMD", include_symbol=False
        )
        intent = lifecycle.observe_exit(
            base_dir=decision,
            position_id="position:AMD:a",
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(decision, "AMD"),
            data_gate_id=decision_evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(decision, "chain:AMD"),
            closes_identity=exit_session.binding_identity(decision, "close:AMD"),
            underlying_close=exit_session.load_bound_close(decision, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )
        fill_evaluation = "2026-07-21"
        fill_decision = "2026-07-22"
        gate = self._write_receipts(
            evaluation=fill_evaluation, requested=fill_decision
        )
        fill_session = exit_session.open_real_exit_session(
            base_dir=self.base,
            decision_session=fill_decision,
            source_evaluation_session=fill_evaluation,
            data_gate_receipt_path=gate,
            now=datetime(2026, 7, 23, 1, tzinfo=timezone.utc),
        )
        fill_evidence = exit_session.record_exit_evidence(
            fill_session, symbol="AMD", include_symbol=False
        )

        closed = lifecycle.process_exit_fill(
            base_dir=fill_session,
            exit_intent_id=intent.event_id,
            fill_session=fill_evaluation,
            chain=exit_session.load_bound_chain(fill_session, "AMD"),
            data_gate_id=fill_evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(
                fill_session, "chain:AMD"
            ),
            closes_identity=exit_session.binding_identity(
                fill_session, "close:AMD"
            ),
            underlying_close=exit_session.load_bound_close(fill_session, "AMD"),
            clock=_clock("2026-07-22T01:00:00+00:00"),
        )

        self.assertEqual(closed.event_type, "paper_fill")
        self.assertEqual(closed.payload["decision_session"], fill_decision)
        self.assertEqual(closed.payload["source_evaluation_session"], fill_evaluation)
        self.assertEqual(closed.payload["fill_session"], fill_evaluation)


class TestPostWindowAndSettlement(ExitSessionCase):
    def test_post_window_authority_is_limited_to_in_window_positions(self):
        evaluation = "2026-10-30"
        decision = "2026-11-02"
        gate = self._write_receipts(evaluation=evaluation, requested=decision)

        session = exit_session.open_real_exit_session(
            base_dir=self.base,
            decision_session=decision,
            source_evaluation_session=evaluation,
            data_gate_receipt_path=gate,
            now=datetime(2026, 11, 3, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(session.authorized_position_ids, ("position:AMD:a",))
        with self.assertRaises(lifecycle.ActivationBoundaryError):
            lifecycle.record_entry_intent(
                base_dir=session,
                symbol="AMD",
                action={},
                decision_chain=pd.DataFrame(),
                decision_session=evaluation,
                source_health_id="unused",
                data_gate_id="unused",
                board_resolution_id="unused",
                chain_identity="unused",
                closes_identity="unused",
            )

    def test_unfinished_eod_is_refused(self):
        evaluation = "2026-07-22"
        gate = self._write_receipts(evaluation=evaluation, requested=evaluation)

        with self.assertRaises(exit_session.ExitSessionRefused):
            exit_session.open_real_exit_session(
                base_dir=self.base,
                decision_session=evaluation,
                source_evaluation_session=evaluation,
                data_gate_receipt_path=gate,
                now=datetime(2026, 7, 22, 19, tzinfo=timezone.utc),
            )

    def test_expiration_settles_at_receipt_bound_intrinsic(self):
        expiration = "2026-07-24"
        self._append_position(
            event_id="open:settlement",
            position_id="position:settlement",
            lane="a",
            structure="long_call",
            expiration=expiration,
            legs=[
                {
                    "name": "long",
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": "C",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": 0.60,
                    "fill_price": 5.16,
                }
            ],
        )
        gate = self._write_receipts(
            evaluation=expiration,
            requested=expiration,
            close_value=120.0,
        )
        session = exit_session.open_real_exit_session(
            base_dir=self.base,
            decision_session=expiration,
            source_evaluation_session=expiration,
            data_gate_receipt_path=gate,
            now=datetime(2026, 7, 25, 1, tzinfo=timezone.utc),
        )
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=False
        )

        settled = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:settlement",
            evaluation_session=expiration,
            chain=exit_session.load_bound_chain(session, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-25T01:00:00+00:00"),
        )

        self.assertEqual(settled.event_type, "paper_fill")
        self.assertEqual(settled.payload["settlement_method"], "intrinsic_at_close")
        self.assertEqual(settled.payload["net_close_credit_per_share"], 20.0)
        self.assertEqual(settled.payload["commission"], config.COMMISSION_PER_CONTRACT)
        positions = lifecycle._replay_positions_at_base(self.base)
        self.assertEqual(
            next(row for row in positions if row.position_id == "position:settlement").state,
            "closed",
        )

    def test_missing_expiration_close_uses_conservative_terminal_fallback(self):
        expiration = "2026-07-24"
        self._append_position(
            event_id="open:fallback",
            position_id="position:fallback",
            lane="a",
            structure="long_call",
            expiration=expiration,
            legs=[
                {
                    "name": "long",
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": "C",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": 0.60,
                    "fill_price": 5.16,
                }
            ],
        )
        gate = self._write_receipts(
            evaluation=expiration,
            requested=expiration,
            verdict="NO_GO",
            missing_close_symbol="AMD",
        )
        session = exit_session.open_real_exit_session(
            base_dir=self.base,
            decision_session=expiration,
            source_evaluation_session=expiration,
            data_gate_receipt_path=gate,
            now=datetime(2026, 7, 25, 1, tzinfo=timezone.utc),
        )
        evidence = exit_session.record_exit_evidence(
            session, symbol="AMD", include_symbol=False
        )

        settled = lifecycle.observe_exit(
            base_dir=session,
            position_id="position:fallback",
            evaluation_session=expiration,
            chain=pd.DataFrame(),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(session, "chain:AMD"),
            closes_identity=exit_session.binding_identity(session, "close:AMD"),
            underlying_close=exit_session.load_bound_close(session, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-25T01:00:00+00:00"),
        )

        self.assertEqual(
            settled.payload["settlement_method"], "conservative_full_loss"
        )
        self.assertEqual(settled.payload["net_close_credit_per_share"], 0.0)
        self.assertEqual(settled.payload["commission"], 0.0)


class TestExitBatchAndCli(ExitSessionCase):
    def _snapshot(self) -> dict[str, bytes]:
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }

    def test_status_cli_validates_authority_without_writing(self):
        before = self._snapshot()

        with (
            patch.object(exit_session, "REAL_FORWARD_STORE", self.base),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = exit_session.main(
                [
                    "status",
                    "--data-gate-receipt",
                    str(self.gate_path),
                    "--decision-session",
                    DECISION,
                    "--source-evaluation-session",
                    EVALUATION,
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("H7 EXIT SESSION READY", output.getvalue())
        self.assertEqual(self._snapshot(), before)

    def test_monitor_batch_leaves_evidence_when_nothing_fires(self):
        self.gate_path = self._write_receipts(
            chain_frame=_chain(bid=5.0, ask=5.1)
        )

        report = exit_session.monitor_real_exits(
            self.open(), clock=_clock("2026-07-21T01:00:00+00:00")
        )

        self.assertFalse(report.failed)
        self.assertEqual(len(report.outcomes), 1)
        self.assertEqual(report.outcomes[0].detail, "NO_TRIGGER")
        event_types = [event.event_type for event in ledger.read_events(self.base)]
        self.assertIn("data_gate", event_types)
        self.assertNotIn("exit_intent", event_types)

    def test_monitor_batch_reports_partial_failure(self):
        self._append_position(
            event_id="open:AMD:b",
            position_id="position:AMD:b",
            lane="b",
            structure="call_debit_spread",
            expiration="2027-01-15",
            legs=[
                {
                    "name": "long",
                    "expiration": "2027-01-15",
                    "strike": 100.0,
                    "right": "C",
                    "side": "buy",
                    "quantity": 1,
                    "raw_bid": 5.0,
                    "raw_ask": 5.1,
                    "raw_open_interest": 500,
                    "raw_delta": 0.60,
                    "fill_price": 5.16,
                }
            ],
        )
        with patch.object(
            lifecycle,
            "observe_exit",
            side_effect=[None, lifecycle.LifecycleValidationError("fixture failure")],
        ):
            report = exit_session.monitor_real_exits(self.open())

        self.assertTrue(report.failed)
        self.assertEqual([item.failed for item in report.outcomes], [False, True])
        self.assertIn("fixture failure", report.outcomes[1].detail)
        self.assertTrue(report.outcomes[1].events)

    def test_fill_batch_processes_due_intent(self):
        decision = self.open()
        evidence = exit_session.record_exit_evidence(
            decision, symbol="AMD", include_symbol=False
        )
        intent = lifecycle.observe_exit(
            base_dir=decision,
            position_id="position:AMD:a",
            evaluation_session=EVALUATION,
            chain=exit_session.load_bound_chain(decision, "AMD"),
            data_gate_id=evidence.data_gate.event_id,
            chain_identity=exit_session.binding_identity(decision, "chain:AMD"),
            closes_identity=exit_session.binding_identity(decision, "close:AMD"),
            underlying_close=exit_session.load_bound_close(decision, "AMD"),
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=_clock("2026-07-21T01:00:00+00:00"),
        )
        self.assertIsNotNone(intent)
        gate = self._write_receipts(
            evaluation="2026-07-21", requested="2026-07-22"
        )
        due = exit_session.open_real_exit_session(
            base_dir=self.base,
            decision_session="2026-07-22",
            source_evaluation_session="2026-07-21",
            data_gate_receipt_path=gate,
            now=datetime(2026, 7, 23, 1, tzinfo=timezone.utc),
        )

        report = exit_session.fill_real_exits(
            due, clock=_clock("2026-07-22T01:00:00+00:00")
        )

        self.assertFalse(report.failed)
        self.assertEqual(len(report.outcomes), 1)
        self.assertEqual(report.outcomes[0].events[-1].event_type, "paper_fill")
        position = lifecycle._replay_positions_at_base(self.base)[0]
        self.assertEqual(position.state, "closed")

    def test_cli_returns_two_for_a_partial_monitor_pass(self):
        failed = exit_session.ExitRunReport(
            (
                exit_session.ExitRunOutcome(
                    position_id="position:AMD:a",
                    symbol="AMD",
                    action="monitor",
                    events=(),
                    detail="fixture failure",
                    failed=True,
                ),
            )
        )
        with (
            patch.object(exit_session, "REAL_FORWARD_STORE", self.base),
            patch.object(exit_session, "monitor_real_exits", return_value=failed),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = exit_session.main(
                [
                    "monitor",
                    "--data-gate-receipt",
                    str(self.gate_path),
                    "--decision-session",
                    DECISION,
                    "--source-evaluation-session",
                    EVALUATION,
                ]
            )

        self.assertEqual(code, 2)
        self.assertIn("H7 EXIT ERROR position:AMD:a", output.getvalue())

    def test_exit_module_has_no_order_or_network_surface(self):
        public = {name for name in dir(exit_session) if not name.startswith("_")}
        self.assertFalse(public & {"order", "place_order", "submit_order", "fetch"})


if __name__ == "__main__":
    unittest.main()

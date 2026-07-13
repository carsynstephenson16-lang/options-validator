"""Stage 4 H7 paper lifecycle -- BUILD-ONLY, SYNTHETIC-ONLY.

Every test injects a temporary forward ledger.  The production ledger is
never an accepted argument and remains absent until Stage 8 activation.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

import config
from data.pandas_feed import adverse_buy
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_paper_lifecycle as life

DECISION = "2026-07-10"
FILL = "2026-07-13"
EXPIRATION = "2026-09-18"


def clock(iso: str):
    return lambda: datetime.fromisoformat(iso)


def event(event_id: str, event_type: str, session: str, *, symbol=None,
          lane=None, causes=None, payload=None):
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": life.session_close_utc(session).isoformat(),
        "evaluation_session": session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes or [],
        "payload": payload or {},
    }


def long_action():
    return {
        "lane": "a",
        "kind": "long_call",
        "expiration": EXPIRATION,
        "strike": 100.0,
        "delta": 0.62,
        "cost": 506.30,
        "stop_ref": 80.0,
    }


def chain(*, bid=4.90, ask=5.00, open_interest=500):
    return pd.DataFrame([{
        "expiration": EXPIRATION,
        "strike": 100.0,
        "right": "C",
        "bid": bid,
        "ask": ask,
        "open_interest": open_interest,
        "delta": 0.62,
    }])


def call_spread_action():
    return {
        "lane": "a",
        "kind": "call_debit_spread",
        "expiration": EXPIRATION,
        "long_strike": 100.0,
        "short_strike": 105.0,
        "cost": 208.60,
        "stop_ref": 80.0,
    }


def call_spread_chain():
    return pd.DataFrame([
        {"expiration": EXPIRATION, "strike": 100.0, "right": "C",
         "bid": 3.90, "ask": 4.00, "open_interest": 500, "delta": 0.60},
        {"expiration": EXPIRATION, "strike": 105.0, "right": "C",
         "bid": 2.00, "ask": 2.10, "open_interest": 500, "delta": 0.25},
    ])


def put_spread_action():
    return {
        "lane": "c",
        "kind": "bull_put_spread",
        "expiration": "2026-08-21",
        "short_strike": 100.0,
        "long_strike": 90.0,
        "short_delta": -0.28,
        "width": 10.0,
        "credit": 3.43,
        "max_loss": 659.60,
        "dte_band": config.H7C_DTE_BAND,
        "stop_ref": 80.0,
    }


def put_spread_chain(*, short_bid=5.00, short_ask=5.20,
                     long_bid=1.40, long_ask=1.50):
    return pd.DataFrame([
        {"expiration": "2026-08-21", "strike": 100.0, "right": "P",
         "bid": short_bid, "ask": short_ask, "open_interest": 500,
         "delta": -0.28},
        {"expiration": "2026-08-21", "strike": 90.0, "right": "P",
         "bid": long_bid, "ask": long_ask, "open_interest": 500,
         "delta": -0.12},
    ])


class LifecycleCase(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / "synthetic-forward"

    def append(self, ev, iso="2026-07-11T00:00:00+00:00"):
        return ledger.append_event(ev, base_dir=self.base, clock=clock(iso))

    def decision_upstream(self, action=None):
        action = long_action() if action is None else action
        self.append(event("sh:T", "source_health", DECISION,
                          payload={"healthy_symbols": ["NVDA"]}))
        self.append(event("dg:T", "data_gate", DECISION,
                          payload={"whole_universe_verdict": "GO"}))
        self.append(event("board:T", "board_resolution", DECISION,
                          causes=["sh:T", "dg:T"],
                          payload={"accepted": [{"symbol": "NVDA",
                                                  "lane": action["lane"],
                                                  "action": action}]}))

    def fill_upstream(self, *, gate="GO", health="CLEAR"):
        self.append(event("sh:T1", "source_health", FILL, symbol="NVDA",
                          payload={"gate": health, "healthy": health == "CLEAR"}))
        self.append(event("dg:T1", "data_gate", FILL,
                          payload={"whole_universe_verdict": gate}))

    def intent(self):
        self.decision_upstream()
        return life.record_entry_intent(
            base_dir=self.base,
            symbol="NVDA",
            action=long_action(),
            decision_chain=chain(),
            decision_session=DECISION,
            source_health_id="sh:T",
            data_gate_id="dg:T",
            board_resolution_id="board:T",
            chain_identity="sha256:decision-chain",
            closes_identity="sha256:decision-closes",
            clock=clock("2026-07-11T01:00:00+00:00"),
        )

    def approve(self):
        return life.record_owner_approval(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            clock=clock("2026-07-13T18:00:00+00:00"),
        )

    def open_position(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        return life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
            clock=clock("2026-07-14T01:00:00+00:00"),
        )


class TestStoreGuard(LifecycleCase):
    def test_real_store_and_symlink_are_refused_without_mutation(self):
        real = Path(life.REAL_FORWARD_STORE)
        before = set(real.iterdir())
        with self.assertRaises(life.ActivationBoundaryError):
            life.replay_positions(base_dir=real)
        link = self.base.parent / "forward-link"
        os.symlink(real, link)
        with self.assertRaises(life.ActivationBoundaryError):
            life.replay_positions(base_dir=link)
        with self.assertRaises(life.ActivationBoundaryError):
            life.replay_positions(base_dir=real / "synthetic-looking-child")
        child_link = self.base.parent / "forward-child-link"
        os.symlink(real / "synthetic-looking-child", child_link)
        with self.assertRaises(life.ActivationBoundaryError):
            life.replay_positions(base_dir=child_link)
        self.assertEqual(set(real.iterdir()), before)

    def test_healthy_empty_board_is_not_a_data_gap(self):
        self.append(event("sh:T", "source_health", DECISION,
                          payload={"healthy_symbols": ["NVDA"]}))
        self.append(event("dg:T", "data_gate", DECISION,
                          payload={"whole_universe_verdict": "GO"}))
        self.append(event("board:T", "board_resolution", DECISION,
                          causes=["sh:T", "dg:T"], payload={"accepted": []}))
        self.assertEqual(life.replay_positions(base_dir=self.base), [])
        self.assertNotIn(
            "data_gap", [stored.event_type for stored in ledger.read_events(self.base)]
        )


class TestIntentAndApproval(LifecycleCase):
    def test_intent_has_required_causes_and_frozen_contract(self):
        result = self.intent()
        self.assertTrue(result.appended)
        stored = ledger.read_events(self.base)[-1]
        self.assertEqual(stored.event_type, "entry_intent")
        self.assertEqual(stored.causes, ["dg:T", "board:T", "sh:T"])
        self.assertEqual(stored.payload["legs"][0]["quantity"], 1)
        self.assertEqual(stored.payload["chain_identity"], "sha256:decision-chain")
        decision_leg = stored.payload["decision_legs"][0]
        self.assertEqual(decision_leg["raw_bid"], 4.90)
        self.assertEqual(decision_leg["raw_ask"], 5.00)
        self.assertEqual(decision_leg["fill_price"], adverse_buy(5.00))
        self.assertEqual(
            stored.payload["decision_commission"],
            config.COMMISSION_PER_CONTRACT,
        )
        self.assertEqual(stored.payload["decision_cash_kind"], "debit")

    def test_stage5_board_reservation_is_replaced_by_exact_intent_risk(self):
        from options_researcher.h7_forward_book import (
            derive_book,
            record_board_resolution,
        )

        universe = sorted(set(config.H7_WATCHLIST) | set(config.H7_BACKTEST_SYMBOLS))
        self.append(event(
            "sh:T", "source_health", DECISION,
            payload={"healthy_symbols": universe},
        ))
        self.append(event(
            "dg:T", "data_gate", DECISION, causes=["sh:T"],
            payload={"whole_universe_verdict": "GO"},
        ))
        board = record_board_resolution(
            base_dir=self.base,
            evaluation_session=DECISION,
            candidates=[{
                "symbol": "NVDA", "lane": "a", "session": DECISION,
                "action": long_action(),
            }],
            source_health_id="sh:T",
            data_gate_id="dg:T",
            clock=clock("2026-07-11T00:00:00+00:00"),
        )
        intent = life.record_entry_intent(
            base_dir=self.base,
            symbol="NVDA",
            action=long_action(),
            decision_chain=chain(),
            decision_session=DECISION,
            source_health_id="sh:T",
            data_gate_id="dg:T",
            board_resolution_id=board.event_id,
            chain_identity="sha256:decision-chain",
            closes_identity="sha256:decision-closes",
            clock=clock("2026-07-11T01:00:00+00:00"),
        )
        snapshot = derive_book(base_dir=self.base, evaluation_session=DECISION)
        self.assertEqual(len(snapshot.reservations), 1)
        self.assertEqual(snapshot.reservations[0].reservation_id, intent.event_id)
        self.assertEqual(snapshot.month_reserved_risk, 506.30)

    def test_stage5_board_risk_mismatch_refuses_intent_without_append(self):
        from options_researcher.h7_forward_book import record_board_resolution

        action = {**long_action(), "cost": 400.0}
        universe = sorted(set(config.H7_WATCHLIST) | set(config.H7_BACKTEST_SYMBOLS))
        self.append(event(
            "sh:T", "source_health", DECISION,
            payload={"healthy_symbols": universe},
        ))
        self.append(event(
            "dg:T", "data_gate", DECISION, causes=["sh:T"],
            payload={"whole_universe_verdict": "GO"},
        ))
        board = record_board_resolution(
            base_dir=self.base,
            evaluation_session=DECISION,
            candidates=[{
                "symbol": "NVDA", "lane": "a", "session": DECISION,
                "action": action,
            }],
            source_health_id="sh:T",
            data_gate_id="dg:T",
            clock=clock("2026-07-11T00:00:00+00:00"),
        )
        before = ledger.verify(self.base).count
        with self.assertRaises(life.LifecycleValidationError):
            life.record_entry_intent(
                base_dir=self.base,
                symbol="NVDA",
                action=action,
                decision_chain=chain(),
                decision_session=DECISION,
                source_health_id="sh:T",
                data_gate_id="dg:T",
                board_resolution_id=board.event_id,
                chain_identity="sha256:decision-chain",
                closes_identity="sha256:decision-closes",
                clock=clock("2026-07-11T01:00:00+00:00"),
            )
        self.assertEqual(ledger.verify(self.base).count, before)

    def test_on_time_approval_uses_system_recorded_time(self):
        self.intent()
        result = self.approve()
        self.assertTrue(result.appended)
        approval = ledger.read_events(self.base)[-1]
        self.assertEqual(approval.event_type, "owner_approval")
        self.assertEqual(approval.evaluation_session, DECISION)
        self.assertEqual(approval.recorded_at_utc, "2026-07-13T18:00:00+00:00")
        self.assertEqual(approval.payload["fill_session"], FILL)

    def test_late_approval_becomes_skip_and_never_approval(self):
        self.intent()
        life.record_owner_approval(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            clock=clock("2026-07-13T21:00:00+00:00"),
        )
        events = ledger.read_events(self.base)
        self.assertEqual(events[-1].event_type, "skip")
        self.assertEqual(events[-1].payload["reason"], "approval_late")
        self.assertNotIn("owner_approval", [e.event_type for e in events])

    def test_board_must_accept_exact_symbol_lane_and_action(self):
        self.append(event("sh:T", "source_health", DECISION,
                          payload={"healthy_symbols": ["NVDA"]}))
        self.append(event("dg:T", "data_gate", DECISION,
                          payload={"whole_universe_verdict": "GO"}))
        self.append(event("board:T", "board_resolution", DECISION,
                          causes=["sh:T", "dg:T"], payload={"accepted": []}))
        with self.assertRaises(life.LifecycleValidationError):
            life.record_entry_intent(
                base_dir=self.base, symbol="NVDA", action=long_action(),
                decision_chain=chain(),
                decision_session=DECISION, source_health_id="sh:T",
                data_gate_id="dg:T", board_resolution_id="board:T",
                chain_identity="sha256:decision-chain",
                closes_identity="sha256:decision-closes",
                clock=clock("2026-07-11T01:00:00+00:00"),
            )

    def test_approval_records_one_authoritative_clock_read(self):
        self.intent()
        times = iter([
            datetime.fromisoformat("2026-07-13T19:59:59+00:00"),
            datetime.fromisoformat("2026-07-13T20:00:01+00:00"),
        ])
        result = life.record_owner_approval(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            clock=lambda: next(times),
        )
        stored = {e.event_id: e for e in ledger.read_events(self.base)}[
            result.event_id
        ]
        self.assertEqual(stored.recorded_at_utc, "2026-07-13T19:59:59+00:00")


class TestEntryFill(LifecycleCase):
    def test_t_plus_one_fill_uses_ask_once_and_replays_open_position(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "paper_fill")
        fill = ledger.read_events(self.base)[-1]
        leg = fill.payload["legs"][0]
        self.assertEqual(leg["raw_ask"], 5.0)
        self.assertEqual(leg["fill_price"], adverse_buy(5.0))
        self.assertEqual(fill.payload["commission"], config.COMMISSION_PER_CONTRACT)
        self.assertEqual(fill.payload["underlying_close"], 100.0)
        self.assertEqual(fill.payload["underlying_close_session"], FILL)
        self.assertEqual(
            fill.payload["underlying_close_identity"], "sha256:fill-closes"
        )
        positions = life.replay_positions(base_dir=self.base)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].state, "open")

    def test_successful_entry_requires_exact_session_adjusted_close(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        count = ledger.verify(self.base).count
        with self.assertRaisesRegex(
            life.LifecycleValidationError, "exact-session adjusted close"
        ):
            life.process_entry_fill(
                base_dir=self.base,
                entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
                fill_session=FILL,
                chain=chain(),
                source_health_id="sh:T1",
                data_gate_id="dg:T1",
                chain_identity="sha256:fill-chain",
                closes_identity="sha256:fill-closes",
                clock=clock("2026-07-14T01:00:00+00:00"),
            )
        self.assertEqual(ledger.verify(self.base).count, count)

    def test_stage5_actual_risk_breach_records_terminal_capacity_skip(self):
        self.append(event(
            "old-intent", "entry_intent", "2026-07-08", symbol="PLTR", lane="a",
            payload={
                "position_id": "old-intent",
                "planned_fill_session": "2026-07-09",
                "decision_at_risk": 5480.0,
                "action": long_action(),
                "legs": [{
                    "name": "long", "expiration": EXPIRATION,
                    "strike": 100.0, "right": "C", "side": "buy",
                    "quantity": config.H7_FORWARD_CONTRACTS,
                }],
            },
        ))
        self.append(event(
            "old-fill", "paper_fill", "2026-07-09", symbol="PLTR", lane="a",
            causes=["old-intent"],
            payload={
                "transition": "open",
                "position_id": "old-intent",
                "entry_intent_id": "old-intent",
                "decision_session": "2026-07-08",
                "fill_session": "2026-07-09",
                "structure": "long_call",
                "at_risk": 5480.0,
                "action": long_action(),
                "legs": [{
                    "name": "long", "expiration": EXPIRATION,
                    "strike": 100.0, "right": "C", "side": "buy",
                    "quantity": config.H7_FORWARD_CONTRACTS,
                }],
            },
        ))
        self.intent()
        self.approve()
        self.fill_upstream()
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(bid=5.00, ask=5.20),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "skip")
        self.assertEqual(result.payload["reason"], "book_capacity_at_fill")
        self.assertEqual(result.payload["failed_constraints"], ["monthly_sleeve"])
        self.assertGreater(result.payload["projected_month_risk"], 6000.0)
        capacity = result.payload["capacity_snapshot"]
        self.assertEqual(capacity["month_actual_risk"], 5480.0)
        self.assertEqual(
            [item["position_id"] for item in capacity["open_positions"]],
            ["old-intent"],
        )
        self.assertEqual(
            capacity["replaced_reservation"]["reservation_id"],
            life.entry_intent_id(DECISION, "NVDA", "a"),
        )

    def test_missing_approval_expires_without_reading_quotes(self):
        self.intent()
        self.fill_upstream()
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=None,
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="unused",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "skip")
        self.assertEqual(result.payload["reason"], "approval_missing")

    def test_missing_entry_quote_records_gap_then_expires(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=pd.DataFrame(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:empty",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "skip")
        self.assertEqual(result.payload["reason"], "entry_data_gap")
        events = ledger.read_events(self.base)
        self.assertEqual(events[-2].event_type, "data_gap")
        self.assertEqual(events[-1].causes[-1], events[-2].event_id)

    def test_fill_session_liquidity_failure_expires(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(open_interest=1),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:thin",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "skip")
        self.assertEqual(result.payload["reason"], "liquidity_at_fill")

    def test_rerun_is_a_deterministic_no_op(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        kwargs = dict(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
        )
        first = life.process_entry_fill(
            **kwargs, clock=clock("2026-07-14T01:00:00+00:00"))
        count = ledger.verify(self.base).count
        second = life.process_entry_fill(
            **kwargs, clock=clock("2026-08-01T01:00:00+00:00"))
        self.assertEqual(second.event_id, first.event_id)
        self.assertEqual(ledger.verify(self.base).count, count)

    def test_conflicting_fill_rerun_refuses(self):
        self.open_position()
        with self.assertRaises(life.LifecycleValidationError):
            life.process_entry_fill(
                base_dir=self.base,
                entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
                fill_session=FILL,
                chain=chain(bid=5.20, ask=5.30),
                source_health_id="sh:T1",
                data_gate_id="dg:T1",
                chain_identity="sha256:fill-chain",
                closes_identity="sha256:fill-closes",
                underlying_close=100.0,
                clock=clock("2026-08-01T01:00:00+00:00"),
            )

    def test_call_spread_prices_buy_at_ask_and_sell_at_bid(self):
        self.decision_upstream(call_spread_action())
        intent = life.record_entry_intent(
            base_dir=self.base,
            symbol="NVDA",
            action=call_spread_action(),
            decision_chain=call_spread_chain(),
            decision_session=DECISION,
            source_health_id="sh:T",
            data_gate_id="dg:T",
            board_resolution_id="board:T",
            chain_identity="sha256:decision-chain",
            closes_identity="sha256:decision-closes",
            clock=clock("2026-07-11T01:00:00+00:00"),
        )
        life.record_owner_approval(
            base_dir=self.base,
            entry_intent_id=intent.event_id,
            clock=clock("2026-07-13T18:00:00+00:00"),
        )
        self.fill_upstream()
        filled = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=intent.event_id,
            fill_session=FILL,
            chain=call_spread_chain(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:spread-fill",
            closes_identity="sha256:fill-closes",
            underlying_close=100.0,
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        legs = {leg["name"]: leg for leg in filled.payload["legs"]}
        self.assertEqual(legs["long"]["fill_price"], life.adverse_buy(4.00))
        self.assertEqual(legs["short"]["fill_price"], life.adverse_sell(2.00))
        self.assertEqual(
            filled.payload["commission"], 2 * config.COMMISSION_PER_CONTRACT
        )

    def test_fill_gate_no_go_expires_without_quote_read(self):
        self.intent()
        self.approve()
        self.fill_upstream(gate="NO_GO")
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=None,
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="unused",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.payload["reason"], "data_gate_no_go")

    def test_fill_earnings_unknown_expires(self):
        self.intent()
        self.approve()
        self.fill_upstream(health="UNKNOWN")
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL,
            chain=chain(),
            source_health_id="sh:T1",
            data_gate_id="dg:T1",
            chain_identity="sha256:fill-chain",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.payload["reason"], "earnings_gate_at_fill")

    def test_second_open_same_symbol_lane_is_refused(self):
        self.open_position()
        session = "2026-07-14"
        self.append(event("sh:new", "source_health", session,
                          payload={"healthy_symbols": ["NVDA"]}))
        self.append(event("dg:new", "data_gate", session,
                          payload={"whole_universe_verdict": "GO"}))
        self.append(event("board:new", "board_resolution", session,
                          causes=["sh:new", "dg:new"], payload={}))
        with self.assertRaises(life.LifecycleValidationError):
            life.record_entry_intent(
                base_dir=self.base,
                symbol="NVDA",
                action=long_action(),
                decision_chain=chain(),
                decision_session=session,
                source_health_id="sh:new",
                data_gate_id="dg:new",
                board_resolution_id="board:new",
                chain_identity="sha256:new-chain",
                closes_identity="sha256:new-closes",
                clock=clock("2026-07-15T01:00:00+00:00"),
            )

    def test_second_pending_intent_same_symbol_lane_is_refused(self):
        self.intent()
        session = "2026-07-14"
        action = long_action()
        self.append(event("sh:new", "source_health", session,
                          payload={"healthy_symbols": ["NVDA"]}))
        self.append(event("dg:new", "data_gate", session,
                          payload={"whole_universe_verdict": "GO"}))
        self.append(event("board:new", "board_resolution", session,
                          causes=["sh:new", "dg:new"],
                          payload={"accepted": [{"symbol": "NVDA", "lane": "a",
                                                  "action": action}]}))
        with self.assertRaises(life.LifecycleValidationError):
            life.record_entry_intent(
                base_dir=self.base, symbol="NVDA", action=action,
                decision_chain=chain(),
                decision_session=session, source_health_id="sh:new",
                data_gate_id="dg:new", board_resolution_id="board:new",
                chain_identity="sha256:new-chain",
                closes_identity="sha256:new-closes",
                clock=clock("2026-07-15T01:00:00+00:00"),
            )

    def test_forged_wrong_type_approval_cannot_fill(self):
        intent = self.intent()
        approval_id = f"s4.owner_approval:{intent.event_id}"
        self.append(event(approval_id, "data_gate", DECISION, causes=[intent.event_id],
                          payload={"whole_universe_verdict": "GO"}))
        self.fill_upstream()
        with self.assertRaises(life.LifecycleValidationError):
            life.process_entry_fill(
                base_dir=self.base, entry_intent_id=intent.event_id,
                fill_session=FILL, chain=chain(), source_health_id="sh:T1",
                data_gate_id="dg:T1", chain_identity="sha256:fill-chain",
                closes_identity="sha256:fill-closes",
                clock=clock("2026-07-14T01:00:00+00:00"),
            )

    def test_forged_late_recorded_approval_cannot_fill(self):
        intent = self.intent()
        approval_id = f"s4.owner_approval:{intent.event_id}"
        self.append(
            event(approval_id, "owner_approval", DECISION,
                  causes=[intent.event_id],
                  payload={"entry_intent_id": intent.event_id,
                           "fill_session": FILL,
                           "approval_cutoff_utc": "2026-07-13T20:00:00+00:00"}),
            iso="2026-07-13T21:00:00+00:00",
        )
        self.fill_upstream()
        with self.assertRaises(life.LifecycleValidationError):
            life.process_entry_fill(
                base_dir=self.base, entry_intent_id=intent.event_id,
                fill_session=FILL, chain=chain(), source_health_id="sh:T1",
                data_gate_id="dg:T1", chain_identity="sha256:fill-chain",
                closes_identity="sha256:fill-closes",
                clock=clock("2026-07-14T01:00:00+00:00"),
            )

    def test_entry_fill_before_session_close_is_refused(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        with self.assertRaises(life.LifecycleValidationError):
            life.process_entry_fill(
                base_dir=self.base,
                entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
                fill_session=FILL, chain=chain(), source_health_id="sh:T1",
                data_gate_id="dg:T1", chain_identity="sha256:fill-chain",
                closes_identity="sha256:fill-closes",
                clock=clock("2026-07-13T19:59:00+00:00"),
            )

    def test_malformed_delta_is_entry_data_gap(self):
        self.intent()
        self.approve()
        self.fill_upstream()
        malformed = chain()
        malformed["delta"] = "not-a-delta"
        result = life.process_entry_fill(
            base_dir=self.base,
            entry_intent_id=life.entry_intent_id(DECISION, "NVDA", "a"),
            fill_session=FILL, chain=malformed, source_health_id="sh:T1",
            data_gate_id="dg:T1", chain_identity="sha256:bad-delta",
            closes_identity="sha256:fill-closes",
            clock=clock("2026-07-14T01:00:00+00:00"),
        )
        self.assertEqual(result.payload["reason"], "entry_data_gap")


class TestExitLifecycle(LifecycleCase):
    def exit_gate(self, session: str, event_id: str, *, verdict="GO"):
        self.append(event(event_id, "data_gate", session,
                          payload={"whole_universe_verdict": verdict}))

    def open_h7c(self):
        action = put_spread_action()
        self.decision_upstream(action)
        intent = life.record_entry_intent(
            base_dir=self.base, symbol="NVDA", action=action,
            decision_chain=put_spread_chain(), decision_session=DECISION,
            source_health_id="sh:T", data_gate_id="dg:T",
            board_resolution_id="board:T",
            chain_identity="sha256:c-decision-chain",
            closes_identity="sha256:c-decision-closes",
            clock=clock("2026-07-11T01:00:00+00:00"),
        )
        life.record_owner_approval(
            base_dir=self.base, entry_intent_id=intent.event_id,
            clock=clock("2026-07-13T18:00:00+00:00"),
        )
        self.fill_upstream()
        return life.process_entry_fill(
            base_dir=self.base, entry_intent_id=intent.event_id,
            fill_session=FILL, chain=put_spread_chain(),
            source_health_id="sh:T1", data_gate_id="dg:T1",
            chain_identity="sha256:c-fill-chain",
            closes_identity="sha256:c-fill-closes",
            underlying_close=100.0,
            clock=clock("2026-07-14T01:00:00+00:00"),
        )

    def test_profit_target_creates_mechanical_exit_intent(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        result = life.observe_exit(
            base_dir=self.base,
            position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40),
            data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes",
            underlying_close=90.0,
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.event_type, "exit_intent")
        self.assertEqual(result.payload["primary_reason"], "profit_target")
        self.assertEqual(result.payload["planned_fill_session"], "2026-07-15")
        self.assertEqual(life.replay_positions(base_dir=self.base)[0].state,
                         "pending_exit")
        with self.assertRaises(life.LifecycleValidationError):
            life.observe_exit(
                base_dir=self.base, position_id=opened.payload["position_id"],
                evaluation_session="2026-07-14",
                chain=chain(bid=10.30, ask=10.40), data_gate_id="dg:exit",
                chain_identity="sha256:exit-observation",
                closes_identity="sha256:exit-closes", underlying_close=70.0,
                earnings_gate="CLEAR", next_report=None, source_health_id=None,
                clock=clock("2026-07-15T02:00:00+00:00"),
            )

    def test_exit_quote_gap_retries_first_later_valid_session(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        intent = life.observe_exit(
            base_dir=self.base,
            position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40),
            data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes",
            underlying_close=90.0,
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.exit_gate("2026-07-15", "dg:fill1")
        gap = life.process_exit_fill(
            base_dir=self.base,
            exit_intent_id=intent.event_id,
            fill_session="2026-07-15",
            chain=pd.DataFrame(),
            data_gate_id="dg:fill1",
            chain_identity="sha256:missing",
            closes_identity="sha256:fill1-closes",
            clock=clock("2026-07-16T01:00:00+00:00"),
        )
        self.assertEqual(gap.event_type, "data_gap")
        self.assertEqual(life.replay_positions(base_dir=self.base)[0].state,
                         "pending_exit")

        self.exit_gate("2026-07-16", "dg:fill2")
        closed = life.process_exit_fill(
            base_dir=self.base,
            exit_intent_id=intent.event_id,
            fill_session="2026-07-16",
            chain=chain(bid=9.00, ask=9.20),
            data_gate_id="dg:fill2",
            chain_identity="sha256:valid-retry",
            closes_identity="sha256:fill2-closes",
            underlying_close=90.0,
            clock=clock("2026-07-17T01:00:00+00:00"),
        )
        self.assertEqual(closed.event_type, "paper_fill")
        self.assertEqual(closed.payload["transition"], "close")
        self.assertEqual(closed.payload["legs"][0]["fill_price"],
                         life.adverse_sell(9.00))
        self.assertEqual(closed.payload["underlying_close"], 90.0)
        self.assertEqual(closed.payload["underlying_close_session"], "2026-07-16")
        self.assertEqual(
            closed.payload["underlying_close_identity"], "sha256:fill2-closes"
        )
        self.assertEqual(life.replay_positions(base_dir=self.base)[0].state,
                         "closed")

    def test_exit_gap_cannot_fill_on_same_planned_session(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        intent = life.observe_exit(
            base_dir=self.base, position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40), data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes", underlying_close=90.0,
            earnings_gate="CLEAR", next_report=None, source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.exit_gate("2026-07-15", "dg:fill1")
        life.process_exit_fill(
            base_dir=self.base, exit_intent_id=intent.event_id,
            fill_session="2026-07-15", chain=pd.DataFrame(),
            data_gate_id="dg:fill1", chain_identity="sha256:missing",
            closes_identity="sha256:fill1-closes",
            clock=clock("2026-07-16T01:00:00+00:00"),
        )
        with self.assertRaises(life.LifecycleValidationError):
            life.process_exit_fill(
                base_dir=self.base, exit_intent_id=intent.event_id,
                fill_session="2026-07-15", chain=chain(bid=9.00, ask=9.20),
                data_gate_id="dg:fill1", chain_identity="sha256:late-arrival",
                closes_identity="sha256:fill1-closes",
                clock=clock("2026-07-16T02:00:00+00:00"),
            )

    def test_exit_observation_and_fill_before_close_are_refused(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        with self.assertRaises(life.LifecycleValidationError):
            life.observe_exit(
                base_dir=self.base, position_id=opened.payload["position_id"],
                evaluation_session="2026-07-14",
                chain=chain(bid=10.30, ask=10.40), data_gate_id="dg:exit",
                chain_identity="sha256:exit-observation",
                closes_identity="sha256:exit-closes", underlying_close=90.0,
                earnings_gate="CLEAR", next_report=None, source_health_id=None,
                clock=clock("2026-07-14T19:59:00+00:00"),
            )
        intent = life.observe_exit(
            base_dir=self.base, position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40), data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes", underlying_close=90.0,
            earnings_gate="CLEAR", next_report=None, source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.exit_gate("2026-07-15", "dg:fill1")
        with self.assertRaises(life.LifecycleValidationError):
            life.process_exit_fill(
                base_dir=self.base, exit_intent_id=intent.event_id,
                fill_session="2026-07-15", chain=chain(bid=9.00, ask=9.20),
                data_gate_id="dg:fill1", chain_identity="sha256:fill",
                closes_identity="sha256:fill1-closes",
                clock=clock("2026-07-15T19:59:00+00:00"),
            )

    def test_conflicting_exit_fill_rerun_refuses(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        intent = life.observe_exit(
            base_dir=self.base, position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40), data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes", underlying_close=90.0,
            earnings_gate="CLEAR", next_report=None, source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.exit_gate("2026-07-15", "dg:fill1")
        life.process_exit_fill(
            base_dir=self.base, exit_intent_id=intent.event_id,
            fill_session="2026-07-15", chain=chain(bid=9.00, ask=9.20),
            data_gate_id="dg:fill1", chain_identity="sha256:valid",
            closes_identity="sha256:fill1-closes",
            underlying_close=90.0,
            clock=clock("2026-07-16T01:00:00+00:00"),
        )
        with self.assertRaises(life.LifecycleValidationError):
            life.process_exit_fill(
                base_dir=self.base, exit_intent_id=intent.event_id,
                fill_session="2026-07-15", chain=chain(bid=8.00, ask=8.20),
                data_gate_id="dg:fill1", chain_identity="sha256:valid",
                closes_identity="sha256:fill1-closes",
                underlying_close=90.0,
                clock=clock("2026-08-01T01:00:00+00:00"),
            )

    def test_exit_gate_no_go_remains_pending(self):
        opened = self.open_position()
        self.exit_gate("2026-07-14", "dg:exit")
        intent = life.observe_exit(
            base_dir=self.base,
            position_id=opened.payload["position_id"],
            evaluation_session="2026-07-14",
            chain=chain(bid=10.30, ask=10.40),
            data_gate_id="dg:exit",
            chain_identity="sha256:exit-observation",
            closes_identity="sha256:exit-closes",
            underlying_close=90.0,
            earnings_gate="CLEAR",
            next_report=None,
            source_health_id=None,
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.exit_gate("2026-07-15", "dg:fill1", verdict="NO_GO")
        result = life.process_exit_fill(
            base_dir=self.base,
            exit_intent_id=intent.event_id,
            fill_session="2026-07-15",
            chain=chain(bid=9.00, ask=9.20),
            data_gate_id="dg:fill1",
            chain_identity="sha256:ignored",
            closes_identity="sha256:fill1-closes",
            clock=clock("2026-07-16T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "data_gap")
        self.assertEqual(result.payload["reason"], "exit_data_gate_no_go")

    def test_primary_reason_reuses_frozen_backtest_order(self):
        self.assertEqual(
            life.primary_exit_reason(
                ["profit_target", "scheduled_dte", "pre_earnings"]
            ),
            "pre_earnings",
        )

    def test_h7c_earnings_close_wins_same_session_trigger_collision(self):
        opened = self.open_h7c()
        trigger_session = "2026-08-18"
        self.exit_gate(trigger_session, "dg:c-exit")
        self.append(event("sh:c-exit", "source_health", trigger_session,
                          symbol="NVDA",
                          payload={"gate": "CLEAR", "healthy": True}))
        result = life.observe_exit(
            base_dir=self.base,
            position_id=opened.payload["position_id"],
            evaluation_session=trigger_session,
            chain=put_spread_chain(short_ask=8.00, long_bid=1.00),
            data_gate_id="dg:c-exit",
            chain_identity="sha256:c-exit-chain",
            closes_identity="sha256:c-exit-closes",
            underlying_close=70.0,
            earnings_gate="CLEAR",
            next_report="2026-08-20",
            source_health_id="sh:c-exit",
            clock=clock("2026-08-19T01:00:00+00:00"),
        )
        self.assertEqual(result.payload["primary_reason"], "pre_earnings")
        self.assertIn("scheduled_dte", result.payload["trigger_reasons"])
        self.assertIn("underlying_stop", result.payload["trigger_reasons"])
        stored = ledger.read_events(self.base)[-1]
        self.assertIn("sh:c-exit", stored.causes)

    def test_h7c_unknown_source_health_forces_conservative_exit(self):
        opened = self.open_h7c()
        trigger_session = "2026-07-14"
        self.exit_gate(trigger_session, "dg:c-unknown")
        self.append(event("sh:c-unknown", "source_health", trigger_session,
                          symbol="NVDA",
                          payload={"gate": "UNKNOWN", "healthy": False}))
        result = life.observe_exit(
            base_dir=self.base, position_id=opened.payload["position_id"],
            evaluation_session=trigger_session, chain=put_spread_chain(),
            data_gate_id="dg:c-unknown",
            chain_identity="sha256:c-unknown-chain",
            closes_identity="sha256:c-unknown-closes",
            underlying_close=90.0, earnings_gate="UNKNOWN", next_report=None,
            source_health_id="sh:c-unknown",
            clock=clock("2026-07-15T01:00:00+00:00"),
        )
        self.assertEqual(result.event_type, "exit_intent")
        self.assertEqual(result.payload["primary_reason"], "earnings_unknown")
        self.assertIn("sh:c-unknown", ledger.read_events(self.base)[-1].causes)


if __name__ == "__main__":
    unittest.main()

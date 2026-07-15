"""Stage 5 global risk accounting, synthetic ledger only."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import config
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_forward_book import (
    BookValidationError,
    assess_entry_fill,
    derive_book,
    expire_unmaterialized_reservation,
    reconcile_position_mirror,
    record_board_resolution,
)
from options_researcher.h7_paper_lifecycle import ActivationBoundaryError
from options_researcher.h7_scope import watch_universe


def _clock():
    return lambda: datetime.fromisoformat("2026-07-15T00:00:00+00:00")


def _event(event_id, event_type, session, *, symbol=None, lane=None,
           causes=None, payload=None):
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": f"{session}T20:00:00+00:00",
        "evaluation_session": session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes or [],
        "payload": payload or {},
    }


def _contract(lane):
    if lane == "c":
        action = {
            "lane": lane, "kind": "bull_put_spread",
            "expiration": "2026-08-21", "short_strike": 100.0,
            "long_strike": 95.0,
        }
        legs = [
            {"name": "short", "expiration": "2026-08-21", "strike": 100.0,
             "right": "P", "side": "sell", "quantity": 1},
            {"name": "long", "expiration": "2026-08-21", "strike": 95.0,
             "right": "P", "side": "buy", "quantity": 1},
        ]
    else:
        action = {
            "lane": lane, "kind": "long_call", "expiration": "2026-08-21",
            "strike": 100.0,
        }
        legs = [
            {"name": "long", "expiration": "2026-08-21", "strike": 100.0,
             "right": "C", "side": "buy", "quantity": 1},
        ]
    return action, legs


class BookCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / "synthetic" / "h7_forward"

    def append(self, *args, **kwargs):
        return ledger.append_event(
            _event(*args, **kwargs), base_dir=self.base, clock=_clock())

    def intent(self, event_id, session, symbol="NVDA", lane="a", risk=900.0,
               fill_session="2026-07-11"):
        action, legs = _contract(lane)
        self.append(
            event_id, "entry_intent", session, symbol=symbol, lane=lane,
            payload={
                "position_id": event_id,
                "planned_fill_session": fill_session,
                "decision_at_risk": risk,
                "action": action,
                "legs": legs,
            },
        )

    def open_fill(self, event_id, intent_id, session, *, symbol="NVDA",
                  lane="a", risk=900.0):
        action, legs = _contract(lane)
        decision_session = next(
            event.evaluation_session
            for event in ledger.read_events(self.base)
            if event.event_id == intent_id
        )
        self.append(
            event_id, "paper_fill", session, symbol=symbol, lane=lane,
            causes=[intent_id],
            payload={
                "transition": "open",
                "position_id": intent_id,
                "entry_intent_id": intent_id,
                "decision_session": decision_session,
                "fill_session": session,
                "at_risk": risk,
                "action": action,
                "legs": legs,
            },
        )

    def close_fill(self, event_id, position_id, session, *, symbol="NVDA",
                   lane="a", cause):
        trigger_session = "2026-07-13"
        exit_intent_id = f"exit:{position_id}:{trigger_session}"
        self.append(
            exit_intent_id, "exit_intent", trigger_session,
            symbol=symbol, lane=lane, causes=[cause],
            payload={
                "position_id": position_id,
                "opening_fill_id": cause,
                "trigger_session": trigger_session,
                "planned_fill_session": session,
            },
        )
        self.append(
            event_id, "paper_fill", session, symbol=symbol, lane=lane,
            causes=[exit_intent_id],
            payload={
                "transition": "close",
                "position_id": position_id,
                "opening_fill_id": cause,
                "exit_intent_id": exit_intent_id,
                "fill_session": session,
            },
        )


class TestReplay(BookCase):
    def test_empty_book(self):
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-10")
        self.assertEqual(snap.open_symbols, ())
        self.assertEqual(snap.open_h7c, 0)
        self.assertEqual(snap.month_actual_risk, 0.0)
        self.assertEqual(snap.month_reserved_risk, 0.0)
        self.assertEqual(snap.sleeve_left, config.H7_MONTHLY_AT_RISK)
        self.assertFalse(self.base.exists())

    def test_unresolved_intent_reserves_all_three_caps(self):
        self.intent("i1", "2026-07-10", symbol="PLTR", lane="c", risk=700.0)
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-10")
        self.assertEqual(snap.open_symbols, ("PLTR",))
        self.assertEqual(snap.open_h7c, 1)
        self.assertEqual(snap.month_reserved_risk, 700.0)
        self.assertEqual(snap.sleeve_left, 5300.0)

    def test_skip_releases_reservation(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.append(
            "s1", "skip", "2026-07-11", symbol="NVDA", lane="a",
            causes=["i1"], payload={"entry_intent_id": "i1", "reason": "x"},
        )
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-11")
        self.assertEqual(snap.open_symbols, ())
        self.assertEqual(snap.month_reserved_risk, 0.0)

    def test_semantically_mismatched_skip_cannot_release_reservation(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.append(
            "s1", "skip", "2026-07-11", symbol="SMCI", lane="a",
            causes=["i1"], payload={"entry_intent_id": "i1", "reason": "x"},
        )
        with self.assertRaises(BookValidationError):
            derive_book(base_dir=self.base, evaluation_session="2026-07-11")

    def test_semantically_mismatched_close_cannot_release_position(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        self.close_fill(
            "f2", "i1", "2026-07-14", symbol="SMCI", cause="f1",
        )
        with self.assertRaises(BookValidationError):
            derive_book(base_dir=self.base, evaluation_session="2026-07-14")

    def test_close_without_exact_exit_intent_cannot_release_position(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        self.append(
            "forged-close", "paper_fill", "2026-07-14",
            symbol="NVDA", lane="a", causes=["f1"],
            payload={
                "transition": "close",
                "position_id": "i1",
                "opening_fill_id": "f1",
                "fill_session": "2026-07-14",
            },
        )
        with self.assertRaises(BookValidationError):
            derive_book(base_dir=self.base, evaluation_session="2026-07-14")

    def test_fill_replaces_reservation_with_actual_and_close_does_not_restore(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        self.close_fill("f2", "i1", "2026-07-14", cause="f1")
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-14")
        self.assertEqual(snap.open_symbols, ())
        self.assertEqual(snap.month_actual_risk, 850.0)
        self.assertEqual(snap.sleeve_left, 5150.0)
        self.assertEqual(snap.rows[0].closed, "2026-07-14")

    def test_prior_month_charge_does_not_reduce_current_month(self):
        self.intent("i1", "2026-06-29", risk=900.0, fill_session="2026-06-30")
        self.open_fill("f1", "i1", "2026-06-30", risk=950.0)
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-10")
        self.assertEqual(snap.month_actual_risk, 0.0)
        self.assertEqual(snap.open_symbols, ("NVDA",))

    def test_future_events_are_excluded_from_as_of_projection(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        snap = derive_book(base_dir=self.base, evaluation_session="2026-07-10")
        self.assertEqual(snap.month_reserved_risk, 700.0)
        self.assertEqual(snap.month_actual_risk, 0.0)

    def test_malformed_risk_fails_closed(self):
        self.intent("i1", "2026-07-10", risk=True)
        with self.assertRaises(BookValidationError):
            derive_book(base_dir=self.base, evaluation_session="2026-07-10")


class TestCapacity(BookCase):
    def test_same_underlying_is_blocked_across_lanes(self):
        self.intent("old", "2026-07-09", symbol="NVDA", lane="a", risk=900.0)
        self.intent("new", "2026-07-10", symbol="NVDA", lane="b", risk=800.0)
        result = assess_entry_fill(
            base_dir=self.base, entry_intent_id="new", fill_session="2026-07-11",
            actual_at_risk=800.0,
        )
        self.assertFalse(result.allowed)
        self.assertIn("underlying_open_or_reserved", result.failed_constraints)

    def test_lane_c_basket_is_blocked_by_other_reservation(self):
        self.intent("old", "2026-07-09", symbol="PLTR", lane="c", risk=500.0)
        self.intent("new", "2026-07-10", symbol="SMCI", lane="c", risk=500.0)
        result = assess_entry_fill(
            base_dir=self.base, entry_intent_id="new", fill_session="2026-07-11",
            actual_at_risk=500.0,
        )
        self.assertFalse(result.allowed)
        self.assertIn("h7c_basket_cap", result.failed_constraints)

    def test_actual_fill_risk_cannot_breach_monthly_sleeve(self):
        self.intent(
            "old", "2026-07-09", symbol="PLTR", risk=5500.0,
            fill_session="2026-07-10",
        )
        self.open_fill("old-fill", "old", "2026-07-10", symbol="PLTR", risk=5500.0)
        self.intent("new", "2026-07-10", symbol="NVDA", risk=400.0)
        result = assess_entry_fill(
            base_dir=self.base, entry_intent_id="new", fill_session="2026-07-11",
            actual_at_risk=600.0,
        )
        self.assertFalse(result.allowed)
        self.assertIn("monthly_sleeve", result.failed_constraints)
        self.assertEqual(result.expected_head, ledger.verify(self.base).head)

    def test_own_reservation_is_replaced_not_double_counted(self):
        self.intent("new", "2026-07-10", risk=5900.0)
        result = assess_entry_fill(
            base_dir=self.base, entry_intent_id="new", fill_session="2026-07-11",
            actual_at_risk=5900.0,
        )
        self.assertTrue(result.allowed)
        self.assertEqual(result.projected_month_risk, 5900.0)

    def test_two_stale_capacity_snapshots_cannot_both_append(self):
        self.intent("old", "2026-07-08", symbol="PLTR", risk=5000.0,
                    fill_session="2026-07-09")
        self.open_fill("old-fill", "old", "2026-07-09", symbol="PLTR",
                       risk=5000.0)
        self.intent("i1", "2026-07-09", symbol="NVDA", risk=100.0,
                    fill_session="2026-07-10")
        self.intent("i2", "2026-07-09", symbol="SMCI", risk=100.0,
                    fill_session="2026-07-10")
        one = assess_entry_fill(
            base_dir=self.base, entry_intent_id="i1", fill_session="2026-07-10",
            actual_at_risk=700.0,
        )
        two = assess_entry_fill(
            base_dir=self.base, entry_intent_id="i2", fill_session="2026-07-10",
            actual_at_risk=700.0,
        )
        self.assertTrue(one.allowed)
        self.assertTrue(two.allowed)
        self.assertEqual(one.expected_head, two.expected_head)
        ledger.append_event(
            _event(
                "fill-i1", "paper_fill", "2026-07-10", symbol="NVDA", lane="a",
                causes=["i1"], payload={
                    "transition": "open", "position_id": "i1",
                    "entry_intent_id": "i1", "decision_session": "2026-07-09",
                    "fill_session": "2026-07-10",
                    "at_risk": 700.0,
                    "action": _contract("a")[0], "legs": _contract("a")[1],
                },
            ),
            base_dir=self.base, expected_head=one.expected_head, clock=_clock(),
        )
        with self.assertRaises(ledger.LedgerHeadConflictError):
            ledger.append_event(
                _event(
                    "fill-i2", "paper_fill", "2026-07-10", symbol="SMCI", lane="a",
                    causes=["i2"], payload={
                        "transition": "open", "position_id": "i2",
                        "entry_intent_id": "i2", "decision_session": "2026-07-09",
                        "fill_session": "2026-07-10",
                        "at_risk": 700.0,
                        "action": _contract("a")[0], "legs": _contract("a")[1],
                    },
                ),
                base_dir=self.base, expected_head=two.expected_head, clock=_clock(),
            )
        recomputed = assess_entry_fill(
            base_dir=self.base, entry_intent_id="i2", fill_session="2026-07-10",
            actual_at_risk=700.0,
        )
        self.assertFalse(recomputed.allowed)
        self.assertIn("monthly_sleeve", recomputed.failed_constraints)


class TestBoard(BookCase):
    def upstream(self, session="2026-07-10"):
        # Active/operational universe (H7_EXCLUDED names e.g. staged IREN are
        # not part of it) -- matches record_board_resolution's expectation.
        universe = sorted(set(watch_universe()) | set(config.H7_BACKTEST_SYMBOLS))
        self.append(
            "health", "source_health", session,
            payload={"healthy_symbols": universe},
        )
        self.append(
            "gate", "data_gate", session, causes=["health"],
            payload={"whole_universe_verdict": "GO"},
        )

    def test_board_uses_ledger_derived_capacity_and_is_idempotent(self):
        self.upstream()
        candidates = [
            {"symbol": "NVDA", "lane": "a", "session": "2026-07-10",
             "action": {"lane": "a", "cost": 1000.0}},
            {"symbol": "SMCI", "lane": "a", "session": "2026-07-10",
             "action": {"lane": "a", "cost": 5500.0}},
        ]
        first = record_board_resolution(
            base_dir=self.base, evaluation_session="2026-07-10",
            candidates=candidates, source_health_id="health", data_gate_id="gate",
            clock=_clock(),
        )
        second = record_board_resolution(
            base_dir=self.base, evaluation_session="2026-07-10",
            candidates=list(reversed(candidates)), source_health_id="health",
            data_gate_id="gate", clock=_clock(),
        )
        self.assertTrue(first.appended)
        self.assertFalse(second.appended)
        self.assertEqual([x["symbol"] for x in first.accepted], ["NVDA"])
        self.assertEqual(first.rejected[0]["rejection"], "sleeve_exhausted")

    def test_incomplete_source_health_refuses_before_board_write(self):
        self.append(
            "health", "source_health", "2026-07-10",
            payload={"healthy_symbols": ["NVDA"]},
        )
        self.append(
            "gate", "data_gate", "2026-07-10", causes=["health"],
            payload={"whole_universe_verdict": "GO"},
        )
        before = ledger.verify(self.base).count
        with self.assertRaises(BookValidationError):
            record_board_resolution(
                base_dir=self.base,
                evaluation_session="2026-07-10",
                candidates=[{
                    "symbol": "NVDA", "lane": "a", "session": "2026-07-10",
                    "action": {"lane": "a", "cost": 900.0},
                }],
                source_health_id="health",
                data_gate_id="gate",
                clock=_clock(),
            )
        self.assertEqual(ledger.verify(self.base).count, before)

    def test_malformed_candidate_refuses_before_partial_board_write(self):
        self.upstream()
        before = ledger.verify(self.base).count
        with self.assertRaises(BookValidationError):
            record_board_resolution(
                base_dir=self.base,
                evaluation_session="2026-07-10",
                candidates=[{
                    "symbol": "nvda", "lane": "a", "session": "2026-07-10",
                    "action": {"lane": "a", "cost": True},
                }],
                source_health_id="health",
                data_gate_id="gate",
                clock=_clock(),
            )
        self.assertEqual(ledger.verify(self.base).count, before)

    def test_month_end_board_reserves_against_planned_fill_month(self):
        self.intent(
            "old", "2026-07-29", symbol="PLTR", risk=5900.0,
            fill_session="2026-07-30",
        )
        self.open_fill(
            "old-fill", "old", "2026-07-30", symbol="PLTR", risk=5900.0,
        )
        self.upstream("2026-07-31")
        result = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-31",
            candidates=[{
                "symbol": "NVDA",
                "lane": "a",
                "session": "2026-07-31",
                "action": {"lane": "a", "cost": 1000.0},
            }],
            source_health_id="health",
            data_gate_id="gate",
            clock=_clock(),
        )
        self.assertEqual([item["symbol"] for item in result.accepted], ["NVDA"])
        board = next(
            event for event in ledger.read_events(self.base)
            if event.event_id == result.event_id
        )
        self.assertEqual(board.payload["risk_month"], "2026-08")
        self.assertEqual(board.payload["planned_fill_session"], "2026-08-03")
        self.assertEqual(board.payload["sleeve_left"], 6000.0)

    def test_accepted_board_is_immediately_a_cross_session_reservation(self):
        self.upstream("2026-07-10")
        first = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-10",
            candidates=[{
                "symbol": "NVDA",
                "lane": "a",
                "session": "2026-07-10",
                "action": {"lane": "a", "cost": 5900.0},
            }],
            source_health_id="health",
            data_gate_id="gate",
            clock=_clock(),
        )
        self.assertEqual([item["symbol"] for item in first.accepted], ["NVDA"])
        reserved = derive_book(
            base_dir=self.base, evaluation_session="2026-07-10",
        )
        self.assertEqual(reserved.open_symbols, ("NVDA",))
        self.assertEqual(reserved.month_reserved_risk, 5900.0)
        self.assertEqual(
            reserved.reservations[0].source_event_type, "board_resolution"
        )

        self.append(
            "health-2", "source_health", "2026-07-13",
            payload={
                "healthy_symbols": sorted(
                    set(watch_universe()) | set(config.H7_BACKTEST_SYMBOLS)
                )
            },
        )
        self.append(
            "gate-2", "data_gate", "2026-07-13", causes=["health-2"],
            payload={"whole_universe_verdict": "GO"},
        )
        second = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-13",
            candidates=[
                {
                    "symbol": "NVDA",
                    "lane": "b",
                    "session": "2026-07-13",
                    "action": {"lane": "b", "cost": 50.0},
                },
                {
                    "symbol": "SMCI",
                    "lane": "a",
                    "session": "2026-07-13",
                    "action": {"lane": "a", "cost": 200.0},
                },
            ],
            source_health_id="health-2",
            data_gate_id="gate-2",
            clock=_clock(),
        )
        reasons = {item["symbol"]: item["rejection"] for item in second.rejected}
        self.assertEqual(reasons["NVDA"], "underlying_open")
        self.assertEqual(reasons["SMCI"], "sleeve_exhausted")

    def test_entry_intent_atomically_replaces_its_board_reservation(self):
        self.upstream()
        board = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-10",
            candidates=[{
                "symbol": "NVDA",
                "lane": "a",
                "session": "2026-07-10",
                "action": {"lane": "a", "cost": 900.0},
            }],
            source_health_id="health",
            data_gate_id="gate",
            clock=_clock(),
        )
        self.append(
            "intent", "entry_intent", "2026-07-10",
            symbol="NVDA", lane="a", causes=[board.event_id],
            payload={
                "position_id": "intent",
                "planned_fill_session": "2026-07-13",
                "decision_at_risk": 900.0,
                "action": {"lane": "a", "cost": 900.0},
            },
        )
        snapshot = derive_book(
            base_dir=self.base, evaluation_session="2026-07-10",
        )
        self.assertEqual(len(snapshot.reservations), 1)
        self.assertEqual(snapshot.reservations[0].reservation_id, "intent")
        self.assertEqual(snapshot.reservations[0].source_event_type, "entry_intent")
        self.assertEqual(snapshot.month_reserved_risk, 900.0)

    def test_unmaterialized_board_reservation_expires_only_after_fill_close(self):
        self.upstream()
        board = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-10",
            candidates=[{
                "symbol": "NVDA", "lane": "a", "session": "2026-07-10",
                "action": {"lane": "a", "cost": 900.0},
            }],
            source_health_id="health",
            data_gate_id="gate",
            clock=_clock(),
        )
        before = ledger.verify(self.base).count
        with self.assertRaises(BookValidationError):
            expire_unmaterialized_reservation(
                base_dir=self.base,
                board_resolution_id=board.event_id,
                symbol="NVDA",
                lane="a",
                clock=lambda: datetime.fromisoformat(
                    "2026-07-13T19:59:59+00:00"
                ),
            )
        self.assertEqual(ledger.verify(self.base).count, before)
        first = expire_unmaterialized_reservation(
            base_dir=self.base,
            board_resolution_id=board.event_id,
            symbol="NVDA",
            lane="a",
            clock=lambda: datetime.fromisoformat("2026-07-13T20:00:01+00:00"),
        )
        second = expire_unmaterialized_reservation(
            base_dir=self.base,
            board_resolution_id=board.event_id,
            symbol="NVDA",
            lane="a",
            clock=lambda: datetime.fromisoformat("2026-08-01T20:00:01+00:00"),
        )
        self.assertTrue(first.appended)
        self.assertFalse(second.appended)
        snapshot = derive_book(
            base_dir=self.base, evaluation_session="2026-07-13",
        )
        self.assertEqual(snapshot.reservations, ())
        self.assertEqual(snapshot.open_symbols, ())

    def test_forged_expiry_metadata_is_refused_on_replay_and_rerun(self):
        self.upstream()
        board = record_board_resolution(
            base_dir=self.base,
            evaluation_session="2026-07-10",
            candidates=[{
                "symbol": "NVDA", "lane": "a", "session": "2026-07-10",
                "action": {"lane": "a", "cost": 900.0},
            }],
            source_health_id="health",
            data_gate_id="gate",
            clock=_clock(),
        )
        reservation_id = f"{board.event_id}:NVDA:a"
        expiry_id = f"h7:reservation-expiry:{board.event_id}:NVDA:a"
        self.append(
            expiry_id, "lane_displaced", "2026-07-13",
            symbol="NVDA", lane="a", causes=[board.event_id],
            payload={
                "reservation_id": reservation_id,
                "reason": "intent_materialization_missing",
                "planned_fill_session": "2026-07-14",
                "book_snapshot_hash": "forged",
            },
        )
        with self.assertRaises(BookValidationError):
            derive_book(base_dir=self.base, evaluation_session="2026-07-13")
        with self.assertRaises(BookValidationError):
            expire_unmaterialized_reservation(
                base_dir=self.base,
                board_resolution_id=board.event_id,
                symbol="NVDA",
                lane="a",
                clock=lambda: datetime.fromisoformat("2026-07-13T20:00:01+00:00"),
            )


class TestReconciliation(BookCase):
    def test_exact_mirror_matches_without_writing(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        mirror = self.base.parent / "positions.csv"
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\nNVDA,a,2026-07-11,850,\n"
        )
        before = mirror.read_bytes()
        report = reconcile_position_mirror(
            base_dir=self.base, evaluation_session="2026-07-11", mirror_path=mirror,
        )
        self.assertEqual(report.verdict, "MATCH")
        self.assertEqual(mirror.read_bytes(), before)

    def test_row_and_aggregate_mismatches_are_explicit(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        mirror = self.base.parent / "positions.csv"
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\nNVDA,a,2026-07-11,800,\n"
        )
        report = reconcile_position_mirror(
            base_dir=self.base, evaluation_session="2026-07-11", mirror_path=mirror,
        )
        self.assertEqual(report.verdict, "MISMATCH")
        self.assertTrue(report.missing_from_mirror)
        self.assertTrue(report.extra_in_mirror)
        self.assertIn("month_spent", report.aggregate_mismatches)

    def test_missing_and_extra_rows_are_reported_separately(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        self.open_fill("f1", "i1", "2026-07-11", risk=850.0)
        mirror = self.base.parent / "positions.csv"
        mirror.write_text("symbol,lane,opened,at_risk,closed\n")
        missing = reconcile_position_mirror(
            base_dir=self.base, evaluation_session="2026-07-11", mirror_path=mirror,
        )
        self.assertTrue(missing.missing_from_mirror)
        self.assertFalse(missing.extra_in_mirror)

        other_base = self.base.parent / "other-forward"
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\nSMCI,b,2026-07-11,500,\n"
        )
        extra = reconcile_position_mirror(
            base_dir=other_base, evaluation_session="2026-07-11", mirror_path=mirror,
        )
        self.assertFalse(extra.missing_from_mirror)
        self.assertTrue(extra.extra_in_mirror)

    def test_open_symbol_and_lane_c_aggregate_mismatches_are_named(self):
        self.intent("i1", "2026-07-10", symbol="PLTR", lane="c", risk=700.0)
        self.open_fill(
            "f1", "i1", "2026-07-11", symbol="PLTR", lane="c", risk=850.0,
        )
        mirror = self.base.parent / "positions.csv"
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\n"
            "PLTR,c,2026-07-11,850,2026-07-11\n"
        )
        report = reconcile_position_mirror(
            base_dir=self.base, evaluation_session="2026-07-11", mirror_path=mirror,
        )
        self.assertIn("open_symbols", report.aggregate_mismatches)
        self.assertIn("open_h7c", report.aggregate_mismatches)

    def test_pending_reservation_does_not_create_false_csv_row_mismatch(self):
        self.intent("i1", "2026-07-10", risk=700.0)
        mirror = self.base.parent / "positions.csv"
        mirror.write_text("symbol,lane,opened,at_risk,closed\n")
        report = reconcile_position_mirror(
            base_dir=self.base, evaluation_session="2026-07-10", mirror_path=mirror,
        )
        self.assertEqual(report.verdict, "MATCH")
        self.assertEqual(len(report.pending_reservations), 1)

    def test_malformed_mirror_fails_closed(self):
        mirror = self.base.parent / "positions.csv"
        mirror.parent.mkdir(parents=True)
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\nNVDA,a,2026-07-11,nan,\n"
        )
        with self.assertRaises(BookValidationError):
            reconcile_position_mirror(
                base_dir=self.base, evaluation_session="2026-07-11",
                mirror_path=mirror,
            )

    def test_extra_mirror_column_fails_closed(self):
        mirror = self.base.parent / "positions.csv"
        mirror.parent.mkdir(parents=True)
        mirror.write_text(
            "symbol,lane,opened,at_risk,closed\n"
            "NVDA,a,2026-07-11,850,,unexpected\n"
        )
        with self.assertRaises(BookValidationError):
            reconcile_position_mirror(
                base_dir=self.base, evaluation_session="2026-07-11",
                mirror_path=mirror,
            )

    def test_strict_mirror_row_validation_classes(self):
        mirror = self.base.parent / "positions.csv"
        mirror.parent.mkdir(parents=True, exist_ok=True)
        rows = {
            "duplicate": (
                "NVDA,a,2026-07-10,100,\nNVDA,a,2026-07-10,100,\n"
            ),
            "future": "NVDA,a,2026-07-12,100,\n",
            "zero": "NVDA,a,2026-07-10,0,\n",
            "negative": "NVDA,a,2026-07-10,-1,\n",
            "invalid_lane": "NVDA,z,2026-07-10,100,\n",
            "close_before_open": "NVDA,a,2026-07-10,100,2026-07-09\n",
        }
        for name, row in rows.items():
            with self.subTest(name=name):
                mirror.write_text("symbol,lane,opened,at_risk,closed\n" + row)
                with self.assertRaises(BookValidationError):
                    reconcile_position_mirror(
                        base_dir=self.base,
                        evaluation_session="2026-07-11",
                        mirror_path=mirror,
                    )


class TestActivationBoundary(unittest.TestCase):
    def test_real_store_is_refused_and_untouched(self):
        real = Path(__file__).resolve().parents[1] / "ledger" / "h7_forward"
        before = tuple(sorted(p.name for p in real.iterdir()))
        with self.assertRaises(ActivationBoundaryError):
            derive_book(base_dir=real, evaluation_session="2026-07-10")
        self.assertEqual(tuple(sorted(p.name for p in real.iterdir())), before)


if __name__ == "__main__":
    unittest.main()

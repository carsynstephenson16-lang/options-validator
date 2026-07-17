"""window_registration event type + builder (Stage 8, BUILD-ONLY/INACTIVE)."""
import tempfile
import unittest
from pathlib import Path

import config
from data.cache_runner import session_close_utc
from options_researcher import h7_event_ledger as el
from options_researcher import h7_forward_book as book
from options_researcher import h7_forward_scoring as scoring
from options_researcher import h7_window_registration as wr


class EventTypeTests(unittest.TestCase):
    def test_window_registration_is_a_valid_event_type(self):
        self.assertIn("window_registration", el.EVENT_TYPES)

    def test_existing_types_unchanged(self):
        for t in ("source_health", "data_gate", "board_resolution", "lane_displaced",
                  "entry_intent", "exit_intent", "owner_approval", "paper_fill",
                  "skip", "data_gap"):
            self.assertIn(t, el.EVENT_TYPES)


def _minimal_registration_event():
    return {
        "schema_version": 1,
        "event_id": "wr:test-window-1",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc("2026-07-10").isoformat(),
        "evaluation_session": "2026-07-10",
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": {"placeholder_for_task2": True},
    }


class ReplaySkipTests(unittest.TestCase):
    def test_book_and_scoring_ignore_window_registration(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        result = el.append_event(_minimal_registration_event(), base_dir=base,
                                  expected_head=None)

        # --- book: a ledger containing only a window_registration event
        # replays to a fully empty book (the event carries no position/
        # reservation/board state for derive_book to fold in), with `head`
        # tracking the ledger tip (the one appended event's record_hash).
        snap = book.derive_book(base_dir=base, evaluation_session="2026-07-10")
        self.assertEqual(snap.rows, ())
        self.assertEqual(snap.reservations, ())
        self.assertEqual(snap.open_symbols, ())
        self.assertEqual(snap.open_h7c, 0)
        self.assertEqual(snap.month_actual_risk, 0.0)
        self.assertEqual(snap.month_reserved_risk, 0.0)
        self.assertEqual(snap.sleeve_left, config.H7_MONTHLY_AT_RISK)
        self.assertEqual(snap.head, result.record_hash)

        # --- scoring: no paper_fill events means zero trades in-window,
        # and the frozen loss-gate verdict machinery must not crash on an
        # empty sample -- it reports INCONCLUSIVE/insufficient_losses.
        scored = scoring.score_forward_window(base_dir=base,
                                               window_start="2026-07-10",
                                               window_end="2026-07-11")
        self.assertEqual(scored["n_trades"], 0)
        self.assertEqual(scored["trades"], [])
        self.assertIsNone(scored["overall"]["mean_underlying_return"])
        self.assertEqual(scored["overall"]["verdict"], "INCONCLUSIVE")
        self.assertEqual(scored["overall"]["reason"], "insufficient_losses")
        for lane in config.H7_LANE_PRIORITY:
            self.assertIn(lane, scored["lanes"])
            self.assertIsNone(scored["lanes"][lane]["mean_underlying_return"])
            self.assertEqual(scored["lanes"][lane]["verdict"], "INCONCLUSIVE")


def owner_inputs(**over):
    base = {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed-string 2026-XX-XX",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,  # 70 sessions from 2026-08-03 ends
        # ~2026-11-09, safely past the 3-calendar-month anniversary (2026-11-03);
        # 64 would end 2026-10-30 and fail the window rule — deliberate margin
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS decision sessions from start inclusive",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "renewal receipt <id>",
    }
    base.update(over)
    return base


def evidence(**over):
    base = {
        "review_evidence": "external review PASS <date>",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:2026-08-01",
        "data_gate_evidence_id": "dg:2026-08-01",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    base.update(over)
    return base


class BuilderTests(unittest.TestCase):
    def test_builds_complete_payload(self):
        event = wr.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence())
        self.assertEqual(event["event_type"], "window_registration")
        self.assertEqual(event["causes"], [])
        p = event["payload"]
        self.assertEqual(p["window"]["start_decision_session"], "2026-08-03")
        self.assertIn("config_hash", p["frozen"])
        self.assertIn("MIN_LOSSES_FOR_VERDICT", p["frozen"]["stage456_parameters"])
        self.assertEqual(p["frozen"]["verdict_mapping"],
                         {"SURVIVED": "ci_above_zero", "REJECTED": "ci_below_zero",
                          "INCONCLUSIVE": "insufficient_or_no_edge"})
        self.assertIn("not live-trading approval", p["frozen"]["survived_disclaimer"])
        self.assertEqual(p["cohort_rule"],
                         "decision_session in registered window (immutable key)")

    def test_missing_owner_input_refuses(self):
        bad = owner_inputs()
        del bad["WINDOW_START_DECISION_SESSION"]
        with self.assertRaises(wr.RegistrationInputError):
            wr.build_window_registration_event(owner=bad, evidence=evidence())

    def test_none_owner_input_refuses(self):
        with self.assertRaises(wr.RegistrationInputError):
            wr.build_window_registration_event(
                owner=owner_inputs(THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH=None),
                evidence=evidence())

    def test_three_month_rule_enforced(self):
        with self.assertRaises(wr.WindowRuleError):
            wr.build_window_registration_event(
                owner=owner_inputs(WINDOW_DECISION_SESSION_COUNT=20),
                evidence=evidence())

    def test_coverage_must_reach_window_end(self):
        with self.assertRaises(wr.WindowRuleError):
            wr.build_window_registration_event(
                owner=owner_inputs(
                    THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH="2026-09-01"),
                evidence=evidence())


class AppendTests(unittest.TestCase):
    def test_registers_as_first_event_on_synthetic_store(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        res = wr.register_window(owner=owner_inputs(), evidence=evidence(),
                                 base_dir=base)
        self.assertEqual(res.seq, 1)
        self.assertTrue(res.appended)

    def test_refuses_non_empty_ledger(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        el.append_event(_minimal_registration_event(), base_dir=base,
                        expected_head=None)
        with self.assertRaises(el.LedgerHeadConflictError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=base)

    def test_refuses_real_store(self):
        from options_researcher.h7_paper_lifecycle import (
            REAL_FORWARD_STORE,
            ActivationBoundaryError,
        )
        with self.assertRaises(ActivationBoundaryError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=REAL_FORWARD_STORE)

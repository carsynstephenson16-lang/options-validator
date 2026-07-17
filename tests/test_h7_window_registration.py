"""window_registration event type + builder (Stage 8, BUILD-ONLY/INACTIVE)."""
import tempfile
import unittest
from pathlib import Path

import config
from data.cache_runner import session_close_utc
from options_researcher import h7_event_ledger as el
from options_researcher import h7_forward_book as book
from options_researcher import h7_forward_scoring as scoring


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

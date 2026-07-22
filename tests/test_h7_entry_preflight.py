"""Daily read-only proof that the real entry path is reachable.

The forward window is live but has never appended a decision event, so the
first real trigger would be the first execution of ``open_real_session``
against real receipts. The preflight exercises exactly that validation every
session -- before a name triggers -- and must never write anything.
"""

from __future__ import annotations

import unittest

from test_h7_session_real_path import (
    DECISION,
    EVALUATION,
    INCLUDED,
    RealSessionCase,
    _snapshot,
)

from options_researcher.h7_entry_preflight import preflight


class PreflightCase(RealSessionCase):
    def run_preflight(self, **over):
        kwargs = {
            "base_dir": self.base,
            "decision_session": DECISION,
            "source_evaluation_session": EVALUATION,
            "data_gate_receipt_path": self._paths(EVALUATION)[1],
        }
        kwargs.update(over)
        return preflight(**kwargs)


class TestPreflightGreenPath(PreflightCase):
    def test_valid_chain_reports_every_cohort_symbol_entry_ready(self):
        result = self.run_preflight()
        self.assertTrue(result.ok, result.refusal)
        self.assertIsNone(result.refusal)
        self.assertEqual(result.entry_ready, tuple(INCLUDED))
        self.assertEqual(result.banned, {})
        self.assertEqual(result.decision_session, DECISION)
        self.assertEqual(result.evaluation_session, EVALUATION)

    def test_preflight_writes_nothing_to_the_forward_store(self):
        before = _snapshot(self.base)
        self.run_preflight()
        self.assertEqual(_snapshot(self.base), before)


class TestPreflightRefusals(PreflightCase):
    def test_unlinked_data_gate_receipt_is_reported_not_raised(self):
        self._write_receipts(EVALUATION, linked=False)
        result = self.run_preflight()
        self.assertFalse(result.ok)
        self.assertIn("receipt", result.refusal)
        self.assertEqual(result.entry_ready, ())

    def test_no_go_data_gate_is_reported(self):
        self._write_receipts(EVALUATION, verdict="NO_GO")
        result = self.run_preflight()
        self.assertFalse(result.ok)
        self.assertIn("whole-universe pass", result.refusal)

    def test_missing_receipt_file_is_reported_not_raised(self):
        result = self.run_preflight(
            data_gate_receipt_path=self.root / "does-not-exist.json")
        self.assertFalse(result.ok)
        self.assertIsNotNone(result.refusal)


class TestPreflightPerSymbolBans(PreflightCase):
    def test_entry_banned_symbol_is_listed_without_failing_the_board(self):
        self._write_receipts(EVALUATION, amd_gate="BANNED")
        result = self.run_preflight()
        self.assertTrue(result.ok, result.refusal)
        self.assertIn("AMD", result.banned)
        self.assertNotIn("AMD", result.entry_ready)
        self.assertIn("MSFT", result.entry_ready)


if __name__ == "__main__":
    unittest.main()

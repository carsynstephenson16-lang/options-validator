"""Offline tests for the read-only H7 window status view."""

import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from options_researcher import h7_window_status


class WindowStatusAbsentStore(unittest.TestCase):
    def test_absent_store_reports_not_activated(self):
        with TemporaryDirectory() as tmp:
            status = h7_window_status.window_status(
                base_dir=Path(tmp) / "nowhere",
                today=date(2026, 7, 22),
            )

        self.assertFalse(status["ok"])
        self.assertIn("no forward store", status["detail"])


class WindowStatusRealStore(unittest.TestCase):
    """Runs against the repo's real store without mutating it."""

    def test_real_store_summary(self):
        status = h7_window_status.window_status(today=date(2026, 7, 22))

        self.assertTrue(status["ok"])
        self.assertEqual(status["start"], "2026-07-20")
        self.assertEqual(status["end"], "2026-10-26")
        self.assertEqual(status["total_sessions"], 70)
        self.assertEqual(
            status["included"],
            ["AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST"],
        )
        self.assertGreaterEqual(status["sessions_elapsed"], 2)
        self.assertEqual(
            status["entries_taken"],
            status["event_counts"].get("entry_intent", 0),
        )
        self.assertIn("receipts", status)


if __name__ == "__main__":
    unittest.main()

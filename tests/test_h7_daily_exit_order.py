"""Static contract for the H7 morning exit-management sequence.

The ritual is deliberately not executed in this test: it targets the real
forward-paper ledger.  The source order is the safety contract instead.
"""

from __future__ import annotations

import unittest
from pathlib import Path

RITUAL = Path(__file__).resolve().parents[1] / "tools" / "daily_ritual.sh"


class H7DailyExitOrderTests(unittest.TestCase):
    def test_exit_fill_then_monitor_runs_before_and_gates_h7_entry_path(self):
        source = RITUAL.read_text(encoding="utf-8")

        step = source.index("# Step 2c — H7 real-paper exit management")
        fill = source.index("options_researcher.h7_exit_session fill")
        monitor = source.index("options_researcher.h7_exit_session monitor")
        gate_block = source.index('if [ "$GATE_GO" -eq 1 ]; then')
        entry_guard = source.index('if [ "$H7_EXIT_READY" -eq 1 ]; then')
        preflight = source.index("options_researcher.h7_entry_preflight")

        self.assertLess(step, fill)
        self.assertLess(fill, monitor)
        self.assertLess(monitor, gate_block)
        self.assertLess(gate_block, entry_guard)
        self.assertLess(entry_guard, preflight)
        self.assertIn("EXIT_FILL_RC", source)
        self.assertIn("EXIT_MONITOR_RC", source)
        self.assertIn('crit "h7 exit', source)

    def test_ritual_has_no_entry_or_scoring_mutation_command(self):
        source = RITUAL.read_text(encoding="utf-8")

        for forbidden in (
            "options_researcher.h7_session propose",
            "options_researcher.h7_session approve",
            "options_researcher.h7_session fill",
            "options_researcher.h7_real_scoring finalize",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()

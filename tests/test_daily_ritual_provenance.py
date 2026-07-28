"""Offline contract tests for the ritual's cache/provenance dependency gate."""

import unittest
from pathlib import Path

RITUAL = Path(__file__).resolve().parents[1] / "tools" / "daily_ritual.sh"


class DailyRitualProvenanceTests(unittest.TestCase):
    def test_ops_publisher_requires_current_main(self):
        source = RITUAL.read_text()
        branch_guard = source.index('if [ "$RITUAL_BRANCH" != "main" ]')
        current_main_guard = source.index(
            'rev-parse origin/main 2>/dev/null'
        )
        publisher_role = source.index(
            "export OPTIONS_VALIDATOR_CACHE_ROLE=publisher"
        )
        topup = source.index(
            '"$UV" run python data/recent_topup.py --scope h7 --refresh-closes'
        )
        self.assertLess(branch_guard, current_main_guard)
        self.assertLess(current_main_guard, publisher_role)
        self.assertLess(publisher_role, topup)

    def test_topup_failure_is_causal_critical_and_blocks_entry_watchers(self):
        source = RITUAL.read_text()
        self.assertIn("H7_DATA_READY=0", source)
        self.assertIn("H7_DATA_READY=1", source)
        self.assertIn(
            'crit "topup/provenance preflight: FAILED', source
        )
        self.assertIn(
            'if [ "$H7_DATA_READY" -ne 1 ]; then\n'
            "  GATE_GO=0\n"
            '  note "registered entry watchers: BLOCKED by upstream '
            'cache/provenance preflight"',
            source,
        )

    def test_h6_and_h8_nonzero_results_are_critical(self):
        source = RITUAL.read_text()
        self.assertIn('crit "h6_features: NONZERO EXIT"', source)
        self.assertIn('crit "h6_watch: NONZERO EXIT"', source)
        self.assertIn('crit "h8_watch: NONZERO EXIT"', source)

    def test_h5_rerun_failure_is_critical_before_terminal_publish(self):
        source = RITUAL.read_text()
        failure = 'crit "h5 entry watch: NONZERO EXIT"'
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        self.assertIn(failure, source)
        self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "WARNING: h5 entry watch failed to run"', source)

    def test_h10_rerun_failures_are_critical_before_terminal_publish(self):
        source = RITUAL.read_text()
        terminal = source.index('if [ "$CRITICAL" -eq 1 ]; then')
        failures = (
            'crit "h10_watch: NONZERO EXIT"',
            'crit "h10_observe: NONZERO EXIT"',
            'crit "h10_watch: module unavailable"',
        )
        for failure in failures:
            with self.subTest(failure=failure):
                self.assertIn(failure, source)
                self.assertLess(source.index(failure), terminal)
        self.assertNotIn('note "h10_watch: NONZERO EXIT"', source)
        self.assertNotIn('note "h10_observe: NONZERO EXIT"', source)

    def test_ritual_terminal_status_is_separate_from_capture_receipt(self):
        source = RITUAL.read_text()
        running = source.index("--status RUNNING")
        capture = source.index(
            '"$UV" run python -m options_researcher.ritual_receipt'
        )
        terminal = source.index('--status "$RITUAL_TERMINAL_STATUS"')
        durability = source.index("# Step 8 — DURABILITY")
        self.assertLess(running, capture)
        self.assertLess(capture, terminal)
        self.assertLess(terminal, durability)
        self.assertIn('RITUAL_TERMINAL_STATUS="BROKEN"', source)
        self.assertIn('RITUAL_TERMINAL_STATUS="OK"', source)


if __name__ == "__main__":
    unittest.main()

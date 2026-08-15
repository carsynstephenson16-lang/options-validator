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
        # The GATE_GO block gained the full-tier fence's condition in the
        # 2026-08-14 switch-on restructure (brief 11 §6.2); it is the same
        # block, so this binds the new condition line rather than dropping
        # the assertion.
        gate_block = source.index(
            'if [ "$FULL_AUTHORITY_RC" -eq 0 ] && [ "$GATE_GO" -eq 1 ]; then'
        )
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


class RitualRefreshBeforeConsumerOrderTests(unittest.TestCase):
    """Regression guard for the 2026-07-24 ordering bug: H10 and H5 entry_watch
    each ran before the store they read was refreshed for the day, producing a
    permanently-mislabeled H10 receipt (all names logged SKIPPED reason=DATA)
    and a stale-IV-rank refusal in H5 entry_watch. See the 2026-07-24 07:10
    production log and facts.log H10_RITUAL_ORDER_FIX.
    """

    def test_qm_ohlcv_refresh_precedes_h10_watch_and_observe(self):
        source = RITUAL.read_text(encoding="utf-8")

        # h10_watch/h10_observe read underlying OHLCV via
        # data/underlying_ohlcv.py (options_researcher/h10_watch.py
        # _load_adjusted/_load_raw), which the QM OHLCV refresh step writes.
        refresh = 'options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF"'
        h10_watch = "options_researcher.h10_watch --as-of"
        h10_observe = "options_researcher.h10_observe --as-of"

        self.assertIn(refresh, source)
        self.assertIn(h10_watch, source)
        self.assertIn(h10_observe, source)
        self.assertLess(source.index(refresh), source.index(h10_watch))
        self.assertLess(source.index(refresh), source.index(h10_observe))

    def test_attractiveness_features_rebuild_precedes_entry_watch(self):
        source = RITUAL.read_text(encoding="utf-8")

        # entry_watch reads IV-rank via options_researcher/features.py
        # load_features(), which reads the store this build_all() call writes
        # (options_researcher/entry_watch.py _gather -> features.load_features).
        rebuild = "from options_researcher.features import build_all; build_all("
        entry_watch = "options_researcher.entry_watch"

        self.assertIn(rebuild, source)
        self.assertIn(entry_watch, source)
        self.assertLess(source.index(rebuild), source.index(entry_watch))

    def test_entry_watch_receives_exact_ritual_session(self):
        source = RITUAL.read_text(encoding="utf-8")
        self.assertIn(
            'options_researcher.entry_watch --as-of "$AS_OF" --out "$EW_OUT"',
            source,
        )

    def test_display_extra_provider_acquisition_is_removed(self):
        source = RITUAL.read_text(encoding="utf-8")

        self.assertNotIn("data/recent_topup.py", source)
        self.assertNotIn("display-extra topup", source)

    def test_canonical_and_display_extra_feature_builds_are_isolated(self):
        source = RITUAL.read_text(encoding="utf-8")
        canonical = (
            "build_all('$AS_OF', symbols=watch_universe())"
        )
        display = (
            "build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)"
        )
        gate_block = source.index(
            'if [ "$FULL_AUTHORITY_RC" -eq 0 ] && [ "$GATE_GO" -eq 1 ]; then'
        )

        self.assertIn(canonical, source)
        self.assertIn(display, source)
        self.assertLess(source.index(canonical), source.index(display))
        self.assertLess(source.index(display), gate_block)
        self.assertIn(
            'note "display-extra features: FAILED (non-blocking;',
            source,
        )


if __name__ == "__main__":
    unittest.main()

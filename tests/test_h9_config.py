"""H9 config block — approved values per spec 2026-07-16 (a78b4db)."""
import unittest

import config


class H9ConfigTests(unittest.TestCase):
    def test_owner_approved_values(self):
        self.assertEqual(config.H9_REACTION_MIN, 0.02)
        self.assertEqual(config.H9_NEXT_REPORT_EXIT_SESSIONS, 2)
        self.assertEqual(config.H9_MIN_ELIGIBLE_EVENTS, 60)
        self.assertEqual(config.H9_PREMIUM_CAP_DOLLARS, 600)
        self.assertEqual(config.H9_SECONDARY_COHORT, ("NOW", "MSFT", "VST", "CEG"))

    def test_universe_is_the_eight_archive_names(self):
        self.assertEqual(config.H9_NAMES, config.H7_BACKTEST_SYMBOLS)
        self.assertEqual(len(config.H9_NAMES), 8)

    def test_window_matches_frozen_h7_window(self):
        self.assertEqual(config.H9_WINDOW, (config.H7_BACKTEST_START, config.H7_BACKTEST_END))

    def test_inherited_h6_construction_unchanged(self):
        # H9 inherits these; if H6 values ever change, the H9 spec freeze is violated.
        self.assertEqual(config.H6_DTE_BAND, (45, 90))
        self.assertEqual(config.H6_DELTA_BAND, (0.30, 0.50))
        self.assertEqual(config.H6_TAKE_PROFIT_PCT, 1.00)
        self.assertEqual(config.H6_CLOSE_AT_DTE, 21)

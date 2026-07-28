"""tests/test_attractiveness_universe.py

ATTRACTIVENESS_UNIVERSE is a display-only superset. Its prefix must remain the
canonical H7 forward scope (options_researcher.h7_scope.watch_universe), while
its suffix contains explicitly owner-authorized display extras. The extras
must never leak into H7's registered scope.
"""
import unittest
from unittest.mock import patch

import config
from options_researcher.h7_scope import scope_symbols, watch_universe


class AttractivenessUniverseTests(unittest.TestCase):
    def test_exact_h7_prefix_and_display_extra_suffix(self):
        h7_symbols = watch_universe()

        self.assertEqual(len(h7_symbols), 15)
        self.assertEqual(
            config.ATTRACTIVENESS_EXTRA_NAMES,
            ["NBIS", "AMAT", "CLSK"],
        )
        self.assertEqual(
            config.ATTRACTIVENESS_UNIVERSE,
            h7_symbols + config.ATTRACTIVENESS_EXTRA_NAMES,
        )
        self.assertEqual(config.ATTRACTIVENESS_UNIVERSE[:15], h7_symbols)
        self.assertEqual(
            config.ATTRACTIVENESS_UNIVERSE[15:],
            ["NBIS", "AMAT", "CLSK"],
        )

    def test_display_extras_are_disjoint_from_every_h7_scope_list(self):
        h7_config_symbols = set(
            config.H7_WATCHLIST
            + config.H7_CORE_LONG_ONLY
            + config.H7_EXCLUDED
            + config.H7_BACKTEST_SYMBOLS
        )

        self.assertTrue(
            set(config.ATTRACTIVENESS_EXTRA_NAMES).isdisjoint(h7_config_symbols)
        )

    def test_core_names_present(self):
        for symbol in config.UNIVERSE:
            self.assertIn(symbol, config.ATTRACTIVENESS_UNIVERSE)

    def test_excluded_names_absent(self):
        for symbol in config.H7_EXCLUDED:
            self.assertNotIn(symbol, config.ATTRACTIVENESS_UNIVERSE)

    def test_no_duplicates(self):
        self.assertEqual(len(config.ATTRACTIVENESS_UNIVERSE),
                         len(set(config.ATTRACTIVENESS_UNIVERSE)))

    def test_h7_scope_refuses_any_non_15_name_configuration(self):
        variants = (
            config.H7_WATCHLIST[:-1],
            [*config.H7_WATCHLIST, "SYNTHETIC_EXTRA"],
        )
        for watchlist in variants:
            with self.subTest(count=len(watchlist) + len(config.H7_CORE_LONG_ONLY)):
                with patch.object(config, "H7_WATCHLIST", watchlist):
                    with self.assertRaisesRegex(
                        RuntimeError, "requires 15 unique names"
                    ):
                        scope_symbols()


if __name__ == "__main__":
    unittest.main()

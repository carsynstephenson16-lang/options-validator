"""tests/test_attractiveness_universe.py

ATTRACTIVENESS_UNIVERSE is a DERIVED display universe: it must always equal
the canonical H7 forward scope (options_researcher.h7_scope.watch_universe)
and must never invent a symbol the H7 scope has not authorized. If this test
fails, fix config.ATTRACTIVENESS_UNIVERSE — never h7_scope — unless an
owner-logged H7 amendment changed the scope itself.
"""
import unittest

import config
from options_researcher.h7_scope import watch_universe


class AttractivenessUniverseTests(unittest.TestCase):
    def test_equals_canonical_h7_scope(self):
        self.assertEqual(config.ATTRACTIVENESS_UNIVERSE, watch_universe())

    def test_core_names_present(self):
        for symbol in config.UNIVERSE:
            self.assertIn(symbol, config.ATTRACTIVENESS_UNIVERSE)

    def test_excluded_names_absent(self):
        for symbol in config.H7_EXCLUDED:
            self.assertNotIn(symbol, config.ATTRACTIVENESS_UNIVERSE)

    def test_no_duplicates(self):
        self.assertEqual(len(config.ATTRACTIVENESS_UNIVERSE),
                         len(set(config.ATTRACTIVENESS_UNIVERSE)))


if __name__ == "__main__":
    unittest.main()

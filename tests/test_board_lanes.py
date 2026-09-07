# tests/test_board_lanes.py
"""Unit tests for the lane-board display constants and the pure lane-board
module (spec docs/superpowers/specs/2026-09-06-attractiveness-board-redesign-design.md).
Nothing here asserts a ranking, a signal, or an authority change."""
import unittest
from pathlib import Path

import config

# from options_researcher import board_lanes as bl  # Task 3 creates it; Task 1 tests skip it


class BoardConstantsTests(unittest.TestCase):
    def test_lane_board_constants_exist_and_are_disjoint(self):
        self.assertIsInstance(config.BOARD_LANES_ENABLED, bool)
        fav = config.BOARD_FAVOURABLE_LANES
        cau = config.BOARD_CAUTION_LANES
        self.assertEqual(fav, ("baseline", "context", "composite", "qm", "tbill"))
        self.assertEqual(cau, ("spread", "tail", "beta"))
        self.assertFalse(set(fav) & set(cau))

    def test_constants_carry_display_only_provenance_comment(self):
        source = Path("config.py").read_text(encoding="utf-8")
        preamble = source[: source.index("BOARD_LANES_ENABLED")][-900:]
        self.assertIn("LLM-proposed 2026-09-06", preamble)
        self.assertIn("display-only", preamble.lower())


if __name__ == "__main__":
    unittest.main()

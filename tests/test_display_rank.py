"""Frozen display-ranking extraction tests for Brief 25 WP-A."""

from __future__ import annotations

import unittest

from options_researcher import attractiveness_dashboard as dashboard
from options_researcher import display_rank


class DisplayQualityKeyTests(unittest.TestCase):
    def test_moved_quality_key_matches_pre_move_golden_for_every_lane(self) -> None:
        cases = (
            (
                "put",
                {"grades": {"a": "GREEN", "b": "AMBER"}, "rank_leader": True},
                {"ma_posture": "above_all"},
                (-0.5, -1, -1),
            ),
            (
                "cc",
                {"grades": {"a": "GREEN", "b": "GREEN"}},
                {"ma_posture": "below_all"},
                (-1.0, 0, 0),
            ),
            ("pmcc", {"grades": {"a": "AMBER"}}, {"ma_posture": "mixed"}, (-0.0, 0, -1)),
            (
                "leaps",
                {"grades": {"a": "GREEN", "b": "RED"}},
                {"trend": "up", "breakout_20d": False},
                (-0.5, 0, -1),
            ),
            (
                "long_call",
                {"grades": {"a": "GREEN"}},
                {"trend": "down", "breakout_20d": False},
                (-1.0, 0, 0),
            ),
            ("put", {"grades": {}}, None, (-0.0, 0, 0)),
        )

        for lane, card, technicals, expected in cases:
            with self.subTest(lane=lane, card=card):
                self.assertEqual(
                    display_rank.display_quality_key(card, lane, technicals),
                    expected,
                )
                self.assertEqual(
                    dashboard._display_quality_key(card, lane, technicals),
                    expected,
                )

    def test_lane_sets_are_the_frozen_dashboard_sets(self) -> None:
        self.assertEqual(display_rank.SELL_LANES, ("put", "cc", "pmcc"))
        self.assertEqual(display_rank.BUY_LANES, ("leaps", "long_call"))


if __name__ == "__main__":
    unittest.main()

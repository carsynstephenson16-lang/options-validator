"""Context-aware shortlist scorer tests for Brief 25 WP-B."""

from __future__ import annotations

import unittest

import config
from options_researcher import context_lane


def _pool_item(
    symbol: str,
    *,
    green_fraction: float,
    leader: int = 0,
    tech_conf: int = 0,
    tie: float = 0.0,
    lane: str = "put",
    strike: float = 95.0,
) -> tuple[tuple, dict]:
    candidate_id = f"{symbol}:{lane}:2026-09-18:{strike:.2f}"
    card = {
        "headline": f"{symbol} candidate",
        "top3_snapshot": {"candidate_id": candidate_id},
    }
    key = (-green_fraction, -leader, -tech_conf, tie, symbol, lane, strike)
    return key, {
        "symbol": symbol,
        "lane": lane,
        "strike": strike,
        "expiry": "2026-09-18",
        "dte": 23,
        "score": 0,
        "card": card,
    }


def _composite(
    symbol: str,
    *,
    grade: str = "A",
    trend: str = "UP",
    aligned_count: int = 4,
    internals: str = "CONFIRM",
) -> dict:
    return {
        "symbol": symbol,
        "grade": grade,
        "aligned_count": aligned_count,
        "max_asof": "2026-08-25",
        "trend": {"state": trend, "data_blocked": trend == "DATA_BLOCKED"},
        "vol_premium": {
            "state": "CHEAP" if aligned_count >= 2 else "NEUTRAL",
            "data_blocked": False,
        },
        "regime": {"state": "CALM", "high_dispersion": aligned_count < 3, "data_blocked": False},
        "internals": {
            "state": internals if aligned_count >= 4 else "NEUTRAL",
            "data_blocked": False,
        },
    }


class ContextLaneRankingTests(unittest.TestCase):
    def test_feature_flag_defaults_to_owner_authorized_enabled_state(self) -> None:
        self.assertIs(config.CONTEXT_LANE_ENABLED, True)

    def test_green_fraction_lexicographically_dominates_context_term(self) -> None:
        pool = [
            _pool_item("GREEN", green_fraction=1.0),
            _pool_item("CONTEXT", green_fraction=0.75),
        ]
        board = [
            _composite("GREEN", trend="DATA_BLOCKED", aligned_count=0),
            _composite("CONTEXT", aligned_count=4),
        ]

        rows = context_lane.rank_context_lane(pool, board, board_as_of="2026-08-25", n=2)

        self.assertEqual([row["symbol"] for row in rows], ["GREEN", "CONTEXT"])
        self.assertEqual(rows[0]["context_term"], 0)
        self.assertEqual(rows[1]["context_term"], 4)

    def test_full_frozen_tail_is_deterministic_across_pool_permutations(self) -> None:
        pool = [
            _pool_item("CCC", green_fraction=0.5, tie=-0.20),
            _pool_item("AAA", green_fraction=0.5, tie=-0.30),
            _pool_item("BBB", green_fraction=0.5, tie=-0.30),
        ]
        board = [_composite(symbol, aligned_count=2) for symbol in ("AAA", "BBB", "CCC")]

        forward = context_lane.rank_context_lane(pool, board, board_as_of="2026-08-25", n=3)
        reverse = context_lane.rank_context_lane(
            list(reversed(pool)), list(reversed(board)), board_as_of="2026-08-25", n=3
        )

        self.assertEqual([row["symbol"] for row in forward], ["AAA", "BBB", "CCC"])
        self.assertEqual(
            [row["candidate_id"] for row in reverse],
            [row["candidate_id"] for row in forward],
        )

    def test_context_reasons_are_fail_visible_and_up_only(self) -> None:
        symbols = ("VETO", "DOWN", "MIXED", "BLOCKED", "ABSENT")
        pool = [_pool_item(symbol, green_fraction=0.5) for symbol in symbols]
        board = [
            _composite("VETO", grade="C", internals="VETO"),
            _composite("DOWN", trend="DOWN"),
            _composite("MIXED", trend="MIXED", aligned_count=0),
            _composite("BLOCKED", trend="DATA_BLOCKED", aligned_count=0),
        ]

        rows = context_lane.rank_context_lane(pool, board, board_as_of="2026-08-25", n=len(symbols))
        by_symbol = {row["symbol"]: row for row in rows}

        self.assertEqual(by_symbol["VETO"]["context_reason"], "VETOED")
        self.assertEqual(by_symbol["DOWN"]["context_reason"], "DIRECTION_MISMATCH")
        self.assertEqual(by_symbol["MIXED"]["context_reason"], "DIRECTION_MISMATCH")
        self.assertEqual(by_symbol["BLOCKED"]["context_reason"], "BLOCKED")
        self.assertEqual(by_symbol["ABSENT"]["context_reason"], "BLOCKED")
        self.assertTrue(all(by_symbol[symbol]["context_term"] == 0 for symbol in symbols))

    def test_rows_carry_identity_score_dates_and_aligned_angle_names(self) -> None:
        row = context_lane.rank_context_lane(
            [_pool_item("AAA", green_fraction=0.5)],
            [_composite("AAA", aligned_count=4)],
            board_as_of="2026-08-25",
            n=1,
        )[0]

        self.assertEqual(row["candidate_id"], "AAA:put:2026-09-18:95.00")
        self.assertEqual(row["board_as_of"], "2026-08-25")
        self.assertEqual(row["context_max_asof"], "2026-08-25")
        self.assertEqual(row["context_term"], 4)
        self.assertEqual(
            row["aligned_angles"],
            ("TREND", "VOL_PREMIUM", "REGIME", "INTERNALS"),
        )
        self.assertEqual(len(row["score"]), 8)


if __name__ == "__main__":
    unittest.main()

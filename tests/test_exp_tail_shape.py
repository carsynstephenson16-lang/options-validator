from __future__ import annotations

import math
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

import config
from options_researcher import exp_tail_shape as tail

EXPECTED_KEYS = {
    "experiment_id",
    "state",
    "data_blocked",
    "reason",
    "asof",
    "max_asof",
    "skew",
    "excess_kurtosis",
    "jump_count",
    "jump_rate",
    "window",
    "n_obs",
    "window_agreement",
    "caveat",
}


def _closes_from_returns(
    returns: np.ndarray | list[float], *, start: str = "2020-01-01"
) -> pd.Series:
    values = np.exp(np.r_[0.0, np.cumsum(np.asarray(returns, dtype=float))])
    index = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=index)


def _alternating_returns(n: int, magnitude: float = 0.01) -> np.ndarray:
    return np.resize(np.array([-magnitude, magnitude]), n)


class ExpTailShapeTests(unittest.TestCase):
    def test_key_contract(self) -> None:
        closes = _closes_from_returns(_alternating_returns(400))

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(set(result), EXPECTED_KEYS)
        self.assertEqual(result["experiment_id"], "EXP-TAIL")

    def test_synthetic_negative_skew_recovered(self) -> None:
        rng = np.random.default_rng(20260809)
        returns = -(rng.exponential(scale=0.004, size=5_000) - 0.004)
        closes = _closes_from_returns(returns)

        with mock.patch.object(tail, "EXP_TAIL_WINDOW", 5_000):
            result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertAlmostEqual(result["skew"], -2.0, delta=0.1)

    def test_synthetic_kurtosis_recovered(self) -> None:
        rng = np.random.default_rng(90210)
        returns = rng.laplace(loc=0.0, scale=0.003, size=5_000)
        closes = _closes_from_returns(returns)

        with mock.patch.object(tail, "EXP_TAIL_WINDOW", 5_000):
            result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertAlmostEqual(result["excess_kurtosis"], 3.0, delta=0.3)

    def test_jump_count_engineered_jumps(self) -> None:
        returns = _alternating_returns(300)
        returns[140] = 0.08
        returns[275] = -0.08
        closes = _closes_from_returns(returns)

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(result["jump_count"], 2)

    def test_causal_sigma_red(self) -> None:
        # With 126 prior +/-1% observations, 3.05% exceeds causal 3-sigma.
        # A rolling sigma that incorrectly includes the judged move absorbs it.
        returns = _alternating_returns(250)
        returns[126] = 0.0305
        closes = _closes_from_returns(returns)

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(result["jump_count"], 1)

    def test_causal_sigma_min_periods_boundary(self) -> None:
        returns = _alternating_returns(250)
        returns[125] = 0.0305  # Only 125 prior returns: not evaluable.
        returns[126] = 0.10  # Exactly 126 prior returns: evaluable.
        closes = _closes_from_returns(returns)

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(result["jump_count"], 1)
        self.assertAlmostEqual(result["jump_rate"], 1 / 124)

    def test_min_obs_blocked(self) -> None:
        closes = _closes_from_returns(_alternating_returns(249))

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertTrue(result["data_blocked"])
        self.assertIn("fewer than 250 usable sessions", result["reason"])
        self.assertEqual(set(result), EXPECTED_KEYS)

    def test_window_agreement_flag(self) -> None:
        returns = _alternating_returns(378)
        returns[170] = 0.20
        returns[180] = 0.20
        returns[300] = -0.12
        closes = _closes_from_returns(returns)

        result = tail.exp_tail_shape(closes, asof=str(closes.index[-1].date()))

        self.assertEqual(result["state"], "UNSTABLE")
        self.assertFalse(result["window_agreement"])

    def test_no_lookahead_invariance(self) -> None:
        past_returns = _alternating_returns(300)
        future_returns = np.r_[past_returns, 0.50, -0.40]
        truncated = _closes_from_returns(past_returns)
        full = _closes_from_returns(future_returns)
        asof = str(truncated.index[-1].date())

        expected = tail.exp_tail_shape(truncated, asof=asof)
        actual = tail.exp_tail_shape(full, asof=asof)

        self.assertEqual(actual, expected)

    def test_board_blocked_card(self) -> None:
        with mock.patch.object(
            tail, "load_closes_adjusted", side_effect=FileNotFoundError("missing cache")
        ):
            board = tail.build_exp_tail_board(["VST"], asof="2026-08-04")

        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["symbol"], "VST")
        self.assertEqual(board[0]["state"], "DATA_BLOCKED")
        self.assertTrue(board[0]["data_blocked"])
        self.assertIn("missing cache", board[0]["reason"])
        self.assertEqual(set(board[0]) - {"symbol"}, EXPECTED_KEYS)

    def test_real_cache_board_when_available(self) -> None:
        symbols = config.ATTRACTIVENESS_UNIVERSE[:15]
        cache_dir = Path(".cache/underlying")
        if not all((cache_dir / f"{symbol}.parquet").exists() for symbol in symbols):
            self.skipTest("the complete 15-name underlying-close cache is unavailable")

        board = tail.build_exp_tail_board(symbols, asof="2026-08-04")

        self.assertEqual(len(board), 15)
        self.assertTrue(all(card["state"] != "DATA_BLOCKED" for card in board))
        self.assertTrue(all(math.isfinite(card["skew"]) for card in board))


if __name__ == "__main__":
    unittest.main()

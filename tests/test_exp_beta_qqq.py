"""Tests for the display-only EXP-BETA lane."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import config
from options_researcher.exp_beta_qqq import (
    build_exp_beta_board,
    exp_beta_qqq,
)

CAVEAT = (
    "Betas drift toward 1 in sharp selloffs; a calm-period beta "
    "understates crash co-movement. Descriptive history, not a forecast."
)


def _closes_from_returns(returns: np.ndarray, *, start: str = "2024-01-02") -> pd.Series:
    index = pd.date_range(start, periods=len(returns) + 1, freq="B")
    log_prices = np.concatenate(([np.log(100.0)], np.log(100.0) + np.cumsum(returns)))
    return pd.Series(np.exp(log_prices), index=index)


def _benchmark_returns(n: int) -> np.ndarray:
    x = np.arange(n, dtype=float)
    return 0.001 + 0.008 * np.sin(x / 7.0) + 0.003 * np.cos(x / 13.0)


class ExpBetaQqqTests(unittest.TestCase):
    def test_key_contract(self) -> None:
        closes = _closes_from_returns(_benchmark_returns(150))

        result = exp_beta_qqq(closes, closes, asof="2024-12-31")

        self.assertEqual(
            set(result),
            {
                "experiment_id",
                "state",
                "data_blocked",
                "reason",
                "asof",
                "max_asof",
                "beta",
                "r_squared",
                "beta_half_window",
                "n_obs",
                "caveat",
            },
        )
        self.assertEqual(result["experiment_id"], "EXP-BETA")
        self.assertEqual(result["caveat"], CAVEAT)

    def test_qqq_vs_itself_beta_one(self) -> None:
        closes = _closes_from_returns(_benchmark_returns(300))

        result = exp_beta_qqq(closes, closes, asof="2025-02-24")

        self.assertAlmostEqual(result["beta"], 1.0, delta=0.01)
        self.assertAlmostEqual(result["r_squared"], 1.0, delta=0.01)
        self.assertAlmostEqual(result["beta_half_window"], 1.0, delta=0.01)

    def test_synthetic_double_beta(self) -> None:
        benchmark = _closes_from_returns(_benchmark_returns(300))
        doubled = _closes_from_returns(2.0 * _benchmark_returns(300))

        result = exp_beta_qqq(doubled, benchmark, asof="2025-02-24")

        self.assertAlmostEqual(result["beta"], 2.0, delta=0.05)

    def test_insufficient_overlap_blocked(self) -> None:
        closes = _closes_from_returns(_benchmark_returns(125))

        result = exp_beta_qqq(closes, closes, asof="2025-02-24")

        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertTrue(result["data_blocked"])
        self.assertEqual(result["reason"], "insufficient overlapping history (<126 sessions)")
        self.assertEqual(result["n_obs"], 125)

    def test_degenerate_bench_blocked(self) -> None:
        benchmark = _closes_from_returns(np.full(150, 0.001))
        closes = _closes_from_returns(_benchmark_returns(150))

        result = exp_beta_qqq(closes, benchmark, asof="2025-02-24")

        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertEqual(result["reason"], "degenerate benchmark variance")

    def test_missing_benchmark_blocked(self) -> None:
        closes = _closes_from_returns(_benchmark_returns(150))

        result = exp_beta_qqq(closes, pd.Series(dtype=float), asof="2025-02-24")

        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertIn("benchmark", result["reason"])

    def test_unstable_flag(self) -> None:
        benchmark_returns = _benchmark_returns(252)
        name_returns = np.concatenate(
            (2.0 * benchmark_returns[:126], 0.2 * benchmark_returns[126:])
        )

        result = exp_beta_qqq(
            _closes_from_returns(name_returns),
            _closes_from_returns(benchmark_returns),
            asof="2025-02-24",
        )

        self.assertEqual(result["state"], "UNSTABLE")
        self.assertGreater(abs(result["beta"] - result["beta_half_window"]), 0.5)

    def test_no_lookahead_invariance(self) -> None:
        benchmark = _closes_from_returns(_benchmark_returns(180))
        closes = _closes_from_returns(1.5 * _benchmark_returns(180))
        asof = str(benchmark.index[149].date())
        future_index = pd.date_range(benchmark.index[-1], periods=3, freq="B")[1:]
        future_benchmark = pd.concat([benchmark, pd.Series([500.0, 25.0], index=future_index)])
        future_closes = pd.concat([closes, pd.Series([1.0, 1000.0], index=future_index)])

        def full_loader(symbol: str, *_args: object, **_kwargs: object) -> pd.Series:
            return future_benchmark if symbol == "QQQ" else future_closes

        def truncated_loader(symbol: str, *_args: object, **_kwargs: object) -> pd.Series:
            series = benchmark if symbol == "QQQ" else closes
            return series.loc[:asof]

        with patch(
            "options_researcher.exp_beta_qqq.load_closes_adjusted",
            side_effect=full_loader,
        ):
            full = build_exp_beta_board(["AAA"], asof=asof)[0]
        with patch(
            "options_researcher.exp_beta_qqq.load_closes_adjusted",
            side_effect=truncated_loader,
        ):
            truncated = build_exp_beta_board(["AAA"], asof=asof)[0]

        for key in ("beta", "r_squared", "beta_half_window", "n_obs", "max_asof"):
            self.assertEqual(full[key], truncated[key])

    def test_max_asof_min_of_asymmetric_end_dates(self) -> None:
        benchmark = _closes_from_returns(_benchmark_returns(150))
        closes = _closes_from_returns(_benchmark_returns(151))

        result = exp_beta_qqq(closes, benchmark, asof="2025-02-24")

        self.assertEqual(result["max_asof"], str(benchmark.index[-1].date()))

    def test_board_builder_blocked_card_on_exception(self) -> None:
        benchmark = _closes_from_returns(_benchmark_returns(150))

        def loader(symbol: str, *_args: object, **_kwargs: object) -> pd.Series:
            if symbol == "QQQ":
                return benchmark
            raise ValueError("bad fixture")

        with patch(
            "options_researcher.exp_beta_qqq.load_closes_adjusted",
            side_effect=loader,
        ):
            result = build_exp_beta_board(["AAA"], asof="2025-02-24")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["symbol"], "AAA")
        self.assertEqual(result[0]["state"], "DATA_BLOCKED")
        self.assertIn("ValueError", result[0]["reason"])
        self.assertEqual(result[0]["caveat"], CAVEAT)

    @unittest.skipUnless(
        Path(".cache/underlying/QQQ.parquet").exists(),
        "real underlying cache is absent in this checkout",
    )
    def test_real_cache_coverage(self) -> None:
        cards = build_exp_beta_board(list(config.ATTRACTIVENESS_UNIVERSE), asof="2026-08-03")

        rendered = sum(card["state"] != "DATA_BLOCKED" for card in cards)
        self.assertGreaterEqual(rendered, 12)


if __name__ == "__main__":
    unittest.main()

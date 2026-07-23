"""Tests for the one-run, descriptive RQ1 rank-quality runner."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from options_researcher import rq1_runner


class PureMetricTests(unittest.TestCase):
    def test_green_fraction_uses_all_grade_values(self):
        self.assertAlmostEqual(
            rq1_runner.green_fraction(
                {"yield": "GREEN", "liquidity": "AMBER", "earnings": "UNKNOWN"}
            ),
            1 / 3,
        )
        self.assertIsNone(rq1_runner.green_fraction({}))

    def test_forward_realized_vol_excludes_the_signal_day_return(self):
        closes = pd.Series(
            [100.0, 110.0, 121.0, 133.1, 146.41],
            index=pd.Index(["2026-01-02", "2026-01-05", "2026-01-06",
                            "2026-01-07", "2026-01-08"]),
        )
        out = rq1_runner.forward_realized_vol(closes, horizon=2)
        expected = np.log(pd.Series([121.0 / 110.0, 133.1 / 121.0])).std(ddof=1)
        self.assertAlmostEqual(out.loc["2026-01-02"], expected * np.sqrt(252), places=10)

    def test_spearman_is_rank_based(self):
        self.assertAlmostEqual(
            rq1_runner.spearman_rho([0.1, 0.5, 0.9], [3.0, 2.0, 1.0]),
            -1.0,
        )
        self.assertIsNone(rq1_runner.spearman_rho([1.0], [2.0]))


class CausalBoardTests(unittest.TestCase):
    def test_future_feature_row_is_excluded(self):
        rows = [
            {"symbol": "AAA", "date": "2026-01-02", "green_fraction": 0.5,
             "features_as_of": "2026-01-02", "synthetic": False},
            {"symbol": "AAA", "date": "2026-01-03", "green_fraction": 0.7,
             "features_as_of": "2026-01-04", "synthetic": False},
        ]
        kept, excluded = rq1_runner.filter_causal_board_rows(rows)
        self.assertEqual([r["date"] for r in kept], ["2026-01-02"])
        self.assertEqual(excluded["future_feature_row"], 1)

    def test_synthetic_rows_are_excluded(self):
        rows = [{"symbol": "AAA", "date": "2026-01-02", "green_fraction": 0.5,
                 "features_as_of": "2026-01-02", "synthetic": True}]
        kept, excluded = rq1_runner.filter_causal_board_rows(rows)
        self.assertEqual(kept, [])
        self.assertEqual(excluded["synthetic"], 1)


class OneRunTests(unittest.TestCase):
    def test_existing_report_refuses_before_loader_is_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rq1.json"
            path.write_text("{}", encoding="utf-8")

            def should_not_run():
                raise AssertionError("loader was touched after one-run gate")

            with self.assertRaises(rq1_runner.OneRunError):
                rq1_runner.run_once(
                    load_rows=should_not_run,
                    report_path=path,
                    append_result=False,
                )

    def test_report_is_deterministic_for_same_rows(self):
        rows = [
            {"symbol": "AAA", "date": "2026-01-02", "green_fraction": 0.2,
             "forward_rv": 0.3, "forward_iv_change": 0.1,
             "features_as_of": "2026-01-02", "synthetic": False},
            {"symbol": "BBB", "date": "2026-01-02", "green_fraction": 0.8,
             "forward_rv": 0.1, "forward_iv_change": -0.1,
             "features_as_of": "2026-01-02", "synthetic": False},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            first = rq1_runner.run_once(
                load_rows=lambda: rows,
                report_path=Path(tmp) / "first.json",
                append_result=False,
            )
            second = rq1_runner.summarize(rows)
            self.assertEqual(first["results"]["pooled"], second["pooled"])
            self.assertEqual(first["results"]["observation_count"], 2)


if __name__ == "__main__":
    unittest.main()

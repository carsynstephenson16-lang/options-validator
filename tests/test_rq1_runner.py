"""Tests for the one-run, descriptive RQ1 rank-quality runner."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

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

    def test_forward_iv_uses_exact_trading_session_horizon(self):
        features = pd.DataFrame(
            {"atm_iv": [0.20, 0.30, 0.40]},
            index=pd.Index(["2026-01-02", "2026-01-05", "2026-01-07"]),
        )
        sessions = ["2026-01-02", "2026-01-05", "2026-01-06", "2026-01-07"]

        result = rq1_runner.exact_forward_iv(features, sessions, horizon=2)

        self.assertTrue(pd.isna(result.iloc[0]))
        self.assertAlmostEqual(result.iloc[1], 0.10)
        self.assertTrue(pd.isna(result.iloc[2]))
        self.assertTrue(pd.isna(result.iloc[3]))


class CausalBoardTests(unittest.TestCase):
    def test_earnings_are_selected_from_the_board_day_information_set(self):
        assertions = [
            {
                "record_id": "known",
                "symbol": "AAA",
                "event_id": "AAA-Q1",
                "record_type": "assertion",
                "supersedes": "",
                "event_class": "actual_quarterly_earnings",
                "status": "confirmed",
                "expected_date": date(2026, 2, 1),
                "occurred_date": None,
                "known_as_of_utc": datetime(2026, 1, 2, 15, tzinfo=timezone.utc),
            },
            {
                "record_id": "future-known-later",
                "symbol": "AAA",
                "event_id": "AAA-Q2",
                "record_type": "assertion",
                "supersedes": "",
                "event_class": "actual_quarterly_earnings",
                "status": "confirmed",
                "expected_date": date(2026, 5, 1),
                "occurred_date": None,
                "known_as_of_utc": datetime(2026, 2, 1, tzinfo=timezone.utc),
            },
        ]

        result = rq1_runner._point_in_time_earnings(
            assertions, "AAA", date(2026, 1, 2)
        )

        self.assertEqual(result, [date(2026, 2, 1)])

    def test_unproven_fomc_calendar_is_fail_closed(self):
        with self.assertRaises(rq1_runner.RQ1Error):
            rq1_runner._point_in_time_fomc([date(2026, 2, 1)], date(2026, 1, 2))

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

    def test_failed_ledger_append_can_retry_existing_report(self):
        rows = [
            {
                "symbol": "AAA",
                "date": "2026-01-02",
                "green_fraction": 0.5,
                "forward_rv": 0.3,
                "forward_iv_change": 0.1,
                "features_as_of": "2026-01-02",
                "synthetic": False,
            }
        ]
        calls = 0

        def loader():
            nonlocal calls
            calls += 1
            return rows

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rq1.json"
            with patch(
                "options_researcher.rq1_runner._append_ledger_result",
                side_effect=[RuntimeError("ledger temporarily unavailable"), "hash"],
            ):
                with self.assertRaisesRegex(RuntimeError, "temporarily unavailable"):
                    rq1_runner.run_once(
                        load_rows=loader,
                        report_path=path,
                        append_result=True,
                    )
                retry = rq1_runner.run_once(
                    load_rows=loader,
                    report_path=path,
                    append_result=True,
                )

        self.assertEqual(calls, 1)
        self.assertEqual(retry["hypothesis_id"], "RQ1")


if __name__ == "__main__":
    unittest.main()

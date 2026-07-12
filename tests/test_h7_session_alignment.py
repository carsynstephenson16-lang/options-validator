"""7b-0 session discipline: the watcher evaluates exactly ONE completed NY
session; closes and chain must both end at it. NO-GO remediation for
'watcher consumed an intraday quote as a close' and the 6-day stale-chain
fallback that paired old chains with wall-clock DTE math."""

import unittest
from datetime import date

import pandas as pd

from data.underlying_closes import drop_same_day_rows
from options_researcher.h7_watch import check_alignment, evaluation_session


class TestEvaluationSession(unittest.TestCase):
    def test_friday_run_evaluates_thursday(self):
        self.assertEqual(evaluation_session(date(2026, 7, 10)),
                         date(2026, 7, 9))

    def test_monday_after_holiday_weekend(self):
        # 2026-07-04 falls on a Saturday; XNYS observed the holiday Friday
        # 2026-07-03, so Monday 07-06 evaluates Thursday 07-02.
        self.assertEqual(evaluation_session(date(2026, 7, 6)),
                         date(2026, 7, 2))

    def test_never_returns_the_run_date_itself(self):
        # even ON a trading day, that session is not complete/final in cache
        for d in (date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 12)):
            self.assertLess(evaluation_session(d), d)


def _closes(end_iso, n=5):
    idx = pd.bdate_range(end=end_iso, periods=n)
    return pd.Series([100.0] * n, index=idx, name="close")


class TestCheckAlignment(unittest.TestCase):
    def test_aligned_inputs_pass(self):
        self.assertIsNone(check_alignment(
            _closes("2026-07-09"), "2026-07-09", "2026-07-09"))

    def test_stale_closes_are_a_gap(self):
        reason = check_alignment(_closes("2026-07-06"), "2026-07-09", "2026-07-09")
        self.assertIsNotNone(reason)
        self.assertIn("2026-07-06", reason)

    def test_closes_past_the_session_are_refused(self):
        # a row AFTER the completed session can only be contamination
        reason = check_alignment(_closes("2026-07-10"), "2026-07-09", "2026-07-09")
        self.assertIsNotNone(reason)
        self.assertIn("refuse", reason)

    def test_stale_or_missing_chain_is_a_gap(self):
        self.assertIsNotNone(check_alignment(
            _closes("2026-07-09"), "2026-07-08", "2026-07-09"))
        self.assertIsNotNone(check_alignment(
            _closes("2026-07-09"), None, "2026-07-09"))


class TestDropSameDayRows(unittest.TestCase):
    def test_todays_partial_row_is_dropped(self):
        rows = [("2026-07-08", 101.0), ("2026-07-09", 102.0),
                ("2026-07-10", 55.5)]  # fetched intraday on 07-10
        self.assertEqual(drop_same_day_rows(rows, "2026-07-10"),
                         [("2026-07-08", 101.0), ("2026-07-09", 102.0)])

    def test_past_rows_untouched(self):
        rows = [("2026-07-08", 101.0)]
        self.assertEqual(drop_same_day_rows(rows, "2026-07-10"), rows)

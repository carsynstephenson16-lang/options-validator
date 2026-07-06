"""tests/test_study_earnings.py"""
import unittest
from datetime import date

import pandas as pd

from options_researcher.studies.earnings_behavior import compute_earnings_behavior


def fixture():
    idx = pd.bdate_range("2024-01-02", periods=40).strftime("%Y-%m-%d")
    f = pd.DataFrame(index=idx)
    f["close"] = 100.0
    f["atm_iv"] = 0.30
    # earnings on day 20: IV ramps into it, crushes after; price gaps 5%
    f.iloc[10:20, f.columns.get_loc("atm_iv")] = [0.32 + i * 0.01 for i in range(10)]
    f.iloc[20, f.columns.get_loc("atm_iv")] = 0.25          # post-crush
    f.iloc[20:, f.columns.get_loc("close")] = 105.0
    e = [date.fromisoformat(idx[19])]                        # amc on day 19
    return f, e


class StudyBTests(unittest.TestCase):
    def test_measures_runup_crush_and_move(self):
        f, e = fixture()
        out = compute_earnings_behavior(f, e)
        self.assertEqual(len(out), 1)
        row = out.iloc[0]
        self.assertGreater(row["iv_runup"], 0.05)            # ramped ~.09
        self.assertLess(row["iv_crush"], -0.10)              # .41 -> .25
        self.assertAlmostEqual(row["abs_move_pct"], 5.0, places=1)

    def test_skips_events_without_data_margin(self):
        f, _ = fixture()
        out = compute_earnings_behavior(f, [date(2030, 1, 15)])
        self.assertEqual(len(out), 0)                        # off the frame

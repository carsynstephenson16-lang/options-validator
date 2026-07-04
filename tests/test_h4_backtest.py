"""tests/test_h4_backtest.py"""
import unittest

import pandas as pd

from options_researcher.h4_backtest import _quarter, quarterly


class QuarterlyTests(unittest.TestCase):
    def test_quarter_labels(self):
        self.assertEqual(_quarter("2024-01-15"), "2024Q1")
        self.assertEqual(_quarter("2024-12-31"), "2024Q4")

    def test_quarterly_aggregates_legs_and_totals(self):
        legs = {
            "a": pd.DataFrame({"expiry": ["2024-02-16", "2024-05-17"],
                               "pnl": [100.0, -40.0]}),
            "b": pd.DataFrame({"exit": ["2024-02-20"], "pnl": [10.0]}),
            "empty": pd.DataFrame(),
        }
        q = quarterly(legs)
        self.assertAlmostEqual(q.loc["2024Q1", "total"], 110.0)
        self.assertAlmostEqual(q.loc["2024Q2", "total"], -40.0)
        self.assertAlmostEqual(q.loc["2024Q2", "b"], 0.0)   # filled

if __name__ == "__main__":
    unittest.main()

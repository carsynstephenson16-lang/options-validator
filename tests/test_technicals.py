"""tests/test_technicals.py -- offline synthetic-series tests for technicals.

Fully offline: synthetic pd.Series only; no file or network access.
"""
import math
import unittest

import numpy as np
import pandas as pd

import config
from options_researcher.technicals import technical_snapshot, technical_summary_line

EXPECTED_KEYS = {
    "sma20", "sma50", "sma200",
    "px_vs_sma20", "px_vs_sma50", "px_vs_sma200",
    "ma_posture", "breakout_20d", "hh_20d",
    "high_52w", "dist_52w_high",
    "mom_1m", "mom_3m", "trend",
}


def series(values) -> pd.Series:
    idx = pd.bdate_range("2024-01-02", periods=len(values))
    return pd.Series(np.asarray(values, dtype=float), index=idx)


class TestTechnicalSnapshot(unittest.TestCase):
    def test_key_contract(self):
        snap = technical_snapshot(series(np.full(300, 100.0)))
        self.assertEqual(set(snap.keys()), EXPECTED_KEYS)

    def test_flat_series_is_sideways(self):
        snap = technical_snapshot(series(np.full(300, 100.0)))
        self.assertEqual(snap["trend"], "sideways")
        # px equals every SMA exactly: neither strictly above nor below all.
        self.assertEqual(snap["ma_posture"], "mixed")
        for w in config.TECH_SMA_WINDOWS:
            self.assertAlmostEqual(snap[f"sma{w}"], 100.0)
            self.assertAlmostEqual(snap[f"px_vs_sma{w}"], 0.0)
        self.assertAlmostEqual(snap["hh_20d"], 100.0)
        # Spec defines breakout as close >= PRIOR 20d high; a dead-flat series
        # ties its prior high exactly, so the >= contract makes this True.
        self.assertTrue(snap["breakout_20d"])
        self.assertAlmostEqual(snap["mom_1m"], 0.0)
        self.assertAlmostEqual(snap["mom_3m"], 0.0)
        self.assertAlmostEqual(snap["dist_52w_high"], 0.0)
        self.assertAlmostEqual(snap["high_52w"], 100.0)

    def test_no_breakout_when_below_prior_high(self):
        # Flat at 100 except one earlier spike to 110 inside the prior-20
        # window: last close 100 < prior high 110 -> NOT a breakout.
        vals = np.full(300, 100.0)
        vals[-6] = 110.0
        snap = technical_snapshot(series(vals))
        self.assertAlmostEqual(snap["hh_20d"], 110.0)
        self.assertFalse(snap["breakout_20d"])
        self.assertLess(snap["dist_52w_high"], 0.0)

    def test_monotone_uptrend(self):
        snap = technical_snapshot(series(np.linspace(100.0, 400.0, 300)))
        self.assertEqual(snap["ma_posture"], "above_all")
        self.assertEqual(snap["trend"], "up")
        self.assertTrue(snap["breakout_20d"])
        self.assertGreater(snap["sma20"], snap["sma50"])
        self.assertGreater(snap["sma50"], snap["sma200"])
        for w in config.TECH_SMA_WINDOWS:
            self.assertGreater(snap[f"px_vs_sma{w}"], 0.0)
        self.assertGreater(snap["mom_1m"], 0.0)
        self.assertGreater(snap["mom_3m"], snap["mom_1m"])
        # Last close IS the 52w high in a monotone uptrend.
        self.assertAlmostEqual(snap["dist_52w_high"], 0.0)
        self.assertAlmostEqual(snap["high_52w"], 400.0)

    def test_monotone_downtrend_below_all(self):
        snap = technical_snapshot(series(np.linspace(400.0, 100.0, 300)))
        self.assertEqual(snap["ma_posture"], "below_all")
        self.assertEqual(snap["trend"], "down")
        self.assertFalse(snap["breakout_20d"])
        for w in config.TECH_SMA_WINDOWS:
            self.assertLess(snap[f"px_vs_sma{w}"], 0.0)
        self.assertLess(snap["mom_1m"], 0.0)
        self.assertLess(snap["mom_3m"], 0.0)
        self.assertLess(snap["dist_52w_high"], 0.0)

    def test_short_series_insufficient_history(self):
        snap = technical_snapshot(series(np.full(10, 100.0)))  # must not raise
        for w in config.TECH_SMA_WINDOWS:
            self.assertTrue(math.isnan(snap[f"sma{w}"]))
            self.assertTrue(math.isnan(snap[f"px_vs_sma{w}"]))
        self.assertEqual(snap["ma_posture"], "insufficient_history")
        self.assertEqual(snap["trend"], "insufficient_history")
        self.assertTrue(math.isnan(snap["hh_20d"]))
        self.assertFalse(snap["breakout_20d"])
        self.assertTrue(math.isnan(snap["mom_1m"]))
        self.assertTrue(math.isnan(snap["mom_3m"]))
        # 52w high still computes over the history that exists.
        self.assertAlmostEqual(snap["high_52w"], 100.0)
        self.assertAlmostEqual(snap["dist_52w_high"], 0.0)

    def test_mid_length_series_sma200_nan_gates_trend(self):
        snap = technical_snapshot(series(np.linspace(100.0, 120.0, 60)))
        self.assertFalse(math.isnan(snap["sma20"]))
        self.assertTrue(math.isnan(snap["sma200"]))
        self.assertEqual(snap["ma_posture"], "insufficient_history")
        self.assertEqual(snap["trend"], "insufficient_history")

    def test_empty_series_does_not_raise(self):
        snap = technical_snapshot(pd.Series(dtype=float))
        self.assertEqual(set(snap.keys()), EXPECTED_KEYS)
        self.assertEqual(snap["ma_posture"], "insufficient_history")
        self.assertEqual(snap["trend"], "insufficient_history")
        self.assertFalse(snap["breakout_20d"])
        self.assertTrue(math.isnan(snap["high_52w"]))

    def test_breakout_no_look_ahead(self):
        # Flat at 100, then a final-bar spike to 105: the spike must be judged
        # against the PRIOR high (100), which EXCLUDES the spike itself.
        vals = np.full(250, 100.0)
        vals[-1] = 105.0
        snap = technical_snapshot(series(vals))
        self.assertAlmostEqual(snap["hh_20d"], 100.0)  # spike not in own hurdle
        self.assertTrue(snap["breakout_20d"])
        # Converse: a 105 print two bars back IS part of the prior window, so
        # a last close of 100 sits below the prior high -> no breakout.
        vals2 = np.full(250, 100.0)
        vals2[-3] = 105.0
        snap2 = technical_snapshot(series(vals2))
        self.assertAlmostEqual(snap2["hh_20d"], 105.0)
        self.assertFalse(snap2["breakout_20d"])


class TestSummaryLine(unittest.TestCase):
    def test_uptrend_line(self):
        snap = technical_snapshot(series(np.linspace(100.0, 400.0, 300)))
        line = technical_summary_line(snap)
        self.assertIn("above all MAs", line)
        self.assertIn("20d breakout", line)
        self.assertIn("1M", line)
        self.assertIn("at 52w high", line)

    def test_downtrend_line(self):
        snap = technical_snapshot(series(np.linspace(400.0, 100.0, 300)))
        line = technical_summary_line(snap)
        self.assertIn("below all MAs", line)
        self.assertNotIn("breakout", line)
        self.assertIn("off 52w high", line)

    def test_insufficient_history_line(self):
        snap = technical_snapshot(series(np.full(5, 100.0)))
        line = technical_summary_line(snap)
        # No MA posture, no breakout, no momentum -- only the 52w piece over
        # available history survives; a flat stub sits AT its trailing high.
        self.assertIn("at 52w high", line)
        empty = technical_summary_line(technical_snapshot(pd.Series(dtype=float)))
        self.assertEqual(empty, "insufficient history")


if __name__ == "__main__":
    unittest.main()

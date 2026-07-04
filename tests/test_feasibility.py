"""tests/test_feasibility.py -- measured cached-chain feasibility."""

import unittest
from unittest import mock

import pandas as pd

from analysis import feasibility
from data.thetadata_adapter import OOSDataTouchError

LIQ = 500


def synth_chain(rows):
    return pd.DataFrame(
        [
            {
                "expiration": e,
                "strike": float(k),
                "right": r,
                "bid": float(b),
                "ask": float(a),
                "open_interest": int(oi),
                "iv": 0.25,
                "delta": float(d),
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.1,
            }
            for (e, k, r, b, a, oi, d) in rows
        ]
    )


class MeasuredFeasibilityTests(unittest.TestCase):
    def test_counts_accepted_exact_strike_miss_and_liquidity_failures(self):
        exp = "2022-07-08"
        chains = {
            "2022-06-01": synth_chain([
                (exp, 100.0, "P", 1.20, 1.30, LIQ, -0.30),
                (exp, 98.0, "P", 0.60, 0.64, LIQ, -0.25),
            ]),
            "2022-06-02": synth_chain([
                (exp, 100.0, "P", 1.20, 1.30, LIQ, -0.30),
                (exp, 98.0, "P", 0.50, 0.80, LIQ, -0.25),
            ]),
            "2022-06-03": synth_chain([
                (exp, 100.0, "P", 1.20, 1.30, LIQ, -0.30),
            ]),
        }

        def fake_loader(symbol, start_iso, end_iso, *, allow_oos=False):
            self.assertEqual(symbol, "SYN")
            self.assertEqual(start_iso, "2022-06-01")
            self.assertEqual(end_iso, "2022-06-03")
            self.assertFalse(allow_oos)
            return chains

        with mock.patch.object(
            feasibility.pandas_feed, "load_cached_chains", fake_loader
        ):
            report = feasibility.measured_feasibility(
                symbols=["SYN"], widths=[2], start="2022-06-01", end="2022-06-03"
            )

        stats = report["widths"][2]
        self.assertEqual(report["cached_chain_days"], 3)
        self.assertEqual(stats["observations"], 3)
        self.assertEqual(stats["accepted"], 1)
        self.assertEqual(
            stats["skip_reasons"], {"liquidity": 1, "long_strike_missing": 1}
        )
        self.assertAlmostEqual(stats["credit"]["median"], 0.5416)
        self.assertEqual(stats["contracts"]["min"], 4)

    def test_refuses_oos_window_before_loading_any_cached_values(self):
        loader = mock.Mock(side_effect=AssertionError("must not load OOS values"))

        with mock.patch.object(feasibility.pandas_feed, "load_cached_chains", loader):
            with self.assertRaises(OOSDataTouchError):
                feasibility.measured_feasibility(
                    symbols=["SPY"], widths=[2], start="2022-12-30", end="2023-01-03"
                )

        loader.assert_not_called()


if __name__ == "__main__":
    unittest.main()

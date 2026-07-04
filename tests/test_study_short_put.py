"""tests/test_study_short_put.py"""
import unittest

import pandas as pd

import config
from options_researcher.studies.short_put_vertical import compute_put_cycles
from strategies.base import entry_credit_conservative


def chain(iso_exp, rows_spec):
    rows = []
    for right, strike, delta, bid in rows_spec:
        rows.append({"expiration": iso_exp, "strike": strike, "right": right,
                     "bid": bid, "ask": bid + 0.10, "open_interest": 500,
                     "iv": 0.40, "delta": delta, "gamma": 0.0, "theta": 0.0,
                     "vega": 0.0})
    return pd.DataFrame(rows)


class ShortPutTests(unittest.TestCase):
    def setUp(self):
        # One cycle: roll 2024-05-17, monthly expiry 2024-06-21.
        self.closes_win = pd.Series({"2024-05-17": 100.0, "2024-06-21": 105.0})
        self.closes_loss = pd.Series({"2024-05-17": 100.0, "2024-06-21": 80.0})
        self.chains = {"2024-05-17": chain("2024-06-21", [
            ("P", 95.0, -0.30, 2.00),     # short leg
            ("P", 90.0, -0.20, 1.00),     # long wing for $5 spread
        ])}

    def test_naked_win_keeps_credit(self):
        t = compute_put_cycles("VST", self.closes_win, self.chains,
                               target_delta=0.30, width=None)
        row = t[t["skipped"].isna()].iloc[0]
        expected_credit = 2.00 * (1 - config.SLIPPAGE_HAIRCUT) * 100 - 0.65
        self.assertTrue(bool(row["expired_worthless"]))
        self.assertAlmostEqual(row["pnl"], expected_credit, places=2)

    def test_naked_loss_pays_intrinsic(self):
        t = compute_put_cycles("VST", self.closes_loss, self.chains,
                               target_delta=0.30, width=None)
        row = t[t["skipped"].isna()].iloc[0]
        expected_credit = 2.00 * (1 - config.SLIPPAGE_HAIRCUT) * 100 - 0.65
        self.assertAlmostEqual(row["pnl"],
                               expected_credit - (95.0 - 80.0) * 100, places=2)

    def test_spread_caps_loss_at_width_minus_credit(self):
        t = compute_put_cycles("VST", self.closes_loss, self.chains,
                               target_delta=0.30, width=5.0)
        row = t[t["skipped"].isna()].iloc[0]
        credit = entry_credit_conservative(
            2.00, 2.10, 1.00, 1.10, config.SLIPPAGE_HAIRCUT) * 100 - 2 * 0.65
        # close 80: short pays -1500, wing pays +1000 -> net -500 + credit
        self.assertAlmostEqual(row["pnl"], credit - 500.0, places=2)

    def test_missing_wing_skips_fail_closed(self):
        chains = {"2024-05-17": chain("2024-06-21", [("P", 95.0, -0.30, 2.00)])}
        t = compute_put_cycles("VST", self.closes_win, chains,
                               target_delta=0.30, width=5.0)
        self.assertEqual(t.iloc[0]["skipped"], "no_long_wing")


if __name__ == "__main__":
    unittest.main()

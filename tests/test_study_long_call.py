"""tests/test_study_long_call.py"""
import unittest

import pandas as pd

import config
from options_researcher.studies.long_call_carry import (
    compute_leaps_cycles, compute_long_call_cycles)


def chain(rows_spec):
    rows = []
    for exp, right, strike, delta, bid in rows_spec:
        rows.append({"expiration": exp, "strike": strike, "right": right,
                     "bid": bid, "ask": bid + 0.10, "open_interest": 500,
                     "iv": 0.40, "delta": delta, "gamma": 0.0, "theta": 0.0,
                     "vega": 0.0})
    return pd.DataFrame(rows)


class LongCallTests(unittest.TestCase):
    def test_monthly_call_win_and_loss_arithmetic(self):
        closes = pd.Series({"2024-05-17": 100.0, "2024-06-21": 112.0})
        chains = {"2024-05-17": chain([
            ("2024-06-21", "C", 105.0, 0.40, 2.00),
            ("2024-06-21", "P", 95.0, -0.30, 1.50),   # expiry discovery
        ])}
        t = compute_long_call_cycles("VST", closes, chains, target_delta=0.40)
        h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        cost = 2.10 * (1 + h) * 100 + comm
        self.assertAlmostEqual(t.iloc[0]["pnl"], (112 - 105) * 100 - cost, places=2)
        self.assertTrue(bool(t.iloc[0]["won"]))

    def test_leaps_cycle_uses_exit_bid_and_stock_compare(self):
        entry_exp = "2025-06-20"
        chains = {
            "2024-06-14": chain([(entry_exp, "C", 90.0, 0.70, 18.00)]),
            "2025-06-13": chain([(entry_exp, "C", 90.0, 0.85, 32.00)]),
        }
        closes = pd.Series({"2024-06-14": 100.0, "2025-06-13": 120.0})
        t = compute_leaps_cycles("VST", closes, chains, target_delta=0.70)
        h, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        cost = 18.10 * (1 + h) * 100 + comm
        proceeds = 32.00 * (1 - h) * 100 - comm
        self.assertEqual(len(t), 1)
        self.assertAlmostEqual(t.iloc[0]["pnl"], proceeds - cost, places=2)
        self.assertAlmostEqual(t.iloc[0]["stock_pnl_100sh"], 2000.0, places=2)


if __name__ == "__main__":
    unittest.main()

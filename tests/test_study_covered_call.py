"""tests/test_study_covered_call.py"""
import unittest

import pandas as pd

import config
from options_researcher.studies.covered_call_income import compute_cc_cycles


def chain(iso_exp, strike, delta, bid):
    # BOTH rights: expiration discovery (nearest_monthly) walks PUT rows by
    # M1 design -- real chains always carry both sides; a call-only fixture
    # would make cycle discovery return None (plan defect fixed 2026-07-04).
    rows = []
    for right, d in (("P", -0.30), ("C", delta)):
        rows.append({"expiration": iso_exp, "strike": strike,
                     "right": right, "bid": bid, "ask": bid + 0.10,
                     "open_interest": 500, "iv": 0.40, "delta": d,
                     "gamma": 0.0, "theta": 0.0, "vega": 0.0})
    return pd.DataFrame(rows)


class CoveredCallTests(unittest.TestCase):
    def test_two_cycles_one_assignment(self):
        # Cycle 1: roll 2024-05-17, expiry 2024-06-21 (real 3rd Fridays).
        # Sell 0.30d call K=110 for bid 2.00; close at expiry 105 -> keep
        # premium, not assigned. Cycle 2: roll 2024-06-21, expiry 2024-07-19,
        # K=112, bid 2.00; close 120 -> assigned at 112.
        closes = pd.Series({"2024-05-17": 100.0, "2024-06-21": 105.0,
                            "2024-07-19": 120.0})
        chains = {"2024-05-17": chain("2024-06-21", 110.0, 0.30, 2.00),
                  "2024-06-21": chain("2024-07-19", 112.0, 0.30, 2.00)}
        out = compute_cc_cycles("VST", closes, chains, target_delta=0.30)
        self.assertEqual(len(out), 2)
        c1, c2 = out.iloc[0], out.iloc[1]

        haircut, comm = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        credit = 2.00 * (1 - haircut) * 100 - comm
        self.assertFalse(bool(c1["assigned"]))
        self.assertAlmostEqual(c1["cc_pnl"], (105 - 100) * 100 + credit, places=2)
        self.assertAlmostEqual(c1["bh_pnl"], 500.0, places=2)
        self.assertTrue(bool(c2["assigned"]))
        # assigned: stock sold at 112, upside above capped
        self.assertAlmostEqual(c2["cc_pnl"], (112 - 105) * 100 + credit, places=2)
        self.assertAlmostEqual(c2["bh_pnl"], (120 - 105) * 100, places=2)
        self.assertLess(c2["cc_pnl"], c2["bh_pnl"])   # capped upside, stated

    def test_skips_cycle_when_no_delta_band_call(self):
        closes = pd.Series({"2024-05-17": 100.0, "2024-06-21": 105.0})
        chains = {"2024-05-17": chain("2024-06-21", 110.0, 0.05, 2.00)}
        out = compute_cc_cycles("VST", closes, chains, target_delta=0.30)
        self.assertEqual(len(out), 0)                 # fail closed

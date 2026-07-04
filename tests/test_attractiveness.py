"""tests/test_attractiveness.py"""
import unittest

import pandas as pd

import config
from options_researcher.attractiveness import (cc_card_rows, grade,
                                               put_card_rows)


def chain_rows(specs, exp="2026-07-17"):
    rows = []
    for right, strike, delta, bid in specs:
        rows.append({"expiration": exp, "strike": strike, "right": right,
                     "bid": bid, "ask": bid + 0.10, "open_interest": 500,
                     "iv": 0.5, "delta": delta, "gamma": 0.0, "theta": 0.0,
                     "vega": 0.0})
    return pd.DataFrame(rows)


class GradeTests(unittest.TestCase):
    def test_grade_directions(self):
        self.assertEqual(grade(0.012, 0.010, 0.006), "GREEN")
        self.assertEqual(grade(0.007, 0.010, 0.006), "AMBER")
        self.assertEqual(grade(0.005, 0.010, 0.006), "RED")
        self.assertEqual(grade(0.2, 0.3, 0.7, higher_is_better=False), "GREEN")
        self.assertEqual(grade(0.8, 0.3, 0.7, higher_is_better=False), "RED")


class PutCardTests(unittest.TestCase):
    def test_golden_numbers(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62,
                             earnings_in_cycle=False)
        r = rows[0]
        h = config.SLIPPAGE_HAIRCUT
        credit = 2.15 * (1 - h) * 100 - config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(r["credit"], credit, places=2)
        self.assertAlmostEqual(r["yield_mo"], credit / 14500.0, places=6)
        self.assertAlmostEqual(r["cushion"], 0.6495, places=3)
        self.assertEqual(r["grades"]["cushion"], "AMBER")
        self.assertEqual(r["grades"]["yield"], "GREEN")
        self.assertEqual(r["grades"]["iv_for_seller"], "GREEN")
        self.assertIn("promising", r["verdict"].lower())


class CCCardTests(unittest.TestCase):
    def test_below_basis_skipped_with_message(self):
        chain = chain_rows([("C", 110.0, 0.20, 1.50),
                            ("P", 100.0, -0.30, 1.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=112.0,
                            cost_basis=118.5, iv_rank=0.3,
                            earnings_in_cycle=False)
        self.assertIn("skipped", rows[0])
        self.assertIn("cost basis", rows[0]["skipped"])

    def test_normal_cc_grades(self):
        chain = chain_rows([("C", 175.0, 0.20, 1.60),
                            ("P", 145.0, -0.20, 2.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=160.0,
                            cost_basis=118.5, iv_rank=0.6,
                            earnings_in_cycle=True)
        r = rows[0]
        h = config.SLIPPAGE_HAIRCUT
        credit = 1.60 * (1 - h) * 100 - config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(r["credit"], credit, places=2)
        self.assertEqual(r["grades"]["earnings"], "AMBER")
        self.assertEqual(r["grades"]["upside_room"], "GREEN")   # +9.4%
        self.assertIn("rents out", r["verdict"])


if __name__ == "__main__":
    unittest.main()

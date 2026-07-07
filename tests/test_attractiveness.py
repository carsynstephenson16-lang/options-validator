"""tests/test_attractiveness.py"""
import unittest

import pandas as pd

import config
from options_researcher.attractiveness import cc_card_rows, grade, put_card_rows


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
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
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


class VrpSellerTests(unittest.TestCase):
    """Seller lanes grade premium richness on the variance risk premium
    (iv_minus_rv), not on IV-rank alone. GREEN when IV >= trailing realized
    (positive VRP: the seller is paid at least the vol the stock recently
    delivered); AMBER otherwise. IV-rank stays as a separate context badge."""

    def test_positive_vrp_grades_green_on_put(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.05,
                             earnings_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "GREEN")

    def test_negative_vrp_grades_amber_on_put(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=-0.07,
                             earnings_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "AMBER")

    def test_vrp_badge_on_covered_call(self):
        chain = chain_rows([("C", 175.0, 0.20, 1.60), ("P", 145.0, -0.20, 2.0)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=160.0,
                            cost_basis=118.5, iv_rank=0.6, iv_minus_rv=-0.02,
                            earnings_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "AMBER")

    def test_vrp_badge_on_pmcc(self):
        from options_researcher.attractiveness import pmcc_card_rows
        chain = chain_rows([("C", 420.0, 0.20, 1.50), ("P", 340.0, -0.30, 5.0)])
        rows = pmcc_card_rows("MSFT", chain, "2026-06-30",
                              leaps_strike=340.0, leaps_premium=79.54,
                              close=373.0, iv_rank=0.88, iv_minus_rv=0.03,
                              earnings_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "GREEN")


class CCCardTests(unittest.TestCase):
    def test_below_basis_skipped_with_message(self):
        chain = chain_rows([("C", 110.0, 0.20, 1.50),
                            ("P", 100.0, -0.30, 1.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=112.0,
                            cost_basis=118.5, iv_rank=0.3, iv_minus_rv=0.0,
                            earnings_in_cycle=False)
        self.assertIn("skipped", rows[0])
        self.assertIn("cost basis", rows[0]["skipped"])

    def test_normal_cc_grades(self):
        chain = chain_rows([("C", 175.0, 0.20, 1.60),
                            ("P", 145.0, -0.20, 2.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=160.0,
                            cost_basis=118.5, iv_rank=0.6, iv_minus_rv=0.01,
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


class PMCCCardTests(unittest.TestCase):
    def test_only_safe_strikes_and_golden_numbers(self):
        from options_researcher.attractiveness import pmcc_card_rows
        # MSFT LEAPS strike 340 + premium 79.54 => safety strike 419.54.
        # $400 call is UNSAFE (below), must be excluded; $420 is safe.
        chain = chain_rows([("C", 400.0, 0.28, 3.00),
                            ("C", 420.0, 0.20, 1.50),
                            ("P", 340.0, -0.30, 5.00)])   # for expiry discovery
        rows = pmcc_card_rows("MSFT", chain, "2026-06-30",
                              leaps_strike=340.0, leaps_premium=79.54,
                              close=373.0, iv_rank=0.88, iv_minus_rv=0.0,
                              earnings_in_cycle=False)
        self.assertEqual([r["strike"] for r in rows], [420.0])  # 400 excluded
        r = rows[0]
        h = config.SLIPPAGE_HAIRCUT
        credit = 1.50 * (1 - h) * 100 - config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(r["credit"], credit, places=2)
        self.assertAlmostEqual(r["yield_mo"], credit / (79.54 * 100), places=6)
        self.assertEqual(r["grades"]["safety"], "GREEN")
        self.assertIn("419.54", r["verdict"])          # states the safe floor
        self.assertIn("LEAPS", r["verdict"])

    def test_no_safe_strike_returns_empty(self):
        from options_researcher.attractiveness import pmcc_card_rows
        chain = chain_rows([("C", 400.0, 0.20, 3.00),
                            ("P", 340.0, -0.30, 5.00)])
        rows = pmcc_card_rows("MSFT", chain, "2026-06-30",
                              leaps_strike=340.0, leaps_premium=79.54,
                              close=373.0, iv_rank=0.88, iv_minus_rv=0.0,
                              earnings_in_cycle=False)
        self.assertEqual(rows, [])                      # 400 < 419.54, no safe

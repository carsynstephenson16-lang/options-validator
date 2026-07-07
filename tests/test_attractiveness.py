"""tests/test_attractiveness.py"""
import unittest

import pandas as pd

import config
from options_researcher.attractiveness import cc_card_rows, grade, put_card_rows


def chain_rows(specs, exp="2026-07-17", *, vega=0.0, iv=0.5):
    rows = []
    for right, strike, delta, bid in specs:
        rows.append({"expiration": exp, "strike": strike, "right": right,
                     "bid": bid, "ask": bid + 0.10, "open_interest": 500,
                     "iv": iv, "delta": delta, "gamma": 0.0, "theta": 0.0,
                     "vega": vega})
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
                             earnings_in_cycle=False, fomc_in_cycle=False)
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


class FomcCardTests(unittest.TestCase):
    """FOMC-in-cycle is a descriptive AMBER/GREEN badge, parallel to
    earnings-in-cycle -- it never gates, scores, or ranks a candidate."""

    def test_fomc_in_cycle_grades_amber(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=False, fomc_in_cycle=True)
        self.assertEqual(rows[0]["grades"]["fomc"], "AMBER")

    def test_fomc_not_in_cycle_grades_green(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["fomc"], "GREEN")


class VrpSellerTests(unittest.TestCase):
    """Seller lanes grade premium richness on the variance risk premium
    (iv_minus_rv), not on IV-rank alone. GREEN when IV >= trailing realized
    (positive VRP: the seller is paid at least the vol the stock recently
    delivered); AMBER otherwise. IV-rank stays as a separate context badge."""

    def test_positive_vrp_grades_green_on_put(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.05,
                             earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "GREEN")

    def test_negative_vrp_grades_amber_on_put(self):
        chain = chain_rows([("P", 145.0, -0.20, 2.15)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=-0.07,
                             earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "AMBER")

    def test_vrp_badge_on_covered_call(self):
        chain = chain_rows([("C", 175.0, 0.20, 1.60), ("P", 145.0, -0.20, 2.0)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=160.0,
                            cost_basis=118.5, iv_rank=0.6, iv_minus_rv=-0.02,
                            earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "AMBER")

    def test_vrp_badge_on_pmcc(self):
        from options_researcher.attractiveness import pmcc_card_rows
        chain = chain_rows([("C", 420.0, 0.20, 1.50), ("P", 340.0, -0.30, 5.0)])
        rows = pmcc_card_rows("MSFT", chain, "2026-06-30",
                              leaps_strike=340.0, leaps_premium=79.54,
                              close=373.0, iv_rank=0.88, iv_minus_rv=0.03,
                              earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows[0]["grades"]["vrp_for_seller"], "GREEN")


class LongCallTests(unittest.TestCase):
    """TACTICAL short-dated long call: buy ~H4_TACTICAL_DELTA on the nearest
    monthly. Max loss = premium, so fits_cap grades cost vs MAX_LOSS_PER_TRADE;
    iv_for_buyer prefers LOW IV-rank. Descriptive preview, not an H5 income lane."""

    def test_picks_tactical_delta_and_grades(self):
        # a put row must exist so nearest_monthly can resolve the expiration
        from options_researcher.attractiveness import long_call_card_rows
        chain = chain_rows([("C", 170.0, 0.40, 3.00), ("P", 150.0, -0.20, 2.0)])
        rows = long_call_card_rows("VST", chain, "2026-06-30",
                                   close=160.0, iv_rank=0.3)
        r = rows[0]
        self.assertEqual(r["strike"], 170.0)
        ask = 3.00 + 0.10  # chain_rows sets ask = bid + 0.10
        cost = ask * (1 + config.SLIPPAGE_HAIRCUT) * 100 + config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(r["cost"], cost, places=2)      # ~$313.75
        self.assertEqual(r["grades"]["fits_cap"], "GREEN")     # <= 600
        self.assertEqual(r["grades"]["iv_for_buyer"], "GREEN")  # rank 0.3 <= 0.3
        self.assertIn("liquidity", r["grades"])

    def test_over_cap_and_high_iv_grade_red(self):
        from options_researcher.attractiveness import long_call_card_rows
        chain = chain_rows([("C", 170.0, 0.40, 7.00), ("P", 150.0, -0.20, 2.0)])
        rows = long_call_card_rows("VST", chain, "2026-06-30",
                                   close=160.0, iv_rank=0.9)
        self.assertEqual(rows[0]["grades"]["fits_cap"], "RED")      # ~$718 > 600
        self.assertEqual(rows[0]["grades"]["iv_for_buyer"], "RED")  # rank 0.9 >= 0.7

    def test_long_call_card_speaks_vega_and_iv(self):
        from options_researcher.attractiveness import long_call_card_rows
        chain = chain_rows([("C", 170.0, 0.40, 3.00), ("P", 150.0, -0.20, 2.0)],
                           vega=42.0, iv=0.35)
        rows = long_call_card_rows("VST", chain, "2026-06-30",
                                   close=160.0, iv_rank=0.3)
        self.assertIn("implied vol drops 1 point", rows[0]["verdict"])
        self.assertIn("35%", rows[0]["verdict"])
        self.assertAlmostEqual(rows[0]["vega"], 42.0)
        self.assertAlmostEqual(rows[0]["iv"], 0.35)

    def test_long_call_omits_vol_when_nan(self):
        from options_researcher.attractiveness import long_call_card_rows
        chain = chain_rows([("C", 170.0, 0.40, 3.00), ("P", 150.0, -0.20, 2.0)],
                           vega=42.0, iv=0.35)
        chain.loc[0, "vega"] = float("nan")
        rows = long_call_card_rows("VST", chain, "2026-06-30",
                                   close=160.0, iv_rank=0.3)
        self.assertNotIn("implied vol drops 1 point", rows[0]["verdict"])
        self.assertIsNone(rows[0]["vega"])
        self.assertIsNone(rows[0]["iv"])


class LeapsCardTests(unittest.TestCase):
    def test_leaps_card_speaks_vega_and_iv(self):
        from options_researcher.attractiveness import leaps_card_rows
        chain = chain_rows([("C", 350.0, 0.70, 80.0)], exp="2027-06-17",
                           vega=129.24, iv=0.378)
        rows = leaps_card_rows("MSFT", chain, "2026-06-30", close=373.0,
                               iv_rank=0.5, bucket_room=10_000.0)
        self.assertIn("implied vol drops 1 point", rows[0]["verdict"])
        self.assertIn("129", rows[0]["verdict"])
        self.assertAlmostEqual(rows[0]["vega"], 129.24)
        self.assertAlmostEqual(rows[0]["iv"], 0.378)

    def test_leaps_omits_vol_when_nan(self):
        from options_researcher.attractiveness import leaps_card_rows
        chain = chain_rows([("C", 350.0, 0.70, 80.0)], exp="2027-06-17",
                           vega=129.24, iv=0.378)
        chain.loc[0, "iv"] = float("nan")
        rows = leaps_card_rows("MSFT", chain, "2026-06-30", close=373.0,
                               iv_rank=0.5, bucket_room=10_000.0)
        self.assertNotIn("implied vol drops 1 point", rows[0]["verdict"])
        self.assertIsNone(rows[0]["vega"])
        self.assertIsNone(rows[0]["iv"])


class SectionsJsonTests(unittest.TestCase):
    def test_serializes_sections_to_json(self):
        import json

        from options_researcher.attractiveness_dashboard import sections_json
        fake = [{"symbol": "VST", "as_of": "2026-06-30", "close": 158.63,
                 "iv_rank": 0.47, "groups": [
                     {"kind": "put", "title": "SELL A PUT?", "preview": False,
                      "cards": [{"strike": 145.0, "credit": 212.0,
                                 "grades": {"liquidity": "RED"}}], "empty": None}]}]
        out = json.loads(sections_json(fake))
        self.assertEqual(out["sections"][0]["symbol"], "VST")
        self.assertEqual(out["sections"][0]["groups"][0]["cards"][0]["strike"], 145.0)


class CCCardTests(unittest.TestCase):
    def test_below_basis_skipped_with_message(self):
        chain = chain_rows([("C", 110.0, 0.20, 1.50),
                            ("P", 100.0, -0.30, 1.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=112.0,
                            cost_basis=118.5, iv_rank=0.3, iv_minus_rv=0.0,
                            earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertIn("skipped", rows[0])
        self.assertIn("cost basis", rows[0]["skipped"])

    def test_normal_cc_grades(self):
        chain = chain_rows([("C", 175.0, 0.20, 1.60),
                            ("P", 145.0, -0.20, 2.00)])
        rows = cc_card_rows("VST", chain, "2026-06-30", close=160.0,
                            cost_basis=118.5, iv_rank=0.6, iv_minus_rv=0.01,
                            earnings_in_cycle=True, fomc_in_cycle=False)
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
                              earnings_in_cycle=False, fomc_in_cycle=False)
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
                              earnings_in_cycle=False, fomc_in_cycle=False)
        self.assertEqual(rows, [])                      # 400 < 419.54, no safe

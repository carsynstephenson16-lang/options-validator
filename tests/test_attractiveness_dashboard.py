"""tests/test_attractiveness_dashboard.py"""
import math
import unittest

from options_researcher import attractiveness_dashboard as ad


class PriceLadderTests(unittest.TestCase):
    def test_ladder_uses_moves_strike_breakeven_and_tags(self):
        rows = ad._price_ladder(close=100.0, rv21=math.sqrt(12) * 0.10,
                                strike=95.0, breakeven=97.0)
        # monthly_move = 0.10 -> points at 80,90,100,110,120 plus 95,97
        prices = [r["price"] for r in rows]
        self.assertEqual(prices, sorted(prices))          # ascending
        self.assertEqual(len(prices), len(set(prices)))   # deduped
        self.assertTrue(all(p > 0 for p in prices))
        tag_by_price = {r["price"]: r["tag"] for r in rows}
        self.assertEqual(tag_by_price[100.0], "today")
        self.assertEqual(tag_by_price[95.0], "strike")
        self.assertEqual(tag_by_price[97.0], "breakeven")

    def test_invalid_vol_falls_back_to_close_strike_breakeven(self):
        rows = ad._price_ladder(close=100.0, rv21=float("nan"),
                                strike=95.0, breakeven=97.0)
        self.assertEqual([r["price"] for r in rows], [95.0, 97.0, 100.0])

    def test_nonpositive_prices_dropped(self):
        # huge vol would push the -2 sigma point below zero
        rows = ad._price_ladder(close=10.0, rv21=math.sqrt(12) * 0.60,
                                strike=10.0, breakeven=None)
        self.assertTrue(all(r["price"] > 0 for r in rows))

    def test_coinciding_anchor_tags_are_combined(self):
        # strike and breakeven landing on the same rounded price keep both
        # labels instead of the later one silently overwriting the earlier.
        rows = ad._price_ladder(close=100.0, rv21=float("nan"),
                                strike=95.0, breakeven=95.0)
        tag_by_price = {r["price"]: r["tag"] for r in rows}
        self.assertEqual(tag_by_price[95.0], "strike, breakeven")


class PayoffTests(unittest.TestCase):
    def test_put_pnl(self):
        self.assertAlmostEqual(ad._put_pnl(145.0, 145.0, 212.20), 212.20, 2)
        self.assertAlmostEqual(ad._put_pnl(130.0, 145.0, 212.20), -1287.80, 2)

    def test_cc_pnl_vs_today(self):
        # called away at strike above today: credit + 100*(strike-close)
        self.assertAlmostEqual(ad._cc_pnl(180.0, 175.0, 150.0, 160.0),
                               150.0 + 1500.0, 2)
        # below strike: marked at scenario price
        self.assertAlmostEqual(ad._cc_pnl(150.0, 175.0, 150.0, 160.0),
                               150.0 - 1000.0, 2)

    def test_pmcc_split(self):
        above = ad._pmcc_pnl(430.0, 420.0, 340.0, 7954.0, 100.0)
        self.assertAlmostEqual(above[0], (420.0 - 340.0) * 100 - 7954.0 + 100.0, 2)
        self.assertEqual(above[1], "")
        below = ad._pmcc_pnl(400.0, 420.0, 340.0, 7954.0, 100.0)
        self.assertAlmostEqual(below[0], 100.0, 2)
        self.assertIn("LEAPS value not counted", below[1])

    def test_leaps_pnl(self):
        self.assertAlmostEqual(ad._leaps_pnl(457.32, 340.0, 7954.0),
                               (457.32 - 340.0) * 100 - 7954.0, 2)
        self.assertAlmostEqual(ad._leaps_pnl(300.0, 340.0, 7954.0), -7954.0, 2)


class ScenarioRowsTests(unittest.TestCase):
    def test_put_scenarios_carry_pnl_and_tags(self):
        card = {"strike": 145.0, "credit": 212.20}
        rows = ad.scenario_rows(card, "put", close=160.0,
                                rv21=math.sqrt(12) * 0.10)
        self.assertTrue(rows)
        self.assertTrue(any(r["tag"] == "strike" for r in rows))
        strike_row = next(r for r in rows if r["tag"] == "strike")
        self.assertAlmostEqual(strike_row["pnl"], 212.20, 2)

    def test_pmcc_scenarios_note_below_strike(self):
        card = {"strike": 420.0, "credit": 100.0,
                "leaps_strike": 340.0, "leaps_cost": 7954.0}
        rows = ad.scenario_rows(card, "pmcc", close=373.02,
                                rv21=math.sqrt(12) * 0.11)
        below = [r for r in rows if r["price"] < 420.0]
        self.assertTrue(below and all(r["note"] for r in below))

    def test_unknown_structure_raises(self):
        with self.assertRaises(ValueError):
            ad.scenario_rows({"strike": 1.0}, "bogus", close=1.0, rv21=1.0)


class AssembleTests(unittest.TestCase):
    def _fake_symbol(self):
        return {
            "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
            "iv_rank": 0.88,
            "groups": [
                {"kind": "put", "title": "SELL A PUT?",
                 "cards": [{"strike": 350.0, "expiry": "2026-07-17",
                            "dte": 17, "credit": 250.0, "yield_mo": 0.0071,
                            "grades": {"yield": "AMBER"},
                            "verdict": "you'd be promising..."}],
                 "empty": None},
                {"kind": "pmcc", "title": "SELL A CALL AGAINST YOUR LEAPS?",
                 "leaps_strike": 340.0, "leaps_premium": 79.54,
                 "cards": [{"strike": 420.0, "expiry": "2026-07-17",
                            "dte": 17, "credit": 100.0, "yield_mo": 0.0126,
                            "grades": {"safety": "GREEN"},
                            "verdict": "sells a $420 call..."}],
                 "empty": None},
            ],
        }

    def test_assemble_attaches_scenarios_and_enriches_pmcc(self):
        d = ad.assemble(symbol_sections=[self._fake_symbol()],
                        rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})
        put_card = d["symbols"][0]["groups"][0]["cards"][0]
        self.assertTrue(put_card["scenarios"])
        self.assertIn("Sell", put_card["headline"])
        pmcc_card = d["symbols"][0]["groups"][1]["cards"][0]
        self.assertEqual(pmcc_card["leaps_strike"], 340.0)
        self.assertAlmostEqual(pmcc_card["leaps_cost"], 7954.0, 2)
        self.assertTrue(any(r["note"] for r in pmcc_card["scenarios"]))

    def test_skipped_card_gets_no_scenarios(self):
        section = {"symbol": "VST", "as_of": "2026-06-30", "close": 112.0,
                   "iv_rank": 0.3,
                   "groups": [{"kind": "cc", "title": "SELL A COVERED CALL?",
                               "cards": [{"strike": 110.0,
                                          "skipped": "strike below cost basis"}],
                               "empty": None}]}
        d = ad.assemble(symbol_sections=[section],
                        rv21_by_symbol={"VST": 0.5})
        card = d["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(card["scenarios"], [])
        self.assertEqual(card["headline"], "")

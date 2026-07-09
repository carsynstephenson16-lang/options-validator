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

    def test_long_call_scenarios_carry_pnl(self):
        card = {"strike": 340.0, "cost": 7954.0, "breakeven": 419.54}
        rows = ad.scenario_rows(card, "long_call", close=373.02,
                                rv21=math.sqrt(12) * 0.11)
        self.assertTrue(rows)
        strike_row = next(r for r in rows if r["tag"] == "strike")
        self.assertAlmostEqual(strike_row["pnl"], -7954.0, 2)

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

    def test_multi_card_ladder_group_survives_and_marks_one_leader(self):
        # A real ladder group carries several expirations; only the ranked
        # leader's headline gets the star.
        section = {
            "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
            "iv_rank": 0.88,
            "groups": [
                {"kind": "put", "title": "SELL A PUT?",
                 "cards": [
                     {"strike": 350.0, "expiry": "2026-07-17", "dte": 17,
                      "credit": 250.0, "yield_mo": 0.0071,
                      "grades": {"yield": "AMBER"},
                      "verdict": "near-dated put...", "rank_leader": False},
                     {"strike": 345.0, "expiry": "2026-08-21", "dte": 52,
                      "credit": 420.0, "yield_mo": 0.0122,
                      "grades": {"yield": "GREEN"},
                      "verdict": "further-dated put...", "rank_leader": True},
                 ],
                 "empty": None},
            ],
        }
        d = ad.assemble(symbol_sections=[section],
                        rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})
        cards = d["symbols"][0]["groups"][0]["cards"]
        self.assertEqual(len(cards), 2)                      # both survive
        headlines = [c["headline"] for c in cards]
        self.assertEqual(len(headlines), 2)
        starred = [h for h in headlines if "★" in h]
        self.assertEqual(len(starred), 1)                    # exactly one leader
        leader = next(c for c in cards if c["rank_leader"])
        self.assertIn("★", leader["headline"])

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


class HeadlineTests(unittest.TestCase):
    def test_headline_marks_ladder_leader(self):
        leader = {"strike": 145.0, "expiry": "2026-08-15", "dte": 60,
                  "credit": 210.0, "rank_leader": True}
        s = ad._headline("VST", "put", leader)
        self.assertIn("★", s)
        self.assertIn("60 days out", s)

    def test_headline_no_star_when_not_leader(self):
        card = {"strike": 145.0, "expiry": "2026-08-15", "dte": 60,
                "credit": 210.0, "rank_leader": False}
        s = ad._headline("VST", "put", card)
        self.assertNotIn("★", s)


class RenderTests(unittest.TestCase):
    def _assembled(self):
        return ad.assemble(
            symbol_sections=[{
                "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
                "iv_rank": 0.88,
                "groups": [
                    {"kind": "put", "title": "SELL A PUT?",
                     "cards": [{"strike": 350.0, "expiry": "2026-07-17",
                                "dte": 17, "credit": 250.0,
                                "grades": {"yield": "AMBER"},
                                "verdict": "promise to buy lower"}],
                     "empty": None},
                    {"kind": "cc", "title": "SELL A COVERED CALL?",
                     "cards": [], "empty": "no candidates this cycle"},
                ]}],
            rv21_by_symbol={"MSFT": 1.1})

    def test_render_has_label_and_no_external_assets(self):
        html = ad.render(self._assembled())
        self.assertIn("Your gain or loss", html)
        self.assertNotIn("You end up with", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://cdn", html)
        self.assertIn("<style>", html)

    def test_render_shows_empty_state_line(self):
        html = ad.render(self._assembled())
        self.assertIn("no candidates this cycle", html)

    def test_render_shows_grade_badges(self):
        html = ad.render(self._assembled())
        self.assertIn("yield:AMBER", html)

    def test_render_escapes_dynamic_text(self):
        assembled = self._assembled()
        assembled["symbols"][0]["groups"][0]["cards"][0]["verdict"] = "<x>&"
        html = ad.render(assembled)
        self.assertNotIn("<x>&", html)
        self.assertIn("&lt;x&gt;&amp;", html)

    def test_render_defines_label_css(self):
        # The scenario tags / notes / countdown lean on the .label class;
        # regressing the copied stylesheet would silently unstyle them.
        html = ad.render(self._assembled())
        self.assertIn(".label", html)

    def test_render_skipped_card(self):
        d = ad.assemble(
            symbol_sections=[{
                "symbol": "VST", "as_of": "2026-06-30", "close": 112.0,
                "iv_rank": 0.3,
                "groups": [{"kind": "cc", "title": "SELL A COVERED CALL?",
                            "cards": [{"strike": 110.0,
                                       "skipped": "strike below cost basis"}],
                            "empty": None}]}],
            rv21_by_symbol={"VST": 0.5})
        html = ad.render(d)
        self.assertIn("strike below cost basis", html)
        # a skipped card carries no scenario table
        self.assertNotIn("Your gain or loss", html)

    def test_render_pmcc_note_and_leaps_countdown(self):
        d = ad.assemble(
            symbol_sections=[{
                "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
                "iv_rank": 0.88,
                "groups": [
                    {"kind": "pmcc", "title": "PMCC",
                     "leaps_strike": 340.0, "leaps_premium": 79.54,
                     "cards": [{"strike": 420.0, "expiry": "2026-07-17",
                                "dte": 17, "credit": 100.0,
                                "grades": {"safety": "GREEN"},
                                "verdict": "safe strike"}],
                     "empty": None},
                    {"kind": "leaps", "title": "BUY A LEAPS?",
                     "cards": [{"strike": 340.0, "expiry": "2027-06-17",
                                "dte": 352, "cost": 7954.0, "breakeven": 419.54,
                                "grades": {"fits_bucket": "RED"},
                                "verdict": "buys upside"}],
                     "empty": None},
                ]}],
            rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})
        html = ad.render(d)
        self.assertIn("LEAPS value not counted", html)   # PMCC note branch
        self.assertIn("roll reminder", html)             # leaps countdown branch


class MainTests(unittest.TestCase):
    def test_main_writes_file_and_prints_path(self):
        import io
        import os
        import tempfile
        from contextlib import redirect_stdout
        from unittest import mock

        section = {"symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
                   "iv_rank": 0.88,
                   "groups": [{"kind": "put", "title": "SELL A PUT?",
                               "cards": [], "empty": "none this cycle"}]}
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "dashboard", "attractiveness.html")
            with mock.patch.object(ad, "OUTPUT_PATH", out):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    path = ad.main(symbol_sections=[section],
                                   rv21_by_symbol={"MSFT": 1.1})
                self.assertTrue(os.path.exists(out))
                self.assertIn("attractiveness.html", buf.getvalue())
                self.assertEqual(path, os.path.abspath(out))

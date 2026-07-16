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


class DataAsOfBannerTests(unittest.TestCase):
    def test_page_data_as_of_single_date(self):
        sections = [{"as_of": "2026-06-30"}, {"as_of": "2026-06-30"}]
        self.assertEqual(ad._page_data_as_of(sections), "2026-06-30")

    def test_page_data_as_of_picks_earliest_when_mixed(self):
        # A stale name's chain cache must not hide behind a fresher one.
        sections = [{"as_of": "2026-06-30"}, {"as_of": "2026-06-01"}]
        self.assertEqual(ad._page_data_as_of(sections), "2026-06-01")

    def test_page_data_as_of_falls_back_when_no_sections(self):
        self.assertEqual(ad._page_data_as_of([]), "no cached data")

    def test_assemble_attaches_page_data_as_of(self):
        section = {"symbol": "MSFT", "as_of": "2026-06-15", "close": 373.02,
                   "iv_rank": 0.5,
                   "groups": [{"kind": "put", "title": "SELL A PUT?",
                               "cards": [], "empty": "none this cycle"}]}
        d = ad.assemble(symbol_sections=[section], rv21_by_symbol={"MSFT": 1.1})
        self.assertEqual(d["data_as_of"], "2026-06-15")

    def test_render_shows_prominent_data_as_of_banner(self):
        section = {"symbol": "MSFT", "as_of": "2026-06-15", "close": 373.02,
                   "iv_rank": 0.5,
                   "groups": [{"kind": "put", "title": "SELL A PUT?",
                               "cards": [], "empty": "none this cycle"}]}
        d = ad.assemble(symbol_sections=[section], rv21_by_symbol={"MSFT": 1.1})
        html = ad.render(d)
        self.assertIn("DATA AS-OF 2026-06-15 CLOSE", html)
        self.assertIn("Research only", html)
        self.assertIn("verify live quotes in your broker", html)
        self.assertIn("data-asof-banner", html)
        self.assertLess(html.index("DATA AS-OF"),
                        html.index("WHICH OPTIONS LOOK ATTRACTIVE TODAY?"))

    def test_render_falls_back_banner_text_when_no_data(self):
        d = {"symbols": [], "data_as_of": None}
        html = ad.render(d)
        self.assertIn("DATA AS-OF no cached data CLOSE", html)


class BbbRowsTests(unittest.TestCase):
    # rv21 = sqrt(12) * 0.10 -> monthly_move = 0.10 exactly.
    RV = math.sqrt(12) * 0.10

    def test_put_bbb_math_k1(self):
        card = {"strike": 95.0, "credit": 200.0, "dte": 30}
        rows = ad.bbb_rows(card, "put", close=100.0, rv21=self.RV)
        self.assertEqual([r["scenario"] for r in rows],
                         ["bear", "base", "bull"])
        by = {r["scenario"]: r for r in rows}
        # dte=30 -> k=1 -> bear 90, base 100, bull 110
        self.assertAlmostEqual(by["bear"]["price"], 90.0, 2)
        self.assertAlmostEqual(by["base"]["price"], 100.0, 2)
        self.assertAlmostEqual(by["bull"]["price"], 110.0, 2)
        self.assertAlmostEqual(by["bear"]["pnl"], 200.0 - 500.0, 2)
        self.assertAlmostEqual(by["base"]["pnl"], 200.0, 2)
        self.assertAlmostEqual(by["bull"]["pnl"], 200.0, 2)

    def test_k_scales_with_dte_and_caps_at_two(self):
        card = {"strike": 95.0, "credit": 200.0, "dte": 120}
        by = {r["scenario"]: r for r in
              ad.bbb_rows(card, "put", close=100.0, rv21=self.RV)}
        self.assertAlmostEqual(by["bear"]["price"], 80.0, 2)  # k=2
        self.assertAlmostEqual(by["bull"]["price"], 120.0, 2)
        card = {"strike": 95.0, "credit": 200.0, "dte": 300}  # sqrt(10)>2
        by = {r["scenario"]: r for r in
              ad.bbb_rows(card, "put", close=100.0, rv21=self.RV)}
        self.assertAlmostEqual(by["bear"]["price"], 80.0, 2)  # still capped

    def test_cc_bbb_math(self):
        card = {"strike": 105.0, "credit": 150.0, "dte": 30}
        by = {r["scenario"]: r for r in
              ad.bbb_rows(card, "cc", close=100.0, rv21=self.RV)}
        self.assertAlmostEqual(by["bear"]["pnl"], 150.0 - 1000.0, 2)
        self.assertAlmostEqual(by["base"]["pnl"], 150.0, 2)
        self.assertAlmostEqual(by["bull"]["pnl"], 150.0 + 500.0, 2)

    def test_pmcc_bbb_math_and_note(self):
        card = {"strike": 105.0, "credit": 100.0, "dte": 30,
                "leaps_strike": 80.0, "leaps_cost": 2500.0}
        by = {r["scenario"]: r for r in
              ad.bbb_rows(card, "pmcc", close=100.0, rv21=self.RV)}
        self.assertAlmostEqual(by["bull"]["pnl"],
                               (105.0 - 80.0) * 100 - 2500.0 + 100.0, 2)
        self.assertAlmostEqual(by["bear"]["pnl"], 100.0, 2)
        self.assertIn("LEAPS value not counted", by["bear"]["note"])

    def test_leaps_and_long_call_bbb_math(self):
        card = {"strike": 90.0, "cost": 1500.0, "dte": 30}
        for structure in ("leaps", "long_call"):
            by = {r["scenario"]: r for r in
                  ad.bbb_rows(card, structure, close=100.0, rv21=self.RV)}
            self.assertAlmostEqual(by["bull"]["pnl"], 2000.0 - 1500.0, 2)
            self.assertAlmostEqual(by["base"]["pnl"], 1000.0 - 1500.0, 2)
            self.assertAlmostEqual(by["bear"]["pnl"], -1500.0, 2)

    def test_bad_rv21_returns_empty_never_invents(self):
        card = {"strike": 95.0, "credit": 200.0, "dte": 30}
        for rv in (float("nan"), 0.0, -0.3):
            self.assertEqual(ad.bbb_rows(card, "put", close=100.0, rv21=rv),
                             [])

    def test_unknown_structure_raises(self):
        with self.assertRaises(ValueError):
            ad.bbb_rows({"strike": 1.0, "dte": 30}, "bogus",
                        close=1.0, rv21=self.RV)


def _pick_card(strike, expiry, *, dte=45, lane_fields=None, grades=None,
               rank_leader=False):
    card = {"strike": strike, "expiry": expiry, "dte": dte,
            "rank_leader": rank_leader, "grades": grades or {}}
    card.update(lane_fields or {})
    return card


class SelectTopPicksTests(unittest.TestCase):
    def _data(self):
        tech_up = {"trend": "up", "breakout_20d": False,
                   "ma_posture": "above_all"}
        return {"symbols": [
            {"symbol": "AAA", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01", "technicals": tech_up,
             "groups": [
                 {"kind": "put", "title": "P", "empty": None, "cards": [
                     _pick_card(95.0, "2026-08-21", rank_leader=True,
                                grades={"yield": "GREEN",
                                        "liquidity": "GREEN"},
                                lane_fields={"credit": 200.0,
                                             "annualized_yield": 0.30}),
                     _pick_card(90.0, "2026-09-18", dte=73,
                                grades={"yield": "GREEN",
                                        "liquidity": "GREEN"},
                                lane_fields={"credit": 300.0,
                                             "annualized_yield": 0.50}),
                 ]},
                 {"kind": "long_call", "title": "LC", "empty": None,
                  "cards": [
                      _pick_card(105.0, "2026-08-21",
                                 grades={"fits_cap": "GREEN",
                                         "liquidity": "GREEN"},
                                 lane_fields={"cost": 500.0,
                                              "breakeven": 110.0,
                                              "breakeven_move": 0.10}),
                  ]},
             ]},
            {"symbol": "BBB", "close": 50.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [
                 {"kind": "put", "title": "P", "empty": None, "cards": [
                     _pick_card(45.0, "2026-08-21",
                                grades={"yield": "GREEN", "cushion": "GREEN",
                                        "vrp_for_seller": "GREEN",
                                        "liquidity": "RED"},
                                rank_leader=True,
                                lane_fields={"credit": 100.0,
                                             "annualized_yield": 0.90}),
                     _pick_card(44.0, "2026-08-21",
                                grades={"yield": "GREEN",
                                        "liquidity": "GREEN"},
                                lane_fields={"credit": 80.0,
                                             "annualized_yield": 0.20}),
                 ]},
             ]},
        ]}

    def test_liquidity_red_is_a_hard_veto(self):
        picks = ad.select_top_picks(self._data())
        vetoed = [p for p in picks
                  if p["symbol"] == "BBB" and p["strike"] == 45.0]
        self.assertEqual(vetoed, [])

    def test_scoring_greens_leader_and_tech_bonus(self):
        import config
        picks = ad.select_top_picks(self._data())
        by_key = {(p["symbol"], p["lane"], p["strike"]): p for p in picks}
        # AAA put leader: 2 GREEN + leader bonus + sell-side tech bonus
        leader = by_key[("AAA", "put", 95.0)]
        self.assertEqual(leader["score"],
                         2 * config.PICK_GREEN_POINT
                         + config.PICK_RANK_LEADER_BONUS
                         + config.PICK_TECH_BONUS)
        # AAA long_call: 2 GREEN + buy-side tech bonus (trend up), no leader
        lc = by_key[("AAA", "long_call", 105.0)]
        self.assertEqual(lc["score"],
                         2 * config.PICK_GREEN_POINT + config.PICK_TECH_BONUS)
        # BBB has NO technicals snapshot -> no tech bonus for its put
        bbb = by_key[("BBB", "put", 44.0)]
        self.assertEqual(bbb["score"], 2 * config.PICK_GREEN_POINT)

    def test_one_pick_per_symbol_lane(self):
        picks = ad.select_top_picks(self._data(), n=10)
        keys = [(p["symbol"], p["lane"]) for p in picks]
        self.assertEqual(len(keys), len(set(keys)))
        # only ONE AAA put survives even though two candidates score equally
        self.assertEqual(sum(1 for k in keys if k == ("AAA", "put")), 1)

    def test_sell_lane_tiebreak_prefers_higher_annualized_yield(self):
        data = {"symbols": [
            {"symbol": "AAA", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "put", "title": "P", "empty": None,
                         "cards": [
                             _pick_card(95.0, "2026-08-21",
                                        grades={"yield": "GREEN"},
                                        lane_fields={
                                            "credit": 200.0,
                                            "annualized_yield": 0.30}),
                         ]}]},
            {"symbol": "BBB", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "put", "title": "P", "empty": None,
                         "cards": [
                             _pick_card(95.0, "2026-08-21",
                                        grades={"yield": "GREEN"},
                                        lane_fields={
                                            "credit": 200.0,
                                            "annualized_yield": 0.60}),
                         ]}]},
        ]}
        picks = ad.select_top_picks(data, n=2)
        self.assertEqual(picks[0]["symbol"], "BBB")  # higher yield first

    def test_buy_lane_tiebreak_prefers_smaller_breakeven_move(self):
        def lc(sym, move):
            return {"symbol": sym, "close": 100.0, "iv_rank": 0.5,
                    "as_of": "2026-07-01",
                    "groups": [{"kind": "long_call", "title": "LC",
                                "empty": None,
                                "cards": [_pick_card(
                                    105.0, "2026-08-21",
                                    grades={"fits_cap": "GREEN"},
                                    lane_fields={"cost": 500.0,
                                                 "breakeven": 110.0,
                                                 "breakeven_move": move})]}]}
        data = {"symbols": [lc("AAA", 0.12), lc("BBB", 0.04)]}
        picks = ad.select_top_picks(data, n=2)
        self.assertEqual(picks[0]["symbol"], "BBB")  # smaller move first

    def test_skipped_cards_never_enter_the_pool(self):
        data = {"symbols": [
            {"symbol": "AAA", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "cc", "title": "C", "empty": None,
                         "cards": [{"strike": 95.0,
                                    "skipped": "below cost basis"}]}]}]}
        self.assertEqual(ad.select_top_picks(data), [])

    def test_pick_carries_card_ref_and_fields(self):
        picks = ad.select_top_picks(self._data())
        p = picks[0]
        for key in ("symbol", "lane", "strike", "expiry", "dte", "score",
                    "card"):
            self.assertIn(key, p)
        self.assertIsInstance(p["card"], dict)


class LoadContextTests(unittest.TestCase):
    def _write(self, tmp, name, payload):
        import os
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            f.write(payload)
        return path

    def test_exact_match_no_warning(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "2026-07-15.json",
                        '{"as_of": "2026-07-15", "provenance": "LLM-asserted"}')
            ctx, warn = ad.load_context("2026-07-15", base_dir=tmp)
            self.assertEqual(ctx["as_of"], "2026-07-15")
            self.assertIsNone(warn)

    def test_stale_fallback_newest_not_after_as_of(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "2026-07-01.json", '{"as_of": "2026-07-01"}')
            self._write(tmp, "2026-07-10.json", '{"as_of": "2026-07-10"}')
            self._write(tmp, "2026-07-20.json", '{"as_of": "2026-07-20"}')
            ctx, warn = ad.load_context("2026-07-15", base_dir=tmp)
            self.assertEqual(ctx["as_of"], "2026-07-10")  # newest <= as-of
            self.assertEqual(warn, "research context is from 2026-07-10 "
                                   "(stale vs data as-of 2026-07-15)")

    def test_missing_returns_none_none(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ad.load_context("2026-07-15", base_dir=tmp),
                             (None, None))
            # only files dated AFTER the as-of -> still nothing usable
            self._write(tmp, "2026-07-20.json", '{"as_of": "2026-07-20"}')
            self.assertEqual(ad.load_context("2026-07-15", base_dir=tmp),
                             (None, None))
            # nonexistent dir is also honest
            gone = os.path.join(tmp, "nope")
            self.assertEqual(ad.load_context("2026-07-15", base_dir=gone),
                             (None, None))

    def test_malformed_json_warns_never_fabricates(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "2026-07-15.json", "{not json")
            ctx, warn = ad.load_context("2026-07-15", base_dir=tmp)
            self.assertIsNone(ctx)
            self.assertIn("unreadable", warn)

    def test_non_date_as_of_returns_none_none(self):
        self.assertEqual(ad.load_context("no cached data"), (None, None))


def _v2_section():
    return {
        "symbol": "MSFT", "as_of": "2026-06-30", "close": 373.02,
        "iv_rank": 0.88,
        "technicals": {"trend": "up", "breakout_20d": True,
                       "ma_posture": "above_all", "mom_1m": 0.042},
        "technicals_line": "above all MAs · 20d breakout · +4.2% 1M",
        "groups": [
            {"kind": "put", "title": "SELL A PUT?",
             "cards": [{"strike": 350.0, "expiry": "2026-07-17", "dte": 17,
                        "credit": 250.0, "annualized_yield": 0.15,
                        "rank_leader": True,
                        "grades": {"yield": "GREEN", "liquidity": "GREEN"},
                        "verdict": "promise to buy lower"}],
             "empty": None},
        ],
    }


def _v2_context(strike=350.0):
    return {
        "as_of": "2026-06-30",
        "provenance": "LLM-asserted (test fixture, web research 2026-06-30)",
        "market": {"summary": "megacaps steady into month end",
                   "regime": "mixed", "notes": ["breadth still narrow"]},
        "symbols": {"MSFT": {"news_summary": "Azure demand headlines",
                             "sentiment": "bull",
                             "catalysts": [{"date": "2026-07-22",
                                            "what": "earnings report",
                                            "source": "example"}]}},
        "top_picks": [{"symbol": "MSFT", "lane": "put", "strike": strike,
                       "expiry": "2026-07-17",
                       "why_now": "IV elevated vs realized",
                       "hypothesis": "premium overpays the move",
                       "thesis": "stays above 350",
                       "bull": "expires worthless, keep credit",
                       "base": "expires worthless",
                       "bear": "assigned at 350",
                       "logic": "cushion exceeds monthly move"}],
    }


class V2RenderTests(unittest.TestCase):
    def _assembled(self):
        return ad.assemble(symbol_sections=[_v2_section()],
                           rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})

    def test_hero_with_matched_context_pick(self):
        html = ad.render(self._assembled(), context=_v2_context())
        self.assertIn("TOP 3 PICKS TODAY", html)
        self.assertIn("IV elevated vs realized", html)          # why_now
        self.assertIn("cushion exceeds monthly move", html)     # logic
        self.assertIn("Sell the MSFT $350 put", html)           # matched card
        self.assertNotIn("unmatched to current candidates", html)
        # matched pick == python shortlist -> no disagreement note
        self.assertNotIn("Python quantitative shortlist differs", html)

    def test_hero_unmatched_pick_warns_and_discloses_disagreement(self):
        html = ad.render(self._assembled(), context=_v2_context(strike=999.0))
        self.assertIn("unmatched to current candidates", html)
        self.assertIn("Python quantitative shortlist differs", html)

    def test_provenance_label_on_every_narrative_surface(self):
        html = ad.render(self._assembled(), context=_v2_context())
        prov = "LLM-asserted (test fixture, web research 2026-06-30)"
        # hero narrative, market strip, and symbol news all carry the tag
        self.assertGreaterEqual(html.count(ad._esc(prov)), 3)
        self.assertIn('class="prov"', html)

    def test_missing_context_renders_honest_quant_shortlist(self):
        html = ad.render(self._assembled())
        self.assertIn("TOP 3 PICKS TODAY", html)
        self.assertIn("no research narratives for this date", html)
        self.assertIn("quantitative shortlist only", html)
        self.assertIn("pick score", html)
        # honesty: no narrative vocabulary invented
        self.assertNotIn("why now", html)

    def test_market_strip_present_with_context_absent_without(self):
        with_ctx = ad.render(self._assembled(), context=_v2_context())
        self.assertIn("MARKET CONTEXT", with_ctx)
        self.assertIn("megacaps steady into month end", with_ctx)
        self.assertIn("regime: mixed", with_ctx)
        without = ad.render(self._assembled())
        self.assertNotIn("MARKET CONTEXT", without)

    def test_symbol_panel_shows_technicals_line_and_news(self):
        html = ad.render(self._assembled(), context=_v2_context())
        self.assertIn("above all MAs", html)                  # technicals line
        self.assertIn("Azure demand headlines", html)         # news blurb
        self.assertIn("earnings report", html)                # catalyst

    def test_render_survives_sections_without_technicals(self):
        section = _v2_section()
        del section["technicals"]
        del section["technicals_line"]
        d = ad.assemble(symbol_sections=[section],
                        rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11})
        html = ad.render(d)
        self.assertIn("Sell the MSFT $350 put", html)
        self.assertNotIn('<div class="tech-line">', html)

    def test_cards_render_in_grid_with_collapsed_ladder_and_bbb(self):
        html = ad.render(self._assembled())
        self.assertIn('class="card-grid"', html)
        self.assertIn("<details><summary>payoff ladder</summary>", html)
        self.assertIn("scenario framing from realized vol", html)
        for tag in ("bear", "base", "bull"):
            self.assertIn(f"<td>{tag}</td>", html)

    def test_context_warning_banner_rendered(self):
        warn = ("research context is from 2026-06-25 "
                "(stale vs data as-of 2026-06-30)")
        html = ad.render(self._assembled(), context=_v2_context(),
                         context_warning=warn)
        self.assertIn("stale vs data as-of 2026-06-30", html)

    def test_assemble_attaches_bbb_and_empty_on_bad_rv(self):
        d = self._assembled()
        card = d["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(len(card["bbb"]), 3)
        d2 = ad.assemble(symbol_sections=[_v2_section()],
                         rv21_by_symbol={})  # rv21 -> NaN
        card2 = d2["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(card2["bbb"], [])

    def test_sections_json_carries_technicals(self):
        import json
        payload = json.loads(ad.sections_json([_v2_section()]))
        self.assertEqual(payload["sections"][0]["technicals"]["trend"], "up")
        self.assertIn("technicals_line", payload["sections"][0])


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

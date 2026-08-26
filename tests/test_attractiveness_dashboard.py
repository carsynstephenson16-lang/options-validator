"""tests/test_attractiveness_dashboard.py"""
import json
import math
import tempfile
import unittest
from pathlib import Path

import config
from options_researcher import attractiveness_dashboard as ad
from options_researcher.hypothesis_evidence import (
    EvidenceRow,
    EvidenceSource,
    EvidenceState,
    SymbolEvidence,
)


def _evidence(symbol: str) -> SymbolEvidence:
    return SymbolEvidence(
        symbol=symbol,
        hypotheses=(
            EvidenceRow(
                family="H5<script>",
                membership="tracked <owner>",
                family_state="NO_SIGNAL",
                symbol_states=(
                    EvidenceState("entry<label>", "WAIT & WATCH"),
                ),
                evaluation_session="2026-07-24",
                run_date="2026-07-25",
                sources=(
                    EvidenceSource(
                        "entry_watch",
                        "reports/h5/<unsafe>.txt",
                        "2026-07-24",
                    ),
                ),
                detail="NO RECEIPT H5 — expected daily <unsafe>",
                expected_daily=True,
                descriptive_only=False,
            ),
        ),
        intraday=EvidenceRow(
            family="INTRADAY",
            membership="descriptive-only capture",
            family_state="ok",
            symbol_states=(EvidenceState("capture", "ok"),),
            evaluation_session=None,
            run_date="2026-07-24",
            sources=(
                EvidenceSource(
                    "intraday",
                    "reports/intraday_capture/2026-07-24/preclose.json",
                    "2026-07-24",
                ),
            ),
            detail="solver-derived, not rank-comparable",
            expected_daily=False,
            descriptive_only=True,
        ),
    )


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


class SourceRenderingTests(unittest.TestCase):
    def test_structured_v2_source_renders_as_clickable_url(self):
        url = "https://investor.example.com/events"
        rendered = ad._sources_html(
            [
                {
                    "url": url,
                    "source_tier": "issuer_ir",
                    "published_at": "2026-07-01T12:00:00-04:00",
                    "publication_time_unknown_rationale": None,
                    "retrieved_at_utc": "2026-07-27T11:45:00Z",
                }
            ]
        )
        self.assertIn(f'href="{url}"', rendered)
        self.assertNotIn("source_tier", rendered)

    def test_legacy_url_string_still_renders_as_link(self):
        url = "https://example.com/legacy"
        self.assertIn(f'href="{url}"', ad._sources_html([url]))


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
        self.assertIn("365 calendar days", html)
        self.assertIn("252 trading sessions", html)
        self.assertNotIn("You end up with", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://cdn", html)
        self.assertIn("<style>", html)

    def test_render_shows_empty_state_line(self):
        html = ad.render(self._assembled())
        self.assertIn("no candidates this cycle", html)

    def test_render_shows_grade_badges(self):
        html = ad.render(self._assembled())
        self.assertIn("yield · AMBER", html)
        self.assertIn('class="status-badge watch"', html)

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

    def test_render_shows_compact_data_as_of_metadata_without_ribbon(self):
        section = {"symbol": "MSFT", "as_of": "2026-06-15", "close": 373.02,
                   "iv_rank": 0.5,
                   "groups": [{"kind": "put", "title": "SELL A PUT?",
                               "cards": [], "empty": "none this cycle"}]}
        d = ad.assemble(symbol_sections=[section], rv21_by_symbol={"MSFT": 1.1})
        html = ad.render(d)
        self.assertIn("<strong>Market close</strong> 2026-06-15", html)
        self.assertIn("Paper research", html)
        self.assertIn("verify the live broker quote", html)
        self.assertNotIn("data-asof-banner", html)
        self.assertNotIn("Research only", html)

    def test_render_falls_back_metadata_text_when_no_data(self):
        d = {"symbols": [], "data_as_of": None}
        html = ad.render(d)
        self.assertIn("<strong>Market close</strong> no cached data", html)

    def test_stale_display_extra_has_separate_visible_date(self):
        def section(symbol, as_of):
            return {
                "symbol": symbol,
                "as_of": as_of,
                "close": 100.0,
                "iv_rank": 0.5,
                "groups": [{
                    "kind": "put",
                    "title": "SELL A PUT?",
                    "cards": [],
                    "empty": "none this cycle",
                }],
            }

        data = ad.assemble(
            symbol_sections=[
                section("MSFT", "2026-07-24"),
                section("CLSK", "2026-07-01"),
            ],
            rv21_by_symbol={},
        )

        self.assertEqual(data["data_as_of"], "2026-07-24")
        self.assertEqual(data["display_data_as_of"], "2026-07-01")
        html = ad.render(data)
        self.assertIn("<strong>Market close</strong> 2026-07-24", html)
        self.assertIn("<strong>All display data</strong> 2026-07-01", html)


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

    def test_default_shortlist_width_is_configured_top_n(self):
        data = {"symbols": []}
        for index in range(6):
            data["symbols"].append({
                "symbol": f"S{index}", "close": 100.0, "iv_rank": 0.5,
                "as_of": "2026-07-01", "groups": [{
                    "kind": "put", "title": "P", "empty": None,
                    "cards": [_pick_card(
                        95.0, "2026-08-21", grades={"liquidity": "GREEN"},
                        lane_fields={"credit": 200.0,
                                     "annualized_yield": 0.30 - index / 100})],
                }],
            })
        picks = ad.select_top_picks(data)
        self.assertEqual(len(picks), config.PICK_TOP_N)
        self.assertEqual(config.PICK_TOP_N, 5)

    def test_scoring_greens_leader_and_tech_bonus(self):
        # The legacy display score stays on each pick for the audit line;
        # one-per-symbol means each symbol surfaces only its best card, so
        # score arithmetic is checked on single-symbol universes.
        import config
        data = self._data()
        aaa = {"symbols": [data["symbols"][0]]}
        bbb = {"symbols": [data["symbols"][1]]}
        # AAA put leader: 2 GREEN + leader bonus + sell-side tech bonus
        leader = ad.select_top_picks(aaa, n=1)[0]
        self.assertEqual((leader["lane"], leader["strike"]), ("put", 95.0))
        self.assertEqual(leader["score"],
                         2 * config.PICK_GREEN_POINT
                         + config.PICK_RANK_LEADER_BONUS
                         + config.PICK_TECH_BONUS)
        # BBB has NO technicals snapshot -> no tech bonus for its put
        bbb_pick = ad.select_top_picks(bbb, n=1)[0]
        self.assertEqual(bbb_pick["strike"], 44.0)
        self.assertEqual(bbb_pick["score"], 2 * config.PICK_GREEN_POINT)

    def test_at_most_one_pick_per_symbol(self):
        # AMZN once held 2 of 3 hero slots (put + call). The hero is a
        # cross-name shortlist: each symbol surfaces only its best card.
        picks = ad.select_top_picks(self._data(), n=10)
        symbols = [p["symbol"] for p in picks]
        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertEqual(sum(1 for s in symbols if s == "AAA"), 1)

    def test_green_fraction_not_raw_count_orders_cross_lane(self):
        # Seller lanes carry 7 gradeable badges, buyer lanes 3: raw GREEN
        # counts are not comparable across lanes. A 3/3 buyer card must
        # outrank a 5/7 seller card.
        data = {"symbols": [
            {"symbol": "SELL", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "put", "title": "P", "empty": None,
                         "cards": [_pick_card(
                             95.0, "2026-08-21",
                             grades={"yield": "GREEN", "cushion": "GREEN",
                                     "iv_for_seller": "GREEN",
                                     "vrp_for_seller": "GREEN",
                                     "liquidity": "GREEN",
                                     "earnings": "AMBER", "fomc": "AMBER"},
                             lane_fields={"credit": 200.0,
                                          "annualized_yield": 0.30})]}]},
            {"symbol": "BUYY", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "long_call", "title": "LC", "empty": None,
                         "cards": [_pick_card(
                             105.0, "2026-08-21",
                             grades={"fits_cap": "GREEN",
                                     "iv_for_buyer": "GREEN",
                                     "liquidity": "GREEN"},
                             lane_fields={"cost": 500.0, "breakeven": 110.0,
                                          "breakeven_move": 0.10})]}]},
        ]}
        picks = ad.select_top_picks(data, n=2)
        self.assertEqual(picks[0]["symbol"], "BUYY")
        self.assertEqual(picks[1]["symbol"], "SELL")

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

    def test_perfect_display_extra_cannot_change_mechanical_picks_or_gaps(self):
        import copy

        baseline = self._data()
        expected_picks = [
            (pick["symbol"], pick["lane"], pick["strike"])
            for pick in ad.select_top_picks(baseline)
        ]
        expected_gaps = ad._top3_gap_reasons(baseline)
        extra = copy.deepcopy(baseline["symbols"][0])
        extra["symbol"] = "CLSK"
        extra["display_only"] = True
        for group in extra["groups"]:
            for card in group["cards"]:
                card["grades"] = {
                    "fits_cap": "GREEN",
                    "yield": "GREEN",
                    "liquidity": "GREEN",
                }
                card["rank_leader"] = True
                card["breakeven_move"] = 0.0
                card["annualized_yield"] = 99.0
        with_extra = copy.deepcopy(baseline)
        with_extra["symbols"].insert(0, extra)

        actual_picks = [
            (pick["symbol"], pick["lane"], pick["strike"])
            for pick in ad.select_top_picks(with_extra)
        ]
        self.assertEqual(actual_picks, expected_picks)
        self.assertEqual(ad._top3_gap_reasons(with_extra), expected_gaps)
        self.assertNotIn("CLSK", {symbol for symbol, _, _ in actual_picks})


def _dominance_card(*, annualized_yield=0.20, cushion=0.10, upside=0.10,
                    cost=500.0, breakeven=105.0, breakeven_move=0.05,
                    grades=None, **extra):
    card = {
        "headline": extra.pop("headline", "candidate"),
        "annualized_yield": annualized_yield, "cushion": cushion,
        "upside": upside, "cost": cost, "breakeven": breakeven,
        "breakeven_move": breakeven_move,
        "grades": grades or {"liquidity": "GREEN", "portfolio": "GREEN"},
        "top3_snapshot": {"rank_eligible": True,
                          "selection_status": "ELIGIBLE",
                          "policy": {"status": "ELIGIBLE", "reason_codes": []}},
    }
    card.update(extra)
    return card


class DominancePartitionTests(unittest.TestCase):
    def test_put_dominance_hides_only_directly_dominated_card(self):
        best = _dominance_card(annualized_yield=0.30, cushion=0.15)
        worse = _dominance_card(annualized_yield=0.20, cushion=0.10)
        tradeoff = _dominance_card(annualized_yield=0.40, cushion=0.05)
        shown, hidden = ad.dominated_partition([best, worse, tradeoff], "put", 100.0)
        self.assertEqual(shown, [best, tradeoff])
        self.assertEqual(hidden, [(worse, best)])

    def test_missing_axis_is_incomparable_and_never_hidden(self):
        best = _dominance_card(annualized_yield=0.30, cushion=0.15)
        incomparable = _dominance_card(annualized_yield=0.20, cushion=None)
        third = _dominance_card(annualized_yield=0.10, cushion=0.05)
        shown, hidden = ad.dominated_partition([best, incomparable, third], "put", 100.0)
        self.assertIn(incomparable, shown)
        self.assertNotIn(incomparable, [card for card, _ in hidden])

    def test_liquidity_red_and_blocked_cards_are_never_hidden(self):
        best = _dominance_card(annualized_yield=0.30, cushion=0.15)
        liquidity_red = _dominance_card(
            annualized_yield=0.20, cushion=0.10,
            grades={"liquidity": "RED", "portfolio": "RED"})
        blocked = _dominance_card(annualized_yield=0.10, cushion=0.05)
        blocked["top3_snapshot"] = {"selection_status": "DATA_BLOCKED"}
        shown, hidden = ad.dominated_partition(
            [best, liquidity_red, blocked], "put", 100.0)
        self.assertEqual(shown, [best, liquidity_red, blocked])
        self.assertEqual(hidden, [])

    def test_portfolio_red_only_card_is_hideable(self):
        best = _dominance_card(annualized_yield=0.30, cushion=0.15)
        worse = _dominance_card(annualized_yield=0.20, cushion=0.10,
                                grades={"liquidity": "GREEN", "portfolio": "RED"})
        third = _dominance_card(annualized_yield=0.10, cushion=0.05)
        _shown, hidden = ad.dominated_partition([best, worse, third], "put", 100.0)
        self.assertIn(worse, [card for card, _ in hidden])

    def test_two_card_and_pmcc_lanes_are_exempt(self):
        best = _dominance_card(annualized_yield=0.30, cushion=0.15)
        worse = _dominance_card(annualized_yield=0.20, cushion=0.10)
        third = _dominance_card(annualized_yield=0.10, cushion=0.05)
        self.assertEqual(ad.dominated_partition([best, worse], "put", 100.0),
                         ([best, worse], []))
        self.assertEqual(ad.dominated_partition([best, worse, third], "pmcc", 100.0),
                         ([best, worse, third], []))

    def test_hidden_cards_have_a_shown_front_dominator(self):
        front = _dominance_card(annualized_yield=0.40, cushion=0.20)
        middle = _dominance_card(annualized_yield=0.30, cushion=0.15)
        low = _dominance_card(annualized_yield=0.20, cushion=0.10)
        shown, hidden = ad.dominated_partition([front, middle, low], "put", 100.0)
        self.assertEqual(shown, [front])
        self.assertEqual(hidden, [(middle, front), (low, front)])

    def test_group_render_keeps_liquidity_warning_outside_hidden_details(self):
        def renderable(card, headline):
            card.update({"headline": headline, "strike": 95.0,
                         "expiry": "2026-08-21", "dte": 45, "risk": {},
                         "scenarios": [], "bbb": [], "verdict": "display only"})
            return card
        best = renderable(_dominance_card(annualized_yield=0.30, cushion=0.15),
                          "best shown")
        warning = renderable(_dominance_card(
            annualized_yield=0.20, cushion=0.10,
            grades={"liquidity": "RED", "portfolio": "RED"}),
            "liquidity warning shown")
        hideable = renderable(_dominance_card(
            annualized_yield=0.10, cushion=0.05,
            grades={"liquidity": "GREEN", "portfolio": "RED"}),
            "portfolio-only hidden")
        html = ad._group_html({"kind": "put", "title": "PUT",
                               "cards": [best, warning, hideable]},
                              rank=1, close=100.0)
        hidden_start = html.index('<details class="dominated-candidates">')
        self.assertLess(html.index("liquidity warning shown"), hidden_start)
        self.assertGreater(html.index("portfolio-only hidden"), hidden_start)

    def test_group_dom_records_each_candidate_identity_once(self):
        def renderable(card, ident, headline):
            card.update({"headline": headline, "strike": 95.0,
                         "expiry": "2026-08-21", "dte": 45, "risk": {},
                         "scenarios": [], "bbb": [], "verdict": "display only"})
            card["top3_snapshot"]["candidate_id"] = ident
            return card

        best = renderable(
            _dominance_card(annualized_yield=0.30, cushion=0.15),
            "AAA:put:best", "best shown")
        hidden = renderable(
            _dominance_card(annualized_yield=0.20, cushion=0.10),
            "AAA:put:hidden", "hidden but retained")
        tradeoff = renderable(
            _dominance_card(annualized_yield=0.40, cushion=0.05),
            "AAA:put:tradeoff", "tradeoff shown")

        html = ad._group_html(
            {"kind": "put", "title": "PUT", "cards": [best, hidden, tradeoff]},
            rank=1, close=100.0)

        for ident in ("AAA:put:best", "AAA:put:hidden", "AAA:put:tradeoff"):
            self.assertEqual(html.count(f'data-candidate-id="{ident}"'), 1)


class SymbolPanelStatusTests(unittest.TestCase):
    def test_fail_visible_labels_open_panel(self):
        blocked = _dominance_card()
        blocked["top3_snapshot"] = {"selection_status": "DATA_BLOCKED"}
        section = {"symbol": "AAA", "features_stale": True,
                   "groups": [{"cards": [blocked, {"skipped": "no quote"}]}]}
        self.assertEqual(ad._panel_status(section, {"AAA"}),
                         (["DATA_BLOCKED", "STALE", "SKIPPED"], True))

    def test_liquidity_warning_only_panel_is_collapsed(self):
        card = _dominance_card(grades={"liquidity": "RED"})
        section = {"symbol": "AAA", "groups": [{"cards": [card]}]}
        self.assertEqual(ad._panel_status(section, set()),
                         (["LIQUIDITY WARNING"], False))

    def test_clean_panel_is_current_and_collapsed(self):
        section = {"symbol": "AAA", "groups": [{"cards": [_dominance_card()]}]}
        self.assertEqual(ad._panel_status(section, set()), (["CURRENT"], False))

    def test_render_uses_details_and_fail_visible_open_attribute(self):
        section = _v2_section()
        section["symbol"] = "AMZN"
        data = ad.assemble(symbol_sections=[section],
                           rv21_by_symbol={"AMZN": math.sqrt(12) * 0.11})
        data["stale_symbols"] = []
        data["symbols"][0]["features_stale"] = False
        data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"].update(
            {"rank_eligible": True, "selection_status": "ELIGIBLE"})
        clean_html = ad.render(data)
        self.assertIn('<details class="panel symbol-panel">', clean_html)
        self.assertNotIn('<details class="panel symbol-panel" open>', clean_html)
        data["symbols"][0]["features_stale"] = True
        self.assertIn('<details class="panel symbol-panel" open>', ad.render(data))


class RegimeStripTests(unittest.TestCase):
    def _status(self, root: Path, *, evaluation_date="2026-08-26",
                max_asof="2026-08-25"):
        sidecar = {
            "schema": "regime_report/v1",
            "as_of_written": "2026-08-26T12:00:00.000000Z",
            "evaluation_date": evaluation_date,
            "symbols": {symbol: {"label": index,
                                  "high_dispersion": bool(index % 2),
                                  "max_asof": max_asof,
                                  "skipped_reason": None}
                        for index, symbol in enumerate(config.REGIME_SYMBOLS)},
        }
        path = root / "wasserstein-regime.json"
        path.write_text(json.dumps(sidecar, sort_keys=True,
                                   separators=(",", ":")) + "\n")
        return {"state": "published", "generation_id":
                "20260826T120000000000Z-0123456789abcdef0123456789abcdef",
                "artifacts": {"wasserstein-regime.json": path}}

    def test_regime_strip_renders_valid_sidecar_and_shared_disclaimer(self):
        with tempfile.TemporaryDirectory() as tmp:
            html = ad._regime_strip_html(self._status(Path(tmp)), "2026-08-26")
        self.assertIn("REGIME (descriptive)", html)
        for symbol in config.REGIME_SYMBOLS:
            self.assertIn(symbol, html)
        self.assertIn("not a registered signal", html)
        self.assertNotIn("regime view unpublished/stale", html)

    def test_absent_or_future_sidecar_is_loud(self):
        self.assertIn("regime view unpublished/stale — see Experiments shelf",
                      ad._regime_strip_html({"state": "absent"}, "2026-08-26"))
        with tempfile.TemporaryDirectory() as tmp:
            status = self._status(Path(tmp), evaluation_date="2026-08-27",
                                  max_asof="2026-08-27")
            html = ad._regime_strip_html(status, "2026-08-26")
        self.assertIn("regime view unpublished/stale — see Experiments shelf", html)


class SelectQmTopPicksTests(unittest.TestCase):
    @staticmethod
    def _context(*, as_of="2026-07-01", breakout=True, parabolic=False, status="CURRENT"):
        return {
            "as_of": as_of,
            "status": status,
            "symbols": {
                "AAA": {
                    "status": status,
                    "breakout_fire": breakout,
                    "parabolic_fire": parabolic,
                    "ma_supports_bullish": True,
                },
                "BBB": {
                    "status": status,
                    "breakout_fire": False,
                    "parabolic_fire": False,
                    "ma_supports_bullish": False,
                },
            },
        }

    def test_an_uncovered_pick_keeps_its_slot_instead_of_blanking_the_panel(self):
        # brief 12 D5 gate 5: a mechanical pick the frozen study never covered
        # is a permanent fact about that name. Dropping every slot over it hid
        # the covered names' context forever; QM still selects nothing.
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        context = self._context()
        context["symbols"]["BBB"] = {
            "status": "NOT_IN_FROZEN_STUDY",
            "reason": "BBB is not in the frozen QM study sidecar",
        }
        context["not_covered"] = ["BBB"]

        mechanical = [(p["symbol"], p["lane"], p["strike"])
                      for p in ad.select_top_picks(data, include_csp_watch=True)]
        picks = ad.select_qm_top_picks(data, context, include_csp_watch=True)
        self.assertEqual([(p["symbol"], p["lane"], p["strike"]) for p in picks],
                         mechanical)
        self.assertIn("BBB", {p["symbol"] for p in picks})

        card_html = ad._qm_card_context_html(
            picks[-1], context["symbols"]["BBB"])
        self.assertIn("QM NOT COVERED", card_html)
        self.assertIn("not in the frozen QM study", card_html)
        self.assertNotIn("QM DATA BLOCKED", card_html)

    def test_qm_context_uses_exact_mechanical_picks_without_changing_selector(self):
        import json
        from pathlib import Path

        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        baseline = (
            (Path(__file__).parent / "fixtures" / "top3_fixed_baseline_d5c241a.json")
            .read_bytes()
            .rstrip(b"\n")
        )

        plain_output_before = ad.select_top_picks(data)
        plain_bytes_before = json.dumps(
            plain_output_before, sort_keys=True, separators=(",", ":")
        ).encode()
        plain_before = [
            (p["symbol"], p["lane"], p["strike"], p["expiry"]) for p in plain_output_before
        ]
        qm = ad.select_qm_top_picks(data, self._context())
        plain_output_after = ad.select_top_picks(data)
        plain_bytes_after = json.dumps(
            plain_output_after, sort_keys=True, separators=(",", ":")
        ).encode()
        plain_after = [
            (p["symbol"], p["lane"], p["strike"], p["expiry"]) for p in plain_output_after
        ]

        self.assertEqual(
            plain_before,
            [("AAA", "put", 95.0, "2026-08-21"), ("BBB", "put", 44.0, "2026-08-21")],
        )
        self.assertEqual(plain_after, plain_before)
        self.assertEqual(plain_bytes_before, baseline)
        self.assertEqual(plain_bytes_after, plain_bytes_before)
        self.assertEqual(
            [(p["symbol"], p["lane"], p["strike"], p["expiry"]) for p in qm],
            plain_before,
        )

    def test_stale_top_level_context_blocks_the_qm_list(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        self.assertEqual(
            ad.select_qm_top_picks(data, self._context(as_of="2026-06-30", status="STALE")),
            [],
        )

    def test_qm_cannot_admit_liquidity_red_card(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        picks = ad.select_qm_top_picks(data, self._context())
        self.assertNotIn(("BBB", 45.0), [(p["symbol"], p["strike"]) for p in picks])

    def test_qm_cannot_admit_a_policy_rejected_card(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        data["symbols"] = [data["symbols"][0]]
        data["symbols"][0]["groups"] = [data["symbols"][0]["groups"][1]]
        rejected = data["symbols"][0]["groups"][0]["cards"][0]
        rejected["top3_snapshot"] = {
            "rank_eligible": False,
            "selection_status": "PLAN_ONLY",
            "policy": {"reason_codes": ["NOT_REGISTERED"]},
        }

        self.assertEqual(ad.select_qm_top_picks(data, self._context()), [])

    def test_candidate_evidence_is_materialized_in_the_qm_context(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        context = ad.enrich_qm_context_with_candidates(data, self._context())
        self.assertIsInstance(context, dict)
        picks = ad.select_qm_top_picks(data, context)
        key = ad._qm_candidate_key(picks[0])
        evidence = context["symbols"]["AAA"]["option_candidates"][key]
        self.assertEqual(evidence["candidate_id"], key)
        self.assertIn("underlying_breakeven_frequency", evidence)
        self.assertFalse(evidence["underlying_breakeven_frequency"]["available"])
        self.assertIn(
            "not tested by QM",
            evidence["underlying_breakeven_frequency"]["label"],
        )
        self.assertIsNone(evidence["underlying_breakeven_frequency"]["option_win_rate"])

    def test_qm_signals_cannot_reorder_the_mechanical_context_cards(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        signal_on = self._context(breakout=True)
        signal_off = self._context(breakout=False)
        signal_off["symbols"]["AAA"]["ma_supports_bullish"] = False
        signal_off["symbols"]["BBB"]["ma_supports_bullish"] = True

        mechanical = [
            (pick["symbol"], pick["lane"], pick["strike"], pick["expiry"])
            for pick in ad.select_top_picks(data)
        ]
        for context in (signal_on, signal_off):
            self.assertEqual(
                [
                    (pick["symbol"], pick["lane"], pick["strike"], pick["expiry"])
                    for pick in ad.select_qm_top_picks(data, context)
                ],
                mechanical,
            )

    def test_parabolic_never_changes_mechanical_context_card_order(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        base = self._context(breakout=False, parabolic=False)
        warning = self._context(breakout=False, parabolic=True)
        without = [
            (p["symbol"], p["lane"], p["strike"]) for p in ad.select_qm_top_picks(data, base)
        ]
        with_warning = [
            (p["symbol"], p["lane"], p["strike"]) for p in ad.select_qm_top_picks(data, warning)
        ]
        self.assertEqual(with_warning, without)

    def test_missing_one_symbol_context_blocks_the_whole_qm_list(self):
        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        context = self._context()
        del context["symbols"]["AAA"]
        picks = ad.select_qm_top_picks(data, context)
        self.assertEqual(picks, [])

    def test_perfect_display_extra_cannot_block_or_change_qm_picks(self):
        import copy

        data = SelectTopPicksTests()._data()
        data["data_as_of"] = "2026-07-01"
        context = self._context()
        expected = [
            (pick["symbol"], pick["lane"], pick["strike"])
            for pick in ad.select_qm_top_picks(data, context)
        ]
        extra = copy.deepcopy(data["symbols"][0])
        extra["symbol"] = "NBIS"
        extra["display_only"] = True
        for group in extra["groups"]:
            for card in group["cards"]:
                card["grades"] = {
                    "fits_cap": "GREEN",
                    "yield": "GREEN",
                    "liquidity": "GREEN",
                }
                card["rank_leader"] = True
                card["breakeven_move"] = 0.0
                card["annualized_yield"] = 99.0
        data["symbols"].insert(0, extra)

        enriched = ad.enrich_qm_context_with_candidates(data, context)
        self.assertNotIn("NBIS", enriched["symbols"])
        actual = [
            (pick["symbol"], pick["lane"], pick["strike"])
            for pick in ad.select_qm_top_picks(data, enriched)
        ]
        self.assertEqual(actual, expected)
        self.assertNotIn("NBIS", {symbol for symbol, _, _ in actual})


class StrategySectionRankingTests(unittest.TestCase):
    @staticmethod
    def _group(title, kind, cards):
        return {"title": title, "kind": kind, "cards": cards, "empty": None}

    @staticmethod
    def _card(*, grades, annualized_yield=0.20, rank_leader=False,
              policy="ELIGIBLE"):
        return {
            "strike": 95.0,
            "expiry": "2026-08-21",
            "dte": 45,
            "credit": 100.0,
            "grades": grades,
            "annualized_yield": annualized_yield,
            "rank_leader": rank_leader,
            "top3_snapshot": {
                "rank_eligible": policy == "ELIGIBLE",
                "policy": {"status": policy},
                "selection_status": policy,
            },
        }

    def test_sections_sort_by_best_card_then_policy_and_liquidity(self):
        groups = [
            self._group("plan", "pmcc", [self._card(
                grades={"liquidity": "GREEN", "yield": "GREEN"},
                policy="PLAN_ONLY")]),
            self._group("low eligible", "put", [self._card(
                grades={"liquidity": "GREEN"})]),
            self._group("empty", "cc", []),
            self._group("high eligible", "put", [self._card(
                grades={"liquidity": "GREEN", "yield": "GREEN"},
                rank_leader=True)]),
            self._group("illiquid", "put", [self._card(
                grades={"liquidity": "RED", "yield": "GREEN"},
                rank_leader=True)]),
            self._group("watch", "put", [self._card(
                grades={"liquidity": "GREEN", "yield": "GREEN"},
                rank_leader=True, policy="WATCH")]),
        ]

        ordered = ad._rank_groups_for_display(groups)

        self.assertEqual(
            [group["title"] for group in ordered],
            ["high eligible", "low eligible", "watch", "plan", "illiquid",
             "empty"],
        )

    def test_selection_status_outranks_policy_status(self):
        # A card whose FEATURES are stale has selection_status=DATA_BLOCKED
        # even when its portfolio policy passes; the merged selection_status
        # is authoritative and the card must never sort as eligible.
        stale = self._card(grades={"liquidity": "GREEN", "yield": "GREEN"})
        stale["top3_snapshot"] = {
            "rank_eligible": False,
            "policy": {"status": "ELIGIBLE"},
            "selection_status": "DATA_BLOCKED",
        }
        self.assertEqual(ad._display_policy_tier(stale), 3)
        eligible = self._card(grades={"liquidity": "GREEN"})
        self.assertLess(ad._display_policy_tier(eligible),
                        ad._display_policy_tier(stale))

    def test_missing_or_malformed_snapshot_never_best_tier(self):
        no_snapshot = self._card(grades={"liquidity": "GREEN"})
        del no_snapshot["top3_snapshot"]
        self.assertEqual(ad._display_policy_tier(no_snapshot), 3)
        malformed = self._card(grades={"liquidity": "GREEN"})
        malformed["top3_snapshot"] = {"rank_eligible": False,
                                      "policy": "not-a-mapping"}
        self.assertEqual(ad._display_policy_tier(malformed), 3)

    def test_watch_selection_status_is_watch_tier(self):
        card = self._card(grades={"liquidity": "GREEN"}, policy="WATCH")
        self.assertEqual(ad._display_policy_tier(card), 1)

    def test_green_fraction_orders_lanes_within_symbol(self):
        # Same cross-lane comparability rule as the hero: 3/3 GREEN buyer
        # section outranks a 5/7 GREEN seller section.
        seller = self._card(grades={"yield": "GREEN", "cushion": "GREEN",
                                    "iv_for_seller": "GREEN",
                                    "vrp_for_seller": "GREEN",
                                    "liquidity": "GREEN",
                                    "earnings": "AMBER", "fomc": "AMBER"})
        buyer = self._card(grades={"fits_cap": "GREEN",
                                   "iv_for_buyer": "GREEN",
                                   "liquidity": "GREEN"})
        groups = [self._group("seller", "put", [seller]),
                  self._group("buyer", "long_call", [buyer])]
        ordered = ad._rank_groups_for_display(groups)
        self.assertEqual([g["title"] for g in ordered], ["buyer", "seller"])

    def test_render_numbers_and_orders_strategy_sections(self):
        section = {
            "symbol": "AAA", "as_of": "2026-07-15", "close": 100.0,
            "iv_rank": 0.5,
            "groups": [
                self._group("lower", "put", [self._card(
                    grades={"liquidity": "GREEN"})]),
                self._group("higher", "put", [self._card(
                    grades={"liquidity": "GREEN", "yield": "GREEN"},
                    rank_leader=True)]),
            ],
        }
        assembled = ad.assemble(symbol_sections=[section],
                                rv21_by_symbol={"AAA": 0.4})

        html = ad.render(assembled)

        self.assertLess(html.index("higher"), html.index("lower"))
        self.assertIn('class="group-rank" aria-label="Rank 1">1</span>', html)
        self.assertIn('class="group-rank" aria-label="Rank 2">2</span>', html)
        self.assertIn("Strategy rank: 1 is the strongest current fit", html)


class PinnedPicksTests(unittest.TestCase):
    def _data(self):
        return {"symbols": [
            {"symbol": "AAA", "close": 100.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "put", "title": "P", "empty": None,
                         "cards": [_pick_card(
                             95.0, "2026-08-21",
                             grades={"yield": "GREEN", "liquidity": "GREEN"},
                             lane_fields={"credit": 200.0,
                                          "annualized_yield": 0.30})]}]},
            {"symbol": "BBB", "close": 50.0, "iv_rank": 0.5,
             "as_of": "2026-07-01",
             "groups": [{"kind": "put", "title": "P", "empty": None,
                         "cards": [_pick_card(
                             45.0, "2026-08-21",
                             grades={"yield": "GREEN", "liquidity": "RED"},
                             lane_fields={"credit": 100.0,
                                          "annualized_yield": 0.90})]}]},
        ]}

    def test_pinned_symbol_surfaces_best_admissible_card(self):
        from unittest import mock

        import config
        with mock.patch.object(config, "PICK_PINNED_SYMBOLS",
                               ["AAA"], create=True):
            pinned = ad.pinned_picks(self._data())
        self.assertEqual(len(pinned), 1)
        self.assertEqual(pinned[0]["symbol"], "AAA")
        self.assertEqual(pinned[0]["pick"]["strike"], 95.0)

    def test_pinned_symbol_with_no_admissible_card_is_honest_gap(self):
        from unittest import mock

        import config
        # BBB's only card is liquidity-RED (hard veto); ZZZ has no section.
        with mock.patch.object(config, "PICK_PINNED_SYMBOLS",
                               ["BBB", "ZZZ"], create=True):
            pinned = ad.pinned_picks(self._data())
        self.assertEqual([p["symbol"] for p in pinned], ["BBB", "ZZZ"])
        self.assertIsNone(pinned[0]["pick"])
        self.assertIsNone(pinned[1]["pick"])

    def test_render_pinned_strip_labeled_not_ranked(self):
        from unittest import mock

        import config
        data = ad.assemble(symbol_sections=self._data()["symbols"],
                           rv21_by_symbol={"AAA": 0.4, "BBB": 0.4})
        with mock.patch.object(config, "PICK_PINNED_SYMBOLS",
                               ["AAA", "ZZZ"], create=True):
            html = ad.render(data)
        self.assertIn("owner-pinned visibility", html)
        self.assertIn("not ranked", html)
        self.assertIn("ZZZ", html)  # gap is shown, never fabricated
        self.assertIn("no eligible liquid card", html)


class BlockedSectionsTests(unittest.TestCase):
    _BLOCKED = [
        {"symbol": "CRWV", "reason_code": "FEATURES_MISSING",
         "detail": "no feature frame", "last_known_date": "2026-07-15",
         "unexpected": False},
        {"symbol": "USAR", "reason_code": "UNEXPECTED_ERROR",
         "detail": "KeyError: 'iv'", "last_known_date": None,
         "unexpected": True},
    ]

    def test_assemble_carries_blocked_records(self):
        data = ad.assemble(symbol_sections=[], rv21_by_symbol={},
                           blocked=self._BLOCKED)
        self.assertEqual(data["blocked"], self._BLOCKED)
        default = ad.assemble(symbol_sections=[], rv21_by_symbol={})
        self.assertEqual(default["blocked"], [])

    def test_render_shows_blocked_strip(self):
        data = ad.assemble(symbol_sections=[], rv21_by_symbol={},
                           blocked=self._BLOCKED)
        html = ad.render(data)
        self.assertIn("CRWV", html)
        self.assertIn("FEATURES_MISSING", html)
        self.assertIn("2026-07-15", html)
        self.assertIn("USAR", html)
        self.assertIn("UNEXPECTED_ERROR", html)

    def test_no_blocked_no_strip(self):
        data = ad.assemble(symbol_sections=[], rv21_by_symbol={})
        # The assembly-level blocked-symbol strip is absent. The independent
        # QM list may still show its required fail-closed DATA BLOCKED slots.
        self.assertNotIn('<div class="eyebrow">DATA BLOCKED</div>', ad.render(data))

    def test_exit_code_nonzero_only_for_unexpected(self):
        self.assertEqual(ad._run_exit_code([]), 0)
        self.assertEqual(ad._run_exit_code([self._BLOCKED[0]]), 0)
        self.assertEqual(ad._run_exit_code(self._BLOCKED), 1)

    def test_display_only_chip_is_pinned_on_success_and_blocked_rows(self):
        section = {
            "symbol": "AMAT",
            "as_of": "2026-07-24",
            "close": 200.0,
            "iv_rank": 0.5,
            "groups": [{
                "kind": "put",
                "title": "SELL A PUT?",
                "cards": [],
                "empty": "none this cycle",
            }],
        }
        blocked = [{
            "symbol": "CLSK",
            "reason_code": "NO_CACHED_CHAINS",
            "detail": "no chain parquet",
            "last_known_date": None,
            "unexpected": False,
        }]
        data = ad.assemble(
            symbol_sections=[section],
            rv21_by_symbol={},
            blocked=blocked,
        )

        self.assertTrue(data["symbols"][0]["display_only"])
        self.assertTrue(data["blocked"][0]["display_only"])
        html = ad.render(data)
        self.assertEqual(html.count(ad.DISPLAY_ONLY_LABEL), 2)


class HypothesisEvidencePanelTests(unittest.TestCase):
    def test_panel_escapes_all_values_and_keeps_intraday_separate(self):
        data = ad.assemble(
            symbol_sections=[_v2_section()],
            rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11},
            hypothesis_evidence_by_symbol={"MSFT": _evidence("MSFT")},
        )

        html = ad.render(data)

        self.assertIn('<details class="hypothesis-evidence">', html)
        self.assertIn("Hypothesis evidence", html)
        self.assertIn("Intraday context — descriptive only", html)
        self.assertIn("H5&lt;script&gt;", html)
        self.assertIn("tracked &lt;owner&gt;", html)
        self.assertIn("entry&lt;label&gt;", html)
        self.assertIn("WAIT &amp; WATCH", html)
        self.assertIn("reports/h5/&lt;unsafe&gt;.txt", html)
        self.assertNotIn("<script>", html)

    def test_evidence_is_inside_a_blocked_symbol_row(self):
        data = ad.assemble(
            symbol_sections=[],
            rv21_by_symbol={},
            blocked=[{
                "symbol": "CLSK",
                "reason_code": "NO_CACHED_CHAINS",
                "detail": "no chain parquet",
                "last_known_date": None,
                "unexpected": False,
            }],
            hypothesis_evidence_by_symbol={"CLSK": _evidence("CLSK")},
        )

        html = ad.render(data)
        blocked_start = html.index('<div class="eyebrow">DATA BLOCKED</div>')
        evidence_start = html.index(
            '<details class="hypothesis-evidence">', blocked_start
        )
        blocked_end = html.index("</section>", blocked_start)
        self.assertLess(evidence_start, blocked_end)

    def test_evidence_cannot_change_top3_order_or_card_grades(self):
        import json

        baseline = ad.assemble(
            symbol_sections=[_v2_section()],
            rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11},
        )
        evidenced = ad.assemble(
            symbol_sections=[_v2_section()],
            rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11},
            hypothesis_evidence_by_symbol={"MSFT": _evidence("MSFT")},
        )

        baseline_bytes = json.dumps(
            ad.select_top_picks(baseline),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        evidenced_bytes = json.dumps(
            ad.select_top_picks(evidenced),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self.assertEqual(evidenced_bytes, baseline_bytes)
        self.assertEqual(
            [section["symbol"] for section in evidenced["symbols"]],
            [section["symbol"] for section in baseline["symbols"]],
        )
        baseline_card = baseline["symbols"][0]["groups"][0]["cards"][0]
        evidenced_card = evidenced["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(evidenced_card["grades"], baseline_card["grades"])
        self.assertNotIn("hypothesis_evidence", evidenced_card)


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
            self.assertEqual(warn, "company-research annotations are from "
                                   "2026-07-10 (stale vs data as-of "
                                   "2026-07-15; QM status has its own "
                                   "exact-date check)")

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

    def test_evidence_loader_hashes_the_same_single_byte_snapshot_it_parses(self):
        import hashlib
        import tempfile
        from pathlib import Path
        from unittest import mock

        raw = b'{"as_of":"2026-07-15","annotations":{}}\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-07-15.json"
            path.write_bytes(raw)
            with mock.patch.object(Path, "read_bytes", return_value=raw) as read:
                evidence = ad.load_context_evidence("2026-07-15", base_dir=tmp)

        self.assertEqual(read.call_count, 1)
        self.assertEqual(evidence["context"]["as_of"], "2026-07-15")
        self.assertEqual(evidence["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(evidence["source_path"], str(path.resolve()))

    def test_evidence_hash_drift_fails_closed_without_reparsing_new_bytes(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-07-15.json"
            path.write_text('{"as_of":"2026-07-15","annotations":{}}\n')
            evidence = ad.load_context_evidence("2026-07-15", base_dir=tmp)
            path.write_text('{"as_of":"2026-07-14","annotations":{}}\n')

            verified = ad._verify_context_evidence(evidence)

        self.assertEqual(verified["state"], "integrity_failed")
        self.assertIsNone(verified["context"])
        self.assertIn("hash drift", verified["warning"])

    def test_evidence_loader_rejects_a_dated_symlink_outside_context_root(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "context"
            root.mkdir()
            outside = Path(tmp) / "outside.json"
            outside.write_text('{"as_of":"2026-07-15","annotations":{}}\n')
            (root / "2026-07-15.json").symlink_to(outside)

            evidence = ad.load_context_evidence("2026-07-15", base_dir=str(root))

        self.assertEqual(evidence["state"], "integrity_failed")
        self.assertIsNone(evidence["context"])
        self.assertIn("escapes context root", evidence["warning"])

    def test_evidence_loader_classifies_a_symlink_loop_as_integrity_failed(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "context"
            root.mkdir()
            loop = root / "2026-07-15.json"
            loop.symlink_to(loop.name)

            evidence = ad.load_context_evidence("2026-07-15", base_dir=str(root))

        self.assertEqual(evidence["state"], "integrity_failed")
        self.assertIsNone(evidence["context"])
        self.assertIn("unreadable", evidence["warning"])

    def test_rendered_context_freshness_has_all_evidence_derived_states(self):
        data = {
            "symbols": [], "blocked": [], "data_as_of": "2026-07-15",
            "evaluation_date": "2026-08-26", "composite_signals": [],
            "family_evidence": [],
            "underlying_closes_freshness": {
                "state": "unavailable", "detail": "fixture"},
        }

        def chip(context, evidence):
            html = ad.render(data, context=context, context_evidence=evidence)
            start = html.index("Research context")
            return html[start:html.index("</span>", start)]

        exact = {"as_of": "2026-07-15", "annotations": {}}
        stale = {"as_of": "2026-07-14", "annotations": {}}
        loaded = {"state": "loaded", "source_path": "/fixture/context.json",
                  "sha256": "a" * 64}
        self.assertIn(
            "Research context EXACT — context as of 2026-07-15; board as of 2026-07-15.",
            chip(exact, {**loaded, "context": exact}),
        )
        self.assertIn(
            "Research context STALE — context as of 2026-07-14; board as of 2026-07-15.",
            chip(stale, {**loaded, "context": stale}),
        )
        self.assertIn(
            "Research context UNAVAILABLE — context as of unavailable; board as of 2026-07-15.",
            chip(None, {"state": "unavailable", "context": None}),
        )
        self.assertIn(
            "Research context INTEGRITY_FAILED — context as of unavailable; board as of 2026-07-15.",
            chip(None, {"state": "integrity_failed", "context": None}),
        )
        future = {"as_of": "2026-07-16", "annotations": {}}
        self.assertIn("Research context INTEGRITY_FAILED", chip(
            future, {**loaded, "context": future}))
        invalid_annotations = {"as_of": "2026-07-15", "annotations": []}
        self.assertIn("Research context INTEGRITY_FAILED", chip(
            invalid_annotations, {**loaded, "context": invalid_annotations}))

    def test_mutable_refresh_files_cannot_change_injected_context_chip(self):
        import tempfile
        from pathlib import Path

        data = {
            "symbols": [], "blocked": [], "data_as_of": "2026-07-15",
            "evaluation_date": "2026-08-26", "composite_signals": [],
            "family_evidence": [],
            "underlying_closes_freshness": {
                "state": "unavailable", "detail": "fixture"},
        }
        context = {"as_of": "2026-07-15", "annotations": {}}
        evidence = {"state": "loaded", "context": context,
                    "source_path": "/fixture/context.json", "sha256": "a" * 64}
        with tempfile.TemporaryDirectory() as tmp:
            files = [Path(tmp) / name for name in (
                "guard.json", "refresh.log", "final-manifest.json")]
            for path in files:
                path.write_text("before")
            before = ad.render(data, context=context, context_evidence=evidence)
            for path in files:
                path.write_text("after")
            after = ad.render(data, context=context, context_evidence=evidence)

        self.assertEqual(before, after)


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


def _valid_annotation():
    """One schema-valid advisory annotation (top3_context contract)."""
    return {
        "research_as_of_utc": "2026-06-30T12:00:00Z",
        "market_as_of_date": "2026-06-30",
        "claims": [{
            "id": "issuer-event",
            "text": "Issuer event is scheduled.",
            "classification": "fact",
            "source_url": "https://example.com/issuer-event",
            "unknown_rationale": None,
            "source_tier": "issuer_ir",
            "fact_date": "2026-06-30",
            "date_certainty": "confirmed",
            "countercase": "The event may not move the stock.",
        }],
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
        self.assertIn("TOP 5 PICKS TODAY", html)
        self.assertIn("Legacy agent-selected top_picks were ignored", html)
        self.assertNotIn("IV elevated vs realized", html)
        self.assertNotIn("cushion exceeds monthly move", html)
        self.assertNotIn("Python quantitative shortlist differs", html)

    def test_hero_unmatched_pick_warns_and_discloses_disagreement(self):
        html = ad.render(self._assembled(), context=_v2_context(strike=999.0))
        self.assertIn("Legacy agent-selected top_picks were ignored", html)
        self.assertNotIn("unmatched to current candidates", html)
        self.assertNotIn("Python quantitative shortlist differs", html)

    def test_stale_annotation_does_not_hide_matching_current_annotation(self):
        candidate_id = "MSFT:put:2026-07-17:350.00"
        annotation = _valid_annotation()
        context = _v2_context()
        context["annotations"] = {
            candidate_id: annotation,
            "MSFT:put:2026-07-17:999.00": annotation,
        }

        annotations, warning = ad._research_annotation_map(
            [{"card": {"top3_snapshot": {"candidate_id": candidate_id}}}],
            context,
        )
        html = ad._research_html(
            annotations[candidate_id], data_as_of="2026-06-30"
        )

        # The rotated-off card no longer nukes the whole set...
        self.assertIn("Research evidence · complete", html)
        # ...but its key is still REPORTED, never silently swallowed.
        self.assertIsNotNone(warning)
        self.assertIn("MSFT:put:2026-07-17:999.00", warning)

    def test_annotation_for_current_candidate_only_gives_no_notice(self):
        candidate_id = "MSFT:put:2026-07-17:350.00"
        context = _v2_context()
        context["annotations"] = {candidate_id: _valid_annotation()}
        annotations, warning = ad._research_annotation_map(
            [{"card": {"top3_snapshot": {"candidate_id": candidate_id}}}],
            context,
        )
        self.assertIn(candidate_id, annotations)
        self.assertIsNone(warning)

    def test_malformed_annotation_for_current_candidate_still_warns(self):
        # The pre-filter must not swallow a genuinely malformed annotation
        # that belongs to a card actually on the board.
        candidate_id = "MSFT:put:2026-07-17:350.00"
        bad = dict(_valid_annotation())
        bad["claims"] = "not-a-list"
        context = _v2_context()
        context["annotations"] = {candidate_id: bad}
        annotations, warning = ad._research_annotation_map(
            [{"card": {"top3_snapshot": {"candidate_id": candidate_id}}}],
            context,
        )
        self.assertEqual(annotations, {})
        self.assertIsNotNone(warning)
        self.assertIn("research annotations invalid", warning)

    def test_mistyped_candidate_key_is_reported_not_silent(self):
        # A near-miss key (wrong strike) intended for a current card would
        # otherwise vanish with no signal at all.
        candidate_id = "MSFT:put:2026-07-17:350.00"
        context = _v2_context()
        context["annotations"] = {"MSFT:put:2026-07-17:350.0": _valid_annotation()}
        annotations, warning = ad._research_annotation_map(
            [{"card": {"top3_snapshot": {"candidate_id": candidate_id}}}],
            context,
        )
        self.assertEqual(annotations, {})
        self.assertIsNotNone(warning)
        self.assertIn("MSFT:put:2026-07-17:350.0", warning)

    def test_provenance_label_on_every_narrative_surface(self):
        html = ad.render(self._assembled(), context=_v2_context())
        prov = "LLM-asserted (test fixture, web research 2026-06-30)"
        # hero narrative, market strip, and symbol news all carry the tag
        self.assertGreaterEqual(html.count(ad._esc(prov)), 3)
        self.assertIn('class="prov"', html)

    def test_missing_context_renders_honest_quant_shortlist(self):
        html = ad.render(self._assembled())
        self.assertIn("TOP 5 PICKS TODAY", html)
        self.assertIn("No qualifying contract", html)
        # honesty: no narrative vocabulary invented
        self.assertNotIn("why now", html)

    def test_market_strip_present_with_context_absent_without(self):
        with_ctx = ad.render(self._assembled(), context=_v2_context())
        self.assertIn("Market context", with_ctx)
        self.assertIn("megacaps steady into month end", with_ctx)
        self.assertIn("Regime · mixed", with_ctx)
        without = ad.render(self._assembled())
        self.assertNotIn("Market context", without)

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

    @staticmethod
    def _qm_context(*, status="CURRENT", as_of="2026-06-30"):
        return {
            "as_of": as_of,
            "status": status,
            "reason": "OHLCV refresh incomplete" if status != "CURRENT" else "",
            "symbols": {
                "MSFT": {
                    "status": "CURRENT" if status == "CURRENT" else "STALE",
                    "signal_status": "BREAKOUT",
                    "breakout_fire": True,
                    "parabolic_fire": True,
                    "price": 373.02,
                    "sma20": 360.0,
                    "sma50": 350.0,
                    "sma200": 320.0,
                    "price_vs_sma20": 0.0362,
                    "price_vs_sma50": 0.0658,
                    "price_vs_sma200": 0.1657,
                    "ma_supports_bullish": True,
                    "historical_breakout_fires": 0,
                    "historical_parabolic_fires": 0,
                    "study": {"evidence_status": "DESCRIPTIVE_ONLY"},
                    "parabolic_study": {
                        "evidence_status": "FADE_REJECTED",
                        "decision": "The preregistered fade reading failed.",
                    },
                    "thesis": "A qualifying base can precede continuation.",
                    "counter_case": "Option P&L was not tested.",
                    "study_date": "2026-07-14",
                    "provenance": "Frozen report hash abc123.",
                }
            },
            "quant_want": {
                "trend": {
                    "status": "MARKET_BACKGROUND_ONLY",
                    "plain_language": "Broad trend is background only.",
                },
                "momentum": {"status": "DEFERRED", "plain_language": "Momentum is deferred."},
                "low_max": {"status": "DEFERRED", "plain_language": "Low-MAX is deferred."},
                "source_commit": "abc123",
            },
        }

    @staticmethod
    def _movement_context(*, statuses=("BREAKOUT",), uncovered=False):
        context = V2RenderTests._qm_context()
        context["movement_as_of"] = "2026-06-30"
        context["movement_symbols"] = {
            f"SYM{index}": {
                "status": "CURRENT",
                "signal_status": status,
                "breakout_fire": "BREAKOUT" in status,
                "parabolic_fire": "PARABOLIC WARNING" in status,
                "frozen_study_coverage": "NOT_COVERED" if uncovered else "COVERED",
                "frozen_study_reason": "SYM0 is not covered by the frozen study"
                if uncovered and index == 0 else "",
            }
            for index, status in enumerate(statuses)
        }
        return context

    def test_movement_lane_renders_current_fire_without_mechanical_card(self):
        html = ad.render(
            self._assembled(),
            qm_context=self._movement_context(statuses=("BREAKOUT + PARABOLIC WARNING",)),
        )

        movement_start = html.index("QM MOVEMENT LANE")
        movement_end = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        lane = html[movement_start:movement_end]
        self.assertIn("SYM0", lane)
        self.assertIn("BREAKOUT + PARABOLIC WARNING", lane)
        self.assertIn("DESCRIPTIVE ONLY — NOT A TRADE RANKING", lane)
        self.assertIn("UNVALIDATED SIGNAL -- descriptive screen; no forward evidence exists until the SS5 study reports; not an entry recommendation; no book path.", lane)

    def test_movement_lane_uncovered_card_omits_frozen_study_evidence(self):
        context = self._movement_context(statuses=("BREAKOUT",), uncovered=True)
        context["movement_symbols"]["SYM0"].update({
            "historical_breakout_fires": 99,
            "historical_parabolic_fires": 88,
            "thesis": "must not render",
            "counter_case": "must not render",
            "option_candidates": {"must-not": "render"},
        })
        html = ad.render(self._assembled(), qm_context=context)
        movement_start = html.index("QM MOVEMENT LANE")
        movement_end = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        lane = html[movement_start:movement_end]

        self.assertIn("not covered by the frozen study", lane)
        for forbidden in (
            "99", "88", "must not render", "Frozen study evidence", "breakeven", "candidate",
        ):
            self.assertNotIn(forbidden, lane)

    def test_movement_lane_no_fires_renders_exact_empty_state_without_placeholders(self):
        html = ad.render(
            self._assembled(),
            qm_context=self._movement_context(statuses=("NO FIRE", "NO FIRE")),
        )
        movement_start = html.index("QM MOVEMENT LANE")
        movement_end = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        lane = html[movement_start:movement_end]

        self.assertIn(
            "No movement fires today. Expected — these patterns fired ~46 times in nine years across twelve names.",
            lane,
        )
        self.assertNotIn('class="movement-card"', lane)

    def test_movement_lane_blocked_context_never_claims_no_fires(self):
        """A gate-blocked/no-data lane must render BLOCKED, not a no-fires observation."""
        context = self._qm_context()
        context["status"] = "DATA_BLOCKED"
        context["reason"] = "pre-registration gate refused"
        # No movement_symbols key at all — the shape load_qm_context returns when blocked.
        html = ad.render(self._assembled(), qm_context=context)
        movement_start = html.index("QM MOVEMENT LANE")
        movement_end = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        lane = html[movement_start:movement_end]

        self.assertIn("BLOCKED — movement state is unavailable this session", lane)
        self.assertIn("pre-registration gate refused", lane)
        self.assertNotIn("No movement fires today", lane)

        context_all_dead = self._movement_context(statuses=("BREAKOUT",))
        for item in context_all_dead["movement_symbols"].values():
            item["status"] = "DATA_BLOCKED"
        html = ad.render(self._assembled(), qm_context=context_all_dead)
        lane = html[html.index("QM MOVEMENT LANE"):html.index("QM + MOVING-AVERAGE CONTEXT")]
        self.assertIn("BLOCKED — movement state is unavailable this session", lane)
        self.assertNotIn("No movement fires today", lane)

    def test_movement_lane_discloses_partially_unavailable_names(self):
        context = self._movement_context(statuses=("NO FIRE", "NO FIRE"))
        context["movement_symbols"]["SYM1"] = {
            "status": "NO_DATA",
            "reason": "no cached adjusted OHLCV",
        }
        html = ad.render(self._assembled(), qm_context=context)
        lane = html[html.index("QM MOVEMENT LANE"):html.index("QM + MOVING-AVERAGE CONTEXT")]

        self.assertIn("No movement fires today", lane)
        self.assertIn("Not evaluated this session: SYM1 (NO_DATA).", lane)

    def test_movement_fires_leave_canonical_mechanical_selection_bytes_unchanged(self):
        import json

        data = self._assembled()
        baseline = json.dumps(
            ad.select_top_picks(data), sort_keys=True, separators=(",", ":")
        ).encode()
        for statuses in ((), ("BREAKOUT",), ("PARABOLIC WARNING",),
                         ("BREAKOUT + PARABOLIC WARNING",)):
            with self.subTest(statuses=statuses):
                ad.render(data, qm_context=self._movement_context(statuses=statuses))
                actual = json.dumps(
                    ad.select_top_picks(data), sort_keys=True, separators=(",", ":")
                ).encode()
                self.assertEqual(actual, baseline)

    def test_movement_lane_sits_between_mechanical_top_three_and_retained_comparison(self):
        html = ad.render(self._assembled(), qm_context=self._movement_context())
        self.assertLess(html.index("Rule-based top 5"), html.index("QM MOVEMENT LANE"))
        self.assertLess(
            html.index("QM MOVEMENT LANE"),
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
        )

    def test_configured_slots_render_as_two_lists_and_duplicate_is_allowed(self):
        section = _v2_section()
        section["symbol"] = "AMZN"  # registered CSP name; appears as WATCH
        data = ad.assemble(symbol_sections=[section], rv21_by_symbol={"AMZN": math.sqrt(12) * 0.11})
        snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        snapshot["selection_status"] = "ELIGIBLE"
        snapshot["rank_eligible"] = True
        snapshot["policy"] = {"status": "ELIGIBLE", "reason_codes": []}
        qm_context = self._qm_context()
        qm_context["symbols"]["AMZN"] = qm_context["symbols"].pop("MSFT")
        html = ad.render(data, qm_context=qm_context)
        self.assertIn("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5", html)
        self.assertIn("Rule-based top 5", html)
        self.assertEqual(html.count('class="hero-card '), 2 * config.PICK_TOP_N)
        self.assertGreaterEqual(html.count("Sell the AMZN $350 put"), 2)
        original_start = html.index("Rule-based top 5")
        qm_start = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        self.assertNotIn("Current QM signal", html[original_start:qm_start])
        self.assertIn(
            "QM is descriptive context only; it cannot change this mechanical card's "
            "membership, order, edge, or verdict.",
            html[qm_start:],
        )
        self.assertIn("PARABOLIC WARNING", html)
        self.assertIn("does not change the mechanical selection, order, edge, or verdict", html)
        self.assertIn("Parabolic FADE_REJECTED", html)
        self.assertIn("The preregistered fade reading failed.", html)

    def test_long_call_card_explains_when_frozen_study_cannot_support_frequency(self):
        section = _v2_section()
        section["groups"] = [
            {
                "kind": "long_call",
                "title": "BUY A CALL?",
                "empty": None,
                "cards": [
                    {
                        "strike": 380.0,
                        "expiry": "2026-07-17",
                        "dte": 17,
                        "cost": 250.0,
                        "breakeven": 382.5,
                        "breakeven_move": 0.025,
                        "rank_leader": True,
                        "grades": {"fits_cap": "GREEN", "liquidity": "GREEN"},
                    }
                ],
            }
        ]
        data = ad.assemble(
            symbol_sections=[section], rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11}
        )
        snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        snapshot["selection_status"] = "ELIGIBLE"
        snapshot["rank_eligible"] = True
        snapshot["policy"] = {"status": "ELIGIBLE", "reason_codes": []}
        html = ad.render(data, qm_context=self._qm_context())
        self.assertIn("frozen study records aggregate excursions, not per-fire moves", html)
        self.assertIn("not recomputed from today&#x27;s cache", html)

    def test_stale_qm_context_renders_configured_blocked_slots_but_original_remains(self):
        html = ad.render(
            self._assembled(),
            qm_context=self._qm_context(status="DATA_BLOCKED", as_of="2026-06-29"),
        )
        qm_start = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        original_start = html.index("Rule-based top 5")
        qm_section = html[qm_start:]
        self.assertEqual(qm_section.count("DATA BLOCKED"), config.PICK_TOP_N)
        self.assertIn("Sell the MSFT $350 put", html[original_start:])

    def test_incomplete_current_qm_context_renders_configured_blocked_slots(self):
        context = self._qm_context()
        del context["symbols"]["MSFT"]
        html = ad.render(self._assembled(), qm_context=context)
        qm_start = html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5")
        self.assertEqual(html[qm_start:].count("DATA BLOCKED"), config.PICK_TOP_N)
        self.assertIn("QM context missing or stale for: MSFT", html)

    def test_qm_section_reports_dropped_research_annotation(self):
        context = _v2_context()
        context["annotations"] = {
            "MSFT:put:2026-07-17:999.00": _valid_annotation(),
        }

        html = ad.render(self._assembled(), context=context, qm_context=self._qm_context())

        desk_start = html.index("RESEARCH DESK")
        desk_end = html.index("EXPERIMENTS SHELF")
        self.assertIn("research annotation(s) do not match any card", html[desk_start:desk_end])

    def test_page_order_puts_mechanical_list_before_descriptive_qm_comparison(self):
        html = ad.render(self._assembled(), context=_v2_context(), qm_context=self._qm_context())
        self.assertLess(
            html.index("Rule-based top 5"),
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
        )
        self.assertLess(
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
            html.index("Quant-want background"),
        )
        self.assertLess(html.index("Quant-want background"), html.index("Market context"))
        self.assertLess(html.index("Market context"), html.index("Symbol review"))
        self.assertIn("DESCRIPTIVE ONLY — NOT A TRADE RANKING", html)

    def test_composite_board_renders_between_qm_comparison_and_quant_background(self):
        from options_researcher import composite_signals as cs

        blocked_card = cs._card_blocked(
            "ZZZ", "no cached closes (FileNotFoundError)", asof="2026-07-01"
        )
        data = self._assembled()
        data["composite_signals"] = [blocked_card]
        html = ad.render(data, context=_v2_context(), qm_context=self._qm_context())
        self.assertLess(
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
            html.index("Composite signal board"),
        )
        self.assertLess(
            html.index("Composite signal board"), html.index("Quant-want background")
        )


class ContextLaneRenderTests(unittest.TestCase):
    def _data(self, count=6):
        sections = []
        for index in range(count):
            sections.append({
                "symbol": f"S{index}",
                "as_of": "2026-08-25",
                "close": 100.0,
                "iv_rank": 0.5,
                "groups": [{
                    "kind": "put",
                    "title": "SELL A PUT?",
                    "cards": [{
                        "strike": 95.0,
                        "expiry": "2026-09-18",
                        "dte": 24,
                        "credit": 100.0 + (count - index),
                        "annualized_yield": 0.30 - index / 100.0,
                        "cushion": 0.05,
                        "grades": {"yield": "GREEN", "liquidity": "GREEN"},
                        "verdict": "display only",
                    }],
                    "empty": None,
                }],
            })
        data = ad.assemble(
            symbol_sections=sections,
            rv21_by_symbol={},
            today="2026-08-25",
            composite_signals=[],
        )
        for section in data["symbols"]:
            snapshot = section["groups"][0]["cards"][0]["top3_snapshot"]
            snapshot.update({
                "rank_eligible": True,
                "selection_status": "ELIGIBLE",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            })
        return data

    @staticmethod
    def _composite(symbol, *, count=3, trend="UP", grade="A"):
        return {
            "symbol": symbol,
            "grade": grade,
            "aligned_count": count,
            "max_asof": "2026-08-25",
            "trend": {"state": trend, "data_blocked": trend == "DATA_BLOCKED"},
            "vol_premium": {"state": "CHEAP" if count >= 2 else "NEUTRAL",
                            "data_blocked": False},
            "regime": {"state": "CALM", "high_dispersion": count < 3,
                       "data_blocked": False},
            "internals": {"state": "CONFIRM" if count >= 4 else "NEUTRAL",
                          "data_blocked": False},
        }

    def test_flag_off_matches_post_brief26_golden_bytes(self):
        import hashlib
        from unittest import mock

        case = LaneBoardPresentationTests()
        with mock.patch.object(config, "CONTEXT_LANE_ENABLED", False):
            html = ad.render(
                case._data(),
                context=case._context(),
                qm_context={"status": "DATA_BLOCKED"},
                research_views_status={"state": "absent"},
            )

        self.assertEqual(
            hashlib.sha256(html.encode()).hexdigest(),
            "f092f03e0c58a904a7126a03e6107494ee4740695e7c7e717eb965b9570c5af7",
        )
        self.assertNotIn("CONTEXT-AWARE SHORTLIST — EXPERIMENTAL", html)

    def test_flag_on_reorders_full_pool_and_diagnoses_displaced_frozen_name(self):
        from unittest import mock

        data = self._data()
        data["composite_signals"] = [
            self._composite(f"S{index}", count=(4 if index == 5 else 3))
            for index in range(6)
        ]
        data["composite_signals"][4] = self._composite(
            "S4", count=0, trend="MIXED", grade="B"
        )
        frozen = [pick["symbol"] for pick in ad.select_top_picks(
            data, include_csp_watch=True)]

        with mock.patch.object(config, "CONTEXT_LANE_ENABLED", True):
            html = ad.render(data)

        section_start = html.index("CONTEXT-AWARE SHORTLIST — EXPERIMENTAL")
        section_end = html.index("QM MOVEMENT LANE")
        section = html[section_start:section_end]
        self.assertEqual(frozen, ["S0", "S1", "S2", "S3", "S4"])
        self.assertIn('data-context-symbol="S5"', section)
        self.assertNotIn('data-context-symbol="S4"', section)
        self.assertIn('data-diagnostic-symbol="S4">DISPLACED', section)
        for symbol in frozen:
            self.assertIn(f'data-diagnostic-symbol="{symbol}"', section)
        self.assertLess(html.index("Rule-based top 5"), section_start)
        self.assertLess(section_start, html.index("QM MOVEMENT LANE"))
        self.assertIn(
            "Experimental re-ordering by market context. The rule-based list above is "
            "the registered baseline. This lane is display-only and carries no verdict "
            "or trade authority; once the pick tracker is live its picks will be tracked "
            "descriptively against the baseline.",
            section,
        )

    def test_selected_blocked_composite_stays_in_slot_with_reason(self):
        from unittest import mock

        data = self._data(count=1)
        data["composite_signals"] = [
            self._composite("S0", count=0, trend="DATA_BLOCKED", grade="C")
        ]

        with mock.patch.object(config, "CONTEXT_LANE_ENABLED", True):
            html = ad.render(data)

        section = html[
            html.index("CONTEXT-AWARE SHORTLIST — EXPERIMENTAL"):
            html.index("QM MOVEMENT LANE")
        ]
        self.assertIn('data-context-symbol="S0"', section)
        self.assertIn("BLOCKED", section)

    def test_flag_on_shows_zero_credit_for_vetoed_down_and_mixed_context(self):
        from unittest import mock

        data = self._data(count=3)
        data["composite_signals"] = [
            self._composite("S0", count=3, grade="C"),
            self._composite("S1", count=3, trend="DOWN"),
            self._composite("S2", count=0, trend="MIXED"),
        ]

        with mock.patch.object(config, "CONTEXT_LANE_ENABLED", True):
            html = ad.render(data)

        section = html[
            html.index("CONTEXT-AWARE SHORTLIST — EXPERIMENTAL") :
            html.index("QM MOVEMENT LANE")
        ]
        for symbol, reason in (
            ("S0", "VETOED"),
            ("S1", "DIRECTION_MISMATCH"),
            ("S2", "DIRECTION_MISMATCH"),
        ):
            start = section.index(f'data-context-symbol="{symbol}"')
            card = section[start : section.index("</details></div>", start)]
            self.assertIn(reason, card)
            self.assertIn("context term 0", card)

    def test_scoring_exception_renders_loud_failure(self):
        from unittest import mock

        with (
            mock.patch.object(config, "CONTEXT_LANE_ENABLED", True),
            mock.patch(
                "options_researcher.context_lane.rank_context_lane",
                side_effect=RuntimeError("injected"),
            ),
        ):
            html = ad.render(self._data(count=1))

        self.assertIn("CONTEXT LANE FAILED — RuntimeError", html)


class InputRootFallbackTests(unittest.TestCase):
    """ATTRACTIVENESS_INPUT_ROOT unset -> default to the ops checkout.

    Owner-directed 2026-08-25: a repo/dev build must read board inputs
    (receipts, caches) from the ops checkout by default, because capture
    receipts are written only there; reading the dev checkout's own
    reports/ renders a falsely stale board.
    """

    def _run(self, fallback, env_value=None):
        import os
        import tempfile
        from pathlib import Path
        from unittest import mock

        del tempfile  # helper signature symmetry; dirs made by callers
        with mock.patch.dict(os.environ):
            os.environ.pop("ATTRACTIVENESS_INPUT_ROOT", None)
            if env_value is not None:
                os.environ["ATTRACTIVENESS_INPUT_ROOT"] = env_value
            with mock.patch.object(ad, "OPS_CHECKOUT_FALLBACK", fallback):
                before = Path.cwd()
                with ad._input_root_cwd() as root:
                    inside = Path.cwd()
                after = Path.cwd()
        return before, root, inside, after

    def test_unset_env_defaults_to_existing_ops_checkout(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ops = Path(tmp) / "options-validator-ops"
            ops.mkdir()
            before, root, inside, after = self._run(ops)
        self.assertEqual(root, ops.resolve())
        self.assertEqual(inside, ops.resolve())
        self.assertEqual(after, before)

    def test_unset_env_without_ops_checkout_stays_in_cwd(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no-such-checkout"
            before, root, inside, after = self._run(missing)
        self.assertEqual(root, before)
        self.assertEqual(inside, before)
        self.assertEqual(after, before)

    def test_explicit_env_wins_over_ops_fallback(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ops = Path(tmp) / "options-validator-ops"
            ops.mkdir()
            explicit = Path(tmp) / "explicit-root"
            explicit.mkdir()
            before, root, inside, after = self._run(
                ops, env_value=str(explicit))
        self.assertEqual(root, explicit.resolve())
        self.assertEqual(inside, explicit.resolve())
        self.assertEqual(after, before)

    def test_env_dot_forces_current_checkout(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            ops = Path(tmp) / "options-validator-ops"
            ops.mkdir()
            before, root, inside, after = self._run(ops, env_value=".")
        self.assertEqual(root, before.resolve())
        self.assertEqual(inside, before.resolve())
        self.assertEqual(after, before)

    def test_fallback_equal_to_cwd_does_not_chdir(self):
        from pathlib import Path

        before, root, inside, after = self._run(Path.cwd())
        self.assertEqual(root, before)
        self.assertEqual(inside, before)
        self.assertEqual(after, before)


class MainTests(unittest.TestCase):
    def setUp(self):
        # Hermeticity: keep env-unset builds in the test cwd even on the
        # machine where the real ops checkout exists (the default-input-root
        # fallback is covered by InputRootFallbackTests above).
        from pathlib import Path
        from unittest import mock

        patcher = mock.patch.object(
            ad, "OPS_CHECKOUT_FALLBACK", Path("/nonexistent-ops-checkout"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_main_loads_board_and_context_from_same_external_root(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest import mock

        section = {
            "symbol": "MSFT",
            "as_of": "2026-07-24",
            "close": 373.02,
            "iv_rank": 0.88,
            "groups": [{
                "kind": "put",
                "title": "SELL A PUT?",
                "cards": [],
                "empty": "none this cycle",
            }],
        }
        original_cwd = Path.cwd()
        observed: dict[str, Path] = {}

        def gather():
            observed["board"] = Path.cwd()
            return [section], {"MSFT": 1.1}, [], {
                "verified_sessions": [], "failures": [], "receipts_found": False}

        def load_context_evidence(_as_of):
            observed["context"] = Path.cwd()
            return {"state": "unavailable", "context": None,
                    "warning": None, "source_path": None, "sha256": None}

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            board_root = (root / "ops").resolve()
            board_root.mkdir()
            output = root / "research" / "attractiveness.html"
            with (
                mock.patch.dict(
                    os.environ,
                    {"ATTRACTIVENESS_INPUT_ROOT": str(board_root)},
                ),
                mock.patch.object(ad, "_gather_all", side_effect=gather),
                mock.patch.object(
                    ad, "load_context_evidence", side_effect=load_context_evidence),
                mock.patch.object(config, "CONTEXT_LANE_ENABLED", True),
                mock.patch.object(ad, "OUTPUT_PATH", str(output)),
                mock.patch(
                    "options_researcher.hypothesis_evidence.gather_hypothesis_evidence",
                    return_value={},
                ),
                mock.patch(
                    "options_researcher.qm_dashboard.load_qm_context",
                    return_value={},
                ),
            ):
                path = ad.main()

        self.assertEqual(observed["board"], board_root)
        self.assertEqual(observed["context"], board_root)
        self.assertEqual(Path.cwd(), original_cwd)
        self.assertEqual(Path(path).resolve(), output.resolve())

    def test_flag_off_build_uses_same_root_context_but_keeps_legacy_chip_path(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest import mock

        section = {
            "symbol": "MSFT",
            "as_of": "2026-07-24",
            "close": 373.02,
            "iv_rank": 0.88,
            "groups": [{
                "kind": "put",
                "title": "SELL A PUT?",
                "cards": [],
                "empty": "none this cycle",
            }],
        }
        context = {"as_of": "2026-07-24", "annotations": {}}
        with tempfile.TemporaryDirectory() as temp:
            board_root = (Path(temp) / "input-root").resolve()
            board_root.mkdir()
            output = Path(temp) / "deployment" / "attractiveness.html"
            observed = {}

            def load_evidence(_as_of):
                observed["context_cwd"] = Path.cwd()
                return {
                    "state": "loaded",
                    "context": context,
                    "warning": None,
                    "source_path": str(board_root / "context.json"),
                    "sha256": "a" * 64,
                }

            with (
                mock.patch.object(config, "CONTEXT_LANE_ENABLED", False),
                mock.patch.dict(
                    os.environ, {"ATTRACTIVENESS_INPUT_ROOT": str(board_root)}
                ),
                mock.patch.object(ad, "load_context") as legacy,
                mock.patch.object(
                    ad, "load_context_evidence", side_effect=load_evidence
                ) as evidence,
                mock.patch.object(
                    ad, "_verify_context_evidence", side_effect=lambda value: value
                ),
                mock.patch.object(ad, "render", return_value="baseline-bytes") as render,
                mock.patch.object(ad, "OUTPUT_PATH", str(output)),
                mock.patch(
                    "options_researcher.research_views_publication.copy_publication"
                ),
                mock.patch(
                    "options_researcher.qm_dashboard.load_qm_context", return_value={}
                ),
            ):
                ad._build_and_write(
                    symbol_sections=[section], rv21_by_symbol={"MSFT": 1.1}
                )

        legacy.assert_not_called()
        evidence.assert_called_once_with("2026-07-24")
        self.assertEqual(observed["context_cwd"], board_root)
        self.assertIsNone(render.call_args.kwargs["context_evidence"])
        self.assertEqual(render.call_args.kwargs["context"], context)

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


# ---------------------------------------------------------------------------
# Brief 13: passive Lane Board presentation surfaces.
# ---------------------------------------------------------------------------


class LaneBoardPresentationTests(unittest.TestCase):
    """Presentation-only board surfaces must stay injected and fail-visible."""

    def _data(self):
        data = ad.assemble(
            symbol_sections=[
                _fresh_section("NVDA", "2026-08-14", closes_as_of="2026-08-13"),
                _stale_section("MSFT", "2026-08-11", closes_as_of="2026-08-12"),
            ],
            rv21_by_symbol={},
            today="2026-08-14",
            composite_signals=[
                {"symbol": "NVDA", "grade": "A", "max_asof": "2026-08-13"},
                {"symbol": "MSFT", "grade": "B", "max_asof": "2026-08-12"},
            ],
        )
        return data

    def _context(self):
        return {
            "as_of": "2026-08-14",
            "researched_on": "2026-08-14",
            "provenance": "fixture provenance",
            "symbols": {"NVDA": {"news_summary": "covered"}},
        }

    def test_status_reader_accepts_only_validated_current_generation(self):
        from options_researcher import research_views_publication as publication

        generation_id = "20260815T113000000000Z-0123456789abcdef0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            dashboard = Path(tmp)
            staging = dashboard / "research-views-generations" / f".staging-{generation_id}"
            staging.mkdir(parents=True)
            for name in publication.ARTIFACTS:
                (staging / name).write_text(f"{name}\n")
            publication.publish_generation(
                dashboard_dir=dashboard, staging_dir=staging,
                generation_id=generation_id,
                published_at="2026-08-15T11:30:00.000000Z",
                producer_commit="a" * 40)
            status = ad.load_research_views_status(dashboard)
            self.assertEqual(status["state"], "published")
            self.assertEqual(status["generation_id"], generation_id)
            status_path = status["artifacts"]["research-views-status.txt"]
            status_path.write_bytes(status_path.read_bytes() + b"x")
            self.assertEqual(ad.load_research_views_status(dashboard)["state"],
                             "integrity_failed")

    def test_freshness_research_composite_and_shelf_are_visible_in_board_order(self):
        html = ad.render(
            self._data(),
            context=self._context(),
            qm_context={"status": "DATA_BLOCKED"},
            research_views_status={
                "state": "published",
                "published_at": "2026-08-15T11:30:00.000000Z",
                "generation_id": "20260815T113000000000Z-0123456789abcdef0123456789abcdef",
            },
        )
        self.assertIn("DATA FRESHNESS", html)
        self.assertIn("Frozen EOD (.cache/chains)", html)
        self.assertIn("Verified Schwab 15:45 pre-close (.cache/schwab_chains)", html)
        self.assertIn("Underlying closes", html)
        self.assertIn("Rule-based top 5 — best policy-and-liquidity fit today", html)
        self.assertIn(
            "Chosen by fixed rules (green-check fraction, one pick per stock). This is a fit ranking, not a prediction; whether it predicts anything is exactly what the registered RQ2/A2 studies will measure.",
            html,
        )
        self.assertIn("Highest agreement today: NVDA", html)
        self.assertIn("RESEARCH DESK", html)
        self.assertEqual(html.count('class="research-coverage-row"'), 18)
        self.assertIn("EXPERIMENTS SHELF", html)
        self.assertIn('href="research-views-generations/', html)
        self.assertIn("experiments: OK", html)
        self.assertIn("wasserstein: OK", html)
        for earlier, later in (
            ("DATA FRESHNESS", "Rule-based top 5"),
            ("Rule-based top 5", "QM MOVEMENT LANE"),
            ("QM MOVEMENT LANE", "QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
            ("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5", "Composite signal board"),
            ("Composite signal board", "RESEARCH DESK"),
            ("RESEARCH DESK", "EXPERIMENTS SHELF"),
            ("EXPERIMENTS SHELF", "Symbol review"),
        ):
            self.assertLess(html.index(earlier), html.index(later))

    def test_experiments_views_freshness_chip_is_inside_top_freshness_strip(self):
        """A shelf-only status must not satisfy the top-strip freshness contract."""
        html = ad.render(
            self._data(),
            context=self._context(),
            research_views_status={
                "state": "published",
                "published_at": "2026-08-15T11:30:00.000000Z",
                "generation_id": "20260815T113000000000Z-0123456789abcdef0123456789abcdef",
            },
        )

        freshness = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("Experiments views</strong>", freshness)
        self.assertIn("2026-08-15T11:30:00.000000Z", freshness)
        self.assertIn("experiments: OK", freshness)
        self.assertIn("wasserstein: OK", freshness)

    def test_experiments_views_absent_chip_honestly_says_not_published(self):
        html = ad.render(self._data(), research_views_status={"state": "absent"})
        freshness = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("Experiments views</strong> not published", freshness)
        self.assertIn("BLOCKED", freshness)

    def test_underlying_closes_freshness_uses_configured_store_max_not_section_date(self):
        import tempfile
        from unittest import mock

        import pandas as pd

        from data import underlying_closes

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(underlying_closes, "CACHE_DIR", tmp):
                underlying_closes.store_closes(
                    "NVDA",
                    pd.DataFrame({
                        "date": ["2026-08-13", "2026-08-14"],
                        "close": [100.0, 101.0],
                    }),
                )
                freshness = ad._underlying_closes_store_freshness(("NVDA",))

            data = ad.assemble(
                symbol_sections=[
                    _fresh_section("NVDA", "2026-08-13", closes_as_of="2026-08-13"),
                ],
                rv21_by_symbol={},
                today="2026-08-14",
                underlying_closes_freshness=freshness,
            )

        html = ad.render(data)
        strip = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("Underlying closes</strong> max session 2026-08-14", strip)
        self.assertNotIn("Underlying closes</strong> as of 2026-08-13", strip)

    def test_underlying_closes_freshness_fails_honestly_for_missing_and_malformed_store(self):
        import tempfile
        from pathlib import Path
        from unittest import mock

        import pandas as pd

        from data import underlying_closes

        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            with mock.patch.object(underlying_closes, "CACHE_DIR", tmp):
                underlying_closes.store_closes(
                    "NVDA",
                    pd.DataFrame({"date": ["2026-08-14"], "close": [101.0]}),
                )
                missing = ad._underlying_closes_store_freshness(("NVDA", "MSFT"))
                (cache / "MSFT.parquet").write_text("not a parquet file")
                malformed = ad._underlying_closes_store_freshness(("NVDA", "MSFT"))

        self.assertEqual(missing["state"], "unavailable")
        self.assertIn("missing", missing["detail"])
        self.assertEqual(malformed["state"], "unavailable")
        self.assertIn("malformed", malformed["detail"])

        data = self._data()
        data["underlying_closes_freshness"] = malformed
        html = ad.render(data)
        strip = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("Underlying closes</strong> unavailable", strip)
        self.assertIn("BLOCKED", strip)

    def test_registered_bets_tracker_escapes_states_and_sits_before_shelf(self):
        """A raw receipt summary remains escaped, descriptive, and unranked."""
        data = self._data()
        data["family_evidence"] = [{
            "family": "H5<script>",
            "ritual_state": "MISSING",
            "ritual_detail": "NO RECEIPT <unsafe>",
            "raw_state_counts": [{"state": "UNKNOWN", "count": 2}],
            "evaluation_session": None,
            "run_date": None,
            "sources": [{"path": "reports/<unsafe>.json"}],
            "registered_window_end": None,
            "registered_window_metadata": None,
        }]

        html = ad.render(data, context=self._context())

        self.assertIn("REGISTERED-BETS TRACKER", html)
        self.assertIn("H5&lt;script&gt;", html)
        self.assertIn("NO RECEIPT &lt;unsafe&gt;", html)
        self.assertIn("evidence UNKNOWN: 2", html)
        self.assertIn("read-only receipt summary", html)
        self.assertIn("cannot activate, rank, or place a trade", html)
        self.assertNotIn("<script>", html)
        self.assertLess(html.index("RESEARCH DESK"), html.index("REGISTERED-BETS TRACKER"))
        self.assertLess(html.index("REGISTERED-BETS TRACKER"), html.index("EXPERIMENTS SHELF"))

    def test_tracker_attachment_cannot_change_mechanical_selection_bytes(self):
        """A family rollup is presentation data, never a selection input."""
        import json

        baseline = self._data()
        tracked = self._data()
        tracked["family_evidence"] = [{
            "family": "H10a",
            "ritual_state": "REFUSED",
            "ritual_detail": "preflight exit 1",
            "raw_state_counts": [{"state": "UNKNOWN", "count": 1}],
            "evaluation_session": None,
            "run_date": None,
            "sources": [],
            "registered_window_end": "2026-10-06",
            "registered_window_metadata": "registered-window metadata",
        }]
        baseline_bytes = json.dumps(
            ad.select_top_picks(baseline), sort_keys=True, separators=(",", ":")
        ).encode()

        ad.render(tracked)

        self.assertEqual(
            json.dumps(
                ad.select_top_picks(tracked), sort_keys=True, separators=(",", ":")
            ).encode(),
            baseline_bytes,
        )

    def test_full_lane_board_order_keeps_named_sections_distinct(self):
        """The retained QM comparison stays below movement without merging lanes."""
        data = self._data()
        data["family_evidence"] = [{
            "family": "H5",
            "ritual_state": "NO_SIGNAL",
            "ritual_detail": "no signal",
            "raw_state_counts": [{"state": "WAIT", "count": 1}],
            "evaluation_session": "2026-08-14",
            "run_date": "2026-08-14",
            "sources": [],
            "registered_window_end": None,
            "registered_window_metadata": None,
        }]
        context = self._context()
        context["market"] = {"summary": "Fixture market context."}
        html = ad.render(
            data,
            context=context,
            qm_context={"status": "DATA_BLOCKED"},
            research_views_status={"state": "absent"},
        )
        headings = (
            "DATA FRESHNESS",
            "Rule-based top 5",
            "QM MOVEMENT LANE",
            "QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5",
            "Composite signal board",
            "RESEARCH DESK",
            "REGISTERED-BETS TRACKER",
            "EXPERIMENTS SHELF",
            "CORE NAMES",
            "Market context",
            "Symbol review",
        )
        for earlier, later in zip(headings, headings[1:]):
            self.assertLess(html.index(earlier), html.index(later))

    def test_unknown_freshness_and_absent_research_are_blocked_not_ok(self):
        data = self._data()
        data["symbols"][0]["as_of"] = "not-a-date"
        data["symbols"][0]["closes_as_of"] = "not-a-date"
        data["chain_age_sessions"] = None
        html = ad.render(data, research_views_status={"state": "absent"})
        freshness = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("UNKNOWN", freshness)
        self.assertIn("BLOCKED", freshness)
        self.assertIn("research: none", html)
        self.assertIn("not published", html)

    def test_research_desk_marks_stale_and_scalar_packets_uncovered(self):
        context = self._context()
        context.update({"as_of": "2026-08-11", "symbols": {"NVDA": "bad packet"}})
        html = ad.render(self._data(), context=context)
        desk = html[html.index("RESEARCH DESK"):html.index("EXPERIMENTS SHELF")]
        self.assertIn("stale by 3 sessions", desk)
        self.assertIn("NVDA</strong> · no mapping-valued packet", desk)
        self.assertEqual(desk.count('class="research-coverage-row"'), 18)

    def test_research_freshness_uses_later_board_evaluation_not_mixed_source_date(self):
        data = self._data()
        data["evaluation_date"] = "2026-08-17"
        html = ad.render(data, context=self._context())
        freshness = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        self.assertIn("Research</strong> as of 2026-08-14; researched on 2026-08-14; stale by 1 sessions; WARN", freshness)

    def test_schwab_freshness_uses_stalest_constituent_date(self):
        data = ad.assemble(
            symbol_sections=[
                _fresh_section("NVDA", "2026-08-11"),
                _fresh_section("AMD", "2026-08-14"),
            ],
            rv21_by_symbol={},
            today="2026-08-14",
        )
        html = ad.render(data)
        freshness = html[html.index("DATA FRESHNESS"):html.index("Rule-based top 5")]
        schwab = freshness[freshness.index("Verified Schwab"):freshness.index("Underlying closes")]
        self.assertIn("as of 2026-08-11; 3 sessions old", schwab)
        self.assertIn("BLOCKED", schwab)

    def test_hard_chain_block_banner_survives_freshness_strip(self):
        data = ad.assemble(
            symbol_sections=[_stale_section("MSFT", "2026-08-11")],
            rv21_by_symbol={},
            today="2026-08-14",
        )
        html = ad.render(data)
        self.assertIn("STALE BOARD", html)
        self.assertLess(html.index("DATA FRESHNESS"), html.index("STALE BOARD"))

    def test_composite_summary_never_promotes_malformed_or_non_a_cards(self):
        html = ad._composite_html({
            "composite_signals": [
                {"symbol": "MSFT", "grade": "B"},
                {"symbol": "bad", "grade": None},
                "not-a-card",
            ]
        })
        self.assertIn("Highest agreement today: none at grade A", html)

    def test_empty_composite_lane_is_rendered_with_honest_no_data_state_in_order(self):
        data = self._data()
        data["composite_signals"] = []
        html = ad.render(data, context=self._context())
        composite = html[html.index("Composite signal board"):html.index("RESEARCH DESK")]

        self.assertIn("display-only", composite)
        self.assertIn("Highest agreement today: none at grade A", composite)
        self.assertIn("No composite cards are available for this board.", composite)
        self.assertLess(
            html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"),
            html.index("Composite signal board"),
        )
        self.assertLess(html.index("Composite signal board"), html.index("RESEARCH DESK"))


class ChainAgeBannerTests(unittest.TestCase):
    """The board must state how old its option quotes are.

    Reproduces the 2026-08-04 production gap: a chain cache frozen at
    2026-07-27 rendered as a normal board because every internal consistency
    check passed -- the features were exactly as stale as the chain.
    """

    def _section(self, as_of: str) -> dict:
        return {
            "symbol": "MSFT", "as_of": as_of, "close": 373.02,
            "iv_rank": 0.30, "features_as_of": as_of, "features_stale": False,
            "groups": [
                {"kind": "put", "title": "SELL A PUT?",
                 "cards": [{"strike": 350.0, "expiry": "2026-09-18",
                            "dte": 45, "credit": 494.0, "yield_mo": 0.0071,
                            "grades": {"yield": "AMBER"},
                            "verdict": "you'd be promising..."}],
                 "empty": None},
            ],
        }

    def _assemble(self, as_of: str, today: str | None):
        return ad.assemble(symbol_sections=[self._section(as_of)],
                           rv21_by_symbol={"MSFT": math.sqrt(12) * 0.11},
                           today=today)

    def test_injected_fixtures_are_never_aged_out_by_the_calendar(self):
        data = self._assemble("2026-06-30", None)
        self.assertIsNone(data["chain_age_sessions"])
        self.assertNotIn("STALE BOARD", ad.render(data))

    def test_production_gap_renders_a_loud_stale_banner(self):
        data = self._assemble("2026-07-27", "2026-08-04")
        self.assertEqual(data["chain_age_sessions"], 6)
        html = ad.render(data)
        self.assertIn("STALE BOARD", html)
        self.assertIn("6 trading sessions old", html)
        self.assertIn("2026-07-27", html)

    def test_stale_board_loses_rank_eligibility(self):
        data = self._assemble("2026-07-27", "2026-08-04")
        snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        self.assertFalse(snapshot["rank_eligible"])
        self.assertIn("CHAIN_STALE_VS_TODAY",
                      snapshot["integrity"]["reason_codes"])

    def test_one_session_old_warns_without_blocking(self):
        data = self._assemble("2026-08-03", "2026-08-04")
        self.assertEqual(data["chain_age_sessions"], 1)
        html = ad.render(data)
        self.assertIn("1 trading session old", html)
        self.assertNotIn("STALE BOARD", html)
        # Integrity only: rank_eligible also carries lane portfolio policy,
        # which this gate must not influence in either direction.
        snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        self.assertEqual(snapshot["integrity"]["status"], "ELIGIBLE")
        self.assertNotIn("CHAIN_STALE_VS_TODAY",
                         snapshot["integrity"]["reason_codes"])

    def test_current_session_says_so(self):
        data = self._assemble("2026-08-04", "2026-08-04")
        self.assertEqual(data["chain_age_sessions"], 0)
        html = ad.render(data)
        self.assertIn("most recent completed session", html)
        self.assertNotIn("STALE BOARD", html)

    def test_unknown_age_is_stated_not_silently_passed(self):
        data = self._assemble("2026-08-05", "2026-08-04")
        self.assertIsNone(data["chain_age_sessions"])
        self.assertIn("UNKNOWN", ad.render(data))


# ---------------------------------------------------------------------------
# Brief 12 (rev-2): Schwab pre-close display freshness.
# ---------------------------------------------------------------------------

SCHWAB_SOURCE = "schwab_preclose"
THETA_SOURCE = "thetadata_eod"


def _fresh_section(symbol="NVDA", as_of="2026-08-14", **overrides):
    section = {
        "symbol": symbol,
        "as_of": as_of,
        "close": 225.08,
        "iv_rank": float("nan"),
        "chain_source": SCHWAB_SOURCE,
        "close_as_of": as_of,
        "close_kind": "preclose_mid_1545",
        "closes_as_of": "2026-08-04",
        "technicals_as_of": "2026-08-04",
        "features_as_of": as_of,
        "features_stale": False,
        "features_source": "schwab_preclose_session",
        "atm_iv": 0.4772,
        "feature_unavailable": [
            {"field": "rv21",
             "reason": "underlying closes end 2026-08-04, before this "
                       "2026-08-14 session"},
        ],
        "groups": [{"kind": "put", "title": "SELL A PUT?", "cards": [],
                    "empty": "none this cycle"}],
    }
    section.update(overrides)
    return section


def _stale_section(symbol="MSFT", as_of="2026-07-27", **overrides):
    section = {
        "symbol": symbol,
        "as_of": as_of,
        "close": 180.0,
        "iv_rank": 0.42,
        "chain_source": THETA_SOURCE,
        "close_as_of": as_of,
        "close_kind": "eod_close",
        "features_as_of": as_of,
        "features_stale": False,
        "groups": [{"kind": "put", "title": "SELL A PUT?", "cards": [],
                    "empty": "none this cycle"}],
    }
    section.update(overrides)
    return section


class SchwabFreshnessPageDateTests(unittest.TestCase):
    """D3: one date can no longer describe two sources, so the page says both."""

    def test_page_date_follows_the_newest_verified_fresh_session(self):
        sections = [_fresh_section("NVDA", "2026-08-14"),
                    _stale_section("MSFT", "2026-07-27")]
        self.assertEqual(ad._page_data_as_of(sections), "2026-08-14")
        self.assertEqual(ad._page_as_of_kind(sections), SCHWAB_SOURCE)
        self.assertEqual(ad._stale_path_as_of(sections),
                         ("2026-07-27", ["MSFT"]))

    def test_without_a_fresh_source_the_earliest_date_still_wins(self):
        sections = [_stale_section("MSFT", "2026-07-27"),
                    _stale_section("CLSK", "2026-07-01")]
        self.assertEqual(ad._page_data_as_of(sections), "2026-07-01")
        self.assertEqual(ad._page_as_of_kind(sections), THETA_SOURCE)

    def test_assemble_publishes_both_sides_of_a_mixed_board(self):
        data = ad.assemble(
            symbol_sections=[_fresh_section("NVDA", "2026-08-14"),
                             _stale_section("MSFT", "2026-07-27")],
            rv21_by_symbol={}, today="2026-08-14")
        self.assertEqual(data["data_as_of"], "2026-08-14")
        self.assertEqual(data["as_of_kind"], SCHWAB_SOURCE)
        self.assertEqual(data["fresh_symbols"], ["NVDA"])
        self.assertEqual(data["stale_symbols"], ["MSFT"])
        self.assertEqual(data["stale_as_of"], "2026-07-27")
        self.assertEqual(data["stale_chain_age_sessions"], 14)

    def test_banner_states_the_pre_close_source_and_the_stale_names(self):
        data = ad.assemble(
            symbol_sections=[_fresh_section("NVDA", "2026-08-14"),
                             _stale_section("MSFT", "2026-07-27")],
            rv21_by_symbol={}, today="2026-08-14")
        html = ad.render(data)
        # The BANNER's own sentence -- the per-section line carries the same
        # label, so a page-wide substring would pass with the banner gutted.
        self.assertIn(
            "<strong>Option quotes: 15:45 pre-close (Schwab) session "
            "2026-08-14</strong>", html)
        self.assertIn("a 15:45 ET snapshot, NOT an end-of-day close", html)
        self.assertIn("STALE BOARD for MSFT", html)
        self.assertIn("14 trading sessions old", html)

    def test_header_chip_never_calls_a_pre_close_snapshot_a_close(self):
        data = ad.assemble(symbol_sections=[_fresh_section()],
                           rv21_by_symbol={}, today="2026-08-14")
        html = ad.render(data)
        self.assertIn("<strong>Pre-close 15:45 (Schwab)</strong> 2026-08-14",
                      html)
        self.assertNotIn("<strong>Market close</strong> 2026-08-14", html)

    def test_thetadata_only_board_keeps_the_market_close_chip(self):
        data = ad.assemble(symbol_sections=[_stale_section("MSFT", "2026-07-27")],
                           rv21_by_symbol={}, today="2026-08-14")
        html = ad.render(data)
        self.assertIn("<strong>Market close</strong> 2026-07-27", html)
        self.assertNotIn("Pre-close 15:45", html)

    def test_fresh_card_passes_the_wall_clock_gate_that_stale_cards_fail(self):
        # The per-card CHAIN_STALE_VS_TODAY gate is UNCHANGED. It stands down
        # for fresh cards because their session really is today's, and it still
        # blocks the frozen-cache names on the same board.
        card = {"strike": 220.0, "expiry": "2026-09-18", "dte": 35,
                "credit": 400.0, "annualized_yield": 0.2,
                "grades": {"liquidity": "GREEN"}, "verdict": "…"}
        fresh = _fresh_section(groups=[{"kind": "put", "title": "SELL A PUT?",
                                        "cards": [dict(card)], "empty": None}])
        stale = _stale_section(groups=[{"kind": "put", "title": "SELL A PUT?",
                                        "cards": [dict(card)], "empty": None}])
        data = ad.assemble(symbol_sections=[fresh, stale],
                           rv21_by_symbol={}, today="2026-08-14")
        fresh_snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        stale_snapshot = data["symbols"][1]["groups"][0]["cards"][0]["top3_snapshot"]
        self.assertNotIn("CHAIN_STALE_VS_TODAY",
                         fresh_snapshot["integrity"]["reason_codes"])
        self.assertIn("CHAIN_STALE_VS_TODAY",
                      stale_snapshot["integrity"]["reason_codes"])

    def test_section_states_its_source_and_that_the_price_is_a_1545_mid(self):
        data = ad.assemble(symbol_sections=[_fresh_section()],
                           rv21_by_symbol={}, today="2026-08-14")
        html = ad.render(data)
        self.assertIn("Quotes: 15:45 pre-close (Schwab) session 2026-08-14",
                      html)
        self.assertIn("15:45 spot mid from the same capture instant", html)
        self.assertIn("<span>Spot 15:45 pre-close</span>", html)
        self.assertIn("closes through 2026-08-04", html)

    def test_refused_fresh_chain_is_visible_not_silent(self):
        section = _stale_section(
            "NVDA", "2026-07-27",
            fresh_refusal_reason=("no verified 15:45 spot for 2026-08-14 — "
                                  "fresh 15:45 pre-close (Schwab) chain not "
                                  "rendered; this symbol stays on the frozen "
                                  "cache below"))
        html = ad.render(ad.assemble(symbol_sections=[section],
                                     rv21_by_symbol={}, today="2026-08-14"))
        self.assertIn("no verified 15:45 spot for 2026-08-14", html)

    def test_verification_failure_is_loud_on_the_page(self):
        data = ad.assemble(symbol_sections=[_stale_section("MSFT", "2026-07-27")],
                           rv21_by_symbol={}, today="2026-08-14")
        data["schwab_lane"] = {
            "verified_sessions": [],
            "failures": [{"session": "2026-08-14",
                          "reason": "SchwabChainManifestError: hash mismatch for NVDA"}],
            "receipts_found": True,
        }
        html = ad.render(data)
        self.assertIn("Schwab capture session 2026-08-14 FAILED verification",
                      html)
        self.assertIn("hash mismatch for NVDA", html)
        self.assertIn("chains were NOT used", html)

    def test_footer_says_the_two_dashboards_date_independently(self):
        # rev-2 D3: mission control is out of scope and keeps its own
        # closes-derived date, so the difference must be stated, not left to
        # look like one of the two being broken.
        html = ad.render(ad.assemble(symbol_sections=[_fresh_section()],
                                     rv21_by_symbol={}, today="2026-08-14"))
        self.assertIn("mission-control dashboard date INDEPENDENTLY", html)
        self.assertIn("a difference between the two is expected", html)

    def test_a_checkout_with_no_receipts_says_so(self):
        data = ad.assemble(symbol_sections=[_stale_section("MSFT", "2026-07-27")],
                           rv21_by_symbol={}, today="2026-08-14")
        data["schwab_lane"] = {"verified_sessions": [], "failures": [],
                               "receipts_found": False}
        html = ad.render(data)
        self.assertIn("No Schwab pre-close capture receipts found", html)


class FailClosedFeatureTests(unittest.TestCase):
    """D4a: a missing input renders UNKNOWN, never a default that reads GREEN."""

    def test_missing_iv_rank_does_not_grade_a_buyer_green(self):
        import config
        from options_researcher.attractiveness import grade

        self.assertEqual(
            grade(0.0, config.H5_IVR_BUY_GREEN, config.H5_IVR_BUY_RED,
                  higher_is_better=False),
            "GREEN")
        self.assertEqual(
            grade(float("nan"), config.H5_IVR_BUY_GREEN, config.H5_IVR_BUY_RED,
                  higher_is_better=False),
            "UNKNOWN")

    def test_missing_vrp_does_not_clear_a_zero_threshold(self):
        from options_researcher.attractiveness import _vrp_seller_grade

        self.assertEqual(_vrp_seller_grade(0.0), "GREEN")
        self.assertEqual(_vrp_seller_grade(float("nan")), "UNKNOWN")

    def test_missing_iv_rank_does_not_grade_a_seller(self):
        from options_researcher.attractiveness import _iv_seller_grade

        self.assertEqual(_iv_seller_grade(0.9), "GREEN")
        self.assertEqual(_iv_seller_grade(float("nan")), "UNKNOWN")

    def test_unavailable_iv_rank_is_words_not_a_number(self):
        data = ad.assemble(symbol_sections=[_fresh_section()],
                           rv21_by_symbol={}, today="2026-08-14")
        html = ad.render(data)
        self.assertIn("<span>IV rank</span><strong>unavailable</strong>", html)
        self.assertNotIn("<span>IV rank</span><strong>0.00</strong>", html)

    def test_unavailable_features_are_named_with_their_reason(self):
        html = ad.render(ad.assemble(symbol_sections=[_fresh_section()],
                                     rv21_by_symbol={}, today="2026-08-14"))
        self.assertIn("Unavailable for this session", html)
        self.assertIn("rv21: underlying closes end 2026-08-04", html)
        self.assertIn("show UNKNOWN (never a default value)", html)

    def test_absent_scenario_table_says_why(self):
        card = {"strike": 220.0, "expiry": "2026-09-18", "dte": 35,
                "credit": 400.0, "annualized_yield": 0.2,
                "grades": {"liquidity": "GREEN"}, "verdict": "…"}
        section = _fresh_section(groups=[{"kind": "put", "title": "SELL A PUT?",
                                          "cards": [card], "empty": None}])
        data = ad.assemble(symbol_sections=[section],
                           rv21_by_symbol={"NVDA": float("nan")},
                           today="2026-08-14")
        enriched = data["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(enriched["bbb"], [])
        self.assertIn("underlying closes end 2026-08-04", enriched["bbb_absent"])
        html = ad.render(data)
        self.assertIn("Scenario table unavailable", html)

    def test_atm_iv_from_the_fresh_session_is_shown(self):
        html = ad.render(ad.assemble(symbol_sections=[_fresh_section()],
                                     rv21_by_symbol={}, today="2026-08-14"))
        self.assertIn("<span>ATM IV</span><strong>47.7%</strong>", html)

    def test_receipt_without_local_chains_is_stated_without_a_false_alarm(self):
        data = ad.assemble(symbol_sections=[_stale_section("MSFT", "2026-07-27")],
                           rv21_by_symbol={}, today="2026-08-14")
        data["schwab_lane"] = {
            "verified_sessions": [],
            "failures": [{"session": "2026-08-14", "kind": "chains_absent",
                          "reason": "no chain files for session 2026-08-14"}],
            "receipts_found": True,
        }
        html = ad.render(data)
        self.assertIn("are present, but its chain files are not in this checkout",
                      html)
        self.assertNotIn("FAILED verification", html)


class FreshSourceAgesTests(unittest.TestCase):
    """N1: "verified pre-close" describes the SOURCE, never the clock.

    If captures stop, the newest verified session keeps its badge while
    silently becoming days old. The fresh line and the header chip therefore
    read the same chain_age_sessions the cards do.
    """

    def _data(self, today):
        card = {"strike": 220.0, "expiry": "2026-09-18", "dte": 35,
                "credit": 400.0, "annualized_yield": 0.2,
                "grades": {"liquidity": "GREEN"}, "verdict": "…"}
        section = _fresh_section(groups=[{"kind": "put", "title": "SELL A PUT?",
                                          "cards": [card], "empty": None}])
        return ad.assemble(symbol_sections=[section], rv21_by_symbol={},
                           today=today)

    def test_same_day_capture_is_calm_info(self):
        data = self._data("2026-08-14")
        self.assertEqual(data["chain_age_sessions"], 0)
        html = ad.render(data)
        self.assertIn('<div class="notice info"><strong>Option quotes: '
                      "15:45 pre-close (Schwab) session 2026-08-14</strong>",
                      html)
        self.assertNotIn("captures have STOPPED", html)
        self.assertIn("<strong>Pre-close 15:45 (Schwab)</strong>", html)

    def test_one_session_old_warns_and_says_how_old(self):
        data = self._data("2026-08-17")           # Mon after a Fri capture
        self.assertEqual(data["chain_age_sessions"], 1)
        html = ad.render(data)
        self.assertIn("now 1 trading session old", html)
        self.assertIn('<div class="notice watch">', html)
        self.assertIn("Pre-close 15:45 (Schwab) · 1 sessions old", html)
        self.assertNotIn("captures have STOPPED", html)

    def test_past_the_block_bar_the_fresh_line_is_loud_not_calm(self):
        data = self._data("2026-08-20")           # 4 sessions after 08-14
        self.assertEqual(data["chain_age_sessions"], 4)
        html = ad.render(data)
        self.assertIn("STALE BOARD — pre-close captures have STOPPED", html)
        self.assertIn("newest verified session (2026-08-14) is 4 trading "
                      "sessions old", html)
        self.assertIn('<div class="notice bad">', html)
        # The exact failure the reviewer demonstrated: the calm info line must
        # be gone, not merely accompanied by a warning.
        self.assertNotIn('<div class="notice info"><strong>Option quotes: ',
                         html)
        self.assertIn("STALE · Pre-close 15:45 (Schwab) · 4 sessions old", html)

    def test_a_long_capture_outage_cannot_read_like_a_current_board(self):
        data = self._data("2026-09-15")           # 22 sessions after 08-14
        self.assertEqual(data["chain_age_sessions"], 22)
        html = ad.render(data)
        self.assertIn("is 22 trading sessions old", html)
        self.assertIn("captures have STOPPED", html)
        snapshot = data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"]
        # The banner's tone now matches what the cards already did.
        self.assertIn("CHAIN_STALE_VS_TODAY",
                      snapshot["integrity"]["reason_codes"])

    def test_unknown_age_on_a_fresh_source_says_unknown(self):
        data = self._data(None)
        self.assertIsNone(data["chain_age_sessions"])
        html = ad.render(data)
        self.assertIn("could NOT be compared with the evaluation date", html)
        self.assertIn("age UNKNOWN", html)

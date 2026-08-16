"""Release-blocker fixes of 2026-07-16: earnings UNKNOWN tri-state, per-card
risk economics reconciled against the repo risk policy, PMCC-preview full
two-leg P&L + structural-preview exclusion, stale-feature veto, and the
sources / research-date rendering. Offline; synthetic fixtures only."""
import unittest

import pandas as pd

import options_researcher.attractiveness_dashboard as ad


def chain_rows(specs, exp="2026-07-17", *, vega=0.0, iv=0.5):
    rows = []
    for right, strike, delta, bid in specs:
        rows.append({"expiration": exp, "strike": strike, "right": right,
                     "bid": bid, "ask": bid + 0.10, "open_interest": 500,
                     "iv": iv, "delta": delta, "gamma": 0.0, "theta": 0.0,
                     "vega": vega})
    return pd.DataFrame(rows)


def _card(strike, expiry, *, dte=45, lane_fields=None, grades=None,
          rank_leader=False, risk=None, preview=False):
    card = {"strike": strike, "expiry": expiry, "dte": dte,
            "rank_leader": rank_leader, "grades": grades or {}}
    if risk is not None:
        card["risk"] = risk
    if preview:
        card["preview"] = True
    card.update(lane_fields or {})
    return card


class EarningsUnknownTests(unittest.TestCase):
    def test_ladder_marks_unknown_beyond_coverage_horizon(self):
        """Calendar's last entry 2026-05-01 + 98d coverage = 2026-08-07: the
        07-17 bucket is credibly covered (GREEN); the 09-18 bucket is beyond
        coverage with no known date in cycle (UNKNOWN, never GREEN)."""
        from datetime import date

        from options_researcher.attractiveness import ladder_cards, put_card_rows
        chain = pd.concat([
            chain_rows([("P", 150.0, -0.20, 2.00)], exp="2026-07-17"),
            chain_rows([("P", 150.0, -0.20, 5.00)], exp="2026-09-18"),
        ], ignore_index=True)
        rows = ladder_cards(put_card_rows, "VST", chain, "2026-06-30",
                            rank_key="annualized_yield", higher_is_better=True,
                            close=160.0, rv21=0.50, iv_rank=0.62,
                            iv_minus_rv=0.04,
                            earnings_dates=[date(2026, 5, 1)],
                            fomc_dates=[])
        by_expiry = {r["expiry"]: r for r in rows}
        self.assertEqual(by_expiry["2026-07-17"]["grades"]["earnings"],
                         "GREEN")
        self.assertEqual(by_expiry["2026-09-18"]["grades"]["earnings"],
                         "UNKNOWN")

    def test_in_cycle_beats_unknown(self):
        from options_researcher.attractiveness import put_card_rows
        chain = chain_rows([("P", 150.0, -0.20, 2.00)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=True, fomc_in_cycle=False,
                             earnings_unknown=True)
        self.assertEqual(rows[0]["grades"]["earnings"], "AMBER")

    def test_builder_unknown_flag_grades_unknown(self):
        from options_researcher.attractiveness import put_card_rows
        chain = chain_rows([("P", 150.0, -0.20, 2.00)])
        rows = put_card_rows("VST", chain, "2026-06-30", close=160.0,
                             rv21=0.50, iv_rank=0.62, iv_minus_rv=0.04,
                             earnings_in_cycle=False, fomc_in_cycle=False,
                             earnings_unknown=True)
        self.assertEqual(rows[0]["grades"]["earnings"], "UNKNOWN")


class RiskEconomicsTests(unittest.TestCase):
    def test_put_worst_case_is_strike_minus_credit(self):
        r = ad.risk_economics({"strike": 225.0, "credit": 494.35}, "put",
                              close=255.0)
        self.assertAlmostEqual(r["capital_required"], 22500.0)
        self.assertAlmostEqual(r["max_loss"], 22005.65)
        self.assertAlmostEqual(r["breakeven"], 220.06, places=2)

    def test_cc_worst_case_counts_the_share_leg(self):
        r = ad.risk_economics({"strike": 110.0, "credit": 150.0}, "cc",
                              close=100.0)
        self.assertAlmostEqual(r["capital_required"], 0.0)
        self.assertAlmostEqual(r["max_loss"], 9850.0)
        self.assertAlmostEqual(r["breakeven"], 98.50)

    def test_pmcc_full_structure_economics(self):
        card = {"strike": 470.0, "credit": 647.8,
                "leaps_strike": 360.0, "leaps_cost": 8151.0}
        r = ad.risk_economics(card, "pmcc", close=395.0)
        self.assertAlmostEqual(r["max_loss"], 8151.0 - 647.8)
        self.assertAlmostEqual(r["breakeven"], 360.0 + (8151.0 - 647.8) / 100,
                               places=2)
        self.assertAlmostEqual(r["max_profit"],
                               (470 - 360) * 100 - 8151.0 + 647.8)

    def test_long_call_max_loss_is_cost(self):
        r = ad.risk_economics({"cost": 440.0, "breakeven": 264.4},
                              "long_call", close=255.0)
        self.assertAlmostEqual(r["max_loss"], 440.0)
        self.assertAlmostEqual(r["capital_required"], 440.0)


class PmccPreviewPnlTests(unittest.TestCase):
    def test_preview_bbb_includes_the_long_leg_loss(self):
        """Below the LEAPS strike the preview P&L must show the LEAPS wipeout,
        not credit-only optimism."""
        card = {"strike": 470.0, "credit": 600.0, "dte": 30,
                "leaps_strike": 360.0, "leaps_cost": 8000.0, "preview": True}
        rows = ad.bbb_rows(card, "pmcc", close=395.0, rv21=0.40)
        bear = next(r for r in rows if r["scenario"] == "bear")
        # bear price ~349.4 < 360: LEAPS worthless -> -8000 + 600 credit
        self.assertAlmostEqual(bear["pnl"], -7400.0)
        self.assertIn("two-leg", bear["note"])

    def test_held_pmcc_keeps_credit_only_view_with_note(self):
        card = {"strike": 470.0, "credit": 600.0, "dte": 30,
                "leaps_strike": 360.0, "leaps_cost": 8000.0}
        rows = ad.bbb_rows(card, "pmcc", close=395.0, rv21=0.40)
        bear = next(r for r in rows if r["scenario"] == "bear")
        self.assertAlmostEqual(bear["pnl"], 600.0)
        self.assertIn("LEAPS value not counted", bear["note"])


def _sec(symbol, groups, *, technicals=None, close=100.0, stale=None):
    sec = {"symbol": symbol, "close": close, "iv_rank": 0.5,
           "as_of": "2026-07-15", "groups": groups}
    if technicals is not None:
        sec["technicals"] = technicals
    if stale is not None:
        sec["features_stale"] = stale
        sec["features_as_of"] = "2026-06-30" if stale else "2026-07-15"
    return sec


def _grp(kind, cards, *, preview=None):
    grp = {"kind": kind, "title": kind.upper(), "empty": None, "cards": cards}
    if preview is not None:
        grp["preview"] = preview
    return grp


class PolicyVetoTests(unittest.TestCase):
    def _fit_card(self, **kw):
        return _card(105.0, "2026-08-21",
                     grades={"fits_cap": "GREEN", "liquidity": "GREEN"},
                     lane_fields={"cost": 400.0, "breakeven": 109.0,
                                  "breakeven_move": 0.09},
                     risk={"capital_required": 400.0, "max_loss": 400.0,
                           "breakeven": 109.0}, **kw)

    def _big_card(self, **kw):
        return _card(95.0, "2026-08-21", rank_leader=True,
                     grades={"yield": "GREEN", "cushion": "GREEN",
                             "liquidity": "GREEN"},
                     lane_fields={"credit": 500.0, "annualized_yield": 0.30},
                     risk={"capital_required": 9500.0, "max_loss": 9000.0,
                           "breakeven": 90.0}, **kw)

    def test_universal_policy_veto_no_longer_excludes_cash_secured_puts(self):
        data = {"symbols": [_sec("AAA", [
            _grp("put", [self._big_card()]),
            _grp("long_call", [self._fit_card()])])]}
        picks = ad.select_top_picks(data)
        # The big-assignment CSP is NOT vetoed by the long-call cap; it wins
        # its symbol's slot outright (one pick per symbol keeps the second
        # lane off the hero).
        self.assertEqual([(p["lane"], p["strike"]) for p in picks],
                         [("put", 95.0)])

    def test_legacy_policy_veto_argument_is_a_noop(self):
        data = {"symbols": [_sec("AAA", [_grp("put", [self._big_card()])])]}
        picks = ad.select_top_picks(data)
        with_legacy_argument = ad.select_top_picks(data, policy_veto=False)
        self.assertEqual(len(picks), 1)
        self.assertEqual(picks, with_legacy_argument)

    def test_cards_without_risk_are_never_vetoed(self):
        data = {"symbols": [_sec("AAA", [_grp("put", [
            _card(95.0, "2026-08-21",
                  grades={"yield": "GREEN", "liquidity": "GREEN"},
                  lane_fields={"credit": 500.0,
                               "annualized_yield": 0.30})])])]}
        self.assertEqual(len(ad.select_top_picks(data)), 1)

    def test_paper_hero_can_show_only_assignment_capital_watch(self):
        candidate = self._big_card()
        candidate["top3_snapshot"] = {
            "rank_eligible": False,
            "selection_status": "WATCH",
            "policy": {"reason_codes": [
                "CSP_ASSIGNMENT_CAPITAL_UNCONFIRMED"]},
        }
        data = {"symbols": [_sec("AMZN", [_grp("put", [candidate])])]}
        self.assertEqual(ad.select_top_picks(data), [])
        picks = ad.select_top_picks(data, include_csp_watch=True)
        self.assertEqual([(pick["lane"], pick["strike"]) for pick in picks],
                         [("put", 95.0)])

    def test_structural_pmcc_preview_never_competes(self):
        pm = _card(120.0, "2026-08-21",
                   grades={"yield": "GREEN", "liquidity": "GREEN"},
                   lane_fields={"credit": 300.0, "annualized_yield": 0.40},
                   risk={"capital_required": 100.0, "max_loss": 100.0,
                         "breakeven": 101.0})
        data = {"symbols": [_sec("AAA", [_grp("pmcc", [pm], preview=True)])]}
        pm["top3_snapshot"] = {"rank_eligible": False}
        self.assertEqual(ad.select_top_picks(data), [])
        del pm["top3_snapshot"]
        data2 = {"symbols": [_sec("AAA", [_grp("pmcc", [pm], preview=False)])]}
        self.assertEqual(len(ad.select_top_picks(data2)), 1)

    def test_stale_features_section_never_competes(self):
        data = {"symbols": [
            _sec("AAA", [_grp("long_call", [self._fit_card()])], stale=True)]}
        data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"] = {
            "rank_eligible": False}
        self.assertEqual(ad.select_top_picks(data), [])

    def test_assemble_adds_risk_and_lane_specific_policy_badge(self):
        put = _card(95.0, "2026-08-21",
                    grades={"yield": "GREEN", "liquidity": "GREEN"},
                    lane_fields={"credit": 500.0, "annualized_yield": 0.30,
                                 "verdict": "v"})
        data = ad.assemble(
            symbol_sections=[_sec("AAA", [_grp("put", [put])])],
            rv21_by_symbol={"AAA": 0.4})
        card = data["symbols"][0]["groups"][0]["cards"][0]
        self.assertEqual(card["grades"]["portfolio"], "RED")
        self.assertEqual(card["top3_snapshot"]["policy"]["status"],
                         "PLAN_ONLY")
        self.assertAlmostEqual(card["risk"]["max_loss"], 9000.0)


class RenderHonestyTests(unittest.TestCase):
    def _data_one_fit_one_big(self):
        fit = _card(105.0, "2026-08-21",
                    grades={"fits_cap": "GREEN", "liquidity": "GREEN",
                            "fits_policy": "GREEN"},
                    lane_fields={"cost": 400.0, "breakeven": 109.0,
                                 "breakeven_move": 0.09, "headline": "H-FIT",
                                 "scenarios": [], "bbb": []},
                    risk={"capital_required": 400.0, "max_loss": 400.0,
                          "breakeven": 109.0})
        big = _card(95.0, "2026-08-21", rank_leader=True,
                    grades={"yield": "GREEN", "liquidity": "GREEN",
                            "fits_policy": "RED"},
                    lane_fields={"credit": 500.0, "annualized_yield": 0.30,
                                 "headline": "H-BIG", "scenarios": [],
                                 "bbb": []},
                    risk={"capital_required": 22500.0, "max_loss": 22005.65,
                          "breakeven": 220.06})
        return {"data_as_of": "2026-07-15", "symbols": [
            _sec("AAA", [_grp("put", [big]), _grp("long_call", [fit])])]}

    def test_only_n_fit_note_and_risk_lines(self):
        html = ad.render(self._data_one_fit_one_big())
        self.assertIn("TOP 3 PICKS TODAY", html)
        self.assertNotIn("EXCEEDS the $600/trade hard cap", html)
        self.assertIn("worst case -$22,006 at expiration", html)
        self.assertIn("vs $14,000 sleeve", html)

    def test_no_candidate_fits_fallback_is_loud(self):
        data = self._data_one_fit_one_big()
        del data["symbols"][0]["groups"][1]          # only the big put remains
        data["symbols"][0]["groups"][0]["cards"][0]["top3_snapshot"] = {
            "rank_eligible": False}
        html = ad.render(data)
        self.assertIn("No qualifying contract", html)
        self.assertIn("This is an intentional open slot", html)

    def test_partial_top3_keeps_three_visible_slots_in_each_list(self):
        html = ad.render(self._data_one_fit_one_big())
        self.assertEqual(html.count('<div class="hero-card '), 6)
        self.assertIn("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 3", html)
        self.assertIn("Rule-based top 3 — best policy-and-liquidity fit today", html)
        self.assertIn("Pick 3", html)
        self.assertIn("No qualifying contract", html)
        self.assertIn("not missing UI", html)

    def test_open_slot_explains_actual_liquidity_and_policy_gates(self):
        data = {"symbols": [
            {"symbol": "VST", "groups": [{"kind": "long_call", "cards": [{
                "strike": 165.0,
                "grades": {"liquidity": "RED"},
                "top3_snapshot": {
                    "rank_eligible": True,
                    "policy": {"status": "ELIGIBLE", "reason_codes": []},
                },
            }]}]},
            {"symbol": "MSFT", "groups": [{"kind": "put", "cards": [{
                "strike": 350.0,
                "grades": {"liquidity": "GREEN"},
                "top3_snapshot": {
                    "rank_eligible": False,
                    "policy": {"status": "PLAN_ONLY", "reason_codes": [
                        "CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES"]},
                },
            }]}]},
        ]}
        reasons = ad._top3_gap_reasons(data)
        self.assertIn("VST $165 call passes portfolio policy but fails liquidity.",
                      reasons)
        self.assertIn("MSFT puts are plan-only outside the registered "
                      "cash-secured-put names.", reasons)

    def test_status_badges_pair_semantic_color_with_text_and_symbol(self):
        html = ad._badges({"policy": "GREEN", "event": "AMBER",
                           "liquidity": "RED", "source": "UNKNOWN"})
        self.assertIn('class="status-badge good">✓ policy · GREEN', html)
        self.assertIn('class="status-badge watch">! event · AMBER', html)
        self.assertIn('class="status-badge bad">× liquidity · RED', html)
        self.assertIn('class="status-badge unknown">? source · UNKNOWN', html)

    def test_stale_features_warning_rendered(self):
        data = self._data_one_fit_one_big()
        data["symbols"][0]["features_stale"] = True
        data["symbols"][0]["features_as_of"] = "2026-06-30"
        html = ad.render(data)
        self.assertIn("IV features are from 2026-06-30", html)
        self.assertIn("excluded from the Top-3 shortlist", html)

    def test_preview_card_warns_two_leg(self):
        pm = _card(470.0, "2026-09-18",
                   grades={"liquidity": "GREEN", "fits_policy": "RED"},
                   lane_fields={"credit": 600.0, "annualized_yield": 0.4,
                                "headline": "H-PM", "scenarios": [],
                                "bbb": []},
                   risk={"capital_required": 8000.0, "max_loss": 7400.0,
                         "breakeven": 434.0, "max_profit": 3600.0},
                   preview=True)
        data = {"data_as_of": "2026-07-15", "symbols": [
            _sec("AAA", [_grp("pmcc", [pm], preview=True)])]}
        html = ad.render(data)
        self.assertIn("two-leg preview", html)
        self.assertIn("max profit $3,600", html)

    def test_sources_and_research_date_rendered(self):
        data = self._data_one_fit_one_big()
        context = {"provenance": "LLM-asserted (test)",
                   "researched_on": "2026-07-16",
                   "symbols": {"AAA": {
                       "news_summary": "news here",
                       "catalysts": [{"date": None, "what": "thing",
                                      "confirmed": False, "source": "x"}],
                       "sources": ["https://example.com/a", "not-a-url"]}}}
        html = ad.render(data, context=context)
        self.assertIn('href="https://example.com/a"', html)
        self.assertIn("sources (2)", html)
        self.assertIn("[UNCONFIRMED/estimated]", html)


if __name__ == "__main__":
    unittest.main()

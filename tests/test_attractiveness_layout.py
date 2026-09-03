"""tests/test_attractiveness_layout.py

Display-only layout contract for the attractiveness board (2026-09-03).

Nothing here may assert a ranking, a signal, or an authority change: every
test below is about WHERE a fact is printed and how many times, never about
what the fact is.  The authority/disclaimer sentences are asserted verbatim
so a layout edit can never quietly drop one.
"""
import re
import unittest

import config
from options_researcher import attractiveness_dashboard as ad
from options_researcher.schwab_chain_view import (
    CHAIN_SOURCE,
    CONVENTION_LABEL,
    THETADATA_CHAIN_SOURCE,
)


def _put_section(symbol, *, as_of="2026-08-25", chain_source=THETADATA_CHAIN_SOURCE,
                 credit=100.0, **overrides):
    section = {
        "symbol": symbol,
        "as_of": as_of,
        "close": 100.0,
        "iv_rank": 0.5,
        "chain_source": chain_source,
        "close_as_of": as_of,
        "close_kind": "eod_close",
        "features_as_of": as_of,
        "features_stale": False,
        "groups": [{
            "kind": "put",
            "title": "SELL A PUT?",
            "cards": [{
                "strike": 95.0,
                "expiry": "2026-09-18",
                "dte": 24,
                "credit": credit,
                "annualized_yield": 0.30,
                "cushion": 0.05,
                "grades": {"yield": "GREEN", "liquidity": "GREEN"},
                "verdict": "display only",
            }],
            "empty": None,
        }],
    }
    section.update(overrides)
    return section


def _board(symbols, *, eligible=True, today="2026-08-25", **assemble_kwargs):
    data = ad.assemble(
        symbol_sections=[_put_section(symbol) for symbol in symbols],
        rv21_by_symbol={},
        today=today,
        composite_signals=[],
        **assemble_kwargs,
    )
    if eligible:
        for section in data["symbols"]:
            section["groups"][0]["cards"][0]["top3_snapshot"].update({
                "rank_eligible": True,
                "selection_status": "ELIGIBLE",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            })
    return data


def _composite_card(symbol, *, grade="A", trend="UP", vol="RICH",
                    regime="TYPICAL", internals="CONFIRM", as_of="2026-08-25"):
    return {
        "symbol": symbol,
        "grade": grade,
        "max_asof": as_of,
        "trend": {"state": trend, "data_blocked": trend == "DATA_BLOCKED"},
        "vol_premium": {"state": vol, "data_blocked": False},
        "regime": {"state": regime, "data_blocked": False},
        "internals": {"state": internals, "data_blocked": False},
    }


class EmptySlotConsolidationTests(unittest.TestCase):
    """Five byte-identical 'OPEN' cards are one fact printed five times."""

    def test_all_open_rule_based_slots_collapse_into_one_block(self):
        html = ad.render(_board(["AAA"], eligible=False))
        hero = html[html.index("Rule-based top 5"):html.index("Context-aware Top 5")]

        self.assertEqual(hero.count("empty-slot"), 1)
        self.assertIn(f"{config.PICK_TOP_N} of {config.PICK_TOP_N} slots open", hero)
        self.assertIn("No qualifying contract", hero)
        # The gate reasons themselves must survive the collapse.
        self.assertIn("This is an intentional open slot, not missing UI.", hero)
        self.assertIn(
            "A blocked or illiquid idea is never promoted just to fill the list.",
            hero,
        )

    def test_single_open_slot_is_not_consolidated(self):
        data = _board([f"S{index}" for index in range(config.PICK_TOP_N - 1)])
        html = ad.render(data)
        hero = html[html.index("Rule-based top 5"):html.index("Context-aware Top 5")]

        self.assertEqual(hero.count("empty-slot"), 1)
        self.assertIn(f"<span>Pick {config.PICK_TOP_N}</span>", hero)
        self.assertNotIn("slots open", hero)

    def test_context_lane_open_slots_collapse_and_keep_counters(self):
        html = ad.render(_board(["AAA"]))
        lane = html[
            html.index("Context-aware Top 5"):
            html.index("Frozen-shortlist comparison diagnostics")
        ]

        self.assertEqual(lane.count("empty-slot"), 1)
        self.assertIn(f"{config.PICK_TOP_N - 1} of {config.PICK_TOP_N} slots open", lane)
        self.assertIn("The full admissible pool did not supply another symbol.", lane)

    def test_blocked_qm_slots_collapse_into_one_block(self):
        html = ad.render(_board(["AAA"]), qm_context={"status": "DATA_BLOCKED"})
        qm = html[html.index("QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5"):]

        self.assertEqual(qm.count("DATA BLOCKED"), 1)
        self.assertIn(f"{config.PICK_TOP_N} of {config.PICK_TOP_N} slots open", qm)
        self.assertIn("QM context withheld", qm)

    def test_shortlist_counters_still_report_every_slot(self):
        html = ad.render(_board(["AAA"], eligible=False))
        hero = html[html.index("Rule-based top 5"):html.index("Context-aware Top 5")]

        self.assertIn("<span>Eligible</span>", hero)
        self.assertIn("<span>Watch</span>", hero)
        self.assertIn(f"<strong>{config.PICK_TOP_N}</strong><span>Open</span>", hero)


class PositionsAndRiskFirstTests(unittest.TestCase):
    """The paper book's open risk is the first thing the board says."""

    def _positions(self, **overrides):
        payload = {
            "rows": [
                {
                    "book": "H6",
                    "identifier": "H6-0001",
                    "text": "H6-0001 NVDA $220.00 call · exp 2026-09-18 · "
                            "entered 2026-07-13",
                },
                {
                    "book": "shares",
                    "identifier": "VST",
                    "text": "VST 39 shares · cost basis $142.28 · acquired 2026-06-15",
                },
            ],
            "missing_sources": [],
            "sources": ["data/positions/h6_positions.csv",
                        "data/positions/holdings.csv"],
            "h6_last_mark": "2026-07-27",
        }
        payload.update(overrides)
        return payload

    def test_tracker_renders_before_the_shortlist_with_positions_kicker(self):
        data = _board(["AAA"])
        data["open_positions"] = self._positions()
        html = ad.render(data)

        self.assertLess(html.index("REGISTERED-BETS TRACKER"),
                        html.index("Rule-based top 5"))
        self.assertLess(html.index("DATA FRESHNESS"),
                        html.index("REGISTERED-BETS TRACKER"))
        self.assertIn("POSITIONS &amp; RISK", html)
        # The tracker's authority sentence is unchanged by the move.
        self.assertIn("This is a read-only receipt summary and cannot activate, "
                      "rank, or place a trade.", html)

    def test_open_positions_render_one_line_each_from_the_book(self):
        data = _board(["AAA"])
        data["open_positions"] = self._positions()
        html = ad.render(data)
        block = html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]

        self.assertIn("H6-0001 NVDA $220.00 call", block)
        self.assertIn("exp 2026-09-18", block)
        self.assertIn("entered 2026-07-13", block)
        self.assertIn("VST 39 shares", block)
        self.assertEqual(block.count('class="open-position"'), 2)

    def test_stale_last_mark_is_flagged_with_its_age(self):
        data = _board(["AAA"], today="2026-08-25")
        data["open_positions"] = self._positions()
        html = ad.render(data)
        block = html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]

        self.assertIn("last mark 2026-07-27", block)
        self.assertRegex(block, r"last mark 2026-07-27 \(\d+ sessions ago\)")

    def test_current_last_mark_makes_no_age_claim(self):
        data = _board(["AAA"], today="2026-07-27")
        data["open_positions"] = self._positions()
        html = ad.render(data)
        block = html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]

        self.assertNotIn("sessions ago", block)

    def test_missing_position_source_says_so_and_never_invents_a_row(self):
        data = _board(["AAA"])
        data["open_positions"] = self._positions(
            rows=[], missing_sources=["data/positions/holdings.csv"],
            h6_last_mark=None)
        html = ad.render(data)
        block = html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]

        self.assertIn("data/positions/holdings.csv", block)
        self.assertIn("could not be read", block)
        self.assertEqual(block.count('class="open-position"'), 0)

    def test_unread_position_sources_are_declared_not_assumed_empty(self):
        html = ad.render(_board(["AAA"]))
        block = html[html.index("POSITIONS &amp; RISK"):html.index("Rule-based top 5")]

        self.assertIn("not read for this render", block)
        self.assertNotIn("No open paper positions", block)

    def test_position_loader_reads_the_paper_book_without_fabricating(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            positions = root / "data" / "positions"
            positions.mkdir(parents=True)
            (positions / "h6_positions.csv").write_text(
                "id,symbol,strike,expiration,contracts,entry_date,entry_cost,"
                "entry_receipt_hash,exit_date,exit_proceeds,exit_reason,"
                "exit_receipt_hash\n"
                "H6-0001,NVDA,220.0,2026-09-18,1,2026-07-13,920.65,abc,,,,\n"
                "H6-0002,PLTR,90.0,2026-08-21,1,2026-06-02,300.0,def,"
                "2026-07-01,400.0,take_profit,ghi\n"
            )
            loaded = ad.load_open_positions(root=root)

        identifiers = [row["identifier"] for row in loaded["rows"]]
        self.assertEqual(identifiers, ["H6-0001"])  # the closed leg is not open
        self.assertIn("data/positions/holdings.csv", loaded["missing_sources"])
        self.assertIsNone(loaded["h6_last_mark"])


class SymbolPanelCollapseTests(unittest.TestCase):
    """Eighteen expanded panels are a scroll, not a board."""

    def _data(self, chain_source=CHAIN_SOURCE,
              close_kind="preclose_mid_1545", **section_kwargs):
        # A uniformly fresh board so no panel is force-opened by the
        # fail-visible STALE rule; collapse is then the only thing under test.
        data = ad.assemble(
            symbol_sections=[
                _put_section(symbol, chain_source=chain_source,
                             close_kind=close_kind,
                             technicals_as_of="2026-08-25", **section_kwargs)
                for symbol in ("VST", "NVDA", "MSFT")
            ],
            rv21_by_symbol={},
            today="2026-08-25",
            composite_signals=[],
        )
        for section in data["symbols"]:
            section["groups"][0]["cards"][0]["top3_snapshot"].update({
                "rank_eligible": True,
                "selection_status": "ELIGIBLE",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            })
        return data

    def test_clean_panels_are_closed_except_owner_pinned_symbols(self):
        html = ad.render(self._data())
        panels = re.findall(r'<details class="panel symbol-panel"( open)?>', html)

        self.assertEqual(len(panels), 3)
        self.assertEqual(sum(1 for panel in panels if panel), 1)  # VST only
        vst = html[html.index('id="symbol-VST"'):html.index('id="symbol-NVDA"')]
        self.assertIn('<details class="panel symbol-panel" open>', vst)

    def test_panel_summary_is_one_line_with_source_asof_and_grade(self):
        html = ad.render(self._data())
        start = html.index('id="symbol-MSFT"')
        summary = html[start:html.index("</summary>", start)]

        self.assertIn("MSFT", summary)
        self.assertIn(f"{CONVENTION_LABEL} 2026-08-25", summary)
        self.assertRegex(summary, r"GREEN \d+/\d+")
        self.assertNotIn("<h2>", summary)

    def test_frozen_eod_panels_name_their_source_in_the_summary(self):
        html = ad.render(self._data(chain_source=THETADATA_CHAIN_SOURCE,
                                    close_kind="eod_close"))
        start = html.index('id="symbol-NVDA"')
        summary = html[start:html.index("</summary>", start)]

        self.assertIn("frozen EOD 2026-08-25", summary)

    def test_symbol_heading_text_is_unchanged_inside_the_panel(self):
        html = ad.render(self._data())
        start = html.index('id="symbol-NVDA"')
        body = html[html.index("</summary>", start):html.index("</details>", start)]

        self.assertIn('<div class="eyebrow">Symbol review</div>', body)
        self.assertIn("<h2>NVDA</h2>", body)


class StickyNavTests(unittest.TestCase):
    def test_nav_links_every_present_section_and_symbol(self):
        data = _board(["VST", "NVDA"])
        html = ad.render(data)
        nav = html[html.index('class="sticky-nav"'):html.index("</nav>")]

        self.assertIn("position: sticky", html)
        for anchor in ("#positions-and-risk", "#rule-based-top-5",
                       "#composite-board", "#pick-tracker", "#diagnostics"):
            self.assertIn(f'href="{anchor}"', nav)
        self.assertIn('href="#symbol-VST"', nav)
        self.assertIn('href="#symbol-NVDA"', nav)

    def test_nav_never_links_a_section_that_is_not_on_the_page(self):
        from unittest import mock

        with mock.patch.object(config, "CONTEXT_LANE_ENABLED", False):
            html = ad.render(_board(["AAA"]))
        nav = html[html.index('class="sticky-nav"'):html.index("</nav>")]

        self.assertNotIn('href="#context-aware-top-5"', nav)


class CompositeTableTests(unittest.TestCase):
    def test_composite_board_is_one_table_with_every_label_preserved(self):
        data = _board(["AAA"])
        data["composite_signals"] = [
            _composite_card("AAA"),
            _composite_card("BBB", grade="B", trend="MIXED", vol="CHEAP",
                            regime="HIGH_DISPERSION", internals="VETO"),
            _composite_card("CCC", grade="C", trend="DOWN", vol="NEUTRAL",
                            internals="NEUTRAL"),
        ]
        html = ad.render(data)
        board = html[html.index("Composite signal board"):]
        board = board[:board.index("</section>")]

        self.assertIn("<table", board)
        self.assertEqual(board.count("<tr"), 4)  # header + one row per name
        for header in ("Symbol", "Grade", "Trend", "Vol", "Regime",
                       "Internals", "as of"):
            self.assertIn(header, board)
        for label in ("GRADE A", "GRADE B", "GRADE C", "TREND UP", "TREND DOWN",
                      "TREND MIXED", "VOL RICH", "VOL CHEAP", "VOL NEUTRAL",
                      "REGIME TYPICAL", "REGIME HIGH_DISPERSION",
                      "INTERNALS CONFIRM", "INTERNALS VETO",
                      "INTERNALS NEUTRAL", "as of 2026-08-25"):
            self.assertIn(label, board)
        self.assertIn("Highest agreement today: AAA", board)
        self.assertIn("Not verdict-bearing, not FIRE-capable", board)

    def test_blocked_angle_reason_is_still_printed(self):
        data = _board(["AAA"])
        blocked = _composite_card("AAA", trend="DATA_BLOCKED")
        blocked["trend"]["reason"] = "no cached closes (FileNotFoundError)"
        data["composite_signals"] = [blocked]
        html = ad.render(data)

        self.assertIn("no cached closes (FileNotFoundError)", html)


class DiagnosticsDrawerTests(unittest.TestCase):
    _DRAWER_SECTIONS = (
        "QM MOVEMENT LANE",
        "QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 5",
        "Research context and coverage",
        "Passive research views",
        "Quant-want background",
        "Market context",
    )

    def _rendered(self):
        data = _board(["AAA"])
        context = {
            "as_of": "2026-08-25",
            "researched_on": "2026-08-25",
            "provenance": "fixture provenance",
            "market": {"summary": "Fixture market context.", "regime": "mixed"},
            "symbols": {"AAA": {"news_summary": "covered"}},
        }
        return ad.render(
            data,
            context=context,
            qm_context={
                "status": "DATA_BLOCKED",
                "quant_want": {"trend": {"status": "UP",
                                         "plain_language": "fixture trend"}},
                "source_commit": "fixture",
            },
            research_views_status={"state": "absent"},
        )

    def test_drawer_is_closed_and_holds_the_six_diagnostic_sections(self):
        html = self._rendered()
        drawer_open = html.index('class="panel diagnostics-drawer"')

        self.assertIn('<details class="panel diagnostics-drawer" id="diagnostics">',
                      html)
        self.assertIn("Diagnostics &amp; provenance", html)
        offsets = [html.index(section) for section in self._DRAWER_SECTIONS]
        self.assertTrue(all(offset > drawer_open for offset in offsets))
        self.assertEqual(offsets, sorted(offsets))  # relative order preserved

    def test_scoreboard_and_pinned_strip_stay_in_the_main_flow(self):
        html = self._rendered()
        drawer_open = html.index('class="panel diagnostics-drawer"')

        self.assertLess(html.index("Shortlist outcome scoreboard"), drawer_open)
        self.assertLess(html.index("Rule-based top 5"),
                        html.index("Shortlist outcome scoreboard"))

    def test_symbol_panels_precede_the_drawer(self):
        html = self._rendered()

        self.assertLess(html.index('id="symbol-AAA"'),
                        html.index('class="panel diagnostics-drawer"'))


class AuthorityWordingSurvivesLayoutTests(unittest.TestCase):
    """Every authority/disclaimer sentence must survive the redesign verbatim."""

    _SENTENCES = (
        "Composite signal board — display-only",
        "Not verdict-bearing, not FIRE-capable; writes nothing to ledger/ or "
        "positions.",
        "This is a read-only receipt summary and cannot activate, rank, or "
        "place a trade.",
        "Descriptive only; no verdict, ranking, sizing, or trade authority.",
        "DESCRIPTIVE ONLY — NOT A TRADE RANKING",
        "QM does not select, rank, validate, or change the edge or verdict of "
        "any option contract.",
        "This does not select, order, gate, or validate a mechanical pick.",
        "Experimental re-ordering by market context. The rule-based list above "
        "is the registered baseline. This lane is display-only and carries no "
        "verdict or trade authority; once the pick tracker is live its picks "
        "will be tracked descriptively against the baseline.",
        "owner-pinned visibility — not ranked; these cards do not compete with "
        "or reorder the Top-5 shortlist.",
        "This is a fit ranking, not a prediction",
        "Trend does not rank these contracts.",
        "Payoffs are at-expiration scenarios, not predictions.",
    )

    def test_disclaimers_are_present_verbatim(self):
        data = _board(["VST", "AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        html = ad.render(
            data,
            context={"as_of": "2026-08-25", "provenance": "fixture",
                     "market": {"summary": "Fixture."}, "symbols": {}},
            qm_context={
                "status": "DATA_BLOCKED",
                "quant_want": {"trend": {"status": "UP",
                                         "plain_language": "fixture trend"}},
                "source_commit": "fixture",
            },
            research_views_status={"state": "absent"},
        )
        for sentence in self._SENTENCES:
            with self.subTest(sentence=sentence[:48]):
                self.assertIn(sentence, html)


class PickTrackerBindingTests(unittest.TestCase):
    """The tracker's source-row digest must still bind the new HTML."""

    def test_digest_comment_round_trips_through_the_new_layout(self):
        from options_researcher import pick_tracker

        html = ad.render(_board(["AAA"]))
        digest = "a" * 64
        bound = pick_tracker._bind_source_rows_html(html.encode(), digest)

        self.assertEqual(pick_tracker._html_source_rows_digest(bound), digest)
        self.assertIn(b"<!-- pick-tracker-source-rows-sha256:", bound)
        self.assertTrue(bound.decode().startswith("<!doctype html>"))

    def test_layout_adds_no_second_html_comment_that_could_shadow_the_digest(self):
        html = ad.render(_board(["AAA"]))

        self.assertEqual(html.count("<!--"), 0)


class NoScriptTests(unittest.TestCase):
    def test_board_stays_javascript_free(self):
        data = _board(["AAA"])
        data["composite_signals"] = [_composite_card("AAA")]
        html = ad.render(data)

        self.assertNotIn("<script", html.lower())
        self.assertNotIn("onclick", html.lower())


if __name__ == "__main__":  # pragma: no cover - manual runs
    unittest.main()

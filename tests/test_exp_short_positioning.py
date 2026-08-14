"""EXP-SHORT lane tests.

The lane is disabled by default. When enabled it reads local validated
artifacts only, keeps every failure visible, and leaves the existing lanes and
the production ranking untouched.
"""

from __future__ import annotations

import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import config
from options_researcher import exp_short_positioning as lane
from options_researcher import experiments_dashboard as dashboard
from options_researcher.short_positioning_context import (
    CARD_CAVEAT,
    DAYS_TO_COVER_NOTE,
    LANE_HEADING,
    LANE_TEXT,
    LANE_TITLE,
)

ASOF = "2026-07-21"
BUILD_BUDGET_SECONDS = 5.0


class LaneTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        patcher = mock.patch.object(config, "SHORT_POSITIONING_ROOT", str(self.root))
        patcher.start()
        self.addCleanup(patcher.stop)

    def enabled(self):
        return mock.patch.object(config, "SHORT_CONTEXT_ENABLED", True)


class BoardTests(LaneTestCase):
    def test_the_default_configuration_keeps_the_lane_off(self):
        self.assertIs(config.SHORT_CONTEXT_ENABLED, False)
        self.assertEqual(config.SHORT_POSITIONING_PROVIDER_ORDER, ("finra",))
        self.assertEqual(config.SHORT_POSITIONING_MAX_AGE_RELEASES, 1)

    def test_load_returns_nothing_while_disabled(self):
        self.assertIsNone(lane.load_exp_short_lane(["MSFT"], asof=ASOF))

    def test_load_returns_cards_when_enabled(self):
        with self.enabled():
            cards = lane.load_exp_short_lane(["MSFT", "AMZN"], asof=ASOF)
        assert cards is not None
        self.assertEqual([card.symbol for card in cards], ["MSFT", "AMZN"])

    def test_board_emits_one_visible_card_per_symbol_with_no_data(self):
        cards = lane.build_exp_short_board(["MSFT", "AMZN"], asof=ASOF)
        self.assertEqual(len(cards), 2)
        self.assertEqual({card.primary_status for card in cards}, {"NO_RECORD"})

    def test_a_failure_becomes_a_visible_error_card_not_an_empty_lane(self):
        with mock.patch.object(
            lane,
            "build_short_positioning_context",
            side_effect=RuntimeError("synthetic lane failure <unsafe>"),
        ):
            cards = lane.build_exp_short_board(["MSFT"], asof=ASOF)

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].primary_status, "SCHEMA_ERROR")
        self.assertEqual(cards[0].tone, "red")
        self.assertIn("synthetic lane failure", cards[0].explanation)

    def test_an_error_card_escapes_provider_controlled_text(self):
        with mock.patch.object(
            lane,
            "build_short_positioning_context",
            side_effect=RuntimeError("<script>alert(1)</script>"),
        ):
            cards = lane.build_exp_short_board(["MSFT"], asof=ASOF)
        html = lane.render_short_positioning_card(cards[0])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_the_full_universe_builds_inside_the_display_budget(self):
        started = time.monotonic()
        cards = lane.build_exp_short_board(list(config.ATTRACTIVENESS_UNIVERSE), asof=ASOF)
        elapsed = time.monotonic() - started
        self.assertEqual(len(cards), len(config.ATTRACTIVENESS_UNIVERSE))
        self.assertLess(elapsed, BUILD_BUDGET_SECONDS)

    def test_an_invalid_asof_is_a_visible_error_card(self):
        cards = lane.build_exp_short_board(["MSFT"], asof="not-a-date")
        self.assertEqual(cards[0].tone, "red")


class DashboardIntegrationTests(LaneTestCase):
    def test_disabled_render_contains_no_exp_short_text(self):
        data = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)
        html = dashboard.render(data, build_asof=ASOF)

        self.assertNotIn("exp_short", data)
        for fragment in (LANE_HEADING, LANE_TITLE, LANE_TEXT, CARD_CAVEAT, DAYS_TO_COVER_NOTE):
            self.assertNotIn(fragment, html)

    def test_enabled_render_shows_the_lane_with_its_exact_copy(self):
        with self.enabled():
            data = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)
            html = dashboard.render(data, build_asof=ASOF)

        self.assertIn("exp_short", data)
        for fragment in (LANE_HEADING, LANE_TITLE, LANE_TEXT, CARD_CAVEAT, DAYS_TO_COVER_NOTE):
            self.assertIn(fragment, html)

    def test_enabling_the_lane_leaves_the_existing_lanes_untouched(self):
        disabled = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)
        with self.enabled():
            enabled = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)

        for key in ("exp_beta", "exp_tail", "exp_spread", "exp_tbill"):
            self.assertEqual(disabled[key], enabled[key])

    def test_the_lane_never_uses_a_directional_good_badge(self):
        with self.enabled():
            data = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)
            html = dashboard.render(data, build_asof=ASOF)

        short_section = html[html.index(LANE_HEADING) :]
        self.assertNotIn("status-badge good", short_section)

    def test_the_lane_adds_no_ranking_or_verdict_language(self):
        with self.enabled():
            data = dashboard.build_experiment_lanes(["MSFT"], asof=ASOF)
            html = dashboard.render(data, build_asof=ASOF).lower()
        for banned in ("squeeze", "bullish", "bearish", "conviction", "opportunity"):
            self.assertNotIn(banned, html)


if __name__ == "__main__":
    unittest.main()

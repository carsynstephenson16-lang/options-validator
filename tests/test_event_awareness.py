"""Characterization and feature tests for Brief 28's display-only event layer."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import config
from options_researcher import attractiveness_dashboard as ad
from options_researcher import attractiveness_research_v2 as research
from options_researcher import event_calendar, fomc
from options_researcher.source_policy import BANNED_HOST_FRAGMENTS


def _event(**changes: object) -> dict[str, object]:
    event = {
        "event_id": "evt",
        "date": "2026-08-27",
        "time_et": "UNKNOWN",
        "kind": "other",
        "title": "Test event",
        "source_url": "https://fed.example/a",
        "source_kind": "official_gov",
        "verification": "fetched",
        "source_quote": "A short source sentence.",
        "captured_at": "2026-08-26T15:53:26Z",
        "added_by": "LLM-seeded-2026-08-25",
    }
    event.update(changes)
    return event


class EventCalendarTests(unittest.TestCase):
    """Each test names the production break it catches in its assertion."""

    def _load(self, rows: list[dict[str, object]]):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            return event_calendar.load_calendar(path)

    def test_source_policy_moves_without_changing_research_consumer(self):
        # Catches a split denylist where calendar and research disagree.
        self.assertIs(research.BANNED_HOST_FRAGMENTS, BANNED_HOST_FRAGMENTS)
        self.assertIn("reddit.", BANNED_HOST_FRAGMENTS)

    def test_schema_sorting_duplicate_banned_host_and_fetched_quote_are_enforced(self):
        # Catches accepting uncheckable fetched claims or unsafe calendar input.
        calendar = self._load(
            [_event(event_id="later", date="2026-08-28"), _event(event_id="early")]
        )
        self.assertEqual([item.event_id for item in calendar], ["early", "later"])
        with self.assertRaisesRegex(ValueError, "duplicate event_id"):
            self._load([_event(), _event()])
        with self.assertRaisesRegex(ValueError, "banned source host"):
            self._load([_event(source_url="https://reddit.com/event")])
        with self.assertRaisesRegex(ValueError, "source_quote"):
            self._load([_event(source_quote="")])

    def test_asserted_and_stale_markers_remain_visible(self):
        # Catches silently presenting unverified or stale claims as current.
        asserted = self._load([_event(verification="asserted", source_quote="")])[0]
        stale = self._load([_event(captured_at="2026-07-01T00:00:00Z")])[0]
        self.assertTrue(event_calendar.provenance_markers(asserted, date(2026, 8, 26))[0])
        self.assertIn(
            "re-verify source", event_calendar.provenance_markers(stale, date(2026, 8, 26))
        )

    def test_fomc_adapter_is_exactly_existing_source_without_duplicate_rows(self):
        # Catches a second FOMC calendar that can drift from load_fomc().
        calendar = event_calendar.calendar_with_fomc([], fomc.load_fomc())
        self.assertEqual([item.date for item in calendar], fomc.load_fomc())
        self.assertEqual(len(calendar), len({item.event_id for item in calendar}))

    def test_complex_map_rejects_future_membership(self):
        # Catches hindsight membership applied to an earlier event.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "complex.json"
            path.write_text(
                json.dumps(
                    {
                        "as_of": "2026-08-28",
                        "clusters": {"x": {"members": ["AAA"], "events_propagate_from": ["AAA"]}},
                    }
                )
            )
            with self.assertRaisesRegex(ValueError, "later than event"):
                event_calendar.load_complex_map(path, [self._load([_event()])[0]])

    def test_seed_files_are_valid_and_map_exactly_the_display_universe(self):
        # Catches a seed typo that silently drops or adds complex members.
        calendar = event_calendar.load_calendar()
        complex_map = event_calendar.load_complex_map(
            events=[item for item in calendar if item.date >= date(2026, 8, 25)]
        )
        self.assertEqual(len(calendar), 7)
        self.assertEqual(
            set(complex_map["clusters"]["ai_infra"]["members"]), set(config.ATTRACTIVENESS_UNIVERSE)
        )


class EventChipTests(unittest.TestCase):
    def setUp(self):
        self.calendar = self._calendar(
            [
                _event(event_id="nvda-results", date="2026-08-27"),
                _event(event_id="expiry", date="2026-08-30"),
            ]
        )

    @staticmethod
    def _calendar(rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.jsonl"
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
            return event_calendar.load_calendar(path)

    def test_life_window_edges_and_complex_propagation(self):
        # Catches expiry-day omissions, post-expiry chips, and self-as-complex lies.
        own = ad.event_chips(
            {"expiry": "2026-08-30"},
            "NVDA",
            "2026-08-26",
            self.calendar,
            {"clusters": {"x": {"members": ["NVDA", "MSFT"], "events_propagate_from": ["NVDA"]}}},
        )
        related = ad.event_chips(
            {"expiry": "2026-08-30"},
            "MSFT",
            "2026-08-26",
            self.calendar,
            {"clusters": {"x": {"members": ["NVDA", "MSFT"], "events_propagate_from": ["NVDA"]}}},
        )
        self.assertEqual([chip["marker"] for chip in own], ["cal", "cal"])
        self.assertIn("complex", [chip["marker"] for chip in related])
        self.assertEqual(
            ad.event_chips({"expiry": "2026-08-29"}, "NVDA", "2026-08-26", self.calendar, {}),
            [own[0]],
        )

    def test_pure_render_all_card_surfaces_and_failure_notice(self):
        # Catches event chips disappearing from hero/pinned/context or file I/O in render().
        card = {
            "headline": "NVDA call",
            "expiry": "2026-08-30",
            "strike": 100.0,
            "dte": 4,
            "grades": {},
            "scenarios": [],
            "bbb": [],
            "verdict": "x",
            "risk": {},
            "top3_snapshot": {
                "candidate_id": "nvda:long_call:1",
                "rank_eligible": True,
                "selection_status": "ELIGIBLE",
                "policy": {"status": "ELIGIBLE", "reason_codes": []},
            },
        }
        data = {
            "evaluation_date": "2026-08-26",
            "data_as_of": "2026-08-26",
            "symbols": [
                {
                    "symbol": "NVDA",
                    "as_of": "2026-08-26",
                    "close": 100.0,
                    "groups": [{"kind": "long_call", "title": "Calls", "cards": [card]}],
                }
            ],
            "blocked": [],
            "stale_symbols": [],
        }
        sections_before = ad.sections_json(data["symbols"]).encode()
        grades_before = [
            set(candidate["grades"])
            for group in data["symbols"][0]["groups"]
            for candidate in group["cards"]
        ]
        picks_before = ad.select_top_picks(data, include_csp_watch=True)
        view = {"calendar": self.calendar, "complex_map": {}, "implied_moves": {}, "failures": {}}
        with mock.patch("builtins.open", side_effect=AssertionError("render read file")):
            html = ad.render(data, event_view=view)
        self.assertGreaterEqual(html.count("event-chip"), 3)
        self.assertIn("EVENT", html)
        self.assertIn("event-chip-style", html)
        self.assertEqual(ad.sections_json(data["symbols"]).encode(), sections_before)
        self.assertEqual(
            [
                set(candidate["grades"])
                for group in data["symbols"][0]["groups"]
                for candidate in group["cards"]
            ],
            grades_before,
        )
        self.assertEqual(ad.select_top_picks(data, include_csp_watch=True), picks_before)
        failed = ad.render(
            data,
            event_view={
                "calendar": [],
                "complex_map": {},
                "implied_moves": {},
                "failures": {"NVDA": "ValueError"},
            },
        )
        self.assertIn("EVENT LAYER FAILED — ValueError", failed)

    def test_empty_view_is_prebrief_html_and_has_no_event_css(self):
        # Catches rollback changing page bytes or leaving unconditional event styling.
        data = {
            "evaluation_date": "2026-08-26",
            "data_as_of": "2026-08-26",
            "symbols": [],
            "blocked": [],
            "stale_symbols": [],
        }
        self.assertEqual(ad.render(data), ad.render(data, event_view=None))
        self.assertNotIn("event-chip-style", ad.render(data, event_view=None))


class ImpliedMoveTests(unittest.TestCase):
    def test_exact_atm_straddle_and_loud_unavailable_reasons(self):
        # Catches parity/close substitutions, wrong strike selection, and silent unavailable values.
        chain = [
            {
                "expiration": "2026-09-05",
                "strike": 100.0,
                "putCall": "CALL",
                "bid": 4.0,
                "ask": 6.0,
            },
            {"expiration": "2026-09-05", "strike": 100.0, "putCall": "PUT", "bid": 2.0, "ask": 4.0},
        ]
        value = event_calendar.implied_move(chain, "2026-08-26", 101.0, "schwab_preclose")
        self.assertEqual(value["text"], "7.92%")
        for source, reason in [
            ("thetadata_eod", "non-Schwab source"),
            ("schwab_preclose", "missing verified stock_snapshot spot"),
        ]:
            unavailable = event_calendar.implied_move(chain, "2026-08-26", None, source)
            self.assertIn(reason, unavailable["reason"])


if __name__ == "__main__":
    unittest.main()

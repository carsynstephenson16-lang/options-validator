"""Characterization and feature tests for Brief 28's display-only event layer."""

from __future__ import annotations

import json
import re
import subprocess
import sys
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
        self.assertTrue(
            all(item.verification == "asserted" and not item.source_quote for item in calendar)
        )
        self.assertTrue(
            all(item.source_url.startswith("https://www.federalreserve.gov/") for item in calendar)
        )

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

    def test_cli_add_appends_one_valid_row_and_refuses_duplicate(self):
        # Catches a manual add path bypassing the same schema and duplicate guard.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar.jsonl"
            args = [
                sys.executable,
                "-m",
                "options_researcher.event_calendar",
                "add",
                "--path",
                str(path),
                "--event-id",
                "cli",
                "--date",
                "2026-08-27",
                "--time-et",
                "UNKNOWN",
                "--kind",
                "other",
                "--title",
                "CLI event",
                "--source-url",
                "https://example.gov/event",
                "--source-kind",
                "official_gov",
                "--verification",
                "asserted",
                "--source-quote",
                "",
                "--captured-at",
                "2026-08-26T15:53:26Z",
                "--added-by",
                "test",
            ]
            self.assertEqual(subprocess.run(args, capture_output=True, text=True).returncode, 0)
            self.assertEqual(len(path.read_text().splitlines()), 1)
            self.assertNotEqual(subprocess.run(args, capture_output=True, text=True).returncode, 0)

    def test_seed_evidence_is_pinned_to_reviewed_literals(self):
        # Catches paraphrased source quotes that cannot be verified in a diff.
        expected = {
            "nvda-fy27q2-results-2026-08-26": "This material will be posted to investor.nvidia.com immediately after the company’s results are publicly announced at approximately 1:20 p.m. PT.",
            "bea-gdp-q2-second-estimate-2026-08-26": "GDP (Second Estimate) and Corporate Profits, 2nd Quarter 2026",
            "bea-personal-income-outlays-july-2026-08-26": "Personal Income and Outlays, July 2026",
            "jackson-hole-symposium-2026": "Jackson Hole Economic Policy Symposium, August 27–29, 2026",
            "warsh-jackson-hole-keynote-2026-08-28": "Speech - Chairman Kevin Warsh",
            "avgo-fy26q3-results-2026-09-02": "Broadcom Inc. to Announce Third Quarter Fiscal Year 2026 Financial Results on Wednesday, September 2, 2026",
            "iren-fy26-results-2026-08-27": "IREN to Release FY26 Results on August 27, 2026",
        }
        seeded = {item.event_id: item for item in event_calendar.load_calendar()}
        self.assertEqual({key: item.source_quote for key, item in seeded.items()}, expected)
        self.assertEqual(
            seeded["nvda-fy27q2-results-2026-08-26"].source_url,
            "https://investor.nvidia.com/news/press-release-details/2026/NVIDIA-Sets-Conference-Call-for-Second-Quarter-Financial-Results/default.aspx",
        )
        self.assertEqual(
            seeded["warsh-jackson-hole-keynote-2026-08-28"].source_url,
            "https://www.federalreserve.gov/newsevents/2026-august.htm",
        )


class EventChipTests(unittest.TestCase):
    def setUp(self):
        self.calendar = self._calendar(
            [
                _event(event_id="nvda-results", date="2026-08-27"),
                _event(event_id="macro-third", date="2026-08-29"),
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
        self.assertEqual([chip["marker"] for chip in own], ["cal", "cal", "cal"])
        self.assertIn("complex", [chip["marker"] for chip in related])
        self.assertEqual(
            ad.event_chips({"expiry": "2026-08-29"}, "NVDA", "2026-08-26", self.calendar, {}),
            own[:2],
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

    def test_missing_both_event_files_disables_exactly_to_prebrief_render(self):
        # Catches rollback leaving FOMC, CSS, notices, or implied annotations behind.
        data = {
            "evaluation_date": "2026-08-26",
            "data_as_of": "2026-08-26",
            "symbols": [],
            "blocked": [],
            "stale_symbols": [],
        }
        with (
            tempfile.TemporaryDirectory() as tmp,
            mock.patch.object(event_calendar, "CALENDAR_PATH", Path(tmp) / "none.jsonl"),
            mock.patch.object(event_calendar, "COMPLEX_MAP_PATH", Path(tmp) / "none.json"),
        ):
            self.assertIsNone(ad.build_event_view(data, "2026-08-26"))
        self.assertEqual(ad.render(data), ad.render(data, event_view=None))

    def test_populated_hero_lane_context_and_pinned_surfaces_share_exact_chip_list(self):
        # Catches a consumer drifting from the single event-chip join contract.
        def card(symbol):
            return {
                "headline": f"{symbol} call",
                "expiry": "2026-09-06",
                "strike": 100.0,
                "dte": 11,
                "cost": 100.0,
                "breakeven": 101.0,
                "breakeven_move": 0.01,
                "grades": {
                    "fits_bucket": "GREEN",
                    "fits_cap": "GREEN",
                    "iv_for_buyer": "GREEN",
                    "liquidity": "GREEN",
                },
                "scenarios": [],
                "bbb": [],
                "verdict": "x",
                "risk": {},
                "top3_snapshot": {
                    "candidate_id": f"{symbol}:long_call:100",
                    "rank_eligible": True,
                    "selection_status": "ELIGIBLE",
                    "policy": {"status": "ELIGIBLE", "reason_codes": []},
                },
            }

        symbols = ["NVDA", "AMD", "AVGO"]
        data = {
            "evaluation_date": "2026-08-26",
            "data_as_of": "2026-08-26",
            "blocked": [],
            "stale_symbols": [],
            "symbols": [
                {
                    "symbol": symbol,
                    "as_of": "2026-08-26",
                    "close": 100.0,
                    "groups": [{"kind": "long_call", "title": "Calls", "cards": [card(symbol)]}],
                }
                for symbol in symbols
            ],
            "composite_signals": [
                {
                    "symbol": symbol,
                    "grade": "A",
                    "aligned_count": 1,
                    "max_asof": "2026-08-26",
                    "trend": {"state": "UP", "data_blocked": False},
                    "vol_premium": {"data_blocked": True},
                    "regime": {"data_blocked": True},
                    "internals": {"data_blocked": True},
                }
                for symbol in symbols
            ],
        }
        grades_before = [
            dict(section["groups"][0]["cards"][0]["grades"]) for section in data["symbols"]
        ]
        picks_before = json.dumps(ad.select_top_picks(data), sort_keys=True, separators=(",", ":"))
        sections_before = ad.sections_json(data["symbols"])
        view = {"calendar": self.calendar, "complex_map": {}, "implied_moves": {}, "failures": {}}
        with (
            mock.patch.object(config, "CONTEXT_LANE_ENABLED", True),
            mock.patch.object(config, "PICK_PINNED_SYMBOLS", ["NVDA"]),
        ):
            html = ad.render(data, event_view=view)

        def chips(fragment):
            return re.findall(r'<span class="event-chip">(.*?)</span>', fragment)

        lane = html[html.index('data-candidate-id="NVDA:long_call:100"') :]
        hero = html[html.index('<div class="hero-card good">') :]
        context = html[html.index('data-context-symbol="NVDA"') :]
        pinned = html[html.index('<div class="pinned-card good">') :]
        expected = chips(lane)[:3]
        self.assertGreaterEqual(len(expected), 3)
        self.assertEqual(chips(hero)[: len(expected)], expected)
        self.assertEqual(chips(context)[: len(expected)], expected)
        self.assertEqual(chips(pinned)[: len(expected)], expected)
        self.assertGreaterEqual(html.count('<div class="hero-card good">'), 3)
        self.assertEqual(
            len(chips(html[html.index("empty-slot") : html.index("empty-slot") + 350])), 0
        )
        self.assertEqual(
            [section["groups"][0]["cards"][0]["grades"] for section in data["symbols"]],
            grades_before,
        )
        self.assertEqual(
            json.dumps(ad.select_top_picks(data), sort_keys=True, separators=(",", ":")),
            picks_before,
        )
        self.assertEqual(ad.sections_json(data["symbols"]), sections_before)

    def test_chip_exception_is_contained_and_explicit_event_date_is_required(self):
        # Catches a renderer crash or stale data_as_of fallback in the event boundary.
        data = {
            "evaluation_date": "2026-08-26",
            "data_as_of": "2020-01-01",
            "symbols": [],
            "blocked": [],
            "stale_symbols": [],
        }
        with self.assertRaises(TypeError):
            ad.build_event_view(data)  # type: ignore[call-arg]
        event = self.calendar[0]
        view = event_calendar.EventView.create([event], {}, {}, {})
        with self.assertRaises(TypeError):
            view.failures["x"] = "y"  # type: ignore[index]
        card = {"expiry": "2026-08-30"}
        with mock.patch.object(ad, "event_chips", side_effect=RuntimeError):
            html = ad._event_chips_html(card, "NVDA", "2026-08-26", view)
        self.assertIn("EVENT LAYER FAILED — RuntimeError", html)


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

    def test_implied_move_stamps_and_each_unavailable_reason(self):
        # Catches lossy provenance stamps or a quiet invalid/missing option leg.
        chain = [
            {"expiration": "2026-09-05", "strike": 100.0, "right": "C", "bid": 4.0, "ask": 6.0},
            {"expiration": "2026-09-05", "strike": 100.0, "right": "P", "bid": 2.0, "ask": 4.0},
        ]
        good = event_calendar.implied_move(
            chain,
            "2026-08-26",
            100.0,
            "schwab_preclose",
            spot_timestamp="15:45:00",
            receipt_session="2026-08-26",
        )
        self.assertEqual(good["method"], "atm_straddle_mid/v1")
        self.assertEqual(good["capture_convention"], "15:45 ET preclose")
        self.assertEqual(good["spot_source"], "stock_snapshot")
        for rows, reason in [
            (chain[:1], "missing put"),
            (chain[1:], "missing call"),
            ([{**chain[0], "bid": float("nan")}], "missing call"),
            ([{**chain[0], "expiration": "2026-10-30"}], "no expiry"),
        ]:
            self.assertIn(
                reason,
                event_calendar.implied_move(rows, "2026-08-26", 100.0, "schwab_preclose")["reason"],
            )


if __name__ == "__main__":
    unittest.main()

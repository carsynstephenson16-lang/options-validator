"""Display-card construction and rendering tests.

Display-only: no directional colour, no directional wording, every failure
visible, every provider-controlled string escaped.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from data.short_positioning.normalize import write_normalized_partition
from data.short_positioning.provider import CaptureRequest
from data.short_positioning.providers.finra import normalize_finra_row, parse_finra_payload
from options_researcher.short_positioning_context import (
    CARD_CAVEAT,
    DAYS_TO_COVER_NOTE,
    LANE_HEADING,
    LANE_TEXT,
    LANE_TITLE,
    ShortPositioningCard,
    build_short_positioning_context,
    render_short_positioning_card,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
ASOF = datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
RAW_SHA = "b" * 64


def _card(**overrides) -> ShortPositioningCard:
    kwargs = {
        "symbol": "ZQXA",
        "source": "finra",
        "issue_name": "ZEPHYR QUANTA HOLDINGS INC COMMON STOCK",
        "settlement_date": "2026-07-15",
        "publication_date": "2026-07-17",
        "max_asof": "2026-07-17T20:40:00+00:00",
        "data_age_sessions": 1,
        "current_short_shares": 1_250_000,
        "change_shares": 250_000,
        "change_pct": Decimal("25"),
        "days_to_cover": Decimal("2.5"),
        "short_pct_float": None,
        "primary_status": "FLOAT_UNAVAILABLE",
        "statuses": ("FLOAT_UNAVAILABLE",),
        "explanation": "position shown as reported",
    }
    kwargs.update(overrides)
    return ShortPositioningCard(**kwargs)


class ExactCopyTests(unittest.TestCase):
    def test_lane_and_card_copy_is_exactly_as_specified(self):
        self.assertEqual(LANE_HEADING, "EXP-SHORT")
        self.assertEqual(LANE_TITLE, "Short positioning context")
        self.assertEqual(
            LANE_TEXT,
            "Issuer-level reported positioning. Display-only. No ranking, verdict, entry, "
            "sizing, or execution authority.",
        )
        self.assertEqual(CARD_CAVEAT, "Positioning snapshot, not direction or timing.")
        self.assertEqual(
            DAYS_TO_COVER_NOTE,
            "Source-defined liquidity ratio, not a countdown or timing forecast.",
        )


class ToneTests(unittest.TestCase):
    def test_integrity_failures_are_red(self):
        for status in (
            "SCHEMA_ERROR",
            "HASH_MISMATCH",
            "FUTURE_DATA",
            "MISSING_PROVENANCE",
            "PARTIAL_CAPTURE",
            "LICENSE_BLOCKED",
        ):
            with self.subTest(status=status):
                self.assertEqual(_card(primary_status=status, statuses=(status,)).tone, "red")

    def test_health_states_are_amber(self):
        for status in ("STALE", "REVISED", "FLOAT_UNAVAILABLE", "NOT_YET_PUBLISHED"):
            with self.subTest(status=status):
                self.assertEqual(_card(primary_status=status, statuses=(status,)).tone, "amber")

    def test_ordinary_states_are_neutral_never_green(self):
        for status in ("OK", "NO_RECORD", "PROVIDER_CONFLICT", "AMBIGUOUS_SECURITY"):
            with self.subTest(status=status):
                self.assertEqual(_card(primary_status=status, statuses=(status,)).tone, "neutral")

    def test_no_tone_is_ever_a_directional_good_state(self):
        for status in ("OK", "STALE", "SCHEMA_ERROR"):
            tone = _card(primary_status=status, statuses=(status,)).tone
            self.assertNotIn(tone, {"good", "bad"})


class ContextBuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def seed(self, index=0, symbols=("ZQXA",)):
        request = CaptureRequest(
            provider="finra",
            dataset="consolidated-short-interest",
            publication_date=date(2026, 7, 17),
            symbols=symbols,
            output_root=self.root,
            source_data_version="1.0",
            request_id="ctx-seed",
            execute=True,
        )
        rows = parse_finra_payload((FIXTURES / "finra_valid.json").read_bytes())
        records = [
            normalize_finra_row(
                rows[index],
                request=request,
                retrieved_at=datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
                row_ordinal=index,
                raw_sha256=RAW_SHA,
            )
        ]
        write_normalized_partition(records, root=self.root, request=request)

    def test_a_stored_symbol_produces_a_populated_card(self):
        self.seed()
        (card,) = build_short_positioning_context(["ZQXA"], asof=ASOF, root=self.root)

        self.assertEqual(card.symbol, "ZQXA")
        self.assertEqual(card.source, "finra")
        self.assertEqual(card.settlement_date, "2026-07-15")
        self.assertEqual(card.publication_date, "2026-07-17")
        self.assertEqual(card.current_short_shares, 1_250_000)
        self.assertEqual(card.change_shares, 250_000)
        self.assertEqual(card.change_pct, Decimal("25"))
        self.assertEqual(card.days_to_cover, Decimal("2.5"))
        self.assertEqual(card.data_age_sessions, 1)
        self.assertIsNone(card.short_pct_float)
        self.assertEqual(card.max_asof, "2026-07-17T20:40:00+00:00")

    def test_an_unknown_symbol_is_a_visible_no_record_card(self):
        self.seed()
        (card,) = build_short_positioning_context(["NOSUCH"], asof=ASOF, root=self.root)
        self.assertEqual(card.primary_status, "NO_RECORD")
        self.assertIsNone(card.current_short_shares)
        self.assertEqual(card.tone, "neutral")

    def test_an_empty_root_still_renders_one_card_per_symbol(self):
        cards = build_short_positioning_context(["ZQXA", "TRNVQ"], asof=ASOF, root=self.root)
        self.assertEqual(len(cards), 2)
        self.assertEqual({card.primary_status for card in cards}, {"NO_RECORD"})

    def test_output_is_deterministic_for_identical_inputs(self):
        self.seed()
        first = build_short_positioning_context(["ZQXA"], asof=ASOF, root=self.root)
        second = build_short_positioning_context(["ZQXA"], asof=ASOF, root=self.root)
        self.assertEqual(first, second)
        self.assertEqual(
            render_short_positioning_card(first[0]), render_short_positioning_card(second[0])
        )


class RenderTests(unittest.TestCase):
    def test_every_required_field_is_rendered(self):
        html = render_short_positioning_card(_card())
        for fragment in (
            "ZQXA",
            "finra",
            "2026-07-15",
            "2026-07-17",
            "2026-07-17T20:40:00+00:00",
            "1,250,000",
            "250,000",
            "2.5",
            "FLOAT_UNAVAILABLE",
        ):
            self.assertIn(fragment, html)
        self.assertIn("1 XNYS session", html)

    def test_the_caveat_and_days_to_cover_note_appear_on_every_card(self):
        for status in ("OK", "SCHEMA_ERROR", "STALE"):
            with self.subTest(status=status):
                html = render_short_positioning_card(
                    _card(primary_status=status, statuses=(status,))
                )
                self.assertIn(CARD_CAVEAT, html)
                self.assertIn(DAYS_TO_COVER_NOTE, html)

    def test_secondary_statuses_are_all_visible(self):
        html = render_short_positioning_card(
            _card(
                primary_status="STALE",
                statuses=("STALE", "REVISED", "FLOAT_UNAVAILABLE"),
            )
        )
        for status in ("STALE", "REVISED", "FLOAT_UNAVAILABLE"):
            self.assertIn(status, html)

    def test_provider_controlled_text_is_escaped(self):
        html = render_short_positioning_card(_card(issue_name='<script>alert("x")</script> & CO'))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp; CO", html)

    def test_missing_values_render_as_unavailable_never_zero(self):
        html = render_short_positioning_card(
            _card(
                current_short_shares=None,
                change_shares=None,
                change_pct=None,
                days_to_cover=None,
                data_age_sessions=None,
                primary_status="NO_RECORD",
                statuses=("NO_RECORD",),
            )
        )
        self.assertIn("unavailable", html)
        self.assertNotIn(">0<", html)

    def test_no_directional_or_predictive_wording_appears(self):
        # The two mandated caveats deliberately contain "forecast" and
        # "direction"; strip them so this checks the data presentation itself.
        html = render_short_positioning_card(_card())
        html = html.replace(CARD_CAVEAT, "").replace(DAYS_TO_COVER_NOTE, "").lower()
        for banned in (
            "bull",
            "bear",
            "squeeze",
            "edge",
            "opportunity",
            "conviction",
            "buy",
            "sell",
            "forecast",
            "predict",
        ):
            self.assertNotIn(banned, html)


if __name__ == "__main__":
    unittest.main()

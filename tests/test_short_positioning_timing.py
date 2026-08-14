"""Point-in-time timing and causal snapshot-resolution tests.

The information clock is publication availability, never the settlement date,
and never weekday arithmetic. Future rows are refused rather than displayed.
"""

from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from data.short_positioning.models import (
    ShortInterestFeaturesV1,
    ShortPositioningSchemaError,
)
from data.short_positioning.normalize import write_normalized_partition
from data.short_positioning.provider import CaptureRequest, next_available_session
from data.short_positioning.providers.finra import (
    finra_available_at,
    normalize_finra_row,
    parse_finra_payload,
)
from data.short_positioning.snapshots import (
    load_latest_available_records,
    resolve_short_positioning_snapshot,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
EASTERN = ZoneInfo("America/New_York")
RAW_SHA = "f" * 64


class NextSessionTests(unittest.TestCase):
    def test_release_after_the_close_enters_the_following_session(self):
        # 2026-07-17 is a Friday session; the next session is Monday 2026-07-20.
        self.assertEqual(next_available_session(date(2026, 7, 17)), date(2026, 7, 20))

    def test_holiday_is_skipped_by_the_exchange_calendar(self):
        # Monday 2026-09-07 is Labor Day, so Friday's release lands on Tuesday.
        self.assertEqual(next_available_session(date(2026, 9, 4)), date(2026, 9, 8))

    def test_early_close_session_still_uses_the_next_completed_session(self):
        # 2026-11-27 is the post-Thanksgiving early close; next session is Monday.
        self.assertEqual(next_available_session(date(2026, 11, 27)), date(2026, 11, 30))

    def test_weekend_publication_date_resolves_forward(self):
        self.assertEqual(next_available_session(date(2026, 7, 18)), date(2026, 7, 20))

    def test_available_at_is_the_documented_four_forty_pm_eastern(self):
        available_at = finra_available_at(date(2026, 7, 17))
        self.assertEqual(available_at.astimezone(EASTERN).hour, 16)
        self.assertEqual(available_at.astimezone(EASTERN).minute, 40)
        self.assertEqual(available_at.tzinfo, ZoneInfo("UTC"))

    def test_a_late_release_is_not_backdated_to_the_scheduled_time(self):
        scheduled = finra_available_at(date(2026, 7, 17))
        observed = datetime(2026, 7, 17, 19, 15, tzinfo=EASTERN).astimezone(timezone.utc)
        late = finra_available_at(date(2026, 7, 17), observed_release_at=observed)
        self.assertEqual(late, observed)
        self.assertGreater(late, scheduled)

    def test_an_early_observed_timestamp_never_moves_availability_earlier(self):
        scheduled = finra_available_at(date(2026, 7, 17))
        early = datetime(2026, 7, 17, 9, 0, tzinfo=EASTERN).astimezone(timezone.utc)
        self.assertEqual(
            finra_available_at(date(2026, 7, 17), observed_release_at=early), scheduled
        )


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def request(self, **overrides) -> CaptureRequest:
        kwargs = {
            "provider": "finra",
            "dataset": "consolidated-short-interest",
            "publication_date": date(2026, 7, 17),
            "symbols": ("ZQXA",),
            "output_root": self.root,
            "source_data_version": "1.0",
            "request_id": "seed",
            "execute": True,
        }
        kwargs.update(overrides)
        return CaptureRequest(**kwargs)

    def seed(self, *, fixture="finra_valid.json", request=None, retrieved_at=None, index=0):
        request = request or self.request()
        retrieved_at = retrieved_at or datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
        rows = parse_finra_payload((FIXTURES / fixture).read_bytes())
        records = [
            normalize_finra_row(
                rows[index],
                request=request,
                retrieved_at=retrieved_at,
                row_ordinal=index,
                raw_sha256=RAW_SHA,
            )
        ]
        write_normalized_partition(records, root=self.root, request=request)
        return records[0]


class CausalResolutionTests(StoreTestCase):
    def test_record_is_invisible_before_it_became_available(self):
        record = self.seed()
        before = record.available_at.replace(hour=12)
        self.assertEqual(
            load_latest_available_records(
                self.root,
                provider="finra",
                dataset="consolidated-short-interest",
                symbol="ZQXA",
                asof=before,
            ),
            (),
        )

    def test_asof_before_publication_is_refused_as_future_data(self):
        self.seed()
        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 7, 16, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(snapshot.primary_status, "FUTURE_DATA")
        self.assertIsNone(snapshot.short_interest)
        self.assertIsNone(snapshot.features)

    def test_a_symbol_with_no_stored_row_is_no_record(self):
        self.seed()
        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="NOSUCH", asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(snapshot.primary_status, "NO_RECORD")
        self.assertIsNone(snapshot.short_interest)

    def test_available_record_resolves_with_shares_and_session_age(self):
        self.seed()
        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
        )
        self.assertIsNotNone(snapshot.short_interest)
        assert snapshot.short_interest is not None
        self.assertEqual(snapshot.short_interest.current_short_shares, 1_250_000)
        assert snapshot.features is not None
        self.assertEqual(snapshot.features.data_age_sessions, 1)
        self.assertEqual(snapshot.features.change_pct, Decimal("25"))

    def test_max_asof_never_comes_from_the_settlement_date(self):
        record = self.seed()
        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(snapshot.max_asof, record.available_at)
        self.assertNotEqual(snapshot.max_asof.date(), record.settlement_date)

    def test_float_is_unavailable_in_v1_so_percent_of_float_is_never_shown(self):
        self.seed()
        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
        )
        self.assertIn("FLOAT_UNAVAILABLE", snapshot.statuses)
        assert snapshot.features is not None
        self.assertIsNone(snapshot.features.short_pct_float)
        self.assertIsNone(snapshot.features.float_shares)

    def test_a_revision_supersedes_the_original_for_display_but_both_persist(self):
        self.seed()
        self.seed(fixture="finra_revision.json", request=self.request(request_id="rev"))
        asof = datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)

        records = load_latest_available_records(
            self.root,
            provider="finra",
            dataset="consolidated-short-interest",
            symbol="ZQXA",
            asof=asof,
        )
        self.assertEqual(len(records), 2)

        snapshot = resolve_short_positioning_snapshot(self.root, symbol="ZQXA", asof=asof)
        self.assertIn("REVISED", snapshot.statuses)
        assert snapshot.short_interest is not None
        self.assertEqual(snapshot.short_interest.current_short_shares, 1_310_000)

    def test_two_missed_releases_make_the_symbol_stale(self):
        self.seed()
        # Two later publications exist and are available, neither carrying ZQXA.
        for publication, request_id in (
            (date(2026, 7, 31), "later-1"),
            (date(2026, 8, 14), "later-2"),
        ):
            request = self.request(
                publication_date=publication, symbols=("TRNVQ",), request_id=request_id
            )
            self.seed(
                request=request,
                index=1,
                retrieved_at=datetime(2026, 8, 17, 12, 0, tzinfo=timezone.utc),
            )

        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 8, 18, 20, 0, tzinfo=timezone.utc)
        )
        self.assertIn("STALE", snapshot.statuses)
        self.assertEqual(snapshot.primary_status, "STALE")

    def test_one_missed_release_is_within_the_display_health_budget(self):
        self.seed()
        request = self.request(
            publication_date=date(2026, 7, 31), symbols=("TRNVQ",), request_id="later-1"
        )
        self.seed(
            request=request, index=1, retrieved_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
        )

        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 8, 4, 20, 0, tzinfo=timezone.utc)
        )
        self.assertNotIn("STALE", snapshot.statuses)

    def test_a_corrupt_partition_surfaces_a_schema_error_not_an_empty_lane(self):
        self.seed()
        partition = next(self.root.rglob("records-*.json"))
        partition.write_text(json.dumps({"records": [{"symbol": "ZQXA"}]}))

        snapshot = resolve_short_positioning_snapshot(
            self.root, symbol="ZQXA", asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)
        )
        self.assertEqual(snapshot.primary_status, "SCHEMA_ERROR")
        self.assertIsNone(snapshot.short_interest)


class FloatLookaheadTests(unittest.TestCase):
    def _features(self, **overrides) -> ShortInterestFeaturesV1:
        kwargs = {
            "schema_version": "short-interest-features/v1",
            "source_record_key": "finra|consolidated-short-interest|NNM|ZQXA|2026-07-15|original",
            "provider": "finra",
            "feature_asof": datetime(2026, 7, 20, 20, 0, tzinfo=timezone.utc),
            "available_at": datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc),
            "available_session": date(2026, 7, 20),
            "change_pct": None,
            "change_1_cycle": None,
            "change_3_cycles": None,
            "float_shares": None,
            "float_asof": None,
            "float_available_at": None,
            "float_source": None,
            "short_pct_float": None,
            "own_history_percentile": None,
            "cross_sectional_percentile": None,
            "data_age_sessions": 1,
            "price_return_since_settlement": None,
            "price_return_since_publication": None,
            "lineage_sha256": RAW_SHA,
        }
        kwargs.update(overrides)
        return ShortInterestFeaturesV1(**kwargs)

    def test_a_current_float_cannot_populate_a_historical_denominator(self):
        with self.assertRaises(ShortPositioningSchemaError):
            self._features(
                float_shares=1_000_000,
                float_asof=date(2026, 8, 10),
                float_available_at=datetime(2026, 8, 10, 20, 0, tzinfo=timezone.utc),
                float_source="synthetic-current-float",
                short_pct_float=Decimal("12.5"),
            )

    def test_a_causally_available_float_is_accepted(self):
        features = self._features(
            float_shares=1_000_000,
            float_asof=date(2026, 7, 10),
            float_available_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            float_source="synthetic-pit-float",
            short_pct_float=Decimal("125.0"),
        )
        self.assertEqual(features.short_pct_float, Decimal("125.0"))


if __name__ == "__main__":
    unittest.main()

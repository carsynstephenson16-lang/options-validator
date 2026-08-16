"""Phase 1 contract tests for the short-positioning normalized schemas.

Every value here is invented. No licensed or provider-published row is copied
into this repository (see docs/data/short-positioning-contract.md).
"""

from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from data.short_positioning.models import (
    STATUS_PRECEDENCE,
    SecurityIdentityV1,
    ShortInterestFeaturesV1,
    ShortInterestRecordV1,
    ShortPositioningSchemaError,
    ShortPositioningSnapshotV1,
    SourceProvenanceV1,
    build_source_record_key,
    primary_status_of,
    validate_short_interest_record,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"

# Invented tickers only. If a fixture ever gains a real listed symbol this set
# must be updated deliberately, which is the point of the assertion below.
SYNTHETIC_SYMBOLS = {"ZQXA", "TRNVQ", "HLGRD"}

_RAW_SHA = "a" * 64


def _provenance(**overrides) -> SourceProvenanceV1:
    kwargs = {
        "schema_version": "short-positioning-provenance/v1",
        "provider": "finra",
        "dataset": "consolidated-short-interest",
        "source_document": "https://developer.finra.org/docs",
        "access_method": "api",
        "source_data_version": "1.0",
        "source_release_at": datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc),
        "source_timezone": "America/New_York",
        "source_field_map_version": "finra-consolidated-short-interest/v1",
        "source_row_ordinal": 0,
        "request_id": "local-dry-run-0001",
        "raw_sha256": _RAW_SHA,
        "data_classification": "synthetic_test",
    }
    kwargs.update(overrides)
    return SourceProvenanceV1(**kwargs)


def _record(**overrides) -> ShortInterestRecordV1:
    kwargs = {
        "schema_version": "short-interest-core/v1",
        "provider": "finra",
        "dataset": "consolidated-short-interest",
        "source_record_key": build_source_record_key(
            provider="finra",
            dataset="consolidated-short-interest",
            market="NNM",
            symbol="ZQXA",
            settlement_date=date(2026, 7, 15),
            source_revision="original",
        ),
        "security_id": None,
        "symbol": "ZQXA",
        "market": "NNM",
        "issue_name": "ZEPHYR QUANTA HOLDINGS INC COMMON STOCK",
        "settlement_date": date(2026, 7, 15),
        "publication_date": date(2026, 7, 17),
        "available_at": datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc),
        "available_session": date(2026, 7, 20),
        "retrieved_at": datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
        "current_short_shares": 1_250_000,
        "previous_short_shares": 1_000_000,
        "change_shares": 250_000,
        "average_daily_volume_shares": 500_000,
        "days_to_cover": Decimal("2.5"),
        "revision_flag": None,
        "stock_split_flag": None,
        "raw_sha256": _RAW_SHA,
        "source_provenance": _provenance(),
    }
    kwargs.update(overrides)
    return ShortInterestRecordV1(**kwargs)


class ProvenanceContractTests(unittest.TestCase):
    def test_dataclasses_are_frozen_and_slotted(self):
        provenance = _provenance()
        with self.assertRaises(FrozenInstanceError):
            provenance.provider = "other"  # type: ignore[misc]
        self.assertFalse(hasattr(provenance, "__dict__"), "instances must not carry a __dict__")
        for model in (
            SourceProvenanceV1,
            SecurityIdentityV1,
            ShortInterestRecordV1,
            ShortInterestFeaturesV1,
            ShortPositioningSnapshotV1,
        ):
            self.assertIn("__slots__", model.__dict__, f"{model.__name__} must use slots")

    def test_unknown_access_method_and_classification_fail_closed(self):
        with self.assertRaises(ShortPositioningSchemaError):
            _provenance(access_method="carrier_pigeon")
        with self.assertRaises(ShortPositioningSchemaError):
            _provenance(data_classification="whatever")

    def test_raw_sha256_must_be_lowercase_hex(self):
        with self.assertRaises(ShortPositioningSchemaError):
            _provenance(raw_sha256=_RAW_SHA.upper())
        with self.assertRaises(ShortPositioningSchemaError):
            _provenance(raw_sha256="abc")

    def test_unknown_schema_version_fails_closed(self):
        with self.assertRaises(ShortPositioningSchemaError):
            _provenance(schema_version="short-positioning-provenance/v2")


class RecordValidationTests(unittest.TestCase):
    def test_valid_record_passes(self):
        validate_short_interest_record(_record())

    def test_negative_current_short_shares_rejected(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(current_short_shares=-1))

    def test_missing_values_stay_none_and_are_never_zero_filled(self):
        record = _record(
            previous_short_shares=None,
            change_shares=None,
            average_daily_volume_shares=None,
            days_to_cover=None,
        )
        validate_short_interest_record(record)
        self.assertIsNone(record.previous_short_shares)
        self.assertIsNone(record.change_shares)
        self.assertIsNone(record.average_daily_volume_shares)
        self.assertIsNone(record.days_to_cover)

    def test_settlement_date_may_not_follow_publication_date(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(
                _record(settlement_date=date(2026, 7, 18), publication_date=date(2026, 7, 17))
            )

    def test_naive_timestamps_rejected(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(retrieved_at=datetime(2026, 7, 18, 12, 0)))
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(available_at=datetime(2026, 7, 17, 20, 40)))

    def test_non_utc_timestamps_rejected(self):
        eastern = timezone(timedelta(hours=-4))
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(
                _record(retrieved_at=datetime(2026, 7, 18, 8, 0, tzinfo=eastern))
            )

    def test_available_at_after_retrieved_at_rejected(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(
                _record(retrieved_at=datetime(2026, 7, 17, 20, 0, tzinfo=timezone.utc))
            )

    def test_record_hash_must_match_provenance_hash(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(raw_sha256="b" * 64))

    def test_source_record_key_is_deterministic_and_enforced(self):
        first = build_source_record_key(
            provider="finra",
            dataset="consolidated-short-interest",
            market="NNM",
            symbol="ZQXA",
            settlement_date=date(2026, 7, 15),
            source_revision="original",
        )
        second = build_source_record_key(
            provider="finra",
            dataset="consolidated-short-interest",
            market="NNM",
            symbol="ZQXA",
            settlement_date=date(2026, 7, 15),
            source_revision="original",
        )
        revised = build_source_record_key(
            provider="finra",
            dataset="consolidated-short-interest",
            market="NNM",
            symbol="ZQXA",
            settlement_date=date(2026, 7, 15),
            source_revision="revised",
        )
        self.assertEqual(first, second)
        self.assertNotEqual(first, revised)
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(source_record_key="hand-written-key"))

    def test_share_counts_must_be_integers_not_floats_or_bools(self):
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(current_short_shares=1250000.5))
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(current_short_shares=True))

    def test_days_to_cover_keeps_source_decimal(self):
        record = _record(days_to_cover=Decimal("6.25"))
        validate_short_interest_record(record)
        self.assertEqual(record.days_to_cover, Decimal("6.25"))
        with self.assertRaises(ShortPositioningSchemaError):
            validate_short_interest_record(_record(days_to_cover=6.25))


class FeatureContractTests(unittest.TestCase):
    def _features(self, **overrides) -> ShortInterestFeaturesV1:
        kwargs = {
            "schema_version": "short-interest-features/v1",
            "source_record_key": _record().source_record_key,
            "provider": "finra",
            "feature_asof": datetime(2026, 7, 20, 20, 0, tzinfo=timezone.utc),
            "available_at": datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc),
            "available_session": date(2026, 7, 20),
            "change_pct": Decimal("25.0"),
            "change_1_cycle": Decimal("0.25"),
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
            "lineage_sha256": _RAW_SHA,
        }
        kwargs.update(overrides)
        return ShortInterestFeaturesV1(**kwargs)

    def test_change_pct_above_one_hundred_percent_is_preserved_unclamped(self):
        features = self._features(change_pct=Decimal("150.0"))
        self.assertEqual(features.change_pct, Decimal("150.0"))

    def test_short_pct_float_above_one_hundred_percent_is_preserved_unclamped(self):
        features = self._features(
            float_shares=1_000_000,
            float_asof=date(2026, 7, 10),
            float_available_at=datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
            float_source="synthetic-test-float",
            short_pct_float=Decimal("125.0"),
        )
        self.assertEqual(features.short_pct_float, Decimal("125.0"))

    def test_percentiles_stay_none_in_v1(self):
        features = self._features()
        self.assertIsNone(features.own_history_percentile)
        self.assertIsNone(features.cross_sectional_percentile)

    def test_feature_fields_match_the_registered_contract(self):
        self.assertEqual(
            [f.name for f in fields(ShortInterestFeaturesV1)],
            [
                "schema_version",
                "source_record_key",
                "provider",
                "feature_asof",
                "available_at",
                "available_session",
                "change_pct",
                "change_1_cycle",
                "change_3_cycles",
                "float_shares",
                "float_asof",
                "float_available_at",
                "float_source",
                "short_pct_float",
                "own_history_percentile",
                "cross_sectional_percentile",
                "data_age_sessions",
                "price_return_since_settlement",
                "price_return_since_publication",
                "lineage_sha256",
            ],
        )


class SnapshotStatusTests(unittest.TestCase):
    def _snapshot(self, statuses, primary=None, **overrides):
        kwargs = {
            "schema_version": "short-positioning-snapshot/v1",
            "symbol": "ZQXA",
            "asof": datetime(2026, 7, 20, 20, 0, tzinfo=timezone.utc),
            "max_asof": datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc),
            "primary_status": primary or primary_status_of(statuses),
            "statuses": tuple(statuses),
            "short_interest": None,
            "features": None,
            "provider_extension_ref": None,
            "explanation": "synthetic",
        }
        kwargs.update(overrides)
        return ShortPositioningSnapshotV1(**kwargs)

    def test_precedence_order_matches_the_registered_taxonomy(self):
        self.assertEqual(
            STATUS_PRECEDENCE,
            (
                "SCHEMA_ERROR",
                "HASH_MISMATCH",
                "FUTURE_DATA",
                "MISSING_PROVENANCE",
                "PARTIAL_CAPTURE",
                "LICENSE_BLOCKED",
                "AMBIGUOUS_SECURITY",
                "CORPORATE_ACTION",
                "NOT_YET_PUBLISHED",
                "NO_RECORD",
                "PROVIDER_CONFLICT",
                "STALE",
                "REVISED",
                "FLOAT_UNAVAILABLE",
                "OK",
            ),
        )

    def test_primary_status_takes_the_highest_precedence_member(self):
        self.assertEqual(primary_status_of(("OK", "STALE", "REVISED")), "STALE")
        self.assertEqual(primary_status_of(("FLOAT_UNAVAILABLE", "HASH_MISMATCH")), "HASH_MISMATCH")
        self.assertEqual(primary_status_of(("OK",)), "OK")

    def test_snapshot_rejects_mismatched_primary_status(self):
        with self.assertRaises(ShortPositioningSchemaError):
            self._snapshot(("OK", "STALE"), primary="OK")

    def test_snapshot_rejects_empty_duplicate_or_unknown_statuses(self):
        with self.assertRaises(ShortPositioningSchemaError):
            self._snapshot((), primary="OK")
        with self.assertRaises(ShortPositioningSchemaError):
            self._snapshot(("OK", "OK"))
        with self.assertRaises(ShortPositioningSchemaError):
            self._snapshot(("SQUEEZE_IMMINENT",), primary="SQUEEZE_IMMINENT")

    def test_snapshot_accepts_a_valid_multi_status_set(self):
        snapshot = self._snapshot(("STALE", "REVISED", "FLOAT_UNAVAILABLE"))
        self.assertEqual(snapshot.primary_status, "STALE")
        self.assertEqual(snapshot.statuses, ("STALE", "REVISED", "FLOAT_UNAVAILABLE"))


class SyntheticFixtureTests(unittest.TestCase):
    def test_every_fixture_is_synthetic_and_parses(self):
        for name in (
            "finra_valid.json",
            "finra_revision.json",
            "finra_split.json",
            "finra_malformed.json",
        ):
            with self.subTest(fixture=name):
                rows = json.loads((FIXTURES / name).read_text())
                self.assertTrue(rows, f"{name} must contain at least one row")
                for row in rows:
                    self.assertIn(row["symbolCode"], SYNTHETIC_SYMBOLS)

    def test_malformed_fixture_carries_a_drifted_field_and_a_bad_type(self):
        rows = json.loads((FIXTURES / "finra_malformed.json").read_text())
        self.assertTrue(any("unexpectedProviderField" in row for row in rows))
        self.assertTrue(
            any(isinstance(row["currentShortPositionQuantity"], str) for row in rows),
        )

    def test_valid_fixture_covers_nulls_and_above_one_hundred_percent_change(self):
        rows = json.loads((FIXTURES / "finra_valid.json").read_text())
        self.assertTrue(any(row["previousShortPositionQuantity"] is None for row in rows))
        self.assertTrue(any((row["changePercent"] or 0) > 100 for row in rows))


if __name__ == "__main__":
    unittest.main()

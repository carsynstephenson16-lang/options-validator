"""FINRA Consolidated Short Interest adapter tests.

Every payload here is invented. No FINRA request is made and no published
sample row is copied. Transports are mocked; the real transport is never
called from the test suite.
"""

from __future__ import annotations

import json
import os
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlencode

from data.short_positioning.models import ShortPositioningSchemaError
from data.short_positioning.provider import (
    CaptureRequest,
    CredentialError,
    ProviderUnavailableError,
    next_available_session,
)
from data.short_positioning.providers.finra import (
    FINRA_DATASET,
    FINRA_FIELD_MAP,
    FINRA_GROUP,
    FINRA_KNOWN_FIELDS,
    FinraConsolidatedShortInterestAdapter,
    build_finra_request,
    finra_available_at,
    normalize_finra_row,
    parse_finra_payload,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
RETRIEVED_AT = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
RAW_SHA = "c" * 64


def _request(**overrides) -> CaptureRequest:
    kwargs = {
        "provider": "finra",
        "dataset": "consolidated-short-interest",
        "publication_date": date(2026, 7, 17),
        "symbols": ("ZQXA", "TRNVQ", "HLGRD"),
        "output_root": Path("/tmp/does-not-exist-short-positioning"),
        "source_data_version": "1.0",
        "request_id": "test-0001",
        "execute": False,
    }
    kwargs.update(overrides)
    return CaptureRequest(**kwargs)


def _rows(fixture: str) -> list[dict]:
    return parse_finra_payload((FIXTURES / fixture).read_bytes())


def _normalize(row: dict, **overrides) -> object:
    kwargs = {
        "request": _request(),
        "retrieved_at": RETRIEVED_AT,
        "row_ordinal": 0,
        "raw_sha256": RAW_SHA,
    }
    kwargs.update(overrides)
    return normalize_finra_row(row, **kwargs)


class FieldMapTests(unittest.TestCase):
    def test_known_fields_are_exactly_the_documented_source_fields(self):
        self.assertEqual(
            FINRA_KNOWN_FIELDS,
            frozenset(
                {
                    "accountingYearMonthNumber",
                    "averageDailyVolumeQuantity",
                    "changePercent",
                    "changePreviousNumber",
                    "currentShortPositionQuantity",
                    "daysToCoverQuantity",
                    "issueName",
                    "issuerServicesGroupExchangeCode",
                    "marketClassCode",
                    "previousShortPositionQuantity",
                    "revisionFlag",
                    "settlementDate",
                    "stockSplitFlag",
                    "symbolCode",
                }
            ),
        )

    def test_each_core_destination_is_mapped_exactly_once(self):
        destinations = list(FINRA_FIELD_MAP.values())
        self.assertEqual(len(destinations), len(set(destinations)))
        self.assertEqual(
            set(FINRA_FIELD_MAP),
            {
                "issueName",
                "symbolCode",
                "marketClassCode",
                "settlementDate",
                "currentShortPositionQuantity",
                "previousShortPositionQuantity",
                "changePreviousNumber",
                "averageDailyVolumeQuantity",
                "daysToCoverQuantity",
                "stockSplitFlag",
                "revisionFlag",
            },
        )

    def test_reconciliation_and_provenance_fields_are_not_core_destinations(self):
        for source_field in (
            "changePercent",
            "issuerServicesGroupExchangeCode",
            "accountingYearMonthNumber",
        ):
            self.assertNotIn(source_field, FINRA_FIELD_MAP)


class RequestBuilderTests(unittest.TestCase):
    def test_plan_targets_the_documented_group_and_dataset(self):
        plan = build_finra_request(_request())
        self.assertEqual(FINRA_GROUP, "otcMarket")
        self.assertEqual(FINRA_DATASET, "consolidatedShortInterest")
        self.assertIn(FINRA_GROUP.lower(), plan.url.lower())
        self.assertIn(FINRA_DATASET.lower(), plan.url.lower())

    def test_plan_pins_an_explicit_source_data_version(self):
        plan = build_finra_request(_request(source_data_version="1.0"))
        self.assertEqual(dict(plan.query).get("dataVersion"), "1.0")

    def test_plan_is_dry_run_by_default_and_names_credentials_without_values(self):
        # Credential NAMES are allowed to appear (and do contain words like
        # "secret"); credential VALUES must never appear anywhere in the plan.
        values = {
            "FINRA_API_CLIENT_ID": "FAKE-NOT-A-REAL-CREDENTIAL-2",
            "FINRA_API_CLIENT_SECRET": "FAKE-NOT-A-REAL-CREDENTIAL-3",
        }
        with mock.patch.dict(os.environ, values, clear=False):
            plan = build_finra_request(_request())

        self.assertTrue(plan.dry_run)
        self.assertEqual(
            plan.credential_env_names, ("FINRA_API_CLIENT_ID", "FINRA_API_CLIENT_SECRET")
        )
        rendered = json.dumps(
            {
                "url": plan.url,
                "query": plan.query,
                "credential_env_names": plan.credential_env_names,
            }
        )
        for fake_value in values.values():
            self.assertNotIn(fake_value, rendered)
        self.assertNotIn("authorization", rendered.lower())

    def test_plan_for_a_future_publication_date_is_allowed_but_records_are_not(self):
        # The pre-release dry-run exception belongs to the plan only.
        plan = build_finra_request(_request(publication_date=date(2099, 1, 4)))
        self.assertTrue(plan.dry_run)


class NormalizationTests(unittest.TestCase):
    def test_valid_row_maps_every_documented_field(self):
        record = _normalize(_rows("finra_valid.json")[0])
        self.assertEqual(record.symbol, "ZQXA")
        self.assertEqual(record.market, "NNM")
        self.assertEqual(record.issue_name, "ZEPHYR QUANTA HOLDINGS INC COMMON STOCK")
        self.assertEqual(record.settlement_date, date(2026, 7, 15))
        self.assertEqual(record.publication_date, date(2026, 7, 17))
        self.assertEqual(record.current_short_shares, 1_250_000)
        self.assertEqual(record.previous_short_shares, 1_000_000)
        self.assertEqual(record.change_shares, 250_000)
        self.assertEqual(record.average_daily_volume_shares, 500_000)
        self.assertEqual(record.days_to_cover, Decimal("2.5"))
        self.assertIsNone(record.revision_flag)
        self.assertIsNone(record.stock_split_flag)
        self.assertIsNone(record.security_id)
        self.assertEqual(record.raw_sha256, RAW_SHA)
        self.assertEqual(record.source_provenance.data_classification, "public_local_only")

    def test_shares_stay_integers_and_days_to_cover_stays_decimal(self):
        record = _normalize(_rows("finra_valid.json")[0])
        self.assertIsInstance(record.current_short_shares, int)
        self.assertNotIsInstance(record.current_short_shares, bool)
        self.assertIsInstance(record.days_to_cover, Decimal)

    def test_nulls_are_preserved_and_never_zero_filled(self):
        record = _normalize(_rows("finra_valid.json")[2])
        self.assertIsNone(record.previous_short_shares)
        self.assertIsNone(record.change_shares)
        self.assertIsNone(record.average_daily_volume_shares)
        self.assertIsNone(record.days_to_cover)

    def test_change_above_one_hundred_percent_is_preserved(self):
        record = _normalize(_rows("finra_valid.json")[1])
        self.assertEqual(record.current_short_shares, 2_500_000)
        self.assertEqual(record.change_shares, 1_500_000)

    def test_change_percent_is_reconciliation_only_and_a_mismatch_fails_closed(self):
        row = dict(_rows("finra_valid.json")[0])
        row["changePercent"] = Decimal("99.0")
        with self.assertRaises(ShortPositioningSchemaError):
            _normalize(row)

    def test_revision_row_sets_the_flag_and_a_distinct_record_key(self):
        original = _normalize(_rows("finra_valid.json")[0])
        revised = _normalize(_rows("finra_revision.json")[0])
        self.assertTrue(revised.revision_flag)
        self.assertNotEqual(original.source_record_key, revised.source_record_key)
        self.assertIn("revised", revised.source_record_key)
        self.assertIn("original", original.source_record_key)

    def test_split_row_sets_the_split_flag(self):
        record = _normalize(
            _rows("finra_split.json")[0],
            request=_request(symbols=("TRNVQ",), publication_date=date(2026, 8, 4)),
            retrieved_at=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(record.stock_split_flag)

    def test_unknown_flag_value_fails_closed_instead_of_coercing(self):
        row = dict(_rows("finra_valid.json")[0])
        row["revisionFlag"] = "MAYBE"
        with self.assertRaises(ShortPositioningSchemaError):
            _normalize(row)

    def test_malformed_payload_fails_closed(self):
        with self.assertRaises(ShortPositioningSchemaError):
            _rows("finra_malformed.json")

    def test_unknown_source_field_fails_closed(self):
        payload = json.dumps([{"symbolCode": "ZQXA", "brandNewField": 1}]).encode()
        with self.assertRaises(ShortPositioningSchemaError):
            parse_finra_payload(payload)

    def test_daily_short_sale_volume_dataset_is_refused(self):
        row = _rows("finra_valid.json")[0]
        with self.assertRaises(ShortPositioningSchemaError):
            _normalize(row, request=_request(dataset="daily-short-sale-volume"))

    def test_accounting_year_month_must_agree_with_the_settlement_cycle(self):
        row = dict(_rows("finra_valid.json")[0])
        row["accountingYearMonthNumber"] = 202512
        with self.assertRaises(ShortPositioningSchemaError):
            _normalize(row)


class TimingTests(unittest.TestCase):
    def test_available_at_is_four_forty_pm_new_york_in_utc(self):
        available_at = finra_available_at(date(2026, 7, 17))
        self.assertEqual(available_at, datetime(2026, 7, 17, 20, 40, tzinfo=timezone.utc))
        self.assertEqual(available_at.utcoffset().total_seconds(), 0)

    def test_friday_release_first_enters_the_monday_session(self):
        self.assertEqual(next_available_session(date(2026, 7, 17)), date(2026, 7, 20))

    def test_record_carries_the_next_session_not_the_publication_date(self):
        record = _normalize(_rows("finra_valid.json")[0])
        self.assertEqual(record.available_session, date(2026, 7, 20))
        self.assertNotEqual(record.available_session, record.publication_date)
        self.assertNotEqual(record.available_session, record.settlement_date)

    def test_a_late_captured_revision_is_bounded_by_when_it_was_retrieved(self):
        # The correction did not exist publicly at the original scheduled
        # release; it can only be "known" once it was actually captured.
        scheduled = finra_available_at(date(2026, 7, 17))
        late_retrieval = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        record = _normalize(_rows("finra_revision.json")[0], retrieved_at=late_retrieval)
        self.assertTrue(record.revision_flag)
        self.assertEqual(record.available_at, late_retrieval)
        self.assertGreater(record.available_at, scheduled)

    def test_a_promptly_captured_revision_keeps_the_scheduled_availability(self):
        scheduled = finra_available_at(date(2026, 7, 17))
        record = _normalize(_rows("finra_revision.json")[0], retrieved_at=scheduled)
        self.assertTrue(record.revision_flag)
        self.assertEqual(record.available_at, scheduled)

    def test_an_original_rows_available_at_is_unaffected_by_retrieval_time(self):
        scheduled = finra_available_at(date(2026, 7, 17))
        late_retrieval = datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc)
        record = _normalize(_rows("finra_valid.json")[0], retrieved_at=late_retrieval)
        self.assertIsNone(record.revision_flag)
        self.assertEqual(record.available_at, scheduled)


class _Transport:
    """Scripted mock transport. Records calls; never touches a network."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, url, *, headers, timeout):
        self.calls += 1
        outcome = self.responses.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RetryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.adapter = FinraConsolidatedShortInterestAdapter()
        self.plan = build_finra_request(_request(execute=True))
        self.slept: list[float] = []

    def _fetch(self, transport):
        return self.adapter.fetch(self.plan, transport=transport, sleep=self.slept.append)

    def test_rate_limit_is_retried_and_retry_after_is_honored(self):
        transport = _Transport(
            [
                (429, {"Retry-After": "7"}, b""),
                (200, {}, b"[]"),
            ]
        )
        self._fetch(transport)
        self.assertEqual(transport.calls, 2)
        self.assertEqual(self.slept, [7.0])

    def test_server_error_is_retried_then_reported_unavailable(self):
        transport = _Transport([(500, {}, b"")] * 12)
        with self.assertRaises(ProviderUnavailableError):
            self._fetch(transport)
        self.assertGreater(transport.calls, 1)
        self.assertTrue(all(delay > 0 for delay in self.slept))

    def test_timeout_is_retried(self):
        transport = _Transport([TimeoutError("synthetic timeout"), (200, {}, b"[]")])
        self._fetch(transport)
        self.assertEqual(transport.calls, 2)

    def test_authentication_and_bad_request_are_not_retried(self):
        for status, expected in ((401, CredentialError), (403, CredentialError)):
            with self.subTest(status=status):
                transport = _Transport([(status, {}, b"")])
                with self.assertRaises(expected):
                    self._fetch(transport)
                self.assertEqual(transport.calls, 1)

    def test_query_parameters_are_encoded_onto_the_request_url(self):
        captured_urls: list[str] = []

        def transport(url, *, headers, timeout):
            captured_urls.append(url)
            return (200, {}, b"[]")

        self._fetch(transport)

        self.assertEqual(len(captured_urls), 1)
        base, _, query = captured_urls[0].partition("?")
        self.assertEqual(base, self.plan.url)
        self.assertTrue(query, "query parameters were dropped from the request URL")
        self.assertEqual(parse_qs(query), parse_qs(urlencode(self.plan.query)))

    def test_dry_run_plan_never_calls_the_transport(self):
        transport = _Transport([])
        plan = build_finra_request(_request(execute=False))
        result = self.adapter.fetch(plan, transport=transport, sleep=self.slept.append)
        self.assertEqual(transport.calls, 0)
        self.assertTrue(result.dry_run)
        self.assertIsNone(result.artifact)


if __name__ == "__main__":
    unittest.main()

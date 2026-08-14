"""Raw-artifact and normalized-partition storage tests.

All storage happens under a temporary directory. No provider is contacted.
"""

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from data.short_positioning.models import ShortPositioningSchemaError
from data.short_positioning.normalize import write_normalized_partition
from data.short_positioning.provider import (
    ArtifactIntegrityError,
    CaptureRequest,
    PartialCaptureError,
)
from data.short_positioning.providers.finra import normalize_finra_row, parse_finra_payload
from data.short_positioning.raw_store import (
    raw_partition_dir,
    verify_raw_artifact,
    write_raw_artifact,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
RETRIEVED_AT = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
RAW_SHA = "d" * 64


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
            "symbols": ("ZQXA", "TRNVQ", "HLGRD"),
            "output_root": self.root,
            "source_data_version": "1.0",
            "request_id": "test-0001",
            "execute": True,
        }
        kwargs.update(overrides)
        return CaptureRequest(**kwargs)

    def records(self, fixture="finra_valid.json", *, request=None, raw_sha256=RAW_SHA):
        request = request or self.request()
        rows = parse_finra_payload((FIXTURES / fixture).read_bytes())
        return [
            normalize_finra_row(
                row,
                request=request,
                retrieved_at=RETRIEVED_AT,
                row_ordinal=ordinal,
                raw_sha256=raw_sha256,
            )
            for ordinal, row in enumerate(rows)
        ]


class RawArtifactTests(StoreTestCase):
    def test_raw_bytes_and_manifest_are_written_with_a_matching_hash(self):
        payload = (FIXTURES / "finra_valid.json").read_bytes()
        artifact = write_raw_artifact(
            payload, root=self.root, request=self.request(), retrieved_at=RETRIEVED_AT
        )

        self.assertTrue(artifact.path.exists())
        self.assertEqual(artifact.path.read_bytes(), payload)
        self.assertEqual(artifact.byte_count, len(payload))
        self.assertRegex(artifact.sha256, r"^[0-9a-f]{64}$")

        manifest = json.loads(artifact.path.with_suffix(".manifest.json").read_text())
        self.assertEqual(manifest["raw_sha256"], artifact.sha256)
        self.assertEqual(manifest["byte_count"], len(payload))
        verify_raw_artifact(artifact)

    def test_tampered_bytes_are_detected_as_a_hash_mismatch(self):
        payload = b'[{"symbolCode": "ZQXA"}]'
        artifact = write_raw_artifact(
            payload, root=self.root, request=self.request(), retrieved_at=RETRIEVED_AT
        )
        artifact.path.write_bytes(payload + b" ")
        with self.assertRaises(ArtifactIntegrityError):
            verify_raw_artifact(artifact)

    def test_a_raw_artifact_is_immutable_and_never_overwritten(self):
        payload = b"[]"
        write_raw_artifact(
            payload, root=self.root, request=self.request(), retrieved_at=RETRIEVED_AT
        )
        with self.assertRaises(ArtifactIntegrityError):
            write_raw_artifact(
                b'[{"symbolCode": "ZQXA"}]',
                root=self.root,
                request=self.request(),
                retrieved_at=RETRIEVED_AT,
            )

    def test_raw_partition_is_scoped_by_provider_dataset_and_publication_date(self):
        path = raw_partition_dir(self.root, self.request())
        parts = path.as_posix()
        self.assertIn("provider=finra", parts)
        self.assertIn("dataset=consolidated-short-interest", parts)
        self.assertIn("publication_date=2026-07-17", parts)


class NormalizedPartitionTests(StoreTestCase):
    def test_partition_is_written_once_every_record_validates(self):
        path = write_normalized_partition(self.records(), root=self.root, request=self.request())
        self.assertTrue(path.exists())
        stored = json.loads(path.read_text())
        self.assertEqual(len(stored["records"]), 3)
        self.assertEqual(stored["schema_version"], "short-interest-core/v1")
        self.assertEqual({row["symbol"] for row in stored["records"]}, {"ZQXA", "TRNVQ", "HLGRD"})

    def test_duplicate_source_record_keys_block_the_partition(self):
        records = self.records()
        with self.assertRaises(ShortPositioningSchemaError):
            write_normalized_partition(
                [*records, records[0]], root=self.root, request=self.request()
            )
        self.assertEqual(list(self.root.rglob("records-*.json")), [])

    def test_original_and_revised_captures_both_persist(self):
        # FINRA exposes only the latest corrected view, so a re-capture must
        # land beside the original rather than replacing it.
        original_request = self.request(symbols=("ZQXA",), request_id="orig")
        revised_request = self.request(symbols=("ZQXA",), request_id="rev")
        original = self.records("finra_valid.json", request=original_request)[:1]
        revised = self.records("finra_revision.json", request=revised_request)

        first = write_normalized_partition(original, root=self.root, request=original_request)
        second = write_normalized_partition(revised, root=self.root, request=revised_request)

        self.assertNotEqual(first, second)
        self.assertTrue(first.exists() and second.exists())
        self.assertEqual(first.parent, second.parent)

        keys = set()
        for path in sorted(self.root.rglob("records-*.json")):
            keys |= {row["source_record_key"] for row in json.loads(path.read_text())["records"]}
        self.assertEqual(len(keys), 2)
        self.assertTrue(any("revised" in key for key in keys))
        self.assertTrue(any("original" in key for key in keys))

    def test_a_capture_is_immutable_and_never_rewritten(self):
        request = self.request(symbols=("ZQXA",), request_id="orig")
        records = self.records("finra_valid.json", request=request)[:1]
        write_normalized_partition(records, root=self.root, request=request)
        with self.assertRaises(ArtifactIntegrityError):
            write_normalized_partition(records, root=self.root, request=request)

    def test_a_missing_requested_symbol_rolls_the_partition_back(self):
        records = self.records()[:2]
        with self.assertRaises(PartialCaptureError):
            write_normalized_partition(records, root=self.root, request=self.request())
        self.assertEqual(list(self.root.rglob("records-*.json")), [])

    def test_an_interrupted_publish_leaves_no_partition_and_no_temp_file(self):
        with mock.patch(
            "data.short_positioning.normalize.os.replace",
            side_effect=OSError("synthetic interruption"),
        ):
            with self.assertRaises(OSError):
                write_normalized_partition(self.records(), root=self.root, request=self.request())

        self.assertEqual(list(self.root.rglob("records-*.json")), [])
        self.assertEqual([p for p in self.root.rglob("*") if p.suffix == ".tmp"], [])

    def test_an_invalid_record_blocks_the_whole_partition(self):
        records = self.records()
        broken = replace(records[0], current_short_shares=-5)
        with self.assertRaises(ShortPositioningSchemaError):
            write_normalized_partition(
                [*records[1:], broken], root=self.root, request=self.request()
            )
        self.assertEqual(list(self.root.rglob("records-*.json")), [])

    def test_stored_partition_round_trips_share_counts_and_decimals_as_text(self):
        path = write_normalized_partition(self.records(), root=self.root, request=self.request())
        stored = json.loads(path.read_text())
        row = next(r for r in stored["records"] if r["symbol"] == "ZQXA")
        self.assertEqual(row["current_short_shares"], 1_250_000)
        self.assertEqual(row["days_to_cover"], "2.5")
        null_row = next(r for r in stored["records"] if r["symbol"] == "HLGRD")
        self.assertIsNone(null_row["previous_short_shares"])
        self.assertIsNone(null_row["days_to_cover"])


if __name__ == "__main__":
    unittest.main()

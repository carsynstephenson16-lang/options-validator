"""Offline data-audit tests.

The audit reads local artifacts, never repairs them, never reaches a network,
and never writes a row-level provider value into a receipt.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from data.short_positioning.audit import (
    audit_normalized_partition,
    audit_provider_conflicts,
    audit_raw_partition,
    render_short_positioning_audit,
    write_short_positioning_audit_receipt,
)
from data.short_positioning.normalize import write_normalized_partition
from data.short_positioning.provider import CaptureRequest
from data.short_positioning.providers.finra import normalize_finra_row, parse_finra_payload
from data.short_positioning.raw_store import write_raw_artifact
from tools import short_positioning_audit as audit_cli

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
PAYLOAD = (FIXTURES / "finra_valid.json").read_bytes()
RETRIEVED_AT = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
ASOF = datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc)

# Row-level values that must never reach a receipt.
REDACTABLE_VALUE = "FAKE-NOT-A-REAL-CREDENTIAL-4"
ROW_LEVEL_MARKERS = ("1250000", "2500000", "ZEPHYR QUANTA HOLDINGS", "TERRANOVA VECTOR")


class AuditTestCase(unittest.TestCase):
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
            "request_id": "audit-seed",
            "execute": True,
        }
        kwargs.update(overrides)
        return CaptureRequest(**kwargs)

    def seed(self, request=None, *, payload=PAYLOAD, write_raw=True):
        request = request or self.request()
        artifact = None
        if write_raw:
            artifact = write_raw_artifact(
                payload, root=self.root, request=request, retrieved_at=RETRIEVED_AT
            )
        rows = parse_finra_payload(payload)
        records = [
            normalize_finra_row(
                row,
                request=request,
                retrieved_at=RETRIEVED_AT,
                row_ordinal=ordinal,
                raw_sha256=artifact.sha256 if artifact else "0" * 64,
            )
            for ordinal, row in enumerate(rows)
            if row["symbolCode"] in request.symbols
        ]
        write_normalized_partition(records, root=self.root, request=request)
        return artifact

    def audit_raw(self, **overrides):
        kwargs = {
            "provider": "finra",
            "dataset": "consolidated-short-interest",
            "publication_date": date(2026, 7, 17),
        }
        kwargs.update(overrides)
        return audit_raw_partition(self.root, **kwargs)

    def audit_normalized(self, **overrides):
        kwargs = {
            "provider": "finra",
            "dataset": "consolidated-short-interest",
            "publication_date": date(2026, 7, 17),
            "asof": ASOF,
        }
        kwargs.update(overrides)
        return audit_normalized_partition(self.root, **kwargs)


class RawAuditTests(AuditTestCase):
    def test_a_clean_partition_passes(self):
        self.seed()
        report = self.audit_raw()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["counts"]["artifacts"], 1)

    def test_a_tampered_artifact_blocks(self):
        artifact = self.seed()
        assert artifact is not None
        artifact.path.write_bytes(PAYLOAD + b"\n")

        report = self.audit_raw()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("HASH_MISMATCH", [finding["code"] for finding in report["findings"]])

    def test_a_missing_manifest_blocks(self):
        artifact = self.seed()
        assert artifact is not None
        artifact.path.with_suffix(".manifest.json").unlink()

        report = self.audit_raw()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("MISSING_PROVENANCE", [finding["code"] for finding in report["findings"]])

    def test_an_absent_partition_blocks_rather_than_passing_silently(self):
        report = self.audit_raw(publication_date=date(2026, 1, 2))
        self.assertEqual(report["status"], "BLOCK")


class NormalizedAuditTests(AuditTestCase):
    def test_a_clean_partition_passes_with_counts_only(self):
        self.seed()
        report = self.audit_normalized()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["counts"]["records"], 3)
        self.assertEqual(report["counts"]["symbols"], 3)

    def test_duplicate_record_keys_block(self):
        self.seed()
        path = next(self.root.rglob("records-*.json"))
        document = json.loads(path.read_text())
        document["records"].append(document["records"][0])
        path.write_text(json.dumps(document))

        report = self.audit_normalized()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("DUPLICATE_KEY", [finding["code"] for finding in report["findings"]])

    def test_a_future_row_is_refused(self):
        self.seed()
        report = self.audit_normalized(asof=datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("FUTURE_DATA", [finding["code"] for finding in report["findings"]])

    def test_source_version_drift_across_rows_blocks(self):
        self.seed()
        path = next(self.root.rglob("records-*.json"))
        document = json.loads(path.read_text())
        document["records"][0]["source_provenance"]["source_field_map_version"] = "drifted/v9"
        path.write_text(json.dumps(document))

        report = self.audit_normalized()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SOURCE_VERSION_DRIFT", [finding["code"] for finding in report["findings"]])

    def test_a_malformed_partition_blocks_with_a_schema_error(self):
        self.seed()
        next(self.root.rglob("records-*.json")).write_text("{not json")
        report = self.audit_normalized()
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SCHEMA_ERROR", [finding["code"] for finding in report["findings"]])

    def test_the_audit_never_repairs_the_partition(self):
        self.seed()
        path = next(self.root.rglob("records-*.json"))
        document = json.loads(path.read_text())
        document["records"].append(document["records"][0])
        broken = json.dumps(document)
        path.write_text(broken)

        self.audit_normalized()
        self.assertEqual(path.read_text(), broken)


class ProviderConflictTests(AuditTestCase):
    def test_agreeing_providers_pass(self):
        self.seed()
        self.seed(self.request(provider="synthetic", request_id="synthetic-seed"))
        report = audit_provider_conflicts(
            self.root,
            dataset="consolidated-short-interest",
            providers=("finra", "synthetic"),
            asof=ASOF,
        )
        self.assertEqual(report["status"], "PASS")

    def test_disagreeing_providers_are_reported_without_choosing_a_winner(self):
        self.seed()
        other = self.request(provider="synthetic", request_id="synthetic-seed")
        altered = json.loads(PAYLOAD.decode())
        altered[0]["currentShortPositionQuantity"] = 1_400_000
        altered[0]["changePreviousNumber"] = 400_000
        altered[0]["changePercent"] = 40.0
        self.seed(other, payload=json.dumps(altered).encode())

        report = audit_provider_conflicts(
            self.root,
            dataset="consolidated-short-interest",
            providers=("finra", "synthetic"),
            asof=ASOF,
        )
        self.assertEqual(report["status"], "BLOCK")
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("PROVIDER_CONFLICT", codes)
        rendered = json.dumps(report)
        for marker in ("1400000", "1250000"):
            self.assertNotIn(marker, rendered)

    def test_a_malformed_partition_produces_a_blocking_finding_not_a_crash(self):
        self.seed()
        partition = next(self.root.rglob("records-*.json"))
        partition.write_text("{not json")

        report = audit_provider_conflicts(
            self.root, dataset="consolidated-short-interest", providers=("finra",), asof=ASOF
        )
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SCHEMA_ERROR", [finding["code"] for finding in report["findings"]])

    def test_a_row_missing_symbol_produces_a_blocking_finding_not_a_crash(self):
        self.seed()
        partition = next(self.root.rglob("records-*.json"))
        document = json.loads(partition.read_text())
        del document["records"][0]["symbol"]
        partition.write_text(json.dumps(document))

        report = audit_provider_conflicts(
            self.root, dataset="consolidated-short-interest", providers=("finra",), asof=ASOF
        )
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SCHEMA_ERROR", [finding["code"] for finding in report["findings"]])

    def test_a_negative_share_partition_blocks_without_crashing_the_conflict_scan(self):
        self.seed()
        partition = next(self.root.rglob("records-*.json"))
        document = json.loads(partition.read_text())
        document["records"][0]["current_short_shares"] = -1
        partition.write_text(json.dumps(document))

        report = audit_provider_conflicts(
            self.root, dataset="consolidated-short-interest", providers=("finra",), asof=ASOF
        )
        self.assertEqual(report["status"], "BLOCK")
        self.assertIn("SCHEMA_ERROR", [finding["code"] for finding in report["findings"]])


class ReceiptTests(AuditTestCase):
    def test_receipt_carries_statuses_and_counts_but_no_row_level_values(self):
        self.seed()
        report = {
            "root": str(self.root),
            "checks": [self.audit_raw(), self.audit_normalized()],
        }
        path = write_short_positioning_audit_receipt(report, self.root / "receipt.json")
        text = path.read_text()

        self.assertIn("PASS", text)
        for marker in ROW_LEVEL_MARKERS:
            self.assertNotIn(marker, text)

    def test_receipt_redacts_anything_that_looks_like_a_credential(self):
        self.seed()
        report = {
            "root": str(self.root),
            "note": f"operator token {REDACTABLE_VALUE}",
            "checks": [self.audit_raw()],
        }
        path = write_short_positioning_audit_receipt(report, self.root / "receipt.json")
        self.assertNotIn(REDACTABLE_VALUE, path.read_text())

    def test_render_is_human_readable_and_lists_every_check(self):
        self.seed()
        rendered = render_short_positioning_audit(
            {"root": str(self.root), "checks": [self.audit_raw(), self.audit_normalized()]}
        )
        self.assertIn("raw_partition", rendered)
        self.assertIn("normalized_partition", rendered)
        self.assertIn("PASS", rendered)
        for marker in ROW_LEVEL_MARKERS:
            self.assertNotIn(marker, rendered)


class AuditCliTests(AuditTestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = audit_cli.main(argv)
        return code, out.getvalue() + err.getvalue()

    def argv(self, *extra):
        return [
            "--root",
            str(self.root),
            "--provider",
            "finra",
            "--dataset",
            "consolidated-short-interest",
            "--through-publication-date",
            "2026-07-17",
            "--asof",
            "2026-07-21T20:00:00+00:00",
            *extra,
        ]

    def test_exit_zero_when_the_audit_passes(self):
        self.seed()
        code, output = self.run_cli(self.argv())
        self.assertEqual(code, 0)
        self.assertIn("PASS", output)

    def test_exit_two_when_the_audit_blocks(self):
        artifact = self.seed()
        assert artifact is not None
        artifact.path.write_bytes(PAYLOAD + b"\n")

        code, output = self.run_cli(self.argv("--strict"))
        self.assertEqual(code, 2)
        self.assertIn("BLOCK", output)

    def test_cli_output_carries_no_row_level_values(self):
        self.seed()
        _code, output = self.run_cli(self.argv())
        for marker in ROW_LEVEL_MARKERS:
            self.assertNotIn(marker, output)


if __name__ == "__main__":
    unittest.main()

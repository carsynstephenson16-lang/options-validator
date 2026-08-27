"""Offline tests for the read-only receipt-backed job-health digest.

Fixture schemas were copied from the current producers. Market values and
paths were reduced to the fields needed by this consumer after confirming the
source receipts contain no credentials or account identifiers.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from options_researcher.h7_scope import watch_universe
from research.hashing import canonical_json, sha256_file, sha256_hex
from tools import schwab_chain_manifest
from tools.job_health_digest import HealthStatus, collect_health, render_digest

AS_OF = "2026-08-21"
FIXTURES = Path(__file__).parent / "fixtures" / "job_health"
REPO_ROOT = Path(__file__).resolve().parents[1]
NY_TZ = ZoneInfo("America/New_York")
WATCH_UNIVERSE = tuple(watch_universe())
INTRADAY_FIXTURE_FIELDS = {
    "open_auction": ("09:31", "09:31:00", "13:31:00"),
    "open": ("09:35", "09:35:00", "13:35:00"),
    "midmorning": ("11:00", "11:00:00", "15:00:00"),
    "midday": ("13:00", "13:00:00", "17:00:00"),
    "preclose": ("15:45", "15:45:00", "19:45:00"),
}


class JobHealthDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.root_dir.cleanup)
        self.root = Path(self.root_dir.name)

    def _copy(self, fixture: str, relative: str) -> Path:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / fixture, target)
        return target

    def _install_intraday_tag(self, tag: str) -> Path:
        scheduled, captured_et, captured_utc = INTRADAY_FIXTURE_FIELDS[tag]
        payload = json.loads((FIXTURES / "intraday_preclose.json").read_text())
        payload.update(
            {
                "session_tag": tag,
                "scheduled_et": scheduled,
                "captured_at_et": f"{AS_OF}T{captured_et}-04:00",
                "captured_at_utc": f"{AS_OF}T{captured_utc}+00:00",
                "universe": list(WATCH_UNIVERSE),
                "names": {symbol: {"symbol": symbol, "status": "ok"} for symbol in WATCH_UNIVERSE},
            }
        )
        path = self.root / f"reports/intraday_capture/{AS_OF}/{tag}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return path

    def _install_schwab_package(self, symbols: list[str] | None = None) -> None:
        chain_dir = self.root / ".cache" / "schwab_chains"
        report_dir = self.root / "reports" / "schwab_chains" / AS_OF
        chain_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(
            [
                {"expiration": "2026-09-18", "strike": 100.0},
                {"expiration": "2026-10-16", "strike": 105.0},
            ]
        )
        symbols = sorted(WATCH_UNIVERSE if symbols is None else symbols)
        names = {}
        for symbol in symbols:
            path = chain_dir / f"{symbol}_{AS_OF}.parquet"
            frame.to_parquet(path)
            names[symbol] = {
                "status": "ok",
                "row_count": 2,
                "expiration_count": 2,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "path": f".cache/schwab_chains/{path.name}",
            }
        manifest = schwab_chain_manifest.build_manifest(AS_OF, symbols, chain_dir)
        schwab_chain_manifest.write_manifest(manifest, report_dir / "manifest.json")
        receipt = json.loads((FIXTURES / "schwab_preclose.json").read_text())
        receipt.update(
            {
                "manifest_hash": manifest["manifest_hash"],
                "names": names,
                "universe": symbols,
            }
        )
        (report_dir / "preclose.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )

    @staticmethod
    def _set_mtime_for_invocation_date(path: Path, invocation_date) -> None:
        timestamp = datetime.combine(invocation_date, time(12), tzinfo=NY_TZ).timestamp()
        os.utime(path, (timestamp, timestamp))

    def _install_all_ok(self) -> None:
        self._copy("run_status.json", f"reports/ritual/run_status_{AS_OF}.json")
        self._copy(
            "capture_receipt.json",
            f"reports/ritual/capture_receipt_{AS_OF}.json",
        )
        for tag in INTRADAY_FIXTURE_FIELDS:
            self._install_intraday_tag(tag)
        self._install_schwab_package()
        self._copy("alignment.log", f".tmp/alignment_check/{AS_OF}.log")
        self._copy(
            "research_refresh.json",
            f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json",
        )

    @staticmethod
    def _by_job(rows):
        return {row.job: row for row in rows}

    def test_current_producer_shapes_classify_as_ok(self):
        self._install_all_ok()

        rows = self._by_job(collect_health(self.root, AS_OF))

        for job in (
            "Ritual overall",
            "Ritual hypotheses",
            "Intraday capture (open_auction)",
            "Intraday capture (open)",
            "Intraday capture (midmorning)",
            "Intraday capture (midday)",
            "Intraday capture (preclose)",
            "Schwab preclose",
            "Alignment check",
            "Research refresh (midmorning)",
        ):
            self.assertEqual(rows[job].status, HealthStatus.OK, job)
        self.assertEqual(
            rows["Research display refresh"].status,
            HealthStatus.NOT_INSTRUMENTED,
        )
        self.assertNotIn("Live dashboard", rows)

    def test_ritual_hypotheses_requires_exact_registered_key_set(self):
        self._install_all_ok()
        path = self.root / f"reports/ritual/capture_receipt_{AS_OF}.json"
        original = json.loads(path.read_text())
        cases = (
            (
                {key: value for key, value in original["hypotheses"].items() if key != "H10"},
                "missing=H10",
            ),
            ({**original["hypotheses"], "H11": original["hypotheses"]["H10"]}, "unexpected=H11"),
        )
        for hypotheses, reason in cases:
            with self.subTest(reason=reason):
                payload = {**original, "hypotheses": hypotheses}
                path.write_text(json.dumps(payload))

                row = self._by_job(collect_health(self.root, AS_OF))["Ritual hypotheses"]

                self.assertEqual(row.status, HealthStatus.FAILED)
                self.assertIn(reason, row.reason)

    def test_ritual_hypotheses_requires_matching_capture_session(self):
        self._install_all_ok()
        capture = self.root / f"reports/ritual/capture_receipt_{AS_OF}.json"
        payload = json.loads(capture.read_text())
        payload["as_of"] = "2026-08-20"
        capture.write_text(json.dumps(payload))
        status = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        status_payload = json.loads(status.read_text())
        status_payload["capture_receipt_sha256"] = sha256_file(capture)
        status.write_text(json.dumps(status_payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Ritual hypotheses"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("session mismatch", row.reason)

    def test_all_five_intraday_tags_are_classified_independently(self):
        self._install_all_ok()

        rows = collect_health(self.root, AS_OF)
        intraday = [(row.job, row.status) for row in rows if row.job.startswith("Intraday capture")]

        self.assertEqual(
            intraday,
            [
                ("Intraday capture (open_auction)", HealthStatus.OK),
                ("Intraday capture (open)", HealthStatus.OK),
                ("Intraday capture (midmorning)", HealthStatus.OK),
                ("Intraday capture (midday)", HealthStatus.OK),
                ("Intraday capture (preclose)", HealthStatus.OK),
            ],
        )

    def test_one_good_intraday_tag_does_not_mask_four_missing_launches(self):
        self._install_intraday_tag("preclose")

        rows = collect_health(self.root, AS_OF)
        intraday = [(row.job, row.status) for row in rows if row.job.startswith("Intraday capture")]

        self.assertEqual(
            intraday,
            [
                ("Intraday capture (open_auction)", HealthStatus.MISSING),
                ("Intraday capture (open)", HealthStatus.MISSING),
                ("Intraday capture (midmorning)", HealthStatus.MISSING),
                ("Intraday capture (midday)", HealthStatus.MISSING),
                ("Intraday capture (preclose)", HealthStatus.OK),
            ],
        )

    def test_intraday_tag_receipt_identity_must_match_expected_slot(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/open.json"
        original = json.loads(path.read_text())
        cases = (
            ("receipt_kind", "intraday_capture/v0", "receipt_kind mismatch"),
            ("force", True, "force must be false"),
            ("session_tag", "preclose", "session_tag mismatch"),
            ("scheduled_et", "15:45", "scheduled_et mismatch"),
            ("captured_at_utc", "2026-08-20T13:35:00+00:00", "session mismatch"),
        )
        for field, value, reason in cases:
            with self.subTest(field=field):
                path.write_text(json.dumps({**original, field: value}))

                row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture (open)"]

                self.assertEqual(row.status, HealthStatus.FAILED)
                self.assertIn(reason, row.reason)

    def test_capture_receipts_require_canonical_watch_universe(self):
        self._install_intraday_tag("open")
        intraday_path = self.root / f"reports/intraday_capture/{AS_OF}/open.json"
        intraday = json.loads(intraday_path.read_text())
        omitted = intraday["universe"].pop()
        del intraday["names"][omitted]
        intraday_path.write_text(json.dumps(intraday))
        self._install_schwab_package(["CEG", "VST"])

        rows = self._by_job(collect_health(self.root, AS_OF))

        for job in ("Intraday capture (open)", "Schwab preclose"):
            with self.subTest(job=job):
                self.assertEqual(rows[job].status, HealthStatus.FAILED)
                self.assertIn("canonical watch universe", rows[job].reason)

    def test_schwab_preclose_requires_unforced_launchd_receipt(self):
        self._install_all_ok()
        path = self.root / f"reports/schwab_chains/{AS_OF}/preclose.json"
        original = json.loads(path.read_text())
        cases = (
            ("force", True, HealthStatus.FAILED, "force=false"),
            ("invocation_source", "manual", HealthStatus.DEGRADED, "launchd"),
        )
        for field, value, status, reason in cases:
            with self.subTest(field=field):
                path.write_text(json.dumps({**original, field: value}))

                row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

                self.assertEqual(row.status, status)
                self.assertIn(reason, row.reason)

    def test_schwab_manifest_failure_overrides_policy_degradation(self):
        self._install_all_ok()
        chain = self.root / ".cache" / "schwab_chains" / f"CEG_{AS_OF}.parquet"
        with chain.open("r+b") as stream:
            stream.seek(16)
            original_byte = stream.read(1)
            stream.seek(16)
            stream.write(bytes([original_byte[0] ^ 0x01]))
        receipt = self.root / f"reports/schwab_chains/{AS_OF}/preclose.json"
        original = json.loads(receipt.read_text())
        cases = (("force", True), ("invocation_source", "manual"))
        for field, value in cases:
            with self.subTest(field=field):
                receipt.write_text(json.dumps({**original, field: value}))

                row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

                self.assertEqual(row.status, HealthStatus.FAILED)
                self.assertIn("manifest verification failed", row.reason)

    def test_schwab_preclose_runs_offline_manifest_verification(self):
        self._install_all_ok()
        chain = self.root / ".cache" / "schwab_chains" / f"CEG_{AS_OF}.parquet"
        with chain.open("r+b") as stream:
            stream.seek(16)
            original = stream.read(1)
            stream.seek(16)
            stream.write(bytes([original[0] ^ 0x01]))

        row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("manifest verification failed", row.reason)

    def test_schwab_nonfinite_manifest_value_is_failed(self):
        self._install_all_ok()
        manifest = self.root / f"reports/schwab_chains/{AS_OF}/manifest.json"
        payload = json.loads(manifest.read_text())
        payload["invalid_nonfinite"] = float("nan")
        manifest.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("manifest verification failed", row.reason)

    def test_schwab_malformed_byte_consistent_parquet_is_failed(self):
        self._install_all_ok()
        chain = self.root / ".cache" / "schwab_chains" / f"CEG_{AS_OF}.parquet"
        malformed = pd.DataFrame(
            [
                {"expiration": ["2026-09-18"], "strike": 100.0},
                {"expiration": ["2026-10-16"], "strike": 105.0},
            ]
        )
        malformed.to_parquet(chain)
        actual_hash = sha256_file(chain)
        actual_size = chain.stat().st_size

        manifest_path = self.root / f"reports/schwab_chains/{AS_OF}/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["files"]["CEG"].update({"sha256": actual_hash, "size_bytes": actual_size})
        manifest_body = {key: value for key, value in manifest.items() if key != "manifest_hash"}
        manifest["manifest_hash"] = sha256_hex(canonical_json(manifest_body))
        manifest_path.write_text(json.dumps(manifest))

        receipt_path = self.root / f"reports/schwab_chains/{AS_OF}/preclose.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["manifest_hash"] = manifest["manifest_hash"]
        receipt["names"]["CEG"].update({"sha256": actual_hash, "size_bytes": actual_size})
        receipt_path.write_text(json.dumps(receipt))

        row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("manifest verification failed", row.reason)

    def test_schwab_manifest_symlink_cannot_escape_root(self):
        self._install_all_ok()
        external_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, external_dir, True)
        manifest = self.root / f"reports/schwab_chains/{AS_OF}/manifest.json"
        external = external_dir / "manifest.json"
        manifest.replace(external)
        manifest.symlink_to(external)

        row = self._by_job(collect_health(self.root, AS_OF))["Schwab preclose"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("escapes root", row.reason)

    def test_approved_status_mappings_fail_closed(self):
        self._install_all_ok()
        run_path = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        run_payload = json.loads(run_path.read_text())
        run_payload["status"] = "BROKEN"
        run_path.write_text(json.dumps(run_payload))

        capture_path = self.root / f"reports/ritual/capture_receipt_{AS_OF}.json"
        capture_payload = json.loads(capture_path.read_text())
        capture_payload["hypotheses"]["H5"]["status"] = "REFUSED"
        capture_payload["hypotheses"]["H7"]["status"] = "MISSING"
        capture_path.write_text(json.dumps(capture_payload))

        schwab_path = self.root / f"reports/schwab_chains/{AS_OF}/preclose.json"
        schwab_payload = json.loads(schwab_path.read_text())
        schwab_payload["overall_status"] = "failed"
        schwab_path.write_text(json.dumps(schwab_payload))

        alignment_path = self.root / f".tmp/alignment_check/{AS_OF}.log"
        alignment_path.write_text(
            "2026-08-21T15:30:00-0400 status=AHEAD_CODE branch=main detail=refused\n"
        )

        rows = self._by_job(collect_health(self.root, AS_OF))

        self.assertEqual(rows["Ritual overall"].status, HealthStatus.FAILED)
        self.assertEqual(rows["Ritual hypotheses"].status, HealthStatus.DEGRADED)
        self.assertIn("H5=REFUSED", rows["Ritual hypotheses"].reason)
        self.assertEqual(rows["Schwab preclose"].status, HealthStatus.FAILED)
        self.assertEqual(rows["Alignment check"].status, HealthStatus.FAILED)

    def test_ritual_overall_maps_every_producer_status(self):
        self._install_all_ok()
        path = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        expected = {
            "OK": HealthStatus.OK,
            "OK_STARVED": HealthStatus.DEGRADED,
            "RUNNING": HealthStatus.DEGRADED,
            "BROKEN": HealthStatus.FAILED,
        }
        for producer_status, health_status in expected.items():
            with self.subTest(status=producer_status):
                payload = json.loads(path.read_text())
                payload["status"] = producer_status
                path.write_text(json.dumps(payload))

                row = self._by_job(collect_health(self.root, AS_OF))["Ritual overall"]

                self.assertEqual(row.status, health_status)

    def test_ritual_overall_verifies_capture_receipt_hash(self):
        self._install_all_ok()
        capture = self.root / f"reports/ritual/capture_receipt_{AS_OF}.json"
        capture.write_text(capture.read_text() + "\n")

        row = self._by_job(collect_health(self.root, AS_OF))["Ritual overall"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("capture_receipt_sha256 mismatch", row.reason)

    def test_ritual_overall_validates_status_receipt_identity(self):
        self._install_all_ok()
        path = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        cases = (
            ("schema_version", "daily_ritual/run_status/v0", "schema_version mismatch"),
            ("as_of", "2026-08-20", "session mismatch"),
            (
                "capture_receipt_path",
                "reports/ritual/capture_receipt_other.json",
                "capture_receipt_path mismatch",
            ),
        )
        original = json.loads(path.read_text())
        for field, value, reason in cases:
            with self.subTest(field=field):
                payload = dict(original)
                payload[field] = value
                path.write_text(json.dumps(payload))

                row = self._by_job(collect_health(self.root, AS_OF))["Ritual overall"]

                self.assertEqual(row.status, HealthStatus.FAILED)
                self.assertIn(reason, row.reason)

    def test_wrong_typed_status_fields_fail_closed(self):
        self._install_all_ok()
        overall_path = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        overall = json.loads(overall_path.read_text())
        overall["status"] = ["BROKEN"]
        overall_path.write_text(json.dumps(overall))

        capture_path = self.root / f"reports/ritual/capture_receipt_{AS_OF}.json"
        capture = json.loads(capture_path.read_text())
        capture["hypotheses"]["H5"]["status"] = ["REFUSED"]
        capture_path.write_text(json.dumps(capture))

        rows = self._by_job(collect_health(self.root, AS_OF))

        self.assertEqual(rows["Ritual overall"].status, HealthStatus.FAILED)
        self.assertEqual(rows["Ritual hypotheses"].status, HealthStatus.FAILED)

    def test_fixed_receipt_symlinks_cannot_escape_root(self):
        external_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, external_dir, True)
        cases = (
            (
                "Ritual overall",
                "run_status.json",
                f"reports/ritual/run_status_{AS_OF}.json",
            ),
            (
                "Ritual hypotheses",
                "capture_receipt.json",
                f"reports/ritual/capture_receipt_{AS_OF}.json",
            ),
            (
                "Schwab preclose",
                "schwab_preclose.json",
                f"reports/schwab_chains/{AS_OF}/preclose.json",
            ),
            (
                "Alignment check",
                "alignment.log",
                f".tmp/alignment_check/{AS_OF}.log",
            ),
            (
                "Research refresh (midmorning)",
                "research_refresh.json",
                f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json",
            ),
        )
        for _job, fixture, relative in cases:
            external = external_dir / fixture
            shutil.copyfile(FIXTURES / fixture, external)
            link = self.root / relative
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(external)

        rows = self._by_job(collect_health(self.root, AS_OF))

        for job, _fixture, _relative in cases:
            with self.subTest(job=job):
                self.assertEqual(rows[job].status, HealthStatus.FAILED)
                self.assertIn("escapes root", rows[job].reason)

    def test_alignment_evidence_only_is_degraded(self):
        self._install_all_ok()
        path = self.root / f".tmp/alignment_check/{AS_OF}.log"
        path.write_text(
            "2026-08-21T15:30:00-0400 status=AHEAD_EVIDENCE_ONLY "
            "branch=main detail=capture remains allowed\n"
        )

        row = self._by_job(collect_health(self.root, AS_OF))["Alignment check"]

        self.assertEqual(row.status, HealthStatus.DEGRADED)

    def test_intraday_tags_aggregate_coverage_independently(self):
        self._install_all_ok()
        preclose_path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(preclose_path.read_text())
        payload["names"]["VST"] = {
            "symbol": "VST",
            "status": "unavailable",
            "note": "provider unreachable",
        }
        preclose_path.write_text(json.dumps(payload))

        rows = self._by_job(collect_health(self.root, AS_OF))
        row = rows["Intraday capture (preclose)"]

        self.assertEqual(row.status, HealthStatus.DEGRADED)
        self.assertEqual(row.path, f"reports/intraday_capture/{AS_OF}/preclose.json")
        self.assertIn(f"{len(WATCH_UNIVERSE) - 1}/{len(WATCH_UNIVERSE)}", row.reason)
        self.assertEqual(rows["Intraday capture (open)"].status, HealthStatus.OK)

    def test_zero_intraday_coverage_is_failed(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        for row in payload["names"].values():
            row["status"] = "unavailable"
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture (preclose)"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn(f"0/{len(WATCH_UNIVERSE)}", row.reason)

    def test_intraday_missing_expected_symbol_row_is_failed(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        del payload["names"]["VST"]
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture (preclose)"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("missing symbol rows: VST", row.reason)

    def test_intraday_row_symbol_must_match_its_name_key(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        payload["names"]["VST"]["symbol"] = "CEG"
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture (preclose)"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("symbol identity mismatch", row.reason)

    def test_intraday_receipt_symlink_cannot_escape_root(self):
        external_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, external_dir, True)
        external = external_dir / "preclose.json"
        shutil.copyfile(FIXTURES / "intraday_preclose.json", external)
        directory = self.root / f"reports/intraday_capture/{AS_OF}"
        directory.mkdir(parents=True)
        (directory / "preclose.json").symlink_to(external)

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture (preclose)"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("escapes root", row.reason)

    def test_intraday_directory_symlink_cannot_escape_root(self):
        external_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, external_dir, True)
        shutil.copyfile(
            FIXTURES / "intraday_preclose.json",
            external_dir / "preclose.json",
        )
        parent = self.root / "reports" / "intraday_capture"
        parent.mkdir(parents=True)
        (parent / AS_OF).symlink_to(external_dir, target_is_directory=True)

        rows = self._by_job(collect_health(self.root, AS_OF))

        for tag in INTRADAY_FIXTURE_FIELDS:
            with self.subTest(tag=tag):
                row = rows[f"Intraday capture ({tag})"]
                self.assertEqual(row.status, HealthStatus.FAILED)
                self.assertIn("escapes root", row.reason)

    def test_research_refresh_ignores_payload_after_freshness_check(self):
        self._install_all_ok()
        path = self.root / f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json"
        path.write_text("this is deliberately not JSON\n")

        row = self._by_job(collect_health(self.root, AS_OF))["Research refresh (midmorning)"]

        self.assertEqual(row.status, HealthStatus.OK)
        self.assertIn("fresh", row.reason)

    def test_real_world_august_21_absence_is_reported_as_problems(self):
        self._copy("alignment.log", f".tmp/alignment_check/{AS_OF}.log")

        rows = collect_health(self.root, AS_OF)
        digest = render_digest(AS_OF, rows)

        by_job = self._by_job(rows)
        for job in (
            "Ritual overall",
            "Ritual hypotheses",
            "Intraday capture (open_auction)",
            "Intraday capture (open)",
            "Intraday capture (midmorning)",
            "Intraday capture (midday)",
            "Intraday capture (preclose)",
            "Schwab preclose",
            "Research refresh (midmorning)",
        ):
            self.assertEqual(by_job[job].status, HealthStatus.MISSING, job)
        self.assertEqual(by_job["Alignment check"].status, HealthStatus.OK)
        self.assertTrue(digest.startswith("9 PROBLEMS\n"), digest)

    def test_xnys_holiday_reports_no_session_without_problems(self):
        holiday = "2026-12-25"

        rows = collect_health(self.root, holiday)
        digest = render_digest(holiday, rows)

        session_rows = [row for row in rows if row.status is not HealthStatus.NOT_INSTRUMENTED]
        self.assertTrue(session_rows)
        self.assertTrue(all(row.status is HealthStatus.NO_SESSION for row in session_rows))
        self.assertTrue(digest.startswith("ALL OK\n"), digest)
        self.assertIn("NO_SESSION", digest)
        self.assertNotIn("MISSING", digest)

    def test_malformed_json_is_failed_instead_of_raising(self):
        self._install_all_ok()
        path = self.root / f"reports/ritual/run_status_{AS_OF}.json"
        path.write_text("{broken\n")

        row = self._by_job(collect_health(self.root, AS_OF))["Ritual overall"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("invalid JSON", row.reason)

    def test_digest_sorts_worst_first_and_counts_only_problems(self):
        self._install_all_ok()
        os.remove(self.root / f"reports/ritual/run_status_{AS_OF}.json")
        path = self.root / f"reports/schwab_chains/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        payload["overall_status"] = "failed"
        path.write_text(json.dumps(payload))

        digest = render_digest(AS_OF, collect_health(self.root, AS_OF))

        self.assertTrue(digest.startswith("2 PROBLEMS\n"), digest)
        table_rows = [line for line in digest.splitlines() if line.startswith("|")][2:]
        statuses = [line.split("|")[2].strip() for line in table_rows]
        self.assertLess(statuses.index("FAILED"), statuses.index("MISSING"))
        self.assertLess(statuses.index("MISSING"), statuses.index("OK"))
        self.assertEqual(digest.count("| Job | Status | Reason | Receipt path |"), 1)

    def test_cli_reads_research_receipt_from_separate_root(self):
        self._install_all_ok()
        (self.root / f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json").unlink()
        research_dir = Path(tempfile.mkdtemp())
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, research_dir, True)
        self.addCleanup(shutil.rmtree, output_dir, True)
        receipt = research_dir / f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json"
        receipt.parent.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "research_refresh.json", receipt)
        self._set_mtime_for_invocation_date(receipt, datetime.now(NY_TZ).date())

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(research_dir),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("| Research refresh (midmorning) | OK |", completed.stdout)

    def test_cli_default_research_root_is_under_home(self):
        self._install_all_ok()
        (self.root / f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json").unlink()
        home = Path(tempfile.mkdtemp())
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home, True)
        self.addCleanup(shutil.rmtree, output_dir, True)
        receipt = (
            home
            / "options-validator-research"
            / ".tmp"
            / "research_refresh"
            / f"receipt_v2_{AS_OF}_midmorning.json"
        )
        receipt.parent.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "research_refresh.json", receipt)
        self._set_mtime_for_invocation_date(receipt, datetime.now(NY_TZ).date())

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "HOME": str(home), "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("| Research refresh (midmorning) | OK |", completed.stdout)

    def test_research_refresh_requires_invocation_date_freshness(self):
        self._install_all_ok()
        research_dir = Path(tempfile.mkdtemp())
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, research_dir, True)
        self.addCleanup(shutil.rmtree, output_dir, True)
        receipt = research_dir / f".tmp/research_refresh/receipt_v2_{AS_OF}_midmorning.json"
        receipt.parent.mkdir(parents=True)
        shutil.copyfile(FIXTURES / "research_refresh.json", receipt)
        invocation_date = datetime.now(NY_TZ).date()
        self._set_mtime_for_invocation_date(receipt, invocation_date - timedelta(days=1))

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(research_dir),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("| Research refresh (midmorning) | MISSING |", completed.stdout)
        self.assertIn(f"not fresh for invocation date {invocation_date}", completed.stdout)

    def test_cli_out_dir_is_the_exact_digest_directory(self):
        self._install_all_ok()
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, output_dir, True)

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        output = output_dir / f"digest_{AS_OF}.md"
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, output.read_text())
        self.assertFalse((output_dir / ".tmp" / "job_health").exists())

    def test_cli_allows_output_under_read_roots_equal_to_cwd(self):
        self._install_all_ok()
        output_dir = self.root / ".tmp" / "job_health"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=self.root,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue((output_dir / f"digest_{AS_OF}.md").is_file())

    def test_cli_rejects_output_under_a_different_checkout_read_root(self):
        self._install_all_ok()
        invoking_dir = Path(tempfile.mkdtemp())
        other_research = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, invoking_dir, True)
        self.addCleanup(shutil.rmtree, other_research, True)
        cases = (
            (self.root, other_research, self.root / ".tmp" / "job_health", "--root"),
            (
                invoking_dir,
                other_research,
                other_research / ".tmp" / "job_health",
                "--research-root",
            ),
        )
        for root, research_root, output_dir, label in cases:
            with self.subTest(label=label):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "tools.job_health_digest",
                        "--root",
                        str(root),
                        "--research-root",
                        str(research_root),
                        "--out-dir",
                        str(output_dir),
                        "--as-of",
                        AS_OF,
                    ],
                    cwd=invoking_dir,
                    env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
                    capture_output=True,
                    text=True,
                )

                self.assertEqual(completed.returncode, 2)
                self.assertIn(
                    f"--out-dir resolves inside {label} for a different checkout",
                    completed.stderr,
                )
                self.assertFalse((output_dir / f"digest_{AS_OF}.md").exists())

    def test_cli_rejects_symlinked_digest_target_without_following_it(self):
        self._install_all_ok()
        output_dir = Path(tempfile.mkdtemp())
        external_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, output_dir, True)
        self.addCleanup(shutil.rmtree, external_dir, True)
        external = external_dir / "outside.md"
        external.write_text("preserve me\n")
        (output_dir / f"digest_{AS_OF}.md").symlink_to(external)

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--out-dir",
                str(output_dir),
                "--as-of",
                AS_OF,
            ],
            cwd=REPO_ROOT,
            env={**os.environ, "PYTHONPATH": str(REPO_ROOT)},
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("digest output path must not be a symlink", completed.stderr)
        self.assertEqual(external.read_text(), "preserve me\n")

    def test_cli_prints_digest_and_writes_only_under_invoking_cwd(self):
        self._install_all_ok()
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, output_dir, True)
        before = sorted(path.relative_to(self.root) for path in self.root.rglob("*"))
        env = {
            **os.environ,
            "PYTHONPATH": str(REPO_ROOT),
        }

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        output = output_dir / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.stdout, output.read_text())
        self.assertEqual(
            sorted(path.relative_to(self.root) for path in self.root.rglob("*")),
            before,
        )
        self.assertEqual(
            [path for path in output_dir.rglob("*") if path.is_file()],
            [output],
        )

    def test_cli_without_root_reads_and_writes_under_invoking_cwd(self):
        self._install_all_ok()
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        output = self.root / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.stdout, output.read_text())

    def test_cli_accepts_explicit_root_from_invoking_subdirectory(self):
        self._install_all_ok()
        output_dir = self.root / "nested_invocation"
        output_dir.mkdir()
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        output = output_dir / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, output.read_text())

    def test_cli_rejects_outer_root_from_nested_worktree(self):
        self._install_all_ok()
        (self.root / ".git").mkdir()
        nested_worktree = self.root / ".tmp" / "worktrees" / "review"
        nested_worktree.mkdir(parents=True)
        (nested_worktree / ".git").write_text("gitdir: ../../../../.git/worktrees/review\n")
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=nested_worktree,
            env=env,
            capture_output=True,
            text=True,
        )

        output = nested_worktree / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "--out-dir resolves inside --root for a different checkout",
            completed.stderr,
        )
        self.assertFalse(output.exists())

    def test_cli_rejects_unknown_outer_root_from_known_nested_checkout(self):
        self._install_all_ok()
        nested_checkout = self.root / "nested_checkout"
        nested_checkout.mkdir()
        (nested_checkout / ".git").write_text("gitdir: ../git-data\n")
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=nested_checkout,
            env=env,
            capture_output=True,
            text=True,
        )

        output = nested_checkout / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.returncode, 2)
        self.assertIn(
            "--out-dir resolves inside --root for a different checkout",
            completed.stderr,
        )
        self.assertFalse(output.exists())

    def test_cli_accepts_explicit_root_equal_to_invoking_cwd(self):
        self._install_all_ok()
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )

        output = self.root / ".tmp" / "job_health" / f"digest_{AS_OF}.md"
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, output.read_text())

    def test_cli_rejects_calendar_dates_outside_supported_range(self):
        output_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, output_dir, True)
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--research-root",
                str(self.root),
                "--as-of",
                "0001-01-01",
            ],
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("outside supported XNYS calendar range", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)
        self.assertFalse((output_dir / ".tmp" / "job_health").exists())


if __name__ == "__main__":
    unittest.main()

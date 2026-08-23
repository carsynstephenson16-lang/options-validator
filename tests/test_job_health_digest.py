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
from pathlib import Path

from tools.job_health_digest import HealthStatus, collect_health, render_digest

AS_OF = "2026-08-21"
FIXTURES = Path(__file__).parent / "fixtures" / "job_health"
REPO_ROOT = Path(__file__).resolve().parents[1]


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

    def _install_all_ok(self) -> None:
        self._copy("run_status.json", f"reports/ritual/run_status_{AS_OF}.json")
        self._copy(
            "capture_receipt.json",
            f"reports/ritual/capture_receipt_{AS_OF}.json",
        )
        self._copy(
            "intraday_preclose.json",
            f"reports/intraday_capture/{AS_OF}/preclose.json",
        )
        self._copy(
            "schwab_preclose.json",
            f"reports/schwab_chains/{AS_OF}/preclose.json",
        )
        self._copy("alignment.log", f".tmp/alignment_check/{AS_OF}.log")
        self._copy(
            "research_refresh.json",
            f".tmp/research_refresh/receipt_v2_{AS_OF}_premarket.json",
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
            "Intraday capture",
            "Schwab preclose",
            "Alignment check",
            "Research refresh (premarket)",
        ):
            self.assertEqual(rows[job].status, HealthStatus.OK, job)
        self.assertEqual(
            rows["Research display refresh"].status,
            HealthStatus.NOT_INSTRUMENTED,
        )
        self.assertNotIn("Live dashboard", rows)

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

    def test_alignment_evidence_only_is_degraded(self):
        self._install_all_ok()
        path = self.root / f".tmp/alignment_check/{AS_OF}.log"
        path.write_text(
            "2026-08-21T15:30:00-0400 status=AHEAD_EVIDENCE_ONLY "
            "branch=main detail=capture remains allowed\n"
        )

        row = self._by_job(collect_health(self.root, AS_OF))["Alignment check"]

        self.assertEqual(row.status, HealthStatus.DEGRADED)

    def test_intraday_uses_latest_producer_timestamp_and_aggregates_coverage(self):
        self._install_all_ok()
        self._copy(
            "intraday_open.json",
            f"reports/intraday_capture/{AS_OF}/open.json",
        )
        preclose_path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(preclose_path.read_text())
        payload["names"]["VST"] = {
            "symbol": "VST",
            "status": "unavailable",
            "note": "provider unreachable",
        }
        preclose_path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture"]

        self.assertEqual(row.status, HealthStatus.DEGRADED)
        self.assertEqual(row.path, f"reports/intraday_capture/{AS_OF}/preclose.json")
        self.assertIn("1/2", row.reason)

    def test_zero_intraday_coverage_is_failed(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        for row in payload["names"].values():
            row["status"] = "unavailable"
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("0/2", row.reason)

    def test_intraday_missing_expected_symbol_row_is_failed(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        del payload["names"]["VST"]
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("missing symbol rows: VST", row.reason)

    def test_intraday_row_symbol_must_match_its_name_key(self):
        self._install_all_ok()
        path = self.root / f"reports/intraday_capture/{AS_OF}/preclose.json"
        payload = json.loads(path.read_text())
        payload["names"]["VST"]["symbol"] = "CEG"
        path.write_text(json.dumps(payload))

        row = self._by_job(collect_health(self.root, AS_OF))["Intraday capture"]

        self.assertEqual(row.status, HealthStatus.FAILED)
        self.assertIn("symbol identity mismatch", row.reason)

    def test_research_refresh_uses_existence_only(self):
        self._install_all_ok()
        path = self.root / f".tmp/research_refresh/receipt_v2_{AS_OF}_premarket.json"
        path.write_text("this is deliberately not JSON\n")

        row = self._by_job(collect_health(self.root, AS_OF))["Research refresh (premarket)"]

        self.assertEqual(row.status, HealthStatus.OK)
        self.assertIn("exists", row.reason)

    def test_real_world_august_21_absence_is_reported_as_problems(self):
        self._copy("alignment.log", f".tmp/alignment_check/{AS_OF}.log")

        rows = collect_health(self.root, AS_OF)
        digest = render_digest(AS_OF, rows)

        by_job = self._by_job(rows)
        for job in (
            "Ritual overall",
            "Ritual hypotheses",
            "Intraday capture",
            "Schwab preclose",
            "Research refresh (premarket)",
        ):
            self.assertEqual(by_job[job].status, HealthStatus.MISSING, job)
        self.assertEqual(by_job["Alignment check"].status, HealthStatus.OK)
        self.assertTrue(digest.startswith("5 PROBLEMS\n"), digest)

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

    def test_cli_rejects_explicit_root_that_contains_output_path(self):
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
                "--as-of",
                AS_OF,
            ],
            cwd=output_dir,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("inside explicit --root", completed.stderr)
        self.assertFalse((output_dir / ".tmp" / "job_health").exists())

    def test_cli_rejects_explicit_root_equal_to_invoking_cwd(self):
        self._install_all_ok()
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.job_health_digest",
                "--root",
                str(self.root),
                "--as-of",
                AS_OF,
            ],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("inside explicit --root", completed.stderr)
        self.assertFalse((self.root / ".tmp" / "job_health").exists())

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

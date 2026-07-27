"""Offline tests for the ritual-level terminal status projection."""

import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from options_researcher import ritual_status

AS_OF = "2026-07-24"
RUN_DATE = "2026-07-27"
CODE_SHA = "a" * 40


class RitualStatusTests(unittest.TestCase):
    def test_build_status_binds_exact_capture_identity_and_et_timestamp(self):
        payload = ritual_status.build_status(
            as_of=AS_OF,
            run_date=RUN_DATE,
            status="OK",
            code_sha=CODE_SHA,
            capture_receipt_path=(
                "reports/ritual/capture_receipt_2026-07-24.json"
            ),
            capture_receipt_sha256="b" * 64,
            log_path=".tmp/daily_ritual/run.log",
            now_utc=datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(
            payload["schema_version"], "daily_ritual/run_status/v1"
        )
        self.assertEqual(payload["status"], "OK")
        self.assertEqual(payload["run_at_utc"], "2026-07-27T12:00:00Z")
        self.assertEqual(payload["run_at_et"], "2026-07-27T08:00:00-04:00")

    def test_running_marker_invalidates_prior_ok_before_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ritual_dir = root / "reports" / "ritual"
            ritual_dir.mkdir(parents=True)
            output = ritual_dir / f"run_status_{AS_OF}.json"
            output.write_text('{"status":"OK"}\n')

            with patch.object(
                ritual_status, "_current_code_sha", return_value=CODE_SHA
            ):
                ritual_status.publish_status(
                    root=root,
                    as_of=AS_OF,
                    run_date=RUN_DATE,
                    status="RUNNING",
                    log_path=".tmp/daily_ritual/run.log",
                )

            payload = json.loads(output.read_text())
            self.assertEqual(payload["status"], "RUNNING")
            self.assertEqual(payload["capture_receipt_sha256"], "0" * 64)
            self.assertTrue(
                (ritual_dir / f".{output.name}.previous").is_file()
            )

    def test_terminal_status_hashes_capture_and_later_broken_replaces_ok(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ritual_dir = root / "reports" / "ritual"
            ritual_dir.mkdir(parents=True)
            capture = ritual_dir / f"capture_receipt_{AS_OF}.json"
            capture.write_text('{"status":"NO_SIGNAL"}\n')
            expected_sha = hashlib.sha256(capture.read_bytes()).hexdigest()

            with patch.object(
                ritual_status, "_current_code_sha", return_value=CODE_SHA
            ):
                output = ritual_status.publish_status(
                    root=root,
                    as_of=AS_OF,
                    run_date=RUN_DATE,
                    status="OK",
                    log_path=".tmp/daily_ritual/first.log",
                )
                ritual_status.publish_status(
                    root=root,
                    as_of=AS_OF,
                    run_date=RUN_DATE,
                    status="BROKEN",
                    log_path=".tmp/daily_ritual/second.log",
                )

            payload = json.loads(output.read_text())
            self.assertEqual(payload["status"], "BROKEN")
            self.assertEqual(payload["capture_receipt_sha256"], expected_sha)


if __name__ == "__main__":
    unittest.main()

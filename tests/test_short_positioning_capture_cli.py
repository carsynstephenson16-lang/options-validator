"""Capture-CLI tests: documented exit codes, dry-run safety, secret redaction.

The CLI is never invoked with --execute against a real provider. Every
execute path here injects a scripted mock transport.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from data.short_positioning.provider import ArtifactIntegrityError
from tools import short_positioning_capture as cli

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"
VALID_PAYLOAD = (FIXTURES / "finra_valid.json").read_bytes()
MALFORMED_PAYLOAD = (FIXTURES / "finra_malformed.json").read_bytes()


class _Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def __call__(self, url, *, headers, timeout):
        self.calls += 1
        outcome = self.responses.pop(0) if self.responses else (200, {}, b"[]")
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class CaptureCliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def argv(self, *extra, symbols="ZQXA,TRNVQ,HLGRD"):
        return [
            "--provider",
            "finra",
            "--dataset",
            "consolidated-short-interest",
            "--publication-date",
            "2026-07-17",
            "--symbols",
            symbols,
            "--output-root",
            str(self.root),
            "--data-version",
            "1.0",
            "--request-id",
            "test-0001",
            *extra,
        ]

    def run_cli(self, argv, *, transport=None, sleep=lambda _seconds: None):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv, transport=transport, sleep=sleep)
        return code, out.getvalue() + err.getvalue()


class DryRunTests(CaptureCliTestCase):
    def test_dry_run_is_the_default_and_touches_no_network_and_no_disk(self):
        transport = _Transport([])
        code, output = self.run_cli(self.argv(), transport=transport)

        self.assertEqual(code, 0)
        self.assertEqual(transport.calls, 0)
        self.assertIn("DRY RUN", output.upper())
        self.assertEqual(list(self.root.rglob("*.json")), [])

    def test_dry_run_prints_credential_names_and_never_credential_values(self):
        # Invented, obviously-not-real value. Its only job is to prove the
        # CLI prints credential NAMES and never credential VALUES.
        fake_value = "FAKE-NOT-A-REAL-CREDENTIAL-1"
        env = {"FINRA_API_CLIENT_SECRET": fake_value, "FINRA_API_TOKEN": fake_value}
        with mock.patch.dict(os.environ, env, clear=False):
            code, output = self.run_cli(self.argv(), transport=_Transport([]))

        self.assertEqual(code, 0)
        self.assertNotIn(fake_value, output)
        self.assertIn("FINRA_API_CLIENT_SECRET", output)

    def test_module_entry_point_runs_a_dry_run_offline(self):
        repo_root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "tools/short_positioning_capture.py", *self.argv()],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DRY RUN", (result.stdout + result.stderr).upper())
        self.assertEqual(list(self.root.rglob("*.json")), [])


class ExitCodeTests(CaptureCliTestCase):
    def test_zero_on_successful_execute_with_a_mocked_transport(self):
        transport = _Transport([(200, {}, VALID_PAYLOAD)])
        code, _ = self.run_cli(self.argv("--execute"), transport=transport)

        self.assertEqual(code, 0)
        self.assertEqual(transport.calls, 1)
        self.assertEqual(len(list(self.root.rglob("records-*.json"))), 1)
        partition = json.loads(next(self.root.rglob("records-*.json")).read_text())
        self.assertEqual(len(partition["records"]), 3)

    def test_two_on_cli_input_error(self):
        code, _ = self.run_cli(
            [
                "--provider",
                "finra",
                "--dataset",
                "consolidated-short-interest",
                "--publication-date",
                "not-a-date",
                "--symbols",
                "ZQXA",
                "--output-root",
                str(self.root),
            ]
        )
        self.assertEqual(code, 2)

    def test_two_when_no_symbols_are_requested(self):
        code, _ = self.run_cli(self.argv(symbols=""))
        self.assertEqual(code, 2)

    def test_three_on_credential_failure(self):
        transport = _Transport([(401, {}, b"")])
        code, _ = self.run_cli(self.argv("--execute"), transport=transport)
        self.assertEqual(code, 3)

    def test_four_when_the_provider_stays_unavailable(self):
        transport = _Transport([(503, {}, b"")] * 12)
        code, _ = self.run_cli(self.argv("--execute"), transport=transport)
        self.assertEqual(code, 4)

    def test_five_on_source_schema_drift(self):
        transport = _Transport([(200, {}, MALFORMED_PAYLOAD)])
        code, _ = self.run_cli(self.argv("--execute"), transport=transport)
        self.assertEqual(code, 5)
        self.assertEqual(list(self.root.rglob("records-*.json")), [])

    def test_six_on_hash_or_atomic_write_failure(self):
        transport = _Transport([(200, {}, VALID_PAYLOAD)])
        with mock.patch.object(
            cli, "write_raw_artifact", side_effect=ArtifactIntegrityError("synthetic hash failure")
        ):
            code, _ = self.run_cli(self.argv("--execute"), transport=transport)
        self.assertEqual(code, 6)

    def test_seven_when_a_requested_symbol_is_missing_from_the_response(self):
        transport = _Transport([(200, {}, VALID_PAYLOAD)])
        code, _ = self.run_cli(
            self.argv("--execute", symbols="ZQXA,TRNVQ,HLGRD,ABSENTX"), transport=transport
        )
        self.assertEqual(code, 7)
        self.assertEqual(list(self.root.rglob("records-*.json")), [])

    def test_eight_when_the_provider_is_license_blocked(self):
        code, output = self.run_cli(
            [
                "--provider",
                "sp_global",
                "--dataset",
                "securities-finance",
                "--publication-date",
                "2026-07-17",
                "--symbols",
                "ZQXA",
                "--output-root",
                str(self.root),
                "--execute",
            ]
        )
        self.assertEqual(code, 8)
        self.assertIn("LICENSE", output.upper())

    def test_every_documented_exit_code_is_declared(self):
        self.assertEqual(
            cli.EXIT_CODE_MEANINGS,
            {
                0: "success or dry-run",
                2: "CLI input or local validation failure",
                3: "credential or authentication failure",
                4: "provider unavailable or retry exhaustion",
                5: "source schema or field-map mismatch",
                6: "atomic-write or hash failure",
                7: "partial capture rolled back",
                8: "license or entitlement blocked",
            },
        )


if __name__ == "__main__":
    unittest.main()

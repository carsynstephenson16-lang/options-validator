"""Offline tests for the durable Schwab preclose chain capture lane."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd
from authlib.integrations.base_client.errors import OAuthError

from options_researcher import schwab_chain_capture as capture
from research.hashing import sha256_file
from tools.schwab_chain_manifest import verify_session

NY = ZoneInfo("America/New_York")
PRECLOSE = pd.Timestamp("2026-08-10T15:45:00", tz=NY).to_pydatetime()


def full_frame(*, expirations=("2026-08-21", "2026-09-18"), bid=1.0):
    rows = []
    for expiration in expirations:
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "contract_symbol": f"AAA-{expiration}-{right}-100",
                    "bid": bid,
                    "ask": 1.2,
                    "open_interest": 100,
                    "implied_vol": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                    "multiplier": 100.0,
                    "non_standard": False,
                    "mini": False,
                    "timestamp": pd.Timestamp("2026-08-10T19:44:30Z"),
                    "trade_timestamp": pd.Timestamp("2026-08-10T19:44:20Z"),
                }
            )
    return pd.DataFrame(rows)


class FakeClient:
    provider_name = "schwab"
    provider_version = "test"

    def __init__(self, *, fail_symbol=None, expirations=("2026-08-21", "2026-09-18"), bid=1.0):
        self.fail_symbol = fail_symbol
        self.expirations = expirations
        self.bid = bid
        self.calls = []

    def option_full_chain(self, symbol):
        self.calls.append(symbol)
        if symbol == self.fail_symbol:
            raise RuntimeError("synthetic provider failure")
        return full_frame(expirations=self.expirations, bid=self.bid)


class SchwabChainCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chain_dir = self.root / "chains"
        self.reports_dir = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def _capture(self, client, *, universe=("AAA", "BBB"), now_ny=PRECLOSE):
        with mock.patch.object(
            capture, "FACTS_DIR", self.root / "ledger", create=True
        ):
            return capture.capture(
                client=client,
                now_ny=now_ny,
                universe=list(universe),
                chain_dir=self.chain_dir,
                reports_dir=self.reports_dir,
                force=False,
            )

    def test_force_refuses_before_fetching_or_writing_anything(self):
        client = FakeClient()

        with mock.patch.object(
            capture, "FACTS_DIR", self.root / "ledger", create=True
        ):
            exit_code, receipt = capture.capture(
                client=client,
                now_ny=PRECLOSE,
                universe=["AAA", "BBB"],
                chain_dir=self.chain_dir,
                reports_dir=self.reports_dir,
                force=True,
            )

        self.assertEqual(exit_code, 1)
        self.assertIsNone(receipt)
        self.assertEqual(client.calls, [])
        self.assertFalse(self.chain_dir.exists())
        self.assertFalse(self.reports_dir.exists())
        self.assertFalse((self.root / "ledger").exists())

    def test_complete_capture_writes_h7_columns_manifest_and_receipt(self):
        exit_code, receipt = self._capture(FakeClient())

        self.assertEqual(exit_code, 0)
        self.assertEqual(receipt["overall_status"], "ok")
        self.assertEqual(receipt["session"], "2026-08-10")
        self.assertEqual(
            receipt["session_chain_convention"], "preclose_snapshot_v1"
        )
        self.assertEqual(receipt["universe"], ["AAA", "BBB"])
        self.assertTrue((self.reports_dir / "2026-08-10" / "manifest.json").is_file())
        self.assertTrue((self.reports_dir / "2026-08-10" / "preclose.json").is_file())
        expected_columns = [
            "expiration",
            "strike",
            "right",
            "contract_symbol",
            "bid",
            "ask",
            "open_interest",
            "iv",
            "delta",
            "gamma",
            "theta",
            "vega",
            "multiplier",
            "non_standard",
            "mini",
            "timestamp",
            "trade_timestamp",
        ]
        for symbol in ("AAA", "BBB"):
            frame = pd.read_parquet(
                self.chain_dir / f"{symbol}_2026-08-10.parquet"
            )
            self.assertEqual(list(frame.columns), expected_columns)
            self.assertEqual(frame["expiration"].nunique(), 2)
            self.assertEqual(set(frame["right"]), {"C", "P"})
            self.assertTrue(frame["contract_symbol"].str.startswith("AAA-").all())
            self.assertEqual(set(frame["multiplier"]), {100.0})
            self.assertEqual(set(frame["non_standard"]), {False})
            self.assertEqual(set(frame["mini"]), {False})
            self.assertTrue(frame["timestamp"].notna().all())
            self.assertTrue(frame["trade_timestamp"].notna().all())

    def test_success_appends_manifest_and_receipt_hashes_to_facts_log(self):
        exit_code, receipt = self._capture(FakeClient(), universe=("AAA",))

        self.assertEqual(exit_code, 0)
        receipt_path = self.reports_dir / "2026-08-10" / "preclose.json"
        lines = (self.root / "ledger" / "facts.log").read_text().splitlines()
        self.assertEqual(len(lines), 1)
        _, payload = lines[0].split("\t", 1)
        self.assertEqual(
            payload,
            "SCHWAB_CHAIN_CAPTURE "
            f"session=2026-08-10 manifest_hash={receipt['manifest_hash']} "
            f"receipt_hash={sha256_file(receipt_path)}",
        )

    def test_identical_successful_replay_keeps_one_fact_for_session(self):
        first_code, _ = self._capture(FakeClient(), universe=("AAA",))
        second_code, _ = self._capture(FakeClient(), universe=("AAA",))

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        lines = (self.root / "ledger" / "facts.log").read_text().splitlines()
        self.assertEqual(len(lines), 1)

    def test_partial_capture_writes_failed_receipt_and_no_manifest(self):
        exit_code, receipt = self._capture(FakeClient(fail_symbol="BBB"))

        self.assertEqual(exit_code, 1)
        self.assertEqual(receipt["overall_status"], "failed")
        self.assertEqual(receipt["names"]["AAA"]["status"], "ok")
        self.assertEqual(receipt["names"]["BBB"]["status"], "failed")
        self.assertIsNone(receipt["manifest_hash"])
        self.assertFalse((self.reports_dir / "2026-08-10" / "manifest.json").exists())
        self.assertFalse((self.root / "ledger" / "facts.log").exists())

    def test_single_expiration_is_marked_failed(self):
        exit_code, receipt = self._capture(
            FakeClient(expirations=("2026-08-21",)), universe=("AAA",)
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(receipt["names"]["AAA"]["status"], "failed")
        self.assertIn("at least two expirations", receipt["names"]["AAA"]["note"])

    def test_required_greek_column_missing_entirely_is_marked_failed(self):
        client = FakeClient()
        client.option_full_chain = mock.Mock(return_value=full_frame().drop(columns="gamma"))

        exit_code, receipt = self._capture(client, universe=("AAA",))

        self.assertEqual(exit_code, 1)
        self.assertEqual(receipt["names"]["AAA"]["status"], "failed")
        self.assertIn("missing required columns", receipt["names"]["AAA"]["note"])

    def test_invalid_session_refuses_before_default_client_construction(self):
        sunday = pd.Timestamp("2026-08-09T15:45:00", tz=NY).to_pydatetime()
        with mock.patch.object(
            capture, "_default_client", side_effect=AssertionError("client constructed")
        ):
            exit_code, receipt = capture.capture(
                client=None,
                now_ny=sunday,
                chain_dir=self.chain_dir,
                reports_dir=self.reports_dir,
            )

        self.assertEqual(exit_code, 1)
        self.assertIsNone(receipt)
        self.assertFalse(self.reports_dir.exists())

    def test_changed_retry_refuses_existing_file_and_receipt(self):
        first_code, _ = self._capture(FakeClient(bid=1.0), universe=("AAA",))
        second_code, second_receipt = self._capture(
            FakeClient(bid=1.1), universe=("AAA",)
        )

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 2)
        self.assertEqual(second_receipt["overall_status"], "failed")
        stored = json.loads(
            (self.reports_dir / "2026-08-10" / "preclose.json").read_text()
        )
        self.assertEqual(stored["overall_status"], "ok")

    def test_expired_refresh_token_propagates_to_cli_boundary(self):
        expired = OAuthError(
            "invalid_grant",
            "Refresh token is invalid, expired or revoked",
        )
        client = FakeClient()
        client.option_full_chain = mock.Mock(side_effect=expired)

        with self.assertRaises(OAuthError):
            self._capture(client, universe=("AAA",))

        self.assertFalse(self.reports_dir.exists())

    def test_main_classifies_expired_schwab_refresh_token(self):
        expired = OAuthError(
            "invalid_grant",
            "Refresh token is invalid, expired or revoked",
        )
        stdout = io.StringIO()

        with (
            mock.patch.object(capture, "capture", side_effect=expired),
            mock.patch("sys.stdout", stdout),
        ):
            rc = capture.main(["--force"])

        self.assertEqual(rc, 1)
        self.assertEqual(
            stdout.getvalue(),
            "schwab_chain_capture auth EXPIRED: Refresh token is invalid, "
            "expired or revoked; run uv run python tools/setup_schwab.py\n",
        )


class InvocationSourceTests(unittest.TestCase):
    """rev-2.1 item 3a — unattended-vs-manual capture provenance.

    Spec: docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md
    §7 condition 3, option 3a; owner-ratified in
    reports/2026-08-14-owner-answers-decision-menu.md item 3.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chain_dir = self.root / "chains"
        self.reports_dir = self.root / "reports"

    def tearDown(self):
        self.tmp.cleanup()

    def _capture(self, client, *, universe=("AAA",)):
        with mock.patch.object(
            capture, "FACTS_DIR", self.root / "ledger", create=True
        ):
            return capture.capture(
                client=client,
                now_ny=PRECLOSE,
                universe=list(universe),
                chain_dir=self.chain_dir,
                reports_dir=self.reports_dir,
                force=False,
            )

    def _capture_with_env(self, value, *, universe=("AAA",)):
        # The writer reads the process-start snapshot, not live os.environ
        # (review 2026-08-15 F2: a runtime dotenv load must not set the
        # marker), so tests simulate the start environment via the snapshot.
        with mock.patch.object(capture, "_INVOCATION_MARKER_AT_IMPORT", value):
            return self._capture(FakeClient(), universe=universe)

    def test_runtime_environ_mutation_cannot_forge_unattended_provenance(self):
        # data.schwab_adapter and LumiBot both load .env into os.environ at
        # runtime on the capture path. A marker arriving that way must degrade
        # to "manual" -- only the process-start environment counts.
        with mock.patch.object(capture, "_INVOCATION_MARKER_AT_IMPORT", None):
            with mock.patch.dict(
                os.environ, {capture.INVOCATION_SOURCE_ENV: "launchd"}
            ):
                self.assertEqual(capture.resolve_invocation_source(), "manual")

    def test_dotenv_file_cannot_forge_unattended_provenance(self):
        # End-to-end F2 pin: a fresh interpreter whose REAL environment lacks
        # the marker, in a cwd whose .env carries it. The dotenv load lands in
        # os.environ (asserted, so this test can never pass vacuously) yet the
        # process-start snapshot in options_researcher/__init__.py wins.
        repo_root = Path(__file__).resolve().parents[1]
        code = (
            "import os; import options_researcher.schwab_chain_capture as m; "
            "from dotenv import load_dotenv; load_dotenv('.env'); "
            "assert os.environ.get(m.INVOCATION_SOURCE_ENV) == 'launchd', "
            "'dotenv load did not take'; "
            "print(m.resolve_invocation_source())"
        )
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".env").write_text(
                f"{capture.INVOCATION_SOURCE_ENV}=launchd\n"
            )
            env = dict(os.environ)
            env.pop(capture.INVOCATION_SOURCE_ENV, None)
            env["PYTHONPATH"] = str(repo_root)
            result = subprocess.run(
                [sys.executable, "-c", code],
                env=env,
                capture_output=True,
                text=True,
                cwd=tmp,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "manual")

    def test_marker_in_process_start_environment_is_honored(self):
        # End-to-end positive path: launchd sets the marker before python
        # starts, so a fresh interpreter must resolve "launchd".
        env = dict(os.environ)
        env[capture.INVOCATION_SOURCE_ENV] = "launchd"
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import options_researcher.schwab_chain_capture as m;"
                "print(m.resolve_invocation_source())",
            ],
            env=env,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "launchd")

    def test_receipt_records_launchd_when_the_plist_marker_is_set(self):
        exit_code, receipt = self._capture_with_env("launchd")

        self.assertEqual(exit_code, 0)
        self.assertEqual(receipt["invocation_source"], "launchd")
        stored = json.loads(
            (self.reports_dir / "2026-08-10" / "preclose.json").read_text()
        )
        self.assertEqual(stored["invocation_source"], "launchd")

    def test_receipt_records_manual_when_the_marker_is_absent(self):
        exit_code, receipt = self._capture_with_env(None)

        self.assertEqual(exit_code, 0)
        self.assertEqual(receipt["invocation_source"], "manual")

    def test_unrecognized_marker_degrades_to_manual_never_to_launchd(self):
        # Fail-closed direction: a typo, an empty value, or any other string
        # must never let a hand-run capture claim unattended provenance. It
        # must also never raise on the irreplaceable-capture critical path.
        for value in ("", " ", "cron", "LAUNCHD", "manual", "true"):
            with self.subTest(value=value):
                self.setUp()
                try:
                    exit_code, receipt = self._capture_with_env(value)
                    self.assertEqual(exit_code, 0)
                    self.assertEqual(receipt["invocation_source"], "manual")
                finally:
                    self.tearDown()

    def test_new_receipt_carrying_the_field_still_verifies_offline(self):
        # verify_session is S1 condition 1's check; the new field must not
        # break it.
        exit_code, _ = self._capture_with_env("launchd")

        self.assertEqual(exit_code, 0)
        result = verify_session(
            "2026-08-10",
            ["AAA"],
            self.chain_dir,
            self.reports_dir / "2026-08-10" / "manifest.json",
            self.reports_dir / "2026-08-10" / "preclose.json",
        )
        self.assertEqual(result["session"], "2026-08-10")

    def test_pre_3a_receipt_without_the_field_still_verifies_offline(self):
        # Backward compatibility with the sealed 2026-08-14 canary receipt,
        # which predates the field: a missing key must never crash a consumer.
        exit_code, _ = self._capture_with_env("launchd")
        self.assertEqual(exit_code, 0)
        receipt_path = self.reports_dir / "2026-08-10" / "preclose.json"
        stored = json.loads(receipt_path.read_text())
        del stored["invocation_source"]
        receipt_path.write_text(
            json.dumps(stored, indent=2, sort_keys=True) + "\n"
        )

        result = verify_session(
            "2026-08-10",
            ["AAA"],
            self.chain_dir,
            self.reports_dir / "2026-08-10" / "manifest.json",
            receipt_path,
        )
        self.assertEqual(result["session"], "2026-08-10")

    def test_receipt_is_unattended_only_for_launchd(self):
        self.assertTrue(capture.receipt_is_unattended({"invocation_source": "launchd"}))
        self.assertFalse(capture.receipt_is_unattended({"invocation_source": "manual"}))
        self.assertFalse(capture.receipt_is_unattended({"invocation_source": "LAUNCHD"}))
        self.assertFalse(capture.receipt_is_unattended({"invocation_source": None}))

    def test_receipt_is_unattended_treats_a_missing_field_as_not_unattended(self):
        # S1 counting rule: a pre-3a receipt is "unknown provenance", which
        # must never be counted toward the three unattended sessions.
        self.assertFalse(capture.receipt_is_unattended({}))

    def test_sealed_2026_08_14_canary_receipt_is_untouched_and_not_unattended(self):
        # The 08-14 canary receipt is immutable evidence written before 3a.
        # This change must not retro-fit it, and the S1 bar must not credit it.
        canary = json.loads(
            (
                Path(__file__).resolve().parents[1]
                / "reports"
                / "schwab_chains"
                / "2026-08-14"
                / "preclose.json"
            ).read_text()
        )
        self.assertEqual(canary["receipt_kind"], "schwab_chain_capture/v1")
        self.assertNotIn("invocation_source", canary)
        self.assertFalse(capture.receipt_is_unattended(canary))


if __name__ == "__main__":
    unittest.main()

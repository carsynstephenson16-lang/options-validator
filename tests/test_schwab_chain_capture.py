"""Offline tests for the durable Schwab preclose chain capture lane."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd
from authlib.integrations.base_client.errors import OAuthError

from options_researcher import schwab_chain_capture as capture
from research.hashing import sha256_file

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


if __name__ == "__main__":
    unittest.main()

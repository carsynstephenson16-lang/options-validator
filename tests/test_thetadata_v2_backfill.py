"""Offline safety and resumability tests for the OD-1 v2 backfill."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from tools import thetadata_v2_backfill as backfill


def _v2_chain() -> pd.DataFrame:
    timestamp = pd.Timestamp("2026-07-27 17:15:00", tz="America/New_York")
    underlying_timestamp = pd.Timestamp("2026-07-27 16:00:00", tz="America/New_York")
    return pd.DataFrame(
        [
            {
                "expiration": "2026-08-21",
                "strike": 100.0,
                "right": "C",
                "bid": 1.0,
                "ask": 1.1,
                "open_interest": 500,
                "iv": 0.3,
                "delta": 0.4,
                "gamma": 0.02,
                "theta": -0.04,
                "vega": 0.12,
                "timestamp": timestamp,
                "bid_size": 10,
                "bid_condition": 50,
                "ask_size": 12,
                "ask_condition": 50,
                "iv_error": 0.001,
                "underlying_timestamp": underlying_timestamp,
                "underlying_price": 101.0,
                "thetadata_client_version": "1.0.9",
            }
        ]
    )


class ScopeTests(unittest.TestCase):
    def test_scope_is_exact_and_call_bound_is_mechanical(self):
        plan = backfill.scope_plan()
        self.assertEqual(plan["symbols"], list(backfill.SYMBOLS))
        self.assertEqual(plan["session_count"], 252)
        self.assertEqual(plan["partition_count"], 2016)
        self.assertEqual(plan["base_provider_calls"], 4032)
        self.assertEqual(plan["maximum_provider_calls_including_retries"], 4100)
        self.assertFalse(plan["provider_call"])

    def test_output_refuses_v1_or_descendant(self):
        with tempfile.TemporaryDirectory() as temp:
            v1 = Path(temp) / "chains"
            with self.assertRaises(backfill.BackfillRefused):
                backfill._safe_output_dir(v1, v1_dir=v1)
            with self.assertRaises(backfill.BackfillRefused):
                backfill._safe_output_dir(v1 / "v2", v1_dir=v1)

    def test_dry_run_never_loads_credentials_or_provider(self):
        with (
            mock.patch("data.thetadata_adapter._client") as client,
            mock.patch("dotenv.load_dotenv") as load_dotenv,
        ):
            self.assertEqual(backfill.main([]), 0)
        client.assert_not_called()
        load_dotenv.assert_not_called()

    def test_call_budget_refuses_retry_over_ceiling(self):
        budget = backfill.CallBudget(2)
        budget.reserve_partition_attempt()
        with self.assertRaisesRegex(backfill.BackfillRefused, "ceiling"):
            budget.reserve_partition_attempt()

    def test_owner_facts_require_exact_decision_and_pull(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            facts = root / "facts.log"
            output = root / "v2"
            decision = "decision"
            approval = backfill.pull_approval_payload(output)
            facts.write_text(f"t\t{decision}\nt\t{approval}\n")
            decision_hash = backfill.hashlib.sha256(decision.encode()).hexdigest()
            with mock.patch.object(backfill, "OWNER_DECISION_PAYLOAD_SHA256", decision_hash):
                verified = backfill._verify_owner_facts(facts, output)
                self.assertEqual(verified["owner_decision_payload_sha256"], decision_hash)
                facts.write_text(f"t\t{decision}\n")
                with self.assertRaisesRegex(backfill.BackfillRefused, "pull approval"):
                    backfill._verify_owner_facts(facts, output)


class CaptureTests(unittest.TestCase):
    def test_capture_writes_side_by_side_and_resume_makes_no_call(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "v2"
            v1 = root / "chains"
            v1.mkdir()
            old = v1 / "NVDA_2026-07-27.parquet"
            old.write_bytes(b"immutable-v1")
            with mock.patch.object(
                backfill.thetadata_adapter,
                "_fetch_merged_chain",
                return_value=(_v2_chain(), 0),
            ) as fetch:
                first = backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
                second = backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            self.assertEqual(first["status"], "FETCHED")
            self.assertEqual(second["status"], "VERIFIED")
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(old.read_bytes(), b"immutable-v1")
            attestation = json.loads(
                backfill._attestation_path(output, "NVDA", "2026-07-27").read_text()
            )
            self.assertEqual(attestation["schema_version"], 2)
            self.assertEqual(attestation["status"], "COMPLETE")

    def test_existing_partition_without_attestation_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            _v2_chain().to_parquet(backfill._partition_path(output, "NVDA", "2026-07-27"))
            with self.assertRaisesRegex(backfill.BackfillRefused, "orphaned"):
                backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)

    def test_partial_v2_response_creates_no_partition(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            partial = _v2_chain().drop(columns=["underlying_timestamp"])
            with mock.patch.object(
                backfill.thetadata_adapter,
                "_fetch_merged_chain",
                return_value=(partial, 0),
            ):
                with self.assertRaises(ValueError):
                    backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            self.assertFalse(backfill._partition_path(output, "NVDA", "2026-07-27").exists())


if __name__ == "__main__":
    unittest.main()

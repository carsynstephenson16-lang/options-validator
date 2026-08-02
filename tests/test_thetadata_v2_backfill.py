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
    # EOD Greeks ``timestamp`` is the last option-trade time, not the
    # report-creation time.  A normal intraday value must remain auditable.
    timestamp = pd.Timestamp("2026-07-27 15:59:00", tz="America/New_York")
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


def _raw_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    chain = _v2_chain()
    greeks = chain.drop(columns=["open_interest", "thetadata_client_version"])
    open_interest = chain[["expiration", "strike", "right", "open_interest"]]
    return greeks, open_interest


class ScopeTests(unittest.TestCase):
    def test_scope_is_exact_and_call_bound_is_mechanical(self):
        plan = backfill.scope_plan()
        self.assertEqual(plan["symbols"], list(backfill.SYMBOLS))
        self.assertEqual(plan["session_count"], 256)
        self.assertEqual(plan["partition_count"], 4608)
        self.assertEqual(plan["base_provider_calls"], 9216)
        self.assertEqual(plan["maximum_provider_calls_including_retries"], 9500)
        self.assertEqual(plan["predecessor_reserved_provider_calls"], 434)
        self.assertEqual(plan["minimum_total_reservations_to_complete"], 9290)
        self.assertFalse(plan["provider_call"])
        intended = Path("/Users/carsynstephenson/options-validator/.cache/chains_v2/od1-2026-08-01")
        approval_hash = backfill.hashlib.sha256(
            backfill.pull_approval_payload(intended).encode()
        ).hexdigest()
        self.assertEqual(approval_hash, backfill.PULL_APPROVAL_PAYLOAD_SHA256)

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
        with tempfile.TemporaryDirectory() as temp:
            journal = Path(temp) / "reservations.jsonl"
            budget = backfill.CallBudget(2, journal, "run-1")
            budget.reserve_partition_attempt("NVDA", "2026-07-27")
            with self.assertRaisesRegex(backfill.BackfillRefused, "ceiling"):
                budget.reserve_partition_attempt("NVDA", "2026-07-27")
            restarted = backfill.CallBudget(2, journal, "run-2")
            with self.assertRaisesRegex(backfill.BackfillRefused, "ceiling"):
                restarted.reserve_partition_attempt("NVDA", "2026-07-27")

    def test_predecessor_reservation_prefix_is_exact_and_cannot_be_reclaimed(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = Path(temp) / "reservations.jsonl"
            entries = []
            for index in range(2):
                entries.append(
                    json.dumps(
                        {
                            "schema": "thetadata-call-reservation/v1",
                            "reservation_id": f"old-{index}",
                            "run_id": "old-run",
                            "scope_id": backfill.SCOPE_ID,
                            "symbol": "NVDA",
                            "session": "2026-07-27",
                            "reserved_calls": 2,
                            "reserved_at_utc": "2026-08-01T00:00:00+00:00",
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
            prefix = "".join(entries).encode()
            journal.write_bytes(prefix)
            with (
                mock.patch.object(backfill, "PREDECESSOR_RESERVATION_ENTRIES", 2),
                mock.patch.object(backfill, "PREDECESSOR_RESERVED_PROVIDER_CALLS", 4),
                mock.patch.object(
                    backfill,
                    "PREDECESSOR_RESERVATION_PREFIX_SHA256",
                    backfill.hashlib.sha256(prefix).hexdigest(),
                ),
            ):
                backfill._verify_predecessor_reservations(journal)
                journal.write_text(entries[0])
                with self.assertRaisesRegex(backfill.BackfillRefused, "predecessor"):
                    backfill._verify_predecessor_reservations(journal)

    def test_exact_predecessor_scope_creates_append_only_amendment(self):
        with tempfile.TemporaryDirectory() as temp:
            meta = Path(temp)
            scope_path = meta / "scope.json"
            scope_path.write_text('{"old": true}\n')
            old_bytes = scope_path.read_bytes()
            new_record = {"expanded": True}
            with mock.patch.object(
                backfill,
                "PREDECESSOR_SCOPE_SHA256",
                backfill.hashlib.sha256(old_bytes).hexdigest(),
            ):
                backfill._bind_scope_record(meta, new_record)
                backfill._bind_scope_record(meta, new_record)
                self.assertEqual(scope_path.read_bytes(), old_bytes)
                amendment = json.loads((meta / "scope_amendment.json").read_text())
                self.assertEqual(amendment["expanded_scope_record"], new_record)
                scope_path.write_text('{"tampered": true}\n')
                with self.assertRaisesRegex(backfill.BackfillRefused, "scope"):
                    backfill._bind_scope_record(meta, new_record)

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

    def test_provider_policy_is_closed_after_completed_pull(self):
        with self.assertRaises(backfill.provider_policy.ProviderDisabledError):
            backfill.provider_policy.require_thetadata_acquisition("test")
        with (
            mock.patch("dotenv.load_dotenv") as load_dotenv,
            mock.patch.object(backfill, "execute") as execute,
            self.assertRaises(backfill.provider_policy.ProviderDisabledError),
        ):
            backfill.main(["--execute"])
        load_dotenv.assert_not_called()
        execute.assert_not_called()


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
                "_fetch_raw",
                return_value=_raw_frames(),
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
            self.assertEqual(
                set(attestation["artifacts"]),
                {"normalized_v2", "raw_greeks_eod", "raw_open_interest"},
            )
            self.assertTrue(
                backfill._raw_path(output, "greeks_eod", "NVDA", "2026-07-27").is_file()
            )

    def test_raw_provider_columns_are_preserved_but_not_promoted_to_canonical(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            greeks, oi = _raw_frames()
            greeks["future_provider_field"] = "keep-me"
            with mock.patch.object(
                backfill.thetadata_adapter, "_fetch_raw", return_value=(greeks, oi)
            ):
                backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            raw = pd.read_parquet(backfill._raw_path(output, "greeks_eod", "NVDA", "2026-07-27"))
            canonical = pd.read_parquet(backfill._partition_path(output, "NVDA", "2026-07-27"))
            self.assertIn("future_provider_field", raw.columns)
            self.assertNotIn("future_provider_field", canonical.columns)

    def test_pending_three_file_publish_recovers_without_provider_call(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            real_publish = backfill.publish_staged_file
            calls = 0

            def crash_once(staged, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated crash")
                real_publish(staged, destination)

            with (
                mock.patch.object(
                    backfill.thetadata_adapter, "_fetch_raw", return_value=_raw_frames()
                ),
                mock.patch.object(backfill, "publish_staged_file", side_effect=crash_once),
            ):
                with self.assertRaisesRegex(OSError, "simulated crash"):
                    backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            with mock.patch.object(backfill.thetadata_adapter, "_fetch_raw") as fetch:
                result = backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            fetch.assert_not_called()
            self.assertEqual(result["status"], "RECOVERED")

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
            raw_oi = _raw_frames()[1]
            with mock.patch.object(
                backfill.thetadata_adapter,
                "_fetch_raw",
                return_value=(partial.drop(columns=["open_interest"]), raw_oi),
            ):
                with self.assertRaisesRegex(backfill.BackfillRefused, "raw frames preserved"):
                    backfill._capture_one(output, "NVDA", "2026-07-27", code_sha="a" * 40)
            self.assertFalse(backfill._partition_path(output, "NVDA", "2026-07-27").exists())
            self.assertTrue(backfill._raw_path(output, "greeks_eod", "NVDA", "2026-07-27").exists())
            self.assertTrue(backfill._schema_block_path(output, "NVDA", "2026-07-27").exists())


if __name__ == "__main__":
    unittest.main()

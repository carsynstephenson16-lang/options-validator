"""Offline fail-closed tests for the Schwab exact-session H7 data gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher import h7_data_gate
from options_researcher import h7_schwab_data_gate as gate
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import sha256_file
from research.receipts import make_receipt, write_immutable_receipt
from tools import schwab_chain_manifest as manifest

SESSION = "2026-08-10"
REQUESTED = date(2026, 8, 11)
SYMBOLS = sorted(watch_universe())
TARGET = SYMBOLS[0]


def chain_frame(*, expirations=("2026-08-21", "2026-09-18")):
    rows = []
    for expiration in expirations:
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "bid": 1.0,
                    "ask": 1.2,
                    "open_interest": 100,
                    "iv": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                }
            )
    return pd.DataFrame(rows)


class H7SchwabDataGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chain_dir = self.root / "chains"
        self.close_dir = self.root / "closes"
        self.report_dir = self.root / "reports" / SESSION
        self.chain_dir.mkdir(parents=True)
        self.close_dir.mkdir(parents=True)
        self.report_dir.mkdir(parents=True)
        for symbol in SYMBOLS:
            chain_frame().to_parquet(self.chain_dir / f"{symbol}_{SESSION}.parquet")
            pd.DataFrame({"date": [SESSION], "close": [100.0]}).to_parquet(
                self.close_dir / f"{symbol}.parquet"
            )
        self._write_package()

    def tearDown(self):
        self.tmp.cleanup()

    @property
    def manifest_path(self):
        return self.report_dir / "manifest.json"

    @property
    def receipt_path(self):
        return self.report_dir / "preclose.json"

    def _write_package(self, *, receipt_session=SESSION):
        built = manifest.build_manifest(SESSION, SYMBOLS, self.chain_dir)
        manifest.write_manifest(built, self.manifest_path)
        names = {}
        for symbol in SYMBOLS:
            path = self.chain_dir / f"{symbol}_{SESSION}.parquet"
            frame = pd.read_parquet(path)
            names[symbol] = {
                "status": "ok",
                "row_count": len(frame),
                "expiration_count": int(frame["expiration"].nunique()),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        receipt = {
            "receipt_kind": "schwab_chain_capture/v1",
            "session": receipt_session,
            "session_chain_convention": "preclose_snapshot_v1",
            "captured_at_et": "2026-08-10T15:45:00-04:00",
            "scheduled_session_tag": "preclose",
            "force": False,
            "universe": SYMBOLS,
            "overall_status": "ok",
            "names": names,
            "manifest_hash": built["manifest_hash"],
        }
        self.receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    def _evaluate(self):
        return gate.evaluate(
            REQUESTED,
            close_dir=self.close_dir,
            chain_dir=self.chain_dir,
            manifest_path=self.manifest_path,
            receipt_path=self.receipt_path,
            symbols=SYMBOLS,
        )

    def _source_health(self):
        return make_receipt(
            "source_health",
            {
                "evaluation_session": SESSION,
                "scope": scope_identity(),
                "symbols": {symbol: {"healthy": True, "gate": "CLEAR"} for symbol in SYMBOLS},
            },
        )

    def _assert_package_no_go(self, result, *, error_contains):
        self.assertEqual(result["whole_universe_verdict"], "NO_GO")
        self.assertEqual(result["go_count"], 0)
        self.assertEqual(result["no_go_count"], len(SYMBOLS))
        for symbol in SYMBOLS:
            record = result["symbols"][symbol]
            self.assertEqual(record["verdict"], "NO_GO")
            self.assertEqual(record["reason_codes"], [gate.SCHWAB_PACKAGE_INVALID])
            self.assertFalse(record["chain"]["audit_receipt"]["valid"])
            self.assertIn(error_contains, record["chain"]["audit_receipt"]["error"])

    def test_verified_package_reuses_h7_integrity_checks(self):
        result = self._evaluate()

        self.assertEqual(result["evidence_mode"], "REAL-H7-SCHWAB-PRECLOSE-AUDIT")
        self.assertEqual(result["evaluation_session"], SESSION)
        self.assertEqual(result["whole_universe_verdict"], "GO")
        for symbol in SYMBOLS:
            binding = result["symbols"][symbol]["chain"]["audit_receipt"]
            self.assertTrue(binding["valid"])
            self.assertEqual(binding["provider"], "schwab")

    def test_verified_package_builds_hash_bound_durable_receipt(self):
        result = self._evaluate()

        receipt = h7_data_gate.build_receipt(
            result,
            source_health_receipt=self._source_health(),
            source_health_receipt_path=self.root / "source-health.json",
        )

        stored_manifest = json.loads(self.manifest_path.read_text())
        self.assertEqual(receipt["evidence_mode"], gate.EVIDENCE_MODE)
        self.assertEqual(receipt["schwab_manifest_hash"], stored_manifest["manifest_hash"])
        self.assertEqual(receipt["schwab_capture_receipt_hash"], sha256_file(self.receipt_path))

    def test_verified_receipt_passes_registration_builder_end_to_end(self):
        from test_h7_schwab_window_registration import evidence, owner_inputs, owner_manifest

        from options_researcher import h7_schwab_window_registration as registration

        result = self._evaluate()
        source_health = self._source_health()
        source_health_path = self.root / "source-health.json"
        write_immutable_receipt(source_health, source_health_path)
        receipt = h7_data_gate.build_receipt(
            result,
            source_health_receipt=source_health,
            source_health_receipt_path=source_health_path,
        )
        event = registration.build_window_registration_event(
            owner=owner_inputs(
                SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH=SESSION,
                WINDOW_START_DECISION_SESSION="2026-08-11",
            ),
            evidence=evidence(
                data_gate_evidence_mode=receipt["evidence_mode"],
                data_gate_receipt=receipt,
                data_gate_receipt_hash=receipt["receipt_hash"],
                source_health_receipt_hash=receipt["source_health_receipt_hash"],
                source_health_evidence_id=receipt["source_health_receipt_hash"],
                data_gate_evidence_id=receipt["receipt_hash"],
                last_historical_session=SESSION,
                last_historical_manifest_receipt_hash=receipt["schwab_manifest_hash"],
            ),
            universe_manifest=owner_manifest(),
        )

        self.assertEqual(
            event["payload"]["gates"]["data_gate_receipt_hash"],
            receipt["receipt_hash"],
        )

    def test_forged_input_binding_cannot_pass_durable_validation(self):
        from research.receipts import input_file_record, verify_receipt

        result = self._evaluate()
        source_health = self._source_health()
        source_health_path = self.root / "source-health.json"
        write_immutable_receipt(source_health, source_health_path)
        receipt = h7_data_gate.build_receipt(
            result,
            source_health_receipt=source_health,
            source_health_receipt_path=source_health_path,
        )
        h7_data_gate.validate_durable_receipt(receipt)

        first, second = SYMBOLS[0], SYMBOLS[1]
        payload = {
            key: value
            for key, value in receipt.items()
            if key not in ("receipt_schema", "receipt_type", "receipt_hash")
        }
        payload["input_files"] = dict(payload["input_files"])
        payload["input_files"][f"close:{first}"] = input_file_record(
            self.close_dir / f"{second}.parquet"
        )
        forged = make_receipt("data_gate", payload)

        self.assertEqual([], verify_receipt(forged))
        with self.assertRaisesRegex(ValueError, "input binding failed scope closure"):
            h7_data_gate.validate_durable_receipt(forged)

    def test_thetadata_shaped_binding_cannot_wear_schwab_mode(self):
        result = self._evaluate()
        for record in result["symbols"].values():
            record["chain"]["audit_receipt"] = {
                "valid": True,
                "schema": "cache-audit-v2",
                "consumer_scope": "H7",
            }

        with self.assertRaisesRegex(ValueError, "verified Schwab"):
            h7_data_gate.build_receipt(
                result,
                source_health_receipt=self._source_health(),
                source_health_receipt_path=self.root / "source-health.json",
            )

    def test_schwab_binding_cannot_wear_thetadata_mode(self):
        result = self._evaluate()
        result["evidence_mode"] = h7_data_gate.REAL_H7_EVIDENCE_MODE

        with self.assertRaisesRegex(ValueError, "real H7 full-audit"):
            h7_data_gate.build_receipt(
                result,
                source_health_receipt=self._source_health(),
                source_health_receipt_path=self.root / "source-health.json",
            )

    def test_manifest_tampered_after_evaluation_cannot_build_receipt(self):
        result = self._evaluate()
        stored_manifest = json.loads(self.manifest_path.read_text())
        stored_manifest["files"][SYMBOLS[0]]["row_count"] += 1
        self.manifest_path.write_text(json.dumps(stored_manifest, indent=2, sort_keys=True) + "\n")

        with self.assertRaisesRegex(ValueError, "verified Schwab"):
            h7_data_gate.build_receipt(
                result,
                source_health_receipt=self._source_health(),
                source_health_receipt_path=self.root / "source-health.json",
            )

    def test_missing_session_file_refuses_without_fallback(self):
        path = self.chain_dir / f"{TARGET}_{SESSION}.parquet"
        path.rename(self.chain_dir / f"{TARGET}_2026-08-07.parquet")

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="missing")

    def test_stale_receipt_refuses(self):
        receipt = json.loads(self.receipt_path.read_text())
        receipt["session"] = "2026-08-07"
        self.receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="receipt session")

    def test_partial_receipt_refuses(self):
        receipt = json.loads(self.receipt_path.read_text())
        receipt["universe"] = [TARGET]
        self.receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="universe")

    def test_single_expiration_smuggling_refuses(self):
        chain_frame(expirations=("2026-08-21",)).to_parquet(
            self.chain_dir / f"{TARGET}_{SESSION}.parquet"
        )
        self.manifest_path.unlink()
        self._write_package()

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="expiration")

    def test_same_size_byte_tamper_returns_no_go_and_logs_failure(self):
        path = self.chain_dir / f"{TARGET}_{SESSION}.parquet"
        with path.open("r+b") as stream:
            stream.seek(16)
            original = stream.read(1)
            stream.seek(16)
            stream.write(bytes([original[0] ^ 0x01]))

        with self.assertLogs(gate.__name__, level="ERROR") as captured:
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains=f"hash mismatch for {TARGET}")
        self.assertIn("Schwab package verification failed", captured.output[0])
        self.assertIn(f"hash mismatch for {TARGET}", captured.output[0])
        self.assertIn("Traceback", captured.output[0])

    def test_evaluation_never_constructs_a_schwab_client(self):
        with mock.patch(
            "data.schwab_adapter._client", side_effect=AssertionError("network client")
        ):
            result = self._evaluate()
        self.assertEqual(result["whole_universe_verdict"], "GO")


if __name__ == "__main__":
    unittest.main()

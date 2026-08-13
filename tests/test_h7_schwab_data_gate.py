"""Offline fail-closed tests for the Schwab exact-session H7 data gate."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher import h7_schwab_data_gate as gate
from research.hashing import sha256_file
from tools import schwab_chain_manifest as manifest

SESSION = "2026-08-10"
REQUESTED = date(2026, 8, 11)
SYMBOLS = ["AAA", "BBB"]


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
            "force": False,
            "universe": SYMBOLS,
            "overall_status": "ok",
            "names": names,
            "manifest_hash": built["manifest_hash"],
        }
        self.receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )

    def _evaluate(self):
        return gate.evaluate(
            REQUESTED,
            close_dir=self.close_dir,
            chain_dir=self.chain_dir,
            manifest_path=self.manifest_path,
            receipt_path=self.receipt_path,
            symbols=SYMBOLS,
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

    def test_missing_session_file_refuses_without_fallback(self):
        path = self.chain_dir / f"AAA_{SESSION}.parquet"
        path.rename(self.chain_dir / "AAA_2026-08-07.parquet")

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="missing")

    def test_stale_receipt_refuses(self):
        receipt = json.loads(self.receipt_path.read_text())
        receipt["session"] = "2026-08-07"
        self.receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="receipt session")

    def test_partial_receipt_refuses(self):
        receipt = json.loads(self.receipt_path.read_text())
        receipt["universe"] = ["AAA"]
        self.receipt_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n"
        )

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="universe")

    def test_single_expiration_smuggling_refuses(self):
        chain_frame(expirations=("2026-08-21",)).to_parquet(
            self.chain_dir / f"AAA_{SESSION}.parquet"
        )
        self.manifest_path.unlink()
        self._write_package()

        with self.assertLogs(gate.__name__, level="ERROR"):
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="expiration")

    def test_same_size_byte_tamper_returns_no_go_and_logs_failure(self):
        path = self.chain_dir / f"AAA_{SESSION}.parquet"
        with path.open("r+b") as stream:
            stream.seek(16)
            original = stream.read(1)
            stream.seek(16)
            stream.write(bytes([original[0] ^ 0x01]))

        with self.assertLogs(gate.__name__, level="ERROR") as captured:
            result = self._evaluate()

        self._assert_package_no_go(result, error_contains="hash mismatch for AAA")
        self.assertIn("Schwab package verification failed", captured.output[0])
        self.assertIn("hash mismatch for AAA", captured.output[0])
        self.assertIn("Traceback", captured.output[0])

    def test_evaluation_never_constructs_a_schwab_client(self):
        with mock.patch(
            "data.schwab_adapter._client", side_effect=AssertionError("network client")
        ):
            result = self._evaluate()
        self.assertEqual(result["whole_universe_verdict"], "GO")


if __name__ == "__main__":
    unittest.main()

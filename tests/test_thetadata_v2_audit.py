"""Offline wrapper tests for the full OD-1 v2 data audit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock

import pandas as pd
from test_thetadata_v2_backfill import _raw_frames

from research.hashing import sha256_file
from tools import thetadata_v2_audit as audit
from tools import thetadata_v2_backfill as backfill

SESSION = "2026-07-27"


class V2FullAuditTests(unittest.TestCase):
    def _identity(self):
        return {"commit": "test", "source_paths": [], "dirty": False, "dirty_paths": []}

    def test_source_identity_covers_runtime_write_and_fixture_dependencies(self):
        self.assertIn("data/atomic_io.py", audit.SOURCE_PATHS)
        self.assertIn("options_researcher/h7_synthetic_proof.py", audit.SOURCE_PATHS)

    def test_source_identity_uses_latest_source_commit_and_exact_hashes(self):
        source_commit = CompletedProcess([], 0, "source-commit\n", "")
        clean_status = CompletedProcess([], 0, "", "")
        with mock.patch(
            "tools.thetadata_v2_audit.subprocess.run",
            side_effect=(source_commit, clean_status),
        ) as run:
            identity = audit._source_identity()

        command = run.call_args_list[0].args[0]
        self.assertEqual(command[:5], ("git", "log", "-1", "--format=%H", "--"))
        self.assertEqual(command[5:], audit.SOURCE_PATHS)
        self.assertEqual(identity["git_source_commit"], "source-commit")
        self.assertEqual(set(identity["source_hashes"]), set(audit.SOURCE_PATHS))
        self.assertTrue(identity["source_hashes_hash"])

    def test_full_audit_binds_both_raw_provider_frames(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(
                backfill.thetadata_adapter, "_fetch_raw", return_value=_raw_frames()
            ):
                backfill._capture_one(root, "NVDA", SESSION, code_sha="a" * 40)
            base = {
                "blocks": [],
                "warnings": [],
                "verdict": "PASS",
                "file_hashes": {},
            }
            with (
                mock.patch.object(audit, "SYMBOLS", ("NVDA",)),
                mock.patch.object(audit, "EXPECTED_SESSIONS", 1),
                mock.patch.object(audit, "trading_days", return_value=[SESSION]),
                mock.patch.object(audit.base_audit, "run_audit", return_value=base) as base_run,
            ):
                report = audit.run_full_audit(root, root / "closes", identity=self._identity())
            self.assertEqual(report["verdict"], "PASS WITH WARNINGS")
            self.assertEqual(len(report["raw_file_hashes"]), 2)
            self.assertTrue(report["receipt_hash"])
            self.assertEqual(base_run.call_args.kwargs["parity_mode"], "diagnostic")

    def test_missing_attestation_is_a_provenance_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = {
                "blocks": [],
                "warnings": [],
                "verdict": "PASS",
                "file_hashes": {},
            }
            with (
                mock.patch.object(audit, "SYMBOLS", ("NVDA",)),
                mock.patch.object(audit, "EXPECTED_SESSIONS", 1),
                mock.patch.object(audit, "trading_days", return_value=[SESSION]),
                mock.patch.object(audit.base_audit, "run_audit", return_value=base),
            ):
                report = audit.run_full_audit(root, root / "closes", identity=self._identity())
            self.assertEqual(report["verdict"], "BLOCK")
            self.assertEqual(report["blocks"][0]["check"], "PROVENANCE")

    def test_option_timestamp_after_report_window_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            greeks, open_interest = _raw_frames()
            greeks = greeks.copy()
            greeks["timestamp"] = pd.Timestamp("2026-07-27 17:31:00", tz="America/New_York")
            with mock.patch.object(
                backfill.thetadata_adapter,
                "_fetch_raw",
                return_value=(greeks, open_interest),
            ):
                backfill._capture_one(root, "NVDA", SESSION, code_sha="a" * 40)
            base = {
                "blocks": [],
                "warnings": [],
                "verdict": "PASS",
                "file_hashes": {},
            }
            with (
                mock.patch.object(audit, "SYMBOLS", ("NVDA",)),
                mock.patch.object(audit, "EXPECTED_SESSIONS", 1),
                mock.patch.object(audit, "trading_days", return_value=[SESSION]),
                mock.patch.object(audit.base_audit, "run_audit", return_value=base),
            ):
                report = audit.run_full_audit(root, root / "closes", identity=self._identity())
            self.assertEqual(report["verdict"], "BLOCK")
            self.assertIn(
                "option last-trade timestamp is after 17:30 ET",
                [item["detail"] for item in report["blocks"]],
            )

    def test_exact_hash_quarantine_excludes_real_quote_defect_from_verdict_use(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(
                backfill.thetadata_adapter, "_fetch_raw", return_value=_raw_frames()
            ):
                backfill._capture_one(root, "NVDA", SESSION, code_sha="a" * 40)
            chain_path = root / f"NVDA_{SESSION}.parquet"
            quarantine = root / "quarantine.json"
            quarantine.write_text(
                json.dumps(
                    {
                        "schema": "v2-partition-quarantine/v1",
                        "scope_id": audit.SCOPE_ID,
                        "entries": [
                            {
                                "symbol": "NVDA",
                                "session": SESSION,
                                "sha256": sha256_file(chain_path),
                                "size": chain_path.stat().st_size,
                                "checks": [6],
                                "reason": "provider EOD snapshot contains crossed markets",
                            }
                        ],
                    }
                )
            )
            base = {
                "blocks": [
                    {
                        "check": 6,
                        "symbol": "NVDA",
                        "session": SESSION,
                        "detail": "1 crossed market",
                    }
                ],
                "warnings": [],
                "verdict": "BLOCK",
                "file_hashes": {str(chain_path): sha256_file(chain_path)},
            }
            with (
                mock.patch.object(audit, "SYMBOLS", ("NVDA",)),
                mock.patch.object(audit, "EXPECTED_SESSIONS", 1),
                mock.patch.object(audit, "trading_days", return_value=[SESSION]),
                mock.patch.object(audit.base_audit, "run_audit", return_value=base),
            ):
                report = audit.run_full_audit(
                    root,
                    root / "closes",
                    identity=self._identity(),
                    quarantine_path=quarantine,
                )

            self.assertEqual(report["verdict"], "PASS WITH WARNINGS")
            self.assertEqual(report["blocks"], [])
            self.assertEqual(len(report["quarantined_partitions"]), 1)
            self.assertEqual(report["quarantined_findings"][0]["check"], 6)

            payload = json.loads(quarantine.read_text())
            payload["entries"][0]["sha256"] = "0" * 64
            quarantine.write_text(json.dumps(payload))
            with (
                mock.patch.object(audit, "SYMBOLS", ("NVDA",)),
                mock.patch.object(audit, "EXPECTED_SESSIONS", 1),
                mock.patch.object(audit, "trading_days", return_value=[SESSION]),
                mock.patch.object(audit.base_audit, "run_audit", return_value=base),
            ):
                changed = audit.run_full_audit(
                    root,
                    root / "closes",
                    identity=self._identity(),
                    quarantine_path=quarantine,
                )
            self.assertEqual(changed["verdict"], "BLOCK")
            self.assertTrue(any(item["check"] == "QUARANTINE" for item in changed["blocks"]))


if __name__ == "__main__":
    unittest.main()

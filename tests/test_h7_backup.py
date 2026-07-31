"""Offline allow-list and restore-verification tests for the H7 backup tool."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data.cache_schema import CHAIN_COLUMNS_V1
from options_researcher.h7_scope import scope_identity
from research.receipts import make_receipt, write_immutable_receipt
from tools import h7_forward_backup as backup


def _write_v1_chain(path: Path) -> tuple[str, int]:
    pd.DataFrame(columns=CHAIN_COLUMNS_V1).to_parquet(path, index=False)
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest(), len(content)


class BackupTests(unittest.TestCase):
    def test_backup_command_has_no_credentials_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".cache/chains").mkdir(parents=True)
            (root / ".cache/chains/one.parquet").write_bytes(b"chain")
            (root / ".env").write_text("SECRET=do-not-back-up")
            fake = mock.Mock(return_value=mock.Mock(stdout='{"snapshot_id":"abc123"}\n'))
            with mock.patch.object(backup, "_run_restic", fake):
                path = backup.run_backup(
                    completed_session="2026-07-10", root=root, receipt_path=root / "backup.json"
                )
            args = fake.call_args.args[0]
            self.assertNotIn("SECRET=do-not-back-up", args)
            self.assertIn("--exclude", args)
            self.assertEqual(path.read_text().count("abc123"), 1)

    def test_restore_verification_checks_manifest_and_gate_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/chains/one.parquet"
            chain.parent.mkdir(parents=True)
            digest, size = _write_v1_chain(chain)
            manifest = root / "data/chain_cache_manifest.txt"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(f"{digest}  {size}  one.parquet\n")
            receipt_dir = root / "reports/h7_receipts"
            record = {
                "path": ".cache/chains/one.parquet",
                "exists": True,
                "sha256": digest,
            }
            receipt = make_receipt(
                "data_gate",
                {
                    "scope": scope_identity(),
                    "whole_universe_verdict": "GO",
                    "go_count": 15,
                    "input_files": {"chain": record},
                },
            )
            write_immutable_receipt(receipt, receipt_dir / "gate.json")
            result = backup.verify_restored_tree(root)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["manifest"], "OK")
            self.assertEqual(result["data_gates"], 1)

    def test_restore_verification_finds_data_gate_receipt_in_real_location(self):
        # Regression (2026-07-20 restore drill): production writes data_gate
        # receipts to reports/h7_data_gate/<scope_id>/receipts/, NOT
        # reports/h7_receipts. Before the fix verify_restored_tree scanned only
        # reports/h7_receipts, so a COMPLETE backup verified as data_gates=0 and
        # failed closed. This pins the real production path.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/chains/one.parquet"
            chain.parent.mkdir(parents=True)
            digest, size = _write_v1_chain(chain)
            manifest = root / "data/chain_cache_manifest.txt"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(f"{digest}  {size}  one.parquet\n")
            scope_id = scope_identity()["scope_id"]
            receipt_dir = root / "reports/h7_data_gate" / scope_id / "receipts"
            record = {
                "path": ".cache/chains/one.parquet",
                "exists": True,
                "sha256": digest,
            }
            receipt = make_receipt(
                "data_gate",
                {
                    "scope": scope_identity(),
                    "whole_universe_verdict": "GO",
                    "go_count": 15,
                    "input_files": {"chain": record},
                },
            )
            write_immutable_receipt(receipt, receipt_dir / "2026-07-17.json")
            result = backup.verify_restored_tree(root)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["data_gates"], 1)


if __name__ == "__main__":
    unittest.main()

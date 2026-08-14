"""Offline allow-list and restore-verification tests for the H7 backup tool."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from options_researcher.h7_scope import scope_identity
from research.receipts import make_receipt, write_immutable_receipt
from tools import h7_forward_backup as backup


class BackupTests(unittest.TestCase):
    def test_allow_list_includes_new_schwab_evidence_and_ledger(self):
        expected = {
            Path(".cache/schwab_chains"),
            Path("reports/schwab_chains"),
            Path("reports/h7_forward_schwab"),
            Path("ledger/h7_forward_schwab"),
        }
        self.assertTrue(expected <= set(backup.BACKUP_PATHS))

    def test_backup_command_has_no_credentials_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".cache/chains").mkdir(parents=True)
            (root / ".cache/chains/one.parquet").write_bytes(b"chain")
            (root / ".env").write_text("SECRET=do-not-back-up")
            fake = mock.Mock(return_value=mock.Mock(stdout='{"snapshot_id":"abc123"}\n'))
            with mock.patch.object(backup, "_run_restic", fake):
                path = backup.run_backup(
                    completed_session="2026-07-10", root=root,
                    receipt_path=root / "backup.json")
            args = fake.call_args.args[0]
            self.assertNotIn("SECRET=do-not-back-up", args)
            self.assertIn("--exclude", args)
            self.assertEqual(path.read_text().count("abc123"), 1)

    def test_restore_verification_checks_manifest_and_gate_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/chains/one.parquet"
            chain.parent.mkdir(parents=True)
            chain.write_bytes(b"chain")
            manifest = root / "data/chain_cache_manifest.txt"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                f"{hashlib.sha256(b'chain').hexdigest()}  5  one.parquet\n")
            receipt_dir = root / "reports/h7_receipts"
            record = {"path": ".cache/chains/one.parquet", "exists": True,
                      "sha256": hashlib.sha256(b"chain").hexdigest()}
            receipt = make_receipt("data_gate", {
                "scope": scope_identity(), "whole_universe_verdict": "GO",
                "go_count": 15, "input_files": {"chain": record},
            })
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
            chain.write_bytes(b"chain")
            manifest = root / "data/chain_cache_manifest.txt"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                f"{hashlib.sha256(b'chain').hexdigest()}  5  one.parquet\n")
            scope_id = scope_identity()["scope_id"]
            receipt_dir = root / "reports/h7_data_gate" / scope_id / "receipts"
            record = {"path": ".cache/chains/one.parquet", "exists": True,
                      "sha256": hashlib.sha256(b"chain").hexdigest()}
            receipt = make_receipt("data_gate", {
                "scope": scope_identity(), "whole_universe_verdict": "GO",
                "go_count": 15, "input_files": {"chain": record},
            })
            write_immutable_receipt(receipt, receipt_dir / "2026-07-17.json")
            result = backup.verify_restored_tree(root)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["data_gates"], 1)

    def _backup_receipt(self, root: Path, *, completed_session="2026-08-10",
                        snapshot_id="snapshot-abc") -> tuple[Path, dict]:
        receipt = make_receipt("backup", {
            "completed_session": completed_session,
            "snapshot_id": snapshot_id,
            "scope": scope_identity(),
            "input_files": backup.backup_inventory(root),
        })
        path = root / "backup-receipt.json"
        write_immutable_receipt(receipt, path)
        return path, receipt

    def _restic_restore(self, source: Path):
        def restore(args, *, cwd):
            target = Path(args[args.index("--target") + 1])
            for child in source.iterdir():
                if child.name == "backup-receipt.json":
                    continue
                destination = target / child.name
                if child.is_dir():
                    shutil.copytree(child, destination)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(child, destination)
            return mock.Mock(stdout="")

        return mock.Mock(side_effect=restore)

    def test_restore_check_uses_receipt_snapshot_and_requires_exact_inventory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/schwab_chains/VST_2026-08-10.parquet"
            chain.parent.mkdir(parents=True)
            chain.write_bytes(b"exact-chain")
            backup_path, backup_receipt = self._backup_receipt(root)
            restore_receipt_path = root / "restore-receipt.json"
            fake = self._restic_restore(root)

            with (
                mock.patch.object(backup, "_run_restic", fake),
                mock.patch.object(
                    backup, "verify_restored_tree", return_value={"ok": True}
                ),
            ):
                backup.run_restore_check(
                    backup_receipt_path=backup_path,
                    completed_session="2026-08-10",
                    root=root,
                    receipt_path=restore_receipt_path,
                )

            self.assertEqual(fake.call_args.args[0][1], "snapshot-abc")
            restored = json.loads(restore_receipt_path.read_text())
            self.assertEqual(restored["snapshot_id"], "snapshot-abc")
            self.assertEqual(
                restored["backup_receipt_hash"], backup_receipt["receipt_hash"]
            )
            self.assertEqual(restored["restored_inventory"], backup_receipt["input_files"])

    def test_restore_check_refuses_wrong_snapshot_receipt_and_session(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/schwab_chains/VST_2026-08-10.parquet"
            chain.parent.mkdir(parents=True)
            chain.write_bytes(b"chain")
            backup_path, _ = self._backup_receipt(root)

            with self.assertRaisesRegex(RuntimeError, "snapshot"):
                backup.run_restore_check(
                    backup_receipt_path=backup_path,
                    snapshot="different-snapshot",
                    completed_session="2026-08-10",
                    root=root,
                )
            with self.assertRaisesRegex(RuntimeError, "completed session"):
                backup.run_restore_check(
                    backup_receipt_path=backup_path,
                    completed_session="2026-08-07",
                    root=root,
                )

            wrong = make_receipt("backup_restore", {
                "completed_session": "2026-08-10",
                "snapshot_id": "snapshot-abc",
                "scope": scope_identity(),
                "input_files": backup.backup_inventory(root),
            })
            wrong_path = root / "wrong-type.json"
            write_immutable_receipt(wrong, wrong_path)
            with self.assertRaisesRegex(ValueError, "expected 'backup'"):
                backup.run_restore_check(
                    backup_receipt_path=wrong_path,
                    completed_session="2026-08-10",
                    root=root,
                )

    def test_restore_check_refuses_missing_extra_changed_size_and_changed_hash(self):
        mutations = {
            "missing": lambda path, restored: path.unlink(),
            "extra": lambda path, restored: (
                (restored / ".cache/schwab_chains/EXTRA_2026-08-10.parquet")
                .write_bytes(b"extra")
            ),
            "changed size": lambda path, restored: path.write_bytes(b"different-size"),
            "changed hash": lambda path, restored: path.write_bytes(b"other"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                chain = root / ".cache/schwab_chains/VST_2026-08-10.parquet"
                chain.parent.mkdir(parents=True)
                chain.write_bytes(b"chain")
                backup_path, _ = self._backup_receipt(root)

                def restore(args, *, cwd):
                    restored = Path(args[args.index("--target") + 1])
                    target = restored / ".cache/schwab_chains/VST_2026-08-10.parquet"
                    target.parent.mkdir(parents=True)
                    target.write_bytes(b"chain")
                    mutate(target, restored)
                    return mock.Mock(stdout="")

                with (
                    mock.patch.object(backup, "_run_restic", side_effect=restore),
                    mock.patch.object(
                        backup, "verify_restored_tree", return_value={"ok": True}
                    ),
                ):
                    with self.assertRaisesRegex(RuntimeError, "inventory"):
                        backup.run_restore_check(
                            backup_receipt_path=backup_path,
                            completed_session="2026-08-10",
                            root=root,
                        )


if __name__ == "__main__":
    unittest.main()

"""Offline allow-list and restore-verification tests for the H7 backup tool."""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from options_researcher.h7_scope import scope_identity
from research.receipts import make_receipt, write_immutable_receipt
from tools import h7_forward_backup as backup
from tools.irreplaceable_data_guard import DEFAULT_NAMESPACES


class BackupTests(unittest.TestCase):
    def test_allow_list_includes_new_schwab_evidence_and_ledger(self):
        expected = {
            Path(".cache/schwab_chains"),
            Path("reports/schwab_chains"),
            Path("reports/h7_forward_schwab"),
            Path("ledger/h7_forward_schwab"),
        }
        self.assertTrue(expected <= set(backup.BACKUP_PATHS))

    def test_allow_list_covers_every_irreplaceable_namespace(self):
        protected = {Path(namespace) for namespace in DEFAULT_NAMESPACES}

        self.assertEqual(set(), protected - set(backup.BACKUP_PATHS))

    def test_backup_prints_expected_payload_size_before_restic(self):
        with tempfile.TemporaryDirectory() as temp:
            # run_backup resolves its root, and on macOS the tempdir lives
            # behind the /var -> /private/var symlink; resolve up front so the
            # cwd assertion below compares like with like.
            root = Path(temp).resolve()
            chain = root / ".cache/chains/one.parquet"
            chain.parent.mkdir(parents=True)
            chain.write_bytes(b"chain")
            output = io.StringIO()

            def fake_restic(_args, *, cwd):
                self.assertEqual(cwd, root)
                self.assertEqual(
                    output.getvalue(),
                    "H7 BACKUP PREFLIGHT -- expected payload: 5 bytes (5 B)\n",
                )
                return mock.Mock(stdout='{"snapshot_id":"abc123"}\n')

            with (
                redirect_stdout(output),
                mock.patch.object(backup, "_run_restic", side_effect=fake_restic),
            ):
                backup.run_backup(
                    completed_session="2026-07-10",
                    root=root,
                    receipt_path=root / "backup.json",
                )

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


class RecordedInvalidationTests(unittest.TestCase):
    """Drill disposition B (owner-directed 2026-08-14, decision-menu ruling 1).

    A sealed receipt's input binding that an owner-approved data refresh made
    permanently unverifiable is accepted ONLY when a well-formed recorded fact
    names that receipt, that label, and that sealed hash. Everything else --
    no fact, another receipt's fact, a malformed fact, a vanished file -- still
    fails exactly as it did before.
    """

    SEALED = hashlib.sha256(b"july-closes").hexdigest()
    INVALIDATED_BY = "2026-08-05 closes refresh (owner-directed 2026-08-04)"
    PROVENANCE = "owner-directed in-session 2026-08-14 (disposition B)"

    def _tree(self, *, close_bytes=b"august-closes", second_close=False,
              session="2026-07-17", variant="") -> tuple[Path, dict, Path]:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        chain = root / ".cache/chains/one.parquet"
        chain.parent.mkdir(parents=True)
        chain.write_bytes(b"chain")
        manifest = root / "data/chain_cache_manifest.txt"
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            f"{hashlib.sha256(b'chain').hexdigest()}  5  one.parquet\n")
        inputs = {
            "chain:AMD": {"path": ".cache/chains/one.parquet", "exists": True,
                          "sha256": hashlib.sha256(b"chain").hexdigest()},
            "close:AMD": {"path": ".cache/underlying/AMD.parquet", "exists": True,
                          "sha256": self.SEALED},
        }
        closes = root / ".cache/underlying"
        closes.mkdir(parents=True)
        (closes / "AMD.parquet").write_bytes(close_bytes)
        if second_close:
            inputs["close:VST"] = {"path": ".cache/underlying/VST.parquet",
                                   "exists": True, "sha256": self.SEALED}
            (closes / "VST.parquet").write_bytes(close_bytes)
        receipt = make_receipt("data_gate", {
            "scope": scope_identity(), "whole_universe_verdict": "GO",
            "go_count": len(scope_identity()["symbols"]),
            "evaluation_session": session,
            # Changes the receipt's CONTENT hash without moving its path.
            "source_hash": f"variant{variant}",
            "input_files": inputs,
        })
        path = (root / "reports/h7_data_gate" / scope_identity()["scope_id"]
                / "receipts" / f"{session}.json")
        write_immutable_receipt(receipt, path)
        return root, receipt, path

    def _record(self, root: Path, receipt_path: Path, **overrides) -> list[str]:
        kwargs = {
            "receipt_paths": [receipt_path], "label_prefix": "close:",
            "invalidated_by": self.INVALIDATED_BY,
            "recorded_session": "2026-08-14", "provenance": self.PROVENANCE,
            "root": root,
        }
        kwargs.update(overrides)
        return backup.record_invalidations(**kwargs)

    @staticmethod
    def _write_fact_line(root: Path, text: str) -> None:
        log = root / "ledger/facts.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"2026-08-14T23:00:00+00:00\t{text}\n")

    # --- the four required cases -----------------------------------------
    def test_mismatch_with_recorded_fact_passes_with_a_note_naming_the_fact(self):
        root, receipt, receipt_path = self._tree()
        [line] = self._record(root, receipt_path)
        payload = backup.parse_invalidation_fact(line)
        self.assertIsNotNone(payload)

        result = backup.verify_restored_tree(root)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["problems"], [])
        self.assertEqual(len(result["notes"]), 1)
        note = result["notes"][0]
        self.assertIn("changed input close:AMD", note)
        self.assertIn(backup.INVALIDATION_TOKEN, note)
        self.assertIn(backup.invalidation_fact_id(payload), note)
        self.assertIn(self.INVALIDATED_BY, note)
        self.assertIn(self.PROVENANCE, note)
        self.assertIn("ledger/facts.log", note)

    def test_mismatch_without_any_recorded_fact_still_fails(self):
        root, _, _ = self._tree()

        result = backup.verify_restored_tree(root)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])
        self.assertTrue(
            any("changed input close:AMD" in problem
                for problem in result["problems"]), result["problems"])

    def test_fact_recorded_for_a_different_receipt_covers_nothing(self):
        root, receipt, _ = self._tree()
        other_root, other, other_receipt_path = self._tree(session="2026-07-20")
        [line] = self._record(other_root, other_receipt_path)
        # Same sealed hash and same label, DIFFERENT sealed receipt: a fact is
        # bound to one receipt's content hash and covers nothing else.
        self.assertNotEqual(receipt["receipt_hash"], other["receipt_hash"])
        self._write_fact_line(root, line)

        result = backup.verify_restored_tree(root)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])
        self.assertTrue(any("changed input close:AMD" in problem
                            for problem in result["problems"]))

    def test_fact_from_a_different_receipt_at_the_same_path_covers_nothing(self):
        # Isolates the receipt-hash key: same relative path, same label, same
        # sealed hash -- only the receipt's CONTENT differs. Without the
        # content hash in the coverage key, one receipt's recorded
        # invalidation would silently bless another receipt's binding.
        root, receipt, _ = self._tree(variant="a")
        other_root, other, other_receipt_path = self._tree(variant="b")
        [line] = self._record(other_root, other_receipt_path)
        self.assertNotEqual(receipt["receipt_hash"], other["receipt_hash"])
        self.assertIn(
            "reports/h7_data_gate/h7-forward-15-v1/receipts/2026-07-17.json", line)
        self._write_fact_line(root, line)

        result = backup.verify_restored_tree(root)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])
        self.assertTrue(any("changed input close:AMD" in problem
                            for problem in result["problems"]))

    def test_fact_naming_the_wrong_sealed_hash_covers_nothing(self):
        # Isolates the sealed hash in the coverage key: right receipt, right
        # label, but the fact claims a DIFFERENT sealed hash than the one this
        # receipt committed to, so it describes some other binding entirely.
        root, _, receipt_path = self._tree()
        [line] = self._record(root, receipt_path, dry_run=True)
        payload = backup.parse_invalidation_fact(line)
        assert payload is not None
        wrong_sealed = hashlib.sha256(b"some-other-sealed-bytes").hexdigest()
        self.assertNotEqual(wrong_sealed, self.SEALED)
        mislabelled = {**payload, "bindings": {"close:AMD": wrong_sealed}}
        index = {(payload["receipt_hash"], "close:AMD", wrong_sealed): mislabelled}

        result = backup.verify_restored_tree(root, invalidations=index)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])
        self.assertTrue(any("changed input close:AMD" in problem
                            for problem in result["problems"]))

    def test_a_second_change_still_passes_but_is_called_out_in_the_note(self):
        """Characterization of the spec's "Deliberate limits" (sealed side only).

        Coverage pins the hash the receipt SEALED, not the replacement bytes,
        because the closes cache is refreshed on the ordinary operating cadence
        and pinning the replacement would re-break the drill every refresh. The
        price is that a later, unrelated change to the same file is accepted
        too -- so the note says so, loudly, instead of staying silent.
        """
        root, _, receipt_path = self._tree()
        [line] = self._record(root, receipt_path)
        payload = backup.parse_invalidation_fact(line)
        assert payload is not None
        recorded_observed = payload["observed"]["close:AMD"]

        before = backup.verify_restored_tree(root)
        self.assertTrue(before["ok"], before)
        self.assertNotIn("AGAIN", before["notes"][0])

        # A THIRD value: neither the sealed July bytes nor the bytes observed
        # when the invalidation was recorded.
        (root / ".cache/underlying/AMD.parquet").write_bytes(b"september-closes")
        after = backup.verify_restored_tree(root)

        self.assertTrue(after["ok"], after)
        self.assertEqual(after["problems"], [])
        self.assertEqual(len(after["notes"]), 1)
        self.assertNotEqual(after["notes"][0], before["notes"][0])
        self.assertIn("changed AGAIN since the invalidation was recorded",
                      after["notes"][0])
        self.assertIn(recorded_observed[:12], after["notes"][0])
        self.assertIn(
            hashlib.sha256(b"september-closes").hexdigest()[:12], after["notes"][0])

    def test_fact_recorded_at_a_different_receipt_path_covers_nothing(self):
        root, receipt, receipt_path = self._tree()
        [line] = self._record(root, receipt_path, dry_run=True)
        payload = backup.parse_invalidation_fact(line)
        assert payload is not None
        # Right receipt hash, right label, right sealed hash -- but the fact
        # claims the receipt lives somewhere else, so it does not apply.
        moved = {**payload, "receipt": "reports/h7_receipts/somewhere-else.json"}
        index = {(payload["receipt_hash"], label, sealed): moved
                 for label, sealed in payload["bindings"].items()}

        result = backup.verify_restored_tree(root, invalidations=index)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])

    def test_malformed_or_partial_facts_cover_nothing(self):
        _, receipt, receipt_path = self._tree()
        base_root, _, base_receipt_path = self._tree()
        [good] = self._record(base_root, base_receipt_path, dry_run=True)
        prefix, _, body = good.partition("{")
        payload = json.loads("{" + body)
        relative = payload["receipt"]

        def rendered(mutated: dict, *, path: str | None = None) -> str:
            from research.hashing import canonical_json

            return (f"{backup.INVALIDATION_TOKEN} {path or relative} "
                    f"{canonical_json(mutated)}")

        mutations = {
            "truncated json": prefix + '{"schema": "h7-input',
            "not json at all": f"{backup.INVALIDATION_TOKEN} {relative} nonsense",
            "no json part": f"{backup.INVALIDATION_TOKEN}{relative}",
            "wrong schema": rendered({**payload, "schema": "something-else/v1"}),
            "missing field": rendered(
                {key: value for key, value in payload.items() if key != "provenance"}),
            "extra field": rendered({**payload, "surprise": "extra"}),
            "empty bindings": rendered({**payload, "bindings": {}}),
            "non hex binding": rendered(
                {**payload, "bindings": {"close:AMD": "not-a-sha256"}}),
            "blank provenance": rendered({**payload, "provenance": "   "}),
            "path disagrees with payload": rendered(payload, path="reports/other.json"),
            "absolute receipt path": rendered(
                {**payload, "receipt": f"/{relative}"}, path=f"/{relative}"),
            "traversing receipt path": rendered(
                {**payload, "receipt": f"../{relative}"}, path=f"../{relative}"),
            "receipt hash truncated": rendered(
                {**payload, "receipt_hash": receipt["receipt_hash"][:32]}),
        }
        for label, text in mutations.items():
            with self.subTest(mutation=label):
                self.assertIsNone(backup.parse_invalidation_fact(text))
                root, _, _ = self._tree()
                self._write_fact_line(root, text)
                result = backup.verify_restored_tree(root)
                self.assertFalse(result["ok"], f"{label}: {result}")
                self.assertEqual(result["notes"], [], label)

    # --- the boundaries the mechanism must NOT cross ----------------------
    def test_recorded_fact_never_covers_a_vanished_input(self):
        root, _, receipt_path = self._tree()
        [line] = self._record(root, receipt_path)
        self.assertIsNotNone(backup.parse_invalidation_fact(line))
        (root / ".cache/underlying/AMD.parquet").unlink()

        result = backup.verify_restored_tree(root)

        self.assertFalse(result["ok"], result)
        self.assertEqual(result["notes"], [])
        self.assertTrue(any("changed input close:AMD" in problem
                            for problem in result["problems"]))

    def test_coverage_is_per_label_not_per_receipt(self):
        root, _, receipt_path = self._tree(second_close=True)
        [line] = self._record(root, receipt_path)
        payload = backup.parse_invalidation_fact(line)
        assert payload is not None
        # Strip one label back out of the recorded fact: the receipt is the
        # same, but close:VST was never recorded, so it must still fail.
        narrowed = dict(payload)
        narrowed["bindings"] = {"close:AMD": payload["bindings"]["close:AMD"]}
        narrowed["observed"] = {"close:AMD": payload["observed"]["close:AMD"]}
        index = {
            (narrowed["receipt_hash"], label, sealed): narrowed
            for label, sealed in narrowed["bindings"].items()
        }

        result = backup.verify_restored_tree(root, invalidations=index)

        self.assertFalse(result["ok"], result)
        self.assertEqual(
            [problem.split(": ", 1)[1] for problem in result["problems"]],
            ["changed input close:VST"])
        self.assertEqual(len(result["notes"]), 1)
        self.assertIn("close:AMD", result["notes"][0])

    def test_intact_binding_is_never_pre_authorised_by_the_recorder(self):
        root, _, receipt_path = self._tree()
        # chain:AMD still verifies; --label-prefix chain: therefore records
        # nothing at all rather than blessing a healthy binding.
        self.assertEqual(
            self._record(root, receipt_path, label_prefix="chain:", dry_run=True), [])

    def test_facts_are_read_from_the_restored_tree_not_the_operator_disk(self):
        root, _, receipt_path = self._tree()
        elsewhere = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, elsewhere, True)
        self._record(root, receipt_path, ledger_dir=elsewhere / "ledger")

        self.assertFalse((root / "ledger/facts.log").exists())
        self.assertFalse(backup.verify_restored_tree(root)["ok"])

    # --- the recorder itself ----------------------------------------------
    def test_recorder_is_append_only_idempotent_and_refuses_divergence(self):
        root, _, receipt_path = self._tree()
        first = self._record(root, receipt_path)
        again = self._record(root, receipt_path)
        log = (root / "ledger/facts.log").read_text(encoding="utf-8")

        self.assertEqual(first, again)
        self.assertEqual(log.count(backup.INVALIDATION_TOKEN), 1)

        with self.assertRaisesRegex(RuntimeError, "dedupe refused"):
            self._record(root, receipt_path, recorded_session="2026-08-15")

    def test_dry_run_records_nothing(self):
        root, _, receipt_path = self._tree()
        self.assertTrue(self._record(root, receipt_path, dry_run=True))
        self.assertFalse((root / "ledger/facts.log").exists())

    def test_recorder_refuses_a_tampered_receipt(self):
        root, _, receipt_path = self._tree()
        tampered = json.loads(receipt_path.read_text())
        tampered["go_count"] = 1
        receipt_path.write_text(json.dumps(tampered))

        with self.assertRaisesRegex(ValueError, "tampered"):
            self._record(root, receipt_path)


if __name__ == "__main__":
    unittest.main()

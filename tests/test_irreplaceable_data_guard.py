"""Tests for tools/irreplaceable_data_guard.py.

These run entirely against temporary fixtures -- never the real 5 GB cache --
so they stay offline, fast, and green on a fresh clone with no cache present.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import irreplaceable_data_guard as guard


def _write(root: Path, rel: str, payload: bytes = b"x") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


class ScanTests(unittest.TestCase):
    def test_absent_directory_reports_not_present(self):
        with tempfile.TemporaryDirectory() as temp:
            result = guard.scan(os.path.join(temp, "nope"))
        self.assertFalse(result["present"])
        self.assertEqual(result["file_count"], 0)
        self.assertEqual(result["total_bytes"], 0)

    def test_counts_nested_files_recursively(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "raw/MU/2025-07-25/chain.parquet", b"abc")
            _write(root, "raw/ET/2025-07-25/chain.parquet", b"de")
            _write(root, "top.parquet", b"f")
            result = guard.scan(str(root))
        self.assertTrue(result["present"])
        self.assertEqual(result["file_count"], 3)
        self.assertEqual(result["total_bytes"], 6)

    def test_deep_digest_is_deterministic_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "a/one.parquet", b"one")
            _write(root, "b/two.parquet", b"two")
            first = guard.scan(str(root), deep=True)
            second = guard.scan(str(root), deep=True)
            self.assertEqual(first["content_digest"], second["content_digest"])

            _write(root, "b/two.parquet", b"CHANGED")
            third = guard.scan(str(root), deep=True)
        self.assertNotEqual(first["content_digest"], third["content_digest"])


class VerifyTests(unittest.TestCase):
    def test_healthy_cache_reports_no_problems(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}
            self.assertEqual(guard.verify(inventory), [])

    def test_lost_file_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            kept = _write(root, "b.parquet", b"bbb")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            kept.unlink()
            problems = guard.verify(inventory)
        self.assertEqual(len(problems), 2)  # lost file + shrank
        self.assertIn("LOST FILES", problems[0])

    def test_entirely_missing_namespace_fails_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            for child in root.iterdir():
                child.unlink()
            root.rmdir()
            problems = guard.verify(inventory)
        self.assertEqual(len(problems), 1)
        self.assertIn("MISSING ENTIRELY", problems[0])

    def test_allow_absent_skips_fresh_clone_but_still_catches_partial_loss(self):
        """A fresh clone has no cache (fine). A HALF-DELETED cache is not fine."""
        with tempfile.TemporaryDirectory() as temp:
            gone = Path(temp) / "gone"
            partial = Path(temp) / "partial"
            _write(gone, "a.parquet", b"aaa")
            _write(partial, "a.parquet", b"aaa")
            doomed = _write(partial, "b.parquet", b"bbb")
            inventory = {
                "namespaces": {
                    str(gone): guard.scan(str(gone)),
                    str(partial): guard.scan(str(partial)),
                }
            }

            gone.joinpath("a.parquet").unlink()
            gone.rmdir()
            doomed.unlink()

            problems = guard.verify(inventory, allow_absent=True)
        self.assertTrue(all("MISSING ENTIRELY" not in p for p in problems))
        self.assertTrue(any("LOST FILES" in p for p in problems))

    def test_growth_is_not_a_problem(self):
        """Adding data is fine; only loss is an incident."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"aaa")
            inventory = {"namespaces": {str(root): guard.scan(str(root))}}

            _write(root, "c.parquet", b"ccccc")
            self.assertEqual(guard.verify(inventory), [])

    def test_never_recorded_namespace_is_ignored(self):
        inventory = {
            "namespaces": {"/nonexistent/ns": {"present": False, "file_count": 0, "total_bytes": 0}}
        }
        self.assertEqual(guard.verify(inventory), [])

    def test_deep_verify_detects_silent_content_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "ns"
            _write(root, "a.parquet", b"original")
            inventory = {"namespaces": {str(root): guard.scan(str(root), deep=True)}}

            _write(root, "a.parquet", b"tampered")  # same name, same length
            shallow = guard.verify(inventory, deep=False)
            deep = guard.verify(inventory, deep=True)
        self.assertEqual(shallow, [])  # counts/sizes match -- invisible
        self.assertEqual(len(deep), 1)
        self.assertIn("CONTENT CHANGED", deep[0])


class InventoryShapeTests(unittest.TestCase):
    def test_future_tickers_is_covered(self):
        """The 2026-08-03 incident namespace must never drop off the list."""
        self.assertIn(".cache/future_tickers", guard.DEFAULT_NAMESPACES)

    def test_chains_v2_is_covered(self):
        self.assertIn(".cache/chains_v2", guard.DEFAULT_NAMESPACES)

    def test_committed_inventory_records_the_incident_namespace(self):
        import json

        repo_root = Path(__file__).resolve().parents[1]
        inventory_path = repo_root / guard.DEFAULT_INVENTORY
        if not inventory_path.exists():  # fresh clone before first generate
            self.skipTest("inventory not generated in this checkout")
        inventory = json.loads(inventory_path.read_text())
        self.assertIn(".cache/future_tickers", inventory["namespaces"])


class RepoRootAnchoringTests(unittest.TestCase):
    """The CLI must anchor on the main checkout, never the invoking directory.

    2026-08-09 false alarm: run with cwd inside a linked worktree, the guard
    found the committed inventory (it travels with every checkout) but not the
    gitignored bytes (they exist only in the main checkout), and reported all
    ~5 GB as MISSING ENTIRELY while every byte sat safe. The one alarm that
    must never cry wolf was crying wolf in its primary use case -- CLAUDE.md
    requires running it exactly when worktrees are about to be deleted.
    """

    GUARD = str(Path(guard.__file__).resolve())

    def _run(self, cwd, *argv, env=None):
        return subprocess.run(
            [sys.executable, self.GUARD, *argv],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env,
        )

    def _fixture_repo(self, temp: Path) -> Path:
        """A tiny git repo shaped like the real one: committed inventory,
        gitignored-in-spirit (untracked) namespace bytes."""
        repo = temp / "main"
        repo.mkdir()

        def git(*args: str) -> None:
            subprocess.run(
                ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                check=True,
                capture_output=True,
            )

        git("init", "-q")
        _write(repo, "myns/a.parquet", b"aaa")
        inventory = {"namespaces": {"myns": guard.scan(str(repo / "myns"))}}
        inv = repo / "data" / "irreplaceable_data_inventory.json"
        inv.parent.mkdir(parents=True)
        inv.write_text(json.dumps(inventory))
        git("add", "data")
        git("commit", "-qm", "inventory")
        return repo

    def test_verify_from_linked_worktree_is_not_a_loss_report(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            worktree = Path(temp) / "wt"
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "add", "--detach", "-q", str(worktree)],
                check=True,
                capture_output=True,
            )
            result = self._run(worktree, "verify")
        self.assertNotIn("MISSING ENTIRELY", result.stderr)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("irreplaceable data: OK", result.stdout)
        self.assertIn("main checkout", result.stderr)  # says what it anchored on

    def test_verify_from_subdirectory_anchors_on_repo_root(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            sub = repo / "deep" / "dir"
            sub.mkdir(parents=True)
            result = self._run(sub, "verify")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertNotIn("MISSING ENTIRELY", result.stderr)

    def test_outside_any_repo_is_a_location_error_not_a_loss(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(Path(temp).parent)}
            result = self._run(temp, "verify", env=env)
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertIn("NOT a data-loss finding", result.stderr)
        self.assertNotIn("MISSING ENTIRELY", result.stderr)

    def test_genuine_loss_still_alarms_from_the_main_checkout(self):
        """The fix must not soften the real alarm -- only relocate its anchor."""
        with tempfile.TemporaryDirectory() as temp:
            repo = self._fixture_repo(Path(temp))
            (repo / "myns" / "a.parquet").unlink()
            (repo / "myns").rmdir()
            result = self._run(repo, "verify")
        self.assertEqual(result.returncode, 1)
        self.assertIn("MISSING ENTIRELY", result.stderr)
        self.assertIn("cannot be re-fetched", result.stderr)
        # every namespace absent => point at the canonical checkout first
        self.assertIn("canonical", result.stderr)


if __name__ == "__main__":
    unittest.main()

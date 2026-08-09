"""Tests for tools/irreplaceable_data_guard.py.

These run entirely against temporary fixtures -- never the real 5 GB cache --
so they stay offline, fast, and green on a fresh clone with no cache present.
"""
from __future__ import annotations

import os
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
    def test_schwab_chains_is_covered(self):
        self.assertIn(".cache/schwab_chains", guard.DEFAULT_NAMESPACES)

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
        self.assertIn(".cache/schwab_chains", inventory["namespaces"])


if __name__ == "__main__":
    unittest.main()

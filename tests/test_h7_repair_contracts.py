"""Offline tests for the H7 scope, immutable receipts, and refresh manifest."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from data import cache_runner
from options_researcher.h7_scope import H7_SCOPE_ID, scope_hash, scope_identity
from research.receipts import input_files, load_receipt, make_receipt, write_immutable_receipt


class ScopeContractTests(unittest.TestCase):
    def test_current_scope_is_versioned_and_15_names(self):
        identity = scope_identity()
        self.assertEqual(identity["scope_id"], H7_SCOPE_ID)
        self.assertEqual(len(identity["symbols"]), 15)
        self.assertEqual(identity["scope_hash"], scope_hash())

    def test_old_12_name_identity_cannot_equal_current(self):
        old = ("CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD",
               "AVGO", "VST", "CEG", "MSFT", "AMZN")
        self.assertNotEqual(scope_identity(old)["scope_hash"], scope_hash())
        self.assertNotEqual(scope_identity(old)["scope_id"], H7_SCOPE_ID)


class ReceiptContractTests(unittest.TestCase):
    def test_identical_replay_allowed_but_conflicting_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "receipt.json"
            receipt = make_receipt("test", {"scope": scope_identity()})
            self.assertEqual(write_immutable_receipt(receipt, path),
                             receipt["receipt_hash"])
            self.assertEqual(write_immutable_receipt(receipt, path),
                             receipt["receipt_hash"])
            changed = make_receipt("test", {"scope": scope_identity(),
                                             "changed": True})
            with self.assertRaises(FileExistsError):
                write_immutable_receipt(changed, path)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "receipt.json"
            receipt = make_receipt("test", {"value": 1})
            write_immutable_receipt(receipt, path)
            value = json.loads(path.read_text())
            value["value"] = 2
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError):
                load_receipt(path)

    def test_file_hash_changes_are_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.txt"
            path.write_text("one")
            first = input_files({"input": path})
            path.write_text("two")
            second = input_files({"input": path})
            self.assertNotEqual(first, second)


class CacheManifestTests(unittest.TestCase):
    def test_parallel_refresh_writes_resumable_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old_cache = cache_runner.thetadata_adapter.CACHE_DIR
            old_days = cache_runner.trading_days
            cache_runner.thetadata_adapter.CACHE_DIR = root / "chains"
            cache_runner.thetadata_adapter.CACHE_DIR.mkdir()
            cache_runner.trading_days = lambda _start, _end: ["2022-01-03"]
            try:
                def fetch(symbol, day):
                    cache_runner._cache_path(symbol, day).write_text("done")

                manifest = root / "run.json"
                result = cache_runner._run_window(
                    ["2022-01-03"], ["SPY", "QQQ"], fetch, str(root / "ledger"),
                    workers=4, manifest_path=manifest)
                self.assertEqual(result["fetched"], 2)
                state = json.loads(manifest.read_text())
                self.assertEqual(state["status"], "COMPLETE")
                self.assertEqual(set(state["tasks"].values()), {"FETCHED"})
            finally:
                cache_runner.trading_days = old_days
                cache_runner.thetadata_adapter.CACHE_DIR = old_cache


if __name__ == "__main__":
    unittest.main()

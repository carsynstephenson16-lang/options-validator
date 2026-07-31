"""tools/cache_manifest.py: content-addressed manifest of the gitignored
parquet cache, so a reproducer can verify a re-fetched cache byte-for-byte
against the one a ledger record was produced from."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from tools.cache_manifest import build_manifest, verify_manifest, write_manifest


def _write(cache_dir, name, data: bytes):
    path = os.path.join(cache_dir, name)
    with open(path, "wb") as fh:
        fh.write(data)


def _write_v1_partition(cache_dir: str, name: str) -> None:
    pd.DataFrame(
        [
            {
                "expiration": "2024-02-16",
                "strike": 100.0,
                "right": "C",
                "bid": 1.00,
                "ask": 1.05,
                "open_interest": 500,
                "iv": 0.25,
                "delta": 0.30,
                "gamma": 0.02,
                "theta": -0.04,
                "vega": 0.12,
            }
        ]
    ).to_parquet(Path(cache_dir) / name)


class CacheManifestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache = self._tmp.name
        _write_v1_partition(self.cache, "VST_2024-01-02.parquet")
        _write_v1_partition(self.cache, "AMZN_2024-01-02.parquet")

    def tearDown(self):
        self._tmp.cleanup()

    def test_manifest_is_sorted_and_content_addressed(self):
        rows = build_manifest(self.cache)
        self.assertEqual(
            [row.name for row in rows], ["AMZN_2024-01-02.parquet", "VST_2024-01-02.parquet"]
        )
        import hashlib

        vst = Path(self.cache) / "VST_2024-01-02.parquet"
        self.assertEqual(
            rows[1].sha256,
            hashlib.sha256(vst.read_bytes()).hexdigest(),
        )

    def test_roundtrip_verifies_clean(self):
        with tempfile.NamedTemporaryFile("r", suffix=".txt") as out:
            write_manifest(self.cache, out.name)
            self.assertEqual(verify_manifest(self.cache, out.name), [])

    def test_tampered_file_is_reported(self):
        with tempfile.NamedTemporaryFile("r", suffix=".txt") as out:
            write_manifest(self.cache, out.name)
            _write(self.cache, "VST_2024-01-02.parquet", b"tampered")
            problems = verify_manifest(self.cache, out.name)
            self.assertEqual(len(problems), 1)
            self.assertIn("MISMATCH", problems[0])
            self.assertIn("VST_2024-01-02.parquet", problems[0])

    def test_missing_and_extra_files_are_reported(self):
        with tempfile.NamedTemporaryFile("r", suffix=".txt") as out:
            write_manifest(self.cache, out.name)
            os.remove(os.path.join(self.cache, "AMZN_2024-01-02.parquet"))
            _write(self.cache, "CEG_2024-01-02.parquet", b"gamma")
            problems = verify_manifest(self.cache, out.name)
            self.assertTrue(any("MISSING" in p and "AMZN" in p for p in problems))
            self.assertTrue(any("EXTRA" in p and "CEG" in p for p in problems))

    def test_cli_verify_exit_codes(self):
        from tools.cache_manifest import main

        with tempfile.NamedTemporaryFile("r", suffix=".txt") as out:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(["generate", "--cache-dir", self.cache, "--manifest", out.name]), 0
                )
                self.assertEqual(
                    main(["verify", "--cache-dir", self.cache, "--manifest", out.name]), 0
                )
                _write(self.cache, "VST_2024-01-02.parquet", b"tampered")
                self.assertEqual(
                    main(["verify", "--cache-dir", self.cache, "--manifest", out.name]), 1
                )


if __name__ == "__main__":
    unittest.main()

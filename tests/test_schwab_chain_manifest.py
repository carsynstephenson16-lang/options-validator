"""Offline byte-binding tests for Schwab exact-session chain packages."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from research.hashing import sha256_file
from tools import schwab_chain_manifest as manifest

SESSION = "2026-08-10"
SYMBOLS = ["AAA", "BBB"]


def chain_frame(*, expirations: tuple[str, ...] = ("2026-08-21", "2026-09-18")):
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


class SchwabChainManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.chain_dir = self.root / "chains"
        self.report_dir = self.root / "reports" / SESSION
        self.chain_dir.mkdir(parents=True)
        self.report_dir.mkdir(parents=True)
        for symbol in SYMBOLS:
            chain_frame().to_parquet(self.chain_dir / f"{symbol}_{SESSION}.parquet")

    def tearDown(self):
        self.tmp.cleanup()

    def _write_package(
        self,
        *,
        receipt_session: str = SESSION,
        captured_at_et: str = "2026-08-10T15:45:00-04:00",
        force: bool = False,
    ):
        built = manifest.build_manifest(SESSION, SYMBOLS, self.chain_dir)
        manifest_path = manifest.write_manifest(built, self.report_dir / "manifest.json")
        names = {}
        for symbol in SYMBOLS:
            path = self.chain_dir / f"{symbol}_{SESSION}.parquet"
            names[symbol] = {
                "status": "ok",
                "row_count": 4,
                "expiration_count": 2,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        receipt = {
            "receipt_kind": "schwab_chain_capture/v1",
            "session": receipt_session,
            "session_chain_convention": "preclose_snapshot_v1",
            "captured_at_et": captured_at_et,
            "scheduled_session_tag": "preclose",
            "force": force,
            "universe": SYMBOLS,
            "overall_status": "ok",
            "names": names,
            "manifest_hash": built["manifest_hash"],
        }
        receipt_path = self.report_dir / "preclose.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return manifest_path, receipt_path, built

    def test_verifies_exact_session_universe_hashes_and_expirations(self):
        manifest_path, receipt_path, built = self._write_package()

        verified = manifest.verify_session(
            SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
        )

        self.assertEqual(built["schema_version"], "schwab-chain-manifest/v1")
        self.assertEqual(built["session"], SESSION)
        self.assertEqual(built["symbols"], SYMBOLS)
        self.assertEqual(set(built["files"]), set(SYMBOLS))
        self.assertEqual(verified["manifest_hash"], built["manifest_hash"])

    def test_missing_exact_session_file_refuses_without_prior_day_fallback(self):
        manifest_path, receipt_path, _ = self._write_package()
        missing = self.chain_dir / f"AAA_{SESSION}.parquet"
        missing.rename(self.chain_dir / "AAA_2026-08-07.parquet")

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "missing"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_stale_receipt_refuses(self):
        manifest_path, receipt_path, _ = self._write_package(
            receipt_session="2026-08-07"
        )

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "receipt session"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_review_probe_at_0931_with_force_true_refuses(self):
        manifest_path, receipt_path, _ = self._write_package(
            captured_at_et="2026-08-10T09:31:00-04:00",
            force=True,
        )

        with self.assertRaises(manifest.SchwabChainManifestError):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_out_of_preclose_tolerance_receipt_refuses_without_force(self):
        manifest_path, receipt_path, _ = self._write_package(
            captured_at_et="2026-08-10T09:31:00-04:00",
        )

        with self.assertRaisesRegex(
            manifest.SchwabChainManifestError, "preclose tolerance"
        ):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_force_true_receipt_refuses_inside_preclose_tolerance(self):
        manifest_path, receipt_path, _ = self._write_package(force=True)

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "force=false"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_partial_universe_refuses(self):
        manifest_path, receipt_path, _ = self._write_package()
        receipt = json.loads(receipt_path.read_text())
        receipt["universe"] = ["AAA"]
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "universe"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_single_expiration_file_refuses(self):
        chain_frame(expirations=("2026-08-21",)).to_parquet(
            self.chain_dir / f"AAA_{SESSION}.parquet"
        )
        manifest_path, receipt_path, _ = self._write_package()

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "expiration"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )

    def test_tampered_parquet_refuses(self):
        manifest_path, receipt_path, _ = self._write_package()
        path = self.chain_dir / f"AAA_{SESSION}.parquet"
        with path.open("r+b") as stream:
            stream.seek(16)
            original = stream.read(1)
            stream.seek(16)
            stream.write(bytes([original[0] ^ 0x01]))

        with self.assertRaisesRegex(manifest.SchwabChainManifestError, "hash"):
            manifest.verify_session(
                SESSION, SYMBOLS, self.chain_dir, manifest_path, receipt_path
            )


if __name__ == "__main__":
    unittest.main()

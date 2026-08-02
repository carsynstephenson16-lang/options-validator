"""Q9 offline cache-inventory, replay, and flow-readiness tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from research.hashing import sha256_file
from tools import thetadata_exit_audit as audit
from tools.cache_manifest import write_manifest

SESSION = "2022-12-30"


def _chain() -> pd.DataFrame:
    rows = []
    for expiration in ("2023-02-17", "2023-06-16", "2023-12-15"):
        for strike in (90.0, 95.0, 100.0, 105.0, 110.0):
            for right, delta in (("C", 0.60), ("P", -0.25)):
                intrinsic = max(100.0 - strike, 0.0) if right == "C" else max(strike - 100.0, 0.0)
                mid = intrinsic + 2.0
                rows.append(
                    {
                        "expiration": expiration,
                        "strike": strike,
                        "right": right,
                        "bid": mid - 0.05,
                        "ask": mid + 0.05,
                        "open_interest": 500,
                        "iv": 0.40,
                        "delta": delta,
                        "gamma": 0.02,
                        "theta": -0.03,
                        "vega": 0.10,
                    }
                )
    return pd.DataFrame(rows)


class OfflineIntelligenceReadinessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.chains = self.root / "chains"
        self.closes = self.root / "closes"
        self.chains.mkdir()
        self.closes.mkdir()
        self.chain_path = self.chains / f"AMD_{SESSION}.parquet"
        _chain().to_parquet(self.chain_path, index=False)
        pd.DataFrame({"date": [SESSION], "close": [100.0]}).to_parquet(
            self.closes / "AMD.parquet", index=False
        )
        self.manifest = self.root / "manifest.txt"
        write_manifest(str(self.chains), str(self.manifest))
        self.identity = {
            "commit": "test",
            "source_paths": list(audit.READINESS_SOURCE_PATHS),
            "source_hashes": {},
            "missing_source_paths": [],
            "dirty": False,
            "dirty_paths": [],
        }

    def _inventory(self, *, classification_path: Path | None = None) -> dict:
        kwargs = {}
        if classification_path is not None:
            kwargs["classification_path"] = classification_path
        return audit.inventory_cache(
            chain_dir=self.chains,
            manifest_path=self.manifest,
            **kwargs,
        )

    def _classification_registry(self, nested: Path, *, sha256: str | None = None) -> Path:
        path = self.root / "cache-file-classifications.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "cache-file-classifications/v1",
                    "entries": [
                        {
                            "path": nested.relative_to(self.chains).as_posix(),
                            "sha256": sha256 or sha256_file(nested),
                            "size": nested.stat().st_size,
                            "classification": "NONCANONICAL_ALTERNATE_SNAPSHOT",
                            "canonical_path": self.chain_path.name,
                            "reason": "separately sourced reduced-coverage snapshot",
                        }
                    ],
                },
                sort_keys=True,
            )
        )
        return path

    def test_inventory_is_deterministic_and_metadata_only(self):
        first = self._inventory()
        second = self._inventory()

        self.assertEqual(first, second)
        self.assertEqual(first["verdict"], "PASS")
        self.assertEqual(first["scan_mode"], "PARQUET_METADATA_ONLY_NO_VALUE_PAGES")
        self.assertEqual(first["counts"]["parquet_files"], 1)
        self.assertEqual(first["counts"]["rows"], len(_chain()))
        self.assertTrue(all(value == 0 for value in first["null_counts"].values()))

    def test_schema_and_null_missingness_block_without_silent_drop(self):
        changed = _chain().drop(columns=["vega"])
        changed.loc[0, "iv"] = float("nan")
        changed.to_parquet(self.chain_path, index=False)
        write_manifest(str(self.chains), str(self.manifest))

        report = self._inventory()

        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["findings"]["schema_issues"][0]["missing"], ["vega"])
        self.assertEqual(report["findings"]["null_issues"][0]["field"], "iv")

    def test_nested_duplicate_and_unmanifested_input_block(self):
        nested = self.chains / "legacy"
        nested.mkdir()
        duplicate = nested / self.chain_path.name
        _chain().to_parquet(duplicate, index=False)

        report = self._inventory()

        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["findings"]["nested_files"], [f"legacy/{self.chain_path.name}"])
        self.assertEqual(len(report["findings"]["duplicate_symbol_sessions"]), 1)
        self.assertIn(f"legacy/{self.chain_path.name}", report["unmanifested_file_hashes"])

    def test_exact_hash_classification_excludes_known_noncanonical_nested_file(self):
        nested_dir = self.chains / "legacy"
        nested_dir.mkdir()
        duplicate = nested_dir / self.chain_path.name
        _chain().iloc[:4].to_parquet(duplicate, index=False)
        registry = self._classification_registry(duplicate)

        report = self._inventory(classification_path=registry)

        self.assertEqual(report["verdict"], "PASS", report["findings"])
        self.assertEqual(report["counts"]["parquet_files"], 1)
        self.assertEqual(report["counts"]["all_parquet_files"], 2)
        self.assertEqual(report["counts"]["classified_noncanonical_parquet_files"], 1)
        self.assertEqual(report["findings"]["nested_files"], [])
        self.assertEqual(report["findings"]["duplicate_symbol_sessions"], [])
        self.assertNotIn(f"legacy/{self.chain_path.name}", report["unmanifested_file_hashes"])
        self.assertEqual(
            report["classified_noncanonical_files"][0]["path"],
            f"legacy/{self.chain_path.name}",
        )

    def test_changed_classified_nested_file_still_blocks(self):
        nested_dir = self.chains / "legacy"
        nested_dir.mkdir()
        duplicate = nested_dir / self.chain_path.name
        _chain().iloc[:4].to_parquet(duplicate, index=False)
        registry = self._classification_registry(duplicate, sha256="0" * 64)

        report = self._inventory(classification_path=registry)

        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["findings"]["nested_files"], [f"legacy/{self.chain_path.name}"])
        self.assertTrue(report["findings"]["classification_problems"])
        self.assertIn(f"legacy/{self.chain_path.name}", report["unmanifested_file_hashes"])

    def test_manifest_extra_and_malformed_line_both_surface(self):
        extra = self.chains / f"MSFT_{SESSION}.parquet"
        _chain().to_parquet(extra, index=False)
        with self.manifest.open("a") as handle:
            handle.write("malformed manifest line\n")

        report = self._inventory()

        self.assertEqual(report["verdict"], "BLOCK")
        problems = report["findings"]["manifest_problems"]
        self.assertTrue(any(problem.startswith("MANIFEST_LINE") for problem in problems))
        self.assertIn(extra.name, report["unmanifested_file_hashes"])

    def test_invalid_manifest_record_cannot_bind_cache_bytes(self):
        self.manifest.write_text(
            f"{'0' * 63}  {self.chain_path.stat().st_size}  {self.chain_path.name}\n"
        )

        report = self._inventory()

        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["manifest_entry_count"], 0)
        self.assertIn(self.chain_path.name, report["unmanifested_file_hashes"])
        self.assertTrue(
            any("invalid sha256" in problem for problem in report["findings"]["manifest_problems"])
        )

    def test_unmanifested_extra_links_fact_and_attestation_bytes(self):
        extra = self.chains / f"VST_{SESSION}.parquet"
        _chain().to_parquet(extra, index=False)
        digest = sha256_file(extra)
        attestation_dir = self.chains / ".attestations"
        attestation_dir.mkdir()
        attestation = attestation_dir / f"VST_{SESSION}.json"
        attestation.write_text(
            json.dumps(
                {
                    "schema": "blind-cache-attestation/v1",
                    "symbol": "VST",
                    "date": SESSION,
                    "status": "COMPLETE",
                    "sha256": digest,
                }
            )
        )
        facts = {
            ("VST", SESSION): {
                "sha256": digest,
                "fetched": datetime(2022, 12, 31, tzinfo=timezone.utc),
            }
        }

        with mock.patch.object(audit, "fetch_facts", return_value=facts):
            report = self._inventory()

        provenance = report["unmanifested_provenance"][extra.name]
        self.assertEqual(provenance["status"], "FACT_AND_ATTESTATION")
        self.assertTrue(provenance["fact_sha_matches"])
        self.assertTrue(provenance["attestation_matches"])
        self.assertIn(f".attestations/VST_{SESSION}.json", report["sidecar_file_hashes"])
        self.assertEqual(report["findings"]["provenance_mismatches"], [])

    def test_network_disabled_replay_reads_consumers_without_calls_or_writes(self):
        before_hash = sha256_file(self.chain_path)

        replay = audit.run_network_disabled_replay(
            symbol="AMD",
            session=SESSION,
            chain_dir=self.chains,
            close_dir=self.closes,
            manifest_path=self.manifest,
        )

        self.assertEqual(replay["verdict"], "PASS", replay["blocks"])
        self.assertEqual(
            set(item["consumer"] for item in replay["checks"]),
            {
                "cache-only adapter",
                "backtest feed",
                "features",
                "H5",
                "H6",
                "H7",
                "H8",
            },
        )
        self.assertTrue(all(count == 0 for count in replay["sentinel_calls"].values()))
        self.assertEqual(replay["cache_before"], replay["cache_after"])
        self.assertEqual(before_hash, sha256_file(self.chain_path))

    def test_flow_absence_stays_separately_signed_and_data_gated(self):
        report = audit.build_flow_readiness(
            created_at_utc="2026-08-01T12:00:00+00:00",
            flow_dir=self.root / "missing-flow",
            source_identity_record=self.identity,
        )

        self.assertEqual(report["status"], "NOT AUDITED / DATA-GATED")
        self.assertEqual(report["real_empirical_sample_size"], 0)
        self.assertFalse(report["flow_dir_exists"])
        self.assertIsNone(report["empirical_opinion"])
        self.assertTrue(report["receipt_hash"])

    def test_signed_readiness_receipt_recomputes_and_detects_mutation(self):
        report = audit.run_readiness(
            chain_dir=self.chains,
            close_dir=self.closes,
            manifest_path=self.manifest,
            flow_dir=self.root / "missing-flow",
            replay_symbol="AMD",
            replay_session=SESSION,
            created_at_utc="2026-08-01T12:00:00+00:00",
            identity=self.identity,
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertIn("NOT APPENDED", report["ledger_note"])
        path = audit.write_readiness_receipt(report, self.root / "reports")

        ok, failures = audit.verify_readiness_receipt(
            path,
            chain_dir=self.chains,
            close_dir=self.closes,
            manifest_path=self.manifest,
            flow_dir=self.root / "missing-flow",
            identity=self.identity,
        )
        self.assertTrue(ok, failures)

        changed = _chain()
        changed.loc[0, "bid"] += 0.01
        changed.to_parquet(self.chain_path, index=False)
        ok, failures = audit.verify_readiness_receipt(
            path,
            chain_dir=self.chains,
            close_dir=self.closes,
            manifest_path=self.manifest,
            flow_dir=self.root / "missing-flow",
            identity=self.identity,
        )
        self.assertFalse(ok)
        self.assertIn("inventory", failures)


if __name__ == "__main__":
    unittest.main()

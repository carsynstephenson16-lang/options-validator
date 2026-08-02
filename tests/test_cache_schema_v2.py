"""Contract tests for receipt-bound, cache-only schema-v2 reads."""

from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data import thetadata_adapter
from data.cache_schema import CHAIN_V2_CAPTURE_FIELDS


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _v1_chain() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2022-02-18",
                "strike": 390.0,
                "right": "P",
                "bid": 1.00,
                "ask": 1.05,
                "open_interest": 500,
                "iv": 0.25,
                "delta": -0.30,
                "gamma": 0.02,
                "theta": -0.04,
                "vega": 0.12,
            }
        ]
    )


def _v2_chain() -> pd.DataFrame:
    frame = _v1_chain()
    values = {
        "timestamp": pd.Timestamp("2022-01-03 17:15", tz="America/New_York"),
        "bid_size": 17,
        "bid_condition": 50,
        "ask_size": 23,
        "ask_condition": 50,
        "iv_error": 0.001,
        "underlying_timestamp": pd.Timestamp(
            "2022-01-03 16:00", tz="America/New_York"
        ),
        "underlying_price": 477.71,
        "thetadata_client_version": "1.0.9",
    }
    for column in CHAIN_V2_CAPTURE_FIELDS:
        frame[column] = values[column]
    return frame


def _write_audit_receipt(
    cache_dir: Path, chain_path: Path, *, quarantined: bool = False
) -> None:
    repo_root = Path(thetadata_adapter.__file__).resolve().parents[1]
    source_relative = "data/cache_schema.py"
    source_hashes = {source_relative: _sha256_file(repo_root / source_relative)}
    file_hashes = {str(chain_path.resolve()): _sha256_file(chain_path)}
    base = {
        "source_identity": {
            "dirty": False,
            "source_paths": [source_relative],
            "source_hashes": source_hashes,
        },
        "file_hashes": file_hashes,
        "file_hashes_hash": _sha256_text(_canonical_json(file_hashes)),
        "blocks": [],
        "verdict": "PASS WITH WARNINGS",
    }
    base_hashable = {key: value for key, value in base.items() if key != "file_hashes"}
    base["receipt_hash"] = _sha256_text(_canonical_json(base_hashable))
    report = {
        "schema": "thetadata-v2-full-audit/v1",
        "output_namespace": str(cache_dir.resolve()),
        "symbols": ["SPY"],
        "sessions": ["2022-01-03"],
        "base_fourteen_check_audit": base,
        "blocks": [],
        "verdict": "PASS WITH WARNINGS",
        "quarantined_partitions": (
            [{"symbol": "SPY", "session": "2022-01-03"}]
            if quarantined
            else []
        ),
    }
    report["receipt_hash"] = _sha256_text(_canonical_json(report))
    receipt = cache_dir / "_meta" / "full_audit.json"
    receipt.parent.mkdir()
    receipt.write_text(json.dumps(report), encoding="utf-8")


class CacheSchemaV2ContractTests(unittest.TestCase):
    def test_loader_exposes_explicit_verdict_bearing_gate(self):
        self.assertIn(
            "verdict_bearing",
            inspect.signature(thetadata_adapter.load_cached_chain).parameters,
        )

    def test_v1_remains_display_only_for_verdict_reads(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            _v1_chain().to_parquet(cache_dir / "SPY_2022-01-03.parquet")

            displayed = thetadata_adapter.load_cached_chain(
                "SPY", "2022-01-03", cache_dir=cache_dir
            )
            self.assertEqual(len(displayed), 1)

            with self.assertRaisesRegex(ValueError, "display-only"):
                thetadata_adapter.load_cached_chain(
                    "SPY",
                    "2022-01-03",
                    cache_dir=cache_dir,
                    verdict_bearing=True,
                )

    def test_audited_v2_read_is_cache_only_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            chain_path = cache_dir / "SPY_2022-01-03.parquet"
            _v2_chain().to_parquet(chain_path)
            _write_audit_receipt(cache_dir, chain_path)

            with mock.patch.object(
                thetadata_adapter,
                "_client",
                side_effect=AssertionError("network client constructed"),
            ):
                loaded = thetadata_adapter.load_cached_chain(
                    "SPY",
                    "2022-01-03",
                    cache_dir=cache_dir,
                    verdict_bearing=True,
                )
            self.assertEqual(len(loaded), 1)

            changed = pd.read_parquet(chain_path)
            changed.loc[0, "bid"] += 0.01
            changed.to_parquet(chain_path)
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                thetadata_adapter.load_cached_chain(
                    "SPY",
                    "2022-01-03",
                    cache_dir=cache_dir,
                    verdict_bearing=True,
                )

    def test_quarantined_v2_partition_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            chain_path = cache_dir / "SPY_2022-01-03.parquet"
            _v2_chain().to_parquet(chain_path)
            _write_audit_receipt(cache_dir, chain_path, quarantined=True)

            with self.assertRaisesRegex(ValueError, "quarantined"):
                thetadata_adapter.load_cached_chain(
                    "SPY",
                    "2022-01-03",
                    cache_dir=cache_dir,
                    verdict_bearing=True,
                )


if __name__ == "__main__":
    unittest.main()

"""Offline contract tests for versioned ThetaData chain-cache partitions."""

from __future__ import annotations

import tempfile
import unittest
from importlib.metadata import version
from pathlib import Path
from unittest import mock

import pandas as pd

from data import thetadata_adapter
from options_researcher import h7_data_gate, h9_census
from tools.cache_manifest import read_manifest, write_manifest

V2_PROVIDER_FIELDS = [
    "timestamp",
    "bid_size",
    "bid_condition",
    "ask_size",
    "ask_condition",
    "iv_error",
    "underlying_timestamp",
    "underlying_price",
]
V2_CAPTURE_FIELDS = [*V2_PROVIDER_FIELDS, "thetadata_client_version"]


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


def _provider_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    option_timestamp = pd.Timestamp(
        "2022-01-03 17:15:00",
        tz="America/New_York",
    )
    underlying_timestamp = pd.Timestamp(
        "2022-01-03 16:00:00",
        tz="America/New_York",
    )
    greeks = pd.DataFrame(
        [
            {
                "symbol": "SPY",
                "expiration": "2022-02-18",
                "strike": 390.0,
                "right": "PUT",
                "timestamp": option_timestamp,
                "bid_size": 17,
                "bid": 1.00,
                "bid_condition": 50,
                "ask_size": 23,
                "ask": 1.05,
                "ask_condition": 50,
                "delta": -0.30,
                "gamma": 0.02,
                "theta": -0.04,
                "vega": 0.12,
                "implied_vol": 0.25,
                "iv_error": 0.001,
                "underlying_timestamp": underlying_timestamp,
                "underlying_price": 477.71,
            }
        ]
    )
    open_interest = pd.DataFrame(
        [
            {
                "expiration": "2022-02-18",
                "strike": 390.0,
                "right": "PUT",
                "open_interest": 500,
            }
        ]
    )
    return greeks, open_interest


class ChainSchemaV2Tests(unittest.TestCase):
    def test_v2_writer_round_trips_every_new_field(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            old_cache_dir = thetadata_adapter.CACHE_DIR
            thetadata_adapter.CACHE_DIR = cache_dir
            try:
                greeks, open_interest = _provider_frames()
                with (
                    mock.patch.object(
                        thetadata_adapter,
                        "_fetch_raw",
                        return_value=(greeks, open_interest),
                    ),
                    mock.patch.object(
                        thetadata_adapter,
                        "_require_cache_publisher",
                    ),
                    mock.patch.object(
                        thetadata_adapter,
                        "_client",
                        side_effect=AssertionError("network client constructed"),
                    ),
                ):
                    written = thetadata_adapter.get_eod_chain(
                        "SPY",
                        "2022-01-03",
                    )
                stored = pd.read_parquet(thetadata_adapter._cache_path("SPY", "2022-01-03"))
            finally:
                thetadata_adapter.CACHE_DIR = old_cache_dir

        self.assertEqual(
            thetadata_adapter.CHAIN_COLUMNS_V2,
            [*thetadata_adapter.CHAIN_COLUMNS, *V2_CAPTURE_FIELDS],
        )
        self.assertEqual(list(written.columns), thetadata_adapter.CHAIN_COLUMNS_V2)
        self.assertEqual(list(stored.columns), thetadata_adapter.CHAIN_COLUMNS_V2)
        expected = {
            **{field: greeks.iloc[0][field] for field in V2_PROVIDER_FIELDS},
            "thetadata_client_version": version("thetadata"),
        }
        for field, value in expected.items():
            self.assertEqual(stored.iloc[0][field], value, field)

    def test_new_writer_refuses_partial_v2_response_without_creating_partition(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            old_cache_dir = thetadata_adapter.CACHE_DIR
            thetadata_adapter.CACHE_DIR = cache_dir
            try:
                greeks, open_interest = _provider_frames()
                greeks = greeks.drop(columns=["underlying_timestamp"])
                with (
                    mock.patch.object(
                        thetadata_adapter,
                        "_fetch_raw",
                        return_value=(greeks, open_interest),
                    ),
                    mock.patch.object(
                        thetadata_adapter,
                        "_require_cache_publisher",
                    ),
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "underlying_timestamp",
                    ):
                        thetadata_adapter.get_eod_chain(
                            "SPY",
                            "2022-01-03",
                        )
                self.assertFalse(
                    thetadata_adapter._cache_path(
                        "SPY",
                        "2022-01-03",
                    ).exists()
                )
            finally:
                thetadata_adapter.CACHE_DIR = old_cache_dir

    def test_loader_accepts_v1_for_display_but_refuses_it_for_verdicts(self):
        with tempfile.TemporaryDirectory() as temp:
            cache_dir = Path(temp)
            path = cache_dir / "SPY_2022-01-03.parquet"
            _v1_chain().to_parquet(path)

            displayed = thetadata_adapter.load_cached_chain(
                "SPY",
                "2022-01-03",
                cache_dir=cache_dir,
                verdict_bearing=False,
            )
            self.assertEqual(list(displayed.columns), thetadata_adapter.CHAIN_COLUMNS)

            with self.assertRaisesRegex(
                thetadata_adapter.CacheSchemaVersionError,
                r"schema_version=1.*display-only",
            ):
                thetadata_adapter.load_cached_chain(
                    "SPY",
                    "2022-01-03",
                    cache_dir=cache_dir,
                    verdict_bearing=True,
                )

    def test_manifest_records_schema_version_and_v1_display_only_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache_dir = root / "chains"
            cache_dir.mkdir()
            v1_name = "SPY_2022-01-03.parquet"
            v2_name = "SPY_2022-01-04.parquet"
            _v1_chain().to_parquet(cache_dir / v1_name)

            greeks, open_interest = _provider_frames()
            v2_chain = thetadata_adapter._merge_chain_frames(
                greeks,
                open_interest,
            )
            v2_chain.to_parquet(cache_dir / v2_name)

            manifest_path = root / "manifest.txt"
            write_manifest(str(cache_dir), str(manifest_path))
            entries = read_manifest(str(manifest_path))

        self.assertEqual(entries[v1_name].schema_version, 1)
        self.assertEqual(entries[v1_name].usage, "display-only")
        self.assertEqual(entries[v2_name].schema_version, 2)
        self.assertEqual(entries[v2_name].usage, "verdict-eligible")

    def test_legacy_manifest_entry_is_explicitly_display_only(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest_path = Path(temp) / "manifest.txt"
            manifest_path.write_text(
                "# chain-cache-manifest/v2\n"
                "# legacy-entry-defaults schema_version=1 usage=display-only\n"
                f"{'a' * 64}  123  SPY_2022-01-03.parquet\n"
            )
            entries = read_manifest(str(manifest_path))

        entry = entries["SPY_2022-01-03.parquet"]
        self.assertEqual(entry.schema_version, 1)
        self.assertEqual(entry.usage, "display-only")

    def test_h7_verdict_gate_marks_v1_display_only_and_accepts_v2(self):
        with tempfile.TemporaryDirectory() as temp:
            chain_dir = Path(temp)
            v1_path = chain_dir / "SPY_2022-01-03.parquet"
            _v1_chain().to_parquet(v1_path, index=False)

            v1_record, v1_codes = h7_data_gate._evaluate_chain(
                "SPY",
                "2022-01-03",
                chain_dir,
            )

            greeks, open_interest = _provider_frames()
            thetadata_adapter._merge_chain_frames(
                greeks,
                open_interest,
            ).to_parquet(v1_path, index=False)
            v2_record, v2_codes = h7_data_gate._evaluate_chain(
                "SPY",
                "2022-01-03",
                chain_dir,
            )

        self.assertEqual(v1_record["schema_version"], 1)
        self.assertEqual(v1_record["usage"], "display-only")
        self.assertIn("CHAIN_SCHEMA_V1_DISPLAY_ONLY", v1_codes)
        self.assertEqual(v2_record["schema_version"], 2)
        self.assertEqual(v2_record["usage"], "verdict-eligible")
        self.assertNotIn("CHAIN_SCHEMA_V1_DISPLAY_ONLY", v2_codes)

    def test_h9_verdict_loader_explicitly_requires_v2(self):
        with mock.patch.object(
            h9_census,
            "load_cached_chain",
            return_value=_v1_chain(),
        ) as loader:
            h9_census._entry_chain(
                "SPY",
                "2022-01-03",
                Path("/fixture/chains"),
            )

        loader.assert_called_once_with(
            "SPY",
            "2022-01-03",
            allow_oos=True,
            cache_dir=Path("/fixture/chains"),
            verdict_bearing=True,
        )


if __name__ == "__main__":
    unittest.main()

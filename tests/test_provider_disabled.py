"""Fail-closed proof for the retired ThetaData acquisition surface."""

import tempfile
import unittest
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

import config
import smoke_test
from data import cache_runner, provider_policy, recent_topup, thetadata_adapter, underlying_closes
from data.options_flow import adapter as flow_adapter
from options_researcher import intraday_capture, live_quotes
from tools import options_flow


def _cached_chain() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2022-02-18",
                "strike": 390.0,
                "right": "P",
                "bid": 1.0,
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


class ProviderPolicyTests(unittest.TestCase):
    def test_policy_is_disabled_without_an_environment_override(self):
        self.assertTrue(provider_policy.THETADATA_ACQUISITION_DISABLED)
        self.assertNotIn("DATA_PROVIDER", vars(config))

    def test_adapter_refuses_before_key_resolution_or_construction(self):
        with mock.patch.object(thetadata_adapter, "_resolve_api_key") as key:
            with self.assertRaisesRegex(
                provider_policy.ProviderDisabledError,
                "ThetaData acquisition is disabled",
            ):
                thetadata_adapter._client()
        key.assert_not_called()

    def test_cached_chain_read_remains_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(thetadata_adapter, "CACHE_DIR", Path(tmp)):
                _cached_chain().to_parquet(thetadata_adapter._cache_path("SPY", "2022-01-03"))
                result = thetadata_adapter.get_eod_chain("SPY", "2022-01-03")
        self.assertEqual(len(result), 1)

    def test_missing_chain_refuses_before_publisher_or_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.object(thetadata_adapter, "CACHE_DIR", Path(tmp)),
                mock.patch.object(thetadata_adapter, "_require_cache_publisher") as publish,
                mock.patch.object(thetadata_adapter, "_fetch_merged_chain") as fetch,
            ):
                with self.assertRaises(provider_policy.ProviderDisabledError):
                    thetadata_adapter.get_eod_chain("SPY", "2022-01-03")
        publish.assert_not_called()
        fetch.assert_not_called()

    def test_blind_cache_refuses_before_transaction_or_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "chains"
            with (
                mock.patch.object(thetadata_adapter, "CACHE_DIR", cache),
                mock.patch.object(thetadata_adapter, "_cache_publisher_transaction") as tx,
            ):
                with self.assertRaises(provider_policy.ProviderDisabledError):
                    thetadata_adapter.blind_cache_chain("SPY", "2023-01-03")
                self.assertFalse(cache.exists())
        tx.assert_not_called()


class AcquisitionEntrypointTests(unittest.TestCase):
    def test_cache_runners_refuse_before_window_execution(self):
        with mock.patch.object(cache_runner, "_run_window") as run_window:
            with self.assertRaises(provider_policy.ProviderDisabledError):
                cache_runner.cache_in_sample(["SPY"])
            with self.assertRaises(provider_policy.ProviderDisabledError):
                cache_runner.cache_oos_blind(["SPY"])
        run_window.assert_not_called()

    def test_topup_refuses_before_cache_inventory(self):
        with mock.patch.object(recent_topup, "latest_complete_session") as latest:
            with self.assertRaises(provider_policy.ProviderDisabledError):
                recent_topup.run_topup(symbols=["SPY"], today="2026-07-31")
        latest.assert_not_called()

    def test_smoke_refuses_before_read_or_fact_append(self):
        with (
            mock.patch.object(smoke_test, "get_eod_chain") as read,
            mock.patch.object(smoke_test.facts, "append_fact") as append,
        ):
            with self.assertRaises(provider_policy.ProviderDisabledError):
                smoke_test.main()
        read.assert_not_called()
        append.assert_not_called()

    def test_options_flow_execute_refuses_before_output_or_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "flow"
            args = Namespace(
                dry_run=False,
                execute=True,
                symbols=["MSFT"],
                max_symbols=1,
                start_date="2025-01-02",
                end_date="2025-01-02",
                output=output,
            )
            with mock.patch.object(options_flow, "fetch_session") as fetch:
                with self.assertRaises(provider_policy.ProviderDisabledError):
                    options_flow.run(args)
            self.assertFalse(output.exists())
        fetch.assert_not_called()

    def test_flow_default_refuses_before_shared_client(self):
        with mock.patch.object(thetadata_adapter, "_client") as client:
            with self.assertRaises(provider_policy.ProviderDisabledError):
                flow_adapter.default_client()
        client.assert_not_called()

    def test_underlying_thetadata_fetch_refuses_before_shared_client(self):
        with mock.patch.object(thetadata_adapter, "_client") as client:
            with self.assertRaises(provider_policy.ProviderDisabledError):
                underlying_closes.fetch_underlying_eod("SPY", "2022-01-03", "2022-01-04")
        client.assert_not_called()

    def test_live_provider_requires_explicit_schwab_and_refuses_thetadata(self):
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            with self.assertRaisesRegex(RuntimeError, "must be set explicitly"):
                live_quotes._configured_provider()
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {"LIVE_MARKET_DATA_PROVIDER": "thetadata"}, clear=True),
        ):
            with self.assertRaises(provider_policy.ProviderDisabledError):
                live_quotes._configured_provider()
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {"LIVE_MARKET_DATA_PROVIDER": "schwab"}, clear=True),
        ):
            self.assertEqual(live_quotes._configured_provider(), "schwab")

    def test_live_probe_refuses_before_shared_client_construction(self):
        now_ny = datetime(2026, 7, 15, 11, 0, tzinfo=ZoneInfo("America/New_York"))
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {"LIVE_MARKET_DATA_PROVIDER": "thetadata"}, clear=True),
            mock.patch.object(thetadata_adapter, "_client") as client,
        ):
            with self.assertRaises(provider_policy.ProviderDisabledError):
                live_quotes.run_probe(now_ny=now_ny)
        client.assert_not_called()

    def test_intraday_capture_refuses_before_client_or_receipt(self):
        now_ny = datetime(2026, 7, 15, 11, 0, tzinfo=ZoneInfo("America/New_York"))
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {"LIVE_MARKET_DATA_PROVIDER": "thetadata"}, clear=True),
            mock.patch.object(thetadata_adapter, "_client") as client,
            mock.patch.object(intraday_capture, "_write_receipt") as write_receipt,
        ):
            with self.assertRaises(provider_policy.ProviderDisabledError):
                intraday_capture.capture("midmorning", now_ny=now_ny, universe=["MSFT"])
        client.assert_not_called()
        write_receipt.assert_not_called()


if __name__ == "__main__":
    unittest.main()

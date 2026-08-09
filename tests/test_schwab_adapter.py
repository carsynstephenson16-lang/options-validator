"""Offline contract tests for the read-only Schwab market-data facade."""

from __future__ import annotations

import os
import tempfile
import threading
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

from data import schwab_adapter as sa
from data import schwab_credentials as credentials


class FakeResponse:
    def __init__(self, payload, *, status_code=200, headers=None):
        self.payload = payload
        self.status_code = status_code
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeApi:
    def __init__(self):
        self.chain_calls = 0
        self.expiration_calls = 0
        self.market_hours_calls = 0

    def get_quotes(self, symbols):
        return FakeResponse(
            {
                symbol: {
                    "quote": {
                        "bidPrice": 99.9,
                        "askPrice": 100.1,
                        "lastPrice": 100.0,
                        "mark": 100.0,
                        "closePrice": 98.5,
                        "totalVolume": 12_345,
                        "securityStatus": "Normal",
                        "quoteTime": 1_784_112_600_000,
                    },
                    "realtime": True,
                }
                for symbol in symbols
            }
        )

    def get_option_chain(self, symbol, **kwargs):
        self.chain_calls += 1
        return FakeResponse(
            {
                "status": "SUCCESS",
                "isDelayed": False,
                "isChainTruncated": False,
                "numberOfContracts": 2,
                "callExpDateMap": {
                    "2026-08-21:23": {
                        "100.0": [
                            {
                                "symbol": "VST  260821C00100000",
                                "strikePrice": 100.0,
                                "bid": 4.9,
                                "ask": 5.1,
                                "last": 5.0,
                                "mark": 5.0,
                                "totalVolume": 25,
                                "delta": 0.55,
                                "gamma": 0.02,
                                "theta": -0.03,
                                "vega": 0.10,
                                "rho": 0.02,
                                "volatility": 31.5,
                                "openInterest": 450,
                                "intrinsicValue": 0.0,
                                "extrinsicValue": 5.0,
                                "daysToExpiration": 23,
                                "multiplier": 100.0,
                                "nonStandard": False,
                                "mini": False,
                                "quoteTimeInLong": 1_784_112_600_000,
                            }
                        ]
                    }
                },
                "putExpDateMap": {
                    "2026-08-21:23": {
                        "100.0": [
                            {
                                "symbol": "VST  260821P00100000",
                                "strikePrice": 100.0,
                                "bid": 4.7,
                                "ask": 4.9,
                                "last": 4.8,
                                "mark": 4.8,
                                "totalVolume": 30,
                                "delta": -0.45,
                                "gamma": 0.02,
                                "theta": -0.03,
                                "vega": 0.10,
                                "rho": -0.02,
                                "volatility": 32.0,
                                "openInterest": 500,
                                "intrinsicValue": 0.0,
                                "extrinsicValue": 4.8,
                                "daysToExpiration": 23,
                                "multiplier": 100.0,
                                "nonStandard": False,
                                "mini": False,
                                "quoteTimeInLong": 1_784_112_600_000,
                            }
                        ]
                    }
                },
            }
        )

    def get_option_expiration_chain(self, symbol):
        self.expiration_calls += 1
        return FakeResponse(
            {
                "expirationList": [
                    {
                        "expirationDate": "2026-08-21",
                        "daysToExpiration": 23,
                        "expirationType": "M",
                        "settlementType": "P",
                        "standard": True,
                        "optionRoots": "VST",
                    }
                ]
            }
        )

    def get_market_hours(self, markets, **kwargs):
        self.market_hours_calls += 1
        return FakeResponse(
            {
                "equity": {
                    "EQ": {
                        "sessionHours": {
                            "regularMarket": [
                                {
                                    "start": "2026-07-29T09:30:00-04:00",
                                    "end": "2026-07-29T16:00:00-04:00",
                                }
                            ]
                        }
                    }
                },
                "option": {
                    "EQO": {
                        "sessionHours": {
                            "regularMarket": [
                                {
                                    "start": "2026-07-29T09:30:00-04:00",
                                    "end": "2026-07-29T16:00:00-04:00",
                                }
                            ]
                        }
                    }
                },
            }
        )


class FullChainApi(FakeApi):
    def __init__(self):
        super().__init__()
        self.last_chain_kwargs = None

    def get_option_chain(self, symbol, **kwargs):
        self.last_chain_kwargs = dict(kwargs)
        response = super().get_option_chain(symbol, **kwargs)
        payload = response.payload
        payload["numberOfContracts"] = 4
        for map_name, right in (("callExpDateMap", "C"), ("putExpDateMap", "P")):
            original = next(iter(payload[map_name]["2026-08-21:23"].values()))[0]
            second = dict(original)
            second["symbol"] = f"VST  260918{right}00100000"
            second["daysToExpiration"] = 51
            payload[map_name]["2026-09-18:51"] = {"100.0": [second]}
        return FakeResponse(payload)


class SchwabMarketDataTests(unittest.TestCase):
    def test_stock_quotes_are_thetadata_shaped_and_timezone_aware(self):
        client = sa.SchwabMarketData(FakeApi())
        frame = client.stock_snapshot_quote(["vst"])
        self.assertEqual(frame.loc[0, "symbol"], "VST")
        self.assertAlmostEqual(frame.loc[0, "bid"], 99.9)
        self.assertAlmostEqual(frame.loc[0, "previous_close"], 98.5)
        self.assertTrue(frame.loc[0, "realtime"])
        self.assertIsNotNone(pd.Timestamp(frame.loc[0, "timestamp"]).tzinfo)

    def test_chain_normalizes_right_iv_and_reuses_one_vendor_response(self):
        api = FakeApi()
        client = sa.SchwabMarketData(api)
        exp = date(2026, 8, 21)
        greeks = client.option_snapshot_greeks_all("VST", expiration=exp)
        oi = client.option_snapshot_open_interest("VST", expiration=exp)
        quote = client.option_snapshot_quote("VST", expiration=exp)
        self.assertEqual(set(greeks["right"]), {"C", "P"})
        self.assertAlmostEqual(greeks.iloc[0]["implied_vol"], 0.315)
        self.assertEqual(set(oi["open_interest"]), {450, 500})
        self.assertEqual(len(quote), 2)
        self.assertEqual(api.chain_calls, 1)
        self.assertEqual(set(quote["chain_status"]), {"SUCCESS"})
        self.assertFalse(quote["chain_is_delayed"].any())

    def test_full_chain_returns_every_expiration_with_h7_fields(self):
        api = FullChainApi()
        frame = sa.SchwabMarketData(api).option_full_chain("vst")

        self.assertEqual(set(frame["expiration"]), {"2026-08-21", "2026-09-18"})
        self.assertEqual(set(frame["right"]), {"C", "P"})
        self.assertTrue(
            {
                "expiration",
                "strike",
                "right",
                "bid",
                "ask",
                "open_interest",
                "implied_vol",
                "delta",
                "gamma",
                "theta",
                "vega",
            }.issubset(frame.columns)
        )
        self.assertEqual(api.chain_calls, 1)
        self.assertNotIn("from_date", api.last_chain_kwargs)
        self.assertNotIn("to_date", api.last_chain_kwargs)

    def test_chain_cache_expires_before_next_thirty_second_dashboard_refresh(self):
        api = FakeApi()
        ticks = iter([100.0, 110.0, 126.0])
        client = sa.SchwabMarketData(api, clock=lambda: next(ticks))
        exp = date(2026, 8, 21)
        client.option_snapshot_quote("VST", expiration=exp)
        client.option_snapshot_open_interest("VST", expiration=exp)
        client.option_snapshot_quote("VST", expiration=exp)
        self.assertEqual(api.chain_calls, 2)

    def test_expiration_metadata_uses_dedicated_endpoint(self):
        api = FakeApi()
        frame = sa.SchwabMarketData(api).option_list_expirations("vst")
        self.assertEqual(api.expiration_calls, 1)
        self.assertEqual(frame.loc[0, "expiration"], "2026-08-21")
        self.assertTrue(frame.loc[0, "standard"])

    def test_regular_session_requires_equity_and_options_windows_open(self):
        api = FakeApi()
        client = sa.SchwabMarketData(api)
        now_ny = datetime(
            2026, 7, 29, 10, 30, tzinfo=ZoneInfo("America/New_York")
        )
        state = client.regular_session_state(now_ny)
        self.assertTrue(state["open"])
        self.assertTrue(state["equity_regular_open"])
        self.assertTrue(state["option_regular_open"])
        self.assertEqual(api.market_hours_calls, 1)
        client.regular_session_state(now_ny)
        self.assertEqual(api.market_hours_calls, 1)

    def test_facade_exposes_no_account_or_order_methods(self):
        client = sa.SchwabMarketData(FakeApi())
        for name in ("get_account", "get_orders", "place_order", "cancel_order"):
            self.assertFalse(hasattr(client, name), name)
        wrapper = credentials.LockedReadOnlySchwabClient(
            "client-id", "secret", Path("/private/tmp/unused-token.json")
        )
        for name in ("get_account", "get_orders", "place_order", "cancel_order"):
            self.assertFalse(hasattr(wrapper, name), name)


class ConfigSafetyTests(unittest.TestCase):
    def _env(self, token_path: Path) -> dict[str, str]:
        return {
            "SCHWAB_API_KEY": "client-id",
            "SCHWAB_CALLBACK_URL": sa.EXPECTED_CALLBACK_URL,
            "SCHWAB_TOKEN_PATH": str(token_path),
            "SCHWAB_TRADING_ENABLED": "false",
            "SCHWAB_ENTITLEMENT": "NP",
        }

    def test_trading_flag_fails_closed(self):
        env = self._env(sa.DEFAULT_TOKEN_PATH)
        env["SCHWAB_TRADING_ENABLED"] = "true"
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "must remain false"):
                sa.load_config(require_token=False)

    def test_token_must_stay_in_private_support_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = self._env(Path(tmp) / "token.json")
            with mock.patch.dict(os.environ, env, clear=True):
                with self.assertRaisesRegex(RuntimeError, "private Schwab"):
                    sa.load_config(require_token=False)

    def test_plaintext_secret_is_refused(self):
        with mock.patch.dict(os.environ, {"SCHWAB_APP_SECRET": "must-not-live-here"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Plaintext"):
                credentials.load_client_secret()

    def test_keychain_lookup_does_not_put_secret_in_command(self):
        result = mock.Mock(returncode=0, stdout="secret-from-keychain\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch.object(credentials.subprocess, "run", return_value=result) as run:
                self.assertEqual(credentials.load_client_secret(), "secret-from-keychain")
        command = run.call_args.args[0]
        self.assertNotIn("secret-from-keychain", command)
        self.assertEqual(command[-1], "-w")

    def test_token_writer_is_atomic_and_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.json"
            token = {"creation_timestamp": 1, "token": {"access_token": "redacted"}}
            credentials._atomic_write_token(path, token)
            self.assertEqual(credentials._read_token(path), token)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_token_lock_serializes_concurrent_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.json"
            first_entered = threading.Event()
            release_first = threading.Event()
            second_entered = threading.Event()

            def hold_first():
                with credentials._token_lock(path):
                    first_entered.set()
                    release_first.wait(timeout=2)

            def enter_second():
                with credentials._token_lock(path):
                    second_entered.set()

            first = threading.Thread(target=hold_first)
            second = threading.Thread(target=enter_second)
            first.start()
            self.assertTrue(first_entered.wait(timeout=1))
            second.start()
            self.assertFalse(second_entered.wait(timeout=0.05))
            release_first.set()
            first.join(timeout=2)
            second.join(timeout=2)
            self.assertTrue(second_entered.is_set())
            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())

    def test_read_only_wrapper_retries_bounded_transient_responses(self):
        wrapper = credentials.LockedReadOnlySchwabClient(
            "client-id", "secret", Path("/private/tmp/unused-token.json")
        )
        api = mock.Mock()
        api.get_quote.side_effect = [
            FakeResponse({}, status_code=503),
            FakeResponse({"VST": {}}, status_code=200),
        ]
        context = mock.MagicMock()
        context.__enter__.return_value = api
        with mock.patch.object(wrapper, "_client", return_value=context):
            with mock.patch.object(credentials.time, "sleep") as sleep:
                with mock.patch.object(credentials.random, "uniform", return_value=0):
                    response = wrapper.get_quote("VST")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(api.get_quote.call_count, 2)
        sleep.assert_called_once_with(credentials.SCHWAB_BACKOFF_BASE_SECONDS)

    def test_long_retry_after_fails_fast_for_caller_to_label(self):
        wrapper = credentials.LockedReadOnlySchwabClient(
            "client-id", "secret", Path("/private/tmp/unused-token.json")
        )
        api = mock.Mock()
        api.get_quote.return_value = FakeResponse(
            {}, status_code=429, headers={"retry-after": "60"}
        )
        context = mock.MagicMock()
        context.__enter__.return_value = api
        with mock.patch.object(wrapper, "_client", return_value=context):
            with mock.patch.object(credentials.time, "sleep") as sleep:
                response = wrapper.get_quote("VST")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(api.get_quote.call_count, 1)
        sleep.assert_not_called()

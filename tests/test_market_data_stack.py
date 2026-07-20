from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from market_data.models import (
    DataTiming,
    OptionQuote,
    ValidationStatus,
    compute_midpoint,
    normalize_option_symbol,
    parse_option_symbol,
)
from market_data.providers.alpha_vantage import AlphaVantageProvider
from market_data.providers.massive import MassiveProvider
from market_data.providers.schwab import FileTokenStore, SchwabReadOnlyProvider
from market_data.transport import (
    DiskResponseCache,
    ProviderError,
    RateLimiter,
    RetryingJsonTransport,
)
from market_data.validation import validate_chain, validate_quote


class FakeTransport:
    def __init__(self, payloads: dict[str, object]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_json(self, url, *, params=None, headers=None, cache_namespace=None):
        request_params = dict(params or {})
        self.calls.append((url, request_params))
        for key, payload in self.payloads.items():
            if key in url or request_params.get("function") == key:
                return payload
        raise AssertionError(f"unexpected fake request: {url} {request_params}")


class MarketDataStackTests(unittest.TestCase):
    def test_option_symbol_round_trip(self):
        symbol = normalize_option_symbol("aapl", date(2024, 1, 19), "c", 150)
        self.assertEqual(symbol, "O:AAPL240119C00150000")
        contract = parse_option_symbol(symbol)
        self.assertEqual(contract.underlying_symbol, "AAPL")
        self.assertEqual(contract.option_type, "call")
        self.assertEqual(contract.strike, 150.0)

    def test_midpoint_never_fabricates_missing_premium_as_zero(self):
        self.assertIsNone(compute_midpoint(None, None))
        self.assertIsNone(compute_midpoint(-1, 2))
        self.assertEqual(compute_midpoint(0, 2), 1.0)

    def test_rate_limiter_waits_for_window(self):
        now = [0.0]
        sleeps: list[float] = []

        def clock() -> float:
            return now[0]

        def sleep(seconds: float) -> None:
            sleeps.append(seconds)
            now[0] += seconds

        limiter = RateLimiter(1, 10, clock=clock, sleep=sleep)
        limiter.acquire()
        limiter.acquire()
        self.assertEqual(sleeps, [10.0])

    def test_cache_excludes_api_key_from_raw_cache_file(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = DiskResponseCache(directory)
            cache.write(
                "https://example.test/query",
                {"apikey": "SECRET", "symbol": "AAPL"},
                "test",
                {"value": 1},
            )
            files = list(Path(directory).glob("*.json"))
            self.assertEqual(len(files), 1)
            self.assertNotIn("SECRET", files[0].read_text(encoding="utf-8"))
            self.assertEqual(
                cache.read("https://example.test/query", {"apikey": "OTHER", "symbol": "AAPL"}, "test").payload,
                {"value": 1},
            )

    def test_retry_transport_retries_transport_errors(self):
        class Flaky:
            def __init__(self):
                self.calls = 0

            def get_json(self, *args, **kwargs):
                self.calls += 1
                if self.calls < 3:
                    raise ProviderError("temporary")
                return {"ok": True}

        sleeps: list[float] = []
        flaky = Flaky()
        retrying = RetryingJsonTransport(flaky, attempts=3, sleep=sleeps.append)
        self.assertEqual(retrying.get_json("https://example.test"), {"ok": True})
        self.assertEqual(flaky.calls, 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_massive_contract_reference_normalizes_missing_fields(self):
        fake = FakeTransport(
            {
                "contracts": {
                    "results": [
                        {
                            "ticker": "O:AAPL240119C00150000",
                            "underlying_ticker": "AAPL",
                            "contract_type": "call",
                            "strike_price": 150,
                            "expiration_date": "2024-01-19",
                        }
                    ]
                }
            }
        )
        quote = MassiveProvider(api_key="secret", transport=fake).get_option_chain("AAPL")[0]
        self.assertEqual(quote.symbol, "O:AAPL240119C00150000")
        self.assertIsNone(quote.midpoint)
        self.assertIn("quote", quote.missing_field_reasons)
        self.assertEqual(quote.timing, DataTiming.DELAYED)
        self.assertEqual(fake.calls[0][1]["apiKey"], "secret")

    def test_alpha_vantage_does_not_request_free_premium_options(self):
        provider = AlphaVantageProvider(api_key="secret", transport=FakeTransport({}))
        with self.assertRaisesRegex(Exception, "premium-only"):
            provider.get_option_chain("AAPL")

    def test_alpha_vantage_compact_daily_response_has_source_label(self):
        fake = FakeTransport({"TIME_SERIES_DAILY": {"Time Series (Daily)": {}}})
        response = AlphaVantageProvider(api_key="secret", transport=fake).get_daily_prices("AAPL")
        self.assertEqual(response.provider, "alpha_vantage")
        self.assertEqual(response.endpoint, "TIME_SERIES_DAILY")
        self.assertEqual(fake.calls[0][1]["apikey"], "secret")
        self.assertEqual(fake.calls[0][1]["outputsize"], "compact")

    def test_validation_reports_missing_fields_as_unavailable(self):
        quote = OptionQuote(
            provider="massive",
            symbol="O:AAPL240119C00150000",
            underlying_symbol="AAPL",
            option_type="call",
            strike=150,
            expiration=date(2024, 1, 19),
            bid=None,
            ask=None,
            last_price=1.0,
            quote_timestamp=datetime(2024, 1, 10, tzinfo=timezone.utc),
            timing=DataTiming.DELAYED,
        )
        results = validate_quote(quote, as_of=date(2024, 1, 10), now=datetime(2024, 1, 10, tzinfo=timezone.utc))
        by_rule = {result.rule_name: result for result in results}
        self.assertEqual(by_rule["zero_or_missing_spread"].status, ValidationStatus.UNAVAILABLE)
        self.assertEqual(by_rule["missing_open_interest"].status, ValidationStatus.UNAVAILABLE)
        self.assertNotIn("zero", by_rule["zero_or_missing_spread"].explanation.lower())

    def test_validation_detects_stale_quote_and_provider_disagreement(self):
        old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        first = OptionQuote(
            provider="massive", symbol="O:AAPL240119C00150000", underlying_symbol="AAPL",
            option_type="call", strike=150, expiration=date(2024, 1, 19), bid=1, ask=1.2,
            midpoint=1.1, last_price=1.1, quote_timestamp=old,
        )
        second = OptionQuote(
            provider="schwab", symbol="O:AAPL240119C00150000", underlying_symbol="AAPL",
            option_type="call", strike=150, expiration=date(2024, 1, 19), bid=2, ask=2.2,
            midpoint=2.1, last_price=2.1, quote_timestamp=old + timedelta(seconds=10),
        )
        results = validate_chain(
            [first, second], now=datetime(2024, 1, 2, tzinfo=timezone.utc), max_stale_seconds=60
        )
        rules = {result.rule_name: result for result in results}
        self.assertEqual(rules["stale_quote"].status, ValidationStatus.FAIL)
        self.assertTrue(any(result.rule_name == "large_provider_price_difference" and result.status == ValidationStatus.FAIL for result in results))
        self.assertTrue(any(result.rule_name == "duplicate_contract" for result in results))

    def test_schwab_token_path_is_project_scoped_and_provider_has_no_order_method(self):
        with tempfile.TemporaryDirectory() as directory:
            store = FileTokenStore(project_root=directory)
            self.assertTrue(store.path.is_relative_to(Path(directory).resolve()))
            with self.assertRaises(ValueError):
                FileTokenStore(project_root=directory, relative_path="../outside.json")
        provider = SchwabReadOnlyProvider(
            app_key="app", app_secret="secret", callback_url="https://localhost/callback"
        )
        self.assertFalse(hasattr(provider, "place_order"))
        self.assertFalse(hasattr(provider, "cancel_order"))
        self.assertIn("client_id=app", provider.authorization_url("state-1"))


if __name__ == "__main__":
    unittest.main()

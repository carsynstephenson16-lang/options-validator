"""Tests for provider-dispatched EOD chain fetching (DoltHub / Alpha Vantage).

All tests are offline: HTTP is injected, never called. The seams are the
public mapping/fetch functions and get_eod_chain's dispatch+cache behavior.
"""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import config
from data import thetadata_adapter
from data.thetadata_adapter import CHAIN_COLUMNS, validate_chain_schema


def dolthub_rows():
    """Shape observed live from the DoltHub SQL API on 2026-07-01 (post-no-preference/options):
    strings for numerics, call_put in {'Call','Put'}, 'vol' is the IV column,
    and NO open interest / volume columns exist in option_chain."""
    return [
        {"date": "2022-06-15", "act_symbol": "SPY", "expiration": "2022-07-13",
         "strike": "355.00", "call_put": "Put", "bid": "6.10", "ask": "6.31",
         "vol": "0.2734", "delta": "-0.3001", "gamma": "0.0072",
         "theta": "-0.3873", "vega": "0.3357", "rho": "-0.0891"},
        {"date": "2022-06-15", "act_symbol": "SPY", "expiration": "2022-07-13",
         "strike": "350.00", "call_put": "Call", "bid": "31.10", "ask": "31.90",
         "vol": "0.3106", "delta": "0.7810", "gamma": "0.0054",
         "theta": "-0.4211", "vega": "0.2903", "rho": "0.1201"},
    ]


class TestDolthubMapping(unittest.TestCase):
    def test_maps_rows_to_chain_schema(self):
        from data.dolthub import chain_from_rows
        chain = chain_from_rows(dolthub_rows())
        self.assertEqual(list(chain.columns), CHAIN_COLUMNS)
        self.assertEqual(len(chain), 2)
        # right normalized to P/C
        self.assertEqual(set(chain["right"]), {"P", "C"})
        # numerics coerced from API strings
        self.assertAlmostEqual(float(chain.iloc[0]["bid"]), 6.10)
        self.assertAlmostEqual(float(chain.iloc[0]["iv"]), 0.2734)
        # DoltHub has no open interest: fail-closed 0.0 so the liquidity
        # filter refuses these chains rather than fabricating liquidity.
        self.assertTrue((chain["open_interest"] == 0.0).all())
        validate_chain_schema(chain)  # must not raise

    def test_drops_rows_with_missing_numerics_rather_than_failing_validation(self):
        from data.dolthub import chain_from_rows
        rows = dolthub_rows()
        rows.append({**rows[0], "strike": "360.00", "delta": None})
        chain = chain_from_rows(rows)
        self.assertEqual(len(chain), 2)
        validate_chain_schema(chain)

    def test_empty_rows_raise(self):
        from data.dolthub import chain_from_rows
        with self.assertRaises(ValueError):
            chain_from_rows([])


def av_payload():
    """Shape observed live from HISTORICAL_OPTIONS with the demo key on
    2026-07-01: numerics as strings, type in {'call','put'}, IV/greeks columns.
    Second contract carries the junk-greeks pattern seen live (deep-ITM
    IV=4.2): bid/ask are fine but computed greeks are garbage."""
    good = {"contractID": "SPY220713P00355000", "symbol": "SPY",
            "expiration": "2022-07-13", "strike": "355.00", "type": "put",
            "last": "6.20", "mark": "6.21", "bid": "6.10", "bid_size": "12",
            "ask": "6.31", "ask_size": "9", "volume": "1200",
            "open_interest": "5321", "date": "2022-06-15",
            "implied_volatility": "0.27340", "delta": "-0.30010",
            "gamma": "0.00720", "theta": "-0.38730", "vega": "0.33570",
            "rho": "-0.08910"}
    junk = dict(good, contractID="SPY220713C00075000", type="call",
                strike="75.00", implied_volatility="4.20990", delta="0.98977")
    return {"endpoint": "Historical Options", "message": "success",
            "data": [good, junk]}


class TestAlphaVantageMapping(unittest.TestCase):
    def test_maps_payload_and_drops_junk_greek_rows(self):
        from data.alphavantage import chain_from_payload
        chain = chain_from_payload(av_payload())
        self.assertEqual(list(chain.columns), CHAIN_COLUMNS)
        self.assertEqual(len(chain), 1)  # junk-IV row dropped
        row = chain.iloc[0]
        self.assertEqual(row["right"], "P")
        self.assertAlmostEqual(float(row["open_interest"]), 5321.0)
        self.assertAlmostEqual(float(row["iv"]), 0.2734)
        validate_chain_schema(chain)

    def test_information_payload_raises_instead_of_returning_empty(self):
        from data.alphavantage import chain_from_payload
        gated = {"Information": "Thank you for using Alpha Vantage! This is a "
                                "premium endpoint."}
        with self.assertRaises(RuntimeError):
            chain_from_payload(gated)

    def test_empty_data_raises(self):
        from data.alphavantage import chain_from_payload
        with self.assertRaises(ValueError):
            chain_from_payload({"message": "success", "data": []})


class TestGetEodChainDispatch(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_cache = thetadata_adapter.CACHE_DIR
        self._orig_provider = config.DATA_PROVIDER
        thetadata_adapter.CACHE_DIR = Path(self._tmp.name)

    def tearDown(self):
        thetadata_adapter.CACHE_DIR = self._orig_cache
        config.DATA_PROVIDER = self._orig_provider
        self._tmp.cleanup()

    def test_cache_path_is_provider_scoped(self):
        config.DATA_PROVIDER = "dolthub"
        p1 = thetadata_adapter._cache_path("SPY", "2022-06-15")
        config.DATA_PROVIDER = "alphavantage"
        p2 = thetadata_adapter._cache_path("SPY", "2022-06-15")
        self.assertNotEqual(p1, p2)
        self.assertIn("dolthub", p1.parts)
        self.assertIn("alphavantage", p2.parts)

    def test_dispatch_fetches_validates_caches_then_reads_cache(self):
        from data import dolthub
        config.DATA_PROVIDER = "dolthub"
        calls = []

        def fake_fetch(symbol, date):
            calls.append((symbol, date))
            return dolthub.chain_from_rows(dolthub_rows())

        orig = thetadata_adapter._FETCHERS.get("dolthub")
        thetadata_adapter._FETCHERS["dolthub"] = fake_fetch
        try:
            first = thetadata_adapter.get_eod_chain("SPY", "2022-06-15")
            second = thetadata_adapter.get_eod_chain("SPY", "2022-06-15")
        finally:
            thetadata_adapter._FETCHERS["dolthub"] = orig
        self.assertEqual(calls, [("SPY", "2022-06-15")])  # second hit the cache
        pd.testing.assert_frame_equal(first, second)
        self.assertTrue(
            (Path(self._tmp.name) / "dolthub" / "SPY_2022-06-15.parquet").exists())

    def test_thetadata_provider_still_raises_not_implemented(self):
        config.DATA_PROVIDER = "thetadata"
        with self.assertRaises(NotImplementedError):
            thetadata_adapter.get_eod_chain("SPY", "2022-06-15")

    def test_unknown_provider_fails_loud(self):
        config.DATA_PROVIDER = "yahoo"
        with self.assertRaises(ValueError):
            thetadata_adapter.get_eod_chain("SPY", "2022-06-15")


class TestCrossCheck(unittest.TestCase):
    def _chain(self, bid=6.10):
        from data.dolthub import chain_from_rows
        rows = dolthub_rows()
        rows[0] = dict(rows[0], bid=str(bid))
        return chain_from_rows(rows)

    def test_identical_chains_report_zero_diff(self):
        from analysis.cross_check_quotes import compare_chains
        stats = compare_chains(self._chain(), self._chain())
        self.assertEqual(stats["n_matched"], 2)
        self.assertEqual(stats["max_abs_bid_diff"], 0.0)
        self.assertEqual(stats["max_abs_ask_diff"], 0.0)

    def test_bid_discrepancy_is_detected(self):
        from analysis.cross_check_quotes import compare_chains
        stats = compare_chains(self._chain(bid=6.10), self._chain(bid=6.60))
        self.assertEqual(stats["n_matched"], 2)
        self.assertAlmostEqual(stats["max_abs_bid_diff"], 0.50)


if __name__ == "__main__":
    unittest.main()

"""tests/test_pandas_feed.py -- cache chains -> per-contract Lumibot Data.

The feed is the offline data path proven by the 2026-07-03 spike: one Data
object per option contract, quote columns pre-widened by the frozen haircut
with ADVERSE penny rounding (engine fills can never be better than the frozen
conservative model), close = raw mid (mark-to-market only, never a fill),
bars stamped 16:00 America/New_York.

All fixtures are synthetic; the suite must run offline and without .cache/.
"""
import math
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

import config
from data import pandas_feed, thetadata_adapter


def synth_chain(rows):
    """Minimal valid CHAIN_COLUMNS frame from (exp, strike, right, bid, ask,
    oi, delta) tuples."""
    return pd.DataFrame(
        [
            {
                "expiration": e, "strike": float(k), "right": r,
                "bid": float(b), "ask": float(a), "open_interest": int(oi),
                "iv": 0.25, "delta": float(d), "gamma": 0.01,
                "theta": -0.05, "vega": 0.1,
            }
            for (e, k, r, b, a, oi, d) in rows
        ]
    )


class OptionAssetKeyTests(unittest.TestCase):
    def test_option_asset_builds_canonical_put_key(self):
        a = pandas_feed.option_asset("spy", "2022-07-01", 395)
        self.assertEqual(a.symbol, "SPY")
        self.assertEqual(a.asset_type, "option")
        self.assertEqual(a.expiration, date(2022, 7, 1))
        self.assertEqual(a.strike, 395.0)
        self.assertEqual(str(a.right), "PUT")

    def test_same_contract_hashes_equal(self):
        a = pandas_feed.option_asset("SPY", "2022-07-01", 395.0)
        b = pandas_feed.option_asset("SPY", "2022-07-01", 395)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)


class BuildOptionDataTests(unittest.TestCase):
    def chains(self):
        # two days, one liquid put tracked across both
        return {
            "2022-06-01": synth_chain([
                ("2022-07-01", 395.0, "P", 1.23, 1.31, 500, -0.30),
                ("2022-07-01", 393.0, "P", 1.00, 1.08, 400, -0.26),
            ]),
            "2022-06-02": synth_chain([
                ("2022-07-01", 395.0, "P", 1.40, 1.50, 500, -0.32),
                ("2022-07-01", 393.0, "P", 1.10, 1.18, 400, -0.28),
            ]),
        }

    def test_one_data_per_contract_with_ny_1600_stamps(self):
        feed = pandas_feed.build_option_data(
            self.chains(), "SPY", exp_max="2022-09-16")
        self.assertEqual(len(feed), 2)
        key = pandas_feed.option_asset("SPY", "2022-07-01", 395.0)
        data = feed[key]
        idx = data.df.index
        self.assertEqual(len(idx), 2)
        self.assertEqual(str(idx[0].tz), "America/New_York")
        self.assertEqual((idx.hour == 16).all(), True)

    def test_quotes_widened_with_adverse_penny_rounding(self):
        feed = pandas_feed.build_option_data(
            self.chains(), "SPY", exp_max="2022-09-16")
        key = pandas_feed.option_asset("SPY", "2022-07-01", 395.0)
        row = feed[key].df.iloc[0]
        h = config.SLIPPAGE_HAIRCUT
        # bid: widened DOWN then floored to the cent (1.23*0.99=1.2177 -> 1.21)
        self.assertAlmostEqual(row["bid"], math.floor(1.23 * (1 - h) * 100) / 100)
        # ask: widened UP then ceiled to the cent (1.31*1.01=1.3231 -> 1.33)
        self.assertAlmostEqual(row["ask"], math.ceil(1.31 * (1 + h) * 100) / 100)
        # close = RAW mid, not widened (mark-to-market only)
        self.assertAlmostEqual(row["close"], (1.23 + 1.31) / 2)

    def test_calls_and_far_expirations_excluded(self):
        chains = {
            "2022-06-01": synth_chain([
                ("2022-07-01", 395.0, "C", 1.0, 1.1, 500, 0.30),   # call
                ("2022-12-16", 395.0, "P", 1.0, 1.1, 500, -0.30),  # beyond reach
                ("2022-07-01", 395.0, "P", 1.0, 1.1, 500, -0.30),
            ]),
        }
        feed = pandas_feed.build_option_data(chains, "SPY", exp_max="2022-09-16")
        self.assertEqual(
            list(feed), [pandas_feed.option_asset("SPY", "2022-07-01", 395.0)])

    def test_delta_band_keeps_full_series_once_included(self):
        # in band on day 2 only -> whole series (both days) must be present,
        # otherwise lumibot forward-fills a gap with stale quotes
        chains = {
            "2022-06-01": synth_chain([
                ("2022-07-01", 300.0, "P", 0.01, 0.03, 500, -0.001),
            ]),
            "2022-06-02": synth_chain([
                ("2022-07-01", 300.0, "P", 0.50, 0.60, 500, -0.10),
            ]),
        }
        feed = pandas_feed.build_option_data(chains, "SPY", exp_max="2022-09-16")
        key = pandas_feed.option_asset("SPY", "2022-07-01", 300.0)
        self.assertIn(key, feed)
        self.assertEqual(len(feed[key].df), 2)

    def test_never_in_band_contract_excluded(self):
        chains = {
            "2022-06-01": synth_chain([
                ("2022-07-01", 100.0, "P", 0.0, 0.02, 10, -0.0005),
            ]),
        }
        feed = pandas_feed.build_option_data(chains, "SPY", exp_max="2022-09-16")
        self.assertEqual(len(feed), 0)


class LoadCachedChainsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old_cache = thetadata_adapter.CACHE_DIR
        thetadata_adapter.CACHE_DIR = Path(self._tmp.name)
        self._old_fetch = thetadata_adapter._fetch_merged_chain

        def _poisoned(*a, **k):
            raise AssertionError("offline test tried a live fetch")
        thetadata_adapter._fetch_merged_chain = _poisoned

    def tearDown(self):
        thetadata_adapter.CACHE_DIR = self._old_cache
        thetadata_adapter._fetch_merged_chain = self._old_fetch
        self._tmp.cleanup()

    def _write(self, symbol, day, chain):
        chain.to_parquet(Path(self._tmp.name) / f"{symbol}_{day}.parquet")

    def test_loads_only_days_present_in_cache(self):
        chain = synth_chain([("2022-07-01", 395.0, "P", 1.0, 1.1, 500, -0.30)])
        self._write("SPY", "2022-06-01", chain)   # Wed
        self._write("SPY", "2022-06-03", chain)   # Fri; Thu missing = non-trading
        out = pandas_feed.load_cached_chains("SPY", "2022-06-01", "2022-06-05")
        self.assertEqual(sorted(out), ["2022-06-01", "2022-06-03"])

    def test_post_boundary_date_refused_without_allow_oos(self):
        chain = synth_chain([("2023-02-17", 395.0, "P", 1.0, 1.1, 500, -0.30)])
        self._write("SPY", "2023-01-03", chain)
        with self.assertRaises(thetadata_adapter.OOSDataTouchError):
            pandas_feed.load_cached_chains("SPY", "2023-01-02", "2023-01-04")


if __name__ == "__main__":
    unittest.main()

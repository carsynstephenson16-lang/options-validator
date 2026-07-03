"""Blind-cache mode (pre-registration decision doc, section 4): post-
IN_SAMPLE_END chains may be fetched and written to parquet during the paid
month, but their VALUES must never surface before the OOS reveal. Only safe
metadata escapes (symbol, date, row count, schema names, file hash), every
invocation appends an auditable facts event, and reading the cached values
stays gated by the existing OOS reveal path."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import config
from data import thetadata_adapter
from research import facts

OOS_DATE = "2023-06-01"       # inside the extended OOS window
IN_SAMPLE_DATE = "2022-06-01"


def _frames(n=3):
    base = {
        "expiration": ["2023-07-21"] * n,
        "strike": [380.0 + 5 * i for i in range(n)],
        "right": ["PUT"] * n,
    }
    greeks = pd.DataFrame({**base,
                           "bid": [1.00 + i for i in range(n)],
                           "ask": [1.10 + i for i in range(n)],
                           "delta": [-0.30] * n, "gamma": [0.02] * n,
                           "theta": [-0.04] * n, "vega": [0.12] * n,
                           "implied_vol": [0.25] * n})
    oi = pd.DataFrame({**base, "open_interest": [500] * n})
    return greeks, oi


class BlindCacheTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._old_cache = thetadata_adapter.CACHE_DIR
        thetadata_adapter.CACHE_DIR = tmp / "chains"
        thetadata_adapter.CACHE_DIR.mkdir(parents=True)
        self.ledger_dir = str(tmp / "ledger")

        self._old_fetch_raw = thetadata_adapter._fetch_raw
        self._old_client = thetadata_adapter._client
        self.fetch_calls = []

        def fake_fetch_raw(symbol, date):
            self.fetch_calls.append((symbol, date))
            return _frames()

        thetadata_adapter._fetch_raw = fake_fetch_raw

        def _client_forbidden():
            raise AssertionError("no test should construct a real ThetaClient")

        thetadata_adapter._client = _client_forbidden

    def tearDown(self):
        thetadata_adapter._fetch_raw = self._old_fetch_raw
        thetadata_adapter._client = self._old_client
        thetadata_adapter.CACHE_DIR = self._old_cache
        self._tmp.cleanup()

    def _forbid_network(self):
        def raiser(*args, **kwargs):
            raise AssertionError("network fetch must not happen here")
        thetadata_adapter._fetch_raw = raiser
        thetadata_adapter._client = raiser

    def test_refuses_in_sample_dates(self):
        with self.assertRaises(ValueError):
            thetadata_adapter.blind_cache_chain(
                "SPY", IN_SAMPLE_DATE, ledger_dir=self.ledger_dir)
        self.assertFalse(
            thetadata_adapter._cache_path("SPY", IN_SAMPLE_DATE).exists())
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_writes_parquet_and_returns_only_safe_metadata(self):
        meta = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        self.assertEqual(set(meta), set(thetadata_adapter.BLIND_CACHE_METADATA_KEYS))
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        self.assertTrue(path.exists())
        self.assertEqual(meta["symbol"], "SPY")
        self.assertEqual(meta["date"], OOS_DATE)
        self.assertEqual(meta["rows"], 3)
        self.assertEqual(meta["columns"], thetadata_adapter.CHAIN_COLUMNS)
        self.assertEqual(meta["sha256"],
                         hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertFalse(meta["already_cached"])
        # nothing frame-like or price-like may escape: scalar/list types only
        for value in meta.values():
            self.assertNotIsInstance(value, (pd.DataFrame, pd.Series))

    def test_every_invocation_appends_an_auditable_fact(self):
        meta = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        lines = facts.read_facts(self.ledger_dir)
        self.assertEqual(len(lines), 1)
        for token in ("BLIND_CACHE", "symbol=SPY", f"date={OOS_DATE}",
                      "rows=3", f"sha256={meta['sha256']}"):
            self.assertIn(token, lines[0])

    def test_blind_cached_values_stay_gated_by_the_reveal_path(self):
        thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)
        self._forbid_network()

        # the cached file exists, but the gate must still refuse a plain read
        with self.assertRaises(thetadata_adapter.OOSDataTouchError):
            thetadata_adapter.get_eod_chain("SPY", OOS_DATE)

        # the reveal seam reads the blind cache without touching the network
        chain = thetadata_adapter.get_eod_chain("SPY", OOS_DATE, allow_oos=True)
        self.assertEqual(len(chain), 3)
        self.assertEqual(list(chain.columns), thetadata_adapter.CHAIN_COLUMNS)

    def test_empty_merge_is_a_gap_not_an_empty_cache_file(self):
        # Observed live (QQQ 2023-12-27): greeks and OI reports both populated
        # but sharing ZERO contract keys (strike-adjustment mismatch) -> the
        # inner join is empty. That must surface as the gap RuntimeError
        # ("returned no rows" token), never be written as a zero-row parquet.
        def disjoint_fetch_raw(symbol, date):
            greeks, oi = _frames()
            oi = oi.copy()
            oi["strike"] = oi["strike"] + 0.22  # no key overlap
            return greeks, oi

        thetadata_adapter._fetch_raw = disjoint_fetch_raw

        with self.assertRaisesRegex(RuntimeError, "returned no rows"):
            thetadata_adapter.blind_cache_chain(
                "QQQ", OOS_DATE, ledger_dir=self.ledger_dir)
        self.assertFalse(thetadata_adapter._cache_path("QQQ", OOS_DATE).exists())

    def test_already_cached_file_is_not_refetched_and_still_audited(self):
        first = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)
        self._forbid_network()

        second = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        self.assertTrue(second["already_cached"])
        self.assertEqual(second["rows"], first["rows"])
        self.assertEqual(second["sha256"], first["sha256"])
        self.assertEqual(second["columns"], first["columns"])
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 2)


if __name__ == "__main__":
    unittest.main()

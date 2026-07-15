"""tests/test_underlying_ohlcv.py"""
import contextlib
import io
import tempfile
import unittest
from unittest import mock

import pandas as pd

import config
from data import underlying_closes, underlying_ohlcv
from data.thetadata_adapter import OOSDataTouchError


def synthetic_frame():
    return pd.DataFrame({
        "date": ["2022-12-29", "2022-12-30", "2023-01-03", "2022-12-28"],
        "open": [381.0, 379.0, 383.0, 382.0],
        "high": [384.0, 382.0, 386.0, 385.0],
        "low": [380.0, 378.0, 382.0, 381.0],
        "close": [382.4, 380.1, 384.2, 383.0],
        "volume": [1000.0, 1100.0, 1200.0, 900.0],
    })


class UnderlyingOhlcvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_ohlcv, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        underlying_ohlcv.store_ohlcv("VST", synthetic_frame())

    def test_store_sorts_and_dedupes(self):
        df = underlying_ohlcv.load_ohlcv("VST", "2022-12-01", "2022-12-31")
        self.assertEqual(list(df.index),
                         ["2022-12-28", "2022-12-29", "2022-12-30"])

    def test_load_columns_and_dtypes(self):
        df = underlying_ohlcv.load_ohlcv("VST", "2022-12-01", "2022-12-31")
        self.assertEqual(list(df.columns),
                         ["open", "high", "low", "close", "volume"])
        self.assertTrue(all(str(dt) == "float64" for dt in df.dtypes))

    def test_dedupe_keeps_last(self):
        frame = pd.DataFrame({
            "date": ["2022-12-28", "2022-12-28"],
            "open": [1.0, 2.0], "high": [1.0, 2.0], "low": [1.0, 2.0],
            "close": [1.0, 2.0], "volume": [10.0, 20.0],
        })
        underlying_ohlcv.store_ohlcv("DUP", frame)
        df = underlying_ohlcv.load_ohlcv("DUP", "2022-12-01", "2022-12-31")
        self.assertEqual(float(df.loc["2022-12-28", "close"]), 2.0)

    def test_store_rejects_wrong_columns(self):
        with self.assertRaises(ValueError):
            underlying_ohlcv.store_ohlcv(
                "VST", pd.DataFrame({"day": ["2022-12-28"], "close": [1.0]}))

    def test_loader_refuses_post_insample_by_default(self):
        with self.assertRaises(OOSDataTouchError):
            underlying_ohlcv.load_ohlcv("VST", "2022-12-01", "2023-01-31")

    def test_loader_allows_explicit_oos(self):
        df = underlying_ohlcv.load_ohlcv(
            "VST", "2022-12-01", "2023-01-31", allow_oos=True)
        self.assertIn("2023-01-03", df.index)

    def test_boundary_inclusive_no_flag_needed(self):
        df = underlying_ohlcv.load_ohlcv("VST", "2022-12-01",
                                         config.IN_SAMPLE_END)
        self.assertEqual(len(df), 3)


class RowsToFrameTests(unittest.TestCase):
    def test_rows_to_frame_normalizes(self):
        rows = [("2023-01-04", 1.0, 2.0, 0.5, 1.5, 100.0)]
        frame = underlying_ohlcv.rows_to_frame(rows)
        self.assertEqual(list(frame.columns),
                         ["date", "open", "high", "low", "close", "volume"])
        self.assertEqual(list(frame["date"]), ["2023-01-04"])


class YahooOhlcvPayloadTests(unittest.TestCase):
    @staticmethod
    def payload(ts, opens, highs, lows, closes, vols, tz="America/New_York"):
        return {"chart": {"error": None, "result": [{
            "meta": {"exchangeTimezoneName": tz},
            "timestamp": ts,
            "indicators": {"quote": [{
                "open": opens, "high": highs, "low": lows,
                "close": closes, "volume": vols}]}}]}}

    def test_error_payload_raises(self):
        with self.assertRaises(ValueError):
            underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
                {"chart": {"error": {"code": "Not Found"}, "result": None}})

    def test_empty_result_raises(self):
        with self.assertRaises(ValueError):
            underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
                {"chart": {"error": None, "result": []}})

    def test_missing_volume_array_raises(self):
        with self.assertRaises(ValueError):
            underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
                self.payload([1654286400], [122.0], [123.0], [121.0],
                             [122.35], None))

    def test_rows_parse_and_skip_null_high(self):
        # 2022-06-03 20:00 UTC == 16:00 ET; second session has a None high.
        rows = underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
            self.payload([1654286400, 1654545600],
                         [122.0, 124.0], [123.0, None], [121.0, 123.0],
                         [122.35, 125.0], [1000.0, 2000.0]))
        self.assertEqual(rows, [("2022-06-03", 122.0, 123.0, 121.0,
                                 122.35, 1000.0)])

    def test_all_null_rows_raise(self):
        with self.assertRaises(ValueError):
            underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
                self.payload([1654286400], [None], [None], [None],
                             [None], [None]))

    def test_timezone_from_meta_respected(self):
        # 2022-06-04 04:00 UTC: NY (UTC-4) -> 06-04, LA (UTC-7) -> 06-03.
        ny = underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
            self.payload([1654315200], [1.0], [1.0], [1.0], [1.0], [1.0],
                         tz="America/New_York"))
        la = underlying_ohlcv.yahoo_ohlcv_rows_from_payload(
            self.payload([1654315200], [1.0], [1.0], [1.0], [1.0], [1.0],
                         tz="America/Los_Angeles"))
        self.assertEqual(ny[0][0], "2022-06-04")
        self.assertEqual(la[0][0], "2022-06-03")


class UnsplitOhlcvTests(unittest.TestCase):
    def test_unsplit_multiplies_presplit_prices_divides_volume(self):
        rows = [("2022-06-03", 122.35, 123.0, 121.0, 122.35, 2000.0),
                ("2022-06-06", 124.79, 125.0, 123.0, 124.79, 1500.0)]
        out = underlying_ohlcv.unsplit_ohlcv(rows, "AMZN")
        # pre-split row: prices x20, volume /20
        self.assertAlmostEqual(out[0][1], 2447.0)
        self.assertAlmostEqual(out[0][2], 2460.0)
        self.assertAlmostEqual(out[0][3], 2420.0)
        self.assertAlmostEqual(out[0][4], 2447.0)
        self.assertAlmostEqual(out[0][5], 100.0)
        # post-split row untouched
        self.assertEqual(out[1], ("2022-06-06", 124.79, 125.0, 123.0,
                                  124.79, 1500.0))

    def test_unsplit_noop_for_unsplit_symbols(self):
        rows = [("2020-01-02", 160.62, 161.0, 159.0, 160.5, 500.0)]
        self.assertEqual(underlying_ohlcv.unsplit_ohlcv(rows, "MSFT"), rows)


class LoadOhlcvAdjustedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_ohlcv, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        # RAW (as-traded) AMZN across the 2022-06-06 20:1 split boundary.
        frame = pd.DataFrame({
            "date": ["2022-06-03", "2022-06-06"],
            "open": [2440.0, 124.0],
            "high": [2460.0, 125.0],
            "low": [2420.0, 123.0],
            "close": [2447.0, 124.79],
            "volume": [1000000.0, 500000.0],
        })
        underlying_ohlcv.store_ohlcv("AMZN", frame)

    def test_adjusted_close_continuous_and_volume_inverse(self):
        df = underlying_ohlcv.load_ohlcv_adjusted("AMZN", "2022-06-01",
                                                  "2022-06-30")
        # pre-split close /20 becomes continuous with the post-split level
        self.assertAlmostEqual(df.loc["2022-06-03", "close"], 122.35)
        self.assertAlmostEqual(df.loc["2022-06-06", "close"], 124.79)
        # volume inverse-adjusted: pre-split x20, post-split unchanged
        self.assertAlmostEqual(df.loc["2022-06-03", "volume"], 20000000.0)
        self.assertAlmostEqual(df.loc["2022-06-06", "volume"], 500000.0)

    def test_raw_unchanged(self):
        df = underlying_ohlcv.load_ohlcv("AMZN", "2022-06-01", "2022-06-30")
        self.assertAlmostEqual(df.loc["2022-06-03", "close"], 2447.0)
        self.assertAlmostEqual(df.loc["2022-06-03", "volume"], 1000000.0)


class PersistOhlcvRowsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_ohlcv, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_persist_drops_same_day_and_appends_fact(self):
        rows = [("2023-01-03", 1.0, 2.0, 0.5, 1.5, 100.0),
                ("2023-01-05", 1.0, 2.0, 0.5, 1.5, 200.0)]
        with mock.patch.object(underlying_ohlcv, "append_fact") as fact:
            path = underlying_ohlcv.persist_ohlcv_rows("VST", rows,
                                                       "2023-01-05")
        # same-day (>= today) row dropped -> only one row stored
        df = underlying_ohlcv.load_ohlcv("VST", "2023-01-01", "2023-01-31",
                                         allow_oos=True)
        self.assertEqual(list(df.index), ["2023-01-03"])
        fact.assert_called_once()
        text = fact.call_args[0][0]
        self.assertIn("DATA_PULL_OHLCV 2023-01-05", text)
        self.assertIn("Yahoo OHLCV refresh VST", text)
        self.assertIn("rows=1", text)
        self.assertIn(f"path={path}", text)


class BlindnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_ohlcv, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_store_and_load_print_nothing(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            underlying_ohlcv.store_ohlcv("VST", synthetic_frame())
            underlying_ohlcv.load_ohlcv("VST", "2022-12-01", "2022-12-31")
        self.assertEqual(buf.getvalue(), "")


class SharedSplitRegistryTests(unittest.TestCase):
    def test_reuses_underlying_closes_splits(self):
        # No duplicated SPLITS table -- the module reuses the closes registry.
        self.assertIs(underlying_ohlcv.SPLITS, underlying_closes.SPLITS)


if __name__ == "__main__":
    unittest.main()

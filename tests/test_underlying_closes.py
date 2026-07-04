"""tests/test_underlying_closes.py"""
import tempfile
import unittest
from unittest import mock

import pandas as pd

import config
from data import underlying_closes
from data.thetadata_adapter import OOSDataTouchError


def synthetic_frame():
    return pd.DataFrame({
        "date": ["2022-12-29", "2022-12-30", "2023-01-03", "2022-12-28"],
        "close": [382.4, 380.1, 384.2, 383.0],
    })


class UnderlyingClosesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(underlying_closes, "CACHE_DIR", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        underlying_closes.store_closes("VST", synthetic_frame())

    def test_store_sorts_and_dedupes(self):
        s = underlying_closes.load_closes("VST", "2022-12-01", "2022-12-31")
        self.assertEqual(list(s.index),
                         ["2022-12-28", "2022-12-29", "2022-12-30"])

    def test_store_rejects_wrong_columns(self):
        with self.assertRaises(ValueError):
            underlying_closes.store_closes(
                "VST", pd.DataFrame({"day": ["2022-12-28"], "close": [1.0]}))

    def test_loader_refuses_post_insample_by_default(self):
        with self.assertRaises(OOSDataTouchError):
            underlying_closes.load_closes("VST", "2022-12-01", "2023-01-31")

    def test_loader_allows_explicit_oos(self):
        s = underlying_closes.load_closes(
            "VST", "2022-12-01", "2023-01-31", allow_oos=True)
        self.assertIn("2023-01-03", s.index)

    def test_boundary_inclusive_no_flag_needed(self):
        s = underlying_closes.load_closes("VST", "2022-12-01",
                                          config.IN_SAMPLE_END)
        self.assertEqual(len(s), 3)


if __name__ == "__main__":
    unittest.main()


class FetchNormalizationTests(unittest.TestCase):
    def test_rows_to_frame_normalizes(self):
        rows = [("2023-01-04", 385.12), ("2023-01-03", 384.20)]
        frame = underlying_closes.rows_to_frame(rows)
        self.assertEqual(list(frame.columns), ["date", "close"])
        self.assertEqual(list(frame["date"]), ["2023-01-04", "2023-01-03"])
        self.assertAlmostEqual(float(frame["close"].iloc[1]), 384.20)


class AlphaVantagePayloadTests(unittest.TestCase):
    def test_gate_payload_raises(self):
        with self.assertRaises(RuntimeError):
            underlying_closes.av_rows_from_payload(
                {"Information": "premium endpoint"})

    def test_empty_series_raises(self):
        with self.assertRaises(RuntimeError):
            underlying_closes.av_rows_from_payload({})

    def test_series_maps_to_rows(self):
        payload = {"Time Series (Daily)": {
            "2022-06-03": {"1. open": "2516.0", "4. close": "2447.00"},
            "2022-06-06": {"1. open": "125.2", "4. close": "124.79"},
        }}
        rows = underlying_closes.av_rows_from_payload(payload)
        self.assertIn(("2022-06-03", 2447.00), rows)
        self.assertIn(("2022-06-06", 124.79), rows)


class ParitySpotTests(unittest.TestCase):
    @staticmethod
    def parity_chain(spot, expiration="2024-06-21"):
        rows = []
        for k in (spot - 10, spot - 5, spot, spot + 5, spot + 10):
            call_mid = max(spot - k, 0) + 2.0
            put_mid = call_mid - (spot - k)          # C - P = S - K (r=0)
            for right, m in (("C", call_mid), ("P", put_mid)):
                rows.append({"expiration": expiration, "strike": float(k),
                             "right": right, "bid": m - 0.05, "ask": m + 0.05,
                             "open_interest": 1000, "iv": 0.3, "delta": 0.5,
                             "gamma": 0.0, "theta": 0.0, "vega": 0.0})
        import pandas as _pd
        return _pd.DataFrame(rows)

    def test_recovers_known_spot(self):
        est = underlying_closes.parity_spot_from_chain(
            self.parity_chain(300.0), "2024-05-24")
        self.assertAlmostEqual(est, 300.0, places=6)

    def test_nan_when_no_monthly_in_band(self):
        est = underlying_closes.parity_spot_from_chain(
            self.parity_chain(300.0, expiration="2024-06-14"), "2024-05-24")
        self.assertTrue(est != est)   # NaN

    def test_nan_when_no_pc_overlap(self):
        chain = self.parity_chain(300.0)
        est = underlying_closes.parity_spot_from_chain(
            chain[chain["right"] == "P"], "2024-05-24")
        self.assertTrue(est != est)

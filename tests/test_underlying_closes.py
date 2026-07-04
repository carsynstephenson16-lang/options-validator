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

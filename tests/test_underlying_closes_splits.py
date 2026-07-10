"""Split registry must cover every split inside the cached chain windows
(Official-source dates, ledger REPORT_ADJUDICATION 2026-07-09):
NVDA 4:1 first split-adjusted trade 2021-07-20, 10:1 2024-06-10;
NOW 5:1 2025-12-18; SMCI 10:1 2024-10-01; AMZN 20:1 2022-06-06 (existing).
Raw chain cache is as-traded, so Yahoo's split-adjusted closes must be
multiplied back for pre-split rows or every H7 signal (52wk high, 20d high,
realized vol) reads a fake crash at the boundary."""

import unittest

from data.underlying_closes import SPLITS, unsplit


class TestSplitRegistry(unittest.TestCase):
    def test_registry_contains_all_known_splits(self):
        self.assertEqual(SPLITS["AMZN"], [("2022-06-06", 20.0)])
        self.assertEqual(SPLITS["NVDA"], [("2021-07-20", 4.0), ("2024-06-10", 10.0)])
        self.assertEqual(SPLITS["NOW"], [("2025-12-18", 5.0)])
        self.assertEqual(SPLITS["SMCI"], [("2024-10-01", 10.0)])

    def test_no_registry_for_names_without_splits(self):
        for sym in ("MSFT", "VST", "CEG", "PLTR", "CRWV", "TEM"):
            self.assertNotIn(sym, SPLITS)


class TestUnsplit(unittest.TestCase):
    def test_pre_split_closes_multiply_back(self):
        rows = [("2024-06-06", 120.0), ("2024-06-07", 121.0), ("2024-06-10", 122.0)]
        out = unsplit(rows, "NVDA")
        self.assertEqual(out[0], ("2024-06-06", 1200.0))
        self.assertEqual(out[1], ("2024-06-07", 1210.0))
        self.assertEqual(out[2], ("2024-06-10", 122.0))

    def test_both_nvda_splits_compound_for_2021_rows(self):
        rows = [("2021-07-19", 45.0), ("2021-07-20", 46.0), ("2024-06-10", 120.0)]
        out = unsplit(rows, "NVDA")
        # pre-2021-07-20 row: x4 (2021 split) then x10 (2024 split) = x40
        self.assertEqual(out[0], ("2021-07-19", 1800.0))
        # between the splits: only the 2024 10:1 applies
        self.assertEqual(out[1], ("2021-07-20", 460.0))
        self.assertEqual(out[2], ("2024-06-10", 120.0))

    def test_symbol_without_splits_is_untouched(self):
        rows = [("2024-06-06", 120.0)]
        self.assertEqual(unsplit(rows, "MSFT"), rows)


class TestAdjustedClosesForSignals(unittest.TestCase):
    """Review R1: raw (unsplit) closes align with strikes but read a split as
    a crash; signals must consume the adjusted series instead."""

    def test_adjustment_factor_is_future_split_product(self):
        from data.underlying_closes import adjustment_factor
        self.assertEqual(adjustment_factor("NVDA", "2021-07-19"), 40.0)
        self.assertEqual(adjustment_factor("NVDA", "2021-07-20"), 10.0)
        self.assertEqual(adjustment_factor("NVDA", "2024-06-10"), 1.0)
        self.assertEqual(adjustment_factor("MSFT", "2020-01-01"), 1.0)

    def test_adjusted_series_is_continuous_across_the_boundary(self):
        import pandas as pd

        from data.underlying_closes import adjusted_from_raw
        raw = pd.Series([1200.0, 1210.0, 122.0],
                        index=["2024-06-06", "2024-06-07", "2024-06-10"])
        adj = adjusted_from_raw(raw, "NVDA")
        self.assertAlmostEqual(adj.iloc[0], 120.0)
        self.assertAlmostEqual(adj.iloc[1], 121.0)
        self.assertAlmostEqual(adj.iloc[2], 122.0)
        # no fabricated crash: max day-over-day move ~1%
        self.assertLess(adj.pct_change().abs().max(), 0.02)

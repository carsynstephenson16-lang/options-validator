"""tests/test_portfolio.py"""
import os
import tempfile
import unittest
from datetime import date

import pandas as pd

import config
from options_researcher.portfolio import (check_buckets, load_positions,
                                          mark_position)

HDR = "id,structure,symbol,right,strike,expiration,contracts,entry_date,entry_price,bucket\n"


def chain_row(right, strike, exp, bid):
    return {"expiration": exp, "strike": strike, "right": right, "bid": bid,
            "ask": bid + 0.20, "open_interest": 500, "iv": 0.4,
            "delta": 0.7 if right == "C" else -0.2, "gamma": 0.0,
            "theta": 0.0, "vega": 0.0}


class LoadTests(unittest.TestCase):
    def write(self, body):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".csv",
                                               delete=False)
        self.tmp.write(HDR + body)
        self.tmp.close()
        self.addCleanup(os.unlink, self.tmp.name)
        return self.tmp.name

    def test_empty_book_ok(self):
        self.assertTrue(load_positions(self.write("")).empty)

    def test_wrong_right_fails_loud(self):
        path = self.write("p1,csp,VST,C,150,2026-08-21,1,2026-07-04,2.0,csp\n")
        with self.assertRaises(ValueError):
            load_positions(path)

    def test_valid_book_loads(self):
        path = self.write(
            "p1,leaps_call,MSFT,C,400,2027-06-18,1,2026-07-04,35.0,thesis\n"
            "p2,csp,VST,P,150,2026-08-21,1,2026-07-04,2.5,csp\n")
        self.assertEqual(len(load_positions(path)), 2)


class MarkTests(unittest.TestCase):
    def test_long_call_mark_and_pnl(self):
        chain = pd.DataFrame([chain_row("C", 400.0, "2027-06-18", 40.00)])
        row = pd.Series({"id": "p1", "structure": "leaps_call",
                         "symbol": "MSFT", "strike": 400.0,
                         "expiration": "2027-06-18", "contracts": 1,
                         "entry_price": 35.0})
        m = mark_position(row, chain, 450.0, "2026-07-04", [])
        h, c = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(m["pnl"],
                               (40.0 * (1 - h) - 35.0) * 100 - 2 * c, places=2)
        self.assertNotIn("ROLL_DUE(dte<=90)", m["flags"])   # dte ~349

    def test_short_put_pnl_and_assignment_watch(self):
        chain = pd.DataFrame([chain_row("P", 150.0, "2026-08-21", 3.00)])
        row = pd.Series({"id": "p2", "structure": "csp", "symbol": "VST",
                         "strike": 150.0, "expiration": "2026-08-21",
                         "contracts": 1, "entry_price": 2.5})
        m = mark_position(row, chain, 151.0, "2026-07-04",
                          [date(2026, 7, 8)])
        h, c = config.SLIPPAGE_HAIRCUT, config.COMMISSION_PER_CONTRACT
        self.assertAlmostEqual(m["pnl"],
                               (2.5 - 3.20 * (1 + h)) * 100 - 2 * c, places=2)
        self.assertIn("ASSIGNMENT_WATCH(|close-K|<=2%)", m["flags"])
        self.assertTrue(any(f.startswith("EARNINGS_") for f in m["flags"]))

    def test_quote_missing_flagged(self):
        chain = pd.DataFrame([chain_row("C", 999.0, "2027-06-18", 1.0)])
        row = pd.Series({"id": "p1", "structure": "leaps_call",
                         "symbol": "MSFT", "strike": 400.0,
                         "expiration": "2027-06-18", "contracts": 1,
                         "entry_price": 35.0})
        m = mark_position(row, chain, 450.0, "2026-07-04", [])
        self.assertIn("QUOTE_MISSING", m["flags"])
        self.assertIsNone(m["pnl"])


class BucketTests(unittest.TestCase):
    def frame(self, rows):
        return pd.DataFrame(rows, columns=["id", "structure", "symbol",
                                           "right", "strike", "expiration",
                                           "contracts", "entry_date",
                                           "entry_price", "bucket"])

    def test_thesis_premium_caps(self):
        f = self.frame([
            ["p1", "leaps_call", "MSFT", "C", 400, "2027-06-18", 1,
             "2026-07-04", 105.0, "thesis"],    # $10,500 > 10k per-name cap
                                                # (owner amendment 2026-07-04)
        ])
        issues = check_buckets(f)
        self.assertTrue(any("premium MSFT" in i for i in issues))

    def test_tactical_cap_and_count(self):
        f = self.frame([
            ["t1", "tactical_call", "VST", "C", 180, "2026-08-21", 2,
             "2026-07-04", 4.0, "tactical"],    # $800+comm > $600 cap
        ])
        issues = check_buckets(f)
        self.assertTrue(any("economic max loss" in i for i in issues))

    def test_clean_book_no_issues(self):
        f = self.frame([
            ["p1", "leaps_call", "VST", "C", 150, "2027-06-18", 1,
             "2026-07-04", 30.0, "thesis"],
            ["p2", "csp", "AMZN", "P", 200, "2026-08-21", 1,
             "2026-07-04", 2.5, "csp"],
        ])
        self.assertEqual(check_buckets(f), [])


if __name__ == "__main__":
    unittest.main()

"""Offline tests for quote-relative side and condition interpretation."""

import json
import unittest
from pathlib import Path

import pandas as pd

from data.options_flow.classify import classify_trades
from data.options_flow.normalize import normalize_trade_quotes

FIXTURES = Path(__file__).parent / "fixtures" / "options_flow"


class ClassificationTests(unittest.TestCase):
    def setUp(self):
        raw = pd.DataFrame(
            json.loads(line) for line in (FIXTURES / "trade_quote.jsonl").read_text().splitlines()
        )
        self.frame = normalize_trade_quotes(
            raw,
            symbol="MSFT",
            session="2025-01-02",
            acquired_at_utc="2025-01-03T00:00:00+00:00",
            source_version="fixture",
        )

    def test_ask_bid_mid_and_complex_are_separate(self):
        out = classify_trades(self.frame)
        self.assertEqual(out.loc[0, "side"], "LIKELY_ASK_SIDE")
        self.assertEqual(out.loc[1, "side"], "LIKELY_BID_SIDE")
        self.assertEqual(out.loc[2, "side"], "MID_UNCERTAIN")
        self.assertEqual(out.loc[3, "condition_class"], "MULTI_LEG_COMPLEX")
        self.assertFalse(out.loc[3, "directional_eligible"])

    def test_outside_market_is_invalid_not_directional(self):
        changed = self.frame.copy()
        changed.loc[0, "trade_price"] = 20.0
        out = classify_trades(changed)
        self.assertEqual(out.loc[0, "side"], "OUTSIDE_MARKET_INVALID")
        self.assertFalse(out.loc[0, "directional_eligible"])

    def test_condition_mapping_preserves_sweep_label(self):
        changed = self.frame.copy()
        changed.loc[0, "trade_condition"] = 95
        out = classify_trades(changed)
        self.assertEqual(out.loc[0, "condition_class"], "CONFIRMED_INTERMARKET_SWEEP")
        self.assertEqual(out.loc[0, "condition_name"], "INTERMARKET_SWEEP")
        self.assertFalse(out.loc[0, "directional_eligible"])

    def test_explicit_aggressor_is_not_merged_with_quote_proxy(self):
        changed = self.frame.copy()
        changed.loc[0, "trade_condition"] = 146
        out = classify_trades(changed)
        self.assertEqual(out.loc[0, "aggressor_source"], "EXCHANGE_EXPLICIT")
        self.assertEqual(out.loc[0, "explicit_aggressor_side"], "ASK_AGGRESSOR")
        self.assertTrue(out.loc[0, "explicit_directional_eligible"])
        self.assertFalse(out.loc[0, "proxy_directional_eligible"])

    def test_auction_and_cross_iso_are_not_mislabeled_as_sweeps(self):
        changed = pd.concat([self.frame.iloc[[0]], self.frame.iloc[[0]]], ignore_index=True)
        changed["trade_condition"] = [126, 128]
        out = classify_trades(changed)
        self.assertEqual(out.loc[0, "condition_class"], "AUCTION")
        self.assertEqual(out.loc[1, "condition_class"], "CROSS")

    def test_fractional_condition_code_is_rejected_not_truncated(self):
        changed = self.frame.copy()
        changed.loc[0, "trade_condition"] = 145.5
        with self.assertRaisesRegex(ValueError, "must be integral"):
            classify_trades(changed)

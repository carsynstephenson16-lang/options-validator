"""Lane decisions are pure: (closes, one day's chain, budget/ban state) ->
action dict or None. The Lumibot glue only executes actions, so the
backtest's economics are testable offline without the engine."""

import unittest
from datetime import date

import pandas as pd

from strategies.h7_lanes import decide_lane_a, decide_lane_b, decide_lane_c

TODAY = date(2026, 7, 8)
DEEP_RECLAIM = [140.0] * 240 + [66.0] * 25 + [74.0]
QUIET_COIL = [100.0] * 260


def closes_series(path):
    idx = pd.bdate_range(end="2026-07-08", periods=len(path))
    return pd.Series([float(v) for v in path], index=idx, name="close")


def chain(center: float, iv: float, put_iv: float | None = None):
    """Monthly 2026-10-16 (~100 DTE) + 2026-08-21 (~44 DTE); tight NTM quotes
    both rights; call deltas fall with strike, put |deltas| rise."""
    rows = []
    for k in range(10):
        strike = center - 10 + 2.5 * k
        c_bid = max(0.5, 14.0 - 1.5 * k)
        p_bid = max(0.5, 2.0 + 1.1 * k)
        for exp in ("2026-08-21", "2026-10-16"):
            rows.append({
                "expiration": exp, "strike": strike, "right": "C",
                "bid": c_bid, "ask": c_bid * 1.04, "open_interest": 900,
                "iv": iv, "delta": max(0.05, 0.90 - 0.09 * k),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
            rows.append({
                "expiration": exp, "strike": strike, "right": "P",
                "bid": p_bid, "ask": p_bid * 1.04, "open_interest": 900,
                "iv": put_iv if put_iv is not None else iv,
                "delta": -min(0.95, 0.10 + 0.09 * k),
                "gamma": 0.0, "theta": 0.0, "vega": 0.0,
            })
    return pd.DataFrame(rows)


class TestLaneA(unittest.TestCase):
    def test_armed_cheap_iv_buys_call_within_budget(self):
        action = decide_lane_a(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=0.30),
            today=TODAY, month_spent=0.0, banned=False,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action["kind"], "long_call")
        self.assertGreaterEqual(action["delta"], 0.55)
        self.assertLessEqual(action["delta"], 0.70)
        self.assertLessEqual(action["cost"], 6000)
        self.assertEqual(action["lane"], "a")

    def test_par_iv_builds_debit_spread(self):
        # RV of the reclaim tape is ~0.45; iv 0.48 -> ratio ~1.07 (par band)
        action = decide_lane_a(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=0.48),
            today=TODAY, month_spent=0.0, banned=False,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action["kind"], "call_debit_spread")
        self.assertLess(action["long_strike"], action["short_strike"])
        self.assertLessEqual(action["cost"], 6000)

    def test_budget_ban_and_unarmed_return_none(self):
        s = closes_series(DEEP_RECLAIM)
        ch = chain(74.0, iv=0.30)
        self.assertIsNone(decide_lane_a(closes=s, chain=ch, today=TODAY,
                                        month_spent=5900.0, banned=False))
        self.assertIsNone(decide_lane_a(closes=s, chain=ch, today=TODAY,
                                        month_spent=0.0, banned=True))
        self.assertIsNone(decide_lane_a(closes=closes_series(QUIET_COIL),
                                        chain=ch, today=TODAY,
                                        month_spent=0.0, banned=False))

    def test_rich_iv_is_not_lane_a_business(self):
        action = decide_lane_a(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=1.20),
            today=TODAY, month_spent=0.0, banned=False,
        )
        self.assertIsNone(action)


class TestLaneB(unittest.TestCase):
    def test_coil_with_cheap_iv_buys_call(self):
        # a coil compresses FROM volatility: wild 200 sessions, then a tight
        # 60-session cycle puts current 20d RV in the bottom quartile of its
        # own 1yr history (a flat prefix would invert the percentile)
        path = [100.0, 110.0, 90.0, 105.0, 95.0] * 40 + [98.0, 99.0, 100.0, 101.0] * 15
        action = decide_lane_b(
            closes=closes_series(path), chain=chain(100.0, iv=0.10),
            today=TODAY, month_spent=0.0, banned=False,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action["kind"], "long_call")
        self.assertEqual(action["lane"], "b")

    def test_wide_range_returns_none(self):
        path = [100.0] * 200 + [80.0, 120.0] * 30
        self.assertIsNone(decide_lane_b(
            closes=closes_series(path), chain=chain(100.0, iv=0.10),
            today=TODAY, month_spent=0.0, banned=False,
        ))


class TestLaneC(unittest.TestCase):
    def test_rich_iv_stabilized_sells_put_spread_meeting_floor(self):
        action = decide_lane_c(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=1.20),
            today=TODAY, month_spent=0.0, banned=False, open_h7c=0,
        )
        self.assertIsNotNone(action)
        self.assertEqual(action["kind"], "bull_put_spread")
        self.assertLessEqual(abs(action["short_delta"]), 0.30)
        self.assertGreaterEqual(action["credit"], 0.30 * action["width"])
        self.assertLessEqual(action["max_loss"], 6000)
        self.assertEqual(action["dte_band"], (30, 45))

    def test_concurrency_cap_blocks_second_position(self):
        self.assertIsNone(decide_lane_c(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=1.20),
            today=TODAY, month_spent=0.0, banned=False, open_h7c=1,
        ))

    def test_cheap_iv_is_not_lane_c_business(self):
        self.assertIsNone(decide_lane_c(
            closes=closes_series(DEEP_RECLAIM), chain=chain(74.0, iv=0.30),
            today=TODAY, month_spent=0.0, banned=False, open_h7c=0,
        ))


class TestLaneCThinCredit(unittest.TestCase):
    def test_low_put_bids_fail_the_credit_floor(self):
        ch = chain(74.0, iv=1.20)
        # crush put bids so the spread credit collapses below 30% of width
        puts = ch.right == "P"
        ch.loc[puts, "bid"] = 0.30
        ch.loc[puts, "ask"] = 0.34
        self.assertIsNone(decide_lane_c(
            closes=closes_series(DEEP_RECLAIM), chain=ch,
            today=TODAY, month_spent=0.0, banned=False, open_h7c=0,
        ))

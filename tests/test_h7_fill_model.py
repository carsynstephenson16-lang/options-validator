"""7b-2R finding 5: ONE canonical adverse-price transform everywhere;
crossed/one-sided/non-finite quotes rejected at every pricing point;
vertical bounds on entry economics and exit marks; boundary cases where
unrounded math passes but rounded (= exact engine) execution must cancel."""

import math
import unittest
from datetime import date
from types import SimpleNamespace

import pandas as pd

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from strategies import h7_lanes
from strategies.h7_backtest import H7LaneBacktest, _H7Position


def R(bid, ask, strike=0.0):
    return SimpleNamespace(bid=bid, ask=ask, strike=strike,
                           open_interest=1000)


def strat_with(pos, chain):
    s = H7LaneBacktest.__new__(H7LaneBacktest)
    s._pos = pos
    s.symbol = pos.symbol
    s._chain_provider = lambda sym, iso: chain
    return s


def chain_of(rows):
    return pd.DataFrame([
        {"expiration": e, "strike": float(k), "right": r,
         "bid": b, "ask": a, "open_interest": 1000, "iv": 0.5,
         "delta": d, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
        for (e, k, r, b, a, d) in rows
    ])


class TestCanonicalTransform(unittest.TestCase):
    def test_buy_rounds_up_sell_rounds_down(self):
        # 9.8817 * 1.01 = 9.980517 -> buy 9.99 (up), never 9.98
        self.assertEqual(adverse_buy(9.8817), 9.99)
        # 3.539 * 0.99 = 3.50361 -> sell 3.50 (down), never 3.51
        self.assertEqual(adverse_sell(3.539), 3.50)

    def test_transform_matches_engine_feed_widening(self):
        # the feed builds bid/ask with the SAME functions; spot-check the
        # historic inline formulas they replaced
        for a in (0.37, 1.234, 25.50, 9.8817):
            self.assertEqual(adverse_buy(a),
                             math.ceil(a * 1.01 * 100) / 100)
        for b in (0.37, 1.234, 25.00, 3.539):
            self.assertEqual(adverse_sell(b),
                             math.floor(b * 0.99 * 100) / 100)

    def test_decide_layer_fills_are_the_canonical_transform(self):
        row = R(bid=3.539, ask=9.8817)
        self.assertEqual(h7_lanes._buy_fill(row), adverse_buy(9.8817))
        self.assertEqual(h7_lanes._sell_fill(row), adverse_sell(3.539))


class TestQuoteValidity(unittest.TestCase):
    def test_rejects_crossed_one_sided_and_non_finite(self):
        self.assertTrue(quote_valid(1.00, 1.10))
        self.assertTrue(quote_valid(1.00, 1.00))       # locked is executable
        self.assertFalse(quote_valid(1.20, 1.10))      # crossed
        self.assertFalse(quote_valid(0.0, 1.10))       # one-sided
        self.assertFalse(quote_valid(1.00, 0.0))
        self.assertFalse(quote_valid(float("nan"), 1.10))
        self.assertFalse(quote_valid(1.00, float("inf")))
        self.assertFalse(quote_valid(None, 1.10))

    def test_monthly_rows_exclude_crossed_books(self):
        chain = chain_of([
            ("2022-09-16", 67.5, "C", 9.90, 9.80, 0.63),   # crossed
            ("2022-09-16", 70.0, "C", 9.00, 9.20, 0.60),
        ])
        rows = h7_lanes._monthly_rows(
            chain, date(2022, 6, 7), config.H7_LONG_DTE_BAND, "C")
        self.assertEqual(list(rows.strike), [70.0])

    def test_leg_rows_reject_crossed_quote(self):
        chain = chain_of([("2022-09-16", 67.5, "C", 9.90, 9.80, 0.63)])
        strat = H7LaneBacktest.__new__(H7LaneBacktest)
        action = {"kind": "long_call", "strike": 67.5}
        self.assertIsNone(
            H7LaneBacktest._leg_rows(strat, chain, action, "2022-09-16"))


class TestRoundedBoundaryCancels(unittest.TestCase):
    """Unrounded math passes; the exact rounded engine price must cancel."""

    def _reval(self, action, rows, budget):
        strat = H7LaneBacktest.__new__(H7LaneBacktest)
        return H7LaneBacktest._revalidate_economics(strat, action, rows,
                                                    budget)

    def test_budget_boundary_long_call(self):
        # unrounded: 9.8817*1.01*100 + 1.30 = 999.35 <= 1000 (passes)
        # rounded:   9.99*100 + 1.30       = 1000.30 > 1000 (must cancel)
        rows = {"long": R(bid=9.50, ask=9.8817)}
        action = {"kind": "long_call", "strike": 67.5}
        unrounded = 9.8817 * 1.01 * 100 + 2 * config.COMMISSION_PER_CONTRACT
        self.assertLessEqual(unrounded, 1000.00)
        self.assertIsNone(self._reval(action, rows, budget=1000.00))
        self.assertIsNotNone(self._reval(action, rows, budget=1000.30))

    def test_credit_floor_boundary_h7c(self):
        # width 5, floor 1.50. unrounded credit 3.50361-2.001012 = 1.5026
        # (passes); rounded 3.50-2.01 = 1.49 (must cancel)
        rows = {"short": R(bid=3.539, ask=3.60, strike=65.0),
                "long": R(bid=1.90, ask=1.9812, strike=60.0)}
        action = {"kind": "bull_put_spread", "short_strike": 65.0,
                  "long_strike": 60.0}
        unrounded = 3.539 * 0.99 - 1.9812 * 1.01
        self.assertGreaterEqual(unrounded, 1.50)
        self.assertIsNone(self._reval(action, rows, budget=10_000))


class TestVerticalBounds(unittest.TestCase):
    def _reval(self, action, rows, budget=10_000):
        strat = H7LaneBacktest.__new__(H7LaneBacktest)
        return H7LaneBacktest._revalidate_economics(strat, action, rows,
                                                    budget)

    def test_h7c_credit_at_or_above_width_rejected(self):
        rows = {"short": R(bid=5.30, ask=5.40, strike=65.0),
                "long": R(bid=0.10, ask=0.15, strike=60.0)}
        action = {"kind": "bull_put_spread", "short_strike": 65.0,
                  "long_strike": 60.0}
        # credit = 5.24 - 0.16 = 5.08 >= width 5 -> broken data, no trade
        self.assertIsNone(self._reval(action, rows))

    def test_debit_spread_above_width_rejected(self):
        rows = {"long": R(bid=8.00, ask=8.20, strike=65.0),
                "short": R(bid=2.90, ask=3.00, strike=70.0)}
        action = {"kind": "call_debit_spread", "long_strike": 65.0,
                  "short_strike": 70.0}
        # debit = 8.29 - 2.87 = 5.42 > width 5 -> reject
        self.assertIsNone(self._reval(action, rows))

    def test_exit_bounds_reject_buyback_above_width_and_negative(self):
        pos = _H7Position(
            lane="c", structure="bull_put_spread", symbol="X",
            expiration=date(2022, 7, 15),
            legs={"short": ("s", "sell"), "long": ("l", "buy")},
            action={"kind": "bull_put_spread", "short_strike": 65.0,
                    "long_strike": 60.0},
            signal_date="", entry_date="", stop_ref=0.0, at_risk=0.0,
            width=5.0)
        too_wide = {"short": R(bid=5.80, ask=6.00, strike=65.0),
                    "long": R(bid=0.10, ask=0.15, strike=60.0)}
        self.assertFalse(H7LaneBacktest._exit_bounds_ok(pos, too_wide))
        negative = {"short": R(bid=0.05, ask=0.10, strike=65.0),
                    "long": R(bid=0.50, ask=0.60, strike=60.0)}
        self.assertFalse(H7LaneBacktest._exit_bounds_ok(pos, negative))
        sane = {"short": R(bid=2.00, ask=2.10, strike=65.0),
                "long": R(bid=0.50, ask=0.60, strike=60.0)}
        self.assertTrue(H7LaneBacktest._exit_bounds_ok(pos, sane))


class TestExitMarksRejectInvalidQuotes(unittest.TestCase):
    def _pos_call(self):
        return _H7Position(
            lane="a", structure="long_call", symbol="X",
            expiration=date(2022, 9, 16),
            legs={"long": (SimpleNamespace(right="CALL", strike=67.5),
                           "buy")},
            action={"kind": "long_call", "strike": 67.5},
            signal_date="", entry_date="", stop_ref=0.0, at_risk=0.0)

    def test_crossed_exit_quote_is_no_mark(self):
        chain = chain_of([("2022-09-16", 67.5, "C", 9.90, 9.80, 0.63)])
        s = strat_with(self._pos_call(), chain)
        self.assertIsNone(s._conservative_marks("2022-06-08"))

    def test_valid_quote_marks_at_canonical_sell(self):
        chain = chain_of([("2022-09-16", 67.5, "C", 9.80, 9.90, 0.63)])
        s = strat_with(self._pos_call(), chain)
        liq, buyback = s._conservative_marks("2022-06-08")
        self.assertEqual(liq, adverse_sell(9.80))
        self.assertIsNone(buyback)

    def test_h7c_buyback_beyond_width_is_no_mark(self):
        pos = _H7Position(
            lane="c", structure="bull_put_spread", symbol="X",
            expiration=date(2022, 7, 15),
            legs={"short": (SimpleNamespace(right="PUT", strike=65.0),
                            "sell"),
                  "long": (SimpleNamespace(right="PUT", strike=60.0),
                           "buy")},
            action={"kind": "bull_put_spread", "short_strike": 65.0,
                    "long_strike": 60.0},
            signal_date="", entry_date="", stop_ref=0.0, at_risk=0.0,
            width=5.0)
        chain = chain_of([("2022-07-15", 65.0, "P", 5.80, 6.00, -0.9),
                          ("2022-07-15", 60.0, "P", 0.10, 0.15, -0.2)])
        s = strat_with(pos, chain)
        self.assertIsNone(s._conservative_marks("2022-06-08"))


class TestFrozenSizingAndBands(unittest.TestCase):
    def test_diagnostic_sizing_and_feed_bands_are_frozen_config(self):
        self.assertEqual(config.H7_DIAGNOSTIC_CONTRACTS, 1)
        self.assertEqual(config.FEED_PUT_DELTA_BAND, (0.03, 0.65))
        self.assertEqual(config.FEED_CALL_DELTA_BAND, (0.10, 0.90))
        self.assertEqual(config.H7_MAX_HOLD_BUFFER_D, 2)
        self.assertEqual(config.H7_WARMUP_EXTRA_SESSIONS, 2)
        self.assertEqual(config.H7_CLOSES_LOOKBACK_D, 600)
        from data import pandas_feed
        self.assertEqual((pandas_feed.DELTA_MIN, pandas_feed.DELTA_MAX),
                         config.FEED_PUT_DELTA_BAND)
        self.assertEqual(
            (pandas_feed.CALL_DELTA_MIN, pandas_feed.CALL_DELTA_MAX),
            config.FEED_CALL_DELTA_BAND)

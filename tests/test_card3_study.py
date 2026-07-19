"""Offline unit tests for the Card 3 near-the-bottom long-call study.

All fixtures are synthetic; no network, no real-cache reads. The study's
seal (in-sample-only, cached-only) is covered separately by the adapter's
own OOS tests -- here we pin the frozen signal / selection / exit / book
semantics with dependency-injected chains.
"""
from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
import pandas as pd

import config
from options_researcher import card3_study as c3


def _adjusted_close_series() -> pd.Series:
    """254 sessions: climb to a 100 peak, a >40% decline to ~58, then a
    two-day bounce. The final session satisfies all four entry conditions."""
    climb = np.linspace(50.0, 100.0, 200)      # idx 0..199, peak 100
    decline = np.linspace(100.0, 58.0, 52)     # idx 200..251, trough 58
    bounce = np.array([59.0, 62.0])            # idx 252 (up), 253 (up bounce)
    vals = np.concatenate([climb, decline, bounce])
    idx = pd.bdate_range("2020-01-01", periods=len(vals)).strftime("%Y-%m-%d")
    return pd.Series(vals, index=idx, dtype=float)


def _row(strike, expiration, bid, ask, delta, oi=500):
    return {"right": "C", "strike": float(strike), "expiration": expiration,
            "bid": float(bid), "ask": float(ask), "delta": float(delta),
            "open_interest": int(oi)}


def _chain(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)


MONTHLY_91DTE = "2021-04-16"   # 3rd Friday; 91 DTE from 2021-01-15
NON_MONTHLY = "2021-04-09"     # 2nd Friday -> not a listed monthly


class EntrySignalTests(unittest.TestCase):
    def test_all_four_conditions_fire_on_the_bounce(self):
        closes = _adjusted_close_series()
        frame = c3.entry_signal_frame(closes)
        last = closes.index[-1]
        self.assertTrue(bool(frame.loc[last, "cond1"]))
        self.assertTrue(bool(frame.loc[last, "cond2"]))
        self.assertTrue(bool(frame.loc[last, "cond3"]))
        self.assertTrue(bool(frame.loc[last, "cond4"]))
        self.assertIn(last, c3.entry_signals(closes))

    def test_climb_day_is_not_a_signal(self):
        closes = _adjusted_close_series()
        frame = c3.entry_signal_frame(closes)
        climb_day = closes.index[150]           # near its own trailing high
        self.assertFalse(bool(frame.loc[climb_day, "cond1"]))
        self.assertNotIn(climb_day, c3.entry_signals(closes))

    def test_down_day_fails_cond4(self):
        closes = _adjusted_close_series().copy()
        last = closes.index[-1]
        closes.loc[last] = closes.iloc[-2] - 1.0   # make the bounce a down day
        self.assertNotIn(last, c3.entry_signals(closes))

    def test_new_20_session_low_sets_cond3_false(self):
        # A close that breaks strictly below the prior-20 minimum IS a new
        # 20-session low -> cond3 False. (Such a day is necessarily a down-day,
        # so cond4 also excludes it; this isolates the cond3 mechanics.)
        closes = _adjusted_close_series().copy()
        last = closes.index[-1]
        closes.loc[last] = 50.0    # below the prior-20 minimum (~58) -> new low
        frame = c3.entry_signal_frame(closes)
        self.assertFalse(bool(frame.loc[last, "cond3"]))
        self.assertNotIn(last, c3.entry_signals(closes))

    def test_short_history_yields_no_signals(self):
        closes = _adjusted_close_series().iloc[:100]     # < 252 sessions
        self.assertEqual(c3.entry_signals(closes), [])


class ContractSelectionTests(unittest.TestCase):
    def test_highest_delta_in_band_monthly_liquid_wins(self):
        chain = _chain([
            _row(90, MONTHLY_91DTE, 4.90, 5.00, 0.58),
            _row(85, MONTHLY_91DTE, 6.90, 7.00, 0.66),   # highest in-band delta
            _row(80, MONTHLY_91DTE, 9.90, 10.0, 0.72),   # out of band (>0.70)
            _row(88, NON_MONTHLY, 5.90, 6.00, 0.68),     # not a monthly
        ])
        row = c3.select_contract(chain, "2021-01-15")
        self.assertIsNotNone(row)
        self.assertEqual(float(row["strike"]), 85.0)
        self.assertAlmostEqual(float(row["delta"]), 0.66)

    def test_dte_out_of_band_excluded(self):
        chain = _chain([_row(90, "2021-02-19", 4.90, 5.00, 0.60)])  # ~35 DTE
        self.assertIsNone(c3.select_contract(chain, "2021-01-15"))

    def test_liquidity_failure_excluded(self):
        chain = _chain([
            _row(85, MONTHLY_91DTE, 6.90, 7.00, 0.66, oi=50),        # OI < 100
            _row(84, MONTHLY_91DTE, 6.00, 7.20, 0.64),               # spread > 10%
        ])
        self.assertIsNone(c3.select_contract(chain, "2021-01-15"))

    def test_entry_cost_cap(self):
        cheap = pd.Series(_row(85, MONTHLY_91DTE, 4.90, 5.00, 0.66))
        self.assertIsNotNone(c3.entry_cost_if_within_cap(cheap))
        self.assertLessEqual(c3.entry_cost_if_within_cap(cheap), config.MAX_LOSS_PER_TRADE)
        pricey = pd.Series(_row(70, MONTHLY_91DTE, 6.90, 7.00, 0.66))  # 707.65 > 600
        self.assertIsNone(c3.entry_cost_if_within_cap(pricey))
        self.assertIsNone(c3.entry_cost_if_within_cap(None))


def _provider(mapping):
    """(sym, iso) -> chain; FileNotFoundError on a missing day (a data gap)."""
    def provider(sym, iso):
        key = (sym, iso)
        if key not in mapping:
            raise FileNotFoundError(f"no cached chain {sym} {iso}")
        return mapping[key]
    return provider


ENTRY = "2021-01-15"
S1, S2, S3, S4 = "2021-01-19", "2021-02-16", "2021-03-18", "2021-04-01"
BENIGN = _chain([_row(85, MONTHLY_91DTE, 3.00, 3.10, 0.66)])   # mid 3.05, no TP


class SimulateTradeTests(unittest.TestCase):
    def _entry_chain(self):
        return _chain([_row(85, MONTHLY_91DTE, 4.90, 5.00, 0.66)])  # e_mid 4.95, cost 505.65

    def test_take_profit(self):
        tp_chain = _chain([_row(85, MONTHLY_91DTE, 9.95, 10.05, 0.80)])  # mid 10.0 >= 9.9
        prov = _provider({("X", ENTRY): self._entry_chain(),
                          ("X", S1): tp_chain})
        trade = c3.simulate_trade("X", ENTRY, prov, [S1, S2, S3])
        self.assertEqual(trade["exit_reason"], "take_profit")
        self.assertEqual(trade["exit_fill_session"], S1)
        self.assertGreater(trade["pnl"], 0.0)
        # conservative fill: adverse_sell(9.95)*100 - comm - cost
        self.assertAlmostEqual(trade["pnl"], 984.35 - 505.65, places=2)

    def test_time_exit(self):
        prov = _provider({("X", ENTRY): self._entry_chain(),
                          ("X", S1): BENIGN, ("X", S2): BENIGN, ("X", S3): BENIGN})
        trade = c3.simulate_trade("X", ENTRY, prov, [S1, S2, S3])  # S3 DTE 29 <= 30
        self.assertEqual(trade["exit_reason"], "time_exit")
        self.assertEqual(trade["exit_fill_session"], S3)
        self.assertLess(trade["pnl"], 0.0)
        self.assertFalse(trade["worthless_quote_exit"])

    def test_worthless_books_max_loss(self):
        dead = _chain([_row(85, MONTHLY_91DTE, 0.0, 0.05, 0.66)])
        prov = _provider({("X", ENTRY): self._entry_chain(),
                          ("X", S1): BENIGN, ("X", S2): BENIGN, ("X", S3): dead})
        trade = c3.simulate_trade("X", ENTRY, prov, [S1, S2, S3])
        self.assertTrue(trade["worthless_quote_exit"])
        self.assertAlmostEqual(trade["pnl"], -505.65, places=2)

    def test_eod_gap_on_exit_day_is_skipped_and_logged(self):
        # S3 (the protective session) is missing -> gap logged, fill at S4.
        prov = _provider({("X", ENTRY): self._entry_chain(),
                          ("X", S1): BENIGN, ("X", S2): BENIGN,
                          ("X", S4): _chain([_row(85, MONTHLY_91DTE, 2.00, 2.05, 0.66)])})
        trade = c3.simulate_trade("X", ENTRY, prov, [S1, S2, S3, S4])
        self.assertEqual(trade["exit_reason"], "time_exit")
        self.assertIn(S3, trade["gaps"])
        self.assertEqual(trade["exit_fill_session"], S4)

    def test_open_at_in_sample_end_when_exit_unobservable(self):
        # No session reaches DTE<=30 and no TP -> unresolved, never peeks past seal.
        prov = _provider({("X", ENTRY): self._entry_chain(),
                          ("X", S1): BENIGN, ("X", S2): BENIGN})
        trade = c3.simulate_trade("X", ENTRY, prov, [S1, S2])
        self.assertIsNone(trade["pnl"])
        self.assertEqual(trade["exit_reason"], "open_at_in_sample_end")

    def test_no_tradable_contract_returns_none(self):
        prov = _provider({("X", ENTRY): _chain([_row(80, MONTHLY_91DTE, 9.90, 10.0, 0.72)])})
        self.assertIsNone(c3.simulate_trade("X", ENTRY, prov, [S1, S2, S3]))


class BookRuleTests(unittest.TestCase):
    def test_one_open_per_name_then_reentry(self):
        entry_chain = _chain([_row(85, MONTHLY_91DTE, 4.90, 5.00, 0.66)])
        s3_entry = _chain([_row(85, "2021-07-16", 4.90, 5.00, 0.66)])  # 106 DTE
        prov = _provider({
            ("X", ENTRY): entry_chain, ("X", S1): BENIGN, ("X", S2): BENIGN,
            ("X", S3): BENIGN,                              # signal1 time-exit @ S3
            ("X", S4): s3_entry,                            # signal3 re-entry
        })
        sessions = [S1, S2, S3, "2021-04-05", "2021-06-01"]
        with mock.patch.object(c3, "entry_signals",
                               return_value=[ENTRY, "2021-02-01", S4]):
            res = c3.run_symbol("X", prov, pd.Series(dtype=float), sessions)
        # signal1 fills (time-exit @ S3); signal2 (2021-02-01) blocked while open;
        # signal3 (2021-04-01 > S3) re-enters.
        self.assertEqual(len(res["trades"]), 2)
        self.assertEqual(res["trades"][0]["exit_fill_session"], S3)
        self.assertEqual(res["trades"][1]["entry_date"], S4)
        self.assertTrue(any(s["reason"] == "position_open" for s in res["skips"]))

    def test_no_fill_does_not_block_later_signal(self):
        empty = _chain([_row(80, MONTHLY_91DTE, 9.90, 10.0, 0.72)])  # nothing tradable
        good = _chain([_row(85, "2021-07-16", 4.90, 5.00, 0.66)])    # 106 DTE from S4
        prov = _provider({("X", ENTRY): empty, ("X", S4): good,
                          ("X", "2021-04-05"): BENIGN, ("X", "2021-06-01"): BENIGN})
        sessions = [S1, S2, S3, "2021-04-05", "2021-06-01"]
        with mock.patch.object(c3, "entry_signals", return_value=[ENTRY, S4]):
            res = c3.run_symbol("X", prov, pd.Series(dtype=float), sessions)
        self.assertEqual(len(res["trades"]), 1)          # only signal3 filled
        self.assertEqual(res["trades"][0]["entry_date"], S4)
        self.assertTrue(any(s["reason"] == "no_tradable_contract_or_over_cap"
                            for s in res["skips"]))


class VerdictTests(unittest.TestCase):
    def test_verdict_lines(self):
        self.assertEqual(
            c3.card3_verdict({"n_losses": 12, "expectancy_CI90": (-50.0, -10.0)}),
            c3.VERDICT_REJECTED)
        self.assertEqual(
            c3.card3_verdict({"n_losses": 12, "expectancy_CI90": (10.0, 50.0)}),
            c3.VERDICT_GRADUATE)
        self.assertEqual(
            c3.card3_verdict({"n_losses": 3, "expectancy_CI90": (-50.0, -10.0)}),
            c3.VERDICT_INCONCLUSIVE)
        self.assertEqual(
            c3.card3_verdict({"n_losses": 12, "expectancy_CI90": (-10.0, 10.0)}),
            c3.VERDICT_INCONCLUSIVE)


class ProviderSealTests(unittest.TestCase):
    def test_provider_raises_on_missing_cache(self):
        prov = c3._cached_chain_provider("ZZZZ")
        with self.assertRaises(FileNotFoundError):
            prov("ZZZZ", "2019-01-02")   # no such cached parquet


if __name__ == "__main__":
    unittest.main()

"""tests/test_run_backtest_harness.py -- harness/run_backtest.run() wiring.

run() executes per-symbol, per-calendar-year chunked Lumibot backtests from
the offline cache (memory: a 5-year single feed would need ~10^5 per-contract
Data objects). Chunking must not change WHAT is traded:
  * interior chunks allow entries through Dec 31 and simulate a tail into the
    next year so every position exits inside its own chunk;
  * a position that exits inside the NEXT chunk's calendar blocks that chunk's
    entries until after the exit day (one-spread-per-underlying is preserved
    across the seam);
  * the FINAL chunk stops entries MAX_HOLD_DAYS before `end` so no in-sample
    position ever needs post-IN_SAMPLE_END (holdout) quotes to exit.

All fixtures synthetic; offline; no .cache/ dependency.
"""
import unittest
from datetime import date, timedelta
from unittest import mock

import pandas as pd

from data import thetadata_adapter
from harness import run_backtest
from strategies.put_credit_spread import PutCreditSpread


def synth_chain(rows):
    return pd.DataFrame(
        [
            {
                "expiration": e, "strike": float(k), "right": r,
                "bid": float(b), "ask": float(a), "open_interest": int(oi),
                "iv": 0.25, "delta": float(d), "gamma": 0.01,
                "theta": -0.05, "vega": 0.1,
            }
            for (e, k, r, b, a, oi, d) in rows
        ]
    )


class YearChunkTests(unittest.TestCase):
    def test_full_window_makes_five_chunks(self):
        chunks = run_backtest._year_chunks(
            date(2018, 1, 1), date(2022, 12, 31))
        self.assertEqual(len(chunks), 5)
        sim_start, cutoff, sim_end = chunks[0]
        self.assertEqual(sim_start, "2018-01-01")
        self.assertEqual(cutoff, "2018-12-31")
        # tail = MAX_HOLD_DAYS into 2019 so Dec-2018 entries can exit
        self.assertEqual(
            sim_end,
            (date(2018, 12, 31)
             + timedelta(days=run_backtest.MAX_HOLD_DAYS)).isoformat())

    def test_final_chunk_entry_cutoff_protects_the_holdout(self):
        chunks = run_backtest._year_chunks(
            date(2018, 1, 1), date(2022, 12, 31))
        sim_start, cutoff, sim_end = chunks[-1]
        self.assertEqual(sim_start, "2022-01-01")
        self.assertEqual(
            cutoff,
            (date(2022, 12, 31)
             - timedelta(days=run_backtest.MAX_HOLD_DAYS)).isoformat())
        self.assertEqual(sim_end, "2022-12-31")  # never past `end`

    def test_partial_year_window(self):
        chunks = run_backtest._year_chunks(date(2022, 6, 1), date(2022, 8, 31))
        self.assertEqual(len(chunks), 1)
        sim_start, cutoff, sim_end = chunks[0]
        self.assertEqual(sim_start, "2022-06-01")
        self.assertEqual(
            cutoff,
            (date(2022, 8, 31)
             - timedelta(days=run_backtest.MAX_HOLD_DAYS)).isoformat())
        self.assertEqual(sim_end, "2022-08-31")


class OOSGuardTests(unittest.TestCase):
    def test_run_refuses_post_boundary_end_without_allow_oos(self):
        with self.assertRaises(thetadata_adapter.OOSDataTouchError):
            run_backtest.run(PutCreditSpread, end="2023-06-30")


class CarryOverBlockingTests(unittest.TestCase):
    def test_blocked_until_carries_tail_exit_into_next_chunk(self):
        calls = []

        def fake_chunk(strategy_cls, symbol, sim_start, cutoff, sim_end,
                       blocked_until, allow_oos):
            calls.append((symbol, sim_start, blocked_until))
            if sim_start == "2021-01-01":
                return [{"pnl": 1.0, "capital_at_risk": 100.0,
                         "entry_date": "2021-12-20", "symbol": symbol,
                         "economic_max_loss": 105.0,
                         "exit_reason": "close_at_dte",
                         "exit_date": "2022-01-25"}]
            return []

        with mock.patch.object(run_backtest, "_run_chunk", fake_chunk):
            trades = run_backtest.run(
                PutCreditSpread, start="2021-01-01", end="2022-12-31",
                symbols=["SPY"])
        self.assertEqual(len(trades), 1)
        blocked_by_chunk = {c[1]: c[2] for c in calls}
        self.assertIsNone(blocked_by_chunk["2021-01-01"])
        # the 2022 chunk must not enter before the carried exit day
        self.assertEqual(blocked_by_chunk["2022-01-01"], "2022-01-25")

    def test_trades_sorted_by_entry_date_across_symbols(self):
        def fake_chunk(strategy_cls, symbol, sim_start, cutoff, sim_end,
                       blocked_until, allow_oos):
            day = "2022-03-01" if symbol == "AAA" else "2022-02-01"
            return [{"pnl": 1.0, "capital_at_risk": 100.0, "entry_date": day,
                     "symbol": symbol, "economic_max_loss": 105.0,
                     "exit_reason": "profit_target", "exit_date": day}]

        with mock.patch.object(run_backtest, "_run_chunk", fake_chunk):
            trades = run_backtest.run(
                PutCreditSpread, start="2022-01-01", end="2022-12-31",
                symbols=["AAA", "BBB"])
        self.assertEqual([t["symbol"] for t in trades], ["BBB", "AAA"])


class RunEndToEndSyntheticTests(unittest.TestCase):
    """run() through the REAL Lumibot on synthetic cached chains: the same
    profit-target scenario as tests/test_pcs_adapters.py, but entered via the
    harness (loader patched -- the suite must not depend on .cache/)."""

    @classmethod
    def setUpClass(cls):
        exp = "2022-07-08"
        entry = [
            (exp, 100.0, "P", 1.20, 1.30, 500, -0.30),
            (exp,  98.0, "P", 0.60, 0.64, 500, -0.25),
        ]
        decay = [
            (exp, 100.0, "P", 0.20, 0.24, 500, -0.10),
            (exp,  98.0, "P", 0.05, 0.07, 500, -0.04),
        ]
        days = ["2022-06-01", "2022-06-02", "2022-06-03", "2022-06-06",
                "2022-06-07", "2022-06-08", "2022-06-09", "2022-06-10"]
        chains = {d: synth_chain(entry if d < "2022-06-03" else decay)
                  for d in days}

        def fake_loader(symbol, start_iso, end_iso, *, allow_oos=False):
            assert symbol == "SYN"
            assert not allow_oos
            return {d: c for d, c in chains.items() if start_iso <= d <= end_iso}

        with mock.patch.object(
                run_backtest.pandas_feed, "load_cached_chains", fake_loader):
            cls.trades = run_backtest.run(
                PutCreditSpread, start="2022-06-01", end="2022-08-31",
                symbols=["SYN"])

    def test_one_trade_extracted_with_hand_math(self):
        self.assertEqual(len(self.trades), 1)
        t = self.trades[0]
        self.assertEqual(t["symbol"], "SYN")
        self.assertEqual(t["entry_decision_date"], "2022-06-01")
        self.assertEqual(t["entry_date"], "2022-06-02")
        self.assertEqual(t["exit_decision_date"], "2022-06-03")
        self.assertEqual(t["exit_date"], "2022-06-06")
        self.assertAlmostEqual(t["pnl"], 117.60, places=2)

    def test_trades_feed_the_scoreboard(self):
        from metrics import scoreboard
        sb = scoreboard(self.trades, label="harness synthetic")
        self.assertIn("INSUFFICIENT SAMPLE", sb["verdict"])


if __name__ == "__main__":
    unittest.main()

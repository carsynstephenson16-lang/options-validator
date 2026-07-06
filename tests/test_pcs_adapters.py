"""tests/test_pcs_adapters.py -- PutCreditSpread Lumibot adapters.

Two layers:
  1. Pure selection/gating adapters, tested on a bare instance (no engine).
  2. One synthetic end-to-end backtest through the REAL installed Lumibot
     (PandasData path proven by the 2026-07-03 spike): entry, profit-target
     exit, and closed-trade extraction with hand-computed dollar values.

All fixtures are synthetic; the suite must run offline and without .cache/.
"""
import unittest
from datetime import date, datetime

import pandas as pd

import config
from data import pandas_feed
from strategies.base import round_trip_commission_per_spread
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


def bare_strategy(today: date, **params):
    """A PutCreditSpread with NO engine: only the attributes the pure
    adapters need."""
    s = object.__new__(PutCreditSpread)
    s.delta = config.A_SHORT_PUT_DELTA
    s.width = config.A_SPREAD_WIDTH
    s.dte_band = config.A_TARGET_DTE
    s.haircut = config.SLIPPAGE_HAIRCUT
    s._chain_provider = params.get("chain_provider")
    s._tradeable = params.get("tradeable_assets")
    s._entry_cutoff = params.get("entry_cutoff")
    s._blocked_until = params.get("blocked_until")
    s._spreads = {}
    s.closed_trades = []
    s.get_datetime = lambda: datetime(today.year, today.month, today.day, 16)
    return s


LIQ = 500  # comfortably past MIN_OPEN_INTEREST


class SelectionAdapterTests(unittest.TestCase):
    def chain(self):
        # today = 2022-06-01: DTEs are 16 (Jun 17), 37 (Jul 8), 58 (Jul 29)
        return synth_chain([
            ("2022-06-17", 100.0, "P", 1.0, 1.05, LIQ, -0.30),
            ("2022-07-08", 100.0, "P", 1.20, 1.30, LIQ, -0.30),
            ("2022-07-08",  98.0, "P", 0.60, 0.66, LIQ, -0.25),
            ("2022-07-08",  90.0, "P", 0.10, 0.11, LIQ, -0.05),
            ("2022-07-29", 100.0, "P", 1.6, 1.7, LIQ, -0.31),
            ("2022-07-08", 100.0, "C", 2.0, 2.1, LIQ, 0.70),
        ])

    def test_pick_expiration_nearest_in_band(self):
        s = bare_strategy(date(2022, 6, 1))
        self.assertEqual(
            s._pick_expiration(self.chain(), config.A_TARGET_DTE), "2022-07-08")

    def test_pick_expiration_none_when_band_empty(self):
        s = bare_strategy(date(2022, 6, 1))
        chain = synth_chain([("2022-06-17", 100.0, "P", 1.0, 1.1, LIQ, -0.30)])
        self.assertIsNone(s._pick_expiration(chain, config.A_TARGET_DTE))

    def test_strike_nearest_delta_matches_on_abs_delta_puts_only(self):
        s = bare_strategy(date(2022, 6, 1))
        row = s._strike_nearest_delta(self.chain(), "2022-07-08", 0.30)
        self.assertEqual(row.strike, 100.0)
        self.assertEqual(row.right, "P")

    def test_strike_below_finds_width_lower(self):
        s = bare_strategy(date(2022, 6, 1))
        short = s._strike_nearest_delta(self.chain(), "2022-07-08", 0.30)
        long = s._strike_below(self.chain(), "2022-07-08", short, 2)
        self.assertEqual(long.strike, 98.0)

    def test_strike_below_none_when_absent(self):
        s = bare_strategy(date(2022, 6, 1))
        short = s._strike_nearest_delta(self.chain(), "2022-07-08", 0.30)
        self.assertIsNone(s._strike_below(self.chain(), "2022-07-08", short, 3))

    def test_liquid_gates_on_oi_and_spread(self):
        s = bare_strategy(date(2022, 6, 1))
        good = self.chain().iloc[1]
        bad_oi = good.copy(); bad_oi["open_interest"] = 5
        wide = good.copy(); wide["bid"] = 1.0; wide["ask"] = 1.3
        self.assertTrue(s._liquid(good))
        self.assertFalse(s._liquid(bad_oi))
        self.assertFalse(s._liquid(wide))


class EntryGateTests(unittest.TestCase):
    def test_blocked_until_is_exclusive_cutoff_inclusive(self):
        s = bare_strategy(date(2022, 6, 1),
                          blocked_until="2022-06-01", entry_cutoff="2022-06-01")
        self.assertFalse(s._entry_allowed())  # still blocked ON the date
        s2 = bare_strategy(date(2022, 6, 2), blocked_until="2022-06-01")
        self.assertTrue(s2._entry_allowed())
        s3 = bare_strategy(date(2022, 6, 2), entry_cutoff="2022-06-01")
        self.assertFalse(s3._entry_allowed())  # past the cutoff

    def test_default_is_allowed(self):
        self.assertTrue(bare_strategy(date(2022, 6, 1))._entry_allowed())


class FailLoudTests(unittest.TestCase):
    def test_submit_spread_raises_when_leg_missing_from_feed(self):
        s = bare_strategy(date(2022, 6, 1), tradeable_assets=set())
        chain = synth_chain([
            ("2022-07-08", 100.0, "P", 1.2, 1.3, LIQ, -0.30),
            ("2022-07-08",  98.0, "P", 0.6, 0.7, LIQ, -0.25),
        ])
        short = s._strike_nearest_delta(chain, "2022-07-08", 0.30)
        long = s._strike_below(chain, "2022-07-08", short, 2)
        with self.assertRaises(RuntimeError):
            s._submit_spread("SYN", "2022-07-08", short, long, 1, 0.48)


class EndToEndSyntheticBacktestTests(unittest.TestCase):
    """One spread, entered 2022-06-01, profit-target exit -- through the real
    installed Lumibot. Hand-computed expectations:

    day-1 raw quotes: short 100P 1.20/1.30, long 98P 0.60/0.64 (both pass the
    10% max-spread and MIN_OPEN_INTEREST gates)
      model credit  = 1.20*0.99 - 0.64*1.01             = 0.5416
      contracts     = floor(600 / ((2-0.5416)*100+2.60)) = 4
      engine credit = floor(1.188)c - ceil(0.6464)c      = 1.18 - 0.65 = 0.53
    decay-day raw quotes: short 0.20/0.24, long 0.05/0.07
      cost-to-close = 0.24*1.01 - 0.05*0.99 = 0.1929
      captured vs engine credit 0.53 -> 64% >= 50% -> profit_target
      engine debit  = ceil(0.2424)c - floor(0.0495)c     = 0.25 - 0.04 = 0.21
      pnl = (0.53-0.21)*100*4 - 2.60*4 = 128.00 - 10.40  = 117.60
    """

    @classmethod
    def setUpClass(cls):
        exp = "2022-07-08"
        entry = [
            (exp, 100.0, "P", 1.20, 1.30, LIQ, -0.30),
            (exp,  98.0, "P", 0.60, 0.64, LIQ, -0.25),
        ]
        decay = [
            (exp, 100.0, "P", 0.20, 0.24, LIQ, -0.10),
            (exp,  98.0, "P", 0.05, 0.07, LIQ, -0.04),
        ]
        days = ["2022-06-01", "2022-06-02", "2022-06-03",
                "2022-06-06", "2022-06-07", "2022-06-08",
                "2022-06-09", "2022-06-10"]
        cls.chains = {d: synth_chain(entry if d < "2022-06-03" else decay)
                      for d in days}
        feed = pandas_feed.build_option_data(cls.chains, "SYN", exp_max="2022-09-16")
        assert len(feed) == 2

        from lumibot.backtesting import PandasDataBacktesting
        from lumibot.entities import TradingFee
        fee = TradingFee(per_contract_fee=config.COMMISSION_PER_CONTRACT)
        cls.result, cls.strat = PutCreditSpread.run_backtest(
            PandasDataBacktesting,
            backtesting_start=datetime(2022, 6, 1),
            backtesting_end=datetime(2022, 6, 10),
            pandas_data=feed,
            budget=config.STARTING_CAPITAL,
            buy_trading_fees=[fee],
            sell_trading_fees=[fee],
            benchmark_asset=None,
            risk_free_rate=0.0,
            analyze_backtest=False,
            show_plot=False,
            save_tearsheet=False,
            show_tearsheet=False,
            show_progress_bar=False,
            quiet_logs=True,
            save_logfile=False,
            save_stats_file=False,
            parameters={
                "symbols": ["SYN"],
                "chain_provider": lambda sym, iso: cls.chains.get(iso),
                "tradeable_assets": set(feed.keys()),
            },
        )

    def test_exactly_one_closed_trade(self):
        self.assertEqual(len(self.strat.closed_trades), 1)

    def test_trade_dict_matches_hand_math(self):
        t = self.strat.closed_trades[0]
        self.assertEqual(t["symbol"], "SYN")
        self.assertEqual(t["entry_date"], "2022-06-01")
        self.assertAlmostEqual(t["pnl"], 117.60, places=2)
        self.assertAlmostEqual(t["capital_at_risk"], (2 - 0.53) * 100 * 4, places=2)
        self.assertAlmostEqual(
            t["economic_max_loss"],
            ((2 - 0.53) * 100 + round_trip_commission_per_spread()) * 4,
            places=2)
        self.assertEqual(t["exit_reason"], "profit_target")

    def test_engine_cash_agrees_with_extracted_pnl(self):
        self.assertAlmostEqual(
            float(self.strat.cash), config.STARTING_CAPITAL + 117.60, places=2)

    def test_no_open_spread_left(self):
        self.assertEqual(self.strat._spreads, {})


if __name__ == "__main__":
    unittest.main()

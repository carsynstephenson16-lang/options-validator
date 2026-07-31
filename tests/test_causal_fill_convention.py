"""Causal execution tests for the offline Lumibot backtest path.

Synthetic chains are written to a temporary parquet cache and loaded through
the production cache reader. Any attempt to fetch ThetaData fails the test.
"""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from data import pandas_feed, thetadata_adapter
from strategies.put_credit_spread import PutCreditSpread


def _chain(
    short_bid: float,
    short_ask: float,
    long_bid: float,
    long_ask: float,
    *,
    short_delta: float = -0.30,
    long_delta: float = -0.25,
    expiration: str = "2022-07-08",
):
    return pd.DataFrame(
        [
            {
                "expiration": expiration,
                "strike": 100.0,
                "right": "P",
                "bid": short_bid,
                "ask": short_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": short_delta,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
            {
                "expiration": expiration,
                "strike": 98.0,
                "right": "P",
                "bid": long_bid,
                "ask": long_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": long_delta,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
        ]
    )


def _run_cached_backtest(
    chains_by_day: dict[str, pd.DataFrame],
    end: datetime,
    *,
    forbidden_strategy_chain_days: set[str] | None = None,
):
    sessions = tuple(sorted(chains_by_day))
    forbidden_days = forbidden_strategy_chain_days or set()
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        for day, chain in chains_by_day.items():
            chain.to_parquet(cache_dir / f"SYN_{day}.parquet")

        def forbidden_fetch(*_args, **_kwargs):
            raise AssertionError("offline causal-fill test attempted ThetaData")

        with (
            mock.patch.object(thetadata_adapter, "CACHE_DIR", cache_dir),
            mock.patch.object(thetadata_adapter, "_fetch_merged_chain", forbidden_fetch),
        ):
            chains = pandas_feed.load_cached_chains("SYN", sessions[0], sessions[-1])

    exp_max = max(
        str(frame["expiration"].max())
        for frame in chains.values()
    )
    feed = pandas_feed.build_option_data(chains, "SYN", exp_max=exp_max)
    available_by_session = pandas_feed.assets_by_session(feed)

    from lumibot.backtesting import PandasDataBacktesting
    from lumibot.entities import TradingFee

    def chain_provider(_symbol, day):
        if day in forbidden_days:
            raise AssertionError(f"strategy read unavailable fill-day EOD chain for {day}")
        return chains.get(day)

    fee = TradingFee(per_contract_fee=config.COMMISSION_PER_CONTRACT)
    _result, strategy = PutCreditSpread.run_backtest(
        PandasDataBacktesting,
        backtesting_start=datetime.fromisoformat(sessions[0]),
        backtesting_end=end,
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
            "chain_provider": chain_provider,
            "tradeable_assets": set(feed),
            "tradeable_assets_by_session": available_by_session,
            "trading_sessions": sessions,
        },
    )
    return strategy


class CausalEntryFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signal_day = "2022-06-01"
        cls.fill_day = "2022-06-02"
        chains_by_day = {
            # Day-D executable credit after haircut/rounding: 1.18 - 0.65 = 0.53.
            cls.signal_day: _chain(1.20, 1.30, 0.60, 0.64),
            # Day-D+1 executable credit: 1.48 - 0.71 = 0.77.
            cls.fill_day: _chain(1.50, 1.60, 0.65, 0.70),
            "2022-06-03": _chain(1.50, 1.60, 0.65, 0.70),
            "2022-06-06": _chain(1.50, 1.60, 0.65, 0.70),
        }
        cls.strategy = _run_cached_backtest(
            chains_by_day,
            datetime(2022, 6, 7),
        )

    def test_owner_froze_d_plus_1_close(self):
        self.assertEqual(
            config.BACKTEST_EXECUTION_CONVENTION,
            "D_PLUS_1_CLOSE",
        )

    def test_fill_uses_d_plus_1_quotes_not_signal_day_quotes(self):
        position = self.strategy._spreads["SYN"]
        self.assertEqual(position.entry_decision_date, self.signal_day)
        self.assertAlmostEqual(position.entry_credit, 0.77, places=2)
        self.assertNotAlmostEqual(position.entry_credit, 0.53, places=2)
        self.assertEqual(position.entry_fill_date, self.fill_day)

    def test_entry_submission_does_not_read_fill_day_eod_chain(self):
        chains_by_day = {
            self.signal_day: _chain(1.20, 1.30, 0.60, 0.64),
            self.fill_day: _chain(1.50, 1.60, 0.65, 0.70),
            "2022-06-03": _chain(1.50, 1.60, 0.65, 0.70),
        }
        strategy = _run_cached_backtest(
            chains_by_day,
            datetime(2022, 6, 4),
            forbidden_strategy_chain_days={self.fill_day},
        )
        position = strategy._spreads["SYN"]
        self.assertEqual(position.entry_decision_date, self.signal_day)
        self.assertEqual(position.entry_fill_date, self.fill_day)
        self.assertAlmostEqual(position.entry_credit, 0.77, places=2)


class PointInTimeFeedAvailabilityTests(unittest.TestCase):
    def test_future_delta_admission_cannot_create_an_earlier_fill(self):
        def with_driver(frame):
            driver = frame.iloc[[0]].copy()
            driver["strike"] = 80.0
            driver["bid"] = 5.00
            driver["ask"] = 5.20
            driver["delta"] = -0.65
            return pd.concat([frame, driver], ignore_index=True)

        out_of_band = with_driver(
            _chain(
                1.20,
                1.30,
                0.60,
                0.64,
                short_delta=-0.02,
                long_delta=-0.015,
            )
        )
        future_admission = with_driver(_chain(1.20, 1.30, 0.60, 0.64))
        with self.assertRaisesRegex(
            RuntimeError, "frozen entry leg.*missing from the offline feed"
        ):
            _run_cached_backtest(
                {
                    "2022-06-01": out_of_band,
                    "2022-06-02": out_of_band,
                    "2022-06-03": future_admission,
                },
                datetime(2022, 6, 3),
            )


class CausalExitFillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        entry = _chain(1.20, 1.30, 0.60, 0.64)
        trigger = _chain(0.20, 0.24, 0.05, 0.07)
        next_close = _chain(0.30, 0.34, 0.10, 0.12)
        cls.strategy = _run_cached_backtest(
            {
                "2022-06-01": entry,
                "2022-06-02": entry,
                "2022-06-03": trigger,
                "2022-06-06": next_close,
                "2022-06-07": next_close,
                "2022-06-08": next_close,
            },
            datetime(2022, 6, 9),
        )

    def test_exit_trigger_fills_at_next_session_close(self):
        trade = self.strategy.closed_trades[0]
        # Entry credit 0.53; D+1 exit debit 0.35 - 0.09 = 0.26; four
        # contracts; $2.60 round-trip commission per spread.
        self.assertAlmostEqual(trade["pnl"], 97.60, places=2)
        self.assertEqual(trade["exit_decision_date"], "2022-06-03")
        self.assertEqual(trade["exit_date"], "2022-06-06")

    def test_final_session_trigger_records_terminal_conservative_mark(self):
        expiration = "2023-02-03"
        entry = _chain(1.20, 1.30, 0.60, 0.64, expiration=expiration)
        trigger = _chain(0.20, 0.24, 0.05, 0.07, expiration=expiration)

        strategy = _run_cached_backtest(
            {
                "2022-12-28": entry,
                "2022-12-29": entry,
                "2022-12-30": trigger,
            },
            datetime(2022, 12, 31),
        )

        self.assertEqual(strategy._spreads, {})
        self.assertEqual(len(strategy.closed_trades), 1)
        trade = strategy.closed_trades[0]
        self.assertEqual(trade["exit_decision_date"], "2022-12-30")
        self.assertEqual(trade["exit_date"], "2022-12-30")
        self.assertAlmostEqual(trade["pnl"], 117.60, places=2)
        self.assertEqual(
            trade["exit_execution"],
            "terminal_conservative_mark",
        )


if __name__ == "__main__":
    unittest.main()

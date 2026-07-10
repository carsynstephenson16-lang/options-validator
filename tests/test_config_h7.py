"""Freeze-integrity: config H7 values must match the ledger registration
(experiments.jsonl trial_intent f1887c9d..., amendment e266770f...). A red
test here means someone edited a frozen number without a ledger amendment."""

import unittest

import config


class TestH7Freeze(unittest.TestCase):
    def test_universe_and_lanes(self):
        self.assertEqual(
            config.H7_WATCHLIST,
            ["CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO"],
        )
        self.assertEqual(config.H7_CORE_LONG_ONLY, ["VST", "CEG", "MSFT", "AMZN"])
        self.assertEqual(config.H7_EXCLUDED, ["HYLN"])

    def test_entry_thresholds(self):
        self.assertEqual(config.H7A_DRAWDOWN_MIN, 0.25)
        self.assertEqual(config.H7A_RECLAIM_LOOKBACK_D, 20)
        self.assertEqual(config.H7B_RANGE_MAX, 0.15)
        self.assertEqual(config.H7B_RANGE_LOOKBACK_D, 60)
        self.assertEqual(config.H7B_RV_PCTILE_MAX, 0.25)
        self.assertEqual(config.H7_IV_CHEAP_K, 1.00)
        self.assertEqual(config.H7_IV_PAR_K, 1.15)
        self.assertEqual(config.H7_IV_RICH_K, 1.25)
        self.assertEqual(config.H7_RV_LOOKBACK_D, 21)

    def test_structures_and_exits(self):
        self.assertEqual(config.H7_LONG_DELTA_BAND, (0.55, 0.70))
        self.assertEqual(config.H7_LONG_DTE_BAND, (60, 120))
        self.assertEqual(config.H7_SPREAD_LONG_DELTA, 0.60)
        self.assertEqual(config.H7_SPREAD_SHORT_DELTA, 0.25)
        self.assertEqual(config.H7_LONG_TP_PCT, 1.00)
        self.assertEqual(config.H7_SPREAD_TP_FRAC_MAX, 0.75)
        self.assertEqual(config.H7_CLOSE_AT_DTE, 30)
        self.assertEqual(config.H7C_SHORT_DELTA_MAX, 0.30)
        self.assertEqual(config.H7C_DTE_BAND, (30, 45))
        self.assertEqual(config.H7C_CREDIT_FLOOR_FRAC, 0.30)
        self.assertEqual(config.H7C_WIDTH_FRAC_OF_SPOT, 0.10)
        self.assertEqual(config.H7C_TP_FRAC, 0.50)
        self.assertEqual(config.H7C_STOP_CREDIT_MULT, 2.0)
        self.assertEqual(config.H7C_MAX_CONCURRENT, 1)

    def test_sizing_admission_and_verdict(self):
        self.assertEqual(config.H7_MONTHLY_AT_RISK, 6000)
        self.assertEqual(config.H7_MAX_OPEN_PER_UNDERLYING, 1)
        self.assertEqual(config.H7_ADMIT_MIN_CONTRACTS, 5)
        self.assertEqual(config.H7_ADMIT_MAX_SPREAD_PCT, 0.05)
        self.assertEqual(config.H7_EARNINGS_BAN_SESSIONS, 5)
        self.assertEqual(
            config.H7_BACKTEST_SYMBOLS,
            ["NOW", "NVDA", "PLTR", "MSFT", "AMZN", "VST", "CEG", "SMCI"],
        )
        self.assertEqual(config.H7_BACKTEST_START, "2018-01-02")
        self.assertEqual(config.H7_BACKTEST_END, "2026-06-30")

    def test_v1_2_amendment_constants(self):
        # ledger H7_AMENDMENT_V1_2 (f880b4d1...), owner-ratified 2026-07-10
        self.assertEqual(config.H7C_CLOSE_AT_DTE, 7)
        self.assertEqual(config.H7_DELTA_TOLERANCE, 0.07)
        self.assertEqual(config.H7_LANE_PRIORITY, ("a", "b", "c"))
        self.assertEqual(config.H7C_TIEBREAK, "credit_to_width")

    def test_previously_hardcoded_registered_numbers(self):
        self.assertEqual(config.H7_IV_TENOR_DTE_BAND, (72, 108))
        self.assertEqual(config.H7_NTM_BAND, 0.10)
        self.assertEqual(config.H7_DD_LOOKBACK_D, 252)
        self.assertEqual(config.H7B_RV_WINDOW_D, 20)
        self.assertEqual(config.H7B_RV_HISTORY_D, 252)
        self.assertEqual(config.H7B_RV_MIN_HISTORY_D, 106)
        self.assertEqual(config.H7_EARNINGS_KNOWN_HORIZON_D, 45)

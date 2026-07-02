import unittest
import tempfile
from pathlib import Path

import config
from analysis.feasibility import (
    ASSUMED_CREDIT_FRAC,
    contracts_that_fit,
    max_loss_per_spread,
)
import pandas as pd

from data import thetadata_adapter
from data.thetadata_adapter import mid_price, passes_liquidity
from metrics import scoreboard
from strategies.base import (
    capital_at_risk_per_spread,
    economic_max_loss_per_spread,
    entry_credit_conservative,
    round_trip_commission_per_spread,
    size_defined_risk,
)


class PricingAndSizingTests(unittest.TestCase):
    def test_conservative_credit_is_worse_than_mid_credit(self):
        mid_credit = mid_price(1.00, 1.20) - mid_price(0.30, 0.40)
        conservative = entry_credit_conservative(1.00, 1.20, 0.30, 0.40)

        self.assertLess(conservative, mid_credit)

    def test_conservative_credit_crosses_bid_ask_then_haircuts(self):
        credit = entry_credit_conservative(1.00, 1.20, 0.30, 0.40)

        expected = 1.00 * (1 - config.SLIPPAGE_HAIRCUT) - 0.40 * (
            1 + config.SLIPPAGE_HAIRCUT
        )
        self.assertAlmostEqual(credit, expected)

    def test_conservative_credit_rejects_invalid_quotes(self):
        with self.assertRaises(ValueError):
            entry_credit_conservative(1.20, 1.00, 0.30, 0.40)

    def test_defined_risk_sizing_never_rounds_up(self):
        contracts, economic_max_loss = size_defined_risk(width=5, net_credit=1.50)

        self.assertAlmostEqual(economic_max_loss, 352.60)
        self.assertEqual(contracts, int((config.RISK_SLEEVE * config.RISK_PER_TRADE) // 352.60))

    def test_round_trip_commission_per_spread_counts_two_legs_each_way(self):
        self.assertAlmostEqual(round_trip_commission_per_spread(), 2.60)

    def test_economic_max_loss_adds_commissions_to_margin(self):
        self.assertAlmostEqual(capital_at_risk_per_spread(width=2, net_credit=0.60), 140.0)
        self.assertAlmostEqual(economic_max_loss_per_spread(width=2, net_credit=0.60), 142.60)

    def test_two_wide_zero_slack_gross_fit_is_rejected_on_economic_risk(self):
        contracts, economic_max_loss = size_defined_risk(width=2, net_credit=0.60)

        self.assertAlmostEqual(economic_max_loss, 142.60)
        self.assertEqual(contracts, 0)

    def test_impossible_vertical_credit_fails_closed(self):
        contracts, economic_max_loss = size_defined_risk(width=2, net_credit=2.00)

        self.assertEqual(contracts, 0)
        self.assertEqual(economic_max_loss, float("inf"))


class LiquidityTests(unittest.TestCase):
    def test_rejects_crossed_or_invalid_quotes(self):
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, 1.10, 1.00))
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, -0.01, 1.00))
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, 0.00, 0.00))

    def test_accepts_tight_quote_with_enough_open_interest(self):
        self.assertTrue(passes_liquidity(config.MIN_OPEN_INTEREST, 1.00, 1.05))


class ChainCacheTests(unittest.TestCase):
    def _valid_chain(self):
        return pd.DataFrame([{
            "expiration": "2022-02-18",
            "strike": 390.0,
            "right": "P",
            "bid": 1.00,
            "ask": 1.05,
            "open_interest": 500,
            "iv": 0.25,
            "delta": -0.30,
            "gamma": 0.02,
            "theta": -0.04,
            "vega": 0.12,
        }])

    def test_cache_path_rejects_unsafe_symbol_or_date(self):
        with self.assertRaises(ValueError):
            thetadata_adapter._cache_path("../SPY", "2022-01-03")
        with self.assertRaises(ValueError):
            thetadata_adapter._cache_path("SPY", "2022-99-99")

    def test_cached_chain_must_match_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cache = thetadata_adapter.CACHE_DIR
            try:
                thetadata_adapter.CACHE_DIR = Path(tmp)
                bad = self._valid_chain().drop(columns=["delta"])
                bad.to_parquet(thetadata_adapter._cache_path("SPY", "2022-01-03"))

                with self.assertRaises(ValueError):
                    thetadata_adapter.get_eod_chain("SPY", "2022-01-03")
            finally:
                thetadata_adapter.CACHE_DIR = old_cache

    def test_valid_cached_chain_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cache = thetadata_adapter.CACHE_DIR
            try:
                thetadata_adapter.CACHE_DIR = Path(tmp)
                self._valid_chain().to_parquet(
                    thetadata_adapter._cache_path("spy", "2022-01-03")
                )

                out = thetadata_adapter.get_eod_chain("SPY", "2022-01-03")
            finally:
                thetadata_adapter.CACHE_DIR = old_cache

        self.assertEqual(list(out.columns), thetadata_adapter.CHAIN_COLUMNS)
        self.assertEqual(out.iloc[0]["right"], "P")


class ChainMergeTests(unittest.TestCase):
    """Pin the offline-testable half of the ThetaData fetch: the four
    per-contract frames must merge into a valid CHAIN_COLUMNS chain,
    fail-closed on gaps, and fail loud on unexpected column names."""

    def _frames(self, n=3):
        base = {
            "expiration": ["2022-02-18"] * n,
            "strike": [380.0 + 5 * i for i in range(n)],
            "right": ["put"] * n,
        }
        eod = pd.DataFrame({**base,
                            "bid": [1.00 + i for i in range(n)],
                            "ask": [1.10 + i for i in range(n)]})
        greeks = pd.DataFrame({**base, "delta": [-0.30] * n, "gamma": [0.02] * n,
                               "theta": [-0.04] * n, "vega": [0.12] * n})
        iv = pd.DataFrame({**base, "implied_volatility": [0.25] * n})
        oi = pd.DataFrame({**base, "open_interest": [500] * n})
        return eod, greeks, iv, oi

    def test_merge_produces_valid_chain_and_normalizes_rights(self):
        chain = thetadata_adapter._merge_chain_frames(*self._frames())

        self.assertEqual(list(chain.columns), thetadata_adapter.CHAIN_COLUMNS)
        self.assertEqual(set(chain["right"]), {"P"})
        thetadata_adapter.validate_chain_schema(chain)

    def test_merge_drops_contracts_missing_open_interest(self):
        eod, greeks, iv, oi = self._frames(3)

        chain = thetadata_adapter._merge_chain_frames(eod, greeks, iv, oi.iloc[:2])

        self.assertEqual(len(chain), 2)

    def test_merge_keeps_last_report_per_contract(self):
        eod, greeks, iv, _ = self._frames(1)
        oi = pd.DataFrame({
            "expiration": ["2022-02-18"] * 2,
            "strike": [380.0] * 2,
            "right": ["put"] * 2,
            "timestamp": ["2022-01-03T10:00:00", "2022-01-03T16:00:00"],
            "open_interest": [100, 700],
        })

        chain = thetadata_adapter._merge_chain_frames(eod, greeks, iv, oi)

        self.assertEqual(chain.iloc[0]["open_interest"], 700)

    def test_merge_fails_loud_when_quote_columns_missing(self):
        eod, greeks, iv, oi = self._frames(1)

        with self.assertRaisesRegex(ValueError, r"none of.*bid"):
            thetadata_adapter._merge_chain_frames(
                eod.drop(columns=["bid", "ask"]), greeks, iv, oi)


class OOSTouchGuardTests(unittest.TestCase):
    """Spec Unit 4: 'just printing a chain' after IN_SAMPLE_END is a holdout
    look. The adapter refuses post-2022 dates -- even cached ones -- unless the
    OOS reveal gate passes allow_oos=True."""

    def _valid_chain(self):
        return pd.DataFrame([{
            "expiration": "2023-02-17", "strike": 390.0, "right": "P",
            "bid": 1.00, "ask": 1.05, "open_interest": 500, "iv": 0.25,
            "delta": -0.30, "gamma": 0.02, "theta": -0.04, "vega": 0.12,
        }])

    def test_post_in_sample_chain_refused_without_gate(self):
        with self.assertRaises(thetadata_adapter.OOSDataTouchError):
            thetadata_adapter.get_eod_chain("SPY", "2023-01-05")

    def test_even_cached_post_in_sample_chain_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_cache = thetadata_adapter.CACHE_DIR
            try:
                thetadata_adapter.CACHE_DIR = Path(tmp)
                self._valid_chain().to_parquet(
                    thetadata_adapter._cache_path("SPY", "2023-01-05"))

                with self.assertRaises(thetadata_adapter.OOSDataTouchError):
                    thetadata_adapter.get_eod_chain("SPY", "2023-01-05")

                gated = thetadata_adapter.get_eod_chain(
                    "SPY", "2023-01-05", allow_oos=True)
            finally:
                thetadata_adapter.CACHE_DIR = old_cache

        self.assertEqual(len(gated), 1)

class ScoreboardTests(unittest.TestCase):
    def test_scoreboard_requires_capital_at_risk(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 12.0}])

    def test_scoreboard_rejects_zero_capital_at_risk(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 12.0, "capital_at_risk": 0.0,
                         "entry_date": "2021-01-04", "symbol": "SPY"}])

    def test_loss_count_gate_blocks_thin_short_vol_sample(self):
        trades = [
            {"pnl": 20.0, "capital_at_risk": 100.0, "entry_date": "2021-01-04", "symbol": "SPY"},
            {"pnl": 15.0, "capital_at_risk": 100.0, "entry_date": "2021-01-11", "symbol": "SPY"},
            {"pnl": -70.0, "capital_at_risk": 100.0, "entry_date": "2021-01-19", "symbol": "SPY"},
        ]

        result = scoreboard(trades)

        self.assertEqual(result["n_losses"], 1)
        self.assertIn("INSUFFICIENT SAMPLE", result["verdict"])

    def test_scoreboard_rejects_is_win_contradicting_net_pnl(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": -12.0, "capital_at_risk": 100.0,
                         "entry_date": "2021-01-04", "symbol": "SPY",
                         "is_win": True}])

    def test_flat_trades_do_not_satisfy_loss_floor(self):
        trades = [
            {"pnl": 40.0, "capital_at_risk": 100.0,
             "entry_date": f"2021-{month:02d}-01", "symbol": "SPY"}
            for month in range(1, 7)
        ] + [
            {"pnl": 0.0, "capital_at_risk": 100.0,
             "entry_date": f"2022-{month:02d}-01", "symbol": "SPY"}
            for month in range(1, config.MIN_LOSSES_FOR_VERDICT + 1)
        ]

        result = scoreboard(trades)

        self.assertEqual(result["n_losses"], 0)
        self.assertIn("INSUFFICIENT SAMPLE", result["verdict"])

    def test_scoreboard_reports_secondary_economic_max_loss_return(self):
        trades = [
            {"pnl": 10.0, "capital_at_risk": 100.0, "economic_max_loss": 110.0,
             "entry_date": "2021-01-04", "symbol": "SPY"},
            {"pnl": 20.0, "capital_at_risk": 100.0, "economic_max_loss": 110.0,
             "entry_date": "2021-01-11", "symbol": "SPY"},
        ]

        result = scoreboard(trades)

        self.assertAlmostEqual(result["return_on_economic_max_loss"], 30.0 / 110.0)

    def test_scoreboard_rejects_partial_economic_max_loss(self):
        trades = [
            {"pnl": 10.0, "capital_at_risk": 100.0, "economic_max_loss": 110.0,
             "entry_date": "2021-01-04", "symbol": "SPY"},
            {"pnl": 20.0, "capital_at_risk": 100.0,
             "entry_date": "2021-01-11", "symbol": "SPY"},
        ]

        with self.assertRaises(ValueError):
            scoreboard(trades)

    def test_scoreboard_rejects_economic_max_loss_below_margin(self):
        with self.assertRaises(ValueError):
            scoreboard([{"pnl": 12.0, "capital_at_risk": 100.0,
                         "economic_max_loss": 99.0,
                         "entry_date": "2021-01-04", "symbol": "SPY"}])


class HonestSleeveConfigTests(unittest.TestCase):
    """Locks the decided CAPITAL-HONEST config: $14k sleeve, $2-wide.

    IMPORTANT: these preserve the original gross-feasibility fact under the
    current ASSUMED_CREDIT_FRAC. Runtime sizing now gates on economic max loss,
    so the $2-wide zero-slack gross fit is correctly rejected once commissions
    are included.
    """

    def _gross_max_loss(self, width):
        return max_loss_per_spread(width, ASSUMED_CREDIT_FRAC * width)

    def _contracts_for_width(self, width):
        budget = config.RISK_SLEEVE * config.RISK_PER_TRADE
        return contracts_that_fit(budget, self._gross_max_loss(width))

    def test_sleeve_is_capital_honest_fourteen_k(self):
        self.assertEqual(config.RISK_SLEEVE, 14_000)

    def test_configured_width_is_two(self):
        self.assertEqual(config.A_SPREAD_WIDTH, 2)

    def test_two_wide_is_a_zero_slack_gross_threshold_fit(self):
        # Per-trade budget exactly equals the $2-wide GROSS max loss: zero
        # slack. Commissions / worse real fills push true risk over budget.
        budget = config.RISK_SLEEVE * config.RISK_PER_TRADE
        self.assertEqual(self._gross_max_loss(2), budget)  # exact knife-edge
        self.assertEqual(self._contracts_for_width(2), 1)  # gross threshold fit

    def test_five_wide_does_not_fit_the_honest_sleeve(self):
        self.assertEqual(self._contracts_for_width(5), 0)

    def test_fourteen_k_is_a_feasibility_candidate(self):
        self.assertIn(14_000, config.RISK_SLEEVE_CANDIDATES)


if __name__ == "__main__":
    unittest.main()

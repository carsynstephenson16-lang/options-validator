import unittest

import config
from analysis.feasibility import (
    ASSUMED_CREDIT_FRAC,
    contracts_that_fit,
    max_loss_per_spread,
)
from data.thetadata_adapter import mid_price, passes_liquidity
from metrics import scoreboard
from strategies.base import entry_credit_conservative, size_defined_risk


class PricingAndSizingTests(unittest.TestCase):
    def test_conservative_credit_is_worse_than_mid_credit(self):
        mid_credit = mid_price(1.00, 1.20) - mid_price(0.30, 0.40)
        conservative = entry_credit_conservative(1.00, 1.20, 0.30, 0.40)

        self.assertLess(conservative, mid_credit)

    def test_defined_risk_sizing_never_rounds_up(self):
        contracts, max_loss = size_defined_risk(width=5, net_credit=1.50)

        self.assertEqual(max_loss, 350.0)
        self.assertEqual(contracts, int((config.RISK_SLEEVE * config.RISK_PER_TRADE) // 350))


class LiquidityTests(unittest.TestCase):
    def test_rejects_crossed_or_invalid_quotes(self):
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, 1.10, 1.00))
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, -0.01, 1.00))
        self.assertFalse(passes_liquidity(config.MIN_OPEN_INTEREST, 0.00, 0.00))

    def test_accepts_tight_quote_with_enough_open_interest(self):
        self.assertTrue(passes_liquidity(config.MIN_OPEN_INTEREST, 1.00, 1.05))


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


class HonestSleeveConfigTests(unittest.TestCase):
    """Locks the decided CAPITAL-HONEST config: $14k sleeve, $2-wide.

    IMPORTANT: these assert GROSS feasibility only, under the current
    ASSUMED_CREDIT_FRAC. $2-wide is a ZERO-SLACK gross threshold, NOT a robust
    all-in fit: the sizing formula excludes commissions and assumes the 30%
    credit holds, so true all-in risk can exceed budget. Do not read a passing
    test here as "$2-wide is safe to trade." See spec
    2026-07-01-reproducible-foundation-design.md.
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

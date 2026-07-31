"""Honesty tests for closed-trade capital-use summary metrics."""

import unittest

from metrics import scoreboard


def _trade(pnl, entry_date, exit_date=None):
    trade = {
        "pnl": pnl,
        "capital_at_risk": 110.0,
        "entry_date": entry_date,
        "symbol": "VST",
    }
    if exit_date is not None:
        trade["exit_date"] = exit_date
    return trade


class CapitalFamilyTests(unittest.TestCase):
    def test_concurrent_and_sequential_trades_distinguish_peak_capital_return(self):
        concurrent = [
            _trade(11.0, "2024-01-02", "2024-01-12"),
            _trade(11.0, "2024-01-03", "2024-01-11"),
        ]
        sequential = [
            _trade(11.0, "2024-01-02", "2024-01-10"),
            _trade(11.0, "2024-01-11", "2024-01-19"),
        ]

        concurrent_result = scoreboard(concurrent)
        sequential_result = scoreboard(sequential)

        self.assertAlmostEqual(concurrent_result["trade_weighted_return_on_risk"], 22.0 / 220.0)
        self.assertAlmostEqual(sequential_result["trade_weighted_return_on_risk"], 22.0 / 220.0)
        self.assertAlmostEqual(
            concurrent_result["capital_day_efficiency"], 22.0 / (110.0 * 11 + 110.0 * 9)
        )
        self.assertNotEqual(
            concurrent_result["peak_capital_return"],
            sequential_result["peak_capital_return"],
        )
        self.assertAlmostEqual(concurrent_result["peak_capital_return"], 22.0 / 220.0)
        self.assertAlmostEqual(sequential_result["peak_capital_return"], 22.0 / 110.0)

    def test_more_identical_trades_do_not_inflate_trade_weighted_return_on_risk(self):
        one_trade = [_trade(11.0, "2024-01-02")]
        three_trades = [
            _trade(11.0, "2024-01-02"),
            _trade(11.0, "2024-01-09"),
            _trade(11.0, "2024-01-16"),
        ]

        one_result = scoreboard(one_trade)
        three_result = scoreboard(three_trades)

        self.assertAlmostEqual(one_result["trade_weighted_return_on_risk"], 0.10)
        self.assertAlmostEqual(three_result["trade_weighted_return_on_risk"], 0.10)

    def test_first_losing_trade_has_nonzero_closed_trade_pnl_drawdown(self):
        result = scoreboard([_trade(-25.0, "2024-01-02")])

        self.assertEqual(result["closed_trade_pnl_drawdown"], 25.0)

    def test_time_based_metrics_are_omitted_without_all_exit_dates(self):
        result = scoreboard(
            [
                _trade(11.0, "2024-01-02", "2024-01-12"),
                _trade(11.0, "2024-01-16"),
            ]
        )

        self.assertNotIn("capital_day_efficiency", result)
        self.assertNotIn("peak_capital_return", result)


if __name__ == "__main__":
    unittest.main()

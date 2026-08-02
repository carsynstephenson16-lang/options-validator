import unittest
from datetime import date

import pandas as pd

import config
from data import pandas_feed
from strategies.base import (
    adverse_buy,
    adverse_sell,
    economic_max_loss_per_spread,
    entry_credit_conservative,
    size_defined_risk,
)
from strategies.put_credit_spread import select_put_credit_spread_candidate


def _vertical_chain(
    short_bid: float,
    short_ask: float,
    long_bid: float,
    long_ask: float,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "expiration": "2022-07-08",
                "strike": 100.0,
                "right": "P",
                "bid": short_bid,
                "ask": short_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": -0.30,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
            {
                "expiration": "2022-07-08",
                "strike": 98.0,
                "right": "P",
                "bid": long_bid,
                "ask": long_ask,
                "open_interest": 500,
                "iv": 0.25,
                "delta": -0.25,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.10,
            },
        ]
    )


class CanonicalPricingTests(unittest.TestCase):
    def test_penny_rounding_prevents_exact_602_40_cap_breach(self):
        credit = entry_credit_conservative(1.05, 1.05, 0.50, 0.50, haircut=0.01)
        contracts, _ = size_defined_risk(width=2.0, net_credit=credit)
        executable_credit = adverse_sell(1.05, 0.01) - adverse_buy(0.50, 0.01)
        executable_loss = economic_max_loss_per_spread(2.0, executable_credit)

        self.assertEqual(executable_credit, 0.52)
        self.assertEqual(executable_loss, 150.60)
        self.assertEqual(contracts, 3)
        self.assertLessEqual(contracts * executable_loss, config.MAX_LOSS_PER_TRADE)

    def test_price_grid_sizing_never_breaches_cap_after_executable_rounding(self):
        width = 2.0
        haircut = 0.01

        for short_bid_cents in range(1, 501):
            short_bid = short_bid_cents / 100.0
            for long_ask_cents in range(1, 501):
                long_ask = long_ask_cents / 100.0
                selection_credit = entry_credit_conservative(
                    short_bid,
                    short_bid,
                    long_ask,
                    long_ask,
                    haircut=haircut,
                )
                contracts, _ = size_defined_risk(width, selection_credit)
                executable_credit = adverse_sell(short_bid, haircut) - adverse_buy(
                    long_ask, haircut
                )
                executable_loss = economic_max_loss_per_spread(
                    width, executable_credit
                )
                actual_risk = contracts * executable_loss
                if actual_risk > config.MAX_LOSS_PER_TRADE:
                    self.fail(
                        "cap breached at "
                        f"short_bid={short_bid:.2f}, long_ask={long_ask:.2f}: "
                        f"{contracts} * {executable_loss:.2f} = {actual_risk:.2f}"
                    )

    def test_selector_credit_equals_engine_fill_credit_for_same_quotes(self):
        chain = _vertical_chain(1.05, 1.10, 0.46, 0.50)
        selection = select_put_credit_spread_candidate(
            chain,
            date(2022, 6, 1),
            width=2.0,
            delta=0.30,
            dte_band=config.A_TARGET_DTE,
            haircut=0.01,
        )
        feed = pandas_feed.build_option_data(
            {"2022-06-01": chain},
            "SYN",
            exp_max="2022-07-08",
            haircut=0.01,
        )
        short_asset = pandas_feed.option_asset("SYN", "2022-07-08", 100.0)
        long_asset = pandas_feed.option_asset("SYN", "2022-07-08", 98.0)
        engine_fill_credit = (
            feed[short_asset].df.iloc[0]["bid"]
            - feed[long_asset].df.iloc[0]["ask"]
        )

        self.assertTrue(selection.accepted)
        self.assertEqual(selection.credit, engine_fill_credit)


if __name__ == "__main__":
    unittest.main()

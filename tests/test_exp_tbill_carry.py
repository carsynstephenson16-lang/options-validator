import math
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import config
from data.rates import MissingRateError
from options_researcher import exp_tbill_carry as exp_tbill_module
from options_researcher.exp_tbill_carry import (
    build_exp_tbill_board,
    early_assignment_flag,
    exp_tbill_carry,
)


def contract_row(*, bid=1.0, ask=3.0, strike=100.0, expiration="2026-08-26"):
    return {
        "bid": bid,
        "ask": ask,
        "strike": strike,
        "expiration": expiration,
    }


def chain_frame(*, bid=1.0, ask=3.0, expiration="2026-08-21"):
    return pd.DataFrame(
        [
            {
                "right": "P",
                "bid": bid,
                "ask": ask,
                "strike": 100.0,
                "expiration": expiration,
                "delta": -0.50,
            }
        ]
    )


def rate_result(
    rate=math.log1p(0.05),
    source_date=date(2026, 7, 23),
    valid_through=date(2026, 7, 27),
):
    return SimpleNamespace(
        rate=rate,
        source_date=source_date,
        provenance=SimpleNamespace(
            source_url="https://home.treasury.gov/example",
            captured_at_utc="2026-07-28T01:00:00+00:00",
            valid_through=valid_through,
        ),
    )


class TestAssignmentStub(unittest.TestCase):
    def test_assignment_stub_always_blocked_red(self):
        cases = (
            (),
            ("VST",),
            ({"dividend_yield": 0.08, "days_to_ex_dividend": 1},),
            (200.0, 150.0, "deep-in-the-money dividend capture setup"),
        )
        for args in cases:
            with self.subTest(args=args):
                result = early_assignment_flag(*args, dividend_capture=True)
                self.assertEqual(
                    result,
                    {
                        "state": "DATA_BLOCKED",
                        "reason": "EX_DIV_DATE_UNAVAILABLE",
                        "unlock": "owner-sourced forward ex-dividend date calendar",
                    },
                )
                self.assertNotIn("verdict", result)
                self.assertNotIn("probability", result)


class TestCarryMath(unittest.TestCase):
    def test_module_defaults_match_composite_convention(self):
        self.assertEqual(exp_tbill_module.EXP_TBILL_TENOR_DTE, (15, 60))
        self.assertEqual(exp_tbill_module.EXP_TBILL_TARGET_DELTA, 0.50)

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_key_contract(self, mocked_rate):
        mocked_rate.return_value = rate_result()
        result = exp_tbill_carry(
            contract_row(),
            105.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        self.assertEqual(
            set(result),
            {
                "experiment_id",
                "state",
                "data_blocked",
                "reason",
                "asof",
                "max_asof",
                "credit_mid",
                "collateral",
                "credit_annualized_yield",
                "tbill_annualized_yield",
                "carry_spread",
                "opportunity_cost",
                "rate_provenance",
                "assignment",
                "caveat",
            },
        )

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_occ_opportunity_cost_hand_computed(self, mocked_rate):
        continuous_rate = math.log1p(0.05)
        mocked_rate.return_value = rate_result(continuous_rate)
        result = exp_tbill_carry(
            contract_row(strike=200.0),
            205.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        expected = 20_000.0 * (math.exp(continuous_rate * 30.0 / 365.0) - 1.0)
        self.assertAlmostEqual(result["opportunity_cost"], expected, delta=1e-6)

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_carry_spread_sign_states(self, mocked_rate):
        mocked_rate.return_value = rate_result()
        above = exp_tbill_carry(
            contract_row(bid=4.0, ask=6.0),
            105.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        below = exp_tbill_carry(
            contract_row(bid=0.05, ask=0.15),
            105.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        self.assertEqual(above["state"], "ABOVE_TBILL")
        self.assertGreater(above["carry_spread"], 0.0)
        self.assertEqual(below["state"], "BELOW_TBILL")
        self.assertLess(below["carry_spread"], 0.0)

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_missing_rate_blocked_via_loader(self, mocked_rate):
        message = "no Treasury curve known by valuation close for 2026-07-27"
        mocked_rate.side_effect = MissingRateError(message)
        result = exp_tbill_carry(
            contract_row(),
            105.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertTrue(result["data_blocked"])
        self.assertEqual(result["reason"], message)
        self.assertIsNone(result["credit_mid"])

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_invalid_reference_quotes_blocked(self, mocked_rate):
        for bid, ask in ((0.0, 1.0), (2.0, 1.0), (-2.0, 1.0)):
            with self.subTest(bid=bid, ask=ask):
                result = exp_tbill_carry(
                    contract_row(bid=bid, ask=ask),
                    105.0,
                    symbol="VST",
                    asof="2026-07-27",
                    expiration="2026-08-26",
                )
                self.assertEqual(result["state"], "DATA_BLOCKED")
                self.assertEqual(result["reason"], "invalid reference quote")
                self.assertIsNone(result["credit_annualized_yield"])
        mocked_rate.assert_not_called()

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    def test_mid_quote_used_not_bid_or_ask(self, mocked_rate):
        mocked_rate.return_value = rate_result(0.0)
        result = exp_tbill_carry(
            contract_row(bid=1.0, ask=3.0),
            105.0,
            symbol="VST",
            asof="2026-07-27",
            expiration="2026-08-26",
        )
        self.assertEqual(result["credit_mid"], 2.0)
        self.assertAlmostEqual(result["credit_annualized_yield"], 2.0 * 365 / 3000)
        self.assertIn("mid or worse", result["caveat"])

    def test_no_lookahead_rates_gate(self):
        message = "no Treasury curve known by valuation close for 2026-08-10"
        result = exp_tbill_carry(
            contract_row(expiration="2026-09-18"),
            105.0,
            symbol="VST",
            asof="2026-08-10",
            expiration="2026-09-18",
        )
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertEqual(result["reason"], message)


class TestBoard(unittest.TestCase):
    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    @patch("options_researcher.exp_tbill_carry.load_closes")
    @patch("options_researcher.exp_tbill_carry.load_range")
    @patch("options_researcher.exp_tbill_carry._latest_cached_session")
    def test_spot_session_matches_chain_session(
        self, latest_session, mocked_load_range, mocked_load_closes, mocked_rate
    ):
        latest_session.return_value = "2026-07-25"
        mocked_load_range.return_value = {"2026-07-25": chain_frame(expiration="2026-08-21")}
        observed = {}

        def load_spot(symbol, start, end, *, allow_oos=False):
            observed.update(symbol=symbol, start=start, end=end, allow_oos=allow_oos)
            return pd.Series([105.0], index=[end])

        mocked_load_closes.side_effect = load_spot
        mocked_rate.return_value = rate_result(valid_through=date(2026, 7, 24))

        result = build_exp_tbill_board(["VST"], asof="2026-07-27")[0]

        self.assertFalse(result["data_blocked"])
        self.assertEqual(result["asof"], "2026-07-25")
        self.assertEqual(result["max_asof"], "2026-07-23")
        self.assertEqual(result["symbol"], "VST")
        self.assertEqual(
            observed,
            {
                "symbol": "VST",
                "start": "2018-01-01",
                "end": "2026-07-25",
                "allow_oos": True,
            },
        )

    @patch("options_researcher.exp_tbill_carry.load_range")
    @patch("options_researcher.exp_tbill_carry._latest_cached_session")
    def test_no_reference_put_blocked(self, latest_session, mocked_load_range):
        latest_session.return_value = "2026-07-25"
        mocked_load_range.return_value = {"2026-07-25": pd.DataFrame()}
        result = build_exp_tbill_board(["VST"], asof="2026-07-27")[0]
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertEqual(result["symbol"], "VST")
        self.assertEqual(result["reason"], "no valid reference put")

    @patch("options_researcher.exp_tbill_carry._latest_cached_session")
    def test_board_blocked_card(self, latest_session):
        latest_session.return_value = None
        result = build_exp_tbill_board(["VST"], asof="2026-07-27")[0]
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertEqual(result["symbol"], "VST")
        self.assertEqual(result["reason"], "no cached chain for the as-of session")
        self.assertEqual(result["assignment"], early_assignment_flag())

    @patch("options_researcher.exp_tbill_carry.risk_free_rate")
    @patch("options_researcher.exp_tbill_carry.load_closes")
    @patch("options_researcher.exp_tbill_carry.load_range")
    @patch("options_researcher.exp_tbill_carry._latest_cached_session")
    def test_builder_uses_frozen_module_constants(
        self, latest_session, mocked_load_range, mocked_load_closes, mocked_rate
    ):
        latest_session.return_value = "2026-07-25"
        mocked_load_range.return_value = {"2026-07-25": chain_frame()}
        mocked_load_closes.return_value = pd.Series([105.0], index=["2026-07-25"])
        mocked_rate.return_value = rate_result()
        with (
            patch.object(exp_tbill_module, "EXP_TBILL_TENOR_DTE", (30, 60)),
            patch.object(exp_tbill_module, "EXP_TBILL_TARGET_DELTA", 0.25),
        ):
            result = build_exp_tbill_board(["VST"], asof="2026-07-27")[0]
        self.assertEqual(result["state"], "DATA_BLOCKED")
        self.assertEqual(result["reason"], "no valid reference put")

    def test_real_cache_board_has_at_least_one_unblocked_name_when_available(self):
        cache = Path(".cache/chains")
        if not cache.exists() or not any(cache.glob("*.parquet")):
            self.skipTest("real chain cache is not mounted in this worktree")
        board = build_exp_tbill_board(config.ATTRACTIVENESS_UNIVERSE, asof="2026-07-27")
        self.assertTrue(
            any(not card["data_blocked"] for card in board),
            "real-cache EXP-TBILL board is entirely DATA_BLOCKED",
        )


if __name__ == "__main__":
    unittest.main()

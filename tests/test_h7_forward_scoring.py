"""Stage 6 forward-window scoring from a synthetic verified ledger."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import config
from data.pandas_feed import adverse_buy, adverse_sell
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_forward_book import BookValidationError
from options_researcher.h7_forward_scoring import (
    ScoringIncompleteError,
    ScoringValidationError,
    map_forward_verdict,
    score_forward_window,
)
from options_researcher.h7_paper_lifecycle import ActivationBoundaryError


def _clock():
    return lambda: datetime.fromisoformat("2026-08-01T00:00:00+00:00")


def _event(event_id, event_type, session, *, symbol=None, lane=None,
           causes=None, payload=None):
    return {
        "schema_version": 1,
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at_utc": f"{session}T20:00:00+00:00",
        "evaluation_session": session,
        "symbol": symbol,
        "lane": lane,
        "causes": causes or [],
        "payload": payload or {},
    }


class ScoringCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name) / "synthetic-forward"

    def append(self, *args, **kwargs):
        return ledger.append_event(
            _event(*args, **kwargs), base_dir=self.base, clock=_clock()
        )

    def trade(
        self,
        key,
        *,
        symbol="NVDA",
        lane="a",
        decision="2026-07-06",
        fill_decision=None,
        opened="2026-07-07",
        trigger="2026-07-08",
        closed="2026-07-09",
        entry_net=None,
        exit_net=None,
        entry_commission=None,
        exit_commission=None,
        at_risk=None,
        entry_underlying=100.0,
        exit_underlying=110.0,
        entry_benchmark_session=None,
        exit_benchmark_session=None,
        opening_open_interest=100,
        opening_bid=None,
        forge_opening_strike=None,
        close=True,
    ):
        expiration = "2026-08-21"
        if lane == "c":
            action = {
                "lane": lane,
                "kind": "bull_put_spread",
                "expiration": expiration,
                "short_strike": 100.0,
                "long_strike": 95.0,
            }
            opening_legs = [
                {
                    "name": "short", "expiration": expiration,
                    "strike": 100.0, "right": "P", "side": "sell",
                    "quantity": config.H7_FORWARD_CONTRACTS,
                    "raw_bid": 4.0, "raw_ask": 4.1,
                    "open_interest": opening_open_interest,
                    "raw_delta": -0.4, "fill_price": adverse_sell(4.0),
                },
                {
                    "name": "long", "expiration": expiration,
                    "strike": 95.0, "right": "P", "side": "buy",
                    "quantity": config.H7_FORWARD_CONTRACTS,
                    "raw_bid": 0.92, "raw_ask": 1.0,
                    "open_interest": opening_open_interest,
                    "raw_delta": -0.2, "fill_price": adverse_buy(1.0),
                },
            ]
            closing_legs = [
                {
                    **{key: opening_legs[0][key] for key in (
                        "name", "expiration", "strike", "right", "quantity"
                    )},
                    "side": "buy", "raw_bid": 1.9, "raw_ask": 2.0,
                    "open_interest": 100, "raw_delta": -0.3,
                    "fill_price": adverse_buy(2.0),
                },
                {
                    **{key: opening_legs[1][key] for key in (
                        "name", "expiration", "strike", "right", "quantity"
                    )},
                    "side": "sell", "raw_bid": 0.55, "raw_ask": 0.6,
                    "open_interest": 100, "raw_delta": -0.1,
                    "fill_price": adverse_sell(0.55),
                },
            ]
            computed_entry = sum(
                (-leg["fill_price"] if leg["side"] == "sell" else leg["fill_price"])
                for leg in opening_legs
            )
            computed_exit = sum(
                (leg["fill_price"] if leg["side"] == "sell" else -leg["fill_price"])
                for leg in closing_legs
            )
            computed_at_risk = (
                (5.0 + computed_entry) * 100 * config.H7_FORWARD_CONTRACTS
                + 4 * config.COMMISSION_PER_CONTRACT
            )
        else:
            action = {
                "lane": lane,
                "kind": "long_call",
                "expiration": expiration,
                "strike": 100.0,
            }
            opening_legs = [{
                "name": "long", "expiration": expiration, "strike": 100.0,
                "right": "C", "side": "buy",
                "quantity": config.H7_FORWARD_CONTRACTS,
                "raw_bid": 4.8, "raw_ask": 4.9,
                "open_interest": opening_open_interest,
                "raw_delta": 0.5, "fill_price": adverse_buy(4.9),
            }]
            closing_legs = [{
                "name": "long", "expiration": expiration, "strike": 100.0,
                "right": "C", "side": "sell",
                "quantity": config.H7_FORWARD_CONTRACTS,
                "raw_bid": 6.1, "raw_ask": 6.2, "open_interest": 100,
                "raw_delta": 0.6, "fill_price": adverse_sell(6.1),
            }]
            computed_entry = opening_legs[0]["fill_price"]
            computed_exit = closing_legs[0]["fill_price"]
            computed_at_risk = (
                computed_entry * 100 * config.H7_FORWARD_CONTRACTS
                + 2 * config.COMMISSION_PER_CONTRACT
            )
        if entry_net is None:
            entry_net = computed_entry
        if exit_net is None:
            exit_net = computed_exit
        if at_risk is None:
            at_risk = computed_at_risk
        if entry_benchmark_session is None:
            entry_benchmark_session = opened
        if exit_benchmark_session is None:
            exit_benchmark_session = closed
        if opening_bid is not None:
            opening_legs[0]["raw_bid"] = opening_bid
            if opening_legs[0]["side"] == "sell":
                opening_legs[0]["fill_price"] = adverse_sell(opening_bid)
        leg_count = len(opening_legs)
        if entry_commission is None:
            entry_commission = (
                leg_count
                * config.H7_FORWARD_CONTRACTS
                * config.COMMISSION_PER_CONTRACT
            )
        if exit_commission is None:
            exit_commission = entry_commission
        if fill_decision is None:
            fill_decision = decision
        intent = f"intent:{key}"
        opening = f"open:{key}"
        exit_intent = f"exit:{key}"
        self.append(
            intent, "entry_intent", decision, symbol=symbol, lane=lane,
            payload={
                "position_id": intent,
                "planned_fill_session": opened,
                "decision_at_risk": at_risk,
                "action": action,
                "legs": [
                    {key: leg[key] for key in (
                        "name", "expiration", "strike", "right", "side", "quantity"
                    )}
                    for leg in opening_legs
                ],
            },
        )
        opening_action = action
        if forge_opening_strike is not None:
            opening_action = dict(action)
            opening_action["strike"] = forge_opening_strike
            opening_legs[0]["strike"] = forge_opening_strike
            closing_legs[0]["strike"] = forge_opening_strike
        self.append(
            opening, "paper_fill", opened, symbol=symbol, lane=lane,
            causes=[intent],
            payload={
                "transition": "open",
                "position_id": intent,
                "entry_intent_id": intent,
                "decision_session": fill_decision,
                "fill_session": opened,
                "structure": action["kind"],
                "action": opening_action,
                "legs": opening_legs,
                "net_debit_per_share": entry_net,
                "commission": entry_commission,
                "at_risk": at_risk,
                "underlying_close": entry_underlying,
                "underlying_close_session": entry_benchmark_session,
                "underlying_close_identity": f"sha256:open:{key}",
                "closes_identity": f"sha256:open:{key}",
            },
        )
        if not close:
            return
        self.append(
            exit_intent, "exit_intent", trigger, symbol=symbol, lane=lane,
            causes=[opening],
            payload={
                "position_id": intent,
                "opening_fill_id": opening,
                "trigger_session": trigger,
                "planned_fill_session": closed,
                "primary_reason": "profit_target",
            },
        )
        self.append(
            f"close:{key}", "paper_fill", closed, symbol=symbol, lane=lane,
            causes=[exit_intent],
            payload={
                "transition": "close",
                "position_id": intent,
                "opening_fill_id": opening,
                "exit_intent_id": exit_intent,
                "fill_session": closed,
                "net_close_credit_per_share": exit_net,
                "commission": exit_commission,
                "underlying_close": exit_underlying,
                "primary_reason": "profit_target",
                "structure": action["kind"],
                "legs": closing_legs,
                "underlying_close_session": exit_benchmark_session,
                "underlying_close_identity": f"sha256:close:{key}",
                "closes_identity": f"sha256:close:{key}",
            },
        )


class TestEconomicsAndBenchmarks(ScoringCase):
    def test_debit_and_credit_pnl_after_all_costs(self):
        self.trade("debit")
        self.trade(
            "credit", symbol="PLTR", lane="c",
            decision="2026-07-13", opened="2026-07-14",
            trigger="2026-07-15", closed="2026-07-16",
            entry_underlying=50.0, exit_underlying=45.0,
        )
        result = score_forward_window(
            base_dir=self.base,
            window_start="2026-07-06",
            window_end="2026-07-31",
        )
        self.assertEqual(len(result["trades"]), 2)
        debit, credit = result["trades"]
        self.assertAlmostEqual(debit["pnl"], 106.7)
        self.assertAlmostEqual(credit["pnl"], 144.4)
        self.assertAlmostEqual(debit["capital_at_risk"], 496.3)
        self.assertEqual(debit["underlying_move"], 10.0)
        self.assertAlmostEqual(debit["underlying_return"], 0.10)
        self.assertEqual(credit["underlying_move"], -5.0)

    def test_inclusive_decision_bounds_and_deterministic_order(self):
        self.trade("outside", symbol="SMCI", decision="2026-07-03",
                   opened="2026-07-06", trigger="2026-07-07", closed="2026-07-08")
        self.trade("end", symbol="PLTR", decision="2026-07-10",
                   opened="2026-07-13", trigger="2026-07-14", closed="2026-07-15")
        self.trade("start", symbol="NVDA", decision="2026-07-06")
        first = score_forward_window(
            base_dir=self.base, window_start="2026-07-06", window_end="2026-07-10"
        )
        second = score_forward_window(
            base_dir=self.base, window_start="2026-07-06", window_end="2026-07-10"
        )
        self.assertEqual(first, second)
        self.assertEqual(
            [trade["symbol"] for trade in first["trades"]], ["NVDA", "PLTR"]
        )

    def test_included_open_position_refuses_incomplete_score(self):
        self.trade("open", close=False)
        with self.assertRaises(ScoringIncompleteError):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_included_unresolved_intent_refuses_incomplete_score(self):
        self.append(
            "intent:pending",
            "entry_intent",
            "2026-07-06",
            symbol="NVDA",
            lane="a",
            payload={
                "position_id": "intent:pending",
                "planned_fill_session": "2026-07-07",
                "decision_at_risk": 500.0,
            },
        )
        with self.assertRaisesRegex(ScoringIncompleteError, "remain unresolved"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_forged_opening_decision_session_refuses(self):
        self.trade("forged", fill_decision="2026-07-05", close=False)
        with self.assertRaisesRegex(BookValidationError, "planned session"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_opening_contract_must_match_entry_intent(self):
        self.trade("changed-contract", forge_opening_strike=105.0)
        with self.assertRaisesRegex(BookValidationError, "entry-intent action"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_stage4_quote_admission_rules_are_replayed(self):
        self.trade("low-oi", opening_open_interest=1)
        with self.assertRaisesRegex(ScoringValidationError, "Stage-4 liquidity"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_zero_bid_is_not_a_scoreable_fill(self):
        self.trade("zero-bid", opening_bid=0.0)
        with self.assertRaisesRegex(ScoringValidationError, "Stage-4 liquidity"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_wide_spread_is_not_a_scoreable_fill(self):
        self.trade("wide-spread", opening_bid=1.0)
        with self.assertRaisesRegex(ScoringValidationError, "Stage-4 liquidity"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_wrong_frozen_commission_refuses(self):
        self.trade("bad-cost", entry_commission=0.0)
        with self.assertRaisesRegex(ScoringValidationError, "frozen cost"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_forged_net_refuses(self):
        self.trade("bad-net", entry_net=1.0)
        with self.assertRaisesRegex(ScoringValidationError, "fill legs"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_forged_at_risk_refuses(self):
        self.trade("bad-risk", at_risk=1.0)
        with self.assertRaisesRegex(ScoringValidationError, "at-risk"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_wrong_benchmark_session_refuses(self):
        self.trade("bad-session", entry_benchmark_session="2026-07-06")
        with self.assertRaisesRegex(ScoringValidationError, "fill session"):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )

    def test_malformed_benchmark_or_commission_refuses(self):
        self.trade("bad-benchmark", entry_underlying="bad")
        with self.assertRaises(ScoringValidationError):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )


class TestVerdicts(ScoringCase):
    def test_exact_three_word_vocabulary_and_gate_mapping(self):
        cases = [
            ({"n_losses": 9, "verdict": "INSUFFICIENT SAMPLE", "expectancy_CI90": [-1, 1]},
             ("INCONCLUSIVE", "insufficient_losses")),
            ({"n_losses": 10, "verdict": "INSUFFICIENT SAMPLE", "expectancy_CI90": [-1, 1]},
             ("INCONCLUSIVE", "insufficient_cohorts")),
            ({"n_losses": 10, "verdict": "x", "expectancy_CI90": [-2, -1]},
             ("REJECTED", "ci_below_zero")),
            ({"n_losses": 10, "verdict": "x", "expectancy_CI90": [1, 2]},
             ("SURVIVED", "ci_above_zero")),
            ({"n_losses": 10, "verdict": "x", "expectancy_CI90": [-1, 2]},
             ("INCONCLUSIVE", "no_edge")),
        ]
        for board, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(map_forward_verdict(board), expected)
        self.assertEqual(
            {map_forward_verdict(board)[0] for board, _ in cases},
            {"SURVIVED", "REJECTED", "INCONCLUSIVE"},
        )

    def test_overall_and_all_lanes_are_always_present(self):
        self.trade("one")
        result = score_forward_window(
            base_dir=self.base,
            window_start="2026-07-06",
            window_end="2026-07-31",
        )
        self.assertEqual(set(result["lanes"]), {"a", "b", "c"})
        self.assertEqual(result["lanes"]["a"]["scoreboard"]["n_trades"], 1)
        self.assertEqual(result["lanes"]["b"]["scoreboard"]["n_trades"], 0)
        self.assertEqual(result["overall"]["verdict"], "INCONCLUSIVE")


class TestGuardsAndPurity(ScoringCase):
    def test_scoring_is_read_only(self):
        self.trade("one")
        before = (self.base.joinpath("events.jsonl").read_bytes(),
                  self.base.joinpath("HEAD").read_bytes())
        score_forward_window(
            base_dir=self.base,
            window_start="2026-07-06",
            window_end="2026-07-31",
        )
        self.assertEqual(
            (self.base.joinpath("events.jsonl").read_bytes(),
             self.base.joinpath("HEAD").read_bytes()),
            before,
        )

    def test_real_store_is_refused_and_untouched(self):
        real = Path(__file__).resolve().parents[1] / "ledger" / "h7_forward"
        before = tuple(sorted(path.name for path in real.iterdir()))
        with self.assertRaises(ActivationBoundaryError):
            score_forward_window(
                base_dir=real,
                window_start="2026-07-06",
                window_end="2026-07-31",
            )
        self.assertEqual(tuple(sorted(path.name for path in real.iterdir())), before)

    def test_invalid_window_refuses(self):
        with self.assertRaises(ScoringValidationError):
            score_forward_window(
                base_dir=self.base,
                window_start="2026-07-31",
                window_end="2026-07-06",
            )


if __name__ == "__main__":
    unittest.main()

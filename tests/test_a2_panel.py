"""Regression tests for local-only, causal A2 panel construction."""

from __future__ import annotations

import unittest

import pandas as pd

import config
from options_researcher.a2_panel import (
    A2Diagnostics,
    audit_historical_inputs,
    build_historical_outcomes,
    select_income_contract,
    select_leaps_contract,
    select_tactical_contract,
)

SYMBOL = config.A2_UNIVERSE[0]


def _chain(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def _row(**overrides: object) -> dict:
    row: dict[str, object] = {
        "expiration": "2025-02-21",
        "strike": 100.0,
        "right": "P",
        "bid": 2.0,
        "ask": 2.2,
        "open_interest": 500,
        "delta": -0.20,
        "iv": 0.30,
        "gamma": 0.02,
        "theta": -0.03,
        "vega": 0.10,
        "contract_symbol": "AAA250221P00100000",
        "timestamp": "2025-01-03T21:00:00+00:00",
        "underlying_price": 105.0,
    }
    row.update(overrides)
    return row


class SelectorTests(unittest.TestCase):
    def test_registered_constants_are_frozen_and_universe_has_fifteen_names(self):
        self.assertEqual(config.A2_REGISTRATION_ID, "A2-v1")
        self.assertEqual(len(config.A2_UNIVERSE), 15)
        self.assertEqual(config.A2_CSP_FIXED_HORIZON_SESSIONS, 10)
        self.assertEqual(config.A2_LEAPS_HORIZONS, (21, 63, 126))
        self.assertEqual(config.A2_TACTICAL_HORIZONS, (5, 10, 20))

    def test_income_selector_uses_delta_then_expiration_strike_right_and_symbol(self):
        chain = _chain(
            [
                _row(strike=101.0, contract_symbol="Z"),
                _row(strike=99.0, contract_symbol="A"),
                _row(strike=98.0, contract_symbol="B", delta=-0.19),
            ]
        )
        selected = select_income_contract(chain, "2025-01-03", right="P")
        self.assertEqual(float(selected["strike"]), 99.0)
        self.assertEqual(selected["contract_symbol"], "A")

    def test_leaps_and_tactical_selectors_use_registered_deltas(self):
        leaps = _chain([_row(right="C", expiration="2025-12-19", delta=0.70)])
        tactical = _chain([_row(right="C", delta=0.40)])
        self.assertEqual(float(select_leaps_contract(leaps, "2025-01-03")["delta"]), 0.70)
        self.assertEqual(float(select_tactical_contract(tactical, "2025-01-03")["delta"]), 0.40)

    def test_leaps_selector_breaks_equal_delta_ties_by_contract_identity(self):
        chain = _chain(
            [
                _row(
                    right="C",
                    expiration="2025-12-19",
                    strike=110.0,
                    delta=0.70,
                    contract_symbol="Z",
                ),
                _row(
                    right="C",
                    expiration="2025-12-19",
                    strike=100.0,
                    delta=0.70,
                    contract_symbol="A",
                ),
            ]
        )
        selected = select_leaps_contract(chain, "2025-01-03")
        self.assertEqual((float(selected["strike"]), selected["contract_symbol"]), (100.0, "A"))

    def test_entry_uses_exact_next_session_and_never_a_later_chain_row(self):
        signal_chain = _chain([_row()])
        later_chain = _chain([_row(bid=2.5, ask=2.7)])
        diagnostics = A2Diagnostics()
        outcomes = build_historical_outcomes(
            signals={"2025-01-02": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-02": signal_chain, "2025-01-06": later_chain}},
            raw_closes={SYMBOL: {"2025-01-02": 105.0, "2025-01-03": 104.0}},
            adjusted_closes={SYMBOL: {"2025-01-02": 105.0, "2025-01-03": 104.0}},
            diagnostics=diagnostics,
        )
        self.assertEqual(outcomes, ())
        self.assertEqual(diagnostics.skips["missing_entry_chain"], 1)


class ResolutionTests(unittest.TestCase):
    def test_csp_fixed_horizon_is_expiration_first_and_cost_preserves_bid_ask(self):
        entry = _chain([_row(expiration="2025-01-17")])
        exit_chain = _chain([_row(expiration="2025-01-17", bid=0.5, ask=0.7)])
        outcomes = build_historical_outcomes(
            signals={"2024-12-31": {SYMBOL: 1.0}},
            chains={
                SYMBOL: {
                    "2024-12-31": _chain([_row()]),
                    "2025-01-01": entry,
                    "2025-01-02": entry,
                    "2025-01-17": exit_chain,
                }
            },
            raw_closes={
                SYMBOL: {
                    "2024-12-31": 105.0,
                    "2025-01-01": 104.0,
                    "2025-01-02": 104.0,
                    "2025-01-03": 104.0,
                    "2025-01-06": 104.0,
                    "2025-01-17": 95.0,
                }
            },
            adjusted_closes={
                SYMBOL: {
                    "2024-12-31": 105.0,
                    "2025-01-01": 104.0,
                    "2025-01-02": 104.0,
                    "2025-01-03": 104.0,
                    "2025-01-06": 104.0,
                    "2025-01-17": 95.0,
                }
            },
            rates={SYMBOL: {"2025-01-01": 0.0}},
        )
        fixed = next(row for row in outcomes if row.arm == "fixed_10_sessions")
        self.assertEqual(fixed.resolution_date, "2025-01-17")
        self.assertGreater(fixed.modeled_cost, fixed.bid_ask_cost)
        self.assertAlmostEqual(fixed.cost_adjusted_return, fixed.gross_return - fixed.modeled_cost)

    def test_csp_capture_50_settles_at_expiration_when_target_never_occurs(self):
        entry = _chain([_row(expiration="2025-01-17")])
        outcomes = build_historical_outcomes(
            signals={"2024-12-31": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-01": entry, "2025-01-02": entry}},
            raw_closes={
                SYMBOL: {
                    "2024-12-31": 105.0,
                    "2025-01-01": 104.0,
                    "2025-01-02": 104.0,
                    "2025-01-17": 95.0,
                }
            },
            adjusted_closes={
                SYMBOL: {
                    "2024-12-31": 105.0,
                    "2025-01-01": 104.0,
                    "2025-01-02": 104.0,
                    "2025-01-17": 95.0,
                }
            },
            rates={SYMBOL: {"2025-01-01": 0.0}},
        )
        capture = next(row for row in outcomes if row.arm == "capture_50")
        self.assertEqual(capture.resolution_date, "2025-01-17")

    def test_csp_requires_explicit_matched_tenor_rate(self):
        diagnostics = A2Diagnostics()
        outcomes = build_historical_outcomes(
            signals={"2024-12-31": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-01": _chain([_row(expiration="2025-01-17")])}},
            raw_closes={SYMBOL: {"2024-12-31": 105.0, "2025-01-01": 104.0}},
            adjusted_closes={SYMBOL: {"2024-12-31": 105.0, "2025-01-01": 104.0}},
            diagnostics=diagnostics,
        )
        self.assertEqual(outcomes, ())
        self.assertEqual(diagnostics.skips["missing_matched_tenor_rate"], 1)

    def test_missing_or_invalid_resolution_quote_is_counted_and_not_substituted(self):
        diagnostics = A2Diagnostics()
        outcomes = build_historical_outcomes(
            signals={"2025-01-31": {SYMBOL: 1.0}},
            chains={
                SYMBOL: {
                    "2025-01-31": _chain([_row(expiration="2025-03-21")]),
                    "2025-02-03": _chain([_row(expiration="2025-03-21")]),
                    "2025-02-28": _chain([_row(expiration="2025-03-21", bid=3.0, ask=2.0)]),
                    "2025-01-13": _chain([_row(bid=0.5, ask=0.7)]),
                }
            },
            raw_closes={
                SYMBOL: {
                    "2025-01-31": 105.0,
                    "2025-02-03": 104.0,
                    "2025-02-28": 95.0,
                    "2025-01-13": 95.0,
                }
            },
            adjusted_closes={
                SYMBOL: {
                    "2025-01-31": 105.0,
                    "2025-02-03": 104.0,
                    "2025-02-28": 95.0,
                    "2025-01-13": 95.0,
                }
            },
            rates={SYMBOL: {"2025-02-03": 0.0}},
            diagnostics=diagnostics,
        )
        self.assertFalse(outcomes)
        self.assertGreaterEqual(diagnostics.skips["invalid_resolution_quote"], 1)

    def test_audit_returns_all_fourteen_checks_and_blocks_tradeable_crossed_quote(self):
        audit = audit_historical_inputs(
            chains={"AAA": {"2025-01-03": _chain([_row(bid=3.0, ask=2.0)])}},
            raw_closes={"AAA": {"2025-01-03": 105.0}},
            selected_contracts={("AAA", "2025-01-03", "AAA250221P00100000")},
        )
        self.assertEqual(tuple(audit.checks), tuple(range(1, 15)))
        self.assertEqual(audit.verdict, "BLOCK")

    def test_audit_blocks_selected_underlying_mismatch_and_stale_timestamp(self):
        audit = audit_historical_inputs(
            chains={
                "AAA": {
                    "2025-01-03": _chain(
                        [_row(underlying_price=99.0, timestamp="2024-12-01T21:00:00+00:00")]
                    )
                }
            },
            raw_closes={"AAA": {"2025-01-03": 105.0}},
            selected_contracts={("AAA", "2025-01-03", "AAA250221P00100000")},
        )
        self.assertEqual(audit.verdict, "BLOCK")
        self.assertTrue(audit.checks[9])
        self.assertTrue(audit.checks[13])


if __name__ == "__main__":
    unittest.main()

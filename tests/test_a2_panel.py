"""Regression tests for local-only, causal A2 panel construction."""

from __future__ import annotations

import math
import unittest

import pandas as pd

import config
from options_researcher.a2_panel import (
    A2Diagnostics,
    _covered_call,
    _csp,
    _long,
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

    def test_income_selector_rejects_malformed_entry_candidate_fields_before_monthly_lookup(self):
        # Removing A2's pre-selector sanitization lets nearest_monthly() raise
        # on these values before the existing unusable-entry path can run.
        for field, value in (
            ("bid", "not-a-number"),
            ("ask", float("inf")),
            ("expiration", "not-a-date"),
            ("strike", float("nan")),
            ("open_interest", "not-a-number"),
            ("delta", float("inf")),
        ):
            with self.subTest(field=field):
                self.assertIsNone(
                    select_income_contract(
                        _chain([_row(**{field: value})]), "2025-01-03", right="P"
                    )
                )

    def test_malformed_income_entry_is_counted_as_invalid_csp_entry(self):
        diagnostics = A2Diagnostics()
        outcomes = build_historical_outcomes(
            signals={"2025-01-02": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-03": _chain([_row(bid="not-a-number")])}},
            raw_closes={SYMBOL: {"2025-01-02": 105.0, "2025-01-03": 104.0}},
            adjusted_closes={SYMBOL: {"2025-01-02": 105.0, "2025-01-03": 104.0}},
            diagnostics=diagnostics,
        )
        self.assertEqual(outcomes, ())
        self.assertEqual(diagnostics.skips["invalid_csp_entry"], 1)

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
    def _csp_rows(
        self,
        raw: dict[str, float],
        chains: dict[str, pd.DataFrame],
        diagnostics: A2Diagnostics | None = None,
    ):
        return _csp(
            SYMBOL,
            "2025-01-30",
            "2025-01-31",
            pd.Series(_row(expiration="2025-03-21")),
            1.0,
            chains,
            raw,
            diagnostics or A2Diagnostics(),
            {"source": "fixture"},
            0.0,
        )

    def test_csp_breach_arm_holds_unbreached_path_to_expiration(self):
        rows = self._csp_rows(
            {
                "2025-01-31": 105.0,
                "2025-02-28": 104.0,
                "2025-03-21": 103.0,
            },
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
        )
        self.assertIsNotNone(rows)
        by_arm = {row.arm: row for row in rows or ()}
        self.assertEqual(by_arm["close_21_dte"].resolution_date, "2025-02-28")
        self.assertEqual(by_arm["breach_hold_21_dte"].resolution_date, "2025-03-21")
        self.assertEqual(by_arm["breach_hold_21_dte"].maximum_resolution_date, "2025-03-21")

    def test_csp_breach_after_21_dte_closes_next_session_not_same_bar(self):
        rows = self._csp_rows(
            {
                "2025-01-31": 105.0,
                "2025-02-28": 105.0,
                "2025-03-03": 99.0,
                "2025-03-04": 98.0,
                "2025-03-21": 97.0,
            },
            {
                "2025-02-28": _chain([_row(expiration="2025-03-21")]),
                "2025-03-04": _chain([_row(expiration="2025-03-21", bid=2.5, ask=2.7)]),
            },
        )
        self.assertIsNotNone(rows)
        breach = next(row for row in rows or () if row.arm == "breach_hold_21_dte")
        self.assertEqual(breach.resolution_date, "2025-03-04")

    def test_csp_breach_before_21_dte_waits_for_threshold_and_at_strike_is_not_breach(self):
        cases = (
            (
                "strict breach before threshold",
                {
                    "2025-01-31": 105.0,
                    "2025-02-10": 99.0,
                    "2025-02-28": 98.0,
                    "2025-03-21": 97.0,
                },
                "2025-02-28",
            ),
            (
                "at strike is unbreached",
                {
                    "2025-01-31": 105.0,
                    "2025-02-28": 105.0,
                    "2025-03-03": 100.0,
                    "2025-03-21": 101.0,
                },
                "2025-03-21",
            ),
        )
        for label, raw, expected_resolution in cases:
            with self.subTest(label=label):
                rows = self._csp_rows(
                    raw,
                    {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
                )
                self.assertIsNotNone(rows)
                breach = next(row for row in rows or () if row.arm == "breach_hold_21_dte")
                self.assertEqual(breach.resolution_date, expected_resolution)

    def test_csp_breach_at_expiration_uses_expiration_settlement(self):
        rows = self._csp_rows(
            {
                "2025-01-31": 105.0,
                "2025-02-28": 105.0,
                "2025-03-21": 99.0,
            },
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
        )
        self.assertIsNotNone(rows)
        breach = next(row for row in rows or () if row.arm == "breach_hold_21_dte")
        self.assertEqual(breach.resolution_date, "2025-03-21")

    def test_breach_scan_missing_underlying_close_sessions_are_counted(self):
        # F3 (independent adversarial review, 2026-08-30): the breach scan
        # only ever looks at sessions present in ``raw``; a hole in the
        # underlying close series inside the scan window used to resolve
        # silently as "unbreached" with no diagnostic.  This does not change
        # resolution behavior (still no substituted close), it only detects
        # and counts the gap, surfaced like any other skip counter.
        diagnostics = A2Diagnostics()
        self._csp_rows(
            {"2025-01-31": 105.0, "2025-02-28": 104.0, "2025-03-21": 103.0},
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
            diagnostics,
        )
        self.assertGreater(diagnostics.skips["breach_scan_missing_underlying_close_session"], 0)

    def test_breach_at_expiration_is_counted_as_a_terminal_exception_settlement(self):
        # F4: breach-on-expiration resolves by settlement (Definition 1.2's
        # sole exemption from the t+1 rule) and must be counted separately
        # from an ordinary breach-then-hold resolution.
        diagnostics = A2Diagnostics()
        self._csp_rows(
            {"2025-01-31": 105.0, "2025-02-28": 105.0, "2025-03-21": 99.0},
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
            diagnostics,
        )
        self.assertEqual(diagnostics.breach_on_expiry_settlements, 1)

    def test_unbreached_path_does_not_count_a_terminal_exception_settlement(self):
        diagnostics = A2Diagnostics()
        self._csp_rows(
            {"2025-01-31": 105.0, "2025-02-28": 104.0, "2025-03-21": 103.0},
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
            diagnostics,
        )
        self.assertEqual(diagnostics.breach_on_expiry_settlements, 0)

    def test_csp_breach_missing_exit_is_counted_by_breach_path(self):
        diagnostics = A2Diagnostics()
        rows = self._csp_rows(
            {
                "2025-01-31": 105.0,
                "2025-02-28": 105.0,
                "2025-03-03": 99.0,
                "2025-03-04": 98.0,
                "2025-03-21": 97.0,
            },
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
            diagnostics,
        )
        self.assertIsNone(rows)
        self.assertEqual(
            diagnostics.skips["breach_hold_21_dte_breached_invalid_resolution_quote"], 1
        )

    def test_csp_unbreached_missing_settlement_is_counted_by_breach_path(self):
        diagnostics = A2Diagnostics()
        rows = self._csp_rows(
            {"2025-01-31": 105.0, "2025-02-28": 105.0},
            {"2025-02-28": _chain([_row(expiration="2025-03-21")])},
            diagnostics,
        )
        self.assertIsNone(rows)
        self.assertEqual(diagnostics.skips["breach_hold_21_dte_unbreached_missing_raw_close"], 1)

    def test_leaps_components_use_exact_marks_greeks_earnings_and_adjusted_drawdown(self):
        sessions = [day.strftime("%Y-%m-%d") for day in pd.bdate_range("2025-01-02", periods=24)]
        entry_day, resolution_day = sessions[0], sessions[21]
        entry = _chain(
            [
                _row(
                    right="C",
                    expiration="2025-12-19",
                    bid=2.0,
                    ask=2.2,
                    delta=0.6,
                    vega=0.2,
                    iv=0.4,
                )
            ]
        ).iloc[0]
        exit_quote = _row(
            right="C", expiration="2025-12-19", bid=3.1, ask=3.3, delta=0.6, vega=0.2, iv=0.5
        )
        chains = {day: _chain([exit_quote]) for day in sessions[1:]}
        raw = {day: 100.0 + index * 2.0 for index, day in enumerate(sessions)}
        adjusted = dict(raw)
        adjusted[sessions[2]] = 96.0
        outcome = _long(
            SYMBOL,
            "2025-01-01",
            entry_day,
            entry,
            1.0,
            chains,
            raw,
            "leaps",
            (21,),
            A2Diagnostics(),
            {"source": "fixture"},
            adjusted,
            None,
            {SYMBOL: (sessions[2],)},
        )[0]
        adverse_buy_mark = lambda value: math.ceil(value * 1.01 * 100.0) / 100.0
        adverse_sell_mark = lambda value: math.floor(value * 0.99 * 100.0) / 100.0
        denom = adverse_buy_mark(2.2) * 100
        option_pnl = (adverse_sell_mark(3.1) - adverse_buy_mark(2.2)) * 100
        bid_ask = abs(adverse_buy_mark(2.2) - 2.1) * 100 + abs(adverse_sell_mark(3.1) - 3.2) * 100
        self.assertEqual(outcome.resolution_date, resolution_day)
        self.assertAlmostEqual(outcome.components["option_result"], option_pnl / denom)
        stock_pnl = (raw[resolution_day] - raw[entry_day]) * 100.0
        self.assertAlmostEqual(outcome.components["stock_result"], stock_pnl / denom)
        self.assertAlmostEqual(
            outcome.components["delta_adjusted_stock_result"], 0.6 * stock_pnl / denom
        )
        self.assertAlmostEqual(outcome.components["spread_cost"], -bid_ask / denom)
        self.assertAlmostEqual(outcome.components["vega_contribution"], 0.2 * 0.1 / (denom / 100))
        self.assertEqual(outcome.components["earnings_exposure_count"], 1.0)
        self.assertAlmostEqual(outcome.components["drawdown"], -400.0 / denom)

    def test_tactical_components_reconcile_each_horizon_from_derived_greeks(self):
        sessions = [day.strftime("%Y-%m-%d") for day in pd.bdate_range("2025-01-02", periods=24)]
        entry_day = sessions[0]
        entry = _chain(
            [
                _row(
                    right="C",
                    expiration="2025-12-19",
                    bid=2.0,
                    ask=2.2,
                    delta=0.5,
                    gamma=0.02,
                    theta=-0.01,
                    vega=0.2,
                    iv=0.4,
                )
            ]
        ).iloc[0]
        exit_ivs = {5: 0.45, 10: 0.52, 20: 0.61}
        chains = {
            day: _chain(
                [
                    _row(
                        right="C",
                        expiration="2025-12-19",
                        bid=2.5 + index / 10.0,
                        ask=2.7 + index / 10.0,
                        delta=0.5,
                        gamma=0.02,
                        theta=-0.01,
                        vega=0.2,
                        iv=exit_ivs.get(index, 0.4),
                    )
                ]
            )
            for index, day in enumerate(sessions[1:], start=1)
        }
        raw = {day: 100.0 + index * 1.5 for index, day in enumerate(sessions)}
        outcomes = _long(
            SYMBOL,
            "2025-01-01",
            entry_day,
            entry,
            1.0,
            chains,
            raw,
            "tactical_call",
            (5, 10, 20),
            A2Diagnostics(),
            {"source": "fixture"},
            raw,
            None,
            None,
        )
        adverse_buy_mark = lambda value: math.ceil(value * 1.01 * 100.0) / 100.0
        adverse_sell_mark = lambda value: math.floor(value * 0.99 * 100.0) / 100.0
        denom, tau = (
            adverse_buy_mark(2.2) * 100,
            (pd.Timestamp("2025-12-19") - pd.Timestamp(entry_day)).days / 365.0,
        )

        def normal_cdf(value: float) -> float:
            return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))

        ratio = 0.5 / (0.02 * 100.0 * 0.4 * math.sqrt(tau))
        low, high = -10.0, 10.0
        for _ in range(80):
            midpoint = (low + high) / 2.0
            phi = math.exp(-0.5 * midpoint * midpoint) / math.sqrt(2.0 * math.pi)
            if normal_cdf(midpoint) / phi < ratio:
                low = midpoint
            else:
                high = midpoint
        d1 = (low + high) / 2.0
        d2 = d1 - 0.4 * math.sqrt(tau)
        vanna = -0.02 * 100.0 * math.sqrt(tau) * d2
        volga = 0.2 * d1 * d2 / 0.4
        for outcome, horizon in zip(outcomes, (5, 10, 20), strict=True):
            resolution = sessions[horizon]
            ds, d_sigma = raw[resolution] - raw[entry_day], exit_ivs[horizon] - 0.4
            bid, ask = 2.5 + horizon / 10.0, 2.7 + horizon / 10.0
            option_pnl = (adverse_sell_mark(bid) - adverse_buy_mark(2.2)) * 100
            bid_ask = (
                abs(adverse_buy_mark(2.2) - 2.1) * 100
                + abs(adverse_sell_mark(bid) - (bid + ask) / 2.0) * 100
            )
            expected = {
                "stock_price": 0.5 * ds * 100 / denom,
                "iv": 0.2 * d_sigma / (denom / 100),
                "decay": -0.01
                * (pd.Timestamp(resolution) - pd.Timestamp(entry_day)).days
                * 100
                / denom,
                "cross_effects": (
                    0.5 * 0.02 * ds * ds + 0.5 * volga * d_sigma * d_sigma + vanna * ds * d_sigma
                )
                * 100
                / denom,
                "spread_cost": -bid_ask / denom,
            }
            for component, value in expected.items():
                self.assertAlmostEqual(outcome.components[component], value)
            self.assertAlmostEqual(
                outcome.components["residual"], option_pnl / denom - sum(expected.values())
            )
            self.assertAlmostEqual(sum(outcome.components.values()), outcome.gross_return)

    def test_long_exit_rejects_crossed_zero_illiquid_and_malformed_structural_rows(self):
        entry_day, exit_day = "2025-01-02", "2025-01-03"
        entry = _chain([_row(right="C", expiration="2025-12-19", iv=0.4, vega=0.2)]).iloc[0]
        raw = {entry_day: 100.0, exit_day: 101.0}
        for exit_row in (
            _row(right="C", expiration="2025-12-19", bid=3.0, ask=2.0),
            _row(right="C", expiration="2025-12-19", bid=0.0, ask=2.0),
            _row(right="C", expiration="2025-12-19", open_interest=0),
            _row(right="C", expiration="2025-12-19", strike="not-a-number"),
            _row(right="C", expiration="2025-12-19", strike=float("nan")),
            _row(right="C", expiration="2025-12-19", open_interest="not-a-number"),
            _row(right="C", expiration="2025-12-19", open_interest=float("inf")),
        ):
            diagnostics = A2Diagnostics()
            self.assertIsNone(
                _long(
                    SYMBOL,
                    "2025-01-01",
                    entry_day,
                    entry,
                    1.0,
                    {exit_day: _chain([exit_row])},
                    raw,
                    "leaps",
                    (1,),
                    diagnostics,
                    {"source": "fixture"},
                    raw,
                    None,
                    None,
                )
            )
            self.assertEqual(diagnostics.skips["invalid_resolution_quote"], 1)
        diagnostics = A2Diagnostics()
        malformed = _row(right="C", expiration="2025-12-19", iv="not-a-number", vega=0.2)
        self.assertIsNone(
            _long(
                SYMBOL,
                "2025-01-01",
                entry_day,
                entry,
                1.0,
                {exit_day: _chain([malformed])},
                raw,
                "leaps",
                (1,),
                diagnostics,
                {"source": "fixture"},
                raw,
                None,
                None,
            )
        )
        self.assertEqual(diagnostics.skips["invalid_leaps_numeric_input"], 1)
        diagnostics = A2Diagnostics()
        tactical_malformed = _row(
            right="C", expiration="2025-12-19", iv=float("inf"), gamma=0.02, theta=-0.01, vega=0.2
        )
        self.assertIsNone(
            _long(
                SYMBOL,
                "2025-01-01",
                entry_day,
                entry,
                1.0,
                {exit_day: _chain([tactical_malformed])},
                raw,
                "tactical_call",
                (1,),
                diagnostics,
                {"source": "fixture"},
                raw,
                None,
                None,
            )
        )
        self.assertEqual(diagnostics.skips["invalid_tactical_attribution_input"], 1)

    def test_covered_call_assigned_decomposition_is_uncapped_stock_plus_short_call(self):
        outcome = _covered_call(
            SYMBOL,
            "2025-01-02",
            "2025-01-03",
            _chain([_row(right="C", strike=100.0)]).iloc[0],
            1.0,
            {"2025-01-03": 90.0, "2025-02-21": 120.0},
            A2Diagnostics(),
            {"source": "fixture"},
        )
        self.assertAlmostEqual(outcome.components["stock_result"], 30 / 90)
        self.assertAlmostEqual(outcome.components["short_call_result"], (198 - 2000) / 9000)
        self.assertAlmostEqual(
            outcome.components["combined_result"],
            outcome.components["stock_result"] + outcome.components["short_call_result"],
        )

    def test_covered_call_unassigned_keeps_zero_assignment_and_lost_upside(self):
        outcome = _covered_call(
            SYMBOL,
            "2025-01-02",
            "2025-01-03",
            _chain([_row(right="C", strike=100.0)]).iloc[0],
            1.0,
            {"2025-01-03": 90.0, "2025-02-21": 95.0},
            A2Diagnostics(),
            {"source": "fixture"},
        )
        self.assertEqual(outcome.components["assignment_incidence"], 0.0)
        self.assertEqual(outcome.components["lost_upside"], 0.0)

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
        self.assertEqual(capture.maximum_resolution_date, "2025-01-17")

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

    def test_csp_cash_forgone_uses_actual_arm_tenor_and_mae_is_never_positive(self):
        entry = _chain([_row(expiration="2025-01-17")])
        target = _chain([_row(expiration="2025-01-17", bid=0.47, ask=0.5)])
        diagnostics = A2Diagnostics()
        outcomes = build_historical_outcomes(
            signals={"2024-12-31": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-01": entry, "2025-01-02": target}},
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
            rates={SYMBOL: {"2025-01-01": 0.365}},
            diagnostics=diagnostics,
        )
        capture = next(row for row in outcomes if row.arm == "capture_50")
        assigned = next(row for row in outcomes if row.arm == "assignment_accepting")
        self.assertGreater(
            capture.components["cash_return_forgone"], assigned.components["cash_return_forgone"]
        )
        self.assertLessEqual(capture.components["max_adverse_excursion"], 0.0)
        self.assertIn((SYMBOL, "2025-01-01", "AAA250221P00100000"), diagnostics.selected_contracts)
        self.assertIn((SYMBOL, "2025-01-02", "AAA250221P00100000"), diagnostics.selected_contracts)

    def test_invalid_rate_is_a_counted_skip(self):
        diagnostics = A2Diagnostics()
        build_historical_outcomes(
            signals={"2024-12-31": {SYMBOL: 1.0}},
            chains={SYMBOL: {"2025-01-01": _chain([_row(expiration="2025-01-17")])}},
            raw_closes={SYMBOL: {"2024-12-31": 105.0, "2025-01-01": 104.0}},
            adjusted_closes={SYMBOL: {"2024-12-31": 105.0, "2025-01-01": 104.0}},
            rates={SYMBOL: {"2025-01-01": float("nan")}},
            diagnostics=diagnostics,
        )
        self.assertEqual(diagnostics.skips["invalid_matched_tenor_rate"], 1)

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

    def test_audit_scoped_row_failure_excludes_unscoped_bad_row(self):
        good = _row(contract_symbol="GOOD")
        bad = _row(contract_symbol="BAD", bid=3.0, ask=2.0)
        audit = audit_historical_inputs(
            chains={"AAA": {"2025-01-03": _chain([good, bad])}},
            raw_closes={"AAA": {"2025-01-03": 105.0}},
            selected_contracts={("AAA", "2025-01-03", "GOOD")},
        )
        self.assertNotEqual(audit.verdict, "BLOCK")

    def test_audit_blocks_selected_malformed_structural_quote_fields(self):
        for row in (
            _row(strike="not-a-number"),
            _row(open_interest="not-a-number"),
        ):
            audit = audit_historical_inputs(
                chains={"AAA": {"2025-01-03": _chain([row])}},
                raw_closes={"AAA": {"2025-01-03": 105.0}},
                selected_contracts={("AAA", "2025-01-03", "AAA250221P00100000")},
            )
            self.assertEqual(audit.verdict, "BLOCK")

    def test_audit_reports_missing_canonical_metadata_as_warning(self):
        row = _row()
        row.pop("timestamp")
        row.pop("underlying_price")
        audit = audit_historical_inputs(
            chains={"AAA": {"2025-01-03": _chain([row])}}, raw_closes={"AAA": {"2025-01-03": 105.0}}
        )
        self.assertTrue(audit.checks[9])
        self.assertTrue(audit.checks[13])


if __name__ == "__main__":
    unittest.main()

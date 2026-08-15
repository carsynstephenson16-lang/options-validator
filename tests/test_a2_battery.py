"""Contract tests for the pure, offline A2 outcome battery boundary."""

from __future__ import annotations

import math
import unittest
from dataclasses import replace

from options_researcher.a2_battery import (
    LANE_COMPONENTS,
    A2Outcome,
    non_overlapping_inference_rows,
    staggered_descriptive_rows,
    summarize_lane,
    validate_outcomes,
)

_CSP_COMPONENTS = {
    "option_pnl": 0.04,
    "assigned_stock_result": 0.0,
    "collateral_return": 0.0,
    "cash_return_forgone": 0.0,
    "max_adverse_excursion": -0.02,
    "final_loss": 0.0,
}


def _outcome(
    *,
    symbol: str = "AAA",
    decision_date: str = "2025-01-02",
    entry_date: str = "2025-01-03",
    resolution_date: str = "2025-01-10",
    lane: str = "csp",
    arm: str = "capture_50",
    score: float = 1.0,
    gross_return: float = 0.05,
    modeled_cost: float = 0.01,
    bid_ask_cost: float = 0.005,
    cost_adjusted_return: float | None = None,
    components: dict[str, float] | None = None,
    provenance: dict[str, str] | None = None,
) -> A2Outcome:
    return A2Outcome(
        symbol=symbol,
        decision_date=decision_date,
        entry_date=entry_date,
        resolution_date=resolution_date,
        lane=lane,
        arm=arm,
        score=score,
        gross_return=gross_return,
        modeled_cost=modeled_cost,
        bid_ask_cost=min(bid_ask_cost, modeled_cost),
        cost_adjusted_return=(
            gross_return - modeled_cost if cost_adjusted_return is None else cost_adjusted_return
        ),
        components=components
        if components is not None
        else {
            **_CSP_COMPONENTS,
            "option_pnl": gross_return + 0.02,
        },
        provenance=provenance if provenance is not None else {"source": "fixture"},
    )


class ContractTests(unittest.TestCase):
    def test_csp_tail_loss_is_not_a_per_row_required_component(self):
        self.assertNotIn("tail_event_loss", _CSP_COMPONENTS)
        self.assertNotIn("tail_event_loss", LANE_COMPONENTS["csp"])

    def test_invalid_dates_fail_closed(self):
        for field in ("decision_date", "entry_date", "resolution_date"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    _outcome(**{field: "not-a-date"})

    def test_entry_must_follow_decision_and_resolution_must_follow_entry(self):
        with self.assertRaises(ValueError):
            _outcome(entry_date="2025-01-02")
        with self.assertRaises(ValueError):
            _outcome(resolution_date="2025-01-02")

    def test_unknown_lane_and_arm_fail_closed(self):
        with self.assertRaises(ValueError):
            _outcome(lane="unknown")
        with self.assertRaises(ValueError):
            _outcome(arm="unknown")

    def test_nonfinite_returns_and_negative_costs_fail_closed(self):
        with self.assertRaises(ValueError):
            _outcome(gross_return=math.nan)
        with self.assertRaises(ValueError):
            _outcome(modeled_cost=-0.01)
        with self.assertRaises(ValueError):
            _outcome(bid_ask_cost=-0.01)

    def test_missing_lane_accounting_component_fails_closed(self):
        with self.assertRaises(ValueError):
            _outcome(components={"option_pnl": 0.04})

    def test_component_and_cost_reconciliation_is_required(self):
        with self.assertRaises(ValueError):
            _outcome(components={**_CSP_COMPONENTS, "option_pnl": math.nan})
        with self.assertRaises(ValueError):
            _outcome(cost_adjusted_return=0.99)  # type: ignore[call-arg]

    def test_duplicate_identity_and_mixed_lanes_fail_closed(self):
        row = _outcome()
        with self.assertRaises(ValueError):
            validate_outcomes((row, row))
        with self.assertRaises(ValueError):
            validate_outcomes((row, replace(row, lane="covered_call", arm="covered_call")))

    def test_provenance_requires_nonempty_scalar_source_or_receipt_identity(self):
        for provenance in (
            {"source": ""},
            {"source": "   "},
            {"source": None},
            {"source": False},
            {"source": True},
            {"source": 0},
            {"source": 1},
            {"source": 0.0},
            {"source": 1.0},
            {"source": {"path": "fixture"}},
            {"regime": "normal"},
        ):
            with self.subTest(provenance=provenance):
                with self.assertRaises(ValueError):
                    _outcome(provenance=provenance)


class ViewSeparationTests(unittest.TestCase):
    def test_inference_accepts_only_strictly_nonoverlapping_cohorts(self):
        rows = (
            _outcome(symbol="AAA", entry_date="2025-01-03", resolution_date="2025-01-10"),
            _outcome(symbol="BBB", entry_date="2025-01-03", resolution_date="2025-01-10"),
            _outcome(symbol="CCC", entry_date="2025-01-10", resolution_date="2025-01-20"),
            _outcome(symbol="DDD", entry_date="2025-01-21", resolution_date="2025-01-30"),
        )
        accepted = non_overlapping_inference_rows(rows)
        self.assertEqual(tuple(row.symbol for row in accepted), ("AAA", "BBB", "DDD"))

    def test_staggered_view_keeps_all_rows_and_is_immutable(self):
        rows = (_outcome(), replace(_outcome(), symbol="BBB"))
        self.assertEqual(len(staggered_descriptive_rows(rows)), 2)
        self.assertIsInstance(staggered_descriptive_rows(rows), tuple)

    def test_staggered_rows_cannot_change_inference_summary(self):
        base = tuple(
            _outcome(symbol=s, score=float(i), gross_return=0.01 * (i + 1), modeled_cost=0.0)
            for i, s in enumerate(("A", "B", "C"), start=1)
        )
        extra = replace(
            _outcome(symbol="Z"),
            decision_date="2025-01-09",
            entry_date="2025-01-10",
            resolution_date="2025-01-20",
        )
        changed_extra = replace(
            extra,
            gross_return=-0.50,
            cost_adjusted_return=-0.51,
            components={**_CSP_COMPONENTS, "option_pnl": -0.48},
        )
        first_rows = non_overlapping_inference_rows(base + (extra,))
        second_rows = non_overlapping_inference_rows(base + (changed_extra,))
        first = summarize_lane(first_rows, lane="csp", arm="capture_50")
        second = summarize_lane(second_rows, lane="csp", arm="capture_50")
        self.assertEqual(first_rows, second_rows)
        self.assertEqual(first.spread, second.spread)
        first_staggered = staggered_descriptive_rows(base + (extra,))
        second_staggered = staggered_descriptive_rows(base + (changed_extra,))
        self.assertEqual(len(first_staggered), 4)
        self.assertNotEqual(
            first_staggered[-1].cost_adjusted_return, second_staggered[-1].cost_adjusted_return
        )


class SummaryTests(unittest.TestCase):
    def _fifteen(self) -> tuple[A2Outcome, ...]:
        rows = []
        for i in range(15):
            gross = (15 - i) / 100
            rows.append(
                _outcome(
                    symbol=f"N{i:02d}",
                    score=float(15 - i),
                    gross_return=gross,
                    modeled_cost=0.0,
                    components={**_CSP_COMPONENTS, "option_pnl": gross + 0.02},
                )
            )
        return tuple(rows)

    def test_summary_has_deterministic_terciles_and_stress(self):
        summary = summarize_lane(self._fifteen(), lane="csp", arm="capture_50")
        self.assertEqual(summary.top_count, 5)
        self.assertEqual(summary.middle_count, 5)
        self.assertEqual(summary.bottom_count, 5)
        self.assertEqual(summary.spread, 0.10)
        self.assertTrue(summary.middle_monotonicity)
        self.assertEqual(summary.positive_cohort_win_rate, 1.0)
        self.assertEqual(summary.median, 0.10)
        self.assertEqual(summary.worst_period, 0.10)
        self.assertEqual(summary.drawdown, 0.0)
        self.assertEqual(summary.turnover, 0.0)
        self.assertEqual(summary.bottom_bucket_observation_count, 5)
        self.assertEqual(set(summary.cost_stress), {0.5, 1.0, 1.5})
        self.assertEqual(summary.cost_stress, {0.5: 0.10, 1.0: 0.10, 1.5: 0.10})
        self.assertEqual(summary.bid_ask_stress, {0.5: 0.10, 1.0: 0.10, 1.5: 0.10})

    def test_holm_adjustment_requires_complete_sibling_arm_family(self):
        family = {
            "capture_50": 0.01,
            "close_21_dte": 0.02,
            "fixed_10_sessions": 0.03,
            "breach_hold_21_dte": 0.04,
            "assignment_accepting": 0.05,
        }
        complete = summarize_lane(
            self._fifteen(), lane="csp", arm="capture_50", family_raw_p_values=family
        )
        self.assertEqual(complete.raw_p_value, 0.01)
        self.assertEqual(complete.adjusted_p_value, 0.05)

        incomplete = summarize_lane(
            self._fifteen(),
            lane="csp",
            arm="capture_50",
            family_raw_p_values={"capture_50": 0.01, "close_21_dte": 0.02},
        )
        self.assertEqual(incomplete.raw_p_value, 0.01)
        self.assertIsNone(incomplete.adjusted_p_value)

    def test_empty_pmcc_is_no_data(self):
        summary = summarize_lane((), lane="pmcc", arm="pmcc")
        self.assertEqual(summary.status, "no data")


if __name__ == "__main__":
    unittest.main()

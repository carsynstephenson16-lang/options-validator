"""Contract tests for the pure, offline A2 outcome battery boundary."""

from __future__ import annotations

import math
import unittest
from collections import Counter
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
    maximum_resolution_date: str | None = None,
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
        maximum_resolution_date=maximum_resolution_date or resolution_date,
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

    def test_maximum_resolution_must_cover_realized_resolution(self):
        with self.assertRaises(ValueError):
            _outcome(maximum_resolution_date="2025-01-02")
        with self.assertRaises(ValueError):
            _outcome(maximum_resolution_date="2025-01-09")

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

    def test_mapping_outcomes_are_coerced_and_invalid_shapes_fail_closed(self):
        row = _outcome()
        raw = {
            "ticker": row.symbol,
            "decision": row.decision_date,
            "entry": row.entry_date,
            "resolution": row.resolution_date,
            "maximum_resolution": row.maximum_resolution_date,
            "lane": row.lane,
            "parameter_id": row.arm,
            "score": str(row.score),
            "return": str(row.gross_return),
            "cost": str(row.modeled_cost),
            "bid_ask": str(row.bid_ask_cost),
            "net_return": str(row.cost_adjusted_return),
            "accounting": {key: str(value) for key, value in row.components.items()},
            "source_provenance": dict(row.provenance),
        }
        coerced = validate_outcomes((raw,))
        self.assertEqual(coerced[0], row)

        with self.assertRaises(ValueError):
            validate_outcomes(({**raw, "accounting": []},))
        with self.assertRaises(ValueError):
            validate_outcomes(({**raw, "accounting": {1: "0.0"}},))

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
    @staticmethod
    def _board(
        decision: str,
        entry: str,
        resolution: str,
        maximum_resolution: str,
        symbols: tuple[str, ...] = ("AAA", "BBB", "CCC"),
    ) -> tuple[A2Outcome, ...]:
        return tuple(
            _outcome(
                symbol=symbol,
                decision_date=decision,
                entry_date=entry,
                resolution_date=resolution,
                maximum_resolution_date=maximum_resolution,
            )
            for symbol in symbols
        )

    def test_inference_uses_earliest_complete_board_per_iso_week_and_counts_skips(self):
        rows = (
            *self._board("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB")),
            *self._board("2025-01-07", "2025-01-08", "2025-01-09", "2025-01-14"),
            *self._board("2025-01-08", "2025-01-09", "2025-01-10", "2025-01-10"),
            *self._board("2025-01-13", "2025-01-14", "2025-01-15", "2025-01-17"),
            *self._board("2025-01-20", "2025-01-21", "2025-01-22", "2025-01-24", ("AAA",)),
            *self._board("2025-01-27", "2025-01-28", "2025-01-29", "2025-01-31"),
        )
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            expected_symbols=("AAA", "BBB", "CCC"),
            decision_dates=(
                "2025-01-06",
                "2025-01-07",
                "2025-01-08",
                "2025-01-13",
                "2025-01-20",
                "2025-01-27",
            ),
            diagnostics=diagnostics,
        )
        self.assertEqual(
            tuple(dict.fromkeys(row.decision_date for row in accepted)),
            ("2025-01-07", "2025-01-27"),
        )
        self.assertEqual(diagnostics["accepted_board_not_first_session_of_week"], 1)
        self.assertEqual(diagnostics["weeks_without_complete_board"], 1)
        self.assertEqual(diagnostics["weeks_skipped_by_spacing"], 1)

    def test_inference_spacing_uses_ex_ante_maximum_not_realized_resolution(self):
        first = self._board("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-20")
        overlapping = self._board("2025-01-13", "2025-01-14", "2025-01-15", "2025-01-17")
        after_maximum = self._board("2025-01-20", "2025-01-21", "2025-01-22", "2025-01-24")
        accepted = non_overlapping_inference_rows(
            first + overlapping + after_maximum,
            expected_symbols=("AAA", "BBB", "CCC"),
        )
        self.assertEqual(
            tuple(dict.fromkeys(row.decision_date for row in accepted)),
            ("2025-01-06", "2025-01-20"),
        )

    def test_spacing_failure_does_not_promote_a_later_board_in_same_week(self):
        rows = (
            *self._board("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-15"),
            *self._board("2025-01-13", "2025-01-14", "2025-01-14", "2025-01-14"),
            *self._board("2025-01-14", "2025-01-16", "2025-01-16", "2025-01-16"),
        )
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            expected_symbols=("AAA", "BBB", "CCC"),
            diagnostics=diagnostics,
        )
        self.assertEqual({row.decision_date for row in accepted}, {"2025-01-06"})
        self.assertEqual(diagnostics["weeks_skipped_by_spacing"], 1)

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
            maximum_resolution_date="2025-01-20",
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


class EntryTimeBoardTests(unittest.TestCase):
    """A2_AMENDMENT_V1_1 (ledger seq 27) + the 2026-08-15 breach/weekly-cohort
    amendment Definition 2.1: the week's candidate is chosen from the
    ENTRY-TIME board (independent of whether rows later resolved); a
    resolution gap on the chosen day SKIPS the week rather than promoting a
    later, fuller day.  Independent adversarial review 2026-08-30, findings
    F1/F2/F7b/F7c.
    """

    @staticmethod
    def _rows(
        decision: str,
        entry: str,
        resolution: str,
        maximum_resolution: str,
        symbols: tuple[str, ...],
    ) -> tuple[A2Outcome, ...]:
        return tuple(
            _outcome(
                symbol=symbol,
                decision_date=decision,
                entry_date=entry,
                resolution_date=resolution,
                maximum_resolution_date=maximum_resolution,
            )
            for symbol in symbols
        )

    def test_resolution_gap_on_the_chosen_day_skips_the_week_not_promotes_a_later_day(self):
        # F2: day1's entry-time board is the full six names, but only two of
        # them ever resolved (a post-entry data gap) -- below
        # MIN_TERCILE_COHORT_SIZE.  day2, later in the SAME ISO week, has a
        # fully resolved six-name board.  The week must be skipped outright:
        # day2 may never be substituted for day1's candidacy.
        rows = self._rows(
            "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB")
        ) + self._rows(
            "2025-01-08", "2025-01-09", "2025-01-10", "2025-01-13", ("AAA", "BBB", "CCC")
        )
        board_symbols_by_date = {
            "2025-01-06": ("AAA", "BBB", "CCC"),
            "2025-01-08": ("AAA", "BBB", "CCC"),
        }
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            board_symbols_by_date=board_symbols_by_date,
            decision_dates=("2025-01-06", "2025-01-08"),
            diagnostics=diagnostics,
        )
        self.assertEqual(accepted, ())
        self.assertEqual(diagnostics["weeks_skipped_unresolvable_board"], 1)
        self.assertEqual(diagnostics["weeks_without_complete_board"], 0)

    def test_partial_realized_cohort_is_used_not_rejected_for_being_short_of_the_full_board(self):
        # F1: the entry-time board has six names, but only four resolved.
        # Four is still >= MIN_TERCILE_COHORT_SIZE, so the partial cohort is
        # used for inference (skip-not-reject only applies below the floor).
        rows = self._rows(
            "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB", "CCC", "DDD")
        )
        board_symbols_by_date = {"2025-01-06": ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")}
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            board_symbols_by_date=board_symbols_by_date,
            diagnostics=diagnostics,
        )
        self.assertEqual({row.symbol for row in accepted}, {"AAA", "BBB", "CCC", "DDD"})
        self.assertEqual(diagnostics["weeks_without_complete_board"], 0)
        self.assertEqual(diagnostics["weeks_skipped_unresolvable_board"], 0)

    def test_split_entry_date_realized_cohort_is_counted_distinctly_and_skipped(self):
        # F7c: two resolution sub-groups on the chosen day disagree on
        # entry_date (e.g. some names' next session differed).  This is
        # counted separately from "no board at all".
        rows = self._rows(
            "2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB", "CCC")
        ) + self._rows("2025-01-06", "2025-01-08", "2025-01-09", "2025-01-11", ("DDD",))
        board_symbols_by_date = {"2025-01-06": ("AAA", "BBB", "CCC", "DDD")}
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            board_symbols_by_date=board_symbols_by_date,
            diagnostics=diagnostics,
        )
        self.assertEqual(accepted, ())
        self.assertEqual(diagnostics["weeks_skipped_split_entry_date"], 1)
        self.assertEqual(diagnostics["weeks_without_complete_board"], 0)

    def test_entry_time_board_below_the_tercile_floor_never_becomes_a_candidate(self):
        # A two-name entry-time board can never form a top/bottom tercile
        # split; the week has "no usable board", counted distinctly from an
        # unresolvable/partial realized cohort.
        rows = self._rows("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB"))
        board_symbols_by_date = {"2025-01-06": ("AAA", "BBB")}
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(
            rows,
            board_symbols_by_date=board_symbols_by_date,
            diagnostics=diagnostics,
        )
        self.assertEqual(accepted, ())
        self.assertEqual(diagnostics["weeks_without_complete_board"], 1)
        self.assertEqual(diagnostics["weeks_skipped_unresolvable_board"], 0)

    def test_legacy_path_without_a_board_also_enforces_the_tercile_floor(self):
        # F7b: even the legacy (no board_symbols_by_date, no expected_symbols)
        # contract must refuse a cohort too small to form a tercile split --
        # the guard belongs in the splitting function, not only in callers.
        rows = self._rows("2025-01-06", "2025-01-07", "2025-01-08", "2025-01-10", ("AAA", "BBB"))
        diagnostics: Counter[str] = Counter()
        accepted = non_overlapping_inference_rows(rows, diagnostics=diagnostics)
        self.assertEqual(accepted, ())
        self.assertEqual(diagnostics["weeks_without_complete_board"], 1)


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

    def test_nonzero_modeled_cost_has_distinct_half_base_and_one_half_stress(self):
        rows = tuple(
            _outcome(
                symbol=f"C{i}",
                score=float(20 - i),
                gross_return=0.10,
                modeled_cost=0.01 + i * 0.001,
                bid_ask_cost=0.005,
                components={**_CSP_COMPONENTS, "option_pnl": 0.10},
            )
            for i in range(15)
        )
        summary = summarize_lane(rows, lane="csp", arm="capture_50")
        self.assertGreater(summary.cost_stress[1.5], summary.cost_stress[1.0])
        self.assertGreater(summary.cost_stress[1.0], summary.cost_stress[0.5])

    def test_empty_pmcc_is_no_data(self):
        summary = summarize_lane((), lane="pmcc", arm="pmcc")
        self.assertEqual(summary.status, "no data")


if __name__ == "__main__":
    unittest.main()

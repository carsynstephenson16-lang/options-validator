"""Deterministic, offline tests for the research-only robustness subsystem."""

from __future__ import annotations

import csv
import json
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from options_researcher import attractiveness
from options_researcher.robustness import runner
from options_researcher.robustness.models import (
    ExperimentSpec,
    SpecValidationError,
)
from options_researcher.robustness.registry import (
    CheckpointConflictError,
    ExperimentRegistry,
    IncompatibleSchemaError,
)
from options_researcher.robustness.reporting import write_reports
from options_researcher.robustness.runner import run_experiment
from options_researcher.robustness.screening import (
    PanelObservation,
    cost_adjusted_primary_metric,
    evaluate_parameter_variants,
    handoff_finalists,
)
from options_researcher.robustness.stability import (
    ParameterFoldResult,
    StabilityDiagnostic,
    analyze_stability,
)
from options_researcher.robustness.statistics import (
    CircularBlockPermutation,
    empirical_null_test,
    holm_step_down,
)
from options_researcher.robustness.walk_forward import WalkForwardSplitter


def _iso_days(count: int, start: date = date(2025, 1, 2)) -> list[str]:
    return [(start + timedelta(days=offset)).isoformat() for offset in range(count)]


def _spec_dict() -> dict[str, object]:
    return {
        "experiment_name": "rq2-robustness",
        "version": "1",
        "research_question_id": "RQ2-v1",
        "lane": "sell_put",
        "signal_version": "green-v1",
        "dataset_fingerprint": "a" * 64,
        "point_in_time_cutoff": "2026-07-20",
        "train_window": {"start": "2025-01-01", "end": "2025-06-30"},
        "validation_window": {"start": "2025-07-01", "end": "2025-09-30"},
        "test_window": {"start": "2025-10-01", "end": "2026-07-20"},
        "purge_observations": 5,
        "embargo_observations": 2,
        "forward_outcome_horizon": 5,
        "walk_forward_mode": "expanding",
        "train_observations": 20,
        "test_observations": 10,
        "step_observations": 12,
        "cost_model": {"model": "repo-frozen", "stress": 1.0},
        "parameter_grid": [{"parameter_id": "baseline"}, {"parameter_id": "badge-b"}],
        "random_seed": 42,
        "permutation_count": 99,
        "permutation_method": "circular_block",
        "multiple_testing_method": "holm",
        "multiple_testing_alpha": 0.10,
        "git_commit_sha": "b" * 40,
        "status": "registered",
        "claim_label": "Repo-verified",
        "owner_controls": {
            "bucket_count": 3,
            "minimum_adverse_bottom_bucket": 10,
            "holm_sidedness": "one-sided-positive",
            "forward_backstop": "2027-07-23",
        },
    }


def _panel(parameter_id: str = "baseline", lane: str = "sell_put") -> list[PanelObservation]:
    rows: list[PanelObservation] = []
    for day_index, day in enumerate(_iso_days(4)):
        for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC")):
            adjusted_return = float(ticker_index) * 0.02 - 0.01 + day_index * 0.001
            rows.append(
                PanelObservation(
                    panel_date=day,
                    ticker=ticker,
                    lane=lane,
                    parameter_id=parameter_id,
                    score=float(ticker_index),
                    gross_forward_return=adjusted_return + 0.005,
                    modeled_cost=0.005,
                    bid_ask_cost=0.003,
                    forward_cost_adjusted_return=adjusted_return,
                    regime="normal",
                )
            )
    return rows


def _runner_fixture_rows() -> list[PanelObservation]:
    rows: list[PanelObservation] = []
    for parameter_id in ("baseline", "badge-b"):
        for day_index, day in enumerate(_iso_days(60)):
            for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC")):
                adjusted_return = (
                    ticker_index * 0.01
                    + day_index * 0.0001
                    + (0.001 if parameter_id == "badge-b" else 0.0)
                )
                rows.append(
                    PanelObservation(
                        panel_date=day,
                        ticker=ticker,
                        lane="sell_put",
                        parameter_id=parameter_id,
                        score=float(ticker_index),
                        gross_forward_return=adjusted_return + 0.002,
                        modeled_cost=0.002,
                        bid_ask_cost=0.0015,
                        forward_cost_adjusted_return=adjusted_return,
                        regime="normal",
                    )
                )
    return rows


def _stability_diagnostic(gate_outcomes: object) -> StabilityDiagnostic:
    return StabilityDiagnostic(
        parameter_id="baseline",
        neighboring_parameter_performance=None,
        rank_stability=1.0,
        sign_consistency=1.0,
        out_of_sample_decay=0.0,
        ticker_concentration=0.5,
        regime_concentration=0.5,
        window_concentration=0.5,
        minimum_observation_count=30,
        cost_sensitive=False,
        brittle_isolated_peak=False,
        gate_outcomes=gate_outcomes,  # type: ignore[arg-type]
    )


class ExperimentSpecTests(unittest.TestCase):
    def test_deterministic_serialization_hash_and_run_id(self):
        first = ExperimentSpec.from_mapping(_spec_dict())
        shuffled = dict(reversed(list(_spec_dict().items())))
        second = ExperimentSpec.from_mapping(shuffled)
        self.assertEqual(first.canonical_json(), second.canonical_json())
        self.assertEqual(first.config_hash, second.config_hash)
        self.assertEqual(first.run_id, second.run_id)

    def test_incomplete_owner_fields_block(self):
        payload = _spec_dict()
        payload["owner_controls"] = {"bucket_count": 3}
        with self.assertRaisesRegex(SpecValidationError, "owner control"):
            ExperimentSpec.from_mapping(payload)

    def test_overlap_and_unsigned_registration_block(self):
        payload = _spec_dict()
        payload["validation_window"] = {"start": "2025-06-01", "end": "2025-09-30"}
        with self.assertRaisesRegex(SpecValidationError, "overlap"):
            ExperimentSpec.from_mapping(payload)

        spec = ExperimentSpec.from_mapping(_spec_dict())
        with self.assertRaisesRegex(SpecValidationError, "not registered"):
            spec.require_registration([])
        spec.require_registration(
            [{"entry_type": "trial_intent", "hypothesis_id": "RQ2-v1", "seq": 18}]
        )


class WalkForwardTests(unittest.TestCase):
    def test_chronology_purge_embargo_and_no_leakage(self):
        dates = _iso_days(24)
        splitter = WalkForwardSplitter(
            train_observations=8,
            test_observations=4,
            step_observations=6,
            purge_observations=2,
            embargo_observations=2,
            mode="expanding",
        )
        folds = splitter.split(dates)
        self.assertGreaterEqual(len(folds), 2)
        first = folds[0]
        self.assertEqual(first.train_dates, tuple(dates[:6]))
        self.assertEqual(first.purge_dates, tuple(dates[6:8]))
        self.assertEqual(first.test_dates, tuple(dates[8:12]))
        self.assertEqual(first.embargo_dates, tuple(dates[12:14]))
        self.assertLess(max(first.train_dates), min(first.test_dates))
        self.assertTrue(set(first.train_dates).isdisjoint(first.test_dates))
        self.assertGreater(min(folds[1].test_dates), max(first.embargo_dates))

    def test_rolling_window_sparse_dates_and_missing_panel(self):
        dates = [
            "2025-01-02",
            "2025-01-10",
            "2025-02-03",
            "2025-03-17",
            "2025-06-01",
            "2025-09-09",
            "2025-12-31",
        ]
        splitter = WalkForwardSplitter(4, 2, 3, 1, 0, mode="rolling")
        fold = splitter.split(dates)[0]
        self.assertEqual(fold.train_dates, tuple(dates[:3]))
        self.assertEqual(fold.test_dates, tuple(dates[4:6]))
        self.assertEqual(splitter.split([]), ())


class ScreeningTests(unittest.TestCase):
    def test_cost_adjusted_spread_and_lane_isolation(self):
        result = cost_adjusted_primary_metric(_panel(), bucket_count=3)
        self.assertAlmostEqual(result.spread, 0.04)
        self.assertEqual(result.top_count, 4)
        self.assertEqual(result.bottom_count, 4)
        with self.assertRaisesRegex(ValueError, "single lane"):
            cost_adjusted_primary_metric(
                [*_panel(), *_panel(parameter_id="other", lane="covered_call")],
                bucket_count=3,
            )

    def test_workers_are_deterministic(self):
        rows = [*_panel("baseline"), *_panel("badge-b")]
        serial = evaluate_parameter_variants(rows, bucket_count=3, workers=1)
        parallel = evaluate_parameter_variants(rows, bucket_count=3, workers=2)
        self.assertEqual(serial, parallel)

    def test_lumibot_handoff_receives_only_finalists(self):
        received: list[str] = []

        class Adapter:
            def validate_finalists(self, parameter_ids: tuple[str, ...]) -> object:
                received.extend(parameter_ids)
                return {"count": len(parameter_ids)}

        result = handoff_finalists(Adapter(), ("winner",))
        self.assertEqual(received, ["winner"])
        self.assertEqual(result, {"count": 1})

    def test_production_ranking_path_is_unchanged(self):
        cards = [{"id": "a", "yield": 1.0}, {"id": "b", "yield": 2.0}]
        before = [
            row["id"]
            for row in attractiveness.rank_cards(
                [dict(row) for row in cards], "yield", higher_is_better=True
            )
        ]
        evaluate_parameter_variants(_panel(), bucket_count=3)
        after = [
            row["id"]
            for row in attractiveness.rank_cards(
                [dict(row) for row in cards], "yield", higher_is_better=True
            )
        ]
        self.assertEqual(before, after)


class StatisticsTests(unittest.TestCase):
    def test_block_permutation_preserves_contiguous_blocks_and_seed(self):
        method = CircularBlockPermutation(block_size=2)
        first = method.permute(tuple(range(8)), seed=7)
        second = method.permute(tuple(range(8)), seed=7)
        self.assertEqual(first, second)
        self.assertEqual(
            sorted(tuple(first[index : index + 2]) for index in range(0, 8, 2)),
            [(0, 1), (2, 3), (4, 5), (6, 7)],
        )

    def test_finite_sample_p_value(self):
        result = empirical_null_test(
            observed=3.0,
            null_values=(0.0, 1.0, 2.0, 4.0),
            alternative="greater",
        )
        self.assertEqual(result.raw_p_value, 2 / 5)
        self.assertAlmostEqual(result.effect_size, 1.25)

    def test_holm_reference_case(self):
        adjusted = holm_step_down(
            {"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.20},
            alpha=0.05,
        )
        self.assertAlmostEqual(adjusted["a"].adjusted_p_value, 0.04)
        self.assertAlmostEqual(adjusted["c"].adjusted_p_value, 0.09)
        self.assertAlmostEqual(adjusted["b"].adjusted_p_value, 0.09)
        self.assertTrue(adjusted["a"].rejected)
        self.assertFalse(adjusted["b"].rejected)


class StabilityTests(unittest.TestCase):
    def test_isolated_peak_and_concentration_are_flagged(self):
        results = (
            ParameterFoldResult(
                parameter_id="peak",
                fold=0,
                train_metric=0.10,
                test_metric=0.09,
                observation_count=30,
                ticker_contributions={"AAA": 0.08, "BBB": 0.01},
                regime_contributions={"calm": 0.09},
                cost_stress_metrics={1.0: 0.09, 1.5: 0.01},
                neighbor_ids=("left", "right"),
            ),
            ParameterFoldResult("left", 0, 0.02, 0.01, 30),
            ParameterFoldResult("right", 0, 0.01, 0.00, 30),
        )
        diagnostic = analyze_stability("peak", results, minimum_observations=10)
        self.assertTrue(diagnostic.brittle_isolated_peak)
        self.assertGreater(diagnostic.ticker_concentration, 0.8)
        self.assertTrue(diagnostic.cost_sensitive)

    def test_cost_sensitivity_ignores_a_failing_unpinned_higher_cost_arm(self):
        diagnostic = analyze_stability(
            "baseline",
            (
                ParameterFoldResult(
                    parameter_id="baseline",
                    fold=0,
                    train_metric=0.10,
                    test_metric=0.10,
                    observation_count=30,
                    cost_stress_metrics={1.0: 0.10, 1.5: 0.08, 2.0: -0.01},
                ),
            ),
            minimum_observations=10,
        )
        self.assertFalse(diagnostic.cost_sensitive)


class RegistryAndReportTests(unittest.TestCase):
    def _run_fixture(
        self,
        base: Path,
        *,
        diagnostic: StabilityDiagnostic | None = None,
    ) -> tuple[list[dict[str, object]], tuple[Path, Path, Path]]:
        payload = _spec_dict()
        payload["permutation_count"] = 9
        spec = ExperimentSpec.from_mapping(payload)
        with ExperimentRegistry(base / "registry.sqlite3") as registry:
            if diagnostic is None:
                paths = run_experiment(
                    spec,
                    _runner_fixture_rows(),
                    [{"entry_type": "trial_intent", "hypothesis_id": "RQ2-v1"}],
                    registry,
                    output_directory=base / "reports",
                    matrix_root=base / "matrices",
                )
            else:
                with patch.object(runner, "analyze_stability", return_value=diagnostic):
                    paths = run_experiment(
                        spec,
                        _runner_fixture_rows(),
                        [{"entry_type": "trial_intent", "hypothesis_id": "RQ2-v1"}],
                        registry,
                        output_directory=base / "reports",
                        matrix_root=base / "matrices",
                    )
            return registry.task_records(spec.run_id), paths

    def test_idempotent_resume_and_conflict_detection(self):
        spec = ExperimentSpec.from_mapping(_spec_dict())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "registry.sqlite3"
            with ExperimentRegistry(path) as registry:
                registry.register_run(spec)
                registry.register_run(spec)
                payload = {
                    "metrics": {"spread": 0.04},
                    "raw_p_value": 0.2,
                    "adjusted_p_value": 0.3,
                    "gate_outcomes": {"sample": "PASS"},
                    "artifact_paths": [],
                }
                registry.record_completed_task(spec.run_id, 0, "baseline", payload)
                registry.record_completed_task(spec.run_id, 0, "baseline", payload)
                self.assertEqual(registry.completed_tasks(spec.run_id), {(0, "baseline")})
                changed = {**payload, "metrics": {"spread": 9.0}}
                with self.assertRaises(CheckpointConflictError):
                    registry.record_completed_task(spec.run_id, 0, "baseline", changed)

    def test_schema_rejection_and_corrupt_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "future.sqlite3"
            connection = sqlite3.connect(path)
            connection.execute("PRAGMA user_version = 999")
            connection.close()
            with self.assertRaises(IncompatibleSchemaError):
                ExperimentRegistry(path)

            corrupt = Path(tmp) / "corrupt.sqlite3"
            corrupt.write_text("not sqlite", encoding="utf-8")
            with self.assertRaises(IncompatibleSchemaError):
                ExperimentRegistry(corrupt)

    def test_json_csv_and_markdown_reports_are_reproducible(self):
        spec = ExperimentSpec.from_mapping(_spec_dict())
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with ExperimentRegistry(base / "registry.sqlite3") as registry:
                registry.register_run(spec)
                registry.record_completed_task(
                    spec.run_id,
                    0,
                    "baseline",
                    {
                        "metrics": {
                            "spread": 0.04,
                            "top_count": 12,
                            "bottom_count": 12,
                        },
                        "raw_p_value": 0.2,
                        "adjusted_p_value": 0.2,
                        "gate_outcomes": {"registration": "PASS"},
                        "artifact_paths": [],
                    },
                )
                paths = write_reports(registry, spec.run_id, base / "reports")
            self.assertEqual({path.suffix for path in paths}, {".json", ".csv", ".md"})
            payload = json.loads(next(path for path in paths if path.suffix == ".json").read_text())
            self.assertEqual(payload["research_only"], True)
            markdown = next(path for path in paths if path.suffix == ".md").read_text()
            self.assertIn("RESEARCH-ONLY", markdown)
            self.assertIn("No production recommendation", markdown)

    def test_runner_surfaces_all_stability_gates_in_registry_and_reports(self):
        expected_gates = {
            "registration": "PASS",
            "adverse_bottom_bucket": "PASS",
            "holm": "FAIL",
            "production_promotion": "BLOCKED",
            "minimum_observations": "PASS",
            "sign_consistency": "PASS",
            "ticker_concentration": "FAIL",
            "regime_concentration": "FAIL",
            "window_concentration": "PASS",
            "cost_stress": "PASS",
            "brittleness": "PASS",
        }
        with tempfile.TemporaryDirectory() as tmp:
            records, paths = self._run_fixture(Path(tmp))
            json_payload = json.loads(next(path for path in paths if path.suffix == ".json").read_text())
            csv_rows = list(
                csv.DictReader(
                    next(path for path in paths if path.suffix == ".csv").read_text().splitlines()
                )
            )
            markdown = next(path for path in paths if path.suffix == ".md").read_text()

        for record, json_task, csv_row in zip(
            records, json_payload["tasks"], csv_rows, strict=True
        ):
            metrics = record["metrics"]
            self.assertIsInstance(metrics, dict)
            self.assertEqual(metrics["spread"], 0.02)
            self.assertEqual(record["raw_p_value"], 1.0)
            self.assertEqual(record["adjusted_p_value"], 1.0)
            gates = record["gate_outcomes"]
            self.assertEqual(gates, expected_gates)
            self.assertEqual(gates["registration"], "PASS")
            self.assertEqual(gates["adverse_bottom_bucket"], "PASS")
            self.assertEqual(gates["holm"], "FAIL")
            self.assertEqual(gates["production_promotion"], "BLOCKED")
            self.assertEqual(json_task["gate_outcomes"], expected_gates)
            self.assertEqual(json.loads(csv_row["gate_outcomes"]), expected_gates)
        for key, value in expected_gates.items():
            self.assertIn(f"{key}={value}", markdown)

    def test_runner_rejects_stability_gate_collision_with_runner_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "stability gate"):
                self._run_fixture(Path(tmp), diagnostic=_stability_diagnostic((("holm", "FAIL"),)))

    def test_runner_rejects_empty_duplicate_and_malformed_stability_gates(self):
        cases = {
            "empty": (),
            "duplicate": (("minimum_observations", "PASS"), ("minimum_observations", "FAIL")),
            "empty-key": (("", "PASS"),),
            "empty-value": (("minimum_observations", ""),),
            "not-a-pair": (("minimum_observations",),),
        }
        for name, gate_outcomes in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError, "stability gate"):
                    self._run_fixture(
                        Path(tmp), diagnostic=_stability_diagnostic(gate_outcomes)
                    )

    def test_markdown_discloses_arithmetic_stress_sensitivity_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            _records, paths = self._run_fixture(Path(tmp))
            markdown = next(path for path in paths if path.suffix == ".md").read_text()

        self.assertIn(
            "Total modeled-cost stress (0.5x / 1.0x / 1.5x; arithmetic sensitivity; "
            "same-sample point estimates; no stress-arm CI; all modeled cost, including any "
            "commission embedded upstream, is scaled arithmetically)",
            markdown,
        )
        self.assertIn(
            "Bid/ask stress (0.5x / 1.0x / 1.5x; arithmetic sensitivity; same-sample point "
            "estimates; no stress-arm CI)",
            markdown,
        )

    def test_runner_resumes_without_rewriting_completed_tasks(self):
        payload = _spec_dict()
        payload["permutation_count"] = 9
        spec = ExperimentSpec.from_mapping(payload)
        rows: list[PanelObservation] = []
        for parameter_id in ("baseline", "badge-b"):
            for day_index, day in enumerate(_iso_days(60)):
                for ticker_index, ticker in enumerate(("AAA", "BBB", "CCC")):
                    adjusted_return = (
                        ticker_index * 0.01
                        + day_index * 0.0001
                        + (0.001 if parameter_id == "badge-b" else 0.0)
                    )
                    rows.append(
                        PanelObservation(
                            panel_date=day,
                            ticker=ticker,
                            lane="sell_put",
                            parameter_id=parameter_id,
                            score=float(ticker_index),
                            gross_forward_return=adjusted_return + 0.002,
                            modeled_cost=0.002,
                            bid_ask_cost=0.0015,
                            forward_cost_adjusted_return=adjusted_return,
                            regime="normal",
                        )
                    )
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with ExperimentRegistry(base / "registry.sqlite3") as registry:
                first = run_experiment(
                    spec,
                    rows,
                    [
                        {
                            "entry_type": "trial_intent",
                            "hypothesis_id": "RQ2-v1",
                        }
                    ],
                    registry,
                    output_directory=base / "reports",
                    workers=1,
                    matrix_root=base / "matrices",
                )
                task_count = len(registry.task_records(spec.run_id))
                second = run_experiment(
                    spec,
                    rows,
                    [
                        {
                            "entry_type": "trial_intent",
                            "hypothesis_id": "RQ2-v1",
                        }
                    ],
                    registry,
                    output_directory=base / "reports",
                    workers=2,
                    matrix_root=base / "matrices",
                )
                self.assertEqual(len(registry.task_records(spec.run_id)), task_count)
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

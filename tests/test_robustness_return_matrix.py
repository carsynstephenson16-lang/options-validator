"""Deterministic, offline tests for the robustness return-matrix observability
artifact (options_researcher/robustness/return_matrix.py) and its wiring into
runner.py/reporting.py.

Mirrors tests/test_robustness_layer.py's fixture conventions (small helpers
duplicated locally, not imported cross-module: ``import tests.test_x`` does
not resolve in this environment because ``tests/`` has no ``__init__.py`` and
a same-named regular package exists under .venv/site-packages -- the
documented test entrypoint is ``unittest discover -s tests``, not dotted
imports).

The one invariant every test here ultimately serves: registered robustness
outputs (SQLite runs/tasks rows; JSON/CSV/Markdown reports) must be
byte-identical whether return-matrix capture is on, off, or failing.
"""

from __future__ import annotations

import contextlib
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

import config
import metrics
from options_researcher.robustness.models import ExperimentSpec
from options_researcher.robustness.registry import ExperimentRegistry
from options_researcher.robustness.return_matrix import (
    ReturnMatrixError,
    ReturnMatrixWriter,
    _Row,
    measured_trial_sr_stats,
    write_manifest_once,
)
from options_researcher.robustness.runner import run_experiment
from options_researcher.robustness.screening import (
    PanelObservation,
    cost_adjusted_primary_metric,
    daily_spread_series,
)
from research.hashing import sha256_file


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
        "permutation_count": 9,
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


def _matrix_panel(parameter_id: str, day_count: int = 6, lane: str = "sell_put"):
    rows: list[PanelObservation] = []
    for day_index, day in enumerate(_iso_days(day_count)):
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


def _60day_two_variant_panel() -> list[PanelObservation]:
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


class ReturnMatrixWriterTests(unittest.TestCase):
    """(a) roundtrip and (b) alignment invariants."""

    def _write_two_variants(self, root: Path) -> dict[str, object]:
        spec = ExperimentSpec.from_mapping(_spec_dict())
        writer = ReturnMatrixWriter(spec, matrix_root=root)
        dates = _iso_days(6)
        date_to_fold = {d: 0 for d in dates}
        for parameter_id in ("baseline", "badge-b"):
            writer.capture(
                parameter_id,
                _matrix_panel(parameter_id),
                bucket_count=3,
                date_to_fold=date_to_fold,
            )
        manifest = writer.finalize()
        self.assertIsNotNone(manifest)
        return manifest

    def test_roundtrip_shape_matches_manifest_and_sha256(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._write_two_variants(Path(tmp) / "matrices")
            parquet_path = Path(manifest["output"]["path"])
            frame = pd.read_parquet(parquet_path)
            pivot = frame.pivot(
                index="panel_date", columns="parameter_id", values="cost_adjusted_return"
            )
            self.assertEqual(
                pivot.shape,
                (manifest["matrix_shape"]["periods_t"], manifest["matrix_shape"]["variants_m"]),
            )
            self.assertEqual(sha256_file(parquet_path), manifest["output"]["sha256"])

    def test_alignment_identical_dates_per_variant_no_nan_or_inf(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._write_two_variants(Path(tmp) / "matrices")
            frame = pd.read_parquet(Path(manifest["output"]["path"]))
            date_sets = frame.groupby("parameter_id")["panel_date"].apply(
                lambda series: frozenset(series)
            )
            self.assertEqual(len(set(date_sets)), 1)
            values = frame["cost_adjusted_return"].to_numpy(dtype=float)
            self.assertFalse(np.isnan(values).any())
            self.assertTrue(np.isfinite(values).all())

    def test_daily_spread_series_matches_registered_primary_metric(self):
        # Cross-check that the captured values are the SAME floats the
        # registered cost_adjusted_primary_metric computes, not a
        # re-derivation that happens to look similar.
        rows = _matrix_panel("baseline")
        metric = cost_adjusted_primary_metric(rows, bucket_count=3)
        series = daily_spread_series(rows, bucket_count=3)
        self.assertEqual(len(series), len(metric.daily_spreads))
        for (_, spread_value, _), expected in zip(series, metric.daily_spreads, strict=True):
            self.assertEqual(spread_value, expected)


class WriteOnceTests(unittest.TestCase):
    """(f) write-once manifest semantics."""

    def test_identical_retry_is_a_noop_and_differing_bytes_refuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "return_matrix.manifest.json"
            write_manifest_once(path, '{"a":1}')
            first_bytes = path.read_bytes()
            write_manifest_once(path, '{"a":1}')  # identical retry: benign no-op
            self.assertEqual(path.read_bytes(), first_bytes)
            with self.assertRaises(ReturnMatrixError):
                write_manifest_once(path, '{"a":2}')
            # refusal must not have clobbered the original content
            self.assertEqual(path.read_bytes(), first_bytes)


class MeasuredTrialSrStatsTests(unittest.TestCase):
    """(d) DSR-from-matrix numeric vector against hand-derived arithmetic."""

    # Three variants x 8 daily cost-adjusted-return observations each.
    # Hand arithmetic (also cross-checked with numpy in the derivation
    # session; reproduced here so the assertion is self-contained):
    #   A = [1..8]:      mean=4.5, sample var (ddof=1) = 42/7 = 6.0,
    #                     std=sqrt(6)=2.449489742783178, SR=4.5/std=1.8371173070873836
    #   B = [8..1]:       same multiset as A (just reordered) -> identical
    #                     mean/var/std/SR = 1.8371173070873836
    #   C = [4,5,4,5,...]: mean=4.5, deviations +/-0.5 each,
    #                     sum(sq)=8*0.25=2.0, sample var=2/7=0.2857142857142857,
    #                     std=sqrt(2/7)=0.5345224838248488, SR=4.5/std=8.418729120241368
    #   mean_trial_sr = (1.8371173070873836*2 + 8.418729120241368) / 3
    #                 = 4.030987911472045
    #   trial_sr_variance (ddof=1, n=3) = 14.43920468634936
    VALUES_A = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
    VALUES_B = [8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.0, 1.0]
    VALUES_C = [4.0, 5.0, 4.0, 5.0, 4.0, 5.0, 4.0, 5.0]
    SR_A = 1.8371173070873836
    SR_C = 8.418729120241368
    MEAN_TRIAL_SR = 4.030987911472045
    TRIAL_SR_VARIANCE = 14.43920468634936
    # dsr() of variant A against the trial population above, T=8, skew=0.0,
    # kurt=1.7619047619047619 (metrics.sample_moments(A)); sr_star =
    # metrics.expected_max_sr(MEAN_TRIAL_SR, TRIAL_SR_VARIANCE, 3) =
    # 7.2715557525820085; psr(SR_A, sr_star, 8, skew, kurt) underflows the
    # normal CDF to exactly 0.0 (SR_A sits far below sr_star).
    EXPECTED_DSR_A = 0.0

    def _write_three_variants(self, root: Path) -> Path:
        spec = ExperimentSpec.from_mapping(_spec_dict())
        writer = ReturnMatrixWriter(spec, matrix_root=root)
        dates = _iso_days(8)
        date_to_fold = {d: 0 for d in dates}
        for parameter_id, values in (
            ("var-a", self.VALUES_A),
            ("var-b", self.VALUES_B),
            ("var-c", self.VALUES_C),
        ):
            frame_rows = [
                (date_str, value, 1) for date_str, value in zip(dates, values, strict=True)
            ]
            # Bypass daily_spread_series (which needs a PanelObservation
            # cross-section) and append hand-built rows directly, since this
            # test is exercising measured_trial_sr_stats' arithmetic on a
            # known vector, not the panel-to-spread derivation (covered by
            # test_daily_spread_series_matches_registered_primary_metric
            # above).
            for panel_date, value, observation_count in frame_rows:
                writer._rows.append(
                    _Row(
                        parameter_id=parameter_id,
                        panel_date=panel_date,
                        cost_adjusted_return=value,
                        fold=date_to_fold[panel_date],
                        observation_count=observation_count,
                    )
                )
        manifest = writer.finalize()
        return Path(manifest["output"]["path"])

    def test_measured_trial_sr_stats_matches_hand_derivation(self):
        with tempfile.TemporaryDirectory() as tmp:
            parquet_path = self._write_three_variants(Path(tmp) / "matrices")
            mean_trial_sr, trial_sr_variance, n_trials = measured_trial_sr_stats(parquet_path)
            self.assertEqual(n_trials, 3)
            self.assertAlmostEqual(mean_trial_sr, self.MEAN_TRIAL_SR, places=9)
            self.assertAlmostEqual(trial_sr_variance, self.TRIAL_SR_VARIANCE, places=9)

    def test_dsr_of_best_variant_matches_hand_computed_expected_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            parquet_path = self._write_three_variants(Path(tmp) / "matrices")
            mean_trial_sr, trial_sr_variance, n_trials = measured_trial_sr_stats(parquet_path)
            skew, kurt = metrics.sample_moments(self.VALUES_A)
            value = metrics.dsr(
                self.SR_A,
                len(self.VALUES_A),
                skew,
                kurt,
                trial_sr_variance=trial_sr_variance,
                n_trials=n_trials,
                mean_trial_sr=mean_trial_sr,
            )
            self.assertAlmostEqual(value, self.EXPECTED_DSR_A, places=9)

    def test_raises_below_dsr_min_n_trials(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "matrices"
            spec = ExperimentSpec.from_mapping(_spec_dict())
            writer = ReturnMatrixWriter(spec, matrix_root=root)
            dates = _iso_days(8)
            date_to_fold = {d: 0 for d in dates}
            # Only one usable variant -- below config.DSR_MIN_N_TRIALS.
            for panel_date, value in zip(dates, self.VALUES_A, strict=True):
                writer._rows.append(
                    _Row(
                        parameter_id="only-variant",
                        panel_date=panel_date,
                        cost_adjusted_return=value,
                        fold=date_to_fold[panel_date],
                        observation_count=1,
                    )
                )
            manifest = writer.finalize()
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest["matrix_shape"]["variants_m"], 1)
            self.assertGreaterEqual(config.DSR_MIN_N_TRIALS, 2)  # sanity: floor is >= 2
            with self.assertRaises(ReturnMatrixError):
                measured_trial_sr_stats(Path(manifest["output"]["path"]))


class FailSafeTests(unittest.TestCase):
    """(e) a capture/finalize failure never breaks the run."""

    def _fixture(self):
        spec = ExperimentSpec.from_mapping(_spec_dict())
        rows = _60day_two_variant_panel()
        records = [{"entry_type": "trial_intent", "hypothesis_id": "RQ2-v1"}]
        return spec, rows, records

    def test_capture_raising_every_call_does_not_break_the_run(self):
        spec, rows, records = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch.object(
                ReturnMatrixWriter, "capture", side_effect=OSError("simulated capture failure")
            ):
                with ExperimentRegistry(base / "registry.sqlite3") as registry:
                    paths = run_experiment(
                        spec,
                        rows,
                        records,
                        registry,
                        output_directory=base / "reports",
                        matrix_root=base / "matrices",
                        workers=1,
                    )
                    self.assertEqual(registry.run_record(spec.run_id)["status"], "COMPLETE")
                    self.assertEqual(len(registry.task_records(spec.run_id)), 6)  # 3 folds x 2 params
            for path in paths:
                self.assertTrue(path.exists())
            self.assertFalse((base / "matrices").exists())

    def test_finalize_raising_does_not_break_the_run(self):
        spec, rows, records = self._fixture()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with mock.patch.object(
                ReturnMatrixWriter, "finalize", side_effect=OSError("simulated disk error")
            ):
                with ExperimentRegistry(base / "registry.sqlite3") as registry:
                    paths = run_experiment(
                        spec,
                        rows,
                        records,
                        registry,
                        output_directory=base / "reports",
                        matrix_root=base / "matrices",
                        workers=1,
                    )
                    self.assertEqual(registry.run_record(spec.run_id)["status"], "COMPLETE")
                    self.assertEqual(len(registry.task_records(spec.run_id)), 6)  # 3 folds x 2 params
            for path in paths:
                self.assertTrue(path.exists())


class ByteIdentityPinTests(unittest.TestCase):
    """(c) THE PIN: registered outputs are byte-identical whether capture
    succeeds or is monkeypatched to always raise -- except exactly one
    additive Governance bullet line in the Markdown report.

    Design decision (documented per the task brief's "decide precisely"
    instruction): JSON and CSV reports never reference the return matrix at
    all (write_reports only threads matrix_root into the Markdown bullet),
    so they are pinned FULLY byte-identical with no exception. Markdown is
    pinned line-for-line identical except the one Governance DSR bullet,
    whose text differs by construction (it reports whether the matrix is
    available) -- this is the stricter of the two workable designs named in
    the brief: JSON/CSV get zero tolerance, Markdown gets a single named,
    asserted line.

    Wall-clock timestamps (runs.started_at_utc / runs.tasks.completed_at_utc)
    are the one other source of nondeterminism between two independent
    run_experiment invocations, entirely unrelated to return-matrix capture
    (finish_run() always stamps "now"). Both invocations here run under a
    frozen registry._utc_now so this does not confound the comparison.
    """

    FIXED_TS = "2026-01-01T00:00:00+00:00"

    def _fixture(self):
        spec = ExperimentSpec.from_mapping(_spec_dict())
        rows = _60day_two_variant_panel()
        records = [{"entry_type": "trial_intent", "hypothesis_id": "RQ2-v1"}]
        return spec, rows, records

    def _run(self, spec, rows, records, base: Path, *, break_capture: bool):
        patcher = (
            mock.patch.object(
                ReturnMatrixWriter, "capture", side_effect=OSError("simulated capture failure")
            )
            if break_capture
            else contextlib.nullcontext()
        )
        with mock.patch(
            "options_researcher.robustness.registry._utc_now", return_value=self.FIXED_TS
        ):
            with patcher:
                with ExperimentRegistry(base / "registry.sqlite3") as registry:
                    paths = run_experiment(
                        spec,
                        rows,
                        records,
                        registry,
                        output_directory=base / "reports",
                        matrix_root=base / "matrices",
                        workers=1,
                    )
                    run_record = registry.run_record(spec.run_id)
                    task_records = registry.task_records(spec.run_id)
        return paths, run_record, task_records

    def test_reports_and_registry_rows_are_pinned(self):
        spec, rows, records = self._fixture()
        with (
            tempfile.TemporaryDirectory() as tmp_a,
            tempfile.TemporaryDirectory() as tmp_b,
        ):
            base_a, base_b = Path(tmp_a), Path(tmp_b)
            paths_a, run_a, tasks_a = self._run(spec, rows, records, base_a, break_capture=False)
            paths_b, run_b, tasks_b = self._run(spec, rows, records, base_b, break_capture=True)

            # SQLite runs/tasks rows: fully identical (frozen clock).
            self.assertEqual(run_a, run_b)
            self.assertEqual(tasks_a, tasks_b)

            json_a = next(p for p in paths_a if p.suffix == ".json").read_bytes()
            json_b = next(p for p in paths_b if p.suffix == ".json").read_bytes()
            self.assertEqual(json_a, json_b)

            csv_a = next(p for p in paths_a if p.suffix == ".csv").read_bytes()
            csv_b = next(p for p in paths_b if p.suffix == ".csv").read_bytes()
            self.assertEqual(csv_a, csv_b)

            md_a = next(p for p in paths_a if p.suffix == ".md").read_text().splitlines()
            md_b = next(p for p in paths_b if p.suffix == ".md").read_text().splitlines()
            self.assertEqual(len(md_a), len(md_b))
            diffs = [(i, a, b) for i, (a, b) in enumerate(zip(md_a, md_b)) if a != b]
            self.assertEqual(len(diffs), 1, f"expected exactly one differing line, got: {diffs}")
            _, line_a, line_b = diffs[0]
            self.assertTrue(line_a.startswith("- DSR (measured-from-return-matrix):"))
            self.assertTrue(line_b.startswith("- DSR (measured-from-return-matrix):"))
            self.assertNotIn("matrix unavailable", line_a)
            self.assertIn("matrix unavailable", line_b)

            # And the working-capture path really did produce a matrix.
            self.assertTrue((base_a / "matrices").exists())
            self.assertFalse((base_b / "matrices").exists())


if __name__ == "__main__":
    unittest.main()

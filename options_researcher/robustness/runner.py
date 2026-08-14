"""End-to-end deterministic runner over precomputed, point-in-time panel rows."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping, Sequence

from options_researcher.robustness.models import ExperimentSpec, SpecValidationError
from options_researcher.robustness.registry import ExperimentRegistry
from options_researcher.robustness.reporting import write_reports
from options_researcher.robustness.return_matrix import DEFAULT_MATRIX_ROOT, ReturnMatrixWriter
from options_researcher.robustness.screening import (
    LumibotFinalistAdapter,
    PanelObservation,
    PrimaryMetric,
    cost_adjusted_primary_metric,
    handoff_finalists,
)
from options_researcher.robustness.stability import (
    ParameterFoldResult,
    analyze_stability,
)
from options_researcher.robustness.statistics import (
    CircularBlockPermutation,
    empirical_null_test,
    holm_step_down,
)
from options_researcher.robustness.walk_forward import WalkForwardSplitter

logger = logging.getLogger(__name__)

PANEL_FIELDS = {
    "panel_date",
    "ticker",
    "lane",
    "parameter_id",
    "score",
    "gross_forward_return",
    "modeled_cost",
    "bid_ask_cost",
    "forward_cost_adjusted_return",
    "regime",
}

_REQUIRED_STABILITY_GATE_KEYS = {
    "minimum_observations",
    "sign_consistency",
    "ticker_concentration",
    "regime_concentration",
    "window_concentration",
    "cost_stress",
    "brittleness",
}
_VALID_STABILITY_GATE_OUTCOMES = {"PASS", "FAIL", "BLOCKED"}


@dataclass(frozen=True, slots=True)
class _ComputedTask:
    metric: PrimaryMetric
    train_spread: float
    audit_ranges: dict[str, dict[str, str] | None]
    cost_stress: dict[float, float]
    bid_ask_stress: dict[float, float]


def _merge_stability_gate_outcomes(
    runner_gates: Mapping[str, str], stability_gates: object
) -> dict[str, str]:
    if not isinstance(stability_gates, (tuple, list)) or not stability_gates:
        raise ValueError("stability gate outcomes must be non-empty pairs")
    validated: dict[str, str] = {}
    for gate in stability_gates:
        if not isinstance(gate, tuple) or len(gate) != 2:
            raise ValueError("stability gate outcomes must contain string pairs")
        key, value = gate
        if (
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, str)
            or value not in _VALID_STABILITY_GATE_OUTCOMES
        ):
            raise ValueError("stability gate outcomes must contain valid string pairs")
        if key in validated:
            raise ValueError(f"duplicate stability gate outcome {key!r}")
        if key in runner_gates:
            raise ValueError(f"stability gate outcome collides with runner gate {key!r}")
        validated[key] = value
    if not _REQUIRED_STABILITY_GATE_KEYS.issubset(validated):
        raise ValueError("stability gate outcomes must contain the complete stability gate set")
    return {**runner_gates, **validated}


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_spec(path: str | Path) -> ExperimentSpec:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecValidationError(f"cannot read experiment specification: {exc}") from exc
    if not isinstance(payload, dict):
        raise SpecValidationError("experiment specification root must be an object")
    return ExperimentSpec.from_mapping(payload)


def load_panels(path: str | Path) -> tuple[PanelObservation, ...]:
    panel_path = Path(path)
    try:
        with panel_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = PANEL_FIELDS - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"panel CSV missing field(s): {sorted(missing)}")
            rows = tuple(
                PanelObservation(
                    panel_date=row["panel_date"],
                    ticker=row["ticker"],
                    lane=row["lane"],
                    parameter_id=row["parameter_id"],
                    score=float(row["score"]),
                    gross_forward_return=float(row["gross_forward_return"]),
                    modeled_cost=float(row["modeled_cost"]),
                    bid_ask_cost=float(row["bid_ask_cost"]),
                    forward_cost_adjusted_return=float(row["forward_cost_adjusted_return"]),
                    regime=row["regime"],
                )
                for row in reader
            )
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"cannot read panel CSV: {exc}") from exc
    return rows


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SpecValidationError(f"cannot resolve git HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def doctor(
    spec: ExperimentSpec,
    panels_path: str | Path,
    ledger_records: Sequence[Mapping[str, object]],
    *,
    repo_root: str | Path,
) -> dict[str, object]:
    spec.require_registration(ledger_records)
    actual_fingerprint = file_sha256(panels_path)
    if actual_fingerprint != spec.dataset_fingerprint:
        raise SpecValidationError(
            "dataset fingerprint mismatch: specification does not identify this panel file"
        )
    head = _git_head(Path(repo_root))
    if head != spec.git_commit_sha:
        raise SpecValidationError(
            f"git HEAD {head} does not match registered SHA {spec.git_commit_sha}"
        )
    rows = load_panels(panels_path)
    if not rows:
        raise SpecValidationError("panel file is empty")
    if {row.lane for row in rows} != {spec.lane}:
        raise SpecValidationError("panel lane does not match the immutable specification")
    expected_parameters = {
        str(dict(parameter)["parameter_id"]) for parameter in spec.parameter_grid
    }
    actual_parameters = {row.parameter_id for row in rows}
    if actual_parameters != expected_parameters:
        raise SpecValidationError("panel parameter ids do not match the immutable parameter grid")
    cutoff = spec.point_in_time_cutoff
    if max(row.panel_date for row in rows) > cutoff:
        raise SpecValidationError("panel contains observations after point_in_time_cutoff")
    surfaces = {
        parameter_id: {
            (row.panel_date, row.ticker) for row in rows if row.parameter_id == parameter_id
        }
        for parameter_id in actual_parameters
    }
    first_surface = next(iter(surfaces.values()))
    if any(surface != first_surface for surface in surfaces.values()):
        raise SpecValidationError(
            "parameter variants do not share the same date/ticker panel surface"
        )
    return {
        "status": "PASS",
        "run_id": spec.run_id,
        "rows": len(rows),
        "parameters": sorted(actual_parameters),
        "lane": spec.lane,
        "network_calls": 0,
        "production_ranking_changed": False,
    }


def _permutation_result(
    rows: Sequence[PanelObservation],
    *,
    observed: float,
    bucket_count: int,
    block_size: int,
    permutations: int,
    seed: int,
) -> tuple[float, float, tuple[float, float]]:
    ordered = sorted(rows, key=lambda row: (row.panel_date, row.ticker))
    grouped_rows: list[list[PanelObservation]] = []
    for row in ordered:
        if not grouped_rows or grouped_rows[-1][0].panel_date != row.panel_date:
            grouped_rows.append([])
        grouped_rows[-1].append(row)
    values = tuple(
        tuple(row.forward_cost_adjusted_return for row in daily) for daily in grouped_rows
    )
    method = CircularBlockPermutation(block_size=block_size)
    null_values: list[float] = []
    for iteration in range(permutations):
        permuted_days = method.permute(values, seed=seed + iteration)
        permuted_rows: list[PanelObservation] = []
        for daily_rows, daily_values in zip(grouped_rows, permuted_days, strict=True):
            if len(daily_rows) != len(daily_values):
                raise ValueError("daily panel shape changes across the null permutation")
            permuted_rows.extend(
                replace(
                    row,
                    gross_forward_return=value + row.modeled_cost,
                    forward_cost_adjusted_return=value,
                )
                for row, value in zip(daily_rows, daily_values, strict=True)
            )
        null_values.append(
            cost_adjusted_primary_metric(permuted_rows, bucket_count=bucket_count).spread
        )
    result = empirical_null_test(
        observed=observed,
        null_values=null_values,
        alternative="greater",
        method="circular_block",
        seed=seed,
    )
    return result.raw_p_value, result.effect_size, result.confidence_interval


def _stress_metrics(
    rows: Sequence[PanelObservation], *, bucket_count: int
) -> tuple[dict[float, float], dict[float, float]]:
    all_costs: dict[float, float] = {}
    bid_ask: dict[float, float] = {}
    for multiplier in (0.5, 1.0, 1.5):
        cost_rows = tuple(
            replace(
                row,
                modeled_cost=row.modeled_cost * multiplier,
                bid_ask_cost=row.bid_ask_cost * multiplier,
                forward_cost_adjusted_return=(
                    row.gross_forward_return - row.modeled_cost * multiplier
                ),
            )
            for row in rows
        )
        all_costs[multiplier] = cost_adjusted_primary_metric(
            cost_rows, bucket_count=bucket_count
        ).spread
        spread_rows: list[PanelObservation] = []
        for row in rows:
            stressed_cost = max(
                0.0,
                row.modeled_cost + row.bid_ask_cost * (multiplier - 1.0),
            )
            spread_rows.append(
                replace(
                    row,
                    modeled_cost=stressed_cost,
                    bid_ask_cost=row.bid_ask_cost * multiplier,
                    forward_cost_adjusted_return=(row.gross_forward_return - stressed_cost),
                )
            )
        bid_ask[multiplier] = cost_adjusted_primary_metric(
            spread_rows, bucket_count=bucket_count
        ).spread
    return all_costs, bid_ask


def _regime_contributions(
    rows: Sequence[PanelObservation], *, bucket_count: int
) -> dict[str, float]:
    output: dict[str, float] = {}
    for regime in sorted({row.regime for row in rows}):
        regime_rows = [row for row in rows if row.regime == regime]
        metric = cost_adjusted_primary_metric(regime_rows, bucket_count=bucket_count)
        if metric.daily_spreads:
            output[regime] = metric.spread
    return output


def run_experiment(
    spec: ExperimentSpec,
    rows: Sequence[PanelObservation],
    registration_records: Sequence[Mapping[str, object]],
    registry: ExperimentRegistry,
    *,
    output_directory: str | Path,
    workers: int = 1,
    lumibot_adapter: LumibotFinalistAdapter | None = None,
    matrix_root: str | Path = DEFAULT_MATRIX_ROOT,
) -> tuple[Path, Path, Path]:
    spec.require_registration(registration_records)
    if workers < 1 or workers > 8:
        raise ValueError("workers must be between one and eight")
    if {row.lane for row in rows} != {spec.lane}:
        raise SpecValidationError("runner panel lane does not match the specification")
    controls = dict(spec.owner_controls)
    bucket_value = controls["bucket_count"]
    adverse_value = controls["minimum_adverse_bottom_bucket"]
    if not isinstance(bucket_value, int) or isinstance(bucket_value, bool):
        raise ValueError("owner bucket_count is not an integer")
    if not isinstance(adverse_value, int) or isinstance(adverse_value, bool):
        raise ValueError("owner minimum adverse count is not an integer")
    bucket_count = bucket_value
    minimum_adverse = adverse_value
    parameter_ids_list: list[str] = []
    for item in spec.parameter_grid:
        parameter_id = dict(item)["parameter_id"]
        if not isinstance(parameter_id, str):
            raise ValueError("parameter_id is not text")
        parameter_ids_list.append(parameter_id)
    parameter_ids = tuple(parameter_ids_list)
    if {row.parameter_id for row in rows} != set(parameter_ids):
        raise SpecValidationError("runner panel parameter ids do not match the specification")
    neighbor_map: dict[str, tuple[str, ...]] = {}
    for index, parameter_id in enumerate(parameter_ids):
        neighbors = parameter_ids[max(0, index - 1) : index]
        neighbors += parameter_ids[index + 1 : index + 2]
        neighbor_map[parameter_id] = neighbors
    panel_dates = sorted({row.panel_date for row in rows})
    splitter = WalkForwardSplitter(
        train_observations=spec.train_observations,
        test_observations=spec.test_observations,
        step_observations=spec.step_observations,
        purge_observations=spec.purge_observations,
        embargo_observations=spec.embargo_observations,
        mode=spec.walk_forward_mode,
    )
    folds = splitter.split(panel_dates)
    if not folds:
        raise ValueError("panel does not contain enough dates for one walk-forward fold")
    registry.register_run(spec)
    completed = registry.completed_tasks(spec.run_id)

    computed: dict[tuple[int, str], _ComputedTask] = {}
    fold_results: list[ParameterFoldResult] = []
    oos_rows: dict[str, list[PanelObservation]] = {
        parameter_id: [] for parameter_id in parameter_ids
    }
    block_size = max(2, spec.forward_outcome_horizon)
    for fold in folds:
        train_dates = set(fold.train_dates)
        test_dates = set(fold.test_dates)
        for parameter_id in parameter_ids:
            train_rows = [
                row
                for row in rows
                if row.parameter_id == parameter_id and row.panel_date in train_dates
            ]
            test_rows = [
                row
                for row in rows
                if row.parameter_id == parameter_id and row.panel_date in test_dates
            ]
            if not train_rows or not test_rows:
                raise ValueError(
                    f"missing panel rows for fold {fold.fold}, parameter {parameter_id}"
                )
            train_metric = cost_adjusted_primary_metric(train_rows, bucket_count=bucket_count)
            test_metric = cost_adjusted_primary_metric(test_rows, bucket_count=bucket_count)
            oos_rows[parameter_id].extend(test_rows)
            ticker = dict(test_metric.ticker_spread_contributions)
            regime = _regime_contributions(test_rows, bucket_count=bucket_count)
            cost_stress, bid_ask_stress = _stress_metrics(test_rows, bucket_count=bucket_count)
            fold_results.append(
                ParameterFoldResult(
                    parameter_id=parameter_id,
                    fold=fold.fold,
                    train_metric=train_metric.spread,
                    test_metric=test_metric.spread,
                    observation_count=test_metric.observation_count,
                    ticker_contributions=ticker,
                    regime_contributions=regime,
                    cost_stress_metrics=cost_stress,
                    neighbor_ids=neighbor_map[parameter_id],
                )
            )
            computed[(fold.fold, parameter_id)] = _ComputedTask(
                metric=test_metric,
                train_spread=train_metric.spread,
                audit_ranges=fold.audit_ranges(),
                cost_stress=cost_stress,
                bid_ask_stress=bid_ask_stress,
            )

    # Fail-open return-matrix capture (owner-directed 2026-07-24; see
    # options_researcher/robustness/return_matrix.py). Every call site below
    # is wrapped in its own try/except that logs and continues -- a capture
    # failure must NEVER change parameter_nulls/adjusted/stability, never
    # prevent record_completed_task/finish_run, and never prevent
    # write_reports. This is an observability side-channel, not part of the
    # registered computation.
    matrix_writer: ReturnMatrixWriter | None = None
    date_to_fold: dict[str, int] = {}
    try:
        matrix_writer = ReturnMatrixWriter(spec, matrix_root=matrix_root)
        for fold in folds:
            for panel_date in fold.test_dates:
                date_to_fold[panel_date] = fold.fold
    except Exception:
        logger.warning(
            "return-matrix writer setup failed for run %s; continuing without capture",
            spec.run_id,
            exc_info=True,
        )
        matrix_writer = None

    parameter_nulls: dict[str, tuple[float, float, tuple[float, float]]] = {}
    for index, parameter_id in enumerate(parameter_ids):
        aggregate_rows = oos_rows[parameter_id]
        aggregate_metric = cost_adjusted_primary_metric(aggregate_rows, bucket_count=bucket_count)
        parameter_nulls[parameter_id] = _permutation_result(
            aggregate_rows,
            observed=aggregate_metric.spread,
            bucket_count=bucket_count,
            block_size=block_size,
            permutations=spec.permutation_count,
            seed=spec.random_seed + index * 100_000,
        )
        if matrix_writer is not None:
            try:
                matrix_writer.capture(
                    parameter_id,
                    aggregate_rows,
                    bucket_count=bucket_count,
                    date_to_fold=date_to_fold,
                )
            except Exception:
                logger.warning(
                    "return-matrix capture failed for parameter %s in run %s",
                    parameter_id,
                    spec.run_id,
                    exc_info=True,
                )
    adjusted = holm_step_down(
        {parameter_id: parameter_nulls[parameter_id][0] for parameter_id in parameter_ids},
        alpha=spec.multiple_testing_alpha,
    )
    stability = {
        parameter_id: analyze_stability(
            parameter_id,
            fold_results,
            minimum_observations=minimum_adverse * bucket_count,
        )
        for parameter_id in parameter_ids
    }
    for (fold, parameter_id), payload in sorted(computed.items()):
        if (fold, parameter_id) in completed:
            continue
        metric = payload.metric
        holm = adjusted[parameter_id]
        _, effect_size, null_interval = parameter_nulls[parameter_id]
        diagnostic = stability[parameter_id]
        adverse_gate = "PASS" if metric.bottom_count >= minimum_adverse else "BLOCKED"
        runner_gates = {
            "registration": "PASS",
            "adverse_bottom_bucket": adverse_gate,
            "holm": "PASS" if holm.rejected else "FAIL",
            "production_promotion": "BLOCKED",
        }
        registry.record_completed_task(
            spec.run_id,
            fold,
            parameter_id,
            {
                "metrics": {
                    "spread": metric.spread,
                    "top_count": metric.top_count,
                    "bottom_count": metric.bottom_count,
                    "observation_count": metric.observation_count,
                    "train_spread": payload.train_spread,
                    "out_of_sample_decay": diagnostic.out_of_sample_decay,
                    "sign_consistency": diagnostic.sign_consistency,
                    "rank_stability": diagnostic.rank_stability,
                    "ticker_concentration": diagnostic.ticker_concentration,
                    "regime_concentration": diagnostic.regime_concentration,
                    "window_concentration": diagnostic.window_concentration,
                    "brittle_isolated_peak": diagnostic.brittle_isolated_peak,
                    "cost_stress": payload.cost_stress,
                    "bid_ask_stress": payload.bid_ask_stress,
                    "null_effect_size": effect_size,
                    "null_confidence_interval": null_interval,
                    "walk_forward_ranges": payload.audit_ranges,
                },
                "raw_p_value": holm.raw_p_value,
                "adjusted_p_value": holm.adjusted_p_value,
                "gate_outcomes": _merge_stability_gate_outcomes(
                    runner_gates, diagnostic.gate_outcomes
                ),
                "artifact_paths": [],
            },
        )

    if matrix_writer is not None:
        try:
            matrix_writer.finalize()
        except Exception:
            logger.warning("return-matrix finalize failed for run %s", spec.run_id, exc_info=True)
    registry.finish_run(spec.run_id)

    if lumibot_adapter is not None:
        aggregate = {
            parameter_id: sum(
                item.test_metric for item in fold_results if item.parameter_id == parameter_id
            )
            for parameter_id in parameter_ids
        }
        finalist = max(aggregate, key=lambda item: (aggregate[item], item))
        handoff_finalists(lumibot_adapter, (finalist,))
    return write_reports(registry, spec.run_id, output_directory, matrix_root=matrix_root)

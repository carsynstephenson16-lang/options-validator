"""Deterministic JSON, CSV, and concise Markdown experiment reports."""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import config
from metrics import dsr, sample_moments
from options_researcher.robustness.registry import ExperimentRegistry
from options_researcher.robustness.return_matrix import (
    DEFAULT_MATRIX_ROOT,
    MANIFEST_NAME,
    measured_trial_sr_stats,
)

logger = logging.getLogger(__name__)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        temporary = Path(temporary_name)
        if temporary.exists():
            temporary.unlink()


def _report_payload(registry: ExperimentRegistry, run_id: str) -> dict[str, object]:
    run = registry.run_record(run_id)
    tasks = registry.task_records(run_id)
    spec = run["spec"]
    assert isinstance(spec, dict)
    folds: set[int] = set()
    for task in tasks:
        fold = task["fold"]
        if not isinstance(fold, int):
            raise ValueError("stored task fold is not an integer")
        folds.add(fold)
    return {
        "research_only": True,
        "production_ranking_changed": False,
        "run": run,
        "lane": spec["lane"],
        "outcome_definition": "forward_cost_adjusted_return",
        "walk_forward_folds": sorted(folds),
        "tasks": tasks,
        "claim_label": spec["claim_label"],
        "production_recommendation": None,
    }


def _csv_text(tasks: list[dict[str, object]]) -> str:
    output = io.StringIO()
    fields = [
        "run_id",
        "fold",
        "parameter_id",
        "status",
        "spread",
        "top_count",
        "bottom_count",
        "out_of_sample_decay",
        "sign_consistency",
        "rank_stability",
        "ticker_concentration",
        "regime_concentration",
        "window_concentration",
        "cost_stress",
        "bid_ask_stress",
        "raw_p_value",
        "adjusted_p_value",
        "gate_outcomes",
    ]
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for task in tasks:
        metrics = task["metrics"]
        gates = task["gate_outcomes"]
        assert isinstance(metrics, dict)
        writer.writerow(
            {
                "run_id": task["run_id"],
                "fold": task["fold"],
                "parameter_id": task["parameter_id"],
                "status": task["status"],
                "spread": metrics.get("spread"),
                "top_count": metrics.get("top_count"),
                "bottom_count": metrics.get("bottom_count"),
                "out_of_sample_decay": metrics.get("out_of_sample_decay"),
                "sign_consistency": metrics.get("sign_consistency"),
                "rank_stability": metrics.get("rank_stability"),
                "ticker_concentration": metrics.get("ticker_concentration"),
                "regime_concentration": metrics.get("regime_concentration"),
                "window_concentration": metrics.get("window_concentration"),
                "cost_stress": json.dumps(
                    metrics.get("cost_stress"), sort_keys=True, separators=(",", ":")
                ),
                "bid_ask_stress": json.dumps(
                    metrics.get("bid_ask_stress"), sort_keys=True, separators=(",", ":")
                ),
                "raw_p_value": task["raw_p_value"],
                "adjusted_p_value": task["adjusted_p_value"],
                "gate_outcomes": json.dumps(gates, sort_keys=True, separators=(",", ":")),
            }
        )
    return output.getvalue()


def _governance_dsr_bullet(run_id: str, matrix_root: str | Path) -> str:
    """Best-effort, NEVER-blocking read of the return-matrix manifest for one
    additive Governance bullet (owner-directed 2026-07-24). Any failure --
    missing matrix, malformed manifest, thin sample -- degrades to an honest
    string; it never raises into write_reports and never touches the JSON or
    CSV artifacts. See options_researcher/robustness/return_matrix.py and
    docs/superpowers/specs/2026-07-24-robustness-return-matrix-addendum.md.
    """
    unavailable = (
        "- DSR (measured-from-return-matrix): matrix unavailable; N=0 variants; "
        "population = parameter-variant selection within this one experiment, "
        "NOT the whole-program trial count; diagnostic only, never gates promotion."
    )
    try:
        manifest_path = Path(matrix_root) / run_id / MANIFEST_NAME
        if not manifest_path.exists():
            return unavailable
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parquet_path = manifest["output"]["path"]
        mean_trial_sr, trial_sr_variance, n_trials = measured_trial_sr_stats(parquet_path)
        frame = pd.read_parquet(parquet_path)
        best_sr = float("-inf")
        best_series: np.ndarray | None = None
        for _parameter_id, group in frame.groupby("parameter_id"):
            series = group.sort_values("panel_date")["cost_adjusted_return"].to_numpy(dtype=float)
            if len(series) < 2:
                continue
            std = float(series.std(ddof=1))
            if not np.isfinite(std) or std == 0.0:
                continue
            variant_sr = float(series.mean()) / std
            if variant_sr > best_sr:
                best_sr, best_series = variant_sr, series
        if best_series is None or len(best_series) < config.DSR_MIN_T:
            value_text = "INSUFFICIENT SAMPLE FOR DSR"
        else:
            skew, kurt = sample_moments(best_series)
            value = dsr(
                best_sr,
                len(best_series),
                skew,
                kurt,
                trial_sr_variance=trial_sr_variance,
                n_trials=n_trials,
                mean_trial_sr=mean_trial_sr,
            )
            value_text = f"{value:.4f}" if np.isfinite(value) else "nan"
        return (
            f"- DSR (measured-from-return-matrix): {value_text}; N={n_trials} variants; "
            "population = parameter-variant selection within this one experiment, "
            "NOT the whole-program trial count; diagnostic only, never gates promotion."
        )
    except Exception:
        logger.warning("DSR governance bullet computation failed for run %s", run_id, exc_info=True)
        return unavailable


def _markdown_text(payload: dict[str, object], governance_dsr_bullet: str) -> str:
    run = payload["run"]
    tasks = payload["tasks"]
    assert isinstance(run, dict)
    assert isinstance(tasks, list)
    spec = run["spec"]
    assert isinstance(spec, dict)
    lines = [
        f"# Robustness experiment — {run['run_id']}",
        "",
        "**RESEARCH-ONLY. No production recommendation.**",
        "",
        "## Identity",
        "",
        f"- Status: {run['status']}",
        f"- Research question: {spec['research_question_id']}",
        f"- Lane: {spec['lane']}",
        f"- Signal/validator: {spec['signal_version']}",
        f"- Dataset fingerprint: `{spec['dataset_fingerprint']}`",
        f"- Git SHA: `{spec['git_commit_sha']}`",
        f"- Config hash: `{spec['config_hash']}`",
        f"- Seed / null method: {spec['random_seed']} / {spec['permutation_method']}",
        f"- Claim label: {spec['claim_label']}",
        "",
        "## Fold results",
        "",
        "| Fold | Parameter | Cost-adjusted spread | N top / bottom | Raw p | Holm p | Gates |",
        "|---:|---|---:|---:|---:|---:|---|",
    ]
    for task in tasks:
        metrics = task["metrics"]
        gates = task["gate_outcomes"]
        assert isinstance(metrics, dict)
        assert isinstance(gates, dict)
        gate_text = ", ".join(f"{key}={value}" for key, value in sorted(gates.items()))
        lines.append(
            "| {fold} | {parameter} | {spread} | {top}/{bottom} | {raw} | "
            "{adjusted} | {gates} |".format(
                fold=task["fold"],
                parameter=task["parameter_id"],
                spread=metrics.get("spread", ""),
                top=metrics.get("top_count", ""),
                bottom=metrics.get("bottom_count", ""),
                raw=task["raw_p_value"],
                adjusted=task["adjusted_p_value"],
                gates=gate_text,
            )
        )
    lines.extend(["", "## Stability, null, and cost diagnostics", ""])
    for task in tasks:
        metrics = task["metrics"]
        assert isinstance(metrics, dict)
        lines.extend(
            [
                f"### Fold {task['fold']} — {task['parameter_id']}",
                "",
                f"- Train spread: {metrics.get('train_spread')}; "
                f"OOS decay: {metrics.get('out_of_sample_decay')}.",
                f"- Sign consistency: {metrics.get('sign_consistency')}; "
                f"fold-rank stability: {metrics.get('rank_stability')}.",
                f"- Ticker concentration: {metrics.get('ticker_concentration')}; "
                f"regime concentration: {metrics.get('regime_concentration')}; "
                f"window concentration: {metrics.get('window_concentration')}.",
                f"- Isolated-peak brittleness: {metrics.get('brittle_isolated_peak')}.",
                "- Total modeled-cost stress (0.5x / 1.0x / 1.5x; arithmetic sensitivity; "
                "same-sample point estimates; no stress-arm CI; all modeled cost, including any "
                "commission embedded upstream, is scaled arithmetically): "
                f"{metrics.get('cost_stress')}.",
                "- Bid/ask stress (0.5x / 1.0x / 1.5x; arithmetic sensitivity; same-sample "
                f"point estimates; no stress-arm CI): {metrics.get('bid_ask_stress')}.",
                f"- Null effect / interval: {metrics.get('null_effect_size')} / "
                f"{metrics.get('null_confidence_interval')}.",
                f"- Walk-forward coverage: {metrics.get('walk_forward_ranges')}.",
                "",
            ]
        )
    lines.extend(
        [
            "",
            "## Governance",
            "",
            "- Production ranking changed: no.",
            "- Fast-screen outputs are exploratory and display-only.",
            "- Lumibot remains the event-driven finalist validation path.",
            "- No production recommendation while governance blocks remain.",
            governance_dsr_bullet,
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    registry: ExperimentRegistry,
    run_id: str,
    output_directory: str | Path,
    *,
    matrix_root: str | Path = DEFAULT_MATRIX_ROOT,
) -> tuple[Path, Path, Path]:
    output = Path(output_directory)
    payload = _report_payload(registry, run_id)
    tasks = payload["tasks"]
    assert isinstance(tasks, list)
    json_path = output / f"{run_id}.json"
    csv_path = output / f"{run_id}.csv"
    markdown_path = output / f"{run_id}.md"
    _atomic_write(
        json_path,
        json.dumps(
            payload,
            sort_keys=True,
            indent=2,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
    )
    _atomic_write(csv_path, _csv_text(tasks))
    governance_dsr_bullet = _governance_dsr_bullet(run_id, matrix_root)
    _atomic_write(markdown_path, _markdown_text(payload, governance_dsr_bullet))
    return json_path, csv_path, markdown_path

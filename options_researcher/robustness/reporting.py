"""Deterministic JSON, CSV, and concise Markdown experiment reports."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from options_researcher.robustness.registry import ExperimentRegistry


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


def _markdown_text(payload: dict[str, object]) -> str:
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
                f"- Total-cost stress (0.5x/1.0x/1.5x): {metrics.get('cost_stress')}.",
                f"- Bid/ask stress (0.5x/1.0x/1.5x): {metrics.get('bid_ask_stress')}.",
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
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(
    registry: ExperimentRegistry, run_id: str, output_directory: str | Path
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
    _atomic_write(markdown_path, _markdown_text(payload))
    return json_path, csv_path, markdown_path

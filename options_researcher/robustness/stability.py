"""Separate, non-composite diagnostics for parameter and concentration stability."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class ParameterFoldResult:
    parameter_id: str
    fold: int
    train_metric: float
    test_metric: float
    observation_count: int
    ticker_contributions: Mapping[str, float] = field(default_factory=dict)
    regime_contributions: Mapping[str, float] = field(default_factory=dict)
    cost_stress_metrics: Mapping[float, float] = field(default_factory=dict)
    neighbor_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StabilityDiagnostic:
    parameter_id: str
    neighboring_parameter_performance: float | None
    rank_stability: float
    sign_consistency: float
    out_of_sample_decay: float | None
    ticker_concentration: float
    regime_concentration: float
    window_concentration: float
    minimum_observation_count: int
    cost_sensitive: bool
    brittle_isolated_peak: bool
    gate_outcomes: tuple[tuple[str, str], ...]


def _concentration(contributions: Mapping[str, float]) -> float:
    denominator = sum(abs(value) for value in contributions.values())
    return max((abs(value) for value in contributions.values()), default=0.0) / (denominator or 1.0)


def analyze_stability(
    parameter_id: str,
    results: Sequence[ParameterFoldResult],
    *,
    minimum_observations: int,
) -> StabilityDiagnostic:
    target = [item for item in results if item.parameter_id == parameter_id]
    if not target:
        raise ValueError(f"no results for parameter {parameter_id!r}")
    if minimum_observations < 1:
        raise ValueError("minimum_observations must be positive")
    neighbor_ids = {neighbor for item in target for neighbor in item.neighbor_ids}
    neighbors = [item.test_metric for item in results if item.parameter_id in neighbor_ids]
    neighbor_mean = sum(neighbors) / len(neighbors) if neighbors else None
    target_tests = [item.test_metric for item in target]
    target_trains = [item.train_metric for item in target]
    sign_consistency = sum(value > 0 for value in target_tests) / len(target_tests)

    fold_winners: list[bool] = []
    for target_item in target:
        same_fold = [item for item in results if item.fold == target_item.fold]
        fold_winners.append(target_item.test_metric == max(item.test_metric for item in same_fold))
    rank_stability = sum(fold_winners) / len(fold_winners)
    train_mean = sum(target_trains) / len(target_trains)
    test_mean = sum(target_tests) / len(target_tests)
    decay = None if train_mean == 0 else (train_mean - test_mean) / abs(train_mean)

    ticker_totals: dict[str, float] = {}
    regime_totals: dict[str, float] = {}
    for item in target:
        for ticker, value in item.ticker_contributions.items():
            ticker_totals[ticker] = ticker_totals.get(ticker, 0.0) + value
        for regime, value in item.regime_contributions.items():
            regime_totals[regime] = regime_totals.get(regime, 0.0) + value
    ticker_concentration = _concentration(ticker_totals)
    regime_concentration = _concentration(regime_totals)
    window_concentration = _concentration({str(item.fold): item.test_metric for item in target})
    minimum_count = min(item.observation_count for item in target)

    cost_sensitive = False
    for item in target:
        base = item.cost_stress_metrics.get(1.0)
        stressed = [
            value for multiplier, value in item.cost_stress_metrics.items() if multiplier > 1.0
        ]
        if (
            base is not None
            and stressed
            and (any(value <= 0 < base for value in stressed) or min(stressed) < base * 0.5)
        ):
            cost_sensitive = True
    neighbor_peak = max(neighbors, default=float("-inf"))
    brittle = (
        bool(neighbors)
        and test_mean > 0
        and (neighbor_peak <= 0 or test_mean > neighbor_peak * 1.5)
    )
    gates = {
        "minimum_observations": ("PASS" if minimum_count >= minimum_observations else "BLOCKED"),
        "sign_consistency": "PASS" if math.isclose(sign_consistency, 1.0) else "FAIL",
        "ticker_concentration": "PASS" if ticker_concentration <= 0.5 else "FAIL",
        "regime_concentration": "PASS" if regime_concentration <= 0.75 else "FAIL",
        "window_concentration": "PASS" if window_concentration <= 0.75 else "FAIL",
        "cost_stress": "FAIL" if cost_sensitive else "PASS",
        "brittleness": "FAIL" if brittle else "PASS",
    }
    return StabilityDiagnostic(
        parameter_id=parameter_id,
        neighboring_parameter_performance=neighbor_mean,
        rank_stability=rank_stability,
        sign_consistency=sign_consistency,
        out_of_sample_decay=decay,
        ticker_concentration=ticker_concentration,
        regime_concentration=regime_concentration,
        window_concentration=window_concentration,
        minimum_observation_count=minimum_count,
        cost_sensitive=cost_sensitive,
        brittle_isolated_peak=brittle,
        gate_outcomes=tuple(sorted(gates.items())),
    )

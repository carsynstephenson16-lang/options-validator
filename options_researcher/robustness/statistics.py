"""Time-series-aware null methods and family-wise error correction."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Protocol, Sequence, TypeVar

T = TypeVar("T")


class NullMethod(Protocol):
    def permute(self, values: Sequence[T], *, seed: int) -> tuple[T, ...]: ...


@dataclass(frozen=True, slots=True)
class CircularBlockPermutation:
    block_size: int

    def __post_init__(self) -> None:
        if self.block_size < 2:
            raise ValueError("block_size must be at least two")

    def permute(self, values: Sequence[T], *, seed: int) -> tuple[T, ...]:
        if len(values) < self.block_size * 2:
            raise ValueError("at least two complete blocks are required")
        blocks = [
            tuple(values[index : index + self.block_size])
            for index in range(0, len(values), self.block_size)
        ]
        rng = random.Random(seed)
        rng.shuffle(blocks)
        return tuple(item for block in blocks for item in block)


@dataclass(frozen=True, slots=True)
class NullTestResult:
    observed: float
    raw_p_value: float
    effect_size: float
    confidence_interval: tuple[float, float]
    permutation_count: int
    method: str
    seed: int | None


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("quantile requires values")
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def empirical_null_test(
    *,
    observed: float,
    null_values: Sequence[float],
    alternative: str = "greater",
    method: str = "provided",
    seed: int | None = None,
) -> NullTestResult:
    if not math.isfinite(observed) or not null_values:
        raise ValueError("observed and null values are required")
    if any(not math.isfinite(value) for value in null_values):
        raise ValueError("null values must be finite")
    if alternative not in {"greater", "less", "two-sided"}:
        raise ValueError("unsupported alternative")
    if alternative == "greater":
        extreme = sum(value >= observed for value in null_values)
    elif alternative == "less":
        extreme = sum(value <= observed for value in null_values)
    else:
        center = sum(null_values) / len(null_values)
        distance = abs(observed - center)
        extreme = sum(abs(value - center) >= distance for value in null_values)
    p_value = (1 + extreme) / (len(null_values) + 1)
    null_mean = sum(null_values) / len(null_values)
    return NullTestResult(
        observed=observed,
        raw_p_value=p_value,
        effect_size=observed - null_mean,
        confidence_interval=(_quantile(null_values, 0.05), _quantile(null_values, 0.95)),
        permutation_count=len(null_values),
        method=method,
        seed=seed,
    )


@dataclass(frozen=True, slots=True)
class HolmResult:
    raw_p_value: float
    adjusted_p_value: float
    rejected: bool
    rank: int


def holm_step_down(p_values: dict[str, float], *, alpha: float) -> dict[str, HolmResult]:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between zero and one")
    if any(not 0.0 <= value <= 1.0 for value in p_values.values()):
        raise ValueError("p-values must be between zero and one")
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted_running = 0.0
    reject_open = True
    output: dict[str, HolmResult] = {}
    for index, (name, raw) in enumerate(ordered):
        multiplier = count - index
        adjusted_running = max(adjusted_running, min(1.0, multiplier * raw))
        threshold = alpha / multiplier
        rejected = reject_open and raw <= threshold
        if not rejected:
            reject_open = False
        output[name] = HolmResult(
            raw_p_value=raw,
            adjusted_p_value=adjusted_running,
            rejected=rejected,
            rank=index + 1,
        )
    return output

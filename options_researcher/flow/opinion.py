"""Calibrated, noncausal opinion synthesis from historical analog outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import cast

import numpy as np

from .analogs import AnalogResult


@dataclass(frozen=True, slots=True)
class HistoricalOpinion:
    status: str
    directional_opinion: str
    volatility_opinion: str
    reasons: tuple[str, ...]
    sample_size: int
    median_excess_return_5: float | None
    return_interval_90: tuple[float, float] | None
    positive_frequency: float | None
    matched_base_positive_frequency: float | None
    median_iv_change_5: float | None
    iv_interval_90: tuple[float, float] | None
    counterexamples: tuple[dict[str, object], ...]
    disclaimer: str = (
        "Historical similarity is observational and noncausal; this is not a trade "
        "recommendation or evidence of customer intent or dealer positioning."
    )

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _moving_block_median_interval(
    values: np.ndarray,
    *,
    seed: int,
    samples: int = 2_000,
    block_length: int = 2,
) -> tuple[float, float]:
    """Deterministic dependence-aware bootstrap of the median."""
    clean = values[np.isfinite(values)]
    if len(clean) < 2:
        return (np.nan, np.nan)
    length = len(clean)
    starts = np.random.default_rng(seed).integers(0, length, size=(samples, length))
    offsets = np.arange(block_length)
    blocks = clean[(starts[..., None] + offsets) % length]
    resampled = blocks.reshape(samples, -1)[:, :length]
    medians = np.median(resampled, axis=1)
    low, high = np.quantile(medians, (0.05, 0.95))
    return float(low), float(high)


def synthesize_historical_opinion(
    primary: AnalogResult,
    *,
    pooled: AnalogResult | None,
    matched_base_positive_frequency: float | None,
    seed: int = 19,
) -> HistoricalOpinion:
    """Apply preregistered lean gates and preserve contradictory examples."""
    matched_base_positive_frequency = _validated_base_positive_frequency(
        matched_base_positive_frequency
    )
    reasons = list(primary.reasons)
    if primary.status != "READY":
        reasons.append("PRIMARY_ANALOG_RESULT_NOT_READY")
    if pooled is None or pooled.status != "READY":
        reasons.append("POOLED_SENSITIVITY_NOT_READY")
    if matched_base_positive_frequency is None:
        reasons.append("MATCHED_BASE_POSITIVE_FREQUENCY_UNAVAILABLE")
    # Analogs are selected in distance order. Restore session order before the
    # moving-block bootstrap so each block represents adjacent trading sessions.
    rows = sorted(primary.analogs, key=lambda row: str(row["session"]))
    return_key = "excess_return_5" if rows and "excess_return_5" in rows[0] else "return_5"
    returns = np.asarray(
        [_as_float(row.get(return_key, np.nan)) for row in rows],
        dtype=float,
    )
    returns = returns[np.isfinite(returns)]
    iv_changes = np.asarray(
        [_as_float(row.get("iv_change_5", np.nan)) for row in rows],
        dtype=float,
    )
    iv_changes = iv_changes[np.isfinite(iv_changes)]
    if len(returns) < 10:
        reasons.append("FEWER_THAN_10_VALID_T5_OUTCOMES")

    return_interval = (
        _moving_block_median_interval(returns, seed=seed) if len(returns) >= 2 else None
    )
    median_return = float(np.median(returns)) if len(returns) else None
    positive_frequency = float((returns > 0).mean()) if len(returns) else None
    pooled_rows = list(pooled.analogs) if pooled is not None else []
    pooled_returns = np.asarray(
        [_as_float(row.get(return_key, np.nan)) for row in pooled_rows],
        dtype=float,
    )
    pooled_returns = pooled_returns[np.isfinite(pooled_returns)]
    same_sign = (
        median_return is not None
        and len(pooled_returns) > 0
        and np.sign(median_return) == np.sign(float(np.median(pooled_returns)))
        and np.sign(median_return) != 0
    )
    frequency_delta_ok = (
        positive_frequency is not None
        and matched_base_positive_frequency is not None
        and abs(positive_frequency - matched_base_positive_frequency) >= 0.10
    )
    interval_excludes_zero = return_interval is not None and (
        return_interval[0] > 0 or return_interval[1] < 0
    )
    directional = "MIXED_OR_INDETERMINATE"
    if not reasons and same_sign and frequency_delta_ok and interval_excludes_zero:
        directional = (
            "POSITIVE_HISTORICAL_LEAN"
            if median_return is not None and median_return > 0
            else "NEGATIVE_HISTORICAL_LEAN"
        )

    iv_interval = (
        _moving_block_median_interval(iv_changes, seed=seed + 1) if len(iv_changes) >= 2 else None
    )
    median_iv_change = float(np.median(iv_changes)) if len(iv_changes) else None
    volatility = "MIXED_OR_INDETERMINATE"
    if not reasons and iv_interval is not None and (iv_interval[0] > 0 or iv_interval[1] < 0):
        volatility = (
            "VOLATILITY_EXPANSION_LEAN"
            if median_iv_change is not None and median_iv_change > 0
            else "VOLATILITY_COMPRESSION_LEAN"
        )

    counterexamples = tuple(
        sorted(
            (
                row
                for row in rows
                if np.isfinite(_as_float(row.get(return_key, np.nan)))
                and median_return is not None
                and np.sign(_as_float(row[return_key])) != np.sign(median_return)
            ),
            key=lambda row: _as_float(row[return_key]),
        )[:3]
    )
    status = "READY" if not reasons else "ABSTAIN_INSUFFICIENT_OR_UNRELIABLE_DATA"
    return HistoricalOpinion(
        status,
        directional,
        volatility,
        tuple(dict.fromkeys(reasons)),
        len(returns),
        median_return,
        return_interval,
        positive_frequency,
        matched_base_positive_frequency,
        median_iv_change,
        iv_interval,
        counterexamples,
    )


def _as_float(value: object) -> float:
    return float(cast(float | int | str, value))


def _validated_base_positive_frequency(value: float | None) -> float | None:
    """Return a finite matched-regime base rate or reject invalid external input."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("matched_base_positive_frequency must be within [0, 1]") from exc
    if not np.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
        raise ValueError("matched_base_positive_frequency must be within [0, 1]")
    return numeric

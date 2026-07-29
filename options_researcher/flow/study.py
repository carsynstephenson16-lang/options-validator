"""Offline leakage-safe labels and a small nested baseline comparison."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import cast

import numpy as np
import pandas as pd

from options_researcher.robustness.walk_forward import WalkForwardSplitter


def make_forward_labels(closes: pd.DataFrame) -> pd.DataFrame:
    """Create forward returns and RV21 from date-aligned close observations."""
    required = {"symbol", "session", "close"}
    missing = sorted(required - set(closes.columns))
    if missing:
        raise ValueError(f"close panel missing columns: {missing}")
    out = closes.copy()
    out["session"] = pd.to_datetime(out["session"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["close"] = pd.to_numeric(out["close"], errors="coerce")
    if bool(pd.isna(out[["session", "close"]]).to_numpy().any()) or bool(
        (cast(pd.Series, out["close"]) <= 0).any()
    ):
        raise ValueError("close panel contains malformed or non-positive values")
    out = out.sort_values(["symbol", "session"]).reset_index(drop=True)
    for horizon in (1, 5, 21):
        out[f"return_{horizon}"] = (
            out.groupby("symbol")["close"].shift(-horizon).div(out["close"]) - 1.0
        )
    rv_values: list[float] = []
    for _, group in out.groupby("symbol", sort=False):
        values = pd.Series(np.log(group["close"].to_numpy(dtype=float))).diff().to_numpy()
        for index in range(len(group)):
            future = values[index + 1 : index + 22]
            rv_values.append(
                float(np.std(future, ddof=1) * np.sqrt(252)) if len(future) >= 2 else np.nan
            )
    # Group iteration is sorted identically to the sorted frame above.
    out["future_rv21"] = rv_values
    return out


def seeded_sign_placebo(values: pd.Series, *, seed: int) -> pd.Series:
    """Return a deterministic sign-permuted negative-control series."""
    rng = random.Random(seed)
    signs = [1.0 if rng.random() >= 0.5 else -1.0 for _ in values]
    return values.reset_index(drop=True) * signs


@dataclass(frozen=True, slots=True)
class FoldComparison:
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    baseline_rmse: float
    augmented_rmse: float
    rmse_improvement: float
    baseline_observations: int
    augmented_observations: int


def _design(frame: pd.DataFrame, columns: list[str], means=None, scales=None):
    values = frame.loc[:, columns].to_numpy(dtype=float)
    if means is None:
        means = np.nanmean(values, axis=0)
    if scales is None:
        scales = np.nanstd(values, axis=0)
    scales = np.where(scales > 0, scales, 1.0)
    values = (values - means) / scales
    return np.column_stack([np.ones(len(values)), values]), means, scales


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, columns: list[str], target: str):
    train = train.dropna(subset=columns + [target])
    test = test.dropna(subset=columns + [target])
    if train.empty or test.empty:
        return None
    x_train, means, scales = _design(train, columns)
    x_test, _, _ = _design(test, columns, means, scales)
    coefficients, _, _, _ = np.linalg.lstsq(x_train, train[target].to_numpy(float), rcond=None)
    actual = test[target].to_numpy(float)
    return actual, x_test @ coefficients


def compare_walk_forward(
    panel: pd.DataFrame,
    *,
    target: str,
    target_horizon_observations: int,
    flow_columns: list[str],
    baseline_column: str = "baseline_validator_output",
    context_columns: list[str] | None = None,
    train_observations: int = 30,
    test_observations: int = 10,
    step_observations: int = 11,
    purge_observations: int = 21,
    embargo_observations: int = 1,
    holdout_observations: int = 0,
) -> pd.DataFrame:
    """Compare baseline-only versus baseline-plus-flow on walk-forward folds.

    ``target_horizon_observations`` declares how many future observations are
    used by ``target``.  The purge must cover that entire look-ahead horizon.
    """
    contexts = context_columns or []
    required = {"session", baseline_column, target, *contexts, *flow_columns}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise ValueError(f"study panel missing columns: {missing}")
    if target_horizon_observations < 1:
        raise ValueError("target_horizon_observations must be positive")
    if purge_observations < target_horizon_observations:
        raise ValueError("purge_observations must be at least target_horizon_observations")
    if purge_observations >= train_observations:
        raise ValueError("purge must leave training observations")
    ordered = panel.sort_values("session").copy()
    dates = sorted(str(value) for value in ordered["session"].unique())
    if holdout_observations < 0 or holdout_observations >= len(dates):
        raise ValueError("holdout must leave at least one development session")
    development_dates = dates[:-holdout_observations] if holdout_observations else dates
    folds = WalkForwardSplitter(
        train_observations=train_observations,
        test_observations=test_observations,
        step_observations=step_observations,
        purge_observations=purge_observations,
        embargo_observations=embargo_observations,
    ).split(development_dates)
    results: list[dict[str, object]] = []
    baseline_columns = [baseline_column, *contexts]
    augmented_columns = [*baseline_columns, *flow_columns]
    for fold in folds:
        train = cast(pd.DataFrame, ordered[ordered["session"].isin(fold.train_dates)])
        test = cast(pd.DataFrame, ordered[ordered["session"].isin(fold.test_dates)])
        complete_columns = [*augmented_columns, target]
        train = train.dropna(subset=complete_columns)
        test = test.dropna(subset=complete_columns)
        baseline = _fit_predict(train, test, baseline_columns, target)
        augmented = _fit_predict(train, test, augmented_columns, target)
        if baseline is None or augmented is None:
            continue
        actual, baseline_prediction = baseline
        _, augmented_prediction = augmented
        baseline_rmse = float(np.sqrt(np.mean((actual - baseline_prediction) ** 2)))
        augmented_rmse = float(np.sqrt(np.mean((actual - augmented_prediction) ** 2)))
        results.append(
            {
                "fold": fold.fold,
                "train_start": fold.train_dates[0],
                "train_end": fold.train_dates[-1],
                "test_start": fold.test_dates[0],
                "test_end": fold.test_dates[-1],
                "baseline_rmse": baseline_rmse,
                "augmented_rmse": augmented_rmse,
                "rmse_improvement": baseline_rmse - augmented_rmse,
                "baseline_observations": len(actual),
                "augmented_observations": len(actual),
            }
        )
    if not results:
        return pd.DataFrame(columns=pd.Index(FoldComparison.__annotations__.keys()))
    return pd.DataFrame(results)

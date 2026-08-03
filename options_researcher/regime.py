"""options_researcher/regime.py -- offline Wasserstein regime clustering.

DISPLAY-ONLY descriptive lane. Adapted from
mehul532/wasserstein-market-regime-clustering (MIT License, Copyright (c)
2026 mehul532) -- see .cursorrules "Scope guard" owner-directed exception,
2026-08-03, for the authorization and the constraints it carries.

Only the Wasserstein-distance math, the barycenter/k-means clustering, and a
strictly-causal walk-forward labeling path are ported. The upstream project's
backtest/equity-curve/position/Sharpe code is deliberately NOT ported: this
module emits labels, centroids, dispersion, and transition frequencies only.
No position, no P&L, no verdict of any kind reads these values.

WALK-FORWARD CAUSALITY (stricter than upstream): at each labeling step, the
model is fit only on windows strictly BEFORE the window being labeled, and
that window is never a member of its own training set. Upstream's own
walk-forward path fits on windows[: i + 1] (which includes window i) before
predicting window i -- this module corrects that look-ahead rather than
reproducing it.

Regime labels are unsupervised historical descriptions of past return-window
shape. They carry no predictive claim and are not a registered signal.
Transition frequencies below are HISTORICAL FREQUENCIES, NOT FORECASTS.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def _as_1d_finite(values: np.ndarray, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if arr.size == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _as_2d_finite(values: np.ndarray, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be two-dimensional")
    if arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError(f"{name} must not be empty")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values")
    return arr


def _validate_p(p: int | float) -> float:
    p_float = float(p)
    if p_float < 1:
        raise ValueError("p must be at least 1")
    return p_float


def wasserstein_1d(a: np.ndarray, b: np.ndarray, p: int | float = 1) -> float:
    """1-D empirical p-Wasserstein distance between two EQUAL-LENGTH samples.

    RESTRICTION (validated, not just documented): the closed form used here

        W_p(a, b) = mean(|sort(a) - sort(b)| ** p) ** (1 / p)

    is only the true optimal-transport distance when `a` and `b` have the
    SAME number of observations, so that sorting both and pairing equal
    quantile ranks is the optimal coupling. Unequal-length samples require a
    general OT solver, which this module does not implement -- callers must
    supply equal-length samples (e.g. equal-length rolling return windows).
    """
    a_arr = _as_1d_finite(a, "a")
    b_arr = _as_1d_finite(b, "b")
    p_float = _validate_p(p)
    if a_arr.shape[0] != b_arr.shape[0]:
        raise ValueError(
            "wasserstein_1d requires equal-length samples (equal-length "
            f"special case only); got {a_arr.shape[0]} vs {b_arr.shape[0]}"
        )
    diff = np.abs(np.sort(a_arr) - np.sort(b_arr))
    return float(np.mean(diff**p_float) ** (1.0 / p_float))


def pairwise_wasserstein(windows: np.ndarray, p: int | float = 1) -> np.ndarray:
    """Symmetric pairwise p-Wasserstein distance matrix between window rows.

    Each row of `windows` is an equal-length empirical return-window sample;
    see `wasserstein_1d` for the equal-length restriction this relies on.
    """
    arr = _as_2d_finite(windows, "windows")
    p_float = _validate_p(p)
    sorted_windows = np.sort(arr, axis=1)
    n_windows = sorted_windows.shape[0]
    distances = np.zeros((n_windows, n_windows), dtype=float)
    for i in range(n_windows):
        diff = np.abs(sorted_windows[i + 1 :] - sorted_windows[i])
        if diff.size == 0:
            continue
        row = np.mean(diff**p_float, axis=1) ** (1.0 / p_float)
        distances[i, i + 1 :] = row
        distances[i + 1 :, i] = row
    return distances


def wasserstein_barycenter_1d(windows: np.ndarray) -> np.ndarray:
    """Mean of sorted samples across window rows (1-D Wasserstein barycenter).

    In one dimension the Wasserstein barycenter's quantile function equals
    the average of the member quantile functions; for equally weighted,
    equal-length empirical windows this reduces to sorting every window and
    averaging each quantile rank.
    """
    arr = _as_2d_finite(windows, "windows")
    return np.mean(np.sort(arr, axis=1), axis=0)


def make_return_windows(
    closes: pd.Series,
    window: int,
    step: int,
) -> tuple[np.ndarray, list]:
    """Build overlapping log-return windows from a date-indexed close series.

    Each returned row is one empirical return distribution; its paired
    end_date is the LAST session the window covers -- the earliest timestamp
    at which that distribution is observable (no look-ahead). Log returns are
    `log(c_t / c_{t-1})`; the resulting leading NaN is dropped before
    windowing.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    if step <= 0:
        raise ValueError("step must be positive")
    if not isinstance(closes, pd.Series):
        raise TypeError("closes must be a pandas Series")

    checked_index = pd.to_datetime(closes.index)
    if not checked_index.is_monotonic_increasing:
        raise ValueError("closes index must be monotonic increasing (sorted dates)")
    if checked_index.has_duplicates:
        raise ValueError("closes index must not contain duplicate dates")

    log_returns = np.log(closes / closes.shift(1)).dropna()
    if len(log_returns) < window:
        raise ValueError(
            f"only {len(log_returns)} log returns available; need at least {window}"
        )

    values = log_returns.to_numpy(dtype=float)
    dates = log_returns.index
    windows: list[np.ndarray] = []
    end_dates: list = []
    for start in range(0, len(values) - window + 1, step):
        end = start + window
        windows.append(values[start:end])
        end_dates.append(dates[end - 1])
    return np.asarray(windows, dtype=float), end_dates


@dataclass
class _FitResult:
    labels: np.ndarray
    centroids: np.ndarray
    inertia: float


class WassersteinKMeans:
    """K-means over 1-D return-window empirical distributions.

    Assignment uses p-Wasserstein distance between sorted windows; centroid
    updates use the 1-D Wasserstein barycenter (Lloyd's algorithm). DISPLAY-
    ONLY descriptive clustering -- not registered strategy machinery.
    Initialization is UNIFORM random sampling of data points as starting
    centroids (upstream's choice), not k-means++.
    """

    def __init__(
        self,
        n_clusters: int = 3,
        *,
        p: int | float = 1,
        max_iter: int = 100,
        tol: float = 1e-4,
        n_init: int = 5,
        random_state: int | None = None,
    ) -> None:
        if n_clusters <= 0:
            raise ValueError("n_clusters must be positive")
        if p < 1:
            raise ValueError("p must be at least 1")
        if max_iter <= 0:
            raise ValueError("max_iter must be positive")
        if tol < 0:
            raise ValueError("tol must be non-negative")
        if n_init <= 0:
            raise ValueError("n_init must be positive")

        self.n_clusters = int(n_clusters)
        self.p = float(p)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.n_init = int(n_init)
        self.random_state = random_state

        self.labels_: np.ndarray | None = None
        self.centroids_: np.ndarray | None = None
        self.inertia_: float | None = None

    def fit(self, windows: np.ndarray) -> "WassersteinKMeans":
        """Fit via `n_init` random restarts, keeping the lowest-inertia run."""
        sorted_windows = self._validate(windows)
        if self.n_clusters > sorted_windows.shape[0]:
            raise ValueError("n_clusters cannot exceed the number of windows")

        rng = np.random.default_rng(self.random_state)
        best: _FitResult | None = None
        for _ in range(self.n_init):
            candidate = self._fit_once(sorted_windows, rng)
            if best is None or candidate.inertia < best.inertia:
                best = candidate

        assert best is not None
        self.labels_ = best.labels
        self.centroids_ = best.centroids
        self.inertia_ = best.inertia
        return self

    def predict(self, windows: np.ndarray) -> np.ndarray:
        """Assign windows to the nearest fitted Wasserstein centroid."""
        if self.centroids_ is None:
            raise ValueError("WassersteinKMeans must be fitted before predict")
        sorted_windows = self._validate(windows)
        distances = self._distances(sorted_windows, self.centroids_)
        return np.argmin(distances, axis=1)

    def fit_predict(self, windows: np.ndarray) -> np.ndarray:
        self.fit(windows)
        assert self.labels_ is not None
        return self.labels_.copy()

    def _fit_once(self, sorted_windows: np.ndarray, rng: np.random.Generator) -> _FitResult:
        indices = rng.choice(sorted_windows.shape[0], size=self.n_clusters, replace=False)
        centroids = sorted_windows[indices].copy()
        labels = np.full(sorted_windows.shape[0], -1, dtype=int)
        inertia = float("inf")

        for _ in range(self.max_iter):
            distances = self._distances(sorted_windows, centroids)
            new_labels = np.argmin(distances, axis=1)
            new_inertia = float(np.sum(np.min(distances, axis=1) ** 2))

            new_centroids = np.empty_like(centroids)
            for cluster in range(self.n_clusters):
                members = sorted_windows[new_labels == cluster]
                if len(members) == 0:
                    new_centroids[cluster] = sorted_windows[
                        rng.integers(0, sorted_windows.shape[0])
                    ]
                else:
                    new_centroids[cluster] = wasserstein_barycenter_1d(members)

            shift = float(np.max(self._paired_distance(centroids, new_centroids)))
            changed = not np.array_equal(labels, new_labels)
            labels, centroids, inertia = new_labels, new_centroids, new_inertia
            if not changed or shift <= self.tol:
                break

        return _FitResult(labels=labels, centroids=centroids, inertia=inertia)

    def _distances(self, sorted_windows: np.ndarray, sorted_centroids: np.ndarray) -> np.ndarray:
        diff = np.abs(sorted_windows[:, None, :] - sorted_centroids[None, :, :])
        return np.mean(diff**self.p, axis=2) ** (1.0 / self.p)

    def _paired_distance(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        diff = np.abs(a - b)
        return np.mean(diff**self.p, axis=1) ** (1.0 / self.p)

    @staticmethod
    def _validate(windows: np.ndarray) -> np.ndarray:
        arr = np.asarray(windows, dtype=float)
        if arr.ndim != 2:
            raise ValueError("windows must be a two-dimensional array")
        if arr.shape[0] == 0 or arr.shape[1] == 0:
            raise ValueError("windows must not be empty")
        if not np.all(np.isfinite(arr)):
            raise ValueError("windows contains non-finite values")
        return np.sort(arr, axis=1)


def walk_forward_labels(
    windows: np.ndarray,
    end_dates: list,
    *,
    n_clusters: int,
    refit_every: int,
    min_fit_windows: int,
    n_init: int,
    seed: int,
    p: int | float = 1,
    max_iter: int = 100,
) -> pd.DataFrame:
    """Strictly-causal walk-forward regime labels.

    At step i (0-indexed), the model may be refit only on `windows[:i]` --
    windows ending strictly BEFORE the window being labeled -- so window i
    can never be a member of its own training set. A refit happens the first
    time at least `min_fit_windows` training windows are available, and
    thereafter at most every `refit_every` steps; between refits the
    previously fitted model is reused for prediction only. The first
    `min_fit_windows` steps carry no label (`pd.NA`). Each refit uses
    `seed + i` (upstream's per-refit seed convention).

    Returns a DataFrame indexed by end_date with columns:
      - label (nullable Int64): the assigned regime label, or NA if unlabeled.
      - high_dispersion (nullable boolean): whether this window's label is the
        max-centroid-dispersion regime of the model CURRENTLY active at this
        step (dispersion = std of each centroid's own sorted return values).
      - n_fit_windows (nullable Int64): how many training windows produced the
        model used to label this step.

    Labels are historical descriptions, not forecasts of anything.
    """
    window_arr = np.asarray(windows, dtype=float)
    if window_arr.ndim != 2:
        raise ValueError("windows must be a two-dimensional array")
    n = window_arr.shape[0]
    if len(end_dates) != n:
        raise ValueError("end_dates and windows must have the same length")
    if n_clusters <= 0:
        raise ValueError("n_clusters must be positive")
    if refit_every <= 0:
        raise ValueError("refit_every must be positive")
    if min_fit_windows < n_clusters:
        raise ValueError("min_fit_windows must be at least n_clusters")

    labels: list[int | None] = []
    high_dispersion: list[bool | None] = []
    n_fit: list[int | None] = []

    model: WassersteinKMeans | None = None
    last_fit_at = -1
    for i in range(n):
        if i < min_fit_windows:
            labels.append(None)
            high_dispersion.append(None)
            n_fit.append(None)
            continue

        # Refit only on windows[:i] -- window i is NEVER in its own training
        # set. Reuse the current model between scheduled refits.
        if model is None or (i - last_fit_at) >= refit_every:
            model = WassersteinKMeans(
                n_clusters=n_clusters,
                p=p,
                max_iter=max_iter,
                n_init=n_init,
                random_state=seed + i,
            ).fit(window_arr[:i])
            last_fit_at = i

        assert model.centroids_ is not None
        label = int(model.predict(window_arr[i : i + 1])[0])
        dispersion = np.std(model.centroids_, axis=1, ddof=1)
        high_regime = int(np.argmax(dispersion))

        labels.append(label)
        high_dispersion.append(bool(label == high_regime))
        n_fit.append(last_fit_at)

    return pd.DataFrame(
        {
            "label": pd.array(labels, dtype="Int64"),
            "high_dispersion": pd.array(high_dispersion, dtype="boolean"),
            "n_fit_windows": pd.array(n_fit, dtype="Int64"),
        },
        index=pd.Index(end_dates, name="end_date"),
    )


def transition_frequencies(labels: pd.Series | np.ndarray) -> pd.DataFrame:
    """Empirical next-label transition frequencies.

    HISTORICAL FREQUENCIES, NOT FORECASTS: this is a row-normalized count of
    what label followed what label across the walk-forward-labeled history
    that has already occurred. It carries no claim about what will happen
    next.
    """
    series = labels.dropna() if isinstance(labels, pd.Series) else pd.Series(labels).dropna()
    if len(series) < 2:
        raise ValueError("transition_frequencies needs at least 2 labeled steps")
    values = series.astype(int).to_numpy()

    unique = np.unique(values)
    counts = pd.DataFrame(0.0, index=unique, columns=unique)
    for current, nxt in zip(values[:-1], values[1:]):
        counts.loc[current, nxt] += 1.0
    row_sums = counts.sum(axis=1).replace(0.0, np.nan)
    freq = counts.div(row_sums, axis=0).fillna(0.0)
    freq.index.name = "label"
    freq.columns.name = "next_label"
    return freq

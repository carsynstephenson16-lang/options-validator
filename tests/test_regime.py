"""tests/test_regime.py -- offline tests for the Wasserstein regime lane.

Fully offline; synthetic in-memory data only, no filesystem cache
dependency (the close-loader is always injected). See
options_researcher/regime.py and options_researcher/regime_report.py for the
DISPLAY-ONLY lane these tests cover (.cursorrules "Scope guard" owner-
directed exception, 2026-08-03).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from options_researcher import regime, regime_report


def _bdates(n: int, start: str = "2020-01-02") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


class WassersteinDistanceTests(unittest.TestCase):
    def test_zero_self_distance(self):
        a = np.array([0.01, -0.02, 0.03, 0.0])
        self.assertAlmostEqual(regime.wasserstein_1d(a, a, p=1), 0.0)

    def test_symmetry(self):
        a = np.array([0.01, -0.02, 0.03, 0.0])
        b = np.array([0.02, 0.01, -0.01, 0.05])
        self.assertAlmostEqual(
            regime.wasserstein_1d(a, b, p=1), regime.wasserstein_1d(b, a, p=1)
        )

    def test_shifted_samples_distance_equals_shift(self):
        a = np.array([0.0, 0.01, 0.02, 0.03, 0.04])
        shift = 0.05
        b = a + shift
        self.assertAlmostEqual(regime.wasserstein_1d(a, b, p=1), shift, places=9)

    def test_unequal_length_raises(self):
        with self.assertRaises(ValueError):
            regime.wasserstein_1d(np.array([0.0, 0.1]), np.array([0.0, 0.1, 0.2]))

    def test_scipy_cross_check_if_available(self):
        try:
            import scipy.stats  # noqa: F401
        except ImportError:
            self.skipTest("scipy is not a project dependency; skipping cross-check")
        from scipy.stats import wasserstein_distance

        rng = np.random.default_rng(0)
        a = rng.normal(size=50)
        b = rng.normal(loc=0.1, size=50)
        expected = wasserstein_distance(a, b)
        got = regime.wasserstein_1d(a, b, p=1)
        self.assertAlmostEqual(got, expected, places=6)


class BarycenterTests(unittest.TestCase):
    def test_identical_windows_barycenter_is_sorted_window(self):
        window = np.array([0.03, -0.01, 0.02, 0.0])
        stacked = np.vstack([window, window])
        got = regime.wasserstein_barycenter_1d(stacked)
        np.testing.assert_allclose(got, np.sort(window))


class PairwiseWassersteinTests(unittest.TestCase):
    def test_matrix_is_symmetric_with_zero_diagonal(self):
        windows = np.array([[0.0, 0.01, 0.02], [0.01, 0.02, 0.03], [-0.02, -0.01, 0.0]])
        dist = regime.pairwise_wasserstein(windows, p=1)
        np.testing.assert_allclose(np.diag(dist), 0.0)
        np.testing.assert_allclose(dist, dist.T)


class MakeReturnWindowsTests(unittest.TestCase):
    def test_shapes_and_end_dates(self):
        dates = _bdates(20)
        closes = pd.Series(100 * np.cumprod(1 + 0.001 * np.arange(20)), index=dates)
        windows, end_dates = regime.make_return_windows(closes, window=5, step=2)
        self.assertEqual(windows.shape[1], 5)
        self.assertEqual(len(end_dates), windows.shape[0])

    def test_non_monotonic_index_rejected(self):
        dates = list(_bdates(5))
        closes = pd.Series(
            [1.0, 2.0, 3.0, 4.0, 5.0],
            index=[dates[0], dates[2], dates[1], dates[3], dates[4]],
        )
        with self.assertRaises(ValueError):
            regime.make_return_windows(closes, window=2, step=1)

    def test_too_short_series_rejected(self):
        closes = pd.Series([1.0, 2.0, 3.0], index=_bdates(3))
        with self.assertRaises(ValueError):
            regime.make_return_windows(closes, window=5, step=1)


def _synthetic_regime_windows(seed: int = 0, n_low: int = 40, n_high: int = 40, window: int = 20):
    rng = np.random.default_rng(seed)
    low = rng.normal(0.0, 0.005, size=(n_low, window))
    high = rng.normal(0.0, 0.03, size=(n_high, window))
    windows = np.vstack([low, high])
    labels_true = np.array([0] * n_low + [1] * n_high)
    return windows, labels_true


class WassersteinKMeansTests(unittest.TestCase):
    def test_deterministic_under_fixed_seed(self):
        windows, _ = _synthetic_regime_windows()
        m1 = regime.WassersteinKMeans(n_clusters=2, n_init=3, random_state=42).fit(windows)
        m2 = regime.WassersteinKMeans(n_clusters=2, n_init=3, random_state=42).fit(windows)
        np.testing.assert_array_equal(m1.labels_, m2.labels_)
        np.testing.assert_allclose(m1.centroids_, m2.centroids_)

    def test_recovers_two_separated_regimes(self):
        windows, labels_true = _synthetic_regime_windows()
        model = regime.WassersteinKMeans(n_clusters=2, n_init=5, random_state=7).fit(windows)
        labels = model.labels_
        assert labels is not None
        # Cluster identity is arbitrary; check the partition matches the true
        # low-vol/high-vol split up to a label permutation.
        same = float(np.mean(labels == labels_true))
        flipped = float(np.mean(labels == (1 - labels_true)))
        self.assertGreaterEqual(max(same, flipped), 0.95)


class WalkForwardCausalityTests(unittest.TestCase):
    def _make_closes(self, n: int = 400, seed: int = 1) -> pd.Series:
        rng = np.random.default_rng(seed)
        dates = _bdates(n)
        rets = rng.normal(0.0, 0.01, size=n)
        return pd.Series(100 * np.cumprod(1 + rets), index=dates)

    def _windows(self):
        closes = self._make_closes()
        return regime.make_return_windows(closes, window=20, step=5)

    def test_causality_tail_mutation_does_not_change_past_labels(self):
        windows, end_dates = self._windows()
        common_kwargs = dict(n_clusters=2, refit_every=5, min_fit_windows=10, n_init=2, seed=3)

        labeled_before = regime.walk_forward_labels(windows, end_dates, **common_kwargs)

        k = len(windows) // 2
        mutated = windows.copy()
        rng = np.random.default_rng(999)
        mutated[k + 1 :] = rng.normal(0.0, 0.05, size=mutated[k + 1 :].shape)
        labeled_after = regime.walk_forward_labels(mutated, end_dates, **common_kwargs)

        pd.testing.assert_series_equal(
            labeled_before["label"].iloc[: k + 1], labeled_after["label"].iloc[: k + 1]
        )
        pd.testing.assert_series_equal(
            labeled_before["n_fit_windows"].iloc[: k + 1],
            labeled_after["n_fit_windows"].iloc[: k + 1],
        )
        pd.testing.assert_series_equal(
            labeled_before["high_dispersion"].iloc[: k + 1],
            labeled_after["high_dispersion"].iloc[: k + 1],
        )

    def test_no_window_in_own_training_set(self):
        windows, end_dates = self._windows()
        labeled = regime.walk_forward_labels(
            windows, end_dates, n_clusters=2, refit_every=5, min_fit_windows=10, n_init=2, seed=3
        )
        labeled_rows = labeled.dropna(subset=["label"])
        for end_date, n_fit in labeled_rows["n_fit_windows"].items():
            step = labeled.index.get_loc(end_date)
            # Training-set size used for this step must be strictly less than
            # the number of windows observable through and including step i
            # (i + 1): the window being labeled is never inside its own fit.
            self.assertLess(int(n_fit), step + 1)

    def test_first_min_fit_windows_have_no_label(self):
        windows, end_dates = self._windows()
        labeled = regime.walk_forward_labels(
            windows, end_dates, n_clusters=2, refit_every=5, min_fit_windows=10, n_init=2, seed=3
        )
        self.assertTrue(labeled["label"].iloc[:10].isna().all())
        self.assertFalse(labeled["label"].iloc[10:].isna().all())

    def test_invalid_min_fit_windows_below_n_clusters_rejected(self):
        windows, end_dates = self._windows()
        with self.assertRaises(ValueError):
            regime.walk_forward_labels(
                windows, end_dates, n_clusters=3, refit_every=5, min_fit_windows=2, n_init=2, seed=3
            )


class TransitionFrequenciesTests(unittest.TestCase):
    def test_rows_sum_to_one(self):
        labels = pd.Series([0, 0, 1, 1, 0, 1, 1, 1])
        freq = regime.transition_frequencies(labels)
        row_sums = freq.sum(axis=1)
        for value in row_sums:
            self.assertAlmostEqual(value, 1.0, places=9)

    def test_too_few_labels_rejected(self):
        with self.assertRaises(ValueError):
            regime.transition_frequencies(pd.Series([0]))


class BuildReportTests(unittest.TestCase):
    def _loader(self, series_by_symbol: dict, missing: tuple = ()):
        def _load(symbol: str, start_iso: str, end_iso: str) -> pd.Series:
            if symbol in missing:
                raise FileNotFoundError(f"no cached closes for {symbol}")
            return series_by_symbol[symbol]

        return _load

    def _make_closes(self, n: int = 400, seed: int = 2) -> pd.Series:
        rng = np.random.default_rng(seed)
        dates = _bdates(n)
        rets = rng.normal(0.0, 0.01, size=n)
        return pd.Series(100 * np.cumprod(1 + rets), index=[str(d.date()) for d in dates])

    def test_report_contains_asof_date_and_disclaimers(self):
        closes = self._make_closes()
        loader = self._loader({"VST": closes})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.md"
            text, exit_code = regime_report.build_report(
                ["VST"], out_path=out_path, loader=loader, end_iso="2021-06-01"
            )
            self.assertTrue(out_path.is_file())
        self.assertEqual(exit_code, 0)
        self.assertIn(str(closes.index[-1]), text)
        self.assertIn("non-verdict-bearing", text)
        self.assertIn("historical frequencies, not forecasts", text)

    def test_missing_symbol_is_skipped_not_crashed(self):
        closes = self._make_closes()
        loader = self._loader({"CEG": closes}, missing=("VST",))
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.md"
            text, exit_code = regime_report.build_report(
                ["VST", "CEG"], out_path=out_path, loader=loader, end_iso="2021-06-01"
            )
        self.assertIn("VST -- SKIPPED", text)
        self.assertEqual(exit_code, 0)  # CEG still produced a section

    def test_all_symbols_missing_returns_exit_code_1(self):
        loader = self._loader({}, missing=("VST", "CEG"))
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.md"
            text, exit_code = regime_report.build_report(
                ["VST", "CEG"], out_path=out_path, loader=loader, end_iso="2021-06-01"
            )
        self.assertIn("VST -- SKIPPED", text)
        self.assertIn("CEG -- SKIPPED", text)
        self.assertEqual(exit_code, 1)

    def test_exactly_one_labeled_step_renders_without_transition_table(self):
        # 184 closes -> 183 log returns -> 25 windows (63/5) -> exactly one
        # labeled step at min_fit_windows=24. Pre-fix this band crashed in
        # transition_frequencies; the section must render and stay exit 0.
        closes = self._make_closes(n=184, seed=5)
        loader = self._loader({"VST": closes})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.md"
            text, exit_code = regime_report.build_report(
                ["VST"], out_path=out_path, loader=loader, end_iso="2021-06-01"
            )
        self.assertEqual(exit_code, 0)
        self.assertIn("Latest walk-forward regime label", text)
        self.assertIn("only one labeled step", text)

    def test_too_short_history_is_skipped(self):
        short_closes = pd.Series(
            [100.0, 101.0, 102.0], index=["2026-01-02", "2026-01-05", "2026-01-06"]
        )
        loader = self._loader({"VST": short_closes})
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "report.md"
            text, exit_code = regime_report.build_report(
                ["VST"], out_path=out_path, loader=loader, end_iso="2026-01-06"
            )
        self.assertIn("VST -- SKIPPED", text)
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()

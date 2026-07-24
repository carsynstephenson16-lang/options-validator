"""tests/test_deflated_sharpe.py -- Probabilistic/Deflated Sharpe Ratio
(PSR/DSR) display/diagnostic layer (Phase-1B, 2026-07-24).

Official-source: Bailey, D.H. & Lopez de Prado, M. (2012), "The Sharpe Ratio
Efficient Frontier", Journal of Risk 15(2); and (2014), "The Deflated Sharpe
Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-
Normality", Journal of Portfolio Management 40(5). The re-derivation lives
in metrics.py's PSR/DSR docstring block, reproduced here in brief:

    PSR(SR*) = Phi[ (SR_hat - SR*) * sqrt(T-1)
                     / sqrt(1 - skew*SR_hat + ((kurt-1)/4)*SR_hat**2) ]
        SR_hat = observed per-period (NOT annualized) Sharpe; T = number of
        return observations; skew = sample skewness; kurt = RAW (non-excess)
        kurtosis (normal -> 3.0, not 0.0).

    DSR = PSR(SR* = E[max of N trial SRs])
    E[max SR] = mean_trial_sr + sqrt(trial_sr_variance) *
                [ (1-gamma)*Phi^-1(1-1/N) + gamma*Phi^-1(1-1/(N*e)) ]
        gamma = Euler-Mascheroni constant ~ 0.5772156649.

Every pinned vector below was independently re-derived by hand from this
formula (see the mission report for the arithmetic) before being checked
against the implementation. All matched to >= 6 decimal places -- no
discrepancy between the brief's LLM-computed vectors and this
implementation was found.

PSR/DSR are diagnostics only: this file does not (and must not) assert
anything about verdict, gating, ranking, or triggers -- see
ScoreboardDsrIntegrationTests.test_verdict_byte_identical_with_and_without_dsr.
"""
import math
import tempfile
import unittest
from datetime import date

import numpy as np

import config
import metrics
from metrics import dsr, expected_max_sr, psr, sample_moments, scoreboard
from research import ledger


class NormInverseAccuracyTests(unittest.TestCase):
    """Pin metrics._norm_ppf (Acklam's rational approximation + one Halley
    refinement step against math.erfc, no scipy) against textbook standard-
    normal quantiles."""

    def test_975_quantile(self):
        self.assertAlmostEqual(metrics._norm_ppf(0.975), 1.959963984540054, places=9)

    def test_90_quantile(self):
        self.assertAlmostEqual(metrics._norm_ppf(0.9), 1.2815515655446008, places=9)

    def test_50_quantile_is_zero(self):
        self.assertAlmostEqual(metrics._norm_ppf(0.5), 0.0, places=9)

    def test_99_quantile(self):
        self.assertAlmostEqual(metrics._norm_ppf(0.99), 2.3263478740408408, places=8)

    def test_rejects_outside_open_interval(self):
        for p in (0.0, 1.0, -0.1, 1.1):
            with self.subTest(p=p):
                with self.assertRaises(ValueError):
                    metrics._norm_ppf(p)

    def test_cdf_ppf_roundtrip(self):
        for z in (-2.5, -1.0, 0.0, 0.33, 1.96, 3.0):
            with self.subTest(z=z):
                p = metrics._norm_cdf(z)
                self.assertAlmostEqual(metrics._norm_ppf(p), z, places=6)


class PsrVectorTests(unittest.TestCase):
    """Pinned PSR vectors from the mission brief (LLM-computed, then
    independently re-derived by hand and confirmed to >= 6dp)."""

    def test_zero_skew_normal_kurtosis(self):
        self.assertAlmostEqual(psr(0.30, 0, 60, 0.0, 3.0), 0.987908, places=6)

    def test_negative_skew_fat_tail_options_selling_shape(self):
        # The options-selling shape: many small wins, rare large losses.
        # Negative skew + fat tails (kurt > 3) should DEFLATE PSR relative
        # to the same SR/T under a normal-ish return distribution.
        self.assertAlmostEqual(psr(0.30, 0, 60, -1.2, 6.0), 0.971216, places=6)
        self.assertLess(
            psr(0.30, 0, 60, -1.2, 6.0),
            psr(0.30, 0, 60, 0.0, 3.0),
        )

    def test_nonzero_null_short_sample(self):
        self.assertAlmostEqual(psr(1.0, 0.5, 24, -0.5, 5.0), 0.935313, places=6)


class ExpectedMaxSrVectorTests(unittest.TestCase):
    def test_n2(self):
        self.assertAlmostEqual(expected_max_sr(0.0, 0.09, 2), 0.155927, places=6)

    def test_n10(self):
        self.assertAlmostEqual(expected_max_sr(0.0, 0.09, 10), 0.472379, places=6)

    def test_n100(self):
        self.assertAlmostEqual(expected_max_sr(0.0, 0.09, 100), 0.759181, places=6)

    def test_monotone_increasing_in_n(self):
        vals = [expected_max_sr(0.0, 0.09, n) for n in (2, 10, 100, 1000)]
        for a, b in zip(vals, vals[1:]):
            self.assertLess(a, b)

    def test_rejects_one_trial(self):
        with self.assertRaises(ValueError):
            expected_max_sr(0.0, 0.09, 1)

    def test_rejects_zero_trials(self):
        with self.assertRaises(ValueError):
            expected_max_sr(0.0, 0.09, 0)


class DsrVectorTests(unittest.TestCase):
    def test_pinned_vector(self):
        self.assertAlmostEqual(
            dsr(0.9, 60, -1.2, 6.0, trial_sr_variance=0.09, n_trials=10),
            0.969105, places=6,
        )

    def test_propagates_expected_max_sr_value_error(self):
        with self.assertRaises(ValueError):
            dsr(0.9, 60, -1.2, 6.0, trial_sr_variance=0.09, n_trials=1)

    def test_monotone_decreasing_in_n_trials(self):
        """More trials -> a higher E[max SR] benchmark -> a HARDER bar to
        clear -> a lower (or equal) DSR, everything else held fixed."""
        values = [
            dsr(0.9, 60, -1.2, 6.0, trial_sr_variance=0.09, n_trials=n)
            for n in (2, 5, 10, 50, 200, 1000)
        ]
        for a, b in zip(values, values[1:]):
            self.assertGreaterEqual(a, b)

    def test_mean_trial_sr_default_is_zero(self):
        explicit = dsr(0.9, 60, -1.2, 6.0, trial_sr_variance=0.09, n_trials=10,
                        mean_trial_sr=0.0)
        default = dsr(0.9, 60, -1.2, 6.0, trial_sr_variance=0.09, n_trials=10)
        self.assertEqual(explicit, default)


class PsrNaNPathTests(unittest.TestCase):
    """NaN is a valid, non-raising outcome for a thin/degenerate sample --
    matches scoreboard()'s refusal philosophy elsewhere in this repo."""

    def test_nan_below_two_observations(self):
        self.assertTrue(math.isnan(psr(0.3, 0.0, 1, 0.0, 3.0)))
        self.assertTrue(math.isnan(psr(0.3, 0.0, 0, 0.0, 3.0)))

    def test_nan_when_denominator_non_positive(self):
        # skew=5, sr=1, kurt=3 -> denom_sq = 1 - 5*1 + (2/4)*1**2 = -3.5 < 0
        self.assertTrue(math.isnan(psr(1.0, 0.0, 60, 5.0, 3.0)))

    def test_nan_propagates_from_nan_skew_kurt(self):
        skew, kurt = sample_moments([1.0, 1.0])  # n=2 -> both undefined
        self.assertTrue(math.isnan(skew))
        self.assertTrue(math.isnan(kurt))
        self.assertTrue(math.isnan(psr(0.3, 0.0, 60, skew, kurt)))

    def test_finite_at_exactly_two_observations(self):
        # t=2 is the boundary: sqrt(t-1)=1 is defined, so psr() should NOT
        # be NaN here (only t<2 triggers the thin-sample NaN path).
        self.assertFalse(math.isnan(psr(0.3, 0.0, 2, 0.0, 3.0)))


class SampleMomentsTests(unittest.TestCase):
    """Plain (biased/population, method-of-moments) skew/kurt estimators --
    NOT scipy's bias-corrected g1/G1. kurt uses the RAW (non-excess)
    convention: a normal sample reads ~3.0, not ~0.0."""

    def test_large_normal_sample_reads_near_textbook_values(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=200_000)
        skew, kurt = sample_moments(x)
        self.assertAlmostEqual(skew, 0.0, delta=0.05)
        self.assertAlmostEqual(kurt, 3.0, delta=0.05)

    def test_never_raises_on_empty(self):
        skew, kurt = sample_moments([])
        self.assertTrue(math.isnan(skew))
        self.assertTrue(math.isnan(kurt))

    def test_nan_below_three_observations(self):
        skew, kurt = sample_moments([1.0, 2.0])
        self.assertTrue(math.isnan(skew))
        self.assertTrue(math.isnan(kurt))

    def test_skew_defined_kurt_nan_at_exactly_three(self):
        skew, kurt = sample_moments([1.0, 2.0, 5.0])
        self.assertFalse(math.isnan(skew))
        self.assertTrue(math.isnan(kurt))

    def test_both_defined_at_four_observations(self):
        skew, kurt = sample_moments([1.0, 2.0, 5.0, 3.0])
        self.assertFalse(math.isnan(skew))
        self.assertFalse(math.isnan(kurt))

    def test_zero_variance_sample_is_nan_not_a_crash(self):
        skew, kurt = sample_moments([2.0, 2.0, 2.0, 2.0])
        self.assertTrue(math.isnan(skew))
        self.assertTrue(math.isnan(kurt))


def _trades(pnls, start=date(2020, 1, 6)):
    """Weekly-spaced synthetic trades: enough distinct ISO-week cohorts for
    scoreboard()'s dependence-aware CI, one per element of `pnls`."""
    base = start.toordinal()
    return [
        {
            "pnl": float(p),
            "capital_at_risk": 350.0,
            "entry_date": date.fromordinal(base + i * 7).isoformat(),
            "symbol": "VST",
        }
        for i, p in enumerate(pnls)
    ]


class ScoreboardDsrIntegrationTests(unittest.TestCase):
    def setUp(self):
        # 12 modest wins + 10 sizeable losses: n=22 >= DSR_MIN_T (10), and
        # enough losses/cohorts to reach a real (non-INSUFFICIENT-SAMPLE)
        # verdict, so the byte-identity test below compares two real verdicts.
        import random
        rng = random.Random(3)
        self.pnls = ([rng.uniform(20, 80) for _ in range(12)]
                     + [-rng.uniform(150, 400) for _ in range(10)])
        self.assertGreaterEqual(len(self.pnls), config.DSR_MIN_T)

    def test_absent_kwargs_add_no_keys(self):
        result = scoreboard(_trades(self.pnls))
        for key in ("dsr", "psr_vs_zero", "dsr_n_trials", "dsr_n_provenance", "dsr_note"):
            self.assertNotIn(key, result)

    def test_partial_kwargs_do_not_activate_dsr(self):
        # ALL THREE dsr_* kwargs are required together; one or two supplied
        # must behave exactly like none supplied.
        only_n = scoreboard(_trades(self.pnls), dsr_n_trials=5)
        self.assertNotIn("dsr", only_n)
        n_and_var = scoreboard(_trades(self.pnls), dsr_n_trials=5,
                                dsr_trial_sr_variance=0.01)
        self.assertNotIn("dsr", n_and_var)

    def test_present_when_all_three_supplied(self):
        result = scoreboard(
            _trades(self.pnls), dsr_n_trials=21, dsr_trial_sr_variance=0.05,
            dsr_n_provenance="ledger-trial-count",
        )
        for key in ("dsr", "psr_vs_zero", "dsr_n_trials", "dsr_n_provenance", "dsr_note"):
            self.assertIn(key, result)
        self.assertEqual(result["dsr_n_trials"], 21)
        self.assertEqual(result["dsr_n_provenance"], "ledger-trial-count")
        self.assertIn("N=21 trials (ledger-trial-count)", result["dsr_note"])
        self.assertIn("does not replace the loss-gated verdict", result["dsr_note"])

    def test_verdict_byte_identical_with_and_without_dsr(self):
        """The load-bearing non-negotiable: nothing about DSR may touch the
        loss-gated verdict."""
        without = scoreboard(_trades(self.pnls))
        with_dsr = scoreboard(
            _trades(self.pnls), dsr_n_trials=21, dsr_trial_sr_variance=0.05,
            dsr_n_provenance="ledger-trial-count",
        )
        self.assertEqual(without["verdict"], with_dsr["verdict"])
        # Byte-identical, not just equal: same type, same exact string.
        self.assertIs(type(without["verdict"]), type(with_dsr["verdict"]))
        self.assertEqual(
            without["verdict"].encode(), with_dsr["verdict"].encode())

    def test_insufficient_sample_below_dsr_min_t(self):
        short = self.pnls[:config.DSR_MIN_T - 1]
        result = scoreboard(
            _trades(short), dsr_n_trials=21, dsr_trial_sr_variance=0.05,
            dsr_n_provenance="p",
        )
        self.assertEqual(result["dsr"], "INSUFFICIENT SAMPLE FOR DSR")

    def test_numeric_dsr_at_or_above_min_t(self):
        result = scoreboard(
            _trades(self.pnls), dsr_n_trials=21, dsr_trial_sr_variance=0.05,
            dsr_n_provenance="p",
        )
        self.assertIsInstance(result["dsr"], float)
        self.assertIsInstance(result["psr_vs_zero"], float)


class LedgerBackwardCompatibilityTests(unittest.TestCase):
    """The chain is tamper-evident; loosening the deflated_sharpe schema
    must never invalidate a single historical record. Read-only against the
    REAL committed ledger (never writes)."""

    def test_real_committed_ledger_still_verifies(self):
        ledger.verify("ledger")  # must not raise

    def test_real_committed_ledger_trial_count_unaffected(self):
        # A schema-validation change must not alter trial counting.
        count = ledger.current_trial_count("ledger")
        self.assertIsInstance(count, int)
        self.assertGreaterEqual(count, 0)

    def test_synthetic_pre_phase_1b_ledger_still_verifies(self):
        """A ledger written entirely under the OLD (always-null) regime must
        still verify unchanged under the new schema code."""
        with tempfile.TemporaryDirectory() as base:
            ledger.append({
                "entry_type": "run",
                "timestamp": "2026-01-01T00:00:00+00:00",
                "run_id": "legacy-run",
                "hypothesis_id": "H-legacy",
                "decision_threshold": "expectancy CI lower bound > 0",
                "code_sha": "e" * 40,
                "config_hash": "a" * 64,
                "cost_model_hash": "b" * 64,
                "source_hash": "c" * 64,
                "data_window_hash": "d" * 64,
                "risk_basis": "economic_max_loss",
                "is_window": {"start": "2018-01-01", "end": "2022-12-31"},
                "is_result": {"verdict": "x"},
                "oos_window": {"start": "2023-01-01", "end": "2024-12-31"},
                "oos_result": None,
                "deflated_sharpe": None,
                "pbo": None,
                "notes": "",
                "scope": {"symbols": ["SPY"]},
            }, base)
            ledger.verify(base)  # no raise


if __name__ == "__main__":
    unittest.main()

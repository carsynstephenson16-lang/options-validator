"""Offline tests for labels, placebo determinism, and walk-forward comparison."""

import unittest

import numpy as np
import pandas as pd

from options_researcher.flow.study import (
    compare_walk_forward,
    make_forward_labels,
    seeded_sign_placebo,
)


class StudyTests(unittest.TestCase):
    def test_forward_labels_use_only_future_closes(self):
        dates = pd.bdate_range("2025-01-02", periods=25)
        closes = pd.DataFrame(
            {
                "symbol": "MSFT",
                "session": dates.strftime("%Y-%m-%d"),
                "close": np.arange(100.0, 125.0),
            }
        )
        out = make_forward_labels(closes)
        self.assertAlmostEqual(out.iloc[0]["return_1"], 101.0 / 100.0 - 1.0)
        self.assertTrue(pd.isna(out.iloc[-1]["return_1"]))
        self.assertFalse(pd.isna(out.iloc[0]["future_rv21"]))

    def test_seeded_placebo_is_reproducible(self):
        values = pd.Series([1.0, 2.0, 3.0, 4.0])
        self.assertTrue(
            seeded_sign_placebo(values, seed=7).equals(seeded_sign_placebo(values, seed=7))
        )
        self.assertFalse(seeded_sign_placebo(values, seed=7).equals(values))

    def test_walk_forward_accepts_purge_at_target_horizon_and_detects_flow_improvement(self):
        # target column follows the "return_<horizon>" naming convention
        # (required_horizon_for), not an arbitrary generic name -- see
        # test_walk_forward_rejects_unknown_target_naming_convention below
        # for what happens when it does not.
        dates = pd.bdate_range("2025-01-02", periods=75)
        panel = pd.DataFrame(
            {
                "session": dates.strftime("%Y-%m-%d"),
                "baseline_validator_output": np.linspace(-1.0, 1.0, len(dates)),
                "flow_signal": np.sin(np.arange(len(dates)) / 5.0),
            }
        )
        panel["return_5"] = panel["baseline_validator_output"] * 0.5 + panel["flow_signal"] * 0.2
        out = compare_walk_forward(
            panel,
            target="return_5",
            target_horizon_observations=5,
            flow_columns=["flow_signal"],
            train_observations=30,
            test_observations=10,
            step_observations=12,
            purge_observations=5,
            embargo_observations=2,
        )
        self.assertGreater(len(out), 0)
        self.assertTrue((out["test_start"] > out["train_end"]).all())
        self.assertTrue((out["rmse_improvement"] > 0.0).all())

    def test_walk_forward_rejects_purge_shorter_than_target_horizon(self):
        dates = pd.bdate_range("2025-01-02", periods=50)
        panel = pd.DataFrame(
            {
                "session": dates.strftime("%Y-%m-%d"),
                "baseline_validator_output": np.linspace(-1.0, 1.0, len(dates)),
                "flow_signal": np.sin(np.arange(len(dates)) / 5.0),
                "return_5": np.linspace(0.0, 1.0, len(dates)),
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            "purge_observations must be at least target_horizon_observations",
        ):
            compare_walk_forward(
                panel,
                target="return_5",
                target_horizon_observations=5,
                flow_columns=["flow_signal"],
                train_observations=30,
                test_observations=10,
                step_observations=12,
                purge_observations=4,
                embargo_observations=2,
            )

    def test_walk_forward_rejects_purge_shorter_than_the_targets_own_horizon(self):
        """Codex PR #19 review finding: purge was only checked against the
        caller-supplied `target_horizon_observations`, with no check tying it
        to what `target` itself actually needs. A caller could declare a
        too-small target_horizon_observations for a "return_21" target and
        still pass purge_observations=5 -- 16 observations short of the real
        21-session look-ahead the target encodes -- leaking future
        information across the purge boundary. The registry-derived check
        must catch this even when the caller-supplied value agrees."""
        dates = pd.bdate_range("2025-01-02", periods=75)
        panel = pd.DataFrame(
            {
                "session": dates.strftime("%Y-%m-%d"),
                "baseline_validator_output": np.linspace(-1.0, 1.0, len(dates)),
                "flow_signal": np.sin(np.arange(len(dates)) / 5.0),
                "return_21": np.linspace(0.0, 1.0, len(dates)),
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            r"purge_observations must be at least 'return_21'.*21 observations",
        ):
            compare_walk_forward(
                panel,
                target="return_21",
                target_horizon_observations=5,  # understates the true 21 horizon
                flow_columns=["flow_signal"],
                train_observations=30,
                test_observations=10,
                step_observations=12,
                purge_observations=5,  # passes the (wrong) caller-supplied check
                embargo_observations=2,
            )

    def test_walk_forward_rejects_unknown_target_naming_convention(self):
        """A target column that encodes no recognizable horizon must fail
        loudly rather than silently skipping the registry-derived purge
        check (Codex PR #19 review finding)."""
        dates = pd.bdate_range("2025-01-02", periods=50)
        panel = pd.DataFrame(
            {
                "session": dates.strftime("%Y-%m-%d"),
                "baseline_validator_output": np.linspace(-1.0, 1.0, len(dates)),
                "flow_signal": np.sin(np.arange(len(dates)) / 5.0),
                "unlabeled_target": np.linspace(0.0, 1.0, len(dates)),
            }
        )
        with self.assertRaisesRegex(
            ValueError,
            "does not encode a forward-looking horizon",
        ):
            compare_walk_forward(
                panel,
                target="unlabeled_target",
                target_horizon_observations=5,
                flow_columns=["flow_signal"],
                train_observations=30,
                test_observations=10,
                step_observations=12,
                purge_observations=5,
                embargo_observations=2,
            )

    def test_context_is_in_both_models_and_final_holdout_is_untouched(self):
        dates = pd.bdate_range("2025-01-02", periods=110)
        panel = pd.DataFrame(
            {
                "session": dates.strftime("%Y-%m-%d"),
                "baseline_validator_output": np.linspace(-1.0, 1.0, len(dates)),
                "iv_context": np.sin(np.arange(len(dates)) / 7.0),
                "flow_signal": np.cos(np.arange(len(dates)) / 5.0),
            }
        )
        panel["return_5"] = panel["baseline_validator_output"] + panel["iv_context"]
        out = compare_walk_forward(
            panel,
            target="return_5",
            target_horizon_observations=5,
            flow_columns=["flow_signal"],
            context_columns=["iv_context"],
            train_observations=35,
            test_observations=10,
            step_observations=11,
            purge_observations=5,
            embargo_observations=1,
            holdout_observations=42,
        )
        holdout_start = dates[-42].date().isoformat()
        self.assertGreater(len(out), 0)
        self.assertTrue((out["test_end"] < holdout_start).all())
        self.assertLess(out["baseline_rmse"].max(), 1e-10)

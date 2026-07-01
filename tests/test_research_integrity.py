import os
import json
import math
import subprocess
import unittest

import config
from analysis import feasibility
from research import hashing
import tempfile
from pathlib import Path
from research import ledger
from research import windows
from research import experiments
from research import cli


class ConfigKnobTests(unittest.TestCase):
    def test_oos_look_budget_is_three(self):
        self.assertEqual(config.OOS_LOOK_BUDGET, 3)

    def test_block_exponent_is_one_third(self):
        self.assertAlmostEqual(config.BOOTSTRAP_BLOCK_EXPONENT, 1.0 / 3.0)

    def test_block_constants_are_the_frozen_envelope(self):
        self.assertEqual(list(config.BOOTSTRAP_BLOCK_CONSTANTS), [0.5, 1, 2, 4])

    def test_cohort_granularity_is_week(self):
        self.assertEqual(config.COHORT_GRANULARITY, "week")

    def test_fill_model_id_is_versioned_string(self):
        self.assertEqual(config.FILL_MODEL_ID, "conservative_mid_minus_haircut_v1")


class HashingTests(unittest.TestCase):
    def test_canonical_json_is_sorted_and_compact(self):
        self.assertEqual(hashing.canonical_json({"b": 1, "a": 2}), '{"a":2,"b":1}')

    def test_canonical_json_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            hashing.canonical_json({"bad": math.nan})

    def test_cost_model_snapshot_includes_scattered_credit_frac(self):
        snap = hashing.cost_model_snapshot()
        # ASSUMED_CREDIT_FRAC lives in feasibility.py, not config -- must be captured.
        self.assertEqual(snap["ASSUMED_CREDIT_FRAC"], feasibility.ASSUMED_CREDIT_FRAC)
        for key in ("SLIPPAGE_HAIRCUT", "MAX_SPREAD_PCT", "MIN_OPEN_INTEREST",
                    "FILL_MODEL_ID", "BOOTSTRAP_BLOCK_CONSTANTS", "COHORT_GRANULARITY",
                    "OOS_LOOK_BUDGET"):
            self.assertIn(key, snap)

    def test_cost_model_hash_is_deterministic(self):
        self.assertEqual(hashing.cost_model_hash(), hashing.cost_model_hash())

    def test_cost_model_hash_changes_when_a_frozen_param_changes(self):
        before = hashing.cost_model_hash()
        original = config.SLIPPAGE_HAIRCUT
        try:
            config.SLIPPAGE_HAIRCUT = original + 0.01
            self.assertNotEqual(hashing.cost_model_hash(), before)
        finally:
            config.SLIPPAGE_HAIRCUT = original

    def test_data_window_hash_is_stable_for_equal_windows(self):
        w = {"start": "2018-01-01", "end": "2022-12-31", "universe": ["SPY"]}
        self.assertEqual(hashing.data_window_hash(w), hashing.data_window_hash(dict(w)))

    def test_source_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.py").write_text("X = 1\n")
            self.assertEqual(
                hashing.source_hash(paths=("a.py",), root=tmp),
                hashing.source_hash(paths=("a.py",), root=tmp),
            )

    def test_source_snapshot_default_root_includes_config(self):
        self.assertIn("config.py", hashing.source_snapshot())

    def test_source_snapshot_default_root_includes_dependency_lock_surface(self):
        snap = hashing.source_snapshot()
        self.assertIn("pyproject.toml", snap)
        self.assertIn("uv.lock", snap)

    def test_source_hash_changes_when_source_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "a.py")
            path.write_text("X = 1\n")
            before = hashing.source_hash(paths=("a.py",), root=tmp)
            path.write_text("X = 2\n")
            self.assertNotEqual(hashing.source_hash(paths=("a.py",), root=tmp), before)


class LedgerChainTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_chains_and_verifies(self):
        ledger.append({"entry_type": "trial_intent", "reason": "first"}, self.base)
        ledger.append({"entry_type": "trial_intent", "reason": "second"}, self.base)
        ledger.verify(self.base)  # must not raise
        records = ledger.read_all(self.base)
        self.assertEqual([r["seq"] for r in records], [0, 1])
        self.assertEqual(records[1]["prev_hash"], records[0]["record_hash"])

    def test_head_matches_tip(self):
        h = ledger.append({"entry_type": "trial_intent", "reason": "x"}, self.base)
        self.assertEqual(ledger.tip(self.base), h)

    def test_verify_detects_a_tampered_record(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        ledger.append({"entry_type": "trial_intent", "reason": "keep2"}, self.base)
        jsonl = Path(self.base) / "experiments.jsonl"
        lines = jsonl.read_text().splitlines()
        lines[0] = lines[0].replace("keep", "HACKED")
        jsonl.write_text("\n".join(lines) + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_verify_wraps_invalid_json_as_ledger_error(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        (Path(self.base) / "experiments.jsonl").write_text("{not json}\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_verify_detects_head_mismatch(self):
        ledger.append({"entry_type": "trial_intent", "reason": "x"}, self.base)
        (Path(self.base) / "HEAD").write_text("0" * 64 + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base)

    def test_trial_counter_counts_runs_and_intents_only(self):
        ledger.append({"entry_type": "trial_intent", "reason": "a"}, self.base)
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        ledger.append({"entry_type": "oos_reveal", "hypothesis_id": "H1"}, self.base)
        self.assertEqual(ledger.current_trial_count(self.base), 2)

    def test_append_rejects_reserved_chain_fields(self):
        for key in ("seq", "prev_hash", "record_hash"):
            with self.subTest(key=key):
                with self.assertRaises(ledger.LedgerError):
                    ledger.append({"entry_type": "trial_intent", key: "bad"}, self.base)

    def test_append_refuses_to_build_on_broken_chain(self):
        ledger.append({"entry_type": "trial_intent", "reason": "keep"}, self.base)
        (Path(self.base) / "HEAD").write_text("0" * 64 + "\n")
        with self.assertRaises(ledger.LedgerError):
            ledger.append({"entry_type": "trial_intent", "reason": "next"}, self.base)


class LedgerAnchoringTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = self._tmp.name
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.email", "t@t.t"], check=True)
        subprocess.run(["git", "-C", self.repo, "config", "user.name", "t"], check=True)
        self.base = os.path.join(self.repo, "ledger")

    def tearDown(self):
        self._tmp.cleanup()

    def _clean_tracked(self, paths):
        # Same semantics as the default, but scoped to the temp repo via git -C.
        for p in paths:
            rel = os.path.relpath(p, self.repo)
            t = subprocess.run(["git", "-C", self.repo, "ls-files", "--error-unmatch", rel],
                               capture_output=True, text=True)
            if t.returncode != 0:
                return False
            s = subprocess.run(["git", "-C", self.repo, "status", "--porcelain", "--", rel],
                               capture_output=True, text=True)
            if s.stdout.strip():
                return False
        return True

    def test_anchored_verify_fails_when_uncommitted(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        with self.assertRaises(ledger.LedgerError):
            ledger.verify(self.base, anchored=True, git_clean_tracked=self._clean_tracked)

    def test_anchored_verify_passes_when_committed_clean(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        subprocess.run(["git", "-C", self.repo, "add", "ledger"], check=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-q", "-m", "anchor"], check=True)
        ledger.verify(self.base, anchored=True, git_clean_tracked=self._clean_tracked)  # no raise

    def test_default_clean_checker_is_repo_root_scoped(self):
        ledger.append({"entry_type": "run", "hypothesis_id": "H1"}, self.base)
        subprocess.run(["git", "-C", self.repo, "add", "ledger"], check=True)
        subprocess.run(["git", "-C", self.repo, "commit", "-q", "-m", "anchor"], check=True)

        old_root = ledger.REPO_ROOT
        old_cwd = os.getcwd()
        try:
            ledger.REPO_ROOT = Path(self.repo)
            os.chdir(Path(self.repo).parent)
            ledger.verify(self.base, anchored=True)  # no injected checker
        finally:
            os.chdir(old_cwd)
            ledger.REPO_ROOT = old_root


class WindowTests(unittest.TestCase):
    def test_split_partitions_at_in_sample_end(self):
        dates = ["2021-06-01", "2022-12-31", "2023-01-01", "2024-05-05"]
        is_idx, oos_idx = windows.split_is_oos(dates, "2022-12-31")
        self.assertEqual(is_idx, [0, 1])   # <= 2022-12-31 is in-sample
        self.assertEqual(oos_idx, [2, 3])  # strictly after is out-of-sample

    def test_assert_oos_only_raises_on_in_sample_leak(self):
        with self.assertRaises(ValueError):
            windows.assert_oos_only(["2023-02-01", "2022-11-01"], "2022-12-31")

    def test_assert_oos_only_accepts_pure_oos(self):
        windows.assert_oos_only(["2023-02-01", "2024-01-01"], "2022-12-31")  # no raise

    def test_assert_within_window_accepts_registered_range(self):
        windows.assert_within_window(
            ["2023-01-01", "2024-12-31"],
            {"start": "2023-01-01", "end": "2024-12-31"},
        )

    def test_assert_within_window_rejects_before_start(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                ["2022-12-31", "2023-01-02"],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_assert_within_window_rejects_after_end(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                ["2024-12-31", "2025-01-01"],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_assert_within_window_rejects_invalid_date_type(self):
        with self.assertRaises(ValueError):
            windows.assert_within_window(
                [123],
                {"start": "2023-01-01", "end": "2024-12-31"},
            )

    def test_split_rejects_invalid_date_type(self):
        with self.assertRaises(ValueError):
            windows.split_is_oos([object()], "2022-12-31")


def _window():
    return {"start": "2018-01-01", "end": "2024-12-31",
            "is_window": {"start": "2018-01-01", "end": "2022-12-31"},
            "oos_window": {"start": "2023-01-01", "end": "2024-12-31"},
            "universe": ["SPY"]}


class RegisterCounterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True  # simulate a committed-clean source surface

    def tearDown(self):
        self._tmp.cleanup()

    def test_register_writes_run_record_with_null_oos(self):
        experiments.register("H1", "expectancy CI lower bound > 0",
                             is_result={"verdict": "NO EDGE"},
                             data_window=_window(), risk_basis="economic_max_loss",
                             base_dir=self.base, code_sha="deadbeef",
                             source_clean_tracked=self.clean)
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["entry_type"], "run")
        self.assertEqual(rec["hypothesis_id"], "H1")
        self.assertIsNone(rec["oos_result"])
        self.assertIsNone(rec["deflated_sharpe"])
        self.assertIsNone(rec["pbo"])
        self.assertEqual(rec["source_hash"], hashing.source_hash())

    def test_counter_increments_on_register_and_trial_log_only(self):
        experiments.log_trial_intent("eyeballed a 25-delta", base_dir=self.base)
        experiments.register("H1", "t", is_result={}, data_window=_window(),
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha="deadbeef", source_clean_tracked=self.clean)
        self.assertEqual(experiments.current_trial_count(self.base), 2)

    def test_counter_is_monotonic_and_non_resettable(self):
        experiments.log_trial_intent("a", base_dir=self.base)
        experiments.log_trial_intent("b", base_dir=self.base)
        ledger.verify(self.base)
        self.assertEqual(experiments.current_trial_count(self.base), 2)

    def test_register_rejects_duplicate_hypothesis_id(self):
        experiments.register("H1", "t", is_result={}, data_window=_window(),
                             risk_basis="economic_max_loss", base_dir=self.base,
                             code_sha="deadbeef", source_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("H1", "t2", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_register_rejects_dirty_source_surface(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hdirty", "t", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=lambda paths: False)

    def test_register_rejects_unknown_risk_basis(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hbad", "t", is_result={}, data_window=_window(),
                                 risk_basis="typo", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_register_rejects_empty_identity_or_threshold(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("", "t", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("H1", "", is_result={}, data_window=_window(),
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_register_rejects_malformed_data_window(self):
        bad = dict(_window())
        del bad["oos_window"]
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hbadwindow", "t", is_result={}, data_window=bad,
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_register_sanitizes_non_finite_is_result_to_null(self):
        # A real scoreboard carries float('nan') (e.g. Sharpe on a zero-variance
        # or insufficient-sample run). json_safe must turn it into JSON null so
        # the fail-closed ledger (allow_nan=False) can store the run instead of
        # crashing -- logging the honest INSUFFICIENT result is the whole point.
        experiments.register("Hnan", "t",
                             is_result={"sharpe_per_trade": float("nan"),
                                        "expectancy_CI90": [float("nan"), float("nan")],
                                        "verdict": "INSUFFICIENT SAMPLE"},
                             data_window=_window(), risk_basis="economic_max_loss",
                             base_dir=self.base, code_sha="deadbeef",
                             source_clean_tracked=self.clean)
        ledger.verify(self.base)  # must not raise -> the record is valid JSON
        rec = ledger.read_all(self.base)[-1]
        self.assertIsNone(rec["is_result"]["sharpe_per_trade"])
        self.assertEqual(rec["is_result"]["expectancy_CI90"], [None, None])
        self.assertEqual(rec["is_result"]["verdict"], "INSUFFICIENT SAMPLE")

    def test_register_rejects_non_serializable_is_result(self):
        # A set is not JSON-serializable and json_safe passes it through unchanged.
        # The gate must surface this as OOSGateError, not a bare TypeError.
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hobj", "t", is_result={"bad": {1, 2, 3}},
                                 data_window=_window(), risk_basis="economic_max_loss",
                                 base_dir=self.base, code_sha="deadbeef",
                                 source_clean_tracked=self.clean)

    def test_register_rejects_oos_window_overlapping_in_sample(self):
        bad = dict(_window())
        bad["oos_window"] = {"start": "2022-06-01", "end": "2024-12-31"}  # starts in-sample
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hoverlap", "t", is_result={}, data_window=bad,
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_register_rejects_is_window_past_in_sample_end(self):
        bad = dict(_window())
        bad["is_window"] = {"start": "2018-01-01", "end": "2023-06-01"}  # ends after IN_SAMPLE_END
        with self.assertRaises(experiments.OOSGateError):
            experiments.register("Hlate", "t", is_result={}, data_window=bad,
                                 risk_basis="economic_max_loss", base_dir=self.base,
                                 code_sha="deadbeef", source_clean_tracked=self.clean)

    def test_source_clean_default_checker_against_real_temp_repo(self):
        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.email", "t@t.t"], check=True)
            subprocess.run(["git", "-C", repo, "config", "user.name", "t"], check=True)
            (Path(repo) / "config.py").write_text("X = 1\n")
            subprocess.run(["git", "-C", repo, "add", "config.py"], check=True)
            subprocess.run(["git", "-C", repo, "commit", "-q", "-m", "init"], check=True)
            original_root = hashing.REPO_ROOT
            try:
                hashing.REPO_ROOT = Path(repo)
                # committed + clean -> True
                self.assertTrue(experiments._source_clean_tracked_default(["config.py"]))
                # locally modified (uncommitted) -> False
                (Path(repo) / "config.py").write_text("X = 2\n")
                self.assertFalse(experiments._source_clean_tracked_default(["config.py"]))
                # untracked file -> False
                (Path(repo) / "new.py").write_text("Y = 1\n")
                self.assertFalse(experiments._source_clean_tracked_default(["new.py"]))
            finally:
                hashing.REPO_ROOT = original_root


def _oos_trades(n=1):
    # All strictly after IN_SAMPLE_END, so the partition assertion passes.
    return [{"pnl": 1.0, "capital_at_risk": 100.0,
             "entry_date": "2023-06-01", "symbol": "SPY"} for _ in range(n)]


class OOSGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name
        self.clean = lambda paths: True  # simulate committed-clean source/ledger files

    def tearDown(self):
        self._tmp.cleanup()

    def _register(self, hyp="H1"):
        experiments.register(hyp, "expectancy CI lower bound > 0", is_result={},
                             data_window=_window(), risk_basis="economic_max_loss",
                             base_dir=self.base, code_sha="deadbeef",
                             source_clean_tracked=self.clean)

    def test_reveal_refused_without_registration(self):
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_on_cost_model_drift(self):
        self._register()
        original = config.SLIPPAGE_HAIRCUT
        try:
            config.SLIPPAGE_HAIRCUT = original + 0.05
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            config.SLIPPAGE_HAIRCUT = original

    def test_reveal_refused_on_config_drift(self):
        self._register()
        original = config.A_SPREAD_WIDTH
        try:
            config.A_SPREAD_WIDTH = original + 1
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            config.A_SPREAD_WIDTH = original

    def test_reveal_refused_on_source_drift(self):
        self._register()
        original = hashing.source_hash
        try:
            hashing.source_hash = lambda: "different"
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                       scoreboard_fn=lambda t: {"verdict": "x"},
                                       git_clean_tracked=self.clean)
        finally:
            hashing.source_hash = original

    def test_reveal_is_write_once(self):
        self._register()
        experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                               scoreboard_fn=lambda t: {"verdict": "x"},
                               git_clean_tracked=self.clean)
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_when_budget_exhausted(self):
        for i in range(config.OOS_LOOK_BUDGET):
            self._register(f"H{i}")
            experiments.reveal_oos(f"H{i}", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)
        self._register("Hlast")
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("Hlast", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_on_in_sample_leak(self):
        self._register()
        leaky = lambda: [{"pnl": 1.0, "capital_at_risk": 100.0,
                          "entry_date": "2021-01-01", "symbol": "SPY"}]
        with self.assertRaises(ValueError):
            experiments.reveal_oos("H1", run_fn=leaky, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_outside_registered_oos_window(self):
        self._register()
        wrong_window = lambda: [{"pnl": 1.0, "capital_at_risk": 100.0,
                                 "entry_date": "2025-01-01", "symbol": "SPY"}]
        with self.assertRaises(ValueError):
            experiments.reveal_oos("H1", run_fn=wrong_window, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_refused_when_ledger_dirty(self):
        self._register()
        with self.assertRaises(ledger.LedgerError):
            experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=lambda paths: False)

    def test_reveal_happy_path_writes_oos_reveal_record(self):
        self._register()
        out = experiments.reveal_oos("H1", run_fn=_oos_trades, base_dir=self.base,
                                     scoreboard_fn=lambda t: {"verdict": "PASS"},
                                     git_clean_tracked=self.clean)
        self.assertEqual(out["verdict"], "PASS")
        rec = ledger.read_all(self.base)[-1]
        self.assertEqual(rec["entry_type"], "oos_reveal")
        self.assertEqual(rec["hypothesis_id"], "H1")
        ledger.verify(self.base)

    def test_reveal_rejects_oos_trade_missing_entry_date(self):
        self._register()
        no_date = lambda: [{"pnl": 1.0, "capital_at_risk": 100.0, "symbol": "SPY"}]
        with self.assertRaises(experiments.OOSGateError):
            experiments.reveal_oos("H1", run_fn=no_date, base_dir=self.base,
                                   scoreboard_fn=lambda t: {"verdict": "x"},
                                   git_clean_tracked=self.clean)

    def test_reveal_sanitizes_non_finite_oos_result(self):
        # A real OOS scoreboard can carry float('nan'); json_safe must null it so
        # the fail-closed ledger (allow_nan=False) can store the reveal.
        self._register()
        out = experiments.reveal_oos(
            "H1", run_fn=_oos_trades, base_dir=self.base,
            scoreboard_fn=lambda t: {"sharpe_per_trade": float("nan"), "verdict": "NO EDGE"},
            git_clean_tracked=self.clean)
        self.assertIsNone(out["sharpe_per_trade"])
        ledger.verify(self.base)
        rec = ledger.read_all(self.base)[-1]
        self.assertIsNone(rec["oos_result"]["sharpe_per_trade"])


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_trial_log_then_verify_returns_zero(self):
        self.assertEqual(cli.main(["trial-log", "--reason", "swept width",
                                   "--ledger", self.base]), 0)
        self.assertEqual(cli.main(["verify", "--ledger", self.base]), 0)

    def test_verify_returns_nonzero_on_tamper(self):
        cli.main(["trial-log", "--reason", "x", "--ledger", self.base])
        jsonl = Path(self.base) / "experiments.jsonl"
        jsonl.write_text(jsonl.read_text().replace("x", "HACK"))
        self.assertNotEqual(cli.main(["verify", "--ledger", self.base]), 0)

    def test_trial_log_returns_nonzero_on_tampered_ledger(self):
        # trial-log must surface a corrupted chain as a clean nonzero exit, not a
        # bare LedgerError traceback (mirrors the verify subcommand's handling).
        cli.main(["trial-log", "--reason", "x", "--ledger", self.base])
        jsonl = Path(self.base) / "experiments.jsonl"
        jsonl.write_text(jsonl.read_text().replace("x", "HACK"))
        self.assertNotEqual(cli.main(["trial-log", "--reason", "y",
                                      "--ledger", self.base]), 0)

    def test_register_subcommand_is_a_distinct_seam(self):
        calls = {}
        original = experiments.register
        try:
            def fake_register(hypothesis_id, decision_threshold, is_result, *,
                              data_window, risk_basis, notes="", base_dir="ledger"):
                calls.update({
                    "hypothesis_id": hypothesis_id,
                    "decision_threshold": decision_threshold,
                    "is_result": is_result,
                    "data_window": data_window,
                    "risk_basis": risk_basis,
                    "notes": notes,
                    "base_dir": base_dir,
                })
                return "hash"
            experiments.register = fake_register
            rc = cli.main([
                "register",
                "--hypothesis-id", "H1",
                "--decision-threshold", "ci_lo>0",
                "--is-result-json", json.dumps({"verdict": "NO EDGE"}),
                "--data-window-json", json.dumps(_window()),
                "--risk-basis", "economic_max_loss",
                "--notes", "synthetic",
                "--ledger", self.base,
            ])
        finally:
            experiments.register = original
        self.assertEqual(rc, 0)
        self.assertEqual(calls["hypothesis_id"], "H1")
        self.assertEqual(calls["base_dir"], self.base)

    def test_reveal_oos_subcommand_is_a_distinct_gate(self):
        # With no registration, the integrity gate refuses before any data path.
        self.assertNotEqual(cli.main(["reveal-oos", "--hypothesis-id", "H1",
                                      "--ledger", self.base]), 0)


if __name__ == "__main__":
    unittest.main()

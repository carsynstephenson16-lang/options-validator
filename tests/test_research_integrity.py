import os
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


if __name__ == "__main__":
    unittest.main()

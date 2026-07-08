"""tools/reveal_preflight.py must be importable and testable: every reveal
gate it predicts is exercised here against a temp ledger, so the one tool on
the OOS-reveal path is no longer untested."""
import contextlib
import io
import tempfile
import unittest

import config
from research import ledger
from tools.reveal_preflight import preflight

TEST_HASHES = {
    "config_hash": "a" * 64,
    "cost_model_hash": "b" * 64,
    "source_hash": "c" * 64,
}
_CLEAN = lambda paths: True  # noqa: E731  - simulate committed-clean ledger files


def _run_record(hyp="H1", run_id="run1", hashes=TEST_HASHES):
    return {
        "entry_type": "run",
        "timestamp": "2026-07-01T00:00:00+00:00",
        "run_id": run_id,
        "hypothesis_id": hyp,
        "decision_threshold": "expectancy CI lower bound > 0",
        "code_sha": "e" * 40,
        "config_hash": hashes["config_hash"],
        "cost_model_hash": hashes["cost_model_hash"],
        "source_hash": hashes["source_hash"],
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
    }


def _attempt_record(hyp="H1", run_id="run1", budget_used=1):
    return {
        "entry_type": "oos_attempt",
        "timestamp": "2026-07-01T00:00:00+00:00",
        "hypothesis_id": hyp,
        "run_id": run_id,
        "budget_used": budget_used,
        "budget_total": 3,
    }


def _reveal_record(hyp="H1", run_id="run1", budget_used=1):
    return {
        "entry_type": "oos_reveal",
        "timestamp": "2026-07-01T00:00:00+00:00",
        "hypothesis_id": hyp,
        "run_id": run_id,
        "oos_result": {"verdict": "x"},
        "budget_used": budget_used,
        "budget_total": 3,
    }


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


class RevealPreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_refuses_when_no_registered_run_exists(self):
        ledger.append({"entry_type": "trial_intent",
                       "timestamp": "2026-07-01T00:00:00+00:00",
                       "reason": "x"}, self.base)
        self.assertFalse(_quiet(preflight, "H9", base_dir=self.base,
                                live_hashes=TEST_HASHES,
                                ledger_clean_tracked=_CLEAN))

    def test_all_gates_pass_with_matching_hashes_and_anchored_ledger(self):
        ledger.append(_run_record(), self.base)
        self.assertTrue(_quiet(preflight, "H1", base_dir=self.base,
                               live_hashes=TEST_HASHES,
                               ledger_clean_tracked=_CLEAN))

    def test_drifted_config_hash_predicts_refusal(self):
        drifted = dict(TEST_HASHES, config_hash="f" * 64)
        ledger.append(_run_record(hashes=drifted), self.base)
        self.assertFalse(_quiet(preflight, "H1", base_dir=self.base,
                                live_hashes=TEST_HASHES,
                                ledger_clean_tracked=_CLEAN))

    def test_already_revealed_hypothesis_predicts_write_once_refusal(self):
        ledger.append(_run_record(), self.base)
        ledger.append(_attempt_record(), self.base)
        ledger.append(_reveal_record(), self.base)
        self.assertFalse(_quiet(preflight, "H1", base_dir=self.base,
                                live_hashes=TEST_HASHES,
                                ledger_clean_tracked=_CLEAN))

    def test_exhausted_budget_predicts_refusal_for_new_hypothesis(self):
        ledger.append(_run_record("HN", "runN"), self.base)
        for i in range(config.OOS_LOOK_BUDGET):
            hyp = f"H{i}"
            ledger.append(_run_record(hyp, f"run{i}"), self.base)
            ledger.append(_attempt_record(hyp, f"run{i}", budget_used=i + 1),
                          self.base)
            ledger.append(_reveal_record(hyp, f"run{i}", budget_used=i + 1),
                          self.base)
        self.assertFalse(_quiet(preflight, "HN", base_dir=self.base,
                                live_hashes=TEST_HASHES,
                                ledger_clean_tracked=_CLEAN))

    def test_unanchored_ledger_predicts_refusal(self):
        ledger.append(_run_record(), self.base)
        self.assertFalse(_quiet(preflight, "H1", base_dir=self.base,
                                live_hashes=TEST_HASHES,
                                ledger_clean_tracked=lambda paths: False))

    def test_tampered_chain_raises_instead_of_passing(self):
        from pathlib import Path
        ledger.append(_run_record(), self.base)
        jsonl = Path(self.base) / "experiments.jsonl"
        jsonl.write_text(jsonl.read_text().replace('"H1"', '"H2"'))
        with self.assertRaises(Exception):
            _quiet(preflight, "H2", base_dir=self.base,
                   live_hashes=TEST_HASHES, ledger_clean_tracked=_CLEAN)


if __name__ == "__main__":
    unittest.main()

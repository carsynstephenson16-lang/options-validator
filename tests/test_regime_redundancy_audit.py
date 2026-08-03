"""tests/test_regime_redundancy_audit.py -- offline tests for the
REGIME-AMI-v1 redundancy audit (tools/regime_redundancy_audit.py).

Fully offline; no cache dependency (closes loaders and the ledger reader are
always injected). See docs/superpowers/2026-08-03-regime-ami-redundancy-
registration.md for the frozen design this tool implements.
"""
from __future__ import annotations

import json
import math
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from tools import regime_redundancy_audit as tool


def _registered_records() -> list[dict]:
    return [
        {
            "entry_type": "trial_intent",
            "hypothesis_id": "REGIME-AMI-v1",
            "reason": "REGISTRATION",
            "trial_count": 1,
            "seq": 0,
            "prev_hash": "0" * 64,
            "record_hash": "1" * 64,
        }
    ]


class AdjustedMutualInformationTests(unittest.TestCase):
    def test_identical_labelings_give_one(self):
        rng = np.random.default_rng(1)
        u = rng.integers(0, 3, size=500)
        ami, degenerate = tool.adjusted_mutual_info(u, u)
        self.assertFalse(degenerate)
        self.assertAlmostEqual(ami, 1.0, places=9)

    def test_pure_relabeling_gives_one(self):
        rng = np.random.default_rng(2)
        u = rng.integers(0, 3, size=500)
        perm = {0: 2, 1: 0, 2: 1}
        v = np.array([perm[x] for x in u])
        ami, degenerate = tool.adjusted_mutual_info(u, v)
        self.assertFalse(degenerate)
        self.assertAlmostEqual(ami, 1.0, places=9)

    def test_independent_random_labelings_near_zero(self):
        rng = np.random.default_rng(3)
        n = 3000
        u = rng.integers(0, 3, size=n)
        v = rng.integers(0, 3, size=n)
        ami, degenerate = tool.adjusted_mutual_info(u, v)
        self.assertFalse(degenerate)
        self.assertLess(abs(ami), 0.05)

    def test_single_class_degenerate(self):
        u = np.zeros(10, dtype=int)
        rng = np.random.default_rng(4)
        v = rng.integers(0, 3, size=10)
        ami, degenerate = tool.adjusted_mutual_info(u, v)
        self.assertEqual(ami, 0.0)
        self.assertTrue(degenerate)

        # Both degenerate.
        ami2, degenerate2 = tool.adjusted_mutual_info(u, np.zeros(10, dtype=int))
        self.assertEqual(ami2, 0.0)
        self.assertTrue(degenerate2)

    def test_hand_checkable_2x2_case(self):
        # Table = [[2,1],[1,2]] (a=[3,3], b=[3,3], n=6) -- computed
        # independently here (math.comb hypergeometric pmf) rather than via
        # the module's lgamma-based EMI, as a cross-check of that formula.
        u = np.array([0, 0, 0, 1, 1, 1])
        v = np.array([0, 0, 1, 0, 1, 1])
        table = np.array([[2, 1], [1, 2]])
        n = 6
        a = table.sum(axis=1)
        b = table.sum(axis=0)

        mi = 0.0
        for i in range(2):
            for j in range(2):
                nij = table[i, j]
                mi += (nij / n) * math.log((nij * n) / (a[i] * b[j]))

        def hyper_pmf(ai: int, bj: int, nij: int) -> float:
            return (
                math.comb(bj, nij) * math.comb(n - bj, ai - nij)
            ) / math.comb(n, ai)

        emi = 0.0
        for ai in a:
            for bj in b:
                lo = max(int(ai) + int(bj) - n, 0)
                hi = min(int(ai), int(bj))
                for nij in range(lo, hi + 1):
                    if nij == 0:
                        continue
                    emi += (
                        (nij / n)
                        * math.log((n * nij) / (ai * bj))
                        * hyper_pmf(int(ai), int(bj), nij)
                    )

        hu = -sum((ai / n) * math.log(ai / n) for ai in a)
        hv = -sum((bj / n) * math.log(bj / n) for bj in b)
        denom = 0.5 * (hu + hv) - emi
        expected_ami = (mi - emi) / denom

        got_ami, degenerate = tool.adjusted_mutual_info(u, v)
        self.assertFalse(degenerate)
        self.assertAlmostEqual(got_ami, expected_ami, places=9)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            tool.adjusted_mutual_info(np.array([0, 1]), np.array([0, 1, 2]))

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            tool.adjusted_mutual_info(np.array([]), np.array([]))


class FeatureBinningTests(unittest.TestCase):
    def test_rv_exactly_one_is_tercile_two(self):
        self.assertEqual(tool.rv_tercile(1.0), 2)

    def test_rv_boundary_one_third_is_bin_one(self):
        self.assertEqual(tool.rv_tercile(1.0 / 3.0), 1)

    def test_rv_zero_is_bin_zero(self):
        self.assertEqual(tool.rv_tercile(0.0), 0)

    def test_rv_boundary_two_thirds_is_bin_two(self):
        self.assertEqual(tool.rv_tercile(2.0 / 3.0), 2)

    def test_rv_just_under_two_thirds_is_bin_one(self):
        self.assertEqual(tool.rv_tercile(2.0 / 3.0 - 1e-9), 1)

    def test_posture_index_fixed_mapping(self):
        self.assertEqual(
            tool.POSTURE_INDEX, {"above_all": 0, "below_all": 1, "mixed": 2}
        )

    def test_feature_grid_cell_combines_tercile_and_posture(self):
        self.assertEqual(tool.feature_grid_cell(0.0, "above_all"), 0)
        self.assertEqual(tool.feature_grid_cell(0.5, "below_all"), 1 * 3 + 1)
        self.assertEqual(tool.feature_grid_cell(0.9, "mixed"), 2 * 3 + 2)

    def test_feature_grid_cell_none_for_insufficient_history(self):
        self.assertIsNone(tool.feature_grid_cell(0.5, "insufficient_history"))


class DecisionRuleTests(unittest.TestCase):
    def test_median_exactly_threshold_is_redundant(self):
        results = [
            {"status": "OK", "eligible": True, "ami": 0.50},
            {"status": "OK", "eligible": True, "ami": 0.50},
        ]
        decision, median = tool.decide(results)
        self.assertEqual(decision, "REDUNDANT")
        self.assertEqual(median, 0.50)

    def test_median_below_threshold_retains_distinct(self):
        results = [
            {"status": "OK", "eligible": True, "ami": 0.40},
            {"status": "OK", "eligible": True, "ami": 0.45},
        ]
        decision, median = tool.decide(results)
        self.assertEqual(decision, "RETAINS_DISTINCT_INFORMATION")
        self.assertAlmostEqual(median, 0.425)

    def test_fewer_than_two_eligible_is_insufficient_data(self):
        results = [
            {"status": "OK", "eligible": True, "ami": 0.90},
            {"status": "OK", "eligible": False, "ami": 0.10},
            {"status": "DATA_MISSING", "eligible": False, "ami": None},
        ]
        decision, median = tool.decide(results)
        self.assertEqual(decision, "INSUFFICIENT_DATA")
        self.assertIsNone(median)

    def test_zero_eligible_is_insufficient_data(self):
        results = [
            {"status": "DATA_MISSING", "eligible": False, "ami": None},
            {"status": "DATA_MISSING", "eligible": False, "ami": None},
        ]
        decision, median = tool.decide(results)
        self.assertEqual(decision, "INSUFFICIENT_DATA")
        self.assertIsNone(median)

    def test_ineligible_symbol_excluded_even_with_ami_present(self):
        # An eligible-False row must never leak into the median even if it
        # somehow carries a non-null ami.
        results = [
            {"status": "OK", "eligible": True, "ami": 0.10},
            {"status": "OK", "eligible": True, "ami": 0.20},
            {"status": "OK", "eligible": False, "ami": 0.99},
        ]
        decision, median = tool.decide(results)
        self.assertEqual(decision, "RETAINS_DISTINCT_INFORMATION")
        self.assertAlmostEqual(median, 0.15)


class RegistrationGateTests(unittest.TestCase):
    def test_check_registration_false_when_absent(self):
        self.assertFalse(tool.check_registration([]))
        self.assertFalse(
            tool.check_registration([{"entry_type": "trial_intent",
                                      "hypothesis_id": "SOMETHING-ELSE"}])
        )

    def test_check_registration_true_when_present(self):
        self.assertTrue(tool.check_registration(_registered_records()))

    def test_require_registration_raises_when_absent(self):
        with self.assertRaises(tool.RegistrationGateError):
            tool.require_registration([])

    def test_require_registration_passes_when_present(self):
        tool.require_registration(_registered_records())  # must not raise

    def test_run_audit_refuses_without_registration(self):
        def _never_called_loader(symbol, start_iso, end_iso, *, allow_oos=False):
            raise AssertionError("loader must not be called before the gate")

        with self.assertRaises(tool.RegistrationGateError):
            tool.run_audit(loader=_never_called_loader, ledger_reader=lambda: [])


def _synthetic_closes(n: int, seed: int, start_price: float = 100.0) -> pd.Series:
    """Varying-volatility synthetic close series, ISO-string-indexed
    ascending (mirrors data.underlying_closes.load_closes_adjusted output),
    long enough for the frozen window=63/step=5/min_fit_windows=24 config to
    label >=100 steps with valid (non-insufficient-history) posture."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    vol = 0.006 + 0.006 * (np.sin(t / 37.0) ** 2)
    returns = rng.normal(0.0, 1.0, size=n) * vol
    closes = start_price * np.exp(np.cumsum(returns))
    dates = pd.bdate_range(start="2015-01-02", periods=n).strftime("%Y-%m-%d")
    return pd.Series(closes, index=pd.Index(dates, name="date"), dtype=float)


class EndToEndAuditTests(unittest.TestCase):
    def test_two_symbol_synthetic_run_writes_receipt(self):
        series = {
            "AAA": _synthetic_closes(780, seed=11),
            "BBB": _synthetic_closes(780, seed=22),
        }

        def _loader(symbol, start_iso, end_iso, *, allow_oos=False):
            return series[symbol]

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp)
            started = time.monotonic()
            outcome = tool.run_audit(
                loader=_loader,
                ledger_reader=_registered_records,
                out_dir=out_dir,
                symbols=["AAA", "BBB"],
                today_iso="2099-01-01",
            )
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 60.0, "audit run took too long for a unit test")

            self.assertIn(
                outcome["decision"],
                {"REDUNDANT", "RETAINS_DISTINCT_INFORMATION"},
            )
            self.assertEqual(outcome["exit_code"], 0)

            results_by_symbol = {r["symbol"]: r for r in outcome["results"]}
            for sym in ("AAA", "BBB"):
                r = results_by_symbol[sym]
                self.assertEqual(r["status"], "OK")
                self.assertGreaterEqual(r["n_included"], 100)
                self.assertTrue(r["eligible"])
                self.assertIsNotNone(r["as_of"])
                self.assertIsNotNone(r["ami"])

            json_path = out_dir / tool.RECEIPT_JSON_NAME
            md_path = out_dir / tool.RECEIPT_MD_NAME
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            payload = json.loads(json_path.read_text())
            self.assertEqual(payload["decision"], outcome["decision"])
            self.assertEqual(payload["hypothesis_id"], "REGIME-AMI-v1")
            self.assertTrue(payload["ledger_record_present"])
            for entry in payload["symbols"]:
                if entry["status"] == "OK":
                    self.assertIsNotNone(entry["as_of"])
            self.assertIn(tool.DISCLAIMER, payload["disclaimer"])

    def test_data_missing_symbol_marked_not_eligible(self):
        def _loader(symbol, start_iso, end_iso, *, allow_oos=False):
            raise FileNotFoundError(symbol)

        with tempfile.TemporaryDirectory() as tmp:
            outcome = tool.run_audit(
                loader=_loader,
                ledger_reader=_registered_records,
                out_dir=Path(tmp),
                symbols=["ZZZ"],
                today_iso="2099-01-01",
            )
        self.assertEqual(outcome["decision"], "INSUFFICIENT_DATA")
        self.assertEqual(outcome["exit_code"], 1)
        r = outcome["results"][0]
        self.assertEqual(r["status"], "DATA_MISSING")
        self.assertFalse(r["eligible"])
        self.assertIsNone(r["ami"])


if __name__ == "__main__":
    unittest.main()

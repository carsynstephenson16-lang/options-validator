"""7b-2 C3: non-trial diagnostic ledger records. Attempts bind every
verdict-affecting hash BEFORE execution; results are write-once and bind
exactly one attempt; the project trial count provably never moves; the OOS
reveal path refuses diagnostics."""

import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

from research import diagnostics, experiments, hashing, ledger

WINDOW = {"start": "2018-01-02", "end": "2026-06-30"}
MANIFEST = "c" * 64


def _seed_h7_registration(base):
    """A tmp ledger with one H7 trial_intent (the registration to bind)."""
    ledger.append({
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H7",
        "reason": "synthetic H7 registration for diagnostic tests",
    }, base_dir=base)


def _attempt(base, diagnostic_id="H7a-diag-1", lane="a"):
    return diagnostics.record_diagnostic_attempt(
        diagnostic_id=diagnostic_id, lane=lane, symbols=["NVDA", "SMCI"],
        window=WINDOW, estimand="isolated-lane non-blind diagnostic (v1.2(6))",
        data_manifest_hash=MANIFEST, base_dir=base)


class TestDiagnosticRecords(unittest.TestCase):
    def test_attempt_then_result_verifies_and_trial_count_frozen(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            before = ledger.current_trial_count(base)
            attempt_hash = _attempt(base)
            diagnostics.record_diagnostic_result(
                diagnostic_id="H7a-diag-1",
                result={"trades": 0, "note": "synthetic"}, base_dir=base)
            ledger.verify(base)                      # chain + semantics hold
            after = ledger.current_trial_count(base)
            self.assertEqual(before, after)          # NON-trial: count frozen
            recs = ledger.read_all(base)
            self.assertEqual(recs[-1]["attempt_hash"], attempt_hash)
            self.assertEqual(recs[-1]["trial_count"], before)

    def test_attempt_binds_v2_source_surface(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            rec = ledger.read_all(base)[-1]
            self.assertEqual(rec["source_hash_version"], 2)
            self.assertEqual(rec["source_hash_v2"],
                             hashing.diagnostic_source_hash())
            # v2 covers options_researcher/ (the NO-GO gap) and tools/
            snap = hashing.source_snapshot(
                paths=hashing.DIAGNOSTIC_SOURCE_PATHS_V2)
            self.assertTrue(any(p.startswith("options_researcher/")
                                for p in snap))
            self.assertTrue(any(p.startswith("tools/") for p in snap))
            # the legacy contract is untouched (historical entries verify)
            legacy = hashing.source_snapshot()
            self.assertFalse(any(p.startswith("options_researcher/")
                                 for p in legacy))

    def test_duplicate_result_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            diagnostics.record_diagnostic_result(
                diagnostic_id="H7a-diag-1", result={"trades": 0},
                base_dir=base)
            with self.assertRaises(ledger.LedgerError):
                diagnostics.record_diagnostic_result(
                    diagnostic_id="H7a-diag-1", result={"trades": 1},
                    base_dir=base)

    def test_result_without_attempt_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.record_diagnostic_result(
                    diagnostic_id="never-attempted", result={},
                    base_dir=base)

    def test_result_with_wrong_attempt_hash_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            with self.assertRaises(ledger.LedgerError):
                ledger.append({
                    "entry_type": "diagnostic_result",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "diagnostic_id": "H7a-diag-1",
                    "attempt_hash": "d" * 64,     # not the attempt's hash
                    "result": {},
                }, base_dir=base)

    def test_duplicate_attempt_id_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            with self.assertRaises(ledger.LedgerError):
                _attempt(base)

    def test_unknown_field_rejected(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            with self.assertRaises(ledger.LedgerError):
                ledger.append({
                    "entry_type": "diagnostic_attempt",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "diagnostic_id": "x", "hypothesis_id": "H7",
                    "lane": "a", "scope": {"symbols": ["NVDA"]},
                    "window": WINDOW, "estimand": "e",
                    "code_sha": "e" * 40, "config_hash": "a" * 64,
                    "cost_model_hash": "a" * 64, "source_hash_v2": "a" * 64,
                    "source_hash_version": 2, "data_manifest_hash": "a" * 64,
                    "registration_hashes": ["a" * 64],
                    "smuggled_state": True,
                }, base_dir=base)

    def test_reveal_path_refuses_diagnostics(self):
        # a diagnostic attempt+result never enables the OOS reveal machinery:
        # no `run` registration exists, so reveal refuses outright
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            diagnostics.record_diagnostic_result(
                diagnostic_id="H7a-diag-1", result={"trades": 0},
                base_dir=base)
            with self.assertRaises(experiments.OOSGateError):
                experiments.reveal_oos(
                    "H7", run_fn=lambda: [], base_dir=base)

    def test_stale_attempt_blocks_execution(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            diagnostics.verify_attempt_current("H7a-diag-1", base_dir=base)
            with mock.patch.object(diagnostics, "diagnostic_source_hash",
                                   lambda: "f" * 64):
                with self.assertRaises(diagnostics.DiagnosticError):
                    diagnostics.verify_attempt_current(
                        "H7a-diag-1", base_dir=base)

    def test_real_ledger_still_verifies(self):
        ledger.verify("ledger")

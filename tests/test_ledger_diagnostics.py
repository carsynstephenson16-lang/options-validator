"""7b-2 C3: non-trial diagnostic ledger records. Attempts bind every
verdict-affecting hash BEFORE execution; results are write-once and bind
exactly one attempt; the project trial count provably never moves; the OOS
reveal path refuses diagnostics."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from research import diagnostics, experiments, hashing, ledger

WINDOW = {"start": "2018-01-02", "end": "2026-06-30"}
MANIFEST = "c" * 64
RECEIPT_HASH = "b" * 64
OK_RECEIPT = {"verdict": "PASS", "receipt_hash": RECEIPT_HASH,
              "manifest_hash": MANIFEST}


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
        data_manifest_hash=MANIFEST, receipt_hash=RECEIPT_HASH,
        base_dir=base)


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
                    "receipt_hash": "a" * 64,
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
            diagnostics.verify_attempt_current("H7a-diag-1", base_dir=base,
                                               receipt=OK_RECEIPT)
            with mock.patch.object(diagnostics, "diagnostic_source_hash",
                                   lambda: "f" * 64):
                with self.assertRaises(diagnostics.DiagnosticError):
                    diagnostics.verify_attempt_current(
                        "H7a-diag-1", base_dir=base, receipt=OK_RECEIPT)

    def test_launch_gate_refuses_non_pass_receipt(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            bad = dict(OK_RECEIPT, verdict="BLOCK")
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.verify_attempt_current("H7a-diag-1",
                                                   base_dir=base, receipt=bad)

    def test_launch_gate_refuses_receipt_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            other = dict(OK_RECEIPT, receipt_hash="e" * 64)
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.verify_attempt_current(
                    "H7a-diag-1", base_dir=base, receipt=other)

    def test_launch_gate_refuses_manifest_mismatch(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            other = dict(OK_RECEIPT, manifest_hash="e" * 64)
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.verify_attempt_current(
                    "H7a-diag-1", base_dir=base, receipt=other)

    def test_launch_gate_refuses_unsupported_source_version(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            with mock.patch.object(diagnostics,
                                   "DIAGNOSTIC_SOURCE_HASH_VERSION", 3):
                with self.assertRaises(diagnostics.DiagnosticError):
                    diagnostics.verify_attempt_current(
                        "H7a-diag-1", base_dir=base, receipt=OK_RECEIPT)

    def test_launch_gate_refuses_changed_registration_set(self):
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            _attempt(base)
            _seed_h7_registration(base)   # a NEW H7 registration afterwards
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.verify_attempt_current(
                    "H7a-diag-1", base_dir=base, receipt=OK_RECEIPT)

    def test_real_ledger_still_verifies(self):
        ledger.verify("ledger")


class TestH7RetirementTombstone(unittest.TestCase):
    """7b-2R.2: once H7_AMENDMENT_V1_3 exists in a ledger, the historical
    H7 diagnostic machinery refuses PERMANENTLY -- before reading any
    market data. Synthetic ledgers (which cannot contain the frozen hash)
    keep the machinery testable; the REAL ledger contains it."""

    def test_real_ledger_is_retired(self):
        with self.assertRaises(diagnostics.DiagnosticError) as ctx:
            diagnostics.require_h7_diagnostic_not_retired("ledger")
        self.assertIn("PERMANENTLY WITHDRAWN", str(ctx.exception))

    def test_attempt_recording_refuses_on_a_retired_ledger(self):
        # copy the REAL ledger into a tmp dir: refusal must fire BEFORE any
        # append, so nothing can ever be written to the real chain
        import shutil
        with tempfile.TemporaryDirectory() as base:
            for name in ("experiments.jsonl", "HEAD"):
                shutil.copy(f"ledger/{name}", f"{base}/{name}")
            experiments_path = Path(base) / "experiments.jsonl"
            before = experiments_path.read_text()
            with self.assertRaises(diagnostics.DiagnosticError):
                _attempt(base)
            self.assertEqual(experiments_path.read_text(), before)

    def test_authorize_oos_run_refuses_first_on_a_retired_ledger(self):
        import shutil
        with tempfile.TemporaryDirectory() as base:
            for name in ("experiments.jsonl", "HEAD"):
                shutil.copy(f"ledger/{name}", f"{base}/{name}")
            with self.assertRaises(diagnostics.DiagnosticError) as ctx:
                diagnostics.authorize_oos_run(
                    "any-id", lane="a",
                    window={"start": "2018-01-02", "end": "2026-06-30"},
                    symbols=["NVDA"], manifest={}, base_dir=base)
        self.assertIn("PERMANENTLY WITHDRAWN", str(ctx.exception))

    def test_retirement_detected_via_frozen_config_hash(self):
        # a synthetic ledger record whose hash is patched into the frozen
        # constant triggers the tombstone -- proving detection is BY HASH
        import config as cfg
        with tempfile.TemporaryDirectory() as base:
            _seed_h7_registration(base)
            rec_hash = ledger.read_all(base)[-1]["record_hash"]
            with mock.patch.object(cfg, "H7_HISTORICAL_WITHDRAWAL_HASH",
                                   rec_hash):
                with self.assertRaises(diagnostics.DiagnosticError):
                    diagnostics.require_h7_diagnostic_not_retired(base)
                with self.assertRaises(diagnostics.DiagnosticError):
                    _attempt(base)
            # unpatched, the same synthetic ledger still works
            diagnostics.require_h7_diagnostic_not_retired(base)
            _attempt(base)

    def test_frozen_hash_matches_the_committed_amendment(self):
        import config as cfg
        recs = [r for r in ledger.read_all("ledger")
                if r.get("record_hash") == cfg.H7_HISTORICAL_WITHDRAWAL_HASH]
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["entry_type"], "trial_intent")
        self.assertEqual(recs[0]["hypothesis_id"], "H7")
        self.assertIn("H7_AMENDMENT_V1_3", recs[0]["reason"])
        self.assertIn("WITHDRAWN", recs[0]["reason"])

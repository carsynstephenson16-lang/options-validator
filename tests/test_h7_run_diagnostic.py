"""7b-2R finding 7: ONE mechanically gated launch command. No public
allow_oos, invocation defined by the committed attempt, receipt-bound
inputs, ledger-before-print, trial count provably frozen."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from research import diagnostics, ledger
from research.hashing import canonical_json, sha256_hex
from tools import h7_run_diagnostic as gated

WINDOW = {"start": "2018-01-02", "end": "2026-06-30"}
FAKE_MANIFEST = {"NVDA": {"eligible": ["2022-06-06"], "excluded": {}}}
MANIFEST_HASH = sha256_hex(canonical_json(FAKE_MANIFEST))


def seed(base, receipt_hash):
    ledger.append({
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H7",
        "reason": "synthetic H7 registration",
    }, base_dir=base)
    return diagnostics.record_diagnostic_attempt(
        diagnostic_id="H7a-diag-1", lane="a", symbols=["NVDA"],
        window=WINDOW, estimand="isolated-lane non-blind diagnostic",
        data_manifest_hash=MANIFEST_HASH, receipt_hash=receipt_hash,
        base_dir=base)


def fake_run_lane(lane, start, end, *, symbols, manifest, capability):
    from datetime import date, timedelta
    assert capability is not None
    monday = date(2022, 1, 3)
    return {"lane": lane,
            "trades": [{"pnl": -100.0, "capital_at_risk": 1000.0,
                        "economic_max_loss": 1000.0,
                        "entry_date": (monday + timedelta(weeks=i)).isoformat(),
                        "symbol": "NVDA"} for i in range(30)],
            "cancelled": [], "quarantined": [], "gaps": [],
            "coverage": {"NVDA": {"eligible": 1, "evaluated": 1,
                                  "unaccounted": []}}}


class TestGatedLaunch(unittest.TestCase):
    def _receipt_file(self, tmp, verdict="PASS"):
        receipt = {"verdict": verdict, "manifest_hash": MANIFEST_HASH,
                   "audit_version": "h7-data-audit/2"}
        receipt["receipt_hash"] = sha256_hex(canonical_json(receipt))
        p = Path(tmp) / "receipt_v2.json"
        p.write_text(json.dumps(receipt))
        return p, receipt["receipt_hash"]

    def _run(self, base, tmp, receipt_path, results_dir=None,
             run_lane=fake_run_lane, record_result=None):
        from contextlib import ExitStack

        from tools import h7_data_audit
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                h7_data_audit, "RECEIPT_PATH", receipt_path))
            stack.enter_context(mock.patch.object(
                h7_data_audit, "verify_receipt", lambda: (True, [])))
            stack.enter_context(mock.patch(
                "harness.run_h7_backtest.run_lane", run_lane))
            stack.enter_context(mock.patch(
                "data.h7_manifest.eligible_manifest",
                lambda **kw: FAKE_MANIFEST))
            stack.enter_context(mock.patch.object(
                gated, "RESULTS_DIR", Path(results_dir or tmp) / "results"))
            if record_result is not None:
                stack.enter_context(mock.patch.object(
                    gated, "_record_result", record_result))
            return gated.run_gated_diagnostic("H7a-diag-1", base_dir=base)

    def test_happy_path_ledgers_before_artifact_and_freezes_trial_count(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            receipt_path, receipt_hash = self._receipt_file(tmp)
            seed(base, receipt_hash)
            before = ledger.current_trial_count(base)
            out = self._run(base, tmp, receipt_path)
            self.assertEqual(out["adjudication"]["verdict"], "REJECTED")
            self.assertEqual(ledger.current_trial_count(base), before)
            recs = ledger.read_all(base)
            self.assertEqual(recs[-1]["entry_type"], "diagnostic_result")
            self.assertEqual(recs[-1]["result"]["adjudication"]["verdict"],
                             "REJECTED")
            self.assertTrue(Path(out["artifact"]).exists())

    def test_refuses_second_run_under_same_id(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            receipt_path, receipt_hash = self._receipt_file(tmp)
            seed(base, receipt_hash)
            self._run(base, tmp, receipt_path)
            with self.assertRaises(diagnostics.DiagnosticError):
                self._run(base, tmp, receipt_path)

    def test_refuses_non_pass_receipt(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            receipt_path, receipt_hash = self._receipt_file(tmp,
                                                            verdict="BLOCK")
            seed(base, receipt_hash)
            with self.assertRaises(diagnostics.DiagnosticError):
                self._run(base, tmp, receipt_path)

    def test_refuses_manifest_drift(self):
        # the receipt binds a DIFFERENT manifest hash than the recomputed one
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            receipt = {"verdict": "PASS", "manifest_hash": "e" * 64,
                       "audit_version": "h7-data-audit/2"}
            receipt["receipt_hash"] = sha256_hex(canonical_json(receipt))
            receipt_path = Path(tmp) / "receipt_v2.json"
            receipt_path.write_text(json.dumps(receipt))
            seed(base, receipt["receipt_hash"])
            with self.assertRaises(diagnostics.DiagnosticError):
                self._run(base, tmp, receipt_path)

    def test_refuses_unanchored_ledger(self):
        with mock.patch.object(gated.subprocess, "run") as run:
            run.return_value = mock.Mock(stdout=" M ledger/experiments.jsonl\n")
            with mock.patch.object(gated.ledger, "verify", lambda base_dir: None):
                with self.assertRaises(diagnostics.DiagnosticError):
                    gated._require_anchored_ledger("ledger")

    def test_no_artifact_when_ledger_write_fails(self):
        # ORDERING PROOF: if the write-once ledger append fails, nothing is
        # printed or exported -- a result can never exist outside the ledger
        def boom(diagnostic_id, result_body, base_dir):
            raise ledger.LedgerError("synthetic failure")

        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            receipt_path, receipt_hash = self._receipt_file(tmp)
            seed(base, receipt_hash)
            with self.assertRaises(ledger.LedgerError):
                self._run(base, tmp, receipt_path, record_result=boom)
            self.assertFalse((Path(tmp) / "results").exists())

    def test_run_lane_has_no_public_allow_oos(self):
        import inspect

        from harness.run_h7_backtest import run_lane
        self.assertNotIn("allow_oos",
                         inspect.signature(run_lane).parameters)

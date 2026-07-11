"""7b-2R finding 7 + 7b-2R.1 finding A: ONE mechanically gated launch
command, and the OOS gate lives INSIDE run_lane's execution boundary.
There is no freely constructible authorization object; invocation is
defined by the committed attempt, inputs are receipt-bound, results are
ledgered before print, and the trial count is provably frozen."""

import functools
import inspect
import json
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from harness import run_h7_backtest as run_h7
from research import diagnostics, ledger
from research.hashing import canonical_json, sha256_hex
from tools import h7_run_diagnostic as gated

WINDOW = {"start": "2018-01-02", "end": "2026-06-30"}
FAKE_MANIFEST = {"NVDA": {"eligible": ["2022-06-06"], "excluded": {}}}
MANIFEST_HASH = sha256_hex(canonical_json(FAKE_MANIFEST))
EMPTY_CHUNK = {"trades": [], "cancelled": [], "quarantined": [],
               "month_risk": {}, "gaps": [],
               "coverage": {"eligible": 0, "evaluated": 0,
                            "unaccounted": []}}


def seed_registration(base):
    ledger.append({
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H7",
        "reason": "synthetic H7 registration",
    }, base_dir=base)


def seed(base, receipt_hash="b" * 64):
    seed_registration(base)
    return diagnostics.record_diagnostic_attempt(
        diagnostic_id="H7a-diag-1", lane="a", symbols=["NVDA"],
        window=WINDOW, estimand="isolated-lane non-blind diagnostic",
        data_manifest_hash=MANIFEST_HASH, receipt_hash=receipt_hash,
        base_dir=base)


def receipt_file(tmp, verdict="PASS", manifest_hash=MANIFEST_HASH):
    receipt = {"verdict": verdict, "manifest_hash": manifest_hash,
               "audit_version": "h7-data-audit/2"}
    receipt["receipt_hash"] = sha256_hex(canonical_json(receipt))
    p = Path(tmp) / "receipt_v2.json"
    p.write_text(json.dumps(receipt))
    return p, receipt["receipt_hash"]


def fake_run_lane(lane, start, end, *, symbols, diagnostic_id):
    from datetime import date, timedelta
    assert diagnostic_id
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
    def _run(self, base, tmp, run_lane=fake_run_lane, record_result=None,
             diagnostic_id="H7a-diag-1"):
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                diagnostics, "_ledger_git_status", lambda base_dir: ""))
            stack.enter_context(mock.patch(
                "harness.run_h7_backtest.run_lane", run_lane))
            stack.enter_context(mock.patch.object(
                gated, "RESULTS_DIR", Path(tmp) / "results"))
            if record_result is not None:
                stack.enter_context(mock.patch.object(
                    gated, "_record_result", record_result))
            return gated.run_gated_diagnostic(diagnostic_id, base_dir=base)

    def test_happy_path_ledgers_before_artifact_and_freezes_trial_count(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            seed(base)
            before = ledger.current_trial_count(base)
            out = self._run(base, tmp)
            self.assertEqual(out["adjudication"]["verdict"], "REJECTED")
            self.assertEqual(ledger.current_trial_count(base), before)
            recs = ledger.read_all(base)
            self.assertEqual(recs[-1]["entry_type"], "diagnostic_result")
            self.assertEqual(recs[-1]["result"]["adjudication"]["verdict"],
                             "REJECTED")
            self.assertTrue(Path(out["artifact"]).exists())

    def test_invocation_comes_from_the_ledgered_attempt(self):
        # nothing but the id is taken from the caller; the runner receives
        # the attempt's lane/window/symbols plus the id it self-authorizes on
        calls = {}

        def spy(lane, start, end, *, symbols, diagnostic_id):
            calls.update(lane=lane, start=start, end=end, symbols=symbols,
                         diagnostic_id=diagnostic_id)
            return fake_run_lane(lane, start, end, symbols=symbols,
                                 diagnostic_id=diagnostic_id)

        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            seed(base)
            self._run(base, tmp, run_lane=spy)
        self.assertEqual(calls["diagnostic_id"], "H7a-diag-1")
        self.assertEqual(calls["lane"], "a")
        self.assertEqual(calls["start"], WINDOW["start"])
        self.assertEqual(calls["end"], WINDOW["end"])
        self.assertEqual(calls["symbols"], ["NVDA"])

    def test_refuses_missing_attempt(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            seed_registration(base)      # valid ledger, NO attempt
            with self.assertRaises(diagnostics.DiagnosticError):
                self._run(base, tmp)

    def test_refuses_second_run_under_same_id(self):
        # write-once: the boundary gate refuses a rerun outright; with the
        # runner mocked here, the ledger's own write-once append refuses
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            seed(base)
            self._run(base, tmp)
            with self.assertRaises(
                    (diagnostics.DiagnosticError, ledger.LedgerError)):
                self._run(base, tmp)

    def test_refuses_unanchored_ledger(self):
        with mock.patch.object(diagnostics, "_ledger_git_status",
                               lambda base_dir: " M ledger/experiments.jsonl"), \
             mock.patch.object(diagnostics.ledger, "verify",
                               lambda base_dir: None):
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.require_anchored_ledger("ledger")

    def test_no_artifact_when_ledger_write_fails(self):
        # ORDERING PROOF: if the write-once ledger append fails, nothing is
        # printed or exported -- a result can never exist outside the ledger
        def boom(diagnostic_id, result_body, base_dir):
            raise ledger.LedgerError("synthetic failure")

        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp:
            seed(base)
            with self.assertRaises(ledger.LedgerError):
                self._run(base, tmp, record_result=boom)
            self.assertFalse((Path(tmp) / "results").exists())


class TestRunLaneBoundary(unittest.TestCase):
    """7b-2R.1 finding A adversarial tests: verification is INSIDE
    run_lane. Any OOS window without a fully verified diagnostic id is
    refused BEFORE any loader touches chains or closes."""

    def _loader_spies(self, stack):
        chain_calls, closes_calls = [], []

        def spy_chains(*a, **k):
            chain_calls.append(a)
            return {}

        def spy_closes(*a, **k):
            closes_calls.append(k)
            return (None, None)

        stack.enter_context(mock.patch(
            "data.pandas_feed.load_cached_chains", spy_chains))
        stack.enter_context(mock.patch.object(
            run_h7, "_load_closes", spy_closes))
        return chain_calls, closes_calls

    def _redirect_ledger(self, stack, base):
        # point the REAL authorize_oos_run at the tmp ledger (no logic is
        # mocked away) and neutralize the git-porcelain check for tmp dirs
        real = diagnostics.authorize_oos_run
        stack.enter_context(mock.patch.object(
            diagnostics, "authorize_oos_run",
            functools.partial(real, base_dir=base)))
        stack.enter_context(mock.patch.object(
            diagnostics, "_ledger_git_status", lambda base_dir: ""))

    def _bind_receipt(self, stack, receipt_path):
        from tools import h7_data_audit
        stack.enter_context(mock.patch.object(
            h7_data_audit, "RECEIPT_PATH", receipt_path))
        stack.enter_context(mock.patch.object(
            h7_data_audit, "verify_receipt", lambda: (True, [])))

    def test_oos_window_without_id_never_touches_loaders(self):
        with ExitStack() as stack:
            chains, closes = self._loader_spies(stack)
            with self.assertRaises(diagnostics.DiagnosticError) as ctx:
                run_h7.run_lane("a", "2018-01-02", "2026-06-30",
                                symbols=["NVDA"], assertions=[],
                                manifest=FAKE_MANIFEST)
            self.assertIn("diagnostic id", str(ctx.exception))
            self.assertEqual(chains, [])
            self.assertEqual(closes, [])

    def test_oos_window_with_bogus_id_refused_before_loaders(self):
        with tempfile.TemporaryDirectory() as base, ExitStack() as stack:
            seed_registration(base)      # valid tmp ledger, NO attempt
            self._redirect_ledger(stack, base)
            chains, closes = self._loader_spies(stack)
            with self.assertRaises(diagnostics.DiagnosticError) as ctx:
                run_h7.run_lane("a", "2018-01-02", "2026-06-30",
                                symbols=["NVDA"], assertions=[],
                                manifest=FAKE_MANIFEST,
                                diagnostic_id="not-a-real-attempt")
            self.assertIn("no diagnostic_attempt", str(ctx.exception))
            self.assertEqual(chains, [])
            self.assertEqual(closes, [])

    def test_oos_non_pass_receipt_refused_before_loaders(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            receipt_path, receipt_hash = receipt_file(tmp, verdict="BLOCK")
            seed(base, receipt_hash)
            self._redirect_ledger(stack, base)
            self._bind_receipt(stack, receipt_path)
            chains, closes = self._loader_spies(stack)
            with self.assertRaises(diagnostics.DiagnosticError):
                run_h7.run_lane("a", WINDOW["start"], WINDOW["end"],
                                symbols=["NVDA"], assertions=[],
                                manifest=FAKE_MANIFEST,
                                diagnostic_id="H7a-diag-1")
            self.assertEqual(chains, [])
            self.assertEqual(closes, [])

    def test_oos_manifest_drift_refused_before_loaders(self):
        # a runner manifest that is not EXACTLY the audited one is refused
        drifted = {"NVDA": {"eligible": ["2022-06-07"], "excluded": {}}}
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            receipt_path, receipt_hash = receipt_file(tmp)
            seed(base, receipt_hash)
            self._redirect_ledger(stack, base)
            self._bind_receipt(stack, receipt_path)
            chains, closes = self._loader_spies(stack)
            with self.assertRaises(diagnostics.DiagnosticError) as ctx:
                run_h7.run_lane("a", WINDOW["start"], WINDOW["end"],
                                symbols=["NVDA"], assertions=[],
                                manifest=drifted,
                                diagnostic_id="H7a-diag-1")
            self.assertIn("data_manifest_hash", str(ctx.exception))
            self.assertEqual(chains, [])
            self.assertEqual(closes, [])

    def test_oos_lane_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            receipt_path, receipt_hash = receipt_file(tmp)
            seed(base, receipt_hash)     # the attempt authorizes lane "a"
            self._redirect_ledger(stack, base)
            self._bind_receipt(stack, receipt_path)
            chains, closes = self._loader_spies(stack)
            with self.assertRaises(diagnostics.DiagnosticError) as ctx:
                run_h7.run_lane("b", WINDOW["start"], WINDOW["end"],
                                symbols=["NVDA"], assertions=[],
                                manifest=FAKE_MANIFEST,
                                diagnostic_id="H7a-diag-1")
            self.assertIn("authorizes lane", str(ctx.exception))
            self.assertEqual(chains, [])
            self.assertEqual(closes, [])

    def test_verified_attempt_opens_oos_with_allow_oos_true(self):
        # positive control: the fully verified id opens the window and the
        # loaders/chunks all run with allow_oos=True
        with tempfile.TemporaryDirectory() as base, \
             tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            receipt_path, receipt_hash = receipt_file(tmp)
            seed(base, receipt_hash)
            self._redirect_ledger(stack, base)
            self._bind_receipt(stack, receipt_path)
            closes_flags, chunk_flags = [], []
            stack.enter_context(mock.patch.object(
                run_h7, "_load_closes",
                lambda sym, s, e, allow_oos:
                closes_flags.append(allow_oos) or (None, None)))

            def fake_chunk(lane, symbol, sim_start, cutoff, sim_end,
                           blocked_until, *, allow_oos, **kw):
                chunk_flags.append(allow_oos)
                return dict(EMPTY_CHUNK)

            stack.enter_context(mock.patch.object(
                run_h7, "_run_chunk", fake_chunk))
            out = run_h7.run_lane("a", WINDOW["start"], WINDOW["end"],
                                  symbols=["NVDA"], assertions=[],
                                  manifest=FAKE_MANIFEST,
                                  diagnostic_id="H7a-diag-1")
        self.assertEqual(out["lane"], "a")
        self.assertEqual(closes_flags, [True])
        self.assertTrue(chunk_flags)
        self.assertTrue(all(chunk_flags))

    def test_in_sample_window_still_runs_without_id(self):
        def boom(*a, **k):
            raise AssertionError(
                "authorize_oos_run must not be consulted in-sample")

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                diagnostics, "authorize_oos_run", boom))
            closes_flags = []
            stack.enter_context(mock.patch.object(
                run_h7, "_load_closes",
                lambda sym, s, e, allow_oos:
                closes_flags.append(allow_oos) or (None, None)))
            stack.enter_context(mock.patch.object(
                run_h7, "_run_chunk", lambda *a, **k: dict(EMPTY_CHUNK)))
            out = run_h7.run_lane("a", "2022-01-03", "2022-06-30",
                                  symbols=["NVDA"], assertions=[],
                                  manifest=FAKE_MANIFEST)
        self.assertEqual(out["lane"], "a")
        self.assertEqual(closes_flags, [False])

    def test_no_capability_object_and_no_privileged_params(self):
        src = inspect.getsource(run_h7)
        self.assertNotIn("DiagnosticCapability", src)
        params = inspect.signature(run_h7.run_lane).parameters
        self.assertNotIn("capability", params)
        self.assertNotIn("allow_oos", params)
        self.assertIn("diagnostic_id", params)

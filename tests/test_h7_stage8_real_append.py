"""Stage-8 guarded real-store append path (BUILD-ONLY; the append itself is
owner-gated and never runs here).

These tests exercise ``register_window_real`` ONLY against temp-dir synthetic
stores, plus two boundary proofs: (1) the function refuses when handed a guard
report that is not a full, store-bound, fresh PASS while pointed at the real
``ledger/h7_forward`` store, and (2) that real store verifies byte-identical
(VALID EMPTY) before and after this module runs -- mirroring
``test_h7_stage7_synthetic_proof``'s before/after invariant.
"""
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from options_researcher import h7_activation_guard as ag
from options_researcher import h7_event_ledger as el
from options_researcher import h7_window_registration as wr
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from research.hashing import sha256_file

_CHECK_NAMES = (
    "ledger_valid_empty",
    "source_health_whole_universe",
    "data_gate_go",
    "owner_inputs_complete",
    "working_tree_clean",
)
# A real on-disk spec fixture: the append path hashes the FILE, not a string
# (review condition C1), so the fixture sha must come from real bytes.
_SPEC_DIR = tempfile.TemporaryDirectory()
_SPEC_PATH = Path(_SPEC_DIR.name) / "activation-spec.md"
_SPEC_PATH.write_text("stage-8 activation spec fixture\n")
_SPEC_SHA = sha256_file(_SPEC_PATH)
# Report built 00:00, appends "now" at 00:30 -- inside the 3600s bound (C2).
_BUILT = "2026-08-01T00:00:00+00:00"
_NOW = datetime.fromisoformat("2026-08-01T00:30:00+00:00")


def gates(**over):
    base = {
        "source_health_all_healthy": True,
        "data_gate_go": True,
        "source_health_evidence_id": "sh:2026-08-01",
        "data_gate_evidence_id": "dg:2026-08-01",
    }
    base.update(over)
    return base


def _head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def owner_inputs(**over):
    base = {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed-string 2026-XX-XX",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS decision sessions from start inclusive",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "renewal receipt <id>",
    }
    base.update(over)
    return base


def evidence(head, **over):
    base = {
        "review_evidence": "external review PASS <date>",
        "activation_spec_sha256": _SPEC_SHA,
        "code_commit": head,
        "source_health_evidence_id": "sh:2026-08-01",
        "data_gate_evidence_id": "dg:2026-08-01",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    base.update(over)
    return base


def ready_report(base_dir, head, *, ok=True, forward_base=None, code_commit=None):
    checks = [ag.Check(name, ok, "ok" if ok else "blocked") for name in _CHECK_NAMES]
    return ag.GuardReport(
        checks=checks,
        forward_base=forward_base if forward_base is not None
        else str(Path(base_dir).resolve()),
        code_commit=code_commit if code_commit is not None else head,
        built_at_utc=_BUILT,
    )


class RegisterWindowRealTests(unittest.TestCase):
    def setUp(self):
        self.head = _head()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name) / "synthetic-forward"

    def _call(self, **over):
        kwargs = dict(
            owner=owner_inputs(),
            evidence=evidence(self.head),
            guard_report=ready_report(self.base, self.head),
            spec_sha256=_SPEC_SHA,
            spec_path=_SPEC_PATH,
            base_dir=self.base,
            code_state=lambda: (self.head, True),
            recheck_gates=gates,
            now=_NOW,
        )
        kwargs.update(over)
        return wr.register_window_real(**kwargs)

    def test_appends_as_first_event_when_everything_passes(self):
        res = self._call()
        self.assertEqual(res.seq, 0)
        self.assertTrue(res.appended)
        v = el.verify(base_dir=self.base)
        self.assertEqual(v.count, 1)
        stored = el.read_events(self.base)[0]
        self.assertEqual(stored.event_type, "window_registration")
        self.assertEqual(stored.payload["activation_spec_sha256"], _SPEC_SHA)
        self.assertEqual(stored.payload["code_commit"], self.head)

    def test_refuses_when_report_not_ready(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(guard_report=ready_report(self.base, self.head, ok=False))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_report_bound_to_a_different_store(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(guard_report=ready_report(
                self.base, self.head, forward_base="/somewhere/else"))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_spec_sha_mismatches_evidence(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(spec_sha256="d" * 64)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_tree_is_dirty_at_append(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(code_state=lambda: (self.head, False))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_code_moved_since_guard(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(code_state=lambda: ("f" * 40, True))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_evidence_commit_disagrees_with_head(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(evidence=evidence(self.head, code_commit="a" * 40))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    # --- review conditions C2/C3 (2026-07-19): pinned refusal branches ---

    def test_refuses_empty_code_commit_identity(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(guard_report=ready_report(self.base, self.head,
                                                 code_commit=""))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_empty_built_at(self):
        report = ready_report(self.base, self.head)
        report.built_at_utc = ""
        with self.assertRaises(wr.ActivationRefused):
            self._call(guard_report=report)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_malformed_spec_sha(self):
        for bad in ("abc", "C" * 64, "g" * 64, _SPEC_SHA[:-1] + "G"):
            with self.subTest(bad=bad):
                with self.assertRaises(wr.ActivationRefused):
                    self._call(spec_sha256=bad)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_stale_guard_report(self):
        late = _NOW + timedelta(seconds=wr.GUARD_REPORT_MAX_AGE_S + 1)
        with self.assertRaises(wr.ActivationRefused):
            self._call(now=late)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_future_guard_report(self):
        early = datetime.fromisoformat(_BUILT) - timedelta(seconds=1)
        with self.assertRaises(wr.ActivationRefused):
            self._call(now=early)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_on_disk_spec_drift(self):
        drifted = Path(self.tmp.name) / "drifted-spec.md"
        drifted.write_text("stage-8 activation spec fixture EDITED\n")
        with self.assertRaises(wr.ActivationRefused):
            self._call(spec_path=drifted)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_missing_spec_file(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(spec_path=Path(self.tmp.name) / "no-such-spec.md")
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_failed_gate_recheck(self):
        for over in ({"source_health_all_healthy": False},
                     {"data_gate_go": False}):
            with self.subTest(over=over):
                with self.assertRaises(wr.ActivationRefused):
                    self._call(recheck_gates=lambda o=over: gates(**o))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_gate_evidence_id_mismatch(self):
        with self.assertRaises(wr.ActivationRefused):
            self._call(recheck_gates=lambda: gates(
                source_health_evidence_id="sh:some-other-run"))
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_missing_owner_input(self):
        bad = owner_inputs()
        del bad["WINDOW_START_DECISION_SESSION"]
        with self.assertRaises(wr.RegistrationInputError):
            self._call(owner=bad)
        self.assertTrue(el.verify(base_dir=self.base).empty)

    def test_refuses_when_ledger_not_valid_empty(self):
        # A pre-existing event makes the store non-empty; the append path must
        # re-verify VALID EMPTY itself and refuse, not trust the guard report.
        el.append_event({
            "schema_version": 1, "event_id": "x:1", "event_type": "skip",
            "occurred_at_utc": "2026-07-10T20:00:00+00:00",
            "evaluation_session": "2026-07-10", "symbol": None, "lane": None,
            "causes": [], "payload": {}}, base_dir=self.base, expected_head=None)
        with self.assertRaises(wr.ActivationRefused):
            self._call()
        self.assertEqual(el.verify(base_dir=self.base).count, 1)  # only the skip


class RealStoreUntouchedTests(unittest.TestCase):
    def test_real_store_refuses_incomplete_report_and_stays_valid_empty(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertTrue(before.valid and before.empty)
        head = _head()
        # An honest readiness snapshot against the real store: owner inputs
        # blank -> report not ready. Pointing the real-append path at the real
        # store with this report must refuse before any write.
        report = ag.activation_preconditions(
            forward_base=REAL_FORWARD_STORE,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result={"whole_universe_verdict": "GO", "go_count": 1,
                              "universe": ["MSFT"]},
            owner_inputs={}, allow_real_readonly=True)
        self.assertFalse(report.ready)
        with self.assertRaises(wr.ActivationRefused):
            wr.register_window_real(
                owner=owner_inputs(), evidence=evidence(head),
                guard_report=report, spec_sha256=_SPEC_SHA,
                spec_path=_SPEC_PATH, base_dir=REAL_FORWARD_STORE,
                code_state=lambda: (head, True), recheck_gates=gates,
                now=_NOW)
        after = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertEqual((after.valid, after.empty, after.count, after.head),
                         (before.valid, before.empty, before.count, before.head))


if __name__ == "__main__":
    unittest.main()

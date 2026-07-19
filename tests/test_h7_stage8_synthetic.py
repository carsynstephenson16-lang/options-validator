"""Stage-8 synthetic rehearsal: guard blocks -> inputs supplied -> registration
appends as the first event -> replays skip it -> real store untouched."""
import tempfile
import unittest
from pathlib import Path

from options_researcher import h7_activation_guard as ag
from options_researcher import h7_event_ledger as el
from options_researcher import h7_window_registration as wr
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE

# Fixture helpers copied verbatim from tests/test_h7_window_registration.py.
# tests/ has no __init__.py (not an importable package) and the repo
# convention (test_qm_watch.py, test_smoke.py) is to copy fixture shapes
# rather than cross-import between test modules.


def owner_inputs(**over):
    base = {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed-string 2026-XX-XX",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,  # 70 sessions from 2026-08-03 ends
        # ~2026-11-09, safely past the 3-calendar-month anniversary (2026-11-03);
        # 64 would end 2026-10-30 and fail the window rule — deliberate margin
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS decision sessions from start inclusive",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "renewal receipt <id>",
    }
    base.update(over)
    return base


def evidence(**over):
    base = {
        "review_evidence": "external review PASS <date>",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:2026-08-01",
        "data_gate_evidence_id": "dg:2026-08-01",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    base.update(over)
    return base


class Stage8SyntheticRehearsal(unittest.TestCase):
    def test_full_arc_on_synthetic_store(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertTrue(before.valid)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        universe = ("MSFT", "AMZN", "VST")
        health = {s: True for s in universe}
        gate = {"whole_universe_verdict": "GO", "go_count": 3,
                "universe": list(universe)}

        blocked = ag.activation_preconditions(
            forward_base=base, source_health_by_symbol=health,
            universe=universe, data_gate_result=gate, owner_inputs={})
        self.assertFalse(blocked.ready)  # owner inputs blank -> correctly blocked

        ready = ag.activation_preconditions(
            forward_base=base, source_health_by_symbol=health,
            universe=universe, data_gate_result=gate,
            owner_inputs=owner_inputs())
        self.assertTrue(ready.by_name["owner_inputs_complete"].ok)

        res = wr.register_window(owner=owner_inputs(), evidence=evidence(),
                                 base_dir=base)
        self.assertEqual(res.seq, 0)  # ledger seq is 0-indexed; first event
        after_reg = el.verify(base_dir=base)
        self.assertEqual(after_reg.count, 1)

        # a second registration refuses (head no longer empty)
        with self.assertRaises(el.LedgerHeadConflictError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=base)

        after = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertEqual((after.valid, after.empty, after.count, after.head),
                         (before.valid, before.empty, before.count, before.head))

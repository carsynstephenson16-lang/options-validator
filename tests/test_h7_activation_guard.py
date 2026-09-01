"""Stage-8 activation guard — every precondition, typed reasons, no side effects."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from options_researcher import h7_activation_guard as ag
from options_researcher.h7_window_registration import (
    OWNER_FIELDS as LEGACY_OWNER_FIELDS,
)


def go_gate(universe):
    return {"whole_universe_verdict": "GO", "go_count": len(universe),
            "universe": list(universe)}


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "synthetic-forward"
        self.addCleanup(self.tmp.cleanup)
        mapping = dict(ag.OWNER_FIELDS_BY_STORE)
        mapping[self.base.resolve()] = LEGACY_OWNER_FIELDS
        mapping_patch = patch.object(ag, "OWNER_FIELDS_BY_STORE", mapping)
        mapping_patch.start()
        self.addCleanup(mapping_patch.stop)

    def test_unrecognized_store_refuses(self):
        with self.assertRaisesRegex(
            ag.ActivationBoundaryError, "unrecognized forward store"
        ):
            ag.activation_preconditions(
                forward_base=self.base.parent / "unknown",
                source_health_by_symbol={"MSFT": True},
                universe=("MSFT",),
                data_gate_result=go_gate(("MSFT",)),
                owner_inputs={},
            )

    def test_schwab_store_selects_schwab_owner_fields(self):
        from options_researcher.h7_schwab_window_registration import (
            SCHWAB_FORWARD_STORE,
        )

        report = ag.activation_preconditions(
            forward_base=ag.REPO_ROOT / SCHWAB_FORWARD_STORE,
            source_health_by_symbol={"MSFT": True},
            universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)),
            owner_inputs={},
            allow_real_readonly=True,
        )
        reason = report.by_name["owner_inputs_complete"].reason
        self.assertIn("SCHWAB_MIN_LOSSES_FOR_VERDICT", reason)
        self.assertIn("SCHWAB_CONFIRMATION_EVIDENCE", reason)

    def test_all_preconditions_reported(self):
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True},
            universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)),
            owner_inputs={},
        )
        names = {c.name for c in report.checks}
        self.assertEqual(names, {"ledger_valid_empty", "source_health_whole_universe",
                                 "data_gate_go", "owner_inputs_complete",
                                 "working_tree_clean"})

    def test_blank_owner_inputs_block(self):
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)), owner_inputs={})
        check = report.by_name["owner_inputs_complete"]
        self.assertFalse(check.ok)
        self.assertIn("WINDOW_START_DECISION_SESSION", check.reason)
        self.assertFalse(report.ready)

    def test_one_unhealthy_symbol_blocks(self):
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True, "CRWV": False},
            universe=("MSFT", "CRWV"),
            data_gate_result=go_gate(("MSFT", "CRWV")), owner_inputs={})
        check = report.by_name["source_health_whole_universe"]
        self.assertFalse(check.ok)
        self.assertIn("CRWV", check.reason)

    def test_universe_count_is_derived_not_hardcoded(self):
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"A": True, "B": True, "C": True},
            universe=("A", "B", "C"),
            data_gate_result=go_gate(("A", "B", "C")), owner_inputs={})
        self.assertTrue(report.by_name["source_health_whole_universe"].ok)

    def test_no_go_gate_blocks(self):
        gate = {"whole_universe_verdict": "NO_GO", "go_count": 0, "universe": ["MSFT"]}
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result=gate, owner_inputs={})
        self.assertFalse(report.by_name["data_gate_go"].ok)

    def test_non_empty_ledger_blocks(self):
        from data.cache_runner import session_close_utc
        from options_researcher import h7_event_ledger as el
        el.append_event({
            "schema_version": 1, "event_id": "x:1", "event_type": "skip",
            "occurred_at_utc": session_close_utc("2026-07-10").isoformat(),
            "evaluation_session": "2026-07-10", "symbol": None, "lane": None,
            "causes": [], "payload": {}}, base_dir=self.base, expected_head=None)
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)), owner_inputs={})
        self.assertFalse(report.by_name["ledger_valid_empty"].ok)

    def test_real_store_readonly_snapshot_allowed(self):
        from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
        report = ag.activation_preconditions(
            forward_base=REAL_FORWARD_STORE,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)), owner_inputs={},
            allow_real_readonly=True)
        # Phase-aware: post-activation (2026-07-20) the real store is correctly
        # non-empty, so the ledger_valid_empty precondition now reports not-ok — that
        # is the guard working (it would refuse a second activation). The invariant
        # this test guards is that allow_real_readonly lets the snapshot run WITHOUT
        # raising; assert the report was produced and the check ran, not that it is ok.
        self.assertIn("ledger_valid_empty", report.by_name)
        self.assertFalse(report.by_name["ledger_valid_empty"].ok)

    def test_real_store_refused_without_readonly_flag(self):
        from options_researcher.h7_paper_lifecycle import (
            REAL_FORWARD_STORE,
            ActivationBoundaryError,
        )
        with self.assertRaises(ActivationBoundaryError):
            ag.activation_preconditions(
                forward_base=REAL_FORWARD_STORE,
                source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
                data_gate_result=go_gate(("MSFT",)), owner_inputs={})

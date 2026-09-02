"""Stage-8 activation guard — every precondition, typed reasons, no side effects."""
import tempfile
import unittest
from pathlib import Path

from options_researcher import h7_activation_guard as ag
from options_researcher.h7_schwab_data_gate import EVIDENCE_MODE as SCHWAB_EVIDENCE
from options_researcher.h7_schwab_window_registration import (
    OWNER_FIELDS as SCHWAB_OWNER_FIELDS,
)
from options_researcher.h7_schwab_window_registration import (
    SCHWAB_FORWARD_STORE,
)
from options_researcher.h7_window_registration import (
    OWNER_FIELDS as LEGACY_OWNER_FIELDS,
)


def go_gate(universe, *, evidence_mode: str | None = None):
    gate = {"whole_universe_verdict": "GO", "go_count": len(universe),
            "universe": list(universe)}
    if evidence_mode is not None:
        gate["evidence_mode"] = evidence_mode
    return gate


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "synthetic-forward"
        self.addCleanup(self.tmp.cleanup)

    def test_synthetic_store_resolves_legacy_fields_without_any_patching(self):
        """Round-1 F2: pre-branch behavior for a synthetic store, unpatched."""
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True},
            universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)),
            owner_inputs={},
        )
        check = report.by_name["owner_inputs_complete"]
        self.assertFalse(check.ok)
        self.assertEqual(check.reason, f"blank: {list(LEGACY_OWNER_FIELDS)}")

    def test_synthetic_store_with_schwab_evidence_resolves_schwab_fields(self):
        report = ag.activation_preconditions(
            forward_base=self.base,
            source_health_by_symbol={"MSFT": True},
            universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",), evidence_mode=SCHWAB_EVIDENCE),
            owner_inputs={},
        )
        check = report.by_name["owner_inputs_complete"]
        self.assertEqual(check.reason, f"blank: {list(SCHWAB_OWNER_FIELDS)}")

    def test_owner_field_set_cannot_be_supplied_or_named_by_a_caller(self):
        for forbidden in ({"owner_fields": ()}, {"scope_id": "h7-forward-schwab-v1"},
                          {"namespace": "h7-forward-schwab-v1"}):
            with self.assertRaises(TypeError):
                ag.activation_preconditions(
                    forward_base=self.base,
                    source_health_by_symbol={"MSFT": True},
                    universe=("MSFT",),
                    data_gate_result=go_gate(("MSFT",)),
                    owner_inputs={},
                    **forbidden,
                )

    def test_schwab_store_selects_schwab_owner_fields(self):
        report = ag.activation_preconditions(
            forward_base=ag.REPO_ROOT / SCHWAB_FORWARD_STORE,
            source_health_by_symbol={"MSFT": True},
            universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",), evidence_mode=SCHWAB_EVIDENCE),
            owner_inputs={},
            allow_real_readonly=True,
        )
        reason = report.by_name["owner_inputs_complete"].reason
        self.assertIn("SCHWAB_MIN_LOSSES_FOR_VERDICT", reason)
        self.assertIn("SCHWAB_CONFIRMATION_EVIDENCE", reason)

    def test_schwab_evidence_cannot_activate_the_legacy_real_store(self):
        from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE

        with self.assertRaisesRegex(
            ag.ActivationBoundaryError, "legacy"
        ):
            ag.activation_preconditions(
                forward_base=REAL_FORWARD_STORE,
                source_health_by_symbol={"MSFT": True},
                universe=("MSFT",),
                data_gate_result=go_gate(("MSFT",), evidence_mode=SCHWAB_EVIDENCE),
                owner_inputs={},
                allow_real_readonly=True,
            )

    def test_legacy_evidence_cannot_activate_the_schwab_real_store(self):
        with self.assertRaisesRegex(
            ag.ActivationBoundaryError, "Schwab data-gate evidence"
        ):
            ag.activation_preconditions(
                forward_base=ag.REPO_ROOT / SCHWAB_FORWARD_STORE,
                source_health_by_symbol={"MSFT": True},
                universe=("MSFT",),
                data_gate_result=go_gate(("MSFT",)),
                owner_inputs={},
                allow_real_readonly=True,
            )

    def test_a_subpath_of_either_real_store_is_still_boundary_guarded(self):
        from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE

        for store, mode in (
            (Path(REAL_FORWARD_STORE) / "nested", None),
            (ag.REPO_ROOT / SCHWAB_FORWARD_STORE / "nested", SCHWAB_EVIDENCE),
        ):
            with self.assertRaisesRegex(
                ag.ActivationBoundaryError, "synthetic stores"
            ):
                ag.activation_preconditions(
                    forward_base=store,
                    source_health_by_symbol={"MSFT": True},
                    universe=("MSFT",),
                    data_gate_result=go_gate(("MSFT",), evidence_mode=mode),
                    owner_inputs={},
                )

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

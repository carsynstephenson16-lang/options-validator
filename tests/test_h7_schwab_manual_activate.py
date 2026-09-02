"""Brief 36 WP-C owner-confirmed Schwab activation CLI tests."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_h7_schwab_window_registration import (
    _verified_data_gate_receipt,
    evidence,
    owner_inputs,
)

from options_researcher import h7_activation_guard as guard
from options_researcher import h7_data_gate
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_schwab_window_registration as registration
from options_researcher.h7_scope import scope_identity
from research.hashing import sha256_file
from research.receipts import (
    load_receipt,
    make_receipt,
    write_immutable_receipt,
)
from tools import h7_schwab_manual_activate as cli


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def authorization_text() -> str:
    return (
        "OD-3 2026-09-01: "
        f"{cli.OD3_NAMESPACE_COMMITMENT} "
        f"{cli.QUOTE_AGE_COMMITMENT} "
        f"{cli.QUOTE_AGE_EVIDENCE_CITATION}"
    )


class SchwabManualActivateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.store = self.root / "h7-forward-schwab"
        self.spec = self.root / "activation-spec.md"
        self.spec.write_text(
            "owner-reviewed Schwab activation fixture\n",
            encoding="utf-8",
        )
        self.data_path = self.root / "data-gate.json"
        self.backup_path = self.root / "backup-restore.json"
        self.evidence_path = self.root / "evidence.json"

        self.data = _verified_data_gate_receipt()
        write_immutable_receipt(self.data, self.data_path)
        self.source_path = Path(self.data["source_health_receipt_path"])
        self.source = load_receipt(self.source_path, expected_type="source_health")
        self.backup = make_receipt(
            "backup_restore",
            {
                "scope": scope_identity(),
                "completed_session": self.data["evaluation_session"],
                "verification": {"ok": True},
            },
        )
        write_immutable_receipt(self.backup, self.backup_path)
        self.owner = owner_inputs(H7_STAGE8_EXPLICIT_AUTHORIZATION=authorization_text())
        self.evidence = evidence(
            activation_spec_sha256=sha256_file(self.spec),
            code_commit=_head(),
        )
        self.evidence_path.write_text(json.dumps(self.evidence), encoding="utf-8")

    def test_authorization_requires_od3_and_row7_content(self):
        cli.validate_authorization_text(authorization_text())
        for missing in (
            cli.OD3_NAMESPACE_COMMITMENT,
            cli.QUOTE_AGE_COMMITMENT,
            cli.QUOTE_AGE_EVIDENCE_CITATION,
        ):
            with self.subTest(missing=missing):
                with self.assertRaisesRegex(ValueError, "authorization text"):
                    cli.validate_authorization_text(authorization_text().replace(missing, ""))

    def test_cli_has_no_store_universe_or_trim_escape_hatch(self):
        actions = {
            option: action for action in cli._parser()._actions for option in action.option_strings
        }
        for forbidden in ("--store", "--universe", "--trim-unhealthy"):
            self.assertNotIn(forbidden, actions)
        for required in (
            "--h7-stage8-explicit-authorization",
            "--window-start-decision-session",
            "--window-decision-session-count",
            "--window-end-rule-acknowledged",
            "--window-minimum-three-calendar-months-per-lane-acknowledged",
            "--schwab-capture-lane-verified-through",
            "--schwab-capture-commitment-through",
            "--schwab-confirmation-evidence",
            "--session-chain-convention",
            "--schwab-min-losses-for-verdict",
            "--schwab-starvation-risk-preacceptance",
        ):
            self.assertTrue(actions[required].required)

    def test_confirmation_is_required_before_evidence_reads(self):
        with self.assertRaisesRegex(ValueError, "type exactly"):
            cli.activate(
                owner=self.owner,
                evidence_path=self.root / "missing.json",
                source_health_path=self.source_path,
                data_gate_path=self.data_path,
                backup_restore_path=self.backup_path,
                completed_session=self.data["evaluation_session"],
                confirmation="wrong",
                spec_path=self.spec,
                forward_base=self.store,
            )

    def test_temp_store_activation_delegates_to_actual_one_door(self):
        # Round-1 F2: the Schwab owner fields are resolved from the receipt's
        # own Schwab evidence mode; nothing about the guard is patched.
        with (
            mock.patch.object(
                guard,
                "_working_tree_clean",
                return_value=guard.Check("working_tree_clean", True, "clean"),
            ),
        ):
            result = cli.activate(
                owner=self.owner,
                evidence_path=self.evidence_path,
                source_health_path=self.source_path,
                data_gate_path=self.data_path,
                backup_restore_path=self.backup_path,
                completed_session=self.data["evaluation_session"],
                confirmation=cli.CONFIRMATION,
                spec_path=self.spec,
                forward_base=self.store,
                code_state=lambda: (_head(), True),
            )

        self.assertEqual(result.seq, 0)
        events = ledger.read_events(self.store)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, "window_registration")
        self.assertEqual(events[0].payload["namespace"], registration.NAMESPACE)
        self.assertEqual(
            events[0].payload["owner_authorization"]["H7_STAGE8_EXPLICIT_AUTHORIZATION"],
            authorization_text(),
        )

    def test_durable_data_gate_is_revalidated_before_door(self):
        with mock.patch.object(
            h7_data_gate,
            "validate_durable_receipt",
            side_effect=ValueError("forced stale receipt"),
        ):
            with self.assertRaisesRegex(ValueError, "forced stale receipt"):
                cli.activate(
                    owner=self.owner,
                    evidence_path=self.evidence_path,
                    source_health_path=self.source_path,
                    data_gate_path=self.data_path,
                    backup_restore_path=self.backup_path,
                    completed_session=self.data["evaluation_session"],
                    confirmation=cli.CONFIRMATION,
                    spec_path=self.spec,
                    forward_base=self.store,
                )
        self.assertTrue(ledger.verify(self.store).empty)


if __name__ == "__main__":
    unittest.main()

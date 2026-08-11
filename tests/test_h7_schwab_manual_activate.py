"""Offline composition tests for the owner-gated Schwab registration CLI."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from options_researcher import h7_activation_guard as activation_guard
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_schwab_window_registration as registration
from options_researcher.h7_scope import scope_identity
from research.hashing import (
    canonical_json,
    config_hash,
    diagnostic_source_hash,
    sha256_file,
    sha256_hex,
)
from research.receipts import make_receipt
from tools import h7_schwab_manual_activate as cli

SESSION = "2026-08-10"
REQUESTED = "2026-08-11"
CANONICAL_UNIVERSE = [
    "AMD",
    "AMZN",
    "AVGO",
    "CEG",
    "CRWV",
    "ET",
    "IREN",
    "MSFT",
    "NOW",
    "NVDA",
    "PLTR",
    "SMCI",
    "TEM",
    "USAR",
    "VST",
]


def _write_json(path: Path, value: dict) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _feasibility() -> dict:
    payload = {
        "receipt_kind": "h7_schwab_feasibility/v1",
        "provenance": "LLM/tool-computed",
        "lookback_start": "2026-04-16",
        "lookback_end": "2026-07-27",
        "lookback_sessions": 70,
        "stack_version": "h7-frozen-entry-stack-plus-board/v1",
        "code_sha": "a" * 40,
        "config_hash": "80fe2bf649e16e9b18f7cb7a9ccc26b9b01bcb852fcb6998c7b14611934a4d49",
        "error_count": 0,
        "errors": [],
        "tool_label": "cached-only read-only measurement; no verdict",
        "universe": CANONICAL_UNIVERSE,
        "universe_size": 15,
        "window_sessions": 70,
        "symbol_days": 1050,
        "full_stack_passes": 20,
        "base_rate": 20 / 1050,
        "expected_entries": 20.0,
    }
    return {**payload, "receipt_hash": sha256_hex(canonical_json(payload))}


class SchwabManualActivateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / "ledger"
        self.names = list(scope_identity()["symbols"])
        self.head = "b" * 40

        self.spec = self.root / "activation.md"
        self.spec.write_text("reviewed Schwab activation fixture\n", encoding="utf-8")
        self.spec_sha = sha256_file(self.spec)
        feasibility = _feasibility()
        self.owner_path = _write_json(
            self.root / "owner.json",
            {
                "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed fixture",
                "WINDOW_START_DECISION_SESSION": "2026-08-11",
                "WINDOW_DECISION_SESSION_COUNT": 70,
                "WINDOW_END_RULE_ACKNOWLEDGED": "owner-typed fixture",
                "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": (
                    "owner-typed fixture"
                ),
                "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH": SESSION,
                "SCHWAB_CAPTURE_COMMITMENT_THROUGH": "2026-12-31",
                "SCHWAB_CONFIRMATION_EVIDENCE": "owner-typed fixture",
                "SESSION_CHAIN_CONVENTION": "preclose_snapshot_v1",
                "H7_SCHWAB_FEASIBILITY_DECISION": (
                    "REJECT OLD 3/1050 STARVATION-RISK PATH; BIND "
                    "h7-forward-schwab-v1 TO QUALIFYING FEASIBILITY RECEIPT "
                    f"{feasibility['receipt_hash']}"
                ),
            },
        )
        source = make_receipt(
            "source_health",
            {
                "evaluation_session": SESSION,
                "scope": scope_identity(),
                "healthy_count": 15,
                "unhealthy_count": 0,
                "unhealthy_symbols": [],
                "activation_ready": True,
                "symbols": {symbol: {"symbol": symbol, "healthy": True} for symbol in self.names},
            },
        )
        self.source_path = _write_json(self.root / "source.json", source)

        manifest_path = self.root / "manifest.json"
        capture_path = self.root / "preclose.json"
        symbols = {}
        for symbol in self.names:
            symbols[symbol] = {
                "symbol": symbol,
                "verdict": "GO",
                "close": {"path": str(self.root / "closes" / f"{symbol}.parquet")},
                "chain": {
                    "expected_path": str(self.root / "chains" / f"{symbol}_{SESSION}.parquet"),
                    "audit_receipt": {
                        "valid": True,
                        "provider": "schwab",
                        "session": SESSION,
                        "session_chain_convention": "preclose_snapshot_v1",
                        "manifest_hash": "f" * 64,
                        "manifest_path": str(manifest_path),
                        "receipt_path": str(capture_path),
                    },
                },
            }
        self.data_result = {
            "evidence_mode": "REAL-H7-SCHWAB-PRECLOSE-AUDIT",
            "evaluation_session": SESSION,
            "requested_run_date": REQUESTED,
            "scope": scope_identity(),
            "universe": self.names,
            "whole_universe_verdict": "GO",
            "go_count": 15,
            "no_go_count": 0,
            "symbols": symbols,
        }
        data_receipt = make_receipt(
            "data_gate",
            {
                **self.data_result,
                "source_health_receipt_hash": source["receipt_hash"],
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )
        self.data_path = _write_json(self.root / "data-gate.json", data_receipt)

        backup_receipt = make_receipt(
            "backup",
            {
                "completed_session": SESSION,
                "snapshot_id": "snapshot-abc",
                "scope": scope_identity(),
                "input_files": {"ledger/h7_forward_schwab": {"kind": "directory", "files": {}}},
            },
        )
        self.backup_path = _write_json(self.root / "backup.json", backup_receipt)
        restore_receipt = make_receipt(
            "backup_restore",
            {
                "completed_session": SESSION,
                "verified_at_utc": datetime.now(timezone.utc).isoformat(),
                "snapshot": "snapshot-abc",
                "snapshot_id": "snapshot-abc",
                "backup_receipt_hash": backup_receipt["receipt_hash"],
                "scope": scope_identity(),
                "restored_inventory": backup_receipt["input_files"],
                "verification": {"ok": True},
            },
        )
        self.restore_path = _write_json(self.root / "restore.json", restore_receipt)

        self.evidence_path = _write_json(
            self.root / "evidence.json",
            {
                "review_evidence": "independent review PASS fixture",
                "activation_spec_sha256": self.spec_sha,
                "code_commit": self.head,
                "source_health_evidence_id": source["receipt_hash"],
                "data_gate_evidence_id": data_receipt["receipt_hash"],
                "source_health_receipt_hash": source["receipt_hash"],
                "data_gate_receipt_hash": data_receipt["receipt_hash"],
                "backup_restore_receipt_hash": restore_receipt["receipt_hash"],
                "last_historical_session": SESSION,
                "last_historical_manifest_receipt_hash": "f" * 64,
                "provider_identity": "schwab-read-only/v1",
                "cache_namespace": ".cache/schwab_chains/",
                "feasibility_receipt": feasibility,
                "feasibility_receipt_hash": feasibility["receipt_hash"],
                "darwin_durability_verified": True,
                "pre_append_state": "VALID EMPTY",
            },
        )

    def _activate(self, *, code_state=None, data_gate_evaluator=None):
        evaluator = data_gate_evaluator or (lambda *args, **kwargs: dict(self.data_result))
        source_evaluator = lambda **kwargs: {"activation_ready": True}
        with (
            mock.patch.object(
                activation_guard,
                "_working_tree_clean",
                return_value=activation_guard.Check("working_tree_clean", True, "clean"),
            ),
            mock.patch.object(activation_guard, "_git_head", return_value=self.head),
        ):
            return cli.activate(
                owner_path=self.owner_path,
                evidence_path=self.evidence_path,
                source_health_path=self.source_path,
                data_gate_path=self.data_path,
                backup_path=self.backup_path,
                backup_restore_path=self.restore_path,
                completed_session=SESSION,
                confirmation=cli.CONFIRMATION,
                spec_path=self.spec,
                forward_base=self.store,
                code_state=code_state or (lambda: (self.head, True)),
                data_gate_evaluator=evaluator,
                source_health_evaluator=source_evaluator,
                source_assertion_loader=lambda: [],
            )

    def test_full_scope_evidence_registers_through_one_door(self):
        result = self._activate()

        self.assertEqual(result.seq, 0)
        event = ledger.read_events(self.store)[0]
        self.assertEqual(event.payload["universe"]["included"], self.names)
        restore = json.loads(self.restore_path.read_text())
        self.assertEqual(
            event.payload["gates"]["backup_restore_receipt_hash"],
            restore["receipt_hash"],
        )

    def test_partial_scope_receipt_refuses(self):
        receipt = json.loads(self.data_path.read_text())
        body = {key: value for key, value in receipt.items() if key != "receipt_hash"}
        body["universe"] = self.names[:-1]
        body["go_count"] = 14
        _write_json(
            self.data_path,
            make_receipt(
                "data_gate",
                {
                    key: value
                    for key, value in body.items()
                    if key not in ("receipt_schema", "receipt_type")
                },
            ),
        )

        with self.assertRaisesRegex(ValueError, "official 15-name scope"):
            self._activate()
        self.assertTrue(ledger.verify(self.store).empty)

    def test_stale_completed_session_evidence_refuses(self):
        receipt = json.loads(self.data_path.read_text())
        payload = {
            key: value
            for key, value in receipt.items()
            if key not in ("receipt_schema", "receipt_type", "receipt_hash")
        }
        payload["evaluation_session"] = "2026-08-07"
        _write_json(self.data_path, make_receipt("data_gate", payload))

        with self.assertRaisesRegex(ValueError, "completed session"):
            self._activate()
        self.assertTrue(ledger.verify(self.store).empty)

    def test_dirty_or_moved_head_refuses(self):
        for label, code_state in (
            ("dirty", lambda: (self.head, False)),
            ("moved", lambda: ("c" * 40, True)),
        ):
            with self.subTest(label=label):
                with self.assertRaises(registration.ActivationRefused):
                    self._activate(code_state=code_state)
                self.assertTrue(ledger.verify(self.store).empty)

    def test_append_time_valid_backup_pair_substitution_refuses(self):
        calls = 0

        def evaluator(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                backup = make_receipt(
                    "backup",
                    {
                        "completed_session": SESSION,
                        "snapshot_id": "snapshot-substituted",
                        "scope": scope_identity(),
                        "input_files": {
                            "ledger/h7_forward_schwab": {
                                "kind": "directory",
                                "files": {},
                            }
                        },
                    },
                )
                _write_json(self.backup_path, backup)
                restore = make_receipt(
                    "backup_restore",
                    {
                        "completed_session": SESSION,
                        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
                        "snapshot": "snapshot-substituted",
                        "snapshot_id": "snapshot-substituted",
                        "backup_receipt_hash": backup["receipt_hash"],
                        "scope": scope_identity(),
                        "restored_inventory": backup["input_files"],
                        "verification": {"ok": True},
                    },
                )
                _write_json(self.restore_path, restore)
            return dict(self.data_result)

        with self.assertRaises(registration.ActivationRefused):
            self._activate(data_gate_evaluator=evaluator)
        self.assertEqual(calls, 2)
        self.assertTrue(ledger.verify(self.store).empty)


if __name__ == "__main__":
    unittest.main()

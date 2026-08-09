"""Synthetic-only tests for the new Schwab H7 registration namespace."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from options_researcher import h7_activation_guard as activation_guard
from options_researcher import h7_event_ledger as ledger
from options_researcher import h7_schwab_window_registration as registration
from research.hashing import canonical_json, sha256_file, sha256_hex


def feasibility_receipt(**overrides) -> dict:
    payload = {
        "receipt_kind": "h7_schwab_feasibility/v1",
        "provenance": "LLM/tool-computed",
        "lookback_start": "2026-05-08",
        "lookback_end": "2026-08-07",
        "stack_version": "h7-frozen-entry-stack/v1",
        "code_sha": "b" * 40,
        "universe_size": 15,
        "window_sessions": 70,
        "symbol_days": 540,
        "full_stack_passes": 3,
        "base_rate": 3 / 540,
        "expected_entries": (3 / 540) * 70 * 15,
    }
    payload.update(overrides)
    payload["receipt_hash"] = sha256_hex(canonical_json(payload))
    return payload


def owner_inputs(**overrides) -> dict:
    values = {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed placeholder",
        "WINDOW_START_DECISION_SESSION": "2026-08-10",
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "owner-typed placeholder",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "owner-typed placeholder",
        "SCHWAB_CAPTURE_LANE_VERIFIED_THROUGH": "2026-08-07",
        "SCHWAB_CAPTURE_COMMITMENT_THROUGH": "2026-12-31",
        "SCHWAB_CONFIRMATION_EVIDENCE": "owner-typed placeholder",
        "SESSION_CHAIN_CONVENTION": "preclose_snapshot_v1",
    }
    values.update(overrides)
    return values


def evidence(**overrides) -> dict:
    receipt = feasibility_receipt()
    values = {
        "review_evidence": "external adversarial review placeholder",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:2026-08-07",
        "data_gate_evidence_id": "dg:2026-08-07",
        "source_health_receipt_hash": "c" * 64,
        "data_gate_receipt_hash": "d" * 64,
        "last_historical_session": "2026-08-07",
        "last_historical_manifest_receipt_hash": "e" * 64,
        "provider_identity": "schwab-read-only/v1",
        "cache_namespace": ".cache/schwab_chains/",
        "feasibility_receipt": receipt,
        "feasibility_receipt_hash": receipt["receipt_hash"],
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    values.update(overrides)
    return values


class BuilderTests(unittest.TestCase):
    def test_builds_new_namespace_with_unchanged_frozen_rules(self):
        event = registration.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence()
        )
        payload = event["payload"]
        self.assertEqual(payload["namespace"], "h7-forward-schwab-v1")
        self.assertEqual(payload["provider"]["identity"], "schwab-read-only/v1")
        self.assertEqual(payload["provider"]["cache_namespace"], ".cache/schwab_chains/")
        self.assertEqual(
            payload["provider"]["session_chain_convention"],
            "preclose_snapshot_v1",
        )
        self.assertEqual(payload["frozen"]["scorer"]["min_losses_for_verdict"], 10)
        self.assertEqual(payload["history"]["last_session"], "2026-08-07")
        self.assertEqual(
            payload["feasibility"]["receipt"]["provenance"],
            "LLM/tool-computed",
        )

    def test_missing_owner_field_refuses(self):
        owner = owner_inputs()
        del owner["SCHWAB_CONFIRMATION_EVIDENCE"]
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner, evidence=evidence()
            )

    def test_capture_commitment_short_of_window_end_refuses(self):
        with self.assertRaises(registration.WindowRuleError):
            registration.build_window_registration_event(
                owner=owner_inputs(SCHWAB_CAPTURE_COMMITMENT_THROUGH="2026-09-01"),
                evidence=evidence(),
            )

    def test_wrong_convention_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(SESSION_CHAIN_CONVENTION="eod_mark_v1"),
                evidence=evidence(),
            )

    def test_tampered_feasibility_payload_refuses(self):
        receipt = feasibility_receipt()
        receipt["full_stack_passes"] = 999
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )


class SyntheticAppendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "h7_forward_schwab"

    def test_happy_path_registers_and_verifies_temp_store(self):
        result = registration.register_window(
            owner=owner_inputs(), evidence=evidence(), base_dir=self.store
        )
        self.assertEqual(result.seq, 0)
        verified = ledger.verify(self.store)
        self.assertTrue(verified.valid)
        self.assertEqual(verified.count, 1)

    def test_non_empty_target_refuses(self):
        registration.register_window(
            owner=owner_inputs(), evidence=evidence(), base_dir=self.store
        )
        with self.assertRaises(ledger.LedgerHeadConflictError):
            registration.register_window(
                owner=owner_inputs(), evidence=evidence(), base_dir=self.store
            )


class GuardedDoorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "h7_forward_schwab"
        self.spec = Path(self.temp.name) / "activation.md"
        self.spec.write_text("owner-reviewed activation fixture\n", encoding="utf-8")
        self.spec_sha = sha256_file(self.spec)
        self.head = "b" * 40
        checks = [activation_guard.Check("all", True, "ok")]
        self.report = activation_guard.GuardReport(
            checks=checks,
            forward_base=str(self.store.resolve()),
            code_commit=self.head,
            built_at_utc="2026-08-09T20:00:00+00:00",
        )

    def call(self):
        return registration.register_window_real(
            owner=owner_inputs(),
            evidence=evidence(
                activation_spec_sha256=self.spec_sha,
                code_commit=self.head,
            ),
            guard_report=self.report,
            spec_sha256=self.spec_sha,
            spec_path=self.spec,
            base_dir=self.store,
            code_state=lambda: (self.head, True),
            recheck_gates=lambda: {
                "source_health_all_healthy": True,
                "data_gate_go": True,
                "source_health_evidence_id": "sh:2026-08-07",
                "data_gate_evidence_id": "dg:2026-08-07",
            },
            now=datetime.fromisoformat("2026-08-09T20:30:00+00:00"),
        )

    def test_guarded_door_appends_only_as_first_event(self):
        result = self.call()
        self.assertEqual(result.seq, 0)
        self.assertEqual(ledger.verify(self.store).count, 1)

    def test_guarded_door_refuses_non_empty_target(self):
        ledger.append_event(
            {
                "schema_version": 1,
                "event_id": "existing:1",
                "event_type": "skip",
                "occurred_at_utc": "2026-08-07T20:00:00+00:00",
                "evaluation_session": "2026-08-07",
                "symbol": None,
                "lane": None,
                "causes": [],
                "payload": {},
            },
            base_dir=self.store,
            expected_head=None,
        )
        with self.assertRaises(registration.ActivationRefused):
            self.call()
        self.assertEqual(ledger.verify(self.store).count, 1)


if __name__ == "__main__":
    unittest.main()

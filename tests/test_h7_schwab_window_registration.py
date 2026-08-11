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


def feasibility_receipt(**overrides) -> dict:
    payload = {
        "receipt_kind": "h7_schwab_feasibility/v1",
        "provenance": "LLM/tool-computed",
        "lookback_start": "2026-04-16",
        "lookback_end": "2026-07-27",
        "lookback_sessions": 70,
        "stack_version": "h7-frozen-entry-stack-plus-board/v1",
        "code_sha": "b" * 40,
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
    payload.update(overrides)
    payload["receipt_hash"] = sha256_hex(canonical_json(payload))
    return payload


def owner_inputs(*, receipt_hash: str | None = None, **overrides) -> dict:
    if receipt_hash is None:
        receipt_hash = feasibility_receipt()["receipt_hash"]
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
        "H7_SCHWAB_FEASIBILITY_DECISION": (
            "REJECT OLD 3/1050 STARVATION-RISK PATH; BIND "
            "h7-forward-schwab-v1 TO QUALIFYING FEASIBILITY RECEIPT "
            f"{receipt_hash}"
        ),
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
        "backup_restore_receipt_hash": "f" * 64,
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
            registration.build_window_registration_event(owner=owner, evidence=evidence())

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

    def test_exactly_twenty_expected_entries_is_accepted(self):
        receipt = feasibility_receipt()
        event = registration.build_window_registration_event(
            owner=owner_inputs(receipt_hash=receipt["receipt_hash"]),
            evidence=evidence(
                feasibility_receipt=receipt,
                feasibility_receipt_hash=receipt["receipt_hash"],
            ),
        )

        self.assertEqual(event["payload"]["feasibility"]["receipt"]["expected_entries"], 20.0)

    def test_qualifying_receipt_requires_exact_hash_and_namespace_owner_line(self):
        receipt = feasibility_receipt()
        exact = owner_inputs(receipt_hash=receipt["receipt_hash"])
        wrong_lines = {
            "missing": None,
            "stale hash": exact["H7_SCHWAB_FEASIBILITY_DECISION"].replace(
                receipt["receipt_hash"], "0" * 64
            ),
            "wrong namespace": exact["H7_SCHWAB_FEASIBILITY_DECISION"].replace(
                "h7-forward-schwab-v1", "h7-forward-schwab-v2"
            ),
        }
        for label, decision in wrong_lines.items():
            with self.subTest(label=label):
                owner = owner_inputs(receipt_hash=receipt["receipt_hash"])
                if decision is None:
                    del owner["H7_SCHWAB_FEASIBILITY_DECISION"]
                else:
                    owner["H7_SCHWAB_FEASIBILITY_DECISION"] = decision
                with self.assertRaises(registration.RegistrationInputError):
                    registration.build_window_registration_event(
                        owner=owner,
                        evidence=evidence(
                            feasibility_receipt=receipt,
                            feasibility_receipt_hash=receipt["receipt_hash"],
                        ),
                    )

    def test_shortened_denominator_cannot_manufacture_twenty_expected_entries(self):
        receipt = feasibility_receipt(
            symbol_days=210,
            full_stack_passes=4,
            base_rate=4 / 210,
            expected_entries=20.0,
        )
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(receipt_hash=receipt["receipt_hash"]),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_receipt_universe_must_equal_canonical_manifest_universe(self):
        receipt = feasibility_receipt(universe=["FAKE1", "FAKE2"])
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(receipt_hash=receipt["receipt_hash"]),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_alternate_study_identity_refuses(self):
        for label, overrides in (
            ("stack", {"stack_version": "alternate-entry-stack/v1"}),
            ("tool", {"tool_label": "different measurement tool"}),
            ("lookback", {"lookback_sessions": 69}),
            ("start", {"lookback_start": "2026-04-17"}),
            ("end", {"lookback_end": "2026-07-28"}),
            ("errors", {"error_count": 1}),
            ("hidden errors", {"errors": [{"error": "fixture"}]}),
            ("config", {"config_hash": "0" * 64}),
        ):
            with self.subTest(label=label):
                receipt = feasibility_receipt(**overrides)
                with self.assertRaises(registration.RegistrationInputError):
                    registration.build_window_registration_event(
                        owner=owner_inputs(receipt_hash=receipt["receipt_hash"]),
                        evidence=evidence(
                            feasibility_receipt=receipt,
                            feasibility_receipt_hash=receipt["receipt_hash"],
                        ),
                    )

    def test_measurement_code_sha_may_precede_registration_commit(self):
        event = registration.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence(code_commit="c" * 40)
        )
        self.assertEqual(
            event["payload"]["feasibility"]["receipt"]["code_sha"],
            "b" * 40,
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

    def test_nonqualifying_hash_correct_receipts_refuse_before_append(self):
        for passes in (3, 4):
            with self.subTest(passes=passes):
                receipt = feasibility_receipt(
                    full_stack_passes=passes,
                    base_rate=passes / 1050,
                    expected_entries=float(passes),
                )
                store = Path(self.temp.name) / f"h7_forward_schwab_{passes}"
                with self.assertRaises(registration.RegistrationInputError):
                    registration.register_window(
                        owner=owner_inputs(receipt_hash=receipt["receipt_hash"]),
                        evidence=evidence(
                            feasibility_receipt=receipt,
                            feasibility_receipt_hash=receipt["receipt_hash"],
                        ),
                        base_dir=store,
                    )
                self.assertTrue(ledger.verify(store).empty)

    def test_non_empty_target_refuses(self):
        registration.register_window(owner=owner_inputs(), evidence=evidence(), base_dir=self.store)
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
                "backup_restore_receipt_hash": "f" * 64,
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

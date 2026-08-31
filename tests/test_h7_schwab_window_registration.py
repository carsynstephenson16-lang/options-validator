"""Synthetic-only tests for the new Schwab H7 registration namespace."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from options_researcher import h7_activation_guard as activation_guard
from options_researcher import (
    h7_data_gate,
    h7_schwab_data_gate,
)
from options_researcher import h7_event_ledger as ledger
from options_researcher import (
    h7_schwab_window_registration as registration,
)
from options_researcher import h7_window_registration as old_registration
from options_researcher.h7_scope import scope_identity
from research.hashing import canonical_json, config_hash, sha256_file, sha256_hex
from research.receipts import make_receipt, write_immutable_receipt
from tools import schwab_chain_manifest

_DEFAULT_UNIVERSE = old_registration.default_universe_manifest()["included"]
_REAL_GATE_TMP: tempfile.TemporaryDirectory | None = None
_REAL_GATE_RECEIPT: dict | None = None


def _chain_frame() -> pd.DataFrame:
    rows = []
    for expiration in ("2026-08-21", "2026-09-18"):
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "bid": 1.0,
                    "ask": 1.2,
                    "open_interest": 100,
                    "iv": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                }
            )
    return pd.DataFrame(rows)


def _verified_data_gate_receipt() -> dict:
    """Create one persistent real Schwab package for registration tests."""
    global _REAL_GATE_RECEIPT, _REAL_GATE_TMP
    if _REAL_GATE_RECEIPT is not None:
        return copy.deepcopy(_REAL_GATE_RECEIPT)

    _REAL_GATE_TMP = tempfile.TemporaryDirectory()
    root = Path(_REAL_GATE_TMP.name)
    chain_dir = root / "chains"
    close_dir = root / "closes"
    report_dir = root / "reports" / "2026-08-07"
    chain_dir.mkdir(parents=True)
    close_dir.mkdir(parents=True)
    report_dir.mkdir(parents=True)
    for symbol in _DEFAULT_UNIVERSE:
        frame = _chain_frame()
        frame.to_parquet(chain_dir / f"{symbol}_2026-08-07.parquet")
        pd.DataFrame({"date": ["2026-08-07"], "close": [100.0]}).to_parquet(
            close_dir / f"{symbol}.parquet"
        )

    manifest_path = report_dir / "manifest.json"
    capture_receipt_path = report_dir / "preclose.json"
    built = schwab_chain_manifest.build_manifest(
        "2026-08-07", _DEFAULT_UNIVERSE, chain_dir
    )
    schwab_chain_manifest.write_manifest(built, manifest_path)
    names = {}
    for symbol in _DEFAULT_UNIVERSE:
        path = chain_dir / f"{symbol}_2026-08-07.parquet"
        frame = pd.read_parquet(path)
        names[symbol] = {
            "status": "ok",
            "row_count": len(frame),
            "expiration_count": int(frame["expiration"].nunique()),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    capture_receipt_path.write_text(
        json.dumps(
            {
                "receipt_kind": "schwab_chain_capture/v1",
                "session": "2026-08-07",
                "session_chain_convention": "preclose_snapshot_v1",
                "captured_at_et": "2026-08-07T15:45:00-04:00",
                "scheduled_session_tag": "preclose",
                "force": False,
                "universe": _DEFAULT_UNIVERSE,
                "overall_status": "ok",
                "names": names,
                "manifest_hash": built["manifest_hash"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    result = h7_schwab_data_gate.evaluate(
        date(2026, 8, 8),
        close_dir=close_dir,
        chain_dir=chain_dir,
        manifest_path=manifest_path,
        receipt_path=capture_receipt_path,
        symbols=_DEFAULT_UNIVERSE,
    )
    source_health = make_receipt(
        "source_health",
        {
            "evaluation_session": "2026-08-07",
            "scope": scope_identity(),
            "symbols": {
                symbol: {"healthy": True, "gate": "CLEAR"}
                for symbol in _DEFAULT_UNIVERSE
            },
        },
    )
    source_health_path = report_dir / "source-health.json"
    write_immutable_receipt(source_health, source_health_path)
    _REAL_GATE_RECEIPT = h7_data_gate.build_receipt(
        result,
        source_health_receipt=source_health,
        source_health_receipt_path=source_health_path,
    )
    return copy.deepcopy(_REAL_GATE_RECEIPT)


def feasibility_receipt(**overrides) -> dict:
    payload = {
        "receipt_kind": "h7_schwab_feasibility/v1",
        "provenance": "LLM/tool-computed",
        "lookback_start": "2026-05-08",
        "lookback_end": "2026-08-07",
        "stack_version": "h7-frozen-entry-stack/v1",
        "code_sha": "b" * 40,
        "config_hash": config_hash(),
        "universe": list(_DEFAULT_UNIVERSE),
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


def data_gate_receipt(**overrides) -> dict:
    receipt = _verified_data_gate_receipt()
    payload = {
        key: value
        for key, value in receipt.items()
        if key not in {"receipt_schema", "receipt_type", "receipt_hash"}
    }
    payload.update(overrides)
    return make_receipt("data_gate", payload)


def evidence(**overrides) -> dict:
    receipt = feasibility_receipt()
    gate_receipt = data_gate_receipt()
    values = {
        "review_evidence": "external adversarial review placeholder",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": gate_receipt[
            "source_health_receipt_hash"
        ],
        "data_gate_evidence_id": gate_receipt["receipt_hash"],
        "data_gate_evidence_mode": "REAL-H7-SCHWAB-PRECLOSE-AUDIT",
        "source_health_receipt_hash": gate_receipt["source_health_receipt_hash"],
        "data_gate_receipt": gate_receipt,
        "data_gate_receipt_hash": gate_receipt["receipt_hash"],
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
    def test_durability_evidence_requires_json_boolean_true(self):
        for invalid in ("false", "true", 0, 1, None, False):
            with self.subTest(invalid=invalid):
                with self.assertRaises(registration.RegistrationInputError):
                    registration.build_window_registration_event(
                        owner=owner_inputs(),
                        evidence=evidence(darwin_durability_verified=invalid),
                    )

        event = registration.build_window_registration_event(
            owner=owner_inputs(),
            evidence=evidence(darwin_durability_verified=True),
        )
        self.assertIs(event["payload"]["darwin_durability_verified"], True)

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

    def test_thetadata_evidence_mode_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_evidence_mode="REAL-H7-FULL-AUDIT"),
            )

    def test_data_gate_receipt_mode_mismatch_refuses(self):
        receipt = data_gate_receipt(evidence_mode="REAL-H7-FULL-AUDIT")
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_hash_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_receipt_hash="d" * 64),
            )

    def test_data_gate_evidence_id_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_evidence_id="dg:detached"),
            )

    def test_source_health_evidence_id_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(source_health_evidence_id="sh:detached"),
            )

    def test_fabricated_content_addressed_go_receipt_refuses(self):
        fabricated = data_gate_receipt()
        for field in (
            "symbols",
            "input_files",
            "source_health_receipt_path",
            "source_health_receipt_hash",
            "source_hash",
            "source_hash_contract",
        ):
            fabricated.pop(field, None)
        payload = {
            key: value
            for key, value in fabricated.items()
            if key not in {"receipt_schema", "receipt_type", "receipt_hash"}
        }
        fabricated = make_receipt("data_gate", payload)

        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=fabricated,
                    data_gate_receipt_hash=fabricated["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_config_hash_mismatch_refuses(self):
        receipt = data_gate_receipt(config_hash="0" * 64)
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_universe_name_mismatch_refuses(self):
        tampered = list(_DEFAULT_UNIVERSE)
        tampered[0] = "ZZZZ"
        receipt = data_gate_receipt(universe=tampered)
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_no_go_refuses(self):
        receipt = data_gate_receipt(
            whole_universe_verdict="NO_GO",
            go_count=len(_DEFAULT_UNIVERSE) - 1,
            no_go_count=1,
        )
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_session_mismatch_refuses(self):
        receipt = data_gate_receipt(evaluation_session="2026-08-06")
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
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

    def test_measurement_code_sha_may_precede_registration_commit(self):
        event = registration.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence(code_commit="c" * 40)
        )
        self.assertEqual(
            event["payload"]["feasibility"]["receipt"]["code_sha"],
            "b" * 40,
        )

    # -- adversarial review 2026-08-12, finding B3 -------------------------- #
    # `d77f995` removed the only binding between the feasibility receipt and
    # the code/config that produced it. These tests reconstruct the review's
    # fix: the receipt's config_hash must equal the registering commit's
    # config_hash(), and its universe must be the EXACT name list the
    # registration cohort resolves to (not just the same count).

    def test_feasibility_config_hash_mismatch_refuses(self):
        receipt = feasibility_receipt(config_hash="0" * 64)
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_universe_name_mismatch_refuses(self):
        # Same cardinality (15 names) as the registration cohort, but one
        # name swapped -- the pre-B3-fix cardinality-only check would have
        # let this through silently.
        tampered = list(_DEFAULT_UNIVERSE)
        tampered[0] = "ZZZZ"
        self.assertEqual(len(tampered), len(_DEFAULT_UNIVERSE))
        receipt = feasibility_receipt(universe=tampered)
        with self.assertRaises(registration.RegistrationInputError):
            registration.build_window_registration_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_config_hash_and_universe_match_registers(self):
        event = registration.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence()
        )
        receipt = event["payload"]["feasibility"]["receipt"]
        self.assertEqual(receipt["config_hash"], config_hash())
        self.assertEqual(receipt["universe"], list(_DEFAULT_UNIVERSE))


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
        evidence_values = evidence(
            activation_spec_sha256=self.spec_sha,
            code_commit=self.head,
        )
        return registration.register_window_real(
            owner=owner_inputs(),
            evidence=evidence_values,
            guard_report=self.report,
            spec_sha256=self.spec_sha,
            spec_path=self.spec,
            base_dir=self.store,
            code_state=lambda: (self.head, True),
            recheck_gates=lambda: {
                "source_health_all_healthy": True,
                "data_gate_go": True,
                "source_health_evidence_id": evidence_values[
                    "source_health_evidence_id"
                ],
                "data_gate_evidence_id": evidence_values[
                    "data_gate_evidence_id"
                ],
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

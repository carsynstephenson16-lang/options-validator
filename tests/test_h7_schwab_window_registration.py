"""Synthetic-only tests for the new Schwab H7 registration namespace."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

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
from research.hashing import (
    canonical_json,
    config_hash,
    sha256_file,
    sha256_hex,
    source_hash,
)
from research.receipts import make_receipt, write_immutable_receipt
from tools import schwab_chain_manifest

_DEFAULT_UNIVERSE = old_registration.default_universe_manifest()["included"]
_OWNER_TYPED_COHORT = [
    "AMD",
    "AMZN",
    "CEG",
    "ET",
    "MSFT",
    "NOW",
    "PLTR",
    "TEM",
    "VST",
]
_EXCLUDED = ("AVGO", "CRWV", "IREN", "NVDA", "SMCI", "USAR")
_REAL_GATE_TMP: tempfile.TemporaryDirectory | None = None
_REAL_GATE_RECEIPT: dict | None = None
_INPUT_TMP = tempfile.TemporaryDirectory()
_INPUT_ROOT = Path(_INPUT_TMP.name)


def tearDownModule() -> None:
    _INPUT_TMP.cleanup()


# The validation contract derives paths from the selected cohort and sessions.
# Point only its data-root seam at a temporary panel so this suite never writes
# a cache file into the shared checkout.
registration.FEASIBILITY_DATA_ROOT = _INPUT_ROOT


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
    built = schwab_chain_manifest.build_manifest("2026-08-07", _DEFAULT_UNIVERSE, chain_dir)
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
            "symbols": {symbol: {"healthy": True, "gate": "CLEAR"} for symbol in _DEFAULT_UNIVERSE},
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


def _sessions() -> list[str]:
    first = date(2026, 5, 1)
    return [(first + timedelta(days=offset)).isoformat() for offset in range(70)]


def _fixture_input_files(universe: list[str], sessions: list[str]) -> dict[str, dict]:
    paths = registration._expected_feasibility_input_paths(universe, sessions)
    result = {}
    for label, relative in paths.items():
        path = _INPUT_ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(f"fixture input: {label}\n", encoding="utf-8")
        result[label] = {"path": relative, "sha256": sha256_file(path)}
    return result


def owner_manifest(
    *,
    included: list[str] | None = None,
    excluded: tuple[str, ...] = _EXCLUDED,
    trim_rule: str = "inherited_seq0_cohort_2026-07-20",
) -> dict:
    scope = scope_identity()
    return {
        "scope_id": scope["scope_id"],
        "scope_hash": scope["scope_hash"],
        "included": list(_OWNER_TYPED_COHORT if included is None else included),
        "excluded": [
            {
                "symbol": symbol,
                "reason": f"Owner-typed Schwab-era exclusion for {symbol}",
            }
            for symbol in excluded
        ],
        "trim_rule": trim_rule,
    }


def feasibility_receipt(**overrides) -> dict:
    universe = list(overrides.pop("universe", _OWNER_TYPED_COHORT))
    sessions = list(overrides.pop("sessions", _sessions()))
    passing_pairs = [
        (sessions[0], universe[0]),
        (sessions[10], universe[1]),
        (sessions[20], universe[2]),
    ]
    input_files = overrides.pop("input_files", _fixture_input_files(universe, sessions))
    payload = {
        "receipt_kind": "h7_schwab_feasibility/v1",
        "provenance": "LLM/tool-computed",
        "lookback_start": sessions[0],
        "lookback_end": sessions[-1],
        "stack_version": registration.FEASIBILITY_STACK_VERSION,
        "tool_label": registration.FEASIBILITY_TOOL_LABEL,
        "code_sha": "b" * 40,
        "config_hash": config_hash(),
        "universe": universe,
        "universe_size": len(universe),
        "window_sessions": 70,
        "lookback_sessions": 70,
        "sessions": sessions,
        "symbol_days": len(sessions) * len(universe),
        "full_stack_passes": 3,
        "base_rate": 3 / (len(sessions) * len(universe)),
        "expected_entries": 3.0,
        "occupancy_constrained_expected_entries": 3.0,
        "occupancy_constrained_count": 3,
        "occupancy_lockout_sessions": 42,
        "occupancy_input_rows": [
            {"session": session, "symbol": symbol, "lane": "a"} for session, symbol in passing_pairs
        ],
        "occupancy_upper_bound": True,
        "input_files": input_files,
        "source_paths": list(registration.FEASIBILITY_SOURCE_PATHS),
        "source_hash": source_hash(
            paths=registration.FEASIBILITY_SOURCE_PATHS,
            root=registration.REPO_ROOT,
        ),
        "passing_symbol_days": [
            {"session": session, "symbol": symbol} for session, symbol in passing_pairs
        ],
        "errors": [],
        "error_count": 0,
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
        "SCHWAB_MIN_LOSSES_FOR_VERDICT": 7,
        "SCHWAB_STARVATION_RISK_PREACCEPTANCE": (
            "Owner pre-accepts starvation for this upper-bound estimate; "
            "occupancy_constrained_expected_entries=3"
        ),
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
        "source_health_evidence_id": gate_receipt["source_health_receipt_hash"],
        "data_gate_evidence_id": gate_receipt["receipt_hash"],
        "data_gate_evidence_mode": "REAL-H7-SCHWAB-PRECLOSE-AUDIT",
        "source_health_receipt_hash": gate_receipt["source_health_receipt_hash"],
        "data_gate_receipt": gate_receipt,
        "data_gate_receipt_hash": gate_receipt["receipt_hash"],
        "last_historical_session": "2026-08-07",
        "last_historical_manifest_receipt_hash": gate_receipt["schwab_manifest_hash"],
        "provider_identity": "schwab-read-only/v1",
        "cache_namespace": ".cache/schwab_chains/",
        "feasibility_receipt": receipt,
        "feasibility_receipt_hash": receipt["receipt_hash"],
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    values.update(overrides)
    return values


def build_event(**kwargs) -> dict:
    """Call the builder with the explicit owner-typed manifest by default."""
    kwargs.setdefault("universe_manifest", owner_manifest())
    return registration.build_window_registration_event(**kwargs)


class BuilderTests(unittest.TestCase):
    def test_durability_evidence_requires_json_boolean_true(self):
        for invalid in ("false", "true", 0, 1, None, False):
            with self.subTest(invalid=invalid):
                with self.assertRaises(registration.RegistrationInputError):
                    build_event(
                        owner=owner_inputs(),
                        evidence=evidence(darwin_durability_verified=invalid),
                    )

        event = build_event(
            owner=owner_inputs(),
            evidence=evidence(darwin_durability_verified=True),
        )
        self.assertIs(event["payload"]["darwin_durability_verified"], True)

    def test_builds_new_namespace_with_unchanged_frozen_rules(self):
        event = build_event(owner=owner_inputs(), evidence=evidence())
        payload = event["payload"]
        self.assertEqual(payload["namespace"], "h7-forward-schwab-v1")
        self.assertEqual(payload["provider"]["identity"], "schwab-read-only/v1")
        self.assertEqual(payload["provider"]["cache_namespace"], ".cache/schwab_chains/")
        self.assertEqual(
            payload["provider"]["session_chain_convention"],
            "preclose_snapshot_v1",
        )
        self.assertEqual(payload["frozen"]["scorer"]["min_losses_for_verdict"], 7)
        self.assertEqual(
            payload["frozen"]["stage456_parameters"]["MIN_LOSSES_FOR_VERDICT"],
            7,
        )
        self.assertEqual(payload["history"]["last_session"], "2026-08-07")
        self.assertEqual(
            payload["feasibility"]["receipt"]["provenance"],
            "LLM/tool-computed",
        )

    def test_missing_owner_field_refuses(self):
        owner = owner_inputs()
        del owner["SCHWAB_CONFIRMATION_EVIDENCE"]
        with self.assertRaises(registration.RegistrationInputError):
            build_event(owner=owner, evidence=evidence())

    def test_loss_bar_requires_owner_typed_positive_integer(self):
        missing = owner_inputs()
        del missing["SCHWAB_MIN_LOSSES_FOR_VERDICT"]
        with self.assertRaises(registration.RegistrationInputError):
            build_event(owner=missing, evidence=evidence())

        for invalid in (True, 0, 7.0, "7"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(registration.RegistrationInputError):
                    build_event(
                        owner=owner_inputs(SCHWAB_MIN_LOSSES_FOR_VERDICT=invalid),
                        evidence=evidence(),
                    )

    def test_capture_commitment_short_of_window_end_refuses(self):
        with self.assertRaises(registration.WindowRuleError):
            build_event(
                owner=owner_inputs(SCHWAB_CAPTURE_COMMITMENT_THROUGH="2026-09-01"),
                evidence=evidence(),
            )

    def test_wrong_convention_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(SESSION_CHAIN_CONVENTION="eod_mark_v1"),
                evidence=evidence(),
            )

    def test_thetadata_evidence_mode_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_evidence_mode="REAL-H7-FULL-AUDIT"),
            )

    def test_data_gate_receipt_mode_mismatch_refuses(self):
        receipt = data_gate_receipt(evidence_mode="REAL-H7-FULL-AUDIT")
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_hash_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_receipt_hash="d" * 64),
            )

    def test_data_gate_evidence_id_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(data_gate_evidence_id="dg:detached"),
            )

    def test_source_health_evidence_id_mismatch_refuses(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
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
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=fabricated,
                    data_gate_receipt_hash=fabricated["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_config_hash_mismatch_refuses(self):
        receipt = data_gate_receipt(config_hash="0" * 64)
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_universe_name_mismatch_refuses(self):
        tampered = list(_OWNER_TYPED_COHORT)
        tampered[0] = "ZZZZ"
        receipt = data_gate_receipt(universe=tampered)
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
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
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_data_gate_receipt_session_mismatch_refuses(self):
        receipt = data_gate_receipt(evaluation_session="2026-08-06")
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    data_gate_receipt=receipt,
                    data_gate_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_source_paths_equal_the_recomputed_import_closure(self):
        # Round-3 B1: a hand-curated tuple compared against a hand-copied
        # duplicate cannot detect an omitted dependency. The frozen constant
        # must EQUAL the transitive first-party import closure of the
        # measurement tool, recomputed here from the actual source files
        # (config.py excluded: it is independently content-bound by
        # config_hash()). Adding or removing an import anywhere in that
        # closure fails this test until the constant is deliberately updated.
        recomputed = registration.feasibility_source_closure(registration.REPO_ROOT)
        self.assertEqual(registration.FEASIBILITY_SOURCE_PATHS, recomputed)
        self.assertEqual(recomputed, tuple(sorted(set(recomputed))))
        self.assertIn("tools/h7_schwab_feasibility.py", recomputed)
        self.assertIn("tools/h7_entry_variant_menu.py", recomputed)
        # Modules the round-3 review found reachable but omitted from the
        # hand list: each must now be bound.
        for path in (
            "data/atomic_io.py",
            "data/cache_provenance.py",
            "data/provider_policy.py",
            "research/facts.py",
            "research/receipts.py",
            "options_researcher/h7_scope.py",
            "options_researcher/h7_cohort.py",
            "options_researcher/h7_paper_lifecycle.py",
            "options_researcher/h7_forward_book.py",
            "strategies/h7_backtest.py",
        ):
            self.assertIn(path, recomputed, path)
        self.assertNotIn("config.py", recomputed)
        self.assertFalse(any(path.startswith("tests/") for path in recomputed))

    def test_feasibility_source_closure_walker_follows_transitive_first_party_imports(self):
        # The walker itself is exercised on a synthetic tree so the closure
        # test above is not trusting an untested walker: a -> b -> c via
        # `import`, `from pkg import module`, and `from pkg.module import
        # name`; third-party and unresolvable imports are ignored; a module
        # that is never imported stays out; config.py is excluded.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tools").mkdir()
            (root / "data").mkdir()
            (root / "data" / "__init__.py").write_text("")
            (root / "data" / "sub").mkdir()
            (root / "data" / "sub" / "__init__.py").write_text("")
            (root / "tools" / "entry.py").write_text(
                "import json\nimport config\nfrom data import b\nfrom data.c import thing\n"
                "import data.e\n"
            )
            (root / "data" / "b.py").write_text("import pandas as pd\nfrom data.d import x\n")
            (root / "data" / "c.py").write_text("thing = 1\n")
            (root / "data" / "d.py").write_text("x = 1\n")
            # Round-4 N1: importing data.sub.f also executes data/sub/__init__.py,
            # so the ancestor package file must be bound even though nothing
            # imports it by name.
            (root / "data" / "e.py").write_text("from data.sub.f import w\n")
            (root / "data" / "sub" / "f.py").write_text("w = 1\n")
            (root / "data" / "unused.py").write_text("y = 1\n")
            (root / "config.py").write_text("Z = 1\n")

            closure = registration.feasibility_source_closure(root, entry="tools/entry.py")

        self.assertEqual(
            closure,
            (
                "data/__init__.py",
                "data/b.py",
                "data/c.py",
                "data/d.py",
                "data/e.py",
                "data/sub/__init__.py",
                "data/sub/f.py",
                "tools/entry.py",
            ),
        )

    @staticmethod
    def _copy_bound_surface(root: Path) -> None:
        # Must run BEFORE REPO_ROOT is patched to the temp root.
        for relative in registration.FEASIBILITY_SOURCE_PATHS:
            source = registration.REPO_ROOT / relative
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())

    def _feasibility_receipt_over_copied_surface(self, root: Path):
        input_files = {}
        for label, relative in registration._expected_feasibility_input_paths(
            _OWNER_TYPED_COHORT, _sessions()
        ).items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture input: {label}\n", encoding="utf-8")
            input_files[label] = {"path": relative, "sha256": sha256_file(path)}
        return feasibility_receipt(input_files=input_files)

    def test_feasibility_refuses_a_receipt_listing_a_different_source_surface(self):
        # Round-4 N2: brief W3 requires the tuple-equality refusal to be
        # distinct from the hash refusal -- a receipt that omits one bound
        # dependency must refuse BEFORE any hashing.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_bound_surface(root)
            with (
                mock.patch.object(registration, "REPO_ROOT", root),
                mock.patch.object(registration, "FEASIBILITY_DATA_ROOT", root),
            ):
                receipt = self._feasibility_receipt_over_copied_surface(root)
                receipt["source_paths"] = [
                    path for path in receipt["source_paths"]
                    if path != "options_researcher/h7_signals.py"
                ]
                # Re-seal so the tamper check cannot mask the refusal under test.
                receipt.pop("receipt_hash")
                receipt["receipt_hash"] = sha256_hex(canonical_json(receipt))
                with self.assertRaisesRegex(
                    registration.RegistrationInputError,
                    "source_paths disagrees with the frozen computation surface",
                ):
                    registration._validate_feasibility(receipt, receipt["receipt_hash"])

    def test_feasibility_refuses_when_a_bound_source_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._copy_bound_surface(root)
            with (
                mock.patch.object(registration, "REPO_ROOT", root),
                mock.patch.object(registration, "FEASIBILITY_DATA_ROOT", root),
            ):
                receipt = self._feasibility_receipt_over_copied_surface(root)
                (root / "options_researcher/h7_signals.py").unlink()
                with self.assertRaisesRegex(
                    registration.RegistrationInputError,
                    "computation source path is missing",
                ):
                    registration._validate_feasibility(receipt, receipt["receipt_hash"])

    def test_feasibility_refuses_when_bound_signal_source_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative in registration.FEASIBILITY_SOURCE_PATHS:
                source = registration.REPO_ROOT / relative
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())

            with (
                mock.patch.object(registration, "REPO_ROOT", root),
                mock.patch.object(registration, "FEASIBILITY_DATA_ROOT", root),
            ):
                input_files = {}
                for label, relative in registration._expected_feasibility_input_paths(
                    _OWNER_TYPED_COHORT, _sessions()
                ).items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(f"fixture input: {label}\n", encoding="utf-8")
                    input_files[label] = {"path": relative, "sha256": sha256_file(path)}
                receipt = feasibility_receipt(input_files=input_files)

                signal_source = root / "options_researcher/h7_signals.py"
                signal_source.write_bytes(signal_source.read_bytes() + b"\n# mutation fixture\n")
                with self.assertRaisesRegex(
                    registration.RegistrationInputError, "source hash mismatch"
                ):
                    registration._validate_feasibility(receipt, receipt["receipt_hash"])

    def test_tampered_feasibility_payload_refuses(self):
        receipt = feasibility_receipt()
        receipt["full_stack_passes"] = 999
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_input_hash_mismatch_refuses(self):
        receipt = feasibility_receipt()
        receipt["input_files"]["gating_assertions"]["sha256"] = "0" * 64
        receipt["receipt_hash"] = sha256_hex(
            canonical_json({key: value for key, value in receipt.items() if key != "receipt_hash"})
        )
        with self.assertRaisesRegex(registration.RegistrationInputError, "input hash mismatch"):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_missing_and_absolute_input_paths_refuse(self):
        cases = (
            {"missing": {"path": "missing-input.parquet", "sha256": "0" * 64}},
            {
                "absolute": {
                    "path": str(Path("pyproject.toml").resolve()),
                    "sha256": sha256_file(Path("pyproject.toml")),
                }
            },
        )
        for input_files in cases:
            with self.subTest(input_files=input_files):
                receipt = feasibility_receipt(input_files=input_files)
                with self.assertRaises(registration.RegistrationInputError):
                    build_event(
                        owner=owner_inputs(),
                        evidence=evidence(
                            feasibility_receipt=receipt,
                            feasibility_receipt_hash=receipt["receipt_hash"],
                        ),
                    )

    def test_feasibility_errors_or_wrong_tool_identity_refuse(self):
        for overrides in (
            {"error_count": 1, "errors": [{"error": "fixture"}]},
            {"tool_label": "wrong tool"},
            {"stack_version": "wrong stack"},
        ):
            with self.subTest(overrides=overrides):
                receipt = feasibility_receipt(**overrides)
                with self.assertRaises(registration.RegistrationInputError):
                    build_event(
                        owner=owner_inputs(),
                        evidence=evidence(
                            feasibility_receipt=receipt,
                            feasibility_receipt_hash=receipt["receipt_hash"],
                        ),
                    )

    def test_upper_bound_receipt_requires_canonical_owner_preacceptance(self):
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(
                    SCHWAB_MIN_LOSSES_FOR_VERDICT=1,
                    SCHWAB_STARVATION_RISK_PREACCEPTANCE="",
                ),
                evidence=evidence(),
            )

        event = build_event(owner=owner_inputs(), evidence=evidence())
        self.assertEqual(
            event["payload"]["feasibility"]["occupancy_constrained_expected_entries"],
            3.0,
        )
        self.assertEqual(
            event["payload"]["owner_authorization"]["SCHWAB_STARVATION_RISK_PREACCEPTANCE"],
            owner_inputs()["SCHWAB_STARVATION_RISK_PREACCEPTANCE"],
        )

        for text in (
            "",
            "Owner prose occupancy_constrained_expected_entries=4",
            "Owner prose occupancy_constrained_expected_entries=3.0",
            "occupancy_constrained_expected_entries=3 occupancy_constrained_expected_entries=3",
        ):
            with self.subTest(text=text):
                with self.assertRaises(registration.RegistrationInputError):
                    build_event(
                        owner=owner_inputs(SCHWAB_STARVATION_RISK_PREACCEPTANCE=text),
                        evidence=evidence(),
                    )

    def test_owner_typed_manifest_is_frozen_verbatim(self):
        manifest = owner_manifest()
        event = build_event(owner=owner_inputs(), evidence=evidence(), universe_manifest=manifest)
        self.assertEqual(event["payload"]["universe"], manifest)

    def test_blank_owner_exclusion_reason_refuses(self):
        manifest = owner_manifest()
        manifest["excluded"][0]["reason"] = "  "
        with self.assertRaisesRegex(registration.RegistrationInputError, "blank exclusion reason"):
            build_event(owner=owner_inputs(), evidence=evidence(), universe_manifest=manifest)

    def test_preacceptance_mismatch_names_both_numbers(self):
        """Round-1 F5: WP-B requires the receipt figure AND the owner's."""
        with self.assertRaises(registration.RegistrationInputError) as caught:
            build_event(
                owner=owner_inputs(
                    SCHWAB_STARVATION_RISK_PREACCEPTANCE=(
                        "Owner prose occupancy_constrained_expected_entries=4"
                    )
                ),
                evidence=evidence(),
            )
        message = str(caught.exception)
        self.assertIn("3", message)  # the receipt's occupancy-constrained figure
        self.assertIn("4", message)  # the number the owner's text quotes

    def test_measurement_code_sha_may_precede_registration_commit(self):
        event = build_event(owner=owner_inputs(), evidence=evidence(code_commit="c" * 40))
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
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_universe_name_mismatch_refuses(self):
        # Same cardinality (9 names) as the registration cohort, but one
        # name swapped -- the pre-B3-fix cardinality-only check would have
        # let this through silently.
        tampered = list(_OWNER_TYPED_COHORT)
        tampered[0] = "ZZZZ"
        self.assertEqual(len(tampered), len(_OWNER_TYPED_COHORT))
        receipt = feasibility_receipt(universe=tampered)
        with self.assertRaises(registration.RegistrationInputError):
            build_event(
                owner=owner_inputs(),
                evidence=evidence(
                    feasibility_receipt=receipt,
                    feasibility_receipt_hash=receipt["receipt_hash"],
                ),
            )

    def test_feasibility_config_hash_and_universe_match_registers(self):
        event = build_event(owner=owner_inputs(), evidence=evidence())
        receipt = event["payload"]["feasibility"]["receipt"]
        self.assertEqual(receipt["config_hash"], config_hash())
        self.assertEqual(receipt["universe"], list(_OWNER_TYPED_COHORT))


class SyntheticAppendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "h7_forward_schwab"

    def test_happy_path_registers_and_verifies_temp_store(self):
        result = registration.register_window(
            owner=owner_inputs(),
            evidence=evidence(),
            base_dir=self.store,
            universe_manifest=owner_manifest(),
        )
        self.assertEqual(result.seq, 0)
        verified = ledger.verify(self.store)
        self.assertTrue(verified.valid)
        self.assertEqual(verified.count, 1)

    def test_non_empty_target_refuses(self):
        registration.register_window(
            owner=owner_inputs(),
            evidence=evidence(),
            base_dir=self.store,
            universe_manifest=owner_manifest(),
        )
        with self.assertRaises(ledger.LedgerHeadConflictError):
            registration.register_window(
                owner=owner_inputs(),
                evidence=evidence(),
                base_dir=self.store,
                universe_manifest=owner_manifest(),
            )


class GuardedDoorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name) / "h7_forward_schwab"
        self.spec = registration.SCHWAB_ACTIVATION_SPEC_PATH
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
                "source_health_evidence_id": evidence_values["source_health_evidence_id"],
                "data_gate_evidence_id": evidence_values["data_gate_evidence_id"],
            },
            universe_manifest=owner_manifest(),
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

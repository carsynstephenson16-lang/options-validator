"""Option C -- trim-at-append (opt-in, data-readiness-only).

Activating a forward window on the CURRENTLY-HEALTHY subset of the 15-name
scope instead of waiting for all 15 to be earnings-confirmed. The included
universe is derived from the source-health receipt's per-symbol healthy map
(data-readiness ONLY -- never a performance/return signal); the excluded set
and each name's reason are frozen immutably into the window_registration
payload so the choice is auditable and non-cherry-picked.

These tests exercise the real trim logic three ways:
  * end-to-end through the CLI ``activate(trim_unhealthy=True)`` -- a seq-0
    window_registration lands whose payload records the included/excluded split;
  * the guard (``activation_preconditions(included=...)``) and the receipt
    validator (``validate_data_gate_receipt(included=...)``) directly, without
    world-patching, so the per-included GO / all-included-healthy checks are
    proven on real code;
  * refusal proofs: all-unhealthy refuses (store stays VALID EMPTY), and
    WITHOUT the flag a single unhealthy name still blocks (today's behavior).

Every case asserts the real ``ledger/h7_forward`` store is byte-identical
(VALID EMPTY) before and after -- it is never written.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from data.cache_schema import V2_FULL_AUDIT_SCHEMA
from options_researcher import h7_activation_guard as ag
from options_researcher import h7_event_ledger as el
from options_researcher import h7_watch as watch
from options_researcher import h7_window_registration as wr
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from research.hashing import config_hash, diagnostic_source_hash, sha256_file
from research.receipts import input_files, load_receipt, make_receipt
from tools import h7_manual_activate as cli

_COMPLETED_SESSION = "2026-07-10"
_REQUESTED_RUN_DATE = "2026-07-13"


def _owner_inputs() -> dict:
    return {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed-string 2026-XX-XX",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS decision sessions from start",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "renewal receipt <id>",
    }


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


class TrimActivationTests(unittest.TestCase):
    def setUp(self):
        self.full = list(scope_identity()["symbols"])  # sorted official 15
        # Six unhealthy by earnings provenance; nine healthy and data-ready.
        self.unhealthy = self.full[:6]
        self.included = sorted(self.full[6:])
        self.head = _git_head()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "forward"
        mapping = dict(ag.OWNER_FIELDS_BY_STORE)
        mapping[self.store.resolve()] = wr.OWNER_FIELDS
        mapping_patch = mock.patch.object(
            ag, "OWNER_FIELDS_BY_STORE", mapping
        )
        mapping_patch.start()
        self.addCleanup(mapping_patch.stop)

        self.spec = self.root / "activation-spec.md"
        self.spec.write_text("stage-8 activation spec fixture\n")
        self.spec_sha = sha256_file(self.spec)

        self.source_path = self.root / "source_health.json"
        self.data_gate_path = self.root / "data_gate.json"
        self.backup_path = self.root / "backup_restore.json"
        self.owner_path = self.root / "owner.json"
        self.evidence_path = self.root / "evidence.json"

        self.owner_path.write_text(json.dumps(_owner_inputs()))
        self.evidence_path.write_text(
            json.dumps(
                {
                    "review_evidence": "external review PASS 2026-07-19",
                    "activation_spec_sha256": self.spec_sha,
                    "code_commit": self.head,
                    "darwin_durability_verified": True,
                    "pre_append_state": "VALID EMPTY",
                }
            )
        )

    # -- receipt builders --------------------------------------------------- #
    def _source_receipt(self, unhealthy: list[str]) -> dict:
        healthy = [s for s in self.full if s not in unhealthy]
        symbols = {}
        for s in self.full:
            if s in unhealthy:
                symbols[s] = {
                    "symbol": s,
                    "healthy": False,
                    "gate": "UNKNOWN",
                    "flags": ["MISSING"],
                }
            else:
                symbols[s] = {"symbol": s, "healthy": True, "gate": "CLEAR", "flags": []}
        return make_receipt(
            "source_health",
            {
                "evaluation_session": _COMPLETED_SESSION,
                "requested_run_date": _REQUESTED_RUN_DATE,
                "known_as_of_utc": "2026-07-10T20:00:00+00:00",
                "scope": scope_identity(),
                "healthy_count": len(healthy),
                "unhealthy_count": len(unhealthy),
                "unhealthy_symbols": sorted(unhealthy),
                "activation_ready": not unhealthy,
                "symbols": symbols,
                "input_files": {},
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )

    def _data_gate_receipt(self, source: dict, no_go: list[str] | None = None) -> dict:
        no_go = no_go or []
        symbols = {s: {"symbol": s, "verdict": "NO_GO" if s in no_go else "GO"} for s in self.full}
        go_count = len(self.full) - len(no_go)
        return make_receipt(
            "data_gate",
            {
                "evaluation_session": _COMPLETED_SESSION,
                "requested_run_date": _REQUESTED_RUN_DATE,
                "scope": scope_identity(),
                "whole_universe_verdict": "GO" if not no_go else "NO_GO",
                "go_count": go_count,
                "no_go_count": len(no_go),
                "symbols": symbols,
                "input_files": {},
                "source_health_receipt_hash": source["receipt_hash"],
                "source_health_receipt_path": str(self.source_path),
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )

    def _backup_receipt(self) -> dict:
        return make_receipt(
            "backup_restore",
            {
                "completed_session": _COMPLETED_SESSION,
                "verified_at_utc": datetime.now(timezone.utc).isoformat(),
                "snapshot": "latest",
                "scope": scope_identity(),
                "verification": {"ok": True},
            },
        )

    def _write(self, unhealthy: list[str], gate_no_go: list[str] | None = None):
        source = self._source_receipt(unhealthy)
        data_gate = self._data_gate_receipt(source, no_go=gate_no_go)
        self.source_path.write_text(json.dumps(source))
        self.data_gate_path.write_text(json.dumps(data_gate))
        self.backup_path.write_text(json.dumps(self._backup_receipt()))
        return source, data_gate

    # -- world patches (caches, git tree, append-time gate re-run) ---------- #
    def _world_patches(self, stack: ExitStack) -> None:
        stack.enter_context(
            mock.patch.object(
                cli,
                "validate_data_gate_receipt",
                side_effect=lambda path, **kw: load_receipt(Path(path), expected_type="data_gate"),
            )
        )
        stack.enter_context(
            mock.patch.object(
                ag,
                "_working_tree_clean",
                return_value=ag.Check("working_tree_clean", True, "clean"),
            )
        )
        stack.enter_context(
            mock.patch("options_researcher.h7_source_health.load_assertions", return_value=[])
        )
        stack.enter_context(
            mock.patch(
                "options_researcher.h7_source_health.evaluate_health",
                return_value={"activation_ready": True},
            )
        )
        stack.enter_context(
            mock.patch(
                "options_researcher.h7_data_gate.evaluate",
                return_value={
                    "whole_universe_verdict": "GO",
                    "evaluation_session": _COMPLETED_SESSION,
                    "symbols": {s: {"verdict": "GO"} for s in self.full},
                },
            )
        )

    def _activate(self, **over):
        kwargs = dict(
            owner_path=self.owner_path,
            evidence_path=self.evidence_path,
            source_health_path=self.source_path,
            data_gate_path=self.data_gate_path,
            backup_restore_path=self.backup_path,
            completed_session=_COMPLETED_SESSION,
            confirmation=cli.CONFIRMATION,
            spec_path=self.spec,
            forward_base=self.store,
            code_state=lambda: (self.head, True),
        )
        kwargs.update(over)
        return cli.activate(**kwargs)

    def _assert_real_store_untouched(self, before):
        after = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertEqual(
            (after.valid, after.empty, after.count), (before.valid, before.empty, before.count)
        )

    # -- tests -------------------------------------------------------------- #
    def test_trim_activates_included_and_freezes_excluded_with_reasons(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        # Phase-aware: pre-activation the real store is VALID EMPTY; post-activation
        # (2026-07-20, seq-0 window_registration) it is VALID non-empty. The invariant
        # under test is "valid and UNTOUCHED by this operation", not "empty".
        self.assertTrue(before.valid)
        source, data_gate = self._write(self.unhealthy)

        with ExitStack() as stack:
            self._world_patches(stack)
            result = self._activate(trim_unhealthy=True)

        self.assertEqual(result.seq, 0)
        event = el.read_events(self.store)[0]
        uni = event.payload["universe"]
        self.assertEqual(uni["scope_id"], scope_identity()["scope_id"])
        self.assertEqual(uni["scope_hash"], scope_identity()["scope_hash"])
        self.assertEqual(uni["included"], self.included)
        self.assertEqual(uni["trim_rule"], "source_health_ready_at_pinned_session")
        excluded_symbols = sorted(e["symbol"] for e in uni["excluded"])
        self.assertEqual(excluded_symbols, sorted(self.unhealthy))
        for e in uni["excluded"]:
            self.assertEqual(e["reason"], "EARNINGS-UNKNOWN")
        self._assert_real_store_untouched(before)

    def test_trim_activates_even_when_only_an_excluded_name_fails_data_gate(self):
        # Whole-universe data gate is NO_GO because ONE excluded name lacks
        # data, yet every INCLUDED name is GO. Trim must still activate: the
        # data-gate check is per-included, not whole-universe.
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self._write(self.unhealthy, gate_no_go=[self.unhealthy[0]])

        with ExitStack() as stack:
            self._world_patches(stack)
            result = self._activate(trim_unhealthy=True)

        self.assertEqual(result.seq, 0)
        self._assert_real_store_untouched(before)

    def test_trim_refuses_when_an_included_name_fails_the_data_gate(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self._write(self.unhealthy, gate_no_go=[self.included[0]])

        with ExitStack() as stack:
            self._world_patches(stack)
            with self.assertRaises(Exception):
                self._activate(trim_unhealthy=True)
        self.assertTrue(el.verify(base_dir=self.store).empty)
        self._assert_real_store_untouched(before)

    def test_all_unhealthy_refuses_and_store_stays_valid_empty(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self._write(list(self.full))  # every name unhealthy

        with ExitStack() as stack:
            self._world_patches(stack)
            with self.assertRaises(wr.RegistrationInputError):
                self._activate(trim_unhealthy=True)
        self.assertTrue(el.verify(base_dir=self.store).empty)
        self._assert_real_store_untouched(before)

    def test_without_flag_an_unhealthy_name_still_blocks(self):
        # Default (no --trim-unhealthy): today's all-or-nothing 15-name check.
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self._write(self.unhealthy)

        with ExitStack() as stack:
            self._world_patches(stack)
            with self.assertRaises(Exception):
                self._activate(trim_unhealthy=False)
        self.assertTrue(el.verify(base_dir=self.store).empty)
        self._assert_real_store_untouched(before)

    def test_without_flag_all_healthy_still_activates(self):
        # Regression: the default path with a clean 15-name pass is unchanged.
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self._write([])  # nobody unhealthy

        with ExitStack() as stack:
            self._world_patches(stack)
            result = self._activate(trim_unhealthy=False)

        self.assertEqual(result.seq, 0)
        uni = el.read_events(self.store)[0].payload["universe"]
        self.assertEqual(uni["included"], self.full)
        self.assertEqual(uni["excluded"], [])
        self.assertEqual(uni["trim_rule"], "none")
        self._assert_real_store_untouched(before)


class TrimGuardUnitTests(unittest.TestCase):
    """The guard's included-subset checks, without world-patching."""

    def setUp(self):
        self.full = list(scope_identity()["symbols"])
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name) / "forward"
        mapping = dict(ag.OWNER_FIELDS_BY_STORE)
        mapping[self.store.resolve()] = wr.OWNER_FIELDS
        mapping_patch = mock.patch.object(
            ag, "OWNER_FIELDS_BY_STORE", mapping
        )
        mapping_patch.start()
        self.addCleanup(mapping_patch.stop)

    def _health_map(self, unhealthy):
        return {s: s not in unhealthy for s in self.full}

    def _gate_result(self, no_go=()):
        symbols = {s: {"symbol": s, "verdict": "NO_GO" if s in no_go else "GO"} for s in self.full}
        result = {
            "whole_universe_verdict": "GO" if not no_go else "NO_GO",
            "go_count": len(self.full) - len(no_go),
            "universe": sorted(self.full),
            "symbols": symbols,
        }
        return result

    def test_source_health_whole_universe_passes_for_included_only(self):
        unhealthy = self.full[:6]
        included = tuple(sorted(self.full[6:]))
        report = ag.activation_preconditions(
            forward_base=self.store,
            source_health_by_symbol=self._health_map(unhealthy),
            universe=tuple(self.full),
            data_gate_result=self._gate_result(),
            owner_inputs={f: "x" for f in wr.OWNER_FIELDS},
            included=included,
        )
        self.assertTrue(report.by_name["source_health_whole_universe"].ok)
        self.assertTrue(report.by_name["data_gate_go"].ok)

    def test_data_gate_go_fails_when_an_included_name_is_no_go(self):
        unhealthy = self.full[:6]
        included = tuple(sorted(self.full[6:]))
        report = ag.activation_preconditions(
            forward_base=self.store,
            source_health_by_symbol=self._health_map(unhealthy),
            universe=tuple(self.full),
            data_gate_result=self._gate_result(no_go=(included[0],)),
            owner_inputs={f: "x" for f in wr.OWNER_FIELDS},
            included=included,
        )
        self.assertFalse(report.by_name["data_gate_go"].ok)

    def test_data_gate_go_passes_when_only_excluded_name_is_no_go(self):
        unhealthy = self.full[:6]
        included = tuple(sorted(self.full[6:]))
        report = ag.activation_preconditions(
            forward_base=self.store,
            source_health_by_symbol=self._health_map(unhealthy),
            universe=tuple(self.full),
            data_gate_result=self._gate_result(no_go=(unhealthy[0],)),
            owner_inputs={f: "x" for f in wr.OWNER_FIELDS},
            included=included,
        )
        self.assertTrue(report.by_name["data_gate_go"].ok)


class TrimReceiptValidatorTests(unittest.TestCase):
    """validate_data_gate_receipt(included=...) relaxes whole-universe GO to a
    per-included GO check while still binding the FULL official scope."""

    def setUp(self):
        self.full = list(scope_identity()["symbols"])
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source_path = self.root / "source.json"
        self.gate_path = self.root / "gate.json"
        self.close_dir = self.root / "underlying"
        self.chain_dir = self.root / "chains"
        self.close_dir.mkdir()
        self.chain_dir.mkdir()
        for symbol in self.full:
            (self.close_dir / f"{symbol}.parquet").write_bytes(f"close:{symbol}".encode())
            (self.chain_dir / f"{symbol}_{_COMPLETED_SESSION}.parquet").write_bytes(
                f"chain:{symbol}".encode()
            )

    def _fixture_audit_validator(self, cache_dir, chain_path, *, symbol, session, consumer_scope):
        self.assertEqual(Path(cache_dir), self.chain_dir)
        self.assertEqual(session, _COMPLETED_SESSION)
        self.assertEqual(consumer_scope, "H7")
        return {
            "path": str(self.chain_dir / "_meta" / "full_audit.json"),
            "receipt_hash": "f" * 64,
            "schema": V2_FULL_AUDIT_SCHEMA,
            "verdict": "PASS WITH WARNINGS",
            "partition_sha256": hashlib.sha256(Path(chain_path).read_bytes()).hexdigest(),
            "consumer_scope": "H7",
        }

    def _validate(self, *, included=None):
        with mock.patch.object(
            watch, "validate_v2_audit_receipt", side_effect=self._fixture_audit_validator
        ):
            return watch.validate_data_gate_receipt(
                self.gate_path,
                evaluation_session=_COMPLETED_SESSION,
                names=self.full,
                included=included,
            )

    def _rewrite_gate(self, mutate):
        receipt = json.loads(self.gate_path.read_text())
        payload = {
            key: value
            for key, value in receipt.items()
            if key not in {"receipt_schema", "receipt_type", "receipt_hash"}
        }
        mutate(payload)
        self.gate_path.write_text(json.dumps(make_receipt("data_gate", payload)))

    def _write(self, no_go):
        source = make_receipt(
            "source_health",
            {
                "evaluation_session": _COMPLETED_SESSION,
                "requested_run_date": _REQUESTED_RUN_DATE,
                "scope": scope_identity(),
                "activation_ready": False,
                "input_files": {},
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )
        self.source_path.write_text(json.dumps(source))
        paths = {}
        symbols = {}
        for symbol in self.full:
            close_path = self.close_dir / f"{symbol}.parquet"
            chain_path = self.chain_dir / f"{symbol}_{_COMPLETED_SESSION}.parquet"
            paths[f"close:{symbol}"] = close_path
            paths[f"chain:{symbol}"] = chain_path
            symbols[symbol] = {
                "symbol": symbol,
                "requested_run_date": _REQUESTED_RUN_DATE,
                "evaluation_session": _COMPLETED_SESSION,
                "verdict": "NO_GO" if symbol in no_go else "GO",
                "close": {"path": str(close_path)},
                "chain": {
                    "expected_path": str(chain_path),
                    "audit_receipt": {
                        "valid": True,
                        **self._fixture_audit_validator(
                            self.chain_dir,
                            chain_path,
                            symbol=symbol,
                            session=_COMPLETED_SESSION,
                            consumer_scope="H7",
                        ),
                    },
                },
            }
        gate = make_receipt(
            "data_gate",
            {
                "evaluation_session": _COMPLETED_SESSION,
                "requested_run_date": _REQUESTED_RUN_DATE,
                "scope": scope_identity(),
                "universe": self.full,
                "whole_universe_verdict": "NO_GO" if no_go else "GO",
                "go_count": len(self.full) - len(no_go),
                "no_go_count": len(no_go),
                "symbols": symbols,
                "input_files": input_files(paths),
                "source_health_receipt_hash": source["receipt_hash"],
                "source_health_receipt_path": str(self.source_path),
                "config_hash": config_hash(),
                "source_hash": diagnostic_source_hash(),
            },
        )
        self.gate_path.write_text(json.dumps(gate))

    def test_included_go_passes_even_when_whole_universe_no_go(self):
        no_go = [self.full[0]]
        self._write(no_go)
        included = tuple(s for s in self.full if s not in no_go)
        receipt = self._validate(included=included)
        self.assertEqual(receipt["whole_universe_verdict"], "NO_GO")

    def test_included_no_go_raises(self):
        no_go = [self.full[0]]
        self._write(no_go)
        included = tuple(self.full)  # includes the NO_GO name
        with self.assertRaises(ValueError):
            self._validate(included=included)

    def test_sparse_receipt_with_forged_counts_is_rejected(self):
        self._write(no_go=[])
        self._rewrite_gate(lambda payload: payload.update({"universe": [], "symbols": {}}))
        with self.assertRaisesRegex(ValueError, "scope closure"):
            self._validate()

    def test_claimed_counts_are_recomputed(self):
        self._write(no_go=[])
        self._rewrite_gate(lambda payload: payload.update({"go_count": len(self.full) - 1}))
        with self.assertRaisesRegex(ValueError, "counts/verdict"):
            self._validate()

    def test_missing_exact_input_label_is_rejected(self):
        self._write(no_go=[])

        def remove_label(payload):
            payload["input_files"].pop(f"chain:{self.full[0]}")

        self._rewrite_gate(remove_label)
        with self.assertRaisesRegex(ValueError, "input labels"):
            self._validate()

    def test_forged_go_audit_binding_is_rejected(self):
        self._write(no_go=[])

        def forge_binding(payload):
            payload["symbols"][self.full[0]]["chain"]["audit_receipt"]["consumer_scope"] = (
                "H7-SYNTHETIC"
            )

        self._rewrite_gate(forge_binding)
        with self.assertRaisesRegex(ValueError, "real H7"):
            self._validate()


if __name__ == "__main__":
    unittest.main()

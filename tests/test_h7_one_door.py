"""One-door registration reconciliation plus typed post-registration writers.

Each namespace's ``register_window_real`` is the only path allowed to create
its seq-0 registration. ``tools/h7_manual_activate.py`` remains the only caller
for the legacy real H7 forward store. The
later real exit/scoring arc intentionally adds factory-issued, receipt-gated
append paths after registration; those are distinct typed doors, not alternate
activation paths.

What the STRUCTURAL (AST) scan below actually proves -- and what it does NOT:
  * It PROVES that, across the scanned source roots, no module makes a direct
    ``append_event`` call whose ``base_dir`` is REAL_FORWARD_STORE (literally
    or via an in-function alias / default-parameter alias), and that the CLI
    makes no ``append_event`` call at all. In other words: no source-level
    second door that names the real store.
  * It does NOT, by itself, prove "exactly one runtime path writes the real
    store." ``register_window_real`` legitimately appends to whatever
    ``base_dir`` it is handed (the CLI hands it REAL_FORWARD_STORE via a
    default), and a static scan cannot follow that value at runtime. The
    registration guarantee is carried by RUNTIME guards, not this scan:
    ``expected_head=None`` makes a concurrent/second seq-0 write lose, and the
    append-time VALID-EMPTY re-verify inside ``register_window_real`` refuses
    if the store is not empty. Post-registration writers must separately earn
    their typed authority and can never create or replace seq 0. The scan is
    the source-level tripwire that keeps a NEW direct named-store door from
    being added silently.

Four proofs:
  (a) structural scan: no scanned module appends to REAL_FORWARD_STORE (direct,
      aliased, or default-parameter alias), and the CLI contains no
      ``append_event`` call at all;
  (b) end-to-end synthetic activation through the CLI ``activate`` -- a seq-0
      window_registration lands with the receipt hashes in its payload;
  (c) a receipt-hash mismatch discovered INSIDE the CLI's append-time
      ``recheck_gates`` refuses through the one door and writes nothing;
  (d) revert-proof: the same scanners, fed a CLI that regained a direct or
      alias-laundered ``append_event(..., base_dir=REAL_FORWARD_STORE, ...)``,
      flag it.
"""
from __future__ import annotations

import ast
import json
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from options_researcher import h7_activation_guard as ag
from options_researcher import h7_event_ledger as el
from options_researcher import h7_window_registration as wr
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from research.hashing import config_hash, diagnostic_source_hash, sha256_file
from research.receipts import load_receipt, make_receipt
from tools import h7_manual_activate as cli

_SCAN_ROOTS = (Path("options_researcher"), Path("tools"), Path("research"),
               Path("data"), Path("harness"))
_LEDGER_MODULE = "h7_event_ledger.py"  # defines append_event; not a caller


# --------------------------------------------------------------------------- #
# Shared AST scanners (used by the structural proofs AND the revert-proof test)
# --------------------------------------------------------------------------- #
def _calls_named(node: ast.AST, name: str) -> bool:
    """True if any Call under ``node`` invokes ``name`` (bare or as attribute)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Attribute) and func.attr == name:
                return True
            if isinstance(func, ast.Name) and func.id == name:
                return True
    return False


def _has_append_call(source: str) -> bool:
    """True if the source contains an ``append_event(...)`` invocation."""
    return _calls_named(ast.parse(source), "append_event")


def _real_store_constructor_functions(source: str) -> list[str]:
    """Functions that construct a real-store-CAPABLE append base.

    A function qualifies when it (1) calls ``append_event``, (2) builds a
    ``Path`` (i.e. constructs its own base rather than inheriting an already
    -guarded one from a caller), and (3) does NOT route that base through
    ``_synthetic_base`` -- the guard that refuses REAL_FORWARD_STORE. This is
    exactly ``register_window_real``'s shape (``base = Path(base_dir)`` with no
    synthetic guard); ``register_window`` and every lifecycle/book/proof appender
    either call ``_synthetic_base`` in-function or inherit a guarded base without
    calling ``Path`` themselves, so they do not qualify.
    """
    out = []
    for fn in ast.walk(ast.parse(source)):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if (_calls_named(fn, "append_event")
                    and _calls_named(fn, "Path")
                    and not _calls_named(fn, "_synthetic_base")):
                out.append(fn.name)
    return out


def _is_real_store_ref(node: ast.AST) -> bool:
    """A bare reference to REAL_FORWARD_STORE (Name or attribute access), NOT a
    derivation of it such as ``REAL_FORWARD_STORE.resolve()`` (that is a Call)."""
    return ((isinstance(node, ast.Name) and node.id == "REAL_FORWARD_STORE")
            or (isinstance(node, ast.Attribute)
                and node.attr == "REAL_FORWARD_STORE"))


def _real_store_alias_names(fn: ast.AST) -> set[str]:
    """Names bound inside ``fn`` to a bare REAL_FORWARD_STORE reference -- via a
    default parameter value (``def f(base=REAL_FORWARD_STORE)``) or a local
    assignment (``base = REAL_FORWARD_STORE``). A value DERIVED from it (e.g.
    ``REAL_FORWARD_STORE.resolve()``) is a Call, not a bare ref, so it does not
    launder into the real store for append purposes and is not treated as an
    alias."""
    aliases: set[str] = set()
    if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        a = fn.args
        positional = a.posonlyargs + a.args
        offset = len(positional) - len(a.defaults)
        for i, default in enumerate(a.defaults):
            if _is_real_store_ref(default):
                aliases.add(positional[offset + i].arg)
        for arg, default in zip(a.kwonlyargs, a.kw_defaults):
            if default is not None and _is_real_store_ref(default):
                aliases.add(arg.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Assign) and _is_real_store_ref(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases.add(target.id)
        if (isinstance(node, ast.AnnAssign) and node.value is not None
                and _is_real_store_ref(node.value)
                and isinstance(node.target, ast.Name)):
            aliases.add(node.target.id)
    return aliases


def _appends_to_real_store(source: str) -> bool:
    """True if any function in ``source`` makes an ``append_event`` call whose
    ``base_dir`` is the real store -- either literally REAL_FORWARD_STORE, or a
    name that aliases it (in-function assignment OR default parameter). Catches
    both the old two-door literal (``base_dir=REAL_FORWARD_STORE``) and an
    alias-laundered evasion (``def f(base=REAL_FORWARD_STORE): append_event(
    ..., base_dir=base)``)."""
    tree = ast.parse(source)
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        aliases = _real_store_alias_names(fn)
        for sub in ast.walk(fn):
            if not (isinstance(sub, ast.Call)
                    and ((isinstance(sub.func, ast.Attribute)
                          and sub.func.attr == "append_event")
                         or (isinstance(sub.func, ast.Name)
                             and sub.func.id == "append_event"))):
                continue
            candidates = list(sub.args)
            candidates += [kw.value for kw in sub.keywords if kw.arg == "base_dir"]
            for val in candidates:
                if _is_real_store_ref(val):
                    return True
                if isinstance(val, ast.Name) and val.id in aliases:
                    return True
    # Module-level append at import time (no enclosing function) -- defensive.
    for sub in ast.walk(tree):
        if (isinstance(sub, ast.Call)
                and ((isinstance(sub.func, ast.Attribute)
                      and sub.func.attr == "append_event")
                     or (isinstance(sub.func, ast.Name)
                         and sub.func.id == "append_event"))):
            for val in list(sub.args) + [kw.value for kw in sub.keywords
                                         if kw.arg == "base_dir"]:
                if _is_real_store_ref(val):
                    return True
    return False


def _module_sources() -> dict[str, str]:
    srcs = {}
    for root in _SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts or path.name == _LEDGER_MODULE:
                continue
            srcs[str(path)] = path.read_text()
    return srcs


class StructuralOneDoorTests(unittest.TestCase):
    def test_each_namespace_has_one_unguarded_registration_constructor(self):
        # NOTE: this proves each ``register_window_real`` is the only function that
        # BUILDS its own append base without the ``_synthetic_base`` refusal --
        # i.e. the only one structurally CAPABLE of appending to whatever store
        # it is handed. It does not (and cannot statically) prove exactly one
        # runtime writer; post-registration typed writers inherit a validated
        # base and are covered by the separate guard proof below.
        offenders = {name: _real_store_constructor_functions(src)
                     for name, src in _module_sources().items()}
        with_constructor = {name: fns for name, fns in offenders.items() if fns}
        self.assertEqual(
            with_constructor,
            {
                "options_researcher/h7_schwab_window_registration.py": [
                    "register_window_real"
                ],
                "options_researcher/h7_window_registration.py": [
                    "register_window_real"
                ],
            },
            "only one register_window_real per namespace may construct an "
            "unguarded seq-0 append base",
        )

    def test_post_registration_typed_writers_keep_runtime_guards(self):
        sources = _module_sources()
        exit_source = sources["options_researcher/h7_exit_session.py"]
        lifecycle_source = sources["options_researcher/h7_paper_lifecycle.py"]
        scoring_source = sources["options_researcher/h7_real_scoring.py"]

        self.assertIn("_revalidate(session)", exit_source)
        self.assertIn("_validate_bound_transition_inputs", lifecycle_source)
        self.assertIn("_resolve_exit_base", lifecycle_source)
        self.assertIn("_revalidate(session)", scoring_source)
        self.assertIn("_require_review_passes(session)", scoring_source)

    def test_cli_never_appends_directly(self):
        cli_src = Path("tools/h7_manual_activate.py").read_text()
        # The CLI must contain NO append_event call: it routes through the one
        # door. (This is the primary revert guard -- see the (d) test below.)
        self.assertFalse(_has_append_call(cli_src),
                         "h7_manual_activate must not call append_event")
        # ...and it must call the one door.
        self.assertIn("register_window_real", cli_src)

    def test_schwab_cli_never_appends_directly(self):
        cli_src = Path("tools/h7_schwab_manual_activate.py").read_text()
        self.assertFalse(
            _has_append_call(cli_src),
            "h7_schwab_manual_activate must not call append_event",
        )
        self.assertIn("register_window_real", cli_src)

    def test_no_module_appends_to_the_real_store(self):
        # No scanned module may append_event to REAL_FORWARD_STORE, whether
        # literally or via an in-function / default-parameter alias.
        for name, src in _module_sources().items():
            self.assertFalse(
                _appends_to_real_store(src),
                f"{name} appends to REAL_FORWARD_STORE (direct or aliased)")

    def test_revert_to_a_direct_or_aliased_cli_append_is_caught(self):
        # (d) Revert-proof: reconstruct BOTH evasions and prove the SAME
        # scanners the structural tests use would flag them. If a future edit
        # reintroduces either, test_cli_never_appends_directly (via
        # _has_append_call) AND test_no_module_appends_to_the_real_store (via
        # _appends_to_real_store) fail.
        direct = (
            "from options_researcher import h7_event_ledger as ledger\n"
            "from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE\n"
            "def activate(event):\n"
            "    return ledger.append_event(event, base_dir=REAL_FORWARD_STORE,\n"
            "                               expected_head=None)\n"
        )
        # Alias-laundered: base_dir=name whose default is REAL_FORWARD_STORE.
        aliased = (
            "from options_researcher import h7_event_ledger as ledger\n"
            "from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE\n"
            "def activate(event, base=REAL_FORWARD_STORE):\n"
            "    return ledger.append_event(event, base_dir=base,\n"
            "                               expected_head=None)\n"
        )
        for regressed in (direct, aliased):
            self.assertTrue(_has_append_call(regressed))
            self.assertTrue(_appends_to_real_store(regressed))
        # And the current CLI is clean under both -- its forward_base=
        # REAL_FORWARD_STORE default is NOT flagged because activate makes no
        # append_event call (it hands the base to the one door instead).
        cli_src = Path("tools/h7_manual_activate.py").read_text()
        self.assertFalse(_has_append_call(cli_src))
        self.assertFalse(_appends_to_real_store(cli_src))


# --------------------------------------------------------------------------- #
# End-to-end activation harness (synthetic: temp store, temp receipts, temp spec)
# --------------------------------------------------------------------------- #
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
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


class ActivationOneDoorTests(unittest.TestCase):
    def setUp(self):
        self.names = list(scope_identity()["symbols"])
        self.head = _git_head()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "forward"

        self.spec = self.root / "activation-spec.md"
        self.spec.write_text("stage-8 activation spec fixture\n")
        self.spec_sha = sha256_file(self.spec)

        self.source_path = self.root / "source_health.json"
        self.data_gate_path = self.root / "data_gate.json"
        self.backup_path = self.root / "backup_restore.json"
        self.owner_path = self.root / "owner.json"
        self.evidence_path = self.root / "evidence.json"

        self.source = self._write_source(self.source_path)
        self.data_gate = self._write_data_gate(self.data_gate_path, self.source)
        self._write_backup(self.backup_path)
        self.owner_path.write_text(json.dumps(_owner_inputs()))
        self.evidence_path.write_text(json.dumps({
            "review_evidence": "external review PASS 2026-07-19",
            "activation_spec_sha256": self.spec_sha,
            "code_commit": self.head,
            "darwin_durability_verified": True,
            "pre_append_state": "VALID EMPTY",
        }))

    # -- receipt builders (real make_receipt -> intact hashes) -------------- #
    def _write_source(self, path: Path) -> dict:
        receipt = make_receipt("source_health", {
            "evaluation_session": _COMPLETED_SESSION,
            "requested_run_date": _REQUESTED_RUN_DATE,
            "known_as_of_utc": "2026-07-10T20:00:00+00:00",
            "scope": scope_identity(),
            "healthy_count": len(self.names),
            "unhealthy_count": 0,
            "unhealthy_symbols": [],
            "activation_ready": True,
            "symbols": {s: {"symbol": s, "healthy": True} for s in self.names},
            "input_files": {},
            "config_hash": config_hash(),
            "source_hash": diagnostic_source_hash(),
        })
        path.write_text(json.dumps(receipt))
        return receipt

    def _write_data_gate(self, path: Path, source: dict) -> dict:
        receipt = make_receipt("data_gate", {
            "evaluation_session": _COMPLETED_SESSION,
            "requested_run_date": _REQUESTED_RUN_DATE,
            "scope": scope_identity(),
            "whole_universe_verdict": "GO",
            "go_count": len(self.names),
            "no_go_count": 0,
            "symbols": {s: {} for s in self.names},
            "input_files": {},
            "source_health_receipt_hash": source["receipt_hash"],
            "source_health_receipt_path": str(self.source_path),
            "config_hash": config_hash(),
            "source_hash": diagnostic_source_hash(),
        })
        path.write_text(json.dumps(receipt))
        return receipt

    def _write_backup(self, path: Path) -> dict:
        receipt = make_receipt("backup_restore", {
            "completed_session": _COMPLETED_SESSION,
            "verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "snapshot": "latest",
            "scope": scope_identity(),
            "verification": {"ok": True},
        })
        path.write_text(json.dumps(receipt))
        return receipt

    # -- patches that stand in for the real world (caches, git tree) -------- #
    def _world_patches(self, stack: ExitStack) -> None:
        stack.enter_context(mock.patch.object(
            cli, "validate_data_gate_receipt",
            side_effect=lambda path, **kw: load_receipt(
                Path(path), expected_type="data_gate")))
        stack.enter_context(mock.patch.object(
            ag, "_working_tree_clean",
            return_value=ag.Check("working_tree_clean", True, "clean")))
        # Append-time gate re-run: deterministic PASS (the real evaluators read
        # real caches; those paths are covered by their own tests).
        stack.enter_context(mock.patch(
            "options_researcher.h7_source_health.load_assertions",
            return_value=[]))
        stack.enter_context(mock.patch(
            "options_researcher.h7_source_health.evaluate_health",
            return_value={"activation_ready": True}))
        stack.enter_context(mock.patch(
            "options_researcher.h7_data_gate.evaluate",
            return_value={"whole_universe_verdict": "GO",
                          "evaluation_session": _COMPLETED_SESSION}))

    def test_activation_lands_seq0_with_receipt_hashes_in_payload(self):
        real_before = el.verify(base_dir=REAL_FORWARD_STORE)
        # Phase-aware: pre-activation the real store is VALID EMPTY; post-activation
        # (2026-07-20, seq-0 window_registration) it is VALID non-empty. The invariant
        # under test is "valid and UNTOUCHED by this operation", not "empty".
        self.assertTrue(real_before.valid)

        with ExitStack() as stack:
            self._world_patches(stack)
            result = cli.activate(
                owner_path=self.owner_path, evidence_path=self.evidence_path,
                source_health_path=self.source_path,
                data_gate_path=self.data_gate_path,
                backup_restore_path=self.backup_path,
                completed_session=_COMPLETED_SESSION,
                confirmation=cli.CONFIRMATION, spec_path=self.spec,
                forward_base=self.store, code_state=lambda: (self.head, True))

        self.assertEqual(result.seq, 0)
        v = el.verify(base_dir=self.store)
        self.assertEqual(v.count, 1)
        event = el.read_events(self.store)[0]
        self.assertEqual(event.event_type, "window_registration")
        self.assertEqual(event.payload["activation_spec_sha256"], self.spec_sha)
        self.assertEqual(event.payload["code_commit"], self.head)
        gates = event.payload["gates"]
        self.assertEqual(gates["source_health_evidence_id"],
                         self.source["receipt_hash"])
        self.assertEqual(gates["data_gate_evidence_id"],
                         self.data_gate["receipt_hash"])

        # The real store is byte-identical before and after (never touched).
        real_after = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertEqual(
            (real_after.valid, real_after.empty, real_after.count),
            (real_before.valid, real_before.empty, real_before.count))

    def test_recheck_receipt_hash_mismatch_refuses_and_writes_nothing(self):
        # (c) After the good source receipt is bound into the evidence, replace
        # the on-disk source receipt with a DIFFERENT (still internally valid)
        # receipt. The CLI's append-time recheck reloads it, sees a hash that
        # disagrees with the assembled evidence, and refuses through the one
        # door -- nothing is written.
        source_good = load_receipt(self.source_path, expected_type="source_health")
        tampered = make_receipt("source_health", {
            **{k: v for k, v in source_good.items() if k != "receipt_hash"},
            "healthy_count": len(self.names) - 1,  # changes the content -> hash
        })
        self.assertNotEqual(tampered["receipt_hash"], source_good["receipt_hash"])
        self.source_path.write_text(json.dumps(tampered))

        recheck = cli._make_recheck(
            source=source_good, data_gate=self.data_gate,
            source_path=self.source_path, data_gate_path=self.data_gate_path,
            names=self.names, completed_session=_COMPLETED_SESSION)

        report = ag.GuardReport(
            checks=[ag.Check(n, True, "ok") for n in (
                "ledger_valid_empty", "source_health_whole_universe",
                "data_gate_go", "owner_inputs_complete", "working_tree_clean")],
            forward_base=str(self.store.resolve()),
            code_commit=self.head,
            built_at_utc=datetime.now(timezone.utc).isoformat())

        evidence = {
            "review_evidence": "external review PASS 2026-07-19",
            "activation_spec_sha256": self.spec_sha,
            "code_commit": self.head,
            "source_health_evidence_id": source_good["receipt_hash"],
            "data_gate_evidence_id": self.data_gate["receipt_hash"],
            "darwin_durability_verified": True,
            "pre_append_state": "VALID EMPTY",
        }
        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                cli, "validate_data_gate_receipt",
                side_effect=lambda path, **kw: load_receipt(
                    Path(path), expected_type="data_gate")))
            with self.assertRaises(wr.ActivationRefused):
                wr.register_window_real(
                    owner=_owner_inputs(), evidence=evidence,
                    guard_report=report, spec_sha256=self.spec_sha,
                    spec_path=self.spec, base_dir=self.store,
                    code_state=lambda: (self.head, True),
                    recheck_gates=recheck)
        self.assertTrue(el.verify(base_dir=self.store).empty)


if __name__ == "__main__":
    unittest.main()

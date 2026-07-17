# H7 Stage-8 `window_registration` Schema + Activation Guard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `window_registration` event type and the Stage-8 activation guard, test-first on synthetic stores, so the forward paper window can open the moment the owner supplies the §3 packet inputs and the external review passes — while the real forward store stays `VALID EMPTY` throughout.

**Architecture:** Three small changes: (1) add `"window_registration"` to `EVENT_TYPES` in `h7_event_ledger.py` (flat tuple, membership-validated; replays in book/lifecycle/scoring positive-match by type so the new no-cause event is naturally skipped); (2) new module `h7_window_registration.py` that validates and builds the packet-§4 event payload (10 required field groups) and appends it as the FIRST event via `expected_head=None`; (3) new module `h7_activation_guard.py` that computes every precondition (whole-universe source health loop, data gate GO, VALID EMPTY, owner inputs, coverage-through arithmetic, 3-calendar-month proof) and refuses with typed reasons. Everything mirrors the Stage-7 synthetic-store discipline (`_synthetic_base` guard: `ActivationBoundaryError` on the real store).

**Tech Stack:** Python 3.12, unittest, existing modules only.

**HARD GATES:**
- BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. No task may create `ledger/h7_forward/events.jsonl` or `HEAD`. Every test asserts the real store verifies `VALID EMPTY` before AND after (copy the pattern in `tests/test_h7_stage7_synthetic_proof.py`).
- No CLI that appends to the real store. No scheduler. The real `window_registration` append happens only in a future owner-authorized Stage-8 opening session after external review — outside this plan.
- Universe counts are DERIVED (`watch_universe()` ∪ `config.H7_BACKTEST_SYMBOLS`), never hardcoded 12 or 14 (the packet's "12/12" text is stale against the live 14-name union — derive, don't transcribe).
- Owner window inputs (packet §3) remain blank; the guard treats absent inputs as a refusal reason, which is the correct current state.

---

### Task 1: Add the event type

**Files:**
- Modify: `options_researcher/h7_event_ledger.py:52-56` (the `EVENT_TYPES` tuple)
- Test: `tests/test_h7_window_registration.py` (new file, first test class)

- [ ] **Step 1: Write the failing test**

```python
"""window_registration event type + builder (Stage 8, BUILD-ONLY/INACTIVE)."""
import unittest

from options_researcher import h7_event_ledger as el


class EventTypeTests(unittest.TestCase):
    def test_window_registration_is_a_valid_event_type(self):
        self.assertIn("window_registration", el.EVENT_TYPES)

    def test_existing_types_unchanged(self):
        for t in ("source_health", "data_gate", "board_resolution", "lane_displaced",
                  "entry_intent", "exit_intent", "owner_approval", "paper_fill",
                  "skip", "data_gap"):
            self.assertIn(t, el.EVENT_TYPES)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_h7_window_registration.py -q`
Expected: FAIL — `'window_registration' not found in EVENT_TYPES`

- [ ] **Step 3: Add the type** — in `h7_event_ledger.py`, extend the tuple (keep it last, comment it):

```python
EVENT_TYPES = (
    "source_health", "data_gate", "board_resolution", "lane_displaced",
    "entry_intent", "exit_intent", "owner_approval", "paper_fill",
    "skip", "data_gap",
    "window_registration",  # Stage 8: first-and-only preamble event, causes=[]
)
```

- [ ] **Step 4: Run the ledger + new tests**

Run: `uv run pytest tests/test_h7_window_registration.py tests/test_h7_event_ledger.py -q`
Expected: PASS (existing ledger tests unaffected — the tuple only gained a member)

- [ ] **Step 5: Verify replays skip the new type harmlessly** — add to the same test file:

```python
import tempfile
from pathlib import Path

from data.cache_runner import session_close_utc
from options_researcher import h7_forward_book as book
from options_researcher import h7_forward_scoring as scoring


def _minimal_registration_event():
    return {
        "schema_version": 1,
        "event_id": "wr:test-window-1",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc("2026-07-10").isoformat(),
        "evaluation_session": "2026-07-10",
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": {"placeholder_for_task2": True},
    }


class ReplaySkipTests(unittest.TestCase):
    def test_book_and_scoring_ignore_window_registration(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        el.append_event(_minimal_registration_event(), base_dir=base,
                        expected_head=None)
        snap = book.derive_book(base_dir=base, evaluation_session="2026-07-10")
        self.assertEqual(snap.positions, {})   # adapt to BookSnapshot's actual empty shape
        result = scoring.score_forward_window(base_dir=base,
                                              window_start="2026-07-10",
                                              window_end="2026-07-11")
        self.assertEqual(result["n_trades"], 0)  # adapt key to scorer's actual output
```

NOTE for implementer: before finalizing the two `assertEqual`s, read `BookSnapshot`'s empty-state fields (`h7_forward_book.py`, dataclass near `derive_book`) and the scorer's zero-trade output keys (`score_forward_window` return dict) and assert on the real names. The invariant under test: neither replay raises on the new type and both report an empty book/zero trades.

- [ ] **Step 6: Run and commit**

Run: `uv run pytest tests/test_h7_window_registration.py -q`
Expected: PASS

```bash
git add options_researcher/h7_event_ledger.py tests/test_h7_window_registration.py
git commit -m "feat(h7-stage8): window_registration event type; replays skip it harmlessly"
```

---

### Task 2: Registration event builder — `h7_window_registration.py`

**Files:**
- Create: `options_researcher/h7_window_registration.py`
- Test: `tests/test_h7_window_registration.py` (extend)

The payload must carry the packet-§4 field groups. Owner §3 inputs arrive as an explicit dict — no defaults, no inference (`None`/missing → `RegistrationInputError`).

- [ ] **Step 1: Write the failing tests** (append to the test file)

```python
from options_researcher import h7_window_registration as wr


def owner_inputs(**over):
    base = {
        "H7_STAGE8_EXPLICIT_AUTHORIZATION": "owner-typed-string 2026-XX-XX",
        "WINDOW_START_DECISION_SESSION": "2026-08-03",
        "WINDOW_DECISION_SESSION_COUNT": 70,  # 70 sessions from 2026-08-03 ends
        # ~2026-11-09, safely past the 3-calendar-month anniversary (2026-11-03);
        # 64 would end 2026-10-30 and fail the window rule — deliberate margin
        "WINDOW_END_RULE_ACKNOWLEDGED": "70 XNYS decision sessions from start inclusive",
        "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED": "yes",
        "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH": "2026-12-31",
        "THETADATA_CONFIRMATION_EVIDENCE": "renewal receipt <id>",
    }
    base.update(over)
    return base


def evidence(**over):
    base = {
        "review_evidence": "external review PASS <date>",
        "activation_spec_sha256": "a" * 64,
        "code_commit": "b" * 40,
        "source_health_evidence_id": "sh:2026-08-01",
        "data_gate_evidence_id": "dg:2026-08-01",
        "darwin_durability_verified": True,
        "pre_append_state": "VALID EMPTY",
    }
    base.update(over)
    return base


class BuilderTests(unittest.TestCase):
    def test_builds_complete_payload(self):
        event = wr.build_window_registration_event(
            owner=owner_inputs(), evidence=evidence())
        self.assertEqual(event["event_type"], "window_registration")
        self.assertEqual(event["causes"], [])
        p = event["payload"]
        self.assertEqual(p["window"]["start_decision_session"], "2026-08-03")
        self.assertIn("config_hash", p["frozen"])
        self.assertIn("MIN_LOSSES_FOR_VERDICT", p["frozen"]["stage456_parameters"])
        self.assertEqual(p["frozen"]["verdict_mapping"],
                         {"SURVIVED": "ci_above_zero", "REJECTED": "ci_below_zero",
                          "INCONCLUSIVE": "insufficient_or_no_edge"})
        self.assertIn("not live-trading approval", p["frozen"]["survived_disclaimer"])
        self.assertEqual(p["cohort_rule"],
                         "decision_session in registered window (immutable key)")

    def test_missing_owner_input_refuses(self):
        bad = owner_inputs()
        del bad["WINDOW_START_DECISION_SESSION"]
        with self.assertRaises(wr.RegistrationInputError):
            wr.build_window_registration_event(owner=bad, evidence=evidence())

    def test_none_owner_input_refuses(self):
        with self.assertRaises(wr.RegistrationInputError):
            wr.build_window_registration_event(
                owner=owner_inputs(THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH=None),
                evidence=evidence())

    def test_three_month_rule_enforced(self):
        # 20 sessions from 2026-08-03 ends ~2026-08-28 << 3-calendar-month anniversary
        with self.assertRaises(wr.WindowRuleError):
            wr.build_window_registration_event(
                owner=owner_inputs(WINDOW_DECISION_SESSION_COUNT=20),
                evidence=evidence())

    def test_coverage_must_reach_window_end(self):
        with self.assertRaises(wr.WindowRuleError):
            wr.build_window_registration_event(
                owner=owner_inputs(
                    THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH="2026-09-01"),
                evidence=evidence())


class AppendTests(unittest.TestCase):
    def test_registers_as_first_event_on_synthetic_store(self):
        import tempfile
        from pathlib import Path
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        res = wr.register_window(owner=owner_inputs(), evidence=evidence(),
                                 base_dir=base)
        self.assertEqual(res.seq, 1)
        self.assertTrue(res.appended)

    def test_refuses_non_empty_ledger(self):
        import tempfile
        from pathlib import Path
        from options_researcher import h7_event_ledger as el
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        el.append_event(_minimal_registration_event(), base_dir=base,
                        expected_head=None)
        with self.assertRaises(el.LedgerHeadConflictError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=base)

    def test_refuses_real_store(self):
        from options_researcher.h7_paper_lifecycle import (
            REAL_FORWARD_STORE, ActivationBoundaryError)
        with self.assertRaises(ActivationBoundaryError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=REAL_FORWARD_STORE)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h7_window_registration.py -q`
Expected: FAIL with `ModuleNotFoundError: h7_window_registration`

- [ ] **Step 3: Implement `options_researcher/h7_window_registration.py`**

```python
"""Stage 8 window_registration builder + synthetic-store append.

BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. The real first append happens only in
a future owner-authorized Stage-8 opening arc (readiness packet §5 steps
5-9) after external review — never from this module's tests and never via
any CLI (none exists here on purpose).
"""
from __future__ import annotations

from datetime import date

import config
from data.cache_runner import session_close_utc, trading_days
from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_paper_lifecycle import _synthetic_base
from research.hashing import config_hash, cost_model_hash

OWNER_FIELDS = (
    "H7_STAGE8_EXPLICIT_AUTHORIZATION",
    "WINDOW_START_DECISION_SESSION",
    "WINDOW_DECISION_SESSION_COUNT",
    "WINDOW_END_RULE_ACKNOWLEDGED",
    "WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED",
    "THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH",
    "THETADATA_CONFIRMATION_EVIDENCE",
)
EVIDENCE_FIELDS = (
    "review_evidence", "activation_spec_sha256", "code_commit",
    "source_health_evidence_id", "data_gate_evidence_id",
    "darwin_durability_verified", "pre_append_state",
)
STAGE456_PARAMETER_NAMES = (
    "H7_FORWARD_CONTRACTS", "COMMISSION_PER_CONTRACT", "SLIPPAGE_HAIRCUT",
    "H7_LANE_PRIORITY", "H7_LONG_DELTA_BAND", "H7_LONG_DTE_BAND",
    "H7_SPREAD_LONG_DELTA", "H7_SPREAD_SHORT_DELTA", "H7_LONG_TP_PCT",
    "H7_SPREAD_TP_FRAC_MAX", "H7_CLOSE_AT_DTE", "H7_DELTA_TOLERANCE",
    "H7C_SHORT_DELTA_MAX", "H7C_DTE_BAND", "H7C_CREDIT_FLOOR_FRAC",
    "H7C_WIDTH_FRAC_OF_SPOT", "H7C_TP_FRAC", "H7C_STOP_CREDIT_MULT",
    "H7C_MAX_CONCURRENT", "H7C_CLOSE_AT_DTE", "H7C_CLOSE_BEFORE_EARNINGS",
    "H7C_TIEBREAK", "H7_MONTHLY_AT_RISK", "H7_MAX_OPEN_PER_UNDERLYING",
    "H7_ADMIT_MIN_CONTRACTS", "H7_ADMIT_MAX_SPREAD_PCT",
    "H7_EARNINGS_BAN_SESSIONS", "H7_EARNINGS_POST_REPORT_GRACE_D",
    "MIN_LOSSES_FOR_VERDICT", "BOOTSTRAP_SAMPLES",
)


class RegistrationInputError(ValueError):
    """An owner/evidence input is missing, None, or malformed."""


class WindowRuleError(ValueError):
    """The window arithmetic violates a registered rule."""


def _require(mapping: dict, fields: tuple, label: str) -> None:
    for f in fields:
        if mapping.get(f) in (None, ""):
            raise RegistrationInputError(f"{label} input {f} is missing/None; "
                                         "no default may be inferred")


def _add_months(d: date, months: int) -> date:
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                      else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def derive_window_end(start_iso: str, session_count: int) -> str:
    """Final decision session; must be >= the 3-calendar-month anniversary."""
    horizon = trading_days(start_iso, "2100-01-01")[:session_count]
    if len(horizon) < session_count:
        raise WindowRuleError("calendar cannot supply the requested session count")
    end_iso = horizon[-1]
    anniversary = _add_months(date.fromisoformat(start_iso), 3)
    if date.fromisoformat(end_iso) < anniversary:
        raise WindowRuleError(
            f"final decision session {end_iso} precedes the three-calendar-month "
            f"anniversary {anniversary.isoformat()}; a shorter count is invalid")
    return end_iso


def build_window_registration_event(*, owner: dict, evidence: dict) -> dict:
    _require(owner, OWNER_FIELDS, "owner")
    _require(evidence, EVIDENCE_FIELDS, "evidence")
    start = owner["WINDOW_START_DECISION_SESSION"]
    count = int(owner["WINDOW_DECISION_SESSION_COUNT"])
    end = derive_window_end(start, count)
    coverage = str(owner["THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH"])
    if coverage < end:
        raise WindowRuleError(
            f"paid coverage confirmed through {coverage} < window end {end} "
            "(plus lifecycle exits); coverage must span the full window")
    payload = {
        "owner_authorization": {f: owner[f] for f in OWNER_FIELDS},
        "review_evidence": evidence["review_evidence"],
        "activation_spec_sha256": evidence["activation_spec_sha256"],
        "code_commit": evidence["code_commit"],
        "window": {
            "start_decision_session": start,
            "decision_session_count": count,
            "final_decision_session": end,
            "end_rule": "inclusive count of XNYS decision sessions from start",
            "three_month_proof": f"{end} >= 3-calendar-month anniversary of {start}",
        },
        "cohort_rule": "decision_session in registered window (immutable key)",
        "frozen": {
            "config_hash": config_hash(),
            "cost_model_hash": cost_model_hash(),
            "stage456_parameters": {n: getattr(config, n)
                                    for n in STAGE456_PARAMETER_NAMES},
            "scorer": {"module": "options_researcher.h7_forward_scoring",
                       "bootstrap_samples": config.BOOTSTRAP_SAMPLES,
                       "min_losses_for_verdict": config.MIN_LOSSES_FOR_VERDICT},
            "verdict_mapping": {"SURVIVED": "ci_above_zero",
                                "REJECTED": "ci_below_zero",
                                "INCONCLUSIVE": "insufficient_or_no_edge"},
            "survived_disclaimer": ("SURVIVED is not live-trading approval, not a "
                                    "profitability claim, and not validation"),
        },
        "gates": {"source_health_evidence_id": evidence["source_health_evidence_id"],
                  "data_gate_evidence_id": evidence["data_gate_evidence_id"]},
        "coverage_evidence": owner["THETADATA_CONFIRMATION_EVIDENCE"],
        "darwin_durability_verified": bool(evidence["darwin_durability_verified"]),
        "pre_append_state": evidence["pre_append_state"],
    }
    return {
        "schema_version": ledger.SCHEMA_VERSION,
        "event_id": f"wr:{start}:{count}",
        "event_type": "window_registration",
        "occurred_at_utc": session_close_utc(start).isoformat(),
        "evaluation_session": start,
        "symbol": None,
        "lane": None,
        "causes": [],
        "payload": payload,
    }


def register_window(*, owner: dict, evidence: dict, base_dir,
                    clock=None) -> ledger.AppendResult:
    """Append the registration as the FIRST event. Synthetic stores only."""
    base = _synthetic_base(base_dir)
    event = build_window_registration_event(owner=owner, evidence=evidence)
    return ledger.append_event(event, base_dir=base, clock=clock,
                               expected_head=None)
```

NOTE for implementer: `_synthetic_base` is module-private in `h7_paper_lifecycle`; if importing it draws a ruff private-usage warning, copy the four-line guard into this module verbatim (that is what `h7_forward_book`/`h7_forward_scoring` do — four identical copies exist by design).

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_h7_window_registration.py -q`
Expected: PASS (all builder + append + refusal tests)

- [ ] **Step 5: Commit**

```bash
git add options_researcher/h7_window_registration.py tests/test_h7_window_registration.py
git commit -m "feat(h7-stage8): window_registration builder with packet-§4 payload and window-rule proofs"
```

---

### Task 3: Activation guard — `h7_activation_guard.py`

**Files:**
- Create: `options_researcher/h7_activation_guard.py`
- Test: `tests/test_h7_activation_guard.py`

Read-only precondition computer. Returns a typed report; refuses nothing itself except the real-store boundary (it must be runnable against synthetic fixtures AND — read-only — against the real gates for a readiness snapshot).

- [ ] **Step 1: Write the failing tests**

```python
"""Stage-8 activation guard — every precondition, typed reasons, no side effects."""
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

from options_researcher import h7_activation_guard as ag


def go_gate(universe):
    return {"whole_universe_verdict": "GO", "go_count": len(universe),
            "universe": list(universe)}


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name) / "synthetic-forward"
        self.addCleanup(self.tmp.cleanup)

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
        # 3-symbol synthetic universe must be accepted as "whole universe"
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
        # the guard may READ the real store's verify state (it appends nothing)
        from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
        report = ag.activation_preconditions(
            forward_base=REAL_FORWARD_STORE,
            source_health_by_symbol={"MSFT": True}, universe=("MSFT",),
            data_gate_result=go_gate(("MSFT",)), owner_inputs={},
            allow_real_readonly=True)
        self.assertTrue(report.by_name["ledger_valid_empty"].ok)  # VALID EMPTY today
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_h7_activation_guard.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `options_researcher/h7_activation_guard.py`**

```python
"""Stage-8 activation guard — read-only precondition computation.

Appends nothing, ever. `allow_real_readonly=True` permits VERIFY-ONLY reads
of the real store for readiness snapshots; every mutating Stage-8 action
lives elsewhere and stays owner-gated.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_window_registration import OWNER_FIELDS


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    reason: str


@dataclass
class GuardReport:
    checks: list = field(default_factory=list)

    @property
    def by_name(self) -> dict:
        return {c.name: c for c in self.checks}

    @property
    def ready(self) -> bool:
        return all(c.ok for c in self.checks)


def _working_tree_clean() -> Check:
    out = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                         text=True, check=True).stdout.strip()
    return Check("working_tree_clean", out == "",
                 "clean" if out == "" else f"dirty: {out.splitlines()[:5]}")


def activation_preconditions(*, forward_base, source_health_by_symbol: dict,
                             universe: tuple, data_gate_result: dict,
                             owner_inputs: dict,
                             allow_real_readonly: bool = False) -> GuardReport:
    from options_researcher.h7_paper_lifecycle import (
        REAL_FORWARD_STORE, ActivationBoundaryError)
    base = Path(forward_base).resolve()
    if not allow_real_readonly and (base == REAL_FORWARD_STORE
                                    or REAL_FORWARD_STORE in base.parents):
        raise ActivationBoundaryError("guard test fixtures must use synthetic stores")

    report = GuardReport()
    v = ledger.verify(base_dir=base)
    report.checks.append(Check(
        "ledger_valid_empty", v.valid and v.empty,
        "VALID EMPTY" if v.valid and v.empty
        else f"valid={v.valid} empty={v.empty} count={v.count}"))

    unhealthy = sorted(s for s in universe
                       if not source_health_by_symbol.get(s, False))
    missing = sorted(set(universe) - set(source_health_by_symbol))
    report.checks.append(Check(
        "source_health_whole_universe", not unhealthy and not missing,
        "all healthy" if not unhealthy and not missing
        else f"unhealthy={unhealthy} missing={missing}"))

    gate_ok = (data_gate_result.get("whole_universe_verdict") == "GO"
               and data_gate_result.get("go_count") == len(data_gate_result.get("universe", [])))
    report.checks.append(Check(
        "data_gate_go", gate_ok,
        "GO whole-universe" if gate_ok
        else f"verdict={data_gate_result.get('whole_universe_verdict')}"))

    blank = [f for f in OWNER_FIELDS if owner_inputs.get(f) in (None, "")]
    report.checks.append(Check(
        "owner_inputs_complete", not blank,
        "complete" if not blank else f"blank: {blank}"))

    report.checks.append(_working_tree_clean())
    return report
```

- [ ] **Step 4: Run tests + full suite + linters**

Run: `uv run pytest tests/test_h7_activation_guard.py -q && uv run pytest -q && uv run ruff check . && uv run pyright`
Expected: all green. (The `working_tree_clean` check will read the actual git state — tests must not assert on its `ok` value, only on its presence, which the Task-3 tests already respect.)

- [ ] **Step 5: Verify the real store is untouched**

Run: `uv run python -m options_researcher.h7_event_ledger verify`
Expected: `VALID EMPTY`, exit 0

- [ ] **Step 6: Commit**

```bash
git add options_researcher/h7_activation_guard.py tests/test_h7_activation_guard.py
git commit -m "feat(h7-stage8): read-only activation guard with derived universe counts"
```

---

### Task 4: Synthetic end-to-end rehearsal + real-store invariant

**Files:**
- Test: `tests/test_h7_stage8_synthetic.py`

- [ ] **Step 1: Write the test** (this is the Stage-7-style proof for Stage 8)

```python
"""Stage-8 synthetic rehearsal: guard blocks -> inputs supplied -> registration
appends as the first event -> replays skip it -> real store untouched."""
import tempfile
import unittest
from pathlib import Path

from options_researcher import h7_activation_guard as ag
from options_researcher import h7_event_ledger as el
from options_researcher import h7_window_registration as wr
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE

# NOTE for implementer: if `tests` is not an importable package in this repo
# (no tests/__init__.py), copy the owner_inputs()/evidence() fixture helpers
# from tests/test_h7_window_registration.py into this file verbatim instead
# of importing them.
from tests.test_h7_window_registration import evidence, owner_inputs


class Stage8SyntheticRehearsal(unittest.TestCase):
    def test_full_arc_on_synthetic_store(self):
        before = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertTrue(before.valid)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name) / "synthetic-forward"
        universe = ("MSFT", "AMZN", "VST")
        health = {s: True for s in universe}
        gate = {"whole_universe_verdict": "GO", "go_count": 3,
                "universe": list(universe)}

        blocked = ag.activation_preconditions(
            forward_base=base, source_health_by_symbol=health,
            universe=universe, data_gate_result=gate, owner_inputs={})
        self.assertFalse(blocked.ready)  # owner inputs blank -> correctly blocked

        ready = ag.activation_preconditions(
            forward_base=base, source_health_by_symbol=health,
            universe=universe, data_gate_result=gate,
            owner_inputs=owner_inputs())
        self.assertTrue(ready.by_name["owner_inputs_complete"].ok)

        res = wr.register_window(owner=owner_inputs(), evidence=evidence(),
                                 base_dir=base)
        self.assertEqual(res.seq, 1)
        after_reg = el.verify(base_dir=base)
        self.assertEqual(after_reg.count, 1)

        # a second registration refuses (head no longer empty)
        with self.assertRaises(el.LedgerHeadConflictError):
            wr.register_window(owner=owner_inputs(), evidence=evidence(),
                               base_dir=base)

        after = el.verify(base_dir=REAL_FORWARD_STORE)
        self.assertEqual((after.valid, after.empty, after.count, after.head),
                         (before.valid, before.empty, before.count, before.head))
```

- [ ] **Step 2: Run it**

Run: `uv run pytest tests/test_h7_stage8_synthetic.py -q`
Expected: PASS

- [ ] **Step 3: Full suite, linters, ledger verify**

Run: `uv run pytest -q && uv run ruff check . && uv run pyright && uv run python -m options_researcher.h7_event_ledger verify`
Expected: all green; `VALID EMPTY`

- [ ] **Step 4: Commit**

```bash
git add tests/test_h7_stage8_synthetic.py
git commit -m "test(h7-stage8): synthetic rehearsal — guard, first-event registration, real store untouched"
```

---

### Task 5: Ledger fact + docs sync — orchestrator executes

- [ ] **Step 1:** Append a fact via `research.facts.append_fact`:
`H7_STAGE8_SCHEMA_BUILT <date>: window_registration event type + builder (packet-§4 payload, 3-calendar-month proof, coverage arithmetic) + read-only activation guard (derived universe counts, never hardcoded 12) implemented test-first on synthetic stores at commit <sha>; real forward store VALID EMPTY throughout; ordering deviation from packet §5 (build before owner §3 inputs) owner-authorized 2026-07-16 ("this project needs to begin now") — §3 values are runtime inputs to the registration EVENT, not the schema. Stage 8 remains NOT OPEN: owner §3 inputs blank, external review pending, no real append path exists.`
- [ ] **Step 2:** Update `docs/superpowers/plans/2026-07-13-h7-stage8-activation-readiness.md` §2 table row "Code/config identity" and §4 note "The event type and schema do not exist yet" with a dated addendum line pointing to this plan (do not rewrite history — append an `**Addendum <date>:**` line).
- [ ] **Step 3:** Commit.

---

## Self-review notes (against packet §4/§5 + interface map)

- Packet §4 items 1–10 → builder payload fields (Task 2 `BuilderTests.test_builds_complete_payload` asserts the load-bearing ones; every §4 group present in `payload`). ✓
- §3 owner inputs all required, no defaults → `_require` + tests. ✓
- 3-calendar-month end rule + session-count derivation → `derive_window_end` + `WindowRuleError` tests. ✓
- Coverage-through ≥ window end → builder check + test. ✓
- VALID EMPTY / first-event / `expected_head=None` → AppendTests + rehearsal. ✓
- Real-store boundary → `test_refuses_real_store`, rehearsal before/after, `verify` CLI steps. ✓
- Derived universe counts (stale "12/12" trap) → `test_universe_count_is_derived_not_hardcoded`. ✓
- Replay compatibility (no dispatch table) → Task 1 Step 5. ✓
- Known deferred checks for the implementer: `BookSnapshot` empty-shape field names and scorer zero-trade keys (Task 1 Step 5 note); `_synthetic_base` import vs copy (Task 2 note).

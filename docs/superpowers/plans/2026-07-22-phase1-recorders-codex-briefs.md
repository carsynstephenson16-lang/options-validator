# Phase 1 Recorders — Codex Implementation Briefs

> **For agentic workers:** Executor is **Codex** (owner-launched sessions; rules in
> `AGENTS.md`). Claude orchestrates and reviews; the owner types all frozen
> numbers and grants all ratifications. Work strictly task-by-task with the
> checkbox steps below. If a cited interface does not match the installed code,
> STOP and report — do not improvise.

**Goal:** Every live hypothesis records evidence daily — H10a/b get a capture
path, H5's trigger watch joins the morning ritual, the ritual emits a
per-hypothesis capture receipt, and (once owner-ratified) H7 gets its real exit
and scoring paths.

**Architecture:** Additive only. New modules follow the existing
watcher/injection pattern (`qm_watch.py`-style injectable loaders, unittest,
offline). The H7 exit/scoring build implements the already-written SPEC
verbatim — the SPEC, not this plan, is normative for its internals.

**Tech stack:** Python 3.12, uv, unittest (offline, no network), ruff, pyright,
append-only JSONL evidence files, `tools/daily_ritual.sh` (bash).

**Spec:** `docs/superpowers/specs/2026-07-22-project-replan-design.md` (§3).

---

## Execution tracks

- **Track A — unblocked NOW:** Task 1 (H10 config), Task 2 (H10 watcher),
  Task 3 (H10 book+observations), Task 4 (H5 ritual wiring), Task 5 (capture
  receipt). Order: 1 → 2 → 3, then 4 and 5 in either order.
- **Track B — owner-gated:** Task 6 (H7 exit+scoring) MUST NOT start until the
  owner ratifies `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`
  (currently stamped "SPEC CANDIDATE ONLY. NOT BUILD-AUTHORIZED", spec lines
  3-4) with a typed ledger fact. Task 7 (ritual wiring of exit/monitoring
  sessions) MUST NOT start until Task 6's independent adversarial review
  records a PASS in the ledger.

Global rules for every task: run `uv run python -m unittest discover -s tests`
(exit code is the verdict), `uv run ruff check .`, `uv run pyright` before every
commit. Never edit `ledger/facts.log`, `ledger/experiments.jsonl`, or
`ledger/h7_forward/{events.jsonl,HEAD}` by hand. Commit after each green task
with the message given in the task.

---

### Task 1: H10 frozen parameters into config.py (transcription, not invention)

**Files:**
- Modify: `config.py` (new `H10` block near the existing QM/H8 blocks)
- Test: `tests/test_h10_config.py` (create)

The registered values live in `ledger/experiments.jsonl` seq 15 (H10a) and
seq 16 (H10b). This task TRANSCRIBES them; inventing or "improving" any value
is prohibited.

- [ ] **Step 1: Write the failing test** — `tests/test_h10_config.py`:

```python
import json
import unittest

import config


def _load_registration(seq):
    with open("ledger/experiments.jsonl", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("seq") == seq:
                return rec
    raise AssertionError(f"seq {seq} not found")


class H10ConfigMatchesRegistration(unittest.TestCase):
    def test_constants_exist(self):
        for name in (
            "H10_MAX_PREMIUM_PER_TRADE",
            "H10_MONTHLY_PREMIUM_CAP",
            "H10_DELTA_MIN",
            "H10_DELTA_MAX",
            "H10_STRIKE_BAND_PCT",
            "H10_DTE_MIN",
            "H10_DTE_MAX",
            "H10_PROFIT_TARGET_PCT",
            "H10_TIME_EXIT_SESSIONS",
            "H10_DTE_EXIT",
            "H10_MIN_LOSSES_FOR_VERDICT",
            "H10A_WINDOW_END",
            "H10B_WINDOW_END",
        ):
            self.assertTrue(hasattr(config, name), name)

    def test_values_match_registration_text(self):
        reg_a = json.dumps(_load_registration(15))
        reg_b = json.dumps(_load_registration(16))
        self.assertEqual(config.H10_MAX_PREMIUM_PER_TRADE, 600)
        self.assertEqual(config.H10_MONTHLY_PREMIUM_CAP, 2000)
        self.assertEqual((config.H10_DELTA_MIN, config.H10_DELTA_MAX), (0.40, 0.60))
        self.assertEqual(config.H10_STRIKE_BAND_PCT, 0.10)
        self.assertEqual((config.H10_DTE_MIN, config.H10_DTE_MAX), (30, 60))
        self.assertEqual(config.H10_PROFIT_TARGET_PCT, 1.00)
        self.assertEqual(config.H10_TIME_EXIT_SESSIONS, 20)
        self.assertEqual(config.H10_DTE_EXIT, 21)
        self.assertEqual(config.H10_MIN_LOSSES_FOR_VERDICT, 7)
        self.assertEqual(config.H10A_WINDOW_END, "2026-10-06")
        self.assertEqual(config.H10B_WINDOW_END, "2027-01-06")
        # anchor: the registration text must actually contain the key numbers
        self.assertIn("2026-10-06", reg_a)
        self.assertIn("2027-01-06", reg_b)
```

IMPORTANT: before finalizing this test, READ seq 15/16 yourself and correct any
expected value above that disagrees with the registration text — the ledger
wins over this plan. If a discrepancy exists, report it in the commit message.

- [ ] **Step 2: Run it, verify it fails** —
`uv run python -m unittest tests.test_h10_config -v` → FAIL (missing attrs).

- [ ] **Step 3: Add the `H10` block to `config.py`**, each constant with a
comment citing `ledger/experiments.jsonl seq 15/16` as its source. No other
config edits.

- [ ] **Step 4: Full suite + ruff + pyright green.**

- [ ] **Step 5: Commit** — `feat(h10): transcribe registered H10a/b parameters into config (ledger seq 15/16)`

### Task 2: `h10_watch` — daily signal evaluation (alerts + receipt payloads, no book writes)

**Files:**
- Create: `options_researcher/h10_watch.py`
- Test: `tests/test_h10_watch.py` (create)

Reuse, do not duplicate: signal functions from `qm_signals` (same ones
`options_researcher/qm_watch.py` calls), `adverse_buy`/`adverse_sell` pricing
from `data/pandas_feed.py` (`:53`/`:62`) and `passes_liquidity` from
`data/thetadata_adapter.py` (`:456`) — the exact split `qm_watch.py:34-35`
imports (brief corrected 2026-07-22 after Codex flagged the mismatch), the H7 admission
re-measure used by the watcher stack (≥5 NTM monthly contracts, spread ≤5%,
OI ≥100 — per seq 15/16). Follow `qm_watch.py`'s injectable-loader signature
style (`load_adjusted`, `load_chain`, `params`, `gate` as function args) so all
tests stay offline; that pattern is named at `qm_watch.py:52-56`.

Behavioral contract (test each):
1. For each name in `config.H7_WATCHLIST`, evaluate H10a (parabolic
   continuation) and H10b (breakout continuation) fires for the last completed
   session.
2. On fire: select the candidate contract per Task 1 constants (delta
   0.40–0.60, strike within ±10% of spot, 30–60 DTE, premium ≤ $600 after
   mid-or-worse + slippage + commission); apply the earnings-in-life skip and
   the per-name source-health entry ban (same fail-closed sources the H7
   watcher uses); apply the $2,000 open-premium concurrency cap by reading the
   open rows of `data/positions/h10_positions.csv` (Task 3 creates it; the
   watcher must also run correctly when the file has header only).
3. Emit exactly one dated receipt JSON per run to
   `reports/h10/receipts/h10_watch_<AS_OF>.json` containing: as_of, per-name
   evaluation (fired / no-signal / SKIPPED+reason), candidate contract if any,
   and a `book_action_required` boolean. Writing the receipt is the ONLY
   filesystem write this module may perform. It never writes the positions
   file — book entries are owner-recorded (H6 convention).
4. `--as-of` in the future → refuse, exit 2 (mirror `qm_watch.py:317-325`).
5. Re-running the same as_of must be idempotent (same receipt content, no
   duplicate side effects).

- [ ] **Step 1: Write failing tests** — `tests/test_h10_watch.py`, unittest
classes mirroring `tests/test_qm_watch.py`'s structure (`QuietTests`,
`FireTests`, `CapTests`, `EarningsSkipTests`, `ReceiptTests`,
`FutureAsOfTests`), synthetic DataFrames via injected loaders,
`tempfile.TemporaryDirectory` for the receipts dir. Assert the receipt schema
keys exactly; assert cap-exceeded produces `SKIPPED reason=CAP` not silence.
- [ ] **Step 2: Run tests, verify failures** —
`uv run python -m unittest tests.test_h10_watch -v`.
- [ ] **Step 3: Implement `h10_watch.py`** to the contract above. Banner must
state: forward paper study H10a/H10b, alerts + receipts only, never trades,
verdict gates on losses.
- [ ] **Step 4: Full suite + ruff + pyright green.**
- [ ] **Step 5: Commit** — `feat(h10): daily H10a/b watcher with receipts (no book writes)`

### Task 3: H10 paper book + append-only observations log + ritual wiring

**Files:**
- Create: `data/positions/h10_positions.csv` (header only)
- Create: `options_researcher/h10_observe.py`
- Modify: `tools/daily_ritual.sh` (insert after the H8 step at `:174-176`,
  inside the `GATE_GO` block ending `:177`; add new artifact paths to the
  Step-8 `git add` evidence allow-list at `:218-254`)
- Test: `tests/test_h10_observe.py` (create)

- [ ] **Step 1: Create the book file** with the repo-standard 12-column header
(exactly the `h6_positions.csv`/`h8_positions.csv` header):
`id,symbol,strike,expiration,contracts,entry_date,entry_cost,entry_receipt_hash,exit_date,exit_proceeds,exit_reason,exit_receipt_hash`
- [ ] **Step 2: Write failing tests for `h10_observe.py`** — it appends one
line per run to `reports/h10/observations.jsonl`:
`{"as_of":..., "receipt":"reports/h10/receipts/h10_watch_<AS_OF>.json", "receipt_sha256":..., "summary":{"fired":[...],"no_signal":[...],"skipped":{...}}, "open_positions": N}`.
Tests: appends exactly one line per as_of (idempotent re-run replaces nothing
and refuses a conflicting duplicate — mirror the `event_id`+hash dedupe idea:
same as_of + same receipt hash → no-op; same as_of + different hash → nonzero
exit and loud message); malformed existing line → nonzero exit, file untouched.
- [ ] **Step 3: Implement, suite green.**
- [ ] **Step 4: Ritual wiring** — add after the H8 step:

```bash
# ---- Step 5b: H10a/b watcher + observation append (forward paper, no orders)
if uv run python -c "import options_researcher.h10_watch" 2>/dev/null; then
  run_step "h10_watch" uv run python -m options_researcher.h10_watch --as-of "$AS_OF"
  run_step "h10_observe" uv run python -m options_researcher.h10_observe --as-of "$AS_OF"
fi
```

(Adapt to the script's actual step-runner helper; H8 at `:174-176` is the
model. If the script uses plain command lines rather than a `run_step` helper,
follow the script's own idiom.) Add `reports/h10/` to the Step-8 allow-list.
- [ ] **Step 5: Verify the ritual script parses** — `bash -n tools/daily_ritual.sh`.
- [ ] **Step 6: Commit** — `feat(h10): paper book, append-only observations, ritual wiring`

### Task 4: H5 `entry_watch` into the ritual with loud FIRE surfacing

**Files:**
- Modify: `tools/daily_ritual.sh` (new step alongside the H6 step at
  `:170-171`; artifact path into the Step-8 allow-list)

`options_researcher/entry_watch.py` prints `{symbol}: WAIT|FIRE ...` lines and
always exits 0 (`entry_watch.py:97-102`, `main()` returns None). Do NOT modify
the module — wrap it:

- [ ] **Step 1: Add the ritual step**

```bash
# ---- Step 4b: H5 LEAPS entry-trigger watch (alert-only; never auto-enters)
EW_OUT="reports/h5/entry_watch_${AS_OF}.txt"
mkdir -p reports/h5
if uv run python -m options_researcher.entry_watch | tee "$EW_OUT"; then
  if grep -q "FIRE" "$EW_OUT"; then
    echo "CRITICAL: H5 ENTRY TRIGGER FIRE — read $EW_OUT and evaluate per H5 CORE rules" >&2
    RITUAL_ALERTS=$((RITUAL_ALERTS+1))
  fi
else
  echo "WARNING: entry_watch failed to run" >&2
fi
```

(Match the script's existing alert/summary variables; if none exists, the
Task 5 receipt is where the alert lands — coordinate with Task 5.) Add
`reports/h5/` to the Step-8 allow-list.
- [ ] **Step 2: `bash -n tools/daily_ritual.sh`** parses clean.
- [ ] **Step 3: Commit** — `feat(h5): entry_watch joins the daily ritual (alert-only)`

### Task 5: Per-hypothesis capture receipt — silence becomes impossible

**Files:**
- Create: `options_researcher/ritual_receipt.py`
- Modify: `tools/daily_ritual.sh` (insert immediately before the Step-8
  durability block at `:208`; receipt path into the allow-list)
- Test: `tests/test_ritual_receipt.py` (create)

Contract: `python -m options_researcher.ritual_receipt --as-of $AS_OF` writes
`reports/ritual/capture_receipt_<AS_OF>.json` summarizing, for each of
H5/H6/H7/H8/H10: `{"status": "CAPTURED"|"NO_SIGNAL"|"REFUSED"|"MISSING", "evidence": <path or null>, "detail": <one line>}`, by checking the existence
and freshness (must be dated AS_OF) of that day's artifacts: H7 = data-gate
receipt + watch output + preflight result; H6/H8 = watcher outputs; H5 =
`reports/h5/entry_watch_<AS_OF>.txt`; H10 = receipt + observation line. Any
`MISSING`/`REFUSED` → exit 1, and the ritual must surface that as a loud
failure line (not abort the durability step — evidence still gets committed).
- [ ] **Step 1: Write failing tests** — synthetic tmp dirs; cases: all present
→ exit 0 with five CAPTURED/NO_SIGNAL entries; one missing → exit 1 and status
MISSING; stale (yesterday-dated) artifact → MISSING with detail "stale".
- [ ] **Step 2: Implement; suite + ruff + pyright green.**
- [ ] **Step 3: Wire into the ritual** before the durability block; add
`reports/ritual/` to the allow-list; `bash -n` clean.
- [ ] **Step 4: Commit** — `feat(ritual): per-hypothesis capture receipt; silent no-op runs impossible`

### Task 6 (GATED — owner ratification required first): H7 real exit + scoring

**Files:** per the SPEC — primarily `options_researcher/h7_event_ledger.py`
(new authority/event types), `options_researcher/h7_session.py` +
`options_researcher/h7_window_registration.py` siblings (exit door),
new scoring module + CLIs, `tests/test_h7_event_ledger.py` and new test files.

**Normative source:** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`
§3–§9 (distinct real-exit authority type; per-session receipt/cache-byte
re-verification; monitoring-session evidence events; decision-vs-evaluation
session split; owner-visible exit/scoring CLIs; ONE durable scoring result;
required tests). Where this plan and the SPEC disagree, the SPEC wins.

- [ ] **Step 0 (owner, not Codex): ratification** — owner reads the SPEC and
records a typed ratification fact in the ledger. Codex MUST refuse to start
without it (the SPEC's own lines 3-4 demand this).
- [ ] **Step 1: test-first per SPEC §9** — extend
`tests/test_h7_event_ledger.py` (follow its `LedgerBase` tempdir pattern) for
each new event type's validation, chain, idempotency, and refusal rules before
implementing; then implement in `h7_event_ledger.py` (`EVENT_TYPES` at
`:52-57` currently has `exit_intent` but no exit-fill/scoring types — extend
exactly as the SPEC names them).
- [ ] **Step 2: exit door + scoring module test-first**, mirroring the
one-door refusal-chain style of `register_window_real`
(`h7_window_registration.py:303`, 9-point refusal chain) — the SPEC defines
the checks; every refusal is a typed, tested error.
- [ ] **Step 3: CLIs** per SPEC §7, following `h7_session.py`'s subcommand
pattern (`:496-592`).
- [ ] **Step 4: full suite + ruff + pyright green; commit in SPEC-delta-sized
units** — `feat(h7): <delta name> per real-exit-scoring SPEC §N`.
- [ ] **Step 5 (Claude + independent agent, not Codex): adversarial review**
of the whole build against the SPEC; PASS/FAIL recorded in the ledger. No
ritual activation in this task.

### Task 7 (GATED on Task 6 review PASS): ritual activation of exit/monitoring sessions

**Files:** `tools/daily_ritual.sh`; possibly a small runbook doc
`docs/superpowers/plans/2026-07-22-h7-operator-runbook.md` (create).

- [ ] **Step 1:** wire the SPEC's monitoring/evaluation session commands into
the ritual after `h7_entry_preflight` (`:159-160`), preserving the one-door
rule: the ritual RECORDS and ALERTS; owner-in-the-loop CLI steps
(`propose|approve|fill`, exit equivalents) remain manual by design — the
ritual never fires them.
- [ ] **Step 2:** operator runbook: the exact command sequence the owner runs
on an ENTRY-OK or EXIT-DUE day, copy-pasteable, with where each receipt lands.
- [ ] **Step 3:** `bash -n` clean; first live rehearsal observed; commit —
`feat(h7): ritual surfaces exit/monitoring sessions; operator runbook`

---

## Plan self-review (done at write time)

Spec coverage: R1→Tasks 6, R2→Task 7, R3→Tasks 1-3, R4→Task 4, R5→Task 5 — all
§3 items covered. Gates: Task 6 Step 0 enforces the SPEC's NOT-BUILD-AUTHORIZED
stamp; Task 7 gates on review PASS. Types/naming: h10 artifact paths
(`reports/h10/receipts/h10_watch_<AS_OF>.json`, `reports/h10/observations.jsonl`)
are used consistently across Tasks 2, 3, 5. Known intentional deviation from
the writing-plans house style: Task 6 contains interface-level rather than
line-level code because its line-level truth is the owner-ratified SPEC — 
duplicating it here would create a second, driftable copy.

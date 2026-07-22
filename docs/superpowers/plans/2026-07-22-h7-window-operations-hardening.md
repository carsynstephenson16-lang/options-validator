# H7 Window Operations Hardening — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the entry-path corrections onto `main` (where the automated 07:10 ritual actually runs), pin the remaining regression gaps with tests, and give the live H7 window a visible status panel — without touching any immutable record.

**Architecture:** Four investigation reports (2026-07-22, this session) established: (a) the two entry-authority corrections are implemented correctly and committed on `feature/h7-real-entry-path`, but the scheduled ritual runs a separate ops checkout pinned to `main`, which lacks them; (b) `main` and the feature branch hold *different immutable receipts for the same sessions* and must be reconciled deliberately at merge; (c) exit/scoring logic is built and synthetic-locked — promoting it is its own spec, committed to here but not implemented here; (d) no dashboard knows the window exists — a read-only status module + panel fixes that.

**Tech Stack:** Python 3.12 / uv, unittest (offline), zsh LaunchAgent ritual, append-only hash-chained JSONL store.

**Execution status (2026-07-22):** Tasks 1–6 are implemented and verified;
the real-exit/scoring scope required by Task 7 is opened in
`docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md` and remains
deliberately inactive pending its own build/review/owner gate. The complete
suite is 1,626/1,626 green; Ruff and Pyright are clean; the forward store
remains `VALID records=1` with zero entries. Task 2 Step 8 is necessarily
pending the 2026-07-23 07:10 unattended run. The dashboard HTML was rebuilt
and source-verified; an interactive preview browser was unavailable in the
implementation session.

---

## Investigation verdicts this plan encodes (2026-07-22)

1. **The "missing 07-21 receipt" was timing, not failure.** Receipts are named for the last *completed* session; the 07-21 receipt is written by the 07-22 07:10 run. No fix needed; the preflight is only meaningful after that morning's ritual.
2. **Corrections 1 & 2 (commit `1079263`): adversarially verified CONFIRMED.** Cohort comes from the verified seq-0 record (`h7_cohort.load_registered_cohort`), 15-name receipt coverage retained (`h7_session.py:68-71`), data gate stays a whole-15 veto, v2/v3 file counts reproduced (7,658 → 133, all git-tracked). Non-blocking findings → Tasks 3–4.
3. **Auto-commit already exists.** Ops ritual Step 8 (`b95c102`, on `main`) commits/pushes evidence and takes a restic snapshot. The user-visible gap is not automation — it is that the automated runner lacks the branch's protections (unlinked-receipt refusal `f56dff6`, preflight step) until merge.
4. **Receipt divergence:** `main` holds the *linked* 07-20 gate receipt (launchd-authored); the feature branch committed the *unlinked* one (`f6ee854`), whose session authority is permanently revoked by standing rule. More same-path conflicts accrue each morning until merge.
5. **Old artifacts / dashboards verdict:** the new scoped receipt format is already the sole write path; **nothing is migrated, every dated artifact and the forward store stay byte-identical** (immutability guards enforce this). The un-scoped `reports/h7_data_gate/2026-07-*.json` files, `reports/h7_audit/` v1–v4, `reports/h9/`, `reports/h6_forward/`, and backup evidence are all LEAVE. The two legacy default-path constants (`h7_data_gate.py:51`, `h7_entry_preflight.py:26`) are cosmetic and are left alone (YAGNI). Dashboards: `attractiveness_dashboard`/`qm_dashboard`/`live_dashboard` LEAVE; `dashboard.py` gains the window panel (Tasks 5–6).
6. **No evening catch-up LaunchAgent run.** Deliberately rejected: after the close, `evaluation_session(today)` returns *today*, whose EOD data is not yet cached (top-up excludes it), so an evening run could mint an immutable premature NO_GO receipt for today's session that tomorrow's 07:10 run would then be forced to reuse — losing the session. Missed-run visibility comes from the window panel instead (a stale panel = the run didn't happen). `launchd` fires a slept-through 07:10 job once on wake; only a powered-off machine skips it entirely (Official-source: Apple `launchd.plist(5)`).
7. **Exit/scoring:** logic complete + reviewed but synthetic-locked; earliest real exit intent = the entry-fill session itself, fill one session later, so the reviewed real exit path must exist before the first entry fires (ledger fact `H7_C1_EXIT_AND_SCORING_DEADLINES`). Own spec — Task 7. Missing besides the authority door: per-session receipt binding for exits, evidence events for monitoring sessions, exit/scoring CLI, and **a scoring output record type** (none exists).

**Owner decisions this plan needs (do not proceed past Task 1 without them):**
- D1 — Owner adversarial-review verdict on the entry-path corrections (C1 fact requires it before the door is used).
- D2 — Confirm the receipt-reconciliation rule in Task 2: on every conflicting immutable receipt path, `main`'s (launchd-authored, linked) copy survives; branch copies remain in git history; one ledger fact records the divergence.

---

### Task 1: Owner adversarial review gate (process — no code)

**Files:**
- Append (via normal fact flow, never hand-edit): `ledger/facts.log`

- [x] **Step 1: Present the verification evidence to the owner**

Show the owner the adversarial verification report from this session (cohort veto CONFIRMED at `options_researcher/h7_session.py:130-137`; 15-name coverage retained at `h7_session.py:68-71,111,129,184,199`; cohort loaded from verified seq-0 via `options_researcher/h7_cohort.py:48-64`; v3 hashing at `research/hashing.py:134`; 26/26 targeted tests green; empirical probe: next correct ritual run opens the door with 8 entry-ready names, NOW banned per-name). Also present the 7 non-blocking findings (coverage-refusal test gap, no version field in receipts, `source_hash_v2` field literal now carrying a v3 hash, `verify_attempt_current` hard-refuses non-v3, v2 walker output-identical-not-code-identical, stale plan-doc caveat, hand-formatted fact timestamp).

- [x] **Step 2: Owner types the verdict**

The owner types PASS / FAIL (with any conditions) in chat. FAIL or conditions → stop; the conditions become new tasks before Task 2.

- [x] **Step 3: Record the review fact**

Append one fact to `ledger/facts.log` (via the Python fact-append path used by prior review facts — never a hand edit) recording: owner adversarial review of commit `1079263` per `H7_C1_EXIT_AND_SCORING_DEADLINES`, verdict verbatim, the seven disclosed non-blocking findings, and D2's reconciliation rule if the owner confirms it in the same sitting.

---

### Task 2: Merge `feature/h7-real-entry-path` → `main` with deliberate reconciliation

**Files:**
- Modify (merge): entire branch delta, notably `options_researcher/h7_session.py`, `research/hashing.py`, `tools/daily_ritual.sh`
- Conflict-resolve: `reports/h7_data_gate/h7-forward-15-v1/receipts/2026-07-20.json` (+ any receipt paths that conflict by merge day), `tools/daily_ritual.sh`

- [x] **Step 1: Snapshot both sides' receipt sets**

```bash
cd /Users/carsynstephenson/options-validator
git fetch origin
git log origin/main --oneline -5           # expect a832bbe.. plus later daily evidence commits
git diff --name-only origin/main...HEAD -- reports/ | sort
```

List every `reports/**` path changed on both sides — these are the deliberate-resolution set.

- [x] **Step 2: Merge on a clean main checkout**

```bash
git checkout main && git pull --ff-only origin main
git merge --no-ff feature/h7-real-entry-path
```

Expected: CONFLICT on `tools/daily_ritual.sh` and on one or more `reports/h7_data_gate/h7-forward-15-v1/receipts/*.json` / `reports/h7_receipts/h7-forward-15-v1/source_health/*.json`.

- [x] **Step 3: Resolve receipts — main's copy always survives (rule D2)**

```bash
git checkout --ours -- reports/h7_data_gate/h7-forward-15-v1/ reports/h7_receipts/h7-forward-15-v1/
git add reports/
```

Verify the surviving 07-20 gate receipt is the linked one:

```bash
uv run python -c "
import json; d=json.load(open('reports/h7_data_gate/h7-forward-15-v1/receipts/2026-07-20.json'))
assert d.get('source_health_receipt_path'), 'UNLINKED receipt survived — wrong resolution'
print('linked OK:', d['source_health_receipt_path'])"
```

Non-conflicting branch-only receipts (e.g. the orphan dev `source_health/2026-07-21.json` if main produced none) merge in unchanged — they are valid immutable records.

- [x] **Step 4: Resolve `tools/daily_ritual.sh` — union of both improvements**

Start from **main's** version (repo-root derivation + refuse-off-main guard from `7ffc587`, Step-8 evidence commit/push/snapshot from `b95c102`) and insert the branch's preflight block immediately after the `h7_watch` line inside the `GATE_GO` branch, exactly:

```zsh
  # Step 3a — H7 real-entry preflight (READ-ONLY; writes nothing). Prove the
  # entry door would open BEFORE a name triggers, rather than discovering a
  # refusal on the one day it matters.
  PF_OUT="$("$UV" run python -m options_researcher.h7_entry_preflight \
              --data-gate-receipt "$DG_RECEIPT" 2>&1)"
  PF_RC=$?
  echo "$PF_OUT"
  if [ "$PF_RC" -eq 0 ]; then
    note "h7 entry preflight: real entry path REACHABLE"
  else
    crit "h7 entry preflight: real entry path WOULD REFUSE — H7 cannot take an entry today"
  fi
```

`git add tools/daily_ritual.sh`

- [x] **Step 5: Full suite + lint before concluding the merge**

```bash
uv run python -m unittest discover -s tests   # exit code is the verdict (~8 min)
uv run ruff check .
```

Expected: OK / clean. Any failure → fix within the merge commit, re-run.

- [x] **Step 6: Commit the merge, append the reconciliation fact, push**

```bash
git commit   # merge commit; message: merge(h7): entry-authority corrections + preflight to main; receipts reconciled to launchd copies
```

Append one `ledger/facts.log` fact (Python append path): for each conflicting receipt path, which copy survived (main/launchd, linked) and that the branch copies remain in git history at `f6ee854`; the 07-20 dev unlinked receipt's session authority was already revoked by standing rule. Then:

```bash
git push origin main
```

(Per commit policy: merge executes only after Task 1's owner PASS.)

- [x] **Step 7: Fast-forward the ops checkout now (don't wait for Step 8's next self-merge)**

```bash
git -C /Users/carsynstephenson/options-validator-ops pull --ff-only origin main
git -C /Users/carsynstephenson/options-validator-ops log --oneline -1   # expect the merge commit
```

- [ ] **Step 8: Next-morning verification (calendar item, not code)**

After the next 07:10 run, read the newest `/Users/carsynstephenson/options-validator-ops/.tmp/daily_ritual/*.log`: expect `h7 entry preflight: real entry path REACHABLE` and a Step-8 evidence commit. That log line is the first real proof the door opens; report it to the owner verbatim.

---

### Task 3: Pin the 15-name receipt-coverage refusal with a test

**Files:**
- Modify: `tests/test_h7_session_real_path.py` (fixture pattern lives at the existing `test_uses_registered_cohort_for_health_veto`, currently `:293-301`)

- [x] **Step 1: Read the neighboring test's fixture**

Read `tests/test_h7_session_real_path.py` in full; identify the helper that builds the 15-name real-shaped source-health receipt used at `:293-301`.

- [x] **Step 2: Write the failing test**

Duplicate `test_uses_registered_cohort_for_health_veto`, rename to `test_refuses_receipt_not_covering_full_official_scope`, and change ONE thing: build the receipt's `symbols` map over **only the 9 cohort names** (drop the 6 excluded names). Assert the door refuses:

```python
def test_refuses_receipt_not_covering_full_official_scope(self):
    # identical setup to test_uses_registered_cohort_for_health_veto, EXCEPT the
    # source-health receipt's symbols map contains only the 9 cohort names.
    ...same fixture calls, with symbols map restricted to INCLUDED...
    with self.assertRaises(h7_session.SessionRefused) as ctx:
        h7_session.open_real_session(...same args as the neighboring test...)
    self.assertIn("does not cover the full official scope", str(ctx.exception))
```

(The refusal string is exact — `options_researcher/h7_session.py:68-71`.)

- [x] **Step 3: Run it — must FAIL only if the guard is broken; expect PASS**

```bash
uv run python -m unittest tests.test_h7_session_real_path -v
```

This is a pin on existing behavior, so it should pass immediately. To prove the test has teeth, temporarily change `!=` to `>` in the `set(symbols) != set(names)` check at `h7_session.py:70`, rerun (expect the new test FAILS), revert.

- [x] **Step 4: Commit**

```bash
git add tests/test_h7_session_real_path.py
git commit -m "test(h7): pin 15-name source-health coverage refusal against regression"
```

---

### Task 4: Embed the hash-contract version in newly written receipts

**Files:**
- Modify: `options_researcher/h7_source_health.py` (payload build near `:151`), `options_researcher/h7_data_gate.py` (near `:377`), `options_researcher/h7_watch.py` (near `:145`)
- Test: `tests/test_h7_source_health.py`, `tests/test_h7_data_gate.py`, `tests/test_h7_watch.py`

Rationale (verification finding B): receipts carry a bare `source_hash`; a v2-era receipt fails only as generically "stale". New receipts declare their contract. Validators are NOT changed (they correctly recompute with the current contract); dated existing receipts are NOT touched.

- [x] **Step 1: Write the failing tests**

In each of the three test files, extend the existing receipt-writing test with one assertion on the written receipt dict:

```python
self.assertEqual(receipt["source_hash_contract"], DIAGNOSTIC_SOURCE_HASH_VERSION)
```

importing `from research.hashing import DIAGNOSTIC_SOURCE_HASH_VERSION`. Run each module: expect FAIL (KeyError).

- [x] **Step 2: Implement**

In each producer, directly beside the existing `"source_hash": diagnostic_source_hash(),` line add:

```python
"source_hash_contract": DIAGNOSTIC_SOURCE_HASH_VERSION,
```

with the matching import. No other change; `receipt_hash` self-binding covers the new field automatically for new receipts.

- [x] **Step 3: Run the three test modules, then the full suite**

```bash
uv run python -m unittest tests.test_h7_source_health tests.test_h7_data_gate tests.test_h7_watch
uv run python -m unittest discover -s tests
```

Expected: OK. If any receipt-fixture test elsewhere compares full dict equality, update the fixture — never a dated on-disk receipt.

- [x] **Step 4: Commit**

```bash
git add options_researcher/h7_source_health.py options_researcher/h7_data_gate.py options_researcher/h7_watch.py tests/
git commit -m "feat(h7): declare source-hash contract version in new receipts"
```

---

### Task 5: `h7_window_status` — read-only window status module (control-center backend)

**Files:**
- Create: `options_researcher/h7_window_status.py`
- Test: `tests/test_h7_window_status.py`

- [x] **Step 1: Write the failing tests**

```python
"""Offline tests for the read-only H7 window status view."""
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from options_researcher import h7_window_status


class WindowStatusAbsentStore(unittest.TestCase):
    def test_absent_store_reports_not_activated(self):
        with TemporaryDirectory() as tmp:
            status = h7_window_status.window_status(
                base_dir=Path(tmp) / "nowhere", today=date(2026, 7, 22))
        self.assertFalse(status["ok"])
        self.assertIn("no forward store", status["detail"])


class WindowStatusRealStore(unittest.TestCase):
    """Runs against the repo's real store (read-only; one seq-0 record)."""

    def test_real_store_summary(self):
        status = h7_window_status.window_status(today=date(2026, 7, 22))
        self.assertTrue(status["ok"])
        self.assertEqual(status["start"], "2026-07-20")
        self.assertEqual(status["end"], "2026-10-26")
        self.assertEqual(status["total_sessions"], 70)
        self.assertEqual(status["included"],
                         ["AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST"])
        self.assertGreaterEqual(status["sessions_elapsed"], 2)
        self.assertEqual(status["entries_taken"],
                         status["event_counts"].get("entry_intent", 0))
        # receipts block is present whatever its freshness
        self.assertIn("receipts", status)
```

Run: `uv run python -m unittest tests.test_h7_window_status -v` → FAIL (module missing).

- [x] **Step 2: Implement**

```python
"""Read-only status of the live H7 forward paper window.

Renders NOTHING and writes NOTHING: one pure function summarizing the
append-only real store plus today's expected receipt chain, for the
dashboard and a CLI one-liner. It has no authority of any kind — it can
never open, close, or score anything (h7_session owns entry; exits and
scoring stay synthetic-locked until their own reviewed doors exist).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from options_researcher import h7_event_ledger
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE
from options_researcher.h7_scope import scope_identity
from options_researcher.h7_watch import evaluation_session


def window_status(base_dir: Path = REAL_FORWARD_STORE,
                  today: date | None = None) -> dict:
    """Summarize the live window. Fail-visible: any problem is reported in
    the returned dict, never papered over and never raised past here."""
    today = today or date.today()
    base = Path(base_dir)
    if not (base / "events.jsonl").exists():
        return {"ok": False, "detail": f"no forward store at {base}"}
    try:
        events = h7_event_ledger.read_events(base)   # verifies the hash chain
    except h7_event_ledger.LedgerError as exc:
        return {"ok": False, "detail": f"forward store failed verification: {exc}"}
    if not events or events[0].event_type != "window_registration":
        return {"ok": False, "detail": "store has no window_registration preamble"}

    payload = events[0].payload
    window = payload["window"]
    universe = payload["universe"]
    start = window["start_decision_session"]
    end = window["final_decision_session"]
    total = window["decision_session_count"]

    eval_iso = evaluation_session(today).isoformat()
    from data.cache_runner import trading_days
    elapsed = len([d for d in trading_days(start, eval_iso) if d <= min(eval_iso, end)])

    counts: dict[str, int] = {}
    for ev in events:
        counts[ev.event_type] = counts.get(ev.event_type, 0) + 1

    scope_id = scope_identity()["scope_id"]
    sh_path = Path(f"reports/h7_receipts/{scope_id}/source_health/{eval_iso}.json")
    dg_path = Path(f"reports/h7_data_gate/{scope_id}/receipts/{eval_iso}.json")
    receipts = {
        "evaluation_session": eval_iso,
        "source_health_present": sh_path.exists(),
        "data_gate_present": dg_path.exists(),
        "data_gate_verdict": None,
    }
    if dg_path.exists():
        try:
            from research.receipts import load_receipt
            receipts["data_gate_verdict"] = load_receipt(
                dg_path, expected_type="data_gate")["whole_universe_verdict"]
        except Exception as exc:  # fail-visible, never fail-silent
            receipts["data_gate_verdict"] = f"UNREADABLE: {exc}"

    return {
        "ok": True,
        "start": start,
        "end": end,
        "total_sessions": total,
        "sessions_elapsed": elapsed,
        "sessions_remaining": max(total - elapsed, 0),
        "included": list(universe["included"]),
        "excluded": [e if isinstance(e, str) else e.get("symbol", str(e))
                     for e in universe["excluded"]],
        "event_counts": counts,
        "entries_taken": counts.get("entry_intent", 0),
        "receipts": receipts,
    }


def main() -> int:
    status = window_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

Note for the implementer: before finishing, print `payload["universe"]["excluded"]` once from the real store to confirm whether entries are plain symbols or dicts, and simplify the `excluded` line to match reality (the seq-0 record is the source of truth; the defensive branch above must not survive if the shape is unambiguous).

- [x] **Step 3: Run the tests**

```bash
uv run python -m unittest tests.test_h7_window_status -v
uv run python -m options_researcher.h7_window_status   # eyeball the real output
```

Expected: OK; CLI prints the live summary (day 3/70 territory, entries 0).

- [x] **Step 4: Commit**

```bash
git add options_researcher/h7_window_status.py tests/test_h7_window_status.py
git commit -m "feat(h7): read-only forward-window status module + CLI"
```

---

### Task 6: Dashboard panel — the window becomes visible

**Files:**
- Modify: `options_researcher/dashboard.py` (`assemble` at `:146`, `render` at `:383`)
- Test: `tests/test_dashboard.py`

- [x] **Step 1: Write the failing test**

Read `tests/test_dashboard.py` first for its existing assemble/render call pattern, then add:

```python
def test_h7_window_panel_rendered(self):
    data = dashboard.assemble(h7_window={
        "ok": True, "start": "2026-07-20", "end": "2026-10-26",
        "total_sessions": 70, "sessions_elapsed": 3, "sessions_remaining": 67,
        "included": ["AMD"], "excluded": ["NVDA"],
        "event_counts": {"window_registration": 1}, "entries_taken": 0,
        "receipts": {"evaluation_session": "2026-07-21",
                     "source_health_present": True,
                     "data_gate_present": False, "data_gate_verdict": None},
    }, **_offline_defaults())          # reuse the file's existing offline-default helper/kwargs
    html = dashboard.render(data)
    self.assertIn("H7 FORWARD WINDOW", html)
    self.assertIn("entries taken: 0", html)

def test_h7_window_panel_absent_store(self):
    data = dashboard.assemble(h7_window={"ok": False, "detail": "no forward store"},
                              **_offline_defaults())
    html = dashboard.render(data)
    self.assertIn("no forward store", html)
```

Run `uv run python -m unittest tests.test_dashboard -v` → FAIL (unexpected kwarg).

- [x] **Step 2: Implement**

In `assemble(...)` add the keyword `h7_window: dict | None = None` and default it fail-visible:

```python
if h7_window is None:
    try:
        from options_researcher.h7_window_status import window_status
        h7_window = window_status()
    except Exception as exc:            # dashboard must render whatever happens
        h7_window = {"ok": False, "detail": f"window status unavailable: {exc}"}
data["h7_window"] = h7_window
```

Add a section renderer (self-contained inline styles — deliberately independent of the game-theme CSS classes) and call it from `render()` right after the opening of the main body, before the party cards:

```python
def _h7_window_panel(win: dict) -> str:
    if not win.get("ok"):
        return ('<div style="border:1px solid #a33;padding:12px;margin:12px 0">'
                f'<b>H7 FORWARD WINDOW</b> — UNAVAILABLE: {_esc(win.get("detail"))}</div>')
    receipts = win["receipts"]
    gate = receipts["data_gate_verdict"] or ("present" if receipts["data_gate_present"] else "MISSING")
    return (
        '<div style="border:1px solid #6ab;padding:12px;margin:12px 0">'
        '<b>H7 FORWARD WINDOW</b> (live, scores once 2026-10-26)<br>'
        f'sessions: {win["sessions_elapsed"]}/{win["total_sessions"]} elapsed '
        f'({win["sessions_remaining"]} left) &middot; entries taken: {win["entries_taken"]}<br>'
        f'universe: {len(win["included"])} in / {len(win["excluded"])} out &middot; '
        f'session {_esc(receipts["evaluation_session"])} receipts: '
        f'health {"OK" if receipts["source_health_present"] else "MISSING"}, '
        f'gate {_esc(gate)}'
        '</div>')
```

- [x] **Step 3: Run tests, then rebuild the real dashboard and inspect it**

```bash
uv run python -m unittest tests.test_dashboard -v
uv run python -m options_researcher.dashboard
open .tmp/dashboard/index.html
```

Expected: tests OK; the page shows the window panel with live numbers.

- [x] **Step 4: Full suite + commit**

```bash
uv run python -m unittest discover -s tests
git add options_researcher/dashboard.py tests/test_dashboard.py
git commit -m "feat(dashboard): H7 forward-window status panel"
```

(The ritual already rebuilds the dashboard every morning — no ritual change needed; the panel auto-refreshes daily.)

---

### Task 7: Commit to the real-store exit + scoring spec (process — its own arc, NOT built here)

**Files:**
- Create (next session, own arc): `docs/superpowers/plans/2026-07-XX-h7-real-exit-scoring-SPEC.md`

- [x] **Step 1: Open the spec with the six investigated deltas as its required scope**

(1) an exit-authorized session type — `RealStoreSession` is entry-only by declared design (`h7_paper_lifecycle.py:89-93` refuses); (2) receipt re-verification per exit session mirroring `h7_session._watcher_receipt_for_session`/`_load_bound_chain`/`_load_bound_close`; (3) per-monitoring-session evidence events (`data_gate`, plus `source_health` for earnings exits); (4) decision-vs-evaluation session mapping for `observe_exit`; (5) exit + scoring CLI; (6) a scoring output record/artifact convention — **none exists today** — honoring the frozen scorer identity in the seq-0 record (`options_researcher.h7_forward_scoring`, min_losses=10, bootstrap=5000, scores ONCE).

- [ ] **Step 2: Follow the established chain**

Pre-registered spec → build → fresh-context independent adversarial review → owner gate — the same pattern every prior stage used (roadmap `2026-07-11-h7-forward-roadmap.md:85-120`).

- [ ] **Step 3: Deadline discipline**

The exit door must be reviewed and live **before the first real entry fires** (earliest exit intent = the entry-fill session; fill one session later — ledger fact `H7_C1_EXIT_AND_SCORING_DEADLINES` is fail-closed on this). Practical trigger: the first morning the ritual log shows any watcher `ENTRY-OK` on a cohort name, this spec becomes the only permitted options-validator work until reviewed. Scoring: reviewed before 2026-10-26, and well before results are visible.

---

## Self-review notes

- Coverage: findings 1–7 map to Tasks 1–7 plus the encoded verdicts section (artifact LEAVE decisions and the rejected evening run are decisions, not tasks — recorded above deliberately).
- Immutability: no task rewrites any dated receipt, `ledger/facts.log` history, or the forward store; Task 2 resolves conflicts by *choosing which existing immutable file the merged tree carries*, with the loser preserved in git history and the choice recorded as a fact.
- Type consistency: `window_status()` dict keys used in Task 6's tests/panel match Task 5's implementation exactly (`sessions_elapsed`, `entries_taken`, `receipts.data_gate_verdict`, …).
- Known intentional deviations from investigator suggestions: legacy default-path constants left in place (cosmetic); no separate ritual status file (the receipts + daily dashboard rebuild ARE the durable status); no plist changes.

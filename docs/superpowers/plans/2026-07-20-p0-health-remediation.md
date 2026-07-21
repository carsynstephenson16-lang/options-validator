# P0 Health Remediation Plan (Codex handoff)

> **For agentic workers:** Execute task-by-task, in order, test-first. Steps use
> checkbox (`- [ ]`) syntax for tracking. Every claim of "done" requires the
> verification command's exit code, not a grep of its output.

**Goal:** Make the live H7 forward window operationally trustworthy — canonical
checkout, honest ritual exit status, frozen cohort enforced, a reviewed real
entry path, the H7c cutoff finished test-first — and close the two non-H7 P0
integrity holes (OOS reveal data binding, attractiveness badge honesty).

**Architecture:** Four phases. A merges the reviewed repo-rag branch into
`main`, parks the not-yet-ready market-data bundle on its own branch, and
restores canonical operations (no new Python). B makes `main`'s suite green
post-activation and adds the one missing primitive — a reader that loads the
frozen 9-name cohort back out of the immutable seq-0 registration — then wires
the watcher to it. C opens a single authorized real-store path for the ENTRY
side only (decisions → owner approval → fills), leaving exits/scoring
synthetic-only with declared deadlines, and finishes the H7c report-gated exit
test-first. D binds OOS reveals to actual cache bytes + coverage and stops the
attractiveness board from fabricating zeros or reading future-dated rows.

**Tech stack:** Python 3.12 / uv / unittest (offline, no network), zsh, launchd.

**Source of facts:** repo health review 2026-07-20 + direct code extraction the
same day. Line numbers cited below were verified 2026-07-20 on `main` @6701b70
unless noted. Per `.cursorrules`, re-verify every signature against the
installed code before trusting it.

---

## Standing rules for this work (do not skip)

- **Never** hand-edit `ledger/h7_forward/{events.jsonl,HEAD}` or any file under
  a real or fixture H7 store — append only via the typed API. `ledger/facts.log`
  is append-only (a union merge driver exists for it).
- Suite command: `uv run python -m unittest discover -s tests` (module-path
  form `python -m unittest tests.X` fails — no `tests/__init__.py`; use
  discovery, or pytest for a single file).
- Verdict on any run = **exit code**, never grepped output.
- Commit each test-green unit (owner's standing commit policy). Never rewrite
  pushed history. Merges of Phases B–D branches into `main` are the owner's
  call; **Phase A's merge of `feature/repo-rag-phases-3-6` into `main` is
  owner-authorized (Carsyn, 2026-07-20)** — the repo-rag work is reviewed and
  complete (10 commits, 68 tests, eval 4/4). The not-yet-ready market-data
  bundle is uncommitted working-tree state and is explicitly kept OFF `main`
  (parked in A1).
- Alert-only boundary is untouched: nothing in this plan places orders or adds
  a trigger path.
- **Until Task B2 lands:** the watcher still evaluates all 15 names. The owner
  must treat any ENTRY-OK for a name outside the frozen cohort
  `[AMD, AMZN, CEG, ET, MSFT, NOW, PLTR, TEM, VST]` as noise. No launchd pause
  is needed (the ritual is alert-only), but Phase A + B are same-priority
  urgent.

---

## Phase A — Merge repo-rag into main + restore canonical operations (do first, same day)

Verified 2026-07-20: the operational checkout
`/Users/carsynstephenson/options-validator` is on `feature/repo-rag-phases-3-6`
@12b3dcf, 11 commits ahead of `main`. Those 11 commits are **10 repo-rag
commits + the ritual fix `12b3dcf`** — all reviewed, tested, owner-cleared to
merge. Everything else is **uncommitted working-tree state**: modified tracked
files (`.env.example`, `.gitignore`, `ledger/facts.log`) and a large untracked
bundle (`market_data/`, `tools/third_party/`, `tools/bs_parity/`,
`tools/financepy_validation/`, `tools/openbb_equity_research/`,
`docs/research/notebooklm-modern-ai/`, `MARKET_DATA_PROVIDERS.md`,
`MCP_SETUP_REPORT.md`, `SECURITY.md`, `.agents/skills/architecture-reviewer/`,
`reports/h7_data_gate/h7-forward-15-v1/`, `reports/h7_receipts/`,
`tests/test_market_data_stack.py`, `tools/playwright_mcp_readonly_proxy.mjs`,
`docs/superpowers/plans/2026-07-18-cross-repo-external-quant-integration-map.md`).
Because that bundle is uncommitted, it does NOT ride the merge; A1 parks it so
only the reviewed repo-rag work lands on `main`. `ledger/facts.log` diverges in
committed history too, but `.gitattributes` already carries
`ledger/facts.log merge=union`, so the merge auto-unions it (no manual
resolution expected).

### Task A1: Park the not-ready market-data bundle on its own branch (keep it OFF main)

The `.env.example` working-tree edit dropped `SEC_USER_AGENT` and
`OPTIONS_CACHE_DIR` (a regression — code still reads both); `main`'s
`.env.example` keeps the correct versions, and this task quarantines the
regression on the parking branch rather than fixing it inline.

- [ ] **Step 1:** From the current checkout (on `feature/repo-rag-phases-3-6`),
  cut a parking branch and commit ALL the in-flight working-tree state there —
  tracked modifications + the untracked bundle — but leave THIS plan file
  untracked so it survives the later `git checkout main` and lands on `main`
  in A3:

```bash
git checkout -b parking/market-data-bundle-2026-07-20
git add -A -- ':!docs/superpowers/plans/2026-07-20-p0-health-remediation.md'
git commit -m "park: in-flight market-data/tooling bundle + env/gitignore edits, NOT for main (P1 hardening pending)"
git push origin parking/market-data-bundle-2026-07-20
```

- [ ] **Step 2:** Confirm the repo-rag branch ref is unchanged and the tree is
  clean except the plan file:

```bash
git rev-parse feature/repo-rag-phases-3-6   # still 12b3dcf
git status --porcelain                       # exactly one ?? line: the plan file
```

If any other tracked modification lingers, stop — the merge must start from a
clean tree.

### Task A2: Merge feature/repo-rag-phases-3-6 into main

- [ ] **Step 1:** Confirm the union driver is live (it is, per above) so
  `facts.log` auto-resolves: `git check-attr merge -- ledger/facts.log` →
  `ledger/facts.log: merge: union`.
- [ ] **Step 2:** Switch to `main` and merge. The untracked plan file rides
  along untouched.

```bash
git checkout main && git pull --ff-only
git merge --no-ff feature/repo-rag-phases-3-6 -m "merge: repo-rag phases 3-6 (reviewed; 68 tests, eval 4/4) into main"
```

If any conflict surfaces OUTSIDE `ledger/facts.log`, stop and report — do not
resolve broad conflicts silently. A `facts.log` conflict should not appear
(union driver); if it somehow does, keep BOTH sides' lines, never drop entries.
- [ ] **Step 3:** Full suite on the merge result. Expect only the 5 known stale
  H7 failures from Task B1 (`test_h7_stage8_real_append`, `test_h7_one_door`,
  `test_h7_trim_at_append`, `test_h7_activation_guard`,
  `test_h7_stage7_synthetic_proof` — all stale
  "real-store-is-empty" assumptions, fixed in Phase B) and nothing else new:

```bash
uv run python -m unittest discover -s tests
uv run ruff check .
```

If any failure beyond those 5 appears, stop and report — the merge introduced a
regression that must be understood before pushing.
- [ ] **Step 4:** These 5 stale failures already fail on plain `main` @6701b70
  (they broke at activation, independent of this merge — the merge introduces
  none of them). To avoid pushing an already-red `main` and leaving it red
  until Phase B, **apply Task B1's test-only fixes now, on top of the merge
  commit, before pushing** — run B1 Steps 1-5, confirm the full suite is 0
  failures, then `git push origin main` (owner-authorized, see standing rules).
  This greens `main` with the merge. Task B1 is then already complete; Phase B
  continues at Task B2. (B1 is pure test hygiene — no guard or ledger code
  changes — so folding it into the authorized Phase A push is safe.)

### Task A3: Verify the ledger, commit the plan, confirm operations

The operational checkout is now on `main` (from A2). launchd needs no change —
its plist already targets this directory
(`com.carsyn.options-validator.daily-ritual.plist`, WorkingDirectory
`/Users/carsynstephenson/options-validator`).

- [ ] **Step 1:** Confirm branch + activated ledger:

```bash
git branch --show-current                                    # main
uv run python -m options_researcher.h7_event_ledger verify   # VALID, 1 record (seq-0 window_registration)
```

If verify reports EMPTY, stop — you are not in the canonical checkout.
- [ ] **Step 2:** Commit this plan file on `main`:

```bash
git add docs/superpowers/plans/2026-07-20-p0-health-remediation.md
git commit -m "docs: P0 health remediation plan (2026-07-20 review)"
git push origin main
```

- [ ] **Step 3:** Run the ritual once by hand and read the log it writes to
  `.tmp/daily_ritual/`:

```bash
/bin/zsh tools/daily_ritual.sh; echo "exit=$?"
```

Expected: receipts now link (no "watcher will refuse" note); the ritual fix
`12b3dcf` is present because the merge brought it in.

### Task A4: Make the ritual exit nonzero on infrastructure failures

`tools/daily_ritual.sh` currently ends with unconditional `exit 0` (line 146,
as merged in from `12b3dcf`). Distinguish **designed stops** (data-gate NO_GO with a valid
receipt chain — "the system working", stays exit 0) from **broken
infrastructure** (missing receipts, watcher crash, unresolvable session), which
must exit 1 so launchd/`launchctl list` and any future alerting can see it.

- [ ] **Step 1:** Edit `tools/daily_ritual.sh`. Add after the `note()`
  definition (line 21):

```zsh
CRITICAL=0
crit() { CRITICAL=1; note "CRITICAL: $1"; }
```

- [ ] **Step 2:** Route these existing failure branches through `crit` instead
  of `note` (keep the message text, drop the old `note` call):
  - source-health receipt missing (line 66-69 block): the "gate runs unlinked;
    watcher will refuse" branch.
  - data gate exited 0 but `DG_RECEIPT` is empty (add this check inside the
    `DG_RC -eq 0` branch): `[ -z "$DG_RECEIPT" ] && crit "data gate GO but receipt path not captured"`.
  - `h7_watch: NONZERO EXIT` (line 99).
  - evaluation-session resolution failure (line 91-94 block).

  Leave as plain `note`: topup failure/skip (runs on cache by design), data
  gate NO_GO with receipts intact, dashboard rebuild failures, H6/H8/QM legs.
- [ ] **Step 3:** Replace the final `exit 0` (line 146):

```zsh
if [ "$CRITICAL" -eq 1 ]; then
  echo "RITUAL STATUS: BROKEN (see CRITICAL lines above)"
  exit 1
fi
echo "RITUAL STATUS: OK"
exit 0
```

Also prefix the osascript notification title with `[BROKEN] ` when
`CRITICAL=1` so a failed unattended run is visible without opening the log.
- [ ] **Step 4:** Verify both paths by hand: run once normally (`exit=0`
  expected), then run once with the source-health receipt forced missing, e.g.
  `SH_RECEIPT=""` injected by temporarily exporting a bogus
  `THETADATA_API_KEY` is NOT sufficient — instead test the branch directly:

```bash
zsh -n tools/daily_ritual.sh   # syntax check
/bin/zsh tools/daily_ritual.sh; echo "exit=$?"   # normal run
```

For the failure path, temporarily rename the source-health module invocation
target is overkill; it is acceptable to verify by code review that every
`crit` call site is reachable and that `CRITICAL` propagates (the script has
no subshell around those branches — check the `SH_OUT="$( ... )"` command
substitutions do not swallow `crit`, which they don't because `crit` is called
outside them).
- [ ] **Step 5:** Commit on main: `git add tools/daily_ritual.sh && git commit -m "fix(ritual): nonzero exit + BROKEN status on infrastructure failures" && git push origin main`.

### Task A5: Tighten .env permissions

- [ ] **Step 1:** `chmod 600 .env && stat -f "%Lp" .env` → `600`.
  (No commit — `.env` is gitignored.)

---

## Phase B — Green main + frozen cohort (branch `fix/h7-post-activation-tests` off main)

### Task B1: Make the five stale activation tests phase-aware

Each fails because it encodes "the real store is empty" — true pre-activation,
now stale (the real store correctly holds the seq-0 record). Exactly one test
per file fails; the "untouched" comparisons (`_assert_real_store_untouched`,
before/after equality) already pass and stay. **None of these are guard/logic
regressions — the production code is correct; only the tests' expectations are
stale. Do NOT change any guard or ledger code to make them pass.**

Codex confirmed two further stale files during the A2 merge gate (2026-07-20)
that were not in the original review's list of three:
`test_h7_activation_guard.py:90` needs a distinct readonly-snapshot assertion,
and `test_h7_stage7_synthetic_proof.py:39` needs the same valid-and-untouched
assertion as the first three.

**Files:**
- Modify: `tests/test_h7_stage8_real_append.py:243`
- Modify: `tests/test_h7_one_door.py:383`
- Modify: `tests/test_h7_trim_at_append.py:203`
- Modify: `tests/test_h7_activation_guard.py:90`
- Modify: `tests/test_h7_stage7_synthetic_proof.py:39`

- [ ] **Step 1:** In `test_h7_stage8_real_append.py` line 243 and
  `test_h7_trim_at_append.py` line 203, replace

```python
self.assertTrue(before.valid and before.empty)
```

with

```python
# Phase-aware: pre-activation the real store is VALID EMPTY; post-activation
# (2026-07-20, seq-0 window_registration) it is VALID non-empty. The invariant
# under test is "valid and UNTOUCHED by this operation", not "empty".
self.assertTrue(before.valid)
```

- [ ] **Step 2:** `tests/test_h7_one_door.py:383`
  (`test_activation_lands_seq0_with_receipt_hashes_in_payload`) asserts
  `real_before.valid and real_before.empty` and then expects activation to land
  seq-0. Post-activation that can only run against an **isolated fixture
  store**, never the repo store. Read the test: if its
  `register_window_real(..., base_dir=...)` already targets a tmp fixture and
  only the *precondition* reads the repo store, apply the same Step-1
  replacement. If the test actually appends to the repo store path, redirect
  its `base_dir` to a `tempfile.TemporaryDirectory()` fixture seeded empty, and
  keep asserting seq-0 lands **in the fixture** while the repo store is
  untouched (mirror the `_assert_real_store_untouched` pattern at
  `tests/test_h7_trim_at_append.py:194-200`).
- [ ] **Step 3 (the fourth file):** `tests/test_h7_activation_guard.py:90`,
  `test_real_store_readonly_snapshot_allowed`. This test points at the REAL
  store (`forward_base=REAL_FORWARD_STORE, allow_real_readonly=True`) and
  asserts the activation guard's `ledger_valid_empty` check is `.ok == True`.
  That was only true when the real store was empty; post-activation the check
  correctly reports not-ok. **The guard is right — this is exactly the check
  that would refuse a second activation.** The real point of THIS test (vs the
  tmp-base tests) is that a read-only snapshot of the real store is *allowed*
  (does not raise `ActivationBoundaryError`), which the sibling test
  `test_real_store_refused_without_readonly_flag` (line 92) covers for the
  no-flag path. Make it phase-aware — replace line 90:

```python
self.assertTrue(report.by_name["ledger_valid_empty"].ok)
```

with

```python
# Phase-aware: post-activation (2026-07-20) the real store is correctly
# non-empty, so the ledger_valid_empty precondition now reports not-ok — that
# is the guard working (it would refuse a second activation). The invariant
# this test guards is that allow_real_readonly lets the snapshot run WITHOUT
# raising; assert the report was produced and the check ran, not that it is ok.
self.assertIn("ledger_valid_empty", report.by_name)
self.assertFalse(report.by_name["ledger_valid_empty"].ok)
```

Do not touch `options_researcher/h7_activation_guard.py`.
- [ ] **Step 4 (the fifth file):**
  `tests/test_h7_stage7_synthetic_proof.py:39` runs the proof against a
  temporary fixture, then verifies the real store was unchanged. Replace

```python
self.assertTrue(before.empty)
```

with a phase-aware valid-and-untouched assertion:

```python
# Phase-aware: after Stage 8 activation the real store correctly has seq-0.
# This synthetic-only proof must leave it valid and untouched, not require it
# to be empty.
self.assertTrue(before.valid)
```

- [ ] **Step 5:** Run the five files individually (pytest for single files),
  then the full suite:

```bash
uv run python -m pytest tests/test_h7_stage8_real_append.py tests/test_h7_one_door.py tests/test_h7_trim_at_append.py tests/test_h7_activation_guard.py tests/test_h7_stage7_synthetic_proof.py -q
uv run python -m unittest discover -s tests
```

Expected: 0 failures. If any OTHER failure appears, it is not part of this
stale-empty class — stop and report it rather than folding it in blindly.
- [ ] **Step 6:** Commit: `git commit -am "test(h7): phase-aware real-store preconditions after Stage 8 activation (incl. activation-guard readonly snapshot)"`.

### Task B2: Enforce the frozen 9-name cohort from the seq-0 registration

**The gap (verified):** no production code reads the registered cohort back.
`h7_watch.py:356` builds `names = watch_universe()` — the full 15-name scope
from `options_researcher/h7_scope.py:63` — so an excluded name turning
source-healthy could receive ENTRY-OK. The only code that parses
`payload["universe"]` back out of the store is a test
(`tests/test_h7_trim_at_append.py:211-219`).

**Design:** one new read-only module + a watcher change. The data gate stays
whole-universe (its receipts cover all 15; receipt validation keeps the full
list). Entry evaluation shrinks to the frozen included cohort. Fail-closed
bonus: if the real store has no activation record (i.e. someone runs from a
non-canonical checkout again), the loader raises and the watcher refuses to
run — the exact failure mode that motivated Phase A becomes loud.

**Files:**
- Create: `options_researcher/h7_cohort.py`
- Modify: `options_researcher/h7_watch.py:356` (and the entry-evaluation loop below it)
- Test: `tests/test_h7_cohort.py`

- [ ] **Step 1:** Write the failing tests in `tests/test_h7_cohort.py`.
  Build a fixture store with the synthetic door
  (`h7_window_registration.register_window` with a `universe_manifest` whose
  `included` = the 9 names and `excluded` = 6 names with reasons — reuse the
  manifest-building helpers already used by `tests/test_h7_trim_at_append.py`):

```python
import tempfile
import unittest
from pathlib import Path

from options_researcher.h7_cohort import CohortUnavailableError, load_registered_cohort

INCLUDED = ["AMD", "AMZN", "CEG", "ET", "MSFT", "NOW", "PLTR", "TEM", "VST"]


class CohortLoaderTests(unittest.TestCase):
    def test_loads_frozen_included_and_excluded_from_seq0(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _register_fixture_window(base, included=INCLUDED)  # helper per trim-test pattern
            cohort = load_registered_cohort(base_dir=base)
            self.assertEqual(sorted(cohort.included), INCLUDED)
            self.assertEqual(len(cohort.excluded), 6)

    def test_empty_store_raises_typed_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(CohortUnavailableError):
                load_registered_cohort(base_dir=Path(tmp))

    def test_first_event_not_registration_raises(self):
        ...  # append a non-registration first event to a fixture; expect CohortUnavailableError
```

- [ ] **Step 2:** Run them, confirm they fail with `ModuleNotFoundError`.
- [ ] **Step 3:** Implement `options_researcher/h7_cohort.py`:

```python
"""Read the frozen H7 forward cohort back from the immutable seq-0 registration.

Read-only. This module is the ONLY sanctioned way for watchers, boards,
lifecycle, and receipts to learn which names are in the live window; nothing
may fall back to the 15-name scope for entry decisions.
"""

from dataclasses import dataclass
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_paper_lifecycle import REAL_FORWARD_STORE


class CohortUnavailableError(RuntimeError):
    """No valid seq-0 window_registration in the store (wrong checkout?)."""


@dataclass(frozen=True)
class RegisteredCohort:
    included: tuple[str, ...]
    excluded: dict[str, str]  # name -> frozen exclusion reason
    event_id: str


def load_registered_cohort(base_dir: Path = REAL_FORWARD_STORE) -> RegisteredCohort:
    result = ledger.verify(base_dir)
    if not result.valid or result.empty:
        raise CohortUnavailableError(
            f"no valid activation record in {base_dir} "
            f"(valid={result.valid}, empty={result.empty}); refusing to run — "
            "check this is the canonical activated checkout"
        )
    first = ledger.read_events(base_dir)[0]
    # Field access mirrors tests/test_h7_trim_at_append.py:211-219 — verify
    # attribute names against h7_event_ledger before trusting this sketch.
    if first.event_type != "window_registration":
        raise CohortUnavailableError(
            f"seq-0 event is {first.event_type!r}, not window_registration"
        )
    universe = first.payload["universe"]
    return RegisteredCohort(
        included=tuple(universe["included"]),
        excluded=dict(universe["excluded"]),
        event_id=first.event_id,
    )
```

- [ ] **Step 4:** Tests pass; commit the module + tests.
- [ ] **Step 5:** Write the failing watcher test (extend the existing
  `h7_watch` test file): with a fixture store whose cohort excludes name X,
  a fully healthy X must NOT be entry-evaluated; and with an empty store the
  watch run must fail closed with a typed refusal, not fall back to 15 names.
- [ ] **Step 6:** Wire `options_researcher/h7_watch.py` at line 356:

```python
gate_names = watch_universe()  # full 15-name scope: receipts cover the whole universe
cohort = load_registered_cohort()  # raises CohortUnavailableError -> refuse run
entry_names = [n for n in gate_names if n in set(cohort.included)]
```

Receipt validation (`validate_data_gate_receipt(..., names=...)`, lines
362-364) keeps `gate_names`. The entry-evaluation loop iterates `entry_names`
only; excluded names print one line each:
`f"{name}: EXCLUDED (frozen at registration: {cohort.excluded[name]})"`.
Catch `CohortUnavailableError` at the CLI boundary → print the message, exit 2.
- [ ] **Step 7:** Full suite + ruff; commit; open PR to main (owner merges).

---

## Phase C — Real H7 entry path + H7c cutoff

### Task C1: Activation-aware session orchestrator (ENTRY side only)

**Current state (verified):** all lifecycle/book/scoring entry points guard
with `_synthetic_base(base_dir)`, which raises `ActivationBoundaryError` when
`base_dir` is (or is under) `REAL_FORWARD_STORE`
(`h7_paper_lifecycle.py:67-77`, `h7_forward_book.py:107-115`,
`h7_forward_scoring.py:44-52`). So the window is activated but no reviewed
code path can record a real entry.

**Design — extend the one-door pattern, don't bypass it:**

**C1 timing/evidence amendment (owner-authorized 2026-07-20):** an operator
decision date and the immutable source-data evaluation date are distinct
facts. The window guard and planned T+1 fill use `decision_session`; the
receipt, board, and intent's root `evaluation_session` retain the prior
source-data date. A valid receipt chain may therefore support a decision
without relabeling stale cache data as fresh. Before the typed lifecycle
functions may cite that chain, the session module publishes only idempotent,
receipt-hash-bound `source_health` / `data_gate` evidence. It cannot publish
an intent, approval, fill, exit, or score directly.

1. New module `options_researcher/h7_session.py` exposing
   `open_real_session() -> RealStoreSession`. It refuses (typed
   `SessionRefused` error) unless ALL hold:
   - `load_registered_cohort()` succeeds (valid activated store);
   - today's source-health receipt exists and the data-gate receipt links it
     (reuse the exact validation the watcher performs —
     `validate_data_gate_receipt`);
   - the data gate verdict is GO;
   - the target symbol (when given) is in `cohort.included` and not
     per-name entry-banned by source health.
2. `RealStoreSession` is a frozen dataclass carrying `base_dir`
   (= `REAL_FORWARD_STORE`), the activation `event_id`, and the validated
   receipt paths, hashes, `decision_session`, and `evaluation_session`. In
   `h7_paper_lifecycle.py` add:

```python
def _resolve_base(base_dir):
    """Synthetic guard unchanged; a RealStoreSession is the ONLY real-path key."""
    if isinstance(base_dir, RealStoreSession):
        return base_dir.base_dir
    return _synthetic_base(base_dir)
```

3. Switch `_synthetic_base(...)` → `_resolve_base(...)` in the ENTRY-side
   functions only: `record_entry_intent` (:272), `record_owner_approval`
   (:471), `process_entry_fill` (:659), and in `h7_forward_book.py`:
   `record_board_resolution` (:724), `derive_book` (:201, read-only).
   **Exits and scoring keep `_synthetic_base` unchanged** — `observe_exit`
   (:980), `process_exit_fill` (:1178), `expire_unmaterialized_reservation`
   (:910), `reconcile_position_mirror` (:1059), and all of
   `h7_forward_scoring.py` stay synthetic-only. Deadlines: the exit path MUST
   be built (same design, follow-up plan) **before the first real position's
   first possible exit session**, and scoring before the window scores
   **~2026-10-26**. Record both deadlines in `ledger/facts.log` when C1 merges.
4. CLI: `python -m options_researcher.h7_session {status|propose|approve|fill}`
   — `propose --symbol S --lane L --data-gate-receipt PATH` builds an
   `entry_intent` only from the immutable watcher receipt's exact
   `ENTRY-OK` action; `approve --intent-id ID --owner
   carsyn` records `owner_approval` (owner runs this by hand — approval is
   never automated); `fill --intent-id ID` records the `paper_fill` at the
   spec's fill session/pricing rules using receipt-hashed cache files. Every
   subcommand goes through
   `open_real_session()` first and appends only via the existing typed
   lifecycle functions (which use `append_event` with head chaining
   internally), except the narrow receipt-evidence publisher described above.

**Files:**
- Create: `options_researcher/h7_session.py`, `tests/test_h7_session_real_path.py`
- Modify: `options_researcher/h7_cohort.py` (load and validate frozen window
  decision-date bounds)
- Modify: `options_researcher/h7_paper_lifecycle.py` (add `RealStoreSession`,
  `_resolve_base`; swap guard in the 3 entry functions)
- Modify: `options_researcher/h7_forward_book.py` (swap guard in
  `record_board_resolution`, `derive_book`)

- [ ] **Step 1:** Failing tests first, all against tmp fixture stores seeded
  via the synthetic door with a registration event (never the repo store):
  - refusals: no activation record; missing/unlinked receipts; gate NO_GO;
    symbol not in cohort; symbol entry-banned by source health.
  - happy path: receipt-derived propose → approve → fill lands `entry_intent`,
    `owner_approval`, `paper_fill` in causal order; `verify()` stays valid;
    `derive_book` shows the position; a prior source-data session and a later
    decision session yield the next session after the decision date, never the
    source date.
  - boundary: exits still refuse — `process_exit_fill` with a
    `RealStoreSession` must raise `ActivationBoundaryError` (guard unchanged).
  - repo-store safety: every test asserts the actual `REAL_FORWARD_STORE`
    before/after snapshots are identical (reuse the
    `_assert_real_store_untouched` pattern).
- [ ] **Step 2:** Implement to green, smallest diff that passes; ruff + pyright
  + full suite.
- [ ] **Step 3:** Commit per green unit; PR to main; this PR needs the owner's
  adversarial review pass (same bar as the one-door activation review:
  "show me how this could write something unauthorized").

### Task C2: Finish the H7c report-gated exit — test-first, not merge-as-is

**Spec (frozen, verbatim source):**
`docs/superpowers/plans/2026-07-12-h7-stage4-t1-paper-lifecycle-SPEC.md:96-112`
— a report-gated (H7c short premium) pending exit retry is bounded by the last
completed session strictly before the next scheduled report; if it cannot fill
by then it terminates with a terminal fail-loud `data_gap`, reason
`exit_data_gap_at_earnings_cutoff`; **no exit `paper_fill` may be dated at a
session on or after the scheduled report.**

**Current state (verified):** `main`'s `process_exit_fill`
(`h7_paper_lifecycle.py:1178`) implements only the expiration fail-loud
(:1238-1242) and unbounded gap-retry (:1207-1223, :1243-1284). The WIP sits on
branch `feature/h7c-report-gated-exit` @c3f43f0, subject says "(untested)",
+153 lines in `h7_paper_lifecycle.py` only.

- [ ] **Step 1:** New branch off main: `git checkout -b feature/h7c-report-gated-exit-v2 main`.
- [ ] **Step 2:** Write failing tests in the existing lifecycle test file
  (synthetic fixture stores), one per spec clause:
  - retry before the cutoff session still allowed (existing behavior holds);
  - gap at cutoff → terminal `data_gap` with reason exactly
    `exit_data_gap_at_earnings_cutoff`, intent no longer pending;
  - attempt to fill on/after the report session → typed validation error
    (the invariant), never a `paper_fill`;
  - non-report-gated lanes (a/b) unchanged: unbounded retry to expiration.
- [ ] **Step 3:** Use the WIP diff as reference material, not as the change:
  `git diff bf779ff..c3f43f0 -- options_researcher/h7_paper_lifecycle.py`.
  Re-implement (or port with edits) until the Step-2 tests pass. Do not
  cherry-pick c3f43f0 wholesale.
- [ ] **Step 4:** Full suite + ruff + pyright; commit; PR to main (owner merges).

---

## Phase D — OOS reveal binding + badge honesty (independent; branch each off main)

### Task D1: Bind OOS reveals to cache bytes and coverage

**Current state (verified):**
- `research/hashing.py:108` `data_window_hash(window)` hashes only the declared
  window identity dict (`sha256_hex(canonical_json(window))`) — no content.
- `harness/run_backtest.py:58-64` `_run_chunk` returns `[]` when
  `load_cached_chains` comes back empty — an absent cache is indistinguishable
  from a genuine zero-opportunity window.
- `research/experiments.py:218` `reveal_oos` appends a charging `oos_attempt`
  (:291-299) then records whatever `run_fn()` returns (:301-333) with **no
  zero-trade special case** — the docstring even warns a zero-trade run still
  permanently consumes the scarce look.
- Reusable machinery already present: `data/h7_manifest.py` eligible-session
  manifest + `classify_cache` (:35, :64), consumed by
  `research/diagnostics.py::authorize_oos_run` (:214) which already computes
  `manifest_hash = sha256_hex(canonical_json(manifest))` (:252); per-file
  sha256 record pattern at `options_researcher/h6_features.py:99-101`.

**Design:** put the binding in the authorization receipt, verified at reveal
time, and refuse *before* the scarce look is charged.

- [ ] **Step 1:** Failing tests (`tests/` — extend the diagnostics/experiments
  test files):
  - `authorize_oos_run` output gains `content_files` (relative path → sha256)
    and `coverage_complete: bool`; authorization REFUSES when any
    manifest-eligible session has no cache file (coverage incomplete).
  - `reveal_oos` gains a required `authorization` argument; it re-hashes the
    listed files immediately before appending the `oos_attempt` and raises
    (charging nothing) on any mismatch or on `coverage_complete is not True`.
  - zero-trade recording is now legal ONLY under a verified
    `coverage_complete=True` authorization (data present, genuinely no
    trades); with tampered/missing files the reveal refuses instead of
    recording "consistent with zero edge".
- [ ] **Step 2:** Implement:
  - `research/diagnostics.py::authorize_oos_run`: after the existing manifest
    hash, walk the cached chain files for the authorized window, record
    `{relpath: sha256}` (reuse the `_file_record` approach), set
    `coverage_complete` from `classify_cache` (every eligible day accounted
    for). Hashing bytes does not read results — the holdout seal is not
    breached; do NOT load or print any quote content.
  - `research/experiments.py::reveal_oos(hypothesis_id, run_fn, *, authorization, ...)`:
    verify before the `oos_attempt` append at :291. Update all call sites and
    tests (signature change is deliberate — an unbound reveal must become
    impossible, not deprecated).
  - `research/hashing.py::data_window_hash`: unchanged behavior, but fix the
    docstring to state plainly that content binding lives in the authorization
    receipt, not this hash.
  - New registrations: add an optional `data_binding` field (authorization
    receipt hash) to registration entries going forward; existing sealed
    registrations are untouched (append-only ledger).
- [ ] **Step 3:** Full suite + ruff + pyright; commit; PR (owner merges).

### Task D2: Stop fabricated zeros and future-dated feature rows

**Current state (verified):**
- `options_researcher/attractiveness.py:455-458`: NaN `iv_rank` /
  `iv_minus_rv` coerced to `0.0`.
- `options_researcher/attractiveness_dashboard.py:968-970`: same coercion
  duplicated in `_gather_symbol`.
- `options_researcher/attractiveness_dashboard.py:954-961`: when every feature
  row post-dates the chain day, the fallback picks `feats.iloc[0]` — a
  future-dated (look-ahead) row.
- Reuse, don't invent: `_block(symbol, code, detail, day)` at :895-899 with
  reason codes `NO_CACHED_CHAINS` / `INPUT_MISSING` / `UNEXPECTED_ERROR`;
  `FileNotFoundError` from `_gather_symbol` already routes to
  `_block(symbol, "INPUT_MISSING", ...)` (:926-927). No thresholds change.

- [ ] **Step 1:** Failing tests (small DataFrame fixtures):
  - NaN `iv_rank` → CLI prints `UNKNOWN`, symbol takes no GREEN/score;
    dashboard marks the symbol blocked, not GREEN-with-zero.
  - features all future-dated relative to `day` → symbol blocked with a
    visible reason, never rendered from the future row.
- [ ] **Step 2:** Implement:

`attractiveness.py:455-458` →

```python
rv21 = float(row["rv21"])
iv_rank = float(row["iv_rank"]) if pd.notna(row["iv_rank"]) else None
iv_minus_rv = float(row["iv_minus_rv"]) if pd.notna(row["iv_minus_rv"]) else None
if iv_rank is None or iv_minus_rv is None:
    missing = "iv_rank" if iv_rank is None else "iv_minus_rv"
    print(f"{symbol}: UNKNOWN -- {missing} unavailable at this session; not scored")
    continue
```

(Adjust to the loop's actual print/score structure; the requirement is that a
missing input yields UNKNOWN-and-unscored, never a numeric 0.)

`attractiveness_dashboard.py:954-961` →

```python
feats = load_features(symbol)
at_or_before = feats.loc[feats.index.astype(str) <= day]
if at_or_before.empty:
    raise FileNotFoundError(
        f"no feature row at or before {day} for {symbol}; "
        f"earliest available is {feats.index[0]} (future-dated)"
    )  # -> _gather_all catches -> _block(symbol, "INPUT_MISSING", ...)
row = at_or_before.iloc[-1]
features_as_of = str(at_or_before.index[-1])
```

`attractiveness_dashboard.py:968-970` → same None-preserving pattern as the
CLI; a symbol with missing `iv_rank` raises the same `FileNotFoundError` route
(`f"iv_rank unavailable for {symbol} at {features_as_of}"`) so it lands in the
blocked list instead of scoring on zeros.
- [ ] **Step 3:** Full suite + ruff; rebuild the dashboard once and eyeball
  that previously-GREEN symbols with real data still render:
  `uv run python -m options_researcher.attractiveness_dashboard`.
- [ ] **Step 4:** Commit; PR (owner merges).

---

## What's next after P0 (notes for follow-up passes — NOT in this plan's scope)

**P1 (next pass, roughly in this order):**
1. **H10 capture-or-defer decision (owner call, urgent):** H10a/H10b are
   registered (`ledger/experiments.jsonl:16`) but nothing captures
   observations; every trading day silently missed cannot be backfilled
   honestly. Either build the minimal watcher/receipt path now or formally
   void/defer-and-re-register in the ledger.
2. **H7 exit path + scoring real-store build** (deadlines recorded by C1:
   before first possible exit; scoring before ~2026-10-26).
3. **Market-data bundle hardening before landing:** the bundle is parked on
   `parking/market-data-bundle-2026-07-20` (A1) and is NOT on `main`. Before it
   ever lands: `market_data/transport.py:71` can relabel old cached data as
   fresh (preserve original fetch timestamps, add TTLs); Schwab account
   responses must not persist through the generic cache (and never with
   permissive modes); add provider protocol-conformance tests. The parked
   commit also carries the `.env.example` key-removal regression and a
   `.gitignore` edit — review both before cherry-picking anything off that
   branch.
4. **Generic research ledger parity:** port the H7 ledger's locking, fsync,
   and atomic-HEAD protections to `research/ledger.py:451`.
5. **`tools/score_backtest.py:50` preregistration guard:** exploratory
   backtests should require a ledger registration or refuse (ledger-discipline
   skill is the reference for the rule).

**P2 (cleanup / truth maintenance):**
- README + H7 docs truth-up: Stage 8 is ACTIVATED (not closed/empty); paper
  positions ARE open (H6 NVDA call); do not touch the hash-bound activation
  spec itself.
- Dashboard hard-coded 38 VST shares vs canonical 39 in holdings.
- Nested RAG tests into CI; broaden the pyright `include` list.
- Land-or-remove: isolated quant-tool bundle commands that fail in a fresh
  clone; BS descriptive integration; sample `crawler.js`.
- Prune the ~10 linked worktrees after branch reconciliation
  (`git worktree list`; several sit in session temp dirs).

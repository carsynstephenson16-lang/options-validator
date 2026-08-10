# Fable review — Stage B hardening + Stage C (commits 6c41585, 2a7707c)

Date: 2026-08-10. Reviewer: Fable (main session) synthesizing three Sonnet
subagent reviews (spec-compliance, adversarial test-honesty + receipt
forensics, live mutation testing). Subject: `codex/attractive-exp-hardening`
@ `2a7707c` (base `1fe8169`), implementing
`docs/superpowers/plans/2026-08-10-05-hardening-stage-c-codex-brief.md`,
which was commissioned by
`reports/2026-08-10-attractiveness-stage-b-fable-review.md`.

## Verdict

**PASS. All five brief parts implemented as specified; every new guard was
live-mutation-tested and every planted bug was caught.** Stage C is closed
with a committed receipt whose claims reconciled against an independent
rerun. Not yet rejected by any check that can actually fail — and this time
every guard was demonstrated ABLE to fail. Merge decisions remain the
owner's.

## What was verified, and how

- **Numbers reconcile exactly.** Full suite `Ran 2643 ... OK (skipped=5)`
  (base was 2,639; net +4 = 5 new tests minus 1 deleted vacuous test).
  Experiment glob `test_exp*` 60/5-skipped; baseline file 11 tests. Ruff
  clean, pyright 0, `git diff --check` clean — all independently rerun.
- **Receipt forensics (F2 resolved for this task):** the captured RED
  tracebacks were checked character-for-character against the committed
  code; all verifiable captures match exactly. The zero-marker RED capture's
  `AssertionError: 2 != 0` matches the exact count of "experiment"
  substrings the module emits — a figure fabrication would have had no
  reason to land on. The two RED captures that mutate never-committed
  intermediate states are inherently unverifiable post-hoc, but the
  spec-compliance agent *observed the sentinel demonstration live* in the
  worktree mid-review, corroborating the receipt's account.
- **Mutation testing — the decisive evidence.** Four bugs were deliberately
  planted, one per guard, and each tripped its test, then reverted to green
  with the worktree left byte-identical to `2a7707c`:
  - M1 sentinel constant in config → drift test FAILED (named the sentinel).
  - M2 the original audit-B1 bug reintroduced verbatim (None→self-compute in
    `assemble()` under `real_assembly`) → FOUR tests failed, including both
    new guards and the pre-existing production-entry test.
  - M3 `__main__` force-enable (`force_all=True`) → subprocess test FAILED
    (markers leaked into the no-args build).
  - M4 caveat fallback removed → caveat test FAILED.
- **Dashboard behavior unchanged where it must be:** default no-args build
  is byte-identical in size to the Stage-B-verified artifact (105,961
  bytes, 0 experiment markers); `--experiments` build (140,584 bytes) shows
  the section, per-lane `max as-of` stamps, and blocked-reason lines. All
  four `EXPERIMENT_LANES_ENABLED` flags remain False at HEAD. The display
  fixes are only reachable through `_experiments_html()`'s untouched
  early-return gate, so the diff is structurally incapable of altering
  default production HTML.
- **Scope:** exactly the three permitted files across the whole branch;
  no config/pyproject/uv.lock changes; no history rewrites.

## Residual findings (none blocking)

- **R1 (MINOR, flakiness):** the subprocess test writes to the shared,
  unlocked `.tmp/dashboard/attractiveness.html` (the module offers no
  output override; the brief sanctioned this). Under concurrent sessions in
  one checkout this is a real flake surface — observed live during this
  review when a concurrent mutation run made the test fail spuriously. A
  narrow vacuity also exists: if the `__main__` block were deleted AND a
  stale HTML file were present, the no-args half could pass on stale
  content. One-line fix whenever convenient: assert the module's
  `"wrote "` stdout line so the test proves a fresh build happened.
- **R2 (INFO):** the Stage C receipt never states that the vacuous
  byte-identity test was DELETED (it frames the change as additions) — a
  material omission in a document about fixing that test. The deletion is
  correct and brief-mandated; this receipt records it.
- **R3 (INFO, future-fragility):** the builders-never-invoked guard works
  because the four `build_exp_*_board` imports are function-local in
  `_cli_experiment_payloads` (re-resolved at call time, so `mock.patch`
  intercepts). Moving those imports to module top-level would silently
  blind the guard. Do not "tidy" those imports upward.
- **R4 (INFO):** drift-test AST scan matches only literal-string
  `getattr(config, "EXP_...", d)` names (dynamic names would escape —
  exotic); the `EXPERIMENT_LANES_ENABLED` exclusion filter is a no-op since
  the name doesn't start with `EXP_` (harmless).
- **R5 (INFO):** the receipt's dotted invocation
  `unittest tests.test_experiments_baseline` cannot run in this repo
  (`tests/` has no `__init__.py`); counts were verified via
  `discover -p "test_experiments_baseline.py"` instead.
- **R6 (unchanged, owner decision):** F4 from the Stage B review — one
  malformed card would crash the whole dashboard once any lane flag is
  flipped True — remains intentionally out of scope. Record a
  fail-loud-vs-quarantine decision before any flag flip.

## Process note (orchestration lesson, Fable's own)

Two review agents were dispatched into overlapping workspace: the
spec-compliance agent entered the preserved Codex worktree while the
mutation runner was actively planting/reverting bugs there, observed the
tree mutating, and ran one `git stash`/`git stash pop` against its
read-only mandate (verified afterward: stash list empty, state restored,
final worktree byte-identical to `2a7707c`, nothing lost). Future briefs
for parallel reviewers must assign disjoint workspaces explicitly. The
collision had one silver lining: the spec agent independently witnessed the
M3 mutation making the subprocess test fail — live confirmation of both
the guard and R1's flake surface.

## Recommended next step

Nothing further is required from Codex. The program's engineering arc
(Stage A modules → Stage B wiring → hardening + Stage C) is complete and
verified. Open owner decisions: (1) merge `codex/attractive-exp-wiring`,
`codex/attractive-exp-hardening`, and the two review branches — suggested
together, code never landing without its hardened tests; (2) the R6/F4
design decision before any experiment flag is ever enabled; (3) optional
R1 one-liner folded into any future touch of the test file.

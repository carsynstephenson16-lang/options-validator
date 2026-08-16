# Adversarial review receipt — ritual switch-on rev-2.1 implementation

**Date:** 2026-08-14 (evening). **Branch:** `claude/ritual-switch-on-rev21`
(base `bfa58d8`). **Spec:** brief 11 rev-2.1
(`docs/superpowers/plans/2026-08-14-11-ritual-switch-on-rev2-spec.md`).
**Implementer:** Opus implementation agent. **Reviewer:** independent Opus
adversarial agent (fresh context, no shared state with the implementer).
**Orchestration:** Fable session; owner directive "go ahead with D-1 through
D-4, implement the switch-on" recorded in
`reports/2026-08-14-switch-on-owner-decisions.md`.

## Verdict trail

Round 1: **PASS WITH FIXES** — 2 blockers, 7 cautions.

- **B-1 (blocker):** the two-region fence's guard condition was not
  test-enforced. Reviewer's novel mutation (guard variable
  `FULL_AUTHORITY_RC` → `AUTHORITY_RC`) left the entire 2910-test suite
  green. Post-registration consequence would have been H7 receipts and
  ledger appends produced under data-tier authority.
- **B-2 (blocker):** the D-3 capture-gate relaxation used per-commit
  `git log --name-only`, which is blind to merge-commit paths and rename
  sources. Reviewer verified two working bypasses in throwaway repos (evil
  merge editing code; `git mv` of code into an evidence path).
- Cautions C-1..C-7: catch-all verb families too narrow; hash test name
  overclaim; push-matcher case accident; evidence allow-list file-type
  blindness; stale mutation-report count; side-effect test scope; region B
  silent on GATE_GO=0 with full authority.

Round 2 (fixes `8dcc7ec`, `7505499`, `eb63a28`): reviewer re-ran its own
attack repros against the fixed tree. **Both blockers CONFIRMED FIXED:**

- B-1: all three fence attacks (guard rename, conjunct drop, surface lifted
  out of region) now RED inside `tests/test_daily_ritual_provenance.py`
  itself (`test_full_tier_regions_are_opened_by_the_authority_guard`,
  `test_every_fenced_surface_lies_inside_a_full_tier_region`).
- B-2: gate now tree-diffs (`git diff --name-only --no-renames
  origin/main HEAD`); evil-merge and rename vectors REFUSE; all six intended
  behaviors preserved (evidence-only ahead proceeds; behind, mixed, pure
  code, unresolvable identity refuse; aligned silent).
- Cautions: C-1/C-2/C-3/C-5/C-6 fixed and spot-checked (C-3 verified by a
  discriminating probe: the anchoring, not the case accident, does the
  exclusion); C-4 and C-7 recorded as accepted residuals in
  `reports/2026-08-14-switch-on-mutation-results.md`.

## Final verification (reviewer's own, clean tree)

- Suite: `Ran 2914 tests … OK (skipped=5)`, exit code 0 (captured
  explicitly; 2910 → 2914 = exactly the four new guard/regression tests).
- `ruff check .` clean; `pyright` 0 errors.
- Mutation battery: 13/13 RED then restored green (M1-M10 spec-listed,
  M11-M13 review-born).
- Hash containment: `config.py` zero diff lines; `data/ritual_authority.py`
  is the sole changed file inside the `diagnostic_source_hash` surface.
- `ritual_data_phase_active=False` everywhere on the branch — the D-2 flip
  is a separate commit, after this receipt.

## Open residuals (accepted, minor)

1. Evidence allow-list is path-name-based; file types (symlinks,
   executables) unrestricted — low severity while nothing executes from
   evidence paths.
2. C-6 side-effect snapshot has a ~1s concurrency window and will run
   slower in the main checkout (full parquet cache walked).
3. Region B emits no `note` when full authority is granted but GATE_GO=0 —
   spec-conformant; revisit post-registration.
4. D-4 sub-fork 3a/3b and D-6 remain owner-open (see the decision record).

## Process note

The implementer's first mutation-battery driver used a blanket
`git checkout -- tests/` revert that transiently discarded uncommitted fix
edits mid-battery (caught via test-count mismatch, driver rewritten, entire
battery re-run; no recorded result derives from the bad run). Kept here as a
lesson: mutation drivers must restore exact bytes per touched file, never
directory-wide checkouts over uncommitted work.

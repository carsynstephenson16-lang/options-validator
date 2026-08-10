# Fable review — Stage B experiment wiring (commit 1fe8169)

Date: 2026-08-10. Reviewer: Fable (main session) synthesizing three independent
Sonnet subagent reviews (spec-compliance, adversarial correctness, independent
verification run). Subject: `codex/attractive-exp-wiring` @ `1fe8169`
("feat(exp): wire display-only attractiveness experiments"), reviewed against
`docs/superpowers/plans/2026-08-09-attractiveness-experiment-program-codex-master-brief.md`
and its Fable review checklist. Provenance: all findings below were verified
against the actual diff/output; the CRITICAL finding was independently
re-confirmed by the main session before publication.

## Verdict

**Implementation: sound. B1 production boundary holds. Test suite: one vacuous
test and three hardening gaps.** Not yet rejected by any check that can
actually fail. Merge decision remains the owner's.

## Checklist results (master brief items 1–8)

1. File scope — PASS. Stage B touches only the three named files;
   `pyproject.toml`/`uv.lock` untouched across the whole branch.
2. Red-first receipt — **UNVERIFIABLE.** Tests and implementation landed in one
   commit; no receipt artifact exists on the branch. Codex's "written RED
   first" chat claim is unsupported by repo evidence, and the production-entry
   test would have passed even at the parent commit (the guarded string could
   not exist yet).
3. No network / no new deps / no magic numbers — PASS (verified by grep of the
   diff and of both built HTML files; only display format specifiers outside
   the provenance-labeled `EXP_*` constants).
4. No forbidden imports (ledger, positions, registered-hypothesis modules,
   `.tmp/composite_cache`) — PASS (full-tree grep at 1fe8169).
5. DATA_BLOCKED fail-visible — PASS in the built HTML (per-lane blocked
   reasons, per-symbol DATA_BLOCKED badges, as-of lines). See finding F6/F7
   for two brittleness caveats.
6. Baseline byte-identity test green — test is green but **vacuous** (F1).
   The property itself is supported by other evidence (F1 note).
7. Full suite + ruff + pyright + `git diff --check` — PASS, independently
   re-run: 2,639 tests OK (5 skipped; Codex claimed 2,638 — off by one),
   experiment suite 56/56 under glob `test_exp*` (NOT `test_experiments*`,
   which finds only 7), ruff clean, pyright 0 errors.
8. HTML inspected with and without `--experiments` — PASS. Default build:
   zero occurrences of "experiment" (105,961 bytes). `--experiments` build:
   section + health strip + all four lanes + per-lane as-of stamps + refusal
   copy (140,888 bytes). No network-error signatures in either build; all
   observed failures were local `.cache/*.parquet` FileNotFoundErrors
   (worktree had an empty cache, so only the blocked-data render path was
   exercised — the with-data path was NOT rendered in this review).

## B1 boundary (the critical invariant) — HOLDS

Traced at every call site by two independent reviewers: `assemble()`'s four
`exp_*` kwargs are pure pass-through (`exp_beta or []`), with no
None-triggers-self-compute branch analogous to the composite lane;
`main()` never calls `_cli_experiment_payloads()`; the only caller is the
`__main__` guard, gated on `"--experiments" in sys.argv` (exact membership,
not substring) or a call-time read of `EXPERIMENT_LANES_ENABLED` (all four
False in config). `tools/research_context_assemble.py`, `daily_ritual.sh:345`,
and `research_refresh.sh:213` all reach the no-experiments path.

## Findings

- **F1 (CRITICAL, test-quality):**
  `test_all_lanes_off_is_byte_identical_to_omitting_experiment_keywords`
  compares `assemble(...)` with kwargs omitted vs explicitly `None` — by
  Python default-argument semantics these are the identical call, so the test
  can never fail for ANY implementation (even one with a None→self-compute
  bug, since both sides would self-compute identically). Both sides also run
  with `real_assembly=False`, never touching the dangerous branch. The
  byte-identity property the spec (§7a) wanted is currently evidenced only by
  the production-entry test + this review's HTML grep, not by this test. Fix:
  diff against captured pre-program `render()` output, or at minimum against a
  call path that could diverge.
- **F2 (IMPORTANT, evidence):** RED-first unverifiable (checklist item 2
  above). Future briefs should require the failing-run output to be committed
  as a receipt in the same PR.
- **F3 (IMPORTANT, coverage):** No test runs the literal production command
  (`python -m options_researcher.attractiveness_dashboard`, no args) as a
  subprocess asserting the section is absent — the `__main__` wiring point
  itself is untested end-to-end. The subprocess tooling already exists in the
  same test file (config-drift test).
- **F4 (IMPORTANT, blast radius):** `render()` calls `_experiments_html()`
  inline with no isolation, and `_experiment_card_line()` uses hard indexing
  on card fields. Once any lane flag is flipped True, a malformed card crashes
  the ENTIRE dashboard build (Top-3 included), indistinguishable from a
  production outage. Zero live risk while all flags are False; decide
  fail-loud-vs-quarantine before any flag flip.
- **F5 (MINOR, drift):** `test_config_matches_every_module_frozen_default`
  re-derives module defaults via subprocess (good) but enumerates the 16
  `EXP_*` constants in a hand-maintained dict — a constant added later to
  config + module escapes drift detection silently. Enumerate `EXP_*`
  attributes programmatically instead.
- **F6 (MINOR, display):** Health-strip badges hardcode
  `class="status-badge unknown"` for every state; text is honest but a
  healthy and a fully blocked lane look visually identical. Composite section
  has a grade→class map to copy.
- **F7 (MINOR, brittleness):** EXP-TBILL assignment caveat renders only for
  reason `EX_DIV_DATE_UNAVAILABLE` (the only value v1 emits); any future
  reason would silently drop the caveat rather than showing a generic one.
- **F8 (INFO):** Experiment test files are `test_exp_*.py`; the natural glob
  `test_experiments*` matches only the 7 baseline tests. Anyone spot-checking
  Codex's "56 tests" with the obvious pattern will wrongly see a shortfall.
- **F9 (INFO):** Stage A landed as feat+fix commit pairs rather than the
  brief's "one commit" per module; content-wise the fixes align modules WITH
  the briefs, so this is process drift, not spec drift.

## Attacks that failed (sound as implemented)

Flag defaults False (asserted by test); `EXPERIMENT_LANES_ENABLED` read at
call time, not import time; no vocabulary-discipline violations in new HTML
copy; display-only guarantee holds (experiment modules import only cached-data
readers, no writes, no network); `sections_json()` path unaffected.

## Recommended next step

Fold F1/F3/F5 (and optionally F6/F7) into a short Codex hardening brief
before or alongside Stage C; F4 is a design decision to record before any
lane flag is ever flipped. None of these block the owner's merge decision on
functional grounds — the production-safety property was independently
verified against the built artifact.

# Codex brief 05 — Stage B test hardening + Stage C verification (2026-08-10)

Executor model: gpt-5.6-sol · Reasoning effort: medium ·
Orchestrator/reviewer: Claude Fable 5 · Implementation mode: autonomous,
evidence-grounded, test-driven.

Base commit: `1fe8169` (tip of `codex/attractive-exp-wiring`; branch from it).
New branch: `codex/attractive-exp-hardening`.
Worktree: `.tmp/worktrees/attractive-exp-hardening` — nowhere else.
Master brief (binding preamble, hard rules, worktree rules):
`docs/superpowers/plans/2026-08-09-attractiveness-experiment-program-codex-master-brief.md`.
Review that commissioned this brief (read it — every fix below is a finding
there): `reports/2026-08-10-attractiveness-stage-b-fable-review.md`.

Touch ONLY: `tests/test_experiments_baseline.py`,
`options_researcher/attractiveness_dashboard.py`, and the new receipt file
`reports/2026-08-10-attractiveness-stage-c-receipt.md`. No other file.
`pyproject.toml`/`uv.lock` untouched. Offline only; no new dependencies;
no ledger writes; no changes to ranking logic or any `h5/h6/h7/h8/h10*`
module; no owner-value invention.

## Part 1 — replace the vacuous byte-identity test (fixes F1)

`test_all_lanes_off_is_byte_identical_to_omitting_experiment_keywords`
compares `assemble(...)` with the four `exp_*` keywords omitted against the
same call with them explicitly `None`. Because `None` IS the default, Python
makes those the identical call — the test cannot fail for any implementation,
including one with a None→self-compute bug (both sides would self-compute
identically). Delete it and replace with two tests that CAN fail:

1. `test_default_path_never_invokes_experiment_builders` — patch each of the
   four experiment board builders (`exp_beta_qqq`, `exp_tail_shape`,
   `exp_spread_stability`, `exp_tbill_carry` — patch the function the wiring
   layer actually calls, verify the name against the source, do not guess)
   with a `side_effect` that raises `AssertionError("experiment builder
   invoked on default path")`. Then run the real `dashboard.main()` with no
   args under the same mock scaffolding as the existing
   `test_main_no_args_keeps_experiments_out_of_production_entry_point`
   (mocked `_gather_all`, `load_context`, etc. — the `real_assembly=True`
   branch must be exercised). Assert it completes and the output HTML exists.
   This fails the moment anyone adds a None→auto-build branch or calls
   `_cli_experiment_payloads` from `main()`.
2. `test_default_path_html_has_zero_experiment_markers` — same mocked
   `main()` run; assert the written HTML contains zero case-insensitive
   occurrences of the substring `experiment` (this matches what the
   2026-08-10 review verified by hand on the real build: 0 matches in
   105,961 bytes). A stricter check than the current single-heading
   `assertNotIn`. Keep the existing heading assertion too; it costs nothing.

Do NOT reintroduce any omitted-vs-explicit-`None` comparison under a
byte-identity name. If a genuine byte-comparison is wanted, it must compare
two states that a bug could make diverge; if you cannot construct one
offline, state that in the receipt instead of shipping a test that cannot
fail (that is precisely the defect being removed).

## Part 2 — end-to-end subprocess test of the literal production command (fixes F3)

`daily_ritual.sh:345` and `research_refresh.sh:213` run
`python -m options_researcher.attractiveness_dashboard` with no args, which
executes the `if __name__ == "__main__":` block — a code path no current
test reaches (`main()` in-process bypasses it). Add:

3. `test_module_entry_no_args_matches_production_command` — use
   `subprocess.run([sys.executable, "-m",
   "options_researcher.attractiveness_dashboard"], ...)` with NO extra args
   (the subprocess pattern already used by
   `test_config_matches_every_module_frozen_default` is the precedent).
   Assert exit code 0 and that the HTML it writes contains zero
   case-insensitive `experiment` occurrences. Then run it again WITH
   `--experiments` and assert the section heading
   `Experiments — display-only` IS present. Constraints: the test must stay
   offline and must pass with an empty `.cache/` (the 2026-08-10 review
   confirmed both builds succeed in a cache-empty worktree, all lanes
   DATA_BLOCKED — that is the expected fixture state, not a failure).
   Redirect or contain the output HTML so the test does not clobber a real
   `.tmp/dashboard/` artifact non-hermetically; if the module offers no
   output-path override, writing to the gitignored default and cleaning up
   is acceptable — say which you did in the receipt. If the no-args build
   cannot run offline in a clean environment for a reason the review missed,
   STOP and report; do not weaken the test to pass.

## Part 3 — make the config-drift test enumerate, not recite (fixes F5)

`test_config_matches_every_module_frozen_default` checks a hand-maintained
16-entry dict; a 17th `EXP_*` constant added later to `config.py` and a
module would silently escape checking. Rework so membership is derived, not
typed: programmatically collect (a) every `config` attribute matching
`EXP_*` (excluding `EXPERIMENT_LANES_ENABLED`), and (b) every
`getattr(config, "EXP_...", default)` reference in the four `exp_*.py`
sources (AST or regex over the module source is fine — it is a test).
Assert the two sets are equal AND every value matches the module's frozen
default (keep the existing config-stripped-subprocess derivation for
values — it is sound). The hardcoded dict may remain only as a third
cross-check; set equality with the derived collections is what must gate.

## Part 4 — display fixes (fixes F6, F7; small, display-only)

4. Health-strip/lane badges currently hardcode
   `class="status-badge unknown"` for every state
   (`attractiveness_dashboard.py` ~2806, ~2891), so a healthy card and a
   fully blocked card look identical. Map state → CSS class following the
   existing `_COMPOSITE_GRADE_CLASS` precedent (~2739): OK-like states get
   the same class the composite section uses for good grades,
   DATA_BLOCKED/blocked states the bad/blocked class, everything unmapped
   stays `unknown`. Reuse the CSS classes that already exist in the
   stylesheet — add no new CSS and invent no new taxonomy; state TEXT
   remains the source of truth.
5. The EXP-TBILL assignment caveat renders only when
   `assignment.get("reason") == "EX_DIV_DATE_UNAVAILABLE"` (~2938). Add a
   generic fallback: any OTHER non-empty assignment reason renders a visible
   generic caveat line quoting the raw reason string verbatim, instead of
   silently dropping it (fail-visible principle). RED test: feed a card with
   reason `"SOME_FUTURE_REASON"` and assert the caveat line appears.

Every behavior change in Parts 1–4 gets a red test first, and the failing
run's output is CAPTURED (copy-paste, not paraphrase) into the receipt —
this is finding F2's fix applied to this task: red-first is evidence in the
repo or it did not happen.

## Part 5 — Stage C verification receipt (closes the master brief's Stage C)

Write `reports/2026-08-10-attractiveness-stage-c-receipt.md` containing,
with literal command output excerpts and exit codes:
- Full suite (`uv run python -m unittest discover -s tests`) — exit code and
  `Ran N tests` line. Note: expected baseline is 2,639 + your new tests; the
  2026-08-09 chat claim of 2,638 was off by one.
- Experiment suite via `-p "test_exp*"` (NOT `test_experiments*` — that glob
  catches only the baseline file; record both counts so the trap is
  documented where the next auditor will look).
- `uv run ruff check .`, `uv run pyright`, `git diff --check`.
- Dashboard built with and without `--experiments`; for each: HTML byte
  size, `grep -ci experiment` count, and quoted snippets showing (no-args)
  zero markers / (--experiments) section heading + per-lane `max as-of`
  stamps + at least one blocked-reason line.
- The captured RED outputs from Parts 1–4.
- Commit SHAs, deviations (none-or-listed), and the sentence "all flags in
  `EXPERIMENT_LANES_ENABLED` remain False" verified against the final tree.

## Acceptance (Fable will re-review against these)

- The replaced tests each demonstrably CAN fail: receipt shows each one red
  before its fix/feature and green after.
- Subprocess test runs the literal production command, offline, cache-empty.
- Drift test derives membership from config + module sources; adding a fake
  `EXP_TEST_SENTINEL = 1` to config locally makes it fail (show this in the
  receipt, then remove the sentinel — do not commit it).
- Badge classes vary by state; unknown states still render `unknown`.
- Unknown assignment reasons render a visible generic caveat.
- Full suite, ruff, pyright, `git diff --check` all clean; receipt committed
  ON the branch; branch pushed. Merge remains the owner's decision.

## Stop conditions

Inherited verbatim from the master brief: missing capability, any test
needing network, ambiguity forcing invention, hook blocks (a block is
correct), base commit unavailable, worktree-hygiene guard failure. One
addition: if the no-args module entry cannot run hermetically offline,
stop and report rather than shipping a weakened Part-2 test.

## Explicitly OUT of scope

- F4 (render blast-radius if a lane flag is ever flipped True) — that is a
  fail-loud-vs-quarantine DESIGN decision for the owner/orchestrator to
  record before any flag flip, not a Codex code change.
- Any change to experiment math, board contracts, constants' values,
  `EXPERIMENT_LANES_ENABLED` defaults, or ranking logic.
- Squashing/rebasing existing history (F9 stays as-is; no history rewrites).

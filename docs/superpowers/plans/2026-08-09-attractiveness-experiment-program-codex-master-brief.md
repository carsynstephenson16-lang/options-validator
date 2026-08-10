# Codex master brief — attractiveness experiment program (2026-08-09)

Executor model: gpt-5.6-sol · Reasoning effort: medium ·
Orchestrator/reviewer: Claude Fable 5 · Research workers: Claude Sonnet 5 ·
Implementation mode: autonomous, evidence-grounded, test-driven.

Base commit: `1866f59f5d9c976363315878072a1e17165a385a` (branch from it).
Design authority: `docs/superpowers/specs/2026-08-09-attractiveness-experiment-program-design.md`.
Authorization: `.cursorrules`/`AGENTS.md` 2026-08-09 paragraph +
`reports/2026-08-09-attractiveness-experiment-authorization.md`.

Before ANY edit, Codex must read: `AGENTS.md` (whole file), `.cursorrules`,
the design spec above, and the specific brief for its task. Hard rules that
bind every task: no network/provider calls; no new dependencies; no ledger
writes; no changes to `attractiveness.py` ranking logic, `robustness/`,
any `h5/h6/h7/h8/h10*` module, or the paper book; tests are offline
`unittest`; a failing (red) test precedes each behavior change; no
owner-value invention — every constant comes verbatim from the briefs with
its provenance comment.

## Implementation order

- **Stage A — four independent module tasks, may run in parallel**
  (zero shared files; each task edits ONLY its own two new files):
  1. `2026-08-09-01-beta-to-qqq-codex-brief.md` → `options_researcher/exp_beta_qqq.py` + `tests/test_exp_beta_qqq.py`
  2. `2026-08-09-02-tail-shape-codex-brief.md` → `options_researcher/exp_tail_shape.py` + `tests/test_exp_tail_shape.py`
  3. `2026-08-09-03-spread-stability-codex-brief.md` → `options_researcher/exp_spread_stability.py` + `tests/test_exp_spread_stability.py`
  4. `2026-08-09-04-tbill-carry-codex-brief.md` → `options_researcher/exp_tbill_carry.py` + `tests/test_exp_tbill_carry.py`
  Stage-A tasks do NOT touch `config.py`: each module reads its constants
  via `getattr(config, "EXP_...", <brief value>)` with the brief value as
  the in-module frozen default, so Stage A is conflict-free and testable.
- **Stage B — single fan-in wiring task, sequential, after all of A**
  (branch `codex/attractive-exp-wiring`; touch ONLY `config.py`,
  `options_researcher/attractiveness_dashboard.py`, and
  `tests/test_experiments_baseline.py`): append the four `EXP_*` constant
  blocks + `EXPERIMENT_LANES_ENABLED` (all False) to `config.py`
  (module defaults then defer to config); add the "Experiments —
  display-only" section renderer + health strip to
  `attractiveness_dashboard.py`; add optional `exp_beta/exp_tail/
  exp_spread/exp_tbill` keywords to `assemble()` (default None). **CRITICAL
  departure from the composite precedent (audit B1): an experiment keyword
  left as None must NEVER self-compute — `assemble()`'s composite branch
  auto-builds on None during real assembly with no flag gate, and copying
  that would silently enable experiments in every no-arg production
  rebuild (`daily_ritual.sh`, `research_refresh.sh`). Only the CLI path
  builds experiment payloads, and only when `--experiments` is passed or
  a lane's `EXPERIMENT_LANES_ENABLED` flag is True.** Add the
  `--experiments` CLI flag; add `tests/test_experiments_baseline.py`
  (written RED first) covering: byte-identity with all lanes off; flags
  default False; a mocked-`_gather_all` `main()` call with no args
  asserting the Experiments section is ABSENT from the real production
  entry point (precedent: `tests/test_attractiveness_dashboard.py:1696`);
  and a config-vs-module-default consistency check for every `EXP_*`
  constant.
- **Stage C — verification task**: full suite, ruff, pyright,
  `git diff --check`, dashboard build with and without `--experiments`,
  HTML inspection evidence (section present/absent, per-lane as-of stamps,
  refusal copy), receipt.

## Branch and worktree rules

One branch per task: `codex/attractive-exp-<slug>` with slugs
`beta-qqq`, `tail-shape`, `spread-stability`, `tbill-carry`, `wiring`.
Worktrees only under `.tmp/worktrees/attractive-exp-<slug>` — NEVER in
/tmp, ~/Downloads, or as bare siblings. No branch deletion, no
destructive cleanup, no history rewrites. Before removing any worktree:
`uv run python tools/irreplaceable_data_guard.py verify` AND
`git -C <path> status --short --ignored=matching --untracked-files=all`.
Push every branch when its task completes (backup, not integration);
merge decisions are the owner's. Record every commit SHA in the receipt.

## Exact prompts per Codex run

Run 1..4 (Stage A, parallelizable):
> Read AGENTS.md, .cursorrules,
> docs/superpowers/specs/2026-08-09-attractiveness-experiment-program-design.md,
> and docs/superpowers/plans/2026-08-09-0<N>-<slug>-codex-brief.md.
> Implement exactly that brief on branch codex/attractive-exp-<slug>
> from base 1866f59, in worktree .tmp/worktrees/attractive-exp-<slug>.
> Test-driven: write the brief's named red test first, show it fail, then
> implement to green. Touch ONLY the two files the brief names. Offline
> only. Finish with: uv run python -m unittest tests.test_exp_<name>,
> uv run ruff check <files>, uv run pyright, and a receipt (files, tests,
> commands + outputs, commit SHA, deviations=none-or-listed).

Run 5 (Stage B) uses the same preamble with the master brief §Stage B as
scope, MUST include the sentence "Touch ONLY config.py,
options_researcher/attractiveness_dashboard.py, and
tests/test_experiments_baseline.py", and MUST run the full suite (all
tests), not just its own.

## Fable review checklist (applied to every diff before integration)

1. Diff touches only the files the brief names.
2. Red test existed and failed for the right reason (receipt evidence).
3. No network; no new dependencies — `pyproject.toml` and `uv.lock` must
   be untouched in every task's diff; no magic numbers outside the
   provenance-labeled constants.
4. No import of, or write to, registered-hypothesis modules, ledgers,
   positions, or `.tmp/composite_cache` (read-only where allowed).
5. DATA_BLOCKED paths covered by tests; no silent fallback anywhere.
6. Baseline byte-identity test green (Stage B onward).
7. Full suite + ruff + pyright green; `git diff --check` clean.
8. Dashboard HTML inspected (not assumed) with `--experiments` on and off.

## Stop conditions (per task)

Stop and report instead of working around: any needed capability missing
from the installed libraries; any test that requires network; any
ambiguity that would force inventing a constant or convention not in the
brief; any conflict with a hook (a block is correct by default); base
commit unavailable; guard failure on worktree hygiene.

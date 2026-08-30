# DRAFT SPEC — Honest provenance labeling for score_backtest's DSR ledger mode

- **Status:** DRAFT v2 — APPROVED by owner 2026-08-30 (in-session directive: "114 yes approve"; status line updated same day, previously "NOT approved, NOT scheduled"). Implementation NOT yet scheduled — the landing-window constraint below (batch with the next `options_researcher/`/`tools` landing; never mid-ritual) still binds. v1 was BLOCKED by the fresh-context adversarial verifier (2026-08-14) on three grounds; v2 is narrowed to what survives. No production code was changed in the review session.
- **Date:** 2026-08-13, rewritten 2026-08-14 (America/New_York)
- **Owner:** Carsyn (approval + landing window); implementing agent: Codex from this brief.
- **Decision label:** INSTRUMENT ONLY (audit-label honesty on a display-only diagnostic; zero verdict authority).
- **Source evidence:** Repo-verified, twice-reviewed finding. In `tools/score_backtest.py`, `--dsr-n-source=ledger` takes trial count N from `research_ledger.current_trial_count()` (~line 87) but the trial-SR variance V is operator-typed (`--dsr-trial-sr-var`), and the composite provenance label recorded is `"ledger-trial-count"` (~line 89). The deflation hurdle is linear in sqrt(V) but only ~sqrt(2·ln N) in N — the dominant input is the operator-typed one, while the label implies the quantity is ledger-derived. **Verifier correction folded in (B1): the V *value* IS already recorded** — `result["dsr_trial_sr_variance_input"]` (score_backtest.py:105-110, asserted at tests/test_score_backtest_cli.py:126). The verified remaining gap is only: (a) the *origin/justification* of V is nowhere recorded, and (b) the composite label `"ledger-trial-count"` overstates what came from the ledger. Paper context only (not load-bearing): Bailey & López de Prado, "The Deflated Sharpe Ratio" (JPM 2014; formulas verified against the author-hosted PDF 2026-08-13; the repo's `metrics.py` implementation matches and is untouched here).

## Repository state at spec time
- Branch `claude/options-validator-research-review-e27946`, HEAD `eea4700b36266da74b35f37e83467816947e0933`, clean tree, retrieved 2026-08-13 23:43 EDT.
- Relevant files: `tools/score_backtest.py` (dsr block ~64-110), `tests/test_score_backtest_cli.py` (label assertion at ~123, V-input assertion at ~126).

## Problem statement
A diagnostic that exists to police selection bias carries a provenance label that overstates its own auditability: the origin of the dominant input V is unrecorded, and the label names only the N source.

## Existing behavior and verified gap
- CLI refuses ledger mode without `--dsr-trial-sr-var` (never guesses) — good, keep.
- V's numeric value is recorded (`dsr_trial_sr_variance_input`) — present, keep, do NOT duplicate under a second key.
- Gap: no record of where V came from; label `"ledger-trial-count"` (also in help text, score_backtest.py:64).

## Goal
A ledger-mode DSR block is self-describing: N source, V value (existing key), V origin (verbatim operator string), and an honest composite label.

## Scope
1. Add a required companion flag `--dsr-trial-sr-var-provenance "<free text>"` whenever `--dsr-n-source=ledger` is used; refuse without it, mirroring the existing V refusal (stderr message + nonzero exit).
2. Record `dsr_trial_sr_variance_provenance` (verbatim string) in the output next to the existing `dsr_trial_sr_variance_input`.
3. Change the composite provenance label from `"ledger-trial-count"` to `"ledger-N-operator-variance"` (or equivalent honest wording settled in the PR), updating BOTH the recorded value and the CLI help text (score_backtest.py:64), and the existing label assertion at tests/test_score_backtest_cli.py:123.

## Non-goals (with verifier rationale)
- NO V-sensitivity triplet (v1 Scope 3, REMOVED): computing DSR at V/2 and 2V in the tool layer requires `skew`/`kurt`, which `scoreboard()` computes locally and does not export (metrics.py:567); re-deriving per-trade returns outside `metrics.py` is a silent-drift path, and printing extra DSR numbers below the `DSR_MIN_T` sample floor would be a display-integrity regression (verifier B2, B3). If the owner wants the triplet later, it needs its own spec with an owner-gated `metrics.py` export.
- NO change to `metrics.py`, `DSR_MIN_T`, `DSR_DEFAULT_MEAN_TRIAL_SR`, the measured-variance path, or any ledger schema. Note (verifier M4): `research/ledger.py:292-295` `DEFLATED_SHARPE_KEYS` is a closed set that rejects unknown keys — the tool's new output field must never be lifted into a ledger row; no ledger change is part of this spec.
- NO retroactive edits to any existing output, report, or ledger row. (Verified: no ledger row on disk uses `n_provenance`, so no chain discontinuity.)

## Forbidden changes
`research/**`, `ledger/**`, `metrics.py`, `config.py`, `strategies/**`, all `h7_*` modules, live-order paths, frozen constants. No new dependencies.

## Architecture fit and ownership boundary
Tool-layer only. Landing-window fact: `tools/` is inside `diagnostic_source_hash()` (`research/hashing.py:132-133`), so this shares the batching constraint — land with the next planned `options_researcher/`/`tools` landing, never mid-ritual. No interaction with robustness `ExperimentSpec` registration.

## Interfaces, schemas, formulas, units
DSR formula and computation path unchanged. One new output field + one relabeled field. The tool prints JSON to stdout and writes no artifact file (verifier M4) — downstream consumers are humans and transcripts.

## Fail-closed and abstention behavior
Missing provenance flag in ledger mode → refuse (stderr + nonzero exit). Empty/whitespace-only provenance string → refuse (a blank origin is the dishonesty this spec removes). All other refusal behavior unchanged.

## Point-in-time, preregistration, OOS, licensing
No data fetches, no OOS interaction, no registration change, no third-party code.

## Edge cases
- `current_trial_count()` < 2: unchanged behavior (existing contract; out of scope).
- Provenance string containing JSON-hostile characters: serialized verbatim via the existing JSON emitter (no manual escaping).

## Test-first plan and targeted tests
1. Failing test: ledger mode without `--dsr-trial-sr-var-provenance` exits nonzero with the refusal message; whitespace-only string also refused.
2. Failing test: output contains `dsr_trial_sr_variance_provenance` verbatim and the new honest label; `dsr_trial_sr_variance_input` still present (existing assertion untouched in meaning).
3. Update the label assertion at tests/test_score_backtest_cli.py:~123 to the new label (this is the one intended behavior change).
4. Invariance: non-ledger modes and the no-DSR path produce output identical to pre-change fixtures.

## Required full checks
`uv run python -m unittest discover -s tests` (offline), `uv run ruff check .`, `uv run pyright` — all exit 0.

## Acceptance criteria
1. Ledger-mode output self-describes N source, V value, V origin, honest label.
2. Refusal paths per fail-closed section verified by tests.
3. Baseline invariance for all non-ledger paths.
4. Full suite, ruff, pyright green.

## Risks and invalidation
Risk: an existing automation calls the CLI with the old flag set — Codex must grep the repo (tools/, scripts/, docs runbooks, LaunchAgent shell scripts in the ops checkouts if visible) for `--dsr-n-source` callers BEFORE changing the contract; if any scheduled/production caller exists, STOP and report to the owner instead of silently breaking a job. Invalidation: if fresh-HEAD re-verification shows V origin is already recorded, STOP and report.

## Rollback / disable path
Single revert commit; display-only tool, no ledger or verdict consequence.

## Residual unknowns
Whether any out-of-repo automation (ops checkout scripts) invokes `--dsr-n-source=ledger`; Codex reports what it can see and flags the rest for the owner.

## Paste-ready Codex prompt
> Implement `docs/superpowers/specs/2026-08-13-dsr-ledger-mode-provenance-draft-spec.md` (v2) in the options-validator repo. First: capture fresh repo state (branch, HEAD, `git status`) and re-verify on YOUR HEAD — read `tools/score_backtest.py` (~64-110) and confirm: V value recorded as `dsr_trial_sr_variance_input`, V origin NOT recorded, label `"ledger-trial-count"`; if the origin is already recorded, STOP and report. Grep for `--dsr-n-source` callers (tools/, scripts/, docs, any visible ops scripts) and report them BEFORE changing the CLI contract; if a scheduled/production caller exists, STOP and report. Then write the tests in the spec's test plan (new refusal + new fields failing first; update the existing label assertion at tests/test_score_backtest_cli.py:~123 as the one intended behavior change), and make the smallest change per Scope 1-3. Forbidden: `research/**`, `ledger/**`, `metrics.py`, `config.py`, `strategies/**`, `h7_*`, frozen constants, new dependencies. Run targeted tests, then the full offline suite, `ruff check .`, `pyright`; report exact commands, exit codes, changed files, failures. Review the diff for scope creep and unsafe defaults. Batch landing with the next `options_researcher`/`tools` landing (diagnostic_source_hash rekey). No completion claim without fresh verification output.

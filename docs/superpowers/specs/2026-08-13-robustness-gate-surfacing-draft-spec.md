# DRAFT SPEC — Surface the computed-but-discarded robustness gate outcomes (+ honest stress-arm labeling)

- **Status:** DRAFT — NOT approved, NOT scheduled. Produced by the 2026-08-13 weekly-digest review session. No code was changed in that session.
- **Date:** 2026-08-13 (America/New_York)
- **Owner:** Carsyn (approval + landing window); implementing agent: Codex from this brief.
- **Decision label:** INSTRUMENT ONLY (audit-output completeness; zero verdict authority).
- **Source evidence:** Repo-verified defect found during adversarial architecture review (Opus reviewer, 2026-08-13): `analyze_stability()` returns a `gate_outcomes` map including a computed `cost_stress` FAIL/PASS gate and a `cost_sensitive` flag, but the runner records only `registration / adverse_bottom_bucket / holm / production_promotion`. The computed cost gate — plus `sign_consistency`, `ticker/regime/window_concentration`, and `minimum_observations` gates — never reaches the registry, CSV, JSON, or markdown outputs. No paper is load-bearing for this spec; it is an internal completeness defect.

## Repository state at spec time

- Branch `claude/options-validator-research-review-e27946`, HEAD `eea4700b36266da74b35f37e83467816947e0933`, clean tree, retrieved 2026-08-13 23:43 EDT.
- Relevant files: `options_researcher/robustness/runner.py` (stress arms at line 225; diagnostic recording ~lines 430-482), `options_researcher/robustness/stability.py` (cost_sensitive predicate lines 83-107), `options_researcher/robustness/reporting.py` (CSV lines ~85-116; markdown ~246-250), `tests/test_robustness_layer.py`.

## Problem statement

The robustness diagnostic layer computes stability gates it then silently drops. An auditor reading the recorded gate map would conclude cost sensitivity was never assessed, when in fact it was assessed and discarded. Additionally, the stress arms (0.5x/1.0x/1.5x) are point estimates with no bootstrap CI, and the `all_costs` arm scales the deterministic $0.65/leg commission (which has no economic reason to scale) — the current labels do not disclose either fact.

## Existing behavior and verified gap

- `stability.analyze_stability()` computes `cost_sensitive` (any multiplier > 1.0 arm flipping sign vs base, or `min(stressed) < base * 0.5`) and a `gate_outcomes` dict including `"cost_stress": "FAIL"/"PASS"`.
- `runner.py` (~430-482) consumes only `out_of_sample_decay`, `sign_consistency` (partially), `rank_stability`, concentrations, `brittle_isolated_peak`; the recorded gate map omits the stability-layer gates above. VERIFIED by adversarial review this session; Codex must re-verify from fresh HEAD before changing anything.

## Goal

Every gate the robustness layer computes appears verbatim in every recorded output surface (registry record, CSV, JSON, markdown), and stress-arm labels state what the numbers are (deterministic arithmetic sensitivities of one sample, no CI, commission scaled arithmetically in the `all_costs` arm).

## Scope

1. Pass `diagnostic.gate_outcomes` through to the recorded gate map and all report surfaces, additively (existing keys keep their names and values).
2. Pin the `stability.py` `cost_sensitive` predicate to the explicit multiplier set `(1.5,)` — i.e., freeze current semantics by construction instead of "all multipliers > 1.0" — so any future arm addition cannot silently change the gate. This is a semantics-preserving refactor; a red-green test must prove the predicate's outputs are unchanged on fixture data.
3. Reporting labels: mark stress arms "arithmetic sensitivity (no CI; commissions scaled arithmetically in all-costs arm)"; give the 0.5x arm equal visual weight to the >1x arms.

## Non-goals

- NO new stress multiplier (a proposed 2.0x arm was reviewed and REJECTED 2026-08-13).
- NO wiring of any surfaced gate into promotion, ranking, registration, or verdict logic. Surfacing is reporting only.
- NO change to Holm parameters, primary metric, fold logic, or `ExperimentSpec` schema.

## Forbidden changes

`research/hashing.py`, `research/ledger.py`, `research/experiments.py`, `ledger/**` (append-only; typed APIs only), `config.py` frozen constants, `options_researcher/robustness/models.py`, `walk_forward.py`, `return_matrix.py`, all `h7_*` modules, `strategies/**`, `metrics.py`. No new dependencies. Existing H7 receipts on disk are never edited.

## Architecture fit and ownership boundary

Stays entirely inside the display-only robustness diagnostic lane (no verdict authority per repo policy). Owner approval is required only for the landing window (below), not for any number — this spec freezes no new constant.

## Landing-window constraint (operationally binding)

`options_researcher/` is inside the live `diagnostic_source_hash()` surface (`research/hashing.py` `DIAGNOSTIC_SOURCE_PATHS_V2/V3`) consumed by `h7_watch`, `h7_exit_session`, `h7_source_health`, `h7_activation_guard`. Landing this change rekeys the live H7 source identity: receipts cut before the merge will be refused until the next session re-cuts them. Therefore: (a) batch this with the next planned `options_researcher/` landing rather than landing it alone; (b) it MUST land before any robustness `ExperimentSpec` is registered (the runner's `doctor()` pins `git_commit_sha`); (c) never land it mid-ritual between a receipt cut and its consuming session.

## File-level change plan

- `options_researcher/robustness/runner.py`: merge `diagnostic.gate_outcomes` into the recorded gate map (namespaced or flat — keep existing four keys untouched; on any key collision, fail loudly rather than overwrite).
- `options_researcher/robustness/stability.py`: replace the implicit "all multipliers > 1.0" iteration with an explicit frozen tuple `(1.5,)` module constant, documented as semantics-preserving.
- `options_researcher/robustness/reporting.py`: emit the enlarged gate map in CSV/JSON/markdown; add the arithmetic-sensitivity labels; equal-weight 0.5x arm.
- `tests/test_robustness_layer.py`: (1) failing-first test that the recorded gate map contains `cost_stress`, `sign_consistency`, concentration and `minimum_observations` gates; (2) invariance test that the four existing gate keys and the `cost_sensitive` boolean are byte-identical on fixture data before/after; (3) collision fail-loud test.

## Interfaces, schemas, formulas, units

No formula changes. Gate map schema gains keys with the exact names `analyze_stability()` already emits. All outputs continue to carry their max as-of session stamps where present. Timestamps unchanged.

## Fail-closed and abstention behavior

If `gate_outcomes` is missing or malformed, the runner must raise (fail loud), not silently record a partial map. No fallback defaults.

## Point-in-time, preregistration, OOS, licensing

No data access, no OOS interaction, no registration change, no third-party code (licensing: none).

## Edge cases

- Zero-variant runs / empty panels: gate map absent → runner already refuses; keep that.
- A future added multiplier must NOT alter `cost_sensitive` (guaranteed by the pinned tuple + test).

## Test-first plan and required checks

Red-green as above, then: `uv run python -m unittest discover -s tests -p "test_robustness_layer.py"`, then full `uv run python -m unittest discover -s tests`, `uv run ruff check .`, `uv run pyright`. All exit 0 required.

## Acceptance criteria

1. Every gate `analyze_stability()` computes appears in registry + CSV + JSON + markdown for a fixture run.
2. Existing four gate keys, `cost_sensitive`, primary metrics, Holm outputs: byte-identical on fixtures (baseline-invariance check).
3. Stress labels disclose arithmetic-sensitivity + commission caveat.
4. Full suite, ruff, pyright green.

## Risks and invalidation

Risk: silent semantic drift of `cost_sensitive` — mitigated by pinned tuple + invariance test. Risk: H7 receipt refusal on landing day — mitigated by the landing-window constraint. Invalidation: if fresh-HEAD re-verification shows the gates are already surfaced (i.e., the defect was fixed since `eea4700`), STOP and report; do not re-implement.

## Rollback / disable path

Single revert commit; the lane is diagnostic-only, so rollback has no verdict or ledger consequence. Receipts re-cut next session either way.

## Residual unknowns

Whether the owner wants the surfaced gates namespaced (e.g. `stability.cost_stress`) or flat — implementer proposes in the PR, does not invent a schema elsewhere.

## Paste-ready Codex prompt

> Implement `docs/superpowers/specs/2026-08-13-robustness-gate-surfacing-draft-spec.md` in the options-validator repo. First: capture fresh repo state (branch, HEAD SHA, `git status`) and re-verify the defect on YOUR HEAD — read `options_researcher/robustness/runner.py` (~lines 430-482) and `stability.py` (~83-107) and confirm `gate_outcomes` (incl. `cost_stress`) is computed but absent from recorded outputs; if already fixed, STOP and report. Then: write the failing tests listed in the spec's test-first plan and show them fail. Then make the smallest change per the file-level plan — runner gate-map merge (fail-loud on collision), stability predicate pinned to explicit `(1.5,)` with an invariance test, reporting labels. Forbidden: everything in the spec's Forbidden changes section; no new dependencies; no edits to frozen config constants, ledgers, registrations, OOS data, or live-order paths. Run: targeted `unittest discover -s tests -p "test_robustness_layer.py"`, then the full offline suite, `ruff check .`, `pyright` — report exact commands, exit codes, changed files, any failures. Review your own diff for scope creep and unsafe defaults before finishing. Respect the spec's landing-window constraint: this batches with the next `options_researcher/` landing and must precede any robustness ExperimentSpec registration; note this in your handoff. No completion claim without fresh verification output.

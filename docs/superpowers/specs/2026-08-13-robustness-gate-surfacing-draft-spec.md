# DRAFT SPEC — Surface the computed-but-discarded robustness gate outcomes (+ honest stress-arm labeling)

- **Status:** DRAFT v2 — NOT approved, NOT scheduled. Produced by the 2026-08-13/14 weekly-digest review session; v2 folds in the fresh-context adversarial verifier's corrections (B6-B8, M9). No production code was changed in that session.
- **Date:** 2026-08-13, revised 2026-08-14 (America/New_York)
- **Owner:** Carsyn (approval + landing window); implementing agent: Codex from this brief.
- **Decision label:** INSTRUMENT ONLY (audit-output completeness; zero verdict authority).
- **Source evidence:** Repo-verified defect (two independent Opus reviews, 2026-08-13/14): `analyze_stability()` returns `gate_outcomes` — a tuple of (name, PASS/FAIL) pairs including a computed `cost_stress` gate — plus a `cost_sensitive` flag, but `runner.py` records only four gate keys (`registration / adverse_bottom_bucket / holm / production_promotion`, runner.py:472-477). `StabilityDiagnostic.gate_outcomes` has ZERO consumers repo-wide (verified by grep: only stability.py:36,122). The computed stability gates (`cost_stress`, `sign_consistency`, ticker/regime/window concentrations, `minimum_observations`, `brittleness`) never reach the registry, CSV, JSON, or markdown. No paper is load-bearing for this spec; it is an internal completeness defect.

## Repository state at spec time
- Branch `claude/options-validator-research-review-e27946`, HEAD `eea4700b36266da74b35f37e83467816947e0933`, clean tree, retrieved 2026-08-13 23:43 EDT.
- Relevant files: `options_researcher/robustness/runner.py` (stress arms line 225; gate recording ~430-482, four-key map at 472-477), `options_researcher/robustness/stability.py` (predicate `multiplier > 1.0` at line 87; `gate_outcomes` construction ~108-122), `options_researcher/robustness/reporting.py` (CSV ~85-116, gates serialized wholesale ~120; markdown ~219, 246-250), `tests/test_robustness_layer.py`.

## Problem statement
The robustness diagnostic layer computes stability gates it then silently drops. An auditor reading the recorded gate map would conclude cost sensitivity was never assessed, when it was assessed and discarded. Additionally, the stress arms (0.5x/1.0x/1.5x) are point estimates with no bootstrap CI, and the `all_costs` arm scales the deterministic $0.65/leg commission (no economic reason to scale) — current labels disclose neither fact.

## Existing behavior and verified gap
- `stability.analyze_stability()` computes `cost_sensitive` (any multiplier > 1.0 arm flipping sign vs base, or `min(stressed) < base * 0.5`) and `gate_outcomes` as a `tuple[tuple[str, str], ...]` (NOT a dict — stability.py:36,122) including `"cost_stress"`.
- `runner.py:472-477` records exactly four gate keys; none of the stability-layer gates appear in any output surface. VERIFIED twice this session; Codex must re-verify from fresh HEAD before changing anything.

## Goal
Every gate `analyze_stability()` emits — including `brittleness` — appears in the recorded registry payload and every report surface, unambiguously distinguishable from the existing keys, and stress-arm labels state what the numbers are (deterministic arithmetic sensitivities of one sample, no CI, commission scaled arithmetically in the `all_costs` arm).

## Scope
1. Convert `diagnostic.gate_outcomes` (tuple of pairs) to a dict and merge into the recorded gate map **namespaced with a `stability.` prefix** (e.g. `stability.cost_stress`). Rationale (verifier B7): a flat merge would collide with the EXISTING `cost_stress` key in the recorded metrics dict / CSV column (runner.py:466; reporting.py:85,112), which holds the stress-arm value mapping — same name, different meaning. The namespace decision is made HERE, not left to the implementer.
2. Pin the `stability.py` cost-sensitivity predicate to the explicit multiplier set `(1.5,)` — freezing current semantics by construction instead of "all multipliers > 1.0". **Fail-loud requirement (verifier B8):** if the pinned multiplier is absent from `cost_stress_metrics`, raise — never let an empty `stressed` list silently produce an optimistic PASS. A red-green test proves predicate outputs are unchanged on fixture data.
3. Reporting labels: mark stress arms "arithmetic sensitivity (no CI; commissions scaled arithmetically in all-costs arm)"; give the 0.5x arm equal visual weight to the >1x arms.

## Non-goals
- NO new stress multiplier (a proposed 2.0x arm was reviewed and REJECTED 2026-08-13: runner.py sits inside the live `diagnostic_source_hash()` surface; the arm would not be display-only under the current predicate; marginal information ~zero).
- NO wiring of any surfaced gate into promotion, ranking, registration, or verdict logic. Surfacing is reporting only.
- NO change to Holm parameters, primary metric, fold logic, or `ExperimentSpec` schema.

## Forbidden changes
`research/hashing.py`, `research/ledger.py`, `research/experiments.py`, `ledger/**` (append-only; typed APIs only), `config.py` frozen constants, `options_researcher/robustness/models.py`, `walk_forward.py`, `return_matrix.py`, all `h7_*` modules, `strategies/**`, `metrics.py`. No new dependencies. Existing H7 receipts on disk are never edited.

## Architecture fit and ownership boundary
Stays entirely inside the display-only robustness diagnostic lane. Owner approval is required only for the landing window; this spec freezes no new constant (the `(1.5,)` pin restates the existing runner literal; provenance: semantics-preserving refactor, not a new number).

## Landing-window constraint (operationally binding)
`options_researcher/` is inside the live `diagnostic_source_hash()` surface (`research/hashing.py:132-133`, `DIAGNOSTIC_SOURCE_PATHS_V2/V3`) consumed by `h7_watch`, `h7_exit_session`, `h7_source_health`, `h7_activation_guard`, **and `h7_data_gate`**. Landing this change rekeys the live H7 source identity: receipts cut before the merge will be refused until re-cut. Therefore: (a) batch with the next planned `options_researcher/` landing, never alone; (b) MUST land before any robustness `ExperimentSpec` is registered (`doctor()` pins `git_commit_sha`); (c) never land mid-ritual between a receipt cut and its consuming session.

## File-level change plan
- `options_researcher/robustness/runner.py`: `dict(diagnostic.gate_outcomes)` → merge under `stability.` prefix into the recorded gate map; existing four keys untouched.
- `options_researcher/robustness/stability.py`: explicit pinned tuple `(1.5,)` module constant + fail-loud on absence (Scope 2).
- `options_researcher/robustness/reporting.py`: gates are serialized wholesale (~120, 219), so surfaces pick the new keys up automatically once the runner merges — verify rather than re-plumb; add the arithmetic-sensitivity labels; equal-weight 0.5x arm.
- `tests/test_robustness_layer.py`:
  1. Failing-first test: the recorded **registry payload** (the discriminating surface — CSV/JSON/markdown serialize the same map wholesale and cannot fail independently) contains every gate name `analyze_stability()` emits, `stability.`-prefixed, including `stability.brittleness`.
  2. Invariance test: the four existing gate keys, their values, and the `cost_sensitive` boolean are identical on fixture data before/after.
  3. Fail-loud test: predicate raises when 1.5 is absent from `cost_stress_metrics`.
  4. Collision guard: asserting the existing `cost_stress` metrics key and `stability.cost_stress` coexist with distinct values on a fixture.

## Interfaces, schemas, formulas, units
No formula changes. Gate map gains `stability.`-prefixed keys mirroring `analyze_stability()` names verbatim. Outputs keep their max as-of session stamps. Timestamps unchanged.

## Fail-closed and abstention behavior
(Verifier B6: `gate_outcomes` is a required dataclass field, so "missing → raise" is unfalsifiable and is NOT the contract.) The testable invariant instead: every gate name emitted by `analyze_stability()` on the fixture appears in the recorded map — enforced by test 1. The Scope-2 fail-loud (pinned multiplier absent) is the one new runtime raise.

## Point-in-time, preregistration, OOS, licensing
No data access, no OOS interaction, no registration change, no third-party code (licensing: none).

## Edge cases
- Zero-variant runs / empty panels: runner already refuses; keep that.
- A future added multiplier cannot alter `cost_sensitive` (pinned tuple + tests 2-3).

## Test-first plan and required checks
Red-green per the four tests above, then: `uv run python -m unittest discover -s tests -p "test_robustness_layer.py"`, then full `uv run python -m unittest discover -s tests`, `uv run ruff check .`, `uv run pyright`. All exit 0 required.

## Acceptance criteria
1. Every `analyze_stability()` gate (incl. `brittleness`) appears `stability.`-prefixed in the registry payload for a fixture run (test 1 — the discriminating criterion).
2. Existing four gate keys, `cost_sensitive`, primary metrics, Holm outputs: identical on fixtures (baseline invariance, test 2).
3. Predicate fail-loud verified (test 3); no key collision (test 4).
4. Stress labels disclose arithmetic-sensitivity + commission caveat.
5. Full suite, ruff, pyright green.

## Risks and invalidation
Risk: silent semantic drift of `cost_sensitive` — mitigated by pinned tuple + invariance + fail-loud tests. Risk: H7 receipt refusal on landing day — mitigated by the landing-window constraint. Invalidation: if fresh-HEAD re-verification shows the gates already surfaced, STOP and report; do not re-implement.

## Rollback / disable path
Single revert commit; diagnostic-only lane, no verdict or ledger consequence. Receipts re-cut next session either way.

## Residual unknowns
None blocking. (v1's namespacing question was resolved by the verifier: `stability.` prefix, see Scope 1.)

## Paste-ready Codex prompt
> Implement `docs/superpowers/specs/2026-08-13-robustness-gate-surfacing-draft-spec.md` (v2) in the options-validator repo. First: capture fresh repo state (branch, HEAD SHA, `git status`) and re-verify the defect on YOUR HEAD — read `options_researcher/robustness/runner.py` (gate recording ~472-477) and `stability.py` (~36, 87, 108-122) and confirm `gate_outcomes` (a tuple of (name, PASS/FAIL) pairs incl. `cost_stress` and `brittleness`) is computed but absent from recorded outputs; if already fixed, STOP and report. Then: write the four failing tests in the spec's test plan and show them fail. Then make the smallest change per the file-level plan — dict() the gate tuple and merge under a `stability.` prefix (the existing flat `cost_stress` metrics key must remain untouched and distinct), pin the stability predicate to `(1.5,)` with fail-loud on absence, add the reporting labels. Forbidden: everything in the spec's Forbidden changes section; no new dependencies; no edits to frozen config constants, ledgers, registrations, OOS data, or live-order paths. Run: targeted `unittest discover -s tests -p "test_robustness_layer.py"`, then the full offline suite, `ruff check .`, `pyright` — report exact commands, exit codes, changed files, failures. Review your own diff for scope creep and unsafe defaults. Respect the landing-window constraint: batch with the next `options_researcher/` landing (diagnostic_source_hash rekey; receipts re-cut), and land before any robustness ExperimentSpec registration; state this in your handoff. No completion claim without fresh verification output.

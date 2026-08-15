# A2 Outcome Battery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run the one-shot exploratory A2-v1 historical outcome battery that measures whether the frozen mechanical ranking's top tercile beats its bottom tercile after costs, separately by strategy lane and registered arm.

**Architecture:** A narrow A2 module constructs immutable, causal outcome rows from local point-in-time inputs and converts only non-overlapping cohorts into the existing robustness panel/statistics boundary. A separate descriptive staggered-book view consumes all eligible entries but cannot feed inference. One orchestration module validates preregistration and the owner-approved entry addendum, writes a deterministic one-run report, and appends a result only after the report exists.

**Tech Stack:** Python 3.12, pandas, NumPy, unittest, existing `options_researcher.attractiveness`, `options_researcher.robustness`, `metrics`, `research.hashing`, and `research.ledger` modules. No new dependency.

**Spec:** `docs/superpowers/specs/2026-08-15-a2-entry-convention-addendum.md`, together with `docs/superpowers/plans/2026-07-23-twelve-month-scanner-research-program.md` sections 4-6 and `docs/superpowers/plans/2026-07-23-codex-execution-queue.md` EX8.

## Global Constraints

- Historical output is exploratory only and never verdict-bearing, FIRE-capable, ranking-changing, or production-promoting.
- Use cached local chain, close, feature, rate, earnings, and position inputs only; no network provider and no live or paper order path.
- Signal date uses only information available by that close; entry is the next trading-session close; liquidity and exact quotes are required at entry and resolution.
- Lanes never pool. CSP arms and LEAPS/tactical horizons remain distinct parameter IDs. PMCC with no real recorded LEAPS is `no data`.
- Inference uses non-overlapping cohorts only. The staggered view is descriptive and structurally cannot enter p-values, confidence intervals, or Holm adjustment.
- Reuse the existing top-minus-bottom metric, dependence-aware bootstrap/permutation, Holm alpha 0.10, bucket count 3, 5,000 repetitions, cost model, and plus/minus 50 percent stress logic.
- The one-run report refuses before data loading if the report/result exists or required registration/addendum evidence is absent.
- Follow strict red-green-refactor. Preserve scanner grades/order byte-identical and do not touch unrelated work.

---

### Task 1: Pure A2 contracts, cohort separation, and battery summary

**Files:**
- Create: `options_researcher/a2_battery.py`
- Create: `tests/test_a2_battery.py`

**Interfaces:**
- Consumes: resolved outcome records containing decision, entry, resolution, lane/arm, score, return, cost, component, and provenance fields.
- Produces: `A2Outcome`, `A2VariantSummary`, `validate_outcomes(...)`, `non_overlapping_inference_rows(...)`, `staggered_descriptive_rows(...)`, and `summarize_lane(...)`.

- [ ] **Step 1: Write failing contract and causality tests**

  Add literal fixtures proving invalid dates, entry not after decision, resolution before entry, unknown lanes/arms, non-finite returns, negative costs, missing lane-specific accounting fields, duplicate identities, and mixed lanes fail closed. The production mutation each test catches is a malformed or pooled row entering A2.

- [ ] **Step 2: Run the focused tests and verify RED**

  Run: `uv run python -m unittest discover -s tests -p 'test_a2_battery.py'`

  Expected: import failure because `options_researcher.a2_battery` does not exist.

- [ ] **Step 3: Implement immutable outcome contracts and validation**

  Use frozen dataclasses and literal lane/parameter registries. Require all registered accounting components by lane. Preserve gross return, modeled cost, bid/ask cost, and cost-adjusted return separately and require exact reconciliation within `1e-12`.

- [ ] **Step 4: Write failing cohort-separation tests**

  Test that inference greedily accepts chronologically ordered cohort dates only when the prior accepted cohort's maximum resolution date is strictly before the next entry date. Test that every valid row remains in the staggered view and that changing staggered-only rows cannot change the inference summary.

- [ ] **Step 5: Implement structurally separate views**

  Return distinct immutable tuples. Do not add a flag that lets the staggered view call inference code.

- [ ] **Step 6: Write failing summary tests**

  With hand-computed 15-name fixtures, assert deterministic five/five/five terciles, top-minus-bottom spread, middle monotonicity, positive-cohort win rate, median, worst cohort, cumulative-spread drawdown, top-bucket turnover, bottom-bucket observation count, and 0.5/1.0/1.5 cost stresses. Assert empty PMCC renders `no data`. Assert CSP arms and long-call horizons remain separate.

- [ ] **Step 7: Implement the minimal battery summary**

  Convert inference rows to existing `robustness.screening.PanelObservation`; reuse `cost_adjusted_primary_metric`, `_stress_metrics`, `_permutation_result`, `holm_step_down`, and `metrics.dependence_aware_expectancy_ci` rather than duplicating their math. Emit raw and Holm-adjusted p-values separately. If effective K or measured dependence requires Romano-Wolf, emit `BLOCKED_ROMANO_WOLF_UNAVAILABLE` and no adjusted claim.

- [ ] **Step 8: Verify and commit Task 1**

  Run the focused A2 tests plus `test_robustness_layer.py`, `test_bootstrap.py`, and Ruff on the two task files. Commit only Task 1 files.

### Task 2: Causal local-cache panel construction and outcome resolution

**Files:**
- Create: `options_researcher/a2_panel.py`
- Create: `tests/test_a2_panel.py`
- Modify: `config.py`

**Interfaces:**
- Consumes: explicit local paths/loaders for chain cache, raw/adjusted closes, features, rates, earnings assertions, and positions; the approved selectors in the A2 addendum.
- Produces: `build_historical_outcomes(...) -> tuple[A2Outcome, ...]` plus counted skip/data-quality diagnostics and max-as-of provenance.

- [ ] **Step 1: Add failing selector and T+1 tests**

  Pin the CSP/CC nearest-income-delta selectors, LEAPS thesis-delta selector, tactical-delta selector, deterministic tie order, signal at `t`, fill at `t+1`, and the 15-name registered A2 universe. Later fixture rows must not change a day-`t` selection.

- [ ] **Step 2: Verify RED and add only the frozen constants**

  Run: `uv run python -m unittest discover -s tests -p 'test_a2_panel.py'`

  Add A2 registration identifiers, universe, horizons, and arm names to `config.py` with sequence-19/addendum citations. Do not add tunable thresholds.

- [ ] **Step 3: Implement causal entry construction**

  Reuse card/chain selection primitives, but return typed A2 entry records rather than presentation dictionaries. Require exact next-session quotes and entry liquidity. CC creates the approved same-close 100-share benchmark. PMCC reads real positions only and otherwise returns the explicit empty-lane status.

- [ ] **Step 4: Add failing outcome-resolution tests**

  Cover five CSP exits including expiration-first fixed horizon and breach-to-21-DTE; CC option/stock/combined/benchmark/assignment/lost-upside decomposition; LEAPS 21/63/126 marks; tactical 5/10/20 marks and six-term attribution reconciliation; roll close-plus-open cost; missing resolution quotes; crossed/zero/illiquid quotes; and plus/minus 50 percent cost preservation.

- [ ] **Step 5: Implement minimal lane resolvers**

  Use adverse quote-side fills and per-leg/per-side commissions from existing helpers. Skip and count missing or invalid resolution inputs; never substitute a later quote. Raw closes drive strike/payoff; adjusted closes drive trailing features. Preserve full component accounting in every outcome.

- [ ] **Step 6: Add a programmatic data-audit surface**

  `audit_historical_inputs(...)` must print/return all fourteen checks required by `.agents/skills/options-data-audit/SKILL.md`, scoped to contracts actually selected or eligible. A tradeable-contract failure returns `BLOCK`; warnings never disappear silently.

- [ ] **Step 7: Verify and commit Task 2**

  Run `test_a2_panel.py`, `test_attractiveness.py`, `test_rq1_runner.py`, `test_top3_snapshot.py`, and Ruff/Pyright on affected files. Commit only Task 2 files.

### Task 3: One-run orchestration, immutable report, and historical execution gate

**Files:**
- Create: `options_researcher/a2_runner.py`
- Create: `tests/test_a2_runner.py`
- Create: `reports/2026-08-15-a2-entry-convention-validation.md`

**Interfaces:**
- Consumes: Task 2 outcomes/audit plus Task 1 summaries.
- Produces: `reports/a2/a2-v1.json`, optional CSV/Markdown views, and an optional chained `retrospective_result` ledger append after report verification.

- [ ] **Step 1: Write failing governance and one-run tests**

  Assert refusal before loaders when the report exists; refusal without ledger seq 19, its exact record hash, `RQ2_A2_PIN_ADDENDUM_V1`, and the new owner-approved entry-convention fact; retry of an existing verified report after a failed ledger append; refusal on any data-audit `BLOCK`; and refusal to expose a forward verdict.

- [ ] **Step 2: Verify RED and implement the write-once shell**

  Use exclusive-create/atomic writes, canonical JSON, file hashes, Git SHA, runner hash, chain/close max-as-of values, exclusion counts, registration/addendum references, and explicit `RESEARCH-ONLY / NO VERDICT` labels.

- [ ] **Step 3: Write failing report-content tests**

  Pin all five lane statuses, each arm/horizon, inference vs staggered separation, required diagnostics, raw/adjusted p-values, cost stress, provenance, audit verdict, realism grade, and unsupported-forward-fields list. Scanner ordering/grades must be byte-identical before and after importing/running the module on fixtures.

- [ ] **Step 4: Implement CLI and report assembly**

  Provide `python -m options_researcher.a2_runner --historical` with local-path overrides for tests and `--append-result` as an explicit publication action. No network, broker, paper-book, dashboard, or ranking imports are allowed in the runner.

- [ ] **Step 5: Verify and commit Task 3 before any historical run**

  Run all A2 tests, targeted adjacent suites, Ruff, formatting, and Pyright. Generate an adversarial review receipt before invoking `--historical`.

- [ ] **Step 6: Audit and execute once**

  Append the owner-approved entry-convention fact through `research.facts.append_fact`. Run the programmatic options-data audit. Perform the realism audit. Only if neither blocks, invoke the historical runner exactly once, append the retrospective result immediately, and then red-team the statistics before discussing them.

- [ ] **Step 7: Final verification**

  Run `uv run python -m unittest discover -s tests`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`. Independently review the whole diff and report any unrelated baseline warnings separately.


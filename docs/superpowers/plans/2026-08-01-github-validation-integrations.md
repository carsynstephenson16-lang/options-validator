# Free GitHub Validation Integrations Implementation Plan

> **For implementation:** Follow this plan in order. Preserve the isolated
> worktree boundary, demonstrate red/green evidence for each integration, and
> commit each component separately. QuantLib Task 3 is blocked until the owner
> explicitly overrides the older C3 trigger in
> `2026-07-23-six-library-adoption-codex-brief.md` for this test-only use.

**Goal:** Integrate Hypothesis 6.164.0, QuantLib 1.43, and Coverage.py 7.15.2
as free, test-only validation infrastructure without changing production
pricing, research authority, data, ledgers, caches, or trading paths.

**Architecture:** Hypothesis drives bounded offline properties against the
existing European Black-Scholes module. QuantLib remains in a separate uv
project and provides a serialized reference adapter for European comparisons
and American/discrete-dividend bounds. Coverage.py measures the existing root
suite and adds a baseline-derived non-regression gate. No selected component is
imported from a production execution path.

**Toolchain:** Python 3.12, uv, unittest, Hypothesis, QuantLib Python bindings,
Coverage.py, Ruff, Pyright, GitHub Actions.

**Design:**
`docs/superpowers/specs/2026-08-01-github-validation-integrations-design.md`

**Worktree:**
`/Users/carsynstephenson/Downloads/options-validator/github-integrations-20260801`

**Branch:** `optimization/github-integrations-20260801`

**Base:** `5167d3853a87c4f11b17a18e8c65d236afad91b3`

**No-push default:** Do not push this branch.

---

## Task 1: Capture the reproducible implementation baseline

**Files:**

- Create: `/private/tmp/options-validator-github-integrations-baseline/`
  artifacts only; do not add it to Git.
- Inspect: `pyproject.toml`
- Inspect: `uv.lock`
- Inspect: `.github/workflows/ci.yml`
- Inspect: `tests/test_black_scholes.py`
- Inspect: `PROJECT_STATE.md`

### Step 1: Reconfirm the isolated worktree

Run:

```bash
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
```

Expected:

- Top level is the approved isolated worktree.
- Branch is `optimization/github-integrations-20260801`.
- HEAD includes only the approved design/plan commits over the recorded base.
- Status is clean.

### Step 2: Record runtime and locked-environment metadata

Run:

```bash
uv --version
uv run --frozen python --version
uv tree --depth 2
```

Save command, version, exit code, and relevant output in the final audit notes.
Do not change the lock.

### Step 3: Run baseline lint and types

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --offline ruff check .
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --offline pyright
```

Expected: exit 0 based on Phase 1. If dependency cache is incomplete, rerun the
same commands with approved read-only package access and document why.

### Step 4: Run the baseline unit suite outside the restrictive SQLite sandbox

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -m unittest discover -s tests
```

Record total tests, elapsed time, exit code, first failure, and whether the
checkout changed during the run. Do not call a partial run the full baseline.

### Step 5: Measure pre-integration coverage without changing tracked files

Run with an ephemeral pinned tool:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --with coverage==7.15.2 coverage erase
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --with coverage==7.15.2 coverage run --branch --source=options_researcher,data,research,strategies,harness -m unittest discover -s tests
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --with coverage==7.15.2 coverage report --show-missing
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen --with coverage==7.15.2 coverage json -o /private/tmp/options-validator-github-integrations-baseline/coverage.json
```

Expected: a measured statement and branch baseline. If the full suite fails,
preserve the partial coverage output only as diagnostic evidence and label the
full coverage baseline BLOCKED; do not derive a fail-under threshold from an
incomplete run.

### Step 6: Confirm no tracked mutation

Run:

```bash
git status --short
```

Expected: clean. Remove no files; if `.coverage` appears, add the narrow ignore
during Task 4 rather than deleting user artifacts in another checkout.

---

## Task 2: Integrate Hypothesis property tests

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create: `tests/test_black_scholes_properties.py`
- Test: `tests/test_black_scholes.py`

### Step 1: Add the property test before the dependency

Create `tests/test_black_scholes_properties.py` with a minimal first property:

```python
import math
import unittest

from hypothesis import given, settings, strategies as st

from options_researcher.black_scholes import bs_price


FINITE_POSITIVE = st.floats(
    min_value=1.0,
    max_value=1_000.0,
    allow_nan=False,
    allow_infinity=False,
)


class TestBlackScholesProperties(unittest.TestCase):
    @settings(max_examples=100, deadline=None, derandomize=True)
    @given(
        spot=FINITE_POSITIVE,
        strike=FINITE_POSITIVE,
        tenor=st.floats(0.0, 5.0, allow_nan=False, allow_infinity=False),
        rate=st.floats(-0.10, 0.20, allow_nan=False, allow_infinity=False),
        dividend=st.floats(0.0, 0.20, allow_nan=False, allow_infinity=False),
        sigma=st.floats(0.0, 3.0, allow_nan=False, allow_infinity=False),
    )
    def test_put_call_parity(self, spot, strike, tenor, rate, dividend, sigma):
        call = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="C", q=dividend
        )
        put = bs_price(
            S=spot, K=strike, t=tenor, r=rate, sigma=sigma, right="P", q=dividend
        )
        expected = spot * math.exp(-dividend * tenor) - strike * math.exp(-rate * tenor)
        self.assertAlmostEqual(call - put, expected, delta=1e-9 * max(1.0, spot, strike))
```

The implementation may factor shared strategies for readability, but it must
not widen domains beyond the production module's documented support.

### Step 2: Run the red test

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -m unittest tests.test_black_scholes_properties
```

Expected: FAIL because `hypothesis` is not in the locked root environment.
Capture the exact failure.

If Hypothesis is unexpectedly already importable through a transitive package,
the red proof becomes an explicit assertion that the project declares version
6.164.0 in its dev group; add that characterization test before proceeding.

### Step 3: Add only the pinned free test dependency

Modify `[dependency-groups].dev`:

```toml
"hypothesis==6.164.0",
```

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv lock
```

Inspect:

```bash
git diff -- pyproject.toml uv.lock
uv tree --package hypothesis
```

Expected:

- Direct version is exactly 6.164.0.
- Only Hypothesis and required transitive packages are introduced.
- No unrelated direct dependency changes.
- No paid service, credential, or runtime network dependency appears.

### Step 4: Expand the property suite

Add bounded deterministic properties for:

1. call/put monotonicity in spot;
2. call/put monotonicity in strike;
3. discounted European lower and upper bounds;
4. put-call parity under continuous yield;
5. gamma and vega nonnegativity on the strict interior domain;
6. IV round trips over prices safely inside the `[IV_LOW, IV_HIGH]` bracket;
7. expiry and zero-volatility behavior; and
8. invalid non-finite/negative inputs using explicit examples.

Use tolerances scaled to price magnitude. Do not silence falsifying examples,
use unbounded random domains, or reduce an assertion merely to make it pass.

### Step 5: Run green focused tests

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -m unittest tests.test_black_scholes_properties tests.test_black_scholes
```

Expected: PASS. Record test count, examples where visible, elapsed time, and
Hypothesis version:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -c "import hypothesis; print(hypothesis.__version__)"
```

### Step 6: Run integration-specific quality checks

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen ruff check tests/test_black_scholes_properties.py
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen pyright tests/test_black_scholes_properties.py
git diff --check
```

Expected: all exit 0.

### Step 7: Commit Hypothesis separately

Before staging:

```bash
git branch --show-current
git status --short
```

Stage only:

```bash
git add pyproject.toml uv.lock tests/test_black_scholes_properties.py
git diff --cached --check
git diff --cached --stat
git commit -m "test(options): add Hypothesis pricing invariants"
```

---

## Task 3: Integrate the isolated QuantLib reference

**Hard gate:** Do not execute this task until the owner explicitly confirms:

```text
override C3 for test-only QuantLib validation without registering a new hypothesis
```

That approval supersedes only the QuantLib C3 trigger for this isolated test
adapter. It does not close P0.6, authorize research registration, or change any
model/strategy verdict.

**Files:**

- Create: `tools/quantlib_validation/pyproject.toml`
- Create: `tools/quantlib_validation/uv.lock`
- Create: `tools/quantlib_validation/__init__.py`
- Create: `tools/quantlib_validation/adapter.py`
- Create: `tools/quantlib_validation/tests/__init__.py`
- Create: `tools/quantlib_validation/tests/test_adapter.py`
- Create: `tools/quantlib_validation/README.md`
- Modify: `.github/workflows/ci.yml`
- Do not modify: `options_researcher/black_scholes.py` unless a minimized,
  independently proven defect requires a separately reviewed fix.

### Step 1: Create the isolated dependency manifest and failing tests

Create `tools/quantlib_validation/pyproject.toml`:

```toml
[project]
name = "options-validator-quantlib-validation"
version = "0.1.0"
description = "Isolated QuantLib reference checks for Options Validator"
requires-python = ">=3.12,<3.13"
dependencies = ["QuantLib==1.43"]

[tool.uv]
package = false
```

Create `tests/test_adapter.py` importing the not-yet-existing adapter symbols:

```python
from tools.quantlib_validation.adapter import (
    ExerciseStyle,
    OptionRight,
    PricingRequest,
    price_option,
)
```

Initial tests must cover a known European vector, input rejection, and
evaluation-date restoration.

### Step 2: Lock and run the red test

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv lock --project tools/quantlib_validation
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --project tools/quantlib_validation --frozen python -m unittest discover -s tools/quantlib_validation/tests
```

Expected: FAIL because `tools.quantlib_validation.adapter` does not exist.

Inspect the lock before native execution:

```bash
git diff -- tools/quantlib_validation/uv.lock
uv tree --project tools/quantlib_validation
```

Expected: exact QuantLib 1.43, no runtime HTTP client or paid service.

### Step 3: Implement typed request validation and global-state restoration

Implement frozen enums/dataclasses for option right, exercise style, dividend
treatment, request, and result. Validate all Python inputs before constructing
native objects.

Core implementation shape:

```python
_QUANTLIB_LOCK = threading.Lock()


def price_option(request: PricingRequest) -> PricingResult:
    request.validate()
    with _QUANTLIB_LOCK:
        settings = ql.Settings.instance()
        previous_date = settings.evaluationDate
        try:
            settings.evaluationDate = _to_ql_date(request.valuation_date)
            return _price_with_declared_engine(request)
        finally:
            settings.evaluationDate = previous_date
```

Do not return raw QuantLib objects. The result records price, engine, exercise
style, dividend treatment, grid settings, day count, and QuantLib version.

### Step 4: Implement European and American engine paths

- European continuous-yield path: `AnalyticEuropeanEngine`.
- American continuous-yield path: `FdBlackScholesVanillaEngine` with declared
  grid sizes.
- Discrete-cash-dividend path: use the version-1.43 supported dividend schedule
  overload only after verifying its actual Python signature through `help()`.
- If the official wheel does not expose a safe discrete-dividend overload,
  mark that case BLOCKED and do not fake it with a continuous-yield conversion.

### Step 5: Add independent validation tests

Tests must include:

1. Internal European price versus QuantLib analytic European price.
2. Put-call parity computed independently of QuantLib.
3. American option price is at least intrinsic value.
4. American option price is at least the matched European value within the
   declared numerical tolerance.
5. A dividend-paying American call sensitivity case.
6. A non-dividend American call converges toward its European counterpart as
   the grid is refined.
7. Negative-rate support where both engines accept the declared input.
8. Invalid dates, spot, strike, volatility, dividend schedule, and grid sizes.
9. Evaluation-date restoration after success and forced failure.
10. Deterministic repeated results.

QuantLib comparison is never the only assertion in a test.

### Step 6: Run green and inspect native behavior

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --project tools/quantlib_validation --frozen python -m unittest discover -s tools/quantlib_validation/tests -v
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --project tools/quantlib_validation --frozen python -c "import QuantLib as ql; print(ql.__version__)"
```

Expected: PASS and version `1.43`.

### Step 7: Document assumptions, free-use terms, and rollback

`tools/quantlib_validation/README.md` must state:

- BSD-3-Clause and required notice handling;
- free/offline/no-key/no-service operation;
- test-only boundary;
- no thread safety because of QuantLib globals;
- ACT/365 Fixed convention;
- continuous versus discrete dividend behavior;
- engine/grid choices and tolerances;
- exact run command; and
- rollback by reverting the integration commit.

### Step 8: Add the isolated CI command

Add a step after root tests in `.github/workflows/ci.yml`:

```yaml
- name: QuantLib reference validation
  run: >-
    uv run --project tools/quantlib_validation --frozen
    python -m unittest discover -s tools/quantlib_validation/tests
```

Do not use a mutable third-party action or download a binary outside uv.

### Step 9: Run integration-specific quality checks

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen ruff check tools/quantlib_validation
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen pyright tools/quantlib_validation
git diff --check
```

Expected: all exit 0. If Pyright cannot resolve the isolated native module from
the root environment, configure a narrow isolated type-check command or a typed
protocol boundary; do not add `Any` or blanket ignores merely to get green.

### Step 10: Commit QuantLib separately

```bash
git branch --show-current
git add .github/workflows/ci.yml tools/quantlib_validation
git diff --cached --check
git diff --cached --stat
git commit -m "feat(options): add isolated QuantLib validation"
```

---

## Task 4: Integrate Coverage.py and a measured non-regression gate

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `.gitignore`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/test_coverage_configuration.py`

### Step 1: Write a failing configuration contract

Add a unittest that parses `pyproject.toml` with `tomllib` and requires:

- `coverage==7.15.2` in the dev dependency group;
- `[tool.coverage.run]` with `branch = true`;
- explicit measured source packages;
- omission of tests, caches, reports, isolated tools, and generated files; and
- `[tool.coverage.report]` with `show_missing = true` and the measured
  baseline-derived `fail_under` value.

### Step 2: Run red

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -m unittest tests.test_coverage_configuration
```

Expected: FAIL because coverage is not yet declared/configured.

### Step 3: Add the pinned dependency and configuration

Add to `[dependency-groups].dev`:

```toml
"coverage==7.15.2",
```

Add configuration equivalent to:

```toml
[tool.coverage.run]
branch = true
source = ["data", "harness", "options_researcher", "research", "strategies"]
omit = [
    "tests/*",
    "tools/*",
    "reports/*",
    "results/*",
    ".cache/*",
    ".tmp/*",
]

[tool.coverage.report]
show_missing = true
skip_empty = true
fail_under = <MEASURED_COMPLETE_BASELINE_FLOOR>

[tool.coverage.json]
output = "coverage.json"
pretty_print = true
```

Set `fail_under` only from the complete Task 1 baseline, rounding downward so
the unchanged tree passes. If a complete baseline is BLOCKED, omit `fail_under`
and record the reason; visibility is still useful, but no fabricated gate is
allowed.

Add only generated local coverage paths to `.gitignore`:

```text
.coverage
.coverage.*
coverage.json
htmlcov/
```

### Step 4: Update the lock and inspect the diff

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv lock
git diff -- pyproject.toml uv.lock .gitignore
uv tree --package coverage
```

Expected: Coverage.py 7.15.2 and no unrelated direct dependency change.

### Step 5: Run green contract and coverage command

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen python -m unittest tests.test_coverage_configuration
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage erase
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage run -m unittest discover -s tests
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage report
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage json
```

Expected: configuration test and full suite PASS; coverage report exits 0 and
records statement/branch totals.

### Step 6: Replace the CI unit-test step with measured coverage

Use one suite invocation:

```yaml
- name: Unit tests with branch coverage
  run: uv run coverage run -m unittest discover -s tests

- name: Coverage non-regression gate
  run: uv run coverage report
```

Do not run the full suite twice. Do not upload private reports to a third-party
service.

### Step 7: Run integration-specific checks

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen ruff check pyproject.toml tests/test_coverage_configuration.py
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen pyright tests/test_coverage_configuration.py
git diff --check
git status --short
```

Expected: all exit 0; only scoped files and ignored coverage artifacts exist.

### Step 8: Commit Coverage.py separately

```bash
git branch --show-current
git add .github/workflows/ci.yml .gitignore pyproject.toml uv.lock tests/test_coverage_configuration.py
git diff --cached --check
git diff --cached --stat
git commit -m "test(options): add measured branch coverage gate"
```

---

## Task 5: Full validation and audit-ready closeout

**Files:**

- Create: `reports/strategy-evaluations/17_github_validation_integrations_audit.md`
- Verify: all files changed since base
- Do not modify: ledgers, cache data, portfolio state, hypothesis registry, or
  provider configuration

### Step 1: Verify branch, diff, and commit separation

Run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline 5167d3853a87c4f11b17a18e8c65d236afad91b3..HEAD
git diff --stat 5167d3853a87c4f11b17a18e8c65d236afad91b3..HEAD
git diff --check 5167d3853a87c4f11b17a18e8c65d236afad91b3..HEAD
```

Expected: separate design, plan, Hypothesis, authorized QuantLib, Coverage,
and final-report commits; clean worktree.

### Step 2: Run all root gates

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv sync --frozen
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen ruff check .
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen pyright
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage erase
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage run -m unittest discover -s tests
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage report
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --frozen coverage json
```

Record exit codes, test count, elapsed time, coverage totals, and any failure
classification. Do not suppress failures.

### Step 3: Run the isolated QuantLib gate if authorized

Run:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --project tools/quantlib_validation --frozen python -m unittest discover -s tools/quantlib_validation/tests -v
```

If authorization was not provided, mark this integration BLOCKED and absent;
do not claim it was implemented.

### Step 4: Run read-only supply-chain checks

Use a pinned ephemeral scanner without `--fix`:

```bash
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --with pip-audit==2.10.1 pip-audit --local --strict
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run --project tools/quantlib_validation --with pip-audit==2.10.1 pip-audit --local --strict
```

Record every advisory and collection failure. An advisory requires analysis; it
must not be ignored merely to produce a green result. Skip the second command
when QuantLib is not authorized/installed.

### Step 5: Inspect the final diff adversarially

Review:

- dependency and lock changes;
- test determinism and tolerances;
- false-positive and false-negative risk;
- QuantLib global-state restoration and native failure paths;
- CI command correctness and duplicate suite runs;
- license/notice compliance;
- paid-service, telemetry, credential, provider, cache, and ledger absence;
- rollback completeness; and
- whether any production source change lacks independent proof.

### Step 6: Write the audit report

The report must include:

1. verdict and READY/NOT READY decision;
2. Phase 0–7 summary;
3. exact branch, base, final SHA, and commit list;
4. changed files by integration;
5. red/green and baseline/post-change commands with exits and elapsed time;
6. coverage before/after numbers with scope caveats;
7. component versions, canonical URLs, licenses, and free-use conclusion;
8. security and transitive dependency results;
9. unsupported assumptions and remaining gaps;
10. rollback commands per integration; and
11. no-push confirmation.

The report also gives the owner a concrete, recommendation-only design for a
weekly GitHub scan across the Kalshi weather bot, Options Validator, Equity
Research, and future relationship-manager sales-pipeline repositories. It must
require verified gaps, primary-source repository evidence, commercial-use
license checks, security review, weighted scoring, and explicit approval before
any install.

### Step 7: Validate and commit the report

Run:

```bash
git diff --check
git status --short
```

Stage only the audit report and any final documentation correction:

```bash
git add reports/strategy-evaluations/17_github_validation_integrations_audit.md
git diff --cached --check
git commit -m "docs(options): record validation integration audit"
```

### Step 8: Final clean-state proof

Run:

```bash
git status --short
git log --oneline 5167d3853a87c4f11b17a18e8c65d236afad91b3..HEAD
```

Expected: clean worktree and the exact reversible commit series. Do not push.

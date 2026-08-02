# GitHub Validation Integrations Audit

**Date:** 2026-08-01

**Repository:** Options Validator

**Branch:** `optimization/github-integrations-20260801`

**Base:** `5167d3853a87c4f11b17a18e8c65d236afad91b3`

**Implementation HEAD before this report:** `1b458532e1b45ae4f506bee8bedf695444015efe`

**Push status:** not pushed

## Verdict

**NOT READY as the original three-component package. READY FOR OWNER REVIEW as
the two-component validation-only subset.**

- **VERIFIED:** Hypothesis 6.164.0 is integrated as a development-only
  dependency with deterministic Black-Scholes properties.
- **VERIFIED:** Coverage.py 7.15.2 is integrated as a development-only
  dependency with one CI suite invocation and a baseline-derived 79% floor.
- **BLOCKED:** QuantLib 1.43 is absent. The older C3 repository rule says it is
  not installed until a registered American-exercise-Greeks trigger exists.
  The approved general design did not explicitly override that later-discovered
  rule, so implementation stopped fail-closed.
- **OBSERVED:** The complete integrated root suite passes 2,295 tests.
- **OBSERVED:** The read-only environment audit reports 35 advisory rows across
  9 pre-existing packages. Neither new package appears in the findings, but the
  environment-wide security gate is red and must not be described as clean.

No production pricing, strategy, provider, cache, ledger, portfolio, research
registration, verdict, or order source was changed.

## Phase 0-7 record

| Phase | Result | Evidence |
|---|---|---|
| 0. Preflight | **VERIFIED / BLOCKED by repo** | Options Validator was eligible for validation-only work in an isolated worktree. Equity Research retained its red hard gate, so no Equity Research files were changed. |
| 1. Current state | **VERIFIED** | Root lint and types were green; 2,283 tests passed with the explicit provider test setting and loopback permission; no measured coverage gate existed. |
| 2. Gap ranking | **VERIFIED** | Highest actionable gaps were mathematical property validation, an independent pricing reference, and measured test coverage. |
| 3. External research | **VERIFIED** | Versions, upstream repositories, licenses, release artifacts, dependency models, global-state risks, and commercial-use terms were reviewed. |
| 4. Selection | **VERIFIED** | Hypothesis scored 95/100, QuantLib 92/100, and Coverage.py 90/100 under the approved weighted rubric. |
| 5. Baseline | **VERIFIED** | Authoritative root run: 2,283 tests passed in 292.001s. Coverage baseline: 79.299716% combined, 82.581501% statements, 70.386100% branches. |
| 6. Implementation | **PARTIAL** | Hypothesis and Coverage.py landed in separate commits. QuantLib is blocked and absent. |
| 7. Validation | **PARTIAL / RED security context** | 2,295 tests, Ruff, Pyright, lock consistency, and the 79% coverage gate pass. The environment advisory scan is red; lockfile-mode scanning is unsupported by pip-audit 2.10.1 for `uv.lock`. |

## Reversible commit series

From the base through the implementation HEAD:

```text
1b45853 test(options): add measured branch coverage gate
8d67a9c test(options): add Hypothesis pricing invariants
a7ade0a docs(options): plan free validation integrations
9dc5f62 docs(options): design free validation integrations
```

This audit report is committed after the implementation series. A Git commit
cannot embed its own final SHA without changing that SHA; the exact report
commit and final branch HEAD belong in the external handoff produced after the
commit.

## Changed files by integration

### Design and execution plan

- `docs/superpowers/specs/2026-08-01-github-validation-integrations-design.md`
- `docs/superpowers/plans/2026-08-01-github-validation-integrations.md`

### Hypothesis 6.164.0

- `pyproject.toml`: exact development dependency
- `uv.lock`: Hypothesis plus `sortedcontainers` transitive dependency, with
  artifact hashes
- `tests/test_black_scholes_properties.py`: eight deterministic properties,
  each configured for 100 generated examples

Properties cover spot and strike monotonicity, discounted European bounds,
put-call parity, non-negative gamma and vega, identifiable implied-volatility
round trips, expiry intrinsic value, zero-volatility discounted intrinsic
value, and fail-closed invalid domains.

### Coverage.py 7.15.2

- `pyproject.toml`: exact development dependency and branch/source/report/JSON
  configuration
- `uv.lock`: Coverage.py artifacts and hashes
- `.gitignore`: only local generated coverage artifacts
- `.github/workflows/ci.yml`: one covered test invocation followed by the
  report gate; no duplicate full-suite run and no third-party upload
- `tests/test_coverage_configuration.py`: configuration contract, including
  the measured 79% floor

### QuantLib 1.43

- No files. No dependency. No lock change. No CI step.
- **BLOCKED** until the owner explicitly approves: `override C3 for test-only
  QuantLib validation without registering a new hypothesis`.

### Explicitly unchanged

- production modules under `options_researcher/`, `data/`, `research/`,
  `strategies/`, and `harness/`
- all ledgers, frozen caches, reports containing research results, portfolio
  state, hypothesis registrations, provider runtime configuration, and order
  paths
- the Equity Research repository

## Red/green and validation evidence

### Baseline

| Command or check | Exit | Result |
|---|---:|---|
| `uv run --frozen --offline ruff check .` | 0 | All checks passed; 1.21s. |
| `uv run --frozen --offline pyright` | 0 | 0 errors, warnings, or information; 18.71s. |
| Full suite without `LIVE_MARKET_DATA_PROVIDER` | 1 | 2,283 tests in 309.831s; 62 configuration errors from the explicit provider guard. Not used as authoritative baseline. |
| Full suite with provider setting inside the managed sandbox | 1 | 2,283 tests in 310.043s; only 8 loopback-bind permission errors. Not a code failure. |
| Full suite with `LIVE_MARKET_DATA_PROVIDER=schwab` and loopback permission | 0 | 2,283 tests in 292.001s; authoritative baseline. |
| Ephemeral Coverage.py 7.15.2 full run on untouched implementation | 0 | 2,283 tests in 255.659s. |

The explicit provider environment setting is required because the repository
fails closed when no supported live-data provider is named. The tests use fakes
and local fixtures; this setting did not authorize live acquisition or orders.

### Hypothesis TDD

| Check | Exit | Result |
|---|---:|---|
| Property module before dependency | 1 | Expected red: `No module named 'hypothesis'`. |
| First generated run | 1 | Found a low-vega IV identifiability edge; the test was corrected to exclude mathematically flat cases, with no production change. |
| Property suite | 0 | 8 tests in 1.231s, 100 deterministic examples per property. |
| Existing and generated Black-Scholes tests | 0 | 31 tests in 1.521s. |
| Focused Ruff | 0 | All checks passed. |
| Focused Pyright | 0 | 0 errors or warnings. |
| `uv lock --check` | 0 | 329 packages resolved consistently. |

### Coverage.py TDD and final root gates

| Check | Exit | Result |
|---|---:|---|
| Configuration contract before dependency/config | 1 | Expected red: 1 failure and 3 missing-configuration errors. |
| Configuration contract after implementation | 0 | 4 tests pass. |
| Complete integrated suite under coverage | 0 | 2,295 tests in 201.845s. |
| `coverage report --format=total` | 0 | Displays 79 and passes `fail_under = 79`. |
| Full Ruff | 0 | All checks passed. |
| Full Pyright | 0 | 0 errors, warnings, or information. |
| `git diff --check` | 0 | No whitespace errors. |

## Coverage before and after

| Metric | Untouched baseline | Integrated | Change |
|---|---:|---:|---:|
| Combined line+branch coverage | 79.299716% | 79.320496% | +0.020780 pp |
| Statement coverage | 82.581501% | 82.595716% | +0.014215 pp |
| Branch coverage | 70.386100% | 70.424710% | +0.038610 pp |
| Covered lines / statements | 17,428 / 21,104 | 17,431 / 21,104 | +3 covered lines |
| Covered / total branches | 5,469 / 7,770 | 5,472 / 7,770 | +3 covered branches |

**Scope caveat:** Coverage measures the explicitly named source packages and
omits tests, isolated tools, reports, results, and caches. The percentage is a
non-regression floor, not proof that every risk-bearing path is adequately
tested. Rounding the complete baseline down to 79 avoids inventing a higher
standard than the current repository can meet.

## Components, licensing, and free-use conclusion

| Component | Canonical sources | License | Cost and use conclusion |
|---|---|---|---|
| Hypothesis 6.164.0 | [GitHub](https://github.com/HypothesisWorks/hypothesis), [PyPI](https://pypi.org/project/hypothesis/6.164.0/) | MPL-2.0 | Free/open source and usable commercially. Used unmodified as a development dependency; no hosted service, telemetry, API key, or paid tier is required. |
| Coverage.py 7.15.2 | [GitHub](https://github.com/nedbat/coveragepy), [PyPI](https://pypi.org/project/coverage/7.15.2/) | Apache-2.0 | Free/open source and usable commercially. Runs locally and writes only ignored local artifacts; no hosted upload or paid tier is required. |
| QuantLib 1.43 | [GitHub](https://github.com/lballabio/QuantLib), [PyPI](https://pypi.org/project/QuantLib/1.43/) | BSD-3-Clause | Free/open source and commercially usable, but not installed because repository authorization is still blocked. |

**100% free constraint:** the software integrations require no payment and can
run entirely on the local machine. The CI edit reuses the repository's existing
GitHub Actions workflow and introduces no new vendor. GitHub-hosted compute can
be subject to an account's included-minute limits for private repositories; a
local or self-hosted runner preserves a no-new-cost path if that quota matters.

## Supply-chain and security evidence

### New dependencies

- **VERIFIED:** root direct dependencies added are only `hypothesis==6.164.0`
  and `coverage==7.15.2`, both in the development group.
- **VERIFIED:** Hypothesis adds `sortedcontainers==2.4.0`; Coverage.py adds no
  Python runtime dependency.
- **VERIFIED:** the lock records exact versions and artifact hashes.
- **OBSERVED:** installed metadata reports Hypothesis 6.164.0 with the
  `MPL-2.0` license expression. Coverage.py's installed metadata exposes the
  upstream homepage but no `License-Expression` field; the Apache-2.0 result
  comes from the reviewed upstream/PyPI project metadata.
- **OBSERVED:** neither Hypothesis nor Coverage.py appears in the vulnerability
  findings below.

### Audit limitations and findings

`pip-audit==2.10.1 --locked .` exits 1 with `no lockfiles found in .`; this
version does not recognize `uv.lock` in lockfile mode. That check is **BLOCKED**
by scanner capability, not reported as green.

The supported installed-environment scan,
`pip-audit --path .venv/lib/python3.12/site-packages`, exits 1 and reports 35
advisory rows across 9 packages:

| Existing package | Installed | Advisory rows | Fix information reported by scanner |
|---|---:|---:|---|
| aiohttp | 3.13.4 | 11 | 3.14.0 or 3.14.1, depending on advisory |
| click | 8.1.8 | 1 | 8.3.3 |
| langgraph | 0.4.7 | 2 | 1.0.10 / 1.0.10rc1 |
| litellm | 1.83.14 | 3 | 1.84.0 |
| nltk | 3.9.4 | 4 | 3.10.0 for three rows; one row has no fix listed |
| pyarrow | 21.0.0 | 1 | 23.0.1 |
| pyasn1 | 0.6.3 | 4 | 0.6.4 |
| setuptools | 80.10.2 | 2 | 83.0.0 |
| starlette | 0.52.1 | 7 | 1.0.1 through 1.3.1, depending on advisory |

Some rows are duplicate IDs from package metadata paths, but the scanner's
headline is preserved exactly. These packages and versions predate the two new
development dependencies; the branch changes only add Hypothesis,
sortedcontainers, and Coverage.py to the lock. Remediation requires a separate
dependency-impact task because several fixes may be constrained by large
transitive frameworks. No `--fix`, ignore rule, or unrelated upgrade was used.

## Adversarial review

- **False-positive risk:** generated floating-point examples use explicit
  tolerances. IV equality is asserted only where vega is meaningful; otherwise
  price cannot identify volatility reliably.
- **False-negative risk:** deterministic properties cover broad domains but do
  not replace independent American-option or discrete-dividend validation.
  That remaining gap is exactly why QuantLib was selected.
- **Determinism:** each property uses `derandomize=True`, `deadline=None`, and
  100 examples. No example database or network data is required.
- **CI correctness:** the full suite runs once under coverage and the following
  report command enforces the gate. No report is uploaded externally.
- **Provider boundary:** CI names the repository-required `schwab` provider for
  configuration validation only. Tests remain mocked/local. No secret or OAuth
  credential is added.
- **Native/runtime risk:** Hypothesis now ships a native wheel on supported
  targets; the lock also contains its source distribution. Coverage.py ships a
  C extension and a pure-Python wheel. Both have platform artifacts and hashes
  in `uv.lock`.
- **QuantLib global state:** no risk was introduced because QuantLib is absent.
  If later authorized, its global evaluation date must be serialized and
  restored in `finally`, and the isolated test environment must fail loudly on
  native-wheel problems.
- **Production behavior:** no production source changed. The work adds tests,
  development dependencies, local measurement configuration, and CI gates.

## Unsupported assumptions and remaining gaps

1. **BLOCKED:** no explicit owner override of the older QuantLib C3 trigger.
2. **OBSERVED:** the environment-wide vulnerability audit is red and needs a
   separately scoped compatibility/remediation pass.
3. **INFERRED:** GitHub Actions will permit the new coverage command wherever
   the existing workflow already runs. Account quota/cost is outside this repo;
   local execution remains free.
4. **ESTIMATED:** 100 examples per property balance speed and discovery. That
   number is not evidence of exhaustive numerical proof.
5. **BLOCKED:** Equity Research remains outside implementation because its own
   hard gate was red during preflight.

## Rollback

Run reversions from newest to oldest in a clean checkout. These commands create
recoverable revert commits and do not rewrite history.

### Coverage.py only

```bash
git revert 1b458532e1b45ae4f506bee8bedf695444015efe
```

This removes the CI coverage invocation, 79% gate, coverage configuration,
ignored artifacts, configuration test, and direct Coverage.py lock entry.

### Hypothesis only

```bash
git revert 8d67a9c
```

This removes the generated property suite and the Hypothesis/sortedcontainers
lock entries.

### Design and plan documents, if the entire initiative is abandoned

```bash
git revert a7ade0a
git revert 9dc5f62
```

### QuantLib

No rollback is needed because nothing was installed or changed.

## Recommendation-only weekly GitHub improvement scan

Do not auto-install repositories. Run a read-only weekly discovery pass, then
require explicit approval for every experiment. To guarantee no new software
bill, run it locally with existing Git/GitHub tooling and public repository
metadata; do not call paid enrichment, search, LLM, or market-data APIs.

### Portfolio lanes

1. **Kalshi weather trading bot:** weather/NWS ingestion, probabilistic
   calibration, forecast scoring, event-contract parsing, execution safety,
   settlement, and observability.
2. **Options Validator:** pricing/reference engines, point-in-time market-data
   quality, cost/slippage modeling, backtest correctness, property testing, and
   research governance.
3. **Equity Research:** SEC/EDGAR/XBRL ingestion, filing timelines, valuation,
   evidence citations, point-in-time fundamentals, and reproducible reports.
4. **Relationship-manager sales pipeline:** privacy-safe CRM, relationship
   graphs, lead qualification, workflow automation, email/calendar connectors,
   auditability, consent, and compliance.

### Weekly candidate gate

Every recommended repository must:

- map to a verified current-repo gap, not generic popularity;
- be compared with at least two alternatives, including “build nothing”;
- use a clear commercial-use license and require no paid API/service;
- show active maintenance, releases, tests, and supported runtimes;
- pass advisory, dependency, telemetry, credential, and data-egress review;
- fit as a small isolated experiment without rewriting production paths; and
- receive an accuracy/reliability/fit/effort/maintenance/security weighted
  score plus explicit **GO / HOLD / REJECT** reasoning.

Prefer MIT, BSD, Apache-2.0, and unmodified dependency use under MPL-2.0. Hold
copyleft or source-available licenses for legal/architecture review. Reject an
unclear license, required paid tier, abandoned project, undisclosed telemetry,
credential harvesting, critical unmitigated advisory, or proposed rewrite.

### Copy-paste weekly prompt

```text
Perform a read-only weekly GitHub improvement scan for these projects:
1) Kalshi weather bot, 2) Options Validator, 3) Equity Research, and
4) the relationship-manager sales pipeline.

Hard constraints:
- 100% free software and no required paid API/service.
- Commercial use must be permitted by a verified license.
- Do not install, edit, push, message anyone, or open a PR.
- Read each repo's AGENTS.md/CLAUDE.md, project state, current tests, recent
  commits, dependency files, and open blockers before recommending anything.
- Preserve trading, research-governance, credential, privacy, and owner-approval
  boundaries.

For each project:
1. State the top 3 verified current gaps with file/command evidence.
2. Search current GitHub repositories/releases that directly address those
   gaps; popularity alone is not evidence.
3. Compare the best candidate with at least two alternatives and doing nothing.
4. Verify license, commercial use, latest release, maintenance, runtime fit,
   dependencies, known advisories, telemetry/data egress, secrets required,
   and whether a paid tier is necessary.
5. Score 0-100 using accuracy/reliability 30, repo fit 25, implementation and
   rollback effort 15, maintenance 10, security/privacy 15, and truly-free use 5.
6. Recommend only a tiny isolated test experiment with success/failure metrics.

Output one concise weekly digest containing:
- project and verified gap;
- candidate URL/version/license;
- why it helps and what it cannot solve;
- free-use and security verdict;
- weighted score and GO/HOLD/REJECT;
- smallest reversible experiment;
- explicit approval needed before any change.

End with a cross-project shortlist of no more than 3 candidates for the week.
If no candidate clears the evidence and safety gates, recommend nothing.
```

### Suggested cadence

- Run once weekly, preferably before the weekly repo review.
- Compare only changes since the prior digest: new releases, advisories,
  archived projects, license changes, and new verified repo gaps.
- Keep a small rejection ledger so the same unsuitable popular repositories do
  not reappear every week without new evidence.
- Re-evaluate installed tools separately; discovery approval is never install
  approval.

No recurring automation was created in this task.

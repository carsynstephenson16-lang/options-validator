# Free GitHub Validation Integrations Design

**Date:** 2026-08-01

**Status:** owner-approved design

**Branch:** `optimization/github-integrations-20260801`

**Base:** `5167d3853a87c4f11b17a18e8c65d236afad91b3`

## 1. Objective

Add three free and open-source, test-only components that measurably improve
Options Validator correctness and validation visibility without changing live
research authority, provider access, cached evidence, ledgers, portfolio state,
or any trading path:

1. Hypothesis 6.164.0 for property-based boundary and invariant testing.
2. QuantLib 1.43 for an isolated independent pricing reference.
3. Coverage.py 7.15.2 for reproducible statement and branch coverage evidence.

The components are selected from the 2026-08-01 repository audit using the
required weighted model. They scored 95, 92, and 90 out of 100 respectively.

This work supports the live H5/H6/H7/H8 research program by strengthening the
mechanical evidence used to reject invalid calculations. It does not register a
new hypothesis, run a backtest, append a correction fact, promote a strategy,
or produce a research verdict. The open P0.6 owner-gated fact append remains
untouched.

## 2. Free-use and license gate

All selected components must remain usable without a subscription, API key,
hosted account, usage charge, or paid service:

| Component | Version | License | Use in this design | Required handling |
|---|---:|---|---|---|
| Hypothesis | 6.164.0 | MPL-2.0 | Test dependency | Keep upstream license metadata; do not modify or vendor its source. |
| QuantLib | 1.43 | BSD-3-Clause | Isolated validation dependency | Retain license and copyright notice in the isolated tool documentation. |
| Coverage.py | 7.15.2 | Apache-2.0 | Test/CI dependency | Retain upstream license/NOTICE metadata; do not redistribute a modified copy. |

Optional paid support advertised by an upstream does not become a project
dependency. The integration must fail review if any implementation step adds a
paid API, SaaS requirement, telemetry requirement, credential, or proprietary
runtime dependency.

## 3. Constraints

- Production dependencies and production pricing interfaces stay unchanged.
- No provider calls, downloads of market data, ledger writes, cache mutation,
  report verdicts, order routing, or live/paper execution are permitted.
- Tests use deterministic settings and bounded example counts.
- QuantLib never becomes the sole proof that the internal model is correct.
- The root environment must not gain QuantLib as a production dependency.
- Existing isolated vollib and FinancePy validation tools remain intact.
- Equity Research receives no tracked change while its documented Phase 0 hard
  gate is red. Reuse there is a future decision, not part of this branch.
- No generated coverage database or HTML report is committed.
- The existing P0/P1 sequence in `PROJECT_STATE.md` remains authoritative for
  research work; this branch is validation infrastructure only.

## 4. Architecture

### 4.1 Hypothesis property tests

Hypothesis belongs in a development dependency group, not `[project].dependencies`.
New tests exercise the existing offline modules directly and preserve the
standard unittest discovery path.

Initial properties cover:

- European call price is nondecreasing in spot and nonincreasing in strike.
- European put price is nonincreasing in spot and nondecreasing in strike.
- Call and put prices stay within their discounted no-arbitrage bounds.
- Put-call parity holds only under the documented European, continuous-yield,
  ACT/365 assumptions.
- Gamma and vega are nonnegative on the supported interior domain.
- Implied-volatility round trips recover the original volatility within a
  tolerance appropriate to the solver and input scale.
- Invalid, non-finite, expired, zero-volatility, deep-ITM, and deep-OTM inputs
  exercise explicit documented behavior.

Every property uses explicit finite ranges, a fixed CI profile, disabled
deadlines where timing is machine-sensitive, and deterministic reproduction
through Hypothesis's example database or printed falsifying example. No test
depends on network data or the mutable market cache.

### 4.2 Isolated QuantLib reference adapter

QuantLib lives under `tools/quantlib_validation/` as its own uv project with an
exact lock. The adapter accepts a small typed input record and returns a typed
result; it does not import into production modules.

The adapter explicitly records:

- valuation date and maturity date;
- option type and exercise style;
- spot, strike, volatility, risk-free rate, and dividend assumption;
- ACT/365 Fixed day count;
- continuous-yield versus discrete-cash-dividend treatment;
- selected engine and numerical grid/step settings; and
- the QuantLib version used.

Validation cases compare the internal European implementation with QuantLib's
analytic European engine and test American relationships with an American-
capable finite-difference engine. The tests check independent identities and
bounds in addition to library-to-library agreement.

QuantLib's global evaluation date is process-global. The adapter therefore:

1. serializes a validation call;
2. saves the previous evaluation date;
3. sets the declared valuation date;
4. performs the calculation; and
5. restores the previous value in a `finally` block.

The tool is not safe for shared multithreaded use and documents that limitation.
The CI command invokes it in a single process.

### 4.3 Coverage evidence

Coverage.py also belongs in the development dependency group. Configuration is
stored in `pyproject.toml` and measures project source rather than tests,
generated reports, caches, or isolated third-party environments.

The first measured full-suite run establishes the baseline. The implementation
must not invent a target or claim an improvement from static test counts. The
initial gate is set no higher than the reproducible measured baseline and is
intended to prevent regression. Branch coverage is reported separately from
statement coverage in a machine-readable JSON artifact.

The proposed commands are:

```text
uv run coverage erase
uv run coverage run --branch -m unittest discover -s tests
uv run coverage report --show-missing
uv run coverage json -o reports/validation/coverage.json
```

The report path is a CI artifact/output location and is ignored by Git. If the
full suite has known environment-dependent failures, the baseline records the
exact failure and a targeted offline subset is used only as additional evidence,
not presented as a full-suite result.

## 5. Dependency and supply-chain controls

- Pin the selected direct versions and update `uv.lock` deterministically.
- Inspect the resolved lock diff for unrelated upgrades before committing.
- Install only from PyPI through uv; no curl-pipe-shell, package post-install
  command, browser download, or elevated installer is allowed.
- Hypothesis 6.164.0 includes a Rust native extension built by Maturin. Prefer
  the official wheel selected and hashed by the uv lock; do not build from an
  unreviewed source checkout in CI.
- QuantLib is a compiled C++ wheel. The isolated lock and smoke test must prove
  the expected macOS ARM64 and CI Linux wheel paths. No runtime network access
  is permitted.
- Coverage.py may use its C tracer wheel; its documented Python tracer fallback
  does not justify silently accepting a failed or unexpected build.
- Run a read-only dependency audit during final validation. Do not use an
  automatic `--fix` mode and do not suppress advisories without a documented,
  reviewed rationale.

## 6. Error handling

- Property tests fail with the minimized counterexample and declared seed or
  reproduction blob.
- QuantLib adapter input validation rejects unsupported styles, non-finite
  values, invalid date ordering, nonpositive spot/strike, and invalid grids
  before entering native code.
- QuantLib calculation errors retain the engine, assumptions, and original
  exception without returning success-shaped results.
- A missing optional validation environment is reported as an installation
  failure, not as a passed validation.
- Coverage collection and reporting failures propagate nonzero exit codes.

## 7. Test strategy and definition of done

The work is complete only when all of the following are true:

1. A failing test is demonstrated before each meaningful implementation change.
2. Hypothesis properties pass under the pinned version and standard unittest
   discovery.
3. QuantLib comparison, American-bound, early-exercise, dividend-sensitivity,
   invalid-input, and state-restoration tests pass in the isolated environment.
4. Coverage produces statement and branch totals plus JSON output from the
   declared test command.
5. Existing ruff and pyright gates pass through the repository's uv toolchain.
6. The full existing test command is run and all outcomes are separated into
   pre-existing, introduced, and environment-blocked results.
7. No provider, cache, ledger, portfolio, research-verdict, or order path is
   touched.
8. Each integration is a separate reversible commit.
9. License, security, unsupported assumptions, and exact rollback commands are
   included in the final audit report.

## 8. Rollout and rollback

Implementation order follows the weighted ranking:

1. Hypothesis property tests.
2. QuantLib isolated reference validation.
3. Coverage measurement and regression gate.

Rollback is commit-scoped. Reverting the relevant commit removes the associated
test dependency, isolated tool, or coverage gate without changing production
pricing behavior. No database or data migration is involved.

## 9. Rejected approaches

- Replacing the internal pricer with QuantLib: too much production behavior and
  global-state risk for a validation objective.
- Loading QuantLib in normal scanner/dashboard paths: violates the isolation
  boundary and makes native availability operationally significant.
- FinancePy as the selected oracle: already present and GPL-isolated; selecting
  it again would duplicate existing work and complicate commercial distribution.
- Vollib as the selected oracle: useful for European parity but does not close
  the verified American-exercise gap.
- SlipCover instead of Coverage.py: attractive performance, but the mature
  reporting, subprocess, and CI behavior of Coverage.py is a better fit for the
  current reproducibility gap.
- A paid hosted code-quality or financial-model service: conflicts with the
  explicit free-only requirement and increases replacement risk.

## 10. Deferred cross-repository opportunity

After this implementation is validated, a separate owner-approved workflow may
scan current GitHub releases each week and map candidates to verified gaps in
the owner's Kalshi weather bot, Options Validator, Equity Research, and future
relationship-manager sales-pipeline repositories. That workflow must remain
recommendation-only by default, verify license and maintenance evidence, and
never install or modify a repository automatically.

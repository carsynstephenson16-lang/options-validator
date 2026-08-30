# Domain 2 — Tests and Reliability Audit

**Audit basis:** frozen `c9e74ccd05e4ecdd0de8de6f35bef714bc6f1771`; read-only review. No
provider, paper, cache, ledger, receipt, source, or test mutation was performed.

## Verdict

**NOT READY as a reliable, portable verification gate.** The core suite has broad
offline and fail-closed coverage, but the supplied full-suite runs cannot currently
distinguish a product regression from a host process-exhaustion failure. CI also
does not exercise the macOS/zsh operational surface or the independent `repo-rag`
tool test suite.

## Evidence reviewed

- **Verified:** `tests/` has 194 `test_*.py` files and 3,821 `def test_` / test-class
  declarations. Large risk-bearing modules have substantial focused suites, e.g.
  `tests/test_attractiveness_dashboard.py` (2,681 lines),
  `tests/test_h7_exit_session.py` (1,894), `tests/test_intraday_capture.py` (1,642),
  and `tests/test_research_integrity.py` (1,289).
- **Verified:** the primary CI job pins Python 3.12, syncs the lock, runs Ruff,
  Pyright, branch coverage plus root `tests/`, coverage report, and the isolated
  QuantLib suite ([`.github/workflows/ci.yml:15-48`](../../../../.github/workflows/ci.yml)).
  `pyproject.toml` enables branch coverage over the five core packages and sets a
  79% fail-under gate; its contract is itself tested in
  [`tests/test_coverage_configuration.py:26-51`](../../../../tests/test_coverage_configuration.py).
- **Verified:** provider-facing tests mostly use explicit barriers and mocks rather
  than real clients: `tests/test_blind_cache.py:76-118` replaces both the publisher
  guard and client/fetch seam, while `tests/test_provider_disabled.py` asserts
  refusal before client construction. This is good counterevidence to a claim that
  the reported full suite performed provider operations.
- **Supplied baseline evidence (not independently rerun):** first full coverage
  run: 3,229 tests, 2 environment failures, 5 skips. After a shared `.venv`
  symlink and canonical `TMPDIR`, another run reached 3,229 tests but ended with
  7 failures and 4 errors attributed to macOS `Resource temporarily unavailable`
  fork failures; the initial two targeted tests passed.
- **Verified current host counterevidence/root-cause evidence:** `launchctl limit
  maxproc` reports a per-user soft limit of 1,333 (hard 2,000), while the current
  user process count was 1,280. Of those, 797 were zombies parented by the external
  `FwUpdateManagerd` PID 2842 (not this repository). This leaves little process
  headroom and directly explains why otherwise ordinary `fork`/subprocess creation
  can return `EAGAIN`; it does **not** evidence an options-validator product
  regression.

## Findings

### P1 — Process-starved macOS runs produce non-actionable test failures

**Status: Verified.** The suite contains a real cross-process regression test:
`BlindCacheTests.test_two_process_publishers_leave_one_canonical_fact_and_hash`
unconditionally selects `multiprocessing.get_context("fork")`, starts two child
processes, then waits up to 15 seconds each
([`tests/test_blind_cache.py:203-230`](../../../../tests/test_blind_cache.py)).
The same suite has numerous `subprocess.run` integration contracts. In the observed
host state, the per-user process budget has only roughly 53 slots before accounting
for concurrent work; 797 unreaped external zombies consume most of it. The supplied
`Resource temporarily unavailable` failures are consequently consistent with host
process exhaustion.

This is **not** evidence that the publisher lock is wrong: the target test's
assertions are valuable and its child target uses a temporary cache/ledger path plus
mocked acquisition (`tests/test_blind_cache.py:42-73`). It is instead a reliability
and diagnostics gap: the default `unittest` invocation does not preflight/report
process headroom, distinguish `EAGAIN` from a contract failure, or preserve a
machine-readable test report.

**Plan-only remediation:** before a full local suite, add a read-only process-budget
preflight that fails loudly with current/limit/zombie counts and a rerun instruction.
Keep the two-process correctness test mandatory when capacity exists; do not silently
skip it. Add a controlled CI/local diagnostic that records the exact failed test and
`OSError.errno`, then rerun that one test only after host capacity is restored.

### P1 — CI does not validate the macOS/zsh operational surface

**Status: Verified.** The sole quality runner is `ubuntu-latest`
([`.github/workflows/ci.yml:13-16`](../../../../.github/workflows/ci.yml)).
`ResearchDisplayRefreshTests` is explicitly skipped when `/bin/zsh` is absent and
labels its wrapper macOS/zsh-only
([`tests/test_research_display_refresh.py:12-16`](../../../../tests/test_research_display_refresh.py));
the test invokes the actual zsh wrapper using fake executables
([`tests/test_research_display_refresh.py:51-76`](../../../../tests/test_research_display_refresh.py)).
Other wrapper suites have the same runtime `zsh` skips (`test_daily_ritual_provenance`,
`test_schwab_chain_schedule`, `test_ops_alignment_check`, and
`test_research_context_assemble`).

Therefore a green Ubuntu CI run cannot establish that the launchd/zsh contracts used
on the owner’s macOS environment execute correctly. This is an execution-platform
gap, not a claim that these wrappers are currently broken.

**Plan-only remediation:** provide a macOS runner (self-hosted or managed) that runs
the existing mock-only zsh-wrapper tests with network/provider execution explicitly
disabled. Publish platform and skipped-test counts in the CI summary; retain Ubuntu
as the main fast gate.

### P2 — Two tracked verification surfaces are outside the principal CI contract

**Status: Verified.** `tools/repo_rag` is an independent, tracked read-only
application with its own Python project (`tools/repo_rag/pyproject.toml:1-16`) and
11 `tools/repo_rag/tests/test_*.py` files. Root CI runs root `tests/` and the
one-file QuantLib suite only
([`.github/workflows/ci.yml:37-48`](../../../../.github/workflows/ci.yml)); it
does not sync or run `tools/repo_rag` tests. In addition, CI runs `ruff check` but
not the repository-required formatting check (`uv run ruff format --check .`).

**Plan-only remediation:** decide whether `repo-rag` is supported production
operational code. If yes, add a separate locked-project test/lint job and a root
format check. If no, explicitly mark it out of release scope and test it through a
named manual/launchd validation procedure. Either choice is better than the current
implicit gap.

### P2 — Coverage evidence is gated but not retained, and cache-backed integration is optional

**Status: Verified.** CI runs `coverage report` only; despite a configured local
`coverage.json` output, it neither generates that JSON nor uploads coverage or
JUnit-style diagnostics ([`.github/workflows/ci.yml:37-43`](../../../../.github/workflows/ci.yml),
[`tests/test_coverage_configuration.py:47-51`](../../../../tests/test_coverage_configuration.py)).
The primary README quickstart likewise only advertises the plain unittest command
([`README.md:78-85`](../../../../README.md)). This makes a CI failure harder to
triage and makes local verification non-parallel with CI.

**Verified:** selected cache-backed integration assertions intentionally skip when
the local immutable cache is unavailable, for example
`test_real_cache_board_has_at_least_one_unblocked_name_when_available`
([`tests/test_exp_tbill_carry.py:287-295`](../../../../tests/test_exp_tbill_carry.py))
and the 60-session replay in
[`tests/test_exp_spread_stability.py:247-273`](../../../../tests/test_exp_spread_stability.py)).
This preserves portability and protects evidence, but leaves an **Unknown**: whether
the full real-cache integration subset passes at this frozen SHA on a sanctioned
data-bearing worktree.

**Plan-only remediation:** make a `coverage json`/XML artifact and test-result
artifact available on failure, document the CI-equivalent command, and define a
separate read-only, cache-mounted integration lane with a manifest preflight. Do not
make developer or PR tests depend on mutable/provider data.

## Strengths and counterevidence

- **Verified:** tests deliberately prove refusal paths before network/client or
  mutation seams (`tests/test_provider_disabled.py`; `tests/test_blind_cache.py:101-118`).
- **Verified:** temporary directories and cleanup are used broadly; the blind-cache
  test restores module globals in `tearDown` (`tests/test_blind_cache.py:106-112`).
- **Verified:** the root project tests are serial `unittest` discovery, so this audit
  found no evidence of intra-suite parallel execution racing ordinary shared globals.
  The process problem is external host saturation plus explicitly spawned child/
  shell tests.
- **Inferred:** the many cross-test imports such as `from test_qm_signals import ...`
  couple tests to `unittest discover -s tests` path behavior. The documented command
  is correct, but targeted dotted-module invocation is less portable. No failure was
  reproduced, so this is not elevated beyond an observation.

## Coverage and validation status

| Area | Status |
|---|---|
| Root unittest/coverage gate | **Blocked** — supplied attempts reached 3,229 tests but host fork exhaustion invalidates a product-level pass/fail conclusion. |
| Coverage threshold | **Verified configured** at branch coverage >=79%; **Unknown measured result** for this frozen audit because no clean full run completed. |
| CI quality gate | **Verified** lint, types, root coverage, and QuantLib invocation exist on Ubuntu. |
| macOS/zsh wrapper verification | **Gap verified** — no macOS CI lane. |
| `tools/repo_rag` verification | **Gap verified** — 11 test files not invoked by root CI. |
| Provider/live/paper safety during this audit | **Verified audit-safe** — no such operation was run; reviewed tests use mocks/refusal seams. |

## Remaining risks / unsupported assumptions

- **Unknown:** the exact identities of all 7 failures and 4 errors from the supplied
  second full run were not preserved in a readable test artifact; they cannot be
  attributed one-by-one without a clean-capacity rerun.
- **Unknown:** branch-coverage percentage and cache-mounted integration behavior at
  this SHA; the audit intentionally did not use protected caches or run providers.
- **Inference:** resolving the external `FwUpdateManagerd` zombie accumulation, or
  otherwise restoring process capacity, should permit a meaningful targeted/full
  retry. That is an OS/operator action outside repository authority.

## Final ready decision

**Not ready** for a claim that verification is reproducible across the supported
macOS operational environment. The next safe step is host process-capacity recovery,
then a diagnostic full root coverage run plus the cache-mounted integration lane;
implementation changes should remain plan-only because protected WIP overlaps the
test/source surface.

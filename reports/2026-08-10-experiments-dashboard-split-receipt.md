# Experiments dashboard split receipt

Date: 2026-08-10
Branch: `codex/experiments-dashboard-split`
Worktree: `.tmp/worktrees/experiments-dashboard-split`
Base: `d6ed665` (`origin/main` after the prerequisite ops-failure-classification merge)
Implementation commit: `09d2344`
Environment: offline; `.cache` was absent before the baseline and artifact builds.

## Sequencing and scope

- `origin` was fetched before reading the required project instructions and
  briefs.
- The fetched `origin/main` first-parent history already contains
  `0964e81` (`codex/ops-failure-classification`) via merge `d6ed665`; the
  prerequisite was therefore already merged and was not repeated.
- Exactly these six files are in scope for this task:
  `config.py`,
  `options_researcher/attractiveness_dashboard.py`,
  `options_researcher/experiments_dashboard.py`,
  `tests/test_experiments_baseline.py`,
  `tests/test_experiments_dashboard.py`, and this receipt.
- No provider, network, ledger, paper-book, ops-checkout, or research-checkout
  writes were performed.

## RED evidence — captured before the implementation

### Production reference guard

The source-reference assertion was run against a temporary local marker
mutation, then the marker was removed. Literal output:

```text
test_production_dashboard_has_no_experiment_references (test_experiments_baseline.ExperimentBaselineTests.test_production_dashboard_has_no_experiment_references) ... FAIL

======================================================================
FAIL: test_production_dashboard_has_no_experiment_references (test_experiments_baseline.ExperimentBaselineTests.test_production_dashboard_has_no_experiment_references)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/experiments-dashboard-split/tests/test_experiments_baseline.py", line 66, in test_production_dashboard_has_no_experiment_references
    self.fail("production dashboard still contains experiment markers")
AssertionError: production dashboard still contains experiment markers

----------------------------------------------------------------------
Ran 4 tests in 4.423s

FAILED (failures=1)
RED_CONCISE_RC=1
```

The original pre-implementation run also failed the AST import guard with
`AssertionError: True is not false` naming the four `options_researcher.exp_*`
imports. The temporary marker was reverted before the green implementation
run.

### New artifact module

Before `options_researcher/experiments_dashboard.py` existed, the literal
focused run failed as follows:

```text
test_experiments_dashboard (unittest.loader._FailedTest.test_experiments_dashboard) ... ERROR

======================================================================
ERROR: test_experiments_dashboard (unittest.loader._FailedTest.test_experiments_dashboard)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_experiments_dashboard
Traceback (most recent call last):
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/loader.py", line 396, in _find_test_path
    module = self._get_module_from_name(name)
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/loader.py", line 339, in _find_test_path
    __import__(name)
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/experiments-dashboard-split/tests/test_experiments_dashboard.py", line 12, in <module>
    from options_researcher import experiments_dashboard as dashboard
ImportError: cannot import name 'experiments_dashboard' from 'options_researcher' (/Users/carsynstephenson/options-validator/.tmp/worktrees/experiments-dashboard-split/options_researcher/__init__.py)

----------------------------------------------------------------------
Ran 1 test in 0.000s

FAILED (errors=1)
```

## Changes

- `config.py`: removed the dead `EXPERIMENT_LANES_ENABLED` gate and added the
  owner-directed `EXPERIMENTS_OUTPUT_PATH`.
- `options_researcher/attractiveness_dashboard.py`: removed all experiment
  keywords, payload pass-through, renderer, CLI flag, and builder imports.
  Its no-argument path remains the original production artifact path.
- `options_researcher/experiments_dashboard.py`: added the independent entry
  point, copied display/refusal/health rendering, self-contained status CSS,
  all-four-lane invocation, atomic HTML write, and per-lane build/render
  quarantine into escaped ERROR cards.
- `tests/test_experiments_baseline.py`: replaced the mock-target guard with
  source/AST boundary guards, retained the fresh no-args subprocess check,
  removed obsolete embed/flag tests, and kept the config drift check.
- `tests/test_experiments_dashboard.py`: added empty-cache subprocess,
  quarantine, self-containment, health, and refusal-copy tests.

Deleted-test inventory:

- `test_default_path_never_invokes_experiment_builders` → replaced by the
  AST import-boundary test; this retires mock-target fragility.
- `test_default_path_html_has_zero_experiment_markers` → redundant injected
  fixture; the literal no-args subprocess test remains the authoritative
  production check.
- `test_experiment_lane_flags_default_false` → no replacement; the flags were
  deliberately deleted with the old embed path.
- `test_main_no_args_keeps_experiments_out_of_production_entry_point` → no
  replacement; the production module is now reference-free and the subprocess
  HTML test remains.
- The `--experiments` half of
  `test_module_entry_no_args_matches_production_command` → replaced by the
  standalone artifact subprocess test.
- `test_cli_builds_only_enabled_lanes_unless_force_all` → replaced by the
  explicit all-four-lane invocation and quarantine test.
- The old `ExperimentDashboardTests` renderer tests → moved to the new
  artifact test module, including health/refusal and CSS coverage.

## Byte-identity gate

Pre-edit base build, empty cache:

```text
wrote .../.tmp/dashboard/attractiveness.html
dc6274eace3e77986f558e00f5e255e3e4d4618ad9fce1994e61458dc4905318  .tmp/dashboard/attractiveness.html
105961
0
```

Post-strip HEAD build, same empty-cache fixture state:

```text
wrote .../.tmp/dashboard/attractiveness.html
dc6274eace3e77986f558e00f5e255e3e4d4618ad9fce1994e61458dc4905318  .tmp/dashboard/attractiveness.html
105961
0
```

The hard gate passed: the hashes and byte counts are equal and the default
HTML contains zero experiment markers.

## Green and final verification

- Focused baseline: `Ran 4 tests ... OK`.
- Focused standalone artifact: `Ran 4 tests ... OK`.
- Full offline suite, after granting only loopback bind permission required by
  unchanged `test_live_dashboard`: `Ran 2645 tests in 137.679s`; `OK
  (skipped=5)`; exit code 0.
- The unprivileged full-suite attempt reached all tests but had eight unchanged
  `PermissionError: [Errno 1] Operation not permitted` localhost-bind errors;
  no changed-scope test failed.
- `uv run ruff check .`: `All checks passed!`.
- `uv run pyright`: `0 errors, 0 warnings, 0 informations`.
- `git diff --check`: clean.
- Repository-wide `ruff format --check .` remains a pre-existing baseline
  failure (`274 files would be reformatted, 114 files already formatted`); the
  two new files were formatted individually, and no unrelated files were
  reformatted.

## Offline artifact evidence

Production command:

```text
python -m options_researcher.attractiveness_dashboard
wrote .../.tmp/dashboard/attractiveness.html
SHA-256 dc6274eace3e77986f558e00f5e255e3e4d4618ad9fce1994e61458dc4905318
105961 bytes; 0 experiment markers
```

Standalone command:

```text
python -m options_researcher.experiments_dashboard
wrote .../.tmp/dashboard/experiments.html
37606 bytes
EXP-BETA, EXP-TAIL, EXP-SPREAD, EXP-TBILL headings present
max as-of occurrences: 7
DATA BLOCKED occurrences: 72
status CSS present: True
production stylesheet link present: False
```

Quoted rendered evidence:

```html
<p>display-only research experiments — not part of Top-3 ranking, no verdict authority.</p>
<div class="label">Build max as-of 2026-08-10</div>
<div class="eyebrow">EXP-BETA</div>
<div class="eyebrow">EXP-TAIL</div>
<div class="eyebrow">EXP-SPREAD</div>
<div class="eyebrow">EXP-TBILL</div>
DATA BLOCKED as of 2026-08-10: benchmark QQQ load failed (FileNotFoundError: ...QQQ.parquet...).
```

Deliberate in-memory beta-builder mutation, automatically reverted by the
mock context, rendered this escaped ERROR card while the other lane headings
remained present:

```html
MUTATION_REVERTED_IN_MEMORY=True
<div class="eyebrow">EXP-BETA</div><div class="card-grid"><div class="panel composite-card"><div class="slot-label"><span>ALL</span><span class="status-badge bad">ERROR</span></div><div>RuntimeError: synthetic beta failure &lt;unsafe&gt; As of 2026-08-10. This lane failed; the other display-only lanes were still rendered.</div></div></div>
```

## Commits and deviations

- Base: `d6ed665`.
- Implementation/tests: `09d2344`.
- Receipt commit: recorded by the final Git handoff after this file is
  committed.
- Branch merge commit: recorded after the authorized `--no-ff` merge.
- Deviations: none in implementation scope. The only validation
  accommodations were reusing the already-installed local `.venv` in offline
  mode, granting loopback permission for eight unchanged server tests, and
  declining the repository-wide pre-existing format churn.

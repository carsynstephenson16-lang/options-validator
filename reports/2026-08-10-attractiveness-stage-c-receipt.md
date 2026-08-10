# Attractiveness experiment Stage C receipt (2026-08-10)

Base: `1fe816981c57c1e1af2f9dbc92c3a2cc96e85e2e`

Branch: `codex/attractive-exp-hardening`

Worktree: `.tmp/worktrees/attractive-exp-hardening`

Environment: offline; `.cache/` contained no files before the baseline or red runs.

## RED evidence

### Display badge state classes and generic assignment caveat

Command:

```text
uv run python -m unittest discover -s tests -p 'test_experiments_baseline.py' -v
```

Literal failing output (exit code 1):

```text
test_experiment_badge_classes_reflect_state (test_experiments_baseline.ExperimentDashboardTests.test_experiment_badge_classes_reflect_state) ... FAIL
test_tbill_line_exposes_unknown_assignment_reason (test_experiments_baseline.ExperimentDashboardTests.test_tbill_line_exposes_unknown_assignment_reason) ... FAIL

======================================================================
FAIL: test_experiment_badge_classes_reflect_state (test_experiments_baseline.ExperimentDashboardTests.test_experiment_badge_classes_reflect_state)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 294, in test_experiment_badge_classes_reflect_state
    self.assertIn('class="status-badge good">OK</span>', lane_html)
AssertionError: 'class="status-badge good">OK</span>' not found in '<div class="eyebrow">EXP-BETA</div><div class="card-grid"><div class="panel composite-card"><div class="slot-label"><span>MSFT</span><span class="status-badge unknown">OK</span></div><div>OK As of 2026-08-03. Descriptive history, not a forecast.</div></div><div class="panel composite-card"><div class="slot-label"><span>CEG</span><span class="status-badge unknown">DATA_BLOCKED</span></div><div>DATA BLOCKED as of 2026-08-03: missing cached data. As of 2026-08-03. Descriptive history, not a forecast.</div></div><div class="panel composite-card"><div class="slot-label"><span>VST</span><span class="status-badge unknown">UNSTABLE</span></div><div>UNSTABLE As of 2026-08-03. Descriptive history, not a forecast.</div></div></div>'

======================================================================
FAIL: test_tbill_line_exposes_unknown_assignment_reason (test_experiments_baseline.ExperimentDashboardTests.test_tbill_line_exposes_unknown_assignment_reason)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 425, in test_tbill_line_exposes_unknown_assignment_reason
    self.assertIn("Early-assignment risk caveat: SOME_FUTURE_REASON.", line)
AssertionError: 'Early-assignment risk caveat: SOME_FUTURE_REASON.' not found in '$18,400 collateral; put credit yield 7.0%/yr vs T-bills 4.9%/yr (carry spread +2.1%/yr; quote mid, real fills are mid or worse). Treasury rate source: treasury.gov capture 2026-07-27 As of 2026-07-27. Display-only comparison.'

----------------------------------------------------------------------
Ran 11 tests in 11.588s

FAILED (failures=2)
```

### Default path builder guard

An intentional local mutation made `main()` call the experiment payload
builders on its default path. The mutation was not retained.

Command:

```text
uv run python -c 'import sys, unittest; sys.path.insert(0, "tests"); suite=unittest.defaultTestLoader.loadTestsFromName("ExperimentBaselineTests.test_default_path_never_invokes_experiment_builders", __import__("test_experiments_baseline")); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
```

Literal failing output (exit code 1):

```text
test_default_path_never_invokes_experiment_builders (test_experiments_baseline.ExperimentBaselineTests.test_default_path_never_invokes_experiment_builders) ... FAIL

======================================================================
FAIL: test_default_path_never_invokes_experiment_builders (test_experiments_baseline.ExperimentBaselineTests.test_default_path_never_invokes_experiment_builders)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 107, in test_default_path_never_invokes_experiment_builders
    self._run_mocked_main(output)
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 83, in _run_mocked_main
    dashboard.main()
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/options_researcher/attractiveness_dashboard.py", line 3272, in main
    assemble_kwargs = _cli_experiment_payloads(force_all=True)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/options_researcher/attractiveness_dashboard.py", line 3251, in _cli_experiment_payloads
    payloads["exp_beta"] = build_exp_beta_board(symbols, asof=asof)
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1198, in _execute_mock_call
    raise effect
AssertionError: experiment builder invoked on default path

----------------------------------------------------------------------
Ran 1 test in 2.578s

FAILED (failures=1)
```

### Default path zero-marker guard

The same intentional local mutation injected experiment payloads into the
default `main()` path. The mutation was not retained.

Command:

```text
uv run python -c 'import sys, unittest; sys.path.insert(0, "tests"); suite=unittest.defaultTestLoader.loadTestsFromName("ExperimentBaselineTests.test_default_path_html_has_zero_experiment_markers", __import__("test_experiments_baseline")); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
```

Literal failing output (exit code 1):

```text
test_default_path_html_has_zero_experiment_markers (test_experiments_baseline.ExperimentBaselineTests.test_default_path_html_has_zero_experiment_markers) ... FAIL

======================================================================
FAIL: test_default_path_html_has_zero_experiment_markers (test_experiments_baseline.ExperimentBaselineTests.test_default_path_html_has_zero_experiment_markers)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 117, in test_default_path_html_has_zero_experiment_markers
    self.assertEqual(html.lower().count("experiment"), 0)
AssertionError: 2 != 0

----------------------------------------------------------------------
Ran 1 test in 3.351s

FAILED (failures=1)
```

### Literal module entry-point guard

An intentional local mutation made the `if __name__ == "__main__"` block
force all experiment lanes even without `--experiments`. The mutation was not
retained. The test uses the literal production argv shape and temporarily
backs up/restores the gitignored `.tmp/dashboard/attractiveness.html` output.

Command:

```text
uv run python -c 'import sys, unittest; sys.path.insert(0, "tests"); suite=unittest.defaultTestLoader.loadTestsFromName("ExperimentBaselineTests.test_module_entry_no_args_matches_production_command", __import__("test_experiments_baseline")); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
```

Literal failing output (exit code 1):

```text
test_module_entry_no_args_matches_production_command (test_experiments_baseline.ExperimentBaselineTests.test_module_entry_no_args_matches_production_command) ... FAIL

======================================================================
FAIL: test_module_entry_no_args_matches_production_command (test_experiments_baseline.ExperimentBaselineTests.test_module_entry_no_args_matches_production_command)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 166, in test_module_entry_no_args_matches_production_command
    self.assertEqual(baseline_html.lower().count("experiment"), 0)
AssertionError: 2 != 0

----------------------------------------------------------------------
Ran 1 test in 4.047s

FAILED (failures=1)
```

### Derived config-membership sentinel

As required by the brief, `EXP_TEST_SENTINEL = 1` was temporarily added to
`config.py`, the derived-membership test was run, and the sentinel was then
removed. It is not part of the final diff.

Command:

```text
uv run python -c 'import sys, unittest; sys.path.insert(0, "tests"); suite=unittest.defaultTestLoader.loadTestsFromName("ExperimentBaselineTests.test_config_matches_every_module_frozen_default", __import__("test_experiments_baseline")); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
```

Literal failing output (exit code 1):

```text
test_config_matches_every_module_frozen_default (test_experiments_baseline.ExperimentBaselineTests.test_config_matches_every_module_frozen_default) ... FAIL

======================================================================
FAIL: test_config_matches_every_module_frozen_default (test_experiments_baseline.ExperimentBaselineTests.test_config_matches_every_module_frozen_default)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/tests/test_experiments_baseline.py", line 215, in test_config_matches_every_module_frozen_default
    self.assertEqual(source_names, config_names)
AssertionError: Items in the second set but not the first:
'EXP_TEST_SENTINEL'

----------------------------------------------------------------------
Ran 1 test in 0.007s

FAILED (failures=1)
```

## GREEN and Stage C verification

### Focused hardening suite

Command:

```text
uv run python -m unittest discover -s tests -p 'test_experiments_baseline.py' -v
```

Literal output excerpt (exit code 0):

```text
test_config_matches_every_module_frozen_default (test_experiments_baseline.ExperimentBaselineTests.test_config_matches_every_module_frozen_default) ... ok
test_default_path_html_has_zero_experiment_markers (test_experiments_baseline.ExperimentBaselineTests.test_default_path_html_has_zero_experiment_markers) ... ok
test_default_path_never_invokes_experiment_builders (test_experiments_baseline.ExperimentBaselineTests.test_default_path_never_invokes_experiment_builders) ... ok
test_module_entry_no_args_matches_production_command (test_experiments_baseline.ExperimentBaselineTests.test_module_entry_no_args_matches_production_command) ... ok
test_experiment_badge_classes_reflect_state (test_experiments_baseline.ExperimentDashboardTests.test_experiment_badge_classes_reflect_state) ... ok
test_tbill_line_exposes_unknown_assignment_reason (test_experiments_baseline.ExperimentDashboardTests.test_tbill_line_exposes_unknown_assignment_reason) ... ok

----------------------------------------------------------------------
Ran 11 tests in 9.422s

OK
```

### Full suite

The first sandboxed run reached all tests but exited 1 because the sandbox
denied eight localhost binds in `test_live_dashboard` (`PermissionError:
[Errno 1] Operation not permitted`). No test in the changed scope failed. The
same offline command was rerun with localhost-bind permission; no test was
skipped or weakened.

Command:

```text
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache MPLCONFIGDIR=/private/tmp/options-validator-mpl uv run python -m unittest discover -s tests
```

Literal successful output excerpt (exit code 0):

```text
----------------------------------------------------------------------
Ran 2643 tests in 176.650s

OK (skipped=5)
```

The Stage-B review baseline was 2,639 tests. This task added four tests, so
2,643 is the expected final count.

### Experiment suite and glob trap

Command:

```text
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run python -m unittest discover -s tests -p 'test_exp*'
```

Literal output excerpt (exit code 0):

```text
----------------------------------------------------------------------
Ran 60 tests in 19.880s

OK (skipped=5)
```

The narrower natural-looking glob is intentionally documented separately:

```text
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run python -m unittest discover -s tests -p 'test_experiments*'
```

Literal output excerpt (exit code 0):

```text
----------------------------------------------------------------------
Ran 11 tests in 18.219s

OK
```

### Static verification

Commands and literal outputs:

```text
$ UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run ruff check .
All checks passed!
exit code 0

$ UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run pyright
0 errors, 0 warnings, 0 informations
exit code 0

$ git diff --check
exit code 0
```

### Offline dashboard build without experiments

Command:

```text
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run python -m options_researcher.attractiveness_dashboard
```

Literal build and HTML inspection output (exit code 0):

```text
wrote /Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/.tmp/dashboard/attractiveness.html
  105961 .tmp/dashboard/attractiveness.html
$ grep -ci experiment .tmp/dashboard/attractiveness.html
0
<h1>Which options look attractive today?
<strong>Market close</strong> no cached data
```

The zero count is the no-args HTML evidence; there is no experiment snippet
to quote because the required marker count is exactly zero.

### Offline dashboard build with experiments

Command:

```text
UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run python -m options_researcher.attractiveness_dashboard --experiments
```

Literal build and HTML inspection output (exit code 0):

```text
wrote /Users/carsynstephenson/options-validator/.tmp/worktrees/attractive-exp-hardening/.tmp/dashboard/attractiveness.html
  140584 .tmp/dashboard/attractiveness.html
$ grep -ci experiment .tmp/dashboard/attractiveness.html
1
<h2>Experiments — display-only (not part of Top-3 ranking)</h2>
EXP-BETA max as-of 2026-08-10
EXP-TAIL max as-of 2026-08-10
EXP-SPREAD max as-of 2026-08-10
EXP-TBILL max as-of 2026-08-10
Blocked: benchmark QQQ load failed (FileNotFoundError: [Errno 2] No such file or directory: &#x27;.cache/underlying/QQQ.parquet&#x27;)
DATA BLOCKED as of 2026-08-10: benchmark QQQ load failed (FileNotFoundError: [Errno 2] No such file or directory: &#x27;.cache/underlying/QQQ.parquet&#x27;). As of 2026-08-10. Betas drift toward 1 in sharp selloffs; a calm-period beta understates crash co-movement. Descriptive history, not a forecast.
```

Both builds used an empty `.cache/`. The blocked lines are expected
fail-visible cache refusals, not provider/network errors.

### Final flags

Command and literal output (exit code 0):

```text
$ UV_CACHE_DIR=/private/tmp/options-validator-uv-cache uv run python -c 'import config; print(config.EXPERIMENT_LANES_ENABLED); assert all(value is False for value in config.EXPERIMENT_LANES_ENABLED.values())'
{'EXP-BETA': False, 'EXP-TAIL': False, 'EXP-SPREAD': False, 'EXP-TBILL': False}
```

All flags in `EXPERIMENT_LANES_ENABLED` remain False.

## Commits and deviations

- Base: `1fe816981c57c1e1af2f9dbc92c3a2cc96e85e2e`
- Implementation/tests: `6c415858d87021f38505f3fa40b43efdedef140d`
- Receipt: committed separately after the implementation SHA and final
  verification evidence were available.
- Deviations: none. The localhost permission rerun was an environment
  accommodation for the unchanged full suite; execution remained offline.

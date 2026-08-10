# Ops failure classification receipt

Date: 2026-08-10
Branch: `codex/ops-failure-classification`
Base: `9640b92a9636a8d22aa83cb6819a8c1a75636bad`
Worktree: `.tmp/worktrees/ops-failure-classification`

## Scope and diagnosis

- `origin/main` was fetched first and resolved to the requested base.
- The observed Authlib exception is `OAuthError` with
  `error="invalid_grant"` and description
  `Refresh token is invalid, expired or revoked`.
- The intraday CLI had no exception boundary for this condition, so
  `tools/intraday_capture.sh` reached its `unrecognized failure mode` branch.
- The independent preclose lane had the same operational gap: its Python
  per-symbol catch converted the OAuth exception into a generic failed receipt,
  and `tools/schwab_chain_capture.sh` labeled every nonzero result only as
  `SCHWAB CHAIN STATUS: BROKEN`. The same named classification was therefore
  applied there.
- All failure tests used a constructed Authlib `OAuthError` and mocks or shell
  fixture input. No network call, Schwab credential read/write, token mutation,
  or retry occurred.

## RED evidence — captured verbatim

### Intraday Python boundary and wrapper classification

Command:

```text
env PYTHONPATH=. .venv/bin/python tests/test_intraday_capture.py MainCLITests.test_main_classifies_expired_schwab_refresh_token WrapperZeroCoverageWarnLiveTests.test_expired_refresh_token_requires_schwab_reauth
```

Output:

```text
EF
======================================================================
ERROR: test_main_classifies_expired_schwab_refresh_token (__main__.MainCLITests.test_main_classifies_expired_schwab_refresh_token)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_intraday_capture.py", line 1224, in test_main_classifies_expired_schwab_refresh_token
    rc = ic.main(["--session-tag", "midday"])
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/options_researcher/intraday_capture.py", line 810, in main
    exit_code, _ = capture(args.session_tag, force=args.force)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1198, in _execute_mock_call
    raise effect
authlib.integrations.base_client.errors.OAuthError: invalid_grant: Refresh token is invalid, expired or revoked

======================================================================
FAIL: test_expired_refresh_token_requires_schwab_reauth (__main__.WrapperZeroCoverageWarnLiveTests.test_expired_refresh_token_requires_schwab_reauth)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_intraday_capture.py", line 1395, in test_expired_refresh_token_requires_schwab_reauth
    self.assertIn(
AssertionError: 'CRITICAL: intraday_capture (midday): SCHWAB REAUTH REQUIRED -- run uv run python tools/setup_schwab.py' not found in 'CRITICAL: intraday_capture (midday): FAILED (exit 1) -- unrecognized failure mode, see output above\n'

----------------------------------------------------------------------
Ran 2 tests in 0.038s

FAILED (failures=1, errors=1)
```

### Preclose Python propagation/boundary and wrapper classification

Commands:

```text
env PYTHONPATH=. MPLCONFIGDIR=/private/tmp/ops-failure-mpl .venv/bin/python tests/test_schwab_chain_capture.py SchwabChainCaptureTests.test_expired_refresh_token_propagates_to_cli_boundary SchwabChainCaptureTests.test_main_classifies_expired_schwab_refresh_token
env PYTHONPATH=. .venv/bin/python tests/test_schwab_chain_schedule.py SchwabChainScheduleTests.test_expired_refresh_token_requires_schwab_reauth
```

Output:

```text
FE
======================================================================
ERROR: test_main_classifies_expired_schwab_refresh_token (__main__.SchwabChainCaptureTests.test_main_classifies_expired_schwab_refresh_token)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_schwab_chain_capture.py", line 197, in test_main_classifies_expired_schwab_refresh_token
    rc = capture.main(["--force"])
         ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/options_researcher/schwab_chain_capture.py", line 244, in main
    exit_code, _ = capture(force=args.force)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1139, in __call__
    return self._mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1143, in _mock_call
    return self._execute_mock_call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/carsynstephenson/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/lib/python3.12/unittest/mock.py", line 1198, in _execute_mock_call
    raise effect
authlib.integrations.base_client.errors.OAuthError: invalid_grant: Refresh token is invalid, expired or revoked

======================================================================
FAIL: test_expired_refresh_token_propagates_to_cli_boundary (__main__.SchwabChainCaptureTests.test_expired_refresh_token_propagates_to_cli_boundary)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_schwab_chain_capture.py", line 181, in test_expired_refresh_token_propagates_to_cli_boundary
    with self.assertRaises(OAuthError):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: OAuthError not raised

----------------------------------------------------------------------
Ran 2 tests in 0.037s

FAILED (failures=1, errors=1)
schwab_chain_capture failed: ['AAA']; receipt=/var/folders/zt/zktvcc0n0z1cq0kdt3mvg5lh0000gn/T/tmpafmntgzc/reports/2026-08-10/preclose.json
F
======================================================================
FAIL: test_expired_refresh_token_requires_schwab_reauth (__main__.SchwabChainScheduleTests.test_expired_refresh_token_requires_schwab_reauth)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_schwab_chain_schedule.py", line 89, in test_expired_refresh_token_requires_schwab_reauth
    self.assertIn(
AssertionError: 'CRITICAL: SCHWAB REAUTH REQUIRED -- run uv run python tools/setup_schwab.py' not found in 'SCHWAB CHAIN STATUS: BROKEN (exit 1; receipt/log contains evidence)\n'

----------------------------------------------------------------------
Ran 1 test in 0.007s

FAILED (failures=1)
```

### Dashboard fresh-build assertion mutation

The test assertions were added first. For the RED proof only, the production
stdout verb was temporarily changed from `wrote` to `rendered`, the focused
test was run, and the production line was immediately restored byte-for-byte.

Command:

```text
env PYTHONPATH=. MPLCONFIGDIR=/private/tmp/ops-failure-mpl .venv/bin/python tests/test_experiments_baseline.py ExperimentBaselineTests.test_module_entry_no_args_matches_production_command
```

Output:

```text
F
======================================================================
FAIL: test_module_entry_no_args_matches_production_command (__main__.ExperimentBaselineTests.test_module_entry_no_args_matches_production_command)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_experiments_baseline.py", line 165, in test_module_entry_no_args_matches_production_command
    self.assertIn("wrote ", without_experiments.stdout)
AssertionError: 'wrote ' not found in '2026-08-10 14:37:10,912 | INFO | LumiBot v4.5.63 starting\n2026-08-10 14:37:12,965 | INFO | .env file loaded from: /Users/carsynstephenson/options-validator/.env\nrendered /Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/.tmp/dashboard/attractiveness.html\nBLOCKED CRWV: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED TEM: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED PLTR: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED NOW: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED SMCI: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED NVDA: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED AMD: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED AVGO: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED IREN: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED USAR: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED ET: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED VST: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED CEG: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED MSFT: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED AMZN: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED NBIS: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED AMAT: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nBLOCKED CLSK: NO_CACHED_CHAINS (no chain parquet in .cache/chains)\nopen it in your browser to see the scenario tables\n'

----------------------------------------------------------------------
Ran 1 test in 4.599s

FAILED (failures=1)
```

### Repo-wide banner-pollution guard integration

The first full-suite run on the implementation exposed the existing guard
against unreviewed raw Python stdout captures. The wrapper's capture is needed
to preserve the Python process exit code and is safe because its only parsed
value uses an anchored grep; it was added to the guard's documented
reason-(a)+(b) allowlist.

Output:

```text
======================================================================
FAIL: test_every_python_capture_is_filtered_or_allowlisted (test_shell_banner_guard.ShellBannerGuardTests.test_every_python_capture_is_filtered_or_allowlisted)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/Users/carsynstephenson/options-validator/.tmp/worktrees/ops-failure-classification/tests/test_shell_banner_guard.py", line 362, in test_every_python_capture_is_filtered_or_allowlisted
    self.assertEqual(
AssertionError: Lists differ: [] != ['tools/schwab_chain_capture.sh:39 ($(...)[155 chars]&1)']

Second list contains 1 additional elements.
First extra element 0:
'tools/schwab_chain_capture.sh:39 ($(...)) CAP_OUT="$(env LIVE_MARKET_DATA_PROVIDER=schwab \\\\n+  SCHWAB_TRADING_ENABLED=false \\\\n+  "$UV" run python -m options_researcher.schwab_chain_capture 2>&1)'

- []
+ ['tools/schwab_chain_capture.sh:39 ($(...)) CAP_OUT="$(env '
+  'LIVE_MARKET_DATA_PROVIDER=schwab \\\\n+  SCHWAB_TRADING_ENABLED=false \\\\n+  '
+  '"$UV" run python -m options_researcher.schwab_chain_capture 2>&1)'] : Unfiltered python-stdout capture(s) found -- this is exactly the banner-pollution bug class (LumiBot v4.5.63 / python-dotenv print import-time INFO lines to stdout; see tools/daily_ritual.sh's 2026-07-23 ef4b3f5 and 2026-07-24 42ae8c8 fixes). Fix it with a strict anchored `grep -Eo '^...$' | tail -1` filter (with an explicit sentinel if empty is a legitimate outcome), or better, a program-written --out file (see options_researcher.h8_watch / entry_watch / h7_entry_preflight). Only add a justified ALLOWLIST entry in this test file if the capture is provably safe per the module docstring's reason (a)/(b).

tools/schwab_chain_capture.sh:39 ($(...)) CAP_OUT="$(env LIVE_MARKET_DATA_PROVIDER=schwab \\
  SCHWAB_TRADING_ENABLED=false \\
  "$UV" run python -m options_researcher.schwab_chain_capture 2>&1)

----------------------------------------------------------------------
Ran 2648 tests in 152.030s

FAILED (failures=1, skipped=5)
```

## Targeted GREEN evidence

- Focused behavior tests: 2 intraday, 2 preclose Python, 1 preclose wrapper,
  and 1 dashboard subprocess test all passed.
- Complete affected files: `test_intraday_capture.py` 80 passed;
  `test_schwab_chain_capture.py` 8 passed;
  `test_schwab_chain_schedule.py` 3 passed;
  `test_experiments_baseline.py` 11 passed.
- Both modified zsh wrappers passed `/bin/zsh -n`.
- No production change remains in `options_researcher/attractiveness_dashboard.py`.

## Final verification

- `uv run python -m unittest discover -s tests -q`:
  `Ran 2648 tests in 160.606s` — `OK (skipped=5)`.
- `uv run ruff check .`: `All checks passed!`
- `uv run pyright`: `0 errors, 0 warnings, 0 informations`.
- `git diff --check`: clean.
- `/bin/zsh -n tools/intraday_capture.sh`: clean.
- `/bin/zsh -n tools/schwab_chain_capture.sh`: clean.
- `uv run ruff format --check .` was also inspected: the fetched base has a
  pre-existing 272-file formatting baseline. It was not mass-formatted because
  that would create unrelated churn; the required repo-wide `ruff check .`
  lint gate is clean and the scoped diff passes `git diff --check`.

## Guardrail result

- Auth expiry remains nonzero and fail-closed; no retry was added.
- Token storage, credential loading, and OAuth refresh logic were not changed.
- No new dependency was added (`authlib` was already locked through the
  existing Schwab integration).
- `ledger/`, `~/options-validator-ops`, and
  `~/options-validator-research` were not modified.

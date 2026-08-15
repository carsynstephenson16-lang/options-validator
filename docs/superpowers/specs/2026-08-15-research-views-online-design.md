# Managed Display-Only Research Views Design

**Status:** proposed for owner review  
**Date:** 2026-08-15  
**Base:** `origin/main` at `7b91ae389dd3b5dcefa0a46461a6eddcd0cb6313`

## Goal

Keep the existing attractiveness/composite, attractiveness-experiment, and
Wasserstein views visible through one managed localhost service without adding
trade authority, registering an experiment, changing H7, or duplicating the
daily ritual's attractiveness build.

## Current state verified before design

- PRs #43 through #47 are present on `origin/main`. PR #47 already fixes and
  tests the `zsh` date comparison; this work must not touch that fix.
- `/Users/carsynstephenson/options-validator-ops` and
  `/Users/carsynstephenson/options-validator-research` are both cleanly aligned
  to current `origin/main`, except for one pre-existing untracked H7 backup
  receipt in the ops checkout. That receipt must be preserved.
- The daily ritual already writes
  `/Users/carsynstephenson/options-validator-ops/.tmp/dashboard/attractiveness.html`.
  That page already contains the display-only composite board.
- `options_researcher.experiments_dashboard` writes
  `.tmp/dashboard/experiments.html` when explicitly invoked.
- `options_researcher.regime_report` writes a display-only Wasserstein report;
  its default location is outside the served dashboard directory.
- Port 8766 is held by unmanaged PID 51099 running
  `/Users/carsynstephenson/options-validator-ops/.venv/bin/python -m http.server 8766 --bind 127.0.0.1`
  with cwd `/Users/carsynstephenson/options-validator-ops/.tmp/dashboard`.
- The current `tools/launchagents/` convention uses tracked templates, hardcoded
  ops-checkout paths, localhost binding, `.tmp` logs, and explicit install and
  verification commands in `tools/launchagents/README.md`.
- Capture-authorization verification found that the documents are still not
  fully self-consistent: the opening state and `docs/provider-transition.md`
  describe the isolated v2 branch as parked/unmerged, while the later Q10
  section says the branch was retired after its useful implementation reached
  `main`. This display task records that finding but does not reconcile it.

## Scope

### In scope

1. Add one display-only refresh wrapper in the ops checkout that runs exactly:
   - `options_researcher.experiments_dashboard`;
   - `options_researcher.regime_report --out .tmp/dashboard/wasserstein-regime.txt`.
2. Run both builders independently. A failure in one must not prevent the
   other from running.
3. Atomically write `.tmp/dashboard/research-views-status.txt` with the run
   timestamp and the success or failure of each builder. Preserve the last good
   experiment or Wasserstein artifact when a later build fails.
4. Add a weekday 07:30 ET and `RunAtLoad` LaunchAgent for the wrapper.
5. Replace the exact unmanaged port-8766 process with a managed, `KeepAlive`,
   `RunAtLoad` LaunchAgent that serves only
   `/Users/carsynstephenson/options-validator-ops/.tmp/dashboard` on
   `127.0.0.1:8766`.
6. Document install, verification, and rollback beside the current
   `tools/launchagents/` instructions.
7. After merge, fast-forward both protected deployment checkouts to the merged
   `origin/main` without touching their runtime artifacts.

### Out of scope

- Editing or invoking the attractiveness builder from the new wrapper.
- Editing `options_researcher/attractiveness.py`,
  `options_researcher/attractiveness_dashboard.py`, QM code, Schwab display
  code, `tools/daily_ritual.sh`, or any H7 path.
- Registering or running a backtest or robustness experiment.
- Changing ranking, verdicts, FIRE behavior, paper books, positions, ledgers,
  provider policy, data acquisition, or live-order capability.
- Repairing the capture-authorization documentation inconsistency.
- Publishing any service beyond localhost.
- Adding a framework, package, database, custom web application, or new Python
  serving module.

## Design

### Artifact production

Create `tools/research_display_refresh.sh`, executed from the ops checkout with
`/bin/zsh`. It resolves its repository root from its own path and defaults to
the ops checkout's `.venv/bin/python`, with a test-only environment override
for the interpreter.

The wrapper creates the dashboard directory, runs the experiments builder,
then runs the Wasserstein builder even if the first command fails. It records
each exit status and writes `research-views-status.txt` through a temporary file
followed by an atomic rename. It exits zero only when both builders succeed.
It performs no Git command, provider call, ledger write, receipt write, or
notification.

The wrapper intentionally does not run the attractiveness builder. The daily
ritual remains the sole producer of `attractiveness.html`, including its
embedded composite board.

### Localhost serving

Add `tools/launchagents/com.carsyn.options-validator.research-views.plist`.
It uses the ops virtual environment's standard-library `http.server`, binds
only `127.0.0.1:8766`, and serves only the ops `.tmp/dashboard` directory.
No repository code or external dependency is needed for serving.

Expected URLs:

- `http://127.0.0.1:8766/attractiveness.html`
- `http://127.0.0.1:8766/experiments.html`
- `http://127.0.0.1:8766/wasserstein-regime.txt`
- `http://127.0.0.1:8766/research-views-status.txt`

Add `tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist`.
It invokes the wrapper from the ops checkout at login/load and at 07:30 ET on
weekdays, after the existing 07:10 ritual schedule. The two jobs are separate:
the file server remains available when a refresh fails, and the refresh does
not need to manage process lifetime.

### Deployment and unmanaged-process replacement

Deployment must re-resolve port 8766 immediately before acting. Stop only the
listener whose command, cwd, bind address, and port match the verified
unmanaged server. If any field differs, stop deployment and report the new
owner instead of killing it.

After the feature branch is reviewed, merged, and fetched:

1. Verify the ops and research checkouts contain no unexpected tracked or
   untracked changes. Preserve the known H7 backup receipt.
2. Fast-forward each checkout to the merged `origin/main`; never reset, stash,
   or clean either checkout.
3. Create the required ops `.tmp` log and dashboard directories.
4. Copy the two reviewed plist templates to `~/Library/LaunchAgents/`.
5. Gracefully terminate the exact unmanaged listener.
6. Bootstrap and enable the managed refresh and server jobs.
7. Kickstart one refresh and verify all four URLs and the LaunchAgent states.

No scheduled job performs Git synchronization. Deployment alignment remains an
explicit reviewed operation.

## Failure behavior

- One builder fails: the other still runs; the wrapper returns nonzero; the
  served status file names the failed builder and exit code; the last good
  artifact is retained.
- Both builders fail: both failures appear in the status file; the server stays
  available; `attractiveness.html` remains owned by the ritual.
- Port 8766 is occupied by a different process at deployment: do not kill it;
  stop and report.
- LaunchAgent cannot start: leave the reviewed plist installed, capture
  `launchctl print` and log evidence, and do not start an ad-hoc replacement.
- Ops or research checkout has unexpected changes: do not update it; report the
  exact paths.
- Cached data is missing or stale: existing builders remain responsible for
  visible `DATA_BLOCKED`, staleness, and max-as-of labels. The wrapper does not
  weaken or reinterpret them.

## Concurrency and commit discipline

- All implementation occurs in `.tmp/worktrees/research-views-online` on
  `codex/research-views-online`, based on the recorded current `origin/main`.
- Before each commit, push, merge, and deployment, fetch `origin/main` and
  compare changed paths with active Claude worktrees.
- The implementation file set is limited to the new wrapper, its new tests,
  the two new plist templates, this spec, its plan, and the existing
  `tools/launchagents/README.md`.
- If Claude changes any of those paths after this spec, rebase and review the
  overlap before continuing. Never merge conflict markers or choose a side
  mechanically.
- Keep the spec/plan commit separate from behavior changes. Do not amend
  commits.

## Test strategy

Use test-driven development for the wrapper and plist contracts.

1. A failing wrapper test first proves the intended two-builder command set,
   output path, independent continuation after a simulated failure, atomic
   status publication, last-good preservation, and aggregate exit code.
2. Minimal wrapper implementation makes that test pass under real `zsh`.
3. Plist tests pin localhost binding, port 8766, ops paths, served directory,
   schedules, `RunAtLoad`, `KeepAlive` only for the server, and log paths.
4. `zsh -n` and `plutil -lint` validate the actual files.
5. Existing `test_experiments_dashboard.py` and `test_regime.py` suites remain
   green.
6. Run scoped Ruff and formatting checks, Pyright, `git diff --check`, then the
   full offline unit-test discovery before opening the pull request.
7. Independent Terra and Luna reviews, controller diff audit, CodeRabbit PR
   review, and green CI are required before merge.
8. Post-deployment verification checks the exact managed PIDs, localhost bind,
   file timestamps, status contents, and HTTP 200 responses for all four URLs.

## Acceptance criteria

1. Both deployment checkouts are on the merged current `origin/main`, with
   pre-existing runtime artifacts preserved.
2. Port 8766 is owned by the reviewed LaunchAgent and binds only localhost.
3. The server root is the ops `.tmp/dashboard` directory.
4. Attractiveness/composite remains ritual-built and is reachable without any
   new wrapper invocation.
5. Experiments and Wasserstein artifacts are built by the new wrapper and are
   reachable at the named URLs.
6. Failure of either builder is visible and does not prevent the other builder
   or the server from operating.
7. No H7, ledger, hypothesis, position, ranking, provider, or live-order path
   changes.
8. The final diff contains no unrelated refactor or new dependency.

## Rollback

1. Boot out the two new LaunchAgents.
2. Leave generated `.tmp/dashboard` artifacts in place; they are disposable
   and do not affect authority.
3. If necessary, restart the prior localhost-only standard-library server with
   the exact previously verified ops-dashboard command.
4. Revert the feature commit through a normal reviewed Git revert if the
   tracked templates or wrapper must be removed. Never reset a protected
   checkout.

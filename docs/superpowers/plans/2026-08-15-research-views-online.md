# Managed Display-Only Research Views Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task by task.

**Goal:** Keep the existing attractiveness/composite, experiments, and Wasserstein display-only research artifacts visible from one managed localhost server without granting them trading or verdict authority.

**Architecture:** A small zsh wrapper in the ops checkout independently invokes the existing experiments and Wasserstein builders and atomically publishes one health file. Two LaunchAgents separately schedule that wrapper and keep a standard-library HTTP server bound to the ops dashboard on localhost. The daily ritual remains the only attractiveness/composite producer.

**Tech Stack:** zsh, Python 3 standard library (`unittest`, `plistlib`, `http.server`), macOS launchd.

**Spec:** `docs/superpowers/specs/2026-08-15-research-views-online-design.md`

## Global Constraints

- Work only in `.tmp/worktrees/research-views-online` on `codex/research-views-online` until merge.
- Do not edit or invoke the attractiveness builder, `tools/daily_ritual.sh`, H7 files, ledgers, ranking, provider, position, paper-book, or order paths.
- Do not add a dependency, web framework, database, Git synchronization, notification, receipt, or new research computation.
- The wrapper runs exactly the existing experiments dashboard and Wasserstein regime report builders. Failure of either builder must not prevent the other from running.
- The wrapper defaults to the ops checkout Python and dashboard paths. `RESEARCH_DISPLAY_PYTHON` and `RESEARCH_DISPLAY_DASHBOARD_DIR` exist only to isolate tests.
- The status artifact is atomically replaced, includes the ET run timestamp and both exit codes, and the wrapper exits zero only if both builders exit zero.
- The server must serve only `/Users/carsynstephenson/options-validator-ops/.tmp/dashboard` on `127.0.0.1:8766`.
- The refresh job runs at load and at 07:30 ET on weekdays. Only the server has `KeepAlive`.
- Preserve last-good display artifacts on builder failure; never pre-delete or rewrite them in the wrapper.
- Use TDD: capture a focused failing test before adding each implementation, then capture the passing result.
- Each task owns only its named files and makes one narrow commit. Do not amend or modify another task's commit.

---

## Task 1: Build the independent refresh wrapper

**Owner:** Terra

**Files:**

- Create: `tests/test_research_display_refresh.py`
- Create: `tools/research_display_refresh.sh`

### Step 1: Write the failing wrapper contract test

Create a `unittest.TestCase` that runs the real `/bin/zsh` wrapper with a temporary dashboard directory and a temporary executable fake interpreter. The fake interpreter must append its full argument list to a log, optionally fail one named module through `FAKE_FAIL_MODULE`, and never touch the real checkout artifacts.

Cover these behaviors in focused tests:

1. The commands are exactly `-m options_researcher.experiments_dashboard` and `-m options_researcher.regime_report --out <temporary-dashboard>/wasserstein-regime.txt`, in that order.
2. If experiments exits nonzero, Wasserstein is still invoked, the wrapper exits nonzero, and the status records `experiments: FAILED exit=17` plus `wasserstein: OK exit=0`.
3. If Wasserstein exits nonzero, experiments still ran, the wrapper exits nonzero, and both outcomes are recorded.
4. If both exit zero, the wrapper exits zero and both outcomes are `OK`.
5. Pre-created `experiments.html` and `wasserstein-regime.txt` sentinel contents survive simulated builder failures.
6. `research-views-status.txt` exists as one complete final file and no sibling `research-views-status.txt.*.tmp` remains after a normal run.

The test fixture must set:

```python
env["RESEARCH_DISPLAY_PYTHON"] = str(fake_python)
env["RESEARCH_DISPLAY_DASHBOARD_DIR"] = str(dashboard_dir)
env["FAKE_PYTHON_LOG"] = str(call_log)
```

Run the RED test:

```bash
uv run python -m unittest tests/test_research_display_refresh.py -v
```

Expected RED: failure because `tools/research_display_refresh.sh` does not yet exist.

### Step 2: Add the minimal wrapper

Implement `tools/research_display_refresh.sh` with this interface and control flow:

```zsh
#!/bin/zsh
set -u

REPO_ROOT="${0:A:h:h}"
PYTHON_BIN="${RESEARCH_DISPLAY_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
DASHBOARD_DIR="${RESEARCH_DISPLAY_DASHBOARD_DIR:-${REPO_ROOT}/.tmp/dashboard}"
STATUS_PATH="${DASHBOARD_DIR}/research-views-status.txt"
STATUS_TEMP="${STATUS_PATH}.$$.tmp"

mkdir -p "$DASHBOARD_DIR"
trap 'rm -f "$STATUS_TEMP"' EXIT

"$PYTHON_BIN" -m options_researcher.experiments_dashboard
experiments_exit=$?

"$PYTHON_BIN" -m options_researcher.regime_report \
  --out "$DASHBOARD_DIR/wasserstein-regime.txt"
wasserstein_exit=$?

timestamp_et="$(TZ=America/New_York date '+%Y-%m-%dT%H:%M:%S%z')"
```

Write the status file with `print -r --` lines in this exact stable shape:

```text
research views refresh: <timestamp>
experiments: OK exit=0
wasserstein: FAILED exit=17
```

Derive `OK` or `FAILED` from each captured exit code, write all lines to `$STATUS_TEMP`, then `mv -f -- "$STATUS_TEMP" "$STATUS_PATH"`. Exit `1` if either captured code is nonzero; otherwise exit `0`. Do not use `set -e`, because both commands must always run. Do not delete or edit either builder's output.

Make the wrapper executable.

### Step 3: Prove GREEN and validate zsh syntax

```bash
uv run python -m unittest tests/test_research_display_refresh.py -v
/bin/zsh -n tools/research_display_refresh.sh
uv run ruff check tests/test_research_display_refresh.py
uv run ruff format --check tests/test_research_display_refresh.py
```

Expected: all tests pass, zsh syntax succeeds, Ruff is clean.

### Step 4: Self-review and commit

Confirm the diff contains only the two owned files, no attractiveness command, no Git command, and no real `.tmp` output.

```bash
git diff --check
git status --short
git add tests/test_research_display_refresh.py tools/research_display_refresh.sh
git commit -m "feat: refresh display-only research views"
```

---

## Task 2: Add managed localhost LaunchAgents and operator instructions

**Owner:** Luna

**Files:**

- Create: `tests/test_research_view_launchagents.py`
- Create: `tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist`
- Create: `tools/launchagents/com.carsyn.options-validator.research-views.plist`
- Modify: `tools/launchagents/README.md`

### Step 1: Write failing plist contract tests

Use `plistlib.loads(Path(...).read_bytes())` to verify the two tracked templates as runtime configuration, not XML formatting.

Assert the server template has:

- Label `com.carsyn.options-validator.research-views`.
- Program arguments exactly:

```python
[
    "/Users/carsynstephenson/options-validator-ops/.venv/bin/python",
    "-m",
    "http.server",
    "8766",
    "--bind",
    "127.0.0.1",
    "--directory",
    "/Users/carsynstephenson/options-validator-ops/.tmp/dashboard",
]
```

- Ops `WorkingDirectory`, `RunAtLoad is True`, `KeepAlive is True`, `ThrottleInterval == 10`, and stdout/stderr below `.tmp/research_views/`.

Assert the refresh template has:

- Label `com.carsyn.options-validator.research-display-refresh`.
- Program arguments exactly `/bin/zsh` plus `/Users/carsynstephenson/options-validator-ops/tools/research_display_refresh.sh`.
- Ops `WorkingDirectory`, `RunAtLoad is True`, no `KeepAlive`, `TZ=America/New_York`, and stdout/stderr below `.tmp/research_views/`.
- `StartCalendarInterval` contains exactly five entries: weekdays 1 through 5, hour 7, minute 30.

Run the RED test:

```bash
uv run python -m unittest tests/test_research_view_launchagents.py -v
```

Expected RED: missing plist templates.

### Step 2: Add the two minimal plist templates

Follow the existing XML plist style. Add only the keys pinned by the tests. Both templates use hardcoded ops paths. The server uses Python's standard-library `http.server`; the refresh template invokes the reviewed wrapper with `/bin/zsh`. Do not add sockets, network exposure, auto-Git behavior, or a dependency.

### Step 3: Document install, verification, replacement, and rollback

Append one `## Display-only research views` section to `tools/launchagents/README.md` that states:

- Attractiveness/composite remains produced by the daily ritual; the refresh job builds only experiments and Wasserstein.
- Both jobs target the ops checkout and port 8766 is localhost-only.
- Before replacement, resolve `lsof -nP -iTCP:8766 -sTCP:LISTEN`, inspect the PID with `ps`, and inspect its cwd with `lsof -a -p PID -d cwd`. Send `TERM` only when command, cwd, bind, and port match the unmanaged ops-dashboard server; otherwise stop.
- Install commands create `.tmp/research_views` and `.tmp/dashboard`, copy the two templates to `~/Library/LaunchAgents/`, then bootstrap and enable both labels.
- Verification commands use `launchctl print`, `launchctl kickstart` for the refresh, and `curl -fsS` for all four named URLs.
- Rollback uses `launchctl bootout` for both labels and leaves generated dashboard artifacts in place. It may restore the prior server only with the exact verified localhost ops-dashboard command.

This is operator documentation; do not execute deployment in this task.

### Step 4: Prove GREEN and validate plist syntax

```bash
uv run python -m unittest tests/test_research_view_launchagents.py -v
plutil -lint tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist
plutil -lint tools/launchagents/com.carsyn.options-validator.research-views.plist
uv run ruff check tests/test_research_view_launchagents.py
uv run ruff format --check tests/test_research_view_launchagents.py
```

Expected: tests pass, both plists are valid, Ruff is clean.

### Step 5: Self-review and commit

Confirm the diff contains only the four owned files and matches the current LaunchAgent conventions without touching port 8765 or H7.

```bash
git diff --check
git status --short
git add tests/test_research_view_launchagents.py \
  tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist \
  tools/launchagents/com.carsyn.options-validator.research-views.plist \
  tools/launchagents/README.md
git commit -m "ops: manage display-only research views"
```

---

## Task 3: Integration verification and landing evidence

**Owner:** Controller after independent reviews

**Files:** No implementation files.

### Step 1: Recheck scope and concurrent work

Fetch current `origin/main`, list all worktrees, compare the feature diff paths against active Claude changes, and stop on overlap. Confirm PR #47 remains present and do not touch its zsh fix. Confirm the capture-authorization contradiction is merely recorded and absent from this diff.

### Step 2: Run affected and repository checks

```bash
uv run python -m unittest \
  tests/test_research_display_refresh.py \
  tests/test_research_view_launchagents.py \
  tests/test_experiments_dashboard.py \
  tests/test_regime.py -v
/bin/zsh -n tools/research_display_refresh.sh
plutil -lint tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist
plutil -lint tools/launchagents/com.carsyn.options-validator.research-views.plist
uv run ruff check .
uv run ruff format --check .
uv run pyright
git diff --check origin/main...HEAD
uv run python -m unittest discover -s tests
```

Record exact exit status and terminal summary for every command. Do not weaken a check or treat truncated output as success.

### Step 3: Review, publish, and merge

Run a final whole-branch Sol review, push the branch, open a pull request that links the spec and plan, invoke CodeRabbit review, resolve all Critical/Important findings through the original implementer and scoped re-review, wait for green required checks, then squash-merge or merge according to repository convention. Re-fetch and verify the merge commit is on `origin/main` before deployment.

### Step 4: Deploy from merged main

Immediately before acting, verify both protected checkouts and re-resolve port 8766. Preserve the known ops untracked H7 backup receipt. Fast-forward the clean research and ops checkouts to merged `origin/main` without reset, stash, or clean.

Create the ops log/dashboard directories, install the reviewed plists, gracefully terminate only the exact verified unmanaged listener, bootstrap and enable both jobs, and kickstart the refresh. If the listener identity or either checkout differs from the verified state, stop deployment.

### Step 5: Verify the live result

Confirm:

- `launchctl print` shows both reviewed labels and managed PIDs.
- `lsof` shows port 8766 bound only to `127.0.0.1` by the managed server.
- The server cwd/root is the ops `.tmp/dashboard` directory.
- All four URLs return HTTP 200.
- `research-views-status.txt` records both builder outcomes and fresh timestamps.
- `attractiveness.html` remains present without the refresh wrapper invoking its builder.
- Ops and research remain aligned with merged `origin/main`, with runtime artifacts preserved.

If a builder reports `DATA_BLOCKED`, report that visible state honestly; do not change data policy or fake freshness.

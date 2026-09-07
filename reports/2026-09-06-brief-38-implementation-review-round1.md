# Brief 38 — independent adversarial IMPLEMENTATION review, round 1 (2026-09-06)

**Reviewer:** Opus adversarial implementation review, round 1 (subagent dispatched by the orchestrating Claude session).
**Target:** PR #158 "Fix ritual evidence staging when optional lanes are absent (Brief 38)", head `204775d`, branch `codex/brief38-evidence-staging`, draft = true, base `main`.
**Brief:** `docs/superpowers/plans/2026-09-06-38-ritual-evidence-staging-codex-brief.md` rev 3 @ `5efb4f9`. **Base:** `origin/main` @ `f83428d`.
**Environment:** macOS, git 2.39.5 (Apple Git-154), zsh 5.9, detached worktree `/Users/carsynstephenson/options-validator/.tmp/worktrees/pr158`.

**Method — everything I actually executed:**

- Read brief rev 3 in full, both brief review receipts, the whole diff `5efb4f9..204775d`, `tools/daily_ritual.sh` (whole file, staging region line by line), and the new `EvidenceStagingTests` class plus `MUTATION_VERB_SITES` / `test_every_script_surface_is_classified`.
- `gh pr view 158` (body, draft state, `statusCheckRollup`). No other network.
- Read-only inspection of `~/options-validator-ops`: HEAD, branch, presence/type/tracked-ness of all 17 allow-list paths, `ls -la reports ledger`, `.cache` symlink, global git config keys, `~/.gitignore_global`, `~/.githooks/`.
- Scratch git repos under `.tmp/brief38-impl-review/`: `git cat-file -e` on trees / files / absent paths / a repo with no HEAD; `git add` on (a) dir with tracked + globally-ignored file, (b) dir whose only file is ignored, (c) dir with a deleted tracked file, (d) dir containing an embedded git repo, (e) an ignored directory path, (f) a `chmod 000` directory.
- zsh one-liners proving `$?` after `_e="$(cmd)"`, `${var//$'\n'/ }`, and `typeset -U` dedupe of an already-populated array (incl. inside an `if` block).
- In the worktree, after `/tmp/pr158-suite.log` reached `EXIT=`: `zsh -n`, the 4 new tests, the whole provenance module, `uv run ruff check .`, `uv run pyright`, `git diff --check`, `gitleaks detect` on the diff, byte-diffs of the old vs new script inside and outside the region, an original-script red check, and **eight** source mutations (the five requested plus three of my own), each restored with `git checkout --`.
- Final `git -C .tmp/worktrees/pr158 status --short`: **empty** (verified after every mutation and at the end).

---

## Verdict: PASS WITH FIXES

The fix is behaviourally correct for Monday's run and conforms to brief rev 3 essentially clause for clause. Everything outside the staging region is byte-identical, both allow-lists are byte-identical, the registry re-pins are exactly right, and all five requested mutations are caught by a test. One MAJOR (a hermeticity hole in the new test harness that lets the tests pass while committing into a *different* repository — the same failure class the brief's round-2 review called a BLOCKER, re-opened through `GIT_DIR` instead of `cwd`) and five MINORs. No BLOCKER. The MAJOR is a one-line fix in the test file; nothing in `tools/daily_ritual.sh` needs to change.

---

## Findings

### 1. MAJOR — the test harness scrubs `cwd` but not inherited `GIT_*` env vars; with `GIT_DIR` set the four tests pass while committing into a foreign repository

`tests/test_daily_ritual_provenance.py:215-220` builds the subprocess environment as `{**os.environ, GIT_CONFIG_GLOBAL, GIT_CONFIG_SYSTEM, HOME}` and relies on `cwd=self.repo` (`:251`, `:280`) for repo selection. `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_CEILING_DIRECTORIES` etc. are passed straight through, and `GIT_DIR` beats `cwd`.

Proved, not argued. I created a throw-away repo (1 commit, `core.hooksPath=/some/hooks`) and ran only `GIT_DIR=<that repo>/.git uv run python -m unittest … -k EvidenceStaging`:

```
BEFORE commits=1 hooksPath=/some/hooks
Ran 4 tests in 1.501s
OK                                  <-- all four PASSED
AFTER  commits=9 hooksPath=[]       <-- 8 commits written into the foreign repo,
                                        its core.hooksPath silently blanked
aa6873c data(ritual): daily ritual data-phase artifacts 2026-09-06
da55a15 baseline
d781f2c data(h7): daily ritual evidence 2026-09-06
...
```

The tests never exercised the temp fixture at all and still reported OK. With `GIT_DIR` **and** `GIT_WORK_TREE` set they fail loudly in `setUp` instead — but `git init`/`git config user.*`/`git config core.hooksPath ""` still land in the foreign repo first.

Why it matters: brief round-2 finding 1 was a BLOCKER for exactly this hazard ("bare `git` commands in the extracted block would run in the REAL checkout"). The fix applied (`cwd=`) closes the *implicit* discovery path and leaves the *explicit* one open. Git sets `GIT_DIR` for every hook it runs and for `git rebase --exec` / `git bisect run` / `git filter-branch`, so any future "run the suite from a hook" wiring silently turns this test class into a writer on the operator's real checkout — the checkout whose `core.hooksPath` it would blank.

Reachability today: **not reachable**. I checked `~/.githooks/post-commit` and `~/bin/repo-reconcile` — neither runs the test suite (`grep -nE 'unittest|pytest|discover'` → no hits in the hook; only an `irreplaceable_data_guard` call in repo-reconcile), and `.github/workflows/ci.yml:38,:88-90` invokes unittest from a plain `run:` step. That is why this is MAJOR and not BLOCKER.

**Exact fix** (`tests/test_daily_ritual_provenance.py:215`), replace the dict literal with:

```python
        _GIT_CONTEXT_VARS = (
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_INDEX_FILE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_CEILING_DIRECTORIES",
            "GIT_NAMESPACE",
            "GIT_PREFIX",
        )
        self.env = {k: v for k, v in os.environ.items() if k not in _GIT_CONTEXT_VARS}
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "HOME": str(home),
            }
        )
```

(Module-level constant is fine too. `self.env` is used by both `_git` and `_stage`, so one edit covers the harness and the extracted region.)

### 2. MINOR — the newline collapse (round-1 finding 11) has no regression test; deleting it leaves all four tests green

`tools/daily_ritual.sh:593` (`_stage_err="${_stage_err//$'\n'/ }"`) is the round-1 MEDIUM-11 protection for `$SUMMARY` (`printf "%b"` at `:641`) and the AppleScript literal at `:655`. I deleted that line and ran the class: **`Ran 4 tests … OK`**. The reason is that the only test that sees git stderr, `test_unreadable_directory_warning_is_critical_even_with_zero_git_exit` (`:313-334`), asserts a *prefix* (`:329-332`) that ends before the newline. The real message is genuinely multi-line — reproduced in a scratch repo:

```
rc=0
out=[warning: could not open directory 'reports/h10/': Permission denied
reports/h10/baseline.txt: Permission denied]
```

so the collapse is load-bearing and unpinned.

**Exact fix** — add to `test_unreadable_directory_warning_is_critical_even_with_zero_git_exit` after the existing `assertIn` (`:333`):

```python
        for line in log.splitlines():
            self.assertRegex(line, r"^(CRITICAL: )?evidence: ")
```

(Every line the region emits goes through `note`/`crit`; a leaked continuation line fails this and nothing else does.)

### 3. MINOR — the `rc != 0` half of the crit condition has no test; deleting it leaves all four tests green

`tools/daily_ritual.sh:594` is `if [ "$rc" -ne 0 ] || [ -n "$_stage_err" ]; then`. I replaced it with `if [ -n "$_stage_err" ]; then` — **`Ran 4 tests … OK`**. No fixture ever produces a non-zero `git add`. The brief (WP-A.3(b), lines 121-124) explicitly names the case that would: an allow-list directory whose path is gitignored exits 1. Verified in a scratch repo:

```
$ git add -- reports/schwab_chains_intraday      # .gitignore: reports/schwab_chains_intraday/
rc=1
out=[The following paths are ignored by one of your .gitignore files: … hint: Use -f …]
```

Today both halves fire together for every failure git produces, so the code is correct; the gap is that a future edit can silently delete half the gate. **Exact fix** — add a fifth case to `EvidenceStagingTests`:

```python
    def test_ignored_allow_list_path_is_a_staging_failure(self):
        (self.repo / ".gitignore").write_text("reports/schwab_chains_intraday/\n", encoding="utf-8")
        self._git("add", "--", ".gitignore")
        self._git("commit", "-q", "-m", "ignore rule")
        intraday = self.repo / "reports/schwab_chains_intraday"
        intraday.mkdir(parents=True)
        (intraday / "r.json").write_text("{}\n", encoding="utf-8")
        log, committed = self._stage()
        self.assertIn(
            "CRITICAL: evidence: STAGING FAILED for reports/schwab_chains_intraday — ", log
        )
        self.assertEqual(committed, {"ledger/facts.log", "reports/h10/new.txt"})
```

(Also kills finding 2's mutation, since git's ignored-path message is four lines.)

### 4. MINOR — no test pins the log ORDER the brief's acceptance section requires

Brief acceptance (lines 266-271): the first ops log after landing must show the absent-path note *followed by* `evidence: committed`. `test_absent_optional_path_does_not_disable_other_evidence` (`:292-300`) asserts both strings with `assertIn` and never their order; `_stage` (`:288`) likewise. The code is ordered correctly (loop `:584-598` precedes the commit branch `:599-605`), but the acceptance criterion itself is unpinned.

**Exact fix** — in `test_absent_optional_path_does_not_disable_other_evidence`, replace the bare membership check with:

```python
        self.assertLess(
            log.index("evidence: allow-list path absent, not staged: reports/schwab_chains_intraday"),
            log.index("evidence: committed"),
        )
```

### 5. MINOR — the PR body's "failed against the original code" red check is true but proves the wrong thing

I reproduced it (`git show 5efb4f9:tools/daily_ritual.sh > tools/daily_ritual.sh`): all four tests **error**, and every one of them errors identically at `tests/test_daily_ritual_provenance.py:181` with `ValueError: substring not found` — `_region(source, "evidence staging")` cannot find the marker. That is "the marker does not exist yet", not "staging is broken". The meaningful red check is mutation M4 below (markers present, original single `git add` restored), which fails all four on behaviour. Recommend the PR body say which red check was run, or that M4 be the one quoted. No code change required.

### 6. MINOR (informational, no fix required) — two accepted false-BROKEN surfaces of the stderr gate that the PR body does not name

`_stage_err="$(git add -- "$p" 2>&1)"` (`:592`) captures stdout **and** stderr, and any non-empty capture crits. Two observed producers beyond the intended one:

- `warning: adding embedded git repository:` — reproduced at **rc = 0** with a 10-line message. Would crit and emit a ~600-char collapsed line into `$SUMMARY`. Not reachable in ops today (no nested `.git` under any allow-list path).
- Any future git *advice/hint* on `git add`.

Conversely I confirmed two non-producers, which is good news for Monday: a directory containing a globally-ignored file (`~/.gitignore_global` is `.DS_Store` only) exits 0 silently even when that file is the directory's only untracked content, and staging a directory with a deleted tracked file inside exits 0 silently and correctly stages the deletion.

Also informational: `git cat-file -e "HEAD:$p"` in a repository with no commits exits 128, so the loop would take the `note` branch for every path. Not reachable in ops — HEAD exists and the branch guard at `:95-100` refuses any non-`main` checkout before Step 8.

---

## Brief conformance, WP by WP

| Brief clause | Implementation | Status |
|---|---|---|
| WP-A.1 markers `# ---- evidence staging ----` / `# ---- end evidence staging ----`, bracketing `DATA_TIER_PATHS=(` … commit `fi` | `tools/daily_ritual.sh:561` and `:607` (a blank line at `:606` sits between `fi` `:605` and the end marker) | CONFORMS. `_region` (`tests/…:180-184`) searches `"# ---- evidence staging "` incl. trailing space — both markers match; `source[start:end]` includes `DATA_TIER_PATHS`, `GIT_ADD_PATHS`, the whole `FULL_AUTHORITY_RC` branch, the loop and the commit branch |
| WP-A.2 `typeset -U GIT_ADD_PATHS` immediately after the concat line, inside the full-authority branch only | `:576`, immediately after `:575` | CONFORMS. Verified in zsh 5.9 that `typeset -U` dedupes an already-populated array, and that doing so inside a top-level `if` block is global (`B=(p q p); if true; then typeset -U B; fi` → `count=2`). Data-tier-only path needs no dedupe: `DATA_TIER_PATHS` (`:562-563`) is 11 distinct paths |
| WP-A.3(a) absent → tracked-in-HEAD crit / untracked note | `:585-590` | CONFORMS. `git cat-file -e "HEAD:<dir>"` returns 0 for a tracked **tree** (verified, with and without trailing slash), 128 for an absent path |
| WP-A.3(b) `_stage_err="$(git add -- "$p" 2>&1)"; rc=$?` | `:592` | CONFORMS. Proved in zsh that `$?` after an assignment from a command substitution is the substitution's status: `_e="$( (echo out; echo err >&2; exit 7) 2>&1 )"; rc=$?` → `rc=7`, `err=[out\nerr]` |
| WP-A.3(b) newline collapse via parameter expansion, never `tr` | `:593` | CONFORMS (`printf "a\nb\nc"` → `[a b c]`). Untested — finding 2 |
| WP-A.3(b) crit on rc≠0 **OR** non-empty stderr | `:594` | CONFORMS. rc-half untested — finding 3 |
| WP-A.5 crit cannot flip `RITUAL_TERMINAL_STATUS` | acknowledged in PR body ("Staging failures occur after the terminal receipt is published…") | CONFORMS |
| WP-A.6 `:583-589` commit branch byte-identical | `diff` old `583-589` vs new `599-605` | **IDENTICAL** |
| WP-A.7 exactly one textual `git add` | `grep -c 'git add' tools/daily_ritual.sh` → **1** (`:592`) | CONFORMS |
| WP-A.8 registry re-pinned to measured lines | see PR-body table below | CONFORMS, all six verified by `grep -n` |
| WP-A.9 `2>/dev/null` removed from the staging call | `:592` | CONFORMS |
| OUT: allow-list content, commit messages, tier logic, commit branch, push fn, restic, terminal status, `EVIDENCE_ALLOW` copies | byte-diffs below | **ALL UNCHANGED** |
| Crit/note strings exactly as prescribed | `:587`, `:589`, `:595` | Character-identical to brief lines 104-105 / 117, em dash included |
| Draft PR, no merge/sync/ledger | `isDraft: true`, one commit, two files | CONFORMS |

**Failure semantics (the highest-value check).** `grep -nE '^\s*(set |setopt|unsetopt|trap )' tools/daily_ritual.sh` → **no matches**; no `emulate` either. There is no `errexit`, no `pipefail`, no `ERR` trap, so neither `git cat-file -e`'s exit 1 nor a failing `git add` inside `$( … )` can abort the script or the loop. The real `crit()` (`:85`) is `crit() { CRITICAL=1; CRIT_COUNT=$((CRIT_COUNT + 1)); note "CRITICAL: $1"; }` — it does **not** exit; the harness stub (`:268`) is behaviourally identical. The `note` stub (`:267`) differs from the real `note()` (`:74`) in that it does not append to `$SUMMARY` and does not echo `>>> `, so the `printf "%b"` / AppleScript path is not exercised — the residual the brief accepts at lines 132-136 and the PR body restates.

**Harness variable coverage.** Every `$`-expansion inside the region is `RUN_DATE`, `FULL_AUTHORITY_RC`, `DATA_TIER_PATHS`, `FULL_TIER_PATHS`, `GIT_ADD_PATHS`, `EVIDENCE_COMMIT_MSG`, `_stage_err`, `rc`, `p`. The prelude (`:264-276`) defines `RUN_DATE`, `FULL_AUTHORITY_RC`, `SUMMARY`, `CRITICAL`, `CRIT_COUNT`, `LOGDIR`, `REPO` — a superset; `LOGDIR` and `REPO` are unused by the region (the brief asked for them anyway). No undefined variable. The region contains **no `cd` and no `$REPO`**, so it depends on cwd — production supplies it with `cd "$REPO"` at `:37`, the harness with `cwd=self.repo`. `$p`, `$rc`, `$_stage_err` appear nowhere else in the script (`grep -nE '(^|[^A-Za-z_$])\$p\b|\$rc\b|_stage_err'` → only `:585-595`).

**Directory / symlink / HEAD behaviour (item b).** `git cat-file -e "HEAD:<tree>"` → 0; `"HEAD:<tree>/"` → 0; `"HEAD:<file>"` → 0; absent → 128; no-HEAD repo → 128 (fatal suppressed by `2>/dev/null`, falls to the `note` branch). Read-only in `~/options-validator-ops`, **none of the 17 allow-list paths is a symlink** (`.cache` is, but it is not on the allow-list); all 17 are present and tracked in HEAD **except** `reports/schwab_chains_intraday` (absent, untracked). So Monday's 09:09 run on this code produces exactly one `note` and zero crits from the loop — the intended outcome.

**Cleanup ordering (item d).** `addCleanup(temporary.cleanup)` is registered in `setUp` (`:209`) and `addCleanup(h10.chmod, original_mode)` in the test (`:316`, before `chmod(0)`); unittest runs cleanups LIFO, so permissions are restored before the tempdir is removed, on the failure path too. `@unittest.skipIf(os.geteuid() == 0, …)` present at `:312`; it did **not** skip in my run (macOS non-root), and `.github/workflows/ci.yml:38` / `:88-90` run non-root.

**Other tests that parse this block.** `test_durability_allow_list_is_tier_scoped` (`:782-843`) anchors on `durability.index("git add --")`, which `git add -- "$p"` preserves; `tests/test_closes_receipt.py` and `tests/test_schwab_chain_intraday.py` were not edited (two-file diff) and are green in the full-suite run below.

---

## PR-body claims audit

| Claim | Status | How |
|---|---|---|
| Only `tools/daily_ritual.sh` + `tests/test_daily_ritual_provenance.py` changed | **VERIFIED** | `git diff --name-only 5efb4f9..204775d` → exactly those two; single commit `204775d` on the branch |
| No allow-list contents / commit messages / commit branch / tier logic / push / backup / terminal receipt changed | **VERIFIED** | `diff` old `1-560` vs new `1-560` → identical; old `590-EOF` vs new `608-EOF` → identical; `DATA_TIER_PATHS`, `FULL_TIER_PATHS`, both commit messages, commit branch `583-589`↔`599-605` → all byte-identical |
| Four hermetic regressions "failed against the original code and pass after the repair" | **VERIFIED, but weak** | They pass now (4/4 OK); against `5efb4f9`'s script all four *error* on the missing region marker, not on behaviour. Finding 5. My M4 supplies the behavioural red |
| Provenance module: 47 tests passed | **VERIFIED** | `Ran 47 tests … OK` (baseline was 43 + 4 new) |
| Permission test ran under a non-root macOS account | **VERIFIED** | `-v` run shows `test_unreadable_directory_… ok`, not skipped |
| "In-memory mutations removing deduplication, ignoring stderr, and downgrading a required missing path were each rejected" | **VERIFIED** (and incomplete) | M1/M2/M3 all rejected. Only three of the five obvious mutations were reported; I ran five (all rejected) plus three more, two of which survive — findings 2 and 3 |
| Full offline suite: 3,807 tests, 5 skipped, exit 0 | **VERIFIED** | `/tmp/pr158-suite.log`: `Ran 3807 tests in 334.239s`, `OK (skipped=5)`, `EXIT=0`. (Body says 321.819s — different run of the same suite, not a discrepancy) |
| Ruff + Pyright passed | **VERIFIED** | `uv run ruff check .` → `All checks passed!`; `uv run pyright` → `0 errors, 0 warnings, 0 informations` |
| `zsh -n` passed | **VERIFIED** | `zsh -n tools/daily_ritual.sh` → exit 0 |
| `git diff --check` passed | **VERIFIED** | `git diff --check 5efb4f9..204775d` → clean |
| Gitleaks scanned the diff without findings | **VERIFIED** | `gitleaks detect --no-git --source /tmp/pr158.diff` → `no leaks found` (binary present at `/opt/homebrew/bin/gitleaks`) |
| GitHub checks: Offline Quality Gates / macOS Shell Contracts / Secret Scan passed, Claude PR Review skipped | **VERIFIED** | `gh pr view 158 --json statusCheckRollup` → `Offline Quality Gates: SUCCESS`, `macOS Shell Contracts: SUCCESS`, `Secret Scan: SUCCESS`, `review: SKIPPED` |
| Registry re-pins 582→592, 585→601, 595→613, 596→614, 597→615, 614→632 | **VERIFIED** | `grep -n` on the new script: `git add` 592, `git commit` 601, `git fetch` 613, `git merge` 614, `git push` 615, `restic backup` 632; `MUTATION_VERB_SITES` (`tests/…:138-143`) matches; `test_every_script_surface_is_classified` green |
| "Exactly one textual staging command remains" | **VERIFIED** | `grep -c 'git add' tools/daily_ritual.sh` → 1 |
| "Byte comparisons verified both allow-lists … and all code outside staging" | **VERIFIED** | reproduced independently (row 2 above) |
| PR stays DRAFT; no merge/sync/ledger; ops fast-forward required before Mon 09:09 or the fix is live from Tuesday | **VERIFIED** | `isDraft: true`; branch has one commit touching two files; body states the ops-sync requirement explicitly, matching brief lines 276-286 |
| "%b expansion of unusual escaped path bytes unchanged; no second sanitizer" | **VERIFIED** | `note()`/`printf "%b"` (`:74`, `:641`, `:655`) untouched |
| "CodeRabbit CLI was unavailable; independent local diff review completed" | **CONSISTENT BUT UNVERIFIED** | Cannot audit an unlogged manual review |
| "268 files would be reformatted (pre-existing debt)" | **CONSISTENT BUT UNVERIFIED** | Not re-run; irrelevant to this diff, which ruff accepts |

---

## Mutation results

All run as `uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py' -k EvidenceStaging`, each restored with `git checkout -- tools/daily_ritual.sh`.

| # | Mutation | Result | Test(s) that caught it |
|---|---|---|---|
| M1 | delete `typeset -U GIT_ADD_PATHS` (`:576`) | **CAUGHT** (1 failure) | `test_full_authority_reports_deleted_duplicate_path_once` |
| M2 | delete `\|\| [ -n "$_stage_err" ]` (`:594`) | **CAUGHT** (1 failure) | `test_unreadable_directory_warning_is_critical_even_with_zero_git_exit` |
| M3 | tracked-absent `crit` → `note` (`:587`) | **CAUGHT** (1 failure) | `test_deleted_tracked_path_is_critical_and_other_evidence_survives` |
| M4 | revert loop to `git add -- "${GIT_ADD_PATHS[@]}" 2>/dev/null` (markers kept) | **CAUGHT** (4 failures) | all four — this is the real behavioural red check |
| M5 | remove `2>&1` from the substitution (`:592`) | **CAUGHT** (1 failure) | `test_unreadable_directory_warning_is_critical_even_with_zero_git_exit` |
| M6 *(mine)* | drop the `[ "$rc" -ne 0 ] \|\|` half only | **SURVIVES — `Ran 4 tests … OK`** | none → finding 3 |
| M8 *(mine)* | delete the newline collapse (`:593`) | **SURVIVES — `Ran 4 tests … OK`** | none → finding 2 |
| M9 *(mine)* | `[ ! -e "$p" ]` → `[ ! -d "$p" ]` | **CAUGHT** (2 failures) | tests 1 and 3 |

All five mutations named in the review assignment are caught. The two survivors are my own additions and are coverage gaps, not defects in shipped behaviour.

---

## Original-script red check

`git show 5efb4f9:tools/daily_ritual.sh > tools/daily_ritual.sh`, then the four tests:

```
ERROR: test_absent_optional_path_does_not_disable_other_evidence
ERROR: test_deleted_tracked_path_is_critical_and_other_evidence_survives
ERROR: test_full_authority_reports_deleted_duplicate_path_once
ERROR: test_unreadable_directory_warning_is_critical_even_with_zero_git_exit
  File ".../tests/test_daily_ritual_provenance.py", line 181, in _region
    start = source.index(f"# ---- {name} ")
ValueError: substring not found
Ran 4 tests in 0.545s
FAILED (errors=4)
```

They fail, but every failure is "the region marker does not exist", i.e. the tests are unrunnable rather than red on behaviour. The behavioural red is M4 (markers present, original single `git add` restored): `FAILED (failures=4)`, with `test_absent_optional_path_does_not_disable_other_evidence` failing precisely because nothing was staged — the production bug. Restored afterwards; `git status --short` empty.

---

## What I executed and raw results

```
git diff --stat 5efb4f9..204775d
  tests/test_daily_ritual_provenance.py | 154 ++++++++++++++++++++--
  tools/daily_ritual.sh                 |  20 ++++-
git log --oneline 5efb4f9..204775d      -> 204775d fix(ritual): stage evidence independently of absent lanes
gh pr view 158                          -> state OPEN, isDraft true, base main, head 204775d
gh pr view 158 --json statusCheckRollup -> Offline Quality Gates SUCCESS / macOS Shell Contracts SUCCESS /
                                           Secret Scan SUCCESS / review SKIPPED

grep -nE '^\s*(set |setopt|unsetopt|trap )' tools/daily_ritual.sh   -> (no matches)
grep -c 'git add' tools/daily_ritual.sh                              -> 1  (line 592)
grep -n 'git commit|fetch|merge|push|restic backup'                  -> 601 / 613 / 614 / 615 / 632
zsh -n tools/daily_ritual.sh                                         -> exit 0
diff old[1-560]  new[1-560]                                          -> IDENTICAL
diff old[590-EOF] new[608-EOF]                                       -> IDENTICAL
diff DATA_TIER_PATHS / FULL_TIER_PATHS / both commit msgs / 583-589  -> IDENTICAL

uv run python -m unittest ... -k EvidenceStaging -v                  -> Ran 4 tests, OK
uv run python -m unittest ... -p test_daily_ritual_provenance.py     -> Ran 47 tests, OK
/tmp/pr158-suite.log                                                 -> Ran 3807 tests in 334.239s
                                                                        OK (skipped=5) ; EXIT=0
uv run ruff check .                                                  -> All checks passed!
uv run pyright                                                       -> 0 errors, 0 warnings, 0 informations
git diff --check 5efb4f9..204775d                                    -> clean
gitleaks detect --no-git --source /tmp/pr158.diff                    -> no leaks found

zsh: _e="$( (echo out; echo err >&2; exit 7) 2>&1 )"; rc=$?          -> rc=7  err=[out\nerr]
zsh: _e="$(printf 'a\nb\nc')"; _e="${_e//$'\n'/ }"                   -> [a b c]
zsh: A=(x y z y x); typeset -U A                                     -> A=(x y z) count=3
zsh: B=(p q p); if true; then typeset -U B; fi                       -> B=(p q) count=2

git cat-file -e HEAD:<tracked dir>      -> 0     HEAD:<dir>/  -> 0     HEAD:<file> -> 0
git cat-file -e HEAD:<absent>           -> 128   (fresh repo, no HEAD) -> 128
git add <dir with tracked + .DS_Store>  -> rc 0, no output
git add <dir whose only file ignored>   -> rc 0, no output
git add <dir with deleted tracked file> -> rc 0, no output, deletion staged (D)
git add <ignored directory path>        -> rc 1, 5-line message
git add <chmod 000 dir>                 -> rc 0, 2-line stderr, NOTHING staged (no deletion staged)
git add <dir containing embedded repo>  -> rc 0, 10-line warning+hints
git show --name-only --format= HEAD     -> bare filenames, no leading blank line (root and non-root commits)

~/options-validator-ops (read-only): HEAD f83428d on main; 16/17 allow-list paths present+tracked;
  reports/schwab_chains_intraday ABSENT + UNTRACKED; no allow-list path is a symlink;
  .cache -> /Users/carsynstephenson/options-validator/.cache (not on the allow-list);
  global core.excludesfile = ~/.gitignore_global (".DS_Store" only); core.hooksPath = ~/.githooks (post-commit only)

GIT_DIR=<throwaway repo>/.git uv run python -m unittest ... -k EvidenceStaging
  -> Ran 4 tests, OK   while the throwaway repo went 1 -> 9 commits and core.hooksPath -> "" (finding 1)

FINAL: git -C /Users/carsynstephenson/options-validator/.tmp/worktrees/pr158 status --short
  -> (empty)
```

Nothing was committed. `ledger/` was not touched in any checkout. The main checkout was read-only except for this receipt file. Scratch repositories live under `.tmp/brief38-impl-review/` and can be deleted.

---

## Fix list for the round (all in `tests/test_daily_ritual_provenance.py`; no change to `tools/daily_ritual.sh`)

1. **(MAJOR)** Scrub `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CEILING_DIRECTORIES`, `GIT_NAMESPACE`, `GIT_PREFIX` from `self.env` at `:215-220` (exact code in finding 1).
2. **(MINOR)** Add the all-lines-are-single-note assertion to the unreadable-directory test (finding 2) so the newline collapse is pinned.
3. **(MINOR)** Add `test_ignored_allow_list_path_is_a_staging_failure` (finding 3) so the `rc != 0` half of the gate is pinned.
4. **(MINOR)** Add the `assertLess` order pin to test 1 (finding 4) so the brief's acceptance ordering is enforced.
5. **(MINOR, PR body only)** State which red check was run, or quote the marker-preserving revert (M4) instead — the plain original-script run errors on the missing marker rather than failing on behaviour (finding 5).

None of these changes any shipped behaviour, so the ops-durability outcome for Monday 2026-09-07 is unaffected by whether they land before or after the merge. The brief's operational point stands and is correctly restated in the PR body: **merging alone does not protect the 09:09 run — `~/options-validator-ops` must be fast-forwarded before it**, and that is the owner's/orchestrator's action, not the executor's.

---

## Fix round — applied on the PR head (2026-09-06 ~22:45 ET, orchestrating session; tests only)

Findings 1–4 applied verbatim to `tests/test_daily_ritual_provenance.py`; `tools/daily_ritual.sh` unchanged (byte-identical to 204775d). Evidence, all Test-verified in the PR worktree:

- Finding 1 (GIT_DIR): red reproduced before the fix — foreign repo 1 → 9 commits, `core.hooksPath` blanked, 4 tests OK. After the fix — foreign repo 1 → 1 commits, hooksPath intact, 5 tests OK.
- Finding 2 (newline collapse) mutation re-check after the fix: deleting the collapse line → `FAILED (failures=1)`.
- Finding 3 (rc half) mutation re-check after the fix: dropping `[ "$rc" -ne 0 ] ||` → `OK`.
- Finding 4 (order pin): `assertLess(note, committed)` in the optional-path test.
- `EvidenceStagingTests`: 5 tests OK; whole provenance file: 48 tests OK; ruff clean. The full offline suite at 204775d was independently re-run by the orchestrator: 3,807 tests, 5 skipped, exit 0 (the fix round changes tests only).
- Finding 5 (weak red check) and 6 (informational): recorded, no code change.

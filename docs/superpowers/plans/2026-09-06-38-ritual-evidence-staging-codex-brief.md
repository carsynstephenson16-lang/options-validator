# Codex brief 38 — Ritual evidence staging must survive an absent allow-list path

**Date:** 2026-09-06 (rev 2; rev 1 reviewed FAIL — `reports/2026-09-06-brief-38-adversarial-review-round1.md`, all 19 findings applied)
**Author:** Claude (orchestrating session; ledger-durability diagnosis, 2026-09-06)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37; owner may substitute at dispatch)
**Status:** DRAFT — pending independent adversarial review (round 2) before hand-off
**Provenance:** file:line constraints are Repo-verified against origin/main
@f83428d unless a sentence carries its own label. "Test-verified" facts were
reproduced read-only in the ops execution checkout (`~/options-validator-ops`)
or in a throw-away temp repository (git 2.39.5, Apple Git-154) on 2026-09-06 by
the author or the round-1 reviewer. Sentences labelled **Inference** are the
author's reading of the code, not a file fact.

## Why this exists (plain language)

Since 2026-09-03 the daily ritual has persisted NOTHING, while printing
"evidence: nothing new to persist" as if that were true. Cause, Test-verified:

1. PR #150 (`6484092`, reached the ops checkout 2026-09-02 20:18 ET, after that
   morning's evidence commit) added `reports/schwab_chains_intraday` to the
   ritual's evidence allow-list `DATA_TIER_PATHS` (`tools/daily_ritual.sh:561-562`).
   The intraday lane's install is an owner-gated staged step that has not
   happened (its LaunchAgent plist is not installed), so that directory does
   not exist in the ops checkout; every other listed path exists.
2. Step 8 stages the whole list in ONE call —
   `git add -- "${GIT_ADD_PATHS[@]}" 2>/dev/null` (`:582`). `git add` aborts
   the entire command on any unmatched pathspec (reproduced: exit 128,
   `fatal: pathspec 'reports/schwab_chains_intraday' did not match any files`)
   and stages nothing; the `2>/dev/null` discards the only evidence of that.
   No single-call form is safe: `--ignore-errors`, `:(glob)` and `:(literal)`
   pathspec magic all exit 128 identically (Test-verified by the reviewer).
3. `git diff --cached --quiet` (`:583`) then sees an empty index and the script
   prints `evidence: nothing new to persist` (`:584`). The 2026-09-03 and
   2026-09-04 ritual logs both carry that line; the 2026-09-02 run printed
   `evidence: committed`. 2026-09-05 was a Saturday, so exactly two runs were
   lost.

Impact, Test-verified: a dry run of the same staging with only the existing
paths listed 36 files / 6,880 lines that had accumulated on one disk —
`ledger/facts.log` appends (SCHWAB_CHAIN_CAPTURE 09-02/09-03, DATA_PULL and
DATA_PULL_OHLCV 09-03/09-04), the 2026-09-02 and 2026-09-03 Schwab capture
receipts (manifest, preclose, quote-age sidecar), H10b observations, the
pick-tracker event log, two H10 watch receipts, a ritual run-status receipt.
The owner-directed rescue commit `f83428d` persisted them on 2026-09-06. The
script is unchanged, so the next ritual — **Mon 2026-09-07 09:09 ET**: the
LaunchAgent's `StartCalendarInterval` is Weekday 1–5 with no market-calendar
filter, so it fires on Labor Day too, and `AS_OF` resolves to the last
completed session so Step 8 runs — will fail the same way. Until this lands,
durability is a manual rescue commit after each run. This brief fixes the
staging so one absent allow-list path can never again silently disable
durability for every other path.

## Scope

**IN:** `tools/daily_ritual.sh` Step 8 staging only (`:561-590`), and
`tests/test_daily_ritual_provenance.py` (the mutation-verb registry it pins,
plus the new hermetic tests).

**OUT (hard):**
- No change to the allow-list CONTENT (`DATA_TIER_PATHS` `:561-562`,
  `FULL_TIER_PATHS` `:571-573`): `reports/schwab_chains_intraday` stays listed —
  it is correct the day the lane is installed.
- No change to the commit messages (`:564-569`, `:575-580`), the tier logic
  (`:570`, `FULL_AUTHORITY_RC`), the `git diff --cached --quiet` branch and
  commit (`:583-589`), the push function (`:594-597`), the restic snapshot
  (`:614`), the `RITUAL_TERMINAL_STATUS` computation/publication (`:514-526`),
  or any `note`/`crit` string that exists today.
- No change to `tools/schwab_chain_intraday_capture.sh` (`EVIDENCE_ALLOW`,
  `:74-79`) — that is the intraday wrapper's alignment guard, not a staging
  list, and is out of scope even though it names the same path.
- No ledger write, no plist/launchd change, no ops-checkout mutation, no
  change to `PYTHON_DASH_C_CLASSIFICATION` sites
  (`tests/test_daily_ritual_provenance.py:96-108`; all nine are before `:561`
  and are unaffected by a change below it).
- No second `git add` textual site (see WP-A step 3).

## Work packages

### WP-A — Stage each allow-list path on its own; never discard the error

1. Bracket the replaced region with the file's existing marker convention —
   `# ---- evidence staging ----` before `DATA_TIER_PATHS=(` and
   `# ---- end evidence staging ----` after the commit branch's closing `fi`
   (`:589`) — exactly like the four regions at `:154/268`, `:270/324`,
   `:326/373`, `:387/479`, so `_region(source, "evidence staging")`
   (`tests/test_daily_ritual_provenance.py:178-183`) can address it and the
   WP-B test never depends on line numbers. Marker lines are comments and are
   excluded from the registry by `_code_lines` (`:192-198`).
2. Dedupe first: `typeset -U GIT_ADD_PATHS` immediately after the array is
   final (`:574`). `ledger/facts.log` is in the array twice on full-authority
   days (`:562` and `:571`+`:574`); without dedupe one absent file would emit
   two crits and add 2 to `CRIT_COUNT`, the pure-counter input to the
   `[DATA-STARVED]` carve-outs at `:631`/`:649`.
3. Replace the single call at `:582` with a loop over `"${GIT_ADD_PATHS[@]}"`
   that, for each path `$p`:
   (a) if `$p` does not exist: if it is tracked in HEAD
   (`git cat-file -e "HEAD:$p" 2>/dev/null`), its absence means committed
   evidence was deleted → `crit "evidence: REQUIRED allow-list path absent: $p"`;
   otherwise it is a lane not installed yet → `note "evidence: allow-list path
   absent, not staged: $p"`. Repo-verified: on `origin/main` every allow-list
   path has tracked files except `reports/schwab_chains_intraday` (0), so this
   rule reproduces the intended behaviour today and self-corrects the day that
   lane's first receipt is committed. Intentional consequence (**Inference**,
   reviewer-confirmed): a wholly-deleted tracked path's deletion is no longer
   staged by the ritual — the safer behaviour for an append-only ledger; a
   human decides such a deletion.
   (b) if `$p` exists: `_stage_err="$(git add -- "$p" 2>&1)"; rc=$?`; then
   collapse newlines — `_stage_err="${_stage_err//$'\n'/ }"` (never pipe
   through `tr`, which would discard the exit status) — and if `rc` is
   non-zero OR `_stage_err` is non-empty →
   `crit "evidence: STAGING FAILED for $p — $_stage_err"`. Both conditions are
   required: `git add` on an unreadable directory exits **0** with only a
   stderr warning (`warning: could not open directory 'reports/h10/':
   Permission denied`) and stages nothing (Test-verified, git 2.39.5); an
   exit-code-only gate would reproduce this bug's silent shape. `git add` on
   a wholly-gitignored directory exits 1 (`The following paths are ignored…`)
   — no allow-list path is ignored today (`git check-ignore -v` on all →
   none), so that would be a genuine BROKEN day, which is correct. `git add`
   on an existing empty directory exits 0 silently (no crit). The variable
   name `_stage_err` has no collision (`grep -n '\b_stage_err\b'` → none).
   Newline collapsing matters because `note()` (`:74`) appends to
   `$SUMMARY`, which is rendered with `printf "%b"` (`:623`) and embedded in
   an AppleScript string literal (`:637`); a raw newline there is a swallowed
   syntax error.
4. Why a loop and not "filter the array to existing paths, then one `git
   add`": per-path error attribution — the filtered form would drop the
   stderr check in 3(b) for the path that actually failed. Do not substitute
   it.
5. What `crit` does here, stated honestly: `crit()` (`:85`) increments
   `CRIT_COUNT` and sets `CRITICAL`, which flips the notification title
   (`:630-636`) and the final `RITUAL STATUS` line and exit code (`:648-654`)
   to BROKEN. It does NOT change `RITUAL_TERMINAL_STATUS`, which is computed
   at `:514-520` and already published at `:521-526` before Step 8 begins at
   `:528` (ordering pinned by `tests/test_daily_ritual_provenance.py:588-591`)
   — the same asymmetry the existing push-failure crit at `:604` carries. A
   staging failure therefore produces a BROKEN notification and exit 1 while
   the run-status receipt keeps that day's `OK`/`OK_STARVED`; that is the
   accepted shape for Step 8 failures. An absent optional path is `note`, so
   an `OK_STARVED` day stays `[DATA-STARVED]`.
6. Keep `:583-589` (the `git diff --cached --quiet` branch and the commit)
   byte-identical; the loop only changes what reaches the index.
7. **Exactly one textual `git add` site must remain.** The provenance test's
   mutation-verb registry (`tests/test_daily_ritual_provenance.py:131-142`,
   `"git add": (582,)` at `:136`) is asserted by exact line set at `:370` and
   closed over every verb family at `:374-376` (`ANY_MUTATION_VERB_RE`); a
   second `git add` line, or a `git add` inside a helper defined elsewhere,
   fails it. Write `git add -- "$p"` once, inline. (The reviewer ran the
   test's own regexes against a simulated patched script: one hit, closure
   clean — the loop shape satisfies the registry.)
8. Because the loop and the two markers add lines, every registered site
   AFTER `:582` shifts: update `MUTATION_VERB_SITES` for `git add`, `git
   commit` (`585`), `git fetch` (`595`), `git merge` (`596`), `git push`
   (`597`) and `restic backup` (`614`) to their new line numbers. The registry
   is a deliberate contract, so the PR body must quote the before/after
   numbers and the reason. (**Inference:** the reviewer's simulation landed
   them at 592 / 598 / 608 / 609 / 610 / 627; the executor measures the real
   values — do not copy these.)
9. Remove the `2>/dev/null` from the staging call. Stderr from `git add` is
   the evidence this bug hid; it now lands in the `crit` text, the log, and
   the summary.

### WP-B — Hermetic proof that one absent path cannot disable staging

1. Add tests to `tests/test_daily_ritual_provenance.py` that extract the
   `evidence staging` region with `_region()` (`:178-183`), define stub
   `note`/`crit` functions that append to a log file, define the variables
   the block reads (`RUN_DATE`, `FULL_AUTHORITY_RC`, `SUMMARY`, `CRITICAL`,
   `CRIT_COUNT`, `LOGDIR`, `REPO`), and run the block with
   `subprocess.run([zsh, "-c", script], …)` where `zsh = shutil.which("zsh")`
   and the test calls `self.skipTest("zsh is required")` when it is absent —
   the pattern already used for THIS script at `:596` and `:621-623`.
   `tools/daily_ritual.sh:1` is `#!/bin/zsh` and the LaunchAgent runs it
   under `/bin/zsh`; a bash harness would not test the production shell (the
   `/bin/bash` precedent at `tests/test_schwab_chain_schedule.py:115-116`
   targets a script that is also zsh and must not be propagated).
2. Hermetic fixture, required exactly: `tempfile.TemporaryDirectory()`; run
   the subprocess with `env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
   "GIT_CONFIG_SYSTEM": os.devnull, "HOME": tmpdir}`; in the temp repo set
   `user.name`, `user.email`, and `core.hooksPath=` (empty). Without this the
   temp repo inherits the operator's `core.hooksPath=~/.githooks` (an
   auto-push `post-commit` hook that writes `~/.local/log/autopush.log`,
   breaking the tempdir-only claim), and on CI — where no identity is
   configured — `git commit` at `:585` fails and the test silently exercises
   the `COMMIT FAILED` branch (`:588`). Offline, no network, no provider.
3. Fixture content: create every `DATA_TIER_PATHS` directory EXCEPT
   `reports/schwab_chains_intraday`, each with one committed file, commit a
   baseline, then append one line to `ledger/facts.log` and add one new file
   under `reports/h10/`. Set `FULL_AUTHORITY_RC=1` so only the data tier is
   staged.
4. Case 1 (the bug): the extracted block ends with `git commit` (`:585`), so
   the index is empty afterwards and must NOT be asserted on. Assert instead:
   `git show --name-only --format= HEAD` lists both changed files (staging
   survived the absent path); the stub log contains `allow-list path absent,
   not staged: reports/schwab_chains_intraday`; the stub log contains NO
   `CRITICAL:` line; `evidence: nothing new to persist` was NOT printed.
5. Case 2 (tracked path deleted): delete `ledger/facts.log` from the fixture
   (it is tracked in the baseline) → the stub log contains `CRITICAL:
   evidence: REQUIRED allow-list path absent: ledger/facts.log`, and HEAD
   still contains the other staged change.
6. Case 3 (real staging failure): make `reports/h10` unreadable (`chmod 000`,
   restored in `addCleanup`; decorate with `@unittest.skipIf(os.geteuid() ==
   0, "chmod-based denial is bypassed for root")`) → the stub log contains
   `CRITICAL: evidence: STAGING FAILED for reports/h10 — ` followed by git's
   warning EVEN THOUGH `git add` exited 0, and `git show --name-only
   --format= HEAD` does NOT list any `reports/h10/` file.
7. Case 4 (dedupe): `FULL_AUTHORITY_RC=0` with `ledger/facts.log` deleted →
   exactly ONE `REQUIRED allow-list path absent: ledger/facts.log` line.
8. Existing tests that must stay green unchanged except for the registry
   numbers in WP-A.8: `test_every_script_surface_is_classified`
   (`:346-376`), `test_durability_allow_list_is_tier_scoped` (`:640-658`,
   which uses `durability.index("git add --")` — the loop preserves that
   string), the ordering pins at `:233-241`, `:583-591`, `:745-757` (all
   outside the changed region), and `zsh -n tools/daily_ritual.sh`.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests        # offline; exit code is the verdict
uv run ruff check . && uv run pyright              # both exit 0
zsh -n tools/daily_ritual.sh                       # the production shell, not bash
uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'
```

CI runs `test_daily_ritual_provenance` in both the ubuntu quality job and the
macOS Shell Contracts job (`.github/workflows/ci.yml:38`, `:90`), both as a
non-root runner, so the chmod case executes there.

Manual proof (orchestrator/owner, ops checkout, read-only for the script): after
landing and syncing ops, the first ritual log must contain
`evidence: allow-list path absent, not staged: reports/schwab_chains_intraday`
followed by `evidence: committed` (or, on a day with nothing new, `nothing new
to persist` AFTER the absent-path note), and `git -C ~/options-validator-ops
status --short --untracked-files=no` must be empty after the run.

Every constraint above is labelled; anything Codex finds that contradicts a
citation is a STOP-and-report, not a workaround. The implementation PR starts
as a GitHub draft; the executor may not make it ready, merge, deploy, sync
`~/options-validator-ops` or `~/options-validator-research`, or touch
`ledger/`. Green checks are review evidence for the owner, not landing
authority. Landing before **Monday 2026-09-07 09:09 ET** is what stops the
next silent loss; until then the orchestrating session rescue-commits after
each run under the owner's 2026-09-06 approval pattern. Timing is the
owner's call.

# Codex brief 38 — Ritual evidence staging must survive an absent allow-list path

**Date:** 2026-09-06
**Author:** Claude (orchestrating session; ledger-durability diagnosis, 2026-09-06)
**Executor:** Codex (Sol, high reasoning — as briefs 07/37; owner may substitute at dispatch)
**Status:** DRAFT — pending independent adversarial review before hand-off
**Provenance:** file:line constraints are Repo-verified against origin/main
@f83428d unless a sentence carries its own label. "Test-verified" facts were
reproduced read-only in the ops execution checkout (`~/options-validator-ops`)
on 2026-09-06. Sentences labelled **Inference** are the author's reading of the
code, not a file fact.

## Why this exists (plain language)

Since 2026-09-03 the daily ritual has persisted NOTHING, while printing
"evidence: nothing new to persist" as if that were true. Cause, Test-verified:

1. PR #150 (`6484092`, merged 2026-09-02) added `reports/schwab_chains_intraday`
   to the ritual's evidence allow-list `DATA_TIER_PATHS`
   (`tools/daily_ritual.sh:561-562`). The intraday lane's install is an
   owner-gated staged step that has not happened, so that directory does not
   exist in the ops checkout (`ls`: MISSING; every other listed path exists).
2. Step 8 stages the whole list in ONE call —
   `git add -- "${GIT_ADD_PATHS[@]}" 2>/dev/null` (`:582`). `git add` aborts
   the entire command on any unmatched pathspec (reproduced:
   `fatal: pathspec 'reports/schwab_chains_intraday' did not match any files`)
   and stages nothing; the `2>/dev/null` discards the only evidence of that.
3. `git diff --cached --quiet` (`:583`) then sees an empty index and the script
   prints `evidence: nothing new to persist` (`:584`). The 2026-09-03 and
   2026-09-04 ritual logs both carry that line; the 2026-09-02 run (before
   #150 reached ops) printed `evidence: committed`.

Impact, Test-verified: a dry run of the same staging with only the existing
paths listed 36 files / 6,880 lines that had accumulated on one disk —
`ledger/facts.log` appends (SCHWAB_CHAIN_CAPTURE 09-02/09-03, DATA_PULL and
DATA_PULL_OHLCV 09-03/09-04), the 2026-09-02 and 2026-09-03 Schwab capture
receipts (manifest, preclose, quote-age sidecar), H10b observations, the
pick-tracker event log, two H10 watch receipts, a ritual run-status receipt.
The owner-directed rescue commit `f83428d` persisted them on 2026-09-06. The
script is unchanged, so the next ritual (Tue 2026-09-08 09:09 ET) will fail
the same way. This brief fixes the staging so one absent allow-list path can
never again silently disable durability for every other path.

## Scope

**IN:** `tools/daily_ritual.sh` Step 8 staging only (`:561-590`), and
`tests/test_daily_ritual_provenance.py` (the mutation-verb registry it pins,
plus one new hermetic test).

**OUT (hard):**
- No change to the allow-list CONTENT (`DATA_TIER_PATHS` `:561-562`,
  `FULL_TIER_PATHS` `:571-573`): `reports/schwab_chains_intraday` stays listed —
  it is correct the day the lane is installed.
- No change to the commit messages (`:564-569`, `:575-580`), the tier logic
  (`:570`, `FULL_AUTHORITY_RC`), the push function (`:594-597`), the restic
  snapshot (`:614`), or any `note`/`crit` string that exists today.
- No ledger write, no plist/launchd change, no ops-checkout mutation, no
  change to `PYTHON_DASH_C_CLASSIFICATION` sites (`tests/test_daily_ritual_provenance.py:96-108`;
  all nine are before `:561` and are unaffected by a change below it).
- No second `git add` textual site (see WP-A step 3).

## Work packages

### WP-A — Stage each allow-list path on its own; never discard the error

1. Replace the single call at `:582` with a loop over `"${GIT_ADD_PATHS[@]}"`
   that, for each path: (a) if the path does not exist, prints
   `note "evidence: allow-list path absent, not staged: $p"` — except for
   the two paths that must always exist, `ledger/facts.log` and
   `reports/ritual`, whose absence is
   `crit "evidence: REQUIRED allow-list path absent: $p"`; (b) if it exists,
   runs `git add -- "$p"` capturing stderr into a variable, and on non-zero
   exit prints `crit "evidence: STAGING FAILED for $p — $err"`. A real
   staging failure is a real break (the silent version of it is this bug),
   so it is `crit`, which flips the terminal status to BROKEN through the
   existing counter logic (`:85` `crit()`; brief 11 §6.4). An absent optional
   path is expected while a lane is uninstalled, so it is `note`.
2. Keep `:583-589` (the `git diff --cached --quiet` branch and the commit)
   byte-identical; the loop only changes what reaches the index.
3. **Exactly one textual `git add` site must remain.** The provenance test's
   mutation-verb registry (`tests/test_daily_ritual_provenance.py:131-142`,
   `"git add": (582,)`) is asserted by exact line set at `:370` and closed
   over every verb family at `:372-375` (`ANY_MUTATION_VERB_RE`); a second
   `git add` line, or a `git add` inside a helper defined elsewhere, fails
   it. Put the loop inline at the same place; write `git add -- "$p"` once.
4. Because the loop adds lines, every registered site AFTER `:582` shifts:
   update `MUTATION_VERB_SITES` for `git add`, `git commit` (`585`),
   `git fetch` (`595`), `git merge` (`596`), `git push` (`597`) and
   `restic backup` (`614`) to their new line numbers — the registry is a
   deliberate contract, so the PR body must quote the before/after line
   numbers and the reason (**Inference:** the shift is N lines where N is
   the loop's added line count; the executor measures it).
5. Remove the `2>/dev/null` from the staging call. Stderr from `git add` is
   the evidence this bug hid; it now lands in the `crit` text and therefore
   in the log and the summary.

### WP-B — Hermetic proof that one absent path cannot disable staging

1. Add one test to `tests/test_daily_ritual_provenance.py` that extracts the
   Step 8 staging block from `tools/daily_ritual.sh` (from the
   `DATA_TIER_PATHS=(` line through the `git diff --cached --quiet` branch —
   bound it by two comment markers added in WP-A, e.g.
   `# ---- evidence staging: begin ----` / `# ---- evidence staging: end ----`,
   so the test never depends on line numbers), defines stub `note`/`crit`
   functions that append to a log, and runs the block with
   `subprocess.run(["/bin/bash", "-c", script], ...)` inside a temporary git
   repository — the pattern already used at
   `tests/test_schwab_chain_schedule.py:115-116`. Offline, no network, no
   provider, writes only under `tempfile.TemporaryDirectory()`.
2. Fixture: create every `DATA_TIER_PATHS` directory EXCEPT
   `reports/schwab_chains_intraday`, commit a baseline, then append one line
   to `ledger/facts.log` and add one new file under `reports/h10/`. Set
   `FULL_AUTHORITY_RC=1` so only the data tier is staged.
3. Assert: `git diff --cached --name-only` in the temp repo lists both
   changed files (staging survived the absent path); the stub log contains
   `allow-list path absent, not staged: reports/schwab_chains_intraday`;
   the stub log contains NO `CRITICAL:` line; and `evidence: nothing new to
   persist` was NOT printed.
4. A second case: delete `ledger/facts.log` from the fixture → the stub log
   contains `CRITICAL: evidence: REQUIRED allow-list path absent:
   ledger/facts.log`.
5. A third case: make `reports/h10` unreadable (chmod 000) so `git add`
   fails → `CRITICAL: evidence: STAGING FAILED for reports/h10 — ` followed
   by git's own message; restore permissions in `addCleanup`.
6. Existing tests that must stay green unchanged except for the registry
   numbers in WP-A.4: `test_every_script_surface_is_classified` (`:346-375`),
   the ordering pins at `:233-241`, `:583-591`, `:745-757` (all outside the
   changed region), and `bash -n tools/daily_ritual.sh`.

## Acceptance / verification

```bash
uv run python -m unittest discover -s tests        # offline; exit code is the verdict
uv run ruff check . && uv run pyright              # both exit 0
bash -n tools/daily_ritual.sh                      # syntax
uv run python -m unittest discover -s tests -p 'test_daily_ritual_provenance.py'
```

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
authority. Landing before Tuesday 2026-09-08 09:09 ET is what stops the next
silent loss; that timing is the owner's call.

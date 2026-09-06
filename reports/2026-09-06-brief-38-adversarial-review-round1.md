# Brief 38 — independent adversarial review, round 1 (2026-09-06)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; no file edited in either checkout).
**Target:** `docs/superpowers/plans/2026-09-06-38-ritual-evidence-staging-codex-brief.md` rev 1 @ `f24e7e5`.
**Base:** `origin/main` @ `f83428d`.
**Method (reviewer's words):** every diagnostic claim reproduced in the ops checkout; every citation opened; the proposed loop simulated into a copy of the script and run under zsh in a temp repo; the provenance test's own regexes run against the simulated script.

## Verdict: FAIL

Diagnosis sound and fully reproduced; the fix design had two unsatisfiable steps, one false mechanism claim, the wrong shell, and a deadline one ritual too late. All 19 findings applied in rev 2 (same session).

## Findings (severity · disposition in rev 2)

1. **BLOCKER** · `git add` on an unreadable directory exits 0 with a stderr warning and stages nothing (Test-verified, git 2.39.5); an exit-code-only gate reproduces the silent shape. → crit on non-zero exit OR non-empty stderr; WP-B.5 asserts the crit fires even though rc = 0 and that no `reports/h10/` file reached HEAD.
2. **BLOCKER** · the extracted block ends with `git commit` (`:585`), so `git diff --cached` is empty afterwards; WP-B.3's index assertion was unsatisfiable. → assert on `git show --name-only --format= HEAD`.
3. **HIGH** · script is `#!/bin/zsh` and the LaunchAgent runs `/bin/zsh`; the brief specified `/bin/bash` (the cited precedent `tests/test_schwab_chain_schedule.py:115-116` is itself wrong). → `zsh = shutil.which("zsh")` + `skipTest`, per `tests/test_daily_ritual_provenance.py:596,621-623`.
4. **HIGH** · a Step-8 `crit` cannot flip `RITUAL_TERMINAL_STATUS` (computed `:514-520`, published `:521-526`, before Step 8 at `:528`; pinned by `tests/…:588-591`); it flips the notification title (`:630-636`) and the final line/exit code (`:648-654`), like the existing push-failure crit at `:604`. → mechanism restated honestly.
5. **HIGH** · the LaunchAgent's `StartCalendarInterval` is Weekday 1–5 with no market-calendar filter; the next silent loss is **Mon 2026-09-07 09:09 ET** (Labor Day), not Tuesday. → both dates corrected.
6. **HIGH** · the hard-coded REQUIRED pair was arbitrary; every allow-list path is tracked on `origin/main` except `reports/schwab_chains_intraday` (0 files). → tracked-ness rule: absent AND tracked in HEAD (`git cat-file -e "HEAD:$p"`) → crit; absent AND untracked → note.
7. **HIGH** · fixture not hermetic: a bare `git init` inherits `core.hooksPath=~/.githooks` (auto-push `post-commit` writing `~/.local/log/autopush.log`) and CI has no git identity, so `git commit` would fail and the test prove nothing. → env isolation (`GIT_CONFIG_GLOBAL`/`GIT_CONFIG_SYSTEM`=devnull, `HOME`=tmpdir), repo-local identity, `core.hooksPath=` empty.
8. **MEDIUM** · `ledger/facts.log` is in `GIT_ADD_PATHS` twice on full-authority days (`:562`, `:571`+`:574`) → two crits, `CRIT_COUNT` +2. → `typeset -U GIT_ADD_PATHS`; a `FULL_AUTHORITY_RC=0` test case.
9. **MEDIUM** · marker convention must match `# ---- <name> ----` / `# ---- end <name> ----` so `_region()` (`tests/…:178-183`) can address it. → fixed.
10. **MEDIUM** · WP-A never told the executor to add the markers; the shift count omitted them. → fixed.
11. **MEDIUM** · multi-line git stderr would corrupt `$SUMMARY` (`printf "%b"` `:623`) and the AppleScript literal (`:637`). → collapse newlines before `crit`.
12. **MEDIUM** · `git add` on a wholly-ignored directory exits 1 — a prospective BROKEN-every-day trap. → named in the brief.
13. **MEDIUM** · chmod-based denial is bypassed at euid 0. → `skipIf(os.geteuid() == 0)`.
14. **MEDIUM** · a second allow-list exists (`tools/schwab_chain_intraday_capture.sh:74-79` `EVIDENCE_ALLOW`, an alignment guard). → fenced in OUT.
15. **LOW** · cite `:346-376` / `:374-376`. → fixed.
16. **LOW** · `zsh -n`, not `bash -n`. → fixed.
17. **LOW** · a wholly-deleted tracked path's deletion is no longer staged by the loop. → stated as intentional (append-only ledger).
18. **LOW** · no single-call form is safe (`--ignore-errors`, `:(glob)`, `:(literal)` all exit 128); loop chosen for per-path attribution. → recorded so the loop is not "simplified" back.
19. **LOW** · name the variable `_stage_err`; no collision today. → fixed.

## Verified correct by the reviewer (attacked and survived)

Dry run in ops reproduces `fatal: pathspec 'reports/schwab_chains_intraday' did not match any files` (exit 128, nothing staged); all ten other paths exist; the #150 intraday plist is not installed; ritual logs 09-03/09-04 say "nothing new to persist", 09-02 says "committed"; `6484092` reached ops at 20:18 on 09-02, after that morning's evidence commit; `f83428d` carries 36 files / 6,880 insertions. The proposed loop satisfies the mutation-verb registry (exactly one `git add` line; simulated sites git add 592, commit 598, fetch 608, merge 609, push 610, restic 627; `ANY_MUTATION_VERB_RE` closure clean; markers excluded by `_code_lines`). `git add` on an empty existing directory exits 0; no allow-list path is gitignored; `:582` is the only `git add` in `tools/` and `.agents/`; `test_durability_allow_list_is_tier_scoped` (`:640-658`) survives. Header, body order, OUT clauses, draft-PR clause, and registry row 38 all correct. Baseline: `test_daily_ritual_provenance` 43 tests OK.

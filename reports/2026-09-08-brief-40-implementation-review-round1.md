# Brief 40 — independent adversarial IMPLEMENTATION review, round 1 (2026-09-08)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only on repo state; nothing created, edited, staged, committed or deleted in any checkout; script exercised only in a throwaway temp git repo).
**Target:** PR #161 "Brief 40: H7 activation-day Schwab receipt chain", head `49e3114`, branch `codex/brief-40-activation-day-chain` (draft), worktree `.tmp/worktrees/brief40`. Base `origin/main` @ `7af04bd`.
**Brief:** rev 3 `docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md` + receipts `reports/2026-09-08-brief-40-adversarial-review-round{1,2}.md`.
**Orchestrator pre-checks (Run-verified before dispatch):** PR #161 CI on `49e3114` = Offline Quality Gates FAILURE + macOS Shell Contracts FAILURE (2 failures each, both in `tests/test_shell_banner_guard.py`; Secret Scan pass); `git diff origin/main --stat -- reports ledger data config.py` empty; the four relocated synthetic fixtures are at `/private/tmp/brief40-synthetic-red-fixtures/` (dated 2026-08-10 content, written 14:40); empty dirs `reports/h7_data_gate/nested/…` remain in the worktree only; `tools/h7_forward_backup.py:418` whole-universe rule pre-exists on `main` at `:376`.
**Method (reviewer's words):** whole diff (11 files) read; the WP-A tool, WP-B script and both new test modules read end to end; `test_shell_banner_guard` (FAILED, 2), `test_h7_schwab_data_gate_receipt` (14 OK), `test_h7_activation_day` (20 OK), `test_schwab_chain_capture` (26 OK), `test_ops_alignment_check` + `test_schwab_chain_intraday` + `test_h7_backup` (exit 0), `ruff check .` (0), `ruff format --check` (0), `zsh -n` (0) executed; `feasibility_source_closure()` recomputed (50, `== FEASIBILITY_SOURCE_PATHS`) and intersected with the changed files (empty); `tools/h7_forward_backup.py` AST-compared to `origin/main`; the script's `CONTEXT` python snippet executed read-only; `/tmp/ci161.log` read.

## Verdict: FAIL — NOT READY

All 26 R-tags are closed in substance, scope discipline is clean, and the three WP test suites are strong and hermetic. But the brief's first mandatory gate (`unittest discover` exit 0) is red at the delivered commit, and the PR body asserts the opposite as a specific verified fact ("exit 0, 3904 tests"). One fix round should close it. Finding 2 is an activation-day blocker that is NOT Codex's to fix — owner ruling required.

## Findings

1. **BLOCKER** · suite red at `49e3114`; PR-body "exit 0, 3904 tests" is false. Run-verified locally and in both CI jobs: `test_no_pipe_fail_relied_on_anywhere` (script sets `setopt PIPE_FAIL` at `tools/h7_activation_day.sh:3`; the guard's reason-(a) allowlist assumes it unset) and `test_every_python_capture_is_filtered_or_allowlisted` (six raw `$(...)` python captures at `:94, 118, 140, 197, 205, 229`). The guard is a static scan of `git ls-files '*.sh'`, so it fails deterministically the moment the script exists in this form; 3904 matches CI's total, so the run was real and its result misreported. **Fix:** (a) delete `setopt PIPE_FAIL` — no pipeline's exit status is relied on (each `print … | sed | tail` extraction is checked for emptiness afterwards at `:114, :203, :239`; `SOURCE_RC`/`DATA_RC` at `:198/:230` are plain substitutions); (b) add six justified `ALLOWLIST` entries to `tests/test_shell_banner_guard.py` — five reason (a) (`CONTEXT :94→:109-113`, `FEASIBILITY_STATE :140→:156`, `HEALTH :205→:218`, `SOURCE_OUT :197→:201`, `DATA_OUT :229→:238`), one reason (b) (`TOKEN_OUT :118`, matched by `case` globs only). The guard verifies reason-(a) entries by finding a nearby ANCHORED derivation, so finding 4 must land with this. Inline anchored filters inside the `$(...)` are not viable for `SOURCE_OUT`/`DATA_OUT` (a pipe inside the substitution destroys the exit code the script must read). Editing `tests/test_shell_banner_guard.py` is outside the brief's Scope IN; **orchestrator ruling: authorized for the fix round** — it is the guard's own sanctioned route and a test for behaviour this brief introduces.
2. **HIGH (activation-day blocker; owner ruling, not a Codex edit)** · `tools/h7_forward_backup.py:403-405` (this PR) makes the restore verifier scan `reports/h7_data_gate_schwab/*/receipts/*.json`, and the pre-existing rule at `:416-421` marks any data-gate receipt whose `whole_universe_verdict != "GO"` or `go_count != 15` as `stale scope`, so `verification.ok` is false (`:461`). Scenario: nine included GO, one EXCLUDED name NO_GO on a data-content check (`CLOSE_STALE`, `CHAIN_EMPTY`, `CHAIN_CROSSED_MARKET`, `CHAIN_NONFINITE`, `CHAIN_DUPLICATE_CONTRACT`, `CHAIN_NEGATIVE_LIQUIDITY_FIELD`, `h7_data_gate.py:160-354` — ordinary on thin names like IREN/USAR/CRWV). WP-A exits 0 under D-5, writes the receipt, `h7_activation_day.sh:245` refuses on restore-check, and even if it did not the door refuses at F3. Undisclosed second-order effect: the receipt is immutable and the namespace is now in `BACKUP_PATHS`, so one NO_GO Schwab receipt makes **every future restore drill fail forever** with `stale scope`. The round-1 reviewer's 15/15 GO on the 2026-09-03 package is one day of evidence. Options: (i) successor brief making the rule scope-aware for the Schwab evidence mode (touches acceptance logic — own review); (ii) in-scope now: revert only the restore-scan half of WP-A.11 (`:403-405`), keep the `BACKUP_PATHS` entry (`data_gates > 0` still satisfied by legacy receipts) — reverses part of round-1 finding 5, needs an amendment. **Do not activate until ruled.** New test `tests/test_h7_schwab_data_gate_receipt.py:418` documents only the GO case.
3. **MEDIUM** · a FOURTH `EVIDENCE_ALLOW` copy at `tools/h7_activation_day.sh:23-29`, byte-identical today (md5 `4a717e66…` for all four) but unpinned; `commit_evidence` (`:169`) validates against its own copy, so a later narrowing of the canonical list reproduces the R2-3 lost-capture failure. → pin it to the capture wrapper's list in `tests/test_h7_activation_day.py:287`.
4. **MEDIUM** · `tools/h7_activation_day.sh:201` parses the source-health receipt path with an unanchored `sed -n 's/.*receipt=\([^;]*\);.*/\1/p'` over raw stdout that carries import banners (`LumiBot v4.5.63 starting`, `.env file loaded`) — the bug class the banner guard exists for. Real line: `summary: N/15 healthy; receipt=<path>; exit …` (`h7_source_health.py:290-292`). → `sed -n 's/^summary: .*receipt=\([^;]*\);.*/\1/p'` (also satisfies the guard's `ANCHORED_FILTER_RE`). `DATA` at `:238` is already anchored.
5. **LOW** · relocation of the four synthetic RED-test files is honest and complete (tracked receipts unchanged; test now uses temp cwd, `tests/test_h7_schwab_data_gate_receipt.py:67,371`); residue = empty dirs `reports/h7_data_gate/nested/h7-forward-15-v1/receipts` and `reports/h7_data_gate/h7-forward-15-v1/receipts` in the worktree only, git-invisible. → `rmdir -p` before worktree removal.
6. **LOW** · `--stage-routine-evidence` commit (`:185-187`) runs before the `tee` log redirect (`:191`), so the prerequisite `data(ritual)` commit leaves no trace in the run log. → move the redirect above it.
7. **LOW** · `tools/h7_schwab_data_gate_receipt.py:19` imports `data.cache_runner` (grpc + ThetaData adapter, 0.76 s, R2-9) at module level; WP-C correctly made it function-local. → move inside `main()` beside its use at `:101`.
8. **LOW** · PR body's "Independent final spec/quality review: PASS" has no artifact anywhere. → attach the receipt or drop the sentence; correct the validation section.

## R-tag closure table

| Tag | Status | Evidence |
|---|---|---|
| R1-1 | CLOSED | `…receipt.py:33,43,123-129` flat chain dir; fixture mirrors |
| R1-2 | CLOSED | `h7_activation_day.sh:82` (untracked counted), `:163-184`, `:269`; tests `:98,:162,:170` |
| R1-3 | CLOSED | `…receipt.py:137` build then `:146` quote-age; raw-result-rejected test present |
| R1-4 | CLOSED | `:241` prints D-6 line; `h7_watch.py` untouched |
| R1-5 | CLOSED (see finding 2) | `…receipt.py:36,92-94,183-184`; `h7_forward_backup.py` BACKUP_PATHS + `:403-405` |
| R1-6 | CLOSED | `:116-117`; `test_missing_package_refuses_before_producers` |
| R1-7 | CLOSED | `:140-161`; tests `:240,:264` |
| R1-8 | CLOSED | `:197-228`; `test_unhealthy_included_stops_even_source_exit_zero` |
| R1-9 | CLOSED | `schwab_chain_capture.py:391`; exact-stdout test |
| R1-10 | CLOSED | `:390-393` precedes `:397`; `default_client.assert_not_called()` |
| R1-11 | CLOSED | `:270-284`; test `:195-198` |
| R1-12 | CLOSED | `:4,:12,:19,:58-65`; no plist parsing; defaults to `$HOME/options-validator-ops` (stricter than brief, defensible) |
| R1-13 | N/A (brief) | — |
| R1-14 | CLOSED | `…receipt.py:142` no-arg cohort, `:76-81` both verdicts, `:189-197` exits |
| R1-15 | CLOSED | `…receipt.py:101` assert; 09-08⇒09-04 test |
| R2-1 | CLOSED (see finding 3) | three wrapper diffs byte-identical; both equality tests green |
| R2-2 | CLOSED | `:256-267` index, `:269` commit; commit-diff test |
| R2-3 | CLOSED | `ROUTINE_ALLOW :66-67`; intersection test; `closes_receipts` refusal test |
| R2-4 | CLOSED | `…receipt.py:192-196`; `:232-237`; two tests |
| R2-5 | CLOSED | `:148`; `test_feasibility_reuse_checks_both_hashes_not_code_sha` |
| R2-6 | CLOSED | `:281,:304-305` |
| R2-7 | CLOSED | `:308` |
| R2-8 | CLOSED | `…receipt.py:142`; `:101,:214` |
| R2-9 | CLOSED (see finding 7) | `schwab_chain_capture.py:390-391` |
| R2-10 | N/A (brief) | — |
| R2-11 | CLOSED | `docs/h7-forward-operations.md` final paragraph |

**Scope OUT: clean.** Closure ∩ changed files = ∅; no `reports/ledger/data/config.py` diff; no validator acceptance logic, `data/ritual_authority.py`, `data/earnings/*`, or `h7_watch.py` edit.

## Verified correct by the reviewer (attacked and survived)

`h7_forward_backup.py` format-churn claim TRUE (AST: 0 removals, 37 additions, all inside the two authorized changes). WP-A: flat chain dir; receipt built before quote-age; `validate_durable_receipt` re-run before any path is created; both immutable destinations preflighted as a pair; legacy namespace refused via `resolve().is_relative_to()`; exit 2 writes nothing (five tests); `immutable receipt <path>` sentinel. Printed activation command valid against `h7_schwab_manual_activate._parser()` (all 13 owner flags exist by name; `--excluded-reason` emitted per excluded name; no owner value filled). Token-age `case` matches `schwab_token_age.py:96,:107,:117` exactly, fail-closed default. `git status --porcelain` byte-identical to `_code_state()`. `.env` handling proven safe by `test_dotenv_unrelated_lines_never_execute_or_leak`. Harness strips inherited `GIT_*` (brief-38 lesson). One `git add` loop + one commit, no push, no activation, stderr checked per add (pipefail not load-bearing). Committed-path assertion reads the wrapper's list, not the script's. WP-C: session before `_default_client()`, function-local import, exact line, Labor Day + Good Friday, real-zsh wrapper test proves auth never touched, `CALENDAR_UNAVAILABLE` composes the wrapper alert. 2026-09-07 package byte-identical. `docs/h7-forward-operations.md` accurate, including the first-order restore-verifier coupling. PR-body claims verified: closure listing, 14/20/26 focused tests, ruff/format/zsh -n exit 0, no operational write, fixture relocation.

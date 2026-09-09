# Brief 40 — independent adversarial IMPLEMENTATION review, round 2 (fix round 1) — 2026-09-09

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; nothing created, edited, staged, committed or deleted in any checkout).
**Target:** PR #161 (draft), head `de640b9` (fix commit on `49e3114`) on `codex/brief-40-activation-day-chain`, worktree `.tmp/worktrees/brief40`. Base `origin/main` @ `acaf216`.
**Inputs:** `reports/2026-09-08-brief-40-implementation-review-round1.md` (8 findings + owner ruling), Brief 40 Amendment A1, `git diff 49e3114 de640b9` (7 files, +58/−57).
**Orchestrator pre-checks (Run-verified 2026-09-09 00:17 ET):** CI on `de640b9` green on all three jobs; `setopt PIPE_FAIL` absent; `tools/h7_forward_backup.py` retains only the `BACKUP_PATHS` entry (`:69`); empty legacy dirs gone; worktree clean.

## Verdict: PASS

Every round-1 finding and Amendment A1 is closed in substance with the minimum edit, and the fix survived attack. Run-verified: full offline suite `Ran 3905 tests … OK (skipped=5)`, exit 0; `ruff check` 0; `pyright` 0/0/0; `ruff format --check` clean on all touched files; `zsh -n` exit 0; CI green. The two plausible regressions — a loosened banner guard, and a pipefail removal changing what some `$?`/`||` reads — both held: guard regexes and every pre-existing allowlist entry byte-identical, six new entries scoped to `tools/h7_activation_day.sh` mapping one-to-one onto its six capture spans, and no pipeline in the script has its exit status consumed. Restore-scan revert is AST-exact (five added nodes = the `BACKUP_PATHS` entry, zero removals).

## Findings (no blocker, no HIGH, no MEDIUM)

1. **NIT (forward-looking)** · `tests/test_shell_banner_guard.py:106-136` — allowlist matching is `substring in span_text` and the new substrings are bare variable prefixes (`HEALTH=`, `CONTEXT=`, `DATA_OUT=`…); a future capture in the same file named e.g. `SOURCE_HEALTH=` would be silently covered. Not live today (instrumented scan: 6 captures, each matched by exactly one entry). Same property as the pre-existing `CAP_OUT=` entries. Optional fix: anchor with a leading newline or match on `_ASSIGN_PREFIX_RE`.
2. **NIT (cosmetic)** · `tests/test_h7_activation_day.py:303-306` — `allowed` and `capture_allowed` are the same regex on the same text; one is redundant.

## Closure table

| Item | Status | Evidence |
|---|---|---|
| F1 pipefail + 6 allowlist entries | CLOSED | `setopt PIPE_FAIL` removed; entries at `tests/test_shell_banner_guard.py:106-136` (5× reason (a): CONTEXT `:93→:108-112`, FEASIBILITY_STATE `:139→:155`, HEALTH `:204→:217`, SOURCE_OUT `:196→:200`, DATA_OUT `:228→:237`; 1× reason (b): TOKEN_OUT `:117`, `case` globs only); guard 4 tests OK. Every pipeline (`:108-112,:155,:200,:217,:237`) feeds a value checked afterwards; `SOURCE_RC`/`DATA_RC` and every `|| refuse` sit on un-piped substitutions. |
| F3 EVIDENCE_ALLOW pin | CLOSED | `tests/test_h7_activation_day.py:304-306` compares the script against `tools/schwab_chain_capture.sh` (not self); star topology with `test_ops_alignment_check.py:310-320` and `test_schwab_chain_intraday.py:440,523` ties all four copies. |
| F4 anchored sed | CLOSED | `:200` `sed -n 's/^summary: .*receipt=\([^;]*\);.*/\1/p'` matches `h7_source_health.py:290-292`; receipt-write-failure path prints no `summary:` → empty → refuse at `:202`. |
| F5 empty legacy dirs | CLOSED (+ correction) | no empty dirs; `nested/` gone. **Round-1 receipt correction:** `reports/h7_data_gate/h7-forward-15-v1/receipts` was never empty — it holds 8 tracked files; Codex's dispute is Run-verified true. |
| F6 log redirect ordering | CLOSED | `:184-190` redirect precedes the `data(ritual)` commit and follows every read-only precondition; `.tmp/` gitignored (real `.gitignore:57`, fixture `:44`); new ordering test + two-commit stage-routine test pass. |
| F7 function-local import | CLOSED | `tools/h7_schwab_data_gate_receipt.py:100` inside `main()`. |
| F8 PR body | CLOSED | "Independent review: PASS" sentence gone, replaced by an explicit non-assertion; every pasted number reproduced (3905 / OK skipped=5 / exit 0; ruff 0; pyright 0/0/0); trailing fixture JSON in the "last five lines" is genuine buffered output. |
| A1 restore-scan revert | CLOSED, exactly | AST diff vs base = 5 additions (`BACKUP_PATHS` entry), zero removals; scan block gone; acceptance test replaced by `test_backup_paths_include_schwab_namespace`; `docs/h7-forward-operations.md:216-221` states Schwab receipts are backed up but not scanned or validated by restore drills. |

## Verified correct (attacked and survived)

Guard module semantic diff `49e3114`→`de640b9`: added = the six entries, removed = none, reason changes on shared entries = none, all three scanner regexes identical. `TOKEN_OUT` `case` globs are unanchored but bounded (EXPIRED tested first, default refuses). Scope OUT clean: `git diff 7af04bd de640b9 -- reports ledger data config.py` empty; 12 files touched, none in `feasibility_source_closure()`. Seven modules green (`test_h7_activation_day` 21 OK, `test_h7_schwab_data_gate_receipt` 14 OK, `test_h7_backup` 24 OK, `test_ops_alignment_check` 15 OK, plus intraday, capture, guard). CI skip-count gap (95 Linux vs 5 local) is environmental. PR still draft; no merge, no ops sync, no activation performed by Codex. Not independently verified: the body's `irreplaceable_data_guard.py verify → exit 0` line and the `rmdir` transcript (end state consistent). D-6 remains open by design.

**Recommendation:** ready for the merge decision.

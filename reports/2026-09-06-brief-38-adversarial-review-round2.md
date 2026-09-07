# Brief 38 — independent adversarial review, round 2 (2026-09-06)

**Reviewer:** Opus subagent dispatched by the orchestrating Claude session (read-only; nothing edited in either checkout). A first round-2 attempt was cut off by a process exit; this is the completed relaunch.
**Target:** brief rev 2 @ `7a37104`. **Base:** `origin/main` @ `f83428d`. git 2.39.5, zsh 5.9.
**Method (reviewer's words):** every citation opened; all 19 round-1 findings checked against the rev-2 text; WP-A steps 1–9 implemented into a copy of `tools/daily_ritual.sh` and WP-B cases 1–4 executed under zsh in hermetic temp repos; the provenance test module's own regexes run against the patched script.

## Verdict: PASS WITH FIXES

The design survived simulation intact: all four WP-B cases produced the brief's asserted strings verbatim, `zsh -n` passed, the mutation-verb registry closure stayed clean (one `git add` site; `git cat-file` matches no mutation family), and every round-1 finding was genuinely applied (7 and 14 partially — completed below). Fourteen wording-only fixes, all applied in rev 3 by the orchestrating session.

## Findings (severity · disposition in rev 3)

1. **BLOCKER (wording)** · WP-B.2 specified no `cwd`; bare `git` commands in the extracted block would run in the REAL checkout under `unittest discover`. → `cwd=<temp repo>` required; `HOME` moved outside the work tree.
2. **HIGH** · "landing before Monday 09:09" over-claims: nothing syncs ops before 09:09 (`tools/ops_alignment_check.sh:6` never pulls; `repo-reconcile` 09:20 treats ops read-only; the ritual's merge `:596` runs after Step 8). → Landing AND ff-merging ops before Monday 09:09, else the fix is live from Tuesday.
3. **MEDIUM** · `EVIDENCE_ALLOW` exists in three byte-identical copies (`ops_alignment_check.sh:62-67`, `schwab_chain_capture.sh:65-70`, `schwab_chain_intraday_capture.sh:73-78`), all omitting `reports/pick_tracker` and `reports/closes_receipts`. → All three fenced; pre-existing divergence recorded as a follow-up.
4. **MEDIUM** · `tests/test_closes_receipt.py:175-186` and `tests/test_schwab_chain_intraday.py:515-519` parse the same block (both survive); `test_closes_receipt.py:158-160` docstring is stale. → Named as green-unchanged, not in scope; docstring a follow-up.
5. **MEDIUM** · stub `crit` output format unspecified while cases assert `CRITICAL:`. → Stub must write `CRITICAL: $1`.
6. **MEDIUM** · `TemporaryDirectory()` is load-bearing (its cleanup resets permissions; `shutil.rmtree` raises on the chmod-000 dir). → Stated; the `mkdtemp` precedent at `:1069-1070` forbidden here.
7. **MEDIUM** · `HOME` pointed inside the work tree. → Covered by 1.
8. **LOW** · `rc` and `p` collision claims missing. → Added (none found).
9. **LOW** · `printf "%b"` residual with C-quoted paths. → Recorded as accepted residual.
10. **LOW** · `typeset -U` placement ambiguous. → Immediately after `:574` inside the branch; `-U` dedupes existing contents (Test-verified).
11. **LOW** · cites `:528`→`:529`, `:561-590`→`:561-589`, `:588-591`→`:589-591`. → Fixed.
12. **LOW** · second simulation landed different shift numbers (592/601/612/613/614/631). → Recorded; "measure, do not copy".
13. **LOW** · finding IDs not cited per step (skill rule). → Steps tagged R1-n / R2-n.
14. **LOW** · `.agents/hooks/block_ledger_edits.py:56-64` blocks shell reproduction of case 2. → Note added: mutate the fixture from inside the test process.

## Simulation summary (reviewer's transcript, trimmed)

`zsh -n` on the patched copy: exit 0. `typeset -U` dedupes an already-built array in both placements. `$?` after `_stage_err="$(git add … 2>&1)"` reflects git's status; `${var//$'\n'/ }` collapses newlines. `git cat-file -e HEAD:<dir>` → 0 for tracked trees (with or without trailing slash), 128 for absent paths. `git add` edge cases: chmod-000 dir rc 0 + 2-line warning + nothing staged; empty dir rc 0; ignored dir rc 1; unmatched rc 128. Provenance regexes on the patched script: `git add` (592,), commit (601,), fetch (612,), merge (613,), push (614,), restic (631,); closure clean; `_region('evidence staging')` resolves; `test_durability_allow_list_is_tier_scoped` passes. WP-B cases 1–4 (hermetic temp repo, `cwd` set, config isolated, ledger path renamed for the shell hook): every asserted string appeared verbatim; case 3's crit fired at rc 0; case 4 produced exactly one REQUIRED line.

## Verified correct

Diagnosis fully reproduced (#150 reached ops 2026-09-02 20:18:32, after that morning's `22c4888`; 09-03/09-04 "nothing new to persist"; 09-02 "committed"; intraday plist not installed; `f83428d` = 36 files / 6,880 insertions). Calendar: 09-05 Saturday, 09-07 Monday; plist Weekday 1–5 09:09, no market-calendar filter; exactly two runs lost. Every rev-2 citation into `tools/daily_ritual.sh` and `tests/test_daily_ritual_provenance.py` exact (three ±1 drifts fixed above). CI: `.github/workflows/ci.yml:38` (ubuntu full discovery) and `:90` (macOS Shell Contracts lists this module), both non-root. All 17 allow-list paths tracked on `origin/main` except `reports/schwab_chains_intraday`; none gitignored. Baseline `test_daily_ritual_provenance`: 43 tests OK. No ledger write, registration, authority flip, frozen-number change, plist change, ops mutation, or live-order path anywhere in the brief; draft-PR clause present; registry row 38 tracked and highest on disk; header/body order per the skill.

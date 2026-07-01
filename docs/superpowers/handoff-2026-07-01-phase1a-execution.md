# Handoff — Phase 1A execution (mid-flight, Tasks 1–8 done, 9–16 remain)

> Paste this whole file as the opening context of a NEW session to continue the
> Phase-1A build without losing anything. It is self-contained. Written
> 2026-07-01 by the Claude session that executed Tasks 1–8.

## 0. One-paragraph project frame

Repo `/Users/carsynstephenson/Downloads/options-validator` is an options-strategy
VALIDATION HARNESS (a disciplined **lie-detector**): does a defined-risk put
credit spread have POSITIVE EXPECTANCY AFTER REALISTIC COSTS across
2018/2020/2022 regimes? It is NOT a live bot; it places no orders. "No edge after
costs" is a SUCCESS. Statistical honesty outranks getting a PASS. WAT framework
(Workflows/Agents/Tools). Python 3.12 via `uv`. Tests are stdlib `unittest`, NOT
pytest. Use `rg`, not grep. Run code as `uv run python ...`; tests as
`uv run python -m unittest discover -s tests`.

## 1. What is being built (Phase 1A = Research Integrity Foundation)

The enforcement SUBSTRATE that must be true BEFORE the first real ThetaData
backtest (run #1), so run #1 records an honest result, not a lie. Every guarantee
is enforced by CODE (not prose). It does NOT wire ThetaData and does NOT compute
Phase-1B stats (DSR/PBO are stubbed `null`).

**Sources of truth (both committed, read them):**
- Spec: `docs/superpowers/specs/2026-07-01-research-integrity-foundation-design.md`
- Plan (16 TDD tasks): `docs/superpowers/plans/2026-07-01-research-integrity-foundation.md`
- Original task brief: `docs/superpowers/handoff-2026-07-01-phase1a.md`
- An implementation audit (from a review agent): `docs/superpowers/reviews/2026-07-01-phase1a-implementation-audit.md`

## 2. CRITICAL: two AI actors have touched this repo

- **This Claude session** designed the spec/plan and executed Tasks 1–8 (via
  subagents with two-stage review).
- **Codex** (a separate agent the owner also runs) independently HARDENED the
  substrate and EXPANDED the spec/plan while this session was paused — adding the
  `source_hash` drift-guard, ledger hardening, and window validation. This
  session audited Codex's work (graded **A–**), kept nearly all of it, folded in
  one improvement (`json_safe`), and consolidated it into clean commits.
- **Coordination rule (do NOT violate):** only ONE agent edits this branch at a
  time. Running Claude + Codex concurrently already corrupted one commit
  (`0ef6a85`) via a test-sweep-in race. The owner's current directive: **Claude
  drives to completion; Codex REVIEWS at the end (not during).** Do not spawn or
  assume Codex is editing concurrently.

## 3. Exact current state (verified at handoff)

- Branch: `phase-1a-research-integrity` (checked out). Base branch: `main`.
- HEAD: `b272b75` (this handoff). Last CODE commit: `04a07ca` (Task 8 CLI +
  trial-log fix). Working tree CLEAN.
- Full suite: **76 tests, green** (`uv run python -m unittest discover -s tests`).
- `research/` modules present: `__init__.py`, `hashing.py`, `ledger.py`,
  `windows.py`, `experiments.py`, `cli.py`. **Missing: `facts.py` (Task 9).**
- `metrics.py` is still the ORIGINAL Phase-0 version (old IID `_expectancy_ci`);
  Tasks 10–14 rewrite it. `harness/run_backtest.py` still a Phase-0 stub (Task 15
  adds a seam). No `ledger/` dir yet (Task 16 creates it).

**Commit history on the branch (newest first):**
```
b272b75 docs: Phase-1A execution handoff (this file)
04a07ca fix(research): trial-log surfaces LedgerError as clean nonzero exit  [Task 8 fix]
0aa8f20 feat(research): integrity CLI seams (verify, trial-log, register, reveal-oos)   [Task 8]
9189405 fix(research): reveal entry_date->OOSGateError; register rejects window straddling IN_SAMPLE_END; single-writer doc  [Task 7 fixes]
53b8a41 feat(research): write-once OOS gate with source/config/cost drift + window checks  [Task 7]
e6f45b4 fix(research): register raises OOSGateError on non-serializable is_result; real-git source-clean test  [Task 6 fixes]
9eb45b8 feat(research): pre-registration + trial counter (source_hash, NaN-safe)  [Task 6]
72039d7 docs: fold source_hash drift-guard into Phase-1A spec + plan  [consolidation - docs]
5be2a60 feat(research): consolidate ledger/hashing/windows integrity hardening  [consolidation - code, SUPERSEDES broken 0ef6a85]
0ef6a85 feat(research): enforce IS/OOS split at IN_SAMPLE_END  [Task 5 - BROKEN IN ISOLATION, see 5.]
6142e7c test(research): anchored verify requires committed clean ledger  [Task 4]
99dbf22 feat(research): append-only hash-chained ledger with HEAD + verify  [Task 3]
2dcebc9 feat(research): canonical cost-model snapshot + hashes  [Task 2]
8b5f2fc feat(config): add frozen Phase-1A integrity knobs  [Task 1]
97f0ccb docs: Phase 1A research-integrity TDD implementation plan
d4ebe9e docs: Phase 1A research-integrity spec (reviewed + reconciled)
```

## 4. What each finished module does (Tasks 1–8)

- **`config.py`** (+Task 1): frozen knobs `OOS_LOOK_BUDGET=3`,
  `BOOTSTRAP_BLOCK_EXPONENT=1/3`, `BOOTSTRAP_BLOCK_CONSTANTS=[0.5,1,2,4]`,
  `COHORT_GRANULARITY="week"`, `FILL_MODEL_ID="conservative_mid_minus_haircut_v1"`.
- **`research/hashing.py`**: `canonical_json` (fail-closed `allow_nan=False`, per
  RFC 8259), `sha256_hex`, `sha256_file`, `cost_model_snapshot`/`cost_model_hash`
  (captures `ASSUMED_CREDIT_FRAC` from `analysis/feasibility.py`, NOT config),
  `config_hash`, `source_snapshot`/`source_hash` over `SOURCE_HASH_PATHS`
  (config, metrics, strategies, analysis, data, harness, research + pyproject/
  uv.lock; excludes ledger/results/docs/tests), `data_window_hash`, `REPO_ROOT`.
- **`research/ledger.py`**: append-only hash-chained JSONL + `HEAD` tip file.
  `append` (fail-closed: verify-before-append, reserved-key guard),
  `verify([anchored],[git_clean_tracked])` (chain + HEAD + optional committed-
  clean), `read_all` (corrupt-JSON→LedgerError), `current_trial_count`,
  `LedgerError`. Git checks scoped via `git -C REPO_ROOT`.
- **`research/windows.py`**: `split_is_oos`, `assert_oos_only` (IN_SAMPLE_END
  boundary), `assert_within_window`, typed `_as_date`.
- **`research/experiments.py`**: `register()` (writes `run` record with
  config/cost/source/data_window hashes, validates identity/threshold/risk_basis/
  windows, cross-checks windows vs IN_SAMPLE_END, refuses duplicate hypothesis_id
  and a dirty source surface, DSR/PBO=null stubs, +1 trial), `log_trial_intent()`
  (+1 trial), `current_trial_count()`, `reveal_oos()` (write-once OOS gate:
  registration → config/cost/source drift → write-once → look-budget → anchored
  ledger → run_fn → assert_oos_only + assert_within_window → scoreboard → append
  `oos_reveal`; does NOT increment counter), `json_safe()` (NaN/Inf→None so
  scoreboards are valid JSON), `OOSGateError`. Concurrency is DEFERRED (single-
  writer trust boundary documented in `reveal_oos` docstring — see 6.).
- **`research/cli.py`**: `main(argv)->int` with subcommands `verify`,
  `trial-log`, `register`, `reveal-oos` (the hook-able seams; no hook built).

## 5. Known caveats (don't re-investigate — already resolved/decided)

- **`0ef6a85` is broken in isolation** (contains hardening tests without their
  source, from the concurrent-edit race). It is SUPERSEDED by `5be2a60`, so
  **HEAD is green and self-consistent**. Do not rebase/rewrite history (owner
  rule: no history rewrite without approval). A clean checkout of HEAD passes 75.
- **Git identity warning** on every commit ("auto-configured name/email") is
  benign; do NOT touch git config.
- **`json_safe` decision:** `canonical_json` is fail-closed (`allow_nan=False`);
  scoreboards legitimately contain `NaN` (Sharpe/Sortino/CI on insufficient
  samples). `experiments.register`/`reveal_oos` sanitize is_result/oos_result via
  `json_safe` (NaN→null) so honest INSUFFICIENT runs can be logged. The metrics
  layer (Tasks 10–14) does NOT need json_safe — sanitization happens at the
  ledger boundary in experiments.
- **Concurrency (Threat Model C):** `reveal_oos`'s read-check-append is not
  locked; two concurrent PROCESSES could both pass the budget/write-once check
  (reproduced by a reviewer). DECISION: deferred, NOT fixed in 1A — it is the
  "hard/autonomous-runner enforcement" the spec explicitly stages to threat B;
  there is no concurrent caller (single-process CLI). Documented as a trust
  boundary in the `reveal_oos` docstring. Do not add fcntl/locking in 1A.

## 6. Process to CONTINUE (follow exactly — this is what kept quality high)

Use **superpowers:subagent-driven-development**. Per task:
1. Read the task's full text from the committed plan file (line ranges in 7.),
   dispatch a fresh **general-purpose** implementer subagent with the COMPLETE
   task text pasted in (don't make it read the plan).
2. **Implementer git rules (paste into every implementer prompt):** (a) first
   `git status --porcelain` MUST be clean or STOP/BLOCKED; (b) `git add` ONLY the
   exact files the task touches (never `-A`/`.`); (c) re-check staged set before
   commit. This prevents the earlier sweep-in corruption.
3. Two-stage review with **read-only `Explore` subagents** (they lack Edit/Write,
   so a reviewer can never again edit source): spec-compliance first, then code
   quality. Have reviewers independently RUN commands, not trust reports.
4. If a reviewer finds real issues, dispatch a fix subagent (same git rules),
   then re-review. Evaluate findings on merit (receiving-code-review discipline);
   don't blindly accept — but this project errs toward airtight integrity code.
5. Commit per task (owner wants commits). Co-author trailer:
   `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` (add
   `Co-Authored-By: Codex <noreply@openai.com>` on consolidations of Codex work).
6. Model choice: sonnet for implementers/most reviews; haiku ok for trivial;
   Explore for all reviews.

**Task 8 is fully closed.** Its read-only review returned spec PASS + quality
"with fixes" (one item: `trial-log` leaked a `LedgerError` traceback instead of
returning an int). That fix landed in `04a07ca` (mirrors `verify`'s handling; a
`test_trial_log_returns_nonzero_on_tampered_ledger` was added). CliTests is now 5
tests; full suite 76 green. No pending fixes remain for Tasks 1–8. Start at
Task 9.

## 7. REMAINING WORK — Tasks 9–16 (all in the committed plan)

Read each task's full text from
`docs/superpowers/plans/2026-07-01-research-integrity-foundation.md` at these
line ranges (verify with `rg -n "^## Task " <plan>`):
- **Task 9** (~L1459): `research/facts.py` — append-only DESCRIPTIVE facts log,
  separate from the ledger, NOT verdict-feeding. Small.
- **Task 10** (~L1539): `metrics.py` — require `entry_date` + `symbol` on the
  verdict path (`_validated_arrays` raises; no IID fallback). UPDATE the existing
  `tests/test_core.py` `ScoreboardTests` (they build trades without the new
  fields). Note: `_validated_arrays` returns a 4-tuple now (adds entry_dates).
- **Task 11** (~L1706): `metrics.py` — `_build_week_cohorts` (ISO-week cohorts),
  `_block_lengths` (frozen envelope `round(c*n_cohorts**(1/3))`, dedup, clamp
  `2<=L<=n_cohorts-1`, EMPTY if n_cohorts<3).
- **Task 12** (~L1807): `metrics.py` — `_resample_block` + `_resample_stationary`
  over weekly cohorts, `_ci_from_cohorts` (widest CI across ALL (method,block_len)
  = min lo / max hi), `_dependence_aware_ci`, explicit `iid_expectancy_ci`
  (illustration only). KEEP old `_expectancy_ci` until Task 13 (avoids a broken
  commit — this ordering fix is already in the plan).
- **Task 13** (~L1964): wire scoreboard to `_ci_from_cohorts`; verdict guards on
  BOTH losses (`MIN_LOSSES_FOR_VERDICT`) AND cohorts (`n_cohorts<3` →
  INSUFFICIENT); DELETE old `_expectancy_ci`; update `_demo` to dated+symboled
  trades.
- **Task 14** (~L2081): the load-bearing under-coverage TEST — a clustered
  synthetic series where IID CI excludes 0 (false PASS) but the dependence-aware
  envelope includes 0 and is wider. Deterministic seed; if borderline, strengthen
  the down-week magnitude, never weaken the IID side.
- **Task 15** (~L2138): `harness/run_backtest.py` — `reveal_out_of_sample()` seam
  delegating to `experiments.reveal_oos` with a still-`NotImplementedError`
  ThetaData run_fn (gate runs BEFORE the unwired data path).
- **Task 16** (~L2209): create committed `ledger/` location (`README.md` +
  `.gitkeep`), confirm `ledger/` is NOT gitignored, full-suite + demo +
  `uv sync --locked --check` (no new deps) green.

**Carry-forward reminders:** (a) when Task 15/real-wiring feeds OOS trades to
`reveal_oos`, those trades must carry `entry_date` + `symbol` (Task-10 contract);
(b) DSR/PBO stay `null` stubs; (c) no ThetaData/Lumibot wiring anywhere in 1A.

## 8. Definition of done + final step

All 16 tasks green (was 75 tests at Task 8; grows through Task 14). Then a FINAL
whole-branch self-review, confirm `uv run python -m unittest discover -s tests`
is green in a clean checkout and `uv run python -m research.cli verify` works,
then **hand the branch to Codex to review** (owner's plan: Codex checks the
finished work). Do not merge to `main` without the owner's say-so.

# Q1-Q9 Sequential Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close or freshly audit Q1 through Q9, implement the owner-approved
prospective H6 hard-kill v2, and stop at the Q10 integration gate.

**Architecture:** Work in one isolated branch with a commit and verification
checkpoint per queue item. Q2 dispatches hard-kill semantics by H6 entry date
and versions decision receipts without migrating the book; every other task is
documentation-only or audit-first unless a fresh regression proves otherwise.

**Tech Stack:** Python 3.12, unittest, uv, Ruff, Pyright, append-only research
ledger, canonical JSON/SHA-256 receipts, Git, and advisory CodeRabbit CLI.

## Global Constraints

- No provider call, cache mutation, live order, book edit, prior-result rewrite,
  retrospective rescore, or unapproved schema-v2 integration.
- Preserve `data/positions/h6_positions.csv` byte-for-byte at SHA-256
  `d9c65cab1a58e2ca0e571ead8c78fe408e19208c5cbbb05b189ccb67d7eab528`.
- Use `research.experiments.log_trial_intent` for the single Q2 chained append.
- Use failing-first tests for every Q2 behavior change and any discovered repair.
- Stop immediately on a ledger, book, receipt, manifest, or registered-result
  mismatch that the scoped task does not explain.

---

### Task 1: Q1 documentation truth repair

**Files:**
- Modify only as needed: `README.md`, `.claude/rules/backtest-engine.md`,
  `ledger/h7_forward/README.md`, `docs/provider-transition.md`,
  `docs/superpowers/specs/2026-07-30-daily-nav-drawdown.md`, `PROJECT_STATE.md`

- [ ] Reconcile the six documents against code, both ledgers, provider policy,
  the H7 store, and the canonical roadmap.
- [ ] Remove stale cache-miss, cancellation-checklist, and H7-restart claims;
  label retained historical text as historical.
- [ ] Mark Q1 complete and run both ledger verifiers, scoped stale-phrase and
  path-reference scans, `git diff --check`, and a docs-only diff inventory.
- [ ] Commit as `docs(governance): close Q1 truth repair`.

### Task 2: Q2 chained registration

**Files:**
- Modify: `ledger/experiments.jsonl`, `PROJECT_STATE.md`

- [ ] Verify the research ledger, the H7 ledger, the H6 book hash, and absence
  of the exact `H6_KILL_V2 2026-08-02` reason.
- [ ] Append one H6 `trial_intent` through
  `research.experiments.log_trial_intent(reason, hypothesis_id="H6")` using the
  owner-approved rule in the design document.
- [ ] Capture the returned record hash, verify the chained ledger, prove one
  matching append, and inspect the one-record diff.
- [ ] Commit as `data(ledger): register prospective H6 kill v2`.

### Task 3: Q2 hard-kill and receipt implementation

**Files:**
- Modify: `config.py`, `options_researcher/h6_watch.py`, `tests/test_h6_watch.py`,
  `PROJECT_STATE.md`

**Interfaces:**
- Add config strings `H6_KILL_V2_EFFECTIVE_ENTRY_DATE` and
  `H6_KILL_V2_TRIAL_INTENT_HASH`.
- Preserve `BookPosition`, `BOOK_FIELDS`, `H6Score`, and public CLI shapes.
- Support historical `h6_exact_session_watch_receipt_v1`; generate and require
  `h6_exact_session_watch_receipt_v2` for decisions on/after 2026-08-03.

- [ ] Add failing tests for the effective-date boundary and v1/v2 isolation;
  run discovery for `test_h6_watch.py` and confirm the expected failures.
- [ ] Add failing tests for shifted exits, partial deployment, positive
  recovery, open cohorts, and zero-deployment gaps; confirm expected failures.
- [ ] Add failing receipt tests for historical v1 acceptance, post-effective
  v1 refusal, and v2 binding of both chained record hashes; confirm failures.
- [ ] Implement the minimal entry-date dispatcher, v2 cohort evaluator,
  versioned config snapshot, receipt build, and receipt verification logic.
- [ ] Run H6 and H8 focused tests, then refactor only while they remain green.
- [ ] Verify the real H6 book and historical receipt without modifying either.
- [ ] Run the full root suite, Ruff, Pyright, scoped format checks, both ledger
  verifiers, cost-model hash comparison, book hash comparison, and diff checks.
- [ ] Check CodeRabbit prerequisites and secrets in the diff; run an advisory
  review against the Q1 commit. Reproduce and fix validated critical/warning
  findings with new red-green tests, then repeat verification.
- [ ] Mark Q2 complete and commit as `feat(h6): add prospective entry-cohort kill v2`.

### Task 4: Q3 atomicity audit

**Files:**
- Modify documentation/proof only if fresh evidence supports it.

- [ ] Run `test_pcs_adapters.py`, inspect the no-naked-leg paths, prove the cost
  model and `FILL_MODEL_ID` unchanged, update the audit status, and commit Q3.
- [ ] If the audit reproduces a regression, stop, invoke systematic debugging,
  and use a new failing test before any production repair.

### Task 5: Q4 exact-session audit

**Files:**
- Modify documentation/proof only if fresh evidence supports it.

- [ ] Run the exact-session consumer modules and a temp-output H5 cache-edge
  smoke; require `DATA_GAP`/`NO_GO` and no `FIRE`, update the audit status, and
  commit Q4 separately.
- [ ] If the audit reproduces a regression, stop, invoke systematic debugging,
  and use a new failing test before any production repair.

### Task 6: Q5-Q9 recurring audits

**Files:**
- Modify `PROJECT_STATE.md` or existing proof documents only when recording
  fresh evidence; do not modify operational data.

- [ ] Q5: prove the provider-closeout fact exists exactly once with its recorded
  hash; review and commit the Q5 checkpoint.
- [ ] Q6: run `uv run python tools/cache_manifest.py verify` and prove cache bytes
  and acquisition facts did not change; review and commit the Q6 checkpoint.
- [ ] Q7: run `test_provider_disabled.py`, its neighboring set, and the guarded
  constructor inventory; review and commit the Q7 checkpoint.
- [ ] Q8: verify `reports/strategy-a-cap-audit/2018-01-01_2022-12-31.json` with
  `tools/strategy_a_cap_audit.py --verify`; review and commit the Q8 checkpoint.
- [ ] Q9: verify both 2026-08-02 readiness receipts with
  `tools/thetadata_exit_audit.py --verify` and run
  `test_offline_intelligence_readiness.py`; review and commit the Q9 checkpoint.

### Task 7: Q10 stop gate and final handoff

- [ ] Confirm no schema-v2 branch merge, artifact rebuild, activation, provider
  call, book change, or cache mutation occurred.
- [ ] Run final ledger, diff, status, and forbidden-surface checks.
- [ ] Stop at Q10 and report the exact owner integration decision still required.

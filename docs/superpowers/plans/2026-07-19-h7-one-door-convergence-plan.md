# H7 One-Door Convergence & Activation Runway — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Codex-assigned tasks carry a verbatim handoff prompt — run exactly one per Codex session, in order, per the master-prompt operating method (one phase per prompt; independent review in a fresh context after each phase; never skip a gate).

**Goal:** Converge the three parallel Stage-8 workstreams into ONE reviewed activation door, then complete the operational runway so the owner can open H7's forward paper window with a single authorized append.

**Architecture:** Integration branch `feature/h7-one-door` built from main absorbs, in order: the architecture repair (receipts/backup/scope identity, branch `feature/h7-architecture-repair` @047452e), the reviewed real-append path (`feature/h7-stage8-real-append` @67e29e3, ten-refusal `register_window_real`), and the *adapted* evidence-hardening deltas from `codex/h7-stage8-critical-20260717` (built pre-ET against 14 names — adapt, never blind-merge). `tools/h7_manual_activate.py` becomes the only CLI and `register_window_real` the only code path that writes `ledger/h7_forward/`. Joint independent review gates the merge to main; owner gates the append.

**Tech Stack:** Python 3.12/uv, unittest (offline), ruff, pyright, git worktrees per agent, restic (backup), Codex CLI for coding-heavy tasks, Claude (this session) for orchestration/review/ledger.

**Division of labor:**
- **Codex** — Tasks A3 (reconciliation coding), A4-prep, B1 (restore-drill script), B5 (preflight/receipt glue). Mechanical, test-first, well-specified.
- **Claude (orchestrator)** — merges, fresh-context independent reviews, ledger facts, gate runs, verdict interpretation, Codex prompt dispatch + phase-gate enforcement.
- **Owner** — the 7 window inputs, trim-at-append yes/no, restic destination+password, per-name earnings promotions, final activation authorization. No agent may fill these.

**Standing guardrails (bind every task):** real store `ledger/h7_forward/` stays VALID EMPTY until Phase C; no paid pulls without per-pull owner approval; ledger writes only via typed APIs (hook-enforced); work in isolated worktrees, never switch the shared checkout's branch; full suite exit code is the verdict; banned vocabulary applies to all outputs.

---

## Phase A — Convergence to one door

### Task A1: Ingest the pending Stage-8 re-verdict (Claude)

**Files:** none (review artifact: `scratchpad/stage8-independent-review.md`)

- [ ] **Step 1:** Wait for the in-flight re-review of `67e29e3` (C1–C3 fixes). On FAIL: fix findings on `feature/h7-stage8-real-append` first, re-submit; do not proceed to A2 until PASS or PASS-WITH-CONDITIONS whose conditions are procedural.
- [ ] **Step 2:** Record the verdict in `ledger/facts.log` via `research.facts.append_fact` (one `H7_STAGE8_REVIEW` fact naming reviewer round, verdict, commit).
- [ ] **Step 3:** Commit the fact: `git add ledger/facts.log && git commit -m "docs(ledger): record stage-8 real-append review verdict"`.

### Task A2: Build the integration branch (Claude)

**Files:** branch only

- [ ] **Step 1:** From a fresh worktree: `git worktree add <scratchpad>/wt-onedoor -b feature/h7-one-door main`
- [ ] **Step 2:** `git merge --no-ff feature/h7-architecture-repair` (expect clean or facts.log union-merge; resolve keep-both only).
- [ ] **Step 3:** `git merge --no-ff feature/h7-stage8-real-append`. Expected conflicts: `options_researcher/h7_activation_guard.py` (repair's strict/receipt params vs real-append's provenance fields — KEEP BOTH: the dataclass gains `forward_base`/`code_commit`/`built_at_utc` AND the strict receipt parameters) and `options_researcher/h7_window_registration.py` (repair edits + `register_window_real` — keep both; the function is additive at module tail).
- [ ] **Step 4:** Run full suite; expect failures at the seam (manual_activate still calls `ledger.append_event` directly; guard signature drift). List them — they are Task A3's Codex work-list, not things to hand-patch now.
- [ ] **Step 5:** Commit the merge state: `git commit -m "merge: one-door integration base (repair + real-append; seam failures listed for A3)"` — committing a red seam on an integration branch is acceptable ONLY here, documented in the message.

### Task A3: Reconcile into one door (CODEX — verbatim handoff prompt below)

**Files:**
- Modify: `tools/h7_manual_activate.py` (append via `register_window_real`, never `ledger.append_event`)
- Modify: `options_researcher/h7_window_registration.py` (accept receipt-backed `recheck_gates`)
- Modify: `options_researcher/h7_activation_guard.py` (unified signature)
- Create: `tests/test_h7_one_door.py`
- Adapt: cherry-pick evidence-hardening ideas from `codex/h7-stage8-critical-20260717` (commits `9b0ef66`, `dc7a5a6`, `ee8d10a`) re-based to the 15-name versioned scope — adapt names/counts, do not blind-merge.

- [ ] **Step 1:** Dispatch Codex in the `wt-onedoor` worktree with this prompt, verbatim:

> You are the implementation agent for options-validator at <worktree path>, branch feature/h7-one-door. Read CLAUDE.md and .cursorrules first and obey them exactly. Phase gate you must satisfy before stopping: ONE code path writes ledger/h7_forward/ — `register_window_real` in options_researcher/h7_window_registration.py — and `tools/h7_manual_activate.py` is its only caller; full suite green; ruff and pyright clean; the real store on disk verifies VALID EMPTY before and after the suite.
>
> Work: (1) In tools/h7_manual_activate.py, replace the direct `ledger.append_event(event, base_dir=REAL_FORWARD_STORE, expected_head=None)` call with a call to `registration.register_window_real(...)`, passing: the owner dict; the evidence dict it already assembles; the guard report it already builds; `spec_sha256` and `spec_path` for docs/superpowers/specs/2026-07-19-h7-stage8-activation-spec.md; `code_state=lambda: (git rev-parse HEAD, porcelain-clean bool)`; and `recheck_gates=` a new function that (a) re-validates the source-health and data-gate receipts by hash exactly as the CLI already does, (b) re-runs `options_researcher.h7_source_health` and `h7_data_gate` for the pinned completed session, and (c) returns {"source_health_all_healthy": bool, "data_gate_go": bool, "source_health_evidence_id": <receipt hash>, "data_gate_evidence_id": <receipt hash>} so the evidence ids match what the CLI put in the evidence dict. (2) Fix the guard's fabricated `source_health_by_symbol={s: True ...}`: pass the real per-symbol health mapping loaded from the source-health receipt. (3) Adapt the evidence-hardening intent of codex/h7-stage8-critical commits 9b0ef66, dc7a5a6, ee8d10a onto the current 15-name versioned scope (scope_identity) — read those commits with `git show`, port what still applies, and note in the commit message what was dropped and why. (4) Write tests/test_h7_one_door.py with, at minimum: a structural test that greps options_researcher/ and tools/ and asserts `append_event(` with `REAL_FORWARD_STORE` appears ONLY inside register_window_real's module path; an end-to-end synthetic activation through the CLI's code path against a temp store proving seq 0 window_registration; and a test that a receipt-hash mismatch in recheck_gates refuses. TDD: write each failing test, run it, implement minimally, re-run, commit. Never touch ledger/h7_forward/, never run a paid pull, never hand-edit any ledger file (a hook blocks it and the hook is correct). Finish with: full suite output tail, ruff, pyright, `python -m options_researcher.h7_event_ledger verify` (expect VALID EMPTY), and a phase-gate report (what changed, what didn't and why, tests run, open assumptions).

- [ ] **Step 2 (Claude):** Read Codex's phase-gate report. Run the full suite + ruff + pyright yourself in the worktree; the exit codes are the verdict, not the report.
- [ ] **Step 3 (Claude):** Verify the structural one-door test fails if reverted: `git stash` the manual_activate change, run `tests/test_h7_one_door.py` (expect FAIL), `git stash pop`.

### Task A4: Joint independent review (Claude)

**Files:** review artifact `scratchpad/one-door-review.md`

- [ ] **Step 1:** Dispatch a FRESH-context adversarial reviewer (Opus subagent) over `feature/h7-one-door`: attack the single-door claim (any other write path?), the receipt-recheck seam (can a stale receipt pair pass?), the ported codex hardening (did adaptation lose a protection?), and spec-vs-code parity for `2026-07-19-h7-stage8-activation-spec.md` (update the spec in the same branch if code moved).
- [ ] **Step 2:** Fix conditions inline (Codex for code, Claude for docs), re-submit to the same reviewer until PASS.
- [ ] **Step 3:** Record the review chain as a fact via `append_fact` and commit.

### Task A5: Merge to main (Claude)

- [ ] **Step 1:** `git checkout main && git merge --no-ff feature/h7-one-door` in the main checkout (facts.log union driver handles ledger overlap).
- [ ] **Step 2:** Full suite on merged main; push only on exit 0 (push must be a separate command gated on the suite — do not chain them).
- [ ] **Step 3:** Confirm CI green on GitHub; record `H7_ONE_DOOR_MERGED` fact.

**Phase A gate:** main has exactly one activation door, jointly reviewed; real store VALID EMPTY; suite/CI green. Codex QM-dashboard branch is explicitly OUT of scope here (separate arc, separate review).

---

## Phase B — Operational runway (parallel where independent)

### Task B1: Restic backup + restore drill (Owner + Codex)

**Files:** uses `tools/h7_forward_backup.py` (exists); Create: `docs/h7-restore-drill-log.md`

- [ ] **Step 1 (Owner):** choose backup destination (local disk / external drive / cloud bucket) and set the restic password + any bucket credentials in `.env` (never in chat, never committed).
- [ ] **Step 2 (Claude):** verify `restic version` runs locally; if absent: `brew install restic`.
- [ ] **Step 3 (Codex prompt):** "In <worktree>, using tools/h7_forward_backup.py's existing interface (read it first), run one full backup of ledger/ + data/earnings/ + reports/h7_receipts/ to the configured restic repo, then a restore into a temp dir, then verify the restore byte-identical (the tool's own verification path). Write the drill evidence (timestamps, snapshot id, verification result — no secrets) to docs/h7-restore-drill-log.md and produce the backup_restore receipt the activation CLI expects. Do not touch ledger/h7_forward/."
- [ ] **Step 4 (Claude):** commit drill log + receipt; `append_fact` a `H7_RESTORE_DRILL` record.

### Task B2: Six-name earnings resolution loop (Claude + Owner)

**Files:** `data/earnings/assertions_v2.csv`, `gating_v3.csv` (typed refresher only)

- [ ] **Step 1:** Every trading day until healthy (or trimmed): dispatch the Sonnet earnings recheck (same prompt as 2026-07-19's run) for NVDA/AVGO/SMCI/CRWV/IREN/USAR. Expected arrivals: NVDA ~Jul 30 (last year's analog), AVGO mid-Aug, others ~1 week pre-report.
- [ ] **Step 2:** On each company confirmation: stage `append-raw` with the company source (AMZN/ET pattern: `uv run python tools/h7_refresh_earnings.py append-raw --symbol <S> ... --source-type company_pr --source-url <company URL>`), then hand the owner the one-line `promote` command. Owner runs it.
- [ ] **Step 3:** After each promotion: run `h7_source_health`, commit the CSVs, update the healthy count in the daily report.

### Task B3: Trim-at-append amendment (Owner gate, then Claude)

**Files:** Modify: `docs/superpowers/specs/2026-07-19-h7-stage8-activation-spec.md`; `tools/h7_manual_activate.py` + tests

- [ ] **Step 1 (Owner):** yes/no on: "any name still lacking a company-confirmed earnings date on append day is excluded from this window's universe, recorded in the registration payload, and the append proceeds with the healthy names."
- [ ] **Step 2 (if yes, Codex):** implement `--trim-unhealthy` on the activation CLI: compute the trimmed scope from the source-health receipt, record `trimmed_names` + reasons in the event payload, refuse if the trim empties a lane. Test: synthetic store, 2 unhealthy of 15 → payload lists exactly those 2.
- [ ] **Step 3:** Spec §2/§3 updated in the same commit; send the delta through the standing reviewer (it amends a reviewed control); owner-typed ratification recorded as a fact.

### Task B4: Owner input packet (Owner, Claude transcribes)

**Files:** Create: `reports/h7_receipts/owner_inputs.json` (values verbatim, entry mechanics disclosed)

- [ ] **Step 1:** Owner supplies the 7 values (authorization string; start session; session count ≥ 3 calendar months; end-rule ack; three-month ack; coverage-through date; coverage evidence pointer).
- [ ] **Step 2:** Claude transcribes to JSON, reads it back to the owner verbatim for confirmation, commits, and records the transcription fact (owner-directed, agent-typed — the established disclosure pattern).

### Task B5: Fresh audit receipt + preflight modernization (Codex)

**Files:** Modify: `tools/thetadata_cutoff_preflight.py` (+ its test)

- [ ] **Step 1 (Codex prompt):** "tools/thetadata_cutoff_preflight.py hardcodes a frozen 12-name scope and the 2026-07-29 cutoff, both stale (15-name versioned scope_identity now exists; renewal executed per THETADATA_RENEWAL_EXECUTED fact). Read the repair's scope_identity() and receipts modules first. Add a `--scope current` mode that derives the live versioned scope and reports against it while PRESERVING the frozen 12-name mode as the default historical behavior (the frozen mode is a registered artifact — do not delete or alter its output). Update tests to cover both modes. Full suite + ruff + pyright green."
- [ ] **Step 2 (Claude):** produce the fresh data-audit receipt for the pinned session via the repair's receipt tooling; commit; verify `h7_manual_activate`'s validation accepts it.

**Phase B gate:** restore drill logged + receipt exists; preflight current-mode green; owner inputs committed; source health 15/15 healthy OR trim ratified; all reviewed deltas merged.

---

## Phase C — Activation (Owner + Claude, one sitting)

### Task C1: The one append

- [ ] **Step 1:** Same-session sequence, no gaps: clean tree check → `h7_source_health` (expect all-healthy or trim list) → `h7_data_gate` (expect GO 15/15) → `h7_event_ledger verify` (expect VALID EMPTY) → generate fresh receipts.
- [ ] **Step 2 (Owner present):** run `uv run python tools/h7_manual_activate.py --owner reports/h7_receipts/owner_inputs.json --evidence <evidence.json> --source-health-receipt <path> --data-gate-receipt <path> --backup-restore-receipt <path>` — the CLI routes through `register_window_real`'s full refusal chain; any refusal = stop, diagnose, re-run gates; never force.
- [ ] **Step 3:** `h7_event_ledger verify` (expect: valid, count 1, seq-0 window_registration); `append_fact` the `H7_STAGE8_ACTIVATED` record binding receipt hashes + spec sha; immediate restic backup; commit + push; update README scope status + memory.

### Task C2: Day-1 forward operations

- [ ] **Step 1:** Wire the daily ritual: gates → receipts → watcher (refuses without matching data-gate receipt, per the repair) → decisions at T, owner-approved entries at T+1 close, every transition into the hash-chained forward ledger.
- [ ] **Step 2:** No interim scoring — the window scores once, at the end, `MIN_LOSSES_FOR_VERDICT=10`. A SURVIVED outcome is not live-trading approval.

**Phase C gate:** chain verifies with exactly one event; first decision session runs clean; backup snapshot exists post-append.

---

## Review cadence (master-prompt method, adopted)

After every Codex task: Claude re-runs the verification commands itself (exit codes, not reports). After every phase: fresh-context adversarial review before the next phase starts. Verification sweep (full suite + ruff + pyright + ledger verify + real-store check) before any merge to main. One Codex prompt per session; if a prompt would require skipping a gate, split it.

## Known risks

- **Shared-checkout crossfire** (bit us twice): all agent work in worktrees; merges only by the orchestrator; check `git status`/branch before trusting anything.
- **Three-strand merge conflicts** in guard/registration modules: resolved keep-both in A2/A3 with the structural one-door test as the arbiter.
- **Codex's 14-name-era assumptions**: port intent, not diffs.
- **Spend limits**: if a subagent dies mid-task, salvage its worktree (pattern proven 2026-07-19) and finish inline.
- **Owner unavailability on announcement days**: promotions are owner-run; batch the commands so each is one paste.

# Repository Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the verified local `main` branch the complete, clean integration point without merging owner-gated or unique branch work.

**Architecture:** `main` is already a descendant of the committed `sfix` history. The sole pending `sfix` wiki record is first committed with this plan, then carried to `main` as a small, reviewable commit. Evidence created by the live main workspace is independently validated and committed only if it matches the repository's receipt contract.

**Tech Stack:** Git worktrees, Python/uv validation commands, the repository's append-only wiki and evidence records.

## Global Constraints

- Do not push, delete remote branches, change live-trading behavior, or fetch provider data.
- Do not merge `codex/od1-v2-current`; `PROJECT_STATE.md` keeps that audited data lane parked pending explicit owner authorization.
- Preserve every branch or worktree with unique commits, unknown ownership, an open pull request, or a runtime reference.
- Remove only clean local worktrees whose checked-out branch is an ancestor of `main`; use `git branch -d`, never force deletion.
- Preserve immutable cache bytes, ledgers, historic receipts, paper books, and raw wiki sources.

---

### Task 1: Settle the pending wiki record on `sfix`

**Files:**
- Modify: `wiki/log.md`
- Create: `docs/superpowers/plans/2026-08-02-main-consolidation-cleanup.md`

- [x] **Step 1: Verify the pending record has a source**

Run: `sed -n '1,240p' tools/repo_rag/logs/repo_rag_health_2026-08-02T070005.log`

Expected: The scheduled run reports the 549-source / 13,137-chunk result and its zero source failures.

- [x] **Step 2: Validate the focused documentation diff**

Run: `git diff --check -- wiki/log.md docs/superpowers/plans/2026-08-02-main-consolidation-cleanup.md`

Expected: no output and exit code 0.

- [ ] **Step 3: Commit only the wiki record and this plan**

Run: `git add -- wiki/log.md docs/superpowers/plans/2026-08-02-main-consolidation-cleanup.md && git commit -m "docs(maintenance): record main consolidation plan"`

Expected: one commit containing exactly the two listed files.

### Task 2: Integrate settled documentation and overdue live evidence into `main`

**Files:**
- Modify: `wiki/log.md` (via the Task 1 commit)
- Add: `reports/intraday_capture/2026-07-28/*.json` (existing live evidence only)

- [ ] **Step 1: Verify the live evidence is a five-snapshot, descriptive-only capture set**

Run: `rg --files reports/intraday_capture/2026-07-28 | sort` and inspect each JSON header.

Expected: exactly `open`, `open_auction`, `midmorning`, `midday`, and `preclose`; no strategy verdict or position mutation.

- [ ] **Step 2: Carry the Task 1 commit onto the live `main` worktree**

Run: `git cherry-pick <task-1-commit>` from `/Users/carsynstephenson/options-validator-ops`.

Expected: a clean cherry-pick that does not alter the five untracked evidence files.

- [ ] **Step 3: Commit only validated existing evidence**

Run: `git add -- reports/intraday_capture/2026-07-28 && git commit -m "evidence(intraday): persist 2026-07-28 snapshots"`

Expected: one commit containing only the five captured JSON files.

### Task 3: Retire only redundant local workspaces and labels

**Files:**
- No tracked file changes.

- [ ] **Step 1: Recheck every worktree's cleanliness and ancestry**

Run: `git worktree list --porcelain` plus `git status --short` and `git merge-base --is-ancestor <branch> main` for each candidate.

Expected: removal candidates are clean, fully merged, and not referenced by runtime configuration.

- [ ] **Step 2: Remove each approved redundant worktree, then safely delete its local branch**

Run: `git worktree remove <path>` followed by `git branch -d <branch>`.

Expected: Git refuses any non-merged or dirty target; remote branches remain untouched.

- [ ] **Step 3: Preserve non-merged work explicitly**

Expected: the H7, data-v2, dashboard, cache, and research-hardening branches remain because they contain unique work or are explicitly parked.

### Task 4: Verify the resulting local `main` codebase

**Files:**
- No further file changes.

- [ ] **Step 1: Run repository checks from `/Users/carsynstephenson/options-validator-ops`**

Run: `uv run python -m unittest discover -s tests`, `uv run ruff check .`, `uv run pyright`, and `uv run python tools/cache_manifest.py verify`.

Expected: all commands succeed; formatting is scoped because the repository has a known broad pre-existing formatting baseline.

- [ ] **Step 2: Verify governed records**

Run: `uv run python -m research.cli verify` and `uv run python -m options_researcher.h7_event_ledger verify`.

Expected: ledger verification succeeds without changing any evidence.

- [ ] **Step 3: Confirm final topology**

Run: `git status --short --branch`, `git log --oneline -n 10 main`, and `git rev-list --left-right --count origin/main...main`.

Expected: local `main` contains the consolidation commits and any remaining divergence is reported without a push.

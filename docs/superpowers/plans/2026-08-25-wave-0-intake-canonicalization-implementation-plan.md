# Wave 0 Intake and Canonicalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the two post-landing documentation commits onto current main, reserve Briefs 28 and 29 without touching their concurrent untracked drafts, and make Brief 26 internally executable only after a written independent PASS.

**Architecture:** Keep all tracked reconciliation in one documentation-only branch based on current `origin/main`. Preserve concurrent drafts in the primary checkout and reserve their identities through a small tracked registry; repair Brief 26 and append review evidence without changing code, ledgers, runtime state, or deployment state.

**Tech Stack:** Markdown, Git, GitHub CLI, repository documentation validators.

**Spec:** `docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md` and `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md`.

## Global Constraints

- The branch starts at current `origin/main`; transplant only the documentation deltas from `7908919` and `839ddb3`.
- Brief 28 is event awareness and Brief 29 is Schwab inventory binding.
- Do not rename, stage, commit, delete, or otherwise mutate any concurrent untracked draft before ownership confirmation.
- Brief 26 requires one focused independent written PASS before hand-off status is effective.
- Every PR is created as draft; workers may not make ready, merge, deploy, sync ops, modify ledgers, register/amend hypotheses, or flip authority.

---

### Task 1: Preserve and reserve the drafts

**Files:**
- Create: `docs/superpowers/plans/BRIEF-NUMBER-REGISTRY.md`

**Interfaces:**
- Consumes: primary-checkout paths, mtimes, and SHA-256 values from the read-only intake.
- Produces: one tracked reservation for Brief 28 and one for Brief 29, plus a visible unresolved collision record.

- [x] Record Brief 28 as event awareness and Brief 29 as Schwab inventory binding.
- [x] Record hashes and paths without staging or editing the drafts.
- [x] Hold the competing midday-29 draft for ownership resolution.

### Task 2: Reconcile the requested commits

**Files:**
- Modify: `docs/superpowers/plans/2026-08-25-25-market-context-signal-lane-codex-brief.md`
- Modify: `docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md`
- Modify: `docs/superpowers/plans/2026-08-25-27-pick-tracker-scoreboard-codex-brief.md`
- Modify: `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`

**Interfaces:**
- Consumes: documentation deltas from `7908919` and `839ddb3`.
- Produces: content-equivalent transplanted commits on current `origin/main` without importing the obsolete branch tree.

- [x] Cherry-pick `7908919` onto the current-main worktree.
- [x] Cherry-pick `839ddb3` onto the current-main worktree.
- [x] Verify both transplanted commits change documentation only.

### Task 3: Repair Brief 26

**Files:**
- Modify: `docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md`

**Interfaces:**
- Consumes: current producer/reader contracts in `tools/research_display_refresh.sh`, `options_researcher/regime_report.py`, and `options_researcher/attractiveness_dashboard.py`.
- Produces: a rev-5 implementation contract with one-pointer generation publication, manifest/hash validation, exact acceptance language, and worker authority stops.

- [x] Replace the impossible two-rename rollback claim with immutable generation plus one atomic pointer commit.
- [x] Specify canonical manifest, SHA-256, size, allow-list, ops-copy, and fail-closed reader behavior.
- [x] Separate the 30% pre-implementation stop gate from exact post-build acceptance.
- [x] Require frozen-input provenance and a draft-only implementation PR.

### Task 4: Obtain independent review

**Files:**
- Modify: `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`
- Modify: `docs/superpowers/plans/2026-08-25-26-board-declutter-top5-codex-brief.md`

**Interfaces:**
- Consumes: final rev-5 Brief 26 text and current-main code evidence.
- Produces: one focused reviewer verdict recorded verbatim enough to establish written PASS or a blocking finding list.

- [ ] Dispatch one independent reviewer focused on contradictions, atomicity, acceptance, ops/hash handling, and authority boundaries.
- [ ] Apply any required correction and return it to the same reviewer.
- [ ] Record written PASS; do not activate hand-off status without it.

### Task 5: Validate and publish the documentation PR

**Files:**
- Verify: all files changed from `origin/main`.

**Interfaces:**
- Consumes: reviewed documentation-only diff.
- Produces: one pushed branch and one GitHub draft PR; no merge or deployment.

- [ ] Run whitespace, conflict-marker, link/path, reservation-hash, and docs-only diff checks.
- [ ] Confirm the primary-checkout draft hashes are unchanged.
- [ ] Push `codex/wave0-intake-canonicalization`.
- [ ] Create the PR with `gh pr create --draft`; verify `isDraft=true`; stop.

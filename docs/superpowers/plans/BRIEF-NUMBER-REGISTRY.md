# Codex brief number registry

**Purpose:** tracked source of truth for reserving the running Codex-brief
sequence before a draft is renamed or added. A reservation assigns an identity;
it does not approve the brief, authorize hand-off, or make an untracked draft
canonical.

**Authority:** only the owner may resolve a conflicting reservation. Workers
must not rename, stage, commit, or delete a concurrent untracked draft merely to
make the filesystem agree with this table.

| Brief | Reserved subject | Repository state at Wave 0 intake | Disposition |
|---|---|---|---|
| 26 | Board declutter / Top-5 / compact regime view | Tracked on `main`; canonical status remains DRAFT until the Wave 0 documentation PR lands | Reconciled and independently reviewed in Wave 0 |
| 27 | Pick-tracker scoreboard | Tracked on `main` | Existing canonical brief |
| 28 | Event awareness | Untracked draft observed at `docs/superpowers/plans/2026-08-25-28-event-awareness-codex-brief.md`; SHA-256 `ef898909924e40f49abd794f75011a870590c1c18122ed3f4081f8bd8aefff03` | **RESERVED**; preserve in place, do not track until concurrent ownership is confirmed. *Status note 2026-08-26 (factual, not a disposition change): the brief is now TRACKED on `origin/main` and implemented (PR #91, merge `1255d5a`) — the do-not-track hold was overtaken by events under its own workstream's authority.* |
| 29 | Schwab inventory binding | Later untracked draft observed already bearing the requested number at `docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md`; SHA-256 `bc56c21a3d22dde77105871875d5b300b2cc08567b3bea2684142686b00c7d7a` | **RESERVED**; preserve in place, do not rename or track until concurrent ownership is confirmed. *Status note 2026-08-26: tracked on `origin/main` as a BLOCKED draft (fail-closed after the failed rev-2 review); later revisions in progress under this reservation.* |
| 30 | Midday chain refresh | The former `2026-08-25-29-midday-chain-refresh-codex-brief.md` collision draft (see below) was renumbered to 30 under its own workstream and is TRACKED on `origin/main` as `docs/superpowers/plans/2026-08-25-30-midday-chain-refresh-codex-brief.md` (Status: READY FOR HAND-OFF, review receipt `reports/2026-08-25-briefs-28-30-adversarial-review-receipt.md`) | Row added 2026-08-26 to close the registry gap; the intake collision below is thereby resolved in fact |
| 31 | Audit close-out follow-ups (SEC-01 trigger/auth-gate test pinning + job-health digest LaunchAgent wiring) | Reserved 2026-08-26 by the claude/codex-handoff-plan-2026-08-22 session; `docs/superpowers/plans/2026-08-26-31-audit-closeout-followups-codex-brief.md` committed together with this row. Highest number on disk at reservation time was 30; `ls` performed immediately before numbering per the 2026-08-25 collision lesson | Reserved and tracked together |
| 36 | H7 Schwab activation door (WP-A input binding P1, WP-B owner-ruled feasibility gate, WP-C rebuilt activation CLI, WP-D durability coercion fix, WP-E quote-age blocking gate F2) | Reserved 2026-08-31 by the PR #71 unfreeze session; `docs/superpowers/plans/2026-08-31-36-h7-schwab-activation-door-codex-brief.md` committed together with this row. Highest number on disk at reservation time was 35 (briefs 32-35, landed 2026-08-29); `ls` performed immediately before numbering | Reserved and tracked together |
| 37 | Dashboard presentation fixes (DR-1..DR-4, DR-6..DR-9 from the 2026-09-04 review: Mission Control as-of/shares/H7-paused/achievements, board rv21 + tracker receipt order + notice aging + chip dedupe, job-health digest cache symlink; DR-5 GREEN-fraction tilt held for owner ruling) | Reserved 2026-09-04 by the options-validator status/dashboard review session; `docs/superpowers/plans/2026-09-04-37-dashboard-presentation-fixes-codex-brief.md` committed together with this row. Highest number on disk at reservation time was 36; `ls` performed immediately before numbering; no untracked drafts present | Reserved and tracked together |

## Intake collision held for owner/concurrent-worker resolution

An additional untracked draft was observed at
`docs/superpowers/plans/2026-08-25-29-midday-chain-refresh-codex-brief.md`
(SHA-256
`068a7bb0552ab642f06d4254bb43cedcdd646a14667306429c8b8728c2ce5070`).
It also claims 29, but 29 is reserved above for the later Schwab-inventory
draft under the owner-directed Wave 0 disposition. This intake does not rename,
stage, commit, delete, or assign a replacement number to the midday draft.
That disposition waits for concurrent ownership confirmation.

## Default PR and authority rule

Every implementation PR created from these briefs starts as a GitHub **draft**.
A worker may not make it ready, merge, deploy, sync operational checkouts,
modify ledgers, register/amend a hypothesis, or flip any authority. Green CI on
a draft PR is evidence for owner review, never landing authority.

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
| 37 | Dashboard presentation fixes — eight fixes from the 2026-09-04 review (DR-1..DR-4, DR-6 sentence-only, DR-7, DR-8a, DR-9: Mission Control as-of/shares/H7-paused/achievements, board gap-sentence truth + tracker receipt order + notice aging, job-health digest cache symlink); DR-5/DR-5b (GREEN-fraction tilt; rv21 badges on Schwab cards) held for owner ruling; DR-8b (event-chip dedupe) held for the visual-redesign brief | Reserved 2026-09-04 by the options-validator status/dashboard review session; `docs/superpowers/plans/2026-09-04-37-dashboard-presentation-fixes-codex-brief.md` committed together with this row (rev 5, READY FOR HAND-OFF after four adversarial review rounds — round 4 PASS WITH FIXES, all applied; receipts `reports/2026-09-04-brief-37-adversarial-review-round{1,2,3,4}.md`). Highest number on disk at reservation time was 36; `ls` performed immediately before numbering; no untracked drafts present | Reserved and tracked together |
| 38 | Ritual evidence staging survives an absent allow-list path (Step 8 `git add` aborted on the uninstalled `reports/schwab_chains_intraday` since #150; 36 files unpersisted 09-03→09-06, rescued in `f83428d`) | Reserved 2026-09-06 by the ledger-durability diagnosis session; `docs/superpowers/plans/2026-09-06-38-ritual-evidence-staging-codex-brief.md` committed together with this row. Highest number on disk at reservation time was 37; `ls` performed immediately before numbering; no untracked drafts present | Reserved and tracked together |
| 39 | Attractiveness board redesign — agreement table (implementation landed via PR #159, squash `d2a280b`, 2026-09-07; deployed to the ops checkout the same evening) | Recorded retroactively 2026-09-08 by the receipt-regeneration session: the brief document `docs/superpowers/plans/2026-09-06-39-attractiveness-board-redesign-codex-brief.md` exists only on the unmerged branch `claude/board-redesign-spec-2026-09-06` (rev 8 @ `ad02d4c`, 2026-09-07) and was never added to this table; number 39 was in use, so it is reserved here to keep the sequence honest. The row does not merge that branch or make its draft canonical | Reserved retroactively; document untracked on `main` |
| 40 | H7 activation-day receipt chain — WP-A `tools/h7_schwab_data_gate_receipt.py` (the missing Schwab-mode durable data-gate receipt producer), WP-B `tools/h7_activation_day.sh` (source health → Schwab data gate → backup/restore → evidence commit in the ops checkout; prints the owner's activation command + an evidence template, never runs it; watcher step dropped in rev 2, R1-4), WP-C trading-calendar refusal in the pre-close capture (Labor Day 2026-09-07 package) | Reserved 2026-09-08 by the receipt-regeneration session; `docs/superpowers/plans/2026-09-08-40-h7-activation-day-receipt-chain-codex-brief.md` committed together with this row (rev 1, DRAFT FOR REVIEW; round 1 FAIL — 2 blockers, 4 HIGH, 7 MEDIUM, 1 LOW, receipt `reports/2026-09-08-brief-40-adversarial-review-round1.md`; rev 2 same day with all 15 applied; round 2 PASS WITH FIXES — 2 blockers rev 2 introduced, 2 HIGH, 5 MEDIUM, 2 LOW, receipt `reports/2026-09-08-brief-40-adversarial-review-round2.md`; rev 3 same day with all 11 applied, READY FOR HAND-OFF, owner-approved in-session 2026-09-08; Codex PR #161 @49e3114 impl-review round 1 FAIL/NOT READY `reports/2026-09-08-brief-40-implementation-review-round1.md`; Amendment A1 owner-directed 2026-09-08: restore-scan half of WP-A.11 reverted, backup coverage kept). Highest number on disk at reservation time was 38 on `main` and 39 on the unmerged spec branch; `ls` performed immediately before numbering; no untracked drafts present | Reserved and tracked together |

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

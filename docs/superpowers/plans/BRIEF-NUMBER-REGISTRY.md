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
| 28 | Event awareness | Untracked draft observed at `docs/superpowers/plans/2026-08-25-28-event-awareness-codex-brief.md`; SHA-256 `ef898909924e40f49abd794f75011a870590c1c18122ed3f4081f8bd8aefff03` | **RESERVED**; preserve in place, do not track until concurrent ownership is confirmed |
| 29 | Schwab inventory binding | Later untracked draft observed already bearing the requested number at `docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md`; SHA-256 `bc56c21a3d22dde77105871875d5b300b2cc08567b3bea2684142686b00c7d7a` | **RESERVED**; preserve in place, do not rename or track until concurrent ownership is confirmed |

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

---
name: daily-ritual
description: Use when Carsyn says "daily ritual", "run the board", "morning check", or asks for the current H5/H6/H7/H8/H10 operating status.
disable-model-invocation: true
---

# Daily Ritual (forward-paper operating board)

Operator order is frozen by H7 amendment v1.4 (2026-07-14), with the step
order updated by H10_RITUAL_ORDER_FIX (2026-07-24, facts.log). The order IS
the control: source health is recorded before the gate so the gate sees fresh
provenance, and every watcher runs behind a GO gate. Never reorder, never
skip a step because yesterday was fine.

## Choose the mode

| Request | Action |
|---|---|
| Current status, results, or "how about now" | Inspect the latest log, ritual-status receipt, capture receipt, and relevant ledgers. Do not run the ritual. |
| Explicitly run the ritual, board, or morning check | Apply the provider-policy preflight below before any execution. |

Never run this proactively. `tools/daily_ritual.sh` is the authoritative
source for both order and effects; do not replace it with hand-typed steps.

## Current provider-policy block

ThetaData acquisition is owner-disabled with no environment override
(`data/provider_policy.py`). Immutable cached reads remain allowed, but the
current script calls the non-dry-run `data/recent_topup.py` path, which refuses
before top-up or close refresh. Therefore the full ritual is currently
**NOT RUNNABLE**.

For an explicit run request, report this deterministic blocker and stop. Do
not treat an API key, subscription state, or a complete cache as an override;
do not skip top-up; and do not manually run the downstream consumers. Resume
only after the authoritative script has been reconciled with the frozen
provider policy through a separately reviewed change.

## Authoritative script contract

When the provider-policy block has been resolved, run only:

```bash
tools/daily_ritual.sh
```

It logs to `.tmp/daily_ritual/<stamp>.log`; read the log and report the
summary. It is branch-guarded: it refuses to run off `main` or when `main`
is not aligned with `origin/main`. A refusal is the system working — report
it, do not work around it.

The script is stateful. It can append receipt-bound H7 real-paper exit events,
append H10 observations, write receipts/reports/feature stores/dashboards,
stage and commit allow-listed evidence, fetch/merge/push `main`, and take a
restic snapshot. H7 exit fill/monitor runs outside the entry `GO` block so a
data-gate refusal does not imply zero mutations. Disclose these effects; never
describe the script or the full consumer sequence as read-only.

It does not place broker orders or authorize entries. Watcher output is
information for the owner, never an instruction to act.

## Report contract

Report the checkout/branch guard, provider-policy state, evaluation session,
source health, data-gate verdict, H7 exit results, each watcher lane, generated
artifacts, evidence commit/push outcome, backup outcome, terminal status, and
log path. Distinguish `SKIPPED`, `BLOCKED`, `BROKEN`, and a normal `WAIT`.

## Hard rules

- Never bypass the provider freeze, branch guard, gate order, or exact-session
  flags.
- Never hand-step around a blocked script or claim a partial manual sequence is
  the daily ritual.
- Never place a live order or manually record an owner decision. Mechanical
  real-paper exit events produced by the script are not owner entry authority.
- Never hand-edit ledger files to make a gate pass. The gate failing IS the
  system working.

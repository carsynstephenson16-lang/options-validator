---
name: daily-ritual
description: Run the owner-frozen H7/H6 daily operating sequence in its exact gate order (topup -> source health -> data gate -> watchers). Use when Carsyn says "daily ritual", "run the board", "morning check", or asks for today's H7/H6 status. User-invoked only — never run this proactively, and never run steps out of order.
disable-model-invocation: true
---

# Daily Ritual (H7 + H6 forward watch)

Operator order is frozen by H7 amendment v1.4 (2026-07-14), with the step
order updated by H10_RITUAL_ORDER_FIX (2026-07-24, facts.log). The order IS
the control: source health is recorded before the gate so the gate sees fresh
provenance, and every watcher runs behind a GO gate. Never reorder, never
skip a step because yesterday was fine.

## Default: run the script

`tools/daily_ritual.sh` is the owner-authorized, single source of truth for
the full sequence and every flag. Prefer running it over hand-typing steps:

```bash
tools/daily_ritual.sh
```

It logs to `.tmp/daily_ritual/<stamp>.log`; read the log and report the
summary. It is branch-guarded: it refuses to run off `main` or when `main`
is not aligned with `origin/main`. A refusal is the system working — report
it, do not work around it.

## Manual stepping (only when the script cannot run)

**Step 0 — recent-day top-up (needs ThetaData; skip iff sub inactive):**

```bash
uv run python data/recent_topup.py --scope h7 --refresh-closes
```

If closes (or any config) changed, downstream feature rebuilds are
mandatory, not optional.

**Step 1 — source health (run AND record; capture the printed receipt path):**

```bash
uv run python -m options_researcher.h7_source_health
```

Exit 1 = one or more names need an earnings refresh. Per amendment v1.4 this
is a PER-NAME entry ban enforced by the watcher's fail-closed gate — it does
NOT block the board. Do not "fix" it inline; the refresh path is the
owner-run `tools/h7_refresh_earnings.py` append-raw/promote flow.

**Step 2 — data gate (HARD GATE; the receipt flag is mandatory):**

```bash
uv run python -m options_researcher.h7_data_gate --source-health-receipt <receipt path printed by Step 1>
```

NEVER run the bare command: a gate receipt written without
`--source-health-receipt` is immutable and permanently revokes that
session's real-entry authority. Exit 0 (GO) is required to proceed. A NO_GO
**blocks the entire run** — stop here, report which names failed and why,
and do not run any watcher. There is no override in this skill.

**Steps 3+ — consumers, in script order.** After the gate, run the remaining
steps in the exact order `tools/daily_ritual.sh` implements them (currently:
H7 exit management -> QM OHLCV refresh -> attractiveness feature rebuild ->
`h7_watch` -> `h6_features --as-of` -> `h6_watch --as-of` -> H5
`entry_watch` -> H10 watch/observe -> dashboards). Read the script for the
exact flags rather than trusting this list — the script is authoritative,
and the H6 commands are exact-session (`--as-of YYYY-MM-DD`, same evaluation
date as above, never "default to today"). Watcher output is alerts only: an
ENTRY-OK line is information for the owner, never an instruction to act.

## Hard rules

- This ritual takes ZERO book actions from a chat session. It reads, gates,
  and reports. Any entry/exit decision is the owner's, recorded through the
  proper ledger/positions flow — never by this skill.
- Never hand-edit ledger files to make a gate pass. The gate failing IS the
  system working.
- Report the end state honestly: per-name health, gate verdict, watcher
  lanes, H6 eligibility. "All WAIT" is a normal, successful day.

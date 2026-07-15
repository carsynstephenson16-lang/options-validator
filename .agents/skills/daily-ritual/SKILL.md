---
name: daily-ritual
description: Run the owner-frozen H7/H6 daily operating sequence in its exact gate order (topup -> source health -> data gate -> watchers). Use when Carsyn says "daily ritual", "run the board", "morning check", or asks for today's H7/H6 status. User-invoked only — never run this proactively, and never run steps out of order.
disable-model-invocation: true
---

# Daily Ritual (H7 + H6 forward watch)

Operator order is frozen by H7 amendment v1.4 (2026-07-14). The order IS the
control: source health is recorded before the gate so the gate sees fresh
provenance, and the watcher only runs behind a GO gate. Never reorder, never
skip a step because yesterday was fine.

## Sequence

**Step 0 — recent-day top-up (needs ThetaData terminal; skip iff sub inactive):**

```bash
uv run python data/recent_topup.py --scope h7 --refresh-closes
```

If closes changed (or any config changed), H6 features are stale — Step 4's
rebuild is then mandatory, not optional.

**Step 1 — source health (run AND record):**

```bash
uv run python -m options_researcher.h7_source_health
```

Exit 1 = one or more names need an earnings refresh. Per amendment v1.4 this
is a PER-NAME entry ban enforced by the watcher's fail-closed gate — it does
NOT block the board. Do not "fix" it inline; the refresh path is the
owner-run `tools/h7_refresh_earnings.py` append-raw/promote flow.

**Step 2 — data gate (HARD GATE):**

```bash
uv run python -m options_researcher.h7_data_gate
```

Exit 0 (GO) is required to proceed. A NO_GO **blocks the entire run** — stop
here, report which names failed and why, and do not run the watcher. There is
no override in this skill.

**Step 3 — H7 watcher (alerts only):**

```bash
uv run python -m options_researcher.h7_watch
```

Read-only alerts against frozen triggers. An ENTRY-OK line is information for
the owner, never an instruction to act.

**Step 4 — H6 leg:**

```bash
uv run python -m options_researcher.h6_features   # rebuild if closes/config changed
uv run python -m options_researcher.h6_watch
```

## Hard rules

- This ritual takes ZERO book actions. It reads, gates, and reports.
  Any entry/exit decision is the owner's, recorded through the proper
  ledger/positions flow — never by this skill.
- Never hand-edit ledger files to make a gate pass. The gate failing IS the
  system working.
- Report the end state honestly: per-name health, gate verdict, watcher
  lanes, H6 eligibility. "All WAIT" is a normal, successful day.

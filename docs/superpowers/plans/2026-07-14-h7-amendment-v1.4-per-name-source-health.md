# H7 amendment v1.4 — per-name source-health exclusion (owner "Fix B")

**Owner decision 2026-07-14.** Trigger: CoreWeave has not published an official
Q2 2026 report date (IR quarterly-results and events pages checked 2026-07-13;
Nasdaq shows no date). Under the v1.0–v1.3 operator order, one name's silent IR
department blocks the daily watch for all 12 names. The owner directs that this
stop being a whole-board block.

## What changes (operator order only)

Old (v1.0–v1.3): `source health → data gate → watcher; never run the watcher
when either preceding command is non-zero.`

New (v1.4):

1. `h7_source_health` remains the mandatory first step of every run and its
   per-name output is recorded with the run. Its non-zero exit **no longer
   forbids running the watcher.**
2. `h7_data_gate` must remain exit 0 (whole-universe GO). A gate NO_GO still
   blocks the watcher run entirely — data completeness is not negotiable.
3. `h7_watch` runs; any name whose earnings provenance is not healthy at the
   evaluation cutoff is **entry-banned by the already-registered fail-closed
   gate** (unknown next report → `EARNINGS-UNKNOWN`, no entry —
   `options_researcher/h7_watch.py` decide-lane gating). The run report must
   list which names were source-excluded.

## What does not change

- The per-name fail-closed entry ban itself (registered since v1.0). CRWV can
  never take an entry while its next report date is unknown. "Fix B" does not
  admit CRWV; it stops CRWV from silencing the other 11 names.
- `H7_EARNINGS_BAN_SESSIONS=5`, all lane definitions, structures, exits,
  sleeve rules — no strategy parameter changes.
- The prohibition on promoting aggregator-estimated dates as gating evidence
  (7b-2R.2 citation contract). The 2026-08-11 CRWV aggregator estimate stays
  diagnostic-only.
- Stage 8 remains closed. Activation readiness continues to report source
  health honestly; sub-12/12 health remains an activation input for owner +
  independent review. This amendment governs the daily read-only watch only.
- Stage-3/Stage-4 event causality (`source_health` events as required causes)
  is unchanged.

## Why this is safe

The whole-board block was a belt-and-suspenders rule from the era when the
watcher's per-name gating was unproven. Stage 7's synthetic proof (commit
b632feb, independent review PASS) exercised the fail-closed refusal arcs; the
per-name gate is now test-verified, so the redundant board-wide block adds
operational fragility (one IPO-year name with a quiet IR page halts research
on eleven liquid names) without adding integrity.

## Ledger

Recorded as `H7_AMENDMENT_V1_4` in `ledger/facts.log` with this document's
SHA-256. Governance docs updated in the same commit: `CLAUDE.md`, `README.md`
(operator-order wording), `AGENTS.md` if it restates the operator order.

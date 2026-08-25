# Chain-Consistency Observation Runbook (Candidate F review)

**Created:** 2026-08-25. **Authority basis:** the owner-ratified verification
addendum (`docs/plans/2026-08-25-research-integration-plan-verification-addendum.md`,
findings 6–7 and the §4 ratified decision table) assigns Candidate F an
observation/retention review with a named operator, cadence, and a falsifiable
acceptance criterion. This runbook is that assignment. It is **research-only**:
it grants no authority over rankings, grades, Top-3, verdicts, sizing, risk,
capture acceptance, or orders, and it is **explicitly not part of the frozen
daily ritual** (`.agents/skills/daily-ritual/SKILL.md`) — the ritual's operator
order is a registered control and is not amended by this document.

## Operator and cadence

- **Operator:** the owner, or a Claude session acting at the owner's direction
  within a normal working session. No scheduler, LaunchAgent, hook, or script
  wiring during the observation phase — manual runs only (ratified scope).
- **Cadence:** once per **new Schwab preclose capture date**. When a new date
  appears under `.cache/schwab_chains/`, run the audit for the newest
  consecutive session pair. A missed run is made up at the next session; the
  tool's pair selection handles gaps (`GAP_SESSION` is an expected flag, not a
  failure).

## The run

```bash
uv run python tools/chain_consistency_audit.py --out-dir reports/chain_consistency
```

- No `--pair` needed: the tool selects the latest consecutive pair itself.
  `--pair PREV CUR` (ISO dates) reruns a specific historical pair.
- `--out-dir reports/chain_consistency` is **required for review runs**: the
  default output directory is `.tmp/chain_consistency/` (ephemeral) and the
  tool only permits these two destinations. Receipts accumulating toward the
  retention decision must be durable, so review runs write to
  `reports/chain_consistency/` and get committed as evidence.
- The tool is read-only on caches, offline, and writes one immutable receipt
  (`chain_consistency_<session>_<hash12>.json`); it prints the receipt path.

After each run, append one row to the disposition log below. "Actioned" means
the flag caused a documented data correction or investigation — that is the
only category that counts toward retention.

## Disposition log

| Date run | Pair | Receipt | Flags seen | Disposition (actioned / expected / noisy) | Note |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Acceptance criterion (ratified, falsifiable)

At approximately **30 captured sessions** (the existing owner disposition's
review horizon, not a statistical proof threshold):

- **Default outcome: REMOVE.** If no flag has caused a documented data action
  over the horizon, the tool is removed (receipts are retained as history).
- **KEEP-MANUAL** requires an explicit owner override with a recorded reason.
- **PROCEED-TO-SEPARATE-DESIGN** (any integration beyond manual runs) requires
  documented actionable use and its own owner-approved brief.
- **Threshold tuning to make history look clean is prohibited** in all cases.
  SPREAD_BLOWOUT stays computed/receipted but demoted from headline status per
  owner disposition A (2026-08-24, commit `107c7b9`); its pre-declared
  remove-if-unactioned review folds into this same horizon.

## Known constraints (disclosed up front)

- As of 2026-08-25 only **4 capture dates** exist (2026-08-14/19/20/24) against
  the ~30-session horizon — expect the review to take months of natural
  accumulation, and state progress in wall-clock terms when reporting.
- Underlying closes are a data dependency: on 2026-08-24 all 15 raw closes were
  missing for the fill study's decomposition. If closes are missing for a pair,
  the audit's affected checks degrade — record that in the log rather than
  substituting data.
- Post-cutoff captures inspected here remain **descriptive data-quality
  evidence only** (no OOS look is spent, and no directional judgment may be
  formed from flag contents — addendum finding 12's labeling discipline).

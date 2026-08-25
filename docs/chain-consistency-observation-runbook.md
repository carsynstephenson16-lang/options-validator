# Chain-Consistency Observation Runbook (Candidate F review)

**Created:** 2026-08-25 (rev 2, post-adversarial-review — abort semantics,
checkout prerequisite, pair-selection and flag-reading corrections).
**Authority basis:** the owner-ratified verification addendum
(`docs/plans/2026-08-25-research-integration-plan-verification-addendum.md`,
findings 6–7 and the §4 ratified decision table) assigns Candidate F an
observation/retention review with a named operator, cadence, and a falsifiable
acceptance criterion. This runbook is that assignment. The ratification's
wording left the runbook's own creation ambiguous ("specific runbook wiring
remains the next separately authorized action"); this document takes the
conservative reading — it wires nothing, schedules nothing, and amends no
operational control — and the owner may veto it like any delegated recording.
It is **research-only**: it grants no authority over rankings, grades, Top-3,
verdicts, sizing, risk, capture acceptance, or orders, and it is **explicitly
not part of the frozen daily ritual** (`.agents/skills/daily-ritual/SKILL.md`)
— the ritual's operator order is a registered control and is not amended by
this document.

## Operator and cadence

- **Operator:** the owner, or a Claude session acting at the owner's direction
  within a normal working session. No scheduler, LaunchAgent, hook, or script
  wiring during the observation phase — manual runs only (ratified scope).
- **Cadence:** once per **new Schwab preclose capture date**. When a new date
  appears under `.cache/schwab_chains/`, run the audit; it takes the latest two
  captured sessions per symbol. Captures are sparse, so most pairs are not
  calendar-adjacent — the calendar gap between them is exactly what the
  `GAP_SESSION` flag measures, not a failure. A missed run is made up at the
  next session.

## Prerequisites (check BEFORE running)

1. **Checkout:** run from a checkout whose HEAD contains
   `tools/chain_consistency_audit.py` (on `main` since PR #72) **and** which
   holds the `.cache/schwab_chains/` captures — the tool reads caches relative
   to its own repo root. As of 2026-08-25 the capture cache lives in the
   primary checkout (`~/options-validator`), whose branch predates the tool;
   sync that checkout with `main` before the first review run, or run wherever
   both conditions hold.
2. **Underlying closes:** the close cache (`.cache/underlying/`) must cover the
   latest capture date. It is populated by the existing authorized capture/
   ritual lanes — do not fetch closes manually for this runbook. **A missing
   close aborts the entire run (exit 1, no receipt is written)** — one missing
   symbol kills the run, there is no partial/degraded mode. If that happens,
   record the aborted attempt in the log and rerun after closes land. (As of
   2026-08-25, closes stop at 2026-08-21 while the latest capture is
   2026-08-24, so the auto-selected pair aborts until the close lane catches
   up.)

## The run

```bash
uv run python tools/chain_consistency_audit.py --out-dir reports/chain_consistency
```

- No `--pair` needed: the tool takes the latest two available captures (per
  symbol). `--pair PREV CUR` (ISO dates, PREV earlier) reruns a specific
  historical pair.
- `--out-dir reports/chain_consistency` is **required for review runs**: the
  default output directory is `.tmp/chain_consistency/` (gitignored,
  ephemeral) and the tool only permits these two directories (and their
  subdirectories). Receipts accumulating toward the retention decision must be
  durable, so review runs write to `reports/chain_consistency/` and get
  committed as evidence.
- The tool is read-only on caches, offline, and writes one immutable receipt;
  it prints the receipt path. **Note:** the filename's session token is the
  latest session across the whole cache, not the audited pair — for `--pair`
  reruns the filename will not identify the pair, so always record the actual
  pair in the log row.

## Reading the result

Judge each run on the receipt's **`flag_counts`**, not the headline `status`.
`GAP_SESSION` sits first in the flag precedence and is not headline-demoted,
so with sparse captures the worst-wins `status` will read `GAP_SESSION` on
most pairs and mask any EXPIRY_VANISHED / STRIKE_VANISHED / DELTA_JUMP
underneath. The counts carry the retention evidence.

After each run, append one row to the disposition log below. "Actioned" means
a flag caused a documented data correction or investigation — that is the only
category that counts toward retention.

## Disposition log

| Date run | Pair (PREV→CUR) | Receipt | flag_counts summary | Disposition (actioned / expected / noisy / aborted) | Note |
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
  owner disposition A (2026-08-24, `107c7b9`, PR #73); its pre-declared
  remove-if-unactioned review folds into this same horizon.

## Known constraints (disclosed up front)

- As of 2026-08-25 only **4 capture dates** exist (2026-08-14/19/20/24) against
  the ~30-session horizon — expect the review to take months of natural
  accumulation, and state progress in wall-clock terms when reporting.
- The close-cache dependency above means capture days can be temporarily
  un-auditable; an aborted run is a data-freshness fact worth logging, never a
  reason to substitute or hand-build a close.
- Post-cutoff captures inspected here remain **descriptive data-quality
  evidence only** (no OOS look is spent, and no directional judgment may be
  formed from flag contents — addendum finding 12's labeling discipline).

# Pick tracker forward window — DRAFT registration packet

**Status: DRAFT — NOT REGISTERED.** This file does not authorize scored
writes, a historical run, a backfill, deployment, an ops-checkout sync, or a
ledger append. Every frozen value and the final registration wording remain
blank for the owner to type through the repository's typed registration path.
Dry-run rows are permanently excluded from any later registered window.

## Study question and authority

Does the pre-registered `context_lane` shortlist have a different normalized
incremental-option-leg outcome from the `frozen_baseline` shortlist during a
future entry window? The tracker is descriptive, non-verdict-bearing, and
cannot rank, size, gate, activate, or trigger a trade. A2-v1 (ledger seq 19/27)
retains interpretive authority for board-level outcome questions.

The owner requested roughly two months of entries. The proposed 42 XNYS
sessions are the **entry window only**. A LEAPS pick entered on the last entry
session can require another 126 sessions (roughly six months) to reach its
longest mark, so the final settled answer arrives months after entries close.

## Frozen design proposed for owner typing

- Scored arms: exactly `frozen_baseline` and `context_lane`.
- Primary contrast: `context_lane - frozen_baseline` normalized return on the
  frozen, lane-specific risk basis.
- Membership event: first entry of an `(arm, symbol, lane)` shortlist slot.
  Re-strikes while the slot stays present are annotations, not new entries;
  exit followed by re-entry is a new event.
- Decision/fill split: decision on verified session D; fill at the conservative
  executable side of the first verified candidate among D+1 and D+2 XNYS
  sessions. A missing/invalid exact contract on that first verified candidate
  cancels; it never hunts a later price.
- Evaluated P&L: the one incremental option leg only. Coverage holdings are
  frozen provenance and normalization context, never marked into pick P&L.
- Marks: LEAPS 21/63/126 sessions and tactical long calls 5/10/20 sessions
  (registered A2 schedule). Proposed income-lane marks are 5/10 sessions plus
  21 only when fill DTE is greater than 30 calendar days. The income schedule
  is LLM-proposed and remains unregistered until the owner types it.
- Aggregation: weekly non-overlapping entry cohorts. Raw dollars stay inside
  lane tables. The primary contrast equal-weights only lanes represented in
  both arms within each cohort; unmatched lanes are disclosed, not imputed.
- Uncertainty: point summaries always render. An exploratory two-week
  moving-block bootstrap interval starts only at eight chronological paired
  cohort contrasts; before then the report says `INSUFFICIENT_COHORTS`.
- Entry window proposal: 42 XNYS sessions. No extension after outcomes begin.
- Context interruption: the first admissible scored session is the later of
  the owner-typed registration and the first exact `origin/main` session with
  `CONTEXT_LANE_ENABLED = True`. A later disable records `LANE_DISABLED`; the
  window is not silently shortened or extended.
- Experiment lanes are descriptive nominations only. They receive no P&L,
  winner language, or promotion authority; scoring one requires a new
  registration.

## Feasibility and cancellation projection — incomplete hard gate

The active feasibility rule warns that "Running the check on many candidate
designs and picking the best is exactly the overfitting this repo exists to
prevent, and remains banned." This packet fixes two arms and one contrast in
advance; it is not a run-many/pick-best sweep and is not loss-gated. The
feasibility gate's loss trigger is specifically a design "with a loss-gated
verdict"; this tracker has no verdict. Any later attempt to promote, rank, or
select from these results is a separate owner decision and must re-enter the
repository's hypothesis-authority rules.

| Proposal | Provenance and status |
|---|---|
| 42-session entry window | Owner-selected 2026-08-25 after parameter audit; still unregistered until typed |
| Income marks 5/10, conditional 21 | LLM-proposed 2026-08-25 and audit-amended; owner-selected but still unregistered until typed |
| CI after 8 paired cohorts, block length 2 weeks | LLM-proposed 2026-08-25; exploratory only and still unregistered until typed |
| D+1/D+2 fill bound | Brief 27 rev-6 decision/fill contract, derived from ledger seq 21 discipline; still unregistered until typed |

The owner's spoken 2026-08-25 pre-acceptance is ex ante and incomplete until
all three current measurements below are inserted and quoted verbatim. This
implementation did **not** run historical tracker data or backfill them.

| Required readiness measurement | Value and provenance |
|---|---|
| (a) membership-entry events per arm per week under slot keying | ____ (tool-computed; current verified captures preferred; frozen ThetaData history only as an explicitly labeled proxy) |
| (b) expected cancellation rate under the exact D+1/D+2 rule | ____ (tool-computed from then-current verified-capture density; every missing candidate session counted) |
| (c) minimum required verified captures per week | ____ (tool-computed) |

If (b) exceeds 50% or (a) is below one event per arm per week, return the
packet to the owner for fresh confirmation before typing. Pre-acceptance does
not cover materially worse measured numbers.

Registration presentation is also blocked until a fresh owner/operator health
check proves the relevant repair is present and at least five consecutive
trading-session daily receipts committed cleanly; any gap or failed commit
resets the streak.

## Owner-typed blanks

| Field | OWNER TYPES at ratification |
|---|---|
| Namespace/version | ____ |
| Exact registration timestamp and ledger sequence | ____ |
| Entry-window first admissible session | ____ |
| Entry-window length (proposal: 42 XNYS sessions) | ____ |
| Income-lane mark schedule (proposal: 5/10, +21 only when fill DTE > 30) | ____ |
| Fill search bound (proposal: D+1/D+2) | ____ |
| Eight-cohort CI threshold and two-week block length | ____ |
| Projection (a), quoted verbatim | ____ |
| Projection (b), quoted verbatim | ____ |
| Projection (c), quoted verbatim | ____ |
| Five-clean-receipt health evidence paths/SHAs | ____ |
| Starvation/cancellation pre-acceptance or re-confirmation wording | ____ |
| No-extension clause acceptance | ____ |

## Owner/operator post-merge deployment checklist — worker must not execute

1. Confirm the implementation PR was separately approved and merged. A green
   draft is not merge or deployment authority.
2. After the 15:50 capture completes and before the next 07:10 ritual, record
   `git -C ~/options-validator-ops rev-parse HEAD` as the pre-sync SHA.
3. Follow
   `docs/superpowers/plans/2026-08-13-08-fork-healing-ops-sync-canary-runbook.md`
   and perform only the owner-authorized fast-forward operation.
4. Record the post-sync ops SHA and prove it equals the authorized merge SHA.
5. Verify the next ritual log contains the isolated pick-tracker recorder and
   evaluator steps. Do not treat checkout alignment alone as health evidence.
6. Establish the five-consecutive-clean-receipt streak before presenting this
   packet for typing; a gap or failed commit resets the count.
7. Insert measurements (a), (b), and (c). If either re-confirmation threshold
   fires, stop for the owner.
8. Only the owner types the blanks and invokes the typed registration path.
   Scored writes begin no earlier than the resulting first admissible session;
   dry-run data is never copied or promoted.

## Mandatory report header

> DESCRIPTIVE ONLY — NOT A TRADE RANKING; no verdict authority; dry-run rows
> are permanently excluded from any registered window; A2-v1 (ledger seq
> 19/27) retains interpretive authority for board-level outcome questions;
> CONCENTRATION: picks are drawn from one 18-name AI-infrastructure board and
> are correlated — the effective sample is far smaller than the row count.

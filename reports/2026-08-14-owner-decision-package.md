# Owner decision package — 2026-08-14 (assembled by the orchestrating session)

Every open decision surfaced by today's six-agent audit fleet, organized by
when Carsyn can act. Nothing here is decided by an agent; recommendations are
labeled and each cites its source document. Two inputs were pending at
assembly time and are marked ⏳: the 15:45 canary result and the brief-09
variant menu (in flight).

## Already decided (recorded; no action needed)

- Starvation → REDESIGN over pre-accept (owner, 2026-08-13, in-session).
- Ritual switch-on directed (owner, 2026-08-14: "I want to switch it back
  on") — implementation spec is rev-2.1 (`docs/superpowers/plans/
  2026-08-14-11-ritual-switch-on-rev2-spec.md` @e2baeb4, adversarially
  reviewed PASS WITH FIXES, all 18 findings applied).
- 10:00 ET second chain capture directed (owner, 2026-08-14) — DEFERRED to
  after switch-on; rev-1 spec FAILED review on receipt-poisoning grounds
  (`reports/2026-08-14-brief-10-adversarial-review-receipt.md`); needs its
  own new spec.
- PR #36 merge (owner, 2026-08-14 10:28 ET). Aftermath handled: ops+research
  realigned 14:28-14:56 ET; canary gate re-verified ALIGNED.

## Group 1 — typeable NOW (independent of canary result)

1. **Train GO** (unblocks tonight's sequence): authorize merging, in order,
   `wt/recovery-slice-b-backup-0814` (97fda34) → run backup/restore drill →
   `wt/recovery-slice-a-earnings-0814` (bc74234) → stale-doc fixes
   (PROJECT_STATE B2 line; file the missing B2 review receipt). All branches
   are main+1, suite 2884/2887 green, ruff+pyright clean; slice B red-test
   proven. Merges are owner-gated; one word covers the batch.
2. **D-1 hypothesis fence** (rev-2.1 §D-1): which of H5/H6/H8/H10 ritual
   observation steps resume under data-only authority. Recommendation F1:
   none — all five are chain-starved anyway; resuming ledger-appending
   (h10_observe) or FIRE-capable (entry_watch) steps under data-only
   authority would be pre-registration dishonesty for zero fresh data.
3. **D-2 switch-on flip** (`ritual_data_phase_active=True` once rev-2.1 is
   implemented + landed): honest delivery = running ritual, fresh OHLCV for
   the 9-name watch universe ONLY (closes store stays frozen at 2026-08-05),
   daily dashboard rebuilds, legible per-lane starvation record. NOT fresh
   hypothesis signals; research refresh stays blocked until registration
   day. Recommendation: yes, with that expectation.
4. **D-3 capture-wrapper alignment-gate relaxation** (rev-2.1 §D-3).
   Recommendation: yes.
5. **D-4 source-activation bar S1** (three consecutive unattended verifying
   preclose sessions before `exact_session_source_active=True`;
   LLM-proposed). Includes the C-f fork: add an invocation-provenance
   receipt field (a hashed-file change) OR drop the "unattended" condition.
6. **D-6 intra-day alignment check** (NEW, born from today's real 4-hour
   behind-window): scheduled pre-15:45 alignment check (new plist = standing
   config) vs documented manual habit vs accept the risk.
7. **OD-3 namespace wording** (gate packet `reports/h7_forward_schwab/
   2026-08-09-owner-gate-packet.md`): typeable now; non-operative until
   registration. Also re-type the 08-13 redesign decision into the packet's
   designated slot (provenance hygiene; currently prose-only).
8. **$16k vs $14k ruling** (financial audit): `H4_THESIS_MAX_PREMIUM_TOTAL
   = 16_000` structurally exceeds `RISK_SLEEVE = 14_000`; the $16k amendment
   lived only in the advisory facts log, never the chained ledger. Dormant
   (no LEAPS open). Rule: intentional, or cap to sleeve.
9. **RQ2 V1 statistic pin** (unrelated to H7; pre-result amendment,
   owner-typed). Can wait; listed for completeness.

## Group 2 — after pending inputs land

10. **Variant pick + frozen numbers** ⏳ needs the brief-09 frequency-only
    menu (Opus build in flight on `wt/brief09-variant-menu-0814`, based on
    slice A). Owner picks the variant and types every frozen number;
    feasibility gate: expected entries ≥ 20 (2× loss bar 10) or explicit
    pre-accept quoting the computed number.
11. **Registration authorization** ⏳ needs: canary verified + drill receipt
    + variant picked + ONE reconciled feasibility receipt (financial audit:
    repo currently holds 3/1050 on main vs 4/1050 on the unmerged branch;
    fresh receipt after slice A supersedes both and re-binds config_hash).
12. **h7_active flip** — strictly last. The 2026-08-09 PREPARED patch must
    be REGENERATED (rev-2.1 C-c: the third flag breaks both its hunks).

## Available on request (agent-doable, no decision required)

- `SHORT_CONTEXT_ENABLED=True` (FINRA short-interest display lane).
- Attractiveness experiments dashboard runs (explicit invocation by design).
- Stale-branch cleanup batch (guard + untracked check each, per rule).

## Canary status

⏳ At assembly time: gate re-verified ALIGNED at c96ed4b (14:56 ET);
scheduled fire 15:45 ET. Result appended below when known.

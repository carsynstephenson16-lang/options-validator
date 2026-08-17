# H10a-v2 re-registration packet — DRAFT (owner-typed registration required)

**Status: DRAFT. Nothing here is registered.** Provenance: owner directive
2026-08-16 ("reopen h10a"), recorded in
`reports/2026-08-16-owner-directives.md`. Because H10a (seq 15) was
adjudicated 2026-08-16 (facts.log `H10A_RESULT`: INSUFFICIENT_SAMPLE —
STARVED, 0 trades), the append-only ledger and the H7/OD-3 precedent require
a **new registration under a new namespace**, not an un-close. New
registrations are owner-typed — this packet only prepares the decision.

## Proposed design (carry-over, no parameter changes)

H10a-v2 = the seq-15 design verbatim (QM parabolic long-continuation, forward
paper only; defined-risk single long call, premium <= $600; delta 0.40–0.60
within +/-10% of spot; 30–60 DTE; H7-admission universe re-measured at entry;
mid-or-worse fills + haircut + commissions; 1 contract; own $2k/month cap;
earnings-skip; per-name source-health entry ban; exits +100% / 20 sessions /
21 DTE; 7-loss bar) with exactly two changes:

1. **Data source:** Schwab 15:45 ET preclose chain captures (the canary-proven
   lane) instead of the dead ThetaData feed — same substitution language as
   H10B_AMENDMENT_V1_1 clause 2 **rev 2** (review FX-I: the rev-2 clause adds
   the declared 15:45-vs-close timing convention, the Schwab IV percent→
   decimal normalization obligation, and fail-closed capture verification —
   all inherited here).
2. **Window:** new forward window, opening on the owner-typed registration
   date and ending on an owner-typed end date (blank left for the owner; the
   v1 window length was ~2.5 months; the v1 verdict said starvation, so a
   longer window is worth considering — owner's call, not proposed as a
   number here).

The v1 disclosures carry forward verbatim: outcome-informed SELECTION
disclosure (the signal's origin study had seen outcomes) and the
weaker-verdict disclosure. The v1 STARVED result stays on the record as v1's
result; v2 does not reinterpret it.

## Feasibility gate (2026-07-24) — must be confronted, not skipped

The gate requires projected entries >= 2x the loss bar over the window, OR an
explicit owner starvation pre-acceptance quoting the computed number. v1's
observed base rate (3 usable sessions, 0 fires, 11 names) cannot honestly
project 14+ entries. The fresh precedent is the H7 owner ruling recorded
2026-08-16 (PR #57): starvation pre-acceptance with the receipt-bound number
quoted (3 vs bar 14). The owner should either:

- **(a)** pre-accept starvation for H10a-v2, quoting a freshly computed
  receipt-bound expected-entries number over the chosen window (a
  feasibility run against the Schwab-capture universe is required first), or
- **(b)** choose a window long enough that the computed projection clears the
  bar, or
- **(c)** decline to re-register (the v1 STARVED verdict already stands as a
  legitimate outcome).

## Owner-typed blanks

| Field | Value (OWNER TYPES at ratification) |
|---|---|
| Namespace | H10a-v2 (proposed; owner may rename) |
| Window open | ____ (ratification day; owner selected 2026-08-17: proceed) |
| Window end | ____ (owner selected 2026-08-17: same-as-v1 length, ~2.5 months ⇒ ≈2026-11-01 if ratified now; exact date typed at ratification) |
| Feasibility disposition | **pre-accept starvation** (owner selected 2026-08-17), quoting the freshly computed receipt-bound number (base rate measured on ThetaData history, labeled as such — H7 3-vs-14 precedent) |

## Ordered steps

1. Independent adversarial review of this packet.
2. Fresh feasibility computation, receipt-bound, with its measurement window
   and feed stated explicitly (review FX-K): as of this draft the Schwab lane
   has only 1–2 sessions of chain history, so an honest projection must
   either use the frozen ThetaData history for the BASE-RATE estimate
   (labeled as measured-on-ThetaData, the H7 3-vs-14 precedent) or wait for
   Schwab sessions to accumulate — a 2-session base rate would be no more
   informative than v1's.
3. Owner types the blanks and ratifies; registration appended via the typed
   ledger API by the owner or an explicitly authorized agent in that session.
4. Watcher implementation (shared with the H10b/H5 re-pointing Codex brief) —
   NOTE (review FX-J): "H10a-v2" is not a free string; `h10_watch.py` and
   `hypothesis_evidence.py` hardcode the `{"H10a","H10b"}` namespace set and
   ordering, so a third namespace breaks existing invariants and the brief
   must extend those surfaces deliberately, with tests.

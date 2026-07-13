# H7 Stage 5 global-risk amendment — reservation continuity

**Status: PRE-REGISTRATION CANDIDATE. BUILD-ONLY, SYNTHETIC-ONLY, INACTIVE.
This amendment introduces no parameter and does not authorize a real forward
event or Stage-8 activation.**

Independent implementation review found a concurrency gap between a recorded
board acceptance and its later `entry_intent`. The Stage-5 spec's reservation
rule is therefore tightened as follows before the implementation checkpoint:

1. A Stage-5 `board_resolution` acceptance is an immediate provisional
   reservation of its underlying, lane-c seat when applicable, and action
   at-risk in the calendar month of its planned T+1 fill.
2. The caused `entry_intent` atomically replaces exactly that provisional
   reservation. Its decision session, planned fill session, exact accepted
   action, and decision at-risk must match; a changed ledger head or changed
   economics fails closed.
3. If no intent materializes, the provisional reservation may be released
   only at or after the planned-fill session close by a deterministic
   `lane_displaced` event caused by the board, with reason
   `intent_materialization_missing`. It cannot be released early or by mutable
   book state. Reruns are idempotent and a stale head refuses.
4. Fill-time capacity decisions record the complete pre-substitution snapshot:
   actual month usage, every other reservation and its identity, open position
   identities, open symbols, lane-c occupancy, sleeve remaining, the replaced
   reservation, projected totals, constraints, frozen limits, and canonical
   snapshot hash.
5. Reconciliation remains read-only and pending board/intent reservations are
   reported separately from the legacy CSV rows.

This amendment closes a safety race; it does not change candidate order,
position size, sleeve amount, concurrency limits, scoring, or activation.


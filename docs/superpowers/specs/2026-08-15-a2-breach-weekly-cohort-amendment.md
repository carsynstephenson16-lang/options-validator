# A2-v1 amendment — breach-arm and weekly-cohort definitions (historical pass only)

**Date:** 2026-08-15
**Provenance:** owner-delegated standing 2026-07-25. Independent adversarial
review: Opus subagent, 2026-08-15 session (verdicts PASS-WITH-CHANGES; all
required changes are incorporated below). Independent claim verification:
Sonnet subagent, same session (all Codex handoff claims verified at branch
tip `1075c74`). Drafted and recorded by the main session (model
claude-fable-5) after reading both reports, cross-checking the duplicate-arm
finding against the Sonnet evidence, and rewriting Codex's proposed
definitions to incorporate every blocking change — that review-and-record act
is the Fable-session sign-off contemplated by the 2026-07-25 standing; no
separate approval ceremony occurred and none is claimed. Owner veto: by
further append-only amendment (a decision note was surfaced to the owner
in-session; precedent note — the sibling fixed-horizon pin in
`RQ2_A2_PIN_ADDENDUM_V1` clause (i) was owner-typed, so the owner may prefer
to ratify these personally; until any veto, this recording stands).
**Scope:** the A2-v1 HISTORICAL exploratory pass only. Forward-window cadence
and forward dates remain unpinned and deferred to owner approval.
**Registered basis being filled (ledger seq 19, quoted):** the arm named
"breach-defensive with breach followed by hold to 21 DTE then mechanical
close" (no trigger defined anywhere), and "weekly non-overlapping cohorts for
inference" (no board pinning defined anywhere). Neither definition below
introduces a new frozen number; both use already-registered quantities
(short-put strike, 21 DTE, 15-name universe) plus the ISO-week calendar
convention.

## Definition 1 — breach arm (amended from Codex proposal)

1. **Breach trigger:** the first EOD underlying close strictly below the
   short-put strike. ("Strictly below" inherits the repo's settlement
   convention at `a2_panel.py:347` — `raw[expiry] < strike` and
   `max(strike - close, 0)`; the `<=` in the 21-DTE test inherits
   `a2_panel.py:296`. The asymmetry is inherited, not chosen.)
2. **Breached path:** close at the next available trading-session close on or
   after the first session at or below 21 DTE, and never earlier than t+1
   relative to the breach session (same-bar execution prohibited; matches the
   registered T+1 entry convention).
3. **No-breach path (pinned):** hold to expiration settlement (the existing
   settlement branch). The arm is therefore assignment-accepting on unbreached
   paths and a 21-DTE mechanical close on breached paths — distinct from both
   `close_21_dte` and `assignment_accepting`. The report MUST state the
   observed duplication rate against `close_21_dte`.
4. **Missing exit quote:** if the pinned exit session is at or after
   expiration, resolve by expiration settlement from the raw close — never
   skip. Any other missing exit quote is a counted skip with no substitution.
   The report MUST break out breach-arm skip counts by breached vs.
   unbreached, and MUST disclose that one arm's data gap propagates to all
   five arms and to cohort completeness (the all-arms-or-none rule at
   `a2_panel.py:381`).

## Definition 2 — weekly cohorts (amended from Codex proposal)

1. **Candidate board:** the earliest complete 15-name decision board in each
   ISO week. That board is the week's ONLY candidate; a week whose candidate
   fails the spacing test is skipped and counted. A partial board is never
   tercile-split; if no complete 15-name board ever exists, the variant
   reports `no data` (fail-closed).
2. **Spacing rule (replaces Codex's realized-resolution rule, which was
   rejected as outcome-dependent):** a candidate cohort is accepted only when
   its T+1 entry occurs strictly after the previous accepted cohort's
   EX-ANTE maximum possible resolution date, known at entry: the selected
   contract's expiration for `capture_50`, `breach_hold_21_dte`, and
   `assignment_accepting`; the 21-DTE session for `close_21_dte`;
   min(10 sessions, expiration) for `fixed_10_sessions`; the stated horizon
   for LEAPS/tactical lanes. Cohort membership is thereby independent of
   realized returns.
3. **Required diagnostics in `a2-v1.json`:** counted (a) weeks whose accepted
   board was not the week's first session, (b) weeks with no complete board,
   (c) weeks skipped by the spacing test.
4. **Feasibility projection (append before running):** before the historical
   pass executes, the implementing agent MUST append to this amendment the
   computed projected accepted-cohort count per lane/arm/horizon over the
   cache span (2025-04-07 to 2026-06-30), and pre-declare which long-horizon
   variants are structurally expected to report INSUFFICIENT_SAMPLE against
   the registered `MIN_ADVERSE_BOTTOM_BUCKET=10`. Discovering starvation
   after the run is not acceptable; declaring it before is.

## Pre-result attestation

As of this recording: `reports/a2/` does not exist; the ledger holds zero
A2-v1 retrospective results; and — stated in the stronger observation form
the adversarial review required — no A2 outcome return, bucket spread, arm
comparison, or summary statistic has been observed by any operator or agent.
(The audit path did construct outcome rows in memory; only IV/check counts
were ever printed.) These definitions are frozen now and cannot be re-pinned
when corrected data later arrives.

## Policy call — IV BLOCK retained (operational no-go, not an amendment)

The historical pass stays blocked pending corrected provenance-bearing
chain/Greeks data. Required corrections to how this is described anywhere it
is quoted:
1. The supportable claim is: a completed merged 15-symbol audit does not
   exist (AMZN never ran; `_merge_audits` never executed); exact
   selected-contract evidence exists for CRWV only (21 rows `iv = 0`, two
   rows `iv > 5`); 13 further per-symbol BLOCK prints exist without preserved
   contract identities. "13 of 14 symbols blocked on invalid provider IV" is
   NOT supportable.
2. The flagged rows are deep-ITM / zero-DTE monitoring snapshots outside
   every entry delta band; IV does not enter any A2 return. The block is
   retained on AUDIT-COMPLETENESS grounds, not demonstrated price corruption.
3. Unblock criterion: a completed, merged 15-symbol audit (including AMZN)
   over provenance-bearing chain/Greeks data with preserved contract
   identities, in which check 10 passes or its failures are shown to be
   outside all entry selections.
4. "Never run — data blocked" is a legitimate terminal state for the
   historical pass, which is one-shot and untimed; no registered clock runs
   while blocked (forward dates are unpinned).
5. Separate follow-up (audit-scope gap): check 10 audits `selected|eligible`
   contracts only; the chain rows feeding the ranking's `atm_iv` /
   `iv_minus_rv` are not IV-audited. Do not treat check 10 as covering
   ranking-input IV.

## Implementation notes for the repairing agent (Codex)

- `breach_hold_21_dte` at `a2_panel.py:374-379` currently duplicates
  `close_21_dte` (verified); implement Definition 1 as pinned above.
- `non_overlapping_inference_rows` at `a2_battery.py:350-371` is greedy-daily
  (verified); implement Definition 2 as pinned above.
- Re-run the scoped A2 suite + pyright + the final-branch-review checklist
  after repair; the historical run remains prohibited until the IV unblock
  criterion is met AND the Definition-2 feasibility projection is appended.

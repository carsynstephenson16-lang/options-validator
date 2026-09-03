# H7 Schwab activation specification

Status: UNSIGNED — the owner must review this exact revision and supply its SHA-256 at activation time.

This specification governs only the `h7-forward-schwab-v1` first-window registration door. It does not grant activation, registration, deployment, trading, or ledger-write authority.

## Owner authorization inputs

The Schwab door requires all owner-typed fields in its registration contract, including `SCHWAB_MIN_LOSSES_FOR_VERDICT` and `SCHWAB_STARVATION_RISK_PREACCEPTANCE`. The starvation pre-acceptance is retained verbatim in the event and must include one exact `occupancy_constrained_expected_entries=<value>` token.

schwab_min_losses_for_verdict=7

## Cohort and evidence

The owner supplies the included and excluded names at invocation. Their sets must exactly equal the read-only seq-0 H7 manifest: the nine inherited included names and the six inherited exclusions. Each excluded name has a fresh, nonblank owner reason. The only permitted trim rule is `inherited_seq0_cohort_2026-07-20`.

The qualifying data-gate receipt remains full 15-name evidence; each included name must be per-symbol `GO`. A `NO_GO` on an excluded name does not narrow the evidence scope.

## Quote-age obligation and ordering

Quote age is a post-registration arming obligation, not a registration gate. The ruling-3 60-minute dispersion reference is display-only and does not authorize an absolute-age blocker.

This specification is reviewed before use. After code review and merge, the owner regenerates feasibility, source-health, and data-gate receipts against the resulting configuration, reviews this exact spec revision, supplies its SHA-256 and the required confirmation, and only then may invoke the owner-gated CLI.

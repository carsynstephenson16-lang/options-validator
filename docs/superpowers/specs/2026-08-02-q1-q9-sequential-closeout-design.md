# Q1-Q9 Sequential Closeout Design

**Status:** OWNER-APPROVED 2026-08-02

## Goal

Close or freshly audit roadmap tasks Q1 through Q9 without altering existing
paper-book rows, historical receipts, cache bytes, prior results, or live-order
boundaries. Stop at Q10 because schema-v2 integration remains separately
owner-gated.

## Execution boundary

Work occurs on an isolated branch from the latest local `sfix` commit. Each
queue item receives a fresh verification gate and its own commit before the
next item starts. Unexpected overlap with unrelated work stops the affected
task; it is never absorbed or reverted.

Q1 is documentation-only. Q3 through Q9 are audit-first: production code may
change only if a fresh regression reproduces, after which systematic debugging
and failing-first tests are mandatory. No provider call, cache mutation, live
order, retrospective rescore, book edit, or prior-result reinterpretation is
authorized.

## Q2 H6 hard-kill v2

The owner authorized a prospective, verdict-bearing H6 amendment effective for
entries on or after 2026-08-03. It is registered through one chained H6
`trial_intent`, not the descriptive-only facts stream.

The exact rule is:

- Pre-effective entries retain the registered v1 exit-month/full-cap-loss rule.
- Post-effective entries use H6-only calendar entry-month cohorts.
- A v2 cohort is a full loss only when at least one position was deployed,
  every position opened in that month is closed, and aggregate exit proceeds
  are exactly zero relative to the positive deployed premium.
- An open position makes its cohort unevaluable. A zero-deployment month or any
  non-full-loss month breaks the consecutive streak.
- Three consecutive full-loss calendar entry months trigger H6 rejection.
- V1 and v2 rows never contribute to one another's hard-kill calculation.
- The existing eight-completed-position bootstrap, entry and exit rules, cost
  model, sizing, H6 CSV schema, and `H6Score` interface do not change.
- H8 remains separate. No combined H6/H8 emergency stop is authorized.

Internal dispatch uses the position `entry_date`, so the existing `H6-0001`
row remains v1 without a schema migration. Historical receipt-v1 documents
remain supported for pre-effective decisions. Receipt-v2 applies to decisions
on or after the effective date and binds both the original H6 registration and
the new chained amendment record.

## Failure handling and proof

The chained append is preceded by duplicate and ledger-integrity checks and is
performed exactly once through `research.experiments.log_trial_intent`. Any
duplicate, ledger failure, book-hash change, receipt incompatibility, or
registered-result change stops Q2.

Q2 follows red-green-refactor for the date boundary, shifted exit months,
partial deployment, positive recovery, open cohorts, zero-deployment gaps,
mixed-version isolation, receipt compatibility, receipt-v2 provenance, and H8
non-interference. Completion also requires the full suite, Ruff, Pyright, both
ledger verifiers, book/receipt verification, unchanged cost-model identity, a
clean diff review, and advisory CodeRabbit review when available.

Q5-Q9 remain read-only audits of their canonical facts, manifest, provider
disablement, cap receipt, and offline-readiness receipts. Q9 must continue to
report EOD readiness as passing while real options flow remains DATA-GATED.

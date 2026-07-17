# QM dashboard remediation addendum (2026-07-17)

**Status: documentation and presentation hardening only.** This addendum does
not register a hypothesis, reopen H7, promote H9, change a model input, or
authorize a data pull, decision, or order.

## Finding and decision

The dashboard kept the mechanical and QM candidate lists isolated in code but
rendered the QM list first in the same hero treatment. That presentation gave
the frozen QM study primary visual weight even though its sidecar records
`DESCRIPTIVE_ONLY`, only 11 correlated Breakout fires, and no historical
option-P&L validation. The dashboard must lead with the mechanical shortlist;
the QM list is a secondary descriptive comparison and is never an action
ranking.

The prior Pyright result did not cover `options_researcher/`, including the
dashboard and QM modules changed by this work. The project type-check scope
now includes those two modules explicitly. A whole-package dry run currently
surfaces 163 pre-existing errors in unrelated modules; clearing that debt is a
separate package-wide effort and must not be hidden by claiming a project-wide
Pyright pass.

## Four separately gated merge tracks

The current branch contains work from otherwise independent arcs. Treat the
following as separate merge units; a passing check in one is not evidence for
another.

| Track | Scope | Gate to merge | Explicit non-authority |
|---|---|---|---|
| 1 | H7 forward-paper / Stage 8 | Its existing owner, source-health, exact-session, and registration gates | No historical H7 diagnostic, event, or activation |
| 2 | H9 conditional historical study | Owner-typed registration, hash, ledger fact, and its one-run gate | No validation or rejection of H7/H6/H8 |
| 3 | Mechanical attractiveness dashboard | Existing policy/snapshot/liquidity tests plus rendered-artifact review | No new strategy rule or trade instruction |
| 4 | QM dashboard comparison | This addendum's UI, type, provenance, and cross-book checks | No edge claim, option-P&L claim, or ranking authority |

Track 4 is deliberately a fourth track, not a hidden dependency of H7 or H9.
It may be cherry-picked and reviewed after its prerequisite QM dashboard
commit, but it must not be merged merely because the wider H9/Stage-8 branch
is ready.

## Track-4 remediation plan and acceptance checks

1. Put `ORIGINAL MECHANICAL TOP 3` before the QM section in rendered DOM
   order. Render QM in a visually subordinate comparison panel carrying the
   exact label `DESCRIPTIVE ONLY — NOT A TRADE RANKING`.
2. Preserve fail-closed behavior: a stale or incomplete symbol blocks all
   three QM slots, while the mechanical list remains visible. Keep the
   withheld underlying-breakeven/option-win-rate behavior for both long-call
   and non-long-call lanes.
3. Add the two changed `options_researcher` modules to the Pyright include
   set and run type checking against them, not only unrelated project
   directories. Open a separate package-wide typing cleanup before broadening
   the include to the entire package.
4. Preserve append-only provenance. The H7 receipt remains frozen; its
   staleness and the shared OHLCV cache coupling are recorded in `facts.log`.
   The hardcoded `quant want` path and pinned commit are likewise recorded as
   a cross-book dependency, not silently treated as an internal source.
5. Before merging Track 4, run the focused dashboard/QM tests, Pyright,
   Ruff, regenerate `.tmp/dashboard/attractiveness.html`, and inspect the
   artifact for mechanical-first order, the descriptive label, and all three
   fail-closed QM slots under a stale-context fixture.

## Merge hygiene

This addendum is a remediation plan, not a claim that the complete current
branch is safe to merge. The next integration owner should create one review
range per table row from the appropriate base commit, document prerequisite
commits, and reject a range that mixes Stage-8 authorization work with the
QM display-only track. The two append-only facts above must remain in the
review range for Track 4.

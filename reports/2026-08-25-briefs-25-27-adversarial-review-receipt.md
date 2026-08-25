# Adversarial review receipt — Codex briefs 25/26/27 (rev 1)

**Date:** 2026-08-25
**Reviewer:** independent Opus adversarial-review agent (spawned by the
orchestrating Fable session; instructed to attack, verify every citation
against the working tree, and re-run live-system observations).
**Subject:** rev 1 of
`docs/superpowers/plans/2026-08-25-25-market-context-signal-lane-codex-brief.md`,
`…-26-board-declutter-top5-codex-brief.md`,
`…-27-pick-tracker-scoreboard-codex-brief.md`.

## Verdicts (rev 1)

| Brief | Verdict |
|---|---|
| 25 (market-context lane) | **FAIL** |
| 26 (board declutter / top-5) | **FAIL** |
| 27 (pick tracker) | **FAIL** |

## Blockers found (all confirmed by the orchestrating session)

1. Brief 25's load-bearing premise was false under a fabricated live-system
   attestation: the research-refresh LaunchAgent is ENABLED (13 runs, last
   exit 3 `UPSTREAM_BLOCKED` — upstream ritual status not OK), not
   "intentionally disabled." Independently re-verified by the orchestrating
   session via `launchctl print` and producer logs before rev 2.
2. All three briefs cited a dirty-tree SHA as "Repo-verified" while
   depending on then-uncommitted code (`OPS_CHECKOUT_FALLBACK`); line
   citations resolved against HEAD, not the tree Codex would get.
3. Brief 27's entry marks were non-causal (decision quote == fill quote)
   and inverted registered seq 21 (`D_PLUS_1_CLOSE`) while citing it.
4. Brief 27's scoreboard statistics (no overlap rule, no CI, no
   multiplicity control, no concentration disclosure) were weaker than the
   registered A2-v1 battery measuring the same board.
5. Brief 27's 7-arm forward horse race is the practice the 2026-07-24
   feasibility-gate doc explicitly bans at `:71-73`; the brief cited that
   doc three times without quoting the adverse clause.
6. Brief 27 created a parallel, unregistered outcome measurement running
   concurrently on A2-v1's open verdict-bearing forward window.

Plus 23 MAJOR findings (direction-blind context term discarding a
registered veto; non-deterministic score tail; vacuous flag-ON tests;
hardcoded owner-facing money figures with a wrong citation; unmanaged
25/26 collisions; wrong ledger-seq citation; six-not-four slot literals;
self-contradictory byte-reduction target; dominance axes missing on 3 of 5
lanes; falsifiable summary text; hidable liquidity-RED cards; markdown
parsing of a file the same brief reformats; mtime as freshness oracle;
unspecified shortlist variant incl. WATCH cards; single 42-session horizon
biasing buy lanes; impossible in-process-data premise; unhandled ops sync;
`as_of` ambiguity; misfiled config provenance; disclaimer falsified by
brief 27; no enable path for the flag; spend increase disclosed only in a
PR description) and 11 MINOR citation/line errors. Full finding text lives
in the session transcript; every finding was either applied in rev 2 or
explicitly surfaced as an owner decision.

## Disposition

Rev 2 of all three briefs written 2026-08-25 by the orchestrating session,
applying every blocker and major finding (or converting it to a named owner
decision), with a binding landing order 26 → 25 → 27 and provenance
re-anchored on commit `720a20e`.

## Round 2 (same reviewer, same day, on rev 2)

Closure table: 30 of 40 rev-1 findings CLOSED, 6 PARTIALLY CLOSED, plus 12
new findings (N-1..N-12). Round-2 verdicts:

| Brief | Round-2 verdict | Disqualifiers |
|---|---|---|
| 25 | **PASS WITH FIXES** (N-1 nonexistent SIDEWAYS trend state; N-2 move-list omission; N-10 stale carried-over citations; N-12 disclaimer future-truth) | — |
| 26 | **FAIL** | N-4: the rev-2 "never hide any RED card" rule covers 77% of live cards (portfolio/fits_cap REDs dominate) and nullifies the collapse, with a threshold-free acceptance metric unable to detect it; plus N-5 (cc `upside` axis missing, pmcc degenerate), N-7 (sidecar contract gaps), N-11 |
| 27 | **FAIL** | N-8 (picks artifact not writable where specified — selection lives inside `render()`); N-3 (CSP/CC/PMCC mark points invented under a Repo-verified label); N-9 (primary contrast can register empty — flip/registration ordering unspecified); N-6 (study is not two months; no entry-count projection) |

Notable round-2 confirmation: the round-1 live-system correction stood —
the research producer is enabled and failing UPSTREAM_BLOCKED, independently
re-verified by both the reviewer and the orchestrating session.

Rev 3 of all three briefs written 2026-08-25, applying N-1..N-12 (brief 25:
4 fixes; brief 26: safety-badge scoping to `liquidity`-RED only + measured
50% acceptance floor + cc/pmcc axis repair + sidecar atomic-set publish +
renames; brief 27: `render()` selection-sink design, seq-19 mark-schedule
honesty with owner-typed CSP/CC/PMCC points, flip-before-registration
ordering with later-of admissibility, retitle + mandatory entry-count
projection with sparsity pre-acceptance). Briefs 26 and 27 require a
round-3 re-review before hand-off; brief 25 requires a confirmation pass.

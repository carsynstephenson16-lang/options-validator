# Adversarial review receipt — Codex briefs 25/26/27 (three rounds, 2026-08-25)

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
projection with sparsity pre-acceptance).

## Round 3 (same reviewer, same day, on rev 3 @9708a90)

All twelve N-findings verified CLOSED. Six new findings in the changed
passages: NEW-1 (MAJOR — 50% acceptance floor near-certainly unreachable:
measured 14/18 panels contain a liquidity-RED card, 82/222 blocks
liquidity-RED), NEW-2 (MAJOR — picks-artifact test pinned the
watch-inclusive hero list while the scored arm excludes WATCH), NEW-3
(MINOR — stale rev-2 mark-schedule prose), NEW-4 (MAJOR — capture-density
figure wrong: verified sessions are 2 in repo / 4 receipt dirs in ops, not
"~6"; cancellation rate unprojected; ops-health only a "should"), NEW-5
(MINOR — WP-E test names encoded the replaced blanket-RED rule), NEW-6
(MINOR — staleness reference date unpinned).

**Round-3 verdicts: brief 25 PASS (ready for hand-off); brief 26 PASS WITH
FIXES (NEW-1, NEW-5, NEW-6); brief 27 PASS WITH FIXES (NEW-2, NEW-3,
NEW-4).**

Rev 4 of briefs 26 and 27 written 2026-08-25 applying all six. Brief 26
rev 4 additionally narrows the panel-open rule to DATA_BLOCKED/stale only
(a liquidity-RED card no longer forces its panel open, only its
never-dominance-hidden guarantee remains) — an orchestrating-session design
decision responding to NEW-1's measurement, NOT itself re-reviewed; flagged
in the brief's Status line for the implementing reviewer. Acceptance
switched from a percentage floor to dry-run rule-faithfulness with a <30%
STOP-and-report-to-owner clause.

## Round 4 (2026-08-25 pm — parameter audit, fresh Opus agent)

Owner approved the packet proposals in-session ("42 / 21 / pre-accept is
good and annotate all 5 picks") and directed "audit your proposals then go
with what's best." Focused audit of the four values, with measurements:

| Value | Verdict | Disposition |
|---|---|---|
| 42-session entry window | DEFECTIVE (keying, not length) — measured on the frozen cache 2026-05-01→2026-07-27: winning expiry+strike changes ~90% of consecutive session pairs, median candidate_id run 1 session → candidate_id-keyed "once-only" events would flood with re-struck duplicates | Entry events re-keyed to (arm, symbol, lane) SLOTS with RESTRIKE annotations (brief 27 WP-B.2); window 42 retained |
| 21-session income-lane mark | DEFECTIVE — units conflation (seq 19's "close at 21 DTE" is remaining tenor, not elapsed sessions; seq-30 IV-units pattern) AND unreachable for the modal ~11-DTE pick; income lanes may rarely enter the shortlist at all (badge census: sell cards can't reach GREEN-fraction 1.0 while FOMC/VRP/earnings sit AMBER/UNKNOWN) | Replaced with 5/10 sessions + 21 only for DTE>30 entries; MARK_AFTER_EXPIRY handling incl. registered tactical marks; per-lane unreachable-mark counts; zero-entry lanes report "no data" (brief 27 WP-C.3) |
| Pre-accept clause | SOUND WITH CAVEAT — projection duty survives, but (c) could be dropped and the owner ruled ex ante, before numbers exist | Clause hardened: all three numbers quoted verbatim; return-to-owner trigger if cancellations >50% or entries <1/arm/week (brief 27 WP-F.4) |
| 5-pick research annotations | SOUND — count is derived, nothing pins 3; verifier derives required symbols | Recorded as ruled D-2 with the fail-closed budget line (brief 25 WP-E.5) |

All amendments applied same-day; owner-typed registration values remain
owner-typed (the approvals are spoken selections of proposals, not typed
registrations).

## Wave 0 focused independent review — Brief 26 rev 5

**Date:** 2026-08-25

**Reviewer:** one independent Codex GPT-5.6 high-reasoning review agent,
read-only and scoped to Brief 26's contradictions, atomic publication,
acceptance language, ops/copy/hash protocol, and worker authority boundaries.

**Review base:** `origin/main@77b1a46`; initial reviewed head `9c46f93`;
final reviewed head `99b7bba`.

The first pass correctly withheld PASS for four blockers: generation identity,
containment, timestamp ordering, locking, and fsync were underspecified; the
hash chain and copy provenance were inconsistent; builder CLI and failure
semantics were not executable against current code; and the dashboard did not
carry `_input_root_cwd()`'s resolved source root into the copy step. After
those corrections, the same reviewer found one remaining failure-receipt
causality issue. Rev 5 then made the durable current pointer the sole success
receipt and introduced a lock-ordered, UTC-completed `last-failure` channel
that copies independently even when the ops generation is unchanged.

**Final written verdict on `99b7bba`: PASS.** The reviewer confirmed all four
original findings closed, coherent failure causality, explicit crash,
concurrency, integrity, copy, and compatibility tests, a documentation-only
branch, clean `git diff --check`, and unchanged hashes for the concurrent
untracked drafts.

This PASS authorizes the owner-directed Brief 26 hand-off only if the Wave 0
documentation PR lands. The PR remains draft; the reviewer did not authorize
merge, deployment, ops mutation, ledger mutation, authority changes, or making
any PR ready.

## Post-submission Git audit — PR #80

**Date:** 2026-08-25

After the draft PR was pushed, a fresh Git/GitHub audit verified its ancestry,
exact patch-id equivalence for source commits `7908919` and `839ddb3`, changed
paths, CI, review/comment state, and protected untracked-draft hashes. Two
documentation gaps were corrected before the audit-fix commit:

1. Brief 26 named nonexistent `tests/test_regime_report.py`; the existing
   regime-report coverage is in `tests/test_regime.py`, now cited correctly.
2. The central number registry was not routed from the canonical
   `codex-brief-writing` skill, and the draft-only worker rule was not present
   in `AGENTS.md`. Both entry points now carry the reservation/collision and
   draft-PR authority rules.

Post-fix validation used unittest discovery (the repository's required test
shape): regime/report 23/23 PASS, experiments-dashboard 4/4 PASS, and
research-display-refresh 7/7 PASS; `git diff --check` was clean.

One separate implementation gap remains outside this documentation PR:
`tools/anti-stranding/repo-reconcile` still creates non-`wip/*` PRs ready by
default, although its merge loop correctly excludes drafts. That script is
already concurrently modified in the dedicated
`codex/repo-reconcile-publish` worktree/branch. PR #80 does not overlap that
owned worktree or deploy a reconciler change; the default-draft code change
must be reconciled in that lane before its next deployment.

## Full-PR Wave 1 readiness audit — PR #80

**Date:** 2026-08-25

CodeRabbit's review skill was used, but its CLI was not installed; no
CodeRabbit verdict is claimed. The fallback audit combined Git/GitHub state,
current source inspection, executable command/path checks, and repeated
read-only review by the same independent Codex reviewer.

The first full-PR pass found two blockers and seven warnings outside Brief
26's already-passed atomic protocol: Brief 27 delegated ops deployment to its
worker and lacked enough CC/PMCC identity to compute its promised P&L; Brief
25 omitted the real MIXED trend state, contradicted its own full-pool ranking,
hardcoded a time-sensitive failure cause, and delegated a flag flip; Brief 27
pooled incomparable raw dollars, lacked a cohort sufficiency rule, and still
required later landing-order review; the Wave 0 transplant constraint was
stale. All were corrected.

Follow-up review then caught and closed four executable-contract defects:
repo-wide Ruff formatting failed on the 281-file baseline and was narrowed to
new files only; research-refresh evidence could not prove failure states;
put assignment-capital provenance was not present in the snapshot; and the
CI contract overstated independence. The briefs now use scoped formatting,
strike-derived put provenance, lane-normalized incremental-option returns,
and an exploratory two-week moving-block CI only after eight chronological
cohorts. A final review caught one publication-cycle circularity in Brief 25;
the freshness chip now snapshots board and context from one input root and
reports only evidence-derived EXACT/STALE/UNAVAILABLE/INTEGRITY_FAILED states,
without consulting PENDING/FINAL publication state, guard state, or logs.

**Final written reviewer verdict: PASS.** No Critical or Warning findings
remain. Brief 26 rev 6 is authorized for hand-off only after the owner lands
this still-draft documentation PR. Brief 25 rev 4 waits for Brief 26's
implementation to land. Brief 27 rev 5 remains DRAFT until Briefs 26 and 25
land, it is rebased/reverified, and it receives its own fresh written PASS.
The reviewer authorized no readiness transition, merge, deployment, ops or
ledger mutation, registration, flag enablement, or authority change.

Fresh pre-commit validation after the final receipt/status edits: regime/report
23/23 PASS, experiments-dashboard 4/4 PASS, research-display-refresh 7/7 PASS,
Ruff PASS, Pyright 0 errors, `git diff --check` PASS, no conflict markers, and
all three protected untracked-draft SHA-256 values unchanged. The repo-wide
Ruff formatter baseline remains noncompliant (281 pre-existing files); the
implementation briefs therefore check formatting only on their genuinely new
Python modules and do not authorize a mass rewrite.

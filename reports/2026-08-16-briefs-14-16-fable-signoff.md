# Briefs 14–16 — round-3 independent review + Fable sign-off decision (2026-08-16)

**Reviewer:** independent Opus-model adversarial pass (round 3), 2026-08-16,
read-only, commissioned per the owner directive of 2026-08-16
(`reports/2026-08-16-owner-directives.md` Directive 2).
**Fable decision: SIGN-OFF WITHHELD for hand-off.** Round 3 verdict: **FAIL**
— four blockers (BL-1..BL-4), eight non-blocking fixes (FX-1..FX-8). The
round-1/2 receipt's paperwork claims all verified true (hash chain seq 0→27
recomputed clean; ledger seq 26/27 text verbatim from the reviewed drafts;
owner-rulings source on disk; every round-2 blocker fix physically present).
What rounds 1–2 missed is feasibility of the registered design against its
own pinned price source.

## Blockers and their status

- **BL-1 (immutable; needs further pre-result amendment + owner input).**
  B1's percentile thresholds need a 252-session trailing IV history. The
  pinned source (Schwab 15:45 preclose captures) has ~1 session of history;
  the ThetaData cache ended 2026-07-27; splicing the two IV series is
  fabrication per `options_researcher/schwab_chain_view.py:334-337`. Seq 26
  wrote a provider-parity guard for V1 only — B1 has none. Consequence: B1
  is UNAVAILABLE-by-construction for roughly the first half of a
  twelve-month verdict-bearing window, and no feasibility computation for
  B1 was ever run (2026-07-24 gate). Disposition options for the owner:
  (a) pre-accept the ramp-up starvation explicitly (quote the number of
  UNAVAILABLE months), (b) amend B1's lookback/min-obs (pre-result; but any
  new number needs provenance), or (c) delay the window open. Until then
  B1 rows must render fail-visible UNAVAILABLE — never a spliced value.
- **BL-2 (immutable; needs owner decision).** The preclose capture universe
  (`watch_universe()`) is 15 names; the registered 18-name board includes
  AMAT/CLSK/NBIS which are deliberately excluded from capture
  (`config.py:650-654`). Either the owner authorizes a capture-universe
  expansion (a provider-scope change — owner-gated), or a further amendment
  records the honest 15-name executable board for options-derived badges.
- **BL-3 (applied this revision).** Brief 14's WP-C now binds to ledger seq
  26 clause 5a instead of the superseded 2026-07-22 §V1, and the V1 refusal
  language/tests now match the gated rule (compute line-1 when the
  amendment is present; refuse ranking/blends always).
- **BL-4 (applied this revision).** `PROJECT_STATE.md` and the auth-diagnosis
  header no longer claim both lanes verified 15/15 over 08-12→08-14; the
  intraday lane did, the preclose lane's first clean run was 08-14.

## Non-blocking fixes

FX-2 (earnings_tag source pinned to `h7_earnings`, frozen window) and FX-3
(universe hash + freeze test in brief 14) are applied this revision. FX-5/FX-8
were stale-branch artifacts (resolved on `origin/main` via PR #57). Remaining
open, tracked for the follow-up batch: FX-1 (seq-26 backstop wording moves
the end date later — disclose or amend), FX-4 (`.cache/underlying` closes end
2026-08-04; refresh before 08-17 or A1 renders fail-visible), FX-6 (V1's
statistic is a constant until provider parity — disclose in output), FX-7
(two provenance-label tightenings, partially applied via BL-3's rewrite).

## Sign-off statement

Briefs 15 and 16 carry no blocker of their own but ship as a batch with
brief 14; the batch does not go to Codex until BL-1 and BL-2 have a recorded
disposition (owner input required for both). Ledger seq 26/27 stand as
recorded — they are pre-result amendments and their defects are correctable
by a further pre-result amendment, which is the honest append-only path.
This document is the Fable sign-off record required by the owner-delegated
standing 2026-07-25 for the round-3 review cycle: sign-off is **withheld**,
with the two text-fixable blockers already fixed and the two structural ones
routed to the owner.

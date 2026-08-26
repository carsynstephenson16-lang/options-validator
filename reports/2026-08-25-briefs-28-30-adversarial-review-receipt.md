# Adversarial review receipt — Codex briefs 28 (event awareness) and 30 (midday chain refresh)

**Date:** 2026-08-25 (evening)
**Reviewer:** the same independent Opus adversarial-review agent used for
briefs 25–27 (receipt `reports/2026-08-25-briefs-25-27-adversarial-review-receipt.md`),
with a dedicated capture-lane scout pass feeding brief 30's factual basis.
**Note:** brief 30 was numbered 29 at round 1; renumbered same-day because
another session took slot 29 (Schwab inventory binding).

## Round 1 (on rev 1)

| Brief | Verdict | Headline findings |
|---|---|---|
| 28 | PASS WITH FIXES (1–9) | allowlist-vs-denylist confusion ("company IR" cannot be host-allowlisted); LLM-seeded calendar facts wearing an unearned Official-source label (Warsh entry singled out); WP-D implied move had no spot source; `sections_json` byte-stability unprotected; landing order delegated as a repo-state branch |
| 30 | FAIL (10–18) | BLOCKER: WP-C.3 let Codex choose a render route, one branch of which re-runs selection at 13:05 and collides with brief 27's fail-closed recorder; no landing order; freshness guard in prose but not schema; output-equality proof insufficient for touching the live pre-close core (staged deploy demanded); 3-of-18 names permanently unrefreshable, undisclosed |

Scout addendum folded in after round 1: `tools/chain_consistency_audit.py`
(brief 22, on origin/main) is a FOURTH consumer reading `.cache/schwab_chains`
directly with date-keyed adjacency — a same-directory midday capture would
corrupt it into false DELTA/SPREAD flags; and PR #76 (merged @31215c5) moved
`reports/schwab_chains` into DATA_TIER_PATHS.

## Round 2 (on rev 2, @3659bd4)

F1–F18 closure: 17 CLOSED, F4 NOT CLOSED. New findings:
- **NEW-1 (BLOCKER, brief 28):** rev 2 named "parity spot" as WP-D's spot
  source — the exact source the boundary module forbids
  (`schwab_chain_view.load_preclose_spot` docstring: "never a parity
  fallback"; requires `spot_source == "stock_snapshot"`). Fixed in rev 3:
  `load_preclose_spot` named, intraday-lane dependency disclosed.
- **NEW-2 (BLOCKER, brief 30):** rev 2's mandated client-side fetch breaks
  `render()`'s self-contained contract and fails silently under `file://`.
  The "inject at next board build" alternative was rejected on timing:
  on a normal day the newest midday JSON at the 07:10 build carries the
  SAME session date as that build's pre-close chain — not strictly newer
  — so it displays only on days the prior pre-close capture FAILED
  (round-3 NEW-7 corrected this receipt's earlier "always older / never
  displays" phrasing, which was wrong on both counts). Fixed in rev 3:
  standalone self-contained `midday_refresh.html` linked once from the
  Experiments shelf.
- **NEW-3 (MAJOR, both):** unconditional CSS/script emission falsified the
  rollback byte-identity claims. Fixed: conditional chip-CSS emission
  (28); board delta = exactly one shelf link, pinned-content test (30).
- **NEW-4/NEW-5 (MINOR):** `source_quote` field for in-repo auditability of
  "fetched" claims (28); midday spot source named as the midday
  intraday-capture receipt (30).

Round-2 verdicts: **28 PASS WITH FIXES; 30 FAIL (scoped to WP-C.3 route).**

## Round 3 (on rev 3, @5d76498)

NEW-1..NEW-5 all CLOSED (NEW-2 as to the rejected routes). New findings:
- **NEW-6 (BLOCKER, brief 30):** rev 3's freshness guard compared the
  midday JSON's `session` against `board_session_at_write` — two fields
  written by the same runner in the same instant, a tautology that can
  never detect staleness; a leftover quote-line page would present
  yesterday's 13:00 prices as fresh on exactly the failure-days that are
  currently common. Fixed in rev 4: comparands are two named,
  independently-sourced values (newest `verified_midday_sessions()` vs
  newest pre-close `verified_sessions()`), evaluated at each writer's
  runtime, plus a 07:10 janitor sweep that rewrites a superseded page to
  "outdated"; `board_session_at_write` demoted to provenance.
- **NEW-7 (MINOR):** the orchestrator's timing argument had the right
  conclusion, wrong reasons (equal-not-older; "never displays" is false
  on failed-capture days). Corrected in the brief and this receipt.
- **NEW-8 (MINOR, brief 28):** persistent implied-move UNAVAILABLE is an
  intraday-lane health signal, not an event-layer bug — sentence added.

**Round-3 verdicts: brief 28 PASS (ready for hand-off in its landing
slot); brief 30 FAIL — third consecutive fail, all three on WP-C.3's
delivery mechanism; everything outside WP-C.3 signed off unchanged.**

## Round 4 (on rev 4, @cbf03c2; scope WP-C.3/WP-E.4 only)

NEW-6 confirmed CLOSED with a formal ordering argument (board ≤ B < A
whenever quote lines render — no pair compared wrongly, no window where
the quote-line page is older than the board). Six MINOR residuals, all
mechanical: A-empty branch unpinned; HTML write atomicity unspecified;
janitor vs module-executing baseline test; janitor skipped on
failed-build mornings (disclosure needed); comparand-B rationale
sentence; plus confirmation that the rev-4 two-writer design is cleaner
than the reviewer's own conditional-link suggestion ("adopt it as
written"). Receipt and brief-28 NEW-8 line confirmed faithful.

**Round-4 verdict: brief 30 PASS WITH FIXES — all six applied same-day
(rev 5 = final).** Final states: **brief 28 READY (round-3 PASS); brief
30 READY (round-4 PASS WITH FIXES, applied).**

## Disposition

Historical review-time landing order was 26 → 25 → 27 → 28 → 30. It is
superseded by the 2026-08-26 correction addendum below; the canonical order
is 26 → 25 → 28 → 27 → 30, with brief 30's WP-A additionally staged (WP-A
alone → one green 15:45 ops cycle → remainder). Process note for the record (reviewer's words): the
recurring failure in this work package was "guards specified in prose
that turn out to compare the wrong pair" — future briefs should state
guards as concrete comparisons between named, independently-sourced
values from the first draft.

## 2026-08-26 independent correction review

**Reviewer:** isolated GPT-5.6 high-reasoning reviewer, read-only.
**Reviewed commit:** `bc760a22d0c01e30e8d526158188158f06a32bc9`.
**Verified base:** post-Brief-25
`origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023`.
**Verdict:** **PASS**.

The reviewer independently checked all six correction criteria:

1. Active passages use exactly 26 → 25 → 28 → 27 → 30.
2. Briefs 28/30 are rebased and provenanced to the verified base, and the
   refreshed line citations support their claims.
3. Brief 28 explicitly covers landed Brief-25 context cards through each
   row's underlying `pick["card"]`, render-only and non-grading, with a named
   acceptance proof.
4. Brief 30 retains all five keyword-only capture-core parameters, including
   `receipt_kind` and `convention`, and the midday call supplies its distinct
   identity values.
5. Only gitignored `.cache/schwab_chains_midday` enters the irreplaceable-data
   guard; tracked `reports/schwab_chains_midday` relies on `DATA_TIER_PATHS`
   plus git/remote and carries no inventory floor.
6. No stale active passage, hidden authority expansion, or internal contract
   contradiction was introduced.

No blocking findings were reported.

## 2026-08-26 final-head correction review — superseding FAIL

**Reviewer:** isolated GPT-5.6 high-reasoning reviewer, read-only.
**Reviewed commit:** `1d09e8ae81b1ff371ebc9111f4d65ee3d6f43ac9`.
**Verified base:** post-Brief-25
`origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023`.
**Verdict:** **FAIL**. This verdict supersedes the PASS above for merge
eligibility until a later immutable commit receives a fresh independent PASS.

The reviewer found three blocking documentation defects:

1. Brief 25 still stated the obsolete active order 26 → 25 → 27.
2. Brief 30's durability language recorded an absent cache namespace but did
   not require guard semantics or a first-population floor, while the current
   guard skips recorded-absent entries.
3. Briefs 28/30 cited only the hashing function body and omitted the lines
   that include `options_researcher/` and `tools/` in its source paths.

Revisions 25 rev 5, 28 rev 6, and 30 rev 7 are the correction candidate for
these findings. A later section must record the immutable correction commit
and fresh independent verdict before this package may merge.

## 2026-08-26 corrected-pass review

**Reviewer:** isolated GPT-5.6 high-reasoning reviewer, read-only.
**Reviewed commit:** `572cabce863c8f62db4b084d98590bcb253883b1`.
**Verified base:** post-Brief-25
`origin/main@8a6920a2449094f4e5db5ad6ff00741f2d388023`.
**Verdict:** **PASS**.

The reviewer confirmed that the immutable correction commit closes all three
prior blockers: every active train passage uses 26 → 25 → 28 → 27 → 30;
the hashing citations cover both source-path membership and the hash function;
and Brief 30 fail-closes absent-to-populated cache state and requires a real,
positive first-population floor before scheduling or cleanup. The reviewer
also reconfirmed Brief 28's render-only, non-grading context-card chip coverage,
Brief 30's five keyword-only capture parameters and distinct midday identity,
and the boundary that only `.cache/schwab_chains_midday` enters the guard while
tracked `reports/schwab_chains_midday` relies on `DATA_TIER_PATHS` plus
git/remote. No authority expansion or blocking contradiction was found.

# Project replan — recorders first, then honest new plays

**Date:** 2026-07-22
**Status:** Owner-approved in session (Carsyn, 2026-07-22). Implementation is
Codex-executed; Claude orchestrates and reviews; owner types all frozen numbers.
**Scope gate check:** every Phase 1–2 item moves a live hypothesis (H7, H10a/b,
H5, RQ1) toward its declared verdict or corrects the record. Phase 3 items are
owner-gated new registrations, permitted under the 2026-07-16 operating-manual
amendment (extension work inside the existing book).

## 1. Why this replan

Owner directive (2026-07-22): re-evaluate the project, get every H level to
completion, update README/.cursorrules, change the attractiveness scanner,
promote 3 parking-lot ideas, and orient toward volatile-name opportunities
(reference case: CRWV ~$73 close on 07-17 → ~$84 intraday 07-22; sector-driven,
not market-wide — VIX 15–19).

Adversarially-reviewed finding (Opus review, this session): the project's real
defect is not missing strategies — it is that **two live-clocked experiments
are recording nothing**:

- H7's forward window (seq-0, hash-locked, 70 XNYS sessions, scores once
  2026-10-26) has zero real entries recorded; the daily ritual runs an
  alerts-only watcher plus a read-only preflight. The real-store **exit and
  scoring paths do not exist yet** (registered deadline fact
  `H7_C1_EXIT_AND_SCORING_DEADLINES`).
- H10a/H10b (registered 2026-07-19; backstops 2026-10-06 / 2027-01-06) have
  **no watcher, no paper book, no capture path**; `qm_watch.py` is alerts-only
  and absent from the ritual. Post-registration days not captured are lost —
  backfill is prohibited by the registrations themselves.
- H5's `entry_watch` is manual-only and not in the ritual, while 2 of 3 entry
  conditions are already met.
- RQ1 is registered with zero code.

"Complete all H levels" is therefore redefined honestly as: **every live
hypothesis has a working capture path and a known score date.** Verdict dates
themselves are session/sample-gated and cannot be accelerated: H7 2026-10-26;
H10a ≥7 losses or 2026-10-06; H10b ≥7 losses or 2027-01-06 (owner-disclosed
risk: may stay INSUFFICIENT_SAMPLE); H6/H8 sample-gated (8 completed positions
or hard-kill). H9 and Card 3 are adjudicated and spent forever.

## 2. Decisions recorded (owner answers, 2026-07-22 session)

1. **Recorders first.** Phase 1 precedes all new plays.
2. **H11 (drawdown-reversal bounce) will be drafted** for owner ratification.
   Its registration MUST cite as declared priors: Card 3 (6 trades, expectancy
   −$85.47/trade, CI90 [−$187.97, +$13.87], INSUFFICIENT_SAMPLE) and the QM
   parabolic-fade REJECTED reading (violent up-moves continued in-sample).
3. **Scanner changes by addition only.** Current GREEN recipe is frozen for
   RQ1's sake; new lenses ship as new display badges under a fresh RQ2
   registration. No RQ1 code is written until the freeze-vs-re-register choice
   in §5 N4 is resolved.
4. **Parking-lot promotions:** (a) drawdown-reversal → H11 (the owner's bounce
   play and the parked 2026-07-09 scanner idea are the same idea; H11 is its
   registered form), (b) market-implied probability readout, (c) scanner
   enrichment badges (bounce lens + repo-scale corner indicator) under RQ2.
   Qullamaggie is delivered via the H10a/b recorders (two of its three legs are
   already registered); its parabolic-short leg is NOT registered (contradicted
   in-sample; shorting out-of-mandate). The full-market "Primary Model
   Separation & Corner Indicator" study stays parked pending owner
   strengthening (see §7).
5. **Division of labor:** Codex writes all code from briefs; Claude
   orchestrates, reviews, and verifies; owner types every frozen number and
   ledger registration.

## 3. Phase 1 — turn the recorders on (critical path)

Ordering within Phase 1: R1 → R2 (exit/scoring before real capture), R3–R5
parallel. Each item is a separate Codex brief with acceptance criteria; all
work test-first, offline, unittest, against briefs derived from this spec.

- **R1 — H7 real-store exit + scoring paths.** Implement the reviewed exit
  path (per the amended §4a expiration-settlement spec, be0c43e) and the
  once-at-close scoring path for `ledger/h7_forward/`. Acceptance: append-only
  typed API only; hash chain verified by `h7_event_ledger verify`; independent
  adversarial review PASS recorded in the ledger before enablement; no
  interim-verdict output anywhere.
- **R2 — wire real H7 capture into the daily ritual.** Replace
  preflight-only operation with the one-door real-append path once R1's review
  passes. Acceptance: a ritual run on a FIRE day writes a real event; a NO_GO
  day writes the NO_GO receipt; ops worktree verified to run the registered
  code lineage.
- **R3 — H10a/H10b capture path.** Watcher (from the frozen H10 registration
  parameters), paper book (`data/positions/h10_positions.csv`), receipts, and
  ritual wiring. Acceptance: signals evaluated daily post-registration;
  no-signal days recorded as explicit no-signal observations; no backfill
  capability exists by construction.
- **R4 — H5 `entry_watch` into the ritual.** Alert-only, unchanged triggers.
  Acceptance: gate-clear produces a loud alert artifact; no auto-entry.
- **R5 — ritual capture receipt.** The 07:10 run emits a per-hypothesis
  status line (captured N / no-signal / REFUSED + reason) and fails loudly on
  refusal instead of no-op success. Acceptance: a silent no-op is impossible;
  tomorrow's (2026-07-23) rehearsal outcome is recorded either way.

## 4. Phase 2 — make the record tell the truth

- **T1 — README + .cursorrules + AGENTS.md refresh** (paired, no drift):
  Scope status rewritten to the verified state: live (H5/H6/H7/H8/H10a/H10b +
  RQ1), spent forever (H1/H2, H9, Card 3, QM study), verdict dates and gates
  as in §1, H7 9-name cohort with 6 permanently excluded names, recorder
  status. Vocabulary discipline unchanged.
- **T2 — branch consolidation.** Delete branches fully merged to main;
  list survivors with one-line dispositions for owner sign-off (known live
  candidates: `feature/repo-rag-phases-3-6`, `data-layer`,
  `parking/market-data-bundle-2026-07-20`, `feature/bs-attractiveness-descriptive`).
  No history rewrites; ops worktree untouched until after the 07-23 rehearsal.
- **T3 — parking-lot hygiene.** Commit the owner-pasted corner-indicator
  text verbatim (preservation), then reformat into a proper parked entry once
  the owner strengthens it (§7).

## 5. Phase 3 — new plays, honestly registered (owner-gated)

- **N1 — H11 drawdown-reversal registration draft.** Claude proposes the
  full parameter table (universe, drawdown trigger, reversal confirmation,
  IV-rank gate, liquidity gates both legs, structure, monthly cap, exits,
  earnings rule, loss-gated verdict spec, calendar backstop) with reasoning;
  owner types the frozen values into the ledger. Priors cited per §2.2.
  Dependency: **N1a — official earnings-date capture for CRWV and IREN**
  (sanctioned Trafilatura flow on IR/SEC primary sources +
  `tools/h7_refresh_earnings.py` owner-run promote) so CRWV can be admitted
  under fail-closed earnings gates; CRWV reports 2026-08-18 — the earnings
  rule must be typed before any CRWV-eligible window opens.
- **N2 — scanner enrichment badges (display-only) + RQ2 registration.**
  Badge A: bounce lens (violent drawdown + recent-RV context from existing
  `dist_52w_high`, `mom_1m`, `rv21`). Badge B: repo-scale corner indicator
  (term-structure steepness × VRP-proxy corner from existing `iv_minus_rv`
  plus a second ATM-IV tenor). Both are presentation-layer only, gate nothing,
  and enter ranking (if at all) only under the RQ2-registered definition.
  Thresholds owner-typed.
- **N3 — market-implied probability readout.** Display-only risk-neutral
  P(close beyond level by expiry) from cached chains, one-page spec first;
  never grades, ranks, or triggers.
- **N4 — RQ1 disposition.** Owner picks before any RQ1 code: (a) compute
  RQ1 against the frozen pre-badge GREEN-fraction (badges excluded from its
  input), or (b) supersede RQ1 in the ledger and re-register against the
  enriched recipe. Default recommendation: (a).

## 6. Horizon items (decisions, not work)

- **ThetaData extension (~Nov 2026):** coverage is confirmed through
  2026-11-30; H10b's 2027-01-06 backstop and any H7 positions open late in the
  window need marks into Jan 2027. Owner decision with dated receipt required
  before reliance.
- **NBIS admission:** deferred until N1a lands and owner re-confirms interest
  (needs watchlist amendment + earnings source; measured margins thin).

## 7. Owner inputs requested (the "make ideas stronger" list)

Delivered in-session as a plain-language list: corner-indicator scope and data
intent; H11 blanks (names, "violent" definition, reversal confirmation,
earnings rule, cap, exits); probability readout display choices; ET
shares-vs-LEAPS fork; diversification-shortlist goal; VIXEQ feed intent; NBIS
still-wanted. H11 and RQ2 cannot register until their blanks are owner-typed.

## 8. Risks and honesty notes

- No item in this plan promises earlier verdicts; it promises that verdicts
  land on recorded evidence.
- H11's own priors lean negative; registering it is a test, not a trade
  recommendation. "No edge after costs" remains a success outcome.
- Changing ranking recipes mid-study is the project's known contamination
  hazard; §5.N2/N4 exist to prevent it.
- The validator never places live orders; nothing in this plan changes that
  boundary.

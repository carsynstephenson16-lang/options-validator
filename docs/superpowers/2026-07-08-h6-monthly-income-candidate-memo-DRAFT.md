# H6 candidate memo (DRAFT) — monthly income WITHOUT capping the LEAPS — 2026-07-08

Status: **DRAFT — nothing here is registered, frozen, or runnable.** This memo
exists because the owner (a) decided not to sell covered calls against held
LEAPS (upside-cap aversion) and (b) asked for a "new monthly profit trade
strategy" on an expanded name list. Per ledger discipline this is a NEW
hypothesis (H6), not a tweak to H5; H5's forward window continues unchanged
(its CC/PMCC lanes simply go unused — declining to act on a lane is an owner
choice, not a design change).

## 1. What this repo already knows about "monthly profit trades"

These are ledger facts, not opinions:

- **H1 ($2-wide) and H2 ($5-wide) monthly put credit spreads: registered,
  honest in-sample FAILs** after realistic costs (mid-or-worse fills +
  slippage + commissions + half-spread on both legs). Every width in the
  sweep had bootstrap CI90 below zero; wider was less bad, never good.
- **Single-name variants also failed** (the "$2 grid mirage" finding).
- Translation: the canonical retail "monthly income" trade — short premium,
  defined risk, monthly cadence — was tested twice here and **rejected after
  costs**. Any H6 must state what is DIFFERENT about it, or it is a request
  to re-run a rejected idea until it accidentally passes.
- Structural honesty: monthly income from options = selling optionality.
  "Uncapped upside AND monthly income from the same capital" is a tension,
  not a strategy; every income structure gives up something (upside, or
  downside protection, or capital).

## 2. The requested name list (owner message 2026-07-08)

Raw: "crwv pltr hyln now ceg tem nvda and amzn".

**AMBIGUITY — owner must confirm:** is "hyln now" HYLN (Hyliion) *plus* NOW
(ServiceNow), or a typo? Reading as 8 names: CRWV, PLTR, HYLN, NOW, CEG,
TEM, NVDA, AMZN.

Per-name status (labels per claim discipline):

| Name | In frozen universe? | Chain data cached? | Notes |
|------|--------------------|--------------------|-------|
| CEG  | YES | YES | usable today |
| AMZN | YES | YES | usable today |
| PLTR | no  | legacy 9-symbol cache only (pre-pivot; 695 pre-listing gaps noted) | Repo-verified cache exists; scope re-add was REJECTED at the 2026-07 pivot |
| NVDA | no  | no | Assumption: deep, liquid options — but zero local data |
| CRWV | no  | no | IPO 2025-03 (Assumption): ~1yr of chain history max |
| TEM  | no  | no | IPO 2024-06 (Assumption): ~2yr max, thinner market |
| NOW  | no  | no | Assumption (high confidence): share price makes CSPs capital-infeasible at this account size |
| HYLN | no  | no | Assumption (high confidence): low-priced, thin options; unlikely to pass MIN_OPEN_INTEREST / MAX_SPREAD_PCT on any leg |

Constraints that bind before any design:

1. **Universe expansion is an owner scope decision** (the 4-name universe is
   an owner decision of 2026-07-03; a prior ticker expansion was rejected).
2. **Data**: 6 of 8 names have no usable cached chains. Fetching them hits
   the paid ThetaData subscription (live now, cancels ~2026-07-25 per
   checklist) — owner sign-off required on the spend and the added
   cache/audit work. Short-history names (CRWV, TEM) cannot support the
   2018/2020/2022 regime-spanning backtest design at all.
3. **Capital**: liquid capital on record is ~$7k against a nominal $20k
   sleeve (flagged drift, unresolved). One cash-secured put on a $150 stock
   ties up ~$15k. Most of this list is CSP-infeasible at this size; that
   pushes any premium-selling design toward spreads — which is what H1/H2
   already rejected.
4. **Concentration**: all 8 names are the same AI/semis/power factor the
   owner's portfolio already concentrates in (standing audit rule). Eight
   tickers here are one bet, not eight.

## 3. Candidate directions (menu for ONE choice — not a shopping list)

A. **Use H5's existing CSP lane** (0.20Δ monthly, already registered,
   evaluator live) on whichever names pass liquidity + capital gates.
   Cheapest honest option; no new hypothesis needed; capital-bound.
B. **Partial/far-OTM coverage variant** (e.g. short calls at ≤0.10Δ or on
   half the position): keeps MOST upside, small income. This is an H5
   amendment = logged new version (H5.1) with its own forward window.
C. **Put credit spreads, retried with a stated conditional edge** (e.g.
   only when the VRP proxy and IVR gates are green): must pre-declare why
   the conditioning defeats the H1/H2 failure mode, with rejection criteria
   frozen first. High burden of proof — two prior FAILs.
D. **Directional monthly structures (call debit spreads/diagonals into
   catalysts)**: highest risk, highest overfit surface, weakest prior
   support; would need the strictest pre-registration and a forward-only
   validation design (2023+ backtests are not credible for AI names).

Recommendation (advisory only): A on the names that survive a feasibility
profile, and treat B as the compromise if some income from the held LEAPS
is still wanted. C/D only with a genuinely new, pre-stated edge argument.

## 4. What the owner must supply before anything is registered
(numbers are owner-entered per operating manual; Claude proposes, never freezes)

1. Confirmed ticker list (resolve "hyln now").
2. Decision: spend ThetaData fetches on new names before ~07-25? (y/n, and
   which names — HYLN/NOW likely not worth the fetch, see table).
3. Capital per position and true liquid sleeve (resolve the $7k vs $20k drift).
4. Max acceptable loss per month, in dollars (the verdict gates on losses).
5. Structure choice from §3 (exactly one).
6. Earnings handling (hold through / exit before / skip entry) — mandatory
   registration field; all 8 names report late July–early Aug.
7. The numeric result that REJECTS H6, declared before the first run.

Nothing in this memo ranks, scores, or suggests specific trades; it is a
design-gate document. Next step is a filled-in pre-registration WITH the
owner, then (if data spend approved) a data audit on any newly fetched
chains before first use.

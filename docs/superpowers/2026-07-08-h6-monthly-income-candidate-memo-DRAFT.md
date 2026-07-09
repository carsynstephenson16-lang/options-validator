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

---

## 5. Owner inputs recorded (same day, 2026-07-08 — facts.log H6_OWNER_INPUTS)

1. **Tickers:** "hyln now" = HYLN *and* NOW, plus **SMCI** added. Candidate
   list (9): CRWV, PLTR, HYLN, NOW, CEG, TEM, NVDA, AMZN, SMCI.
2. **Data:** ThetaData sub active (owner statement); fetch approved. A
   six-week EOD window (2026-05-26..2026-07-07) for the 7 uncached names
   was pulled and audited the same day (facts.log H6_DATA_PULL).
3. **Capital:** total budget **$45k** (owner-asserted). Conflicts with the
   recorded $7k-liquid / $20k-sleeve figures; owner statement supersedes,
   drift noted and NOT silently reconciled.
4. **Monthly loss budget: $800.** Open semantics question for registration:
   is $800 (a) the maximum capital AT RISK per month (hard, structural), or
   (b) a realized-loss stop for the month? The difference decides which
   structures are even legal (see §6).
5. **Timing doctrine:** avoid IV-crush exposure now (pre-earnings); "really
   trade" after earnings.

## 6. What the $800/month budget does to the structure menu (Inference — arithmetic, not opinion)

- **Cash-secured puts on $100+ names cannot honor a hard $800 cap.** One
  0.20Δ CSP on a ~$150 name puts ~$14-15k at risk; an earnings-adjacent gap
  can realize a multi-thousand-dollar loss in one day. Under semantics (a),
  CSPs on most of this list are ILLEGAL structures. Under (b) they carry
  gap-through-the-stop risk that a stop cannot bound.
- **Defined-risk spreads fit the cap mechanically**: a $5-wide put spread
  collecting ~$1.00 risks ~$400/contract → two contracts/month max; a
  $10-wide risks ~$900 → one contract and it breaches on a full loss.
  So a hard $800 cap forces the trade H1/H2 already rejected after costs,
  in tiny size, where fixed costs (commissions + half-spread) weigh
  HEAVIEST. This is the central tension of H6 and it must be stated in the
  registration, not discovered after.
- **Consistency check the owner should confirm:** $800/month against $45k
  is a ~1.8%/month worst-case burn — coherent as risk appetite, but note
  the income side at that risk level is correspondingly small; "highest
  profit margin" and "$800 max monthly loss" pull in opposite directions.

## 7. Pre/post-earnings design sketch (aligned with the timing doctrine)

All four candidate names' earnings cluster late July–early Aug. IV-crush
mechanics (Inference from standard option pricing; no forecast): implied
vol on the front expirations inflates into a report and collapses after.
Therefore:

- **Now → each name's report: NO new long-premium positions** on candidate
  names (debit spreads/calls bought now pay the inflated vol and eat the
  crush even when direction is right). Short premium "wins" the crush but
  carries the gap through the report — incompatible with a hard $800 cap.
  Pre-earnings period = data collection, watchlists, and the H5 lanes on
  already-cached names if their gates pass. Standing aside IS the trade.
- **After each report:** vol resets; entries per whichever §3 structure the
  owner picks, gated on the frozen liquidity checks and sized to the $800
  budget. This becomes H6's entry-timing rule if the owner freezes it:
  e.g. "no entry in the N trading days before a scheduled report; entries
  allowed from the first session after the report."
- **What H6 still needs before registration:** (i) the $800 semantics call
  (§5.4), (ii) ONE structure from §3, (iii) the numeric rejection
  criterion, (iv) per-name earnings dates pinned from IR pages, (v) the
  liquidity screen results from the new-name data pull (feasibility gate:
  names failing MIN_OPEN_INTEREST / MAX_SPREAD_PCT on the contracts the
  strategy would trade are OUT regardless of preference).

---

## 8. Liquidity screen results (2026-07-08 pull; Repo-verified from cached chains)

Six-week EOD window (2026-05-26..2026-07-07), 29 trading days per name,
audit verdict PASS WITH WARNINGS across all 203 name-days (warnings are
IV=NaN/0 on non-selectable deep-ITM/far-OTM rows only; zero BLOCKs).
Profiler = ATM ~37-DTE puts, frozen gates MIN_OPEN_INTEREST=100,
MAX_SPREAD_PCT=10%. A correction to §2: NOW trades ~$106 post-split
(mkt cap ~$110B) — the "CSPs capital-infeasible" assumption was stale;
NOW fails on LIQUIDITY, not capital.

| Name | Median ATM spread % | Median ATM OI | Liquid strikes (median) | Screen verdict |
|------|--------------------:|--------------:|------------------------:|----------------|
| NVDA | 1.17 | 732 | 14 | **PASS** (deep history 2018+ in legacy cache; 2022+ passes gates) |
| PLTR | 3.13 | 172 | 9 | **PASS** (history 2021+ passes gates) |
| SMCI | 17.18 | 128 | 0 | **FAIL (marginal)** — OI fine, spreads blown out in the current crisis regime; recheck post-probe/earnings |
| NOW  | 13.33 | 61 | 0 | **FAIL** — ATM monthly puts have failed these gates EVERY year 2018–2026 (repo data) |
| CRWV | 10.57 | 56 | 0 | **FAIL** (thin OI, borderline spreads; ~1yr listed history) |
| TEM  | 18.48 | 0  | 0 | **FAIL** |
| HYLN | 26.89 | 69 | 0 | **FAIL (hard)** — ~128 rows/day, median ONE contract chain-wide passes the gates |

Feasible set for monthly structures under the frozen gates, as of this
screen: **NVDA, PLTR (new) + CEG, AMZN (already in universe).** Failing
names are not banned opinions — they are gate readings from our own data
and can be rescreened later (SMCI especially, once its crisis IV regime
resolves).

## 9. Earnings + IV landscape (web research 2026-07-08/09; secondary sources, labeled)

| Name | Next earnings | Confirmed? | Price ~7/8 | IV context (Barchart snapshot 7/9) |
|------|--------------|-----------|-----------:|-------------------------------------|
| NOW  | **Jul 22** | company-confirmed | ~$106 | IV rank ~86, percentile 95 — biggest earnings-IV ramp of the list |
| MSFT | Jul 29 | company-confirmed | ~$382 | — |
| AMZN | ~Jul 30 | estimated | ~$242-244 | — |
| PLTR | ~Aug 3 | estimated | ~$132 | IV ~60%, rank ~57 |
| SMCI | ~Aug 4 | estimated | ~$27 | IV ~99%, percentile 99 — **crisis-driven** (Taiwan export probe + $7B dilution), not earnings premium |
| CEG  | Aug 6 | IR-confirmed | ~$245 | — |
| TEM  | ~Aug 7 | estimated | ~$57 | IV ~79%, rank ~54; short interest ~30% of float |
| VST  | Aug 7 | company-confirmed | ~$155 | — |
| CRWV | ~Aug 11 | estimated (least reliable) | ~$90 | IV ~97% (Meta-resale scare), rank ~51 |
| HYLN | ~Aug 11 | estimated | ~$4 | IV ~143% |
| NVDA | ~Aug 26 | estimated | ~$201 | IV ~41%, rank ~40 — no earnings ramp yet |

Doctrine mapping ("no IV-crush exposure now; real trades after earnings"):
the earliest post-earnings windows on feasible names open ~Jul 31 (AMZN),
~Aug 4 (PLTR), Aug 7 (CEG); NVDA not until ~Aug 27. Between now and then,
long premium on these names buys inflated vol; short premium eats the gap
— under the $800 budget, standing aside on candidates IS the position.
SMCI note: 99th-percentile IV looks like "juicy premium" and is actually
regulatory-tail pricing; it also fails the liquidity screen. Not a trade.

## 10. Proposed H6 registration skeleton (Claude PROPOSES, owner ENTERS/OVERRIDES every number)

| Field | Proposal (LLM-asserted, reasoning inline) |
|-------|--------------------------------------------|
| Name/version | H6 "post-earnings monthly income" v1 |
| Tickers | NVDA, PLTR, CEG, AMZN (screen §8; others excluded by gates) |
| Structure | ONE of §3 — given $800 hard cap, the only mechanically legal defaults are defined-risk spreads (§6); owner picks width |
| Entry rule | no entry within N days BEFORE a scheduled report (owner picks N, e.g. 5); entries allowed from first session after the report; liquidity gates on BOTH legs |
| Short-leg delta | 0.20 (reuse H5_INCOME_DELTA; band ±0.15) unless owner overrides |
| Expiry | nearest monthly, 20–45 DTE at entry |
| Exit rule | owner must pick: hold-to-expiry vs profit-take/stop (H1 evidence: the stop was the loss engine) |
| Max at-risk per month | $800 TOTAL across all open H6 positions (semantics (a)); if owner meant (b), redesign needed |
| Capital assumption | $45k total (owner-asserted 2026-07-08) |
| Earnings handling | skip-entry-before, enter-after (the doctrine itself) |
| Validation design | forward paper window (2023+ backtests not credible for AI names); backtest only as descriptive context on NVDA/PLTR history |
| REJECTS H6 | e.g. "expectancy CI90 upper bound < 0 after M losses" — owner must set M and the window |
| Justifies continuing | owner must set before first entry |

Registration happens in the chained ledger only after the owner fills the
blanks. Until then H6 does not exist as a hypothesis; this memo is context.

---

## 11. Owner revision V2 (2026-07-08, facts.log H6_OWNER_INPUTS_V2) and the concrete proposal

Owner: **$2,000/month max capital at risk** (hard at-risk semantics);
put-spread proposal REJECTED as too conservative; rejection-criterion
indifference ("meh") — so every number below is stated explicitly and the
owner confirms or overrides; silence is not registration.

**H6 v1 proposal: "post-earnings tactical long calls"** (every value
LLM-proposed unless marked owner):

- **Names:** NVDA, PLTR, AMZN. CEG is excluded by DATA: its 45–90 DTE
  calls quoted 14–17% spreads on 2026-07-06 — fails MAX_SPREAD_PCT on the
  leg this structure trades (Repo-verified from cache). SMCI/NOW/CRWV/
  TEM/HYLN already failed §8.
- **Entry:** only in the first 5 trading sessions AFTER a name's earnings
  report (the crush is behind, the gap is behind); never in the 5 sessions
  before one. Contract must pass MIN_OPEN_INTEREST / MAX_SPREAD_PCT.
- **Contract:** single long call, nearest monthly 45–90 DTE, target delta
  0.40 (band ±0.15 reused). Cache pricing 07-06/07-07: NVDA 0.42Δ Sep18
  ≈ $1,035; PLTR 0.40Δ Sep18 ≈ $865; AMZN 0.41Δ Sep18 ≈ $1,150 — i.e.
  roughly TWO contracts per month inside the cap.
- **Sizing (owner):** total premium at risk ≤ $2,000/month; max one
  contract per name, max 2 concurrent positions. Premium = max loss;
  the cap cannot be gapped through (defined risk).
- **Exit (proposed, frozen at registration):** close at 21 DTE at
  conservative fills; NO intramonth stop (H1 evidence: stops were the
  loss engine); no profit-take in v1 (each extra rule is a fittable knob).
- **Validation:** forward paper window in the tracked book; descriptive
  backtest on NVDA/PLTR history allowed as context, never as the verdict.
- **REJECTS H6 (proposed, needs owner literal confirm):** after 8
  completed positions, if bootstrap CI90 upper bound of per-trade
  expectancy < 0 → REJECT; hard kill regardless: 3 consecutive months
  of full-cap loss → REJECT.
- **Justifies continuing:** CI90 lower bound > 0 after 8 completed
  positions → extend the window, nothing more.

Honesty line (unchanged by the excitement): this is a directional bet
that AI names drift up post-earnings. It has no demonstrated edge; the
forward window exists to measure whether it has one. "No edge after
costs" remains a successful outcome.

# H9 — post-earnings conditional historical study (REGISTERED)

**Status: REGISTERED 2026-07-18 (owner PASS confirmation in chat, this
session). §5 values were owner-approved 2026-07-16 by reference (entry
mechanics disclosed in §5). External independent review (hybrid model, owner
decision 2026-07-16): adversarial fresh-context review returned FAIL with
four blockers (B1 silent-fetch, B2 non-quarterly exit contamination, B3
stale trial pin, B4 hardcoded DRAFT path); all were fixed plus conditions
C5/C6 (commit 3a592a9) and a post-merge chain_dir-coherence defect (commit
705325d); re-review returned PASS-WITH-CONDITIONS whose residual conditions
RC1/RC2 are executed by this freeze commit (atomic rename +
`config.H9_SPEC_PATH` update; `spec_sha256=<hex>` bound literally in the
`H9_REGISTERED` fact). `trial_count` is DERIVED from
`ledger/experiments.jsonl` at registration time (the append-only ledger is
the single source of truth; never pin a stale count in the spec, code, or
tests — review B3). The sha256 of this exact committed file is bound in the
`H9_REGISTERED` fact; any later edit to this file is spec drift and the
prereg gate refuses.**

**Authority:** `H7_7B2R1_DECISIONS` item (5): "a post-earnings-only
historical study may later be registered as a SEPARATE conditional hypothesis
and must never reject or validate H7." This document is that registration.
It does not touch the tombstoned H7 historical diagnostic
(`H7_HISTORICAL_WITHDRAWAL_HASH`), does not amend H6 or H8, and runs on
already-cached data only — **zero new data spend is a hard property; if any
required input is not already in the local cache, the affected event is
excluded or the study halts, never fetched.**

---

## 1. Hypothesis

On the eight archived names, a **positive first-close reaction to a verified
quarterly earnings report** is followed by enough continued upside that an
H6-style long call opened at the next session's close has per-trade
expectancy > 0 after frozen costs.

H9 is **calls-only**. A negative or sub-threshold reaction produces NO TRADE
(a put lane would be a different hypothesis with different mechanics; it is
out of scope and its absence is disclosed, not implied).

**Declared non-blind.** The full 2018-01-02..2026-06-30 window is historical
and the spec was written in 2026 with market hindsight; additionally the
Phase E1 descriptive study (2026-07-15) has already examined post-earnings
IV/price behavior for NVDA, AMZN, PLTR, SMCI (not NOW, MSFT, VST, CEG). The
trigger below is not derived from E1 outputs (E1 measured IV crush, spreads,
and decay — not reaction-sign drift), and the H6 construction predates E1
(registered 2026-07-08); both facts limit but do not remove the
contamination. The outcome vocabulary in §7 is how this is priced in.

**Relation to live hypotheses (owner rule, invariant):** no H9 outcome
rejects, validates, or amends H7, H6, or H8. H6's forward window resolves on
its own registered terms regardless of what H9 shows.

## 2. Event timing (owner rule 1 — exact, no look-ahead)

All session and close-time arithmetic uses the repo's XNYS calendar with
close timestamps (the same calendar bound into audit receipts v3/v4).
Holidays and half-days are handled by that calendar, never assumed.

- **T_accept** — the 8-K Item 2.02 `acceptanceDateTime` (UTC) of the
  verified occurred report, from `data/earnings/assertions_v2.csv`.
  Dedupe rule: **earliest acceptance per (symbol, report date)**; later
  duplicates and 8-K/A amendments never create a second event and never
  move an existing event's T_accept.
- **T_pre** — the last XNYS session whose official close is **strictly
  before** T_accept.
- **T_dec (decision point)** — the first XNYS session whose official close
  is **strictly after** T_accept. For an after-market filing this is the
  next trading day's close; for a before-open filing it is the same day's
  close. The filing is treated as knowable only from T_dec's close onward.
- **T_entry** — the next XNYS session after T_dec. The entry fill occurs at
  T_entry's close under the frozen fill model. This preserves the repo's
  registered T→T+1 decision-to-fill causality: decide on T_dec's completed
  close, enter no earlier than the following trading day.
- If T_accept falls in a window with no next session inside the study window
  (e.g., report near 2026-06-30), the event is excluded with reason
  `window_edge`, counted in the census.
- **Event classification (added pre-freeze 2026-07-17, final-review finding):**
  raw Item 2.02 occurred rows are NOT all quarterly earnings (SMCI
  delinquency-era business updates; NOW 2019-10-21 non-earnings filing).
  Every event must carry a `quarterly_results` classification in
  `data/earnings/h9_event_class_v1.csv` (append-only; one row per event;
  SEC evidence URL required; classes: quarterly_results | business_update |
  other_item_202). Missing or non-quarterly classification fails closed
  (`unclassified_event` / `non_earnings_event` census exclusions). The
  next-report exit and the near-report fail-loud geometry are computed on
  the CLASSIFIED quarterly set only — with genuine quarterly spacing a
  near-report abort indicates an invariant violation, so aborting the run
  remains correct.

## 3. Trigger and lifecycle (owner rule 2 — the measurable condition)

"It is after earnings" is not the trigger. The trigger is:

- **Reaction:** `R = close(T_dec) / close(T_pre) − 1`, from adjusted
  underlying closes via the registered closes contract
  (`load_closes_adjusted`).
- **Direction rule:** `R ≥ +H9_REACTION_MIN` → CALL candidate.
  `R < +H9_REACTION_MIN` (including all negative R) → NO TRADE, recorded
  with reason `reaction_below_min`.
- **Contract selection (inherited from H6, §4):** the highest-delta call
  with delta in **[0.30, 0.50]**, nearest **monthly** expiry with DTE in
  **[45, 90]** at T_entry, ask ≤ the premium cap in §5. Selection uses
  T_entry's EOD chain only.
- **Liquidity gate at T_entry (inherited, repo general gate):** valid
  two-sided NBBO, OI ≥ 100, quoted spread ≤ 10% of mid. Any failure →
  **cancel-never-chase**: the event terminates with reason
  `entry_liquidity_fail` or `no_contract_in_bands`; no substitute session,
  no substitute contract outside the bands.
- **Exits — deterministic same-session priority (protective before
  profitable, matching the repo's frozen exit-reason ordering):**
  1. **Pre-next-report close:** hard close at the session
     `H9_NEXT_REPORT_EXIT_SESSIONS` XNYS sessions before the *next* verified
     occurred report of the same symbol. DISCLOSED CAVEAT: the historical
     study uses the realized next-report date, which a live trader would
     have known only approximately; this is a mild look-ahead in exit
     timing, unsigned in direction (it removes both the next event's gains
     and its losses), and exists to keep each trade a single-event estimand.
  2. **DTE close:** close when remaining DTE ≤ `H6_CLOSE_AT_DTE` (21).
  3. **Take-profit:** close at the first session close where the position
     marks ≥ `H6_TAKE_PROFIT_PCT` (+100%) over entry cost. The mark
     convention must be identical to `h6_watch`'s registered sell-side
     valuation — the implementation imports or mirrors it exactly; a new
     mark convention is a spec violation.
  All exits are evaluated at session closes only and fill at the **next**
  session's close (same T→T+1 rule as entries). A missing exit-session
  chain follows Stage-4 doctrine: append the visible gap and exit at the
  first later valid session; the gap is recorded in the run artifact.
  **Quote-state semantics on the fill path (added pre-freeze, 2026-07-17,
  from adversarial review of the engine):** a chain row that is PRESENT
  with bid ≤ 0 is not a data gap — it is the market pricing the call as
  worthless, and the trade books a realized max loss (`pnl = −entry cost`,
  flagged `worthless_quote_exit`) rather than dropping out of the scored
  set. Routing present 0-bids to the gap bucket would disproportionately
  exclude losers and bias the verdict away from REJECTED. A present but
  crossed/malformed quote remains a data-artifact gap. The protective
  exits (pre-next-report, DTE close) are pure calendar decisions and never
  depend on quote presence; only the take-profit check reads quotes. A
  next report closer to entry than `H9_NEXT_REPORT_EXIT_SESSIONS + 1`
  sessions is contaminated geometry and fails loud (no trade simulated).
- **No stop-loss** (H1 evidence: stops were the loss engine; inherited
  design decision, disclosed).
- **Sizing:** fixed 1 contract per event; no compounding; no monthly or
  sleeve caps — this is a registered **isolated-lane diagnostic** per the
  owner's prior estimand ruling (7b-0.1: portfolio caps do not apply in the
  diagnostic; per-trade risk and one-event-one-trade still bind).

## 4. Inheritance table (owner rule 3 — field by field, no "where applicable")

| # | Field | Value | Source | Notes |
|---|-------|-------|--------|-------|
| 1 | Universe | NOW, NVDA, PLTR, MSFT, AMZN, VST, CEG, SMCI | **H7-frozen** (the 8 audited archive names) | only names with both full chain caches and SEC occurred archives |
| 2 | Window | 2018-01-02 .. 2026-06-30 | **H7-frozen** (`H7_BACKTEST_START/END`) | non-blind, disclosed §1 |
| 3 | Event source | `assertions_v2.csv` occurred rows, 8-K Item 2.02, earliest acceptance per report date | **Existing store** | append-only; no aggregator dates |
| 4 | Session calendar | XNYS with close timestamps | **H7-frozen** | receipts v3/v4 lineage |
| 5 | Decision/entry causality | decide T_dec close, fill T_entry close (T→T+1) | **H7-frozen** (7b-1 harness) | §2 |
| 6 | Underlying closes | adjusted, via `load_closes_adjusted` | **H7-frozen** (CLOSES CONTRACT) | includes USAR-style entity floors; splits handled by the SPLITS registry |
| 7 | Fill model | full per-leg spread crossing + 1% `SLIPPAGE_HAIRCUT` + adverse penny rounding, once | **H7-frozen** (realism-audit grade A−) | |
| 8 | Commission | $0.65/contract/leg each way | **H7-frozen** (`COMMISSION_PER_CONTRACT`) | regulatory fees absent — inflates results slightly, disclosed as in 7b-1 |
| 9 | Liquidity gate | two-sided NBBO, OI ≥ 100, spread ≤ 10% mid | **H7-frozen** (general gate) | evaluated at T_entry only |
| 10 | Option structure | single long call, nearest monthly | **H6-frozen** | |
| 11 | DTE band at entry | 45–90 | **H6-frozen** (`H6_DTE_BAND`) | |
| 12 | Delta band | 0.30–0.50, highest delta | **H6-frozen** (`H6_DELTA_BAND`) | |
| 13 | Take-profit | +100% | **H6-frozen** (`H6_TAKE_PROFIT_PCT`) | |
| 14 | DTE close | 21 DTE | **H6-frozen** (`H6_CLOSE_AT_DTE`) | |
| 15 | Stop-loss | none | **H6-frozen** | disclosed §3 |
| 16 | Entry timing | exactly T_entry (one session), conditional on R | **NEW — this spec** | deliberately narrower than H6-forward's unconditional 5-session window; this difference IS the hypothesis |
| 17 | Premium cap per trade | **OWNER DECISION §5** | **CONFLICT** | `H6_MAX_ASK_DOLLARS`=$1,000 vs global `MAX_LOSS_PER_TRADE`=$600; a long call's max loss is its full cost; the owner must pick which binds |
| 18 | Reaction threshold `H9_REACTION_MIN` | **OWNER-TYPED §5** | **NEW** | |
| 19 | Next-report exit buffer `H9_NEXT_REPORT_EXIT_SESSIONS` | **OWNER-TYPED §5** | **NEW** (H8 uses 2 for its analogous rule — offered as a default, not inherited silently) | |
| 20 | Census floor `H9_MIN_ELIGIBLE_EVENTS` | **OWNER-TYPED §5** | **NEW** | §6 |
| 21 | Adjudication stats | `MIN_LOSSES_FOR_VERDICT`=10, `BOOTSTRAP_SAMPLES`=5000, block bootstrap (Politis-White n^(1/3), constants [0.5,1,2,4]), dependence-aware CI90 | **Repo-frozen** | no new statistical machinery |
| 22 | Contracts per event | 1, no compounding | **H7-frozen** (`H7_FORWARD_CONTRACTS` convention) | |
| 23 | Portfolio caps | none (isolated-lane diagnostic) | **Owner-ruled** (7b-0.1 estimand decision) | disclosed §3 |
| 24 | Exclusion registry | PLTR pre-2020-10-05, CEG pre-2022-02-08, SMCI 2018-08-23..2020-05-04 | **H7-frozen** (`H7_AMENDMENT_V1_3`, ratified) | archive-availability gaps, no existence claim |

Every field is one of: H7-frozen, H6-frozen, repo-frozen, owner-ruled,
OWNER-TYPED, or OWNER DECISION. There is no "where applicable" anywhere in
this spec.

## 5. Owner-typed values (APPROVED 2026-07-16; entry mechanics disclosed)

**ENTRY MECHANICS (disclosed):** the owner did not retype the five numerals.
The owner approved the LLM-proposed values by reference in the 2026-07-16
orchestration session (verbatim: "I approve the five H9 timing rules
previously stated"); the agent transcribed them into the value column at
owner direction, following the repo's established owner-directed
transcription pattern (H7_STAGE4_SPEC_AMENDMENT_V1 precedent). Provenance of
each value remains LLM-proposed, owner-adopted.

| Parameter | Owner-approved value | LLM proposal | Proposal reasoning (Inference) |
|---|---|---|---|
| `H9_REACTION_MIN` | **0.02** | 0.02 | must exceed ordinary daily noise so the sign is an earnings reaction, not drift; a lower value (even 0.0) reduces researcher degrees of freedom at the cost of noisier direction; a higher value shrinks the sample |
| `H9_NEXT_REPORT_EXIT_SESSIONS` | **2** | 2 | matches `H8_EXIT_SESSIONS_BEFORE_REPORT`; one session of schedule-slip buffer before T-1 |
| `H9_MIN_ELIGIBLE_EVENTS` | **60** | 60 | ~254 occurred events, minus exclusions/data attrition, then the reaction filter roughly halves triggered trades; below ~60 data-sufficient events the CI90 on expectancy is unlikely to be decision-grade, and `MIN_LOSSES_FOR_VERDICT`=10 becomes hard to reach |
| Premium cap per trade (§4 row 17) | **$600** | $600 | the global `MAX_LOSS_PER_TRADE` is the older, stricter promise; a long call's premium is its max loss, so $1,000 asks would breach it — but the owner owns this reconciliation |
| Cohort cut ratification (§6) | **yes** | yes | pre-declare the E1-uncontaminated secondary cut (NOW, MSFT, VST, CEG) as informational-only; verdict binds to the primary (all-8) cohort |

## 6. Eligibility census — counts and data only, before the one run (owner rule 4)

A census tool runs BEFORE the backtest and may inspect ONLY:

1. presence and parseability of the 8-K acceptance timestamp;
2. resolvability of T_pre / T_dec / T_entry on the calendar;
3. presence of adjusted underlying closes at T_pre and T_dec;
4. presence of the T_entry EOD chain in the cache;
5. presence of chains across the maximum exit window (gaps listed);
6. existence of ≥1 contract passing the §3/§4 bands and liquidity gate at
   T_entry.

The census **must not** compute R, returns, P&L, or any price path beyond
the T_entry contract-existence check. It emits per-name
eligible/excluded counts with typed reason codes
(`no_acceptance_ts`, `window_edge`, `registry_excluded`, `missing_closes`,
`missing_entry_chain`, `no_contract_in_bands`, `entry_liquidity_fail`,
`exit_window_gaps` as WARN) and a content-addressed manifest of every file
it touched.

**If data-sufficient events < `H9_MIN_ELIGIBLE_EVENTS`, the study terminates
as INSUFFICIENT_SAMPLE without the run ever executing.** No parameter may be
adjusted to harvest more events after the census is seen — the census result
is itself part of the registered record.

## 7. Outcomes — frozen vocabulary, three values only (owner rule 5)

| Outcome | Meaning | Trigger |
|---|---|---|
| `REJECTED` | the conditional post-earnings call idea failed its own test | bootstrap CI90 **upper** bound of per-trade expectancy < 0, with ≥ `MIN_LOSSES_FOR_VERDICT` losses in cohort |
| `INSUFFICIENT_SAMPLE` | not enough events or losses to say anything | census floor unmet, OR triggered trades' losses < `MIN_LOSSES_FOR_VERDICT`, OR CI unstable across registered block constants |
| `NOT_REJECTED_FOR_THIS_NARROW_HISTORICAL_TEST` | survived a non-blind, calls-only, single-construction historical test — nothing more | neither of the above |

The third outcome **explicitly does not** authorize any live trade, does not
validate H7 (owner rule, `H7_7B2R1` item 5), does not amend H6 or H8, and is
not a profitability claim. Kill-not-bless: this study can only remove an
idea or fail to remove it.

The verdict binds to the primary all-8-name cohort. If ratified in §5, the
E1-uncontaminated cut (NOW, MSFT, VST, CEG) is reported alongside as
informational, and cannot flip the verdict in either direction.

## 8. Run binding and required adversarial tests (owner rule 6)

Exactly **one** run. The run artifact binds, content-addressed:

- this spec's frozen sha256 and the immutable code commit;
- the canonical config hash;
- the census output and the full eligible/excluded event table with reasons;
- the manifest (path + sha256) of every cache file read;
- the exact assertion-store rows (by id) that defined the events.

Ledger flow, strictly ordered: owner types §5 → owner's external review
returns PASS on the typed spec → frozen spec committed + `H9_REGISTERED`
(spec sha256 bound in the fact as `spec_sha256=<hex>`; `trial_count` derived
from `ledger/experiments.jsonl` at registration, not pinned here) →
`H9_CENSUS` → `H9_RESULT` (verdict + receipt
hash). Registration never precedes the external review. Any deviation, crash, or input change
mid-run voids the run; a voided run is recorded honestly and does NOT refund
the one-run contract without a new owner decision.

**Test matrix the implementation must pass before the run (test-first;
Sonnet builds, Opus adversarially reviews, orchestrator verifies):**

1. after-market filing → T_dec is next session's close, never same-day;
2. before-open filing → T_dec is same-day close;
3. acceptance timestamp exactly at the close boundary → strict inequality
   resolves it (after close ⇒ next session);
4. duplicate 8-K and 8-K/A amendment → one event, earliest acceptance,
   immutable T_accept;
5. missing T_entry chain → cancel-never-chase, reason-coded, no substitute;
6. missing exit-session chain → visible gap + first later valid session;
7. stock split inside a holding period → adjusted continuity, position marks
   and exit math consistent (SPLITS registry);
8. T_entry falls on a holiday/half-day → calendar resolves the true next
   session and its real close time;
9. registry-excluded windows (PLTR/CEG/SMCI) → events inside them excluded
   with `registry_excluded`, never silently absent;
10. next verified report closer than the DTE window → pre-next-report exit
    fires first per §3 priority;
11. census attempts to read a price path beyond its charter → test asserts
    the census API cannot return returns/P&L (structural, not honor-system).

## 9. What this study is not

Not a reopening of the tombstoned H7 historical diagnostic (different
hypothesis, different trigger, different construction, own registration).
Not evidence about H6's forward window. Not a data-spend vehicle. Not
repeatable: one vintage, one run, one verdict, per the one-run contract
discipline established by the QM study.

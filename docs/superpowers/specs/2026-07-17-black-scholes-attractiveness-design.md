# Black–Scholes descriptive layer for attractiveness + QM re-examination — design

**Date:** 2026-07-17 (rev. 2026-07-18, owner integrity corrections folded in)
**Status:** DESIGN — pending owner review of this rev, then writing-plans.
**Audience:** implementable by another agent (Codex/ChatGPT/Claude). Every study
formula and record type is frozen here; nothing is left to implementer taste.
**Author:** Claude Code (Opus 4.8), with owner (Carsyn) corrections folded in.

## 0. One-line intent

Add a real, tested Black–Scholes math unit and wire it into the attractiveness
layer **only as descriptive/data-quality features** (never a trigger); fix the
earnings silent-GREEN integrity hole **on the path that actually renders core
names**; publish a mechanically-valid, trial-counted QM "attempt #2"
retrospective record from the already-computed readings (no rerun); and set up
owner-typed forward registrations (H10a/H10b as two separate records) and a
no-verdict rank-quality study. **No P&L backtest, no OOS reveal, no verdict is
produced by this arc.**

## 1. Plain-English primitives

- **Black–Scholes (BS):** a *European*-option closed-form pricing model; a
  no-arbitrage quoting/interpolation convention, **not** an alpha model.
- **Greeks:** sensitivities of option value to underlying (delta), its rate
  (gamma), time (theta), volatility (vega), rates (rho).
- **Implied volatility (IV):** the volatility input making a model price equal a
  market price; the market's price inverted through BS, not a forecast.

## 2. The single authority rule

> **The agent drafts every threshold as a blank. The owner types all
> H10a/H10b and rank-quality-study values before they take effect. Because the
> QM/H10 signals are chosen with the study outcome already known, "freeze before
> seeing results" is impossible and is NOT claimed; instead the signal selection
> is declared *outcome-informed and permanently disclosed*, and only
> **observations recorded after the registration timestamp** count toward any
> future reading. The agent never types a study threshold.**

This rule supersedes any other phrasing here. Math *conventions* (§4), detector
*tolerances* (§5), and sourced market *inputs* (§7) are engineer-proposed and
owner-approved via this spec — but the staleness limit (§8) is owner-typed
because it gates a trade-facing GREEN badge. All numeric tolerances must appear
with values and units in this spec before approval; none may stay "TBD."

## 3. Scope boundary

**IN (descriptive / data-quality / integrity — no verdict, no reveal):** BS math
unit (§4); gross-error detector (§5); earnings-conditioned IV term-structure
column (§6); point-in-time rates/dividends (§7); the *real-path* earnings
staleness fix (§8); QM retrospective_result publication (§9); feature-validation
recompute (§10); rank-quality descriptive study (§11); dashboard surfacing
(§12); H10a/H10b forward registrations (§13).

**PARKED → `ideas-parking-lot.md`:** BS "fair value vs market" richness ranking;
generic (non-earnings-conditioned) term/skew richness; any P&L backtest on the
big 4; any QM study rerun or fresh QM historical recomputation.

## 4. Component: `options_researcher/black_scholes.py`

Pure, offline, no I/O. Functions: `d1`, `d2`, `bs_price`, `delta`, `gamma`,
`vega`, `theta`, `rho`, `implied_vol`.

### 4.1 ThetaData reference facts (Official-source: ThetaData Greeks docs, owner-supplied)

ThetaData's EOD Greeks are computed with **European Black–Scholes** (same model
class as this unit — so any BS-vs-vendor gap is an *input/convention* gap, not a
model-class gap). ThetaData: uses the **exact underlying tick** (not the daily
close); defaults the rate to **SOFR**; **ignores dividends unless supplied**;
and reports **vega and rho scaled such that they require ÷100** to be per one
percentage-point. The repo currently passes `vega`/`theta` through without ÷100
(`thetadata_adapter.py:271-275`) while `_vol_prose` treats vega as per-1-point —
**an unresolved units inconsistency the detector must pin before trusting vega.**

### 4.2 Frozen conventions (engineer-proposed; owner approves via this spec)

| Convention | Frozen choice |
|---|---|
| Rate / dividend compounding | continuous-compounded `r` and `q` |
| Time to expiry | ACT/365 Fixed: `t = calendar_days / 365` |
| Valuation & expiration instant | valuation at **market close 16:00 America/New_York**; expiry at **16:00 ET on the expiration date**; `t` in calendar days between those instants ÷ 365 |
| Spot vs strike basis | **raw (unadjusted) spot vs raw strikes**, both from the *same synchronized snapshot* |
| Price used for IV inversion | quote **midpoint** `(bid+ask)/2`, only after quote validation (§4.3) |
| Theta units & sign | per **calendar day**; **sign negative** for long options losing value as time passes (θ = ∂V/∂t with t = time, reported as decay/day) |
| Vega units | per **1 percentage-point** (0.01) vol change |
| Rho units | per **1 percentage-point** (0.01) rate change |
| IV solver | Newton seeded at 0.30, **bisection fallback** on `[0.01, 5.0]` |
| Convergence tolerance | `|model_price − target| < 1e-6` USD, max 100 iterations |
| Zero volatility (`σ→0`) | `C = max(S·e^{−qt} − K·e^{−rt}, 0)`, `P = max(K·e^{−rt} − S·e^{−qt}, 0)` (discounted intrinsic) |
| At/after expiry (`t ≤ 0`) | price = undiscounted intrinsic; IV = `NaN` + `expired` flag |
| Target price with no European root | IV = `NaN` + **`no_european_bs_root`** flag (a valid American price can have no European BS IV — this is NOT an arbitrage violation) |
| Tolerance units | all detector tolerances expressed in **absolute USD** unless explicitly a Greek epsilon (§5) |

### 4.3 Quote validation (before any midpoint use)

A row is usable for IV inversion only if `bid` and `ask` are finite, `bid ≥ 0`,
`ask ≥ 0`, and `bid ≤ ask`. Otherwise the row is `MISSING`/`NOT_ASSESSED` (§5),
never inverted.

### 4.4 Tests (unittest, offline)

Textbook price vectors; European put–call parity as a **unit-level invariant
only** (never applied to live quotes — §5); Greeks vs central finite-difference
within tolerance; IV round-trip (price→IV→price) within `1e-6`; boundary
behavior at `t≤0`, `σ→0`, no-root, and out-of-range inputs; theta sign test.

## 5. Component: gross-error detector

Catches **data glitches**, never model disagreement. It needs **synchronized
inputs** (underlying price + option quote from the same instant). The current
cache lacks them (§5.3), so it runs only on enriched rows; legacy rows are
`NOT_ASSESSED`.

### 5.1 Disjoint outcome tiers

- **INVALID_NO_ARB** — American no-arbitrage bound violation (§5.2).
- **INVALID_GREEK** — a Greek is impossible: non-finite; `gamma < 0`;
  `vega < 0`; delta outside range by more than a **named Greek epsilon
  `DELTA_EPS = 0.02` (dimensionless)** — calls outside `[0−DELTA_EPS, 1+DELTA_EPS]`,
  puts outside `[−1−DELTA_EPS, 0+DELTA_EPS]`.
- **INVALID_QUOTE** — crossed (`bid > ask`) or negative quote.
- **EXTREME** — IV `≤ 0.02` or `≥ 5.0`, **after confirming the cache stores IV
  in decimal units** (`0.35`, not `35`). Suspicious, not impossible.
- **no_european_bs_root** — midpoint has no European BS IV (from §4). Reported,
  **not** INVALID.
- **MISSING / NOT_ASSESSED** — vendor field absent/non-finite, or the row lacks
  the synchronized inputs the detector requires. Not a data error — an absence
  of ability to assess.

Never emit any flag for ordinary BS-vs-vendor numeric disagreement.

### 5.2 Executable American no-arbitrage bounds

For standard American equity options (loose, execution-side, with USD tolerance
`NOARB_TOL = 0.02` USD):

```
Call:  max(S − K, 0)  ≤  C  ≤  S
Put:   max(K − S, 0)  ≤  P  ≤  K
```

Flag **INVALID_NO_ARB** only when `ask < lower − NOARB_TOL` (offered below the
floor → executable arbitrage) **or** `bid > upper + NOARB_TOL` (bid above the
ceiling). A merely low bid or an absurdly high ask **alone is not** executable
arbitrage and is not flagged. `S` is the **synchronized raw spot**, `K` the raw
strike.

### 5.3 Cache cannot currently run the synchronized detector

`CHAIN_COLUMNS` (`thetadata_adapter.py:46-55`) has no underlying price,
underlying/option timestamp, `iv_error`, rate, dividend input, or model version;
the merge (`:274-280`) strips them. Therefore:

- **Legacy cached rows are `NOT_ASSESSED`** by the detector — no fabricated spot,
  **never** substitute the daily close for the synchronized tick.
- Enabling the detector requires either (a) **enriching future cache rows** with
  the synchronized fields, or (b) an **explicitly owner-authorized historical
  re-pull**. This spec authorizes neither silently; it flags the dependency and
  defaults to `NOT_ASSESSED` until the owner chooses.

## 6. Component: earnings-conditioned IV term-structure column (fully frozen)

Descriptive study-selection column; never a GREEN action badge. **Entire formula
frozen here before any value is revealed:**

- **ATM selection:** the contract whose strike minimizes `|strike − synchronized
  spot|` per (expiry, right); use the **put** side (matches existing `atm_iv`).
- **Near tenor:** nearest monthly expiry with DTE in `[15, 45]`. **Long tenor:**
  nearest monthly with DTE in `[60, 120]`.
- **Interpolation:** none across strikes; if no expiry falls in a tenor band,
  the column is `MISSING` for that date (no extrapolation).
- **Slope metric:** `term_slope = atm_iv(near) − atm_iv(long)` (positive =
  inverted/near-rich).
- **Earnings-window rule:** the column is *interpreted* only when a scheduled
  earnings report lies in `(chain_date, near_expiry]` under point-in-time
  evidence; otherwise it is emitted but tagged `no_earnings_in_window`.
- **Normalization:** **percentile rank** of `term_slope` within that name's
  **prior-through-date history** — observations with date `≤ current date`
  **only** (causal; never full-history). Window = trailing **252 trading days**;
  **minimum 60 observations** or the column is `MISSING`. Ties: average rank.
  Missing rows are excluded from the percentile base, not zero-filled.
- **Point-in-time / lookahead rule:** historical dates use
  `assertions_view(assertions, known_as_of=<that date>)`. If point-in-time
  earnings evidence is unavailable for a date, that date's column is labeled
  `ex-post / lookahead-contaminated` and **excluded from H10 and rank-quality
  evidence** (may be displayed as a descriptive artifact only).

## 7. Component: point-in-time rates & dividends (replaces scalar RISK_FREE_RATE)

**No scalar `RISK_FREE_RATE`.** A frozen function
`risk_free_rate(observation_date, expiration_date) → continuous rate`:

- **Tenor selection:** choose the Treasury constant-maturity tenor bracketing
  the option's calendar days to expiry.
- **Interpolation:** linear in time-to-maturity between the two bracketing
  tenors.
- **Compounding conversion:** convert the interpolated **par yield** to a
  continuous-compounded rate. The Treasury CMT curve is a **par-yield** curve;
  treating it as a zero-coupon curve is an **approximation, labeled as such**
  (Official-source: US Treasury CMT methodology).
- **Provenance (recorded with the data):** source URL, capture time (ISO),
  units, refresh/staleness rule, complete-universe coverage.

**Dividend yield `q`:** defined precisely as **expected annual cash dividend
known as of the observation date ÷ synchronized spot**, continuous-compounded. A
legitimate `q = 0` requires **sourced evidence** the name pays no dividend; a
missing `q` **blocks that name's BS computation** (fail-closed), never a silent
zero. **No retroactive application:** today's `r`/`q` are not applied backward;
either use point-in-time values, or label the recompute `synthetic` and
**exclude it from rank-quality conclusions**.

## 8. Component: earnings staleness fix on the *real* rendering path

The documented core-name silent-GREEN failure is **not** reachable by editing
`earnings_cycle.py` alone: core names take the curated-CSV branch
(`attractiveness_dashboard.py:975-980`) and `apply_cycle_badges` runs **only
when `earnings_source == "v3_store"`** (`:1072`). Fix options (choose one in the
plan):

1. **Route every live badge through the v3 point-in-time store** (core names too),
   retiring the curated-CSV badge path; or
2. **Add explicit per-symbol `checked_through` metadata to the curated CSV
   path**, and a fail-closed gate: if `checked_through < evaluation_date −
   STALENESS_LIMIT`, force the badge to `UNKNOWN`/`DATA_BLOCKED`
   (`earnings source stale`), making GREEN unreachable on stale data.

**`STALENESS_LIMIT` is owner-typed** (§15) — it gates a trade-facing GREEN. A
regression test reproduces the 2026-07-16 state (core CSVs stale past
2026-05-11, badges silently GREEN) and asserts non-GREEN after the fix.

## 9. Component: QM retrospective_result publication (mechanically valid)

The QM one-run-per-vintage study is **spent**; this arc does **not** rerun it or
recompute QM history. It:

1. **Defines and tests a new chained-ledger record type `retrospective_result`**
   in `research/ledger.py` — a **trial-counting** record for a result whose
   inputs already exist. A `trial_intent` here would be **semantically false**
   (intent implies pre-result), so it is not used.
2. **Publishes** the QM attempt-#2 record by referencing the existing artifacts
   by hash — **without invoking `qm_study`**: it pins `report_sha` (of
   `reports/2026-07-14-qm-base-rates.md`), `context_sha`, the **preregistration
   fact hash** (`QM_STUDY_PREREG`), and the **original report commit**
   (`14e754c…`; the context file already carries the report hash). Exact SHAs
   are computed at implementation time and written into the record.
3. Writes to the **chained** ledger (`experiments.jsonl` via `research/ledger.py`;
   `facts.log` is not tamper-evident, `ledger/README.md:13-27`), carrying the
   permanent labels **attempt #2 · outcome-selected · self-deceiving ·
   descriptive-only · no-verdict · cannot-promote**, and incrementing the
   QM trial count (now 2) for results-red-team.

## 10. Test A — feature-validation (not P&L)

Recompute BS + detector + term-structure features over the **deep parquet cache**
for VST/CEG/MSFT/AMZN ("backtest the 4" = computation validation on
**outcome-selected** names, not evidence) and **forward** on the watchlist. Assert
finiteness, in-range, stability. No P&L, no verdict, no reveal. Runs **after**
owner types study rules and after registration (§14).

## 11. Test B — rank-quality descriptive study (pre-registered, no verdict)

Does a name's attractiveness ranking co-move with subsequent realized/implied vol
behavior? Owner types null hypothesis + thresholds (§15). Permanent label: the
big 4 are outcome-selected — no correlation here is ever edge without a fresh
forward pre-registration. `synthetic` and `lookahead-contaminated` rows (§6, §7)
are excluded from evidence.

## 12. Component: dashboard surfacing

Surface detector tiers (INVALID_*/EXTREME/no_european_bs_root/NOT_ASSESSED) as a
data-quality dimension; the earnings-conditioned term-structure column
(descriptive); existing QM readings honestly (parabolic excluded from ordering);
and the QM attempt-#2 numbers walled off as non-verdict. Stale-source earnings
render DATA_BLOCKED, never GREEN.

## 13. Component: H10a and H10b — two separate ledger records

**Two separate `experiments.jsonl` records** (one record cannot count as two
attempts under the present schema), each incrementing the cumulative attempt
count independently. Both **forward-observation only after registration**;
signal selection is outcome-informed and permanently disclosed (§2). Verified by
`research.cli verify`.

If a lane measures **only stock returns**, state that explicitly and **remove the
option-loss fields**. Owner-typed blanks per lane (§15): structure; contract
selection; DTE; fills/costs; liquidity; sizing; concurrency; earnings treatment;
exit priority; receipt/book path; minimum sample; rejection threshold;
further-testing threshold; forward window.

## 14. Sequencing (reordered so no study value is revealed before rules are typed)

1. **Math + data infrastructure:** `black_scholes.py`; `risk_free_rate`/`q`
   functions with provenance; detector on enriched rows (legacy = NOT_ASSESSED);
   `retrospective_result` record type; the earnings staleness fix path.
2. **Synthetic tests only:** unit tests + regression tests on synthetic/known
   inputs (no study values revealed).
3. **Owner types all study rules** (§15): H10a, H10b, rank-quality, and
   `STALENESS_LIMIT`.
4. **Chained registration:** two H10 records + rank-quality prereg + QM
   `retrospective_result`; `research.cli verify` passes.
5. **Historical computation / reveal:** feature-validation recompute (§10) and
   rank-quality computation (§11) — only now are study values produced.
6. **Dashboard surfacing** (§12).

Steps 1–2 are agent work; step 3 blocks on the owner; 4–6 follow.

## 15. Owner-typed parameter tables (blanks — owner fills)

**`STALENESS_LIMIT`** = ____ (days; gates trade-facing GREEN).

**H10a — signal: ____  direction: ____  measures: [option P&L | stock return]**

| Field | Value (owner types) |
|---|---|
| Universe | ____ |
| Structure (e.g. long call / spread / stock) | ____ |
| Contract selection (strike/delta) | ____ |
| DTE | ____ |
| Fills / costs assumptions | ____ |
| Liquidity filter | ____ |
| Position sizing | ____ |
| Concurrency cap | ____ |
| Earnings treatment (hold/exit/skip) | ____ |
| Exit priority / rule | ____ |
| Receipt / book path | ____ |
| Minimum sample | ____ |
| Rejection threshold | ____ |
| Further-testing threshold | ____ |
| Forward window | ____ |
| Option-loss fields (omit if stock-return-only) | ____ |

**H10b** — same table, separate record.

**Rank-quality descriptive study**

| Field | Value (owner types) |
|---|---|
| Null hypothesis | ____ |
| Correlation metric | ____ |
| "Notable" threshold (descriptive only) | ____ |
| Feature-row exclusions | synthetic + lookahead-contaminated (fixed) |

Detector tolerances (`DELTA_EPS=0.02`, `NOARB_TOL=0.02` USD, EXTREME band
`[0.02, 5.0]`, convergence `1e-6` USD) are engineer-proposed conventions frozen
above with explicit values/units.

## 16. README & attempt-count discipline

The README currently states **four** live hypotheses (`README.md:183`). Do **not**
pre-write "five (or six)." Update to **six** only after **both** H10 records
verify. The cumulative ledger attempt count is a **separate concept computed from
the chain**, never asserted in prose.

## 17. Integrity summary

Fail-closed everywhere (missing input → NOT_ASSESSED/DATA_BLOCKED/UNKNOWN, never
fabricated or silently-GREEN); no look-ahead (point-in-time or labeled+excluded);
no verdict/P&L/OOS reveal; permanent records in the chained ledger; owner owns
every study threshold and the staleness limit; agent only drafts blanks and
freezes engineering conventions with explicit values.

## 18. Testing strategy

`unittest`, offline, local cache. New tests: BS math (vectors, parity as unit
invariant, finite-diff Greeks, IV round-trip, boundaries, theta sign); detector
(each tier incl. no_european_bs_root and NOT_ASSESSED; no false-flag on model
disagreement; American-bound equations); earnings staleness regression on the
**curated-CSV path** (reproduce 2026-07-16, assert non-GREEN); term-structure
point-in-time (assert lookahead exclusion + causal percentile window);
`retrospective_result` record type (trial-count increments, chain verifies);
feature-validation finiteness/stability. `ruff` + `pyright` clean.

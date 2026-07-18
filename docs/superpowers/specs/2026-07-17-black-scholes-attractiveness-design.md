# Black–Scholes descriptive layer for attractiveness + QM re-examination — design

**Date:** 2026-07-17
**Status:** DESIGN — pending owner review of this spec, then writing-plans.
**Author:** Claude Code (Opus 4.8), with owner (Carsyn) corrections folded in.

## 0. One-line intent

Add a real, tested Black–Scholes math unit and wire it into the attractiveness
layer **only as descriptive/data-quality features** (never a trigger); fix the
earnings silent-GREEN integrity hole; publish a properly-labeled QM "attempt #2"
record from the already-computed readings; and set up owner-typed forward
registrations (H10a/H10b) and a no-verdict rank-quality study. **No P&L
backtest, no OOS reveal, no verdict is produced by this arc.**

## 1. Plain-English primitives (shared vocabulary)

- **Black–Scholes (BS):** a *European*-option closed-form pricing model. It is a
  no-arbitrage quoting/interpolation convention, **not** an alpha model.
- **Greeks:** estimates of how an option's value reacts to underlying price
  (delta), the rate of that (gamma), time (theta), volatility (vega), and rates
  (rho).
- **Implied volatility (IV):** the volatility input that makes a model price
  equal a given market price. IV is the *market's* price inverted through BS,
  not a forecast BS discovers.

## 2. The single authority rule (resolves the earlier wording conflict)

> **The agent drafts every threshold as a blank in a table. The owner types all
> H10a/H10b and rank-quality-study values — entry/exit observation rules,
> rejection thresholds, further-testing thresholds — BEFORE any forward
> observation (or any historical number for those studies) is viewed. The agent
> never freezes a study threshold.**

This rule supersedes any other phrasing in this document. Math *conventions*
(§4) and sourced market *inputs* (§7) are not study thresholds: the agent
proposes conventions (owner approves this spec) and sources market inputs with
provenance. Only H10 and rank-quality *thresholds* are owner-typed.

## 3. Scope boundary

**IN (all descriptive / data-quality / integrity — no verdict, no reveal):**

1. `black_scholes.py` — tested pricing + Greeks + IV solver (math unit).
2. **Gross-error detector** — INVALID / EXTREME flags on vendor quotes+Greeks
   using American no-arbitrage bounds (§5). NOT a BS-vs-vendor model audit.
3. **Earnings-conditioned IV term-structure column** — descriptive study-
   selection input, point-in-time disciplined (§6).
4. **Surface existing QM readings** in the dashboard (already computed; no
   rerun) + publish the QM attempt-#2 record to the chained ledger (§9).
5. **Earnings-source staleness fail-closed gate** — fix the silent-GREEN hole
   (§8).
6. **Feature-validation** recompute (big-4 deep cache + watchlist forward) (§10).
7. **Rank-quality descriptive study** — pre-registered, owner-typed, no verdict
   (§11).
8. **Dashboard surfacing** of the above (§12).
9. **H10a / H10b** forward-paper registrations — owner-typed, no historical
   backtest (§13).

**PARKED → `ideas-parking-lot.md` (not built):**

- Any BS "fair value vs market price" *richness ranking* (VRP-in-disguise;
  research agent's harshest warning).
- Any generic (non-earnings-conditioned) term-structure/skew richness score.
- Any P&L backtest of any strategy on the big 4 (sealed-holdout violation).
- Any QM study rerun or fresh QM historical recomputation (§9).

## 4. Component: `options_researcher/black_scholes.py`

Pure, offline, no I/O. Functions: `d1`, `d2`, `bs_price`, `delta`, `gamma`,
`vega`, `theta`, `rho`, `implied_vol`.

**Frozen mathematical conventions (agent-proposed; owner approves via this spec):**

| Convention | Frozen choice |
|---|---|
| Rate / dividend compounding | continuous-compounded `r` and `q` |
| Day-count / time to expiry | ACT/365 Fixed: `t = calendar_days(chain_date→expiry) / 365` |
| Spot vs strike basis | **raw (unadjusted) spot against raw (unadjusted) strikes** — never split-adjusted spot vs raw strike |
| Price used for IV inversion | quote **midpoint** `(bid+ask)/2` |
| Price interval used by the detector | the **bid/ask interval** (not the midpoint) |
| Theta units | per **calendar day** (annual θ ÷ 365) |
| Vega units | per **1 percentage-point** (0.01) change in vol |
| Rho units | per **1 percentage-point** (0.01) change in rate |
| IV solver | Newton–Raphson seeded at 0.30, **bisection fallback** on bracket `[0.01, 5.0]` |
| Convergence tolerance | `|model_price − target| < 1e-6`, max 100 iterations |
| At/after expiry (`t ≤ 0`) | price = intrinsic; IV = `NaN` + `expired` flag |
| Zero volatility (`σ → 0`) | price = discounted intrinsic |
| Target price outside no-arb bounds | IV = `NaN` + `no_arb_violation` flag (do not return a fabricated root) |

**American-vs-European limitation (labeled Assumption):** BS is European; the
vendor (ThetaData) IV/Greeks use an American model. For dividend-paying ITM
contracts they diverge *systematically*. This unit is therefore used for (a) IV
inversion on near-ATM contracts where the gap is small, and (b) feeding the
detector's no-arb bounds — **never** to claim the vendor is "wrong" on a fine
model disagreement.

**Tests (unittest, offline):** textbook price vectors; European put–call parity
holds in the unit tests (this is a *unit-level* invariant, NOT applied to live
quotes — see §5); Greeks vs central finite-difference within tolerance;
IV round-trip (price → IV → price) recovers price; boundary behavior at `t≤0`,
`σ→0`, and out-of-bounds target price.

## 5. Component: gross-error detector

Purpose: catch **data glitches**, not model disagreement. Operates on the cached
chain rows (`bid, ask, iv, delta, gamma, vega, strike, expiration`), with
**matched strike/expiry** and **synchronized quotes** (same chain snapshot).

Two disjoint outcome tiers:

- **INVALID** (mathematically impossible / no-arbitrage-violating):
  - non-finite or negative IV;
  - crossed (`bid > ask`) or negative quotes;
  - delta outside its defensible range (calls `[0,1]`, puts `[-1,0]`, with a
    small bid/ask tolerance);
  - negative gamma or negative vega;
  - option price (bid/ask interval) outside **American** no-arbitrage bounds
    for the matched strike/expiry, with a bid/ask tolerance band.
- **EXTREME** (suspicious, not impossible): IV `≤ 0.02` or `≥ 5.0`, **after
  confirming the cache stores IV in decimal units** (e.g. `0.35`, not `35`).

**Never flag** ordinary BS-vs-vendor model disagreement. The European parity
equality from §4 is a unit-test invariant only; live-quote checks use American
no-arb bounds with tolerance. Detector output is a per-row flag consumed by the
feature store / dashboard as a data-quality dimension (feeds DATA_BLOCKED-style
display, never a GREEN action badge).

## 6. Component: earnings-conditioned IV term-structure column

Descriptive study-selection column. Measures near-tenor ATM IV vs longer-tenor
ATM IV (term-structure slope/level), **normalized to the name's own history**
(percentile or z-score), **interpreted only when a scheduled earnings report
sits in the near window**. Never a badge that can go GREEN into an action.

**Point-in-time discipline (non-negotiable):**

- **Live board:** earnings schedule known-as-of today → legitimate.
- **Historical deep-cache recompute:** at each past date, use only
  `assertions_view(assertions, known_as_of=<that past date>)` earnings evidence.
- **If point-in-time earnings evidence is unavailable for a historical date,**
  the column for that date is labeled `ex-post / lookahead-contaminated` and is
  **excluded from H10 and rank-quality evidence** (may be displayed as a
  descriptive artifact only).

## 7. Component: sourced rates & dividend yields

`RISK_FREE_RATE` and per-name dividend yields are **sourced market inputs**, not
judgment calls. Each requires, recorded alongside the value:

- source URL, capture time (ISO), units, refresh/staleness rule, and **complete
  universe coverage** (every name that gets a BS computation has a `q`).

**No retroactive application:** today's dividend yields are **not** applied
backward across the historical cache. Either (a) use point-in-time historical
`r`/`q`, or (b) label the recomputation `synthetic` and **exclude it from
rank-quality conclusions**. A missing `q` for any name blocks that name's BS
computation (fail-closed), it does not default to zero silently.

## 8. Component: earnings-source staleness fail-closed gate

Fixes the silent-GREEN hole in `earnings_cycle.py`. Before the GREEN branch
(`earnings_cycle.py:64-66`) can be reached, a **freshness gate** checks that the
earnings evidence store was refreshed recently enough (staleness threshold in
`config.py`, agent-proposed convention, owner approves) relative to the
evaluation date. If the source is stale, the badge is forced to `UNKNOWN` /
`DATA_BLOCKED` with reason `earnings source stale as of <date>` — **GREEN is
unreachable on stale data.** Ledger fact 2026-07-16 documented the exact failure
(core-name earnings CSVs stale past 2026-05-11, badges silently GREEN); a
regression test reproduces that state and asserts non-GREEN.

## 9. Component: QM attempt-#2 record (publish, do not rerun)

The QM one-run-per-vintage study is **spent**. This arc does **not** rerun the
study and does **not** perform fresh QM historical recomputation. It:

1. **Reads the already-computed, hash-bound QM readings** and **publishes** an
   "attempt #2" record.
2. Writes the permanent record to the **chained** ledger
   (`experiments.jsonl` via `research/ledger.py`), because `facts.log` is not
   tamper-evident (`ledger/README.md:13-27`). `facts.log` carries at most a
   pointer.
3. The record carries the permanent labels: **attempt #2 · outcome-selected ·
   self-deceiving · descriptive-only · no-verdict · cannot-promote**, and states
   the multiple-testing denominator (QM tries = 2) for results-red-team.

This is the honest reading of the owner's "historical backtest anyway" choice:
the owner sees the numbers, walled off from any verdict, with no new run.

## 10. Test A — feature-validation (not P&L)

- **"Backtest the big 4":** recompute all BS + detector + term-structure
  features over the **deep parquet cache** for VST/CEG/MSFT/AMZN; assert the
  features are finite, in-range, and stable. Names are **outcome-selected** —
  this is computation validation, not evidence of anything.
- **"Forward-test the rest":** compute the same features going forward on the
  thin-history watchlist names.
- No P&L, no verdict, no reveal.

## 11. Test B — rank-quality descriptive study (pre-registered, no verdict)

Pre-registered as a **no-verdict descriptive study**: does a name's
attractiveness ranking co-move with its subsequent realized/implied vol
behavior? Owner types the null hypothesis and correlation thresholds (§15). The
study carries a **permanent label**: the big 4 are outcome-selected, so no
correlation here can ever become evidence of edge without a fresh forward
pre-registration. Any `synthetic` / `lookahead-contaminated` feature rows (§6,
§7) are excluded from this study's evidence.

## 12. Component: dashboard surfacing

- Surface detector INVALID/EXTREME flags as a data-quality dimension.
- Surface the earnings-conditioned term-structure column (descriptive).
- Surface existing QM readings honestly (parabolic excluded from ordering, per
  current behavior); show the QM attempt-#2 numbers walled off as non-verdict.
- Ensure stale-source earnings render DATA_BLOCKED, never GREEN.

## 13. Component: H10a / H10b forward registrations (owner-typed)

Two **separately-judged** readings, **counted as two hypothesis attempts** even
if one registration record contains both lanes:

- **H10a** — (owner names the signal, e.g. QM parabolic long-continuation):
  direction, entry observation rule, exit observation rule, rejection threshold,
  further-testing threshold — **all owner-typed**.
- **H10b** — (owner names the signal, e.g. QM breakout continuation): same
  fields, **all owner-typed**.

Both are **forward-paper only** (no historical backtest, no peeking before
freeze). Registered to the **chained** ledger via `research/ledger.py`, verified
by `research.cli verify`. The README "four live hypotheses" statement
(`README.md:183`) is updated to five (or six) **only after** registration lands.

## 14. Sequencing (each unit test-green, then auto-commit per commit policy)

1. `black_scholes.py` + unit tests.
2. Gross-error detector + tests.
3. `RISK_FREE_RATE` + dividend-yield sourcing (provenance recorded).
4. **Earnings-source staleness gate** + regression test (item 5 / §8).
5. Earnings-conditioned term-structure column + point-in-time handling (§6).
6. Feature-validation recompute (big-4 deep + watchlist forward) (§10).
7. QM attempt-#2 record published to chained ledger (§9) — no rerun.
8. Dashboard surfacing (§12).
9. **Owner-typed tables** for H10a/H10b + rank-quality (§15) — blocks on owner.
10. Register H10a/H10b + rank-quality study after owner types values; update
    README.

Steps 1–8 are agent work with verification gates. Steps 9–10 block on the owner.

## 15. Owner-typed parameter tables (blanks — owner fills before any observation)

**H10a — signal: __________  direction: __________**

| Field | Value (owner types) |
|---|---|
| Universe | ____ |
| Entry observation rule | ____ |
| Exit observation rule | ____ |
| Max loss per trade / capital assumption | ____ |
| Rejection threshold (kills the idea) | ____ |
| Further-testing threshold (justifies more) | ____ |
| Forward window length | ____ |

**H10b — signal: __________  direction: __________** (same fields as H10a)

**Rank-quality descriptive study**

| Field | Value (owner types) |
|---|---|
| Null hypothesis | ____ |
| Correlation metric | ____ |
| Threshold for "notable" (descriptive only) | ____ |
| Feature-row exclusions | synthetic + lookahead-contaminated (fixed, §6/§7) |

**Math conventions (§4), staleness threshold (§8), and detector bands (§5)** are
agent-proposed and owner-approved via this spec — they are not study thresholds.

## 16. Error handling & integrity summary

- Every new feature is fail-closed: missing input → DATA_BLOCKED/UNKNOWN, never
  a fabricated or silently-GREEN value.
- No look-ahead: point-in-time earnings + rates/dividends, or labeled and
  excluded.
- No verdict, no P&L, no OOS reveal anywhere in this arc.
- Permanent research records go in the chained ledger; `facts.log` is advisory.
- Owner owns every study threshold; the agent only drafts blanks.

## 17. Testing strategy

`unittest`, offline, against the local parquet cache. New tests: BS math
(vectors, parity, finite-diff Greeks, IV round-trip, boundaries); detector
(INVALID/EXTREME classification, no false-flag on model disagreement); earnings
staleness regression (reproduce 2026-07-16 silent-GREEN, assert non-GREEN);
term-structure point-in-time (assert lookahead exclusion when evidence absent);
feature-validation finiteness/stability. `ruff` + `pyright` clean.

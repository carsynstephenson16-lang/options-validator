# §15 parameter proposals — H10a / H10b / rank-quality / STALENESS_LIMIT

**Date:** 2026-07-18
**Status:** PROPOSALS ONLY. Every value below is Claude-proposed with reasoning.
**Carsyn types the frozen numbers into the chained-ledger registration itself.**
Nothing here is frozen; this doc cannot register anything. It exists so you type
from reasoned starting points, not blank fields (Operating Manual rule #3).

Anchors (real `config.py` values, so proposals stay consistent):
RISK_SLEEVE $14,000 · MAX_LOSS_PER_TRADE $600 · MIN_LOSSES_FOR_VERDICT 10 ·
MIN_OPEN_INTEREST 100 · MAX_SPREAD_PCT 0.10 (H7 admission 0.05) ·
COMMISSION_PER_CONTRACT $0.65/leg/way · SLIPPAGE_HAIRCUT 0.01 ·
QM_TRADABILITY_DTE (30,60) · QM_NTM_BAND 0.10 · QM_HORIZONS (5,10,20) ·
H6/H8 DTE (45,90), H6 close-at-21DTE, H8 exit T-2, H6+H8 share a monthly cap.

---

## STALENESS_LIMIT (§8) — gates a trade-facing GREEN, so you type it

| Proposed | Reasoning |
|---|---|
| **35 calendar days** | The documented bug was a source stale ~66 days (past 2026-05-11, caught 2026-07-16) still emitting GREEN. Earnings cadence is quarterly (~90d; `EARNINGS_COVERAGE_DAYS`=98), so the limit must be well under a quarter to catch a newly-scheduled or revised report before it can hide in a window. 35d sits between the weekday refresh cadence and the 66d failure — ~2.5 refresh cycles per quarter, safe without false-blocking normal operation. **Trade-off:** tighter (e.g. 14d) = more UNKNOWN/DATA_BLOCKED false-closes but safer; looser (e.g. 60d) = closer to the failure that caused the bug. |

---

## H10a — QM **parabolic long-continuation** (measures: option P&L → keep option-loss fields)

| Field | Proposed value | Reasoning |
|---|---|---|
| Universe | H7_WATCHLIST names that pass **H7 admission at entry** (≥5 NTM monthly contracts, spread ≤5%, OI ≥100) | Reuse the existing admission gate; don't invent a universe. Re-measured at entry because margins are thin (IREN admits at exactly 5). |
| Signal / direction | QM parabolic fire (`parabolic_fires`, frozen params) → **long** continuation | The study's disclosed outcome-informed reading; permanently disclosed as such (§2). |
| Structure | Defined-risk **single long call**, economic max loss = premium paid | Continuation is directional-long; a long call caps loss at premium (no stop needed). Matches H6/H8 long-call shape and the long-lanes-only mandate. |
| Contract selection | Any listed call with **delta 0.40–0.60** within ±10% of spot (`QM_NTM_BAND`) | **Owner-set 2026-07-18:** a range, not a single strike — modestly-ITM to modestly-OTM; excludes far/cheap and deep/expensive. |
| DTE | **30–60** (`QM_TRADABILITY_DTE`) | Reuse the frozen QM tradability band; long enough to outlast theta over a 5–20 session move. |
| Fills / costs | mid-or-worse + `SLIPPAGE_HAIRCUT` + `COMMISSION_PER_CONTRACT` both legs each way | **Not a free choice** — `.cursorrules` guardrail. Listed so the registration records it explicitly. |
| Liquidity | both sides: OI ≥100 **and** spread ≤5% (H7 admission bar) | Reuse H7 admission; stricter than the 10% board bar. |
| Sizing | **1 contract**, premium ≤ **$600** (`MAX_LOSS_PER_TRADE` / `H9_PREMIUM_CAP`) | Keeps a single trade inside the per-trade cap; no discretion. |
| Concurrency | ≤ **$2,000/month** premium at risk across open H10a positions | Mirrors H6/H8 monthly discipline; consider whether H10 shares H6+H8's cap or gets its own (**your call** — affects total sleeve exposure). |
| Earnings treatment | **Skip entry** if a known report lands inside the option's life; source-health UNHEALTHY = per-name entry ban (v1.4 pattern) | Keeps H10 a *pure momentum* signal, uncontaminated by the H6/H8 earnings hypotheses. |
| Exit priority | (1) **+100% profit target**, else (2) **time-exit at 20 trading sessions** (QM max horizon), else (3) 21 DTE | Anchor the exit to the signal's own pre-declared forward window (5/10/20); don't hold past the horizon it was studied on. |
| Receipt / book path | forward paper receipt appended to the forward book (H6-0001 pattern), **no order path** | Paper-only; hook-enforced boundary. |
| Minimum sample | verdict gates at **≥7 losses**, not trades | **Owner-set 2026-07-18:** overrides the repo default `MIN_LOSSES_FOR_VERDICT`=10 for H10 only. Consequence disclosed: a 7-loss verdict is weaker/noisier than a 10-loss one. |
| Rejection threshold | at ≥7 losses, 90% bootstrap CI on after-cost expectancy/trade has **upper bound ≤ 0** | Mirrors the H1/H2 verdict framing ("consistent with zero edge"). |
| Further-testing threshold | at ≥7 losses, after-cost expectancy CI **lower bound > 0** | Only a strictly-positive CI justifies continuation. |
| Forward window | run until **≥10 losses OR 2026-10-06** (quarterly audit), then adjudicate | Loss-gated with a calendar backstop. |

---

## H10b — QM **breakout continuation** (separate ledger record; measures: option P&L)

Same table as H10a, with these deltas:

| Field | Proposed value | Reasoning |
|---|---|---|
| Signal / direction | QM **breakout** fire (`breakout_fires`: base 10–40d, depth ≤0.20, prior run ≥+30%, vol dry-up ≤0.65) → **long** | The breakout continuation setup. |
| Minimum sample | **≥7 losses** (owner override, as H10a) — but note only **11 historical fires** existed | Honest flag: even at 7, a forward window may take a **long time** to accrue losses; the verdict could stay `INSUFFICIENT_SAMPLE` well past 2027-01-06. |
| Forward window | run until ≥10 losses OR **2027-01-06**, then adjudicate | Longer backstop than H10a given the lower fire rate. |

All other fields (structure, selection, DTE, costs, liquidity, sizing,
concurrency, earnings, exit, receipt, thresholds) = **identical to H10a** unless
you change them. **This is a second, separate `experiments.jsonl` record and
counts as a second attempt** (cumulative QM attempts: study #1, retrospective #2,
H10a #3, H10b #4 — surfaced for results-red-team).

---

## Rank-quality descriptive study (§11) — no verdict, ever

| Field | Proposed value | Reasoning |
|---|---|---|
| Null hypothesis | attractiveness rank has **zero** rank-correlation with subsequent vol behavior (Spearman ρ = 0) | Descriptive; a null you can fail-to-reject honestly. |
| Correlation metric | **Spearman ρ** between a name's attractiveness GREEN-fraction and its **forward 21-trading-day realized vol** (and, separately, forward IV change) | Rank-based (robust to outliers); 21d matches `rv21`. |
| "Notable" threshold | flag \|ρ\| ≥ **0.30** as notable — **descriptive only, never a verdict** | Modest effect-size floor; purely a display flag. |
| Feature-row exclusions | `synthetic` + `lookahead-contaminated` rows excluded (fixed, §6/§7) | Non-negotiable; not your choice. |
| Permanent label | big 4 are outcome-selected → no ρ here is ever edge without a fresh forward pre-registration | Standing honesty label. |

---

## Two decisions — RESOLVED by owner 2026-07-18

1. **H10 gets its OWN monthly cap** (not shared with H6+H8). Consequence to keep
   visible: this adds up to a full separate month of at-risk premium on top of
   H6+H8, and because the whole book is one AI factor, that new premium
   concentrates rather than diversifies. The cap **dollar amount is still
   owner-typed** (proposed $2,000/mo).
2. **Register BOTH H10a and H10b.** Both become separate `experiments.jsonl`
   records and both count as attempts (cumulative QM: study #1, retrospective
   #2, H10a #3, H10b #4). H10b is accepted knowing it may sit
   `INSUFFICIENT_SAMPLE` for months given its low fire rate.

## Still blocking registration (owner-typed numbers + build work)

Registration cannot happen until BOTH:
- **You type the verdict/risk-gating numbers** (the short set below), and
- The **ledger path is built + tested**: the new `retrospective_result` record
  type (§9) and the `research/ledger.py` registration API — not yet written, and
  I will not fake it.

**Owner-set values — LOCKED 2026-07-18** (typed/confirmed by owner):
`STALENESS_LIMIT` = **35d** (+ cross-check H10-name earnings against the
equity-research book, as a confirmation source only) · H10 own monthly cap =
**$2,000/mo** · contract delta = **0.40–0.60** · DTE = **30–60** · minimum-losses
gate = **7** (H10 override of the repo default 10) · reject = CI upper ≤ 0 at ≥7
losses · further-testing = CI lower > 0 at ≥7 losses · H10a window end =
**2026-10-06** · H10b window end = **2027-01-06**. Cost model, liquidity gates,
and structure (long call) inherit from `config.py`.

**Still open before registration:** (1) rank-quality thresholds (Spearman,
|ρ|≥0.30, 21d) — low-stakes, no-verdict; confirm or amend. (2) the path to the
equity-research checkout for the earnings cross-check. (3) build + test the
`retrospective_result` type + `research/ledger.py` registration path.

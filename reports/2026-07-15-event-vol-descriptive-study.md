# Phase E1 — descriptive earnings-window option-behavior study

**Date:** 2026-07-15
**Phase:** E1 of the promoted event-edge signal
(`docs/superpowers/plans/2026-07-15-event-edge-phase-plan.md`; ledger fact
EVENT_EDGE_UNPARKED).
**What this is:** measurement only — implied vs realized earnings moves, ATM-IV
run-up and crush by tenor, contract price paths, spreads, and decay, from the
LOCAL cache. **Not a backtest**: no entry/exit rule was simulated, no P&L, no
win rate, no expectancy. Per the H6 registration, descriptive history is
context, never verdict.
**Reproduce:** `uv run python analysis/earnings_event_vol_study.py` (offline;
reads chain parquet caches + `data/earnings/assertions_v2.csv` occurred rows).
Executed 2026-07-15 by an Opus research subagent; numbers below are its
reported outputs (Repo-verified from cache unless labeled otherwise).

## Coverage

| Name | Covered events | Era split (pre/post 2023) | Notes |
|---|---|---|---|
| NVDA | 36 | 22 / 14 | full history |
| AMZN | 34 | 21 / 13 | full history, all AMC |
| PLTR | 23 | 9 / 14 | post-IPO (2020-11+); BMO→AMC switch mid-2023 |
| SMCI | 38 | 18 / 20 | 7 events skipped for missing chain windows (2019-05..2020-05), logged not interpolated |
| AMD / AVGO | 0 | — | no `status==occurred` earnings rows locally; AVGO chains start 2026-05-26 — excluded entirely |

Conventions (in the script header and the subagent methodology): T-1 = last
clean pre-report session (announcement date itself for AMC/unknown, prior
session for BMO); realized move = |close(T+1)/close(T-1) − 1|; implied move =
ATM straddle mid / spot at T-1 on the first post-event expiry (raw, not
de-biased — absolute levels are upward-biased vs a 1-σ expected move; compare
across names/tenors, not against 1.0); tenor buckets short = 14–30 DTE
(target 21) and long = 45–90 DTE (target 60), measured at observation date.

## Headline tables

**Implied vs realized move (medians per event set):**

| Name | Implied (straddle/spot) | Realized | Realized/implied (median) |
|---|---|---|---|
| NVDA | 6.9% | 4.5% | 0.60 |
| AMZN | 6.1% | 5.5% | 0.80 |
| PLTR | 13.7% | 12.0% | 0.86 |
| SMCI | 12.6% | 10.8% | 0.95 |

**IV run-up (T-15→T-1) and crush (T-1→T+1) by tenor (mean ATM IV):**

| Name | Bucket | T-15 | T-1 | T+1 | Run-up | Crush | Crush % of T-1 |
|---|---|---|---|---|---|---|---|
| NVDA | 14–30d | 56.0% | 56.0% | 44.8% | ~0 | −11.1 pts | 19.9% |
| NVDA | 45–90d | 48.6% | 48.3% | 43.8% | −0.3 | −4.5 pts | 9.3% |
| AMZN | 14–30d | 41.0% | 44.1% | 31.1% | +3.1 | −13.0 pts | 29.5% |
| AMZN | 45–90d | 34.5% | 36.4% | 30.6% | +1.9 | −5.8 pts | 15.8% |
| PLTR | 14–30d | 70.6% | 92.6% | 64.2% | +22.0 | −28.4 pts | 30.7% |
| PLTR | 45–90d | 66.9% | 73.6% | 62.5% | +6.8 | −11.1 pts | 15.1% |
| SMCI | 14–30d | 79.1% | 88.7% | 76.5% | +9.6 | −12.2 pts | 13.8% |
| SMCI | 45–90d | 75.3% | 74.6% | 71.6% | −0.7 | −3.0 pts | 4.0% |

Short-tenor crush exceeds long-tenor crush in **every** name: ~2.2× (AMZN),
~2.5× (NVDA), ~2.6× (PLTR), ~4.1× (SMCI) in absolute IV points.

**Costs (median half-spread % of mid, ~0.50-delta call, T-15..T-1):**
NVDA 1.3%/1.0%, AMZN 1.8%/1.1%, PLTR 2.0%/1.2%, SMCI 3.8%/3.7%
(short/long). Long tenor is the cheaper bucket in all three mega-caps.

**Decay context (CONFOUNDED by spot drift — net mid change, not clean
theta):** where drift was small, the short bucket bled faster (SMCI −7.6%/day
short vs −2.8% long; AMZN −0.8% vs −0.6%); in strong uptrends the sign flips
positive for both buckets (NVDA, PLTR).

**Structural finding from the contract traces:** the 14–30 DTE comparison
contract **routinely expires before T+3** — a short-dated pre-earnings hold
often has no schedule margin if a report slips or an exit is delayed. The
45–90 DTE contract survives the whole window in every trace. Also, the
long-dated call's T-15→T-1 mid is driven by spot drift at least as much as by
IV — PLTR 2026-02-02: the selected call went $12.62 → $2.52 *before* the
report as spot fell away.

## Implications (every sentence Inference; no edge claim)

1. A pre-earnings-entry / exit-before-report design never *harvests* crush
   avoidance directly — but tenor choice sets the penalty for a missed or
   partial exit: 2–4× smaller at 45–90 DTE than at 14–30 DTE.
2. The 45–90 DTE tenor is the mechanically cheaper multi-week hold (lower
   half-spread %, slower decay where drift is controlled) and the only one
   with schedule margin around the event.
3. The harvestable IV run-up is strongly name-dependent: large for PLTR,
   moderate for SMCI/AMZN, ≈0 for NVDA (chronically elevated surface). Any
   design that keys on run-up needs per-name evidence, not a universal rule.
4. Front-expiry options were richly priced into these events on median
   (realized/implied 0.60–0.95 on raw straddle/spot) — context that cuts
   *against* buying short-dated event vol, but this is not de-biased and not
   net of costs, so it is context only.
5. Directional spot exposure — not vol — is the dominant risk a 45–90 DTE
   pre-earnings long call carries. The design's real bet is drift into the
   report, with the exit-before-report rule capping the vol side.

Data gaps skipped and logged: 7 SMCI event windows; AMD/AVGO entirely (no
local historical occurred dates). Nothing interpolated.

**What may act on this:** nothing, until a hypothesis is pre-registered with
owner-typed numbers — see the paired proposal
`docs/superpowers/specs/2026-07-15-pre-post-earnings-plan.md`. Phase E2
(any grading/gating) remains closed.

# Daily-NAV drawdown — durable build spec (NOT REGISTERED, NOT SCHEDULED)

**Status:** PARKED with a design. Owner-directed 2026-07-30: *"I want to do
option 3 but I need the daily NAV curve build to be stored somewhere so I can
revisit it later."*
**This document is that store.** Nothing here is registered, no number here is
frozen, and no session is scheduled against it.

**Companion:** [`reports/strategy-evaluations/12_review_of_the_two_landed_commits.md`](../../../reports/strategy-evaluations/12_review_of_the_two_landed_commits.md) §F5.

---

## 1. The limitation, in plain English

Drawdown means "the worst drop from a high point." Today the project measures it
by lining up finished trades and running a total. It never looks at what the
account was worth on any given day while trades were still open.

So a spread that goes badly against you for three weeks and then recovers to
close for a small profit is recorded as: *small profit, no drawdown.* Your
actual account statement would have shown an ugly number for three weeks.

A day-by-day account value — a NAV curve (NAV = net asset value = what the whole
account is worth right now, with open positions valued at current prices) — is
the only thing that catches that. It is also the only version that answers the
question that actually matters: **would I have panicked and quit?**

---

## 2. Closed-trade ordering is fixed; daily marks remain absent

### Closed defect A — trade ordering

Commit `5626c3f` made `closed_trade_pnl_drawdown` zero-anchored and stably
ordered by `entry_date`. A shuffle-invariance regression now pins that
definition. H9's receipt had supplied an alphabetically ordered trade list,
which explains the obsolete stored value below.

Measured consequence on the H9 record:

| Ordering | Drawdown |
|---|---:|
| As recorded — alphabetical, no zero start | $361.30 |
| Alphabetical, zero-anchored (post-`88ffbb6`) | $482.30 |
| **Chronological by entry date** | **$718.50** |
| Chronological by exit date | $572.20 |

The recorded figure reproduces exactly under the alphabetical ordering and no
other, which establishes the cause.

**Implemented convention:** entry-date order, retained under the explicit name
`closed_trade_pnl_drawdown`. It is a completed-trade path statistic, not daily
NAV. The append-only `METRIC_CORRECTION` fact records $718.50 for H9 under this
definition and preserves $572.20 as the distinct exit-session aggregation.

### Defect B — no daily marks at all (this spec)

Even perfectly ordered, closed-trade drawdown is blind to the middle of a trade.

---

## 3. Why the daily-NAV build is not a small job

The ingredients exist and are **thrown away twice**:

1. `strategies/put_credit_spread.py:_spread_mark` computes an honest
   conservative daily mark for every open spread, and uses it only to decide
   exits. It is never stored.
2. `harness/run_backtest.py` discards Lumibot's own result object, which
   carries per-iteration portfolio value.

The genuine obstacle is structural, not plumbing:

> **The harness runs one backtest per symbol, per calendar year, with capital
> reset each time** (`harness/run_backtest.py`, `_chunks`). There is no single
> account and therefore no single equity curve to draw. Chunking was adopted for
> memory reasons — one 5-year, 9-symbol feed would need ~10⁵ per-contract `Data`
> objects — and the module states that chunking must not change *what* is
> traded.

So a NAV curve requires stitching per-symbol-per-year runs into one notional
account. That stitch is where all the difficulty lives.

---

## 4. Design sketch (for whoever picks this up)

**Step 1 — record the marks.** In `_spread_mark`, append
`(session_date, symbol, mark, contracts, unrealised_pnl)` to a per-run list.
Purely additive; no behaviour change; no registered value touched. This is the
cheap half and could ship independently — even unstitched marks are a strictly
better diagnostic than nothing.

**Step 2 — decide the stitching convention.** This is the real decision and it
is an owner call, because it defines what "the account" means:

| Option | What it says | Cost |
|---|---|---|
| **Per-symbol-per-year curves, report the worst** | "No single symbol-year ever drew down more than X." Honest, requires no stitching, understates portfolio drawdown because it cannot see two symbols losing together. | Cheapest. Available immediately after step 1. |
| **Sum daily unrealised P&L across all concurrent chunks into one notional curve** | "If all these ran in one account, the curve looked like this." Closest to the real question. | Needs a shared calendar across chunks and a decision on what happens at year boundaries where capital resets. |
| **Re-architect the harness to one continuous account** | Genuinely correct. | Contradicts the memory constraint chunking exists to solve. Probably not worth it. |

**Step 3 — report it under a name that cannot be confused with the closed-trade
figure.** Both numbers should be reported side by side, never one replacing the
other.

**Step 4 — the test that matters.** A fixture with a position that goes deep
against the account and recovers to a small profit must produce a *large*
NAV drawdown and a *near-zero* closed-trade drawdown. If both numbers come out
similar, the build is not doing its job.

---

## 5. Known limits this build will *not* remove

- **Marks are end-of-day only.** The cache stores one snapshot per contract per
  day. Intraday lows are invisible, so even a correct NAV curve understates the
  worst moment. Fixing that needs intraday data the account is not entitled to
  (see report 12 §4).
- **Date-only capital metrics.** `_date_based_capital_metrics`
  ([`metrics.py:279-315`](../../../metrics.py#L279-L315)) counts inclusive
  calendar dates and has no intraday timestamps. If trade A closes and trade B
  opens the same day, both are counted as tying up capital that day, even though
  A's money was free before B needed it. This **overstates** capital used, which
  **understates** returns — an error in the safe direction, and one no amount of
  cleverness removes without timestamps the cache does not store. It is
  documented, not fixable at the current schema.

---

## 6. Trigger to revisit

Any of:

- A hypothesis is registered whose decision rule depends on drawdown tolerance
  rather than expectancy.
- Cache schema v2 lands (Session 5), which would make timestamps available and
  retire the inclusive-date approximation.
- A forward paper window accumulates enough open-position history that the
  closed-trade figure becomes visibly misleading.

Until one of those fires, the honest position is: **drawdown in this repo is
closed-trade P&L based, and it is labelled as such.**

# Attractiveness expiration ladder + transparent ranking — design

**Date:** 2026-07-09
**Status:** approved design, pending spec review
**Scope class:** in-scope tooling change to the H5 scanner surface. NOT a new
hypothesis (no ledger trial). NOT the parked "ranked trade suggestor"
(`ideas-parking-lot.md`): ranking is a single visible quantity per structure,
not a composite recommender.

## Problem

Every attractiveness card is built off ONE expiration. `_monthly_rows()`
(`options_researcher/attractiveness.py:35`) calls
`chains.nearest_monthly(chain, today)` — the earliest monthly in a 15–60 DTE
window — so the surface only ever shows the single nearest monthly (~46 DTE
today). The owner wants to see several tenors and have the current spot decide
which is most attractive.

## Requirements

1. Show a ladder of expirations per name at ~2 weeks / 1 / 2 / 3 / 4 months.
2. Pick the nearest available expiration to each target **within a per-bucket
   window** (weeklies are now eligible for the 2-week bucket).
3. Rank candidates by ONE transparent, config-visible quantity per structure,
   best-first, and mark the leader (★). No composite/hidden score.
4. Ranking is spot-based (uses today's underlying price).

## Frozen parameters (owner-entered 2026-07-09)

### Ladder buckets — `config.A_LADDER_BUCKETS`

Per-bucket accept windows, NOT a flat tolerance. Rationale: a flat ±10 on the
14-day bucket would admit a ~4-DTE option (gamma-dominated, a different
instrument). Windows are disjoint, so each expiration maps to at most one
bucket; upper tolerance widens with tenor because monthlies thin to ~30-day
spacing far out.

| Bucket (label) | Target DTE | Accept window (DTE) |
|---|---|---|
| 2 weeks | 14  | 10–21   |
| 1 month | 30  | 24–38   |
| 2 months| 60  | 50–75   |
| 3 months| 90  | 76–105  |
| 4 months| 120 | 106–140 |

Representation: `A_LADDER_BUCKETS = ((14, 10, 21), (30, 24, 38), (60, 50, 75),
(90, 76, 105), (120, 106, 140))` — tuples of `(target, lo, hi)`.

Selection rule: within each bucket's window, choose the expiration whose DTE is
nearest the target. If no expiration falls in the window, **skip that bucket and
log it** (never widen the window to fill it). Disjoint windows make dedup
unnecessary, but if a future config overlaps them, keep the first (shorter)
bucket's claim.

### Ranking metrics (ordering only — add NO new grade thresholds)

- **Credit structures** (sell put, covered call, PMCC): **annualized yield on
  capital tied up** = `(credit / capital) * (365 / dte)`, higher = better.
  `capital` is the existing per-structure base (100·strike for a put/CC;
  `leaps_cost` for PMCC). This replaces the current "%/mo" label, which is
  misleading across mixed DTEs. Cards still show cushion, dollar credit, and
  liquidity unchanged.
- **Long call** (tactical buy lane): **required breakeven move** =
  `breakeven / close - 1`, lower = better. Rejected cost-per-delta as the
  primary metric: for equal current delta a short-dated call is cheaper on
  premium, so cost-per-delta systematically favors short-dated lottery tickets.
  Breakeven-move answers the analyst's question — how far must the stock move
  for this to work. **Cost per delta** = `cost / (100 * delta)` is shown as a
  SECONDARY number so the leverage trade-off stays visible. The guardrail that
  keeps breakeven-move from collapsing to trivially-winning deep-ITM calls is
  the existing delta-band filter (`long_call_card_rows` already restricts to
  `|delta − H4_TACTICAL_DELTA| <= DELTA_BAND`, attractiveness.py:269).

## What changes

### `config.py`
- Add `A_LADDER_BUCKETS` (above). No new thresholds.

### `options_researcher/chains.py`
- Add `ladder_expirations(chain, today) -> list[tuple[int, date]]`: for each
  `(target, lo, hi)` in `A_LADDER_BUCKETS`, return `(target, nearest_exp)` for
  the available expiration nearest `target` inside `[lo, hi]`; omit buckets with
  no match. Weekly and monthly expirations both eligible (drop the
  `is_monthly` restriction for this path). `nearest_monthly` is untouched;
  other callers keep using it.

### `options_researcher/attractiveness.py`
- Generalize `_monthly_rows(chain, day, right)` → `_expiry_rows(chain, day,
  right, exp)` taking an explicit expiration. Keep behavior identical for a
  single expiration.
- The four ladder-eligible builders (`put_card_rows`, `cc_card_rows`,
  `pmcc_card_rows`, `long_call_card_rows`) loop `ladder_expirations`, emit **one
  representative candidate per bucket** (the strike nearest the lane's target
  delta), then attach the structure's ranking metric, sort best-first, and set
  `rank_leader=True` on the top row. `leaps_card_rows` is unchanged (its own
  270–500 DTE tenor; the ladder does not apply).
  - Open decision for spec review: one candidate per bucket (5 rows, cleanest
    ladder) vs the current up-to-`N_CANDIDATES` strikes per bucket. Default:
    one per bucket.
- Add `annualized_yield` (credit lanes) and `breakeven_move` +
  `cost_per_delta` (long-call lane) to the emitted dicts. Update verdict text
  from "%/mo" to annualized where the metric changed.
- Frozen-cost and liquidity handling is reused verbatim (SLIPPAGE_HAIRCUT,
  COMMISSION_PER_CONTRACT, `passes_liquidity`); thin weeklies fail the gate and
  are dropped exactly as today. No new fill/cost logic.

### `options_researcher/attractiveness_dashboard.py`
- Render every ladder bucket per name, sorted, ★ on the leader; replace the
  single "N days out" line with the ladder. Payoff math already uses spot and
  per-card DTE, so no change there.

### Tests (`tests/`)
- `ladder_expirations`: nearest-to-target within window; bucket skipped when the
  window is empty (and logged); disjoint-window assignment; weekly eligibility.
- Ranking: annualized-yield ordering for a credit lane; breakeven-move ordering
  (and that a cheap short-dated OTM call does NOT outrank a nearer-breakeven
  call); leader flag set on exactly one row.
- Existing single-expiration card tests keep passing (via `_expiry_rows`).

### Ledger / notes
- One line in `ledger/facts.log`: scanner gained a 5-bucket expiration ladder +
  transparent per-structure sort (tooling; no hypothesis change). H5/H6
  registrations and entry triggers untouched.

## Non-goals

- No composite attractiveness score, no "recommendation" verdict, no sizing, no
  tracking, no order placement.
- No change to LEAPS tenor, frozen costs, liquidity gates, or any H5/H6
  threshold.
- No term-structure IV signal (that stays parked and separately
  pre-registered).

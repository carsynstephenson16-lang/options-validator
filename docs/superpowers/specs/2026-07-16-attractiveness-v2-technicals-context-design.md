# Attractiveness dashboard v2 — technicals, market context, Top 3 picks

**Date:** 2026-07-16 · **Status:** owner-approved in session (all-lanes Top 3;
agent-research-per-run with dated JSON) · **Owner authorization:** this makes
the descriptive scanner more suggestor-shaped; owner explicitly requested it
2026-07-16. Read-only research; no orders; vocabulary discipline applies.

## Problem

The attractiveness pipeline today uses ONLY: delta targeting, IV-rank,
IV-minus-RV, yield/cushion from rv21, earnings/FOMC windows, liquidity.
No moving averages, no price action, no breakout context, no news/market
layer, and the HTML is a long vertical stack that is hard to compare.

## Design

### 1. `options_researcher/technicals.py` (offline, deterministic)

`technical_snapshot(closes: pd.Series) -> dict` computed from the cached
underlying closes (no network; unit-tested on synthetic series):

- `sma20, sma50, sma200` and `px_vs_sma20/50/200` (pct distance)
- `ma_posture`: `above_all | mixed | below_all`
- `breakout_20d`: close ≥ prior 20-day high (bool); `hh_20d` the level
- `dist_52w_high` (pct below 52-week high), `mom_1m`, `mom_3m`
- `trend`: `up | down | sideways` from SMA20 vs SMA50 vs SMA200 ordering

All windows/thresholds live in `config.py` (`TECH_*`), labeled LLM-asserted
proposals (presentation-layer only — NOT strategy gates; H5/H6/H7 frozen
numbers untouched).

### 2. Deterministic bull/base/bear rows on EVERY card (offline)

Per card, at-expiration scenarios from existing payoff functions at three
price points scaled by rv21 monthly move and DTE:
bear = close·(1 − k·move), base = close (flat), bull = close·(1 + k·move),
k = sqrt(dte/30) capped at 2 monthly moves. Pure arithmetic; labeled
"scenario framing, not a forecast."

### 3. Agent research layer (per run, dated JSON, never baked into Python)

Each dashboard build, subagents (web search) write
`reports/attractiveness_context/YYYY-MM-DD.json`:

```json
{
  "as_of": "YYYY-MM-DD",
  "provenance": "LLM-asserted (Claude subagents, web research YYYY-MM-DD)",
  "market": {"summary": "...", "regime": "risk_on|risk_off|mixed",
              "notes": ["..."]},
  "symbols": {"MSFT": {"news_summary": "...", "sentiment": "bull|bear|neutral",
               "catalysts": [{"date": "YYYY-MM-DD|null", "what": "...",
                               "source": "url"}],
               "move_thesis": "...", "sources": ["url"]}},
  "top_picks": [{"symbol": "", "lane": "put|cc|pmcc|leaps|long_call",
                  "strike": 0, "expiry": "YYYY-MM-DD",
                  "why_now": "", "hypothesis": "", "thesis": "",
                  "bull": "", "base": "", "bear": "", "logic": ""}]
}
```

Dashboard loads the file matching its data as-of date (fallback: newest ≤
as-of, with a stale warning); missing file renders an honest "no research
context for this date" banner — never invented. Every rendered narrative
carries the LLM-asserted provenance label. tests stay offline: renderer
tested with injected JSON fixtures.

### 4. Top 3 picks (all lanes, all universe names — owner choice)

Transparent two-stage:
1. Python shortlist: per-lane `rank_leader`s across all names, scored by
   `pick_score` = GREEN badge count − heavy liquidity-RED penalty + technical
   confluence bonus (weights in `config.py`, LLM-asserted, presentation-only).
2. Research agents write the final Top 3 narratives (why_now / hypothesis /
   thesis / bull/base/bear / logic) for the highest-scored picks into
   `top_picks`. If agent picks diverge from the Python shortlist order, the
   JSON says so and the dashboard shows both.

### 5. Layout redesign

- Sticky as-of banner (kept) → **TOP 3 PICKS TODAY** hero cards (full
  narrative note each) → market context strip → per-symbol sections with a
  **responsive side-by-side card grid** (CSS grid, `minmax(320px, 1fr)`).
- Each card: headline, key numbers, technicals strip (MA posture · breakout ·
  momentum), grade badges, deterministic bull/base/bear mini-table, symbol
  news blurb, payoff ladder collapsed inside native `<details>`.
- No JS framework; self-contained HTML as before.

## Not doing

- No changes to frozen H5/H6/H7 gates, entry triggers, or verdict logic.
- No live quotes, no orders, no network in the Python layer or tests.
- No parameter optimizer; pick_score is presentation ordering only.

## Testing

- `technicals.py`: synthetic-series unit tests (flat, uptrend, breakout,
  below-all-MA cases).
- Dashboard: assemble/render tests with injected sections + injected context
  JSON (present, missing, stale); Top-3 selection test with fixed cards.
- Full suite must stay green offline.

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

### 3. Agent research layer (ON-DEMAND, dated JSON, never baked into Python)

*Amended 2026-07-16 (14-name expansion session):* research is ON-DEMAND,
not per-build. The daily 07:10 ritual rebuilds the deterministic board with
no LLM in the loop; agent research runs only when the owner asks for it,
covers only the symbols on the board (Top-3 + pinned), and its schema
protects ranking membership — NOT factual truth. `top3_context` validation
cannot verify that a URL labeled issuer_ir actually belongs to the issuer or
that a claim is true; provenance labels stay mandatory for that reason.

When research does run, subagents (web search) write
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

*Amended 2026-07-25 (owner-directed): scheduled research refresh.* The
owner directed in-session on 2026-07-25 ("make it not be stale on monday
i want it to run llm research … i dont want to have to ask for a
refresh") that §3's "agent research runs only when the owner asks for
it" is replaced by a standing schedule. Cadence: Mon–Fri 07:40 ET
(post-ritual premarket) and 16:45 ET (post-close), plus Sat 09:00 ET (a
weekend catch-up that also converges chain/feature freshness), via
LaunchAgent `com.carsyn.options-validator.research-refresh` running
`tools/research_refresh.sh`. Each run first converges data freshness
(topup → attractiveness features → QM OHLCV — all no-ops when current),
then runs a headless Sonnet session (skill `research-refresh`) that
produces `reports/attractiveness_context/<data-as-of>.json` through the
unchanged `top3_context` validation, then rebuilds the dashboard and
verifies the stale-research banners are gone. Unchanged invariants: the
research layer stays advisory-only and LLM-asserted-labeled; it cannot
add, remove, or reorder candidates; the deterministic 07:10 ritual is
untouched; a failed refresh degrades to the board's honest stale
banners, never to invented content. Controls: kill-switch file
`.research-refresh-off` at the repo root; per-run dollar cap via
`claude --max-budget-usd`; no runtime auto-commit (context files are
committed by humans/sessions, avoiding unattended commits on whatever
branch the checkout has). Provenance: owner-directed 2026-07-25,
recorded by the implementing agent; veto or change by further
append-only amendment.

*Hardening amendment 2026-07-27 (implementation safety correction).* The
research refresh is a consumer of the daily ritual, not a second data
producer. It no longer runs topups, feature builders, or QM refreshes. Before
any LLM invocation it must read an explicitly configured authoritative ritual
checkout and prove that `capture_receipt_<data-as-of>.json` has the exact
market session, the current `America/New_York` run date, successful
`CAPTURED|NO_SIGNAL` statuses for H5/H6/H7/H8/H10, and readable evidence for
each status. Those statuses are necessary but not sufficient: the checkout
must also expose `run_status_<data-as-of>.json` with schema
`daily_ritual/run_status/v1`, global status `OK`, a full ritual code SHA, and a
binding to the exact capture-receipt path and SHA. A later broken rerun replaces
the mutable latest status and therefore blocks research. Any failure returns
`UPSTREAM_BLOCKED` before research spend.

Successful research uses the `attractiveness_research/v2` contract. The
producer copies and hashes every source packet, records the exact deterministic
candidate IDs, pinned symbols, UTC and ET generation timestamps, producer
commit/source hashes, and ritual receipt/evidence hashes. It deterministically
renders `reports/<market-as-of>-attractiveness-research-context.md` from the
machine JSON and publishes the manifest last as the commit marker. Verification
fails closed on byte drift, missing candidate or required-symbol coverage,
temporal mismatch, source-link mismatch, or a missing/confirmed/non-PJM
`PJM_BRA_NEXT` entry for either VST or CEG. Critic freshness is the immutable
`run_id` plus context SHA-256 pair, never filesystem mtime. This amendment does
not authorize enabling or changing a LaunchAgent.

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

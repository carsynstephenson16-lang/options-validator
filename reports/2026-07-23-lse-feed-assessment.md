# LSE feed assessment — test_lse_feed.py (2026-07-23)

**Verdict: PARKED, not adopted.** Measured against this repo's guardrails, the
feed cannot serve as a ThetaData backup or an index-chain source as-is.

## What it actually is (Repo-verified + Official-source, accessed 2026-07-23)

- `test_lse_feed.py` is a 29-line read-only smoke test of the `lse-data`
  v0.14.0 PyPI package by **"London Strategic Edge"**
  (londonstrategicedge.com) — **NOT LSEG / London Stock Exchange Group**; the
  name collision is a real confusion risk. The package lives in an ad hoc
  `lse_env/` venv (2026-07-22), not in the project's uv environment, and
  `.env` already labels the key "unverified vendor, test script only."
- One controlled probe ran (single HTTPS call, no repo changes): 323 AAPL
  call rows returned.

## Why it fails the core use (measured, not assumed)

1. **No bid, no ask, no open interest** in the options-chain payload — only
   `last_price` plus vendor-modeled IV/greeks. The repo's non-negotiables
   (fills at mid-or-worse, MIN_OPEN_INTEREST and MAX_SPREAD_PCT on both legs)
   are unsatisfiable from this payload.
2. **No point-in-time chain history** — only a "live" current chain, trailing
   trade prints, and per-contract minute candles; no historical snapshot
   endpoint, so no look-ahead-free backtest reconstruction.
3. **Reproducible staleness red flag:** the probe requested 7–30 DTE and
   received expiries of 2026-07-02 and 2026-07-06 — already expired — from a
   claimed continuously-refreshed endpoint (possibly a demo-tier artifact;
   the client exposes an account tier property).

## The narrow residual use, if any

The vendor's streaming stock tick feed does carry bid/ask — a conceivable
spot-quote input for the live-dashboard PREVIEW lane, or `options_flow()` as
qualitative unusual-activity color. Neither is verdict-bearing under this
repo's rules, and both would require the existing `--probe`-before-live-lane
discipline plus resolution of the stale-date anomaly.

## Un-park gate (owner)

(1) Re-run the stale-date check on another session; (2) confirm with the
vendor whether bid/ask/OI and true point-in-time chains exist on any tier;
(3) if pursued, scope strictly to spot-quote/flow color, never chain or
backtest data, with key handling promoted into `.env.example` only after
verification. Until then: parked; ThetaData extension remains the live
data-continuity decision (~2026-10-01).

# Underlying closes/OHLCV source decision — 2026-08-04

**Question (owner-directed in-session):** now that ThetaData is gone, is the
Schwab API — or any other source — a better provider of daily underlying
closes/OHLCV than the Yahoo chart endpoint the repo currently uses?

**Decision: Yahoo stays primary. Schwab is NOT adopted for this lane.**

Scope note: this is about UNDERLYING STOCK daily closes/OHLCV only. It does
not change the options-chain situation — chains remain frozen at 2026-07-27
(OD-4), and no source evaluated here replaces dated historical chains.

## Why Schwab loses despite better nominal data quality

Schwab's `/marketdata/v1/pricehistory` is real, documented, and generous on
rate limits (120 req/min). It fails on operations, not data:

1. **7-day hard refresh-token expiry** (Official-source: Schwab developer
   docs; corroborated by schwab-py auth docs, retrieved 2026-08-04). Access
   tokens last 30 minutes; the refresh token cannot be extended server-side.
   An unattended daily LaunchAgent that sleeps between runs dies every week
   and needs an interactive browser OAuth re-login. Making it work requires
   building and maintaining an always-on refresher process — real ongoing
   burden for a research validator that fetches once a day.
2. **Entitlement instability already observed in this repo.** The live-quote
   lane recorded `stock_entitled: false` on 2026-07-24 and `true` on
   2026-07-29 (`reports/live_probe/2026-07-24.json`,
   `reports/live_probe/2026-07-29.json`). An input that can silently flip
   entitlement is a poor foundation for a daily gate.
3. **No credentials on disk for it anyway** — Schwab auth lives in the macOS
   Keychain and the six `SCHWAB_*` keys are absent from `.env`.

## Why Yahoo holds

- **Validated level-exact**: `ledger/facts.log` `UNDERLYING_CLOSES_YAHOO`
  (2026-07-04) — max |diff| = $0.0000 vs ThetaData true closes across four
  names, n=41 each.
- **Zero credentials, zero token maintenance** — the decisive property for an
  unattended job.
- The repo already handles its two known quirks: raw-strike alignment via the
  `SPLITS` back-multiply in `data/underlying_closes.py`, and the same-day
  partial-print guard (`drop_same_day_rows`).

**Honest weaknesses of the incumbent (recorded, not hidden):** the Yahoo chart
endpoint is undocumented/unofficial — Yahoo can change or rate-limit it at any
time, and the repo has already hit a 429 once (`facts.log`, 2026-07-06). There
is no formal ToS permitting automated retrieval.

## If Yahoo degrades, the next step is NOT Schwab

Preferred backups, both static-key (no OAuth refresh burden), both with a
formal ToS: **Tiingo** (~300 req/day free) and **Polygon/Massive** (5 req/min,
EOD, one call covers a whole date range — efficient for ~25 symbols).
Alpha Vantage remains available as a cross-check (key present;
`fetch_underlying_eod_av` already implemented) but its full daily history is
paywalled and it needs pacing. Stooq was already ruled out (blocks
programmatic access, `facts.log` 2026-07-06).

## Executed under this decision (2026-08-04)

Owner-authorized refresh: 25/25 closes and 20/20 OHLCV symbol stores
refreshed via Yahoo, all now current through **2026-08-03** (Monday's close;
the same-day guard correctly excludes the in-progress 08-04 session).
Attractiveness features rebuilt at the chain edge (2026-07-27 — features need
an exact-session chain), both dashboards and the composite signal board
rebuilt. Composite cards now stamp max as-of 2026-08-03; chain-derived values
(IV, spreads, open interest) remain honestly stamped 2026-07-27 and will stay
there until the provider decision is made.

Provenance: source comparison is LLM-assisted research with cited primary
docs; the Yahoo exactness claim and the entitlement flip are repo receipts.

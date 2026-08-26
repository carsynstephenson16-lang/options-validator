# Data layer

Derived map of where the platform's data lives — the files are the source
of truth, this is a directory. See [[hypotheses]] for who reads each store
and [[automation]] for what refreshes them daily.

## Options chain cache
Daily EOD option chains, one parquet file per symbol-day, under
`.cache/chains/` (e.g. `AAPL_2018-01-02.parquet`). Reproducibility:
`data/chain_cache_manifest.txt` freezes a sha256 per file;
`tools/cache_manifest.py verify` proves byte-identity to what a ledger
record used. The cache only ever **adds** missing days — `data/recent_topup.py`
(`--scope h7 --refresh-closes`, the daily-ritual call) blind-fetches missing
recent XNYS sessions and self-audits.

## Underlying closes store
Adjusted daily closes per symbol as parquet under `.cache/underlying/`
(`data/underlying_closes.py:24-40`, `store_closes`/`load_closes`) — this is
where `QQQ.parquet` and `SPY.parquet` live (the legacy SPY/QQQ backtests and
any RQ2 line needing an index close). Same module holds split-adjustment
logic (`adjustment_factor`) and the parity-fallback spot price used when a
real quote isn't available (`parity_spot_from_chain`).

## Earnings gating store
`data/earnings/gating_v3.csv` is the current point-in-time earnings-
provenance store: one row per assertion, each timestamped `known_as_of_utc`
so a watcher can ask "what did we know as of this exact session" without
look-ahead. Sourced from SEC filings/IR pages; aggregator-estimated dates
are marked non-promotable. Lineage: `assertions.csv` → `assertions_v2.csv`
→ `gating_v3.csv`. Health over this store: `options_researcher.h7_source_health`
(per-name UNHEALTHY = entry-banned by the watcher's fail-closed gate).

## Rates and dividends CSVs
`data/rates/treasury_cmt.csv` (yield curve, for cash-collateral comparison
lines; provenance `data/rates/treasury_cmt.provenance.md`) and
`data/rates/expected_dividends.csv` (early-assignment risk flag input —
owner spot-check pending, see [[decisions]]). Reader: `data/rates.py`.

## Blind / in-sample split (legacy holdout)
`config.IN_SAMPLE_END = "2022-12-31"` and `config.BACKTEST_END = "2026-06-30"`
(`config.py:77-78`) split the legacy H1/H2 SPY/QQQ backtests into in-sample
vs. a **sealed** holdout; reveal budget 0/3 spent (`ledger/facts.log:8589`,
owner declined). This split does **not** cover the four core names or the
H7 watchlist — they were chosen already knowing the 2023+ AI boom
(`PIVOT_4NAME_SCOPE`, `ledger/facts.log:8590`), so every hypothesis
registered since H5 pre-declares its own validation design instead (usually
a forward paper window — [[hypotheses]]).

## Provider status (as of 2026-08-26): ThetaData retired, Schwab captures
ThetaData acquisition is **DISABLED** — the subscription ended ~2026-07-29
and `data/provider_policy.py` holds a non-overridable refusal; only cached
reads remain (the parquet cache is the permanent record). The remote-MDDS
adapter (`data/thetadata_adapter.py`) survives for cached-read compatibility
only; this page's earlier "subscription confirmed through 2026-11-30" claim
described the pre-July state and was stale. The current capture path is the
**Schwab 15:45 ET preclose lane**: exact-session chain packages land in
`.cache/schwab_chains/` (gitignored, unrepurchasable — currently an
inventory-guard protection GAP; brief 29 is closing it but is BLOCKED
pending re-review as of 2026-08-26) with tracked manifests/receipts
under `reports/schwab_chains/` (capture
`options_researcher/schwab_chain_capture.py`, verifier
`tools/schwab_chain_manifest.py`). Operational sharp edge: the Schwab OAuth
refresh token dies a hard **7 days after creation** (Official-source —
Schwab developer documentation mirrored in the diagnosis report; separately
Test-verified by the 2026-08 production expiry observation; refreshing an
access token does NOT reset the clock) — weekend re-auth procedure in
`reports/2026-08-12-schwab-auth-diagnosis.md`.

## Supporting modules
`data/atomic_io.py` (atomic parquet/JSON writes, tmp file + `os.replace`,
used for every receipt/cache file); `data/cache_provenance.py` (acquisition
facts bound to each cached chain); `data/h7_manifest.py` (self-hashed
feature-build manifests binding input chains + closes + constants to an
H6/H7 feature output).

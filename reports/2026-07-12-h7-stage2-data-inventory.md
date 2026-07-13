# H7 Stage 2 readiness — 12-name local data inventory (Arc B, read-only)

**Bottom line: whole-universe `NO_GO` — 0/12 names GO.** Every name fails on
recency alone: adjusted closes end 2026-07-09 (one session stale) and no name
has a chain snapshot for the 2026-07-10 evaluation session. Everything that
*is* cached is structurally healthy (all 12 newest-day chain audits return
PASS WITH WARNINGS, warnings only on non-selectable rows).

Machine-readable twin: `reports/2026-07-12-h7-stage2-data-inventory.json`
(deterministic, sorted; per-symbol paths, dates, counts, audit results,
reason codes, remediation classes).

## Evaluation identity

- Requested run date: **2026-07-12**
- Evaluation session (derived via `options_researcher.h7_watch.evaluation_session`, not hardcoded): **2026-07-10**
- Causal cutoff (`data.cache_runner.session_close_utc`): **2026-07-10T20:00:00+00:00**
- Universe (`options_researcher.h7_scope.watch_universe()`, exactly 12): AMD, AMZN, AVGO, CEG, CRWV, MSFT, NOW, NVDA, PLTR, SMCI, TEM, VST
- Basis commit: `1924488` (main); inventory branch `research/h7-stage2-readiness-inventory-2026-07-12`
- Read-only: no network call, no ThetaData/paid endpoint, no cache mutation
  (before/after full-cache SHA-256 comparison in the session record: 21,669
  files, 2,540,878,522 bytes, unchanged).

## 12-name verdict table

| Symbol | Verdict | Latest adj close | Newest chain | Cached chain days | Gating reason codes |
|---|---|---|---|---|---|
| AMD | NO_GO | 2026-07-09 | 2026-07-08 | 30 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| AMZN | NO_GO | 2026-07-09 | 2026-07-06 | 2137 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| AVGO | NO_GO | 2026-07-09 | 2026-07-08 | 30 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| CEG | NO_GO | 2026-07-09 | 2026-07-06 | 1103 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| CRWV | NO_GO | 2026-07-09 | 2026-07-07 | 29 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| MSFT | NO_GO | 2026-07-09 | 2026-07-06 | 2137 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| NOW | NO_GO | 2026-07-09 | 2026-07-07 | 2138 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| NVDA | NO_GO | 2026-07-09 | 2026-07-07 | 2138 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| PLTR | NO_GO | 2026-07-09 | 2026-07-07 | 1443 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| SMCI | NO_GO | 2026-07-09 | 2026-07-07 | 1875 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| TEM | NO_GO | 2026-07-09 | 2026-07-07 | 29 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |
| VST | NO_GO | 2026-07-09 | 2026-07-06 | 2137 | CLOSE_STALE, CHAIN_SESSION_MISSING, CHAIN_STALE |

Identical code set on all 12 names; the whole-universe verdict follows
mechanically (GO requires 12/12 GO).

## Data-quality findings

- **Closes** (all 12): file present; zero null/non-finite closes; zero
  duplicate dates; no future rows. Sole defect: last stored session is
  2026-07-09 — the Friday 2026-07-10 close was never pulled.
- **Chains, evaluation session**: no `SYMBOL_2026-07-10.parquet` exists for
  any name, so every eval-session quality metric (schema, nulls, duplicate
  contracts, negative/crossed/zero quotes, audit verdict) is
  **null-by-absence** — unmeasurable, not passing.
- **Chains, supplementary newest-day audits** (labeled supplementary in the
  JSON; read-only `data.recent_topup.audit_chain` on each symbol's newest
  cached day): 12/12 **PASS WITH WARNINGS**, each warning the standard
  non-selectable-row note (e.g., IV NaN on deep-ITM/far-OTM rows that the
  liquidity gate filters). No BLOCK anywhere; no schema gaps; no duplicate
  contracts; no negative or crossed quotes on any newest cached day.
- No future or same-day-partial snapshot exists for any name (nothing dated
  after 2026-07-10 in the chain cache; closes contain nothing after
  2026-07-09).
- Thresholds used are repo-defined only (`MIN_OPEN_INTEREST`,
  `MAX_SPREAD_PCT` via `_liquid_mask`/`audit_chain`); no new threshold was
  invented, and no `OWNER_THRESHOLD_REQUIRED` situation arose.

## Remediation matrix — local refresh vs paid pull

| Need | Names | Class | Paid? |
|---|---|---|---|
| Friday 2026-07-10 close | all 12 | LOCAL_CLOSE_REFRESH_AVAILABLE (`fetch_underlying_eod_av` / `fetch_underlying_eod_yahoo`) | No — free sources exist (network run still needs owner go-ahead) |
| 2026-07-10 EOD chain snapshot | all 12 | PAID_THETADATA_CHAIN_PULL_REQUIRED (`recent_topup` → ThetaData) | **Yes** |

- Names repairable without a paid subscription: **closes only, all 12**.
- Names requiring a ThetaData EOD chain pull: **all 12**.
- Missing paid chain snapshots for this evaluation session: **12** (one per
  name).
- Structural/file repair needed: **none** (no corrupt, misshapen, or
  duplicate-key files found).

## ThetaData decision implications

A Stage 2 daily whole-universe gate is only ever GO on a session whose chains
exist locally — which requires a **fresh ThetaData EOD pull every trading
day** of any forward window, not a one-off backfill. The subscription
currently cancels ~**2026-07-25**. Decision required before any forward
window start date: renew (or re-subscribe on trigger) so daily 12-name chain
pulls are possible, or accept that the Stage 2 gate will report NO_GO on
every session after the cache's last pull. Backfilling only 2026-07-10
(12 snapshots) would green exactly one historical gate day and no future day.

## Scope statements

- **Source health remains 11/12 (exit 1) — CRWV lacks any gating earnings
  assertion pending an official CoreWeave advisory — and that independently
  blocks Stage 2 authorization regardless of this inventory** (decision gate,
  `docs/superpowers/plans/2026-07-12-h7-stage1-closeout-stage2-readiness.md`).
- **This inventory implements nothing and authorizes nothing**: it is Arc B
  read-only discovery. The Stage 2 module/CLI is not built here, and Stages
  3–8 remain unauthorized. No historical H7 diagnostic or backtest ran; no
  trade decision was emitted.

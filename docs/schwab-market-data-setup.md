# Schwab Market Data setup

The integration is installed in both `options-validator` and
`equity-research`. It is intentionally read-only: quotes and option chains are
available, while accounts, positions, transactions, and order endpoints are
not exposed.

The two repositories use one OAuth token for the same Schwab app. Every API
call takes an inter-process file lock, reloads the newest token, applies a
15-second HTTP timeout, uses bounded retry/backoff for transient read-only
failures, and atomically persists any refresh. This prevents the dashboard and
an equity-research pull from refreshing the same token concurrently with stale
in-memory state.

## What you do

Run:

```bash
cd /Users/carsynstephenson/options-validator
uv run python tools/setup_schwab.py
```

Then:

1. Paste the Schwab **Client Secret** at the macOS Keychain prompt.
2. Complete the single Schwab sign-in/approval page.

The secret is pasted once and stored in macOS Keychain, never in either
repository. Both repositories must use the same Schwab Client ID for this
shared-token configuration; the setup helper refuses a mismatch.

The local callback is exactly `https://127.0.0.1:8182`. It is a temporary
listener on this Mac, not a file, folder, or public website. A browser
certificate warning for this loopback callback is expected during first-time
OAuth. Proceed only when the warning page shows this exact address.

## After setup

When setup runs during NYSE regular hours, it automatically checks both stock
quotes and the option-chain schema. If setup runs while the market is closed,
it prints this one deferred market-hours command:

```bash
uv run python -m options_researcher.live_quotes --probe
```

The mission-control live preview will then use Schwab. Historical caches,
backtests, entry scoring, positions, receipts, and official verdicts are
unchanged.

The dashboard uses:

- batched underlying quotes;
- the dedicated expiration-list endpoint;
- current option-chain bid/ask/mark, Greeks, IV, volume, open interest, and
  contract metadata;
- Schwab market-hours windows;
- a 25-second in-process chain cache, so the dashboard's 30-second refresh
  fetches a new snapshot while reusing one response across quote/Greeks/OI
  projections within a refresh.

Delayed or truncated chains, non-success chain status, non-standard
deliverables, non-100 multipliers, stale/future timestamps, and unavailable
market-hours state fail closed in the live preview.

In `equity-research`, the normal market pull adds a cited Schwab quote
cross-check while retaining stockanalysis.com for market cap, valuation
multiples, and analyst consensus:

```bash
cd /Users/carsynstephenson/equity-research
.venv/bin/python scripts/ticker_market_pull.py NVDA
```

The cross-check selects the regular quote during the regular session, the
extended quote in pre/post-market, and a labeled regular close when closed.
Schwab never replaces the primary parsed quote and never changes a research
conclusion.

## Schwab versus ThetaData

A sanitized live probe on 2026-07-30 verified Schwab quotes, multi-symbol
quotes, current option chains, expiration metadata, underlying price history,
instrument lookup, fundamental projection, market hours, and movers for the
configured individual developer account.

Schwab replaces ThetaData only for the current live-preview process. ThetaData
remains required for historical option research: dated EOD chains/Greeks,
point-in-time historical open interest, trade-and-quote history, OPRA
trade-side matching, immutable historical caches, backtests, and OOS replay.
No Schwab response is written into `.cache/chains` or any blind-study cache.

## Security

- The Client Secret is stored in macOS Keychain, not `.env`.
- Refresh tokens live under
  `~/Library/Application Support/Carsyn Research/Schwab/shared-market-data-tokens.json`.
- The token directory is mode `0700`; each token is mode `0600`.
- `SCHWAB_TRADING_ENABLED=false` is enforced in code.
- The SDK surface is allowlisted to read-only market-data methods; account and
  trading methods are unavailable through the wrapper.
- Re-run the setup command if Schwab reports that browser authorization is
  required. No fixed token lifetime is assumed here.

No local storage can guarantee protection from malware already running as your
macOS user. Keep FileVault enabled, keep macOS updated, and rotate a Schwab
Client Secret if it is ever shown in chat, a screenshot, or a public log.

# Market-data providers

This layer is read-only and provider-neutral. It is separate from the
canonical H7/ThetaData cache path, and it never turns missing data into zero.
Every normalized option row carries its provider, quote timestamp, retrieval
timestamp, delayed/real-time label, quality status, and missing-field reasons.

## Priority and roles

1. **Schwab** — authorized current account, quote, and option-chain data. It
   is read-only in this repository; OAuth is not started automatically.
2. **ThetaData** — subscribed historical/EOD chain data. The adapter delegates
   to the repository's existing official `thetadata` client and cache reader;
   cache-only reads are the default.
3. **Massive** — free end-of-day contract discovery and previous-day option
   bars. `MASSIVE_API_KEY` is preferred; `POLYGON_API_KEY` is a compatibility
   fallback.
4. **Alpha Vantage** — supplemental company fundamentals, earnings, compact
   daily equity data, economic/news research, and its official MCP server. It
   is not the primary options source.

The priority is a fallback order, not permission to mix timestamps. A caller
must validate freshness and data quality before reconciling providers.

## Provider limits and unavailable fields

### Massive

The current [Options Basic plan](https://massive.com/pricing?product=options)
documents 5 API calls/minute, two years of historical data, end-of-day data,
reference data, corporate actions, and minute aggregates. The adapter uses
the official [options REST endpoints](https://massive.com/docs/rest/options/overview)
and caches raw JSON responses without the API key.

Options Basic is not treated as providing real-time/15-minute-delayed quotes,
live Greeks/IV, daily open interest, snapshots, WebSockets, or historical
NBBO. Those fields remain unavailable unless the provider response actually
contains them. Contract reference discovery and previous-day bars are safe
development defaults; a full chain quote fan-out is not performed implicitly.

### Alpha Vantage

The official [support page](https://www.alphavantage.co/support/) documents up
to 25 requests/day for the free stock API. The adapter enforces a local
25-request/24-hour limiter, disk caching, duplicate-request prevention, and
bounded retry handling. Daily prices default to `compact`; the official
[documentation](https://www.alphavantage.co/documentation/) identifies full
history and realtime US options data as premium-only capabilities.

The adapter exposes `OVERVIEW`, `EARNINGS`, `TIME_SERIES_DAILY` (compact), and
`NEWS_SENTIMENT`. It refuses to call realtime or historical options endpoints
under a free-tier configuration. Each non-option response is wrapped with a
provider, endpoint, retrieval time, and delayed label.

The official [Alpha Vantage MCP server](https://mcp.alphavantage.co/mcp) is
registered separately in Codex using its OAuth-capable hosted endpoint. The
API key is entered only in the provider's authorization page when you choose
to connect it.

### ThetaData

The project already declares the official `thetadata` package and has a
canonical cache adapter. The official [Python library documentation](https://docs.thetadata.us/Python-Library/Getting-Started.html)
supports API-key authentication through `THETADATA_API_KEY` and also documents
email/password authentication. This project prefers the API-key path already
used by `data/thetadata_adapter.py`; username/password names are retained in
`.env.example` for account setup compatibility.

Subscription entitlement, history window, endpoint coverage, and timestamps
must be checked against the account response. No paid subscription is started
by setup. `fetch_on_miss=False` is the provider adapter default; use the
existing project acquisition gates explicitly when a live fetch is intended.

### Schwab

The scaffold uses the documented Schwab OAuth authorization-code endpoints and
read-only account/market-data paths. It supports account discovery, positions,
quotes, and option chains after the owner completes authorization. Tokens are
stored only through a repo-local `FileTokenStore` interface at
`.secrets/schwab_tokens.json` by default, with mode `0600` and a hard
`PROJECT_ROOT` boundary.

The scaffold does not contain order placement, replacement, cancellation,
exercise, account transfer, or money-movement methods. The callback URL used by
the OAuth request must exactly match the Schwab developer application.

## Freshness and reconciliation rules

- A quote with no timezone-aware quote timestamp is unavailable for freshness
  checks.
- Delayed and real-time fields are never silently combined.
- Midpoint is computed only from finite, non-negative, non-crossed bid/ask
  values. Missing premium fields remain `None`.
- Expired contracts, crossed quotes, negative prices, stale timestamps, invalid
  symbols, duplicate contracts, missing liquidity fields, and large provider
  disagreements produce explicit validation results.
- Earnings, dividend, and early-assignment checks are unavailable until the
  corresponding event data is supplied; they are never assumed clear.
- Raw responses are cached for debugging, but cache keys remove sensitive
  authentication parameters and request errors omit query strings.

## Code entry points

- `market_data.models` — normalized rows, timing/quality status, OCC symbols.
- `market_data.transport` — GET-only transport, cache, retry, and rate limit.
- `market_data.providers.massive` — Massive contract and previous-day adapter.
- `market_data.providers.alpha_vantage` — supplemental Alpha Vantage adapter.
- `market_data.providers.thetadata` — bridge to the canonical ThetaData path.
- `market_data.providers.schwab` — read-only Schwab OAuth/API scaffold.
- `market_data.validation` — per-row and cross-provider validation.

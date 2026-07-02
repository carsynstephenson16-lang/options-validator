# Phase 0 — Lumibot/ThetaData verification against the INSTALLED library

**Date:** 2026-07-02
**Installed:** lumibot 4.5.63 (uv-locked; numpy renegotiated 2.5.0 -> 2.4.6, suite
stayed 147 green). Every claim below cites the installed source file:line or a
fetched doc URL — nothing here is from memory.

## Verified capabilities (usable as sketched)

| Claim | Evidence |
|---|---|
| `from lumibot.backtesting import ThetaDataBacktesting` valid | alias to `ThetaDataBacktestingPandas` — `backtesting/thetadata_backtesting.py:6` |
| Credentials via `THETADATA_USERNAME`/`THETADATA_PASSWORD` env (or ctor args) | `credentials.py:288-291`; datasource `__init__` (`thetadata_backtesting_pandas.py:119-155`) |
| Lumibot manages a LOCAL ThetaTerminal; needs **Java >= 21** | `tools/thetadata_helper.py:389,862` (`_ensure_java_runtime(min_major=21)`); `start_theta_data_client` writes `~/ThetaData/ThetaTerminal/creds.txt` 0600 + launches jar (`:4814-4880`) |
| Quote-based fills at the ADVERSE side (buy@ask / sell@bid) | `backtesting/backtesting_broker.py:4191` (`fill_price = ask if is_buy else bid`), also `:2239,2327` — engine fill model == our frozen bid/ask-crossing model, pre-haircut |
| No silent fallback to trade-OHLC for option quotes | `thetadata_backtesting_pandas.py:52-54` (`option_quote_fallback_allowed = False`, `allow_option_quote_fallback=False`) — unpriceable contract = skip, matches the EOD-gap guardrail |
| Per-contract commissions | `TradingFee(per_contract_fee=0.65)` charged x quantity per fill — `entities/trading_fee.py:7`, `backtesting_broker.py:1985-2017`. NOTE: use `per_contract_fee`, NOT `flat_fee` (flat is per ORDER; the old harness sketch was wrong) |
| Multi-leg orders in backtesting | `Order.OrderClass.MULTILEG` + `child_orders` — `entities/order.py:162,1124`; parent/child processing `backtesting_broker.py:986+` |
| Daily cadence supported | `MIN_TIMESTEP="minute"` but `ALLOW_DAILY_TIMESTEP=True`; broker flips to day for `sleeptime="1D"` (`thetadata_backtesting_pandas.py:45-48`) |
| Chain skeleton + per-contract quotes at sim time | `get_chains(asset)` (`thetadata_backtesting_pandas.py:3945`), `get_quote(asset, ...)` (`:3385`) |
| Endpoints lumibot calls (local terminal, port 25503) | `/v3/option/history/{eod,quote,ohlc}`, `/v3/option/list/expirations`, `/v3/stock/history/*` — `thetadata_helper.py:461-472,342` |

## Capability GAPS (the Phase-0 finding — corrected 2026-07-02)

> An initial "no greeks anywhere in lumibot" claim was a search false negative
> (rg silently honors .gitignore on .venv walks — see
> lessons/2026-07-02-rg-gitignore-false-negatives.md). Corrected picture below,
> re-verified with `rg --no-ignore` + runtime `hasattr` probes.

1. **Lumibot never fetches ThetaData's historical greeks.** The helper calls no
   greeks endpoint (file-scoped search of `thetadata_helper.py` — valid).
   `Strategy.get_greeks` DOES exist, but in backtesting it delegates to
   `data_source.calculate_greeks` (`data_sources/data_source.py:664`), which
   COMPUTES model greeks locally from option price + underlying price +
   risk-free rate (cached per day; `query_greeks=True` only applies to live
   brokers). Model greeks carry assumptions (rate source, dividend handling,
   European-style math on American options) — a prior data review already
   caught computed greeks going junk at extremes.
2. **No open interest in the ThetaData backtest path.** `open_interest` appears
   in live sources (tradier) and entity plumbing, but the ThetaData helper and
   datasource never populate it. The liquidity gate (MIN_OPEN_INTEREST on BOTH
   legs) cannot be enforced from Lumibot's ThetaData backtest data.

**Resolution (keeps the "configure Lumibot, don't build an engine" guardrail):**
the engine (event loop, fills at adverse NBBO, cash/positions, per-contract fees)
stays 100% Lumibot. Selection data (delta, IV, OI) comes from ThetaData's own
REST API on the SAME local ThetaTerminal that lumibot manages, through
`data/thetadata_adapter.get_eod_chain` — the adapter that was always the planned
chain source (`CHAIN_COLUMNS` has included delta/iv/open_interest since Phase 0,
and `strategies/put_credit_spread._get_eod_chain` is the seam that consumes it).
This is a deliberate choice of exchange-derived historical greeks over locally
computed model greeks — data over model — at no extra subscription cost, since
Standard is already required for 2018 history depth. It is data access, not
engine building.

**ThetaData REST facts (fetched from docs.thetadata.us, 2026-07-02):**
- `/v3/option/history/open_interest` — params `symbol`, `expiration` (`*` = all),
  `strike` (`*`), `right` (both), `date`, `format`; returns symbol/expiration/
  strike/right/timestamp/open_interest. **Tier: Value+ (NOT Free).**
- `/v3/option/history/eod` — same param family; response includes OHLC, volume,
  and the closing NBBO bid/ask.
- Greeks (v2->v3 migration guide): `/v3/option/history/greeks/first_order`
  (delta lives here; second/third order exist), IV at
  `/v3/option/history/greeks_implied_volatility`.
- Terminal default base: `http://127.0.0.1:25503` (also `thetadata_helper.py:342`).
- v3 merged bulk into history: `expiration=*` + `strike=*` returns the whole chain.
- **Open live question for the smoke test:** the exact EOD/interval semantics of
  the greeks/IV history endpoints (interval param name/values, response column
  names). The adapter requests `interval=1d`, fails loud on unexpected columns,
  and the first live smoke test settles it. Do NOT trust the greeks call until
  the smoke test passes.
- **Tier gate for greeks:** today's subscriptions doc confirms OI needs Value+
  but doesn't tier the greeks endpoints; a prior session's live pricing check
  (2026-07-01, in project memory) recorded Standard = EOD bid/ask + 1st-order
  greeks + IV, Pro = all greeks. First-order (delta) is all Strategy A needs.
  Still: probe the greeks endpoint immediately after subscribing, BEFORE
  relying on it. (Fallback if it were Pro-gated: lumibot's local
  `calculate_greeks` model values — extra assumptions, decide only if needed.)

## Subscription tiers (fetched from thetadata.net + docs, 2026-07-02)

| Tier | Options price | History from | Notes |
|---|---|---|---|
| Free | $0 | 2023-06-01 | **Every priced date is inside the post-2022 OOS holdout** |
| Value | $40/mo | 2020-01-01 | misses the 2018 regime -> unusable for the configured window |
| Standard | $80/mo | 2016-01-01 | **minimum tier covering BACKTEST_START=2018-01-01** |
| Pro | $160/mo | 2012-06-01 | more than needed |

**Integrity collision, stated plainly:** the "free tier first" idea cannot probe
PRICE data without touching the holdout, because free-tier history starts
2023-06-01 and the spec says "'just printing a chain' after 2022 is still a
holdout look" (smoke probes must stay <= IN_SAMPLE_END). Free tier is still fine
for: account creation, terminal/auth verification, and METADATA endpoints
(terminal status, expirations list — reference data, not market data; lumibot's
own healthcheck hits `/v3/option/list/expirations`, `thetadata_helper.py:410`).
The real smoke test (SMOKE_TEST_DATE=2022-12-30) needs **Standard**.

## Authentication model — TWO paths, an unresolved decision (2026-07-02)

> **LIVE RESULT (2026-07-02, later same day): Path A executed and REJECTED.**
> Prereqs all held (Java 26, `THETADATA_USERNAME`/`THETADATA_PASSWORD` present
> in `.env` — checked as booleans, values never read). Lumibot's launcher
> downloaded/launched ThetaTerminal (Bootstrap 20250709, Terminal 20260629),
> wrote `creds.txt` 0600 — and the terminal rejected the login on every
> ~30s relaunch: `ERROR: Invalid credentials. Please check your credentials
> file, API key, or environment variable, and try again.` Port 25503 never
> served; the free metadata probe was never reached. Note the 20260629 error
> text puts "API key" first-class — the account may have moved to key auth,
> or the password is stale. **OWNER ACTION (only the owner can fix
> credentials):** log in at thetadata.net and verify/reset the email+password
> in `.env`, or explicitly authorize Path B (launch with `THETA_DATA_API_KEY`;
> terminal 20260629 >= the 20260615 minimum). The fetch path stays
> launcher-agnostic either way. Recorded in `ledger/facts.log`.

The owner supplied a ThetaData **API key** (`td1_prod_...`, stored in `.env` as
`THETA_DATA_API_KEY` — the exact var ThetaTerminal reads per docs.thetadata.us;
requires ThetaTerminal/Bootstrap >= 20260615). But the **installed lumibot
4.5.63 authenticates ThetaData ONLY via `THETADATA_USERNAME`/`THETADATA_PASSWORD`**
(email+password -> `creds.txt` -> it launches `ThetaTerminalv3.jar`;
`credentials.py:288-291`, `thetadata_helper.py:4814-4880`). Re-verified with
`rg --no-ignore`: lumibot has NO ThetaData API-key path (its API_KEY/token
config entries are Polygon/DataBento/Alpaca/Tradier, not ThetaData).

So the API key alone will NOT authenticate through lumibot's launcher. Pick one
in the next session (this is the "most optimal way" call the owner deferred):

- **Path A — email+password (least change):** add `THETADATA_USERNAME`/
  `THETADATA_PASSWORD` to `.env`; lumibot launches the terminal exactly as the
  installed code expects. The API key goes unused.
- **Path B — API key (decouples from lumibot's launcher):** launch
  ThetaTerminal ourselves with `THETA_DATA_API_KEY` exported (CLI `--api-key`
  or env var; terminal must be >= 20260615), then `data/thetadata_adapter.py`
  hits `localhost:25503` — the fetch path is launcher-agnostic once the terminal
  is alive. Needs a version check on the jar lumibot downloads, and a small
  launcher (bypassing `start_theta_data_client`'s username/password write).

`_ensure_terminal()` currently implements Path A and fails loud pointing at both
options; the merge/fetch/OOS-guard logic is already Path-agnostic and offline-tested.

## Prerequisites before the first live call (owner actions)

1. **Java >= 21** — DONE 2026-07-02: `brew install openjdk` + `brew link --force
   openjdk` -> OpenJDK 26.0.1 at `/opt/homebrew/bin/java` (verified `java -version`).
2. **ThetaData auth** -> resolve Path A vs B above. API key already in `.env`;
   add email+password there if Path A. `.env` is gitignored (never committed).
3. **Options Standard ($80, one month)** when ready to pull real history; plan
   remains: subscribe -> smoke test (2022-12-30) -> cache 2018-2022 in-sample
   locally (parquet) -> backtest from cache -> cancel. Free tier can only do
   account/terminal/auth + metadata checks ($0) since its price history starts
   inside the holdout.

## Sequencing note (charge-on-touch)

The audit's "notes-later" item stands: when the OOS reveal is eventually run,
the data seam must expose "post-2022 data opened" as an auditable event. The
adapter's fetch path will refuse post-IN_SAMPLE_END dates unless explicitly
flagged by the reveal gate — enforced in code when the OOS path is wired
(not needed for in-sample caching).

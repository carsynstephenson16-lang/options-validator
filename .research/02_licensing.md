# Phase 0 / 02 — Data-licensing audit: "intraday volume periodicity" candidate signal

- **Research cutoff / access date:** 2026-07-24 (all web sources fetched this date unless noted)
- **Scope:** every dataset/API this candidate signal could plausibly depend on. The
  signal needs **intraday equity VOLUME** (minute-level or finer) for the repo's
  research universe, both (a) historically, to estimate a per-name volume profile,
  and (b) LIVE every trading day, to compare that day's volume shape against the
  profile.
- **Gate being tested (owner rule, not this file's call):** any NEW data dependency
  must be free for live use, with published terms permitting it. Paid access,
  unclear licensing, or cloud-only data = automatic FAIL.
- **Vocabulary/claim discipline applied throughout:** every availability/licensing
  claim below is labeled Repo-verified, Official-source (URL + access date),
  Inference, or Assumption. No claim of "free"/"live"/"permitted" appears without
  one of those labels attached.

## 0. Repo-verified starting facts

**Universe (Repo-verified, `config.py`, read 2026-07-24):** the backtest
`UNIVERSE` is 4 names (`MSFT, AMZN, VST, CEG`). The live/attractiveness universe
is wider: `H7_WATCHLIST = [CRWV, TEM, PLTR, NOW, SMCI, NVDA, AMD, AVGO, IREN,
USAR, ET]` (11 names) plus `H7_CORE_LONG_ONLY = [VST, CEG, MSFT, AMZN]` (4 names),
minus `H7_EXCLUDED = [HYLN]` (not a member of either list). `config.
ATTRACTIVENESS_UNIVERSE` is exactly that union: **15 names**, not 14 — the task
brief's list of 14 omits `USAR` (USA Rare Earth). This audit treats "~14–15 US
equity names" as the correct sizing; it does not change any conclusion below
(every provider's free-tier symbol/request caps are evaluated against 15, the
more conservative number).

**ThetaData current entitlement (Repo-verified, `reports/live_probe/
2026-07-24.json`, produced by `options_researcher/live_quotes.py --probe` this
session):**

```
"stock_entitled": false
"stock_snapshot_quote": PERMISSION_DENIED — "Requesting a stock endpoint
  requiring a value subscription, but you only have a FREE subscript[ion]"
"option_snapshot_greeks_all": PERMISSION_DENIED — "Requesting an option endpoint
  requiring a professional subscription, but you only have a STAND[ARD]..."
"option_list_expirations": ok
"option_snapshot_quote": ok
"option_snapshot_open_interest": ok
```

This is a live, real error from ThetaData's own v3 gRPC service, not a docs
claim. It confirms two things Repo-verified beyond any doubt: (1) the repo's
current ThetaData plan carries **FREE-tier stock entitlement** (denied for the
real-time stock snapshot endpoint) and **STANDARD-tier options entitlement**
(denied only for the PROFESSIONAL-gated greeks-all snapshot); (2) `live_quotes.py`
already assumes stock endpoints may be unentitled and falls back to a
put-call-parity spot — i.e., the repo engineering already treats "no live stock
feed" as the default-safe case. Any intraday-volume signal needs a **stock**
(not options) feed, which today's ThetaData plan explicitly does not carry live.

---

## 1. QuantConnect — the critical provider

### 1a. Historical access inside QuantConnect Cloud research notebooks

- **Official-source** (quantconnect.com/docs/v2/cloud-platform/organizations/
  tier-features, accessed 2026-07-24): the **Free** organization tier gets
  "minute to daily resolutions" of US Equity data, unlimited backtesting, "no
  live trading, no local coding, no tick/second data resolution, 1 research
  node only."
- **Official-source** (quantconnect.com/docs/v2/writing-algorithms/datasets/
  algoseek/us-equities, accessed 2026-07-24): the default US Equities dataset is
  **AlgoSeek**, "survivorship bias-free" coverage of the full SIP CTA/UTP feed
  since 1998, ~27,500 securities, "Tick, Second, Minute, Hourly, & Daily"
  resolutions, sourced via Equinix co-located servers (i.e., professional-grade
  provenance, not a compromise on data quality — the constraint here is
  entirely licensing/cost, not accuracy).
- **Bottom line 1a:** yes, minute-resolution equity volume is genuinely free to
  *look at inside a Cloud research notebook or backtest*. This is real, but it
  is also the exact thing the task warns not to treat as proof of anything
  more: it cannot be exported, cannot run live, and cannot be scheduled to run
  unattended every trading day outside the browser/cloud IDE.

### 1b. Historical access OUTSIDE the cloud (local Lean CLI / per-file purchase)

- **Official-source** (quantconnect.com/docs/v2/lean-cli/api-reference/
  lean-data-download, accessed 2026-07-24): *"To use the CLI, you must be a
  member in an organization on a paid tier."* Data from the Dataset Market "is
  priced on a per-file per-download basis... QCC is deducted from your
  organization's QCC balance when a file is downloaded." No free dataset is
  identified anywhere in this command's documentation.
- **Official-source** (quantconnect.com/docs/v2/cloud-platform/organizations/
  tier-features, accessed 2026-07-24): local Lean CLI access ("access to the
  QuantConnect API and can use the CLI to run Lean locally") begins at the
  **Quant Researcher** tier, not Free.
- Secondary-source estimate (newtrading.io review, accessed via search
  2026-07-24, **not confirmed on QuantConnect's own pricing page**, which showed
  "custom pricing" with no visible number for this tier): ~$60/month for the
  Researcher/Quant Researcher tier. **Flagged as unresolved** — the official
  pricing page did not render a specific dollar figure for this session; treat
  the $60 figure as Inference from a third party, not Official-source.
- **Conclusion 1b:** local download requires (i) a paid organization tier, (ii)
  per-file QCC credit spend on top of that, for essentially every dataset this
  signal would need at 15-name x years-of-history granularity. There is no
  free local-download path identified.

### 1c. Rights to download data locally

- **Official-source, verbatim** (quantconnect.com/docs/v2/cloud-platform/
  datasets/licensing, accessed 2026-07-24): *"This download is for the licensed
  organization's internal LEAN use only and cannot be redistributed or
  converted in any format."* Users may share chart images derived from the
  data only if "the original data can't be reconstructed from the image." The
  page states outright that QuantConnect "can't freely redistribute most of
  the datasets" because of its own contracts with data providers.
- **Conclusion 1c:** even a paid download license does not grant a portable,
  reusable copy of the data for use in this repo's own harness/parquet cache —
  it must stay inside LEAN, unconverted, non-redistributed. That is a hard
  structural mismatch with this repo's architecture (`data/` parquet cache
  read by `options_researcher/*`, independent of any Lean runtime).

### 1d. LIVE data availability — tier/live-node requirement

- **Official-source** (quantconnect.com/docs/v2/cloud-platform/organizations/
  tier-features, accessed 2026-07-24): *"Free Tier Live Trading: No. The Free
  tier makes no mention of live trading capability; live trading access begins
  at the Quant Researcher tier."* Quant Researcher unlocks "up to 2 live
  trading nodes," Team "up to 10," Trading Firm/Institution "no limit."
- **Official-source** (quantconnect.com/docs/v2/cloud-platform/live-trading/
  deployment, accessed 2026-07-24): confirms the Free tier row shows "0" live
  trading nodes; live trading node pricing is on the separate Pricing page.
- Secondary-source figures (search results, accessed 2026-07-24, not directly
  re-confirmed on the rendered pricing page in this session): live node prices
  ranging **$24/month (1 CPU / 1GB RAM) up to $1,000/month** (GPU nodes),
  independent of the organization-tier subscription cost itself.
- For **Cloud** live deployment specifically, one 2026 forum/search source
  states Polygon is the (or a) supported streaming data provider; for **local**
  Lean CLI live deployment, QuantConnect documents separate, bring-your-own
  data-provider integrations (Polygon, IEX Cloud, or a brokerage's own feed),
  each carrying its own account/API-key/cost requirements outside QuantConnect
  itself (see §5/§6 below for those providers' own free-tier terms).
- **Conclusion 1d:** there is no dollar-zero path to live QuantConnect
  deployment at all. Minimum stack is: paid organization tier (Quant
  Researcher or above) **+** a paid live trading node **+** (for local
  deployment) a separately-licensed live data feed.

### 1e. Latency and US equity coverage

- **Official-source** (AlgoSeek US Equities docs, accessed 2026-07-24):
  co-located, full-SIP-feed sourcing — this is high-quality, low-latency,
  professional data. **This provider does not fail on data quality.** It fails
  on the combination of cost + license scope for live/local use.

### 1f. Commercial-use / redistribution restrictions

- Covered in 1c: internal-LEAN-use-only, no redistribution, no format
  conversion, chart-image sharing only if the source data is not
  reconstructable. Contractually driven by QuantConnect's own upstream data
  contracts, per the licensing page itself.

### Authentication (QuantConnect)

Official-source (docs, accessed 2026-07-24): account + organization
membership (email login), API key/token for Lean CLI programmatic access at
paid tiers; Free tier authenticates via the web IDE session only (no CLI/API
key issued for local use).

### QuantConnect bottom line

**FAILS the free-for-live-use gate at every layer that matters for this
signal.** The only genuinely free layer (1a, Cloud research/backtest) is
explicitly non-live and non-exportable — the task's own instruction not to
treat free cloud backtesting as proof of local/live access is confirmed
correct by QuantConnect's own docs. Local storage, local live deployment, and
Cloud live deployment all require a paid organization tier at minimum, plus
per-file data costs, plus a live-node fee, plus (for local live) a
separately-licensed live feed. No configuration of QuantConnect delivers
"minute equity volume, historical + live, for $0, with published terms
permitting it."

---

## 2. ThetaData (current subscription; already paid for options)

- **Official-source** (docs.thetadata.us/Articles/Getting-Started/
  Subscriptions.html, accessed 2026-07-24) — **Stock** data tiers (separate
  subscription from Options; explicitly stated: *"Purchasing one does not grant
  access to the other"*):
  - **FREE** — EOD only, history from 2023-06-01, 30 req/min.
  - **VALUE** — 1-minute granularity, history from 2021-01-01, **15-minute
    delayed** (not live).
  - **STANDARD** — 1-minute granularity, history from 2016-01-01, real-time.
  - **PRO** — tick-level, history from 2012-06-01, real-time.
- **Repo-verified** (§0 above): the repo's live stock entitlement today is
  **FREE** (EOD only; the live snapshot endpoint was denied outright, not
  merely delayed).
- **Official-source** (thetadata.net/pricing, accessed 2026-07-24) — the
  visible pricing table on this fetch was **Options**-labeled: Value $40/mo
  (real-time, 1-min intervals, 4yr history), Standard $80/mo (tick-level, 8yr
  history), Pro $160/mo (full tick stream, 12yr history). **Evidence conflict,
  disclosed rather than resolved:** a separate secondary source (search results,
  same access date) attached the same $40/$80/$160 numbers to differently-named
  tiers ("Standard"/"Pro"/unnamed $160) for what may be the *stock* line, not
  options. The two official-looking fetches did not agree on which product
  line ($40/$80/$160) maps to which tier name for **stock** specifically. This
  session could not resolve the ambiguity — record as an **unresolved evidence
  gap**: the exact current monthly price of ThetaData's stock VALUE/STANDARD
  tiers (the tiers that would actually unlock minute-level live volume) was not
  cleanly confirmed, only that they are paid, and higher than the FREE tier
  the repo has now.
- **Official-source, verbatim** (thetadata.net/terms-and-conditions, accessed
  2026-07-24): personal use is restricted to *"personal, non-commercial use of
  Subscriber's Authorized Users"* and *"personal investment activities and the
  personal investment activities of your immediate family members."*
  Subscribers must not *"use the Services Data in connection with any trade,
  business, professional or other commercial activities."* A separate
  "Business" tier exists for commercial use (thetadata.net/commercial-use,
  accessed 2026-07-24: "Individual — Personal use only, no redistribution or
  business use" vs. "Business — For commercial applications and business use
  cases," listed price range **$400–$1,600/month** in one fetch of that page).
  This repo's stated posture (research-only, no live orders, not a business)
  plausibly fits "Individual," which is the relevant comparison point, not the
  Business tier.
- Caveat: the Terms & Conditions page also contains generic anti-scraping /
  anti-robot language typical of a marketing-site ToS template; it is unclear
  from this fetch alone whether that clause targets the *website* or the
  *paid API itself* (which is obviously meant to be queried programmatically
  by paying subscribers) — flagged as **Assumption** that it does not apply to
  authorized API use, not confirmed.
- **Conclusion:** getting live, real-time (or even 15-minute-delayed) minute
  stock volume from ThetaData requires **upgrading the stock subscription from
  FREE to at least VALUE** (paid) — a new, ongoing cost on top of the existing
  options subscription. FREE stock tier gives EOD-only history from
  2023-06-01, which cannot support either "live daily comparison" or a
  historical volume-profile estimate deeper than ~3 years.
- **Authentication (Repo-verified):** per-account API credentials against a
  local ThetaData Terminal/gRPC client (`data/thetadata_adapter.py::_client()`
  in this repo); the terminal process authenticates the subscription tier
  server-side, which is exactly how §0's live probe surfaced the FREE-vs-paid
  denial.

---

## 3. Alpha Vantage (free tier)

- **Official-source** (alphavantage.co/premium/, accessed 2026-07-24): free
  tier is throttled to a *"standard API usage limit (25 API requests per
  day)."* For 15 symbols this is exhausted by one request per symbol per day,
  leaving no headroom for repeated intraday snapshots.
- **Official-source** (alphavantage.co/documentation/, TIME_SERIES_INTRADAY,
  accessed 2026-07-24): the endpoint returns OHLCV (volume included), "20+
  years of historical intraday" depth. Critically: *"by default, `entitlement`
  is not set and historical data is returned"* — i.e., **the free-tier default
  response is NOT live/real-time data**; realtime or 15-minute-delayed access
  requires the `entitlement` parameter, gated behind "premium membership."
- **Terms of Service:** fetched as a PDF (alphavantage.co/terms_of_service/,
  accessed 2026-07-24) — the tool returned garbled/undecodable binary content;
  **could not extract verbatim redistribution/commercial-use terms this
  session.** Recorded as an access gap, not inferred.
- **Conclusion:** even ignoring the unresolved ToS text, 25 requests/day
  structurally cannot serve 15 names at intraday cadence, and the free-tier
  default is historical/delayed rather than live by the documentation's own
  wording.
- **Authentication:** free `apikey` query parameter, obtained via email
  sign-up at alphavantage.co — no payment method required for the free key
  itself (Official-source, alphavantage.co, accessed 2026-07-24).

---

## 4. yfinance / Yahoo Finance

- **Official-source, verbatim** (legal.yahoo.com/us/en/yahoo/terms/otos/
  index.html, accessed 2026-07-24), Yahoo Terms of Service §2.4(ix):
  *"access or collect data, or attempt to access or collect data, from our
  Services using any automated means, devices, programs, algorithms or
  methodologies, including but not limited to robots, spiders, scrapers, data
  mining tools, or data gathering or extraction tools, for any purpose without
  our express, prior permission."*
- §2.4(x), same page: prohibits using Yahoo data *"to create any database,
  archive, mobile application, data feed, widget or any other aggregated data
  source that competes with or constitutes a material substitute for the
  Services... or the services offered by our data providers."*
- **Official-source** (github.com/ranaroussi/yfinance README, accessed
  2026-07-24): *"yfinance is not affiliated, endorsed, or vetted by Yahoo,
  Inc."* and *"the Yahoo! finance API is intended for personal use only"* —
  the library's own maintainers explicitly disclaim official status and point
  users back to Yahoo's ToS to judge their own rights to the data.
- **Conclusion:** this is the clean, unambiguous case the task anticipated —
  **published terms explicitly do not permit the automated-scraping access
  method yfinance uses.** This is not an "unclear licensing" case; it is a
  clear "no." Reliability is also a known risk (unofficial endpoint, breaks on
  Yahoo backend changes, no SLA) — Official-source-adjacent (yfinance's own
  README disclaims stability guarantees) but secondary in the sense that this
  is community consensus, not a Yahoo statement.

---

## 5. Polygon.io (rebranded **Massive.com**, July 2026)

- **Official-source** (massive.com/pricing?product=stocks, accessed
  2026-07-24 — polygon.io/pricing now 301-redirects here): free **"Stocks
  Basic"** tier — $0/month, "5 API Calls/Minute," 2 years of historical data,
  **"End of day data only (not real-time),"** minute aggregates available
  (historically, delivered as an EOD batch, not live-streamed through the
  day), labeled **"Individual use"** only.
- Paid **Stocks Starter** — $29/month, unlimited calls, 5-year history,
  **15-minute delayed** live data.
- Paid **Stocks Developer** — $79/month, trade-level data, 10-year history.
- Paid **Stocks Advanced** — $199/month, **real-time** data, 20+ year history.
- The free-tier page flags "[Non-pros only]" (a link to a "professional
  status" definition) implying professional/institutional use requires a
  different license, but the exact professional-status test text was not
  fetched this session (gap).
- **Conclusion:** free tier gives 2 years of minute-bar history for free but
  is explicitly EOD-batch, not live — same-day, intraday updates require the
  $29/month Starter plan at minimum (still only 15-min-delayed), and true
  real-time needs $199/month.
- **Authentication:** free API key via email sign-up, "no credit card
  required" per the free-tier page (Official-source, massive.com/pricing,
  accessed 2026-07-24).

---

## 6. Alpaca Market Data (free "Basic" tier, IEX feed)

- **Official-source** (docs.alpaca.markets, "About Market Data API," accessed
  2026-07-24): Basic (free) plan — **real-time** feed but **IEX exchange
  only** for equities (not the full consolidated SIP tape); Algo Trader Plus
  ($99/month) unlocks "All US Stock Exchanges." Rate limit 200 calls/min
  (Basic) vs. 10,000/min (paid). Both plans cover history "Since 2016," but
  Basic restricts **the most recent 15 minutes** of historical/REST bar
  queries (i.e., a 15-minute recency lag on pulled bars — true real-time
  requires reading the live websocket stream directly rather than the REST
  history endpoint). Websocket subscriptions on Basic are capped at **30
  symbols** for equities — the repo's 15-name universe fits comfortably under
  this cap.
- **Official-source, verbatim** (Alpaca Terms and Conditions / Customer
  Agreement PDFs, files.alpaca.markets/disclosures/library/, accessed via
  search 2026-07-24): users "agree not to reproduce, distribute, sell or
  commercially exploit the market data in any manner without written consent
  from Alpaca," and to use the Services/Content "solely for their own personal
  and non-commercial purposes." The Basic plan is free; the paid Pro plan
  requires accepting a separate NASDAQ/exchange market-data-display agreement.
- Account requirement: signing up for a free Alpaca account (no confirmed KYC
  or funded-brokerage requirement solely for market-data API keys; some
  regional/tax-residency restrictions may apply per community sources, not
  independently confirmed against an official page this session).
- **Signal-quality consequence (Inference, not this file's call to make):**
  IEX is one execution venue among many. **Official-source** (marketsmedia.com
  / IEX's own published statistics, accessed 2026-07-24): IEX's own reported
  share of US equity volume was **~3.2%–3.8%** of total consolidated volume
  including off-exchange trading in Q4 2025 (and up to ~6% of on-exchange-only
  volume, excluding off-exchange/dark trading), with a much higher (~25%+)
  share specifically of midpoint/block notional volume. A volume-periodicity
  signal built on IEX-only prints is therefore built on a **small, and
  venue-composition-skewed** (more midpoint/algorithmic, per IEX's own
  marketing) slice of the tape, not the full market. Whether that slice's
  *intraday shape* (the periodicity a profile-based signal would key off) is
  representative of the full tape's shape is an open empirical question this
  audit did not test — flagged explicitly as Inference/unverified, for the
  signal designer or gatekeeper to weigh, not decided here.
- **Conclusion:** this is the one candidate in the audit that is genuinely
  **$0, real-time (via websocket), minute-capable, and covers all 15 names**
  under its symbol cap, with published terms that appear compatible with a
  personal, non-commercial research validator (not a redistribution/resale
  product). Its real, disclosed limitation is IEX-only partial-market-volume
  coverage, not cost or license clarity.

---

## 7. Finnhub (free tier) — brief record

- **Official-source** (search of finnhub.io/pricing-stock-api-market-data and
  finnhub.io/docs/api/rate-limit, accessed 2026-07-24): free plan is commonly
  cited at **60 API calls/minute**; direct WebFetch of both pages returned
  only page titles/metadata, not the rendered pricing table, in this session
  — **could not independently confirm the rate limit or plan features from
  primary text this session.**
- **Unresolved evidence gap:** whether free-tier US stock intraday candles
  (`/stock/candle`) are actually served is disputed. A public GitHub issue
  (finnhubio/Finnhub-API #546, accessed 2026-07-24) shows a user reporting
  `{"error":"You don't have access to this resource."}` on the free plan
  fetching AAPL candles, with no official Finnhub maintainer response visible
  in the issue thread. No official page confirming or denying free-tier
  intraday-candle access was successfully fetched this session. **Recorded as
  Assumption/unresolved, not decided.**
- **Conclusion:** cannot be certified as a free, working path to intraday
  equity volume without further direct testing (e.g., an actual free API key
  call), which is outside this audit's read-only research scope.
- **Authentication:** free API key via email sign-up (Official-source,
  finnhub.io, accessed 2026-07-24 — sign-up flow confirmed to exist, feature
  gating on the resulting key not confirmed, see gap above).

---

## 8. Twelve Data (free tier) — brief record

- **Official-source** (twelvedata.com/pricing, accessed 2026-07-24): free
  "Basic" plan — 8 requests/minute (≈800/day cap), license text states access
  is for **"personal, internal, and non-commercial purposes"** with
  **"internal non-display usage"** (i.e., no external redistribution/display).
  The same page's feature list states "Real-time US equities and ETFs" are
  included on Basic.
- **Evidence conflict, disclosed:** multiple secondary sources (search
  results, same access date) instead describe Twelve Data's free tier as
  delayed (1–15 minutes depending on exchange) and unsuitable for intraday use
  at scale. This session's direct fetch of the official pricing page said
  "real-time," contradicting the secondary characterization. **Not resolved
  either way — flag both claims, do not pick one.**
- **Conclusion:** even setting the real-time/delayed dispute aside, 800
  requests/day split across 15 names (~53 calls/name/day) is thin for a true
  intraday-periodicity signal requiring many samples through the trading day,
  though it might support a handful of coarse snapshots per name per day.
  License text ("personal, internal, non-commercial") is compatible with this
  repo's stated research-only posture.
- **Authentication:** free API key via email sign-up (Official-source,
  twelvedata.com, accessed 2026-07-24).

---

## 9. Stooq — brief record

- Search-derived characterization (accessed 2026-07-24, **could not
  independently confirm via direct WebFetch** — stooq.com and stooq.com/
  terms.html both returned empty/unrenderable content to the fetch tool this
  session): Stooq has **no documented API**; access is via a manual
  ticker-search-and-CSV-download web portal. Reported resolutions: hourly bars
  ≈9 months lookback (≈1,400 points), 5-minute bars ≈1 month lookback (≈2,000
  points), daily EOD 20+ years. No live/real-time streaming offering was
  identified.
- **Unresolved evidence gap:** Stooq's terms-of-use page could not be fetched
  this session (empty response both attempts); redistribution/commercial-use
  terms are **unconfirmed**, and the licensing-clarity gate cannot be
  satisfied on unconfirmed terms even if the depth/resolution were otherwise
  sufficient.
- **Conclusion:** no live capability at all (fails the "live every day" half
  of the requirement outright), and terms of use could not be verified this
  session — automatic FAIL on both the live-availability and
  licensing-clarity dimensions, independent of each other.
- **Authentication:** none identified — manual web download only, no API key
  or account system found in this session's research.

---

## 10. Nasdaq Data Link (formerly Quandl) — brief record

- Search-derived characterization (accessed 2026-07-24; direct WebFetch of
  data.nasdaq.com/publishers/QDL and docs.data.nasdaq.com/docs/
  terms-of-service returned empty content / HTTP 404 respectively this
  session — **could not confirm via primary text**): the platform aggregates
  400+ third-party data publishers; free datasets are described as
  "often... daily frequency"; intraday equity data, where it exists on the
  platform at all, is generally attached to paid, publisher-specific
  datasets rather than a blanket free intraday feed.
- **Unresolved evidence gap:** no single Nasdaq-Data-Link-wide terms page was
  successfully fetched this session; licensing is per-publisher/per-dataset
  rather than platform-wide, which this audit could not enumerate
  exhaustively.
- **Conclusion:** no evidence of a free, platform-wide intraday equity volume
  feed; EOD-only is the well-supported default expectation. Fails on
  historical-resolution grounds alone for this signal's needs, independent of
  the live question.
- **Authentication:** API key via account sign-up at data.nasdaq.com (general
  platform pattern); per-publisher datasets may require separate paid
  entitlement on top of the base key (not enumerated this session).

---

## Summary table

| Provider | Free minute-bar history? | Free LIVE minute volume? | Covers 15 names? | Published terms clear? | Verdict for this signal |
|---|---|---|---|---|---|
| QuantConnect (Cloud) | Yes, in-cloud only | **No** (Free tier: 0 live nodes) | Yes (in-cloud) | Yes — explicitly non-exportable, no redistribution | FAIL (not live/local) |
| QuantConnect (local Lean CLI) | No — paid tier + per-file QCC | **No** — paid tier + paid live node + own feed | N/A | Yes — internal-LEAN-only, no redistribution | FAIL (paid at every layer) |
| ThetaData (current repo plan) | No — FREE stock tier is EOD-only, 2023-06-01+ | **No** — live/minute stock needs paid VALUE+ upgrade | Options tier only; stock untested at scale | Individual/Business split documented; some ambiguity on exact stock tier pricing | FAIL as currently subscribed; a real (quantified) upgrade cost, not free |
| Alpha Vantage | Yes (structurally, 20+yr) but only 25 req/day | **No** — default response is historical, live needs premium `entitlement` | No — 25 req/day too thin for 15 names | ToS unreadable this session (gap) | FAIL (rate limit + non-live default) |
| yfinance / Yahoo | Yes (unofficial) | Yes (unofficial), but **prohibited by Yahoo's own ToS** | Yes, informally | **Yes — and it says no** (anti-scraping clause) | FAIL (clear prohibition, not "unclear") |
| Polygon.io / Massive.com | Yes, free, 2yr, minute aggregates | **No** — free tier is EOD-batch only; live needs $29–199/mo | Yes | Yes — "Individual use" only | FAIL (no free live path) |
| Alpaca (IEX, Basic) | Yes, free, since 2016 (15-min REST lag) | **Yes** — real-time IEX websocket, free | Yes (≤30 symbols) | Yes — personal/non-commercial, compatible with this repo | **Only provider that clears the free-for-live gate**, with a disclosed partial-market-coverage caveat |
| Finnhub | Disputed/unconfirmed | Disputed/unconfirmed | Unclear | Not confirmed this session | GAP — cannot certify |
| Twelve Data | Conflicting claims (real-time vs delayed) | Conflicting claims | Thin (800 req/day / 15 names) | Yes — personal/internal/non-commercial | Likely FAIL on volume of calls even if license is fine |
| Stooq | Partial (short intraday lookback) | **No** — no live offering | Yes (manual only) | Unconfirmed (fetch failed) | FAIL (no live + unconfirmed terms) |
| Nasdaq Data Link | EOD-dominant | **No** evidence of free intraday | Unclear | Per-publisher, not enumerated | FAIL (no live path found) |

---

## Bottom line

### Cheapest valid FREE path to minute-level equity volume (historical + live) for ~15 names, if any exists

**Alpaca Market Data's free "Basic" plan (IEX feed)** is the only candidate in
this audit that combines, on Official-source evidence: (1) $0 cost, (2) a
genuinely real-time (not artificially delayed) live feed via websocket, (3)
minute-bar OHLCV history back to 2016 (with a 15-minute recency lag specific to
the REST historical-bars endpoint, not the live stream), (4) a 30-symbol
websocket cap that comfortably covers the repo's 15-name universe, and (5)
published Terms and Conditions whose "personal and non-commercial purposes"
restriction is plausibly compatible with this repo's stated research-only,
no-live-orders posture.

**Its limitation is structural, not financial:** IEX represents only
~3–6% of total US consolidated equity volume (IEX's own published market-share
statistics, Q4 2025). A "volume periodicity" profile built and monitored on
IEX-only prints is a profile of one venue's activity, not the market's. Twelve
Data's free tier is a distant second (if its "real-time" claim on the official
pricing page is correct rather than the conflicting secondary "delayed"
characterization) but is rate-limited to ~53 calls/name/day across 15 names —
thin for anything beyond a few coarse daily snapshots. Every other audited
provider fails either the live-availability test, the free-cost test, or the
clear-published-terms test outright.

### Would DELAYED data structurally break a live scanner signal? (Inference — not this file's gate to decide)

Reasoning, not a decision: a "volume periodicity" signal, by the task's own
framing, compares *today's* evolving intraday volume shape against a
historical profile to flag an anomaly or confirmation *while the trading day
is still in progress* (that is the only reason "live" matters at all — an
end-of-day comparison would need only yesterday's close, which every free EOD
provider already supplies for free). If the live feed is delayed by even 15
minutes (Polygon/Massive Starter, Alpaca's REST-history endpoint, Alpha
Vantage's non-premium default), the scanner is comparing a profile against
data that is structurally always one reporting-lag behind the present moment.
For a signal whose entire value proposition is *intraday timing* (catching a
periodicity deviation as it happens, not after the fact), a persistent lag
shortens the usable reaction window by exactly the delay's length and — if the
periodicity effect being hunted for operates on a timescale shorter than the
delay (e.g., an opening-30-minutes or closing-30-minutes volume pattern
compared against a 15-minute-delayed feed) — could eliminate the tradeable
window entirely. Whether 15 minutes is "structurally fatal" or merely
"reduces edge" depends on the still-undesigned signal's own timescale, which
this licensing audit was not asked to specify. This is offered as reasoning
for the gatekeeper, not as this file's verdict.

---

## Evidence gaps (unresolved this session)

1. ThetaData: exact current monthly price of the **stock** VALUE/STANDARD
   tiers could not be cleanly separated from the **options** pricing table in
   this session's fetches (two sources attached the same $40/$80/$160 numbers
   to differently-labeled tiers).
2. Alpha Vantage: terms_of_service page fetched as an unreadable PDF; no
   verbatim redistribution/commercial-use text obtained.
3. Finnhub: official pricing/rate-limit pages returned only titles/metadata to
   the fetch tool; free-tier intraday-candle access is disputed in public
   GitHub issues with no official resolution found.
4. Twelve Data: official pricing page says free-tier US equities are
   "real-time"; multiple secondary sources say delayed. Not reconciled.
5. Stooq: both the homepage and the dedicated terms.html page returned empty
   content to WebFetch in this session; terms of use are unconfirmed from
   primary text.
6. Nasdaq Data Link: publisher-listing page and terms-of-service page were
   empty/404 respectively in this session; licensing is understood to be
   per-publisher rather than platform-wide, but this was not enumerated.
7. QuantConnect: the ~$60/month Quant Researcher tier figure is a secondary-
   source estimate; the official pricing page rendered "custom pricing" with
   no visible number in this session's fetch.
8. Alpaca: whether free market-data-only API keys require any brokerage
   KYC/funding step was characterized from community sources, not confirmed
   against an official Alpaca account-opening page directly.

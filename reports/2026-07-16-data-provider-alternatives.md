# Options EOD Data-Provider Alternatives — Evaluation

**Author:** research agent (read-only pass)
**Date:** 2026-07-16
**Purpose:** ThetaData subscription ends 2026-07-29. Evaluate renewal vs. alternatives for a forward paper-trading window that needs daily EOD option chains (real NBBO + OI) for 14 underlyings, 3+ months.
**Scope note:** No account was created, nothing was purchased, and no paid-data script was run. Every price carries its source URL and access date. Unconfirmed items are labeled **UNVERIFIED** rather than guessed.

---

## 1. Requirements recap

The frozen fill model (see `data/thetadata_adapter.py`) consumes an 11-column per-contract chain:
`expiration, strike, right, bid, ask, open_interest, iv, delta, gamma, theta, vega`.

Hard requirements for any replacement:

1. **True EOD NBBO bid/ask per contract** — genuine consolidated OPRA best bid/offer at/near session close. **Not** interpolated quotes, model marks, or trade prices. (Greeks/IV *may* be model-computed — the current adapter already ingests ThetaData's Black-Scholes greeks; the "no model quotes" rule binds the **bid/ask**, not the greeks.)
2. **Open interest per contract**, from the OPRA OI report (current adapter joins prior-day-close OI, which is look-ahead-free).
3. **Full chains** (all strikes/expirations) for all 14 names: CRWV, TEM, PLTR, NOW, SMCI, NVDA, AMD, AVGO, IREN, USAR, VST, CEG, MSFT, AMZN (US equities on NYSE/NASDAQ).
4. **EOD snapshots, not intraday.** One snapshot per symbol per trading day.
5. Ongoing **daily** cadence for ≥3 calendar months forward. Deep history (2018+) is a **bonus, not required** — the local cache already holds 2018-2022 in-sample data for the deep-history names.
6. Manageable **integration effort** relative to the existing ThetaData adapter, and **rate limits** that tolerate ~14 full chains/day.

**What the current baseline looks like (from the adapter):** ThetaData supplies NBBO + greeks + IV from its 17:15 ET EOD report via `option_history_greeks_eod`, and OI via `option_history_open_interest` (the ~06:30 ET OPRA report = previous day's close). NBBO is consolidated OPRA. Two bulk calls per symbol-day, merged inner-join into the 11-column schema. This is the reference quote-provenance the frozen fill model was calibrated against.

---

## 2. Local data-preservation check (read-only)

Cache layout is flat parquet files: `.cache/chains/<SYMBOL>_<YYYY-MM-DD>.parquet` (28,091 files total). Latest cached session per target symbol:

| Symbol | Files | Earliest cached | Latest cached |
|--------|-------|-----------------|---------------|
| CRWV | 322 | 2025-04-02 | **2026-07-15** |
| TEM | 511 | 2024-07-01 | **2026-07-15** |
| PLTR | 1449 | 2020-10-06 | **2026-07-15** |
| NOW | 2144 | 2018-01-02 | **2026-07-15** |
| SMCI | 1881 | 2018-01-02 | **2026-07-15** |
| NVDA | 2144 | 2018-01-02 | **2026-07-15** |
| AMD | 2144 | 2018-01-02 | **2026-07-15** |
| AVGO | 2144 | 2018-01-02 | **2026-07-15** |
| IREN | 1055 | 2022-04-29 | **2026-07-15** |
| USAR | 319 | 2025-04-07 | **2026-07-15** |
| VST | 2144 | 2018-01-02 | **2026-07-15** |
| CEG | 1110 | 2022-02-09 | **2026-07-15** |
| MSFT | 2144 | 2018-01-02 | **2026-07-15** |
| AMZN | 2144 | 2018-01-02 | **2026-07-15** |

**All 14 names are current through 2026-07-15** (the last trading session before today, 2026-07-16). Preservation is up to date. Newer-listing names (CRWV, USAR, TEM, IREN, CEG) start at their listing/history-availability date, as expected. No gaps at the tail.

---

## 3. Baseline: ThetaData renewal

| Tier | $/month | History | Includes | Source |
|------|---------|---------|----------|--------|
| Options Value | $40 | 4 yr | "1 minute intervals" — **NBBO quote line not listed at this tier** | [thetadata.net/pricing](https://www.thetadata.net/pricing) (accessed 2026-07-16) |
| **Options Standard** | **$80** | **8 yr (~2018+)** | **"Every NBBO quote reported by OPRA"** + EOD summaries + daily OI + greeks | same |
| Options Pro | $160 | 12 yr (~2014+) | Same as Standard, deeper history | same |

- ThetaData confirms coverage: "Every NBBO quote reported by OPRA," "Daily open interest updates across all strikes and expirations," "1st, 2nd, and 3rd order Greeks," data "Since June 2012" ([thetadata.net/options-data](https://www.thetadata.net/options-data), accessed 2026-07-16).
- **Minimum tier for EOD NBBO + OI = Options Standard ($80/mo).** The $40 Value tier does not list the OPRA NBBO feature line; the forward window only needs going-forward daily EOD, so 8-yr history (Standard) is more than sufficient. Pro ($160) is only needed if 2014-2017 history is wanted (it is not — cache already starts 2018).
- **Integration effort: zero.** The adapter is already built and live-verified against this exact API. Renewal is the null-change option.

---

## 4. Decision table — alternatives

Columns: **NBBO EOD?** (true consolidated bid/ask at EOD) / **OI?** / **Coverage of all 14?** / **$/month** / **History depth** / **Integration effort** (vs. existing ThetaData adapter) / **Disqualifiers / caveats**. All prices accessed **2026-07-16**.

| Provider | NBBO EOD? | OI? | 14 names? | $/month | History | Integration effort | Disqualifiers / caveats |
|----------|-----------|-----|-----------|---------|---------|--------------------|-------------------------|
| **ThetaData (renew)** — [pricing](https://www.thetadata.net/pricing) | Yes — OPRA NBBO, 17:15 ET EOD report | Yes | Yes (full OPRA) | **$80** (Standard) | 8 yr / 12 yr (Pro $160) | **None** (adapter live) | Baseline. Only "disqualifier" is that the sub lapses 2026-07-29. |
| **Polygon.io / "Massive"** — [pricing](https://polygon.io/pricing), [options](https://polygon.io/options) | Yes — OPRA-licensed; EOD NBBO via last-quote in snapshot/quotes endpoints | Yes — "daily open interest" | Yes (100% US options) | **$29** Starter / **$79** Developer / **$199** Advanced | 2 yr / 4 yr / 5+ yr | **Moderate** — REST rewrite; snapshot endpoint returns bid/ask+OI+IV+greeks per contract in one call/underlying; unlimited API calls | Paid tiers below Advanced are **15-min delayed real-time**, but that does **not** block EOD capture (full day's NBBO available after close). If same-session-close timing is wanted without delay, that is Advanced ($199). Rebrand to "Massive" in progress. |
| **marketdata.app** — [pricing](https://www.marketdata.app/pricing/), [options](https://www.marketdata.app/data/options/) | Yes — L1 bid/ask EOD quotes; chain endpoint returns bid/ask/mid/OI/IV/greeks | Yes | Yes (full OPRA universe) | **$30** Starter ($12/mo annual) / **$75** Trader ($30/mo annual) / $125 Quant | Starter 5 yr; Trader+ unlimited; EOD quotes back to 2010 | **Low/Moderate** — REST `options/chain` returns the full 11-field schema in one call; cleanest field match to `CHAIN_COLUMNS` | **Credit accounting is the risk:** "each API request is usually one credit" but a chain is generally billed **per contract returned** — a single NVDA/AMD chain can be thousands of contracts. 14 full chains/day likely exceeds Starter's 10,000 daily credits → **Trader ($75/mo, 100,000/day) is the safe tier.** Exact per-chain credit count **UNVERIFIED** — confirm before committing. NBBO consolidation method vs. OPRA-17:15 **UNVERIFIED**. |
| **ORATS** — [data-api](https://orats.com/data-api), [near-eod](https://orats.com/near-eod-data) | **Near-EOD, not close** — quotes gathered **~14 min before close** to avoid closing-auction wide spreads | Yes | Yes (all US equity/ETF/index options) | **$99–$299** (per coverage/history); +$50 real-time add-on | Back to 2007 | **Moderate** — REST `strikes` endpoint returns quotes+greeks+OI | **Quote-timing mismatch:** 15:46 ET snapshot ≠ ThetaData's 17:15 ET EOD NBBO. This is a *disclosed model-input change*, not a defect, but it shifts the fill reference. Would need to be characterized in the amendment. Pricing band **partly UNVERIFIED** (ranges from search + [flashalpha comparison]; confirm on ORATS pricing page). |
| **CBOE DataShop — Option EOD Summary** — [product](https://datashop.cboe.com/option-eod-summary) | Yes — "NBBO & Size" at **two snapshots: 15:45 ET and EOD**; authoritative (exchange source) | Yes (OI at EOD snapshot) | Yes (US stocks/ETFs/indices via OPRA) | **UNVERIFIED** — not published; contact-sales / cart-config; historically full-market flat-file pricing is materially higher than API subs | Since Jan 2012 | **High** — **flat-file download, not an API.** New ingestion path (scheduled daily-file fetch + parser), not a drop-in for the client-based adapter. Greeks are a paid "Calcs" add-on. | Highest-authority NBBO (exchange itself) and has a genuine EOD snapshot, but delivery model and opaque/likely-high pricing make it the heaviest lift. Price **UNVERIFIED**. |
| **dxFeed** — [site](https://dxfeed.com/), [datarade profile](https://datarade.ai/data-providers/dxfeed/profile) | Likely (OPRA feed, real-time + historical) | Likely | Yes (OPRA) | **UNVERIFIED** — enterprise, not published ("from $19/mo" via 3rd-party retail resellers is not the direct-API price) | Deep | **High** — enterprise feed/API, new SDK integration | Enterprise-oriented; pricing opaque; feed-handler complexity. EOD-snapshot suitability and OI granularity **UNVERIFIED**. Poor fit for a single-analyst EOD paper-trade use case. |
| **Intrinio** — [pricing](https://intrinio.com/pricing), [eod-options](https://intrinio.com/options/eod-historical-options) | Yes — "Close Bid" / "Close Ask" per contract at EOD | Yes — OI + OI change | Yes (US options) | **$150/mo** (Individual plan for EOD historical options) | Standard to 2021-09-27; one-time bulk to 2008 | **Moderate** — REST SDK; EOD options-prices endpoint returns close bid/ask + OI + greeks + IV | Field match is good; price is ~2x ThetaData Standard for equivalent EOD scope. NBBO consolidation detail **UNVERIFIED**. |
| **Tradier** — [market-data docs](https://docs.tradier.com/docs/market-data), [pricing](https://tradier.com/individuals/pricing) | Current chains only — bid/ask + greeks + OI in `/markets/options/chains`; **no historical EOD options API** | Yes (in live chain) | Yes | **$10** Pro / **$35** Pro Plus (data bundled with brokerage account) | **None** (live snapshot only) | **Low** code effort, but requires **funded brokerage account** + a scheduled at-close poll to build EOD snapshots yourself | **Two blockers:** (1) requires opening/funding a brokerage account (an account signup — flagged, not actioned here); (2) no historical options API, so you would only ever have data from the day you start polling forward. Feed is Tradier's consolidated quote, **NBBO-vs-OPRA equivalence UNVERIFIED**. Cheapest, but the account requirement and self-built EOD capture make it operationally heavier than it looks. |

---

## 5. What switching means (honest characterization for the frozen model)

A provider change is a **disclosed amendment to the frozen cost model and, more importantly, to the frozen fill model's data provenance.** The pre-registration froze the fill model against a specific NBBO definition. Two things must be stated plainly in any amendment:

1. **Quote-timing / consolidation differences are a model-input change, not a free swap.**
   - ThetaData's reference is the **OPRA consolidated NBBO from the 17:15 ET EOD report.**
   - **ORATS** deliberately samples **~14 minutes before the close** — different timestamp, tighter spreads (it exists specifically to dodge closing-auction spread blowouts). Fills computed off a 15:46 snapshot are not the same distribution as fills off a 17:15 close. This must be characterized, not silently absorbed.
   - **CBOE DataShop** offers both a 15:45 and an EOD snapshot — closest to a true exchange-authoritative close, but delivered as flat files.
   - **Polygon, Intrinio, marketdata.app, Tradier** each consolidate/timestamp NBBO their own way; where equivalence to the OPRA-17:15 reference is **UNVERIFIED** above, that verification is a precondition of the amendment, not a footnote.
2. **The fill model requires genuine bid/ask (no interpolation/model marks).** Every provider in the table that passes the "NBBO EOD?" column supplies real bid/ask; none of the recommended candidates would introduce interpolated quotes. Greeks being Black-Scholes-computed is unchanged from today (ThetaData already computes them).
3. **Cost-model line item.** Current frozen assumption ≈ $80/mo (ThetaData Standard). A switch changes that number: cheaper (Polygon Starter $29, marketdata Trader $75, Tradier $10-35) or dearer (Intrinio $150, ORATS $99-299, CBOE/dxFeed UNVERIFIED). The amendment should record the new monthly figure and the provenance change together.

**Integration-effort summary (relative to the existing adapter):** ThetaData renew = none · marketdata.app / Polygon / Intrinio = moderate REST rewrite, all 11 fields available per-underlying · ORATS = moderate + timing caveat · Tradier = low code but account + self-built EOD capture · CBOE DataShop / dxFeed = high (new flat-file or enterprise-feed ingestion path).

---

## 6. Owner decision required

This section presents options only. **No purchase decision is made here — per the standing rule, the owner enters/commits any spend.**

**Option A — Renew ThetaData (Standard, $80/mo).** Zero integration risk, zero provenance change, frozen fill model untouched. Highest cost among the cheap tier but the only option that requires no amendment beyond "renewed." Deadline pressure: sub lapses 2026-07-29.

**Option B — Switch to a cheaper OPRA-NBBO REST provider for the forward window.**
- **Polygon/Massive Developer ($79/mo)** or **Starter ($29/mo, 15-min delayed but fine for EOD)** — moderate one-time adapter rewrite, unlimited API calls, full OPRA.
- **marketdata.app Trader ($75/mo, or $30/mo on annual)** — cleanest field match; **must first verify per-chain credit consumption** fits the daily quota (Starter's 10k/day is likely insufficient for 14 full chains).
- Both require verifying NBBO timestamp/consolidation vs. the frozen 17:15 ET OPRA reference and disclosing it as a cost-model + provenance amendment.

**Option C — Higher-authority / deeper-history providers.** Intrinio ($150/mo, EOD close bid/ask + OI), CBOE DataShop Option EOD Summary (exchange-authoritative NBBO, flat-file, **price UNVERIFIED**, high integration effort). Consider only if exchange-grade provenance is judged worth the cost/effort.

**Option D — Tradier ($10-35/mo).** Cheapest, but requires a **funded brokerage account** (an account action, deliberately not taken here) and building EOD snapshots by polling at close (no historical options API). Feed NBBO-equivalence UNVERIFIED.

**Items to verify before any commitment (UNVERIFIED flags to clear):**
- marketdata.app: exact credits charged per full chain → which tier actually clears 14 chains/day.
- ORATS, CBOE DataShop, dxFeed: current direct-subscription pricing (not third-party reseller quotes).
- Any non-ThetaData choice: NBBO consolidation method + snapshot timestamp vs. the frozen OPRA-17:15 reference.

**Timing note:** the ThetaData window ends **2026-07-29**; the local cache is current through 2026-07-15, so there is no immediate data loss, but a decision (renew vs. switch) should land before the lapse to avoid a forward-window gap.

---

*Sources accessed 2026-07-16: [thetadata.net/pricing](https://www.thetadata.net/pricing), [thetadata.net/options-data](https://www.thetadata.net/options-data), [polygon.io/pricing](https://polygon.io/pricing), [polygon.io/options](https://polygon.io/options), [marketdata.app/pricing](https://www.marketdata.app/pricing/), [marketdata.app/data/options](https://www.marketdata.app/data/options/), [orats.com/data-api](https://orats.com/data-api), [orats.com/near-eod-data](https://orats.com/near-eod-data), [datashop.cboe.com/option-eod-summary](https://datashop.cboe.com/option-eod-summary), [dxfeed.com](https://dxfeed.com/), [intrinio.com/pricing](https://intrinio.com/pricing), [intrinio.com/options/eod-historical-options](https://intrinio.com/options/eod-historical-options), [docs.tradier.com/docs/market-data](https://docs.tradier.com/docs/market-data), [tradier.com/individuals/pricing](https://tradier.com/individuals/pricing).*

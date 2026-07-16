# Non-AI diversification candidates — research memo

**Date:** 2026-07-15
**Trigger:** owner request following the deep-research report (7) reconciliation
(`reports/2026-07-15-deep-research-7-reconciliation.md`, Section 3.4), which
found that adding more AI-adjacent story names *raises* the owner's standing
single-factor concentration (AI/semis/power) instead of lowering it.
**Method:** three parallel research subagents (Sonnet), one sector lane each —
healthcare, financials, consumer/industrials/energy/materials — screened
against the reconciliation's three criteria: (1) non-AI primary revenue
driver, (2) liquid monthly options, (3) low fundamental overlap with the
existing AI cluster. Synthesized and reviewed by the orchestrating session.

**Scope status: RESEARCH ONLY — PARKED.** Nothing here changes `config.py`,
the H7 watchlist, or any registered hypothesis. Per the scope guard, ticker
selection is an owner decision; this memo exists so that decision can be made
from screened evidence instead of intuition. Parking-lot entry added the same
day.

**Claim discipline:** every liquidity number below is **web-asserted**
(secondary aggregators — MarketChameleon, Barchart, OptionCharts, Benzinga —
not OCC/exchange official). None was cross-checked against the repo's
ThetaData parquet cache. The owner is fluent in options; the point of the
labels is provenance, not tutoring.

---

## Consolidated candidates (12 names, 3 lanes)

| Ticker | Lane | Real earnings driver | Fit | Weakest link |
|---|---|---|---|---|
| UNH | Healthcare — managed care | Medical-loss ratio, MA rates, regulation | 8/10 | Violent idiosyncratic tail risk (DOJ, MA cuts) |
| LMT | Defense | Procurement backlog, appropriations | 8/10 | Budget politics; cleaner than RTX/NOC on AI-narrative creep |
| XOM | Energy — integrated O&G | Crude/gas price × volume, crack spreads | 8/10 | Chain-wide 15% avg spread stat (likely far-OTM artifact — verify ATM) |
| V | Financials — payments | Payment volume × take-rate | 8/10 | Liquidity claim incomplete this pass |
| PGR | Financials — P&C insurance | Underwriting margin, combined ratio | 8/10\* | Thinnest options market of the financials set; monthly 8-K cadence complicates post-earnings windows |
| JPM | Financials — money-center bank | NII, credit provisions, deal flow | 7/10 | Minor AI-capex debt-syndicate fee exposure |
| BAC | Financials — money-center bank | NII, consumer banking | 7/10 | Same syndicate caveat; ~redundant with JPM (pick one) |
| AXP | Financials — closed-loop cards | Affluent-consumer spend + card NII | 7/10 | Second-order wealth-effect link to AI-driven equity gains |
| LLY | Healthcare — pharma | GLP-1 franchise demand/capacity | 7/10 | Crowded growth trade; still risk-on beta |
| VRTX | Healthcare — biotech | CF franchise + FDA catalysts | 7/10 | Binary FDA gap risk off-cycle from earnings |
| COST | Consumer | Membership retail | 7/10 | ~$900 share price → coarse strike spacing; liquidity unverified |
| NEM | Materials — gold | Spot gold (real rates, dollar, haven) | 7/10 | Weakest-verified liquidity; likely non-penny quotes |

Also screened, weaker: MCD 7/10 (clean driver, no numeric liquidity), PFE 6/10
(possibly too low-beta to generate the post-earnings move H6-style lanes need),
HCA 6/10 (cleanest story, most doubtful liquidity), DE 6/10 (AI-as-product-
feature, not AI-infrastructure — needs owner's judgment call).

**Portfolio-level observation (Inference):** NEM is the only candidate whose
driver (gold) plausibly moves *against* the risk-on AI complex; everything
else diversifies the earnings driver but keeps broad-market beta. UNH/VRTX
carry genuinely idiosyncratic (regulatory/FDA) catalysts. Financials swap AI
exposure for rate exposure — a different factor, which is the point, but it
should be stated as a new factor, not "no factor."

## Crossover traps — screened and REJECTED

This list is the memo's most valuable output: names that look like
diversification but are the same AI trade in costume.

- **FCX** (copper) — 2026 rally explicitly narrated as AI data-center copper
  demand. [web-asserted]
- **CAT** — 2 GW generator deal for hyperscale AI backup power; re-rating on
  AI power demand. [web-asserted]
- **PWR** — backlog/guidance attributed to hyperscaler grid buildout.
  [web-asserted]
- **Uranium/nuclear names** (CCJ-type, royalty vehicles) — the entire 2026
  narrative is Big-Tech nuclear for AI power; this is the owner's VST/CEG
  factor. [web-asserted]
- **ISRG** — da Vinci 5 compute built with NVIDIA; markets AI analytics as a
  growth driver. [web-asserted]
- **BX / APO / KKR** — now materially AI-capex financiers ($35B Broadcom
  platform, $10B+ AI data-center vehicles). [web-asserted]
- **ICE** — revenue is fine, but the public narrative is saturated with AI
  deployment; sentiment-linkage risk. Soft reject. [web-asserted]
- **BLK** — AUM fees carry embedded beta to AI-driven mega-cap index weight.
  [Inference]
- **RTX / NOC** — legitimate defense drivers but higher AI-narrative creep
  than LMT; deprioritized, not rejected.
- **REGN** — soft reject (AI/computational-biology marketing angle + Eylea
  patent-cliff noise); flagged for owner review.

## Verification gaps (all must close before any name enters scope)

1. **Liquidity is unverified.** Every OI/spread/volume figure is web-asserted.
   The vetting bar is the one the H7 names cleared: near-the-money OI and
   spread at monthly expiries from real chain data.
2. **Correlation is asserted, not measured.** No return-correlation
   computation against the four-name core was run. If pursued, compute it
   from cached/free OHLCV (the repo already has Yahoo OHLCV tooling) — no
   paid data needed for this step.
3. **Earnings cadence** claims are Inference; dates would need the same
   provenance discipline as the H7 earnings store (confirmed vs. estimated).
4. **Time-sensitive:** the ThetaData subscription ends ~2026-07-29. If the
   owner wants real chain-liquidity vetting for any shortlist, the cheap
   window is before the sub lapses; each pull needs per-pull owner approval
   per standing policy.

## What this memo does NOT do

It does not add tickers, does not propose frozen parameters, does not touch
any live hypothesis, and does not claim any of these names has edge —
"no edge after costs" remains a successful outcome for anything eventually
tested. Activation path, if ever: owner shortlist → liquidity vetting against
real chain data → correlation check → a NEW pre-registered hypothesis (or an
owner-logged scope override, as H7 was) with owner-typed frozen numbers.

**Review date:** at the first H5/H6 verdict, or the 2026-10-06 quarterly
audit, whichever comes first (same gate as the other parked ideas).

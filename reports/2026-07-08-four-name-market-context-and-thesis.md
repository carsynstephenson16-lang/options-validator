# Four-name market context + options thesis — 2026-07-08

Descriptive research brief, NOT a hypothesis and NOT a verdict input. Compiled
by Claude (web research, sources linked). Every price is a retail quote-page
figure, approximate to cents. Nothing here amends the frozen
H5_ENTRY_TRIGGER_PREREG rule; it only describes the tape around it.
Label for the whole document: **web-sourced, secondary data; verify against
cached chains / IR pages before any decision.**

## Snapshot vs frozen triggers (prices as of 2026-07-08 close)

| Name | Close | Frozen trigger | Distance | Next earnings |
|------|-------|----------------|----------|---------------|
| VST  | ~$152.32 | ≤ $140 | +8.8% above | **Aug 7, 2026 — company-confirmed** (same morning as July jobs report) |
| AMZN | ~$242.22 | ≤ $220 | +10.1% above | Jul 30, 2026 — **estimated**, not company-confirmed (trackers conflict) |
| CEG  | ~$244.52 | (no trigger) | near 52-wk low $228.63; ~-35% H1 2026 | Aug 6, 2026 — IR-confirmed |
| MSFT | ~$382.11 | (no trigger) | ~-20% YTD | Jul 29, 2026 AMC — company-confirmed 2026-07-08 |

Repo entry_watch (run 2026-07-08, closes cache stale at 2026-06-30):
VST WAIT (price + LEAPS liquidity unmet; IV-rank 0.47 vs max 0.5),
AMZN WAIT (price + IV-rank 0.58 unmet).

## VST specifics

- 52-wk range $132.66–$219.82; ~-6% YTD, ~-30% off the high.
- 2026 pullback pattern: sharp, short-lived flushes — 2026 low ~$134.71 on
  May 19, back to ~$156 by May 22. The ≤$140 trigger zone WAS touched this
  year, but only for days. (Single-source price history; re-verify before
  relying on exact dates/levels.)
- Catalysts: Meta 20-yr nuclear PPAs (2,600+ MW, deliveries from late 2026);
  Cogentrix ~5.5 GW gas completed; KKR/Nvidia/KIA $10B "Helix" AI-infra
  partnership (June 2026); record Q1 adj. EBITDA ~$1.5B.
- Options: 30-day mean IV ≈ 59.5% vs 30-day realized ≈ 46.2% (AlphaQuery,
  2026-07-07; mid-tier source, indicative only). Earnings premium only
  partially inside that window. No credible IV-rank source found — compute
  IVR from our own features, never from the web.

## AMZN specifics

- ~$200B 2026 capex plan, majority AWS; Trainium3 reportedly ~fully
  subscribed (company-asserted); Bloomberg 6/18: **early** talks to sell
  Trainium to third parties, no deal signed; $25B+ bond sale ~7/7 with
  soft demand noted in press.
- 52-wk low $196 — the ≤$220 zone traded within the past year (date unverified).

## CEG / MSFT one-liners

- CEG: weakest of the four (-35% H1), Walmart 15-yr nuclear PPA, NY license
  renewals to 2049; Street Q2 ~$2.24 EPS (analyst estimate).
- MSFT: deep de-rating year (52-wk $349–$555); ~4,800 layoffs; $2.5B
  "Microsoft Frontier" enterprise-AI unit; shifting Office to in-house models.

## Macro calendar, next ~5 weeks (Fed + OMB official schedules)

- Jul 14 CPI (June) · Jul 15 PPI
- Jul 28–29 **FOMC** (no SEP) — MSFT earnings Jul 29 AMC, same window
- Jul 30 Q2 GDP advance + PCE — same day as AMZN's estimated earnings
- Aug 7 **Jobs report + VST earnings, same morning**
- Aug 12 CPI (July) · next FOMC Sep 15–16

## Thesis (descriptive, falsifiable framing — not advice, not a signal)

1. **The frozen pullback-entry design is consistent with how these names
   actually traded in 2026**: VST's flushes into the $130s reversed within
   days, so a standing limit-style trigger (price AND IV-rank AND liquidity)
   is the mechanism that can catch it; discretionary chasing cannot.
2. **Pre-earnings LEAPS buying is structurally paying up**: IV ≈ 59% vs
   realized ≈ 46% means the pre-earnings option is priced rich relative to
   recent movement. The IVR ≤ 0.5 gate exists precisely to block buying a
   0.70-delta LEAPS when its vol is expensive. "Stock might boom on earnings"
   is a direction bet layered on an expensive-vol entry — two ways to be
   right needed, one way to pay twice.
3. **Event congestion late July / early Aug**: FOMC 7/28–29, GDP+PCE+AMZN
   7/30, jobs+VST 8/7, CPI 8/12. Elevated IV into these dates favors the
   income lanes (CC/CSP against declared lots, per H5 rules) over fresh
   long-vol entries, subject to the frozen AMBER-flag earnings handling.
4. **Exit framing already in force**: income cycles per H5 never sell a call
   below cost basis (or below the PMCC safety strike); LEAPS roll at ≤90 DTE.
   No new exit rules are asserted here.

What would falsify the pullback-entry premise: VST/AMZN grinding higher
without a ≥8–10% flush for the remainder of the forward window — the trigger
then simply never fires and the book stays smaller. That outcome is
acceptable by design; it is not a reason to raise the trigger after the fact.

## Sources

VST earnings PR: stocktitan.net/news/VST/vistra-to-report-second-quarter-results-on-aug-7-27cmv7htv7is.html · investor.vistracorp.com/news
VST price/history/news: stockanalysis.com/stocks/VST/ (+/history/) · gurufocus.com/news/8946183
Meta PPA: utilitydive.com/news/meta-nuclear-deal-oklo-vistra-terrapower-ai-data-centers/809215/
Cogentrix: enverus.com/blog/vistra-doubles-down-on-data-centers/
AMZN: stockanalysis.com/stocks/AMZN/ · nasdaq.com/market-activity/stocks/amzn/earnings · convergedigest.com/amazon-ties-200-billion-2026-capex-plan-to-ai-aws-and-custom-silicon/ · SEC 8-K amzn-20260331xex991
CEG: investors.constellationenergy.com/events (Aug 6 call) · stockanalysis.com/stocks/CEG/
MSFT: marketscreener.com/news/microsoft-announces-quarterly-earnings-release-date-ce7f5ed9dd8cf223 · stockanalysis.com/stocks/MSFT/
VST IV: alphaquery.com/stock/VST/volatility-option-statistics/30-day/iv-mean (2026-07-07)
Macro: federalreserve.gov/monetarypolicy/fomccalendars.htm · OMB CY2026 release schedule (whitehouse.gov PDF)

Conflicts/could-not-verify log: AMZN 7/30 date is tracker-estimated;
Investing.com's CEG 7/30 and MSFT 7/28 dates conflict with IR/company pages
(IR governs); VST May-low path single-sourced; no tier-1 IV/IVR source found.

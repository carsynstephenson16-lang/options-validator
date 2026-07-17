# VST / CEG Pre-Earnings Public Footprints — Case Study
**Date:** 2026-07-16 · **Author:** research agent (Claude) · **Status:** descriptive study, NOT a trade recommendation
**Question:** what PUBLIC, trackable footprints historically appeared BEFORE VST/CEG earnings prints, and could a disciplined observer have anticipated the surprise?
**Honesty rule applied:** only signals provably public before the print count as signals. Everything else is labeled hindsight. "No usable signal" is an acceptable answer — and is, in fact, largely the answer for the prints themselves.

**Price-data convention.** Both companies release earnings **before market open (BMO)**, so the "reaction" is the **same-day** close-to-close move (prior close → report-day close); next-day move also shown where informative. All % moves below were computed by this agent from Yahoo Finance chart-API adjusted daily closes (query1.finance.yahoo.com/v8/finance/chart/{VST,CEG}), pulled 2026-07-16. A subagent cross-check found consistent magnitudes where press coverage exists (e.g., CEG −11% Nov 4 2024 per Motley Fool vs −12.5% computed; CEG +22% Sept 20 2024 per IBKR/Barchart vs +22.3% computed). Single-source price risk is flagged in section (e).

---

## (a) Event table

### VST — last 9 prints (8-window = Aug 2024 → May 2026; May 2024 shown as context)

Report dates anchored to SEC 8-K Item 2.02 filings (EDGAR submissions API, CIK 0001692819, accessed 2026-07-16).

| Quarter | Report date (8-K 2.02) | Same-day move | Next-day move | Dominant driver per VST's own release |
|---|---|---|---|---|
| Q1 2024 | 2024-05-08 | **+9.1%** | +4.5% | Raised Energy Harbor synergy + consolidated adj EBITDA expectations (S&P 500 inclusion same day) — IR release "Raises Expectations for Energy Harbor and Consolidated Adjusted EBITDA," 8-K accession 0001193125-24-133760 |
| Q2 2024 | 2024-08-08 | **+6.9%** | −0.6% | Raised 2025 adj EBITDA midpoint by $200M; Microsoft/Amazon solar PPAs; Comanche Peak 20-yr NRC license extension; PJM capacity windfall quantified 9 days earlier (see below) — 8-K 0001193125-24-196470 |
| Q3 2024 | 2024-11-07 | **+7.6%** | +4.5% | Raised & narrowed FY24 + initiated above-consensus 2025 guidance ($5.5–6.1B); +$1.0B buyback — 8-K 0001193125-24-252608 |
| Q4/FY 2024 | 2025-02-27 | **−12.3%** | +2.8% | Beat original FY24 guidance but only *reaffirmed* (did not raise) FY25 — sell-the-reaffirm amid post-DeepSeek AI-power de-rating; no new data-center deal delivered — 8-K 0001193125-25-037636 |
| Q1 2025 | 2025-05-07 | −3.7% | +1.0% | GAAP net loss $268M + negative FCF despite record-Q1 adj EBITDA $1.24B; guidance reaffirmed (−6.2% two-day) — 8-K 0001193125-25-114425 |
| Q2 2025 | 2025-08-07 | +2.4% | −1.7% | Headline EPS miss (outage/depreciation costs) — gapped ~−4.9% pre-market, then REVERSED to +2.4% close on raised 2026 midpoint opportunity (>$6.8B) and ~100%/95% hedged 2025/2026 disclosure — 8-K 0001193125-25-174942 |
| Q3 2025 | 2025-11-06 | −2.5% | +3.5% | "Narrows 2025 Guidance, Initiates 2026 Guidance"; earnings/revenue miss vs consensus, guidance maintained — 8-K 0001193125-25-268033 |
| Q4/FY 2025 | 2026-02-26 | +0.8% ⚠️conflict | −1.7% | Adjusted EPS miss ($2.13 vs ~$2.33 consensus) vs record 2025 EBITDA ($5,912M) + 2026 guidance. **Magnitude conflict:** computed closes say +0.8%/−1.7%, but Zacks/TradingView report "slid more than 5%" and CoinCentral "−13%" (likely intraday-from-highs and/or follow-through incl. an executive share-sale story). UNVERIFIED which convention those figures use; computed close-to-close retained as canonical here |
| Q1 2026 | 2026-05-07 | −2.7% | −4.0% | EPS beat ($2.87 vs ~$2.21) but selloff on buyback-completion/capital-allocation concern, FERC co-location scrutiny, ~3.5x ND/EBITDA; −2.74% per OptionSlam (matches computed), ~−8.2% on the week — 8-K 0001692819-26-000011 |

Big-reaction VST prints (|same-day close-to-close| ≥ ~5%): **2024-05-08, 2024-08-08, 2024-11-07, 2025-02-27.** All four cluster in the first year of the AI-power narrative; the last five prints were ≤ 4% same-day close-to-close (though Q1'25, Q4'25, and Q1'26 built into larger multi-day declines, and Q2'25 had a >7pp intraday reversal). Pattern worth noting: **all three 2024 quarterly prints ripped higher; both full-year (Feb) prints produced the deepest drawdowns despite in-line/record headline results — the annual reports were the sell-the-news events.**

### CEG — last 8 prints (lower depth)

Anchored to 8-K Item 2.02 filings, CIK 0001868275.

| Quarter | Report date | Same-day move | Dominant driver per CEG's own release |
|---|---|---|---|
| Q2 2024 | 2024-08-06 | **+6.5%** | Raised FY24 EPS guidance midpoint; PJM auction upside |
| Q3 2024 | 2024-11-04 | **−12.5%** | Guidance narrowed upward, Microsoft/Crane PPA recapped — but tape driven by FERC's Nov 1 rejection of the Talen/Amazon co-location amendment (see (b)) |
| Q4/FY 2024 | 2025-02-18 | +2.6% | Record FY24 adj EPS $8.67; Calpine pending; dividend +25% |
| Q1 2025 | 2025-05-06 | **+10.3%** | In-line Q1, reaffirmed FY25 $8.90–9.60, Calpine on track (also a post-tariff-selloff rebound tape) |
| Q2 2025 | 2025-08-07 | −0.6% | Meta/Clinton PPA (announced Jun 3) + Calpine approvals; adj EPS $1.91 |
| Q3 2025 | 2025-11-07 | +2.0% | Adj EPS $3.04 (slight miss vs ~$3.11); narrowed FY25 upward |
| Q4/FY 2025 | 2026-02-24 | **+6.4%** | FY25 adj EPS $9.39; Calpine integration; dividend +10%; multi-year FCF outlook |
| Q1 2026 | 2026-05-11 | −1.3% | Beat ($2.74 vs $2.59 est); reaffirmed FY26 $11–12 — sold off anyway |

**First structural observation:** for both names, the biggest *stock* moves of 2024–2026 were mostly NOT on earnings days: CEG +22.3% (Microsoft/TMI, 2024-09-20), CEG +25.2% (Calpine, 2025-01-10), CEG −20.8% / VST −28.3% (DeepSeek, 2025-01-27), VST +14.8% (2024-07-31, day after PJM BRA results), VST +16.6% (2024-09-20, sympathy with CEG/TMI). The prints are second-order events in these names; the deal/regulatory tape is first-order.

---

## (b) Pre-print footprint reconstruction — big-reaction quarters

### VST Q2 2024 (print 2024-08-08, +6.9%) — the cleanest genuine footprint in the sample
- **2024-07-30:** PJM posted 2025/26 Base Residual Auction results — RTO clearing price $269.92/MW-day, ~9x the prior auction. **Same day, VST filed an 8-K (accession 0001193125-24-189392) quantifying its own award: 10,255 MW cleared at weighted-avg $273.45/MW-day** (~$1.02B/yr of capacity revenue for delivery year June 2025–May 2026, computable as MW × price × 365 from the 8-K's own zone table). [SOURCED: 8-K (2024-07-31 filed, event 2024-07-30), URL: https://www.sec.gov/Archives/edgar/data/1692819/000119312524189392/d828589d8k.htm, accessed 2026-07-16]
- **2024-07-31:** VST +14.8% (the auction reaction).
- **2024-08-08 (9 days later):** print +6.9% on raised guidance. The auction told you the *direction* of the guidance revision with 9 days' lead — but the stock had already repriced +15% on the auction itself. The residual +6.9% was the size of the guidance raise, which no public data quantified in advance.
- CEG ran the same sequence: its own 8-K on 2024-07-30 (Item 8.01, accession 0001868275-24-000045), then +6.5% at its 2024-08-06 print.

### VST Q3 2024 (print 2024-11-07, +7.6%)
- **2024-09-20:** CEG/Microsoft TMI announcement; VST +16.6% same day in sympathy — the market repriced the whole nuclear fleet for data-center PPAs.
- **2024-09-24 (approx.):** VST 8-K (Items 1.01, 8.01) — Vistra Vision minority-interest buy-in period [direction-relevant but not independently verified in detail here — UNVERIFIED detail].
- **2024-11-01 (Fri):** FERC rejected the Talen/Amazon Susquehanna ISA co-location amendment — public, negative for co-location economics. VST still printed +7.6% on 11/7 (its driver was guidance, not co-location).
- Verdict: the pre-print footprints here were *sector narrative* items, not VST-quarter fundamentals. Guidance initiation for 2025 (the actual driver) had no public precursor.

### VST Q4 2024 (print 2025-02-27, −12.3%) — the case against footprint trading
- **2025-01-27:** DeepSeek selloff, VST −28.3% in one day. The narrative had already cracked a month before the print.
- The print itself **beat and reaffirmed guidance** (per VST's release and coverage: "Vistra stock falls, erasing earlier gains after Q4 earnings," Yahoo Finance) — and the stock fell 12.3% anyway. No public pre-print signal pointed down; the move was expectations-and-narrative (no new Comanche Peak deal announced, market wanted one). **Honest label: no usable signal existed for this, the largest VST print move in the sample.**

### CEG Q3 2024 (print 2024-11-04, −12.5%) — the one genuinely leading regulatory footprint
- **2024-11-01 (one trading day before the print):** FERC's co-location rejection was public. CEG fell into and through its Nov 4 print; press coverage attributed the "crash 11%" to FERC + valuation, not the results (Motley Fool, 2024-11-04). A disciplined observer had ~1 trading day to act on a public, directional, thesis-relevant ruling — but it was a tape event, not an earnings predictor; it would have told you nothing about the (fine) Q3 numbers.

### CEG Q1 2025 (print 2025-05-06, +10.3%)
- No single public footprint. The +10.3% is best read as a rebound print (tape had sold off hard on April tariffs), in-line results, Calpine reaffirmation. Hindsight-only.

### CEG Q4 2025 (print 2026-02-24, +6.4%)
- Calpine had closed ~2026-01-07 (8-K accession 0001104659-26-001780) — publicly known 7 weeks ahead; first print consolidating it, plus dividend raise. The *existence* of accretion was foreseeable from the closing 8-K; its *size vs consensus* was not. Partial credit at best.

### The deal announcements as "prints of their own"
- CEG/Microsoft TMI: 8-K + PR **2024-09-20** (accession 0001868275-24-000058), +22.3% same day; next print 2024-11-04, 45 days later — deal fully priced by then. [SOURCED: https://www.sec.gov/Archives/edgar/data/1868275/000186827524000058/ceg-20240920.htm, accessed 2026-07-16]
- CEG/Meta Clinton: announced **2025-06-03**; CEG ≈ flat (−0.1%) — largely anticipated. Same event class, opposite surprise content.
- **VST/Comanche Peak: 8-K 2025-09-29** (accession 0001193125-25-221774) — 20-yr PPA (options to +20 yrs) with "a large, investment grade company" (widely reported as AWS) for 1,200 MW of nuclear power, delivery starting Q4 2027, full ramp by 2032. **VST fell −4.5% that day.** The long-awaited deal *underwhelmed* on disclosed economics. [SOURCED: https://www.sec.gov/Archives/edgar/data/1692819/000119312525221774/d43667d8k.htm, accessed 2026-07-16]
- Direction of this event class across three occurrences: **+22%, ~0%, −4.5%.** Knowing a deal is coming does not tell you the sign.

### Insider Form 4 activity (SEC EDGAR, owner=only atom feeds, both CIKs, accessed 2026-07-16)
- **VST:** filings cluster on calendar events — late-Feb (post-10-K), early-Mar, and ~May 19 batches of 6–10 filings on a single day in both 2025 and 2026 (annual grant/vesting cycles). The one striking pattern: **an unbroken every-2-3-trading-days run of Form 4s from 2025-09-12 through 2025-10-31** — inspected filing 0001268406-25-000021 (2025-10-06): **CEO James Burke, transaction codes M (option exercise @ $19.68) + S (sale @ ~$204–206)** — i.e., a pre-scheduled exercise-and-sell program running into the Nov 6 Q3'25 print (which came in soft, −2.5%). Because 10b5-1-style programmatic selling carries no discretionary information, this is **not admissible as a signal**, and reading it as one is exactly the hindsight trap this study is supposed to avoid.
- **CEG:** near-perfect quarterly clockwork (Jan 2–3, Apr 2, Jul 1–2, Oct 2 batches = director comp grants) plus post-earnings February batches. No discretionary pre-print pattern found in the window examined.
- **Verdict: no informative pre-print insider footprint in either name over this window.**

### Congressional trades
- Sparse and small: ~11 VST trades by 4 members across the whole period (~$1.7M buys / $24K sells, per pelositracker.app, accessed 2026-07-16); a pair of opposing small CEG trades Apr 2026. STOCK Act disclosure lag (up to 45 days) means these publish *after* the window in which they could inform a print. **Verified sparse, confirmed useless pre-print.**

### EIA generation data
- EIA's Electric Power Monthly publishes ~the end of month M+2 (data for June appears late August). A quarter ending June 30 is reported on Aug 7; EPM covering June isn't out yet. **The publication lag structurally guarantees EIA data cannot cover the full quarter before the print.** Hindsight-only by construction. [Schedule characterization from EIA release cadence, eia.gov/electricity/monthly/ — lag figure approximate, not re-verified to the day; UNVERIFIED detail.]

---

## (c) Contract paper trail: award → filing → revenue → print

Ranked by how early and how *quantified* the paper trail is:

**1. PJM capacity auction awards — the gold standard of early, computable revenue.**
- **T+0:** PJM posts BRA results (2024-07-30 for DY2025/26 at ~$269.92/MW-day RTO; 2025-07-22 for DY2026/27 at $329.17/MW-day — the price cap).
- **T+0 (same day):** VST files an 8-K with its OWN cleared MW and weighted-average price, by zone (10,255 MW @ $273.45 in 2024; ~10,314 MW @ $329.17 in 2025). Annual capacity revenue is arithmetic from the 8-K table. CEG files the same pattern (8-Ks 2024-07-30, 2025-07-22).
- **T+9 to T+16 days:** next earnings print, where the award shows up as raised/initiated *guidance* (not yet revenue).
- **T+11 to T+23 months:** the actual revenue recognition, spread over the June-to-May delivery year.
- The paper trail leads the *revenue* by ~1–2 years and the *guidance event* by ~1–2 weeks. But the *stock* reprices on auction day (+14.8% next day in 2024, +5.8% next day in 2025), leaving unclear residual for the print.

**2. Data-center / nuclear PPAs (8-K Item 8.01 + press release).**
- Signing 8-K discloses MW, term, and start window but usually NOT price (CEG/Microsoft ~$785M/yr by 2030 was a Bloomberg estimate, not a filing number; VST's 8-K gave 1,200 MW and "consistent with previously communicated 2026 expectation" — deliberately unquantified).
- Revenue starts **2–7 years after signing** (Crane ~2027–28; Comanche Peak Q4 2027 ramp to 2032). Enormous lead time to revenue; near-zero lead time as a tradeable pre-print signal because the announcement is itself the surprise, absorbed same-day.
- Contracted-backlog build-up then appears in 10-K commitments/hedging disclosures — but at annual granularity and without deal-level pricing.

**3. Hedge-percentage disclosures (quarterly, in the earnings release/10-Q cycle).**
- VST's own releases: ~100% of expected generation hedged for 2025 and ~95% for 2026 (as of 2025-08-01); ~98%/96%/70% for 2025/26/27 (as of 2025-10-31); ~100%/84%/58% for 2026/27/28 (as of 2026-02-18); ~98%/89%/65% for 2026/27/28 (as of 2026-05-01). [SOURCED: VST Q2'25/Q3'25/Q4'25/Q1'26 releases via 8-K exhibits, e.g. https://www.sec.gov/Archives/edgar/data/1692819/000119312525174942/d929557dex991.htm, accessed 2026-07-16]
- **Consequence (answers task 4 directly): current-year and next-year EBITDA is essentially locked before the year begins.** Spot ERCOT scarcity days, PJM forwards, weather — none of it maps to the next 1–4 prints in any material way. Spot/forward power prices inform the *2–3-years-out* re-rating (the 58–70%-unhedged tail), which is a valuation input, not an earnings-surprise input. Anyone backtesting "hot ERCOT summer → VST beat" is fitting noise against a hedge book that was disclosed, quarterly, to be ~full.

---

## (d) Signal scorecard

| Signal | Typical lead vs print | Direction consistency (this sample) | Verdict |
|---|---|---|---|
| PJM BRA result + same-day company 8-K (cleared MW × price) | 9–16 days to next print; 11–23 months to revenue | 2/2 positive-clear → positive print (+6.9%, +2.4%), but stock repriced on auction day itself (+14.8%, +5.8% next day) | **Usable — but for the auction-day event, only weakly for the print.** The one footprint that is public, quantified, per-company, and scheduled. |
| Data-center PPA 8-Ks (TMI, Meta/Clinton, Comanche/AWS) | Announcement IS the event; 38–45 days to next print (fully priced by then) | +22.3% / −0.1% / −4.5% — **inconsistent** | **Hindsight-only as an earnings signal.** First-order for the stock, zero residual for the print. |
| Regulatory rulings (FERC co-location, Nov 1 2024) | ~1 trading day before the CEG print it contaminated | n=1 | **Weak/unbankable.** Genuinely public and leading, but unscheduled and rare. |
| Spot/forward power prices (ERCOT/PJM) | n/a for prints | n/a | **Not usable for prints — hedge book (~95–100% current+next yr) structurally disconnects prints from spot.** Relevant only to out-year re-rating. |
| EIA generation data | Negative lead (publishes after the print) | n/a | **Not usable by construction** (~2-month lag). |
| Insider Form 4 (60-day pre-print windows) | n/a | Calendar grants + 10b5-1 programs only | **Not usable.** The one visible "pattern" (Burke Sep–Oct 2025 selling) is programmatic. |
| Congressional trades | Disclosure lag ≤45 days, sparse | n/a | **Not usable — verified, not assumed.** |
| Guidance-revision direction (the actual print driver) | 0 days — revealed at the print | The four big VST prints were all guidance/expectations events | **No public precursor existed.** This is the honest core finding. |

**Bottom line:** across 9 VST and 8 CEG prints, the earnings-day surprises were dominated by guidance revisions and narrative/expectations (Feb 2025: beat + reaffirm → −12.3%), which no provably-public footprint anticipated. The public paper trail (PJM 8-Ks, PPA 8-Ks) is real, early, and quantified — but the market consumes it same-day, leaving little to harvest at the print. **For an options program, the tradeable insight is inverted: the scheduled PJM auction-result date and unscheduled deal 8-Ks are the vol events comparable to prints, and the prints themselves have become progressively smaller-move events (VST: last five prints ≤4% same-day vs first four ≥6.9%).**

---

## (e) How this could be lying

1. **Small n, one regime.** 9+8 prints, all inside a single AI-power-narrative bull-then-wobble regime (mid-2024→mid-2026). The "PJM 8-K is usable" verdict rests on n=2 auctions, both of which cleared UP. A down auction has never been observed in this sample; direction consistency of 2/2 is nearly meaningless.
2. **Pattern-matching known outcomes.** I knew the outcomes (TMI +22%, DeepSeek crash, Feb-2025 −12%) before reconstructing the footprints. Every footprint list above was assembled by someone who could not un-know the answer. The only structurally protected claims are the negative ones (EIA lag, disclosure lag, hedge percentages), which are properties of publication calendars, not of the sample.
3. **Hedge-book opacity cuts both ways.** "~100% hedged" is management's characterization of *expected generation* at a point in time; hedge effectiveness, collateral effects, and retail-segment offsets are not visible. The claim "spot doesn't map to prints" is directionally supported by the disclosures but is not verifiable at position level; a quarter where hedges misbehave would break it without warning.
4. **Same-day vs next-day attribution.** BMO releases mean the "reaction" day also contains everything else that happened that day (Nov 4 2024 CEG print is contaminated by the Nov 1 FERC ruling; May 6 2025 CEG print sits on a rebound tape). Single-day close-to-close moves attribute the whole tape to the print.
5. **Single price source.** All % moves computed from Yahoo chart-API adjusted closes on one pull (2026-07-16). Cross-checked against press-reported figures on 3 events (consistent), but the other ~20 cells are single-source. A subagent's independent attempt produced conflicting values for four CEG cells (marked UNVERIFIED in its output); I used my own computed values throughout for internal consistency.
6. **Survivorship of the question itself.** VST/CEG are being studied *because* they had spectacular moves. The footprint classes graded here (capacity auctions, PPA 8-Ks) would grade far worse on the median power name that never got a deal — the study design imports the outcome.
7. **Unverified cells.** VST 2024-09-24 8-K contents (detail); EIA publication day-of-month; exact CEG single-day moves for Feb 2025/Aug 2025/Nov 2025/Feb 2026 per the subagent (my computed values fill them, single-source). Congressional-trade counts from pelositracker.app (aggregator, not primary STOCK Act filings). **VST 2026-02-26 magnitude is actively conflicting** (computed +0.8% close-to-close vs press ">5% slide"/"−13%"); the computed pipeline is validated against OptionSlam on 2026-05-07 (−2.7% vs −2.74%), so close-to-close is retained, but if the press figures reflect open-to-low intraday action, the "prints have gotten smaller" claim in (d) weakens for that date. Resolve with a second canonical daily-close source before any production use.
8. **Cross-checked aggregator noise (examples caught).** Two search snippets claimed VST moved "+1.12%" on 2025-02-27 (actual: −12.3% — both this agent's computed closes and the subagent's stockanalysis.com pull agree); one snippet claimed CEG "+48% to $254.98" on 2024-09-20 (actual: +22.3% to ~$252, the $254.98 being intraday); one outlet (TIKR) headlined a "14% jump" for VST Q1'26 that was a trailing-week figure, not the (negative) earnings reaction. Aggregator/news percentage claims for single days are unreliable without a stated convention — a finding in itself for any footprint backtest.

---

## Key sources (all accessed 2026-07-16)
- SEC EDGAR submissions API: https://data.sec.gov/submissions/CIK0001692819.json (VST), https://data.sec.gov/submissions/CIK0001868275.json (CEG) — all report and 8-K dates
- VST PJM 2025/26 award 8-K: https://www.sec.gov/Archives/edgar/data/1692819/000119312524189392/d828589d8k.htm (10,255 MW @ $273.45/MW-day)
- VST PJM 2026/27 award 8-K: https://www.sec.gov/Archives/edgar/data/1692819/000119312525162749/d907220d8k.htm (~10,314 MW @ $329.17/MW-day)
- VST Comanche Peak PPA 8-K (2025-09-29): https://www.sec.gov/Archives/edgar/data/1692819/000119312525221774/d43667d8k.htm
- CEG Microsoft/TMI 8-K (2024-09-20): https://www.sec.gov/Archives/edgar/data/1868275/000186827524000058/ceg-20240920.htm
- CEG Calpine 8-K (2025-01-10): https://www.sec.gov/Archives/edgar/data/1868275/000186827525000006/ceg-20250110.htm ; closing 8-K (2026-01-07): accession 0001104659-26-001780
- VST hedge %s: Q2'25 release exhibit https://www.sec.gov/Archives/edgar/data/1692819/000119312525174942/d929557dex991.htm ; Q3'25 https://www.sec.gov/Archives/edgar/data/1692819/000119312525268033/d33941dex991.htm ; Q4'25/Q1'26 via investor.vistracorp.com
- Insider Form 4 sample: https://www.sec.gov/Archives/edgar/data/1692819/000126840625000021/wk-form4_1759798378.xml (Burke M+S codes)
- CEG Q3'24 reaction coverage: https://www.fool.com/investing/2024/11/04/why-constellation-energy-stock-crashed-11-after-ea/
- TMI +22% coverage: https://www.interactivebrokers.com/campus/traders-insight/securities/stocks/constellation-energy-inks-nuclear-power-deal-with-microsoft-stock-gains/ ; CNBC https://www.cnbc.com/2024/09/20/constellation-energy-to-restart-three-mile-island-and-sell-the-power-to-microsoft.html
- Meta/Clinton: https://www.cnbc.com/2025/06/03/meta-signs-nuclear-power-deal-with-constellation-energy-.html ; https://investors.constellationenergy.com/news-releases/news-release-details/constellation-meta-sign-20-year-deal-clean-reliable-nuclear
- Congressional trades: https://pelositracker.app/stock/vst ; https://www.kavout.com/market-lens/congressional-contrasts-a-tale-of-two-trades-in-constellation-energy
- Price data: Yahoo Finance chart API (adjusted closes), pulled 2026-07-16; cross-checks: stockanalysis.com history API (subagent pull, corrupted for Feb-2026), OptionSlam VST earnings tracker https://www.optionslam.com/earnings/stocks/VST (BMO labels + 2026-05-07 −2.74%)
- VST IR earnings releases (all BMO): https://investor.vistracorp.com/2024-05-08-Vistra-Reports-First-Quarter-2024-Results,-Raises-Expectations-for-Energy-Harbor-and-Consolidated-Adjusted-EBITDA and successive quarterly release pages through https://investor.vistracorp.com/2026-05-07-Vistra-Reports-First-Quarter-2026-Results (8-K accessions in table (a))
- VST Q4'25 reaction coverage (conflicting): https://www.tradingview.com/news/zacks:54dd3cbca094b:0-vistra-s-q4-earnings-miss-estimates-revenues-increase-y-y/ ; https://coincentral.com/vistra-corp-vst-stock-drops-13-following-q4-earnings-miss-and-executive-share-sale/
- VST Q1'25/Q2'25/Q3'25/Q1'26 reaction coverage: https://www.fool.com/investing/2025/05/07/why-vistra-stock-dropped-after-earnings/ ; https://www.ainvest.com/news/vistra-q2-2025-earnings-strategic-moves-case-accelerated-growth-transformed-energy-landscape-2508/ ; https://sherwood.news/markets/vistra-misses-sales-and-profit-estimates-stock-drops/ ; https://blog.mexc.com/finance/why-vst-stock-down-record-q1-beat-what-comes-next-2/

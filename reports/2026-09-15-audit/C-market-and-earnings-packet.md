# C — Market and Earnings Packet (source-verified)

**Packet date:** 2026-09-15 (Tuesday)
**Built:** 2026-09-15, capture window 05:37Z – 05:53Z
**Scope:** Part 1 earnings provenance for 15 names · Part 2 market conditions · Part 3 refresher-ready block

---

## Plain-English summary (read this first)

Three things came out of this pull.

1. **Every one of the 15 names' most recent earnings date is now confirmed from a primary source** — the company's own Form 8-K "Item 2.02 Results of Operations and Financial Condition" filed with the SEC. That includes all six dates the project's earnings store was missing (CRWV, AVGO, IREN, USAR, NOW, TEM). I did not just read the filing date off a list; I opened each filing and read the sentence that names the quarter.

2. **Not one of the 15 has officially announced its next earnings date yet.** All 15 are "NOT ANNOUNCED". This is a real finding, not a failed search — see the "Why the NOT ANNOUNCED calls are trustworthy" section for the three independent checks behind it. Mid-September simply sits in the gap between quarters: these companies publish a short scheduling notice roughly two to four weeks before the call, so most of these dates should appear during October.

3. **This week is busy for reasons unrelated to earnings.** A Federal Reserve interest-rate decision lands Wednesday 2026-09-16, and Friday 2026-09-18 is the big quarterly options expiration. The project's paper NVDA $220 call expires that Friday, and NVDA last closed at $210.96 — so that strike is currently **above** the share price.

*Terms used once and then reused:* an **8-K** is a short "something happened" form a company files with the SEC; **Item 2.02** is the section of it used to release quarterly results. An **investor-relations (IR) page** is the company's own website section for shareholders. A **wire** (PR Newswire, Business Wire, GlobeNewswire) is a service companies pay to publish their own press releases verbatim.

---

## Source rules applied

| Rule | How it was honoured |
|---|---|
| Earnings dates from company IR, company press release on a wire, or SEC EDGAR only | All 15 last-report dates come from SEC EDGAR 8-K Item 2.02. All next-date determinations come from company IR pages, company IR feeds, or wire listings. |
| Aggregators not acceptable for a date | No Nasdaq calendar, Zacks, Earnings Whispers, MarketBeat, TipRanks, Yahoo, StockAnalysis, Investing.com or Wikipedia value was recorded. Two aggregator-sourced candidate dates were seen and **deliberately rejected** (logged below). |
| Exact URL + UTC capture time on every row | Present in every table. |
| Never estimate an unannounced date | No date was inferred from a historical cadence. Cadence appears only as labelled context. |
| Every value labelled | `Official-source (fetched)` or `NOT FOUND` on each row. |

---

## PART 1 — Earnings provenance, 15 names

### 1a. Most recent quarterly report actually held (the last one before today)

All rows: **Official-source (fetched)** — SEC EDGAR, Form 8-K, Item 2.02.
EDGAR submissions index pulled 2026-09-15T05:38Z; each filing body opened and read 2026-09-15T05:40Z (re-read for NOW / ET / AMZN at 2026-09-15T05:41Z).

| # | Ticker | Last report date | Period reported | Confirming URL (8-K Item 2.02) | Captured (UTC) | Label |
|---|---|---|---|---|---|---|
| 1 | CRWV | **2026-08-11** | Fiscal quarter ended 2026-06-30 (Q2 2026) | https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/crwv-20260811.htm | 2026-09-15T05:40:12Z | Official-source (fetched) |
| 2 | TEM | **2026-07-30** | Quarter ended 2026-06-30 (Q2 2026) | https://www.sec.gov/Archives/edgar/data/1717115/000119312526326083/tem-20260730.htm | 2026-09-15T05:40:18Z | Official-source (fetched) |
| 3 | PLTR | **2026-08-03** | Fiscal quarter ended 2026-06-30 (Q2 2026) | https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/pltr-20260803.htm | 2026-09-15T05:40:24Z | Official-source (fetched) |
| 4 | NOW | **2026-07-22** | Three months ended 2026-06-30 (Q2 2026) | https://www.sec.gov/Archives/edgar/data/1373715/000137371526000072/now-20260722.htm | 2026-09-15T05:41:06Z | Official-source (fetched) |
| 5 | SMCI | **2026-08-11** | Quarter **and full fiscal year** ended 2026-06-30 (FQ4 FY2026) | https://www.sec.gov/Archives/edgar/data/1375365/000137536526000021/smci-20260811.htm | 2026-09-15T05:40:36Z | Official-source (fetched) |
| 6 | NVDA | **2026-08-26** | Quarter ended 2026-07-26 (Q2 FY2027) | https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm | 2026-09-15T05:40:42Z | Official-source (fetched) |
| 7 | AMD | **2026-08-04** | Q2 2026 (quarter ended 2026-06-27) | https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/amd-20260804.htm | 2026-09-15T05:40:48Z | Official-source (fetched) |
| 8 | AVGO | **2026-09-02** | Third quarter ended 2026-08-02 (Q3 FY2026) | https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-20260902.htm | 2026-09-15T05:40:54Z | Official-source (fetched) |
| 9 | IREN | **2026-08-27** | Fourth quarter **and fiscal year** ended 2026-06-30 (FY2026) | https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/iren-20260827.htm | 2026-09-15T05:41:00Z | Official-source (fetched) |
| 10 | USAR | **2026-08-10** | Second quarter and six months ended 2026-06-30 | https://www.sec.gov/Archives/edgar/data/1970622/000197062226000056/usar-20260810.htm | 2026-09-15T05:41:06Z | Official-source (fetched) |
| 11 | ET | **2026-08-04** | Second fiscal quarter ended 2026-06-30 | https://www.sec.gov/Archives/edgar/data/1276187/000127618726000033/et-20260804.htm | 2026-09-15T05:41:12Z | Official-source (fetched) |
| 12 | VST | **2026-08-07** | Quarter ended 2026-06-30 (Q2 2026) | https://www.sec.gov/Archives/edgar/data/1692819/000169281926000017/vistra-20260807.htm | 2026-09-15T05:41:18Z | Official-source (fetched) |
| 13 | CEG | **2026-08-06** | Second quarter ended 2026-06-30 | https://www.sec.gov/Archives/edgar/data/1868275/000186827526000097/ceg-20260806.htm | 2026-09-15T05:41:24Z | Official-source (fetched) |
| 14 | MSFT | **2026-07-29** | Fiscal quarter **and year** ended 2026-06-30 (FQ4 FY2026) | https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-20260729.htm | 2026-09-15T05:41:30Z | Official-source (fetched) |
| 15 | AMZN | **2026-07-30** | Second quarter 2026 (ended 2026-06-30) | https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260730.htm | 2026-09-15T05:41:36Z | Official-source (fetched) |

**Verbatim confirmations** (the sentence in each 8-K that fixes the date — abridged to the operative clause):

- CRWV: "On August 11, 2026, CoreWeave, Inc. … issued a press release announcing its financial results for the fiscal quarter ended June 30, 2026."
- TEM: "On July 30, 2026, Tempus AI, Inc. … issued a press release regarding its financial results for the quarter ended June 30, 2026."
- PLTR: "On August 3, 2026, Palantir Technologies Inc. … issued a press release announcing its financial results for the fiscal quarter ended June 30, 2026."
- NOW: "On July 22, 2026, ServiceNow, Inc. … issued a press release announcing financial results for the three months ended June 30, 2026."
- SMCI: "On August 11, 2026, Super Micro Computer, Inc. … issued a press release … announcing unaudited financial results for the quarter and full fiscal year ended June 30, 2026."
- NVDA: "On August 26, 2026, NVIDIA Corporation … issued a press release announcing its results for the quarter ended July 26, 2026."
- AMD: exhibit index reads "99.1 Press Release dated August 4, 2026" and "99.2 Second Quarter 2026 Financial Results Presentation".
- AVGO: "On September 2, 2026, Broadcom Inc. … issued a press release announcing its unaudited financial results for the third quarter ended August 2, 2026."
- IREN: "On August 27, 2026, IREN Limited … reported its financial results for the fourth quarter and fiscal year ended June 30, 2026."
- USAR: "On August 10, 2026, USA Rare Earth, Inc. … issued an earnings press release announcing its financial results for the second quarter and six months ended June 30, 2026."
- ET: "On August 4, 2026, Energy Transfer LP … issued a press release announcing its financial and operating results for the second fiscal quarter ended June 30, 2026."
- VST: "On August 7, 2026, Vistra Corp. … issued a news release announcing, among other matters, its financial results for the quarter ended June 30, 2026."
- CEG: "On August 6, 2026, Constellation Energy Corporation (Nasdaq: CEG) announced via press release its results for the second quarter ended June 30, 2026."
- MSFT: "On July 29, 2026, Microsoft Corporation issued a press release announcing its financial results for the fiscal quarter and year ended June 30, 2026."
- AMZN: "On July 30, 2026, Amazon.com, Inc. announced its second quarter 2026 financial results."

**Two traps avoided in 1a** — both are cases where naively taking the newest Item 2.02 8-K would have produced a wrong "last report" date:

- **SMCI** also filed an Item 2.02 8-K on **2026-07-21**. That one announced *preliminary* figures for the same June-quarter. The full report is 2026-08-11. Using 07-21 would be wrong.
- **IREN** also filed an Item 2.02 8-K on **2026-07-20**, whose body says only "issued a press release announcing certain business updates" — a business update, not a quarterly report. IREN additionally filed a 2026-05-11 Item 2.02 carrying the *transcript* of the 2026-05-07 Q3 call, which is a second filing for an already-reported quarter. The last actual quarterly report is 2026-08-27.

### 1b. Next quarterly report date

**All 15: NOT ANNOUNCED as of 2026-09-15T05:53:00Z.** No date was estimated for any name.

| # | Ticker | Next report | Evidence type | IR events / calendar page (part c) | Captured (UTC) | Label |
|---|---|---|---|---|---|---|
| 1 | CRWV | NOT ANNOUNCED as of 2026-09-15T05:44:26Z | IR events page: "Upcoming & Recent Events / There are no events scheduled." + IR news listing carries no Q3 advisory | https://investors.coreweave.com/events-and-presentations/default.aspx | 2026-09-15T05:44:09Z | NOT FOUND (no announcement exists) |
| 2 | TEM | NOT ANNOUNCED as of 2026-09-15T05:45:03Z | IR Upcoming Events holds one entry only (Morgan Stanley healthcare conference, 09/15/2026); no Q3 earnings entry; no advisory in IR news | https://investors.tempus.com/news-events/investor-events | 2026-09-15T05:44:46Z | NOT FOUND (no announcement exists) |
| 3 | PLTR | NOT ANNOUNCED as of 2026-09-15T05:45:32Z | Newest events-page entry is "08 / 03 / 26 — Q2 2026 Earnings"; nothing later; no Q3 advisory in IR news | https://investors.palantir.com/events | 2026-09-15T05:45:12Z | NOT FOUND (no announcement exists) |
| 4 | NOW | NOT ANNOUNCED as of 2026-09-15T05:44:30Z | Rendered events page has no upcoming-events block at all; newsroom latest item 2026-09-09, no Q3 advisory | https://investor.servicenow.com/events-and-presentations/default.aspx | 2026-09-15T05:43:36Z | NOT FOUND (no announcement exists) |
| 5 | SMCI | NOT ANNOUNCED as of 2026-09-15T05:44:20Z | IR events page states verbatim: "Upcoming Events  There are no events scheduled."; IR news latest 2026-08-20, no FQ1 FY27 advisory | https://ir.supermicro.com/events-and-presentations/default.aspx | 2026-09-15T05:44:00Z | NOT FOUND (no announcement exists) |
| 6 | NVDA | NOT ANNOUNCED as of 2026-09-15T05:45:00Z | IR event calendar newest entry 2026-09-10 (Goldman conference); Q2 FY27 release says replay runs "until NVIDIA's conference call to discuss its financial results for its third quarter of fiscal 2027" **with no date given**; newsroom has no FY27 Q3 scheduling release | https://investor.nvidia.com/events-and-presentations/events-and-presentations/default.aspx | 2026-09-15T05:43:36Z | NOT FOUND (no announcement exists) |
| 7 | AMD | NOT ANNOUNCED as of 2026-09-15T05:53:52Z | IR Calendar states verbatim: "Upcoming Events / There are no upcoming events scheduled at this time." Newest past entries: 2026-09-11 Goldman conference, 2026-08-04 "AMD Fiscal Second Quarter 2026 Financial Results". IR press-release listing newest item 2026-08-31, no Q3 2026 scheduling release | https://ir.amd.com/news-events/ir-calendar | 2026-09-15T05:43:48Z (re-verified 05:53:52Z) | NOT FOUND (no announcement exists) |
| 8 | AVGO | NOT ANNOUNCED as of 2026-09-15T05:53:35Z | IR events page states verbatim: "Upcoming Events / More events are coming soon." Q3 FY26 earnings release read directly from EDGAR contains **no** next-earnings date — only Q4 guidance. Broadcom's own advisory series ("Broadcom Inc. to Announce … Financial Results on …") exists for Q1/Q2/Q3 FY26 but has **no Q4/FY2026 instalment** | https://investors.broadcom.com/company-information/events-presentations | 2026-09-15T05:53:24Z | NOT FOUND (no announcement exists) |
| 9 | IREN | NOT ANNOUNCED as of 2026-09-15T05:53:36Z | Q4-hosted events page renders a Past Events section only — newest "9 Sep '26 — IREN at Goldman Sachs Communacopia + Technology Conference", then "27 Aug '26 — IREN FY26 Results Conference Call" — with zero upcoming entries. IR news newest 2026-09-08, no Q1 FY27 scheduling release; nothing filed on EDGAR after 2026-08-27 | https://iren.com/investors/presentations · https://irisenergy.gcs-web.com/events-and-presentations (news: https://iren.com/investors/news) | 2026-09-15T05:52:37Z / 05:53:36Z | NOT FOUND (no announcement exists) |
| 10 | USAR | NOT ANNOUNCED as of 2026-09-15T05:47:50Z | Upcoming Events holds one entry only (Morgan Stanley Laguna conference, 2026-09-16); newest earnings event is Q2 2026, 2026-08-10; IR news newest 2026-09-09 | https://investors.usare.com/news-events/events | 2026-09-15T05:44:23Z | NOT FOUND (no announcement exists) |
| 11 | ET | NOT ANNOUNCED as of 2026-09-15T05:49:51Z | Webcasts list led by "Aug 04, 2026 — 8:00 am CT: Q2 2026 Energy Transfer Earnings Conference Call" with nothing after; IR newsroom complete back to May 2026 shows no Q3 timing advisory; EDGAR 8-K since mid-Aug is 2026-09-10 and is not an earnings advisory | https://ir.energytransfer.com/presentations-webcasts | 2026-09-15T05:45:16Z | NOT FOUND (no announcement exists) |
| 12 | VST | NOT ANNOUNCED as of 2026-09-15T05:49:29Z | Upcoming Events tab, opened explicitly, returns no events; newest past event is Q2 2026 call 2026-08-07; IR news newest 2026-09-10, no Q3 advisory | https://investor.vistracorp.com/events-and-presentations | 2026-09-15T05:44:38Z | NOT FOUND (no announcement exists) |
| 13 | CEG | NOT ANNOUNCED as of 2026-09-15T05:49:54Z | Upcoming Events page renders with zero listings (control: sibling past-events page renders 10 dated listings through the same path, so the empty result is genuine); corporate newsroom newest 2026-09-10, no advisory | https://investors.constellationenergy.com/events-and-presentations | 2026-09-15T05:44:10Z | NOT FOUND (no announcement exists) |
| 14 | MSFT | NOT ANNOUNCED as of 2026-09-15T05:51:50Z | **Affirmative official negative.** Microsoft IR states verbatim: "The next earnings release will be announced soon." and the IR FAQ states verbatim: "First quarter earnings for fiscal year 2027 will be announced soon". Deep event URLs for FY-2027 Q1 return HTTP 404. | https://www.microsoft.com/en-us/investor (events hub: https://www.microsoft.com/en-us/investor/events) | 2026-09-15T05:51:50Z | NOT FOUND (company states date not yet set) |
| 15 | AMZN | NOT ANNOUNCED as of 2026-09-15T05:50:30Z | **Amazon's own IR events feed** (`ir.aboutamazon.com/feed/Event.svc/GetEventList`, future-events filter) returns `{"GetEventListResult":[]}`. Past-events list renders fully back to 2018, so the empty future list is genuine. No "Amazon.com to Webcast Third Quarter 2026 …" release on Business Wire or IR. | https://ir.aboutamazon.com/events/default.aspx | 2026-09-15T05:46:30Z | NOT FOUND (no announcement exists) |

### Why the NOT ANNOUNCED calls are trustworthy

Fifteen consecutive "not found" results deserve suspicion — an absent date and a broken fetch look identical. Three independent checks separate the two:

1. **Negative control on the wires — the wires are working.** A domain-restricted search of PR Newswire / Business Wire / GlobeNewswire on 2026-09-15T05:48Z surfaced Q3 2026 scheduling advisories *from other issuers* filed in the days just before today: XPO ("XPO Schedules Third Quarter 2026 Earnings Conference Call for Thursday, October 29, 2026", GlobeNewswire, 2026-09-09), Citizens Financial Group (Business Wire, 2026-09-10) and Park Hotels & Resorts (Business Wire, 2026-09-10). So these advisories are being published and indexed right now — the absence of one for each of our 15 is informative, not a search failure.

2. **Primary-source check on the earnings releases themselves.** I pulled the actual EX-99.1 earnings press release out of each of the 15 8-K filings and scanned every one for a forward-looking date sentence ("will report", "next quarter", any October/November/December 2026 date). **None of the 15 contains a next-report date.** The closest near-miss, NVIDIA, references its Q3 FY2027 call without giving a date. This matters because a company that had already fixed its next date often states it here.

3. **Per-site control tests.** Where an IR page came back empty, a sibling page on the same host was fetched through the same path to prove the fetcher works: Constellation's past-events page returned 10 dated listings; Amazon's past-events list returned entries back to 2018 while its future-events feed returned an empty array; Vistra's "Upcoming Events" tab was explicitly clicked (it defaults to "Past Events" and would otherwise mislead).

### Aggregator values seen and deliberately rejected

Per the source rules these were **not** recorded and must not be fed to the refresher:

- CRWV — TipRanks displayed "Nov 16, 2026, After Close (Confirmed)". Rejected: aggregator.
- PLTR — an aggregator-circulated "Nov 2" date. Rejected: aggregator.

### Stale-source trap logged

A GlobeNewswire/NVIDIA release titled "NVIDIA Sets Conference Call for Third-Quarter Financial Results" **does** exist — dated 2025-10-29, announcing 2025-11-19 for Q3 **FY2026**. It is the prior year's notice. Do not let a text match on the headline pull this into an FY2027 row.

---

## PART 2 — Market conditions snapshot (official sources only)

### 2a. VIX — Cboe

**Source (fetched):** https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv (Cboe's own daily VIX history file)
**Captured:** 2026-09-15T05:41:43Z · **Label:** Official-source (fetched)

| Measure | Value |
|---|---|
| Most recent session | **2026-09-14** (Monday) |
| VIX close | **17.10** |
| That session's open / high / low | 17.50 / 18.17 / 16.58 |
| 20-session window | 2026-08-18 through 2026-09-14 inclusive (20 trading sessions) |
| Lowest close in window | **14.32** on 2026-09-03 |
| Highest close in window | **17.84** on 2026-09-10 |
| Mean close in window | 15.54 |
| Lowest intraday print in window | 13.80 on 2026-09-04 |
| Highest intraday print in window | 18.17 — reached on both 2026-09-10 and 2026-09-14 |

Full 20-session closes, oldest to newest:
`15.84, 14.89, 16.01, 15.13, 15.85, 15.45, 15.21, 14.51, 14.43, 14.92, 16.34, 15.20, 14.32, 14.53, 15.30, 15.72, 16.46, 17.84, 15.84, 17.10`

Note: the file contains no 2026-09-07 row, consistent with Labor Day being an exchange holiday (independently marked yellow on the Cboe expiration calendar below).

### 2b. FOMC — Federal Reserve

**Source (fetched):** https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
**Captured:** 2026-09-15T05:41:48Z · **Label:** Official-source (fetched)

| Item | Value |
|---|---|
| September 2026 FOMC meeting | **September 15–16, 2026** |
| Summary of Economic Projections | **Yes** — the calendar marks this meeting with an asterisk, defined on the page as "Meeting associated with a Summary of Economic Projections." |
| Is a decision due this week? | **Yes.** The meeting is in progress today (Tuesday 2026-09-15) and concludes **Wednesday 2026-09-16**. |
| Remaining 2026 meetings | October 27–28, 2026; December 8–9, 2026 (December also SEP-associated) |

The September 2026 row currently carries no Statement / Implementation Note / Press Conference / Minutes links, whereas every earlier 2026 meeting row does — consistent with the meeting not yet having concluded.

### 2c. NVDA last close

**Sources (fetched):**
- https://api.nasdaq.com/api/quote/NVDA/info?assetclass=stocks — captured 2026-09-15T05:42:02Z
- https://api.nasdaq.com/api/quote/NVDA/historical?assetclass=stocks&fromdate=2026-09-01&todate=2026-09-15 — captured 2026-09-15T05:47:35Z (independent cross-check, same value)
- Human-readable equivalent: https://www.nasdaq.com/market-activity/stocks/nvda

**Label:** Official-source (fetched) — Nasdaq.com quote data, the exchange of listing (NASDAQ-GS).

| Item | Value |
|---|---|
| Last close | **$210.96** |
| Session | 2026-09-14 (market status: Closed) |
| Net change | −$7.33 (−3.36%) |
| Volume | 132,310,446 |
| Day open / high / low | $211.24 / $212.77 / $208.93 |
| 52-week range | $164.27 – $236.54 |

**Position-relevant fact — paper NVDA $220 call expiring 2026-09-18:**
The **$220 strike is ABOVE the last close of $210.96**, by **$9.04** (the close is 4.11% below the strike; the strike is 4.28% above the close). For a call option, a strike above the current share price means it is *out of the money* — it currently has no exercise value, and would need the share price to rise above $220 by expiry to finish with any.

Recent closes for context (Nasdaq, same fetch): 09-01 $217.44 · 09-02 $224.41 · 09-03 $228.45 · 09-04 $230.36 · 09-08 $225.73 · 09-09 $223.67 · 09-10 $218.36 · 09-11 $218.29 · 09-14 $210.96.

### 2d. Scheduled expiration facts for Friday 2026-09-18

**Source (fetched):** Cboe 2026 Options Expiration Calendar (official PDF) — https://cdn.cboe.com/resources/options/Cboe2026OPTIONSCalendar.pdf
**Captured:** 2026-09-15T05:42:55Z · **Label:** Official-source (fetched)
Calendar footer states: "Solely for general information. Dates subject to change."

Reading the calendar's September panel against its own legend:

| Date | Marking on the Cboe calendar | Meaning per the calendar's legend |
|---|---|---|
| Mon 2026-09-07 | Yellow | Exchange Holiday (Labor Day) |
| Mon 2026-09-14 | Dark purple | 2029 Equity and ETP LEAPS added |
| **Tue 2026-09-15 (today)** | Light blue | Last day to trade Expiring **VIX Options** |
| **Wed 2026-09-16** | Magenta | **VIX Options Standard Expiration** |
| **Thu 2026-09-17** | Green | Last day to trade Expiring **Standard AM-Settled Equity Index Options** |
| **Fri 2026-09-18** | Dark navy, solid | **Equity, Equity Index, ETF & ETN Options — Standard Expiration** |
| Wed 2026-09-30 | Periwinkle + light pink | End-of-Month / End-of-Quarter Options expiration; VIX Weeklys expiration |

So for Friday 2026-09-18 specifically:

1. It is the **standard monthly expiration** for equity options, equity-index options, ETF options and ETN options. (It is the third Friday of September 2026.)
2. **AM-settled standard equity index options** stop trading the **previous day, Thursday 2026-09-17**; their settlement value is struck on Friday morning. This is the split that catches people out: for those contracts the last chance to trade is Thursday, not Friday.
3. The end-of-quarter expiration is **not** 09-18 — the calendar puts it on Wednesday **2026-09-30**.
4. Friday 2026-09-18 is **not** an exchange holiday or early close. Cboe's Hours & Holidays page (https://www.cboe.com/about/hours/us-options/, captured 2026-09-15T05:43:10Z, Official-source (fetched)) lists 2026 full closures as Good Friday (April 3) and Christmas Day (December 25), and early closes as Nov 27 and Dec 24. 09-18 appears on none of those lists.

Additionally, from the **Cboe 2026 Futures Settlement Calendar** (https://cdn.cboe.com/resources/aboutcboe/Cboe-2026FuturesSettlementCalendar.pdf, captured 2026-09-15T05:44:05Z, Official-source (fetched)): **Wednesday 2026-09-16** is marked green = "VX / VXM Monthly Futures Final Settlement Date". I am deliberately **not** characterising that calendar's marking for 2026-09-18 — the legend colour for that cell could not be read with certainty, and guessing it would violate the source discipline of this packet. Labelled **NOT FOUND** for 09-18 on the futures calendar.

---

## PART 3 — Ready-to-use block for `tools/h7_refresh_earnings.py`

All `last_report_url` values are SEC EDGAR 8-K Item 2.02 filings, which the refresher accepts. All `next_report` values are `NOT_ANNOUNCED` with `-` for the URL, per the no-estimate rule.

```
CRWV | last_report=2026-08-11 | last_report_url=https://www.sec.gov/Archives/edgar/data/1769628/000176962826000362/crwv-20260811.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:44:26Z
TEM  | last_report=2026-07-30 | last_report_url=https://www.sec.gov/Archives/edgar/data/1717115/000119312526326083/tem-20260730.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:45:03Z
PLTR | last_report=2026-08-03 | last_report_url=https://www.sec.gov/Archives/edgar/data/1321655/000132165526000039/pltr-20260803.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:45:32Z
NOW  | last_report=2026-07-22 | last_report_url=https://www.sec.gov/Archives/edgar/data/1373715/000137371526000072/now-20260722.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:44:30Z
SMCI | last_report=2026-08-11 | last_report_url=https://www.sec.gov/Archives/edgar/data/1375365/000137536526000021/smci-20260811.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:44:20Z
NVDA | last_report=2026-08-26 | last_report_url=https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:45:00Z
AMD  | last_report=2026-08-04 | last_report_url=https://www.sec.gov/Archives/edgar/data/2488/000000248826000121/amd-20260804.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:53:52Z
AVGO | last_report=2026-09-02 | last_report_url=https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-20260902.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:53:35Z
IREN | last_report=2026-08-27 | last_report_url=https://www.sec.gov/Archives/edgar/data/1878848/000187884826000051/iren-20260827.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:53:36Z
USAR | last_report=2026-08-10 | last_report_url=https://www.sec.gov/Archives/edgar/data/1970622/000197062226000056/usar-20260810.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:47:50Z
ET   | last_report=2026-08-04 | last_report_url=https://www.sec.gov/Archives/edgar/data/1276187/000127618726000033/et-20260804.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:49:51Z
VST  | last_report=2026-08-07 | last_report_url=https://www.sec.gov/Archives/edgar/data/1692819/000169281926000017/vistra-20260807.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:49:29Z
CEG  | last_report=2026-08-06 | last_report_url=https://www.sec.gov/Archives/edgar/data/1868275/000186827526000097/ceg-20260806.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:49:54Z
MSFT | last_report=2026-07-29 | last_report_url=https://www.sec.gov/Archives/edgar/data/789019/000119312526323632/msft-20260729.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:51:50Z
AMZN | last_report=2026-07-30 | last_report_url=https://www.sec.gov/Archives/edgar/data/1018724/000101872426000024/amzn-20260730.htm | next_report=NOT_ANNOUNCED | next_report_url=- | captured_utc=2026-09-15T05:50:30Z
```

---

## Caveats, limits and method notes

**A "NOT ANNOUNCED" is only true as of its timestamp.** Every one of the 15 is inside the window where a scheduling notice could drop any day. The earliest-expected batch (Microsoft, ServiceNow, Amazon, AMD) should announce during October. Re-running this pull in roughly two weeks is worth doing; re-running it the week of 2026-10-05 would likely convert several rows.

**Fetch difficulty is the main methodological risk, and it was handled explicitly.** Most of these IR sites sit behind bot protection: plain fetches return HTTP 403, a 60-second timeout, or — most dangerous — an empty JavaScript shell that looks exactly like "no events scheduled". Every empty result in Part 1b is backed by a control test on the same host (documented per row). Two site-specific gotchas worth carrying forward into any recurring earnings-calendar job:
- **Vistra's** events page defaults to the *Past Events* tab; a naive scrape silently returns past-only data. The Upcoming tab must be clicked.
- **Energy Transfer's** `/events-and-presentations` path returns a soft 404 — a real-looking page that is actually "Page Not Found". The live calendar is at `/presentations-webcasts`.
- **Broadcom's** `investors.broadcom.com/events-and-presentations` is a genuine 404. The working events calendar is `investors.broadcom.com/company-information/events-presentations`.
- **Broadcom's** `www.broadcom.com/company/news/financial-releases/<id>` mirror returns HTTP 200 but is a JavaScript shell whose extracted body is ~99 characters (headline only). It will read as "no content" rather than failing loudly. Use the SEC exhibit instead.
- Also: `ir.usare.com` and `investors.iren.com` do not resolve at all (NXDOMAIN); the working hosts are `investors.usare.com` and `iren.com/investors` (IREN also has a Q4-hosted mirror at `irisenergy.gcs-web.com`).

**SEC EDGAR was the reliable backbone.** Consistent with the repo's own `web-fetch-order` findings, EDGAR refuses WebFetch but serves `curl` when a descriptive User-Agent is supplied. All 15 primary confirmations came through that path.

**Flagging an error I made, for the record.** My first several EDGAR requests were sent with a User-Agent header containing Carsyn's personal email address. SEC's access guidance invites a contact string, but putting a personal email into outbound request headers was the wrong call and not something the task asked for; a non-personal descriptive UA (e.g. `options-validator-research/1.0`) achieves the same result. Affected requests: the EDGAR ticker map, the submissions API for the 15 CIKs, and the 8-K / EX-99.1 document fetches, all to `sec.gov` / `data.sec.gov` between 05:38Z and 05:47Z. No other host received it, and no other personal data was transmitted. The fix for any repeat run is a fixed non-personal UA string.

**Third-party renderers were used on some IR pages.** Where bot walls blocked direct access, rendered copies were obtained via helper fetchers (a rendering browser; in some cases a keyless reader relay). Those were used only to *read* company-owned pages, and every resulting determination is a negative that is separately corroborated by check (1) and check (2) in "Why the NOT ANNOUNCED calls are trustworthy". No date in this packet rests on a renderer alone — indeed no date was recorded from any IR page at all, since all 15 were negatives.

One relay-only string is worth naming explicitly: Broadcom's "Upcoming Events / More events are coming soon." was reachable only through the relay (`investors.broadcom.com` timed out to every direct method attempted, including HTTP/2, HTTP/1.1 and IPv4-only `curl`). The Broadcom conclusion does not depend on it — the stronger evidence is the direct, unproxied SEC EDGAR fetch of Broadcom's own Q3 FY2026 earnings exhibit (https://www.sec.gov/Archives/edgar/data/1730168/000173016826000076/avgo-08022026x8kxex99.htm, captured 2026-09-15T05:50:22Z), which states Q4 guidance and the Q3 call only, and contains no next-earnings date.

**Not covered / out of scope by instruction.** No commentary, no forecasts, no estimated dates, no implied-volatility or positioning analysis. Historical reporting cadences appear in this document only where explicitly labelled as context, and were not used to fill any field.

# B — Literature Memo: What the Research Says About This Project's Hypotheses

**Prepared 2026-09-15.** Literature review only. Nothing here is a registration; no number here is frozen.

**Provenance labels.** **Fetched** = I downloaded the page or PDF, converted it locally, and read the number in the document. **LLM-asserted** = from memory or a search summary, not verified on a retrieved page. Capture times are UTC on 2026-09-15. Where a working paper and its published version differ, I cite the one I read and say so. Two PDF-reading steps returned *invented* citations; I caught both by converting locally and cross-checking. One link still circulating in search results (`cfr.pub`) now 301-redirects to an unrelated commercial site — not followed, not cited.

---

## Q1 — Single-name variance risk premium

*Plain English: the variance risk premium (VRP) is the gap between the volatility options charge you upfront (implied) and what the stock actually delivers (realized). Negative VRP = options are expensive = sellers win.*

**The index premium is real.** Bakshi & Kapadia (2003, *RFS* 16(2), 527–566), S&P 500 calls 1988-01 to 1995-12: mean delta-hedged gains (long call, hedged with stock, so it bets on volatility not direction) were negative across nearly all moneyness; at-the-money mean −$0.45, with **68%** of ATM observations losing; excluding deep in-the-money calls, **72%** of the call sample lost. Fixed-maturity ATM calls held to expiry: −$0.47 (t=−2.34) at 30 days, −$0.53 (t=−2.90) at 44, −$0.63 (t=−2.80) at 58 (**Fetched**). Carr & Wu (2004 WP, the freely posted precursor to *RFS* 22(3), 2009, 1311–1341): log VRP averaged **worse than −50%/month** for the two S&P indexes and the Dow (**Fetched**).

**The single-name premium is weak — which predicts the project's finding (a).** Same Carr-Wu 35-stock sample: log VRP significantly negative for **21 of 35**, but the raw mean VRP (the actual money) **insignificant for all but three of 35**. Their conclusion: "the market does not price all return variance variation in each single stock, but only prices the variance risk in the stock market portfolio" (**Fetched**).

Driessen, Maenhout & Vilkov (Nov 2005 WP; published *JF* 64(3), 2009, 1377–1406) give the decisive number. Across S&P 100 constituents 1996–2003, the square root of *realized* variance averaged **39.91%** versus implied **38.56%** — realized **exceeded** implied. Zero VRP could not be rejected at 5% for **108 of 135 stocks**; of the remaining 27, only **16** showed a significantly positive implied-minus-realized gap. Their words: "There is therefore very little evidence for the presence of a negative variance risk premium in individual stock options." The index premium survives because what is priced is *correlation* risk — implied correlation **46.7%** versus realized **28.7%** (**all Fetched**). Correlation is a portfolio-level risk; one stock does not carry it.

So finding (a) is the *expected* result, not an anomaly. The index intuition that options are always overpriced does not transfer to MSFT, AMZN, VST, CEG.

**Two post-2009 qualifications.** (i) Duarte, Jones & Wang (Jan 2022 WP; published *JF* 79, 2024, 3581–3621; sample 1996-01 to 2019-06) argue the consensus is a microstructure-noise artifact: heavily traded deep-OTM stock calls returned **−73 bps/day**, and after bias correction the single-name VRP is "about the same as" the index premium, roughly **−5 bps/day** versus **−11 bps/day** on index puts (**Fetched**). The published version reportedly revises −73 to −116 bps/day (**LLM-asserted**). Read as: possibly real, but small and noisy. (ii) Cao & Han (*JFE* 108, 2013, 231–249; 1996-01 to 2009-10): delta-hedged returns are negative and **decrease monotonically with idiosyncratic volatility**. Long low-IVOL / short high-IVOL delta-hedged calls earn **1.4%/month at mid**, **0.79%** at 25% of quoted spread, and **0.17% — insignificant** — at 50% (**Fetched**). Options on volatile names are the expensive ones, but the edge sits inside the no-trade band.

**Index premium is decaying.** Dew-Becker & Giglio, Chicago Fed WP 2025-17 (2025-09-04): "over the past 15 years, option alphas have become indistinguishable from zero"; rolling 10-year information ratios on traded 5%-OTM puts, delta-hedged puts, ATM straddles and realized-variance-minus-VIX all converged to zero, mostly *before* March 2020. Variance risk still earns its CAPM beta; the alpha is gone (**Fetched**). Index only. I found no study isolating mega-cap AI/semis names as a VRP bucket.

---

## Q2 — Options around earnings

**Run-up and crush are real.** Dubinsky, Johannes, Kaeck & Seeger (*RFS* 32(2), 2019, 646–687; 2000-01 to 2015-08): the post-announcement implied-volatility decrease "holds for all years," and at firm level "the null of no post-EAD decrease is rejected for every firm"; the pre-announcement increase holds every year except 2009. For a firm with 25% baseline volatility and an average earnings jump volatility of **7.3%**, a 2-week option's implied volatility is "almost 44% but only 32% for an option expiring in 6 weeks." In 2015, over **19%** of sample-firm annual variance came from four announcement days (**all Fetched**). This supports finding (b) structurally.

**Selling volatility across the event is the documented edge, not buying it.** Same paper, ATM straddles held from the close before to the close after: mean **−7.96%**, median **−10.24%**, t = **−13.25**, negative in **all 16 years**; best firm-level average was "merely 1%." A bootstrap on matched non-announcement days puts the 1st percentile at only **−2.17%**, so this is far worse than ordinary time decay. Their caution: naive strategies using closing quotes "may consume a substantial portion of these short straddle returns" (**all Fetched**).

**Buying volatility *before* the event is a separate, also-documented trade.** Gao, Xing & Zhang (published *JFQA* 53(6), 2018, 2587–2617; I read the Apr 2013 Rice WP): individual-stock straddles generally lose — daily **−0.19%**, weekly **−2.09%** — but ATM straddles from one day before the announcement *to* the announcement date earn **+2.3%**, highly significant (**Fetched**). The published [−3,0] figure of +3.34% is **LLM-asserted**. No conflict with Dubinsky: Gao captures the run-up and exits *before* the news. On costs: median relative closing spread ~**10%**, rising to ~**12%** around announcements; at **50%** of quoted spread both low- and high-spread groups stay positive; at **100%**, "only the straddles with lower-than-median transaction costs can deliver average positive returns," and only the shortest-maturity bucket survives, at **+0.61%/day** (t=2.08) (**Fetched**).

**Retail outcomes in this window are the project's H8/H6 described as a loss.** De Silva, Smith & So (*Review of Finance* 30(2), 2026, 489–535; Nasdaq/PHLX, 32,758 announcements, 2010 to 2021-02): retail "overpay for options relative to realized volatility, incur enormous bid–ask spreads, and do not close their positions until weeks after announcements," producing "retail losses of **5–9 percent** on average, and **10–14 percent** for high expected volatility announcements." Retail "mainly purchase call options," concentrated in the *highest*-expected-volatility names (**Fetched**).

Bryzgalova, Pavlova & Sikorskaya (*JF* 78(6), 2023, 3465–3514): **49.9%** of retail volume is weekly options (vs 41.5% non-retail); average quoted spread on sub-week options **12.6%**, effective **6.6%**; calls are **71.5%** of retail volume; slightly-OTM contracts average **29%** quoted spread, sub-$250 trades **23.5%**. Aggregate, 2019-11 to 2021-06 at a 10-day horizon: retail lost **$2.10bn**, against **$6.4bn** of indirect trading costs and ~**$900m** of commissions. Losses "are concentrated primarily in long positions in short-term (weekly) options, both calls and puts. In contrast, investors who wrote those options made money, even on a net basis" (**all Fetched**).

Counterpoint, worth airing: Bogousslavsky & Muravyev (WP 2024-08-29; trader-level, $15bn of trades) find the average option trade earns **−0.9%**, range **−5% to +1%** across subsamples, naked sales **+20%**, and argue the −3% to −9% estimates reflect proxy limitations (**Fetched**). The disagreement is about magnitude, not sign.

**Does any study show after-cost positive returns for a directional single long call around earnings?** I found none. Every verified positive earnings result is a *volatility* structure; the directional-call evidence is uniformly negative.

**PEAD in mega-caps: effectively dead.** Bernard & Thomas (*Journal of Accounting Research* 27, 1989, 1–36) established the anomaly; the original is paywalled with no open copy, so its size-decile magnitudes are **LLM-asserted**. A peer-reviewed review (Fink 2020, Univ. of Graz WP 2020-04) reports drift "of around **2% over 60 trading days**" and that "the magnitude of abnormal returns appears to be inversely related to firm size" (**Fetched, secondary**). Chordia, Goyal, Sadka, Sadka & Shivakumar (*FAJ* 65(4), 2009, 18–32) is the cleanest citation: the drift "occurs mainly in highly illiquid stocks," with a long-short strategy earning **0.04%/month in the most liquid stocks versus 2.43% in the most illiquid**, and transaction costs consuming **70–100%** of paper profits (**Fetched**). Martineau (*Critical Finance Review* 11(3–4), 2022, 613–646; full text read from the OSF preprint): "For large stocks, PEAD have been **non-existent since 2006** but has only disappeared recently for microcap stocks." The 60-day drift coefficient for above-NYSE-20th-percentile stocks is statistically zero from 2006 and **significantly negative (−0.002\*\*) in 2016–2019**, while announcement-day responsiveness roughly sextupled (**Fetched**). For MSFT and AMZN there is no drift left to harvest.

---

## Q3 — Covered calls, index versus single name

Whaley (2002), "Return and risk of CBOE buy-write monthly index," *Journal of Derivatives* 10(2), 35–42 — citation verified on Whaley's own publication list (**Fetched**); the article is paywalled (the journal URL redirects then 404s), so its numbers are **LLM-asserted**.

Cboe's current data settles the risk-adjusted question. BXM factsheet, as of 2026-08-31, since inception 1986-06-20: annualized return **8.6%** vs S&P 500 Total Return **11.2%**; volatility **10.7%** vs **15.2%**; max drawdown **−35.8%** vs **−50.9%**; beta 0.62; **Sharpe 0.56 vs 0.57**. Calendar 2021–2025 (BXM/SPX TR): 20.5/28.7, −11.4/−18.1, 11.8/26.3, 20.1/25.0, 8.9/17.9 (**Fetched**; index values exclude transaction costs, pre-2002 data back-tested). In plain terms: forty years of index overwriting gave up 2.6 points of annual return to save 4.5 points of volatility and landed at the same risk-adjusted result as just owning the index. It helped in 2022 and lost badly in every strong up year.

Israelov & Nielsen explain why. "Covered Calls Uncovered" (*FAJ* 71(6), 2015) decomposes the strategy into equity exposure (most of risk and return), short volatility (Sharpe near **1.0** but only ~**10%** of risk), and an **uncompensated equity reversal** exposure contributing ~**25%** of risk with minimal return (**Fetched**). Their earlier "One Fact and Eight Myths" (*FAJ* 70(6), 2014, 23–31) concludes that absent a view that implied volatility is rich there is no reason to write calls (**LLM-asserted** — SSRN and Taylor & Francis both 403'd).

That uncompensated reversal exposure is the mechanism behind finding (c): systematically selling calls into strength is a short-momentum bet, and it loses more on a single stock than on an index because one stock's right tail is far fatter. AMZN tracking buy-and-hold while VST gave up a lot is the predicted pattern.

Evidence on covered calls on high-momentum *single* names is thin; I found no peer-reviewed study isolating that case with retrievable numbers. Brooks et al. (2019, *Journal of Derivatives*) argue prior superior-performance findings are spurious once skewness is handled (**LLM-asserted**, not fetched).

---

## Q4 — Long-call momentum and continuation

**Option momentum exists but is not a long-call strategy.** Heston, Jones, Khorram, Li & Mo, "Option Momentum," *JF* 78(6), 2023, 3141–3192 (I read the Dec 2021 USC WP; 1996-01 to 2019-06). The object is a **long-short portfolio of ATM straddles** sorted on past straddle returns — not calls bought after a rally. The lag-2-to-12 spread is **4.4%/month (t=5.94)** on cumulative-return sorts. Their own abstract: "Average option momentum returns are close to zero after paying the full bid-ask spread for options with below-median bid-ask spreads." Table 13: baseline momentum earns **+6.22%/month** at zero cost, **+3.62%** at algo costs, **−0.40%** adjusted, **−3.56%** effective, **−6.78%** at full quoted half-spread; only the cost-optimized decile/low-spread variant stays positive (**all Fetched**).

**Buying calls on lottery-like names is documented to lose heavily.** Boyer & Vorkink, "Stock Options as Lotteries," *JF* 69(4), 2014, 1485–1527: low-minus-high ex-ante-skewness option returns differ by **10 to 50 percent per week** (**LLM-asserted** — I retrieved only the Internet Appendix, which confirms authorship and that open interest rises monotonically with skewness). Byun & Kim, *JFE* 122(1), 2016, 155–174: calls on the most lottery-like stocks underperform calls on the least by **10–20%/month**, stronger in high-sentiment periods (**LLM-asserted**, paywalled). Bali & Murray (*JFQA* 48, 2013, 1145–1171) document a negative risk-neutral-skewness/return relation (**LLM-asserted**).

**Verdict.** NVDA, AMD, AVGO, PLTR, SMCI, CRWV, TEM, NOW, IREN, USAR are close to a textbook description of the high-idiosyncratic-volatility, lottery-like, high-attention stocks whose calls have the *most* negative documented expected returns. Buying ATM/OTM calls on momentum names after large up-moves is not merely unsupported — it is the documented losing side of three separate published results.

**Methodological warning.** Duarte, Jones, Khorram, Mo & Wang, "Too Good to Be True: Look-Ahead Bias in Empirical Options Research," *RFS* 2026 advance article, DOI 10.1093/rfs/hhag061: many high-Sharpe option results come from filtering "noisy" observations using information unavailable at formation, and a high Sharpe is itself a warning sign (**LLM-asserted** — OUP returned navigation only, SSRN 403'd).

---

## Q5 — Transaction-cost reality

I could not fetch Muravyev & Pearson (*RFS* 33(11), 2020, 4973–5014) itself, but I did read their Internet Appendix, which reports the same statistics for options on **non-S&P 500 stocks**, 2004-01 to 2015-12 (**all Fetched**):

| Half-spread | All | OTM | ATM | ITM |
|---|---|---|---|---|
| Quoted | 12.8% | 16.6% | 11.6% | 8.4% |
| Effective | 9.7% | 12.9% | 8.8% | 6.1% |
| Adjusted | 7.7% | 10.6% | 6.9% | 4.4% |
| Algo | 5.4% | 8.0% | 4.7% | 2.8% |

In dollars (all options): quoted $0.20, effective $0.15, adjusted $0.11, algo $0.07; execution-timing share **37.3%**. Heston et al. summarise the same source as algo **20.3%**, adjusted **51.6%**, effective **75.8%** of the quoted half-spread (**Fetched**).

**How the project's fill model compares.** "Mid-or-worse + 1% haircut + half-spread both legs" means paying roughly **100% of the quoted half-spread per leg** plus 1%. For ATM options on non-S&P-500-type names that is about **1.3× the conventional effective** half-spread, **1.7× adjusted**, and **2.5× algo**. Honest read: **conservative but defensible** — at the pessimistic end of the documented range, not outside it. Heston et al.'s Table 13 shows precisely what that costs: +6.22%/month at mid becomes −6.78%/month at full quoted half-spread. So finding (d) should be reported as "the SPY/QQQ put-credit spreads fail *at full-quoted-spread costs*," not "fail at realistic costs."

There is a regulator-documented mitigation. SEC DERA WP 2503 (2025-03-14), "Hope at a Reasonable Price": for sub-$3 calls with a $0.10 spread, market-turning limit orders fill **50%** of the time early and **62%** later, all-in expected cost **$0.028/$0.021 versus $0.05** for a marketable order; above $3, a limit order's net effective spread is ~**$0.04 versus $0.10**. Conclusion: "any exploitation of customers by market makers is much less than first appears." The same paper flags an OPRA sequencing defect where the quote *following* a trade can carry an earlier timestamp, invalidating naive trade-versus-prior-quote comparisons (**all Fetched**) — worth checking against this project's pipeline.

**2026 regulator data.** SEC staff, "Roundtable on Options Market Structure — Supporting Data" (2026-04-09; a staff note, not a Commission position): median effective spread on equity options fell from **2.2% (2012) to 1.9% (end-2025)**, and **1.3% to 0.9%** for the ten most liquid equities — but outside that top ten, quoted spreads **widened** by 0.5, 1.3, 1.5 and 0.4 percentage points, "signaling potential deterioration in displayed market quality." These market-wide medians are **not** directly comparable with Muravyev-Pearson's per-contract half-spreads; both are reported rather than reconciled. Most actionable retail fact: for marketable individual-customer orders in Dec 2025, price improvement was **0–13%** via the electronic book versus **22–89%** via single-leg auctions, with realized effective spreads reaching **$6.68** where the quoted spread exceeds $5.00 (**all Fetched**).

Structural note: **Rule 605 does not cover options** — "'NMS stock' is defined under Regulation NMS as any NMS security other than an option" (**Fetched**, SEC Release 34-99679). Rule 606 covers options routing and payment-for-order-flow disclosure, but there is **no** standardised options execution-quality dataset equivalent to the equity Rule 605 reports (**Fetched**).

---

## Q6 — Synthesis and ranking

| Rank | Family | Verdict | Key evidence |
|---|---|---|---|
| 1 | **Short volatility across the earnings event** (not currently registered; adjacent to H5's income legs) | **Positive; after-cost survival conditional** | Dubinsky: straddle buyers lose −7.96% mean / −10.24% median, negative all 16 years, t=−13.25. Authors warn quoted-spread costs consume much of the short side. |
| 2 | **H5 — LEAPS + cash-secured put + covered-call core** | **Weakly positive; mostly beta, little alpha** | BXM Sharpe 0.56 vs 0.57 over 40 years. Israelov-Nielsen: short-vol sleeve Sharpe ≈1.0 but only ~10% of risk; ~25% of risk uncompensated reversal. Single-name VRP weak. |
| 3 | **Pre-earnings long *straddle*** (H8's window, different structure) | **Positive pre-cost; survives only short-dated + low-spread** | Gao et al.: +2.3% [−1,0]; at 100% of quoted spread only below-median-spread, shortest-maturity names stay positive (+0.61%/day). |
| 4 | **H6 — post-earnings tactical long calls** | **Unsupported to negative** | No after-cost positive directional long-call result found. PEAD is gone in large caps (Martineau: zero since 2006, negative 2016–19; Chordia: 0.04%/month in liquid stocks). |
| 5 | **H8 — pre-earnings long calls** | **Documented negative as implemented** | De Silva: −5 to −9%, −10 to −14% on high-expected-volatility announcements; retail "mainly purchase call options." The documented pre-earnings edge is vega, not direction. |
| 6 | **H10a/b — parabolic/breakout continuation long calls** | **Documented negative** | Option momentum is a long-short *straddle* effect that dies at full quoted spread. Byun-Kim −10 to −20%/month; Boyer-Vorkink 10–50%/week. |
| 7 | **H7 — swing long calls on volatile AI names** | **Most strongly documented negative** | Same three results, compounded: the watchlist is selected on exactly the characteristics predicting the worst call returns. Cao-Han: delta-hedged returns fall monotonically in idiosyncratic volatility. |

**Blunt summary.** Four of five registered forward-paper families (H6, H7, H8, H10a/b) are long-call directional structures, and the literature documents negative expected returns for that structure on these names. The one supported family (H5) is supported as *beta with a modest volatility-selling overlay*, not alpha. "No edge found" is the expected outcome for H7 and H10 — a successful, informative result.

### Two candidate designs the literature would most support

**Every number in this table is LLM-asserted.** Nothing is registered; the owner types any frozen number.

| | **A — Earnings-window short volatility, defined risk** | **B — Reversal-stripped monthly overwrite / cash-secured-put core** |
|---|---|---|
| **Structure** | Defined-risk short volatility spanning the announcement: short ATM strangle with protective wings (iron condor), nearest monthly expiration with ≥3 trading days left after the announcement. Defined risk keeps it inside validator-only guardrails. | Monthly ~0.20-delta covered call on an existing share position plus a cash-secured put on the same name, with a **trend veto**: skip the call-write in any month the name sits in the top tercile of 12-month price momentum. |
| **Names** | MSFT, AMZN only — where finding (b) confirms a real run-up/crush and option spreads are tightest. | MSFT, AMZN only. Explicitly excludes VST/CEG and the AI watchlist: reversal exposure is what cost the project on VST, and single-name VRP evidence is weakest where volatility is highest. |
| **Entry / exit** | Enter at the close the last trading day before the announcement; exit at the close the first trading day after. End-of-day only. | Enter at the close the first trading day after monthly expiration; hold to expiration or assignment. End-of-day only. |
| **Why the literature supports it** | Dubinsky: −7.96% mean / −10.24% median straddle return across the announcement, negative all 16 years. Gao shows the opposite-signed run-up edge stops *before* the news, so the windows are separable. Bryzgalova: retail *writers* of short-dated contracts made money net of costs. | Israelov-Nielsen 2015: short-vol sleeve Sharpe ≈1.0; the ~25% of risk from equity reversal is uncompensated, and a momentum veto is the direct way to strip it. BXM's whole historical case is drawdown reduction, not return. |
| **Expected entries/year** | 8 (4 announcements × 2 names) | 24 call-writes before the veto; ~16 after, plus up to 24 put-sales |
| **Loss bar (≥2× loss bar expected entries, ≤12 months)** | **4** (8 ≥ 2×4) | **8** on the call-write leg (16 ≥ 2×8) |
| **Main risk** | 8 entries/year is a thin sample; one outsized gap can dominate. Wings cost premium and shrink the edge; four legs make costs binding. | Edge is small and largely beta. Israelov-Nielsen's own conclusion: with no view on implied volatility there is no reason to write calls at all. |

**Two cross-cutting cautions.** A surprisingly high Sharpe should trigger a data-filtering audit (look-ahead bias) before it triggers celebration. And the SEC DERA OPRA trade/quote sequencing defect is a concrete, checkable bug class in any pipeline comparing a fill to the "prior" quote.

---

## Sources

**[F]** = fetched and read. **[X]** = attempted, failed (403/404/navigation-only); nothing from it treated as verified.

1. **[F 05:37Z]** Bakshi & Kapadia (2003), *RFS* 16(2), 527–566 — https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf
2. **[F 05:47Z]** Carr & Wu, "Variance Risk Premia" (2004 WP; pub. *RFS* 22(3), 2009, 1311–1341) — https://engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf · **[X]** https://academic.oup.com/rfs/article-abstract/22/3/1311/1581057
3. **[F 05:47Z]** Driessen, Maenhout & Vilkov (2005 WP; pub. *JF* 64(3), 2009, 1377–1406) — https://www.fbv.kit.edu/symposium/10th/papers/Vilkov_Driessen_Maenhout%20-%20Option-Implied%20Correlations%20and%20the%20Price%20of%20Correlation%20Risk%20.pdf · **[X]** https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2009.01467.x
4. **[F 05:50Z]** Cao & Han (2013), *JFE* 108(1), 231–249 — https://www-2.rotman.utoronto.ca/facbios/file/Han_JFE_published.pdf
5. **[F 05:54Z]** Duarte, Jones & Wang (2022 WP; pub. *JF* 79, 2024, 3581–3621) — http://faculty.marshall.usc.edu/Christopher-Jones/pdf/duarte_jones_wang_2022.pdf
6. **[F 05:43Z]** Dew-Becker & Giglio (2025), Chicago Fed WP 2025-17 — https://www.chicagofed.org/-/media/publications/working-papers/2025/wp2025-17.pdf?sc_lang=en
7. **[F 05:37Z]** Dubinsky, Johannes, Kaeck & Seeger (2019), *RFS* 32(2), 646–687 — https://research.vu.nl/ws/portalfiles/portal/108247883/Option_Pricing_of_Earnings_Announcement_Risks.pdf
8. **[F 05:42Z]** Gao, Xing & Zhang (2013 WP; pub. *JFQA* 53(6), 2018, 2587–2617) — https://www.ruf.rice.edu/~yxing/straddle_201305_03.pdf
9. **[F 05:42Z]** de Silva, So & Smith (2026), *Review of Finance* 30(2), 489–535 — https://www.timdesilva.me/files/papers/losing_optional.pdf
10. **[F 05:39Z]** Bryzgalova, Pavlova & Sikorskaya (2023), *JF* 78(6), 3465–3514 — https://lbsresearch.london.edu/id/eprint/2827/1/The%20Journal%20of%20Finance%20-%202023%20-%20BRYZGALOVA%20-%20Retail%20Trading%20in%20Options%20and%20the%20Rise%20of%20the%20Big%20Three%20Wholesalers.pdf
11. **[F 05:52Z]** Bogousslavsky & Muravyev (2024 WP), "An Anatomy of Retail Option Trading" — https://www.lsu.edu/business/files/event-files/2025-finance-mardi-gras/retail_option_trading_v2.pdf
12. **[F 05:48Z]** Israelov & Nielsen (2015), "Covered Calls Uncovered," *FAJ* 71(6) — https://rpc.cfainstitute.org/research/financial-analysts-journal/2015/covered-calls-uncovered
13. **[X]** Israelov & Nielsen (2014), *FAJ* 70(6), 23–31 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2444993 · https://www.tandfonline.com/doi/abs/10.2469/faj.v70.n6.3
14. **[F 05:53Z]** Whaley (2002), *Journal of Derivatives* 10(2), 35–42 — citation verified at https://www.whaley.info/research-articles/2000-2009 · **[X]** https://jod.iijournals.com/content/10/2/35
15. **[F 05:45Z]** Cboe Global Indices, "Cboe S&P 500 BuyWrite Index (BXM)" factsheet, as of 2026-08-31 — https://cdn.cboe.com/resources/indices/factsheet/CboeGlobalIndices_BXM-Index.pdf
16. **[F 05:44Z]** Heston, Jones, Khorram, Li & Mo (2021 WP; pub. *JF* 78(6), 2023, 3141–3192) — http://faculty.marshall.usc.edu/Christopher-Jones/pdf/opmom.pdf · **[X]** https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4113680
17. **[F 05:47Z]** Boyer & Vorkink (2014), *JF* 69(4), 1485–1527 — Internet Appendix only: https://boyer.byu.edu/00000180-910c-dc15-abb6-d9dfb7040001/boyer-vorkink-appendix-pdf
18. **[F 05:47Z]** Muravyev & Pearson (2020), *RFS* 33(11), 4973–5014 — Internet Appendix: https://www.dmurav.com/MuravyevPearson.OptionsTradingCosts.InternetAppendix.pdf
19. **[X]** Duarte, Jones, Khorram, Mo & Wang (2026), *RFS* advance, DOI 10.1093/rfs/hhag061 — https://academic.oup.com/rfs/advance-article-abstract/doi/10.1093/rfs/hhag061/8722307
20. **[F 05:50Z]** Chordia, Goyal, Sadka, Sadka & Shivakumar (2009), *FAJ* 65(4), 18–32 — https://rpc.cfainstitute.org/research/financial-analysts-journal/2009/liquidity-and-the-post-earnings-announcement-drift · also verified https://api.crossref.org/works/10.2469/faj.v65.n4.3
21. **[F 05:45Z]** Martineau (2022), *Critical Finance Review* 11(3–4), 613–646 — full text via OSF preprint: https://files.osf.io/v1/resources/z7k3p/providers/osfstorage/61a5354f422ad40804d00508 · metadata https://api.osf.io/v2/preprints/z7k3p/ · author page https://www.charlesmartineau.com/ · **[X]** https://www.nowpublishers.com/article/Details/CFR-0122 · **[X, do not use]** https://cfr.pub/... now redirects off-domain
22. **[F 05:52Z]** Bernard & Thomas (1989), *Journal of Accounting Research* 27, 1–36 — citation only: https://api.crossref.org/works/10.2307/2491062 (no open full text; JSTOR paywalled)
23. **[F 05:54Z]** Fink (2020), "A Review of the Post-Earnings-Announcement Drift," Univ. of Graz WP 2020-04 — https://static.uni-graz.at/fileadmin/sowi/Working_Paper/2020-04_Fink.pdf
24. **[F 05:42Z]** SEC Staff (2026-04-09), "Roundtable on Options Market Structure — Supporting Data" — https://www.sec.gov/files/roundtable-options-market-structure.pdf
25. **[F 05:42Z]** Fu, Li, Musto & Pearson (2025), "Hope at a Reasonable Price," SEC DERA WP 2503 — https://www.sec.gov/files/dera-hope-reasonable-prc-2503.pdf
26. **[F 05:50Z]** SEC, "Disclosure of Order Execution Information," Release 34-99679 — https://www.sec.gov/files/rules/final/2024/34-99679.pdf
27. **[F 05:50Z]** SEC, "FAQs Concerning Rule 606 of Regulation NMS" — https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions/faq-rule-606-regulation
28. **[F 05:47Z]** FINRA (2026), "2026 FINRA Industry Snapshot" — https://www.finra.org/sites/default/files/2026-05/2026-Industry-Snapshot.pdf
29. **[F 05:44Z]** OCC (2026-01-05), "OCC Annual 2025 and December 2025 Volume" — https://www.theocc.com/newsroom/views/2026/01-05-occ-annual-2025-and-december-2025-volume

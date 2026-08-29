# Literature brief: options-market signals for a 4-name AI-infrastructure research program (VST, CEG, MSFT, AMZN), EOD chains

Prepared as a quant-research-librarian pass: WebSearch + WebFetch verification only, no fabricated citations.
Where WebFetch hit a 403 or unparseable binary, that is noted explicitly and the claim is corroborated instead
via 2+ independent secondary summaries (SSRN/RePEc/ResearchGate/Semantic Scholar listings, citing papers).

Labels follow the repo's claim-discipline convention: **Official-source** (publisher/journal page or author's own
PDF), **Repo-verified** (n/a here — no repo code checked), **Inference** (my synthesis connecting a verified
finding to this project), **Assumption** (unverified secondary-source figure, flagged).

---

## 1. Volatility risk premium (VRP): index vs. single names

**Bakshi, G., and N. Kapadia (2003a). "Delta-Hedged Gains and the Negative Market Volatility Risk Premium."
*Review of Financial Studies* 16(2): 527–566.**
URL: https://academic.oup.com/rfs/article-abstract/16/2/527/1579962 (also free PDF:
https://people.umass.edu/~nkapadia/docs/Bakshi_and_Kapadia_2003_RFS.pdf) — Official-source.
Finding: delta-hedged S&P 500 index option portfolios earn significantly negative average gains (avg. SPX
delta-hedged call loss ≈ 3.31% of option value / 0.07% of index value); losses are larger for at-the-money
options, larger in high-volatility periods, and survive controls for jump risk — read as a negative market
volatility risk premium, not (mainly) a jump-risk artifact.
Practical implication: the "index options are systematically overpriced for buyers / underpriced for
short-vol sellers" result is an *index*-level finding; do not assume it transfers 1:1 to VST/CEG/MSFT/AMZN
single names without separately testing each name.

**Bakshi, G., and N. Kapadia (2003b). "Volatility Risk Premiums Embedded in Individual Equity Options: Some
New Insights." *Journal of Derivatives* 11(1): 45–54.**
URL: https://jod.pm-research.com/content/11/1/45 — Official-source (abstract; body paywalled).
Finding: in a sample of individual-stock options, volatility risk is still priced with a negative sign, but
*market-wide* (systematic) volatility risk is more important than firm-specific (idiosyncratic) volatility
risk in explaining the premium — i.e., the single-name premium is smaller and is largely a pass-through of
the same systematic factor priced at the index level, not an independent firm-level effect.

**Carr, P., and L. Wu (2009). "Variance Risk Premiums." *Review of Financial Studies* 22(3): 1311–1341.**
URL search-confirmed via RePEc/Federal Reserve citations; direct PDF at Liuren Wu's faculty page 404'd on
fetch (site redirect) — Official-source status: paper existence/venue confirmed by 3 independent secondary
sources (Fed working paper citations, Alex Chinco's notes, multiple RePEc entries); numeric claims below are
Assumption-labeled pending a clean primary-text pull.
Finding (Assumption, corroborated by 2 independent secondary summaries): a significantly negative variance
risk premium for the S&P 100 index, while individual-stock variance risk premiums are "often zero or even
positive" — not explained by CAPM or Fama-French factors, implying a distinct priced factor for variance
itself (not just its correlation with returns).

**Corroborating/extending: Driessen, J., P. Maenhout, and G. Vilkov (2009). "The Price of Correlation Risk:
Evidence from Equity Options." *Journal of Finance.***
URL: https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID1157804_code417015.pdf?abstractid=673425 —
Official-source (SSRN-hosted full text).
Finding: the gap between option-implied and realized stock-return correlations (avg. implied 39.5% vs.
realized 32.5% for S&P 500 constituents in their sample) is direct evidence of a large negative *correlation*
risk premium, and this — not a separate individual-stock variance risk premium — is what explains why the
index-level VRP is large and negative while individual-name VRP is small/zero. Individual variance risk was
not found to be priced in their 1996–2003 sample.

**Bottom line for item 1 (Inference):** all three papers agree on sign and relative size — index-level short-vol
premium is real, negative, and driven substantially by *correlation risk*, not by each single name's own
variance risk. For VST/CEG/MSFT/AMZN specifically, the literature predicts a smaller, noisier, and
possibly-absent single-name VRP relative to what SPX/SPY intuition would suggest. This is a reason to expect
"no edge after costs" as a live possibility for single-name short-premium strategies on these names, consistent
with the project's own framing that a null result is a legitimate outcome.

---

## 2. Goyal & Saretto (2009): IV-minus-realized-volatility sort on straddle returns

**Goyal, A., and A. Saretto (2009). "Cross-Section of Option Returns and Volatility." *Journal of Financial
Economics* 94(2): 310–326.**
URLs: https://www.sciencedirect.com/science/article/abs/pii/S0304405X09001251 (403 on WebFetch — sandboxed
sciencedirect, consistent with this repo's own web-fetch-order finding);
free author PDF: https://personal.utdallas.edu/~axs125732/CrossOptionsJFE.pdf (WebFetch cert error — corp/edu
self-signed cert issue, not a content problem); working-paper twin:
https://docs.lib.purdue.edu/ciberwp/55/ — Official-source (existence/venue), numbers below cross-checked
across 2 independent secondary summaries.
Finding: construct decile portfolios of straddles (and delta-hedged calls/puts) sorted on
(implied − historical/realized volatility), "IVRV." A zero-cost long-(most positive IVRV)/short-(most
negative IVRV) straddle portfolio earns an economically and statistically significant average monthly return.
Secondary sources differ slightly on the exact gross decimal (22.7%/month, Sharpe 0.710 vs. 21.9%/month,
Sharpe 0.626 — **flagged discrepancy, not resolved**, likely different secondary paraphrases of the same
table), but **agree closely** that the return falls to **3.9% per month** once options are assumed to trade at
their full quoted (effective) bid-ask spread rather than the midpoint. Result is robust to market conditions,
industry, and standard risk-factor models; comparable in order of magnitude to Coval & Shumway (2001)'s
finding of ~3%/week on zero-beta SPX straddles.
Practical implication: IVRV (not raw IV level, and not "IV rank") is the specific construct with a
peer-reviewed, cost-aware effect size. Given this project's CONSERVATIVE FILLS + full-cost guardrail, expect
something closer to the post-cost ~4%/month order of magnitude (if it replicates at all on 4 idiosyncratic
names, decile-sort machinery built for hundreds of names may not translate cleanly to n=4).

---

## 3. IV rank / IV percentile: practitioner heuristic vs. actual academic support

**Verified: no peer-reviewed paper tests "IV rank" or "IV percentile" as defined and popularized by
tastytrade** (IV Rank = 100 × (current IV − 52-week IV low) / (52-week IV high − 52-week IV low)). Search
across academic databases (RePEc/SSRN/ResearchGate/Semantic Scholar) returns only trading-education sites
(Barchart, Warrior Trading, Option Samurai, PowerOptions, MenthorQ, tastytrade's own materials) for this exact
construct — confirms the honest framing is "practitioner heuristic." This is a **negative verification**, not
a fabrication risk: absence of hits across multiple academic search engines for a well-known retail term is
itself informative.

Indirect academic support exists via two channels:

**(a) The VRP literature itself** (items 1–2 above: Bakshi-Kapadia, Carr-Wu, Goyal-Saretto) establishes that
IV normally sits above subsequent realized vol, and that *the gap* (not the level, and not the level's
percentile rank) has documented predictive power for straddle returns. IV rank is a level-based, not
gap-based, filter — a meaningfully different construct from what's actually validated.

**(b) Term-structure overreaction/misreaction — the closest thing to a "vol mean-reversion speed" literature:**

**Stein, J. (1989). "Overreactions in the Options Market." *Journal of Finance* 44(4): 1011–1023.**
Official-source (venue/pages corroborated by 2 independent secondary sources incl. citing papers in JFQA).
Finding: using S&P 100 (OEX) index option term structure, the empirical elasticity of long-dated implied vol
to short-dated implied-vol moves is *larger* than a rational-expectations, mean-reverting-volatility model
predicts — i.e., long-dated IV "overreacts" to short-term IV shocks rather than cleanly mean-reverting on the
model-implied schedule.

**Poteshman, A. (2001). "Underreaction, Overreaction, and Increasing Misreaction to Information in the
Options Market." *Journal of Finance* 56(3): 851–876.**
Venue/pages corroborated via secondary citation (not independently primary-sourced — Assumption on exact
page range). Finding: refines Stein — options *underreact* to new information at short horizons and show
increasingly severe *overreaction* as the information-accumulation horizon lengthens.

**Realized/latent-volatility mean-reversion-with-jumps (adjacent, not IV):
Eraker, B., M. Johannes, and N. Polson (2003). "The Impact of Jumps in Volatility and Returns." *Journal of
Finance* 58(3): 1269–1300.**
URL: https://onlinelibrary.wiley.com/doi/10.1111/1540-6261.00566 — Official-source (venue confirmed); the
specific mean-reversion-speed (κ) parameter estimate could not be extracted without full-text/paywalled
access — **VERIFICATION FAILED for the numeric κ value specifically**; paper's existence, venue, and
qualitative finding (strong evidence of jumps in volatility itself, on top of jumps in returns, using SPX/NDX
index returns) are confirmed.

Practical implication: don't backtest "IV rank" as if it were pre-validated — treat it as an unvalidated
heuristic requiring its own registered test, exactly as this project's feasibility-gate process already
requires for any new signal. If a mean-reversion-style vol-timing signal is wanted, Goyal-Saretto's IVRV or
Vasquez's term-structure slope (item 4) are the literature-grounded substitutes for a raw IV-rank level filter.

---

## 4. Implied-vol term structure and option returns

**Vasquez, A. (2017). "Equity Volatility Term Structures and the Cross Section of Option Returns." *Journal
of Financial and Quantitative Analysis* 52(6): 2727–2754.**
URL: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/equity-volatility-term-structures-and-the-cross-section-of-option-returns/F0A40E99FD2458367DD9A56A89783D38
— Official-source (abstract fetched directly; DOI 10.1017/S002210901700076X).
Finding (full abstract quoted): "The slope of the implied volatility term structure is positively related to
future option returns. I rank firms based on the slope of the volatility term structure and analyze the
returns for straddle portfolios. Straddle portfolios with high slopes of the volatility term structure
outperform straddle portfolios with low slopes by an economically and statistically significant amount. The
results are robust to different empirical setups and are not explained by traditional factors, higher-order
option factors, or jump risk." Exact percentage spread and t-stats were **not extractable** from the abstract
page (body paywalled) — direction and robustness confirmed, magnitude is VERIFICATION FAILED at the specific-number level.
Practical implication: term-structure slope (e.g., a near-term vs. 60–90 DTE ATM IV spread) is a
literature-validated, complementary cross-sectional signal to IVRV for the 4-name universe.

---

## 5. Risk-reversal / skew as predictor

**Xing, Y., X. Zhang, and R. Zhao (2010). "What Does the Individual Option Volatility Smirk Tell Us About
Future Equity Returns?" *Journal of Financial and Quantitative Analysis* 45(3): 641–662.**
URL: https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/what-does-the-individual-option-volatility-smirk-tell-us-about-future-equity-returns/ECFD16BA9ACBDC8D577D1BD866FBEA72
— Official-source (venue/pages corroborated across ResearchGate/SSRN/Cambridge/RePEc listings, all agreeing).
Finding: stocks with the steepest OTM-put-driven volatility smirks underperform stocks with the flattest
smirks by **10.9% per year on a risk-adjusted basis**; predictability persists ≥ 6 months; steep-smirk firms
subsequently have worse earnings surprises. Interpreted as informed traders preferring OTM puts to trade on
negative news, with slow equity-market incorporation of that information.
Practical implication: this is an *equity-return* predictor sourced from the options market, not an
option-return predictor — directly usable as a signal on the underlying stock (VST/CEG/MSFT/AMZN), not just
as an options-strategy filter, with a citable annualized effect size.

---

## 6. Options volume/flow and open interest as predictors

**Pan, J., and A. Poteshman (2006). "The Information in Option Volume for Future Stock Prices." *Review of
Financial Studies* 19(3): 871–908.**
URL: https://academic.oup.com/rfs/article-abstract/19/3/871/1646711 (NBER working-paper twin:
https://www.nber.org/papers/w10925; free PDF: https://www.mit.edu/~junpan/volume.pdf) — Official-source.
Finding: using CBOE buy-to-open put and call volume (1990–2001), stocks in the lowest put/call
buy-to-open-volume-ratio quintile outperform the highest quintile by **>40 bp the next day and >1% over the
next week**; effect attributed to non-public information held by option traders (not market inefficiency);
stronger where informed-trader concentration and option leverage are higher.

**Fodor, A., K. Krieger, and J. S. Doran (2011). "Do Option Open-Interest Changes Foreshadow Future Equity
Returns?" *Financial Markets and Portfolio Management* 25(3): 265–280.** DOI 10.1007/s11408-011-0164-z.
URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1918778 — Official-source (venue/DOI corroborated
across SSRN/RePEc/Springer listings).
Finding: increases in call open interest precede significantly higher subsequent equity returns; increases in
put open interest precede weaker returns (this leg is less robust once controls are added); the *change* in
the call-to-put open-interest ratio predicts the following week's equity return even after controls.
Practical implication: Pan-Poteshman needs buy-to-open volume classification (intraday trade-direction data),
which an EOD chain snapshot generally does not carry — a real data-availability gate. Fodor-Krieger-Doran's
signal is built on raw *open interest levels/changes*, which ARE EOD-native and already partially present in
this project's OI-change-line work (per project history) — this is the more directly implementable of the two
given the data this project actually has.

---

## 7. Earnings and IV: run-up and crush magnitude

**Dubinsky, A., and M. Johannes (2006). "Earnings Announcements and Equity Options." Working paper, Columbia
Business School.** URL: https://business.columbia.edu/faculty/research/earnings-announcements-and-equity-options
(PDF: https://business.columbia.edu/sites/default/files-efs/pubfiles/6051/DJ_2006.pdf, binary/unparsed by
WebFetch but existence and hosting confirmed) — **Verification note: this paper appears to have remained an
unpublished Columbia working paper (first draft Nov. 2003; cited version 2006) across every citation found —
not a peer-reviewed journal publication.** Treat accordingly per this project's claim-discipline rule
(Inference/working-paper tier, not Official-source-journal tier).
Finding: builds a no-arbitrage option-pricing model with jumps on earnings-announcement dates; concrete
worked example — Intel, July 15 1997 earnings (after close): the July at-the-money call's Black-Scholes
implied vol was **71.15% the day before** the announcement and **42.96% the day after** (a roughly 40%
relative overnight IV collapse). Adding earnings-day jumps to the model materially reduces pricing errors
vs. plain Black-Scholes; estimated earnings-announcement uncertainty rises in stress periods (2000–2001).

**Actual peer-reviewed originators of the pre-earnings run-up / post-earnings decline finding:**
**Patell, J., and M. Wolfson (1979). "Anticipated Information Releases Reflected in Call Option Prices."
*Journal of Accounting and Economics* 1(2): 117–140.**
**Patell, J., and M. Wolfson (1981). "The Ex Ante and Ex Post Price Effects of Quarterly Earnings Announcements
Reflected in Option and Stock Prices." *Journal of Accounting Research*: 434–458.**
Venue/pages corroborated via multiple citing papers (Billings & Jennings 2010's citing text, Barth HBS paper,
Baruch working paper) — Official-source status for existence/venue; direct primary text not fetched.
Finding: documented build-up in implied vol immediately pre-announcement and decline post-announcement, most
pronounced in short-dated options and progressively weaker in longer-dated ones (consistent with a transitory,
event-specific volatility component rather than a permanent repricing).
Practical implication: for earnings-adjacent strategies on MSFT/AMZN (both report quarterly with material
moves), the citable peer-reviewed foundation is Patell & Wolfson, not Dubinsky-Johannes — the latter is a
useful, illustrative, but *unpublished* model paper; the project's H8 pre-earnings work should lean on the
former if a "peer-reviewed" label is required, and label Dubinsky-Johannes explicitly as a working paper if
cited.

---

## 8. Delta-hedged short-premium returns in high-idiosyncratic-vol / lottery-like single names

**Cao, J., and B. Han (2013). "Cross-Section of Option Returns and Idiosyncratic Stock Volatility." *Journal
of Financial Economics* 108(2): 231–249.**
URL: https://www-2.rotman.utoronto.ca/facbios/file/Han_JFE_published.pdf (author-hosted PDF, existence
confirmed via search; ScienceDirect record: https://www.sciencedirect.com/science/article/abs/pii/S0304405X12002450)
— Official-source.
Finding: delta-hedged option returns decrease **monotonically** as the underlying stock's idiosyncratic
volatility rises (holds for both calls and puts); a portfolio long delta-hedged calls in the lowest
idiosyncratic-vol quintile and short the highest quintile earns **≈1.4% per month**; not explained by standard
risk factors; attributed to dealer/intermediary constraints (limits to arbitrage) rather than a pure
volatility-risk-premium story — controlling for limits-to-arbitrage proxies cuts the effect by ~40%.

**Boyer, B., and K. Vorkink (2014). "Stock Options as Lotteries." *Journal of Finance* 69(4): 1485–1527.**
URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12152 — Official-source (venue/pages/volume
corroborated across Wiley, SSRN, BYU ScholarsArchive).
Finding: ex-ante total skewness has a strong, *negative* relationship with average option returns (not just
coskewness, contra older theory); skewness-sorted option portfolios spread **10%–50% per week**; interpreted
as intermediaries charging a premium to accommodate investor demand for lottery-like (high-skew) payoffs.

**Bottom line for item 8 (Inference, not a direct quote from either paper):** the literature does **not**
describe the vol premium "inverting" in high-idiosyncratic-vol/lottery names — both papers point the *same*
direction as the plain VRP story: sellers of premium on high-idiosyncratic-vol, high-skew names are
compensated *more*, not less, consistent with VST/CEG (high-beta AI-power names) plausibly having a *larger*
theoretical short-premium edge than MSFT/AMZN (larger, more index-like, lower idiosyncratic vol). The caveat
in both papers is that this compensation is explained by dealer intermediation costs / limits to arbitrage,
not a clean risk premium — meaning realistic frictions (financing costs, margin, inability to hedge cheaply)
plausibly eat a large share of the theoretical edge, which is exactly what this project's cost/liquidity
guardrails are designed to pressure-test.

---

## 9. Combining an equity trend signal with an options-implied signal

**Liu, M.-Y., W.-I. Chuang, and C.-L. Lo (2021). "Options-Implied Information and the Momentum Cycle."
*Journal of Financial Markets* 53: 100565.** DOI 10.1016/j.finmar.2020.100565.
URL: https://www.sciencedirect.com/science/article/abs/pii/S1386418120300343 (403 on WebFetch, consistent
with sciencedirect access pattern noted above; venue/DOI corroborated via RePEc/ResearchGate) —
Official-source (existence/venue), exact magnitude not extracted — Assumption for effect size.
Finding: implied-vol spread (put vs. call) and implied-vol skew are used to classify momentum stocks into
"early-stage" vs. "late-stage." An early-stage-identified winners-minus-losers strategy outperforms plain
price momentum; late-stage-identified outperformance underperforms plain momentum. The improvement is
concentrated in better identification of *losers*, and strengthens with option-market liquidity.
This is the most directly on-point paper for "momentum + IV" as literally described in the task.

**Heston, S., C. Jones, M. Khorram, S. Li, and H. Mo (2023). "Option Momentum." *Journal of Finance* 78(6):
3141–3192.** DOI 10.1111/jofi.13279.
URL: https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.13279 — Official-source (venue/pages/DOI
corroborated across Wiley, SSRN, RePEc, USC faculty PDF).
Finding: past straddle-return winners keep outperforming over 6–36 month horizons (options themselves have
momentum), unlike stock momentum this does *not* mean-revert/reverse long-run; tested alongside — but
distinct from — Vasquez's term-structure slope and Goyal-Saretto's IVRV as related, not identical, factors.
This is momentum *within* option returns, not equity trend + IV combined, so it answers a related but
different question than item 9 as posed.
Practical implication: Liu-Chuang-Lo's recipe (equity price momentum refined/split by an IV-based signal) is
the literature-closest match to "momentum + IV" and is conceptually implementable on a small (n=4) universe
since it doesn't require cross-sectional decile sorts — it classifies *within* a name's own momentum state.
Heston et al.'s option-return momentum would need a long panel of each name's own historical straddle returns,
likely underpowered for a 4-name, ~single-decade-of-clean-data program.

---

## Cross-cutting notes for this project

- Every headline effect size above is *before* this project's own cost/liquidity stack (conservative mid-or-worse
  fills, slippage haircut, commission on both legs both ways, half-spread on each leg, OI/spread liquidity
  gates). Goyal-Saretto is the one paper in this set that explicitly reports a post-cost number (3.9%/mo vs.
  ~22%/mo gross) — treat that ~5x shrinkage as a directional sanity check for how much of any of these other
  gross effect sizes might survive this project's own guardrails, not as a literal multiplier.
- Several items (3, 6-Pan/Poteshman, 9) require data granularity (buy-to-open intraday classification, 52-week
  IV history, panel length) that may not be fully available from EOD chain snapshots on a 4-name universe —
  flagged inline per item, not resolved here.
- Two numeric claims are explicitly **VERIFICATION FAILED at the specific-digit level** (both directionally
  confirmed, digits not): Vasquez (2017) exact return spread/t-stats; Eraker-Johannes-Polson (2003) exact
  mean-reversion-speed (κ) parameter. Both would need a full-text (likely paywalled/institutional-access) pull
  to close out.
- One unresolved minor discrepancy: Goyal-Saretto's gross monthly return figure appears as either 22.7%
  (Sharpe 0.710) or 21.9% (Sharpe 0.626) across two different secondary sources; the post-cost 3.9%/month
  figure is consistent across both, so the gross-number ambiguity does not affect the item this project would
  actually rely on.

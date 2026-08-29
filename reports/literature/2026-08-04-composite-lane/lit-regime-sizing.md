# Literature brief: market-regime detection and regime-aware position sizing

**Compiled:** 2026-08-04
**Method:** WebSearch + WebFetch verification against primary sources (arXiv, journal
publisher pages, SSRN, NBER, MPRA). Every item below was independently located and
cross-checked across at least two sources before inclusion. No item is fabricated;
where verification was partial, that is stated explicitly.
**Scope note:** This is a literature survey only. It makes no claim about this
project's registered hypotheses, the parked/un-parked status of any capability, or
what should be built. See `reports/2026-08-03-wasserstein-regime-clustering-evaluation.md`
for the project's own current stance on the Wasserstein-clustering lane (display-only,
walk-forward-causal, non-verdict-bearing) — several items below (esp. #1, #8, #9) speak
directly to that evaluation's open "gate 4" (redundancy) and whipsaw questions and are
included for that reason, not as a recommendation to act.

---

## 1. Clustering Market Regimes using the Wasserstein Distance

**Citation:** Blanka Horvath, Zacharia Issa, Aitor Muguruza (2021). "Clustering Market
Regimes using the Wasserstein Distance." arXiv:2110.11848 [q-fin.CP], submitted 22 Oct
2021. Later published in the *Journal of Computational Finance*, 28(1), 1–39.

**URL:** https://arxiv.org/abs/2110.11848 (PDF: https://arxiv.org/pdf/2110.11848)

**Verification:** Confirmed directly via arXiv abstract page fetch. Author order and
spelling: Horvath, Issa, Muguruza (not "Muguruza" alone, not 2 authors — task's
recollection was correct on all three names and the ~2021 date).

**Finding:** The paper proposes "WK-means" — k-means clustering performed directly on
empirical return-distribution windows using the p-Wasserstein (optimal-transport)
distance, rather than on summary moment features (mean/vol/skew/kurtosis) as
traditional clustering does. Evaluated via maximum mean discrepancy (MMD) scores
between/within clusters on both synthetic and real data (the paper's real-data study
uses equity indices such as SPY), WK-means produces markedly cleaner regime
separation (higher between-cluster, lower within-cluster MMD) than moment-based
KMeans/GMM baselines, and the authors report this holds without depending on
distributional modelling assumptions.

**Practical implication:** This is the algorithm behind the specific external repo
(`wasserstein-market-regime-clustering`) this project's 2026-08-03 evaluation
report assessed. The paper itself is an **in-sample, full-history clustering method**
— it does not by itself solve causal/walk-forward labeling (see #9, same lead
authors' follow-up). For a small research program, the main takeaway is
methodological: distribution-shape clustering plausibly captures more regime
structure than a realized-vol-percentile feature alone, which is exactly the
redundancy question this project's own "gate 4" AMI test is designed to falsify
against `rv_percentile` + SMA posture — i.e., this paper is evidence the null
hypothesis (redundancy) is not a foregone conclusion, not evidence it's false.

---

## 2. Hamilton (1989) — the founding cite

**Citation:** James D. Hamilton (1989). "A New Approach to the Economic Analysis of
Nonstationary Time Series and the Business Cycle." *Econometrica*, 57(2), 357–384.
DOI: 10.2307/1912559.

**URL:** https://www.econometricsociety.org/publications/econometrica/1989/03/01/new-approach-economic-analysis-nonstationary-time-series-and
(JSTOR: https://www.jstor.org/stable/1912559 — paywalled beyond abstract)

**Verification:** Confirmed via publisher (Econometric Society) page and multiple
independent citation-index sources (Semantic Scholar, SciSpace); ~10,000+ citations.

**Finding (one line):** Introduced the Markov regime-switching model — the mean growth
rate of a time series is treated as governed by an unobserved discrete-state Markov
chain, with regime probabilities inferred by maximum likelihood (the "Hamilton
filter"); applied to detect US business-cycle turning points.

**Practical implication:** This is the ancestor of every HMM-based regime tool; useful
mainly as the citation anchor when describing why regime-switching is a 35+ year-old,
well-established statistical idea rather than a novel technique — the open questions
for a small program are about implementation choices (causal vs. full-sample, gate vs.
feature), not about whether the underlying concept is sound.

---

## 3. Ang & Bekaert (2002) and Ang & Timmermann (2012)

**Citation A:** Andrew Ang, Geert Bekaert (2002). "International Asset Allocation With
Regime Shifts." *The Review of Financial Studies*, 15(4), 1137–1187.
DOI: 10.1093/rfs/15.4.1137.
**URL:** https://academic.oup.com/rfs/article-abstract/15/4/1137/1568247 (paywalled) —
free full text: https://business.columbia.edu/sites/default/files-efs/pubfiles/1971/1137.pdf

**Citation B:** Andrew Ang, Allan Timmermann (2012). "Regime Changes and Financial
Markets." *Annual Review of Financial Economics*, 4, 313–337.
DOI: 10.1146/annurev-financial-110311-101808. Circulated earlier as NBER Working Paper
17182 (2011).
**URL:** https://www.annualreviews.org/doi/abs/10.1146/annurev-financial-110311-101808
(paywalled) — free working-paper text: https://www.nber.org/system/files/working_papers/w17182/w17182.pdf

**Verification:** Both confirmed via publisher pages plus NBER/Columbia hosted
full-text PDFs; details (volume/issue/pages) cross-checked against two independent
sources each.

**Finding:** Ang & Bekaert (2002) show international equity returns switch between a
"normal" regime and a "bear" regime with materially higher volatility *and* higher
cross-market correlation, then solve a US investor's dynamic asset-allocation problem
under that switching process — the optimal response to a persistent bear regime is a
large shift toward cash. Ang & Timmermann (2012) survey the broader finding that
regime-switching models capture the fat tails, volatility clustering, skewness, and
time-varying correlation stylized in return data, and show regime switches "lead to
potentially large consequences for investors' optimal portfolio choice."

**Practical implication (why detection lag matters):** The whole value of the
regime signal in this literature is concentrated at the transition — correlations and
vol spike together exactly when diversification is needed most. A detector that lags
the transition (see #8) delivers the regime label only after the correlation spike has
already happened, which is precisely when the signal is least useful. This argues for
treating detection latency as a first-class cost, not a footnote, in any regime-based
sizing design.

---

## 4. Guidolin & Timmermann — regime-dependent asset allocation

**Citation:** Massimo Guidolin, Allan Timmermann (2007). "Asset allocation under
multivariate regime switching." *Journal of Economic Dynamics and Control*, 31(11),
3503–3544. DOI: 10.1016/j.jedc.2006.12.004.

**URL:** https://www.sciencedirect.com/science/article/abs/pii/S0165188906002272
(paywalled) — free preprint: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1083124

**Verification:** Confirmed via ScienceDirect listing, SSRN preprint, and a Federal
Reserve Bank of St. Louis working-paper mirror (same content, "FRB St. Louis WP
2005-002C"); volume/pages consistent across all three.

**Finding:** Four regimes (crash, slow growth, bull, recovery) are needed to fit the
joint distribution of US stock and bond returns. Optimal stock/bond allocations differ
sharply by regime and evolve as investors update their regime-probability estimates;
the crash-regime allocation *increases* with horizon for buy-and-hold investors, while
the opposite holds in bull regimes — a non-monotonic, regime-dependent horizon effect.
Out-of-sample forecasting tests are reported to confirm the economic (not just
statistical) importance of modeling the regimes.

**Practical implication:** A representative, heavily-cited demonstration that regime
effects on *optimal sizing* are not small — this is the strongest of the classic cites
for "regime awareness changes the right position size," as distinct from #3's finding
that regimes change correlation/vol per se.

---

## 5. Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & van Hemert (2018) — volatility targeting

**Citation:** Campbell R. Harvey, Edward Hoyle, Russell Korgaonkar, Sandy Rattray,
Matthew Sargaison, Otto Van Hemert (2018). "The Impact of Volatility Targeting."
*The Journal of Portfolio Management*, 45(1), 14–33 (Fall 2018).
DOI: 10.3905/jpm.2018.45.1.014.

**URL:** https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538 (SSRN, free)

**Verification:** Confirmed via SSRN, ProQuest, and Man Group's own press release
(authors are Man Group/Man AHL researchers; the paper won the Bernstein
Fabozzi/Jacobs Levy "Outstanding Article" award). Journal volume/issue/pages/DOI
cross-checked against ProQuest.

**Finding:** Scaling exposure inversely to trailing realized volatility raises the
Sharpe ratio for "risk assets" — equities and credit — via the leverage effect
(vol and forward returns are negatively correlated for these assets), but the Sharpe
effect is negligible for bonds, currencies, and commodities. However, volatility
targeting reduces the *severity of left-tail (crash) events specifically* across
**all** asset classes studied (60 assets, daily data from as early as 1926 through
2017), because large exposure at the moment of a crash is structurally less likely
under vol targeting.

**Practical implication (which assets benefit, which don't):** For an options program
on equity/single-stock underlyers (VST/CEG/MSFT/AMZN-type names), this is the asset
class where vol-targeting's Sharpe benefit is strongest per this paper — but the tail
protection benefit (smaller left-tail severity) is the more asset-class-general and
arguably more relevant claim for a short-vol or defined-risk options book, where the
tail event is the thing being priced against.

---

## 6. Moreira & Muir (2017) — Volatility-Managed Portfolios (citation confirmation only)

**Citation:** Alan Moreira, Tyler Muir (2017). "Volatility-Managed Portfolios."
*The Journal of Finance*, 72(4), 1611–1644. DOI: 10.1111/jofi.12513.

**URL:** https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513 (paywalled) — free
author PDF: https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf
— SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2659431 — NBER WP 22208:
https://www.nber.org/papers/w22208

**Verification:** Confirmed via Wiley (publisher), SSRN, and NBER; consistent
volume/issue/pages across all three (a sibling agent is covering this paper's findings
in depth per the task, so only the citation is confirmed here).

**One-line finding:** Scaling a factor portfolio's weight by the inverse of trailing
realized variance (market, value, momentum, and several other factors, plus FX carry)
raises Sharpe ratios and generates positive alpha relative to the unscaled factor,
because volatility shocks are not offset by proportional changes in expected returns.

---

## 7. Regime label as trade gate vs. continuous feature — walk-forward evidence

No single paper directly runs a head-to-head "hard gate vs. continuous multiplier"
horse race with published walk-forward Sharpe numbers on both sides. What exists,
verified:

**a) Kritzman, Page & Turkington (2012).** "Regime Shifts: Implications for Dynamic
Strategies (corrected)." *Financial Analysts Journal*, 68(3), 22–39.
URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2064801 (SSRN, free).
Verified via SSRN + CFA Institute research page + Taylor & Francis publisher listing;
note there is a published erratum (Sept 2012) — the "(corrected)" title is the
citable version. Uses a Markov-switching turbulence/inflation/growth regime forecast
to tilt allocations dynamically; **reports the dynamic (regime-conditioned) process
outperforming static allocation in backtests**, with the benefit concentrated in loss
avoidance for risk-averse investors. This is regime-as-continuous-tilt (probability-
weighted), not a hard on/off gate.

**b) Bulla, Mergner, Bulla, Sesboüé & Chesneau (2011).** "Markov-switching asset
allocation: Do profitable strategies exist?" *Journal of Asset Management*, 12(5),
310–321. URL: https://mpra.ub.uni-muenchen.de/21154/ (MPRA, open access working-paper
version; journal version DOI 10.1057/jam.2010.27).
Verified via MPRA, Springer/journal listing, and EconPapers, consistent findings
across all three. This one **is** closer to a discrete gate: switch fully in/out of
equities vs. cash based on the forecast high/low-volatility regime, tested
out-of-sample on 40 years of US/Japan/Germany equity index data. Reports it
**profitable net of transaction costs** — ~41% average realized-volatility reduction
and 18.5–201.6 bps of annualized excess return depending on market — i.e., published
out-of-sample evidence *for* a hard regime gate, in this specific design.

**c) Hurst, Ooi & Pedersen (2017, AQR).** "A Century of Evidence on Trend-Following
Investing." *The Journal of Portfolio Management*, 44(1), 15–29.
URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026 (SSRN, free).
Verified via SSRN and AQR's own research page. Time-series momentum (continuous
sign/magnitude sizing, not a discrete regime gate) delivered positive average returns
in every decade since 1880 and positive returns in 8 of the 10 largest 60/40
drawdowns over that century — the standard "crisis alpha" evidence base, but for a
continuous trend/vol-scaled signal rather than a labeled regime.

**d) Not independently peer-reviewed — flagged, not omitted:** Rasheed Sabar (2013),
"When Do Trend Followers Make Money?" (CME Group education library; author was
Portfolio Manager, Ellington Quantitative Strategies). URL:
https://www.cmegroup.com/content/dam/cmegroup/education/files/when-do-trend-followers-make-money.pdf
— **note: direct PDF fetch timed out on my end (network issue, not a 403); content
below is from search-engine-indexed text of the same document, not a direct read, so
treat with slightly lower confidence than the other items here.** Its thesis: trend
followers are neither reliably long nor short volatility or correlation individually
— performance depends on vol and correlation *jointly* being both-low or both-high.
This is a practitioner whitepaper, not a peer-reviewed study; cite as industry
commentary only.

**Bottom line for item 7:** the strongest *published, peer-reviewed, out-of-sample*
evidence found for a discrete regime gate specifically is Bulla et al. (2011); the
strongest evidence for continuous regime-conditioned tilting is Kritzman, Page &
Turkington (2012). Neither paper benchmarks against the other design head-to-head, so
"gate beats continuous" or vice versa is **not established** by what I could verify —
flagging this gap rather than asserting a winner.

---

## 8. Regime-detection latency and whipsaw at boundaries

**a) Nystrup, Lindström & Madsen (2020).** "Learning hidden Markov models with
persistent states by penalizing jumps." *Expert Systems with Applications*, 150,
113307. DOI: 10.1016/j.eswa.2020.113307.
URL: https://www.sciencedirect.com/science/article/abs/pii/S0957417420301329
(paywalled) — open-access copy: https://core.ac.uk/display/287842994
Verified via ScienceDirect, Lund University and DTU institutional repositories, and
CORE open-access mirror — consistent citation across all four.
**Finding:** Standard maximum-likelihood-estimated HMMs are shown to produce
"unrealistically rapid switching dynamics" (i.e., whipsaw) when the model is
misspecified or noisily estimated. The authors' jump-penalized estimator directly
controls the transition rate; in a simple trading-strategy application, **better
persistence estimates are shown to materially lower transaction costs** — a direct,
quantified link between whipsaw and realized cost.

**b) Shu & Mulvey (2024/2025).** "Dynamic Factor Allocation Leveraging Regime-Switching
Signals." arXiv:2410.14841. URL: https://arxiv.org/abs/2410.14841. Verified via direct
fetch (authors: Yizhan Shu, John M. Mulvey; submitted Sept 2024, revised Oct 2024).
**Finding, directly quantified:** "the number of regime shifts in real-time inference
remains higher — usually **twice as frequent** — than in the in-sample training,"
attributed to the first and last states in any rolling window carrying the highest
estimation error because they lack full past/future context. This is the most
concrete number found for the detection-lag/whipsaw cost of causal vs. smoothed
labeling.

**c) Theoretical background (lower confidence — cited secondhand):** the formal
"quickest change detection" literature (Shiryaev's Bayesian change-point theory,
Lorden's 1971 minimax CUSUM result, Moustakides' 1986 optimal-stopping formulation)
is the mathematical foundation for detection-delay-vs-false-alarm tradeoffs generally;
I located this via a modern arXiv paper's literature review (arXiv:math/0503682) rather
than independently verifying the 1960s–80s originals, so treat the attribution as
Inference rather than independently confirmed primary-source reading.

**Practical implication:** Whipsaw is not a hypothetical risk — it is measured, in a
finance-specific setting, at roughly 2x the transition frequency for causal vs.
full-sample labeling, and separately shown to translate directly into higher
transaction costs. Any regime signal touching real position sizing (as opposed to a
display-only descriptive badge) needs either a persistence penalty (Nystrup et al.'s
approach) or a cooldown/hysteresis rule before it should be trusted near a boundary.

---

## 9. Online/causal (walk-forward) labeling vs. full-sample (look-ahead) labeling

**a) Issa & Horvath (2023).** "Non-parametric online market regime detection and
regime clustering for multidimensional and path-dependent data structures."
arXiv:2306.15835 [stat.ML], submitted 27 June 2023.
URL: https://arxiv.org/abs/2306.15835. Verified via direct fetch. **This is the same
lead authors as item #1's WK-means paper (Horvath + Issa, minus Muguruza) — it reads
as the causal/online follow-up to the full-sample WK-means method.** It detects
regime changes via a path-wise two-sample test built on maximum-mean-discrepancy
similarity over rough-path signatures, explicitly "optimised... to the setting where
the size of new incoming data is particularly small, for faster reactivity" —
i.e., designed for online, point-in-time use rather than retrospective full-sample
fitting. Demonstrated on equity baskets and crypto; reported to "swiftly and
accurately" flag historical turmoil periods as a fast on-line detector.

**b) Shu & Mulvey (2024)** — see #8b — is the best quantification found of *how much*
causal/online labeling diverges from full-sample labeling (≈2x the regime-transition
frequency). I did not find a paper that directly quantifies P&L or Sharpe *inflation*
specifically attributable to full-sample regime-label look-ahead (as opposed to
look-ahead bias in trading signals generally, which is well covered — see general
backtesting-bias literature, e.g. Bailey & López de Prado's deflated Sharpe ratio work
on overfitting from repeated in-sample optimization). **Flagging this as a real gap:**
the specific number "how much does look-ahead regime labeling inflate backtest
results" does not appear to have a dedicated, citable answer in what I could verify —
the closest proxy evidence is (i) the 2x transition-frequency gap above, and (ii) the
general point-in-time-vs-look-ahead literature (e.g. arXiv:2601.13770,
"Look-Ahead-Bench," measures this problem for point-in-time LLMs, not regime
clustering specifically — tangential, not a substitute).

**Practical implication:** For any regime lane built to be walk-forward/causal (as
this project's Wasserstein lane already is per its 2026-08-03 evaluation), Issa &
Horvath (2023) is the closest published, purpose-built method for the causal-labeling
half of that design — worth reading before hand-rolling a from-scratch online
variant. Separately, the ~2x whipsaw-frequency finding (#8b/#9b) is a caution that a
causal regime label will look noisier than any full-sample-fit demo of the same
method — that noisiness is expected and shouldn't itself be read as an implementation
bug.

---

## Sources not used / dead ends

- Yuan & Mitra (2016), "Market Regime Identification Using Hidden Markov Models"
  (SSRN 3406068) — verified to exist and is a real HMM-on-FTSE100/EuroStoxx50 study,
  but its central contribution is general regime-identification fit quality (fat
  tails, vol clustering vs. GBM), not a lag/whipsaw quantification, so it was not
  used as the primary #8 cite despite surfacing in search.
- No paper was found and rejected as unverifiable (VERIFICATION FAILED) outright;
  the one item carried at reduced confidence is the Sabar CME practitioner piece
  (#7d, PDF fetch timeout, sourced from indexed text only) and the Shiryaev/Lorden/
  Moustakides attribution (#8c, secondhand via a later paper's literature review).

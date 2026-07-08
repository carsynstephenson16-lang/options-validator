# H3 Options Strategy Audit

Research plan used for this audit. I verified the memo’s core claims about friction, stops, ticker expansion, conditional volatility risk premium, the trend filter, the exact cited papers, strategy family fit, and parity-based feature construction. I prioritized peer-reviewed finance papers, SSRN and arXiv papers with verifiable records, plus Cboe and OCC documentation. Evidence against H3 included any finding that the cited literature does not support the exact rule set, that realistic costs or margin erase the edge, that SPY and QQQ add hidden concentration instead of independent sample, or that parity-derived closes are not reliable enough for lagged features without separate validation. The uploaded attachment states that the draft memo, width-sweep note, single-name diagnostics, `README.md`, and `config.py` should be attached if available, but those materials were not present here, which limits direct audit of H1, H2, and the single-name rejection logic. fileciteturn0file0

## Executive verdict

**Final recommendation: Revise H3 before registration.**

H3 is plausible but unproven. The strongest evidence supports a negative market volatility risk premium in S&P 500 index options, the value of trading-cost realism, and the idea that trend filters help during major drawdowns. The evidence does **not** directly validate this exact bundle of rules: SPY plus QQQ, approximate 0.50-delta short put, exactly $5 width, 30 to 45 DTE, 70th-percentile VRP threshold, no stop, and auto-close at 7 DTE. citeturn14view0turn14view1turn15view1turn19view0turn21view1

The main revision is simple. Make **SPY the primary registered strategy** and treat **QQQ as a separate robustness sleeve**, not part of the core pass or fail test. The literature support is materially stronger for broad S&P 500 index option risk premium than for a pooled SPY and QQQ test. QQQ also adds concentrated Nasdaq-100 exposure, and Invesco states that QQQ is non-diversified and more exposed to sector concentration risk. SPY’s top holdings already include NVIDIA, Apple, Microsoft, Amazon, Alphabet, Broadcom, Micron, Meta, and Tesla, so a pooled SPY and QQQ test understates overlap. citeturn7view2turn9view0turn8view2

A second revision is methodological. Do **not** rely on parity-derived closes for trend or realized-volatility features unless they first match known historical ETF closes closely enough in a locked validation step. Cboe’s volatility-index methodology infers an **option-implied forward** from ATM call and put midquotes after strict quote filters. That is not the same object as a clean ETF close, and ETF options are American-style and physically settled, which further weakens a direct spot-close substitution. citeturn26view0turn27view0turn21view1turn31view0

No clearly better new family surfaced from the literature under this harness. Long-vol and straddle-style ideas face premium drag from the same negative volatility risk premium literature. 0DTE ideas are a poor fit for an EOD harness and have bad retail evidence. Deep-learning options strategies rely on much broader data and modeling infrastructure than this project allows. citeturn15view1turn22academia2turn15view0turn16academia0

## Claim audit

| Claim | Verdict | Evidence | Caveats | Implication |
|---|---|---|---|---|
| H1 and H2 failed mainly because frictions consumed too much credit on narrow or low-delta spreads, not because of ticker selection. | Unverifiable | Santa-Clara and Saretto find short-option strategies on the S&P 500 attractive gross, yet trading costs and margin requirements severely condition implementation. Goyal and Saretto also show trading frictions reduce option-strategy profitability. citeturn14view0turn14view1 | The project files needed to audit H1 and H2 diagnostics were not attached here. fileciteturn0file0 | Treat this as a plausible project diagnosis, not a verified project fact. |
| The 2x-credit stop was the loss engine because conservative close costs turned quote noise into realized losses. | Partly supported | The options literature in this source set strongly supports cost sensitivity. It does not directly test a 2x-credit stop on vertical spreads, yet it does show that trading frictions and margin materially damage option strategies. citeturn14view0turn14view1 | No attached trade log or stop-attribution file was available. fileciteturn0file0 | Removing the stop is reasonable for a clean test, but the memo’s causal claim is not proven. |
| Expanding into VST, CEG, MSFT, and AMZN should be rejected because of liquidity, sample size, earnings gap risk, wider spreads, and or failed diagnostics. | Partly supported | The harness preference for SPY and QQQ is sensible because ETF options are standard, heavily used listed products, while equity and ETF options are physically settled and American-style, which adds exercise and assignment complexity. QQQ itself is described by Invesco as one of the most heavily traded ETFs. citeturn21view1turn8view2turn31view0 | The missing single-name diagnostics keep the strongest part of this claim out of reach. MSFT and AMZN are far more liquid than VST or CEG, so a blanket rejection needs project data. fileciteturn0file0 | Reject VST and CEG under current evidence. Keep MSFT and AMZN outside the primary hypothesis unless a separate, pre-specified single-name protocol handles earnings and quote quality. |
| The strongest candidate is `H3-cvrp-spy-qqq-atm5w-noStop-eod-v1`. | Unsupported | The papers support volatility risk premium, cost realism, and broad trend logic. None of them directly support this exact strategy bundle. citeturn14view0turn14view1turn15view1turn19view0 | “Strongest candidate” depends on missing internal comparisons and diagnostics. fileciteturn0file0 | H3 deserves revision before any registration. |
| The best-supported edge is conditional volatility risk premium, not unconditional short-premium selling. | Partly supported | Bakshi and Kapadia support a negative market volatility risk premium in S&P 500 index options. Goyal and Saretto support IV versus historical-volatility differences as return predictors. Hansen, Huang, Tong, and Wang support time variation in VRP. citeturn15view1turn14view1turn12academia6 | The cited papers do not directly test the memo’s exact conditional filter on ETF put spreads. | Use conditional VRP as the core economic prior. Do not treat it as proof of net edge for this exact spread. |
| The memo cites Santa-Clara and Saretto 2009, Goyal and Saretto 2009, Bakshi and Kapadia 2003, arXiv 2112.05302, arXiv 2607.00883, arXiv 2303.16371, and Beckmeyer, Branger, Gayda on 0DTE. | Supported | All of those citations exist and were verified. citeturn14view0turn14view1turn15view1turn12academia6turn25academia0turn22academia2turn15view0 | Existence does not mean strong support for H3. | Keep the citations. Downgrade how strongly they are said to support the exact strategy. |
| Long-vol, straddles, calendars, 0DTE, and deep-learning options strategies are likely unsuitable for this harness because of costs, data requirements, sample size, or premium drag. | Partly supported | Negative volatility risk premium evidence cuts against persistent long-vol or long-straddle exposure. Beckmeyer, Branger, and Gayda show large retail losses in 0DTE S&P 500 options. Tan, Roberts, and Zohren rely on a broad S&P 100 option data set and end-to-end deep learning. citeturn15view1turn22academia2turn15view0turn16academia0 | The literature does not rule out every calendar or long-vol design in all settings. It rules them out for this harness more by fit than by universal impossibility. | Keep these families out of the registered test set for now. |
| Underlying closes can be derived from cached chains using put-call parity well enough for lagged trend and realized-volatility features. | Unsupported | Cboe’s methodology uses ATM call and put midpoint quotes to infer an **option-implied forward** and requires strict quote filtering. That supports a forward estimate, not direct proof of accurate ETF spot closes. ETF options are American-style and physically settled, which adds dividend and exercise complications. citeturn26view0turn27view0turn21view1turn31view0 | Accuracy versus true underlying close was not documented in the material available here. | Use direct ETF closes if present. If absent, parity-based features need a locked validation step before any trading test. |

## Literature verification

| Paper | Exists | What it actually finds | Support for H3 | Costs, margin, liquidity, realistic fills | Data fit with this harness |
|---|---|---|---|---|---|
| Santa-Clara and Saretto, “Option Strategies: Good Deals and Margin Calls” | Yes | The abstract states that short-option strategies in S&P 500 options look attractive, yet trading costs and margin requirements severely condition implementation, with margin calls forcing exits while trades are losing. citeturn14view0 | **Indirect support.** It supports skepticism, cost realism, and defined-risk design. It does not test H3’s exact filter set. | **Directly relevant.** This paper is one of the strongest warnings in the source set against gross-return storytelling. citeturn14view0 | Broadly compatible. It studies S&P 500 options, which are closer to SPY or SPX logic than single-name options. |
| Goyal and Saretto, “Cross-section of option returns and volatility” | Yes | They sort stocks on historical realized volatility minus ATM implied volatility and find large returns in long cheap-vol and short expensive-vol portfolios. They also report that transaction costs reduce profitability and that short margin adds another wedge. citeturn14view1 | **Indirect support.** It supports IV versus RV as a signal. It does not test ETF vertical put spreads or the memo’s threshold. | **Partly survives frictions in their setup.** Their abstract and introduction show reduced, not erased, long-short profits after spreads, while margin hurts short positions. citeturn14view1 | Partial fit only. Their design needs a broad stock-option cross-section, not a two-ETF harness. |
| Bakshi and Kapadia, “Delta-Hedged Gains and the Negative Market Volatility Risk Premium” | Yes | Using S&P 500 index options, they find delta-hedged strategies underperform zero, the underperformance is smaller away from the money, larger in high-volatility states, and consistent with a negative market volatility risk premium. citeturn15view1 | **Indirect support.** This is the strongest direct foundation for a short-volatility prior in broad index options. It does not test credit spreads, stops, or 7-DTE exits. | The paper is about delta-hedged option portfolios, not retail spread execution. It does not solve fill, slippage, or assignment issues. | Good conceptual fit for SPY. Weaker fit for pooled SPY plus QQQ. |
| Hansen, Huang, Tong, Wang, “Realized GARCH, CBOE VIX, and the Volatility Risk Premium” | Yes | The paper derives closed-form expressions for VIX and VRP in a Realized GARCH setting and shows improved modeling of time-varying VRP in S&P 500 data. citeturn12academia6 | **Indirect support.** It supports the idea that VRP is conditional and state-varying. It does not justify the memo’s exact 70th-percentile rule. | It is not a transaction-cost paper. It offers no evidence on realistic spread fills. | Partial fit. The model uses richer volatility inputs than a simple EOD chain harness. |
| Noguer I Alonso and Al Fallouji, “Tail Risk Management with Puts and Trend Following: A CVaR Framework for Crashes and Drawdowns” | Yes | This very recent paper blends long puts with trend following in a CVaR framework and argues that convex insurance helps on jump impact while trend following helps in persistent drawdowns. The reported results are stylized and calibration-dependent. citeturn25academia0 | **Not direct.** It supports trend-based crash defense in principle, not short put spreads. | It does not validate realistic retail fills or this harness’s cost model. | Weak fit. It is a theoretical tail-allocation paper, not a direct rules-based spread study. |
| Bakshi, Crosby, Gao, “Dark Matter in Volatility and Equity Option Risk Premiums” | Yes | The paper decomposes option risk premia and reports evidence supportive of negative risk premia tied to jumps crossing the strike and local time, with negative premia for OTM call options and straddles in weekly and farther-dated index options. citeturn22academia2 | **Indirect support.** It supports the broad risk-premium idea and warns that strike-crossing risk matters. It does not support H3 directly. | It is not an implementation paper. It does not test conservative retail-like fills. | Partial fit only. It uses richer surface and decomposition work than this harness holds. |
| Beckmeyer, Branger, Gayda, “Retail Traders Love 0DTE Options... But Should They?” | Yes | Using retail-identified 0DTE trades, the authors find that more than 75 percent of retail S&P 500 option trades involve 0DTE contracts and that retail investors still suffer substantial losses despite lower effective spreads. citeturn15view0 | **Supports rejection of 0DTE.** It says little about H3 beyond that. | Strongly relevant to retail losses. Strongly against 0DTE migration. | Poor fit for harness testing because it relies on retail-trade identification and same-day data. |
| Tan, Roberts, Zohren, “Deep Learning for Options Trading: An End-To-End Approach” | Yes | The paper backtests deep-learning models on more than a decade of S&P 100 option contracts and reports better risk-adjusted performance than rules-based baselines, with turnover regularization helping under high transaction costs. citeturn16academia0 | **Not support for H3.** It supports the view that deep learning belongs in a different research stack. | It explicitly addresses transaction costs, yet within a large-scale ML pipeline. | Poor fit. The input data and model scope exceed this harness by a wide margin. |

### What the literature does and does not support

The literature supports three points with reasonable strength. First, broad-index option sellers have historically earned compensation for bearing volatility and tail risk. Second, option frictions and margin are strong enough to erase a large share of gross edge. Third, trend-like overlays often behave best in crisis periods, which makes a long-run trend filter defensible as a crash-avoidance prior. citeturn15view1turn14view0turn14view1turn19view0

The literature does **not** support several memo specifics with the same strength. No cited paper validates a 70th-percentile VRP threshold, a no-stop rule, a 7-DTE exit, an exact $5 width, or pooled SPY and QQQ as one registered claim. Those items are best described as reasonable design choices, not literature-backed facts. citeturn14view1turn12academia6turn15view1

## H3 evaluation

**Evidence**

Conditional VRP is a credible timing signal. Bakshi and Kapadia show a negative market volatility risk premium in S&P 500 index options, and Hansen, Huang, Tong, and Wang show VRP is time varying rather than static. Goyal and Saretto add evidence that large gaps between historical realized volatility and ATM implied volatility are linked to option returns, though in a stock-option cross-section rather than in ETF put spreads. citeturn15view1turn12academia6turn14view1

The 200-day SMA filter is defensible as a crash-avoidance prior, though it is not proven inside this exact strategy. Hurst, Ooi, and Pedersen report positive time-series-momentum returns across decades and strong behavior in 8 of the 10 largest crisis periods they study. That supports a simple trend gate as a regime filter, especially when the strategy’s left tail is driven by downside shocks. citeturn19view0

The case for ATM $5-wide put credit spreads is weaker. No paper in this source set tests “ATM, $5 wide, 30 to 45 DTE, close at 7 DTE” as a package. Still, wider spreads with larger gross credit leave less room for commissions and spread loss to consume the entire premium than narrow, low-credit structures. Santa-Clara and Saretto and Goyal and Saretto both show that option strategies live or die on friction share once costs and margin enter. citeturn14view0turn14view1

The “no stop, close at 7 DTE” rule is **plausible but unproven**. The literature here supports cost discipline and skepticism toward excessive trading. It does not provide direct evidence for this exact exit rule. The best argument for “no stop” is structural. If a defined-risk spread already has a hard maximum loss, repeated stopouts on conservative closes risk turning transient quote widening into realized loss. That is a reasoned choice, not a literature-verified result. citeturn14view0turn14view1

The 70th-percentile VRP threshold is the weakest element in H3. The cited work supports state variation in VRP. It does **not** support this threshold in particular. A fixed top-30-percent regime rule is not absurd, yet it still looks like a parameter that needs pre-commitment discipline because the literature does not point to “70th percentile” as a natural breakpoint. citeturn14view1turn12academia6

SPY and QQQ together create hidden concentration risk. SPY already holds a large share of today’s mega-cap growth names near the top of the index, while QQQ tracks the Nasdaq-100, is non-diversified, and is more exposed to sector concentration. Pooling both into one registered claim risks treating two related U.S. equity-beta exposures as if they were independent evidence streams. citeturn7view2turn9view0turn8view2

**Inference**

H3 has a coherent economic story. It sells downside insurance only in states where option-implied volatility is rich to realized volatility and where the underlying is already in an established uptrend. That is better grounded than unconditional short-premium selling. Yet the support is strongest at a **concept** level, not at the exact-rule level.

The strategy’s best features are the conditional VRP gate, the broad-index focus, the defined-risk spread structure, and the effort to keep position-level loss within a small sleeve. The weakest features are the 70th-percentile threshold, the pooled SPY and QQQ design, and the lack of direct evidence for “no stop plus 7-DTE close.”

**Speculation**

The most likely failure modes are clear.

| Failure mode | Why it matters |
|---|---|
| Cost share still too high | Even wider spreads fail if conservative fill loss eats too much of the opening credit. citeturn14view0turn14view1 |
| Crash-gap concentration | ATM short put spreads still lose fast in sharp selloffs, especially if the trend filter lags. citeturn19view0turn21view1 |
| Weak sample count | With one open spread max per underlying and multi-week holding periods, the usable sample is limited. |
| Threshold fragility | If results depend on the exact 70th-percentile VRP cutoff, the signal is not robust. citeturn14view1turn12academia6 |
| SPY and QQQ overlap | Pooled results may double-count the same risk theme rather than add independent evidence. citeturn7view2turn9view0turn8view2 |
| Assignment and settlement edge cases | ETF options are physically settled and American-style, so assignment handling matters near deep ITM or expiry. citeturn21view1turn31view0 |
| Bad feature construction | Parity-based closes without prior validation risk contaminating the signal inputs. citeturn26view0turn27view0 |

**Evidence that would kill H3 before any OOS reveal**

A pre-OOS rejection is appropriate if any of the following appear in the in-sample audit: negative net expectancy after conservative fills and fees, net non-positive performance after a modest extra spread penalty, a result dominated by one crisis rebound cluster, strong dependence on QQQ rather than SPY, too few valid trades, or material performance changes when direct ETF closes replace parity-derived proxies. Those are the right failure tests because the source base already tells us that costs, state dependence, and data construction matter more than gross-theory elegance. citeturn14view0turn14view1turn12academia6turn26view0turn27view0

## Alternative strategy ranking

No alternative family in this source set beats a revised H3 on both economic logic and harness fit. The ranking below therefore mixes plausible alternatives with rejected families.

| Strategy | Evidence strength | Data feasibility | Cost sensitivity | Liquidity | Turnover | Assignment and gap risk | Overfit risk | Crowd and capacity risk | Fit with $14k and $600 cap | Expected sample size | Kill reason |
|---|---|---:|---|---|---|---|---|---|---|---|---|
| **H3 revised, SPY primary only, QQQ separate robustness sleeve** | Medium | High | Medium | Strong | Medium | Medium | Medium | Medium | Good | Low to medium | Reject if SPY-only net expectancy is non-positive after conservative fills. |
| **H3 original, pooled SPY and QQQ** | Medium minus | High | Medium | Strong | Medium | Medium | Medium to high | Medium | Good | Medium | Reject because pooling weakens inference through concentration overlap. citeturn7view2turn9view0turn8view2 |
| **Defined-risk SPY put-write proxy, monthly ATM or near-ATM spread, no VRP conditioning** | Medium minus | High | Medium | Strong | Low | Medium | Low | High | Good | Low | Reject if unconditional short premium underperforms the conditional VRP version. citeturn14view0turn15view1 |
| **OTM 25 to 35 delta SPY put credit spread with same VRP and trend gates** | Low to medium | High | High | Strong to medium | Medium | Medium | Medium | High | Good | Low to medium | Reject if credit is too small after conservative fills, which recreates the narrow-credit problem. citeturn14view0turn14view1 |
| **Long-vol or long-straddle timing strategy** | Low | High | Medium | Strong | Medium | Low | Medium | Medium | Good | Low to medium | Reject because negative volatility risk premium works against persistent long-vol carry. citeturn15view1turn22academia2 |
| **0DTE short-premium family** | Low for this harness | Low | High | Strong | High | High | High | High | Mechanical fit only | High if intraday data existed | Reject because it is intraday by nature and retail evidence is poor. citeturn15view0 |
| **Deep-learning options strategy** | Medium in its own literature | Low | Model dependent | Broad-universe dependent | High | Varies | High | Medium | Poor | High only with broad data | Reject because the data and model stack do not match this harness. citeturn16academia0 |

The best “alternative” is therefore not a brand-new family. It is a **revised H3** with a tighter scope and cleaner inference. That keeps the strongest economic prior and removes the weakest structural choice, which is pooled SPY plus QQQ.

## Recommended next hypothesis

**Chosen action: Revise H3 before registration.**

**Reason.** The evidence backs conditional VRP, cost realism, and crash-regime awareness. It does not back the exact memo bundle strongly enough for unchanged registration. A narrower SPY-first version is better aligned with the literature and yields a cleaner test.

**Recommended falsifiable pre-registration**

**Name:** `H3R-cvrp-spy-atm5w-noStop-eod-v2`

**Hypothesis:**  
A defined-risk SPY put credit spread strategy entered only when prior-day implied volatility is rich to prior realized volatility and prior-day price is above its 200-day SMA has **positive net expectancy after conservative fills, commissions, quote-quality filters, and assignment handling** during 2018-01-01 through 2022-12-31.

**Rules**

| Field | Rule |
|---|---|
| Primary universe | SPY only |
| Robustness sleeve | QQQ tested separately, with no effect on primary pass or fail |
| Warmup | 252 prior trading days required before any signal is live |
| Volatility signal | Prior-day ATM implied volatility minus prior 21-trading-day realized volatility |
| VRP gate | Enter only when that signal is at or above its own trailing 252-day 70th percentile |
| Trend gate | Prior-day close above prior-day 200-day SMA |
| Expiry choice | Nearest listed expiry in the 30 to 45 DTE window |
| Structure | Sell the put closest to 0.50 delta and buy the put exactly $5 lower |
| Credit gate | Conservative opening credit of at least $1.50, using short-leg bid minus long-leg ask |
| Position count | One open SPY spread maximum |
| Exit | Close at 7 DTE using conservative close pricing, short-leg ask minus long-leg bid |
| Stop | None |
| Profit target | None |
| Risk cap | Max economic loss including fees stays within the project cap |
| Feature data | Direct SPY close series preferred. If absent, parity-derived proxy must pass a locked validation test first. |

**Kill criteria before any OOS reveal**

| Test | Reject before OOS if this occurs |
|---|---|
| Net expectancy | Mean net P&L per trade is zero or below |
| Cost robustness | Net expectancy falls to zero or below after a modest extra fill penalty |
| Year concentration | One calendar year dominates the full result |
| Trade concentration | One small cluster of trades drives most total P&L |
| Sample sufficiency | Valid trade count is too thin for a meaningful inference |
| SPY versus QQQ reliance | SPY fails while pooled SPY plus QQQ looks acceptable |
| Feature integrity | Using direct closes materially changes the signal versus parity-derived proxies |
| Tail behavior | Loss profile breaches the stated sleeve and max-loss design intent |
| Quote quality | A meaningful share of fills rely on crossed, zero-bid, or otherwise bad quotes |

## Implementation notes

For an EOD harness, the main priority is data integrity. Cboe’s methodology is useful here because it shows what robust option-data filtering looks like. The methodology infers an option-implied forward from ATM call and put midpoint quotes, rejects series with null quotes or bid above ask, and stops if key quote conditions fail. Use the same spirit in the backtest. Reject stale, crossed, zero-bid, or structurally broken quotes before strategy logic ever runs. citeturn26view0turn27view0

Use direct ETF closes for the 200-day SMA and realized-volatility inputs if those prices exist in the local data stack. If direct closes do not exist, parity-derived substitutes need a locked validation step against known historical closes before any strategy result is counted. Cboe’s formula gives an implied forward, not a guaranteed close proxy. citeturn26view0turn27view0

Treat ETF option mechanics seriously. Cboe states that ETF options are physically settled and American-style. OCC states that exercise or assignment results in acquisition or delivery of the underlying shares. That means the harness needs explicit handling for deep ITM exits, expiration-near assignment exposure, and post-settlement stock positions. citeturn21view1turn31view0

Keep P&L decomposition explicit. Each trade record should store opening credit, closing debit, estimated commissions and fees, spread loss from conservative execution, and any assignment-related cash flow. Without that breakdown, there is no clean audit trail for the memo’s friction claims.

**Do not do this**

| Prohibited move | Why it matters |
|---|---|
| Do not change the 70th-percentile threshold after seeing the in-sample result. | That turns a registered test into a rescued test. |
| Do not re-pool SPY and QQQ if SPY fails on its own. | That weakens causal inference. |
| Do not swap conservative fills for midpoint fills after poor results. | The literature says frictions are load-bearing. citeturn14view0turn14view1 |
| Do not add profit targets or dynamic stops after seeing path behavior. | That is post hoc tuning. |
| Do not add single names after SPY underperforms. | That changes the hypothesis and reopens the search space. |
| Do not remove 2020 or 2022 from the in-sample period. | Those regimes are central to the project question. |
| Do not let parity-derived features into the final test without prior validation. | Bad feature construction contaminates the whole signal stack. citeturn26view0turn27view0 |
| Do not use OOS as a debugging sandbox. | That destroys the holdout. |

## Bibliography

Santa-Clara, Pedro, and Alessio Saretto, “Option Strategies: Good Deals and Margin Calls.” citeturn14view0

Goyal, Amit, and Alessio Saretto, “Cross-section of Option Returns and Volatility.” citeturn14view1

Bakshi, Gurdip, and Nikunj Kapadia, “Delta-Hedged Gains and the Negative Market Volatility Risk Premium.” citeturn15view1

Hansen, Peter Reinhard, Zhuo Huang, Chen Tong, and Tianyi Wang, “Realized GARCH, CBOE VIX, and the Volatility Risk Premium.” citeturn12academia6

Noguer I Alonso, Miquel, and Ali Al Fallouji, “Tail Risk Management with Puts and Trend Following: A CVaR Framework for Crashes and Drawdowns.” citeturn25academia0

Bakshi, Gurdip, John Crosby, and Xiaohui Gao, “Dark Matter in Volatility and Equity Option Risk Premiums.” citeturn22academia2

Beckmeyer, Heiner, Nicole Branger, and Leander Gayda, “Retail Traders Love 0DTE Options... But Should They?” citeturn15view0

Tan, Wee Ling, Stephen Roberts, and Stefan Zohren, “Deep Learning for Options Trading: An End-To-End Approach.” citeturn16academia0

Hurst, Brian, Yao Hua Ooi, and Lasse Heje Pedersen, “A Century of Evidence on Trend-Following Investing.” citeturn19view0

Cboe, “Cboe Volatility Index Mathematics Methodology.” citeturn26view0turn27view0

Cboe, “The Facts About Options.” citeturn21view1

OCC, “Equity Options Product Specifications.” citeturn31view0

State Street, SPY fund page and top holdings. citeturn7view2

Invesco, QQQ fund page and product details. citeturn9view0turn8view2

Uploaded project attachment listing additional files that were not present in this audit. fileciteturn0file0

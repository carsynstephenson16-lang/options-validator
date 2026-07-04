# H3 candidate research memo — DRAFT, NOT REGISTERED (2026-07-03)

> **SUPERSEDED (2026-07-03, same day):** after the external audit
> (`2026-07-04-chatgpt-deep-research-h3-audit-report.md`) and a fresh
> multi-workstream comparison, this memo's pooled-SPY/QQQ H3 is replaced by
> **H3R** — see `specs/2026-07-03-h3r-preregistration-DRAFT.md` and
> `plans/2026-07-03-h3r-implementation-plan-DRAFT.md`. Kept for the record.

**Status: awaiting owner review. Nothing in this document is registered, run,
or committed as a hypothesis. No OOS look is proposed. Holdout remains sealed
at 0/3.**

---

## 1. What the H1/H2 failure actually taught us

The width sweep and single-name diagnostics establish four mechanical facts:

1. **Frictions are fixed per contract; credit scales with width/moneyness.**
   Round-trip friction (≈$2.60 commissions + two crossed half-spreads + 1%
   adverse haircut) was ~50–100% of the ~$29 credit at $2-wide/30Δ and still
   ~30–40% of the ~$65–75 credit at $5-wide. Expectancy improved monotonically
   (−$185 → −$103 → −$39) purely as the friction share shrank — and still
   never reached zero (CI90 upper bound −$18 at $5).
2. **The 2×credit stop, measured against conservative cost-to-close, was the
   loss engine.** H1 anatomy: every loss was a stop; wins were only
   profit-targets. A stop keyed to quote noise in a conservative fill model
   converts noise into realized losses.
3. **The fine-strike universe was a mirage.** MSFT lost its $2 grid after
   2019; AMZN had none pre-split; VST and NOW never passed OI/spread gates.
   Structures must use strikes that actually exist at scale ($1 grids near
   ATM on SPY/QQQ; $5 grids on high-priced names).
4. **The FAIL is universal across names.** Every scoreable symbol failed
   individually. Changing tickers does not change the cost arithmetic.

Conclusion: the failure was **structural (tiny edge vs. fixed frictions +
noise-triggered stops)**, not a ticker-selection problem.

## 2. Candidate tickers: VST, CEG, MSFT, AMZN — evaluated and rejected

| Ticker | Cache? | In-sample (2018–2022) reality | Verdict |
|---|---|---|---|
| VST | yes (2134 d) | **Zero trades** — OI < 100 floor, >10% spreads for most of the window; liquidity is a post-2023 AI-era phenomenon, i.e. inside the blind OOS period we may not develop on | Unusable in-sample |
| CEG | **no** | Began regular-way trading 2022-02-02 (Exelon spinoff); ~11 months of in-sample history, early options spinoff-adjusted; would require new data spend | Dead on arrival |
| AMZN | yes | No usable grid pre-June-2022 split; the 14 in-sample trades all post-split; single-name diag: −$240/trade, worst of all names | Insufficient usable sample |
| MSFT | yes | Liquid throughout, but wider quoted spreads than SPY/QQQ, quarterly earnings gap risk unmanageable at EOD cadence; diag FAIL −$85/trade | Dominated by SPY/QQQ |

**Answer to the owner's question: no.** These names do not offer a better
opportunity than the failed family. The single-name diagnostics already
proved the FAIL is friction-structural and universal. Single names add
earnings gap risk (EOD data cannot exit intraday through a gap), wider
spreads (higher friction), and smaller samples. SPY/QQQ remain the only
underlyings in the cache where the friction share can be driven into single
digits.

## 3. Literature synthesis (primary sources)

- **Santa-Clara & Saretto (JFM 2009)**: index option-selling Sharpe ratios
  look great at mid quotes; transaction costs and margin calls gut them, and
  margin forces exits exactly at loss points. Confirms our harness's frozen
  conservative-fill philosophy is the correct null.
- **Goyal & Saretto (JFE 2009)** and **Bakshi & Kapadia (RFS 2003)**: the one
  robust, replicated, EOD-computable option edge is the **volatility risk
  premium conditional on the realized-vol/implied-vol gap** — options are
  systematically rich when IV is high relative to realized vol, and the gap
  predicts option returns.
- **arXiv 2112.05302 (Realized GARCH, VIX, VRP)**: the VRP is time-varying
  and forecastable from realized measures; supports *conditioning* premium
  sales on an RV-forecast-vs-IV comparison rather than selling
  unconditionally (which is exactly what H1/H2 did).
- **arXiv 2508.16598 (Kelly/VIX put-writing sizing)**: sizing/regime scaling
  matters as much as signal; their best returns come from 0–5 DTE far-OTM
  SPXW — a regime our harness correctly excludes (DTE_MIN=10, EOD data), and
  which the 0DTE retail-loss evidence (Beckmeyer–Branger–Gayda, SSRN 4404704)
  says is a friction meat-grinder for non-institutional flow.
- **arXiv 2607.00883 (CVaR puts + trend following)**: long puts reprice
  instantly on jumps but carry premium drag; trend following is late on jumps
  but cheap in drawdowns. For a premium *seller*, the actionable inverse: use
  a trend filter to refuse to sell into crash/drawdown regimes rather than
  buying protection.
- **arXiv 2303.16371 (Dark matter in option risk premiums)**: OTM options and
  straddles carry negative premiums for buyers (unspanned jump risk) — long
  premium structures lose unconditionally; only conditional long-vol has a
  chance, and it must clear double friction.
- **arXiv 2407.21791 (Deep learning options trading)** and **2504.06208
  (deep hedging on the IV surface)**: end-to-end ML works on S&P-100-wide
  cross-sections with a decade of data and explicit turnover regularization.
  Our sample (2 underlyings × 5 EOD years) cannot support deep models; the
  transferable lesson is **minimize turnover when frictions are high**.

**Most plausible edge source for this harness:** conditional VRP on the most
liquid indices, expressed in a structure whose credit is large relative to
fixed frictions, with no quote-noise stop, entered only when an RV-forecast
says IV is rich and a trend filter says we are not selling into a crash.

## 4. Candidate family ranking

| # | Family | Evidence | Data needed | Already supported? | Expected failure mode | Cost sensitivity | Difficulty | Overfit risk | P(pass in-sample) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Regime-filtered conditional VRP, ATM-ish defined-risk, SPY/QQQ** | Goyal-Saretto; Bakshi-Kapadia; 2112.05302; 2607.00883 (filter) | cached chains + parity-derived closes | **yes** (needs small feature tool) | conditioned edge still < frictions in 2018–22 regimes; entry clustering shrinks effective sample | low-moderate (friction ≈ 6–10% of credit) | low | low-moderate (2 filter params, frozen) | **~25–35%** |
| 2 | Predictive single-stock direction (VST/CEG/MSFT/AMZN) | weak: short-horizon return predictability from lagged daily features is near-zero post-2000 | 2017+ closes; CEG data purchase | partially (VST/CEG unusable) | no signal; double friction on debit structures; earnings gaps | high | medium | high | ~5–10% |
| 3 | Vol expansion/compression (long straddles / calendars when IV < RV forecast) | Goyal-Saretto long side; 2303.16371 warns premiums negative for buyers | same as #1 + term structure | mostly | premium drag + two-leg friction at EOD conservative fills kills the conditional long-vol edge | very high | medium | moderate | ~10% |
| 4 | Tail-risk / trend-following standalone (long puts or long-vol overlays) | 2607.00883; trend literature | underlying closes | yes | premium drag; trend is a risk-reducer, not a return source, at this sleeve size | high | low | low | ~5% (as return strategy) |

Family 4's value survives as the **crash filter inside Family 1**. Family 1
is selected.

## 5. Selected strategy (Family 1) — exact specification

**Name (proposed):** `H3-cvrp-spy-qqq-atm5w-noStop-eod-v1`
(conditional volatility-risk-premium, ATM $5-wide put credit spread, no stop)

**Universe:** SPY and QQQ only. One open spread per underlying.

**Signal (all features lagged to day t−1; entry at day t close):**
- Underlying close series derived from cached chains via put-call parity
  (deterministic tool, unit-tested; no new data purchase).
- `RV(t−1)` = EWMA (λ=0.94, RiskMetrics) of squared daily log returns over
  trailing 21 obs, annualized.
- `IV(t−1)` = implied vol of the ~50Δ put on the nearest 30–45 DTE expiry in
  the cached t−1 chain.
- `VRP(t−1) = IV(t−1) − RV(t−1)`.
- **Entry condition A:** `VRP(t−1)` ≥ 70th percentile of trailing 252
  available VRP observations (minimum 126 required — first entries therefore
  ~mid/late 2018; Q4-2018, 2020, 2022 stress regimes all remain in-sample).
- **Entry condition B (trend/crash filter):** underlying close(t−1) > 200-day
  SMA(t−1) of parity-derived closes.
- **Entry condition C:** no open spread in that underlying; all existing
  liquidity gates pass at t close (OI ≥ 100 both legs, quoted spread ≤ 10%
  both legs).

**Structure:** sell the put with |Δ| closest to 0.50 (accept 0.40–0.60) on
the nearest expiry in 30–45 DTE; buy the put exactly $5 lower (must exist,
fail closed). Conservative credit floor $1.50 ($150/contract) — below floor,
skip.

**Exits:** close at 7 DTE (existing `A_CLOSE_AT_DTE`) or expiry-week
equivalent. **No stop-loss. No profit target.** Max loss is the width — the
defined-risk structure IS the stop. One friction round-trip per trade.

**Sizing:** 1 spread per underlying per signal. Max economic loss per trade
≈ (500 − credit) + commissions ≤ $600 cap ✓. Max concurrent risk 2 spreads ≈
$700–800 ≈ 5–6% of the $14k sleeve. No Kelly — the sample cannot estimate an
edge precisely enough to size on it (lesson from 2508.16598 applied
conservatively).

**Cost model:** unchanged, frozen: mid-or-worse fills, half-spread both legs
both ways, $0.65/contract/leg commissions, 1% adverse haircut. Softening the
fill model to rescue the strategy remains prohibited.

**Sample-size requirement:** ≥ 10 losses and ≥ 3 entry-week cohorts
(existing `MIN_LOSSES_FOR_VERDICT`), else INSUFFICIENT SAMPLE → REVISE at
the owner's door, no auto-adjustment.

## 6. H3 hypothesis draft (falsifiable, pre-registered form)

> **H3:** On SPY and QQQ, selling an ATM ($0.50Δ) $5-wide put credit spread
> at 30–45 DTE, only on days when the prior day's ATM-IV minus EWMA-realized-
> vol spread is in its top trailing tercile AND the underlying is above its
> 200-day average, held without stops to 7 DTE, has **positive expectancy per
> trade after frozen conservative costs** over in-sample 2018-01-01..2022-12-31.

- **PASS:** CI90 lower bound of expectancy/trade > 0, with ≥ 10 losses and
  ≥ 3 cohorts, AND positive point expectancy in ≥ 2 of the 3 stress windows
  (2018 / 2020 / 2022) — a PASS earns only an owner conversation about the
  OOS budget, never an automatic reveal.
- **FAIL:** CI90 upper bound < 0 → hypothesis dead; no OOS look; no width /
  delta / percentile / filter re-tuning against the result.
- **NO EDGE:** CI90 straddles 0 → dead unless the owner explicitly orders a
  (new, separately registered) revision.
- **In-sample:** 2018-01-01..2022-12-31 (entries begin when 200-SMA and
  126-obs VRP history accrue, ~2018-10). **OOS:** sealed, per existing
  policy; H3 does not touch it; budget stays 0/3.
- **No-discretion clause:** every parameter above (0.50Δ, $5 width, 30–45
  DTE, 70th percentile, 252/126 window, 200-SMA, $1.50 floor, 7-DTE exit,
  no stop, no target) is frozen at registration. Exactly ONE in-sample run.
  No sweep. Any variant — different percentile, delta, width, filter — is a
  new hypothesis and a new ledger trial. Signal features use t−1 data only.

## 7. Honest risk disclosures

1. **Family adjacency:** H3 uses the same instrument (put credit spread,
   SPY/QQQ) as H1/H2. It is licensed as NEW by the width-sweep decision doc
   ("any change to exits, stops, credit floors … is a NEW hypothesis"), and
   the claim under test is different (conditional timing + no-stop vs.
   unconditional harvest + stop). But the owner should veto if this reads as
   mutation rather than new hypothesis. The design derives from literature
   priors and friction arithmetic, **not** from scanning in-sample P&L of
   variants — yet we cannot un-know that 2018–22 contained the regimes it
   contains. Residual design-contamination risk is real and is why the OOS
   holdout stays sealed regardless.
2. **Burden of proof is quantified:** H2 (unconditional, 30Δ, $5, with stop)
   sat at −$39/trade. H3's conditioning + ATM credit + no-stop must move
   expectancy > $40/trade just to reach zero. P(pass) ≈ 25–35%, honestly.
3. **Entry clustering:** high-VRP days cluster after vol spikes; the
   week-cohort bootstrap handles dependence, but effective sample may be
   small → INSUFFICIENT SAMPLE is a live outcome.
4. **Warmup data gap:** 200-SMA / VRP percentile warmup burns ~Jan–Sep 2018.
   Alternative (buying 2017 data) is owner-gated and probably not worth it.

## 8. Recommendation

**Revise-then-register:** present this draft to the owner; if approved,
freeze the spec verbatim as H3, build the two small deterministic tools
(parity close series, VRP/SMA feature frame) with tests, register in the
ledger, and run the single in-sample test. Do not register, run, commit, or
reveal anything without explicit owner approval. Reject the VST/CEG/MSFT/AMZN
expansion. If the owner is uncomfortable with family adjacency, the fallback
is "no new hypothesis yet" — which remains a respectable outcome.

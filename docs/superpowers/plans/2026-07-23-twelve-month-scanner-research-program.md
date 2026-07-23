# Twelve-month scanner research program — audit resolution and execution design

**Date:** 2026-07-23. **Program window:** 2026-07-23 → 2027-07-23.
**Research cutoff for everything below:** chains through 2026-07-21; closes and
Treasury curve through 2026-07-22; feature store through 2026-07-20.
**Materials reviewed in full (confirmation):** the 2026-07-22 quant-methods
survey; the RQ2 briefs + registration skeleton; the external Part-I
mathematical critique and Part-II execution directives (owner-forwarded
2026-07-23); the continuation directive; repo ground truth (`config.py`,
`features.py`, `h7_signals.py`, `h7_earnings.py`, `data/rates.py`,
`ledger/experiments.jsonl` seq 17, replan spec, E1/Study-A reports,
parking lot). Contested math re-verified against primary sources by a
dedicated verification agent 2026-07-23 (worked examples executed in code;
citations labeled where live re-fetch did not complete).

**Provenance rule applied throughout:** every Part-II number (badge
thresholds, exit convention, α, backstop) is **LLM-drafted, owner-forwarded
2026-07-23**. It is recorded here as the working value and becomes frozen only
when Carsyn types it into the ledger registration. Nothing in this document
changes the frozen GREEN recipe; RQ1's input surface stays byte-identical.

---

## 1. Audit-resolution decision table

Verdicts: ACCEPT / ACCEPT-MOD (accept with modification) / REJECT / DEFER
(pending data) / REPLACE (stronger method adopted instead).

| # | Audit item | Decision | Resolution (one line each) |
|---|-----------|----------|---------------------------|
| 1 | Expected move "ignores skew; use 0.8·S·IV·√τ" | REPLACE | Quote the **actual ATM straddle mid** (model-free, chains cached — strictly better than either formula); keep `0.8·S·IV·√τ` only as fallback labeled "expected absolute move." The 0.8 is Brenner–Subrahmanyam's √(2/π)=E\|Z\| ATM factor, **not** a skew adjustment — audit's prescription upgraded, its rationale corrected. The 1-SD band `S·IV·√τ` stays as a separate labeled line (a different quantity, not a competing estimate). |
| 2 | N(−d2) "fatally biased" with r,q zeroed | ACCEPT-MOD | Real rates are now sourced (curve live, cc conversion in-repo); q lands with the dividends CSV. Correction to the audit: nothing was ever computing a wrong d2 — the loaders fail closed, the line simply couldn't ship. Rule adopted: probability lines render only with sourced r (and q for payers); no r=0 variant exists. Note: July-2026 short-end is ~3.8–4.1%, not the audit's "5% environment." |
| 3 | Touch probability "drift dominant beyond 30 DTE" | ACCEPT-MOD | Adopt the exact Reiner–Rubinstein first-passage formula with ν=r−q−σ²/2 (worked example S=100/B=90/σ=0.6/45d/r=4%: 61.7%→64.2%). But "dominant" is quantitatively wrong: the correction is +2.2 to +3.4pp across 30–180d, and flips sign near σ≈0.28. Added caveat the audit missed: EOD close-only monitoring biases realized touch DOWN vs the continuous formula (Broadie–Glasserman–Kou). |
| 4 | Taylor attribution "will fail without vanna/volga" | ACCEPT-MOD | Adopt the full 6-term expansion (Δ, ½Γ, vega, ½Volga, Vanna, Θ) — cheap and correct. But measured magnitudes: vanna ≈1% of the vega term ATM on a 1σ day (+5 vol pts), ≈3–4% even on a 3–4σ earnings gap with 20–25pt crush; ATM is where vanna is smallest (peaks in the wings). Display shows the named beginner terms + one aggregated "interaction effects" bucket — full math inside, no jargon on the card. |
| 5 | MFIV strip needs zero-bid stop + density gate | ACCEPT | Cboe rule confirmed (stop after TWO consecutive zero bids; K0 = first strike below F; F from min\|C−P\| parity pair). Add a minimum strike-count/density gate before rendering; stays parked for thin-wing names; tail-risk understatement on sparse strips is disclosed on any render. |
| 6 | OU half-life "misspecified; IV has long memory" | ACCEPT-MOD | Long memory is real (Comte–Renault 1998; ABDL 2003; rough-vol H<½). AR(1) half-life survives ONLY as an ADF-gated, ex-earnings-window, "recent-persistence descriptive summary" — never a structural or predictive parameter. Parked item's gate updated accordingly. |
| 7 | Non-overlapping outcome testing | ACCEPT | Primary inference = non-overlapping fixed-horizon entry cohorts (weekly `COHORT_GRANULARITY` unchanged); overlapping observations never counted as independent evidence. |
| 8 | Daily staggered portfolio testing | ACCEPT | Second, separate realism view: a staggered book with overlapping live positions, reported descriptively (drawdown, turnover, capacity) — never pooled into the inference view. |
| 9 | Time-block resampling | ACCEPT (already in-repo) | Politis–White stationary block bootstrap, 5000 reps, n^(1/3) blocking — the existing frozen machinery is exactly this; reused unchanged. |
| 10 | Romano–Wolf vs Holm | ACCEPT-MOD | Verified: RW controls FWER via the resampled joint distribution and dominates Holm under positive dependence; it reuses our existing block bootstrap. Registered default stays **Holm** at K≈5–8 (hand-auditable); **Romano–Wolf is pre-registered as the switch at K≳10–12** or strong dependence. Replaces the earlier White/SPA escalation (RW gives per-hypothesis decisions; SPA answers a different question). |
| 11 | Earnings event-variance estimation | ACCEPT | Workstream D: bracketing-expiry total-variance decomposition with clean-T3 diffusive estimate (primary) and ex-earnings trailing-RV fallback (labeled), bid/ask bands, refusal conditions, per-name listing-density pre-check. Full spec in the companion file. |
| 12 | Physical earnings-jump forecasting | ACCEPT | Per-name reaction history with bmo/amc session alignment (available in both earnings stores), cluster-mean removal (labeled approximation; beta-vs-QQQ upgrade now unblocked), shrinkage w=n/(n+4) toward the cluster for n<8 (k owner-ratified at registration). |
| 13 | Bid-and-ask execution | ACCEPT (already law) | Frozen fill model unchanged (adverse side + haircut + half-spread both legs, commissions both ways); D adds bid-IV/ask-IV banding so even MEASUREMENTS carry quote-width uncertainty; daily capture records full quotes. |
| 14 | EOD vs intraday entry rules | ACCEPT | Everything is EOD. Signals computed from day-t closes; label entries at day t+1 close (H6/H10 lifecycle precedent) — no same-close execution fiction, no intraday claims anywhere. |
| 15 | Trade-size and capacity | ACCEPT | 1-contract convention (H7 precedent) with each card stating WHICH cap applies ($600 defined-risk vs collateral/equity-sized for CSP/CC); OI/spread gates are the only capacity claims made. |
| 16 | Treasury par-curve conversion | ACCEPT-MOD | Materiality verdict: AUDIT-WRONG if claimed material — par-vs-zero ≈0 at ≤1yr; compounding-convention gap ≈6bp → ≈0.03pp in N(−d2); invisible at whole-percent display. Adopt correctness anyway: par yields are semiannual BEY, so r_c = 2·ln(1+y/2). Found in passing: the repo's `par_to_continuous` uses annual ln(1+y) (3.75% vs 3.78% on today's 1-2mo tenor) — a ~3–4bp nuance filed as a Workstream-H fix, not urgent. |
| 17 | Cash-hurdle rates | ACCEPT | Now computable: matched-tenor T-bill comparison on CSP cards using the sourced curve ("your collateral could earn ~$X risk-free over the same window"). |
| 18 | Declared dividends | ACCEPT-MOD | Use DECLARED amounts (issuer IR/8-K), not analyst "expected"; trailing declared run-rate labeled as estimate where a fresh declaration is pending. CSV pending the sourcing agent + **owner spot-check before the assignment flag ever renders** (wrong dividends are worse than none; the loader's fail-closed design agrees). |
| 19 | Stock-borrow effects | DEFER | No borrow feed exists and none is sanctioned. Adopted as a DATA-QUALITY check only: parity-implied forward residual (which bundles borrow+dividend error) flags names where forward math is untrustworthy; never an input. |
| 20 | Forward-price estimation | ACCEPT | F = S·e^{(r−q)τ} baseline; near-ATM put-call-parity implied forward as cross-check where both legs pass quality gates; American-style limitation disclosed (use near-ATM, shorter tenors); Workstream F. |
| 21 | PMCC return accounting | ACCEPT | Verified as the standard non-flattering convention: denominator = original committed capital (initial LEAPS debit + added cash), separate dollar P&L, chain-linked time-weighted daily returns; never re-based to current market value (which flatters losses). |
| 22 | ATM straddle labeling | ACCEPT | Straddle-quoted move labeled "straddle-implied move (expected absolute move)"; 1-SD band labeled separately; "not a forecast" stays on both. |
| 23 | Variance-premium naming | ACCEPT | Three measures, three names, never conflated: (i) **realized variance gap** (past implied minus subsequently realized, matched cycles); (ii) **forecast variance spread** (current IV² minus physical forecast); (iii) **strip-implied variance** (MFIV, gated). "VRP" alone is banned as a field name. |
| 24 | Concentration calculations | ACCEPT-MOD | ρ̄/n_eff meter stands (one-factor approximation, labeled); companion λ₁-share with Marchenko–Pastur null line; windows disclosed; correlation on log returns; beta and delta-adjusted index exposure now computable (QQQ/SPY closes cached). |
| 25 | IV percentile excluding earnings | ACCEPT | Promoted into Workstream H (measurement hygiene): `iv_percentile_ex_earnings` beside the existing field, plus the naming fix (current `iv_rank` is a percentile, not broker-style min-max — relabel display). |
| 26 | "Retail-grade proxies" framing of N3 | REJECT (framing) | The lines were always labeled descriptive, display-only, never-forecast; the substance of the fixes is accepted above, the "fatally flawed signal" framing is not — nothing was being used as a signal. |

## 2. Corrected current-state summary (2026-07-23)

- Five lanes; GREEN recipe frozen and untested; **RQ1 registered (seq 17),
  unrun, zero code** — N4 resolved to (a) (owner-forwarded), so the RQ1 runner
  brief may now be written; RQ1 computes against the pre-badge recipe.
- No badge in ranking; no new backtest has ever run under this program.
- EOD only; intraday absent; several names <2yr history; big-4 and watchlist
  alike outcome-selected (no honest historical holdout — forward evidence only).
- **Data unlocks executed this session:** `data/rates/treasury_cmt.csv` LIVE
  (10 curve days, 8 tenors 30–730d, capture-time provenance → forward-serving
  only; loader-verified: 2026-09-18 expiry ⇒ cc 3.75%); **QQQ+SPY closes and
  OHLCV cached** (2017-01-03→2026-07-22, sanctioned Yahoo path; the fetch
  self-recorded DATA_PULL_OHLCV provenance facts in `ledger/facts.log`).
  **`expected_dividends.csv` sourced and loader-verified** — all 15 names from
  SEC filings / issuer releases (zero memory fallbacks): 6 payers (MSFT $3.64,
  CEG $1.706, VST $0.916, AVGO $2.60, NVDA $1.00, ET $1.35 — ET is an MLP
  DISTRIBUTION, mechanically equivalent for ex-date option math), 9 confirmed
  non-payers at 0.0. Convention: non-payer validity runs 95d from the
  point-in-time confirmation (capture), payer validity 95d from declaration.
  **OWNER SPOT-CHECK REQUIRED before the assignment flag renders — priority
  item: NVDA raised its dividend 25× ($0.01→$0.25/qtr) on 2026-05-20.**
  Discovered in passing: **Alpha Vantage now paywalls full-history daily
  closes** (its refusal guard fired correctly) — the AV fallback in
  `data/underlying_closes.py` is effectively dead for backfills.
- Phase-1 recorders (R1–R5) remain the critical path; H1 honesty bundle pulled
  forward (owner directive) as a Codex brief; all other builds queue behind.
- **ThetaData coverage confirmed only through 2026-11-30.** The 12-month
  program's daily chain capture dies without the extension — owner decision
  needed by ~2026-10-01 (see §13).
- The 2026-07-22 top-five was a proposal; it is reassessed in §3 below.

## 3. Final top-five decisions (reassessed, three lenses)

Build order is owner-fixed where the owner has spoken: H1 now; recorders
first; badges A/B + N3 with owner-forwarded thresholds queued behind Phase 1.
The lists below are the research prioritization inside that frame.

**By expected scanner value (12-month horizon):**
1. Workstream C — matched variance analysis (the renamed, matched, three-way
   variance family; continuous-first, thresholds only after the relationship
   is measured).
2. Workstream D — earnings variance decomposition (upgrades Badge B's slope
   percentile to a proper event-variance extraction; Badge B ships as
   owner-typed and D either validates or supersedes it at the 6-month review).
3. Workstream H — mechanical controls bundle (assignment flag, cash hurdle,
   ex-earnings IV percentile, naming fixes) — now largely data-unlocked.
4. Workstream G — concentration & clustering panel (now including beta and
   delta-adjusted index exposure).
5. N3 market-implied expectations lines, corrected per §1 (straddle-quoted
   move; drifted touch; rate-gated d2).

**By immediate implementation value (buildable this week as briefs):**
1. H1 honesty bundle (Codex-ready; owner-prioritized).
2. Straddle-quoted expected-move line (pure chain read; no rates needed).
3. Concentration panel (all inputs cached, including QQQ/SPY).
4. Cash-hurdle line + N(−d2) with real rates (non-payers immediately; payers
   after the dividends CSV).
5. IV-percentile naming + ex-earnings variant.

**By value for aggressive volatility trading (the owner's stated appetite):**
1. Workstream D earnings program — August earnings season is weeks away; both
   pre-earnings long-vol (#13) and defined-risk crush (#14) cards hang off it.
2. Workstream B opportunity cards (19 setups, defined-risk only, companion
   file) — the daily "what's aggressive and honest today" surface.
3. Term-structure/calendar cards (#7/#15) + Badge B corner (owner-typed
   75/25, GATED).
4. Badge A bounce lens (owner-typed −20%/+mom/70th) with negative priors
   printed on the card.
5. Vol-of-vol + tail-shape lines as the aggression rails (when the board is
   jumpy, the cards say so).

**Best treated as risk controls only (no return claim ever):** assignment
flag; cash hurdle; liquidity refusals; rank/spread stability; forward/parity
validation; corporate-action controls; annualization labels.

**Best left parked:** OU half-life (relabeled per §1.6); MFIV (density gate);
HAR/GARCH beyond the Workstream-E comparison; PCA/MP beyond the null line;
charm line; regime-conditional thresholds; full-market TS×VRP study
(unchanged).

## 4. Parallel workstreams (separate questions, separate conclusions)

Each workstream registers separately; nothing shares a conclusion across
streams; every registered test increments the program-wide K counter (§6).

**A — Existing scanner baseline.** Two registrations. **RQ1** (seq 17,
frozen): run exactly as registered once its runner exists — Spearman ρ,
GREEN-fraction vs forward 21d realized vol and IV change, descriptive,
|ρ|≥0.30 notable. **A2 (new registration):** per-lane after-cost outcome
battery on the frozen ranking — CSP / CC / PMCC / LEAPS / tactical scored
separately, per-horizon, using the owner-forwarded exit conventions; metrics:
tercile top-vs-bottom spread (primary), middle-tercile monotonicity, win rate
by cohort date, median, worst period, drawdown, turnover, ±50% cost stress.
Views: non-overlapping cohorts (inference) + staggered book (realism). The
historical portion is Card-3-class exploratory (contamination stands); the
verdict-bearing portion is the forward window inside this program. PMCC lane
may be structurally empty (no LEAPS held) — reported as "no data," not
failure.

**B — Aggressive volatility opportunity cards.** Companion file. 19 setups,
defined-risk-only eligibility rulings, refusal-first rendering; feeds the
weekly opportunity report. Descriptive surface + per-setup registered forward
studies only where a setup graduates (its own registration, its own K).

**C — Matched variance analysis.** Three named measures (§1.23), matched by
tenor/earnings-status/delta/name/regime/data-quality. Continuous relationship
first (deciles vs subsequent short-option and long-option cost-adjusted
outcomes, crush prediction, tail losses, regime splits); NO GREEN/AMBER/RED
until the continuous study is run and read. Historical portion one-run
exploratory; forward portion accrues under RQ2-family registration.

**D — Earnings volatility.** Companion file spec. Option-implied event
variance vs physical jump estimate, T-10→T+10 windows, long-vol and short-vol
scored separately, sector/regime splits, refusal-first. First adjudicable
season: August 2026 prints (descriptive), scored across the four seasons in
window.

**E — Volatility forecasting comparison.** One registration. Models: naive
rv21 (incumbent), EWMA (λ=0.94 + fitted), GARCH(1,1), HAR-daily, IV-as-
forecast (tenor-matched), IV+RV blend, jump-robust RV variant. Horizons:
1/3/5/10/21/42/63/126 sessions — economically sensible pairs only (no GARCH at
126d; IV only at its own tenors; HAR at 5–63d). Loss: QLIKE primary, RMSE on
log-vol secondary, tail-miss rate, earnings-window slice, per-name stability.
Promotion: a complex model replaces rv21 in any DISPLAY only if it beats it
consistently across names AND the improvement survives the forward half;
promotion into cushion/grading = a separate owner amendment (frozen-recipe
rule).

**F — Distance to strike.** Standardized moneyness
`d = ln(K/F) / sqrt(total variance to expiry)` with total variance = diffusive
forecast (E's winner, until then rv21) + scheduled event variance (D);
F = S·e^{(r−q)τ} with parity cross-check; puts/calls separate; if earnings
falls inside the tenor and no acceptable event estimate exists, the value must
NOT render as an improvement (fail-closed neutral). Display column only;
banned vocabulary: "safety," "probability of profit/success."

**G — Concentration & relative value.** Board panel: ρ̄ + max pair, n_eff,
λ₁-share vs MP null, cluster concentration (3 named clusters), earnings-date
clustering, beta & delta-adjusted QQQ/SPY exposure, aggregate gamma sign,
combined max-loss bracket, worst observed 1-day AND 5-day replay. Panel stays
out of per-name ranking unless future evidence (registered) supports entry.
Dispersion research: single-stock vs index REALIZED vol now; implied-vol
dispersion blocked on index chains (owner decision).

**H — Mechanical risk controls.** No return claims required: IV-percentile
naming + ex-earnings variant; assignment warnings (OCC-grounded, post
dividends-CSV spot-check); early-exercise incentive check (extrinsic vs
declared dividend); cash hurdle; rate handling (incl. the semiannual-BEY
conversion fix); parity/forward validation flags; corporate-action controls
(splits registry, entity floors); liquidity + missing-data refusal patterns;
cost/annualization labels (H1); rank-stability and spread-stability meters.

## 5. Lane-specific outcome accounting

Exit conventions are owner-forwarded working values; each lane's labels are
frozen at its registration; a roll always closes trade 1 and opens trade 2.

- **CSP:** compare five exit arms as SEPARATE experiments (50% capture;
  21-DTE; fixed horizon; breach-defensive per the owner rule — breach → hold
  to 21 DTE then close, mechanical; assignment-accepting). Track: option P&L,
  assigned-stock result (marked separately), collateral return, cash return
  forgone (curve now live), max adverse excursion, final loss, tail-event
  loss. Note: the owner's "roll or take the loss" is mechanized as take-the-
  loss in labels; rolling is its own comparison arm.
- **CC:** short-call result, stock result, combined, combined minus
  stock-only benchmark, assignment incidence, lost-upside accounting.
- **PMCC:** long-leg and short-leg results; combined; dollar P&L; return on
  ORIGINAL committed capital (initial debit + added cash — the §1.21
  convention); chain-linked daily TWR; per-short-cycle results; assignment
  exposure. Lane may be empty until a LEAPS exists — reported honestly.
- **LEAPS:** 21/63/126-session marks vs stock and delta-adjusted stock;
  spread cost; vega contribution; earnings exposure count; drawdown.
- **Tactical calls:** 5/10/20-session marks with the six-term attribution
  (§1.4) splitting stock-price, IV, decay, cross-effects, and spread-cost
  contributions.

## 6. Statistical testing design

- **Two views everywhere:** non-overlapping fixed-horizon cohorts (weekly)
  carry inference; the staggered realistic book is descriptive.
- **Resampling:** existing stationary block bootstrap, 5000 reps, unchanged.
- **Multiple testing:** Holm at α=0.10 (owner-forwarded) as registered
  default; Romano–Wolf stepdown on the existing bootstrap pre-registered as
  the switch at K≳10–12 or measured strong dependence. K counts every
  variant tried, program-wide, recorded in each registration (ledger rule 8).
- **Adverse-count gates:** MIN_ADVERSE_BOTTOM_BUCKET = 10 (owner-forwarded)
  for ranking tests; per-lane loss floors inherit MIN_LOSSES_FOR_VERDICT
  spirit. Below the gate: INSUFFICIENT_SAMPLE, an accepted outcome.
- **Forward-window backstop:** 12 months (owner-forwarded) — adjudicate at
  the gate or the date, whichever first; no post-hoc extensions.
- **No conclusion mixing:** a finding in one workstream never promotes a
  feature in another; each promotion is its own registered decision.

## 7. Twelve-month calendar

- **Daily (rides the Phase-1 recorder infrastructure + one research-capture
  appendix):** scanner scores; selected contracts + full quotes; underlying
  closes; earnings-store state; declared dividends; Treasury curve refresh;
  corporate actions; B-card opportunities surfaced; label resolutions.
- **Weekly:** aggressive-vol opportunity report (B cards fired/refused with
  reasons); term-structure movers; largest variance gaps (C); upcoming
  earnings windows (D); vol-expansion and vol-collapse candidates;
  concentration panel deltas (G); data failures (loud).
- **Monthly:** descriptive findings; early lane results (A2 accrual);
  forecast-accuracy running table (E); realized execution-cost audit;
  strongest failures; signal stability; parking-lot moves.
- **Earnings seasons (Aug/Nov 2026, Feb/May 2027):** priced vs realized event
  moves; implied vs physical event variance; crush expected vs actual;
  long-vol and short-vol scorecards; cluster differences; model failures (D).
- **Quarterly:** RQ1 status; per-horizon results kept separate; regime
  slices; candidate-signal progress; K counter and multiple-testing impact;
  power achieved vs planned; evidence-justified changes (as NEW
  registrations, never edits).
- **Six months (2027-01-23):** interim report separating mechanical
  improvements / descriptive findings / early evidence / strong evidence /
  weak / inconclusive / stop-list. Badge B vs Workstream D adjudication
  checkpoint.
- **Twelve months (2027-07-23):** final report — features entering ranking
  (registered evidence only), display-only keepers, active controls,
  more-data items, re-parked, rejected.

## 8. Multi-horizon test matrix (Workstream E)

| Model \ Horizon (sessions) | 1 | 3 | 5 | 10 | 21 | 42 | 63 | 126 |
|---|---|---|---|---|---|---|---|---|
| Naive rv21 (incumbent) | ● | ● | ● | ● | ● | ● | ● | ● |
| EWMA (0.94, fitted) | ● | ● | ● | ● | ● | — | — | — |
| GARCH(1,1) | ● | ● | ● | ● | ● | — | — | — |
| HAR (daily components) | — | — | ● | ● | ● | ● | ● | — |
| IV as forecast (tenor-matched) | ● | — | — | — | ● | ● | ● | ● |
| IV+RV blend | — | — | ● | ● | ● | ● | ● | — |
| Jump-robust RV | — | — | ● | ● | ● | ● | — | — |

Horizon results are never pooled; per-name and pooled-cluster results reported
separately; scoring per §4.E.

## 9. Mathematical definitions (the corrected canon)

1. Expected move: primary = ATM straddle mid (label: "straddle-implied
   expected absolute move"); fallback `0.8·S·IV·√(τ/365)` (0.8 = √(2/π));
   separate line: 1-SD band `S·IV·√(τ/365)`.
2. Finish-below probability: `N(−d2)`, `d2 = [ln(S/K)+(r−q−σ²/2)τ]/(σ√τ)`,
   r continuous from the sourced curve, q from declared dividends;
   risk-neutral label permanent.
3. Touch probability: `N((ln(B/S)−ντ)/(σ√τ)) + (B/S)^{2ν/σ²}·N((ln(B/S)+ντ)/(σ√τ))`,
   `ν = r−q−σ²/2`; EOD-monitoring downward bias disclosed.
4. Attribution: `dV ≈ Δ·dS + ½Γ·dS² + 𝒱·dσ + ½·Volga·dσ² + Vanna·dS·dσ + Θ·dt`;
   `Vanna = −e^{−qτ}φ(d1)d2/σ`, `Volga = 𝒱·d1·d2/σ`.
5. Rates: par (semiannual BEY) → continuous: `r_c = 2·ln(1+y/2)`; tenor by
   interpolation on the sourced curve.
6. Event variance and physical jump: companion file §1–§2.
7. Standardized moneyness (F): `d = ln(K/F)/√(σ²_diff·τ + σ²_evt)`.
8. Concentration: `ρ̄` (mean pairwise, 63d, log returns); `n_eff = N/(1+(N−1)ρ̄)`;
   `λ₁/N` vs MP edge `(1+√(N/T))²`.
9. Bucket-spread estimand and gates: unchanged from the RQ2 skeleton
   (2026-07-22 briefs), with §6's Holm→RW schedule.

## 10. Data and execution requirements

- Chains daily (ThetaData — **extension decision required**, see §13);
  closes daily (existing pipeline; QQQ/SPY now included); Treasury curve
  daily append (capture-time provenance; ritual step to add); declared
  dividends refreshed per declaration cycle (owner-run promote after
  spot-check); earnings store per existing v3 discipline; corporate actions
  via the splits registry.
- Execution realism: frozen cost model everywhere; labels enter T+1 close;
  full quotes recorded at entry and resolution; missing EOD marks
  skip-and-log; liquidity gates at entry AND resolution.
- No index option chains, no intraday, no borrow feed: every dependent claim
  carries its stated limitation or is refused.

## 11. Earliest useful finding per study; sample limitations

| Stream | Earliest useful output | Hard limitation |
|---|---|---|
| A/RQ1 | RQ1 ρ within weeks of runner build (historical, registered) | descriptive only; big-4 contamination bounds interpretation |
| A2 | first quarterly tercile read ~Oct 2026 | 12-mo forward window likely INSUFFICIENT_SAMPLE at small effects (~52 weekly cohorts) |
| B | first weekly opportunity report within days of card build | cards are descriptive; no verdict without per-setup registration |
| C | historical continuous-relationship tables ~2–4 wks post-recorders (one-run) | matched-cycle N per name is small (≈32 max for deep names) |
| D | August-season descriptive report ~Sep 2026 | ~60 events/yr board-wide; 4 seasons in window; thin names LOW_PRECISION |
| E | first accuracy table ~1 month after build (historical fit, registered once) | daily-close RV only; no intraday HAR advantage |
| F | display column after E baseline + D event estimates exist | never a safety/PoP claim; earnings-unknown → neutral |
| G | panel live days after build (all data cached) | descriptive forever unless separately registered |
| H | controls land with briefs; assignment flag after dividends spot-check | none — controls carry no return claim |

## 12. Rejected (audit-driven additions to the standing list)

Unchanged rejections stand (survey §6). Added this session: r=0 probability
lines (never ship); un-banded event-variance point estimates (band or flag,
always); naked risk-reversals / short straddles / short strangles /
front-ratio spreads as cards (undefined risk); "probability of profit"
vocabulary anywhere; re-basing PMCC returns to market value; treating the
Part-I "5% rate environment" and "drift dominant" claims as facts (both
measured wrong); pooling horizons or workstream conclusions.

## 13. Remaining owner decisions (blocking order) and next state

1. **Part-II value ratification** (DONE 2026-07-23). The owner-typed RQ2/A2
   values are frozen in ledger sequences 18 and 19: badge thresholds 75/25
   with confirmed-earnings gating; bounce −20%/mom>0/70th; 21-DTE and 50%
   exit arms; α=0.10; adverse gate 10; and a 12-month backstop.
   **1b. Four pin-items the registrations left unfrozen — owner addendum
   required BEFORE the RQ2/A2 runners execute** (specifying them now, before
   any result exists, is clean; after results it is contamination):
   (i) the A2 "fixed-horizon" CSP arm's horizon length (a session count —
   distinct from the assignment-accepting hold-to-expiry arm);
   (ii) the bucket split for top-minus-bottom (terciles proposed);
   (iii) the Holm p-value sidedness convention (one-sided in the hypothesized
   direction, matching the CI90-lower-bound promotion rule, proposed);
   (iv) Badge B's exact "applicable event window" (proposed: a confirmed
   report date strictly inside the near leg's remaining 15–45 DTE life).
2. **ThetaData extension** — the deadline is recorded as approximately
   2026-10-01; coverage is confirmed through 2026-11-30 and renewal/extension
   remains an owner account action.
3. **Dividends CSV spot-check** (DONE 2026-07-23). NVDA was checked first;
   all six cited SEC/issuer/IR amounts match the CSV. Evidence:
   `reports/2026-07-23-dividend-payer-spot-check.md`.
4. **Index-chain top-up (SPY/QQQ)** — DECIDED NO FOR NOW. SPY/QQQ option
   chains are not funded or pulled; implied-vol dispersion remains blocked,
   while realized-vol / beta / concentration work uses existing closes.
5. **A2 / C / D / E registrations** — A2 values are frozen; C / D / E remain
   separate registrations as their briefs mature, with sequencing after
   Phase-1 recorders per the standing directive.

**Recommended next state (updated post-registration):** owner types the §13.1b
pin addendum → Codex executes the queue in
`docs/superpowers/plans/2026-07-23-codex-execution-queue.md` (H1 + recorders
first, RQ1 runner, badges, N3 lines, panel, A2 runner, Workstream D before the
August prints) → quarterly cadence per §7.

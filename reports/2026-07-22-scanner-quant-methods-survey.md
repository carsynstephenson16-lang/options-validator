# Quant-methods survey for the attractiveness scanner — ranked candidates and verdicts

**Date:** 2026-07-22. **Role:** research decision package (no code, no backtest run).
**Produced by:** Claude orchestrator session + 6 parallel research subagents (1 internal
prior-art reader, 4 method streams, 1 validation-design stream), adversarially verified.
**Governing frame:** `docs/superpowers/specs/2026-07-22-project-replan-design.md`
(owner-approved 2026-07-22): current GREEN recipe FROZEN for RQ1's sake; scanner changes
by addition only; new lenses ship as display badges under a fresh RQ2 registration
(§5 N2); market-implied probability readout is N3; RQ1 disposition is N4 (owner choice).
Nothing here runs before Phase 1 (recorders R1–R5) per "recorders first."

Claim labels follow the repo convention: Repo-verified / Test-verified /
Official-source / Inference / Assumption.

---

## 1. Current scanner and market-volatility diagnosis

**The scanner today (Repo-verified).** `options_researcher/attractiveness.py` grades
five card lanes (sell put, covered call, PMCC, LEAPS, tactical call) GREEN/AMBER/RED
against frozen H5 thresholds using: premium yield, cushion = %OTM/(rv21/√12), IV-rank
(percentile of atm_iv over trailing 252 obs), a VRP proxy (atm_iv − trailing rv21 ≥ 0),
point-in-time earnings and FOMC badges, and liquidity gates (OI ≥ 100, spread ≤ 10%).
The dashboard adds a technicals strip (SMA 20/50/200, breakout_20d, mom_1m/3m,
dist_52w_high) and Top-3 ordering by GREEN-count. The scanner explicitly disclaims
prediction; RQ1 (ledger seq 17, registered 2026-07-19, unrun) will measure whether the
GREEN-fraction ranking correlates with anything real.

**Volatility regime as of 2026-07-20 features / 2026-07-21 chains (measured this
session, Repo-verified from the feature store):**

| Measure | Value |
|---|---|
| Board median ATM IV | 0.666 (median rv21 0.546) |
| Board median IV-rank | 0.83 — AMD 1.00, SMCI 1.00, MSFT 0.99, NOW 0.98, IREN 0.94, AMZN 0.89 |
| VRP-proxy GREEN (atm_iv ≥ rv21) | 15 of 15 names |
| 3-month ATM-IV direction | up on most names (AMD 0.58→0.88, MSFT 0.36→0.46, NOW 0.68→0.74) |
| Mean pairwise 63d return correlation | 0.20 (min −0.33, max 0.82) |
| Market backdrop | VIX 15–19 per the replan note — market calm, single-name vol elevated |

**Reading (Inference):** a high, rising single-stock IV regime against a calm index —
sector-driven, not market-wide. Nearly the whole board sits at the top of its own 1-year
IV range going into the late-July/August earnings cluster, so a large share of the
apparent premium richness is scheduled-event pricing, not free carry. That is exactly
the distinction the current badges cannot draw (IV-rank and the VRP proxy are both
inflated mechanically by an approaching report), and it is why the top-ranked addition
below is the earnings-conditioned term-structure badge. Correlation is currently
moderate (0.20), but with pockets at 0.82 the "one AI factor" concern remains live and
is currently invisible on the board.

**Data ground truth for every feasibility call (measured 2026-07-22):**
EOD chains with [bid, ask, OI, iv, delta, gamma, theta, vega]; chain-day file counts:
~2,148 for MSFT/AMZN/NVDA/NOW/AMD/AVGO (2018→2026-07-21), ET 1,945, SMCI 1,885
(of which ~1,797 have a finite ATM IV), PLTR 1,453,
CEG 1,114, IREN 1,059, TEM 515, CRWV 326, USAR 323. Feature store: close, rv21,
atm_iv (15–60 DTE nearest monthly), iv_minus_rv, iv_rank, earnings_week. A second
ATM-IV tenor exists as `h7_signals.atm_iv_90d` (72–108 DTE band).
**Gaps found this session:** `data/rates/` does not exist — both `treasury_cmt.csv`
and `expected_dividends.csv` referenced by the fully-built, fail-closed loaders in
`data/rates.py` are missing; no QQQ/SPY closes exist in `.cache/underlying/` (QQQ/SPY
chain caches are legacy series ending 2026-06-30, and closes are not derivable from
chain files); no intraday data; no VIX/VIXEQ, caps, sectors, flow.

---

## 2. Ranked viable improvements

Ranking criteria: fits the replan's addition-only/display-badge frame; internal
evidence first; data availability; non-redundancy vs existing badges; honest-display
risk; plain-language value. "Test result" reflects what has actually been measured —
no new backtests were run this session (ledger discipline: nothing runs unregistered).

| # | Method | Equation (operational) | Scanner use | Evidence | Test state | Benefit | Conf. | Data | Complexity | Key risk |
|---|--------|------------------------|-------------|----------|-----------|---------|-------|------|-----------|----------|
| 1 | Earnings-conditioned term-structure corner (Badge B) | slope = atm_iv(15–45d) − atm_iv(60–120d); causal 252d percentile; corner = TS pctl ≥ [OWNER] AND VRP pctl ≤ [OWNER], shown only with the earnings tag | display badge, seller lanes | E1 study: short-tenor crush 2–4× long (internal, 2026-07-15); BS spec §6 frozen design | descriptive design frozen; predictive claim untested → RQ2 | separates event-inflated IV from carry — today's board-wide blind spot | High (descr.) | in cache | Low-Med (branch work exists) | degrades to VRP-in-disguise if the earnings conditioning is dropped |
| 2 | Bounce lens (Badge A) | armed = dist_52w_high ≤ −[OWNER]% AND mom_1m > [OWNER] AND rv21 pctl ≥ [OWNER] (blanks owner-typed) | display badge, long lanes | owner-directed (replan §5 N2); priors lean NEGATIVE: Card 3 −$85.47/trade INSUFFICIENT_SAMPLE; QM parabolic-fade REJECTED (continuation) | untested; H11 is its registered form | surfaces the owner's bounce play mechanically, with priors printed on the badge | Med | in cache | Low | reads as a buy signal unless the negative priors are printed on the card |
| 3 | Board concentration & clustering panel | ρ̄ = mean pairwise 63d corr; n_eff = N/(1+(N−1)ρ̄); earnings-cluster count within 5 sessions; Σ max-loss bracket vs $14k sleeve; worst-observed-day replay | board-level display panel | power_check.py already uses n_eff (internal); Markowitz 1952; measured today ρ̄=0.20, max 0.82 | descriptive only; no verdict claim possible or needed | answers the standing "one AI factor" concern; today invisible | High | in cache | Low | must stay descriptive — sits nearest the rejected optimizer line |
| 4 | Market-implied expectations lines (N3) | exp_move = IV·√(τ/365); P(below K) = N(−d2); P(touch) ≈ 2·N(−|ln(K/S)|/(σ√τ)) (+ drift term for precision) | card lines: short-put, ASSIGNMENT_WATCH, long lanes | textbook risk-neutral results; parked entry pre-scoped display-only; replan N3 | display-only; risk-neutral ≠ real-world — never adjudicable as forecast | plain-language "what the market prices" on every card | High (descr.) | in cache | Low | "70%" reads as a forecast; permanent risk-neutral label required |
| 5 | VRP-done-properly pair | VRP_cal = mean over past matched cycles of [IV_entry(τ) − realized vol over that cycle]; crush_med = median per-name (atm_iv[t−1]−atm_iv[t+1])/atm_iv[t−1] across past reports | card lines, seller lanes | Goyal–Saretto 2009; Bakshi–Kapadia 2003; `_vrp_seller_grade` docstring admits the tenor mismatch; E1 internal | calibration lines (backward-looking); forward signal use needs RQ2 | upgrades the scanner's core "is premium rich" question from proxy to measured history | Med-High | in cache (deep names); thin for CRWV/USAR/TEM | Med | look-ahead if cycles not strictly past; small N per name must be printed |
| 6 | Assignment-risk flag + T-bill comparison | flag: extrinsic(short call) < expected dividend before ex-date (OCC mechanics); oc = K·100·(e^{r·τ/365}−1); net = credit − oc | risk badge CC/PMCC; honesty line CSP | OCC *Characteristics and Risks* (June 2024, official); loaders built & fail-closed in data/rates.py | blocked: `data/rates/*.csv` missing | closes a real, documented mechanical blind spot; "am I beating cash?" | High once data exists | **NEEDS-DATA: 2 owner-sourced CSVs** | Low after CSVs | silently-zero dividends would be worse than no flag (loaders correctly refuse) |
| 7 | Tail-shape line ("this name jumps") | rolling 252d skew, excess kurtosis, jump_count = #{\|r\| > 3σ} | honesty line, seller lanes | standard short-vol tail literature; complements cushion (level-only) | descriptive | warns exactly where loss-gated verdicts say the information lives | Med-High | in cache | Low | noisy under ~250 obs — NaN-gate short-history names |
| 8 | Vol-of-vol (earnings-conditioned) | stdev(Δatm_iv, 21d) | instability badge, seller lanes | Goyal–Saretto 2009 (VOV construct) | descriptive | flags unstable-IV names IV-rank can't see | Med | in cache | Low | mechanically spikes near earnings — must be conditioned |
| 9 | IV-rank ex-earnings + naming fix | rank within trailing window excluding earnings_week days; label current field "percentile" | badge variant + docs | features.py:80 is a percentile despite the name (repo-verified) | descriptive | removes earnings contamination from a live threshold input | Med | in cache | Low | shrunken ex-earnings window needs the 126-obs floor |
| 10 | Cost/annualization honesty bundle | "(simple, not compounded)" on yield lines; disclose 252-vs-365 day-count split; round-trip cost % if closed early | label fixes + one line | repo-verified line numbers; vocabulary discipline | trivial; no claim | every income card stops overstating | High | none needed | Trivial | none — wording only |
| 11 | Rank-stability meter | leader_changed = candidate_id_t ≠ candidate_id_{t−1} within expiry bucket | operator churn guard | reuses top3_snapshot.candidate_id (internal) | needs new append-only history log | stops chasing quote-noise reranks | Med | needs new persistence | Med | false flips on normal expiry rollover unless bucket-scoped |
| 12 | Spread-stability liquidity refinement | rel_spread_t / median_20d(rel_spread) per contract | liquidity badge annotation | George–Longstaff 1993 | descriptive | "wide today" vs "always wide" | Med | in cache (20-file join) | Med | earnings-week blowouts inflate the "usual" |
| 13 | Taylor 1-day attribution | dV ≈ Δ·dS + ½Γ·dS² + vega·dσ + θ·dt at dS = S·σ_daily | educational line, long lanes | textbook; dashboard's intrinsic-only ladder must stay separate | descriptive | explains why a card moved | Med | in cache | Low | model output on a deliberately model-free surface — keep visually separate |
| 14 | OU half-life of IV | Δx_t = α + λx_{t−1}: HL = ln2/(−λ), x = log(atm_iv), ADF-gated | context line | standard; econometric caveats (first-hitting-time critique) | descriptive | "how long might elevated IV persist" — new duration axis | Low-Med | in cache | Low | spurious on trending series; never run on price |
| 15 | Beta-to-QQQ exposure line | β = Cov(r_i, r_QQQ)/Var(r_QQQ); QQQ-equiv $ = notional·β | translation line | Sharpe 1964 | blocked | "$16k promise ≈ $9.5k of QQQ" | Med | **NEEDS-DATA: QQQ closes fetch** | Low after fetch | β→1 in crashes; calm-period reading understates |
| 16 | CVaR of the CSP lane | CVaR_5% = E[PnL \| PnL ≤ 5% quantile] over historical τ-day returns | tail-depth badge, deep-history names only | Rockafellar–Uryasev 2000; BCBS FRTB rationale | descriptive, per-name gated | depth-of-bad vs cushion's one-sigma | Med | deep names only | Med | overlapping windows overstate effective N; refuse on thin names |
| 17 | Model-free implied variance (strip integral) | σ²(τ) = (2/τ)Σ ΔK/K²·e^{rτ}Q(K) − (1/τ)(F/K₀−1)² | infrastructure under existing badges | Britten-Jones–Neuberger 2000 | design-only until rates CSV + strike-inclusion rule | robustifies atm_iv point estimate | Low-Med | dense names; needs r | Med | thin wings poison the integral; CBOE zero-bid stop rule required |
| 18 | HAR-RV / EWMA / GARCH forecast comparison | HAR: RV_{t+1} = β₀+β_d RV_t+β_w RV_t^{(5)}+β_m RV_t^{(22)} | possible future rv21 replacement | Corsi 2009 (caveat: daily-only components lose the intraday advantage) | design-only: needs its own registered forecast-error study before any card change | only if it measurably beats rv21 | Low-Med | in cache | Med | replacing rv21 changes cushion/VRP inputs = re-registration territory |
| 19 | 25Δ risk-reversal skew line | RR = IV(25Δ call) − IV(25Δ put) at matched expiry | descriptive line, short-put lane | Xing–Zhang–Zhao 2010 (evidence B−/crowding D per internal survey) | descriptive only; IV-direction written test still unrun | "which side of risk is priced richer" | Med | wings thin on ~7 names | Low | liquidity gates must run on both wing quotes |
| 20 | PCA first-eigenvalue share (+MP null) | λ₁/15 vs MP edge λ₊=(1+√q)² as null line | board panel companion to #3 | Laloux 1999; Bun–Bouchaud–Potters 2017 | descriptive | second factor visibility | Low-Med | in cache | Low-Med | bare eigenvalue share overstates without the null |

---

## 3. Top-five selection and integration design

Selection logic: #1–#5 are the highest evidence-to-cost additions that fit the
replan's frame exactly (two are its named badges; one is its named N3 item), plus the
two genuinely new families this survey adds (concentration panel, VRP-done-properly).
#6 (assignment/T-bill) would be top-five on value but is data-blocked — it becomes
top of the unlock queue. Full integration specs and Codex briefs:
`docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`.

1. **Badge B — earnings-conditioned term-structure corner.** Finish/merge the
   BS-spec-§6 column (branch `feature/bs-attractiveness-descriptive` holds partial
   work), add the corner definition with owner-typed thresholds, render
   contango/backwardation + percentile with the earnings tag. Two owner picks: the
   long band (§6's [60,120] vs `atm_iv_90d`'s (72,108) — one function, one band) and
   whether the corner flag is earnings-GATED or only earnings-TAGGED (briefs, B1).
2. **Badge A — bounce lens.** Mechanical arm from existing `dist_52w_high`, `mom_1m`,
   `rv21` percentile; blanks owner-typed; the badge itself must print its declared
   negative priors (Card 3, QM continuation) per replan §2.2 honesty.
3. **Concentration & clustering panel.** ρ̄/n_eff meter + earnings-cluster count +
   combined-max-loss bracket vs sleeve + worst-observed-day replay. Board header,
   display-only, never ranks, never advises.
4. **Market-implied expectations lines (N3).** Expected move, N(−d2) assignment
   probability, touch probability; permanent "market-priced, not a forecast" label;
   one-page spec then build, per replan N3.
5. **VRP-done-properly calibration pair.** Tenor-matched realized-vs-implied history
   and per-name earnings-crush median, strictly causal, N printed on every render.

**How they get tested (the harness, not a promise):** all five ship as display-only
badges. Any entry into *ranking* goes through the RQ2 registration using the
validation protocol in the briefs doc: primary metric = top-minus-bottom bucket
forward cost-adjusted return spread; adverse-count gate
(MIN_ADVERSE_BOTTOM_BUCKET ≥ [OWNER, proposed 10]); Holm step-down at α=[OWNER,
proposed 0.10] across ALL candidates in one registered run; historical panel is
Card-3-class exploratory only; the verdict path is a pre-registered forward window
with a 12+ month calendar backstop. Power arithmetic (Assumption-labeled σ≈0.35):
at a 5-point spread effect, ~2.6 years to adjudicate — INSUFFICIENT_SAMPLE is an
accepted outcome, as with H9/H10b.

## 4. Implementation and test state (honest)

No code was written and no backtest was run this session. That is by design, not
omission: ledger discipline forbids unregistered evaluation runs; the replan forbids
RQ1 code before the N4 choice and puts recorders (R1–R5) ahead of all new plays; the
division of labor gives implementation to Codex from briefs. What exists as of this
report: the ranked survey (this file), five Codex-ready briefs + the RQ2 registration
skeleton with every owner-typed blank marked, the owner-decision list (below), and
parking-lot updates. The suite was not touched; no tracked file other than this
report, the briefs file, and `ideas-parking-lot.md` changed.

**Owner decisions required before any of this runs:**
1. N4 first: RQ1 disposition (recommendation (a), compute against the frozen
   pre-badge GREEN-fraction).
2. RQ2 blanks: corner thresholds, bounce-lens thresholds, bucket split, adverse
   count, α, forward-window backstop date, and the income-card exit convention
   (no frozen exit exists today for put/CC/PMCC labels — must be typed before any
   label is computed).
3. Data unlocks: source `data/rates/treasury_cmt.csv` (treasury.gov URL already in
   config) and `data/rates/expected_dividends.csv` (issuer IR); approve a QQQ (and
   SPY) daily-closes fetch through the existing sanctioned pipeline.
4. Priority call: these briefs queue behind Phase 1 recorders unless explicitly
   reprioritized.

## 5. Ideas parking lot (this survey's additions)

Recorded in `ideas-parking-lot.md` under "2026-07-22 — Quant-methods survey":
ranks 7–20 above (each with its gate), plus the design-only items: charm line for the
14-DTE bucket; regime-conditional grading thresholds (needs a validated regime read
plus pre-typed per-regime numbers, else pure curve-fitting); put-call-parity/box
implied-financing checks (folds into the BS §5 detector, blocked on synchronized
cache fields); American-premium one-time feasibility scan; SABR out-of-scope note.

## 6. Rejected methods and reasons

- **HMM regime detection** — redundant with `rv_percentile` + SMA posture; unstable
  on 6 short-history names; label-switching across refits.
- **12-1 momentum overlay** — redundant with mom_1m/3m/ma_posture; the academic
  cross-section result does not transfer to a momentum-preselected 15-name list.
- **EVT/Hill tail estimation** — needs ~10k+ obs; longest series ~2.1k. Structural.
- **IV-surface PCA (level/slope/curvature)** — index-literature substrate absent;
  would fuse interpretable badges into an opaque score (rejected-composite family).
- **SABR/stochastic-vol calibration** — the cards need a few observed deltas, not a
  smile model; ill-conditioned on thin single-name chains; violates "no custom
  quant infrastructure."
- **Monte Carlo scenario fans** — contradicts the dashboard's deliberate
  no-model design (docstring, attractiveness_dashboard.py); adds opacity, not information.
- **Cholesky joint simulation / point-estimate portfolio VaR** — misleading precision
  at N=15 with no IV-shock model; replaced by the worst-observed-day replay.
- **Avellaneda–Stoikov** — dealer quote-placement control; this platform never quotes.
- **Gamma/theta breakeven (m\*) as a card line** — category error: it is a
  delta-hedged scalping breakeven applied to unhedged buy-and-hold lanes; only the
  implied-daily-move half survives (inside top-5 item 4).
- **American-exercise binomial as a standing feature** — magnitude sits inside spread
  + existing no-arb tolerance for these lanes; one-time feasibility scan only.
- **Vanna/volga card fields** — no decision they change on a single-leg beginner card.
- **Fresh conditional-expected-return studies (post-drawdown/post-breakout)** —
  already spent (H9), live (H10a/b), or sealed-exploratory (Card 3); a rerun is the
  p-hacking pattern ledger discipline exists to block.
- **Full-market TS×VRP interaction study (Models 1–3, Holm) as drafted** — needs a
  cross-section (hundreds of names, OptionMetrics-class data, cap/sector controls)
  this repo does not have; stays parked per replan §7 pending owner strengthening.
  Its repo-scale corner survives as Badge B.
- **BS fair-value-vs-market ranking** — reconfirmed park-leaning-REJECT (short vol
  restated); nothing in this survey changes that.
- **Sector/market-cap diversification score** — no caps/sectors data; no payoff over
  the correlation meter.

## 7. Recommended scanner architecture and scoring flow

Three layers, strictly separated:

1. **Frozen core (untouched):** the current GREEN recipe and every H5 threshold —
   RQ1's measurement subject. No new feature may alter a grade, a gate, or the
   Top-3 ordering.
2. **Display-badge layer (this survey's output):** new columns in
   `features.py`-adjacent builders + dashboard panels; every column fail-closed
   (NaN → honest gap, never a fabricated GREEN), provenance-labeled, each with its
   own config constants (owner-typed where verdict-adjacent). Board-level panels
   (concentration, clustering) live beside, not inside, per-card grades.
3. **Evaluation layer (RQ2):** one registered run, bucket-spread primary,
   adverse-count gate, Holm across all K candidates (K counts every version tried,
   per ledger discipline rule 8), forward window as the verdict path. Promotion of
   any badge into ranking = the RQ2 result plus an owner amendment, never a quiet
   reorder. RQ1 runs (disposition (a)) against the pre-badge recipe so the baseline
   stays clean.

Daily flow is unchanged: ritual → feature build → board render. New badges compute
in the feature build; no new network, no new dependencies without sign-off, unittest
offline coverage per brief.

## 8. Sources, assumptions, limitations, unresolved questions

**Primary sources (access-dated 2026-07-22 by the research agents):** Goyal &
Saretto 2009 (JFE 94:310–326); Bakshi & Kapadia 2003 (RFS 16:527–566); Corsi 2009
(J. Fin. Econometrics 7:174–196); Xing, Zhang & Zhao 2010 (JFQA 45:641–662);
Cont & da Fonseca 2002 (Quant. Finance 2:45–60); Hagan et al. 2002 (Wilmott);
Britten-Jones & Neuberger 2000 (JF 55:839–866, flagged Inference pending direct
check); Jegadeesh & Titman 1993 (JF 48); Hamilton 1989 (Econometrica 57);
Rockafellar & Uryasev 2000 (J. Risk 2:21–41); Laloux et al. 1999 (PRL 83:1467);
Bun, Bouchaud & Potters 2017 (Phys. Reports 666); Marchenko & Pastur 1967;
George & Longstaff 1993 (JFQA 28); Sharpe 1964 (JF 19); Markowitz 1952 (JF 7);
White 2000 (Econometrica 68); Hansen 2005 (JBES 23); Politis & White 2004
(Econ. Reviews 23, corr. 2009); Benjamini & Hochberg 1995 (JRSS-B 57); López de
Prado 2018 (Wiley). **Official-source:** OCC, *Characteristics and Risks of
Standardized Options* (June 2024 ed.) for early-assignment mechanics; Cboe box-spread
explainer. **Internal:** E1 (2026-07-15), Studies A–E (2026-07-04), QM study
(spent), H9 (spent, INSUFFICIENT_SAMPLE), Card 3 (sealed exploratory),
pre-earnings-signal survey (2026-07-16), BS design spec §5/§6, H10/RQ1 proposals
spec, replan spec (2026-07-22).

**Assumptions (labeled):** σ≈0.35 per-trade return-on-risk SD in the power math
(replace with the exploratory pass's measured value); 3-cluster effective breadth
(Inference from the concentration thesis, not yet measured formally); "VIX 15–19"
is quoted from the replan spec, not measured here (no index feed).

**Limitations:** everything predictive here is *design*, not result — this session
produced zero new empirical verdicts, deliberately. EOD-only. The big-4 and the
watchlist alike are outcome-selected; no historical split of cached data can ever be
a verdict (Card-3-class at best). ThetaData coverage is confirmed only through
2026-11-30.

**Unresolved questions:** N4 choice; RQ2 blanks; the two rates/dividend CSVs; QQQ/SPY
closes fetch approval; whether Badge B's long-tenor band follows BS §6 [60,120] or
H7's (72,108); the income-card exit convention for any future label construction;
whether the IV-direction and TSMC written tests (both still unrun) land before or
after RQ2 registration — their results bear directly on the skew line (rank 19).

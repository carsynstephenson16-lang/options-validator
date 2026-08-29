# Options-Validator Research Integration Plan — 2026-08-24

**Status:** refreshed high-level plan; review-only; no implementation authority.
This update reconciles the original plan with work already completed on `main`.
It changes no production behavior and consumes no OOS look. This version
supersedes the 2026-08-24 original first committed in `3f5dccf` (whose §12
decisions and §2 wording are corrected below and in the addendum).

> **Verification addendum (read with this plan):**
> `docs/plans/2026-08-25-research-integration-plan-verification-addendum.md` —
> a four-auditor verification pass (2026-08-25) confirmed this plan's evidence
> and data inventory, found reasoning defects, and carries the **owner-ratified
> corrected final decision table** (notably: A split with calibration BLOCKED BY
> DATA; B → BLOCKED BY DATA; G → PARK with reopen trigger; F's acceptance
> criterion made falsifiable). Where §4/§12 below disagree with the addendum,
> the addendum governs.

## Audit identity and evidence rules

- **Active checkout (Verified):** branch
  `claude/codex-handoff-plan-2026-08-22`, HEAD
  `77af463cf93b958c61f8044621e16f974c913c42`, clean before this document edit.
- **Canonical `main` (Verified after fetch):**
  `a3114738beae6a3c73ce793163dd9f66f84a71b0`. The active branch and `main`
  diverge at `24368f675f0e70a0c58c39fedb16d0e20a2a6f83`; this planning task does not
  merge or reconcile their unrelated changes.
- **Last five active-branch commits (Verified):** `77af463` (close-quality
  boundaries), `1476a6f` (refresh fill-adversity artifacts), `615b958`
  (format fill-adversity tests), `a9241d8` (brief-24 reconciliation), and
  `489c4ba` (missing-close receipt exclusion).
- **Prior handling (Verified):** this plan was first committed in `3f5dccf`.
  Its chain-consistency workstream was implemented in `b293712`, hardened in
  `6ee1456` and `7a97e82`, merged by `aed7af0`, and disposition-adjusted by
  `107c7b9`. Its fill-adversity study was implemented in `c5db8aa`, corrected
  in `a53c5f9`, refreshed/hardened through `e4cdcf7`, and merged into `main`
  by `a311473`.
- **Worktrees (Verified):** all ordinary worktrees have no tracked or
  untracked dirt; `git worktree prune --dry-run` reports nothing prunable.
  The sanctioned `options-validator-ops` worktree contains current append-only
  facts, receipts, and market-data captures. Those are operational evidence,
  not disposable dirt, and were preserved. Ignored caches were also preserved.
- **Policy documents reviewed (Verified):** `AGENTS.md`, `CLAUDE.md`,
  `.cursorrules`, `.claude/rules/data-and-providers.md`, `PROJECT_STATE.md`,
  README “Scope status,” `reports/2026-08-08-architecture-review-decision.md`,
  `docs/provider-transition.md`, experiment policies/specifications, and the
  current implementation receipts. `PROJECT_CONTROL.md` does not exist;
  `PROJECT_STATE.md` is the canonical roadmap.

Labels used below: **Verified** means inspected code, tests, cached bytes,
receipts, or Git objects; **Inferred** means a conclusion from verified facts;
**Unknown** means the repository does not answer it; **Blocked by missing
data** means the required observations are absent and cannot safely be
invented.

## 1. Executive Verdict

1. **Move forward:** Candidate F only as an **observation and retention
   review** of the already-built, research-only chain-consistency audit. Run
   its immutable receipts over the accumulating Schwab captures, then decide
   after approximately 30 captured sessions whether its flags are actionable,
   should remain manual, or should be removed. Do not wire it into rankings,
   capture refusal, dashboards, or schedulers during this phase.
2. **Remain research-only:** Candidate A's completed fill-adversity context
   study and Candidate D's already-existing simple surface context/QA. A is
   informative about quoted spreads and D-to-D+1 quote movement, but it cannot
   calibrate realized fills without execution records. D already covers most
   proposed simple features and has no authority as a signal.
3. **Remain parked:** Candidates B, E, and H. Assignment has no meaningful
   present exposure and lacks ex-dividend observations; era/regime slicing
   lacks completed-trade sample power; broader deterministic position stress
   tests are sensible only after a supported short or multi-leg lane has real
   exposure or a specific unanswered risk question.
4. **Reject:** Candidates C, G, and I as new systems. C duplicates the current
   experiment specification and ledger; G has no predictive model to ablate;
   framework migration/runtime dependencies add maintenance without answering
   a repo problem. Static QuantLib reference fixtures already exist.
5. **No new implementation is recommended now.** The highest-value next step
   is evidence accumulation and a removal-or-retention decision for F. The
   largest blocker is the absence of broker execution records, continuous
   intraday/package quotes, and package fill states; no model should disguise
   that absence.

## 2. Repo-Verified Current State

| Capability | Current implementation | Exact evidence | Quality level | Remaining gap | Duplication risk |
|---|---|---|---|---|---|
| Conservative bid/ask fills | Per-leg adverse buy at ask and sell at bid, plus 1% adverse haircut | `strategies/base.py` (`adverse_buy`, `adverse_sell`, `entry_credit_conservative`); `config.py` (`SLIPPAGE_HAIRCUT`, `FILL_MODEL_ID`); `tests/test_h7_fill_model.py` | **Verified — strong convention** | Haircut is not calibrated to realized executions | High |
| Commissions | $0.65 per contract through both engine and reconstruction paths | `config.py` (`COMMISSION_PER_CONTRACT`); `harness/run_backtest.py`; `options_researcher/h7_forward_scoring.py` | **Verified — strong** | Other small regulatory/exchange fees are not itemized | High |
| Liquidity gates | OI and spread gates, with stricter H7 admission rules | `data/chain_policy.py` (`passes_liquidity`); `strategies/put_credit_spread.py`; `config.py` | **Verified — strong** | No empirical package-fill capacity or participation calibration | High |
| Multi-leg execution | Conservative leg-by-leg reconstruction; no package-quote model | `strategies/base.py`; `options_researcher/h7_forward_scoring.py`; fill report below | **Verified — conservative but incomplete** | No combo quotes, partial package fills, or broker order-state observations | Medium |
| Fill-adversity study | Read-only two-tier quote-context report with immutable receipt; no config change | `tools/fill_haircut_calibration.py`; `tests/test_fill_haircut_calibration.py`; `reports/fill_calibration/2026-08-24-fill-adversity-context.md`; receipt `2026-08-24-fill-adversity-context-b6191b02abee.json`; commits `c5db8aa`–`e4cdcf7` | **Verified — completed research context** | Explicitly cannot calibrate the 1% haircut against realized fills | High |
| DSR / PSR | Tested Bailey/López de Prado diagnostics with provenance checks | `metrics.py` (`probabilistic_sharpe_ratio`, `deflated_sharpe_ratio`); `tools/score_backtest.py`; `tests/test_deflated_sharpe.py` | **Verified — strong** | None material for present scope | High |
| CSCV / PBO | PBO is schema-enforced null; only minimum M/S feasibility constants exist | `research/ledger.py`; `config.py` (`CSCV_MIN_VARIANTS_M`, `CSCV_MIN_SPLITS_S`) | **Verified absent — deliberate** | No registered experiment grid has sufficient variants | Low |
| OOS control | Charge-on-touch, write-once reveal and look budget | `research/experiments.py`; `data/thetadata_adapter.py` (`OOSDataTouchError`); `ledger/experiments.jsonl` | **Verified — strong** | None; this plan must not consume a look | High |
| Block sensitivity / walk-forward | Stationary and circular block bootstrap; expanding/rolling walk-forward with purge/embargo | `metrics.py` (`_block_lengths` and bootstrap helpers); `options_researcher/robustness/walk_forward.py`; related tests | **Verified — strong** | Not every lane has enough outcomes to use it meaningfully | High |
| Multiple testing | Holm is required by the robustness `ExperimentSpec` | `options_researcher/robustness/models.py`; `options_researcher/robustness/statistics.py` | **Verified — strong in harness** | No justified CSCV input yet | High |
| Experiment isolation / baseline invariance | Separate experiment dashboard; AST/subprocess tests prevent production imports and prove baseline bytes invariant | `tests/test_experiments_baseline.py`; `tests/test_attractiveness_dashboard.py`; experiment specs and receipts | **Verified — strong** | Human cost/maintenance fields are not uniformly summarized in one view | High |
| Point-in-time / provenance | Causal timing, max-as-of stamps, staleness gates, hashes, immutable receipts and manifest verification | `options_researcher/regime.py`; `research/hashing.py`; `research/receipts.py`; `tools/cache_manifest.py`; causal-timing tests | **Verified — strong** | Some thresholds remain explicitly LLM-proposed | High |
| Within-session quote QA | Crossed/negative quotes, no-arb bounds, Greek/IV plausibility, duplicates and coverage checks | `options_researcher/quote_integrity.py`; `data/recent_topup.py`; `tools/h7_data_audit.py` | **Verified — strong** | Does not compare consecutive captures | Medium |
| Cross-session quote QA | Pure audit + CLI for gaps, vanished expiries/strikes, delta jumps and spread blowouts; isolated receipt output | `data/chain_consistency.py`; `tools/chain_consistency_audit.py`; `tests/test_chain_consistency.py`; commits `b293712`, `6ee1456`, `7a97e82`, `107c7b9` on `main` | **Verified on `main` — implemented, manual research tool** | No production caller; utility/actionability is not yet established | High |
| Surface context | ATM IV, realized IV, IV–RV gap, term slope and skew; quote-integrity QA | `options_researcher/features.py`; `options_researcher/composite_signals.py`; `options_researcher/quote_integrity.py`; `config.py` | **Verified — already present/display-only** | Wing curvature and full static-arbitrage surface coverage are not comprehensive | High |
| Assignment / expiration | Deterministic expiration settlement and disclosure; no early-assignment simulation | `options_researcher/h7_paper_lifecycle.py`; H7 real-exit spec; README “Known limitations” | **Verified — expiration only** | No early assignment, broken-spread buying-power simulation, or empirical assignment data | Medium |
| Dividends / corporate actions | Annual expected-dividend snapshot and small manual split registry | `data/rates/expected_dividends.csv`; `data/underlying_closes.py` (`SPLITS`) | **Verified — limited** | No point-in-time ex-dividend calendar or dividend-event history | Low |
| Deterministic stress / stability | Cost and bid/ask stress plus regime/ticker/window concentration in robustness harness | `options_researcher/robustness/runner.py`; `options_researcher/robustness/stability.py` | **Verified — partial** | No unified position scenario library for gaps, IV/skew, assignment and exit failure | Medium |
| Pricing reference fixtures | Isolated QuantLib 1.43 validation for American options and discrete dividends | `tools/quantlib_validation/`; associated tests and lock | **Verified — already implemented/test-only** | No repo defect currently justifies expanding it | High |
| Authority / network boundary | No live orders; cached-data research; display-only experiments; read-only equity bridge | README “Scope status”; `data/ritual_authority.py`; `options_researcher/market_context.py`; offline-readiness tests | **Verified — binding** | Bridge has no consumer, by owner decision | High |

The prior “EOD-only” claim needs nuance: verdict-bearing historical paths use
daily/EOD data, while `.cache/intraday/` contains sparse scheduled snapshots.
Those snapshots do not provide continuous quote aging, package states, or fill
paths. **Verified conclusion:** intraday execution resolution is still
unavailable for the candidate-A questions that require it.

## 3. Audit of the Prior Recommendation

### Recommendations that remain valid

- Fail-closed provenance, baseline invariance, OOS boundaries, conservative
  cost modeling, and research/production isolation remain the correct design.
- Candidate A should stay descriptive unless actual executions become
  available. Its study correctly refused to turn quote movement into a fill
  calibration.
- Candidate F is correctly limited to data-quality flags, never a directional
  signal. Its isolation and deterministic receipts are appropriate.

### Recommendations that are now stale, duplicated, or unsupported

1. **A and F no longer need implementation briefs.** Both narrow workstreams
   were implemented and merged to `main`; recommending them again would
   duplicate completed work.
2. **F is not an automatic capture safeguard.** There is no non-test caller
   outside its CLI/module. The approved implementation deliberately excluded
   scheduler, digest, dashboard, capture-gate, and ranking integration.
3. **A did not calibrate fills.** Its evidence is quoted-spread and overnight
   midpoint context. The report explicitly states that comparison with the
   same quoted spread charged by the model is circular and that observed fills
   are absent.
4. **“CSCV safeguards” was overstated.** The repo has feasibility floors and a
   hard-null PBO field, not a CSCV implementation.
5. **Candidate C was over-prioritized.** `ExperimentSpec`, append-only records,
   feasibility/OOS gates, hashes, metrics, and rollback/removal requirements
   already cover nearly all requested fields. The few human-cost fields belong
   in the next experiment's review template, not a new gate or service.
6. **Candidate D largely duplicates current work.** ATM IV, IV–RV, term slope,
   skew and coverage/integrity checks already exist. Rough-Heston or neural
   modeling has neither a validated consumer nor supporting data need.
7. **Candidate I's static-fixture lesson is already handled.** The isolated
   QuantLib validation lane supplies American/dividend reference fixtures.
8. **Candidate B's theoretical importance was not matched to present
   exposure.** Current paper artifacts show one long-call position and no
   active short/multi-leg book; the necessary ex-dividend event history is
   absent. Exposure must be remeasured before design.
9. **The n8n boundary is stale for this repo.** The 2026-08-22 lean-ops decision
   retained launchd/receipt-reading operations and rejected n8n. Nothing here
   proposes an orchestration change.

## 4. Candidate Scorecard

Every axis is 1–5 with **5 favorable**. For overlap, 5 means high incremental
novelty/low duplication; for complexity, maintenance, and false-confidence
risk, 5 means low burden/risk. Weights: validation benefit 2.0; evidence 1.0;
novelty 1.0; data availability 1.5; simplicity 1.0; low maintenance 1.0;
false-confidence safety 1.5; reversibility 0.5; retail relevance 0.5;
architecture fit 0.5. Maximum is 52.5. Benefit, available evidence, and
false-confidence safety dominate; the score informs but does not automatically
authorize work.

| Candidate | Benefit | Evidence | Novelty | Data | Simple | Low maint. | FC-safe | Reversible | Retail | Fit | Weighted total | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A — execution realism | 4 | 5 | 3 | 2 | 3 | 4 | 3 | 5 | 4 | 5 | **37.5** | RESEARCH ONLY |
| B — early assignment | 2 | 5 | 3 | 1 | 2 | 3 | 3 | 4 | 3 | 4 | **28.5** | PARK |
| C — marginal-value gate | 1 | 5 | 1 | 5 | 3 | 2 | 4 | 4 | 2 | 3 | **31.0** | REJECT |
| D — simple surface features | 2 | 5 | 1 | 4 | 3 | 3 | 3 | 4 | 2 | 4 | **31.5** | RESEARCH ONLY |
| E — era/regime stability | 2 | 4 | 2 | 4 | 3 | 3 | 1 | 5 | 2 | 4 | **29.0** | PARK |
| F — quote/velocity anomalies | 4 | 5 | 3 | 4 | 4 | 4 | 4 | 5 | 4 | 5 | **43.0** | RESEARCH ONLY |
| G — grouping/ablation | 1 | 3 | 4 | 3 | 2 | 2 | 2 | 4 | 1 | 2 | **24.0** | REJECT |
| H — deterministic stress | 3 | 4 | 3 | 5 | 3 | 3 | 4 | 5 | 4 | 4 | **39.0** | PARK |
| I — framework lessons | 1 | 5 | 1 | 5 | 4 | 3 | 4 | 5 | 1 | 2 | **32.5** | REJECT |

Score explanations, including every axis:

- **A:** benefit 4 because cost realism is decision-critical; evidence 5 from
  code/tests/report; novelty 3 because the narrow study already exists; data 2
  because quotes exist but fills/package paths do not; simplicity 3 and
  maintenance 4 for the existing offline CLI; FC-safety 3 because quote
  movement is easy to mislabel as fill evidence; reversibility 5; retail 4;
  fit 5 for cached, receipt-bound research.
- **B:** benefit 2 at current exposure; evidence 5 for the verified absence and
  disclosed limitation; novelty 3; data 1 without ex-div/assignment events;
  simplicity 2; maintenance 3; FC-safety 3 because invented probabilities are
  dangerous; reversibility 4; retail 3; fit 4 if eventually deterministic and
  display-only.
- **C:** benefit 1 because it adds little control; evidence 5; novelty 1 due to
  extensive overlap; data 5 because it is metadata; simplicity 3;
  maintenance 2 for a second governance path; FC-safety 4; reversibility 4;
  retail 2; fit 3. A docs-template field is not a new system.
- **D:** benefit 2; evidence 5 that most features exist; novelty 1; data 4 for
  cached EOD surfaces; simplicity 3; maintenance 3; FC-safety 3 because sparse
  surfaces can look model-ready; reversibility 4; retail 2; fit 4 only as
  display-only QA.
- **E:** benefit 2 until sample sizes grow; evidence 4; novelty 2 because
  regime/stability views already exist; data 4 for market states but not
  outcomes; simplicity 3; maintenance 3; FC-safety 1 due to seven-way slicing
  of starved samples; reversibility 5; retail 2; fit 4 as descriptive output.
- **F:** benefit 4 for irreplaceable-cache QA; evidence 5 from implementation
  and 35 tests; novelty 3 because within-session QA overlaps; data 4 because
  snapshots exist but cadence is sparse; simplicity 4; maintenance 4;
  FC-safety 4 when flags stay non-directional; reversibility 5; retail 4; fit 5.
- **G:** benefit 1 without a predictive consumer; evidence 3 for feature-group
  concepts but not repo efficacy; novelty 4; data 3; simplicity 2;
  maintenance 2; FC-safety 2 due to selection degrees of freedom;
  reversibility 4; retail 1; fit 2.
- **H:** benefit 3; evidence 4 from existing stress arms; novelty 3; data 5 for
  deterministic inputs; simplicity 3; maintenance 3; FC-safety 4 when outputs
  remain hypothetical; reversibility 5; retail 4; fit 4. Its high score does
  not overcome the absence of present short/multi-leg exposure or a concrete
  unanswered scenario.
- **I:** benefit 1 because no migration problem is established; evidence 5
  from repo and official sources; novelty 1 because patterns/fixtures already
  exist; data 5; simplicity 4 for static review but maintenance 3 if retained;
  FC-safety 4; reversibility 5; retail 1; fit 2 for runtime adoption.

## 5. Recommended Scope

The smallest valuable scope contains **no new code** and two independent
research decisions:

1. **WS-F — Chain-consistency observation/retention review.** Accumulate and
   review existing `chain_consistency_audit.py` receipts until roughly 30
   captured sessions are available. Record which flags caused a human action,
   which were expected gaps/noise, and whether the tool should remain manual,
   be removed, or receive a separate integration design. Threshold tuning to
   make history look clean is excluded.
2. **WS-A — Fill-context disposition.** Preserve the completed report as
   context and make no haircut/config change. Reopen design only if actual
   broker executions or equivalent auditable fill observations become
   available. More quoted-spread analysis alone does not clear the blocker.

Candidate D remains an existing research display/QA capability, not a new
workstream. Candidate H gets a separate future brief only after exposure and a
specific risk question are established. Execution, assignment, surfaces,
anomalies, and stress tests must never be combined into one implementation
brief.

## 6. Phased Plan

### Phase 1 — Reconciliation and freeze (complete in this planning pass)

1. **Goal:** prevent duplicate implementation.
2. **Repo areas:** Git/worktrees, this plan, briefs 22/23, current reports and
   tests.
3. **Data:** metadata and existing immutable receipts only.
4. **Interface:** this reviewed high-level plan.
5. **Tests:** current active fill study and `main` chain-consistency tests.
6. **Acceptance:** exact commits and branch divergence recorded; only this
   document changed.
7. **Failure:** merging branches, cleaning operational evidence, or proposing
   an already-landed tool.
8. **Rollback:** discard this uncommitted document edit.
9. **Dependencies:** none.
10. **Exclusions:** code, config, scheduler, PR, commit, OOS access.

### Phase 2 — WS-F observation and retention decision

1. **Goal:** determine whether existing flags create actionable data-quality
   information rather than noise.
2. **Repo areas:** `data/chain_consistency.py`,
   `tools/chain_consistency_audit.py`, `.cache/schwab_chains/`, immutable
   receipt output only.
3. **Data:** consecutive Schwab captures and matching underlying closes;
   approximately 30 captured sessions is the existing owner disposition's
   review horizon, not a statistical proof threshold.
4. **Interface:** existing standalone CLI and receipt schema; human review
   log/decision record, not a production caller.
5. **Tests:** existing 35-test suite; deterministic rerun/hash equality;
   synthetic known-corruption fixtures; verify no production import/caller.
6. **Acceptance:** all flags are reproducible and categorized as actioned,
   expected, or noisy; an explicit KEEP-MANUAL / REMOVE / PROCEED-TO-SEPARATE-
   DESIGN decision is recorded.
7. **Failure:** flags influence rankings/verdicts/capture acceptance; thresholds
   are tuned post hoc; receipts cannot reproduce.
8. **Rollback:** retain historical receipts and remove the isolated module/CLI
   in a separately approved change if the decision is REMOVE.
9. **Dependencies:** enough naturally accumulated capture sessions; no new
   provider.
10. **Exclusions:** signal use, automatic gating, dashboard/digest/scheduler
    wiring, network calls, baseline changes.

### Phase 3 — WS-A data-triggered reconsideration

1. **Goal:** decide whether the 1% adverse haircut can ever be calibrated to
   realized execution rather than quote context.
2. **Repo areas:** existing fill report/tool/test; any future execution dataset
   must enter through a separately approved raw/normalized/provenance boundary.
3. **Data:** broker execution time, order/package identity, leg fills,
   quantities, partial/cancel states, contemporaneous bid/ask and timestamps.
4. **Interface:** no proposal until the data contract is known; eventual
   output would remain a dated research receipt and owner amendment decision.
5. **Tests:** schema/unit/timezone/provenance checks; order-to-quote matching;
   missing/ambiguous-match refusal; frozen-baseline invariance.
6. **Acceptance:** adequate matched observations and an uncertainty interval
   tied to retail business impact, not a paper-derived constant.
7. **Failure:** package identity absent, timestamps ambiguous, selection bias
   unmeasured, or quotes substituted for fills.
8. **Rollback:** leave `SLIPPAGE_HAIRCUT` and `FILL_MODEL_ID` unchanged.
9. **Dependencies:** new owner-approved, legally usable observed execution
   evidence; currently absent.
10. **Exclusions:** synthetic fill probabilities, paid data, new ThetaData
    acquisition, live/broker-write paths, locked OOS reinterpretation.

### Phase 4 — Conditional H feasibility check

1. **Goal:** establish whether a current position/strategy creates an
   unanswered deterministic tail-risk question.
2. **Repo areas:** current paper position schema, `strategies/base.py`, and
   robustness stress outputs.
3. **Data:** current defined position plus cached option/underlying context;
   ex-div dates only if assignment is in scope.
4. **Interface:** separate display-only scenario result, never a score.
5. **Tests:** pinned payoff math, missing-leg refusal, gap/IV/skew/cost cases,
   baseline byte invariance.
6. **Acceptance:** a named exposure and decision use exist before design; each
   scenario has units, provenance and conservative fallback.
7. **Failure:** no exposed short/multi-leg position, arbitrary scenario values,
   or a directional/probabilistic claim.
8. **Rollback:** omit/remove isolated scenario output.
9. **Dependencies:** exposure trigger and separate owner-approved brief.
10. **Exclusions:** generative order books, assignment probabilities, rank or
    verdict authority.

## 7. Validation Design

- **Baseline comparison:** F compares receipt output and human actionability
  against the current manual/no-caller state; A remains compared only with the
  frozen fill convention, without re-scoring returns; H, if triggered, compares
  scenarios with the unchanged marked position.
- **Primary metrics:** F — reproducible flags per session and fraction leading
  to a documented data correction/investigation; A — matched realized
  slippage relative to contemporaneous executable quotes, only if such matches
  later exist; H — deterministic P&L/max-exposure change in dollars and percent
  of defined retail capital.
- **Guardrails:** zero production imports/callers, zero ranking/verdict byte
  drift, zero network calls, zero OOS looks, immutable input/output hashes,
  explicit max-as-of timestamps.
- **Walk-forward:** none for non-predictive QA. Any future directional feature
  requires a new registered causal walk-forward experiment with purge/embargo.
- **OOS protection:** do not rescore frozen runs, inspect locked windows, or
  spend the look budget. Research snapshots after the registered cutoff remain
  descriptive data-quality evidence only.
- **Multiple testing:** no p-values for F/A context. Any later metric family
  uses the existing Holm requirement and predeclared hypotheses.
- **Regime checks:** only after a minimum outcome sample is established;
  predeclare a small set of materially distinct slices. No seven-way fishing.
- **Cost stress:** retain the existing cost/bid-ask arms. A new haircut is not
  accepted merely because it improves headline returns.
- **Tail risk:** deterministic gaps, IV/skew shocks, missing exit liquidity and
  assignment are conditional H scenarios, not likelihood forecasts.
- **Minimum worthwhile improvement:** F must cause a documented data action or
  materially reduce ambiguity during its review horizon; otherwise remove or
  keep it manual. A must materially narrow uncertainty about *realized* retail
  execution using matched observations; quote-only results cannot qualify.
  H must answer a named exposure decision. These criteria are tied to use and
  observed sampling—not arbitrary return thresholds.

## 8. Data Feasibility

Fresh read-only inventory on 2026-08-24:

| Improvement | Required data | Existing coverage | Missing fields / quality | Licensing / retail feasibility | Effect of missing data | Safe fallback |
|---|---|---|---|---|---|---|
| A — quote context | Bid/ask, contract fields, session/quote time, underlying close | Legacy `.cache/chains/`: 31,366 files, 26 symbols, 2018-01-02–2026-07-27; Schwab: 60 files, 15 symbols, four capture dates, 143,738 rows; intraday: 956 sparse snapshots/14 dates | Legacy has no timestamps/sizes; Schwab has no sizes and 19,834 missing `trade_timestamp`; intraday has scheduled snapshots, not continuous paths | Existing authorized cached/read-only sources | Supports spread/context description only | Keep report descriptive |
| A — realized/package fills | Broker order, package, leg-fill, partial/cancel and contemporaneous quote states | **Absent**; no package/combo/net quote fields found | Entire empirical execution path absent | No live/broker-write authority; new ThetaData acquisition disabled | **Blocked by missing data**; cannot calibrate fills or fill probability | Keep frozen model and disclose uncertainty |
| F — cross-session QA | Consecutive chains, timestamps, bid/ask/delta and underlying closes | Schwab captures plus cached closes; main tool already supports pairs | Sparse/nonuniform sessions; one local-date mismatch; no size velocity | Existing read-only bytes, retail-feasible | Gaps become explicit but velocity cannot be reconstructed continuously | Flag `GAP_SESSION`; never infer missing motion |
| B — assignment | Short-position path, ex-div dates, exercise/assignment events, buying-power state | One current long-call paper position; no active short/multi-leg book; annual expected dividends only | No ex-dividend event history, empirical assignment events, or broker buying-power history | Future public/official calendar may be feasible but is not approved/present | **Blocked by missing data and exposure** | Preserve limitation disclosure; deterministic expiration only |
| D — surface QA/context | Cross-strike/expiry bid/ask/IV/Greeks | Legacy and v2 caches; v2 has 4,608 partitions, 18 symbols, 256 sessions and sizes/timestamps | Three quarantined v2 sessions; 152 symbol-sessions excluded by staleness in fill study; sparse surfaces can be discontinuous | Existing v2 bytes are read-only research data; no new acquisition | Coverage gaps prevent complete surface claims | Fail closed/label coverage; no interpolation-as-truth |
| E/G — stability/ablation | Sufficient independent completed outcomes | Market-state data exists; strategy outcome cohorts are starved | Outcome sample, not feature rows, is limiting | Existing data only | Slices/ablations would overfit | Park until preregistered sample-power criterion is met |
| H — deterministic stress | Position definition and deterministic marks | Technically available for defined positions | Ex-div/event path absent for assignment case | Retail-feasible offline | Non-assignment scenarios possible, but currently lack a decision use | Park until exposure trigger |

Additional verified quality facts: Schwab bid/ask/OI/IV/delta fields are
complete and contain no crossed/locked rows in the current inventory; 19,834
rows lack `trade_timestamp`. Tier-2 fill-study processing used 4,605 of 4,608
partitions after three quarantines, admitted 2,236,735 rows, and excluded 152
symbol-sessions for excessive staleness. On 2026-08-24 all 15 raw closes were
missing, so 11,863 admitted rows were correctly excluded from decomposition
and moneyness. Quoted size is context, not proof of executable capacity.

## 9. Architecture Boundaries

- **Domain:** deterministic pricing, QA, stress and cost calculations remain
  pure tested Python. No LLM or orchestration system calculates a verdict.
- **Providers:** no new provider/service and no network in research, scoring,
  dashboard, ranking, or verdict code. Cached raw bytes stay immutable.
- **Pipelines/storage:** normalized data retains provider, timestamps, units,
  contract identity, hashes and max-as-of. Missing/ambiguous combinations fail
  closed. Existing ThetaData bytes remain protected and read-only.
- **Persistence:** research receipts/reports are separate from paper positions,
  facts, registered experiment records and production state.
- **Interfaces:** F remains CLI/manual research during observation. D and any
  future H output stay display-only. No grades, Top-3, entries, exits, sizing,
  risk caps or verdicts change.
- **Orchestration:** current launchd/receipt-reading operations remain. No n8n
  or framework migration is proposed.
- **Equity boundary:** `equity-research` remains the sole source for shared
  equity intelligence; any consumption remains read-only and timezone-aware
  through the existing `as_of` contract.

Candidate I review supports these boundaries but not adoption: NautilusTrader's
[explicit order-state machine](https://nautilustrader.io/docs/latest/concepts/orders/)
is useful vocabulary for a future execution dataset, not a reason to add a
live engine; Qlib's
[Experiment/Recorder hierarchy](https://qlib.readthedocs.io/en/stable/component/recorder.html)
duplicates this repo's ledger/receipt model and would add MLflow burden; LEAN's
[default assignment model](https://github.com/QuantConnect/Lean/blob/master/Common/Securities/Option/DefaultOptionAssignmentModel.cs)
is a heuristic, not an empirical assignment probability; QuantLib's
[American-option fixtures](https://github.com/lballabio/QuantLib/blob/master/test-suite/americanoption.cpp)
reinforce the isolated test-fixture approach already present. Lumibot remains
the thin existing backtest engine; no framework lesson establishes migration
value.

## 10. Risks and Stop Conditions

1. **False confidence:** stop A if quote movement or size is described as
   realized fill evidence; stop B if probabilities are invented.
2. **Leakage:** stop any work that touches locked OOS data, reinterprets frozen
   runs, or selects thresholds after seeing protected results.
3. **Overfitting:** park E/G until preregistered sample power exists; do not
   manufacture cohorts by slicing sparse outcomes.
4. **Execution risk:** keep conservative fills unchanged unless matched,
   auditable observations justify an owner-approved amendment.
5. **Data quality:** stop on missing provider identity, ambiguous timestamps,
   unrecognized contract definitions, quarantined sessions, or nonreproducible
   hashes.
6. **Maintenance:** remove F if flags are unactionable/noisy after the review
   horizon rather than tuning them to silence. Reject a second experiment
   ledger or framework runtime.
7. **Authority:** stop any proposal importing these outputs into ranking,
   grades, Top-3, trade decisions, sizing, risk, capture refusal, or orders.
8. **Parking triggers:** B stays parked until measurable short American-option
   exposure plus point-in-time ex-div data; H until a named exposed position;
   E until adequate independent outcomes; A-full until actual fills exist.

## 11. Recommended Implementation Order

There is no immediate implementation sequence because no new implementation is
recommended.

1. **Accumulate evidence for F first.** The tool exists, data arrives naturally,
   and its retain/remove decision has no dependency on strategy returns.
2. **Record F's human disposition.** Only a documented actionable use may
   justify a separate integration design; otherwise keep manual or remove.
3. **Leave A frozen.** Reopen only after an approved execution-data contract
   exists; then design data validation before fill modeling.
4. **Remeasure exposure before B/H.** A short/multi-leg strategy or position
   must exist before assignment/stress work becomes decision-relevant.
5. **Consider E/G only after sample-power evidence.** Outcome sufficiency
   precedes slicing or ablation.

Each later implementation, if authorized, receives its own brief and review.
Execution, assignment, surface, anomaly, and stress work remain separate.

## 12. Final Decision Table

| Candidate | Decision | Current reason |
|---|---|---|
| A — Execution realism | **RESEARCH ONLY** | Narrow context study is complete; actual calibration remains blocked by missing fills/package paths |
| B — Early-assignment scenarios | **PARK** | No meaningful current exposure and no point-in-time ex-div/assignment observations |
| C — Marginal-value experiment gate | **REJECT** | Duplicates existing `ExperimentSpec`, ledger, hashes, OOS and feasibility controls |
| D — Simple option-surface features | **RESEARCH ONLY** | Core simple features already exist display-only; retain as QA/context, add no complex model |
| E — Era and regime stability | **PARK** | Outcome cohorts are too sparse for credible slices; descriptive regime tools already exist |
| F — Delta and quote-velocity anomalies | **RESEARCH ONLY** | Existing isolated audit should undergo an observation/retention review before any integration |
| G — Feature grouping and ablation | **REJECT** | No predictive consumer; adds selection freedom without validation value |
| H — Deterministic stress tests | **PARK** | Technically feasible but lacks a current exposed short/multi-leg position and named decision use |
| I — External framework lessons | **REJECT** | Static lessons/QuantLib fixtures are already absorbed; migration/runtime dependencies have no repo-supported benefit |

**Ready decision:** ready for owner review as a current-state high-level plan;
**not ready for implementation**. The next authorized action, if accepted, is
observation and disposition of existing Candidate F—not a coding brief.

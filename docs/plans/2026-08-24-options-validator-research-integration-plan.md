# Options-Validator Research Integration Plan — 2026-08-24

**Status: APPROVED TO BRIEF STAGE (owner, in-session 2026-08-24).** The owner
ruled "yes to chains_v2 read-only" — WS-1 Tier-2 read-only research access to
`.cache/chains_v2/od1-2026-08-01/` is authorized (read access only; no merge
of `codex/od1-v2-current`, no verdict eligibility, quarantine stands).
Implementation briefs drafted the same session:
`docs/superpowers/plans/2026-08-24-22-chain-consistency-flags-codex-brief.md`
and `docs/superpowers/plans/2026-08-24-23-slippage-haircut-calibration-codex-brief.md`
(both DRAFT pending independent adversarial review). Original draft status
paragraph retained below for history.

*Original status (2026-08-24 am):* DRAFT — NOT approved, NOT scheduled, NOT
committed. High-level plan only; no implementation specs exist yet. Produced by a Claude orchestration
session from five independent read-only repo audits (execution mechanics,
assignment/dividends, statistical controls, experiment isolation, dataset
inventory). No production behavior was modified; no file other than this one
was written.

**Repo state at audit time (Verified):**

- Branch: `claude/codex-handoff-plan-2026-08-22`
- HEAD: `24368f675f0e70a0c58c39fedb16d0e20a2a6f83` (2026-08-23)
- Working tree: clean
- Recent relevant commits: `24368f6` (2026-08-23 status refresh, PR 63–68
  reconciliation), `2e7eb3e` (owner override: `exact_session_source_active`),
  `3f7d946` (brief-18 merge)

**Evidence labels used throughout:** Verified (code/test/receipt read at HEAD),
Inferred, Unknown, Blocked-by-missing-data.

---

## 1. Executive Verdict

**Move forward (PROCEED TO DESIGN), two small workstreams:**

1. **WS-1 — Slippage-haircut calibration study (Candidate A, narrow slice).**
   The fill model (`conservative_bid_ask_plus_haircut_v1`) is already
   worse-than-mid on both legs, but its 1% adverse haircut
   (`config.SLIPPAGE_HAIRCUT`, `config.py:91`) has **no calibration receipt
   anywhere in the repo** — it is an uncalibrated constant inside every
   verdict-bearing cost model. A bounded, descriptive, research-only study of
   observed spread distributions can either support the constant or show it is
   too generous, without changing it. This is the single highest
   validation-quality-per-complexity item found.
2. **WS-2 — Cross-session chain-consistency shadow flags on the Schwab capture
   lane (Candidate F, narrow slice).** The Schwab 15:45 preclose lane is now
   the repo's only source of forward chain data, holes are permanent, and a
   silently corrupted capture is unrecoverable. Existing audits are strong
   *within* one session (crossed quotes, no-arb bounds, Greek/IV plausibility,
   duplicates) but there is **no day-over-day consistency check** (implausible
   delta/IV jumps vs. the underlying move, vanished strikes, spread blowouts).
   Shadow-mode data-quality flags — never directional signals — protect
   irreplaceable data at low cost.

**Research-only:** Candidate H (deterministic stress scenarios on the paper
book and candidate structures — cheap, deterministic, display-only, but low
urgency with a one-position book), and the no-arb static surface checks from
Candidate D folded into WS-2's audit stack as data-quality checks, not
features.

**Parked:** Candidate B (early assignment — measured current exposure is
**zero**; every position ever opened is long-only; blocked anyway on a missing
ex-dividend-date calendar), Candidate E (regime/era result slicing — no lane
has enough completed trades to slice; slicing starved samples manufactures
false confidence), Candidate I's static pricing/Greeks golden fixtures (fine
idea, no present defect to justify it).

**Rejected:** Candidate C (marginal-value experiment gate — duplicates the
existing pre-registration ledger + 2026-07-24 feasibility gate + robustness
harness's required-fields spec + experiment-program constraints almost
entirely), Candidate G (feature-group ablation — there is no predictive model
in the repo to ablate; complexity with no consumer), Candidate D's new surface
features beyond QA checks (ATM IV, IV−RV, IV rank, term slope, 25Δ skew
already exist; rough-Heston/neural is unsupported by any repo need), and
Candidate I's framework migration in any form.

**Main reasons in one line each:** WS-1 attacks the one uncalibrated constant
inside the frozen cost model; WS-2 protects the only irreplaceable growing
dataset; B has zero measured exposure; C/G/most-of-D duplicate existing
controls or have no consumer; E would slice samples that don't exist yet.

---

## 2. Repo-Verified Current State

| Capability | Current implementation | Evidence | Quality | Remaining gap | Duplication risk if rebuilt |
|---|---|---|---|---|---|
| Conservative fills | Short leg at bid, long at ask (half-spread each), then ±1% adverse haircut; identical convention entry and exit; feed pre-widens quotes so engine fills can never beat it | `strategies/base.py:12-97` (`adverse_buy/adverse_sell/entry_credit_conservative`), `data/pandas_feed.py:176-177`, `tests/test_h7_fill_model.py:41-61` | Verified, strong | Haircut value never calibrated (see WS-1); no regulatory/exchange fees beyond $0.65/contract commission | HIGH — one canonical transform, hash-frozen (`FILL_MODEL_ID`, `config.py:237`) |
| Commission modeling | $0.65/contract, both legs, both ways; Lumibot `TradingFee` in engine path, manual reconstruction with `isclose` cross-check in H7 scoring | `config.py:90`, `harness/run_backtest.py:74`, `options_researcher/h7_forward_scoring.py:302-316` | Verified, strong | No OCC/SEC/TAF fee line items (small, direction: inflates results slightly) | HIGH |
| Liquidity gates | `MIN_OPEN_INTEREST=100`, `MAX_SPREAD_PCT=0.10`, both legs; stricter H7 admission gate (5% spread, ≥5 NTM contracts) | `data/chain_policy.py:43-57`, `strategies/put_credit_spread.py:103-106`, `config.py:466-467` | Verified, strong | **No position-size-vs-OI participation check** (e.g. size ≤ 1% of OI) — established by search | MEDIUM |
| DSR/PSR diagnostics | Full Bailey & López de Prado formulas, shipped and tested, opt-in display layer, refuses to run without variance provenance; explicitly does not replace the loss-gated verdict | `metrics.py:446,487,560-584`, `tools/score_backtest.py:60-141`, `tests/test_deflated_sharpe.py` | Verified, strong — **stronger than the handoff assumed** | None material | HIGH |
| CSCV/PBO | **Not implemented.** `pbo` is a hard-null-enforced ledger stub; pre-registered floors (`CSCV_MIN_VARIANTS_M=10`, `CSCV_MIN_SPLITS_S=16`) exist so a future build can't launch under-powered | `research/ledger.py:422-423`, `config.py:211-222` | Verified absent, deliberately | No registered grid even clears M=10, so building it now has no input | LOW (nothing to duplicate) |
| OOS-look budgeting | `IN_SAMPLE_END=2022-12-31`, budget 3, charge-on-touch, write-once reveal, data-layer `OOSDataTouchError`; ledger shows **0/3 spent** | `research/experiments.py:224`, `data/thetadata_adapter.py:421-490`, `ledger/experiments.jsonl` | Verified, strong | None | HIGH |
| Block-length sensitivity | Stationary + circular block bootstrap across 4 theory-anchored block lengths; reports the **widest** CI; no verdict below 3 weekly cohorts | `metrics.py:69-149`, `tests/test_bootstrap.py` | Verified, strong | None | HIGH |
| Walk-forward | Generic `WalkForwardSplitter` (expanding/rolling, purge, embargo) used by the robustness harness; per-hypothesis forward paper windows coexist | `options_researcher/robustness/walk_forward.py`, `runner.py:499` | Verified | Not mandatory for every hypothesis (by design) | HIGH |
| Multiple-testing | Holm step-down is a **required** field of `ExperimentSpec` in the robustness harness | `options_researcher/robustness/statistics.py:104`, `models.py:136-137` | Verified | Only inside the harness; the one-run/OOS-budget discipline covers the rest | HIGH |
| Experiment isolation | Separate `experiments_dashboard.py` CLI; production board has zero experiment imports, enforced by AST-walking tests + subprocess byte checks; baseline selection bytes proven invariant | `tests/test_experiments_baseline.py:92-138`, `tests/test_attractiveness_dashboard.py:1661` | Verified, strong | `EXP-SHORT` is ON by default (`SHORT_CONTEXT_ENABLED=True`, owner-directed) unlike the other four lanes — isolated but not off | HIGH |
| Point-in-time / as-of | Pervasive: max-as-of stamps, staleness gates (`CHAIN_STALE_*`), strictly-causal regime labeling, D+1 causal fill convention, tz-aware freshness that fails closed | `options_researcher/regime.py:14-19`, `config.py:672-676`, `tests/test_causal_fill_convention.py` | Verified, strong | Two staleness thresholds are LLM-asserted, not owner-typed (`config.py:672-674` says so) | HIGH |
| Provenance | `diagnostic_source_hash` v3, immutable receipts (`research/receipts.py`), Schwab capture receipts + facts, `BLIND_CACHE` facts, cache manifest (31,366 files) | `research/hashing.py:126-155`, `data/schwab_chain_capture.py:296-333`, `tools/cache_manifest.py` | Verified, strong | No literal `source_url` field on captures (carried as provider identity + hash chain instead) — naming gap only | HIGH |
| Within-session data-quality audits | Crossed/negative quotes, no-arb bid/ask bounds, Greek plausibility, IV extremes, duplicates, missing sessions/strikes vs calendar, sha mismatch, PASS/WARN/BLOCK verdicts | `options_researcher/quote_integrity.py:92-137`, `data/recent_topup.py:478-547`, `tools/h7_data_audit.py:271-543` | Verified, strong | **No cross-session (day-over-day) consistency checks** — see WS-2 | MEDIUM |
| OI context | Post-ranking neutral "OI Δ1d" line, board-invariance tested; percentile v2 deliberately inactive pending calibration | `options_researcher/oi_change.py`, `tests/test_oi_change_line.py` | Verified | v2 percentile gated (by design) | HIGH |
| Surface features | ATM IV, RV21, IV−RV, IV rank, term slope (near vs far ATM IV), 25Δ put/call skew + percentiles — display-only, cited constants | `options_researcher/features.py`, `composite_signals.py:61,128-309`, `config.py:815-833` | Verified | No wing curvature / butterfly-convexity / calendar-monotonicity checks (QA-grade only — see WS-2 scope) | HIGH for the listed features |
| Assignment/expiration | Deterministic intrinsic-at-close settlement at the OCC $0.01 exercise-by-exception threshold, conservative fallback, mandatory assignment disclosure on every settlement artifact; **no probabilistic early-assignment model, disclosed as a known limitation** | spec `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md` §4a; `options_researcher/h7_paper_lifecycle.py:1176-1341`; 70 tests pass; README "Known limitations" | Verified (built, tested, **never fired in production** — H7 event store holds exactly 1 registration event) | Early assignment unmodeled; ex-div calendar dataset missing (`exp_tbill_carry.early_assignment_flag` is a permanent `DATA_BLOCKED` stub) | MEDIUM |
| Dividends/corp. actions | 15-row forward annual-dividend snapshot (owner spot-checked 2026-07-23, feeds Black-Scholes q only); manual 5-symbol split registry for close alignment | `data/rates/expected_dividends.csv`, `reports/2026-07-23-dividend-payer-spot-check.md`, `data/underlying_closes.py:208-214` | Verified | No dividend history, no ex-div dates, no other corporate-action types | LOW |
| Network isolation (OD-4) | Active socket/urllib/requests sentinel replay test for the data-consumer path; dashboard path isolated structurally (zero network imports) | `tools/thetadata_exit_audit.py:843-1048`, `tests/test_offline_intelligence_readiness.py:236` | Verified | Dashboard-path isolation is by-absence, not actively sentinel-tested (minor) | HIGH |
| equity-research bridge | Read-only sqlite (`mode=ro`), tz-aware `as_of` filter on `published_at`, fail-empty; **zero callers** beyond its own test at HEAD | `options_researcher/market_context.py:90-120` | Verified | None (retained by owner decision) | HIGH |
| Backtest engine | Lumibot `PandasDataBacktesting` still the live engine for Strategy A (the only reachable verdict-bearing backtest); H7 historical diagnostic permanently withdrawn behind a frozen hash gate; H7 forward-paper machinery BUILD-ONLY/INACTIVE (`h7_active=False`) | `harness/run_backtest.py`, `config.py:554`, `data/ritual_authority.py:39` | Verified | Partial-fill modeling exists only in the Strategy A path, not `h7_paper_lifecycle.py` (moot while inactive; flag at activation) | n/a |

**Execution-resolution answer (handoff gap #1): Verified EOD-only** for
anything verdict-bearing, structurally (the scoring paths only ingest daily
EOD chains; `.cache/intraday/` is a walled-off display-only recorder). This is
a data constraint, not a modeling oversight.

---

## 3. Audit of the Prior Recommendation (the handoff's claims)

**Still valid:** conservative fills, commission modeling, liquidity gates,
DSR/PSR, OOS budgeting, block-length sensitivity, experiment isolation,
baseline-invariance, point-in-time controls, provenance, dashboard split,
experiment program, OI context tests, data-timing tests — all Verified present
(most are stronger than claimed). Claimed gaps confirmed: EOD-only resolution,
arbitrary (uncalibrated) adverse haircut, no early-assignment simulation, no
execution calibration against observed data, no point-in-time dividend-based
assignment testing.

**Incorrect or stale claims needing correction:**

1. **"CSCV safeguards" exist — FALSE.** CSCV/PBO is a hard-null stub with
   pre-registered floors only (`research/ledger.py:422-423`,
   `config.py:211-222`). Listing it as an existing control overstated the
   stack.
2. **`PROJECT_CONTROL.md` — does not exist.** The canonical roadmap is
   `PROJECT_STATE.md`; the scope registry is README "Scope status".
3. **"n8n only coordinates scans, alerts…" — stale.** n8n was evaluated and
   **rejected** 2026-08-22 with recorded reasoning
   (`docs/superpowers/plans/2026-08-22-19-lean-ops-codex-handoff-plan.md:10`).
   The current approved rule is launchd + a $0 receipt-reading digest. Nothing
   in this plan assumes n8n.
4. **"Weak multi-leg slippage modeling" — half wrong.** Slippage is per-leg
   conservative with strict leg-by-leg reconstruction checks
   (`options_researcher/h7_forward_scoring.py:142-265`); what's missing is
   package/combo quotes, and **no dataset on disk carries them**, so
   "improving" this is blocked by data, not by code.
5. **Priority correction:** the handoff implicitly ranked execution realism
   and assignment as co-equal headline items. Measured repo reality inverts
   assignment's priority to near-zero (current assignment exposure is zero —
   §Candidate B) and narrows execution realism to one calibration question.
6. **Assumption correction:** "EXPLORE/IMPLEMENT/VALIDATE/OOS_REVEAL
   boundaries" is not this repo's vocabulary; the actual machinery is
   pre-registration → one-run-spent → charge-on-touch OOS budget → sealed
   holdout. The intent is preserved; the plan uses the repo's real terms.
7. **Known prior-claim hash error found in passing:** the OI-change line's
   shipping commit is `b78d1c7`, not `2864008` (which resolves to an unrelated
   2026-07-24 merge). Recorded here so it isn't re-propagated.

---

## 4. Candidate Scorecard

Scale 1–5 on every axis, **5 always the favorable end** (so for complexity,
maintenance, and false-confidence risk, 5 = low burden / low risk).
Weights: validation benefit ×2.0; data availability ×1.5; false-confidence
safety ×1.5; overlap-novelty, complexity, maintenance, evidence quality ×1.0
each; reversibility, retail relevance, architecture fit ×0.5 each (total
weight 10.5, max score 52.5). Rationale for weights: this repo's stated
objective function is validation quality per unit of complexity and research
risk, and its history shows data availability and false confidence are the
two recurring failure modes (od1-v2 data loss; "green suite hid a real
defect" in the evidence-upgrade memory).

| Candidate | Benefit | Evidence | Novelty | Data | Simplicity | Maint. | FC-safety | Revers. | Retail | Fit | **Weighted** | Decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A-narrow** (haircut calibration + participation flag) | 4 | 5 | 4 | 3 | 4 | 4 | 4 | 5 | 4 | 5 | **41.5** | PROCEED TO DESIGN |
| **F-narrow** (cross-session capture QA flags) | 4 | 5 | 3 | 5 | 4 | 4 | 5 | 5 | 4 | 5 | **44.0** | PROCEED TO DESIGN |
| H (deterministic stress scenarios) | 3 | 4 | 3 | 5 | 4 | 4 | 4 | 5 | 4 | 4 | **38.0** | RESEARCH ONLY |
| D (surface features beyond QA) | 2 | 3 | 2 | 4 | 3 | 3 | 2 | 4 | 2 | 4 | **27.0** | RESEARCH ONLY (QA checks only, folded into F) / REJECT for new features |
| A-full (quote aging, package quotes, fill probability, broker calibration) | 4 | 4 | 2 | 1 | 2 | 3 | 3 | 4 | 4 | 4 | **28.5** | BLOCKED BY DATA |
| B (early assignment) | 2 | 5 | 3 | 1 | 2 | 3 | 3 | 4 | 3 | 4 | **26.0** | PARK |
| E (era/regime result slicing) | 2 | 3 | 3 | 4 | 3 | 3 | 1 | 5 | 2 | 4 | **26.5** | PARK |
| I (framework lessons: static fixtures) | 2 | 3 | 3 | 5 | 4 | 3 | 4 | 5 | 2 | 3 | **32.0** | PARK (fixtures); REJECT (any migration/runtime dep) |
| C (marginal-value experiment gate) | 1 | 4 | 1 | 5 | 3 | 2 | 4 | 4 | 2 | 3 | **26.0** | REJECT |
| G (feature grouping/ablation) | 1 | 2 | 4 | 3 | 2 | 2 | 2 | 4 | 1 | 2 | **20.5** | REJECT |

Key score explanations (no weak data score hidden behind a strong paper):

- **A-narrow Data=3, not higher:** the only quote-size dataset
  (`.cache/chains_v2/od1-2026-08-01/`, 18 symbols, 2025-07-25→2026-07-31) is
  **parked/display-only per its own scope amendment**, with 3 quarantined
  sessions and 10,391 non-blocking warnings; using it even read-only for a
  calibration *report* should get explicit owner acknowledgment because
  `PROJECT_STATE.md` P2.2 parks the lane pending an integration decision. The
  fallback (Schwab preclose spread distributions, no sizes) is unambiguous but
  thinner (3 capture days so far, growing daily).
- **A-full Data=1:** no intraday continuous quotes, no package quotes, no
  broker fills (guardrail-enforced absence), and ThetaData acquisition is
  permanently disabled. These are not buildable gaps.
- **B Benefit=2 despite a real theoretical hole:** the audit measured current
  assignment exposure at exactly zero (every position ever opened is long-only;
  all short-leg designs are retired, archived-unrun, paused with zero fills, or
  observe-only). The repo also already *discloses* the limitation on every
  relevant surface (README, H7 spec §8 mandatory disclosure).
- **C Novelty=1:** each of the 12 fields the handoff asks the gate to record
  already exists somewhere binding: research question/baseline/hashes/metrics →
  pre-registration ledger + `ExperimentSpec` required fields; guardrail
  metrics → robustness stability gates (now surfaced into the registry payload
  per the implemented variant of the 2026-08-13 draft spec); locked test
  period → registered windows; removal/rollback → the 2026-08-09 experiment
  program's per-experiment requirements. Only "complexity cost / data cost /
  maintenance cost / minimum worthwhile improvement" are unformalized — a
  three-line addition to the experiment-spec template, not a process.
- **E FC-safety=1:** slicing a book with one open long call and zero completed
  short-leg trades across 7 regime dimensions is a false-confidence machine by
  construction. The Wasserstein lane + `regime_concentration` gate already
  cover the descriptive need.
- **G Benefit=1:** ablation requires a model; the repo deliberately has none
  (four cited display-only angles, no combined predictive fit).

---

## 5. Recommended Scope

Smallest set with meaningful incremental value — **two independent
workstreams**, deliberately not combined into one brief:

- **WS-1: Execution-cost calibration study (research-only, descriptive).**
  Question: is `SLIPPAGE_HAIRCUT = 0.01` + half-spread consistent with, or
  more generous than, observed spread behavior on the traded universe?
  Output: a dated report + receipt under `reports/`, and (only if the owner
  later chooses) a proposed re-freeze of the constant through the standard
  amendment path. **No config change in this workstream.**
- **WS-2: Schwab-lane cross-session consistency flags (shadow-mode QA).**
  Question: did today's capture plausibly follow yesterday's, given the
  underlying move? Output: per-name flags in the existing capture-audit /
  job-health surfaces, fail-visible, never gating entries and never a signal.

Optional third, sequenced last and only if appetite remains:
**WS-3 (research-only): deterministic stress-scenario library** for
defined-risk structures (spread widening ×k, IV shock ±n vol points, gap ±m%,
missing-leg exit at conservative fallback), reusing `strategies/base.py`
pricing helpers, rendered on the experiments dashboard only.

Explicitly excluded from scope: everything under A-full, B, C, D-features, E,
G, and I (per §4).

---

## 6. Phased Plan

### Phase 1 — WS-2: cross-session capture consistency flags

1. **Goal:** detect implausible day-over-day changes in the Schwab preclose
   captures (and, retroactively, the legacy cache) before bad bytes become
   load-bearing history.
2. **Repo areas:** `data/recent_topup.py` audit stack pattern,
   `tools/h7_data_audit.py`, `options_researcher/quote_integrity.py`
   (tier vocabulary), `data/schwab_chain_capture.py` receipts,
   `tools/job_health_digest.py` (surface). New module proposed:
   `data/chain_consistency.py` (name indicative).
3. **Data requirements:** consecutive-session chain parquets + underlying
   closes — all on disk already. No new data.
4. **Proposed interfaces:** pure function `audit_pair(prev_chain, cur_chain,
   prev_close, cur_close) -> ConsistencyReport` with statuses mirroring the
   existing precedence style (`OK / GAP_SESSION / STRIKE_VANISHED /
   DELTA_JUMP / IV_JUMP / SPREAD_BLOWOUT / …`); wired as a post-capture,
   post-ranking, never-gating pass (the `oi_change.py` attachment pattern).
5. **Tests:** fixture pairs for each flag; a board/receipt-invariance test
   (flags change no ranking bytes — reuse the byte-identity pattern from
   `tests/test_experiments_baseline.py`); precedence tests; fail-visible (a
   broken consistency pass renders an ERROR card, never a silent skip).
6. **Acceptance criteria:** all existing suites stay green (exit code, not
   grep); zero changes to `select_top_picks` bytes; flags reproduce
   deterministically from cached bytes; the known-good 08-19→08-20 Schwab pair
   audits clean; an injected synthetic corruption is flagged.
7. **Failure conditions:** any flag consulted by an entry/exit/gate path; any
   threshold presented as owner-typed when it is LLM-proposed.
8. **Rollback:** delete the module + its attachment call; isolation tests
   prove the baseline was never touched (same rollback shape as the
   experiment lanes).
9. **Dependencies:** none.
10. **Exclusions:** no anomaly-as-signal use (handoff's own rule), no network,
    no live-lane behavior change, no capture-refusal authority (the wrapper's
    existing alignment guard stays the only refusal mechanism).

### Phase 2 — WS-1: slippage-haircut calibration study

1. **Goal:** a descriptive, receipt-bound answer to "what adverse fraction
   beyond the touch do observed spreads imply for the contracts this platform
   actually admits?" — compared against the frozen 1%.
2. **Repo areas:** read-only over `.cache/schwab_chains/` (spread
   distributions on admitted contracts, per `passes_liquidity` and the H7
   admission gate), optionally `.cache/chains_v2/` (the only `bid_size`/
   `ask_size` source) **if and only if the owner authorizes read-only research
   use of the parked lane**; report under `reports/`.
3. **Data requirements:** existing bytes only. Two tiers: Tier-1 (Schwab
   captures, unambiguous, thin but growing daily); Tier-2 (chains_v2,
   one year × 18 symbols with quote sizes, owner-gated, quarantined sessions
   excluded per `data/v2_partition_quarantine.json`).
4. **Proposed interfaces:** a read-only CLI in `tools/` producing a dated
   report + JSON receipt (spread-pct distributions by symbol/DTE/moneyness
   bucket, admitted-contract subset vs. full chain, and the implied cost of
   the current haircut vs. observed half-spreads). No import into `config.py`,
   `strategies/`, or any scoring path.
5. **Tests:** fixture-driven distribution math; refusal on quarantined
   sessions; refusal on chains_v2 input unless an explicit
   `--allow-parked-lane` style acknowledgment flag is passed (fail-closed
   default).
6. **Acceptance criteria:** report states per-bucket observed half-spread and
   the percentile at which the current model's total adverse assumption
   (half-spread + 1%) sits; every number carries its max as-of session; the
   report explicitly does NOT recommend a new frozen value (that is an owner
   amendment decision).
7. **Failure conditions:** any write to `config.py`; any claim phrased as
   "the haircut is correct/proven"; any use of the 3 quarantined chains_v2
   sessions.
8. **Rollback:** delete the tool + report; nothing else references them.
9. **Dependencies:** owner acknowledgment for Tier-2 data only (Tier-1 can
   proceed without any gate).
10. **Exclusions:** no intraday quote-aging claims (no data), no fill-
    probability model (no sizes outside the parked lane, no fills at all), no
    package-quote modeling (no data anywhere), no change to
    `conservative_bid_ask_plus_haircut_v1` (hash-frozen; changing it
    invalidates comparability and is an owner amendment).

### Phase 3 (optional) — WS-3: deterministic stress scenarios

Goal, interfaces, tests, exclusions as sketched in §5; renders only on the
experiments dashboard; scenario constants standard-from-literature or
official-source with LLM-proposed provenance labels (composite-lane
precedent); acceptance = board-invariance + fixture-pinned scenario math;
rollback = delete lane (isolation tests already enforce the boundary).

---

## 7. Validation Design

- **Baseline comparison:** WS-2's baseline is "no flags" — success is measured
  by detection of injected corruptions and zero baseline byte drift, not by
  any market metric. WS-1's baseline is the frozen cost model itself; the
  study's output is a calibration *comparison*, not a performance claim.
- **Primary metrics:** WS-2 — flag precision on synthetic corruptions (target:
  flags every injected case; false-positive review on the real capture
  history is a report section, not a threshold). WS-1 — observed half-spread
  percentile of the current adverse assumption per bucket.
- **Guardrail metrics:** baseline byte identity; suite exit code; zero new
  network imports; zero new ledger writes.
- **Walk-forward structure:** not applicable to either workstream (neither
  fits a predictive model). Anything later promoted from WS-3 into a signal
  would need its own registration through the 2026-07-24 feasibility gate.
- **OOS protections:** neither workstream reads past `IN_SAMPLE_END` in any
  verdict-bearing path; both are descriptive over cached bytes; the reveal
  budget (0/3) is untouched. WS-1 explicitly excludes any re-scoring of
  registered results under an alternative haircut (that would be a silent
  reinterpretation of frozen runs).
- **Multiple-testing controls:** WS-1 reports distributions, not hypothesis
  tests; if any p-values are ever added they go through the robustness
  harness's required Holm field. WS-2 thresholds are QA tolerances, not
  significance claims.
- **Regime checks:** WS-1 report slices by DTE/moneyness/symbol only —
  pre-declared, closed list, to avoid slice-shopping.
- **Cost stress / tail-risk tests:** already present in the robustness
  harness (`_COST_SENSITIVITY_MULTIPLIERS`, bid-ask stress arm); WS-3, if
  built, adds deterministic tail scenarios for *positions*, labeled
  hypothetical.
- **Minimum worthwhile improvement (tied to repo evidence, not arbitrary):**
  *(Corrected 2026-08-24 after adversarial review: the original criterion —
  "assumption below the ~50th percentile of observed adversity" — was
  arithmetically unreachable, because the model already charges each
  contract's own half-spread, making the comparison circular. Superseded by
  brief 23's criterion; wording re-corrected after review round 2 — R2:
  "adverse" was wrong, ~45% of measured drift is favorable; R4: seq-21's
  tolerance governs future Strategy A put-credit-spread backtests only, so
  any comparison is a labeled analogue on constructed two-leg spreads; R5:
  "worthwhile if it reports" was unfalsifiable.)* WS-1 is worthwhile with a
  finding either way: if, in ≥1 pooled bucket meeting the observation floor,
  the median absolute overnight (D→D+1) mid drift differs from the haircut
  by more than 2×, the haircut's magnitude is out of scale with overnight
  quote movement (input to a possible owner amendment); if every qualifying
  bucket sits within 2×, the constant is the right order of magnitude and no
  follow-up is warranted — a null result recorded as such. Drift is an
  independent, non-circular quantity tied to the registered D+1 execution
  convention and the standing P0.3 obligation to report cancellation/resize
  sample effects; WS-2 is
  worthwhile on its first true catch, and its cost floor is one small pure
  module — justified by the measured stakes (permanent, unrecoverable capture
  holes already exist: 07-28→08-04, 08-15/08-18, 08-21).

---

## 8. Data Feasibility

| Proposal | Required data | Coverage on disk | Missing fields | Timestamp quality | Licensing | Retail-feasible | Effect of missing data | Safe fallback |
|---|---|---|---|---|---|---|---|---|
| WS-1 Tier-1 | Preclose chain bid/ask on admitted contracts | `.cache/schwab_chains/`: 15 names × 3 sessions (08-14/19/20), growing daily; per-contract `timestamp` + `trade_timestamp` | `bid_size`/`ask_size`, volume, last | Good (real receipt timestamps) | Schwab read-only lane, already authorized | Yes | Thin sample → report widths honestly, no conclusions until N is stated | Report refuses buckets below a pre-declared min-obs |
| WS-1 Tier-2 | Quote sizes | `.cache/chains_v2/od1-2026-08-01/`: 18 symbols, 2025-07-25→2026-07-31, `bid_size/ask_size/bid_condition/ask_condition` | None for this purpose | EOD-pull with embedded timestamps | ThetaData bytes, owner-approved capture, **parked/display-only scope** | Yes | Without owner OK: Tier-1 only | Fail-closed flag gate; quarantined sessions excluded always |
| WS-2 | Consecutive chains + closes | Legacy cache (2018→2026-07-27), Schwab lane (08-14→), `.cache/underlying/` closes through 08-21 | None | EOD/preclose, adequate | Existing cached bytes | Yes | Known permanent holes become explicit `GAP_SESSION` flags instead of silent absences | Flags-only; nothing gates |
| A-full items | Continuous intraday quotes, package quotes, broker fills | **Absent** (911 sparse display snapshots only; no combo quotes; no fills by guardrail design) | Everything | n/a | New acquisition disabled (OD-4; ThetaData exit) | No | Cannot be built honestly | BLOCKED BY DATA — do not simulate around it |
| B | Forward ex-dividend calendar, dividend history | **Absent** (15-row forward annual amounts only) | Ex-div dates, per-cycle history | n/a | Would need sourcing decision | Possible later | Flag stays `DATA_BLOCKED` (already does, honestly) | Existing stub already fails closed |

---

## 9. Architecture Boundaries

Both workstreams follow the repo's existing modular-monolith seams:

- **Domain calculation** stays in pure, deterministic functions
  (`data/chain_consistency.py` proposed; WS-1 math in a `tools/` CLI) with no
  I/O in the math itself — mirroring `chain_policy.py` / `oi_change.py`.
- **Providers:** untouched. No new provider, no network in any new path
  (OD-4). WS-1/WS-2 read cached parquet + closes only.
- **Persistence:** WS-1 writes a dated report + receipt under `reports/`
  (the `research/receipts.py` pattern); WS-2 writes flags into existing audit/
  digest surfaces; **neither writes ledger, facts, positions, config, or any
  `.cache` byte**.
- **Orchestration:** WS-2 attaches to the existing capture/audit flow the way
  `attach_oi_change` attaches post-ranking; no new scheduled job is required
  (the daily ritual + job-health digest already run).
- **Interfaces/dashboards:** anything rendered goes to the experiments
  dashboard or audit/digest text surfaces, never the frozen production board;
  the AST-walk isolation tests are the enforcement mechanism and stay
  authoritative.
- **equity-research boundary:** untouched; neither workstream reads the
  bridge.

---

## 10. Risks and Stop Conditions

1. **False confidence:** WS-1's biggest risk is its report being read as "our
   costs are validated." Mitigation: mandatory vocabulary discipline in the
   report ("consistent with / more generous than observed", never
   "proven/correct"), and an explicit statement that preclose spreads are not
   fill evidence.
2. **Leakage:** WS-1 must never re-score any registered run under an
   alternative haircut (reinterpretation of frozen results). Stop condition:
   any diff touching `metrics.py`, `strategies/`, or ledger surfaces.
3. **Overfitting:** WS-2 thresholds tuned until historical captures are all
   clean would blind the flags. Mitigation: thresholds frozen from first
   principles/literature with provenance labels, then judged on injected
   corruptions, not on achieving zero historical flags.
4. **Execution-model risk:** unchanged by design — the frozen
   `conservative_bid_ask_plus_haircut_v1` is not modified anywhere in this
   plan.
5. **Data-quality risk:** chains_v2 carries 10,391 warnings + 3 quarantined
   sessions; WS-1 Tier-2 must consume the quarantine file and the audit
   warning profile, not just the parquet bytes.
6. **Maintenance risk:** two small pure modules + one CLI; the main ongoing
   cost is WS-2 threshold review. If flags become noise that nobody reads,
   that is the removal criterion — remove rather than tune-to-silence.
7. **Park/reject triggers:** park WS-1 Tier-2 permanently if the owner
   declines parked-lane access; park WS-2 if the Schwab lane itself is
   retired; reject WS-3 if Phase 1–2 reviews surface residual work — it is
   strictly the lowest priority.

Explicit confirmations required by the handoff's quality-control list: no
proposal here weakens fail-closed behavior (both add refusals/flags, none
remove any); none changes rankings, verdicts, sizing, risk caps, or live
behavior (isolation tests are the proof mechanism); none consumes locked OOS
data (reveal budget stays 0/3); each workstream is small enough for its own
reviewable brief.

---

## 11. Recommended Implementation Order

1. **WS-2 first.** Zero decision dependencies, zero new data, and it protects
   a dataset that is accumulating value every trading day — every session
   that passes without it is a session whose capture quality was never
   cross-checked. It also exercises the exact audit-stack seams WS-1 reads.
2. **WS-1 Tier-1 second.** Independent of WS-2 but benefits from it: a
   calibration study over captures is only as good as the captures, so the
   consistency flags land first. Tier-1 needs no owner gate.
3. **WS-1 Tier-2 third, owner-gated.** The one owner question this plan
   raises: *may the parked chains_v2 bytes be read, read-only, for a
   descriptive calibration report?* If no, Tier-1 stands alone.
4. **WS-3 last, optional.** Pure add-on; nothing depends on it.

---

## 12. Final Decision Table

| Candidate | Decision | One-line reason |
|---|---|---|
| A — Execution realism (narrow: haircut calibration + participation-vs-OI flag) | **PROCEED TO DESIGN** | Only uncalibrated constant in the frozen cost model; existing data suffices for a descriptive study |
| A — Execution realism (quote aging, package quotes, fill probability, broker calibration) | **BLOCKED BY DATA** | No continuous intraday quotes, no combo quotes, no fills; acquisition permanently disabled |
| B — Early-assignment scenarios | **PARK** | Measured current exposure is zero (all positions ever opened are long-only); ex-div calendar absent; limitation already disclosed everywhere; revisit at H7 lane-B/C or covered-call activation |
| C — Marginal-value experiment gate | **REJECT** | Duplicates ledger pre-registration + feasibility gate + `ExperimentSpec` + experiment-program constraints; fold the 3 missing cost fields into the existing spec template as a docs-only tweak |
| D — Simple surface features | **RESEARCH ONLY** (no-arb/curvature QA checks folded into WS-2) / **REJECT** for new signal features and any rough-Heston/neural work | Listed features largely already exist display-only; new ones have no consumer |
| E — Era/regime stability slices | **PARK** | No lane has a sliceable sample; Wasserstein lane + `regime_concentration` already cover the descriptive need; revisit when any lane reaches its loss bar |
| F — Delta/quote-velocity anomaly flags | **PROCEED TO DESIGN** (cross-session subset; shadow-mode only) | Protects the irreplaceable forward capture stream; within-session checks already strong, day-over-day checks absent |
| G — Feature grouping and ablation | **REJECT** | No predictive model exists to ablate; complexity without a customer |
| H — Deterministic stress tests | **RESEARCH ONLY** | Cheap and honest, but low urgency with a one-position book; optional Phase 3 |
| I — External framework lessons | **PARK** (static pricing/Greeks golden fixtures, only if a defect ever motivates them) / **REJECT** (any migration or runtime dependency) | IV solver already calibrated against provider output; repo rule forbids engine-building |

---

*Prepared 2026-08-24 from five independent read-only audits at HEAD `24368f6`.
Not committed. Awaiting owner review before any implementation brief is
drafted.*

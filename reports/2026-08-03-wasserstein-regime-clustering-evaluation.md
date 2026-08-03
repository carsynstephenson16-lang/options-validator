# Wasserstein market-regime clustering — integration evaluation

**Date:** 2026-08-03
**Requested by:** owner ("integrate `mehul532/wasserstein-market-regime-clustering`
into the project to help grasp current market levels and even predictive points")
**Evaluator:** Claude orchestrator session; repository analysis delegated to a
Sonnet scout subagent and independently spot-verified against the source.
**Verdict:** **PARK — do not integrate now.** Entry appended to
`ideas-parking-lot.md` ("Wasserstein regime clustering (parked 2026-08-03)").

This is an opportunity-triage + scope-guard evaluation, not a hypothesis result.
No code from the external repository was added to this project. No provider
call, ledger append, cache mutation, or book change occurred.

## 1. What the external repository actually is

All claims in this section are **Repo-verified** against a read-only clone of
`github.com/mehul532/wasserstein-market-regime-clustering` (MIT license,
1,111 lines in `src/regime_ot`, 16 offline tests).

- **Method:** rolling 63-day windows of daily log returns on a single ticker
  (default SPY) are treated as empirical 1-D distributions; pairwise 1-D
  Wasserstein distances (hand-rolled sort-and-compare, valid only in the 1-D
  special case); custom Lloyd's k-means with quantile-mean barycenters;
  default 3 regimes. Baselines: moment-feature KMeans/GMM.
- **Data source:** `yfinance` only (`src/regime_ot/data.py` raises on any other
  source). No bundled data. Fetches from the network at runtime unless a local
  cache file already exists.
- **Primary output path is in-sample:** `cli.py` and both experiment scripts
  call `WassersteinKMeans.fit(windows)` once on the full sample. The README
  states this itself: "the labels themselves are still in-sample diagnostics."
- **Predictive claims: none.** README line 171: "The backtest is illustrative,
  not predictive. Regime labels are unsupervised and do not guarantee future
  returns." The stated goal of the integration request ("predictive points")
  is a claim the repository's own author explicitly disclaims.
- **One genuinely careful piece:** `backtest.py:
  walk_forward_regime_strategy_backtest` refits only on windows ending at or
  before the decision date and shifts positions by one period
  (`shift(1)`, line 122/187), so the *signal timing* is causal. Label
  identity across refits is not aligned; instead the "high-risk" regime is
  re-selected each refit as the highest-dispersion centroid, which sidesteps
  (rather than solves) label-switching. Windows still overlap by construction.
- **Maturity:** research/portfolio demo, not a production library (no CI, no
  packaging polish; author's own framing).

## 2. Why it is parked, not integrated

Five independent gates fail. Any one would be sufficient.

1. **Scope guard (.cursorrules).** "Does this move one of the live hypotheses
   (H5/H6/H7/H8) toward its declared verdict?" No. All four have frozen,
   registered rules; a regime overlay cannot change a registered trigger or
   verdict without a prospective amendment. This is a new capability, and the
   scope guard's instruction for that case is: park it.
2. **Standing pre-verdict rule (opportunity triage).** options-validator is
   itself pre-verdict — PROJECT_STATE.md 2026-08-02: "No strategy has
   demonstrated an advantage." The standing rule is no new build lands while
   the current project is pre-verdict. This request rhymes with the Kalshi
   pattern (infrastructure accreting before any verdict exists); naming that
   is the point of the gate.
3. **Provider policy.** The repo's sole data path is yfinance — a new,
   unapproved network provider. Acquisition is disabled (OD-4, 2026-07-31);
   live selection is explicitly Schwab-or-error; tests must run offline. An
   offline variant on cached closes is *feasible*, but that means reimplementing
   the data layer, i.e., a build, which gate 2 blocks.
4. **The 2026-07-22 HMM rejection is mostly unanswered.** HMM regime detection
   was rejected (not parked) for: (a) redundancy with `rv_percentile` + SMA
   posture, (b) instability on short-history names, (c) label-switching across
   refits. Wasserstein k-means partially answers (c) (dispersion-based regime
   re-selection) and is agnostic on (b) (single long-history index input),
   but (a) — redundancy — is untouched: 3 coarse volatility regimes on SPY
   plausibly encode little beyond the existing realized-vol percentile.
   **Inference**, falsifiable by the pre-specified test below.
5. **The stated benefit is disclaimed by the source.** "Predictive points" is
   exactly what the README warns it does not provide. Integrating it under
   that motivation would import a claim the evidence does not support
   (vocabulary discipline: at best "not yet rejected" — and nothing has been
   tested yet).

## 3. Pre-specified un-park test (so this is never re-litigated from scratch)

Smallest falsifying test, designed now, runnable offline in under a day at $0,
**only after** a live-hypothesis verdict lands or the owner explicitly
overrides the standing rule:

- **Question:** do Wasserstein regime labels carry information beyond the
  existing `rv_percentile` + SMA-posture features?
- **Data:** cached underlying closes only (frozen v1 cache, ≤ 2026-07-27 edge);
  SPY plus the four core names. No network, no new provider.
- **Procedure:** compute walk-forward labels (the repo's causal path,
  reimplemented minimally in-house per "no external strategy code" hygiene);
  compute adjusted mutual information between labels and a binned
  `rv_percentile` × SMA-posture grid over the same dates.
- **Pass/fail:** owner types the frozen AMI redundancy threshold and window
  set BEFORE the run (feasibility-gate discipline; numbers left blank here
  deliberately). High agreement ⇒ redundant ⇒ convert PARK to the same
  rejected status as HMM. Low agreement ⇒ a one-page owner-nod spec for a
  display-only descriptive badge MAY be drafted — never a ranking, never
  verdict-bearing, per the rejected-composite precedent.
- Regime-conditional GREEN/AMBER thresholds remain "far future" and are NOT
  unlocked by this test (they need pre-typed per-regime numbers).

## 4. Claim labels

- Repo-verified: §1 entirely; graveyard/rejection wording (survey §6,
  `ideas-parking-lot.md`); PROJECT_STATE.md status quotes.
- Inference: gate 4(a) redundancy expectation; the <1-day cost estimate.
- Assumption: cached underlying closes cover SPY densely enough for the test
  window (SPY chain files end 2026-06-30; to be inventoried before the test
  is registered).

## Addendum — owner override and authorized build (2026-08-03, same day)

After reading this evaluation, the owner explicitly overrode the standing
pre-verdict rule and amended the scope guard (owner wording: "I want to amend
my own scope rules and unfreeze that. Continue with implementing this into
the code base"). The exception is recorded in `.cursorrules` and `AGENTS.md`
(kept in sync) and the parking-lot entry is marked UN-PARKED.

Scope of the authorized build — narrower than the original request:

- **Offline only.** Data via `data/underlying_closes.py` (split-adjusted
  cached closes, `allow_oos=True` disclosed post-2022 researcher look).
  yfinance and all network providers stay excluded; OD-4 stands. Gate 3 of
  §2 is therefore satisfied by reimplementation, not waived.
- **Walk-forward causal labeling only.** The upstream in-sample fit path is
  not ported; gate 5's look-ahead concern is closed by construction. The
  upstream backtest/equity-curve code is not ported at all (a backtest would
  require its own pre-registration).
- **Display-only, non-verdict-bearing.** Regime labels are unsupervised
  historical descriptions; transition tables are historical frequencies, not
  forecasts. Nothing in this lane can FIRE, gate, or adjudicate.
- **Gate 4 (redundancy vs `rv_percentile` + SMA posture) remains OPEN.** The
  landed module makes the pre-specified AMI test cheap to run; the owner
  still types the frozen threshold before that test, and a redundant result
  demotes this lane to rejected alongside HMM.

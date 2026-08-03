# REGIME-AMI-v1 — pre-registered redundancy test for the Wasserstein regime lane

**Date registered:** 2026-08-03 (before any result exists; parameters frozen below)
**Authorization:** owner wording, same day: "Go register and run it" — following the
owner-directed scope exception of 2026-08-03 (`.cursorrules` "Scope guard") and the
open gate 4 of `reports/2026-08-03-wasserstein-regime-clustering-evaluation.md` §2/§3.
**Threshold provenance:** the 0.50 decision threshold below is **LLM-proposed,
owner-directed 2026-08-03** (precedent: the IV_CALIBRATION constants,
"LLM-proposed, owner-delegated 2026-07-24"). The owner retains veto: a veto typed
before the run voids this registration; after the run, the recorded result stands
and any change is a new version (REGIME-AMI-v2).
**Ledger:** appended as a `trial_intent` with `hypothesis_id=REGIME-AMI-v1` via
`research.experiments.log_trial_intent` (typed API; seq 21/22 precedent).

## Question (falsifiable, from the 2026-07-22 HMM rejection)

Do walk-forward Wasserstein regime labels carry information beyond the repo's
existing regime read — `rv_percentile` + `ma_posture` — on the four core names?
The HMM regime badge was rejected 2026-07-22 partly for exactly this redundancy;
this lane inherits that objection until tested. This is a descriptive audit of a
display-only lane, not a trade hypothesis: no entry rule, no P&L, no verdict on
any registered H-hypothesis.

## Frozen design (run once, record whatever it shows)

- **Universe:** VST, CEG, MSFT, AMZN (`config.REGIME_SYMBOLS`, frozen at the four
  core names for this test even if that constant later changes).
- **Data:** `data.underlying_closes.load_closes_adjusted(symbol, "2018-01-01",
  <cache edge>, allow_oos=True)` — cached, split-adjusted closes only. No network,
  no provider call, no chain data. The disclosed post-2022 researcher look applies.
- **Regime labels:** `options_researcher.regime.walk_forward_labels` with the
  landed config constants exactly: window 63, step 5, clusters 3, refit_every 20,
  min_fit_windows 24, n_init 5, seed 7, p=1. Unlabeled (NA) steps are excluded.
- **Comparison features, computed at each labeled end date t from `closes.loc[:t]`
  only (same causality rule as the labels):**
  - `rv20_pctile(t)`: `options_researcher.h7_signals.rv_percentile` at its
    registered defaults (20d rolling RV vs own trailing 252-session history,
    minimum 106 RV observations; the function's short-history sentinel value 1.0
    is treated as a VALID feature value, not dropped).
  - `posture(t)`: the `ma_posture` field of
    `options_researcher.technicals` computed on `closes.loc[:t]` — one of
    above_all / below_all / mixed vs SMA(20, 50, 200). Steps where posture is
    `insufficient_history` are excluded from the comparison.
  - **Feature grid cell:** (rv tercile, posture), where rv terciles are the FIXED
    bins [0, 1/3), [1/3, 2/3), [2/3, 1.0] — not data-fitted quantiles. Grid has at
    most 9 cells.
- **Metric:** Adjusted Mutual Information (AMI) between the regime-label series
  and the grid-cell series over the included steps, per symbol. AMI uses the
  exact hypergeometric expected-MI correction and arithmetic-mean normalization
  ((H(U)+H(V))/2), implemented in numpy (no new dependencies). AMI ≈ 0 means
  agreement at chance level; 1 means identical partitions.
- **Eligibility:** a symbol counts only if it contributes ≥ 100 included steps.
- **Decision rule (frozen before any result):**
  - **REDUNDANT** — median per-symbol AMI across eligible symbols ≥ **0.50** →
    the Wasserstein regime lane is demoted to REJECTED alongside the HMM badge
    (parking-lot reclassification; the code may stay but the report is retired
    from routine use).
  - **RETAINS_DISTINCT_INFORMATION** — median < 0.50 → the lane remains exactly
    what it is today: display-only, non-verdict-bearing. This outcome does NOT
    upgrade the lane, imply usefulness, or unlock regime-conditional thresholds
    (still "far future" and separately gated).
  - **INSUFFICIENT_DATA** — fewer than 2 eligible symbols → no decision; recorded
    as such; any rerun with relaxed eligibility is REGIME-AMI-v2.
- **Runner:** `uv run python -m tools.regime_redundancy_audit` — refuses to run
  unless this registration's ledger entry exists; writes a receipt
  (JSON + markdown) under `reports/regime/` with code SHA, per-symbol AMI, step
  counts, cache as-of edge per symbol, and the triggered decision.
- **Outcome recording:** the operator commits the receipt and appends
  `trial_intent` "REGIME-AMI-v1-RESULT: <REDUNDANT|RETAINS_DISTINCT_INFORMATION|
  INSUFFICIENT_DATA> (median AMI <x.xxx>)" via the typed API. One run; a second
  run is only valid as a registered v2.

## Why 0.50 (stated before the run)

AMI is chance-corrected: 0 is the expected agreement of unrelated labelings, 1 is
identity. 0.50 — halfway to identity after chance correction — is proposed as
"substantially the same read": above it, most of what the regime labels say about
a date is already said by the rv-tercile × posture grid, and the rejected-HMM
redundancy objection stands. Below it, the labels are demonstrably not a
re-encoding of the existing badges (which still says nothing about usefulness).

## What this test cannot show (pre-committed interpretation limits)

- It cannot show the regime labels are USEFUL — only whether they are distinct.
- It says nothing about forecasting; transition tables remain historical
  frequencies whatever the outcome.
- A RETAINS_DISTINCT_INFORMATION result is "not yet rejected on redundancy",
  nothing more.

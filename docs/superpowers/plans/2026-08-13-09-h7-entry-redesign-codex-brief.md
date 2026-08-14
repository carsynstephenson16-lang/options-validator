# Codex brief 09 — H7 entry-rule redesign (owner-directed 2026-08-13)

**Date:** 2026-08-13
**Author:** Claude (orchestrating session)
**Executor:** Codex (Sol, high reasoning)
**Owner decision recorded:** Carsyn chose **redesign** over starvation
pre-acceptance for the H7 Schwab restart (in-session, 2026-08-13). The
measured problem: the current full entry stack fires ~4 times per 70-session
window (bound receipt 4/1050, exact 95% CI [1.09, 10.21] expected entries),
vs the 2026-07-24 feasibility gate's bar of >= 2x the loss requirement
(2 x 10 losses = 20 expected entries). Roughly a 5x shortfall.

## Goal

Produce a MEASURED MENU of candidate entry-rule variants whose historical
firing frequency clears the feasibility bar, so the owner can pick one and
type its frozen numbers at registration. This brief produces NO registration,
NO frozen numbers, and NO performance claims — frequency only.

## The one hard integrity rule

**Measure entry FREQUENCY only. Never compute, store, or report P&L, win
rate, premium capture, or any outcome statistic for any variant.** The
moment a variant's historical profitability is observed, choosing it becomes
result-selection and the pre-registration is theater. The deliverable tables
contain: variant definition, entries per 70 sessions, exact binomial CI,
per-name distribution, clustering diagnostics — nothing about outcomes.
(Anti-p-hacking design: selection on trigger frequency, blind to returns,
preserves the validity of the later forward test — this is the standard
protection against selection-induced overfitting; see also the repo's
2026-07-24 feasibility-gate doc.)

## Candidate axes (measure each independently, then sensible combinations)

1. **Signal thresholds:** relax each gate in the current stack one at a time
   (IV-rank bound, price-trigger distance, liquidity minima that are
   fail-closed rather than economic) and measure marginal frequency gain.
   Liquidity/spread caps protecting fill realism MUST NOT be relaxed —
   they are cost-model integrity, not signal.
2. **Universe:** current 15-name cohort vs the wider owner-authorized
   watchlist names that pass source-health; report per-name contribution so
   concentration is visible.
3. **Trigger logic:** AND→OR restructuring of independent conditions where
   the hypothesis rationale still holds (document the rationale change each
   variant implies — a variant that fires often but no longer tests the
   original idea is a DIFFERENT hypothesis and must say so).
4. **Evaluation cadence:** entries evaluated on more than one setup shape per
   session (e.g., both spread lanes) if and only if the registered risk cap
   still binds.

## Method requirements

- Data: cached ThetaData EOD chains + `data/underlying_closes.py` ONLY
  (OD-4 stands; no provider calls). Same 1,050 stock-day panel convention as
  the 2026-08-11 receipt so numbers are comparable, PLUS a longer lookback
  panel (all cached history per name) reported separately — 70 sessions is a
  small sample for rare triggers.
- Causal evaluation: at each historical decision timestamp use only data at
  or before it (no look-ahead), identical to watcher semantics.
- Uncertainty: exact Clopper-Pearson 95% CI on every count, converted to
  expected entries per 70-session window. A variant "clears the bar" only if
  the CI LOWER bound >= 20; report near-misses separately.
- Clustering caveat (required in the report): entry events cluster in
  vol regimes; an unconditional binomial CI understates window-to-window
  variance. Report a per-window (rolling 70-session) min/median/max entry
  count alongside the CI.
- B4-style disclosure travels with every number: measured on ThetaData EOD,
  the future window runs on Schwab 15:45 pre-close; known simplifications
  inflate counts.

## Deliverable

`reports/h7_forward_schwab/2026-08-XX-entry-redesign-menu.md` + a receipt
JSON per variant (config-hash-bound, same schema as the 2026-08-11
feasibility receipt). The report ends with a decision table for the owner:
variant, rationale drift (none/low/high), expected entries (CI), per-name
concentration, rolling-window spread. The owner picks; frozen numbers are
typed by the owner at registration; the registration itself passes the
2026-07-24 gate with the chosen variant's receipt.

## Explicitly forbidden

Computing outcomes/P&L for variants; registering anything; touching the
paused `h7-forward-15-v1` namespace; relaxing liquidity/cost realism gates;
provider calls; hand-edited receipts. Tests for any new measurement tool run
offline on fixtures.

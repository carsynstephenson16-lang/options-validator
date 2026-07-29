# Options-Flow Intelligence Implementation Audit

## Scope

Audit of the offline implementation for point-in-time feature construction,
event/IV context, covariance-aware analog matching, calibrated historical
opinions, and display-only authority isolation.

No paid ThetaData history was fetched. No backtest or trading simulation was
run. This report therefore audits implementation behavior, not market edge.

## Data-quality audit

**Data audited:** normalized MSFT fixture, 2025-01-02, 4 trade rows.

**Result:** `PASS`.

The executable audit printed all required sections and found no failure in the
synthetic fixture. This does not transfer to uncaptured ThetaData history.
Historical data remains `NOT AUDITED`, and all empirical opinions remain on
hold until the bounded acquisition is separately authorized and audited.

## Implementation findings

The first review found and repaired four material defects:

1. ISO auction and cross conditions were incorrectly falling into the sweep
   class. Only the actual intermarket-sweep condition is now a sweep.
2. Volume/OI was summing the same contract's OI once per trade. OI is now
   deduplicated by contract before aggregation.
3. Historical event knowledge used an end-of-day cutoff. It now uses the
   declared 16:00 ET session cutoff and excludes later publications.
4. The former walk-forward design matrix omitted the named baseline regressor.
   Baseline and expanded models now contain the baseline and shared context on
   identical complete cases.

The follow-up audit found no import from flow modules into ranking, scoring,
broker, or order-routing code.

## Results red-team

**Verdict:** NEEDS REPAIR before any empirical conclusion; offline
implementation is suitable for a bounded data pilot.

**Top three remaining threats:**

1. No real historical trade/quote, IV, or event-calendar panel has passed the
   audit. Synthetic correctness cannot establish provider completeness.
2. Exact event and IV regime gates plus `max(126, 8p)` covariance history may
   starve CEG/VST same-ticker analogs. The engine correctly abstains, but useful
   sample size is unproven.
3. MSFT/CEG/VST were purposefully selected and are not a survivorship-neutral
   universe. Pooled results cannot be generalized beyond them.

**Kill test:** Run the preregistered, audited panel through the untouched
42-session holdout. Reject incremental value if the expanded context-plus-flow
model does not improve the context-only baseline after multiplicity correction
and dependence-aware uncertainty.

**What would change the verdict:** A rights-verified pilot and full data audit,
adequate effective sample size after all gates, stable Mahalanobis/RMS neighbors,
and incremental holdout performance that survives the registered controls.

## Verification

- Final focused options-flow suite after all changes: 31 tests passed.
- Full repository suite before the isolated offline CLI addition: 2,085 tests passed.
- Scoped Ruff: passed.
- Scoped Pyright: 0 errors.
- `git diff --check`: passed.
- Live requests: none.
- Hypothesis or execution authority changes: none.

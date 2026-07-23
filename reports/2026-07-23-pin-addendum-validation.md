# Pin-addendum validation — RQ2_A2_PIN_ADDENDUM_V1 (2026-07-23)

Analyst pass on the four §13.1b pin values, performed BEFORE the addendum fact
was appended and before any RQ2/A2 result exists. Owner directed the entry in
session; values were LLM-proposed in the 2026-07-23 decision package and
restated by the owner. Claim labels per repo discipline.

## (i) Fixed-horizon CSP arm = 10 trading sessions

- Distinctness (Repo-verified vs seq 19): the other four arms are
  payoff-triggered (50% capture), expiry-clock (21 DTE), event-triggered
  (breach-defensive), and hold-to-expiry. A 10-session clock from entry is the
  only pure time-from-entry arm, so the five arms measure different things.
- Magnitude (Inference): 10 sessions ≈ 2 calendar weeks, mid-range for the
  15–45 DTE entry band — long enough to observe theta capture, short enough to
  stay clearly distinct from the 21-DTE and expiry arms.
- Edge case pinned (Inference): entries whose expiration arrives before
  session 10 resolve at expiration settlement; without this clause the arm is
  undefined for short-DTE entries.

## (ii) Bucket split = terciles (top third vs bottom third)

- Consistency (Repo-verified): the registered program doc already assumes
  terciles in two places ("tercile top-vs-bottom spread (primary)", "first
  quarterly tercile read ~Oct 2026"); any other split would contradict the
  registered program frame.
- Sample logic (Inference): 15-name board → 5 names per bucket. Halves (7/7)
  blur best and worst together; quartiles (3–4) leave per-bucket means too
  noisy and slow the adverse-gate accrual (MIN_ADVERSE_BOTTOM_BUCKET=10).
  Terciles are the standard small-cross-section choice in portfolio-sort
  research.

## (iii) Holm sidedness = one-sided, hypothesized direction

- Coherence (Repo-verified vs seq 18/19): promotion already requires the
  Holm-adjusted CI90 LOWER bound > 0 — a directional rule. A two-sided
  convention would mismatch the decision rule and waste power. The registered
  rejection rule (upper bound ≤ 0) is untouched.
- Integrity (Inference): declaring sidedness pre-data removes a classic
  forking path — choosing the convention after seeing results.

## (iv) Badge B event window = report strictly inside near-leg life

- Causal logic (Inference): the corner badge measures near-month event
  inflation (near IV rich vs long IV). Only an earnings print the near option
  itself spans can cause that inflation; a report after near expiry loads the
  long leg instead and would invert the slope.
- Boundary (Inference, conservative): a report dated ON expiration day may
  occur after the close (unspanned), so strict inequality excludes it.
- Literature (Inference from published research, not fetched this session):
  event-driven IV term-structure inversion ahead of earnings is a documented
  phenomenon (e.g., Dubinsky & Johannes-type earnings/IV decompositions).

## Multiple-testing note

This addendum completes unfrozen registration fields pre-data. It is NOT a
new hypothesis version: RQ2-v1 and A2-v1 remain v1; the multiple-testing
denominator K is unchanged.

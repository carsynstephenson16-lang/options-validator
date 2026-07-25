# Registration feasibility gate — process rule (owner-approved 2026-07-24)

**Status:** ACTIVE process rule for all FUTURE hypothesis registrations.
It does not amend, re-open, or re-score any already-registered hypothesis
(H5/H6/H7/H8/H10 run exactly as registered).

## The problem this fixes

Two registered hypotheses have now hit, or are projected to hit, the same
failure mode:

- **H9** (trial 15): the one authorized run ended INSUFFICIENT_SAMPLE —
  4 losses against a 10-loss verdict bar. The run was spent; no verdict.
- **H7 forward window** (seq-0, 2026-07-20 → 2026-07-26): a 2026-07-24
  read-only base-rate diagnostic measured the full lane entry stack passing
  on 3 of 540 symbol-days across the 9-name registered cohort over the prior
  60 sessions — extrapolating to roughly 3–5 candidate entries in the whole
  70-session window against a 10-loss verdict bar. (Estimate, LLM-computed
  from the cached feature/close history; scratch script recorded in the
  2026-07-24 session, not a registered result. The window runs to completion
  regardless — this doc changes nothing about it.)

In both cases the entry gates and the verdict bar were each individually
reasonable, but nobody checked whether the two were *jointly reachable*
before freezing. The result is the worst outcome the ledger can produce: a
window that costs months and answers nothing — not "no edge," just no answer.

**Contrast (the correct precedent): H10a/H10b** disclosed their low fire
rate at registration verbatim ("11 historical fires; may stay
INSUFFICIENT_SAMPLE") and lowered their loss bar to 7 as a mitigation. That
is what informed consent to sparsity looks like; this gate makes it
mandatory rather than optional.

## The rule

Before ANY new hypothesis (or new forward window of an existing hypothesis)
is registered with a loss-gated verdict:

1. **Compute the base rate.** Evaluate the complete entry stack — signal
   arming, earnings/eligibility gates, liquidity admission, routing, caps —
   over a lookback of comparable length to the proposed window, on the
   proposed universe, using only data available in the repo's caches. Record
   the count: full-stack passes per symbol-day.
2. **Project the sample.** expected_entries = base_rate × window_sessions ×
   universe_size. State it in the registration.
3. **Pass condition:** expected_entries ≥ **2×** the verdict's loss bar
   (`MIN_LOSSES_FOR_VERDICT` or the hypothesis's own declared bar). The 2×
   margin exists because losses are a subset of trades: a 50% loss rate is
   already an aggressive assumption for a strategy anyone bothered to
   register.
4. **Fail path:** the registration is REFUSED as written. The proposer
   either (a) redesigns (wider arming, longer window, smaller loss bar —
   all owner-typed, all BEFORE registration, which is exactly when such
   tuning is legitimate), or (b) registers anyway with an explicit
   **starvation-risk pre-acceptance clause** in the registration text,
   quoting the computed base rate and expected-entry count (the H10
   precedent). Silence is not an option; the number must appear either way.
5. **Provenance discipline:** the base-rate computation is LLM-assisted
   analysis, labeled as such in the registration; the thresholds (2×
   margin, any redesigned parameters) are owner-typed per the standing
   rule that Claude proposes and the owner enters frozen numbers.

## What this gate is NOT

- Not a backdoor for tuning live hypotheses — it applies at registration
  time only, before any result exists.
- Not a promise of statistical power — reaching the loss bar does not make
  a verdict significant; it makes a verdict *possible*. Power analysis
  remains a separate concern.
- Not a data-mining license — the base-rate check measures how often the
  *already-designed* stack fires; it is not a search over designs. Running
  the check on many candidate designs and picking the best is exactly the
  overfitting this repo exists to prevent, and remains banned.

## Provenance

- Direction approved by owner 2026-07-24 ("let H7 run + add feasibility
  gate") in response to the 0-picks diagnostic.
- Companion guardrail lines added to `.cursorrules`, `CLAUDE.md`, and
  `AGENTS.md` in the same commit as this doc (kept in sync per the standing
  guardrail-drift rule).

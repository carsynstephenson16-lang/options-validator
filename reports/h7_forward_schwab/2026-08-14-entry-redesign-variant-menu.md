# H7 entry-rule redesign — measured variant menu

**Date:** 2026-08-14
**Brief:** `docs/superpowers/plans/2026-08-13-09-h7-entry-redesign-codex-brief.md`
**Branch / code:** `wt/brief09-variant-menu-0814`, receipts bound to code SHA
recorded in each receipt file
**Receipts:** `reports/h7_forward_schwab/variant-receipts/`
**Status:** measurement only. No registration, no frozen numbers, no verdict.

---

## What this document is, and what it is not

This measures **how often** each candidate entry rule would have fired. That
is all it measures.

It contains **no profit-and-loss figures, no win rates, no returns, and no
outcome statistics of any kind** — not for the current rule and not for any
variant. That is deliberate and it is the point of the exercise. If we looked
at which variant made money historically and then picked that one, the forward
paper window would no longer be a test of anything: we would have chosen the
rule *because* it looked good on the same data we then claim to test it on.
Choosing on firing frequency, blind to results, is what keeps the forward test
meaningful.

Two guards enforce this in the code rather than relying on discipline:

- a variant that tries to loosen fill realism, the liquidity caps, or the
  earnings gate raises an error instead of running;
- every receipt is scanned for outcome-shaped fields before it can be written.

**You decide.** This document ranks nothing and recommends no variant. The
owner picks, and types the frozen numbers at registration.

---

## The short version

**No candidate rule reaches the required firing rate once the position limit
you already registered is applied.**

The bar (2026-07-24 feasibility gate) is **20 expected entries** over the
declared window — twice the 10-loss requirement. The current rule produces
**4**. Of the 18 candidates measured:

- **Loosening thresholds does almost nothing.** Every single-threshold
  relaxation lands between 4 and 5 entries. The most permissive sensible
  combination reaches 6. None is close to 20.
- **Two candidates clear 20 on paper** (104 and 147 entries) — but only
  because the measurement assumes you start every single day with an empty
  book and the full monthly budget. Once you apply the rule you already
  registered — one open position per name — those 104 and 147 collapse to
  **10 and 15**. Neither clears 20.
- Both of those two are also **different hypotheses**. They fire so often
  because they arm on *either* of two conditions instead of *both*, which
  stops testing "a beaten-down name stabilising" and starts testing something
  else.

**Why loosening the trigger cannot work:** the trigger is not the bottleneck.
Over the full cached history the signal arms roughly **62 times per
70-session window**, yet only **4 entries** survive. Around 94% of armed days
are lost afterwards — and the two biggest losses are the **earnings gate** and
the **liquidity check**, both of which the brief correctly forbids relaxing
because they protect data honesty and fill realism, not signal.

There is also an arithmetic ceiling, described in section 5, that puts the
maximum achievable entries in a 70-session window at roughly **25** for all 15
names and roughly **15** for the 9-name registered cohort. The 20-entry bar
sits inside that range, which means the design has to run near its physical
maximum to pass — and the 9-name cohort cannot pass at all on a 70-session
window, whatever the entry rule.

---

## 1. The decision table

Panel: the last 70 sessions where all 15 names have a cached chain
(2026-04-16 → 2026-07-27), 1,050 name-days. Same convention as the
2026-08-11 feasibility receipt, so the numbers are directly comparable.

"Expected entries" projects the measured rate onto a 70-session window.
"95% CI" is an exact Clopper-Pearson interval. Following the brief, a variant
only **clears** the bar if the CI's **lower** bound reaches 20.

"After position limit" replays the very same entries through the registered
one-open-position-per-underlying rule, holding each position ~42 sessions
(enter near 90 days to expiry, time-exit at 30). That is schedule arithmetic
only — no prices and no outcomes are consulted.

| Variant | What changes, in plain English | Drift | Entries | 95% CI | Clears 20? | After position limit | Names firing |
|---|---|---|---|---|---|---|---|
| **V0_BASELINE** | The current registered rule. Nothing changes. | none | 4.00 | [1.09, 10.21] | No | 3 | 3 / 15 |
| V1_DRAWDOWN_15 | Arm after a 15% fall from the 1-year high instead of 25%. | low | 5.00 | [1.63, 11.63] | No | 3 | 3 |
| V2_DRAWDOWN_10 | Arm after a 10% fall instead of 25%. | low | 5.00 | [1.63, 11.63] | No | 3 | 3 |
| V3_RANGE_20 | Accept a 60-day price range up to 20% of price instead of 15%. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V4_RVPCTILE_40 | Accept volatility in the quietest 40% of its own year instead of the quietest 25%. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V5_CLOSE_ROUTE_DEADZONE | Close the pricing dead zone: options priced 1.15–1.25× realised volatility are currently routed nowhere and the day is skipped; route them to the debit spread. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V6_ADMIT_3 | Require 3 liquid near-the-money monthly contracts instead of 5. Per-contract liquidity caps unchanged. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V7_DELTA_TOL_10 | Accept strikes within 0.10 of each target delta instead of 0.07. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V8_RECLAIM_10 | Trigger on a close above the prior 10-day high instead of the prior 20-day high. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| **V9_LANE_A_OR** | Arm on a deep fall **or** a 20-day-high reclaim, instead of requiring both. | **high** | 104.00 | [85.73, 124.67] | Yes* | **10** | 7 |
| V10_LANE_B_OR | Arm on a tight range **or** quiet volatility, instead of both. | **high** | 5.00 | [1.63, 11.63] | No | 4 | 4 |
| V11_LANE_B_NO_EDGE | Let the coil setup fire on any qualifying day, not only the first. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V12_MULTI_LANE | Let one name take more than one setup shape the same day. Budget and short-premium caps still bind. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V13_H7C_CONCURRENT_2 | Allow 2 concurrent short-premium positions instead of 1. | low | 4.00 | [1.09, 10.21] | No | 3 | 3 |
| V14_REGISTERED_COHORT_9 | Same rule, restricted to the 9 names frozen into the registered cohort. | none | 4.00 | [1.09, 10.19] | No | 3 | 3 / 9 |
| V15_COMBO_MILD | 15% fall + closed dead zone + coil may re-fire + more than one shape per name. | low | 5.00 | [1.63, 11.63] | No | 3 | 3 |
| V16_COMBO_MEDIUM | 10% fall + 20% range + quietest 40% + closed dead zone + 3-contract breadth + coil re-fire + multi-shape. | low | 6.00 | [2.20, 13.02] | No | 4 | 4 |
| **V17_COMBO_WIDE** | Everything in V16, plus both setups arming on **either** of their two conditions. | **high** | 147.00 | [125.55, 170.60] | Yes* | **15** | 12 |

\* **The asterisk matters.** V9 and V17 clear the bar only in the unconstrained
count. Under the registered one-position-per-name rule they produce 10 and 15
entries. With a deliberately generous 21-session holding assumption they reach
16 and 24. No interval is quoted on the position-limited figures: that replay
is a deterministic schedule filter, not an independent random draw, so a
binomial interval would not mean anything there.

**Multiple-testing count: 18 variants were measured.** Any registration that
selects one of these must disclose that number — picking the highest of 18 on
frequency is still a search over 18.

---

## 2. Where the entries are actually lost

First blocking condition per name-day-lane, over the same 1,050 name-days
(3,150 lane-days). Receipt:
`variant-receipts/comparable_70_common/_baseline_waterfall.json`.

| First blocker | Lane-days | Can the redesign touch it? |
|---|---|---|
| Earnings gate (unknown date, or inside the pre-report ban) | 1,098 | **No** — fail-closed by design |
| Liquidity admission (not enough qualifying contracts) | 957 | **No** — protects fill realism |
| Lane excluded by design (short premium on the 4 core names) | 280 | No — registered scope |
| Arming rule (the technical trigger) | 806 | **Yes** — this is the signal |
| Pricing route (volatility ratio lands in no route) | 5 | Yes |
| Reached ENTRY-OK | 4 | — |

Read as a funnel: 2,870 lane-days are evaluated (280 are excluded by scope);
the earnings gate removes 1,098; liquidity removes 957 of the survivors; the
technical trigger removes 806 more; 4 remain.

**Caveat on this table.** The frozen code checks these conditions in a fixed
order and stops at the first failure, so a day counted against the earnings
gate might also have failed liquidity. These are first-blocker counts, not
independent attributions. The ordering nevertheless makes the conclusion
robust: the two gates checked *first* and *second* are precisely the two the
redesign is not allowed to loosen.

One concrete finding inside this: **V6_ADMIT_3 changed nothing.** Dropping the
breadth requirement from 5 qualifying contracts to 3 produced exactly the same
4 entries. *(Inference)* chains failing admission are therefore failing well
below 3 qualifying contracts — that is, on the per-contract open-interest and
spread caps, which are frozen cost-model integrity. The only liquidity
relaxation the brief permits is the one that does not help.

---

## 3. Concentration — which names actually contribute

The brief requires per-name contribution so concentration is visible.

- **V0_BASELINE (4 entries):** NOW 2, MSFT 1, PLTR 1. **12 of 15 names
  contribute nothing.**
- **V9_LANE_A_OR (104):** PLTR 37, NOW 28, CRWV 12, MSFT 12, SMCI 12, VST 2,
  AVGO 1. Top name = 36% of all entries; 8 of 15 names contribute nothing.
- **V17_COMBO_WIDE (147):** NOW 28, AVGO 24, CRWV 21, MSFT 20, PLTR 16,
  IREN 14, SMCI 11, AMD 5, TEM 3, CEG 2, NVDA 2, AMZN 1. Top name = 19%;
  3 of 15 contribute nothing. This is the least concentrated candidate.
- Almost every entry in every variant comes from **one lane** (the
  drawdown-reclaim setup). The coil setup contributes 1 entry in V10 and V16,
  4 in V17. The short-premium lane contributes **zero entries in every
  variant** on this panel.

The short-premium lane producing nothing anywhere is worth the owner's
attention on its own: it requires the deep-fall trigger *and* options priced
at least 1.25× realised volatility *and* a qualifying put structure, and that
conjunction did not occur once in 1,050 name-days.

---

## 4. Long-history check: the trigger across regimes

70 sessions is a small sample for rare events, so the brief asks for a longer
panel. Here the honest answer is split, because of a data limit described in
the conflicts section: the **full stack cannot be evaluated** before
2026-04-02, so the long panel measures the **technical trigger only**.

Panel: every cached session per name, 2018-01-02 → 2026-07-27, 23,716
name-days. Receipts: `variant-receipts/deep_arming_census/`.

| Variant | Armed name-days | Rate | Per 70-session window | Rolling 70-session min / median / max |
|---|---|---|---|---|
| V0_BASELINE | 1,395 / 23,716 | 5.88% | 61.8 | **0 / 43 / 143** |
| V1_DRAWDOWN_15 | 1,471 | 6.20% | 65.1 | 0 / 45 / 146 |
| V2_DRAWDOWN_10 | 1,512 | 6.38% | 66.9 | 0 / 45 / 146 |
| V3_RANGE_20 | 2,618 | 11.04% | 115.9 | 2 / 72 / 253 |
| V4_RVPCTILE_40 | 2,037 | 8.59% | 90.2 | 1 / 62 / 189 |
| V8_RECLAIM_10 | 1,507 | 6.35% | 66.7 | 3 / 45 / 145 |
| V9_LANE_A_OR | 8,084 | 34.09% | 357.9 | 43 / 212 / 656 |
| V10_LANE_B_OR | 8,519 | 35.92% | 377.2 | 2 / 273 / 682 |
| V14_REGISTERED_COHORT_9 | 1,148 / 15,803 | 7.27% | 45.8 | 0 / 30 / 140 |
| V16_COMBO_MEDIUM | 4,014 | 16.93% | 177.7 | 5 / 126 / 296 |
| V17_COMBO_WIDE | 20,654 | 87.09% | 914.4 | 285 / 665 / 1,044 |

Two things to take from this.

**First, the required clustering caveat, with numbers.** The baseline trigger
arms between **0 and 143 times** per rolling 70-session window, median 43.
Entry opportunities are not evenly spread — they bunch in volatile periods.
A single binomial interval therefore *understates* how much one window can
differ from another. Whatever number is frozen at registration, the actual
count in one particular 70-session window can land far from it.

**Second, the trigger is not the constraint.** The baseline arms ~62 times per
window and delivers 4 entries. Everything that makes entries rare happens
*after* arming.

Also visible: V17 arms on **87% of all name-days**. A rule that considers
almost every day a setup is not a selective entry rule; it is close to "be in
the market", which is a different research question.

---

## 5. The arithmetic ceiling (Inference — please sanity-check this)

The registered design allows **one open position per name**
(`H7_MAX_OPEN_PER_UNDERLYING = 1`). A long-lane position is opened at the
monthly expiry nearest 90 days out and time-exits at 30 days
(`H7_CLOSE_AT_DTE`), so it occupies its name for roughly 60 calendar days ≈
**42 trading sessions**.

That caps how many entries a window can physically contain, whatever the
entry rule:

- 70 sessions ÷ 42 = **1.67 entries per name** per window;
- × 15 names ≈ **25 entries**;
- × 9 names (the registered cohort) ≈ **15 entries**;
- the short-premium lane is capped at 1 concurrent position basket-wide and
  occupies ~21 sessions, adding at most ~3.

**Consequences, if this arithmetic is right:**

1. The 20-entry bar requires running at roughly **80% of the theoretical
   maximum** with the full 15 names. That is a demanding target for a rule
   that is supposed to be selective.
2. With the **9-name registered cohort the bar cannot be met at all** on a
   70-session window — the ceiling (~15, plus ~3) sits below 20 regardless of
   how the entry rule is written.
3. The measured position-limited figures agree with the ceiling: V17 reached
   15 (42-session holds) and 24 (21-session holds), i.e. it is already pressed
   against the ceiling rather than limited by its trigger.

This suggests the productive levers are **structural, not signal**: a longer
declared window, a shorter holding period, more names, or allowing more than
one position per name. All of those are owner decisions, and each needs its
own registration.

---

## 6. Honesty caveats — and which way each one pushes

Per review finding B4, this travels with every number above.

**Everything here was measured on ThetaData end-of-day chains. The forward
window would run on Schwab data captured at 15:45, before the close.** They
are not the same measurement.

| Simplification | Direction | Why |
|---|---|---|
| End-of-day settled quotes rather than 15:45 live quotes | **Inflates** | Settled end-of-day quotes are tighter and cleaner, so the liquidity check passes more often than it would at 15:45. |
| Same-session open interest | **Inflates** | Open interest is published after the close. A 15:45 decision cannot see it; this replay can. |
| Empty book every session, full monthly budget every session | **Inflates, heavily** | No open position ever blocks a name and the budget never depletes. This is the single largest distortion — see the "after position limit" column, where 104 becomes 10. |
| No source-health or data-gate gating applied | **Inflates** | Live, an unhealthy source bans that name for the session; here every name is always eligible. |
| No slippage beyond the frozen adverse-side fill | Neutral | Frozen fill realism was applied unchanged and was never relaxed. |
| Earnings-panel historical coverage | **Deflates** | Where no earnings assertion was knowable, the gate fails closed and no entry is possible. On the 70-session panel this is real; on the long panel it is total (see conflicts). |

Net: **the counts in section 1 are upper bounds, not central estimates.** The
one bias pushing the other way (earnings coverage) is a data-completeness
problem whose correct fix is more primary-source earnings dates — the work
already begun in the 2026-08-11 earnings repair — not a looser gate.

---

## 7. Where the brief met reality

Four points where I could not do exactly what brief 09 asked, and what I did
instead.

**7.1 The long full-stack panel is impossible; it became an arming census.**
The brief asks for "a longer lookback panel (all cached history per name)" for
the full stack. The earnings gating panel's earliest knowable assertion is
**2026-04-02**. Before that date the frozen earnings gate has nothing to read
and fails closed to UNKNOWN for every name, so the full stack produces
structurally zero entries across 2018–2026. Reporting that as a base rate
would have produced a very tight confidence interval around approximately
zero — a number that looks precise and means nothing. The long panel therefore
measures the **technical trigger only** (section 4), which is genuinely
computable across the whole history and is the statistic the clustering
caveat needs. The receipts say this in their own `why_arming_only` field.

**7.2 The "wider universe" axis has nothing to widen to.** The brief's axis 2
compares "the current 15-name cohort vs the wider owner-authorized watchlist
names that pass source-health". On disk, 15 **is** the entire authorised
scope: `H7_WATCHLIST` (11) + `H7_CORE_LONG_ONLY` (4), with one name excluded —
HYLN, excluded for a dead options chain of about 128 rows a day. Adding it
would be a liquidity-realism violation, not a universe choice. I measured the
axis in the only direction available: the registered 9-name cohort versus the
full 15 (V14), and reported per-name contribution throughout. **Widening the
universe beyond 15 requires an owner decision to authorise new names, and new
cached data for them.**

**7.3 The baseline number.** The brief cites 4/1050 from a receipt living on
the unreviewed `codex/h7-schwab-recovery` branch. I re-derived it independently
on this branch and reproduced **4/1050 with the identical four passing
name-days** (NOW 2026-05-18, NOW 2026-07-13, MSFT 2026-07-16, PLTR
2026-07-16), and the input files hash-match. The cited number is confirmed;
the older 3/1050 figure is superseded, as the scope audit stated.

**7.4 Deliverable filename.** The brief names
`reports/h7_forward_schwab/2026-08-XX-entry-redesign-menu.md`; this file uses
the more specific name requested in the task assignment. Same content, same
directory — flagged only so the brief and the artifact can be reconciled.

One further disclosure: the long panel spans 2018–2026 and therefore crosses
`IN_SAMPLE_END` (2022-12-31). It computes **no outcome of any kind**, so it
spends no out-of-sample reveal budget in the sense that budget exists — the
budget protects against seeing *results*, and no result was computed. H7's
historical diagnostic is in any case permanently withdrawn, so there is no
legacy verdict path this could contaminate.

---

## 8. What is now in front of the owner

Nothing in this document is a recommendation. The measured position is:

1. **No variant clears the 20-entry bar under the position limit you already
   registered.** The two that clear it unconstrained are also the two that
   stop testing the original idea.
2. **Loosening the entry thresholds is not the lever.** The trigger arms ~62
   times per window; entries are lost afterwards, mostly at two gates that
   must not be loosened.
3. **The bar may be structurally out of reach on a 70-session window** —
   certainly so for the 9-name cohort, if the section 5 arithmetic holds.

That points the decision away from "which variant" and toward a prior
question: whether the *window and holding period* are the things to change,
rather than the entry rule. A longer declared window is the one lever that
raises the ceiling without touching the hypothesis, without touching fill
realism, and without changing what H7 is testing.

Whatever is chosen: the frozen numbers are typed by the owner at registration,
the registration must pass the 2026-07-24 feasibility gate quoting the chosen
variant's receipt, and it must disclose that 18 candidates were measured.

---

## Reproducing this

```bash
uv run python -m tools.h7_entry_variant_menu --panel both \
  --outdir reports/h7_forward_schwab/variant-receipts
```

Cached data only — parquet chain cache plus cached underlying closes. No
provider calls, no network. Each receipt is hash-bound and immutable: rerunning
against changed inputs raises rather than overwriting.

**Run it from the main checkout.** A worktree has no `.cache` of its own. These
numbers were produced with `.cache` symlinked to the main checkout's, following
the `~/options-validator-ops` convention. That symlink must be **removed before
running the test suite**: two tests legitimately require an empty cache
(`test_experiments_dashboard` asserts the DATA BLOCKED banner, and the
short-positioning git-policy test walks `.cache/` paths), so they fail against
a populated one. The suite was verified green with the symlink removed; the
cache was byte-for-byte unchanged by every run
(`tools/irreplaceable_data_guard.py verify` clean).

Tests: `uv run python -m unittest discover -s tests` (see
`tests/test_h7_entry_variant_menu.py` for the causality, no-look-ahead,
receipt-hashing, integrity-guard, and occupancy tests).

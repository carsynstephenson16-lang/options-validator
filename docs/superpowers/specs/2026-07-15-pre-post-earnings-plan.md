# Pre- and post-earnings plan — owner request 2026-07-15

**Owner's asks, verbatim intent:** (1) discomfort with buying "directly after
earnings" and with having to act fast; (2) preference for buying in the weeks
*leading up to* earnings and selling *before* the IV crush; (3) confirm that
the H6 pattern — longer-dated options sold well before expiry — beats holding
14–21 DTE options on probability and profitability.

**Evidence base:** Phase E1 descriptive study
(`reports/2026-07-15-event-vol-descriptive-study.md`; 36 NVDA / 34 AMZN /
23 PLTR / 38 SMCI past events from the local cache). Everything interpretive
below is labeled Inference; nothing here is a backtest result or an edge claim.

---

## 1. A premise to correct first: H6 does not require acting fast

Repo-verified from the trial-7 registration: post-report entries are allowed
**unconditionally during the first 5 trading sessions after a report**,
evaluated end-of-day by `h6_watch`. That is a full week of once-a-day,
close-of-day decisions — no reaction speed involved. The "act fast" worry
applies to intraday earnings scalping, which this platform has never proposed.

## 2. Post-earnings plan: H6 continues exactly as registered

- H6 keeps running its forward paper window: NVDA/PLTR/AMZN, 45–90 DTE
  nearest monthly, delta 0.30–0.50, exit at 21 DTE or +100% TP, ≤$2k/month
  at risk. One position is already open (H6-0001, NVDA $220C Sep-18) and
  keeps its registered exits.
- Comfort is not a reason to amend a registered trial mid-window; the paper
  book risks zero dollars, and its verdict is valuable **whatever it shows**
  ("no edge" is a success here). If the owner still dislikes post-earnings
  entries after the H6 verdict lands, the lane simply isn't renewed.
- The post-earnings side of the calendar therefore needs no new decision.

## 3. Pre-earnings plan: a NEW hypothesis proposal (H8 candidate)

Buying weeks before the report and exiting before the announcement is not an
H6 tweak — H6 *bans* entries in the 5 sessions pre-report and holds through
nothing. Under ledger discipline this is a new hypothesis with its own
registration, numbers owner-typed. Note for the record: the owner's 2026-07-08
timing doctrine was the opposite ("avoid IV-crush exposure pre-earnings, real
entries after earnings"); reversing it forward-only via a new registration is
legitimate and is disclosed here.

**What the E1 evidence says about this design (Inference):**
- The exit-before-report rule is what protects against crush; **tenor decides
  the penalty when that rule misfires** (late exit, report date slips): crush
  is 2–4× smaller at 45–90 DTE than at 14–30 DTE in every name measured.
- 14–30 DTE contracts routinely expire around the event window itself — no
  schedule margin. The 45–90 DTE contract always survives the window.
- The harvestable pre-event IV run-up is **name-dependent**: PLTR large
  (+22 IV pts short-tenor), SMCI/AMZN moderate, **NVDA ≈ 0** (surface already
  elevated). A pre-earnings lane keyed on run-up cannot treat the universe
  uniformly.
- The dominant risk is **spot drift, not vol**: PLTR 2026-02 trace lost ~80%
  of the call's value *before* the report on an adverse spot move. This lane
  is a directional bet with a vol tailwind at best. No exit-before-report
  rule protects against being simply wrong on direction.

**Proposal table — every number LLM-proposed (Inference from E1 + H6
symmetry); nothing is frozen until the owner types it into the registration:**

| Parameter | Proposed | Rationale (Inference) |
|---|---|---|
| Universe | NVDA, PLTR, AMZN (H6 names) | liquidity already screened; but see run-up nuance — owner may prefer PLTR/AMZN only, NVDA's measured run-up ≈ 0 |
| Structure | single long call, nearest monthly 45–90 DTE at entry | E1: schedule margin, 2–4× smaller crush penalty, ~1% half-spreads, slower decay |
| Delta band | 0.30–0.50, highest delta, ask ≤ $1,000 | mirror H6 for comparability |
| Entry window | T-15 .. T-8 sessions before a **CONFIRMED** report date | E1 measured run-up starting by T-15; estimated dates = no entry (fail closed) |
| Entry vol gate | IV-rank ≤ 0.50 at entry | don't buy the spike you're hoping to ride; NaN IVR = no entry |
| Exit (time) | HARD close at T-2 sessions before the scheduled report | one-session buffer vs T-1; if the confirmed date moves inside T-2, close at the next session's close, no exceptions |
| Exit (profit) | take-profit +75% of premium | shorter hold than H6's window; owner may prefer H6's +100% for symmetry |
| Stop-loss | none | H1 evidence: stops were the loss engine |
| Sizing | ≤ $2,000 premium at risk / calendar month; max 1 contract/name; max 2 concurrent | sleeve arithmetic below |
| Lane exclusivity | never H8 and H6 open on the same underlying at once | H8 exits T-2, H6 enters post-report — naturally sequential |
| Verdict | after 8 completed positions: bootstrap CI90 upper bound of per-trade expectancy < 0 → REJECT; hard kill: 3 consecutive full-cap-loss months | mirror H6's loss-gated design |
| Validation | forward paper window only | 2023+ history is not a credible blind holdout for these names; any historical run would also need its own pre-registration |
| Fills/costs | frozen cost model (mid-or-worse + slippage haircut + commissions both legs/ways) | unchanged repo-wide |

**Sleeve arithmetic the owner must see before typing:** H6 $2k + H7 $6k + a
new H8 $2k = **$10k/month maximum new paper risk against a $14k honest
sleeve**. All paper today — but these caps become the de-facto live template
if lanes ever activate. An alternative is a **shared $2k/month cap across
H6+H8** (one earnings-tactical budget, two windows), which adds zero new
sleeve load. That choice is the owner's.

**Cadence check vs the owner's goal (1–2 trades/month):** three quarterly
reporters give ~12 post-earnings windows/year (H6) and ~12 pre-earnings
windows/year (H8) — combined ≈ 2 candidate windows/month on average,
clustered around earnings seasons. The two-lane plan meets the cadence goal
without touching shorter tenors.

## 4. The tenor question, answered honestly

"Ensure it will be more profitable and higher probability than 14–21 day
options" — **no analysis can ensure that**, and this platform's vocabulary
rules exist precisely for this moment. What the measured evidence supports
(Inference from E1, mechanics not outcomes):

- For the owner's actual use pattern — hold a few weeks, sell well before
  expiry/event — 45–90 DTE dominates 14–21 DTE on **every measured
  mechanical axis**: 2–4× smaller crush exposure if an exit misses, contracts
  that survive schedule slips (14–30 DTE picks routinely expired inside the
  event window), cheaper half-spreads (~1.0–1.2% vs 1.3–2.0% on the
  mega-caps), and slower per-session decay where drift was controlled (SMCI:
  −2.8%/session vs −7.6%).
- A 14–21 DTE option bought pre-earnings is mostly a concentrated bet on the
  event itself, purchased at the top of the run-up, carrying the largest
  measured crush (−11 to −28 IV pts) — the exact exposure the owner said
  they want to avoid.
- Whether the 45–90 DTE *strategy* is profitable with high probability is a
  different question, and only the pre-registered forward paper window can
  answer it. That is what H6 is already doing post-earnings and what H8
  would do pre-earnings. Anything stronger than "the mechanics favor it and
  the test is designed" would be a claim this repo bans.

## 5. What happens next (owner actions, in order)

1. Decide H8: register as proposed / register with edits / decline. If
   registering: **type the frozen numbers personally** into the ledger
   registration (per standing rule 3), including the shared-vs-separate
   monthly cap choice and the NVDA inclusion call.
2. Optionally authorize Phase E2 later — an event-edge *gate* (e.g., enter
   only when implied move ≤ X× median realized of last N like events) —
   which requires its own pre-registered definitions before it filters any
   entry. E1's tables supply the candidate values; E2 stays closed until
   then.
3. No build is needed for H6 (already operational). H8 tooling (an
   `h8_watch` mirroring `h6_watch`'s exact-session read-only pattern) gets
   built only after registration.

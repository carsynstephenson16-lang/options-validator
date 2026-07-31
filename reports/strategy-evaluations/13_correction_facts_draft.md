# 13 — Correction facts for three permanent records: DRAFT, NOT APPENDED

**Date:** 2026-07-30
**Owner decision 2026-07-30:** *"Append correction facts to the ledger."*
**Status: drafted only. Nothing has been written to `ledger/facts.log`.**

Two reasons this is a draft rather than an append:

1. The owner's chosen option said explicitly *"I draft; you read before it lands."*
2. CLAUDE.md requires that a recorded amendment pass independent adversarial
   review before it goes in. That review has not run on this text.

The ledger is append-only. Wrong correction text cannot be edited out, only
appended over — so the cost of a careless append is permanent.

---

## What is wrong, and what is not

The capital-efficiency defect divided total P&L by the **mean** capital instead
of the **total**. That inflates the number by exactly the trade count. The same
defect exists a second time in `return_on_economic_max_loss`, which
`88ffbb6` did **not** fix ([`metrics.py:515-519`](../../metrics.py#L515-L519)) —
so each record carries **two** wrong ratios, not one.

**The adjudicated verdicts are unaffected and stand.** `metrics.scoreboard`
derives the verdict from the loss count, the cohort count and the confidence
interval only ([`metrics.py:521-543`](../../metrics.py#L521-L543)); it never
reads either ratio. H1 FAIL, H2 FAIL, H9 INSUFFICIENT_SAMPLE are all untouched.
What is wrong is the descriptive record around them.

---

## The numbers, recomputed

Honest value = recorded value ÷ trade count, exactly.

| Record | Trades | Field | Recorded | Honest |
|---|---:|---|---:|---:|
| **H1** `ledger/experiments.jsonl` seq 0 | 226 | `capital_efficiency` | −4,510.21% | **−19.96%** |
| | | `return_on_economic_max_loss` | −4,442.93% | **−19.66%** |
| **H2** `ledger/experiments.jsonl` seq 3 | 196 | `capital_efficiency` | −1,835.34% | **−9.36%** |
| | | `return_on_economic_max_loss` | −1,823.97% | **−9.31%** |
| **H9** `reports/h9/receipt.json` | 16 | `capital_efficiency` | +1,387.30% | **+86.71%** |
| | | `return_on_economic_max_loss` | NaN | not affected |

### H9's drawdown is additionally wrong, and by more than previously believed

`10_fix_arc_owner_decisions.md` §D8 attributed it to the missing zero start.
That is secondary. The trade list was handed to `scoreboard` **sorted
alphabetically by ticker**, not chronologically:

| Ordering | Drawdown |
|---|---:|
| As recorded — alphabetical, no zero start | **$361.30** |
| Alphabetical, zero-anchored | $482.30 |
| **Chronological by entry date** | **$718.50** |
| Chronological by exit date | $572.20 |

$361.30 reproduces exactly under the alphabetical ordering and no other.
This figure appears in **prose** in `ledger/facts.log:17892`, not only inside a
JSON blob, so it is the most quotable of the wrong numbers.

**H1 and H2 drawdowns: not corrected here.** No per-trade list survives for
either, so the figures cannot be recomputed. *Inference:* both recorded
drawdowns already exceed the absolute total loss ($23,411.40 vs $23,230.80;
$7,969.00 vs $7,658.60), which implies the equity curve peaked above zero, which
in turn implies the missing zero start did not bind. That is reasoning, not
measurement, and the correction text should say so rather than assert the
figures are fine.

---

## Draft text — for owner review, not yet appended

> **METRIC_CORRECTION 2026-07-30 (H1, H2, H9).** Three permanent records carry
> inflated capital-use ratios. Cause: `metrics.scoreboard` divided total P&L by
> the MEAN per-trade capital instead of the SUM, inflating both
> `capital_efficiency` and `return_on_economic_max_loss` by exactly the trade
> count. Fixed for `capital_efficiency` in commit 88ffbb6 (renamed
> `trade_weighted_return_on_risk`, sum denominator);
> `return_on_economic_max_loss` remained defective at that commit and is
> recorded here as an open defect. Corrected values, recomputed as recorded ÷ n:
> H1 (seq 0, n=226) capital_efficiency −4510.21% → −19.96%,
> return_on_economic_max_loss −4442.93% → −19.66%;
> H2 (seq 3, n=196) −1835.34% → −9.36% and −1823.97% → −9.31%;
> H9 (reports/h9/receipt.json, n=16) capital_efficiency +1387.30% → +86.71%,
> return_on_economic_max_loss NaN (unaffected).
> VERDICTS UNAFFECTED AND STANDING: H1 FAIL, H2 FAIL, H9 INSUFFICIENT_SAMPLE.
> `metrics.scoreboard` derives the verdict from loss count, cohort count and the
> confidence interval only and never reads either ratio (metrics.py:521-543).
> ADDITIONALLY, H9's recorded max_drawdown $361.30 is wrong for a second,
> previously unidentified reason: the trade list was passed to scoreboard sorted
> alphabetically by symbol rather than chronologically, and `_max_drawdown` has
> no ordering contract. Recomputed from the receipt's own trades array: $482.30
> alphabetical zero-anchored, $718.50 chronological by entry date, $572.20
> chronological by exit date. The recorded $361.30 reproduces only under the
> alphabetical no-zero-start computation. The $361.30 figure is also quoted in
> prose at ledger/facts.log:17892. H1 and H2 drawdowns are NOT corrected: no
> per-trade list survives for either; both recorded drawdowns exceed their
> absolute total loss, which is consistent with a positive equity peak and
> therefore with the missing zero start not binding — inference, not
> measurement. No registered parameter, threshold, window or verdict is amended
> by this fact. Provenance: agent-drafted, owner-directed 2026-07-30; entry
> mechanics disclosed.

---

## Before this is appended

- [ ] Independent adversarial review of the text (CLAUDE.md requirement)
- [ ] Owner reads and approves the wording
- [ ] Confirm the ledger-guard hook accepts a `METRIC_CORRECTION` prefix, or
      choose an accepted one
- [ ] Decide whether `return_on_economic_max_loss` gets fixed *before* the fact
      is written, so the fact can say "fixed in <sha>" rather than "open defect"

The last item is worth deciding deliberately: appending a correction that names
a still-open defect is honest, but it means a second correction later.

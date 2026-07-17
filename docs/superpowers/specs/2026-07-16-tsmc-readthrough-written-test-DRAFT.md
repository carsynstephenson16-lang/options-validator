# TSMC monthly-revenue read-through — written test (DRAFT; NO TRADE PERMISSION)

**Status: DRAFT registration for a written study only. Owner directive
2026-07-16: "Put the TSMC monthly-revenue read-through into a written test
only, with no trade permission." This document can never authorize a trade,
a paper position, a lane, or a watcher. Its only possible outputs are the
§4 vocabulary strings. Owner-typed §3 values + external review required
before the single run; one-run contract applies (QM-study precedent).**

Scope-guard note: this does not move a live hypothesis toward its verdict;
it exists by explicit owner decision (2026-07-16 session), which is the
documented override the AGENTS.md scope gate requires.

## 1. Question

TSMC publishes monthly revenue ~the 10th of each month as an immutable SEC
6-K, 5–7 weeks before NVDA/AMD/AVGO quarterly prints (source:
`reports/2026-07-16-pre-earnings-signal-research.md`, candidate 2, with
verified 6-K accessions). Written test: **does the TSMC monthly-revenue
surprise contain directional information about the subsequent fabless
print's reaction, beyond what the option market already implies at T-1?**

## 2. Design (fixed at registration)

- **Signal:** for each subject print (NVDA, AMD, AVGO), take the TSMC
  monthly-revenue reports published inside the subject's fiscal quarter and
  compute the signal metric (§3 owner-typed definition; proposal: YoY growth
  of the latest covered month vs the trailing-12-month YoY trend, sign only).
  known_as_of = the 6-K acceptance timestamp; a report is usable only if
  accepted before the subject's print.
- **Outcome:** subject's next-session close-to-close reaction sign (and,
  informationally, magnitude vs the T-1 ATM-straddle implied move from the
  local chain cache).
- **Association test:** sign agreement rate + exact binomial CI against 0.5,
  and conditional on the option-implied direction being flat-prior (the
  "beats the chain" framing). No P&L, no fills, no cost model — this is a
  written test, not a backtest.
- **Window:** 2018-01-01..2026-06-30 (matches cached chains for the implied
  leg; TSMC 6-Ks are fetched from EDGAR — free, unpaid, allowed).
- **Non-blind disclosure:** the window is historical; the E1 study examined
  NVDA post-earnings option behavior (not TSMC signals). Designed 2026 with
  hindsight; vocabulary prices this in.

## 3. Owner-typed values (blank; registration blocked until typed)

| Parameter | Owner-typed | LLM proposal | Reasoning (Inference) |
|---|---|---|---|
| Signal metric definition | ______ | sign of (latest covered month YoY − trailing-12m mean YoY) | parameter-free apart from the trailing window; sign-only resists overfitting |
| Subjects | ______ | NVDA, AMD, AVGO | the three fabless names with TSMC exposure and full chain caches (AVGO chains begin 2026-05 — implied-move leg will be [DATA GAP] before that; disclose per-name) |
| Minimum events for any verdict | ______ | 24 prints per subject pooled ≥ 60 | below this, INSUFFICIENT_SAMPLE |
| Agreement-rate rejection bound | ______ | CI90 upper < 0.5 → REJECTED (as an anticipation signal) | kill-not-bless symmetry with H9 |

## 4. Outcomes (frozen vocabulary)

`REJECTED | INSUFFICIENT_SAMPLE | NOT_REJECTED_FOR_THIS_NARROW_WRITTEN_TEST`

The third outcome explicitly does not authorize trading, does not create a
lane or hypothesis, and is not evidence for H6/H7/H8/H9. Promoting this
signal to anything trade-adjacent requires a new registration and an owner
decision, from scratch.

## 5. Run binding

One run. Artifact binds spec sha256, code commit, the exact 6-K accession
list, chain-cache manifest for the implied-move leg, and the full event
table. Ledger facts: `TSMC_RT_REGISTERED` → `TSMC_RT_RESULT`.

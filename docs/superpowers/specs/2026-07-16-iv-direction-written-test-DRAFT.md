# Pre-earnings IV-direction study — written test (DRAFT; NO TRADE PERMISSION)

**Status: DRAFT registration for a written study only. Owner directive
2026-07-16 (mid-session addendum): pursue the option-price direction study
as a written test with no trade permission, alongside the TSMC read-through.
This document can never authorize a trade, paper position, lane, or
watcher. Outputs limited to the §4 vocabulary. Owner-typed §3 values +
external review required before the single run; one-run contract applies.**

Scope-guard note: exists by explicit owner decision (2026-07-16 session),
the documented override the AGENTS.md scope gate requires.

## 1. Question

The platform's own chain cache (2018-01-02..2026-06-30, 8 archive names,
NBBO + OI + greeks) permits a replication with perfect local point-in-time
properties: **do pre-earnings option-surface changes (call-vs-put implied-vol
spread; OI-weighted skew shift) predict the DIRECTION of the post-earnings
reaction?** The literature the signal-landscape survey cites reports these
effects as real-but-decaying; a null result is a successful outcome
(replication framing, stated up front).

## 2. Design (fixed at registration)

- **Events:** verified occurred reports from `assertions_v2.csv` (8-K
  acceptance timestamps), same event timing definitions as the H9 spec §2
  (T_pre / T_dec via XNYS close timestamps) — reuse, don't re-derive.
- **Signals measured over T-10..T-1 sessions** (owner-typed window, §3):
  (a) change in ATM call-IV minus put-IV spread; (b) change in 25-delta
  risk-reversal proxy from cached greeks; (c) OI migration sign
  (net new call OI vs put OI, nearest post-event expiry).
- **Outcome:** T_dec close-to-close reaction sign vs T_pre.
- **Test:** per-signal sign-agreement rate with exact binomial CI vs 0.5;
  pooled and per-name. No P&L, no fills, no costs.
- **Non-blind disclosure (material):** the E1 descriptive study already
  examined pre/post-earnings IV behavior for NVDA, AMZN, PLTR, SMCI on this
  same cache. This study's signals overlap E1's measurement families, so
  contamination is REAL for those four names. Pre-declared cohort split:
  primary = all 8 names; secondary informational = E1-untouched names
  (NOW, MSFT, VST, CEG). Verdict binds to primary; the E1-untouched cut is
  reported alongside and cannot flip the verdict.

## 3. Owner-typed values (blank; registration blocked until typed)

| Parameter | Owner-typed | LLM proposal | Reasoning (Inference) |
|---|---|---|---|
| Signal window | ______ | T-10..T-1 sessions | inside the IV run-up E1 measured; short enough to be event-specific |
| Signals included | ______ | (a)+(b)+(c) above, each tested separately, Bonferroni ×3 | testing 3 signals separately without correction is silent p-hacking |
| Minimum events | ______ | 60 data-sufficient pooled | matches H9 census floor logic |
| Rejection bound | ______ | per-signal CI90 upper < 0.5 → REJECTED | kill-not-bless symmetry |

## 4. Outcomes (frozen vocabulary)

`REJECTED | INSUFFICIENT_SAMPLE | NOT_REJECTED_FOR_THIS_NARROW_WRITTEN_TEST`

The third outcome authorizes nothing, creates no lane, and is not evidence
for H6/H7/H8/H9. Any promotion requires a new registration from scratch.

## 5. Run binding

One run. Artifact binds spec sha256, code commit, chain-cache manifest,
assertion-store row ids, and the full event table with per-name
contamination labels. Ledger facts: `IVDIR_REGISTERED` → `IVDIR_RESULT`.

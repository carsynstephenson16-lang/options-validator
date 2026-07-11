# H7 7b-2R.1 correction release (2026-07-11)

**Status: EXECUTING.** Base commit `56d63be`. Ordered by the owner's second
independent review: NO-GO on 7b-3; the historical diagnostic remains
closed; hard-stop for independent review at the end.

## Owner decisions (recorded before any code)

1. **Ratify the three data exclusions ONLY as archive-availability gaps**
   (PLTR 2020-09-30..10-05, 4 sessions; CEG 2022-02-02..02-08, 5; SMCI
   2020-01-14..2020-05-04, 77). No claim that options did not exist — only
   that no causally auditable chain is available. Recorded as
   **H7_AMENDMENT_V1_3 via the conservative trial_intent path; trial count
   10 → 11 accepted.** Registry `ratified_by` = the amendment record's
   full hash, verified mechanically against the ledger.
2. **Earnings coverage declarations REJECTED.** `data/earnings/coverage.json`
   is never created. SEC Item 2.02 completeness cannot prove no schedule
   was publicly available elsewhere. Conflicts/malformed assertions are
   always DATA_GAP; a declaration can never turn a conflict — or an empty
   archive — into PROVEN_UNKNOWN.
3. **Narrowed 49% historical estimand REJECTED** (post-report-grace-only
   sample is not the registered always-on strategy; could falsely kill,
   cannot bless).
4. **The 2018–2026 diagnostic is WITHDRAWN as verdict-capable H7
   evidence.** No diagnostic attempt, no backtest, no P&L. The
   point-in-time **forward paper window is the sole verdict-bearing
   path.** All frozen thresholds unchanged.
5. A post-earnings-only historical study may later be registered as a
   separate conditional hypothesis; it must never reject or validate H7.

## Corrections in this arc

- **A. Launch bypass**: DiagnosticCapability (freely constructible) is
  removed; attempt/receipt/registration/scope/ledger verification moves
  INSIDE the execution boundary (`run_lane` refuses OOS windows without a
  verified diagnostic id, before reading any chain). `h7_adjudicate` CLI
  accepts only an already-ledgered result id (chain verified first).
  Adversarial tests prove neither direct import nor standalone
  adjudication can reveal an unledgered result.
- **B. Receipt v3** (`receipt_v3.json`; v2 preserved as BLOCKED artifact):
  verification RECOMPUTES the audit from current inputs — facts.log
  provenance, tracked manifest + its commit + exact adapter blob hash,
  full chain-directory inventory/classification, calendar identity +
  sessions + actual close timestamps, earnings stores, registry, config/
  cost/source surfaces. New unexpected files, changed provenance facts,
  manifest or calendar drift all invalidate. Machine-readable defect
  identities, not aggregate counts.
- **C. Earnings semantics**: `assertions_v2.csv` becomes RAW evidence
  only. A versioned GATING store (schema v3) separates promotion from
  collection, with event classes (actual_quarterly_earnings /
  preliminary_earnings / business_update / other_item_202 /
  unclassified); only a verified actual quarterly release starts
  H7_EARNINGS_POST_REPORT_GRACE_D; fiscal-period identity + source proof
  required; the 254 bulk rows are NOT bulk-labeled and remain non-gating;
  SMCI 2024-01-18 (update) vs 2024-01-29 (earnings) regressions.
- **D. Mechanical ratification**: `ratified_by` must be the full hash of a
  verified H7 ledger record; the EXAMPLE-label test is replaced with real
  synthetic ledger records; the empty-archive+declaration→PASS behavior is
  deleted.
- **E. Hygiene**: SEC_USER_AGENT required from the environment (committed
  email removed; missing config fails closed); verdict-path broad
  exception handling replaced with explicit exceptions + identity-bearing
  failure records. Strategy dispatch/dict refactors deliberately NOT done
  (parked as architecture work).

## Stopping rule

Full suite, ruff, pyright, pre-commit, ledger verify, adversarial tests,
corrected full-window audit (expected: **BLOCK, honestly** — historical
earnings provenance is insufficient). Hard-stop with commit range, checks,
trial count 11, corrected findings, confirmation that no coverage.json /
attempt / backtest / result artifact / P&L exists, and a PROPOSED (not
implemented) 7b-F0 forward-paper readiness plan. The next independent
review authorizes 7b-F0.

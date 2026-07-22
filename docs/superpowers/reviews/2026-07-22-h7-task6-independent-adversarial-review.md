# H7 Task 6 — independent adversarial review

**Date:** 2026-07-22  
**Branch:** `docs/replan-2026-07-22`  
**Review basis:** candidate worktree after `53e7184`  
**Reviewer:** fresh-context independent Codex reviewer  
**Normative source:** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`

## Verdict

**Implementation review: PASS.** No code blocker remains in the
reviewed authority, receipt-binding, lifecycle, causal-lineage, idempotency,
concurrency, scoring, or result-withholding boundaries.

**Task 6 / activation: BLOCKED pending final proof and owner PASS.** The owner
ratified `H7_EXIT_SCORING_SPEC_AMENDMENT_V1_2` exactly as recommended below at
2026-07-22T23:37:48Z, resolving the review's sole normative condition. The
build remains **BUILD-ONLY / INACTIVE** until the exact committed candidate
passes the complete offline suite and receives the separate §9 owner PASS.
Task 7 remains closed.

## Owner ruling applied to F1

Preview stays completely silent about result-derived values until the owner
has signed off. It reports only that the result is withheld; it does not
compute or expose trade count, verdict, expectancy, confidence intervals, or
other scoring statistics. This is stricter and easier to audit than treating
trade count as harmless interim information.

## Completion-audit findings disposition

| Finding | Disposition |
|---|---|
| F1 interim preview verdict | Remediated. Preview does not call the scorer and emits no result-derived field. |
| F2 exit refusal coverage | Remediated with corrupt/absent ledger, cohort, date, stale contract, receipt, cache-byte, and future-EOD refusal tests. |
| F3 cross-capability guard | Remediated and test-pinned in both directions. |
| F4 mutation-time revalidation | Remediated and proven against post-open evidence changes. |
| F5 settlement structures | Remediated with debit- and credit-spread intrinsic/fallback coverage. |
| F6 replay/idempotency | Remediated through evidence, intent, fill, settlement, and artifact call sites. |
| F7 `ab883f4` wording | Clarified: it fixed an AST one-door classifier false positive, not a runtime security defect. |
| F8 duplicated guards | Accepted as a bounded maintainability item; no activation-safety blocker. |
| F9 immutable-receipt race | Remediated with atomic no-clobber publication, conflict preservation, file sync, and directory sync. |
| F10 scoring seam | Re-derived and test-pinned. The direct ledger writes target only a fresh temporary synthetic store; the production one-door test now describes the actual boundary. |

The review also found and remediated additional trust-boundary defects while
attempting to falsify the candidate:

- real lifecycle mutations now re-earn factory authority and compare the
  exact receipt-bound chain and close values immediately before mutation;
- opening fills, skips, exit intents, retry gaps, market closes, and
  settlements validate deterministic identity, exact causes, recorded-time
  cutoffs, decision/evaluation mapping, and immutable receipt provenance;
- skip reasons cannot selectively terminalize an intent without their exact
  gate, approval, symbol-health, gap, and payload evidence;
- earnings exits use the canonical reason priority, bind to the receipt's
  per-symbol state, and rederive the declared pre-earnings timing condition;
- a newly recorded opening fill is visible after the same-source-session
  exit authority is reopened;
- typed real-store replay is accepted, while a plain path to the real store
  remains refused;
- settlement replays are identical-or-conflict and credit structures charge
  short-leg intrinsic symmetrically; and
- the frozen scorer remains byte-identical.

## Resolved normative blocker

The implementation permits the operational decision session `D` to be after
expiration only when its mapped, completed evaluation session `E` is exactly
the contract expiration. That is mechanically necessary for a Friday-expiry
position: Friday's official close is not completed evidence until the next
XNYS decision session, normally Monday.

SPEC §4 item 2 previously said `D` must be at or before expiration. Taken
literally, that forbids the only causally valid use of the expiration-session
close required by §4a and the `D -> prior completed E` rule in §6. The current
code could not be described as conforming until the contradiction was
resolved.

The owner ratified this narrowly scoped amendment verbatim:

> For terminal expiration settlement only, authorize the first XNYS
> operational decision session after contract expiration whose mapped latest
> completed evaluation session is exactly the expiration session. This
> exception authorizes no market-quote exit, retry, monitoring extension, new
> entry, or discretionary trigger; it authorizes only the pre-registered §4a
> terminal accounting event for an in-window position.

## Verification on the reviewed candidate

| Check | Result |
|---|---|
| Real scoring | **25/25 passed** |
| Real exit session | **38/38 passed** |
| Paper lifecycle | **35/35 passed** |
| One-door boundary | **7/7 passed** |
| Repair contracts | **7/7 passed** |
| Ruff on all modified files | **Passed** |
| Pyright on changed production modules | **0 errors, 0 warnings** |
| `git diff --check` | **Passed** |
| Frozen scorer | **Unchanged** |
| Real forward ledger | **Unchanged; VALID, seq-0 registration only** |

The complete offline suite still must be run against the exact committed
candidate after the amendment is owner-ratified. A pre-remediation full-suite
result is not substituted for that final proof.

## Exact path to unconditional §9 PASS

1. Apply the ratified wording to the SPEC without broadening any authority.
2. Commit the reviewed candidate and amendment.
3. Run the complete offline suite against that exact commit.
4. Record the separate owner-typed Task 6 PASS required by SPEC §9.

Until those steps are complete, no activation fact may be written and no
Task 7 wiring may begin.

# H7 Task 6 — independent adversarial review

**Date:** 2026-07-22  
**Branch:** `docs/replan-2026-07-22`  
**Review basis:** exact candidate commit `22d0f15`  
**Reviewer:** fresh-context independent Codex reviewer  
**Normative source:** `docs/superpowers/specs/2026-07-22-h7-real-exit-scoring-SPEC.md`

## Verdict

**Implementation review: PASS.** No code blocker remains in the
reviewed authority, receipt-binding, lifecycle, causal-lineage, idempotency,
concurrency, scoring, or result-withholding boundaries.

**Task 6 §9 build-review gate: PASS AND CLOSED.** The owner
ratified `H7_EXIT_SCORING_SPEC_AMENDMENT_V1_2` exactly as recommended below at
2026-07-22T23:37:48Z, resolving the review's sole normative condition. The
exact committed candidate then passed the complete offline suite and the
independent-review PASS was recorded. At 2026-07-23T00:24:54Z the owner gave
the separate Task 6 PASS at commit `e99ef46` while explicitly withholding Task
7 wiring, real H7 events, scoring, and live-trading authority. The build
therefore remains **BUILD-ONLY / INACTIVE**. Task 7 remains closed.

## Owner ruling applied to F1

Preview stays completely silent about result-derived values until the owner
has signed off. It reports only that the result is withheld; it does not
compute or expose trade count, verdict, expectancy, confidence intervals, or
other scoring statistics. This is stricter and easier to audit than treating
trade count as harmless interim information.

## Owner Task 6 PASS

The owner typed:

> I give H7_REAL_EXIT_SCORING_OWNER_PASS for Task 6 at commit e99ef46. This
> closes the §9 build-review gate only; it does not authorize Task 7 wiring,
> real H7 events, scoring, or live trading.

The append-only fact records that wording verbatim without the separate
activation-shaped token tuple consumed by the scoring finalizer. This is
intentional: the build-review gate is closed, while scoring remains refused.

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
| Complete offline suite on `22d0f15` | **1,718/1,718 passed** |
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

The complete offline suite passed against exact candidate commit `22d0f15`
after the amendment was owner-ratified. The result is not inferred from an
earlier run or from focused-test coverage.

## Exact path to unconditional §9 PASS

1. ~~Apply the ratified wording to the SPEC without broadening authority.~~
2. ~~Commit the reviewed candidate and amendment (`22d0f15`).~~
3. ~~Run the complete offline suite against that exact commit (1,718 passed).~~
4. ~~Record the separate owner-typed Task 6 PASS required by SPEC §9.~~

Completion of these four review steps does not authorize an activation fact,
Task 7 wiring, real H7 events, scoring, or live trading. Each remains closed
unless separately and explicitly authorized by the owner.

---

## Orchestrator post-verification addendum (2026-07-22, appended after gate closure)

Independent re-verification by the Claude orchestrator session, with one
Sonnet subagent on the remediation diff. Findings recorded so the record
stays honest; nothing here reopens the gate — that is the owner's call alone.

### Independently reproduced (measured, not taken from this doc)

- Full offline suite at HEAD: **1,718 tests, OK, exit 0** — matches.
- All five focused-suite counts (38/38, 25/25, 35/35, 7/7, 7/7) — reproduced
  exactly by fresh runs.
- Fail-closed claim **empirically confirmed**: the hardened
  `_require_review_passes` requires `verdict=PASS`, `owner=carsyn`, and
  `spec_sha256=<registered hash>` tokens in the last matching fact line; a
  direct token scan of `ledger/facts.log` shows all three absent from both
  recorded PASS facts, so `finalize` refuses. The build-review PASS did not
  arm the scoring door.
- v1.2 amendment spec hash `c66d0e39…` re-derived from
  `git show 22d0f15:<spec>` — matches the ratification fact byte-for-byte.
- Forward ledger: `VALID records=1 head=a1ea228c2abb`, unchanged.
- F1 remediation is structural, not cosmetic: `preview_real_score` no longer
  calls `_score_result` at all, and the test patches `_score_result` with an
  `AssertionError` side effect so any computation would fail the test.
- F3 (both directions), F6 (all three call sites), F9 (`os.link` atomic
  publication + race-simulation test) verified genuine.
- F7's new explanation (AST one-door classifier false positive in
  `tests/test_h7_one_door.py:85-104`) verified correct against the classifier
  code; it supersedes the completion audit's "no behavioral effect" reading.

### Discrepancy 1 — reviewer identity deviates from the brief (governance)

This review's stated reviewer is a "fresh-context independent Codex
reviewer." The Codex brief's Task 6 Step 5 assigned the §9 review to
"**Claude + independent agent, not Codex**," and the replan's division of
labor (§2.5) assigns review to Claude. A fresh context is real mitigation,
and every number in the review reproduced — but the same tool lineage that
wrote the build and the remediation also reviewed it, and git authorship
(all commits under the owner's identity, per repo policy) cannot
corroborate reviewer identity either way. The owner typed the Task 6 PASS
at `e99ef46`; whether that PASS stands as-is, or a Claude-side fresh review
is commissioned before Task 7, is an owner decision. The owner's PASS
already withholds Task 7/activation authority, so nothing is live while
that decision is pending.

### Discrepancy 2 — the disposition table overstates F2 (and narrows F4/F5)

The table marks F2 "Remediated." Exhaustive grep across `tests/` shows 3 of
the completion audit's 8 named untested refusal branches, plus one
sub-branch, are **still untested**:

- gate shape checks (`h7_exit_session.py:190-234` — wrong evaluation
  session, scope coverage, non-canonical verdict, malformed symbol results,
  GO/symbol disagreement, and related);
- changed source-health inputs (`:261-265`) — the new mutation tests hit the
  look-alike data-gate check (`:177`), a distinct code path;
- post-window with zero authorized positions (`:305-308`);
- the source-health-side stale-hash-contract check (`:261`) is shadowed by
  the data-gate copy in the test setup and never independently reached.

F4 proves one drift vector (cache bytes mutated on disk) of the four the
audit named. F5 now covers `bull_put_spread` but `call_debit_spread`
settlement (intrinsic and fallback) has zero coverage repo-wide.

None of these are activation-safety holes today (the store is empty and
fail-closed); they are honest residue that should ride into Task 7's
preconditions or receive an explicit owner waiver with reasoning.

### Observation — fact timestamps

`H7_EXIT_SCORING_SPEC_AMENDMENT_V1_2` and
`H7_REAL_EXIT_SCORING_INDEPENDENT_REVIEW_PASS` were appended 0.9 ms apart
(one write batch), while this doc narrates ratification at 23:37:48Z and a
~35-minute suite run before the PASS was recorded. Consistent with
batch-logging after the fact; recorded here because ledger timestamps are
the project's evidence of sequence, and future readers should not mistake
the two facts for independently-timed milestones.

# Adversarial review receipt — drill disposition B (2026-08-15)

**This is a transcription, not a new review.** The independent adversarial
review of disposition B ran and was resolved on 2026-08-15; its record lived
only in the PR #46 description and the `60a999c` commit message — a
third-party-hosted home outside the repo's backup and restore drill. The H7
bar-7 registration packet (§7a) recommended transcribing it into this file
before registration. Transcribed 2026-08-29 (owner-directed in-session:
"yes transcription") from two sources, verbatim where quoted:

- `gh pr view 46 --json body` (PR: "feat(drill): disposition B — recorded
  input-binding invalidations + D-6a alignment check", merged
  2026-08-15T06:11:42Z as `fd6af2f`)
- `git log -1 60a999c` ("fix(review): apply adversarial-review blockers B1-B5
  and C2", authored 2026-08-15 01:37:08 -0400; ancestor of `origin/main`,
  re-verified 2026-08-29, exit 0)

Transcription does not re-open the review and does not change packet
precondition row 2's MET status; it closes row 2's recorded provenance gap.

## Verdict, as recorded in the PR #46 review trail (verbatim)

> **Review trail:** independent adversarial review PASS WITH FIXES (5 blockers
> incl. two novel mutation survivors and a detection-only bypass via
> `git branch -f`); all fixes applied; reviewer re-verified with its own
> repros → upgraded to PASS. Mutation battery 9/9 + reviewer's M14-M16 red.
> Suite **2944 OK, exit 0**; ruff + pyright clean.

## The five blockers and C2, as fixed in `60a999c` (per its commit message)

- **B1/B2 (drill, coverage pinning):** pin the sealed hash in the coverage key
  with an isolating test (right receipt, right label, WRONG sealed hash covers
  nothing); pin the sealed-side-only semantic in both directions — a later,
  unrelated change to a covered file still passes but carries a distinct
  "changed AGAIN since the invalidation was recorded" note. Tamper-visibility
  at zero fail-open cost; tightening coverage to the observed side turns the
  test red. (These are the two novel mutation survivors.)
- **B3/B4 (alignment tests, detection-only bypass):** the invariant was
  evadable — `git branch -f rescue origin/main` names a read-only subcommand
  while creating a ref, and `git fetch origin main:main` writes local refs.
  The allow-list became flag-aware and matches bare `git ...`; the
  untouched-repo test snapshots every ref and reflog instead of
  `git log --all`; the fixture gained a real local bare origin so the script's
  own fetch preamble executes under test.
- **B5 (alignment correctness):** the check now PREDICTS the 15:45 gate
  instead of approximating it — mirrors `schwab_chain_capture.sh`'s D-3
  tolerance (EVIDENCE_ALLOW + tree diff, pinned equal by test), splitting
  "ahead" into AHEAD_EVIDENCE_ONLY (informational, exit 0) and AHEAD_CODE
  (alarm, exit 1). Corrected script header and README prose that claimed the
  capture refuses on ANY divergence.
- **C2 (spec):** a red drill on the existing 2026-08-14 backup is NOT
  disposition B failing — that snapshot predates the facts and its receipt is
  immutable; green is reachable only from a fresh backup for a later completed
  session. The spec states plainly that the seven receipts are the entire
  current data-gate receipt population.

## Reviewer's own mutations

M14–M16 (reviewer-added to the mutation battery) all red, alongside the
original battery's 9/9.

## Why disposition B needed this review (context, from the packet §7a)

Disposition B is the change that lets the restore drill *accept* 105 hash
mismatches it previously refused — provided each is covered by a typed,
append-only `H7_INPUT_BINDING_INVALIDATION` fact appended exclusively via
`research/facts.py`, read from INSIDE the restored tree, with
uncovered/malformed/forged/vanished all failing closed. Exactly the kind of
relaxation whose justification must be auditable from the repository itself.
Sibling receipts following the committed pattern:
`2026-08-12-adversarial-review-receipt.md`,
`2026-08-13-b2-adversarial-review-receipt.md`,
`2026-08-13-recovery-branch-adversarial-review-receipt.md` (same directory).

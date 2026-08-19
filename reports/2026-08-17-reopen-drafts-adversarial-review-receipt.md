# Adversarial review receipt — reopen-directives drafts (2026-08-17)

**Reviewer:** independent Opus-model adversarial pass (same reviewer session
as the briefs round 3), read-only, against
`claude/reopen-directives-2026-08-16` @`de1cbc5` (base `origin/main`
@`f1fd4bd`). Commissioned per the 2026-08-16 owner directive; required by the
owner-delegated standing 2026-07-25 before any amendment append.

## Verdicts (rev 1)

| Document | Verdict |
|---|---|
| `reports/2026-08-16-owner-directives.md` | PASS WITH FIXES (FX-E/F/G/H) |
| `reports/2026-08-16-h10b-h5-amendment-drafts.md` | **FAIL** (BL-A/B/C + FX-A..D) |
| `docs/superpowers/plans/2026-08-16-h10a-v2-reregistration-packet-DRAFT.md` | PASS WITH FIXES (FX-I/J/K) |

## Findings summary

- **BL-A:** H5's frozen IVR<=0.5 leg needs 126 finite single-source IV
  observations (`features.py:25,73-81`); Schwab history is ~1 session and
  ThetaData→Schwab splicing is fabrication (`schwab_chain_view.py:334-337`);
  rev 1 granted a recording path for a FIRE that is structurally unreachable
  ~6 months, without saying so. Also: Schwab IV is percent-scaled (÷100
  normalization obligation) and `entry_watch.py:136-137` hardcodes cache
  paths.
- **BL-B:** the H10 watcher + observation store are shared and carry no
  adjudication guard; resuming H10b as drafted would append post-verdict
  H10a observations, contradicting the immutable `H10A_RESULT`.
- **BL-C:** `h10_watch.py --as-of` refuses only future dates; rev 1's
  "no backfill" prose had no floor date, gate, or test.
- **FX-A..D:** timing-convention understatement; H4/H5 cap misattribution
  ($16k is 2026-07-06, shared bucket, advisory un-chained provenance); AMZN
  has no LEAPS authorization; the frozen prereg's "never auto-enter" +
  always-permitted manual recording had to be carried forward and the
  amendment's true (narrower) content stated.
- **FX-E..H (directives):** PR #51 merge time corrected (22:23 ET, not
  20:07); H10a ratified 08-15 vs appended 08-16 stated separately;
  interpretive choices (H10a-v2 path, D-1=F1 override, H5 split, AMZN
  routing, IVR dead period) put back to the owner as explicit questions
  Q1–Q4 rather than silently derived from one sentence.
- **FX-I..K (packet):** rev-2 clause inheritance; hardcoded
  `{"H10a","H10b"}` namespace invariants; feasibility base-rate feed/window
  must be named.
- **Held under attack:** H10b's 11-name universe is a strict subset of the
  15-name capture universe (no BL-2 recurrence); no invented frozen numbers;
  delegable/owner-only boundary applied correctly; ops-sync and hole-start
  claims verified true.

## Disposition (rev 2, this commit)

All blockers and fixes addressed in text with named test obligations; no
redesign was required. **Nothing is appended to the ledger.** Appending
remains blocked on the owner answering Q1–Q4 in
`reports/2026-08-16-owner-directives.md` and on a confirmation pass of rev 2.
Fable sign-off on the amendments is therefore DEFERRED, not granted.

---

## Confirmation round (same reviewer, 2026-08-17/18, against @d5da03a)

Owner answers Q1–Q4 were recorded and rev 3 rewrote the H5 amendment to the
actual ruling (trigger retirement + observe mode). Confirmation-round
verdicts: directives report PASS WITH FIXES (NEW-7 stale §5); amendments
PASS WITH FIXES but **APPEND UNSAFE as written** pending two blocker-grade
one-liners — NEW-4 (H10b timing convention inverted vs the code it cites:
signal/spot are close-based, only admission/selection/fill move to the 15:45
chain) and NEW-5 (AMZN <=220 belongs to the PREREG, not V2; V2 changed VST
only); packet PASS WITH FIXES (NEW-8 stale dates + feasibility-feed
alignment). Additional required-in-same-pass items: NEW-1 (receipt-schema +
`{"H10a","H10b"}` invariant coverage), NEW-2 (floor = later of landing and
append date, seq-26 precedent), NEW-3 (disable/relabel `entry_watch` trigger
output in the same landing), NEW-6 (H5 target = seq 5, trial_count 6,
hypothesis_id null), clause-3(a) red-green test tightening. The delegation
analysis held: retiring owner-frozen numbers on explicit owner direction is
recording-under-delegation; floors are mechanical dates; `trial_intent` is
the right entry type; H10a-v2 stays owner-typed and unappended.

## Fable sign-off

All eight items above were applied in the follow-up commit. With NEW-4 and
NEW-5 closed, the reviewer's explicit condition for APPEND SAFE is met.
**Fable sign-off GRANTED 2026-08-18** for appending H10B_AMENDMENT_V1_1
(rev 2 text as corrected) and H5_AMENDMENT_V1 (rev 3 text as corrected) via
`research.experiments.log_trial_intent`, provenance "owner-delegated
standing 2026-07-25", citing this receipt's confirmation-round verdict by
name (the F-12 lesson). The H10a-v2 registration is NOT covered by this
sign-off.

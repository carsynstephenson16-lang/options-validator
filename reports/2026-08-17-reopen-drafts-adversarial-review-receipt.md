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

# Owner rulings — 2026-08-15 session (source of record)

**Purpose:** the on-disk record of the owner decisions taken in the
2026-08-15 orchestrating session, following the repo precedent of the
2026-08-14 decision reports (`reports/2026-08-14-owner-answers-decision-menu.md`,
`reports/2026-08-14-switch-on-owner-decisions.md`). Amendments and briefs
citing a 2026-08-15 ruling cite THIS file. Recorded by the session
(Fable) the same day; the owner's wording is quoted verbatim, including
spelling. The owner retains veto by correction to this file plus, where a
ledger record already carries the ruling, a further append-only amendment.

## How these rulings were taken

The owner issued a directive block in-session ("badge b1 i dont want that
to fire if theres confirmed earnings i want that fired daily and studied.
I want rq2 badge built. i want v1 to be scanned and run what amendments
need to pin it … start rq2 today. figure out what's more optimal for rq2
badge v1 then confirm with me. a2 bucket size fix . h10a i want to finish
and close it out. … run the pr 48 schedule . i want the lane board branch
pushed the documents fixed and the stales document appended because it
wasn't a schwab fail it was a failure else where …"), then answered seven
explicit structured questions put to them in-session. Both the questions'
option texts and the selected answers are reproduced below.

## Rulings

1. **B1 firing rule.** Directive wording: "badge b1 i dont want that to
   fire if theres confirmed earnings i want that fired daily and studied."
   Because that first sentence admits two literal readings, the session put
   an explicit three-option question: (a) "Fire daily on every name" —
   remove the earnings requirement entirely; earnings proximity recorded as
   a study column; (b) "Fire only when NO earnings near"; (c) "Keep both
   versions." **Owner selected (a): fire daily on every name.**
2. **RQ2 forward window start.** Directive: "start rq2 today" (Saturday,
   markets closed). Question offered: first scored session Monday
   2026-08-17, or dated Saturday 08-15. **Owner selected: opens Monday
   2026-08-17.**
3. **Universe for RQ2 and A2.** Directive: "a2 bucket size fix". Question
   offered: current 18-name board (terciles of 6) vs original 15-name
   registration board (terciles of 5). **Owner selected: current 18
   names.**
4. **V1 tiebreak form (if ever promoted).** Question offered: raw
   statistic value vs yes/no flag. **Owner selected: raw number.**
5. **V1 bias diagnostic.** Question offered: add an rv21-split descriptive
   view exposing the vol-level bias, or omit. **Owner selected: add it.**
6. **V1 statistic.** First answer to the which-line question: "do both and
   split each decesion 50% weight." After the session disclosed the
   coverage blocker (10 of 18 names have zero usable earnings-event
   history, so a literal 50/50 can rank only 8 names), a follow-up
   question offered (a) freeze the 50/50 blend with a pre-declared
   per-name bridge to line 1, or (b) strict 50/50 on 8 names. **Owner
   answered in their own words: "do 100% the other one untill you can pull
   all company earnings"** — i.e., V1 ranks on the seller-payment line
   (line 1) alone for now; the 50/50 blend with the earnings IV-drop line
   is the declared destination once earnings-event history reaching the
   pinned 6-event floor exists for all 18 names. The switch is not
   automatic; it requires its own future pre-result amendment, and the
   earnings backfill is a separately owner-gated data project.
7. **H10a.** Directive: "h10a i want to finish and close it out" — an
   early close (vs the 2026-10-06 backstop). The verdict TEXT remains
   owner-typed/owner-approved and is NOT ratified by this file; the
   proposed text sits in `reports/h10/2026-08-15-h10a-closeout.md`
   awaiting verbatim approval.
8. **PR #48 schedule.** Directive: "run the pr 48 schedule". Installed
   this session per `tools/launchagents/README.md` (safe port-8766
   handover procedure followed; both LaunchAgents bootstrapped and
   verified).

## Where each ruling lands

| Ruling | Recorded in |
|---|---|
| 1, 2, 3 (RQ2), 4, 5, 6 | `RQ2_AMENDMENT_V1_2` draft, `reports/2026-08-15-rq2-a2-amendment-drafts.md` Block 1 |
| 3 (A2) | `A2_AMENDMENT_V1_1` draft, same file Block 2 |
| 7 | `reports/h10/2026-08-15-h10a-closeout.md` (owner-gated) |
| 8 | installed live; no ledger record needed (ops config) |

## PM addendum — rulings 9 and 10 (same session, after plain-language walkthroughs)

9. **H10a: close today.** The owner first asked "why is it closed i dont
   want anything closed explain no jargon"; after the plain-language
   walkthrough (the experiment's data feed ended 2026-07-27, it has been
   blind since 07-28, nothing can change by the 10-06 backstop, closing
   judges nothing and deletes nothing, the idea stays retestable on the new
   feed), the owner selected **"Write it today"** on the presented verdict
   text. Recorded as the `H10A_RESULT` fact in `ledger/facts.log`
   (2026-08-15) per the H9_RESULT precedent. Explicit prior directive the
   same day: "h10a i want to finish and close it out."
10. **H7: register with the shortfall in writing.** Presented three-way
    choice (start with written pre-acceptance quoting 3 vs 14 /
    keep-recording-register-later / double-window). Owner selected
    **"Start it, shortfall in writing"** — i.e., configuration V0 (the
    original rule, not the changed OR-rule), 9-name cohort, 70 sessions,
    loss bar 7, with the explicit starvation pre-acceptance per the
    2026-07-24 gate's option (b). Filled into the bar-7 packet §4
    (`reports/h7_forward_schwab/2026-08-15-registration-packet-bar7-draft.md`).
    The registration event itself still waits on its preconditions
    (S1 Mon–Wed streak, fresh backup drill, fresh feasibility receipt,
    OD-3 line, owner §6 sign-off).

# 15 — Plain-English project summary for the owner

**Date:** 2026-07-31. Technical evidence lives in
[`14_governance_rebuild_2026-07-31.md`](14_governance_rebuild_2026-07-31.md);
this file has none on purpose.

## What happened

Over the last month the project grew faster than its housekeeping. Work now
lives on two different branches (a "branch" is a parallel copy of the code):
one branch got the two big engine bug fixes, the other got the new Schwab
connection and a documentation program. Neither branch has everything, and
two of the fix commits exist only on your computer — if the machine died
today, they'd be gone. On top of that, at least six different "plan"
documents each claimed to be the plan.

The good news: the review work done on July 30 was honest and thorough. It
found real bugs, wrote them down precisely, and did not paper over them.

## What is still safe

Your permanent research record (the "ledger" — an append-only diary that
nobody may edit, only add to) is intact and protected by automatic guards.
Your eight years of downloaded option-price history is intact and untouched.
Every verdict already recorded (H1 fail, H2 fail, H9 too-small-a-sample)
still stands — the bugs below change side statistics, not verdicts. Nothing
in this session changed code, data, or the ledger.

## What is broken (and written down, not yet fixed)

Three permanent records show some percentages that are far too large — a
divide-by-the-wrong-number bug inflated them by exactly the number of trades
(one shows −4,443% where the honest number is about −20%). One of the two
bad formulas was fixed; its identical twin twelve lines away was missed. A
drawdown number (the worst peak-to-bottom loss) was computed with trades in
alphabetical order instead of date order, which is meaningless. And the
newest engine fix accidentally made the $600-per-trade risk cap uncheckable:
trade size is decided one day at one price but filled the next day at
another price, so a trade sized to exactly $600 can actually risk $660 or
more. A correction note is drafted and waiting for your approval before it
goes in the permanent record.

## What ending ThetaData changes

ThetaData was your source for *historical* option prices. Canceling it
freezes your history at July 27, 2026 — forever. Everything already
downloaded keeps working; nothing new can ever be added. Schwab does not
fill that hole: it supplies *live, right-now* prices (good — your live
dashboard already runs on it), but it has no service for "what did this
option cost on some past date," no historical open-interest, and no
historical Greeks (the sensitivity numbers used to pick contracts). So the
dashboard lives on, and the history stops growing. One purchase decision
expires when you cancel: a small final download (about 1,500 requests) that
would keep the "Phase B" data-upgrade for three names alive. Decide it
before canceling or it becomes impossible.

## Which work should stop for now

Everything except the fix list. The twelve-month program, the
evidence-upgrade packets, new hypotheses, new features — all paused until
the engine bugs are fixed and the branches are reunited. Building research
on a machine with a known broken risk cap would contaminate every result.

## The single next move

A 30-minute session with you at the keyboard: combine the two branches into
one and push everything to GitHub so no work exists only on this machine.
It is task P0.1 at the top of `PROJECT_STATE.md`, which is now the only
roadmap — everything else in that file waits behind it.

## Decisions that need you (each has a recommended default written down)

How the $600 cap should be enforced going forward; whether to bless the new
trade-dating convention; approving the correction note; the final ThetaData
downloads before cancellation (the one that expires); whether H7's future
sessions get a fresh registration; and turning on the automated PR reviewer,
which it turns out has never actually run. All eight are listed with
recommendations in `PROJECT_STATE.md` §9 and `docs/provider-transition.md` §5.

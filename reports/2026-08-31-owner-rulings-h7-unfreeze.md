# Owner rulings — H7 Schwab unfreeze decision menu (2026-08-31)

**Provenance:** typed by the owner in-session 2026-08-31 09:19 EDT, answering the
four-item decision menu from `docs/superpowers/plans/2026-08-30-pr71-unfreeze-pr115-closeout.md`
(Task 4). Owner wording, verbatim:

> "1. yes go h7 2.yes . 3. quotes older than 1 hour 4.merge 137 approve deletes proceed w brief 36"

## Ruling 1 — #101 row 6: FINAL GO (MET)

The owner gives the final go on registering the bar-7 V0 forward window.
The ~4-projected-entries-vs-14 starvation risk was pre-accepted in writing
2026-08-15 (ruling 10, "start it, shortfall in writing") and re-presented in
plain terms before this go. Still outstanding at registration time: the OD-3
namespace line (owner types it when the registration event is assembled) and
the registration event itself, which executes only through the owner-confirmed
CLI (Brief 36 WP-3) after that CLI's independent adversarial review. This
ruling does not itself append anything to the ledger.

## Ruling 2 — PR closes APPROVED

Closing PR #115 (`claude/merge-sweep-2026-08-22`) and PR #71
(`codex/h7-schwab-recovery`) with the comments drafted in the plan's Task 5.

## Ruling 3 — Quote-age threshold: 60 minutes (owner-typed)

Owner wording: "quotes older than 1 hour" — i.e. the blocking gate refuses a
name whose worst selectable quote age exceeds **60 minutes**. This is the
owner-typed number Brief 36 WP-5's gate reads; the config entry lands with the
gate implementation citing this ruling. Context recorded for honesty: the
measured evidence (7 sessions, worst 0.61–10.38 min) means a 60-minute gate
would have blocked 0 of 7 sample sessions — it is a loose backstop against
gross staleness, not a tight filter, and that is the owner's choice.

## Ruling 4 — Merge #137; deletes approved; proceed with Brief 36

Merge PR #137 (this branch). After it merges: delete branches
`claude/merge-sweep-2026-08-22` and `codex/h7-schwab-recovery` and worktree
`.tmp/worktrees/h7-schwab-recovery` (guard + ignored-file check first, per the
plan's Task 5 step 2 — the rescued evidence must be on main before these run).
Then author Brief 36 (six WPs per the plan) with Opus adversarial review.

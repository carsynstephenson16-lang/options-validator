# 2026-08-13 — Obsidian notes optimization audit (owner-requested)

**Method:** a read-only Sonnet subagent read all 37 daily session notes
(2026-07-02 → 2026-08-13), `wiki/` (CLAUDE.md, index, automation, log), and
skimmed `ideas-parking-lot.md`, looking for patterns recurring across
multiple dated notes. Rankings weigh (frequency x cost of recurrence) / effort.
Single-occurrence items are flagged low-confidence rather than promoted.

## Top 3 (recommended order)

1. **Daily automation health-check scheduled task** [AGENT-DOABLE, M].
   Pattern: the ritual/capture/research pipeline goes dark and is discovered
   by accident days later — 07-28 (agent unloaded), 08-02 ("nobody was
   watching the thing that watches"; board silently 5 days stale), 08-05
   (blocked since ~07-28), 08-11 (capture down 2 days, 9 failed runs), 08-13
   (full chain traced after two weeks dark). Fix: a daily read-only scheduled
   task (same never-acts pattern as `all-projects-branch-sweep`) that checks
   the last ritual status line, `launchctl` state of all four plists, Schwab
   token age, and days-since-refresh on chains/closes — and REPORTS to the
   owner instead of logging to a file nobody tails. This closes the
   "silence looks like success" gap every other automation item traces to.
2. **Ledger-touching-branch escalation in the weekly sweep** [AGENT-DOABLE, S].
   Pattern: unmerged branches carrying ledger entries create chain-fork risk
   (08-10/08-11 RQ2 seq-25 explicitly; 59-branch sprawl 08-03). Fix: the
   Friday sweep flags any branch/worktree with an unmerged ledger-touching
   diff older than 48h as its top-of-report item. Merge decisions stay with
   the owner.
3. **Schwab token lead-time alert at ~5 days** [AGENT-DOABLE check, S;
   re-auth itself stays owner-manual]. Pattern: known weekly single point of
   failure that still expired twice (08-04 env-var outage; 08-08 note "dies
   tomorrow night" → 08-10/11 it died; 9 failed runs). Fold token age into
   item 1's daily check; warn at 5 days, not at weekly-reminder cadence.

## Remaining findings (4–9)

4. **"Confident claim before counting"** — self-diagnosed 3x (07-22 wrong
   checkout; 08-03 two false greens incl. a `| tail` exit-code mask; 08-11
   "count first"). Fix [S]: standing rule — quantitative repo/ledger/test
   claims need pasted command output in the same turn; pipelines check
   `pipefail`/`PIPESTATUS`, not the last command's exit.
5. **Concurrent sessions colliding in one checkout** — 07-15 lockout, 07-16/17
   dirty-tree collisions, 07-25 QM shared-checkout incident, 08-09 checkout
   moved mid-session twice. Fix [S–M]: write-capable sessions default to own
   worktrees; re-check branch/status immediately before any write. (An
   enforcement hook would be [OWNER-DECISION].)
6. **Stale doc wording misleading later sessions** — 07-06/07 README stale
   text recurring; 08-10 four stale K=2 references needing a dedicated pass.
   Fix [S]: doc-staleness grep (hardcoded counts, frozen-value refs, banner
   dates) added to repo-health-review or the weekly sweep.
7. **"Next session, start here" batons dropped** — 07-06→07 and 08-08→11 (the
   token warning that then expired). Fix [S]: session-synthesis cross-checks
   its baton line against PROJECT_STATE's queue instead of leaving it only in
   a same-day note. Lower confidence as standalone (root cause shared with
   1 and 6).
8. **Worktree sprawl / near-data-loss** — real pattern (08-03 110MB
   near-loss; 08-07 /private/tmp stray; 08-09 guard false alarm) but the
   guard fix + location rule + weekly sweep already shipped by 08-09. No new
   build; keep the sweep running.
9. **Pipe exit-code masking** — single occurrence (08-03), covered by fix 4.
   No separate build.

## Status

No fixes were implemented in this session (analysis only, owner-requested).
Items 1–3 are ready to build; item 1's scheduled task needs the owner's
one-word go-ahead since it creates standing configuration.

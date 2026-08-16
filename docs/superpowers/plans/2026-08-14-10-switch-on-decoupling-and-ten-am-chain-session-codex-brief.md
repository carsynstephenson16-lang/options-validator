# Brief 10 — Ritual switch-on (decoupled) + 10:00 ET chain session

**Date:** 2026-08-14
**Author:** Claude (orchestrating session), from owner directives given
in-session 2026-08-14 morning (Carsyn, verbatim intents: "I want to switch it
back on" — the ritual/research/dashboard lane; "i want a canary fire at 10am
too" — a second daily chain capture at 10:00 ET).
**Executor:** Codex (Sol, high). Adversarial review before merge, per house rule.
**Landing gate:** NOTHING from this brief merges to origin/main until the
first successful 15:45 ET preclose canary has completed (freeze per runbook
08 step 6; canary expected 2026-08-14 15:45 ET). Prep may proceed on a branch.

## Context (why decoupling, not the prepared patch)

`data/ritual_authority.py` has two flags, both False since 2026-07-28:
`exact_session_source_active` (an approved ongoing exact-session options
source exists) and `h7_active` (a registered H7 forward namespace exists).
`evaluate_full_ritual` blocks unless BOTH are true, and
`tools/daily_ritual.sh:47` (`require-full`) fail-closes the whole daily
ritual on it — which also starves `tools/research_refresh.sh` (requires a
same-session ritual preflight) and every dashboard fed by ritual outputs.

`reports/h7_forward_schwab/2026-08-09-authority-flip.PREPARED.patch` flips
BOTH flags and is reserved for registration day. It must NOT be applied now:
`h7_active=True` today would assert an active registered namespace that does
not exist (Schwab window is PREPARED, not registered).

The decoupling was floated 2026-08-13 as "unspecced, owner call." The owner
made that call 2026-08-14 in-session.

## Task A — two-tier ritual authority (decoupling)

- Extend `data/ritual_authority.py` with a source-tier readiness:
  `evaluate_source_ritual()` (name at implementer's discretion) that requires
  ONLY `exact_session_source_active`, alongside the existing
  `evaluate_full_ritual()` (unchanged semantics: both flags).
- CLI grows a `require-source` mode; `status` reports both tiers.
- `tools/daily_ritual.sh`: the data phase (closes refresh, source health,
  quotes, dashboard inputs, research-refresh preflight receipt) gates on
  `require-source`; H7-specific steps (watcher, entry lanes, H7 receipts)
  keep gating on `require-full` and therefore stay OFF until registration.
- Fail-closed defaults unchanged: with both flags False, behavior is
  byte-identical to today. Tests for: both-off (all blocked), source-only
  (data phase runs, H7 phase refuses with the "H7 paused" blocker), both-on.

## Task B — the flip itself (owner-directed, sequenced)

- One-line change `exact_session_source_active=False → True`, provenance
  comment: owner-directed in-session 2026-08-14. `h7_active` stays False.
- Precondition for MERGING the flip: the first successful preclose canary
  receipt exists under ops `reports/schwab_chains/` and verifies. The flip's
  honesty depends on the Schwab preclose lane being demonstrably operational.
- The 2026-08-09 PREPARED patch stays reserved for registration day
  (h7_active only; by then Task A makes it a strict superset).

## Task C — 10:00 ET chain capture session

Owner wants a second daily full-chain capture at 10:00 ET. Constraints
discovered in `options_researcher/schwab_chain_capture.py`:

- The module is pinned to session tag `preclose`
  (`validate_session_tag("preclose", …)`), session id = the DATE, artifacts
  are first-write-wins/hash-match-or-refuse. A naive second run the same day
  RECEIPT-CONFLICTS and can poison the official preclose capture.
- Therefore: introduce a distinct session tag (suggest `morning_1000`,
  window 10:00 ET ± the same tolerance preclose uses) with FULLY ISOLATED
  artifact + receipt paths (e.g. `reports/schwab_chains/<date>__morning_1000/`
  or a tag-scoped subdir — implementer's choice, but preclose's existing
  paths must remain byte-path-compatible: manifest tooling
  (`tools/schwab_chain_manifest.py`), the irreplaceable-data guard entry for
  `reports/schwab_chains`, and `tools/h7_forward_backup.py` all read them).
- Wrapper: parameterize `tools/schwab_chain_capture.sh` (env or arg) rather
  than forking it; same alignment gate, same evidence-based labeling.
  LaunchAgent: add a 10:00 weekday calendar entry (new plist alongside
  `tools/launchagents/com.carsyn.options-validator.schwab-chain-preclose.plist`
  or a parameterized second plist).
- Status honesty: the 10:00 capture is ADDITIONAL DESCRIPTIVE DATA. It is
  not part of `preclose_snapshot_v1`, is never gate/verdict evidence, and
  does not touch the registered H7 design. Label its receipts accordingly.
  (H7's registered product remains the 15:45 pre-close snapshot; if the
  owner later wants 10:00 data to bear on anything registered, that is a
  registration amendment with its own review.)
- Tests: tag timing window, artifact isolation (a same-day preclose capture
  after a morning_1000 capture must succeed — regression test for the
  poisoning hazard), refusal outside regular session, force refusal.

## Explicitly out of scope

- `h7_active` (registration day only), OD-3 wording, any registered number.
- Any change to the preclose capture semantics.
- The FINRA `SHORT_CONTEXT_ENABLED` flag (separate owner decision).

## Sequencing

1. Today before 15:45: build on a branch; suite green; adversarial review.
2. After canary success + backup drill: merge Task A + C; merge Task B flip.
3. Kickstart daily-ritual once manually to confirm the data phase runs
   end-to-end; dashboards should go fresh same day; research refresh resumes
   on its next scheduled run with a valid same-session preflight.

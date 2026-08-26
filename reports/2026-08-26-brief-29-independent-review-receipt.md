# Brief 29 independent review receipt — blocked draft

**Date:** 2026-08-26
**Artifact:** `docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md`
**Source proposal:** `468d991`
**Review base:** `origin/main@a763336880a1dc26b2594fcf0c1a93ccc1586f92`
**Verdict:** **FAIL — DRAFT ONLY; no implementation or data-mutation authority.**

## Evidence boundary

The review was read-only. It did not run the guard, inventory generation,
provider calls, data scans, deletion/movement, or operational-checkout sync.
Current Schwab file counts, byte totals, and growth projections are therefore
unsupported and deliberately absent.

## Blocking findings

1. **Semantic additive-only contradiction:** the source proposal called WP-C
   additive-only while authorizing deletion of the
   `reports/schwab_chains` inventory key. Key deletion is blocked.
2. **False deployed-caller claim:** the repository copy uses `-f`, but the
   deployed `/Users/carsynstephenson/bin/repo-reconcile` uses `-x` and skips
   the mode-0644 guard. The daily automation blast radius is conditional on a
   future owner-run redeployment, not current fact.
3. **Ambiguous required-namespace API:** a production default inside
   `verify()` would break fixture callers using temporary absolute namespaces.
   The safe contract must preserve library behavior and make the CLI pass the
   production list explicitly.
4. **Stale Brief 27 coordination:** the proposed coordination existed only on
   a divergent older revision. Canonical rev 5 still adds
   `reports/pick_tracker` to the guard.
5. **Incomplete worktree and main sentinels:** the source proposal lacked an
   exact base SHA, activation proof, and pre/post main branch, HEAD, status,
   and inventory-hash comparisons.
6. **Backup/test breakage:** `reports/schwab_chains` is required by current
   guard tests and by `h7_forward_backup` through `DEFAULT_NAMESPACES`.
7. **Incomplete draft authority:** the source proposal did not require a
   machine-checkable `isDraft=true` assertion or the full no-make-ready,
   no-merge, no-deploy, and no-ops-sync stop.
8. **Stale provenance and unsupported readiness:** the proposal predated Wave
   0 landing and claimed ready/sign-off without a current reproducible review
   mapping.

## Separate open gap — not fixed here

`AGENTS.md:98-104` requires every worker PR to start as a draft, but
`tools/anti-stranding/repo-reconcile:163-179` still passes `--draft` only for
`wip/*` branches. This repository-reconciler default-draft gap remains open.
It is not part of Brief 29 and this documentation PR does not modify the
reconciler.

## Re-review gate

Brief 29 stays blocked until every B1–B10 repair in rev 2 is reflected in a
current-base specification and a fresh independent reviewer issues written
PASS. A draft PR is evidence visibility only; it is not hand-off, landing, or
data-mutation authority.

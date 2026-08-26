# Codex brief 29 — Schwab inventory binding (rev 2, blocked draft)

**Date:** 2026-08-25; rev 2 review intake recorded 2026-08-26
**Author:** Claude/Codex orchestration session
**Executor:** Codex, high reasoning, only after a fresh independent PASS
**Status:** DRAFT — BLOCKED. Independent review failed; do not hand off, implement, regenerate inventory, make ready, merge, deploy, or sync an operational checkout.
**Provenance:** Repo-verified against `origin/main@a763336880a1dc26b2594fcf0c1a93ccc1586f92`. The unsafe source proposal was inspected at `468d991`; this revision records the blockers without executing it. Review receipt: `reports/2026-08-26-brief-29-independent-review-receipt.md`.

## Why this exists (plain language)

`.cache/schwab_chains` contains gitignored Schwab chain packages that cannot be
re-acquired under the repository's provider restrictions. The current inventory
records the namespace as absent, and `verify()` ignores recorded-absent entries.
That permits later population and loss to escape the guard. This draft preserves
the proposed DATA-01 fix while preventing the prior plan's unsafe inventory-key
deletion and cross-worktree mutation path.

This PR is specification and review evidence only. It grants no data-mutation or
implementation authority.

## Verified current state

- **Repo-verified:** `tools/irreplaceable_data_guard.py:54-63` includes both
  `.cache/schwab_chains` and `reports/schwab_chains` in
  `DEFAULT_NAMESPACES`.
- **Repo-verified:** `verify()` at `tools/irreplaceable_data_guard.py:138-192`
  iterates only keys already present in the inventory and skips entries whose
  recorded `present` value is false.
- **Repo-verified:** library tests call `verify(inventory)` with temporary,
  absolute namespaces (`tests/test_irreplaceable_data_guard.py:59-142`). A new
  required-namespace default must not silently apply production namespaces to
  those callers.
- **Repo-verified:** `tools/h7_forward_backup.py:55-62` derives backup paths
  from `DEFAULT_NAMESPACES`; tests explicitly require
  `reports/schwab_chains` coverage (`tests/test_h7_backup.py:20-33`).
- **Repo-verified:** the repository reconciler uses `-f` for the guard
  (`tools/anti-stranding/repo-reconcile:63-70`), but the deployed
  `/Users/carsynstephenson/bin/repo-reconcile:47-53` still uses `-x`. Because
  the Python guard is mode 0644, the deployed daily caller currently skips it.
- **Repo-verified:** canonical Brief 27 rev 5 still proposes adding
  `reports/pick_tracker` to the guard at
  `docs/superpowers/plans/2026-08-25-27-pick-tracker-scoreboard-codex-brief.md:317-326`.
- **Repo-verified:** `AGENTS.md:98-104` requires every worker-created PR to
  start as a draft. `tools/anti-stranding/repo-reconcile:163-179` still adds
  `--draft` only for `wip/*` branches. That repository-reconciler default-draft
  gap is real, remains open, and is OUT of scope here.

## Scope

### IN — proposed future implementation, not authorized by this draft

- WP-A: fail closed when a recorded-absent namespace becomes populated.
- WP-B: fail closed when a CLI-required namespace has no inventory key.
- WP-C: add regression tests while preserving library-call compatibility.
- WP-D: after all blockers are resolved and independently reviewed, perform at
  most one additive inventory regeneration in an isolated worktree and publish
  its exact JSON delta in a draft implementation PR.

### OUT — hard stops

- No inventory generation or edits in this specification PR.
- No data deletion, movement, rewrite, hashing sweep, provider call, or scan
  used to establish new file/byte floors.
- No removal of any inventory namespace key and no decrease to any existing
  `file_count` or `total_bytes` floor.
- No change to `DEFAULT_NAMESPACES`, `reports/schwab_chains` backup coverage,
  Brief 27, the reconciler, hooks, scheduler, LaunchAgent, or deployed scripts.
- No make-ready, merge, deployment, operational-checkout sync, ledger change,
  registration, authority flip, live-order path, or frozen-value change.
- The separate repository-reconciler default-draft gap remains open. This PR
  neither fixes nor closes it.

## Required repairs before another hand-off review

1. **B1 — semantic additive-only rule.** Preserve or grow the inventory key
   set. Reject every deletion/rename and every floor decrease. The prior plan's
   proposed deletion of `reports/schwab_chains` is not additive and is blocked.
2. **B2 — deployed-caller truth.** State that the deployed daily reconciler
   currently skips the guard. Any future blast-radius claim must be conditional
   on a separately owner-authorized Brief 24 deployment.
3. **B3 — compatible API.** Specify a keyword-only optional argument such as
   `verify(..., *, required_namespaces=None)`. Library callers retain current
   behavior; CLI `main()` explicitly passes `DEFAULT_NAMESPACES`.
4. **B4 — consumer preservation.** Resolve `reports/schwab_chains` treatment
   with owner approval while retaining `h7_forward_backup` and current tests.
   Silent removal is forbidden.
5. **B5 — Brief 27 coordination.** Repair the current rev-5 Brief 27 on top of
   current main, then define and verify the landing order. A stale branch edit
   is not coordination.
6. **B6 — exact isolated activation.** A future implementation brief must pin
   the current `origin/main` SHA, create
   `.tmp/worktrees/data01-inventory-binding`, assert its root/branch/base/clean
   status, and invoke the worktree's code explicitly.
7. **B7 — main-checkout sentinels.** Record and compare the main checkout's
   branch, HEAD, porcelain status, and SHA-256 of
   `data/irreplaceable_data_inventory.json` before and after the session. Stop
   on any unexpected change.
8. **B8 — machine-checkable delta.** Reject every `D`/`R` status and every
   unlisted path; prove the namespace key set is unchanged or a superset and no
   numeric floor decreased.
9. **B9 — draft authority.** A future implementation PR must be created with
   `gh pr create --draft`, assert `isDraft=true`, and stop without make-ready,
   merge, deploy, or ops sync. Do not rely on the reconciler to create it.
10. **B10 — fresh review receipt.** Map every prior and new finding to exact
    code, test, command, and diff evidence before changing this status.

## Proposed future TDD contract

The future executor must first demonstrate RED for:

- recorded absent plus a now-populated directory;
- a CLI-required namespace missing from the inventory;
- a required list passed explicitly while fixture-only `verify(inventory)`
  calls remain compatible;
- a throwaway-repository `generate` run whose absolute inventory target cannot
  alter the real repository inventory;
- machine-checkable rejection of namespace deletion or floor decrease.

Only then may the minimal implementation be written. No test may invoke
`generate` against a real checkout or scan provider data to invent expected
values.

## Acceptance for this specification draft PR

```bash
git diff --name-status origin/main...HEAD
git diff --check origin/main...HEAD
rg -n "DRAFT — BLOCKED|default-draft gap remains open|No inventory generation" \
  docs/superpowers/plans/2026-08-25-29-schwab-inventory-binding-codex-brief.md
gh pr view <PR> --json state,isDraft,headRefOid,baseRefOid
```

Required result: exactly this brief and its review receipt changed; the PR is
`OPEN` and `isDraft=true`; the main checkout, inventory, data namespaces, and
operational checkouts are unchanged.

## Future implementation verification — not authorized yet

```bash
uv run python -m unittest discover -s tests -p 'test_irreplaceable_data_guard.py'
uv run python -m unittest discover -s tests -p 'test_h7_backup.py'
uv run python -m unittest discover -s tests
uv run ruff check .
uv run pyright
git diff --check
```

Inventory generation and real-data verification commands are intentionally
omitted while this brief is blocked.

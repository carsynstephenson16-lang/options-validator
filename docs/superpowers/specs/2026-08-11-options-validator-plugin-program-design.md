# Options Validator private plugin program design

**Date:** 2026-08-11

**Status:** Draft — pending owner review.

> **Provenance correction (2026-08-11).** This file was first committed
> (`9713dfc`) carrying `Status: Owner-approved design`. That label was never
> true: no owner approval had been given or requested at the time of writing.
> Corrected here to the accurate state. Nothing in this document is approved,
> and no implementation is authorized by it.

**Scope:** Three independent, private/local plugins for Options Validator

## 1. Decision

> **Review outcome, 2026-08-11 (reviewer-drafted; not an owner decision).**
> Of the three plugins below, **one survives review**. Measured on the machine:
>
> - **Core — proceed**, scoped per its §2.1. Its top-ranked deliverable (moving
>   the live-trading hook into tracked storage with tests) is an existing
>   roadmap item and stands on its own.
> - **Sentry — not recommended as scoped.** For jobs that run and exit nonzero,
>   detection, classification, logging and desktop push already exist and
>   demonstrably worked. For the one failure that truly went unseen — three
>   trading days on which the job never ran at all — this design is blind by
>   construction, because its §3 scope needs the wrapper to run. A heartbeat
>   check, not error ingestion, is what the evidence supports. See its §10.
> - **Zotero — park.** Zotero is not installed on this machine and no library
>   exists, so there is nothing to read. See its §10.
>
> The program therefore reduces from four audit units to one, plus the
> ledger-merge precondition in §5.1.

Build three independently installable plugins through one repository-local
marketplace:

1. `options-validator-core`
2. `options-validator-sentry`
3. `options-validator-zotero`

The plugins are deliberately separate. Each has its own manifest, permission
boundary, activation decision, audit receipt, and rollback path. A failure or
uninstall in one plugin must not disable or silently change either of the other
plugins.

OpenAI's plugin packaging contract governs the layout: every plugin has a
`.codex-plugin/plugin.json`, while skills, hooks, assets, and connector mappings
live at the plugin root. The repository marketplace lives at
`.agents/plugins/marketplace.json`, and plugin packages live under `plugins/`.

```text
.agents/plugins/marketplace.json
plugins/
├── options-validator-core/
├── options-validator-sentry/
└── options-validator-zotero/
```

## 2. Goals

- Turn the existing Options Validator skills and guard hooks into a validated,
  private installable package without creating a third unmanaged source tree.
- Add sanitized operational error monitoring without exporting research,
  portfolio, market-data, credential, or ledger content.
- Add read-only Zotero evidence discovery and deterministic non-canonical source
  indexes without giving Zotero content verdict or trading authority.
- Make every build, permission, data-flow, installation, activation, and
  rollback claim auditable from executable checks and receipts.

## 3. Non-goals

- No public plugin publication.
- No claim that these repo-specific workflows are a general-purpose options
  plugin for unrelated repositories.
- No live order placement, broker write surface, or trading activation.
- No market-data provider, data acquisition, ranking input, signal, backtest,
  hypothesis, verdict, or position mutation.
- No automatic ledger or facts append.
- No autonomous Zotero synchronization or Zotero library writes.
- No unrestricted telemetry, log forwarding, performance tracing, profiling,
  session replay, or user analytics.
- No automatic commit, push, scheduler activation, or production deployment.

## 4. Shared authority boundary

| Plugin | Network authority | External writes | Repository writes | Verdict or trading authority |
|---|---|---:|---|---:|
| Core | None | None | Generated package, manifests, hooks, tests, docs | None |
| Sentry | Sanitized telemetry and issue inspection | One approved canary plus later failure events | Instrumentation, tests, setup docs | None |
| Zotero | Selected read-only retrieval | None | Explicit non-canonical source indexes | None |

All three plugins must preserve these invariants:

- no ledger, position, cache, frozen configuration, or registered-hypothesis
  mutation;
- no new market-data provider or provider call;
- no secrets, OAuth material, private attachment paths, or licensed documents
  in Git;
- no background synchronization or automatic commits;
- no output entering ranking, signals, backtests, verdicts, sizing, positions,
  alerts with trading authority, or activation logic;
- missing authentication or dependencies fail closed without degrading the
  other plugins.

## 5. Delivery model

This program is four sequential audit units:

1. Core plugin build and audit.
2. Sentry plugin build and audit.
3. Zotero plugin build and audit.
4. Cross-plugin isolation, disable, and rollback audit.

Each plugin receives a separate implementation plan and commit sequence. Build
completion is not activation. External authentication, a real Sentry canary,
and any production-checkout deployment remain explicit later gates.

The Core plugin is built and smoke-installed in an isolated temporary
repository. It is not enabled in this source checkout because the same 13
skills are already discovered directly from `.agents/skills/`; enabling the
package here would expose duplicate workflows.

### 5.1 Sequencing precondition (added 2026-08-11 by review)

*Reviewer-drafted; not an owner decision.*

No unit of this program should start while the research ledger is forked.
Verified 2026-08-11:

- `main`'s `ledger/experiments.jsonl` holds 25 lines ending at **seq 24**,
  `record_hash` `52f9d972…`, and `main`'s `ledger/HEAD` is that same hash.
- Branch `claude/rq2-k3-and-dashboard-split` is **not** an ancestor of `main`
  (`git merge-base --is-ancestor` exits nonzero) and its commit `f230813`
  appends one line — **seq 25**, `prev_hash` `52f9d972…` — plus the matching
  `ledger/HEAD` update.

Because that pending entry's `prev_hash` is pinned to `main`'s *current* head,
any other session appending to `main` first produces a second, different seq 25
sharing the same predecessor. The chain then has two competing successors and
cannot be reconciled by an append-only rule. The window is open now and closes
only when the branch is merged.

Merging that branch is therefore ordered ahead of unit 1.

## 6. Required audit sequence

Every plugin must pass the following process:

1. Confirm Git root, worktree, branch, clean scope, and source hashes.
2. Add failing contract and adversarial tests before behavior-changing code.
3. Implement the smallest behavior needed to satisfy the approved contract.
4. Validate the plugin manifest, marketplace entry, permissions, and package
   paths.
5. Run privacy, secret, prompt-injection, path-escape, and prohibited-mutation
   checks applicable to that plugin.
6. Run scoped unit tests, Ruff, Ruff format, Pyright, and the affected full
   unittest scope.
7. Install from the local marketplace into an isolated temporary clone or
   fixture containing the required Options Validator repository surface and
   invoke representative workflows.
8. Exercise enable, disable, missing-dependency, and rollback behavior.
9. Review the complete diff for unsupported claims, hidden authority changes,
   dependency risk, unrelated edits, and failure-shaping behavior.
10. Run CodeRabbit review and a security-focused diff scan over connector,
    credential, and telemetry changes.
11. Fix validated findings and rerun every affected check.
12. Write an audit receipt with commands, true exit codes, plugin versions,
    permission state, code SHA, and unresolved limitations.

An audit failure blocks activation of that plugin. It does not authorize a
weaker fallback.

## 7. Cross-plugin failure and rollback

- Each marketplace entry can be disabled independently.
- Core contains no dependency on Sentry or Zotero.
- Sentry unavailability preserves original process behavior and exit codes.
- Zotero unavailability produces no packet and no partial source claim.
- Uninstalling an external plugin does not remove tracked reports or alter
  Zotero, Sentry, ledgers, caches, positions, or configuration.
- Private Zotero attachments are retained on disable or uninstall; deletion is
  a separate destructive action requiring explicit owner approval.
- Rollback receipts record what was disabled or removed and what durable state
  remains.

## 8. Program acceptance criteria

The program is ready only when:

- all three child specifications have executable acceptance tests;
- all three manifests are valid and independently installable;
- the marketplace exposes exactly the intended three private plugins;
- Sentry serialization proves the approved allowlist and prohibited-data
  exclusions;
- Zotero tool exposure is enforceably read-only;
- Core package hashes reconcile with canonical sources and classified `ov/`
  variants;
- isolated install and rollback smokes pass for every plugin;
- the cross-plugin audit proves no research, data, verdict, position, provider,
  or trading authority changed;
- audit receipts state any remaining external activation blockers without
  claiming readiness prematurely.

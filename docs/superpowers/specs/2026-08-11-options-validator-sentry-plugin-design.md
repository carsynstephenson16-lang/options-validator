# Options Validator Sentry private plugin design

**Date:** 2026-08-11

**Status:** Owner-approved design

**Parent:** `2026-08-11-options-validator-plugin-program-design.md`

## 1. Purpose

Add bounded operational failure visibility for the automated Options Validator
surfaces without exporting research, portfolio, market-data, credential, or
ledger content. Sentry is diagnostic only and cannot change process outcomes,
repository state, or research authority.

## 2. Components and separation

`options-validator-sentry` contains:

- `.codex-plugin/plugin.json`;
- a project-specific operational-triage skill;
- a Sentry connector mapping created from the authenticated local connection;
- the event schema and privacy policy as bundled references;
- setup, activation, audit, and rollback guidance.

The repository contains separately tested optional runtime instrumentation.
The connector and ingestion path are independent:

- connector authentication supports issue inspection;
- runtime event ingestion requires a separately configured project DSN;
- installing or authenticating either surface does not enable the other.

The post-install capability inventory must confirm the actual Sentry tools
before the connector mapping is finalized. Unknown or unexpectedly writable
tools are not enabled.

## 3. Initial runtime scope

Only these automated surfaces are eligible:

- live dashboard;
- intraday capture;
- Schwab chain capture;
- daily ritual;
- research refresh.

The initial implementation captures only unhandled Python exceptions and
nonzero scheduled-job outcomes. It sends no success events, ordinary logs,
performance traces, profiles, session replays, user analytics, or breadcrumbs.

Instrumentation is disabled by default. It does not install, enable, kickstart,
or alter a LaunchAgent, provider, hypothesis, research window, or trading path.
Production-checkout deployment remains a later explicit activation step.

## 4. Event allowlist

The serializer may emit only:

- sanitized exception class;
- repository-relative stack-frame locations, with no source lines or local
  variables;
- component and fixed job name;
- integer exit code;
- code SHA and application version;
- explicit environment label such as `ops` or `research`;
- UTC event timestamp.

The following are prohibited:

- prices, quotes, chains, Greeks, symbols obtained from payloads, or cache
  contents;
- positions, quantities, P&L, account information, or portfolio state;
- ledger text, hypothesis parameters, verdicts, or research results;
- documents, attachments, excerpts, prompts, or command output;
- OAuth material, DSNs, tokens, cookies, environment values, usernames, local
  variables, or private absolute paths;
- raw stdout, stderr, command arguments, request bodies, or subprocess payloads.

Sanitization is constructive: the event is built from the allowlist. Arbitrary
objects are never collected and then redacted. Any schema violation drops the
event before transport.

## 5. Runtime implementation boundary

The implementation may add the official Sentry Python SDK only as an optional,
locked dependency after reviewing its current package metadata and defaults.
Default project installation and offline research tests must not require that
extra.

A narrow wrapper configures the SDK with default PII disabled, local variables
disabled, breadcrumbs disabled, tracing disabled, profiling disabled, and the
allowlist serializer installed before transport. Python entrypoints may run in
process to retain sanitized exception type and frame location. Shell jobs emit
only a fixed job-failure summary and exit code; their output is never parsed or
attached.

The wrapper preserves the original exception or process exit code. Telemetry
failure emits at most one bounded local warning and never turns failure into
success or success into failure. Rejected events are not queued to disk.

## 6. Credentials and permission policy

- Connector permissions allow reads without granting silent writes; write
  actions require approval and are outside the plugin workflow.
- The runtime DSN stays outside Git using the repository's local secret-manager
  pattern.
- Plugin manifests, LaunchAgent templates, tests, logs, and events contain no
  credential.
- Missing or unreadable credentials leave telemetry disabled.
- The exact Sentry organization and project are selected before a real canary;
  no default project is guessed.

## 7. Failure and authority rules

- Sentry is not the operational source of truth; local logs and exit codes are.
- Sentry issues never mutate files, ledgers, positions, caches, configuration,
  schedulers, or provider state.
- No Sentry issue can become a ranking input, signal, research result, verdict,
  or activation event.
- Connector or network unavailability has no effect on validator behavior.
- A prohibited field, unknown event shape, or serializer exception drops the
  event and preserves the original failure.

## 8. Tests and audit

Required proof:

- post-install connector tool and permission inventory;
- disabled, missing-DSN, malformed-DSN, and dependency-absent zero-network
  tests;
- fake-transport tests for each permitted event field;
- adversarial fixtures containing positions, ledgers, OAuth values, DSNs,
  absolute paths, commands, source text, symbols, prices, and cache rows, with
  byte-level proof that none reach transport;
- exception and subprocess tests proving original exit behavior;
- serializer-schema rejection and no-retry-queue tests;
- package manifest, marketplace, connection mapping, and permission validation;
- isolated install, issue-read, disable, and rollback smoke;
- dependency and supply-chain review, secret scan, Ruff, Ruff format, Pyright,
  targeted tests, and affected full suite;
- CodeRabbit and security-focused diff review;
- one owner-approved sanitized canary after the destination project is known;
- an audit receipt with plugin and SDK versions, permission state, event schema
  hash, commands, exit codes, and unresolved activation limits.

## 9. Completion and rollback

Build completion requires all offline and fake-transport checks. Activation
requires the destination project, local credential setup, permission review,
and one inspected canary event. Production scheduler deployment is separate.

Rollback disables the plugin and the telemetry kill switch first. Removing the
optional dependency or connector comes only after proving ordinary jobs retain
their prior commands and exit behavior. Rollback never deletes local source
logs or changes research state.

# Options Validator Sentry private plugin design

**Date:** 2026-08-11

**Status:** Draft — pending owner review. **Blocked on §10 below.**

> **Provenance correction (2026-08-11).** First committed (`9713dfc`) carrying
> `Status: Owner-approved design`. That label was never true — no owner
> approval had been given or requested. Corrected to the accurate state.

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

## 10. Alternatives considered — REQUIRED, currently unanswered

*Added 2026-08-11 by review. Reviewer-drafted; not an owner decision. This
section blocks approval of the rest of this specification.*

Sections 1-9 describe how to add Sentry safely. They never establish that
Sentry is needed. This section records what the repository already does, what
actually failed, and the two questions the owner must answer before this
plugin is approved.

### 10.1 What already exists (Repo-verified)

The repository already detects, classifies, and pushes scheduled-job failures:

- `tools/intraday_capture.sh:95-121` captures the Python exit code, refuses to
  guess from the code alone, and classifies the failure from the module's own
  printed lines; the unrecognized-failure branch calls `crit`.
- `tools/intraday_capture.sh:125-132` and `tools/daily_ritual.sh:430-437`
  prefix the notification title with `[BROKEN]` when `CRITICAL=1` and invoke
  `/usr/bin/osascript -e "display notification ..."` on **every** run.
- `tools/daily_ritual.sh:62-63` defines `crit()`; line 436 prints
  `RITUAL STATUS: BROKEN` and exits 1.
- Both wrappers write a full log under `.tmp/{daily_ritual,intraday_capture}/`.

So detection, classification, local logging, non-zero exit, and a macOS push
notification are all already implemented and were already running.

### 10.2 What actually failed (Repo-verified)

`reports/provider-transition/2026-08-04-scanner-staleness-diagnosis.md` §RC-3
records the outage this plugin is implicitly justified by:

- the `com.carsyn.options-validator.intraday-capture` LaunchAgent exited 1
  because `LIVE_MARKET_DATA_PROVIDER` and the six `SCHWAB_*` keys are absent
  from the ops execution dir's `.env` while present in the main repo's;
- the logged line was
  `>>> CRITICAL: intraday_capture (open): FAILED (exit 1)` /
  `RITUAL STATUS: BROKEN`;
- capture receipts and parquet stop at **2026-07-28**; the gap was found on
  **2026-08-04**, and only because the owner compared a live broker ticket
  against the board by hand.

Tracing that failure through `intraday_capture.sh`: the logged text matches the
`else` branch at line 119 verbatim, so the run set `CRITICAL=1` and continued —
the script classifies the exit code rather than aborting on it — and therefore
**reached the `osascript` call at line 129** with a `[BROKEN]` title. Up to
five times per trading day, for roughly a week.

**Precision limit (do not overstate this).** What is Repo-verified is that the
notification call was *executed*. Whether macOS actually *displayed* it is
**not** verified and cannot be verified from the repository: the call ends in
`2>/dev/null`, so a failure to post would have been silent, and a LaunchAgent's
notification authorization and the machine's sleep state are both outside the
repo. Two readings survive, and they point at different fixes:

- **(a) The notification displayed and was ignored.** Then an additional alert
  channel is unlikely to help, and Sentry's case rests entirely on §10.3.
- **(b) The notification never displayed** (agent not authorized to post, or
  machine asleep at 09:35). Then the defect is that the repo's only alert path
  fails silently, and the cheapest correct fix is to make that path verifiable —
  not to add a second one.

**Determining which is true is a prerequisite for this specification**, and it
is cheap: check whether the intraday-capture LaunchAgent is authorized to post
notifications, and remove the `2>/dev/null` so a posting failure is logged.

**Consequence either way.** The gap is *not* detection, *not* classification,
and *not* local logging — all three existed, all three worked, and the outage
still ran from 2026-07-28 to 2026-08-04. Any justification for Sentry resting
on "we would not otherwise know about the failure" is contradicted by the
evidence above and must not be used.

### 10.3 The one thing Sentry plausibly adds

The defensible argument is **durability and off-machine persistence**: a
transient macOS toast fired by a background LaunchAgent vanishes, may be
suppressed for background agents, and is absent entirely if the machine is
asleep. An issue tracker holds a failure open until someone acknowledges it,
and is readable from a device that is not the failing machine.

That is a real gap and the existing mechanism does not close it. The spec must
say so explicitly rather than asserting generic "failure visibility."

### 10.4 The gap Sentry does *not* close (honest limit)

The same report records that **2026-07-29, 07-30 and 07-31 produced no capture
logs at all**, a cause it classifies as UNKNOWN and explicitly *not* explained
by the environment error.

Section 3 of this specification scopes ingestion to "unhandled Python
exceptions and nonzero scheduled-job outcomes." Both require the wrapper to
run. **Neither detects a job that never started.** On three of the affected
days, the design as written would have reported nothing — exactly like the
existing mechanism.

Closing that requires a heartbeat or check-in monitor ("alert me if this job
has not reported success by 10:00"), which is a different capability from
error ingestion and is not specified here.

### 10.5 Owner questions that gate approval

0. **Prerequisite, not a question — settle §10.2(a)-vs-(b) first.** Confirm
   whether the intraday-capture LaunchAgent is authorized to post macOS
   notifications, and drop the `2>/dev/null` on both `osascript` calls so a
   posting failure is logged rather than swallowed. This is a few minutes of
   work and it determines whether Sentry is solving a real gap or duplicating
   a channel that is merely misconfigured.
1. **Is off-machine, persistent-until-acknowledged delivery the actual
   requirement?** If yes, this plugin is justified and §10.3 should replace the
   vague framing in §1. If the real requirement is only "make it harder to
   ignore on this machine," a `launchd` `StandardErrorPath` plus a
   sticky-alert or a ritual precondition that refuses to proceed on stale
   receipts is far cheaper and adds no network path, dependency, or credential.
2. **Should scope include a heartbeat/check-in monitor?** Per §10.4, without
   one the design misses the job-never-ran failure mode, which is one of the
   two modes actually observed. Adding it changes the Sentry product surface
   used and must be priced before, not after, approval.

Until both are answered in writing, sections 1-9 are not approved.

# Options Validator Sentry private plugin design

**Date:** 2026-08-11

**Status:** Draft — **NOT RECOMMENDED**, on measured evidence. See §10.

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

**Measured on the machine, 2026-08-11.** The alert path is functional:

- running the wrapper's exact `osascript display notification` command returns
  **exit 0** with no stderr;
- `com.apple.ScriptEditor2` — the identity `osascript` posts under — is a
  registered notification client in `~/Library/Preferences/com.apple.ncprefs.plist`;
- `launchctl print-disabled gui/$UID` reports the intraday-capture agent
  **enabled**, and it is running: four logs exist for 2026-08-11 alone.

*Not verified:* whether a banner was rendered on screen. macOS TCC denies read
access to the notification store and to Do Not Disturb state, so display cannot
be confirmed directly. The behavioral record below is the evidence that matters.

**Behavioral record.** Every log in
`~/options-validator-ops/.tmp/intraday_capture/` counted and classified by its
own `RITUAL STATUS` line (50 logs, 21 BROKEN). Weekdays confirmed with `date`:

| Trading day | Runs | BROKEN | Note |
|---|---:|---:|---|
| Fri 07-24 | 5 | 2 | |
| Mon 07-27 | 5 | 0 | |
| Tue 07-28 | 5 | 0 | last healthy day; receipts stop here |
| **Wed 07-29** | **0** | — | **no logs at all** |
| **Thu 07-30** | **0** | — | **no logs at all** |
| **Fri 07-31** | **0** | — | **no logs at all** |
| Mon 08-03 | 5 | 5 | ops `.env` missing `LIVE_MARKET_DATA_PROVIDER` |
| Tue 08-04 | 5 | 5 | diagnosed and fixed this day |
| Wed 08-05 – Fri 08-07 | 14 | 0 | fix held |
| Mon 08-10 | 5 | 5 | **new cause** — Schwab OAuth refresh token expired |
| Tue 08-11 | 4 | 4 | **currently down** |

Today's 13:00 log ends in `authlib...OAuthError: unsupported_token_type: 400 ...
"Refresh token is invalid, expired or revoked", "invalid_grant"`. Last good run
08-07, first failure 08-10 — consistent with a seven-day refresh-token lifetime.

**Two corrections this table forces, against the reviewer's own earlier
reading.** They are recorded rather than quietly dropped:

1. The 07-28 → 08-04 gap was **not** "notifications firing and being ignored."
   For three trading days the wrapper **did not run at all** — zero logs, zero
   exit codes, zero notifications possible. Once it did start running (08-03),
   the failure was diagnosed on the **second** day. The alert path is therefore
   *not* demonstrably ignored; the earlier claim that it was is withdrawn.
2. The genuinely undetected mode is the one §10.4 already names: **the job never
   ran.** Three trading days vanished silently and nothing surfaced it. That is
   the real blind spot, and it is precisely the mode this specification's §3
   scope — unhandled exceptions and nonzero job outcomes — **cannot see either**,
   because both require the wrapper to run.

**Consequence for this specification.** The case against Sentry is narrower than
first stated, but it still holds where it matters: for failures that *do* run
and exit nonzero, detection, classification, logging and desktop push already
exist and demonstrably worked on 08-03/08-04. Adding a fourth channel for that
class is redundant. For the failure class that actually went unseen, this design
is blind by construction. So the specification is aimed at the mode that is
already covered and misses the mode that is not.

The live counter-evidence is the current outage: 9 `[BROKEN]` notifications
across 08-10 and 08-11 with the lane still down. Two days is too short to call
that ignored, and today is not over.

**What the evidence supports**, in priority order:

1. **A heartbeat / did-this-job-report check.** This is the only thing that
   would have caught 07-29 → 07-31. It is a different capability from error
   ingestion and is not specified here.
2. **Fix the recurring cause rather than alerting on it.** A credential that
   expires every seven days will fail every seven days forever. A pre-flight
   token-expiry check that refreshes or fails early removes the failure; an
   alert just requests manual repair twenty times a week.
3. **Gate what the owner already looks at.** The 08-04 gap was ultimately
   characterised by comparing the board to a broker ticket. The wall-clock
   staleness gate landed for exactly this reason (`1530444`,
   `config.py:660-670`); extending it to stale capture receipts puts the signal
   where attention already is, with no new channel, dependency or credential.
4. **Only then, if still wanted, Sentry** — for the §10.3 durability argument
   alone, honestly labelled, and only with the heartbeat gap closed.

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

### 10.5 Recommendation

**Do not build this plugin as specified.** Not because operational visibility is
unwanted — because §10.2 shows this design covers the failure class that is
already covered and is blind to the one that actually went unseen. Sections 1-9
are not approved **as scoped**.

Three things the same evidence does support, none blocked by this decision:

1. **A heartbeat check** — the only thing that would have caught the silent
   07-29 → 07-31 no-run. If any part of this program is worth building, it is
   this, and it should be scoped on its own merits rather than smuggled in as
   part of error ingestion.
2. **A Schwab refresh-token expiry pre-check** in the capture wrapper. This
   removes the currently-live failure instead of reporting it.
3. **Extending the staleness gate to capture receipts**, following the
   `1530444` precedent, so the board itself shows the lane is stale.

Reviving the plugin proper requires a written claim that persistent off-machine
delivery (§10.3) is the actual requirement, plus a resolution of the §10.4
heartbeat gap. Absent both, it duplicates working machinery.

**Unrelated but found during this review and more urgent than any of the
above:** the intraday capture lane is **down right now** (08-10 and 08-11, nine
failed runs, expired Schwab refresh token). Whatever is decided about plugins,
that wants attention first.

# Research-context refresh runbook

## Scope and safety boundary

The attractiveness research refresh is an advisory consumer of the
deterministic board and daily ritual. It never runs topups, builds features,
refreshes QM, changes candidate membership, or changes hypothesis gates,
receipts, rankings, thresholds, or verdicts.

The producer must use:

- deployment checkout:
  `/Users/carsynstephenson/options-validator-research`
- authoritative ritual checkout:
  `/Users/carsynstephenson/options-validator-ops`
- authoritative deterministic-board input checkout:
  `/Users/carsynstephenson/options-validator-ops`
- timezone semantics: `America/New_York`

Before any paid LLM invocation, the producer requires the exact market
session's `daily_ritual/run_status/v1` projection to be globally `OK`, bound by
path and SHA-256 to its capture receipt. The required H5, H6, H7, H8, and H10
evidence must also be readable and hashable. A globally `BROKEN` ritual blocks
research even if individual hypothesis rows say `CAPTURED` or `NO_SIGNAL`.

## Producer cadence

The checked-in template is
`tools/launchd/com.carsyn.options-validator.research-refresh.plist`.
It has exactly two triggers on weekdays:

- 07:40 ET: normal producer attempt
- 08:10 ET: idempotent retry

There is no 16:45 run and no Saturday run. A successful 07:40 receipt with the
same ritual-status SHA makes the 08:10 trigger exit without an LLM call.
`launchd` does not start a second instance of the same job while the first is
still running.

`StartCalendarInterval` follows the Mac's system timezone; the plist's `TZ`
environment variable affects the script but does not reinterpret launchd's
calendar. The host timezone must therefore remain `America/New_York`. If it
does not, the script's independent weekday 07:30-08:30 ET guard fails closed
rather than treating a wrong local trigger as premarket.

The template points to the deployment checkout, never a temporary worktree,
and sets:

`RESEARCH_RITUAL_ROOT=/Users/carsynstephenson/options-validator-ops`

It also sets `RESEARCH_BOARD_ROOT` to that ops checkout. The isolated research
worktree reads exact-session cache, feature, QM, and hypothesis evidence there,
while all generated research manifests, reports, logs, and dashboard output
remain in `/Users/carsynstephenson/options-validator-research`.

The producer LaunchAgent is intentionally left disabled and unloaded. Safe
template validation does not enable it:

```bash
plutil -lint tools/launchd/com.carsyn.options-validator.research-refresh.plist
```

After owner approval, copy the reviewed template to
`~/Library/LaunchAgents/`. Enabling/loading it is a separate owner-authorized
operation and is intentionally not part of this runbook.

Kill switch:

```bash
touch /Users/carsynstephenson/options-validator-research/.research-refresh-off
```

Remove that file only when the producer is deliberately allowed to run.

## Schedule and spend guards

`tools/research_refresh.sh` refuses weekends and times outside weekday
07:30-08:30 ET before ritual checks or LLM invocation. For a deliberate manual
run outside that window:

```bash
RESEARCH_REFRESH_MANUAL_OVERRIDE=1 \
RESEARCH_RITUAL_ROOT=/Users/carsynstephenson/options-validator-ops \
/bin/zsh tools/research_refresh.sh
```

`RESEARCH_REFRESH_NOW_ET` is test-only and is rejected unless
`RESEARCH_REFRESH_TEST_OVERRIDE=1`.

The durable guard state lives outside the repo at:

`~/Library/Application Support/options-validator/research-refresh/guard_state.json`

Defaults are conservative:

- maximum cost reservation per attempt: `$8.00`
- monthly worst-case reservation ceiling: `$200.00`
- repeated-failure circuit: opens after 2 consecutive failed paid attempts
- abandoned reservation timeout: 120 minutes, then counted as failed

The maximum cost is reserved atomically before an LLM starts. Reservations
remain in monthly history whether the call succeeds or fails, so retries cannot
evade the ceiling. State and lock permissions are owner-only, and only approved
failure classes are recorded; command output, environment values, prompts, and
secrets are never written to guard state.

Only one non-stale reservation may exist. A concurrent shell, including a
duplicate attempt ID, exits `SINGLE_FLIGHT_ACTIVE` before invoking the LLM.

After investigating and correcting the cause of repeated failures, an operator
may explicitly close only the failure circuit:

```bash
uv run python -m tools.research_refresh_guard reset-failures \
  --state-dir "$HOME/Library/Application Support/options-validator/research-refresh"
```

This does not erase spend history or restore monthly budget.

## Artifact contract

Each source packet must identify every fetched source with:

- `url`
- `source_tier`
- timezone-aware `published_at`, or null plus a non-empty
  `publication_time_unknown_rationale`
- actual `retrieved_at_utc` inside this run's research interval

Claims and catalysts must link to matching source metadata with the same tier.
VST and CEG each retain exactly one `PJM_BRA_NEXT` catalyst, unconfirmed and
dated null, with an official PJM URL at tier `market_operator` until PJM
publishes the exact schedule.

The manifest binds:

- exact candidate IDs and pinned symbols
- distinct research start and finish timestamps in ET and UTC
- producer commit and producer-source hashes
- the exact durable paid-attempt ID
- `uv.lock` SHA-256
- ritual status, capture receipt, and underlying evidence hashes
- run-specific immutable source-packet hashes
- explicit source URL/tier/publication/retrieval metadata
- deterministic JSON and Markdown output hashes

Publication is two-phase:

1. Assembly writes `manifest.pending.json` with
   `publication_status: PENDING_DASHBOARD`. It is not trusted by consumers or
   the independent critic.
2. The dashboard is rebuilt and checked for all stale, incomplete, or orphaned
   research markers. Only then is `manifest.json` atomically written with
   `publication_status: FINAL` and the dashboard path, SHA, and verification
   timestamps. A failed render leaves no new final marker.

When immutable inputs match an already verified final manifest, the producer
returns `NO_NEW_INPUT` and leaves the existing context, Markdown, timestamps,
packets, and final manifest byte-for-byte unchanged.

The final manifest's paid-attempt ID is reconciled to `SUCCEEDED` before a
valid-final shortcut. If the process crashes after final publication but before
the slot receipt, the next invocation verifies the final manifest, reconciles
that exact reservation (including a prior stale classification), recreates the
receipt atomically, and exits before reserving or invoking another LLM.

Manual contract sequence:

```bash
uv run python -m tools.research_context_assemble --preflight \
  --as-of <market-session> \
  --run-date <ET-run-date> \
  --ritual-root /Users/carsynstephenson/options-validator-ops

RESEARCH_STARTED_AT=<timezone-aware-timestamp> \
uv run python -m tools.research_context_assemble --assemble \
  --inputs <research-packet-directory> \
  --ritual-root /Users/carsynstephenson/options-validator-ops

uv run python -m tools.research_context_assemble --verify --pending \
  --bundle-only \
  --ritual-root /Users/carsynstephenson/options-validator-ops

uv run python -m options_researcher.attractiveness_dashboard

uv run python -m tools.research_context_assemble --finalize \
  --ritual-root /Users/carsynstephenson/options-validator-ops

uv run python -m tools.research_context_assemble --verify \
  --ritual-root /Users/carsynstephenson/options-validator-ops
```

Generated research remains uncommitted for human review.

## Independent critic cadence

The desired critic cadence is 08:45 ET on weekdays, after the 08:10 producer
retry. The critic must read only a validated `FINAL` manifest and preserve the
five finding classifications:

`HARD_CONTRADICTION`, `UNSUPPORTED`, `WEAK_INFERENCE`, `UNRESOLVED`,
`SUPPORTED`.

Material assertions retain exactly these evidence labels:

`Repo-verified`, `Test-verified`, `Official-source`, `Inference`,
`Assumption`.

Deployment is currently blocked. Local inspection found no Antigravity CLI or
documented callable task API. The installed Antigravity app exposes scheduling
only through its internal GUI-agent `schedule` and `manage_task` tools, which
are not executable from this repository or launchd. The existing Antigravity
task remains unchanged; no guessed command or non-executable schedule template
is checked in. Change it to weekday 08:45 only through a verified Antigravity
task interface after owner approval.

## Failure interpretation

- `SCHEDULE_BLOCKED`: outside approved weekday premarket window.
- `UPSTREAM_BLOCKED`: exact-session ritual lineage is absent, mismatched, or
  globally broken.
- `FAILURE_CIRCUIT_OPEN`: two consecutive paid attempts failed; investigate,
  then reset explicitly.
- `MONTHLY_BUDGET_EXHAUSTED`: worst-case reservations reached the monthly cap.
- `SINGLE_FLIGHT_ACTIVE`: another non-stale paid attempt already owns the
  producer.
- `RESEARCH_ARTIFACT_REJECTED`: source, timestamp, lineage, output, or
  dashboard verification failed.

All are fail-closed outcomes. The dashboard should retain its honest stale or
incomplete research state rather than receive invented or partially verified
content.

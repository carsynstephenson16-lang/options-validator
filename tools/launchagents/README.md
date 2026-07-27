# Dashboard and intraday LaunchAgents

## Live dashboard

`com.carsyn.options-validator.live-dashboard.plist` keeps the read-only
localhost dashboard running on `127.0.0.1:8765` from the **ops** checkout.
It uses `--no-open`, so launchd restarts do not open extra browser tabs.

Before installing, confirm the ops checkout is clean, on `main`, and contains
the tested dashboard code. Then:

```bash
mkdir -p /Users/carsynstephenson/options-validator-ops/.tmp/live_dashboard
cp tools/launchagents/com.carsyn.options-validator.live-dashboard.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID \
   ~/Library/LaunchAgents/com.carsyn.options-validator.live-dashboard.plist
launchctl enable gui/$UID/com.carsyn.options-validator.live-dashboard
```

Verify both the managed process and the freshness payload:

```bash
launchctl print gui/$UID/com.carsyn.options-validator.live-dashboard
curl -fsS http://127.0.0.1:8765/live.json
```

The direct live adapter remains preferred when its entitlement/schema probe
is healthy. Otherwise, the server reads the newest strictly validated,
same-day `intraday_capture/v1` receipt. Receipt-backed rows are descriptive
only: they cannot emit H5 trigger, gate, armed, or verdict fields.

## Intraday capture

`com.carsyn.options-validator.intraday-capture.plist` is a **template only**.
It is not installed by any Claude Code session — deployment is a separate
owner step, same as the existing daily-ritual LaunchAgent
(`tools/repo_rag/launchd/*.plist` is the sibling convention this mirrors).

It runs `tools/intraday_capture.sh` five times per trading day (09:31 /
09:35 / 11:00 / 13:00 / 15:45 ET, Monday-Friday) against the **ops** checkout
(`/Users/carsynstephenson/options-validator-ops`), never this working
checkout. The wrapper self-selects its `session_tag` from the wall clock
(`options_researcher.intraday_capture.nearest_session_tag`) and exits 0 as a
benign no-op if the machine was asleep through a scheduled moment — a missed
snapshot is not an error, it's just a gap in a descriptive dataset.

## Before installing

1. Confirm `/Users/carsynstephenson/options-validator-ops` exists, is on
   `main`, and has `tools/intraday_capture.sh` (the branch guard inside that
   script refuses to run anything else).
2. Confirm `.tmp/intraday_capture/` is creatable under the ops checkout
   (the wrapper creates it; the LaunchAgent's stdout/stderr paths below
   assume it exists once the wrapper has run at least once, or create it by
   hand first: `mkdir -p /Users/carsynstephenson/options-validator-ops/.tmp/intraday_capture`).

## Install

```bash
mkdir -p /Users/carsynstephenson/options-validator-ops/.tmp/intraday_capture
cp tools/launchagents/com.carsyn.options-validator.intraday-capture.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID \
   ~/Library/LaunchAgents/com.carsyn.options-validator.intraday-capture.plist
launchctl enable gui/$UID/com.carsyn.options-validator.intraday-capture
```

## Verify

```bash
launchctl print gui/$UID/com.carsyn.options-validator.intraday-capture
```

To fire one run immediately without waiting for the next scheduled time:

```bash
launchctl kickstart gui/$UID/com.carsyn.options-validator.intraday-capture
```

## Uninstall

```bash
launchctl bootout gui/$UID/com.carsyn.options-validator.intraday-capture
rm ~/Library/LaunchAgents/com.carsyn.options-validator.intraday-capture.plist
```

## Notes

- The plist's `WorkingDirectory` and `ProgramArguments` path are hardcoded to
  the ops checkout, matching `tools/daily_ritual.sh`'s own hardening lesson
  (a wrong-branch run against real evidence is worse than a missed run).
- `StandardOutPath`/`StandardErrorPath` write to the ops `.tmp/` (gitignored,
  disposable) — the durable record is the receipt under
  `reports/intraday_capture/`, picked up by the daily ritual's evidence
  commit step.
- This LaunchAgent and `tools/daily_ritual.sh`'s existing 07:10 LaunchAgent
  are independent: intraday_capture.sh never commits or pushes anything
  itself.

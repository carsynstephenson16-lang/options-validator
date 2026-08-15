# Dashboard and intraday LaunchAgents

## Ops alignment check (15:30 ET, detection only)

`com.carsyn.options-validator.alignment-check.plist` runs
`tools/ops_alignment_check.sh` at **15:30 ET on weekdays** from the ops
checkout — 15 minutes before the 15:45 Schwab preclose capture, whose own
alignment gate refuses to run on a divergent checkout. Owner ruling 4 of
`reports/2026-08-14-owner-answers-decision-menu.md` (D-6a).

It **only looks**: it fetches `origin/main` (bounded, prompt-free) and compares
HEAD. It predicts the capture's own gate instead of approximating it — that
gate tolerates exactly one divergence shape (owner decision D-3: strictly
ahead, with the tree differing only under evidence paths):

| Result | Meaning | Exit |
| --- | --- | --- |
| `ALIGNED` | nothing to do | 0, log line only |
| `AHEAD_EVIDENCE_ONLY` | evidence commits not yet pushed; **the 15:45 capture still runs** | 0, log + `INFO:` line, no alarm |
| `AHEAD_CODE` | unpushed code; **the capture will refuse** | 1 + notification |
| `BEHIND` / `DIVERGED` / `NOT_ON_MAIN` / `FETCH_FAILED` / `UNRESOLVED` | capture will refuse, or alignment is unknown | 1 + notification |

Every result appends a dated line under `.tmp/alignment_check/`; every nonzero
one also fires a macOS notification carrying the exact realign command. It
never merges, pulls, resets, or pushes — that command is the owner's to run.

Install (**the owner runs these; a Claude session cannot — the classifier
denies `launchctl` to agents**):

```bash
mkdir -p /Users/carsynstephenson/options-validator-ops/.tmp/alignment_check
cp tools/launchagents/com.carsyn.options-validator.alignment-check.plist \
   ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.carsyn.options-validator.alignment-check.plist
launchctl enable gui/$UID/com.carsyn.options-validator.alignment-check
```

Verify, fire one run now, or uninstall:

```bash
launchctl print gui/$UID/com.carsyn.options-validator.alignment-check
launchctl kickstart gui/$UID/com.carsyn.options-validator.alignment-check
launchctl bootout gui/$UID/com.carsyn.options-validator.alignment-check
```

A nonzero exit is the job doing its work, not a bug: it means the ops checkout
needs the printed command before 15:45.

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

## Schwab chain pre-close (15:45 ET, durable capture)

`com.carsyn.options-validator.schwab-chain-preclose.plist` runs
`tools/schwab_chain_capture.sh` at 15:45 ET on weekdays from the **ops**
checkout. Unlike the intraday template above, this job **is installed and
loaded in production**.

Since 2026-08-15 (rev-2.1 item 3a) the plist sets
`OPTIONS_VALIDATOR_INVOCATION_SOURCE=launchd` so capture receipts record
unattended provenance — the measurable input to the S1 activation bar (three
consecutive unattended verifying sessions). Two provenance rules:

- **Never** set `OPTIONS_VALIDATOR_INVOCATION_SOURCE` in a shell, wrapper, or
  any `.env` file. A hand-run capture must record `"manual"`.
- `launchctl kickstart` runs under launchd's environment, so an
  operator-triggered kickstart inside the capture window records
  `"launchd"` — S1 adjudication cross-checks receipt times against the
  schedule for exactly this reason.

The installed copy at `~/Library/LaunchAgents/` is a byte-copy; template
edits do not propagate until it is replaced (owner step):

```
cp tools/launchagents/com.carsyn.options-validator.schwab-chain-preclose.plist \
  ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.carsyn.options-validator.schwab-chain-preclose 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.carsyn.options-validator.schwab-chain-preclose.plist
launchctl print gui/$(id -u)/com.carsyn.options-validator.schwab-chain-preclose | grep -A3 environment
```

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

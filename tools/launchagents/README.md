# Dashboard and intraday LaunchAgents

## Daily ritual (09:09 ET, weekdays)

`com.carsyn.options-validator.daily-ritual.plist` runs `tools/daily_ritual.sh`
at **09:09 ET on weekdays** from the **ops** checkout. It is installed and
loaded in production.

Retimed 2026-08-26 (owner-directed, in-session) from its original 07:10 slot.
This plist was untracked until that change — it lived only in
`~/Library/LaunchAgents/` on one laptop, unlike every other job here — so the
copy in this directory starts at 09:09 and has no 07:10 history.

**The 09:09 slot sits after the daily automerge, and that is load-bearing.**
`~/bin/repo-reconcile` auto-squash-merges green PRs around 08:15, which
advances `origin/main` while the ops checkout stays put. The ritual's first
gate refuses a misaligned checkout:

```
CRITICAL: main is not exactly aligned with origin/main -- refusing cache publisher authority
```

A refusal is not merely a skipped run — the ritual never reaches its Step 8
evidence commit, so that day's capture receipts and `ledger/facts.log` appends
are left uncommitted in ops and exist on one machine only. That is the same
failure class as the 2026-08-20/24 Schwab receipt loss. At 07:10 the ritual
ran *before* the automerge and was usually aligned by default; at 09:09 it
runs *after*, so the ops pull has to actually happen:

```bash
git -C ~/options-validator-ops pull --ff-only
```

The installed copy at `~/Library/LaunchAgents/` is a byte-copy; editing the
template in this directory does **not** change what launchd runs, and even
editing the installed file does nothing until the job is reloaded — launchd
caches the schedule at bootstrap time:

```bash
cp tools/launchagents/com.carsyn.options-validator.daily-ritual.plist \
   ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u)/com.carsyn.options-validator.daily-ritual 2>/dev/null || true
launchctl bootstrap gui/$(id -u) \
   ~/Library/LaunchAgents/com.carsyn.options-validator.daily-ritual.plist
launchctl print gui/$(id -u)/com.carsyn.options-validator.daily-ritual \
  | grep -E '"(Hour|Minute|Weekday)"'
```

That last line is the only honest verification: it prints what launchd holds,
not what the file says. Expect five descriptors, Hour 9 / Minute 9,
Weekdays 1–5.

Note on who may run these: the alignment-check section below states that a
Claude session cannot run `launchctl` because the classifier denies it. That
was not true on 2026-08-26 — the session that performed this retime ran
`bootout` + `bootstrap` + `print` successfully (both rc=0). Treat the claim as
unverified rather than as a guarantee, and confirm with `launchctl print`
either way.

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
- This LaunchAgent and `tools/daily_ritual.sh`'s 09:09 LaunchAgent (07:10
  before 2026-08-26) are independent: intraday_capture.sh never commits or
  pushes anything itself.

## Display-only research views

The attractiveness/composite view remains produced by the daily ritual. The
display refresh job builds only the experiments and Wasserstein artifacts; it
does not replace or rerun the attractiveness producer. Both jobs target the
`/Users/carsynstephenson/options-validator-ops` checkout. The server is
localhost-only on `127.0.0.1:8766` and serves the ops
`.tmp/dashboard/` directory.

The Mac system timezone must remain `America/New_York`. The refresh plist's
`TZ=America/New_York` applies only to its child process; it does not control
when launchd evaluates `StartCalendarInterval`.

### Replace the unmanaged listener safely

Deployment is an owner operation. Immediately before replacing the existing
listener, resolve it again and assign a fresh numeric PID from that output:

```bash
LISTENER="$(lsof -nP -iTCP:8766 -sTCP:LISTEN)"
printf '%s\n' "$LISTENER"
PID="$(printf '%s\n' "$LISTENER" | awk 'NR == 2 { print $2 }')"
case "$PID" in
  ''|*[!0-9]*) echo "stop: listener PID was not numeric: $PID" >&2; exit 1 ;;
esac
EXPECTED_COMMAND='/Users/carsynstephenson/options-validator-ops/.venv/bin/python -m http.server 8766 --bind 127.0.0.1'
EXPECTED_CWD='/Users/carsynstephenson/options-validator-ops/.tmp/dashboard'
ps -p "$PID" -o pid=,command=
lsof -a -p "$PID" -d cwd
```

Inspect the captured listener, command, cwd, bind address, and port. Send
`TERM` only when all match the unmanaged ops-dashboard server. Otherwise stop
and report the process that owns the port; do not kill it or install an ad-hoc
replacement.

Immediately before `TERM`, revalidate the same fresh numeric PID's exact
command, cwd, bind address, and port. Stop on any mismatch; the process may
have exited or the port may have been reassigned.

```bash
CURRENT_COMMAND="$(ps -p "$PID" -o command= | sed -E 's/^[[:space:]]+//')"
if [[ "$CURRENT_COMMAND" != "$EXPECTED_COMMAND" ]]; then
  echo "stop: PID $PID command changed: $CURRENT_COMMAND" >&2
  exit 1
fi
CURRENT_CWD="$(lsof -a -p "$PID" -d cwd -Fn | awk '/^n/ { print substr($0, 2); exit }')"
if [[ "$CURRENT_CWD" != "$EXPECTED_CWD" ]]; then
  echo "stop: PID $PID cwd changed: $CURRENT_CWD" >&2
  exit 1
fi
FINAL_LISTENER="$(lsof -nP -a -p "$PID" -iTCP:8766 -sTCP:LISTEN)"
printf '%s\n' "$FINAL_LISTENER"
FINAL_LISTENER_COUNT="$(printf '%s\n' "$FINAL_LISTENER" | awk 'NR > 1 { count++ } END { print count + 0 }')"
if [[ "$FINAL_LISTENER_COUNT" -ne 1 ]] || ! printf '%s\n' "$FINAL_LISTENER" | awk -v pid="$PID" '$2 == pid && $(NF - 1) == "127.0.0.1:8766" && $NF == "(LISTEN)" { found = 1 } END { exit !found }'; then
  echo "stop: PID $PID no longer uniquely owns 127.0.0.1:8766" >&2
  exit 1
fi
kill -TERM "$PID"

PORT_RELEASED=0
for _ in {1..20}; do
  if ! lsof -nP -iTCP:8766 -sTCP:LISTEN >/dev/null 2>&1; then
    PORT_RELEASED=1
    break
  fi
  sleep 1
done
if [[ "$PORT_RELEASED" -ne 1 ]]; then
  lsof -nP -iTCP:8766 -sTCP:LISTEN
  echo "stop: port 8766 was not released after TERM" >&2
  exit 1
fi
```

### Install

Run these commands from the checkout containing the reviewed templates:

```bash
mkdir -p /Users/carsynstephenson/options-validator-ops/.tmp/research_views \
  /Users/carsynstephenson/options-validator-ops/.tmp/dashboard
cp tools/launchagents/com.carsyn.options-validator.research-display-refresh.plist \
  ~/Library/LaunchAgents/
cp tools/launchagents/com.carsyn.options-validator.research-views.plist \
  ~/Library/LaunchAgents/
launchctl bootstrap gui/$UID \
  ~/Library/LaunchAgents/com.carsyn.options-validator.research-display-refresh.plist
launchctl enable gui/$UID/com.carsyn.options-validator.research-display-refresh
launchctl bootstrap gui/$UID \
  ~/Library/LaunchAgents/com.carsyn.options-validator.research-views.plist
launchctl enable gui/$UID/com.carsyn.options-validator.research-views
```

### Verify

Print both managed jobs, prove the LaunchAgent server owns the localhost
listener and its configured document root, then kick the refresh and require a
fresh immutable-generation pointer before checking that exact generation:

```bash
launchctl print gui/$UID/com.carsyn.options-validator.research-display-refresh
SERVER_JOB="$(launchctl print gui/$UID/com.carsyn.options-validator.research-views)"
printf '%s\n' "$SERVER_JOB"
SERVER_PID="$(printf '%s\n' "$SERVER_JOB" | awk '$1 == "pid" && $2 == "=" { print $3; exit }')"
case "$SERVER_PID" in
  ''|*[!0-9]*) echo "stop: managed server PID was not numeric: $SERVER_PID" >&2; exit 1 ;;
esac
PORT_LISTENER=''
PORT_PID=''
for _ in {1..20}; do
  PORT_LISTENER="$(lsof -nP -iTCP:8766 -sTCP:LISTEN)"
  PORT_PID="$(printf '%s\n' "$PORT_LISTENER" | awk 'NR == 2 { print $2 }')"
  case "$PORT_PID" in
    *[!0-9]*|'') sleep 1 ;;
    *) break ;;
  esac
done
printf '%s\n' "$PORT_LISTENER"
PORT_LISTENER_COUNT="$(printf '%s\n' "$PORT_LISTENER" | awk 'NR > 1 { count++ } END { print count + 0 }')"
if [[ "$PORT_LISTENER_COUNT" -ne 1 ]] || [[ "$PORT_PID" != "$SERVER_PID" ]] || ! printf '%s\n' "$PORT_LISTENER" | awk -v pid="$SERVER_PID" '$2 == pid && $(NF - 1) == "127.0.0.1:8766" && $NF == "(LISTEN)" { found = 1 } END { exit !found }'; then
  echo "stop: managed server PID and localhost listener do not match" >&2
  exit 1
fi
SERVER_COMMAND="$(ps -p "$SERVER_PID" -o command= | sed -E 's/^[[:space:]]+//')"
EXPECTED_SERVER_COMMAND='/Users/carsynstephenson/options-validator-ops/.venv/bin/python -m http.server 8766 --bind 127.0.0.1 --directory /Users/carsynstephenson/options-validator-ops/.tmp/dashboard'
if [[ "$SERVER_COMMAND" != "$EXPECTED_SERVER_COMMAND" ]]; then
  echo "stop: managed server document root differs: $SERVER_COMMAND" >&2
  exit 1
fi
CURRENT_PATH='/Users/carsynstephenson/options-validator-ops/.tmp/dashboard/research-views-current.json'
STATUS_STARTED_AT="$(date +%s)"
launchctl kickstart -k gui/$UID/com.carsyn.options-validator.research-display-refresh
for _ in {1..20}; do
  if [[ -f "$CURRENT_PATH" ]] && [[ "$(stat -f %m "$CURRENT_PATH")" -ge "$STATUS_STARTED_AT" ]]; then
    break
  fi
  sleep 1
done
if [[ ! -f "$CURRENT_PATH" ]] || [[ "$(stat -f %m "$CURRENT_PATH")" -lt "$STATUS_STARTED_AT" ]]; then
  echo "stop: refresh did not publish a fresh current pointer" >&2
  exit 1
fi
curl -fsS http://127.0.0.1:8766/research-views-current.json > /tmp/research-views-current.json
GENERATION_ID="$(/Users/carsynstephenson/options-validator-ops/.venv/bin/python -c 'import json; print(json.load(open("/tmp/research-views-current.json"))["generation_id"])')"
MANIFEST_PATH="research-views-generations/$GENERATION_ID/research-views-manifest.json"
curl -fsS "http://127.0.0.1:8766/$MANIFEST_PATH"
curl -fsS http://127.0.0.1:8766/attractiveness.html
curl -fsS "http://127.0.0.1:8766/research-views-generations/$GENERATION_ID/experiments.html"
curl -fsS "http://127.0.0.1:8766/research-views-generations/$GENERATION_ID/wasserstein-regime.txt"
curl -fsS "http://127.0.0.1:8766/research-views-generations/$GENERATION_ID/wasserstein-regime.json"
curl -fsS "http://127.0.0.1:8766/research-views-generations/$GENERATION_ID/research-views-status.txt"
```

### Rollback

Boot out both labels and leave the generated dashboard artifacts in place:

```bash
launchctl bootout gui/$UID/com.carsyn.options-validator.research-display-refresh
launchctl bootout gui/$UID/com.carsyn.options-validator.research-views
rm -f ~/Library/LaunchAgents/com.carsyn.options-validator.research-display-refresh.plist
rm -f ~/Library/LaunchAgents/com.carsyn.options-validator.research-views.plist
```

These commands remove only the two installed plist copies and leave generated
dashboard artifacts in place. The prior server may be restored only with the
exact, previously verified localhost ops-dashboard command (including its
command, cwd, bind address, and port). Do not substitute an unverified process.

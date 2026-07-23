# H7 operator runbook — receipt-bound paper entry and exit sessions

This runbook operates the H7 **paper ledger only**. None of these commands
fetches market data, modifies an immutable receipt, sends a broker order, or
authorizes live trading. `h7_real_scoring finalize` remains unavailable; do
not run it.

Run commands only from the dedicated operations checkout on committed `main`,
after that day's 07:10 America/New_York ritual has finished. Do not substitute
an evening catch-up run: it can permanently create a premature `NO_GO` receipt
for unfinished same-day EOD data.

## Session variables and evidence locations

Use the same operational decision date and completed source-data date that the
ritual used. This block only derives paths and checks that the immutable
data-gate receipt exists; it writes nothing.

```zsh
cd /Users/carsynstephenson/options-validator-ops
UV="$HOME/.local/bin/uv"
RUN_DATE="$(TZ=America/New_York date +%F)"
AS_OF="$("$UV" run python -c 'from datetime import date; from options_researcher.h7_watch import evaluation_session; print(evaluation_session(date.today()))')"
SCOPE_ID="$("$UV" run python -c 'from options_researcher.h7_scope import scope_identity; print(scope_identity()["scope_id"])')"
DG_RECEIPT="reports/h7_data_gate/${SCOPE_ID}/receipts/${AS_OF}.json"
WATCHER_RECEIPT="reports/h7_receipts/${SCOPE_ID}/watcher/${AS_OF}.json"
test -f "$DG_RECEIPT" || { print -u2 "missing data-gate receipt: $DG_RECEIPT"; exit 2; }
```

The data-gate receipt names and hashes its linked source-health receipt. The
watcher receipt is at `$WATCHER_RECEIPT`; the read-only entry-preflight capture
is `reports/h7_receipts/${SCOPE_ID}/preflight/${AS_OF}.txt`; the ritual log is
`.tmp/daily_ritual/<timestamp>.log`.

## Every morning: read the exit status

The ritual already runs `fill` and then `monitor`, even on a `NO_GO` data-gate
day. Read its log first. A non-zero exit command produces `CRITICAL` and the
ritual skips the H7 watcher/preflight path for that session.

```zsh
"$UV" run python -m options_researcher.h7_exit_session status \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF"
```

`status` writes nothing. If it refuses, preserve the log and receipt bytes;
do not create a different receipt or bypass the refusal.

## EXIT-DUE recovery or controlled replay

Only use this sequence after reading the scheduled ritual log and establishing
that its exit step did not complete. It must use the **same** immutable
receipt. The commands are mechanically idempotent only for identical evidence;
a conflicting replay is a refusal, not permission to overwrite history.

```zsh
"$UV" run python -m options_researcher.h7_exit_session fill \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF"

"$UV" run python -m options_researcher.h7_exit_session monitor \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF"
```

`fill` handles due exits and retries first. `monitor` then evaluates every
open eligible position, writing receipt-bound evidence, an exit intent, or an
honest data-gap as applicable. Stop on exit code 2 or any `H7 EXIT ERROR`;
do not proceed to an entry command that session.

## ENTRY-OK decision session (manual only)

The ritual may report `ENTRY-OK`, but it never invokes these commands. Replace
`SYMBOL`, `LANE`, and the `INTENT_ID` printed by `propose` exactly; do not
invent an action absent from `$WATCHER_RECEIPT`.

```zsh
"$UV" run python -m options_researcher.h7_session status \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF" \
  --symbol SYMBOL

"$UV" run python -m options_researcher.h7_session propose \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF" \
  --watcher-receipt "$WATCHER_RECEIPT" \
  --symbol SYMBOL --lane LANE

"$UV" run python -m options_researcher.h7_session approve \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF" \
  --intent-id INTENT_ID --owner carsyn
```

The planned paper fill is next-session only. On that later morning, rerun the
session-variable block above so `$RUN_DATE`, `$AS_OF`, `$DG_RECEIPT`, and
`$WATCHER_RECEIPT` name the fill session's evidence, then run:

```zsh
"$UV" run python -m options_researcher.h7_session fill \
  --data-gate-receipt "$DG_RECEIPT" \
  --decision-session "$RUN_DATE" \
  --source-evaluation-session "$AS_OF" \
  --watcher-receipt "$WATCHER_RECEIPT" \
  --intent-id INTENT_ID
```

That entry-fill command immediately opens a fresh receipt-bound exit session
and monitors the newly opened position for the same source-data session. A
refusal returns exit code 2 and must be treated as an H7 entry-path failure;
it never routes an order.

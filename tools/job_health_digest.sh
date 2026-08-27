#!/bin/zsh
set -u

# Launchd supplies a minimal environment. Keep the runtime path explicit and
# leave seams for offline wrapper tests; production uses the fixed defaults.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV_BIN="${JOB_HEALTH_UV:-$HOME/.local/bin/uv}"
DATE_BIN="${JOB_HEALTH_DATE:-/bin/date}"
OSASCRIPT_BIN="${JOB_HEALTH_OSASCRIPT:-/usr/bin/osascript}"

cd "$REPO" || exit 2

AS_OF="$(TZ=America/New_York "$DATE_BIN" +%Y-%m-%d)"
STAMP="$(TZ=America/New_York "$DATE_BIN" +%Y-%m-%d_%H%M)"
LOGDIR="$REPO/.tmp/job_health_digest"
mkdir -p "$LOGDIR" || exit 2
LOG="$LOGDIR/${STAMP}_pid-$$.log"
exec > "$LOG" 2>&1

print -r -- "=== job-health digest ${STAMP} ==="
print -r -- "repo: ${REPO}"

critical_notify() {
  local message="$1"
  print -r -- "CRITICAL: ${message}"
  "$OSASCRIPT_BIN" -e "display notification \"${message}\" with title \"[BROKEN] options-validator job health\"" 2>/dev/null
}

LOCKDIR="$LOGDIR/run.lock"
LOCK_HELD=0
TOOL_PID=""

release_lock() {
  if [[ "$LOCK_HELD" -eq 1 ]]; then
    if ! rmdir "$LOCKDIR" 2>/dev/null; then
      print -r -- "CRITICAL: job-health digest could not release run lock: ${LOCKDIR}"
    fi
    LOCK_HELD=0
  fi
  return 0
}

forward_signal() {
  local signal_name="$1"
  trap - EXIT HUP INT TERM
  if [[ -n "$TOOL_PID" ]]; then
    kill -s "$signal_name" "$TOOL_PID" 2>/dev/null
    wait "$TOOL_PID" 2>/dev/null
    TOOL_PID=""
  fi
  release_lock
  kill -s "$signal_name" "$$"
}

if ! mkdir "$LOCKDIR" 2>/dev/null; then
  critical_notify "job-health digest run lock is already held: ${LOCKDIR}"
  exit 75
fi
LOCK_HELD=1
trap 'release_lock' EXIT
trap 'forward_signal HUP' HUP
trap 'forward_signal INT' INT
trap 'forward_signal TERM' TERM

DIGEST_PATH="$REPO/.tmp/job_health/digest_${AS_OF}.md"
if [[ -e "$DIGEST_PATH" || -L "$DIGEST_PATH" ]]; then
  if ! rm -f -- "$DIGEST_PATH"; then
    critical_notify "job-health digest could not invalidate prior report: ${DIGEST_PATH}"
    exit 1
  fi
fi
if [[ -e "$DIGEST_PATH" || -L "$DIGEST_PATH" ]]; then
  critical_notify "job-health digest prior report still exists after invalidation: ${DIGEST_PATH}"
  exit 1
fi

"$UV_BIN" run python -m tools.job_health_digest \
  --as-of "$AS_OF" \
  --root "$REPO" \
  --out-dir "$REPO/.tmp/job_health" 2>&1 &
TOOL_PID=$!
wait "$TOOL_PID"
RC=$?
TOOL_PID=""

if [[ "$RC" -ne 0 ]]; then
  critical_notify "job-health digest failed (exit ${RC})"
  exit "$RC"
fi

if [[ ! -f "$DIGEST_PATH" || -L "$DIGEST_PATH" ]]; then
  critical_notify "job-health digest did not produce a fresh report for ${AS_OF}"
  exit 1
fi
SESSION_LINE="$(sed -n '3p' "$DIGEST_PATH")"
if [[ "$SESSION_LINE" != "Session: ${AS_OF}" ]]; then
  critical_notify "job-health digest report session did not match ${AS_OF}"
  exit 1
fi

HEADLINE="$(sed -n '1p' "$DIGEST_PATH")"
if [[ "$HEADLINE" == "ALL OK" ]]; then
  print -r -- "job-health digest: ALL OK"
elif [[ "$HEADLINE" =~ '^[0-9]+ PROBLEMS$' ]]; then
  critical_notify "job-health digest reported ${HEADLINE}"
else
  critical_notify "job-health digest returned an unrecognized headline"
fi

exit "$RC"

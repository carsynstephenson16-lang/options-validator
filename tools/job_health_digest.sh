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
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

print -r -- "=== job-health digest ${STAMP} ==="
print -r -- "repo: ${REPO}"

DIGEST_PATH="$REPO/.tmp/job_health/digest_${AS_OF}.md"
"$UV_BIN" run python -m tools.job_health_digest \
  --as-of "$AS_OF" \
  --root "$REPO" \
  --out-dir "$REPO/.tmp/job_health" 2>&1
RC=$?

if [[ "$RC" -ne 0 ]]; then
  MESSAGE="job-health digest failed (exit ${RC})"
  print -r -- "CRITICAL: ${MESSAGE}"
  "$OSASCRIPT_BIN" -e "display notification \"${MESSAGE}\" with title \"[BROKEN] options-validator job health\"" 2>/dev/null
  exit "$RC"
fi

HEADLINE="$(sed -n '1p' "$DIGEST_PATH")"
if [[ "$HEADLINE" == "ALL OK" ]]; then
  print -r -- "job-health digest: ALL OK"
elif [[ "$HEADLINE" =~ '^[0-9]+ PROBLEMS$' ]]; then
  MESSAGE="job-health digest reported ${HEADLINE}"
  print -r -- "CRITICAL: ${MESSAGE}"
  "$OSASCRIPT_BIN" -e "display notification \"${MESSAGE}\" with title \"[BROKEN] options-validator job health\"" 2>/dev/null
else
  MESSAGE="job-health digest returned an unrecognized headline"
  print -r -- "CRITICAL: ${MESSAGE}"
  "$OSASCRIPT_BIN" -e "display notification \"${MESSAGE}\" with title \"[BROKEN] options-validator job health\"" 2>/dev/null
fi

exit "$RC"

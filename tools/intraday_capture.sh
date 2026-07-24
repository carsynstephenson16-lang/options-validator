#!/bin/zsh
# Intraday option-board capture wrapper (owner-directed 2026-07-24). Derives
# the session_tag from the wall clock and invokes
# options_researcher.intraday_capture once. DESCRIPTIVE ONLY -- this tool
# never trades, never emits a verdict, and never commits/pushes: the
# reports/intraday_capture/ evidence it writes is picked up by
# tools/daily_ritual.sh's existing evidence-commit step (extended
# 2026-07-24 to include that path). Logs to .tmp/intraday_capture/.
#
# Intended to run five times a trading day via a LaunchAgent (see
# tools/launchagents/com.carsyn.options-validator.intraday-capture.plist),
# once per config.INTRADAY_CAPTURE_TIMES entry, but it is also safe to run
# manually -- it just self-selects whichever scheduled window the current
# wall clock is nearest to, and is a benign no-op if none is close enough.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
# Derive the repo root from THIS script's own location (see
# tools/daily_ritual.sh for why: a hardcoded path would silently bind an
# unattended run to whatever branch that one checkout happens to be on).
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/intraday_capture"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

SUMMARY=""
note() { SUMMARY="${SUMMARY}$1\n"; echo ">>> $1"; }
CRITICAL=0
crit() { CRITICAL=1; note "CRITICAL: $1"; }

echo "=== intraday capture ${STAMP} ==="
echo "repo: ${REPO}"

# Branch guard (fail-closed), same discipline as daily_ritual.sh: an
# unattended capture run must only ever run committed, merged code from
# main -- never an in-progress feature branch.
CAPTURE_BRANCH="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "$CAPTURE_BRANCH" != "main" ]; then
  crit "checkout is on '${CAPTURE_BRANCH}', not main -- refusing to run the unattended capture from unmerged code"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  /usr/bin/osascript -e "display notification \"on '${CAPTURE_BRANCH}', not main -- capture refused\" with title \"[BROKEN] options-validator intraday capture\" subtitle \"repo: ${REPO}\"" 2>/dev/null
  exit 1
fi

# Self-select the session_tag nearest the current wall clock. An empty
# result (outside every window's tolerance, e.g. a LaunchAgent firing late
# after the machine woke from sleep) is a benign skip, not an error --
# tools/intraday_capture.sh is meant to be safe to invoke opportunistically.
TAG="$("$UV" run python -c '
from datetime import datetime
from zoneinfo import ZoneInfo
from options_researcher.intraday_capture import nearest_session_tag
now_ny = datetime.now(ZoneInfo("America/New_York"))
print(nearest_session_tag(now_ny) or "")
' 2>&1)"
TAG_RC=$?
if [ "$TAG_RC" -ne 0 ]; then
  crit "could not resolve a session_tag from the wall clock -- see output above:"
  echo "$TAG"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  exit 1
fi
if [ -z "$TAG" ]; then
  note "no scheduled capture window is near the current wall clock -- skipping (benign)"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  echo "RITUAL STATUS: OK (skipped)"
  exit 0
fi
note "session_tag: ${TAG}"

CAP_OUT="$("$UV" run python -m options_researcher.intraday_capture --session-tag "$TAG" 2>&1)"
CAP_RC=$?
echo "$CAP_OUT"
case "$CAP_RC" in
  0) note "intraday_capture (${TAG}): OK -- $(echo "$CAP_OUT" | grep -m1 '^coverage:')" ;;
  1) crit "intraday_capture (${TAG}): REFUSED (exit 1) -- see output above" ;;
  2) crit "intraday_capture (${TAG}): RECEIPT CONFLICT (exit 2) -- see output above" ;;
  *) crit "intraday_capture (${TAG}): unexpected exit ${CAP_RC}" ;;
esac

echo "=== summary ==="
printf "%b" "$SUMMARY"

TITLE="options-validator intraday capture"
if [ "$CRITICAL" -eq 1 ]; then
  TITLE="[BROKEN] $TITLE"
fi
/usr/bin/osascript -e "display notification \"$(printf '%b' "$SUMMARY" | head -c 220 | tr '"' "'")\" with title \"$TITLE\" subtitle \"tag ${TAG} -- log: .tmp/intraday_capture/${STAMP}.log\"" 2>/dev/null

if [ "$CRITICAL" -eq 1 ]; then
  echo "RITUAL STATUS: BROKEN (see CRITICAL lines above)"
  exit 1
fi
echo "RITUAL STATUS: OK"
exit 0

#!/bin/zsh
# D-6a scheduled pre-close alignment check (owner ruling 4,
# reports/2026-08-14-owner-answers-decision-menu.md).
#
# DETECTION ONLY. This script compares the checkout it runs from against
# origin/main and tells the operator. It NEVER merges, pulls, resets, pushes,
# checks out, or otherwise changes a single byte of repository state -- the
# realign command is printed and notified, and the owner runs it. That is the
# whole point: the 15:45 preclose capture REFUSES to run on a divergence its
# own gate does not tolerate, and every past loss of an irreplaceable capture
# came from finding that out at 15:45 instead of at 15:30.
#
# It predicts that gate rather than approximating it. tools/schwab_chain_capture.sh
# tolerates exactly one divergence shape (owner decision D-3): HEAD strictly
# AHEAD of origin/main, with the tree differing only under evidence paths --
# typically the daily ritual's own evidence commit whose fail-soft push failed.
# The EVIDENCE_ALLOW list and the tree-diff test below mirror that gate's
# alignment_divergence_is_evidence_only() so this check never cries wolf about
# a capture that will actually run, and never stays quiet about one that won't.
#
# The only occurrences of a mutating git verb in this file are inside the
# HINT_* strings below (text shown to the operator). tests/
# test_ops_alignment_check.py binds that invariant.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/alignment_check"
mkdir -p "$LOGDIR" || exit 2
NOW="$(date +%Y-%m-%dT%H:%M:%S%z)"
LOG="$LOGDIR/$(date +%Y-%m-%d).log"

BRANCH="$(git -C "$REPO" branch --show-current 2>/dev/null)"
LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
# Bounded and prompt-free, same discipline as tools/schwab_chain_capture.sh:
# this runs unattended 15 minutes before an irreplaceable capture, so a hung
# or credential-prompting network call must fail closed quickly, not hang.
FETCH_RC=1
if GIT_TERMINAL_PROMPT=0 git -C "$REPO" \
    -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 \
    fetch -q origin main; then
  FETCH_RC=0
fi
REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main 2>/dev/null)"

# --- classification -------------------------------------------------------
HINT_AHEAD="git -C ${REPO} push origin main"
HINT_BEHIND="git -C ${REPO} merge --ff-only origin/main"
HINT_DIVERGED="git -C ${REPO} log --oneline origin/main...HEAD   # owner decides the resolution"
HINT_INSPECT="git -C ${REPO} status && git -C ${REPO} remote -v"

is_count() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  return 0
}

# Kept identical to tools/schwab_chain_capture.sh's EVIDENCE_ALLOW: if the two
# lists drift, this check starts lying about what the 15:45 gate will do.
EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                reports/h7_receipts reports/h7_data_gate reports/h5
                reports/h6_forward reports/h8_forward reports/h10
                reports/ritual reports/intraday_capture reports/live_probe
                reports/cache_runs reports/schwab_chains
                reports/schwab_chains_intraday)

# Tree diff, not per-commit enumeration -- same reasoning the capture wrapper
# documents: `git log --name-only` is blind to an evil merge's own resolution
# and reports only a rename's destination.
ahead_is_evidence_only() {
  AHEAD_PATHS="$(git -C "$REPO" diff --name-only --no-renames origin/main HEAD 2>/dev/null)" || return 1
  while IFS= read -r CHANGED_PATH; do
    [ -z "$CHANGED_PATH" ] && continue
    PATH_OK=1
    for ALLOWED in "${EVIDENCE_ALLOW[@]}"; do
      case "$CHANGED_PATH" in
        "$ALLOWED"|"$ALLOWED"/*) PATH_OK=0; break ;;
      esac
    done
    [ "$PATH_OK" -eq 0 ] || return 1
  done <<< "$AHEAD_PATHS"
  return 0
}

AHEAD=""
BEHIND=""
HINT="$HINT_INSPECT"
if [ "$FETCH_RC" -ne 0 ]; then
  STATUS="FETCH_FAILED"
  DETAIL="could not refresh origin/main (alignment unknown)"
elif [ -z "$LOCAL_SHA" ] || [ -z "$REMOTE_SHA" ]; then
  STATUS="UNRESOLVED"
  DETAIL="could not resolve HEAD or origin/main"
elif [ "$BRANCH" != "main" ]; then
  STATUS="NOT_ON_MAIN"
  DETAIL="checkout is on branch '${BRANCH}', not main"
else
  AHEAD="$(git -C "$REPO" rev-list --count origin/main..HEAD 2>/dev/null)"
  BEHIND="$(git -C "$REPO" rev-list --count HEAD..origin/main 2>/dev/null)"
  if ! is_count "$AHEAD" || ! is_count "$BEHIND"; then
    STATUS="UNRESOLVED"
    DETAIL="could not count divergence against origin/main"
  elif [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -eq 0 ]; then
    STATUS="ALIGNED"
    DETAIL="HEAD matches origin/main"
  elif [ "$BEHIND" -eq 0 ]; then
    HINT="$HINT_AHEAD"
    if ahead_is_evidence_only; then
      STATUS="AHEAD_EVIDENCE_ONLY"
      DETAIL="HEAD is ahead of origin/main by ${AHEAD} evidence-only commit(s); the 15:45 capture will still run (owner decision D-3)"
    else
      STATUS="AHEAD_CODE"
      DETAIL="HEAD is ahead of origin/main by ${AHEAD} commit(s) touching non-evidence paths; the 15:45 capture WILL REFUSE"
    fi
  elif [ "$AHEAD" -eq 0 ]; then
    STATUS="BEHIND"
    DETAIL="HEAD is behind origin/main by ${BEHIND} commit(s)"
    HINT="$HINT_BEHIND"
  else
    STATUS="DIVERGED"
    DETAIL="HEAD and origin/main diverged (${AHEAD} ahead, ${BEHIND} behind)"
    HINT="$HINT_DIVERGED"
  fi
fi

LINE="${NOW} status=${STATUS} branch=${BRANCH:-unknown} head=${LOCAL_SHA:-unknown} origin_main=${REMOTE_SHA:-unknown} ahead=${AHEAD:-na} behind=${BEHIND:-na} detail=${DETAIL}"
echo "$LINE" >> "$LOG"
echo "$LINE"

if [ "$STATUS" = "ALIGNED" ]; then
  exit 0
fi

# Not actionable before 15:45: the capture's own D-3 tolerance covers this
# shape, so say it plainly, log it, and do NOT fire an alarm the operator
# would learn to ignore.
if [ "$STATUS" = "AHEAD_EVIDENCE_ONLY" ]; then
  echo "INFO: ${DETAIL}. Push when convenient: ${HINT}"
  exit 0
fi

MSG="ops checkout ${STATUS} -- ${DETAIL}. Run: ${HINT}"
echo "ACTION NEEDED: ${MSG}"
echo "DETECTION ONLY: this check changed nothing; the command above is the owner's to run."
/usr/bin/osascript -e "display notification \"$(printf '%s' "$MSG" | head -c 220 | tr '"' "'")\" with title \"[ACTION NEEDED] options-validator ops alignment\" subtitle \"15:30 pre-close check -- log: .tmp/alignment_check/$(date +%Y-%m-%d).log\"" 2>/dev/null
exit 1

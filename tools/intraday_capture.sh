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

# Self-select the session_tag nearest the current wall clock. "No window is
# near" (outside every tolerance, e.g. a LaunchAgent firing late after the
# machine woke from sleep) is a benign skip, not an error -- this script is
# meant to be safe to invoke opportunistically.
#
# BANNER-POLLUTION GUARD (same class as the 2026-07-23 H8 fix): LumiBot
# v4.5.63 + python-dotenv print import-time INFO banner lines to stdout on
# `uv run python -c ...`, so the raw command substitution is NOT just the
# answer -- it's banner lines followed by the answer. Filter it the same
# way tools/daily_ritual.sh:82 filters AS_OF: pipe through a strict
# whitelist regex and take the last match. Unlike AS_OF (which has no
# legitimate empty value), "no window near" IS legitimate here, so the
# python side prints an explicit "NONE" sentinel rather than an empty
# line -- an empty line is ambiguous between "prints '' on purpose" and
# "banner pollution ate the real answer," but "NONE" surviving the
# whitelist is unambiguous either way: a truly EMPTY filtered result now
# means only one thing -- the output was unparseable -- and that always
# refuses loudly rather than silently skipping.
TAG_RAW="$("$UV" run python -c '
from datetime import datetime
from zoneinfo import ZoneInfo
from options_researcher.intraday_capture import nearest_session_tag
now_ny = datetime.now(ZoneInfo("America/New_York"))
print(nearest_session_tag(now_ny) or "NONE")
' 2>&1)"
TAG_RC=$?
TAG="$(echo "$TAG_RAW" | grep -Eo '^(open_auction|open|midmorning|midday|preclose|NONE)$' | tail -1)"
if [ "$TAG_RC" -ne 0 ] || [ -z "$TAG" ]; then
  crit "could not resolve a session_tag from the wall clock (nonzero exit, or unparseable/banner-polluted output) -- raw output:"
  echo "$TAG_RAW"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  exit 1
fi
if [ "$TAG" = "NONE" ]; then
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
# Evidence-based labeling, not exit-code guessing: options_researcher.
# intraday_capture's own exit(2) (receipt conflict) collides with
# argparse's exit(2) for a usage error (e.g. an invalid --session-tag), so
# an exit code ALONE cannot honestly distinguish them. Diagnose from the
# module's own printed lines (main() always prints one of these), and only
# fall back to a generic label when nothing recognized is present.
if [ "$CAP_RC" -eq 0 ]; then
  COVERAGE_LINE="$(echo "$CAP_OUT" | grep -m1 '^coverage:')"
  # Zero coverage (e.g. today's 13:00 DNS outage) previously printed a
  # plain "OK -- coverage: 0/15 names captured" line -- indistinguishable
  # from a genuinely healthy run at a glance. A provider outage is a
  # legitimate gap in a descriptive dataset (not fatal, so NOT CRITICAL),
  # but it must be visibly not-OK: WARN, not OK.
  if echo "$COVERAGE_LINE" | grep -Eq '^coverage: 0/[0-9]+ '; then
    note "intraday_capture (${TAG}): WARN -- zero coverage (provider unreachable?) -- ${COVERAGE_LINE}"
  else
    note "intraday_capture (${TAG}): OK -- ${COVERAGE_LINE}"
  fi
elif echo "$CAP_OUT" | grep -q '^intraday_capture refused:'; then
  crit "intraday_capture (${TAG}): REFUSED (exit ${CAP_RC}) -- $(echo "$CAP_OUT" | grep -m1 '^intraday_capture refused:')"
elif echo "$CAP_OUT" | grep -q '^intraday_capture receipt CONFLICT'; then
  crit "intraday_capture (${TAG}): RECEIPT CONFLICT (exit ${CAP_RC}) -- $(echo "$CAP_OUT" | grep -m1 '^intraday_capture receipt CONFLICT')"
else
  crit "intraday_capture (${TAG}): FAILED (exit ${CAP_RC}) -- unrecognized failure mode, see output above"
fi

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

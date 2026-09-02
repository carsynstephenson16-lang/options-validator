#!/bin/zsh
# Durable Schwab INTRADAY chain capture (10:00 "morning" / 13:00 "midday" ET;
# owner-directed 2026-09-02, in-session: "I want a pull at 10am and a pull at
# 1pm"). Cloned from tools/schwab_chain_capture.sh per Brief 30 WP-D.1 so the
# pre-close wrapper stays untouched: same branch guard, bounded fetch,
# alignment gate, failure taxonomy, and notification -- but it may ONLY ever
# run an intraday slot. It asks the module which of {morning, midday} the
# wall clock is nearest to and refuses loudly when neither is: a launchd fire
# that arrives late (machine asleep through 13:00, awake at 15:40) or an
# operator kickstart inside the pre-close window can therefore never resolve
# to "preclose" and never touch .cache/schwab_chains or reports/schwab_chains.
# Read-only, never trades, never invokes the display-only intraday lane.
#
# The intraday slots write to the ISOLATED namespace
# .cache/schwab_chains_intraday/<tag>/ + reports/schwab_chains_intraday/<tag>/
# (receipt kind schwab_chain_capture_intraday/v1, convention
# intraday_snapshot_v1, fact prefix SCHWAB_INTRADAY_CHAIN_CAPTURE tag=<tag>).
# The pre-close lane keys every artifact by symbol + date and is
# first-write-wins, so a same-namespace write would make the 15:45 capture
# refuse and lose that day's H7 evidence -- the separate namespace is what
# makes this job safe, not the schedule.
#
# SAME-DAY RETRY IS UNSAFE, per slot, exactly as for the pre-close lane
# (docs/h7-forward-operations.md "Preclose Schwab chain capture"): a second
# "morning" run on the same day ends in a RECEIPT CONFLICT (exit 2), and a
# missed slot is a permanent gap. Do not blindly re-run.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/schwab_chain_intraday"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

echo "=== Schwab chain intraday ${STAMP} ==="
echo "repo: ${REPO}"

# Unattended evidence may run only from the merged and current ops main.
BRANCH="$(git -C "$REPO" branch --show-current 2>/dev/null)"
LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
if [ "$BRANCH" != "main" ]; then
  echo "schwab_chain_capture wrapper REFUSED: branch is '${BRANCH}', not main"
  exit 1
fi
# Bounded, prompt-free refresh: this fetch sits on the irreplaceable-capture
# critical path, so a hung network call must fail closed well inside the
# preclose tolerance window instead of eating it.
if ! GIT_TERMINAL_PROMPT=0 git -C "$REPO" \
    -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 \
    fetch -q origin main; then
  echo "schwab_chain_capture wrapper REFUSED: could not refresh origin/main"
  exit 1
fi
REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main 2>/dev/null)"
if [ -z "$LOCAL_SHA" ] || [ -z "$REMOTE_SHA" ]; then
  echo "schwab_chain_capture wrapper REFUSED: could not resolve local/remote identity"
  exit 1
fi
# --- alignment gate: evidence-only divergence tolerance -------------------
# Owner decision D-3 (2026-08-14, reports/2026-08-14-switch-on-owner-decisions.md;
# brief 11 §9.2). The gate's purpose is "no unreviewed CODE runs unattended".
# A strict SHA equality also refused when the only divergence was the daily
# ritual's own evidence commit whose fail-soft push had failed -- turning a
# transient push failure into a PERMANENTLY lost irreplaceable capture. So:
# refuse unless HEAD's tree differs from origin/main's ONLY under evidence
# allow-list paths. Being BEHIND origin/main still refuses exactly as before
# (running stale code unattended is what this guard exists to prevent), and
# anything unresolvable fails closed.
EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                reports/h7_receipts reports/h7_data_gate reports/h5
                reports/h6_forward reports/h8_forward reports/h10
                reports/ritual reports/intraday_capture reports/live_probe
                reports/cache_runs reports/schwab_chains
                reports/schwab_chains_intraday)
alignment_divergence_is_evidence_only() {
  BEHIND_COUNT="$(git -C "$REPO" rev-list --count HEAD..origin/main 2>/dev/null)"
  case "$BEHIND_COUNT" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$BEHIND_COUNT" -ne 0 ] && return 1
  # TREE diff, not per-commit enumeration. `git log --name-only` has two
  # documented blind spots that both let a code change through: it emits NO
  # paths at all for a merge commit (so an "evil merge" whose conflict
  # resolution edits code shows only the evidence paths of its parents), and
  # it reports only the DESTINATION of a rename (so `git mv` of a code file
  # into an evidence path reads as evidence-only). Comparing the trees asks
  # the strictly stronger question this guard actually means: does the working
  # HEAD differ from reviewed origin/main anywhere outside the evidence
  # paths? --no-renames forces both sides of a rename to be reported.
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
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  if ! alignment_divergence_is_evidence_only; then
    echo "schwab_chain_capture wrapper REFUSED: HEAD is not aligned with origin/main"
    exit 1
  fi
  echo "schwab_chain_capture: HEAD is AHEAD of origin/main by evidence-only commit(s) -- proceeding (owner decision D-3). Realign with: git -C ${REPO} push origin main"
fi
# --- end alignment gate ---------------------------------------------------

# Slot self-selection runs AFTER the branch/alignment gates on purpose: the
# module is repo Python, and it must not execute from a checkout that has not
# yet been verified as merged-and-current. `--tags morning,midday` restricts
# the answer to this job's own slots (see the header for why). "No slot is
# near" is a LOUD refusal (exit 1 + notification), not a benign skip: a
# durable capture that silently does nothing is an irreplaceable gap.
#
# BANNER-POLLUTION GUARD (same class as the 2026-07-23 H8 fix): LumiBot +
# python-dotenv print import-time INFO banner lines to stdout, so the raw
# output is banner lines followed by the answer. Whitelist-filter and take
# the last match; the module prints an explicit "NONE" sentinel rather than
# an empty line, so an EMPTY filtered result means only "unparseable" and
# always refuses.
TAG_RAW="$("$UV" run python -m options_researcher.schwab_chain_capture --print-nearest-tag --tags morning,midday 2>&1)"
TAG_RC=$?
TAG="$(echo "$TAG_RAW" | grep -Eo '^(morning|midday|NONE)$' | tail -1)"
if [ "$TAG_RC" -ne 0 ] || [ -z "$TAG" ]; then
  echo "schwab_chain_intraday wrapper REFUSED: could not resolve an intraday slot from the wall clock (nonzero exit, or unparseable/banner-polluted output) -- raw output:"
  echo "$TAG_RAW"
  /usr/bin/osascript -e "display notification \"could not resolve an intraday slot from the wall clock -- capture refused\" with title \"[BROKEN] options-validator schwab intraday capture\" subtitle \"log: .tmp/schwab_chain_intraday/${STAMP}.log\"" 2>/dev/null
  exit 1
fi
if [ "$TAG" = "NONE" ]; then
  echo "schwab_chain_intraday wrapper REFUSED: no intraday slot (10:00 / 13:00 ET +/- tolerance) is near the current wall clock -- a late or out-of-window fire must not capture (and can never fall through to the pre-close slot)"
  /usr/bin/osascript -e "display notification \"no intraday slot near the wall clock -- capture refused\" with title \"[BROKEN] options-validator schwab intraday capture\" subtitle \"log: .tmp/schwab_chain_intraday/${STAMP}.log\"" 2>/dev/null
  exit 1
fi
echo "session_tag: ${TAG}"

# Provider selection is explicit. Trading remains fail-closed even if the
# caller's environment says otherwise.
#
# DO NOT ADD OPTIONS_VALIDATOR_INVOCATION_SOURCE HERE (rev-2.1 item 3a, spec
# §7 condition 3). That marker is set by the schwab-chain-intraday plist
# (and, for the pre-close lane, by its own plist) and by nothing else, so the receipt's invocation_source distinguishes a
# LaunchAgent fire from a hand-run of this wrapper. Setting it here would make
# every manual run claim "launchd" and would silently void S1's condition 3.
# The `env` prefix below deliberately has no `-i`: the plist's marker must be
# inherited through to python, not cleared.
CAP_OUT="$(env LIVE_MARKET_DATA_PROVIDER=schwab \
  SCHWAB_TRADING_ENABLED=false \
  "$UV" run python -m options_researcher.schwab_chain_capture --session-tag "$TAG" 2>&1)"
RC=$?
echo "$CAP_OUT"

# Evidence-based labeling, not exit-code guessing (same discipline as the
# sibling display-only intraday capture wrapper uses for its own CAP_OUT):
# options_researcher.schwab_chain_capture's own exit(2) (receipt conflict)
# collides with argparse's exit(2) for an unrelated usage error, so an exit
# code ALONE cannot honestly distinguish REFUSED / RECEIPT CONFLICT / a
# partial per-symbol failure. Diagnose from the module's own printed lines
# (capture()/main() always print one of these on a nonzero exit), and only
# fall back to a generic label when nothing recognized is present.
CRITICAL=0
MSG="SCHWAB CHAIN STATUS: OK"
if [ "$RC" -ne 0 ]; then
  CRITICAL=1
  if echo "$CAP_OUT" | grep -q '^schwab_chain_capture auth EXPIRED:'; then
    MSG="CRITICAL: SCHWAB REAUTH REQUIRED -- run uv run python tools/setup_schwab.py"
    echo "$MSG"
  elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture refused:'; then
    MSG="CRITICAL: SCHWAB CHAIN REFUSED (exit ${RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture refused:')"
    echo "$MSG"
    echo "SCHWAB CHAIN STATUS: BROKEN (exit ${RC}; receipt/log contains evidence)"
  elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture receipt CONFLICT:'; then
    MSG="CRITICAL: SCHWAB CHAIN RECEIPT CONFLICT (exit ${RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture receipt CONFLICT:')"
    echo "$MSG"
    echo "SAME-DAY RETRY IS UNSAFE: capture always refetches the whole watch universe live and both the per-symbol files and the session receipt are hash-match-or-refuse, so simply re-running today will almost always conflict again instead of completing the session -- see docs/h7-forward-operations.md before acting."
    echo "SCHWAB CHAIN STATUS: BROKEN (exit ${RC}; receipt/log contains evidence)"
  elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture failed:'; then
    MSG="CRITICAL: SCHWAB CHAIN PARTIAL FAILURE (exit ${RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture failed:')"
    echo "$MSG"
    echo "SAME-DAY RETRY IS UNSAFE: a same-day retry refetches the whole watch universe live, so the immutable per-symbol and receipt writes will very likely turn this partial session into a RECEIPT CONFLICT instead of filling the gap -- see docs/h7-forward-operations.md before acting."
    echo "SCHWAB CHAIN STATUS: BROKEN (exit ${RC}; receipt/log contains evidence)"
  else
    MSG="CRITICAL: SCHWAB CHAIN STATUS unrecognized failure mode (exit ${RC}) -- see log above"
    echo "$MSG"
    echo "SCHWAB CHAIN STATUS: BROKEN (exit ${RC}; receipt/log contains evidence)"
  fi
else
  echo "$MSG"
fi

TITLE="options-validator schwab intraday capture (${TAG})"
if [ "$CRITICAL" -eq 1 ]; then
  TITLE="[BROKEN] $TITLE"
fi
/usr/bin/osascript -e "display notification \"$(printf '%s' "$MSG" | head -c 220 | tr '"' "'")\" with title \"$TITLE\" subtitle \"tag ${TAG} -- log: .tmp/schwab_chain_intraday/${STAMP}.log\"" 2>/dev/null

exit "$RC"

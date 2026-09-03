#!/bin/zsh
# Independent durable Schwab preclose-chain capture. Read-only, never trades,
# and never invokes the display-only intraday lane. Intended for the ops
# checkout through its own LaunchAgent template.
#
# SAME-DAY RETRY IS UNSAFE (audit M7, docs/h7-forward-operations.md
# "Preclose Schwab chain capture" has the full explanation): capture()
# always refetches the WHOLE watch universe live in one pass, and both the
# per-symbol parquet writes and the session-level receipt are
# hash-match-or-refuse / first-write-wins (see
# options_researcher/schwab_chain_capture.py's _write_parquet_once and
# _write_receipt). A session therefore completes cleanly in only ONE atomic
# run -- because live market data and the receipt's wall-clock timestamp
# differ between invocations, simply re-running this wrapper for the SAME
# session (day) after a partial or failed first run does not "fill the
# gap"; it almost always ends in a RECEIPT CONFLICT (exit 2) instead. A
# partial/failed preclose day needs explicit operator handling, not a blind
# re-run -- see docs/h7-forward-operations.md before acting.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/schwab_chain_capture"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

echo "=== Schwab chain preclose ${STAMP} ==="
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

# Proactive refresh-token age line (2026-09-02). The Schwab refresh token
# dies 7 days after CREATION and refreshing an access token does not reset
# that clock, so on 2026-08-31 and 2026-09-01 this log recorded only a generic
# failure. Printing the advisory BEFORE the capture means the 15:45 log names
# the cause even when the capture then dies. Advisory only: the module never
# touches the network, its CLI always exits 0, and `|| true` keeps it out of
# this wrapper's exit path and out of the CRITICAL labeling below.
echo "--- schwab token age (advisory) ---"
"$UV" run python -m options_researcher.schwab_token_age || true

# Provider selection is explicit. Trading remains fail-closed even if the
# caller's environment says otherwise.
#
# DO NOT ADD OPTIONS_VALIDATOR_INVOCATION_SOURCE HERE (rev-2.1 item 3a, spec
# §7 condition 3). That marker is set by the schwab-chain-preclose plist and
# by nothing else, so the receipt's invocation_source distinguishes a
# LaunchAgent fire from a hand-run of this wrapper. Setting it here would make
# every manual run claim "launchd" and would silently void S1's condition 3.
# The `env` prefix below deliberately has no `-i`: the plist's marker must be
# inherited through to python, not cleared.
CAP_OUT="$(env LIVE_MARKET_DATA_PROVIDER=schwab \
  SCHWAB_TRADING_ENABLED=false \
  "$UV" run python -m options_researcher.schwab_chain_capture 2>&1)"
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

TITLE="options-validator schwab preclose capture"
if [ "$CRITICAL" -eq 1 ]; then
  TITLE="[BROKEN] $TITLE"
fi
/usr/bin/osascript -e "display notification \"$(printf '%s' "$MSG" | head -c 220 | tr '"' "'")\" with title \"$TITLE\" subtitle \"log: .tmp/schwab_chain_capture/${STAMP}.log\"" 2>/dev/null

exit "$RC"

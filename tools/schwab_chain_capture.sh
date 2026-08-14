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
if ! git -C "$REPO" fetch -q origin main; then
  echo "schwab_chain_capture wrapper REFUSED: could not refresh origin/main"
  exit 1
fi
REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main 2>/dev/null)"
if [ "$BRANCH" != "main" ]; then
  echo "schwab_chain_capture wrapper REFUSED: branch is '${BRANCH}', not main"
  exit 1
fi
if [ -z "$LOCAL_SHA" ] || [ -z "$REMOTE_SHA" ]; then
  echo "schwab_chain_capture wrapper REFUSED: could not resolve local/remote identity"
  exit 1
fi
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  echo "schwab_chain_capture wrapper REFUSED: HEAD is not aligned with origin/main"
  exit 1
fi

# Provider selection is explicit. Trading remains fail-closed even if the
# caller's environment says otherwise.
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

#!/bin/zsh
# Independent durable Schwab preclose-chain capture. Read-only, never trades,
# and never invokes the display-only intraday lane. Intended for the ops
# checkout through its own LaunchAgent template.

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
LIVE_MARKET_DATA_PROVIDER=schwab \
SCHWAB_TRADING_ENABLED=false \
  "$UV" run python -m options_researcher.schwab_chain_capture
RC=$?
if [ "$RC" -ne 0 ]; then
  echo "SCHWAB CHAIN STATUS: BROKEN (exit ${RC}; receipt/log contains evidence)"
  exit "$RC"
fi
echo "SCHWAB CHAIN STATUS: OK"
exit 0

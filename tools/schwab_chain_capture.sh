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

SUMMARY=""
note() { SUMMARY="${SUMMARY}$1\n"; echo ">>> $1"; }
CRITICAL=0
crit() { CRITICAL=1; note "CRITICAL: $1"; }
notify() {
  TITLE="options-validator Schwab chain preclose"
  if [ "$CRITICAL" -eq 1 ]; then
    TITLE="[BROKEN] $TITLE"
  fi
  /usr/bin/osascript -e "display notification \"$(printf '%b' "$SUMMARY" | head -c 220 | tr '"' "'")\" with title \"$TITLE\" subtitle \"log: .tmp/schwab_chain_capture/${STAMP}.log\"" 2>/dev/null
}

echo "=== Schwab chain preclose ${STAMP} ==="
echo "repo: ${REPO}"

# Unattended evidence may run only from the merged and current ops main.
BRANCH="$(git -C "$REPO" branch --show-current 2>/dev/null)"
LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"
REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main 2>/dev/null)"
if [ "$BRANCH" != "main" ]; then
  crit "schwab_chain_capture wrapper REFUSED: branch is '${BRANCH}', not main"
  notify
  exit 1
fi
if [ -z "$LOCAL_SHA" ] || [ -z "$REMOTE_SHA" ]; then
  crit "schwab_chain_capture wrapper REFUSED: could not resolve local/remote identity"
  notify
  exit 1
fi
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  crit "schwab_chain_capture wrapper REFUSED: HEAD is not aligned with origin/main"
  notify
  exit 1
fi

# Provider selection is explicit. Trading remains fail-closed even if the
# caller's environment says otherwise.
CAP_OUT="$(LIVE_MARKET_DATA_PROVIDER=schwab \
SCHWAB_TRADING_ENABLED=false \
  "$UV" run python -m options_researcher.schwab_chain_capture 2>&1)"
CAP_RC=$?
echo "$CAP_OUT"

# Diagnose from the capture CLI's printed evidence, not exit code alone:
# exit 2 is a receipt conflict, but it can also be an argument/usage error.
if [ "$CAP_RC" -eq 0 ]; then
  note "schwab_chain_capture: OK"
elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture refused:'; then
  crit "schwab_chain_capture: REFUSED (exit ${CAP_RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture refused:')"
elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture receipt CONFLICT'; then
  crit "schwab_chain_capture: RECEIPT CONFLICT (exit ${CAP_RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture receipt CONFLICT')"
elif echo "$CAP_OUT" | grep -q '^schwab_chain_capture failed:'; then
  crit "schwab_chain_capture: PARTIAL FAILURE (exit ${CAP_RC}) -- $(echo "$CAP_OUT" | grep -m1 '^schwab_chain_capture failed:')"
  crit "same-day retry requires a whole-universe refetch and can hit hash-match refusal; one session completes only in one atomic run. Stale partials require explicit operator handling."
else
  crit "schwab_chain_capture: FAILED (exit ${CAP_RC}) -- unrecognized failure mode, see output above"
fi

echo "=== summary ==="
printf "%b" "$SUMMARY"
notify

if [ "$CRITICAL" -eq 1 ]; then
  echo "SCHWAB CHAIN STATUS: BROKEN (see CRITICAL lines above)"
  exit "$CAP_RC"
fi
echo "SCHWAB CHAIN STATUS: OK"
exit 0

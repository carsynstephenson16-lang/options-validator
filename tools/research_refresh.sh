#!/bin/zsh
# Scheduled research refresh — spec amendment "2026-07-25 (owner-directed):
# scheduled research refresh" in docs/superpowers/specs/2026-07-16-
# attractiveness-v2-technicals-context-design.md. Display-layer ONLY: it
# converges chain/feature freshness, runs a headless Sonnet session to
# rebuild reports/attractiveness_context/<as-of>.json, rebuilds the
# dashboard, verifies. It NEVER touches H7 receipts/gates/ledger, never
# commits, never pushes. Kill-switch: .research-refresh-off at repo root.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
CLAUDE="$HOME/.local/bin/claude"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/research_refresh"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1
echo "=== research refresh ${STAMP} ==="

if [ -f "$REPO/.research-refresh-off" ]; then
  echo "DISABLED by .research-refresh-off — exiting 0"; exit 0
fi

HOUR="$(TZ=America/New_York date +%H)"
if [ "$HOUR" -lt 12 ]; then SLOT="premarket"; else SLOT="postclose"; fi
[ "$(TZ=America/New_York date +%u)" = 6 ] && SLOT="weekend"

# --- Stage 1: converge data freshness (no-ops when already current) ---
"$UV" run python data/recent_topup.py --scope h7 --refresh-closes \
  || echo "WARN: h7 topup failed — continuing on cached data"
"$UV" run python data/recent_topup.py --scope display-extra --refresh-closes \
  || echo "WARN: display-extra topup failed — continuing"
AS_OF="$("$UV" run python -m tools.research_context_assemble --print-ids 2>/dev/null \
  | tail -1 | "$UV" run python -c 'import json,sys; print(json.load(sys.stdin)["data_as_of"])')"
if [ -z "$AS_OF" ]; then
  echo "CRITICAL: could not resolve board data_as_of"; exit 1
fi
RECEIPT="$LOGDIR/receipt_${AS_OF}_${SLOT}.json"
if [ -f "$RECEIPT" ]; then
  echo "SKIP: ${SLOT} refresh for ${AS_OF} already succeeded (${RECEIPT})"; exit 0
fi
"$UV" run python -c "from options_researcher.features import build_all; from options_researcher.h7_scope import watch_universe; build_all('$AS_OF', symbols=watch_universe())" \
  || { echo "CRITICAL: watch feature rebuild failed"; exit 1; }
"$UV" run python -c "from config import ATTRACTIVENESS_EXTRA_NAMES; from options_researcher.features import build_all; build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)" \
  || echo "WARN: display-extra features failed (non-blocking)"
"$UV" run python -m options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF" \
  || echo "WARN: QM OHLCV refresh failed (QM cards will show DATA BLOCKED)"

# --- Stage 2: headless research session (Sonnet, hard dollar cap) ---
"$CLAUDE" -p "/research-refresh" \
  --model sonnet \
  --max-budget-usd 8 \
  --allowedTools "Bash Read Write Edit Grep Glob WebSearch WebFetch Task TodoWrite Skill" \
  > "$LOGDIR/claude_${STAMP}.out" 2>&1
CLAUDE_RC=$?
tail -3 "$LOGDIR/claude_${STAMP}.out"
if [ "$CLAUDE_RC" -ne 0 ]; then
  echo "CRITICAL: headless research session exit ${CLAUDE_RC}"; exit 1
fi

# --- Stage 3: independent verification (never trust the agent's own OK) ---
"$UV" run python -m options_researcher.attractiveness_dashboard \
  || { echo "CRITICAL: dashboard rebuild failed"; exit 1; }
if "$UV" run python -m tools.research_context_assemble --verify; then
  echo "{\"as_of\": \"${AS_OF}\", \"slot\": \"${SLOT}\", \"stamp\": \"${STAMP}\", \"status\": \"ok\"}" > "$RECEIPT"
  echo "RESULT: OK ${AS_OF} ${SLOT}"
  echo "NOTE: context file left uncommitted by design; commit it in a session"
else
  echo "CRITICAL: verification failed — board keeps honest stale banners"; exit 1
fi

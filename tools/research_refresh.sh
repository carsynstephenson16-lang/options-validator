#!/bin/zsh
# Scheduled research refresh. This job is a research consumer only: the daily
# ritual owns topups, features, QM data, and hypothesis evidence. Research
# refuses before invoking an LLM unless the authoritative checkout contains a
# successful receipt for this exact market session and ET run date.
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${0:A:h:h}"
UV="${RESEARCH_REFRESH_UV:-$HOME/.local/bin/uv}"
CLAUDE="${RESEARCH_REFRESH_CLAUDE:-$HOME/.local/bin/claude}"
LOGDIR="${RESEARCH_REFRESH_LOG_DIR:-$REPO/.tmp/research_refresh}"
RITUAL_ROOT="${RESEARCH_RITUAL_ROOT:-}"
RUN_DATE="${RESEARCH_RUN_DATE:-$(TZ=America/New_York date +%Y-%m-%d)}"
cd "$REPO" || exit 2

mkdir -p "$LOGDIR"
STAMP="$(TZ=America/New_York date +%Y-%m-%d_%H%M%S)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1
echo "=== research refresh ${STAMP} ET ==="

if [ -f "$REPO/.research-refresh-off" ]; then
  echo "DISABLED by .research-refresh-off — exiting 0"
  exit 0
fi

if [ -z "$RITUAL_ROOT" ]; then
  echo "UPSTREAM_BLOCKED: RESEARCH_RITUAL_ROOT is not configured"
  exit 3
fi

HOUR="$(TZ=America/New_York date +%H)"
if [ "$HOUR" -lt 12 ]; then
  SLOT="premarket"
else
  SLOT="postclose"
fi
[ "$(TZ=America/New_York date +%u)" = 6 ] && SLOT="weekend"

# The board is read-only here. A test-only override avoids touching live board
# data while exercising the fail-closed shell path.
AS_OF="${RESEARCH_MARKET_AS_OF:-}"
if [ -z "$AS_OF" ]; then
  AS_OF="$("$UV" run python -m tools.research_context_assemble --print-ids 2>/dev/null \
    | sed -n 's/^{"data_as_of": "\([0-9-]*\)".*/\1/p' | tail -1)"
fi
if [ -z "$AS_OF" ]; then
  echo "UPSTREAM_BLOCKED: could not resolve board data_as_of"
  exit 3
fi

PREFLIGHT_META="$LOGDIR/preflight_${STAMP}.json"
"$UV" run python -m tools.research_context_assemble \
  --preflight --as-of "$AS_OF" --run-date "$RUN_DATE" \
  --ritual-root "$RITUAL_ROOT" --receipt-out "$PREFLIGHT_META"
PREFLIGHT_RC=$?
if [ "$PREFLIGHT_RC" -ne 0 ]; then
  echo "UPSTREAM_BLOCKED: exact-session ritual preflight failed"
  exit 3
fi

RECEIPT="$LOGDIR/receipt_v2_${AS_OF}_${SLOT}.json"
if [ -f "$RECEIPT" ]; then
  CURRENT_RITUAL_SHA="$(sed -n 's/.*"ritual_run_status_sha256":"\([^"]*\)".*/\1/p' "$PREFLIGHT_META" | tail -1)"
  PRIOR_RITUAL_SHA="$(sed -n 's/.*"ritual_run_status_sha256":"\([^"]*\)".*/\1/p' "$RECEIPT" | tail -1)"
  PRIOR_STATUS="$(sed -n 's/.*"status":"\([^"]*\)".*/\1/p' "$RECEIPT" | tail -1)"
  if [ "$PRIOR_STATUS" = "ok" ] && [ -n "$CURRENT_RITUAL_SHA" ] && [ "$CURRENT_RITUAL_SHA" = "$PRIOR_RITUAL_SHA" ]; then
    echo "SKIP: ${SLOT} refresh for ${AS_OF} already succeeded against the same ritual status"
    exit 0
  fi
  echo "INFO: prior slot receipt has different ritual lineage; refreshing"
fi

"$CLAUDE" -p "/research-refresh" \
  --model sonnet \
  --max-budget-usd 8 \
  --allowedTools "Bash Read Write Edit Grep Glob WebSearch WebFetch Task TodoWrite Skill" \
  > "$LOGDIR/claude_${STAMP}.out" 2>&1
CLAUDE_RC=$?
tail -3 "$LOGDIR/claude_${STAMP}.out"
if [ "$CLAUDE_RC" -ne 0 ]; then
  echo "CRITICAL: headless research session exit ${CLAUDE_RC}"
  exit 1
fi

"$UV" run python -m tools.research_context_assemble \
  --verify --bundle-only --ritual-root "$RITUAL_ROOT" \
  || { echo "CRITICAL: bundle verification failed before dashboard render"; exit 1; }
"$UV" run python -m options_researcher.attractiveness_dashboard \
  || { echo "CRITICAL: dashboard rebuild failed"; exit 1; }
VERIFY_META="$LOGDIR/verify_${STAMP}.json"
"$UV" run python -m tools.research_context_assemble \
  --verify --ritual-root "$RITUAL_ROOT" --receipt-out "$VERIFY_META"
VERIFY_RC=$?
if [ "$VERIFY_RC" -ne 0 ]; then
  echo "CRITICAL: verification failed — manifest remains untrusted"
  exit 1
fi

RUN_ID="$(sed -n 's/.*"run_id":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
CONTEXT_SHA="$(sed -n 's/.*"context_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
RITUAL_STATUS_SHA="$(sed -n 's/.*"ritual_run_status_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
RITUAL_RECEIPT_SHA="$(sed -n 's/.*"ritual_receipt_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
printf '%s\n' \
  "{\"schema_version\":\"attractiveness_research/v2\",\"as_of\":\"${AS_OF}\",\"slot\":\"${SLOT}\",\"run_id\":\"${RUN_ID}\",\"context_sha256\":\"${CONTEXT_SHA}\",\"ritual_run_status_sha256\":\"${RITUAL_STATUS_SHA}\",\"ritual_receipt_sha256\":\"${RITUAL_RECEIPT_SHA}\",\"status\":\"ok\"}" \
  > "$RECEIPT"
echo "RESULT: OK ${AS_OF} ${SLOT} run_id=${RUN_ID}"
echo "NOTE: generated research artifacts remain uncommitted for review"

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
STATE_DIR="${RESEARCH_REFRESH_STATE_DIR:-$HOME/Library/Application Support/options-validator/research-refresh}"
ATTEMPT_BUDGET_USD="${RESEARCH_REFRESH_ATTEMPT_BUDGET_USD:-8.00}"
MONTHLY_BUDGET_USD="${RESEARCH_REFRESH_MONTHLY_BUDGET_USD:-200.00}"
MAX_FAILURES="${RESEARCH_REFRESH_MAX_FAILURES:-2}"
STALE_MINUTES="${RESEARCH_REFRESH_STALE_MINUTES:-120}"
MANUAL_OVERRIDE="${RESEARCH_REFRESH_MANUAL_OVERRIDE:-0}"
TEST_OVERRIDE="${RESEARCH_REFRESH_TEST_OVERRIDE:-0}"
NOW_ET="${RESEARCH_REFRESH_NOW_ET:-}"
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

if [ -n "$NOW_ET" ] && [ "$TEST_OVERRIDE" != "1" ]; then
  echo "GUARD_STATE_REJECTED: RESEARCH_REFRESH_NOW_ET requires RESEARCH_REFRESH_TEST_OVERRIDE=1"
  exit 7
fi
NOW_ARGS=()
[ -n "$NOW_ET" ] && NOW_ARGS=(--now "$NOW_ET")
WINDOW_ARGS=()
[ "$MANUAL_OVERRIDE" = "1" ] && WINDOW_ARGS=(--manual-override)
"$UV" run python -m tools.research_refresh_guard window \
  "${NOW_ARGS[@]}" "${WINDOW_ARGS[@]}"
WINDOW_RC=$?
if [ "$WINDOW_RC" -ne 0 ]; then
  echo "SCHEDULE_BLOCKED: research refresh is weekday premarket only"
  exit "$WINDOW_RC"
fi

if [ -z "$RITUAL_ROOT" ]; then
  echo "UPSTREAM_BLOCKED: RESEARCH_RITUAL_ROOT is not configured"
  exit 3
fi

SLOT="premarket"

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

# The durable final manifest is the authoritative idempotency record. A prior
# run may have finalized successfully and then crashed before writing the
# convenience slot receipt below; verify the final bundle against the current
# ritual binding before spending again.
FINAL_MANIFEST="$REPO/reports/attractiveness_research/$AS_OF/manifest.json"
EXISTING_FINAL_META="$LOGDIR/existing_final_${STAMP}.json"
if [ -f "$FINAL_MANIFEST" ] \
  && "$UV" run python -m tools.research_context_assemble \
    --verify --bundle-only --ritual-root "$RITUAL_ROOT" \
    --receipt-out "$EXISTING_FINAL_META"; then
  echo "SKIP: verified final research for ${AS_OF} already binds the current ritual"
  exit 0
fi

RECEIPT="$LOGDIR/receipt_v2_${AS_OF}_${SLOT}.json"
if [ -f "$RECEIPT" ]; then
  echo "INFO: prior slot receipt exists; final manifest must still verify and reconcile"
fi

write_slot_receipt() {
  local meta_path="$1"
  local run_id
  local producer_attempt_id
  local context_sha
  local ritual_status_sha
  local ritual_receipt_sha
  local receipt_tmp
  run_id="$(sed -n 's/.*"run_id":"\([^"]*\)".*/\1/p' "$meta_path" | tail -1)"
  producer_attempt_id="$(sed -n 's/.*"producer_attempt_id":"\([^"]*\)".*/\1/p' "$meta_path" | tail -1)"
  context_sha="$(sed -n 's/.*"context_sha256":"\([^"]*\)".*/\1/p' "$meta_path" | tail -1)"
  ritual_status_sha="$(sed -n 's/.*"ritual_run_status_sha256":"\([^"]*\)".*/\1/p' "$meta_path" | tail -1)"
  ritual_receipt_sha="$(sed -n 's/.*"ritual_receipt_sha256":"\([^"]*\)".*/\1/p' "$meta_path" | tail -1)"
  if [ -z "$run_id" ] || [ -z "$producer_attempt_id" ] || [ -z "$context_sha" ] || [ -z "$ritual_status_sha" ] || [ -z "$ritual_receipt_sha" ]; then
    echo "CRITICAL: verified final receipt metadata is incomplete"
    return 1
  fi
  receipt_tmp="$RECEIPT.${STAMP}.$$.tmp"
  printf '%s\n' \
    "{\"schema_version\":\"attractiveness_research/v2\",\"as_of\":\"${AS_OF}\",\"slot\":\"${SLOT}\",\"run_id\":\"${run_id}\",\"producer_attempt_id\":\"${producer_attempt_id}\",\"context_sha256\":\"${context_sha}\",\"ritual_run_status_sha256\":\"${ritual_status_sha}\",\"ritual_receipt_sha256\":\"${ritual_receipt_sha}\",\"status\":\"ok\"}" \
    > "$receipt_tmp"
  mv "$receipt_tmp" "$RECEIPT"
}

verify_reconcile_final() {
  local receipt_meta="$1"
  "$UV" run python -m tools.research_context_assemble \
    --verify --bundle-only --ritual-root "$RITUAL_ROOT"
  local verify_rc=$?
  [ "$verify_rc" -eq 0 ] || return 1
  "$UV" run python -m tools.research_context_assemble \
    --verify --bundle-only --ritual-root "$RITUAL_ROOT" \
    --reconcile-published-attempt --guard-state-dir "$STATE_DIR" \
    --receipt-out "$receipt_meta"
  local reconcile_rc=$?
  [ "$reconcile_rc" -eq 0 ] || return 2
  return 0
}

FINAL_MANIFEST="${RESEARCH_REFRESH_FINAL_MANIFEST:-$REPO/reports/attractiveness_research/$AS_OF/manifest.json}"
if [ "$FINAL_MANIFEST" != "$REPO/reports/attractiveness_research/$AS_OF/manifest.json" ] && [ "$TEST_OVERRIDE" != "1" ]; then
  echo "GUARD_STATE_REJECTED: RESEARCH_REFRESH_FINAL_MANIFEST requires RESEARCH_REFRESH_TEST_OVERRIDE=1"
  exit 7
fi
if [ -f "$FINAL_MANIFEST" ]; then
  RECOVERY_META="$LOGDIR/recovery_${STAMP}.json"
  verify_reconcile_final "$RECOVERY_META"
  RECOVERY_RC=$?
  if [ "$RECOVERY_RC" -eq 0 ]; then
    write_slot_receipt "$RECOVERY_META" || exit 1
    echo "RECOVERED: valid final manifest reconciled before LLM invocation"
    exit 0
  fi
  if [ "$RECOVERY_RC" -eq 2 ]; then
    echo "CRITICAL: final manifest verified but its paid attempt could not be reconciled"
    exit 1
  fi
  echo "INFO: existing final manifest is not valid for the current board and ritual"
fi

ATTEMPT_ID="${AS_OF}_${STAMP}"
"$UV" run python -m tools.research_refresh_guard reserve \
  --state-dir "$STATE_DIR" \
  --attempt-id "$ATTEMPT_ID" \
  --attempt-budget-usd "$ATTEMPT_BUDGET_USD" \
  --monthly-budget-usd "$MONTHLY_BUDGET_USD" \
  --max-failures "$MAX_FAILURES" \
  --stale-minutes "$STALE_MINUTES" \
  "${NOW_ARGS[@]}"
GUARD_RC=$?
if [ "$GUARD_RC" -ne 0 ]; then
  echo "CIRCUIT_BLOCKED: LLM invocation was not attempted"
  exit "$GUARD_RC"
fi

record_failure() {
  "$UV" run python -m tools.research_refresh_guard record \
    --state-dir "$STATE_DIR" \
    --attempt-id "$ATTEMPT_ID" \
    --failure-class "$1" \
    "${NOW_ARGS[@]}" \
    || echo "CRITICAL: failed to persist non-secret failure classification"
}

if [ -n "$NOW_ET" ]; then
  export RESEARCH_STARTED_AT="$NOW_ET"
else
  export RESEARCH_STARTED_AT="$(TZ=UTC date +%Y-%m-%dT%H:%M:%SZ)"
fi
export RESEARCH_REFRESH_ATTEMPT_ID="$ATTEMPT_ID"
"$CLAUDE" -p "/research-refresh" \
  --model sonnet \
  --max-budget-usd "$ATTEMPT_BUDGET_USD" \
  --allowedTools "Bash Read Write Edit Grep Glob WebSearch WebFetch Task TodoWrite Skill" \
  > "$LOGDIR/claude_${STAMP}.out" 2>&1
CLAUDE_RC=$?
tail -3 "$LOGDIR/claude_${STAMP}.out"
if [ "$CLAUDE_RC" -ne 0 ]; then
  record_failure "CLAUDE_EXIT"
  echo "CRITICAL: headless research session exit ${CLAUDE_RC}"
  exit 1
fi

VERIFY_META="$LOGDIR/verify_${STAMP}.json"
if [ -f "$FINAL_MANIFEST" ]; then
  verify_reconcile_final "$VERIFY_META"
  FINAL_RC=$?
  if [ "$FINAL_RC" -ne 0 ]; then
    if [ "$FINAL_RC" -eq 1 ]; then
      record_failure "BUNDLE_VERIFY"
    fi
    echo "CRITICAL: final manifest verification or paid-attempt reconciliation failed"
    exit 1
  fi
else
  "$UV" run python -m tools.research_context_assemble \
    --verify --pending --bundle-only --ritual-root "$RITUAL_ROOT" \
    || {
      record_failure "BUNDLE_VERIFY"
      echo "CRITICAL: pending bundle verification failed before dashboard render"
      exit 1
    }
  "$UV" run python -m options_researcher.attractiveness_dashboard \
    || {
      record_failure "DASHBOARD_BUILD"
      echo "CRITICAL: dashboard rebuild failed"
      exit 1
    }
  "$UV" run python -m tools.research_context_assemble \
    --finalize --ritual-root "$RITUAL_ROOT"
  VERIFY_RC=$?
  if [ "$VERIFY_RC" -ne 0 ]; then
    record_failure "FINAL_VERIFY"
    echo "CRITICAL: dashboard verification failed — no final manifest was published"
    exit 1
  fi
  verify_reconcile_final "$VERIFY_META"
  FINAL_RC=$?
  if [ "$FINAL_RC" -ne 0 ]; then
    echo "CRITICAL: final manifest published but paid-attempt reconciliation failed"
    exit 1
  fi
fi

RUN_ID="$(sed -n 's/.*"run_id":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
PRODUCER_ATTEMPT_ID="$(sed -n 's/.*"producer_attempt_id":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
CONTEXT_SHA="$(sed -n 's/.*"context_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
RITUAL_STATUS_SHA="$(sed -n 's/.*"ritual_run_status_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
RITUAL_RECEIPT_SHA="$(sed -n 's/.*"ritual_receipt_sha256":"\([^"]*\)".*/\1/p' "$VERIFY_META" | tail -1)"
if [ -z "$RUN_ID" ] || [ -z "$PRODUCER_ATTEMPT_ID" ] || [ -z "$CONTEXT_SHA" ] || [ -z "$RITUAL_STATUS_SHA" ] || [ -z "$RITUAL_RECEIPT_SHA" ]; then
  record_failure "FINAL_VERIFY"
  echo "CRITICAL: verified receipt metadata is incomplete"
  exit 1
fi
if [ "$PRODUCER_ATTEMPT_ID" != "$ATTEMPT_ID" ]; then
  "$UV" run python -m tools.research_refresh_guard record \
    --state-dir "$STATE_DIR" \
    --attempt-id "$ATTEMPT_ID" \
    --success \
    "${NOW_ARGS[@]}" \
    || {
      echo "CRITICAL: could not close the current paid attempt"
      exit 1
    }
fi
write_slot_receipt "$VERIFY_META" || exit 1
echo "RESULT: OK ${AS_OF} ${SLOT} run_id=${RUN_ID}"
echo "NOTE: generated research artifacts remain uncommitted for review"

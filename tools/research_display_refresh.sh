#!/bin/zsh
set -u

REPO_ROOT="${0:A:h:h}"
PYTHON_BIN="${RESEARCH_DISPLAY_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
DASHBOARD_DIR="${RESEARCH_DISPLAY_DASHBOARD_DIR:-${REPO_ROOT}/.tmp/dashboard}"
STATUS_PATH="${DASHBOARD_DIR}/research-views-status.txt"
STATUS_TEMP="${STATUS_PATH}.$$.tmp"

mkdir -p "$DASHBOARD_DIR"
trap 'rm -f "$STATUS_TEMP"' EXIT

"$PYTHON_BIN" -m options_researcher.experiments_dashboard
experiments_exit=$?

"$PYTHON_BIN" -m options_researcher.regime_report \
  --out "$DASHBOARD_DIR/wasserstein-regime.txt"
wasserstein_exit=$?

timestamp_et="$(TZ=America/New_York date '+%Y-%m-%dT%H:%M:%S%z')"

if [[ "$experiments_exit" -eq 0 ]]; then
  experiments_status="OK"
else
  experiments_status="FAILED"
fi

if [[ "$wasserstein_exit" -eq 0 ]]; then
  wasserstein_status="OK"
else
  wasserstein_status="FAILED"
fi

{
  print -r -- "research views refresh: $timestamp_et"
  print -r -- "experiments: $experiments_status exit=$experiments_exit"
  print -r -- "wasserstein: $wasserstein_status exit=$wasserstein_exit"
} > "$STATUS_TEMP"
mv -f -- "$STATUS_TEMP" "$STATUS_PATH"

if [[ "$experiments_exit" -ne 0 || "$wasserstein_exit" -ne 0 ]]; then
  exit 1
fi

exit 0

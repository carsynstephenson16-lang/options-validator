#!/bin/zsh
set -u

REPO_ROOT="${0:A:h:h}"
PYTHON_BIN="${RESEARCH_DISPLAY_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
DASHBOARD_DIR="${RESEARCH_DISPLAY_DASHBOARD_DIR:-${REPO_ROOT}/.tmp/dashboard}"
STATUS_PATH="${DASHBOARD_DIR}/research-views-status.txt"
STATUS_TEMP="${STATUS_PATH}.$$.tmp"
WASSERSTEIN_PATH="${DASHBOARD_DIR}/wasserstein-regime.txt"
WASSERSTEIN_TEMP="${WASSERSTEIN_PATH}.$$.tmp"

if ! mkdir -p "$DASHBOARD_DIR"; then
  print -u2 -r -- "failed to create dashboard directory: $DASHBOARD_DIR"
  exit 1
fi
trap 'rm -f "$STATUS_TEMP" "$WASSERSTEIN_TEMP"' EXIT

"$PYTHON_BIN" -m options_researcher.experiments_dashboard
experiments_exit=$?

"$PYTHON_BIN" -m options_researcher.regime_report \
  --out "$WASSERSTEIN_TEMP"
wasserstein_exit=$?

if [[ "$wasserstein_exit" -eq 0 ]]; then
  mv -f -- "$WASSERSTEIN_TEMP" "$WASSERSTEIN_PATH"
  wasserstein_publish_exit=$?
  if [[ "$wasserstein_publish_exit" -ne 0 ]]; then
    wasserstein_exit=$wasserstein_publish_exit
  fi
else
  rm -f -- "$WASSERSTEIN_TEMP"
fi

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

if [[ -d "$STATUS_PATH" ]]; then
  print -u2 -r -- "failed to publish research views status: $STATUS_PATH is a directory"
  exit 1
fi

{
  print -r -- "research views refresh: $timestamp_et"
  print -r -- "experiments: $experiments_status exit=$experiments_exit"
  print -r -- "wasserstein: $wasserstein_status exit=$wasserstein_exit"
} > "$STATUS_TEMP"
status_write_exit=$?

if [[ "$status_write_exit" -ne 0 ]]; then
  print -u2 -r -- "failed to write research views status: $STATUS_TEMP"
  exit 1
fi

mv -f -- "$STATUS_TEMP" "$STATUS_PATH"
status_rename_exit=$?

if [[ "$status_rename_exit" -ne 0 ]]; then
  print -u2 -r -- "failed to publish research views status: $STATUS_PATH"
  exit 1
fi

if [[ "$experiments_exit" -ne 0 || "$wasserstein_exit" -ne 0 ]]; then
  exit 1
fi

exit 0

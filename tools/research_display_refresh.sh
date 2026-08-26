#!/bin/zsh
set -u

REPO_ROOT="${0:A:h:h}"
if ! cd "$REPO_ROOT"; then
  print -u2 -r -- "failed to enter repo root: $REPO_ROOT"
  exit 1
fi

PYTHON_BIN="${RESEARCH_DISPLAY_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
DASHBOARD_DIR="${RESEARCH_DISPLAY_DASHBOARD_DIR:-${REPO_ROOT}/.tmp/dashboard}"
EVALUATION_DATE="$(TZ=America/New_York date '+%Y-%m-%d')"

begin_output="$($PYTHON_BIN -m options_researcher.research_views_publication begin \
  --dashboard-dir "$DASHBOARD_DIR")"
begin_exit=$?
if [[ "$begin_exit" -ne 0 ]]; then
  print -u2 -r -- "failed to initialize research-view generation"
  exit "$begin_exit"
fi
begin_lines=("${(@f)begin_output}")
if [[ "${#begin_lines}" -ne 3 ]]; then
  print -u2 -r -- "publication helper returned an invalid begin receipt"
  exit 1
fi
generation_id="${begin_lines[1]}"
attempted_at="${begin_lines[2]}"
staging_dir="${begin_lines[3]}"

"$PYTHON_BIN" -m options_researcher.experiments_dashboard \
  --out "$staging_dir/experiments.html" \
  --evaluation-date "$EVALUATION_DATE"
experiments_exit=$?

"$PYTHON_BIN" -m options_researcher.regime_report \
  --out "$staging_dir/wasserstein-regime.txt" \
  --json-out "$staging_dir/wasserstein-regime.json" \
  --evaluation-date "$EVALUATION_DATE"
wasserstein_exit=$?

"$PYTHON_BIN" -m options_researcher.research_views_publication finish \
  --dashboard-dir "$DASHBOARD_DIR" \
  --staging-dir "$staging_dir" \
  --generation-id "$generation_id" \
  --attempted-at "$attempted_at" \
  --producer-root "$REPO_ROOT" \
  --experiments-exit "$experiments_exit" \
  --wasserstein-exit "$wasserstein_exit"
finish_exit=$?

if [[ "$experiments_exit" -ne 0 || "$wasserstein_exit" -ne 0 ]]; then
  exit 1
fi
exit "$finish_exit"

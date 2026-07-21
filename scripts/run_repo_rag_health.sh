#!/bin/bash
# Scheduled, advisory-only RAG health run. It cannot modify H7 state, ledgers,
# positions, hypotheses, execution behavior, or any trading decision path.
set -euo pipefail

REPO="/Users/carsynstephenson/options-validator"
APP="$REPO/tools/repo_rag"
LOG_DIR="$APP/logs"
STAMP="$(date '+%Y-%m-%dT%H%M%S')"
LOG="$LOG_DIR/repo_rag_health_${STAMP}.log"

mkdir -p "$LOG_DIR"
{
  echo "=== repo-rag health $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
  cd "$APP"
  /usr/bin/env python3 -m repo_rag health
} >>"$LOG" 2>&1

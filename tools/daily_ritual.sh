#!/bin/zsh
# Automated daily ritual — frozen operator order per H7 amendment v1.4
# (2026-07-14): topup -> source health -> data gate (HARD) -> h7_watch ->
# h6_features -> h6_watch [-> h8_watch if built] -> dashboards.
# Owner-authorized for unattended cron use 2026-07-15. Alert-only: this
# script takes ZERO book actions; a failing gate stopping the run IS the
# system working. Logs to .tmp/daily_ritual/.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
REPO="/Users/carsynstephenson/options-validator"
UV="$HOME/.local/bin/uv"
cd "$REPO" || exit 2

LOGDIR="$REPO/.tmp/daily_ritual"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

SUMMARY=""
note() { SUMMARY="${SUMMARY}$1\n"; echo ">>> $1"; }

echo "=== daily ritual ${STAMP} ==="

# Preflight — ThetaData auth. PATH C (data/thetadata_adapter.py) uses a direct
# API key over HTTP against the remote MDDS: NO local ThetaTerminal process,
# no port to start. The only unattended dependency is THETADATA_API_KEY
# resolving from .env — which load_dotenv() reads relative to this working
# directory (set above by `cd $REPO`). Surface a missing key LOUDLY rather
# than letting the top-up fail into a silently stale board.
if "$UV" run python -c 'from data.thetadata_adapter import _resolve_api_key; _resolve_api_key()' 2>/dev/null; then
  KEY_OK=1
else
  KEY_OK=0
  note "ThetaData API key: NOT RESOLVED from .env — top-up cannot fetch; board will be STALE"
fi

# Step 0 — recent-day top-up (fetches yesterday's finalized EOD via the keyed
# HTTP adapter; skips cleanly if the key is absent or the subscription lapsed).
if [ "$KEY_OK" -eq 1 ] && "$UV" run python data/recent_topup.py --scope h7 --refresh-closes; then
  note "topup: OK (closes refreshed)"
else
  note "topup: FAILED/SKIPPED (no key or subscription lapsed) — running on cached data"
fi

# Step 1 — source health (run AND record; per-name ban, never blocks board).
if "$UV" run python -m options_researcher.h7_source_health; then
  note "source health: HEALTHY"
else
  note "source health: exit 1 — per-name entry bans apply (fail-closed in watcher)"
fi

# Step 2 — data gate (HARD GATE; NO_GO blocks the watchers, no override).
if "$UV" run python -m options_researcher.h7_data_gate; then
  note "data gate: GO"
  GATE_GO=1
else
  note "data gate: NO_GO — watchers NOT run (this is the system working)"
  GATE_GO=0
fi

# LumiBot import banners can land on stdout — keep only the final date line.
AS_OF="$("$UV" run python -c 'from datetime import date; from options_researcher.h7_watch import evaluation_session; print(evaluation_session(date.today()))' | grep -Eo '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | tail -1)"
if [ -z "$AS_OF" ]; then
  note "evaluation session: FAILED to resolve — H6/H8 leg skipped"
  GATE_GO=0
fi
note "evaluation session: ${AS_OF}"

if [ "$GATE_GO" -eq 1 ]; then
  # Step 3 — H7 watcher (alerts only).
  "$UV" run python -m options_researcher.h7_watch && note "h7_watch: ran" || note "h7_watch: NONZERO EXIT"

  # Step 4 — H6 leg (exact-session; features rebuild is mandatory after topup).
  "$UV" run python -m options_researcher.h6_features --as-of "$AS_OF" && note "h6_features: rebuilt" || note "h6_features: NONZERO EXIT"
  "$UV" run python -m options_researcher.h6_watch --as-of "$AS_OF" && note "h6_watch: ran" || note "h6_watch: NONZERO EXIT"

  # Step 5 — H8 watcher, only once its tooling exists (registered lanes only).
  if "$UV" run python -c 'import options_researcher.h8_watch' 2>/dev/null; then
    "$UV" run python -m options_researcher.h8_watch --as-of "$AS_OF" && note "h8_watch: ran" || note "h8_watch: NONZERO EXIT"
  fi
fi

# QM dashboard context requires the exact completed session. Refresh only
# missing/stale OHLCV names, then fail visibly if Yahoo cannot supply AS_OF.
# The attractiveness dashboard still rebuilds: its QM list will show three
# DATA BLOCKED slots while the unchanged mechanical list remains available.
if [ -n "$AS_OF" ]; then
  "$UV" run python -m options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF" \
    && note "QM OHLCV: exact-session current to $AS_OF" \
    || note "QM OHLCV: FAILED/STALE — QM Top 3 will show DATA BLOCKED"
else
  note "QM OHLCV: SKIPPED (no evaluation session) — QM Top 3 will show DATA BLOCKED"
fi

# Attractiveness feature store — separate from the H6 manifested store
# (.tmp/research/attractiveness vs .tmp/research; a shared path corrupted the
# H6 AMZN manifest 2026-07-16). Rebuild to the evaluation session so the
# dashboard's IV-ranks are never silently stale at BACKTEST_END.
if [ -n "$AS_OF" ]; then
  "$UV" run python -c "from options_researcher.features import build_all; build_all('$AS_OF')" \
    && note "attractiveness features: rebuilt to $AS_OF" \
    || note "attractiveness features: FAILED — dashboard will flag stale/missing features"
else
  note "attractiveness features: SKIPPED (no evaluation session)"
fi

# Dashboards rebuild regardless of gate state — they display cached truth
# and carry their own honest data-as-of banner.
"$UV" run python -m options_researcher.dashboard && note "dashboard: rebuilt" || note "dashboard: FAILED"
"$UV" run python -m options_researcher.attractiveness_dashboard && note "attractiveness dashboard: rebuilt" || note "attractiveness dashboard: FAILED"

echo "=== summary ==="
printf "%b" "$SUMMARY"

# Surface completion without requiring the owner to ask.
/usr/bin/osascript -e "display notification \"$(printf '%b' "$SUMMARY" | head -c 220 | tr '"' "'")\" with title \"options-validator daily ritual\" subtitle \"session ${AS_OF} — log: .tmp/daily_ritual/${STAMP}.log\"" 2>/dev/null

exit 0

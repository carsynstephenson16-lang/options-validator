#!/bin/zsh
# Automated daily ritual — frozen operator order per H7 amendment v1.4
# (2026-07-14): source health -> data gate (HARD) -> h7 exit
# management -> QM OHLCV refresh -> attractiveness feature rebuild ->
# h7_watch -> h6_features -> h6_watch -> h5 entry_watch [-> h8_watch if
# built] -> h10_watch/h10_observe -> dashboards. The QM OHLCV refresh and
# attractiveness feature rebuild moved ahead of h10_watch/h10_observe and
# h5 entry_watch on 2026-07-24 (H10_RITUAL_ORDER_FIX, facts.log): each
# consumer was running BEFORE its own data refresh, producing false
# DATA/stale-IV-rank skips (see the 2026-07-24 07:10 production log).
# A read-only tracked authority preflight runs before log creation or any
# receipt, ledger, paper-book, Git, backup, or provider surface. It never
# places a broker order. TWO TIERS gate this script (brief 11 §6.2):
# require-data is the only top gate and covers the daily non-verdict-bearing
# data/display phase; require-full fences the H7 surfaces, which are NOT
# contiguous -- region A and region B sandwich an unfenced data-tier island.
# The frozen consumer order above is unchanged by that fencing: it adds
# if/fi lines and moves no step relative to any other step.
# Logs for full runs go to .tmp/daily_ritual/.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
# Derive the repo root from THIS script's own location rather than hardcoding
# one checkout. A hardcoded path silently binds the unattended ritual to
# whatever branch that one directory happens to be on -- on 2026-07-20 a
# concurrent agent left it on an in-progress feature branch, which would have
# run unreviewed code against the real H7 ledger. Deriving the root lets the
# ritual live in a dedicated ops worktree; the branch guard below is the
# backstop that makes a wrong branch fail loudly instead of silently.
REPO="${0:A:h:h}"
UV="$HOME/.local/bin/uv"
PYTHON="$REPO/.venv/bin/python"
cd "$REPO" || exit 2

if [ ! -x "$PYTHON" ]; then
  echo "ritual authority unavailable: expected installed interpreter at $PYTHON" >&2
  exit 2
fi

RITUAL_MODE="${1:-run}"
if [ "$RITUAL_MODE" = "status" ]; then
  exec env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority status
fi
if [ "$RITUAL_MODE" != "run" ]; then
  echo "usage: tools/daily_ritual.sh [run|status]" >&2
  exit 2
fi

# This gate is deliberately before mkdir/log redirection and every stateful
# surface below. A blocked full run emits only the read-only JSON status to
# stdout and exits; it does not create a success-shaped ritual artifact.
# Data tier (brief 11 §6.2): authorizes the daily non-verdict-bearing
# data/display phase to run from cached data. It asserts NOTHING about a live
# exact-session source and NOTHING about H7 -- those stay behind the inner
# require-full gate below.
env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority require-data
AUTHORITY_RC=$?
if [ "$AUTHORITY_RC" -ne 0 ]; then
  echo "RITUAL STATUS: BLOCKED BY TRACKED AUTHORITY (data phase)"
  exit "$AUTHORITY_RC"
fi

LOGDIR="$REPO/.tmp/daily_ritual"
mkdir -p "$LOGDIR"
STAMP="$(date +%Y-%m-%d_%H%M)"
LOG="$LOGDIR/${STAMP}.log"
exec > "$LOG" 2>&1

SUMMARY=""
note() { SUMMARY="${SUMMARY}$1\n"; echo ">>> $1"; }
CRITICAL=0
# CRIT_COUNT/STARVED_CRIT exist so the notification title can distinguish "the
# only CRITICAL is the expected starved-lane capture receipt" from "something
# is actually broken" WITHOUT grepping $SUMMARY (brief 11 §6.4): any future
# CRITICAL whose text happened to contain "capture receipt" would otherwise
# silently downgrade a genuinely broken run. STARVED_CRIT is set at exactly one
# call site -- the capture receipt's failure branch.
CRIT_COUNT=0
STARVED_CRIT=0
DATA_STARVED=0
crit() { CRITICAL=1; CRIT_COUNT=$((CRIT_COUNT + 1)); note "CRITICAL: $1"; }

echo "=== daily ritual ${STAMP} ==="
echo "repo: ${REPO}"

# Branch guard (fail-closed). The unattended ritual must only ever run
# committed, merged code from main. Running a feature branch means running
# unreviewed work against the REAL H7 forward ledger during a live verdict
# window -- refuse loudly rather than produce alerts nobody can trust.
RITUAL_BRANCH="$(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [ "$RITUAL_BRANCH" != "main" ]; then
  crit "checkout is on '${RITUAL_BRANCH}', not main -- refusing to run the unattended ritual from unmerged code"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  /usr/bin/osascript -e "display notification \"on '${RITUAL_BRANCH}', not main -- ritual refused\" with title \"[BROKEN] options-validator daily ritual\" subtitle \"repo: ${REPO}\"" 2>/dev/null
  exit 1
fi
if [ "$(git -C "$REPO" rev-parse HEAD 2>/dev/null)" != "$(git -C "$REPO" rev-parse origin/main 2>/dev/null)" ]; then
  crit "main is not exactly aligned with origin/main -- refusing cache publisher authority"
  echo "=== summary ==="
  printf "%b" "$SUMMARY"
  exit 1
fi
# Single-writer cache authority. data/thetadata_adapter.py independently
# verifies this role, repository root, main branch, and origin/main identity
# before any OOS cache or BLIND_CACHE fact mutation.
export OPTIONS_VALIDATOR_CACHE_ROLE=publisher

# Step 1 — source health (run AND record; per-name ban, never blocks board).
# One-door repair (e64e5e9) receipt chain: the gate must LINK the health
# receipt, and the watcher refuses without a linked gate receipt — so thread
# the receipt paths through. --as-of maps today to the last completed session
# so all three receipts agree on evaluation_session (a bare run stamps the
# calendar date and the chain refuses on Mondays/holidays).
RUN_DATE="$(TZ=America/New_York date +%F)"
AS_OF="$("$UV" run python -c 'from datetime import date; from options_researcher.h7_watch import evaluation_session; print(evaluation_session(date.today()))' | grep -Eo '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' | tail -1)"
SCOPE_ID="$("$UV" run python -c 'from options_researcher.h7_scope import scope_identity; print(scope_identity()["scope_id"])' | grep -Eo '^[A-Za-z0-9._-]+$' | tail -1)"
if [ -z "$AS_OF" ]; then
  crit "evaluation session: FAILED to resolve — H6/H8 leg skipped"
fi
if [ -z "$SCOPE_ID" ]; then
  crit "H7 scope identity: FAILED to resolve — receipt reuse unavailable"
fi

# Cache-edge honesty note (brief 11 §6.3). Deliberately implemented in the
# shell and NOT in options_researcher/ritual_receipt.py: putting an
# explanatory string in Python would change diagnostic_source_hash. The
# machine-readable capture receipt keeps its exact current semantics and
# status vocabulary; no new capture status is introduced here.
CHAIN_EDGE="$(ls .cache/chains 2>/dev/null | sed -n 's/.*_\([0-9-]\{10\}\)\.parquet$/\1/p' | sort -u | tail -1)"
note "canonical chain cache edge: ${CHAIN_EDGE:-none} (evaluation session ${AS_OF})"
if [ -n "$CHAIN_EDGE" ] && [ "$CHAIN_EDGE" \< "$AS_OF" ]; then
  DATA_STARVED=1
  note "chain-dependent lanes are STARVED: no exact-session chain for ${AS_OF} (cache frozen at ${CHAIN_EDGE}; OD-2/OD-4 forbid refill)"
fi
if [ -n "$AS_OF" ]; then
  "$UV" run python -m options_researcher.ritual_status \
    --root "$REPO" --as-of "$AS_OF" --run-date "$RUN_DATE" \
    --status RUNNING --log-path "$LOG" \
    && note "ritual status: RUNNING marker published" \
    || crit "ritual status: could not invalidate prior terminal status"
fi
# Evaluate the FULL-tier authority ONCE and reuse the return code for both
# fenced regions below (brief 11 §6.2). The H7 surfaces are NOT contiguous:
# region A and region B sandwich a data-tier island that must keep running
# every day, so the fence is applied twice rather than as one wrap.
env PYTHONDONTWRITEBYTECODE=1 "$PYTHON" -m data.ritual_authority require-full
FULL_AUTHORITY_RC=$?

# ---- full-tier region A (brief 11 §6.2) ----
if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then
  EXPECTED_SH_RECEIPT="reports/h7_receipts/${SCOPE_ID}/source_health/${AS_OF}.json"
  EXPECTED_DG_RECEIPT="reports/h7_data_gate/${SCOPE_ID}/receipts/${AS_OF}.json"
  SH_OUT="$("$UV" run python -m options_researcher.h7_source_health --as-of "$RUN_DATE" 2>&1)"
  SH_RC=$?
  echo "$SH_OUT"
  SH_RECEIPT="$(echo "$SH_OUT" | grep -Eo 'receipt=[^ ;]+' | tail -1 | cut -d= -f2)"
  if [ "$SH_RC" -eq 0 ]; then
    note "source health: HEALTHY"
  else
    note "source health: exit ${SH_RC} — per-name entry bans apply (fail-closed in watcher)"
  fi
  if [ -z "$SH_RECEIPT" ] || [ ! -f "$SH_RECEIPT" ]; then
    if [ -n "$AS_OF" ] && [ -n "$SCOPE_ID" ] && [ -f "$EXPECTED_SH_RECEIPT" ]; then
      note "source-health receipt: already exists for this session (immutable; benign re-run) — reusing $EXPECTED_SH_RECEIPT"
      SH_RECEIPT="$EXPECTED_SH_RECEIPT"
    else
      crit "source-health receipt could not be produced and none exists on disk"
      SH_RECEIPT=""
    fi
  fi

  # Step 2 — data gate (HARD GATE; NO_GO blocks the watchers, no override).
  # Same-day re-runs: receipts are immutable but replay-identical; if inputs
  # changed intraday the gate refuses to overwrite — that refusal is the
  # system working, not a bug. Delete nothing; wait for the next session.
  GATE_ARGS=()
  [ -n "$SH_RECEIPT" ] && GATE_ARGS=(--source-health-receipt "$SH_RECEIPT")
  DG_OUT="$("$UV" run python -m options_researcher.h7_data_gate "${GATE_ARGS[@]}" 2>&1)"
  DG_RC=$?
  echo "$DG_OUT"
  DG_RECEIPT="$(echo "$DG_OUT" | sed -n 's/^immutable receipt //p' | tail -1)"
  if [ -z "$DG_RECEIPT" ] || [ ! -f "$DG_RECEIPT" ]; then
    if [ -n "$AS_OF" ] && [ -n "$SCOPE_ID" ] && [ -f "$EXPECTED_DG_RECEIPT" ]; then
      note "data-gate receipt: already exists for this session (immutable; benign re-run) — reusing $EXPECTED_DG_RECEIPT"
      DG_RECEIPT="$EXPECTED_DG_RECEIPT"
    else
      crit "data-gate receipt could not be produced and none exists on disk"
      DG_RECEIPT=""
    fi
  fi

  GATE_GO=0
  if [ -n "$DG_RECEIPT" ] && [ -f "$DG_RECEIPT" ]; then
    DG_VERDICT_OUT="$("$UV" run python -c 'import sys; from pathlib import Path; from research.receipts import load_receipt; print(load_receipt(Path(sys.argv[1]), expected_type="data_gate")["whole_universe_verdict"])' "$DG_RECEIPT" 2>&1)"
    DG_VERDICT_RC=$?
    DG_VERDICT="$(printf '%s\n' "$DG_VERDICT_OUT" | grep -E '^(GO|NO_GO)$' | tail -1)"
    if [ "$DG_VERDICT_RC" -ne 0 ]; then
      crit "data-gate receipt exists but could not be read"
    elif [ "$DG_VERDICT" = "GO" ]; then
      if [ "$DG_RC" -eq 0 ]; then
        note "data gate: GO"
      else
        note "data gate: GO (reused immutable receipt)"
      fi
      GATE_GO=1
    elif [ "$DG_VERDICT" = "NO_GO" ]; then
      note "data gate: NO_GO — watchers NOT run (this is the system working)"
    else
      crit "data-gate receipt has unexpected verdict: $DG_VERDICT"
    fi
  fi
  note "evaluation session: ${AS_OF}"

  # Step 2c — H7 real-paper exit management. This is intentionally outside
  # GATE_GO: a NO_GO must create an honest exit data-gap/retry record rather than
  # silently leave an existing paper position unmanaged. Due fills/retries go
  # first; the observation pass then includes every position still open. Neither
  # command has a network or broker-order surface.
  H7_EXIT_READY=0
  if [ -z "$AS_OF" ] || [ -z "$DG_RECEIPT" ] || [ ! -f "$DG_RECEIPT" ]; then
    crit "h7 exit management: receipt/evaluation session unavailable — H7 entry path blocked"
  else
    # No output capture here (banner-pollution guard): these two calls' stdout
    # was previously captured into a variable purely to be echoed straight back
    # -- nothing ever parsed a value out of it. exec above already redirects
    # this whole script's stdout+stderr to $LOG, so letting the process write
    # directly gets the exact same log content without a needless capture that
    # would otherwise hold LumiBot v4.5.63's import-time banner line.
    "$UV" run python -m options_researcher.h7_exit_session fill \
      --data-gate-receipt "$DG_RECEIPT" \
      --decision-session "$RUN_DATE" \
      --source-evaluation-session "$AS_OF"
    EXIT_FILL_RC=$?
    if [ "$EXIT_FILL_RC" -eq 0 ]; then
      note "h7 exit fill: ran"
    else
      crit "h7 exit fill: REFUSED (exit ${EXIT_FILL_RC}) — H7 entry path blocked"
    fi

    "$UV" run python -m options_researcher.h7_exit_session monitor \
      --data-gate-receipt "$DG_RECEIPT" \
      --decision-session "$RUN_DATE" \
      --source-evaluation-session "$AS_OF"
    EXIT_MONITOR_RC=$?
    if [ "$EXIT_MONITOR_RC" -eq 0 ]; then
      note "h7 exit monitor: ran"
    else
      crit "h7 exit monitor: REFUSED (exit ${EXIT_MONITOR_RC}) — H7 entry path blocked"
    fi

    if [ "$EXIT_FILL_RC" -eq 0 ] && [ "$EXIT_MONITOR_RC" -eq 0 ]; then
      H7_EXIT_READY=1
    fi
  fi
else
  # A deliberately paused lane is not a failure: note, never crit. Today's
  # crit would fire every single day under the data tier and train the
  # operator to ignore CRITICAL lines.
  GATE_GO=0
  H7_EXIT_READY=0
  note "H7 lanes: PAUSED — full ritual authority not granted (h7_active / exact-session source)"
fi
# ---- end full-tier region A ----

# ---- data-tier island (brief 11 §6.2) — UNFENCED, runs every day ----
# These are the only steps that actually produce anything under the data tier.
# Fencing them behind require-full would leave a "switch-on" that switches
# nothing on, so they deliberately sit BETWEEN the two full-tier regions.
#
# QM OHLCV refresh and the attractiveness feature rebuild run BEFORE the
# GATE_GO block below (moved 2026-07-24 in the ritual-grace integration wave,
# merge 7c39a70; a facts.log entry for the move was never appended):
# Step 5b (H10 watcher/observe) reads underlying OHLCV via
# data/underlying_ohlcv.py's load_ohlcv/load_ohlcv_adjusted, and Step 4b
# (H5 entry_watch) reads IV-rank via options_researcher/features.py
# load_features() -- both are refreshers for stores those consumers read
# moments later, and running the refresh first (not after) is the fix.
# They stay unconditional on GATE_GO -- dashboards must rebuild off cached
# truth regardless of gate state -- only their position moved.

# QM dashboard context requires the exact completed session. Refresh only
# missing/stale OHLCV for names covered by the frozen QM sidecar; an uncovered
# name is rejected before cache read/write. The attractiveness dashboard still
# rebuilds: its QM context will show three DATA BLOCKED slots while the
# unchanged mechanical list remains available.
if [ -n "$AS_OF" ]; then
  "$UV" run python -m options_researcher.qm_dashboard --refresh-ohlcv --as-of "$AS_OF" \
    && note "QM OHLCV: exact-session current to $AS_OF" \
    || note "QM OHLCV: FAILED/STALE — QM context will show DATA BLOCKED"
else
  note "QM OHLCV: SKIPPED (no evaluation session) — QM context will show DATA BLOCKED"
fi

# Attractiveness feature store — separate from the H6 manifested store
# (.tmp/research/attractiveness vs .tmp/research; a shared path corrupted the
# H6 AMZN manifest 2026-07-16). Rebuild to the evaluation session so the
# dashboard's IV-ranks are never silently stale at BACKTEST_END, and so
# Step 4b's entry_watch (which reads this same store) never reads yesterday's
# IV-rank against today's close.
if [ -n "$AS_OF" ]; then
  "$UV" run python -c "from options_researcher.features import build_all; from options_researcher.h7_scope import watch_universe; build_all('$AS_OF', symbols=watch_universe())" \
    && note "attractiveness features: rebuilt to $AS_OF" \
    || note "attractiveness features: FAILED — dashboard will flag stale/missing features"
  "$UV" run python -c "from config import ATTRACTIVENESS_EXTRA_NAMES; from options_researcher.features import build_all; build_all('$AS_OF', symbols=ATTRACTIVENESS_EXTRA_NAMES)" \
    && note "display-extra features: rebuilt to $AS_OF" \
    || note "display-extra features: FAILED (non-blocking; extras will stay visibly stale/blocked)"
else
  note "attractiveness features: SKIPPED (no evaluation session)"
  note "display-extra features: SKIPPED (no evaluation session; non-blocking)"
fi
# ---- end data-tier island ----

# ---- full-tier region B (brief 11 §6.2) ----
if [ "$FULL_AUTHORITY_RC" -eq 0 ] && [ "$GATE_GO" -eq 1 ]; then
  if [ "$H7_EXIT_READY" -eq 1 ]; then
    # Step 3 — H7 watcher (alerts only; requires the linked gate receipt).
    "$UV" run python -m options_researcher.h7_watch --data-gate-receipt "$DG_RECEIPT" && note "h7_watch: ran" || crit "h7_watch: NONZERO EXIT"

    # Step 3a — H7 real-entry preflight (READ-ONLY; writes nothing besides its
    # own --out receipt below). The forward ledger holds only the
    # registration event, so the append path has never run on real receipts.
    # Prove the entry door would open BEFORE a name triggers, rather than
    # discovering a refusal on the one day it matters.
    #
    # --out (not a shell capture): banner-pollution guard, same class as the
    # 2026-07-23 H8 fix. This receipt is committed as durable H7 evidence
    # (Step 8 below); capturing this process's stdout into a shell variable
    # first would have put LumiBot v4.5.63's import-time banner line into
    # that committed file. The module writes its own receipt directly; its
    # normal stdout still reaches $LOG via the script-level exec redirect.
    PF_RECEIPT_DIR="reports/h7_receipts/${SCOPE_ID}/preflight"
    mkdir -p "$PF_RECEIPT_DIR"
    "$UV" run python -m options_researcher.h7_entry_preflight \
                --data-gate-receipt "$DG_RECEIPT" \
                --out "${PF_RECEIPT_DIR}/${AS_OF}.txt"
    PF_RC=$?
    if [ "$PF_RC" -eq 0 ]; then
      note "h7 entry preflight: real entry path REACHABLE"
    else
      crit "h7 entry preflight: real entry path WOULD REFUSE — H7 cannot take an entry today"
    fi
  else
    note "h7 entry path: SKIPPED — exit management did not complete cleanly"
  fi

  # Step 4 — H6 leg (exact-session; features rebuild is mandatory after topup).
  "$UV" run python -m options_researcher.h6_features --as-of "$AS_OF" && note "h6_features: rebuilt" || crit "h6_features: NONZERO EXIT"
  "$UV" run python -m options_researcher.h6_watch --as-of "$AS_OF" \
    --write-receipt "reports/h6_forward/${AS_OF}.json" && note "h6_watch: ran" || crit "h6_watch: NONZERO EXIT"

  # Step 4b — H5 LEAPS entry-trigger watch (alert-only; never auto-enters).
  # Reads the attractiveness feature store rebuilt above, which is why that
  # rebuild now runs ahead of the GATE_GO block instead of after it.
  #
  # --out (not `| tee`): banner-pollution guard, same class as the
  # 2026-07-23 H8 fix. `| tee "$EW_OUT"` would have captured LumiBot
  # v4.5.63's import-time banner line into the persisted FIRE-signal receipt
  # `grep -q "FIRE"` reads below -- and in zsh (no `setopt PIPE_FAIL`), `if
  # cmd | tee file; then` checks tee's exit status, not cmd's, so a real
  # entry_watch failure could have been silently swallowed by a
  # successful tee. The module now writes its own report file directly;
  # its normal stdout still reaches $LOG via the script-level exec
  # redirect, and $? below is entry_watch's own exit code.
  EW_OUT="reports/h5/entry_watch_${AS_OF}.txt"
  mkdir -p reports/h5
  if "$UV" run python -m options_researcher.entry_watch --as-of "$AS_OF" --out "$EW_OUT"; then
    if grep -q "FIRE" "$EW_OUT"; then
      crit "H5 ENTRY TRIGGER FIRE — read $EW_OUT and evaluate per H5 CORE rules"
    else
      note "h5 entry watch: WAIT (no trigger fired)"
    fi
  else
    crit "h5 entry watch: NONZERO EXIT"
  fi

  # Step 5 — H8 watcher, only once its tooling exists (registered lanes only).
  if "$UV" run python -c 'import options_researcher.h8_watch' 2>/dev/null; then
    mkdir -p reports/h8_forward
    "$UV" run python -m options_researcher.h8_watch --as-of "$AS_OF" --json --out \
      "reports/h8_forward/${AS_OF}.json" && note "h8_watch: ran" || crit "h8_watch: NONZERO EXIT"
  fi

  # Step 5b — H10a/b watcher + observation append (forward paper, no orders).
  # H10's --as-of is a requested RUN date and evaluates the prior completed
  # session, so pass RUN_DATE (not the already-resolved session in AS_OF).
  # Reads underlying OHLCV via the QM refresh above (data/underlying_ohlcv.py),
  # which is why that refresh now runs ahead of this block instead of after it.
  if "$UV" run python -c 'import options_researcher.h10_watch' 2>/dev/null; then
    "$UV" run python -m options_researcher.h10_watch --as-of "$RUN_DATE" && note "h10_watch: ran" || crit "h10_watch: NONZERO EXIT"
    "$UV" run python -m options_researcher.h10_observe --as-of "$RUN_DATE" && note "h10_observe: appended" || crit "h10_observe: NONZERO EXIT"
  else
    crit "h10_watch: module unavailable"
  fi
elif [ "$FULL_AUTHORITY_RC" -ne 0 ]; then
  note "H5/H6/H8/H10 lanes: PAUSED — gated behind the H7 data gate; see brief 11 §6.1"
fi
# ---- end full-tier region B ----

# Dashboards rebuild regardless of gate state — they display cached truth
# and carry their own honest data-as-of banner.
"$UV" run python -m options_researcher.dashboard && note "dashboard: rebuilt" || note "dashboard: FAILED"
"$UV" run python -m options_researcher.attractiveness_dashboard && note "attractiveness dashboard: rebuilt" || note "attractiveness dashboard: FAILED"

# Per-hypothesis capture receipt. A missing/refused leg is CRITICAL, but this
# runs fail-soft so Step 8 can still preserve every artifact that did exist.
if [ -n "$AS_OF" ]; then
  if "$UV" run python -m options_researcher.ritual_receipt \
       --as-of "$AS_OF" --run-date "$RUN_DATE"; then
    note "capture receipt: complete"
  else
    # The ONLY site that sets STARVED_CRIT (brief 11 §6.4). A refused capture
    # receipt is the expected shape of a chain-starved day; every other
    # CRITICAL is a real break and must keep the [BROKEN] label.
    STARVED_CRIT=1
    crit "capture receipt: MISSING/REFUSED — see per-hypothesis lines above"
  fi
else
  crit "capture receipt: REFUSED — evaluation session unavailable"
fi

# Publish the enclosing ritual's terminal state separately from the per-lane
# capture receipt. Downstream LLM research requires this exact-session status
# to be OK and hash-bound to the capture receipt; all-NO_SIGNAL lanes alone do
# not prove that exit management or another deterministic step succeeded.
if [ -n "$AS_OF" ]; then
  if [ "$CRITICAL" -eq 1 ]; then
    RITUAL_TERMINAL_STATUS="BROKEN"
  else
    RITUAL_TERMINAL_STATUS="OK"
  fi
  "$UV" run python -m options_researcher.ritual_status \
    --root "$REPO" --as-of "$AS_OF" --run-date "$RUN_DATE" \
    --status "$RITUAL_TERMINAL_STATUS" --log-path "$LOG" \
    && note "ritual status receipt: $RITUAL_TERMINAL_STATUS" \
    || crit "ritual status receipt: FAILED — downstream research remains blocked"
fi

# ---------------------------------------------------------------------------
# Step 8 — DURABILITY (added 2026-07-21, the day after Stage-8 activation).
# The live forward window's evidence must not exist only in this working tree:
# over a 70-session window that would put the entire verdict trail on one disk,
# unversioned. Commit the generated evidence under a NARROW allow-list (never
# code), merge+push to origin/main, then take an encrypted restic snapshot.
# The commit/backup steps stay FAIL-SOFT on the EXIT CODE -- persistence must
# not break the ritual that produces the evidence -- but a failed PUSH is now
# CRITICAL (brief 11 §9.2): it leaves this checkout AHEAD of origin/main, and
# the 15:45 Schwab capture wrapper refuses on that divergence, so the
# consequence is not deferred persistence but a lost irreplaceable capture the
# same afternoon.
#
# The allow-list is TIER-SCOPED (brief 11 §6.4): under the data tier the ritual
# produces NO H7 evidence, so H7 paths are neither staged nor described.
# ---------------------------------------------------------------------------
DATA_TIER_PATHS=(reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs)
GIT_ADD_PATHS=("${DATA_TIER_PATHS[@]}")
EVIDENCE_COMMIT_MSG="data(ritual): daily ritual data-phase artifacts ${RUN_DATE}

No H7 evidence was produced by this run: the H7 lanes are PAUSED under
data-tier authority (brief 11 §6.2), so only the ritual's own data-phase
artifacts are persisted. Written by tools/daily_ritual.sh under an
evidence-path allow-list; this commit never contains code."
if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then
  FULL_TIER_PATHS=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                   reports/h7_receipts reports/h7_data_gate reports/h5
                   reports/h6_forward reports/h8_forward reports/h10
                   reports/schwab_chains)
  GIT_ADD_PATHS=("${GIT_ADD_PATHS[@]}" "${FULL_TIER_PATHS[@]}")
  EVIDENCE_COMMIT_MSG="data(h7): daily ritual evidence ${RUN_DATE}

Autonomous persistence of the LIVE H7 forward window's daily evidence
(source-health / data-gate / watcher receipts, facts.log, forward ledger).
Written by tools/daily_ritual.sh under an evidence-path allow-list; this
commit never contains code."
fi
git add -- "${GIT_ADD_PATHS[@]}" 2>/dev/null
if git diff --cached --quiet 2>/dev/null; then
  note "evidence: nothing new to persist"
elif git commit -q -m "$EVIDENCE_COMMIT_MSG"; then
  note "evidence: committed"
else
  note "evidence: COMMIT FAILED (retries next run)"
fi

# Bounded and prompt-free, matching the capture wrapper's own discipline: an
# unattended push must fail closed quickly rather than hang. Most failures are
# a concurrent push, which fetch+merge+retry resolves.
push_evidence_once() {
  git fetch -q origin main 2>/dev/null \
    && git merge -q --no-edit origin/main 2>/dev/null \
    && GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 push -q origin main 2>/dev/null
}
if push_evidence_once; then
  note "evidence: pushed to origin/main"
elif push_evidence_once; then
  note "evidence: pushed to origin/main (bounded retry)"
else
  crit "evidence: PUSH FAILED — ops HEAD is AHEAD of origin/main; the 15:45 Schwab capture WILL REFUSE until this is realigned. Run: git -C ${REPO} push origin main"
fi

# Encrypted off-tree snapshot. Git+GitHub is the primary durable copy; this is
# belt-and-suspenders and covers the gitignored stores too. Read only the two
# RESTIC_* keys from .env rather than sourcing it (never export API secrets).
if [ -f .env ] && grep -q '^RESTIC_REPOSITORY=' .env && command -v restic >/dev/null 2>&1; then
  RESTIC_REPOSITORY="$(grep -m1 '^RESTIC_REPOSITORY=' .env | cut -d= -f2-)"
  RESTIC_PASSWORD_FILE="$(grep -m1 '^RESTIC_PASSWORD_FILE=' .env | cut -d= -f2-)"
  export RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
  if restic backup --tag "h7-daily-${RUN_DATE}" \
       ledger reports data/earnings data/chain_cache_manifest.txt >/dev/null 2>&1; then
    note "restic snapshot: taken"
  else
    note "restic snapshot: FAILED (non-blocking)"
  fi
fi

echo "=== summary ==="
printf "%b" "$SUMMARY"

# Surface completion without requiring the owner to ask. The [DATA-STARVED]
# label is a PURE COUNTER comparison (brief 11 §6.4) — no text matching on
# $SUMMARY anywhere — so the instant a second CRITICAL exists from any source,
# [BROKEN] wins regardless of what any line says.
TITLE="options-validator daily ritual"
if [ "$CRITICAL" -eq 1 ]; then
  if [ "$DATA_STARVED" -eq 1 ] && [ "$STARVED_CRIT" -eq 1 ] && [ "$CRIT_COUNT" -eq 1 ]; then
    TITLE="[DATA-STARVED] $TITLE"
  else
    TITLE="[BROKEN] $TITLE"
  fi
fi
/usr/bin/osascript -e "display notification \"$(printf '%b' "$SUMMARY" | head -c 220 | tr '"' "'")\" with title \"$TITLE\" subtitle \"session ${AS_OF} — log: .tmp/daily_ritual/${STAMP}.log\"" 2>/dev/null

if [ "$CRITICAL" -eq 1 ]; then
  echo "RITUAL STATUS: BROKEN (see CRITICAL lines above)"
  exit 1
fi
echo "RITUAL STATUS: OK"
exit 0

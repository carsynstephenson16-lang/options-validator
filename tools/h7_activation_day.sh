#!/bin/zsh
# Owner-run receipt chain only. Never invokes activation or pushes a checkout.
REPO="${0:A:h:h}"
UV="$(command -v uv)"
ALLOW_CHECKOUT=""
STAGE_ROUTINE=0
COMMIT_PARTIAL=0
refuse() { print -r -- "h7_activation_day REFUSED: $*"; exit 1; }
while [ "$#" -gt 0 ]; do
  case "$1" in
    --allow-checkout) [ "$#" -ge 2 ] || refuse 'missing checkout path'; ALLOW_CHECKOUT="${2:A}"; shift 2 ;;
    --stage-routine-evidence) STAGE_ROUTINE=1; shift ;;
    --commit-partial) COMMIT_PARTIAL=1; shift ;;
    *) refuse "unknown argument $1" ;;
  esac
done
EXPECTED_CHECKOUT="$HOME/options-validator-ops"
[ "$REPO" = "${EXPECTED_CHECKOUT:A}" ] || [ "$REPO" = "$ALLOW_CHECKOUT" ] || refuse "use --allow-checkout $REPO for an explicitly approved alternate checkout"
[ -n "$UV" ] || refuse 'uv unavailable'
cd "$REPO" || exit 2
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
EVIDENCE_ALLOW=(ledger/facts.log ledger/h7_forward ledger/h7_forward_schwab
                reports/h7_receipts reports/h7_data_gate
                reports/h7_data_gate_schwab reports/h7_forward_schwab reports/h5
                reports/h6_forward reports/h8_forward reports/h10
                reports/ritual reports/intraday_capture reports/live_probe
                reports/cache_runs reports/schwab_chains
                reports/schwab_chains_intraday)
alignment_divergence_is_evidence_only() {
  BEHIND_COUNT="$(git -C "$REPO" rev-list --count HEAD..origin/main 2>/dev/null)"
  case "$BEHIND_COUNT" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$BEHIND_COUNT" -ne 0 ] && return 1
  # TREE diff, not per-commit enumeration. `git log --name-only` has two
  # documented blind spots that both let a code change through: it emits NO
  # paths at all for a merge commit (so an "evil merge" whose conflict
  # resolution edits code shows only the evidence paths of its parents), and
  # it reports only the DESTINATION of a rename (so `git mv` of a code file
  # into an evidence path reads as evidence-only). Comparing the trees asks
  # the strictly stronger question this guard actually means: does the working
  # HEAD differ from reviewed origin/main anywhere outside the evidence
  # paths? --no-renames forces both sides of a rename to be reported.
  AHEAD_PATHS="$(git -C "$REPO" diff --name-only --no-renames origin/main HEAD 2>/dev/null)" || return 1
  while IFS= read -r CHANGED_PATH; do
    [ -z "$CHANGED_PATH" ] && continue
    PATH_OK=1
    for ALLOWED in "${EVIDENCE_ALLOW[@]}"; do
      case "$CHANGED_PATH" in
        "$ALLOWED"|"$ALLOWED"/*) PATH_OK=0; break ;;
      esac
    done
    [ "$PATH_OK" -eq 0 ] || return 1
  done <<< "$AHEAD_PATHS"
  return 0
}
BRANCH="$(git branch --show-current)" || refuse 'branch unavailable'
[ "$BRANCH" = main ] || refuse "branch is $BRANCH, not main"
GIT_TERMINAL_PROMPT=0 git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=20 fetch -q origin main || refuse 'could not refresh origin/main'
LOCAL_SHA="$(git rev-parse HEAD)" || refuse 'HEAD unavailable'
REMOTE_SHA="$(git rev-parse origin/main)" || refuse 'origin/main unavailable'
if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]; then
  alignment_divergence_is_evidence_only || refuse 'HEAD is not aligned with origin/main'
fi
ROUTINE_ALLOW=(reports/ritual reports/intraday_capture reports/live_probe reports/cache_runs
               reports/h5 reports/h10 reports/schwab_chains reports/schwab_chains_intraday ledger/facts.log)
path_allowed() {
  local candidate="$1" allowed
  shift
  for allowed in "$@"; do
    case "$candidate" in "$allowed"|"$allowed"/*) return 0 ;; esac
  done
  return 1
}
# NUL-delimited Git paths include both sides of staged/unstaged renames.
dirty_paths() {
  git diff --name-only --no-renames -z || return 1
  git diff --cached --name-only --no-renames -z || return 1
  git ls-files --others --exclude-standard -z
}
DIRTY="$(git status --porcelain)" || refuse 'could not inspect working tree'
ROUTINE_PATHS=()
if [ -n "$DIRTY" ]; then
  print -r -- "$DIRTY"
  [ "$STAGE_ROUTINE" -eq 1 ] || refuse 'working tree is dirty; remedy: --stage-routine-evidence for the permitted data-tier/evidence intersection only'
  while IFS= read -r -d '' entry; do
    path_allowed "$entry" "${ROUTINE_ALLOW[@]}" || refuse "dirty path outside routine evidence intersection: $entry"
    ROUTINE_PATHS+=("$entry")
  done < <(dirty_paths)
  typeset -U ROUTINE_PATHS
fi
# All read-only preconditions finish before even an ignored log is created.
CONTEXT="$("$UV" run python - <<'PY'
from datetime import date, datetime
from zoneinfo import ZoneInfo
from options_researcher.h7_watch import evaluation_session
from options_researcher.h7_cohort import load_registered_cohort
from options_researcher.h7_scope import scope_identity
now = datetime.now(ZoneInfo("America/New_York")).date()
cohort = load_registered_cohort()
print('RUN_DATE=' + now.isoformat())
print('SESSION=' + evaluation_session(now).isoformat())
print('SCOPE_ID=' + scope_identity()['scope_id'])
print('INCLUDED=' + ' '.join(cohort.included))
print('EXCLUDED=' + ' '.join(cohort.excluded))
PY
)" || refuse 'session or registered cohort unavailable'
RUN_DATE="$(print -r -- "$CONTEXT" | sed -n 's/^RUN_DATE=//p')"
SESSION="$(print -r -- "$CONTEXT" | sed -n 's/^SESSION=//p')"
SCOPE_ID="$(print -r -- "$CONTEXT" | sed -n 's/^SCOPE_ID=//p')"
INCLUDED_TEXT="$(print -r -- "$CONTEXT" | sed -n 's/^INCLUDED=//p')"
EXCLUDED_TEXT="$(print -r -- "$CONTEXT" | sed -n 's/^EXCLUDED=//p')"
[ -n "$SESSION" ] && [ -n "$RUN_DATE" ] && [ -n "$SCOPE_ID" ] && [ -n "$INCLUDED_TEXT" ] || refuse 'empty session/cohort context'
INCLUDED=("${(@s: :)INCLUDED_TEXT}")
MANIFEST="reports/schwab_chains/$SESSION/manifest.json"
[ -f "$MANIFEST" ] && [ -f "reports/schwab_chains/$SESSION/preclose.json" ] || refuse "NO_PACKAGE_FOR_SESSION $SESSION"
TOKEN_OUT="$("$UV" run python -m options_researcher.schwab_token_age 2>&1)" || refuse 'token-age check failed'
print -r -- "$TOKEN_OUT"
case "$TOKEN_OUT" in
  *'TOKEN EXPIRED'*) refuse 'Schwab token EXPIRED; run uv run python tools/setup_schwab.py' ;;
  *'TOKEN OK:'*|*'TOKEN EXPIRES IN '*|*'TOKEN OK') ;;
  *) refuse 'Schwab token status unavailable; check token-age output' ;;
esac
# Parse values as inert strings; never source .env or export unrelated keys.
if [ -f .env ]; then
  while IFS='=' read -r env_key env_value; do
    case "$env_key" in
      RESTIC_REPOSITORY|RESTIC_PASSWORD_FILE|RESTIC_PASSWORD_COMMAND)
        env_value="${env_value%$'\r'}"
        if [[ "$env_value" = \"*\" ]] || [[ "$env_value" = \'*\' ]]; then
          env_value="${env_value[2,-2]}"
        fi
        export "$env_key=$env_value" ;;
    esac
  done < .env
fi
[ -n "${RESTIC_REPOSITORY:-}" ] || refuse 'RESTIC_REPOSITORY is required'
[ -n "${RESTIC_PASSWORD_FILE:-}${RESTIC_PASSWORD_COMMAND:-}" ] || refuse 'RESTIC_PASSWORD_FILE or RESTIC_PASSWORD_COMMAND is required'
FEASIBILITY_STATE="$("$UV" run python - <<'PY'
import json
from pathlib import Path
from options_researcher.h7_schwab_window_registration import FEASIBILITY_SOURCE_PATHS
from research.hashing import config_hash, source_hash
paths = sorted(Path('reports/h7_forward_schwab').glob('*-feasibility-cohort9.json'))
if paths:
    value = json.loads(paths[-1].read_text())
    if value.get('source_hash') == source_hash(paths=FEASIBILITY_SOURCE_PATHS, root=Path.cwd()) and value.get('config_hash') == config_hash():
        print('REUSE=' + str(paths[-1]))
    else:
        print('REGENERATE')
else:
    print('REGENERATE')
PY
)" || refuse 'feasibility receipt unreadable'
FEASIBILITY="$(print -r -- "$FEASIBILITY_STATE" | sed -n 's/^REUSE=//p')"
REGENERATED=0
if [ -z "$FEASIBILITY" ]; then
  FEASIBILITY="reports/h7_forward_schwab/$RUN_DATE-feasibility-cohort9.json"
  REGENERATED=1
fi
# A single staging/commit implementation serves routine, explicit partial, and final evidence.
commit_evidence() {
  local message="$1" item stage_err stage_rc
  shift
  local -a selected
  selected=("$@")
  for item in "${selected[@]}"; do
    path_allowed "$item" "${EVIDENCE_ALLOW[@]}" || return 1
  done
  while IFS= read -r -d '' item; do
    path_allowed "$item" "${selected[@]}" || { print -r -- "unexpected dirty path: $item"; return 1; }
  done < <(dirty_paths)
  for item in "${selected[@]}"; do
    stage_err="$(git add -- "$item" 2>&1)"; stage_rc=$?
    if [ "$stage_rc" -ne 0 ] || [ -n "$stage_err" ]; then
      print -r -- "STAGING FAILED for $item: $stage_err"
      return 1
    fi
  done
  git diff --cached --quiet && return 0
  git commit -q -m "$message" || return 1
  [ -z "$(git status --porcelain)" ]
}
LOG_DIR=".tmp/h7_activation_day"
mkdir -p "$LOG_DIR" || exit 2
LOG="$LOG_DIR/${RUN_DATE}_$(date +%H%M).log"
exec > >(tee -a "$LOG") 2>&1
if [ "${#ROUTINE_PATHS[@]}" -gt 0 ]; then
  commit_evidence "data(ritual): activation-day prerequisite artifacts $RUN_DATE" "${ROUTINE_PATHS[@]}" || refuse 'routine evidence commit failed'
fi
CHAIN_PATHS=()
if [ "$REGENERATED" -eq 1 ]; then
  "$UV" run python tools/h7_schwab_feasibility.py --symbols "${INCLUDED[@]}" --output "$FEASIBILITY" || refuse 'feasibility regeneration failed'
  CHAIN_PATHS+=("$FEASIBILITY")
fi
SOURCE_OUT="$("$UV" run python -m options_researcher.h7_source_health --as-of "$RUN_DATE" 2>&1)"
SOURCE_RC=$?
print -r -- "$SOURCE_OUT"
print -r -- "source-health exit $SOURCE_RC ignored; included health controls continuation"
SOURCE="$(print -r -- "$SOURCE_OUT" | sed -n 's/^summary: .*receipt=\([^;]*\);.*/\1/p' | tail -1)"
EXPECTED_SOURCE="reports/h7_receipts/$SCOPE_ID/source_health/$SESSION.json"
[ "$SOURCE" = "$EXPECTED_SOURCE" ] && [ -f "$SOURCE" ] || refuse 'source-health receipt path missing or unexpected'
CHAIN_PATHS+=("$SOURCE")
HEALTH="$("$UV" run python - "$SOURCE" "$SESSION" <<'PY'
import sys
from pathlib import Path
from options_researcher.h7_cohort import load_registered_cohort
from options_researcher.h7_scope import scope_identity
from research.receipts import load_receipt
value = load_receipt(Path(sys.argv[1]), expected_type='source_health')
if value.get('scope') != scope_identity() or value.get('evaluation_session') != sys.argv[2]:
    raise ValueError('source-health scope/session mismatch')
bad = [s for s in load_registered_cohort().included if value.get('symbols', {}).get(s, {}).get('healthy') is not True]
print('BAD=' + ' '.join(bad))
PY
)" || refuse 'source-health receipt invalid'
BAD="$(print -r -- "$HEALTH" | sed -n 's/^BAD=//p')"
if [ -n "$BAD" ]; then
  print -r -- "included names unhealthy: $BAD"
  print -r -- 'refresh usage: uv run python tools/h7_refresh_earnings.py --help'
  if [ "$COMMIT_PARTIAL" -eq 1 ]; then
    commit_evidence "evidence(h7): partial activation-day receipts $SESSION" "${CHAIN_PATHS[@]}" || refuse 'partial commit failed'
  else
    print -r -- 'source receipt remains uncommitted; --commit-partial requires explicit owner choice'
  fi
  exit 1
fi
DATA_OUT="$("$UV" run python tools/h7_schwab_data_gate_receipt.py --as-of "$RUN_DATE" --source-health-receipt "$SOURCE" 2>&1)"
DATA_RC=$?
print -r -- "$DATA_OUT"
case "$DATA_RC" in
  0) ;;
  3) print -r -- 'Mode B quote-age warning (exit 3); continuing receipt chain' ;;
  1|2) exit "$DATA_RC" ;;
  *) refuse "unexpected data-gate exit $DATA_RC" ;;
esac
DATA="$(print -r -- "$DATA_OUT" | sed -n 's/^immutable receipt //p' | tail -1)"
[ "$DATA" = "reports/h7_data_gate_schwab/$SCOPE_ID/receipts/$SESSION.json" ] && [ -f "$DATA" ] || refuse 'data-gate receipt path missing or unexpected'
ARTIFACT="reports/h7_data_gate_schwab/$SCOPE_ID/$SESSION.json"
print -r -- 'Watcher omitted: owner item D-6; current watcher cannot bind Schwab evidence.'
BACKUP="reports/h7_receipts/backup/$SESSION.json"
RESTORE="reports/h7_receipts/backup_restore/$SESSION.json"
"$UV" run python tools/h7_forward_backup.py backup --completed-session "$SESSION" --receipt "$BACKUP" || refuse 'backup failed'
"$UV" run python tools/h7_forward_backup.py restore-check --backup-receipt "$BACKUP" --completed-session "$SESSION" --receipt "$RESTORE" || refuse 'restore-check failed; unchanged verifier requires whole-universe GO'
"$UV" run python - "$RESTORE" "$SESSION" <<'PY'
import sys
from pathlib import Path
from research.receipts import load_receipt
from options_researcher.h7_scope import scope_identity
value = load_receipt(Path(sys.argv[1]), expected_type='backup_restore')
if value.get('verification', {}).get('ok') is not True or value.get('completed_session') != sys.argv[2] or value.get('scope') != scope_identity():
    raise ValueError('restore receipt is unverified or stale')
PY
[ "$?" -eq 0 ] || refuse 'restore receipt verification failed'
INDEX="reports/h7_forward_schwab/$RUN_DATE-activation-day-receipts.json"
"$UV" run python - "$INDEX" "$RUN_DATE" "$SESSION" "$SOURCE" "$ARTIFACT" "$DATA" "$BACKUP" "$RESTORE" "$FEASIBILITY" <<'PY'
import hashlib, json, sys
from pathlib import Path
labels = ('source_health','data_gate_artifact','data_gate_receipt','backup','backup_restore','feasibility')
paths = sys.argv[4:]
value = {'schema':'h7-activation-day-index/v1', 'run_date':sys.argv[2], 'completed_session':sys.argv[3],
         'receipts':{label:{'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for label,p in zip(labels,paths,strict=True)}}
p = Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True)
p.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
[ "$?" -eq 0 ] || refuse 'index write failed'
CHAIN_PATHS+=("$ARTIFACT" "$DATA" "$BACKUP" "$RESTORE" "$INDEX")
commit_evidence "evidence(h7): activation-day receipts $SESSION" "${CHAIN_PATHS[@]}" || refuse 'evidence commit failed or working tree is dirty'
TEMPLATE="$LOG_DIR/$RUN_DATE-evidence.template.json"
HEAD_AFTER="$(git rev-parse HEAD)" || exit 2
"$UV" run python - "$TEMPLATE" "$HEAD_AFTER" "$MANIFEST" "$FEASIBILITY" <<'PY'
import json,sys
from pathlib import Path
from options_researcher.h7_schwab_window_registration import EVIDENCE_FIELDS
value = dict.fromkeys(EVIDENCE_FIELDS, '<OWNER TYPES>')
feasibility = json.loads(Path(sys.argv[4]).read_text())
value.update(code_commit=sys.argv[2], feasibility_receipt=feasibility,
             feasibility_receipt_hash=feasibility['receipt_hash'],
             last_historical_manifest_receipt_hash=json.loads(Path(sys.argv[3]).read_text())['manifest_hash'])
value['_source_data_fields_note'] = 'The activation CLI overwrites source/data fields from its validated receipt arguments; these template fields are not load-bearing.'
Path(sys.argv[1]).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
PY
[ "$?" -eq 0 ] || refuse 'template write failed'
SPEC='docs/superpowers/specs/2026-09-02-h7-schwab-activation-spec.md'
print -r -- "cd ${(q)REPO}"
print -r -- "PYTHONPATH=${(q)REPO} uv run python tools/h7_schwab_manual_activate.py --evidence ${(q)TEMPLATE} --source-health-receipt ${(q)SOURCE} --data-gate-receipt ${(q)DATA} --backup-restore-receipt ${(q)RESTORE} --completed-session $SESSION --activation-spec $SPEC --included-symbols $INCLUDED_TEXT \\"
OWNER_OPTIONS=(owner-typed-spec-sha256 trim-rule confirm h7-stage8-explicit-authorization
 window-start-decision-session window-decision-session-count window-end-rule-acknowledged
 window-minimum-three-calendar-months-per-lane-acknowledged schwab-capture-lane-verified-through
 schwab-capture-commitment-through schwab-confirmation-evidence session-chain-convention
 schwab-min-losses-for-verdict schwab-starvation-risk-preacceptance)
for option in "${OWNER_OPTIONS[@]}"; do
  print -r -- "  --$option '<OWNER TYPES>' \\"
done
# The exclusion keys are derived; reasons remain owner supplied, one per excluded name.
EXCLUDED=("${(@s: :)EXCLUDED_TEXT}")
for (( i=1; i<=${#EXCLUDED[@]}; i++ )); do
  suffix=' \'
  [ "$i" -eq "${#EXCLUDED[@]}" ] && suffix=''
  print -r -- "  --excluded-reason '${EXCLUDED[$i]}=<OWNER TYPES>'${suffix}"
done
print -r -- "shasum -a 256 $SPEC"
print -r -- "template code_commit: $HEAD_AFTER; compare: git rev-parse HEAD"
print -r -- 'if you commit ANYTHING before activating, recompute code_commit'
print -r -- 'EVIDENCE TEMPLATE IS INCOMPLETE — complete every <OWNER TYPES> field before use'
print -r -- "realign command: git -C ${(q)REPO} push origin main"
print -r -- "If unpushed, the next morning's ritual Step 8 attempts to push this evidence commit."
exit 0

#!/bin/zsh
# Claude Code WorktreeRemove hook: last-chance backup before a worktree disappears.
# Written to RESCUE (push) rather than rely on blocking, since blocking semantics
# for WorktreeRemove are not guaranteed. Also refuses silence about untracked
# data (the 2026-08-03 od1-v2 incident lost 110 MB that lived only in a worktree).
set +e
input=$(cat)
wt=$(printf '%s' "$input" | /usr/bin/python3 -c \
  'import json,sys;d=json.load(sys.stdin);print(d.get("worktree_path") or d.get("cwd") or "")' 2>/dev/null)
[ -d "$wt" ] || exit 0
br=$(git -C "$wt" symbolic-ref --quiet --short HEAD)
unpushed=0
if [ -n "$br" ] && git -C "$wt" rev-parse --verify -q "origin/$br" >/dev/null; then
  unpushed=$(git -C "$wt" rev-list --count "origin/$br..$br" 2>/dev/null)
elif [ -n "$br" ]; then
  unpushed=$(git -C "$wt" rev-list --count "$br" --not --remotes=origin 2>/dev/null)
fi
untracked=$(git -C "$wt" status --short --ignored=matching --untracked-files=all 2>/dev/null | wc -l | tr -d ' ')
if [ "${unpushed:-0}" != "0" ] || [ "${untracked:-0}" != "0" ]; then
  [ -n "$br" ] && ( setsid git -C "$wt" push --quiet origin "refs/heads/$br:refs/heads/$br" >/dev/null 2>&1 ) &
  echo "{\"decision\":\"block\",\"reason\":\"Worktree $wt has ${unpushed:-0} unpushed commit(s) and ${untracked:-0} untracked/ignored file(s). Backup push attempted. Verify with: git -C $wt status --short --ignored=matching --untracked-files=all — and run the irreplaceable-data guard before removal.\"}"
  exit 0
fi
exit 0

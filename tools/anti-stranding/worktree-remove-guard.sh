#!/bin/zsh
# Claude Code WorktreeRemove hook: last-chance backup before a worktree disappears.
# Written to RESCUE (push) rather than rely on blocking, since blocking semantics
# for WorktreeRemove are not guaranteed. Also refuses silence about untracked
# data (the 2026-08-03 od1-v2 incident lost 110 MB that lived only in a worktree).
set +e
input=$(cat)
wt=$(printf '%s' "$input" | /usr/bin/python3 -c \
  'import json,sys;d=json.load(sys.stdin);print(d.get("worktree_path") or d.get("cwd") or "")' 2>/dev/null \
  | grep -E '^/' | tail -1)
[ -d "$wt" ] || exit 0
br=$(git -C "$wt" symbolic-ref --quiet --short HEAD)
unpushed=0
if [ -n "$br" ] && git -C "$wt" rev-parse --verify -q "origin/$br" >/dev/null; then
  unpushed=$(git -C "$wt" rev-list --count "origin/$br..$br" 2>/dev/null)
elif [ -n "$br" ]; then
  unpushed=$(git -C "$wt" rev-list --count "$br" --not --remotes=origin 2>/dev/null)
else
  # Detached HEAD: a clean detached worktree can still hold the ONLY copy of
  # its commits. If HEAD is unreachable from every remote ref, name it so
  # removal cannot strand it.
  unpushed=$(git -C "$wt" rev-list --count HEAD --not --remotes 2>/dev/null)
  if [ "${unpushed:-0}" != "0" ]; then
    sha=$(git -C "$wt" rev-parse --short HEAD 2>/dev/null)
    git -C "$wt" branch "rescue/wt-detached-$sha" HEAD 2>/dev/null
  fi
fi
untracked=$(git -C "$wt" status --short --ignored=matching --untracked-files=all 2>/dev/null | wc -l | tr -d ' ')
if [ "${unpushed:-0}" != "0" ] || [ "${untracked:-0}" != "0" ]; then
  # Backup push runs under the same gates as the post-commit hook: owned
  # origin only (fail closed without the cached login) and a gitleaks scan
  # of the unpushed range — removal must not publish what other layers blocked.
  push_ok=1
  gh_login=$(cat "$HOME/.config/repo-reconcile/gh-login" 2>/dev/null)
  [ -n "$gh_login" ] || push_ok=0
  [ -r "$HOME/bin/anti-stranding-lib.sh" ] || push_ok=0
  if [ "$push_ok" = "1" ]; then
    source "$HOME/bin/anti-stranding-lib.sh" || push_ok=0
  fi
  if [ "$push_ok" = "1" ]; then
    anti_stranding_remote_owner_ok "$wt" "$gh_login" || push_ok=0
  fi
  if [ "$push_ok" = "1" ] && [ -n "$br" ] && command -v gitleaks >/dev/null 2>&1; then
    if git -C "$wt" rev-parse --verify -q "origin/$br" >/dev/null; then range="origin/$br..$br"
    else range="$br --not --remotes=origin"; fi
    gitleaks git --no-banner --log-opts="$range" "$wt" >/dev/null 2>&1 || push_ok=0
  fi
  # nohup, not setsid: setsid is not a standard macOS executable.
  [ "$push_ok" = "1" ] && [ -n "$br" ] && ( nohup git -C "$wt" push --quiet origin "refs/heads/$br:refs/heads/$br" </dev/null >/dev/null 2>&1 ) &
  echo "{\"decision\":\"block\",\"reason\":\"Worktree $wt has ${unpushed:-0} unpushed commit(s) and ${untracked:-0} untracked/ignored file(s). Backup push attempted; detached commits were saved to a rescue/ branch. Verify with: git -C $wt status --short --ignored=matching --untracked-files=all — and run the irreplaceable-data guard before removal.\"}"
  exit 0
fi
exit 0

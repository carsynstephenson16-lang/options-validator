#!/bin/zsh
# Claude Code SessionEnd hook: rescue uncommitted TRACKED work when a session ends.
# Commits tracked changes only (-a never stages untracked files, so a stray
# credentials file can never be auto-published to a public repo), then pushes
# in the background — the SessionEnd time budget is too small for a network
# round-trip. nohup, not setsid: setsid is not a standard macOS executable.
set +e
input=$(cat)
cwd=$(printf '%s' "$input" | /usr/bin/python3 -c \
  'import json,sys;print(json.load(sys.stdin).get("cwd",""))' 2>/dev/null \
  | grep -E '^/' | tail -1)
[ -z "$cwd" ] && cwd="$PWD"
repo=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0

case "$repo" in
  "$HOME/options-validator-ops"|"$HOME/options-validator-research") exit 0;;
esac
br=$(git -C "$repo" symbolic-ref --quiet --short HEAD)
case "$br" in ""|main|master|deploy/*) exit 0;; esac  # detached/main -> reconciler

# Working-tree AND staged-only changes both count: an interrupted session
# often leaves everything staged, which `git diff --quiet` alone misses.
if ! git -C "$repo" diff --quiet 2>/dev/null || ! git -C "$repo" diff --cached --quiet 2>/dev/null; then
  git -C "$repo" commit -a --no-verify -q \
    -m "wip(auto): session-end rescue $(date -Iseconds)" \
    -m "Auto-committed by SessionEnd hook. Tracked files only; untracked files were left alone and appear in the daily reconciler digest." 2>/dev/null
fi

# Same gates as the post-commit hook — a rescue commit must not bypass them:
# never push to an origin the owner doesn't own (fail closed without the
# cached login), and never publish a commit gitleaks would have blocked.
gh_login=$(cat "$HOME/.config/repo-reconcile/gh-login" 2>/dev/null)
[ -n "$gh_login" ] || exit 0
[ -r "$HOME/bin/anti-stranding-lib.sh" ] || exit 0
source "$HOME/bin/anti-stranding-lib.sh" || exit 0
anti_stranding_remote_owner_ok "$repo" "$gh_login" || exit 0
if command -v gitleaks >/dev/null 2>&1; then
  if git -C "$repo" rev-parse --verify -q "origin/$br" >/dev/null; then range="origin/$br..$br"
  else range="$br --not --remotes=origin"; fi
  gitleaks git --no-banner --log-opts="$range" "$repo" >/dev/null 2>&1 || exit 0
fi

( nohup git -C "$repo" push --quiet origin "refs/heads/$br:refs/heads/$br" </dev/null >/dev/null 2>&1 ) &
exit 0

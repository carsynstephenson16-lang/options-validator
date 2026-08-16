#!/bin/zsh
# Claude Code SessionEnd hook: rescue uncommitted TRACKED work when a session ends.
# Commits tracked changes only (-a never stages untracked files, so a stray
# credentials file can never be auto-published to a public repo), then pushes
# detached — the SessionEnd time budget is too small for a network round-trip.
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

if ! git -C "$repo" diff --quiet 2>/dev/null; then
  git -C "$repo" commit -a --no-verify -q \
    -m "wip(auto): session-end rescue $(date -Iseconds)" \
    -m "Auto-committed by SessionEnd hook. Tracked files only; untracked files were left alone and appear in the daily reconciler digest." 2>/dev/null
fi

( setsid git -C "$repo" push --quiet origin "refs/heads/$br:refs/heads/$br" >/dev/null 2>&1 ) &
exit 0

#!/bin/zsh
# One-command install of the anti-stranding system (owner-run, reversible).
# Layers: L1 global git post-commit auto-push  ·  L3 daily reconciler (08:15)
# Claude SessionEnd/WorktreeRemove hooks (L2) are a separate manual paste —
# see README.md — so a bad hook can never lock out sessions silently.
set -e
here=${0:a:h}

echo "== L1: global git auto-push hook =="
mkdir -p "$HOME/.githooks" "$HOME/.local/log" "$HOME/bin"
cp "$here/post-commit" "$HOME/.githooks/post-commit"
chmod +x "$HOME/.githooks/post-commit"
git config --global core.hooksPath "$HOME/.githooks"
echo "   installed (opt a repo out: git -C <repo> config core.hooksPath .git/hooks)"

echo "== secret scanner (required: repos are public) =="
command -v gitleaks >/dev/null 2>&1 || brew install gitleaks

echo "== cache GitHub login (ownership gate for the global auto-push hook) =="
mkdir -p "$HOME/.config/repo-reconcile"
# Capture first, write only on success: a transient gh failure must neither
# truncate a previously valid cache nor kill the installer via set -e.
gh_login=$(gh api user -q .login 2>/dev/null) || gh_login=""
if [ -n "$gh_login" ]; then
  echo "$gh_login" > "$HOME/.config/repo-reconcile/gh-login"
  echo "   login cached: $gh_login"
elif [ -s "$HOME/.config/repo-reconcile/gh-login" ]; then
  echo "   gh lookup failed — keeping existing cached login: $(cat "$HOME/.config/repo-reconcile/gh-login")"
else
  echo "   WARNING: could not resolve gh login — auto-push stays disabled (fail closed) until this file exists"
fi

echo "== L2 helper scripts (hooks registered manually per README) =="
cp "$here/claude-session-rescue.sh" "$here/worktree-remove-guard.sh" "$HOME/bin/"
chmod +x "$HOME/bin/claude-session-rescue.sh" "$HOME/bin/worktree-remove-guard.sh"

echo "== L3: daily reconciler =="
cp "$here/repo-reconcile" "$HOME/bin/repo-reconcile"
chmod +x "$HOME/bin/repo-reconcile"
cp "$here/com.carsyn.repo-reconcile.plist" "$HOME/Library/LaunchAgents/"
# Conditional so set -e survives the routine already-loaded case; the
# launchctl print check below is the real verdict either way.
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.carsyn.repo-reconcile.plist" 2>/dev/null || true
# Verify the service is actually loaded: bootstrap fails for many reasons
# besides "already loaded" (bad plist, wrong domain, permissions), and a
# swallowed failure would silently leave the daily safety-net layer absent.
if launchctl print "gui/$(id -u)/com.carsyn.repo-reconcile" >/dev/null 2>&1; then
  echo "   reconciler loaded (test now: launchctl kickstart gui/$(id -u)/com.carsyn.repo-reconcile)"
else
  echo "   ERROR: reconciler LaunchAgent is NOT loaded — daily layer absent. Run manually:"
  echo "   launchctl bootstrap gui/$(id -u) $HOME/Library/LaunchAgents/com.carsyn.repo-reconcile.plist"
  exit 1
fi

echo "== merge policy (owner directive 2026-08-15: automatic merges) =="
mkdir -p "$HOME/.config/repo-reconcile"
if [ -f "$HOME/.config/repo-reconcile/automerge" ]; then
  echo "   auto-merge flag already '$(cat "$HOME/.config/repo-reconcile/automerge")' — left unchanged (a reinstall never reverses an opt-out)."
else
  echo 1 > "$HOME/.config/repo-reconcile/automerge"
  echo "   auto-merge ENABLED: your own green-check PRs merge daily (echo 0 > ~/.config/repo-reconcile/automerge to revert)"
fi

echo ""
echo "Done. First run is worth doing by hand in dry-run mode:"
echo "  DRY_RUN=1 ~/bin/repo-reconcile && open ~/Desktop/repo-digest.md"

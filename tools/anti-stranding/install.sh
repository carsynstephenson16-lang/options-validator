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

echo "== L2 helper scripts (hooks registered manually per README) =="
cp "$here/claude-session-rescue.sh" "$here/worktree-remove-guard.sh" "$HOME/bin/"
chmod +x "$HOME/bin/claude-session-rescue.sh" "$HOME/bin/worktree-remove-guard.sh"

echo "== L3: daily reconciler =="
cp "$here/repo-reconcile" "$HOME/bin/repo-reconcile"
chmod +x "$HOME/bin/repo-reconcile"
cp "$here/com.carsyn.repo-reconcile.plist" "$HOME/Library/LaunchAgents/"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.carsyn.repo-reconcile.plist" 2>/dev/null \
  || echo "   (already loaded — run: launchctl kickstart gui/$(id -u)/com.carsyn.repo-reconcile to test)"

echo ""
echo "Done. First run is worth doing by hand in dry-run mode:"
echo "  DRY_RUN=1 ~/bin/repo-reconcile && open ~/Desktop/repo-digest.md"

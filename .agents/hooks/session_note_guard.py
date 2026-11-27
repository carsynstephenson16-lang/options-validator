#!/usr/bin/env python3
"""Stop hook: ensure a daily Obsidian session note exists on working days.

The vault IS this repo, and daily notes live at the MAIN checkout root as
`<repo>/YYYY-MM-DD.md` (gitignored). Notes are produced by the manual
`session-synthesis` skill, so any day nobody says "wrap up" produces no note.
This hook closes that gap: if there was meaningful work in this checkout today
(commits since midnight and/or uncommitted changes) but today's note does not
exist yet, it BLOCKS the stop and tells the model to run session-synthesis.

Worktree anchoring (2026-08-14): the note path anchors on the MAIN checkout
via `git rev-parse --git-common-dir`, never on a linked worktree's root — a
gitignored note written inside a worktree is silently destroyed when the
worktree is removed (the defect the 2026-08-14 skills audit found). Work
detection still runs in the session's own checkout.

Silent (lets the stop proceed) when:
  - today's note already exists (self-terminates once written),
  - there was no work today (no commits, clean tree) -> trivial Q&A days,
  - it already blocked once this stop-cycle (stop_hook_active) -> loop safety.
"""
import datetime
import json
import os
import subprocess
import sys


def _allow():
    # No stdout + exit 0 => the stop proceeds normally.
    sys.exit(0)


def _git(project, *args):
    try:
        return subprocess.run(
            ["git", "-C", project, *args],
            capture_output=True,
            text=True,
            timeout=8,
        ).stdout.strip()
    except Exception:
        return ""


def _main_checkout(project):
    """Resolve the MAIN checkout root for a (possibly linked-worktree) path.

    `--git-common-dir` is the shared .git of the main checkout; its parent is
    the main root. In the main checkout it returns `.git` (relative), which
    resolves back to `project` — behavior there is unchanged. Any failure
    falls back to `project` so this can never make the hook stricter than
    the old behavior, only better-anchored.
    """
    common = _git(project, "rev-parse", "--git-common-dir")
    if not common:
        return project
    if not os.path.isabs(common):
        common = os.path.join(project, common)
    root = os.path.dirname(os.path.normpath(common))
    return root if os.path.isdir(root) else project


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    # Loop safety: if we already blocked once this stop-cycle, let it stop.
    if data.get("stop_hook_active"):
        _allow()

    project = os.environ.get("CLAUDE_PROJECT_DIR") or _git(
        os.getcwd(), "rev-parse", "--show-toplevel"
    )
    if not project or not os.path.isdir(project):
        _allow()

    root = _main_checkout(project)

    today = datetime.date.today().isoformat()
    note = os.path.join(root, f"{today}.md")
    if os.path.exists(note):
        _allow()

    commits = _git(project, "log", "--since=midnight", "--oneline")
    dirty = _git(project, "status", "--porcelain")
    if not commits and not dirty:
        _allow()

    reason = (
        f"No Obsidian session note exists for today ({today}), but there was "
        f"meaningful work in this repo today. Before ending: invoke the "
        f"session-synthesis skill and write the daily note to {note} following "
        f"that skill's format (<=250 words; decisions+reasons; rejected ideas; "
        f"open worries; next-session-start). Write it at that MAIN-checkout "
        f"path even from a worktree session — a note left inside a worktree "
        f"is destroyed with the worktree. If today truly had no substantive "
        f"work worth a note, instead write {note} containing the single line "
        f"'(no substantive work)' so this reminder stops for today."
    )
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()

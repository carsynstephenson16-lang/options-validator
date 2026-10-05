"""Tests for the session_note_guard Stop hook.

The hook (.agents/hooks/session_note_guard.py) blocks a session stop ONCE when
the checkout saw work today (commits since midnight or a dirty tree) and no
`<main-checkout>/YYYY-MM-DD.md` note exists. It anchors the note path on the
MAIN checkout via `git rev-parse --git-common-dir` even when the session runs
in a linked worktree (2026-08-14 fix), and it is silent when the note exists,
when there was no work, or when it already blocked this stop-cycle.

Contract: stdout JSON `{"decision": "block", "reason": ...}` + exit 0 to block;
no stdout + exit 0 to allow. Specified by the 2026-08-11 core-plugin design;
the hook body was laptop-only until 2026-09-15.
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".agents" / "hooks" / "session_note_guard.py"

_GIT_CONTEXT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


class SessionNoteGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="note-guard-"))
        self.addCleanup(shutil.rmtree, root, True)
        home = root / "home"
        home.mkdir()
        self.env = {k: v for k, v in os.environ.items() if k not in _GIT_CONTEXT_VARS}
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "HOME": str(home),
            }
        )
        self.repo = root / "main"
        self.repo.mkdir()
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Note guard test")
        self._git("config", "user.email", "note-guard-test@example.invalid")
        self._git("config", "core.hooksPath", "")
        (self.repo / "code.py").write_text("x = 1\n", encoding="utf-8")
        self._git("add", "--", "code.py")
        # Baseline commit dated two days ago so a clean tree reads as "no work".
        old = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()
        self._git(
            "commit",
            "-q",
            "-m",
            "baseline",
            env_extra={"GIT_AUTHOR_DATE": old, "GIT_COMMITTER_DATE": old},
        )
        self.today = datetime.date.today().isoformat()

    def _git(self, *args: str, env_extra: dict | None = None) -> str:
        env = dict(self.env)
        if env_extra:
            env.update(env_extra)
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _run(self, project: Path, payload: dict | None = None) -> subprocess.CompletedProcess:
        env = dict(self.env)
        env["CLAUDE_PROJECT_DIR"] = str(project)
        return subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload or {}),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=project,
        )

    def test_hook_script_exists(self):
        self.assertTrue(HOOK.exists(), f"stop hook missing at {HOOK}")

    def test_no_work_today_is_silent(self):
        proc = self._run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_dirty_tree_without_note_blocks_with_the_note_path(self):
        (self.repo / "code.py").write_text("x = 2\n", encoding="utf-8")
        proc = self._run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn(str(self.repo / f"{self.today}.md"), payload["reason"])
        self.assertIn("session-synthesis", payload["reason"])

    def test_commit_today_without_note_blocks(self):
        (self.repo / "code.py").write_text("x = 3\n", encoding="utf-8")
        self._git("add", "--", "code.py")
        self._git("commit", "-q", "-m", "today")
        proc = self._run(self.repo)
        self.assertEqual(json.loads(proc.stdout)["decision"], "block")

    def test_existing_note_allows(self):
        (self.repo / "code.py").write_text("x = 2\n", encoding="utf-8")
        (self.repo / f"{self.today}.md").write_text("# note\n", encoding="utf-8")
        proc = self._run(self.repo)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_second_block_in_one_stop_cycle_is_suppressed(self):
        (self.repo / "code.py").write_text("x = 2\n", encoding="utf-8")
        proc = self._run(self.repo, {"stop_hook_active": True})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_linked_worktree_anchors_the_note_on_the_main_checkout(self):
        worktree = self.repo.parent / "linked"
        self._git("worktree", "add", "-q", str(worktree), "-b", "feature")
        (worktree / "code.py").write_text("x = 9\n", encoding="utf-8")
        proc = self._run(worktree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["decision"], "block")
        self.assertIn(str(self.repo / f"{self.today}.md"), payload["reason"])
        self.assertNotIn(str(worktree / f"{self.today}.md"), payload["reason"])

    def test_note_in_main_checkout_silences_a_worktree_session(self):
        worktree = self.repo.parent / "linked2"
        self._git("worktree", "add", "-q", str(worktree), "-b", "feature2")
        (worktree / "code.py").write_text("x = 9\n", encoding="utf-8")
        (self.repo / f"{self.today}.md").write_text("# note\n", encoding="utf-8")
        proc = self._run(worktree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")

    def test_garbage_stdin_does_not_wedge_the_stop(self):
        env = dict(self.env)
        env["CLAUDE_PROJECT_DIR"] = str(self.repo)
        proc = subprocess.run(
            [sys.executable, str(HOOK)],
            input="not json{{{",
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=self.repo,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()

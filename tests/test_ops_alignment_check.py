"""Offline structural + behavioural tests for the D-6a ops alignment check.

Owner ruling 4, `reports/2026-08-14-owner-answers-decision-menu.md`: a
scheduled 15:30 ET check that DETECTS a divergent ops checkout before the
15:45 preclose capture refuses on it. The load-bearing invariant is that the
check only ever looks: it must never merge, pull, reset or push.
"""

from __future__ import annotations

import plistlib
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "ops_alignment_check.sh"
PLIST = (
    ROOT
    / "tools"
    / "launchagents"
    / "com.carsyn.options-validator.alignment-check.plist"
)
MUTATING_VERBS = ("merge", "pull", "reset", "push")
GIT_ENV = {
    "PATH": "/usr/bin:/bin:/usr/local/bin",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


class OpsAlignmentCheckTests(unittest.TestCase):
    # --- detection-only invariant -----------------------------------------
    def test_script_never_executes_a_mutating_git_verb(self):
        source = SCRIPT.read_text(encoding="utf-8")
        offenders = []
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if not any(verb in stripped for verb in MUTATING_VERBS):
                continue
            # The ONLY permitted home for a mutating verb is a HINT_* string:
            # text the operator is shown and runs themselves.
            if not stripped.startswith("HINT_"):
                offenders.append(line)
        self.assertEqual(offenders, [], f"mutating git verb outside a HINT_ string: {offenders}")

    def test_hint_strings_can_never_be_executed(self):
        source = SCRIPT.read_text(encoding="utf-8")
        # No eval/exec/sh -c: a hint is data, and there is no path that turns
        # it back into a command.
        self.assertNotIn("eval", source)
        self.assertNotIn("exec ", source)
        for line in source.splitlines():
            if "$HINT" not in line and "${HINT" not in line:
                continue
            stripped = line.strip()
            self.assertTrue(
                stripped.startswith(("HINT=", "MSG=", "echo", "/usr/bin/osascript")),
                f"$HINT used outside assignment/echo/notification: {line!r}",
            )

    def test_only_read_only_git_subcommands_are_invoked(self):
        # Line continuations collapsed first, so the multi-line bounded fetch
        # reads as one invocation and `-c key=value` options are skipped.
        flat = re.sub(
            r"\s+", " ", SCRIPT.read_text(encoding="utf-8").replace("\\\n", " "))
        invoked = set(re.findall(r'git -C "\$REPO" (?:-c \S+ )*([a-z][a-z-]*)', flat))
        self.assertTrue(invoked, "expected the script to invoke git at all")
        self.assertTrue(
            invoked <= {"branch", "rev-parse", "rev-list", "fetch"},
            f"unexpected git subcommand(s): {sorted(invoked)}",
        )

    def test_fetch_is_bounded_and_prompt_free(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GIT_TERMINAL_PROMPT=0", source)
        self.assertIn("http.lowSpeedLimit=1000", source)
        self.assertIn("http.lowSpeedTime=20", source)
        self.assertIn("fetch -q origin main", source)

    def test_notification_is_guarded_like_the_sibling_wrappers(self):
        source = SCRIPT.read_text(encoding="utf-8")
        osascript_lines = [
            line for line in source.splitlines() if "osascript -e" in line
        ]
        self.assertTrue(osascript_lines, "expected an osascript notification line")
        for line in osascript_lines:
            self.assertIn("display notification", line)
            self.assertTrue(
                line.rstrip().endswith("2>/dev/null"),
                f"osascript line not guarded like the sibling: {line!r}",
            )

    # --- plist -------------------------------------------------------------
    def test_plist_runs_weekdays_at_1530_et_from_the_ops_checkout(self):
        payload = plistlib.loads(PLIST.read_bytes())
        self.assertEqual(
            payload["Label"], "com.carsyn.options-validator.alignment-check"
        )
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator-ops/tools/ops_alignment_check.sh",
            ],
        )
        self.assertEqual(
            payload["WorkingDirectory"],
            "/Users/carsynstephenson/options-validator-ops",
        )
        self.assertEqual(payload["EnvironmentVariables"]["TZ"], "America/New_York")
        self.assertEqual(
            payload["StartCalendarInterval"],
            [
                {"Weekday": weekday, "Hour": 15, "Minute": 30}
                for weekday in range(1, 6)
            ],
        )
        self.assertFalse(payload["RunAtLoad"])
        self.assertNotIn("KeepAlive", payload)

    def test_plist_runs_15_minutes_before_the_preclose_capture(self):
        preclose = plistlib.loads(
            (
                ROOT
                / "tools"
                / "launchagents"
                / "com.carsyn.options-validator.schwab-chain-preclose.plist"
            ).read_bytes()
        )
        payload = plistlib.loads(PLIST.read_bytes())
        check = payload["StartCalendarInterval"][0]
        capture = preclose["StartCalendarInterval"][0]
        self.assertEqual(
            check["Hour"] * 60 + check["Minute"] + 15,
            capture["Hour"] * 60 + capture["Minute"],
        )

    def test_readme_documents_the_owner_run_bootstrap_command(self):
        readme = (ROOT / "tools" / "launchagents" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("com.carsyn.options-validator.alignment-check.plist", readme)
        self.assertIn(
            "launchctl bootstrap gui/$UID "
            "~/Library/LaunchAgents/com.carsyn.options-validator.alignment-check.plist",
            readme.replace("\\\n   ", ""),
        )

    # --- behaviour ---------------------------------------------------------
    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env={**GIT_ENV, "HOME": str(repo)},
        )

    def _repo(self, *, ahead: int = 0, behind: int = 0, branch: str = "main") -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / "checkout"
        repo.mkdir()
        self._git(repo, "init", "-q", "-b", "main")
        (repo / "code.py").write_text("x = 1\n")
        self._git(repo, "add", "code.py")
        self._git(repo, "commit", "-qm", "base")
        # Build the REMOTE side first, pin origin/main to it by hand (so the
        # test never touches a network), rewind, then build the LOCAL side:
        # ahead / behind / diverged all fall out of the same three steps.
        for index in range(behind):
            (repo / f"remote{index}.py").write_text(f"y = {index}\n")
            self._git(repo, "add", f"remote{index}.py")
            self._git(repo, "commit", "-qm", f"remote {index}")
        self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        if behind:
            self._git(repo, "rev-parse", "HEAD")
            self._git(repo, "checkout", "-q", "--detach")
            self._git(repo, "checkout", "-q", "-B", "main", f"HEAD~{behind}")
        for index in range(ahead):
            (repo / f"local{index}.py").write_text(f"z = {index}\n")
            self._git(repo, "add", f"local{index}.py")
            self._git(repo, "commit", "-qm", f"local {index}")
        if branch != "main":
            self._git(repo, "checkout", "-q", "-b", branch)
        return repo

    def _run(self, repo: Path, *, fetch_rc: int = 0) -> subprocess.CompletedProcess:
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        source = SCRIPT.read_text(encoding="utf-8")
        block = source[source.index("# --- classification"):]
        logdir = repo / ".tmp/alignment_check"
        logdir.mkdir(parents=True, exist_ok=True)
        preamble = [
            "REPO=" + shlex.quote(str(repo)),
            "LOGDIR=" + shlex.quote(str(logdir)),
            'LOG="$LOGDIR/test.log"',
            "NOW=2026-08-14T15:30:00-0400",
            f"FETCH_RC={fetch_rc}",
            'BRANCH="$(git -C "$REPO" branch --show-current 2>/dev/null)"',
            'LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD 2>/dev/null)"',
            'REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main 2>/dev/null)"',
        ]
        return subprocess.run(
            [zsh, "-c", "\n".join([*preamble, block])],
            capture_output=True,
            text=True,
            timeout=60,
            env={**GIT_ENV, "HOME": str(repo)},
        )

    def test_aligned_checkout_exits_zero_and_notifies_nobody(self):
        repo = self._repo()
        completed = self._run(repo)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("status=ALIGNED", completed.stdout)
        self.assertNotIn("ACTION NEEDED", completed.stdout)
        log = (repo / ".tmp/alignment_check/test.log").read_text()
        self.assertIn("status=ALIGNED", log)

    def test_every_divergence_shape_exits_nonzero_with_the_realign_command(self):
        cases = {
            "AHEAD": (self._repo(ahead=1), "push origin main"),
            "BEHIND": (self._repo(behind=1), "merge --ff-only origin/main"),
            "DIVERGED": (self._repo(ahead=1, behind=1), "log --oneline"),
        }
        for status, (repo, expected_hint) in cases.items():
            with self.subTest(status=status):
                completed = self._run(repo)

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn(f"status={status}", completed.stdout)
                self.assertIn("ACTION NEEDED", completed.stdout)
                self.assertIn(expected_hint, completed.stdout)
                self.assertIn("DETECTION ONLY", completed.stdout)
                log = (repo / ".tmp/alignment_check/test.log").read_text()
                self.assertIn(f"status={status}", log)

    def test_failed_fetch_and_wrong_branch_fail_closed(self):
        for label, repo, fetch_rc, status in (
            ("fetch failed", self._repo(), 1, "FETCH_FAILED"),
            ("not on main", self._repo(branch="side"), 0, "NOT_ON_MAIN"),
        ):
            with self.subTest(case=label):
                completed = self._run(repo, fetch_rc=fetch_rc)

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn(f"status={status}", completed.stdout)
                self.assertIn("ACTION NEEDED", completed.stdout)

    def test_check_leaves_the_repository_untouched(self):
        repo = self._repo(ahead=2)
        before = subprocess.run(
            ["git", "-C", str(repo), "log", "--format=%H", "--all"],
            capture_output=True, text=True, check=True, env={**GIT_ENV, "HOME": str(repo)},
        ).stdout
        status_before = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, check=True, env={**GIT_ENV, "HOME": str(repo)},
        ).stdout

        self._run(repo)

        after = subprocess.run(
            ["git", "-C", str(repo), "log", "--format=%H", "--all"],
            capture_output=True, text=True, check=True, env={**GIT_ENV, "HOME": str(repo)},
        ).stdout
        status_after = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True, text=True, check=True, env={**GIT_ENV, "HOME": str(repo)},
        ).stdout
        self.assertEqual(before, after)
        # Only the check's own gitignored .tmp log may appear.
        self.assertEqual(
            [line for line in status_after.splitlines() if ".tmp/" not in line],
            [line for line in status_before.splitlines() if ".tmp/" not in line],
        )


if __name__ == "__main__":
    unittest.main()

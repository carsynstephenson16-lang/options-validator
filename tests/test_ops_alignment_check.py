"""Offline structural + behavioural tests for the D-6a ops alignment check.

Owner ruling 4, `reports/2026-08-14-owner-answers-decision-menu.md`: a
scheduled 15:30 ET check that DETECTS a divergent ops checkout before the
15:45 preclose capture refuses on it. The load-bearing invariant is that the
check only ever looks: it must never merge, pull, reset or push.
"""

from __future__ import annotations

import plistlib
import re
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

    @staticmethod
    def _executed_git_invocations() -> list[tuple[str, list[str]]]:
        """Every git command the script actually runs, as (subcommand, args).

        Line continuations are joined first; comments and the HINT_* strings
        (operator-facing text, never executed) are excluded. Matches a bare
        `git ...` too, not only `git -C "$REPO" ...`.
        """
        source = SCRIPT.read_text(encoding="utf-8").replace("\\\n", " ")
        invocations = []
        for line in source.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "HINT_")):
                continue
            for match in re.finditer(
                r"\bgit\s+((?:-[Cc]\s+\S+\s+)*)([a-z][a-z-]*)([^;|)\n]*)", stripped
            ):
                invocations.append((match.group(2), match.group(3).split()))
        return invocations

    def test_only_read_only_git_subcommands_and_flags_are_invoked(self):
        # A subcommand allow-list alone is evadable: `git branch -f rescue
        # origin/main` and `git fetch origin main:main` both mutate refs while
        # naming a "read-only" subcommand. So the flags are checked too.
        invocations = self._executed_git_invocations()
        self.assertTrue(invocations, "expected the script to invoke git at all")
        forbidden_flags = {"-f", "--force", "-D", "-d", "-m", "-M", "--delete",
                           "--move", "--copy", "-C", "--update-head-ok"}
        for subcommand, args in invocations:
            with self.subTest(subcommand=subcommand, args=args):
                self.assertIn(
                    subcommand,
                    {"branch", "rev-parse", "rev-list", "fetch", "diff"},
                    f"unexpected git subcommand: {subcommand}",
                )
                self.assertEqual(
                    [flag for flag in args if flag in forbidden_flags], [],
                    f"ref-writing flag on `git {subcommand}`: {args}",
                )
                if subcommand == "fetch":
                    # A refspec (`src:dst`) makes fetch write local refs.
                    self.assertEqual(
                        [arg for arg in args
                         if ":" in arg and not arg.startswith("2>")], [],
                        f"`git fetch` carries a refspec: {args}",
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

    def _repo(self, *, ahead_paths: tuple[str, ...] = (), behind: int = 0,
              branch: str = "main", break_remote: bool = False) -> Path:
        """Fixture with a REAL local `origin` (a bare repo in tmp).

        The script's own fetch preamble therefore executes under test — an
        earlier version of these tests injected FETCH_RC by hand and never ran
        the fetch at all.
        """
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        origin = tmp / "origin.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
            check=True, capture_output=True, env={**GIT_ENV, "HOME": str(tmp)},
        )
        repo = tmp / "checkout"
        repo.mkdir()
        self._git(repo, "init", "-q", "-b", "main")
        (repo / "code.py").write_text("x = 1\n")
        self._git(repo, "add", "code.py")
        self._git(repo, "commit", "-qm", "base")
        self._git(repo, "remote", "add", "origin", str(origin))
        self._git(repo, "push", "-q", "origin", "main")
        for index in range(behind):
            (repo / f"remote{index}.py").write_text(f"y = {index}\n")
            self._git(repo, "add", f"remote{index}.py")
            self._git(repo, "commit", "-qm", f"remote {index}")
        if behind:
            self._git(repo, "push", "-q", "origin", "main")
            self._git(repo, "reset", "-q", "--hard", f"HEAD~{behind}")
        for index, relative in enumerate(ahead_paths):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"payload {index}\n")
            self._git(repo, "add", "--", relative)
            self._git(repo, "commit", "-qm", f"ahead {relative}")
        if branch != "main":
            self._git(repo, "checkout", "-q", "-b", branch)
        if break_remote:
            self._git(repo, "remote", "set-url", "origin", str(tmp / "gone.git"))
        return repo

    def _run(self, repo: Path) -> subprocess.CompletedProcess:
        """Run the REAL script, from a copy inside the fixture checkout."""
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        installed = repo / "tools" / SCRIPT.name
        installed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCRIPT, installed)
        return subprocess.run(
            [zsh, str(installed)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**GIT_ENV, "HOME": str(repo)},
        )

    @staticmethod
    def _log_text(repo: Path) -> str:
        logs = sorted((repo / ".tmp/alignment_check").glob("*.log"))
        return "\n".join(path.read_text() for path in logs)

    def test_aligned_checkout_exits_zero_and_notifies_nobody(self):
        repo = self._repo()
        completed = self._run(repo)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("status=ALIGNED", completed.stdout)
        self.assertNotIn("ACTION NEEDED", completed.stdout)
        self.assertIn("status=ALIGNED", self._log_text(repo))

    def test_evidence_only_commits_ahead_are_informational_not_an_alarm(self):
        # Owner decision D-3: the 15:45 capture RUNS in this shape, so crying
        # wolf here would train the operator to ignore the 15:30 alarm.
        repo = self._repo(
            ahead_paths=("reports/ritual/run_status.json", "ledger/facts.log"))
        completed = self._run(repo)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("status=AHEAD_EVIDENCE_ONLY", completed.stdout)
        self.assertIn("15:45 capture will still run", completed.stdout)
        self.assertIn("INFO:", completed.stdout)
        self.assertNotIn("ACTION NEEDED", completed.stdout)
        self.assertIn("push origin main", completed.stdout)
        self.assertIn("status=AHEAD_EVIDENCE_ONLY", self._log_text(repo))

    def test_code_ahead_is_an_alarm_because_the_capture_will_refuse(self):
        for label, ahead_paths in (
            ("code only", ("options_researcher/h7_watch.py",)),
            ("mixed with evidence",
             ("reports/ritual/run_status.json", "tools/daily_ritual.sh")),
        ):
            with self.subTest(case=label):
                repo = self._repo(ahead_paths=ahead_paths)
                completed = self._run(repo)

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn("status=AHEAD_CODE", completed.stdout)
                self.assertIn("WILL REFUSE", completed.stdout)
                self.assertIn("ACTION NEEDED", completed.stdout)
                self.assertIn("push origin main", completed.stdout)

    def test_evidence_allow_list_matches_the_capture_gate_it_predicts(self):
        # If the two lists drift, this check lies about what happens at 15:45.
        def allow_list(text: str) -> list[str]:
            start = text.index("EVIDENCE_ALLOW=(")
            return text[start + len("EVIDENCE_ALLOW=("):text.index(")", start)].split()

        self.assertEqual(
            allow_list(SCRIPT.read_text(encoding="utf-8")),
            allow_list(
                (ROOT / "tools" / "schwab_chain_capture.sh").read_text(encoding="utf-8")),
        )

    def test_every_refusing_divergence_shape_exits_nonzero_with_the_command(self):
        cases = {
            "BEHIND": (self._repo(behind=1), "merge --ff-only origin/main"),
            "DIVERGED": (
                self._repo(behind=1, ahead_paths=("ledger/facts.log",)),
                "log --oneline",
            ),
        }
        for status, (repo, expected_hint) in cases.items():
            with self.subTest(status=status):
                completed = self._run(repo)

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn(f"status={status}", completed.stdout)
                self.assertIn("ACTION NEEDED", completed.stdout)
                self.assertIn(expected_hint, completed.stdout)
                self.assertIn("DETECTION ONLY", completed.stdout)
                self.assertIn(f"status={status}", self._log_text(repo))

    def test_failed_fetch_and_wrong_branch_fail_closed(self):
        for label, repo, status in (
            ("fetch failed", self._repo(break_remote=True), "FETCH_FAILED"),
            ("not on main", self._repo(branch="side"), "NOT_ON_MAIN"),
        ):
            with self.subTest(case=label):
                completed = self._run(repo)

                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn(f"status={status}", completed.stdout)
                self.assertIn("ACTION NEEDED", completed.stdout)

    def _ref_state(self, repo: Path) -> tuple[str, str, str]:
        """Refs, reflogs and worktree state — what a ref-writing git call moves."""
        def run(*args: str) -> str:
            return subprocess.run(
                ["git", "-C", str(repo), *args], capture_output=True, text=True,
                check=True, env={**GIT_ENV, "HOME": str(repo)},
            ).stdout

        reflogs = "\n".join(
            f"{path.relative_to(repo)}::{path.read_text(errors='replace')}"
            for path in sorted((repo / ".git/logs").rglob("*")) if path.is_file()
        )
        worktree = "\n".join(
            line for line in run("status", "--porcelain").splitlines()
            if ".tmp/" not in line and "tools/" not in line
        )
        return run("for-each-ref", "--format=%(refname) %(objectname)"), reflogs, worktree

    def test_check_leaves_every_ref_and_reflog_untouched(self):
        # `git log --all` alone is too weak: `git branch -f rescue origin/main`
        # creates a ref pointing at an existing commit, so the commit graph is
        # unchanged. Refs and reflogs are what actually move. The fixture is
        # ahead-only, so the script's own (legitimate) fetch has nothing to
        # update and even refs/remotes/origin/main must be byte-identical.
        repo = self._repo(ahead_paths=("options_researcher/h7_watch.py",))
        before = self._ref_state(repo)

        self._run(repo)

        self.assertEqual(self._ref_state(repo), before)


if __name__ == "__main__":
    unittest.main()

"""Offline structural tests for the independent Schwab preclose job."""

from __future__ import annotations

import plistlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "schwab_chain_capture.sh"
PLIST = (
    ROOT
    / "tools"
    / "launchagents"
    / "com.carsyn.options-validator.schwab-chain-preclose.plist"
)


class SchwabChainScheduleTests(unittest.TestCase):
    def test_wrapper_is_separate_and_fail_closed(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn('BRANCH="$(git -C "$REPO" branch --show-current', source)
        self.assertIn('LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD', source)
        self.assertIn('REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main', source)
        self.assertIn('if [ "$BRANCH" != "main" ]', source)
        self.assertIn('if [ "$LOCAL_SHA" != "$REMOTE_SHA" ]', source)
        self.assertIn("LIVE_MARKET_DATA_PROVIDER=schwab", source)
        self.assertIn("SCHWAB_TRADING_ENABLED=false", source)
        self.assertIn(
            "python -m options_researcher.schwab_chain_capture", source
        )
        self.assertNotIn("options_researcher.intraday_capture", source)
        self.assertNotIn("tools/intraday_capture.sh", source)

    def test_wrapper_refreshes_origin_main_before_comparing_head(self):
        source = WRAPPER.read_text(encoding="utf-8")
        fetch = source.index("fetch -q origin main")
        read_remote = source.index(
            'REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main'
        )
        branch_check = source.index('if [ "$BRANCH" != "main" ]')

        # Offline refusal reasons stay honest: the branch check runs before
        # the network fetch, and the fetch is bounded and prompt-free because
        # it sits on the irreplaceable-capture critical path.
        self.assertLess(branch_check, fetch)
        self.assertLess(fetch, read_remote)
        self.assertIn("GIT_TERMINAL_PROMPT=0", source)
        self.assertIn("http.lowSpeedLimit=1000", source)
        self.assertIn("http.lowSpeedTime=20", source)

    def test_plist_runs_only_weekdays_at_1545_et(self):
        payload = plistlib.loads(PLIST.read_bytes())
        self.assertEqual(
            payload["Label"],
            "com.carsyn.options-validator.schwab-chain-preclose",
        )
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator-ops/tools/schwab_chain_capture.sh",
            ],
        )
        intervals = payload["StartCalendarInterval"]
        self.assertEqual(
            intervals,
            [
                {"Weekday": weekday, "Hour": 15, "Minute": 45}
                for weekday in range(1, 6)
            ],
        )
        self.assertFalse(payload["RunAtLoad"])
        self.assertNotIn("KeepAlive", payload)
        self.assertNotIn("intraday_capture", str(payload))

    # --- audit M7: failure-taxonomy parity with tools/intraday_capture.sh ---
    #
    # options_researcher/schwab_chain_capture.py's own printed lines are the
    # evidence keyed on below (never the exit code alone -- exit 2 is used
    # both for a genuine receipt CONFLICT and could collide with an
    # unrelated argparse usage error, same caveat as
    # tools/intraday_capture.sh:96-101 documents for its own lane):
    #   "schwab_chain_capture auth EXPIRED: ..."     (main(), exit 1)
    #   "schwab_chain_capture refused: ..."          (capture(), exit 1)
    #   "schwab_chain_capture receipt CONFLICT: ..." (capture(), exit 2)
    #   "schwab_chain_capture failed: ...; receipt=" (capture(), exit 1)
    # This is a *wrapper-only* contract: schwab_chain_capture.py itself is
    # never touched by this change.

    def _run_status_tail(self, *, rc: int, cap_out: str) -> subprocess.CompletedProcess:
        """Run the wrapper's post-capture status/notification tail (the part
        of the script that runs after CAP_OUT/RC are known) with a synthetic
        RC/CAP_OUT, so this test never has to invoke the real Schwab client.
        Extracted by marker rather than line numbers so the test breaks
        loudly (KeyError-shaped ValueError from str.index) if the marker
        text is renamed, instead of silently testing stale dead code."""
        source = WRAPPER.read_text(encoding="utf-8")
        start = source.index("CRITICAL=0")
        block = source[start:]
        script = "\n".join(
            [
                "set -u",
                "REPO=" + shlex.quote(str(ROOT)),
                "STAMP=test-stamp",
                "RC=" + str(rc),
                "CAP_OUT=" + shlex.quote(cap_out),
                block,
            ]
        )
        return subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_expired_refresh_token_requires_schwab_reauth(self):
        cap_out = (
            "schwab_chain_capture auth EXPIRED: Refresh token is invalid, "
            "expired or revoked; run uv run python tools/setup_schwab.py"
        )
        completed = self._run_status_tail(rc=1, cap_out=cap_out)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "CRITICAL: SCHWAB REAUTH REQUIRED -- run uv run python "
            "tools/setup_schwab.py",
            completed.stdout,
        )
        self.assertNotIn("receipt/log contains evidence", completed.stdout)

    def test_refused_branch_is_distinct_from_generic_broken(self):
        cap_out = (
            "schwab_chain_capture refused: 2026-08-10T16:05:00-04:00 ET is "
            "outside the NY regular session"
        )
        completed = self._run_status_tail(rc=1, cap_out=cap_out)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("CRITICAL: SCHWAB CHAIN REFUSED", completed.stdout)
        self.assertIn(
            "schwab_chain_capture refused: 2026-08-10T16:05:00-04:00 ET is "
            "outside the NY regular session",
            completed.stdout,
        )

    def test_receipt_conflict_branch_is_exit_2_and_documents_retry_constraint(
        self,
    ):
        cap_out = (
            "schwab_chain_capture receipt CONFLICT: "
            "reports/schwab_chains/2026-08-10/preclose.json"
        )
        completed = self._run_status_tail(rc=2, cap_out=cap_out)

        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertIn("CRITICAL: SCHWAB CHAIN RECEIPT CONFLICT", completed.stdout)
        self.assertIn("SAME-DAY RETRY IS UNSAFE", completed.stdout)
        self.assertIn("hash-match-or-refuse", completed.stdout)
        self.assertIn("docs/h7-forward-operations.md", completed.stdout)

    def test_partial_failure_branch_is_distinct_and_documents_retry_constraint(
        self,
    ):
        cap_out = (
            "schwab_chain_capture failed: ['CEG']; "
            "receipt=reports/schwab_chains/2026-08-10/preclose.json"
        )
        completed = self._run_status_tail(rc=1, cap_out=cap_out)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("CRITICAL: SCHWAB CHAIN PARTIAL FAILURE", completed.stdout)
        self.assertIn("SAME-DAY RETRY IS UNSAFE", completed.stdout)
        self.assertIn("docs/h7-forward-operations.md", completed.stdout)

    def test_unrecognized_failure_still_falls_back_to_generic_broken(self):
        cap_out = "Traceback (most recent call last):\nRuntimeError: boom"
        completed = self._run_status_tail(rc=1, cap_out=cap_out)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "CRITICAL: SCHWAB CHAIN STATUS unrecognized failure mode",
            completed.stdout,
        )
        self.assertIn(
            "SCHWAB CHAIN STATUS: BROKEN (exit 1; receipt/log contains evidence)",
            completed.stdout,
        )

    def test_ok_result_has_no_critical_line(self):
        completed = self._run_status_tail(rc=0, cap_out="schwab_chain_capture complete: 2/2 x")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("CRITICAL", completed.stdout)
        self.assertIn("SCHWAB CHAIN STATUS: OK", completed.stdout)

    def test_operator_notification_present_and_guarded_like_sibling(self):
        source = WRAPPER.read_text(encoding="utf-8")
        # Guarded the same way as tools/intraday_capture.sh's own osascript
        # calls: a bare `/usr/bin/osascript -e ... 2>/dev/null` fire-and-
        # forget invocation with no pre-existence check and no `$?`
        # handling, so it is a silent no-op on any non-macOS host (this
        # container included) rather than a build/runtime failure.
        self.assertIn("/usr/bin/osascript -e", source)
        self.assertIn('display notification', source)
        osascript_lines = [
            line for line in source.splitlines() if "osascript -e" in line
        ]
        self.assertTrue(osascript_lines, "expected an osascript notification line")
        for line in osascript_lines:
            self.assertTrue(
                line.rstrip().endswith("2>/dev/null"),
                f"osascript line not guarded like the sibling: {line!r}",
            )

    def test_notification_fires_as_a_no_op_off_macos_on_every_branch(self):
        # This container has no /usr/bin/osascript, so if the guard were
        # missing (e.g. an unguarded `$(osascript ...)` whose failure is
        # checked), these would fail or hang instead of returning the
        # underlying RC cleanly.
        for rc, cap_out in (
            (0, "schwab_chain_capture complete: 2/2 x"),
            (1, "schwab_chain_capture refused: outside regular session"),
            (2, "schwab_chain_capture receipt CONFLICT: x"),
        ):
            with self.subTest(rc=rc):
                completed = self._run_status_tail(rc=rc, cap_out=cap_out)
                self.assertEqual(completed.returncode, rc, completed.stderr)

    def test_same_day_retry_constraint_documented_in_wrapper_source(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("SAME-DAY RETRY", source)
        self.assertIn("hash-match-or-refuse", source)
        self.assertIn("docs/h7-forward-operations.md", source)

    # --- owner decision D-3: evidence-only divergence tolerance -------------
    #
    # The gate's purpose is "no unreviewed CODE runs unattended". Strict SHA
    # equality also refused when the only divergence was the daily ritual's own
    # evidence commit whose fail-soft push had failed, turning a transient push
    # failure into a permanently lost irreplaceable 15:45 capture (brief 11
    # §9.2). Behind-divergence still refuses exactly as before.

    def _run_alignment_gate(self, repo: Path) -> subprocess.CompletedProcess:
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        source = WRAPPER.read_text(encoding="utf-8")
        start = source.index("# --- alignment gate")
        end = source.index("# --- end alignment gate")
        block = source[start:end]
        script = "\n".join(
            [
                "REPO=" + shlex.quote(str(repo)),
                'LOCAL_SHA="$(git -C "$REPO" rev-parse HEAD)"',
                'REMOTE_SHA="$(git -C "$REPO" rev-parse origin/main)"',
                block,
                'echo "GATE PASSED"',
            ]
        )
        return subprocess.run(
            [zsh, "-c", script], capture_output=True, text=True, timeout=60
        )

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(repo),
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.com",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
            },
        )

    def _repo_with(self, *, ahead_paths: tuple[str, ...]) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / "checkout"
        repo.mkdir()
        self._git(repo, "init", "-q", "-b", "main")
        (repo / "code.py").write_text("x = 1\n")
        self._git(repo, "add", "code.py")
        self._git(repo, "commit", "-qm", "base")
        self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        for index, relative in enumerate(ahead_paths):
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"payload {index}\n")
            self._git(repo, "add", "--", relative)
            self._git(repo, "commit", "-qm", f"ahead {relative}")
        return repo

    def test_alignment_gate_tolerates_evidence_only_divergence(self):
        repo = self._repo_with(
            ahead_paths=("reports/ritual/run_status.json", "ledger/facts.log")
        )
        completed = self._run_alignment_gate(repo)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("GATE PASSED", completed.stdout)
        self.assertIn("evidence-only commit(s)", completed.stdout)
        self.assertNotIn("REFUSED", completed.stdout)

    def test_alignment_gate_refuses_a_code_commit_ahead(self):
        repo = self._repo_with(ahead_paths=("options_researcher/h7_watch.py",))
        completed = self._run_alignment_gate(repo)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "REFUSED: HEAD is not aligned with origin/main", completed.stdout
        )
        self.assertNotIn("GATE PASSED", completed.stdout)

    def test_alignment_gate_refuses_a_mixed_evidence_and_code_commit(self):
        repo = self._repo_with(
            ahead_paths=("reports/ritual/run_status.json", "tools/daily_ritual.sh")
        )
        completed = self._run_alignment_gate(repo)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "REFUSED: HEAD is not aligned with origin/main", completed.stdout
        )

    def test_alignment_gate_still_refuses_when_behind_origin_main(self):
        repo = self._repo_with(ahead_paths=("reports/ritual/run_status.json",))
        # origin/main moves ahead of this checkout: the divergence is now
        # "unreviewed-code-may-be-missing", which must refuse exactly as before.
        self._git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        self._git(repo, "reset", "-q", "--hard", "HEAD~1")
        completed = self._run_alignment_gate(repo)

        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn(
            "REFUSED: HEAD is not aligned with origin/main", completed.stdout
        )

    def test_alignment_gate_is_silent_when_exactly_aligned(self):
        repo = self._repo_with(ahead_paths=())
        completed = self._run_alignment_gate(repo)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("GATE PASSED", completed.stdout)
        self.assertNotIn("evidence-only", completed.stdout)

    def test_alignment_gate_refuses_an_evil_merge_that_edits_code(self):
        """`git log --name-only` emits NO paths for a merge commit.

        A merge whose own resolution edits a code file therefore reads as
        "evidence-only" under per-commit enumeration. The tree diff sees the
        code file, because the tree really does differ from origin/main.
        """
        repo = self._repo_with(ahead_paths=("reports/ritual/run_status.json",))
        # Every ordinary commit ahead of origin/main touches evidence only; the
        # code edit is introduced by the MERGE COMMIT ITSELF, which is what
        # makes it invisible to per-commit enumeration.
        self._git(repo, "checkout", "-q", "-b", "side", "origin/main")
        side_evidence = repo / "reports" / "ritual" / "side.json"
        side_evidence.parent.mkdir(parents=True, exist_ok=True)
        side_evidence.write_text("{}\n")
        self._git(repo, "add", "--", "reports/ritual/side.json")
        self._git(repo, "commit", "-qm", "side evidence")
        self._git(repo, "checkout", "-q", "main")
        # Same hermetic identity env as _git — this call bypasses the helper
        # only because it needs the returncode (a conflicted merge exits 1).
        merge = subprocess.run(
            ["git", "-C", str(repo), "merge", "--no-commit", "--no-ff", "side"],
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin",
                "HOME": str(repo),
                "GIT_AUTHOR_NAME": "t",
                "GIT_AUTHOR_EMAIL": "t@example.com",
                "GIT_COMMITTER_NAME": "t",
                "GIT_COMMITTER_EMAIL": "t@example.com",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
            },
        )
        self.assertIn(merge.returncode, (0, 1), merge.stderr)
        (repo / "code.py").write_text("x = 3  # smuggled in by the merge itself\n")
        self._git(repo, "add", "code.py")
        self._git(repo, "commit", "-qm", "evil merge")

        # Precondition: the per-commit view really is blind here.
        log_paths = subprocess.run(
            [
                "git",
                "-C",
                str(repo),
                "log",
                "--pretty=format:",
                "--name-only",
                "HEAD",
                "--not",
                "origin/main",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertNotIn("code.py", log_paths)

        completed = self._run_alignment_gate(repo)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn(
            "REFUSED: HEAD is not aligned with origin/main", completed.stdout
        )

    def test_alignment_gate_refuses_a_code_file_renamed_into_an_evidence_path(self):
        """`git log --name-only` reports only a rename's DESTINATION.

        `git mv code.py reports/ritual/code.py` therefore reads as
        evidence-only under per-commit enumeration; the tree diff (with
        --no-renames) reports the deleted source path too.
        """
        repo = self._repo_with(ahead_paths=())
        (repo / "reports" / "ritual").mkdir(parents=True)
        self._git(repo, "mv", "code.py", "reports/ritual/code.py")
        self._git(repo, "commit", "-qm", "move code into an evidence path")

        completed = self._run_alignment_gate(repo)
        self.assertEqual(completed.returncode, 1, completed.stdout + completed.stderr)
        self.assertIn(
            "REFUSED: HEAD is not aligned with origin/main", completed.stdout
        )

    def test_alignment_gate_fails_closed_when_identity_is_unresolvable(self):
        repo = self._repo_with(ahead_paths=("reports/ritual/run_status.json",))
        source = WRAPPER.read_text(encoding="utf-8")
        start = source.index("# --- alignment gate")
        end = source.index("# --- end alignment gate")
        zsh = shutil.which("zsh")
        if zsh is None:
            self.skipTest("zsh is required")
        # A repo whose origin/main cannot be resolved must refuse, never pass.
        script = "\n".join(
            [
                "REPO=" + shlex.quote(str(repo / "does-not-exist")),
                'LOCAL_SHA="a"',
                'REMOTE_SHA="b"',
                source[start:end],
                'echo "GATE PASSED"',
            ]
        )
        completed = subprocess.run(
            [zsh, "-c", script], capture_output=True, text=True, timeout=60
        )
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertNotIn("GATE PASSED", completed.stdout)

    def test_no_behavior_change_to_capture_module_itself(self):
        # Guard rail for this change's own scope: the wrapper may only ever
        # invoke the module as a subprocess, never import/monkeypatch it.
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            "python -m options_researcher.schwab_chain_capture", source
        )


if __name__ == "__main__":
    unittest.main()

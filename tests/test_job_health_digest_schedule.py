"""Offline contract tests for the scheduled job-health digest wrapper."""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools" / "job_health_digest.sh"
PLIST = ROOT / "tools" / "launchagents" / "com.carsyn.options-validator.job-health-digest.plist"


@unittest.skipUnless(Path("/bin/zsh").is_file(), "requires the macOS zsh wrapper")
class JobHealthDigestScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temp_root = Path(temporary.name)
        self.checkout = self.temp_root / "fixture-checkout"
        tools_dir = self.checkout / "tools"
        tools_dir.mkdir(parents=True)
        self.fixture_wrapper = tools_dir / WRAPPER.name
        if WRAPPER.is_file():
            shutil.copy2(WRAPPER, self.fixture_wrapper)

        self.fake_dir = self.checkout / ".tmp" / "fake"
        self.fake_dir.mkdir(parents=True)
        self.argv_log = self.fake_dir / "uv-argv.log"
        self.cwd_log = self.fake_dir / "uv-cwd.log"
        self.date_log = self.fake_dir / "date.log"
        self.notification_log = self.fake_dir / "notification.log"
        self.fake_uv = self._write_executable(
            "fake-uv",
            """#!/bin/zsh
printf '%s\n' "$@" > "$FAKE_UV_ARGV_LOG"
print -r -- "$PWD" > "$FAKE_UV_CWD_LOG"
if [[ "$FAKE_EXPECT_LOCK" == "1" && ! -d "$PWD/.tmp/job_health_digest/run.lock" ]]; then
  print -r -- "expected wrapper lock was missing"
  exit 98
fi
if [[ "$FAKE_UV_WAIT_FOR_SIGNAL" == "1" ]]; then
  print -r -- "$$" > "$FAKE_UV_PID_LOG"
  trap 'print -r -- TERM > "$FAKE_UV_SIGNAL_LOG"; exit 143' TERM
  while true; do sleep 1; done
fi
if [[ "$FAKE_UV_EXIT" -ne 0 ]]; then
  print -r -- "fake digest failure"
  exit "$FAKE_UV_EXIT"
fi
as_of=""
out_dir=""
args=("$@")
for ((index = 1; index <= ${#args}; index++)); do
  if [[ "${args[$index]}" == "--as-of" ]]; then as_of="${args[$((index + 1))]}"; fi
  if [[ "${args[$index]}" == "--out-dir" ]]; then out_dir="${args[$((index + 1))]}"; fi
done
if [[ "$FAKE_UV_WRITE_DIGEST" != "1" ]]; then exit 0; fi
mkdir -p "$out_dir"
if [[ -n "$FAKE_UV_BANNER" ]]; then print -r -- "$FAKE_UV_BANNER"; fi
session="${FAKE_DIGEST_SESSION:-$as_of}"
printf '%s\n\nSession: %s\n' "$FAKE_DIGEST_HEADLINE" "$session" | tee "$out_dir/digest_${as_of}.md"
""",
        )
        self.fake_date = self._write_executable(
            "fake-date",
            """#!/bin/zsh
print -r -- "${TZ:-}|$1" >> "$FAKE_DATE_LOG"
case "$1" in
  +%Y-%m-%d) print -r -- "2026-08-26" ;;
  +%Y-%m-%d_%H%M) print -r -- "2026-08-26_1630" ;;
  *) exit 64 ;;
esac
""",
        )
        self.fake_osascript = self._write_executable(
            "fake-osascript",
            """#!/bin/zsh
printf '%s\n' "$@" >> "$FAKE_NOTIFICATION_LOG"
""",
        )

    def _write_executable(self, name: str, source: str) -> Path:
        path = self.fake_dir / name
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _run_wrapper(
        self,
        *,
        headline: str = "ALL OK",
        tool_exit: int = 0,
        banner: str = "",
        write_digest: bool = True,
        digest_session: str = "",
        expect_lock: bool = False,
        wait_for_signal: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["/bin/zsh", str(self.fixture_wrapper)],
            cwd=self.temp_root,
            env=self._wrapper_env(
                headline=headline,
                tool_exit=tool_exit,
                banner=banner,
                write_digest=write_digest,
                digest_session=digest_session,
                expect_lock=expect_lock,
                wait_for_signal=wait_for_signal,
            ),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _wrapper_env(
        self,
        *,
        headline: str = "ALL OK",
        tool_exit: int = 0,
        banner: str = "",
        write_digest: bool = True,
        digest_session: str = "",
        expect_lock: bool = False,
        wait_for_signal: bool = False,
    ) -> dict[str, str]:
        return {
            **os.environ,
            "HOME": str(self.temp_root / "home"),
            "JOB_HEALTH_UV": str(self.fake_uv),
            "JOB_HEALTH_DATE": str(self.fake_date),
            "JOB_HEALTH_OSASCRIPT": str(self.fake_osascript),
            "FAKE_UV_ARGV_LOG": str(self.argv_log),
            "FAKE_UV_CWD_LOG": str(self.cwd_log),
            "FAKE_UV_EXIT": str(tool_exit),
            "FAKE_DIGEST_HEADLINE": headline,
            "FAKE_UV_BANNER": banner,
            "FAKE_UV_WRITE_DIGEST": "1" if write_digest else "0",
            "FAKE_DIGEST_SESSION": digest_session,
            "FAKE_EXPECT_LOCK": "1" if expect_lock else "0",
            "FAKE_UV_WAIT_FOR_SIGNAL": "1" if wait_for_signal else "0",
            "FAKE_UV_PID_LOG": str(self.fake_dir / "uv-pid.log"),
            "FAKE_UV_SIGNAL_LOG": str(self.fake_dir / "uv-signal.log"),
            "FAKE_DATE_LOG": str(self.date_log),
            "FAKE_NOTIFICATION_LOG": str(self.notification_log),
        }

    def _run_log(self) -> str:
        logs = self._run_logs()
        self.assertEqual(len(logs), 1, logs)
        return logs[0].read_text(encoding="utf-8")

    def _run_logs(self) -> list[Path]:
        return sorted((self.checkout / ".tmp" / "job_health_digest").glob("*.log"))

    def test_wrapper_passes_exact_digest_argv_from_repo_root(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self.argv_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            argv,
            [
                "run",
                "python",
                "-m",
                "tools.job_health_digest",
                "--as-of",
                "2026-08-26",
                "--root",
                str(self.checkout.resolve()),
                "--out-dir",
                str(self.checkout.resolve() / ".tmp" / "job_health"),
            ],
        )
        self.assertRegex(argv[5], re.compile(r"^\d{4}-\d{2}-\d{2}$"))
        self.assertNotIn("--research-root", argv)
        self.assertEqual(
            self.cwd_log.read_text(encoding="utf-8").strip(),
            str(self.checkout.resolve()),
        )
        self.assertEqual(
            self.date_log.read_text(encoding="utf-8").splitlines(),
            [
                "America/New_York|+%Y-%m-%d",
                "America/New_York|+%Y-%m-%d_%H%M",
            ],
        )

    def test_nonzero_tool_exit_is_propagated_and_notified(self) -> None:
        result = self._run_wrapper(tool_exit=17, expect_lock=True)

        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertIn("CRITICAL: job-health digest failed (exit 17)", self._run_log())
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))
        self.assertFalse((self.checkout / ".tmp" / "job_health_digest" / "run.lock").exists())

    def test_stale_digest_is_invalidated_before_a_successful_no_write_run(self) -> None:
        digest = self.checkout / ".tmp" / "job_health" / "digest_2026-08-26.md"
        digest.parent.mkdir(parents=True)
        digest.write_text("ALL OK\n\nSession: 2026-08-26\n", encoding="utf-8")

        result = self._run_wrapper(write_digest=False)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(digest.exists())
        run_log = self._run_log()
        self.assertIn("CRITICAL: job-health digest did not produce a fresh report", run_log)
        self.assertNotIn("job-health digest: ALL OK", run_log)

    def test_successful_tool_without_a_digest_fails_closed(self) -> None:
        result = self._run_wrapper(write_digest=False)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "CRITICAL: job-health digest did not produce a fresh report",
            self._run_log(),
        )
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))

    def test_digest_session_must_match_current_as_of(self) -> None:
        result = self._run_wrapper(digest_session="2026-08-25")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "CRITICAL: job-health digest report session did not match 2026-08-26",
            self._run_log(),
        )
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))

    def test_preexisting_lock_refuses_without_touching_lock_or_running_tool(self) -> None:
        lock = self.checkout / ".tmp" / "job_health_digest" / "run.lock"
        lock.mkdir(parents=True)
        canary = lock / "owner-canary"
        canary.write_text("preserve\n", encoding="utf-8")

        result = self._run_wrapper()

        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertEqual(canary.read_text(encoding="utf-8"), "preserve\n")
        self.assertFalse(self.argv_log.exists())
        self.assertIn("CRITICAL: job-health digest run lock is already held", self._run_log())
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))

    def test_same_minute_runs_have_distinct_logs_and_release_the_lock(self) -> None:
        first = self._run_wrapper()
        second = self._run_wrapper()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        logs = self._run_logs()
        self.assertEqual(len(logs), 2, logs)
        self.assertEqual(len({path.name for path in logs}), 2)
        self.assertFalse((self.checkout / ".tmp" / "job_health_digest" / "run.lock").exists())

    def test_term_signal_releases_lock_and_terminates_tool(self) -> None:
        lock = self.checkout / ".tmp" / "job_health_digest" / "run.lock"
        pid_log = self.fake_dir / "uv-pid.log"
        signal_log = self.fake_dir / "uv-signal.log"
        process = subprocess.Popen(
            ["/bin/zsh", str(self.fixture_wrapper)],
            cwd=self.temp_root,
            env=self._wrapper_env(wait_for_signal=True),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        child_pid: int | None = None
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not pid_log.exists():
                if process.poll() is not None:
                    break
                time.sleep(0.02)
            self.assertTrue(pid_log.exists(), "fake tool did not start")
            child_pid = int(pid_log.read_text(encoding="utf-8").strip())
            self.assertTrue(lock.is_dir(), "wrapper did not hold the run lock")

            process.terminate()
            returncode = process.wait(timeout=5)

            self.assertIn(returncode, (-signal.SIGTERM, 128 + signal.SIGTERM))
            self.assertFalse(lock.exists())
            self.assertEqual(signal_log.read_text(encoding="utf-8"), "TERM\n")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()

    def test_problem_headline_is_critical_and_notified(self) -> None:
        result = self._run_wrapper(headline="2 PROBLEMS")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CRITICAL: job-health digest reported 2 PROBLEMS", self._run_log())
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))

    def test_import_banner_cannot_hide_problem_headline(self) -> None:
        result = self._run_wrapper(
            headline="2 PROBLEMS",
            banner="2026-08-26 16:30:00 | INFO | LumiBot starting",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        run_log = self._run_log()
        self.assertIn("LumiBot starting", run_log)
        self.assertIn("CRITICAL: job-health digest reported 2 PROBLEMS", run_log)
        self.assertNotIn("unrecognized headline", run_log)

    def test_all_ok_headline_is_quiet(self) -> None:
        result = self._run_wrapper()

        self.assertEqual(result.returncode, 0, result.stderr)
        run_log = self._run_log()
        self.assertIn("job-health digest: ALL OK", run_log)
        self.assertNotIn("CRITICAL:", run_log)
        self.assertFalse(self.notification_log.exists())

    def test_wrapper_writes_only_beneath_checkout_tmp(self) -> None:
        outside_canary = self.checkout / "tracked-canary.txt"
        outside_canary.write_text("outside\n", encoding="utf-8")
        inside_canary = self.checkout / ".tmp" / "job_health" / "existing-canary.txt"
        inside_canary.parent.mkdir(parents=True)
        inside_canary.write_text("inside\n", encoding="utf-8")
        before = {
            path.relative_to(self.temp_root): path.read_bytes()
            for path in self.temp_root.rglob("*")
            if path.is_file()
        }

        result = self._run_wrapper(headline="2 PROBLEMS")

        self.assertEqual(result.returncode, 0, result.stderr)
        after = {
            path.relative_to(self.temp_root): path.read_bytes()
            for path in self.temp_root.rglob("*")
            if path.is_file()
        }
        changed = {
            path for path in before.keys() | after.keys() if before.get(path) != after.get(path)
        }
        run_logs = self._run_logs()
        self.assertEqual(len(run_logs), 1, run_logs)
        expected = {
            self.argv_log.relative_to(self.temp_root),
            self.cwd_log.relative_to(self.temp_root),
            self.date_log.relative_to(self.temp_root),
            (self.checkout / ".tmp" / "job_health" / "digest_2026-08-26.md").relative_to(
                self.temp_root
            ),
            run_logs[0].relative_to(self.temp_root),
            self.notification_log.relative_to(self.temp_root),
        }
        self.assertEqual(changed, expected)
        self.assertEqual(outside_canary.read_text(encoding="utf-8"), "outside\n")
        self.assertEqual(inside_canary.read_text(encoding="utf-8"), "inside\n")
        self.assertFalse((self.checkout / ".tmp" / "job_health_digest" / "run.lock").exists())

    def test_plist_runs_from_ops_checkout_on_weekdays_at_1630(self) -> None:
        self.assertTrue(PLIST.is_file(), f"missing LaunchAgent template: {PLIST}")
        payload = plistlib.loads(PLIST.read_bytes())

        self.assertEqual(
            payload["Label"],
            "com.carsyn.options-validator.job-health-digest",
        )
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator-ops/tools/job_health_digest.sh",
            ],
        )
        self.assertEqual(
            payload["WorkingDirectory"],
            "/Users/carsynstephenson/options-validator-ops",
        )
        self.assertEqual(
            payload["StartCalendarInterval"],
            [{"Weekday": weekday, "Hour": 16, "Minute": 30} for weekday in range(1, 6)],
        )
        self.assertEqual(payload["EnvironmentVariables"], {"TZ": "America/New_York"})
        self.assertFalse(payload["RunAtLoad"])
        self.assertNotIn("KeepAlive", payload)
        self.assertTrue(
            payload["StandardOutPath"].startswith(
                "/Users/carsynstephenson/options-validator-ops/.tmp/"
            )
        )
        self.assertTrue(
            payload["StandardErrorPath"].startswith(
                "/Users/carsynstephenson/options-validator-ops/.tmp/"
            )
        )


if __name__ == "__main__":
    unittest.main()

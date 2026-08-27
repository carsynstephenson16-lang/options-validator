"""Offline contract tests for the scheduled job-health digest wrapper."""

from __future__ import annotations

import os
import plistlib
import re
import shutil
import subprocess
import tempfile
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
mkdir -p "$out_dir"
if [[ -n "$FAKE_UV_BANNER" ]]; then print -r -- "$FAKE_UV_BANNER"; fi
printf '%s\n\nSession: %s\n' "$FAKE_DIGEST_HEADLINE" "$as_of" | tee "$out_dir/digest_${as_of}.md"
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
    ) -> subprocess.CompletedProcess[str]:
        env = {
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
            "FAKE_DATE_LOG": str(self.date_log),
            "FAKE_NOTIFICATION_LOG": str(self.notification_log),
        }
        return subprocess.run(
            ["/bin/zsh", str(self.fixture_wrapper)],
            cwd=self.temp_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _run_log(self) -> str:
        logs = sorted((self.checkout / ".tmp" / "job_health_digest").glob("*.log"))
        self.assertEqual(len(logs), 1, logs)
        return logs[0].read_text(encoding="utf-8")

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
        result = self._run_wrapper(tool_exit=17)

        self.assertEqual(result.returncode, 17, result.stderr)
        self.assertIn("CRITICAL: job-health digest failed (exit 17)", self._run_log())
        self.assertIn("display notification", self.notification_log.read_text(encoding="utf-8"))

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
        before = {path.relative_to(self.temp_root) for path in self.temp_root.rglob("*")}

        result = self._run_wrapper(headline="2 PROBLEMS")

        self.assertEqual(result.returncode, 0, result.stderr)
        after = {path.relative_to(self.temp_root) for path in self.temp_root.rglob("*")}
        created = after - before
        allowed_root = (self.checkout / ".tmp").relative_to(self.temp_root)
        self.assertTrue(created)
        self.assertTrue(
            all(path == allowed_root or allowed_root in path.parents for path in created),
            created,
        )

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

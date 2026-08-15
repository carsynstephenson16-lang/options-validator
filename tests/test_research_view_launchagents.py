"""Contract tests for the display-only research-view LaunchAgent templates."""

from __future__ import annotations

import plistlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS_ROOT = "/Users/carsynstephenson/options-validator-ops"
LAUNCHAGENTS = ROOT / "tools" / "launchagents"


class ResearchViewLaunchAgentTest(unittest.TestCase):
    def test_server_template_is_a_managed_localhost_file_server(self):
        path = LAUNCHAGENTS / "com.carsyn.options-validator.research-views.plist"
        payload = plistlib.loads(path.read_bytes())

        self.assertEqual(payload["Label"], "com.carsyn.options-validator.research-views")
        self.assertEqual(
            payload["ProgramArguments"],
            [
                f"{OPS_ROOT}/.venv/bin/python",
                "-m",
                "http.server",
                "8766",
                "--bind",
                "127.0.0.1",
                "--directory",
                f"{OPS_ROOT}/.tmp/dashboard",
            ],
        )
        self.assertEqual(payload["WorkingDirectory"], OPS_ROOT)
        self.assertTrue(payload["RunAtLoad"])
        self.assertTrue(payload["KeepAlive"])
        self.assertEqual(payload["ThrottleInterval"], 10)
        for key in ("StandardOutPath", "StandardErrorPath"):
            self.assertTrue(
                payload[key].startswith(f"{OPS_ROOT}/.tmp/research_views/"),
                f"{key} must be below the research_views log directory",
            )

    def test_refresh_template_runs_weekdays_at_0730_et(self):
        path = LAUNCHAGENTS / "com.carsyn.options-validator.research-display-refresh.plist"
        payload = plistlib.loads(path.read_bytes())

        self.assertEqual(payload["Label"], "com.carsyn.options-validator.research-display-refresh")
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                f"{OPS_ROOT}/tools/research_display_refresh.sh",
            ],
        )
        self.assertEqual(payload["WorkingDirectory"], OPS_ROOT)
        self.assertTrue(payload["RunAtLoad"])
        self.assertNotIn("KeepAlive", payload)
        self.assertEqual(payload["EnvironmentVariables"]["TZ"], "America/New_York")
        self.assertEqual(
            payload["StartCalendarInterval"],
            [{"Weekday": weekday, "Hour": 7, "Minute": 30} for weekday in range(1, 6)],
        )
        for key in ("StandardOutPath", "StandardErrorPath"):
            self.assertTrue(
                payload[key].startswith(f"{OPS_ROOT}/.tmp/research_views/"),
                f"{key} must be below the research_views log directory",
            )


if __name__ == "__main__":
    unittest.main()

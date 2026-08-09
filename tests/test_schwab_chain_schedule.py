"""Offline structural tests for the independent Schwab preclose job."""

from __future__ import annotations

import plistlib
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


if __name__ == "__main__":
    unittest.main()

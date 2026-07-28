"""Offline tests for research-refresh scheduling and durable circuit breakers."""

from __future__ import annotations

import io
import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from tools.research_refresh_guard import (
    ActiveAttempt,
    CircuitOpen,
    MonthlyBudgetExhausted,
    main,
    record_outcome,
    reserve_attempt,
    reset_failures,
    schedule_window_open,
)

NEW_YORK = ZoneInfo("America/New_York")


def _at(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=NEW_YORK)


class ScheduleWindowTest(unittest.TestCase):
    def test_weekday_producer_times_are_allowed(self):
        self.assertTrue(schedule_window_open(_at(27, 7, 40)))
        self.assertTrue(schedule_window_open(_at(27, 8, 10)))

    def test_postclose_and_weekend_are_blocked(self):
        self.assertFalse(schedule_window_open(_at(27, 16, 45)))
        self.assertFalse(schedule_window_open(_at(25, 7, 40)))

    def test_explicit_manual_override_is_required_outside_window(self):
        self.assertTrue(schedule_window_open(_at(25, 16, 45), manual_override=True))


class DurableGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temp.name) / "state"

    def tearDown(self):
        self.temp.cleanup()

    def reserve(self, attempt_id: str, now: datetime, **overrides) -> str:
        kwargs = {
            "attempt_budget_usd": Decimal("8.00"),
            "monthly_budget_usd": Decimal("200.00"),
            "max_failures": 2,
            "stale_minutes": 120,
        }
        kwargs.update(overrides)
        return reserve_attempt(
            self.state_dir,
            attempt_id=attempt_id,
            now_et=now,
            **kwargs,
        )

    def record_failure(self, attempt_id: str, now: datetime) -> str:
        return record_outcome(
            self.state_dir,
            attempt_id=attempt_id,
            succeeded=False,
            failure_class="CLAUDE_EXIT",
            now_et=now,
        )

    def succeed(self, attempt_id: str, now: datetime) -> str:
        return record_outcome(
            self.state_dir,
            attempt_id=attempt_id,
            succeeded=True,
            now_et=now,
        )

    def state(self) -> dict[str, object]:
        path = self.state_dir / "guard_state.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_same_active_attempt_is_single_flight_blocked(self):
        self.assertEqual(self.reserve("a", _at(27, 7, 40)), "RESERVED")
        with self.assertRaisesRegex(ActiveAttempt, "already reserved"):
            self.reserve("a", _at(27, 7, 41))
        attempts = self.state()["attempts"]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["reserved_usd"], "8.00")

    def test_different_active_attempt_is_single_flight_blocked(self):
        self.reserve("a", _at(27, 7, 40))
        with self.assertRaisesRegex(ActiveAttempt, "a is still active"):
            self.reserve("b", _at(27, 7, 41))
        self.assertEqual(len(self.state()["attempts"]), 1)

    def test_two_paid_failures_open_circuit_before_third_attempt(self):
        self.reserve("a", _at(27, 7, 40))
        self.record_failure("a", _at(27, 7, 41))
        self.reserve("b", _at(27, 8, 10))
        self.record_failure("b", _at(27, 8, 11))
        with self.assertRaisesRegex(CircuitOpen, "2 consecutive"):
            self.reserve("c", _at(28, 7, 40))

    def test_success_resets_consecutive_failure_circuit(self):
        self.reserve("a", _at(27, 7, 40))
        self.record_failure("a", _at(27, 7, 41))
        self.reserve("b", _at(27, 8, 10))
        self.succeed("b", _at(27, 8, 11))
        self.assertEqual(self.reserve("c", _at(28, 7, 40)), "RESERVED")
        self.assertEqual(self.state()["consecutive_failures"], 0)

    def test_monthly_worst_case_reservations_are_hard_capped(self):
        limits = {
            "monthly_budget_usd": Decimal("16.00"),
            "max_failures": 10,
        }
        self.reserve("a", _at(27, 7, 40), **limits)
        self.record_failure("a", _at(27, 7, 41))
        self.reserve("b", _at(27, 8, 10), **limits)
        self.record_failure("b", _at(27, 8, 11))
        with self.assertRaisesRegex(MonthlyBudgetExhausted, r"\$16.00"):
            self.reserve("c", _at(28, 7, 40), **limits)

    def test_stale_reservation_becomes_failure_after_timeout(self):
        self.reserve("a", _at(27, 7, 40), max_failures=1)
        with self.assertRaisesRegex(CircuitOpen, "1 consecutive"):
            self.reserve("b", _at(28, 7, 40), max_failures=1)
        attempt = self.state()["attempts"][0]
        self.assertEqual(attempt["status"], "STALE_FAILED")
        self.assertEqual(attempt["failure_class"], "STALE_RESERVATION")

    def test_verified_publication_reconciles_stale_failure_to_success(self):
        self.reserve("published", _at(27, 7, 40), max_failures=10)
        self.reserve("later", _at(28, 7, 40), max_failures=10)
        self.assertEqual(self.state()["attempts"][0]["status"], "STALE_FAILED")
        status = record_outcome(
            self.state_dir,
            attempt_id="published",
            succeeded=True,
            published_success=True,
            now_et=_at(28, 7, 41),
        )
        self.assertEqual(status, "RECONCILED_PUBLISHED")
        attempt = self.state()["attempts"][0]
        self.assertEqual(attempt["status"], "SUCCEEDED")
        self.assertEqual(attempt["reconciled_from"], "STALE_FAILED")
        self.assertNotIn("failure_class", attempt)

    def test_explicit_reset_preserves_budget_history(self):
        self.reserve("a", _at(27, 7, 40))
        self.record_failure("a", _at(27, 7, 41))
        self.reserve("b", _at(27, 8, 10))
        self.record_failure("b", _at(27, 8, 11))
        reset_failures(self.state_dir, now_et=_at(27, 8, 20))
        self.assertEqual(self.reserve("c", _at(28, 7, 40)), "RESERVED")
        attempts = self.state()["attempts"]
        self.assertEqual(
            sum(Decimal(attempt["reserved_usd"]) for attempt in attempts),
            Decimal("24.00"),
        )

    def test_cli_does_not_echo_environment_secrets(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"UNRELATED_SECRET": "do-not-print"}):
            with redirect_stdout(output):
                rc = main(
                    [
                        "reserve",
                        "--state-dir",
                        str(self.state_dir),
                        "--attempt-id",
                        "safe-attempt",
                        "--now",
                        "2026-07-27T07:40:00-04:00",
                    ]
                )
        self.assertEqual(rc, 0)
        self.assertEqual(output.getvalue().strip(), "GUARD_RESERVED")
        self.assertNotIn("do-not-print", output.getvalue())

    def test_cli_returns_nonzero_when_an_attempt_is_active(self):
        self.reserve("active", _at(27, 7, 40))
        output = io.StringIO()
        with redirect_stdout(output):
            rc = main(
                [
                    "reserve",
                    "--state-dir",
                    str(self.state_dir),
                    "--attempt-id",
                    "duplicate-shell",
                    "--now",
                    "2026-07-27T07:41:00-04:00",
                ]
            )
        self.assertEqual(rc, 8)
        self.assertIn("SINGLE_FLIGHT_ACTIVE", output.getvalue())
        self.assertEqual(len(self.state()["attempts"]), 1)

    def test_concurrent_cli_reservations_have_exactly_one_winner(self):
        base = [
            sys.executable,
            "-m",
            "tools.research_refresh_guard",
            "reserve",
            "--state-dir",
            str(self.state_dir),
            "--now",
            "2026-07-27T07:40:00-04:00",
        ]
        processes = [
            subprocess.Popen(
                [*base, "--attempt-id", attempt_id],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for attempt_id in ("concurrent-a", "concurrent-b")
        ]
        results = [process.communicate(timeout=10) for process in processes]
        return_codes = sorted(process.returncode for process in processes)
        self.assertEqual(return_codes, [0, 8], results)
        output = "\n".join(stdout for stdout, _stderr in results)
        self.assertIn("GUARD_RESERVED", output)
        self.assertIn("SINGLE_FLIGHT_ACTIVE", output)
        self.assertEqual(len(self.state()["attempts"]), 1)


class ProducerPlistTest(unittest.TestCase):
    def test_checked_in_schedule_and_environment_are_exact(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "tools/launchd/com.carsyn.options-validator.research-refresh.plist"
        payload = plistlib.loads(path.read_bytes())
        intervals = payload["StartCalendarInterval"]
        actual = {(item["Weekday"], item["Hour"], item["Minute"]) for item in intervals}
        expected = {
            (weekday, hour, minute)
            for weekday in range(1, 6)
            for hour, minute in ((7, 40), (8, 10))
        }
        self.assertEqual(actual, expected)
        self.assertEqual(
            payload["ProgramArguments"],
            [
                "/bin/zsh",
                "/Users/carsynstephenson/options-validator/tools/research_refresh.sh",
            ],
        )
        environment = payload["EnvironmentVariables"]
        self.assertEqual(environment["TZ"], "America/New_York")
        self.assertEqual(
            environment["RESEARCH_RITUAL_ROOT"],
            "/Users/carsynstephenson/options-validator-ops",
        )
        self.assertEqual(environment["RESEARCH_REFRESH_MAX_FAILURES"], "2")
        self.assertEqual(environment["RESEARCH_REFRESH_MONTHLY_BUDGET_USD"], "200.00")


if __name__ == "__main__":
    unittest.main()

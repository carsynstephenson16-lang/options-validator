"""Proactive Schwab refresh-token age advisory (2026-09-02).

The Schwab refresh token dies 7 days after CREATION; refreshing an access
token does NOT reset that clock. Nothing warned before it happened -- the
08-31/09-01 pre-close captures simply died. This module is DISPLAY-ONLY and
advisory: it reads the token file's ``creation_timestamp``, never touches the
network, never mutates the token, and its CLI always exits 0 so it can never
block the ritual or the capture wrapper.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from options_researcher import schwab_token_age

CREATION = datetime(2026, 8, 30, 17, 51, 0, tzinfo=timezone.utc)
EXPIRES_AT_TEXT = "2026-09-06 17:51 UTC"


def _write_token(directory: Path, *, created: datetime) -> Path:
    path = directory / "shared-market-data-tokens.json"
    path.write_text(
        json.dumps(
            {
                "creation_timestamp": int(created.timestamp()),
                "token": {"access_token": "REDACTED", "expires_in": 1800},
            }
        )
    )
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    return path


class TokenExpiryStatusTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_config_constants_are_present(self):
        self.assertEqual(config.SCHWAB_REFRESH_TOKEN_HARD_EXPIRY_DAYS, 7)
        self.assertEqual(config.SCHWAB_TOKEN_WARN_HOURS, 36)

    # -- OK ---------------------------------------------------------------

    def test_fresh_token_is_ok(self):
        path = _write_token(self.dir, created=CREATION)
        result = schwab_token_age.token_expiry_status(
            path, CREATION + timedelta(hours=1))
        self.assertEqual(result["status"], "OK")
        self.assertAlmostEqual(result["hours_remaining"], 167.0, places=3)
        self.assertEqual(result["expires_at_utc"], EXPIRES_AT_TEXT)
        self.assertIn("SCHWAB TOKEN OK", result["message"])
        self.assertIn(EXPIRES_AT_TEXT, result["message"])

    def test_boundary_just_outside_the_warn_window_is_ok(self):
        path = _write_token(self.dir, created=CREATION)
        now = CREATION + timedelta(days=7) - timedelta(hours=36.1)
        result = schwab_token_age.token_expiry_status(path, now)
        self.assertEqual(result["status"], "OK")

    # -- EXPIRING ---------------------------------------------------------

    def test_inside_the_warn_window_is_expiring(self):
        path = _write_token(self.dir, created=CREATION)
        now = CREATION + timedelta(days=7) - timedelta(hours=20.5)
        result = schwab_token_age.token_expiry_status(path, now)
        self.assertEqual(result["status"], "EXPIRING")
        self.assertAlmostEqual(result["hours_remaining"], 20.5, places=3)
        self.assertEqual(
            result["message"],
            "SCHWAB TOKEN EXPIRES IN 20.5h (2026-09-06 17:51 UTC) — re-auth "
            "this weekend with tools/setup_schwab.py",
        )

    def test_warn_hours_boundary_is_expiring(self):
        path = _write_token(self.dir, created=CREATION)
        now = CREATION + timedelta(days=7) - timedelta(hours=36)
        self.assertEqual(
            schwab_token_age.token_expiry_status(path, now)["status"], "EXPIRING")

    # -- EXPIRED ----------------------------------------------------------

    def test_past_hard_expiry_is_expired(self):
        path = _write_token(self.dir, created=CREATION)
        now = CREATION + timedelta(days=7) + timedelta(hours=34.2)
        result = schwab_token_age.token_expiry_status(path, now)
        self.assertEqual(result["status"], "EXPIRED")
        self.assertAlmostEqual(result["hours_remaining"], -34.2, places=3)
        self.assertEqual(result["expires_at_utc"], EXPIRES_AT_TEXT)
        self.assertEqual(
            result["message"],
            "SCHWAB TOKEN EXPIRED 2026-09-06 17:51 UTC (34.2h ago) — re-auth "
            "with: uv run python tools/setup_schwab.py",
        )

    def test_exactly_at_hard_expiry_is_expired(self):
        path = _write_token(self.dir, created=CREATION)
        result = schwab_token_age.token_expiry_status(
            path, CREATION + timedelta(days=7))
        self.assertEqual(result["status"], "EXPIRED")

    def test_hard_expiry_days_argument_is_honoured(self):
        path = _write_token(self.dir, created=CREATION)
        result = schwab_token_age.token_expiry_status(
            path, CREATION + timedelta(days=3), hard_expiry_days=2)
        self.assertEqual(result["status"], "EXPIRED")

    # -- MISSING / UNREADABLE ---------------------------------------------

    def test_missing_file_is_missing(self):
        path = self.dir / "absent.json"
        result = schwab_token_age.token_expiry_status(path, CREATION)
        self.assertEqual(result["status"], "MISSING")
        self.assertIsNone(result["hours_remaining"])
        self.assertIsNone(result["expires_at_utc"])
        self.assertIn("SCHWAB TOKEN MISSING", result["message"])
        self.assertIn("tools/setup_schwab.py", result["message"])

    def test_malformed_json_is_unreadable(self):
        path = self.dir / "bad.json"
        path.write_text("{not json at all")
        result = schwab_token_age.token_expiry_status(path, CREATION)
        self.assertEqual(result["status"], "UNREADABLE")
        self.assertIsNone(result["hours_remaining"])
        self.assertIn("SCHWAB TOKEN UNREADABLE", result["message"])

    def test_missing_creation_timestamp_is_unreadable(self):
        path = self.dir / "nokey.json"
        path.write_text(json.dumps({"token": {"access_token": "x"}}))
        result = schwab_token_age.token_expiry_status(path, CREATION)
        self.assertEqual(result["status"], "UNREADABLE")

    def test_non_numeric_creation_timestamp_is_unreadable(self):
        path = self.dir / "text.json"
        path.write_text(json.dumps({"creation_timestamp": "yesterday"}))
        self.assertEqual(
            schwab_token_age.token_expiry_status(path, CREATION)["status"],
            "UNREADABLE",
        )

    def test_json_list_is_unreadable(self):
        path = self.dir / "list.json"
        path.write_text("[1, 2, 3]")
        self.assertEqual(
            schwab_token_age.token_expiry_status(path, CREATION)["status"],
            "UNREADABLE",
        )

    # -- never leaks the token --------------------------------------------

    def test_message_never_contains_token_material(self):
        path = self.dir / "secret.json"
        path.write_text(
            json.dumps(
                {
                    "creation_timestamp": int(CREATION.timestamp()),
                    "token": {"refresh_token": "SUPERSECRETVALUE"},
                }
            )
        )
        result = schwab_token_age.token_expiry_status(
            path, CREATION + timedelta(hours=1))
        self.assertNotIn("SUPERSECRETVALUE", json.dumps(result))


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def _run(self, path: Path) -> tuple[int, str]:
        import contextlib
        import io

        previous = os.environ.get("SCHWAB_TOKEN_PATH")
        os.environ["SCHWAB_TOKEN_PATH"] = str(path)
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                code = schwab_token_age.main([])
        finally:
            if previous is None:
                os.environ.pop("SCHWAB_TOKEN_PATH", None)
            else:
                os.environ["SCHWAB_TOKEN_PATH"] = previous
        return code, buffer.getvalue()

    def test_cli_exits_zero_and_prints_the_message_when_expired(self):
        path = _write_token(self.dir, created=datetime.now(timezone.utc)
                            - timedelta(days=30))
        code, output = self._run(path)
        self.assertEqual(code, 0)
        self.assertIn("SCHWAB TOKEN EXPIRED", output)

    def test_cli_exits_zero_when_the_token_is_missing(self):
        code, output = self._run(self.dir / "absent.json")
        self.assertEqual(code, 0, "the advisory must never block a caller")
        self.assertIn("SCHWAB TOKEN MISSING", output)


class ShellWiringTests(unittest.TestCase):
    """Both unattended lanes must name the cause before the capture runs."""

    REPO_ROOT = Path(__file__).resolve().parents[1]

    def test_ritual_runs_the_advisory_fail_soft(self):
        source = (self.REPO_ROOT / "tools" / "daily_ritual.sh").read_text()
        self.assertIn(
            '"$UV" run python -m options_researcher.schwab_token_age || true',
            source,
        )
        # Advisory only: it must not touch the status computation.
        line = next(
            line for line in source.splitlines()
            if "options_researcher.schwab_token_age" in line
        )
        self.assertNotIn("crit ", line)
        self.assertNotIn("CRITICAL", line)

    def test_capture_wrapper_runs_the_advisory_before_the_capture(self):
        source = (
            self.REPO_ROOT / "tools" / "schwab_chain_capture.sh"
        ).read_text()
        advisory = source.index("options_researcher.schwab_token_age")
        capture = source.index("options_researcher.schwab_chain_capture 2>&1")
        self.assertLess(advisory, capture)
        self.assertIn(
            '"$UV" run python -m options_researcher.schwab_token_age || true',
            source,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

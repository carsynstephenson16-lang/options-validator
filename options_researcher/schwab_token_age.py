"""Advisory age check for the shared Schwab OAuth refresh token.

Why this exists: the Schwab refresh token expires SEVEN DAYS after it is
CREATED, and refreshing an access token does not reset that clock. Until now
nothing warned in advance -- the token simply died mid-week and the 15:45
pre-close capture failed (2026-08-31, 2026-09-01).

This module is DISPLAY-ONLY:
  * it never touches the network and never contacts Schwab;
  * it never reads, logs, or writes any token material -- only the file's
    ``creation_timestamp``;
  * its CLI always exits 0, so wiring it into the ritual or the capture
    wrapper can never block them.

The 7-day figure is a provider convention, not a tuned parameter; both
constants live in ``config.py`` with their provenance labels.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
from data.schwab_credentials import SHARED_TOKEN_PATH

REPO_ROOT = Path(__file__).resolve().parent.parent
REAUTH_COMMAND = "uv run python tools/setup_schwab.py"
_UTC_FORMAT = "%Y-%m-%d %H:%M UTC"


def _format_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(_UTC_FORMAT)


def _unreadable(path: Path, reason: str) -> dict:
    return {
        "status": "UNREADABLE",
        "hours_remaining": None,
        "expires_at_utc": None,
        "message": (
            f"SCHWAB TOKEN UNREADABLE at {path} ({reason}) — re-auth with: "
            f"{REAUTH_COMMAND}"
        ),
    }


def token_expiry_status(
    token_path: Path,
    now: datetime,
    hard_expiry_days: int = config.SCHWAB_REFRESH_TOKEN_HARD_EXPIRY_DAYS,
    warn_hours: int = config.SCHWAB_TOKEN_WARN_HOURS,
) -> dict:
    """Classify the refresh token's remaining life from its creation stamp.

    Pure: no network, no mutation, no clock read (``now`` is supplied by the
    caller). Returns ``status`` in EXPIRED / EXPIRING / OK / MISSING /
    UNREADABLE, plus a single loud operator line in ``message``.
    """
    token_path = Path(token_path)
    if not token_path.is_file():
        return {
            "status": "MISSING",
            "hours_remaining": None,
            "expires_at_utc": None,
            "message": (
                f"SCHWAB TOKEN MISSING at {token_path} — re-auth with: "
                f"{REAUTH_COMMAND}"
            ),
        }

    try:
        payload = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return _unreadable(token_path, type(error).__name__)
    if not isinstance(payload, dict):
        return _unreadable(token_path, "top level is not a JSON object")
    raw_created = payload.get("creation_timestamp")
    if not isinstance(raw_created, (int, float)) or isinstance(raw_created, bool):
        return _unreadable(token_path, "no numeric creation_timestamp")

    created = datetime.fromtimestamp(float(raw_created), tz=timezone.utc)
    expires_at = created + timedelta(days=hard_expiry_days)
    expires_at_utc = _format_utc(expires_at)
    hours_remaining = (expires_at - now).total_seconds() / 3600.0

    if hours_remaining <= 0.0:
        return {
            "status": "EXPIRED",
            "hours_remaining": hours_remaining,
            "expires_at_utc": expires_at_utc,
            "message": (
                f"SCHWAB TOKEN EXPIRED {expires_at_utc} "
                f"({abs(hours_remaining):.1f}h ago) — re-auth with: "
                f"{REAUTH_COMMAND}"
            ),
        }
    if hours_remaining <= warn_hours:
        return {
            "status": "EXPIRING",
            "hours_remaining": hours_remaining,
            "expires_at_utc": expires_at_utc,
            "message": (
                f"SCHWAB TOKEN EXPIRES IN {hours_remaining:.1f}h "
                f"({expires_at_utc}) — re-auth this weekend with "
                "tools/setup_schwab.py"
            ),
        }
    return {
        "status": "OK",
        "hours_remaining": hours_remaining,
        "expires_at_utc": expires_at_utc,
        "message": (
            f"SCHWAB TOKEN OK: {hours_remaining:.1f}h remaining "
            f"(expires {expires_at_utc})"
        ),
    }


def resolve_token_path() -> Path:
    """Token path from the environment, mirroring data/schwab_adapter.py.

    ``SCHWAB_TOKEN_PATH`` wins if already exported (the LaunchAgents and the
    capture wrapper inherit it); otherwise ``.env`` is consulted, and the
    shared default is the last resort. No validation is done here -- an
    unusable path resolves to MISSING/UNREADABLE, which is exactly the
    advisory this module is for.
    """
    raw = os.environ.get("SCHWAB_TOKEN_PATH", "").strip()
    if not raw:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env")
        raw = os.environ.get("SCHWAB_TOKEN_PATH", "").strip()
    path = Path(raw).expanduser() if raw else Path(SHARED_TOKEN_PATH)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def main(argv: list[str] | None = None) -> int:
    """Print the advisory line. ALWAYS returns 0 -- never blocks a caller."""
    del argv
    try:
        result = token_expiry_status(
            resolve_token_path(), datetime.now(timezone.utc))
        print(result["message"])
    except Exception as error:  # pragma: no cover - advisory must never fail
        print(f"SCHWAB TOKEN CHECK UNAVAILABLE ({type(error).__name__})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))

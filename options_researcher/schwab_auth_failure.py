"""Safe operator classification for Schwab OAuth refresh-token expiry."""

from __future__ import annotations

from authlib.integrations.base_client.errors import OAuthError

SCHWAB_REAUTH_COMMAND = "uv run python tools/setup_schwab.py"


def is_expired_refresh_token_error(exc: BaseException) -> bool:
    """Return true only for Authlib's invalid/expired refresh-token failure."""
    if not isinstance(exc, OAuthError) or exc.error != "invalid_grant":
        return False
    description = str(exc.description or "").lower()
    return "refresh token" in description and any(
        marker in description for marker in ("invalid", "expired", "revoked")
    )


def expired_auth_line(capture_name: str) -> str:
    return (
        f"{capture_name} auth EXPIRED: Refresh token is invalid, expired or "
        f"revoked; run {SCHWAB_REAUTH_COMMAND}"
    )

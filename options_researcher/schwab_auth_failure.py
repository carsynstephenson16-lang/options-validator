"""Safe operator classification for Schwab OAuth refresh-token expiry."""

from __future__ import annotations

import re

from authlib.integrations.base_client.errors import OAuthError

SCHWAB_REAUTH_COMMAND = "uv run python tools/setup_schwab.py"

# Schwab returns the real cause inside the error payload, and authlib does not
# always surface it as ``.error``. The 2026-08-31 / 2026-09-01 pre-close
# failures raised ``UnsupportedTokenTypeError`` (``.error ==
# "unsupported_token_type"``) whose description was:
#   400 Bad Request: "{"error_description":"Refresh token is invalid, expired
#   or revoked","error":"invalid_grant"}"
# so gating on ``.error`` alone missed it and the operator never saw the
# actionable re-auth line. Classify on the description text instead.
_INVALID_GRANT_PAYLOAD = re.compile(r'"error"\s*:\s*"invalid_grant"')
_EXPIRY_MARKERS = ("invalid", "expired", "revoked")


def is_expired_refresh_token_error(exc: BaseException) -> bool:
    """Return true only for Authlib's invalid/expired refresh-token failure.

    The ``OAuthError`` isinstance gate is deliberately kept: a non-OAuth
    exception whose message happens to mention a refresh token is not an auth
    expiry. Within that gate the decision reads the human-readable
    description (and ``str(exc)``, which authlib builds as
    ``"{error}: {description}"``), NOT the ``.error`` code.
    """
    if not isinstance(exc, OAuthError):
        return False
    # Review follow-up A (2026-09-02): an OAuthError whose ``.error`` code IS
    # ``invalid_grant`` is an expiry even when its description is empty; keep
    # that arm alongside the text match so neither shape is missed.
    if getattr(exc, "error", None) == "invalid_grant":
        return True
    text = f"{getattr(exc, 'description', '') or ''}\n{exc}".lower()
    if _INVALID_GRANT_PAYLOAD.search(text):
        return True
    return "refresh token" in text and any(
        marker in text for marker in _EXPIRY_MARKERS
    )


def expired_auth_line(capture_name: str) -> str:
    return (
        f"{capture_name} auth EXPIRED: Refresh token is invalid, expired or "
        f"revoked; run {SCHWAB_REAUTH_COMMAND}"
    )

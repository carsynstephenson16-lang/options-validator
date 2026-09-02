"""Operator classification of Schwab OAuth refresh-token expiry.

Context (2026-09-02): on 2026-08-31 and 2026-09-01 the pre-close capture died
with an expired refresh token, but the operator never saw the actionable
"auth EXPIRED" line. The exception authlib actually raised was
``UnsupportedTokenTypeError`` (class attribute ``.error ==
"unsupported_token_type"``), not a plain ``OAuthError`` with ``.error ==
"invalid_grant"`` -- the real ``invalid_grant`` only appeared inside the
description payload. The old classifier gated on ``.error`` first, so the
classification silently fell through to the generic ``except Exception``
handler in ``schwab_chain_capture.py``.

These tests pin the corrected contract: the ``isinstance(exc, OAuthError)``
gate stays, but classification reads the human-readable description/``str``
text, independent of the ``.error`` code.
"""

from __future__ import annotations

import unittest

from authlib.integrations.base_client.errors import (
    OAuthError,
    UnsupportedTokenTypeError,
)

from options_researcher.schwab_auth_failure import (
    SCHWAB_REAUTH_COMMAND,
    expired_auth_line,
    is_expired_refresh_token_error,
)

# Verbatim description from the 2026-08-31 / 2026-09-01 pre-close failures.
# The full str(exc) was:
#   OAuthError: unsupported_token_type: 400 Bad Request: "{"error_description"
#   :"Refresh token is invalid, expired or revoked","error":"invalid_grant"}"
OBSERVED_DESCRIPTION = (
    '400 Bad Request: "{"error_description":"Refresh token is invalid, '
    'expired or revoked","error":"invalid_grant"}"'
)


class ExpiredRefreshTokenClassificationTests(unittest.TestCase):
    def test_observed_unsupported_token_type_is_classified(self):
        """The exception shape that actually broke the 08-31/09-01 captures."""
        exc = UnsupportedTokenTypeError(description=OBSERVED_DESCRIPTION)
        # Guard the premise: this is the shape the old code could not see.
        self.assertEqual(exc.error, "unsupported_token_type")
        self.assertIsInstance(exc, OAuthError)
        self.assertTrue(is_expired_refresh_token_error(exc))

    def test_legacy_invalid_grant_oautherror_still_classified(self):
        """The originally-handled shape must not regress."""
        exc = OAuthError(
            "invalid_grant", "Refresh token is invalid, expired or revoked")
        self.assertTrue(is_expired_refresh_token_error(exc))

    def test_classification_is_case_insensitive(self):
        exc = UnsupportedTokenTypeError(
            description="REFRESH TOKEN IS INVALID, EXPIRED OR REVOKED")
        self.assertTrue(is_expired_refresh_token_error(exc))

    def test_invalid_grant_json_marker_alone_is_enough(self):
        """A payload naming invalid_grant classifies even without the
        'invalid/expired/revoked' adjectives next to 'refresh token'."""
        exc = UnsupportedTokenTypeError(
            description='400 Bad Request: "{"error":"invalid_grant"}"')
        self.assertTrue(is_expired_refresh_token_error(exc))

    # -- negatives -------------------------------------------------------

    def test_rate_limit_oautherror_is_not_classified(self):
        exc = OAuthError(
            "rate_limit_exceeded",
            "Individual App's transactions per seconds restriction reached.")
        self.assertFalse(is_expired_refresh_token_error(exc))

    def test_unrelated_unsupported_token_type_is_not_classified(self):
        exc = UnsupportedTokenTypeError(
            description="Unsupported token_type: 'access_token'")
        self.assertFalse(is_expired_refresh_token_error(exc))

    def test_non_oautherror_with_matching_text_is_not_classified(self):
        """The isinstance gate stays: a random RuntimeError whose message
        happens to mention a refresh token must not be misread as an auth
        expiry."""
        exc = RuntimeError("Refresh token is invalid, expired or revoked")
        self.assertFalse(is_expired_refresh_token_error(exc))

    def test_empty_description_is_not_classified(self):
        self.assertFalse(is_expired_refresh_token_error(OAuthError()))


class ExpiredAuthLineTests(unittest.TestCase):
    def test_line_names_the_capture_and_the_reauth_command(self):
        line = expired_auth_line("schwab_chain_capture")
        self.assertIn("schwab_chain_capture", line)
        self.assertIn("auth EXPIRED", line)
        self.assertIn(SCHWAB_REAUTH_COMMAND, line)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

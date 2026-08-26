"""Shared source URL policy for cached, display-only research inputs.

Promotion of this policy or its consumers into ranking or signal authority
requires a separate owner decision, registration, and the 2026-07-24 gate.
"""

from __future__ import annotations

from typing import Final

BANNED_HOST_FRAGMENTS: Final = (
    "reddit.",
    "youtube.",
    "youtu.be",
    "seekingalpha.",
    "medium.",
    "substack.",
    "wordpress.",
    "blogspot.",
    "stocktwits.",
    "fool.",
)

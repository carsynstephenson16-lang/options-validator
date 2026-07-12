"""Shared scope identity for every H7 forward-roadmap component."""

from __future__ import annotations

import config


def watch_universe() -> list[str]:
    """The exact names evaluated by H7's watcher and operational gates."""
    return [
        symbol
        for symbol in config.H7_WATCHLIST + config.H7_CORE_LONG_ONLY
        if symbol not in config.H7_EXCLUDED
    ]

"""Shared scope identity for every H7 forward-roadmap component.

The scope is deliberately a small, typed contract instead of an implicit
call to ``config``.  Every receipt-bearing H7 command can therefore prove
which names it evaluated, and an old receipt cannot silently become current
when the watchlist changes.
"""

from __future__ import annotations

import config
from research.hashing import canonical_json, sha256_hex

H7_SCOPE_ID = "h7-forward-15-v1"
H7_SCOPE_VERSION = 1


def scope_symbols() -> tuple[str, ...]:
    """Return the current official 15-name H7 scope in stable order."""
    names = tuple(dict.fromkeys(
        symbol.upper()
        for symbol in config.H7_WATCHLIST + config.H7_CORE_LONG_ONLY
        if symbol not in config.H7_EXCLUDED
    ))
    if len(names) != 15 or len(set(names)) != len(names):
        raise RuntimeError(
            f"{H7_SCOPE_ID} requires 15 unique names; got {list(names)}")
    return names


def scope_manifest(symbols: tuple[str, ...] | list[str] | None = None) -> dict:
    """Return the canonical, hashable identity of an H7 scope.

    ``symbols`` is accepted for replay/tests, but callers that mean the
    official current scope should use the default.  A custom scope gets a
    distinct id so it cannot masquerade as the official activation scope.
    """
    names = tuple(dict.fromkeys(s.upper() for s in
                               (scope_symbols() if symbols is None else symbols)))
    if symbols is None:
        scope_id = H7_SCOPE_ID
    else:
        scope_id = (H7_SCOPE_ID if sorted(names) == sorted(scope_symbols())
                    else "h7-custom-v1")
    return {
        "scope_id": scope_id,
        "scope_version": H7_SCOPE_VERSION,
        "symbols": sorted(names),
    }


def scope_hash(symbols: tuple[str, ...] | list[str] | None = None) -> str:
    """Hash the canonical scope identity used by all H7 evidence."""
    return sha256_hex(canonical_json(scope_manifest(symbols)))


def scope_identity(symbols: tuple[str, ...] | list[str] | None = None) -> dict:
    """Return ``scope_manifest`` plus its stable hash."""
    manifest = scope_manifest(symbols)
    return {**manifest, "scope_hash": scope_hash(symbols)}


def watch_universe() -> list[str]:
    """The exact names evaluated by H7's watcher and operational gates."""
    return list(scope_symbols())

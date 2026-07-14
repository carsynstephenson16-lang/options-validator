"""Canonical parser for content-bound BLIND_CACHE acquisition facts."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

FACTS_PATH = Path("ledger/facts.log")
_BLIND_CACHE_RE = re.compile(
    r"^(\S+)\tBLIND_CACHE symbol=(\S+) date=(\S+) rows=\S+ "
    r"sha256=([0-9a-f]{64})(?:\s|$)"
)


def load_blind_cache_facts(path: Path = FACTS_PATH) -> dict[tuple[str, str], dict]:
    """Return the latest timestamp+SHA evidence for each symbol/session.

    A line that claims to be BLIND_CACHE evidence but violates the canonical
    contract is an integrity error, not an ignorable comment. Later canonical
    lines replace earlier ones for the same symbol/session, matching the cache
    audits' existing latest-evidence behavior.
    """
    source = Path(path)
    out: dict[tuple[str, str], dict] = {}
    if not source.exists():
        return out
    with source.open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if "\tBLIND_CACHE " not in line:
                continue
            match = _BLIND_CACHE_RE.match(line)
            if match is None:
                raise ValueError(
                    f"{source}:{line_number}: malformed BLIND_CACHE fact"
                )
            fetched = datetime.fromisoformat(match.group(1))
            if fetched.tzinfo is None or fetched.utcoffset() is None:
                raise ValueError(
                    f"{source}:{line_number}: BLIND_CACHE timestamp is naive"
                )
            out[(match.group(2), match.group(3))] = {
                "fetched": fetched,
                "sha256": match.group(4),
            }
    return out

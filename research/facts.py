"""
research/facts.py -- append-only DESCRIPTIVE log (ThetaData gaps, measured
spreads, workflow notes). Deliberately separate from the hypothesis ledger and
explicitly NOT verdict-feeding: the "learn facts, not parameters" channel.
"""
from __future__ import annotations

import fcntl
from datetime import datetime, timezone
from pathlib import Path


def _path(base_dir):
    return Path(base_dir) / "facts.log"


def append_fact(
    text: str,
    base_dir="ledger",
    *,
    dedupe_prefix: str | None = None,
) -> None:
    if dedupe_prefix is not None and (
        not dedupe_prefix or not text.startswith(dedupe_prefix)
    ):
        raise ValueError("dedupe_prefix must be a non-empty prefix of the fact")
    p = _path(base_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with p.open("a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            if dedupe_prefix is not None:
                f.seek(0)
                for line in f:
                    _, separator, payload = line.partition("\t")
                    if separator and payload.startswith(dedupe_prefix):
                        return
                f.seek(0, 2)
            f.write(f"{stamp}\t{text}\n")
            f.flush()
            import os
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def read_facts(base_dir="ledger") -> list[str]:
    p = _path(base_dir)
    if not p.exists():
        return []
    return [line for line in p.read_text().splitlines() if line.strip()]

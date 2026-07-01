"""
research/facts.py -- append-only DESCRIPTIVE log (ThetaData gaps, measured
spreads, workflow notes). Deliberately separate from the hypothesis ledger and
explicitly NOT verdict-feeding: the "learn facts, not parameters" channel.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path


def _path(base_dir):
    return Path(base_dir) / "facts.log"


def append_fact(text: str, base_dir="ledger") -> None:
    p = _path(base_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with p.open("a") as f:
        f.write(f"{stamp}\t{text}\n")


def read_facts(base_dir="ledger") -> list[str]:
    p = _path(base_dir)
    if not p.exists():
        return []
    return [line for line in p.read_text().splitlines() if line.strip()]

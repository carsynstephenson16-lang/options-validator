"""options_researcher/earnings.py -- curated earnings-date loader.

CSVs live in data/earnings/{SYMBOL}.csv with columns date,when,source_url.
Every row was compiled with a citation (IR press release or SEC 8-K); this
loader REFUSES malformed files instead of silently coping -- a wrong or
missing earnings date corrupts every downstream study.
"""
from __future__ import annotations

import csv
import os
from datetime import date

EARNINGS_DIR = os.path.join("data", "earnings")
_REQUIRED = ["date", "when", "source_url"]
_WHEN = {"bmo", "amc", "unknown"}


def load_earnings(symbol: str) -> list[date]:
    """Strictly-increasing announcement dates for `symbol`. Raises
    FileNotFoundError (no file) or ValueError (malformed content)."""
    path = os.path.join(EARNINGS_DIR, f"{symbol}.csv")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} missing -- compile it (with source URLs) before "
            "building features for {symbol}")
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _REQUIRED:
            raise ValueError(
                f"{path}: header must be {_REQUIRED}, got {reader.fieldnames}")
        out: list[date] = []
        for i, row in enumerate(reader, start=2):
            if not row["source_url"].strip():
                raise ValueError(f"{path}:{i}: empty source_url")
            if row["when"] not in _WHEN:
                raise ValueError(f"{path}:{i}: when={row['when']!r} not in {_WHEN}")
            d = date.fromisoformat(row["date"])
            if out and d <= out[-1]:
                raise ValueError(f"{path}:{i}: dates not strictly increasing")
            out.append(d)
    return out

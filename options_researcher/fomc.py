"""options_researcher/fomc.py -- FOMC decision-date loader.

data/events/fomc_dates.csv holds the DECISION date (final day) of each
scheduled FOMC meeting, taken from the Federal Reserve's published calendar
(source_url on every row; Official-source). Like earnings.py, this loader
REFUSES malformed files instead of silently coping. Descriptive use only:
the scanner flags "FOMC inside this option's cycle" AMBER; the flag never
gates, scores, or ranks a candidate.
"""
from __future__ import annotations

import csv
import os
from datetime import date

FOMC_PATH = os.path.join("data", "events", "fomc_dates.csv")
_REQUIRED = ["date", "source_url"]


def load_fomc() -> list[date]:
    """Strictly-increasing FOMC decision dates. Raises FileNotFoundError
    (no file) or ValueError (malformed content)."""
    if not os.path.exists(FOMC_PATH):
        raise FileNotFoundError(
            f"{FOMC_PATH} missing -- compile it from the Fed's published "
            "calendar (with source URLs) first")
    with open(FOMC_PATH, newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != _REQUIRED:
            raise ValueError(
                f"{FOMC_PATH}: header must be {_REQUIRED}, "
                f"got {reader.fieldnames}")
        out: list[date] = []
        for i, row in enumerate(reader, start=2):
            if not row["source_url"].strip():
                raise ValueError(f"{FOMC_PATH}:{i}: empty source_url")
            d = date.fromisoformat(row["date"])
            if out and d <= out[-1]:
                raise ValueError(
                    f"{FOMC_PATH}:{i}: dates not strictly increasing")
            out.append(d)
    return out

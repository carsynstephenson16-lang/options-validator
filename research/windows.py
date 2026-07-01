"""
research/windows.py -- the in-sample / out-of-sample boundary at IN_SAMPLE_END.

Keyed on ENTRY date: a trade belongs to the window in which the decision was
made. Keying on exit date would reintroduce look-ahead.
"""
from __future__ import annotations
from datetime import date


def _as_date(x):
    return date.fromisoformat(x) if isinstance(x, str) else x


def split_is_oos(entry_dates, in_sample_end):
    """Return (is_indices, oos_indices). In-sample = entry <= IN_SAMPLE_END."""
    end = _as_date(in_sample_end)
    is_idx = [i for i, d in enumerate(entry_dates) if _as_date(d) <= end]
    oos_idx = [i for i, d in enumerate(entry_dates) if _as_date(d) > end]
    return is_idx, oos_idx


def assert_oos_only(entry_dates, in_sample_end) -> None:
    """Raise if any trade is dated on/before IN_SAMPLE_END (a leak into OOS)."""
    end = _as_date(in_sample_end)
    leaked = [d for d in entry_dates if _as_date(d) <= end]
    if leaked:
        raise ValueError(
            f"OOS evaluation contains {len(leaked)} in-sample-dated trade(s): {leaked[:3]}")

"""Descriptive quote-age sidecar for one Schwab chain capture package.

Codex brief 32 (`docs/superpowers/plans/2026-08-28-32-schwab-quote-age-gate-codex-brief.md`,
rev 4). Owner ruling 2026-08-28 in-session: **"Report now, gate later"** -- this
module ships a DESCRIPTIVE report only. There is no threshold, no gate, and no
GO/NO_GO effect anywhere in it; the blocking per-quote age gate is a recorded
work package of the future H7 Schwab window registration arc and is explicitly
NOT implemented here.

What it writes
--------------
One JSON sidecar per capture, next to that capture's receipt::

    reports/schwab_chains/<session>/<receipt-stem>.quote_age.json

The filename derives from the capture's ``receipt_filename`` stem (pre-close ->
``preclose.quote_age.json``; a second lane writing ``midday.json`` into the SAME
session directory gets ``midday.quote_age.json``). A fixed name would collide
across lanes and the caller's fail-soft wrapper would silently swallow the
refusal.

What the numbers mean (read this before quoting one)
----------------------------------------------------
Every age is measured against the per-symbol MAXIMUM of the same timestamp
column over ALL rows of that symbol's chain file. That makes it a WITHIN-PACKAGE
DISPERSION measure, not absolute wall-clock staleness: a package whose quotes
are ALL late reads as fresh. The only absolute cross-day signal here is the
prior-/after-session row counts, which convert each timestamp to
``America/New_York`` and compare its date against the capture session date (the
stored dtype is ``datetime64[ns, UTC]``, so the tz conversion is explicit).

Statistics are reported for BOTH timestamp columns and for TWO row populations
-- all rows, and the selectable subset -- because a single blended number reads
as a false alarm. Reviewer-measured 2026-08-28 across the seven timestamped
sessions: worst all-rows age 375-1,787 minutes (dominated by illiquid
contracts) against 0.61-10.38 minutes for the selectable subset.

Determinism
-----------
The report is a pure function of (session, symbols, chain frames, manifest
hash). It carries no wall-clock generation stamp, so re-running the same
package reproduces the same bytes and the overwrite guard's "identical rewrite
is a no-op" branch is real rather than decorative.

Authority
---------
The artifact carries the repo's machine-checked pair ``"display_only": true``
and ``"verdict_eligible": false`` (the enforced precedent is
``options_researcher/ownership_context.py:164-166``). It is not verdict-bearing,
not FIRE-capable, and is not a registered signal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import cast

import pandas as pd

import config
from data.atomic_io import atomic_text_write

SCHEMA_VERSION = "schwab_quote_age_report/v1"
SIDECAR_SUFFIX = ".quote_age.json"
NY_TZ = "America/New_York"
TIMESTAMP_COLUMNS = ("timestamp", "trade_timestamp")
SELECTABILITY_COLUMNS = ("bid", "ask", "open_interest", "delta")
POPULATIONS = ("all_rows", "selectable")

# Distinct, stable, anchored prefix for the caller's fail-soft note. It must NOT
# match any of the four pinned `^schwab_chain_capture <label>:` classifications
# that tools/schwab_chain_capture.sh greps for (pinned in
# tests/test_shell_banner_guard.py) -- a chronically failing report has to stay
# greppable in the ops log instead of being misfiled as a capture failure.
SKIP_NOTE_PREFIX = "schwab_quote_age_report skipped:"

# Strategy-selectable moneyness band, mirroring data/recent_topup.py's
# SELECTABLE_ABS_DELTA. That module's default mask is private (`_liquid_mask`)
# and a public accessor for it is future work owned by the H7 registration arc,
# so the band is duplicated here rather than imported: importing
# data.recent_topup would drag data.thetadata_adapter onto the 15:45 capture's
# import path for a display-only sidecar. tests/test_schwab_quote_age_report.py
# asserts this tuple still equals the source of truth, so the copy cannot drift
# silently. The two liquidity thresholds come from config.py (no magic numbers).
SELECTABLE_ABS_DELTA = (0.15, 0.85)

SEMANTICS = (
    "WITHIN-PACKAGE DISPERSION, not absolute wall-clock age: each row's age is "
    "measured against the per-symbol MAXIMUM of the same timestamp column over "
    "ALL rows of that symbol's chain file, so a package whose quotes are ALL "
    "late reads as fresh. Absolute cross-day staleness appears only in "
    "prior_session_rows / after_session_rows, which compare each timestamp "
    "converted to America/New_York against the capture session date. All-rows "
    "statistics are dominated by illiquid contracts and run orders of magnitude "
    "worse than the selectable subset, so the two populations are reported "
    "separately; a single blended statistic reads as a false alarm. Descriptive "
    "only -- no threshold, no gate, no effect on any receipt, verdict, or "
    "GO/NO_GO decision."
)


class SchwabQuoteAgeReportError(RuntimeError):
    """The sidecar could not be built or would overwrite differing bytes."""


def sidecar_filename(receipt_filename: str) -> str:
    """Derive ``<receipt-stem>.quote_age.json`` from a capture receipt name."""
    name = str(receipt_filename)
    if not name or "/" in name or "\\" in name:
        raise SchwabQuoteAgeReportError(f"receipt_filename must be a bare filename: {name!r}")
    stem = Path(name).stem
    if not stem or stem.startswith("."):
        raise SchwabQuoteAgeReportError(f"receipt_filename has no usable stem: {name!r}")
    return f"{stem}{SIDECAR_SUFFIX}"


def sidecar_path(reports_dir: Path, session: str, receipt_filename: str) -> Path:
    """Resolve the sidecar path inside the capture's own session directory."""
    return Path(reports_dir) / session / sidecar_filename(receipt_filename)


def selectable_mask(frame: pd.DataFrame) -> pd.Series:
    """Generic liquid-and-in-band selection proxy over one chain frame.

    Reimplements data/recent_topup.py's DEFAULT audit mask inline (liquidity
    gate from config, then the |delta| band) because that module's mask is
    private and a public accessor is future work owned by the H7 registration
    arc. This is a descriptive proxy for "contracts a strategy lane could
    plausibly select", not any registered lane's exact selection rule.
    """
    missing = [column for column in SELECTABILITY_COLUMNS if column not in frame.columns]
    if missing:
        raise SchwabQuoteAgeReportError(f"chain frame missing selectability columns: {missing}")
    mid = (frame["bid"] + frame["ask"]) / 2.0
    liquid = (
        (frame["open_interest"] >= config.MIN_OPEN_INTEREST)
        & (frame["bid"] >= 0)
        & (frame["ask"] > 0)
        & (frame["ask"] >= frame["bid"])
        & (mid > 0)
    )
    spread = (frame["ask"] - frame["bid"]) / mid.where(mid > 0, 1.0)
    liquid = liquid & (spread <= config.MAX_SPREAD_PCT)
    low, high = SELECTABLE_ABS_DELTA
    return (liquid & frame["delta"].abs().between(low, high)).astype(bool)


def _timestamps(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise SchwabQuoteAgeReportError(f"chain frame missing timestamp column: {column}")
    try:
        return pd.to_datetime(frame[column], utc=True)
    except (TypeError, ValueError) as exc:
        raise SchwabQuoteAgeReportError(f"{column} is not a UTC timestamp column") from exc


def _iso(value: object) -> str | None:
    stamp = value if isinstance(value, pd.Timestamp) else None
    return None if stamp is None else stamp.isoformat()


def _minutes(value) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), 4)


def _population_stats(
    values: pd.Series,
    ages: pd.Series,
    population_size: int,
    session_date: date,
) -> dict:
    """Stats over one (column, population) pair; `values`/`ages` are non-null."""
    stats: dict[str, object] = {
        "row_count": int(population_size),
        "null_count": int(population_size - len(values)),
        "min_utc": None,
        "max_utc": None,
        "prior_session_rows": 0,
        "after_session_rows": 0,
        "age_minutes": {"p50": None, "p90": None, "max": None},
    }
    if values.empty:
        return stats
    ny_dates = values.dt.tz_convert(NY_TZ).dt.date
    stats["min_utc"] = _iso(values.min())
    stats["max_utc"] = _iso(values.max())
    stats["prior_session_rows"] = int((ny_dates < session_date).sum())
    stats["after_session_rows"] = int((ny_dates > session_date).sum())
    if not ages.empty:
        stats["age_minutes"] = {
            "p50": _minutes(ages.quantile(0.5)),
            "p90": _minutes(ages.quantile(0.9)),
            "max": _minutes(ages.max()),
        }
    return stats


def _column_populations(
    frame: pd.DataFrame,
    column: str,
    mask: pd.Series,
) -> tuple[pd.Timestamp | None, dict[str, tuple[pd.Series, pd.Series, int]]]:
    """Return (age reference, {population: (values, ages, population_size)})."""
    stamps = _timestamps(frame, column)
    largest = stamps.max()
    reference = largest if isinstance(largest, pd.Timestamp) else None
    populations: dict[str, tuple[pd.Series, pd.Series, int]] = {}
    for population, selector in (("all_rows", None), ("selectable", mask)):
        subset = stamps if selector is None else cast(pd.Series, stamps[selector])
        size = len(stamps) if selector is None else int(selector.sum())
        present = subset.dropna()
        if reference is None or present.empty:
            ages = pd.Series(dtype="float64")
        else:
            ages = (reference - present).dt.total_seconds() / 60.0
        populations[population] = (present, ages, size)
    return reference, populations


def summarize_package(session: str, frames: Mapping[str, pd.DataFrame]) -> dict:
    """Per-symbol and package-wide quote-age statistics. Pure; no I/O."""
    session_date = date.fromisoformat(session)
    if not frames:
        raise SchwabQuoteAgeReportError("quote-age report needs at least one chain frame")

    symbols_out: dict[str, dict] = {}
    pooled: dict[str, dict[str, list]] = {
        column: {population: [] for population in POPULATIONS} for column in TIMESTAMP_COLUMNS
    }
    pooled_sizes: dict[str, dict[str, int]] = {
        column: {population: 0 for population in POPULATIONS} for column in TIMESTAMP_COLUMNS
    }
    package_rows = 0
    package_selectable = 0
    max_as_of: date | None = None

    for symbol in sorted(frames):
        frame = frames[symbol]
        mask = selectable_mask(frame)
        package_rows += len(frame)
        package_selectable += int(mask.sum())
        columns_out: dict[str, dict[str, object]] = {}
        for column in TIMESTAMP_COLUMNS:
            reference, populations = _column_populations(frame, column, mask)
            column_out: dict[str, object] = {"age_reference_utc": _iso(reference)}
            columns_out[column] = column_out
            for population, (values, ages, size) in populations.items():
                column_out[population] = _population_stats(values, ages, size, session_date)
                pooled[column][population].append((values, ages))
                pooled_sizes[column][population] += size
            if column == "timestamp" and reference is not None:
                observed = reference.tz_convert(NY_TZ).date()
                max_as_of = observed if max_as_of is None else max(max_as_of, observed)
        symbols_out[symbol] = {
            "row_count": int(len(frame)),
            "selectable_row_count": int(mask.sum()),
            "columns": columns_out,
        }

    package_columns: dict[str, dict] = {}
    for column in TIMESTAMP_COLUMNS:
        package_columns[column] = {}
        for population in POPULATIONS:
            parts = pooled[column][population]
            values = cast(pd.Series, pd.concat([part[0] for part in parts], ignore_index=True))
            ages = cast(pd.Series, pd.concat([part[1] for part in parts], ignore_index=True))
            package_columns[column][population] = _population_stats(
                values, ages, pooled_sizes[column][population], session_date
            )

    return {
        "symbols": symbols_out,
        "package": {
            "symbol_count": len(frames),
            "row_count": int(package_rows),
            "selectable_row_count": int(package_selectable),
            "columns": package_columns,
        },
        "max_as_of_session": (max_as_of or session_date).isoformat(),
    }


def build_report(
    *,
    session: str,
    symbols: Sequence[str],
    chain_dir: Path,
    manifest_hash: str | None = None,
) -> dict:
    """Read the session's chain parquet and build the descriptive report."""
    names = sorted(str(symbol) for symbol in symbols)
    if not names:
        raise SchwabQuoteAgeReportError("quote-age report needs a non-empty universe")
    chain_dir = Path(chain_dir)
    frames = {
        symbol: pd.read_parquet(chain_dir / f"{symbol}_{session}.parquet") for symbol in names
    }
    summary = summarize_package(session, frames)
    return {
        "schema_version": SCHEMA_VERSION,
        "session": session,
        "symbols_requested": names,
        "manifest_hash": manifest_hash,
        "display_only": True,
        "verdict_eligible": False,
        "semantics": SEMANTICS,
        "age_reference": (
            "per-symbol maximum of the same timestamp column over ALL rows of "
            "that symbol's chain file"
        ),
        "selectable_definition": {
            "description": (
                "generic liquidity gate plus |delta| band, mirroring "
                "data/recent_topup.py's default audit mask; a descriptive proxy, "
                "not any registered lane's exact selection rule"
            ),
            "min_open_interest": config.MIN_OPEN_INTEREST,
            "max_spread_pct": config.MAX_SPREAD_PCT,
            "abs_delta_band": list(SELECTABLE_ABS_DELTA),
        },
        **summary,
    }


def report_text(report: Mapping[str, object]) -> str:
    """Canonical on-disk bytes for a report dict."""
    return json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_quote_age_report(
    *,
    session: str,
    symbols: Sequence[str],
    chain_dir: Path,
    reports_dir: Path,
    receipt_filename: str,
    manifest_hash: str | None = None,
) -> Path:
    """Build and durably write the sidecar; refuse a differing rewrite.

    An identical rewrite is a no-op (the report is deterministic, so a rerun of
    the same immutable package reproduces the same bytes). Differing bytes raise
    rather than clobber a data-tier artifact.
    """
    path = sidecar_path(reports_dir, session, receipt_filename)
    report = build_report(
        session=session,
        symbols=symbols,
        chain_dir=chain_dir,
        manifest_hash=manifest_hash,
    )
    text = report_text(report)
    if path.exists():
        if path.read_text() == text:
            return path
        raise FileExistsError(f"quote-age report conflict; refusing overwrite: {path}")
    atomic_text_write(text, path)
    return path

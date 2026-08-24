"""Descriptive, cache-only context for the frozen fill haircut.

This module deliberately lives under ``tools`` because the repository's
diagnostic identity includes that namespace.  It reads the two approved cache
namespaces, performs no acquisition, and writes only a dated report and an
immutable receipt when invoked as a command.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

import config
from data import underlying_closes
from research.receipts import make_receipt, write_immutable_receipt

REPO_ROOT = Path(__file__).resolve().parents[1]
TIER1_ROOT = REPO_ROOT / ".cache" / "schwab_chains"
TIER2_ROOT = REPO_ROOT / ".cache" / "chains_v2" / "od1-2026-08-01"
QUARANTINE_PATH = REPO_ROOT / "data" / "v2_partition_quarantine.json"
AUDIT_PATH = TIER2_ROOT / "_meta" / "full_audit.json"
DEFAULT_REPORT = (
    REPO_ROOT / "reports" / "fill_calibration" / ("2026-08-24-fill-adversity-context.md")
)
NY = ZoneInfo("America/New_York")
TIER2_RULING = (
    "Owner ruling 2026-08-24: Tier-2 chains_v2 read-only access is approved "
    "for this descriptive study; the namespace remains parked and excluded "
    "from verdict eligibility."
)

DTE_BANDS = (
    (0, 7, "0-7"),
    (8, 30, "8-30"),
    (31, 60, "31-60"),
    (61, 120, "61-120"),
    (121, math.inf, "121+"),
)
DELTA_BANDS = (
    (0.0, 0.15, "0-0.15"),
    (0.15, 0.35, "0.15-0.35"),
    (0.35, 0.65, "0.35-0.65"),
    (0.65, 1.0, "0.65-1.0"),
)
MIN_BUCKET_OBS = 200
SUCCESS_FACTOR = 2.0
FILE_RE = re.compile(r"^(?P<symbol>[A-Za-z0-9]+)_(?P<session>\d{4}-\d{2}-\d{2})\.parquet$")
KEY_COLUMNS = ["symbol", "expiration", "strike", "right"]


@dataclass
class TieredData:
    """Admitted rows and provenance counters for one cache tier."""

    tier: str
    frames: dict[tuple[str, str], pd.DataFrame] = field(default_factory=dict)
    raw_frames: dict[tuple[str, str], pd.DataFrame] = field(default_factory=dict)
    raw_keys: dict[tuple[str, str], set[tuple[str, str, float, str]]] = field(default_factory=dict)
    stage_counts: dict[tuple[str, str], dict] = field(default_factory=dict)
    input_files: list[str] = field(default_factory=list)
    quarantined: list[tuple[str, str]] = field(default_factory=list)
    warning_counts: dict[str, int] = field(default_factory=dict)
    warning_profile_available: bool = False
    missing_close_sessions: list[tuple[str, str]] = field(default_factory=list)

    @property
    def sessions(self) -> list[str]:
        return sorted({session for _symbol, session in self.frames})

    @property
    def max_session(self) -> str | None:
        values = self.sessions
        return values[-1] if values else None


def _tier_name(tier: str | int) -> str:
    value = str(tier).lower().replace(" ", "")
    if value in {"1", "tier1"}:
        return "Tier 1"
    if value in {"2", "tier2"}:
        return "Tier 2"
    raise ValueError(f"unknown cache tier {tier!r}")


def _parse_path(path: Path) -> tuple[str, str] | None:
    match = FILE_RE.match(path.name)
    if match is None:
        return None
    return match.group("symbol").upper(), match.group("session")


def _load_quarantine(path: Path) -> set[tuple[str, str]]:
    if not Path(path).is_file():
        return set()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "v2-partition-quarantine/v1":
        raise ValueError(f"invalid v2 quarantine registry: {path}")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"invalid v2 quarantine entries: {path}")
    result = set()
    for entry in entries:
        if (
            isinstance(entry, dict)
            and isinstance(entry.get("symbol"), str)
            and isinstance(entry.get("session"), str)
        ):
            result.add((entry["symbol"].upper(), entry["session"]))
    return result


def _warning_profile(path: Path, sessions: Iterable[str]) -> tuple[dict[str, int], bool]:
    counts = {session: 0 for session in sessions}
    if not Path(path).is_file():
        return counts, False
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
    if not isinstance(warnings, list):
        raise ValueError(f"invalid v2 warning profile: {path}")
    for item in warnings:
        if isinstance(item, dict) and isinstance(item.get("session"), str):
            session = item["session"]
            if session in counts:
                counts[session] += 1
    return counts, True


def _liquid_mask(frame: pd.DataFrame) -> pd.Series:
    bid = pd.to_numeric(frame["bid"], errors="coerce")
    ask = pd.to_numeric(frame["ask"], errors="coerce")
    oi = pd.to_numeric(frame["open_interest"], errors="coerce")
    mid = (bid + ask) / 2.0
    spread = (ask - bid) / mid.where(mid > 0, np.nan)
    return (
        bid.ge(0)
        & ask.gt(0)
        & ask.ge(bid)
        & oi.ge(config.MIN_OPEN_INTEREST)
        & mid.gt(0)
        & spread.le(config.MAX_SPREAD_PCT)
    ).fillna(False)


def _timestamp_in_session(frame: pd.DataFrame, session: str) -> pd.Series:
    timestamp = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
    local = timestamp.dt.tz_convert(NY)
    minute = local.dt.hour * 60 + local.dt.minute + local.dt.second / 60.0
    return (
        local.dt.strftime("%Y-%m-%d").eq(session) & minute.ge(9 * 60 + 30) & minute.le(16 * 60 + 15)
    ).fillna(False)


def prepare_frame(
    frame: pd.DataFrame, session: str, *, tier: str | int
) -> tuple[pd.DataFrame, dict]:
    """Apply validity, liquidity, and (for Tier 2) timestamp admission."""
    tier_name = _tier_name(tier)
    out = frame.copy()
    out.columns = [str(column).strip().lower() for column in out.columns]
    out["session"] = session
    if "symbol" not in out:
        out["symbol"] = "UNKNOWN"
    out["symbol"] = out["symbol"].astype(str).str.upper()
    required = {"expiration", "strike", "right", "bid", "ask", "open_interest", "delta"}
    missing = sorted(required.difference(out.columns))
    if missing:
        raise ValueError(f"{tier_name} {session}: missing columns {missing}")
    for column in ("bid", "ask", "open_interest", "delta", "strike"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    valid = (
        out["bid"].notna()
        & out["ask"].notna()
        & out["bid"].ge(0)
        & out["ask"].gt(0)
        & out["ask"].ge(out["bid"])
    )
    validity_dropped = int((~valid).sum())
    valid_frame = out.loc[valid].copy()
    liquid = _liquid_mask(valid_frame)
    liquidity_dropped = int((~liquid).sum())
    admitted = valid_frame.loc[liquid].copy()
    pre_stale = len(admitted)
    staleness_dropped = 0
    if tier_name == "Tier 2":
        if "timestamp" not in admitted:
            raise ValueError(f"Tier 2 {session}: timestamp column is required")
        fresh = _timestamp_in_session(admitted, session)
        staleness_dropped = int((~fresh).sum())
        admitted = admitted.loc[fresh].copy()
    excluded = bool(pre_stale and staleness_dropped / pre_stale > 0.5)
    stats = {
        "raw_rows": int(len(out)),
        "validity_dropped": validity_dropped,
        "liquidity_dropped": liquidity_dropped,
        "pre_staleness_rows": pre_stale,
        "staleness_dropped": staleness_dropped,
        "admitted_rows": int(len(admitted)),
        "excluded_from_drift": excluded,
        "missing_close": False,
        "missing_close_dropped": 0,
    }
    admitted["tier"] = tier_name
    admitted["mid"] = (admitted["bid"] + admitted["ask"]) / 2.0
    return admitted.reset_index(drop=True), stats


def attach_tier1_spots(
    frames: dict[tuple[str, str], pd.DataFrame],
) -> tuple[dict[tuple[str, str], pd.DataFrame], list[tuple[str, str]]]:
    """Attach raw closes; adjusted closes are intentionally never consulted."""
    missing: list[tuple[str, str]] = []
    for key, frame in frames.items():
        symbol, session = key
        value: float | None = None
        try:
            closes = underlying_closes.load_closes(symbol, session, session, allow_oos=True)
            if len(closes):
                value = float(closes.iloc[-1])
        except (FileNotFoundError, KeyError, OSError, ValueError):
            value = None
        frame["spot"] = value
        frame["close_available"] = value is not None and math.isfinite(value)
        if value is None or not math.isfinite(value):
            missing.append(key)
    return frames, missing


def load_tier(
    tier: str | int,
    *,
    allow_parked_chains_v2: bool = False,
    tier1_dir: Path = TIER1_ROOT,
    tier2_dir: Path = TIER2_ROOT,
    quarantine_path: Path = QUARANTINE_PATH,
    audit_path: Path = AUDIT_PATH,
) -> TieredData:
    tier_name = _tier_name(tier)
    if tier_name == "Tier 2" and not allow_parked_chains_v2:
        raise RuntimeError(
            "Tier-2 chains_v2 is parked and refused without "
            "--allow-parked-chains-v2; owner ruling 2026-08-24 permits read-only access only"
        )
    root = Path(tier1_dir if tier_name == "Tier 1" else tier2_dir)
    result = TieredData(tier_name)
    quarantine = _load_quarantine(Path(quarantine_path)) if tier_name == "Tier 2" else set()
    paths = sorted(path for path in root.glob("*.parquet") if _parse_path(path) is not None)
    for path in paths:
        parsed = _parse_path(path)
        if parsed is None:
            continue
        symbol, session = parsed
        key = (symbol, session)
        if key in quarantine:
            result.quarantined.append(key)
            continue
        raw = pd.read_parquet(path)
        raw.columns = [str(column).strip().lower() for column in raw.columns]
        raw["symbol"] = symbol
        raw["session"] = session
        admitted, stats = prepare_frame(raw, session, tier=tier_name)
        result.raw_keys[key] = _key_set(raw)
        # Keep only fields used by measurements.  In particular, retaining
        # the provider's full Greeks frame for every Tier-2 session would
        # multiply the read-only study's memory footprint without changing a
        # reported number.
        keep = [
            column
            for column in (
                "symbol",
                "session",
                "expiration",
                "strike",
                "right",
                "bid",
                "ask",
                "open_interest",
                "delta",
                "timestamp",
                "bid_size",
                "ask_size",
                "underlying_price",
                "mid",
                "tier",
                "spot",
                "close_available",
            )
            if column in admitted.columns
        ]
        result.frames[key] = admitted[keep].copy()
        result.stage_counts[key] = stats
        result.input_files.append(str(path))
    if tier_name == "Tier 1":
        result.frames, result.missing_close_sessions = attach_tier1_spots(result.frames)
        for key in result.missing_close_sessions:
            result.stage_counts[key]["missing_close"] = True
            result.stage_counts[key]["missing_close_dropped"] = int(len(result.frames[key]))
    if tier_name == "Tier 2":
        result.warning_counts, result.warning_profile_available = _warning_profile(
            Path(audit_path), result.sessions
        )
    return result


def _dte_value(expiration: object, session: object) -> float:
    try:
        return float(
            (pd.Timestamp(str(expiration)).date() - pd.Timestamp(str(session)).date()).days
        )
    except (TypeError, ValueError, OverflowError):
        return float("nan")


def _frame_dte(frame: pd.DataFrame) -> np.ndarray:
    expiration = pd.to_datetime(frame["expiration"], errors="coerce")
    session = pd.to_datetime(frame["session"], errors="coerce")
    return (expiration - session).dt.days.to_numpy(dtype=float)


def _dte_bucket(value: float) -> str:
    if not math.isfinite(value):
        return "OUT_OF_BAND"
    for lower, upper, label in DTE_BANDS:
        if lower <= value <= upper:
            return label
    return "OUT_OF_BAND"


def _delta_bucket(value: object) -> str:
    try:
        absolute = abs(float(value))
    except (TypeError, ValueError):
        return "OUT_OF_BAND"
    if not math.isfinite(absolute) or absolute > 1.0:
        return "OUT_OF_BAND"
    for index, (lower, upper, label) in enumerate(DELTA_BANDS):
        if lower <= absolute < upper or (index == len(DELTA_BANDS) - 1 and absolute <= upper):
            return label
    return "OUT_OF_BAND"


def assign_buckets(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "dte" not in out:
        out["dte"] = _frame_dte(out)
    dte_values = pd.to_numeric(out["dte"], errors="coerce").to_numpy(dtype=float)
    dte_labels = np.full(len(out), "OUT_OF_BAND", dtype=object)
    for lower, upper, label in DTE_BANDS:
        dte_labels[(dte_values >= lower) & (dte_values <= upper)] = label
    delta_values = pd.to_numeric(out["delta"], errors="coerce").abs().to_numpy(dtype=float)
    delta_labels = np.full(len(out), "OUT_OF_BAND", dtype=object)
    for index, (lower, upper, label) in enumerate(DELTA_BANDS):
        mask = (delta_values >= lower) & (delta_values < upper)
        if index == len(DELTA_BANDS) - 1:
            mask |= delta_values == upper
        delta_labels[mask] = label
    out["dte_bucket"] = dte_labels
    out["delta_bucket"] = delta_labels
    out["bucket"] = [
        f"DTE {dte}; abs-delta {delta}"
        for dte, delta in zip(out["dte_bucket"], out["delta_bucket"])
    ]
    return out


def _contract_keys(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["expiration"] = out["expiration"].astype(str)
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    out["right"] = out["right"].astype(str).str.upper().str[0]
    out["symbol"] = out["symbol"].astype(str).str.upper()
    return out.drop_duplicates(KEY_COLUMNS, keep="last")


def overnight_vectors(
    day: pd.DataFrame,
    next_day: pd.DataFrame,
    session: str,
    next_session: str,
) -> pd.DataFrame:
    """Match admitted contracts and compute absolute overnight mid movement."""
    left = _contract_keys(day).copy()
    right = _contract_keys(next_day).copy()
    keys = ["symbol", "expiration", "strike", "right"]
    right = right[keys + ["bid", "ask"]].rename(columns={"bid": "next_bid", "ask": "next_ask"})
    merged = left.merge(right, on=keys, how="inner", validate="one_to_one")
    if merged.empty:
        return pd.DataFrame(
            columns=[
                *keys,
                "session",
                "next_session",
                "mid",
                "next_mid",
                "delta_mid",
                "abs_delta_mid",
                "relative_abs_drift",
                "bucket",
            ]
        )
    merged["mid"] = (merged["bid"] + merged["ask"]) / 2.0
    merged["next_mid"] = (merged["next_bid"] + merged["next_ask"]) / 2.0
    merged["delta_mid"] = merged["next_mid"] - merged["mid"]
    merged["abs_delta_mid"] = merged["delta_mid"].abs()
    merged["relative_abs_drift"] = merged["abs_delta_mid"] / merged["mid"]
    merged["session"] = session
    merged["next_session"] = next_session
    return assign_buckets(merged)


def _calendar_pairs(sessions: Iterable[str]) -> set[tuple[str, str]]:
    values = sorted(set(sessions))
    if len(values) < 2:
        return set()
    schedule = mcal.get_calendar("XNYS").schedule(start_date=values[0], end_date=values[-1])
    dates = [stamp.date().isoformat() for stamp in schedule.index]
    return set(zip(dates, dates[1:]))


def _key_set(frame: pd.DataFrame) -> set[tuple[str, str, float, str]]:
    if frame.empty:
        return set()
    normalized = _contract_keys(frame)
    return {
        (str(row.symbol), str(row.expiration), float(row.strike), str(row.right))
        for row in normalized.itertuples()
    }


def _iter_overnight_vectors(
    data: TieredData,
) -> Iterable[tuple[pd.DataFrame, str, dict]]:
    sessions = _calendar_pairs(data.sessions)
    for symbol, session in sorted(data.frames):
        next_candidates = [next_session for left, next_session in sessions if left == session]
        if not next_candidates:
            continue
        next_session = next_candidates[0]
        left_key = (symbol, session)
        right_key = (symbol, next_session)
        left = data.frames[left_key]
        left_stats = data.stage_counts[left_key]
        right_stats = data.stage_counts.get(right_key)
        if left_stats.get("excluded_from_drift") or (
            right_stats and right_stats.get("excluded_from_drift")
        ):
            yield pd.DataFrame(), f"{symbol}@{session}->{next_session}", {"pair_excluded": True}
            continue
        right = data.frames.get(right_key)
        left_keys = _key_set(left)
        if right is None:
            yield (
                pd.DataFrame(),
                f"{symbol}@{session}->{next_session}",
                {
                    "day_admitted": len(left_keys),
                    "next_session_missing": len(left_keys),
                    "vanished": len(left_keys),
                    "next_not_admitted": 0,
                    "matched": 0,
                },
            )
            continue
        raw_right_keys = data.raw_keys.get(right_key)
        if raw_right_keys is None:
            raw_right_keys = _key_set(data.raw_frames.get(right_key, right))
        right_keys = _key_set(right)
        vanished = left_keys - raw_right_keys
        not_admitted = (left_keys & raw_right_keys) - right_keys
        vector = overnight_vectors(left, right, session, next_session)
        yield (
            vector,
            f"{symbol}@{session}->{next_session}",
            {
                "day_admitted": len(left_keys),
                "next_session_missing": 0,
                "vanished": len(vanished),
                "next_not_admitted": len(not_admitted),
                "matched": len(left_keys & right_keys),
            },
        )


def compute_overnight_drift(data: TieredData) -> tuple[pd.DataFrame, dict]:
    vectors: list[pd.DataFrame] = []
    stages: dict[str, dict] = {}
    for vector, stage_key, stage in _iter_overnight_vectors(data):
        if not vector.empty:
            vectors.append(vector)
        stages[stage_key] = stage
    combined = pd.concat(vectors, ignore_index=True) if vectors else pd.DataFrame()
    return combined, stages


def two_leg_vectors(
    day: pd.DataFrame,
    next_day: pd.DataFrame,
    session: str,
    next_session: str,
) -> pd.DataFrame:
    """Construct adjacent-strike put verticals and measure net-credit drift."""
    left = _contract_keys(day)
    right = _contract_keys(next_day)
    key_columns = ["symbol", "expiration", "strike", "right"]
    left_puts = (
        left.loc[left["right"] == "P"]
        .drop_duplicates(key_columns, keep="last")
        .sort_values(["symbol", "expiration", "strike"])
        .copy()
    )
    if left_puts.empty:
        return pd.DataFrame()

    # A grouped shift creates each adjacent-strike pair. Keyed merges retain
    # only pairs for which both legs are present in the next session.
    grouped = left_puts.groupby(["symbol", "expiration"], sort=False)
    left_puts["long_strike"] = grouped["strike"].shift(1)
    left_puts["long_bid"] = grouped["bid"].shift(1)
    left_puts["long_ask"] = grouped["ask"].shift(1)
    verticals = left_puts.loc[left_puts["long_strike"].notna()].rename(
        columns={"strike": "short_strike", "bid": "short_bid", "ask": "short_ask"}
    )
    right_puts = right.loc[right["right"] == "P"].drop_duplicates(key_columns, keep="last")
    short_next = right_puts.rename(
        columns={"strike": "short_strike", "bid": "next_short_bid", "ask": "next_short_ask"}
    )[["symbol", "expiration", "short_strike", "next_short_bid", "next_short_ask"]]
    long_next = right_puts.rename(
        columns={"strike": "long_strike", "bid": "next_long_bid", "ask": "next_long_ask"}
    )[["symbol", "expiration", "long_strike", "next_long_bid", "next_long_ask"]]
    verticals = verticals.merge(
        short_next,
        on=["symbol", "expiration", "short_strike"],
        how="inner",
        validate="many_to_one",
    ).merge(
        long_next,
        on=["symbol", "expiration", "long_strike"],
        how="inner",
        validate="many_to_one",
    )
    if verticals.empty:
        return pd.DataFrame()
    short_mid = (verticals["short_bid"] + verticals["short_ask"]) / 2.0
    long_mid = (verticals["long_bid"] + verticals["long_ask"]) / 2.0
    next_short_mid = (verticals["next_short_bid"] + verticals["next_short_ask"]) / 2.0
    next_long_mid = (verticals["next_long_bid"] + verticals["next_long_ask"]) / 2.0
    verticals["session"] = session
    verticals["next_session"] = next_session
    verticals["net_credit"] = short_mid - long_mid
    verticals["next_net_credit"] = next_short_mid - next_long_mid
    verticals["delta_net_credit"] = verticals["next_net_credit"] - verticals["net_credit"]
    verticals["abs_delta_net_credit"] = verticals["delta_net_credit"].abs()
    verticals["abs_leg_delta_mid_max"] = np.maximum(
        (next_short_mid - short_mid).abs(), (next_long_mid - long_mid).abs()
    )
    verticals["dte"] = (
        pd.to_datetime(verticals["expiration"], errors="coerce") - pd.Timestamp(session)
    ).dt.days
    verticals["delta"] = pd.to_numeric(verticals["delta"], errors="coerce")
    return assign_buckets(verticals)


def summarize_two_leg(vectors: pd.DataFrame) -> dict:
    if vectors.empty:
        return {
            "n": 0,
            "adverse_fraction": None,
            "p50": None,
            "p75": None,
            "p90": None,
            "p95": None,
            "p99": None,
            "by_bucket": {},
        }
    adverse = vectors["delta_net_credit"] < -config.A_ENTRY_CREDIT_TOLERANCE
    if "abs_delta_net_credit" not in vectors:
        vectors = vectors.copy()
        vectors["abs_delta_net_credit"] = vectors["delta_net_credit"].abs()
    values = vectors["abs_delta_net_credit"].astype(float)
    summary = {
        "n": int(len(vectors)),
        "adverse_fraction": float(adverse.mean()),
        "p50": float(np.percentile(values, 50)),
        "p75": float(np.percentile(values, 75)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "by_bucket": {},
    }
    for bucket, group in vectors.groupby("bucket", sort=True):
        numbers = group["abs_delta_net_credit"].astype(float)
        summary["by_bucket"][str(bucket)] = {
            "n": int(len(group)),
            "p50": float(np.percentile(numbers, 50)),
            "p75": float(np.percentile(numbers, 75)),
            "p90": float(np.percentile(numbers, 90)),
            "p95": float(np.percentile(numbers, 95)),
            "p99": float(np.percentile(numbers, 99)),
            "adverse_fraction": float(
                (group["delta_net_credit"] < -config.A_ENTRY_CREDIT_TOLERANCE).mean()
            ),
        }
    return summary


def decompose_quote(bid: float, ask: float) -> dict:
    """Average buy/sell model adversity and its three component shares."""
    bid = float(bid)
    ask = float(ask)
    half_spread = (ask - bid) / 2.0
    buy_ideal = ask * (1.0 + config.SLIPPAGE_HAIRCUT)
    sell_ideal = bid * (1.0 - config.SLIPPAGE_HAIRCUT)
    buy_round = math.ceil(buy_ideal * 100.0) / 100.0 - buy_ideal
    sell_round = sell_ideal - math.floor(sell_ideal * 100.0) / 100.0
    haircut = (ask * config.SLIPPAGE_HAIRCUT + bid * config.SLIPPAGE_HAIRCUT) / 2.0
    rounding = (buy_round + sell_round) / 2.0
    total = half_spread + haircut + rounding
    if total <= 0:
        return {
            "half_spread": 0.0,
            "haircut": 0.0,
            "cent_rounding": 0.0,
            "total": 0.0,
            "half_spread_share": 0.0,
            "haircut_share": 0.0,
            "cent_rounding_share": 0.0,
        }
    return {
        "half_spread": half_spread,
        "haircut": haircut,
        "cent_rounding": rounding,
        "total": total,
        "half_spread_share": half_spread / total,
        "haircut_share": haircut / total,
        "cent_rounding_share": rounding / total,
    }


def render_bucket_table(
    frame: pd.DataFrame, *, min_obs: int = MIN_BUCKET_OBS, value_column: str = "value"
) -> str:
    if frame.empty:
        return "| bucket | n | result |\n|---|---:|---|\n"
    working = frame if "bucket" in frame else assign_buckets(frame)
    lines = ["| bucket | n | result |", "|---|---:|---|"]
    for bucket, group in working.groupby("bucket", sort=True):
        n = len(group)
        if n < min_obs:
            result = f"INSUFFICIENT (n={n})"
        elif value_column in group:
            result = f"p50={float(np.percentile(group[value_column].astype(float), 50)):.6g}"
        else:
            result = f"n={n}"
        lines.append(f"| {bucket} | {n} | {result} |")
    return "\n".join(lines) + "\n"


def render_tier_tables(
    frame: pd.DataFrame, *, value_column: str, min_obs: int = MIN_BUCKET_OBS
) -> dict[str, str]:
    return {
        str(tier): render_bucket_table(group, value_column=value_column, min_obs=min_obs)
        for tier, group in frame.groupby("tier", sort=True)
    }


def _percentile_summary(frame: pd.DataFrame, value: str, min_obs: int) -> dict:
    if frame.empty:
        return {"n": 0, "buckets": {}}
    buckets = {}
    for bucket, group in frame.groupby("bucket", sort=True):
        values = pd.to_numeric(group[value], errors="coerce").dropna()
        item = {"n": int(len(values))}
        if len(values) >= min_obs:
            item.update({f"p{p}": float(np.percentile(values, p)) for p in (50, 75, 90, 95, 99)})
        else:
            item["insufficient"] = True
        buckets[str(bucket)] = item
    return {"n": int(len(frame)), "buckets": buckets}


def _up_down_split(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"up": 0, "down": 0, "flat": 0}
    delta = pd.to_numeric(frame["delta_mid"], errors="coerce")
    return {
        "up": int((delta > 0).sum()),
        "down": int((delta < 0).sum()),
        "flat": int((delta == 0).sum()),
    }


def _decomposition_summary(data: TieredData, min_obs: int) -> dict:
    values: dict[str, dict[str, list[np.ndarray]]] = {}
    row_count = 0
    out_of_band = 0
    for source in data.frames.values():
        frame = source
        if data.tier == "Tier 1" and "close_available" in frame:
            frame = frame.loc[frame["close_available"].fillna(False)]
        if frame.empty:
            continue
        bid = frame["bid"].astype(float)
        ask = frame["ask"].astype(float)
        half = ((ask - bid) / 2.0).to_numpy()
        haircut = (((ask + bid) / 2.0) * config.SLIPPAGE_HAIRCUT).to_numpy()
        buy_ideal = (ask * (1.0 + config.SLIPPAGE_HAIRCUT)).to_numpy()
        sell_ideal = (bid * (1.0 - config.SLIPPAGE_HAIRCUT)).to_numpy()
        rounding = (
            (np.ceil(buy_ideal * 100.0) / 100.0 - buy_ideal)
            + (sell_ideal - np.floor(sell_ideal * 100.0) / 100.0)
        ) / 2.0
        total = half + haircut + rounding
        dte = _frame_dte(frame)
        bucket_frame = assign_buckets(
            pd.DataFrame({"dte": dte, "delta": frame["delta"].to_numpy()})
        )
        row_count += len(bucket_frame)
        out_of_band += int((bucket_frame["delta_bucket"] == "OUT_OF_BAND").sum())
        for bucket, positions in bucket_frame.groupby("bucket", sort=True).groups.items():
            indices = np.asarray(list(positions), dtype=int)
            denominator = total[indices]
            bucket_values = values.setdefault(
                str(bucket), {"half": [], "haircut": [], "rounding": []}
            )
            bucket_values["half"].append(half[indices] / denominator)
            bucket_values["haircut"].append(haircut[indices] / denominator)
            bucket_values["rounding"].append(rounding[indices] / denominator)
    buckets: dict[str, dict] = {}
    for bucket, components in values.items():
        half_values = np.concatenate(components["half"])
        haircut_values = np.concatenate(components["haircut"])
        rounding_values = np.concatenate(components["rounding"])
        n = len(half_values)
        if n < min_obs:
            buckets[str(bucket)] = {"n": int(n), "insufficient": True}
            continue
        buckets[str(bucket)] = {
            "n": int(n),
            "half_spread_share_p50": float(np.percentile(half_values, 50)),
            "haircut_share_p50": float(np.percentile(haircut_values, 50)),
            "cent_rounding_share_p50": float(np.percentile(rounding_values, 50)),
        }
    lines = [
        "| bucket | n | half-spread share p50 | haircut share p50 | cent-rounding share p50 |",
        "|---|---:|---:|---:|---:|",
    ]
    for bucket, values in buckets.items():
        if values.get("insufficient"):
            lines.append(f"| {bucket} | {values['n']} | INSUFFICIENT (n={values['n']}) |  |  |")
        else:
            lines.append(
                f"| {bucket} | {values['n']} | {values['half_spread_share_p50']:.6g} | "
                f"{values['haircut_share_p50']:.6g} | {values['cent_rounding_share_p50']:.6g} |"
            )
    return {
        "n": int(row_count),
        "table": "\n".join(lines) + "\n",
        "buckets": buckets,
        "out_of_band": out_of_band,
    }


def _touch_depth_summary(data: TieredData, min_obs: int) -> dict:
    if data.tier != "Tier 2":
        return {"n": 0, "table": "Tier 1 has no touch-size fields; not applicable.\n"}
    bucket_spreads: dict[str, list[np.ndarray]] = {}
    bid_parts: list[np.ndarray] = []
    ask_parts: list[np.ndarray] = []
    spread_parts: list[np.ndarray] = []
    weight_parts: list[np.ndarray] = []
    row_count = 0
    for source in data.frames.values():
        frame = source
        if "bid_size" not in frame or "ask_size" not in frame:
            continue
        bid = frame["bid_size"].astype(float).to_numpy()
        ask = frame["ask_size"].astype(float).to_numpy()
        mid = (frame["ask"].astype(float) + frame["bid"].astype(float)) / 2.0
        spread = ((frame["ask"].astype(float) - frame["bid"].astype(float)) / mid).to_numpy()
        dte = _frame_dte(frame)
        bucket_frame = assign_buckets(
            pd.DataFrame({"dte": dte, "delta": frame["delta"].to_numpy()})
        )
        row_count += len(bucket_frame)
        bid_parts.append(bid)
        ask_parts.append(ask)
        spread_parts.append(spread)
        weight_parts.append(bid + ask)
        for bucket, positions in bucket_frame.groupby("bucket", sort=True).groups.items():
            indices = np.asarray(list(positions), dtype=int)
            bucket_spreads.setdefault(str(bucket), []).append(spread[indices])
    all_bid = np.concatenate(bid_parts) if bid_parts else np.array([], dtype=float)
    all_ask = np.concatenate(ask_parts) if ask_parts else np.array([], dtype=float)
    all_spread = np.concatenate(spread_parts) if spread_parts else np.array([], dtype=float)
    all_weights = np.concatenate(weight_parts) if weight_parts else np.array([], dtype=float)
    lines = ["| bucket | n | spread fraction p50 |", "|---|---:|---:|"]
    for bucket, parts in bucket_spreads.items():
        values = np.concatenate(parts)
        if len(values) < min_obs:
            lines.append(f"| {bucket} | {len(values)} | INSUFFICIENT (n={len(values)}) |")
        else:
            lines.append(f"| {bucket} | {len(values)} | {float(np.percentile(values, 50)):.6g} |")
    weighted = (
        float(np.average(all_spread, weights=all_weights))
        if len(all_spread) and float(all_weights.sum()) > 0
        else None
    )
    return {
        "n": row_count,
        "table": "\n".join(lines) + "\n",
        "bid_ge_one": float((all_bid >= 1).mean()) if len(all_bid) else None,
        "ask_ge_one": float((all_ask >= 1).mean()) if len(all_ask) else None,
        "size_weighted_mean_spread_fraction": weighted,
        "bid_size_p50": float(np.percentile(all_bid, 50)) if len(all_bid) else None,
        "bid_size_p90": float(np.percentile(all_bid, 90)) if len(all_bid) else None,
        "ask_size_p50": float(np.percentile(all_ask, 50)) if len(all_ask) else None,
        "ask_size_p90": float(np.percentile(all_ask, 90)) if len(all_ask) else None,
    }


def _stream_overnight_summary(data: TieredData, min_obs: int) -> dict:
    relative_by_bucket: dict[str, list[np.ndarray]] = {}
    abs_by_bucket: dict[str, list[np.ndarray]] = {}
    relative_by_symbol_dte: dict[tuple[str, str], list[np.ndarray]] = {}
    total = up = down = flat = out_of_band = 0
    survivorship: dict[str, dict] = {}
    for vector, stage_key, stage in _iter_overnight_vectors(data):
        survivorship[stage_key] = stage
        if vector.empty:
            continue
        total += len(vector)
        delta = vector["delta_mid"].to_numpy(dtype=float)
        up += int((delta > 0).sum())
        down += int((delta < 0).sum())
        flat += int((delta == 0).sum())
        out_of_band += int((vector["delta_bucket"] == "OUT_OF_BAND").sum())
        for bucket, positions in vector.groupby("bucket", sort=True).groups.items():
            indices = np.asarray(list(positions), dtype=int)
            relative_by_bucket.setdefault(str(bucket), []).append(
                vector["relative_abs_drift"].to_numpy(dtype=float)[indices]
            )
            abs_by_bucket.setdefault(str(bucket), []).append(
                vector["abs_delta_mid"].to_numpy(dtype=float)[indices]
            )
        for (symbol, dte_bucket), positions in vector.groupby(
            ["symbol", "dte_bucket"], sort=True
        ).groups.items():
            indices = np.asarray(list(positions), dtype=int)
            relative_by_symbol_dte.setdefault((str(symbol), str(dte_bucket)), []).append(
                vector["relative_abs_drift"].to_numpy(dtype=float)[indices]
            )
    buckets: dict[str, dict] = {}
    for bucket, parts in relative_by_bucket.items():
        values = np.concatenate(parts)
        item = {"n": int(len(values))}
        if len(values) >= min_obs:
            item.update({f"p{p}": float(np.percentile(values, p)) for p in (50, 75, 90, 95, 99)})
        else:
            item["insufficient"] = True
        buckets[bucket] = item
    all_relative = (
        np.concatenate([part for parts in relative_by_bucket.values() for part in parts])
        if relative_by_bucket
        else np.array([], dtype=float)
    )
    all_abs = (
        np.concatenate([part for parts in abs_by_bucket.values() for part in parts])
        if abs_by_bucket
        else np.array([], dtype=float)
    )
    symbol_dte: dict[str, dict] = {}
    for (symbol, dte_bucket), parts in relative_by_symbol_dte.items():
        values = np.concatenate(parts)
        item = {"n": int(len(values))}
        if len(values) >= min_obs:
            item.update({f"p{p}": float(np.percentile(values, p)) for p in (50, 75, 90, 95, 99)})
        else:
            item["insufficient"] = True
        symbol_dte[f"{symbol}; DTE {dte_bucket}"] = item
    return {
        "n": total,
        "summary": {"n": total, "buckets": buckets},
        "up_down_flat": {"up": up, "down": down, "flat": flat},
        "survivorship": survivorship,
        "by_symbol_dte": symbol_dte,
        "out_of_band": out_of_band,
        "relative_exceedance": float((all_relative > config.SLIPPAGE_HAIRCUT).mean())
        if len(all_relative)
        else None,
        "dollar_exceedance": float((all_abs > 0.01).mean()) if len(all_abs) else None,
    }


def _stream_two_leg_summary(data: TieredData, min_obs: int) -> dict:
    calendar_pairs = _calendar_pairs(data.sessions)
    abs_by_bucket: dict[str, list[np.ndarray]] = {}
    delta_by_bucket: dict[str, list[np.ndarray]] = {}
    total = adverse = 0
    for (symbol, session), frame in sorted(data.frames.items()):
        if data.stage_counts[(symbol, session)].get("excluded_from_drift"):
            continue
        next_sessions = [right for left, right in calendar_pairs if left == session]
        if not next_sessions:
            continue
        next_session = next_sessions[0]
        next_stats = data.stage_counts.get((symbol, next_session))
        if next_stats and next_stats.get("excluded_from_drift"):
            continue
        next_frame = data.frames.get((symbol, next_session))
        if next_frame is None:
            continue
        vectors = two_leg_vectors(frame, next_frame, session, next_session)
        if vectors.empty:
            continue
        total += len(vectors)
        delta = vectors["delta_net_credit"].to_numpy(dtype=float)
        adverse += int((delta < -config.A_ENTRY_CREDIT_TOLERANCE).sum())
        for bucket, positions in vectors.groupby("bucket", sort=True).groups.items():
            indices = np.asarray(list(positions), dtype=int)
            abs_by_bucket.setdefault(str(bucket), []).append(
                vectors["abs_delta_net_credit"].to_numpy(dtype=float)[indices]
            )
            delta_by_bucket.setdefault(str(bucket), []).append(delta[indices])
    all_abs = (
        np.concatenate([part for parts in abs_by_bucket.values() for part in parts])
        if abs_by_bucket
        else np.array([], dtype=float)
    )
    buckets: dict[str, dict] = {}
    lines = [
        "| bucket | n | p50 | p75 | p90 | p95 | p99 | adverse fraction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for bucket, parts in abs_by_bucket.items():
        values = np.concatenate(parts)
        adverse_values = np.concatenate(delta_by_bucket[bucket])
        item = {"n": int(len(values))}
        if len(values) >= min_obs:
            item.update({f"p{p}": float(np.percentile(values, p)) for p in (50, 75, 90, 95, 99)})
            item["adverse_fraction"] = float(
                (adverse_values < -config.A_ENTRY_CREDIT_TOLERANCE).mean()
            )
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                    bucket,
                    len(values),
                    *[f"{item[f'p{p}']:.6g}" for p in (50, 75, 90, 95, 99)],
                    f"{item['adverse_fraction']:.6g}",
                )
            )
        else:
            item["insufficient"] = True
            lines.append(
                f"| {bucket} | {len(values)} | INSUFFICIENT (n={len(values)}) |  |  |  |  |  |"
            )
        buckets[bucket] = item
    return {
        "n": total,
        "adverse_fraction": float(adverse / total) if total else None,
        "p50": float(np.percentile(all_abs, 50)) if len(all_abs) else None,
        "p75": float(np.percentile(all_abs, 75)) if len(all_abs) else None,
        "p90": float(np.percentile(all_abs, 90)) if len(all_abs) else None,
        "p95": float(np.percentile(all_abs, 95)) if len(all_abs) else None,
        "p99": float(np.percentile(all_abs, 99)) if len(all_abs) else None,
        "by_bucket": buckets,
        "table": "\n".join(lines) + "\n",
        "vectors": pd.DataFrame(),
    }


def _tier_measurements(data: TieredData, min_obs: int) -> dict:
    drift = _stream_overnight_summary(data, min_obs)
    decomposition = _decomposition_summary(data, min_obs)
    two_leg = _stream_two_leg_summary(data, min_obs)
    return {
        "decomposition": decomposition,
        "drift": {
            **drift,
            "vectors": pd.DataFrame(),
        },
        "two_leg": two_leg,
        "touch_depth": _touch_depth_summary(data, min_obs),
    }


def _json_safe(value):
    if isinstance(value, pd.DataFrame):
        return [_json_safe(item) for item in value.to_dict("records")]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items() if key != "vectors"}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _success_finding(measurements: dict[str, dict], min_obs: int) -> str:
    qualifying: list[float] = []
    for item in measurements.values():
        for bucket in item["drift"]["summary"]["buckets"].values():
            if bucket.get("n", 0) >= min_obs and "p50" in bucket:
                qualifying.append(float(bucket["p50"]))
    if not qualifying:
        return (
            "No pooled overnight-drift bucket met the observation floor, so this run is "
            "insufficient for the declared 2x scale comparison."
        )
    if any(
        value > config.SLIPPAGE_HAIRCUT * SUCCESS_FACTOR
        or value < config.SLIPPAGE_HAIRCUT / SUCCESS_FACTOR
        for value in qualifying
    ):
        return "At least one qualifying bucket is out of scale with the frozen haircut under the declared 2x order-of-magnitude comparison; this is input to a possible future owner amendment."
    return "Every qualifying bucket is within 2x of the frozen haircut, so the constant is the right order of magnitude and no follow-up is warranted by this study."


def _table_with_stamp(table: str, max_session: str | None, n: int) -> str:
    return f"Max as-of session: {max_session or 'none'}; n={n}.\n\n{table}"


def _symbol_dte_appendix(data: dict) -> str:
    lines = [
        f"### {data.get('label', 'Tier')}\n",
        f"Max as-of session: {data.get('max_asof', 'none')}; symbol breakdown is appendix-only.\n",
        "| symbol / DTE band | n | p50 | p75 | p90 | p95 | p99 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    entries = data.get("by_symbol_dte", {})
    if not entries:
        lines.append("| none | 0 | unavailable |  |  |  |  |")
    for key, values in sorted(entries.items()):
        if values.get("insufficient"):
            lines.append(f"| {key} | {values['n']} | INSUFFICIENT (n={values['n']}) |  |  |  |  |")
        else:
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} |".format(
                    key,
                    values["n"],
                    *[f"{values[f'p{p}']:.6g}" for p in (50, 75, 90, 95, 99)],
                )
            )
    return "\n".join(lines) + "\n"


def render_report(payload: dict) -> str:
    """Render the dated report; exceedance fractions are appendix-only."""
    max_asof = payload.get("max_asof", "unknown")
    tier1 = payload.get("tier1", {})
    tier2 = payload.get("tier2", {})
    tier1_headline = tier1.get("headline", "INSUFFICIENT")
    tier2_headline = tier2.get("headline", "INSUFFICIENT")
    tier1_exceedance = tier1.get("exceedance", "unavailable")
    tier2_exceedance = tier2.get("exceedance", "unavailable")
    return f"""# Fill-adversity context study

Max as-of session: {max_asof}.

## Scope and honesty statement

The frozen model charges the quoted half-spread, the configured 1% adverse haircut, and cent rounding. No execution records are present on disk, so the 1% haircut cannot be compared with realized fills. Comparing it with each contract's own quoted spread would be circular because the model already charges that spread. This study describes the model's decomposition and compares the haircut with an independent overnight mid movement; it calibrates nothing.

The overnight movement is absolute rather than directional: a bare chain has no declared position side. Up, down, and flat counts are printed beside each drift table. The drift sample contains contracts admitted at D that remained quoted and fresh at D+1. Contracts that vanish or fail the next-session admission screen drop out. Dropping never-quoted rows removes near-zero movement and can bias drift up, while requiring D+1 presence keeps liquid survivors and can bias it down; the net direction is not determined.

## Decision finding

{payload.get("finding", "No finding was supplied.")}

## Measurement 1 — model decomposition

### Tier 1

{tier1.get("decomposition_table", tier1_headline)}

### Tier 2

{tier2.get("decomposition_table", tier2_headline)}

## Measurement 2 — absolute overnight mid drift

### Tier 1

{tier1.get("drift_table", "INSUFFICIENT")}

Up/down/flat: {tier1.get("up_down_flat", "unavailable")}. The frozen haircut is shown within the percentile scale above; this is a scale comparison, not fill evidence.

### Tier 2

{tier2.get("drift_table", "INSUFFICIENT")}

Up/down/flat: {tier2.get("up_down_flat", "unavailable")}. The frozen haircut is shown within the percentile scale above; this is a scale comparison, not fill evidence.

## Measurement 3 — two-leg net-credit drift (Strategy-A analogue)

{payload.get("two_leg_text", "No two-leg table was supplied.")}

The one-sided adverse fraction below uses the configured `A_ENTRY_CREDIT_TOLERANCE` direction and threshold. seq-21's tolerance governs future Strategy A put-credit-spread backtests only (`ledger/experiments.jsonl:22`); the chains measured here are the H7 story-name universe, which seq 21 excludes. This is an analogue computed on a stated spread construction, not a compliance measurement.

## Measurement 4 — touch depth (Tier 2 context)

{payload.get("touch_text", "Tier 1 has no touch-size fields; not applicable.")}

Quoted size is not fill evidence; it bounds 1-lot plausibility only. {TIER2_RULING}

## Data quality and source lineage

Tier-2 staleness filtering keeps timestamps on the row's session date between 09:30 and 16:15 ET. Rows dropped at each stage and sessions losing more than half their admitted rows are listed in the receipt. The Tier-2 full-audit warning profile is consumed and warning counts are recorded per used session. Missing Tier-1 raw closes exclude the affected session from moneyness tables; no interpolation is performed.

## What this is not

This is not fill evidence, not a recommendation, not a re-scoring of any registered result, and not applicable to any registered result. It does not change the frozen fill model, a strategy, a score, a ledger, authority, the paper book, or an order path.

## Appendix

Symbol breakdowns are appendix-only and use the same floor and absolute
overnight-drift definition; headline tables remain pooled across symbols.

{payload.get("symbol_appendix", "No symbol appendix was supplied.")}

Exceedance fractions are appendix-only and must not be read as headline findings. They are saturated in the available dollar-priced option data: a one-cent dollar threshold is often one tick, so its fraction is a tick-size artifact. Tier 1 `|Δmid|/mid > haircut`: {tier1_exceedance}. Tier 2 `|Δmid|/mid > haircut`: {tier2_exceedance}. Tier 1 `|Δmid| > $0.01`: {tier1.get("dollar_exceedance", "unavailable")}; Tier 2 `|Δmid| > $0.01`: {tier2.get("dollar_exceedance", "unavailable")}.

Receipt hash: {payload.get("receipt_hash", "unavailable")}.
"""


def _headline_from_measurement(item: dict, haircut: float) -> str:
    buckets = item["drift"]["summary"]["buckets"]
    lines = ["| bucket | n | p50 | p75 | p90 | p95 | p99 |", "|---|---:|---:|---:|---:|---:|---:|"]
    for bucket, values in buckets.items():
        if values.get("insufficient"):
            lines.append(
                f"| {bucket} | {values['n']} | INSUFFICIENT (n={values['n']}) |  |  |  |  |"
            )
        else:
            lines.append(
                "| {} | {} | {} | {} | {} | {} | {} |".format(
                    bucket, values["n"], *[f"{values[f'p{p}']:.6g}" for p in (50, 75, 90, 95, 99)]
                )
            )
    lines.append(f"\nHaircut reference: {haircut:.6g}.")
    return "\n".join(lines)


def run_study(
    *,
    include_tier2: bool = False,
    allow_parked_chains_v2: bool = False,
    min_bucket_obs: int = MIN_BUCKET_OBS,
    tier1_dir: Path = TIER1_ROOT,
    tier2_dir: Path = TIER2_ROOT,
    quarantine_path: Path = QUARANTINE_PATH,
    audit_path: Path = AUDIT_PATH,
) -> tuple[dict, dict]:
    if include_tier2 and not allow_parked_chains_v2:
        raise RuntimeError("Tier 2 requires --allow-parked-chains-v2")
    data = {
        "Tier 1": load_tier(
            "Tier 1", tier1_dir=tier1_dir, quarantine_path=quarantine_path, audit_path=audit_path
        )
    }
    if include_tier2:
        data["Tier 2"] = load_tier(
            "Tier 2",
            allow_parked_chains_v2=True,
            tier2_dir=tier2_dir,
            quarantine_path=quarantine_path,
            audit_path=audit_path,
        )
    measurements = {tier: _tier_measurements(item, min_bucket_obs) for tier, item in data.items()}
    max_sessions = [item.max_session for item in data.values() if item.max_session]
    max_asof = max(max_sessions) if max_sessions else None
    payload = {
        "max_asof": max_asof,
        "finding": _success_finding(measurements, min_bucket_obs),
        "tiers": list(data),
        "study_parameters": {
            "dte_bands": DTE_BANDS,
            "delta_bands": DELTA_BANDS,
            "min_bucket_obs": min_bucket_obs,
            "success_factor": SUCCESS_FACTOR,
            "slippage_haircut": config.SLIPPAGE_HAIRCUT,
            "execution_convention": config.BACKTEST_EXECUTION_CONVENTION,
        },
        "input_inventory": {
            tier: {
                "files": len(item.input_files),
                "sessions": len(item.sessions),
                "rows_admitted": sum(
                    int(stats["admitted_rows"]) for stats in item.stage_counts.values()
                ),
                "quarantine_exclusions": len(item.quarantined),
            }
            for tier, item in data.items()
        },
        "source_paths": {
            "tier1_dir": str(tier1_dir),
            "tier2_dir": str(tier2_dir) if include_tier2 else None,
            "quarantine_path": str(quarantine_path) if include_tier2 else None,
            "audit_path": str(audit_path) if include_tier2 else None,
        },
        "stage_counts": {
            tier: {
                f"{symbol}@{session}": stats
                for (symbol, session), stats in item.stage_counts.items()
            }
            for tier, item in data.items()
        },
        "warning_profile_counts": {tier: item.warning_counts for tier, item in data.items()},
        "warning_profile_available": {
            tier: item.warning_profile_available for tier, item in data.items()
        },
        "quarantined_partitions": {tier: item.quarantined for tier, item in data.items()},
        "missing_close_sessions": {
            tier: item.missing_close_sessions for tier, item in data.items()
        },
        "excluded_sessions": {
            tier: [
                f"{symbol}@{session}"
                for (symbol, session), stats in item.stage_counts.items()
                if stats.get("excluded_from_drift")
            ]
            for tier, item in data.items()
        },
        "out_of_band_counts": {tier: measurements[tier]["drift"]["out_of_band"] for tier in data},
        "numeric_tables": {
            tier: {
                "decomposition": measurements[tier]["decomposition"]["buckets"],
                "overnight_mid_drift": measurements[tier]["drift"]["summary"],
                "two_leg_net_credit_drift": measurements[tier]["two_leg"]["by_bucket"],
                "touch_depth": {
                    key: value
                    for key, value in measurements[tier]["touch_depth"].items()
                    if key != "table"
                },
            }
            for tier in data
        },
        "measurements": measurements,
        "git_sha": _git_sha(),
    }
    receipt = make_receipt("fill_adversity_context", _json_safe(payload))
    report_payload = _report_payload(data, measurements, receipt)
    return report_payload, receipt


def _report_payload(data: dict[str, TieredData], measurements: dict, receipt: dict) -> dict:
    result = {
        "max_asof": max(item.max_session for item in data.values() if item.max_session),
        "receipt_hash": receipt["receipt_hash"],
        "finding": _success_finding(
            measurements, int(receipt["study_parameters"]["min_bucket_obs"])
        ),
    }
    for tier, item in data.items():
        measure = measurements[tier]
        drift = measure["drift"]
        result[tier.lower().replace(" ", "")] = {
            "headline": _headline_from_measurement(measure, config.SLIPPAGE_HAIRCUT),
            "decomposition_table": _table_with_stamp(
                measure["decomposition"]["table"],
                item.max_session,
                measure["decomposition"]["n"],
            ),
            "drift_table": _table_with_stamp(
                _headline_from_measurement(measure, config.SLIPPAGE_HAIRCUT),
                item.max_session,
                drift["n"],
            ),
            "up_down_flat": drift["up_down_flat"],
            "by_symbol_dte": drift.get("by_symbol_dte", {}),
            "exceedance": f"{drift['relative_exceedance']:.1%}"
            if drift["relative_exceedance"] is not None
            else "unavailable",
            "dollar_exceedance": f"{drift['dollar_exceedance']:.1%}"
            if drift["dollar_exceedance"] is not None
            else "unavailable",
        }
    two_leg_lines = []
    touch_lines = []
    for tier, measure in measurements.items():
        two_leg_lines.append(
            f"### {tier}\n\nMax as-of session: {data[tier].max_session}; n={measure['two_leg']['n']}. One-sided adverse fraction using `A_ENTRY_CREDIT_TOLERANCE`: {measure['two_leg']['adverse_fraction'] if measure['two_leg']['n'] else 'unavailable'}.\n"
        )
        two_leg_lines.append(measure["two_leg"].get("table", "INSUFFICIENT\n"))
        depth = measure["touch_depth"]
        touch_lines.append(
            f"### {tier}\n\nMax as-of session: {data[tier].max_session}; n={depth['n']}. "
            f"bid_size p50/p90={depth.get('bid_size_p50', 'unavailable')}/{depth.get('bid_size_p90', 'unavailable')}; "
            f"ask_size p50/p90={depth.get('ask_size_p50', 'unavailable')}/{depth.get('ask_size_p90', 'unavailable')}; "
            f"fraction bid_size >= 1={depth.get('bid_ge_one', 'unavailable')}; "
            f"fraction ask_size >= 1={depth.get('ask_ge_one', 'unavailable')}; "
            f"size-weighted mean spread fraction={depth.get('size_weighted_mean_spread_fraction', 'unavailable')}.\n\n"
            f"{depth['table']}"
        )
    result["two_leg_text"] = "\n".join(two_leg_lines)
    result["touch_text"] = "\n".join(touch_lines)
    result["symbol_appendix"] = "\n".join(
        _symbol_dte_appendix(
            {
                "label": tier,
                "max_asof": data[tier].max_session,
                "by_symbol_dte": result[tier.lower().replace(" ", "")]["by_symbol_dte"],
            }
        )
        for tier in data
    )
    return result


def _git_sha() -> str:
    try:
        return subprocess.run(
            ("git", "rev-parse", "HEAD"), cwd=REPO_ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _write_report(report: str, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(report, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-parked-chains-v2", action="store_true")
    parser.add_argument("--min-bucket-obs", type=int, default=MIN_BUCKET_OBS)
    parser.add_argument("--tier1-dir", type=Path, default=TIER1_ROOT)
    parser.add_argument("--tier2-dir", type=Path, default=TIER2_ROOT)
    parser.add_argument("--quarantine-path", type=Path, default=QUARANTINE_PATH)
    parser.add_argument("--audit-path", type=Path, default=AUDIT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--receipt", type=Path, default=None)
    args = parser.parse_args(argv)
    report_payload, receipt = run_study(
        include_tier2=args.allow_parked_chains_v2,
        allow_parked_chains_v2=args.allow_parked_chains_v2,
        min_bucket_obs=args.min_bucket_obs,
        tier1_dir=args.tier1_dir,
        tier2_dir=args.tier2_dir,
        quarantine_path=args.quarantine_path,
        audit_path=args.audit_path,
    )
    report = render_report(report_payload)
    _write_report(report, args.report)
    receipt_path = args.receipt or args.report.with_name(
        f"{args.report.stem}-{receipt['receipt_hash'][:12]}.json"
    )
    write_immutable_receipt(receipt, receipt_path)
    tiers = ",".join(receipt["tiers"])
    print(
        f"fill_adversity_context: tiers={tiers} max_asof={receipt['max_asof']} finding={report_payload['finding']}"
    )
    for tier, inventory in receipt["input_inventory"].items():
        print(
            f"{tier}: files={inventory['files']} sessions={inventory['sessions']} admitted={inventory['rows_admitted']} quarantined={inventory['quarantine_exclusions']}"
        )
    print(f"report={args.report}")
    print(f"receipt={receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""options_researcher/oi_change.py -- neutral "OI Δ1d" context line (v1).

For the specific contract shown on an attractiveness card, report how its
open interest (OI -- the count of contracts outstanding, reported once daily
by OPRA as of the PRIOR day's close) changed between the two most recent
prior-known reports. This is a neutral activity fact: it never touches grades,
scores, ranking, sorting, filtering, or contract selection. Fields attach in a
pass strictly AFTER rank_cards, making board invariance structural.

v1 ships the signed delta plus the UNKNOWN taxonomy only. The percentile and
NOTABLE machinery is deferred to a separately pre-registered v2 calibration
study (config's OI_CHANGE_PCTL_WINDOW / OI_CHANGE_PCT_MIN_OBS /
OI_CHANGE_NOTABLE_PCTL stay INACTIVE until then).

A cached day carries one row per contract; a contract "missing" means the row
is ABSENT (never OI 0). Zero is a present row with open_interest == 0.0
(adapter design: data/thetadata_adapter.py inner-joins and drops incomplete
contracts, and validate_chain_schema forbids NaN). The economic OI figure
known on session D is as-of the close of D-1, so the display carries
"as of prior close" and "Δ1d" spans close(D-2) -> close(D-1).
"""
from __future__ import annotations

import math
from datetime import date
from pathlib import Path

import pandas as pd

import config

# Exact-equality contract key, matching the adapter's _KEY_COLS join convention.
_KEY_COLS = ("expiration", "strike", "right")


def _norm_expiration(value: object) -> str:
    return str(value)


def _norm_right(value: object) -> str:
    return str(value).strip().upper()[:1]


def _key_columns(chain: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    """(expiration, strike, right) normalized to the join types: expiration as
    str, strike as float, right as a single upper-case P/C character."""
    exp = chain["expiration"].astype(str)
    strike = pd.to_numeric(chain["strike"], errors="coerce").astype(float)
    right = chain["right"].astype(str).str.strip().str.upper().str[:1]
    return exp, strike, right


def _shares_any_key(chain_a: pd.DataFrame, chain_b: pd.DataFrame) -> bool:
    exp_a, strike_a, right_a = _key_columns(chain_a)
    exp_b, strike_b, right_b = _key_columns(chain_b)
    keys_a = set(zip(exp_a, strike_a, right_a, strict=True))
    keys_b = set(zip(exp_b, strike_b, right_b, strict=True))
    return bool(keys_a & keys_b)


def _open_interest_for(chain: pd.DataFrame, *, expiration: str, strike: float,
                       right: str) -> float | None:
    """OI for the exact (expiration, strike, right) contract, or None if the
    row is absent. A missing row is NEVER treated as OI 0. A present row with
    a non-finite OI (forbidden by validate_chain_schema, so cache-corrupt if
    ever seen) is unusable data and also reports as absent rather than
    raising."""
    exp, strike_col, right_col = _key_columns(chain)
    mask = (exp == expiration) & (strike_col == strike) & (right_col == right)
    rows = chain.loc[mask.to_numpy()]
    if rows.empty:
        return None
    value = float(pd.to_numeric(rows["open_interest"], errors="coerce").iloc[-1])
    return value if math.isfinite(value) else None


def oi_change_fields(chain_day: pd.DataFrame, chain_prior: pd.DataFrame | None,
                     prior_gap_days: int | None, *, expiration: object,
                     strike: float, right: str) -> dict:
    """Pure OI-change classification for one contract. Status decision order
    (first match wins): NO_PRIOR_CHAIN -> STALE_PRIOR_CHAIN -> GRID_SHIFT ->
    CONTRACT_ABSENT -> LOW_BASE -> OK. Returns
    {"oi_delta_1d": int | None, "oi_change_status": str}."""
    if chain_prior is None:
        return {"oi_delta_1d": None, "oi_change_status": "NO_PRIOR_CHAIN"}
    if prior_gap_days is not None and prior_gap_days > config.OI_CHANGE_MAX_PRIOR_GAP_DAYS:
        return {"oi_delta_1d": None, "oi_change_status": "STALE_PRIOR_CHAIN"}
    if not _shares_any_key(chain_day, chain_prior):
        # Zero shared contract keys indicates a corporate-action grid shift,
        # the same fail-closed heuristic as the adapter's empty-intersection
        # guard.
        return {"oi_delta_1d": None, "oi_change_status": "GRID_SHIFT"}

    expiration = _norm_expiration(expiration)
    strike = float(strike)
    right = _norm_right(right)
    oi_today = _open_interest_for(chain_day, expiration=expiration,
                                  strike=strike, right=right)
    oi_prior = _open_interest_for(chain_prior, expiration=expiration,
                                  strike=strike, right=right)
    if oi_today is None or oi_prior is None:
        return {"oi_delta_1d": None, "oi_change_status": "CONTRACT_ABSENT"}
    if oi_prior < config.OI_CHANGE_MIN_BASE:
        return {"oi_delta_1d": None, "oi_change_status": "LOW_BASE"}
    return {"oi_delta_1d": int(round(oi_today - oi_prior)),
            "oi_change_status": "OK"}


def oi_change_line(fields: dict) -> str:
    """Pinned display wording. OK carries the signed delta (no sign on zero);
    every UNKNOWN status states its reason. The em dash is U+2014."""
    if fields["oi_change_status"] == "OK":
        delta = fields["oi_delta_1d"]
        if delta == 0:
            return "OI Δ1d: 0 contracts (as of prior close)"
        return f"OI Δ1d: {delta:+d} contracts (as of prior close)"
    return f"OI Δ1d: unavailable (UNKNOWN — {fields['oi_change_status']})"


def find_prior_chain(symbol: str, day: str,
                     cache_dir: str = ".cache/chains") -> tuple[str, pd.DataFrame] | None:
    """Latest cached session STRICTLY before `day`: return (prior_day_iso,
    frame), or None if none exists. Files are {cache_dir}/{symbol}_{date}
    .parquet; a same-day or future-dated file is never read (no look-ahead)."""
    day_date = date.fromisoformat(day)
    prior_day: date | None = None
    prior_path: Path | None = None
    for path in Path(cache_dir).glob(f"{symbol}_*.parquet"):
        stamp = path.stem.rsplit("_", 1)[-1]
        try:
            file_date = date.fromisoformat(stamp)
        except ValueError:
            continue
        if file_date < day_date and (prior_day is None or file_date > prior_day):
            prior_day, prior_path = file_date, path
    if prior_path is None or prior_day is None:
        return None
    return prior_day.isoformat(), pd.read_parquet(prior_path)


def attach_oi_change(cards: list[dict], *, right: str, chain_day: pd.DataFrame,
                     symbol: str, day: str,
                     cache_dir: str = ".cache/chains") -> None:
    """Post-ranking pass: resolve the prior chain ONCE, then set the three new
    keys (oi_delta_1d, oi_change_status, oi_change_line) on each card. Never
    reorders, removes, or mutates any existing card key."""
    if not cards:
        return
    prior = find_prior_chain(symbol, day, cache_dir=cache_dir)
    if prior is None:
        chain_prior: pd.DataFrame | None = None
        prior_gap_days: int | None = None
    else:
        prior_day, chain_prior = prior
        prior_gap_days = (date.fromisoformat(day)
                          - date.fromisoformat(prior_day)).days
    for card in cards:
        fields = oi_change_fields(
            chain_day, chain_prior, prior_gap_days,
            expiration=card["expiry"], strike=float(card["strike"]),
            right=right)
        card["oi_delta_1d"] = fields["oi_delta_1d"]
        card["oi_change_status"] = fields["oi_change_status"]
        card["oi_change_line"] = oi_change_line(fields)

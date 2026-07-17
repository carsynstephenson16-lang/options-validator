"""H9 eligibility census — counts and data sufficiency ONLY (spec §6).

Charter: this module may read the T_entry chain solely to test contract
existence and liquidity, and may test exit-window coverage only by file
PRESENCE. It never prices an exit, never computes a return, and never
imports exit-side fill helpers. That restriction is enforced by tests.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

import config
from data.cache_runner import trading_days
from data.thetadata_adapter import get_eod_chain, passes_liquidity
from data.underlying_closes import load_closes_adjusted
from options_researcher.chains import is_monthly
from options_researcher.h9_events import H9Event
from research.hashing import sha256_file

REASONS = ("window_edge", "registry_excluded", "missing_closes",
           "missing_entry_chain", "no_contract_in_bands", "entry_liquidity_fail",
           "no_acceptance_ts")

# Exceptions the loaders below are documented to raise on a genuine data
# miss. Narrowed deliberately (not bare Exception) so a real bug elsewhere
# in the census loop still surfaces as a test failure instead of being
# silently folded into an exclusion count.
_CHAIN_LOAD_ERRORS = (FileNotFoundError, ValueError, RuntimeError)
_CLOSES_LOAD_ERRORS = (FileNotFoundError, ValueError, RuntimeError)


@dataclass
class CensusResult:
    eligible_count: int
    per_symbol: dict
    reasons: Counter
    exit_window_gap_days: int
    manifest: list = field(default_factory=list)  # (path, sha256) of files read
    floor_met: bool = False
    eligible_events: list = field(default_factory=list)


def _entry_chain(symbol: str, iso: str) -> pd.DataFrame:
    return get_eod_chain(symbol, iso, allow_oos=True)


def _closes(symbol: str, start_iso: str, end_iso: str) -> pd.Series:
    return load_closes_adjusted(symbol, start_iso, end_iso, allow_oos=True)


def _dte(entry_iso: str, expiration) -> int:
    exp = expiration if isinstance(expiration, date) else date.fromisoformat(str(expiration)[:10])
    return (exp - date.fromisoformat(entry_iso)).days


def _has_admissible_contract(chain: pd.DataFrame, entry_iso: str) -> tuple[bool, str]:
    lo_d, hi_d = config.H6_DELTA_BAND
    lo_t, hi_t = config.H6_DTE_BAND
    calls: pd.DataFrame = chain.loc[chain["right"].eq("C")].copy()
    in_band: pd.DataFrame = calls.loc[
        (calls["delta"] >= lo_d) & (calls["delta"] <= hi_d)
        & (calls["expiration"].map(lambda e: lo_t <= _dte(entry_iso, e) <= hi_t))
        & (calls["expiration"].map(lambda e: is_monthly(
            e if isinstance(e, date) else date.fromisoformat(str(e)[:10]))))
    ].copy()
    if in_band.empty:
        return False, "no_contract_in_bands"
    liquid: pd.DataFrame = in_band.loc[in_band.apply(
        lambda r: passes_liquidity(r["open_interest"], r["bid"], r["ask"]), axis=1)]
    if liquid.empty:
        return False, "entry_liquidity_fail"
    return True, ""


def _max_exit_horizon(entry_iso: str) -> str:
    days = trading_days(entry_iso, config.H9_WINDOW[1])
    horizon = min(len(days) - 1, config.H6_DTE_BAND[1])
    return days[horizon] if days else entry_iso


def run_census(events: list[H9Event], *, chain_dir: Path,
               floor: int | None = None) -> CensusResult:
    """Counts-only eligibility pass over `events`. Reads the T_entry chain
    solely to test contract existence + liquidity; exit-window coverage is a
    file-PRESENCE check on `chain_dir`, never a content read. Structurally
    cannot return a price, a return, or a P&L figure (see CensusResult and
    the module docstring)."""
    floor = config.H9_MIN_ELIGIBLE_EVENTS if floor is None else floor
    reasons: Counter = Counter()
    per_symbol: dict = {}
    manifest: list = []
    eligible: list = []
    gap_days = 0
    for e in events:
        stats = per_symbol.setdefault(e.symbol, {"eligible": 0, "excluded": 0})
        if e.t_entry is None or e.t_dec is None or e.t_pre is None:
            reasons["window_edge"] += 1
            stats["excluded"] += 1
            continue
        try:
            closes = _closes(e.symbol, e.t_pre, e.t_dec)
        except _CLOSES_LOAD_ERRORS:
            closes = pd.Series(dtype=float)
        if e.t_pre not in closes.index or e.t_dec not in closes.index:
            reasons["missing_closes"] += 1
            stats["excluded"] += 1
            continue
        try:
            chain = _entry_chain(e.symbol, e.t_entry)
        except _CHAIN_LOAD_ERRORS:
            reasons["missing_entry_chain"] += 1
            stats["excluded"] += 1
            continue
        entry_path = chain_dir / f"{e.symbol}_{e.t_entry}.parquet"
        if entry_path.exists():
            manifest.append((str(entry_path), sha256_file(entry_path)))
        ok, reason = _has_admissible_contract(chain, e.t_entry)
        if not ok:
            reasons[reason] += 1
            stats["excluded"] += 1
            continue
        for d in trading_days(e.t_entry, _max_exit_horizon(e.t_entry)):
            if not (chain_dir / f"{e.symbol}_{d}.parquet").exists():
                gap_days += 1
        stats["eligible"] += 1
        eligible.append(e)
    res = CensusResult(eligible_count=len(eligible), per_symbol=per_symbol,
                        reasons=reasons, exit_window_gap_days=gap_days,
                        manifest=manifest, eligible_events=eligible)
    res.floor_met = res.eligible_count >= floor
    return res

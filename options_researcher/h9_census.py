"""H9 eligibility census — counts and data sufficiency ONLY (spec §6).

Charter: this module may read the T_entry chain solely to test contract
existence and liquidity, and may test exit-window coverage only by file
PRESENCE. It never prices an exit, never computes a return, and never
imports exit-side fill helpers. That restriction is enforced by tests.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow.lib

import config
from data.audit_exceptions import excluded as _registry_excluded
from data.cache_runner import trading_days
from data.thetadata_adapter import load_cached_chain, passes_liquidity
from data.underlying_closes import load_closes_adjusted
from options_researcher.chains import is_monthly
from options_researcher.h9_events import H9Event
from research.hashing import sha256_file

REASONS = ("window_edge", "registry_excluded", "missing_closes",
           "missing_entry_chain", "no_contract_in_bands", "entry_liquidity_fail",
           "no_acceptance_ts", "unclassified_event", "non_earnings_event")

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


def _entry_chain(symbol: str, iso: str, chain_dir: Path) -> pd.DataFrame:
    # Cache-ONLY (spec §1 zero new data spend): a missing chain raises
    # FileNotFoundError, which the census loop codes as `missing_entry_chain`
    # and excludes the event -- it is NEVER fetched from the paid client.
    # H9 is verdict-bearing, so legacy v1 partitions are refused as display-only.
    # Reads resolve against the census's OWN chain_dir so presence checks and
    # content reads can never diverge (post-merge test caught the divergence).
    return load_cached_chain(
        symbol,
        iso,
        allow_oos=True,
        cache_dir=chain_dir,
        verdict_bearing=True,
    )


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
    """Last session on/before entry + max-DTE calendar days, clamped to the window."""
    cap = (date.fromisoformat(entry_iso)
           + timedelta(days=config.H6_DTE_BAND[1])).isoformat()
    days = trading_days(entry_iso, min(cap, config.H9_WINDOW[1]))
    return days[-1] if days else entry_iso


def in_registry_exclusion(event: H9Event) -> bool:
    """True when any of the event's sessions fall inside a ratified
    archive-availability exclusion window (data.audit_exceptions, the H7
    reviewed exception registry -- H7_AMENDMENT_V1_3 ratifies the
    data_coverage entries within it). Uses the same per-day `excluded()`
    lookup as data/h7_manifest.py so H9 and H7 never enumerate exclusions
    independently. Registry start/end are already ISO date strings
    (YYYY-MM-DD), so the comparison inside `excluded()` is plain ISO-string
    comparison -- no date-object normalization is needed here."""
    for iso in (event.t_pre, event.t_dec, event.t_entry):
        if iso and _registry_excluded(event.symbol, iso) is not None:
            return True
    return False


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
        if e.exclusion in ("unclassified_event", "non_earnings_event"):
            reasons[e.exclusion] += 1
            stats["excluded"] += 1
            continue
        if e.t_entry is None or e.t_dec is None or e.t_pre is None:
            reasons["window_edge"] += 1
            stats["excluded"] += 1
            continue
        if in_registry_exclusion(e):
            reasons["registry_excluded"] += 1
            stats["excluded"] += 1
            continue
        try:
            closes = _closes(e.symbol, e.t_pre, e.t_dec)
        except pyarrow.lib.ArrowInvalid:
            raise  # cache corruption is systemic — never a per-event exclusion
        except _CLOSES_LOAD_ERRORS:
            closes = pd.Series(dtype=float)
        if e.t_pre not in closes.index or e.t_dec not in closes.index:
            reasons["missing_closes"] += 1
            stats["excluded"] += 1
            continue
        try:
            chain = _entry_chain(e.symbol, e.t_entry, chain_dir)
        except pyarrow.lib.ArrowInvalid:
            raise  # cache corruption is systemic — never a per-event exclusion
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

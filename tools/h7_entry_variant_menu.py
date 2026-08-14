"""Frequency-ONLY measurement of candidate H7 entry-rule variants (brief 09).

WHAT THIS TOOL MEASURES
-----------------------
How OFTEN each candidate entry-rule variant would have fired over a cached,
causally-evaluated historical panel. Nothing else.

THE ONE HARD INTEGRITY RULE (brief 09, 2026-08-13)
--------------------------------------------------
Never compute, store, or report P&L, win rate, premium capture, or ANY outcome
statistic for any variant. The moment a variant's historical profitability is
observed, choosing it becomes result-selection and the later pre-registration
is theater. Selection on trigger frequency, blind to returns, is what preserves
the validity of the forward test.

Two machine-enforced guards implement that rule here:
  * ``FORBIDDEN_OVERRIDE_KEYS`` -- a variant may not relax fill/liquidity/cost
    realism or the earnings gate. Attempting to does not warn, it raises.
  * ``assert_no_outcome_fields`` -- every receipt is scanned for outcome-ish
    keys before it can be written. A receipt that mentions returns cannot be
    produced by this tool at all.

The tool emits NO verdict. It reports counts, exact binomial intervals, and
per-name/rolling-window dispersion. The owner picks a variant and types its
frozen numbers at registration.

Data: cached ThetaData EOD chains + cached underlying closes ONLY (OD-4 stands;
no provider calls, no network).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from data.atomic_io import atomic_text_write  # noqa: E402
from data.cache_runner import session_close_utc  # noqa: E402
from data.underlying_closes import adjusted_from_raw, adjustment_factor  # noqa: E402
from options_researcher import h7_signals as sig  # noqa: E402
from options_researcher import h7_watch  # noqa: E402
from options_researcher.chains import load_range  # noqa: E402
from options_researcher.h7_board import resolve_board  # noqa: E402
from options_researcher.h7_cohort import load_registered_cohort  # noqa: E402
from options_researcher.h7_earnings import load_assertions  # noqa: E402
from options_researcher.h7_scope import watch_universe  # noqa: E402
from options_researcher.h7_watch import assemble_name  # noqa: E402
from research.hashing import (  # noqa: E402
    canonical_json,
    config_hash,
    sha256_file,
    sha256_hex,
)
from strategies import h7_lanes  # noqa: E402

RECEIPT_KIND = "h7_entry_variant_frequency/v1"
BASELINE_STACK_VERSION = "h7-frozen-entry-stack-plus-board/v1"
DEFAULT_CHAIN_DIR = Path(".cache/chains")
UNDERLYING_DIR = Path(".cache/underlying")

# Calendar-day closes preload before each decision session. MUST match the
# frozen feasibility tool's window: reclaimed_20d_high() and episode_low()
# scan backwards for a re-arm event, so the window LENGTH is load-bearing and
# a longer slice is not a no-op.
CLOSES_WINDOW_DAYS = 560

# 2026-07-24 registration feasibility gate: expected entries >= 2x the loss
# requirement. H7's loss bar is 10, so the frequency bar is 20 expected
# entries per declared window. Recorded, never evaluated into a verdict here.
FEASIBILITY_LOSS_BAR = 10
FEASIBILITY_ENTRY_BAR = 2 * FEASIBILITY_LOSS_BAR

# ---------------------------------------------------------------------------
# Integrity guards
# ---------------------------------------------------------------------------

# Config constants that protect FILL REALISM or the EARNINGS gate. Brief 09:
# "Liquidity/spread caps protecting fill realism MUST NOT be relaxed -- they
# are cost-model integrity, not signal." The 2026-08-11 v2 arming-bottleneck
# design adds: "The earnings and options-liquidity gates are hard constraints
# and are not candidates for relaxation."
FORBIDDEN_OVERRIDE_KEYS = frozenset({
    # fill / cost realism
    "SLIPPAGE_HAIRCUT",
    "HALF_SPREAD_COST",
    "COMMISSION_PER_CONTRACT",
    "FILL_MODEL_ID",
    "MAX_SPREAD_PCT",
    "MIN_OPEN_INTEREST",
    "H7_ADMIT_MAX_SPREAD_PCT",
    # earnings gate (fail-closed by design; the fix for UNKNOWN is more
    # primary-source earnings data, never a looser gate)
    "H7_EARNINGS_BAN_SESSIONS",
    "H7_EARNINGS_POST_REPORT_GRACE_D",
    "H7_POST_REPORT_GRACE_DAYS",
    "H7C_CLOSE_BEFORE_EARNINGS",
    # risk sizing frozen by the owner
    "H7_MONTHLY_AT_RISK",
})

# Substrings that would indicate an outcome statistic leaked into a receipt.
# "cost" is deliberately included: trade-construction economics are not
# frequency and have no business in this menu.
FORBIDDEN_RECEIPT_SUBSTRINGS = (
    "pnl", "p_and_l", "profit", "return", "win_rate", "winrate", "loss_rate",
    "expectancy", "sharpe", "premium_captur", "payoff", "credit", "debit",
    "max_loss", "cost", "yield", "drawdown_pct_realized", "equity",
)


def assert_no_outcome_fields(obj, *, path: str = "receipt") -> None:
    """Refuse any structure whose KEYS name an outcome statistic.

    This is the machine-enforced half of brief 09's integrity rule. It runs
    before a receipt can be written, so a receipt carrying an outcome field
    cannot be produced by this tool even by mistake.

    Keys only, deliberately: the prose disclosures in a receipt must be free to
    SAY "no win rate or premium capture is computed", and a value-scanning
    guard would reject its own honesty statement.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = str(key).lower()
            for bad in FORBIDDEN_RECEIPT_SUBSTRINGS:
                if bad in lowered:
                    raise ValueError(
                        f"outcome-shaped key {path}.{key!r} is forbidden in a "
                        f"frequency-only receipt (brief 09 integrity rule)"
                    )
            assert_no_outcome_fields(value, path=f"{path}.{key}")
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            assert_no_outcome_fields(value, path=f"{path}[{index}]")


# ---------------------------------------------------------------------------
# Variant definition
# ---------------------------------------------------------------------------

LANE_MODE_AND = "and"       # frozen: both conditions required
LANE_MODE_OR = "or"         # relaxed: either condition suffices
BOARD_ONE_PER_UNDERLYING = "one_per_underlying"   # frozen resolver
BOARD_MULTI_LANE = "multi_lane_per_underlying"    # variant-only relaxation

DRIFT_NONE = "none"
DRIFT_LOW = "low"
DRIFT_HIGH = "high"


@dataclass(frozen=True)
class Variant:
    """One candidate entry rule. Declarative so the receipt can restate it.

    ``rationale_drift`` answers brief 09's question: does this variant still
    test the ORIGINAL H7 idea? A variant that fires often but no longer tests
    that idea is a DIFFERENT hypothesis and must say so.
    """

    variant_id: str
    axis: str
    rule_change: str
    rationale_drift: str
    config_overrides: dict = field(default_factory=dict)
    lane_a_mode: str = LANE_MODE_AND
    lane_b_mode: str = LANE_MODE_AND
    lane_b_edge_trigger: bool = True
    board_policy: str = BOARD_ONE_PER_UNDERLYING
    universe_label: str = "official_scope_15"

    def __post_init__(self) -> None:
        bad = sorted(set(self.config_overrides) & FORBIDDEN_OVERRIDE_KEYS)
        if bad:
            raise ValueError(
                f"{self.variant_id}: refusing to relax fill-realism / earnings-gate "
                f"constants {bad} (brief 09; cost-model integrity is not signal)"
            )
        unknown = sorted(k for k in self.config_overrides if not hasattr(config, k))
        if unknown:
            raise ValueError(f"{self.variant_id}: unknown config constants {unknown}")
        if self.rationale_drift not in (DRIFT_NONE, DRIFT_LOW, DRIFT_HIGH):
            raise ValueError(f"{self.variant_id}: bad rationale_drift")

    def identity(self) -> dict:
        """The hashable definition of this variant."""
        return {
            "variant_id": self.variant_id,
            "axis": self.axis,
            "rule_change": self.rule_change,
            "rationale_drift": self.rationale_drift,
            "config_overrides": dict(sorted(self.config_overrides.items())),
            "lane_a_mode": self.lane_a_mode,
            "lane_b_mode": self.lane_b_mode,
            "lane_b_edge_trigger": self.lane_b_edge_trigger,
            "board_policy": self.board_policy,
            "universe_label": self.universe_label,
        }

    def identity_hash(self) -> str:
        return sha256_hex(canonical_json(self.identity()))


# ---------------------------------------------------------------------------
# Variant application (patch, measure, restore)
# ---------------------------------------------------------------------------

def _lane_a_armed_or(closes: pd.Series) -> bool:
    """Relaxed lane-a arming: deep drawdown OR a 20d-high reclaim (not both).

    RATIONALE DRIFT IS HIGH. Frozen H7a tests "a beaten-down name stabilising";
    the OR form fires on any reclaim regardless of drawdown, which is a
    momentum-breakout idea, not the registered one.
    """
    return (sig.drawdown_pct(closes) >= config.H7A_DRAWDOWN_MIN
            or sig.reclaimed_20d_high(closes))


def _lane_b_armed_or(closes: pd.Series) -> bool:
    """Relaxed lane-b arming: tight range OR low RV percentile (not both).

    RATIONALE DRIFT IS HIGH. The frozen coil test requires BOTH a narrow price
    range and quiet realized vol; either alone is a much weaker "coil".
    """
    return (sig.range_pct(closes, config.H7B_RANGE_LOOKBACK_D) <= config.H7B_RANGE_MAX
            or sig.rv_percentile(closes) <= config.H7B_RV_PCTILE_MAX)


def _decide_lane_b_no_edge(*, closes, chain, spot, today, month_spent, banned):
    """Lane b WITHOUT the first-day-only edge trigger.

    Frozen decide_lane_b fires only on the first session the coil conditions
    turn on (review finding R14). This variant lets a persisting coil fire on
    any session it is armed. It reuses the frozen ``_long_action`` so structure
    selection, liquidity checks and adverse-side fills stay byte-identical --
    only the arming edge condition differs.
    """
    if banned or not sig.lane_b_armed(closes):
        return None
    stop_ref = float(closes.iloc[-config.H7B_RANGE_LOOKBACK_D:].min())
    return h7_lanes._long_action(closes, chain, spot, today, month_spent, "b", stop_ref)


@contextmanager
def applied(variant: Variant) -> Iterator[None]:
    """Apply a variant's overrides, then restore everything.

    Config constants are read at call time by the frozen signal/lane code, so
    patching the module attributes is enough. ``h7_watch`` imported the lane
    deciders by value, so BOTH module bindings are patched when the lane-b edge
    trigger is relaxed.
    """
    saved_config = {key: getattr(config, key) for key in variant.config_overrides}
    saved_lane_a = sig.lane_a_armed
    saved_lane_b = sig.lane_b_armed
    saved_decide_b_lanes = h7_lanes.decide_lane_b
    saved_decide_b_watch = h7_watch.decide_lane_b
    try:
        for key, value in variant.config_overrides.items():
            setattr(config, key, value)
        if variant.lane_a_mode == LANE_MODE_OR:
            sig.lane_a_armed = _lane_a_armed_or
        if variant.lane_b_mode == LANE_MODE_OR:
            sig.lane_b_armed = _lane_b_armed_or
        if not variant.lane_b_edge_trigger:
            h7_lanes.decide_lane_b = _decide_lane_b_no_edge
            h7_watch.decide_lane_b = _decide_lane_b_no_edge
        yield
    finally:
        for key, value in saved_config.items():
            setattr(config, key, value)
        sig.lane_a_armed = saved_lane_a
        sig.lane_b_armed = saved_lane_b
        h7_lanes.decide_lane_b = saved_decide_b_lanes
        h7_watch.decide_lane_b = saved_decide_b_watch


def resolve_board_multi_lane(candidates: list[dict], *, open_h7c: int = 0,
                             sleeve_left: float = 0.0,
                             open_symbols: tuple = ()) -> tuple[list[dict], list[dict]]:
    """VARIANT-ONLY board: drop one-candidate-per-underlying, keep every cap.

    Brief 09 axis 4 allows evaluating more than one setup shape per session
    "if and only if the registered risk cap still binds". The sleeve and the
    lane-c concurrency cap therefore still bind exactly as in the frozen
    resolver; only the same-underlying exclusivity is relaxed. Positions
    already open in the book still block their underlying.
    """
    order = sorted(candidates, key=lambda c: (
        str(c["session"]), config.H7_LANE_PRIORITY.index(c["lane"]), c["symbol"].upper()))
    book_open = {s.upper() for s in open_symbols}
    c_open = int(open_h7c)
    left = float(sleeve_left)
    accepted: list[dict] = []
    rejected: list[dict] = []
    for cand in order:
        at_risk = float(cand["action"].get("max_loss", cand["action"].get("cost", 0.0)))
        if cand["symbol"].upper() in book_open:
            rejected.append({**cand, "rejection": "underlying_open"})
        elif cand["lane"] == "c" and c_open >= config.H7C_MAX_CONCURRENT:
            rejected.append({**cand, "rejection": "h7c_basket_cap"})
        elif at_risk > left:
            rejected.append({**cand, "rejection": "sleeve_exhausted"})
        else:
            accepted.append(cand)
            left -= at_risk
            if cand["lane"] == "c":
                c_open += 1
    return accepted, rejected


# ---------------------------------------------------------------------------
# Statistics -- frequency and dispersion ONLY
# ---------------------------------------------------------------------------

def clopper_pearson(passes: int, trials: int, *, alpha: float = 0.05
                    ) -> tuple[float, float]:
    """Exact (Clopper-Pearson) two-sided CI for a binomial proportion.

    Verified against the repo's published interval for the 4/1050 baseline:
    [1.09, 10.21] expected entries per 70-session 15-name window.
    """
    from scipy.stats import beta

    if trials <= 0 or passes < 0 or passes > trials:
        raise ValueError("clopper_pearson requires 0 <= passes <= trials, trials > 0")
    low = 0.0 if passes == 0 else float(beta.ppf(alpha / 2, passes, trials - passes + 1))
    high = 1.0 if passes == trials else float(
        beta.ppf(1 - alpha / 2, passes + 1, trials - passes))
    return low, high


# Approximate holding length in SESSIONS for the long lanes, derived purely
# from the registered schedule: enter at the monthly expiration nearest 90 DTE
# (H7_LONG_DTE_BAND midpoint) and time-exit at H7_CLOSE_AT_DTE=30, i.e. ~60
# calendar days ~= 42 trading sessions. The shorter value is a deliberately
# generous early-exit assumption. These are SCHEDULE constants: no price path
# and no outcome is consulted to produce them.
OCCUPANCY_LOCKOUT_SESSIONS = (42, 21)


def occupancy_constrained_count(entry_rows: list[dict], panel_sessions: list[str],
                                lockout_sessions: int) -> int:
    """Entries left once one-open-position-per-underlying is honoured.

    The measurement's clean-book assumption (every session starts flat with the
    full sleeve) lets one name enter over and over inside a window. Live,
    ``H7_MAX_OPEN_PER_UNDERLYING = 1`` blocks the underlying for the whole
    holding period. This replays the recorded entry sessions through a fixed
    per-underlying lockout and reports how many survive.

    Still an UPPER bound: it does not net the monthly sleeve across the
    lockout, and it consults no outcome, so a position that would have been
    closed early is not credited with freeing its slot sooner.
    """
    if lockout_sessions <= 0:
        raise ValueError("lockout_sessions must be positive")
    index = {session: i for i, session in enumerate(panel_sessions)}
    locked_until: dict[str, int] = {}
    kept = 0
    for row in sorted(entry_rows, key=lambda r: (r["session"], r["symbol"], r["lane"])):
        position = index.get(row["session"])
        if position is None:
            continue
        if locked_until.get(row["symbol"], -1) > position:
            continue
        kept += 1
        locked_until[row["symbol"]] = position + lockout_sessions
    return kept


def rolling_window_counts(entry_sessions: list[str], panel_sessions: list[str],
                          window: int) -> dict:
    """Entries inside each rolling `window`-session block of the panel.

    Brief 09 requires this: entry events cluster in vol regimes, so an
    unconditional binomial CI understates window-to-window variance. This is a
    dispersion diagnostic, not an interval.
    """
    if len(panel_sessions) < window:
        return {"windows": 0, "note": f"panel shorter than {window} sessions"}
    index = {session: i for i, session in enumerate(panel_sessions)}
    hits = sorted(index[s] for s in entry_sessions if s in index)
    counts = []
    for start in range(0, len(panel_sessions) - window + 1):
        end = start + window
        counts.append(sum(1 for h in hits if start <= h < end))
    return {
        "windows": len(counts),
        "min": min(counts),
        "median": float(statistics.median(counts)),
        "max": max(counts),
        "zero_entry_window_fraction": sum(1 for c in counts if c == 0) / len(counts),
    }


# ---------------------------------------------------------------------------
# Cached, causal data access
# ---------------------------------------------------------------------------

class PanelData:
    """Read-only cached loader. Loads each closes series and each chain ONCE.

    Causality: ``closes_window`` slices to [session-560d, session] inclusive,
    so no row after the decision session can reach a signal. This reproduces
    ``load_closes_adjusted(symbol, session-560d, session)`` exactly (tested).
    """

    def __init__(self, chain_dir: Path = DEFAULT_CHAIN_DIR,
                 underlying_dir: Path = UNDERLYING_DIR) -> None:
        self.chain_dir = Path(chain_dir)
        self.underlying_dir = Path(underlying_dir)
        self._closes: dict[str, pd.Series] = {}
        self._chains: dict[tuple[str, str], pd.DataFrame | None] = {}

    def full_closes(self, symbol: str) -> pd.Series:
        if symbol not in self._closes:
            frame = pd.read_parquet(self.underlying_dir / f"{symbol}.parquet")
            raw = pd.Series(frame.set_index("date")["close"]).sort_index().astype(float)
            self._closes[symbol] = adjusted_from_raw(raw, symbol)
        return self._closes[symbol]

    def closes_window(self, symbol: str, session: str) -> pd.Series:
        start = (date.fromisoformat(session)
                 - timedelta(days=CLOSES_WINDOW_DAYS)).isoformat()
        floor = config.H7_SIGNAL_CLOSES_START.get(symbol)
        if floor is not None and start < floor:
            start = floor
        return self.full_closes(symbol).loc[start:session]

    def chain(self, symbol: str, session: str) -> pd.DataFrame | None:
        key = (symbol, session)
        if key not in self._chains:
            self._chains[key] = load_range(
                symbol, session, session, allow_oos=True).get(session)
        return self._chains[key]

    def drop_chain_cache(self) -> None:
        """Release per-session chain frames once a session is finished."""
        self._chains.clear()

    def cached_sessions(self, symbol: str) -> set[str]:
        return {path.stem.removeprefix(f"{symbol}_")
                for path in self.chain_dir.glob(f"{symbol}_????-??-??.parquet")}


def common_sessions(symbols: list[str], data: PanelData, *, limit: int | None = None
                    ) -> list[str]:
    """Sessions with an exact cached chain for EVERY symbol, oldest first."""
    common: set[str] | None = None
    for symbol in symbols:
        dates = data.cached_sessions(symbol)
        common = dates if common is None else common & dates
    ordered = sorted(common or set())
    return ordered[-limit:] if limit else ordered


def ragged_sessions(symbols: list[str], data: PanelData) -> dict[str, list[str]]:
    """Every cached session per symbol -- the unequal-history long panel."""
    return {symbol: sorted(data.cached_sessions(symbol)) for symbol in symbols}


# ---------------------------------------------------------------------------
# Core measurement
# ---------------------------------------------------------------------------

def _lane_candidates(symbol: str, card: dict, session: str) -> list[dict]:
    return [
        {"symbol": symbol, "lane": lane[-1], "session": session,
         "action": card[lane]["action"]}
        for lane in ("lane_a", "lane_b", "lane_c")
        if card[lane]["state"] == "ENTRY-OK"
    ]


def measure_variants(*, variants: list[Variant], sessions_by_symbol: dict[str, list[str]],
                     data: PanelData, assertions: list,
                     collect_waterfall_for: str | None = None,
                     arming_only: bool = False) -> dict:
    """Run every variant over the panel in one causal pass.

    The chain parquet for a symbol-day is read ONCE and shared across variants;
    variants never see each other's state because ``applied`` restores every
    patch. Per symbol-day a variant is skipped when NEITHER lane-a nor lane-b
    arming fires: ``_lane_state`` can only return ENTRY-OK when its lane's
    armed_fn is true, and lane c reuses lane a's arming, so an unarmed
    symbol-day provably cannot produce an entry. (Equivalence is tested.)

    ``arming_only`` measures ONLY the technical trigger (a closes-only
    property) and touches no chain. It exists because the full stack cannot be
    evaluated before the earnings panel's coverage floor: with no assertion
    known as of an old session the earnings gate fails closed to UNKNOWN, so a
    long full-stack panel would measure earnings-data coverage rather than
    entry frequency.
    """
    all_sessions = sorted({s for days in sessions_by_symbol.values() for s in days})
    symbols_by_session: dict[str, list[str]] = {}
    for symbol, days in sessions_by_symbol.items():
        for day in days:
            symbols_by_session.setdefault(day, []).append(symbol)

    entries: dict[str, list[dict]] = {v.variant_id: [] for v in variants}
    armed_rows: dict[str, list[dict]] = {v.variant_id: [] for v in variants}
    errors: dict[str, list[dict]] = {v.variant_id: [] for v in variants}
    waterfall: dict[str, int] = {}

    for session in all_sessions:
        today = date.fromisoformat(session)
        known_as_of = None if arming_only else session_close_utc(session)
        candidates: dict[str, list[dict]] = {v.variant_id: [] for v in variants}

        for symbol in sorted(symbols_by_session.get(session, [])):
            chain = None
            spot = None
            try:
                closes = data.closes_window(symbol, session)
                if closes.empty or str(closes.index[-1])[:10] != session:
                    raise RuntimeError("adjusted closes do not end on session")
                if not arming_only:
                    chain = data.chain(symbol, session)
                    if chain is None:
                        raise RuntimeError("exact-session chain unavailable")
                    spot = float(closes.iloc[-1]) * adjustment_factor(symbol, session)
            except Exception as exc:  # a gap is a recorded row, never a crash
                for variant in variants:
                    if symbol in _variant_symbols(variant, sessions_by_symbol):
                        errors[variant.variant_id].append(
                            {"session": session, "symbol": symbol,
                             "error": f"{type(exc).__name__}: {exc}"})
                continue

            armed_cache: dict[tuple, tuple[bool, bool]] = {}
            for variant in variants:
                if symbol not in _variant_symbols(variant, sessions_by_symbol):
                    continue
                with applied(variant):
                    key = arming_signature(variant)
                    if key not in armed_cache:
                        armed_cache[key] = (bool(sig.lane_a_armed(closes)),
                                            bool(sig.lane_b_armed(closes)))
                    a_armed, b_armed = armed_cache[key]
                    armed = a_armed or b_armed
                    if armed:
                        armed_rows[variant.variant_id].append(
                            {"session": session, "symbol": symbol,
                             "lane_a": a_armed, "lane_b": b_armed})
                    if arming_only or chain is None or spot is None:
                        continue
                    want_waterfall = variant.variant_id == collect_waterfall_for
                    if not armed and not want_waterfall:
                        continue
                    card = assemble_name(
                        symbol=symbol, closes=closes, chain=chain, today=today,
                        assertions=assertions, known_as_of=known_as_of,
                        open_positions=(), spot=spot, open_h7c=0, month_spent=0.0)
                    if want_waterfall:
                        _tally_waterfall(waterfall, card, armed=armed)
                    candidates[variant.variant_id].extend(
                        _lane_candidates(symbol, card, session))

        if not arming_only:
            for variant in variants:
                rows = candidates[variant.variant_id]
                if not rows:
                    continue
                with applied(variant):
                    resolver = (resolve_board_multi_lane
                                if variant.board_policy == BOARD_MULTI_LANE
                                else resolve_board)
                    accepted, _ = resolver(
                        rows, open_h7c=0, sleeve_left=config.H7_MONTHLY_AT_RISK,
                        open_symbols=())
                entries[variant.variant_id].extend(
                    {"session": session, "symbol": row["symbol"], "lane": row["lane"]}
                    for row in accepted)
        data.drop_chain_cache()

    return {"entries": entries, "armed": armed_rows, "errors": errors,
            "waterfall": waterfall}


def earnings_coverage_floor(assertions: list) -> str | None:
    """Earliest session at which ANY earnings assertion was knowable.

    Before this date the frozen earnings gate has nothing to read and fails
    closed to UNKNOWN for every name, so no full-stack entry is possible. This
    is a property of the DATA, not of the entry rule.
    """
    stamps = [str(a.get("known_as_of_utc") or "")[:10] for a in assertions]
    stamps = [s for s in stamps if s]
    return min(stamps) if stamps else None


# Config constants the ARMING predicates read. Two variants sharing all of
# these plus both lane modes provably arm identically, so the (expensive)
# rolling-window arming computation is shared between them.
ARMING_CONFIG_KEYS = (
    "H7A_DRAWDOWN_MIN", "H7A_RECLAIM_LOOKBACK_D", "H7_DD_LOOKBACK_D",
    "H7B_RANGE_MAX", "H7B_RANGE_LOOKBACK_D", "H7B_RV_PCTILE_MAX",
    "H7B_RV_WINDOW_D", "H7B_RV_HISTORY_D", "H7B_RV_MIN_HISTORY_D",
)


def arming_signature(variant: Variant) -> tuple:
    """Identity of a variant's arming behaviour. MUST be read under ``applied``."""
    return (tuple(getattr(config, key) for key in ARMING_CONFIG_KEYS),
            variant.lane_a_mode, variant.lane_b_mode)


def _variant_symbols(variant: Variant, sessions_by_symbol: dict[str, list[str]]
                     ) -> list[str]:
    return [s for s in resolve_universe(variant.universe_label)
            if s in sessions_by_symbol]


def _tally_waterfall(waterfall: dict[str, int], card: dict, *, armed: bool) -> None:
    """Count the FIRST blocking condition per lane-day (frozen states only)."""
    for lane in ("lane_a", "lane_b", "lane_c"):
        state = card[lane]["state"]
        if state in ("EARNINGS-UNKNOWN", "EARNINGS-BAN"):
            bucket = "earnings_gate"
        elif state == "EXCLUDED":
            bucket = "lane_excluded_by_design"
        elif state == "WATCH-ONLY":
            bucket = "liquidity_admission"
        elif state == "QUIET":
            bucket = "arming_rule" if not armed else "iv_rv_route"
        elif state in ("BASKET-CAP", "BUDGET-SPENT"):
            bucket = "portfolio_caps"
        elif state == "NO-EXECUTABLE":
            bucket = "no_executable_structure"
        elif state == "ENTRY-OK":
            bucket = "entry_ok_pre_board"
        else:
            bucket = f"other:{state}"
        waterfall[bucket] = waterfall.get(bucket, 0) + 1


@lru_cache(maxsize=None)
def resolve_universe(label: str) -> tuple[str, ...]:
    """Name lists a variant may select. No provider calls, no new names."""
    if label == "official_scope_15":
        return tuple(sorted(watch_universe()))
    if label == "registered_cohort_9":
        return tuple(sorted(load_registered_cohort().included))
    raise ValueError(f"unknown universe label {label!r}")


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------

def summarize_variant(*, variant: Variant, panel_id: str, panel_sessions: list[str],
                      sessions_by_symbol: dict[str, list[str]],
                      entry_rows: list[dict], error_rows: list[dict],
                      window_sessions: int, code_sha: str,
                      baseline_config_hash: str,
                      input_files: dict) -> dict:
    """Build the frequency-only receipt for one variant on one panel."""
    symbols = [s for s in resolve_universe(variant.universe_label)
               if s in sessions_by_symbol]
    symbol_days = sum(len(sessions_by_symbol[s]) for s in symbols)
    if symbol_days <= 0:
        raise ValueError(f"{variant.variant_id}/{panel_id}: empty panel")
    passes = len(entry_rows)
    base_rate = passes / symbol_days
    low, high = clopper_pearson(passes, symbol_days)
    projection = window_sessions * len(symbols)
    per_name: dict[str, int] = {s: 0 for s in symbols}
    for row in entry_rows:
        per_name[row["symbol"]] = per_name.get(row["symbol"], 0) + 1
    per_lane: dict[str, int] = {}
    for row in entry_rows:
        per_lane[row["lane"]] = per_lane.get(row["lane"], 0) + 1
    top_share = (max(per_name.values()) / passes) if passes else 0.0

    receipt = {
        "receipt_kind": RECEIPT_KIND,
        "provenance": "LLM/tool-computed",
        "tool_label": (
            "cached-only read-only ENTRY-FREQUENCY measurement; no verdict, "
            "no outcome statistics of any kind"
        ),
        "integrity_rule": (
            "brief 09: frequency only. No P&L, win rate, premium capture or any "
            "outcome statistic is computed, stored or reported for any variant."
        ),
        "variant": variant.identity(),
        "variant_identity_hash": variant.identity_hash(),
        "baseline_stack_version": BASELINE_STACK_VERSION,
        "panel_id": panel_id,
        "panel_start": panel_sessions[0],
        "panel_end": panel_sessions[-1],
        "panel_sessions": len(panel_sessions),
        "universe": symbols,
        "universe_size": len(symbols),
        "sessions_per_symbol": {s: len(sessions_by_symbol[s]) for s in symbols},
        "symbol_days": symbol_days,
        "entry_symbol_days": passes,
        "base_rate": base_rate,
        "base_rate_ci95_exact": {"low": low, "high": high,
                                 "method": "Clopper-Pearson"},
        "window_sessions": window_sessions,
        "expected_entries_per_window": base_rate * projection,
        "expected_entries_ci95_exact": {"low": low * projection,
                                        "high": high * projection},
        "feasibility_entry_bar": FEASIBILITY_ENTRY_BAR,
        "clears_bar_ci_lower_ge_bar": bool(low * projection >= FEASIBILITY_ENTRY_BAR),
        "point_estimate_ge_bar": bool(base_rate * projection >= FEASIBILITY_ENTRY_BAR),
        "entries_per_symbol": per_name,
        "entries_per_lane": per_lane,
        "top_symbol_share": top_share,
        "rolling_window_entry_counts": rolling_window_counts(
            [row["session"] for row in entry_rows], panel_sessions, window_sessions),
        "occupancy_constrained_entries": {
            str(lockout): occupancy_constrained_count(
                entry_rows, panel_sessions, lockout)
            for lockout in OCCUPANCY_LOCKOUT_SESSIONS
        },
        "occupancy_note": (
            "entries surviving one-open-position-per-underlying for N sessions. "
            "The headline count assumes a flat book every session, which no live "
            "window can reproduce; these are the same entries replayed through the "
            "registered position cap. Schedule arithmetic only -- no price path, no "
            "outcome. Still an upper bound (the monthly sleeve is not netted)."
        ),
        "entry_symbol_day_rows": sorted(
            entry_rows, key=lambda r: (r["session"], r["symbol"], r["lane"])),
        "data_gap_rows": sorted(
            error_rows, key=lambda r: (r["session"], r["symbol"])),
        "data_gap_count": len(error_rows),
        "code_sha": code_sha,
        "baseline_config_hash": baseline_config_hash,
        "input_files": input_files,
        "method": {
            "signal_and_execution": "options_researcher.h7_watch.assemble_name",
            "allocation": ("tools.h7_entry_variant_menu.resolve_board_multi_lane"
                           if variant.board_policy == BOARD_MULTI_LANE
                           else "options_researcher.h7_board.resolve_board"),
            "data": "cached .cache/chains plus .cache/underlying only; no provider calls",
            "causality": (
                "each decision session uses closes sliced to [session-560d, session] "
                "and that session's exact cached chain; earnings knowledge is cut at "
                "session_close_utc(session)"
            ),
            "error_policy": (
                "unavailable symbol-day counts in the denominator and cannot enter"
            ),
            "portfolio_state_assumption": (
                "each historical session starts with no open H7 positions and the full "
                "frozen monthly sleeve; same-session board caps apply. This INFLATES "
                "counts relative to live operation, where an open position blocks its "
                "underlying for the whole holding period."
            ),
            "measurement_bias_disclosure": (
                "B4: measured on ThetaData EOD chains; the forward window would run on "
                "Schwab 15:45 pre-close data. Every known simplification inflates "
                "counts (see the menu report for direction-by-simplification)."
            ),
            "frozen_realism_constants": sorted(FORBIDDEN_OVERRIDE_KEYS),
        },
    }
    receipt["receipt_hash"] = _receipt_hash(receipt)
    return receipt


def summarize_arming(*, variant: Variant, panel_id: str, panel_sessions: list[str],
                     sessions_by_symbol: dict[str, list[str]],
                     armed_rows: list[dict], error_rows: list[dict],
                     window_sessions: int, code_sha: str,
                     baseline_config_hash: str,
                     coverage_floor: str | None) -> dict:
    """Long-history ARMING census: how often the technical trigger fires.

    This is deliberately NOT an entry rate. It is the upper bound the entry
    stack is drawn from, and the only frequency statistic that can honestly be
    measured across the full cached history (see ``earnings_coverage_floor``).
    """
    symbols = [s for s in resolve_universe(variant.universe_label)
               if s in sessions_by_symbol]
    symbol_days = sum(len(sessions_by_symbol[s]) for s in symbols)
    if symbol_days <= 0:
        raise ValueError(f"{variant.variant_id}/{panel_id}: empty panel")
    armed = len(armed_rows)
    rate = armed / symbol_days
    low, high = clopper_pearson(armed, symbol_days)
    projection = window_sessions * len(symbols)
    per_name: dict[str, int] = {s: 0 for s in symbols}
    for row in armed_rows:
        per_name[row["symbol"]] = per_name.get(row["symbol"], 0) + 1
    receipt = {
        "receipt_kind": "h7_entry_arming_frequency/v1",
        "provenance": "LLM/tool-computed",
        "tool_label": (
            "cached-only read-only ARMING-frequency census; no verdict, no "
            "outcome statistics of any kind"
        ),
        "what_this_is_not": (
            "NOT an entry rate. Arming is the technical trigger only; the "
            "earnings gate, liquidity admission, IV/RV routing, executable "
            "structure and board allocation all still have to pass afterwards."
        ),
        "why_arming_only": (
            "the frozen earnings gate fails closed to UNKNOWN when no assertion "
            f"was knowable at the session; the earliest knowable assertion is "
            f"{coverage_floor}, so a longer FULL-STACK panel would measure "
            "earnings-data coverage rather than entry frequency"
        ),
        "earnings_assertion_coverage_floor": coverage_floor,
        "variant": variant.identity(),
        "variant_identity_hash": variant.identity_hash(),
        "panel_id": panel_id,
        "panel_start": panel_sessions[0],
        "panel_end": panel_sessions[-1],
        "panel_sessions": len(panel_sessions),
        "universe": symbols,
        "universe_size": len(symbols),
        "sessions_per_symbol": {s: len(sessions_by_symbol[s]) for s in symbols},
        "symbol_days": symbol_days,
        "armed_symbol_days": armed,
        "armed_rate": rate,
        "armed_rate_ci95_exact": {"low": low, "high": high,
                                  "method": "Clopper-Pearson"},
        "window_sessions": window_sessions,
        "armed_symbol_days_per_window": rate * projection,
        "armed_per_symbol": per_name,
        "armed_lane_a": sum(1 for r in armed_rows if r["lane_a"]),
        "armed_lane_b": sum(1 for r in armed_rows if r["lane_b"]),
        "rolling_window_armed_counts": rolling_window_counts(
            [row["session"] for row in armed_rows], panel_sessions, window_sessions),
        "data_gap_count": len(error_rows),
        "code_sha": code_sha,
        "baseline_config_hash": baseline_config_hash,
        "method": {
            "arming": ("options_researcher.h7_signals.lane_a_armed / lane_b_armed "
                       "under the variant's overrides"),
            "data": "cached .cache/underlying closes only; no chain read, no provider calls",
            "causality": "closes sliced to [session-560d, session] inclusive",
            "panel_axis": "sessions with an exact cached chain file (tradable days)",
        },
    }
    receipt["receipt_hash"] = _receipt_hash(receipt)
    return receipt


def _receipt_hash(receipt: dict) -> str:
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    return sha256_hex(canonical_json(unhashed))


def verify_receipt(receipt: dict) -> bool:
    return receipt.get("receipt_hash") == _receipt_hash(receipt)


def write_receipt(receipt: dict, path: Path) -> None:
    """Immutable, hash-verified, outcome-free write."""
    if not verify_receipt(receipt):
        raise ValueError("refusing to write a receipt with an invalid hash")
    assert_no_outcome_fields(receipt)
    text = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    path = Path(path)
    if path.exists():
        if path.read_text(encoding="utf-8") != text:
            raise FileExistsError(f"immutable variant receipt conflict: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_text_write(text, path)


def input_file_hashes(paths: dict[str, Path]) -> dict:
    """Bind inputs by their BYTES, via the repo's standard file hash.

    Text-mode hashing would silently normalise CRLF to LF -- assertions_v2.csv
    has 254 CRLF rows -- producing a digest that neither binds the real bytes
    nor matches the 2026-08-11 feasibility receipt it must be comparable to.
    """
    out = {}
    for label, path in sorted(paths.items()):
        out[label] = {"path": str(path), "sha256": sha256_file(Path(path))}
    return out


# ---------------------------------------------------------------------------
# The candidate menu
# ---------------------------------------------------------------------------

def build_variants() -> list[Variant]:
    """Every candidate measured. The COUNT matters: selecting the best of N on
    frequency is still a search over N, and the registration must disclose it.
    """
    return [
        Variant(
            variant_id="V0_BASELINE", axis="baseline",
            rule_change="The frozen H7 entry stack exactly as registered. No change.",
            rationale_drift=DRIFT_NONE),

        # --- axis 1: one signal threshold at a time -------------------------
        Variant(
            variant_id="V1_DRAWDOWN_15", axis="signal_threshold",
            rule_change=("Lane a arms after a 15% fall from the 52-week high instead "
                         "of 25%."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.15}),
        Variant(
            variant_id="V2_DRAWDOWN_10", axis="signal_threshold",
            rule_change=("Lane a arms after a 10% fall from the 52-week high instead "
                         "of 25%."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.10}),
        Variant(
            variant_id="V3_RANGE_20", axis="signal_threshold",
            rule_change=("Lane b accepts a 60-day price range up to 20% of spot "
                         "instead of 15%."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7B_RANGE_MAX": 0.20}),
        Variant(
            variant_id="V4_RVPCTILE_40", axis="signal_threshold",
            rule_change=("Lane b accepts realized vol in the quietest 40% of its own "
                         "year instead of the quietest 25%."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7B_RV_PCTILE_MAX": 0.40}),
        Variant(
            variant_id="V5_CLOSE_ROUTE_DEADZONE", axis="signal_threshold",
            rule_change=("Close the routing dead zone: today an option priced between "
                         "1.15x and 1.25x realized vol is routed nowhere and the day "
                         "is skipped. This routes it to the debit spread."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7_IV_PAR_K": 1.25}),
        Variant(
            variant_id="V6_ADMIT_3", axis="signal_threshold",
            rule_change=("Require 3 near-the-money monthly contracts to pass the "
                         "breadth check instead of 5. Per-contract open-interest and "
                         "spread caps are UNCHANGED."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7_ADMIT_MIN_CONTRACTS": 3}),
        Variant(
            variant_id="V7_DELTA_TOL_10", axis="signal_threshold",
            rule_change=("Accept strikes within 0.10 of each registered delta target "
                         "instead of 0.07."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7_DELTA_TOLERANCE": 0.10}),
        Variant(
            variant_id="V8_RECLAIM_10", axis="signal_threshold",
            rule_change=("The stabilisation trigger is a close above the prior 10-day "
                         "high instead of the prior 20-day high."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7A_RECLAIM_LOOKBACK_D": 10}),

        # --- axis 3: trigger logic ------------------------------------------
        Variant(
            variant_id="V9_LANE_A_OR", axis="trigger_logic",
            rule_change=("Lane a arms on a deep drawdown OR a 20-day-high reclaim, "
                         "instead of requiring both."),
            rationale_drift=DRIFT_HIGH, lane_a_mode=LANE_MODE_OR),
        Variant(
            variant_id="V10_LANE_B_OR", axis="trigger_logic",
            rule_change=("Lane b arms on a tight 60-day range OR quiet realized vol, "
                         "instead of requiring both."),
            rationale_drift=DRIFT_HIGH, lane_b_mode=LANE_MODE_OR),
        Variant(
            variant_id="V11_LANE_B_NO_EDGE", axis="trigger_logic",
            rule_change=("Lane b may fire on any session the coil conditions hold, "
                         "not only the first such session."),
            rationale_drift=DRIFT_LOW, lane_b_edge_trigger=False),

        # --- axis 4: evaluation cadence -------------------------------------
        Variant(
            variant_id="V12_MULTI_LANE", axis="evaluation_cadence",
            rule_change=("A name may take more than one setup shape in the same "
                         "session. The monthly risk cap and the lane-c concurrency "
                         "cap still bind."),
            rationale_drift=DRIFT_LOW, board_policy=BOARD_MULTI_LANE),
        Variant(
            variant_id="V13_H7C_CONCURRENT_2", axis="evaluation_cadence",
            rule_change=("Allow 2 concurrent short-premium positions basket-wide "
                         "instead of 1."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7C_MAX_CONCURRENT": 2}),

        # --- axis 2: universe ------------------------------------------------
        Variant(
            variant_id="V14_REGISTERED_COHORT_9", axis="universe",
            rule_change=("Restrict entries to the 9 names frozen into the registered "
                         "cohort (the other 6 were excluded for unknown earnings "
                         "dates at registration)."),
            rationale_drift=DRIFT_NONE, universe_label="registered_cohort_9"),

        # --- combinations -----------------------------------------------------
        Variant(
            variant_id="V15_COMBO_MILD", axis="combination",
            rule_change=("Mild combination: 15% drawdown + closed routing dead zone "
                         "+ lane b may re-fire + more than one shape per name."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.15, "H7_IV_PAR_K": 1.25},
            lane_b_edge_trigger=False, board_policy=BOARD_MULTI_LANE),
        Variant(
            variant_id="V16_COMBO_MEDIUM", axis="combination",
            rule_change=("Medium combination: 10% drawdown + 20% range + quietest 40% "
                         "RV + closed routing dead zone + 3-contract breadth + lane b "
                         "may re-fire + more than one shape per name."),
            rationale_drift=DRIFT_LOW,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.10, "H7B_RANGE_MAX": 0.20,
                              "H7B_RV_PCTILE_MAX": 0.40, "H7_IV_PAR_K": 1.25,
                              "H7_ADMIT_MIN_CONTRACTS": 3},
            lane_b_edge_trigger=False, board_policy=BOARD_MULTI_LANE),
        Variant(
            variant_id="V17_COMBO_WIDE", axis="combination",
            rule_change=("Wide combination: everything in the medium combination plus "
                         "both lanes arming on EITHER of their two conditions."),
            rationale_drift=DRIFT_HIGH,
            config_overrides={"H7A_DRAWDOWN_MIN": 0.10, "H7B_RANGE_MAX": 0.20,
                              "H7B_RV_PCTILE_MAX": 0.40, "H7_IV_PAR_K": 1.25,
                              "H7_ADMIT_MIN_CONTRACTS": 3},
            lane_a_mode=LANE_MODE_OR, lane_b_mode=LANE_MODE_OR,
            lane_b_edge_trigger=False, board_policy=BOARD_MULTI_LANE),
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _code_sha() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Measure candidate H7 entry-rule variants by FREQUENCY ONLY. "
                     "No outcome statistic is computed. No verdict is emitted."))
    parser.add_argument("--panel", choices=("comparable", "deep", "both"),
                        default="both",
                        help="comparable = full stack over the last 70 common sessions "
                             "(1,050 symbol-days, matches the 2026-08-11 receipt); "
                             "deep = ARMING census over all cached history per name "
                             "(the full stack is unevaluable before the earnings "
                             "panel's coverage floor)")
    parser.add_argument("--lookback-sessions", type=int, default=70)
    parser.add_argument("--window-sessions", type=int, default=70)
    parser.add_argument("--outdir", type=Path,
                        default=Path("reports/h7_forward_schwab/variant-receipts"))
    args = parser.parse_args(argv)

    variants = build_variants()
    data = PanelData()
    assertions = load_assertions()
    code_sha = _code_sha()
    baseline_config_hash = config_hash()
    inputs = input_file_hashes({
        "gating_assertions": Path("data/earnings/gating_v3.csv"),
        "raw_assertions": Path("data/earnings/assertions_v2.csv"),
    })
    scope = sorted(watch_universe())

    coverage_floor = earnings_coverage_floor(assertions)

    if args.panel in ("comparable", "both"):
        sessions = common_sessions(scope, data, limit=args.lookback_sessions)
        if len(sessions) < args.lookback_sessions:
            raise RuntimeError(f"only {len(sessions)} common cached sessions")
        sessions_by_symbol = {s: list(sessions) for s in scope}
        panel_id = "comparable_70_common"
        print(f"[{panel_id}] full stack; sessions={len(sessions)} "
              f"symbol_days={len(sessions) * len(scope)}")
        result = measure_variants(
            variants=variants, sessions_by_symbol=sessions_by_symbol, data=data,
            assertions=assertions, collect_waterfall_for="V0_BASELINE")
        for variant in variants:
            receipt = summarize_variant(
                variant=variant, panel_id=panel_id, panel_sessions=sessions,
                sessions_by_symbol=sessions_by_symbol,
                entry_rows=result["entries"][variant.variant_id],
                error_rows=result["errors"][variant.variant_id],
                window_sessions=args.window_sessions, code_sha=code_sha,
                baseline_config_hash=baseline_config_hash, input_files=inputs)
            write_receipt(receipt, Path(args.outdir) / panel_id
                          / f"{variant.variant_id}.json")
            print(f"  {variant.variant_id:26s} "
                  f"entries={receipt['entry_symbol_days']:4d}/"
                  f"{receipt['symbol_days']:6d} "
                  f"expected={receipt['expected_entries_per_window']:8.2f} "
                  f"CI=[{receipt['expected_entries_ci95_exact']['low']:7.2f},"
                  f"{receipt['expected_entries_ci95_exact']['high']:8.2f}] "
                  f"clears={receipt['clears_bar_ci_lower_ge_bar']}")
        wf = {"receipt_kind": "h7_entry_arming_waterfall/v1",
              "provenance": "LLM/tool-computed",
              "panel_id": panel_id,
              "variant_id": "V0_BASELINE",
              "note": ("first blocking condition per lane-day in the FROZEN state "
                       "ladder order (open book, earnings, admission, arming/route, "
                       "caps, structure). Because the ladder short-circuits, a "
                       "lane-day attributed to an earlier gate might also have "
                       "failed a later one: these are first-blocker counts, not "
                       "independent attributions. Frequency diagnostic, no outcomes."),
              "lane_days_by_first_block": dict(sorted(result["waterfall"].items()))}
        wf["receipt_hash"] = _receipt_hash(wf)
        write_receipt(wf, Path(args.outdir) / panel_id / "_baseline_waterfall.json")
        print(f"  waterfall -> {Path(args.outdir) / panel_id}")

    if args.panel in ("deep", "both"):
        ragged = ragged_sessions(scope, data)
        axis = sorted({s for days in ragged.values() for s in days})
        panel_id = "deep_arming_census"
        print(f"[{panel_id}] arming only (earnings coverage floor {coverage_floor}); "
              f"sessions={len(axis)} "
              f"symbol_days={sum(len(v) for v in ragged.values())}")
        result = measure_variants(
            variants=variants, sessions_by_symbol=ragged, data=data,
            assertions=assertions, arming_only=True)
        for variant in variants:
            receipt = summarize_arming(
                variant=variant, panel_id=panel_id, panel_sessions=axis,
                sessions_by_symbol=ragged,
                armed_rows=result["armed"][variant.variant_id],
                error_rows=result["errors"][variant.variant_id],
                window_sessions=args.window_sessions, code_sha=code_sha,
                baseline_config_hash=baseline_config_hash,
                coverage_floor=coverage_floor)
            write_receipt(receipt, Path(args.outdir) / panel_id
                          / f"{variant.variant_id}.json")
            roll = receipt["rolling_window_armed_counts"]
            print(f"  {variant.variant_id:26s} "
                  f"armed={receipt['armed_symbol_days']:5d}/"
                  f"{receipt['symbol_days']:6d} "
                  f"per70={receipt['armed_symbol_days_per_window']:8.2f} "
                  f"roll[min/med/max]={roll.get('min')}/{roll.get('median')}/"
                  f"{roll.get('max')}")

    print(f"variants measured: {len(variants)} "
          f"(multiple-testing count for the later registration)")
    print("NO PASS/FAIL DECISION EMITTED; NO OUTCOME STATISTIC COMPUTED; OWNER DECIDES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

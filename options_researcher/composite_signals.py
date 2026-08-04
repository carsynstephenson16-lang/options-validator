"""options_researcher/composite_signals.py -- composite signal lane.

DISPLAY-ONLY, cached-data-only, walk-forward confluence board. Renders four
INDEPENDENT signal angles per symbol as one card: TREND (direction), VOL
PREMIUM (is optionality rich or cheap), REGIME (what kind of market this is,
historically), and OPTIONS-MARKET INTERNALS (does the options market
corroborate). Design rationale + literature citations:
reports/2026-08-04-composite-signal-lane-decision.md (Part 3).

NOT a registered hypothesis. Nothing here gates, sizes, or triggers a trade;
this lane writes nothing to ledger/ or data/positions and is not FIRE-capable.
Every card carries its own max as-of session and never claims currency past
it. A missing or stale input renders its angle DATA_BLOCKED with a reason --
never silently skipped or guessed (fail-visible, mirroring the DATA_BLOCKED
convention already used across the attractiveness/top3/qm dashboards).

NO LOOK-AHEAD: every angle is computed from data with session <= the
requested `asof`. `confluence_card` truncates BOTH the closes series and the
chains mapping to `<= asof` before any angle function sees them, so passing
in extra future-dated rows can never change the result (see
tests/test_composite_signals.py's no-look-ahead invariance test).

Reuses, never reimplements: `options_researcher.features.build_daily_features`
for atm_iv/rv21/iv_minus_rv (near-tenor, 0.50-delta put, nearest monthly
15-60 DTE); `options_researcher.chains` for monthly-expiration selection and
ATM-by-delta lookup; `options_researcher.oi_change` for the ratified v1
signed-ΔOI taxonomy; `options_researcher.regime` for the walk-forward
Wasserstein regime labels; `data.thetadata_adapter.passes_liquidity` for the
frozen liquidity gates.

The confluence GRADE is a plain lexicographic COUNT of corroborating angles
(never a weighted average -- decision doc Part 3, citing Clemen 1989 and
DeMiguel, Garlappi & Uppal 2009 on why estimated weights lose to simple
structure). Grading never changes what an angle displays on the card; it
only tallies how many angles happen to agree with the established direction.
"""
from __future__ import annotations

import json
import math
import os
from collections.abc import Mapping, Sequence
from datetime import date, timedelta

import numpy as np
import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import atm_row, load_range, nearest_monthly
from options_researcher.features import build_daily_features
from options_researcher.oi_change import oi_change_fields
from options_researcher.regime import make_return_windows, walk_forward_labels

_NAN = float("nan")

# Per-session derived vol-premium/skew store (percentile-history cache). .tmp
# is gitignored scratch: rebuildable by construction from the chain cache,
# never a source of truth. See build_derived_series().
COMPOSITE_CACHE_DIR = os.path.join(".tmp", "composite_cache")
DERIVED_COLUMNS = ["atm_iv_near", "atm_iv_far", "rv", "gap", "skew_25d"]
DERIVED_METHOD_VERSION = "composite-derived-v1"

# Closes are one small parquet file per symbol (cheap to load in full); the
# chain cache is one file PER DAY, so build_board bounds that read to a
# generous calendar-day buffer over the ~378 trading sessions the percentile
# machinery wants, instead of loading the full multi-year cache.
_CLOSES_HISTORY_START = "2018-01-01"  # matches regime_report.CLOSE_HISTORY_START
_CHAIN_LOOKBACK_CALENDAR_DAYS = int(
    (config.COMPOSITE_PCTL_WINDOW + config.COMPOSITE_PCTL_MIN_OBS) * 1.6
)

DISPLAY_ONLY_NOTE = (
    "Display-only, non-verdict-bearing. Not FIRE-capable; writes nothing to "
    "ledger/ or data/positions. Grades are a lexicographic count of "
    "corroborating angles, never a weighted average -- see "
    "reports/2026-08-04-composite-signal-lane-decision.md."
)


# ---------------------------------------------------------------------------
# Blocked-angle constructors: every angle keeps a FIXED key set whether or
# not it renders, mirroring technicals.py's contract-testing convention
# (NaN/None/False in place of a real value, never a missing key).
# ---------------------------------------------------------------------------

def _blocked_trend(reason: str) -> dict:
    return {
        "state": "DATA_BLOCKED", "data_blocked": True, "reason": reason,
        "ema_slow": _NAN, "ema_medium": _NAN, "tsmom": _NAN,
        "vote_close_above_ema_slow": False, "vote_medium_above_slow": False,
        "vote_tsmom_positive": False, "aligned_votes": 0,
    }


def _blocked_vol_premium(reason: str, *, gap: float = _NAN,
                         term_slope: float = _NAN) -> dict:
    return {
        "state": "DATA_BLOCKED", "data_blocked": True, "reason": reason,
        "gap": gap, "gap_pctl": _NAN, "term_slope": term_slope,
        "structure_preference": None,
    }


def _blocked_regime(reason: str) -> dict:
    return {
        "state": "DATA_BLOCKED", "data_blocked": True, "reason": reason,
        "label": None, "label_frequency": _NAN, "high_dispersion": False,
        "size_context": "", "as_of": None,
    }


def _blocked_internals(reason: str) -> dict:
    return {
        "state": "DATA_BLOCKED", "data_blocked": True, "reason": reason,
        "oi_delta_call": None, "oi_delta_put": None,
        "oi_change_status_call": None, "oi_change_status_put": None,
        "direction_agreement": False,
        "skew_25d": _NAN, "skew_pctl": _NAN, "steep_skew": False,
        "liquidity_ok": False,
    }


# ---------------------------------------------------------------------------
# Angle 1 -- TREND
# ---------------------------------------------------------------------------

def trend_angle(closes: pd.Series) -> dict:
    """Direction, from two EMAs (pandas ewm, adjust=False) plus 12-1 month
    time-series momentum. Three boolean votes: close>ema_slow,
    ema_medium>ema_slow, tsmom>0. UP if 3/3, DOWN if 0/3, else MIXED.

    Insufficient history (< COMPOSITE_EMA_SLOW closes) -> DATA_BLOCKED. A
    series long enough for the EMAs but short of COMPOSITE_TSMOM_LOOKBACK+1
    still renders (ema votes are meaningful); tsmom degrades to NaN and its
    vote to False rather than raising -- so a partial-history series can
    reach MIXED/DOWN but never UP (UP needs all three votes, including a
    confirmed positive tsmom)."""
    closes = closes.astype(float)
    n = len(closes)
    if n < config.COMPOSITE_EMA_SLOW:
        return _blocked_trend(
            f"only {n} closes; need >= {config.COMPOSITE_EMA_SLOW} "
            "(COMPOSITE_EMA_SLOW) for a settled EMA read")

    ema_slow = float(
        closes.ewm(span=config.COMPOSITE_EMA_SLOW, adjust=False).mean().iloc[-1])
    ema_medium = float(
        closes.ewm(span=config.COMPOSITE_EMA_MEDIUM, adjust=False).mean().iloc[-1])
    px = float(closes.iloc[-1])

    if n >= config.COMPOSITE_TSMOM_LOOKBACK + 1:
        past = float(closes.iloc[-1 - config.COMPOSITE_TSMOM_LOOKBACK])
        recent = float(closes.iloc[-1 - config.COMPOSITE_TSMOM_SKIP])
        tsmom = (recent / past - 1.0) if past != 0.0 else _NAN
    else:
        tsmom = _NAN

    vote_close = px > ema_slow
    vote_medium = ema_medium > ema_slow
    vote_tsmom = bool(not math.isnan(tsmom) and tsmom > 0.0)
    aligned_votes = int(vote_close) + int(vote_medium) + int(vote_tsmom)
    if aligned_votes == 3:
        state = "UP"
    elif aligned_votes == 0:
        state = "DOWN"
    else:
        state = "MIXED"

    return {
        "state": state, "data_blocked": False, "reason": None,
        "ema_slow": ema_slow, "ema_medium": ema_medium, "tsmom": tsmom,
        "vote_close_above_ema_slow": vote_close,
        "vote_medium_above_slow": vote_medium,
        "vote_tsmom_positive": vote_tsmom,
        "aligned_votes": aligned_votes,
    }


# ---------------------------------------------------------------------------
# Angle 2 -- VOLATILITY PREMIUM
# ---------------------------------------------------------------------------

def _percentile_rank(history: pd.Series | None, value: float) -> float:
    """Inclusive-rank percentile of `value` in the trailing
    <=COMPOSITE_PCTL_WINDOW finite observations of `history` -- same
    convention as features.py's iv_rank. `value` must already be `history`'s
    own last observation (inclusive rank: today counts in its own window).
    NaN below COMPOSITE_PCTL_MIN_OBS finite observations."""
    if history is None or len(history) == 0:
        return _NAN
    window = [float(x) for x in history.tail(config.COMPOSITE_PCTL_WINDOW)
             if np.isfinite(x)]
    if not np.isfinite(value) or len(window) < config.COMPOSITE_PCTL_MIN_OBS:
        return _NAN
    return float(np.mean(np.asarray(window) <= value))


def vol_premium_angle(derived: pd.DataFrame | None) -> dict:
    """Is optionality rich or cheap? Headline: iv_minus_rv gap (near-tenor
    0.50-delta ATM IV minus 21d realized vol), reused from features.py, with
    a percentile of that gap vs its own trailing history. RICH if
    pctl >= COMPOSITE_RICH_PCTL, CHEAP if <= COMPOSITE_CHEAP_PCTL, else
    NEUTRAL. Secondary: term_slope = far ATM IV (61-120 DTE) minus near ATM
    IV (15-60 DTE), displayed with sign regardless of whether the percentile
    activates. Structure preference is a descriptive label, never an entry
    command: RICH -> credit-side, CHEAP -> debit-side, NEUTRAL -> either.

    `derived` is the per-session frame from build_derived_series (already
    truncated to <= asof by the caller); only the LAST row and the trailing
    window are read. Insufficient percentile history renders DATA_BLOCKED
    (distinct from a genuine NEUTRAL reading) but still surfaces `gap` and
    `term_slope` when those are independently available."""
    if derived is None or derived.empty:
        return _blocked_vol_premium(
            "no derived vol-premium series for this symbol/session")

    last = derived.iloc[-1]
    gap = float(last["gap"])
    near_iv = float(last["atm_iv_near"])
    far_iv = float(last["atm_iv_far"])
    term_slope = (far_iv - near_iv
                  if (math.isfinite(near_iv) and math.isfinite(far_iv))
                  else _NAN)

    if not math.isfinite(gap):
        return _blocked_vol_premium(
            "no usable ATM IV/RV for the as-of session", term_slope=term_slope)

    pctl = _percentile_rank(derived["gap"], gap)
    if math.isnan(pctl):
        return _blocked_vol_premium(
            "insufficient trailing gap history for a percentile (need >= "
            f"{config.COMPOSITE_PCTL_MIN_OBS} observations)",
            gap=gap, term_slope=term_slope)

    if pctl >= config.COMPOSITE_RICH_PCTL:
        state, structure = "RICH", "credit-side"
    elif pctl <= config.COMPOSITE_CHEAP_PCTL:
        state, structure = "CHEAP", "debit-side"
    else:
        state, structure = "NEUTRAL", "either"

    return {
        "state": state, "data_blocked": False, "reason": None,
        "gap": gap, "gap_pctl": pctl, "term_slope": term_slope,
        "structure_preference": structure,
    }


# ---------------------------------------------------------------------------
# Angle 3 -- REGIME
# ---------------------------------------------------------------------------

def regime_angle(closes: pd.Series) -> dict:
    """Current walk-forward Wasserstein regime label (options_researcher.
    regime), its historical frequency among all labeled sessions so far, and
    a descriptive (never predictive) size-context string. Regime labels are
    unsupervised historical descriptions of past return-window SHAPE, not a
    signed directional read -- see regime.py's own docstring. DATA_BLOCKED
    when there isn't yet enough causal walk-forward history to emit a label."""
    closes = closes.astype(float)
    min_rows = (config.REGIME_WINDOW_DAYS
                + config.REGIME_MIN_FIT_WINDOWS * config.REGIME_STEP_DAYS)
    if len(closes) < min_rows:
        return _blocked_regime(
            f"only {len(closes)} closes; need >= {min_rows} "
            "(REGIME_WINDOW_DAYS + REGIME_MIN_FIT_WINDOWS * REGIME_STEP_DAYS)")

    try:
        windows, end_dates = make_return_windows(
            closes, config.REGIME_WINDOW_DAYS, config.REGIME_STEP_DAYS)
        labeled = walk_forward_labels(
            windows, end_dates,
            n_clusters=config.REGIME_N_CLUSTERS,
            refit_every=config.REGIME_REFIT_EVERY,
            min_fit_windows=config.REGIME_MIN_FIT_WINDOWS,
            n_init=config.REGIME_N_INIT, seed=config.REGIME_SEED)
    except ValueError as exc:
        return _blocked_regime(f"walk-forward labeling failed: {exc}")

    labeled_rows = labeled.dropna(subset=["label"])
    if labeled_rows.empty:
        return _blocked_regime(
            "cached history produced no walk-forward label yet (fewer than "
            "REGIME_MIN_FIT_WINDOWS training windows)")

    latest = labeled_rows.iloc[-1]
    label = int(latest["label"])
    high_dispersion = bool(latest["high_dispersion"])
    label_frequency = float((labeled_rows["label"] == label).mean())
    size_context = (
        "historically elevated vol — smaller size context" if high_dispersion
        else "historically typical vol — normal size context")

    return {
        "state": "HIGH_DISPERSION" if high_dispersion else "TYPICAL",
        "data_blocked": False, "reason": None,
        "label": label, "label_frequency": label_frequency,
        "high_dispersion": high_dispersion, "size_context": size_context,
        "as_of": str(labeled_rows.index[-1])[:10],
    }


# ---------------------------------------------------------------------------
# Angle 4 -- OPTIONS-MARKET INTERNALS
# ---------------------------------------------------------------------------

def internals_angle(chain_today: pd.DataFrame | None,
                    chain_prior: pd.DataFrame | None,
                    trend_state: str,
                    *,
                    today: date,
                    prior_gap_days: int | None = None,
                    skew_history: pd.Series | None = None) -> dict:
    """Does the options market corroborate? (a) Signed 1-day ΔOI (ratified
    oi_change v1) on the near-tenor ATM (0.50-delta) call and put; direction
    agreement = sign(call ΔOI - put ΔOI) matches the trend direction (only
    meaningful when trend_state is UP or DOWN). (b) 25-delta skew (near
    tenor put IV - call IV) vs its own trailing history; steep-skew flag when
    its percentile >= COMPOSITE_RICH_PCTL (documented bearish-for-underlying
    context per Xing, Zhang & Zhao 2010). (c) liquidity health on both ATM
    reference contracts (frozen MIN_OPEN_INTEREST/MAX_SPREAD_PCT gates).

    State: VETO if liquidity fails; CONFIRM if liquidity passes AND OI
    direction agrees with trend AND NOT (steep-skew while trend UP); else
    NEUTRAL.

    Signature note (deviation from the literal 3-positional-arg brief
    description, documented in the implementation report): `today` is
    required to resolve the near-tenor monthly expiration and cannot be
    derived from the two chain frames alone; `prior_gap_days` and
    `skew_history` are optional keyword extensions the caller (confluence_
    card) already has in hand from resolving chain_today/chain_prior. Missing
    skew_history degrades steep_skew to False (fail-visible via skew_pctl
    staying NaN) rather than blocking the whole angle -- liquidity and OI
    direction remain valid signals on their own."""
    if chain_today is None or chain_today.empty:
        return _blocked_internals("no cached chain for the as-of session")

    near_exp = nearest_monthly(chain_today, today,
                               min_dte=config.COMPOSITE_TERM_NEAR_DTE[0],
                               max_dte=config.COMPOSITE_TERM_NEAR_DTE[1])
    if near_exp is None:
        return _blocked_internals(
            "no near-tenor monthly expiration in the COMPOSITE_TERM_NEAR_DTE band")

    atm_put = atm_row(chain_today, near_exp, right="P", target_delta=0.50)
    atm_call = atm_row(chain_today, near_exp, right="C", target_delta=0.50)
    if atm_put is None or atm_call is None:
        return _blocked_internals(
            "no ATM put/call reference contract on the near-tenor expiration")

    liquidity_ok = bool(
        passes_liquidity(float(atm_put["open_interest"]), float(atm_put["bid"]),
                         float(atm_put["ask"]))
        and passes_liquidity(float(atm_call["open_interest"]), float(atm_call["bid"]),
                             float(atm_call["ask"])))

    put_fields = oi_change_fields(
        chain_today, chain_prior, prior_gap_days,
        expiration=near_exp, strike=float(atm_put["strike"]), right="P")
    call_fields = oi_change_fields(
        chain_today, chain_prior, prior_gap_days,
        expiration=near_exp, strike=float(atm_call["strike"]), right="C")
    put_delta_oi = put_fields["oi_delta_1d"]
    call_delta_oi = call_fields["oi_delta_1d"]

    direction_agreement = False
    if (trend_state in ("UP", "DOWN")
            and put_delta_oi is not None and call_delta_oi is not None):
        diff = call_delta_oi - put_delta_oi
        direction_agreement = diff > 0 if trend_state == "UP" else diff < 0

    skew_put = atm_row(chain_today, near_exp, right="P",
                       target_delta=config.COMPOSITE_SKEW_DELTA)
    skew_call = atm_row(chain_today, near_exp, right="C",
                        target_delta=config.COMPOSITE_SKEW_DELTA)
    skew_25d = (float(skew_put["iv"]) - float(skew_call["iv"])
               if (skew_put is not None and skew_call is not None) else _NAN)
    skew_pctl = (_percentile_rank(skew_history, skew_25d)
                if skew_history is not None else _NAN)
    steep_skew = bool(not math.isnan(skew_pctl)
                      and skew_pctl >= config.COMPOSITE_RICH_PCTL)

    if not liquidity_ok:
        state = "VETO"
    elif direction_agreement and not (steep_skew and trend_state == "UP"):
        state = "CONFIRM"
    else:
        state = "NEUTRAL"

    return {
        "state": state, "data_blocked": False, "reason": None,
        "oi_delta_call": call_delta_oi, "oi_delta_put": put_delta_oi,
        "oi_change_status_call": call_fields["oi_change_status"],
        "oi_change_status_put": put_fields["oi_change_status"],
        "direction_agreement": direction_agreement,
        "skew_25d": skew_25d, "skew_pctl": skew_pctl, "steep_skew": steep_skew,
        "liquidity_ok": liquidity_ok,
    }


# ---------------------------------------------------------------------------
# Percentile-history store (Angle 2 gap + Angle 4 skew)
# ---------------------------------------------------------------------------

def _far_iv_and_skew(chain: pd.DataFrame, today: date) -> tuple[float, float]:
    """Far-tenor ATM IV (0.50-delta put) and near-tenor 25-delta skew for one
    cached chain day -- the two derived values features.build_daily_features
    does not already compute (it only covers the near-tenor 0.50-delta IV
    and RV)."""
    far_exp = nearest_monthly(chain, today,
                              min_dte=config.COMPOSITE_TERM_FAR_DTE[0],
                              max_dte=config.COMPOSITE_TERM_FAR_DTE[1])
    atm_iv_far = _NAN
    if far_exp is not None:
        row = atm_row(chain, far_exp, right="P", target_delta=0.50)
        if row is not None and float(row["iv"]) > 0:
            atm_iv_far = float(row["iv"])

    near_exp = nearest_monthly(chain, today,
                               min_dte=config.COMPOSITE_TERM_NEAR_DTE[0],
                               max_dte=config.COMPOSITE_TERM_NEAR_DTE[1])
    skew_25d = _NAN
    if near_exp is not None:
        skew_put = atm_row(chain, near_exp, right="P",
                           target_delta=config.COMPOSITE_SKEW_DELTA)
        skew_call = atm_row(chain, near_exp, right="C",
                            target_delta=config.COMPOSITE_SKEW_DELTA)
        if skew_put is not None and skew_call is not None:
            skew_25d = float(skew_put["iv"]) - float(skew_call["iv"])
    return atm_iv_far, skew_25d


def _write_derived_metadata(symbol: str, cache_dir: str, max_asof: str) -> None:
    meta_path = os.path.join(cache_dir, f"{symbol}.meta.json")
    payload = {"method_version": DERIVED_METHOD_VERSION, "max_asof": max_asof}
    with open(meta_path, "w") as fh:
        json.dump(payload, fh)


def build_derived_series(symbol: str, *, closes: pd.Series,
                         chains: Mapping[str, pd.DataFrame], asof: str,
                         cache_dir: str = COMPOSITE_CACHE_DIR) -> pd.DataFrame:
    """Walk-forward per-session [atm_iv_near, atm_iv_far, rv, gap, skew_25d]
    frame (index: session ISO date, ascending) through `asof`, persisted
    incrementally to {cache_dir}/{symbol}.parquet plus a
    {cache_dir}/{symbol}.meta.json sidecar recording DERIVED_METHOD_VERSION
    and the max session actually stored. `.tmp/composite_cache` is gitignored
    scratch, rebuildable by construction from the chain cache -- never a
    source of truth.

    INCREMENTAL: only chain days in `chains` that are <= asof and not already
    stored are computed on each call; existing stored rows are never
    recomputed or overwritten. NO LOOK-AHEAD: a session's rv/gap/skew use
    only that session's own cached chain plus trailing closes up to and
    including that session (rv21/atm_iv are reused unmodified from
    features.build_daily_features, which is itself already causal).

    `closes` and `chains` are read as given -- the CALLER truncates to
    `<= asof` (confluence_card does this); passing extra future-dated rows
    is harmless here too since every read is bounded to `<= asof` below, but
    callers should not rely on that as their only guard."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{symbol}.parquet")
    if os.path.exists(path):
        existing = pd.read_parquet(path).set_index("session")
    else:
        # An explicit empty object-dtype index (not the default empty
        # RangeIndex) so `existing.index <= asof` below can compare against
        # ISO-date strings even when nothing has been persisted yet.
        existing = pd.DataFrame(
            columns=DERIVED_COLUMNS, dtype=float,
            index=pd.Index([], dtype=object, name="session"))

    available_days = sorted(d for d in chains if d <= asof)
    missing_days: list[str] = []
    if available_days:
        lookback = config.COMPOSITE_PCTL_WINDOW + config.COMPOSITE_PCTL_MIN_OBS
        wanted_days = (available_days[-lookback:]
                      if len(available_days) > lookback else available_days)
        missing_days = [d for d in wanted_days if d not in existing.index]

    if missing_days:
        start_iso, end_iso = min(missing_days), max(missing_days)
        near_frame = build_daily_features(
            symbol, start_iso, end_iso, closes=closes,
            chains={d: chains[d] for d in missing_days}, earnings=[])
        new_rows: dict[str, dict[str, float]] = {}
        for day in missing_days:
            if day not in near_frame.index:
                continue
            far_iv, skew_25d = _far_iv_and_skew(chains[day], date.fromisoformat(day))
            new_rows[day] = {
                "atm_iv_near": float(near_frame.loc[day, "atm_iv"]),
                "atm_iv_far": far_iv,
                "rv": float(near_frame.loc[day, "rv21"]),
                "gap": float(near_frame.loc[day, "iv_minus_rv"]),
                "skew_25d": skew_25d,
            }
        if new_rows:
            new_frame = pd.DataFrame.from_dict(new_rows, orient="index")
            new_frame.index.name = "session"
            existing = pd.concat([existing, new_frame]).sort_index()
            existing = existing[~existing.index.duplicated(keep="last")]
            existing.reset_index().to_parquet(path)
            _write_derived_metadata(symbol, cache_dir, str(existing.index[-1]))

    return existing.loc[existing.index <= asof].sort_index()


# ---------------------------------------------------------------------------
# Composition -- the confluence card
# ---------------------------------------------------------------------------

def aligned_count(trend: dict, vol_premium: dict, regime: dict,
                  internals: dict) -> int:
    """How many of the four angles corroborate the established trend
    direction -- a plain COUNT feeding the grade, never a weighted average
    (decision doc Part 3). Each angle stays independently displayed on the
    card regardless of this count.

    A trend with no real direction (MIXED or DATA_BLOCKED) has nothing for
    any other angle to align with, so the count is 0 in that case by
    construction. Otherwise:
      - TREND contributes 1 for itself (it defines the direction).
      - VOL_PREMIUM contributes when CHEAP: cheap optionality does not
        structurally fight a directional read; RICH is read as elevated
        uncertainty and does not corroborate. NEUTRAL never contributes.
      - REGIME contributes when the current label is NOT the walk-forward
        high-dispersion regime: a calmer historical regime corroborates
        confidence in the trend read, while a high-dispersion regime is
        explicitly a lower-conviction "smaller size context" (decision doc
        Part 3, Angle 3).
      - INTERNALS contributes exactly when its own state is CONFIRM, which
        is already defined as liquidity-pass + OI-direction-agreement + no
        steep-skew-while-UP contradiction.
    """
    if trend.get("data_blocked") or trend.get("state") not in ("UP", "DOWN"):
        return 0
    count = 1
    if not vol_premium.get("data_blocked") and vol_premium.get("state") == "CHEAP":
        count += 1
    if not regime.get("data_blocked") and regime.get("high_dispersion") is False:
        count += 1
    if not internals.get("data_blocked") and internals.get("state") == "CONFIRM":
        count += 1
    return count


def confluence_grade(trend: dict, vol_premium: dict, regime: dict,
                     internals: dict) -> tuple[str, int]:
    """(grade, aligned_count) from four already-computed angle dicts. Grade
    A needs a real trend direction AND aligned_count >= COMPOSITE_GRADE_A_
    MIN_ALIGNED; grade B needs aligned_count >= COMPOSITE_GRADE_B_MIN_ALIGNED;
    else C. An INTERNALS VETO always caps the grade at C, regardless of how
    many other angles align."""
    count = aligned_count(trend, vol_premium, regime, internals)
    has_direction = trend.get("state") in ("UP", "DOWN")
    if has_direction and count >= config.COMPOSITE_GRADE_A_MIN_ALIGNED:
        grade = "A"
    elif count >= config.COMPOSITE_GRADE_B_MIN_ALIGNED:
        grade = "B"
    else:
        grade = "C"
    if internals.get("state") == "VETO":
        grade = "C"
    return grade, count


def confluence_card(symbol: str, asof: str, *, closes: pd.Series,
                    chains: Mapping[str, pd.DataFrame],
                    cache_dir: str = COMPOSITE_CACHE_DIR) -> dict:
    """One symbol's four-angle confluence card as of `asof` (a cached
    session ISO date). NO LOOK-AHEAD: `closes` and `chains` are truncated to
    `<= asof` here, before any angle function runs, so extra future-dated
    rows in either input can never change the result.

    `max_asof` is the latest session any input actually reflects (bounded
    above by `asof`) -- distinct from the requested `asof` itself, so a
    caller can see when the freshest available data lagged the request."""
    closes_trunc = closes.astype(float).loc[:asof]
    chains_trunc = {d: c for d, c in chains.items() if d <= asof}

    trend = trend_angle(closes_trunc)

    derived = build_derived_series(
        symbol, closes=closes_trunc, chains=chains_trunc, asof=asof,
        cache_dir=cache_dir)
    derived = derived.loc[derived.index <= asof]
    vol_premium = vol_premium_angle(derived)

    regime = regime_angle(closes_trunc)

    chain_days = sorted(chains_trunc)
    chain_today_date = chain_days[-1] if chain_days else None
    chain_today = chains_trunc[chain_today_date] if chain_today_date else None
    prior_days = [d for d in chain_days if d < chain_today_date] if chain_today_date else []
    chain_prior_date = prior_days[-1] if prior_days else None
    chain_prior = chains_trunc[chain_prior_date] if chain_prior_date else None
    prior_gap_days = (
        (date.fromisoformat(chain_today_date) - date.fromisoformat(chain_prior_date)).days
        if chain_today_date and chain_prior_date else None)
    skew_history = derived["skew_25d"] if not derived.empty else None
    today_for_internals = (date.fromisoformat(chain_today_date)
                           if chain_today_date else date.fromisoformat(asof))
    internals = internals_angle(
        chain_today, chain_prior, trend["state"],
        today=today_for_internals, prior_gap_days=prior_gap_days,
        skew_history=skew_history)

    grade, count = confluence_grade(trend, vol_premium, regime, internals)

    candidate_dates = [d for d in (
        str(closes_trunc.index[-1])[:10] if len(closes_trunc) else None,
        chain_today_date,
    ) if d]
    max_asof = max(candidate_dates) if candidate_dates else asof

    return {
        "symbol": symbol, "asof": asof, "max_asof": max_asof,
        "grade": grade, "aligned_count": count,
        "trend": trend, "vol_premium": vol_premium,
        "regime": regime, "internals": internals,
    }


def _card_blocked(symbol: str, reason: str, *, asof: str | None = None) -> dict:
    """A fully-blocked card (e.g. no cached closes at all) with the SAME
    shape as confluence_card's output, so downstream renderers never need a
    special case."""
    return {
        "symbol": symbol, "asof": asof, "max_asof": asof,
        "grade": "C", "aligned_count": 0,
        "trend": _blocked_trend(reason),
        "vol_premium": _blocked_vol_premium(reason),
        "regime": _blocked_regime(reason),
        "internals": _blocked_internals(reason),
    }


def _today_ny_iso() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def build_board(symbols: Sequence[str] | None = None, *, asof: str | None = None,
                cache_dir: str = COMPOSITE_CACHE_DIR) -> list[dict]:
    """One confluence_card per symbol in `symbols` (default
    config.ATTRACTIVENESS_UNIVERSE -- the same display universe the
    attractiveness dashboard iterates) as of `asof` (default: today's NY
    date). Cached-data-only; no network. A symbol with no cached closes at
    all still appears on the board, DATA_BLOCKED with a reason (Part 1.3 of
    the decision doc: display needs honesty labels, not entry gates) -- it
    is never silently dropped."""
    symbols = (list(symbols) if symbols is not None
              else list(config.ATTRACTIVENESS_UNIVERSE))
    resolved_asof = asof or _today_ny_iso()
    chain_start = (date.fromisoformat(resolved_asof)
                  - timedelta(days=_CHAIN_LOOKBACK_CALENDAR_DAYS)).isoformat()

    from data.underlying_closes import load_closes_adjusted

    cards: list[dict] = []
    for symbol in symbols:
        try:
            closes = load_closes_adjusted(
                symbol, _CLOSES_HISTORY_START, resolved_asof, allow_oos=True)
        except FileNotFoundError as exc:
            cards.append(_card_blocked(
                symbol, f"no cached closes ({exc.__class__.__name__})",
                asof=resolved_asof))
            continue
        if closes.empty:
            cards.append(_card_blocked(
                symbol, "cached closes are empty", asof=resolved_asof))
            continue
        try:
            chains = load_range(symbol, chain_start, resolved_asof, allow_oos=True)
        except Exception as exc:  # fail-visible per name; one bad symbol must
                                  # never blank the whole board
            cards.append(_card_blocked(
                symbol, f"chain load failed ({exc.__class__.__name__}: {exc})",
                asof=resolved_asof))
            continue
        cards.append(confluence_card(
            symbol, resolved_asof, closes=closes, chains=chains,
            cache_dir=cache_dir))
    return cards


_GRADE_ORDER = {"A": 0, "B": 1, "C": 2}


def _sort_key(card: dict) -> tuple[int, str]:
    return (_GRADE_ORDER.get(card.get("grade"), 3), str(card.get("symbol", "")))


def render_board_text(cards: list[dict]) -> str:
    """Plain-text board sorted by grade then symbol."""
    header = (f"{'SYMBOL':<8}{'GRADE':<7}{'TREND':<9}{'VOL_PREM':<10}"
             f"{'REGIME':<16}{'INTERNALS':<11}{'AS-OF':<12}")
    lines = [header, "-" * len(header)]
    for card in sorted(cards, key=_sort_key):
        lines.append(
            f"{card['symbol']:<8}{card['grade']:<7}"
            f"{card['trend']['state']:<9}{card['vol_premium']['state']:<10}"
            f"{card['regime']['state']:<16}{card['internals']['state']:<11}"
            f"{card.get('max_asof') or '?':<12}")
    lines.append("")
    lines.append(DISPLAY_ONLY_NOTE)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(
        description="Composite signal lane board (display-only, cached-data-only)")
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--asof", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    cards = sorted(build_board(args.symbols, asof=args.asof), key=_sort_key)
    if args.json:
        print(_json.dumps(cards, indent=2, default=str))
    else:
        print(render_board_text(cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

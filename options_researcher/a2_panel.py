"""Pure local-cache construction for A2-v1; this module never fetches or writes."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Sequence, cast

import exchange_calendars as xcals
import pandas as pd

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.a2_battery import LANE_COMPONENTS, A2Outcome
from options_researcher.chains import is_monthly, nearest_monthly

A2_SIMULATED_BAR_TIME_UTC = "21:00:00+00:00"
A2_QUOTE_TIMESTAMP_TOLERANCE_SECONDS = 3_600


@dataclass(slots=True)
class A2Diagnostics:
    skips: Counter[str] = field(default_factory=Counter)
    max_as_of: str | None = None
    pmcc_status: str = "no data"
    selected_contracts: set[tuple[str, str, str]] = field(default_factory=set)
    # Definition 1.2's sole exemption from the t+1 rule: a breach discovered
    # on the expiration session itself resolves by settlement on that same
    # session.  This is a successful resolution path, not a skip, so it gets
    # its own counter (independent adversarial review 2026-08-30, F4).
    breach_on_expiry_settlements: int = 0
    # C1 (round-2 independent adversarial review 2026-08-30, finding F-F):
    # the breach-scan close-gap check used to increment a plain ``skips``
    # counter once per (symbol, day, contract-selection) call, so the same
    # underlying-close hole got recounted every time an overlapping scan
    # window crossed it, and it lived in ``skips`` even though nothing is
    # excluded by it.  A set of unique (symbol, session) pairs, surfaced on
    # its own field like ``breach_on_expiry_settlements``, fixes both.
    breach_scan_missing_close_sessions: set[tuple[str, str]] = field(default_factory=set)

    def skip(self, reason: str) -> None:
        self.skips[reason] += 1

    def note_breach_on_expiry_settlement(self) -> None:
        self.breach_on_expiry_settlements += 1

    def note_breach_scan_missing_close_session(self, symbol: str, session: str) -> None:
        self.breach_scan_missing_close_sessions.add((symbol, session))


_XNYS_CALENDAR_CACHE: xcals.ExchangeCalendar | None = None


def _xnys_calendar() -> xcals.ExchangeCalendar:
    global _XNYS_CALENDAR_CACHE
    if _XNYS_CALENDAR_CACHE is None:
        _XNYS_CALENDAR_CACHE = xcals.get_calendar("XNYS")
    return _XNYS_CALENDAR_CACHE


@dataclass(frozen=True, slots=True)
class A2AuditResult:
    checks: Mapping[int, tuple[str, ...]]
    verdict: str
    warnings: tuple[str, ...]


def _day(value: object) -> date:
    return date.fromisoformat(str(value))


def _finite_number(value: object) -> float | None:
    try:
        number = float(cast(str | float | int, value))
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _safe_day(value: object) -> date | None:
    try:
        return _day(value)
    except (TypeError, ValueError):
        return None


def _symbol(row: pd.Series) -> str:
    value = row.get("contract_symbol")
    strike = _finite_number(row.get("strike"))
    fallback = f"{strike:.8f}" if strike is not None else "invalid"
    return (
        value
        if isinstance(value, str) and value
        else f"{row['right']}:{row['expiration']}:{fallback}"
    )


def _stable(rows: pd.DataFrame, target: float) -> pd.Series | None:
    if rows.empty:
        return None
    rows = rows.copy()
    rows["_d"] = (rows.delta.abs() - target).abs()
    rows["_s"] = rows.apply(_symbol, axis=1)
    return rows.sort_values(["_d", "expiration", "strike", "right", "_s"], kind="stable").iloc[0]


def _base_rows(chain: pd.DataFrame, right: str | None = None) -> pd.DataFrame:
    required = {"expiration", "strike", "right", "bid", "ask", "open_interest", "delta"}
    if not isinstance(chain, pd.DataFrame) or not required.issubset(chain):
        return pd.DataFrame()
    rows = chain.copy()
    for column in ("strike", "bid", "ask", "open_interest", "delta"):
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    mask = rows.expiration.map(_safe_day).notna() & rows.apply(
        lambda row: _usable(row) and _finite_number(row.get("delta")) is not None,
        axis=1,
    )
    if right is not None:
        mask &= rows.right.astype(str).str.upper() == right
    return cast(pd.DataFrame, rows.loc[mask].copy())


def select_income_contract(chain: pd.DataFrame, as_of: str, *, right: str) -> pd.Series | None:
    """Select at t only: nearest monthly, registered income delta, stable ties."""
    rows = _base_rows(chain)
    expiry = nearest_monthly(rows, _day(as_of))
    if expiry is None:
        return None
    rows = cast(pd.DataFrame, rows.loc[rows.right.astype(str).str.upper() == right])
    rows = cast(pd.DataFrame, rows.loc[rows.expiration.astype(str) == expiry.isoformat()])
    rows = cast(
        pd.DataFrame,
        rows.loc[(rows.delta.abs() - config.H5_INCOME_DELTA).abs() <= config.H5_INCOME_DELTA_BAND],
    )
    return _stable(rows, config.H5_INCOME_DELTA)


def select_leaps_contract(chain: pd.DataFrame, as_of: str) -> pd.Series | None:
    # Reproduce only the approved selector locally so A2's contract tie order
    # is explicit; the shared presentation selector remains unchanged.
    today = _day(as_of)
    rows = _base_rows(chain, "C")
    rows["_expiry"] = rows.expiration.map(_day)
    rows["_dte"] = rows._expiry.map(lambda expiry: (expiry - today).days)
    rows = cast(
        pd.DataFrame,
        rows.loc[rows._dte.between(*config.H4_THESIS_DTE_BAND)],
    )
    rows = cast(
        pd.DataFrame,
        rows.loc[(rows.delta.abs() - config.H4_THESIS_DELTA).abs() <= config.H5_INCOME_DELTA_BAND],
    )
    if rows.empty:
        return None
    rows = rows.copy()
    rows["_tenor_distance"] = (rows._dte - 365).abs()
    rows["_delta_distance"] = (rows.delta.abs() - config.H4_THESIS_DELTA).abs()
    rows["_symbol"] = rows.apply(_symbol, axis=1)
    return rows.sort_values(
        ["_tenor_distance", "_delta_distance", "expiration", "strike", "right", "_symbol"],
        kind="stable",
    ).iloc[0]


def select_tactical_contract(chain: pd.DataFrame, as_of: str) -> pd.Series | None:
    rows = _base_rows(chain, "C")
    today = _day(as_of)
    rows["_expiry"] = rows.expiration.map(_day)
    expiries = sorted(
        expiry
        for expiry in rows._expiry.unique()
        if is_monthly(expiry) and 15 <= (expiry - today).days <= 60
    )
    if not expiries:
        return None
    rows = cast(pd.DataFrame, rows.loc[rows._expiry == expiries[0]])
    rows = cast(
        pd.DataFrame,
        rows.loc[
            (rows.delta.abs() - config.H4_TACTICAL_DELTA).abs() <= config.H5_INCOME_DELTA_BAND
        ],
    )
    return _stable(rows, config.H4_TACTICAL_DELTA)


def _usable(row: pd.Series | None) -> bool:
    if row is None:
        return False
    strike = _finite_number(row.get("strike"))
    open_interest = _finite_number(row.get("open_interest"))
    bid, ask = _finite_number(row.get("bid")), _finite_number(row.get("ask"))
    return (
        strike is not None
        and open_interest is not None
        and bid is not None
        and ask is not None
        and quote_valid(bid, ask)
        and passes_liquidity(open_interest, bid, ask)
    )


def _contract_row(chain: pd.DataFrame | None, contract: pd.Series) -> pd.Series | None:
    if chain is None or not isinstance(chain, pd.DataFrame):
        return None
    required = {"expiration", "strike", "right", "bid", "ask", "open_interest"}
    if not required.issubset(chain):
        return None
    strike = _finite_number(contract.get("strike"))
    if strike is None:
        return None
    strikes = cast(pd.Series, pd.to_numeric(chain.strike, errors="coerce"))
    finite_strikes = strikes.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    rows = chain[
        (chain.expiration.astype(str) == str(contract.expiration))
        & finite_strikes
        & (strikes == strike)
        & (chain.right.astype(str).str.upper() == str(contract.right).upper())
    ]
    if rows.empty:
        return None
    row = min((candidate for _, candidate in rows.iterrows()), key=_symbol)
    return row if _usable(row) else None


def _make(
    symbol: str,
    decision: str,
    entry_day: str,
    resolution: str,
    maximum_resolution: str,
    lane: str,
    arm: str,
    score: float,
    gross_dollars: float,
    commission: float,
    bidask: float,
    denominator: float,
    components: Mapping[str, float],
    provenance: Mapping[str, object],
) -> A2Outcome:
    # The modeled cost is the full adverse-fill friction plus every per-side
    # commission; ``bid_ask_cost`` is its explicitly reported subset.
    gross, cost = gross_dollars / denominator, (commission + bidask) / denominator
    return A2Outcome(
        symbol=symbol,
        decision_date=decision,
        entry_date=entry_day,
        resolution_date=resolution,
        maximum_resolution_date=maximum_resolution,
        lane=lane,
        arm=arm,
        score=score,
        gross_return=gross,
        modeled_cost=cost,
        bid_ask_cost=bidask / denominator,
        cost_adjusted_return=gross - cost,
        components=components,
        provenance=provenance,
    )


def _option_pnl(entry: pd.Series, exit: pd.Series, sell_first: bool) -> tuple[float, float]:
    first = adverse_sell(entry.bid) if sell_first else adverse_buy(entry.ask)
    second = adverse_buy(exit.ask) if sell_first else adverse_sell(exit.bid)
    entry_mid = (float(entry.bid) + float(entry.ask)) / 2
    exit_mid = (float(exit.bid) + float(exit.ask)) / 2
    pnl = ((first - second) if sell_first else (second - first)) * 100
    return pnl, (abs(first - entry_mid) + abs(second - exit_mid)) * 100


def _target_session(sessions: Sequence[str], entry_day: str, horizon: int) -> str | None:
    later = [day for day in sessions if day > entry_day]
    return later[horizon - 1] if len(later) >= horizon else None


def _tactical_d1(contract: pd.Series, spot: float, tau: float) -> float | None:
    """Invert N(d1)/phi(d1) from the entry chain's delta/gamma relation."""
    try:
        sigma, delta, gamma = float(contract.iv), float(contract.delta), float(contract.gamma)
        ratio = delta / (gamma * spot * sigma * math.sqrt(tau))
    except (TypeError, ValueError, OverflowError, ZeroDivisionError):
        return None
    if (
        not all(math.isfinite(value) for value in (sigma, delta, gamma, ratio))
        or sigma <= 0
        or gamma <= 0
        or ratio <= 0
    ):
        return None
    lo, hi = -10.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        phi = math.exp(-0.5 * mid * mid) / math.sqrt(2.0 * math.pi)
        value = 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0))) / phi
        if value < ratio:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _csp(
    symbol: str,
    decision: str,
    entry_day: str,
    contract: pd.Series,
    score: float,
    chains: Mapping[str, pd.DataFrame],
    raw: Mapping[str, float],
    diagnostics: A2Diagnostics,
    provenance: Mapping[str, object],
    rate: float | None,
) -> tuple[A2Outcome, ...] | None:
    if rate is None:
        diagnostics.skip("missing_matched_tenor_rate")
        return None
    expiry, strike, denom = (
        str(contract.expiration),
        float(contract.strike),
        float(contract.strike) * 100,
    )
    sessions, credit = sorted(raw), adverse_sell(contract.bid) * 100
    # F3 (independent adversarial review, 2026-08-30): the breach scan below
    # only ever sees sessions present in ``raw``.  A hole in the underlying
    # close series inside [entry_day, expiry] would otherwise resolve as
    # silently "unbreached" with no diagnostic.  This detects and counts the
    # gap; it does not change resolution behavior (no close is substituted).
    try:
        expected_scan_sessions = {
            stamp.date().isoformat()
            for stamp in _xnys_calendar().sessions_in_range(_day(entry_day), _day(expiry))
        }
    except ValueError:
        expected_scan_sessions = set()
    for _missing_session in sorted(expected_scan_sessions - set(raw)):
        diagnostics.note_breach_scan_missing_close_session(symbol, _missing_session)
    close21 = next(
        (d for d in sessions if d > entry_day and (_day(expiry) - _day(d)).days <= 21), expiry
    )
    breach = next(
        (day for day in sessions if entry_day <= day <= expiry and float(raw[day]) < strike),
        None,
    )
    # C4 (round-2 independent adversarial review 2026-08-30, finding F-I):
    # this used to be counted here, before it was known whether the position
    # survives all-arms-or-none below.  A breach-on-expiry note about a
    # position that gets dropped entirely (any other arm failed to resolve)
    # is not a real report-level settlement; the count is now taken from
    # this local flag only once the position is confirmed to survive.
    breach_settles_on_expiry = breach is not None and breach == expiry
    if breach is None or breach >= expiry:
        breach_exit = expiry
    else:
        candidate = next(
            (day for day in sessions if day > breach and (_day(expiry) - _day(day)).days <= 21),
            expiry,
        )
        breach_exit = expiry if candidate >= expiry else candidate
    fixed_target = _target_session(sessions, entry_day, config.A2_CSP_FIXED_HORIZON_SESSIONS)
    fixed = expiry if fixed_target is None or expiry <= fixed_target else fixed_target
    capture = expiry
    for candidate_day in sessions:
        if not entry_day < candidate_day < expiry:
            continue
        # F7e (independent adversarial review, 2026-08-30): named distinctly
        # from the breach-exit ``candidate`` date above -- this one is the
        # contract row (pd.Series), not a date.
        candidate_contract = _contract_row(chains.get(candidate_day), contract)
        if candidate_contract is None:
            continue
        diagnostics.selected_contracts.add((symbol, candidate_day, _symbol(candidate_contract)))
        if adverse_buy(candidate_contract.ask) * 100 <= credit / 2:
            capture = candidate_day
            break

    def resolve(
        day: str,
        arm: str,
        maximum_resolution: str,
        *,
        skip_prefix: str | None = None,
    ) -> A2Outcome | None:
        if day not in raw:
            diagnostics.skip("missing_raw_close")
            if skip_prefix is not None:
                diagnostics.skip(f"{skip_prefix}_missing_raw_close")
            return None
        settlement = day >= expiry
        quote = None if settlement else _contract_row(chains.get(day), contract)
        if not settlement and quote is None:
            diagnostics.skip("invalid_resolution_quote")
            if skip_prefix is not None:
                diagnostics.skip(f"{skip_prefix}_invalid_resolution_quote")
            return None
        if quote is not None:
            diagnostics.selected_contracts.add((symbol, day, _symbol(quote)))
        if settlement:
            pnl = credit - max(strike - float(raw[day]), 0) * 100
            bidask = (
                abs(adverse_sell(contract.bid) - (float(contract.bid) + float(contract.ask)) / 2)
                * 100
            )
            commission = config.COMMISSION_PER_CONTRACT
        else:
            assert quote is not None
            pnl, bidask = _option_pnl(contract, quote, True)
            commission = 2 * config.COMMISSION_PER_CONTRACT
        components = {key: 0.0 for key in LANE_COMPONENTS["csp"]}
        calendar_days = (_day(day) - _day(entry_day)).days
        try:
            cash_forgone = denom * (math.exp(rate * calendar_days / 365.0) - 1.0)
        except OverflowError:
            diagnostics.skip("invalid_matched_tenor_rate")
            return None
        marks = [float(raw[session]) for session in sessions if entry_day <= session <= day]
        # Dollar loss per assigned 100-share lot, clamped at zero: favorable
        # marks cannot become a positive "adverse" component.
        max_adverse = min(0.0, min((mark - strike) * 100.0 for mark in marks)) if marks else 0.0
        # F7a (independent adversarial review, 2026-08-30): assignment is a
        # fact of expiration settlement below strike, not a fact of which
        # named arm is being reported -- any arm whose particular exit rule
        # happens to degenerate to expiration settlement is equally, factually
        # assigned.  ``pnl`` was already correct for every arm; only this
        # component breakdown was previously scoped to "assignment_accepting".
        assigned = (
            (float(raw[day]) - strike) * 100.0 if settlement and float(raw[day]) < strike else 0.0
        )
        components.update(
            option_pnl=pnl / denom,
            assigned_stock_result=assigned / denom,
            collateral_return=pnl / denom,
            cash_return_forgone=-cash_forgone / denom,
            max_adverse_excursion=max_adverse / denom,
            final_loss=min(pnl, 0) / denom,
        )
        return _make(
            symbol,
            decision,
            entry_day,
            day,
            maximum_resolution,
            "csp",
            arm,
            score,
            pnl,
            commission,
            bidask,
            denom,
            components,
            provenance,
        )

    rows = (
        resolve(capture, "capture_50", expiry),
        resolve(close21, "close_21_dte", close21),
        resolve(fixed, "fixed_10_sessions", fixed),
        resolve(
            breach_exit,
            "breach_hold_21_dte",
            expiry,
            skip_prefix=(
                "breach_hold_21_dte_breached"
                if breach is not None
                else "breach_hold_21_dte_unbreached"
            ),
        ),
        resolve(expiry, "assignment_accepting", expiry),
    )
    if not all(rows):
        return None
    if breach_settles_on_expiry:
        diagnostics.note_breach_on_expiry_settlement()
    return tuple(row for row in rows if row is not None)


def _long(
    symbol: str,
    decision: str,
    entry_day: str,
    contract: pd.Series,
    score: float,
    chains: Mapping[str, pd.DataFrame],
    raw: Mapping[str, float],
    lane: str,
    horizons: Sequence[int],
    diagnostics: A2Diagnostics,
    provenance: Mapping[str, object],
    adjusted: Mapping[str, float],
    features: Mapping[str, Mapping[str, Mapping[str, float]]] | None,
    earnings_assertions: Mapping[str, Sequence[str]] | None,
) -> tuple[A2Outcome, ...] | None:
    denom, sessions = adverse_buy(contract.ask) * 100, sorted(raw)
    rows: list[A2Outcome] = []
    for horizon in horizons:
        day = _target_session(sessions, entry_day, horizon)
        quote = _contract_row(chains.get(day) if day else None, contract)
        if day is None or quote is None:
            diagnostics.skip("invalid_resolution_quote")
            return None
        diagnostics.selected_contracts.add((symbol, day, _symbol(quote)))
        if entry_day not in adjusted or day not in adjusted:
            diagnostics.skip("missing_adjusted_close")
            return None
        pnl, bidask = _option_pnl(contract, quote, False)
        components = {key: 0.0 for key in LANE_COMPONENTS[lane]}
        if lane == "leaps":
            if any(column not in contract or column not in quote for column in ("iv", "vega")):
                diagnostics.skip("missing_leaps_greek_or_iv")
                return None
            try:
                entry_iv, exit_iv = float(contract.iv), float(quote.iv)
                entry_vega, entry_delta = float(contract.vega), float(contract.delta)
                entry_spot, exit_spot = float(raw[entry_day]), float(raw[day])
            except (TypeError, ValueError, OverflowError):
                diagnostics.skip("invalid_leaps_numeric_input")
                return None
            if not all(
                math.isfinite(value)
                for value in (entry_iv, exit_iv, entry_vega, entry_delta, entry_spot, exit_spot)
            ):
                diagnostics.skip("invalid_leaps_numeric_input")
                return None
            adjusted_marks = [
                float(adjusted[session])
                for session in sessions
                if entry_day <= session <= day and session in adjusted
            ]
            components["option_result"] = pnl / denom
            components["stock_result"] = (exit_spot - entry_spot) * 100 / denom
            components["delta_adjusted_stock_result"] = (
                entry_delta * (exit_spot - entry_spot) * 100 / denom
            )
            components["spread_cost"] = -bidask / denom
            components["vega_contribution"] = entry_vega * (exit_iv - entry_iv) / (denom / 100)
            assertions = (earnings_assertions or {}).get(symbol, ())
            components["earnings_exposure_count"] = float(
                sum(entry_day < str(event) <= day for event in assertions)
            )
            components["drawdown"] = (
                (min(adjusted_marks) - float(adjusted[entry_day])) * 100 / denom
            )
        else:
            required = ("iv", "vega", "theta", "gamma", "delta")
            if any(column not in contract or column not in quote for column in required):
                diagnostics.skip("missing_tactical_attribution_input")
                return None
            try:
                entry_spot, exit_spot = float(raw[entry_day]), float(raw[day])
                entry_iv, exit_iv = float(contract.iv), float(quote.iv)
                entry_delta, entry_gamma = float(contract.delta), float(contract.gamma)
                entry_theta, entry_vega = float(contract.theta), float(contract.vega)
            except (TypeError, ValueError, OverflowError):
                diagnostics.skip("invalid_tactical_attribution_input")
                return None
            values = (
                entry_spot,
                exit_spot,
                entry_iv,
                exit_iv,
                entry_delta,
                entry_gamma,
                entry_theta,
                entry_vega,
            )
            if not all(math.isfinite(value) for value in values):
                diagnostics.skip("invalid_tactical_attribution_input")
                return None
            ds = exit_spot - entry_spot
            d_sigma = exit_iv - entry_iv
            iv = entry_iv
            tau = max((_day(str(contract.expiration)) - _day(entry_day)).days / 365.0, 0.0)
            d1 = _tactical_d1(contract, entry_spot, tau) if tau > 0 else None
            if d1 is None:
                diagnostics.skip("invalid_tactical_delta_gamma_ratio")
                return None
            d2 = d1 - iv * math.sqrt(tau)
            numeric = (
                iv,
                d_sigma,
                d1,
                d2,
                entry_theta,
            )
            if not all(math.isfinite(value) for value in numeric) or iv <= 0:
                diagnostics.skip("invalid_tactical_iv")
                return None
            vanna = -entry_gamma * entry_spot * math.sqrt(tau) * d2
            volga = entry_vega * d1 * d2 / iv
            components["stock_price"] = entry_delta * ds * 100 / denom
            components["iv"] = entry_vega * d_sigma / (denom / 100)
            components["decay"] = entry_theta * (_day(day) - _day(entry_day)).days * 100 / denom
            components["cross_effects"] = (
                (
                    0.5 * entry_gamma * ds * ds
                    + 0.5 * volga * d_sigma * d_sigma
                    + vanna * ds * d_sigma
                )
                * 100
                / denom
            )
            components["spread_cost"] = -bidask / denom
            components["residual"] = pnl / denom - sum(components.values())
        rows.append(
            _make(
                symbol,
                decision,
                entry_day,
                day,
                day,
                lane,
                f"{horizon}_sessions",
                score,
                pnl,
                2 * config.COMMISSION_PER_CONTRACT,
                bidask,
                denom,
                components,
                provenance,
            )
        )
    return tuple(rows)


def _covered_call(
    symbol: str,
    decision: str,
    entry_day: str,
    contract: pd.Series,
    score: float,
    raw: Mapping[str, float],
    diagnostics: A2Diagnostics,
    provenance: Mapping[str, object],
) -> A2Outcome | None:
    """Same-close 100-share benchmark; assignment/lost-upside remain visible."""
    expiry, strike = str(contract.expiration), float(contract.strike)
    if expiry not in raw or entry_day not in raw:
        diagnostics.skip("missing_raw_close")
        return None
    entry_close, final_close = float(raw[entry_day]), float(raw[expiry])
    credit = adverse_sell(contract.bid) * 100
    intrinsic = max(final_close - strike, 0.0) * 100
    short_call = credit - intrinsic
    stock = (final_close - entry_close) * 100
    denominator = entry_close * 100
    bidask = abs(adverse_sell(contract.bid) - (float(contract.bid) + float(contract.ask)) / 2) * 100
    components = {key: 0.0 for key in LANE_COMPONENTS["covered_call"]}
    components.update(
        short_call_result=short_call / denominator,
        stock_result=stock / denominator,
        combined_result=(stock + short_call) / denominator,
        combined_minus_stock_only=short_call / denominator,
        assignment_incidence=float(final_close > strike),
        lost_upside=max(final_close - strike, 0) * 100 / denominator,
    )
    return _make(
        symbol,
        decision,
        entry_day,
        expiry,
        expiry,
        "covered_call",
        "covered_call",
        score,
        stock + short_call,
        config.COMMISSION_PER_CONTRACT,
        bidask,
        denominator,
        components,
        provenance,
    )


def build_historical_outcomes(
    *,
    signals: Mapping[str, Mapping[str, float]],
    chains: Mapping[str, Mapping[str, pd.DataFrame]],
    raw_closes: Mapping[str, Mapping[str, float]],
    adjusted_closes: Mapping[str, Mapping[str, float]],
    features: Mapping[str, Mapping[str, Mapping[str, float]]] | None = None,
    rates: Mapping[str, Mapping[str, float]] | None = None,
    earnings_assertions: Mapping[str, Sequence[str]] | None = None,
    positions: Mapping[str, object] | None = None,
    diagnostics: A2Diagnostics | None = None,
) -> tuple[A2Outcome, ...]:
    """Build typed rows from supplied local data; PMCC remains no-data absent recorded positions."""
    del positions
    diag, out = diagnostics or A2Diagnostics(), []
    for decision, board in sorted(signals.items()):
        for symbol, score in sorted(board.items()):
            if symbol not in config.ATTRACTIVENESS_UNIVERSE:
                diag.skip("outside_a2_universe")
                continue
            raw, chain_days = raw_closes.get(symbol, {}), chains.get(symbol, {})
            entry_days = [d for d in sorted(raw) if d > decision]
            if not entry_days or entry_days[0] not in chain_days:
                diag.skip("missing_entry_chain")
                continue
            entry_day = entry_days[0]
            if entry_day not in adjusted_closes.get(symbol, {}):
                diag.skip("missing_adjusted_close")
                continue
            chain, provenance = (
                chain_days[entry_day],
                {
                    "source": "local_cache",
                    "decision_chain_date": decision,
                    "entry_chain_date": entry_day,
                },
            )
            put = select_income_contract(chain, entry_day, right="P")
            if _usable(put):
                assert put is not None
                identity = _symbol(put)
                diag.selected_contracts.add((symbol, entry_day, identity))
                provenance = {**provenance, "contract_symbol": identity}
                raw_rate = (rates or {}).get(symbol, {}).get(entry_day)
                try:
                    rate = float(raw_rate) if raw_rate is not None else None
                except (TypeError, ValueError, OverflowError):
                    diag.skip("invalid_matched_tenor_rate")
                    continue
                if rate is not None and not math.isfinite(rate):
                    diag.skip("invalid_matched_tenor_rate")
                    continue
                rows = _csp(
                    symbol,
                    decision,
                    entry_day,
                    put,
                    float(score),
                    chain_days,
                    raw,
                    diag,
                    provenance,
                    rate,
                )
                if rows:
                    out.extend(rows)
            else:
                diag.skip("invalid_csp_entry")
            call = select_income_contract(chain, entry_day, right="C")
            if _usable(call):
                assert call is not None
                identity = _symbol(call)
                diag.selected_contracts.add((symbol, entry_day, identity))
                provenance = {**provenance, "contract_symbol": identity}
                row = _covered_call(
                    symbol, decision, entry_day, call, float(score), raw, diag, provenance
                )
                if row:
                    out.append(row)
            else:
                diag.skip("invalid_covered_call_entry")
            leaps = select_leaps_contract(chain, entry_day)
            if _usable(leaps):
                assert leaps is not None
                identity = _symbol(leaps)
                diag.selected_contracts.add((symbol, entry_day, identity))
                provenance = {**provenance, "contract_symbol": identity}
                rows = _long(
                    symbol,
                    decision,
                    entry_day,
                    leaps,
                    float(score),
                    chain_days,
                    raw,
                    "leaps",
                    config.A2_LEAPS_HORIZONS,
                    diag,
                    provenance,
                    adjusted_closes.get(symbol, {}),
                    features,
                    earnings_assertions,
                )
                if rows:
                    out.extend(rows)
            tactical = select_tactical_contract(chain, entry_day)
            if _usable(tactical):
                assert tactical is not None
                identity = _symbol(tactical)
                diag.selected_contracts.add((symbol, entry_day, identity))
                provenance = {**provenance, "contract_symbol": identity}
                rows = _long(
                    symbol,
                    decision,
                    entry_day,
                    tactical,
                    float(score),
                    chain_days,
                    raw,
                    "tactical_call",
                    config.A2_TACTICAL_HORIZONS,
                    diag,
                    provenance,
                    adjusted_closes.get(symbol, {}),
                    features,
                    earnings_assertions,
                )
                if rows:
                    out.extend(rows)
            diag.max_as_of = max(raw, default=diag.max_as_of)
    return tuple(out)


def audit_historical_inputs(
    *,
    chains: Mapping[str, Mapping[str, pd.DataFrame]],
    raw_closes: Mapping[str, Mapping[str, float]],
    selected_contracts: set[tuple[str, str, str]] | None = None,
    eligible_contracts: set[tuple[str, str, str]] | None = None,
    audit_start: str | None = None,
    audit_end: str | None = None,
    eligible_universe: set[str] | None = None,
) -> A2AuditResult:
    """Programmatic fourteen-check audit, with any selected-contract failure blocking."""
    selected = (selected_contracts or set()) | (eligible_contracts or set())
    checks = {n: [] for n in range(1, 15)}
    calendar = xcals.get_calendar("XNYS")
    for symbol, daily in chains.items():
        if eligible_universe is not None and symbol not in eligible_universe:
            continue
        observed = {_day(session) for session in daily}
        if observed:
            expected = {
                stamp.date() for stamp in calendar.sessions_in_range(min(observed), max(observed))
            }
            for missing in sorted(expected - observed):
                checks[1].append(f"{symbol} {missing}: missing XNYS session")
        expirations = sorted(
            expiry
            for chain in daily.values()
            if isinstance(chain, pd.DataFrame)
            for _, row in chain.iterrows()
            if (expiry := _safe_day(row.get("expiration"))) is not None
        )
        if audit_start is not None and audit_end is not None and expirations:
            checks[2].append(
                f"{symbol}: weekly cadence N/A for A2 monthly/explicit-expiry selectors"
            )
            start, end = _day(audit_start), _day(audit_end)
            weekly = [expiry for expiry in expirations if start <= expiry <= end]
            months = {(expiry.year, expiry.month) for expiry in weekly if is_monthly(expiry)}
            cursor = date(start.year, start.month, 1)
            while cursor <= end:
                if (cursor.year, cursor.month) not in months:
                    checks[2].append(f"{symbol} {cursor:%Y-%m}: monthly expiration cadence gap")
                cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        for session, chain in daily.items():
            if not isinstance(chain, pd.DataFrame) or chain.empty:
                checks[1].append(f"{symbol} {session}: missing chain")
                continue
            required = {"expiration", "strike", "right", "bid", "ask"}
            if not required.issubset(chain):
                checks[1].append(f"{symbol} {session}: missing columns")
                continue
            raw_close = raw_closes.get(symbol, {}).get(session)
            close = _finite_number(raw_close)
            if close is None:
                checks[13].append(f"{symbol} {session}: missing independent close")
            if "timestamp" not in chain:
                checks[9].append(f"{symbol} {session}: missing timestamp")
            if "volume" not in chain:
                checks[5].append(f"{symbol} {session}: volume metadata unavailable")
            if "underlying_price" not in chain:
                checks[13].append(f"{symbol} {session}: underlying_price metadata unavailable")
            session_day = _safe_day(session)
            if not any(
                expiry is not None and session_day is not None and expiry > session_day
                for _, row in chain.iterrows()
                if (expiry := _safe_day(row.get("expiration"))) is not None
            ):
                checks[2].append(f"{symbol} {session}: no reachable expiration")
            if (
                close is not None
                and close != 0
                and not any(
                    strike is not None and abs(strike - close) / abs(close) <= 0.10
                    for _, row in chain.iterrows()
                    if (strike := _finite_number(row.get("strike"))) is not None
                )
            ):
                checks[3].append(f"{symbol} {session}: no near-ATM strike")
            if chain.duplicated(["expiration", "strike", "right"], keep=False).any():
                checks[12].append(f"{symbol} {session}: duplicate contract")
            for _, row in chain.iterrows():
                tag = f"{symbol} {session} {_symbol(row)}"
                if selected and (symbol, session, _symbol(row)) not in selected:
                    continue
                strike = _finite_number(row.get("strike"))
                open_interest = _finite_number(row.get("open_interest"))
                bid, ask = _finite_number(row.get("bid")), _finite_number(row.get("ask"))
                if strike is None:
                    checks[3].append(tag)
                if open_interest is None:
                    checks[5].append(tag)
                if bid is None or ask is None:
                    checks[4].append(tag)
                if any(
                    (value := _finite_number(row.get(c))) is None or value < 0
                    for c in ("bid", "ask", "volume", "open_interest")
                    if c in row and row.get(c) is not None
                ):
                    checks[5].append(tag)
                if bid is not None and ask is not None and bid > ask:
                    checks[6].append(tag)
                if bid is not None and ask is not None and bid == 0 < ask:
                    checks[7].append(tag)
                if bid is not None and ask is not None:
                    mid = (bid + ask) / 2
                    if mid > 0 and (ask - bid) / mid > 0.20:
                        checks[8].append(tag)
                iv = _finite_number(row.get("iv"))
                if iv is None or not 0 < iv <= 5:
                    checks[10].append(tag)
                delta, gamma = _finite_number(row.get("delta")), _finite_number(row.get("gamma"))
                if (delta is not None and abs(delta) > 1) or (gamma is not None and gamma < 0):
                    checks[11].append(tag)
                expiration = _safe_day(row.get("expiration"))
                if expiration is None or expiration.weekday() >= 5:
                    checks[14].append(tag)
                if expiration is None or not calendar.is_session(expiration):
                    checks[14].append(tag)
                timestamp = row.get("timestamp")
                if timestamp is not None and pd.notna(timestamp):
                    try:
                        quote_stamp = pd.Timestamp(timestamp)
                        expected_stamp = pd.Timestamp(f"{session}T{A2_SIMULATED_BAR_TIME_UTC}")
                        if (
                            abs((quote_stamp - expected_stamp).total_seconds())
                            > A2_QUOTE_TIMESTAMP_TOLERANCE_SECONDS
                        ):
                            checks[9].append(tag)
                    except (TypeError, ValueError):
                        checks[9].append(tag)
                underlying = _finite_number(row.get("underlying_price"))
                if close is not None and underlying is not None and close != 0:
                    if abs(underlying - close) / abs(close) > 0.005:
                        checks[13].append(tag)
    warnings = tuple(f"check {n}: {x}" for n, rows in checks.items() for x in rows)
    selected_tags = {f"{symbol} {session} {contract}" for symbol, session, contract in selected}
    block = any(warning.partition(": ")[2] in selected_tags for warning in warnings)
    result = A2AuditResult(
        {n: tuple(rows) for n, rows in checks.items()},
        "BLOCK" if block else ("PASS WITH WARNINGS" if warnings else "PASS"),
        warnings,
    )
    for number in range(1, 15):
        print(f"A2 audit check {number}: {len(result.checks[number])} issue(s)")
    print(f"A2 audit verdict: {result.verdict}")
    return result


__all__ = [
    "A2AuditResult",
    "A2Diagnostics",
    "audit_historical_inputs",
    "build_historical_outcomes",
    "select_income_contract",
    "select_leaps_contract",
    "select_tactical_contract",
]

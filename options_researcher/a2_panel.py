"""Pure local-cache construction for A2-v1; this module never fetches or writes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Mapping, Sequence, cast

import pandas as pd

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.a2_battery import LANE_COMPONENTS, A2Outcome
from options_researcher.chains import is_monthly, nearest_monthly
from options_researcher.studies.long_call_carry import _leaps_candidate


@dataclass(slots=True)
class A2Diagnostics:
    skips: Counter[str] = field(default_factory=Counter)
    max_as_of: str | None = None
    pmcc_status: str = "no data"

    def skip(self, reason: str) -> None:
        self.skips[reason] += 1


@dataclass(frozen=True, slots=True)
class A2AuditResult:
    checks: Mapping[int, tuple[str, ...]]
    verdict: str
    warnings: tuple[str, ...]


def _day(value: object) -> date:
    return date.fromisoformat(str(value))


def _symbol(row: pd.Series) -> str:
    value = row.get("contract_symbol")
    return (
        value
        if isinstance(value, str) and value
        else f"{row['right']}:{row['expiration']}:{float(row['strike']):.8f}"
    )


def _stable(rows: pd.DataFrame, target: float) -> pd.Series | None:
    if rows.empty:
        return None
    rows = rows.copy()
    rows["_d"] = (rows.delta.abs() - target).abs()
    rows["_s"] = rows.apply(_symbol, axis=1)
    return rows.sort_values(["_d", "expiration", "strike", "right", "_s"], kind="stable").iloc[0]


def _base_rows(chain: pd.DataFrame, right: str) -> pd.DataFrame:
    required = {"expiration", "strike", "right", "bid", "ask", "open_interest", "delta"}
    if not isinstance(chain, pd.DataFrame) or not required.issubset(chain):
        return pd.DataFrame()
    mask = (chain.right.astype(str).str.upper() == right) & chain.apply(
        lambda row: quote_valid(row.bid, row.ask), axis=1
    )
    return cast(pd.DataFrame, chain.loc[mask].copy())


def select_income_contract(chain: pd.DataFrame, as_of: str, *, right: str) -> pd.Series | None:
    """Select at t only: nearest monthly, registered income delta, stable ties."""
    expiry = nearest_monthly(chain, _day(as_of))
    if expiry is None:
        return None
    rows = _base_rows(chain, right)
    rows = cast(pd.DataFrame, rows.loc[rows.expiration.astype(str) == expiry.isoformat()])
    rows = cast(
        pd.DataFrame,
        rows.loc[(rows.delta.abs() - config.H5_INCOME_DELTA).abs() <= config.H5_INCOME_DELTA_BAND],
    )
    return _stable(rows, config.H5_INCOME_DELTA)


def select_leaps_contract(chain: pd.DataFrame, as_of: str) -> pd.Series | None:
    row = _leaps_candidate(chain, _day(as_of), config.H4_THESIS_DELTA)
    return row if row is not None and quote_valid(row.bid, row.ask) else None


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
    return (
        row is not None
        and quote_valid(row.bid, row.ask)
        and passes_liquidity(row.open_interest, row.bid, row.ask)
    )


def _contract_row(chain: pd.DataFrame | None, contract: pd.Series) -> pd.Series | None:
    if chain is None or not isinstance(chain, pd.DataFrame):
        return None
    required = {"expiration", "strike", "right", "bid", "ask", "open_interest"}
    if not required.issubset(chain):
        return None
    rows = chain[
        (chain.expiration.astype(str) == str(contract.expiration))
        & (chain.strike.astype(float) == float(contract.strike))
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
) -> tuple[A2Outcome, ...] | None:
    expiry, strike, denom = (
        str(contract.expiration),
        float(contract.strike),
        float(contract.strike) * 100,
    )
    sessions, credit = sorted(raw), adverse_sell(contract.bid) * 100
    close21 = next(
        (d for d in sessions if d > entry_day and (_day(expiry) - _day(d)).days <= 21), expiry
    )
    fixed_target = _target_session(sessions, entry_day, config.A2_CSP_FIXED_HORIZON_SESSIONS)
    fixed = expiry if fixed_target is None or expiry <= fixed_target else fixed_target
    capture = next(
        (
            d
            for d in sessions
            if entry_day < d < expiry
            and (q := _contract_row(chains.get(d), contract)) is not None
            and adverse_buy(q.ask) * 100 <= credit / 2
        ),
        close21,
    )
    breach = next((d for d in sessions if entry_day < d < expiry and float(raw[d]) < strike), None)

    def resolve(day: str, arm: str) -> A2Outcome | None:
        if day not in raw:
            diagnostics.skip("missing_raw_close")
            return None
        settlement = day >= expiry
        quote = None if settlement else _contract_row(chains.get(day), contract)
        if not settlement and quote is None:
            diagnostics.skip("invalid_resolution_quote")
            return None
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
        components.update(
            option_pnl=pnl / denom,
            collateral_return=pnl / denom,
            final_loss=min(pnl, 0) / denom,
            tail_event_loss=min(pnl, 0) / denom,
        )
        if arm == "breach_hold_21_dte" and breach is not None:
            components["max_adverse_excursion"] = (
                (float(raw[breach]) - float(raw[entry_day])) * 100 / denom
            )
        return _make(
            symbol,
            decision,
            entry_day,
            day,
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
        resolve(capture, "capture_50"),
        resolve(close21, "close_21_dte"),
        resolve(fixed, "fixed_10_sessions"),
        resolve(close21, "breach_hold_21_dte"),
        resolve(expiry, "assignment_accepting"),
    )
    return tuple(row for row in rows if row is not None) if all(rows) else None


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
) -> tuple[A2Outcome, ...] | None:
    denom, sessions = adverse_buy(contract.ask) * 100, sorted(raw)
    rows: list[A2Outcome] = []
    for horizon in horizons:
        day = _target_session(sessions, entry_day, horizon)
        quote = _contract_row(chains.get(day) if day else None, contract)
        if day is None or quote is None:
            diagnostics.skip("invalid_resolution_quote")
            return None
        pnl, bidask = _option_pnl(contract, quote, False)
        components = {key: 0.0 for key in LANE_COMPONENTS[lane]}
        if lane == "leaps":
            components["option_result"] = pnl / denom
            components["stock_result"] = (float(raw[day]) - float(raw[entry_day])) * 100 / denom
        else:
            components["stock_price"] = (float(raw[day]) - float(raw[entry_day])) * 100 / denom
            components["spread_cost"] = -bidask / denom
            components["residual"] = pnl / denom - sum(components.values())
        rows.append(
            _make(
                symbol,
                decision,
                entry_day,
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
    stock = (min(final_close, strike) - entry_close) * 100
    benchmark = (final_close - entry_close) * 100
    denominator = entry_close * 100
    bidask = abs(adverse_sell(contract.bid) - (float(contract.bid) + float(contract.ask)) / 2) * 100
    components = {key: 0.0 for key in LANE_COMPONENTS["covered_call"]}
    components.update(
        short_call_result=credit / denominator,
        stock_result=stock / denominator,
        combined_result=(stock + credit) / denominator,
        combined_minus_stock_only=(stock + credit - benchmark) / denominator,
        assignment_incidence=float(final_close > strike),
        lost_upside=max(final_close - strike, 0) * 100 / denominator,
    )
    return _make(
        symbol,
        decision,
        entry_day,
        expiry,
        "covered_call",
        "covered_call",
        score,
        stock + credit,
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
    features: Mapping[str, object] | None = None,
    rates: Mapping[str, object] | None = None,
    earnings_assertions: Mapping[str, object] | None = None,
    positions: Mapping[str, object] | None = None,
    diagnostics: A2Diagnostics | None = None,
) -> tuple[A2Outcome, ...]:
    """Build typed rows from supplied local data; PMCC remains no-data absent recorded positions."""
    del features, rates, earnings_assertions, positions
    diag, out = diagnostics or A2Diagnostics(), []
    for decision, board in sorted(signals.items()):
        for symbol, score in sorted(board.items()):
            if symbol not in config.A2_UNIVERSE:
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
                )
                if rows:
                    out.extend(rows)
            else:
                diag.skip("invalid_csp_entry")
            call = select_income_contract(chain, entry_day, right="C")
            if _usable(call):
                assert call is not None
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
                )
                if rows:
                    out.extend(rows)
            tactical = select_tactical_contract(chain, entry_day)
            if _usable(tactical):
                assert tactical is not None
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
) -> A2AuditResult:
    """Programmatic fourteen-check audit, with any selected-contract failure blocking."""
    selected, checks = selected_contracts or set(), {n: [] for n in range(1, 15)}
    for symbol, daily in chains.items():
        for session, chain in daily.items():
            if not isinstance(chain, pd.DataFrame) or chain.empty:
                checks[1].append(f"{symbol} {session}: missing chain")
                continue
            required = {"expiration", "strike", "right", "bid", "ask"}
            if not required.issubset(chain):
                checks[1].append(f"{symbol} {session}: missing columns")
                continue
            if session not in raw_closes.get(symbol, {}):
                checks[13].append(f"{symbol} {session}: missing independent close")
            if "timestamp" not in chain:
                checks[9].append(f"{symbol} {session}: missing timestamp")
            if chain.empty:
                checks[2].append(f"{symbol} {session}: missing expirations")
            close = raw_closes.get(symbol, {}).get(session)
            if close is not None and not any(
                abs(float(row.strike) - float(close)) / float(close) <= 0.10
                for _, row in chain.iterrows()
            ):
                checks[3].append(f"{symbol} {session}: no near-ATM strike")
            if chain.duplicated(["expiration", "strike", "right"], keep=False).any():
                checks[12].append(f"{symbol} {session}: duplicate contract")
            for _, row in chain.iterrows():
                tag, bid, ask = f"{symbol} {session} {_symbol(row)}", row.bid, row.ask
                if pd.isna(bid) or pd.isna(ask):
                    checks[4].append(tag)
                if any(
                    pd.notna(row.get(c)) and float(row[c]) < 0
                    for c in ("bid", "ask", "open_interest")
                ):
                    checks[5].append(tag)
                if pd.notna(bid) and pd.notna(ask) and float(bid) > float(ask):
                    checks[6].append(tag)
                if pd.notna(bid) and pd.notna(ask) and float(bid) == 0 < float(ask):
                    checks[7].append(tag)
                mid = (float(bid) + float(ask)) / 2 if pd.notna(bid) and pd.notna(ask) else 0
                if mid > 0 and (float(ask) - float(bid)) / mid > 0.20:
                    checks[8].append(tag)
                iv = row.get("iv")
                if iv is None or pd.isna(iv) or not 0 < float(iv) <= 5:
                    checks[10].append(tag)
                delta, gamma = row.get("delta"), row.get("gamma")
                if (delta is not None and pd.notna(delta) and abs(float(delta)) > 1) or (
                    gamma is not None and pd.notna(gamma) and float(gamma) < 0
                ):
                    checks[11].append(tag)
                if _day(row.expiration).weekday() >= 5:
                    checks[14].append(tag)
    warnings = tuple(f"check {n}: {x}" for n, rows in checks.items() for x in rows)
    block = any(contract in warning for _, _, contract in selected for warning in warnings)
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

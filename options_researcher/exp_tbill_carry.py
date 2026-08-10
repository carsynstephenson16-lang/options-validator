"""Display-only EXP-TBILL carry comparison with assignment fail-closed.

The comparison annualizes the put's quote-mid credit on cash collateral and
compares it with the annually compounded yield implied by the repo's
point-in-time continuous Treasury rate.  Quote mid is display context only;
repo cost discipline requires real fills to be mid or worse.  This experiment
is descriptive, disabled by default, and has no ranking or verdict authority.
"""

from __future__ import annotations

import math
from datetime import date

import config
from data.rates import MissingRateError, risk_free_rate
from data.thetadata_adapter import CACHE_DIR
from data.underlying_closes import load_closes
from options_researcher.chains import atm_row, load_range, nearest_monthly

# PROVENANCE: LLM-proposed 2026-08-09, composite convention; display-only;
# not owner-ratified.
EXP_TBILL_TENOR_DTE = getattr(config, "EXP_TBILL_TENOR_DTE", (15, 60))
# PROVENANCE: LLM-proposed 2026-08-09, composite convention; display-only;
# not owner-ratified.
EXP_TBILL_TARGET_DELTA = getattr(config, "EXP_TBILL_TARGET_DELTA", 0.50)

_ASSIGNMENT_UNLOCK = "owner-sourced forward ex-dividend date calendar"
_CAVEAT = (
    "Display-only comparison using quote mid; real fills are mid or worse. "
    "Carry does not measure assignment probability or predict returns."
)
_PAYLOAD_KEYS = (
    "credit_mid",
    "collateral",
    "credit_annualized_yield",
    "tbill_annualized_yield",
    "carry_spread",
    "opportunity_cost",
    "rate_provenance",
)


def early_assignment_flag(*_args, **_kwargs) -> dict:
    """Refuse an assignment verdict until owner-sourced ex-dividend data exists."""
    return {
        "state": "DATA_BLOCKED",
        "reason": "EX_DIV_DATE_UNAVAILABLE",
        "unlock": _ASSIGNMENT_UNLOCK,
    }


def _blocked_card(reason: str, *, asof: str, max_asof: str | None = None) -> dict:
    card = {
        "experiment_id": "EXP-TBILL",
        "state": "DATA_BLOCKED",
        "data_blocked": True,
        "reason": reason,
        "asof": asof,
        "max_asof": max_asof,
        "assignment": early_assignment_flag(),
        "caveat": _CAVEAT,
    }
    card.update(dict.fromkeys(_PAYLOAD_KEYS))
    return card


def _rate_provenance(resolved_rate) -> str:
    provenance = resolved_rate.provenance
    return (
        f"{provenance.source_url}; Treasury observation "
        f"{resolved_rate.source_date.isoformat()}; captured "
        f"{provenance.captured_at_utc}"
    )


def _board_card(card: dict, symbol: str) -> dict:
    return {**card, "symbol": symbol}


def exp_tbill_carry(
    contract_row,
    spot: float,
    *,
    symbol: str,
    asof: str,
    expiration: str,
) -> dict:
    """Compare one cached reference put's annualized quote credit with T-bills."""
    del spot, symbol  # Required synchronized context; neither changes carry math.
    try:
        bid = float(contract_row["bid"])
        ask = float(contract_row["ask"])
    except (KeyError, TypeError, ValueError):
        return _blocked_card("invalid reference quote", asof=asof)
    mid = (bid + ask) / 2.0
    if (
        not math.isfinite(bid)
        or not math.isfinite(ask)
        or not math.isfinite(mid)
        or bid <= 0.0
        or ask < bid
        or mid <= 0.0
    ):
        return _blocked_card("invalid reference quote", asof=asof)

    try:
        strike = float(contract_row["strike"])
        asof_date = date.fromisoformat(asof)
        expiration_date = date.fromisoformat(expiration)
    except (KeyError, TypeError, ValueError):
        return _blocked_card("invalid contract input", asof=asof)
    tau = (expiration_date - asof_date).days
    if not math.isfinite(strike) or strike <= 0.0 or tau <= 0:
        return _blocked_card("invalid contract input", asof=asof)

    try:
        resolved_rate = risk_free_rate(asof_date, expiration_date)
    except MissingRateError as exc:
        return _blocked_card(str(exc), asof=asof)

    collateral = strike * 100.0
    rate = float(resolved_rate.rate)
    opportunity_cost = collateral * (math.exp(rate * tau / 365.0) - 1.0)
    credit_annualized_yield = (mid * 100.0 / collateral) * (365.0 / tau)
    tbill_annualized_yield = math.exp(rate) - 1.0
    carry_spread = credit_annualized_yield - tbill_annualized_yield
    max_asof = min(asof_date, resolved_rate.source_date).isoformat()
    return {
        "experiment_id": "EXP-TBILL",
        "state": "ABOVE_TBILL" if carry_spread >= 0.0 else "BELOW_TBILL",
        "data_blocked": False,
        "reason": None,
        "asof": asof,
        "max_asof": max_asof,
        "credit_mid": mid,
        "collateral": collateral,
        "credit_annualized_yield": credit_annualized_yield,
        "tbill_annualized_yield": tbill_annualized_yield,
        "carry_spread": carry_spread,
        "opportunity_cost": opportunity_cost,
        "rate_provenance": _rate_provenance(resolved_rate),
        "assignment": early_assignment_flag(),
        "caveat": _CAVEAT,
    }


def _latest_cached_session(symbol: str, asof: str) -> str | None:
    prefix = f"{symbol.strip().upper()}_"
    sessions: list[str] = []
    for path in CACHE_DIR.glob(f"{prefix}*.parquet"):
        session = path.name[len(prefix) : -len(".parquet")]
        try:
            parsed = date.fromisoformat(session)
        except ValueError:
            continue
        if parsed <= date.fromisoformat(asof):
            sessions.append(session)
    return max(sessions) if sessions else None


def _row_expiration_iso(row) -> str:
    value = row["expiration"]
    if isinstance(value, date):
        return value.isoformat()
    return date.fromisoformat(str(value)[:10]).isoformat()


def build_exp_tbill_board(symbols, *, asof) -> list[dict]:
    """Build per-symbol cards from exactly one cached chain session per name."""
    resolved_asof = date.fromisoformat(asof).isoformat()
    cards: list[dict] = []
    for raw_symbol in symbols:
        symbol = str(raw_symbol).strip().upper()
        chain_session = _latest_cached_session(symbol, resolved_asof)
        if chain_session is None:
            cards.append(
                _board_card(
                    _blocked_card("no cached chain for the as-of session", asof=resolved_asof),
                    symbol,
                )
            )
            continue
        try:
            chains = load_range(
                symbol,
                chain_session,
                chain_session,
                allow_oos=True,
            )
            chain = chains.get(chain_session)
            if chain is None or chain.empty:
                cards.append(
                    _board_card(
                        _blocked_card(
                            "no valid reference put",
                            asof=chain_session,
                            max_asof=chain_session,
                        ),
                        symbol,
                    )
                )
                continue
            session_date = date.fromisoformat(chain_session)
            expiration = nearest_monthly(
                chain,
                session_date,
                min_dte=int(EXP_TBILL_TENOR_DTE[0]),
                max_dte=int(EXP_TBILL_TENOR_DTE[1]),
            )
            reference_put = (
                atm_row(
                    chain,
                    expiration,
                    right="P",
                    target_delta=float(EXP_TBILL_TARGET_DELTA),
                )
                if expiration is not None
                else None
            )
            if reference_put is None:
                cards.append(
                    _board_card(
                        _blocked_card(
                            "no valid reference put",
                            asof=chain_session,
                            max_asof=chain_session,
                        ),
                        symbol,
                    )
                )
                continue
            closes = load_closes(
                symbol,
                "2018-01-01",
                chain_session,
                allow_oos=True,
            )
            if closes.empty:
                cards.append(
                    _board_card(
                        _blocked_card(
                            "no synchronized spot for the chain session",
                            asof=chain_session,
                            max_asof=chain_session,
                        ),
                        symbol,
                    )
                )
                continue
            cards.append(
                _board_card(
                    exp_tbill_carry(
                        reference_put,
                        float(closes.iloc[-1]),
                        symbol=symbol,
                        asof=chain_session,
                        expiration=_row_expiration_iso(reference_put),
                    ),
                    symbol,
                )
            )
        except Exception as exc:
            cards.append(
                _board_card(
                    _blocked_card(
                        f"board build failed ({exc.__class__.__name__}: {exc})",
                        asof=chain_session,
                        max_asof=chain_session,
                    ),
                    symbol,
                )
            )
    return cards

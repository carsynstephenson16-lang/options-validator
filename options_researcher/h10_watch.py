"""Daily recorder for the adjudicated H10a and active H10b forward-paper study.

The watcher evaluates H10b's QM breakout signal at the last completed session,
applies the registered H10 contract and entry gates,
and writes one deterministic receipt for the requested run date. It never
writes the paper book, places an order, fetches data, or emits a verdict.

    uv run python -m options_researcher.h10_watch [--as-of YYYY-MM-DD]
"""

from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher import qm_signals
from options_researcher.earnings_cycle import CYCLE_AMBER, cycle_badge
from options_researcher.h7_earnings import load_assertions
from options_researcher.h7_signals import lane_admission
from options_researcher.h7_source_health import symbol_health
from options_researcher.h7_watch import evaluation_session
from tools.schwab_chain_manifest import SchwabChainManifestError

BANNER = (
    "forward paper study H10b (H10a adjudicated); alerts + receipts only; never trades; "
    "verdict gates on losses"
)
H10_BOOK_PATH = Path("data/positions/h10_positions.csv")
H10_RECEIPT_DIR = Path("reports/h10/receipts")
BOOK_FIELDS = (
    "id",
    "symbol",
    "strike",
    "expiration",
    "contracts",
    "entry_date",
    "entry_cost",
    "entry_receipt_hash",
    "exit_date",
    "exit_proceeds",
    "exit_reason",
    "exit_receipt_hash",
)
_CHAIN_FIELDS = {
    "expiration",
    "strike",
    "right",
    "delta",
    "bid",
    "ask",
    "open_interest",
    "iv",
}
_OHLCV_START = "2017-01-01"

# H10A_RESULT — ratified 2026-08-15, appended 2026-08-16: H10a's registered
# trial is adjudicated. It is retained in receipts only as a typed status, not
# as an evaluable hypothesis or writable observation stream.
H10A_ADJUDICATED = "ADJUDICATED"
MIXED_TIMING_CONVENTION = "official_close_spot + 15:45_preclose_schwab_chain"

FrameLoader = Callable[[str, str], pd.DataFrame | None]
PrecloseChainLoader = Callable[[str, str], tuple[pd.DataFrame, str] | None]
Gate = Callable[[], str | None]
AssertionsLoader = Callable[[], list[dict]]

# H10b's registered forward-paper window (ledger/experiments.jsonl seq 16).
# The registration text ("window ends 2027-01-06") does not state whether the
# end date itself is included --
# checked docs/ and the ledger, nothing further is specified. This repo's
# choice: the window-end date is INCLUSIVE (fires/entries are still allowed
# ON the end date); suppression starts the session strictly AFTER it. See
# tests/test_h10_watch.py::H10bWindowTests for the boundary tests that pin
# this choice down.
_WINDOW_END = {"H10b": config.H10B_WINDOW_END}


def _window_status(eval_iso: str) -> dict[str, str]:
    """H10b's registered-window status for `eval_iso`.

    "WINDOW_CLOSED" once eval_iso is strictly after that hypothesis's
    registered window end; "OPEN" on and before the end date.
    """
    return {
        name: ("WINDOW_CLOSED" if eval_iso > end else "OPEN") for name, end in _WINDOW_END.items()
    }


class H10BookError(RuntimeError):
    """The H10 book cannot prove the current open-premium exposure."""


def _load_adjusted(symbol: str, eval_iso: str) -> pd.DataFrame:
    from data.underlying_ohlcv import load_ohlcv_adjusted

    return load_ohlcv_adjusted(symbol, _OHLCV_START, eval_iso, allow_oos=True)


def _load_raw(symbol: str, eval_iso: str) -> pd.DataFrame:
    from data.underlying_ohlcv import load_ohlcv

    return load_ohlcv(symbol, _OHLCV_START, eval_iso, allow_oos=True)


def _load_verified_preclose_chain(
    symbol: str, expected_session: str
) -> tuple[pd.DataFrame, str] | None:
    """Return one expected-session, full-universe verified Schwab chain.

    The verified-view boundary owns package verification; this consumer never
    opens the capture store itself and never falls back to an older package or
    the ThetaData chain.
    """
    from options_researcher import schwab_chain_view

    name = symbol.upper()
    symbols = set(schwab_chain_view.session_symbols(expected_session))
    if name not in symbols or not set(config.H7_WATCHLIST).issubset(symbols):
        return None
    return schwab_chain_view.load_chain(name, expected_session), expected_session


def _last_iso(frame: pd.DataFrame) -> str:
    return str(frame.index[-1])[:10]


def _validated_chain(chain: pd.DataFrame) -> pd.DataFrame:
    missing = _CHAIN_FIELDS - set(chain.columns)
    if missing:
        raise ValueError(f"chain missing required fields: {sorted(missing)}")
    frame = chain.loc[:, sorted(_CHAIN_FIELDS)].copy()
    try:
        frame["expiration"] = pd.to_datetime(frame["expiration"], errors="raise").dt.date
        for field in (
            "strike",
            "delta",
            "bid",
            "ask",
            "open_interest",
            "iv",
        ):
            frame[field] = pd.to_numeric(frame[field], errors="raise")
            if not frame[field].map(math.isfinite).all():
                raise ValueError(f"chain {field} must be finite")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"chain contains malformed values: {exc}") from exc
    frame["right"] = frame["right"].astype(str).str.upper()
    return frame


def _signals_at_session(
    frame: pd.DataFrame, eval_iso: str, params: Mapping[str, Any]
) -> dict[str, bool | None]:
    """H10b's breakout signal at eval_iso; H10a is permanently unevaluated."""
    breakout_fires = qm_signals.breakout_fires(frame, params)
    raw = bool(breakout_fires) and breakout_fires[-1]["t"] == eval_iso
    windows = _window_status(eval_iso)
    return {"H10a": None, "H10b": raw and windows["H10b"] == "OPEN"}


def _candidate_contract(
    chain: pd.DataFrame, *, symbol: str, on: date, spot: float
) -> dict[str, Any] | None:
    """Select one registered H10 call from a validated chain.

    The gates come only from the H10 registrations and shared execution
    surfaces. Among passing rows, the existing directional-call convention is
    deterministic: earliest expiration, then highest delta, lower after-cost
    premium, and lower strike.
    """
    calls = chain.loc[chain["right"].eq("C")].copy()
    calls["dte"] = calls["expiration"].map(lambda expiry: (expiry - on).days)
    calls = calls.loc[
        calls["dte"].between(config.H10_DTE_MIN, config.H10_DTE_MAX)
        & calls["delta"].between(config.H10_DELTA_MIN, config.H10_DELTA_MAX)
        & calls["strike"].between(
            spot * (1.0 - config.H10_STRIKE_BAND_PCT),
            spot * (1.0 + config.H10_STRIKE_BAND_PCT),
        )
    ].copy()
    candidates: list[dict[str, Any]] = []
    for _, row in calls.iterrows():
        bid = float(row["bid"])
        ask = float(row["ask"])
        open_interest = float(row["open_interest"])
        if not quote_valid(bid, ask) or not passes_liquidity(open_interest, bid, ask):
            continue
        midpoint = (bid + ask) / 2.0
        if (ask - bid) / midpoint > config.H7_ADMIT_MAX_SPREAD_PCT:
            continue
        entry_price = adverse_buy(ask)
        entry_cost = round(entry_price * 100.0 + config.COMMISSION_PER_CONTRACT, 2)
        if entry_cost > config.H10_MAX_PREMIUM_PER_TRADE:
            continue
        candidates.append(
            {
                "symbol": symbol,
                "right": "C",
                "strike": float(row["strike"]),
                "expiration": row["expiration"].isoformat(),
                "dte": int(row["dte"]),
                "delta": float(row["delta"]),
                "bid": bid,
                "ask": ask,
                "open_interest": open_interest,
                "iv": float(row["iv"]),
                "spot": spot,
                "entry_price": entry_price,
                "exit_price": adverse_sell(bid),
                "entry_cost": entry_cost,
            }
        )
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda item: (
            item["expiration"],
            -item["delta"],
            item["entry_cost"],
            item["strike"],
        ),
    )


def load_open_premium(path: Path = H10_BOOK_PATH) -> float:
    """Sum entry cost for open rows; malformed or missing books fail closed."""
    try:
        with Path(path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != BOOK_FIELDS:
                raise H10BookError(f"{path}: header {reader.fieldnames} != {BOOK_FIELDS}")
            total = 0.0
            for line_number, row in enumerate(reader, start=2):
                if (row["exit_date"] or "").strip():
                    continue
                value = float(row["entry_cost"])
                if not math.isfinite(value) or value < 0:
                    raise ValueError("entry_cost must be finite and non-negative")
                total += value
    except H10BookError:
        raise
    except (OSError, KeyError, TypeError, ValueError, csv.Error) as exc:
        raise H10BookError(
            f"{path}: line {locals().get('line_number', 1)}: {type(exc).__name__}: {exc}"
        ) from exc
    return round(total, 2)


def _entry_skip_reason(
    symbol: str,
    *,
    on: date,
    expiration: date,
    assertions: list[dict] | None,
    known_as_of: datetime,
) -> str | None:
    if assertions is None:
        return "SOURCE_HEALTH"
    health = symbol_health(
        symbol,
        on,
        assertions,
        known_as_of=known_as_of,
        warn_sessions=config.H7_SOURCE_HEALTH_WARN_SESSIONS,
    )
    if health["healthy"] is not True:
        return "SOURCE_HEALTH"
    cycle, _ = cycle_badge(symbol, on, expiration, assertions, known_as_of=known_as_of)
    if cycle == CYCLE_AMBER:
        return "EARNINGS"
    return None


def _evaluation(
    symbol: str,
    *,
    eval_iso: str,
    params: Mapping[str, Any],
    load_adjusted: FrameLoader,
    load_raw: FrameLoader,
    load_preclose_chain: PrecloseChainLoader,
    assertions: list[dict] | None,
    known_as_of: datetime,
    open_premium: float | None,
) -> dict[str, Any]:
    blank_signals: dict[str, bool | None] = {"H10a": None, "H10b": None}
    window_status = _window_status(eval_iso)

    def result(
        status: str,
        reason: str | None,
        *,
        signals: Mapping[str, bool | None] = blank_signals,
        admitted: int = 0,
        candidate: dict[str, Any] | None = None,
        action: bool = False,
        chain_session: str | None = None,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "signals": dict(signals),
            "h10a_status": H10A_ADJUDICATED,
            "window_status": dict(window_status),
            "status": status,
            "reason": reason,
            "admitted_contracts": admitted,
            "candidate_contract": candidate,
            "book_action_required": action,
            "chain_session": chain_session,
            "chain_timing_convention": MIXED_TIMING_CONVENTION,
        }

    try:
        adjusted = load_adjusted(symbol, eval_iso)
        if adjusted is None or adjusted.empty or _last_iso(adjusted) != eval_iso:
            return result("SKIPPED", "DATA")
        signals = _signals_at_session(adjusted, eval_iso, params)
    except (IndexError, KeyError, OSError, TypeError, ValueError):
        return result("SKIPPED", "DATA")
    if not any(signals.values()):
        return result("NO_SIGNAL", None, signals=signals)

    try:
        raw = load_raw(symbol, eval_iso)
        if raw is None or raw.empty or _last_iso(raw) != eval_iso:
            return result("SKIPPED", "DATA", signals=signals)
        spot = float(raw["close"].iloc[-1])
        if not math.isfinite(spot) or spot <= 0:
            return result("SKIPPED", "DATA", signals=signals)
        preclose = load_preclose_chain(symbol, eval_iso)
        if preclose is None:
            return result("SKIPPED", "SCHWAB_CAPTURE", signals=signals)
        loaded_chain, chain_session = preclose
        if chain_session != eval_iso:
            return result("SKIPPED", "SCHWAB_CAPTURE", signals=signals)
        if date.fromisoformat(chain_session).isoformat() != chain_session:
            return result("SKIPPED", "SCHWAB_CAPTURE", signals=signals)
        if loaded_chain.empty:
            return result(
                "SKIPPED",
                "SCHWAB_CAPTURE",
                signals=signals,
                chain_session=chain_session,
            )
        chain = _validated_chain(loaded_chain)
        on = date.fromisoformat(eval_iso)
        admitted, admitted_count = lane_admission(
            chain,
            spot=spot,
            today=on,
            dte_band=(config.H10_DTE_MIN, config.H10_DTE_MAX),
            right="C",
        )
    except (SchwabChainManifestError, IndexError, KeyError, OSError, TypeError, ValueError):
        return result("SKIPPED", "SCHWAB_CAPTURE", signals=signals)
    if not admitted:
        return result(
            "SKIPPED",
            "ADMISSION",
            signals=signals,
            admitted=admitted_count,
            chain_session=chain_session,
        )

    candidate = _candidate_contract(chain, symbol=symbol, on=on, spot=spot)
    if candidate is None:
        return result(
            "SKIPPED",
            "NO_CONTRACT",
            signals=signals,
            admitted=admitted_count,
            chain_session=chain_session,
        )
    skip = _entry_skip_reason(
        symbol,
        on=on,
        expiration=date.fromisoformat(candidate["expiration"]),
        assertions=assertions,
        known_as_of=known_as_of,
    )
    if skip is not None:
        return result(
            "SKIPPED",
            skip,
            signals=signals,
            admitted=admitted_count,
            candidate=candidate,
            chain_session=chain_session,
        )
    if open_premium is None:
        return result(
            "SKIPPED",
            "BOOK",
            signals=signals,
            admitted=admitted_count,
            candidate=candidate,
            chain_session=chain_session,
        )
    if open_premium + float(candidate["entry_cost"]) > config.H10_MONTHLY_PREMIUM_CAP:
        return result(
            "SKIPPED",
            "CAP",
            signals=signals,
            admitted=admitted_count,
            candidate=candidate,
            chain_session=chain_session,
        )
    return result(
        "FIRED",
        None,
        signals=signals,
        admitted=admitted_count,
        candidate=candidate,
        action=True,
        chain_session=chain_session,
    )


def _receipt_path(receipt_dir: Path, run_date: date) -> Path:
    return Path(receipt_dir) / f"h10_watch_{run_date.isoformat()}.json"


def _write_receipt(receipt: dict[str, Any], path: Path) -> bool:
    """Write once; an identical rerun is a no-op, conflicts are refused."""
    content = json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != content:
            return False
    return True


def main(
    argv: list[str] | None = None,
    *,
    universe: list[str] | None = None,
    load_adjusted: FrameLoader | None = None,
    load_raw: FrameLoader | None = None,
    load_preclose_chain: PrecloseChainLoader | None = None,
    params: Mapping[str, Any] | None = None,
    gate: Gate | None = None,
    load_assertions_fn: AssertionsLoader | None = None,
    book_path: Path = H10_BOOK_PATH,
    receipt_dir: Path = H10_RECEIPT_DIR,
    known_as_of: datetime | None = None,
) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="H10a/H10b forward-paper watcher and receipt recorder"
    )
    parser.add_argument(
        "--as-of",
        help="evaluate the last completed session before this date "
        "(default: today, America/New_York)",
    )
    args = parser.parse_args(argv)

    prereg_gate = gate or qm_signals.qm_prereg_gate
    gate_reason = prereg_gate()
    if gate_reason is not None:
        print(gate_reason)
        return 2

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    try:
        run_date = date.fromisoformat(args.as_of) if args.as_of else ny_today
    except ValueError:
        print(f"--as-of {args.as_of!r} is not YYYY-MM-DD; refusing.")
        return 2
    if run_date > ny_today:
        print(f"--as-of {run_date} is in the future; refusing.")
        return 2
    try:
        eval_date = evaluation_session(run_date)
    except (IndexError, ValueError) as exc:
        print(f"--as-of {run_date} has no prior completed session: {exc}")
        return 2
    eval_iso = eval_date.isoformat()
    if eval_iso < config.H10B_RESUME_FLOOR_SESSION:
        print(
            "H10B REFUSED -- "
            f"evaluation_session={eval_iso} is before resume floor "
            f"{config.H10B_RESUME_FLOOR_SESSION}; no observation recorded."
        )
        return 2

    effective_known_as_of: datetime
    if known_as_of is not None:
        effective_known_as_of = known_as_of
    elif args.as_of:
        from data.cache_runner import session_close_utc

        effective_known_as_of = session_close_utc(eval_iso)
    else:
        effective_known_as_of = datetime.now(timezone.utc)
    if effective_known_as_of.tzinfo is None or effective_known_as_of.utcoffset() is None:
        print("known_as_of must be timezone-aware; refusing.")
        return 2

    load_assertions_fn = load_assertions_fn or load_assertions
    try:
        assertions: list[dict] | None = load_assertions_fn()
    except (OSError, TypeError, ValueError, csv.Error) as exc:
        assertions = None
        print(
            "H10 SOURCE-HEALTH WARNING -- assertions unavailable; "
            f"fires will be skipped: {type(exc).__name__}: {exc}"
        )
    try:
        open_premium: float | None = load_open_premium(Path(book_path))
    except H10BookError as exc:
        open_premium = None
        print(f"H10 BOOK WARNING -- fires will be skipped: {exc}")

    names = list(config.H7_WATCHLIST if universe is None else universe)
    params = qm_signals.qm_params() if params is None else params
    load_adjusted = load_adjusted or _load_adjusted
    load_raw = load_raw or _load_raw
    load_preclose_chain = load_preclose_chain or _load_verified_preclose_chain

    print(f"H10 WATCH session={eval_iso} run={run_date.isoformat()} ({BANNER})")
    # Reserve accepted costs in receipt order.  Passing the same starting
    # balance to every symbol would let a multi-symbol watcher run exceed the
    # registered monthly cap.
    evaluations: list[dict[str, Any]] = []
    reserved_premium = open_premium
    for symbol in names:
        row = _evaluation(
            symbol,
            eval_iso=eval_iso,
            params=params,
            load_adjusted=load_adjusted,
            load_raw=load_raw,
            load_preclose_chain=load_preclose_chain,
            assertions=assertions,
            known_as_of=effective_known_as_of,
            open_premium=reserved_premium,
        )
        evaluations.append(row)
        if row["status"] == "FIRED" and reserved_premium is not None:
            candidate = row["candidate_contract"]
            if candidate is None:  # pragma: no cover - internal invariant
                raise RuntimeError("FIRED evaluation has no candidate contract")
            reserved_premium = round(reserved_premium + float(candidate["entry_cost"]), 2)
    for row in evaluations:
        reason = f" reason={row['reason']}" if row["reason"] else ""
        fired = [name for name, value in row["signals"].items() if value]
        signal_text = f" signals={','.join(fired)}" if fired else ""
        closed = [name for name, value in row["window_status"].items() if value == "WINDOW_CLOSED"]
        window_text = f" window_closed={','.join(closed)}" if closed else ""
        print(f"{row['symbol']}: {row['status']}{reason}{signal_text}{window_text}")

    receipt = {
        "as_of": run_date.isoformat(),
        "evaluation_session": eval_iso,
        "evaluations": evaluations,
        "book_action_required": any(row["book_action_required"] for row in evaluations),
    }
    path = _receipt_path(Path(receipt_dir), run_date)
    try:
        written = _write_receipt(receipt, path)
    except OSError as exc:
        print(f"H10 RECEIPT ERROR -- {type(exc).__name__}: {exc}")
        return 2
    if not written:
        print(f"H10 RECEIPT CONFLICT -- {path} already has different content")
        return 2
    print(f"receipt={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

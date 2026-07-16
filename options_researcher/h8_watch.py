"""Read-only forward-paper watcher for registered H8 trial (pre-earnings calls).

H8 is a directional pre-earnings experiment, not a recommendation engine and
not a live trading path.  This module applies the exact registered entry,
capacity and exit rules to injected or cached EOD facts.  It never writes the
paper book, places an order, fetches market data, or changes a hypothesis
parameter.

H8 differs from H6 on purpose: entries are allowed ONLY inside a
T-15..T-8 XNYS-session window before a CONFIRMED report (estimated dates fail
closed), IV-rank must be <= config.H8_IVR_MAX, the take-profit is +75%, and the
hard exit is a T-2 pre-earnings close rather than a 21-DTE roll.  The monthly
premium-at-risk cap is SHARED with H6, and H8 may never be open on the same
underlying as an H6 position at the same time.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import config
from data.cache_runner import session_close_utc, trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import is_monthly
from options_researcher.h6_features import verify_feature_manifest
from options_researcher.h6_watch import BOOK_FIELDS
from options_researcher.h6_watch import load_book as load_h6_book
from options_researcher.h7_earnings import (
    ASSERTIONS_PATH,
    GATING_EVENT_CLASS,
    RAW_ASSERTIONS_PATH,
    assertions_view,
    load_assertions,
    report_date,
)

H8_BOOK_PATH = Path("data/positions/h8_positions.csv")
H6_BOOK_PATH = Path("data/positions/h6_positions.csv")
EXIT_REASONS = ("take_profit", "hard_exit_t2")
_CHAIN_FIELDS = {
    "expiration",
    "strike",
    "right",
    "delta",
    "bid",
    "ask",
    "open_interest",
}
# Calendar lookback used to enumerate real XNYS sessions before a report.
# 60 days yields ~41 trading sessions, always >= the T-15 entry boundary, so a
# holiday cluster can never silently shorten the window.
_SESSION_LOOKBACK_DAYS = 60


@dataclass(frozen=True)
class Candidate:
    symbol: str | None
    strike: float
    expiration: date
    dte: int
    delta: float
    bid: float
    raw_ask: float
    entry_cost: float


@dataclass(frozen=True)
class BookPosition:
    id: str
    symbol: str
    strike: float
    expiration: date
    contracts: int
    entry_date: date
    entry_cost: float
    entry_receipt_hash: str
    exit_date: date | None = None
    exit_proceeds: float | None = None
    exit_reason: str | None = None
    exit_receipt_hash: str | None = None

    @property
    def is_open(self) -> bool:
        return self.exit_date is None


@dataclass(frozen=True)
class WindowDecision:
    state: str
    reason: str
    report: date | None = None


@dataclass(frozen=True)
class EntryDecision:
    symbol: str
    evaluation_session: date
    status: str
    window: WindowDecision
    iv_rank: float | None
    candidate: Candidate | None
    monthly_risk_used: float
    monthly_headroom: float
    open_h8: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExitDecision:
    position_id: str
    symbol: str
    evaluation_session: date
    action: str
    reason: str
    dte: int
    proceeds: float | None
    pnl: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _validated_chain(chain: pd.DataFrame) -> pd.DataFrame:
    missing = _CHAIN_FIELDS - set(chain.columns)
    if missing:
        raise ValueError(f"chain missing required fields: {sorted(missing)}")
    frame = chain.loc[:, sorted(_CHAIN_FIELDS)].copy()
    try:
        frame["expiration"] = pd.to_datetime(
            frame["expiration"], errors="raise"
        ).dt.date
        for field in ("strike", "delta", "bid", "ask", "open_interest"):
            frame[field] = pd.to_numeric(frame[field], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"chain contains malformed values: {exc}") from exc
    frame["right"] = frame["right"].astype(str).str.upper()
    return frame


def choose_contract(
    chain: pd.DataFrame, on: date, *, symbol: str | None = None
) -> Candidate | None:
    """Select the registered H8 contract, or None when no contract passes.

    The earliest standard monthly in the frozen DTE band is selected first.
    Inside that expiration, the highest absolute delta passing every hard
    gate wins.  Exact-delta ties resolve by lower ask then lower strike; this
    deterministic identity tie-break does not relax any registered gate.  The
    logic mirrors H6, but every number is drawn from the H8_* config block.
    """
    frame = _validated_chain(chain)
    lo_dte, hi_dte = config.H8_DTE_BAND
    calls: pd.DataFrame = frame.loc[frame["right"].eq("C")].copy()
    calls["dte"] = calls["expiration"].map(lambda exp: (exp - on).days)
    calls = calls.loc[
        calls["dte"].between(lo_dte, hi_dte)
        & calls["expiration"].map(is_monthly)
    ]
    if calls.empty:
        return None
    expiration = min(calls["expiration"])
    calls = calls.loc[calls["expiration"].eq(expiration)].copy()
    calls["abs_delta"] = calls["delta"].abs()
    lo_delta, hi_delta = config.H8_DELTA_BAND
    calls = calls.loc[
        calls["abs_delta"].between(lo_delta, hi_delta)
        & ((calls["ask"] * 100.0) <= config.H8_MAX_ASK_DOLLARS)
    ]
    if calls.empty:
        return None
    liquid = []
    for idx, row in calls.iterrows():
        if quote_valid(row["bid"], row["ask"]) and passes_liquidity(
            float(row["open_interest"]), float(row["bid"]), float(row["ask"])
        ):
            liquid.append(idx)
    calls = calls.loc[liquid]
    if calls.empty:
        return None
    row = calls.sort_values(
        ["abs_delta", "ask", "strike"], ascending=[False, True, True]
    ).iloc[0]
    contracts = config.H8_MAX_CONTRACTS_PER_NAME
    entry_cost = (
        adverse_buy(row["ask"]) * 100.0 * contracts
        + config.COMMISSION_PER_CONTRACT * contracts
    )
    return Candidate(
        symbol=symbol.upper() if symbol else None,
        strike=float(row["strike"]),
        expiration=expiration,
        dte=int(row["dte"]),
        delta=float(row["abs_delta"]),
        bid=float(row["bid"]),
        raw_ask=float(row["ask"]),
        entry_cost=round(entry_cost, 2),
    )


def _sessions_before(report: date) -> list[date]:
    """Real XNYS sessions strictly before `report` within the lookback."""
    start = report - timedelta(days=_SESSION_LOOKBACK_DAYS)
    iso = report.isoformat()
    return [
        date.fromisoformat(day)
        for day in trading_days(start.isoformat(), iso)
        if day < iso
    ]


def _symbol_view(
    symbol: str, assertions: list[dict], known_as_of: datetime
) -> list[dict]:
    if known_as_of.tzinfo is None or known_as_of.utcoffset() is None:
        raise ValueError("known_as_of must be timezone-aware")
    return [
        row
        for row in assertions_view(assertions, known_as_of)
        if row["symbol"] == symbol.upper()
        and row.get("event_class") == GATING_EVENT_CLASS
    ]


def entry_window_state(
    symbol: str,
    on: date,
    assertions: list[dict],
    *,
    known_as_of: datetime,
) -> WindowDecision:
    """Classify the registered H8 entry window using causal earnings facts.

    Entries are permitted only on the T-15..T-8 XNYS sessions before a
    CONFIRMED report.  An estimated date inside that provisional window is a
    fail-closed BLOCK (the date is not causally certain yet); conflicting or
    absent schedule facts are UNKNOWN (also fail closed).
    """
    view = _symbol_view(symbol, assertions, known_as_of)
    if not view:
        return WindowDecision("UNKNOWN", "no gating point-in-time assertions for symbol")
    live = [row for row in view if row["status"] in ("estimated", "confirmed")]
    by_period: dict[str, set[date]] = {}
    for row in live:
        if row["fiscal_period"]:
            by_period.setdefault(row["fiscal_period"], set()).add(row["expected_date"])
    for period, dates in sorted(by_period.items()):
        if len(dates) > 1 and max(dates) >= on:
            return WindowDecision("UNKNOWN", f"conflicting schedule assertions for {period}")

    far, near = config.H8_ENTRY_WINDOW_SESSIONS
    future = sorted(
        (row["expected_date"], row["status"])
        for row in live
        if row["expected_date"] >= on
    )
    if not future:
        return WindowDecision("OUT_OF_WINDOW", "no upcoming scheduled report")
    for report, status in future:
        prior = _sessions_before(report)
        if len(prior) < far:
            return WindowDecision("UNKNOWN", f"cannot construct entry window for {report}")
        window_far = prior[-far]
        window_near = prior[-near]
        if window_far <= on <= window_near:
            if status != "confirmed":
                return WindowDecision(
                    "ESTIMATED_BLOCKED",
                    f"report {report.isoformat()} is estimated, not confirmed; "
                    "H8 fails closed",
                    report=report,
                )
            return WindowDecision(
                "IN_WINDOW",
                "inside the confirmed T-15..T-8 entry window",
                report=report,
            )
    return WindowDecision("OUT_OF_WINDOW", "outside the T-15..T-8 entry window")


def next_scheduled_report(
    symbol: str,
    on: date,
    assertions: list[dict],
    *,
    known_as_of: datetime,
) -> date | None:
    """Earliest known report on/after `on` at `known_as_of` (any status)."""
    view = _symbol_view(symbol, assertions, known_as_of)
    upcoming = [report_date(row) for row in view if report_date(row) >= on]
    return min(upcoming) if upcoming else None


def _open_at(book: list[BookPosition], on: date) -> list[BookPosition]:
    """Positions open at `on`, inclusive of the exit session.

    The watcher evaluates capacity before same-session closes, so an exit
    cannot free capacity or a name for a new entry until the next session.
    """
    return [pos for pos in book if pos.exit_date is None or on <= pos.exit_date]


def _month_used(
    h8_book: list[BookPosition], h6_book: list[BookPosition], on: date
) -> float:
    key = (on.year, on.month)
    used = sum(
        pos.entry_cost
        for book in (h8_book, h6_book)
        for pos in book
        if (pos.entry_date.year, pos.entry_date.month) == key
    )
    return round(used, 2)


def _finite_or_none(value: float | None) -> float | None:
    try:
        parsed = math.nan if value is None else float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def evaluate_entry(
    symbol: str,
    on: date,
    chain: pd.DataFrame,
    *,
    iv_rank: float | None,
    assertions: list[dict],
    known_as_of: datetime,
    h8_book: list[BookPosition],
    h6_book: list[BookPosition],
) -> EntryDecision:
    """Apply every registered H8 entry and portfolio gate; never write."""
    sym = symbol.upper()
    if sym not in config.H8_NAMES:
        raise ValueError(f"{sym} is outside registered H8 scope {config.H8_NAMES}")
    validate_book(h8_book)
    for pos in h8_book:
        if pos.entry_date > on:
            raise ValueError(f"H8 book position {pos.id}: entry is after evaluation date")
        if pos.exit_date is not None and pos.exit_date > on:
            raise ValueError(f"H8 book position {pos.id}: exit is after evaluation date")

    candidate = choose_contract(chain, on, symbol=sym)
    window = entry_window_state(sym, on, assertions, known_as_of=known_as_of)
    month_used = _month_used(h8_book, h6_book, on)
    cap = config.H6_MONTHLY_PREMIUM_AT_RISK
    headroom = round(cap - month_used, 2)
    opened_h8 = _open_at(h8_book, on)
    opened_h6 = _open_at(h6_book, on)

    clean_ivr = _finite_or_none(iv_rank)

    if window.state == "OUT_OF_WINDOW":
        return EntryDecision(
            symbol=sym,
            evaluation_session=on,
            status="OUT_OF_WINDOW",
            window=window,
            iv_rank=clean_ivr,
            candidate=candidate,
            monthly_risk_used=month_used,
            monthly_headroom=headroom,
            open_h8=len(opened_h8),
            reasons=(),
        )

    reasons: list[str] = []
    if window.state in ("UNKNOWN", "ESTIMATED_BLOCKED"):
        reasons.append(f"earnings window {window.state}: {window.reason}")
    else:  # IN_WINDOW -- apply the IV-rank gate
        ivr = math.nan if clean_ivr is None else clean_ivr
        if not math.isfinite(ivr):
            reasons.append("IV-rank is unknown; H8 fails closed")
        elif ivr > config.H8_IVR_MAX:
            reasons.append(
                f"IV-rank {ivr:.4f} exceeds H8 maximum {config.H8_IVR_MAX:.4f}"
            )

    if candidate is None:
        reasons.append("no call passes H8 monthly/DTE/delta/ask/liquidity gates")
    elif month_used + candidate.entry_cost > cap:
        reasons.append(
            f"shared H6+H8 monthly premium risk "
            f"${month_used + candidate.entry_cost:,.2f} exceeds ${cap:,.2f}"
        )
    if any(pos.symbol == sym for pos in opened_h8):
        reasons.append(f"{sym} already open in H8; one contract per name")
    if any(pos.symbol == sym for pos in opened_h6):
        reasons.append(f"{sym} already open in H6; H8 and H6 may not share an underlying")
    if len(opened_h8) >= config.H8_MAX_CONCURRENT:
        reasons.append(
            f"open H8 positions {len(opened_h8)} reaches cap {config.H8_MAX_CONCURRENT}"
        )

    status = "ENTRY-OK" if not reasons else "BLOCKED"
    return EntryDecision(
        symbol=sym,
        evaluation_session=on,
        status=status,
        window=window,
        iv_rank=clean_ivr,
        candidate=candidate,
        monthly_risk_used=month_used,
        monthly_headroom=headroom,
        open_h8=len(opened_h8),
        reasons=tuple(reasons),
    )


def evaluate_exit(
    position: BookPosition,
    on: date,
    chain: pd.DataFrame,
    *,
    next_report: date | None,
) -> ExitDecision:
    """Mark one open H8 paper position and raise the registered exit alerts.

    Two alerts fire, in priority order: the T-2 pre-earnings hard close (also
    triggered when a confirmed report has moved inside T-2), then the +75%
    take-profit at conservative marks.  Alerts are information, not orders.
    """
    if not position.is_open:
        raise ValueError(f"position {position.id} is already closed")
    if on < position.entry_date:
        raise ValueError(f"position {position.id}: evaluation predates entry")
    frame = _validated_chain(chain)
    matches = frame[
        (frame["right"] == "C")
        & (frame["expiration"] == position.expiration)
        & (frame["strike"] == position.strike)
    ]
    dte = (position.expiration - on).days
    if len(matches) != 1:
        return ExitDecision(
            position.id, position.symbol, on, "BLOCKED",
            "quote_missing_or_ambiguous", dte, None, None,
        )
    row = matches.iloc[0]
    if not quote_valid(row["bid"], row["ask"]):
        return ExitDecision(
            position.id, position.symbol, on, "BLOCKED",
            "invalid_exit_quote", dte, None, None,
        )
    proceeds = (
        adverse_sell(row["bid"]) * 100.0 * position.contracts
        - config.COMMISSION_PER_CONTRACT * position.contracts
    )
    proceeds = round(proceeds, 2)
    pnl = round(proceeds - position.entry_cost, 2)

    if next_report is not None:
        prior = _sessions_before(next_report)
        near = config.H8_EXIT_SESSIONS_BEFORE_REPORT
        t2_session = prior[-near] if len(prior) >= near else next_report
        if on >= t2_session:
            return ExitDecision(
                position.id, position.symbol, on, "EXIT",
                "hard_exit_t2", dte, proceeds, pnl,
            )
    if proceeds >= position.entry_cost * (1.0 + config.H8_TAKE_PROFIT_PCT):
        return ExitDecision(
            position.id, position.symbol, on, "EXIT", "take_profit", dte, proceeds, pnl
        )
    return ExitDecision(
        position.id, position.symbol, on, "HOLD", "no_exit_trigger", dte, proceeds, pnl
    )


def _require_session(day: date, ctx: str) -> None:
    iso = day.isoformat()
    if trading_days(iso, iso) != [iso]:
        raise ValueError(f"{ctx}: {iso} is not an XNYS session")


def validate_book(book: list[BookPosition]) -> None:
    """Prove all registered H8 book invariants across the full history.

    Independent of CSV parsing so injected books cannot bypass it.  The
    monthly premium check here uses the shared cap as a NECESSARY condition
    on the H8 rows alone; the combined H6+H8 cap is proven in
    ``validate_cross_book``.  Position intervals are inclusive of the exit
    session, matching the watcher's before-close capacity evaluation.
    """
    seen: set[str] = set()
    max_entry_cost = (
        adverse_buy(config.H8_MAX_ASK_DOLLARS / 100.0)
        * 100.0
        * config.H8_MAX_CONTRACTS_PER_NAME
        + config.COMMISSION_PER_CONTRACT * config.H8_MAX_CONTRACTS_PER_NAME
    )
    monthly: dict[tuple[int, int], float] = {}
    change_dates: set[date] = set()
    for pos in book:
        ctx = f"book position {pos.id!r}"
        if not isinstance(pos.id, str) or not pos.id.strip() or pos.id in seen:
            raise ValueError(f"{ctx}: id missing or duplicate")
        seen.add(pos.id)
        if pos.symbol not in config.H8_NAMES:
            raise ValueError(f"{ctx}: symbol {pos.symbol!r} is outside H8")
        if pos.contracts != config.H8_MAX_CONTRACTS_PER_NAME:
            raise ValueError(
                f"{ctx}: contracts must equal {config.H8_MAX_CONTRACTS_PER_NAME}"
            )
        if not math.isfinite(float(pos.strike)) or pos.strike <= 0:
            raise ValueError(f"{ctx}: strike must be finite and positive")
        if type(pos.entry_date) is not date or type(pos.expiration) is not date:
            raise ValueError(f"{ctx}: entry_date and expiration must be dates")
        _require_session(pos.entry_date, f"{ctx} entry_date")
        entry_dte = (pos.expiration - pos.entry_date).days
        if not is_monthly(pos.expiration):
            raise ValueError(f"{ctx}: expiration is not a standard monthly")
        if not config.H8_DTE_BAND[0] <= entry_dte <= config.H8_DTE_BAND[1]:
            raise ValueError(
                f"{ctx}: entry DTE {entry_dte} is outside {config.H8_DTE_BAND}"
            )
        if not math.isfinite(float(pos.entry_cost)) or pos.entry_cost <= 0:
            raise ValueError(f"{ctx}: entry_cost must be finite and positive")
        if pos.entry_cost > max_entry_cost:
            raise ValueError(
                f"{ctx}: entry_cost ${pos.entry_cost:,.2f} exceeds the maximum "
                f"consistent with H8's raw-ask gate (${max_entry_cost:,.2f})"
            )

        close_values = (
            pos.exit_date,
            pos.exit_proceeds,
            pos.exit_reason,
            pos.exit_receipt_hash,
        )
        if any(value is not None for value in close_values) and not all(
            value is not None for value in close_values
        ):
            raise ValueError(f"{ctx}: close fields must be all present or all empty")
        if pos.exit_date is not None:
            if type(pos.exit_date) is not date:
                raise ValueError(f"{ctx}: exit_date must be a date")
            _require_session(pos.exit_date, f"{ctx} exit_date")
            if pos.exit_date < pos.entry_date:
                raise ValueError(f"{ctx}: exit_date predates entry_date")
            if pos.exit_date > pos.expiration:
                raise ValueError(f"{ctx}: exit_date is after expiration")
            if (
                pos.exit_proceeds is None
                or not math.isfinite(float(pos.exit_proceeds))
                or pos.exit_proceeds < 0
            ):
                raise ValueError(f"{ctx}: exit_proceeds must be finite and nonnegative")
            if pos.exit_reason not in EXIT_REASONS:
                raise ValueError(f"{ctx}: exit_reason must be one of {EXIT_REASONS}")
            if (
                pos.exit_reason == "take_profit"
                and pos.exit_proceeds
                < pos.entry_cost * (1.0 + config.H8_TAKE_PROFIT_PCT)
            ):
                raise ValueError(
                    f"{ctx}: take_profit proceeds do not reach +75% of premium"
                )

        key = (pos.entry_date.year, pos.entry_date.month)
        monthly[key] = monthly.get(key, 0.0) + pos.entry_cost
        change_dates.add(pos.entry_date)
        if pos.exit_date is not None:
            change_dates.add(pos.exit_date)

    for key, gross in monthly.items():
        if gross > config.H6_MONTHLY_PREMIUM_AT_RISK:
            raise ValueError(
                f"book {key[0]:04d}-{key[1]:02d} H8 gross premium risk "
                f"${gross:,.2f} exceeds ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.2f}"
            )

    for day in sorted(change_dates):
        active = [
            pos
            for pos in book
            if pos.entry_date <= day
            and (pos.exit_date is None or day <= pos.exit_date)
        ]
        if len(active) > config.H8_MAX_CONCURRENT:
            raise ValueError(
                f"concurrent H8 positions {len(active)} exceeds "
                f"{config.H8_MAX_CONCURRENT} on {day}"
            )
        symbols = [pos.symbol for pos in active]
        for symbol in sorted(set(symbols)):
            if symbols.count(symbol) > 1:
                raise ValueError(f"overlapping H8 positions for {symbol} on {day}")


def validate_cross_book(
    h8_book: list[BookPosition], h6_book: list[BookPosition]
) -> None:
    """Prove the shared H6+H8 invariants: monthly cap and same-name exclusion."""
    cap = config.H6_MONTHLY_PREMIUM_AT_RISK
    monthly: dict[tuple[int, int], float] = {}
    for pos in (*h8_book, *h6_book):
        key = (pos.entry_date.year, pos.entry_date.month)
        monthly[key] = monthly.get(key, 0.0) + pos.entry_cost
    for key, gross in monthly.items():
        if gross > cap:
            raise ValueError(
                f"combined H6+H8 {key[0]:04d}-{key[1]:02d} premium risk "
                f"${gross:,.2f} exceeds ${cap:,.2f}"
            )

    change_dates = {pos.entry_date for pos in (*h8_book, *h6_book)}
    for pos in (*h8_book, *h6_book):
        if pos.exit_date is not None:
            change_dates.add(pos.exit_date)
    for day in sorted(change_dates):
        h8_syms = {pos.symbol for pos in _open_at(h8_book, day) if pos.entry_date <= day}
        h6_syms = {pos.symbol for pos in _open_at(h6_book, day) if pos.entry_date <= day}
        shared = h8_syms & h6_syms
        if shared:
            raise ValueError(f"H8 and H6 both open on {sorted(shared)} on {day}")


def load_book(path: Path = H8_BOOK_PATH) -> list[BookPosition]:
    """Load and validate the manually maintained H8 forward-paper book."""
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != BOOK_FIELDS:
            raise ValueError(
                f"{path}: header must be {BOOK_FIELDS}, got {reader.fieldnames}"
            )
        raw = list(reader)
    out: list[BookPosition] = []
    seen: set[str] = set()
    for line, row in enumerate(raw, start=2):
        ctx = f"{path}:{line}"
        pid = row["id"].strip()
        if not pid or pid in seen:
            raise ValueError(f"{ctx}: position id missing or duplicate")
        seen.add(pid)
        symbol = row["symbol"].strip().upper()
        if symbol not in config.H8_NAMES:
            raise ValueError(f"{ctx}: symbol {symbol!r} is outside H8")
        try:
            strike = float(row["strike"])
            expiration = date.fromisoformat(row["expiration"])
            contracts = int(row["contracts"])
            entry_date = date.fromisoformat(row["entry_date"])
            entry_cost = float(row["entry_cost"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{ctx}: malformed entry fields: {exc}") from exc
        entry_receipt_hash = row["entry_receipt_hash"].strip()
        exit_values = [
            row["exit_date"].strip(),
            row["exit_proceeds"].strip(),
            row["exit_reason"].strip(),
            row["exit_receipt_hash"].strip(),
        ]
        if any(exit_values) and not all(exit_values):
            raise ValueError(f"{ctx}: close fields must be all present or all empty")
        exit_date = None
        exit_proceeds = None
        exit_reason = None
        exit_receipt_hash = None
        if all(exit_values):
            try:
                exit_date = date.fromisoformat(exit_values[0])
                exit_proceeds = float(exit_values[1])
            except ValueError as exc:
                raise ValueError(f"{ctx}: malformed close fields: {exc}") from exc
            exit_reason = exit_values[2]
            exit_receipt_hash = exit_values[3]
        out.append(
            BookPosition(
                id=pid,
                symbol=symbol,
                strike=strike,
                expiration=expiration,
                contracts=contracts,
                entry_date=entry_date,
                entry_cost=entry_cost,
                entry_receipt_hash=entry_receipt_hash,
                exit_date=exit_date,
                exit_proceeds=exit_proceeds,
                exit_reason=exit_reason,
                exit_receipt_hash=exit_receipt_hash,
            )
        )
    validate_book(out)
    return out


def _h6_positions(path: Path) -> list[BookPosition]:
    """Load the H6 book for the shared-cap and same-underlying gates only.

    Receipt verification is skipped: H8 reads H6 solely for its open symbols,
    entry months, and premiums, never to authorize an H6 action.
    """
    h6_rows = load_h6_book(path, verify_receipts=False)
    return [
        BookPosition(
            id=pos.id,
            symbol=pos.symbol,
            strike=pos.strike,
            expiration=pos.expiration,
            contracts=pos.contracts,
            entry_date=pos.entry_date,
            entry_cost=pos.entry_cost,
            entry_receipt_hash=pos.entry_receipt_hash,
            exit_date=pos.exit_date,
            exit_proceeds=pos.exit_proceeds,
            exit_reason=pos.exit_reason,
            exit_receipt_hash=pos.exit_receipt_hash,
        )
        for pos in h6_rows
    ]


def _feature_iv_rank(
    symbol: str, on: date, feature_dir: Path, chain_dir: Path
) -> float:
    path = feature_dir / f"{symbol}_features.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing; run options_researcher.h6_features first"
        )
    verify_feature_manifest(symbol, on, feature_dir=feature_dir, chain_dir=chain_dir)
    frame = pd.read_parquet(path)
    keys = pd.Index(frame.index).astype(str)
    hits = frame.loc[keys == on.isoformat()]
    if len(hits) != 1:
        raise ValueError(f"{path}: requires exactly one row for {on.isoformat()}")
    return float(hits.iloc[0]["iv_rank"])


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def _json_safe(value) -> dict:
    return json.loads(json.dumps(value, default=_json_default, allow_nan=False))


def build_snapshot(
    on: date,
    *,
    h8_book_path: Path = H8_BOOK_PATH,
    h6_book_path: Path = H6_BOOK_PATH,
    chain_dir: Path = Path(".cache/chains"),
    feature_dir: Path = Path(".tmp/research"),
    assertions_path: Path = ASSERTIONS_PATH,
    raw_assertions_path: Path = RAW_ASSERTIONS_PATH,
) -> dict:
    """Evaluate one completed H8 session; read-only, alerts are not errors."""
    iso = on.isoformat()
    _require_session(on, "evaluation_session")
    known_as_of = session_close_utc(iso)
    if datetime.now(timezone.utc) < known_as_of:
        raise ValueError(f"session {iso} is incomplete until {known_as_of.isoformat()}")

    h8_book = load_book(Path(h8_book_path))
    h6_book = _h6_positions(Path(h6_book_path))
    validate_cross_book(h8_book, h6_book)
    assertions = load_assertions(Path(assertions_path), raw_path=Path(raw_assertions_path))

    entries: list[dict] = []
    exits: list[dict] = []
    errors: list[str] = []
    chains: dict[str, pd.DataFrame] = {}
    for symbol in config.H8_NAMES:
        chain_path = Path(chain_dir) / f"{symbol}_{iso}.parquet"
        try:
            if not chain_path.exists():
                raise FileNotFoundError(f"exact chain missing: {chain_path}")
            chain = pd.read_parquet(chain_path)
            chains[symbol] = chain
            iv_rank = _feature_iv_rank(symbol, on, Path(feature_dir), Path(chain_dir))
            entries.append(
                evaluate_entry(
                    symbol,
                    on,
                    chain,
                    iv_rank=iv_rank,
                    assertions=assertions,
                    known_as_of=known_as_of,
                    h8_book=h8_book,
                    h6_book=h6_book,
                ).to_dict()
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            errors.append(f"{symbol}: {exc}")

    for pos in (row for row in h8_book if row.is_open):
        try:
            chain = chains.get(pos.symbol)
            if chain is None:
                chain_path = Path(chain_dir) / f"{pos.symbol}_{iso}.parquet"
                if not chain_path.exists():
                    raise FileNotFoundError(f"exact chain missing: {chain_path}")
                chain = pd.read_parquet(chain_path)
            report = next_scheduled_report(
                pos.symbol, on, assertions, known_as_of=known_as_of
            )
            exits.append(evaluate_exit(pos, on, chain, next_report=report).to_dict())
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            errors.append(f"exit {pos.id}: {exc}")

    cap = config.H6_MONTHLY_PREMIUM_AT_RISK
    used = _month_used(h8_book, h6_book, on)
    payload = {
        "mode": "FORWARD_PAPER_ONLY",
        "orders_enabled": False,
        "evaluation_session": iso,
        "known_as_of_utc": known_as_of,
        "entries": entries,
        "exits": exits,
        "shared_cap": {
            "cap": cap,
            "used": used,
            "headroom": round(cap - used, 2),
        },
        "errors": errors,
    }
    return _json_safe(payload)


def _describe_candidate(candidate: dict | None) -> str:
    if not candidate:
        return "no eligible contract"
    return (
        f"{candidate['symbol']} {candidate['expiration']} "
        f"{candidate['strike']:g}C delta {candidate['delta']:.2f} "
        f"@ ${candidate['entry_cost']:,.2f}"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Read-only exact-session H8 pre-earnings forward-paper watch"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--book", type=Path, default=H8_BOOK_PATH)
    parser.add_argument("--h6-book", type=Path, default=H6_BOOK_PATH)
    parser.add_argument("--chain-dir", type=Path, default=Path(".cache/chains"))
    parser.add_argument("--feature-dir", type=Path, default=Path(".tmp/research"))
    parser.add_argument("--assertions", type=Path, default=ASSERTIONS_PATH)
    parser.add_argument("--raw-assertions", type=Path, default=RAW_ASSERTIONS_PATH)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    iso = args.as_of.isoformat()
    try:
        payload = build_snapshot(
            args.as_of,
            h8_book_path=args.book,
            h6_book_path=args.h6_book,
            chain_dir=args.chain_dir,
            feature_dir=args.feature_dir,
            assertions_path=args.assertions,
            raw_assertions_path=args.raw_assertions,
        )
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(f"H8 FORWARD PAPER ONLY @ {iso} -- live orders: disabled")
        for row in payload["entries"]:
            if row["status"] == "ENTRY-OK":
                detail = _describe_candidate(row["candidate"])
            elif row["status"] == "OUT_OF_WINDOW":
                detail = row["window"]["reason"]
            else:
                detail = "; ".join(row["reasons"]) or row["window"]["reason"]
            print(f"  {row['symbol']}: {row['status']} -- {detail}")
        for row in payload["exits"]:
            print(
                f"  exit {row['position_id']} ({row['symbol']}): "
                f"{row['action']} -- {row['reason']}"
            )
        cap = payload["shared_cap"]
        print(
            f"  shared H6+H8 monthly premium headroom: "
            f"${cap['headroom']:,.2f} of ${cap['cap']:,.2f} "
            f"(used ${cap['used']:,.2f})"
        )
        for error in payload["errors"]:
            print(f"  BLOCKER: {error}", file=sys.stderr)
    return 2 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only forward-paper evaluator for registered H6 trial 7.

H6 is a directional experiment, not a recommendation engine and not a live
trading path.  This module applies the exact registered entry, capacity and
exit rules to injected or cached EOD facts.  It never writes the paper book,
places an order, fetches market data, or changes a hypothesis parameter.

The generic H4/H5 tactical-call preview is intentionally not reused: its
$600 cap, expiration ladder, and descriptive grading are different from H6.
"""
from __future__ import annotations

import csv
import fcntl
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import config
import metrics
from data.cache_runner import session_close_utc, trading_days
from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher.chains import is_monthly
from options_researcher.h6_features import (
    feature_manifest_path,
    verify_feature_manifest,
)
from options_researcher.h7_earnings import (
    ASSERTIONS_PATH,
    GATING_EVENT_CLASS,
    RAW_ASSERTIONS_PATH,
    assertions_view,
    load_assertions,
    report_date,
)
from research.hashing import canonical_json, sha256_file, sha256_hex

H6_BOOK_PATH = Path("data/positions/h6_positions.csv")
H6_RECEIPT_DIR = Path("reports/h6_forward")
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
EXIT_REASONS = ("take_profit", "time_21_dte")
H6_RECEIPT_SCHEMA = "h6_exact_session_watch_receipt_v1"
H6_TRIAL_INTENT_HASH = (
    "5d813b8fe0e89f2d04fe41c9b16561e2374ff873d784a3cd9f2c91e4fe52f3cf"
)
H6_SOURCE_PATHS = (
    "config.py",
    "data/cache_provenance.py",
    "metrics.py",
    "data/cache_runner.py",
    "data/pandas_feed.py",
    "data/thetadata_adapter.py",
    "options_researcher/chains.py",
    "options_researcher/features.py",
    "options_researcher/h6_features.py",
    "options_researcher/h6_watch.py",
    "options_researcher/h7_earnings.py",
    "research/hashing.py",
)
REPO_ROOT = Path(__file__).resolve().parents[1]
_CHAIN_FIELDS = {
    "expiration",
    "strike",
    "right",
    "delta",
    "bid",
    "ask",
    "open_interest",
}


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
class TimingDecision:
    state: str
    reason: str
    post_sessions: tuple[date, ...] = ()


@dataclass(frozen=True)
class EntryDecision:
    symbol: str
    evaluation_session: date
    status: str
    timing: TimingDecision
    iv_rank: float | None
    candidate: Candidate | None
    monthly_risk_used: float
    open_positions: int
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ExitDecision:
    position_id: str
    evaluation_session: date
    action: str
    reason: str
    dte: int
    proceeds: float | None
    pnl: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class H6Score:
    completed_positions: int
    verdict: str
    expectancy_ci90: tuple[float, float] | None
    hard_kill: bool
    reason: str

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
    """Select the registered H6 contract, or None when no contract passes.

    The earliest standard monthly in the frozen DTE band is selected first.
    Inside that expiration, the highest absolute delta passing every hard
    gate wins.  Exact-delta ties resolve by lower ask then lower strike; this
    deterministic identity tie-break does not relax any registered gate.
    """
    frame = _validated_chain(chain)
    lo_dte, hi_dte = config.H6_DTE_BAND
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
    lo_delta, hi_delta = config.H6_DELTA_BAND
    calls = calls.loc[
        calls["abs_delta"].between(lo_delta, hi_delta)
        & ((calls["ask"] * 100.0) <= config.H6_MAX_ASK_DOLLARS)
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
    contracts = config.H6_MAX_CONTRACTS_PER_NAME
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


def _post_report_sessions(assertion: dict) -> tuple[date, ...]:
    reported = report_date(assertion)
    timing = assertion.get("session_timing", "unknown")
    start = reported if timing == "bmo" else reported + timedelta(days=1)
    sessions = trading_days(start.isoformat(), (start + timedelta(days=14)).isoformat())
    return tuple(date.fromisoformat(day) for day in sessions[: config.H6_POST_EARNINGS_SESSIONS])


def timing_state(
    symbol: str,
    on: date,
    assertions: list[dict],
    *,
    known_as_of: datetime,
) -> TimingDecision:
    """Classify the registered H6 entry lane using causal earnings facts."""
    if known_as_of.tzinfo is None or known_as_of.utcoffset() is None:
        raise ValueError("known_as_of must be timezone-aware")
    view = [
        row
        for row in assertions_view(assertions, known_as_of)
        if row["symbol"] == symbol.upper()
        and row.get("event_class") == GATING_EVENT_CLASS
    ]
    if not view:
        return TimingDecision(
            "UNKNOWN", "no gating point-in-time assertions for symbol"
        )
    live = [row for row in view if row["status"] in ("estimated", "confirmed")]
    by_period: dict[str, set[date]] = {}
    for row in live:
        if row["fiscal_period"]:
            by_period.setdefault(row["fiscal_period"], set()).add(
                row["expected_date"]
            )
    for period, dates in sorted(by_period.items()):
        if len(dates) > 1 and max(dates) >= on:
            return TimingDecision(
                "UNKNOWN", f"conflicting schedule assertions for {period}"
            )

    occurred = [row for row in view if row["status"] == "occurred"]
    for row in sorted(occurred, key=report_date, reverse=True):
        post = _post_report_sessions(row)
        if on in post:
            return TimingDecision(
                "POST_REPORT", "inside first five post-report sessions", post
            )
        if report_date(row) == on:
            return TimingDecision(
                "PRE_REPORT_BANNED",
                "report occurred after the evaluated session entry window",
            )

    future = [row["expected_date"] for row in live if row["expected_date"] >= on]
    for report in future:
        start = report - timedelta(days=45)
        prior = [
            date.fromisoformat(day)
            for day in trading_days(start.isoformat(), report.isoformat())
            if day < report.isoformat()
        ]
        if len(prior) < config.H6_EARNINGS_BAN_SESSIONS:
            return TimingDecision(
                "UNKNOWN", f"cannot construct pre-report window for {report}"
            )
        if prior[-config.H6_EARNINGS_BAN_SESSIONS] <= on <= report:
            return TimingDecision(
                "PRE_REPORT_BANNED", "inside the H6 pre-report ban window"
            )
    if not future:
        return TimingDecision(
            "UNKNOWN", "no causally known next report outside post-report window"
        )
    return TimingDecision("IVR_GATED", "outside the post-report entry window")


def _book_state(book: list[BookPosition], on: date) -> tuple[list[BookPosition], float]:
    validate_book(book)
    for pos in book:
        if pos.entry_date > on:
            raise ValueError(f"book position {pos.id}: entry is after evaluation date")
        if pos.exit_date is not None and pos.exit_date > on:
            raise ValueError(f"book position {pos.id}: exit is after evaluation date")
    opened = [
        pos
        for pos in book
        if pos.exit_date is None or on <= pos.exit_date
    ]
    month_used = sum(
        pos.entry_cost
        for pos in book
        if (pos.entry_date.year, pos.entry_date.month) == (on.year, on.month)
    )
    return opened, round(month_used, 2)


def evaluate_entry(
    symbol: str,
    on: date,
    chain: pd.DataFrame,
    *,
    iv_rank: float | None,
    assertions: list[dict],
    known_as_of: datetime,
    book: list[BookPosition],
) -> EntryDecision:
    """Apply every registered H6 entry and portfolio gate; never write."""
    sym = symbol.upper()
    if sym not in config.H6_NAMES:
        raise ValueError(f"{sym} is outside registered H6 scope {config.H6_NAMES}")
    candidate = choose_contract(chain, on, symbol=sym)
    timing = timing_state(sym, on, assertions, known_as_of=known_as_of)
    opened, month_used = _book_state(book, on)
    reasons: list[str] = []

    if timing.state in ("UNKNOWN", "PRE_REPORT_BANNED"):
        reasons.append(f"earnings gate {timing.state}: {timing.reason}")
    elif timing.state == "IVR_GATED":
        try:
            ivr = math.nan if iv_rank is None else float(iv_rank)
        except (TypeError, ValueError):
            ivr = math.nan
        if not math.isfinite(ivr):
            reasons.append("IV-rank is unknown; H6 fails closed")
        elif ivr > config.H6_IVR_MAX:
            reasons.append(
                f"IV-rank {ivr:.4f} exceeds H6 maximum {config.H6_IVR_MAX:.4f}"
            )

    if candidate is None:
        reasons.append("no call passes H6 monthly/DTE/delta/ask/liquidity gates")
    else:
        if month_used + candidate.entry_cost > config.H6_MONTHLY_PREMIUM_AT_RISK:
            reasons.append(
                f"monthly gross premium risk ${month_used + candidate.entry_cost:,.2f} "
                f"exceeds ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.2f}"
            )
    if any(pos.symbol == sym for pos in opened):
        reasons.append(f"{sym} already open; H6 allows one contract per name")
    if len(opened) >= config.H6_MAX_CONCURRENT:
        reasons.append(
            f"open H6 positions {len(opened)} reaches cap {config.H6_MAX_CONCURRENT}"
        )

    clean_ivr = None
    try:
        parsed_ivr = math.nan if iv_rank is None else float(iv_rank)
        if math.isfinite(parsed_ivr):
            clean_ivr = parsed_ivr
    except (TypeError, ValueError):
        pass
    return EntryDecision(
        symbol=sym,
        evaluation_session=on,
        status="BLOCKED" if reasons else "ELIGIBLE",
        timing=timing,
        iv_rank=clean_ivr,
        candidate=candidate,
        monthly_risk_used=month_used,
        open_positions=len(opened),
        reasons=tuple(reasons),
    )


def evaluate_exit(
    position: BookPosition, on: date, chain: pd.DataFrame
) -> ExitDecision:
    """Mark one open H6 paper position at the frozen conservative sale."""
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
            position.id, on, "BLOCKED", "quote_missing_or_ambiguous", dte, None, None
        )
    row = matches.iloc[0]
    if not quote_valid(row["bid"], row["ask"]):
        return ExitDecision(
            position.id, on, "BLOCKED", "invalid_exit_quote", dte, None, None
        )
    proceeds = (
        adverse_sell(row["bid"]) * 100.0 * position.contracts
        - config.COMMISSION_PER_CONTRACT * position.contracts
    )
    proceeds = round(proceeds, 2)
    pnl = round(proceeds - position.entry_cost, 2)
    if proceeds >= position.entry_cost * (1.0 + config.H6_TAKE_PROFIT_PCT):
        return ExitDecision(
            position.id, on, "CLOSE", "take_profit", dte, proceeds, pnl
        )
    if dte <= config.H6_CLOSE_AT_DTE:
        return ExitDecision(
            position.id, on, "CLOSE", "time_21_dte", dte, proceeds, pnl
        )
    return ExitDecision(position.id, on, "HOLD", "no_exit_trigger", dte, proceeds, pnl)


def _require_session(day: date, ctx: str) -> None:
    iso = day.isoformat()
    if trading_days(iso, iso) != [iso]:
        raise ValueError(f"{ctx}: {iso} is not an XNYS session")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_book(book: list[BookPosition]) -> None:
    """Prove all registered H6 book invariants across the full history.

    This validation is deliberately independent of CSV parsing so injected
    books, scoring calls, and future storage adapters cannot bypass it.
    Position intervals are inclusive of the exit session: the watch evaluates
    capacity before same-session closes, so an exit cannot free risk for a new
    entry until the next session.
    """
    seen: set[str] = set()
    max_entry_cost = (
        adverse_buy(config.H6_MAX_ASK_DOLLARS / 100.0)
        * 100.0
        * config.H6_MAX_CONTRACTS_PER_NAME
        + config.COMMISSION_PER_CONTRACT * config.H6_MAX_CONTRACTS_PER_NAME
    )
    monthly: dict[tuple[int, int], float] = {}
    change_dates: set[date] = set()
    for pos in book:
        ctx = f"book position {pos.id!r}"
        if not isinstance(pos.id, str) or not pos.id.strip() or pos.id in seen:
            raise ValueError(f"{ctx}: id missing or duplicate")
        seen.add(pos.id)
        if pos.symbol not in config.H6_NAMES:
            raise ValueError(f"{ctx}: symbol {pos.symbol!r} is outside H6")
        if pos.contracts != config.H6_MAX_CONTRACTS_PER_NAME:
            raise ValueError(
                f"{ctx}: contracts must equal {config.H6_MAX_CONTRACTS_PER_NAME}"
            )
        if not math.isfinite(float(pos.strike)) or pos.strike <= 0:
            raise ValueError(f"{ctx}: strike must be finite and positive")
        if type(pos.entry_date) is not date or type(pos.expiration) is not date:
            raise ValueError(f"{ctx}: entry_date and expiration must be dates")
        _require_session(pos.entry_date, f"{ctx} entry_date")
        entry_dte = (pos.expiration - pos.entry_date).days
        if not is_monthly(pos.expiration):
            raise ValueError(f"{ctx}: expiration is not a standard monthly")
        if not config.H6_DTE_BAND[0] <= entry_dte <= config.H6_DTE_BAND[1]:
            raise ValueError(
                f"{ctx}: entry DTE {entry_dte} is outside {config.H6_DTE_BAND}"
            )
        if not math.isfinite(float(pos.entry_cost)) or pos.entry_cost <= 0:
            raise ValueError(f"{ctx}: entry_cost must be finite and positive")
        if not _is_sha256(pos.entry_receipt_hash):
            raise ValueError(f"{ctx}: entry_receipt_hash must be lowercase SHA-256")
        if pos.entry_cost > max_entry_cost:
            raise ValueError(
                f"{ctx}: entry_cost ${pos.entry_cost:,.2f} exceeds the maximum "
                f"consistent with H6's raw-ask gate (${max_entry_cost:,.2f})"
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
                raise ValueError(
                    f"{ctx}: exit_proceeds must be finite and nonnegative"
                )
            if pos.exit_reason not in EXIT_REASONS:
                raise ValueError(f"{ctx}: exit_reason must be one of {EXIT_REASONS}")
            if not _is_sha256(pos.exit_receipt_hash):
                raise ValueError(
                    f"{ctx}: exit_receipt_hash must be lowercase SHA-256"
                )
            if (
                pos.exit_reason == "take_profit"
                and pos.exit_proceeds
                < pos.entry_cost * (1.0 + config.H6_TAKE_PROFIT_PCT)
            ):
                raise ValueError(
                    f"{ctx}: take_profit proceeds do not reach +100% of premium"
                )
            exit_dte = (pos.expiration - pos.exit_date).days
            if (
                pos.exit_reason == "time_21_dte"
                and exit_dte > config.H6_CLOSE_AT_DTE
            ):
                raise ValueError(
                    f"{ctx}: time_21_dte exit occurred at {exit_dte} DTE"
                )
            if (
                pos.exit_reason == "time_21_dte"
                and pos.exit_proceeds
                >= pos.entry_cost * (1.0 + config.H6_TAKE_PROFIT_PCT)
            ):
                raise ValueError(
                    f"{ctx}: time_21_dte exit met the earlier take-profit rule"
                )

        key = (pos.entry_date.year, pos.entry_date.month)
        monthly[key] = monthly.get(key, 0.0) + pos.entry_cost
        change_dates.add(pos.entry_date)
        if pos.exit_date is not None:
            change_dates.add(pos.exit_date)

    for key, gross in monthly.items():
        if gross > config.H6_MONTHLY_PREMIUM_AT_RISK:
            raise ValueError(
                f"book {key[0]:04d}-{key[1]:02d} gross premium risk "
                f"${gross:,.2f} exceeds ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.2f}"
            )

    for day in sorted(change_dates):
        active = [
            pos
            for pos in book
            if pos.entry_date <= day
            and (pos.exit_date is None or day <= pos.exit_date)
        ]
        if len(active) > config.H6_MAX_CONCURRENT:
            raise ValueError(
                f"concurrent H6 positions {len(active)} exceeds "
                f"{config.H6_MAX_CONCURRENT} on {day}"
            )
        symbols = [pos.symbol for pos in active]
        for symbol in sorted(set(symbols)):
            if symbols.count(symbol) > 1:
                raise ValueError(
                    f"overlapping H6 positions for {symbol} on {day}"
                )


def load_book(
    path: Path = H6_BOOK_PATH,
    *,
    receipt_dir: Path = H6_RECEIPT_DIR,
    verify_receipts: bool = True,
) -> list[BookPosition]:
    """Load and validate the manually maintained H6 forward-paper book."""
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
        if symbol not in config.H6_NAMES:
            raise ValueError(f"{ctx}: symbol {symbol!r} is outside H6")
        try:
            strike = float(row["strike"])
            expiration = date.fromisoformat(row["expiration"])
            contracts = int(row["contracts"])
            entry_date = date.fromisoformat(row["entry_date"])
            entry_cost = float(row["entry_cost"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{ctx}: malformed entry fields: {exc}") from exc
        if not math.isfinite(strike) or strike <= 0:
            raise ValueError(f"{ctx}: strike must be finite and positive")
        if contracts != config.H6_MAX_CONTRACTS_PER_NAME:
            raise ValueError(
                f"{ctx}: contracts must equal {config.H6_MAX_CONTRACTS_PER_NAME}"
            )
        if not math.isfinite(entry_cost) or entry_cost <= 0:
            raise ValueError(f"{ctx}: entry_cost must be finite and positive")
        if expiration <= entry_date:
            raise ValueError(f"{ctx}: expiration must follow entry_date")
        entry_receipt_hash = row["entry_receipt_hash"].strip()
        if not _is_sha256(entry_receipt_hash):
            raise ValueError(f"{ctx}: entry_receipt_hash must be lowercase SHA-256")
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
            if exit_reason not in EXIT_REASONS:
                raise ValueError(f"{ctx}: exit_reason must be one of {EXIT_REASONS}")
            if exit_date < entry_date:
                raise ValueError(f"{ctx}: exit_date predates entry_date")
            if not math.isfinite(exit_proceeds) or exit_proceeds < 0:
                raise ValueError(f"{ctx}: exit_proceeds must be finite and nonnegative")
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
    if verify_receipts:
        verify_book_receipts(out, receipt_dir=receipt_dir)
    return out


def _month_after(key: tuple[int, int]) -> tuple[int, int]:
    year, month = key
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _hard_kill(book: list[BookPosition]) -> bool:
    realized: dict[tuple[int, int], float] = {}
    for pos in book:
        if pos.exit_date is None or pos.exit_proceeds is None:
            continue
        key = (pos.exit_date.year, pos.exit_date.month)
        realized[key] = realized.get(key, 0.0) + (
            pos.exit_proceeds - pos.entry_cost
        )
    full_loss = {
        key
        for key, pnl in realized.items()
        if pnl <= -config.H6_MONTHLY_PREMIUM_AT_RISK
    }
    required = config.H6_HARD_KILL_FULL_LOSS_MONTHS
    if required <= 0:
        raise ValueError("H6_HARD_KILL_FULL_LOSS_MONTHS must be positive")
    for first in full_loss:
        months = [first]
        for _ in range(1, required):
            months.append(_month_after(months[-1]))
        if all(month in full_loss for month in months):
            return True
    return False


def score_book(
    book: list[BookPosition], *, n_boot: int | None = None, seed: int = 42
) -> H6Score:
    """Apply the registered H6 continuation/rejection rule to closed rows."""
    validate_book(book)
    completed = [
        pos
        for pos in book
        if pos.exit_date is not None and pos.exit_proceeds is not None
    ]
    if _hard_kill(completed):
        return H6Score(
            len(completed),
            "REJECT",
            None,
            True,
            f"{config.H6_HARD_KILL_FULL_LOSS_MONTHS} consecutive months "
            f"realized the full ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.0f} "
            "cap as losses",
        )
    if len(completed) < config.H6_MIN_COMPLETED_POSITIONS:
        return H6Score(
            len(completed),
            "INSUFFICIENT_SAMPLE",
            None,
            False,
            f"requires {config.H6_MIN_COMPLETED_POSITIONS} completed positions",
        )
    pnls: list[float] = []
    for pos in completed:
        if pos.exit_proceeds is None:  # narrowed above; defensive for type checker
            raise AssertionError("completed H6 position is missing exit proceeds")
        pnls.append(float(pos.exit_proceeds - pos.entry_cost))
    entry_dates = [pos.entry_date for pos in completed]
    lo, hi = metrics.dependence_aware_expectancy_ci(
        entry_dates, pnls, n_boot=n_boot, seed=seed
    )
    if not (math.isfinite(lo) and math.isfinite(hi)):
        return H6Score(
            len(completed),
            "BLOCKED",
            None,
            False,
            "dependence-aware CI90 is not estimable from the recorded cohorts",
        )
    ci = (float(lo), float(hi))
    if hi < 0:
        return H6Score(
            len(completed), "REJECT", ci, False, "CI90 upper bound is below zero"
        )
    if lo > 0:
        return H6Score(
            len(completed), "EXTEND", ci, False, "CI90 lower bound is above zero"
        )
    return H6Score(
        len(completed),
        "CONTINUE",
        ci,
        False,
        "CI90 includes zero; H6 is not resolved",
    )


def _feature_iv_rank(
    symbol: str, on: date, feature_dir: Path, chain_dir: Path
) -> float:
    path = feature_dir / f"{symbol}_features.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing; run options_researcher.h6_features first"
        )
    verify_feature_manifest(
        symbol, on, feature_dir=feature_dir, chain_dir=chain_dir
    )
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


def h6_config_snapshot() -> dict:
    """Return the explicit verdict-affecting H6 configuration surface."""
    names = (
        "H6_NAMES",
        "H6_EARNINGS_BAN_SESSIONS",
        "H6_POST_EARNINGS_SESSIONS",
        "H6_IVR_MAX",
        "H6_DTE_BAND",
        "H6_DELTA_BAND",
        "H6_MAX_ASK_DOLLARS",
        "H6_MONTHLY_PREMIUM_AT_RISK",
        "H6_MAX_CONTRACTS_PER_NAME",
        "H6_MAX_CONCURRENT",
        "H6_TAKE_PROFIT_PCT",
        "H6_CLOSE_AT_DTE",
        "H6_MIN_COMPLETED_POSITIONS",
        "H6_HARD_KILL_FULL_LOSS_MONTHS",
        "MIN_OPEN_INTEREST",
        "MAX_SPREAD_PCT",
        "COMMISSION_PER_CONTRACT",
        "SLIPPAGE_HAIRCUT",
        "FILL_MODEL_ID",
        "BOOTSTRAP_SAMPLES",
        "BOOTSTRAP_BLOCK_EXPONENT",
        "BOOTSTRAP_BLOCK_CONSTANTS",
    )
    return _json_safe({name: getattr(config, name) for name in names})


def build_snapshot(
    on: date,
    *,
    book_path: Path = H6_BOOK_PATH,
    chain_dir: Path = Path(".cache/chains"),
    feature_dir: Path = Path(".tmp/research"),
    assertions_path: Path = ASSERTIONS_PATH,
    raw_assertions_path: Path = RAW_ASSERTIONS_PATH,
    receipt_dir: Path = H6_RECEIPT_DIR,
) -> tuple[dict, dict[str, Path]]:
    """Evaluate one completed H6 session and return every consumed input path."""
    iso = on.isoformat()
    _require_session(on, "evaluation_session")
    known_as_of = session_close_utc(iso)
    if datetime.now(timezone.utc) < known_as_of:
        raise ValueError(
            f"session {iso} is incomplete until {known_as_of.isoformat()}"
        )

    book_path = Path(book_path)
    assertions_path = Path(assertions_path)
    raw_assertions_path = Path(raw_assertions_path)
    chain_dir = Path(chain_dir)
    feature_dir = Path(feature_dir)
    book = load_book(book_path, receipt_dir=receipt_dir)
    assertions = load_assertions(assertions_path, raw_path=raw_assertions_path)
    inputs: dict[str, Path] = {
        "book": book_path,
        "earnings_gating": assertions_path,
        "earnings_raw": raw_assertions_path,
    }
    entries: list[dict] = []
    exits: list[dict] = []
    errors: list[str] = []
    chains: dict[str, pd.DataFrame] = {}
    for symbol in config.H6_NAMES:
        chain_path = chain_dir / f"{symbol}_{iso}.parquet"
        feature_path = feature_dir / f"{symbol}_features.parquet"
        manifest_path = feature_manifest_path(symbol, feature_dir)
        inputs[f"chain:{symbol}"] = chain_path
        inputs[f"feature:{symbol}"] = feature_path
        inputs[f"feature_manifest:{symbol}"] = manifest_path
        try:
            if not chain_path.exists():
                raise FileNotFoundError(f"exact chain missing: {chain_path}")
            chain = pd.read_parquet(chain_path)
            chains[symbol] = chain
            iv_rank = _feature_iv_rank(symbol, on, feature_dir, chain_dir)
            entries.append(
                evaluate_entry(
                    symbol,
                    on,
                    chain,
                    iv_rank=iv_rank,
                    assertions=assertions,
                    known_as_of=known_as_of,
                    book=book,
                ).to_dict()
            )
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            errors.append(f"{symbol}: {exc}")
    for pos in (row for row in book if row.is_open):
        try:
            chain = chains.get(pos.symbol)
            if chain is None:
                chain_path = chain_dir / f"{pos.symbol}_{iso}.parquet"
                if not chain_path.exists():
                    raise FileNotFoundError(f"exact chain missing: {chain_path}")
                chain = pd.read_parquet(chain_path)
            exits.append(evaluate_exit(pos, on, chain).to_dict())
        except (FileNotFoundError, ValueError, RuntimeError) as exc:
            errors.append(f"exit {pos.id}: {exc}")

    payload = {
        "mode": "FORWARD_PAPER_ONLY",
        "live_orders": False,
        "evaluation_session": iso,
        "known_as_of_utc": known_as_of,
        "entries": entries,
        "exits": exits,
        "score": score_book(book).to_dict(),
        "errors": errors,
    }
    return _json_safe(payload), inputs


def build_receipt(snapshot: dict, inputs: dict[str, Path]) -> dict:
    """Bind a clean exact-session decision to all facts, rules, and code."""
    errors = snapshot.get("errors")
    if errors:
        raise ValueError(f"refusing H6 receipt with blockers: {errors}")
    missing = [label for label, path in inputs.items() if not Path(path).is_file()]
    if missing:
        raise FileNotFoundError(f"H6 receipt inputs missing: {sorted(missing)}")
    input_files = {
        label: {"path": str(Path(path)), "sha256": sha256_file(Path(path))}
        for label, path in sorted(inputs.items())
    }
    source_files = {
        rel: sha256_file(REPO_ROOT / rel) for rel in H6_SOURCE_PATHS
    }
    config_snapshot = h6_config_snapshot()
    receipt = {
        "schema": H6_RECEIPT_SCHEMA,
        "hypothesis_id": "H6",
        "trial_intent_record_hash": H6_TRIAL_INTENT_HASH,
        "snapshot": _json_safe(snapshot),
        "config": config_snapshot,
        "config_hash": sha256_hex(canonical_json(config_snapshot)),
        "input_files": input_files,
        "input_files_hash": sha256_hex(canonical_json(input_files)),
        "source_files": source_files,
        "source_hash": sha256_hex(canonical_json(source_files)),
    }
    receipt["receipt_hash"] = sha256_hex(canonical_json(receipt))
    return receipt


def _durable_sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def write_receipt(receipt: dict, path: Path) -> str:
    """Atomically create one immutable receipt; only identical replay is allowed."""
    path = Path(path)
    payload = canonical_json(receipt) + "\n"
    if path.exists():
        existing = path.read_text()
        if existing == payload:
            return str(receipt["receipt_hash"])
        raise FileExistsError(f"refusing to overwrite non-identical H6 receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        data = payload.encode("utf-8")
        offset = 0
        while offset < len(data):
            offset += os.write(fd, data[offset:])
        _durable_sync(fd)
    except BaseException:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(fd)
    os.replace(tmp, path)
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return str(receipt["receipt_hash"])


def verify_receipt(receipt: dict, current: dict) -> list[str]:
    """Return named integrity differences between a stored and recomputed receipt."""
    failures: list[str] = []
    stored_hashable = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    if sha256_hex(canonical_json(stored_hashable)) != receipt.get("receipt_hash"):
        failures.append("receipt_hash")
    for key in sorted(set(receipt) | set(current)):
        if key == "receipt_hash":
            continue
        if canonical_json(receipt.get(key)) != canonical_json(current.get(key)):
            failures.append(key)
    return failures


def _receipt_index(receipt_dir: Path, wanted: set[str]) -> dict[str, dict]:
    if not wanted:
        return {}
    receipt_dir = Path(receipt_dir)
    if not receipt_dir.is_dir():
        raise FileNotFoundError(f"H6 receipt directory missing: {receipt_dir}")
    found: dict[str, dict] = {}
    for path in sorted(receipt_dir.glob("*.json")):
        try:
            receipt = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"malformed H6 receipt {path}: {exc}") from exc
        if not isinstance(receipt, dict):
            raise ValueError(f"malformed H6 receipt {path}: root must be an object")
        receipt_hash = receipt.get("receipt_hash")
        if not _is_sha256(receipt_hash):
            raise ValueError(f"malformed H6 receipt {path}: invalid receipt_hash")
        hashable = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        try:
            actual_hash = sha256_hex(canonical_json(hashable))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"malformed H6 receipt {path}: {exc}") from exc
        if actual_hash != receipt_hash:
            raise ValueError(f"tampered H6 receipt {path}: receipt_hash mismatch")
        if receipt_hash in found:
            raise ValueError(
                f"duplicate H6 receipt hash {receipt_hash} in {receipt_dir}"
            )
        if receipt_hash in wanted:
            found[receipt_hash] = receipt
    missing = sorted(wanted - set(found))
    if missing:
        raise FileNotFoundError(
            f"referenced H6 receipt hash(es) missing from {receipt_dir}: {missing}"
        )
    return found


def _bound_snapshot(receipt: dict, receipt_hash: str) -> dict:
    if receipt.get("schema") != H6_RECEIPT_SCHEMA:
        raise ValueError(f"H6 receipt {receipt_hash}: unsupported schema")
    if receipt.get("hypothesis_id") != "H6":
        raise ValueError(f"H6 receipt {receipt_hash}: wrong hypothesis_id")
    if receipt.get("trial_intent_record_hash") != H6_TRIAL_INTENT_HASH:
        raise ValueError(f"H6 receipt {receipt_hash}: wrong trial registration")
    snapshot = receipt.get("snapshot")
    if not isinstance(snapshot, dict):
        raise ValueError(f"H6 receipt {receipt_hash}: snapshot must be an object")
    if snapshot.get("mode") != "FORWARD_PAPER_ONLY" or snapshot.get("live_orders"):
        raise ValueError(f"H6 receipt {receipt_hash}: unsafe mode identity")
    if snapshot.get("errors") != []:
        raise ValueError(f"H6 receipt {receipt_hash}: snapshot contains blockers")
    return snapshot


def _same_number(left: object, right: float) -> bool:
    if isinstance(left, bool) or not isinstance(left, (int, float, str)):
        return False
    try:
        return math.isclose(float(left), right, rel_tol=0.0, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def verify_book_receipts(
    book: list[BookPosition], *, receipt_dir: Path = H6_RECEIPT_DIR
) -> None:
    """Require one tamper-evident exact-session decision per recorded action."""
    refs: list[str] = [pos.entry_receipt_hash for pos in book]
    refs.extend(
        pos.exit_receipt_hash
        for pos in book
        if pos.exit_receipt_hash is not None
    )
    if len(refs) != len(set(refs)):
        raise ValueError(
            "each H6 receipt may authorize exactly one book action; receipt reused"
        )
    receipts = _receipt_index(Path(receipt_dir), set(refs))
    for pos in book:
        entry_hash = pos.entry_receipt_hash
        entry_snapshot = _bound_snapshot(receipts[entry_hash], entry_hash)
        if entry_snapshot.get("evaluation_session") != pos.entry_date.isoformat():
            raise ValueError(
                f"book position {pos.id!r}: entry receipt session mismatch"
            )
        entry_matches = [
            row
            for row in entry_snapshot.get("entries", [])
            if isinstance(row, dict)
            and row.get("symbol") == pos.symbol
            and row.get("status") == "ELIGIBLE"
        ]
        if len(entry_matches) != 1:
            raise ValueError(
                f"book position {pos.id!r}: entry receipt lacks one ELIGIBLE decision"
            )
        candidate = entry_matches[0].get("candidate")
        if not isinstance(candidate, dict):
            raise ValueError(
                f"book position {pos.id!r}: entry receipt candidate missing"
            )
        entry_identity_ok = (
            candidate.get("symbol") == pos.symbol
            and candidate.get("expiration") == pos.expiration.isoformat()
            and _same_number(candidate.get("strike"), pos.strike)
            and _same_number(candidate.get("entry_cost"), pos.entry_cost)
        )
        if not entry_identity_ok:
            raise ValueError(
                f"book position {pos.id!r}: entry differs from receipt candidate"
            )

        if pos.exit_receipt_hash is None:
            continue
        if pos.exit_date is None or pos.exit_proceeds is None or pos.exit_reason is None:
            raise AssertionError("validated closed H6 position is incomplete")
        exit_hash = pos.exit_receipt_hash
        exit_snapshot = _bound_snapshot(receipts[exit_hash], exit_hash)
        if exit_snapshot.get("evaluation_session") != pos.exit_date.isoformat():
            raise ValueError(
                f"book position {pos.id!r}: exit receipt session mismatch"
            )
        exit_matches = [
            row
            for row in exit_snapshot.get("exits", [])
            if isinstance(row, dict) and row.get("position_id") == pos.id
        ]
        if len(exit_matches) != 1:
            raise ValueError(
                f"book position {pos.id!r}: exit receipt lacks one decision"
            )
        decision = exit_matches[0]
        exit_identity_ok = (
            decision.get("action") == "CLOSE"
            and decision.get("reason") == pos.exit_reason
            and _same_number(decision.get("proceeds"), pos.exit_proceeds)
        )
        if not exit_identity_ok:
            raise ValueError(
                f"book position {pos.id!r}: exit differs from receipt decision"
            )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Read-only exact-session H6 forward-paper watch"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--book", type=Path, default=H6_BOOK_PATH)
    parser.add_argument("--chain-dir", type=Path, default=Path(".cache/chains"))
    parser.add_argument("--feature-dir", type=Path, default=Path(".tmp/research"))
    parser.add_argument("--assertions", type=Path, default=ASSERTIONS_PATH)
    parser.add_argument("--raw-assertions", type=Path, default=RAW_ASSERTIONS_PATH)
    parser.add_argument("--receipt-dir", type=Path, default=H6_RECEIPT_DIR)
    receipt_group = parser.add_mutually_exclusive_group()
    receipt_group.add_argument("--write-receipt", type=Path)
    receipt_group.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    iso = args.as_of.isoformat()
    try:
        payload, inputs = build_snapshot(
            args.as_of,
            book_path=args.book,
            chain_dir=args.chain_dir,
            feature_dir=args.feature_dir,
            assertions_path=args.assertions,
            raw_assertions_path=args.raw_assertions,
            receipt_dir=args.receipt_dir,
        )
        if args.write_receipt or args.verify_receipt:
            current_receipt = build_receipt(payload, inputs)
            if args.write_receipt:
                receipt_hash = write_receipt(current_receipt, args.write_receipt)
                payload["receipt"] = {
                    "action": "WROTE",
                    "path": str(args.write_receipt),
                    "receipt_hash": receipt_hash,
                }
            else:
                stored = json.loads(args.verify_receipt.read_text())
                if not isinstance(stored, dict):
                    raise ValueError("H6 receipt root must be an object")
                failures = verify_receipt(stored, current_receipt)
                payload["receipt"] = {
                    "action": "VERIFIED" if not failures else "INVALID",
                    "path": str(args.verify_receipt),
                    "receipt_hash": stored.get("receipt_hash"),
                    "failures": failures,
                }
                if failures:
                    payload["errors"].append(
                        f"receipt invalid; mutated surfaces: {failures}"
                    )
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if args.json:
        print(json.dumps(payload, sort_keys=True, indent=2))
    else:
        print(f"H6 FORWARD PAPER ONLY @ {iso} -- live orders: disabled")
        for row in payload["entries"]:
            reasons = "; ".join(row["reasons"]) or "all registered gates pass"
            print(f"  {row['symbol']}: {row['status']} -- {reasons}")
        for row in payload["exits"]:
            print(f"  exit {row['position_id']}: {row['action']} -- {row['reason']}")
        score = payload["score"]
        print(
            f"  score: {score['verdict']} ({score['completed_positions']} completed)"
        )
        if receipt := payload.get("receipt"):
            print(f"  receipt: {receipt['action']} -- {receipt['path']}")
        for error in payload["errors"]:
            print(f"  BLOCKER: {error}", file=sys.stderr)
    return 2 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

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
import json
import math
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
from options_researcher.h7_earnings import (
    GATING_EVENT_CLASS,
    assertions_view,
    report_date,
)

H6_BOOK_PATH = Path("data/positions/h6_positions.csv")
BOOK_FIELDS = (
    "id",
    "symbol",
    "strike",
    "expiration",
    "contracts",
    "entry_date",
    "entry_cost",
    "exit_date",
    "exit_proceeds",
    "exit_reason",
)
EXIT_REASONS = ("take_profit", "time_21_dte")
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
    exit_date: date | None = None
    exit_proceeds: float | None = None
    exit_reason: str | None = None

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
    for pos in book:
        if pos.entry_date > on:
            raise ValueError(f"book position {pos.id}: entry is after evaluation date")
        if pos.exit_date is not None and pos.exit_date > on:
            raise ValueError(f"book position {pos.id}: exit is after evaluation date")
    opened = [pos for pos in book if pos.is_open]
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


def load_book(path: Path = H6_BOOK_PATH) -> list[BookPosition]:
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
        exit_values = [
            row["exit_date"].strip(),
            row["exit_proceeds"].strip(),
            row["exit_reason"].strip(),
        ]
        if any(exit_values) and not all(exit_values):
            raise ValueError(f"{ctx}: close fields must be all present or all empty")
        exit_date = None
        exit_proceeds = None
        exit_reason = None
        if all(exit_values):
            try:
                exit_date = date.fromisoformat(exit_values[0])
                exit_proceeds = float(exit_values[1])
            except ValueError as exc:
                raise ValueError(f"{ctx}: malformed close fields: {exc}") from exc
            exit_reason = exit_values[2]
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
                exit_date=exit_date,
                exit_proceeds=exit_proceeds,
                exit_reason=exit_reason,
            )
        )

    opened = [pos for pos in out if pos.is_open]
    open_symbols = [pos.symbol for pos in opened]
    if len(open_symbols) != len(set(open_symbols)):
        raise ValueError(f"{path}: more than one open H6 contract for a name")
    if len(opened) > config.H6_MAX_CONCURRENT:
        raise ValueError(f"{path}: open H6 position cap exceeded")
    monthly: dict[tuple[int, int], float] = {}
    for pos in out:
        key = (pos.entry_date.year, pos.entry_date.month)
        monthly[key] = monthly.get(key, 0.0) + pos.entry_cost
    for key, gross in monthly.items():
        if gross > config.H6_MONTHLY_PREMIUM_AT_RISK:
            raise ValueError(
                f"{path}: {key[0]:04d}-{key[1]:02d} gross premium risk "
                f"${gross:,.2f} exceeds ${config.H6_MONTHLY_PREMIUM_AT_RISK:,.2f}"
            )
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
    for first in full_loss:
        second = _month_after(first)
        third = _month_after(second)
        if second in full_loss and third in full_loss:
            return True
    return False


def score_book(
    book: list[BookPosition], *, n_boot: int | None = None, seed: int = 42
) -> H6Score:
    """Apply the registered H6 continuation/rejection rule to closed rows."""
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
            "three consecutive months realized the full $2,000 cap as losses",
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


def _feature_iv_rank(symbol: str, on: date, feature_dir: Path) -> float:
    path = feature_dir / f"{symbol}_features.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} missing; run options_researcher.h6_features first"
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


def main(argv: list[str] | None = None) -> int:
    import argparse

    from options_researcher.h7_earnings import load_assertions

    parser = argparse.ArgumentParser(
        description="Read-only exact-session H6 forward-paper watch"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--book", type=Path, default=H6_BOOK_PATH)
    parser.add_argument("--chain-dir", type=Path, default=Path(".cache/chains"))
    parser.add_argument("--feature-dir", type=Path, default=Path(".tmp/research"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    iso = args.as_of.isoformat()
    if trading_days(iso, iso) != [iso]:
        parser.error(f"--as-of must be an XNYS session: {iso}")
    known_as_of = session_close_utc(iso)
    if datetime.now(timezone.utc) < known_as_of:
        parser.error(f"session {iso} is incomplete until {known_as_of.isoformat()}")

    book = load_book(args.book)
    assertions = load_assertions()
    entries: list[dict] = []
    exits: list[dict] = []
    errors: list[str] = []
    chains: dict[str, pd.DataFrame] = {}
    for symbol in config.H6_NAMES:
        path = args.chain_dir / f"{symbol}_{iso}.parquet"
        try:
            if not path.exists():
                raise FileNotFoundError(f"exact chain missing: {path}")
            chain = pd.read_parquet(path)
            chains[symbol] = chain
            iv_rank = _feature_iv_rank(symbol, args.as_of, args.feature_dir)
            entries.append(
                evaluate_entry(
                    symbol,
                    args.as_of,
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
                path = args.chain_dir / f"{pos.symbol}_{iso}.parquet"
                if not path.exists():
                    raise FileNotFoundError(f"exact chain missing: {path}")
                chain = pd.read_parquet(path)
            exits.append(evaluate_exit(pos, args.as_of, chain).to_dict())
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
    if args.json:
        print(json.dumps(payload, default=_json_default, sort_keys=True, indent=2))
    else:
        print(f"H6 FORWARD PAPER ONLY @ {iso} -- live orders: disabled")
        for row in entries:
            reasons = "; ".join(row["reasons"]) or "all registered gates pass"
            print(f"  {row['symbol']}: {row['status']} -- {reasons}")
        for row in exits:
            print(f"  exit {row['position_id']}: {row['action']} -- {row['reason']}")
        score = payload["score"]
        print(
            f"  score: {score['verdict']} ({score['completed_positions']} completed)"
        )
        for error in errors:
            print(f"  BLOCKER: {error}", file=sys.stderr)
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

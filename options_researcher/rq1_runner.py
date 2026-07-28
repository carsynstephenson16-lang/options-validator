"""One-run descriptive RQ1 rank-quality study.

RQ1 measures whether the frozen pre-badge scanner's daily name ranking is
associated with the next 21 trading sessions of realized volatility and IV
change. It is descriptive only: it does not grade, rank, trigger, trade, or
promote a feature.

The default board reconstruction uses the existing pre-badge card builders and
only data at or before each board date. Tests inject board rows so the causal
and one-run contracts stay offline and fast. A report path is write-once; a
second invocation refuses before loading data.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import subprocess
from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

import config

DEFAULT_REPORT_PATH = Path("reports/rq1/rq1-v1.json")
HORIZON_SESSIONS = config.RQ1_HORIZON_SESSIONS
NOTABLE_ABS_RHO = config.RQ1_NOTABLE_ABS_RHO
REGISTRATION_SEQ = 17
logger = logging.getLogger(__name__)


class RQ1Error(RuntimeError):
    """RQ1 cannot produce a trustworthy one-run artifact."""


class OneRunError(RQ1Error):
    """The write-once report already exists or the result is already ledgered."""


def green_fraction(grades: Mapping[str, object]) -> float | None:
    """Return the existing card's GREEN fraction, including UNKNOWN in N."""
    if not grades:
        return None
    values = list(grades.values())
    return sum(value == "GREEN" for value in values) / len(values)


def spearman_rho(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Spearman correlation, returning None for fewer than two observations."""
    if len(x) != len(y) or len(x) < 2:
        return None
    left = pd.Series(list(x), dtype=float)
    right = pd.Series(list(y), dtype=float)
    if not np.isfinite(left).all() or not np.isfinite(right).all():
        raise ValueError("spearman inputs must be finite")
    result = left.rank(method="average").corr(right.rank(method="average"))
    return None if pd.isna(result) else float(result)


def forward_realized_vol(closes: pd.Series, *, horizon: int = HORIZON_SESSIONS) -> pd.Series:
    """Annualized realized volatility over returns from t+1 through t+h.

    The shift is deliberate: the signal day's return is not allowed into its
    own outcome window.
    """
    if horizon < 2:
        raise ValueError("horizon must be at least 2 for sample standard deviation")
    values = closes.astype(float).sort_index()
    if values.index.has_duplicates:
        raise ValueError("close index contains duplicate sessions")
    if (values <= 0).any() or not np.isfinite(values).all():
        raise ValueError("closes must be finite and positive")
    log_values = np.log(values.to_numpy(dtype=float))
    returns = pd.Series(log_values, index=values.index).diff()
    return returns.rolling(horizon).std(ddof=1).shift(-horizon) * np.sqrt(
        config.RQ1_RV_ANNUALIZATION_SESSIONS
    )


def filter_causal_board_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Drop synthetic, lookahead, and malformed board rows fail-closed."""
    excluded = {
        "synthetic": 0,
        "lookahead_contaminated": 0,
        "future_feature_row": 0,
        "invalid": 0,
    }
    kept: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        try:
            board_date = date.fromisoformat(str(row["date"]))
            feature_date = date.fromisoformat(str(row["features_as_of"]))
            score = float(row["green_fraction"])
            if not 0.0 <= score <= 1.0 or not math.isfinite(score):
                raise ValueError("green_fraction out of range")
        except (KeyError, TypeError, ValueError):
            excluded["invalid"] += 1
            continue
        if row.get("synthetic") is True:
            excluded["synthetic"] += 1
            continue
        if row.get("lookahead_contaminated") is True:
            excluded["lookahead_contaminated"] += 1
            continue
        if feature_date > board_date:
            excluded["future_feature_row"] += 1
            continue
        row["date"] = board_date.isoformat()
        row["features_as_of"] = feature_date.isoformat()
        row["green_fraction"] = score
        kept.append(row)
    return kept, excluded


def _metric_result(values_x: list[float], values_y: list[float]) -> dict[str, Any]:
    rho = spearman_rho(values_x, values_y)
    return {
        "n": len(values_x),
        "rho": rho,
        "notable": bool(rho is not None and abs(rho) >= NOTABLE_ABS_RHO),
        "interpretation": "DESCRIPTIVE ONLY; notable is an effect-size flag, not a verdict",
    }


def summarize(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize already-built rows without loading or mutating any state."""
    kept, excluded = filter_causal_board_rows(rows)
    rv_x: list[float] = []
    rv_y: list[float] = []
    iv_x: list[float] = []
    iv_y: list[float] = []
    by_day: dict[str, list[dict[str, Any]]] = {}
    for row in kept:
        by_day.setdefault(row["date"], []).append(row)
        if row.get("forward_rv") is not None:
            try:
                value = float(row["forward_rv"])
                if math.isfinite(value):
                    rv_x.append(float(row["green_fraction"]))
                    rv_y.append(value)
            except (TypeError, ValueError):
                pass
        if row.get("forward_iv_change") is not None:
            try:
                value = float(row["forward_iv_change"])
                if math.isfinite(value):
                    iv_x.append(float(row["green_fraction"]))
                    iv_y.append(value)
            except (TypeError, ValueError):
                pass

    cross_sectional: dict[str, Any] = {}
    for field, outcome in (("forward_rv", "rv"), ("forward_iv_change", "iv_change")):
        daily: list[float] = []
        for day_rows in by_day.values():
            pairs = []
            for row in day_rows:
                value = row.get(field)
                if value is None:
                    continue
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    pairs.append((float(row["green_fraction"]), number))
            if len(pairs) >= 2:
                rho = spearman_rho([pair[0] for pair in pairs], [pair[1] for pair in pairs])
                if rho is not None:
                    daily.append(rho)
        cross_sectional[outcome] = {
            "n_days": len(daily),
            "median_rho": float(np.median(daily)) if daily else None,
            "notable_days": sum(abs(value) >= NOTABLE_ABS_RHO for value in daily),
        }

    return {
        "observation_count": len(kept),
        "symbols": sorted({str(row["symbol"]) for row in kept}),
        "date_start": min((row["date"] for row in kept), default=None),
        "date_end": max((row["date"] for row in kept), default=None),
        "pooled": {
            "forward_realized_vol": _metric_result(rv_x, rv_y),
            "forward_iv_change": _metric_result(iv_x, iv_y),
        },
        "cross_sectional": cross_sectional,
        "excluded": excluded,
        "descriptive_only": True,
        "verdict": "NO VERDICT — descriptive rank-quality measurement only",
    }


def _atomic_create(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise OneRunError(f"RQ1 one-run artifact already exists: {path}") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _report_context_hash() -> str:
    from research.hashing import sha256_file

    return sha256_file(Path("docs/superpowers/plans/2026-07-23-codex-execution-queue.md"))


def _preregistration_hash() -> str:
    from research.ledger import read_all

    for record in read_all("ledger"):
        if record.get("seq") == REGISTRATION_SEQ:
            return str(record["record_hash"])
    raise RQ1Error(f"RQ1 registration seq {REGISTRATION_SEQ} is missing")


def _append_ledger_result(report: Mapping[str, Any], report_path: Path) -> str:
    from research import hashing, ledger

    if any(
        record.get("entry_type") == "retrospective_result" and record.get("hypothesis_id") == "RQ1"
        for record in ledger.read_all("ledger")
    ):
        raise OneRunError("RQ1 already has a retrospective result in the ledger")
    body = {
        "entry_type": "retrospective_result",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "subject": "RQ1 frozen pre-badge GREEN-fraction rank-quality study",
        "hypothesis_id": "RQ1",
        "report_sha256": hashing.sha256_file(report_path),
        "context_sha256": _report_context_hash(),
        "prereg_ref_sha256": _preregistration_hash(),
        "source_commit": _git_head(),
        "labels": [
            "outcome-selected",
            "self-deceiving",
            "descriptive-only",
            "no-verdict",
            "cannot-promote",
        ],
        "result": dict(report["results"]),
    }
    return ledger.append(body, base_dir="ledger")


def run_once(
    *,
    load_rows: Callable[[], Sequence[Mapping[str, Any]]],
    report_path: Path = DEFAULT_REPORT_PATH,
    append_result: bool = False,
) -> dict[str, Any]:
    """Build the single RQ1 report and optionally append its ledger result."""
    if report_path.exists():
        if not append_result:
            raise OneRunError(f"RQ1 one-run artifact already exists: {report_path}")
        # A report is intentionally created before ledger publication. If the
        # append failed after the report was written, retry that verified
        # artifact instead of rebuilding or overwriting it.
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OneRunError(
                f"existing RQ1 artifact is unreadable: {report_path}"
            ) from exc
        if (
            not isinstance(report, dict)
            or report.get("schema") != "rq1_rank_quality_v1"
            or report.get("hypothesis_id") != "RQ1"
            or report.get("registration_seq") != REGISTRATION_SEQ
            or not isinstance(report.get("results"), dict)
            or not isinstance(report.get("provenance"), dict)
        ):
            raise OneRunError(
                f"existing RQ1 artifact failed provenance validation: {report_path}"
            )
        _append_ledger_result(report, report_path)
        return report
    rows = list(load_rows())
    results = summarize(rows)
    report: dict[str, Any] = {
        "schema": "rq1_rank_quality_v1",
        "hypothesis_id": "RQ1",
        "registration_seq": REGISTRATION_SEQ,
        "horizon_sessions": HORIZON_SESSIONS,
        "notable_abs_rho": NOTABLE_ABS_RHO,
        "recipe": (
            "Frozen pre-badge card builders only; per-name score is the best "
            "available card GREEN fraction for that date. Each card's UNKNOWN "
            "grades remain in its denominator. Inputs are same-day or older."
        ),
        "results": results,
    }
    from research.hashing import sha256_file

    report["provenance"] = {
        "source_commit": _git_head(),
        "runner_sha256": sha256_file(Path(__file__)),
        "adversarial_review": (
            "docs/superpowers/reviews/2026-07-23-rq1-runner-adversarial-review.md"
        ),
    }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    _atomic_create(report_path, encoded + b"\n")
    if append_result:
        _append_ledger_result(report, report_path)
    return report


def _date_index(values: Iterable[object]) -> pd.Index:
    return pd.Index([str(value)[:10] for value in values], name="date")


def exact_forward_iv(
    features: pd.DataFrame,
    sessions: Iterable[object],
    *,
    horizon: int = HORIZON_SESSIONS,
) -> pd.Series:
    """Return IV change at the exact trading-session horizon.

    Chain observations can be sparse. Align them to the underlying's
    trading-session calendar before shifting so a missing session remains
    missing instead of becoming the next available chain row.
    """
    if horizon < 1:
        raise ValueError("horizon must be positive")
    if "atm_iv" not in features:
        raise KeyError("features missing atm_iv")
    feature_index = _date_index(features.index)
    if feature_index.has_duplicates:
        raise ValueError("features contain duplicate dates")
    session_index = _date_index(sessions)
    if session_index.has_duplicates:
        raise ValueError("sessions contain duplicate dates")
    iv = pd.Series(features["atm_iv"].to_numpy(), index=feature_index)
    aligned = iv.reindex(session_index)
    return aligned.shift(-horizon) - aligned


def _point_in_time_earnings(
    assertions: list[dict] | None, symbol: str, day: date
) -> list[date]:
    """Return earnings known by the board-day close, including future dates."""
    if assertions is None:
        raise RQ1Error("point-in-time earnings assertions are unavailable")
    from options_researcher.h7_earnings import (
        GATING_EVENT_CLASS,
        assertions_view,
        report_date,
    )

    cutoff = datetime.combine(day, time.max, tzinfo=timezone.utc)
    return sorted(
        report_date(row)
        for row in assertions_view(assertions, cutoff)
        if row["symbol"] == symbol.upper()
        and row.get("event_class") == GATING_EVENT_CLASS
        and report_date(row) is not None
    )


def _point_in_time_fomc(events: Sequence[object], day: date) -> list[date]:
    """Return FOMC dates only when each row carries announcement provenance."""
    cutoff = datetime.combine(day, time.max, tzinfo=timezone.utc)
    dates: list[date] = []
    for event in events:
        if not isinstance(event, Mapping):
            raise RQ1Error(
                "FOMC calendar lacks known_as_of_utc provenance; refusing "
                "historical board reconstruction"
            )
        raw_date = event.get("date")
        known_as_of = event.get("known_as_of_utc")
        if not isinstance(raw_date, date) or not isinstance(known_as_of, datetime):
            raise RQ1Error("FOMC event provenance is malformed")
        if known_as_of.tzinfo is None or known_as_of.utcoffset() is None:
            raise RQ1Error("FOMC event known_as_of_utc must be timezone-aware")
        if known_as_of <= cutoff and raw_date >= day:
            dates.append(raw_date)
    return sorted(dates)


def _finite_number(value: object) -> float | None:
    if not isinstance(value, (str, int, float)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _spent_report_symbols(
    report_path: Path = DEFAULT_REPORT_PATH,
) -> tuple[str, ...]:
    """Read the immutable symbol scope recorded by the spent RQ1 report."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RQ1Error(f"spent RQ1 report is unreadable: {report_path}") from exc
    if (
        not isinstance(report, dict)
        or report.get("schema") != "rq1_rank_quality_v1"
        or report.get("hypothesis_id") != "RQ1"
        or report.get("registration_seq") != REGISTRATION_SEQ
        or not isinstance(report.get("results"), dict)
    ):
        raise RQ1Error(
            f"spent RQ1 report failed scope provenance validation: {report_path}"
        )
    symbols = report["results"].get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise RQ1Error(f"spent RQ1 report has no recorded symbols: {report_path}")
    names: list[str] = []
    for symbol in symbols:
        if not isinstance(symbol, str) or not symbol or symbol != symbol.upper():
            raise RQ1Error(
                f"spent RQ1 report has an invalid recorded symbol: {symbol!r}"
            )
        names.append(symbol)
    if len(names) != len(set(names)):
        raise RQ1Error(f"spent RQ1 report has duplicate symbols: {report_path}")
    return tuple(names)


def _default_rows(
    *, report_path: Path = DEFAULT_REPORT_PATH
) -> list[dict[str, Any]]:
    """Reconstruct only the spent report's board scope from cached chains."""
    import glob

    from data.underlying_closes import load_closes, load_closes_adjusted
    from options_researcher.attractiveness import (
        ladder_cards,
        leaps_card_rows,
        long_call_card_rows,
        put_card_rows,
    )
    from options_researcher.features import load_features
    from options_researcher.fomc import load_fomc
    from options_researcher.h7_earnings import load_assertions

    rows: list[dict[str, Any]] = []
    skipped_days: Counter[str] = Counter()
    for symbol in _spent_report_symbols(report_path):
        files = {
            Path(path).stem.rsplit("_", 1)[-1]: Path(path)
            for path in glob.glob(f".cache/chains/{symbol}_*.parquet")
        }
        if not files:
            continue
        features = load_features(symbol).sort_index()
        raw_closes = load_closes(
            symbol, config.RQ1_CACHE_START, config.BACKTEST_END, allow_oos=True
        )
        adjusted_closes = load_closes_adjusted(
            symbol, config.RQ1_CACHE_START, config.BACKTEST_END, allow_oos=True
        )
        forward_rv = forward_realized_vol(adjusted_closes)
        future_iv = exact_forward_iv(features, raw_closes.index)
        try:
            assertions_all = load_assertions()
        except (FileNotFoundError, ValueError) as exc:
            raise RQ1Error(
                f"point-in-time earnings assertions unavailable: {exc}"
            ) from exc
        try:
            fomc_all = load_fomc()
        except (FileNotFoundError, ValueError):
            fomc_all = []
        if any(not isinstance(event, Mapping) for event in fomc_all):
            raise RQ1Error(
                "FOMC calendar lacks known_as_of_utc provenance; refusing "
                "historical board reconstruction"
            )
        for day_iso in sorted(files):
            if day_iso < config.STUDY_ERA_START.get(symbol, config.BACKTEST_START):
                continue
            if day_iso > config.BACKTEST_END:
                continue
            at_or_before = features.loc[features.index.astype(str) <= day_iso]
            if at_or_before.empty:
                continue
            feature_as_of = str(at_or_before.index[-1])[:10]
            if feature_as_of > day_iso:
                continue
            try:
                feature = at_or_before.iloc[-1]
                close = float(raw_closes.loc[day_iso])
                chain = pd.read_parquet(files[day_iso])
                day = date.fromisoformat(day_iso)
                earnings = _point_in_time_earnings(assertions_all, symbol, day)
                fomc = _point_in_time_fomc(fomc_all, day)
                iv_rank = (
                    float(feature["iv_rank"])
                    if pd.notna(feature["iv_rank"])
                    else 0.0
                )
                iv_minus_rv = (
                    float(feature["iv_minus_rv"])
                    if pd.notna(feature["iv_minus_rv"])
                    else 0.0
                )
                cards: list[dict[str, Any]] = []
                cards.extend(
                    ladder_cards(
                        put_card_rows,
                        symbol,
                        chain,
                        day_iso,
                        rank_key="annualized_yield",
                        higher_is_better=True,
                        close=close,
                        rv21=float(feature["rv21"]),
                        iv_rank=iv_rank,
                        iv_minus_rv=iv_minus_rv,
                        earnings_dates=earnings,
                        fomc_dates=fomc,
                    )
                )
                cards.extend(
                    ladder_cards(
                        long_call_card_rows,
                        symbol,
                        chain,
                        day_iso,
                        rank_key="breakeven_move",
                        higher_is_better=False,
                        close=close,
                        iv_rank=iv_rank,
                    )
                )
                if symbol in config.H4_THESIS_NAMES:
                    cards.extend(
                        leaps_card_rows(
                            symbol,
                            chain,
                            day_iso,
                            close=close,
                            iv_rank=iv_rank,
                            bucket_room=config.H4_THESIS_MAX_PREMIUM_TOTAL,
                        )
                    )
                scored = [
                    (green_fraction(card.get("grades", {})), card)
                    for card in cards
                    if "skipped" not in card
                ]
                scored = [(score, card) for score, card in scored if score is not None]
                if not scored:
                    continue
                best_score, best_card = max(
                    scored, key=lambda item: (item[0], str(item[1].get("expiry", "")))
                )
                rv = _finite_number(forward_rv.get(day_iso))
                iv_delta = _finite_number(future_iv.get(day_iso))
                rows.append(
                    {
                        "symbol": symbol,
                        "date": day_iso,
                        "lane": "best_prebadge_card",
                        "green_fraction": float(best_score),
                        "features_as_of": feature_as_of,
                        "forward_rv": rv,
                        "forward_iv_change": iv_delta,
                        "synthetic": False,
                        "lookahead_contaminated": False,
                        "card_expiry": str(best_card.get("expiry", "")),
                    }
                )
            except (
                FileNotFoundError,
                KeyError,
                TypeError,
                ValueError,
                IndexError,
                RQ1Error,
            ) as exc:
                # A missing/malformed day is a counted, logged gap, not a
                # fabricated zero score. The aggregate uses only usable rows.
                skipped_days[type(exc).__name__] += 1
                logger.warning(
                    "RQ1 reconstruction skipped %s %s (%s): %s",
                    symbol,
                    day_iso,
                    type(exc).__name__,
                    exc,
                )
                continue
    if skipped_days:
        logger.warning(
            "RQ1 reconstruction skipped %d board day(s): %s",
            sum(skipped_days.values()),
            dict(sorted(skipped_days.items())),
        )
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="run once and append the descriptive retrospective result",
    )
    args = parser.parse_args(argv)
    report = run_once(
        load_rows=_default_rows,
        report_path=args.report,
        append_result=args.execute,
    )
    print(json.dumps(report["results"], sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

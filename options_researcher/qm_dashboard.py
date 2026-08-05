"""Exact-session QM context for the six-card attractiveness dashboard.

This module does not run or rewrite the frozen QM study.  It verifies a
machine-readable sidecar against the committed report hash, evaluates only
the current signal/MA state from cached OHLCV, and fails closed if any name is
not aligned to the dashboard's market date. The optional refresh CLI writes
only covered names' existing blind Yahoo OHLCV cache; it has no book or order
path.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from options_researcher import qm_signals

DEFAULT_SIDECAR = Path("reports/qm_context/2026-07-14.json")
_OHLCV_START = "2017-01-01"


class QmContextError(ValueError):
    """The frozen study provenance cannot be trusted or interpreted."""


def load_study_sidecar(path: str | Path = DEFAULT_SIDECAR) -> dict[str, Any]:
    """Load a study sidecar only when its source report hash still matches."""
    sidecar_path = Path(path)
    try:
        payload = json.loads(sidecar_path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QmContextError(
            f"QM sidecar unreadable: {sidecar_path} ({exc.__class__.__name__})"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise QmContextError("QM sidecar schema is not supported")
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise QmContextError("QM sidecar source block is missing")
    report_value = source.get("report_path")
    expected = source.get("report_sha256")
    if not isinstance(report_value, str) or not isinstance(expected, str):
        raise QmContextError("QM sidecar source path/hash is missing")
    report_path = Path(report_value)
    try:
        actual = hashlib.sha256(report_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise QmContextError(f"QM source report unreadable: {report_path}") from exc
    if actual != expected:
        raise QmContextError(
            f"QM source hash mismatch for {report_path}: expected {expected}, got {actual}"
        )
    ledger_value = source.get("ledger_path")
    ledger_prefix = source.get("ledger_fact_prefix")
    ledger_expected = source.get("ledger_fact_sha256")
    if not all(isinstance(value, str) for value in (ledger_value, ledger_prefix, ledger_expected)):
        raise QmContextError("QM sidecar ledger source path/fact/hash is missing")
    assert isinstance(ledger_value, str)
    assert isinstance(ledger_prefix, str)
    assert isinstance(ledger_expected, str)
    ledger_path = Path(ledger_value)
    try:
        ledger_lines = ledger_path.read_text().splitlines()
    except OSError as exc:
        raise QmContextError(f"QM source ledger unreadable: {ledger_path}") from exc
    matching_facts = [
        line for line in ledger_lines if line.split("\t", 1)[-1].startswith(ledger_prefix)
    ]
    if len(matching_facts) != 1:
        raise QmContextError(f"QM source ledger fact {ledger_prefix!r} is missing or ambiguous")
    ledger_actual = hashlib.sha256(matching_facts[0].encode()).hexdigest()
    if ledger_actual != ledger_expected:
        raise QmContextError(
            f"QM ledger fact hash mismatch for {ledger_path}: "
            f"expected {ledger_expected}, got {ledger_actual}"
        )
    if not isinstance(payload.get("symbols"), Mapping):
        raise QmContextError("QM sidecar symbols block is missing")
    return payload


def _default_load_adjusted(symbol: str, as_of: str) -> pd.DataFrame:
    from data.underlying_ohlcv import load_ohlcv_adjusted

    return load_ohlcv_adjusted(symbol, _OHLCV_START, as_of, allow_oos=True)


def _last_iso(frame: pd.DataFrame) -> str | None:
    return str(frame.index[-1])[:10] if frame is not None and not frame.empty else None


def _blocked(
    as_of: str,
    reason: str,
    *,
    symbols: dict[str, Any] | None = None,
    study: Mapping[str, Any] | None = None,
    quant_want: Mapping[str, Any] | None = None,
    unexpected_symbols: Sequence[str] = (),
) -> dict[str, Any]:
    blocked = {
        "as_of": as_of,
        "status": "DATA_BLOCKED",
        "reason": reason,
        "symbols": symbols or {},
        "study": dict(study or {}),
        "quant_want": dict(quant_want or {}),
    }
    if unexpected_symbols:
        blocked["unexpected"] = True
        blocked["unexpected_symbols"] = list(unexpected_symbols)
    return blocked


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _frozen_symbol_or_block(
    symbol: str, study: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    """Return a usable symbol study entry, never aggregate evidence for an uncovered name."""
    sidecar_symbols = study.get("symbols")
    frozen = sidecar_symbols.get(symbol) if isinstance(sidecar_symbols, Mapping) else None
    if not isinstance(frozen, Mapping):
        return None
    if frozen.get("evidence_status") == "NOT_IN_FROZEN_STUDY":
        return None
    return frozen


def _not_in_frozen_study(symbol: str) -> dict[str, str]:
    return {
        "status": "NOT_IN_FROZEN_STUDY",
        "reason": f"{symbol} is not in the frozen QM study sidecar",
    }


def _symbol_context(
    symbol: str,
    frame: pd.DataFrame,
    as_of: str,
    params: Mapping[str, Any],
    study: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = _frozen_symbol_or_block(symbol, study)
    if frozen is None:
        return _not_in_frozen_study(symbol)

    last = _last_iso(frame)
    if last is None:
        return {"status": "NO_DATA", "reason": "no cached adjusted OHLCV"}
    if last != as_of:
        relation = "after" if last > as_of else "before"
        return {
            "status": "STALE",
            "reason": f"OHLCV ends {last}, {relation} required session {as_of}",
        }
    if len(frame) < 200:
        return {
            "status": "NO_DATA",
            "reason": f"only {len(frame)} OHLCV rows; need 200 for SMA200",
        }

    closes = frame["close"].astype(float)
    price = float(closes.iloc[-1])
    smas = {window: float(closes.tail(window).sum()) / window for window in (20, 50, 200)}
    if not all(_finite(value) for value in (price, *smas.values())):
        return {"status": "NO_DATA", "reason": "non-finite price or moving average"}

    breakout_fires = qm_signals.breakout_fires(frame, params)
    parabolic_fires = qm_signals.parabolic_fires(frame, params)
    breakout = bool(breakout_fires) and breakout_fires[-1].get("t") == as_of
    parabolic = bool(parabolic_fires) and parabolic_fires[-1] == as_of
    if breakout and parabolic:
        signal_status = "BREAKOUT + PARABOLIC WARNING"
    elif breakout:
        signal_status = "BREAKOUT"
    elif parabolic:
        signal_status = "PARABOLIC WARNING"
    else:
        signal_status = "NO FIRE"

    breakout_dates = frozen.get("breakout_fire_dates", [])
    if not isinstance(breakout_dates, list):
        breakout_dates = []
    parabolic_dates = frozen.get("parabolic_fire_dates", [])
    if not isinstance(parabolic_dates, list):
        parabolic_dates = []
    study_block = study.get("study")
    study_block = study_block if isinstance(study_block, Mapping) else {}
    breakout_study = study_block.get("breakout")
    breakout_study = breakout_study if isinstance(breakout_study, Mapping) else {}
    symbol_study = dict(breakout_study)
    if isinstance(frozen, Mapping) and frozen.get("evidence_status"):
        symbol_study["evidence_status"] = frozen["evidence_status"]

    return {
        "status": "CURRENT",
        "signal_status": signal_status,
        "breakout_fire": breakout,
        "parabolic_fire": parabolic,
        "price": price,
        "sma20": smas[20],
        "sma50": smas[50],
        "sma200": smas[200],
        "price_vs_sma20": price / smas[20] - 1.0,
        "price_vs_sma50": price / smas[50] - 1.0,
        "price_vs_sma200": price / smas[200] - 1.0,
        "ma_supports_bullish": (price > smas[20] and price > smas[50] and price > smas[200]),
        "historical_breakout_fires": len(breakout_dates),
        "historical_parabolic_fires": len(parabolic_dates),
        "study": symbol_study,
        "parabolic_study": dict(study_block.get("parabolic", {})),
        "thesis": study.get("thesis", "QM thesis unavailable."),
        "counter_case": study.get("counter_case", "QM counter-case unavailable."),
        "study_date": study_block.get("data_vintage"),
        "provenance": study.get("provenance", "QM provenance unavailable."),
    }


def build_qm_context(
    symbols: Sequence[str],
    as_of: str,
    *,
    study: Mapping[str, Any],
    load_adjusted: Callable[[str, str], pd.DataFrame] = _default_load_adjusted,
    params: Mapping[str, Any] | None = None,
    gate: Callable[[], str | None] = qm_signals.qm_prereg_gate,
) -> dict[str, Any]:
    """Build one exact-session QM context object per ticker."""
    gate_reason = gate()
    if gate_reason:
        return _blocked(
            as_of,
            str(gate_reason),
            study=study.get("study", {}),
            quant_want=study.get("quant_want", {}),
        )
    resolved_params = qm_signals.qm_params() if params is None else params
    per_symbol: dict[str, Any] = {}
    unexpected_symbols: list[str] = []
    for symbol in symbols:
        if _frozen_symbol_or_block(symbol, study) is None:
            per_symbol[symbol] = _not_in_frozen_study(symbol)
            continue
        try:
            frame = load_adjusted(symbol, as_of)
            per_symbol[symbol] = _symbol_context(symbol, frame, as_of, resolved_params, study)
        except OSError as exc:  # expected absent/unreadable cache is visible but not a code failure
            per_symbol[symbol] = {
                "status": "NO_DATA",
                "reason": f"{exc.__class__.__name__}: {exc}",
            }
        except Exception as exc:  # fail-visible and nonzero: never success-shaped over a code fault
            unexpected_symbols.append(symbol)
            per_symbol[symbol] = {
                "status": "UNEXPECTED_ERROR",
                "reason": f"{exc.__class__.__name__}: {exc}",
                "unexpected": True,
            }
    blocked = [symbol for symbol, item in per_symbol.items() if item.get("status") != "CURRENT"]
    if blocked:
        uncovered = [
            symbol for symbol in blocked
            if per_symbol[symbol].get("status") == "NOT_IN_FROZEN_STUDY"
        ]
        stale = [symbol for symbol in blocked if symbol not in uncovered]
        reasons = []
        if uncovered:
            reasons.append("not covered by the frozen QM study: " + ", ".join(uncovered))
        if stale:
            reasons.append("QM context is not exact-session current for: " + ", ".join(stale))
        return _blocked(
            as_of,
            "; ".join(reasons),
            symbols=per_symbol,
            study=study.get("study", {}),
            quant_want=study.get("quant_want", {}),
            unexpected_symbols=unexpected_symbols,
        )
    return {
        "as_of": as_of,
        "status": "CURRENT",
        "symbols": per_symbol,
        "study": dict(study.get("study", {})),
        "source": dict(study.get("source", {})),
        "quant_want": dict(study.get("quant_want", {})),
    }


def load_qm_context(as_of: str, *, sidecar_path: str | Path = DEFAULT_SIDECAR) -> dict[str, Any]:
    """Load verified study facts and combine them with current cached OHLCV."""
    reason = qm_signals.qm_prereg_gate()
    if reason:
        return _blocked(as_of, reason)
    try:
        study = load_study_sidecar(sidecar_path)
    except QmContextError as exc:
        return _blocked(as_of, str(exc))
    from options_researcher.h7_scope import watch_universe

    return build_qm_context(watch_universe(), as_of, study=study, gate=lambda: None)


def underlying_breakeven_frequency(
    _symbol_context: Mapping[str, Any],
    _card: Mapping[str, Any],
    lane: str,
) -> dict[str, Any]:
    """Return only source-bound stock-move evidence for a card.

    The frozen report records aggregate excursion summaries, not the per-fire
    values needed to evaluate a particular card's breakeven.  Never recompute
    those values from the refreshable dashboard OHLCV cache: that would turn a
    frozen study claim into a post-hoc calculation.
    """
    unavailable = {
        "available": False,
        "hits": None,
        "sample": 0,
        "frequency": None,
        "option_win_rate": None,
        "label": (
            "Underlying breakeven-move frequency not shown: the frozen study "
            "records aggregate excursions, not per-fire moves. It was not "
            "recomputed from today's cache."
        ),
        "warning": (
            "Actual option win rate unavailable: the QM study measured "
            "underlying moves and tradability, not historical option P&L. "
            "This is not an option win probability."
        ),
    }
    if lane not in {"long_call", "leaps"}:
        unavailable["label"] = (
            "Underlying breakeven comparison not applicable to this structure; "
            "this option structure was not tested by QM."
        )
        return unavailable
    return unavailable


def refresh_qm_ohlcv(
    symbols: Sequence[str],
    as_of: str,
    *,
    study: Mapping[str, Any] | None = None,
    sidecar_path: str | Path = DEFAULT_SIDECAR,
    load_adjusted: Callable[[str, str], pd.DataFrame] = _default_load_adjusted,
    fetch: Callable[[str], str] | None = None,
    gate: Callable[[], str | None] = qm_signals.qm_prereg_gate,
) -> dict[str, Any]:
    """Top up only frozen-study members, then verify the exact market date.

    A sidecar-uncovered symbol is a coverage failure, not an invitation to
    create a new cache dependency. It is rejected before either load or fetch.
    """
    reason = gate()
    if reason:
        return _blocked(as_of, reason)
    if study is None:
        try:
            study = load_study_sidecar(sidecar_path)
        except QmContextError as exc:
            return _blocked(as_of, str(exc))
    if fetch is None:
        from data.underlying_ohlcv import fetch_underlying_ohlcv_yahoo

        fetch = fetch_underlying_ohlcv_yahoo

    results: dict[str, Any] = {}
    for symbol in symbols:
        if _frozen_symbol_or_block(symbol, study) is None:
            results[symbol] = _not_in_frozen_study(symbol)
            continue
        initial_last: str | None = None
        initial_error: Exception | None = None
        try:
            initial_last = _last_iso(load_adjusted(symbol, as_of))
        except Exception as exc:
            initial_error = exc
        if initial_last == as_of:
            results[symbol] = {"status": "CURRENT", "refreshed": False}
            continue
        try:
            fetch(symbol)
            refreshed_last = _last_iso(load_adjusted(symbol, as_of))
        except Exception as exc:
            prior = (
                f"; initial load {initial_error.__class__.__name__}: {initial_error}"
                if initial_error
                else ""
            )
            results[symbol] = {
                "status": "STALE",
                "refreshed": False,
                "reason": f"refresh failed ({exc.__class__.__name__}: {exc}){prior}",
            }
            continue
        if refreshed_last != as_of:
            results[symbol] = {
                "status": "STALE",
                "refreshed": True,
                "reason": (
                    f"refresh ended {refreshed_last or 'empty'}, need exact session {as_of}"
                ),
            }
        else:
            results[symbol] = {"status": "CURRENT", "refreshed": True}

    blocked = [s for s, item in results.items() if item["status"] != "CURRENT"]
    return {
        "as_of": as_of,
        "status": "DATA_BLOCKED" if blocked else "CURRENT",
        "reason": ("QM OHLCV refresh incomplete for: " + ", ".join(blocked) if blocked else ""),
        "symbols": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Exact-session QM OHLCV refresh for the dashboard")
    parser.add_argument("--as-of", required=True, help="exact completed market session YYYY-MM-DD")
    parser.add_argument(
        "--refresh-ohlcv", action="store_true", help="refresh missing/stale QM OHLCV caches"
    )
    args = parser.parse_args(argv)
    if not args.refresh_ohlcv:
        parser.error("--refresh-ohlcv is required")
    from options_researcher.h7_scope import watch_universe

    result = refresh_qm_ohlcv(watch_universe(), args.as_of)
    print(f"QM OHLCV session={args.as_of} status={result['status']}")
    for symbol, item in result["symbols"].items():
        suffix = f" -- {item['reason']}" if item.get("reason") else ""
        print(f"{symbol}: {item['status']}{suffix}")
    return 0 if result["status"] == "CURRENT" else 1


if __name__ == "__main__":
    raise SystemExit(main())

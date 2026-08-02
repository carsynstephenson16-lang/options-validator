"""options_researcher/entry_watch.py -- pre-registered LEAPS entry-trigger watch.

Prints one WAIT/FIRE/DATA_GAP line per name in config.H5_ENTRY_TRIGGERS. FIRE means
"evaluate a 0.70-delta LEAPS per H5 CORE rules now" -- never "buy". The rule
is pre-registered in ledger/facts.log (H5_ENTRY_TRIGGER_PREREG 2026-07-07).
Read-only: never writes positions, never trades. NaN IV-rank counts as
UNMET (unknown never passes a gate).
"""
from __future__ import annotations

import glob
import math
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity


def trigger_status(symbol: str, *, close: float, iv_rank: float,
                   leaps_row: pd.Series | None,
                   chain_missing: bool = False) -> dict:
    """Grade one name against the frozen entry trigger. `leaps_row` is the
    0.70-delta LEAPS candidate row from the supplied exact-session chain, or None
    when no candidate exists in the DTE band. `chain_missing=True` means no
    cached chain file exists at all (a data gap, not a benign no-candidate)."""
    level = config.H5_ENTRY_TRIGGERS[symbol]
    price_ok = close <= level
    iv_ok = iv_rank <= config.H5_ENTRY_IVR_MAX  # NaN compares False
    liq_ok = bool(leaps_row is not None and passes_liquidity(
        leaps_row["open_interest"], leaps_row["bid"], leaps_row["ask"]))
    unmet = []
    if not price_ok:
        unmet.append(f"close ${close:,.2f} > trigger ${level:,.2f}")
    if not iv_ok:
        unmet.append(f"IV-rank {iv_rank:.2f} > {config.H5_ENTRY_IVR_MAX}")
    if not liq_ok:
        if leaps_row is not None:
            unmet.append("LEAPS fails liquidity gates")
        elif chain_missing:
            unmet.append("no cached chain file (.cache/chains) "
                         "-- run the top-up")
        else:
            unmet.append("no LEAPS candidate in DTE band")
    return {"symbol": symbol, "close": close, "trigger": level,
            "iv_rank": iv_rank, "price_ok": price_ok, "iv_ok": iv_ok,
            "liq_ok": liq_ok, "unmet": unmet,
            "verdict": "WAIT" if unmet else "FIRE"}


_CHAIN_NAME = re.compile(r"^[A-Z0-9.-]+_(\d{4}-\d{2}-\d{2})\.parquet$")


def _resolve_evaluation_session(as_of: date | str | None) -> date:
    """Return one completed XNYS session for every H5 input.

    An explicit ``as_of`` is the source-data session itself (matching H6/H8).
    The no-argument dashboard/CLI path reuses H7's established rule: the last
    completed session strictly before the current New York date.
    """
    from data.cache_runner import session_close_utc, trading_days
    from options_researcher.h7_watch import evaluation_session

    if as_of is None:
        selected = evaluation_session(date.today())
    elif isinstance(as_of, date):
        selected = as_of
    else:
        selected = date.fromisoformat(as_of)
    iso = selected.isoformat()
    if iso not in trading_days(iso, iso):
        raise ValueError(f"evaluation session {iso} is not an XNYS session")
    completed_at = session_close_utc(iso)
    if datetime.now(timezone.utc) < completed_at:
        raise ValueError(f"evaluation session {iso} is incomplete until {completed_at.isoformat()}")
    return selected


def _index_days(index: pd.Index, *, context: str) -> list[str]:
    days: list[str] = []
    for value in index:
        raw = str(value)[:10]
        try:
            days.append(date.fromisoformat(raw).isoformat())
        except ValueError as exc:
            raise ValueError(f"{context} contains a non-ISO date index: {value!r}") from exc
    return days


def _exact_close(symbol: str, evaluation_iso: str) -> tuple[float | None, str | None, str | None]:
    from data.underlying_closes import load_closes

    try:
        closes = load_closes(symbol, "2018-01-01", evaluation_iso, allow_oos=True)
    except FileNotFoundError:
        return None, None, f"close file missing; need {evaluation_iso}"
    days = _index_days(pd.Index(closes.index), context=f"{symbol} closes")
    eligible = [(position, day) for position, day in enumerate(days) if day <= evaluation_iso]
    if not eligible:
        return None, None, f"close session missing; need {evaluation_iso}"
    latest = max(day for _, day in eligible)
    hits = [position for position, day in eligible if day == evaluation_iso]
    if len(hits) != 1:
        return None, latest, f"close requires exactly one row for {evaluation_iso}"
    close = float(closes.iloc[hits[0]])
    if not math.isfinite(close):
        return None, latest, f"close is non-finite for {evaluation_iso}"
    return close, latest, None


def _exact_iv_rank(symbol: str, evaluation_iso: str) -> tuple[float | None, str | None, str | None]:
    from options_researcher.features import load_features

    try:
        features = load_features(symbol)
    except FileNotFoundError:
        return None, None, f"feature file missing; need {evaluation_iso}"
    if "iv_rank" not in features.columns:
        raise ValueError(f"{symbol} feature store missing iv_rank")
    days = _index_days(pd.Index(features.index), context=f"{symbol} features")
    eligible = [(position, day) for position, day in enumerate(days) if day <= evaluation_iso]
    if not eligible:
        return None, None, f"feature session missing; need {evaluation_iso}"
    latest = max(day for _, day in eligible)
    hits = [position for position, day in eligible if day == evaluation_iso]
    if len(hits) != 1:
        return None, latest, f"feature requires exactly one row for {evaluation_iso}"
    value = features.iloc[hits[0]]["iv_rank"]
    return (float(value) if pd.notna(value) else float("nan")), latest, None


def _chain_edge(symbol: str, evaluation_iso: str) -> str | None:
    pattern = os.path.join(".cache", "chains", f"{symbol}_*.parquet")
    days: list[str] = []
    for raw_path in glob.glob(pattern):
        match = _CHAIN_NAME.match(os.path.basename(raw_path))
        if match and match.group(1) <= evaluation_iso:
            days.append(match.group(1))
    return max(days, default=None)


def _data_gap_row(
    symbol: str,
    evaluation_iso: str,
    *,
    close: float | None,
    iv_rank: float | None,
    close_asof: str | None,
    iv_asof: str | None,
    chain_asof: str | None,
    gaps: list[str],
) -> dict:
    return {
        "symbol": symbol,
        "close": close,
        "trigger": config.H5_ENTRY_TRIGGERS[symbol],
        "iv_rank": iv_rank,
        "price_ok": False,
        "iv_ok": False,
        "liq_ok": False,
        "unmet": list(gaps),
        "data_gaps": list(gaps),
        "verdict": "DATA_GAP",
        "evaluation_session": evaluation_iso,
        "close_asof": close_asof,
        "chain_asof": chain_asof,
        "iv_asof": iv_asof,
    }


def _gather(as_of: date | str | None = None) -> list[dict]:
    """Read exact-session H5 inputs from local stores only.

    A stale or future close, feature row, or chain may be shown as descriptive
    cache-edge context, but it can never reach ``trigger_status`` or produce
    ``FIRE``. Missing exact inputs produce an explicit per-name ``DATA_GAP``.
    """
    from options_researcher.studies.long_call_carry import _leaps_candidate

    evaluation = _resolve_evaluation_session(as_of)
    evaluation_iso = evaluation.isoformat()
    out: list[dict] = []
    for symbol in config.H5_ENTRY_TRIGGERS:
        close, close_asof, close_gap = _exact_close(symbol, evaluation_iso)
        iv_rank, iv_asof, feature_gap = _exact_iv_rank(symbol, evaluation_iso)
        chain_asof = _chain_edge(symbol, evaluation_iso)
        exact_chain = Path(".cache/chains") / f"{symbol}_{evaluation_iso}.parquet"
        chain_gap = None
        chain = None
        if not exact_chain.is_file():
            chain_gap = f"exact chain missing; need {evaluation_iso}"
        else:
            chain = pd.read_parquet(exact_chain)
            if chain.empty:
                chain_gap = f"exact chain empty for {evaluation_iso}"
        gaps = [gap for gap in (close_gap, feature_gap, chain_gap) if gap is not None]
        if gaps:
            out.append(
                _data_gap_row(
                    symbol,
                    evaluation_iso,
                    close=close,
                    iv_rank=iv_rank,
                    close_asof=close_asof,
                    iv_asof=iv_asof,
                    chain_asof=chain_asof,
                    gaps=gaps,
                )
            )
            continue
        if close is None or iv_rank is None or chain is None:
            raise RuntimeError("exact-session H5 inputs passed validation without values")
        leaps_row = _leaps_candidate(chain, evaluation, config.H4_THESIS_DELTA)
        row = trigger_status(symbol, close=close, iv_rank=iv_rank, leaps_row=leaps_row)
        row["evaluation_session"] = evaluation_iso
        row["close_asof"] = close_asof
        row["chain_asof"] = chain_asof
        row["iv_asof"] = iv_asof
        row["data_gaps"] = []
        out.append(row)
    return out


def _enforce_exact_row(row: dict, expected_session: str | None = None) -> dict:
    checked = dict(row)
    session = expected_session or checked.get("evaluation_session") or checked.get("close_asof")
    gaps = list(checked.get("data_gaps") or [])
    checked["evaluation_session"] = session
    if not isinstance(session, str):
        gaps.append("evaluation session is missing")
    else:
        for label, field in (
            ("close", "close_asof"),
            ("feature", "iv_asof"),
            ("chain", "chain_asof"),
        ):
            if checked.get(field) != session:
                gaps.append(
                    f"{label} as-of {checked.get(field) or 'MISSING'} does not match {session}"
                )
    if gaps:
        unique_gaps = list(dict.fromkeys(gaps))
        checked["data_gaps"] = unique_gaps
        checked["unmet"] = unique_gaps
        checked["verdict"] = "DATA_GAP"
        checked["price_ok"] = False
        checked["iv_ok"] = False
        checked["liq_ok"] = False
    return checked


def main(
    rows: list[dict] | None = None,
    *,
    as_of: date | str | None = None,
    out: str | Path | None = None,
) -> int:
    """Print the WAIT/FIRE/DATA_GAP report and return 1 on any data gap.

    If `out` is given, ALSO write the exact
    same text directly to that path from Python (data/atomic_io.atomic_text_write)
    rather than relying on a shell capturing this function's stdout.

    Banner-pollution guard (same class as the 2026-07-23/24 H8/intraday_capture
    fixes): `uv run python -m options_researcher.entry_watch` prints LumiBot
    v4.5.63's import-time INFO banner line to stdout before this function's
    own output. A shell `| tee file` capture of that combined stream mixes the
    banner into a receipt meant to hold only the report -- and in zsh (no
    `setopt PIPE_FAIL`), `if cmd | tee file; then` even checks tee's exit
    status, not cmd's. Writing the file from here sidesteps both problems.
    """
    expected = _resolve_evaluation_session(as_of).isoformat() if as_of is not None else None
    if rows is None:
        rows = _gather(expected)
    checked_rows = [_enforce_exact_row(row, expected) for row in rows]
    sessions = {row.get("evaluation_session") for row in checked_rows}
    session_label = next(iter(sessions)) if len(sessions) == 1 else "MIXED"
    lines = [
        "H5 LEAPS ENTRY TRIGGER WATCH "
        f"evaluation_session={session_label} (pre-registered "
        "H5_ENTRY_TRIGGER_PREREG; this tool alerts, it never auto-enters)"
    ]
    for r in checked_rows:
        if r["verdict"] == "DATA_GAP":
            line = (
                f"{r['symbol']}: DATA_GAP (needs exact session "
                f"{r.get('evaluation_session') or 'UNKNOWN'})"
            )
            available = []
            if r.get("close_asof"):
                available.append(f"close as of {r['close_asof']}")
            if r.get("iv_asof"):
                available.append(f"IV-rank as of {r['iv_asof']}")
            if r.get("chain_asof"):
                available.append(f"chain as of {r['chain_asof']}")
            if available:
                line += " -- available: " + "; ".join(available)
            line += " -- refusing trigger: " + "; ".join(r["data_gaps"])
            lines.append(line)
            continue
        line = (
            f"{r['symbol']}: {r['verdict']}  close ${r['close']:,.2f} "
            f"(as of {r['close_asof']}) vs trigger ${r['trigger']:,.2f}; "
            f"IV-rank {r['iv_rank']:.2f} (feature as of {r['iv_asof']}; max "
            f"{config.H5_ENTRY_IVR_MAX}); chain as of {r['chain_asof']}"
        )
        if r["unmet"]:
            line += " -- waiting on: " + "; ".join(r["unmet"])
        else:
            line += (
                " -- ALL conditions met: evaluate the 0.70-delta LEAPS "
                "per H5 CORE rules with FRESH data before any entry "
                "(re-subscribe/audit first if the chain cache is old)"
            )
        lines.append(line)
    for line in lines:
        print(line)
    if out is not None:
        from data.atomic_io import atomic_text_write

        atomic_text_write("\n".join(lines) + "\n", Path(out))
    return 1 if any(row["verdict"] == "DATA_GAP" for row in checked_rows) else 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="H5 LEAPS entry-trigger watch (pre-registered; alert-only, never auto-enters)"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="also write the exact report text to this path "
        "directly from Python, so a shell caller never "
        "needs to capture/tee this process's stdout",
    )
    parser.add_argument(
        "--as-of",
        type=date.fromisoformat,
        default=None,
        help="completed evaluation session (YYYY-MM-DD); defaults to the last "
        "completed session before today",
    )
    args = parser.parse_args()
    raise SystemExit(main(as_of=args.as_of, out=args.out))

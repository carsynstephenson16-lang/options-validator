"""H5's verified-Schwab observer; its historic entry trigger is retired.

The real CLI and gather path report only descriptive, non-verdict-bearing
observations. ``trigger_status`` is retained only as a frozen-history helper.
"""
from __future__ import annotations

import glob
import math
import os
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data.thetadata_adapter import passes_liquidity
from tools.schwab_chain_manifest import SchwabChainManifestError


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
    """Return the completed session before the requested observer run date."""
    from options_researcher.h7_watch import evaluation_session

    if as_of is None:
        run_date = datetime.now(ZoneInfo("America/New_York")).date()
    elif isinstance(as_of, date):
        run_date = as_of
    else:
        run_date = date.fromisoformat(as_of)
    today = datetime.now(ZoneInfo("America/New_York")).date()
    if run_date > today:
        raise ValueError(f"--as-of {run_date} is in the future; refusing")
    return evaluation_session(run_date)


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


OBSERVATION_LABEL = "observational / non-verdict-bearing"


def _h5_symbols() -> tuple[str, ...]:
    return tuple(config.H5_ENTRY_TRIGGERS)


def _load_exact_verified_schwab_chain(symbol: str, evaluation_iso: str
                                      ) -> tuple[pd.DataFrame | None, str | None]:
    """Load only the exact verified package; no stale or ThetaData fallback."""
    from options_researcher import schwab_chain_view

    sessions, failures = schwab_chain_view.verified_sessions()
    if evaluation_iso not in sessions:
        failure = next((item for item in failures
                        if item.get("session") == evaluation_iso), None)
        if failure is not None:
            return None, (f"exact verified Schwab capture is unverified for "
                          f"{evaluation_iso}: {failure['reason']}")
        return None, f"exact verified Schwab capture missing for {evaluation_iso}"
    symbols = set(schwab_chain_view.session_symbols(evaluation_iso))
    missing = sorted(set(_h5_symbols()) - symbols)
    if missing:
        return None, (f"exact verified Schwab capture has partial H5 universe "
                      f"for {evaluation_iso}: missing {missing}")
    try:
        frame = schwab_chain_view.load_chain(symbol, evaluation_iso)
    except (SchwabChainManifestError, OSError, ValueError) as exc:
        return None, (f"exact verified Schwab capture is malformed for "
                      f"{evaluation_iso}: {exc}")
    if frame.empty:
        return None, f"exact verified Schwab capture is empty for {evaluation_iso}"
    return frame, None


def _atm_schwab_iv(chain: pd.DataFrame, evaluation: date) -> float | None:
    """One finite ATM put IV using features.py's shared chain helpers."""
    from options_researcher.chains import atm_row, nearest_monthly

    try:
        expiration = nearest_monthly(chain, evaluation)
        row = atm_row(chain, expiration) if expiration is not None else None
        value = float(row["iv"]) if row is not None else float("nan")
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _finite_schwab_observation_count(symbol: str, evaluation: date) -> int:
    """Count one finite ATM IV per verified full-H5 session."""
    from options_researcher import schwab_chain_view

    count = 0
    required = set(_h5_symbols())
    for session in schwab_chain_view.verified_sessions()[0]:
        if session > evaluation.isoformat():
            continue
        if not required.issubset(schwab_chain_view.session_symbols(session)):
            continue
        try:
            chain = schwab_chain_view.load_chain(symbol, session)
        except (SchwabChainManifestError, OSError, ValueError):
            continue
        if _atm_schwab_iv(chain, date.fromisoformat(session)) is not None:
            count += 1
    return count


def _max_asof_session(*sessions: str | None) -> str | None:
    """Return the latest source session recorded for one observer row."""
    return max((session for session in sessions if session is not None), default=None)


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
    """Read exact verified Schwab observer inputs without a trigger verdict."""
    from options_researcher.features import PCT_MIN_OBS

    evaluation = _resolve_evaluation_session(as_of)
    evaluation_iso = evaluation.isoformat()
    if evaluation_iso < config.H5_RESUME_FLOOR_SESSION:
        raise ValueError(f"evaluation_session={evaluation_iso} is before resume floor "
                         f"{config.H5_RESUME_FLOOR_SESSION}")
    out: list[dict] = []
    for symbol in _h5_symbols():
        close, close_asof, close_gap = _exact_close(symbol, evaluation_iso)
        chain, capture_gap = _load_exact_verified_schwab_chain(symbol, evaluation_iso)
        gaps = [gap for gap in (close_gap, capture_gap) if gap is not None]
        if gaps:
            out.append({"symbol": symbol, "state": "DATA_GAP", "verdict": "DATA_GAP",
                        "close": close, "close_asof": close_asof,
                        "capture_available": chain is not None,
                        "capture_session": evaluation_iso if chain is not None else None,
                        "atm_schwab_iv": None, "finite_schwab_iv_observations": 0,
                        "iv_observations_required": PCT_MIN_OBS,
                        "evaluation_session": evaluation_iso,
                        "max_asof_session": _max_asof_session(
                            close_asof,
                            evaluation_iso if chain is not None else None,
                        ),
                        "reason": "; ".join(gaps)})
            continue
        if close is None or chain is None:
            raise RuntimeError("validated H5 observer input is missing")
        out.append({"symbol": symbol, "state": "OBSERVED", "verdict": "OBSERVE",
                    "close": close, "close_asof": close_asof,
                    "capture_available": True, "capture_session": evaluation_iso,
                    "atm_schwab_iv": _atm_schwab_iv(chain, evaluation),
                    "finite_schwab_iv_observations": _finite_schwab_observation_count(
                        symbol, evaluation),
                    "iv_observations_required": PCT_MIN_OBS,
                    "evaluation_session": evaluation_iso,
                    "max_asof_session": evaluation_iso, "reason": None})
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


def _observer_main(*, as_of: date | str | None, out: str | Path | None,
                   rows: list[dict] | None) -> int:
    if rows is not None:
        raise ValueError("H5 observer refuses injected trigger rows")
    try:
        evaluation = _resolve_evaluation_session(as_of)
    except ValueError as exc:
        lines, rc = [f"H5 SCHWAB OBSERVER REFUSED max_asof_session=NONE "
                     f"{OBSERVATION_LABEL} -- {exc}"], 2
    else:
        evaluation_iso = evaluation.isoformat()
        if evaluation_iso < config.H5_RESUME_FLOOR_SESSION:
            lines = ["H5 SCHWAB OBSERVER REFUSED max_asof_session=NONE "
                     f"{OBSERVATION_LABEL} "
                     f"evaluation_session={evaluation_iso} is before resume floor "
                     f"{config.H5_RESUME_FLOOR_SESSION}; no observation recorded"]
            rc = 2
        else:
            observed = _gather(as_of)
            max_asof = max(
                (row["max_asof_session"] for row in observed
                 if row["max_asof_session"] is not None),
                default="NONE",
            )
            lines = ["H5 SCHWAB OBSERVER "
                     f"evaluation_session={evaluation_iso} "
                     f"max_asof_session={max_asof} {OBSERVATION_LABEL}"]
            for row in observed:
                if row["state"] == "DATA_GAP":
                    lines.append(f"{row['symbol']}: DATA_GAP {OBSERVATION_LABEL} "
                                 f"capture_available={row['capture_available']} "
                                 f"-- refusing observer: {row['reason']}")
                    continue
                iv = row["atm_schwab_iv"]
                iv_label = "unavailable" if iv is None else f"{iv:.5f}"
                lines.append(
                    f"{row['symbol']}: OBSERVED {OBSERVATION_LABEL}; "
                    f"close ${row['close']:,.2f} (as of {row['close_asof']}); "
                    f"capture_available={row['capture_available']}; "
                    f"verified Schwab capture session {row['capture_session']}; "
                    f"ATM Schwab IV {iv_label}; "
                    f"{row['finite_schwab_iv_observations']}/"
                    f"{row['iv_observations_required']} finite Schwab observations; "
                    f"max_asof_session={row['max_asof_session']}")
            rc = 1 if any(row["state"] == "DATA_GAP" for row in observed) else 0
    for line in lines:
        print(line)
    if out is not None:
        from data.atomic_io import atomic_text_write
        atomic_text_write("\n".join(lines) + "\n", Path(out))
    return rc


def main(
    rows: list[dict] | None = None,
    *,
    as_of: date | str | None = None,
    out: str | Path | None = None,
) -> int:
    """Run the exact-session Schwab observer; injected trigger rows are refused."""
    return _observer_main(as_of=as_of, out=out, rows=rows)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="H5 verified Schwab observer (trigger retired)"
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
        help="run date (YYYY-MM-DD); evaluates the prior completed XNYS session",
    )
    args = parser.parse_args()
    raise SystemExit(main(as_of=args.as_of, out=args.out))

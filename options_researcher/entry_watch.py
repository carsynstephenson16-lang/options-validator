"""H5's verified-Schwab observer. Its historic entry trigger is RETIRED.

Ledger seq 29 clause 1 (H5_AMENDMENT_V1, 2026-08-17) retired
``H5_ENTRY_TRIGGER_PREREG`` and ``H5_ENTRY_TRIGGER_AMENDMENT_V2`` as entry
rules. There is therefore no trigger evaluation, no grading helper, and no FIRE
path anywhere in this module: the only thing it can produce is a descriptive,
non-verdict-bearing observation of per-name price, capture availability, and
single-source Schwab IV-history accumulation (seq 29 clause 2).

``config.H5_ENTRY_TRIGGERS`` survives as frozen HISTORY and as the registered
two-name universe key; its levels are never compared against anything here.
"""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from tools.schwab_chain_manifest import SchwabChainManifestError

OBSERVATION_LABEL = "observational / non-verdict-bearing"


def _resolve_evaluation_session(as_of: date | str | None) -> date:
    """Return the completed session before the requested observer RUN date.

    `as_of` is a RUN date, not the session to evaluate: the run date's own EOD
    is not final, so the observer reads the last COMPLETED session, exactly as
    `h10_watch` does (`h7_watch.evaluation_session`). The daily ritual passes
    `$RUN_DATE` for this reason and names its output file after the resulting
    evaluation session, which is the session `ritual_receipt._h5` then
    demands -- see `H5ObserverAsOfContractTests`.
    """
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


def _h5_symbols() -> tuple[str, ...]:
    return tuple(config.H5_ENTRY_TRIGGERS)


class _VerifiedViewCache:
    """One-``_gather()``-invocation memo over the verified Schwab view.

    ``verified_sessions()`` re-globs the receipts directory and re-checks each
    session, and ``load_chain`` re-reads a parquet, on every call. The
    IV-accumulation count walks every verified session for every name, and
    ``dashboard.assemble()`` / the live server call ``_gather()`` on every
    render, so the unmemoized version repeated the same reads O(names x
    sessions) times per page. Scope is deliberately ONE invocation: a
    process-lifetime cache would keep serving a stale view after a capture
    lands, which is exactly the failure this lane must not have.
    """

    def __init__(self) -> None:
        self._verified: tuple[list[str], list[dict[str, str]]] | None = None
        self._symbols: dict[str, set[str]] = {}
        self._chains: dict[tuple[str, str], tuple[pd.DataFrame | None, str | None]] = {}

    def verified(self) -> tuple[list[str], list[dict[str, str]]]:
        if self._verified is None:
            from options_researcher import schwab_chain_view

            self._verified = schwab_chain_view.verified_sessions()
        return self._verified

    def symbols(self, session: str) -> set[str]:
        if session not in self._symbols:
            from options_researcher import schwab_chain_view

            self._symbols[session] = set(schwab_chain_view.session_symbols(session))
        return self._symbols[session]

    def chain(self, symbol: str, session: str) -> tuple[pd.DataFrame | None, str | None]:
        key = (symbol, session)
        if key not in self._chains:
            from options_researcher import schwab_chain_view

            try:
                self._chains[key] = (schwab_chain_view.load_chain(symbol, session), None)
            except (SchwabChainManifestError, OSError, ValueError) as exc:
                self._chains[key] = (None, f"{type(exc).__name__}: {exc}")
        return self._chains[key]


def _load_exact_verified_schwab_chain(
    symbol: str, evaluation_iso: str, cache: _VerifiedViewCache
) -> tuple[pd.DataFrame | None, str | None]:
    """Load only this NAME's exact verified package; no stale/ThetaData fallback.

    Availability is PER NAME (seq 29 clause 2). A session that captured VST but
    not AMZN is a real VST observation; failing both names on one name's gap
    threw away evidence the amendment requires to be recorded per name.
    """
    sessions, failures = cache.verified()
    if evaluation_iso not in sessions:
        failure = next((item for item in failures
                        if item.get("session") == evaluation_iso), None)
        if failure is not None:
            return None, (f"exact verified Schwab capture is unverified for "
                          f"{evaluation_iso}: {failure['reason']}")
        return None, f"exact verified Schwab capture missing for {evaluation_iso}"
    if symbol not in cache.symbols(evaluation_iso):
        return None, (f"exact verified Schwab capture omits {symbol} for "
                      f"{evaluation_iso}")
    frame, error = cache.chain(symbol, evaluation_iso)
    if frame is None:
        return None, (f"exact verified Schwab capture is malformed for "
                      f"{evaluation_iso}: {error}")
    if frame.empty:
        return None, f"exact verified Schwab capture is empty for {evaluation_iso}"
    return frame, None


def _atm_schwab_iv(chain: pd.DataFrame, evaluation: date) -> tuple[float | None, str | None]:
    """The ATM IV of the nearest monthly expiration, via `features.py`'s helpers.

    Returns ``(value, defect)``. A quoted-but-non-finite IV is
    ``(None, None)`` -- the provider simply published no vol for that contract,
    which is a normal early-history state. A chain that cannot produce an ATM
    row at all is ``(None, reason)``: that is a data defect and must stay
    visible rather than masquerade as a quiet missing quote.

    The store's ``iv`` is ALREADY a decimal fraction (ledger seq 30 corrects
    seq 28/29 clause 2): it is consumed UNSCALED, with no second division.
    """
    from options_researcher.chains import atm_row, nearest_monthly

    try:
        expiration = nearest_monthly(chain, evaluation)
        if expiration is None:
            return None, "no monthly expiration inside the DTE band"
        row = atm_row(chain, expiration)
        if row is None:
            return None, f"no ATM row for expiration {expiration}"
        value = float(row["iv"])
    except (KeyError, TypeError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    return (value, None) if math.isfinite(value) else (None, None)


def _finite_schwab_observation_count(
    symbol: str, evaluation: date, cache: _VerifiedViewCache
) -> int:
    """Count one finite ATM IV per verified session THAT CAPTURED THIS NAME.

    Per name, per seq 29 clause 2's "per-name price, data availability, and
    single-source IV-history accumulation". A session missing an unrelated name
    is not a hole in this name's history.
    """
    count = 0
    for session in cache.verified()[0]:
        if session > evaluation.isoformat():
            continue
        if symbol not in cache.symbols(session):
            continue
        chain, _error = cache.chain(symbol, session)
        if chain is None:
            continue
        value, _defect = _atm_schwab_iv(chain, date.fromisoformat(session))
        if value is not None:
            count += 1
    return count


def _max_asof_session(*sessions: str | None) -> str | None:
    """Return the latest source session recorded for one observer row."""
    return max((session for session in sessions if session is not None), default=None)


def _gather(as_of: date | str | None = None) -> list[dict]:
    """Read exact verified Schwab observer inputs. There is no trigger verdict."""
    from options_researcher.features import PCT_MIN_OBS

    evaluation = _resolve_evaluation_session(as_of)
    evaluation_iso = evaluation.isoformat()
    if evaluation_iso < config.H5_RESUME_FLOOR_SESSION:
        raise ValueError(f"evaluation_session={evaluation_iso} is before resume floor "
                         f"{config.H5_RESUME_FLOOR_SESSION}")
    cache = _VerifiedViewCache()
    out: list[dict] = []
    for symbol in _h5_symbols():
        close, close_asof, close_gap = _exact_close(symbol, evaluation_iso)
        chain, capture_gap = _load_exact_verified_schwab_chain(symbol, evaluation_iso, cache)
        gaps = [gap for gap in (close_gap, capture_gap) if gap is not None]
        if gaps:
            # An UNKNOWN count is never reported as 0: a data-gap session is not
            # evidence that this name has zero finite Schwab IV observations.
            out.append({"symbol": symbol, "state": "DATA_GAP", "verdict": "DATA_GAP",
                        "close": close, "close_asof": close_asof,
                        "capture_available": chain is not None,
                        "capture_session": evaluation_iso if chain is not None else None,
                        "atm_schwab_iv": None,
                        "atm_schwab_iv_state": "NOT_OBSERVED",
                        "finite_schwab_iv_observations": None,
                        "finite_schwab_iv_observations_state": "NOT_COUNTED",
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
        iv, iv_defect = _atm_schwab_iv(chain, evaluation)
        if iv_defect is not None:
            iv_state = f"MALFORMED: {iv_defect}"
        elif iv is None:
            iv_state = "NON_FINITE"
        else:
            iv_state = "OK"
        out.append({"symbol": symbol, "state": "OBSERVED", "verdict": "OBSERVE",
                    "close": close, "close_asof": close_asof,
                    "capture_available": True, "capture_session": evaluation_iso,
                    "atm_schwab_iv": iv,
                    "atm_schwab_iv_state": iv_state,
                    "finite_schwab_iv_observations": _finite_schwab_observation_count(
                        symbol, evaluation, cache),
                    "finite_schwab_iv_observations_state": "COUNTED",
                    "iv_observations_required": PCT_MIN_OBS,
                    "evaluation_session": evaluation_iso,
                    "max_asof_session": evaluation_iso, "reason": None})
    return out


def _iv_label(row: dict) -> str:
    state = row["atm_schwab_iv_state"]
    if state == "OK":
        return f"{row['atm_schwab_iv']:.5f}"
    if state == "NON_FINITE":
        return "unavailable (non-finite quote)"
    return f"MALFORMED ({state.removeprefix('MALFORMED: ')})"


def report_lines(evaluation_iso: str, observed: list[dict]) -> list[str]:
    """Render one observer report. THE single definition of its wire format.

    Public so consumers' tests can build byte-identical fixtures instead of
    hand-writing prose. Hand-written H5 fixtures are exactly how
    `ritual_receipt` and `hypothesis_evidence` came to demand the RETIRED
    WAIT/FIRE vocabulary from a lane that had stopped emitting it while every
    test stayed green.
    """
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
                         f"finite Schwab observations not counted "
                         f"-- refusing observer: {row['reason']}")
            continue
        lines.append(
            f"{row['symbol']}: OBSERVED {OBSERVATION_LABEL}; "
            f"close ${row['close']:,.2f} (as of {row['close_asof']}); "
            f"capture_available={row['capture_available']}; "
            f"verified Schwab capture session {row['capture_session']}; "
            f"ATM Schwab IV {_iv_label(row)}; "
            f"{row['finite_schwab_iv_observations']}/"
            f"{row['iv_observations_required']} finite Schwab observations; "
            f"max_asof_session={row['max_asof_session']}")
    return lines


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
            lines = report_lines(evaluation_iso, observed)
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

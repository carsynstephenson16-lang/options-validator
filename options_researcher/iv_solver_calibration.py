"""options_researcher/iv_solver_calibration.py -- offline calibration of the
repo's own implied-vol solver (options_researcher.black_scholes.implied_vol,
spec-frozen, reused unmodified) against ThetaData's OWN EOD atm_iv.

Why this exists: the cached EOD atm_iv history is ThetaData's own solver
output (European BS, synchronized tick spot, SOFR rate, q=0 -- no dividends
supplied). OUR solver uses a different, also-defensible input set: parity
spot, Treasury CMT continuous rate (data.rates.risk_free_rate), and a
continuous dividend yield (data.rates.dividend_yield). Same model class,
different inputs -> a measurable convention gap. This module MEASURES that
gap, per name, on the EXACT features.py/chains.atm_row contract-selection
convention (0.50-delta put on the nearest monthly, 15-60 DTE, selected via
the chain's OWN cached ThetaData delta column -- not the fixed-point
reselection intraday_capture._solver_atm_iv uses when no delta column is
available at all). The result is a write-once JSON receipt that
options_researcher.intraday_capture.solver_iv_calibration_gate reads to
decide, per name, whether a solver-derived intraday IV may be spliced into
iv_rank_preview. Fail-closed: no receipt (or a stale/mismatched one), no
splice, no exceptions -- this module never touches that gate itself, it only
produces the receipt the gate reads.

Zero network: reads only the local cached EOD chain parquets already on
disk (chains.load_range, allow_oos=True -- the same disclosed post-2022 look
every attractiveness/features build already takes, facts.log
PIVOT_4NAME_SCOPE). A day with no cached chain, no resolvable monthly
expiry, no dividend coverage, or no rate-curve coverage is skipped and
logged in the receipt -- never fabricated.

    uv run python -m options_researcher.iv_solver_calibration
    uv run python -m options_researcher.iv_solver_calibration --symbols VST,CEG --n-sessions 30
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config
from data import rates as data_rates
from data.thetadata_adapter import mid_price
from data.underlying_closes import parity_spot_from_chain
from options_researcher.black_scholes import implied_vol
from options_researcher.chains import atm_row, load_range, nearest_monthly
from research.hashing import config_hash

RECEIPT_KIND = "iv_solver_calibration/v1"
CONTRACT_SELECTION = (
    "chains.atm_row(chains.nearest_monthly(chain, day, min_dte=15, max_dte=60), "
    "right='P', target_delta=0.50) -- ThetaData's own cached delta column, "
    "the EXACT features.py convention"
)
RECEIPT_DIR = Path(config.IV_CALIBRATION_RECEIPT_DIR)


def _pair_for_session(symbol: str, day_iso: str, chain: pd.DataFrame
                      ) -> tuple[dict | None, str | None]:
    """One (our_iv, their_iv, diff) observation for a single cached session
    day, or (None, skip_reason). Never fabricates: any missing input
    (expiry, contract, rate, dividend, quote) is an honest skip."""
    today = date.fromisoformat(day_iso)
    exp = nearest_monthly(chain, today)
    if exp is None:
        return None, "no nearest-monthly expiration in the 15-60 DTE band"
    row = atm_row(chain, exp, right="P", target_delta=0.50)
    if row is None:
        return None, "no 0.50-delta put row on the selected monthly"

    try:
        their_iv = float(row["iv"])
    except (TypeError, ValueError):
        their_iv = float("nan")
    if not math.isfinite(their_iv) or their_iv <= 0:
        return None, "cached ThetaData iv missing/non-finite at selected contract"

    try:
        spot = parity_spot_from_chain(chain, day_iso)
    except Exception as exc:
        return None, f"parity spot raised: {type(exc).__name__}: {exc}"
    if not math.isfinite(spot) or spot <= 0:
        return None, "parity spot non-finite for this session"

    try:
        r = data_rates.risk_free_rate(today, exp).rate
    except data_rates.MissingRateError:
        return None, "no rate curve coverage"
    try:
        q = data_rates.dividend_yield(symbol, today, spot).yield_rate
    except data_rates.MissingDividendYieldError:
        return None, f"no dividend data for {symbol}"

    t = (exp - today).days / 365.0
    if t <= 0:
        return None, "expired"

    bid, ask = float(row["bid"]), float(row["ask"])
    if not (math.isfinite(bid) and math.isfinite(ask)) or ask <= 0 or ask < bid:
        return None, "non-finite/invalid bid-ask at selected contract"
    price = mid_price(bid, ask)

    result = implied_vol(price=price, S=spot, K=float(row["strike"]), t=t,
                         r=r, right="P", q=q)
    if not result.ok:
        return None, f"solver: {result.reason}"

    diff = result.iv - float(their_iv)
    return {
        "day": day_iso, "our_iv": result.iv, "their_iv": float(their_iv),
        "diff": diff, "expiration": exp.isoformat(), "strike": float(row["strike"]),
    }, None


def _per_name_result(symbol: str, n_sessions: int, end_iso: str) -> dict:
    chains = load_range(symbol, config.BACKTEST_START, end_iso, allow_oos=True)
    days = sorted(chains)
    if n_sessions:
        days = days[-n_sessions:]

    pairs: list[dict] = []
    skips: list[dict] = []
    for day_iso in days:
        pair, skip_reason = _pair_for_session(symbol, day_iso, chains[day_iso])
        if pair is not None:
            pairs.append(pair)
        else:
            skips.append({"day": day_iso, "reason": skip_reason})

    diffs = [p["diff"] for p in pairs]
    abs_diffs = [abs(d) for d in diffs]
    if len(diffs) >= 2:
        median_abs_diff = float(np.median(abs_diffs))
        q1, q3 = (float(x) for x in np.percentile(diffs, [25, 75]))
        iqr_width = q3 - q1
        passed = (median_abs_diff <= config.IV_CALIBRATION_MEDIAN_ABS_DIFF_MAX
                  and iqr_width <= config.IV_CALIBRATION_IQR_MAX)
        fail_reason = None if passed else (
            f"median_abs_diff={median_abs_diff:.4f} "
            f"(max {config.IV_CALIBRATION_MEDIAN_ABS_DIFF_MAX}), "
            f"iqr_width={iqr_width:.4f} (max {config.IV_CALIBRATION_IQR_MAX})")
    else:
        median_abs_diff = None
        q1 = q3 = iqr_width = None
        passed = False
        fail_reason = f"insufficient pairs (n_pairs={len(pairs)})"

    return {
        "n_sessions_considered": len(days),
        "n_pairs": len(pairs),
        "n_skipped": len(skips),
        "skips": skips,
        "median_abs_diff": median_abs_diff,
        "iqr_low": q1,
        "iqr_high": q3,
        "iqr_width": iqr_width,
        "pass": passed,
        "fail_reason": fail_reason,
    }


def calibrate(symbols: list[str] | None = None,
             n_sessions: int = config.IV_CALIBRATION_SESSIONS,
             end_iso: str | None = None) -> dict:
    """Calibrate the solver against ThetaData's own EOD atm_iv for each of
    `symbols` (default config.ATTRACTIVENESS_UNIVERSE), over the last
    `n_sessions` cached EOD chain days up to `end_iso` (default: today).
    Returns the receipt dict; does not write it -- see main()/_write_receipt.
    """
    symbols = list(symbols) if symbols is not None else list(config.ATTRACTIVENESS_UNIVERSE)
    end_iso = end_iso or date.today().isoformat()

    per_name: dict[str, dict] = {}
    names_passed: list[str] = []
    names_failed: dict[str, str] = {}
    for symbol in symbols:
        result = _per_name_result(symbol, n_sessions, end_iso)
        per_name[symbol] = result
        if result["pass"]:
            names_passed.append(symbol)
        else:
            names_failed[symbol] = result["fail_reason"]

    return {
        "receipt_kind": RECEIPT_KIND,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "sessions_evaluated": n_sessions,
        "end_iso": end_iso,
        "contract_selection": CONTRACT_SELECTION,
        "config_hash": config_hash(),
        "per_name": per_name,
        "names_passed": sorted(names_passed),
        "names_failed": names_failed,
    }


def receipt_path(receipt_dir: Path, run_date: date) -> Path:
    return Path(receipt_dir) / f"{run_date.isoformat()}.json"


def _write_receipt(receipt: dict, path: Path) -> bool:
    """Write once; an identical rerun is a no-op, conflicts are refused.
    Mirrors options_researcher.intraday_capture._write_receipt exactly."""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline calibration of the repo's Black-Scholes IV "
                    "solver against ThetaData's own EOD atm_iv. Zero "
                    "network; writes a write-once receipt gating "
                    "intraday_capture's solver-derived iv_rank splice.")
    parser.add_argument(
        "--symbols", default=None,
        help="comma-separated symbols (default: config.ATTRACTIVENESS_UNIVERSE)")
    parser.add_argument(
        "--n-sessions", type=int, default=config.IV_CALIBRATION_SESSIONS,
        help=f"trailing cached EOD sessions per name (default "
            f"{config.IV_CALIBRATION_SESSIONS})")
    parser.add_argument(
        "--end", default=None,
        help="end date YYYY-MM-DD (default: today)")
    args = parser.parse_args(argv)

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else None
    receipt = calibrate(symbols=symbols, n_sessions=args.n_sessions, end_iso=args.end)
    run_date = date.today()
    out_path = receipt_path(RECEIPT_DIR, run_date)
    written = _write_receipt(receipt, out_path)
    if not written:
        print(f"iv_solver_calibration receipt CONFLICT -- {out_path} already "
              "has different content")
        return 2
    print(f"receipt={out_path}")
    print(f"passed={receipt['names_passed']}")
    print(f"failed={receipt['names_failed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

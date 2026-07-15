"""QM event study -- one-shot base-rate report for the two mechanical QM
signals (spec docs/superpowers/specs/2026-07-14-qm-signal-research-design.md
§5). Descriptive only: it counts fires and reports forward outcomes NEXT TO
the per-name unconditional baseline. No baseline, no claim. Vocabulary
discipline (repo law): never "works/edge/proven/confirmed" -- only counts,
distributions, "vs baseline", "consistent with".

Run:
    uv run python -m options_researcher.qm_study [--counts-only] [--out PATH]

The gate runs FIRST (spec §7): with QM_* unset in config or the QM_SCOPE_OVERRIDE
/ QM_STUDY_PREREG facts missing, the CLI prints the refusal and exits 2 before
touching any data. --counts-only is the pre-registered feasibility stage: fire
counts and dates ONLY, no outcome computation, stdout only, no file written.
Full mode writes reports/<today NY>-qm-base-rates.md (override with --out) and
echoes the body to stdout. Every study run is one-per-data-vintage: a re-run on
new data is a new dated report, never a threshold retune (QM_STUDY_PREREG).
"""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

from data.thetadata_adapter import passes_liquidity
from options_researcher import qm_signals

START_ISO = "2017-01-01"

CAVEATS = (
    "12 large-cap AI names hindsight-selected after the AI boom -- fire stats "
    "are only meaningful vs the per-name baseline, never raw.",
    "EOD approximation of intraday setups.",
    "This port is a looser superset of the described discretionary setups "
    "(no contraction/velocity test).",
    "Fires cluster across the 12 correlated names -- counts are not "
    "independent draws.",
)


# --------------------------------------------------------------------------
# Default injectable dependencies (lazy imports keep the gate-refusal path,
# and any offline test, from importing the concurrently-built data layer).
# --------------------------------------------------------------------------


def _default_load_adjusted(symbol: str, start: str, end: str) -> pd.DataFrame:
    from data.underlying_ohlcv import load_ohlcv_adjusted

    return load_ohlcv_adjusted(symbol, start, end, allow_oos=True)


def _default_load_raw(symbol: str, start: str, end: str) -> pd.DataFrame:
    from data.underlying_ohlcv import load_ohlcv

    return load_ohlcv(symbol, start, end, allow_oos=True)


def _default_load_chain(symbol: str, iso: str) -> dict[str, pd.DataFrame]:
    from options_researcher.chains import load_range

    return load_range(symbol, iso, iso, allow_oos=True)


def _now_ny_iso() -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


# --------------------------------------------------------------------------
# Pure metric functions (hand-testable against small frames)
# --------------------------------------------------------------------------


def forward_returns(
    frame: pd.DataFrame, t: str, horizons: Sequence[int]
) -> dict[int, float | None]:
    """Adjusted-close forward return close[t+h]/close[t]-1 per horizon. A
    horizon whose t+h falls beyond history is None (disclosed as truncated)."""
    closes = frame["close"].to_numpy(dtype=float)
    pos = int(frame.index.get_loc(t))
    c0 = closes[pos]
    out: dict[int, float | None] = {}
    for h in horizons:
        j = pos + int(h)
        out[int(h)] = (closes[j] / c0 - 1.0) if j < len(closes) and c0 > 0 else None
    return out


def mfe_mae(
    frame: pd.DataFrame, t: str, h_max: int
) -> tuple[float | None, float | None]:
    """Max favorable / max adverse excursion over sessions t+1..t+h_max,
    adjusted high/low vs the fire session's adjusted close. Window is clamped
    to available history; (None, None) when no forward session exists."""
    closes = frame["close"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    pos = int(frame.index.get_loc(t))
    c0 = closes[pos]
    end = min(pos + int(h_max), len(closes) - 1)
    if end <= pos or c0 <= 0:
        return (None, None)
    mfe = float(highs[pos + 1 : end + 1].max()) / c0 - 1.0
    mae = float(lows[pos + 1 : end + 1].min()) / c0 - 1.0
    return (mfe, mae)


def _summ(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"mean": None, "median": None, "n": 0}
    arr = np.asarray(values, dtype=float)
    return {"mean": float(arr.mean()), "median": float(np.median(arr)), "n": int(arr.size)}


def baseline_stats(
    frame: pd.DataFrame, horizons: Sequence[int]
) -> dict[str, Any]:
    """Unconditional distribution over EVERY session where the forward window
    fits: mean/median forward return per horizon plus MFE/MAE over the longest
    horizon. This is the yardstick every fire statistic is printed beside."""
    closes = frame["close"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    n = len(closes)
    h_max = max(int(h) for h in horizons)

    ret: dict[int, dict[str, Any]] = {}
    for h in horizons:
        h = int(h)
        vals = [
            closes[pos + h] / closes[pos] - 1.0
            for pos in range(n)
            if pos + h < n and closes[pos] > 0
        ]
        ret[h] = _summ(vals)

    mfe_vals: list[float] = []
    mae_vals: list[float] = []
    for pos in range(n):
        end = pos + h_max
        if end < n and closes[pos] > 0:
            mfe_vals.append(float(highs[pos + 1 : end + 1].max()) / closes[pos] - 1.0)
            mae_vals.append(float(lows[pos + 1 : end + 1].min()) / closes[pos] - 1.0)
    return {"returns": ret, "mfe": _summ(mfe_vals), "mae": _summ(mae_vals), "h_max": h_max}


def fire_tradability(
    chain: pd.DataFrame | None,
    fire_iso: str,
    raw_close: float,
    dte_band: tuple[int, int],
    ntm_band: float,
) -> bool | str:
    """Tradability of the fire session: True iff the cached chain holds >=1
    contract with DTE in the inclusive band, RAW strike within +/-ntm_band of
    the RAW close, that passes the frozen liquidity gate. No chain file ->
    "no chain" (excluded from the tradability-rate denominator). Fail-closed:
    a non-finite raw close reads as untradable, never tradable."""
    if chain is None or len(chain) == 0:
        return "no chain"
    if not np.isfinite(raw_close):
        return False
    fire_date = date.fromisoformat(fire_iso)
    lo, hi = int(dte_band[0]), int(dte_band[1])
    exp = pd.to_datetime(chain["expiration"]).dt.date
    for row, e in zip(chain.itertuples(index=False), exp, strict=False):
        dte = (e - fire_date).days
        if dte < lo or dte > hi:
            continue
        if abs(float(row.strike) - raw_close) > float(ntm_band) * raw_close:
            continue
        if passes_liquidity(row.open_interest, row.bid, row.ask):
            return True
    return False


# --------------------------------------------------------------------------
# Per-name aggregation (full mode)
# --------------------------------------------------------------------------


def _aggregate_outcomes(
    frame: pd.DataFrame, fires_iso: Sequence[str], horizons: Sequence[int], h_max: int
) -> dict[str, Any]:
    per_h: dict[int, list[float]] = {int(h): [] for h in horizons}
    mfe_vals: list[float] = []
    mae_vals: list[float] = []
    truncated = 0
    for iso in fires_iso:
        fr = forward_returns(frame, iso, horizons)
        if any(v is None for v in fr.values()):
            truncated += 1
        for h, v in fr.items():
            if v is not None:
                per_h[int(h)].append(v)
        mfe, mae = mfe_mae(frame, iso, h_max)
        if mfe is not None:
            mfe_vals.append(mfe)
        if mae is not None:
            mae_vals.append(mae)
    return {
        "returns": {h: _summ(v) for h, v in per_h.items()},
        "mfe": _summ(mfe_vals),
        "mae": _summ(mae_vals),
        "truncated": truncated,
    }


def _aggregate_tradability(
    load_chain: Callable[[str, str], Any],
    symbol: str,
    raw: pd.DataFrame,
    fires_iso: Sequence[str],
    dte_band: tuple[int, int],
    ntm_band: float,
) -> dict[str, int]:
    tradable = untradable = no_chain = 0
    for iso in fires_iso:
        chains = load_chain(symbol, iso)
        chain = chains.get(iso) if isinstance(chains, dict) else chains
        try:
            raw_close = float(raw.loc[iso, "close"])
        except (KeyError, TypeError, ValueError):
            raw_close = float("nan")
        status = fire_tradability(chain, iso, raw_close, dte_band, ntm_band)
        if status == "no chain":
            no_chain += 1
        elif status:
            tradable += 1
        else:
            untradable += 1
    return {"tradable": tradable, "untradable": untradable, "no_chain": no_chain}


def _study_one_name(
    symbol: str,
    load_adjusted: Callable[[str, str, str], pd.DataFrame],
    load_raw: Callable[[str, str, str], pd.DataFrame],
    load_chain: Callable[[str, str], Any],
    params: Mapping[str, Any],
    end_iso: str,
) -> dict[str, Any]:
    """Full-mode result for one name, or a disclosed gap. Fail-closed: a
    missing OHLCV cache is recorded and the name is skipped, never crashes."""
    try:
        frame = load_adjusted(symbol, START_ISO, end_iso)
        raw = load_raw(symbol, START_ISO, end_iso)
    except FileNotFoundError:
        return {"symbol": symbol, "gap": "no OHLCV cache"}

    horizons = tuple(int(h) for h in params["QM_HORIZONS"])
    h_max = max(horizons)
    dte_band = tuple(int(x) for x in params["QM_TRADABILITY_DTE"])
    ntm_band = float(params["QM_NTM_BAND"])

    b_fires = [str(f["t"]) for f in qm_signals.breakout_fires(frame, params)]
    p_fires = [str(f) for f in qm_signals.parabolic_fires(frame, params)]
    baseline = baseline_stats(frame, horizons)

    return {
        "symbol": symbol,
        "gap": None,
        "baseline": baseline,
        "breakout": {
            "n": len(b_fires),
            "fires": b_fires,
            "agg": _aggregate_outcomes(frame, b_fires, horizons, h_max),
            "trad": _aggregate_tradability(
                load_chain, symbol, raw, b_fires, dte_band, ntm_band
            ),
        },
        "parabolic": {
            "n": len(p_fires),
            "fires": p_fires,
            "agg": _aggregate_outcomes(frame, p_fires, horizons, h_max),
            "trad": _aggregate_tradability(
                load_chain, symbol, raw, p_fires, dte_band, ntm_band
            ),
        },
    }


def _counts_one_name(
    symbol: str,
    load_adjusted: Callable[[str, str, str], pd.DataFrame],
    params: Mapping[str, Any],
    end_iso: str,
) -> dict[str, Any]:
    """Counts-only result: fires + dates ONLY. No outcome function is called
    (pre-registered feasibility stage -- outcome paths must not execute)."""
    try:
        frame = load_adjusted(symbol, START_ISO, end_iso)
    except FileNotFoundError:
        return {"symbol": symbol, "gap": "no OHLCV cache"}
    b_fires = [str(f["t"]) for f in qm_signals.breakout_fires(frame, params)]
    p_fires = [str(f) for f in qm_signals.parabolic_fires(frame, params)]
    return {
        "symbol": symbol,
        "gap": None,
        "breakout": {"n": len(b_fires), "fires": b_fires},
        "parabolic": {"n": len(p_fires), "fires": p_fires},
    }


# --------------------------------------------------------------------------
# Report rendering
# --------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _summ_cell(s: Mapping[str, Any]) -> str:
    return f"{_pct(s['mean'])} / {_pct(s['median'])}"


def _header(today_iso: str) -> list[str]:
    return [
        "# QM signal event study -- base rates",
        "",
        f"Data vintage: {today_iso}. CONTRACT: this study runs once per data "
        "vintage; a re-run on new data is a new dated report, never a threshold "
        "retune without a new fact (spec §5, QM_STUDY_PREREG).",
        "",
        "Descriptive screen only -- no hypothesis, book, or verdict. Fire "
        "outcomes are meaningful ONLY beside the per-name baseline below.",
        "",
        "## Caveats (read first)",
        "",
        *[f"- {c}" for c in CAVEATS],
        "",
    ]


def _counts_table(results: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["## Fire counts", "", "| name | breakout | parabolic | note |",
             "| --- | --- | --- | --- |"]
    for r in results:
        if r.get("gap"):
            lines.append(f"| {r['symbol']} | -- | -- | {r['gap']} |")
        else:
            lines.append(
                f"| {r['symbol']} | {r['breakout']['n']} | "
                f"{r['parabolic']['n']} | |"
            )
    lines.append("")
    return lines


def _fire_dates(results: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["## Fire dates", ""]
    for r in results:
        if r.get("gap"):
            lines.append(f"- {r['symbol']}: {r['gap']}")
            continue
        b = ", ".join(r["breakout"]["fires"]) or "none"
        p = ", ".join(r["parabolic"]["fires"]) or "none"
        lines.append(f"- {r['symbol']} breakout: {b}")
        lines.append(f"- {r['symbol']} parabolic: {p}")
    lines.append("")
    return lines


def _outcome_table(
    title: str,
    agg: Mapping[str, Any],
    baseline: Mapping[str, Any],
    horizons: Sequence[int],
    *,
    flip: bool = False,
) -> list[str]:
    def _flip(s: Mapping[str, Any]) -> dict[str, Any]:
        if not flip:
            return dict(s)
        return {
            "mean": None if s["mean"] is None else -s["mean"],
            "median": None if s["median"] is None else -s["median"],
            "n": s["n"],
        }

    lines = [
        f"#### {title}",
        "",
        "| horizon | fire mean/median | baseline mean/median |",
        "| --- | --- | --- |",
    ]
    for h in horizons:
        h = int(h)
        lines.append(
            f"| +{h}d | {_summ_cell(_flip(agg['returns'][h]))} | "
            f"{_summ_cell(_flip(baseline['returns'][h]))} |"
        )
    if flip:
        # A fade view: down-moves are favorable, so MFE/MAE swap roles.
        fav, adv = _flip(agg["mae"]), _flip(agg["mfe"])
        bfav, badv = _flip(baseline["mae"]), _flip(baseline["mfe"])
    else:
        fav, adv = agg["mfe"], agg["mae"]
        bfav, badv = baseline["mfe"], baseline["mae"]
    lines.append(
        f"| favorable excursion | {_summ_cell(fav)} | {_summ_cell(bfav)} |"
    )
    lines.append(
        f"| adverse excursion | {_summ_cell(adv)} | {_summ_cell(badv)} |"
    )
    trunc = agg.get("truncated", 0)
    if trunc:
        lines.append("")
        lines.append(
            f"_{trunc} fire(s) had >=1 horizon beyond history (truncated, "
            "excluded from that horizon's mean/median)._"
        )
    lines.append("")
    return lines


def _outcomes_section(
    results: Sequence[Mapping[str, Any]], horizons: Sequence[int]
) -> list[str]:
    lines = ["## Outcomes vs baseline", ""]
    for r in results:
        if r.get("gap"):
            lines.append(f"### {r['symbol']}")
            lines.append("")
            lines.append(f"{r['gap']} -- skipped, no outcomes.")
            lines.append("")
            continue
        baseline = r["baseline"]
        lines.append(f"### {r['symbol']}")
        lines.append("")
        b = r["breakout"]
        if b["n"]:
            lines += _outcome_table(
                f"Breakout ({b['n']} fires)", b["agg"], baseline, horizons
            )
        else:
            lines.append("Breakout: fired 0 times.")
            lines.append("")
        p = r["parabolic"]
        if p["n"]:
            lines += _outcome_table(
                f"Parabolic ({p['n']} fires)", p["agg"], baseline, horizons
            )
            lines += _outcome_table(
                f"Parabolic ({p['n']} fires) -- fade view (sign-flipped)",
                p["agg"],
                baseline,
                horizons,
                flip=True,
            )
        else:
            lines.append("Parabolic: fired 0 times.")
            lines.append("")
    return lines


def _tradability_section(results: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = [
        "## Tradability rates",
        "",
        "Rate = tradable / (fires - no-chain); no-chain fires are excluded "
        "from the denominator and disclosed.",
        "",
        "| name | setup | tradable | untradable | no chain |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        if r.get("gap"):
            lines.append(f"| {r['symbol']} | -- | -- | -- | {r['gap']} |")
            continue
        for setup in ("breakout", "parabolic"):
            t = r[setup]["trad"]
            lines.append(
                f"| {r['symbol']} | {setup} | {t['tradable']} | "
                f"{t['untradable']} | {t['no_chain']} |"
            )
    lines.append("")
    return lines


def build_report(
    today_iso: str,
    results: Sequence[Mapping[str, Any]],
    *,
    counts_only: bool = False,
    params: Mapping[str, Any] | None = None,
) -> str:
    """Render the study report. counts_only -> header, caveats, counts and
    fire dates only (no outcome numbers). Full -> adds per-name outcome tables
    beside baselines and tradability rates. Renders provided results only;
    computes nothing itself (outcome paths never run in counts_only)."""
    lines = _header(today_iso)
    lines += _counts_table(results)
    lines += _fire_dates(results)
    if not counts_only:
        horizons = tuple(int(h) for h in (params or {}).get("QM_HORIZONS", ()))
        lines += _outcomes_section(results, horizons)
        lines += _tradability_section(results)
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        prog="qm_study", description="QM signal event study (descriptive, one-shot)"
    )
    ap.add_argument(
        "--counts-only",
        action="store_true",
        help="fire counts and dates only; no outcomes, no file written",
    )
    ap.add_argument("--out", default=None, help="report path (full mode only)")
    return ap.parse_args(list(argv) if argv is not None else None)


def main(
    argv: Sequence[str] | None = None,
    *,
    universe: Sequence[str] | None = None,
    load_adjusted: Callable[[str, str, str], pd.DataFrame] | None = None,
    load_raw: Callable[[str, str, str], pd.DataFrame] | None = None,
    load_chain: Callable[[str, str], Any] | None = None,
    params: Mapping[str, Any] | None = None,
    gate: Callable[[], str | None] | None = None,
) -> int:
    args = _parse_args(argv)

    # GATE FIRST -- before any data is touched (spec §7).
    gate_fn = gate if gate is not None else qm_signals.qm_prereg_gate
    reason = gate_fn()
    if reason:
        print(reason)
        return 2

    if universe is None:
        from options_researcher.h7_scope import watch_universe

        universe = watch_universe()
    if params is None:
        params = qm_signals.qm_params()
    load_adjusted = load_adjusted or _default_load_adjusted
    load_raw = load_raw or _default_load_raw
    load_chain = load_chain or _default_load_chain

    end_iso = _now_ny_iso()

    if args.counts_only:
        results = [
            _counts_one_name(s, load_adjusted, params, end_iso) for s in universe
        ]
        body = build_report(end_iso, results, counts_only=True)
        print(body, end="")
        return 0

    results = [
        _study_one_name(s, load_adjusted, load_raw, load_chain, params, end_iso)
        for s in universe
    ]
    body = build_report(end_iso, results, counts_only=False, params=params)

    out_path = args.out or f"reports/{end_iso}-qm-base-rates.md"
    from pathlib import Path

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(body)
    print(body, end="")
    print(f"\n(wrote {out_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

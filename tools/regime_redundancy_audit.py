"""tools/regime_redundancy_audit.py -- REGIME-AMI-v1 redundancy audit.

Runs the pre-registered, frozen-parameter descriptive test of whether the
walk-forward Wasserstein regime lane (options_researcher/regime.py) carries
information beyond the repo's existing regime read -- rv_percentile +
ma_posture -- on the four core names. Full frozen design, decision rule, and
provenance: docs/superpowers/2026-08-03-regime-ami-redundancy-registration.md.
Every parameter used here (window/step/clusters/refit/seed/etc, the rv
tercile bins, the posture->index mapping, the >=100-step eligibility floor,
and the 0.50 decision threshold) is FROZEN by that registration, not chosen
by this module.

Usage: uv run python -m tools.regime_redundancy_audit

REGISTRATION GATE: this refuses to run (exit 2) unless the ledger already
carries a `trial_intent` record with hypothesis_id == "REGIME-AMI-v1".

VOCABULARY DISCIPLINE (.cursorrules): this is a descriptive audit of a
display-only lane. Its result is never described as "proven", "confirmed",
"works", or "guaranteed" -- only REDUNDANT / RETAINS_DISTINCT_INFORMATION /
INSUFFICIENT_DATA, per the frozen decision rule. It is not a trade verdict
and never gates a registered H-hypothesis.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json  # noqa: E402
import math  # noqa: E402
import statistics  # noqa: E402
import subprocess  # noqa: E402
from datetime import datetime  # noqa: E402
from pathlib import Path  # noqa: E402
from zoneinfo import ZoneInfo  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config  # noqa: E402
from data.underlying_closes import load_closes_adjusted  # noqa: E402
from options_researcher import h7_signals, regime, technicals  # noqa: E402
from research import ledger  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")

HYPOTHESIS_ID = "REGIME-AMI-v1"
REGISTRATION_DOC = "docs/superpowers/2026-08-03-regime-ami-redundancy-registration.md"

# Frozen universe (registration): the four core names AT REGISTRATION TIME,
# not whatever config.REGIME_SYMBOLS happens to hold when this runs later.
FROZEN_SYMBOLS = ["VST", "CEG", "MSFT", "AMZN"]
DATA_START = "2018-01-01"

# Fixed rv-tercile bins (NOT data-fitted quantiles) and posture->index map.
POSTURE_INDEX = {"above_all": 0, "below_all": 1, "mixed": 2}
MEDIAN_AMI_THRESHOLD = 0.50
MIN_INCLUDED_STEPS = 100

DEFAULT_OUT_DIR = Path("reports/regime")
RECEIPT_JSON_NAME = "2026-08-03-regime-ami-v1-receipt.json"
RECEIPT_MD_NAME = "2026-08-03-regime-ami-v1-receipt.md"

DISCLAIMER = (
    "Descriptive audit of a display-only lane; not a trade verdict. A "
    "RETAINS_DISTINCT_INFORMATION result is 'not yet rejected on "
    "redundancy', nothing more."
)


class RegistrationGateError(Exception):
    """Raised when the REGIME-AMI-v1 ledger registration is absent."""


# --------------------------------------------------------------------------
# Registration gate
# --------------------------------------------------------------------------


def check_registration(records: list[dict]) -> bool:
    """True iff a trial_intent record for HYPOTHESIS_ID exists in `records`."""
    return any(
        r.get("entry_type") == "trial_intent" and r.get("hypothesis_id") == HYPOTHESIS_ID
        for r in records
    )


def require_registration(records: list[dict]) -> None:
    if not check_registration(records):
        raise RegistrationGateError(
            f"no trial_intent ledger record for hypothesis_id={HYPOTHESIS_ID!r}; "
            f"register per {REGISTRATION_DOC} before running this audit"
        )


# --------------------------------------------------------------------------
# Feature grid (fixed bins/mapping, per registration)
# --------------------------------------------------------------------------


def rv_tercile(rv: float) -> int:
    """Fixed bins [0,1/3) -> 0, [1/3,2/3) -> 1, [2/3,1.0] -> 2."""
    if rv < 1.0 / 3.0:
        return 0
    if rv < 2.0 / 3.0:
        return 1
    return 2


def feature_grid_cell(rv: float, posture: str) -> int | None:
    """tercile*3 + posture_index, or None when posture has no fixed index
    (i.e. `insufficient_history`, which callers must already have excluded)."""
    posture_index = POSTURE_INDEX.get(posture)
    if posture_index is None:
        return None
    return rv_tercile(rv) * 3 + posture_index


# --------------------------------------------------------------------------
# Adjusted Mutual Information -- numpy + math only, exact hypergeometric EMI.
# --------------------------------------------------------------------------


def _contingency_table(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    _, u_codes = np.unique(u, return_inverse=True)
    _, v_codes = np.unique(v, return_inverse=True)
    n_u = int(u_codes.max()) + 1
    n_v = int(v_codes.max()) + 1
    table = np.zeros((n_u, n_v), dtype=np.int64)
    np.add.at(table, (u_codes, v_codes), 1)
    return table


def _entropy(marginal: np.ndarray, n: float) -> float:
    counts = marginal[marginal > 0].astype(float)
    p = counts / n
    return float(-np.sum(p * np.log(p)))


def _mutual_information(table: np.ndarray) -> float:
    n = float(table.sum())
    a = table.sum(axis=1).astype(float)
    b = table.sum(axis=0).astype(float)
    mi = 0.0
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            nij = float(table[i, j])
            if nij <= 0:
                continue
            mi += (nij / n) * math.log((nij * n) / (a[i] * b[j]))
    return float(mi)


def _expected_mutual_information(a: np.ndarray, b: np.ndarray, n: int) -> float:
    """Exact hypergeometric E[MI] (Vinh/Epps/Hubert), via log-factorials
    (math.lgamma) for numerical stability -- no scipy/sklearn dependency."""
    log_n_fact = math.lgamma(n + 1)
    emi = 0.0
    for a_val in a:
        ai = int(a_val)
        log_ai = math.lgamma(ai + 1)
        log_n_ai = math.lgamma(n - ai + 1)
        for b_val in b:
            bj = int(b_val)
            log_bj = math.lgamma(bj + 1)
            log_n_bj = math.lgamma(n - bj + 1)
            lo = max(ai + bj - n, 0)
            hi = min(ai, bj)
            for nij in range(lo, hi + 1):
                if nij == 0:
                    continue
                log_den = (
                    log_n_fact
                    + math.lgamma(nij + 1)
                    + math.lgamma(ai - nij + 1)
                    + math.lgamma(bj - nij + 1)
                    + math.lgamma(n - ai - bj + nij + 1)
                )
                term = math.exp(log_ai + log_bj + log_n_ai + log_n_bj - log_den)
                emi += (nij / n) * math.log((n * nij) / (ai * bj)) * term
    return float(emi)


def adjusted_mutual_info(u: np.ndarray, v: np.ndarray) -> tuple[float, bool]:
    """(AMI, degenerate) for two equal-length integer label series.

    Natural-log MI from the contingency table; exact hypergeometric E[MI];
    arithmetic-mean normalization (H(U)+H(V))/2, per the registration.
    Degenerate single-class series (either series has one unique value)
    return (0.0, True) rather than dividing by a zero-information baseline.
    A near-zero denominator in the non-degenerate case (both partitions
    carrying identical information, e.g. a pure relabeling of one another)
    resolves to AMI := 1.0.
    """
    u_arr = np.asarray(u)
    v_arr = np.asarray(v)
    if u_arr.shape[0] != v_arr.shape[0]:
        raise ValueError("u and v must be the same length")
    n = u_arr.shape[0]
    if n == 0:
        raise ValueError("u and v must not be empty")
    if len(np.unique(u_arr)) <= 1 or len(np.unique(v_arr)) <= 1:
        return 0.0, True

    table = _contingency_table(u_arr, v_arr)
    n_f = float(n)
    a = table.sum(axis=1).astype(float)
    b = table.sum(axis=0).astype(float)

    mi = _mutual_information(table)
    emi = _expected_mutual_information(a, b, n)
    hu = _entropy(a, n_f)
    hv = _entropy(b, n_f)

    denom = 0.5 * (hu + hv) - emi
    if abs(denom) < 1e-10:
        return 1.0, False
    return float((mi - emi) / denom), False


# --------------------------------------------------------------------------
# Per-symbol computation
# --------------------------------------------------------------------------


def _empty_result(symbol: str, status: str, note: str | None = None) -> dict:
    return {
        "symbol": symbol,
        "status": status,
        "n_labeled": 0,
        "n_included": 0,
        "as_of": None,
        "ami": None,
        "eligible": False,
        "degenerate": False,
        "note": note,
    }


def load_symbol_closes(
    symbol: str,
    loader,
    start_iso: str,
    end_iso: str,
) -> pd.Series | None:
    """None on FileNotFoundError (no cached closes) -- never fabricated."""
    try:
        return loader(symbol, start_iso, end_iso, allow_oos=True)
    except FileNotFoundError:
        return None


def compute_symbol_result(
    symbol: str,
    closes: pd.Series,
    *,
    window: int = config.REGIME_WINDOW_DAYS,
    step: int = config.REGIME_STEP_DAYS,
    n_clusters: int = config.REGIME_N_CLUSTERS,
    refit_every: int = config.REGIME_REFIT_EVERY,
    min_fit_windows: int = config.REGIME_MIN_FIT_WINDOWS,
    n_init: int = config.REGIME_N_INIT,
    seed: int = config.REGIME_SEED,
) -> dict:
    """One symbol's walk-forward labels vs the rv-tercile x posture grid.

    `past = closes.loc[:t]` is INCLUSIVE of the label's own end date t (the
    close at t is known at t's EOD -- the same causality convention the
    walk-forward label itself uses). Steps whose posture is
    `insufficient_history` are excluded from the comparison (not counted in
    n_included, never fed to the AMI computation). Parameter defaults are
    the frozen config.REGIME_* values; overrides exist only for injectable
    test speed-ups, never used by the CLI path.
    """
    try:
        windows_arr, end_dates = regime.make_return_windows(closes, window, step)
        labels_df = regime.walk_forward_labels(
            windows_arr,
            end_dates,
            n_clusters=n_clusters,
            refit_every=refit_every,
            min_fit_windows=min_fit_windows,
            n_init=n_init,
            seed=seed,
        )
    except ValueError as exc:
        result = _empty_result(symbol, "INSUFFICIENT_HISTORY", note=str(exc))
        result["as_of"] = str(closes.index[-1]) if len(closes) > 0 else None
        return result

    labeled = labels_df[labels_df["label"].notna()]
    n_labeled = int(len(labeled))

    included_labels: list[int] = []
    included_cells: list[int] = []
    for t, row in labeled.iterrows():
        past = closes.loc[:t]
        rv = h7_signals.rv_percentile(past)
        posture = technicals.technical_snapshot(past)["ma_posture"]
        if posture == "insufficient_history":
            continue
        cell = feature_grid_cell(rv, posture)
        assert cell is not None
        included_labels.append(int(row["label"]))
        included_cells.append(cell)

    n_included = len(included_labels)
    eligible = n_included >= MIN_INCLUDED_STEPS

    ami: float | None = None
    degenerate = False
    if n_included > 0:
        ami, degenerate = adjusted_mutual_info(
            np.asarray(included_labels), np.asarray(included_cells)
        )

    return {
        "symbol": symbol,
        "status": "OK",
        "n_labeled": n_labeled,
        "n_included": n_included,
        "as_of": str(closes.index[-1]),
        "ami": ami,
        "eligible": eligible,
        "degenerate": degenerate,
        "note": None,
    }


# --------------------------------------------------------------------------
# Decision + receipt
# --------------------------------------------------------------------------


def decide(results: list[dict]) -> tuple[str, float | None]:
    """Median-AMI decision rule, frozen by the registration."""
    eligible_amis = [
        r["ami"]
        for r in results
        if r.get("status") == "OK" and r.get("eligible") and r.get("ami") is not None
    ]
    if len(eligible_amis) < 2:
        return "INSUFFICIENT_DATA", None
    median = float(statistics.median(eligible_amis))
    if median >= MEDIAN_AMI_THRESHOLD:
        return "REDUNDANT", median
    return "RETAINS_DISTINCT_INFORMATION", median


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if out.returncode != 0:
        return "unknown"
    sha = out.stdout.strip()
    return sha if sha else "unknown"


def _resolved_params(overrides: dict) -> dict:
    params = {
        "window": config.REGIME_WINDOW_DAYS,
        "step": config.REGIME_STEP_DAYS,
        "n_clusters": config.REGIME_N_CLUSTERS,
        "refit_every": config.REGIME_REFIT_EVERY,
        "min_fit_windows": config.REGIME_MIN_FIT_WINDOWS,
        "n_init": config.REGIME_N_INIT,
        "seed": config.REGIME_SEED,
        "symbols": list(FROZEN_SYMBOLS),
        "data_start": DATA_START,
        "median_ami_threshold": MEDIAN_AMI_THRESHOLD,
        "min_included_steps": MIN_INCLUDED_STEPS,
    }
    params.update(overrides)
    return params


def _render_markdown(receipt: dict) -> str:
    lines = [
        "# REGIME-AMI-v1 redundancy-audit receipt",
        "",
        f"- hypothesis_id: `{receipt['hypothesis_id']}`",
        f"- registration: `{receipt['registration_doc']}`",
        f"- ledger record present: {receipt['ledger_record_present']}",
        f"- code SHA: `{receipt['code_sha']}`",
        f"- timestamp (America/New_York): {receipt['timestamp']}",
        "",
        "## Frozen parameters",
        "",
        "```json",
        json.dumps(receipt["params"], indent=2),
        "```",
        "",
        "## Per-symbol results",
        "",
        "| symbol | status | n_labeled | n_included | eligible | as_of | ami | degenerate | note |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in receipt["symbols"]:
        ami = "null" if r["ami"] is None else f"{r['ami']:.4f}"
        lines.append(
            f"| {r['symbol']} | {r['status']} | {r['n_labeled']} | {r['n_included']} | "
            f"{r['eligible']} | {r['as_of']} | {ami} | {r['degenerate']} | {r.get('note') or ''} |"
        )
    lines += [
        "",
        f"- eligible symbols: {receipt['eligible_symbols']}",
        f"- median AMI: {receipt['median_ami']}",
        f"- **decision: {receipt['decision']}**",
        "",
        f"> {receipt['disclaimer']}",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_receipt(receipt: dict, out_dir: Path = DEFAULT_OUT_DIR) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / RECEIPT_JSON_NAME
    md_path = out_dir / RECEIPT_MD_NAME
    json_path.write_text(json.dumps(receipt, indent=2) + "\n")
    md_path.write_text(_render_markdown(receipt))
    return json_path, md_path


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def run_audit(
    *,
    loader,
    ledger_reader=ledger.read_all,
    out_dir: Path = DEFAULT_OUT_DIR,
    today_iso: str | None = None,
    symbols: list[str] | None = None,
    regime_overrides: dict | None = None,
) -> dict:
    """Run the full REGIME-AMI-v1 audit and write its receipt.

    `loader` and `ledger_reader` are injected (production defaults are
    data.underlying_closes.load_closes_adjusted and research.ledger.read_all);
    `regime_overrides` lets tests shrink window/step/etc for runtime only --
    the CLI path (main()) never passes any override, so it always uses the
    frozen config.REGIME_* values. Raises RegistrationGateError if the
    REGIME-AMI-v1 trial_intent is absent from the ledger.
    """
    require_registration(ledger_reader())

    syms = list(FROZEN_SYMBOLS) if symbols is None else list(symbols)
    overrides = dict(regime_overrides) if regime_overrides else {}
    resolved_today = (
        datetime.now(NY).date().isoformat() if today_iso is None else today_iso
    )

    results: list[dict] = []
    for symbol in syms:
        closes = load_symbol_closes(symbol, loader, DATA_START, resolved_today)
        if closes is None:
            results.append(_empty_result(symbol, "DATA_MISSING"))
            continue
        results.append(compute_symbol_result(symbol, closes, **overrides))

    decision, median_ami = decide(results)
    eligible_symbols = [
        r["symbol"] for r in results if r.get("status") == "OK" and r.get("eligible")
    ]

    receipt = {
        "hypothesis_id": HYPOTHESIS_ID,
        "registration_doc": REGISTRATION_DOC,
        "ledger_record_present": True,
        "code_sha": _git_sha(),
        "timestamp": datetime.now(NY).isoformat(),
        "params": _resolved_params(overrides),
        "symbols": results,
        "eligible_symbols": eligible_symbols,
        "median_ami": median_ami,
        "decision": decision,
        "disclaimer": DISCLAIMER,
    }

    json_path, md_path = write_receipt(receipt, out_dir)
    exit_code = 1 if decision == "INSUFFICIENT_DATA" else 0

    return {
        "decision": decision,
        "median_ami": median_ami,
        "results": results,
        "receipt": receipt,
        "json_path": json_path,
        "md_path": md_path,
        "exit_code": exit_code,
    }


def main() -> int:
    try:
        outcome = run_audit(loader=load_closes_adjusted, ledger_reader=ledger.read_all)
    except RegistrationGateError as exc:
        print(f"REFUSED: {exc}")
        return 2

    median = outcome["median_ami"]
    median_text = f" (median AMI {median:.3f})" if median is not None else ""
    print(f"DECISION: {outcome['decision']}{median_text}")
    for r in outcome["results"]:
        print(
            f"  {r['symbol']}: status={r['status']} n_included={r['n_included']} "
            f"eligible={r['eligible']} ami={r['ami']}"
        )
    print(f"receipt: {outcome['json_path']}")
    print(f"receipt: {outcome['md_path']}")
    return outcome["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())

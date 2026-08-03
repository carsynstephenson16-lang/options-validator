"""options_researcher/regime_report.py -- Wasserstein regime report CLI.

DISPLAY-ONLY, non-verdict-bearing. Adapted from
mehul532/wasserstein-market-regime-clustering (MIT License, Copyright (c)
2026 mehul532) -- see .cursorrules "Scope guard" owner-directed exception,
2026-08-03. Reads cached underlying closes ONLY (`data.underlying_closes`) --
no network, no yfinance. See `options_researcher/regime.py` for the causal
walk-forward labeling core this report renders.

Every section states its own max as-of session and makes no claim past it.
Regime labels are unsupervised historical descriptions with no predictive
test behind them; transition frequencies are historical frequencies, not
forecasts; nothing here gates, sizes, or triggers a trade.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from options_researcher.regime import (
    make_return_windows,
    transition_frequencies,
    walk_forward_labels,
)

DEFAULT_OUT = Path(".tmp/regime/regime_report.md")
CLOSE_HISTORY_START = "2018-01-01"

DISCLAIMER = (
    "**Display-only, non-verdict-bearing.** This is not a registered signal. "
    "Regime labels are unsupervised historical descriptions that have "
    "survived no predictive test. Transition frequencies are historical "
    "frequencies, not forecasts."
)


def _today_ny_iso() -> str:
    from datetime import datetime

    return datetime.now(ZoneInfo("America/New_York")).date().isoformat()


def _default_loader(symbol: str, start_iso: str, end_iso: str) -> pd.Series:
    from data.underlying_closes import load_closes_adjusted

    return load_closes_adjusted(symbol, start_iso, end_iso, allow_oos=True)


def _min_rows_required() -> int:
    return config.REGIME_WINDOW_DAYS + config.REGIME_MIN_FIT_WINDOWS * config.REGIME_STEP_DAYS


def _skip_section(symbol: str, reason: str) -> str:
    return f"## {symbol} -- SKIPPED\n\nReason: {reason}\n"


def _symbol_section(
    symbol: str,
    *,
    end_iso: str,
    loader: Callable[[str, str, str], pd.Series],
) -> str:
    try:
        closes = loader(symbol, CLOSE_HISTORY_START, end_iso)
    except FileNotFoundError as exc:
        return _skip_section(
            symbol, f"no cached close series ({exc.__class__.__name__}: {exc})"
        )

    min_rows = _min_rows_required()
    if closes is None or len(closes) < min_rows:
        got = 0 if closes is None else len(closes)
        return _skip_section(
            symbol,
            f"only {got} cached close rows through {end_iso}; need at least "
            f"{min_rows} (REGIME_WINDOW_DAYS + REGIME_MIN_FIT_WINDOWS * "
            "REGIME_STEP_DAYS)",
        )

    as_of = str(closes.index[-1])[:10]
    windows, end_dates = make_return_windows(
        closes, config.REGIME_WINDOW_DAYS, config.REGIME_STEP_DAYS
    )
    labeled = walk_forward_labels(
        windows,
        end_dates,
        n_clusters=config.REGIME_N_CLUSTERS,
        refit_every=config.REGIME_REFIT_EVERY,
        min_fit_windows=config.REGIME_MIN_FIT_WINDOWS,
        n_init=config.REGIME_N_INIT,
        seed=config.REGIME_SEED,
    )
    labeled_rows = labeled.dropna(subset=["label"])
    if labeled_rows.empty:
        return _skip_section(
            symbol,
            f"cached history through {as_of} produced no walk-forward label "
            "yet (fewer than REGIME_MIN_FIT_WINDOWS training windows)",
        )

    latest = labeled_rows.iloc[-1]
    latest_date = labeled_rows.index[-1]
    counts = labeled_rows["label"].value_counts().sort_index()

    lines = [f"## {symbol}", ""]
    lines.append(
        f"**Max as-of session (last cached close): {as_of}.** This report "
        "makes no claim about any session after this date."
    )
    lines.append("")
    lines.append(
        f"- Latest walk-forward regime label: **{int(latest['label'])}** "
        f"(window ending {latest_date}, fit on {int(latest['n_fit_windows'])} "
        "training windows)"
    )
    lines.append(
        "- High-dispersion regime at latest label: "
        f"**{'yes' if bool(latest['high_dispersion']) else 'no'}**"
    )
    lines.append("")
    lines.append("Windows per label (walk-forward, all labeled steps to date):")
    lines.append("")
    lines.append("| label | window count |")
    lines.append("|---|---|")
    for label, count in counts.items():
        lines.append(f"| {int(label)} | {int(count)} |")
    lines.append("")
    # transition_frequencies needs >= 2 labeled steps; a history that clears
    # the min-rows gate can still land in the exactly-one-label band, and a
    # display-only report must degrade, not crash (fail-closed discipline).
    if len(labeled_rows) >= 2:
        freq = transition_frequencies(labeled_rows["label"])
        lines.append("Transition frequencies (historical frequencies, not forecasts):")
        lines.append("")
        lines.append("| label | " + " | ".join(str(c) for c in freq.columns) + " |")
        lines.append("|---" * (len(freq.columns) + 1) + "|")
        for label, row in freq.iterrows():
            lines.append(f"| {label} | " + " | ".join(f"{v:.2f}" for v in row) + " |")
    else:
        lines.append(
            "Transition frequencies: not shown -- only one labeled step "
            "exists so far (at least 2 are needed)."
        )
    lines.append("")
    return "\n".join(lines)


def build_report(
    symbols: Sequence[str] = tuple(config.REGIME_SYMBOLS),
    *,
    out_path: Path | str = DEFAULT_OUT,
    loader: Callable[[str, str, str], pd.Series] = _default_loader,
    end_iso: str | None = None,
) -> tuple[str, int]:
    """Render the markdown regime report and write it to `out_path`.

    Returns (report_text, exit_code): exit_code is 0 unless EVERY symbol is
    SKIPPED, in which case it is 1. Never fabricates or substitutes data --
    a symbol with a missing cache file or too short a history is SKIPPED
    with the reason stated, not silently dropped.
    """
    resolved_end = end_iso or _today_ny_iso()
    sections = [
        _symbol_section(symbol, end_iso=resolved_end, loader=loader) for symbol in symbols
    ]
    all_skipped = bool(sections) and all(
        section.splitlines()[0].endswith("SKIPPED") for section in sections
    )

    header = [
        "# Wasserstein regime-clustering report",
        "",
        f"Requested as-of end bound: {resolved_end} (America/New_York). "
        "Adapted from mehul532/wasserstein-market-regime-clustering "
        "(MIT License, Copyright (c) 2026 mehul532).",
        "",
        DISCLAIMER,
        "",
    ]
    text = "\n".join(header) + "\n" + "\n\n".join(sections) + "\n"

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

    return text, (1 if all_skipped else 0)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline Wasserstein regime-clustering report "
            "(display-only, non-verdict-bearing)"
        )
    )
    parser.add_argument("--symbols", nargs="+", default=list(config.REGIME_SYMBOLS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    _, exit_code = build_report(args.symbols, out_path=args.out)
    print(f"Wasserstein regime report written to {args.out}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

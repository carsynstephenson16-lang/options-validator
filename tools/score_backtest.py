"""Read-only in-sample scoreboard over the cached real-data backtest path."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import date as Date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from data.thetadata_adapter import OOSDataTouchError  # noqa: E402
from harness import run_backtest  # noqa: E402
from metrics import print_scoreboard, scoreboard  # noqa: E402
from research import ledger as research_ledger  # noqa: E402
from strategies.put_credit_spread import PutCreditSpread  # noqa: E402


def _parse_symbols(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    symbols = [s.strip().upper() for s in raw.split(",") if s.strip()]
    if not symbols:
        raise ValueError("--symbols must contain at least one symbol")
    return symbols


def _json_ready(value):
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _validate_in_sample(start: str, end: str) -> None:
    start_d = Date.fromisoformat(start)
    end_d = Date.fromisoformat(end)
    if end_d < start_d:
        raise ValueError(f"end {end} is before start {start}")
    if end_d > Date.fromisoformat(config.IN_SAMPLE_END):
        raise OOSDataTouchError(
            f"score_backtest end {end} is past IN_SAMPLE_END={config.IN_SAMPLE_END}; "
            "use the research OOS reveal gate for holdout reads."
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the cached in-sample PutCreditSpread backtest and score it."
    )
    parser.add_argument("--symbols", help="comma-separated symbols, e.g. SPY,QQQ")
    parser.add_argument("--start", default=config.BACKTEST_START)
    parser.add_argument("--end", default=config.IN_SAMPLE_END)
    parser.add_argument("--label")
    parser.add_argument("--json", action="store_true", help="print scoreboard as JSON")
    parser.add_argument(
        "--dsr-n-source", choices=["ledger", "off"], default="off",
        help="Deflated Sharpe Ratio N-trials provenance: 'ledger' reads the "
             "hash-chained research/ledger.py trial count (provenance "
             "'ledger-trial-count'); 'off' (default) computes no DSR/PSR at "
             "all. Display/diagnostic only -- never affects the verdict.",
    )
    parser.add_argument(
        "--dsr-trial-sr-var", type=float, default=None,
        help="trial_sr_variance for the DSR's E[max SR] deflation term. "
             "Required when --dsr-n-source=ledger: there is no stored "
             "per-trial Sharpe series repo-wide to compute this from, so it "
             "must be supplied explicitly -- never guessed or defaulted.",
    )
    args = parser.parse_args(argv)

    dsr_kwargs = {}
    if args.dsr_n_source == "ledger":
        if args.dsr_trial_sr_var is None:
            print(
                "score_backtest refused: --dsr-trial-sr-var is required "
                "when --dsr-n-source=ledger (no stored per-trial SR series "
                "to compute it from; never guessed)",
                file=sys.stderr,
            )
            return 1
        dsr_kwargs = {
            "dsr_n_trials": research_ledger.current_trial_count(),
            "dsr_trial_sr_variance": args.dsr_trial_sr_var,
            "dsr_n_provenance": "ledger-trial-count",
        }

    try:
        symbols = _parse_symbols(args.symbols)
        _validate_in_sample(args.start, args.end)
        trades = run_backtest.run(
            PutCreditSpread,
            start=args.start,
            end=args.end,
            symbols=symbols,
            allow_oos=False,
        )
        label_symbols = ",".join(symbols or config.UNIVERSE)
        label = args.label or (
            f"PutCreditSpread {label_symbols} {args.start}..{args.end}"
        )
        result = scoreboard(trades, label=label, **dsr_kwargs)
    except (ValueError, OOSDataTouchError) as exc:
        print(f"score_backtest refused: {exc}", file=sys.stderr)
        return 1

    if dsr_kwargs:
        # Echo the operator-supplied trial_sr_variance back in both output
        # modes -- it is an input the caller typed, not something scoreboard()
        # computed, so it belongs alongside the result for reproducibility.
        result["dsr_trial_sr_variance_input"] = args.dsr_trial_sr_var

    if args.json:
        print(json.dumps(_json_ready(result), indent=2, sort_keys=True))
    else:
        print_scoreboard(result)
        if dsr_kwargs:
            print(f"  DSR trial_sr_variance input   {args.dsr_trial_sr_var}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

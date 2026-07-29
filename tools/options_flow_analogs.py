"""Offline CLI for point-in-time options-flow analogs and opinion synthesis."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from options_researcher.flow.analogs import match_historical_analogs
from options_researcher.flow.opinion import synthesize_historical_opinion
from options_researcher.flow.schema import DISTANCE_FEATURES


def _features(value: str) -> list[str]:
    fields = [field.strip() for field in value.split(",") if field.strip()]
    if not fields:
        raise argparse.ArgumentTypeError("features must contain at least one column")
    return list(dict.fromkeys(fields))


def _matched_base_positive_frequency(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "matched-base-positive-frequency must be within [0, 1]"
        ) from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        raise argparse.ArgumentTypeError("matched-base-positive-frequency must be within [0, 1]")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build display-only historical options-flow analogs"
    )
    parser.add_argument("panel", type=Path)
    parser.add_argument("--query-session", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument(
        "--features",
        type=_features,
        default=list(DISTANCE_FEATURES),
        help="comma-separated distance columns",
    )
    parser.add_argument(
        "--matched-base-positive-frequency",
        type=_matched_base_positive_frequency,
    )
    parser.add_argument("--output", type=Path)
    return parser


def _read_panel(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError("panel must be parquet or csv")


def run(args: argparse.Namespace) -> int:
    panel = _read_panel(args.panel)
    primary = match_historical_analogs(
        panel,
        query_session=args.query_session,
        symbol=args.symbol,
        feature_columns=args.features,
    )
    pooled = match_historical_analogs(
        panel,
        query_session=args.query_session,
        symbol=args.symbol,
        feature_columns=args.features,
        pool_symbols=True,
    )
    opinion = synthesize_historical_opinion(
        primary,
        pooled=pooled,
        matched_base_positive_frequency=args.matched_base_positive_frequency,
    )
    payload = {
        "authority": "DISPLAY_ONLY_RESEARCH_NONCAUSAL",
        "primary": primary.as_dict(),
        "pooled": pooled.as_dict(),
        "opinion": opinion.as_dict(),
    }
    text = json.dumps(payload, sort_keys=True, indent=2, default=str) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())

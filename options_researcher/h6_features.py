"""Build current H6 IV-rank features from the local cache only.

This command never fetches data.  It rebuilds exactly the existing repo
feature definition over the most recent 252 cached symbol sessions ending on
an explicitly requested evaluation session, then writes the ordinary
``.tmp/research/{symbol}_features.parquet`` artifact consumed by h6_watch.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import config
from data.underlying_closes import load_closes
from options_researcher.features import (
    PCT_MIN_OBS,
    PCT_WINDOW,
    build_daily_features,
)

CHAIN_DIR = Path(".cache/chains")
FEATURE_DIR = Path(".tmp/research")


def _dated_paths(symbol: str, as_of: date, chain_dir: Path) -> list[tuple[date, Path]]:
    out: list[tuple[date, Path]] = []
    prefix = f"{symbol.upper()}_"
    for path in chain_dir.glob(f"{prefix}*.parquet"):
        raw = path.stem[len(prefix):]
        try:
            day = date.fromisoformat(raw)
        except ValueError as exc:
            raise ValueError(f"malformed chain filename for {symbol}: {path}") from exc
        if day <= as_of:
            out.append((day, path))
    return sorted(out)


def build_symbol_features(
    symbol: str,
    as_of: date,
    *,
    chain_dir: Path = CHAIN_DIR,
    feature_dir: Path = FEATURE_DIR,
) -> Path:
    """Build one exact-session H6 feature artifact from cached facts only."""
    sym = symbol.upper()
    if sym not in config.H6_NAMES:
        raise ValueError(f"{sym} is outside registered H6 scope {config.H6_NAMES}")
    dated = _dated_paths(sym, as_of, chain_dir)
    if not dated or dated[-1][0] != as_of:
        raise FileNotFoundError(
            f"exact H6 chain missing: {chain_dir / f'{sym}_{as_of.isoformat()}.parquet'}"
        )
    dated = dated[-PCT_WINDOW:]
    if len(dated) < PCT_MIN_OBS:
        raise ValueError(
            f"{sym}: only {len(dated)} cached sessions through {as_of}; "
            f"IV-rank requires at least {PCT_MIN_OBS}"
        )
    chains = {day.isoformat(): pd.read_parquet(path) for day, path in dated}
    first = dated[0][0]
    close_start = first - timedelta(days=60)
    closes = load_closes(
        sym, close_start.isoformat(), as_of.isoformat(), allow_oos=True
    )
    frame = build_daily_features(
        sym,
        first.isoformat(),
        as_of.isoformat(),
        closes=closes,
        chains=chains,
        earnings=[],
    )
    if frame.empty or frame.index[-1] != as_of.isoformat():
        raise RuntimeError(f"{sym}: feature build did not produce exact session {as_of}")
    if pd.isna(frame.iloc[-1]["iv_rank"]):
        raise RuntimeError(f"{sym}: exact-session IV-rank remains unavailable")
    feature_dir.mkdir(parents=True, exist_ok=True)
    output = feature_dir / f"{sym}_features.parquet"
    frame.to_parquet(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build exact-session H6 IV-rank features from local cache only"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    args = parser.parse_args(argv)
    for symbol in config.H6_NAMES:
        path = build_symbol_features(symbol, args.as_of)
        print(f"{symbol}: {args.as_of.isoformat()} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

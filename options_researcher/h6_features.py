"""Build current H6 IV-rank features from the local cache only.

This command never fetches data.  It rebuilds exactly the existing repo
feature definition over the most recent 252 cached symbol sessions ending on
an explicitly requested evaluation session, then writes the ordinary
``.tmp/research/{symbol}_features.parquet`` artifact consumed by h6_watch.
Each artifact is written atomically with a self-hashed provenance manifest
covering every contributing chain, the close store, feature parameters,
runtime versions, builder source, exact output bytes, and each chain's
content-matching ``BLIND_CACHE`` acquisition fact.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import platform
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pyarrow

import config
from data import underlying_closes
from data.cache_provenance import FACTS_PATH, load_blind_cache_facts
from options_researcher.features import (
    EARN_BD_AFTER,
    EARN_BD_BEFORE,
    PCT_MIN_OBS,
    PCT_WINDOW,
    RV_WINDOW,
    build_daily_features,
)
from research.hashing import canonical_json, sha256_file, sha256_hex

CHAIN_DIR = Path(".cache/chains")
FEATURE_DIR = Path(".tmp/research")
FEATURE_MANIFEST_SCHEMA = "h6_feature_manifest_v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURE_SOURCE_PATHS = (
    "config.py",
    "data/cache_provenance.py",
    "data/underlying_closes.py",
    "options_researcher/chains.py",
    "options_researcher/features.py",
    "options_researcher/h6_features.py",
    "research/hashing.py",
)


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


def feature_manifest_path(symbol: str, feature_dir: Path = FEATURE_DIR) -> Path:
    return Path(feature_dir) / f"{symbol.upper()}_features.manifest.json"


def _feature_parameters() -> dict:
    return {
        "scope": list(config.H6_NAMES),
        "rv_window": RV_WINDOW,
        "iv_rank_window": PCT_WINDOW,
        "iv_rank_min_observations": PCT_MIN_OBS,
        "earnings_business_days_before": EARN_BD_BEFORE,
        "earnings_business_days_after": EARN_BD_AFTER,
        "earnings_input": [],
        "chain_selection": "last_252_cached_sessions_through_as_of",
        "close_lookback_calendar_days": 60,
    }


def _runtime_versions() -> dict:
    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
    }


def _source_files() -> dict[str, str]:
    return {rel: sha256_file(REPO_ROOT / rel) for rel in FEATURE_SOURCE_PATHS}


def _file_record(path: Path) -> dict[str, object]:
    resolved = Path(path).resolve()
    return {"path": str(resolved), "sha256": sha256_file(resolved)}


def _durable_sync(fd: int) -> None:
    os.fsync(fd)
    if sys.platform == "darwin":
        fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


def _sync_parent(path: Path) -> None:
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def _atomic_write_frame(frame: pd.DataFrame, output: Path) -> None:
    with tempfile.NamedTemporaryFile(
        dir=output.parent, prefix=f".{output.name}.", suffix=".tmp", delete=False
    ) as fh:
        tmp = Path(fh.name)
    try:
        frame.to_parquet(tmp)
        fd = os.open(tmp, os.O_RDONLY)
        try:
            _durable_sync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, output)
        _sync_parent(output)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _atomic_write_manifest(manifest: dict, path: Path) -> None:
    payload = (canonical_json(manifest) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as fh:
        tmp = Path(fh.name)
        try:
            fh.write(payload)
            fh.flush()
            _durable_sync(fh.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
        _sync_parent(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _build_manifest(
    symbol: str,
    as_of: date,
    *,
    dated: list[tuple[date, Path]],
    close_path: Path,
    output: Path,
    close_start: date,
    facts_path: Path,
) -> dict:
    facts = load_blind_cache_facts(facts_path)
    chain_files: dict[str, dict[str, object]] = {}
    for day, path in dated:
        iso = day.isoformat()
        record = _file_record(path)
        fact = facts.get((symbol, iso))
        if fact is None:
            raise ValueError(f"{symbol} {iso}: missing BLIND_CACHE provenance fact")
        if fact["sha256"] != record["sha256"]:
            raise ValueError(f"{symbol} {iso}: BLIND_CACHE sha256 mismatch")
        record["provenance"] = {
            "type": "BLIND_CACHE",
            "fetched_at": fact["fetched"].isoformat(),
            "sha256": fact["sha256"],
        }
        chain_files[iso] = record
    provenance_evidence = {
        day: record["provenance"] for day, record in chain_files.items()
    }
    source_files = _source_files()
    manifest = {
        "schema": FEATURE_MANIFEST_SCHEMA,
        "symbol": symbol,
        "as_of": as_of.isoformat(),
        "feature_window": {
            "first_session": dated[0][0].isoformat(),
            "last_session": dated[-1][0].isoformat(),
            "chain_count": len(dated),
            "close_start": close_start.isoformat(),
        },
        "parameters": _feature_parameters(),
        "runtime": _runtime_versions(),
        "inputs": {
            "chains": chain_files,
            "closes": _file_record(close_path),
        },
        "provenance": {
            "source": str(Path(facts_path).resolve()),
            "evidence_hash": sha256_hex(canonical_json(provenance_evidence)),
        },
        "output": _file_record(output),
        "source_files": source_files,
        "source_hash": sha256_hex(canonical_json(source_files)),
    }
    manifest["manifest_hash"] = sha256_hex(canonical_json(manifest))
    return manifest


def verify_feature_manifest(
    symbol: str,
    as_of: date,
    *,
    feature_dir: Path = FEATURE_DIR,
    chain_dir: Path = CHAIN_DIR,
    facts_path: Path = FACTS_PATH,
) -> dict:
    """Verify one feature artifact against every byte that produced it."""
    sym = symbol.upper()
    output = Path(feature_dir) / f"{sym}_features.parquet"
    path = feature_manifest_path(sym, feature_dir)
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid H6 feature manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise ValueError(f"invalid H6 feature manifest {path}: root must be an object")
    hashable = {k: v for k, v in manifest.items() if k != "manifest_hash"}
    if sha256_hex(canonical_json(hashable)) != manifest.get("manifest_hash"):
        raise ValueError(f"invalid H6 feature manifest {path}: manifest_hash")
    if manifest.get("schema") != FEATURE_MANIFEST_SCHEMA:
        raise ValueError(f"invalid H6 feature manifest {path}: schema")
    if manifest.get("symbol") != sym or manifest.get("as_of") != as_of.isoformat():
        raise ValueError(f"invalid H6 feature manifest {path}: identity")
    if manifest.get("parameters") != _feature_parameters():
        raise ValueError(f"invalid H6 feature manifest {path}: parameters")
    if manifest.get("runtime") != _runtime_versions():
        raise ValueError(f"invalid H6 feature manifest {path}: runtime")
    source_files = _source_files()
    if manifest.get("source_files") != source_files:
        raise ValueError(f"invalid H6 feature manifest {path}: source_files")
    if manifest.get("source_hash") != sha256_hex(canonical_json(source_files)):
        raise ValueError(f"invalid H6 feature manifest {path}: source_hash")

    window = manifest.get("feature_window")
    inputs = manifest.get("inputs")
    if not isinstance(window, dict) or not isinstance(inputs, dict):
        raise ValueError(f"invalid H6 feature manifest {path}: structure")
    chains = inputs.get("chains")
    if not isinstance(chains, dict):
        raise ValueError(f"invalid H6 feature manifest {path}: chains")
    expected_dated = _dated_paths(sym, as_of, Path(chain_dir))[-PCT_WINDOW:]
    expected_days = [day.isoformat() for day, _ in expected_dated]
    if not expected_days or (
        window.get("last_session") != as_of.isoformat()
        or window.get("first_session") != expected_days[0]
        or window.get("chain_count") != len(chains)
        or len(chains) < PCT_MIN_OBS
        or list(chains) != expected_days
    ):
        raise ValueError(f"invalid H6 feature manifest {path}: feature_window")
    records = [inputs.get("closes"), manifest.get("output"), *chains.values()]
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"invalid H6 feature manifest {path}: file record")
        recorded_path = record.get("path")
        if not isinstance(recorded_path, str):
            raise ValueError(f"invalid H6 feature manifest {path}: file path")
        file_path = Path(recorded_path)
        if not file_path.is_file() or sha256_file(file_path) != record.get("sha256"):
            raise ValueError(
                f"invalid H6 feature manifest {path}: mutated file {file_path}"
            )
    close_record = inputs.get("closes")
    expected_close_path = (
        Path(underlying_closes.CACHE_DIR) / f"{sym}.parquet"
    ).resolve()
    if not isinstance(close_record, dict) or close_record.get("path") != str(
        expected_close_path
    ):
        raise ValueError(f"invalid H6 feature manifest {path}: close identity")
    for day, record in chains.items():
        if not isinstance(record, dict) or record.get("path") != str(
            (Path(chain_dir) / f"{sym}_{day}.parquet").resolve()
        ):
            raise ValueError(f"invalid H6 feature manifest {path}: chain identity")
    facts = load_blind_cache_facts(facts_path)
    provenance_evidence: dict[str, dict] = {}
    for day, record in chains.items():
        if not isinstance(record, dict):
            raise ValueError(f"invalid H6 feature manifest {path}: chain record")
        fact = facts.get((sym, day))
        expected = None
        if fact is not None:
            expected = {
                "type": "BLIND_CACHE",
                "fetched_at": fact["fetched"].isoformat(),
                "sha256": fact["sha256"],
            }
        if expected is None or record.get("provenance") != expected:
            raise ValueError(f"invalid H6 feature manifest {path}: provenance {day}")
        if expected["sha256"] != record.get("sha256"):
            raise ValueError(
                f"invalid H6 feature manifest {path}: provenance sha256 {day}"
            )
        provenance_evidence[day] = expected
    provenance = manifest.get("provenance")
    expected_evidence_hash = sha256_hex(canonical_json(provenance_evidence))
    if (
        not isinstance(provenance, dict)
        or provenance.get("source") != str(Path(facts_path).resolve())
        or provenance.get("evidence_hash") != expected_evidence_hash
    ):
        raise ValueError(f"invalid H6 feature manifest {path}: provenance identity")
    output_record = manifest.get("output")
    if not isinstance(output_record, dict) or output_record.get("path") != str(
        output.resolve()
    ):
        raise ValueError(f"invalid H6 feature manifest {path}: output identity")
    return manifest


def build_symbol_features(
    symbol: str,
    as_of: date,
    *,
    chain_dir: Path = CHAIN_DIR,
    feature_dir: Path = FEATURE_DIR,
    facts_path: Path = FACTS_PATH,
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
    close_path = Path(underlying_closes.CACHE_DIR) / f"{sym}.parquet"
    if not close_path.is_file():
        raise FileNotFoundError(f"H6 underlying close store missing: {close_path}")
    closes = underlying_closes.load_closes(
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
    _atomic_write_frame(frame, output)
    manifest = _build_manifest(
        sym,
        as_of,
        dated=dated,
        close_path=close_path,
        output=output,
        close_start=close_start,
        facts_path=facts_path,
    )
    _atomic_write_manifest(manifest, feature_manifest_path(sym, feature_dir))
    verify_feature_manifest(
        sym,
        as_of,
        feature_dir=feature_dir,
        chain_dir=chain_dir,
        facts_path=facts_path,
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build exact-session H6 IV-rank features from local cache only"
    )
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    args = parser.parse_args(argv)
    for symbol in config.H6_NAMES:
        path = build_symbol_features(symbol, args.as_of)
        manifest = feature_manifest_path(symbol)
        print(f"{symbol}: {args.as_of.isoformat()} -> {path} + {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

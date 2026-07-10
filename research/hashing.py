"""
research/hashing.py -- deterministic hashing surfaces for the ledger.

The frozen cost/fill params are scattered across files (ASSUMED_CREDIT_FRAC is
in analysis/feasibility.py, the rest in config.py), so we hash ONE explicit
snapshot object -- never a line/string search that could silently miss a param.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import config
from analysis import feasibility

SOURCE_HASH_PATHS = (
    "pyproject.toml",
    "uv.lock",
    "config.py",
    "metrics.py",
    "analysis",
    "data",
    "harness",
    "research",
    "strategies",
)
REPO_ROOT = Path(__file__).resolve().parents[1]


def canonical_json(obj) -> str:
    """Stable serialization: sorted keys, compact, ASCII."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cost_model_snapshot() -> dict:
    """The single frozen, verdict-affecting surface. Hashed into cost_model_hash."""
    return {
        "SLIPPAGE_HAIRCUT": config.SLIPPAGE_HAIRCUT,
        "MAX_SPREAD_PCT": config.MAX_SPREAD_PCT,
        "MIN_OPEN_INTEREST": config.MIN_OPEN_INTEREST,
        "HALF_SPREAD_COST": config.HALF_SPREAD_COST,
        "COMMISSION_PER_CONTRACT": config.COMMISSION_PER_CONTRACT,
        "ASSUMED_CREDIT_FRAC": feasibility.ASSUMED_CREDIT_FRAC,
        "FILL_MODEL_ID": config.FILL_MODEL_ID,
        "BOOTSTRAP_BLOCK_EXPONENT": config.BOOTSTRAP_BLOCK_EXPONENT,
        "BOOTSTRAP_BLOCK_CONSTANTS": list(config.BOOTSTRAP_BLOCK_CONSTANTS),
        "COHORT_GRANULARITY": config.COHORT_GRANULARITY,
        "OOS_LOOK_BUDGET": config.OOS_LOOK_BUDGET,
    }


def cost_model_hash() -> str:
    return sha256_hex(canonical_json(cost_model_snapshot()))


def config_hash() -> str:
    """Provenance hash of ALL uppercase config constants (a superset of the snapshot)."""
    vals = {k: getattr(config, k) for k in dir(config)
            if k.isupper() and not k.startswith("_")}
    return sha256_hex(canonical_json(vals))


def source_snapshot(paths=SOURCE_HASH_PATHS, root=None) -> dict:
    """Hash the verdict/backtest source surface, excluding ledgers and outputs.

    This is intentionally separate from `git rev-parse HEAD`: ledger anchoring
    commits should not invalidate a pre-registration, while source/config changes
    that affect the hypothesis must.
    """
    root_path = Path(root) if root is not None else REPO_ROOT
    out = {}
    for item in paths:
        path = root_path / item
        if path.is_dir():
            files = sorted(
                p for p in path.rglob("*.py")
                if "__pycache__" not in p.parts
            )
        elif path.is_file():
            files = [path]
        else:
            continue
        for file_path in files:
            rel = file_path.relative_to(root_path).as_posix()
            out[rel] = sha256_file(file_path)
    return out


def source_hash(paths=SOURCE_HASH_PATHS, root=None) -> str:
    return sha256_hex(canonical_json(source_snapshot(paths=paths, root=root)))


def data_window_hash(window: dict) -> str:
    """Hash of the data-window identity. Once ThetaData is wired this also folds in
    a content digest of the cached chains; in Phase 1A it hashes the identity dict."""
    return sha256_hex(canonical_json(window))


# ---------------------------------------------------------------------------
# Diagnostic source-hash contract v2 (7b-2, owner decision 2026-07-10).
# The legacy SOURCE_HASH_PATHS above stays byte-identical so every historical
# ledger entry keeps verifying; H7 diagnostic records bind this WIDER surface
# (everything that can affect a diagnostic verdict) and carry an explicit
# source_hash_version so the contract is versioned, never retro-changed.
# ---------------------------------------------------------------------------
DIAGNOSTIC_SOURCE_PATHS_V2 = SOURCE_HASH_PATHS + ("options_researcher", "tools")
DIAGNOSTIC_SOURCE_HASH_VERSION = 2


def diagnostic_source_hash(root=None) -> str:
    return source_hash(paths=DIAGNOSTIC_SOURCE_PATHS_V2, root=root)

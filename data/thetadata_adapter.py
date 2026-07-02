"""
data/thetadata_adapter.py -- EOD option-chain access with local caching.

STATUS: PHASE 0 WIRED, PENDING LIVE SMOKE TEST. The fetch path below talks to
the same local ThetaTerminal that Lumibot manages (see
docs/superpowers/2026-07-02-phase0-lumibot-thetadata-verification.md for the
endpoint evidence). Column names on the greeks/IV endpoints are fail-loud
guesses until the first live smoke test confirms them -- do NOT trust the fetch
path before `python smoke_test.py` passes against a real terminal.

Note: Lumibot ships ThetaDataBacktesting natively, so inside the backtest loop
Lumibot pulls its own quote data for FILLS. This adapter exists because the
installed lumibot exposes NO greeks and NO open interest (verified 2026-07-02):
strike selection by delta and the both-legs OI liquidity gate need this chain.

Integrity: any date after config.IN_SAMPLE_END is refused unless the caller is
the OOS reveal path (allow_oos=True) -- "just printing a chain" after 2022 is
still a holdout look (spec, Unit 4).
"""
from __future__ import annotations
import io
import os
import re
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

import config

CACHE_DIR = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Local ThetaTerminal v3 REST (verified: lumibot thetadata_helper.py:342).
THETA_BASE_URL = os.environ.get("THETADATA_BASE_URL", "http://127.0.0.1:25503")
READINESS_PATH = "/v3/terminal/mdds/status"
_V3_CHAIN_ENDPOINTS = {
    "eod": "/v3/option/history/eod",
    "greeks": "/v3/option/history/greeks/first_order",
    "iv": "/v3/option/history/greeks_implied_volatility",
    "oi": "/v3/option/history/open_interest",
}
_REQUEST_TIMEOUT_S = 120

# Schema every downstream consumer expects from a chain DataFrame:
CHAIN_COLUMNS = [
    "expiration", "strike", "right",         # right in {"P", "C"}
    "bid", "ask", "open_interest",
    "iv", "delta", "gamma", "theta", "vega",
]
NUMERIC_CHAIN_COLUMNS = [
    "strike", "bid", "ask", "open_interest",
    "iv", "delta", "gamma", "theta", "vega",
]
_SYMBOL_RE = re.compile(r"^[A-Z0-9._-]+$")


class OOSDataTouchError(ValueError):
    """A data probe tried to open post-IN_SAMPLE_END market data outside the
    OOS reveal gate. This is an integrity refusal, not a transport error."""


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise ValueError("symbol must be a string")
    normalized = symbol.strip().upper()
    if not normalized or not _SYMBOL_RE.fullmatch(normalized):
        raise ValueError(f"invalid symbol for cache key: {symbol!r}")
    return normalized


def _normalize_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("date must be an ISO date string")
    try:
        return Date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"date must be an ISO date string: {value!r}") from exc


def _cache_path(symbol: str, date: str) -> Path:
    return CACHE_DIR / f"{_normalize_symbol(symbol)}_{_normalize_date(date)}.parquet"


def validate_chain_schema(chain: pd.DataFrame) -> pd.DataFrame:
    """Fail before malformed cached/fetched chain data reaches strategy logic."""
    if not isinstance(chain, pd.DataFrame):
        raise ValueError("option chain must be a pandas DataFrame")
    missing = [col for col in CHAIN_COLUMNS if col not in chain.columns]
    if missing:
        raise ValueError(f"option chain missing required column(s): {missing}")
    if chain["right"].isna().any():
        raise ValueError("option chain column 'right' contains missing values")
    rights = set(chain["right"].astype(str).str.upper().unique())
    invalid_rights = rights - {"P", "C"}
    if invalid_rights:
        raise ValueError(f"option chain has invalid right values: {sorted(invalid_rights)}")
    for col in NUMERIC_CHAIN_COLUMNS:
        values = pd.to_numeric(chain[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"option chain column {col!r} contains non-finite values")
    return chain


# --------------------------------------------------------------------------
# ThetaTerminal fetch path (live-verified only once the smoke test passes)
# --------------------------------------------------------------------------

def _ensure_terminal() -> None:
    """Ensure a local ThetaTerminal is serving at THETA_BASE_URL; if not, start
    it via lumibot's launcher using THETADATA_USERNAME/THETADATA_PASSWORD.

    AUTH NOTE (2026-07-02 live result): Path A (email+password via lumibot's
    launcher) was executed and terminal 20260629 REJECTED the login
    ("Invalid credentials") in a relaunch loop -- see the Phase-0 doc and
    ledger/facts.log. Until the owner refreshes the password or authorizes a
    Path B launch (THETA_DATA_API_KEY, terminal >= 20260615), this probe
    fails loud here. The fetch path below is launcher-agnostic once a
    terminal is alive at THETA_BASE_URL, however it was started."""
    import requests

    try:
        resp = requests.get(THETA_BASE_URL + READINESS_PATH, timeout=2)
        if resp.ok:
            return
    except requests.RequestException:
        pass

    from lumibot.credentials import THETADATA_CONFIG
    from lumibot.tools import thetadata_helper

    username = THETADATA_CONFIG.get("THETADATA_USERNAME")
    password = THETADATA_CONFIG.get("THETADATA_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            f"ThetaTerminal is not running at {THETA_BASE_URL} and "
            "THETADATA_USERNAME/THETADATA_PASSWORD are not set. Either add "
            "email+password to .env for lumibot's launcher, or start "
            "ThetaTerminal yourself with THETA_DATA_API_KEY exported (a valid "
            "key is in .env). Terminal also requires a Java >= 21 runtime."
        )
    thetadata_helper.check_connection(username, password, wait_for_connection=True)

    resp = requests.get(THETA_BASE_URL + READINESS_PATH, timeout=10)
    if not resp.ok:
        raise RuntimeError(
            f"ThetaTerminal did not become ready at {THETA_BASE_URL} "
            f"(status {resp.status_code}). Check credentials and Java runtime."
        )


def _fetch_v3_csv(endpoint_key: str, symbol: str, date: str) -> pd.DataFrame:
    """One whole-chain request (expiration=*, strike=*, both rights) for one day,
    CSV format so the response shape is flat and self-describing."""
    import requests

    params = {
        "symbol": symbol,
        "expiration": "*",
        "strike": "*",
        "right": "both",
        "start_date": date,
        "end_date": date,
        "format": "csv",
    }
    if endpoint_key in ("greeks", "iv"):
        # EOD values: one row per contract. Fail-loud guess until the live
        # smoke test confirms the interval semantics (see module docstring).
        params["interval"] = "1d"
    url = THETA_BASE_URL + _V3_CHAIN_ENDPOINTS[endpoint_key]
    resp = requests.get(url, params=params, timeout=_REQUEST_TIMEOUT_S)
    if not resp.ok:
        raise RuntimeError(
            f"ThetaData {endpoint_key} request failed: HTTP {resp.status_code} "
            f"for {url} ({resp.text[:200]!r})"
        )
    frame = pd.read_csv(io.StringIO(resp.text))
    if frame.empty:
        raise RuntimeError(
            f"ThetaData {endpoint_key} returned no rows for {symbol} @ {date}. "
            "Likely outside your subscription's history window, a non-trading "
            "day, or an EOD gap -- skip the day (log it), do not substitute."
        )
    return frame


def _pick_col(frame: pd.DataFrame, candidates, ctx: str) -> str:
    for name in candidates:
        if name in frame.columns:
            return name
    raise ValueError(
        f"{ctx}: none of {list(candidates)} present; got columns "
        f"{sorted(frame.columns)}"
    )


_KEY_COLS = ["expiration", "strike", "right"]


def _normalize_contract_keys(frame: pd.DataFrame, ctx: str) -> pd.DataFrame:
    """Lowercase columns; normalize right to P/C; one row per contract (last
    report of the day wins when a timestamp column is present)."""
    out = frame.copy()
    out.columns = [str(c).strip().lower() for c in out.columns]
    missing = [k for k in _KEY_COLS if k not in out.columns]
    if missing:
        raise ValueError(
            f"{ctx}: missing contract key column(s) {missing}; got "
            f"{sorted(out.columns)}"
        )
    right = out["right"].astype(str).str.strip().str.upper().str[0]
    if not set(right.unique()) <= {"P", "C"}:
        raise ValueError(
            f"{ctx}: unexpected right values {sorted(out['right'].astype(str).unique())}"
        )
    out["right"] = right
    out["expiration"] = out["expiration"].astype(str)
    out["strike"] = pd.to_numeric(out["strike"], errors="coerce")
    if "timestamp" in out.columns:
        out = out.sort_values("timestamp", kind="stable")
    return out.drop_duplicates(subset=_KEY_COLS, keep="last")


def _merge_chain_frames(eod: pd.DataFrame, greeks: pd.DataFrame,
                        iv: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    """Inner-join the four per-contract frames into CHAIN_COLUMNS.

    Inner join is deliberate fail-closed behavior: a contract missing quotes,
    greeks, or open interest is untradeable under the liquidity/delta rules, so
    it is dropped here rather than passed downstream with NaNs. The caller
    logs the drop count."""
    eod = _normalize_contract_keys(eod, "eod")
    greeks = _normalize_contract_keys(greeks, "greeks")
    iv = _normalize_contract_keys(iv, "implied_volatility")
    oi = _normalize_contract_keys(oi, "open_interest")

    bid_col = _pick_col(eod, ("bid", "close_bid", "bid_price"), "eod")
    ask_col = _pick_col(eod, ("ask", "close_ask", "ask_price"), "eod")
    iv_col = _pick_col(iv, ("implied_volatility", "implied_vol", "iv"), "implied_volatility")
    oi_col = _pick_col(oi, ("open_interest", "oi"), "open_interest")
    for greek in ("delta", "gamma", "theta", "vega"):
        _pick_col(greeks, (greek,), "greeks")

    merged = (
        eod[_KEY_COLS + [bid_col, ask_col]]
        .rename(columns={bid_col: "bid", ask_col: "ask"})
        .merge(greeks[_KEY_COLS + ["delta", "gamma", "theta", "vega"]],
               on=_KEY_COLS, how="inner")
        .merge(iv[_KEY_COLS + [iv_col]].rename(columns={iv_col: "iv"}),
               on=_KEY_COLS, how="inner")
        .merge(oi[_KEY_COLS + [oi_col]].rename(columns={oi_col: "open_interest"}),
               on=_KEY_COLS, how="inner")
    )
    return merged[CHAIN_COLUMNS].reset_index(drop=True)


def _fetch_merged_chain(symbol: str, date: str):
    """Fetch the four per-contract frames and merge into a validated chain.
    Returns (chain, dropped_count). Callers decide how the drop count is
    reported -- the blind-cache path must not print anything."""
    _ensure_terminal()
    eod = _fetch_v3_csv("eod", symbol, date)
    greeks = _fetch_v3_csv("greeks", symbol, date)
    iv = _fetch_v3_csv("iv", symbol, date)
    oi = _fetch_v3_csv("oi", symbol, date)

    chain = _merge_chain_frames(eod, greeks, iv, oi)
    validate_chain_schema(chain)
    return chain, len(eod) - len(chain)


def get_eod_chain(symbol: str, date: str, *, allow_oos: bool = False) -> pd.DataFrame:
    """Return the validated EOD option chain for `symbol` on `date` (YYYY-MM-DD),
    fetched from the local ThetaTerminal on cache miss and cached as parquet.

    Dates after config.IN_SAMPLE_END are refused (OOSDataTouchError) unless the
    OOS reveal gate passes allow_oos=True -- reading a cached post-2022 chain
    outside the gate is still a holdout look.
    """
    symbol = _normalize_symbol(symbol)
    date = _normalize_date(date)
    if date > config.IN_SAMPLE_END and not allow_oos:
        raise OOSDataTouchError(
            f"{symbol} @ {date} is after IN_SAMPLE_END={config.IN_SAMPLE_END}; "
            "post-2022 chains may only be opened through the OOS reveal gate."
        )
    cached = _cache_path(symbol, date)
    if cached.exists():
        return validate_chain_schema(pd.read_parquet(cached))

    chain, dropped = _fetch_merged_chain(symbol, date)
    if dropped:
        print(f"{symbol} @ {date}: dropped {dropped} contracts "
              "missing greeks/IV/OI (fail-closed; untradeable anyway)")
    chain.to_parquet(cached)
    return chain


# --------------------------------------------------------------------------
# Blind cache (pre-registration decision doc 2026-07-02, section 4)
# --------------------------------------------------------------------------

BLIND_CACHE_METADATA_KEYS = (
    "symbol", "date", "rows", "columns", "sha256", "path", "already_cached",
)


def _parquet_metadata_without_values(path: Path):
    """(rows, column_names) read from parquet FILE METADATA only -- the value
    pages are never materialized, so an existing blind-cached file can be
    audited without a holdout look even in-process."""
    import pyarrow.parquet as pq

    f = pq.ParquetFile(path)
    return int(f.metadata.num_rows), list(f.schema_arrow.names)


def blind_cache_chain(symbol: str, date: str, *, ledger_dir="ledger") -> dict:
    """Fetch-and-cache a post-IN_SAMPLE_END chain WITHOUT surfacing its values.

    The OOS holdout may be cached during the paid data month so the eventual
    reveal does not need a second subscription -- but caching must not become
    a stealth look. This path therefore: (1) refuses in-sample dates (use
    get_eod_chain); (2) writes the parquet to the same cache location the
    reveal path reads; (3) returns ONLY safe metadata (BLIND_CACHE_METADATA_KEYS
    -- no prices, greeks, or aggregates thereof); (4) appends an auditable
    facts event on EVERY invocation. Reading the cached values remains gated
    by get_eod_chain's OOS guard / the reveal path (allow_oos=True).
    """
    from research import facts

    symbol = _normalize_symbol(symbol)
    date = _normalize_date(date)
    if date <= config.IN_SAMPLE_END:
        raise ValueError(
            f"{symbol} @ {date} is in-sample (<= {config.IN_SAMPLE_END}); "
            "blind caching is only for the OOS holdout -- use get_eod_chain."
        )
    cached = _cache_path(symbol, date)
    already_cached = cached.exists()
    if already_cached:
        rows, columns = _parquet_metadata_without_values(cached)
    else:
        chain, _dropped = _fetch_merged_chain(symbol, date)
        chain.to_parquet(cached)
        rows, columns = len(chain), list(chain.columns)
        del chain  # values must not outlive the write

    sha256 = __import__("hashlib").sha256(cached.read_bytes()).hexdigest()
    meta = {
        "symbol": symbol,
        "date": date,
        "rows": rows,
        "columns": columns,
        "sha256": sha256,
        "path": str(cached),
        "already_cached": already_cached,
    }
    facts.append_fact(
        "BLIND_CACHE "
        f"symbol={symbol} date={date} rows={rows} sha256={sha256} "
        f"already_cached={str(already_cached).lower()} path={cached}",
        base_dir=ledger_dir,
    )
    return meta


def mid_price(bid: float, ask: float) -> float:
    """Quote mid. Fills must be at this OR WORSE -- never the favorable side."""
    return (bid + ask) / 2.0


def passes_liquidity(open_interest: float, bid: float, ask: float) -> bool:
    """A contract must pass before it is tradeable. Check BOTH legs."""
    if open_interest < config.MIN_OPEN_INTEREST:
        return False
    if bid < 0 or ask <= 0 or ask < bid:
        return False
    mid = mid_price(bid, ask)
    if mid <= 0:
        return False
    return ((ask - bid) / mid) <= config.MAX_SPREAD_PCT

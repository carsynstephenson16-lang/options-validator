"""
data/thetadata_adapter.py -- EOD option-chain access with local caching.

PATH C (2026-07-03): fetches through the OFFICIAL `thetadata` Python client,
authenticating with a direct API key (env THETADATA_API_KEY, legacy
THETA_DATA_API_KEY also accepted) against the remote MDDS -- no ThetaTerminal
process, no lumibot launcher, no local port. Two bulk calls per symbol-day
replace the old four-endpoint REST fetch:
  - `option_history_greeks_eod(symbol, expiration="*", start_date, end_date)`
    returns NBBO (bid/ask) + every greek + implied_vol for the WHOLE chain in
    one frame -- live-verified 2026-07-03 (SPY @ 2022-12-30: 7486 rows, 43
    columns). Values are ThetaData-computed (data over local model, per the
    Phase-0 resolution), generated from the 17:15 ET EOD report.
  - `option_history_open_interest(symbol, expiration="*", start_date,
    end_date)` returns open_interest per contract, sourced from the ~06:30 ET
    OPRA report reflecting the PREVIOUS day's close -- i.e. the OI figure
    already known during day D, so joining day-D OI is look-ahead-free.
  Fewer OI rows than greeks rows is expected (not every contract carries OI);
  the inner join below drops those contracts, which is the existing
  fail-closed design (untradeable under the liquidity gate anyway).

Backtests run fully offline from parquet: this adapter supplies the real
greeks/OI/NBBO chain values, and data/pandas_feed.py turns cached chains into
per-contract Lumibot PandasData objects for quote-side fills. ThetaData is not
called from the backtest loop.

Integrity: any date after config.IN_SAMPLE_END is refused unless the caller is
the OOS reveal path (allow_oos=True) -- "just printing a chain" after 2022 is
still a holdout look (spec, Unit 4).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
from datetime import date as Date
from pathlib import Path

import numpy as np
import pandas as pd

import config
from data.atomic_io import (
    atomic_parquet_write,
    atomic_text_write,
    publish_staged_file,
    stage_parquet_write,
)

CACHE_DIR = Path(os.environ.get("OPTIONS_CACHE_DIR", ".cache/chains"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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


class CacheWriteRefused(PermissionError):
    """A non-authoritative checkout attempted to mutate the shared cache."""


class CacheProvenanceError(RuntimeError):
    """Cached bytes and their content-bound acquisition evidence disagree."""


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
# Official thetadata client fetch path (Path C, live-verified 2026-07-03)
# --------------------------------------------------------------------------

_API_KEY_ENV_VARS = ("THETADATA_API_KEY", "THETA_DATA_API_KEY")

_client_singleton = None  # module-cached ThetaClient; constructed lazily
_client_local = threading.local()


def _resolve_api_key() -> str:
    """Load .env, then resolve the ThetaData API key from either env var name
    (THETADATA_API_KEY preferred; THETA_DATA_API_KEY accepted for the legacy
    name already present in this repo's .env). Never includes any value in
    the error message -- only the variable NAMES are named."""
    from dotenv import load_dotenv

    load_dotenv()
    for name in _API_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    raise RuntimeError(
        "No ThetaData API key found: set one of "
        f"{', '.join(_API_KEY_ENV_VARS)} in .env."
    )


def _client():
    """Module-cached ThetaClient, constructed lazily on first real fetch so
    cache hits and offline tests never authenticate. `ThetaClient.__init__`
    performs a synchronous auth request against the remote MDDS -- importing
    the `thetadata` package here (not at module load) keeps this module's
    import cheap and network-free."""
    global _client_singleton
    client = getattr(_client_local, "client", None)
    if client is None and threading.current_thread() is threading.main_thread():
        client = _client_singleton
    if client is None:
        from thetadata import ThetaClient

        client = ThetaClient(api_key=_resolve_api_key(), dataframe_type="pandas")
        # Fail fast if the authenticated account has no options entitlement --
        # every data call below would otherwise fail one at a time. Default
        # True on a missing attribute so a future client-library change never
        # false-blocks a working account.
        if not getattr(client, "options_subscription", True):
            raise RuntimeError(
                "ThetaData account has no options subscription entitlement -- "
                "data calls would fail; check the account tier."
            )
        _client_local.client = client
        if threading.current_thread() is threading.main_thread():
            _client_singleton = client
    return client


def _reset_client() -> None:
    """Drop the cached ThetaClient so the next fetch re-authenticates on a
    fresh channel. Recovery step after a transport-level gRPC failure --
    observed live 2026-07-03: UNAVAILABLE 'Stream removed (Socket closed)'
    after ~3,890 sequential calls on one channel."""
    global _client_singleton
    if hasattr(_client_local, "client"):
        del _client_local.client
    if threading.current_thread() is threading.main_thread():
        _client_singleton = None


def _fetch_raw(symbol: str, date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two bulk calls for one symbol-day: the whole chain's greeks+NBBO+IV,
    and the whole chain's open interest. expiration="*" per call (per the
    client's own docstring, any expiration=* request is scoped to one day).

    EMPTY-DAY / GAP CONTRACT: a non-trading day, an EOD gap, or a day outside
    the subscription's history window must surface as RuntimeError whose
    message contains "returned no rows" (data/cache_runner.py depends on this
    exact token to distinguish a gap -- skip and log -- from a real failure).
    The installed thetadata.errors defines exactly two exceptions:
    AuthenticationError and NoDataFoundError. Every data method (see
    client.py) maps ONLY grpc.StatusCode.NOT_FOUND to NoDataFoundError, so an
    empty day is normally an EXCEPTION, not an empty frame -- we catch that
    exact type and re-raise with the required token. The empty-frame check is
    kept too, belt-and-braces, in case a future client version returns an
    empty frame instead of raising. Everything else -- AuthenticationError,
    or a raw grpc.RpcError for entitlement (PERMISSION_DENIED), rate-limit
    (RESOURCE_EXHAUSTED), or session (UNAUTHENTICATED) failures -- is not a
    gap and must propagate untouched.
    """
    from thetadata.errors import NoDataFoundError

    fetch_date = Date.fromisoformat(date)
    client = _client()

    try:
        greeks = client.option_history_greeks_eod(
            symbol=symbol, expiration="*", start_date=fetch_date, end_date=fetch_date,
        )
    except NoDataFoundError:
        greeks = None
    if greeks is None or greeks.empty:
        raise RuntimeError(
            f"ThetaData greeks_eod returned no rows for {symbol} @ {date}. "
            "Likely a non-trading day, an EOD gap, or outside the "
            "subscription window -- skip the day (log it), do not substitute."
        )

    try:
        oi = client.option_history_open_interest(
            symbol=symbol, expiration="*", start_date=fetch_date, end_date=fetch_date,
        )
    except NoDataFoundError:
        oi = None
    if oi is None or oi.empty:
        raise RuntimeError(
            f"ThetaData open_interest returned no rows for {symbol} @ {date}. "
            "Likely a non-trading day, an EOD gap, or outside the "
            "subscription window -- skip the day (log it), do not substitute."
        )

    return greeks, oi


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


def _merge_chain_frames(greeks: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    """Inner-join the two per-contract frames into CHAIN_COLUMNS.

    Inner join is deliberate fail-closed behavior: a contract missing quotes,
    greeks, or open interest is untradeable under the liquidity/delta rules, so
    it is dropped here rather than passed downstream with NaNs. The caller
    logs the drop count."""
    greeks = _normalize_contract_keys(greeks, "greeks")
    oi = _normalize_contract_keys(oi, "open_interest")

    bid_col = _pick_col(greeks, ("bid", "close_bid", "bid_price"), "greeks")
    ask_col = _pick_col(greeks, ("ask", "close_ask", "ask_price"), "greeks")
    iv_col = _pick_col(greeks, ("implied_vol", "implied_volatility", "iv"), "greeks")
    oi_col = _pick_col(oi, ("open_interest", "oi"), "open_interest")
    for greek in ("delta", "gamma", "theta", "vega"):
        _pick_col(greeks, (greek,), "greeks")

    merged = (
        greeks[_KEY_COLS + [bid_col, ask_col, "delta", "gamma", "theta", "vega", iv_col]]
        .rename(columns={bid_col: "bid", ask_col: "ask", iv_col: "iv"})
        .merge(oi[_KEY_COLS + [oi_col]].rename(columns={oi_col: "open_interest"}),
               on=_KEY_COLS, how="inner")
    )
    return merged[CHAIN_COLUMNS].reset_index(drop=True)


def _fetch_merged_chain(symbol: str, date: str):
    """Fetch the two bulk frames and merge into a validated chain.
    Returns (chain, dropped_count). Callers decide how the drop count is
    reported -- the blind-cache path must not print anything."""
    greeks, oi = _fetch_raw(symbol, date)

    normalized_greeks = _normalize_contract_keys(greeks, "greeks")
    chain = _merge_chain_frames(greeks, oi)
    if chain.empty:
        # Observed live (QQQ @ 2023-12-27): both reports populated but sharing
        # ZERO contract keys -- greeks strikes came back dividend-adjusted by
        # -0.22 while OI carried the round listing strikes. Do NOT repair the
        # keys (rounding could mis-join genuinely adjusted contracts); an
        # empty intersection is an unusable day. Same guardrail as any EOD
        # gap: skip the day, log it, never write a zero-row cache file.
        raise RuntimeError(
            f"ThetaData merged chain returned no rows for {symbol} @ {date}: "
            "the greeks and open-interest reports share no contract keys "
            "(adjustment mismatch or report glitch) -- skip the day (log it), "
            "do not substitute."
        )
    validate_chain_schema(chain)
    return chain, len(normalized_greeks) - len(chain)


def get_eod_chain(symbol: str, date: str, *, allow_oos: bool = False) -> pd.DataFrame:
    """Return the validated EOD option chain for `symbol` on `date` (YYYY-MM-DD),
    fetched via the official thetadata client on cache miss and cached as
    parquet.

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
    if date > config.IN_SAMPLE_END:
        raise FileNotFoundError(
            f"no cached OOS chain for {symbol} @ {date}; OOS consumers are "
            "cache-only and acquisition must use blind_cache_chain from the "
            "authoritative ops publisher"
        )

    _require_cache_publisher()
    chain, dropped = _fetch_merged_chain(symbol, date)
    if dropped:
        print(f"{symbol} @ {date}: dropped {dropped} contracts "
              "missing open interest (fail-closed; untradeable anyway)")
    atomic_parquet_write(chain, cached)
    return chain


def load_cached_chain(symbol: str, date: str, *, allow_oos: bool = False,
                      cache_dir: Path | None = None) -> pd.DataFrame:
    """Cache-ONLY EOD chain read: return the validated parquet if it already
    exists locally, else raise FileNotFoundError. NEVER constructs the
    ThetaData client and NEVER fetches -- the H9 study's "zero new data spend"
    hard property (spec §1: a missing input is excluded/halts, never fetched)
    depends on this path never touching the network. On a cache miss the H9
    census codes the event `missing_entry_chain` and the study treats the
    session as a data gap; neither ever spends.

    The IN_SAMPLE_END / allow_oos holdout guard still applies, since reading a
    cached post-2022 chain outside the reveal gate is a holdout look.

    `cache_dir` overrides the global cache directory so callers that take an
    injectable chain_dir (the H9 census) stay coherent: presence checks and
    content reads must resolve against the SAME directory, and tests can
    isolate against a temp dir instead of depending on real-cache absence.
    """
    symbol = _normalize_symbol(symbol)
    date = _normalize_date(date)
    if date > config.IN_SAMPLE_END and not allow_oos:
        raise OOSDataTouchError(
            f"{symbol} @ {date} is after IN_SAMPLE_END={config.IN_SAMPLE_END}; "
            "post-2022 chains may only be opened through the OOS reveal gate."
        )
    cached = (Path(cache_dir) / f"{symbol}_{date}.parquet"
              if cache_dir is not None else _cache_path(symbol, date))
    if cached.exists():
        return validate_chain_schema(pd.read_parquet(cached))
    raise FileNotFoundError(
        f"no cached chain for {symbol} @ {date}; this reader is cache-only and "
        "never fetches (H9 zero-new-data-spend guarantee)."
    )


# --------------------------------------------------------------------------
# Blind cache (pre-registration decision doc 2026-07-02, section 4)
# --------------------------------------------------------------------------

BLIND_CACHE_METADATA_KEYS = (
    "symbol", "date", "rows", "columns", "sha256", "path", "already_cached",
    "attestation_status", "identity",
)


def _parquet_metadata_without_values(path: Path):
    """(rows, column_names) read from parquet FILE METADATA only -- the value
    pages are never materialized, so an existing blind-cached file can be
    audited without a holdout look even in-process."""
    import pyarrow.parquet as pq

    f = pq.ParquetFile(path)
    return int(f.metadata.num_rows), list(f.schema_arrow.names)


def _require_cache_publisher() -> None:
    """Require the single authoritative cache writer.

    The environment role is necessary but not sufficient: writes are allowed
    only from the repository root on a main checkout exactly aligned with
    origin/main. Tests replace this guard explicitly and remain isolated in
    temporary cache/ledger directories.
    """
    if os.environ.get("OPTIONS_VALIDATOR_CACHE_ROLE", "consumer") != "publisher":
        raise CacheWriteRefused(
            "cache mutation refused: set OPTIONS_VALIDATOR_CACHE_ROLE=publisher "
            "only in the authoritative ops checkout"
        )

    def git(*args: str) -> str:
        result = subprocess.run(
            ("git", *args),
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise CacheWriteRefused(
                f"cache mutation refused: git {' '.join(args)} failed"
            )
        return result.stdout.strip()

    root = Path(git("rev-parse", "--show-toplevel")).resolve()
    if Path.cwd().resolve() != root:
        raise CacheWriteRefused(
            f"cache mutation refused: run from repository root {root}"
        )
    if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        raise CacheWriteRefused(
            "cache mutation refused: authoritative publisher must be on main"
        )
    if git("rev-parse", "HEAD") != git("rev-parse", "origin/main"):
        raise CacheWriteRefused(
            "cache mutation refused: main must exactly match origin/main"
        )


def _attestation_path(symbol: str, date: str) -> Path:
    return CACHE_DIR / ".attestations" / f"{symbol}_{date}.json"


def _write_attestation(
    meta: dict,
    *,
    status: str,
    staged_path: Path | None = None,
) -> None:
    payload = {
        "schema": "blind-cache-attestation/v1",
        "status": status,
        **{key: meta[key] for key in (
            "symbol", "date", "rows", "columns", "sha256", "path", "identity"
        )},
    }
    if staged_path is not None:
        payload["staged_path"] = str(staged_path)
    atomic_text_write(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        _attestation_path(meta["symbol"], meta["date"]),
    )


def _read_attestation(symbol: str, date: str) -> dict | None:
    path = _attestation_path(symbol, date)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CacheProvenanceError(
            f"malformed blind-cache attestation: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise CacheProvenanceError(
            f"malformed blind-cache attestation: {path}"
        )
    return payload


def _pending_attestation_matches(meta: dict) -> bool:
    payload = _read_attestation(meta["symbol"], meta["date"])
    if payload is None:
        return False
    expected = {
        "schema": "blind-cache-attestation/v1",
        **{key: meta[key] for key in (
            "symbol", "date", "rows", "columns", "sha256", "path", "identity"
        )},
    }
    if payload.get("status") == "PENDING_FACT":
        return payload == {"status": "PENDING_FACT", **expected}
    if payload.get("status") == "PENDING_FILE":
        staged_path = payload.get("staged_path")
        if not isinstance(staged_path, str) or not staged_path:
            return False
        return payload == {
            "status": "PENDING_FILE",
            **expected,
            "staged_path": staged_path,
        }
    return False


def _recover_staged_cache(symbol: str, date: str, cached: Path) -> bool:
    """Publish bytes durably staged by an interrupted authoritative run."""
    payload = _read_attestation(symbol, date)
    if payload is None or payload.get("status") != "PENDING_FILE":
        return False
    staged_value = payload.get("staged_path")
    if not isinstance(staged_value, str) or not staged_value:
        raise CacheProvenanceError(
            f"invalid staged path in blind-cache attestation for {symbol} @ {date}"
        )
    staged = Path(staged_value)
    if (
        staged.parent.resolve() != cached.parent.resolve()
        or not staged.name.startswith(f".{cached.name}.")
        or not staged.name.endswith(".tmp")
    ):
        raise CacheProvenanceError(
            f"non-canonical staged path in blind-cache attestation: {staged}"
        )
    if not staged.is_file():
        raise CacheProvenanceError(
            f"recorded staged cache bytes are missing for {symbol} @ {date}: "
            f"{staged}"
        )
    rows, columns = _parquet_metadata_without_values(staged)
    sha256 = hashlib.sha256(staged.read_bytes()).hexdigest()
    identity = f"{symbol}:{date}:{sha256}"
    expected = {
        "schema": "blind-cache-attestation/v1",
        "status": "PENDING_FILE",
        "symbol": symbol,
        "date": date,
        "rows": rows,
        "columns": columns,
        "sha256": sha256,
        "path": str(cached),
        "identity": identity,
        "staged_path": str(staged),
    }
    if payload != expected:
        raise CacheProvenanceError(
            f"staged cache bytes do not match attestation for {symbol} @ {date}"
        )
    _require_cache_publisher()
    publish_staged_file(staged, cached)
    _write_attestation(expected, status="PENDING_FACT")
    return True


def blind_cache_chain(
    symbol: str,
    date: str,
    *,
    ledger_dir="ledger",
    approved_sha256: str | None = None,
) -> dict:
    """Fetch-and-cache a post-IN_SAMPLE_END chain WITHOUT surfacing its values.

    The OOS holdout may be cached during the paid data month so the eventual
    reveal does not need a second subscription -- but caching must not become
    a stealth look. This path therefore: (1) refuses in-sample dates (use
    get_eod_chain); (2) writes the parquet to the same cache location the
    reveal path reads; (3) returns ONLY safe metadata (BLIND_CACHE_METADATA_KEYS
    -- no prices, greeks, or aggregates thereof); (4) idempotently binds the
    bytes to an auditable facts event. Existing bytes without a matching fact
    are repaired only from a durable pending attestation or an explicitly
    approved incident hash. Reading cached values remains gated by
    get_eod_chain's OOS guard / the reveal path (allow_oos=True).
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
    if not already_cached and _recover_staged_cache(symbol, date, cached):
        already_cached = True
    if already_cached:
        rows, columns = _parquet_metadata_without_values(cached)
    else:
        _require_cache_publisher()
        chain, _dropped = _fetch_merged_chain(symbol, date)
        staged = stage_parquet_write(chain, cached)
        rows, columns = _parquet_metadata_without_values(staged)
        sha256 = hashlib.sha256(staged.read_bytes()).hexdigest()
        staged_meta = {
            "symbol": symbol,
            "date": date,
            "rows": rows,
            "columns": columns,
            "sha256": sha256,
            "path": str(cached),
            "identity": f"{symbol}:{date}:{sha256}",
        }
        try:
            _write_attestation(
                staged_meta,
                status="PENDING_FILE",
                staged_path=staged,
            )
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
        publish_staged_file(staged, cached)
        _write_attestation(staged_meta, status="PENDING_FACT")
        del chain  # values must not outlive the write

    sha256 = hashlib.sha256(cached.read_bytes()).hexdigest()
    identity = f"{symbol}:{date}:{sha256}"
    meta = {
        "symbol": symbol,
        "date": date,
        "rows": rows,
        "columns": columns,
        "sha256": sha256,
        "path": str(cached),
        "already_cached": already_cached,
        "attestation_status": "",
        "identity": identity,
    }

    from data.cache_provenance import load_blind_cache_facts

    fact = load_blind_cache_facts(
        Path(ledger_dir) / "facts.log"
    ).get((symbol, date))
    if fact is not None:
        if fact["sha256"] != sha256:
            raise CacheProvenanceError(
                f"BLIND_CACHE sha256 mismatch for {symbol} @ {date}: "
                f"fact={fact['sha256']} file={sha256}"
            )
        meta["attestation_status"] = "VERIFIED_NOOP"
        return meta

    approved = approved_sha256 is not None
    if approved and approved_sha256 != sha256:
        raise CacheProvenanceError(
            f"approved repair sha256 mismatch for {symbol} @ {date}: "
            f"approved={approved_sha256} file={sha256}"
        )
    recoverable_pending = already_cached and _pending_attestation_matches(meta)
    if already_cached and not approved and not recoverable_pending:
        raise CacheProvenanceError(
            f"orphaned cache file for {symbol} @ {date}: no matching "
            "BLIND_CACHE fact, durable pending attestation, or approved "
            "incident hash"
        )

    _require_cache_publisher()
    _write_attestation(meta, status="PENDING_FACT")
    facts.append_fact(
        "BLIND_CACHE "
        f"symbol={symbol} date={date} rows={rows} sha256={sha256} "
        f"already_cached={str(already_cached).lower()} path={cached}",
        base_dir=ledger_dir,
    )
    meta["attestation_status"] = (
        "REPAIRED_ATTESTATION" if already_cached else "FETCHED_ATTESTED"
    )
    _write_attestation(meta, status="COMPLETE")
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

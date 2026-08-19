"""options_researcher/live_quotes.py -- live intraday PREVIEW adapter.

READ-ONLY, PREVIEW-ONLY. This module never writes positions, the ledger, or
any report other than its own schema-probe record; it never places orders.
There is no H5 entry verdict anywhere in this repo any more:
ledger seq 29 clause 1 (2026-08-17) RETIRED H5_ENTRY_TRIGGER_PREREG and
amendment v2, and options_researcher.entry_watch is now a completed-session
OBSERVER with no FIRE path. Everything produced here is a
"LIVE PREVIEW (awaiting close)" lane: it may prompt a fresh manual review,
and it can never fire a trigger -- because no trigger exists to fire.

Design: docs/superpowers/specs/2026-07-16-live-dashboard-design.md.

Schema gate: market-data providers return server-defined response columns, so
a one-shot probe (run during a regular session via
`python -m options_researcher.live_quotes --probe`) records the real response
columns per endpoint. probe_ok() refuses the live lane when the probe is
missing, stale (config.LIVE_PROBE_MAX_AGE_DAYS), from a different provider or
installed client version, or shows a required endpoint failing.
A stock-entitlement denial does NOT fail the probe -- it selects the
put-call-parity fallback spot for trigger names only.
"""
from __future__ import annotations

import inspect
import json
import math
import os
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config
from data.chain_policy import (
    _normalize_contract_keys,
    _pick_col,
    mid_price,
    passes_liquidity,
)
from data.underlying_closes import parity_spot_from_chain
from options_researcher import features
from options_researcher.chains import atm_row, is_monthly, nearest_monthly
from options_researcher.studies.long_call_carry import _leaps_candidate

PROBE_DIR = "reports/live_probe"
PROBE_SYMBOL = "VST"  # H5 trigger name used for the option-endpoint probes

NY_TZ = "America/New_York"
# NYSE regular session bounds (Official-source: NYSE trading hours). A
# presentation/plumbing gate only -- it decides when live fetches may run,
# never what any strategy does.
SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)

# Monthly ATM band single-sourced from chains.nearest_monthly's defaults
# (15..60 DTE -- the same definition features.py uses).
_NM_PARAMS = inspect.signature(nearest_monthly).parameters
MONTHLY_MIN_DTE = _NM_PARAMS["min_dte"].default
MONTHLY_MAX_DTE = _NM_PARAMS["max_dte"].default
# Same nearest-365 target as studies.long_call_carry._leaps_candidate; the
# band itself comes from config.H4_THESIS_DTE_BAND.
LEAPS_TARGET_DTE = 365

MET, UNMET, UNKNOWN = "MET", "UNMET", "UNKNOWN"
PREVIEW_LANE = "LIVE PREVIEW (awaiting close)"

_TS_CANDIDATES = ("timestamp", "quote_timestamp", "time", "created", "last_trade")
_BID_CANDIDATES = ("bid", "close_bid", "bid_price")
_ASK_CANDIDATES = ("ask", "close_ask", "ask_price")
_IV_CANDIDATES = ("implied_vol", "implied_volatility", "iv")
_OI_CANDIDATES = ("open_interest", "oi")
_SYMBOL_CANDIDATES = ("symbol", "root", "ticker", "underlying")
_EXP_LIST_CANDIDATES = ("expiration", "expirations", "expiry", "date")

REQUIRED_PROBE_ENDPOINTS = (
    "option_list_expirations",
    "option_snapshot_quote",
    "option_snapshot_greeks_all",
    "option_snapshot_open_interest",
)
_FUTURE_CLOCK_TOLERANCE_SECONDS = 5.0


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def in_regular_session(now_ny: datetime) -> bool:
    """NY weekday and 09:30 <= t < 16:00. `now_ny` must already be NY-local."""
    return now_ny.weekday() < 5 and SESSION_OPEN <= now_ny.time() < SESSION_CLOSE


def resolve_expiries(expirations: list[date], today: date) -> dict:
    """{"monthly": earliest MONTHLY expiry in the 15-60 DTE band or None,
    "leaps": expiry inside config.H4_THESIS_DTE_BAND nearest 365 DTE or None}
    from a plain list of dates."""
    monthly = None
    for exp in sorted(expirations):
        dte = (exp - today).days
        if MONTHLY_MIN_DTE <= dte <= MONTHLY_MAX_DTE and is_monthly(exp):
            monthly = exp
            break
    lo, hi = config.H4_THESIS_DTE_BAND
    band = [e for e in expirations if lo <= (e - today).days <= hi]
    leaps = (min(band, key=lambda e: abs((e - today).days - LEAPS_TARGET_DTE))
             if band else None)
    return {"monthly": monthly, "leaps": leaps}


def iv_rank_preview(history_atm_iv: list[float], live_iv: float) -> float:
    """Inclusive-rank percentile of `live_iv` against the trailing EOD atm_iv
    history, mirroring options_researcher.features EXACTLY: live_iv is the
    newest appended observation, the window is the trailing <=252 FINITE
    observations (features.PCT_WINDOW), NaN unless >=126 finite obs
    (features.PCT_MIN_OBS), rank = mean(window <= live_iv)."""
    vals = [float(v) if v is not None else float("nan") for v in history_atm_iv]
    v = float(live_iv) if live_iv is not None else float("nan")
    vals.append(v)
    window = [x for x in vals[-features.PCT_WINDOW:] if np.isfinite(x)]
    if not np.isfinite(v) or len(window) < features.PCT_MIN_OBS:
        return float("nan")
    return float(np.mean(np.asarray(window) <= v))


def quote_is_fresh(quote_ts, now, max_age_seconds) -> bool:
    """tz-aware freshness compare. None or a tz-naive timestamp never passes
    (fail closed): an unlabeled clock cannot certify freshness."""
    if quote_ts is None:
        return False
    ts = pd.Timestamp(quote_ts)
    if pd.isna(ts) or ts.tzinfo is None:
        return False
    now_ts = pd.Timestamp(now)
    if pd.isna(now_ts) or now_ts.tzinfo is None:
        return False
    age_seconds = (now_ts - ts).total_seconds()
    return (
        -_FUTURE_CLOCK_TOLERANCE_SECONDS
        <= age_seconds
        <= float(max_age_seconds)
    )


def _finite_or_none(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _iso_or_none(ts):
    if ts is None:
        return None
    t = pd.Timestamp(ts)
    return None if pd.isna(t) else t.isoformat()


def build_symbol_preview(symbol: str, *, spot, spot_source, spot_ts,
                         trigger_level, atm_iv, iv_history, leaps_row,
                         oi, oi_asof, now) -> dict:
    """Pure assembly of one symbol's LIVE-PREVIEW payload row from injected
    inputs. Gates read MET/UNMET/UNKNOWN and fail closed: any missing input
    is UNKNOWN, never assumed. `armed` mirrors the price gate only -- it is a
    preview flag, not a verdict. This payload NEVER contains a verdict."""
    gates: dict = {}
    armed = False
    spot_f = _finite_or_none(spot)
    if trigger_level is not None:
        if spot_f is None:
            gates["price"] = UNKNOWN
        elif spot_f <= float(trigger_level):
            gates["price"] = MET
            armed = True
        else:
            gates["price"] = UNMET

    rank = iv_rank_preview(iv_history if iv_history is not None else [], atm_iv)
    if np.isfinite(rank):
        gates["ivr"] = MET if rank <= config.H5_ENTRY_IVR_MAX else UNMET
    else:
        gates["ivr"] = UNKNOWN

    bid = ask = None
    if leaps_row is not None:
        bid = _finite_or_none(leaps_row["bid"])
        ask = _finite_or_none(leaps_row["ask"])
    oi_f = _finite_or_none(oi)
    if oi_f is None or bid is None or ask is None:
        gates["liquidity"] = UNKNOWN  # OI absent => UNKNOWN, never assumed
    else:
        gates["liquidity"] = MET if passes_liquidity(oi_f, bid, ask) else UNMET

    leaps = None
    if leaps_row is not None:
        if "exp_date" in leaps_row.index:
            exp_iso = leaps_row["exp_date"].isoformat()
        else:
            exp_iso = pd.Timestamp(leaps_row["expiration"]).date().isoformat()
        leaps = {"expiration": exp_iso,
                 "strike": _finite_or_none(leaps_row["strike"]),
                 "delta": _finite_or_none(leaps_row.get("delta")),
                 "bid": bid, "ask": ask}

    return {
        "symbol": symbol,
        "status": "ok",
        "lane": PREVIEW_LANE,
        "as_of_utc": _iso_or_none(now),
        "spot": spot_f,
        "spot_source": spot_source,
        "spot_ts": _iso_or_none(spot_ts),
        "trigger": float(trigger_level) if trigger_level is not None else None,
        "armed": bool(armed),
        "atm_iv": _finite_or_none(atm_iv),
        "iv_rank_preview": _finite_or_none(rank),
        "gates": gates,
        "open_interest": oi_f,
        # Never label an OI figure that isn't there (fail closed).
        "oi_label": (f"OI observed {oi_asof} "
                     "(provider update cadence/as-of unverified)"
                     if oi_asof and oi_f is not None else None),
        "leaps": leaps,
    }


# ---------------------------------------------------------------------------
# Probe machinery (the schema gate)
# ---------------------------------------------------------------------------

def _installed_thetadata_version() -> str:
    import importlib.metadata

    return importlib.metadata.version("thetadata")


def _configured_provider() -> str:
    """Configured live-preview provider; historical cache paths are unchanged."""
    from dotenv import load_dotenv

    load_dotenv()
    raw_provider = os.environ.get("LIVE_MARKET_DATA_PROVIDER")
    if raw_provider is None or not raw_provider.strip():
        raise RuntimeError(
            "LIVE_MARKET_DATA_PROVIDER must be set explicitly to 'schwab'; "
            "ThetaData acquisition is disabled and no fallback is permitted."
        )
    provider = raw_provider.strip().lower()
    if provider not in {"thetadata", "schwab"}:
        raise RuntimeError(
            "LIVE_MARKET_DATA_PROVIDER must be 'thetadata' or 'schwab'."
        )
    if provider == "thetadata":
        from data import provider_policy

        provider_policy.require_thetadata_acquisition(
            "ThetaData live-preview selection"
        )
    return provider


def _installed_provider_version(provider: str) -> str:
    if provider == "thetadata":
        return _installed_thetadata_version()
    import importlib.metadata

    return importlib.metadata.version("schwab-py")


def _live_client():
    provider = _configured_provider()
    if provider == "schwab":
        from data.schwab_adapter import _client
    else:
        from data.thetadata_adapter import _client

    return _client()


def _exc_note(exc: BaseException) -> str:
    # OAuth/HTTP exception messages can contain request details. Persist only
    # the exception class in dashboard/probe artifacts.
    return type(exc).__name__


def _coerce_expiration(v) -> date:
    """A datetime.date from a server-formatted expiration value (ISO string,
    date/Timestamp, or legacy YYYYMMDD int)."""
    if isinstance(v, (int, np.integer)):
        s = str(int(v))
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return pd.Timestamp(v).date()


def _expirations_from_frame(frame: pd.DataFrame) -> list[date]:
    """Sorted expiration dates from an option_list_expirations response.
    Column resolved by candidate name, or positionally when the frame has
    exactly one column; anything else raises naming the columns seen."""
    cols = [str(c).strip().lower() for c in frame.columns]
    named = [c for c in cols if c in _EXP_LIST_CANDIDATES]
    if named:
        idx = cols.index(named[0])
    elif len(cols) == 1:
        idx = 0
    else:
        raise ValueError(
            f"expirations list: none of {list(_EXP_LIST_CANDIDATES)} present; "
            f"got columns {sorted(cols)}")
    series = frame.iloc[:, idx]
    return sorted({_coerce_expiration(v) for v in series if pd.notna(v)})


def _endpoint_result(fn, *args, **kwargs):
    """(record, frame): record = {"ok", "columns", "error"}; frame is None on
    failure. Never lets a single endpoint failure crash the probe."""
    try:
        frame = fn(*args, **kwargs)
    except Exception as exc:
        return {"ok": False, "columns": None, "error": _exc_note(exc)}, None
    cols = [str(c) for c in getattr(frame, "columns", [])]
    return {"ok": True, "columns": cols, "error": None}, frame


def run_probe(client=None, now_ny=None, out_dir: str = PROBE_DIR) -> dict:
    """One-shot live schema probe: record the real response columns of every
    endpoint the live lane uses, during a regular session only. Writes
    out_dir/<ny_date>.json and returns the dict. A stock-entitlement denial
    is recorded, not fatal (it selects parity-fallback spot mode)."""
    if now_ny is None:
        now_ny = datetime.now(ZoneInfo(NY_TZ))
    if not in_regular_session(now_ny):
        raise RuntimeError(
            "run_probe refused: outside the NY regular session (probe must "
            "observe live snapshot schemas, not closed-market responses)")
    if client is None:
        client = _live_client()
    if hasattr(client, "regular_session_state"):
        provider_session = client.regular_session_state(now_ny)
        if not provider_session.get("open"):
            raise RuntimeError(
                "run_probe refused: Schwab market-hours schedule does not show "
                "both equity and equity-option regular sessions open"
            )
    ny_date = now_ny.date()
    # getattr(obj, name, default) evaluates `default` EAGERLY -- Python
    # builds the whole call before dispatching it, so _configured_provider()
    # (a hard RuntimeError when LIVE_MARKET_DATA_PROVIDER is unset) used to
    # run even when `client` already supplies provider_name, breaking every
    # offline test that injects a fake/stub client. Resolve lazily instead:
    # only call the fallback when the attribute is genuinely absent. A real
    # client missing the label still raises the identical RuntimeError.
    provider = getattr(client, "provider_name", None)
    if provider is None:
        provider = _configured_provider()
    provider_version = getattr(client, "provider_version", None)
    if provider_version is None:
        provider_version = _installed_provider_version(provider)

    endpoints: dict = {}
    stock_res, _ = _endpoint_result(
        client.stock_snapshot_quote, list(config.UNIVERSE))
    endpoints["stock_snapshot_quote"] = stock_res

    exp_res, exp_frame = _endpoint_result(
        client.option_list_expirations, PROBE_SYMBOL)
    endpoints["option_list_expirations"] = exp_res
    monthly = None
    if exp_frame is not None:
        try:
            monthly = resolve_expiries(
                _expirations_from_frame(exp_frame), ny_date)["monthly"]
        except Exception as exc:
            exp_res["ok"] = False
            exp_res["error"] = _exc_note(exc)

    for name in ("option_snapshot_quote", "option_snapshot_greeks_all",
                 "option_snapshot_open_interest"):
        if monthly is None:
            endpoints[name] = {"ok": False, "columns": None,
                               "error": "no monthly expiry resolvable for probe"}
            continue
        res, _frame = _endpoint_result(
            getattr(client, name), PROBE_SYMBOL, expiration=monthly)
        endpoints[name] = res

    probe = {
        "probed_at_utc": now_ny.astimezone(timezone.utc).isoformat(),
        "ny_date": ny_date.isoformat(),
        "provider": provider,
        "provider_version": provider_version,
        "stock_entitled": bool(stock_res["ok"]),
        "probe_symbol": PROBE_SYMBOL,
        "monthly_expiration": monthly.isoformat() if monthly else None,
        "endpoints": endpoints,
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{ny_date.isoformat()}.json"), "w") as fh:
        json.dump(probe, fh, indent=2)
    return probe


def load_latest_probe(dir: str = PROBE_DIR) -> dict | None:
    try:
        names = sorted(n for n in os.listdir(dir) if n.endswith(".json"))
    except FileNotFoundError:
        return None
    if not names:
        return None
    with open(os.path.join(dir, names[-1])) as fh:
        return json.load(fh)


def probe_ok(probe: dict | None, now_utc) -> tuple[bool, str]:
    """Gate the live lane on the recorded schema probe. False when the probe
    is missing, from a different configured provider or installed version, older than
    config.LIVE_PROBE_MAX_AGE_DAYS, or a required endpoint failed. A stock
    entitlement denial does NOT fail the probe (parity-fallback mode)."""
    if probe is None:
        return False, ("no schema probe recorded -- run "
                       "`python -m options_researcher.live_quotes --probe` "
                       "during a regular session")
    configured = _configured_provider()
    recorded_provider = probe.get("provider", "thetadata")
    if recorded_provider != configured:
        return False, (
            f"probe recorded provider={recorded_provider} but configured "
            f"provider={configured} -- re-probe before trusting columns"
        )
    installed = _installed_provider_version(configured)
    recorded = probe.get(
        "provider_version",
        probe.get("thetadata_version"),  # backward-compatible old probes
    )
    if recorded != installed:
        return False, (
            f"probe recorded {configured}=={recorded} but {installed} is "
            "installed -- re-probe before trusting columns"
        )
    try:
        age = pd.Timestamp(now_utc) - pd.Timestamp(probe.get("probed_at_utc"))
    except (TypeError, ValueError):
        return False, "probe probed_at_utc missing or unusable"
    if pd.isna(age) or age > pd.Timedelta(days=config.LIVE_PROBE_MAX_AGE_DAYS):
        return False, (f"probe older than LIVE_PROBE_MAX_AGE_DAYS="
                       f"{config.LIVE_PROBE_MAX_AGE_DAYS} -- re-probe")
    endpoints = probe.get("endpoints") or {}
    for name in REQUIRED_PROBE_ENDPOINTS:
        rec = endpoints.get(name) or {}
        if not rec.get("ok"):
            return False, f"probe endpoint {name} not ok: {rec.get('error')}"
    if not probe.get("stock_entitled"):
        return True, ("ok (no stock entitlement -- parity-fallback spot for "
                      "trigger names only)")
    return True, "ok"


# ---------------------------------------------------------------------------
# Fetch layer (thin; exercised only via injected fakes in tests)
# ---------------------------------------------------------------------------

# Expirations are memoized by NY date. ThetaData OI retains its established
# once-per-day memo. Schwab OI is read from each new live chain snapshot because
# Schwab's intraday update cadence is undocumented; the adapter's 25-second
# chain cache still reuses one response across Greeks and OI within a refresh.
_EXPIRATIONS_MEMO: dict[tuple[str, str], list[date]] = {}
_OI_MEMO: dict[tuple[str, str, str], tuple[dict | None, str | None]] = {}


def _reset_memos() -> None:
    _EXPIRATIONS_MEMO.clear()
    _OI_MEMO.clear()


def _expirations(client, symbol: str, ny_iso: str) -> list[date]:
    key = (symbol, ny_iso)
    if key not in _EXPIRATIONS_MEMO:
        frame = client.option_list_expirations(symbol)
        _EXPIRATIONS_MEMO[key] = _expirations_from_frame(frame)
    return _EXPIRATIONS_MEMO[key]


def _open_interest(client, symbol: str, expiration: date, ny_iso: str):
    """Return OI plus observation date; only ThetaData is memoized by day."""
    key = (symbol, expiration.isoformat(), ny_iso)
    if getattr(client, "provider_name", "") == "schwab":
        try:
            frame = client.option_snapshot_open_interest(
                symbol, expiration=expiration
            )
            return _oi_map(frame, f"{symbol} open_interest"), ny_iso
        except Exception:
            return None, None
    if key not in _OI_MEMO:
        try:
            frame = client.option_snapshot_open_interest(
                symbol, expiration=expiration)
            _OI_MEMO[key] = (_oi_map(frame, f"{symbol} open_interest"), ny_iso)
        except Exception:
            _OI_MEMO[key] = (None, None)  # fail closed; liquidity reads UNKNOWN
    return _OI_MEMO[key]


def _oi_map(frame: pd.DataFrame, ctx: str) -> dict:
    norm = _normalize_contract_keys(frame, ctx)
    col = _pick_col(norm, _OI_CANDIDATES, ctx)
    vals = pd.to_numeric(norm[col], errors="coerce")
    out: dict = {}
    for exp, strike, right, v in zip(norm["expiration"], norm["strike"],
                                     norm["right"], vals):
        if pd.notna(v) and pd.notna(strike):
            out[(_coerce_expiration(exp).isoformat(), float(strike), right)] = float(v)
    return out


def _assemble_chain_frame(frame: pd.DataFrame, ctx: str, *,
                          with_greeks: bool = False) -> pd.DataFrame:
    """Chain-like frame (expiration/strike/right/bid/ask [+iv/delta]) from a
    snapshot response, via the adapter's _pick_col/_normalize_contract_keys
    idiom. A schema surprise raises naming the columns seen -- never guesses."""
    raw = frame.copy()
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    for flag, message in (
        ("chain_is_delayed", "provider marked chain delayed"),
        ("chain_is_truncated", "provider marked chain truncated"),
    ):
        if flag in raw.columns and raw[flag].map(
            lambda value: str(value).strip().lower() in {"1", "true", "yes"}
        ).any():
            raise RuntimeError(f"{ctx}: {message}")
    if "chain_status" in raw.columns:
        statuses = {
            str(value).strip().upper()
            for value in raw["chain_status"]
            if pd.notna(value)
        }
        if statuses and statuses != {"SUCCESS"}:
            raise RuntimeError(f"{ctx}: provider chain status is not SUCCESS")
    if "non_standard" in raw.columns:
        raw = raw.loc[
            ~raw["non_standard"].map(
                lambda value: str(value).strip().lower() in {"1", "true", "yes"}
            )
        ]
    if "multiplier" in raw.columns:
        multiplier = pd.to_numeric(raw["multiplier"], errors="coerce")
        raw = raw.loc[multiplier.eq(100.0)]
    if raw.empty:
        raise RuntimeError(f"{ctx}: no standard 100-multiplier contracts")
    norm = _normalize_contract_keys(raw, ctx)
    rename = {_pick_col(norm, _BID_CANDIDATES, ctx): "bid",
              _pick_col(norm, _ASK_CANDIDATES, ctx): "ask"}
    numeric = ["bid", "ask"]
    if with_greeks:
        rename[_pick_col(norm, _IV_CANDIDATES, ctx)] = "iv"
        _pick_col(norm, ("delta",), ctx)
        numeric += ["iv", "delta"]
    norm = norm.rename(columns=rename)
    for col in numeric:
        norm[col] = pd.to_numeric(norm[col], errors="coerce")
    if (norm["ask"] < norm["bid"]).fillna(False).any():
        raise RuntimeError(f"{ctx}: provider returned a crossed option market")
    if "chain_status" in raw.columns and not {"C", "P"} <= set(norm["right"]):
        raise RuntimeError(f"{ctx}: provider chain is missing calls or puts")
    return norm


def _require_fresh_option_row(row, now_utc, ctx: str) -> None:
    timestamp = row.get("timestamp") if row is not None else None
    if not quote_is_fresh(
        timestamp, now_utc, config.LIVE_QUOTE_MAX_AGE_SECONDS
    ):
        raise RuntimeError(f"{ctx}: stale, future, or missing option quote timestamp")
    bid = _finite_or_none(row.get("bid")) if row is not None else None
    ask = _finite_or_none(row.get("ask")) if row is not None else None
    if bid is None or ask is None or ask <= bid:
        raise RuntimeError(f"{ctx}: missing, crossed, or locked option market")


def _coerce_ts(ts):
    """tz-aware Timestamp or None. Naive server timestamps are localized to
    NY (repo convention: ThetaData last_trade carries America/New_York)."""
    if ts is None:
        return None
    t = pd.Timestamp(ts)
    if pd.isna(t):
        return None
    return t.tz_localize(NY_TZ) if t.tzinfo is None else t


def _load_iv_history(symbol: str) -> list[float]:
    """Trailing EOD atm_iv values from the cached feature frame; [] on any
    failure so the IV-rank preview reads UNKNOWN instead of crashing."""
    try:
        return [float(v) for v in features.load_features(symbol)["atm_iv"]]
    except Exception:
        return []


def _stock_spots(client, probe: dict, now_utc) -> dict:
    """{symbol: (spot_mid, ts, error_note)} from ONE batched
    stock_snapshot_quote call. Freshness is enforced only when the probe
    recorded a timestamp-like column for this endpoint; a stale or missing
    timestamp then fails that symbol closed."""
    rec = ((probe.get("endpoints") or {}).get("stock_snapshot_quote") or {})
    recorded = [str(c).strip().lower() for c in (rec.get("columns") or [])]
    ts_required = any(c in recorded for c in _TS_CANDIDATES)

    frame = client.stock_snapshot_quote(list(config.UNIVERSE))
    f = frame.copy()
    f.columns = [str(c).strip().lower() for c in f.columns]
    ctx = "stock_snapshot_quote"
    sym_col = _pick_col(f, _SYMBOL_CANDIDATES, ctx)
    bid_col = _pick_col(f, _BID_CANDIDATES, ctx)
    ask_col = _pick_col(f, _ASK_CANDIDATES, ctx)
    ts_col = next((c for c in _TS_CANDIDATES if c in f.columns), None)

    out: dict = {}
    for _, r in f.iterrows():
        sym = str(r[sym_col]).strip().upper()
        bid, ask = _finite_or_none(r[bid_col]), _finite_or_none(r[ask_col])
        ts = _coerce_ts(r[ts_col]) if ts_col else None
        if bid is None or ask is None:
            out[sym] = (None, ts, "no finite bid/ask in stock snapshot")
            continue
        if ask < bid:
            out[sym] = (None, ts, "crossed stock market")
            continue
        if ask == bid:
            out[sym] = (None, ts, "locked stock market")
            continue
        if ts_required and not quote_is_fresh(
                ts, now_utc, config.LIVE_QUOTE_MAX_AGE_SECONDS):
            out[sym] = (None, ts, "stale or missing stock quote timestamp")
            continue
        out[sym] = (mid_price(bid, ask), ts, None)
    return out


def _symbol_preview_live(client, symbol: str, trigger, stock_entitled: bool,
                         spots: dict, today: date, ny_iso: str,
                         now_utc) -> dict:
    """One symbol's live preview row. Option endpoints (greeks_all + OI) are
    touched ONLY while the live spot is at-or-through the trigger (armed)."""
    if stock_entitled:
        spot, ts, err = spots.get(
            symbol, (None, None, "symbol missing from batched stock snapshot"))
        if err:
            return {"symbol": symbol, "status": "unavailable", "note": err,
                    "spot_ts": _iso_or_none(ts)}
        spot_source, spot_ts = "stock_snapshot_quote", ts
    else:
        exps = _expirations(client, symbol, ny_iso)
        monthly = resolve_expiries(exps, today)["monthly"]
        if monthly is None:
            return {"symbol": symbol, "status": "unavailable",
                    "note": "no monthly expiry in band -- parity spot underivable"}
        quotes = client.option_snapshot_quote(symbol, expiration=monthly)
        chain_like = _assemble_chain_frame(
            quotes, f"{symbol} option_snapshot_quote")
        spot = parity_spot_from_chain(chain_like, ny_iso)
        if not np.isfinite(spot):
            return {"symbol": symbol, "status": "unavailable",
                    "note": "parity spot underivable from the monthly snapshot"}
        spot_source, spot_ts = "parity", None

    armed = trigger is not None and spot is not None and spot <= trigger
    atm_iv = leaps_row = oi = oi_asof = None
    if armed:
        resolved = resolve_expiries(_expirations(client, symbol, ny_iso), today)
        monthly, leaps_exp = resolved["monthly"], resolved["leaps"]
        if monthly is not None:
            g = client.option_snapshot_greeks_all(symbol, expiration=monthly)
            gf = _assemble_chain_frame(
                g, f"{symbol} greeks {monthly}", with_greeks=True)
            row = atm_row(gf, monthly)
            if row is not None:
                if getattr(client, "provider_name", "") == "schwab":
                    _require_fresh_option_row(
                        row, now_utc, f"{symbol} ATM option"
                    )
                iv = _finite_or_none(row["iv"])
                atm_iv = iv if iv is not None and iv > 0 else None
        if leaps_exp is not None:
            g = client.option_snapshot_greeks_all(symbol, expiration=leaps_exp)
            gf = _assemble_chain_frame(
                g, f"{symbol} greeks {leaps_exp}", with_greeks=True)
            leaps_row = _leaps_candidate(gf, today, config.H4_THESIS_DELTA)
            if leaps_row is not None:
                if getattr(client, "provider_name", "") == "schwab":
                    _require_fresh_option_row(
                        leaps_row, now_utc, f"{symbol} LEAPS option"
                    )
                oi_map, oi_asof = _open_interest(client, symbol, leaps_exp, ny_iso)
                if oi_map is not None:
                    oi = oi_map.get((leaps_row["exp_date"].isoformat(),
                                     float(leaps_row["strike"]), "C"))
                if oi is None:
                    oi_asof = None

    row = build_symbol_preview(
        symbol, spot=spot, spot_source=spot_source, spot_ts=spot_ts,
        trigger_level=trigger, atm_iv=atm_iv,
        iv_history=_load_iv_history(symbol), leaps_row=leaps_row,
        oi=oi, oi_asof=oi_asof, now=now_utc)
    if trigger is not None and not armed:
        row["note"] = ("not armed -- live option preview is fetched only "
                       "at-or-through the trigger level")
    return row


def refresh(client=None, now_ny=None, probe=None) -> dict:
    """Assemble the full live-preview payload. Outside the regular session or
    behind a failed probe gate, every symbol is "off" and NO client call is
    made. Any per-symbol exception marks that symbol "unavailable" and the
    rest continue -- one symbol's failure never kills the payload."""
    if now_ny is None:
        now_ny = datetime.now(ZoneInfo(NY_TZ))
    now_utc = now_ny.astimezone(timezone.utc)
    if probe is None:
        probe = load_latest_probe()
    ok, reason = probe_ok(probe, now_utc)
    session_open = in_regular_session(now_ny)
    payload = {
        "generated_at_utc": now_utc.isoformat(),
        "session_state": "open" if session_open else "closed",
        "probe": {"ok": bool(ok), "reason": reason},
        "symbols": {},
    }
    if not session_open or not ok:
        note = ("market closed / live off" if not session_open
                else f"live off -- {reason}")
        for sym in config.UNIVERSE:
            payload["symbols"][sym] = {"symbol": sym, "status": "off",
                                       "note": note}
        return payload

    if client is None:
        client = _live_client()
    if hasattr(client, "regular_session_state"):
        try:
            provider_session = client.regular_session_state(now_ny)
        except Exception as exc:
            payload["session_state"] = "unknown"
            payload["session_source"] = "schwab_market_hours"
            payload["session_note"] = _exc_note(exc)
            for sym in config.UNIVERSE:
                payload["symbols"][sym] = {
                    "symbol": sym,
                    "status": "off",
                    "note": "market-hours status unavailable / live off",
                }
            return payload
        payload["session_source"] = provider_session.get("source")
        if not provider_session.get("open"):
            payload["session_state"] = "closed"
            for sym in config.UNIVERSE:
                payload["symbols"][sym] = {
                    "symbol": sym,
                    "status": "off",
                    "note": "Schwab schedule: equity/option regular session closed",
                }
            return payload
    today = now_ny.date()
    ny_iso = today.isoformat()
    stock_entitled = bool(probe.get("stock_entitled"))

    spots: dict = {}
    if stock_entitled:
        try:
            spots = _stock_spots(client, probe, now_utc)
        except Exception as exc:
            note = _exc_note(exc)
            for sym in config.UNIVERSE:
                payload["symbols"][sym] = {"symbol": sym,
                                           "status": "unavailable", "note": note}
            return payload

    for sym in config.UNIVERSE:
        trigger = config.H5_ENTRY_TRIGGERS.get(sym)
        if not stock_entitled and trigger is None:
            payload["symbols"][sym] = {
                "symbol": sym, "status": "off",
                "note": ("no live stock feed on the current tier -- parity "
                         "preview covers trigger names only")}
            continue
        try:
            payload["symbols"][sym] = _symbol_preview_live(
                client, sym, trigger, stock_entitled, spots, today, ny_iso,
                now_utc)
        except Exception as exc:
            payload["symbols"][sym] = {"symbol": sym, "status": "unavailable",
                                       "note": _exc_note(exc)}
    return payload


# ---------------------------------------------------------------------------
# CLI: one-shot schema probe against the real client
# ---------------------------------------------------------------------------

def _print_probe_summary(probe: dict) -> None:
    provider = probe.get("provider", "thetadata")
    version = probe.get("provider_version", probe.get("thetadata_version"))
    print(f"live schema probe {probe['ny_date']} ({provider} {version})")
    print(f"stock_entitled: {probe['stock_entitled']}")
    print(f"monthly probe expiration: {probe.get('monthly_expiration')}")
    for name, rec in probe["endpoints"].items():
        if rec.get("ok"):
            print(f"  {name}: ok -- columns {rec['columns']}")
        else:
            print(f"  {name}: FAILED -- {rec.get('error')}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Live-preview plumbing for the mission-control dashboard "
                    "(read-only; the official H5 lane stays with entry_watch).")
    parser.add_argument("--probe", action="store_true",
                        help="run the one-shot live schema probe (regular "
                             "session only; writes reports/live_probe/)")
    args = parser.parse_args()
    if args.probe:
        _print_probe_summary(run_probe())
    else:
        parser.error("nothing to do: pass --probe to record the live schema "
                     "probe (the payload path is exercised by the dashboard "
                     "server, not this CLI)")

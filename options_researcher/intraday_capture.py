"""options_researcher/intraday_capture.py -- intraday option-board capture
(recorder), owner-directed 2026-07-24.

DESCRIPTIVE / ALERT-DISPLAY ONLY. This module has ZERO verdict authority: it
never imports options_researcher.entry_watch, never writes data/positions/
or ledger/, and never renders the verdict vocabulary owned by entry_watch's
trigger grading or the attractiveness dashboard's badges (mirrored by
tests/test_intraday_capture.py's vocabulary test). It snapshots the canonical
15-name H7 scope from options_researcher.h7_scope.watch_universe several times
per trading day; display-only attractiveness extras never trigger paid capture.
It records spot (bid/mid/ask from the stock feed, or a put-call-parity
mid-only fallback when that feed is not entitled -- see "ENTITLEMENT
REALITY" below), nearest-monthly ATM IV, an intraday IV-rank PREVIEW (via
live_quotes.iv_rank_preview against the trailing EOD atm_iv history --
the only correct way to compute this offline, when the greeks endpoint is
entitled), and a full nearest-monthly chain snapshot with per-contract
passes_liquidity admission counts. It is entirely separate from live_quotes'
LIVE PREVIEW lane (which
feeds the H5 mission-control dashboard) and from entry_watch's trigger
grading: this tool captures what the board looked like, it never grades one.

Storage isolation (non-negotiable): full chains go to
.cache/intraday/{symbol}_{date}T{HHMM}.parquet -- a directory that
entry_watch._gather's ".cache/chains/{symbol}_*.parquet" glob can never
reach (different directory alone guarantees this; the "T{HHMM}" timestamp in
the filename is defense in depth). See
tests/test_intraday_capture.py::StorageIsolationTests. Receipts are
write-once JSON under reports/intraday_capture/{date}/{tag}.json
(config.INTRADAY_RECEIPT_DIR), mirroring h10_watch's _write_receipt: an
identical rerun is a benign no-op, a conflicting rerun refuses (exit 2).

Probe auto-heal: before capturing, this module checks its OWN
capture_probe_ok() (see below) against the latest recorded schema probe. If
it is missing or stale AND the wall clock is already inside the regular
session (guaranteed true at capture time, since we refuse outside the
session first), it runs ONE fresh live_quotes.run_probe() and re-checks --
this is the permanent fix for the cold-start problem (a probe that predates
today). If still not ok, the capture refuses fail-closed (exit 1) rather
than fetching against unverified response schemas.

ENTITLEMENT REALITY (probe-verified 2026-07-24, this account's ThetaData
tier at the time): stock_snapshot_quote and option_snapshot_greeks_all both
return PERMISSION_DENIED (stock quotes need a paid stock add-on; greeks need
the PROFESSIONAL option tier -- this account is on STANDARD). Two
consequences baked into the design below, not an afterthought:
  1. capture_probe_ok() uses its OWN REQUIRED_PROBE_ENDPOINTS -- expirations,
     option_snapshot_quote (bid/ask, no greeks), open_interest -- and does
     NOT require option_snapshot_greeks_all, unlike
     live_quotes.REQUIRED_PROBE_ENDPOINTS. Gating this module's entitled
     quotes+OI core on an endpoint this account can never pass would
     silently zero out every capture. live_quotes.probe_ok() itself is
     UNTOUCHED -- this is a separate, module-local gate.
  2. Spot falls back to put-call parity (data.underlying_closes.
     parity_spot_from_chain, the same helper live_quotes uses for its own
     no-stock-entitlement case) computed from the ALREADY-FETCHED
     option_snapshot_quote chain -- no extra paid call. ATM IV / IV-rank
     preview genuinely require greeks; when the greeks endpoint fails, a
     SOLVER-DERIVED ATM IV is now attempted before recording an honest gap
     (2026-07-24, IV-solver-capture): options_researcher.black_scholes.
     implied_vol (spec-frozen, reused unmodified) against the entitled
     chain's own bid/ask mid, a point-in-time Treasury rate
     (data.rates.risk_free_rate) and dividend yield
     (data.rates.dividend_yield), with a bounded delta fixed-point contract
     reselection since this chain has no delta column of its own -- see
     _solver_atm_iv below. A solver-derived IV is NEVER spliced into
     iv_rank_preview (which compares against ThetaData's OWN EOD atm_iv
     history -- a different solver, different conventions) unless
     solver_iv_calibration_gate(symbol) passes a measured calibration
     receipt (options_researcher/iv_solver_calibration.py); otherwise
     iv_rank_preview stays null with an honest iv_label. Only when the
     solver ALSO fails is the ORIGINAL honest-gap behavior preserved
     (greeks_note records the specific reason, never a blanket label):
     one of "solver: no_european_bs_root", "solver: not_converged",
     "solver: expired", "solver: no dividend data for {symbol}",
     "solver: no rate curve coverage", "solver: no quotes at selected
     contract", or "solver: no spot available" (see _solver_atm_iv).
     _load_latest_calibration_receipt selects the newest calibration
     receipt by each file's PARSED run_at_utc, never by filename sort
     (fixed 2026-07-24: a same-day strict-mode all-fail receipt and a
     same-day retrospective-mode mostly-pass receipt name themselves
     YYYY-MM-DD[-retrospective].json, and ASCII "-" sorts before "." --
     a lexicographic sort masked a real 14/15-pass retrospective receipt
     behind a same-day all-fail strict one in production). Whenever a
     splice happens for at least one name, the capture receipt records a
     top-level "iv_rank_calibration" provenance block ({"receipt_path",
     "inputs_mode", "run_at_utc"}) naming exactly which calibration
     evidence authorized it; the block is null when no name spliced.

Reuses rather than reinvents: live_quotes' session-gate machinery,
column-resolution helpers (_pick_col via the adapter), _assemble_chain_frame,
resolve_expiries, iv_rank_preview, _load_iv_history, and the per-day
expirations/open-interest memos; data.thetadata_adapter.passes_liquidity and
mid_price; data.underlying_closes.parity_spot_from_chain (live_quotes' own
no-stock-entitlement fallback); options_researcher.chains.atm_row;
options_researcher.black_scholes.implied_vol/delta (spec-frozen, ZERO
changes); data.rates.risk_free_rate/dividend_yield;
data.atomic_io.atomic_parquet_write; and research.hashing.config_hash for
receipt provenance.

    uv run python -m options_researcher.intraday_capture --session-tag open
    uv run python -m options_researcher.intraday_capture --session-tag open --force
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data import rates as data_rates
from data.atomic_io import atomic_parquet_write
from data.thetadata_adapter import _pick_col, mid_price, passes_liquidity
from data.underlying_closes import parity_spot_from_chain
from options_researcher import live_quotes as lq
from options_researcher.black_scholes import delta as bs_delta
from options_researcher.black_scholes import implied_vol
from options_researcher.chains import atm_row
from options_researcher.h7_scope import watch_universe
from research.hashing import config_hash

NY_TZ = "America/New_York"
CACHE_DIR = Path(config.INTRADAY_CACHE_DIR)
RECEIPT_DIR = Path(config.INTRADAY_RECEIPT_DIR)

# This module's own required-probe-endpoint set -- see the "ENTITLEMENT
# REALITY" note above for why it deliberately omits
# option_snapshot_greeks_all (present in live_quotes.REQUIRED_PROBE_ENDPOINTS
# for the H5 LEAPS delta/IV preview, but not required by this module's
# entitled quotes+OI core). Never edit live_quotes.REQUIRED_PROBE_ENDPOINTS
# to "fix" this -- that would weaken live_quotes' own gate for an unrelated
# module's entitlement gap.
REQUIRED_PROBE_ENDPOINTS = (
    "option_list_expirations",
    "option_snapshot_quote",
    "option_snapshot_open_interest",
)


def _parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


# Parsed once at import from the config string table (config.py stays
# import-free by convention; parsing happens here instead).
SESSION_TIMES: dict[str, time] = {
    tag: _parse_hhmm(hhmm) for tag, hhmm in config.INTRADAY_CAPTURE_TIMES.items()
}


# ---------------------------------------------------------------------------
# Pure timing functions
# ---------------------------------------------------------------------------

def _minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def _scheduled_delta_minutes(tag: str, now_ny: datetime) -> int:
    """Absolute minutes between now_ny's wall clock and `tag`'s scheduled
    time. Raises KeyError for an unknown tag -- callers that need a
    fail-soft answer use nearest_session_tag instead."""
    return abs(_minutes(now_ny.time()) - _minutes(SESSION_TIMES[tag]))


def nearest_session_tag(now_ny: datetime) -> str | None:
    """The session_tag whose scheduled time is closest to now_ny's wall
    clock, if within config.INTRADAY_CAPTURE_TOLERANCE_MINUTES; else None.
    Used by tools/intraday_capture.sh to self-select a tag from the wall
    clock rather than hardcoding one per LaunchAgent invocation."""
    best_tag, best_delta = None, None
    for tag in SESSION_TIMES:
        delta = _scheduled_delta_minutes(tag, now_ny)
        if best_delta is None or delta < best_delta:
            best_tag, best_delta = tag, delta
    if best_delta is None or best_delta > config.INTRADAY_CAPTURE_TOLERANCE_MINUTES:
        return None
    return best_tag


def validate_session_tag(tag: str, now_ny: datetime, *,
                         force: bool = False) -> tuple[bool, str]:
    """(ok, reason). An unknown tag always refuses, even with --force. A
    known tag outside the tolerance window refuses unless force=True."""
    if tag not in SESSION_TIMES:
        return False, (f"unknown session_tag {tag!r}; choices: "
                       f"{sorted(SESSION_TIMES)}")
    if force:
        return True, "forced (scheduled-time check bypassed)"
    delta = _scheduled_delta_minutes(tag, now_ny)
    tol = config.INTRADAY_CAPTURE_TOLERANCE_MINUTES
    if delta > tol:
        scheduled = SESSION_TIMES[tag]
        return False, (
            f"session_tag {tag!r} is scheduled for "
            f"{scheduled.isoformat(timespec='minutes')} ET +/-{tol}min; now "
            f"{now_ny.time().isoformat(timespec='minutes')} ET is {delta}min "
            "off -- pass --force for a manual/testing run")
    return True, f"within {tol}min of the scheduled time"


# ---------------------------------------------------------------------------
# Probe auto-heal
# ---------------------------------------------------------------------------

def capture_probe_ok(probe: dict | None, now_utc) -> tuple[bool, str]:
    """Mirrors live_quotes.probe_ok's version/age/endpoint checks exactly,
    but against THIS module's REQUIRED_PROBE_ENDPOINTS (no
    option_snapshot_greeks_all -- see the module docstring's "ENTITLEMENT
    REALITY" note). A missing stock entitlement is never fatal here either:
    spot falls back to put-call parity (see _spot_for_symbol), same as
    live_quotes' own non-fatal handling of stock_entitled=False."""
    if probe is None:
        return False, ("no schema probe recorded -- run "
                       "`python -m options_researcher.live_quotes --probe` "
                       "during a regular session")
    configured = lq._configured_provider()
    recorded_provider = probe.get("provider", "thetadata")
    if recorded_provider != configured:
        return False, (
            f"probe recorded provider={recorded_provider} but configured "
            f"provider={configured} -- re-probe before trusting columns"
        )
    installed = lq._installed_provider_version(configured)
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
    return True, "ok"


def ensure_probe_ok(client, now_ny: datetime, now_utc: datetime
                    ) -> tuple[dict | None, bool, bool, str]:
    """(probe, healed, ok, reason). If the existing probe already passes
    THIS module's capture_probe_ok, returns it unchanged (healed=False).
    Otherwise -- since a capture run only calls this after confirming
    in_regular_session -- runs ONE fresh live_quotes.run_probe() (the
    shared probe file/format both modules read) and re-checks against
    capture_probe_ok. Never runs a probe outside the regular session
    (mirrors run_probe's own refusal)."""
    probe = lq.load_latest_probe()
    ok, reason = capture_probe_ok(probe, now_utc)
    if ok:
        return probe, False, ok, reason
    if not lq.in_regular_session(now_ny):
        return probe, False, ok, reason
    probe = lq.run_probe(client=client, now_ny=now_ny)
    ok, reason = capture_probe_ok(probe, now_utc)
    return probe, True, ok, reason


# ---------------------------------------------------------------------------
# Fetch layer (thin; exercised only via injected fakes in tests)
# ---------------------------------------------------------------------------

def _stock_spots(client, universe: list[str], probe: dict, now_utc
                 ) -> dict[str, dict]:
    """{symbol: {"bid","ask","mid","ts","error"}} from ONE batched
    stock_snapshot_quote call over `universe`. Mirrors
    live_quotes._stock_spots' column-resolution idiom exactly, but keeps bid
    and ask (not just mid) and is parameterized to any universe rather than
    hardcoding config.UNIVERSE."""
    rec = ((probe.get("endpoints") or {}).get("stock_snapshot_quote") or {})
    recorded = [str(c).strip().lower() for c in (rec.get("columns") or [])]
    ts_required = any(c in recorded for c in lq._TS_CANDIDATES)

    frame = client.stock_snapshot_quote(list(universe))
    f = frame.copy()
    f.columns = [str(c).strip().lower() for c in f.columns]
    ctx = "stock_snapshot_quote"
    sym_col = _pick_col(f, lq._SYMBOL_CANDIDATES, ctx)
    bid_col = _pick_col(f, lq._BID_CANDIDATES, ctx)
    ask_col = _pick_col(f, lq._ASK_CANDIDATES, ctx)
    ts_col = next((c for c in lq._TS_CANDIDATES if c in f.columns), None)

    out: dict[str, dict] = {}
    for _, r in f.iterrows():
        sym = str(r[sym_col]).strip().upper()
        bid, ask = lq._finite_or_none(r[bid_col]), lq._finite_or_none(r[ask_col])
        ts = lq._coerce_ts(r[ts_col]) if ts_col else None
        if bid is None or ask is None:
            out[sym] = {"bid": None, "ask": None, "mid": None, "ts": ts,
                        "error": "no finite bid/ask in stock snapshot"}
            continue
        if ts_required and not lq.quote_is_fresh(
                ts, now_utc, config.LIVE_QUOTE_MAX_AGE_SECONDS):
            out[sym] = {"bid": None, "ask": None, "mid": None, "ts": ts,
                        "error": "stale or missing stock quote timestamp"}
            continue
        out[sym] = {"bid": bid, "ask": ask, "mid": mid_price(bid, ask),
                    "ts": ts, "error": None}
    return out


def _spot_for_symbol(spot_row: dict | None, chain_like: pd.DataFrame,
                     ny_iso: str) -> tuple[dict, str | None]:
    """(spot_fields, note_or_None). Prefers the batched stock quote; falls
    back to put-call parity (data.underlying_closes.parity_spot_from_chain,
    live_quotes' own no-stock-entitlement fallback) computed from the
    ALREADY-FETCHED entitled option_snapshot_quote chain -- no extra paid
    call. spot_source is "stock_snapshot" | "parity_fallback" | None."""
    if spot_row is not None and not spot_row.get("error"):
        return {
            "spot_bid": spot_row["bid"], "spot_ask": spot_row["ask"],
            "spot_mid": spot_row["mid"],
            "spot_ts": (spot_row["ts"].isoformat()
                       if spot_row["ts"] is not None else None),
            "spot_source": "stock_snapshot",
        }, None
    note = (spot_row["error"] if spot_row is not None and spot_row.get("error")
           else "symbol missing from batched stock snapshot")
    parity = parity_spot_from_chain(chain_like, ny_iso)
    if not math.isfinite(parity):
        return {"spot_bid": None, "spot_ask": None, "spot_mid": None,
                "spot_ts": None, "spot_source": None}, note
    return {
        "spot_bid": None, "spot_ask": None, "spot_mid": float(parity),
        "spot_ts": None, "spot_source": "parity_fallback",
    }, note


# ---------------------------------------------------------------------------
# Solver-derived ATM IV (fallback when the greeks endpoint fails/denies)
# ---------------------------------------------------------------------------

def _solver_atm_iv(chain_like: pd.DataFrame, spot: float, symbol: str,
                   monthly: date, today: date) -> tuple[float | None, str | None]:
    """Best-effort solver-derived ATM IV when the greeks endpoint is not
    entitled or otherwise fails. Reuses options_researcher.black_scholes.
    implied_vol (spec-frozen, ZERO changes) against `chain_like`'s OWN
    bid/ask mid (the entitled option_snapshot_quote chain -- no extra paid
    call), a point-in-time Treasury rate (data.rates.risk_free_rate) and
    dividend yield (data.rates.dividend_yield).

    Contract selection: `chain_like` has no delta column here (the greeks
    endpoint that would have supplied one just failed), so the EOD
    atm_iv convention (chains.atm_row's delta-column nearest-0.50-put
    selection) cannot be reused directly. Instead: seed with the
    nearest-strike-to-spot put, solve its IV, compute
    options_researcher.black_scholes.delta() at the solved sigma, and
    re-select+re-solve ONCE against whichever immediately neighboring
    strike has a delta closer to 0.50 -- a bounded, single extra pass, not
    an iterative fixed point.

    Returns (atm_iv_or_None, reason_or_None). `reason` is None on success,
    else one of the specific "solver: ..." strings the module docstring
    documents -- never a blanket label.
    """
    t = (monthly - today).days / 365.0
    if t <= 0:
        return None, "solver: expired"
    try:
        r = data_rates.risk_free_rate(today, monthly).rate
    except data_rates.MissingRateError:
        return None, "solver: no rate curve coverage"
    try:
        q = data_rates.dividend_yield(symbol, today, spot).yield_rate
    except data_rates.MissingDividendYieldError:
        return None, f"solver: no dividend data for {symbol}"

    exp_dates = pd.to_datetime(chain_like["expiration"]).dt.date
    puts = chain_like[(chain_like["right"] == "P") & (exp_dates == monthly)
                      & (chain_like["bid"] > 0) & (chain_like["ask"] >= chain_like["bid"])]
    if puts.empty:
        return None, "solver: no quotes at selected contract"

    def _solve(row):
        price = mid_price(float(row["bid"]), float(row["ask"]))
        return implied_vol(price=price, S=spot, K=float(row["strike"]), t=t,
                           r=r, right="P", q=q)

    strikes = sorted(puts["strike"].unique())
    seed_strike = min(strikes, key=lambda k: abs(k - spot))
    seed_row = puts[puts["strike"] == seed_strike].iloc[0]
    seed_result = _solve(seed_row)
    if not seed_result.ok:
        return None, f"solver: {seed_result.reason}"

    best_result = seed_result
    best_gap = abs(abs(bs_delta(S=spot, K=seed_strike, t=t, r=r,
                                sigma=seed_result.iv, right="P", q=q)) - 0.50)
    seed_idx = strikes.index(seed_strike)
    for neighbor_idx in (seed_idx - 1, seed_idx + 1):
        if neighbor_idx < 0 or neighbor_idx >= len(strikes):
            continue
        neighbor_strike = strikes[neighbor_idx]
        neighbor_row = puts[puts["strike"] == neighbor_strike].iloc[0]
        neighbor_result = _solve(neighbor_row)
        if not neighbor_result.ok:
            continue
        neighbor_gap = abs(abs(bs_delta(S=spot, K=neighbor_strike, t=t, r=r,
                                        sigma=neighbor_result.iv, right="P",
                                        q=q)) - 0.50)
        if neighbor_gap < best_gap:
            best_result, best_gap = neighbor_result, neighbor_gap

    return best_result.iv, None


def _load_latest_calibration_receipt(receipt_dir: str | Path | None = None
                                     ) -> tuple[dict | None, Path | None]:
    """(receipt, path) for the newest reports/iv_solver_calibration
    receipt, or (None, None). "Newest" is decided by each file's OWN
    PARSED run_at_utc field, never by filename -- a same-day strict-mode
    receipt (all-fail) and a same-day retrospective-mode receipt (mostly
    pass) both name themselves by run DATE (YYYY-MM-DD[-retrospective
    ].json), so a lexicographic filename sort is NOT a reliable
    chronological sort: ASCII "-" (0x2D) sorts before "." (0x2E), so
    "2026-07-24-retrospective.json" sorts AFTER "2026-07-24.json" even
    when it names_passed and the plain file doesn't -- fine -- but the
    reverse (plain file run LATER than the retrospective one) sorts the
    same way despite being chronologically backwards. That exact
    situation masked a real 14/15-pass retrospective receipt behind a
    same-day all-fail strict receipt in production on 2026-07-24. Every
    *.json file in the directory is considered; a file that is not valid
    JSON, is not a JSON object, or has an unparseable/missing run_at_utc
    is skipped, never raised. Ties (equal parsed run_at_utc) break
    deterministically by filename -- the lexicographically-last name
    wins, since `names` is iterated in ascending sorted order and later
    files overwrite the running best on `>=`."""
    d = Path(receipt_dir if receipt_dir is not None
             else config.IV_CALIBRATION_RECEIPT_DIR)
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith(".json"))
    except FileNotFoundError:
        return None, None
    best_receipt: dict | None = None
    best_path: Path | None = None
    best_ts = None
    for name in names:
        path = d / name
        try:
            with open(path, encoding="utf-8") as fh:
                receipt = json.load(fh)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
        if not isinstance(receipt, dict):
            continue
        try:
            ts = pd.Timestamp(receipt.get("run_at_utc"))
        except (TypeError, ValueError):
            continue
        if pd.isna(ts):
            continue
        if best_ts is None or ts >= best_ts:
            best_receipt, best_path, best_ts = receipt, path, ts
    return best_receipt, best_path


def _solver_iv_calibration_check(symbol: str
                                 ) -> tuple[bool, dict | None, Path | None]:
    """(passed, receipt, receipt_path). Fail-closed to (False, receipt-or-
    None, path-or-None) in every error case -- missing receipt, stale
    receipt, hash mismatch, a names_failed symbol, or any unexpected
    receipt shape; never raises (mirrors solver_iv_calibration_gate's own
    contract). Exists separately from solver_iv_calibration_gate so a
    caller that needs to know WHICH receipt authorized a splice (for
    provenance) doesn't have to re-load and re-parse it a second time."""
    try:
        receipt, path = _load_latest_calibration_receipt()
        if receipt is None:
            return False, None, None
        age = pd.Timestamp(datetime.now(timezone.utc)) - pd.Timestamp(
            receipt.get("run_at_utc"))
        if pd.isna(age) or age > pd.Timedelta(days=config.IV_CALIBRATION_MAX_AGE_DAYS):
            return False, receipt, path
        if receipt.get("config_hash") != config_hash():
            return False, receipt, path
        passed = symbol in (receipt.get("names_passed") or [])
        return passed, receipt, path
    except Exception:
        return False, None, None


def solver_iv_calibration_gate(symbol: str) -> bool:
    """True only if the newest calibration receipt (by parsed run_at_utc --
    see _load_latest_calibration_receipt) exists, is younger than
    config.IV_CALIBRATION_MAX_AGE_DAYS, its config_hash matches the CURRENT
    config/code (a change since calibration invalidates it), and `symbol`
    is in its names_passed list. Fail-closed in every other case -- missing
    receipt, stale receipt, hash mismatch, a names_failed symbol, or any
    unexpected receipt shape all return False; this NEVER raises. Thin
    bool-only wrapper around _solver_iv_calibration_check; _capture_symbol
    calls the latter directly so it can also record which receipt
    authorized a splice."""
    passed, _receipt, _path = _solver_iv_calibration_check(symbol)
    return passed


def _capture_symbol(client, symbol: str, spot_row: dict | None,
                    today: date, ny_iso: str
                    ) -> tuple[dict, pd.DataFrame | None, dict | None]:
    """One name's descriptive capture row + its full nearest-monthly chain
    frame (or None on failure) + the calibration receipt provenance (or
    None) that authorized an iv_rank_preview splice for THIS symbol, if
    one happened. Lets exceptions propagate -- the caller wraps this per
    symbol so one name's failure never aborts the board.

    The entitled core (expirations, option_snapshot_quote bid/ask,
    open_interest) always runs. Greeks (ATM IV / IV-rank preview) are a
    best-effort ENRICHMENT in a separate try/except: a PERMISSION_DENIED
    there (this account is on STANDARD, not PROFESSIONAL, as of 2026-07-24)
    degrades only atm_iv/iv_rank_preview/chain iv+delta columns to an
    honest gap, never the quotes+OI core."""
    summary: dict = {"symbol": symbol, "status": "ok"}

    exps = lq._expirations(client, symbol, ny_iso)
    monthly = lq.resolve_expiries(exps, today)["monthly"]
    if monthly is None:
        summary["status"] = "unavailable"
        summary["note"] = "no monthly expiry in the 15-60 DTE band"
        return summary, None, None

    # Entitled core: bid/ask chain (no greeks) + open interest.
    q = client.option_snapshot_quote(symbol, expiration=monthly)
    chain_like = lq._assemble_chain_frame(q, f"{symbol} option_snapshot_quote")
    oi_map, oi_asof = lq._open_interest(client, symbol, monthly, ny_iso)

    spot_fields, spot_note = _spot_for_symbol(spot_row, chain_like, ny_iso)
    summary.update(spot_fields)
    if spot_note:
        summary["spot_note"] = spot_note

    admitted = {"C": 0, "P": 0}
    total = {"C": 0, "P": 0}
    spreads: list[float] = []
    rows: list[dict] = []
    for _, row in chain_like.iterrows():
        right = str(row.get("right", "")).strip().upper()
        strike = float(row["strike"])
        bid = lq._finite_or_none(row["bid"])
        ask = lq._finite_or_none(row["ask"])
        exp_iso = pd.Timestamp(row["expiration"]).date().isoformat()
        oi = oi_map.get((exp_iso, strike, right)) if oi_map is not None else None
        row_admitted = False
        if bid is not None and ask is not None and ask > 0 and ask >= bid:
            mid = mid_price(bid, ask)
            if mid > 0:
                spreads.append((ask - bid) / mid)
            if right in total:
                total[right] += 1
        if oi is not None and bid is not None and ask is not None:
            row_admitted = passes_liquidity(oi, bid, ask)
        if row_admitted and right in admitted:
            admitted[right] += 1
        rows.append({
            "expiration": exp_iso, "strike": strike, "right": right,
            "bid": bid if bid is not None else float("nan"),
            "ask": ask if ask is not None else float("nan"),
            "iv": float("nan"), "delta": float("nan"),  # filled in below if entitled
            "open_interest": float(oi) if oi is not None else float("nan"),
            "admitted": bool(row_admitted),
        })

    # Best-effort greeks enrichment (ATM IV / IV-rank preview). Never lets a
    # PERMISSION_DENIED here touch the entitled fields already computed. On
    # failure, attempt a solver-derived ATM IV (2026-07-24) before recording
    # an honest gap -- see _solver_atm_iv and the module docstring.
    atm_iv = None
    ivr = None
    greeks_note = None
    iv_source = None
    iv_label = None
    calibration_used: dict | None = None
    try:
        g = client.option_snapshot_greeks_all(symbol, expiration=monthly)
        gf = lq._assemble_chain_frame(g, f"{symbol} greeks {monthly}", with_greeks=True)
        gkey = {
            (pd.Timestamp(r["expiration"]).date().isoformat(), float(r["strike"]),
             str(r.get("right", "")).strip().upper()):
                (lq._finite_or_none(r.get("iv")), lq._finite_or_none(r.get("delta")))
            for _, r in gf.iterrows()
        }
        for row_dict in rows:
            key = (row_dict["expiration"], row_dict["strike"], row_dict["right"])
            match = gkey.get(key)
            if match is not None:
                iv_val, delta_val = match
                if iv_val is not None:
                    row_dict["iv"] = iv_val
                if delta_val is not None:
                    row_dict["delta"] = delta_val
        atm = atm_row(gf, monthly)
        if atm is not None:
            iv = lq._finite_or_none(atm["iv"])
            atm_iv = iv if iv is not None and iv > 0 else None
        if atm_iv is not None:
            ivr = lq._finite_or_none(
                lq.iv_rank_preview(lq._load_iv_history(symbol), atm_iv))
            iv_source = "greeks_endpoint"
    except Exception as exc:
        greeks_exc_note = (
            "not entitled: option greeks endpoint requires professional "
            f"tier ({type(exc).__name__}: {exc})")
        spot_for_solver = summary.get("spot_mid")
        if spot_for_solver is not None and math.isfinite(spot_for_solver):
            solved_iv, solver_reason = _solver_atm_iv(
                chain_like, spot_for_solver, symbol, monthly, today)
        else:
            solved_iv, solver_reason = None, "solver: no spot available"
        if solved_iv is not None:
            atm_iv = solved_iv
            iv_source = "bs_solver"
            gate_passed, calib_receipt, calib_path = (
                _solver_iv_calibration_check(symbol))
            if gate_passed:
                ivr = lq._finite_or_none(
                    lq.iv_rank_preview(lq._load_iv_history(symbol), atm_iv))
                calibration_used = {
                    "receipt_path": str(calib_path) if calib_path else None,
                    "inputs_mode": (calib_receipt.get("inputs_mode", "strict")
                                    if calib_receipt else "strict"),
                    "run_at_utc": (calib_receipt.get("run_at_utc")
                                   if calib_receipt else None),
                }
            else:
                ivr = None
                iv_label = "solver-derived, not rank-comparable"
        else:
            greeks_note = f"{greeks_exc_note}; solver fallback failed: {solver_reason}"

    chain_frame = pd.DataFrame(rows)

    summary.update({
        "monthly_expiration": monthly.isoformat(),
        "atm_iv": atm_iv,
        "iv_rank_preview": ivr,
        "iv_source": iv_source,
        "iv_label": iv_label,
        "greeks_note": greeks_note,
        "chain_contracts_total": total,
        "chain_contracts_admitted": admitted,
        "min_spread_pct_observed": min(spreads) if spreads else None,
        "open_interest_asof": oi_asof,
    })
    return summary, chain_frame, calibration_used


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def chain_cache_path(symbol: str, ny_date: date, now_ny: datetime,
                     cache_dir: Path = CACHE_DIR) -> Path:
    """.cache/intraday/{symbol}_{YYYY-MM-DD}T{HHMM}.parquet -- a directory
    and filename shape entry_watch._gather's
    ".cache/chains/{symbol}_*.parquet" glob can never match (see
    tests/test_intraday_capture.py::StorageIsolationTests)."""
    stamp = now_ny.strftime("%H%M")
    return Path(cache_dir) / f"{symbol}_{ny_date.isoformat()}T{stamp}.parquet"


def _write_receipt(receipt: dict, path: Path) -> bool:
    """Write once; an identical rerun is a no-op, conflicts are refused.
    Mirrors options_researcher.h10_watch._write_receipt exactly."""
    content = json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != content:
            return False
    return True


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def capture(session_tag: str, *, force: bool = False, client=None,
           now_ny: datetime | None = None, universe: list[str] | None = None,
           cache_dir: Path = CACHE_DIR, receipt_dir: Path = RECEIPT_DIR
           ) -> tuple[int, dict | None]:
    """Run one full-board capture. Returns (exit_code, receipt_or_None).
    exit_code: 0 = wrote (or benignly reused an identical) receipt;
    1 = refused (outside session / bad timing / probe unhealable);
    2 = an existing receipt has different content (conflict)."""
    if now_ny is None:
        now_ny = datetime.now(ZoneInfo(NY_TZ))
    now_utc = now_ny.astimezone(timezone.utc)
    universe = (list(universe) if universe is not None
                else list(watch_universe()))

    if not lq.in_regular_session(now_ny):
        print(f"intraday_capture refused: {now_ny.isoformat()} ET is "
              "outside the NY regular session")
        return 1, None

    ok_tag, reason_tag = validate_session_tag(session_tag, now_ny, force=force)
    if not ok_tag:
        print(f"intraday_capture refused: {reason_tag}")
        return 1, None

    probe, healed, probe_ok_flag, probe_reason = ensure_probe_ok(
        client, now_ny, now_utc)
    if healed:
        print("intraday_capture: schema probe was missing/stale -- ran a "
              "fresh probe (auto-heal)")
    if not probe_ok_flag:
        print(f"intraday_capture refused: schema probe not ok -- {probe_reason}")
        return 1, None

    if client is None:
        client = lq._live_client()

    today = now_ny.date()
    ny_iso = today.isoformat()

    spots: dict[str, dict] = {}
    spots_error: str | None = None
    try:
        spots = _stock_spots(client, universe, probe, now_utc)
    except Exception as exc:
        spots_error = f"{type(exc).__name__}: {exc}"

    names: dict[str, dict] = {}
    iv_rank_calibration: dict | None = None
    for sym in universe:
        try:
            row = None if spots_error is not None else spots.get(sym)
            summary, chain_frame, calib_used = _capture_symbol(
                client, sym, row, today, ny_iso)
            if spots_error is not None:
                # More specific than the generic per-symbol "missing from
                # batched stock snapshot" note _capture_symbol set: the
                # WHOLE batch call raised, not just this one symbol's row.
                summary["spot_note"] = f"stock snapshot batch failed: {spots_error}"
        except Exception as exc:
            summary, chain_frame, calib_used = (
                {"symbol": sym, "status": "unavailable",
                 "note": f"{type(exc).__name__}: {exc}"}, None, None)
        if calib_used is not None:
            # Every splice this run draws on the SAME newest-by-run_at_utc
            # calibration receipt (one _load_latest_calibration_receipt
            # call per symbol, same directory, same wall clock), so later
            # symbols just re-confirm the same provenance -- overwriting is
            # a no-op in practice, not a "last symbol wins" ambiguity.
            iv_rank_calibration = calib_used
        if chain_frame is not None and not chain_frame.empty:
            path = chain_cache_path(sym, today, now_ny, cache_dir=cache_dir)
            atomic_parquet_write(chain_frame, path)
            summary["chain_cache_path"] = str(path)
        names[sym] = summary

    probe_receipt_path = (os.path.join(lq.PROBE_DIR, f"{probe['ny_date']}.json")
                          if probe else None)
    receipt = {
        "receipt_kind": "intraday_capture/v1",
        "session_tag": session_tag,
        "scheduled_et": config.INTRADAY_CAPTURE_TIMES[session_tag],
        "captured_at_et": now_ny.isoformat(),
        "captured_at_utc": now_utc.isoformat(),
        "force": bool(force),
        "universe": list(universe),
        "probe_receipt_path": probe_receipt_path,
        "probe_healed_this_run": bool(healed),
        "config_hash": config_hash(),
        "iv_rank_calibration": iv_rank_calibration,
        "names": names,
    }
    out_path = Path(receipt_dir) / today.isoformat() / f"{session_tag}.json"
    written = _write_receipt(receipt, out_path)
    if not written:
        print(f"intraday_capture receipt CONFLICT -- {out_path} already "
              "has different content")
        return 2, receipt
    print(f"receipt={out_path}")
    covered = sum(1 for n in names.values() if n.get("status") == "ok")
    print(f"coverage: {covered}/{len(universe)} names captured")
    return 0, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Intraday option-board capture (recorder). Descriptive "
                    "only -- zero verdict authority; never trades.")
    parser.add_argument(
        "--session-tag", required=True, choices=sorted(config.INTRADAY_CAPTURE_TIMES),
        help="which scheduled capture window this run represents")
    parser.add_argument(
        "--force", action="store_true",
        help="bypass the scheduled-time tolerance check for a manual/testing "
            "run (recorded in the receipt as force=true)")
    args = parser.parse_args(argv)
    exit_code, _ = capture(args.session_tag, force=args.force)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

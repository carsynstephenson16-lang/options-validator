"""options_researcher/intraday_capture.py -- intraday option-board capture
(recorder), owner-directed 2026-07-24.

DESCRIPTIVE / ALERT-DISPLAY ONLY. This module has ZERO verdict authority: it
never imports options_researcher.entry_watch, never writes data/positions/
or ledger/, and never renders the verdict vocabulary owned by entry_watch's
trigger grading or the attractiveness dashboard's badges (mirrored by
tests/test_intraday_capture.py's vocabulary test). It snapshots
config.ATTRACTIVENESS_UNIVERSE (all 15 scope names) several times per
trading day: spot (bid/mid/ask), nearest-monthly ATM IV, an intraday IV-rank
PREVIEW (via live_quotes.iv_rank_preview against the trailing EOD atm_iv
history -- the only correct way to compute this offline), and a full
nearest-monthly chain snapshot with per-contract passes_liquidity admission
counts. It is entirely separate from live_quotes' LIVE PREVIEW lane (which
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

Probe auto-heal: before capturing, this module checks live_quotes.probe_ok()
against the latest recorded schema probe. If it is missing or stale AND the
wall clock is already inside the regular session (guaranteed true at capture
time, since we refuse outside the session first), it runs ONE fresh
live_quotes.run_probe() and re-checks -- this is the permanent fix for the
cold-start problem (a probe that predates today). If still not ok, the
capture refuses fail-closed (exit 1) rather than fetching against unverified
response schemas.

Reuses rather than reinvents: live_quotes' probe/session-gate machinery,
column-resolution helpers (_pick_col, _normalize_contract_keys via the
adapter), _assemble_chain_frame, resolve_expiries, iv_rank_preview,
_load_iv_history, and the per-day expirations/open-interest memos;
data.thetadata_adapter.passes_liquidity and mid_price;
options_researcher.chains.atm_row; data.atomic_io.atomic_parquet_write; and
research.hashing.config_hash for receipt provenance.

    uv run python -m options_researcher.intraday_capture --session-tag open
    uv run python -m options_researcher.intraday_capture --session-tag open --force
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import config
from data.atomic_io import atomic_parquet_write
from data.thetadata_adapter import _pick_col, mid_price, passes_liquidity
from options_researcher import live_quotes as lq
from options_researcher.chains import atm_row
from research.hashing import config_hash

NY_TZ = "America/New_York"
CACHE_DIR = Path(config.INTRADAY_CACHE_DIR)
RECEIPT_DIR = Path(config.INTRADAY_RECEIPT_DIR)


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

def ensure_probe_ok(client, now_ny: datetime, now_utc: datetime
                    ) -> tuple[dict | None, bool, bool, str]:
    """(probe, healed, ok, reason). If the existing probe already passes
    live_quotes.probe_ok, returns it unchanged (healed=False). Otherwise --
    since a capture run only calls this after confirming in_regular_session
    -- runs ONE fresh live_quotes.run_probe() and re-checks. Never runs a
    probe outside the regular session (mirrors run_probe's own refusal)."""
    probe = lq.load_latest_probe()
    ok, reason = lq.probe_ok(probe, now_utc)
    if ok:
        return probe, False, ok, reason
    if not lq.in_regular_session(now_ny):
        return probe, False, ok, reason
    probe = lq.run_probe(client=client, now_ny=now_ny)
    ok, reason = lq.probe_ok(probe, now_utc)
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


def _capture_symbol(client, symbol: str, spot_row: dict | None,
                    today: date, ny_iso: str) -> tuple[dict, pd.DataFrame | None]:
    """One name's descriptive capture row + its full nearest-monthly chain
    frame (or None on failure). Lets exceptions propagate -- the caller
    wraps this per symbol so one name's failure never aborts the board."""
    summary: dict = {"symbol": symbol, "status": "ok"}
    if spot_row is None:
        summary["spot_note"] = "symbol missing from batched stock snapshot"
    elif spot_row.get("error"):
        summary["spot_note"] = spot_row["error"]
    else:
        summary["spot_bid"] = spot_row["bid"]
        summary["spot_ask"] = spot_row["ask"]
        summary["spot_mid"] = spot_row["mid"]
        summary["spot_ts"] = (spot_row["ts"].isoformat()
                              if spot_row["ts"] is not None else None)

    exps = lq._expirations(client, symbol, ny_iso)
    monthly = lq.resolve_expiries(exps, today)["monthly"]
    if monthly is None:
        summary["status"] = "unavailable"
        summary["note"] = "no monthly expiry in the 15-60 DTE band"
        return summary, None

    g = client.option_snapshot_greeks_all(symbol, expiration=monthly)
    gf = lq._assemble_chain_frame(g, f"{symbol} greeks {monthly}", with_greeks=True)
    oi_map, oi_asof = lq._open_interest(client, symbol, monthly, ny_iso)

    admitted = {"C": 0, "P": 0}
    total = {"C": 0, "P": 0}
    spreads: list[float] = []
    rows: list[dict] = []
    for _, row in gf.iterrows():
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
        iv_val = lq._finite_or_none(row.get("iv"))
        delta_val = lq._finite_or_none(row.get("delta"))
        rows.append({
            "expiration": exp_iso, "strike": strike, "right": right,
            "bid": bid if bid is not None else float("nan"),
            "ask": ask if ask is not None else float("nan"),
            "iv": iv_val if iv_val is not None else float("nan"),
            "delta": delta_val if delta_val is not None else float("nan"),
            "open_interest": float(oi) if oi is not None else float("nan"),
            "admitted": bool(row_admitted),
        })
    chain_frame = pd.DataFrame(rows)

    atm = atm_row(gf, monthly)
    atm_iv = None
    if atm is not None:
        iv = lq._finite_or_none(atm["iv"])
        atm_iv = iv if iv is not None and iv > 0 else None

    ivr = (lq.iv_rank_preview(lq._load_iv_history(symbol), atm_iv)
           if atm_iv is not None else float("nan"))

    summary.update({
        "monthly_expiration": monthly.isoformat(),
        "atm_iv": atm_iv,
        "iv_rank_preview": lq._finite_or_none(ivr),
        "chain_contracts_total": total,
        "chain_contracts_admitted": admitted,
        "min_spread_pct_observed": min(spreads) if spreads else None,
        "open_interest_asof": oi_asof,
    })
    return summary, chain_frame


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
               else list(config.ATTRACTIVENESS_UNIVERSE))

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
        from data.thetadata_adapter import _client
        client = _client()

    today = now_ny.date()
    ny_iso = today.isoformat()

    spots: dict[str, dict] = {}
    spots_error: str | None = None
    try:
        spots = _stock_spots(client, universe, probe, now_utc)
    except Exception as exc:
        spots_error = f"{type(exc).__name__}: {exc}"

    names: dict[str, dict] = {}
    for sym in universe:
        try:
            row = None if spots_error is not None else spots.get(sym)
            summary, chain_frame = _capture_symbol(client, sym, row, today, ny_iso)
            if spots_error is not None:
                # More specific than the generic per-symbol "missing from
                # batched stock snapshot" note _capture_symbol set: the
                # WHOLE batch call raised, not just this one symbol's row.
                summary["spot_note"] = f"stock snapshot batch failed: {spots_error}"
        except Exception as exc:
            summary, chain_frame = (
                {"symbol": sym, "status": "unavailable",
                 "note": f"{type(exc).__name__}: {exc}"}, None)
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

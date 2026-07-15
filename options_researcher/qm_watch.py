"""QM daily watch -- read-only card view for the two QM mechanical signals.

    uv run python -m options_researcher.qm_watch [--as-of YYYY-MM-DD]

Spec: docs/superpowers/specs/2026-07-14-qm-signal-research-design.md §4.

For each of the 12 watch-universe names this evaluates the Breakout and
Parabolic signals (options_researcher.qm_signals) on the split-adjusted OHLCV
cache at the last completed session, and -- on a fire only -- prints option
candidate cards priced through the canonical adverse transforms
(data.pandas_feed.adverse_buy/adverse_sell), with per-leg liquidity flags from
data.thetadata_adapter.passes_liquidity.

Discipline (repo law):
- GATE FIRST: qm_signals.qm_prereg_gate() must clear before ANY data is
  touched (owner-typed QM_* values + both pre-registration facts, spec §7).
- A fire at the evaluation session means the SPEC §3 DEDUPED scan lists that
  session as its LAST entry -- a mid-streak continuation is NOT a new fire.
- Fails CLOSED per name: missing/stale OHLCV or (on a fire) a missing chain
  file prints a DATA-GAP line and moves on; nothing is silently skipped.
- stdout ONLY. This module never writes positions, receipts, facts, or any
  file, never reads or affects the H5/H6/H7 books, and has no --write path.
- Vocabulary discipline: these are UNVALIDATED descriptive screens, never
  edges/entries/verdicts. No forward evidence exists until the SS5 study.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable, Mapping

import pandas as pd

from data.pandas_feed import adverse_buy, adverse_sell, quote_valid
from data.thetadata_adapter import passes_liquidity
from options_researcher import qm_signals
from options_researcher.chains import load_range
from options_researcher.h7_scope import watch_universe
from options_researcher.h7_watch import evaluation_session

# Every fire block opens with this banner, verbatim (spec §4).
BANNER = (
    "UNVALIDATED SIGNAL -- descriptive screen; no forward evidence exists "
    "until the SS5 study reports; not an entry recommendation; no book path."
)

# OHLCV history start: deep enough for every trailing QM window on any name.
_OHLCV_START = "2017-01-01"


# --------------------------------------------------------------------------
# Default (real) dependency loaders. Each is injectable via main(...) so tests
# drive synthetic frames offline (tests/test_entry_watch.py injection pattern).
# data.underlying_ohlcv is imported LAZILY: it is built concurrently to this
# exact contract and must not be an import-time dependency of the module.
# --------------------------------------------------------------------------

def _load_adjusted(symbol: str, eval_iso: str) -> pd.DataFrame:
    """Split-adjusted OHLCV for signal math (spec §3 series). allow_oos=True:
    disclosed post-2022 look, same as every researcher profiler."""
    from data.underlying_ohlcv import load_ohlcv_adjusted

    return load_ohlcv_adjusted(symbol, _OHLCV_START, eval_iso, allow_oos=True)


def _load_raw(symbol: str, eval_iso: str) -> pd.DataFrame:
    """RAW (as-traded) OHLCV: aligned with raw option strikes -- the ONLY
    correct spot for strike/band math. allow_oos=True (disclosed look)."""
    from data.underlying_ohlcv import load_ohlcv

    return load_ohlcv(symbol, _OHLCV_START, eval_iso, allow_oos=True)


def _load_chain(symbol: str, eval_iso: str) -> pd.DataFrame | None:
    """The evaluation session's cached chain, or None when no file exists."""
    return load_range(symbol, eval_iso, eval_iso, allow_oos=True).get(eval_iso)


# --------------------------------------------------------------------------
# Pure card builders (unit-tested directly against fixture chains).
# --------------------------------------------------------------------------

def _badge(name: str, flag: bool) -> str:
    return f"{name}:{'GREEN' if flag else 'RED'}"


def long_option_cards(
    chain: pd.DataFrame, right: str, raw_close: float, eval_iso: str,
    dte_band: tuple[int, int], ntm_band: float,
) -> list[dict[str, Any]]:
    """Near-ATM long single-leg candidates (CALL on a Breakout, PUT on a
    Parabolic). Rows are filtered ONLY on sane quotes and the DTE / near-the-
    money bands -- liquidity is SHOWN via passes_liquidity, never used to
    exclude a card (spec §4 wants the flag visible). Cost is the canonical
    adverse BUY price x100; breakeven walks the premium away from the strike
    (up for a call, down for a put)."""
    today = date.fromisoformat(eval_iso)
    lo_dte, hi_dte = int(dte_band[0]), int(dte_band[1])
    lo_k, hi_k = raw_close * (1 - ntm_band), raw_close * (1 + ntm_band)
    sane = chain[(chain["right"] == right) & (chain["bid"] > 0)
                 & (chain["ask"] >= chain["bid"])]
    cards: list[dict[str, Any]] = []
    for _, r in sane.iterrows():
        strike = float(r["strike"])
        if not (lo_k <= strike <= hi_k):
            continue
        exp = date.fromisoformat(str(r["expiration"]))
        dte = (exp - today).days
        if not (lo_dte <= dte <= hi_dte):
            continue
        bid, ask = float(r["bid"]), float(r["ask"])
        premium = adverse_buy(ask)
        breakeven = strike + premium if right == "C" else strike - premium
        cards.append({
            "right": right, "strike": strike, "expiry": str(r["expiration"]),
            "dte": dte, "bid": bid, "ask": ask,
            "cost": premium * 100.0, "breakeven": breakeven,
            "liq": passes_liquidity(r["open_interest"], bid, ask),
        })
    cards.sort(key=lambda c: (c["expiry"], c["strike"]))
    return cards


def debit_spread_cards(
    chain: pd.DataFrame, right: str, raw_close: float, eval_iso: str,
    dte_band: tuple[int, int], ntm_band: float,
) -> list[dict[str, Any]]:
    """Debit-spread candidates: long THE near-ATM strike (closest to raw
    close, within the band) and short the next listed strike ABOVE it for a
    call spread / BELOW it for a put spread, same expiration. Net cost is the
    adverse BUY of the long leg minus the adverse SELL of the short leg,
    reported as computed (never negative-clipped). A pair is skipped when
    either leg's quote is not a usable book (quote_valid). Both legs' liquidity
    flags are shown."""
    today = date.fromisoformat(eval_iso)
    lo_dte, hi_dte = int(dte_band[0]), int(dte_band[1])
    lo_k, hi_k = raw_close * (1 - ntm_band), raw_close * (1 + ntm_band)
    cards: list[dict[str, Any]] = []
    right_rows = chain[chain["right"] == right]
    for exp_str, grp in right_rows.groupby("expiration"):
        exp = date.fromisoformat(str(exp_str))
        dte = (exp - today).days
        if not (lo_dte <= dte <= hi_dte):
            continue
        by_strike = {float(r["strike"]): r for _, r in grp.iterrows()}
        strikes = sorted(by_strike)
        band = [k for k in strikes if lo_k <= k <= hi_k]
        if not band:
            continue
        long_k = min(band, key=lambda k: abs(k - raw_close))
        if right == "C":
            neighbours = [k for k in strikes if k > long_k]
            short_k = neighbours[0] if neighbours else None
        else:
            neighbours = [k for k in strikes if k < long_k]
            short_k = neighbours[-1] if neighbours else None
        if short_k is None:
            continue
        lr, sr = by_strike[long_k], by_strike[short_k]
        if not quote_valid(lr["bid"], lr["ask"]) or not quote_valid(sr["bid"], sr["ask"]):
            continue
        net = adverse_buy(lr["ask"]) - adverse_sell(sr["bid"])
        breakeven = long_k + net if right == "C" else long_k - net
        cards.append({
            "right": right, "long_strike": long_k, "short_strike": short_k,
            "expiry": str(exp_str), "dte": dte, "net_cost": net,
            "max_value": abs(short_k - long_k), "breakeven": breakeven,
            "long_liq": passes_liquidity(lr["open_interest"], lr["bid"], lr["ask"]),
            "short_liq": passes_liquidity(sr["open_interest"], sr["bid"], sr["ask"]),
        })
    cards.sort(key=lambda c: c["expiry"])
    return cards


# --------------------------------------------------------------------------
# Per-name state machine.
# --------------------------------------------------------------------------

def _last_iso(frame: pd.DataFrame) -> str:
    return str(frame.index[-1])[:10]


def assemble_name(
    symbol: str, frame_adj: pd.DataFrame | None, frame_raw: pd.DataFrame | None,
    chain_or_none: pd.DataFrame | None, eval_iso: str, params: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve ONE name to a card dict. States (spec §4):

    NO-DATA         -- OHLCV cache missing/empty (fail closed).
    STALE           -- OHLCV present but not ending exactly at the session.
    NO-SIGNAL       -- neither signal fires at the session.
    FIRE-BREAKOUT   -- Breakout (long) fires; CALL cards attached.
    FIRE-PARABOLIC  -- Parabolic (fade) fires; PUT cards attached.
    FIRE-NO-CHAIN   -- a signal fires but the session chain file is missing.

    When both signals fire the same session (structurally near-exclusive --
    a tight low-volume base vs a vertical run), Breakout takes precedence and
    the Parabolic is not separately reported.
    """
    if frame_adj is None or frame_raw is None or frame_adj.empty or frame_raw.empty:
        return {"symbol": symbol, "state": "NO-DATA",
                "reason": "no cached OHLCV (run the OHLCV cache builder)"}
    last_adj, last_raw = _last_iso(frame_adj), _last_iso(frame_raw)
    if last_adj != eval_iso or last_raw != eval_iso:
        stray = last_adj if last_adj != eval_iso else last_raw
        rel = "after" if stray > eval_iso else "before"
        return {"symbol": symbol, "state": "STALE",
                "reason": (f"OHLCV ends {stray}, {rel} session {eval_iso} "
                           "-- stale/misaligned cache (run the OHLCV top-up)")}

    b_fires = qm_signals.breakout_fires(frame_adj, params)
    p_fires = qm_signals.parabolic_fires(frame_adj, params)
    breakout = bool(b_fires) and b_fires[-1]["t"] == eval_iso
    parabolic = bool(p_fires) and p_fires[-1] == eval_iso
    if not breakout and not parabolic:
        return {"symbol": symbol, "state": "NO-SIGNAL"}

    right = "C" if breakout else "P"
    state = "FIRE-BREAKOUT" if breakout else "FIRE-PARABOLIC"
    label = None if breakout else "FADE SIGNAL"
    if chain_or_none is None:
        return {"symbol": symbol, "state": "FIRE-NO-CHAIN", "right": right,
                "label": label,
                "reason": f"no cached chain file for {eval_iso}"}

    raw_close = float(frame_raw["close"].iloc[-1])
    dte_band = params["QM_TRADABILITY_DTE"]
    ntm_band = float(params["QM_NTM_BAND"])
    return {
        "symbol": symbol, "state": state, "right": right, "label": label,
        "raw_close": raw_close,
        "long_cards": long_option_cards(chain_or_none, right, raw_close,
                                        eval_iso, dte_band, ntm_band),
        "spread_cards": debit_spread_cards(chain_or_none, right, raw_close,
                                           eval_iso, dte_band, ntm_band),
    }


# --------------------------------------------------------------------------
# Rendering (dict -> text). Pure; returns a newline-joined block.
# --------------------------------------------------------------------------

def _long_line(c: dict[str, Any]) -> str:
    kind = "LONG CALL" if c["right"] == "C" else "LONG PUT"
    return (f"    {kind} ${c['strike']:.0f} {c['expiry']} ({c['dte']}d): "
            f"bid ${c['bid']:.2f}/ask ${c['ask']:.2f} cost ${c['cost']:,.0f} "
            f"breakeven ${c['breakeven']:.2f} [{_badge('liq', c['liq'])}]")


def _spread_line(c: dict[str, Any]) -> str:
    kind = "CALL DEBIT SPREAD" if c["right"] == "C" else "PUT DEBIT SPREAD"
    return (f"    {kind} +${c['long_strike']:.0f}/-${c['short_strike']:.0f} "
            f"{c['expiry']} ({c['dte']}d): net ${c['net_cost']:.2f} "
            f"max ${c['max_value']:.2f} breakeven ${c['breakeven']:.2f} "
            f"[{_badge('long_liq', c['long_liq'])} "
            f"{_badge('short_liq', c['short_liq'])}]")


def render(card: dict[str, Any], eval_iso: str) -> str:
    sym, state = card["symbol"], card["state"]
    if state == "NO-DATA":
        return f"{sym}: DATA-GAP -- {card['reason']}"
    if state == "STALE":
        return f"{sym}: DATA-GAP -- {card['reason']}"
    if state == "NO-SIGNAL":
        return f"{sym}: no signal"

    # Every fire block (including FIRE-NO-CHAIN) opens with the banner verbatim.
    lines = [BANNER]
    signal = "BREAKOUT" if state == "FIRE-BREAKOUT" else "PARABOLIC"
    tag = f" [{card['label']}]" if card.get("label") else ""
    if state == "FIRE-NO-CHAIN":
        lines.append(f"{sym}: {signal} FIRE{tag} session {eval_iso} -- "
                     f"DATA-GAP ({card['reason']}); no cards")
        return "\n".join(lines)

    side = "long-side signal" if signal == "BREAKOUT" else "fade signal"
    lines.append(f"{sym}: {signal} FIRE{tag} ({side}) session {eval_iso}, "
                 f"raw close ${card['raw_close']:.2f}")
    for c in card["long_cards"]:
        lines.append(_long_line(c))
    for c in card["spread_cards"]:
        lines.append(_spread_line(c))
    if not card["long_cards"] and not card["spread_cards"]:
        lines.append("    no near-ATM contract in the tradability DTE band "
                     "this session")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None, *,
         universe: list[str] | None = None,
         load_adjusted: Callable[[str, str], pd.DataFrame | None] | None = None,
         load_raw: Callable[[str, str], pd.DataFrame | None] | None = None,
         load_chain: Callable[[str, str], pd.DataFrame | None] | None = None,
         params: Mapping[str, Any] | None = None,
         gate: Callable[[], str | None] | None = None) -> int:
    import argparse
    from datetime import datetime
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(
        description="QM daily watch (UNVALIDATED descriptive screen; alerts "
                    "only, never trades)")
    parser.add_argument(
        "--as-of",
        help="evaluate the last completed session before this date "
             "(default: today, America/New_York)")
    args = parser.parse_args(argv)

    # GATE FIRST (spec §7): refuse before touching any data.
    gate = gate or qm_signals.qm_prereg_gate
    reason = gate()
    if reason is not None:
        print(reason)
        return 2

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    run_date = date.fromisoformat(args.as_of) if args.as_of else ny_today
    if run_date > ny_today:
        print(f"--as-of {run_date} is in the future; refusing.")
        return 2
    eval_iso = evaluation_session(run_date).isoformat()

    universe = watch_universe() if universe is None else universe
    params = qm_signals.qm_params() if params is None else params
    load_adjusted = load_adjusted or _load_adjusted
    load_raw = load_raw or _load_raw
    load_chain = load_chain or _load_chain

    print(f"QM WATCH session={eval_iso} run={run_date.isoformat()} "
          "(UNVALIDATED descriptive screen; signals + candidate cards only; "
          "no book, no receipt, no verdict; alerts only, never trades)")
    for symbol in universe:
        try:
            frame_adj = load_adjusted(symbol, eval_iso)
        except Exception:
            frame_adj = None
        try:
            frame_raw = load_raw(symbol, eval_iso)
        except Exception:
            frame_raw = None
        try:
            chain = load_chain(symbol, eval_iso)
        except Exception:
            chain = None
        card = assemble_name(symbol, frame_adj, frame_raw, chain, eval_iso, params)
        print(render(card, eval_iso))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

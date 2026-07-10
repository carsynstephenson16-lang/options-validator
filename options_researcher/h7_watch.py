"""H7 daily watcher -- reports lane states per name; NEVER trades, never
mutates positions (candidate -> position only via the owner editing
data/positions/, same as H5). Run: uv run python -m options_researcher.h7_watch

Lane states: EXCLUDED (config) / WATCH-ONLY (admission fail) / QUIET (no
signal or dead-zone IV) / EARNINGS-BAN / POSITION-OPEN / ENTRY-OK. ENTRY-OK
additionally reports the IV route (call / spread / h7c). Data gaps print as
DATA-GAP lines and are skipped, never papered over (EOD-gap house rule).
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import config
from data.underlying_closes import adjustment_factor, load_closes_adjusted
from options_researcher import h7_signals as sig
from options_researcher.chains import load_range
from options_researcher.h7_earnings import entries_banned, load_calendar

H7_POSITIONS_PATH = Path("data/positions/h7_positions.csv")


def _lane_state(*, armed: bool, admitted: bool, banned: bool, has_open: bool,
                route: str, budget_left: float, basket_full: bool) -> str:
    if has_open:
        return "POSITION-OPEN"
    if banned:
        return "EARNINGS-BAN"
    if not admitted:
        return "WATCH-ONLY"
    if not armed or route == "none":
        return "QUIET"
    if basket_full:
        return "BASKET-CAP"      # H7C_MAX_CONCURRENT reached (review R10)
    if budget_left <= 0:
        return "BUDGET-SPENT"    # monthly sleeve exhausted (review R10)
    return "ENTRY-OK"


def assemble_name(*, symbol: str, closes: pd.Series, chain: pd.DataFrame,
                  today: date, calendar: dict, open_positions: tuple,
                  spot: float | None = None, open_h7c: int = 0,
                  month_spent: float = 0.0) -> dict:
    """`closes` MUST be split-adjusted (signals); `spot` is the RAW price
    aligned with the chain's strikes -- defaults to the last adjusted close,
    which is only correct after a symbol's final split (live use)."""
    spot = float(closes.iloc[-1]) if spot is None else float(spot)
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = sig.atm_iv_90d(chain, spot, today)
    route = sig.iv_route(iv=iv, rv=rv)
    banned = entries_banned(symbol, today, calendar)
    has_open = symbol in open_positions
    budget_left = config.H7_MONTHLY_AT_RISK - month_spent

    card: dict = {
        "symbol": symbol, "spot": spot, "rv21": rv, "iv90": iv, "route": route,
        "budget_left": budget_left,
        "benchmark_note": (
            f"underlying move is logged alongside every paper trade "
            f"(spot ref {spot:.2f} @ {today.isoformat()})"
        ),
    }
    lanes = (
        ("lane_a", sig.lane_a_armed, config.H7_LONG_DTE_BAND),
        ("lane_b", sig.lane_b_armed, config.H7_LONG_DTE_BAND),
        ("lane_c", sig.lane_a_armed, config.H7C_DTE_BAND),  # c shares a's stabilization
    )
    for lane, armed_fn, band in lanes:
        if lane == "lane_c" and symbol in config.H7_CORE_LONG_ONLY:
            card[lane] = {"state": "EXCLUDED", "route": "none",
                          "admitted_contracts": 0}
            continue
        admitted, n = sig.lane_admission(
            chain, spot=spot, today=today, dte_band=band,
            right="P" if lane == "lane_c" else "C",
        )
        if lane == "lane_c":
            lane_route = "h7c" if route == "h7c" else "none"
            basket_full = open_h7c >= config.H7C_MAX_CONCURRENT
        else:
            lane_route = "none" if route == "h7c" else route
            basket_full = False
        card[lane] = {
            "state": _lane_state(armed=armed_fn(closes), admitted=admitted,
                                 banned=banned, has_open=has_open,
                                 route=lane_route, budget_left=budget_left,
                                 basket_full=basket_full),
            "admitted_contracts": n,
            "route": lane_route,
        }
    return card


def _open_h7_positions(today: date) -> tuple[tuple, int, float]:
    """(symbols, open lane-c count, at-risk opened this calendar month) from
    the H7 paper book. H5/H6 books are separate files -- matching on
    positions.csv conflated the hypotheses' one-per-underlying rules (R11)."""
    symbols, open_c, month_spent = set(), 0, 0.0
    month = today.isoformat()[:7]
    try:
        with H7_POSITIONS_PATH.open() as f:
            for row in csv.DictReader(f):
                sym = (row.get("symbol") or "").upper()
                if not sym:
                    continue
                symbols.add(sym)
                if (row.get("lane") or "").lower() == "c":
                    open_c += 1
                if (row.get("opened") or "").startswith(month):
                    month_spent += float(row.get("at_risk") or 0.0)
    except OSError:
        pass
    return tuple(symbols), open_c, month_spent


def main() -> int:
    today = date.today()
    today_iso = today.isoformat()
    # 252 trading sessions of signal history plus weekend/holiday slack
    start_iso = (today - timedelta(days=560)).isoformat()
    calendar = load_calendar()
    open_syms, open_c, month_spent = _open_h7_positions(today)
    names = [s for s in config.H7_WATCHLIST + config.H7_CORE_LONG_ONLY
             if s not in config.H7_EXCLUDED]
    print(f"H7 WATCH {today_iso} (registered f1887c9d; alerts only, never trades)")
    print(f"sleeve: ${config.H7_MONTHLY_AT_RISK - month_spent:.0f} of "
          f"${config.H7_MONTHLY_AT_RISK} left this month; "
          f"open H7c {open_c}/{config.H7C_MAX_CONCURRENT}")
    for symbol in names:
        try:
            closes = load_closes_adjusted(symbol, start_iso, today_iso,
                                          allow_oos=True)
            if closes.empty:
                raise RuntimeError("no cached underlying closes")  # R12
            chains_by_day = load_range(symbol, today_iso, today_iso, allow_oos=True)
            chain = chains_by_day.get(today_iso)
            if chain is None:
                # fall back to the latest cached chain day this week, disclosed
                recent = load_range(
                    symbol,
                    (pd.Timestamp(today) - pd.Timedelta(days=6)).date().isoformat(),
                    today_iso, allow_oos=True,
                )
                if not recent:
                    raise RuntimeError("no cached chain in the last 6 days")
                last_day = max(recent)
                chain = recent[last_day]
                print(f"{symbol}: note chain as of {last_day} (cache lag)")
        except Exception as e:  # a gap is a report line, not a crash
            print(f"{symbol}: DATA-GAP ({type(e).__name__}: {e}) -- skipped")
            continue
        raw_spot = float(closes.iloc[-1]) * adjustment_factor(symbol, today_iso)
        card = assemble_name(symbol=symbol, closes=closes, chain=chain,
                             today=today, calendar=calendar,
                             open_positions=open_syms, spot=raw_spot,
                             open_h7c=open_c, month_spent=month_spent)
        print(
            f"{symbol}: spot {card['spot']:.2f} IV90 {card['iv90']:.0%} "
            f"RV21 {card['rv21']:.0%} route={card['route']} | "
            f"a={card['lane_a']['state']} b={card['lane_b']['state']} "
            f"c={card['lane_c']['state']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

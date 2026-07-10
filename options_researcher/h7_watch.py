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
from datetime import date
from pathlib import Path

import pandas as pd

import config
from data.underlying_closes import load_closes
from options_researcher import h7_signals as sig
from options_researcher.chains import load_range
from options_researcher.h7_earnings import entries_banned, load_calendar

_IV90_DTE_BAND = (72, 108)  # +/-18d around the registration's ~90d IV measure


def _lane_state(*, armed: bool, admitted: bool, banned: bool,
                has_open: bool, route: str) -> str:
    if has_open:
        return "POSITION-OPEN"
    if banned:
        return "EARNINGS-BAN"
    if not admitted:
        return "WATCH-ONLY"
    if not armed or route == "none":
        return "QUIET"
    return "ENTRY-OK"


def _atm_iv_90d(chain: pd.DataFrame, spot: float, today: date) -> float:
    df = chain[(chain.right == "C") & (chain.bid > 0) & (chain.ask > 0)].copy()
    if df.empty:
        return 0.0
    exp = pd.to_datetime(df.expiration).dt.date
    df = df.assign(dte=exp.map(lambda d: (d - today).days))
    df = df[df.dte.between(*_IV90_DTE_BAND)]
    if df.empty:
        return 0.0
    row = df.loc[(df.strike - spot).abs().idxmin()]
    return float(row.iv)


def assemble_name(*, symbol: str, closes: pd.Series, chain: pd.DataFrame,
                  today: date, calendar: dict, open_positions: tuple) -> dict:
    spot = float(closes.iloc[-1])
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = _atm_iv_90d(chain, spot, today)
    route = sig.iv_route(iv=iv, rv=rv)
    banned = entries_banned(symbol, today, calendar)
    has_open = symbol in open_positions

    card: dict = {
        "symbol": symbol, "spot": spot, "rv21": rv, "iv90": iv, "route": route,
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
        else:
            lane_route = "none" if route == "h7c" else route
        card[lane] = {
            "state": _lane_state(armed=armed_fn(closes), admitted=admitted,
                                 banned=banned, has_open=has_open,
                                 route=lane_route),
            "admitted_contracts": n,
            "route": lane_route,
        }
    return card


def _open_position_symbols() -> tuple:
    path = Path("data/positions/positions.csv")
    try:
        with path.open() as f:
            return tuple({row["symbol"].upper() for row in csv.DictReader(f)})
    except (OSError, KeyError):
        return ()


def main() -> int:
    today = date.today()
    today_iso = today.isoformat()
    calendar = load_calendar()
    open_syms = _open_position_symbols()
    names = [s for s in config.H7_WATCHLIST + config.H7_CORE_LONG_ONLY
             if s not in config.H7_EXCLUDED]
    print(f"H7 WATCH {today_iso} (registered f1887c9d; alerts only, never trades)")
    for symbol in names:
        try:
            closes = load_closes(symbol, "2024-01-01", today_iso, allow_oos=True)
            chains_by_day = load_range(symbol, today_iso, today_iso, allow_oos=True)
            chain = chains_by_day.get(today_iso)
            if chain is None or closes.empty:
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
        card = assemble_name(symbol=symbol, closes=closes, chain=chain,
                             today=today, calendar=calendar,
                             open_positions=open_syms)
        print(
            f"{symbol}: spot {card['spot']:.2f} IV90 {card['iv90']:.0%} "
            f"RV21 {card['rv21']:.0%} route={card['route']} | "
            f"a={card['lane_a']['state']} b={card['lane_b']['state']} "
            f"c={card['lane_c']['state']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

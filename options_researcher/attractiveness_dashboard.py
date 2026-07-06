"""options_researcher/attractiveness_dashboard.py -- interactive scenario
view over attractiveness candidates.

assemble() gathers the SAME candidates attractiveness.py prints (via its
card-builder functions, unmodified) and attaches an at-expiration payoff
table per candidate. render() turns that into one self-contained HTML
string (reusing dashboard.py's dark CSS; no network, no JS framework, no
options-pricing model). main() writes .tmp/dashboard/attractiveness.html.

Every payoff number is computed AT EXPIRATION from intrinsic value only --
there is deliberately no Black-Scholes / time-value model anywhere here.
"""
from __future__ import annotations

import math
import os

OUTPUT_PATH = os.path.join(".tmp", "dashboard", "attractiveness.html")

_PMCC_NOTE = "just the premium; LEAPS value not counted"


def _round_cents(x: float) -> float:
    return round(float(x), 2)


def _price_ladder(*, close: float, rv21: float, strike: float,
                  breakeven: float | None) -> list[dict]:
    """Ascending, deduped, positive-only price rows with anchor tags.

    Uses +/-1 and +/-2 monthly moves around close when rv21 gives a finite
    positive monthly move; otherwise falls back to close/strike/breakeven
    only (never invents points from a bad vol number)."""
    monthly = rv21 / math.sqrt(12.0) if rv21 and rv21 > 0 else float("nan")
    tagged: dict[float, str] = {}

    def put(price: float, tag: str) -> None:
        p = _round_cents(price)
        if p <= 0:
            return
        existing = tagged.get(p)
        if existing is None:
            tagged[p] = tag
        elif tag and tag not in existing.split(", "):
            # An anchor tag joins the row: replace a prior untagged move-point
            # placeholder, or combine when two anchors coincide to the penny
            # (e.g. strike == breakeven) so no label is silently dropped.
            tagged[p] = tag if not existing else f"{existing}, {tag}"

    if monthly == monthly and monthly > 0:  # finite, positive
        for k in (-2, -1, 1, 2):
            put(close * (1 + k * monthly), "")
    put(close, "today")
    put(strike, "strike")
    if breakeven is not None:
        put(breakeven, "breakeven")
    return [{"price": p, "tag": tagged[p]} for p in sorted(tagged)]


def _put_pnl(price: float, strike: float, credit: float) -> float:
    return credit - max(0.0, strike - price) * 100.0


def _cc_pnl(price: float, strike: float, credit: float, close: float) -> float:
    return credit + 100.0 * (min(price, strike) - close)


def _pmcc_pnl(price: float, short_strike: float, leaps_strike: float,
              leaps_cost: float, credit: float) -> tuple[float, str]:
    if price >= short_strike:
        return ((short_strike - leaps_strike) * 100.0 - leaps_cost + credit, "")
    return (credit, _PMCC_NOTE)


def _leaps_pnl(price: float, strike: float, cost: float) -> float:
    return max(0.0, price - strike) * 100.0 - cost


def scenario_rows(card: dict, structure: str, *, close: float,
                  rv21: float) -> list[dict]:
    """At-expiration payoff rows for one candidate. `structure` is one of
    'put', 'cc', 'pmcc', 'leaps'."""
    strike = float(card["strike"])
    if structure == "put":
        credit = float(card["credit"])
        breakeven = strike - credit / 100.0
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=breakeven)
        return [{**row, "pnl": _round_cents(_put_pnl(row["price"], strike,
                                                     credit)), "note": ""}
                for row in ladder]
    if structure == "cc":
        credit = float(card["credit"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=None)
        return [{**row, "pnl": _round_cents(_cc_pnl(row["price"], strike,
                                                    credit, close)), "note": ""}
                for row in ladder]
    if structure == "pmcc":
        credit = float(card["credit"])
        lk, lc = float(card["leaps_strike"]), float(card["leaps_cost"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=None)
        out = []
        for row in ladder:
            pnl, note = _pmcc_pnl(row["price"], strike, lk, lc, credit)
            out.append({**row, "pnl": _round_cents(pnl), "note": note})
        return out
    if structure == "leaps":
        cost = float(card["cost"])
        breakeven = float(card["breakeven"])
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=breakeven)
        return [{**row, "pnl": _round_cents(_leaps_pnl(row["price"], strike,
                                                      cost)), "note": ""}
                for row in ladder]
    raise ValueError(f"unknown structure {structure!r}")


def _headline(symbol: str, kind: str, card: dict) -> str:
    verbs = {"put": "Sell the {sym} ${k:.0f} put",
             "cc": "Sell the {sym} ${k:.0f} covered call",
             "pmcc": "Sell the {sym} ${k:.0f} call vs your LEAPS",
             "leaps": "Buy the {sym} ${k:.0f} LEAPS"}
    k = float(card["strike"])
    lead = verbs[kind].format(sym=symbol, k=k)
    if kind == "leaps":
        money = f"costs ${float(card['cost']):,.0f}"
    else:
        money = f"collect ${float(card['credit']):,.0f} now"
    return (f"{lead} — {money} — result by {card['expiry']} "
            f"({card['dte']} days out)")


def _countdown(card: dict) -> str:
    import config
    dte = int(card["dte"])
    roll = config.H4_THESIS_ROLL_DTE
    return (f"{dte} days until expiration · roll reminder kicks in with "
            f"{roll} days left")


def assemble(*, symbol_sections: list[dict] | None = None,
             rv21_by_symbol: dict[str, float] | None = None) -> dict:
    """Attach scenario tables + headlines to gathered candidate sections.

    Both arguments default to the real project state (see _gather_all);
    inject them to unit-test without touching disk or the network."""
    if symbol_sections is None:
        symbol_sections, rv21_by_symbol = _gather_all()
    rv21_by_symbol = rv21_by_symbol or {}

    out_symbols = []
    for sec in symbol_sections:
        sym = sec["symbol"]
        rv21 = float(rv21_by_symbol.get(sym, float("nan")))
        out_groups = []
        for grp in sec["groups"]:
            kind = grp["kind"]
            cards = []
            for card in grp["cards"]:
                if "skipped" in card:
                    cards.append({**card, "scenarios": [], "headline": "",
                                  "countdown": ""})
                    continue
                enriched = dict(card)
                if kind == "pmcc":
                    enriched["leaps_strike"] = float(grp["leaps_strike"])
                    enriched["leaps_cost"] = float(grp["leaps_premium"]) * 100.0
                enriched["scenarios"] = scenario_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["headline"] = _headline(sym, kind, enriched)
                enriched["countdown"] = (_countdown(enriched)
                                         if kind == "leaps" else "")
                cards.append(enriched)
            out_groups.append({"kind": kind, "title": grp["title"],
                               "cards": cards, "empty": grp.get("empty")})
        out_symbols.append({"symbol": sym, "close": float(sec["close"]),
                            "iv_rank": float(sec["iv_rank"]),
                            "as_of": sec["as_of"], "groups": out_groups})
    return {"symbols": out_symbols}


def _gather_all() -> tuple[list[dict], dict[str, float]]:
    """Load real per-symbol candidate sections + rv21, mirroring
    attractiveness.main()'s data gathering (no printing)."""
    import glob
    from datetime import date

    import pandas as pd

    import config
    from data.underlying_closes import load_closes
    from options_researcher.attractiveness import (
        cc_card_rows,
        leaps_card_rows,
        pmcc_card_rows,
        put_card_rows,
    )
    from options_researcher.chains import nearest_monthly
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from options_researcher.portfolio import HOLDINGS_PATH, load_holdings, load_positions

    holdings = (load_holdings() if os.path.exists(HOLDINGS_PATH)
                else pd.DataFrame(columns=["symbol", "shares", "cost_basis"]))
    positions = load_positions()
    thesis_used = 0.0
    held_leaps: dict[str, tuple[float, float]] = {}
    if not positions.empty:
        t = positions[positions["bucket"] == "thesis"]
        thesis_used = float((t["entry_price"] * 100 * t["contracts"]).sum())
        for _, lp in positions[positions["structure"] == "leaps_call"].iterrows():
            held_leaps.setdefault(lp["symbol"],
                                  (float(lp["strike"]), float(lp["entry_price"])))
    bucket_room = config.H4_THESIS_MAX_PREMIUM_TOTAL - thesis_used

    sections: list[dict] = []
    rv21_by_symbol: dict[str, float] = {}
    for symbol in config.UNIVERSE:
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        if not files:
            continue
        day = os.path.basename(files[-1]).split("_")[1].replace(".parquet", "")
        chain = pd.read_parquet(files[-1])
        row = load_features(symbol).iloc[-1]
        close = float(load_closes(symbol, "2018-01-01", day,
                                  allow_oos=True).iloc[-1])
        rv21 = float(row["rv21"])
        rv21_by_symbol[symbol] = rv21
        iv_rank = float(row["iv_rank"]) if pd.notna(row["iv_rank"]) else 0.0
        exp = nearest_monthly(chain, date.fromisoformat(day))
        earn_in_cycle = bool(exp is not None and any(
            date.fromisoformat(day) < e <= exp for e in load_earnings(symbol)))

        put_cards = put_card_rows(symbol, chain, day, close=close, rv21=rv21,
                                  iv_rank=iv_rank, earnings_in_cycle=earn_in_cycle)
        groups: list[dict] = [
            {"kind": "put", "title": "SELL A PUT? (promise to buy lower)",
             "cards": put_cards,
             "empty": None if put_cards
             else "no candidates near the target delta this cycle"}]

        lot = holdings[holdings["symbol"] == symbol] if len(holdings) else []
        if len(lot) and int(lot.iloc[0]["shares"]) >= 100:
            groups.append({"kind": "cc",
                           "title": "SELL A COVERED CALL? (rent out your shares)",
                           "cards": cc_card_rows(
                               symbol, chain, day, close=close,
                               cost_basis=float(lot.iloc[0]["cost_basis"]),
                               iv_rank=iv_rank,
                               earnings_in_cycle=earn_in_cycle),
                           "empty": None})
        if symbol in held_leaps:
            lk, lp = held_leaps[symbol]
            groups.append({"kind": "pmcc",
                           "title": "SELL A CALL AGAINST YOUR LEAPS? (PMCC)",
                           "leaps_strike": lk, "leaps_premium": lp,
                           "cards": pmcc_card_rows(
                               symbol, chain, day, leaps_strike=lk,
                               leaps_premium=lp, close=close, iv_rank=iv_rank,
                               earnings_in_cycle=earn_in_cycle),
                           "empty": None})
        if symbol in config.H4_THESIS_NAMES:
            groups.append({"kind": "leaps",
                           "title": f"BUY A LEAPS? (bucket room ${bucket_room:,.0f})",
                           "cards": leaps_card_rows(symbol, chain, day,
                                                    close=close, iv_rank=iv_rank,
                                                    bucket_room=bucket_room),
                           "empty": None})

        sections.append({"symbol": symbol, "as_of": day, "close": close,
                         "iv_rank": iv_rank, "groups": groups})
    return sections, rv21_by_symbol

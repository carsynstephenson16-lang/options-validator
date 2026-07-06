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

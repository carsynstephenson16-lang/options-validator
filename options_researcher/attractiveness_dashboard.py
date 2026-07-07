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

import html as _html
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
    if structure in ("leaps", "long_call"):
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
             "leaps": "Buy the {sym} ${k:.0f} LEAPS",
             "long_call": "Buy the {sym} ${k:.0f} call"}
    k = float(card["strike"])
    lead = verbs[kind].format(sym=symbol, k=k)
    if kind in ("leaps", "long_call"):
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
                # shallow copy: nested dicts (e.g. grades) are shared, not
                # duplicated -- fine because nothing here mutates them in place.
                enriched = dict(card)
                if kind == "pmcc":
                    enriched["leaps_strike"] = float(grp["leaps_strike"])
                    enriched["leaps_cost"] = float(grp["leaps_premium"]) * 100.0
                enriched["scenarios"] = scenario_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["headline"] = _headline(sym, kind, enriched)
                enriched["countdown"] = (_countdown(enriched)
                                         if kind in ("leaps", "long_call")
                                         else "")
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
        long_call_card_rows,
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
        iv_minus_rv = (float(row["iv_minus_rv"])
                       if pd.notna(row["iv_minus_rv"]) else 0.0)
        exp = nearest_monthly(chain, date.fromisoformat(day))
        earn_in_cycle = bool(exp is not None and any(
            date.fromisoformat(day) < e <= exp for e in load_earnings(symbol)))

        put_cards = put_card_rows(symbol, chain, day, close=close, rv21=rv21,
                                  iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                                  earnings_in_cycle=earn_in_cycle)
        groups: list[dict] = [
            {"kind": "put", "title": "SELL A PUT? (promise to buy lower)",
             "cards": put_cards,
             "empty": None if put_cards
             else "no candidates near the target delta this cycle"}]

        lot = holdings[holdings["symbol"] == symbol] if len(holdings) else []
        held_shares = int(lot.iloc[0]["shares"]) if len(lot) else 0
        if held_shares >= 100:
            groups.append({"kind": "cc",
                           "title": "SELL A COVERED CALL? (rent out your shares)",
                           "cards": cc_card_rows(
                               symbol, chain, day, close=close,
                               cost_basis=float(lot.iloc[0]["cost_basis"]),
                               iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                               earnings_in_cycle=earn_in_cycle),
                           "empty": None})
        elif held_shares > 0:
            groups.append({"kind": "cc",
                           "title": "SELL A COVERED CALL? (rent out your shares)",
                           "cards": [],
                           "empty": (f"you hold {held_shares} sh of {symbol} -- a "
                                     "covered call needs 100 per contract. "
                                     "Covered-call rows appear after a declared "
                                     "100-share lot; PMCC rows appear only after "
                                     "a real LEAPS is recorded.")})
        if symbol in held_leaps:
            lk, lp = held_leaps[symbol]
            pmcc_cards = pmcc_card_rows(
                symbol, chain, day, leaps_strike=lk, leaps_premium=lp,
                close=close, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                earnings_in_cycle=earn_in_cycle)
            groups.append({"kind": "pmcc",
                           "title": "SELL A CALL AGAINST YOUR LEAPS? (PMCC)",
                           "leaps_strike": lk, "leaps_premium": lp,
                           "cards": pmcc_cards,
                           "empty": None if pmcc_cards else
                           (f"no SAFE strike this cycle: the rule needs a call "
                            f"at ${lk + lp:.2f}+ and none is listed / all too "
                            "far out to pay -- selling closer would risk locking "
                            "a loss, so H5 shows nothing.")})
        if symbol in config.H4_THESIS_NAMES:
            leaps_cards = leaps_card_rows(symbol, chain, day, close=close,
                                          iv_rank=iv_rank, bucket_room=bucket_room)
            groups.append({"kind": "leaps",
                           "title": f"BUY A LEAPS? (bucket room ${bucket_room:,.0f})",
                           "preview": False, "cards": leaps_cards, "empty": None})
            # PMCC PREVIEW: if no LEAPS is actually held, show what selling a
            # safe call against the *previewed* LEAPS would look like.
            if symbol not in held_leaps and leaps_cards:
                lc = leaps_cards[0]
                lk, lp = float(lc["strike"]), float(lc["cost"]) / 100.0
                preview_pmcc = pmcc_card_rows(
                    symbol, chain, day, leaps_strike=lk, leaps_premium=lp,
                    close=close, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                    earnings_in_cycle=earn_in_cycle)
                groups.append({
                    "kind": "pmcc", "preview": True,
                    "title": "SELL A CALL AGAINST A LEAPS? (PMCC — PREVIEW)",
                    "leaps_strike": lk, "leaps_premium": lp,
                    "cards": preview_pmcc,
                    "empty": None if preview_pmcc else
                    (f"no SAFE strike this cycle: needs a call at "
                     f"${lk + lp:.2f}+ that still pays; none listed.")})

        # TACTICAL long-call preview (descriptive; not an H5 income lane).
        long_calls = long_call_card_rows(symbol, chain, day, close=close,
                                         iv_rank=iv_rank)
        groups.append({"kind": "long_call", "preview": True,
                       "title": "BUY A SHORT-DATED CALL? (TACTICAL — PREVIEW)",
                       "cards": long_calls,
                       "empty": None if long_calls
                       else "no call near the tactical delta this cycle"})

        sections.append({"symbol": symbol, "as_of": day, "close": close,
                         "iv_rank": iv_rank, "groups": groups})
    return sections, rv21_by_symbol


def sections_json(sections: list[dict] | None = None) -> str:
    """Serialize the scanner's candidate sections to JSON. Defaults to the real
    project state via _gather_all(); accepts an explicit list for testing."""
    import json

    if sections is None:
        sections, _ = _gather_all()
    as_of = sections[0]["as_of"] if sections else None
    return json.dumps({"as_of": as_of, "sections": sections},
                      indent=2, sort_keys=False)


_GRADE_COLORS = {"GREEN": "#2fd27d", "AMBER": "#caa53d", "RED": "#ff5470"}

_STYLE = """
  :root {
    color-scheme: dark;
  }
  body {
    background: #0b0e17;
    color: #e6e9f2;
    font-family: ui-monospace, Menlo, monospace;
    margin: 0;
    padding: 24px;
  }
  h1, h2 {
    font-family: ui-monospace, Menlo, monospace;
    letter-spacing: 0.08em;
  }
  .panel {
    background: #141a2a;
    border: 1px solid #2a3350;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
  }
  .header-sub {
    color: #9aa4c0;
    font-size: 0.9em;
  }
  .party-row {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }
  .party-card {
    background: #141a2a;
    border: 1px solid #2a3350;
    border-left: 3px solid;
    border-radius: 12px;
    padding: 12px;
    min-width: 180px;
    flex: 1;
  }
  .party-name {
    font-weight: bold;
    font-size: 1.2em;
  }
  .party-role {
    color: #9aa4c0;
    font-size: 0.85em;
    margin-bottom: 8px;
  }
  .sparkline {
    display: block;
    margin: 6px 0;
  }
  .party-badges {
    margin-top: 6px;
  }
  .pnl-badge {
    font-weight: bold;
    margin-right: 6px;
  }
  .pnl-none {
    color: #6b7280;
    font-size: 0.85em;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th, td {
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px solid #2a3350;
    font-size: 0.9em;
  }
  .pill {
    display: inline-block;
    color: #0b0e17;
    border-radius: 999px;
    padding: 2px 8px;
    margin-right: 4px;
    font-size: 0.75em;
    font-weight: bold;
  }
  .banner {
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
  }
  .banner-green {
    background: #163d2c;
    color: #2fd27d;
    font-weight: bold;
  }
  .banner-red {
    background: #3d1620;
    color: #ff5470;
    font-weight: bold;
  }
  .quest-log {
    padding-left: 20px;
  }
  .quest-done {
    color: #6b7280;
  }
  .quest-active {
    color: #ffd23f;
    font-weight: bold;
  }
  .quest-locked {
    color: #4b5270;
  }
  .ach-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .ach-tile {
    background: #1b2338;
    border: 1px solid #2a3350;
    border-radius: 10px;
    padding: 10px 14px;
    min-width: 160px;
  }
  .ach-title {
    font-weight: bold;
    color: #ffd23f;
  }
  .ach-flavor {
    color: #9aa4c0;
    font-size: 0.85em;
    margin-top: 4px;
  }
  .graveyard {
    margin-top: 16px;
    color: #6b7280;
  }
  .graveyard-title {
    font-weight: bold;
    color: #ff5470;
    margin-bottom: 6px;
  }
  .empty {
    color: #6b7280;
    font-style: italic;
  }
  .label {
    color: #9aa4c0;
    font-size: 0.85em;
  }
"""


def _esc(v) -> str:
    return _html.escape(str(v))


def _badges(grades: dict) -> str:
    if not grades:
        return ""
    pills = []
    for k, v in grades.items():
        color = _GRADE_COLORS.get(v, "#6b7280")
        pills.append(f'<span class="pill" style="background:{color}">'
                     f'{_esc(k)}:{_esc(v)}</span>')
    return f'<div class="party-badges">{"".join(pills)}</div>'


def _pnl_cell(row: dict) -> str:
    pnl = row["pnl"]
    # Derive the sign from the whole-dollar figure we actually display, so a
    # value that rounds to $0 (e.g. a breakeven row a few cents negative)
    # never shows as "-$0".
    rounded = round(pnl)
    color = "#2fd27d" if rounded >= 0 else "#ff5470"
    sign = "+" if rounded >= 0 else "-"
    body = f'<span style="color:{color}">{sign}${abs(pnl):,.0f}</span>'
    if row["note"]:
        body += f' <span class="label">({_esc(row["note"])})</span>'
    return body


def _scenario_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    trs = []
    for r in rows:
        tag = _esc(r["tag"]) if r["tag"] else ""
        trs.append(f"<tr><td>${r['price']:,.2f}</td>"
                   f'<td class="label">{tag}</td>'
                   f"<td>{_pnl_cell(r)}</td></tr>")
    return ("<table><thead><tr><th>Price</th><th></th>"
            "<th>Your gain or loss</th></tr></thead><tbody>"
            + "".join(trs) + "</tbody></table>")


def _card_html(card: dict) -> str:
    if "skipped" in card:
        return (f'<div class="panel"><div class="label">'
                f'{_esc(card["skipped"])}</div></div>')
    parts = ['<div class="panel">',
             f'<div class="party-name">{_esc(card["headline"])}</div>',
             _scenario_table(card["scenarios"]),
             f'<div class="header-sub">{_esc(card.get("verdict", ""))}</div>',
             _badges(card.get("grades", {}))]
    if card.get("countdown"):
        parts.append(f'<div class="label">{_esc(card["countdown"])}</div>')
    parts.append("</div>")
    return "".join(parts)


def _group_html(grp: dict) -> str:
    head = f'<h3>{_esc(grp["title"])}</h3>'
    if not grp["cards"]:
        empty = grp.get("empty") or "none this cycle"
        body = f'<div class="empty">{_esc(empty)}</div>'
    else:
        body = "".join(_card_html(c) for c in grp["cards"])
    return head + body


def render(data: dict) -> str:
    """Render the assemble() dict into one self-contained HTML string.
    Pure string templating: no file I/O, no network, no external assets.
    Every value from `data` is html.escape()'d before embedding."""
    symbols_html = ""
    for sec in data["symbols"]:
        groups = "".join(_group_html(g) for g in sec["groups"])
        symbols_html += (
            f'<div class="panel"><h2>{_esc(sec["symbol"])} '
            f'&mdash; close ${sec["close"]:,.2f} &mdash; '
            f'IV-rank {sec["iv_rank"]:.2f}</h2>{groups}</div>')
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>WHICH OPTIONS LOOK ATTRACTIVE?</title>'
        f'<style>{_STYLE}</style></head><body>'
        '<div class="panel"><h1>WHICH OPTIONS LOOK ATTRACTIVE TODAY?</h1>'
        '<div class="header-sub">at-expiration payoff &mdash; not a '
        'prediction</div></div>'
        f'{symbols_html}</body></html>')


def main(**assemble_kwargs) -> str:
    """Assemble real (or injected) candidates, render, write to OUTPUT_PATH.
    Read-only over project data; the only write is the HTML file."""
    data = assemble(**assemble_kwargs)
    out_html = render(data)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write(out_html)
    abs_path = os.path.abspath(OUTPUT_PATH)
    print(f"wrote {abs_path}")
    print("open it in your browser to see the scenario tables")
    return abs_path


if __name__ == "__main__":
    import sys
    if "--json" in sys.argv:
        print(sections_json())
    else:
        main()

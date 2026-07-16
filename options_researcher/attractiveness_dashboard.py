"""options_researcher/attractiveness_dashboard.py -- interactive scenario
view over attractiveness candidates (v2 layout).

assemble() gathers the SAME candidates attractiveness.py prints (via its
card-builder functions, unmodified) and attaches, per candidate: an
at-expiration payoff ladder, a deterministic bull/base/bear mini-table
(bbb_rows -- scenario framing from realized vol, not a forecast), and a
per-symbol technicals snapshot (options_researcher.technicals).

render() turns that into one self-contained HTML string: sticky data-as-of
banner, a "TOP 3 PICKS TODAY" hero (research-context narratives from
reports/attractiveness_context/<as-of>.json when present via load_context();
otherwise the honest quantitative select_top_picks() shortlist, never
invented prose), a provenance-labeled market-context strip, and per-symbol
panels with a responsive side-by-side card grid. No network, no JS
framework, no options-pricing model. main() writes
.tmp/dashboard/attractiveness.html; `--json` prints the sections (now
including technicals).

Every payoff number is computed AT EXPIRATION from intrinsic value only --
there is deliberately no Black-Scholes / time-value model anywhere here.
The Top-3 ordering weights (PICK_* in config.py) are presentation-layer
display ordering only, never strategy gates.
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


_BBB_LABEL = "scenario framing from realized vol — not a forecast"

_SELL_LANES = ("put", "cc", "pmcc")
_BUY_LANES = ("leaps", "long_call")


def bbb_rows(card: dict, structure: str, *, close: float,
             rv21: float) -> list[dict]:
    """Deterministic bull/base/bear at-expiration rows for one candidate.

    base = close (flat); bull/bear = close * (1 +/- k * monthly_move) where
    monthly_move = rv21 / sqrt(12) and k = min(2.0, sqrt(dte / 30)). Pure
    arithmetic scenario framing from realized vol -- NOT a forecast. Returns
    [] when rv21 is NaN or nonpositive (never invents a move size)."""
    if not isinstance(rv21, (int, float)) or rv21 != rv21 or rv21 <= 0:
        return []
    dte = int(card["dte"])
    monthly_move = float(rv21) / math.sqrt(12.0)
    k = min(2.0, math.sqrt(dte / 30.0))
    points = [("bear", max(0.0, close * (1 - k * monthly_move))),
              ("base", close),
              ("bull", close * (1 + k * monthly_move))]

    strike = float(card["strike"])
    out = []
    for tag, price in points:
        note = ""
        if structure == "put":
            pnl = _put_pnl(price, strike, float(card["credit"]))
        elif structure == "cc":
            pnl = _cc_pnl(price, strike, float(card["credit"]), close)
        elif structure == "pmcc":
            pnl, note = _pmcc_pnl(price, strike, float(card["leaps_strike"]),
                                  float(card["leaps_cost"]),
                                  float(card["credit"]))
        elif structure in ("leaps", "long_call"):
            pnl = _leaps_pnl(price, strike, float(card["cost"]))
        else:
            raise ValueError(f"unknown structure {structure!r}")
        out.append({"scenario": tag, "price": _round_cents(price),
                    "pnl": _round_cents(pnl), "note": note})
    return out


def select_top_picks(data: dict, n: int = 3) -> list[dict]:
    """Transparent quantitative shortlist over EVERY non-skipped card across
    all symbols/lanes in an assemble() dict. Display ordering only (weights =
    config.PICK_*, presentation layer, never strategy gates).

    Hard veto: any card whose grades include liquidity RED is excluded.
    Score = GREEN-badge count * PICK_GREEN_POINT
            + PICK_RANK_LEADER_BONUS if the card leads its lane ladder
            + PICK_TECH_BONUS on technical confluence (buy lanes: trend up or
              20d breakout; sell lanes: ma_posture != below_all); no bonus
              when the section carries no technicals snapshot.
    Ties break by annualized_yield desc (sell lanes) / breakeven_move asc
    (buy lanes), then symbol/lane/strike for determinism. At most one pick
    per (symbol, lane)."""
    import config

    pool: list[tuple[tuple, dict]] = []
    for sec in data.get("symbols", []):
        tech = sec.get("technicals") or {}
        for grp in sec.get("groups", []):
            kind = grp["kind"]
            for card in grp.get("cards", []):
                if "skipped" in card:
                    continue
                grades = card.get("grades") or {}
                if grades.get("liquidity") == "RED":
                    continue
                greens = sum(1 for v in grades.values() if v == "GREEN")
                score = greens * config.PICK_GREEN_POINT
                if card.get("rank_leader"):
                    score += config.PICK_RANK_LEADER_BONUS
                if tech:
                    if kind in _BUY_LANES and (tech.get("trend") == "up"
                                               or tech.get("breakout_20d")):
                        score += config.PICK_TECH_BONUS
                    elif kind in _SELL_LANES and (tech.get("ma_posture")
                                                  != "below_all"):
                        score += config.PICK_TECH_BONUS
                if kind in _SELL_LANES:
                    ay = card.get("annualized_yield")
                    tie = (-float(ay) if isinstance(ay, (int, float))
                           and ay == ay else float("inf"))
                else:
                    bm = card.get("breakeven_move")
                    tie = (float(bm) if isinstance(bm, (int, float))
                           and bm == bm else float("inf"))
                pick = {"symbol": sec["symbol"], "lane": kind,
                        "strike": float(card["strike"]),
                        "expiry": card["expiry"], "dte": int(card["dte"]),
                        "score": score, "card": card}
                pool.append(((-score, tie, pick["symbol"], pick["lane"],
                              pick["strike"]), pick))

    pool.sort(key=lambda item: item[0])
    picks: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for _key, pick in pool:
        lane_key = (pick["symbol"], pick["lane"])
        if lane_key in seen:
            continue
        seen.add(lane_key)
        picks.append(pick)
        if len(picks) == n:
            break
    return picks


def load_context(as_of: str, base_dir: str = "reports/attractiveness_context"
                 ) -> tuple[dict | None, str | None]:
    """Load the research-context JSON for a data as-of date.

    Exact match <base_dir>/<as_of>.json first; else the newest dated file
    <= as_of with a stale warning; else (None, None). Malformed/unreadable
    JSON -> (None, warning). Never fabricates content."""
    import glob
    import json
    import re
    from datetime import date

    try:
        date.fromisoformat(str(as_of))
    except (TypeError, ValueError):
        return None, None

    def _read(path: str) -> tuple[dict | None, str | None]:
        try:
            with open(path) as f:
                ctx = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, (f"research context file {os.path.basename(path)} "
                          f"is unreadable ({e.__class__.__name__}) — "
                          "ignoring it")
        if not isinstance(ctx, dict):
            return None, (f"research context file {os.path.basename(path)} "
                          "is not a JSON object — ignoring it")
        return ctx, None

    exact = os.path.join(base_dir, f"{as_of}.json")
    if os.path.exists(exact):
        return _read(exact)

    dated = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")
    stems = sorted(
        m.group(1)
        for m in (dated.match(os.path.basename(p))
                  for p in glob.glob(os.path.join(base_dir, "*.json")))
        if m and m.group(1) <= as_of)
    if not stems:
        return None, None
    newest = stems[-1]
    ctx, warn = _read(os.path.join(base_dir, f"{newest}.json"))
    if ctx is None:
        return None, warn
    return ctx, (f"research context is from {newest} "
                 f"(stale vs data as-of {as_of})")


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
        if card.get("annualized_yield") is not None:
            money += f" (~{100 * card['annualized_yield']:.0f}%/yr)"
    star = "★ " if card.get("rank_leader") else ""
    return (f"{star}{lead} — {money} — result by {card['expiry']} "
            f"({card['dte']} days out)")


def _countdown(card: dict) -> str:
    import config
    dte = int(card["dte"])
    roll = config.H4_THESIS_ROLL_DTE
    return (f"{dte} days until expiration · roll reminder kicks in with "
            f"{roll} days left")


def _page_data_as_of(sections: list[dict]) -> str:
    """Honest page-level "data as-of" date: the EARLIEST per-symbol as_of
    date across the assembled sections (never today's wall clock). Taking
    the earliest, not the freshest, name means a stale chain cache can never
    hide behind a fresher one -- the banner must say the stale date."""
    dates = sorted({sec["as_of"] for sec in sections if sec.get("as_of")})
    return dates[0] if dates else "no cached data"


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
                    cards.append({**card, "scenarios": [], "bbb": [],
                                  "headline": "", "countdown": ""})
                    continue
                # shallow copy: nested dicts (e.g. grades) are shared, not
                # duplicated -- fine because nothing here mutates them in place.
                enriched = dict(card)
                if kind == "pmcc":
                    enriched["leaps_strike"] = float(grp["leaps_strike"])
                    enriched["leaps_cost"] = float(grp["leaps_premium"]) * 100.0
                enriched["scenarios"] = scenario_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["bbb"] = bbb_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["headline"] = _headline(sym, kind, enriched)
                enriched["countdown"] = (_countdown(enriched)
                                         if kind in ("leaps", "long_call")
                                         else "")
                cards.append(enriched)
            out_groups.append({"kind": kind, "title": grp["title"],
                               "cards": cards, "empty": grp.get("empty")})
        out_sec = {"symbol": sym, "close": float(sec["close"]),
                   "iv_rank": float(sec["iv_rank"]),
                   "as_of": sec["as_of"], "groups": out_groups}
        # injected test sections may omit technicals; render handles absence
        if "technicals" in sec:
            out_sec["technicals"] = sec["technicals"]
        if "technicals_line" in sec:
            out_sec["technicals_line"] = sec["technicals_line"]
        out_symbols.append(out_sec)
    return {"symbols": out_symbols, "data_as_of": _page_data_as_of(out_symbols)}


def _gather_all() -> tuple[list[dict], dict[str, float]]:
    """Load real per-symbol candidate sections + rv21, mirroring
    attractiveness.main()'s data gathering (no printing)."""
    import glob

    import pandas as pd

    import config
    from data.underlying_closes import load_closes
    from options_researcher.attractiveness import (
        cc_card_rows,
        ladder_cards,
        leaps_card_rows,
        long_call_card_rows,
        pmcc_card_rows,
        put_card_rows,
    )
    from options_researcher.earnings import load_earnings
    from options_researcher.features import load_features
    from options_researcher.fomc import load_fomc
    from options_researcher.portfolio import HOLDINGS_PATH, load_holdings, load_positions
    from options_researcher.technicals import (
        technical_snapshot,
        technical_summary_line,
    )

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
        closes = load_closes(symbol, "2018-01-01", day, allow_oos=True)
        close = float(closes.iloc[-1])
        technicals = technical_snapshot(closes)
        rv21 = float(row["rv21"])
        rv21_by_symbol[symbol] = rv21
        iv_rank = float(row["iv_rank"]) if pd.notna(row["iv_rank"]) else 0.0
        iv_minus_rv = (float(row["iv_minus_rv"])
                       if pd.notna(row["iv_minus_rv"]) else 0.0)
        earnings = load_earnings(symbol)
        fomcs = load_fomc()

        put_cards = ladder_cards(put_card_rows, symbol, chain, day,
                                 rank_key="annualized_yield",
                                 higher_is_better=True, close=close, rv21=rv21,
                                 iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                                 earnings_dates=earnings,
                                 fomc_dates=fomcs)
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
                           "cards": ladder_cards(
                               cc_card_rows, symbol, chain, day,
                               rank_key="annualized_yield",
                               higher_is_better=True, close=close,
                               cost_basis=float(lot.iloc[0]["cost_basis"]),
                               iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                               earnings_dates=earnings,
                               fomc_dates=fomcs),
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
            pmcc_cards = ladder_cards(
                pmcc_card_rows, symbol, chain, day,
                rank_key="annualized_yield", higher_is_better=True,
                leaps_strike=lk, leaps_premium=lp,
                close=close, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                earnings_dates=earnings, fomc_dates=fomcs)
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
                preview_pmcc = ladder_cards(
                    pmcc_card_rows, symbol, chain, day,
                    rank_key="annualized_yield", higher_is_better=True,
                    leaps_strike=lk, leaps_premium=lp,
                    close=close, iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                    earnings_dates=earnings, fomc_dates=fomcs)
                groups.append({
                    "kind": "pmcc", "preview": True,
                    "title": "SELL A CALL AGAINST A LEAPS? (PMCC — PREVIEW)",
                    "leaps_strike": lk, "leaps_premium": lp,
                    "cards": preview_pmcc,
                    "empty": None if preview_pmcc else
                    (f"no SAFE strike this cycle: needs a call at "
                     f"${lk + lp:.2f}+ that still pays; none listed.")})

        # TACTICAL long-call preview (descriptive; not an H5 income lane).
        long_calls = ladder_cards(long_call_card_rows, symbol, chain, day,
                                  rank_key="breakeven_move",
                                  higher_is_better=False, close=close,
                                  iv_rank=iv_rank)
        groups.append({"kind": "long_call", "preview": True,
                       "title": "BUY A SHORT-DATED CALL? (TACTICAL — PREVIEW)",
                       "cards": long_calls,
                       "empty": None if long_calls
                       else "no call near the tactical delta this cycle"})

        sections.append({"symbol": symbol, "as_of": day, "close": close,
                         "iv_rank": iv_rank, "groups": groups,
                         "technicals": technicals,
                         "technicals_line": technical_summary_line(technicals)})
    return sections, rv21_by_symbol


def sections_json(sections: list[dict] | None = None) -> str:
    """Serialize the scanner's candidate sections to JSON. Defaults to the real
    project state via _gather_all(); accepts an explicit list for testing."""
    import json

    if sections is None:
        sections, _ = _gather_all()
    _dates = {s["as_of"] for s in sections} if sections else set()
    as_of = next(iter(_dates)) if len(_dates) == 1 else None
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
    padding: 0;
  }
  h1, h2 {
    font-family: ui-monospace, Menlo, monospace;
    letter-spacing: 0.08em;
  }
  .data-asof-banner {
    background: #ffce00;
    color: #1a1300;
    font-weight: 900;
    text-align: center;
    padding: 12px 16px;
    font-size: 1.05em;
    letter-spacing: 0.01em;
    border-bottom: 4px solid #ff5470;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .page-body {
    padding: 24px;
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
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }
  .card-grid .panel {
    margin-bottom: 0;
  }
  .hero {
    border-color: #ffd23f;
  }
  .hero-card {
    background: #1b2338;
    border: 1px solid #3a4670;
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 14px;
  }
  .prov {
    display: inline-block;
    background: #2a3350;
    color: #9aa4c0;
    border-radius: 6px;
    padding: 1px 6px;
    font-size: 0.72em;
    margin-left: 6px;
  }
  .tech-line {
    color: #7fd4ff;
    font-size: 0.9em;
    margin: 4px 0 8px;
  }
  .warn {
    color: #ffce00;
    font-size: 0.9em;
    margin: 6px 0;
  }
  .narr {
    margin: 6px 0;
    font-size: 0.92em;
  }
  .narr-k {
    color: #ffd23f;
    font-weight: bold;
    margin-right: 6px;
  }
  details {
    margin-top: 8px;
  }
  details summary {
    cursor: pointer;
    color: #9aa4c0;
    font-size: 0.9em;
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


def _bbb_table(rows: list[dict]) -> str:
    """Bull/base/bear mini-table with its honest framing label."""
    if not rows:
        return ""
    trs = []
    for r in rows:
        trs.append(f"<tr><td>{_esc(r['scenario'])}</td>"
                   f"<td>${r['price']:,.2f}</td>"
                   f"<td>{_pnl_cell(r)}</td></tr>")
    return (f'<div class="label">{_esc(_BBB_LABEL)}</div>'
            "<table><thead><tr><th>Scenario</th><th>Price</th>"
            "<th>P&amp;L</th></tr></thead><tbody>"
            + "".join(trs) + "</tbody></table>")


def _card_tech_line(kind: str, tech: dict | None) -> str:
    """Lane-aware one-liner derived from the section's technicals snapshot.
    Empty string when no snapshot / nothing meaningful -- never invented."""
    if not tech:
        return ""
    if kind in _BUY_LANES:
        bits = []
        if tech.get("trend") in ("up", "down", "sideways"):
            bits.append(f"trend {tech['trend']}")
        if tech.get("breakout_20d"):
            bits.append("20d breakout")
        mom = tech.get("mom_1m")
        if isinstance(mom, float) and mom == mom:
            bits.append(f"{mom:+.1%} 1M")
        return "buy-side context: " + " · ".join(bits) if bits else ""
    posture = {"above_all": "above all MAs",
               "below_all": "below all MAs",
               "mixed": "mixed vs MAs"}.get(tech.get("ma_posture", ""))
    return f"sell-side context: {posture}" if posture else ""


def _card_html(card: dict, *, tech_note: str = "") -> str:
    if "skipped" in card:
        return (f'<div class="panel"><div class="label">'
                f'{_esc(card["skipped"])}</div></div>')
    parts = ['<div class="panel">',
             f'<div class="party-name">{_esc(card["headline"])}</div>',
             _badges(card.get("grades", {}))]
    if tech_note:
        parts.append(f'<div class="tech-line">{_esc(tech_note)}</div>')
    parts.append(_bbb_table(card.get("bbb", [])))
    parts.append(f'<div class="header-sub">{_esc(card.get("verdict", ""))}</div>')
    if card.get("countdown"):
        parts.append(f'<div class="label">{_esc(card["countdown"])}</div>')
    ladder = _scenario_table(card["scenarios"])
    if ladder:
        parts.append(f"<details><summary>payoff ladder</summary>{ladder}"
                     "</details>")
    parts.append("</div>")
    return "".join(parts)


def _group_html(grp: dict, *, tech: dict | None = None) -> str:
    head = f'<h3>{_esc(grp["title"])}</h3>'
    if not grp["cards"]:
        empty = grp.get("empty") or "none this cycle"
        body = f'<div class="empty">{_esc(empty)}</div>'
    else:
        note = _card_tech_line(grp["kind"], tech)
        cards = "".join(_card_html(c, tech_note=note) for c in grp["cards"])
        body = f'<div class="card-grid">{cards}</div>'
    return head + body


def _prov_tag(context: dict | None) -> str:
    """Small provenance tag for every context-derived narrative block."""
    prov = (context or {}).get("provenance") or (
        "provenance not stated in context file")
    return f'<span class="prov">{_esc(prov)}</span>'


_NARRATIVE_FIELDS = (("why_now", "why now"), ("hypothesis", "hypothesis"),
                     ("thesis", "thesis"), ("bull", "bull"), ("base", "base"),
                     ("bear", "bear"), ("logic", "logic"))


def _find_pick_card(data: dict, pick: dict) -> dict | None:
    """Match a context-JSON top_pick to an assembled card.

    Matching rule: same symbol (case-insensitive), lane == group kind,
    expiry string equal, and float(strike) equal to the cent."""
    sym = str(pick.get("symbol", "")).upper()
    lane = pick.get("lane")
    expiry = pick.get("expiry")
    try:
        strike = float(pick.get("strike"))
    except (TypeError, ValueError):
        return None
    for sec in data.get("symbols", []):
        if str(sec["symbol"]).upper() != sym:
            continue
        for grp in sec["groups"]:
            if grp["kind"] != lane:
                continue
            for card in grp["cards"]:
                if "skipped" in card:
                    continue
                if (card.get("expiry") == expiry
                        and abs(float(card["strike"]) - strike) < 0.005):
                    return card
    return None


def _hero_pick_html(pick: dict, data: dict, context: dict | None) -> str:
    """One hero card: matched scanner numbers (or an unmatched warning) plus
    the JSON's narrative blocks, each provenance-labeled. Never invents."""
    prov = _prov_tag(context)
    card = _find_pick_card(data, pick)
    if card is not None:
        head = (f'<div class="party-name">{_esc(card["headline"])}</div>'
                + _badges(card.get("grades", {}))
                + _bbb_table(card.get("bbb", [])))
    else:
        ident = (f'{pick.get("symbol", "?")} {pick.get("lane", "?")} '
                 f'${pick.get("strike", "?")} exp {pick.get("expiry", "?")}')
        head = (f'<div class="party-name">{_esc(ident)}</div>'
                '<div class="warn">unmatched to current candidates &mdash; '
                "details below are from the research JSON, not the assembled "
                "scanner</div>")
    narrs = []
    for key, label in _NARRATIVE_FIELDS:
        val = pick.get(key)
        if val:
            narrs.append(f'<div class="narr"><span class="narr-k">'
                         f"{_esc(label)}</span>{_esc(val)} {prov}</div>")
    return f'<div class="hero-card">{head}{"".join(narrs)}</div>'


def _hero_html(data: dict, context: dict | None) -> str:
    """TOP 3 PICKS TODAY: research-context narratives when the JSON has
    top_picks; otherwise the quantitative select_top_picks shortlist with an
    honest no-narratives line. Membership disagreements are disclosed."""
    py_picks = select_top_picks(data)
    json_picks = (context or {}).get("top_picks") or []
    if json_picks:
        body = "".join(_hero_pick_html(p, data, context) for p in json_picks)

        def _jkey(p: dict) -> tuple:
            try:
                strike = float(p.get("strike"))
            except (TypeError, ValueError):
                strike = None
            return (str(p.get("symbol", "")).upper(), p.get("lane"),
                    strike, p.get("expiry"))

        jset = {_jkey(p) for p in json_picks}
        pset = {(p["symbol"].upper(), p["lane"], p["strike"], p["expiry"])
                for p in py_picks}
        if py_picks and jset != pset:
            listing = "; ".join(
                f"{p['symbol']} {p['lane']} ${p['strike']:g} {p['expiry']} "
                f"(score {p['score']})" for p in py_picks)
            body += ('<div class="label">Python quantitative shortlist '
                     f"differs: {_esc(listing)}</div>")
    elif py_picks:
        cards = []
        for p in py_picks:
            c = p["card"]
            cards.append(
                '<div class="hero-card">'
                f'<div class="party-name">{_esc(c.get("headline", ""))}</div>'
                + _badges(c.get("grades", {}))
                + _bbb_table(c.get("bbb", []))
                + f'<div class="label">pick score {p["score"]} &middot; '
                  f'{_esc(p["symbol"])} {_esc(p["lane"])}</div></div>')
        body = ("".join(cards)
                + '<div class="warn">no research narratives for this date '
                  "&mdash; quantitative shortlist only</div>")
    else:
        body = ('<div class="empty">no non-vetoed candidates to shortlist '
                "this cycle</div>")
    return f'<div class="panel hero"><h2>TOP 3 PICKS TODAY</h2>{body}</div>'


def _market_html(context: dict | None) -> str:
    """Market-context strip; omitted honestly when the context has none."""
    market = (context or {}).get("market")
    if not isinstance(market, dict) or not market:
        return ""
    prov = _prov_tag(context)
    parts = ['<div class="panel">', f"<h2>MARKET CONTEXT {prov}</h2>"]
    if market.get("summary"):
        parts.append(f'<div class="narr">{_esc(market["summary"])}</div>')
    if market.get("regime"):
        parts.append(f'<div class="label">regime: '
                     f'{_esc(market["regime"])}</div>')
    for note in market.get("notes") or []:
        parts.append(f'<div class="label">&middot; {_esc(note)}</div>')
    parts.append("</div>")
    return "".join(parts)


def _symbol_context_html(symbol: str, context: dict | None) -> str:
    """Per-symbol news/catalysts from the context JSON, provenance-labeled;
    empty string (omitted) when absent."""
    sym_ctx = ((context or {}).get("symbols") or {}).get(symbol)
    if not isinstance(sym_ctx, dict):
        return ""
    prov = _prov_tag(context)
    parts = []
    if sym_ctx.get("news_summary"):
        parts.append(f'<div class="narr"><span class="narr-k">news</span>'
                     f'{_esc(sym_ctx["news_summary"])} {prov}</div>')
    for cat in sym_ctx.get("catalysts") or []:
        if isinstance(cat, dict) and cat.get("what"):
            when = cat.get("date") or "date unknown"
            parts.append(f'<div class="label">catalyst {_esc(when)}: '
                         f'{_esc(cat["what"])} {prov}</div>')
    return "".join(parts)


def render(data: dict, *, context: dict | None = None,
           context_warning: str | None = None) -> str:
    """Render the assemble() dict (plus optional research context) into one
    self-contained HTML string. Pure string templating: no file I/O, no
    network, no external assets. Every value from `data` / `context` is
    html.escape()'d before embedding. Page order: sticky as-of banner ->
    Top-3 hero -> market strip -> per-symbol panels (card grid)."""
    symbols_html = ""
    for sec in data["symbols"]:
        tech = sec.get("technicals")
        groups = "".join(_group_html(g, tech=tech) for g in sec["groups"])
        tech_line = sec.get("technicals_line")
        tech_html = (f'<div class="tech-line">{_esc(tech_line)}</div>'
                     if tech_line else "")
        symbols_html += (
            f'<div class="panel"><h2>{_esc(sec["symbol"])} '
            f'&mdash; close ${sec["close"]:,.2f} &mdash; '
            f'IV-rank {sec["iv_rank"]:.2f}</h2>{tech_html}'
            f'{_symbol_context_html(sec["symbol"], context)}{groups}</div>')
    data_as_of = data.get("data_as_of") or "no cached data"
    banner = (
        '<div class="data-asof-banner">'
        f'DATA AS-OF {_esc(data_as_of)} CLOSE &mdash; quotes move intraday; '
        'verify live quotes in your broker before acting. Research only '
        '&mdash; not investment advice.</div>')
    warn_html = (f'<div class="warn">{_esc(context_warning)}</div>'
                 if context_warning else "")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<title>WHICH OPTIONS LOOK ATTRACTIVE?</title>'
        f'<style>{_STYLE}</style></head><body>'
        f'{banner}'
        '<div class="page-body">'
        '<div class="panel"><h1>WHICH OPTIONS LOOK ATTRACTIVE TODAY?</h1>'
        '<div class="header-sub">at-expiration payoff &mdash; not a '
        'prediction</div></div>'
        f'{warn_html}'
        f'{_hero_html(data, context)}'
        f'{_market_html(context)}'
        f'{symbols_html}</div></body></html>')


def main(**assemble_kwargs) -> str:
    """Assemble real (or injected) candidates, load the dated research
    context (honest fallback when absent), render, write to OUTPUT_PATH.
    Read-only over project data; the only write is the HTML file."""
    data = assemble(**assemble_kwargs)
    context, warning = load_context(data.get("data_as_of") or "")
    out_html = render(data, context=context, context_warning=warning)
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

"""options_researcher/attractiveness_dashboard.py -- interactive scenario
view over attractiveness candidates (v2 layout).

assemble() gathers the SAME candidates attractiveness.py prints (via its
card-builder functions, unmodified) and attaches, per candidate: an
at-expiration payoff ladder, a deterministic bull/base/bear mini-table
(bbb_rows -- scenario framing from realized vol, not a forecast), and a
per-symbol technicals snapshot (options_researcher.technicals).

render() turns that into one self-contained HTML string: a compact as-of
metadata header, the unchanged mechanical Top 3 (research-context narratives
from reports/attractiveness_context/<as-of>.json when present via
load_context()), a secondary exact-session QM/MA comparison, quant/market
background, and per-symbol panels with a responsive side-by-side card grid.
No network, no JS framework, no options-pricing model. main() writes
.tmp/dashboard/attractiveness.html; `--json` prints the sections (now
including technicals).

Every payoff number is computed AT EXPIRATION from intrinsic value only --
there is deliberately no Black-Scholes / time-value model anywhere here.
The Top-3 ordering weights (PICK_* in config.py) are presentation-layer
display ordering only, never strategy gates.

Within each symbol panel, strategy sections are also ordered from the
strongest current candidate to the weakest.  This reuses the same
presentation-only score and leaves the source candidate data, strategy gates,
and position state unchanged.
"""

from __future__ import annotations

import html as _html
import math
import os
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path

OUTPUT_PATH = os.path.join(".tmp", "dashboard", "attractiveness.html")

_PMCC_NOTE = "just the premium; LEAPS value not counted"
DISPLAY_ONLY_LABEL = "DISPLAY-ONLY — not in any registered hypothesis"


@contextmanager
def _input_root_cwd():
    """Read deterministic board inputs from an explicitly configured root.

    Research deployments write their own reports and dashboard, but consume
    the runtime board from the clean ops checkout.  Keep the cwd switch narrow
    so every output path remains rooted in the deployment checkout.
    """
    configured = os.environ.get("ATTRACTIVENESS_INPUT_ROOT")
    if not configured:
        yield Path.cwd()
        return
    input_root = Path(configured).expanduser().resolve()
    if not input_root.is_dir():
        raise FileNotFoundError(
            f"ATTRACTIVENESS_INPUT_ROOT is not a directory: {input_root}"
        )
    previous = Path.cwd()
    os.chdir(input_root)
    try:
        yield input_root
    finally:
        os.chdir(previous)


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


_PMCC_PREVIEW_NOTE = "full two-leg P&L (LEAPS at expiration intrinsic)"


def _pmcc_full_pnl(price: float, short_strike: float, leaps_strike: float,
                   leaps_cost: float, credit: float) -> tuple[float, str]:
    """FULL two-leg PMCC P&L at expiration (LEAPS intrinsic minus its cost,
    plus the short-call leg). Used for PREVIEW structures, where the LEAPS is
    not actually held: showing credit-only there would hide the dominant risk
    -- the long leg you would first have to buy."""
    leaps_leg = max(0.0, price - leaps_strike) * 100.0 - leaps_cost
    short_leg = credit - max(0.0, price - short_strike) * 100.0
    return (leaps_leg + short_leg, _PMCC_PREVIEW_NOTE)


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
        pnl_fn = _pmcc_full_pnl if card.get("preview") else _pmcc_pnl
        breakeven = (lk + (lc - credit) / 100.0 if card.get("preview")
                     else None)
        ladder = _price_ladder(close=close, rv21=rv21, strike=strike,
                               breakeven=breakeven)
        out = []
        for row in ladder:
            pnl, note = pnl_fn(row["price"], strike, lk, lc, credit)
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
            pnl_fn = _pmcc_full_pnl if card.get("preview") else _pmcc_pnl
            pnl, note = pnl_fn(price, strike, float(card["leaps_strike"]),
                               float(card["leaps_cost"]),
                               float(card["credit"]))
        elif structure in ("leaps", "long_call"):
            pnl = _leaps_pnl(price, strike, float(card["cost"]))
        else:
            raise ValueError(f"unknown structure {structure!r}")
        out.append({"scenario": tag, "price": _round_cents(price),
                    "pnl": _round_cents(pnl), "note": note})
    return out


def risk_economics(card: dict, structure: str, *, close: float) -> dict:
    """Worst-case economics AT EXPIRATION for one candidate, in plain dollars.

    Returns {"capital_required", "max_loss", "breakeven"} (plus "max_profit"
    for pmcc, whose profit is capped by construction). In plain English: a
    short put is a paid promise to buy 100 shares at the strike -- its
    worst case is the stock at zero (strike*100 minus the credit), and the
    capital that must sit behind it is the full purchase price. These numbers
    exist so the page can be reconciled against config.RISK_SLEEVE and
    config.MAX_LOSS_PER_TRADE instead of showing credit-only optimism."""
    if structure == "put":
        strike = float(card["strike"])
        credit = float(card["credit"])
        return {"capital_required": strike * 100.0,
                "max_loss": _round_cents(strike * 100.0 - credit),
                "breakeven": _round_cents(strike - credit / 100.0)}
    if structure == "cc":
        credit = float(card["credit"])
        # against shares already held: the option leg adds no capital, but
        # the covered position's worst case is the shares to zero less the
        # credit -- hiding the share leg would be credit-only optimism.
        return {"capital_required": 0.0,
                "max_loss": _round_cents(close * 100.0 - credit),
                "breakeven": _round_cents(close - credit / 100.0)}
    if structure == "pmcc":
        credit = float(card["credit"])
        lk, lc = float(card["leaps_strike"]), float(card["leaps_cost"])
        short_k = float(card["strike"])
        return {"capital_required": _round_cents(lc),
                "max_loss": _round_cents(lc - credit),
                "breakeven": _round_cents(lk + (lc - credit) / 100.0),
                "max_profit": _round_cents(
                    (short_k - lk) * 100.0 - lc + credit)}
    if structure in ("leaps", "long_call"):
        cost = float(card["cost"])
        return {"capital_required": _round_cents(cost),
                "max_loss": _round_cents(cost),
                "breakeven": _round_cents(float(card["breakeven"]))}
    raise ValueError(f"unknown structure {structure!r}")


def _admissible_pick_pool(data: dict, *, include_csp_watch: bool) -> list[tuple[tuple, dict]]:
    """Return cards admitted by the existing Top-3 safety rules.

    Both dashboard lists consume this one pool so QM can change ordering but
    can never admit a card rejected for policy, snapshot integrity, or
    liquidity.  The tuple key remains the original mechanical order.
    """
    pool: list[tuple[tuple, dict]] = []
    for sec in data.get("symbols", []):
        if sec.get("display_only"):
            continue
        tech = sec.get("technicals") or {}
        for grp in sec.get("groups", []):
            kind = grp["kind"]
            for card in grp.get("cards", []):
                if "skipped" in card:
                    continue
                grades = card.get("grades") or {}
                if grades.get("liquidity") == "RED":
                    continue
                snapshot = card.get("top3_snapshot")
                if isinstance(snapshot, dict):
                    eligible = snapshot.get("rank_eligible") is True
                    policy = snapshot.get("policy")
                    reasons = policy.get("reason_codes") if isinstance(policy, Mapping) else ()
                    csp_watch = (
                        include_csp_watch
                        and snapshot.get("selection_status") == "WATCH"
                        and isinstance(reasons, list)
                        and reasons == ["CSP_ASSIGNMENT_CAPITAL_UNCONFIRMED"]
                    )
                    if not eligible and not csp_watch:
                        continue
                quality = _display_quality_key(card, kind, tech)
                score = _display_score(card, kind, tech)
                if kind in _SELL_LANES:
                    ay = card.get("annualized_yield")
                    tie = -float(ay) if isinstance(ay, (int, float)) and ay == ay else float("inf")
                else:
                    bm = card.get("breakeven_move")
                    tie = float(bm) if isinstance(bm, (int, float)) and bm == bm else float("inf")
                pick = {
                    "symbol": sec["symbol"],
                    "lane": kind,
                    "strike": float(card["strike"]),
                    "expiry": card["expiry"],
                    "dte": int(card["dte"]),
                    "score": score,
                    "card": card,
                }
                pool.append(((*quality, tie, pick["symbol"], pick["lane"], pick["strike"]), pick))
    return pool


def _qm_is_not_covered(item: object) -> bool:
    """True for a name the frozen QM study never covered (structural)."""
    return (isinstance(item, Mapping)
            and item.get("status") == "NOT_IN_FROZEN_STUDY")


def _qm_context_block_reason(
    data: Mapping[str, object], qm_context: Mapping[str, object] | None
) -> str | None:
    """Fail-closed reason unless QM is current for every COVERED displayed name.

    Two things changed with the pre-close chain lane, both to keep this gate
    honest rather than to loosen it:

    * the context is bound to the board by ``board_session``, not by an equal
      ``as_of``. QM reads daily bars and the board can read a same-day 15:45
      chain, so exact-date equality would blank the panel every capture day for
      a reason that is not staleness. The panel prints both dates.
    * a name the frozen study never covered is reported per name and does not
      block the covered names, exactly as H7 v1.4 made source health per name.
      A name the study DOES cover still blocks the panel when it is not current.
    """
    market_date = data.get("data_as_of")
    if not isinstance(market_date, str) or not market_date:
        return "dashboard market date is unavailable"
    if not isinstance(qm_context, Mapping):
        return "QM context unavailable"
    if qm_context.get("status") != "CURRENT":
        return str(qm_context.get("reason") or "QM context is not current")
    context_as_of = qm_context.get("as_of")
    if not isinstance(context_as_of, str) or not context_as_of:
        return "QM context date is unavailable"
    board_session = qm_context.get("board_session")
    if isinstance(board_session, str) and board_session:
        if board_session != market_date:
            return (
                f"QM context was built for board session {board_session}, not "
                f"the dashboard's {market_date}"
            )
    elif context_as_of > market_date:
        return (
            f"QM context date {context_as_of} is ahead of dashboard market "
            f"date {market_date}"
        )
    symbols = qm_context.get("symbols")
    if not isinstance(symbols, Mapping):
        return "QM context symbols are unavailable"
    raw_sections = data.get("symbols", [])
    sections = raw_sections if isinstance(raw_sections, (list, tuple)) else ()
    missing = []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        if section.get("display_only"):
            continue
        symbol = section.get("symbol")
        if not isinstance(symbol, str):
            continue
        item = symbols.get(symbol)
        if _qm_is_not_covered(item):
            continue
        if not isinstance(item, Mapping) or item.get("status") != "CURRENT":
            missing.append(symbol)
    if missing:
        return "QM context missing or stale for: " + ", ".join(sorted(missing))
    return None


def select_top_picks(
    data: dict, n: int = 3, *, policy_veto: bool | None = None, include_csp_watch: bool = False
) -> list[dict]:
    """Transparent quantitative shortlist over EVERY non-skipped card across
    all symbols/lanes in an assemble() dict. Display ordering only (weights =
    config.PICK_*, presentation layer, never strategy gates).

    Hard vetoes:
      - liquidity RED;
      - an assembled card whose exact-session / lane-policy snapshot is not
        rank eligible.  The snapshot applies the current policy by structure:
        the defined-risk cap belongs to tactical long calls, while a
        cash-secured put reports its equity-side assignment commitment.

    ``policy_veto`` is retained as a no-op compatibility argument for callers
    of the v2 dashboard.  The former universal max-loss veto was removed: it
    incorrectly treated a cash-secured put as a tactical long call.

    ``include_csp_watch`` is for the paper-only hero.  It admits a permitted
    cash-secured put whose *only* missing fact is explicit assignment-capital
    authorization, and leaves the card visibly marked WATCH.  It never admits
    a plan-only, data-blocked, or otherwise unmodeled lane.

    Ordering is the lexicographic ``_display_quality_key`` (GREEN fraction,
    then lane leadership, then technical confluence — fraction, not raw
    count, because seller lanes carry 7 gradeable badges vs 3 on buyer
    lanes). Ties break by annualized_yield desc (sell lanes) /
    breakeven_move asc (buy lanes), then symbol/lane/strike for determinism.
    At most ONE pick per symbol: the hero is a cross-name shortlist, and
    each symbol surfaces only its best card. The legacy integer
    ``pick_score`` (config.PICK_*) is kept on each pick for the audit line
    but no longer orders the shortlist."""
    del policy_veto

    pool = _admissible_pick_pool(data, include_csp_watch=include_csp_watch)

    pool.sort(key=lambda item: item[0])
    picks: list[dict] = []
    seen: set[str] = set()
    for _key, pick in pool:
        if pick["symbol"] in seen:
            continue
        seen.add(pick["symbol"])
        picks.append(pick)
        if len(picks) == n:
            break
    return picks


def select_qm_top_picks(
    data: dict, qm_context: Mapping[str, object], n: int = 3, *, include_csp_watch: bool = False
) -> list[dict]:
    """Return the exact mechanical picks for the lower descriptive QM panel.

    QM is not a selector or a ranking input.  A current context is required
    only to render the lower, descriptive panel; the returned cards preserve
    the mechanical shortlist's membership, order, lanes, and contracts.
    """
    if _qm_context_block_reason(data, qm_context) is not None:
        return []

    symbols = qm_context.get("symbols")
    if not isinstance(symbols, Mapping):
        return []

    picks = select_top_picks(data, n=n, include_csp_watch=include_csp_watch)
    contextual_picks: list[dict] = []
    for pick in picks:
        qm = symbols.get(pick["symbol"])
        if _qm_is_not_covered(qm):
            # Per name: a mechanical pick the frozen study never covered keeps
            # its slot and renders its own NOT_COVERED line. Dropping the whole
            # panel would hide the covered names' context over a permanent fact
            # about one name -- and the mechanical membership is unchanged
            # either way, since QM never selects or reorders anything.
            contextual_picks.append(dict(pick))
            continue
        if not isinstance(qm, Mapping) or qm.get("status") != "CURRENT":
            return []
        contextual_picks.append(dict(pick))
    return contextual_picks


def _qm_candidate_key(pick: Mapping[str, object]) -> str:
    """Stable key for candidate-specific QM evidence."""
    card = pick.get("card")
    card = card if isinstance(card, Mapping) else {}
    snapshot = card.get("top3_snapshot")
    if isinstance(snapshot, Mapping) and isinstance(snapshot.get("candidate_id"), str):
        return snapshot["candidate_id"]
    strike = pick.get("strike")
    strike_value = float(strike) if isinstance(strike, (int, float)) else 0.0
    return (
        f"{pick.get('symbol', '?')}:{pick.get('lane', '?')}:"
        f"{pick.get('expiry', '?')}:{strike_value:.2f}"
    )


def enrich_qm_context_with_candidates(
    data: dict, qm_context: Mapping[str, object] | None
) -> Mapping[str, object] | None:
    """Attach candidate-specific, non-option-P&L evidence to each ticker.

    QM signals and study provenance are built once per ticker. This later,
    presentation-only join adds the existing policy/liquidity-admitted option
    cards and their breakeven stock-move comparison; it cannot add a card.
    """
    if not isinstance(qm_context, Mapping):
        return qm_context
    import copy

    from options_researcher.qm_dashboard import underlying_breakeven_frequency

    enriched = copy.deepcopy(dict(qm_context))
    symbols = enriched.get("symbols")
    if not isinstance(symbols, dict):
        return enriched
    for _base_key, pick in _admissible_pick_pool(data, include_csp_watch=True):
        symbol = pick["symbol"]
        symbol_context = symbols.get(symbol)
        if not isinstance(symbol_context, dict):
            continue
        candidates = symbol_context.setdefault("option_candidates", {})
        if not isinstance(candidates, dict):
            continue
        key = _qm_candidate_key(pick)
        candidates[key] = {
            "candidate_id": key,
            "lane": pick["lane"],
            "underlying_breakeven_frequency": underlying_breakeven_frequency(
                symbol_context, pick["card"], pick["lane"]
            ),
        }
    return enriched


def pinned_picks(data: dict) -> list[dict]:
    """Owner-pinned visibility for config.PICK_PINNED_SYMBOLS.

    Each pinned symbol surfaces its best ADMISSIBLE card under exactly the
    hero's admission and ordering rules (select_top_picks on the symbol's
    own section, CSP-watch admitted as on the hero). Never fabricated: a
    pinned symbol with no admissible card yields {"symbol", "pick": None}
    so the strip can render an honest gap. Separate from — and never
    reordering — the deterministic Top-3."""
    import config

    out: list[dict] = []
    for symbol in getattr(config, "PICK_PINNED_SYMBOLS", []):
        sub = {"symbols": [s for s in data.get("symbols", [])
                           if s.get("symbol") == symbol]}
        picks = select_top_picks(sub, n=1, include_csp_watch=True)
        out.append({"symbol": symbol,
                    "pick": picks[0] if picks else None})
    return out


_DISPLAY_POLICY_TIER = {
    "ELIGIBLE": 0,
    "WATCH": 1,
    "PLAN_ONLY": 2,
    "DATA_BLOCKED": 3,
}


def _display_score(card: dict, kind: str, tech: dict | None) -> int:
    """Return the existing presentation score for one candidate card.

    This is intentionally the same score used by ``select_top_picks``.  It is
    only used to order the already-visible strategy sections; it does not
    create a recommendation, alter a candidate's policy status, or affect a
    trading rule.
    """
    import config

    grades = card.get("grades") or {}
    greens = sum(1 for value in grades.values() if value == "GREEN")
    score = greens * config.PICK_GREEN_POINT
    if card.get("rank_leader"):
        score += config.PICK_RANK_LEADER_BONUS
    if tech:
        if kind in _BUY_LANES and (tech.get("trend") == "up"
                                   or tech.get("breakout_20d")):
            score += config.PICK_TECH_BONUS
        elif kind in _SELL_LANES and tech.get("ma_posture") != "below_all":
            score += config.PICK_TECH_BONUS
    return score


def _display_quality_key(card: dict, kind: str, tech: dict | None) -> tuple:
    """Lexicographic, lane-size-neutral quality key; better sorts first.

    Levels: GREEN fraction (not the raw count — seller lanes carry 7
    gradeable badges vs 3 on buyer lanes, so counts are not comparable
    across lanes), then lane leadership, then technical confluence. No
    weights: the levels are strictly ordered, never summed.
    """
    grades = card.get("grades") or {}
    greens = sum(1 for value in grades.values() if value == "GREEN")
    frac = greens / len(grades) if grades else 0.0
    leader = 1 if card.get("rank_leader") else 0
    tech_conf = 0
    if tech:
        if kind in _BUY_LANES and (tech.get("trend") == "up"
                                   or tech.get("breakout_20d")):
            tech_conf = 1
        elif kind in _SELL_LANES and tech.get("ma_posture") != "below_all":
            tech_conf = 1
    return (-frac, -leader, -tech_conf)


def _display_policy_tier(card: dict) -> int:
    """Place eligible, watch, and plan-only cards in honest display tiers.

    ``selection_status`` is the authoritative merged status from
    top3_snapshot (DATA_BLOCKED whenever integrity fails — e.g. stale
    features — else the policy status). The lane policy alone is blind to
    data staleness, so it is only a fallback, never the primary key. A card
    with no snapshot carries no integrity evidence at all and must never
    outrank evidenced cards.
    """
    snapshot = card.get("top3_snapshot")
    if not isinstance(snapshot, Mapping):
        return _DISPLAY_POLICY_TIER["DATA_BLOCKED"]
    if snapshot.get("rank_eligible") is True:
        return 0
    selection_status = snapshot.get("selection_status")
    policy = snapshot.get("policy")
    policy_status = policy.get("status") if isinstance(policy, Mapping) else None
    status = (selection_status if isinstance(selection_status, str)
              else policy_status if isinstance(policy_status, str)
              else "DATA_BLOCKED")
    return _DISPLAY_POLICY_TIER.get(status, _DISPLAY_POLICY_TIER["DATA_BLOCKED"])


def _finite_sort_value(value: object, *, default: float = float("inf")) -> float:
    """Return a finite number for deterministic presentation-only sorting."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    number = float(value)
    return number if math.isfinite(number) else default


def _group_candidate_sort_key(card: dict, kind: str,
                              tech: dict | None) -> tuple:
    """Sort key for one card when ordering visible strategy sections.

    Liquidity-RED cards sit below every liquid card, matching the Top-3 hard
    veto.  Otherwise eligibility is shown first, followed by WATCH and then
    PLAN_ONLY candidates.  Score and lane-specific tie breaks are identical
    to the Top-3 display ordering.
    """
    grades = card.get("grades") or {}
    if grades.get("liquidity") == "RED":
        tier = 3
    else:
        tier = _display_policy_tier(card)
    if kind in _SELL_LANES:
        annualized_yield = _finite_sort_value(card.get("annualized_yield"))
        tie = -annualized_yield if math.isfinite(annualized_yield) else annualized_yield
    else:
        tie = _finite_sort_value(card.get("breakeven_move"))
    return (tier, *_display_quality_key(card, kind, tech), tie,
            _finite_sort_value(card.get("dte")),
            _finite_sort_value(card.get("strike")))


def _rank_groups_for_display(groups: list[dict], *,
                             tech: dict | None = None) -> list[dict]:
    """Return groups best-to-worst by their strongest visible candidate.

    Empty or skipped-only sections remain visible but sort after sections with
    actionable cards.  The input list and group dictionaries are not mutated,
    so JSON consumers retain the scanner's original lane order.
    """
    ranked: list[tuple[tuple, int, dict]] = []
    empty_key = (4, 0.0, 0, 0, float("inf"), float("inf"), float("inf"))
    for original_index, group in enumerate(groups):
        kind = str(group.get("kind", ""))
        card_keys = [
            _group_candidate_sort_key(card, kind, tech)
            for card in group.get("cards", [])
            if "skipped" not in card
        ]
        ranked.append((min(card_keys) if card_keys else empty_key,
                       original_index, group))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [group for _key, _original_index, group in ranked]


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
    return ctx, (f"company-research annotations are from {newest} "
                 f"(stale vs data as-of {as_of}; QM status has its own "
                 "exact-date check)")


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
            money += (
                f" (~{100 * card['annualized_yield']:.0f}%/yr) "
                "(simple, not compounded)"
            )
    star = "★ " if card.get("rank_leader") else ""
    return (f"{star}{lead} — {money} — result by {card['expiry']} "
            f"({card['dte']} days out)")


def _countdown(card: dict) -> str:
    import config
    dte = int(card["dte"])
    roll = config.H4_THESIS_ROLL_DTE
    return (f"{dte} days until expiration · roll reminder kicks in with "
            f"{roll} days left")


def _fresh_sections(sections: list[dict]) -> list[dict]:
    """Sections rendered from a VERIFIED Schwab pre-close session."""
    from options_researcher.schwab_chain_view import CHAIN_SOURCE

    return [sec for sec in sections
            if sec.get("chain_source") == CHAIN_SOURCE and sec.get("as_of")]


def _page_data_as_of(sections: list[dict]) -> str:
    """Honest page-level "data as-of" date.

    With no fresh source this is the EARLIEST per-symbol as_of date (never
    today's wall clock): taking the earliest means a stale chain cache can
    never hide behind a fresher one.

    When at least one section rides a VERIFIED pre-close session, the page
    date is that newest fresh session -- the date the freshest data actually
    carries -- and the banner names the still-stale names separately with
    their own date. One date can no longer describe two sources honestly, so
    the page states both rather than letting the stalest name mislabel the
    freshest (or the reverse)."""
    fresh = _fresh_sections(sections)
    if fresh:
        return max(str(sec["as_of"]) for sec in fresh)
    dates = sorted({sec["as_of"] for sec in sections if sec.get("as_of")})
    return dates[0] if dates else "no cached data"


def _page_as_of_kind(sections: list[dict]) -> str:
    """``schwab_preclose`` when the page date is a pre-close session."""
    from options_researcher.schwab_chain_view import (
        CHAIN_SOURCE,
        THETADATA_CHAIN_SOURCE,
    )

    return CHAIN_SOURCE if _fresh_sections(sections) else THETADATA_CHAIN_SOURCE


def _stale_path_as_of(sections: list[dict]) -> tuple[str | None, list[str]]:
    """(earliest as_of, names) for sections still on the frozen cache."""
    from options_researcher.schwab_chain_view import CHAIN_SOURCE

    stale = [sec for sec in sections
             if sec.get("chain_source") != CHAIN_SOURCE and sec.get("as_of")]
    if not stale:
        return None, []
    return (min(str(sec["as_of"]) for sec in stale),
            sorted(str(sec.get("symbol", "?")) for sec in stale))


def _all_display_data_as_of(
    sections: list[dict], blocked: list[dict]
) -> str:
    """Earliest known date across successful and blocked display records."""
    dates = {
        str(sec["as_of"])
        for sec in sections
        if isinstance(sec.get("as_of"), str) and sec.get("as_of")
    }
    dates.update(
        str(rec["last_known_date"])
        for rec in blocked
        if isinstance(rec.get("last_known_date"), str)
        and rec.get("last_known_date")
    )
    return min(dates) if dates else "no cached data"


def _schwab_state_html(data: Mapping[str, object]) -> str:
    """Verified / failed / absent state of the Schwab pre-close capture lane.

    A capture that does not verify must never degrade quietly into "the board
    looks stale today": the page says the session and the verification error
    out loud. A checkout with no receipts at all says that too, so silence is
    never ambiguous between "no captures" and "captures hidden by a bug".
    """
    from options_researcher.schwab_chain_view import CHAINS_ABSENT, CONVENTION_LABEL

    state = data.get("schwab_lane")
    if not isinstance(state, Mapping):
        return ""
    parts: list[str] = []
    failures = state.get("failures")
    failures = failures if isinstance(failures, (list, tuple)) else ()
    for failure in failures:
        if not isinstance(failure, Mapping):
            continue
        session = _esc(str(failure.get("session", "?")))
        if failure.get("kind") == CHAINS_ABSENT:
            # Expected in a research checkout: the receipts are tracked in git,
            # the chain parquet lives only in the ops execution checkout. Said
            # plainly so it is not mistaken for an integrity failure -- and so
            # the real red alarm below keeps its meaning.
            parts.append(
                '<div class="notice info">Schwab capture receipts for session '
                f"{session} are present, but its chain files are not in this "
                "checkout (they live in the ops execution checkout). No "
                "pre-close quotes are available here.</div>")
            continue
        parts.append(
            '<div class="notice bad"><strong>! Schwab capture session '
            f'{session} FAILED verification'
            f'</strong> — {_esc(str(failure.get("reason", "unknown")))}. '
            "Its chains were NOT used; names that depend on it fall back to "
            "the frozen cache with their own older date.</div>")
    if not state.get("receipts_found"):
        parts.append(
            '<div class="notice info">No Schwab pre-close capture receipts '
            "found in this checkout (reports/schwab_chains is empty) — every "
            f"quote below comes from the frozen ThetaData cache, not a "
            f"{_esc(CONVENTION_LABEL)} snapshot.</div>")
    return "".join(parts)


def _chain_age_html(data: Mapping[str, object]) -> str:
    """Say out loud how old the board's option quotes are.

    The per-symbol ``features_stale`` warning compares the feature row to the
    chain session, so a board whose chain and features are equally old shows
    nothing at all.  Without this banner a long-frozen cache renders exactly
    like a current one -- the page is rebuilt daily, so only the quote dates
    betray it.  Silence here is therefore never "fine"; unknown age says so.

    With a verified pre-close source present the statement becomes two lines:
    what the fresh names actually are (a 15:45 snapshot, never a close), and
    the unchanged stale warning scoped to the names still on the frozen cache.
    The per-card CHAIN_STALE_VS_TODAY gate is untouched either way.

    THE FRESH LINE AGES TOO. "Verified pre-close" is a statement about the
    SOURCE, not about the clock: if captures stop, the newest verified session
    keeps its badge while silently becoming days old. So the fresh line reads
    the same ``chain_age_sessions`` the cards do and changes tone at the same
    thresholds -- at the BLOCK bar it must not render as calm info while every
    card below it is DATA_BLOCKED.
    """
    import config
    from options_researcher.schwab_chain_view import CONVENTION_LABEL

    fresh_names = data.get("fresh_symbols")
    fresh_names = list(fresh_names) if isinstance(fresh_names, (list, tuple)) else []
    lane_html = _schwab_state_html(data)
    if fresh_names:
        count = len(fresh_names)
        age = data.get("chain_age_sessions")
        session = _esc(str(data.get("data_as_of") or "?"))
        names = _esc(", ".join(str(name) for name in fresh_names))
        subject = (f"{count} name" if count == 1 else f"{count} names")
        head = (f"Option quotes: {CONVENTION_LABEL} session "
                f"{data.get('data_as_of') or '?'}")
        if not isinstance(age, int):
            fresh_line = (
                '<div class="notice watch"><strong>! '
                f"{_esc(head)}</strong> for {subject} ({names}) — but its age "
                "could NOT be compared with the evaluation date. Treat every "
                "quote as unverified and check the live broker quote.</div>")
        elif age >= config.CHAIN_STALE_BLOCK_SESSIONS:
            sessions = "session" if age == 1 else "sessions"
            fresh_line = (
                '<div class="notice bad"><strong>! STALE BOARD — pre-close '
                f"captures have STOPPED. The newest verified session "
                f"({session}) is {age} trading {sessions} old.</strong> The "
                f"{subject} below ({names}) still carry that snapshot's "
                "premium, delta, and moneyness figures — not today's. Cards "
                f"past the {config.CHAIN_STALE_BLOCK_SESSIONS}-session limit "
                "are marked DATA_BLOCKED and excluded from the shortlist. Do "
                "not size or compare a trade from this page.</div>")
        elif age >= config.CHAIN_STALE_WARN_SESSIONS:
            sessions = "session" if age == 1 else "sessions"
            fresh_line = (
                '<div class="notice watch">! '
                f"{_esc(head)} for {subject} ({names}) — a 15:45 ET snapshot, "
                f"NOT an end-of-day close, and now {age} trading {sessions} "
                "old (no newer verified capture). Verify against the live "
                "broker quote before acting.</div>")
        else:
            fresh_line = (
                f'<div class="notice info"><strong>{_esc(head)}</strong> for '
                f"{subject} ({names}). This is a 15:45 ET snapshot, NOT an "
                "end-of-day close.</div>")
        stale_line = _stale_group_html(data)
        return lane_html + fresh_line + stale_line

    age = data.get("chain_age_sessions")
    as_of = _esc(str(data.get("data_as_of") or "no cached data"))
    evaluation_date = data.get("evaluation_date")

    if not isinstance(age, int):
        if not evaluation_date:
            return lane_html
        return lane_html + (
            '<div class="notice watch">! Option-quote age UNKNOWN — the '
            f"board's chain date ({as_of}) could not be compared with the "
            "evaluation date. Treat every quote as unverified and check "
            "the live broker quote.</div>")

    sessions = "session" if age == 1 else "sessions"
    if age >= config.CHAIN_STALE_BLOCK_SESSIONS:
        return lane_html + (
            '<div class="notice bad"><strong>! STALE BOARD — option quotes '
            f"are {age} trading {sessions} old.</strong> Every premium, "
            "delta, and moneyness figure below is from the "
            f"{as_of} close, not today. Cards past the "
            f"{config.CHAIN_STALE_BLOCK_SESSIONS}-session limit are marked "
            "DATA_BLOCKED and excluded from the shortlist. Do not size or "
            "compare a trade from this page — read the live broker quote."
            "</div>")
    if age >= config.CHAIN_STALE_WARN_SESSIONS:
        return lane_html + (
            '<div class="notice watch">! Option quotes are '
            f"{age} trading {sessions} old (chain close {as_of}). "
            "Verify against the live broker quote before acting.</div>")
    return lane_html + (
        f'<div class="notice info">Option quotes are from the {as_of} '
        "close — the most recent completed session.</div>")


def _stale_group_html(data: Mapping[str, object]) -> str:
    """The unchanged staleness warning, scoped to the still-frozen names."""
    import config

    names = data.get("stale_symbols")
    names = [str(name) for name in names] if isinstance(names, (list, tuple)) else []
    as_of = data.get("stale_as_of")
    if not names or not isinstance(as_of, str) or not as_of:
        return ""
    joined = _esc(", ".join(names))
    age = data.get("stale_chain_age_sessions")
    if not isinstance(age, int):
        return ('<div class="notice watch">! Option-quote age UNKNOWN for '
                f"{joined} (frozen-cache date {_esc(as_of)}). Treat every "
                "quote for these names as unverified.</div>")
    sessions = "session" if age == 1 else "sessions"
    if age >= config.CHAIN_STALE_BLOCK_SESSIONS:
        return ('<div class="notice bad"><strong>! STALE BOARD for '
                f"{joined} — option quotes are {age} trading {sessions} old."
                f"</strong> Their premium, delta, and moneyness figures are "
                f"from the {_esc(as_of)} close, not today. Cards past the "
                f"{config.CHAIN_STALE_BLOCK_SESSIONS}-session limit are marked "
                "DATA_BLOCKED and excluded from the shortlist.</div>")
    if age >= config.CHAIN_STALE_WARN_SESSIONS:
        return ('<div class="notice watch">! Option quotes for '
                f"{joined} are {age} trading {sessions} old (chain close "
                f"{_esc(as_of)}). Verify against the live broker quote.</div>")
    return ""


def _page_chain_age_sessions(page_as_of: str, today: str | None) -> int | None:
    """Age of the page's oldest chain session, in trading sessions.

    None when the age cannot be established (no evaluation date, no cached
    data, or a chain dated ahead of the evaluation date). None means "do not
    claim an age", never "fresh"; the caller renders it as unknown.
    """
    if not today:
        return None
    from datetime import date as _date

    try:
        as_of_date = _date.fromisoformat(page_as_of)
        evaluation_date = _date.fromisoformat(today)
    except (TypeError, ValueError):
        return None
    if as_of_date > evaluation_date:
        return None
    from options_researcher.top3_snapshot import trading_sessions_between

    return trading_sessions_between(page_as_of, today)


def assemble(
    *,
    symbol_sections: list[dict] | None = None,
    rv21_by_symbol: dict[str, float] | None = None,
    blocked: list[dict] | None = None,
    hypothesis_evidence_by_symbol: Mapping[str, object] | None = None,
    composite_signals: list[dict] | None = None,
    today: str | None = None,
) -> dict:
    """Attach scenario tables + headlines to gathered candidate sections.

    The arguments default to the real project state (see _gather_all);
    inject them to unit-test without touching disk or the network.
    ``blocked`` carries the machine-readable per-symbol failure records
    (fail-visible: they render on the page, never disappear).

    ``today`` is the evaluation session for the wall-clock chain-staleness
    gate.  A real assembly defaults it to the current America/New_York date; an
    injected assembly leaves it None unless passed, so fixtures stay
    deterministic and are never aged out by the calendar."""
    real_assembly = symbol_sections is None
    schwab_state: dict | None = None
    if real_assembly:
        symbol_sections, rv21_by_symbol, blocked, schwab_state = _gather_all()
        if today is None:
            from datetime import datetime as _dt
            from zoneinfo import ZoneInfo as _ZoneInfo

            today = _dt.now(_ZoneInfo("America/New_York")).date().isoformat()
    rv21_by_symbol = rv21_by_symbol or {}
    blocked = blocked or []

    import config
    from options_researcher.top3_snapshot import snapshot_candidate

    display_only_names = set(config.ATTRACTIVENESS_EXTRA_NAMES)
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
                # Shallow copy; grades get their own copy because the
                # lane-specific policy badge is added below.
                enriched = dict(card)
                if kind == "pmcc":
                    enriched["leaps_strike"] = float(grp["leaps_strike"])
                    enriched["leaps_cost"] = float(grp["leaps_premium"]) * 100.0
                    if grp.get("preview"):
                        enriched["preview"] = True
                enriched["risk"] = risk_economics(
                    enriched, kind, close=float(sec["close"]))
                snapshot = snapshot_candidate(
                    sec, grp, enriched,
                    csp_open_count=sec.get("csp_open_count"),
                    covered_shares=sec.get("covered_shares"),
                    leaps_held=sec.get("leaps_held"),
                    today=today,
                )
                enriched["top3_snapshot"] = snapshot
                policy = snapshot.get("policy")
                raw_policy_status = (policy.get("status")
                                     if isinstance(policy, Mapping) else None)
                policy_status = (raw_policy_status
                                 if isinstance(raw_policy_status, str)
                                 else "DATA_BLOCKED")
                policy_grade = {"ELIGIBLE": "GREEN", "WATCH": "AMBER",
                                "PLAN_ONLY": "RED"}.get(policy_status, "RED")
                enriched["grades"] = {**(enriched.get("grades") or {}),
                                      "portfolio": policy_grade}
                enriched["scenarios"] = scenario_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                enriched["bbb"] = bbb_rows(
                    enriched, kind, close=float(sec["close"]), rv21=rv21)
                if not enriched["bbb"]:
                    # An absent scenario table states WHY. Silence would read
                    # as "no scenarios worth showing" rather than "the input
                    # this table is built from does not exist".
                    reasons = [item.get("reason")
                               for item in (sec.get("feature_unavailable") or [])
                               if item.get("field") == "rv21"]
                    enriched["bbb_absent"] = (
                        "bull/base/bear scenarios need realized volatility "
                        "(rv21): " + (str(reasons[0]) if reasons
                                      else "no finite rv21 for this session"))
                enriched["headline"] = _headline(sym, kind, enriched)
                enriched["countdown"] = (_countdown(enriched)
                                         if kind in ("leaps", "long_call")
                                         else "")
                cards.append(enriched)
            out_grp = {"kind": kind, "title": grp["title"],
                       "cards": cards, "empty": grp.get("empty")}
            if "preview" in grp:
                out_grp["preview"] = grp["preview"]
            out_groups.append(out_grp)
        out_sec = {"symbol": sym, "close": float(sec["close"]),
                   "iv_rank": float(sec["iv_rank"]),
                   "as_of": sec["as_of"], "groups": out_groups}
        for passthrough in ("chain_source", "close_as_of", "close_kind",
                            "closes_as_of", "technicals_as_of", "atm_iv",
                            "features_source", "feature_unavailable",
                            "iv_rank_label", "fresh_refusal_reason"):
            if passthrough in sec:
                out_sec[passthrough] = sec[passthrough]
        if bool(sec.get("display_only")) or sym in display_only_names:
            out_sec["display_only"] = True
        if "features_as_of" in sec:
            out_sec["features_as_of"] = sec["features_as_of"]
            out_sec["features_stale"] = bool(sec.get("features_stale"))
        if "earnings_source" in sec:
            out_sec["earnings_source"] = sec["earnings_source"]
        # injected test sections may omit technicals; render handles absence
        if "technicals" in sec:
            out_sec["technicals"] = sec["technicals"]
        if "technicals_line" in sec:
            out_sec["technicals_line"] = sec["technicals_line"]
        out_symbols.append(out_sec)
    out_blocked = []
    for rec in blocked:
        out_rec = dict(rec)
        if bool(rec.get("display_only")) or rec.get("symbol") in display_only_names:
            out_rec["display_only"] = True
        out_blocked.append(out_rec)

    if hypothesis_evidence_by_symbol is None and real_assembly:
        from options_researcher.hypothesis_evidence import (
            gather_hypothesis_evidence,
        )

        evidence_symbols = [
            str(record["symbol"])
            for record in [*out_symbols, *out_blocked]
            if isinstance(record.get("symbol"), str)
        ]
        hypothesis_evidence_by_symbol = gather_hypothesis_evidence(
            evidence_symbols,
            root=Path.cwd(),
        )
    if hypothesis_evidence_by_symbol is not None:
        for record in [*out_symbols, *out_blocked]:
            symbol = record.get("symbol")
            if isinstance(symbol, str):
                evidence = hypothesis_evidence_by_symbol.get(symbol)
                if evidence is not None:
                    record["hypothesis_evidence"] = evidence

    if composite_signals is None and real_assembly:
        from options_researcher.composite_signals import build_board

        composite_signals = build_board()

    canonical_symbols = [
        sec for sec in out_symbols if not sec.get("display_only")
    ]
    page_as_of = _page_data_as_of(canonical_symbols)
    stale_as_of, stale_symbols = _stale_path_as_of(canonical_symbols)
    fresh_symbols = [str(sec.get("symbol", "?"))
                     for sec in _fresh_sections(canonical_symbols)]
    out = {
        "symbols": out_symbols,
        "blocked": out_blocked,
        "data_as_of": page_as_of,
        "as_of_kind": _page_as_of_kind(canonical_symbols),
        "fresh_symbols": sorted(fresh_symbols),
        "stale_as_of": stale_as_of,
        "stale_symbols": stale_symbols,
        "stale_chain_age_sessions": (
            _page_chain_age_sessions(stale_as_of, today) if stale_as_of else None
        ),
        "display_data_as_of": _all_display_data_as_of(
            out_symbols, out_blocked
        ),
        "evaluation_date": today,
        "chain_age_sessions": _page_chain_age_sessions(page_as_of, today),
        "composite_signals": composite_signals or [],
    }
    if schwab_state is not None:
        out["schwab_lane"] = schwab_state
    return out


def _gather_all() -> tuple[list[dict], dict[str, float], list[dict], dict]:
    """Load real per-symbol candidate sections + rv21 over the display
    universe (config.ATTRACTIVENESS_UNIVERSE), mirroring
    attractiveness.main()'s data gathering (no printing).

    Per-symbol failures never take the page down: each failed symbol
    becomes a machine-readable blocked record {symbol, reason_code,
    detail, last_known_date, unexpected} rendered on the page. Expected
    data gaps (no chains, missing features/closes) are unexpected=False;
    anything else is unexpected=True and makes the CLI exit nonzero so
    launchd never reports a clean rebuild over a programming failure."""
    import glob
    from datetime import date as date_cls
    from datetime import datetime, timezone

    import pandas as pd

    import config
    from data.underlying_closes import load_closes, load_closes_adjusted
    from options_researcher import schwab_chain_view as schwab_view
    from options_researcher.attractiveness import (
        cc_card_rows,
        ladder_cards,
        leaps_card_rows,
        long_call_card_rows,
        pmcc_card_rows,
        put_card_rows,
    )
    from options_researcher.earnings import load_earnings
    from options_researcher.earnings_cycle import apply_cycle_badges
    from options_researcher.features import load_features
    from options_researcher.fomc import load_fomc
    from options_researcher.h7_earnings import load_assertions
    from options_researcher.oi_change import attach_oi_change
    from options_researcher.portfolio import HOLDINGS_PATH, load_holdings, load_positions
    from options_researcher.technicals import (
        technical_snapshot,
        technical_summary_line,
    )

    holdings = (load_holdings() if os.path.exists(HOLDINGS_PATH)
                else pd.DataFrame({"symbol": pd.Series(dtype="str"),
                                   "shares": pd.Series(dtype="int"),
                                   "cost_basis": pd.Series(dtype="float")}))
    positions = load_positions()
    csp_open_count = (int((positions["structure"] == "csp").sum())
                      if not positions.empty else 0)
    thesis_used = 0.0
    held_leaps: dict[str, tuple[float, float]] = {}
    if not positions.empty:
        t = positions[positions["bucket"] == "thesis"]
        thesis_used = float((t["entry_price"] * 100 * t["contracts"]).sum())
        for _, lp in positions[positions["structure"] == "leaps_call"].iterrows():
            held_leaps.setdefault(str(lp["symbol"]),
                                  (float(lp["strike"]), float(lp["entry_price"])))
    bucket_room = config.H4_THESIS_MAX_PREMIUM_TOTAL - thesis_used

    # One v3 evidence load for the whole page; a broken store degrades every
    # v3-graded badge to UNKNOWN (visible), never crashes the build.
    try:
        v3_assertions = load_assertions()
    except Exception:
        v3_assertions = None
    known_now = datetime.now(timezone.utc)

    sections: list[dict] = []
    rv21_by_symbol: dict[str, float] = {}
    blocked: list[dict] = []

    def _block(symbol: str, code: str, detail: str, day: str | None,
               unexpected: bool = False) -> None:
        record = {"symbol": symbol, "reason_code": code,
                  "detail": detail, "last_known_date": day,
                  "unexpected": unexpected}
        if symbol in config.ATTRACTIVENESS_EXTRA_NAMES:
            record["display_only"] = True
        blocked.append(record)

    schwab_sessions, schwab_failures = schwab_view.verified_sessions()
    schwab_state = {
        "verified_sessions": list(schwab_sessions),
        "failures": [dict(failure) for failure in schwab_failures],
        "receipts_found": bool(schwab_sessions or schwab_failures),
    }

    for symbol in config.ATTRACTIVENESS_UNIVERSE:
        files = sorted(glob.glob(os.path.join(".cache", "chains",
                                              f"{symbol}_*.parquet")))
        theta_day = (os.path.basename(files[-1]).split("_")[1]
                     .replace(".parquet", "") if files else None)
        # Newer of (frozen ThetaData EOD cache, newest VERIFIED Schwab
        # pre-close session), decided by the ONE shared rule the CLI board uses
        # too. A fresh chain is only rendered when a same-instant 15:45 spot
        # exists for it -- pairing 15:45 quotes with the closes store (frozen
        # well behind) misprices moneyness by several percent.
        source = schwab_view.select_display_source(
            symbol, theta_day, have_verified_sessions=bool(schwab_sessions))
        fresh_refusal = source.refusal
        is_fresh = source.kind == schwab_view.CHAIN_SOURCE
        if not is_fresh and theta_day is None:
            detail = ("no chain parquet in .cache/chains"
                      + (f"; {fresh_refusal}" if fresh_refusal else ""))
            _block(symbol, "NO_CACHED_CHAINS", detail, None)
            continue
        if is_fresh:
            chain_frame, day = source.frame, source.session
            preclose_spot = source.spot
            iv_rank_preview = source.iv_rank_preview
            chain_path, chain_source = None, schwab_view.CHAIN_SOURCE
        else:
            chain_frame, preclose_spot, iv_rank_preview = None, None, None
            day, chain_path = theta_day, files[-1]
            chain_source = schwab_view.THETADATA_CHAIN_SOURCE
        try:
            section, rv21 = _gather_symbol(
                symbol, chain_path, day,
                chain_frame=chain_frame, chain_source=chain_source,
                preclose_spot=preclose_spot,
                iv_rank_preview=iv_rank_preview,
                fresh_refusal_reason=fresh_refusal,
                holdings=holdings, held_leaps=held_leaps,
                csp_open_count=csp_open_count, bucket_room=bucket_room,
                v3_assertions=v3_assertions, known_now=known_now,
                load_closes=load_closes,
                load_closes_adjusted=load_closes_adjusted,
                load_earnings=load_earnings, load_features=load_features,
                load_fomc=load_fomc, apply_cycle_badges=apply_cycle_badges,
                technical_snapshot=technical_snapshot,
                technical_summary_line=technical_summary_line,
                ladder_cards=ladder_cards, put_card_rows=put_card_rows,
                cc_card_rows=cc_card_rows, pmcc_card_rows=pmcc_card_rows,
                leaps_card_rows=leaps_card_rows,
                long_call_card_rows=long_call_card_rows,
                attach_oi_change=attach_oi_change,
                date_cls=date_cls, pd=pd, config=config)
        except FileNotFoundError as exc:
            _block(symbol, "INPUT_MISSING", str(exc), day)
            continue
        except Exception as exc:  # fail-visible, never success-shaped
            _block(symbol, "UNEXPECTED_ERROR",
                   f"{type(exc).__name__}: {exc}", day, unexpected=True)
            continue
        if symbol in config.ATTRACTIVENESS_EXTRA_NAMES:
            section["display_only"] = True
        sections.append(section)
        rv21_by_symbol[symbol] = rv21
    return sections, rv21_by_symbol, blocked, schwab_state


def _gather_symbol(symbol, chain_path, day, *, holdings, held_leaps,
                   csp_open_count, bucket_room, v3_assertions, known_now,
                   load_closes, load_closes_adjusted, load_earnings,
                   load_features, load_fomc, apply_cycle_badges,
                   technical_snapshot, technical_summary_line, ladder_cards,
                   put_card_rows, cc_card_rows, pmcc_card_rows,
                   leaps_card_rows, long_call_card_rows, attach_oi_change,
                   date_cls, pd, config, chain_frame=None,
                   chain_source=None, preclose_spot=None,
                   iv_rank_preview=None,
                   fresh_refusal_reason=None) -> tuple[dict, float]:
    """Build one symbol's section (extracted so _gather_all can isolate
    per-symbol failures). Dependencies are passed in to keep the lazy-import
    pattern of the caller.

    A schwab-sourced section (``chain_frame`` + ``chain_source`` +
    ``preclose_spot``) is a 15:45 pre-close snapshot: its close is the receipt's
    same-instant spot mid, its feature values are computed IN MEMORY for that
    session, and every date surface carries the pre-close convention. The
    on-disk feature store is NEVER written from here -- it is H5 entry_watch's
    registered input path.
    """
    from options_researcher import schwab_chain_view as schwab_view

    schwab_sourced = chain_source == schwab_view.CHAIN_SOURCE
    chain = chain_frame if chain_frame is not None else pd.read_parquet(chain_path)
    raw_closes = load_closes(symbol, "2018-01-01", day, allow_oos=True)
    adjusted_closes = load_closes_adjusted(
        symbol, "2018-01-01", day, allow_oos=True)
    closes_as_of = str(raw_closes.index[-1])
    technicals = technical_snapshot(adjusted_closes)
    feature_unavailable: list[dict] = []

    if schwab_sourced:
        # D4b: per-session feature values, computed in memory from the fresh
        # chain. rv21 and iv_minus_rv need underlying closes THROUGH the
        # session; the closes store ends earlier and its refresh is owner-gated,
        # so they are unavailable -- never interpolated across the hole.
        if preclose_spot is None:
            # Unreachable from _gather_all (it refuses a fresh chain without a
            # verified spot); explicit so a future caller cannot pair a fresh
            # chain with a stale close by omission.
            raise ValueError(
                f"{symbol}: a schwab-sourced section requires a verified "
                "15:45 spot")
        close = float(preclose_spot)
        close_as_of, close_kind = day, schwab_view.CLOSE_KIND
        features_as_of, features_stale = day, False
        features_source = "schwab_preclose_session"
        rv21 = float("nan")
        iv_minus_rv = float("nan")
        iv_rank = (float(iv_rank_preview) if iv_rank_preview is not None
                   else float("nan"))
        iv_rank_label = ("preview (capture-lane calibration)"
                         if iv_rank_preview is not None else None)
        atm_iv = _session_atm_iv(chain, day)
        gap = (f"underlying closes end {closes_as_of}, before this "
               f"{day} session")
        feature_unavailable.append({"field": "rv21", "reason": gap})
        feature_unavailable.append({"field": "iv_minus_rv", "reason": gap})
        if iv_rank_preview is None:
            feature_unavailable.append({
                "field": "iv_rank",
                "reason": "no capture-lane IV-rank preview for this session"})
    else:
        # DATE-ALIGNED feature row: the row FOR the chain day when it exists,
        # else the newest row at-or-before it (never a future row -- that
        # would be look-ahead). A mismatch is recorded as features_as_of so
        # the page can say the IV badges are stale instead of hiding it.
        feats = load_features(symbol)
        at_or_before = feats.loc[feats.index.astype(str) <= day]
        if at_or_before.empty:
            row = feats.iloc[0]
            features_as_of = str(feats.index[0])
        else:
            row = at_or_before.iloc[-1]
            features_as_of = str(at_or_before.index[-1])
        close = float(raw_closes.iloc[-1])
        close_as_of, close_kind = closes_as_of, schwab_view.EOD_CLOSE_KIND
        features_stale = features_as_of != day
        features_source = "feature_store"
        iv_rank_label = None
        # FAIL-CLOSED: an unavailable feature stays NaN and grades UNKNOWN.
        # The former `else 0.0` coercions manufactured verdicts out of missing
        # data -- iv_rank 0.0 grades iv_for_buyer GREEN ("cheapest IV this name
        # has ever shown") and iv_minus_rv 0.0 clears the VRP GREEN threshold of
        # exactly 0.0. Both read as evidence; neither was a measurement.
        rv21 = float(row["rv21"]) if pd.notna(row["rv21"]) else float("nan")
        iv_rank = (float(row["iv_rank"]) if pd.notna(row["iv_rank"])
                   else float("nan"))
        iv_minus_rv = (float(row["iv_minus_rv"])
                       if pd.notna(row["iv_minus_rv"]) else float("nan"))
        atm_iv = (float(row["atm_iv"])
                  if "atm_iv" in row.index and pd.notna(row["atm_iv"])
                  else float("nan"))
        for field, value in (("rv21", rv21), ("iv_rank", iv_rank),
                             ("iv_minus_rv", iv_minus_rv)):
            if value != value:
                feature_unavailable.append({
                    "field": field,
                    "reason": f"no finite value in the {features_as_of} "
                              "feature row"})
    # Core names keep the curated per-symbol CSV. Watchlist names have
    # none: the ladder is built with an empty date list (every earnings
    # badge UNKNOWN) and re-graded per card from the v3 point-in-time
    # store below -- never a falsely reassuring GREEN.
    try:
        earnings = load_earnings(symbol)
        earnings_source = "curated_csv"
    except FileNotFoundError:
        earnings = []
        earnings_source = "v3_store"
    fomcs = load_fomc()

    put_cards = ladder_cards(put_card_rows, symbol, chain, day,
                             rank_key="annualized_yield",
                             higher_is_better=True, close=close, rv21=rv21,
                             iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
                             earnings_dates=earnings,
                             fomc_dates=fomcs)
    # Neutral OI-change context, strictly AFTER ranking (board-invariant).
    attach_oi_change(put_cards, right="P", chain_day=chain,
                     symbol=symbol, day=day)
    groups: list[dict] = [
        {"kind": "put", "title": "SELL A PUT? (promise to buy lower)",
         "cards": put_cards,
         "empty": None if put_cards
         else "no candidates near the target delta this cycle"}]

    lot = holdings.loc[holdings["symbol"] == symbol]
    held_shares = int(lot.iloc[0]["shares"]) if len(lot) else 0
    if held_shares >= 100:
        cc_cards = ladder_cards(
            cc_card_rows, symbol, chain, day,
            rank_key="annualized_yield",
            higher_is_better=True, close=close,
            cost_basis=float(lot.iloc[0]["cost_basis"]),
            iv_rank=iv_rank, iv_minus_rv=iv_minus_rv,
            earnings_dates=earnings,
            fomc_dates=fomcs)
        attach_oi_change(cc_cards, right="C", chain_day=chain,
                         symbol=symbol, day=day)
        groups.append({"kind": "cc",
                       "title": "SELL A COVERED CALL? (rent out your shares)",
                       "cards": cc_cards,
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
        # Card's own strike/expiry are the SHORT call it displays (pmcc_card_rows).
        attach_oi_change(pmcc_cards, right="C", chain_day=chain,
                         symbol=symbol, day=day)
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
        attach_oi_change(leaps_cards, right="C", chain_day=chain,
                         symbol=symbol, day=day)
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
            attach_oi_change(preview_pmcc, right="C", chain_day=chain,
                             symbol=symbol, day=day)
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
    attach_oi_change(long_calls, right="C", chain_day=chain,
                     symbol=symbol, day=day)
    groups.append({"kind": "long_call", "preview": True,
                   "title": "BUY A SHORT-DATED CALL? (TACTICAL — PREVIEW)",
                   "cards": long_calls,
                   "empty": None if long_calls
                   else "no call near the tactical delta this cycle"})

    if earnings_source == "v3_store" and v3_assertions is not None:
        apply_cycle_badges(groups, symbol, date_cls.fromisoformat(day),
                           v3_assertions, known_as_of=known_now)

    section = {"symbol": symbol, "as_of": day, "close": close,
               "iv_rank": iv_rank, "groups": groups,
               "csp_open_count": csp_open_count,
               "covered_shares": held_shares,
               "leaps_held": symbol in held_leaps,
               "features_as_of": features_as_of,
               "features_stale": features_stale,
               "features_source": features_source,
               "feature_unavailable": feature_unavailable,
               "atm_iv": atm_iv,
               "chain_source": chain_source or schwab_view.THETADATA_CHAIN_SOURCE,
               "close_as_of": close_as_of,
               "close_kind": close_kind,
               "closes_as_of": closes_as_of,
               "technicals_as_of": closes_as_of,
               "earnings_source": earnings_source,
               "technicals": technicals,
               "technicals_line": technical_summary_line(technicals)}
    if iv_rank_label:
        section["iv_rank_label"] = iv_rank_label
    if fresh_refusal_reason:
        section["fresh_refusal_reason"] = fresh_refusal_reason
    return section, rv21


def _session_atm_iv(chain, day: str) -> float:
    """ATM implied vol for one session, on features.py's own convention.

    0.50-delta PUT on the nearest monthly expiration in the 15-60 DTE band
    (options_researcher.features.build_daily_features). NaN when the band has
    no monthly or no quotable ATM row -- never a substitute tenor.
    """
    from datetime import date as _date

    from options_researcher.chains import atm_row, nearest_monthly

    try:
        expiration = nearest_monthly(chain, _date.fromisoformat(day))
        if expiration is None:
            return float("nan")
        row = atm_row(chain, expiration)
        if row is None:
            return float("nan")
        value = float(row["iv"])
    except (KeyError, TypeError, ValueError):
        return float("nan")
    return value if value == value and value > 0 else float("nan")


def sections_json(sections: list[dict] | None = None) -> str:
    """Serialize the scanner's candidate sections to JSON. Defaults to the real
    project state via _gather_all(); accepts an explicit list for testing."""
    import json

    blocked: list[dict] = []
    if sections is None:
        with _input_root_cwd():
            sections, _rv21, blocked, _schwab_state = _gather_all()
    _dates = {s["as_of"] for s in sections} if sections else set()
    as_of = next(iter(_dates)) if len(_dates) == 1 else None
    return json.dumps({"as_of": as_of, "sections": sections,
                       "blocked": blocked},
                      indent=2, sort_keys=False)


_GRADE_CLASSES = {"GREEN": "good", "AMBER": "watch", "RED": "bad", "UNKNOWN": "unknown"}
_GRADE_SYMBOLS = {"GREEN": "✓", "AMBER": "!", "RED": "×", "UNKNOWN": "?"}

_STYLE = """
  :root {
    color-scheme: light;
    --canvas: #f3f6f4;
    --surface: #ffffff;
    --surface-soft: #f7f9f8;
    --ink: #17251f;
    --muted: #53665c;
    --line: #d9e3dd;
    --line-strong: #c3d1c9;
    --brand: #173f32;
    --good: #116b45;
    --good-bg: #e8f5ee;
    --good-line: #a8d8bd;
    --watch: #8a5700;
    --watch-bg: #fff2cc;
    --watch-line: #e8c66d;
    --bad: #a42335;
    --bad-bg: #fdecef;
    --bad-line: #e7aeb7;
    --unknown: #4f5d56;
    --unknown-bg: #edf1ef;
    --unknown-line: #cbd4cf;
    --info: #235d7d;
    --info-bg: #e8f3f8;
    --shadow: 0 8px 24px rgba(23, 63, 50, 0.06);
  }
  * { box-sizing: border-box; }
  body {
    background: var(--canvas);
    color: var(--ink);
    font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
      "Segoe UI", sans-serif;
    margin: 0;
    padding: 0;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }
  h1, h2, h3, p { margin-top: 0; }
  h1 {
    font-size: clamp(1.65rem, 3vw, 2.45rem);
    letter-spacing: -0.035em;
    line-height: 1.08;
    margin-bottom: 8px;
  }
  h2 {
    font-size: 1.2rem;
    letter-spacing: -0.015em;
    margin-bottom: 8px;
  }
  h3 {
    font-size: 0.82rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 12px;
  }
  a { color: #155f83; text-underline-offset: 2px; }
  .app-header {
    background: var(--surface);
    border-bottom: 1px solid var(--line);
  }
  .app-header-inner {
    align-items: flex-end;
    display: flex;
    gap: 24px;
    justify-content: space-between;
    margin: 0 auto;
    max-width: 1480px;
    padding: 28px 32px 24px;
  }
  .eyebrow {
    color: var(--good);
    font-size: 0.73rem;
    font-weight: 800;
    letter-spacing: 0.12em;
    margin-bottom: 7px;
    text-transform: uppercase;
  }
  .header-sub {
    color: var(--muted);
    font-size: 0.9rem;
    margin: 0;
  }
  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
  }
  .meta-chip {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 999px;
    color: var(--muted);
    font-size: 0.75rem;
    font-weight: 650;
    padding: 6px 10px;
    white-space: nowrap;
  }
  .meta-chip strong { color: var(--ink); }
  .page-body {
    margin: 0 auto;
    max-width: 1480px;
    padding: 24px 32px 40px;
  }
  .panel {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
    padding: 20px;
  }
  .party-name {
    font-size: 1rem;
    font-weight: 750;
    line-height: 1.38;
    margin-bottom: 10px;
  }
  table {
    font-variant-numeric: tabular-nums;
    width: 100%;
    border-collapse: collapse;
  }
  th, td {
    text-align: left;
    padding: 7px 8px;
    border-bottom: 1px solid var(--line);
    font-size: 0.82rem;
  }
  th {
    color: var(--muted);
    font-size: 0.7rem;
    font-weight: 750;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  tr:last-child td { border-bottom: 0; }
  .party-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 0 12px;
  }
  .status-badge, .policy-status {
    align-items: center;
    border: 1px solid;
    border-radius: 999px;
    display: inline-flex;
    font-size: 0.68rem;
    font-weight: 800;
    gap: 4px;
    letter-spacing: 0.035em;
    line-height: 1;
    padding: 5px 8px;
    text-transform: uppercase;
  }
  .status-badge.good, .policy-status.good {
    background: var(--good-bg); border-color: var(--good-line); color: var(--good);
  }
  .status-badge.watch, .policy-status.watch {
    background: var(--watch-bg); border-color: var(--watch-line); color: var(--watch);
  }
  .status-badge.bad, .policy-status.bad {
    background: var(--bad-bg); border-color: var(--bad-line); color: var(--bad);
  }
  .status-badge.unknown, .policy-status.unknown {
    background: var(--unknown-bg); border-color: var(--unknown-line); color: var(--unknown);
  }
  .empty {
    color: var(--muted);
    font-style: italic;
  }
  .label {
    color: var(--muted);
    font-size: 0.8rem;
  }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(320px, 100%), 1fr));
    gap: 12px;
  }
  .card-grid .panel {
    border-radius: 12px;
    box-shadow: none;
    margin-bottom: 0;
    padding: 16px;
  }
  .hero {
    border-color: var(--line-strong);
    padding: 24px;
  }
  .qm-comparison {
    background: var(--surface-soft);
    border-color: var(--line);
    padding: 18px;
  }
  .qm-comparison .hero-card {
    background: var(--surface);
    box-shadow: none;
  }
  .section-header {
    align-items: flex-start;
    display: flex;
    gap: 20px;
    justify-content: space-between;
    margin-bottom: 18px;
  }
  .section-header p { margin-bottom: 0; }
  .hero-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
  }
  .hero-stat {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 10px;
    min-width: 84px;
    padding: 7px 10px;
    text-align: center;
  }
  .hero-stat strong {
    display: block;
    font-size: 1.05rem;
    font-variant-numeric: tabular-nums;
  }
  .hero-stat span {
    color: var(--muted);
    font-size: 0.65rem;
    font-weight: 750;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .hero-stat.good strong { color: var(--good); }
  .hero-stat.watch strong { color: var(--watch); }
  .hero-stat.unknown strong { color: var(--unknown); }
  .hero-grid {
    display: grid;
    gap: 14px;
    grid-template-columns: 1fr;
  }
  .hero-card, .pinned-card {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 14px;
    min-width: 0;
    padding: 17px;
  }
  .hero-card.good, .pinned-card.good { border-top: 4px solid var(--good); }
  .hero-card.watch, .pinned-card.watch { border-top: 4px solid var(--watch); }
  .hero-card.bad { border-top: 4px solid var(--bad); }
  .hero-card.unknown { border-top: 4px solid var(--unknown); }
  .slot-label {
    align-items: center;
    color: var(--muted);
    display: flex;
    font-size: 0.67rem;
    font-weight: 800;
    justify-content: space-between;
    letter-spacing: 0.08em;
    margin-bottom: 10px;
    text-transform: uppercase;
  }
  .hero-card.empty-slot {
    background: var(--unknown-bg);
    border-style: dashed;
  }
  .empty-slot h3 {
    color: var(--ink);
    font-size: 1rem;
    letter-spacing: 0;
    margin: 0 0 8px;
    text-transform: none;
  }
  .gate-list {
    color: var(--muted);
    font-size: 0.8rem;
    margin: 12px 0 0;
    padding-left: 18px;
  }
  .gate-list li + li { margin-top: 7px; }
  .notice {
    border: 1px solid;
    border-radius: 10px;
    font-size: 0.8rem;
    margin: 10px 0;
    padding: 9px 11px;
  }
  .notice.watch {
    background: var(--watch-bg); border-color: var(--watch-line); color: var(--watch);
  }
  .notice.bad {
    background: var(--bad-bg); border-color: var(--bad-line); color: var(--bad);
  }
  .notice.info {
    background: var(--info-bg); border-color: #b9d7e6; color: var(--info);
  }
  .risk-block {
    border-top: 1px solid var(--line);
    margin: 12px 0;
    padding-top: 10px;
  }
  .risk-metrics {
    color: var(--muted);
    font-size: 0.76rem;
    margin-bottom: 7px;
  }
  .policy-line {
    align-items: flex-start;
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
  }
  .policy-detail {
    color: var(--muted);
    flex: 1 1 180px;
    font-size: 0.75rem;
  }
  .prov {
    display: inline-block;
    background: var(--unknown-bg);
    color: var(--unknown);
    border-radius: 999px;
    padding: 2px 7px;
    font-size: 0.65rem;
    margin-left: 6px;
  }
  .tech-line {
    background: var(--info-bg);
    border-radius: 8px;
    color: var(--info);
    font-size: 0.78rem;
    margin: 7px 0 12px;
    padding: 8px 10px;
  }
  .narr {
    margin: 7px 0;
    font-size: 0.84rem;
  }
  .narr-k {
    color: var(--brand);
    font-weight: bold;
    margin-right: 6px;
  }
  .qm-context {
    border-top: 1px solid var(--line);
    margin-top: 12px;
    padding-top: 3px;
  }
  .qm-row {
    border-bottom: 1px solid var(--line);
    font-size: 0.8rem;
    padding: 8px 0;
  }
  .qm-row:last-of-type { border-bottom: 0; }
  .pnl-positive { color: var(--good); font-weight: 750; }
  .pnl-negative { color: var(--bad); font-weight: 750; }
  .pnl-flat { color: var(--unknown); font-weight: 750; }
  .market-panel { padding: 20px 22px; }
  .market-grid {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 14px 0 10px;
  }
  .market-card {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 12px;
  }
  .market-card h3 { margin-bottom: 6px; }
  .market-card p { color: var(--muted); font-size: 0.8rem; margin: 0; }
  .market-summary { font-size: 0.94rem; margin-bottom: 4px; }
  .regime-label {
    color: var(--info);
    font-size: 0.75rem;
    font-weight: 750;
    text-transform: uppercase;
  }
  .symbol-panel { padding: 0; overflow: hidden; }
  .symbol-header {
    align-items: center;
    border-bottom: 1px solid var(--line);
    display: flex;
    gap: 18px;
    justify-content: space-between;
    padding: 20px 22px;
  }
  .symbol-header h2 { font-size: 1.45rem; margin: 0; }
  .symbol-stats { display: flex; gap: 10px; }
  .symbol-stat {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 9px;
    min-width: 105px;
    padding: 7px 10px;
  }
  .symbol-stat span {
    color: var(--muted);
    display: block;
    font-size: 0.63rem;
    font-weight: 750;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .symbol-stat strong {
    font-size: 0.94rem;
    font-variant-numeric: tabular-nums;
  }
  .symbol-body { padding: 18px 22px 22px; }
  .group-section + .group-section {
    border-top: 1px solid var(--line);
    margin-top: 22px;
    padding-top: 20px;
  }
  .group-section > summary {
    align-items: center;
    color: var(--ink);
    display: flex;
    font-size: 0.8rem;
    font-weight: 800;
    gap: 12px;
    justify-content: space-between;
    letter-spacing: 0.055em;
    text-transform: uppercase;
  }
  .group-heading {
    align-items: center;
    display: inline-flex;
    gap: 9px;
    min-width: 0;
  }
  .group-rank {
    align-items: center;
    background: var(--brand);
    border-radius: 999px;
    color: #fff;
    display: inline-flex;
    flex: 0 0 auto;
    font-size: 0.68rem;
    height: 22px;
    justify-content: center;
    letter-spacing: 0;
    width: 22px;
  }
  .strategy-rank-note {
    color: var(--muted);
    font-size: 0.72rem;
    margin: 2px 0 14px;
  }
  .group-count {
    background: var(--unknown-bg);
    border: 1px solid var(--unknown-line);
    border-radius: 999px;
    color: var(--unknown);
    font-size: 0.63rem;
    letter-spacing: 0.02em;
    padding: 3px 7px;
    text-transform: none;
  }
  .context-details {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 10px;
    margin: 10px 0 18px;
    padding: 0 11px 9px;
  }
  details {
    margin-top: 8px;
  }
  details summary {
    cursor: pointer;
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 700;
    padding: 8px 0;
  }
  .research-details {
    border-top: 1px solid var(--line);
    margin-top: 12px;
  }
  .research-details > summary { color: var(--good); }
  .gate-details > summary { color: var(--info); }
  .hypothesis-evidence {
    border-top: 1px solid var(--line);
    margin-top: 20px;
    padding-top: 14px;
  }
  .hypothesis-evidence > summary {
    color: var(--brand);
    font-weight: 800;
  }
  .evidence-grid {
    display: grid;
    gap: 9px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-top: 12px;
  }
  .evidence-row {
    background: var(--surface-soft);
    border: 1px solid var(--line);
    border-radius: 9px;
    min-width: 0;
    padding: 10px;
  }
  .evidence-row-head {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
  }
  .evidence-membership, .evidence-dates, .evidence-detail {
    color: var(--muted);
    font-size: 0.74rem;
    margin-top: 5px;
  }
  .evidence-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 7px;
  }
  .evidence-chip {
    background: var(--unknown-bg);
    border: 1px solid var(--unknown-line);
    border-radius: 999px;
    color: var(--unknown);
    font-size: 0.68rem;
    padding: 3px 7px;
  }
  .evidence-sources {
    color: var(--muted);
    font-size: 0.7rem;
    margin: 7px 0 0;
    overflow-wrap: anywhere;
    padding-left: 18px;
  }
  .intraday-evidence {
    border-top: 1px dashed var(--line);
    margin-top: 12px;
    padding-top: 12px;
  }
  .intraday-evidence h4 {
    color: var(--info);
    font-size: 0.76rem;
    letter-spacing: 0.04em;
    margin: 0 0 8px;
    text-transform: uppercase;
  }
  .page-footer {
    color: var(--muted);
    font-size: 0.72rem;
    padding: 2px 4px 24px;
    text-align: center;
  }
  @media (max-width: 1120px) {
    .market-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 760px) {
    .app-header-inner, .section-header, .symbol-header {
      align-items: stretch;
      flex-direction: column;
    }
    .app-header-inner { padding: 22px 18px 18px; }
    .page-body { padding: 16px 12px 28px; }
    .meta-row, .hero-stats { justify-content: flex-start; }
    .panel, .hero { border-radius: 12px; padding: 16px; }
    .symbol-panel { padding: 0; }
    .symbol-header { padding: 16px; }
    .symbol-body { padding: 15px; }
    .evidence-grid { grid-template-columns: 1fr; }
    .symbol-stats { width: 100%; }
    .symbol-stat { flex: 1; min-width: 0; }
    th, td { padding: 6px 4px; }
  }
"""


def _esc(v) -> str:
    return _html.escape(str(v))


def _badges(grades: dict) -> str:
    if not grades:
        return ""
    pills = []
    for k, v in grades.items():
        status = str(v).upper()
        cls = _GRADE_CLASSES.get(status, "unknown")
        symbol = _GRADE_SYMBOLS.get(status, "?")
        pills.append(f'<span class="status-badge {cls}">'
                     f'{symbol} {_esc(k)} · {_esc(status)}</span>')
    return f'<div class="party-badges">{"".join(pills)}</div>'


def _hero_badges(grades: dict) -> str:
    """Keep the hero scan-friendly while preserving every grade on demand."""
    if not grades:
        return ""
    key_order = ("liquidity", "earnings", "fomc")
    primary = {key: grades[key] for key in key_order if key in grades}
    visible = _badges(primary)
    return (f'{visible}<details class="gate-details">'
            f'<summary>All gate checks ({len(grades)})</summary>'
            f'{_badges(grades)}</details>')


def _pnl_cell(row: dict) -> str:
    pnl = row["pnl"]
    # Derive the sign from the whole-dollar figure we actually display, so a
    # value that rounds to $0 (e.g. a breakeven row a few cents negative)
    # never shows as "-$0".
    rounded = round(pnl)
    if rounded > 0:
        cls, sign = "pnl-positive", "+"
    elif rounded < 0:
        cls, sign = "pnl-negative", "-"
    else:
        cls, sign = "pnl-flat", ""
    body = f'<span class="{cls}">{sign}${abs(pnl):,.0f}</span>'
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


def _bbb_table(rows: list[dict], *, absent_reason: object = None) -> str:
    """Bull/base/bear mini-table with its honest framing label.

    An absent table states WHY when the caller knows: silence reads as "no
    scenarios worth showing" rather than "the input this table needs does not
    exist for this session".
    """
    if not rows:
        if isinstance(absent_reason, str) and absent_reason:
            return ('<div class="notice watch">! Scenario table unavailable — '
                    f"{_esc(absent_reason)}.</div>")
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


def _risk_line(card: dict) -> str:
    """Plain-dollar economics plus the structure-specific policy status.

    A short put's assignment capital is not compared to the tactical long-call
    premium cap.  The policy snapshot says which existing rule applies and
    exposes any unknown portfolio fact rather than inventing a green result.
    """
    import config

    risk = card.get("risk")
    if not isinstance(risk, dict) or "max_loss" not in risk:
        return ""
    bits = [f"worst case -${risk['max_loss']:,.0f} at expiration"]
    cap_req = risk.get("capital_required")
    if isinstance(cap_req, (int, float)) and cap_req > 0:
        bits.append(f"capital required ${cap_req:,.0f}"
                    + (f" vs ${config.RISK_SLEEVE:,.0f} sleeve"
                       if cap_req > config.RISK_SLEEVE else ""))
    if isinstance(risk.get("max_profit"), (int, float)):
        bits.append(f"max profit ${risk['max_profit']:,.0f}")
    if isinstance(risk.get("breakeven"), (int, float)):
        bits.append(f"breakeven ${risk['breakeven']:,.2f}")
    snapshot = card.get("top3_snapshot")
    policy_data = (snapshot.get("policy") if isinstance(snapshot, dict)
                   else None)
    if isinstance(policy_data, dict):
        status = str(policy_data.get("status", "WATCH"))
        reasons = policy_data.get("reason_codes") or []
        detail = ", ".join(
            _POLICY_REASON_LABELS.get(str(reason), str(reason))
            for reason in reasons)
        cls = {"ELIGIBLE": "good", "WATCH": "watch",
               "PLAN_ONLY": "bad", "DATA_BLOCKED": "bad"}.get(
                   status, "unknown")
        symbol = {"ELIGIBLE": "✓", "WATCH": "!",
                  "PLAN_ONLY": "×", "DATA_BLOCKED": "×"}.get(status, "?")
    else:
        status, detail, cls, symbol = "UNKNOWN", "policy status unavailable", \
            "unknown", "?"
    detail_html = (f'<span class="policy-detail">{_esc(detail)}</span>'
                   if detail else "")
    return (
        '<div class="risk-block">'
        f'<div class="risk-metrics">{_esc(" · ".join(bits))}</div>'
        '<div class="policy-line">'
        f'<span class="policy-status {cls}">{symbol} {_esc(status)}</span>'
        f'{detail_html}</div></div>')


_PREVIEW_WARNING = (
    "two-leg preview — the LEAPS is NOT held; this requires "
    "buying the LEAPS first, and the P&L shown includes that "
    "long leg's full risk"
)

_POLICY_REASON_LABELS = {
    "CSP_ASSIGNMENT_CAPITAL_UNCONFIRMED": (
        "cash set aside for a possible 100-share purchase is not recorded"
    ),
    "CSP_ASSIGNMENT_CAPITAL_NOT_AUTHORIZED": (
        "cash for a possible 100-share purchase is not authorized"
    ),
    "CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES": "not an allowed cash-secured-put name",
    "CSP_SLOT_FULL": "the one cash-secured-put slot is already used",
    "CSP_OPEN_COUNT_UNKNOWN": "open cash-secured-put count is unknown",
    "LONG_CALL_MAX_LOSS_EXCEEDS_CAP": ("full premium exceeds the $600 defined-risk cap"),
    "PMCC_PREVIEW_REQUIRES_LEAPS": "the long-dated call is not held",
    "PMCC_LEAPS_NOT_HELD": "the required long-dated call is not held",
    "COVERED_CALL_NOT_FULLY_COVERED": "fewer than 100 shares are recorded",
}


def _card_html(card: dict, *, tech_note: str = "") -> str:
    if "skipped" in card:
        return (f'<div class="panel"><div class="label">'
                f'{_esc(card["skipped"])}</div></div>')
    parts = ['<div class="panel candidate-card">',
             f'<div class="party-name">{_esc(card["headline"])}</div>',
             _badges(card.get("grades", {}))]
    if card.get("preview"):
        parts.append(f'<div class="notice watch">! '
                     f'{_esc(_PREVIEW_WARNING)}</div>')
    parts.append(_risk_line(card))
    if card.get("oi_change_line"):
        # Neutral positioning context (activity fact); reuses the plain label
        # class -- no color coupling to sign, never a grade.
        parts.append(f'<div class="label oi-line">{_esc(card["oi_change_line"])}</div>')
    if tech_note:
        parts.append(f'<div class="tech-line">{_esc(tech_note)}</div>')
    parts.append(_bbb_table(card.get("bbb", []),
                            absent_reason=card.get("bbb_absent")))
    parts.append(f'<div class="header-sub">{_esc(card.get("verdict", ""))}</div>')
    if card.get("countdown"):
        parts.append(f'<div class="label">{_esc(card["countdown"])}</div>')
    ladder = _scenario_table(card["scenarios"])
    if ladder:
        parts.append(f"<details><summary>payoff ladder</summary>{ladder}"
                     "</details>")
    parts.append("</div>")
    return "".join(parts)


def _group_html(grp: dict, *, rank: int, tech: dict | None = None) -> str:
    count = len(grp["cards"])
    count_label = f"{count} contract" + ("" if count == 1 else "s")
    head = (f'<summary><span class="group-heading">'
            f'<span class="group-rank" aria-label="Rank {rank}">{rank}</span>'
            f'<span>{_esc(grp["title"])}</span></span>'
            f'<span class="group-count">{count_label}</span></summary>')
    if not grp["cards"]:
        empty = grp.get("empty") or "none this cycle"
        body = f'<div class="empty">{_esc(empty)}</div>'
    else:
        note = _card_tech_line(grp["kind"], tech)
        cards = "".join(_card_html(c, tech_note=note) for c in grp["cards"])
        body = f'<div class="card-grid">{cards}</div>'
    return f'<details class="group-section">{head}{body}</details>'


def _prov_tag(context: dict | None) -> str:
    """Small provenance tag for every context-derived narrative block."""
    prov = (context or {}).get("provenance") or (
        "provenance not stated in context file")
    return f'<span class="prov">{_esc(prov)}</span>'


def _research_annotation_map(
        picks: list[dict], context: dict | None
        ) -> tuple[dict[str, Mapping[str, object]], str | None]:
    """Validate advisory annotations against the deterministic hero IDs.

    The context JSON may explain a current candidate, but it cannot add one or
    change its ordering.  An annotation whose candidate is not on today's
    board is dropped BEFORE validation, so one rotated-off card can no longer
    invalidate the whole set (the board rotates whenever ranking or data
    changes; that is normal, not a data error).  A malformed annotation for a
    current candidate is still ignored as research evidence and returned as a
    visible warning rather than partly rendered.

    Dropped keys are REPORTED, never silently swallowed: a dropped key is
    either stale research (the honest signal that the context JSON no longer
    covers the picks) or a mis-keyed annotation meant for a current card.
    Both are worth seeing, so the caller gets a visible notice either way.
    """
    from options_researcher.top3_context import (
        AnnotationValidationError,
        normalize_research_annotations,
    )

    raw = (context or {}).get("annotations")
    if raw is None:
        return {}, None
    if not isinstance(raw, dict):
        return {}, "research annotations are not an object — ignoring them"
    keys = [p["card"].get("top3_snapshot", {}).get("candidate_id")
            for p in picks]
    if any(not isinstance(key, str) for key in keys):
        return {}, "candidate identities are invalid — research annotations ignored"
    current_keys = frozenset(keys)
    current_annotations = {key: value for key, value in raw.items()
                           if key in current_keys}
    dropped = sorted(str(key) for key in raw if key not in current_keys)
    try:
        normalized = normalize_research_annotations(keys, current_annotations)
    except AnnotationValidationError as error:
        return {}, f"research annotations invalid ({error.code}) — ignoring them"
    notice = None
    if dropped:
        notice = (f"{len(dropped)} research annotation(s) do not match any "
                  f"card on today's board and were not rendered "
                  f"({', '.join(dropped)}) — the research context is stale "
                  "relative to the current picks, or a key is mistyped")
    return dict(normalized), notice


def _research_html(annotation: Mapping[str, object] | None, *,
                   data_as_of: str) -> str:
    """Render source-linked, advisory research for exactly one hero card."""
    if annotation is None:
        return ('<div class="notice watch">! Research evidence incomplete — '
                "no source-validated annotation for this candidate.</div>")
    market_as_of = annotation.get("market_as_of_date")
    if market_as_of != data_as_of:
        return ('<div class="notice watch">! Research evidence stale — annotation '
                f'market date {_esc(market_as_of or "unknown")} does not '
                f'match card date {_esc(data_as_of)}.</div>')
    raw_claims = annotation.get("claims")
    claims = raw_claims if isinstance(raw_claims, (list, tuple)) else ()
    if not claims:
        return ('<div class="notice watch">! Research evidence incomplete — '
                "the validated annotation has no claims.</div>")
    parts = ['<details class="research-details"><summary>'
             '✓ Research evidence · complete</summary>']
    for claim in claims:
        if not isinstance(claim, Mapping):
            continue
        source = claim.get("source_url")
        source_html = (f' <a href="{_esc(source)}">source</a>'
                       if isinstance(source, str) and source else
                       f' · source unknown: {_esc(claim.get("unknown_rationale", ""))}')
        parts.append(
            '<div class="narr"><span class="narr-k">'
            f'{_esc(claim["classification"])} / '
            f'{_esc(claim["date_certainty"])} / '
            f'{_esc(claim["source_tier"])}</span>'
            f'{_esc(claim["text"])}{source_html}<br>'
            f'<span class="narr-k">counter-case</span>'
            f'{_esc(claim["countercase"])}</div>')
    parts.append('<div class="label">Advisory context only; it does not '
                 'change membership or rank.</div></details>')
    return "".join(parts)


def _qm_card_context_html(pick: dict, symbol_context: Mapping[str, object] | None) -> str:
    """Render QM/MA evidence without converting stock evidence to option P&L."""
    if not isinstance(symbol_context, Mapping):
        return (
            '<div class="notice watch">! QM DATA BLOCKED — no exact-session '
            "context for this symbol.</div>"
        )
    if _qm_is_not_covered(symbol_context):
        # Structural, not staleness: the frozen study never measured this name,
        # and no refresh can change that. Say so per name instead of blanking
        # the panel for the names the study does cover.
        return (
            '<div class="notice info">QM NOT COVERED — '
            f"{_esc(str(symbol_context.get('reason', 'this name is not in the frozen QM study')))}"
            ". No QM context exists for it; the mechanical card above is "
            "unchanged.</div>"
        )
    if symbol_context.get("status") != "CURRENT":
        return (
            '<div class="notice watch">! QM DATA BLOCKED — '
            f"{_esc(symbol_context.get('reason', 'context is not current'))}"
            "</div>"
        )

    signal = str(symbol_context.get("signal_status", "UNKNOWN"))
    breakout_study = symbol_context.get("study")
    breakout_study = breakout_study if isinstance(breakout_study, Mapping) else {}
    parabolic_study = symbol_context.get("parabolic_study")
    parabolic_study = parabolic_study if isinstance(parabolic_study, Mapping) else {}
    breakout_status = breakout_study.get("evidence_status", "UNKNOWN")
    parabolic_status = parabolic_study.get("evidence_status", "UNKNOWN")
    parabolic_result = parabolic_study.get(
        "decision", "No frozen Parabolic conclusion is available."
    )
    context_note = (
        '<div class="notice info">QM is descriptive context only; it cannot change this '
        "mechanical card's membership, order, edge, or verdict.</div>"
    )
    parabolic = ""
    if symbol_context.get("parabolic_fire") is True:
        parabolic = (
            '<div class="notice watch">! PARABOLIC WARNING — the historical '
            "fade reading was rejected. This is displayed as research only and "
            f"does not change the mechanical selection, order, edge, or verdict. "
            f"Result: {_esc(parabolic_result)}</div>"
        )

    def _price(value: object) -> str:
        return f"${float(value):,.2f}" if isinstance(value, (int, float)) else "n/a"

    def _pct(value: object) -> str:
        return f"{float(value):+.1%}" if isinstance(value, (int, float)) else "n/a"

    def _count(value: object) -> int:
        return int(value) if isinstance(value, (int, float)) else 0

    candidate_key = _qm_candidate_key(pick)
    candidate_evidence = symbol_context.get("option_candidates")
    candidate_evidence = (
        candidate_evidence.get(candidate_key) if isinstance(candidate_evidence, Mapping) else None
    )
    move = (
        candidate_evidence.get("underlying_breakeven_frequency")
        if isinstance(candidate_evidence, Mapping)
        else None
    )
    if not isinstance(move, Mapping):
        move = {
            "label": "Underlying breakeven-move frequency unavailable.",
            "warning": (
                "Candidate-specific QM evidence is unavailable; actual option P&L was not tested."
            ),
        }
    history = (
        f"{_count(symbol_context.get('historical_breakout_fires'))} Breakout / "
        f"{_count(symbol_context.get('historical_parabolic_fires'))} Parabolic"
    )
    return (
        '<div class="qm-context">'
        f"{context_note}{parabolic}"
        '<div class="qm-row"><span class="narr-k">Current QM signal</span>'
        f"<strong>{_esc(signal)}</strong></div>"
        '<div class="qm-row"><span class="narr-k">Price vs moving averages</span>'
        f"Price {_price(symbol_context.get('price'))} · "
        f"20d {_price(symbol_context.get('sma20'))} "
        f"({_pct(symbol_context.get('price_vs_sma20'))}) · "
        f"50d {_price(symbol_context.get('sma50'))} "
        f"({_pct(symbol_context.get('price_vs_sma50'))}) · "
        f"200d {_price(symbol_context.get('sma200'))} "
        f"({_pct(symbol_context.get('price_vs_sma200'))})</div>"
        '<div class="qm-row"><span class="narr-k">Frozen study evidence</span>'
        f"{_esc(history)} fires for this name · "
        f"Breakout {_esc(breakout_status)} · "
        f"Parabolic {_esc(parabolic_status)}</div>"
        '<div class="qm-row"><span class="narr-k">Underlying move check</span>'
        f'{_esc(move["label"])}<br><span class="label">'
        f"{_esc(move['warning'])}</span></div>"
        '<div class="qm-row"><span class="narr-k">Actual option win rate</span>'
        "Unavailable — historical option quotes did not support an option-P&amp;L "
        "win-rate study.</div>"
        '<div class="qm-row"><span class="narr-k">Plain-language thesis</span>'
        f"{_esc(symbol_context.get('thesis', 'Unavailable.'))}</div>"
        '<div class="qm-row"><span class="narr-k">Counter-case</span>'
        f"{_esc(symbol_context.get('counter_case', 'Unavailable.'))}</div>"
        '<div class="label">Study date '
        f"{_esc(symbol_context.get('study_date', 'unknown'))} · "
        f"{_esc(symbol_context.get('provenance', 'provenance unavailable'))}"
        "</div></div>"
    )


def _hero_pick_html(
    pick: dict,
    annotation: Mapping[str, object] | None,
    *,
    data_as_of: str,
    slot: int,
    symbol_qm_context: Mapping[str, object] | None = None,
) -> str:
    """Render one deterministic hero pick plus optional lower-panel QM evidence."""
    card = pick["card"]
    preview_warn = (
        f'<div class="notice watch">! {_esc(_PREVIEW_WARNING)}</div>' if card.get("preview") else ""
    )
    snapshot = card.get("top3_snapshot") or {}
    ident = snapshot.get("candidate_id", "candidate identity unavailable")
    status = str(snapshot.get("selection_status", "UNKNOWN"))
    status_cls = {
        "ELIGIBLE": "good",
        "WATCH": "watch",
        "PLAN_ONLY": "bad",
        "DATA_BLOCKED": "bad",
    }.get(status, "unknown")
    symbol = {"ELIGIBLE": "✓", "WATCH": "!", "PLAN_ONLY": "×", "DATA_BLOCKED": "×"}.get(status, "?")
    head = (
        f'<div class="slot-label"><span>Pick {slot}</span>'
        f'<span class="policy-status {status_cls}">{symbol} '
        f"{_esc(status)}</span></div>"
        f'<div class="party-name">{_esc(card["headline"])}</div>'
        + _hero_badges(card.get("grades", {}))
        + preview_warn
        + _risk_line(card)
        + _bbb_table(card.get("bbb", []))
        + "<details><summary>Selection audit</summary>"
        + f'<div class="label">{_quality_audit(pick)} · '
        f"legacy score {pick['score']} · "
        f"{_esc(ident)}</div></details>"
    )
    qm_html = (
        _qm_card_context_html(pick, symbol_qm_context)
        if isinstance(symbol_qm_context, Mapping)
        else ""
    )
    return (
        f'<div class="hero-card {status_cls}">{head}'
        f"{qm_html}"
        f"{_research_html(annotation, data_as_of=data_as_of)}</div>"
    )


def _quality_audit(pick: dict) -> str:
    """Human form of the ranking basis: GREEN fraction + ordered levels."""
    card = pick.get("card") or {}
    grades = card.get("grades") or {}
    greens = sum(1 for value in grades.values() if value == "GREEN")
    parts = [f"GREEN {greens}/{len(grades)}" if grades else "no grades"]
    if card.get("rank_leader"):
        parts.append("lane leader")
    return " · ".join(parts)


def _top3_gap_reasons(data: dict) -> list[str]:
    """Explain an open Top-3 slot from the actual excluded card snapshots."""
    liquid_failures: list[str] = []
    outside_put_names: set[str] = set()
    plan_only = 0
    data_blocked = 0
    lane_names = {"put": "put", "cc": "covered call", "pmcc": "PMCC",
                  "leaps": "LEAPS", "long_call": "call"}
    for sec in data.get("symbols", []):
        if sec.get("display_only"):
            continue
        symbol = str(sec.get("symbol", "?"))
        for grp in sec.get("groups", []):
            lane = str(grp.get("kind", "contract"))
            for card in grp.get("cards", []):
                if "skipped" in card:
                    continue
                snapshot = card.get("top3_snapshot")
                if not isinstance(snapshot, dict):
                    continue
                policy = snapshot.get("policy")
                policy = policy if isinstance(policy, Mapping) else {}
                status = str(policy.get("status", "DATA_BLOCKED"))
                reasons = policy.get("reason_codes") or []
                liquidity = (card.get("grades") or {}).get("liquidity")
                if status == "ELIGIBLE" and liquidity == "RED":
                    strike = card.get("strike")
                    strike_text = (f"${float(strike):g} "
                                   if isinstance(strike, (int, float)) else "")
                    liquid_failures.append(
                        f"{symbol} {strike_text}{lane_names.get(lane, lane)} "
                        "passes portfolio policy but fails liquidity")
                if "CSP_SYMBOL_OUTSIDE_ALLOWED_NAMES" in reasons:
                    outside_put_names.add(symbol)
                if status == "PLAN_ONLY":
                    plan_only += 1
                elif status == "DATA_BLOCKED":
                    data_blocked += 1

    out = []
    if liquid_failures:
        out.append(liquid_failures[0] + ".")
    if outside_put_names:
        names = sorted(outside_put_names)
        joined = (names[0] if len(names) == 1 else
                  ", ".join(names[:-1]) + f" and {names[-1]}")
        out.append(f"{joined} puts are plan-only outside the registered "
                   "cash-secured-put names.")
    elif plan_only:
        out.append(f"{plan_only} remaining contract(s) are plan-only.")
    if data_blocked:
        out.append(f"{data_blocked} contract(s) are blocked by missing data.")
    if not out:
        out.append("No additional contract passed both policy and liquidity gates.")
    out.append("A blocked or illiquid idea is never promoted just to fill the list.")
    return out[:3]


def _empty_hero_slot_html(data: dict, slot: int) -> str:
    reasons = "".join(f"<li>{_esc(reason)}</li>"
                      for reason in _top3_gap_reasons(data))
    return (
        '<div class="hero-card unknown empty-slot">'
        f'<div class="slot-label"><span>Pick {slot}</span>'
        '<span class="policy-status unknown">? OPEN</span></div>'
        '<h3>No qualifying contract</h3>'
        '<div class="label">This is an intentional open slot, not missing UI.</div>'
        f'<ul class="gate-list">{reasons}</ul></div>')


def _blocked_qm_slot_html(
    qm_context: Mapping[str, object] | None, slot: int, *, reason: str | None = None
) -> str:
    context_reason = (qm_context or {}).get("reason") if isinstance(qm_context, Mapping) else None
    reason = reason or (context_reason if isinstance(context_reason, str) else None)
    return (
        '<div class="hero-card bad empty-slot">'
        f'<div class="slot-label"><span>Pick {slot}</span>'
        '<span class="policy-status bad">× DATA BLOCKED</span></div>'
        "<h3>QM context withheld</h3>"
        '<div class="label">Stale or missing QM data leaves the mechanical '
        "ranking unchanged and withholds this descriptive context.</div>"
        f'<div class="notice watch">! {_esc(reason or "QM context unavailable")}'
        "</div></div>"
    )


def _original_hero_html(
    data: dict, context: dict | None, qm_context: Mapping[str, object] | None
) -> str:
    """Render the unchanged mechanical Top-3 plus advisory research.

    Legacy agent-authored ``top_picks`` are deliberately not a membership
    source.  The only hero candidates come from ``select_top_picks`` over the
    assembled, point-in-time policy snapshots.
    """
    py_picks = select_top_picks(data, include_csp_watch=True)
    qualified_picks = select_top_picks(data)
    data_as_of = str(data.get("data_as_of") or "?")
    annotations, annotation_warning = _research_annotation_map(py_picks, context)
    notes = []
    legacy_picks = (context or {}).get("top_picks") or (context or {}).get(
        "legacy_top_picks_unusable"
    )
    if legacy_picks:
        notes.append(
            '<div class="notice info">Legacy agent-selected top_picks were '
            "ignored: only deterministic, policy-qualified cards "
            "may appear here.</div>"
        )
    if annotation_warning:
        notes.append(f'<div class="notice watch">! {_esc(annotation_warning)}</div>')
    if qualified_picks and len(qualified_picks) < len(py_picks):
        notes.append(
            f'<div class="notice watch">! {len(qualified_picks)} card(s) are fully '
            "policy-qualified; the remaining shown card(s) are WATCH only "
            "because equity-side assignment capital is not explicitly authorized.</div>"
        )
    cards = []
    for slot, pick in enumerate(py_picks, start=1):
        snapshot = pick["card"].get("top3_snapshot")
        ident = snapshot.get("candidate_id") if isinstance(snapshot, dict) else None
        annotation = annotations.get(ident) if isinstance(ident, str) else None
        cards.append(
            _hero_pick_html(
                pick,
                annotation,
                data_as_of=data_as_of,
                slot=slot,
            )
        )
    for slot in range(len(py_picks) + 1, 4):
        cards.append(_empty_hero_slot_html(data, slot))

    qualified_count = len(qualified_picks)
    watch_count = max(0, len(py_picks) - qualified_count)
    open_count = max(0, 3 - len(py_picks))
    qualified_cls = "good" if qualified_count else "unknown"
    return (
        '<section class="panel hero">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">Daily shortlist · TOP 3 PICKS TODAY</div>'
        "<h2>ORIGINAL MECHANICAL TOP 3</h2>"
        '<p class="header-sub">The existing membership and order are unchanged. '
        "QM context appears only in the separate descriptive section below.</p></div>"
        '<div class="hero-stats">'
        f'<div class="hero-stat {qualified_cls}"><strong>{qualified_count}</strong>'
        "<span>Eligible</span></div>"
        f'<div class="hero-stat watch"><strong>{watch_count}</strong>'
        "<span>Watch</span></div>"
        f'<div class="hero-stat unknown"><strong>{open_count}</strong>'
        "<span>Open</span></div></div></div>"
        f'{"".join(notes)}<div class="hero-grid">{"".join(cards)}</div></section>'
    )


def _qm_two_date_label_html(
    data: Mapping[str, object], qm_context: Mapping[str, object] | None
) -> str:
    """Print BOTH dates: QM's daily-bar session and the board's chain session.

    They are different data types with different natural frequencies (a daily
    bar for a session that is still open does not exist), so one date cannot
    describe both. Naming each one is what keeps the panel honest now that it
    no longer demands they be equal.
    """
    from options_researcher.schwab_chain_view import CHAIN_SOURCE, CONVENTION_LABEL

    if not isinstance(qm_context, Mapping):
        return ""
    qm_as_of = qm_context.get("as_of")
    board = data.get("data_as_of")
    if not isinstance(qm_as_of, str) or not qm_as_of:
        return ""
    board_text = (
        f"{CONVENTION_LABEL} {board}" if data.get("as_of_kind") == CHAIN_SOURCE
        else f"close {board}"
    )
    not_covered = qm_context.get("not_covered")
    not_covered = [str(name) for name in not_covered] if isinstance(
        not_covered, (list, tuple)) else []
    covered_note = (
        f" Not covered by the frozen study: {', '.join(sorted(not_covered))} "
        "(no QM context exists for these names)."
        if not_covered else ""
    )
    return (
        f'<div class="label">QM daily-bar context as of {_esc(qm_as_of)}; '
        f"board option chains {_esc(str(board_text))}."
        f"{_esc(covered_note)}</div>"
    )


def _qm_hero_html(data: dict, context: dict | None, qm_context: Mapping[str, object] | None) -> str:
    """Render lower QM context on mechanical slots, or three fail-closed slots."""
    data_as_of = str(data.get("data_as_of") or "?")
    block_reason = _qm_context_block_reason(data, qm_context)
    notes: list[str] = []
    if block_reason is not None:
        cards = [
            _blocked_qm_slot_html(qm_context, slot, reason=block_reason) for slot in range(1, 4)
        ]
        selected_count, open_count = 0, 3
    else:
        assert isinstance(qm_context, Mapping)
        picks = select_qm_top_picks(data, qm_context, include_csp_watch=True)
        annotations, annotation_warning = _research_annotation_map(picks, context)
        if annotation_warning:
            notes.append(f'<div class="notice watch">! {_esc(annotation_warning)}</div>')
        qm_symbols = qm_context.get("symbols")
        qm_symbols = qm_symbols if isinstance(qm_symbols, Mapping) else {}
        cards = []
        for slot, pick in enumerate(picks, start=1):
            snapshot = pick["card"].get("top3_snapshot")
            ident = snapshot.get("candidate_id") if isinstance(snapshot, Mapping) else None
            annotation = annotations.get(ident) if isinstance(ident, str) else None
            cards.append(
                _hero_pick_html(
                    pick,
                    annotation,
                    data_as_of=data_as_of,
                    slot=slot,
                    symbol_qm_context=qm_symbols.get(pick["symbol"]),
                )
            )
        for slot in range(len(cards) + 1, 4):
            cards.append(_empty_hero_slot_html(data, slot))
        selected_count, open_count = len(picks), max(0, 3 - len(picks))
    return (
        '<section class="panel qm-comparison">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">DESCRIPTIVE ONLY — NOT A TRADE RANKING</div>'
        "<h2>QM + MOVING-AVERAGE CONTEXT FOR MECHANICAL TOP 3</h2>"
        '<p class="header-sub">A secondary research context shown after the mechanical '
        "shortlist. These are the same mechanical cards in the same mechanical order. "
        "QM does not select, rank, validate, or change the edge or verdict of any "
        f"option contract.</p>{_qm_two_date_label_html(data, qm_context)}</div>"
        '<div class="hero-stats">'
        f'<div class="hero-stat good"><strong>{selected_count}</strong>'
        "<span>Shown</span></div>"
        f'<div class="hero-stat unknown"><strong>{open_count}</strong>'
        "<span>Open/blocked</span></div></div></div>"
        f'{"".join(notes)}<div class="hero-grid">{"".join(cards)}</div></section>'
    )


_QM_MOVEMENT_SIGNAL_STATUSES = frozenset(
    {"BREAKOUT", "PARABOLIC WARNING", "BREAKOUT + PARABOLIC WARNING"}
)
_QM_MOVEMENT_BANNER = (
    "UNVALIDATED SIGNAL -- descriptive screen; no forward evidence exists "
    "until the SS5 study reports; not an entry recommendation; no book path."
)
_QM_MOVEMENT_EMPTY = (
    "No movement fires today. Expected — these patterns fired ~46 times in nine years "
    "across twelve names."
)


def _qm_movement_lane_html(
    data: Mapping[str, object], qm_context: Mapping[str, object] | None
) -> str:
    """Render read-only QM fires without attaching frozen-study evidence."""
    movement = qm_context.get("movement_symbols") if isinstance(qm_context, Mapping) else None
    movement = movement if isinstance(movement, Mapping) else {}
    fires = [
        (str(symbol), item)
        for symbol, item in movement.items()
        if isinstance(item, Mapping)
        and item.get("status") == "CURRENT"
        and item.get("signal_status") in _QM_MOVEMENT_SIGNAL_STATUSES
    ]
    label_context: Mapping[str, object] | None = qm_context
    if isinstance(qm_context, Mapping) and isinstance(qm_context.get("movement_as_of"), str):
        label_context = {**qm_context, "as_of": qm_context["movement_as_of"], "not_covered": []}
    if not fires:
        body = f'<p class="label">{_esc(_QM_MOVEMENT_EMPTY)}</p>'
    else:
        cards = []
        for symbol, item in fires:
            coverage = item.get("frozen_study_coverage")
            coverage_html = (
                '<div class="label">not covered by the frozen study</div>'
                if coverage == "NOT_COVERED"
                else ""
            )
            cards.append(
                '<article class="movement-card">'
                f"<h3>{_esc(symbol)}</h3>"
                f'<div class="label">Current QM signal: {_esc(str(item["signal_status"]))}</div>'
                f"{coverage_html}</article>"
            )
        body = f'<div class="card-grid">{"".join(cards)}</div>'
    return (
        '<section class="panel qm-movement">'
        '<div class="section-header"><div>'
        '<div class="eyebrow">DESCRIPTIVE ONLY — NOT A TRADE RANKING</div>'
        '<h2>QM MOVEMENT LANE</h2>'
        '<p class="header-sub">Current-session mechanical fires from adjusted cached OHLCV, '
        'shown in watch-universe order. This does not select, order, gate, or validate '
        'a mechanical pick.</p>'
        f'<div class="label">{_esc(_QM_MOVEMENT_BANNER)}</div>'
        f"{_qm_two_date_label_html(data, label_context)}</div></div>{body}</section>"
    )


def _hero_html(
    data: dict, context: dict | None, qm_context: Mapping[str, object] | None = None
) -> str:
    return (
        _original_hero_html(data, context, qm_context)
        + _qm_movement_lane_html(data, qm_context)
        + _qm_hero_html(data, context, qm_context)
    )


def _quant_want_html(qm_context: Mapping[str, object] | None) -> str:
    quant = (qm_context or {}).get("quant_want") if isinstance(qm_context, Mapping) else None
    if not isinstance(quant, Mapping) or not quant:
        return ""
    cards = []
    labels = (("trend", "Trend"), ("momentum", "Stock momentum"), ("low_max", "Low-MAX"))
    for key, label in labels:
        item = quant.get(key)
        if not isinstance(item, Mapping):
            continue
        cards.append(
            '<div class="market-card">'
            f"<h3>{_esc(label)} · {_esc(item.get('status', 'UNKNOWN'))}</h3>"
            f"<p>{_esc(item.get('plain_language', 'No background available.'))}</p>"
            "</div>"
        )
    if not cards:
        return ""
    return (
        '<section class="panel market-panel">'
        '<div class="eyebrow">Market background only</div>'
        "<h2>Quant-want background</h2>"
        '<p class="header-sub">Trend does not rank these contracts. Momentum '
        "and low-MAX stay off until their separate phase gates report results.</p>"
        f'<div class="market-grid">{"".join(cards)}</div>'
        f'<div class="label">Committed source {_esc(quant.get("source_commit", "unknown"))}'
        "</div></section>"
    )


def _market_html(context: dict | None) -> str:
    """Market-context strip; omitted honestly when the context has none."""
    market = (context or {}).get("market")
    if not isinstance(market, dict) or not market:
        return ""
    prov = _prov_tag(context)
    parts = ['<section class="panel market-panel">',
             '<div class="eyebrow">Backdrop</div>',
             f"<h2>Market context {prov}</h2>"]
    summary = str(market.get("summary") or "").strip()
    if summary:
        lead, separator, _tail = summary.partition(". ")
        lead = lead + ("." if separator else "")
        parts.append(f'<div class="market-summary">{_esc(lead)}</div>')
    if market.get("regime"):
        parts.append(f'<div class="regime-label">Regime · '
                     f'{_esc(market["regime"])}</div>')
    notes = market.get("notes") or []
    if summary or notes:
        parts.append('<details><summary>Full market narrative &amp; notes</summary>')
        if summary:
            parts.append(f'<div class="narr">{_esc(summary)}</div>')
        for note in notes:
            parts.append(f'<div class="label">&middot; {_esc(note)}</div>')
        parts.append('</details>')
    parts.append("</section>")
    return "".join(parts)


def _sources_html(sources: list | None) -> str:
    """Render legacy URL strings and v2 source-metadata objects as links."""
    items = []
    for source in sources or []:
        u = source.get("url") if isinstance(source, Mapping) else source
        u = str(u or "")
        if u.startswith("http://") or u.startswith("https://"):
            items.append(f'<li><a href="{_esc(u)}">{_esc(u)}</a></li>')
        else:
            items.append(f"<li>{_esc(u)}</li>")
    if not items:
        return ""
    return (f"<details><summary>sources ({len(items)})</summary>"
            f'<ul class="label">{"".join(items)}</ul></details>')


def _symbol_context_html(symbol: str, context: dict | None) -> str:
    """Per-symbol news/catalysts from the context JSON, provenance-labeled
    and source-linked; empty string (omitted) when absent."""
    sym_ctx = ((context or {}).get("symbols") or {}).get(symbol)
    if not isinstance(sym_ctx, dict):
        return ""
    prov = _prov_tag(context)
    parts = ['<details class="context-details"><summary>'
             'Company context, catalysts &amp; sources</summary>']
    if sym_ctx.get("news_summary"):
        parts.append(f'<div class="narr"><span class="narr-k">news</span>'
                     f'{_esc(sym_ctx["news_summary"])} {prov}</div>')
    for cat in sym_ctx.get("catalysts") or []:
        if isinstance(cat, dict) and cat.get("what"):
            when = cat.get("date") or "date unknown"
            confirmed = ("" if cat.get("confirmed", True)
                         else " [UNCONFIRMED/estimated]")
            parts.append(f'<div class="label">catalyst {_esc(when)}'
                         f"{_esc(confirmed)}: {_esc(cat['what'])} {prov}</div>")
    parts.append(_sources_html(sym_ctx.get("sources")))
    parts.append('</details>')
    return "".join(parts)


def _pinned_html(data: dict) -> str:
    """Core-names strip: owner-pinned visibility, explicitly not ranked."""
    pinned = pinned_picks(data)
    if not pinned:
        return ""
    names = " / ".join(_esc(rec["symbol"]) for rec in pinned)
    cards = ""
    for rec in pinned:
        symbol, pick = rec["symbol"], rec["pick"]
        if pick is None:
            cards += (f'<div class="pinned-card watch"><div class="slot-label">'
                      f'<span>{_esc(symbol)}</span>'
                      '<span class="policy-status watch">GAP</span></div>'
                      '<div class="label">no eligible liquid card this run '
                      '— pinning never fabricates a candidate; see the '
                      'symbol panel below for why each card is out.</div>'
                      '</div>')
            continue
        card = pick["card"]
        snapshot = card.get("top3_snapshot")
        status = (snapshot.get("selection_status")
                  if isinstance(snapshot, Mapping) else None) or "?"
        status_cls = {"ELIGIBLE": "good", "WATCH": "watch"}.get(
            str(status), "watch")
        cards += (f'<div class="pinned-card {status_cls}">'
                  f'<div class="slot-label"><span>{_esc(symbol)}</span>'
                  f'<span class="policy-status {status_cls}">'
                  f'{_esc(str(status))}</span></div>'
                  f'<div class="party-name">{_esc(card.get("headline", ""))}'
                  '</div>'
                  + _hero_badges(card.get("grades", {}))
                  + _risk_line(card)
                  + _bbb_table(card.get("bbb", [])) + '</div>')
    return ('<section class="panel hero"><div class="section-header"><div>'
            '<div class="eyebrow">CORE NAMES</div>'
            f'<h2>{names} — ALWAYS SHOWN</h2>'
            '<p>owner-pinned visibility — not ranked; these cards do not '
            'compete with or reorder the Top-3 shortlist.</p></div></div>'
            f'<div class="hero-grid">{cards}</div></section>')


_COMPOSITE_GRADE_CLASS = {"A": "good", "B": "watch", "C": "unknown"}
_COMPOSITE_TREND_CLASS = {"UP": "good", "DOWN": "bad", "MIXED": "watch"}
_COMPOSITE_VOL_CLASS = {"CHEAP": "good", "RICH": "watch", "NEUTRAL": "unknown"}
_COMPOSITE_REGIME_CLASS = {"TYPICAL": "good", "HIGH_DISPERSION": "watch"}
_COMPOSITE_INTERNALS_CLASS = {"CONFIRM": "good", "VETO": "bad", "NEUTRAL": "unknown"}


def _composite_badge(label: str, state: str, cls_map: Mapping[str, str]) -> str:
    cls = cls_map.get(state, "unknown")
    return (f'<span class="status-badge {cls}">{_esc(label)} '
            f'{_esc(state)}</span>')


def _as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _composite_card_html(card: Mapping[str, object]) -> str:
    """One four-angle confluence card. DATA_BLOCKED angles render their
    literal state (never hidden) plus, when present, the block reason."""
    grade = str(card.get("grade") or "C")
    trend = _as_mapping(card.get("trend"))
    vol_premium = _as_mapping(card.get("vol_premium"))
    regime = _as_mapping(card.get("regime"))
    internals = _as_mapping(card.get("internals"))
    badges = (
        _composite_badge("TREND", str(trend.get("state", "DATA_BLOCKED")),
                         _COMPOSITE_TREND_CLASS)
        + _composite_badge("VOL", str(vol_premium.get("state", "DATA_BLOCKED")),
                           _COMPOSITE_VOL_CLASS)
        + _composite_badge("REGIME", str(regime.get("state", "DATA_BLOCKED")),
                           _COMPOSITE_REGIME_CLASS)
        + _composite_badge("INTERNALS", str(internals.get("state", "DATA_BLOCKED")),
                           _COMPOSITE_INTERNALS_CLASS)
    )
    reasons = [
        f"{name}: {angle.get('reason')}"
        for name, angle in (("trend", trend), ("vol", vol_premium),
                            ("regime", regime), ("internals", internals))
        if angle.get("data_blocked") and angle.get("reason")
    ]
    reason_html = (f'<div class="label">{_esc("; ".join(reasons))}</div>'
                  if reasons else "")
    as_of = card.get("max_asof") or card.get("asof") or "?"
    return (
        '<div class="panel composite-card">'
        '<div class="slot-label"><span>' + _esc(str(card.get("symbol", "?")))
        + f'</span><span class="status-badge {_COMPOSITE_GRADE_CLASS.get(grade, "unknown")}">'
        f'GRADE {_esc(grade)}</span></div>'
        f'<div class="party-badges">{badges}</div>'
        f'{reason_html}'
        f'<div class="label">as of {_esc(str(as_of))}</div>'
        '</div>'
    )


def _composite_html(data: dict) -> str:
    """Composite signal board panel: display-only, non-verdict-bearing
    four-angle confluence cards (options_researcher.composite_signals).
    Omitted honestly when nothing was assembled."""
    cards = data.get("composite_signals") or []
    if not cards:
        return ""
    grid = "".join(_composite_card_html(card) for card in cards)
    return (
        '<section class="panel"><div class="section-header"><div>'
        '<div class="eyebrow">COMPOSITE SIGNAL LANE</div>'
        '<h2>Composite signal board — display-only</h2>'
        '<p>Four independent angles (trend, vol premium, regime, options-'
        'market internals) per name. Not verdict-bearing, not FIRE-capable; '
        'writes nothing to ledger/ or positions.</p></div></div>'
        f'<div class="card-grid">{grid}</div></section>'
    )


def _evidence_attr(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _evidence_row_html(row: object) -> str:
    family = str(_evidence_attr(row, "family", "?"))
    membership = str(_evidence_attr(row, "membership", "UNKNOWN"))
    family_state = str(_evidence_attr(row, "family_state", "UNKNOWN"))
    detail = str(_evidence_attr(row, "detail", ""))
    evaluation_session = _evidence_attr(row, "evaluation_session")
    run_date = _evidence_attr(row, "run_date")
    raw_states = _evidence_attr(row, "symbol_states", ())
    raw_states = (
        raw_states if isinstance(raw_states, (list, tuple)) else ()
    )
    state_chips = "".join(
        '<span class="evidence-chip">'
        f'<strong>{_esc(str(_evidence_attr(state, "label", "raw")))}</strong> '
        f'{_esc(str(_evidence_attr(state, "state", "UNKNOWN")))}</span>'
        for state in raw_states
    )
    dates = []
    if evaluation_session:
        dates.append(f"evaluation {evaluation_session}")
    if run_date:
        dates.append(f"run {run_date}")
    date_html = (
        f'<div class="evidence-dates">{_esc(" · ".join(dates))}</div>'
        if dates
        else ""
    )
    sources = _evidence_attr(row, "sources", ())
    sources = sources if isinstance(sources, (list, tuple)) else ()
    source_items = "".join(
        "<li>"
        f'{_esc(str(_evidence_attr(source, "kind", "source")))}: '
        f'<code>{_esc(str(_evidence_attr(source, "path", "?")))}</code> '
        f'({_esc(str(_evidence_attr(source, "date", "?")))})'
        "</li>"
        for source in sources
    )
    sources_html = (
        f'<ul class="evidence-sources">{source_items}</ul>'
        if source_items
        else ""
    )
    detail_html = (
        f'<div class="evidence-detail">{_esc(detail)}</div>'
        if detail
        else ""
    )
    return (
        '<div class="evidence-row">'
        '<div class="evidence-row-head">'
        f'<strong>{_esc(family)}</strong>'
        f'<span class="status-badge unknown">Ritual '
        f"{_esc(family_state)}</span></div>"
        f'<div class="evidence-membership">{_esc(membership)}</div>'
        f'<div class="evidence-chips">{state_chips}</div>'
        f"{date_html}{detail_html}{sources_html}</div>"
    )


def _hypothesis_panel_html(evidence: object | None) -> str:
    """Escaped display-only evidence; never consumed by ranking or policy."""
    if evidence is None:
        return ""
    rows = _evidence_attr(evidence, "hypotheses", ())
    rows = rows if isinstance(rows, (list, tuple)) else ()
    intraday = _evidence_attr(evidence, "intraday")
    hypothesis_rows = "".join(_evidence_row_html(row) for row in rows)
    intraday_html = (
        '<div class="intraday-evidence">'
        '<h4>Intraday context — descriptive only</h4>'
        f"{_evidence_row_html(intraday)}</div>"
        if intraday is not None
        else ""
    )
    if not hypothesis_rows and not intraday_html:
        return ""
    return (
        '<details class="hypothesis-evidence">'
        '<summary>Hypothesis evidence</summary>'
        '<div class="evidence-grid">'
        f"{hypothesis_rows}</div>{intraday_html}</details>"
    )


def _as_of_chip_label(data: Mapping[str, object]) -> str:
    """Header chip label. A pre-close session is never called a close.

    The chip ages with the board: a pre-close badge next to a date that is days
    old reads as "captured today" at a glance, which is the one thing the chip
    must never imply. Past the WARN bar it says how old, and past the BLOCK bar
    it says STALE.
    """
    import config
    from options_researcher.schwab_chain_view import CHAIN_SOURCE, HEADER_CHIP_LABEL

    if data.get("as_of_kind") != CHAIN_SOURCE:
        return "Market close"
    age = data.get("chain_age_sessions")
    if not isinstance(age, int):
        return f"{HEADER_CHIP_LABEL} · age UNKNOWN"
    if age >= config.CHAIN_STALE_BLOCK_SESSIONS:
        return f"STALE · {HEADER_CHIP_LABEL} · {age} sessions old"
    if age >= config.CHAIN_STALE_WARN_SESSIONS:
        return f"{HEADER_CHIP_LABEL} · {age} sessions old"
    return HEADER_CHIP_LABEL


def _as_float(value: object, default: float = 0.0) -> float:
    """Best-effort float for display formatting only."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    return float(value)


def _is_fresh_section(sec: Mapping[str, object]) -> bool:
    from options_researcher.schwab_chain_view import CHAIN_SOURCE

    return sec.get("chain_source") == CHAIN_SOURCE


def _close_stat_label(sec: Mapping[str, object]) -> str:
    """Name the price for what it is; a 15:45 mid is not a close."""
    if sec.get("close_kind") == "preclose_mid_1545":
        return "Spot 15:45 pre-close"
    return "Close"


def _iv_rank_text(sec: Mapping[str, object]) -> str:
    value = sec.get("iv_rank")
    if not isinstance(value, (int, float)) or value != value:
        return "unavailable"
    label = sec.get("iv_rank_label")
    text = f"{float(value):.2f}"
    return f"{text} {label}" if isinstance(label, str) and label else text


def _atm_iv_stat_html(sec: Mapping[str, object]) -> str:
    value = sec.get("atm_iv")
    if not isinstance(value, (int, float)) or value != value:
        return ""
    return ('<div class="symbol-stat"><span>ATM IV</span><strong>'
            f"{float(value):.1%}</strong></div>")


def _section_source_html(sec: Mapping[str, object]) -> str:
    """State each symbol's quote source and the exact instant of its price."""
    from options_researcher.schwab_chain_view import CONVENTION_LABEL

    parts: list[str] = []
    if _is_fresh_section(sec):
        parts.append(
            '<div class="notice info">Quotes: '
            f"{_esc(CONVENTION_LABEL)} session "
            f'{_esc(str(sec.get("as_of", "?")))}; price '
            f"${_as_float(sec.get('close')):,.2f} is the 15:45 spot mid from "
            "the same capture instant, not a closing price. Moving averages "
            f'and trend use closes through {_esc(str(sec.get("technicals_as_of", "?")))}.'
            "</div>")
    refusal = sec.get("fresh_refusal_reason")
    if isinstance(refusal, str) and refusal:
        parts.append(f'<div class="notice watch">! {_esc(refusal)}</div>')
    return "".join(parts)


def _feature_unavailable_html(sec: Mapping[str, object]) -> str:
    """Name every feature this session could not compute, and why.

    Fail-closed display: the affected badges read UNKNOWN rather than taking a
    default value, so this line is what tells the reader the badge is missing
    evidence rather than reporting a measured neutral.
    """
    items = sec.get("feature_unavailable")
    items = items if isinstance(items, (list, tuple)) else ()
    rows = [
        f'{_esc(str(item.get("field", "?")))}: {_esc(str(item.get("reason", "?")))}'
        for item in items
        if isinstance(item, Mapping)
    ]
    if not rows:
        return ""
    return ('<div class="notice watch">! Unavailable for this session — '
            + "; ".join(rows)
            + ". The badges these feed show UNKNOWN (never a default value), "
            "and scenario tables that need them state their absence.</div>")


def _blocked_html(blocked: list[dict]) -> str:
    """Fail-visible strip: every symbol that could not be analyzed, with its
    machine-readable reason. A missing symbol must never just disappear."""
    if not blocked:
        return ""
    rows = ""
    for rec in blocked:
        last = rec.get("last_known_date") or "never cached"
        display_only = (
            f' <span class="status-badge unknown">'
            f"{_esc(DISPLAY_ONLY_LABEL)}</span>"
            if rec.get("display_only")
            else ""
        )
        evidence = _hypothesis_panel_html(
            rec.get("hypothesis_evidence")
        )
        rows += (
            f'<li><strong>{_esc(str(rec.get("symbol", "?")))}</strong>'
            f"{display_only} · "
            f'{_esc(str(rec.get("reason_code", "?")))} · '
            f'{_esc(str(rec.get("detail", "")))} · '
            f'last known data: {_esc(str(last))}{evidence}</li>'
        )
    return ('<section class="panel"><div class="eyebrow">DATA BLOCKED</div>'
            '<div class="notice watch">! These symbols are in the display '
            'universe but could not be analyzed this run — shown so a gap '
            'is never mistaken for a clean board.</div>'
            f'<ul class="blocked-list">{rows}</ul></section>')


def _run_exit_code(
    blocked: list[dict], *, qm_context: Mapping[str, object] | None = None
) -> int:
    """0 for a clean or data-gapped run; 1 when any symbol failed on an
    UNEXPECTED error (programming failure) so cron/launchd never reports a
    clean rebuild over one."""
    qm_unexpected = isinstance(qm_context, Mapping) and qm_context.get("unexpected") is True
    return 1 if any(rec.get("unexpected") for rec in blocked) or qm_unexpected else 0


def render(
    data: dict,
    *,
    context: dict | None = None,
    context_warning: str | None = None,
    qm_context: Mapping[str, object] | None = None,
) -> str:
    """Render the assemble() dict (plus optional research context) into one
    self-contained HTML string. Pure string templating: no file I/O, no
    network, no external assets. Every value from `data` / `context` is
    html.escape()'d before embedding. Page order: compact metadata header ->
    original Top-3 -> descriptive QM comparison -> composite signal board ->
    quant/market background -> pinned names ->
    per-symbol panels (card grid)."""
    qm_context = enrich_qm_context_with_candidates(data, qm_context)
    symbols_html = ""
    for sec in data["symbols"]:
        tech = sec.get("technicals")
        ranked_groups = _rank_groups_for_display(sec["groups"], tech=tech)
        groups = "".join(
            _group_html(group, rank=rank, tech=tech)
            for rank, group in enumerate(ranked_groups, start=1)
        )
        rank_note = (
            '<div class="strategy-rank-note">'
            "Strategy rank: 1 is the strongest current fit; "
            "this display order does not change any policy or trade rule."
            "</div>"
        )
        tech_line = sec.get("technicals_line")
        tech_html = f'<div class="tech-line">{_esc(tech_line)}</div>' if tech_line else ""
        stale_html = ""
        if sec.get("features_stale"):
            stale_html = (
                '<div class="notice watch">! IV features are from '
                f"{_esc(sec.get('features_as_of', '?'))}, older than the "
                f"chain date ({_esc(sec.get('as_of', '?'))}) — IV-rank/VRP "
                "badges are STALE and this symbol is excluded from the "
                "Top-3 shortlist.</div>"
            )
        display_only_html = (
            f'<div><span class="status-badge unknown">'
            f"{_esc(DISPLAY_ONLY_LABEL)}</span></div>"
            if sec.get("display_only")
            else ""
        )
        display_date_stat = (
            f'<div class="symbol-stat"><span>Display data</span><strong>'
            f"{_esc(sec.get('as_of', '?'))}</strong></div>"
            if sec.get("display_only")
            else ""
        )
        symbols_html += (
            '<section class="panel symbol-panel">'
            '<div class="symbol-header"><div>'
            '<div class="eyebrow">Symbol review</div>'
            f"<h2>{_esc(sec['symbol'])}</h2>{display_only_html}</div>"
            '<div class="symbol-stats">'
            f'<div class="symbol-stat"><span>{_esc(_close_stat_label(sec))}'
            f"</span><strong>${sec['close']:,.2f}</strong></div>"
            f'<div class="symbol-stat"><span>IV rank</span><strong>'
            f"{_esc(_iv_rank_text(sec))}</strong></div>"
            f"{_atm_iv_stat_html(sec)}{display_date_stat}</div></div>"
            f'<div class="symbol-body">{_section_source_html(sec)}'
            f"{_feature_unavailable_html(sec)}{stale_html}{tech_html}"
            f"{_symbol_context_html(sec['symbol'], context)}{rank_note}{groups}"
            f"{_hypothesis_panel_html(sec.get('hypothesis_evidence'))}</div>"
            "</section>"
        )
    data_as_of = data.get("data_as_of") or "no cached data"
    display_data_as_of = data.get("display_data_as_of") or data_as_of
    display_date_meta = (
        f'<span class="meta-chip"><strong>All display data</strong> '
        f"{_esc(display_data_as_of)}</span>"
        if display_data_as_of != data_as_of
        else ""
    )
    researched_on = (context or {}).get("researched_on")
    research_meta = (
        f'<span class="meta-chip"><strong>Research updated</strong> {_esc(researched_on)}</span>'
        if researched_on
        else ""
    )
    warn_html = (
        f'<div class="notice watch">! {_esc(context_warning)}</div>' if context_warning else ""
    )
    age_html = _chain_age_html(data)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Options Attractiveness</title>"
        f"<style>{_STYLE}</style></head><body>"
        '<header class="app-header"><div class="app-header-inner">'
        '<div><div class="eyebrow">Options research · Attractiveness</div>'
        "<h1>Which options look attractive today?</h1>"
        '<p class="header-sub">Policy-gated candidates with at-expiration '
        "scenario ranges.</p></div>"
        '<div class="meta-row">'
        f'<span class="meta-chip"><strong>{_esc(_as_of_chip_label(data))}'
        f"</strong> {_esc(data_as_of)}</span>{display_date_meta}{research_meta}"
        '<span class="meta-chip">Paper research</span>'
        '</div></div></header><main class="page-body">'
        f"{age_html}"
        f"{warn_html}"
        f"{_blocked_html(data.get('blocked') or [])}"
        f"{_hero_html(data, context, qm_context)}"
        f"{_composite_html(data)}"
        f"{_quant_want_html(qm_context)}"
        f"{_market_html(context)}"
        f"{_pinned_html(data)}"
        f"{symbols_html}"
        '<footer class="page-footer">Payoffs are at-expiration scenarios, '
        "not predictions. Income annualization uses 365 calendar days; "
        "realized-volatility inputs use 252 trading sessions. Quotes move "
        "intraday; verify the live broker quote before making a decision. "
        "Annualized income is simple, not compounded. This page and the "
        "mission-control dashboard date INDEPENDENTLY: this board can ride a "
        "15:45 pre-close capture while mission control reports its own "
        "closes-derived date, so a difference between the two is expected, "
        "not an error.</footer>"
        "</main></body></html>"
    )


def _build_and_write(**assemble_kwargs) -> tuple[str, int]:
    """Assemble, render, write; return (abs_path, exit_code). The exit code
    is nonzero when any symbol failed unexpectedly (see _run_exit_code) so
    unattended runs never look clean over a programming failure."""
    from options_researcher.qm_dashboard import load_qm_context

    with _input_root_cwd():
        data = assemble(**assemble_kwargs)
        qm_context = load_qm_context(data.get("data_as_of") or "")
    context, warning = load_context(data.get("data_as_of") or "")
    out_html = render(
        data,
        context=context,
        context_warning=warning,
        qm_context=qm_context,
    )
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    # tmp + os.replace so a mid-write crash can never leave a truncated page
    # over the last good one (same convention as h7_data_gate receipts).
    tmp_path = f"{OUTPUT_PATH}.{os.getpid()}.tmp"
    with open(tmp_path, "w") as f:
        f.write(out_html)
    os.replace(tmp_path, OUTPUT_PATH)
    abs_path = os.path.abspath(OUTPUT_PATH)
    print(f"wrote {abs_path}")
    blocked = data.get("blocked") or []
    for rec in blocked:
        print(f"BLOCKED {rec.get('symbol')}: {rec.get('reason_code')} ({rec.get('detail')})")
    print("open it in your browser to see the scenario tables")
    return abs_path, _run_exit_code(blocked, qm_context=qm_context)


def main(**assemble_kwargs) -> str:
    """Assemble real (or injected) candidates, load the dated research
    context (honest fallback when absent), render, write to OUTPUT_PATH.
    Read-only over project data; the only write is the HTML file."""
    abs_path, _exit_code = _build_and_write(**assemble_kwargs)
    return abs_path


if __name__ == "__main__":
    import sys

    if "--json" in sys.argv:
        print(sections_json())
    else:
        raise SystemExit(_build_and_write()[1])

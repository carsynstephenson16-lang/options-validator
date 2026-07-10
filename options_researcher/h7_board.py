"""Board/session allocation resolver (7b-0.1, owner decision 2026-07-10).

H7_LANE_PRIORITY (v1.2(1,2)) and H7C_TIEBREAK (v1.2(3)) are ENFORCED here,
not just documented in config. Pure function, deterministic for any input
iteration order; every displaced candidate carries an explicit rejection
reason. The watcher prints ENTRY-OK only for survivors.

Scope note (v1.2(6)): the registered isolated-lane diagnostic backtest does
NOT use this resolver -- live portfolio caps and cross-lane competition are a
different estimand. Per-trade risk and one-open-position-per-symbol/lane are
enforced inside the diagnostic runner itself.
"""

from __future__ import annotations

import config

REJECT_A_TAKES = "lane_a_takes_underlying"
REJECT_OPEN = "underlying_open"
REJECT_TAKEN = "underlying_taken"
REJECT_BASKET = "h7c_basket_cap"
REJECT_SLEEVE = "sleeve_exhausted"


def _lane_rank(lane: str) -> int:
    return config.H7_LANE_PRIORITY.index(lane)


def _credit_to_width(cand: dict) -> float:
    """v1.2(3) tie-break key: executable credit / width, lane c only."""
    if cand["lane"] != "c":
        return 0.0
    action = cand["action"]
    return float(action["credit"]) / float(action["width"])


def _at_risk(cand: dict) -> float:
    action = cand["action"]
    return float(action.get("max_loss", action.get("cost", 0.0)))


def resolve_board(candidates: list[dict], *, open_h7c: int = 0,
                  sleeve_left: float = 0.0,
                  open_symbols: tuple = ()) -> tuple[list[dict], list[dict]]:
    """Resolve same-board contention. candidates: [{symbol, lane, session,
    action}] where `action` is the decide_lane_* dict. Returns (accepted,
    rejected); rejected items are copies with a "rejection" reason.

    Order of consideration (deterministic for any input order):
      1. chronological opportunity order (session ascending);
      2. lane priority a > b > c within a session (H7_LANE_PRIORITY);
      3. lane-c candidates ranked by executable credit-to-width, descending
         (H7C_TIEBREAK);
      4. symbol ascending as the final tie-break.
    Constraints: lane a defeats lane b for a shared underlying; one candidate
    per underlying vs the live book and earlier acceptances; H7c concurrency
    (H7C_MAX_CONCURRENT incl. open book positions); sleeve capacity netted
    by each acceptance's at-risk."""
    order = sorted(candidates, key=lambda c: (
        str(c["session"]), _lane_rank(c["lane"]),
        -_credit_to_width(c), c["symbol"].upper()))
    book_open = {s.upper() for s in open_symbols}
    accepted_lane_by_symbol: dict[str, str] = {}
    c_open = int(open_h7c)
    left = float(sleeve_left)
    accepted: list[dict] = []
    rejected: list[dict] = []

    for cand in order:
        sym = cand["symbol"].upper()
        if sym in book_open:
            rejected.append({**cand, "rejection": REJECT_OPEN})
        elif sym in accepted_lane_by_symbol:
            if accepted_lane_by_symbol[sym] == "a" and cand["lane"] == "b":
                rejected.append({**cand, "rejection": REJECT_A_TAKES})
            else:
                rejected.append({**cand, "rejection": REJECT_TAKEN})
        elif cand["lane"] == "c" and c_open >= config.H7C_MAX_CONCURRENT:
            rejected.append({**cand, "rejection": REJECT_BASKET})
        elif _at_risk(cand) > left:
            rejected.append({**cand, "rejection": REJECT_SLEEVE})
        else:
            accepted.append(cand)
            accepted_lane_by_symbol[sym] = cand["lane"]
            left -= _at_risk(cand)
            if cand["lane"] == "c":
                c_open += 1
    return accepted, rejected

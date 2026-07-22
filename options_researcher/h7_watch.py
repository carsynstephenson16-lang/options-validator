"""H7 daily watcher -- reports lane states per name; NEVER trades, never
mutates positions (candidate -> position only via the owner editing
data/positions/h7_positions.csv). Run:
    uv run python -m options_researcher.h7_watch [--as-of YYYY-MM-DD]

7b-0 contract (ledger H7_7B_NOGO remediation):
- ONE completed session: closes and the chain snapshot must both end exactly
  at evaluation_session(run date); anything else is a DATA-GAP line. No
  stale-chain fallback, no wall-clock DTE math, no intraday rows.
- ENTRY-OK is printed ONLY when strategies.h7_lanes.decide_lane_* returned an
  executable action from those same inputs; the watcher carries no lane
  logic of its own. Armed-but-unexecutable prints NO-EXECUTABLE. Actionable
  output requires a matching successful H7 data-gate receipt.
- FAIL CLOSED: unreadable/malformed position book -> exit 2, no evaluation;
  a symbol whose next report date is unknown -> EARNINGS-UNKNOWN, no entry.

Lane states: EXCLUDED / POSITION-OPEN / EARNINGS-UNKNOWN / EARNINGS-BAN /
WATCH-ONLY / QUIET / BASKET-CAP / BUDGET-SPENT / NO-EXECUTABLE / ENTRY-OK.
"""

from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import config
from data.underlying_closes import adjustment_factor, load_closes_adjusted
from options_researcher import h7_signals as sig
from options_researcher.chains import load_range
from options_researcher.h7_board import resolve_board
from options_researcher.h7_cohort import (
    CohortUnavailableError,
    load_registered_cohort,
)
from options_researcher.h7_earnings import (
    GATE_BANNED,
    GATE_CLEAR,
    GATE_UNKNOWN,
    earnings_gate,
    load_assertions,
)
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import (
    DIAGNOSTIC_SOURCE_HASH_VERSION,
    canonical_json,
    config_hash,
    diagnostic_source_hash,
)
from research.receipts import (
    changed_input_files,
    input_file_record,
    input_files,
    load_receipt,
    make_receipt,
    write_immutable_receipt,
)
from strategies.h7_lanes import decide_lane_a, decide_lane_b, decide_lane_c

H7_POSITIONS_PATH = Path("data/positions/h7_positions.csv")


def validate_data_gate_receipt(path: Path, *, evaluation_session: str,
                               names: list[str] | tuple[str, ...],
                               included: list[str] | tuple[str, ...] | None
                               = None) -> dict:
    """Validate the pass file and re-hash every file it named.

    ``names`` is always the FULL official scope: the receipt's ``scope`` must
    equal ``scope_identity(names)`` so the evidence provably covers the whole
    universe (anti-cherry-pick), regardless of trimming.

    ``included`` (Option C trim-at-append): when None the receipt must be a
    whole-universe GO covering every name -- today's behavior, unchanged. When
    a subset is given, the whole-universe GO requirement is RELAXED to a
    per-symbol GO check over the included names only; excluded names may be
    NO_GO in the same full-scope receipt without failing validation."""
    receipt = load_receipt(Path(path), expected_type="data_gate")
    expected_scope = scope_identity(names)
    if receipt.get("scope") != expected_scope:
        raise ValueError("data-gate receipt scope is not the official current scope")
    if receipt.get("evaluation_session") != evaluation_session:
        raise ValueError("data-gate receipt session does not match watcher")
    if included is None:
        if receipt.get("whole_universe_verdict") != "GO":
            raise ValueError("data-gate receipt is not a successful whole-universe pass")
        if receipt.get("go_count") != len(names):
            raise ValueError("data-gate receipt does not cover every current name")
    else:
        if not included:
            raise ValueError("data-gate receipt: empty included set")
        per_symbol = receipt.get("symbols", {})
        not_go = sorted(s for s in included
                        if per_symbol.get(s, {}).get("verdict") != "GO")
        if not_go:
            raise ValueError(
                f"data-gate receipt is not GO for included names: {not_go}")
    if not receipt.get("source_health_receipt_hash"):
        raise ValueError("data-gate receipt is not linked to source health")
    source_path = receipt.get("source_health_receipt_path")
    if not source_path:
        raise ValueError("data-gate receipt has no source-health receipt path")
    source = load_receipt(Path(source_path), expected_type="source_health")
    if (source.get("receipt_hash") != receipt["source_health_receipt_hash"]
            or source.get("evaluation_session") != evaluation_session
            or source.get("scope") != expected_scope):
        raise ValueError("linked source-health receipt is stale or mismatched")
    changed_source = changed_input_files(source)
    if changed_source:
        raise ValueError(f"source-health inputs changed since pass: {changed_source}")
    if receipt.get("config_hash") != config_hash():
        raise ValueError("data-gate receipt config identity is stale")
    if receipt.get("source_hash") != diagnostic_source_hash():
        raise ValueError("data-gate receipt source identity is stale")
    changed = []
    for label, stored in sorted(receipt.get("input_files", {}).items()):
        actual = input_file_record(Path(stored["path"]))
        if canonical_json(actual) != canonical_json(stored):
            changed.append(label)
    if changed:
        raise ValueError(f"data-gate inputs changed since pass: {changed}")
    return receipt


def _watcher_receipt(*, result_rows: list[dict], names: list[str],
                     evaluation_session: str, run_date: date,
                     data_gate_receipt: dict, errors: list[str]) -> dict:
    paths = {"assertions": Path("data/earnings/gating_v3.csv"),
             "position_book": H7_POSITIONS_PATH}
    for symbol in names:
        paths[f"close:{symbol}"] = Path(".cache/underlying") / f"{symbol}.parquet"
        paths[f"chain:{symbol}"] = Path(".cache/chains") / \
            f"{symbol}_{evaluation_session}.parquet"
    return make_receipt("watcher_decision", {
        "evaluation_session": evaluation_session,
        "requested_run_date": run_date.isoformat(),
        "scope": scope_identity(names),
        "data_gate_receipt_hash": data_gate_receipt["receipt_hash"],
        "source_health_receipt_hash": data_gate_receipt[
            "source_health_receipt_hash"],
        "input_files": input_files(paths),
        "rows": result_rows,
        "errors": errors,
        "actionable_count": sum(
            1 for row in result_rows if row.get("actionable")),
        "config_hash": config_hash(),
        "source_hash": diagnostic_source_hash(),
        "source_hash_contract": DIAGNOSTIC_SOURCE_HASH_VERSION,
    })


def evaluation_session(run_date: date) -> date:
    """The latest COMPLETED XNYS session strictly before `run_date`. The
    watcher never evaluates the run date itself: its EOD is not final (the
    top-up policy in data/recent_topup.py excludes it for the same reason),
    and an intraday snapshot must never masquerade as a close."""
    from data.cache_runner import trading_days

    run_iso = run_date.isoformat()
    days = trading_days((run_date - timedelta(days=14)).isoformat(), run_iso)
    prior = [d for d in days if d < run_iso]
    return date.fromisoformat(prior[-1])


def check_alignment(closes: pd.Series, chain_day: str | None,
                    eval_iso: str) -> str | None:
    """Gap reason, or None when closes end EXACTLY at the evaluation session
    and the chain snapshot is EXACTLY that session. No fallback, no mixing:
    every decide_lane_* input shares one completed session or nothing runs."""
    last = str(closes.index[-1])[:10]
    if last > eval_iso:
        return (f"closes contain {last}, after session {eval_iso} -- possible "
                f"intraday row, refuse (re-pull closes)")
    if last < eval_iso:
        return (f"closes end {last}, need {eval_iso} -- stale cache "
                f"(run the closes refresh / data.recent_topup)")
    if chain_day != eval_iso:
        return (f"chain snapshot {chain_day or 'MISSING'}, need {eval_iso} "
                f"-- stale cache (run data.recent_topup)")
    return None


def _lane_state(*, armed: bool, admitted: bool, gate: str,
                has_open: bool, route: str, budget_left: float,
                basket_full: bool) -> str:
    """Human-readable REASON ladder only. The final ENTRY-OK is authorized
    exclusively by a non-None decide_lane_* action in assemble_name."""
    if has_open:
        return "POSITION-OPEN"
    if gate == GATE_UNKNOWN:
        return "EARNINGS-UNKNOWN"   # fail closed: next report date unknown
    if gate == GATE_BANNED:
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


def _decide(lane: str, *, symbol: str, closes: pd.Series, chain: pd.DataFrame,
            spot: float, today: date, month_spent: float, banned: bool,
            open_h7c: int):
    """Dispatch to the SINGLE decision authority (strategies.h7_lanes)."""
    if lane == "lane_a":
        return decide_lane_a(closes=closes, chain=chain, spot=spot,
                             today=today, month_spent=month_spent, banned=banned)
    if lane == "lane_b":
        return decide_lane_b(closes=closes, chain=chain, spot=spot,
                             today=today, month_spent=month_spent, banned=banned)
    return decide_lane_c(symbol=symbol, closes=closes, chain=chain, spot=spot,
                         today=today, month_spent=month_spent, banned=banned,
                         open_h7c=open_h7c)


def assemble_name(*, symbol: str, closes: pd.Series, chain: pd.DataFrame,
                  today: date, assertions: list, known_as_of,
                  open_positions: tuple, spot: float | None = None,
                  open_h7c: int = 0, month_spent: float = 0.0) -> dict:
    """`closes` MUST be split-adjusted and end at the evaluation session;
    `chain` MUST be that same session's snapshot (main enforces via
    check_alignment). `spot` is the RAW price aligned with the chain's
    strikes -- defaults to the last adjusted close (correct live, after a
    symbol's final split). Earnings state comes from the typed point-in-time
    gate; UNKNOWN fails closed."""
    spot = float(closes.iloc[-1]) if spot is None else float(spot)
    rv = sig.rv_annualized(closes, config.H7_RV_LOOKBACK_D)
    iv = sig.atm_iv_90d(chain, spot, today)
    route = sig.iv_route(iv=iv, rv=rv)
    gate, gate_reason = earnings_gate(symbol, today, assertions,
                                      known_as_of=known_as_of)
    banned = gate != GATE_CLEAR   # decide_lane_* fail closed on non-CLEAR
    has_open = symbol in open_positions
    budget_left = config.H7_MONTHLY_AT_RISK - month_spent

    card: dict = {
        "symbol": symbol, "spot": spot, "rv21": rv, "iv90": iv, "route": route,
        "budget_left": budget_left, "earnings_gate": gate,
        "earnings_reason": gate_reason,
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
                          "admitted_contracts": 0, "action": None}
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
        state = _lane_state(armed=armed_fn(closes), admitted=admitted,
                            gate=gate, has_open=has_open,
                            route=lane_route, budget_left=budget_left,
                            basket_full=basket_full)
        action = None
        if state == "ENTRY-OK":
            action = _decide(lane, symbol=symbol, closes=closes, chain=chain,
                             spot=spot, today=today, month_spent=month_spent,
                             banned=banned, open_h7c=open_h7c)
            if action is None:
                # armed + admitted + routed, but no executable structure at
                # frozen tolerances/gates. NEVER report ENTRY-OK without an
                # action (7b-0 exit condition).
                state = "NO-EXECUTABLE"
        card[lane] = {"state": state, "admitted_contracts": n,
                      "route": lane_route, "action": action}
    return card


class H7BookError(RuntimeError):
    """The H7 position book is unreadable or malformed. FAIL CLOSED: no
    entry can be evaluated against an unknown book (NO-GO remediation --
    the old code treated any book error as an empty book, which silently
    lifted the one-per-underlying, lane-c-concurrency, and sleeve gates)."""


_BOOK_COLUMNS = ("symbol", "lane", "opened", "at_risk", "closed")


def open_h7_book(today: date, *, path: Path = H7_POSITIONS_PATH
                 ) -> tuple[tuple, int, float]:
    """(open symbols, open lane-c count, at-risk opened this calendar month).

    Book conventions: append-only; closing a position sets `closed`
    (YYYY-MM-DD), never deletes the row. month_spent sums at_risk over rows
    OPENED this month regardless of closed status -- the sleeve caps risk
    OPENED per month, so a same-month close must not resurrect budget."""
    symbols: set[str] = set()
    open_c, month_spent = 0, 0.0
    month = today.isoformat()[:7]
    try:
        with path.open() as f:
            reader = csv.DictReader(f)
            if tuple(reader.fieldnames or ()) != _BOOK_COLUMNS:
                raise H7BookError(
                    f"{path}: header {reader.fieldnames} != {_BOOK_COLUMNS}")
            for i, row in enumerate(reader, start=2):
                sym = (row["symbol"] or "").strip().upper()
                if not sym:
                    raise H7BookError(f"{path}:{i}: empty symbol")
                opened = (row["opened"] or "").strip()
                date.fromisoformat(opened)  # malformed date -> ValueError
                at_risk = float(row["at_risk"])
                closed = (row["closed"] or "").strip()
                if closed:
                    date.fromisoformat(closed)
                else:
                    symbols.add(sym)
                    if (row["lane"] or "").strip().lower() == "c":
                        open_c += 1
                if opened.startswith(month):
                    month_spent += at_risk
    except H7BookError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise H7BookError(f"{path}: {type(e).__name__}: {e}") from e
    return tuple(sorted(symbols)), open_c, month_spent


def main(argv: list[str] | None = None) -> int:
    import argparse
    from datetime import datetime
    from zoneinfo import ZoneInfo

    parser = argparse.ArgumentParser(
        description="H7 daily watcher (alerts only, never trades)")
    parser.add_argument(
        "--as-of",
        help="evaluate the last completed session before this date "
             "(default: today, America/New_York); useful against a cache "
             "that has not been topped up today")
    parser.add_argument("--data-gate-receipt", default=None,
                        help="successful, matching H7 data-gate pass file")
    parser.add_argument("--write-receipt", default=None,
                        help="immutable watcher decision receipt path")
    args = parser.parse_args(argv)

    ny_today = datetime.now(ZoneInfo("America/New_York")).date()
    run_date = date.fromisoformat(args.as_of) if args.as_of else ny_today
    if run_date > ny_today:
        print(f"--as-of {run_date} is in the future; refusing.")
        return 2
    eval_date = evaluation_session(run_date)
    eval_iso = eval_date.isoformat()
    # Gate evidence remains bound to the whole official scope.  The frozen
    # window cohort controls ONLY which names are eligible for entry
    # evaluation; never substitute it into receipt-scope validation.
    gate_names = watch_universe()
    try:
        cohort = load_registered_cohort()
    except CohortUnavailableError as exc:
        print(f"H7 WATCH REFUSED -- {exc}")
        return 2
    registered_names = set(cohort.included) | set(cohort.excluded)
    if set(gate_names) != registered_names:
        print("H7 WATCH REFUSED -- frozen cohort does not cover the current "
              "official scope; refusing to infer eligible names")
        return 2
    entry_names = [name for name in gate_names if name in cohort.included]
    if not args.data_gate_receipt:
        print("H7 WATCH REFUSED -- actionable output requires a matching "
              "data-gate receipt (run source health, then data gate first).")
        return 2
    try:
        data_gate_receipt = validate_data_gate_receipt(
            Path(args.data_gate_receipt), evaluation_session=eval_iso,
            names=gate_names, included=entry_names)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"H7 WATCH REFUSED -- invalid/stale data-gate receipt: "
              f"{type(exc).__name__}: {exc}")
        return 2
    # 252 trading sessions of signal history plus weekend/holiday slack
    start_iso = (eval_date - timedelta(days=560)).isoformat()

    if args.as_of:
        # historical replay: the information cutoff is the evaluation
        # session's ACTUAL close, never the wall clock (7b-2R finding 4 --
        # datetime.now() here was lookahead: a replay of last Tuesday could
        # see announcements published after Tuesday's close)
        from data.cache_runner import session_close_utc
        known_as_of = session_close_utc(eval_iso)
    else:
        known_as_of = datetime.now(ZoneInfo("UTC"))
    try:
        assertions = load_assertions()
    except Exception as e:  # fail closed: cannot verify earnings state
        print(f"H7 EARNINGS-ASSERTIONS ERROR -- refusing to evaluate entries: "
              f"{type(e).__name__}: {e}")
        return 2
    try:
        open_syms, open_c, month_spent = open_h7_book(eval_date)
    except H7BookError as e:
        print(f"H7 BOOK ERROR -- refusing to evaluate entries (fail closed): {e}")
        return 2

    print(f"H7 WATCH session={eval_iso} run={run_date.isoformat()} "
          f"(registered f1887c9d + v1.2 f880b4d1 + v1.3 6faa4945: "
          f"historical diagnostic WITHDRAWN, forward paper is the sole "
          f"verdict path; allocation-grade -- board resolver enforced; "
          f"alerts only, never trades)")
    print(f"sleeve: ${config.H7_MONTHLY_AT_RISK - month_spent:.0f} of "
          f"${config.H7_MONTHLY_AT_RISK} left this month; "
          f"open H7c {open_c}/{config.H7C_MAX_CONCURRENT}")
    for symbol in gate_names:
        if symbol not in cohort.included:
            print(f"{symbol}: EXCLUDED (frozen at registration: "
                  f"{cohort.excluded[symbol]})")

    # pass 1: assemble only the registration-frozen entry cohort (per-symbol
    # gates + decide actions).  Excluded names are deliberately never loaded.
    cards: list[tuple[str, dict]] = []
    watch_errors: list[str] = []
    for symbol in entry_names:
        try:
            closes = load_closes_adjusted(symbol, start_iso, eval_iso,
                                          allow_oos=True)
            if closes.empty:
                raise RuntimeError("no cached underlying closes")  # R12
            chains_by_day = load_range(symbol, eval_iso, eval_iso, allow_oos=True)
            chain = chains_by_day.get(eval_iso)
            if chain is None:
                raise RuntimeError(f"chain snapshot missing for {eval_iso}")
            chain_day = eval_iso if chain is not None else None
            gap = check_alignment(closes, chain_day, eval_iso)
            if gap:
                raise RuntimeError(gap)
        except Exception as e:  # a gap is a report line, not a crash
            print(f"{symbol}: DATA-GAP ({type(e).__name__}: {e}) -- skipped")
            watch_errors.append(f"{symbol}: {type(e).__name__}: {e}")
            continue
        raw_spot = float(closes.iloc[-1]) * adjustment_factor(symbol, eval_iso)
        cards.append((symbol, assemble_name(
            symbol=symbol, closes=closes, chain=chain, today=eval_date,
            assertions=assertions, known_as_of=known_as_of,
            open_positions=open_syms, spot=raw_spot,
            open_h7c=open_c, month_spent=month_spent)))

    # pass 2: board-level allocation (7b-0.1) -- ENTRY-OK survives only if
    # the resolver accepts it; every displaced candidate shows its reason
    candidates = [
        {"symbol": symbol, "lane": lane_key[-1], "session": eval_iso,
         "action": card[lane_key]["action"]}
        for symbol, card in cards
        for lane_key in ("lane_a", "lane_b", "lane_c")
        if card[lane_key]["state"] == "ENTRY-OK"
    ]
    _, displaced = resolve_board(
        candidates, open_h7c=open_c,
        sleeve_left=config.H7_MONTHLY_AT_RISK - month_spent,
        open_symbols=open_syms)
    displaced_by_key = {(d["symbol"], d["lane"]): d["rejection"]
                        for d in displaced}
    for symbol, card in cards:
        for lane_key in ("lane_a", "lane_b", "lane_c"):
            reason = displaced_by_key.get((symbol, lane_key[-1]))
            if reason and card[lane_key]["state"] == "ENTRY-OK":
                card[lane_key]["state"] = f"DISPLACED({reason})"
        print(
            f"{symbol}: spot {card['spot']:.2f} IV90 {card['iv90']:.0%} "
            f"RV21 {card['rv21']:.0%} route={card['route']} | "
            f"a={card['lane_a']['state']} b={card['lane_b']['state']} "
            f"c={card['lane_c']['state']}"
        )
        for lane_key in ("lane_a", "lane_b", "lane_c"):
            if card[lane_key]["state"] == "ENTRY-OK":
                print(f"    {lane_key} action: {card[lane_key]['action']}")
    result_rows = []
    for symbol, card in cards:
        for lane_key in ("lane_a", "lane_b", "lane_c"):
            lane = card[lane_key]
            result_rows.append({
                "symbol": symbol,
                "lane": lane_key,
                "state": lane["state"],
                "actionable": lane["state"] == "ENTRY-OK",
                "action": (json.dumps(lane["action"], sort_keys=True,
                                       default=str)
                           if lane["action"] is not None else None),
            })
    receipt = _watcher_receipt(
        result_rows=result_rows, names=gate_names, evaluation_session=eval_iso,
        run_date=run_date, data_gate_receipt=data_gate_receipt,
        errors=watch_errors)
    receipt_path = (Path(args.write_receipt) if args.write_receipt else
                    Path("reports/h7_receipts") / data_gate_receipt[
                        "scope"]["scope_id"] / "watcher" / f"{eval_iso}.json")
    try:
        write_immutable_receipt(receipt, receipt_path)
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"H7 WATCH ERROR -- cannot write decision receipt: "
              f"{type(exc).__name__}: {exc}")
        return 2
    print(f"immutable decision receipt {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

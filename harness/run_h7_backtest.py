"""harness/run_h7_backtest.py -- offline chunked runner for the H7
isolated-lane diagnostic (7b-1). Mirrors harness/run_backtest.py: Lumibot
stays the engine; this module only loads cached data, builds the
per-contract feed (calls AND puts), runs per-symbol/per-lane/per-year
chunks, and collects closed-trade dicts.

BLOCKED UNTIL 7b-3: this runner is integration-tested on synthetic fixtures
only. No full-window H7 experiment may run before the 7b-2 gates pass, a
diagnostic_attempt ledger record is committed, and the owner's independent
review clears 7b-3 (ledger H7_7B_NOGO + H7_OWNER_DECISIONS_7B01).

Chunking (memory, not statistics), same contract as the H1 runner:
  * interior chunks allow entries through Dec 31 and simulate
    H7_MAX_HOLD_DAYS into the next year so every position exits inside its
    own chunk;
  * a position exiting inside the next chunk's calendar blocks that chunk's
    DECISIONS until after the exit day (one-position-per-symbol/lane holds
    across the seam);
  * the FINAL chunk stops decisions H7_MAX_HOLD_DAYS before `end`: no entry
    is attempted whose execution/exit horizon the data window cannot cover.

Signal state is continuous across chunks by construction: signals derive
from the full adjusted-closes series (loaded once, sliced <= session inside
the strategy), never from chunk-local state.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta

import config
from data import pandas_feed

# Longest possible hold: entry executes at T+1 (one session after the
# decision) on a contract at the top of the long DTE band; expiration bounds
# the exit even if every scheduled exit is data-gapped to the wire. Both
# terms frozen in config (7b-2R finding 5).
H7_MAX_HOLD_DAYS = config.H7_LONG_DTE_BAND[1] + config.H7_MAX_HOLD_BUFFER_D

# How far back the closes series must reach before `start` so the first
# in-window session is already warm (sessions -> calendar-day slack).
_CLOSES_LOOKBACK_DAYS = config.H7_CLOSES_LOOKBACK_D


def _year_chunks(start: Date, end: Date) -> list[tuple[str, str, str]]:
    """(sim_start, decision_cutoff, sim_end) per calendar year, ISO strings.
    decision_cutoff is INCLUSIVE; sim_end never passes `end`."""
    chunks = []
    for year in range(start.year, end.year + 1):
        sim_start = max(Date(year, 1, 1), start)
        year_end = Date(year, 12, 31)
        cutoff = min(year_end, end - timedelta(days=H7_MAX_HOLD_DAYS))
        sim_end = min(year_end + timedelta(days=H7_MAX_HOLD_DAYS), end)
        if cutoff < sim_start:
            continue
        chunks.append((sim_start.isoformat(), cutoff.isoformat(),
                       sim_end.isoformat()))
    return chunks


def _load_closes(symbol: str, start_iso: str, end_iso: str, *,
                 allow_oos: bool):
    from data.underlying_closes import load_closes, load_closes_adjusted
    lookback = (Date.fromisoformat(start_iso)
                - timedelta(days=_CLOSES_LOOKBACK_DAYS)).isoformat()
    adj = load_closes_adjusted(symbol, lookback, end_iso, allow_oos=allow_oos)
    raw = load_closes(symbol, lookback, end_iso, allow_oos=allow_oos)
    return adj, raw


def _run_chunk(lane: str, symbol: str, sim_start: str, cutoff: str,
               sim_end: str, blocked_until: str | None, *,
               closes_adj, closes_raw, assertions, allow_oos: bool,
               known_as_of_fn=None, eligible: set[str] | None = None,
               month_risk_seed: dict | None = None) -> dict:
    """One symbol, one lane, one chunk, one Lumibot backtest -- offline.
    Returns {"trades", "cancelled", "quarantined", "month_risk"}.
    `eligible` is the canonical manifest's eligible-session set (7b-2R
    finding 2): cache files outside it are refused, never parsed, and
    reported. `month_risk_seed` carries risk already opened per calendar
    month into this chunk (7b-2R finding 5: a January entry from a December
    signal must still bind January's sleeve in the next chunk)."""
    from lumibot.backtesting import PandasDataBacktesting
    from lumibot.entities import TradingFee

    from strategies.h7_backtest import H7LaneBacktest

    refused: list[str] = []
    chains = pandas_feed.load_cached_chains(
        symbol, sim_start, sim_end, allow_oos=allow_oos,
        eligible=eligible, refused=refused)
    quarantined = [{"symbol": symbol, "lane": lane, "session": day,
                    "stage": "chain_load",
                    "reason": "present_but_excluded_by_manifest"}
                   for day in refused]
    empty = {"trades": [], "cancelled": [], "quarantined": quarantined,
             "month_risk": dict(month_risk_seed or {})}
    if not chains:
        return empty
    feed = pandas_feed.build_option_data(
        chains, symbol, exp_max=sim_end, rights=("C", "P"))
    if not feed:
        return empty

    fee = TradingFee(per_contract_fee=config.COMMISSION_PER_CONTRACT)
    end_dt = datetime.combine(
        Date.fromisoformat(sim_end) + timedelta(days=1), datetime.min.time())
    parameters = {
        "lane": lane,
        "symbol": symbol,
        "chain_provider": lambda sym, iso_day: chains.get(iso_day),
        "closes_adj": closes_adj,
        "closes_raw": closes_raw,
        "assertions": assertions,
        "tradeable_assets": set(feed.keys()),
        "entry_cutoff": cutoff,
        "blocked_until": blocked_until,
        "month_risk_seed": dict(month_risk_seed or {}),
    }
    if known_as_of_fn is not None:
        parameters["known_as_of_fn"] = known_as_of_fn
    _result, strat = H7LaneBacktest.run_backtest(
        PandasDataBacktesting,
        backtesting_start=datetime.combine(
            Date.fromisoformat(sim_start), datetime.min.time()),
        backtesting_end=end_dt,
        pandas_data=feed,
        budget=config.STARTING_CAPITAL,
        buy_trading_fees=[fee],
        sell_trading_fees=[fee],
        benchmark_asset=None,
        risk_free_rate=0.0,
        analyze_backtest=False,
        show_plot=False,
        save_tearsheet=False,
        show_tearsheet=False,
        show_progress_bar=False,
        quiet_logs=True,
        save_logfile=False,
        save_stats_file=False,
        parameters=parameters,
    )
    if strat._pos is not None:
        # fail LOUD: an unresolved position would silently bias PnL
        raise RuntimeError(
            f"{symbol}/{lane} chunk {sim_start}..{sim_end} ended with an "
            f"unresolved position: state={strat._pos.state} "
            f"queued={strat._pos.queued_exit_iso} "
            f"reasons={strat._pos.exit_reasons}")
    if strat._pending is not None:
        # a decision whose execution session lies outside the chunk is a
        # disclosed cancellation, not an error
        strat.cancelled_entries.append({
            "symbol": symbol, "lane": lane,
            "signal_date": strat._pending["signal_date"],
            "planned_execution": strat._pending["execute_iso"],
            "cancelled_on": sim_end, "reason": "window_end",
            "kind": strat._pending["action"]["kind"],
        })
    return {"trades": list(strat.closed_trades),
            "cancelled": list(strat.cancelled_entries),
            "quarantined": quarantined,
            "month_risk": dict(strat._month_risk)}


def run_lane(lane: str, start: str | None = None, end: str | None = None, *,
             symbols: list[str] | None = None, allow_oos: bool = False,
             assertions: list | None = None,
             known_as_of_fn=None, manifest: dict | None = None) -> dict:
    """Run one lane across symbols/chunks; returns {"trades", "cancelled",
    "quarantined"}.

    `manifest` is the canonical eligible-session manifest (7b-2R finding 2):
    the runner loads ONLY chain files it names eligible; files inside
    excluded intervals are quarantined and reported, never consumed. When
    None it is computed from data.h7_manifest (identical enumeration to the
    audit); the gated 7b-3 launch path passes the receipt-bound manifest
    and separately verifies the two are equal.

    The registered H7 window (H7_BACKTEST_START..H7_BACKTEST_END) extends
    past IN_SAMPLE_END as a DISCLOSED non-blind diagnostic; reaching it
    requires allow_oos=True, which only the 7b-3 launch path (behind a
    committed diagnostic_attempt ledger record) may pass."""
    if lane not in ("a", "b", "c"):
        raise ValueError(f"unknown H7 lane: {lane!r}")
    if assertions is None:
        from options_researcher.h7_earnings import load_assertions
        assertions = load_assertions()
    start_d = Date.fromisoformat(start or config.H7_BACKTEST_START)
    end_d = Date.fromisoformat(end or config.H7_BACKTEST_END)
    if manifest is None:
        from data.h7_manifest import eligible_manifest
        manifest = eligible_manifest(
            symbols=symbols or config.H7_BACKTEST_SYMBOLS,
            start=start_d.isoformat(), end=end_d.isoformat())

    trades: list[dict] = []
    cancelled: list[dict] = []
    quarantined: list[dict] = []
    for symbol in symbols or config.H7_BACKTEST_SYMBOLS:
        eligible = set(manifest[symbol]["eligible"])
        closes_adj, closes_raw = _load_closes(
            symbol, start_d.isoformat(), end_d.isoformat(), allow_oos=allow_oos)
        blocked_until: str | None = None
        month_risk: dict = {}
        chunks = _year_chunks(start_d, end_d)
        for i, (sim_start, cutoff, sim_end) in enumerate(chunks):
            out = _run_chunk(
                lane, symbol, sim_start, cutoff, sim_end, blocked_until,
                closes_adj=closes_adj, closes_raw=closes_raw,
                assertions=assertions, allow_oos=allow_oos,
                known_as_of_fn=known_as_of_fn, eligible=eligible,
                month_risk_seed=month_risk)
            chunk_trades = out["trades"]
            trades.extend(chunk_trades)
            cancelled.extend(out["cancelled"])
            quarantined.extend(out["quarantined"])
            # 7b-2R finding 5: months straddling the seam keep their opened
            # risk; a later same-month signal in the next chunk cannot
            # reuse a sleeve the previous chunk already consumed
            month_risk = out["month_risk"]
            if i + 1 < len(chunks):
                next_start = chunks[i + 1][0]
                tail_exits = [t["exit_date"] for t in chunk_trades
                              if t.get("exit_date") and t["exit_date"] >= next_start]
                blocked_until = max(tail_exits) if tail_exits else None
    trades.sort(key=lambda t: (t["entry_date"], t["symbol"]))
    return {"lane": lane, "trades": trades, "cancelled": cancelled,
            "quarantined": quarantined}

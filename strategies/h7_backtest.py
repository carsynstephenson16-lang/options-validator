"""strategies/h7_backtest.py -- H7 isolated-lane diagnostic strategy (7b-1).

Registration f1887c9d + amendments v1.1/v1.2; execution semantics per the
owner's 2026-07-10 instruction (ledger H7_OWNER_DECISIONS_7B01). Lumibot
remains the engine (fills, cash, fees); decisions delegate to the SAME
strategies.h7_lanes.decide_lane_* functions the watcher executes.

ENTRY CAUSALITY (strict T -> T+1):
  1. completed session T supplies adjusted closes, raw spot, the earnings
     information set (known_as_of <= end of T), and the T EOD chain;
  2. the signal and the selected contract are FROZEN from T;
  3. entry is attempted only on the next trading session T+1;
  4. at T+1 every execution-time requirement is revalidated: contract
     existence, DTE band (F1: an edge-selected contract that slipped out of
     band overnight cancels), earnings gate CLEAR, two-sided books, leg
     liquidity, executable cost/credit within the sleeve;
  5. fills happen at T+1's adverse pre-widened quotes (feed haircut) plus
     per-contract commissions;
  6. absent/invalid T+1 data cancels the entry with an explicit reason --
     never carried, chased, or substituted. No same-bar signal-and-fill.

EXIT CAUSALITY:
  * EOD-observed triggers (profit targets, stops) observed at session S are
    queued and execute no earlier than S+1;
  * date-known exits (H7_CLOSE_AT_DTE / H7C_CLOSE_AT_DTE, the H7c
    pre-earnings hard close) are queued a session early so execution lands ON
    the intended session, not one late;
  * a missing exit quote leaves an explicit pending state retried on the
    first valid later session; unresolved at expiration fails LOUD;
  * simultaneous triggers retain every reason; the primary reason follows
    the frozen priority pre_earnings > scheduled_dte > underlying_stop >
    credit_stop > profit_target.

FROZEN TRIGGER INTERPRETATIONS (commissions affect realized P&L but never
redefine thresholds; haircut-adverse marks, applied exactly once):
  * long call TP: conservative liquidation >= 2 x actual entry debit;
  * call debit spread TP: conservative liquidation >= 0.75 x spread width;
  * H7c TP: executable buyback debit <= 0.5 x actual entry credit;
  * H7c stop: EOD executable buyback debit >= 2 x actual entry credit;
  * underlying stops compare the ADJUSTED close to the decide-layer stop_ref.

ESTIMAND (v1.2(6)): isolated per-symbol/per-lane diagnostic. Portfolio caps
and cross-lane competition are NOT simulated; per-trade risk (the decide
functions' sleeve check, per symbol-lane entry month) and one open position
per symbol/lane still bind. 1 contract per position (F3).

Fidelity note F5: engine fill confirmation is observed on the following
iteration (H1 idiom), so the first trigger observation happens one session
after entry confirmation -- a conservative lag, never look-ahead.

GUARD NOTE: the two Lumibot order-method calls live ONLY inside
_engine_submit_leg (owner-authorized exception to the live-trading content
guard, facts.log HOOK_BYPASS_AUTHORIZATION_7B1 2026-07-10; this is the
offline PandasDataBacktesting engine -- no broker endpoint exists).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date
from datetime import datetime, timedelta

import config
from data import pandas_feed
from data.thetadata_adapter import passes_liquidity
from options_researcher.h7_earnings import (
    GATE_CLEAR,
    GATE_UNKNOWN,
    earnings_gate,
    next_report,
)
from strategies.h7_lanes import (
    _buy_fill,
    _round_trip_commission,
    _sell_fill,
    decide_lane_a,
    decide_lane_b,
    decide_lane_c,
)

try:  # keep importable before lumibot exists (unit tests of pure helpers)
    from lumibot.strategies import Strategy  # VERIFIED import path (4.5.63)
except Exception:  # pragma: no cover
    Strategy = object

# Exit-reason priority, frozen by the owner instruction. earnings_unknown is
# the F2 conservative close (gate turned UNKNOWN while an H7c position was
# open) and shares the pre-earnings priority class.
EXIT_PRIORITY = ("pre_earnings", "earnings_unknown", "scheduled_dte",
                 "underlying_stop", "credit_stop", "profit_target")

# Warm-up before any signal may fire: the 52-week-high window plus the
# reclaim lookback plus the edge-trigger context (all three terms frozen in
# config, 7b-2R finding 5; the lane-b RV-history rule additionally
# self-blocks inside rv_percentile).
WARMUP_SESSIONS = (config.H7_DD_LOOKBACK_D + config.H7A_RECLAIM_LOOKBACK_D
                   + config.H7_WARMUP_EXTRA_SESSIONS)


def primary_exit_reason(reasons: list[str]) -> str:
    for r in EXIT_PRIORITY:
        if r in reasons:
            return r
    raise ValueError(f"unknown exit reasons: {reasons!r}")


def _default_known_as_of(iso_day: str) -> datetime:
    """Backtest causality cutoff for session T: the ACTUAL XNYS close of T
    in UTC (early closes included). An announcement published after the
    close -- e.g. an 8-K accepted 20:03 UTC -- is NOT in T's information set
    and becomes visible at T+1 (7b-2R finding 4)."""
    from data.cache_runner import session_close_utc
    return session_close_utc(iso_day)


@dataclass
class _H7Position:
    lane: str
    structure: str                # long_call | call_debit_spread | bull_put_spread
    symbol: str
    expiration: Date
    legs: dict                    # name -> (asset, entry_side)
    action: dict                  # the frozen decide_lane_* action
    signal_date: str
    entry_date: str               # execution session (T+1)
    stop_ref: float
    at_risk: float                # revalidated at-risk charged to the sleeve
    width: float | None = None
    state: str = "pending_entry"  # -> open -> pending_exit -> (finalized)
    entry_fills: dict = field(default_factory=dict)
    exit_fills: dict = field(default_factory=dict)
    entry_cost: float | None = None   # per-share: debit (long) / credit (h7c)
    queued_exit_iso: str | None = None
    exit_reasons: list = field(default_factory=list)
    exit_decision_date: str | None = None
    exit_date: str | None = None
    underlying_entry_close: float | None = None


class H7LaneBacktest(Strategy):
    """One symbol, one lane, one open position at a time. Daily EOD cadence."""

    def initialize(self):
        self.sleeptime = "1D"
        params = self.parameters or {}
        self.lane = params["lane"]                      # "a" | "b" | "c"
        self.symbol = params["symbol"]
        self._chain_provider = params["chain_provider"]
        self._closes_adj = params["closes_adj"]         # full series, str index
        self._closes_raw = params["closes_raw"]
        self._assertions = params.get("assertions", [])
        self._known_as_of_fn = params.get("known_as_of_fn", _default_known_as_of)
        self._tradeable = params.get("tradeable_assets")
        self._entry_cutoff = params.get("entry_cutoff")
        self._blocked_until = params.get("blocked_until")
        self._trading_days_fn = params.get("trading_days_fn")
        self._pos: _H7Position | None = None
        self._pending: dict | None = None               # decision awaiting T+1
        # 7b-2R finding 5: risk opened per calendar month survives year-chunk
        # seams -- the runner seeds the next chunk with this chunk's ledger
        self._month_risk: dict[str, float] = dict(
            params.get("month_risk_seed") or {})
        self.closed_trades: list[dict] = []
        self.cancelled_entries: list[dict] = []
        # 7b-2R finding 6: a data hole must never read as "no opportunity".
        # Every simulated session is recorded; every input gap emits a
        # structured record the adjudicator can audit.
        self.visited_sessions: set[str] = set()
        self.gap_records: list[dict] = []

    def _gap(self, iso: str, stage: str, reason: str) -> None:
        rec = {"symbol": self.symbol, "lane": self.lane, "session": iso,
               "stage": stage, "reason": reason}
        if rec not in self.gap_records:
            self.gap_records.append(rec)

    # ----- engine adapter (the ONLY place with the guarded method names) ----
    def _engine_submit_leg(self, asset, qty: int, side: str) -> None:
        """Offline Lumibot engine order against PandasDataBacktesting (no
        broker endpoint). Owner-authorized guard exception, 2026-07-10."""
        self.submit_order(self.create_order(asset, qty, side))

    # ----- main loop -------------------------------------------------------
    def on_trading_iteration(self):
        iso = self._today().isoformat()
        self.visited_sessions.add(iso)
        self._sync_fills()
        pos = self._pos
        if pos is not None and pos.state == "pending_exit":
            return  # exit orders live; wait for fills
        if pos is not None and pos.queued_exit_iso is not None:
            if iso >= pos.queued_exit_iso:
                self._execute_exit(iso)
            return  # an exiting position takes no other action
        if self._pending is not None:
            self._execute_pending_entry(iso)
        if self._pos is not None and self._pos.state == "open":
            self._observe_exits(iso)
        if (self._pos is None and self._pending is None
                and self._entry_allowed(iso)):
            self._compute_decision(iso)

    # ----- fill synchronization (H1 idiom) ----------------------------------
    def _sync_fills(self) -> None:
        pos = self._pos
        if pos is None:
            return
        if pos.state == "pending_entry":
            if all(a in pos.entry_fills for a, _ in pos.legs.values()):
                pos.entry_cost = self._net_entry(pos)
                pos.state = "open"
        elif pos.state == "pending_exit":
            if all(a in pos.exit_fills for a, _ in pos.legs.values()):
                self._finalize(pos)

    def on_filled_order(self, position, order, price, quantity, multiplier):
        pos = self._pos
        if pos is None:
            return
        for asset, entry_side in pos.legs.values():
            if order.asset != asset:
                continue
            side = str(order.side).lower()
            if pos.state == "pending_entry" and side == entry_side:
                pos.entry_fills[asset] = float(price)
            elif pos.state == "pending_exit" and side == _flip(entry_side):
                pos.exit_fills[asset] = float(price)
            return

    def _net_entry(self, pos: _H7Position) -> float:
        f = pos.entry_fills
        if pos.structure == "long_call":
            ((asset, _),) = pos.legs.values()
            return f[asset]
        if pos.structure == "call_debit_spread":
            return f[pos.legs["long"][0]] - f[pos.legs["short"][0]]
        # bull_put_spread: net credit received
        return f[pos.legs["short"][0]] - f[pos.legs["long"][0]]

    # ----- decision at T ----------------------------------------------------
    def _entry_allowed(self, iso: str) -> bool:
        if self._blocked_until is not None and iso <= self._blocked_until:
            return False
        if self._entry_cutoff is not None and iso > self._entry_cutoff:
            return False
        return True

    def _compute_decision(self, iso: str) -> None:
        closes = self._closes_adj.loc[:iso]
        if len(closes) < WARMUP_SESSIONS:
            return  # warm-up: disclosed structural suppression, not a gap
        if str(closes.index[-1])[:10] != iso:
            self._gap(iso, "decision", "adjusted_close_missing_for_session")
            return
        chain = self._chain_provider(self.symbol, iso)
        if chain is None:
            self._gap(iso, "decision", "chain_missing_for_session")
            return
        raw = self._closes_raw.loc[:iso]
        if raw.empty or str(raw.index[-1])[:10] != iso:
            self._gap(iso, "decision", "raw_close_missing_for_session")
            return
        spot = float(raw.iloc[-1])
        gate, _ = earnings_gate(self.symbol, Date.fromisoformat(iso),
                                self._assertions,
                                known_as_of=self._known_as_of_fn(iso))
        banned = gate != GATE_CLEAR
        nxt = self._next_session(iso)
        if nxt is None:
            return  # no future session inside the window: nothing to execute
        month_spent = self._month_risk.get(nxt[:7], 0.0)
        action = self._decide(closes, chain, spot, Date.fromisoformat(iso),
                              month_spent, banned)
        if action is not None:
            self._pending = {"action": action, "signal_date": iso,
                             "execute_iso": nxt}

    def _decide(self, closes, chain, spot, today, month_spent, banned):
        if self.lane == "a":
            return decide_lane_a(closes=closes, chain=chain, spot=spot,
                                 today=today, month_spent=month_spent,
                                 banned=banned)
        if self.lane == "b":
            return decide_lane_b(closes=closes, chain=chain, spot=spot,
                                 today=today, month_spent=month_spent,
                                 banned=banned)
        return decide_lane_c(symbol=self.symbol, closes=closes, chain=chain,
                             spot=spot, today=today, month_spent=month_spent,
                             banned=banned, open_h7c=0)

    # ----- entry at T+1 ------------------------------------------------------
    def _execute_pending_entry(self, iso: str) -> None:
        pending = self._pending
        assert pending is not None
        if iso != pending["execute_iso"]:
            # the planned execution session had no bar (data gap) -- cancel,
            # never chase into a later session (owner rule)
            self._cancel(pending, "execution_session_missing", iso)
            return
        action = pending["action"]
        chain = self._chain_provider(self.symbol, iso)
        if chain is None:
            self._cancel(pending, "no_chain_on_execution_session", iso)
            return
        gate, _ = earnings_gate(
            self.symbol, Date.fromisoformat(iso), self._assertions,
            known_as_of=self._known_as_of_fn(iso))
        if gate != GATE_CLEAR:
            self._cancel(pending, f"earnings_gate_{gate.lower()}", iso)
            return
        exp_iso = str(action["expiration"])
        dte = (Date.fromisoformat(exp_iso) - Date.fromisoformat(iso)).days
        band = (config.H7C_DTE_BAND if action["kind"] == "bull_put_spread"
                else config.H7_LONG_DTE_BAND)
        if not (band[0] <= dte <= band[1]):
            self._cancel(pending, "dte_out_of_band", iso)   # F1
            return
        legs_rows = self._leg_rows(chain, action, exp_iso)
        if legs_rows is None:
            self._cancel(pending, "leg_missing_or_invalid_quote", iso)
            return
        if not all(passes_liquidity(r.open_interest, r.bid, r.ask)
                   for r in legs_rows.values()):
            self._cancel(pending, "liquidity", iso)
            return
        budget = config.H7_MONTHLY_AT_RISK - self._month_risk.get(iso[:7], 0.0)
        econ = self._revalidate_economics(action, legs_rows, budget)
        if econ is None:
            self._cancel(pending, "economics_failed_revalidation", iso)
            return
        at_risk, width = econ
        self._submit_entry(action, exp_iso, iso, pending["signal_date"],
                           at_risk, width)
        self._pending = None

    def _leg_rows(self, chain, action: dict, exp_iso: str):
        def row(strike, right):
            rows = chain[(chain["right"] == right)
                         & (chain["expiration"] == exp_iso)
                         & (chain["strike"] == float(strike))]
            if rows.empty:
                return None
            r = rows.iloc[0]
            # finite, two-sided, uncrossed -- everywhere (7b-2R finding 5)
            return r if pandas_feed.quote_valid(r.bid, r.ask) else None

        kind = action["kind"]
        if kind == "long_call":
            r = row(action["strike"], "C")
            return None if r is None else {"long": r}
        if kind == "call_debit_spread":
            lo = row(action["long_strike"], "C")
            hi = row(action["short_strike"], "C")
            return None if lo is None or hi is None else {"long": lo, "short": hi}
        lo = row(action["long_strike"], "P")
        hi = row(action["short_strike"], "P")
        return None if lo is None or hi is None else {"long": lo, "short": hi}

    def _revalidate_economics(self, action, rows, budget):
        """Executable economics at T+1 quotes priced through the ONE
        canonical adverse transform (== the engine's exact fill prices,
        7b-2R finding 5), decide-layer formulas, vertical bounds enforced.
        Returns (at_risk_dollars, width) or None."""
        n = config.H7_DIAGNOSTIC_CONTRACTS
        kind = action["kind"]
        if kind == "long_call":
            cost = (_buy_fill(rows["long"]) * 100 + _round_trip_commission(1)) * n
            return (cost, None) if cost <= budget else None
        if kind == "call_debit_spread":
            debit = _buy_fill(rows["long"]) - _sell_fill(rows["short"])
            spread_w = (float(action["short_strike"])
                        - float(action["long_strike"]))
            if not 0 < debit <= spread_w:   # vertical bounds
                return None
            cost = (debit * 100 + _round_trip_commission(2)) * n
            return (cost, None) if cost <= budget else None
        width = float(action["short_strike"]) - float(action["long_strike"])
        credit = _sell_fill(rows["short"]) - _buy_fill(rows["long"])
        if not 0 < credit < width:          # vertical bounds
            return None
        if credit < config.H7C_CREDIT_FLOOR_FRAC * width:
            return None
        max_loss = ((width - credit) * 100 + _round_trip_commission(2)) * n
        return (max_loss, width) if max_loss <= budget else None

    def _submit_entry(self, action, exp_iso, iso, signal_date, at_risk, width):
        sym = self.symbol
        kind = action["kind"]
        if kind == "long_call":
            legs = {"long": (pandas_feed.option_asset(
                sym, exp_iso, action["strike"], right="CALL"), "buy")}
        elif kind == "call_debit_spread":
            legs = {"long": (pandas_feed.option_asset(
                        sym, exp_iso, action["long_strike"], right="CALL"),
                        "buy"),
                    "short": (pandas_feed.option_asset(
                        sym, exp_iso, action["short_strike"], right="CALL"),
                        "sell")}
        else:
            legs = {"short": (pandas_feed.option_asset(
                        sym, exp_iso, action["short_strike"], right="PUT"),
                        "sell"),
                    "long": (pandas_feed.option_asset(
                        sym, exp_iso, action["long_strike"], right="PUT"),
                        "buy")}
        if self._tradeable is not None:
            missing = [a for a, _ in legs.values() if a not in self._tradeable]
            if missing:
                # fail LOUD: a selected leg without feed Data would leave an
                # order pending forever (silent no-fill would bias results)
                raise RuntimeError(
                    f"selected leg(s) missing from the offline feed: {missing}")
        for asset, side in legs.values():
            self._engine_submit_leg(asset, config.H7_DIAGNOSTIC_CONTRACTS,
                                    side)
        adj = self._closes_adj.loc[:iso]
        self._pos = _H7Position(
            lane=self.lane, structure=kind, symbol=sym,
            expiration=Date.fromisoformat(exp_iso), legs=legs, action=action,
            signal_date=signal_date, entry_date=iso,
            stop_ref=float(action["stop_ref"]), at_risk=float(at_risk),
            width=width,
            underlying_entry_close=(float(adj.iloc[-1]) if not adj.empty
                                    else None),
        )
        self._month_risk[iso[:7]] = (
            self._month_risk.get(iso[:7], 0.0) + float(at_risk))

    def _cancel(self, pending, reason: str, iso: str) -> None:
        self.cancelled_entries.append({
            "symbol": self.symbol, "lane": self.lane,
            "signal_date": pending["signal_date"],
            "planned_execution": pending["execute_iso"],
            "cancelled_on": iso, "reason": reason,
            "kind": pending["action"]["kind"],
        })
        self._pending = None

    # ----- exit observation at S, execution at >= S+1 ------------------------
    def _observe_exits(self, iso: str) -> None:
        pos = self._pos
        assert pos is not None and pos.state == "open"
        today = Date.fromisoformat(iso)
        if today >= pos.expiration:
            raise RuntimeError(
                f"{self.symbol} {pos.structure} reached expiration "
                f"{pos.expiration} unresolved -- exit engine failed loud")
        nxt = self._next_session(iso)
        if nxt is None:
            return
        reasons: list[str] = []

        # date-known exits: queue so execution lands ON the intended session
        close_dte = (config.H7C_CLOSE_AT_DTE
                     if pos.structure == "bull_put_spread"
                     else config.H7_CLOSE_AT_DTE)
        if (pos.expiration - Date.fromisoformat(nxt)).days <= close_dte:
            reasons.append("scheduled_dte")
        if pos.structure == "bull_put_spread":
            gate, _ = earnings_gate(self.symbol, today, self._assertions,
                                    known_as_of=self._known_as_of_fn(iso))
            if gate == GATE_UNKNOWN:
                reasons.append("earnings_unknown")   # F2 conservative close
            r = next_report(self.symbol, today, self._assertions,
                            known_as_of=self._known_as_of_fn(iso))
            if r is not None:
                after_next = self._next_session(nxt)
                # exit ON the last session strictly before the report: queue
                # when the session after next is on/past the report (or the
                # next session itself already is -- late knowledge, F2 spirit)
                if (Date.fromisoformat(nxt) >= r
                        or after_next is None
                        or Date.fromisoformat(after_next) >= r):
                    reasons.append("pre_earnings")

        # EOD-observed triggers on today's conservative marks
        marks = self._conservative_marks(iso)
        if marks is None:
            # open position, unpriceable session: hold is correct, but the
            # monitoring hole must be visible (7b-2R finding 6)
            self._gap(iso, "exit_monitor", "no_valid_marks_or_chain")
        entry = pos.entry_cost
        if marks is not None and entry is not None:
            liq, buyback = marks
            if pos.structure == "long_call":
                if liq is not None and liq >= (1 + config.H7_LONG_TP_PCT) * entry:
                    reasons.append("profit_target")   # liquidation >= 2 x debit
            elif pos.structure == "call_debit_spread":
                w = (float(pos.action["short_strike"])
                     - float(pos.action["long_strike"]))
                if liq is not None and liq >= config.H7_SPREAD_TP_FRAC_MAX * w:
                    reasons.append("profit_target")
            else:
                if buyback is not None:
                    if buyback <= config.H7C_TP_FRAC * entry:
                        reasons.append("profit_target")
                    if buyback >= config.H7C_STOP_CREDIT_MULT * entry:
                        reasons.append("credit_stop")
        adj = self._closes_adj.loc[:iso]
        if (not adj.empty and str(adj.index[-1])[:10] == iso
                and float(adj.iloc[-1]) < pos.stop_ref):
            reasons.append("underlying_stop")

        if reasons:
            for r in reasons:
                if r not in pos.exit_reasons:
                    pos.exit_reasons.append(r)
            if pos.queued_exit_iso is None or nxt < pos.queued_exit_iso:
                pos.queued_exit_iso = nxt
            if pos.exit_decision_date is None:
                pos.exit_decision_date = iso

    def _conservative_marks(self, iso: str):
        """(long-structure liquidation per share, h7c buyback per share)
        priced through the canonical adverse transform; None when today's
        chain, a needed leg quote, or the combination is unusable (hold).
        7b-2R finding 5: legs must be finite/two-sided/uncrossed (a positive
        crossed book previously priced exits), and spread combinations
        outside defensible vertical bounds are INVALID marks, never P&L."""
        pos = self._pos
        assert pos is not None
        chain = self._chain_provider(self.symbol, iso)
        if chain is None:
            return None
        exp_iso = pos.expiration.isoformat()

        def row(asset):
            right = "C" if str(asset.right) == "CALL" else "P"
            rows = chain[(chain["right"] == right)
                         & (chain["expiration"] == exp_iso)
                         & (chain["strike"] == float(asset.strike))]
            if rows.empty:
                return None
            r = rows.iloc[0]
            return r if pandas_feed.quote_valid(r.bid, r.ask) else None

        if pos.structure == "long_call":
            r = row(pos.legs["long"][0])
            if r is None:
                return None
            return (pandas_feed.adverse_sell(r.bid), None)
        lo, hi = row(pos.legs["long"][0]), row(pos.legs["short"][0])
        if lo is None or hi is None:
            return None
        if pos.structure == "call_debit_spread":
            liq = (pandas_feed.adverse_sell(lo.bid)
                   - pandas_feed.adverse_buy(hi.ask))
            spread_w = (float(pos.action["short_strike"])
                        - float(pos.action["long_strike"]))
            if not 0 <= liq <= spread_w:
                return None
            return (liq, None)
        buyback = (pandas_feed.adverse_buy(hi.ask)
                   - pandas_feed.adverse_sell(lo.bid))
        width = pos.width or (float(pos.action["short_strike"])
                              - float(pos.action["long_strike"]))
        if not 0 <= buyback <= width:
            return None
        return (None, buyback)

    def _execute_exit(self, iso: str) -> None:
        pos = self._pos
        assert pos is not None
        if Date.fromisoformat(iso) >= pos.expiration:
            raise RuntimeError(
                f"{self.symbol} {pos.structure} exit unresolved by expiration "
                f"{pos.expiration} (queued {pos.queued_exit_iso}, "
                f"reasons {pos.exit_reasons}) -- failing loud")
        chain = self._chain_provider(self.symbol, iso)
        rows = (None if chain is None
                else self._leg_rows(chain, pos.action,
                                    pos.expiration.isoformat()))
        if rows is None or not self._exit_bounds_ok(pos, rows):
            return  # pending-exit retained; first valid later session retries
        for asset, entry_side in pos.legs.values():
            self._engine_submit_leg(asset, config.H7_DIAGNOSTIC_CONTRACTS,
                                    _flip(entry_side))
        pos.state = "pending_exit"
        pos.exit_date = iso

    @staticmethod
    def _exit_bounds_ok(pos: _H7Position, rows) -> bool:
        """The exit combination the engine WILL fill (canonical transform ==
        exact feed prices) must sit inside defensible vertical bounds; an
        out-of-bounds combination is an invalid mark and the exit stays
        pending (7b-2R finding 5 -- never let broken quotes inflate or
        deflate P&L)."""
        if pos.structure == "long_call":
            return True   # single leg sells at bid >= 0; no vertical bound
        width = (float(pos.action["short_strike"])
                 - float(pos.action["long_strike"]))
        if pos.structure == "call_debit_spread":
            liq = (_sell_fill(rows["long"]) - _buy_fill(rows["short"]))
            return 0 <= liq <= width
        buyback = (_buy_fill(rows["short"]) - _sell_fill(rows["long"]))
        return 0 <= buyback <= width

    def _finalize(self, pos: _H7Position) -> None:
        entry = pos.entry_cost or 0.0
        n = config.H7_DIAGNOSTIC_CONTRACTS
        if pos.structure == "long_call":
            ((asset, _),) = pos.legs.values()
            proceeds = pos.exit_fills[asset]
            pnl = ((proceeds - entry) * 100 - _round_trip_commission(1)) * n
            at_risk = (entry * 100 + _round_trip_commission(1)) * n
        elif pos.structure == "call_debit_spread":
            proceeds = (pos.exit_fills[pos.legs["long"][0]]
                        - pos.exit_fills[pos.legs["short"][0]])
            pnl = ((proceeds - entry) * 100 - _round_trip_commission(2)) * n
            at_risk = (entry * 100 + _round_trip_commission(2)) * n
        else:
            debit = (pos.exit_fills[pos.legs["short"][0]]
                     - pos.exit_fills[pos.legs["long"][0]])
            pnl = ((entry - debit) * 100 - _round_trip_commission(2)) * n
            width = pos.width or 0.0
            at_risk = ((width - entry) * 100 + _round_trip_commission(2)) * n
        adj = self._closes_adj.loc[:(pos.exit_date or "")]
        self.closed_trades.append({
            "pnl": pnl,
            "capital_at_risk": at_risk,
            "economic_max_loss": at_risk,
            "entry_date": pos.entry_date,
            "signal_date": pos.signal_date,
            "exit_date": pos.exit_date,
            "exit_decision_date": pos.exit_decision_date,
            "symbol": pos.symbol,
            "lane": pos.lane,
            "structure": pos.structure,
            "exit_reason": primary_exit_reason(pos.exit_reasons),
            "exit_reasons": list(pos.exit_reasons),
            "underlying_entry_close": pos.underlying_entry_close,
            "underlying_exit_close":
                float(adj.iloc[-1]) if not adj.empty else None,
        })
        self._pos = None

    # ----- session plumbing --------------------------------------------------
    def _today(self):
        return self.get_datetime().date()

    def _next_session(self, iso: str) -> str | None:
        """The next XNYS session after `iso` (deterministic public calendar,
        causally known in advance). Injectable for synthetic tests."""
        if self._trading_days_fn is not None:
            days = self._trading_days_fn(iso)
        else:
            from data.cache_runner import trading_days
            d = Date.fromisoformat(iso)
            days = trading_days(iso, (d + timedelta(days=10)).isoformat())
        later = [x for x in days if x > iso]
        return later[0] if later else None


def _flip(side: str) -> str:
    return "sell" if side == "buy" else "buy"

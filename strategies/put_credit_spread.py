"""
strategies/put_credit_spread.py -- Strategy A: defined-risk put credit spread.

STATUS: REAL-DATA OFFLINE PATH WIRED. Selection uses cached ThetaData
greeks/OI/NBBO chains through the injected chain provider. Lumibot remains the
backtest engine for event flow, quote-side fills, cash, positions, and fees via
the offline PandasData feed.

Execution is causal under BACKTEST_EXECUTION_CONVENTION: a completed day-D EOD
chain may create an intent, but no order is submitted until the next XNYS
session. Entry legs and maximum quantity are frozen on D; D+1's adverse close
may cancel the intent or reduce quantity under the registered cap gate.
EOD-observed exits are likewise queued for the next session. If an exit
triggers on the final available session, the position is closed descriptively
at that session's conservative executable mark and labeled as such; submitting
an asynchronous order with no later engine iteration would leave it unresolved.

Hypothesis: implied vol tends to exceed realized (the volatility risk premium),
so selling a ~30-delta put and capping the downside with a long put $W lower
should show positive expectancy IF it survives costs. The harness exists to test
that claim, not to assume it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date

import config
from data import pandas_feed
from data.thetadata_adapter import passes_liquidity
from strategies.base import (
    adverse_buy,
    adverse_sell,
    capital_at_risk_per_spread,
    economic_max_loss_per_spread,
    entry_credit_conservative,
    round_trip_commission_per_spread,
    size_defined_risk,
)

# Keep the file importable before lumibot is installed.
try:
    from lumibot.strategies import Strategy  # VERIFY import path
except Exception:                            # pragma: no cover
    Strategy = object


@dataclass(frozen=True)
class SpreadSelection:
    """Decision-compatible entry candidate or the exact fail-closed reason."""

    accepted: bool
    reason: str
    expiration: str | None = None
    short_put: object | None = None
    long_put: object | None = None
    credit: float | None = None
    contracts: int = 0
    economic_max_loss: float | None = None


def select_put_credit_spread_candidate(
    chain,
    today: Date,
    *,
    width: float,
    delta: float,
    dte_band: tuple[int, int],
    haircut: float = config.SLIPPAGE_HAIRCUT,
) -> SpreadSelection:
    """Pure entry selection shared by the strategy and measured feasibility.

    This intentionally mirrors the pre-existing entry logic: nearest expiry in
    band, nearest absolute put delta, exact-width lower long leg, both-leg
    liquidity, conservative credit, then economic-risk sizing.
    """
    lo, hi = dte_band
    puts = chain[chain["right"] == "P"]
    dtes = {
        e: (Date.fromisoformat(str(e)) - today).days
        for e in puts["expiration"].unique()
    }
    in_band = {e: d for e, d in dtes.items() if max(lo, config.DTE_MIN) <= d <= hi}
    if not in_band:
        return SpreadSelection(False, "no_expiration")

    expiration = min(in_band, key=lambda e: in_band[e])
    expiry_puts = puts[puts["expiration"] == expiration]
    if expiry_puts.empty:
        return SpreadSelection(False, "short_delta_missing", expiration=str(expiration))

    short_put = expiry_puts.loc[(expiry_puts["delta"].abs() - delta).abs().idxmin()]
    long_rows = expiry_puts[expiry_puts["strike"] == short_put.strike - width]
    if long_rows.empty:
        return SpreadSelection(
            False,
            "long_strike_missing",
            expiration=str(expiration),
            short_put=short_put,
        )
    long_put = long_rows.iloc[0]

    if not (
        passes_liquidity(short_put.open_interest, short_put.bid, short_put.ask)
        and passes_liquidity(long_put.open_interest, long_put.bid, long_put.ask)
    ):
        return SpreadSelection(
            False,
            "liquidity",
            expiration=str(expiration),
            short_put=short_put,
            long_put=long_put,
        )

    credit = entry_credit_conservative(
        short_put.bid, short_put.ask, long_put.bid, long_put.ask, haircut
    )
    if credit <= 0:
        return SpreadSelection(
            False,
            "non_positive_credit",
            expiration=str(expiration),
            short_put=short_put,
            long_put=long_put,
            credit=credit,
        )

    contracts, economic_max_loss = size_defined_risk(width, credit)
    if contracts < 1:
        return SpreadSelection(
            False,
            "risk_budget_too_small",
            expiration=str(expiration),
            short_put=short_put,
            long_put=long_put,
            credit=credit,
            economic_max_loss=economic_max_loss,
        )

    return SpreadSelection(
        True,
        "accepted",
        expiration=str(expiration),
        short_put=short_put,
        long_put=long_put,
        credit=credit,
        contracts=contracts,
        economic_max_loss=economic_max_loss,
    )


class PutCreditSpread(Strategy):
    """One open spread per underlying at a time. EOD (daily) decision cadence."""

    def initialize(self):
        self.sleeptime = "1D"                     # daily EOD cadence (spike-verified)
        params = self.parameters or {}
        self.symbols = params.get("symbols", config.UNIVERSE)
        self.delta = config.A_SHORT_PUT_DELTA
        self.width = config.A_SPREAD_WIDTH
        self.dte_band = config.A_TARGET_DTE
        self.profit_target = config.A_PROFIT_TARGET
        self.stop_mult = config.A_STOP_LOSS
        self.close_dte = config.A_CLOSE_AT_DTE
        self.haircut = config.SLIPPAGE_HAIRCUT
        # harness plumbing (data path + chunk gating), never selection math:
        self._chain_provider = params.get("chain_provider")
        self._tradeable = params.get("tradeable_assets")
        self._tradeable_by_session = params.get("tradeable_assets_by_session")
        self._trading_sessions = tuple(params.get("trading_sessions", ()))
        self._entry_cutoff = params.get("entry_cutoff")
        self._blocked_until = params.get("blocked_until")
        if config.BACKTEST_EXECUTION_CONVENTION != "D_PLUS_1_CLOSE":
            raise RuntimeError(
                "unsupported BACKTEST_EXECUTION_CONVENTION: "
                f"{config.BACKTEST_EXECUTION_CONVENTION!r}"
            )
        if config.BACKTEST_ENTRY_DATE_SEMANTICS != "FILL_SESSION":
            raise RuntimeError(
                "unsupported BACKTEST_ENTRY_DATE_SEMANTICS: "
                f"{config.BACKTEST_ENTRY_DATE_SEMANTICS!r}"
            )
        if (
            config.BACKTEST_TERMINAL_EXIT_CONVENTION
            != "terminal_conservative_mark"
        ):
            raise RuntimeError(
                "unsupported BACKTEST_TERMINAL_EXIT_CONVENTION: "
                f"{config.BACKTEST_TERMINAL_EXIT_CONVENTION!r}"
            )
        if not self._trading_sessions:
            raise RuntimeError("harness must inject deterministic XNYS trading_sessions")
        if self._tradeable_by_session is None:
            raise RuntimeError(
                "harness must inject point-in-time tradeable_assets_by_session"
            )
        self._pending_entries: dict[str, _PendingEntry] = {}
        self._spreads = {}
        self.closed_trades = []
        self.cancelled_entries = []
        self.atomicity_incidents = []

    # ----- main loop -----------------------------------------------------
    def on_trading_iteration(self):
        for symbol in self.symbols:
            if self._has_open_position(symbol):
                pos = self._position(symbol)
                if pos.state == "queued_exit":
                    self._execute_pending_exit(symbol, pos)
                elif self._ready_to_manage(symbol):   # fills confirmed?
                    self._manage_exit(symbol)
            elif symbol in self._pending_entries:
                self._execute_pending_entry(symbol)
            elif self._entry_allowed():               # chunk gating only
                self._try_enter(symbol)

    # ----- ENTRY ---------------------------------------------------------
    def _try_enter(self, symbol):
        chain = self._get_eod_chain(symbol)
        if chain is None:
            self.log_message(f"{symbol}: no chain available, skip"); return

        selection = select_put_credit_spread_candidate(
            chain,
            self._today(),
            width=self.width,
            delta=self.delta,
            dte_band=self.dte_band,
            haircut=self.haircut,
        )
        if selection.reason == "no_expiration":
            self.log_message(
                f"{symbol}: no expiration in {self.dte_band} DTE band, skip"); return
        if selection.reason in {"short_delta_missing", "long_strike_missing"}:
            self.log_message(f"{symbol}: legs unavailable, skip"); return
        if selection.reason == "liquidity":
            self.log_message(f"{symbol}: failed liquidity filter, skip"); return
        if selection.reason == "non_positive_credit":
            self.log_message(f"{symbol}: non-positive credit, skip"); return
        if selection.reason == "risk_budget_too_small":
            self.log_message(
                f"{symbol}: risk budget too small for ${self.width} width "
                f"(economic max loss ${selection.economic_max_loss:.0f} > budget). "
                "Skip -- NOT rounding up.")
            return
        if not selection.accepted:
            raise RuntimeError(f"unexpected spread selection state: {selection!r}")

        expiry = selection.expiration
        short_put = selection.short_put
        long_put = selection.long_put
        contracts = selection.contracts
        credit = selection.credit
        economic_max_loss = selection.economic_max_loss
        assert expiry is not None
        assert short_put is not None
        assert long_put is not None
        assert credit is not None
        assert economic_max_loss is not None

        decision_date = self._today().isoformat()
        execution_date = self._next_session(decision_date)
        if execution_date is None:
            self.log_message(f"{symbol}: no next session for entry, skip")
            return
        self._pending_entries[symbol] = _PendingEntry(
            symbol=symbol,
            expiration=expiry,
            short_strike=float(getattr(short_put, "strike")),
            long_strike=float(getattr(long_put, "strike")),
            contracts=contracts,
            signal_credit=float(credit),
            decision_date=decision_date,
            execution_date=execution_date,
        )
        self.log_message(
            f"{symbol}: queued {contracts}x ${self.width}-wide put spread "
            f"from {decision_date} for {execution_date}; signal credit "
            f"${credit:.2f}, economic max loss ${economic_max_loss:.0f}/contract")

    def _execute_pending_entry(self, symbol):
        pending = self._pending_entries[symbol]
        today = self._today().isoformat()
        if today < pending.execution_date:
            return
        if today != pending.execution_date:
            self._cancel_pending_entry(symbol, "execution_session_missing")
            return

        dte = (
            Date.fromisoformat(pending.expiration) - Date.fromisoformat(today)
        ).days
        lo, hi = self.dte_band
        if not max(lo, config.DTE_MIN) <= dte <= hi:
            self._cancel_pending_entry(symbol, "execution_dte_out_of_band")
            return

        assets = self._spread_assets(
            symbol,
            pending.expiration,
            pending.short_strike,
            pending.long_strike,
        )
        if not self._assets_available(today, assets):
            raise RuntimeError(
                f"{symbol}: frozen entry leg(s) missing from the offline feed "
                f"on execution session {today}: {list(assets)}"
            )

        # This models a day-D standing net-credit limit: the D+1 close decides
        # only whether the already-frozen intent could fill, never what to buy.
        # If it remains inside the owner-typed tolerance, reduce quantity only
        # as needed to keep realized economic max loss <= the hard dollar cap.
        execution_credit = self._frozen_entry_credit(symbol, pending)
        if execution_credit is None:
            raise RuntimeError(
                f"{symbol}: frozen entry quotes missing on execution session {today}"
            )
        execution_credit = round(execution_credit, 2)
        minimum_credit = round(
            pending.signal_credit - config.A_ENTRY_CREDIT_TOLERANCE,
            2,
        )
        if execution_credit < minimum_credit:
            self._cancel_pending_entry(symbol, "fill_credit_below_tolerance")
            return
        fill_contracts, _ = size_defined_risk(self.width, execution_credit)
        contracts = min(pending.contracts, fill_contracts)
        if contracts <= 0:
            self._cancel_pending_entry(symbol, "fill_risk_budget_too_small")
            return
        if contracts < pending.contracts:
            self.log_message(
                f"{symbol}: resized {pending.contracts}x to {contracts}x on "
                f"{today} to preserve the hard dollar cap"
            )

        self._submit_spread(
            symbol,
            pending.expiration,
            pending.short_strike,
            pending.long_strike,
            contracts,
            pending.signal_credit,
            decision_date=pending.decision_date,
            fill_date=today,
        )
        del self._pending_entries[symbol]

    def _cancel_pending_entry(self, symbol, reason):
        pending = self._pending_entries.pop(symbol)
        self.cancelled_entries.append(
            {
                "symbol": symbol,
                "decision_date": pending.decision_date,
                "cancellation_date": self._today().isoformat(),
                "reason": reason,
                "signal_credit": pending.signal_credit,
            }
        )
        self.log_message(
            f"{symbol}: cancelled {pending.decision_date} entry intent on "
            f"{self._today().isoformat()}: {reason}"
        )

    # ----- EXIT ----------------------------------------------------------
    def _manage_exit(self, symbol):
        pos = self._position(symbol)
        entry_credit = pos.entry_credit
        current = self._spread_mark(symbol, pos)                  # conservative mark
        if current is None:
            return  # no chain / leg row today -- hold and re-mark tomorrow
        captured = (entry_credit - current) / entry_credit if entry_credit else 0.0
        dte = self._dte(pos)

        if captured >= self.profit_target:
            self._close(symbol, pos, reason="profit_target")
        elif (current - entry_credit) >= self.stop_mult * entry_credit:
            # NOTE: 2x credit can exceed max loss; if so, max loss governs and
            # the stop never binds. Record the REALIZED exit, not the threshold.
            self._close(symbol, pos, reason="stop_loss")
        elif dte <= self.close_dte:
            self._close(symbol, pos, reason="close_at_dte")

    # ----- Lumibot adapters (verified against installed 4.5.63 + spike) ---
    # Data path: chains come from the injected chain_provider (the offline
    # parquet cache with REAL exchange greeks/OI), never from Lumibot's
    # locally computed model greeks. Orders fill against data/pandas_feed.py
    # Data objects: market sell @ pre-widened bid, buy @ pre-widened ask, so
    # engine fills can never be better than the frozen conservative model.

    def _today(self):
        return self.get_datetime().date()

    def _entry_allowed(self):
        """Chunk gating (harness plumbing): blocked_until is EXCLUSIVE (a
        carried-over position's exit day), entry_cutoff INCLUSIVE (last day
        whose exits still fit inside the data window)."""
        today = self._today().isoformat()
        if self._blocked_until is not None and today <= self._blocked_until:
            return False
        if self._entry_cutoff is not None and today > self._entry_cutoff:
            return False
        return True

    def _get_eod_chain(self, symbol):
        if self._chain_provider is None:
            raise RuntimeError(
                "no chain_provider wired -- the harness must inject the "
                "offline cache reader (parameters['chain_provider'])")
        return self._chain_provider(symbol, self._today().isoformat())

    def _next_session(self, iso):
        later = [session for session in self._trading_sessions if session > iso]
        return later[0] if later else None

    def _pick_expiration(self, chain, band):
        today = self._today()
        lo, hi = band
        puts = chain[chain["right"] == "P"]
        dtes = {
            e: (Date.fromisoformat(str(e)) - today).days
            for e in puts["expiration"].unique()
        }
        in_band = {e: d for e, d in dtes.items()
                   if max(lo, config.DTE_MIN) <= d <= hi}
        if not in_band:
            return None
        return min(in_band, key=lambda e: in_band[e])   # nearest in band

    def _strike_nearest_delta(self, chain, exp, d):
        puts = chain[(chain["right"] == "P") & (chain["expiration"] == exp)]
        if puts.empty:
            return None
        return puts.loc[(puts["delta"].abs() - d).abs().idxmin()]

    def _strike_below(self, chain, exp, ref, width):
        puts = chain[(chain["right"] == "P") & (chain["expiration"] == exp)]
        rows = puts[puts["strike"] == ref.strike - width]
        return None if rows.empty else rows.iloc[0]

    def _liquid(self, leg):
        return passes_liquidity(leg.open_interest, leg.bid, leg.ask)

    def _spread_assets(self, symbol, expiry, short_strike, long_strike):
        return (
            pandas_feed.option_asset(symbol, str(expiry), short_strike),
            pandas_feed.option_asset(symbol, str(expiry), long_strike),
        )

    def _assets_available(self, iso, assets):
        globally_available = self._tradeable if self._tradeable is not None else set()
        if self._tradeable_by_session is None:
            return False
        session_available = self._tradeable_by_session.get(iso, set())
        return all(
            asset in globally_available and asset in session_available
            for asset in assets
        )

    def _frozen_entry_credit(self, symbol, pending):
        """D+1 executable credit for the exact day-D frozen legs."""
        chain = self._get_eod_chain(symbol)
        if chain is None:
            return None

        def leg_row(strike):
            rows = chain[
                (chain["right"] == "P")
                & (chain["expiration"] == pending.expiration)
                & (chain["strike"] == strike)
            ]
            return None if rows.empty else rows.iloc[0]

        short_row = leg_row(pending.short_strike)
        long_row = leg_row(pending.long_strike)
        if short_row is None or long_row is None:
            return None
        return entry_credit_conservative(
            short_row.bid,
            short_row.ask,
            long_row.bid,
            long_row.ask,
            self.haircut,
        )

    def _same_session_entry_unwind_prices(
        self,
        symbol,
        expiry,
        short_strike,
        long_strike,
        assets,
    ):
        """Conservative same-session prices for neutralizing either entry leg."""
        chain = self._get_eod_chain(symbol)
        if chain is None:
            return None

        def leg_row(strike):
            rows = chain[
                (chain["right"] == "P")
                & (chain["expiration"] == str(expiry))
                & (chain["strike"] == strike)
            ]
            return None if rows.empty else rows.iloc[0]

        short_row = leg_row(short_strike)
        long_row = leg_row(long_strike)
        if short_row is None or long_row is None:
            return None
        short_asset, long_asset = assets
        return {
            short_asset: adverse_buy(short_row.ask, self.haircut),
            long_asset: adverse_sell(long_row.bid, self.haircut),
        }

    def _submit_spread(
        self,
        symbol,
        expiry,
        short_strike,
        long_strike,
        contracts,
        credit,
        *,
        decision_date,
        fill_date,
    ):
        short_asset, long_asset = self._spread_assets(
            symbol, expiry, short_strike, long_strike
        )
        if not self._assets_available(fill_date, (short_asset, long_asset)):
            # fail LOUD: a selected leg without same-session feed Data would
            # leave a GTC market order pending and silently chase a later quote.
            raise RuntimeError(
                "selected leg(s) missing from the offline feed on "
                f"{fill_date}: {[short_asset, long_asset]}"
            )
        assets = (short_asset, long_asset)
        unwind_prices = self._same_session_entry_unwind_prices(
            symbol,
            expiry,
            short_strike,
            long_strike,
            assets,
        )
        if unwind_prices is None:
            raise RuntimeError(
                "selected leg(s) lack exact same-session unwind quotes on "
                f"{fill_date}: {[short_asset, long_asset]}"
            )

        short_order = self.create_order(short_asset, contracts, "sell")
        long_order = self.create_order(long_asset, contracts, "buy")
        pos = _OpenSpread(
            symbol=symbol,
            expiration=Date.fromisoformat(str(expiry)),
            short_asset=short_asset,
            long_asset=long_asset,
            contracts=contracts,
            model_credit=float(credit),
            entry_decision_date=decision_date,
            entry_fill_date=fill_date,
            entry_unwind_prices=unwind_prices,
        )
        # Register state before either separate order is submitted so fill and
        # cancellation callbacks can always enforce the atomicity invariant.
        self._spreads[symbol] = pos
        try:
            self.submit_order(short_order)
            self.submit_order(long_order)
        except Exception:
            if symbol in self._spreads and not pos.entry_fills:
                del self._spreads[symbol]
            raise

    def _has_open_position(self, symbol):
        return symbol in self._spreads

    def _position(self, symbol):
        return self._spreads[symbol]

    def _ready_to_manage(self, symbol):
        """Fill-state sync (plumbing): only a spread whose ENTRY fills are
        confirmed is managed; a spread whose EXIT fills are confirmed is
        finalized into closed_trades."""
        pos = self._spreads[symbol]
        if pos.state == "pending_entry":
            if pos.entry_cancelled_assets and len(pos.entry_fills) == 1:
                self._fail_partial_entry_with_conservative_unwind(symbol, pos)
            if pos.short_asset in pos.entry_fills and pos.long_asset in pos.entry_fills:
                pos.entry_credit = (
                    pos.entry_fills[pos.short_asset] - pos.entry_fills[pos.long_asset])
                pos.state = "open"
                return True
            return False
        if pos.state == "pending_exit":
            if pos.short_asset in pos.exit_fills and pos.long_asset in pos.exit_fills:
                self._finalize_trade(symbol, pos)
            return False
        return pos.state == "open"

    def _spread_exit_fills(self, symbol, pos):
        """Return conservative short-buy and long-sell prices for today."""
        chain = self._get_eod_chain(symbol)
        if chain is None:
            return None
        exp = pos.expiration.isoformat()

        def leg_row(asset):
            rows = chain[(chain["right"] == "P")
                         & (chain["expiration"] == exp)
                         & (chain["strike"] == asset.strike)]
            return None if rows.empty else rows.iloc[0]

        srow, lrow = leg_row(pos.short_asset), leg_row(pos.long_asset)
        if srow is None or lrow is None:
            return None
        return (
            adverse_buy(srow.ask, self.haircut),
            adverse_sell(lrow.bid, self.haircut),
        )

    def _spread_mark(self, symbol, pos):
        """Conservative cost-to-close, or None without both leg quotes."""
        fills = self._spread_exit_fills(symbol, pos)
        return None if fills is None else fills[0] - fills[1]

    def _dte(self, pos):
        return (pos.expiration - self._today()).days

    def _close(self, symbol, pos, reason):
        decision_date = self._today().isoformat()
        execution_date = self._next_session(decision_date)
        if execution_date is None:
            terminal_fills = self._spread_exit_fills(symbol, pos)
            if terminal_fills is None:
                self.log_message(
                    f"{symbol}: no next session or terminal mark for {reason} exit"
                )
                return
            pos.exit_reason = reason
            pos.exit_decision_date = decision_date
            pos.exit_fill_date = decision_date
            pos.exit_execution = config.BACKTEST_TERMINAL_EXIT_CONVENTION
            pos.exit_fills = {
                pos.short_asset: terminal_fills[0],
                pos.long_asset: terminal_fills[1],
            }
            self._finalize_trade(symbol, pos)
            return
        pos.state = "queued_exit"
        pos.exit_reason = reason
        pos.exit_decision_date = decision_date
        pos.exit_fill_date = execution_date
        pos.exit_execution = "next_session_engine_fill"

    def _execute_pending_exit(self, symbol, pos):
        today = self._today().isoformat()
        if pos.exit_fill_date is None or today < pos.exit_fill_date:
            return
        assets = (pos.short_asset, pos.long_asset)
        if not self._assets_available(today, assets):
            next_session = self._next_session(today)
            if next_session is None:
                self.log_message(
                    f"{symbol}: exit feed unavailable on {today}; no later session"
                )
                return
            pos.exit_fill_date = next_session
            self.log_message(
                f"{symbol}: exit feed unavailable on {today}; retry {next_session}"
            )
            return
        pos.exit_fill_date = today
        self.submit_order(self.create_order(pos.short_asset, pos.contracts, "buy"))
        self.submit_order(self.create_order(pos.long_asset, pos.contracts, "sell"))
        pos.state = "pending_exit"

    # ----- fills -> closed-trade extraction --------------------------------
    def on_filled_order(self, position, order, price, quantity, multiplier):
        for symbol, pos in list(self._spreads.items()):
            if order.asset == pos.short_asset or order.asset == pos.long_asset:
                side = str(order.side).lower()
                if pos.state == "pending_entry":
                    expected = "sell" if order.asset == pos.short_asset else "buy"
                    if side == expected:
                        pos.entry_fills[order.asset] = float(price)
                        pos.entry_fill_quantities[order.asset] = int(quantity)
                        if pos.entry_cancelled_assets and len(pos.entry_fills) == 1:
                            self._fail_partial_entry_with_conservative_unwind(
                                symbol,
                                pos,
                            )
                elif pos.state == "pending_exit":
                    expected = "buy" if order.asset == pos.short_asset else "sell"
                    if side == expected:
                        pos.exit_fills[order.asset] = float(price)
                return

    def on_partially_filled_order(
        self,
        position,
        order,
        price,
        quantity,
        multiplier,
    ):
        for symbol, pos in list(self._spreads.items()):
            if pos.state != "pending_entry":
                continue
            if order.asset != pos.short_asset and order.asset != pos.long_asset:
                continue
            side = str(order.side).lower()
            expected = "sell" if order.asset == pos.short_asset else "buy"
            if side != expected:
                return
            pos.entry_fills[order.asset] = float(price)
            pos.entry_fill_quantities[order.asset] = int(quantity)
            self._fail_partial_entry_with_conservative_unwind(symbol, pos)

    def on_canceled_order(self, order):
        for symbol, pos in list(self._spreads.items()):
            if pos.state != "pending_entry":
                continue
            if order.asset != pos.short_asset and order.asset != pos.long_asset:
                continue
            side = str(order.side).lower()
            expected = "sell" if order.asset == pos.short_asset else "buy"
            if side != expected:
                return
            pos.entry_cancelled_assets.add(order.asset)
            if len(pos.entry_fills) == 1:
                self._fail_partial_entry_with_conservative_unwind(symbol, pos)
            if not pos.entry_fills and pos.entry_cancelled_assets == {
                pos.short_asset,
                pos.long_asset,
            }:
                self.cancelled_entries.append(
                    {
                        "symbol": symbol,
                        "decision_date": pos.entry_decision_date,
                        "cancellation_date": self._today().isoformat(),
                        "reason": "entry_orders_unfilled",
                        "signal_credit": pos.model_credit,
                    }
                )
                del self._spreads[symbol]
            return

    def _fail_partial_entry_with_conservative_unwind(self, symbol, pos):
        if len(pos.entry_fills) != 1:
            raise RuntimeError(
                f"{symbol}: partial entry invariant requires exactly one filled leg"
            )
        filled_asset, entry_price = next(iter(pos.entry_fills.items()))
        quantity = pos.entry_fill_quantities.get(filled_asset, pos.contracts)
        unwind_price = pos.entry_unwind_prices[filled_asset]
        if filled_asset == pos.short_asset:
            filled_leg = "short"
            unwind_side = "buy"
            gross_pnl = (entry_price - unwind_price) * 100.0 * quantity
        else:
            filled_leg = "long"
            unwind_side = "sell"
            gross_pnl = (unwind_price - entry_price) * 100.0 * quantity
        commissions = 2.0 * config.COMMISSION_PER_CONTRACT * quantity
        incident = {
            "symbol": symbol,
            "session": pos.entry_fill_date,
            "filled_leg": filled_leg,
            "unwind_side": unwind_side,
            "quantity": quantity,
            "entry_price": entry_price,
            "unwind_price": unwind_price,
            "gross_pnl": gross_pnl,
            "commissions": commissions,
            "net_pnl": gross_pnl - commissions,
            "execution": "same_session_conservative_mark",
        }
        self.atomicity_incidents.append(incident)
        del self._spreads[symbol]
        message = (
            f"{symbol}: partial entry fill on {pos.entry_fill_date}; "
            f"conservatively unwound {quantity}x {filled_leg} leg at "
            f"{unwind_price:.2f}; commissions ${commissions:.2f}; "
            f"incident net P&L ${incident['net_pnl']:.2f}; run aborted"
        )
        self.log_message(message)
        raise RuntimeError(message)

    def _finalize_trade(self, symbol, pos):
        """Emit a scored trade from labeled exit fills and release the symbol."""
        exit_debit = (pos.exit_fills[pos.short_asset]
                      - pos.exit_fills[pos.long_asset])
        n = pos.contracts
        width = pos.short_asset.strike - pos.long_asset.strike
        pnl = ((pos.entry_credit - exit_debit) * 100.0 * n
               - round_trip_commission_per_spread() * n)
        self.closed_trades.append({
            "pnl": pnl,
            "capital_at_risk": capital_at_risk_per_spread(width, pos.entry_credit) * n,
            "entry_date": pos.entry_fill_date,
            "entry_decision_date": pos.entry_decision_date,
            "symbol": symbol,
            "economic_max_loss":
                economic_max_loss_per_spread(width, pos.entry_credit) * n,
            "exit_reason": pos.exit_reason,
            "exit_decision_date": pos.exit_decision_date,
            "exit_date": pos.exit_fill_date,
            "exit_execution": pos.exit_execution,
        })
        del self._spreads[symbol]


@dataclass(frozen=True)
class _PendingEntry:
    symbol: str
    expiration: str
    short_strike: float
    long_strike: float
    contracts: int
    signal_credit: float
    decision_date: str
    execution_date: str


@dataclass
class _OpenSpread:
    """Per-underlying open-spread state (one spread per symbol at a time)."""
    symbol: str
    expiration: Date
    short_asset: object
    long_asset: object
    contracts: int
    model_credit: float
    entry_decision_date: str
    entry_fill_date: str
    state: str = "pending_entry"
    entry_credit: float | None = None
    entry_fills: dict = field(default_factory=dict)
    entry_fill_quantities: dict = field(default_factory=dict)
    entry_cancelled_assets: set = field(default_factory=set)
    entry_unwind_prices: dict = field(default_factory=dict)
    exit_fills: dict = field(default_factory=dict)
    exit_reason: str | None = None
    exit_decision_date: str | None = None
    exit_fill_date: str | None = None
    exit_execution: str | None = None

"""
strategies/put_credit_spread.py -- Strategy A: defined-risk put credit spread.

STATUS: PHASE 0. The LOGIC (selection, sizing, exits) is config-driven and
expressed faithfully. Every method marked VERIFY wraps a Lumibot/ThetaData call
that you must confirm against the INSTALLED library before trusting a backtest.
Do not assume this is tested end-to-end.

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
        self._entry_cutoff = params.get("entry_cutoff")
        self._blocked_until = params.get("blocked_until")
        self._spreads = {}
        self.closed_trades = []

    # ----- main loop -----------------------------------------------------
    def on_trading_iteration(self):
        for symbol in self.symbols:
            if self._has_open_position(symbol):
                if self._ready_to_manage(symbol):     # fills confirmed?
                    self._manage_exit(symbol)
            elif self._entry_allowed():               # chunk gating only
                self._try_enter(symbol)

    # ----- ENTRY ---------------------------------------------------------
    def _try_enter(self, symbol):
        chain = self._get_eod_chain(symbol)                       # VERIFY
        if chain is None:
            self.log_message(f"{symbol}: no chain available, skip"); return

        expiry = self._pick_expiration(chain, self.dte_band)
        if expiry is None:
            self.log_message(
                f"{symbol}: no expiration in {self.dte_band} DTE band, skip"); return

        short_put = self._strike_nearest_delta(chain, expiry, self.delta)   # VERIFY
        long_put = self._strike_below(chain, expiry, short_put, self.width)  # VERIFY
        if short_put is None or long_put is None:
            self.log_message(f"{symbol}: legs unavailable, skip"); return

        if not (self._liquid(short_put) and self._liquid(long_put)):
            self.log_message(f"{symbol}: failed liquidity filter, skip"); return

        credit = entry_credit_conservative(
            short_put.bid, short_put.ask, long_put.bid, long_put.ask, self.haircut)
        if credit <= 0:
            self.log_message(f"{symbol}: non-positive credit, skip"); return

        contracts, economic_max_loss = size_defined_risk(self.width, credit)
        if contracts < 1:
            self.log_message(
                f"{symbol}: risk budget too small for ${self.width} width "
                f"(economic max loss ${economic_max_loss:.0f} > budget). "
                "Skip -- NOT rounding up.")
            return

        self._submit_spread(symbol, expiry, short_put, long_put, contracts, credit)  # VERIFY
        self.log_message(
            f"{symbol}: SOLD {contracts}x ${self.width}-wide put spread, "
            f"credit ${credit:.2f}, economic max loss "
            f"${economic_max_loss:.0f}/contract")

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

    def _submit_spread(self, symbol, expiry, short, long, contracts, credit):
        short_asset = pandas_feed.option_asset(symbol, str(expiry), short.strike)
        long_asset = pandas_feed.option_asset(symbol, str(expiry), long.strike)
        if self._tradeable is not None:
            missing = [a for a in (short_asset, long_asset)
                       if a not in self._tradeable]
            if missing:
                # fail LOUD: a selected leg without feed Data would leave an
                # order pending forever -- a silent no-fill would bias results
                raise RuntimeError(
                    f"selected leg(s) missing from the offline feed: {missing}")
        self.submit_order(self.create_order(short_asset, contracts, "sell"))
        self.submit_order(self.create_order(long_asset, contracts, "buy"))
        self._spreads[symbol] = _OpenSpread(
            symbol=symbol,
            expiration=Date.fromisoformat(str(expiry)),
            short_asset=short_asset,
            long_asset=long_asset,
            contracts=contracts,
            model_credit=float(credit),
            entry_decision_date=self._today().isoformat(),
        )

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

    def _spread_mark(self, symbol, pos):
        """Conservative cost-to-close: buy the short leg back at ask*(1+h),
        sell the long leg at bid*(1-h). None when today's chain or a leg row
        is missing (caller holds)."""
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
        return (float(srow.ask) * (1 + self.haircut)
                - float(lrow.bid) * (1 - self.haircut))

    def _dte(self, pos):
        return (pos.expiration - self._today()).days

    def _close(self, symbol, pos, reason):
        self.submit_order(self.create_order(pos.short_asset, pos.contracts, "buy"))
        self.submit_order(self.create_order(pos.long_asset, pos.contracts, "sell"))
        pos.state = "pending_exit"
        pos.exit_reason = reason
        pos.exit_decision_date = self._today().isoformat()

    # ----- fills -> closed-trade extraction --------------------------------
    def on_filled_order(self, position, order, price, quantity, multiplier):
        for pos in self._spreads.values():
            if order.asset == pos.short_asset or order.asset == pos.long_asset:
                side = str(order.side).lower()
                if pos.state == "pending_entry":
                    expected = "sell" if order.asset == pos.short_asset else "buy"
                    if side == expected:
                        pos.entry_fills[order.asset] = float(price)
                elif pos.state == "pending_exit":
                    expected = "buy" if order.asset == pos.short_asset else "sell"
                    if side == expected:
                        pos.exit_fills[order.asset] = float(price)
                return

    def _finalize_trade(self, symbol, pos):
        """Emit the metrics.scoreboard trade dict from ENGINE fills (net of
        the frozen commission model) and release the symbol."""
        exit_debit = (pos.exit_fills[pos.short_asset]
                      - pos.exit_fills[pos.long_asset])
        n = pos.contracts
        width = pos.short_asset.strike - pos.long_asset.strike
        pnl = ((pos.entry_credit - exit_debit) * 100.0 * n
               - round_trip_commission_per_spread() * n)
        self.closed_trades.append({
            "pnl": pnl,
            "capital_at_risk": capital_at_risk_per_spread(width, pos.entry_credit) * n,
            "entry_date": pos.entry_decision_date,
            "symbol": symbol,
            "economic_max_loss":
                economic_max_loss_per_spread(width, pos.entry_credit) * n,
            "exit_reason": pos.exit_reason,
            "exit_date": pos.exit_decision_date,
        })
        del self._spreads[symbol]


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
    state: str = "pending_entry"
    entry_credit: float | None = None
    entry_fills: dict = field(default_factory=dict)
    exit_fills: dict = field(default_factory=dict)
    exit_reason: str | None = None
    exit_decision_date: str | None = None

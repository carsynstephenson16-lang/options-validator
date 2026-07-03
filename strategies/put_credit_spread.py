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

import config
from strategies.base import entry_credit_conservative, size_defined_risk

# Keep the file importable before lumibot is installed.
try:
    from lumibot.strategies import Strategy  # VERIFY import path
except Exception:                            # pragma: no cover
    Strategy = object


class PutCreditSpread(Strategy):
    """One open spread per underlying at a time. EOD (daily) decision cadence."""

    def initialize(self):
        self.sleeptime = "1D"                     # VERIFY: daily EOD cadence
        self.symbols = config.UNIVERSE
        self.delta = config.A_SHORT_PUT_DELTA
        self.width = config.A_SPREAD_WIDTH
        self.dte_band = config.A_TARGET_DTE
        self.profit_target = config.A_PROFIT_TARGET
        self.stop_mult = config.A_STOP_LOSS
        self.close_dte = config.A_CLOSE_AT_DTE
        self.haircut = config.SLIPPAGE_HAIRCUT

    # ----- main loop -----------------------------------------------------
    def on_trading_iteration(self):
        for symbol in self.symbols:
            if self._has_open_position(symbol):
                self._manage_exit(symbol)
            else:
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
        current = self._spread_mark(symbol, pos)                  # VERIFY: conservative mark
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

    # ----- Lumibot adapters: PHASE 0, verify EVERY one -------------------
    def _get_eod_chain(self, symbol):                 raise NotImplementedError("Phase 0: Lumibot chain access")
    def _pick_expiration(self, chain, band):          raise NotImplementedError
    def _strike_nearest_delta(self, chain, exp, d):   raise NotImplementedError
    def _strike_below(self, chain, exp, ref, width):  raise NotImplementedError
    def _liquid(self, leg):                           raise NotImplementedError
    def _submit_spread(self, *a):                     raise NotImplementedError
    def _has_open_position(self, symbol):             raise NotImplementedError
    def _position(self, symbol):                      raise NotImplementedError
    def _spread_mark(self, symbol, pos):              raise NotImplementedError
    def _dte(self, pos):                              raise NotImplementedError
    def _close(self, symbol, pos, reason):            raise NotImplementedError

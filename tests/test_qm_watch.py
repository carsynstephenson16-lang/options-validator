"""QM daily watch tests -- spec §4/§8, offline, synthetic frames only.

Params are injected explicitly (config stays None-scaffolded until the owner
types values, spec §7); loaders and the pre-registration gate are injected so
nothing here touches the network, the real cache, the ledger, or any book.
The signal fixtures are the working recipes from tests.test_qm_signals.
"""

import contextlib
import io
import os
import unittest
from datetime import date, timedelta

import pandas as pd
from test_qm_signals import PARAMS, breakout_fixture, parabolic_fixture

from options_researcher import qm_signals, qm_watch
from options_researcher.h7_watch import evaluation_session

# The exact banner the spec mandates on EVERY fire block (asserted verbatim).
BANNER = (
    "UNVALIDATED SIGNAL -- descriptive screen; no forward evidence exists "
    "until the SS5 study reports; not an entry recommendation; no book path."
)

AS_OF = "2022-06-16"  # a weekday; loaders are injected so no OOS/network gate
EVAL_ISO = evaluation_session(date.fromisoformat(AS_OF)).isoformat()


def _relabel(frame: pd.DataFrame, end_iso: str) -> pd.DataFrame:
    """Re-index `frame` to ISO-date strings (the module's OHLCV contract),
    ascending and ending exactly at `end_iso`, preserving row order/spacing."""
    idx = pd.bdate_range(end=end_iso, periods=len(frame))
    out = frame.copy()
    out.index = pd.Index([d.strftime("%Y-%m-%d") for d in idx], name="date")
    return out


def _adj_breakout(_symbol, eval_iso):
    return _relabel(breakout_fixture(), eval_iso)


def _adj_parabolic(_symbol, eval_iso):
    """Truncate the parabolic fixture at its FIRST qualifying session so the
    deduped scan's last (and only) fire lands exactly on the eval session --
    a mid-streak continuation is not a new fire (spec §3 dedupe)."""
    frame = parabolic_fixture()
    pos = next(i for i, t in enumerate(frame.index)
               if qm_signals.parabolic_qualifies(frame, t, PARAMS))
    return _relabel(frame.iloc[:pos + 1], eval_iso)


def _adj_quiet(_symbol, eval_iso):
    """A flat frame that fires neither signal."""
    closes = [100.0] * 80
    frame = pd.DataFrame(
        {"open": closes, "high": [c + 1 for c in closes],
         "low": [c - 1 for c in closes], "close": closes,
         "volume": [1_000_000.0] * len(closes)},
        dtype=float,
    )
    return _relabel(frame, eval_iso)


def _raw_close(value):
    """A RAW OHLCV loader whose last close (aligned with strikes) is `value`."""
    def _loader(_symbol, eval_iso):
        closes = [value] * 5
        frame = pd.DataFrame(
            {"open": closes, "high": [c + 1 for c in closes],
             "low": [c - 1 for c in closes], "close": closes,
             "volume": [1_000_000.0] * len(closes)},
            dtype=float,
        )
        return _relabel(frame, eval_iso)
    return _loader


def _chain(eval_iso, right, *, oi=900):
    """One monthly-ish expiration ~45 DTE past the eval session, with call and
    put strikes 140/145/150/155. Long call 145 ask 5.00 -> adverse_buy 5.05.
    `oi` sets open interest (drop below MIN_OPEN_INTEREST=100 to force RED)."""
    exp = (date.fromisoformat(eval_iso) + timedelta(days=45)).isoformat()
    rows = []
    for strike in (140.0, 145.0, 150.0, 155.0):
        rows.append({"expiration": exp, "strike": strike, "right": "C",
                     "bid": 4.80, "ask": 5.00, "open_interest": oi,
                     "iv": 0.4, "delta": 0.5, "gamma": 0.0,
                     "theta": 0.0, "vega": 0.0})
        rows.append({"expiration": exp, "strike": strike, "right": "P",
                     "bid": 4.80, "ask": 5.00, "open_interest": oi,
                     "iv": 0.4, "delta": -0.5, "gamma": 0.0,
                     "theta": 0.0, "vega": 0.0})
    df = pd.DataFrame(rows)
    return df if right is None else df


def _chain_loader(eval_iso_expected, *, oi=900):
    def _loader(_symbol, eval_iso):
        return _chain(eval_iso, None, oi=oi)
    return _loader


def _run(argv, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = qm_watch.main(argv, **kw)
    return rc, buf.getvalue()


class GateTests(unittest.TestCase):
    def test_gate_refusal_exits_2_before_loaders(self):
        calls = []

        def spy(_symbol, _eval):
            calls.append(1)
            raise AssertionError("loader must not run when the gate refuses")

        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=spy, load_raw=spy, load_chain=spy,
            params=PARAMS, gate=lambda: "QM pre-registration incomplete: refuse",
        )
        self.assertEqual(rc, 2)
        self.assertEqual(calls, [])
        self.assertIn("refuse", out)


class QuietTests(unittest.TestCase):
    def test_no_signal_prints_quiet_line_no_banner(self):
        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=_adj_quiet, load_raw=_raw_close(100.0),
            load_chain=_chain_loader(EVAL_ISO),
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertIn("MSFT: no signal", out)
        self.assertNotIn(BANNER, out)


class BreakoutFireTests(unittest.TestCase):
    def test_banner_long_call_and_spread_cards(self):
        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=_adj_breakout, load_raw=_raw_close(146.0),
            load_chain=_chain_loader(EVAL_ISO),
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(BANNER), 1)
        self.assertIn("BREAKOUT FIRE", out)
        self.assertIn(qm_watch.BANNER, out)
        # Long call 145 ask 5.00: adverse_buy = ceil(5.00*1.01*100)/100 = 5.05,
        # cost = 505, breakeven = 145 + 5.05 = 150.05.
        self.assertIn("LONG CALL $145", out)
        self.assertIn("cost $505", out)
        self.assertIn("breakeven $150.05", out)
        # Call debit spread long 145 / short 150: net = adverse_buy(5.00) -
        # adverse_sell(4.80) = 5.05 - floor(4.80*0.99*100)/100 = 5.05 - 4.75.
        self.assertIn("CALL DEBIT SPREAD +$145/-$150", out)
        self.assertIn("net $0.30", out)
        self.assertIn("long_liq:GREEN", out)
        self.assertIn("short_liq:GREEN", out)

    def test_builder_exact_numbers(self):
        cards = qm_watch.long_option_cards(
            _chain(EVAL_ISO, None), "C", 146.0, EVAL_ISO, (30, 60), 0.10)
        c145 = next(c for c in cards if c["strike"] == 145.0)
        self.assertAlmostEqual(c145["cost"], 505.0, places=6)
        self.assertAlmostEqual(c145["breakeven"], 150.05, places=6)
        self.assertTrue(c145["liq"])


class ParabolicFireTests(unittest.TestCase):
    def test_fade_label_and_put_cards(self):
        rc, out = _run(
            ["--as-of", AS_OF], universe=["NVDA"],
            load_adjusted=_adj_parabolic, load_raw=_raw_close(146.0),
            load_chain=_chain_loader(EVAL_ISO),
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(BANNER), 1)
        self.assertIn("PARABOLIC FIRE", out)
        self.assertIn("FADE SIGNAL", out)
        self.assertIn("LONG PUT $145", out)
        # Put breakeven = strike - premium = 145 - 5.05 = 139.95.
        self.assertIn("breakeven $139.95", out)
        # Put debit spread long 145 / short 140 (next strike BELOW).
        self.assertIn("PUT DEBIT SPREAD +$145/-$140", out)


class FireNoChainTests(unittest.TestCase):
    def test_missing_chain_prints_gap_no_cards_exit_0(self):
        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=_adj_breakout, load_raw=_raw_close(146.0),
            load_chain=lambda _s, _e: None,
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(BANNER), 1)  # still a fire block
        self.assertIn("DATA-GAP", out)
        self.assertIn("no cards", out)
        self.assertNotIn("LONG CALL", out)


class DataGapTests(unittest.TestCase):
    def test_missing_ohlcv_one_name_others_processed(self):
        def adj(symbol, eval_iso):
            if symbol == "MSFT":
                raise FileNotFoundError("no cache")
            return _adj_quiet(symbol, eval_iso)

        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT", "AMZN"],
            load_adjusted=adj, load_raw=_raw_close(100.0),
            load_chain=_chain_loader(EVAL_ISO),
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertIn("MSFT: DATA-GAP", out)
        self.assertIn("AMZN: no signal", out)

    def test_stale_ohlcv_prints_stale_gap(self):
        stale_end = (pd.bdate_range(end=EVAL_ISO, periods=2)[0]
                     ).strftime("%Y-%m-%d")

        def adj(_symbol, _eval_iso):
            return _relabel(breakout_fixture(), stale_end)

        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=adj, load_raw=_raw_close(146.0),
            load_chain=_chain_loader(EVAL_ISO),
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertIn("MSFT: DATA-GAP", out)
        self.assertIn("stale", out)
        self.assertIn(stale_end, out)
        self.assertNotIn(BANNER, out)


class IlliquidTests(unittest.TestCase):
    def test_illiquid_contract_shows_red_flag_not_excluded(self):
        rc, out = _run(
            ["--as-of", AS_OF], universe=["MSFT"],
            load_adjusted=_adj_breakout, load_raw=_raw_close(146.0),
            load_chain=_chain_loader(EVAL_ISO, oi=1),  # OI below MIN_OPEN_INTEREST
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 0)
        self.assertIn("LONG CALL $145", out)   # shown, not excluded
        self.assertIn("liq:RED", out)


class StdoutOnlyTests(unittest.TestCase):
    def test_main_writes_no_files(self):
        cwd = os.getcwd()
        tmp = os.path.join(
            os.environ.get(
                "TMPDIR", "/tmp"), f"qm_watch_stdout_{os.getpid()}")
        os.makedirs(tmp, exist_ok=True)
        try:
            os.chdir(tmp)
            before = set(os.listdir(tmp))
            _run(
                ["--as-of", AS_OF], universe=["MSFT"],
                load_adjusted=_adj_breakout, load_raw=_raw_close(146.0),
                load_chain=_chain_loader(EVAL_ISO),
                params=PARAMS, gate=lambda: None,
            )
            after = set(os.listdir(tmp))
        finally:
            os.chdir(cwd)
        self.assertEqual(before, after)


class FutureAsOfTests(unittest.TestCase):
    def test_future_as_of_refused_exit_2(self):
        future = (date.today() + timedelta(days=5)).isoformat()
        calls = []

        def spy(_symbol, _eval):
            calls.append(1)
            return None

        rc, out = _run(
            ["--as-of", future], universe=["MSFT"],
            load_adjusted=spy, load_raw=spy, load_chain=spy,
            params=PARAMS, gate=lambda: None,
        )
        self.assertEqual(rc, 2)
        self.assertEqual(calls, [])
        self.assertIn("future", out.lower())


if __name__ == "__main__":
    unittest.main()

"""tests/test_entry_watch.py"""
import unittest

import pandas as pd

import config
from options_researcher import entry_watch as ew


def _leaps_row(oi=500, bid=40.0, ask=41.0):
    return pd.Series({"open_interest": oi, "bid": bid, "ask": ask,
                      "strike": 140.0, "delta": 0.70})


class TriggerStatusTests(unittest.TestCase):
    def test_all_conditions_met_fires(self):
        s = ew.trigger_status("VST", close=139.50, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "FIRE")
        self.assertEqual(s["unmet"], [])

    def test_price_above_trigger_waits(self):
        s = ew.trigger_status("VST", close=158.63, iv_rank=0.40,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("trigger" in u for u in s["unmet"]))

    def test_rich_iv_waits_even_below_price(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.80,
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("IV-rank" in u for u in s["unmet"]))

    def test_illiquid_leaps_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=_leaps_row(oi=10))
        self.assertEqual(s["verdict"], "WAIT")

    def test_missing_leaps_candidate_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                              leaps_row=None)
        self.assertEqual(s["verdict"], "WAIT")
        self.assertTrue(any("no LEAPS candidate" in u for u in s["unmet"]))

    def test_nan_iv_rank_waits(self):
        s = ew.trigger_status("VST", close=139.00, iv_rank=float("nan"),
                              leaps_row=_leaps_row())
        self.assertEqual(s["verdict"], "WAIT")

    def test_uses_config_constants(self):
        self.assertEqual(ew.trigger_status("AMZN", close=219.0, iv_rank=0.1,
                                           leaps_row=_leaps_row())["trigger"],
                         config.H5_ENTRY_TRIGGERS["AMZN"])


class MainTests(unittest.TestCase):
    def _rows(self):
        return [{"symbol": "VST", "close": 158.63, "trigger": 140.0,
                 "iv_rank": 0.47, "price_ok": False, "iv_ok": True,
                 "liq_ok": True, "unmet": ["close $158.63 > trigger $140.00"],
                 "verdict": "WAIT", "close_asof": "2026-07-06",
                 "chain_asof": "2026-07-06"},
                {"symbol": "AMZN", "close": 219.00, "trigger": 220.0,
                 "iv_rank": 0.30, "price_ok": True, "iv_ok": True,
                 "liq_ok": True, "unmet": [], "verdict": "FIRE",
                 "close_asof": "2026-07-06", "chain_asof": "2026-07-02"}]

    def test_main_prints_verdicts_and_staleness(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ew.main(rows=self._rows())
        out = buf.getvalue()
        self.assertIn("VST", out)
        self.assertIn("WAIT", out)
        self.assertIn("FIRE", out)
        self.assertIn("evaluate", out.lower())
        self.assertIn("stale", out.lower())
        self.assertIn("never auto-enters", out)


if __name__ == "__main__":
    unittest.main()

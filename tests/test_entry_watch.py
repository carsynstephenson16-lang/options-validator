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
        above = config.H5_ENTRY_TRIGGERS["VST"] + 5.0
        s = ew.trigger_status("VST", close=above, iv_rank=0.40,
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

    def test_close_exactly_at_trigger_is_ok(self):
        s = ew.trigger_status("VST", close=config.H5_ENTRY_TRIGGERS["VST"],
                              iv_rank=0.40, leaps_row=_leaps_row())
        self.assertTrue(s["price_ok"])
        self.assertEqual(s["verdict"], "FIRE")

    def test_iv_rank_exactly_at_max_is_ok(self):
        s = ew.trigger_status("VST", close=139.00,
                              iv_rank=config.H5_ENTRY_IVR_MAX,
                              leaps_row=_leaps_row())
        self.assertTrue(s["iv_ok"])
        self.assertEqual(s["verdict"], "FIRE")

    def test_missing_chain_file_message_differs_from_no_candidate(self):
        no_cand = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                                    leaps_row=None)
        no_file = ew.trigger_status("VST", close=139.00, iv_rank=0.40,
                                    leaps_row=None, chain_missing=True)
        self.assertEqual(no_cand["verdict"], "WAIT")
        self.assertEqual(no_file["verdict"], "WAIT")
        self.assertTrue(any("no LEAPS candidate" in u
                            for u in no_cand["unmet"]))
        self.assertTrue(any("no cached chain file" in u
                            for u in no_file["unmet"]))
        self.assertTrue(any("top-up" in u for u in no_file["unmet"]))
        self.assertNotEqual(no_cand["unmet"], no_file["unmet"])


class MainTests(unittest.TestCase):
    def _rows(self):
        return [{"symbol": "VST", "close": 158.63, "trigger": 140.0,
                 "iv_rank": 0.47, "price_ok": False, "iv_ok": True,
                 "liq_ok": True, "unmet": ["close $158.63 > trigger $140.00"],
                 "verdict": "WAIT", "close_asof": "2026-07-06",
                 "chain_asof": "2026-07-06", "iv_asof": "2026-07-02"},
                {"symbol": "AMZN", "close": 219.00, "trigger": 220.0,
                 "iv_rank": 0.30, "price_ok": True, "iv_ok": True,
                 "liq_ok": True, "unmet": [], "verdict": "FIRE",
                 "close_asof": "2026-07-06", "chain_asof": "2026-07-02",
                 "iv_asof": "2026-07-06"}]

    def _run_main(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ew.main(rows=self._rows())
        return buf.getvalue()

    def test_main_prints_verdicts_and_staleness(self):
        out = self._run_main()
        self.assertIn("VST", out)
        self.assertIn("WAIT", out)
        self.assertIn("FIRE", out)
        self.assertIn("evaluate", out.lower())
        self.assertIn("stale", out.lower())
        self.assertIn("never auto-enters", out)

    def test_main_prints_stale_iv_rank_note(self):
        out = self._run_main()
        self.assertIn("IV-rank is stale", out)
        self.assertIn("2026-07-02 < close 2026-07-06", out)
        self.assertIn("feature refresh", out)


if __name__ == "__main__":
    unittest.main()

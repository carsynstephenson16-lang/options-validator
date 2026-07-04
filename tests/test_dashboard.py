"""tests/test_dashboard.py"""
import unittest

from options_researcher.dashboard import assemble


class AssembleTests(unittest.TestCase):
    def test_assemble_from_injected_parts(self):
        book = {"marks": [{"id": "p1", "structure": "leaps_call",
                           "symbol": "MSFT", "strike": 340.0,
                           "expiration": "2027-06-17", "contracts": 1,
                           "dte": 300, "mark": 80.0, "pnl": -461.0,
                           "flags": []}],
                "bucket_issues": []}
        facts = ["2026-07-04T00:00:00+00:00\tCEG_CACHE_COMPLETE ...",
                 "2026-07-04T00:00:00+00:00\tSTUDY_C VST d=0.20: ..."]
        d = assemble(book=book, facts=facts,
                     reports=["reports/2026-07-04-study-a.md"],
                     closes={"MSFT": [430.0, 431.5, 429.0]})
        self.assertEqual(d["book"][0]["symbol"], "MSFT")
        self.assertTrue(any(a["key"] == "CEG_CACHE_COMPLETE"
                            for a in d["achievements"]))
        self.assertIn("MSFT", d["sparklines"])


if __name__ == "__main__":
    unittest.main()

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


class RenderTests(unittest.TestCase):
    def test_render_contains_sections_and_no_external_assets(self):
        from options_researcher.dashboard import render
        html = render(assemble(book={"marks": [], "bucket_issues": []},
                               facts=[], reports=[], closes={}))
        for token in ("MISSION CONTROL", "PARTY", "QUEST LOG",
                      "ACHIEVEMENTS", "<style>"):
            self.assertIn(token, html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://cdn", html)

    def test_render_shows_placeholder_for_missing_quote_mark(self):
        # Mirrors what mark_position() actually produces when a chain quote
        # can't be found for a position: mark/pnl both None, QUOTE_MISSING
        # flag set. dict.get("mark", "") does NOT help here because the key
        # is present with value None -- the "" default never kicks in, so
        # the raw Python literal "None" must not leak into the table cell.
        from options_researcher.dashboard import render
        book = {"marks": [{"id": "p1", "structure": "csp", "symbol": "VST",
                           "strike": 100.0, "expiration": "2027-01-15",
                           "contracts": 1, "dte": 30, "mark": None,
                           "pnl": None, "flags": ["QUOTE_MISSING"]}],
                "bucket_issues": []}
        html = render(assemble(book=book, facts=[], reports=[], closes={}))
        self.assertIn("n/a", html)
        self.assertNotIn(">None<", html)


class MainTests(unittest.TestCase):
    def test_main_writes_html_file_and_prints_path(self):
        import io
        import os
        import tempfile
        from contextlib import redirect_stdout
        from unittest import mock

        from options_researcher import dashboard

        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "dashboard", "index.html")
            with mock.patch.object(dashboard, "OUTPUT_PATH", out_path):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    dashboard.main(book={"marks": [], "bucket_issues": []},
                                   facts=[], reports=[], closes={})
            self.assertTrue(os.path.exists(out_path))
            with open(out_path) as f:
                content = f.read()
            self.assertIn("MISSION CONTROL", content)
            self.assertIn(out_path, buf.getvalue())
            self.assertIn("browser", buf.getvalue().lower())


if __name__ == "__main__":
    unittest.main()

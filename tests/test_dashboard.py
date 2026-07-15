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


class DataAsOfBannerTests(unittest.TestCase):
    def test_default_data_as_of_uses_cached_series_index_not_wallclock(self):
        from unittest import mock

        import pandas as pd

        import config
        from options_researcher import dashboard as d

        series = pd.Series([1.0, 2.0], index=["2026-01-02", "2026-01-05"])
        with mock.patch.object(config, "UNIVERSE", ["FAKE"]), \
                mock.patch("data.underlying_closes.load_closes",
                          return_value=series):
            self.assertEqual(d._default_data_as_of(), "2026-01-05")

    def test_default_data_as_of_reports_earliest_symbol_when_stale(self):
        # A stale name must not hide behind a fresher one: the page-level
        # as-of date is the EARLIEST last-cached-close date, not the latest.
        from unittest import mock

        import pandas as pd

        import config
        from options_researcher import dashboard as d

        fresh = pd.Series([1.0], index=["2026-02-01"])
        stale = pd.Series([1.0], index=["2026-01-10"])

        def fake_load(sym, *_a, **_k):
            return {"FRESH": fresh, "STALE": stale}[sym]

        with mock.patch.object(config, "UNIVERSE", ["FRESH", "STALE"]), \
                mock.patch("data.underlying_closes.load_closes",
                          side_effect=fake_load):
            self.assertEqual(d._default_data_as_of(), "2026-01-10")

    def test_default_data_as_of_skips_missing_series_and_falls_back(self):
        from unittest import mock

        import config
        from options_researcher import dashboard as d

        with mock.patch.object(config, "UNIVERSE", ["MISSING"]), \
                mock.patch("data.underlying_closes.load_closes",
                          side_effect=OSError("no such file")):
            self.assertEqual(d._default_data_as_of(), "unknown")

    def test_render_shows_prominent_data_as_of_banner(self):
        from options_researcher.dashboard import assemble, render

        data = assemble(book={"marks": [], "bucket_issues": []}, facts=[],
                        reports=[], closes={}, data_as_of="2026-07-10")
        html = render(data)
        self.assertIn("DATA AS-OF 2026-07-10 CLOSE", html)
        self.assertIn("Research only", html)
        self.assertIn("verify live quotes in your broker", html)
        self.assertIn("data-asof-banner", html)
        # Prominent: the banner appears before the first content panel
        # (the <title> tag also contains "MISSION CONTROL", so anchor on
        # the <h1> heading instead).
        self.assertLess(html.index("DATA AS-OF"), html.index("<h1>MISSION CONTROL"))

    def test_render_falls_back_when_data_as_of_missing(self):
        from options_researcher.dashboard import assemble, render

        data = assemble(book={"marks": [], "bucket_issues": []}, facts=[],
                        reports=[], closes={}, data_as_of=None)
        html = render(data)
        self.assertIn("DATA AS-OF", html)


class TriggerPillTests(unittest.TestCase):
    def test_render_shows_trigger_pills(self):
        from options_researcher import dashboard as d
        data = d.assemble(book={"marks": []}, facts=[], reports=[],
                          closes={}, triggers={"VST": "WAIT", "AMZN": "FIRE"})
        html = d.render(data)
        self.assertIn("TRIGGER: WAIT", html)
        self.assertIn("TRIGGER: FIRE", html)

    def test_assemble_default_triggers_never_raises(self):
        from options_researcher import dashboard as d
        data = d.assemble(book={"marks": []}, facts=[], reports=[], closes={})
        self.assertIsInstance(data["triggers"], dict)

    def test_assemble_warns_on_stderr_when_entry_watch_fails(self):
        import contextlib
        import io
        from unittest import mock

        from options_researcher import dashboard as d
        from options_researcher import entry_watch
        err = io.StringIO()
        with mock.patch.object(entry_watch, "_gather",
                               side_effect=OSError("no cache")), \
                contextlib.redirect_stderr(err):
            data = d.assemble(book={"marks": []}, facts=[], reports=[],
                              closes={})
        self.assertEqual(data["triggers"], {})
        self.assertIn("WARN entry-watch unavailable", err.getvalue())

    def test_assemble_propagates_unexpected_entry_watch_errors(self):
        from unittest import mock

        from options_researcher import dashboard as d
        from options_researcher import entry_watch
        with mock.patch.object(entry_watch, "_gather",
                               side_effect=ZeroDivisionError("bug")):
            with self.assertRaises(ZeroDivisionError):
                d.assemble(book={"marks": []}, facts=[], reports=[],
                           closes={})


if __name__ == "__main__":
    unittest.main()

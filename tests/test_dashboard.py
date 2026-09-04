"""tests/test_dashboard.py"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from options_researcher.dashboard import assemble, render

_H7_WINDOW = {
    "ok": True,
    "start": "2026-07-20",
    "end": "2026-10-26",
    "total_sessions": 70,
    "sessions_elapsed": 3,
    "sessions_remaining": 67,
    "included": ["AMD"],
    "excluded": ["NVDA"],
    "event_counts": {"window_registration": 1},
    "entries_taken": 0,
    "receipts": {
        "evaluation_session": "2026-07-21",
        "source_health_present": True,
        "data_gate_present": False,
        "data_gate_verdict": None,
    },
}


class AssembleTests(unittest.TestCase):
    def test_assemble_from_injected_parts(self):
        book = {
            "marks": [
                {
                    "id": "p1",
                    "structure": "leaps_call",
                    "symbol": "MSFT",
                    "strike": 340.0,
                    "expiration": "2027-06-17",
                    "contracts": 1,
                    "dte": 300,
                    "mark": 80.0,
                    "pnl": -461.0,
                    "flags": [],
                }
            ],
            "bucket_issues": [],
        }
        facts = [
            "2026-07-04T00:00:00+00:00\tCEG_CACHE_COMPLETE ...",
            "2026-07-04T00:00:00+00:00\tSTUDY_C VST d=0.20: ...",
        ]
        d = assemble(
            book=book,
            facts=facts,
            reports=["reports/2026-07-04-study-a.md"],
            closes={"MSFT": [430.0, 431.5, 429.0]},
        )
        self.assertEqual(d["book"][0]["symbol"], "MSFT")
        self.assertTrue(any(a["key"] == "CEG_CACHE_COMPLETE" for a in d["achievements"]))
        self.assertIn("MSFT", d["sparklines"])


class RenderTests(unittest.TestCase):
    @staticmethod
    def _offline_parts() -> dict:
        return {
            "book": {"marks": [], "bucket_issues": []},
            "facts": [],
            "reports": [],
            "closes": {},
            "triggers": {},
            "data_as_of": "2026-07-21",
        }

    def test_h7_window_panel_rendered(self):
        from options_researcher import dashboard

        data = dashboard.assemble(
            h7_window={
                "ok": True,
                "start": "2026-07-20",
                "end": "2026-10-26",
                "total_sessions": 70,
                "sessions_elapsed": 3,
                "sessions_remaining": 67,
                "included": ["AMD"],
                "excluded": ["NVDA"],
                "event_counts": {"window_registration": 1},
                "entries_taken": 0,
                "receipts": {
                    "evaluation_session": "2026-07-21",
                    "source_health_present": True,
                    "data_gate_present": False,
                    "data_gate_verdict": None,
                },
            },
            h7_authority={
                "h7_active": False,
                "blockers": ["H7 forward-paper authority is paused; no active namespace exists."],
            },
            **self._offline_parts(),
        )

        html = dashboard.render(data)
        self.assertIn("H7 FORWARD WINDOW", html)
        self.assertIn("entries taken: 0", html)

    def test_h7_window_panel_absent_store(self):
        from options_researcher import dashboard

        data = dashboard.assemble(
            h7_window={"ok": False, "detail": "no forward store"},
            h7_authority={
                "h7_active": False,
                "blockers": ["H7 forward-paper authority is paused; no active namespace exists."],
            },
            **self._offline_parts(),
        )

        html = dashboard.render(data)
        self.assertIn("no forward store", html)

    def test_render_contains_sections_and_no_external_assets(self):
        from options_researcher.dashboard import render

        html = render(
            assemble(book={"marks": [], "bucket_issues": []}, facts=[], reports=[], closes={})
        )
        for token in ("MISSION CONTROL", "PARTY", "QUEST LOG", "ACHIEVEMENTS", "<style>"):
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

        book = {
            "marks": [
                {
                    "id": "p1",
                    "structure": "csp",
                    "symbol": "VST",
                    "strike": 100.0,
                    "expiration": "2027-01-15",
                    "contracts": 1,
                    "dte": 30,
                    "mark": None,
                    "pnl": None,
                    "flags": ["QUOTE_MISSING"],
                }
            ],
            "bucket_issues": [],
        }
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
                    dashboard.main(
                        book={"marks": [], "bucket_issues": []}, facts=[], reports=[], closes={}
                    )
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
        with (
            mock.patch.object(config, "UNIVERSE", ["FAKE"]),
            mock.patch("data.underlying_closes.load_closes", return_value=series),
        ):
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

        with (
            mock.patch.object(config, "UNIVERSE", ["FRESH", "STALE"]),
            mock.patch("data.underlying_closes.load_closes", side_effect=fake_load),
        ):
            self.assertEqual(d._default_data_as_of(), "2026-01-10")

    def test_default_data_as_of_skips_missing_series_and_falls_back(self):
        from unittest import mock

        import config
        from options_researcher import dashboard as d

        with (
            mock.patch.object(config, "UNIVERSE", ["MISSING"]),
            mock.patch("data.underlying_closes.load_closes", side_effect=OSError("no such file")),
        ):
            self.assertEqual(d._default_data_as_of(), "unknown")

    def test_render_shows_prominent_data_as_of_banner(self):
        from options_researcher.dashboard import assemble, render

        data = assemble(
            book={"marks": [], "bucket_issues": []},
            facts=[],
            reports=[],
            closes={},
            data_as_of="2026-07-10",
        )
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

        data = assemble(
            book={"marks": [], "bucket_issues": []},
            facts=[],
            reports=[],
            closes={},
            data_as_of=None,
        )
        html = render(data)
        self.assertIn("DATA AS-OF", html)


class TriggerPillTests(unittest.TestCase):
    def test_render_shows_trigger_pills(self):
        from options_researcher import dashboard as d

        data = d.assemble(
            book={"marks": []},
            facts=[],
            reports=[],
            closes={},
            triggers={"VST": "WAIT", "AMZN": "FIRE"},
        )
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
        with (
            mock.patch.object(entry_watch, "_gather", side_effect=OSError("no cache")),
            contextlib.redirect_stderr(err),
        ):
            data = d.assemble(book={"marks": []}, facts=[], reports=[], closes={})
        self.assertEqual(data["triggers"], {})
        self.assertIn("WARN entry-watch unavailable", err.getvalue())

    def test_assemble_propagates_unexpected_entry_watch_errors(self):
        from unittest import mock

        from options_researcher import dashboard as d
        from options_researcher import entry_watch

        with mock.patch.object(entry_watch, "_gather", side_effect=ZeroDivisionError("bug")):
            with self.assertRaises(ZeroDivisionError):
                d.assemble(book={"marks": []}, facts=[], reports=[], closes={})


class Brief37DashboardRegressionTests(unittest.TestCase):
    _PAUSED_AUTHORITY = {
        "h7_active": False,
        "blockers": ["H7 forward-paper authority is paused; no active namespace exists."],
    }

    def _assemble(self, **kwargs):
        defaults = {
            "book": {"marks": [], "bucket_issues": []},
            "facts": [],
            "reports": [],
            "closes": {},
            "triggers": {},
            "h7_window": {"ok": False, "detail": "fixture"},
            "h7_authority": self._PAUSED_AUTHORITY,
        }
        defaults.update(kwargs)
        return assemble(**defaults)

    def test_extended_close_range_controls_banner_and_60_point_sparkline(self):
        import config
        from options_researcher import dashboard as d

        series = pd.Series(
            range(70), index=pd.date_range("2026-06-01", periods=70).strftime("%Y-%m-%d")
        )

        def sliced_load(_symbol, start, end, **_kwargs):
            return series.loc[start:end]

        with (
            mock.patch.object(config, "UNIVERSE", ["FAKE"]),
            mock.patch("data.underlying_closes.load_closes", side_effect=sliced_load),
        ):
            self.assertEqual(d._default_data_as_of(today="2026-09-04"), "2026-08-09")
            self.assertEqual(
                d._default_closes(today="2026-09-04"), {"FAKE": [float(v) for v in range(10, 70)]}
            )

    def test_held_role_uses_single_holdings_lot_and_names_no_options(self):
        data = self._assemble(
            holdings=pd.DataFrame(
                [
                    {"symbol": "VST", "shares": 39},
                ]
            )
        )
        self.assertIn("Held — 39 shares, no options", render(data))

    def test_held_role_uses_holdings_sum_and_option_mark_count(self):
        data = self._assemble(
            holdings=pd.DataFrame(
                [{"symbol": "VST", "shares": 20}, {"symbol": "VST", "shares": 19}]
            ),
            book={
                "marks": [{"symbol": "VST", "pnl": 0.0}, {"symbol": "VST", "pnl": 0.0}],
                "bucket_issues": [],
            },
        )
        self.assertIn("Held — 39 shares, 2 open option marks", render(data))

    def test_held_role_makes_holdings_failures_and_missing_row_visible(self):
        from options_researcher import portfolio

        err = io.StringIO()
        with (
            mock.patch.object(portfolio, "load_holdings", side_effect=FileNotFoundError("missing")),
            contextlib.redirect_stderr(err),
        ):
            unreadable = self._assemble()
        self.assertIn("Held — shares UNKNOWN (holdings.csv unreadable)", render(unreadable))
        self.assertIn("missing", err.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            no_row = self._assemble(holdings=pd.DataFrame([{"symbol": "MSFT", "shares": 100}]))
        self.assertIn("Held — shares UNKNOWN (no holdings.csv row for VST)", render(no_row))
        self.assertIn("no holdings.csv row for VST", err.getvalue())

    def test_held_role_treats_short_csv_row_as_unreadable(self):
        from options_researcher import portfolio

        real_load_holdings = portfolio.load_holdings
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "holdings.csv"
            path.write_text("symbol,shares,cost_basis,acquired\nVST,39\n")
            with mock.patch.object(
                portfolio, "load_holdings", side_effect=lambda: real_load_holdings(str(path))
            ):
                data = self._assemble()
        self.assertIn("Held — shares UNKNOWN (holdings.csv unreadable)", render(data))

    def test_h7_panel_pauses_only_when_authority_is_not_granted(self):
        from options_researcher import dashboard

        paused = dashboard._h7_window_panel(_H7_WINDOW, h7_authority=self._PAUSED_AUTHORITY)
        self.assertIn("H7 FORWARD WINDOW — PAUSED (H7 authority not granted)", paused)
        self.assertIn("registered window (paused; scores nothing while paused)", paused)
        self.assertIn("entries taken: 0", paused)
        self.assertNotIn("live", paused)
        expected_live = (
            '<div style="border:1px solid #6ab;padding:12px;margin:12px 0">'
            "<b>H7 FORWARD WINDOW</b> (live, scores once 2026-10-26)<br>"
            "sessions: 3/70 elapsed (67 left) &middot; entries taken: 0<br>"
            "universe: 1 in / 1 out &middot; session 2026-07-21 receipts: "
            "health OK, gate MISSING</div>"
        )
        self.assertEqual(
            dashboard._h7_window_panel(
                _H7_WINDOW, h7_authority={"h7_active": True, "blockers": []}
            ),
            expected_live,
        )

    def test_h7_panel_fails_visible_when_paused_blocker_contract_changes(self):
        from options_researcher import dashboard

        for blockers in ([], ["first", "second"]):
            with self.subTest(blockers=blockers):
                panel = dashboard._h7_window_panel(
                    _H7_WINDOW, h7_authority={"h7_active": False, "blockers": blockers}
                )
                self.assertIn(
                    "H7 BLOCKER TEXT UNAVAILABLE (ritual_authority contract changed)", panel
                )

    def test_achievement_tiles_deduplicate_tag_and_show_count_suffix(self):
        facts = [
            "2026-07-04T00:00:00+00:00\tSTUDY_C first completion",
            "2026-07-05T00:00:00+00:00\tSTUDY_C second completion",
            "2026-07-06T00:00:00+00:00\tSTUDY_C third completion",
        ]
        data = self._assemble(holdings=pd.DataFrame([{"symbol": "VST", "shares": 39}]), facts=facts)
        self.assertEqual(
            data["achievements"],
            [
                {
                    "key": "STUDY_C",
                    "title": "Study Hall: C",
                    "flavor": "Ran the covered-call study",
                    "count": 3,
                }
            ],
        )
        self.assertIn("Study Hall: C ×3", render(data))

    def test_dashboard_source_has_no_stale_vst_share_count(self):
        source = Path(__file__).parents[1] / "options_researcher" / "dashboard.py"
        self.assertNotIn("38 shares", source.read_text())


if __name__ == "__main__":
    unittest.main()

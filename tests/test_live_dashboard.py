"""tests/test_live_dashboard.py -- offline tests for the live dashboard server.

No network beyond 127.0.0.1 loopback sockets, no ThetaData: live_quotes is
never imported (the module under test must not import it at module level
either -- asserted below); every refresh function is a stub injected through
LiveCache / LiveDashboardServer, and entry_watch._gather is patched.
"""
from __future__ import annotations

import contextlib
import http.client
import inspect
import io
import json
import threading
import unittest
from unittest import mock

import config
from options_researcher import live_dashboard


def _live_payload(gen: str = "2026-07-16T15:00:00+00:00",
                  status: str = "ok") -> dict:
    return {
        "generated_at_utc": gen,
        "session_state": "open",
        "probe": {"ok": True, "reason": "fresh"},
        "symbols": {
            "VST": {"status": status, "spot": 158.43, "spot_source": "stock",
                    "spot_ts": gen, "armed": True, "trigger": 160.0,
                    "atm_iv": 0.52, "iv_rank_preview": 0.41, "leaps": None,
                    "gates": {"price": "MET", "ivr": "MET",
                              "liquidity": "UNKNOWN"},
                    "note": ""},
        },
    }


_OFFICIAL_ROWS = [
    {"symbol": "VST", "close": 158.43, "trigger": 160.0, "iv_rank": 0.31,
     "price_ok": True, "iv_ok": True, "liq_ok": False,
     "unmet": ["LEAPS fails liquidity gates"], "verdict": "WAIT",
     "close_asof": "2026-07-15", "chain_asof": "2026-07-15",
     "iv_asof": "2026-07-15"},
    {"symbol": "AMZN", "close": 219.10, "trigger": 220.0, "iv_rank": 0.28,
     "price_ok": True, "iv_ok": True, "liq_ok": True,
     "unmet": [], "verdict": "FIRE",
     "close_asof": "2026-07-15", "chain_asof": "2026-07-15",
     "iv_asof": "2026-07-15"},
]


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class LiveCacheTests(unittest.TestCase):
    def test_ttl_respected(self):
        clock = FakeClock()
        calls = []

        def refresh():
            calls.append(1)
            return _live_payload(gen=f"g{len(calls)}")

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=25, clock=clock)
        p1 = cache.get()
        self.assertEqual(len(calls), 1)
        clock.t = 24.9  # still inside TTL
        self.assertEqual(cache.get()["generated_at_utc"],
                         p1["generated_at_utc"])
        self.assertEqual(len(calls), 1)
        clock.t = 25.0  # expired
        p2 = cache.get()
        self.assertEqual(len(calls), 2)
        self.assertEqual(p2["generated_at_utc"], "g2")

    def test_single_flight_first_fill(self):
        calls = []
        started = threading.Event()
        release = threading.Event()

        def refresh():
            calls.append(1)
            started.set()
            release.wait(timeout=5)
            return _live_payload()

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=60)
        results: list[dict] = []
        threads = [threading.Thread(target=lambda: results.append(cache.get()))
                   for _ in range(6)]
        for t in threads:
            t.start()
        self.assertTrue(started.wait(timeout=5))
        release.set()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(len(calls), 1)  # exactly one refresh for N callers
        self.assertEqual(len(results), 6)
        for r in results:
            self.assertEqual(r["symbols"]["VST"]["status"], "ok")

    def test_stale_served_while_refresh_in_flight(self):
        clock = FakeClock()
        state = {"calls": 0}
        entered = threading.Event()
        release = threading.Event()

        def refresh():
            state["calls"] += 1
            if state["calls"] == 1:
                return _live_payload(gen="g1")
            entered.set()
            release.wait(timeout=5)
            return _live_payload(gen="g2")

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=25, clock=clock)
        self.assertEqual(cache.get()["generated_at_utc"], "g1")
        clock.t = 100.0  # expire; next get() must refresh
        refresher = threading.Thread(target=cache.get)
        refresher.start()
        self.assertTrue(entered.wait(timeout=5))
        # Concurrent caller during the in-flight refresh: served the stale
        # payload immediately, never blocked, never triggered a second call.
        stale = cache.get()
        self.assertEqual(stale["generated_at_utc"], "g1")
        self.assertEqual(state["calls"], 2)
        release.set()
        refresher.join(timeout=5)
        self.assertEqual(cache.get()["generated_at_utc"], "g2")
        self.assertEqual(state["calls"], 2)

    def test_exception_marks_unavailable_and_clears_fields(self):
        clock = FakeClock()
        plan: list = [lambda: _live_payload(gen="g1"), RuntimeError("boom")]

        def refresh():
            step = plan.pop(0)
            if isinstance(step, Exception):
                raise step
            return step()

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=25, clock=clock)
        p1 = cache.get()
        self.assertTrue(p1["symbols"]["VST"]["armed"])
        clock.t = 30.0
        p2 = cache.get()  # refresh raises; must NOT propagate
        self.assertIn("refresh_error", p2)
        self.assertIn("boom", p2["refresh_error"])
        row = p2["symbols"]["VST"]
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(row["last_good_utc"], "g1")
        # Previous armed/green fields are GONE -- only status + last_good_utc
        # survive; no stale spot/gates can stand.
        self.assertEqual(set(row), {"status", "last_good_utc"})
        self.assertNotIn("armed", row)
        self.assertNotIn("spot", row)
        self.assertNotIn("gates", row)
        # The failure payload is cached too (throttles retry storms).
        clock.t = 40.0
        p3 = cache.get()
        self.assertIn("refresh_error", p3)
        self.assertEqual(len(plan), 0)

    def test_recovery_after_next_success(self):
        clock = FakeClock()
        plan: list = [lambda: _live_payload(gen="g1"), RuntimeError("boom"),
                      lambda: _live_payload(gen="g3")]

        def refresh():
            step = plan.pop(0)
            if isinstance(step, Exception):
                raise step
            return step()

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=25, clock=clock)
        cache.get()
        clock.t = 30.0
        self.assertIn("refresh_error", cache.get())
        clock.t = 60.0
        p3 = cache.get()
        self.assertNotIn("refresh_error", p3)
        row = p3["symbols"]["VST"]
        self.assertEqual(row["status"], "ok")
        self.assertTrue(row["armed"])
        self.assertEqual(p3["generated_at_utc"], "g3")

    def test_last_good_injected_when_refresh_reports_nonok(self):
        # A SUCCESSFUL refresh whose row is non-ok (e.g. stale quote) keeps
        # its own fresh fields and gains the retained last_good_utc.
        clock = FakeClock()
        second = _live_payload(gen="g2")
        second["symbols"]["VST"] = {"status": "unavailable",
                                    "note": "stale quote"}
        plan = [_live_payload(gen="g1"), second]
        cache = live_dashboard.LiveCache(lambda: plan.pop(0), ttl_seconds=25,
                                         clock=clock)
        cache.get()
        clock.t = 30.0
        p2 = cache.get()
        row = p2["symbols"]["VST"]
        self.assertEqual(row["status"], "unavailable")
        self.assertEqual(row["last_good_utc"], "g1")
        self.assertEqual(row["note"], "stale quote")
        self.assertNotIn("refresh_error", p2)

    def test_exception_with_no_prior_payload(self):
        def refresh():
            raise OSError("provider down")

        cache = live_dashboard.LiveCache(refresh, ttl_seconds=25,
                                         clock=FakeClock())
        payload = cache.get()  # must not raise
        self.assertIn("refresh_error", payload)
        self.assertEqual(payload["symbols"], {})


class BuildPayloadTests(unittest.TestCase):
    def test_official_failure_tolerated(self):
        with mock.patch("options_researcher.entry_watch._gather",
                        side_effect=OSError("no closes cache")):
            with contextlib.redirect_stderr(io.StringIO()):
                payload = live_dashboard.build_payload({"symbols": {}})
        self.assertEqual(payload["official"], [])
        self.assertIn("no closes cache", payload["official_error"])
        self.assertEqual(payload["poll_seconds"], config.LIVE_POLL_SECONDS)

    def test_official_rows_gathered_and_untouched(self):
        with mock.patch("options_researcher.entry_watch._gather",
                        return_value=list(_OFFICIAL_ROWS)):
            payload = live_dashboard.build_payload(_live_payload())
        self.assertEqual(payload["official"], _OFFICIAL_ROWS)
        self.assertNotIn("official_error", payload)
        self.assertEqual(payload["live"]["symbols"]["VST"]["status"], "ok")
        self.assertEqual(
            payload["freshness"]["official_eod"],
            {"status": "COMPLETE", "as_of": "2026-07-15"},
        )
        self.assertEqual(
            payload["freshness"]["intraday"]["captured_at_utc"],
            "2026-07-16T15:00:00+00:00",
        )

    def test_explicit_rows_bypass_gather(self):
        with mock.patch("options_researcher.entry_watch._gather",
                        side_effect=AssertionError("must not be called")):
            payload = live_dashboard.build_payload({"symbols": {}},
                                                   official_rows=[])
        self.assertEqual(payload["official"], [])
        self.assertNotIn("official_error", payload)


class InjectLivePanelTests(unittest.TestCase):
    def test_panel_and_script_inserted_before_body_close(self):
        html = "<html><body><p>STATIC</p></body></html>"
        out = live_dashboard.inject_live_panel(html)
        self.assertIn('id="live-panel"', out)
        self.assertIn("<script>", out)
        self.assertIn("<p>STATIC</p>", out)
        self.assertIn('id="lv-freshness"', out)
        self.assertLess(out.index('id="live-panel"'), out.rindex("</body>"))
        self.assertLess(out.index("<script>"), out.rindex("</body>"))

    def test_no_external_urls_in_injected_block(self):
        panel = live_dashboard._panel_html()
        self.assertNotIn("http://", panel)
        self.assertNotIn("https://", panel)
        self.assertNotIn("//cdn", panel)
        self.assertIn('fetch("/live.json"', panel)  # relative URL only

    def test_live_lane_renderer_has_no_fire_literal(self):
        # The live-preview lane must be INCAPABLE of rendering FIRE: its
        # renderer contains no FIRE literal anywhere; only the official-lane
        # renderer may carry the word.
        self.assertNotIn("FIRE", live_dashboard._LIVE_LANE_JS)
        self.assertIn("FIRE", live_dashboard._OFFICIAL_LANE_JS)
        # Bind the constants to the page actually served.
        panel = live_dashboard._panel_html()
        self.assertIn(live_dashboard._LIVE_LANE_JS, panel)
        self.assertIn(live_dashboard._OFFICIAL_LANE_JS, panel)
        # Enumerated live-lane vocabulary is present.
        self.assertIn("AT TRIGGER (preview &mdash; awaiting close)",
                      live_dashboard._LIVE_LANE_JS)
        self.assertIn("LIVE DATA UNAVAILABLE", live_dashboard._LIVE_LANE_JS)
        # The "(prior official report)" OI wording comes from the adapter's
        # oi_label (which exists only when the figure does); the JS renders
        # that label rather than composing its own -- see
        # JsAdapterContractTests.test_oi_label_never_dangles_in_js.
        self.assertIn("OI unknown", live_dashboard._LIVE_LANE_JS)

    def test_poll_seconds_substituted(self):
        panel = live_dashboard._panel_html()
        self.assertNotIn("__POLL_SECONDS__", panel)
        self.assertIn(f"var pollSeconds = {config.LIVE_POLL_SECONDS};", panel)

    def test_no_module_level_live_quotes_import(self):
        # live_quotes may not exist yet; the module must import without it.
        src = inspect.getsource(live_dashboard)
        for line in src.splitlines():
            if line.startswith(("import ", "from ")):  # top level only
                self.assertNotIn("live_quotes", line)


class JsAdapterContractTests(unittest.TestCase):
    """The live-lane JS renders fields from live_quotes payload rows. The two
    modules were built independently against a shared contract; this test
    pins them together so a field rename on either side fails here instead
    of silently rendering '?' in the browser (regression: spot_ts_utc vs
    spot_ts, and leaps-level vs row-level OI)."""

    # Keys the SERVER layer adds (LiveCache/refresh paths), not the adapter.
    _SERVER_ADDED = {"last_good_utc", "note", "status"}

    def test_every_js_row_field_exists_in_adapter_payload(self):
        import re

        from options_researcher import live_quotes

        row = live_quotes.build_symbol_preview(
            "VST", spot=158.0, spot_source="stock_snapshot_quote",
            spot_ts="2026-07-16T15:00:00+00:00", trigger_level=160.0,
            atm_iv=0.5, iv_history=[0.4] * 200,
            leaps_row=None, oi=250.0, oi_asof="2026-07-16",
            now="2026-07-16T15:00:00+00:00")
        js = live_dashboard._LIVE_LANE_JS
        s_fields = set(re.findall(r"\bs\.([a-z_]+)", js)) - self._SERVER_ADDED
        missing = s_fields - set(row)
        self.assertFalse(
            missing, f"live-lane JS reads fields the adapter never emits: "
                     f"{sorted(missing)}")
        # leaps sub-fields, against a leaps dict shaped like the adapter's.
        lp_fields = set(re.findall(r"\blp\.([a-z_]+)", js))
        adapter_leaps_keys = {"expiration", "strike", "delta", "bid", "ask"}
        self.assertFalse(
            lp_fields - adapter_leaps_keys,
            f"live-lane JS reads leaps fields the adapter never emits: "
            f"{sorted(lp_fields - adapter_leaps_keys)}")

    def test_oi_label_never_dangles_in_js(self):
        # The OI as-of wording must come from the adapter's oi_label (which
        # exists only when the figure does) -- the JS must not build its own
        # "OI as of" string that could render without a figure.
        self.assertNotIn("OI as of", live_dashboard._LIVE_LANE_JS)
        self.assertIn("oi_label", live_dashboard._LIVE_LANE_JS)


class JsonSafeTests(unittest.TestCase):
    def test_non_finite_floats_become_null(self):
        obj = {"a": float("nan"), "b": [1.0, float("inf")],
               "c": {"d": float("-inf"), "e": "x"}, "f": 2}
        safe = live_dashboard._json_safe(obj)
        self.assertIsNone(safe["a"])
        self.assertEqual(safe["b"], [1.0, None])
        self.assertIsNone(safe["c"]["d"])
        self.assertEqual(safe["c"]["e"], "x")
        self.assertEqual(safe["f"], 2)
        json.dumps(safe, allow_nan=False)  # must not raise


class LiveDashboardServerTests(unittest.TestCase):
    def setUp(self):
        self._refresh_lock = threading.Lock()
        self.refresh_calls = 0

        def refresh():
            with self._refresh_lock:
                self.refresh_calls += 1
            return _live_payload()

        self.server = live_dashboard.LiveDashboardServer(
            refresh_fn=refresh, port=0,  # ephemeral loopback port
            html_provider=lambda: "<html><body><p>STATIC-STUB</p></body></html>")
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())

    def _get(self, path: str) -> tuple[int, str, bytes]:
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port,
                                          timeout=5)
        try:
            conn.request("GET", path)
            resp = conn.getresponse()
            return resp.status, resp.getheader("Content-Type") or "", resp.read()
        finally:
            conn.close()

    def test_root_serves_injected_html(self):
        status, ctype, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        text = body.decode("utf-8")
        self.assertIn("STATIC-STUB", text)
        self.assertIn('id="live-panel"', text)
        self.assertLess(text.index('id="live-panel"'), text.rindex("</body>"))

    def test_root_regenerates_html_from_current_local_state(self):
        rendered = ["<html><body>first</body></html>"]
        server = live_dashboard.LiveDashboardServer(
            refresh_fn=_live_payload,
            port=0,
            html_provider=lambda: rendered[-1],
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            rendered.append("<html><body>second</body></html>")
            conn = http.client.HTTPConnection(
                "127.0.0.1", server.port, timeout=5
            )
            try:
                conn.request("GET", "/")
                body = conn.getresponse().read().decode("utf-8")
            finally:
                conn.close()
            self.assertIn("second", body)
            self.assertNotIn(">first<", body)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_root_refresh_failure_serves_last_good_html(self):
        calls = [0]

        def provider():
            calls[0] += 1
            if calls[0] > 1:
                raise OSError("local cache unavailable")
            return "<html><body>last-good</body></html>"

        server = live_dashboard.LiveDashboardServer(
            refresh_fn=_live_payload, port=0, html_provider=provider
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            conn = http.client.HTTPConnection(
                "127.0.0.1", server.port, timeout=5
            )
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    conn.request("GET", "/")
                    body = conn.getresponse().read().decode("utf-8")
            finally:
                conn.close()
            self.assertIn("last-good", body)
        finally:
            server.shutdown()
            thread.join(timeout=5)

    def test_live_json_carries_both_lanes(self):
        with mock.patch("options_researcher.entry_watch._gather",
                        return_value=list(_OFFICIAL_ROWS)):
            status, ctype, body = self._get("/live.json")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        payload = json.loads(body)
        # Official rows verbatim: one WAIT, one FIRE, untouched.
        self.assertEqual(payload["official"], _OFFICIAL_ROWS)
        verdicts = {r["symbol"]: r["verdict"] for r in payload["official"]}
        self.assertEqual(verdicts, {"VST": "WAIT", "AMZN": "FIRE"})
        self.assertEqual(payload["live"]["symbols"]["VST"]["status"], "ok")
        self.assertEqual(payload["poll_seconds"], config.LIVE_POLL_SECONDS)
        self.assertNotIn("official_error", payload)

    def test_nan_iv_rank_in_official_rows_yields_valid_json(self):
        # entry_watch iv_rank is legitimately NaN below 126 obs; the JSON
        # must stay parseable with null there -- one unknown field must not
        # blank the whole panel (regression: json.dumps emits literal NaN).
        rows = [dict(_OFFICIAL_ROWS[0], iv_rank=float("nan"))]
        with mock.patch("options_researcher.entry_watch._gather",
                        return_value=rows):
            status, _, body = self._get("/live.json")
        self.assertEqual(status, 200)
        payload = json.loads(body)  # raises on literal NaN
        self.assertIsNone(payload["official"][0]["iv_rank"])

    def test_official_failure_degrades_not_500(self):
        with mock.patch("options_researcher.entry_watch._gather",
                        side_effect=OSError("no cache")):
            with contextlib.redirect_stderr(io.StringIO()):
                status, _, body = self._get("/live.json")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["official"], [])
        self.assertIn("no cache", payload["official_error"])

    def test_unknown_path_404(self):
        status, _, _ = self._get("/nope")
        self.assertEqual(status, 404)
        status, _, _ = self._get("/live.json/extra")
        self.assertEqual(status, 404)

    def test_concurrent_live_json_single_refresh(self):
        errors: list[Exception] = []

        def worker():
            try:
                status, _, body = self._get("/live.json")
                assert status == 200
                json.loads(body)
            except Exception as e:  # surfaced after join
                errors.append(e)

        with mock.patch("options_researcher.entry_watch._gather",
                        return_value=[]):
            threads = [threading.Thread(target=worker) for _ in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10)
        self.assertEqual(errors, [])
        # All six requests landed inside one TTL window: exactly one refresh.
        self.assertEqual(self.refresh_calls, 1)


class MainTests(unittest.TestCase):
    def test_without_serve_prints_usage_and_exits(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = live_dashboard.main([])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("options_researcher.dashboard", out)
        self.assertIn("--serve", out)

    def test_no_open_serves_without_opening_browser(self):
        server = mock.Mock()
        server.port = 8765
        server.serve_forever.side_effect = KeyboardInterrupt
        with (
            mock.patch(
                "options_researcher.live_quotes.load_latest_probe",
                return_value={},
            ),
            mock.patch(
                "options_researcher.live_quotes.probe_ok",
                return_value=(False, "not entitled"),
            ),
            mock.patch.object(
                live_dashboard, "LiveDashboardServer", return_value=server
            ),
            mock.patch.object(live_dashboard.webbrowser, "open") as open_browser,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            rc = live_dashboard.main(
                ["--serve", "--port", "8765", "--no-open"]
            )
        self.assertEqual(rc, 0)
        open_browser.assert_not_called()
        server.shutdown.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()

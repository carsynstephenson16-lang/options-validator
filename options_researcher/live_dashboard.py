"""options_researcher/live_dashboard.py -- localhost live-preview dashboard server.

Read-only, localhost-only, preview-only. Serves the existing mission-control
dashboard (dashboard.assemble()/render(), regenerated once at startup) with an
injected LIVE panel whose inline script polls /live.json. Two lanes, never
merged:

- OFFICIAL H5 STATUS (completed sessions): rows verbatim from
  entry_watch._gather() on completed-session closes. This is the ONLY lane
  that may say FIRE -- the pre-registered rule (H5_ENTRY_TRIGGER_PREREG /
  amendment v2) stays with entry_watch, untouched.
- LIVE PREVIEW -- awaiting close: intraday spot/gate preview. It can NEVER
  display FIRE or any FIRE-equivalent green state; at-trigger renders as
  "AT TRIGGER (preview -- awaiting close)" in amber.

This module writes nothing (no positions, no ledger, no reports), places no
orders, and binds to 127.0.0.1 only. Provider calls happen only through
options_researcher.live_quotes.refresh(), which is itself session- and
probe-gated; live_quotes is imported lazily inside functions so this module
imports (and its offline tests run) without it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import config


# ---------------------------------------------------------------------------
# LiveCache -- TTL + single-flight cache in front of live_quotes.refresh()
# ---------------------------------------------------------------------------
class LiveCache:
    """In-memory payload cache: at most ONE refresh in flight (throttles paid
    provider calls); concurrent callers get the stale payload immediately
    instead of blocking (they only block when no payload exists yet).

    refresh_fn exceptions never propagate: the retained payload is served
    with every symbol forced to status "unavailable" (keeping only that
    symbol's last_good_utc -- no stale spot/gates/armed survive) plus a
    top-level "refresh_error". A symbol is only ever served as "ok" straight
    from the most recent successful refresh.
    """

    def __init__(self, refresh_fn, ttl_seconds: float | None = None,
                 clock=time.monotonic):
        self._refresh_fn = refresh_fn
        self._ttl = (config.LIVE_CACHE_TTL_SECONDS if ttl_seconds is None
                     else ttl_seconds)
        self._clock = clock
        self._lock = threading.Lock()
        self._payload: dict | None = None
        self._fetched_at: float | None = None
        self._last_good: dict[str, str] = {}  # symbol -> generated_at_utc

    def _fresh(self) -> bool:
        return (self._payload is not None and self._fetched_at is not None
                and (self._clock() - self._fetched_at) < self._ttl)

    def get(self) -> dict:
        if self._fresh():
            return self._payload  # type: ignore[return-value]
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            stale = self._payload
            if stale is not None:
                return stale  # serve stale rather than pile up on the lock
            self._lock.acquire()  # first fill: block until the refresher is done
        try:
            if self._fresh():  # another thread refreshed while we waited
                return self._payload  # type: ignore[return-value]
            return self._refresh_locked()
        finally:
            self._lock.release()

    def _refresh_locked(self) -> dict:
        try:
            fresh = self._refresh_fn()
        except Exception as e:  # never propagate to the HTTP layer
            payload = dict(self._payload) if self._payload else {}
            unavailable: dict[str, dict] = {}
            for sym in (payload.get("symbols") or {}):
                row: dict = {"status": "unavailable"}
                if sym in self._last_good:
                    row["last_good_utc"] = self._last_good[sym]
                unavailable[sym] = row
            payload["symbols"] = unavailable
            payload["refresh_error"] = f"{type(e).__name__}: {e}"
            self._payload = payload
            self._fetched_at = self._clock()  # throttle retries too
            return payload
        payload = dict(fresh)
        generated = payload.get("generated_at_utc")
        symbols: dict[str, dict] = {}
        for sym, row in (payload.get("symbols") or {}).items():
            row = dict(row)
            if row.get("status") == "ok":
                if generated is not None:
                    self._last_good[sym] = generated
            elif sym in self._last_good:
                row.setdefault("last_good_utc", self._last_good[sym])
            symbols[sym] = row
        payload["symbols"] = symbols
        self._payload = payload
        self._fetched_at = self._clock()
        return payload


# ---------------------------------------------------------------------------
# Payload assembly
# ---------------------------------------------------------------------------
def _gather_official() -> tuple[list[dict], str | None]:
    """entry_watch._gather() wrapped tolerantly (mirrors dashboard.py's
    trigger fallback): the live server must keep answering /live.json even
    when the official lane can't be computed, so ANY failure degrades to an
    empty lane plus an explicit "official_error" string."""
    try:
        from options_researcher import entry_watch
        return list(entry_watch._gather()), None
    except Exception as e:
        print(f"WARN entry-watch unavailable, official lane empty: {e}",
              file=sys.stderr)
        return [], f"{type(e).__name__}: {e}"


def _json_safe(obj):
    """Recursively replace non-finite floats (NaN/inf) with None. Official
    rows legitimately carry NaN (e.g. entry_watch iv_rank before 126 obs);
    json.dumps would emit literal NaN -- invalid JSON that kills the whole
    browser panel. One unknown field must degrade to null, not take down
    the display."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def build_payload(live: dict, official_rows: list[dict] | None = None) -> dict:
    """Merge the live-preview payload with the OFFICIAL entry-watch rows.
    When official_rows is None, gather them fresh (offline/cheap) with the
    tolerant wrapper; on failure the payload carries "official_error"."""
    payload: dict = {"live": live, "poll_seconds": config.LIVE_POLL_SECONDS}
    if official_rows is None:
        official_rows, err = _gather_official()
        if err is not None:
            payload["official_error"] = err
    payload["official"] = official_rows
    return payload


# ---------------------------------------------------------------------------
# HTML augmentation -- LIVE panel + inline polling script.
#
# The script is assembled from two named constants so a unit test can assert
# the live-lane renderer contains NO "FIRE" literal: _OFFICIAL_LANE_JS is the
# only place the word FIRE may appear; _LIVE_LANE_JS renders exclusively from
# enumerated values (MET/UNMET/UNKNOWN, status badges, "AT TRIGGER (preview
# -- awaiting close)") so there is no code path that can write FIRE into the
# live panel.
# ---------------------------------------------------------------------------
_OFFICIAL_LANE_JS = """
  // OFFICIAL lane -- the ONLY function allowed to render the word FIRE.
  function renderOfficialLane(payload) {
    var rows = payload.official || [];
    var out = "";
    if (payload.official_error) {
      out += '<div class="lv-err">official lane error: '
        + esc(payload.official_error) + "</div>";
    }
    if (!rows.length && !payload.official_error) {
      out = '<div class="lv-dim">no official rows</div>';
    }
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var color = r.verdict === "FIRE" ? "#ff5470" : "#caa53d";
      out += '<div class="lv-row"><span class="lv-sym">' + esc(r.symbol)
        + '</span> <span style="color:' + color + ';font-weight:bold">'
        + esc(r.verdict) + "</span> close $" + esc(r.close)
        + " (close as of " + esc(r.close_asof) + ")";
      if (r.unmet && r.unmet.length) {
        out += ' <span class="lv-dim">waiting on: '
          + esc(r.unmet.join("; ")) + "</span>";
      }
      out += "</div>";
    }
    document.getElementById("lv-official-lane").innerHTML = out;
  }
"""

_LIVE_LANE_JS = """
  // LIVE preview lane -- renders ONLY enumerated states; no fire-equivalent
  // words or green states may appear here, ever.
  function gateLabel(v) {
    if (v === "MET") {
      return '<span style="color:#caa53d;font-weight:bold">MET</span>';
    }
    if (v === "UNMET") { return '<span style="color:#6b7280">UNMET</span>'; }
    return '<span style="color:#6b7280">UNKNOWN ?</span>';
  }
  function leapsLine(s) {
    var lp = s.leaps;
    var parts = [];
    if (lp.expiration != null) { parts.push("exp " + esc(lp.expiration)); }
    if (lp.strike != null) { parts.push("strike " + esc(lp.strike)); }
    if (lp.delta != null) { parts.push("delta " + esc(lp.delta)); }
    if (lp.bid != null && lp.ask != null) {
      parts.push("bid/ask " + esc(lp.bid) + "/" + esc(lp.ask));
    }
    // OI + its as-of label live at ROW level; the adapter guarantees
    // oi_label exists only when the figure does. No figure => "OI unknown",
    // never a dangling as-of label.
    var oi = (s.open_interest != null && s.oi_label != null)
      ? "OI " + esc(s.open_interest) + " (" + esc(s.oi_label) + ")"
      : "OI unknown";
    return '<div class="lv-sub">LEAPS candidate: '
      + (parts.join(", ") || "(no details)")
      + " &mdash; " + oi + "</div>";
  }
  function renderLiveLane(payload) {
    var live = payload.live || {};
    var banner = document.getElementById("lv-session-banner");
    banner.innerHTML = live.session_state === "closed"
      ? '<div class="lv-banner">market closed &mdash; live off</div>' : "";
    var out = "";
    if (live.refresh_error) {
      out += '<div class="lv-unavail">LIVE DATA UNAVAILABLE (refresh error: '
        + esc(live.refresh_error) + ")</div>";
    }
    var syms = live.symbols || {};
    var names = Object.keys(syms).sort();
    if (!names.length && !live.refresh_error) {
      out += '<div class="lv-dim">no live symbols</div>';
    }
    for (var i = 0; i < names.length; i++) {
      var name = names[i];
      var s = syms[name] || {};
      if (s.status === "unavailable") {
        out += '<div class="lv-row"><span class="lv-sym">' + esc(name)
          + '</span> <span class="lv-unavail">LIVE DATA UNAVAILABLE</span>'
          + (s.last_good_utc
             ? ' <span class="lv-dim">last good ' + esc(s.last_good_utc)
               + "</span>" : "")
          + "</div>";
        continue;
      }
      if (s.status === "off") {
        out += '<div class="lv-row lv-dim"><span class="lv-sym">' + esc(name)
          + "</span> live off"
          + (s.note ? " &mdash; " + esc(s.note) : "") + "</div>";
        continue;
      }
      out += '<div class="lv-row"><span class="lv-sym">' + esc(name)
        + "</span> spot " + esc(s.spot == null ? "?" : s.spot)
        + ' <span class="lv-dim">(' + esc(s.spot_source || "?") + " "
        + esc(s.spot_ts || "?") + ")</span>";
      if (s.trigger != null) {
        var g = s.gates || {};
        out += '<div class="lv-sub">trigger ' + esc(s.trigger)
          + " &nbsp;price " + gateLabel(g.price)
          + " &nbsp;ivr " + gateLabel(g.ivr)
          + " &nbsp;liquidity " + gateLabel(g.liquidity) + "</div>";
        if (s.armed === true) {
          out += '<div class="lv-sub" style="color:#caa53d;font-weight:bold">'
            + "AT TRIGGER (preview &mdash; awaiting close)</div>";
        }
      }
      if (s.leaps) { out += leapsLine(s); }
      if (s.note) {
        out += '<div class="lv-sub lv-dim">' + esc(s.note) + "</div>";
      }
      out += "</div>";
    }
    document.getElementById("lv-live-lane").innerHTML = out;
  }
  function liveLaneUnavailable(ts) {
    // fetch error: clear old rows -- stale numbers must never stand.
    document.getElementById("lv-live-lane").innerHTML =
      '<div class="lv-unavail">LIVE DATA UNAVAILABLE (poll failed '
      + esc(ts) + ")</div>";
  }
"""

_PANEL_TEMPLATE = """
<div id="live-panel">
  <style>
    #live-panel { background: #141a2a; border: 1px solid #2a3350;
      border-radius: 12px; padding: 16px; margin: 20px 24px;
      font-family: ui-monospace, Menlo, monospace; color: #e6e9f2; }
    #live-panel h2 { letter-spacing: 0.08em; margin-top: 0; }
    #live-panel h3 { color: #9aa4c0; letter-spacing: 0.06em; }
    #live-panel .lv-lane { background: #0f1422; border: 1px solid #2a3350;
      border-radius: 10px; padding: 10px 14px; margin-bottom: 14px; }
    #live-panel .lv-row { padding: 4px 0;
      border-bottom: 1px solid #1b2338; font-size: 0.9em; }
    #live-panel .lv-sub { margin-left: 16px; font-size: 0.85em; }
    #live-panel .lv-sym { font-weight: bold; }
    #live-panel .lv-dim { color: #6b7280; }
    #live-panel .lv-err { color: #ff5470; }
    #live-panel .lv-unavail { color: #ff5470; font-weight: bold; }
    #live-panel .lv-banner { background: #3d1620; color: #ff5470;
      font-weight: bold; border-radius: 8px; padding: 8px 12px;
      margin-bottom: 10px; }
  </style>
  <h2>LIVE PANEL</h2>
  <div id="lv-session-banner"></div>
  <div class="lv-lane">
    <h3>OFFICIAL H5 STATUS (completed sessions)</h3>
    <div id="lv-official-lane" class="lv-dim">loading&hellip;</div>
  </div>
  <div class="lv-lane">
    <h3>LIVE PREVIEW &mdash; awaiting close</h3>
    <div id="lv-live-lane" class="lv-dim">loading&hellip;</div>
  </div>
</div>
<script>
(function () {
  "use strict";
  var pollSeconds = __POLL_SECONDS__;
  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;",
              '"': "&quot;", "'": "&#39;"}[c];
    });
  }
__OFFICIAL_LANE_JS__
__LIVE_LANE_JS__
  function schedule() { setTimeout(poll, pollSeconds * 1000); }
  function poll() {
    fetch("/live.json", {cache: "no-store"}).then(function (resp) {
      if (!resp.ok) { throw new Error("HTTP " + resp.status); }
      return resp.json();
    }).then(function (payload) {
      if (payload.poll_seconds) { pollSeconds = payload.poll_seconds; }
      renderOfficialLane(payload);
      renderLiveLane(payload);
      schedule();
    }).catch(function () {
      liveLaneUnavailable(new Date().toTimeString().slice(0, 8));
      schedule();
    });
  }
  poll();
})();
</script>
"""


def _panel_html() -> str:
    """The injected block: panel div + inline style + inline script. Fully
    self-contained -- no external assets or absolute URLs."""
    return (_PANEL_TEMPLATE
            .replace("__OFFICIAL_LANE_JS__", _OFFICIAL_LANE_JS)
            .replace("__LIVE_LANE_JS__", _LIVE_LANE_JS)
            .replace("__POLL_SECONDS__", str(config.LIVE_POLL_SECONDS)))


def inject_live_panel(html: str) -> str:
    """Insert the LIVE panel immediately before </body>. The static
    dashboard HTML itself is not modified in any other way; if no </body>
    exists the panel is appended."""
    panel = _panel_html()
    idx = html.rfind("</body>")
    if idx == -1:
        return html + panel
    return html[:idx] + panel + html[idx:]


# ---------------------------------------------------------------------------
# HTTP server -- 127.0.0.1 only; GET / and GET /live.json, nothing else.
# ---------------------------------------------------------------------------
def _default_html() -> str:
    from options_researcher import dashboard
    return dashboard.render(dashboard.assemble())


class _HTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    # socketserver's default listen backlog is 5; a burst of parallel
    # connections (multiple tabs, browser refresh storms) overflows it and
    # macOS RSTs the extras. Localhost-only, so a deeper queue is free.
    request_queue_size = 32
    owner: "LiveDashboardServer | None" = None


class _Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        owner = self.server.owner  # type: ignore[attr-defined]
        path = self.path.split("?", 1)[0]
        if path == "/":
            self._send(200, "text/html; charset=utf-8", owner.html.encode("utf-8"))
        elif path == "/live.json":
            # allow_nan=False: belt-and-braces -- live_payload() already
            # sanitizes, and a NaN slipping through must fail loudly here
            # rather than emit invalid JSON.
            body = json.dumps(owner.live_payload(), allow_nan=False).encode("utf-8")
            self._send(200, "application/json", body)
        else:
            self._send(404, "text/plain; charset=utf-8", b"not found")

    def log_message(self, format: str, *args) -> None:  # quiet server
        return


class LiveDashboardServer:
    """ThreadingHTTPServer bound to 127.0.0.1 (never a public interface).

    GET /          -> static dashboard HTML (regenerated once at startup)
                      with the LIVE panel injected.
    GET /live.json -> build_payload(LiveCache.get()) plus fresh official rows.
    Anything else  -> 404. No other methods.
    """

    def __init__(self, refresh_fn, port: int | None = None, html_provider=None):
        self._cache = LiveCache(refresh_fn)
        provider = html_provider if html_provider is not None else _default_html
        self.html = inject_live_panel(provider())
        bind_port = config.LIVE_DASH_PORT if port is None else port
        self._httpd = _HTTPServer(("127.0.0.1", bind_port), _Handler)
        self._httpd.owner = self

    @property
    def port(self) -> int:
        return self._httpd.server_address[1]

    def live_payload(self) -> dict:
        # Official rows are offline/cheap -- recomputed per request, tolerant.
        # _json_safe: NaN/inf degrade to null so one unknown field can never
        # invalidate the JSON and blank the whole panel.
        return _json_safe(build_payload(self._cache.get()))

    def serve_forever(self) -> None:
        self._httpd.serve_forever()

    def shutdown(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
_USAGE = """live_dashboard serves; it does not write files.
Run with --serve [--port N] to start the localhost live-preview server.
For the static generators use:
  uv run python -m options_researcher.dashboard
  uv run python -m options_researcher.attractiveness_dashboard"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="options_researcher.live_dashboard",
        description="Read-only localhost live-preview dashboard server.")
    parser.add_argument("--serve", action="store_true",
                        help="start the 127.0.0.1 HTTP server")
    parser.add_argument("--port", type=int, default=config.LIVE_DASH_PORT,
                        help=f"port (default {config.LIVE_DASH_PORT})")
    args = parser.parse_args(argv)
    if not args.serve:
        print(_USAGE)
        return 0

    from datetime import datetime, timezone

    from options_researcher import live_quotes

    probe = live_quotes.load_latest_probe()
    ok, reason = live_quotes.probe_ok(probe, datetime.now(timezone.utc))
    state = "ON" if ok else "OFF (official lane only)"
    print(f"live lane {state}: {reason}")

    server = LiveDashboardServer(refresh_fn=lambda: live_quotes.refresh(),
                                 port=args.port)
    url = f"http://127.0.0.1:{server.port}/"
    print(f"serving read-only dashboard at {url} (Ctrl-C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down -- nothing was written, no orders were placed")
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""tests/test_intraday_capture.py -- offline tests for the intraday
option-board capture (recorder).

No network, no ThetaData client, no .env: every fetch path is exercised via
an injected FakeClient, and receipts/chains are written to tempdirs, never
the repo's real reports/intraday_capture or .cache/intraday.
"""
import glob
import inspect
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd
from authlib.integrations.base_client.errors import OAuthError

import config
from options_researcher import intraday_capture as ic
from options_researcher import live_quotes as lq
from options_researcher.black_scholes import bs_price as _bs_price
from options_researcher.chains import third_friday
from research.hashing import config_hash

REPO_ROOT = Path(__file__).resolve().parents[1]

NY = ZoneInfo("America/New_York")
TODAY = date(2026, 7, 15)                      # a Wednesday
NOW_NY = datetime(2026, 7, 15, 11, 0, tzinfo=NY)  # exactly the "midmorning" tag
SATURDAY = datetime(2026, 7, 18, 12, 0, tzinfo=NY)
MONTHLY_EXP = third_friday(2026, 8)             # 37 DTE from TODAY (in 15-60)
UNIVERSE = ["VST", "CEG"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _probe(now_utc, **over):
    endpoints = {
        "stock_snapshot_quote": {"ok": True, "columns": ["symbol", "bid", "ask"],
                                 "error": None},
        "option_list_expirations": {"ok": True, "columns": ["expiration"],
                                    "error": None},
        "option_snapshot_quote": {"ok": True,
                                  "columns": ["expiration", "strike", "right",
                                              "bid", "ask"], "error": None},
        "option_snapshot_greeks_all": {"ok": True,
                                       "columns": ["expiration", "strike",
                                                   "right", "bid", "ask",
                                                   "delta", "implied_vol"],
                                       "error": None},
        "option_snapshot_open_interest": {"ok": True,
                                          "columns": ["expiration", "strike",
                                                      "right", "open_interest"],
                                          "error": None},
    }
    provider = lq._configured_provider()
    p = {"probed_at_utc": now_utc.isoformat(), "ny_date": TODAY.isoformat(),
         "provider": provider,
         "provider_version": lq._installed_provider_version(provider),
         "stock_entitled": True, "probe_symbol": lq.PROBE_SYMBOL,
         "monthly_expiration": MONTHLY_EXP.isoformat(), "endpoints": endpoints}
    p.update(over)
    return p


def _probe_realistic_entitlement(now_utc, **over):
    """Mirrors the real 2026-07-24 09:31 production probe (reports/
    live_probe/2026-07-24.json, primary checkout): stock_snapshot_quote AND
    option_snapshot_greeks_all both PERMISSION_DENIED (this account is on a
    tier without a stock add-on and without the PROFESSIONAL option tier);
    expirations, option_snapshot_quote, and open_interest all ok."""
    return _probe(
        now_utc,
        stock_entitled=False,
        endpoints={
            "stock_snapshot_quote": {
                "ok": False, "columns": None,
                "error": "PERMISSION_DENIED: FREE subscription does not "
                        "include stock quotes"},
            "option_list_expirations": {"ok": True, "columns": ["expiration"],
                                        "error": None},
            "option_snapshot_quote": {
                "ok": True,
                "columns": ["expiration", "strike", "right", "bid", "ask"],
                "error": None},
            "option_snapshot_greeks_all": {
                "ok": False, "columns": None,
                "error": "PERMISSION_DENIED: requires a PROFESSIONAL "
                        "option subscription"},
            "option_snapshot_open_interest": {
                "ok": True,
                "columns": ["expiration", "strike", "right", "open_interest"],
                "error": None},
        },
        **over)


class FakeClient:
    """Records every call; raises where a test asks it to."""

    def __init__(self, spots=None, stock_ts=None, greeks_raises=(),
                 oi_raises=(), expirations_raises=(), quote_raises=(),
                 stock_raises=False):
        self.spots = spots or {}
        self.stock_ts = stock_ts
        self.greeks_raises = set(greeks_raises)
        self.oi_raises = set(oi_raises)
        self.expirations_raises = set(expirations_raises)
        self.quote_raises = set(quote_raises)
        self.stock_raises = stock_raises
        self.calls = {"stock": 0, "expirations": [], "quote": [],
                      "greeks": [], "oi": []}

    def stock_snapshot_quote(self, symbols, **kw):
        self.calls["stock"] += 1
        if self.stock_raises:
            raise RuntimeError(
                "PERMISSION_DENIED: FREE subscription does not include "
                "stock quotes")
        rows = []
        for s in symbols:
            if s not in self.spots:
                continue
            row = {"symbol": s, "bid": self.spots[s] - 0.05,
                   "ask": self.spots[s] + 0.05}
            if self.stock_ts is not None:
                row["timestamp"] = self.stock_ts
            rows.append(row)
        return pd.DataFrame(rows)

    def option_list_expirations(self, symbol):
        self.calls["expirations"].append(symbol)
        if symbol in self.expirations_raises:
            raise RuntimeError("boom expirations")
        return pd.DataFrame({"expiration": [MONTHLY_EXP.isoformat()]})

    def option_snapshot_quote(self, symbol, expiration=None, **kw):
        """ENTITLED: bid/ask only, no greeks. The entitled core (spread%,
        OI-based admission, put-call-parity spot fallback) is built entirely
        from this + option_snapshot_open_interest."""
        self.calls["quote"].append((symbol, str(expiration)))
        if symbol in self.quote_raises:
            raise RuntimeError("boom quote")
        exp = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration)
        return pd.DataFrame([
            {"expiration": exp, "strike": 150.0, "right": "P", "bid": 2.0,
             "ask": 2.1},
            {"expiration": exp, "strike": 150.0, "right": "C", "bid": 2.2,
             "ask": 2.4},
            # wide spread -- must fail the spread gate regardless of OI
            {"expiration": exp, "strike": 200.0, "right": "C", "bid": 0.05,
             "ask": 0.50},
        ])

    def option_snapshot_greeks_all(self, symbol, expiration=None, **kw):
        """This account is on STANDARD as of 2026-07-24: PERMISSION_DENIED
        is the REAL failure mode when greeks_raises requests it, mirroring
        the production incident, not a synthetic exception type."""
        self.calls["greeks"].append((symbol, str(expiration)))
        if symbol in self.greeks_raises:
            raise RuntimeError(
                "PERMISSION_DENIED: option greeks requires a PROFESSIONAL "
                "subscription")
        exp = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration)
        return pd.DataFrame([
            {"expiration": exp, "strike": 150.0, "right": "P", "bid": 2.0,
             "ask": 2.1, "delta": -0.50, "implied_vol": 0.30},
            {"expiration": exp, "strike": 150.0, "right": "C", "bid": 2.2,
             "ask": 2.4, "delta": 0.55, "implied_vol": 0.28},
        ])

    def option_snapshot_open_interest(self, symbol, expiration=None, **kw):
        self.calls["oi"].append((symbol, str(expiration)))
        if symbol in self.oi_raises:
            raise RuntimeError("boom oi")
        exp = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration)
        return pd.DataFrame([
            {"expiration": exp, "strike": 150.0, "right": "P", "open_interest": 500},
            {"expiration": exp, "strike": 150.0, "right": "C", "open_interest": 400},
            # below config.MIN_OPEN_INTEREST
            {"expiration": exp, "strike": 200.0, "right": "C", "open_interest": 10},
        ])


class ExpiredRefreshTokenClient:
    """Provider double whose every live call reports the exact Authlib error."""

    @staticmethod
    def _expired(*_args, **_kwargs):
        raise OAuthError(
            "invalid_grant",
            "Refresh token is invalid, expired or revoked",
        )

    stock_snapshot_quote = _expired
    option_list_expirations = _expired
    option_snapshot_quote = _expired
    option_snapshot_greeks_all = _expired
    option_snapshot_open_interest = _expired
    regular_session_state = _expired


class ExpiredRefreshTokenAfterStockClient(ExpiredRefreshTokenClient):
    """Lets the batch succeed so the per-symbol exception path is reached."""

    @staticmethod
    def stock_snapshot_quote(symbols, **_kwargs):
        return pd.DataFrame([
            {"symbol": symbol, "bid": 100.0, "ask": 100.1}
            for symbol in symbols
        ])


class _FrozenCaptureDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW_NY if tz is None else NOW_NY.astimezone(tz)


def _tree_snapshot(root: Path) -> dict:
    if not root.exists():
        return {}
    return {str(p): p.stat().st_mtime_ns for p in sorted(root.rglob("*")) if p.is_file()}


def _tmp_dirs():
    tmp = tempfile.mkdtemp()
    return Path(tmp) / "cache", Path(tmp) / "receipts"


# ---------------------------------------------------------------------------
# Pure timing functions
# ---------------------------------------------------------------------------

class SessionTagValidationTests(unittest.TestCase):
    def test_unknown_tag_always_refuses(self):
        ok, _ = ic.validate_session_tag("bogus", NOW_NY)
        self.assertFalse(ok)
        ok_forced, _ = ic.validate_session_tag("bogus", NOW_NY, force=True)
        self.assertFalse(ok_forced)

    def test_exact_scheduled_time_ok(self):
        ok, _ = ic.validate_session_tag("midmorning", NOW_NY)  # exactly 11:00
        self.assertTrue(ok)

    def test_outside_tolerance_refuses(self):
        late = NOW_NY.replace(hour=11, minute=30)  # 30min past sched, tol=10
        ok, reason = ic.validate_session_tag("midmorning", late)
        self.assertFalse(ok)
        self.assertIn("--force", reason)

    def test_force_bypasses_timing(self):
        late = NOW_NY.replace(hour=11, minute=30)
        ok, _ = ic.validate_session_tag("midmorning", late, force=True)
        self.assertTrue(ok)

    def test_edge_of_tolerance_window(self):
        at_edge = NOW_NY.replace(minute=10)     # 11:10 -- exactly 10min (tol)
        self.assertTrue(ic.validate_session_tag("midmorning", at_edge)[0])
        past_edge = NOW_NY.replace(minute=11)   # 11:11 -- 11min, over tol
        self.assertFalse(ic.validate_session_tag("midmorning", past_edge)[0])


class NearestSessionTagTests(unittest.TestCase):
    def test_picks_closest_tag(self):
        self.assertEqual(ic.nearest_session_tag(NOW_NY), "midmorning")

    def test_none_when_far_from_every_tag(self):
        # halfway between midmorning (11:00) and midday (13:00)
        far = NOW_NY.replace(hour=12, minute=0)
        self.assertIsNone(ic.nearest_session_tag(far))

    def test_picks_open_auction_near_open(self):
        t = NOW_NY.replace(hour=9, minute=31)
        self.assertEqual(ic.nearest_session_tag(t), "open_auction")


# ---------------------------------------------------------------------------
# Storage isolation
# ---------------------------------------------------------------------------

class StorageIsolationTests(unittest.TestCase):
    def test_default_cache_dir_is_not_the_eod_chains_dir(self):
        self.assertEqual(str(ic.CACHE_DIR), config.INTRADAY_CACHE_DIR)
        self.assertNotEqual(str(ic.CACHE_DIR), ".cache/chains")
        self.assertNotIn("chains", Path(config.INTRADAY_CACHE_DIR).parts)

    def test_chain_path_never_matches_eod_glob_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            intraday_dir = root / "intraday"
            eod_dir = root / "chains"
            path = ic.chain_cache_path("VST", TODAY, NOW_NY, cache_dir=intraday_dir)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"x")
            # entry_watch._gather's exact glob pattern, rooted at the
            # separate EOD directory: it can never see our file because our
            # file was never placed there.
            matches = glob.glob(str(eod_dir / "VST_*.parquet"))
            self.assertEqual(matches, [])
            self.assertNotEqual(path.parent, eod_dir)

    def test_filename_carries_a_time_component_defense_in_depth(self):
        path = ic.chain_cache_path("VST", TODAY, NOW_NY)
        # The EOD cache key is exactly "{symbol}_{date}.parquet" (no time
        # component). Our filename always carries a "T{HHMM}" segment, so
        # even a glob pointed at our OWN directory by mistake would not
        # collide with an EOD-shaped consumer expecting date-only names.
        self.assertRegex(path.name, r"^VST_\d{4}-\d{2}-\d{2}T\d{4}\.parquet$")


# ---------------------------------------------------------------------------
# Probe auto-heal
# ---------------------------------------------------------------------------

class ProbeAutoHealTests(unittest.TestCase):
    def test_healthy_probe_is_not_touched(self):
        probe = _probe(NOW_NY.astimezone(timezone.utc))
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe), \
             mock.patch.object(lq, "run_probe") as run_probe:
            out_probe, healed, ok, _ = ic.ensure_probe_ok(
                None, NOW_NY, NOW_NY.astimezone(timezone.utc))
        run_probe.assert_not_called()
        self.assertFalse(healed)
        self.assertTrue(ok)
        self.assertEqual(out_probe, probe)

    def test_stale_probe_is_healed_in_session(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        stale = _probe(now_utc - timedelta(days=30))
        fresh = _probe(now_utc)
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe", return_value=fresh) as run_probe:
            out_probe, healed, ok, _ = ic.ensure_probe_ok(object(), NOW_NY, now_utc)
        run_probe.assert_called_once()
        self.assertTrue(healed)
        self.assertTrue(ok)
        self.assertEqual(out_probe, fresh)

    def test_missing_probe_is_healed_in_session(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        fresh = _probe(now_utc)
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: None), \
             mock.patch.object(lq, "run_probe", return_value=fresh) as run_probe:
            out_probe, healed, ok, _ = ic.ensure_probe_ok(object(), NOW_NY, now_utc)
        run_probe.assert_called_once()
        self.assertTrue(healed)
        self.assertTrue(ok)

    def test_stale_probe_outside_session_is_not_healed(self):
        sat_utc = SATURDAY.astimezone(timezone.utc)
        stale = _probe(sat_utc - timedelta(days=30))
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe") as run_probe:
            out_probe, healed, ok, _ = ic.ensure_probe_ok(object(), SATURDAY, sat_utc)
        run_probe.assert_not_called()
        self.assertFalse(healed)
        self.assertFalse(ok)

    def test_still_bad_after_heal_reports_not_ok(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        stale = _probe(now_utc - timedelta(days=30))
        still_bad = _probe(now_utc, provider_version="0.0.0-wrong")
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe", return_value=still_bad):
            out_probe, healed, ok, reason = ic.ensure_probe_ok(
                object(), NOW_NY, now_utc)
        self.assertTrue(healed)
        self.assertFalse(ok)
        self.assertIn(lq._configured_provider(), reason)


# ---------------------------------------------------------------------------
# Capture-specific probe gate (entitlement reality: this module's gate must
# differ from live_quotes.probe_ok's -- see the 2026-07-24 production
# incident: greeks denied should NOT block a quotes+OI capture)
# ---------------------------------------------------------------------------

class CaptureProbeOkTests(unittest.TestCase):
    def test_passes_when_greeks_denied_but_quotes_and_oi_ok(self):
        probe = _probe_realistic_entitlement(NOW_NY.astimezone(timezone.utc))
        ok, reason = ic.capture_probe_ok(probe, NOW_NY.astimezone(timezone.utc))
        self.assertTrue(ok, reason)

    def test_live_quotes_own_gate_would_refuse_the_same_probe(self):
        # Proves the two gates are genuinely different, not accidentally
        # identical: live_quotes.REQUIRED_PROBE_ENDPOINTS includes
        # option_snapshot_greeks_all, so ITS OWN probe_ok refuses the exact
        # probe capture_probe_ok just accepted above. live_quotes' gate is
        # untouched by this fix.
        probe = _probe_realistic_entitlement(NOW_NY.astimezone(timezone.utc))
        ok, reason = lq.probe_ok(probe, NOW_NY.astimezone(timezone.utc))
        self.assertFalse(ok)
        self.assertIn("option_snapshot_greeks_all", reason)

    def test_fails_when_the_entitled_quote_endpoint_itself_fails(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        base = _probe_realistic_entitlement(now_utc)
        broken_endpoints = dict(base["endpoints"])
        broken_endpoints["option_snapshot_quote"] = {
            "ok": False, "columns": None, "error": "boom"}
        probe = _probe(now_utc, stock_entitled=False, endpoints=broken_endpoints)
        ok, reason = ic.capture_probe_ok(probe, now_utc)
        self.assertFalse(ok)
        self.assertIn("option_snapshot_quote", reason)

    def test_fails_when_probe_missing_same_as_live_quotes(self):
        ok, _ = ic.capture_probe_ok(None, NOW_NY.astimezone(timezone.utc))
        self.assertFalse(ok)

    def test_fails_on_version_mismatch_same_as_live_quotes(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        probe = _probe_realistic_entitlement(
            now_utc, provider_version="0.0.0-wrong"
        )
        ok, reason = ic.capture_probe_ok(probe, now_utc)
        self.assertFalse(ok)
        self.assertIn(lq._configured_provider(), reason)


# ---------------------------------------------------------------------------
# Full-board capture (integration, fully offline)
# ---------------------------------------------------------------------------

class CaptureIntegrationTests(unittest.TestCase):
    def setUp(self):
        lq._reset_memos()

    def _run(self, client, *, session_tag="midmorning", now_ny=None,
             force=False, universe=UNIVERSE, probe=None):
        now_ny = now_ny or NOW_NY
        probe = probe or _probe(now_ny.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe):
            rc, receipt = ic.capture(
                session_tag, client=client, now_ny=now_ny, force=force,
                universe=universe, cache_dir=cache_dir, receipt_dir=receipt_dir)
        return rc, receipt, cache_dir, receipt_dir

    def test_full_capture_happy_path(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        rc, receipt, cache_dir, receipt_dir = self._run(client)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["names"]["VST"]["status"], "ok")
        self.assertEqual(receipt["names"]["CEG"]["status"], "ok")
        self.assertEqual(receipt["names"]["VST"]["chain_contracts_admitted"],
                         {"C": 1, "P": 1})
        self.assertEqual(receipt["names"]["VST"]["chain_contracts_total"],
                         {"C": 2, "P": 1})
        chain_path = Path(receipt["names"]["VST"]["chain_cache_path"])
        self.assertTrue(chain_path.exists())
        self.assertTrue(chain_path.is_relative_to(cache_dir))
        out = receipt_dir / NOW_NY.date().isoformat() / "midmorning.json"
        self.assertTrue(out.exists())
        self.assertIn("config_hash", receipt)
        self.assertFalse(receipt["force"])
        # Greeks are entitled in the default fixture -- no honest-gap note,
        # and ATM IV/IV-rank preview should be genuinely populated.
        self.assertIsNone(receipt["names"]["VST"]["greeks_note"])
        self.assertEqual(receipt["names"]["VST"]["atm_iv"], 0.30)
        self.assertEqual(receipt["names"]["VST"]["spot_source"], "stock_snapshot")

    def test_default_capture_is_pinned_to_canonical_h7_scope(self):
        canonical_h7 = [
            "CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO",
            "IREN", "USAR", "ET", "VST", "CEG", "MSFT", "AMZN",
        ]
        display_extras = ["NBIS", "AMAT", "CLSK"]
        probe = _probe(NOW_NY.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()

        def fake_capture_symbol(_client, symbol, _spot_row, _today, _ny_iso):
            return {"symbol": symbol, "status": "unavailable"}, None, None

        with (
            mock.patch.object(
                config,
                "ATTRACTIVENESS_UNIVERSE",
                canonical_h7 + display_extras,
            ),
            mock.patch.object(ic, "watch_universe", return_value=canonical_h7),
            mock.patch.object(
                ic,
                "ensure_probe_ok",
                return_value=(probe, False, True, "ok"),
            ),
            mock.patch.object(ic, "_stock_spots", return_value={}),
            mock.patch.object(ic, "_capture_symbol", side_effect=fake_capture_symbol),
        ):
            rc, receipt = ic.capture(
                "midmorning",
                client=object(),
                now_ny=NOW_NY,
                cache_dir=cache_dir,
                receipt_dir=receipt_dir,
            )

        self.assertEqual(rc, 0)
        self.assertIsNotNone(receipt)
        assert receipt is not None
        self.assertEqual(receipt["universe"], canonical_h7)
        self.assertTrue(set(display_extras).isdisjoint(receipt["names"]))

    def test_per_name_degradation_does_not_abort_the_board(self):
        # option_snapshot_quote is part of the entitled CORE (unlike
        # greeks) -- a failure there is a genuine per-name hard abort.
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            quote_raises={"VST"})
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["names"]["VST"]["status"], "unavailable")
        self.assertIn("boom quote", receipt["names"]["VST"]["note"])
        self.assertEqual(receipt["names"]["CEG"]["status"], "ok")

    def test_oi_failure_fails_soft_to_zero_admission_not_a_board_abort(self):
        # live_quotes._open_interest already fails soft ((None, None)) on an
        # OI fetch error -- liquidity reads as "no admission possible" for
        # that name rather than aborting the whole per-name capture. The
        # chain snapshot (bid/ask/iv/delta) is still genuinely useful even
        # without OI, so "ok" (with admitted counts at 0) is correct, not
        # "unavailable".
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0}, oi_raises={"CEG"})
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["names"]["VST"]["status"], "ok")
        self.assertEqual(receipt["names"]["CEG"]["status"], "ok")
        self.assertEqual(receipt["names"]["CEG"]["chain_contracts_admitted"],
                         {"C": 0, "P": 0})
        self.assertIsNone(receipt["names"]["CEG"]["open_interest_asof"])

    def test_spot_missing_falls_back_to_parity_and_chain_still_captured(self):
        client = FakeClient(spots={"CEG": 90.0})  # VST absent from stock batch
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        vst = receipt["names"]["VST"]
        self.assertEqual(vst["status"], "ok")  # chain still fetched
        self.assertIn("missing from batched stock snapshot", vst["spot_note"])
        # No per-symbol row means no stock bid/ask -- but the parity
        # fallback (computed from the already-fetched entitled quote chain)
        # still supplies a mid.
        self.assertIsNone(vst["spot_bid"])
        self.assertIsNone(vst["spot_ask"])
        self.assertIsNotNone(vst["spot_mid"])
        self.assertEqual(vst["spot_source"], "parity_fallback")

    def test_whole_stock_batch_failure_degrades_every_name_spot_only(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0}, stock_raises=True)
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        for sym in UNIVERSE:
            row = receipt["names"][sym]
            self.assertEqual(row["status"], "ok")  # chain independent of spot
            self.assertIn("stock snapshot batch failed", row["spot_note"])

    def test_outside_regular_session_refuses(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        rc, receipt, *_ = self._run(client, now_ny=SATURDAY)
        self.assertEqual(rc, 1)
        self.assertIsNone(receipt)
        self.assertEqual(client.calls["stock"], 0)

    def test_bad_timing_refuses_without_force(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        rc, receipt, *_ = self._run(client, session_tag="midday")  # 13:00 vs now 11:00
        self.assertEqual(rc, 1)
        self.assertIsNone(receipt)
        self.assertEqual(client.calls["stock"], 0)

    def test_bad_timing_with_force_proceeds_and_is_recorded(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        rc, receipt, *_ = self._run(client, session_tag="midday", force=True)
        self.assertEqual(rc, 0)
        self.assertTrue(receipt["force"])
        self.assertEqual(receipt["session_tag"], "midday")

    # -- Entitlement reality (2026-07-24 production incident) -------------

    def test_stock_denied_falls_back_to_parity_spot(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0}, stock_raises=True)
        probe = _probe_realistic_entitlement(NOW_NY.astimezone(timezone.utc))
        rc, receipt, *_ = self._run(client, probe=probe)
        self.assertEqual(rc, 0)
        for sym in UNIVERSE:
            row = receipt["names"][sym]
            self.assertEqual(row["status"], "ok")
            self.assertEqual(row["spot_source"], "parity_fallback")
            self.assertIsNotNone(row["spot_mid"])
            self.assertIsNone(row["spot_bid"])
            self.assertIsNone(row["spot_ask"])
            self.assertIn("PERMISSION_DENIED", row["spot_note"])
            # the entitled quotes+OI core is untouched by the spot fallback
            self.assertEqual(row["chain_contracts_admitted"], {"C": 1, "P": 1})

    def test_greeks_denied_records_honest_gap_and_core_still_works(self):
        # 2026-07-24 (IV-solver-capture): a greeks denial now attempts the
        # solver fallback before recording an honest gap -- deterministically
        # force that fallback to ALSO fail (no rate curve coverage) so this
        # test's outcome never depends on the real repo's Treasury CSV
        # content or its validity window. See SolverIvCaptureIntegrationTests
        # for the solver-SUCCESS paths.
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST", "CEG"})
        probe = _probe_realistic_entitlement(NOW_NY.astimezone(timezone.utc))
        with mock.patch.object(
                ic.data_rates, "risk_free_rate",
                side_effect=ic.data_rates.MissingRateError("no curve")):
            rc, receipt, *_ = self._run(client, probe=probe)
        self.assertEqual(rc, 0)
        for sym in UNIVERSE:
            row = receipt["names"][sym]
            self.assertEqual(row["status"], "ok")
            self.assertIsNone(row["atm_iv"])
            self.assertIsNone(row["iv_rank_preview"])
            self.assertIsNone(row["iv_source"])
            self.assertIsNone(row["iv_label"])
            self.assertIn("not entitled: option greeks endpoint requires "
                          "professional tier", row["greeks_note"])
            self.assertIn("PERMISSION_DENIED", row["greeks_note"])
            # the solver fallback's specific failure reason is recorded too
            # -- never a blanket label in place of the greeks note.
            self.assertIn("solver: no rate curve coverage", row["greeks_note"])
            # the entitled quotes+OI core is untouched by the greeks gap
            self.assertEqual(row["chain_contracts_admitted"], {"C": 1, "P": 1})
            self.assertIsNotNone(row["min_spread_pct_observed"])
            self.assertIsNotNone(row["chain_cache_path"])
            chain = pd.read_parquet(row["chain_cache_path"])
            self.assertTrue(chain["iv"].isna().all())
            self.assertTrue(chain["delta"].isna().all())

    def test_realistic_2026_07_24_production_entitlement_end_to_end(self):
        # Both denials at once, exactly as the real 09:31 run saw them:
        # stock_snapshot_quote AND option_snapshot_greeks_all both
        # PERMISSION_DENIED, expirations/quote/OI all fine. The solver
        # fallback is deterministically forced to fail too (see the test
        # above) so this stays independent of real Treasury CSV content.
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            stock_raises=True, greeks_raises={"VST", "CEG"})
        probe = _probe_realistic_entitlement(NOW_NY.astimezone(timezone.utc))
        with mock.patch.object(
                ic.data_rates, "risk_free_rate",
                side_effect=ic.data_rates.MissingRateError("no curve")):
            rc, receipt, *_ = self._run(client, probe=probe)
        self.assertEqual(rc, 0)
        covered = sum(1 for n in receipt["names"].values() if n["status"] == "ok")
        self.assertEqual(covered, len(UNIVERSE))
        for sym in UNIVERSE:
            row = receipt["names"][sym]
            self.assertEqual(row["spot_source"], "parity_fallback")
            self.assertIsNone(row["atm_iv"])
            self.assertIsNone(row["iv_source"])
            self.assertEqual(row["chain_contracts_admitted"], {"C": 1, "P": 1})
            self.assertEqual(row["chain_contracts_total"], {"C": 2, "P": 1})


class ProbeAutoHealIntegrationTests(unittest.TestCase):
    def setUp(self):
        lq._reset_memos()

    def test_capture_auto_heals_a_stale_probe(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        stale = _probe(now_utc - timedelta(days=30))
        fresh = _probe(now_utc)
        cache_dir, receipt_dir = _tmp_dirs()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe", return_value=fresh) as run_probe:
            rc, receipt = ic.capture(
                "midmorning", client=client, now_ny=NOW_NY, universe=UNIVERSE,
                cache_dir=cache_dir, receipt_dir=receipt_dir)
        run_probe.assert_called_once()
        self.assertEqual(rc, 0)
        self.assertTrue(receipt["probe_healed_this_run"])

    def test_capture_refuses_fail_closed_when_still_bad_after_heal(self):
        now_utc = NOW_NY.astimezone(timezone.utc)
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        stale = _probe(now_utc - timedelta(days=30))
        still_bad = _probe(now_utc, provider_version="wrong-version")
        cache_dir, receipt_dir = _tmp_dirs()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe", return_value=still_bad):
            rc, receipt = ic.capture(
                "midmorning", client=client, now_ny=NOW_NY, universe=UNIVERSE,
                cache_dir=cache_dir, receipt_dir=receipt_dir)
        self.assertEqual(rc, 1)
        self.assertIsNone(receipt)
        # fail-closed BEFORE touching the client at all
        self.assertEqual(client.calls["stock"], 0)
        self.assertEqual(client.calls["greeks"], [])


# ---------------------------------------------------------------------------
# Receipt immutability
# ---------------------------------------------------------------------------

class ReceiptImmutabilityTests(unittest.TestCase):
    def setUp(self):
        lq._reset_memos()

    def test_identical_rerun_is_a_benign_noop(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        probe = _probe(NOW_NY.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe), \
             mock.patch.object(ic, "config_hash", lambda: "fixedhash"):
            rc1, _ = ic.capture("midmorning", client=client, now_ny=NOW_NY,
                                universe=UNIVERSE, cache_dir=cache_dir,
                                receipt_dir=receipt_dir)
            out = receipt_dir / NOW_NY.date().isoformat() / "midmorning.json"
            first_bytes = out.read_bytes()
            rc2, _ = ic.capture("midmorning", client=client, now_ny=NOW_NY,
                                universe=UNIVERSE, cache_dir=cache_dir,
                                receipt_dir=receipt_dir)
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertEqual(out.read_bytes(), first_bytes)

    def test_conflicting_receipt_refuses(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        probe = _probe(NOW_NY.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()
        out = receipt_dir / NOW_NY.date().isoformat() / "midmorning.json"
        out.parent.mkdir(parents=True)
        out.write_text('{"not": "the same content"}')
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe):
            rc, receipt = ic.capture("midmorning", client=client, now_ny=NOW_NY,
                                     universe=UNIVERSE, cache_dir=cache_dir,
                                     receipt_dir=receipt_dir)
        self.assertEqual(rc, 2)
        self.assertEqual(out.read_text(), '{"not": "the same content"}')  # untouched


# ---------------------------------------------------------------------------
# Solver-derived ATM IV (2026-07-24, IV-solver-capture)
# ---------------------------------------------------------------------------

class SolverAtmIvTests(unittest.TestCase):
    """Direct unit tests of _solver_atm_iv: contract selection, the bounded
    delta fixed-point reselection, and every specific failure reason."""

    def setUp(self):
        self.today = date(2026, 7, 15)
        self.monthly = third_friday(2026, 8)  # 37 DTE from self.today
        rate_patcher = mock.patch.object(
            ic.data_rates, "risk_free_rate",
            return_value=SimpleNamespace(rate=0.04))
        div_patcher = mock.patch.object(
            ic.data_rates, "dividend_yield",
            return_value=SimpleNamespace(yield_rate=0.01))
        self.addCleanup(rate_patcher.stop)
        self.addCleanup(div_patcher.stop)
        rate_patcher.start()
        div_patcher.start()

    def test_reselects_to_a_neighbor_with_closer_to_050_delta(self):
        # spot=151.0: the nearest-to-spot strike (150.0, true sigma 0.20)
        # has delta -0.4266 (gap 0.0734 from 0.50); its neighbor (152.5,
        # true sigma 0.25) has delta -0.5179 (gap 0.0179) -- strictly
        # closer. Values confirmed by direct computation while writing
        # this test. The fixed-point reselection must pick the neighbor.
        spot = 151.0
        exp_iso = self.monthly.isoformat()
        rows = [
            {"expiration": exp_iso, "strike": 147.5, "right": "P",
             "bid": 1.28967453449129, "ask": 1.28967453449129},
            {"expiration": exp_iso, "strike": 150.0, "right": "P",
             "bid": 3.129947148330899, "ask": 3.129947148330899},
            {"expiration": exp_iso, "strike": 152.5, "right": "P",
             "bid": 5.340925499570034, "ask": 5.340925499570034},
        ]
        chain = pd.DataFrame(rows)
        iv, reason = ic._solver_atm_iv(chain, spot, "VST", self.monthly, self.today)
        self.assertIsNone(reason)
        self.assertAlmostEqual(iv, 0.25, places=3)

    def test_seed_wins_when_it_already_has_the_closest_delta(self):
        # ATM seed with symmetric neighbors -- the seed's own delta is
        # already closest to 0.50, so reselection must be a no-op.
        spot = 150.0
        exp_iso = self.monthly.isoformat()
        t = (self.monthly - self.today).days / 365.0
        rows = []
        for strike, sigma in ((145.0, 0.20), (150.0, 0.20), (155.0, 0.20)):
            price = _bs_price(S=spot, K=strike, t=t, r=0.04, sigma=sigma,
                              right="P", q=0.01)
            rows.append({"expiration": exp_iso, "strike": strike, "right": "P",
                        "bid": price, "ask": price})
        chain = pd.DataFrame(rows)
        iv, reason = ic._solver_atm_iv(chain, spot, "VST", self.monthly, self.today)
        self.assertIsNone(reason)
        self.assertAlmostEqual(iv, 0.20, places=3)

    def test_expired_reports_specific_reason(self):
        past = self.today - timedelta(days=400)
        iv, reason = ic._solver_atm_iv(pd.DataFrame(), 150.0, "VST", past, self.today)
        self.assertIsNone(iv)
        self.assertEqual(reason, "solver: expired")

    def test_no_rate_curve_coverage_reports_specific_reason(self):
        with mock.patch.object(
                ic.data_rates, "risk_free_rate",
                side_effect=ic.data_rates.MissingRateError("no curve")):
            iv, reason = ic._solver_atm_iv(pd.DataFrame(), 150.0, "VST",
                                           self.monthly, self.today)
        self.assertIsNone(iv)
        self.assertEqual(reason, "solver: no rate curve coverage")

    def test_no_dividend_data_reports_specific_reason(self):
        with mock.patch.object(
                ic.data_rates, "dividend_yield",
                side_effect=ic.data_rates.MissingDividendYieldError("no div")):
            iv, reason = ic._solver_atm_iv(pd.DataFrame(), 150.0, "VST",
                                           self.monthly, self.today)
        self.assertIsNone(iv)
        self.assertEqual(reason, "solver: no dividend data for VST")

    def test_no_quotes_at_selected_contract_reports_specific_reason(self):
        chain = pd.DataFrame(columns=["expiration", "strike", "right", "bid", "ask"])
        iv, reason = ic._solver_atm_iv(chain, 150.0, "VST", self.monthly, self.today)
        self.assertIsNone(iv)
        self.assertEqual(reason, "solver: no quotes at selected contract")

    def test_no_european_bs_root_reports_specific_reason(self):
        exp_iso = self.monthly.isoformat()
        # Deep ITM put priced far below its own intrinsic value: no root.
        chain = pd.DataFrame([{"expiration": exp_iso, "strike": 500.0,
                              "right": "P", "bid": 0.01, "ask": 0.01}])
        iv, reason = ic._solver_atm_iv(chain, 150.0, "VST", self.monthly, self.today)
        self.assertIsNone(iv)
        self.assertEqual(reason, "solver: no_european_bs_root")


# ---------------------------------------------------------------------------
# solver_iv_calibration_gate (2026-07-24, IV-solver-capture)
# ---------------------------------------------------------------------------

class SolverIvCalibrationGateTests(unittest.TestCase):
    def test_missing_receipt_dir_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist"
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", str(missing)):
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))

    def test_fresh_matching_passed_symbol_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                receipt = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": config_hash(),
                    "names_passed": ["VST"],
                }
                (Path(tmp) / "2026-07-24.json").write_text(json.dumps(receipt))
                self.assertTrue(ic.solver_iv_calibration_gate("VST"))
                self.assertFalse(ic.solver_iv_calibration_gate("CEG"))

    def test_stale_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                old = (datetime.now(timezone.utc)
                      - timedelta(days=config.IV_CALIBRATION_MAX_AGE_DAYS + 5))
                receipt = {
                    "run_at_utc": old.isoformat(),
                    "config_hash": config_hash(),
                    "names_passed": ["VST"],
                }
                (Path(tmp) / "2026-06-01.json").write_text(json.dumps(receipt))
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))

    def test_config_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                receipt = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": "stale-hash-from-before-a-config-change",
                    "names_passed": ["VST"],
                }
                (Path(tmp) / "2026-07-24.json").write_text(json.dumps(receipt))
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))

    def test_symbol_not_in_names_passed_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                receipt = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": config_hash(),
                    "names_passed": ["CEG"],
                }
                (Path(tmp) / "2026-07-24.json").write_text(json.dumps(receipt))
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))

    def test_malformed_receipt_fails_closed_without_raising(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                (Path(tmp) / "2026-07-24.json").write_text("{not valid json")
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))

    def test_newest_receipt_wins_when_several_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                older = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": config_hash(), "names_passed": ["VST"],
                }
                newer = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": config_hash(), "names_passed": ["CEG"],
                }
                (Path(tmp) / "2026-07-01.json").write_text(json.dumps(older))
                (Path(tmp) / "2026-07-24.json").write_text(json.dumps(newer))
                # "newer" has the later (or tied, tie-break-by-filename)
                # run_at_utc AND the lexicographically-later filename, so
                # both the pre-fix and post-fix selection rules agree here
                # -- this test alone can't distinguish them (see
                # LoadLatestCalibrationReceiptTests below for a fixture
                # where filename order and run_at_utc order actively
                # disagree, which is the real 2026-07-24 production bug).
                # 2026-07-24.json passes CEG, not VST.
                self.assertFalse(ic.solver_iv_calibration_gate("VST"))
                self.assertTrue(ic.solver_iv_calibration_gate("CEG"))


# ---------------------------------------------------------------------------
# _load_latest_calibration_receipt selection (fix for the 2026-07-24
# production incident: filename-lexicographic sort masked a real
# retrospective-mode PASS behind a same-day strict-mode all-FAIL receipt)
# ---------------------------------------------------------------------------

class LoadLatestCalibrationReceiptTests(unittest.TestCase):
    def test_both_same_day_receipts_retrospective_with_later_run_at_utc_governs(self):
        # Mirrors the real production fixture: "2026-07-24.json" (strict,
        # all-fail, run 14:54 UTC) and "2026-07-24-retrospective.json"
        # (retrospective_official, 14/15 pass, run 15:28 UTC -- LATER in
        # time but LEXICOGRAPHICALLY EARLIER as a filename, since "-"
        # sorts before "."). The parsed-run_at_utc selection must pick the
        # retrospective receipt and its names splice.
        with tempfile.TemporaryDirectory() as tmp:
            # config_hash() hashes ALL uppercase config constants, including
            # IV_CALIBRATION_RECEIPT_DIR itself -- compute it INSIDE the
            # patched config state so the gate's later re-hash matches (see
            # SolverIvCaptureIntegrationTests.test_solver_success_and_gate_
            # pass_splices_rank for the same discipline).
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                current_hash = config_hash()
                strict = {
                    "run_at_utc": "2026-07-24T14:54:20.993776+00:00",
                    "inputs_mode": None, "config_hash": current_hash,
                    "names_passed": [],
                }
                retro = {
                    "run_at_utc": "2026-07-24T15:28:17.508115+00:00",
                    "inputs_mode": "retrospective_official",
                    "config_hash": current_hash,
                    "names_passed": ["VST", "CEG"],
                }
                (Path(tmp) / "2026-07-24.json").write_text(json.dumps(strict))
                (Path(tmp) / "2026-07-24-retrospective.json").write_text(
                    json.dumps(retro))
                # Filename order alone would put the plain file last (it
                # sorts lexicographically after the "-retrospective" file),
                # which is exactly the bug: prove that's true of this
                # fixture too.
                self.assertEqual(
                    sorted(["2026-07-24.json",
                           "2026-07-24-retrospective.json"])[-1],
                    "2026-07-24.json")
                receipt, path = ic._load_latest_calibration_receipt(tmp)
                self.assertEqual(receipt["names_passed"], ["VST", "CEG"])
                self.assertEqual(path.name, "2026-07-24-retrospective.json")
                self.assertTrue(ic.solver_iv_calibration_gate("VST"))
                self.assertTrue(ic.solver_iv_calibration_gate("CEG"))

    def test_strict_only_fixture_strict_governs(self):
        with tempfile.TemporaryDirectory() as tmp:
            strict = {
                "run_at_utc": datetime.now(timezone.utc).isoformat(),
                "config_hash": config_hash(), "names_passed": ["VST"],
            }
            (Path(tmp) / "2026-07-24.json").write_text(json.dumps(strict))
            receipt, path = ic._load_latest_calibration_receipt(tmp)
            self.assertEqual(receipt["names_passed"], ["VST"])
            self.assertEqual(path.name, "2026-07-24.json")

    def test_malformed_receipt_file_is_skipped_valid_ones_still_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", tmp):
                current_hash = config_hash()
                good = {
                    "run_at_utc": "2026-07-24T15:28:17.508115+00:00",
                    "config_hash": current_hash, "names_passed": ["VST"],
                }
                # Not valid JSON at all.
                (Path(tmp) / "2026-07-24-broken.json").write_text(
                    "{not valid json")
                # Valid JSON, but run_at_utc doesn't parse as a timestamp.
                (Path(tmp) / "2026-07-24-badtime.json").write_text(json.dumps(
                    {"run_at_utc": "not-a-real-timestamp",
                     "config_hash": current_hash, "names_passed": ["CEG"]}))
                # Valid JSON, but not an object at all.
                (Path(tmp) / "2026-07-24-notdict.json").write_text(json.dumps(
                    ["not", "a", "dict"]))
                (Path(tmp) / "2026-07-24-good.json").write_text(json.dumps(good))
                receipt, path = ic._load_latest_calibration_receipt(tmp)
                self.assertEqual(receipt["names_passed"], ["VST"])
                self.assertEqual(path.name, "2026-07-24-good.json")
                self.assertTrue(ic.solver_iv_calibration_gate("VST"))
                self.assertFalse(ic.solver_iv_calibration_gate("CEG"))

    def test_only_malformed_files_present_yields_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "2026-07-24-broken.json").write_text("{not valid json")
            receipt, path = ic._load_latest_calibration_receipt(tmp)
            self.assertIsNone(receipt)
            self.assertIsNone(path)

    def test_missing_dir_yields_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does_not_exist"
            receipt, path = ic._load_latest_calibration_receipt(missing)
            self.assertIsNone(receipt)
            self.assertIsNone(path)


# ---------------------------------------------------------------------------
# Solver splice -- capture integration (2026-07-24, IV-solver-capture)
# ---------------------------------------------------------------------------

class SolverIvCaptureIntegrationTests(unittest.TestCase):
    def setUp(self):
        lq._reset_memos()

    def _run(self, client, *, session_tag="midmorning", now_ny=None,
             universe=UNIVERSE, probe=None):
        now_ny = now_ny or NOW_NY
        probe = probe or _probe_realistic_entitlement(now_ny.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe):
            rc, receipt = ic.capture(
                session_tag, client=client, now_ny=now_ny, force=False,
                universe=universe, cache_dir=cache_dir, receipt_dir=receipt_dir)
        return rc, receipt

    def test_solver_success_and_gate_pass_splices_rank(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST", "CEG"})
        history = [0.20 + 0.001 * i for i in range(150)]  # >= PCT_MIN_OBS
        with tempfile.TemporaryDirectory() as calib_dir:
            # config_hash() hashes ALL uppercase config constants, including
            # IV_CALIBRATION_RECEIPT_DIR itself -- so the receipt's stored
            # hash must be computed INSIDE the same patched config state the
            # gate will later re-hash and compare against, or the patch's
            # own directory value silently mismatches the receipt.
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", calib_dir):
                calibration_receipt = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "config_hash": config_hash(),
                    "names_passed": ["VST", "CEG"],
                }
                (Path(calib_dir) / "2026-07-24.json").write_text(
                    json.dumps(calibration_receipt))
                with mock.patch.object(ic.data_rates, "risk_free_rate",
                                       return_value=SimpleNamespace(rate=0.04)), \
                     mock.patch.object(ic.data_rates, "dividend_yield",
                                       return_value=SimpleNamespace(yield_rate=0.0)), \
                     mock.patch.object(lq, "_load_iv_history", return_value=history):
                    rc, receipt = self._run(client)
        self.assertEqual(rc, 0)
        row = receipt["names"]["VST"]
        self.assertEqual(row["status"], "ok")
        self.assertEqual(row["iv_source"], "bs_solver")
        self.assertIsNotNone(row["atm_iv"])
        self.assertIsNotNone(row["iv_rank_preview"])
        self.assertIsNone(row["iv_label"])
        self.assertIsNone(row["greeks_note"])
        # Splice provenance (2026-07-24 fix): the top-level block names
        # exactly which calibration receipt authorized the splice.
        self.assertEqual(receipt["iv_rank_calibration"], {
            "receipt_path": str(Path(calib_dir) / "2026-07-24.json"),
            "inputs_mode": "strict",  # calibration_receipt has no key -> default
            "run_at_utc": calibration_receipt["run_at_utc"],
        })

    def test_solver_success_no_receipt_nulls_rank_with_label(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST", "CEG"})
        with tempfile.TemporaryDirectory() as calib_dir:
            with mock.patch.object(ic.data_rates, "risk_free_rate",
                                   return_value=SimpleNamespace(rate=0.04)), \
                 mock.patch.object(ic.data_rates, "dividend_yield",
                                   return_value=SimpleNamespace(yield_rate=0.0)), \
                 mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", calib_dir):
                # No receipt written -- calib_dir stays empty.
                rc, receipt = self._run(client)
        self.assertEqual(rc, 0)
        row = receipt["names"]["VST"]
        self.assertEqual(row["iv_source"], "bs_solver")
        self.assertIsNotNone(row["atm_iv"])
        self.assertIsNone(row["iv_rank_preview"])
        self.assertEqual(row["iv_label"], "solver-derived, not rank-comparable")
        self.assertIsNone(row["greeks_note"])
        # No name spliced (gate failed -- no receipt at all) -- no provenance.
        self.assertIsNone(receipt["iv_rank_calibration"])

    def test_solver_failure_records_specific_reason_string(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST", "CEG"})
        with mock.patch.object(
                ic.data_rates, "risk_free_rate",
                side_effect=ic.data_rates.MissingRateError("no curve")):
            rc, receipt = self._run(client)
        self.assertEqual(rc, 0)
        row = receipt["names"]["VST"]
        self.assertIsNone(row["iv_source"])
        self.assertIsNone(row["atm_iv"])
        self.assertIsNone(row["iv_rank_preview"])
        self.assertIn("solver: no rate curve coverage", row["greeks_note"])
        self.assertIn("not entitled", row["greeks_note"])
        # Solver itself failed -- nothing to splice, no provenance.
        self.assertIsNone(receipt["iv_rank_calibration"])

    def test_greeks_success_path_is_unaffected_by_solver_wiring(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})  # greeks OK
        rc, receipt = self._run(
            client, probe=_probe(NOW_NY.astimezone(timezone.utc)))
        self.assertEqual(rc, 0)
        row = receipt["names"]["VST"]
        self.assertEqual(row["iv_source"], "greeks_endpoint")
        self.assertEqual(row["atm_iv"], 0.30)
        self.assertIsNone(row["iv_label"])
        self.assertIsNone(row["greeks_note"])
        # The greeks-endpoint path never touches the solver/calibration
        # machinery at all -- no provenance to record.
        self.assertIsNone(receipt["iv_rank_calibration"])

    def test_provenance_reports_the_actual_inputs_mode_not_a_default(self):
        # A retrospective-mode receipt's own "inputs_mode" must appear
        # verbatim in the provenance block, not the "strict" default that
        # only applies when the key is genuinely absent.
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST", "CEG"})
        history = [0.20 + 0.001 * i for i in range(150)]
        with tempfile.TemporaryDirectory() as calib_dir:
            with mock.patch.object(config, "IV_CALIBRATION_RECEIPT_DIR", calib_dir):
                calibration_receipt = {
                    "run_at_utc": datetime.now(timezone.utc).isoformat(),
                    "inputs_mode": "retrospective_official",
                    "config_hash": config_hash(),
                    "names_passed": ["VST", "CEG"],
                }
                (Path(calib_dir) / "2026-07-24-retrospective.json").write_text(
                    json.dumps(calibration_receipt))
                with mock.patch.object(ic.data_rates, "risk_free_rate",
                                       return_value=SimpleNamespace(rate=0.04)), \
                     mock.patch.object(ic.data_rates, "dividend_yield",
                                       return_value=SimpleNamespace(yield_rate=0.0)), \
                     mock.patch.object(lq, "_load_iv_history", return_value=history):
                    rc, receipt = self._run(client)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["iv_rank_calibration"]["inputs_mode"],
                         "retrospective_official")
        self.assertEqual(receipt["iv_rank_calibration"]["run_at_utc"],
                         calibration_receipt["run_at_utc"])
        self.assertEqual(
            receipt["iv_rank_calibration"]["receipt_path"],
            str(Path(calib_dir) / "2026-07-24-retrospective.json"))


# ---------------------------------------------------------------------------
# Zero verdict authority
# ---------------------------------------------------------------------------

class ZeroVerdictAuthorityTests(unittest.TestCase):
    def test_no_entry_watch_import(self):
        src = inspect.getsource(ic)
        for line in src.splitlines():
            if line.startswith(("import ", "from ")):
                self.assertNotIn("entry_watch", line)

    def test_banned_verdict_vocabulary_absent(self):
        src = inspect.getsource(ic)
        for word in ("FIRE", "GREEN", "ENTRY-OK", "BUY", "SELL"):
            self.assertNotIn(word, src)

    def test_capture_run_does_not_touch_ledger_or_positions(self):
        ledger_before = _tree_snapshot(Path("ledger"))
        positions_before = _tree_snapshot(Path("data/positions"))
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0})
        probe = _probe(NOW_NY.astimezone(timezone.utc))
        cache_dir, receipt_dir = _tmp_dirs()
        lq._reset_memos()
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: probe):
            rc, _ = ic.capture("midmorning", client=client, now_ny=NOW_NY,
                               universe=UNIVERSE, cache_dir=cache_dir,
                               receipt_dir=receipt_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(_tree_snapshot(Path("ledger")), ledger_before)
        self.assertEqual(_tree_snapshot(Path("data/positions")), positions_before)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class MainCLITests(unittest.TestCase):
    def _run_main_with_expired_client(self, probe, client=None):
        stdout = io.StringIO()
        with (
            mock.patch.object(
                lq, "_live_client",
                return_value=client or ExpiredRefreshTokenClient()),
            mock.patch.object(lq, "load_latest_probe", return_value=probe),
            mock.patch.object(ic, "datetime", _FrozenCaptureDateTime),
            mock.patch.object(ic, "_write_receipt", return_value=True),
            mock.patch("sys.stdout", stdout),
        ):
            rc = ic.main(["--session-tag", "midmorning"])
        return rc, stdout.getvalue()

    def test_main_forwards_session_tag_and_force(self):
        calls = {}

        def fake_capture(session_tag, force=False):
            calls["session_tag"] = session_tag
            calls["force"] = force
            return 0, {}

        with mock.patch.object(ic, "capture", fake_capture):
            rc = ic.main(["--session-tag", "midday", "--force"])
        self.assertEqual(rc, 0)
        self.assertEqual(calls, {"session_tag": "midday", "force": True})

    def test_main_rejects_unknown_tag(self):
        with self.assertRaises(SystemExit):
            ic.main(["--session-tag", "bogus"])

    def test_main_requires_session_tag(self):
        with self.assertRaises(SystemExit):
            ic.main([])

    def test_main_reports_expired_auth_from_fresh_probe_capture(self):
        rc, output = self._run_main_with_expired_client(
            _probe(NOW_NY.astimezone(timezone.utc)))

        self.assertEqual(rc, 1)
        self.assertEqual(
            output,
            "intraday_capture auth EXPIRED: Refresh token is invalid, expired "
            "or revoked; run uv run python tools/setup_schwab.py\n",
        )

    def test_main_reports_expired_auth_from_fresh_probe_symbol_capture(self):
        rc, output = self._run_main_with_expired_client(
            _probe(NOW_NY.astimezone(timezone.utc)),
            client=ExpiredRefreshTokenAfterStockClient(),
        )

        self.assertEqual(rc, 1)
        self.assertEqual(
            output,
            "intraday_capture auth EXPIRED: Refresh token is invalid, expired "
            "or revoked; run uv run python tools/setup_schwab.py\n",
        )

    def test_main_reports_expired_auth_while_healing_stale_probe(self):
        rc, output = self._run_main_with_expired_client(
            _probe(NOW_NY.astimezone(timezone.utc) - timedelta(days=30)))

        self.assertEqual(rc, 1)
        self.assertEqual(
            output,
            "intraday_capture auth EXPIRED: Refresh token is invalid, expired "
            "or revoked; run uv run python tools/setup_schwab.py\n",
        )


# ---------------------------------------------------------------------------
# tools/intraday_capture.sh banner-pollution guard (2026-07-24 production
# incident: LumiBot + python-dotenv print import-time INFO banner lines to
# stdout, so a naive `$(uv run python -c ...)` command substitution
# captures banner text ahead of the real answer -- the same class of bug
# the 2026-07-23 H8 fix addressed, fixed here the way
# tools/daily_ritual.sh:82 fixes AS_OF: a strict whitelist grep + tail -1.)
# ---------------------------------------------------------------------------

WRAPPER = REPO_ROOT / "tools" / "intraday_capture.sh"


class WrapperBannerPollutionGuardTests(unittest.TestCase):
    """Static/structural checks that the specific fix elements are present,
    mirroring tests/test_h7_daily_exit_order.py's source-order style."""

    def test_tag_extraction_uses_a_strict_whitelist_filter(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            "grep -Eo '^(open_auction|open|midmorning|midday|preclose|NONE)$'",
            source)
        self.assertIn("| tail -1", source)

    def test_none_sentinel_disambiguates_benign_skip_from_unparseable_output(self):
        source = WRAPPER.read_text(encoding="utf-8")
        # The python side always prints a real tag OR the literal "NONE"
        # sentinel -- never a bare empty line, which would be ambiguous
        # between "legitimately no window near" and "banner ate the answer".
        self.assertIn('or "NONE"', source)
        self.assertIn('if [ "$TAG" = "NONE" ]; then', source)

    def test_empty_filtered_tag_always_refuses_loudly(self):
        source = WRAPPER.read_text(encoding="utf-8")
        idx_extract = source.index('TAG="$(echo "$TAG_RAW"')
        idx_refuse = source.index(
            'if [ "$TAG_RC" -ne 0 ] || [ -z "$TAG" ]; then')
        idx_none_check = source.index('if [ "$TAG" = "NONE" ]; then')
        # Extraction happens first, then the "unparseable" refusal check,
        # then (only for a non-empty, non-NONE tag) the benign-skip check.
        self.assertLess(idx_extract, idx_refuse)
        self.assertLess(idx_refuse, idx_none_check)
        exit_snippet = source[idx_refuse:idx_refuse + 400]
        self.assertIn("exit 1", exit_snippet)

    def test_exit_code_label_mapping_is_evidence_based_not_guessed(self):
        # The bug this specifically fixes: exit(2) from argparse (a usage
        # error, e.g. banner-polluted --session-tag) and exit(2) from this
        # module's OWN receipt-conflict path are indistinguishable by exit
        # code alone. The wrapper must diagnose from the module's printed
        # output, not assume a meaning for a bare exit code.
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("grep -q '^intraday_capture refused:'", source)
        self.assertIn("grep -q '^intraday_capture receipt CONFLICT'", source)
        self.assertIn("unrecognized failure mode", source)
        # The old blind `case "$CAP_RC" in 2) ... RECEIPT CONFLICT` pattern
        # must be gone.
        self.assertNotIn('2) crit "intraday_capture', source)


# ---------------------------------------------------------------------------
# Zero-coverage WARN, not a plain OK (today's 13:00 DNS outage looked like
# ">>> intraday_capture (midday): OK -- coverage: 0/15 names captured";
# an outage gap is a legitimate, non-fatal descriptive-dataset gap -- NOT
# CRITICAL -- but must be visibly not-OK, not indistinguishable from a
# genuinely healthy run.)
# ---------------------------------------------------------------------------

class WrapperZeroCoverageWarnStaticTests(unittest.TestCase):
    def test_zero_coverage_branch_present_and_not_critical(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            "grep -Eq '^coverage: 0/[0-9]+ '", source)
        self.assertIn(
            'note "intraday_capture (${TAG}): WARN -- zero coverage '
            '(provider unreachable?) -- ${COVERAGE_LINE}"', source)
        # The WARN branch calls note(), never crit() -- zero coverage alone
        # must not flip the run to CRITICAL/BROKEN.
        warn_idx = source.index("WARN -- zero coverage")
        line_start = source.rfind("\n", 0, warn_idx) + 1
        line_end = source.index("\n", warn_idx)
        self.assertTrue(source[line_start:line_end].lstrip().startswith("note "))

    def test_nonzero_coverage_still_reaches_plain_ok(self):
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn(
            'note "intraday_capture (${TAG}): OK -- ${COVERAGE_LINE}"', source)


class WrapperZeroCoverageWarnLiveTests(unittest.TestCase):
    """Executes the ACTUAL coverage-labeling block sliced verbatim out of
    tools/intraday_capture.sh (between the `if [ "$CAP_RC" -eq 0 ]; then`
    marker and its matching `fi`) in a real bash subprocess, with CAP_OUT/
    CAP_RC/TAG set to fixture values and a stub note()/crit(). This is the
    live counterpart to the static checks above -- proves the actual
    conditional logic branches correctly, not just that certain strings
    are present somewhere in the file."""

    def _extract_block(self) -> str:
        source = WRAPPER.read_text(encoding="utf-8")
        start = source.index('if [ "$CAP_RC" -eq 0 ]; then')
        end = source.index("\nfi\n", start) + len("\nfi")
        return source[start:end]

    def _run_block(self, cap_out: str, cap_rc: int) -> str:
        block = self._extract_block()
        # shlex.quote (not Python's repr!) -- a real embedded newline stays
        # a literal newline inside bash single quotes, whereas repr() would
        # emit the two-character escape "\n", which bash single quotes
        # do NOT interpret, silently breaking grep's line-anchored '^...'.
        quoted_cap_out = shlex.quote(cap_out)
        # Plain concatenation, NOT an f-string: `block` is real bash source
        # containing literal "${...}" parameter expansions, which an
        # f-string would misparse as Python replacement fields.
        script = "\n".join([
            "set -u",
            'SUMMARY=""',
            'note() { SUMMARY="${SUMMARY}$1\\n"; }',
            'crit() { SUMMARY="${SUMMARY}CRITICAL: $1\\n"; }',
            'TAG="midday"',
            "CAP_OUT=" + quoted_cap_out,
            "CAP_RC=" + str(cap_rc),
            block,
            'printf "%b" "$SUMMARY"',
            "",
        ])
        completed = subprocess.run(
            ["/bin/bash", "-c", script], capture_output=True, text=True,
            timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return completed.stdout

    def test_zero_of_fifteen_produces_warn_not_ok(self):
        out = self._run_block(
            "receipt=reports/intraday_capture/2026-07-24/midday.json\n"
            "coverage: 0/15 names captured", 0)
        self.assertIn("WARN -- zero coverage", out)
        self.assertNotIn("CRITICAL", out)
        self.assertNotIn(": OK -- coverage: 0/15", out)

    def test_nonzero_coverage_still_produces_plain_ok(self):
        out = self._run_block(
            "receipt=reports/intraday_capture/2026-07-24/midday.json\n"
            "coverage: 14/15 names captured", 0)
        self.assertIn(": OK -- coverage: 14/15 names captured", out)
        self.assertNotIn("WARN", out)
        self.assertNotIn("CRITICAL", out)

    def test_full_coverage_produces_plain_ok(self):
        out = self._run_block(
            "receipt=reports/intraday_capture/2026-07-24/midday.json\n"
            "coverage: 15/15 names captured", 0)
        self.assertIn(": OK -- coverage: 15/15 names captured", out)
        self.assertNotIn("WARN", out)
        self.assertNotIn("CRITICAL", out)


class TagDerivationBannerLiveTests(unittest.TestCase):
    """Runs the EXACT python one-liner the wrapper uses (real imports, real
    LumiBot/dotenv banner side effects -- not mocked), through the SAME
    grep pipeline, proving end-to-end that banner noise cannot leak into
    the extracted tag. This is the live counterpart to the static checks
    above; together they prove both the fix's presence and its behavior."""

    def _run_tag_script(self, now_ny_literal: str) -> str:
        script = (
            "from datetime import datetime\n"
            "from zoneinfo import ZoneInfo\n"
            "from options_researcher.intraday_capture import nearest_session_tag\n"
            "NY = ZoneInfo('America/New_York')\n"
            f"now_ny = {now_ny_literal}\n"
            'print(nearest_session_tag(now_ny) or "NONE")\n'
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, (str(REPO_ROOT), env.get("PYTHONPATH"))))
        completed = subprocess.run(
            [sys.executable, "-c", script], cwd=REPO_ROOT, env=env,
            capture_output=True, text=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        raw = completed.stdout + completed.stderr
        whitelist = {"open_auction", "open", "midmorning", "midday",
                     "preclose", "NONE"}
        matches = [ln for ln in raw.splitlines() if ln.strip() in whitelist]
        self.assertTrue(
            matches,
            f"no whitelisted line found in real subprocess output: {raw!r}")
        return matches[-1]

    def test_real_import_time_noise_does_not_pollute_a_resolved_tag(self):
        tag = self._run_tag_script(
            "datetime(2026, 7, 24, 9, 35, tzinfo=NY)")  # exactly "open"
        self.assertEqual(tag, "open")

    def test_real_import_time_noise_does_not_pollute_the_none_sentinel(self):
        tag = self._run_tag_script(
            "datetime(2026, 7, 24, 12, 0, tzinfo=NY)")  # between windows
        self.assertEqual(tag, "NONE")


if __name__ == "__main__":
    unittest.main()

"""tests/test_intraday_capture.py -- offline tests for the intraday
option-board capture (recorder).

No network, no ThetaData client, no .env: every fetch path is exercised via
an injected FakeClient, and receipts/chains are written to tempdirs, never
the repo's real reports/intraday_capture or .cache/intraday.
"""
import glob
import inspect
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

import config
from options_researcher import intraday_capture as ic
from options_researcher import live_quotes as lq
from options_researcher.chains import third_friday

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
    p = {"probed_at_utc": now_utc.isoformat(), "ny_date": TODAY.isoformat(),
         "thetadata_version": lq._installed_thetadata_version(),
         "stock_entitled": True, "probe_symbol": lq.PROBE_SYMBOL,
         "monthly_expiration": MONTHLY_EXP.isoformat(), "endpoints": endpoints}
    p.update(over)
    return p


class FakeClient:
    """Records every call; raises where a test asks it to."""

    def __init__(self, spots=None, stock_ts=None, greeks_raises=(),
                 oi_raises=(), expirations_raises=(), stock_raises=False):
        self.spots = spots or {}
        self.stock_ts = stock_ts
        self.greeks_raises = set(greeks_raises)
        self.oi_raises = set(oi_raises)
        self.expirations_raises = set(expirations_raises)
        self.stock_raises = stock_raises
        self.calls = {"stock": 0, "expirations": [], "greeks": [], "oi": []}

    def stock_snapshot_quote(self, symbols, **kw):
        self.calls["stock"] += 1
        if self.stock_raises:
            raise RuntimeError("stock feed down")
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

    def option_snapshot_greeks_all(self, symbol, expiration=None, **kw):
        self.calls["greeks"].append((symbol, str(expiration)))
        if symbol in self.greeks_raises:
            raise RuntimeError("boom greeks")
        exp = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration)
        return pd.DataFrame([
            {"expiration": exp, "strike": 150.0, "right": "P", "bid": 2.0,
             "ask": 2.1, "delta": -0.50, "implied_vol": 0.30},
            {"expiration": exp, "strike": 150.0, "right": "C", "bid": 2.2,
             "ask": 2.4, "delta": 0.55, "implied_vol": 0.28},
            # wide spread -- must fail the spread gate regardless of OI
            {"expiration": exp, "strike": 200.0, "right": "C", "bid": 0.05,
             "ask": 0.50, "delta": 0.10, "implied_vol": 0.60},
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
        still_bad = _probe(now_utc, thetadata_version="0.0.0-wrong")
        with mock.patch.object(lq, "load_latest_probe",
                               lambda dir=lq.PROBE_DIR: stale), \
             mock.patch.object(lq, "run_probe", return_value=still_bad):
            out_probe, healed, ok, reason = ic.ensure_probe_ok(
                object(), NOW_NY, now_utc)
        self.assertTrue(healed)
        self.assertFalse(ok)
        self.assertIn("thetadata", reason)


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

    def test_per_name_degradation_does_not_abort_the_board(self):
        client = FakeClient(spots={"VST": 150.0, "CEG": 90.0},
                            greeks_raises={"VST"})
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        self.assertEqual(receipt["names"]["VST"]["status"], "unavailable")
        self.assertIn("boom greeks", receipt["names"]["VST"]["note"])
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

    def test_spot_missing_degrades_but_chain_still_captured(self):
        client = FakeClient(spots={"CEG": 90.0})  # VST absent from stock batch
        rc, receipt, *_ = self._run(client)
        self.assertEqual(rc, 0)
        vst = receipt["names"]["VST"]
        self.assertEqual(vst["status"], "ok")  # chain still fetched
        self.assertIn("missing from batched stock snapshot", vst["spot_note"])
        self.assertNotIn("spot_bid", vst)

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
        still_bad = _probe(now_utc, thetadata_version="wrong-version")
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


if __name__ == "__main__":
    unittest.main()

"""tests/test_live_quotes.py -- offline tests for the live PREVIEW adapter.

No network, no ThetaData client, no .env: every fetch path is exercised via
injected fake clients, and the pure functions are tested directly.
"""
import json
import tempfile
import unittest
from datetime import date, datetime, time, timedelta, timezone
from unittest import mock
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

import config
from options_researcher import live_quotes as lq
from options_researcher.chains import third_friday
from options_researcher.features import build_daily_features

NY = ZoneInfo("America/New_York")

TODAY = date(2026, 7, 15)                     # a Wednesday
NOW_NY = datetime(2026, 7, 15, 10, 30, tzinfo=NY)
NOW_UTC = NOW_NY.astimezone(timezone.utc)
SATURDAY = datetime(2026, 7, 18, 12, 0, tzinfo=NY)

MONTHLY_EXP = third_friday(2026, 8)           # 37 DTE from TODAY (in 15-60)
WEEKLY_EXP = MONTHLY_EXP + timedelta(days=7)  # in band but NOT a monthly
LEAPS_EXP = third_friday(2027, 7)             # 366 DTE (in H4_THESIS_DTE_BAND)

# This module's own fixtures (below) and several production functions under
# test (probe_ok's cross-check against the currently-configured provider)
# call live_quotes._configured_provider(), which reads LIVE_MARKET_DATA_PROVIDER.
# Pin it for the whole module so the suite is hermetic (2026-08-11 audit L5)
# instead of depending on ambient shell/.env state. clear=False -- only this
# one key is touched; unrelated ambient env (PATH, HOME, ...) that some tests
# still spawn real subprocesses against stays intact. dotenv.load_dotenv is
# stubbed too so a real .env on disk cannot clobber or interfere.
_env_patcher = mock.patch.dict(
    "os.environ", {"LIVE_MARKET_DATA_PROVIDER": "schwab"})
_dotenv_patcher = mock.patch("dotenv.load_dotenv")


def setUpModule():
    _dotenv_patcher.start()
    _env_patcher.start()


def tearDownModule():
    _env_patcher.stop()
    _dotenv_patcher.stop()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _probe(**over):
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
    p = {"probed_at_utc": NOW_UTC.isoformat(),
         "ny_date": TODAY.isoformat(),
         "provider": provider,
         "provider_version": lq._installed_provider_version(provider),
         "stock_entitled": True,
         "endpoints": endpoints}
    p.update(over)
    return p


def _greeks_frame(expiration):
    exp = expiration if isinstance(expiration, str) else expiration.isoformat()
    if exp == MONTHLY_EXP.isoformat():
        rows = [
            {"expiration": exp, "strike": 150.0, "right": "P", "bid": 2.0,
             "ask": 2.1, "delta": -0.50, "implied_vol": 0.30},
            {"expiration": exp, "strike": 145.0, "right": "P", "bid": 1.0,
             "ask": 1.1, "delta": -0.40, "implied_vol": 0.35},
        ]
    else:  # LEAPS expiry
        rows = [
            {"expiration": exp, "strike": 140.0, "right": "C", "bid": 40.0,
             "ask": 41.0, "delta": 0.70, "implied_vol": 0.32},
            {"expiration": exp, "strike": 180.0, "right": "C", "bid": 20.0,
             "ask": 21.0, "delta": 0.55, "implied_vol": 0.31},
        ]
    return pd.DataFrame(rows)


def _oi_frame(expiration):
    exp = expiration if isinstance(expiration, str) else expiration.isoformat()
    return pd.DataFrame([
        {"expiration": exp, "strike": 140.0, "right": "C", "open_interest": 500},
        {"expiration": exp, "strike": 180.0, "right": "C", "open_interest": 300},
    ])


def _quote_chain(spot, expiration):
    """Monthly C+P snapshot whose mids satisfy parity exactly at `spot`."""
    exp = expiration if isinstance(expiration, str) else expiration.isoformat()
    rows = []
    for k in (spot - 5.0, spot, spot + 5.0):
        c_mid = 2.0 + max(0.0, spot - k)
        p_mid = c_mid - spot + k
        rows.append({"expiration": exp, "strike": k, "right": "C",
                     "bid": c_mid - 0.05, "ask": c_mid + 0.05})
        rows.append({"expiration": exp, "strike": k, "right": "P",
                     "bid": p_mid - 0.05, "ask": p_mid + 0.05})
    return pd.DataFrame(rows)


class FakeClient:
    """Records every call; raises where a test asks it to."""

    def __init__(self, spots=None, parity_spots=None, stock_ts=None,
                 greeks_raises=(), oi_raises=False, stock_raises=False):
        self.spots = spots or {}
        self.parity_spots = parity_spots or {}
        self.stock_ts = stock_ts
        self.greeks_raises = set(greeks_raises)
        self.oi_raises = oi_raises
        self.stock_raises = stock_raises
        self.calls = {"stock": 0, "expirations": [], "quote": [],
                      "greeks": [], "oi": []}

    def stock_snapshot_quote(self, symbols, **kw):
        self.calls["stock"] += 1
        if self.stock_raises:
            raise RuntimeError("PERMISSION_DENIED: no stock entitlement")
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
        return pd.DataFrame({"expiration": [MONTHLY_EXP.isoformat(),
                                            WEEKLY_EXP.isoformat(),
                                            LEAPS_EXP.isoformat()]})

    def option_snapshot_quote(self, symbol, expiration=None, **kw):
        self.calls["quote"].append((symbol, str(expiration)))
        return _quote_chain(self.parity_spots.get(symbol, 150.0), expiration)

    def option_snapshot_greeks_all(self, symbol, expiration=None, **kw):
        self.calls["greeks"].append((symbol, str(expiration)))
        if symbol in self.greeks_raises:
            raise RuntimeError("boom greeks")
        return _greeks_frame(expiration)

    def option_snapshot_open_interest(self, symbol, expiration=None, **kw):
        self.calls["oi"].append((symbol, str(expiration)))
        if self.oi_raises:
            raise RuntimeError("boom oi")
        return _oi_frame(expiration)


class ScheduleClient(FakeClient):
    def __init__(self, *args, session_open=True, session_raises=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_open = session_open
        self.session_raises = session_raises
        self.calls["market_hours"] = 0

    def regular_session_state(self, now_ny):
        self.calls["market_hours"] += 1
        if self.session_raises:
            raise RuntimeError("market-hours unavailable")
        return {
            "open": self.session_open,
            "equity_regular_open": self.session_open,
            "option_regular_open": self.session_open,
            "source": "schwab_market_hours",
        }


class ExplodingClient:
    """Any attribute access is a test failure: the path must not touch it."""

    def __getattr__(self, name):
        raise AssertionError(f"client must not be touched, accessed {name!r}")


def _features_frame(values):
    return pd.DataFrame({"atm_iv": values})


def _patch_features(values):
    return mock.patch.object(lq.features, "load_features",
                             lambda sym: _features_frame(values))


def _leaps_series(oi_unused=None, bid=40.0, ask=41.0, delta=0.70):
    return pd.Series({"expiration": LEAPS_EXP.isoformat(),
                      "exp_date": LEAPS_EXP, "strike": 140.0,
                      "delta": delta, "bid": bid, "ask": ask})


def _preview(**over):
    kw = dict(spot=150.0, spot_source="stock_snapshot_quote", spot_ts=NOW_UTC,
              trigger_level=config.H5_ENTRY_TRIGGERS["VST"], atm_iv=0.30,
              iv_history=[0.5] * 200, leaps_row=_leaps_series(), oi=500.0,
              oi_asof=TODAY.isoformat(), now=NOW_UTC)
    kw.update(over)
    return lq.build_symbol_preview("VST", **kw)


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

class SessionWindowTests(unittest.TestCase):
    def test_before_open_is_closed(self):
        self.assertFalse(lq.in_regular_session(
            datetime(2026, 7, 15, 9, 29, tzinfo=NY)))

    def test_at_open_is_open(self):
        self.assertTrue(lq.in_regular_session(
            datetime(2026, 7, 15, 9, 30, tzinfo=NY)))

    def test_just_before_close_is_open(self):
        self.assertTrue(lq.in_regular_session(
            datetime(2026, 7, 15, 15, 59, tzinfo=NY)))

    def test_at_close_is_closed(self):
        self.assertFalse(lq.in_regular_session(
            datetime(2026, 7, 15, 16, 0, tzinfo=NY)))

    def test_weekend_is_closed(self):
        self.assertFalse(lq.in_regular_session(SATURDAY))
        self.assertFalse(lq.in_regular_session(
            datetime(2026, 7, 19, 12, 0, tzinfo=NY)))


class ResolveExpiriesTests(unittest.TestCase):
    def test_earliest_in_band_monthly_wins(self):
        out = lq.resolve_expiries(
            [LEAPS_EXP, third_friday(2026, 9), MONTHLY_EXP], TODAY)
        self.assertEqual(out["monthly"], MONTHLY_EXP)

    def test_non_monthly_in_band_is_skipped(self):
        earlier_weekly = MONTHLY_EXP - timedelta(days=14)  # Friday, not 3rd
        self.assertFalse((earlier_weekly - TODAY).days < 15)
        out = lq.resolve_expiries([earlier_weekly, MONTHLY_EXP], TODAY)
        self.assertEqual(out["monthly"], MONTHLY_EXP)

    def test_monthly_outside_band_is_none(self):
        out = lq.resolve_expiries(
            [third_friday(2026, 7), third_friday(2026, 12)], TODAY)
        self.assertIsNone(out["monthly"])

    def test_empty_gives_both_none(self):
        out = lq.resolve_expiries([], TODAY)
        self.assertIsNone(out["monthly"])
        self.assertIsNone(out["leaps"])

    def test_leaps_nearest_365_within_band(self):
        e300 = TODAY + timedelta(days=300)
        e400 = TODAY + timedelta(days=400)
        out = lq.resolve_expiries([e300, e400], TODAY)
        self.assertEqual(out["leaps"], e400)  # |400-365| < |300-365|

    def test_leaps_outside_band_excluded(self):
        lo, hi = config.H4_THESIS_DTE_BAND
        out = lq.resolve_expiries([TODAY + timedelta(days=lo - 5),
                                   TODAY + timedelta(days=hi + 30)], TODAY)
        self.assertIsNone(out["leaps"])


def _chain_day(iv, expiration):
    return pd.DataFrame([{
        "expiration": expiration, "strike": 100.0, "right": "P",
        "bid": 2.0, "ask": 2.1, "open_interest": 500, "iv": iv,
        "delta": -0.50, "gamma": 0.0, "theta": 0.0, "vega": 0.0}])


def _features_fixture(n_days=300, last_iv=0.90):
    days = pd.bdate_range("2019-01-02", periods=n_days)
    isos = days.strftime("%Y-%m-%d")
    closes = pd.Series(np.full(n_days, 100.0), index=isos)
    rng = np.random.default_rng(7)
    chains = {}
    for i, (ts, iso) in enumerate(zip(days, isos)):
        d = ts.date()
        month = d.month + (2 if d.day > 10 else 1)
        year = d.year + (1 if month > 12 else 0)
        month = month if month <= 12 else month - 12
        exp = third_friday(year, month)
        iv = last_iv if i == n_days - 1 else float(0.15 + 0.20 * rng.random())
        chains[iso] = _chain_day(iv, exp.isoformat())
    return isos, closes, chains


class IvRankPreviewTests(unittest.TestCase):
    def test_parity_with_build_daily_features(self):
        isos, closes, chains = _features_fixture(300, last_iv=0.27)
        f = build_daily_features("VST", isos[0], isos[-1],
                                 closes=closes, chains=chains, earnings=[])
        hist = [float(v) for v in f["atm_iv"].iloc[:-1]]
        live = float(f["atm_iv"].iloc[-1])
        self.assertAlmostEqual(lq.iv_rank_preview(hist, live),
                               float(f["iv_rank"].iloc[-1]), places=12)

    def test_nan_below_min_obs(self):
        self.assertTrue(np.isnan(lq.iv_rank_preview([0.2] * 100, 0.30)))

    def test_none_live_iv_is_nan(self):
        self.assertTrue(np.isnan(lq.iv_rank_preview([0.2] * 200, None)))

    def test_window_truncates_to_last_252(self):
        hist = [0.9] * 10 + [0.2] * 251
        self.assertEqual(lq.iv_rank_preview(hist, 0.30), 1.0)

    def test_non_finite_history_entries_excluded(self):
        hist = [float("nan")] * 50 + [0.2] * 150
        rank = lq.iv_rank_preview(hist, 0.30)
        self.assertEqual(rank, 1.0)  # 150 finite + live = 151 >= 126


class QuoteIsFreshTests(unittest.TestCase):
    def test_fresh(self):
        ts = NOW_UTC - timedelta(seconds=30)
        self.assertTrue(lq.quote_is_fresh(
            ts, NOW_UTC, config.LIVE_QUOTE_MAX_AGE_SECONDS))

    def test_stale(self):
        ts = NOW_UTC - timedelta(
            seconds=config.LIVE_QUOTE_MAX_AGE_SECONDS + 1)
        self.assertFalse(lq.quote_is_fresh(
            ts, NOW_UTC, config.LIVE_QUOTE_MAX_AGE_SECONDS))

    def test_none_is_stale(self):
        self.assertFalse(lq.quote_is_fresh(
            None, NOW_UTC, config.LIVE_QUOTE_MAX_AGE_SECONDS))

    def test_naive_timestamp_fails_closed(self):
        naive = datetime(2026, 7, 15, 10, 29, 45)
        self.assertFalse(lq.quote_is_fresh(
            naive, NOW_UTC, config.LIVE_QUOTE_MAX_AGE_SECONDS))

    def test_future_timestamp_beyond_clock_tolerance_fails_closed(self):
        future = NOW_UTC + timedelta(
            seconds=lq._FUTURE_CLOCK_TOLERANCE_SECONDS + 1
        )
        self.assertFalse(
            lq.quote_is_fresh(
                future, NOW_UTC, config.LIVE_QUOTE_MAX_AGE_SECONDS
            )
        )


class ChainQualityTests(unittest.TestCase):
    def _frame(self, **overrides):
        row = {
            "expiration": MONTHLY_EXP.isoformat(),
            "strike": 150.0,
            "right": "P",
            "bid": 2.0,
            "ask": 2.1,
            "delta": -0.50,
            "implied_vol": 0.30,
            "timestamp": NOW_UTC,
            "multiplier": 100,
            "non_standard": False,
            "chain_is_delayed": False,
            "chain_is_truncated": False,
            "chain_status": "SUCCESS",
        }
        row.update(overrides)
        return pd.DataFrame([row])

    def test_delayed_chain_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "delayed"):
            lq._assemble_chain_frame(
                self._frame(chain_is_delayed=True),
                "delayed",
                with_greeks=True,
            )

    def test_truncated_chain_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "truncated"):
            lq._assemble_chain_frame(
                self._frame(chain_is_truncated=True),
                "truncated",
                with_greeks=True,
            )

    def test_nonstandard_and_wrong_multiplier_contracts_are_rejected(self):
        frame = pd.concat(
            [
                self._frame(non_standard=True),
                self._frame(multiplier=10),
            ],
            ignore_index=True,
        )
        with self.assertRaisesRegex(RuntimeError, "no standard"):
            lq._assemble_chain_frame(frame, "nonstandard", with_greeks=True)

    def test_fresh_option_timestamp_is_required(self):
        lq._require_fresh_option_row(
            self._frame().iloc[0], NOW_UTC, "fresh option"
        )
        with self.assertRaisesRegex(RuntimeError, "stale"):
            lq._require_fresh_option_row(
                self._frame(
                    timestamp=NOW_UTC
                    - timedelta(
                        seconds=config.LIVE_QUOTE_MAX_AGE_SECONDS + 1
                    )
                ).iloc[0],
                NOW_UTC,
                "stale option",
            )

    def test_selected_locked_option_market_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "locked"):
            lq._require_fresh_option_row(
                self._frame(bid=2.0, ask=2.0).iloc[0],
                NOW_UTC,
                "locked option",
            )


class BuildSymbolPreviewTests(unittest.TestCase):
    def test_all_gates_met_and_armed(self):
        row = _preview()
        self.assertEqual(row["gates"],
                         {"price": "MET", "ivr": "MET", "liquidity": "MET"})
        self.assertTrue(row["armed"])
        self.assertEqual(row["status"], "ok")

    def test_price_unmet_above_trigger(self):
        row = _preview(spot=config.H5_ENTRY_TRIGGERS["VST"] + 5.0)
        self.assertEqual(row["gates"]["price"], "UNMET")
        self.assertFalse(row["armed"])

    def test_price_exactly_at_trigger_is_met(self):
        row = _preview(spot=config.H5_ENTRY_TRIGGERS["VST"])
        self.assertEqual(row["gates"]["price"], "MET")
        self.assertTrue(row["armed"])

    def test_spot_none_price_unknown_not_armed(self):
        row = _preview(spot=None)
        self.assertEqual(row["gates"]["price"], "UNKNOWN")
        self.assertFalse(row["armed"])

    def test_non_trigger_name_has_no_price_gate(self):
        row = _preview(trigger_level=None)
        self.assertNotIn("price", row["gates"])
        self.assertFalse(row["armed"])
        self.assertIsNone(row["trigger"])

    def test_ivr_unmet_when_rank_above_max(self):
        # live IV above the whole history -> rank 1.0 > H5_ENTRY_IVR_MAX
        row = _preview(atm_iv=0.90, iv_history=[0.2] * 200)
        self.assertEqual(row["gates"]["ivr"], "UNMET")

    def test_ivr_unknown_when_atm_iv_missing(self):
        row = _preview(atm_iv=None)
        self.assertEqual(row["gates"]["ivr"], "UNKNOWN")
        self.assertIsNone(row["iv_rank_preview"])

    def test_ivr_unknown_when_history_short(self):
        row = _preview(iv_history=[0.5] * 50)
        self.assertEqual(row["gates"]["ivr"], "UNKNOWN")

    def test_liquidity_unmet_on_low_oi(self):
        row = _preview(oi=config.MIN_OPEN_INTEREST - 1)
        self.assertEqual(row["gates"]["liquidity"], "UNMET")

    def test_liquidity_unmet_on_wide_spread(self):
        row = _preview(leaps_row=_leaps_series(bid=30.0, ask=41.0))
        self.assertEqual(row["gates"]["liquidity"], "UNMET")

    def test_oi_absent_liquidity_unknown_fail_closed(self):
        row = _preview(oi=None)
        self.assertEqual(row["gates"]["liquidity"], "UNKNOWN")
        self.assertIsNone(row["oi_label"])

    def test_no_leaps_row_liquidity_unknown(self):
        row = _preview(leaps_row=None, oi=None, oi_asof=None)
        self.assertEqual(row["gates"]["liquidity"], "UNKNOWN")
        self.assertIsNone(row["leaps"])

    def test_all_unknown_fail_closed(self):
        row = _preview(spot=None, atm_iv=None, iv_history=[],
                       leaps_row=None, oi=None, oi_asof=None)
        self.assertEqual(row["gates"],
                         {"price": "UNKNOWN", "ivr": "UNKNOWN",
                          "liquidity": "UNKNOWN"})
        self.assertFalse(row["armed"])

    def test_oi_label_does_not_claim_unverified_provider_update_semantics(self):
        row = _preview()
        self.assertEqual(row["oi_label"],
                         f"OI observed {TODAY.isoformat()} "
                         "(provider update cadence/as-of unverified)")

    def test_awaiting_close_label_present(self):
        self.assertIn("awaiting close", _preview()["lane"])

    def test_fire_never_appears_in_any_preview_payload(self):
        cases = [
            _preview(),  # fully green, all gates MET, armed
            _preview(spot=None, atm_iv=None, iv_history=[], leaps_row=None,
                     oi=None, oi_asof=None),
            _preview(spot=999.0),
            _preview(trigger_level=None),
            _preview(atm_iv=0.90, iv_history=[0.2] * 200,
                     oi=config.MIN_OPEN_INTEREST - 1),
        ]
        for row in cases:
            dumped = json.dumps(row)  # also proves JSON-serializable
            self.assertNotIn("FIRE", dumped)
            self.assertNotIn("verdict", dumped)


# ---------------------------------------------------------------------------
# Probe machinery
# ---------------------------------------------------------------------------

class ProbeOkTests(unittest.TestCase):
    def test_missing_probe_fails(self):
        ok, reason = lq.probe_ok(None, NOW_UTC)
        self.assertFalse(ok)
        self.assertIn("probe", reason)

    def test_good_probe_passes(self):
        ok, reason = lq.probe_ok(_probe(), NOW_UTC)
        self.assertTrue(ok)
        self.assertEqual(reason, "ok")

    def test_version_mismatch_fails(self):
        ok, reason = lq.probe_ok(_probe(provider_version="0.0.1"), NOW_UTC)
        self.assertFalse(ok)
        self.assertIn("0.0.1", reason)

    def test_stale_probe_fails(self):
        old = (NOW_UTC - timedelta(days=config.LIVE_PROBE_MAX_AGE_DAYS + 1))
        ok, reason = lq.probe_ok(
            _probe(probed_at_utc=old.isoformat()), NOW_UTC)
        self.assertFalse(ok)
        self.assertIn("LIVE_PROBE_MAX_AGE_DAYS", reason)

    def test_required_endpoint_failure_fails(self):
        p = _probe()
        p["endpoints"]["option_snapshot_greeks_all"] = {
            "ok": False, "columns": None, "error": "RpcError: boom"}
        ok, reason = lq.probe_ok(p, NOW_UTC)
        self.assertFalse(ok)
        self.assertIn("option_snapshot_greeks_all", reason)

    def test_stock_denied_still_ok(self):
        p = _probe(stock_entitled=False)
        p["endpoints"]["stock_snapshot_quote"] = {
            "ok": False, "columns": None,
            "error": "RpcError: PERMISSION_DENIED"}
        ok, reason = lq.probe_ok(p, NOW_UTC)
        self.assertTrue(ok)
        self.assertIn("parity", reason)


class RunProbeTests(unittest.TestCase):
    def test_refuses_outside_regular_session(self):
        with self.assertRaises(RuntimeError):
            lq.run_probe(client=ExplodingClient(), now_ny=SATURDAY)

    def test_records_endpoints_and_roundtrips(self):
        fake = FakeClient(spots={s: 150.0 for s in config.UNIVERSE})
        with tempfile.TemporaryDirectory() as tmp:
            probe = lq.run_probe(client=fake, now_ny=NOW_NY, out_dir=tmp)
            back = lq.load_latest_probe(dir=tmp)
        self.assertEqual(back, probe)
        self.assertTrue(probe["stock_entitled"])
        self.assertEqual(probe["monthly_expiration"], MONTHLY_EXP.isoformat())
        for name in lq.REQUIRED_PROBE_ENDPOINTS:
            self.assertTrue(probe["endpoints"][name]["ok"], name)
        ok, _ = lq.probe_ok(probe, NOW_UTC)
        self.assertTrue(ok)

    def test_stock_denial_recorded_not_fatal(self):
        fake = FakeClient(stock_raises=True)
        with tempfile.TemporaryDirectory() as tmp:
            probe = lq.run_probe(client=fake, now_ny=NOW_NY, out_dir=tmp)
        self.assertFalse(probe["stock_entitled"])
        rec = probe["endpoints"]["stock_snapshot_quote"]
        self.assertFalse(rec["ok"])
        self.assertEqual(rec["error"], "RuntimeError")
        ok, _ = lq.probe_ok(probe, NOW_UTC)
        self.assertTrue(ok)

    def test_load_latest_probe_missing_dir_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(lq.load_latest_probe(dir=tmp + "/nope"))
            self.assertIsNone(lq.load_latest_probe(dir=tmp))


class RunProbeProviderLazyDefaultTests(unittest.TestCase):
    """Pins the 2026-08-11 audit L5 fix at run_probe()'s provider/version
    resolution. getattr(obj, name, default) evaluates `default` EAGERLY --
    Python builds the full call before dispatching it -- so
    _configured_provider() (a hard RuntimeError when
    LIVE_MARKET_DATA_PROVIDER is unset) used to run even when `client`
    already supplied provider_name, breaking every offline test that injects
    a fake client. Both cases below run with NO env var and NO .env file to
    prove the fallback is now reached only when the attribute is genuinely
    absent -- a real client missing the label must still raise identically."""

    def test_client_supplied_provider_label_bypasses_configured_provider(self):
        fake = FakeClient(spots={s: 150.0 for s in config.UNIVERSE})
        fake.provider_name = "schwab"
        fake.provider_version = "stub-1"
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {}, clear=True),
            tempfile.TemporaryDirectory() as tmp,
        ):
            probe = lq.run_probe(client=fake, now_ny=NOW_NY, out_dir=tmp)
        # provider/provider_version came straight off the fake client --
        # _configured_provider()/_installed_provider_version() were never
        # reached, so a genuinely empty environment did not raise.
        self.assertEqual(probe["provider"], "schwab")
        self.assertEqual(probe["provider_version"], "stub-1")

    def test_missing_provider_label_still_raises_the_same_error(self):
        fake = FakeClient(spots={s: 150.0 for s in config.UNIVERSE})
        self.assertFalse(hasattr(fake, "provider_name"))
        with (
            mock.patch("dotenv.load_dotenv"),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                r"LIVE_MARKET_DATA_PROVIDER must be set explicitly to "
                r"'schwab'; ThetaData acquisition is disabled and no "
                r"fallback is permitted\.",
            ):
                lq.run_probe(client=fake, now_ny=NOW_NY)


# ---------------------------------------------------------------------------
# refresh() with fake clients
# ---------------------------------------------------------------------------

def _entitled_spots():
    # VST 150 < 160 trigger -> armed; AMZN 230 > 220 -> not armed.
    return {"VST": 150.0, "AMZN": 230.0, "MSFT": 400.0, "CEG": 300.0}


class RefreshTests(unittest.TestCase):
    def setUp(self):
        lq._reset_memos()

    def test_closed_session_makes_no_client_calls(self):
        payload = lq.refresh(client=ExplodingClient(), now_ny=SATURDAY,
                             probe=_probe())
        self.assertEqual(payload["session_state"], "closed")
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "off")
            self.assertIn("closed", payload["symbols"][sym]["note"])

    def test_probe_failure_turns_live_off(self):
        bad = _probe(provider_version="0.0.1")
        payload = lq.refresh(client=ExplodingClient(), now_ny=NOW_NY,
                             probe=bad)
        self.assertEqual(payload["session_state"], "open")
        self.assertFalse(payload["probe"]["ok"])
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "off")

    def test_entitled_happy_path(self):
        fake = FakeClient(spots=_entitled_spots())
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "ok")
        self.assertTrue(vst["armed"])
        self.assertEqual(vst["gates"]["price"], "MET")
        self.assertAlmostEqual(vst["spot"], 150.0)
        self.assertEqual(vst["spot_source"], "stock_snapshot_quote")
        self.assertAlmostEqual(vst["atm_iv"], 0.30)
        self.assertEqual(vst["gates"]["ivr"], "MET")
        self.assertEqual(vst["gates"]["liquidity"], "MET")
        self.assertEqual(vst["open_interest"], 500.0)
        self.assertEqual(vst["leaps"]["strike"], 140.0)
        self.assertIn("update cadence/as-of unverified", vst["oi_label"])
        amzn = payload["symbols"]["AMZN"]
        self.assertEqual(amzn["status"], "ok")
        self.assertFalse(amzn["armed"])
        self.assertEqual(amzn["gates"]["price"], "UNMET")
        self.assertEqual(amzn["gates"]["ivr"], "UNKNOWN")
        self.assertIn("not armed", amzn["note"])
        msft = payload["symbols"]["MSFT"]
        self.assertEqual(msft["status"], "ok")
        self.assertNotIn("price", msft["gates"])
        self.assertEqual(fake.calls["stock"], 1)  # one batched call
        self.assertNotIn("FIRE", json.dumps(payload))

    def test_armed_only_option_calls(self):
        fake = FakeClient(spots=_entitled_spots())
        with _patch_features([0.5] * 200):
            lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        greeks_syms = {s for s, _ in fake.calls["greeks"]}
        self.assertEqual(greeks_syms, {"VST"})       # armed name only
        self.assertEqual(len(fake.calls["greeks"]), 2)  # monthly + LEAPS
        self.assertEqual(fake.calls["oi"],
                         [("VST", str(LEAPS_EXP))])
        self.assertEqual(fake.calls["expirations"], ["VST"])
        self.assertEqual(fake.calls["quote"], [])    # entitled: no parity

    def test_stale_stock_timestamp_is_unavailable(self):
        probe = _probe()
        probe["endpoints"]["stock_snapshot_quote"]["columns"] = [
            "symbol", "bid", "ask", "timestamp"]
        stale = NOW_UTC - timedelta(
            seconds=config.LIVE_QUOTE_MAX_AGE_SECONDS + 60)
        fake = FakeClient(spots=_entitled_spots(), stock_ts=stale)
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=probe)
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "unavailable")
        self.assertEqual(fake.calls["greeks"], [])  # nothing armed on stale

    def test_fresh_stock_timestamp_passes(self):
        probe = _probe()
        probe["endpoints"]["stock_snapshot_quote"]["columns"] = [
            "symbol", "bid", "ask", "timestamp"]
        fake = FakeClient(spots=_entitled_spots(),
                          stock_ts=NOW_UTC - timedelta(seconds=5))
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=probe)
        self.assertEqual(payload["symbols"]["VST"]["status"], "ok")

    def test_future_stock_timestamp_is_unavailable(self):
        probe = _probe()
        probe["endpoints"]["stock_snapshot_quote"]["columns"] = [
            "symbol", "bid", "ask", "timestamp"]
        fake = FakeClient(
            spots=_entitled_spots(),
            stock_ts=NOW_UTC
            + timedelta(seconds=lq._FUTURE_CLOCK_TOLERANCE_SECONDS + 1),
        )
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=probe)
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "unavailable")

    def test_provider_market_hours_closed_turns_live_off(self):
        fake = ScheduleClient(spots=_entitled_spots(), session_open=False)
        payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        self.assertEqual(payload["session_state"], "closed")
        self.assertEqual(payload["session_source"], "schwab_market_hours")
        self.assertEqual(fake.calls["market_hours"], 1)
        self.assertEqual(fake.calls["stock"], 0)
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "off")

    def test_provider_market_hours_failure_turns_live_off_unknown(self):
        fake = ScheduleClient(
            spots=_entitled_spots(), session_raises=True
        )
        payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        self.assertEqual(payload["session_state"], "unknown")
        self.assertEqual(fake.calls["stock"], 0)
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "off")

    def test_parity_fallback_path(self):
        probe = _probe(stock_entitled=False)
        probe["endpoints"]["stock_snapshot_quote"] = {
            "ok": False, "columns": None, "error": "PERMISSION_DENIED"}
        fake = FakeClient(parity_spots={"VST": 150.0, "AMZN": 230.0})
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=probe)
        self.assertEqual(fake.calls["stock"], 0)  # never touches stock feed
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "ok")
        self.assertEqual(vst["spot_source"], "parity")
        self.assertAlmostEqual(vst["spot"], 150.0, places=6)
        self.assertTrue(vst["armed"])
        amzn = payload["symbols"]["AMZN"]
        self.assertEqual(amzn["spot_source"], "parity")
        self.assertFalse(amzn["armed"])
        for sym in ("MSFT", "CEG"):  # non-trigger names: off, no option calls
            self.assertEqual(payload["symbols"][sym]["status"], "off")
        quote_syms = {s for s, _ in fake.calls["quote"]}
        self.assertEqual(quote_syms, {"VST", "AMZN"})
        greeks_syms = {s for s, _ in fake.calls["greeks"]}
        self.assertEqual(greeks_syms, {"VST"})  # only the armed trigger name

    def test_per_symbol_exception_isolation(self):
        # Both trigger names armed; VST's greeks call explodes, AMZN survives.
        spots = {"VST": 150.0, "AMZN": 210.0, "MSFT": 400.0, "CEG": 300.0}
        fake = FakeClient(spots=spots, greeks_raises={"VST"})
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "unavailable")
        self.assertIn("RuntimeError", vst["note"])
        amzn = payload["symbols"]["AMZN"]
        self.assertEqual(amzn["status"], "ok")
        self.assertTrue(amzn["armed"])
        self.assertEqual(amzn["gates"]["liquidity"], "MET")

    def test_oi_failure_reads_liquidity_unknown(self):
        fake = FakeClient(spots=_entitled_spots(), oi_raises=True)
        with _patch_features([0.5] * 200):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "ok")
        self.assertEqual(vst["gates"]["liquidity"], "UNKNOWN")
        self.assertIsNone(vst["open_interest"])
        self.assertIsNone(vst["oi_label"])

    def test_expirations_and_oi_memoized_per_ny_date(self):
        fake = FakeClient(spots=_entitled_spots())
        with _patch_features([0.5] * 200):
            lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
            lq.refresh(client=fake, now_ny=NOW_NY + timedelta(minutes=5),
                       probe=_probe())
        self.assertEqual(fake.calls["expirations"], ["VST"])  # once, not twice
        self.assertEqual(len(fake.calls["oi"]), 1)
        self.assertEqual(len(fake.calls["greeks"]), 4)  # greeks NOT memoized
        self.assertEqual(fake.calls["stock"], 2)

    def test_schwab_oi_is_observed_from_each_new_snapshot_not_daily_memo(self):
        fake = FakeClient()
        fake.provider_name = "schwab"
        first, first_asof = lq._open_interest(
            fake, "VST", LEAPS_EXP, TODAY.isoformat()
        )
        second, second_asof = lq._open_interest(
            fake, "VST", LEAPS_EXP, TODAY.isoformat()
        )
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first_asof, TODAY.isoformat())
        self.assertEqual(second_asof, TODAY.isoformat())
        self.assertEqual(len(fake.calls["oi"]), 2)

    def test_missing_features_file_reads_ivr_unknown(self):
        fake = FakeClient(spots=_entitled_spots())

        def _raise(sym):
            raise FileNotFoundError(f"no features for {sym}")

        with mock.patch.object(lq.features, "load_features", _raise):
            payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "ok")
        self.assertEqual(vst["gates"]["ivr"], "UNKNOWN")

    def test_batched_stock_failure_marks_all_unavailable(self):
        fake = FakeClient(stock_raises=True)
        payload = lq.refresh(client=fake, now_ny=NOW_NY, probe=_probe())
        for sym in config.UNIVERSE:
            self.assertEqual(payload["symbols"][sym]["status"], "unavailable")
        self.assertEqual(fake.calls["greeks"], [])

    def test_full_payload_never_contains_fire(self):
        cases = []
        fake = FakeClient(spots=_entitled_spots())
        with _patch_features([0.5] * 200):
            cases.append(lq.refresh(client=fake, now_ny=NOW_NY,
                                    probe=_probe()))
        cases.append(lq.refresh(client=ExplodingClient(), now_ny=SATURDAY,
                                probe=_probe()))
        for payload in cases:
            self.assertNotIn("FIRE", json.dumps(payload))


class SessionEdgeSanityTests(unittest.TestCase):
    def test_fixture_dates_are_what_they_claim(self):
        self.assertEqual(TODAY.weekday(), 2)          # Wednesday
        self.assertEqual(SATURDAY.weekday(), 5)       # Saturday
        self.assertEqual(lq.SESSION_OPEN, time(9, 30))
        self.assertEqual(lq.SESSION_CLOSE, time(16, 0))


if __name__ == "__main__":
    unittest.main()

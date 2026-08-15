"""Gather-path tests for brief 12 (rev-2): D2/D2b (source choice + receipt
spot), D4b (in-memory session features, never the on-disk store), and the
owner-directed fresh-path name scope.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher import attractiveness_dashboard as ad
from options_researcher import schwab_chain_view as view
from tools.schwab_chain_manifest import build_manifest, write_manifest

SESSION = "2026-08-14"
DAY = "2026-08-14"          # Friday
EXPIRATION = "2026-09-18"   # 3rd Friday of September 2026 -> a real monthly
ATM_PUT_IV = 0.4772         # decimal, as the store already stores it
SPOT = 225.08


def _display_chain() -> pd.DataFrame:
    """A minimal but realistic display-schema chain for one monthly."""
    rows = []
    for strike, delta, iv, bid, ask in (
        (200.0, -0.20, 0.5310, 3.10, 3.20),
        (225.0, -0.50, ATM_PUT_IV, 9.80, 9.95),
    ):
        rows.append({"expiration": EXPIRATION, "strike": strike, "right": "P",
                     "bid": bid, "ask": ask, "open_interest": 4000, "iv": iv,
                     "delta": delta, "gamma": 0.01, "theta": -0.05,
                     "vega": 0.20})
    for strike, delta, iv, bid, ask in (
        (240.0, 0.40, 0.5100, 8.40, 8.55),
        (260.0, 0.20, 0.5600, 3.60, 3.70),
    ):
        rows.append({"expiration": EXPIRATION, "strike": strike, "right": "C",
                     "bid": bid, "ask": ask, "open_interest": 4000, "iv": iv,
                     "delta": delta, "gamma": 0.01, "theta": -0.05,
                     "vega": 0.20})
    return pd.DataFrame(rows)


def _store_frame() -> pd.DataFrame:
    """Store-schema frame (display columns plus the capture-only ones).

    Carries TWO expirations because ``verify_session`` refuses a package with
    fewer -- a one-expiration capture is a truncated chain.
    """
    second = _display_chain().assign(expiration="2026-10-16")
    frame = pd.concat([_display_chain(), second], ignore_index=True)
    frame.insert(3, "contract_symbol",
                 [f"X{index}" for index in range(len(frame))])
    frame["multiplier"] = 100.0
    frame["non_standard"] = False
    frame["mini"] = False
    frame["timestamp"] = pd.to_datetime([f"{SESSION}T19:45:32Z"] * len(frame))
    frame["trade_timestamp"] = pd.to_datetime([f"{SESSION}T19:40:00Z"] * len(frame))
    return frame


def write_schwab_store(root: Path, symbols: list[str], *,
                       session: str = SESSION, force: bool = False) -> None:
    """Write a byte-consistent capture package exactly as the writer does."""
    chain_dir = root / ".cache" / "schwab_chains"
    chain_dir.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        _store_frame().to_parquet(chain_dir / f"{symbol}_{session}.parquet")
    reports = root / "reports" / "schwab_chains" / session
    reports.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(session, sorted(symbols), chain_dir)
    write_manifest(manifest, reports / "manifest.json")
    receipt = {
        "receipt_kind": "schwab_chain_capture/v1",
        "session": session,
        "session_chain_convention": "preclose_snapshot_v1",
        "captured_at_et": f"{session}T15:45:10.701024-04:00",
        "scheduled_session_tag": "preclose",
        "force": force,
        "universe": sorted(symbols),
        "overall_status": "ok",
        "manifest_hash": manifest["manifest_hash"],
        "names": {
            symbol: {
                "status": "ok",
                "row_count": manifest["files"][symbol]["row_count"],
                "expiration_count": manifest["files"][symbol]["expiration_count"],
                "sha256": manifest["files"][symbol]["sha256"],
                "size_bytes": manifest["files"][symbol]["size_bytes"],
                "path": str(chain_dir / f"{symbol}_{session}.parquet"),
            }
            for symbol in sorted(symbols)
        },
    }
    (reports / "preclose.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def write_intraday_receipt(root: Path, records: dict[str, dict], *,
                           session: str = SESSION, force: bool = False) -> None:
    reports = root / "reports" / "intraday_capture" / session
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "preclose.json").write_text(json.dumps({
        "receipt_kind": "intraday_capture/v1",
        "session_tag": "preclose",
        "scheduled_et": "15:45",
        "force": force,
        "captured_at_et": f"{session}T15:45:13.597551-04:00",
        "universe": sorted(records),
        "names": records,
    }, indent=2) + "\n")


def _closes(end: str = "2026-08-04", value: float = 211.94) -> pd.Series:
    index = [d.date().isoformat() for d in pd.bdate_range(end=end, periods=40)]
    return pd.Series([value] * len(index), index=index, dtype=float)


class GatherSymbolSourceTests(unittest.TestCase):
    def _gather(self, **overrides):
        calls: dict[str, int] = {"load_features": 0}

        def load_features(_symbol):
            calls["load_features"] += 1
            raise AssertionError(
                "the on-disk feature store must not be read for a "
                "schwab-sourced section")

        kwargs = dict(
            holdings=pd.DataFrame({"symbol": pd.Series(dtype="str"),
                                   "shares": pd.Series(dtype="int"),
                                   "cost_basis": pd.Series(dtype="float")}),
            held_leaps={},
            csp_open_count=0,
            bucket_room=5000.0,
            v3_assertions=None,
            known_now=datetime.now(timezone.utc),
            load_closes=lambda *_a, **_k: _closes(),
            load_closes_adjusted=lambda *_a, **_k: _closes(),
            load_earnings=lambda _symbol: (_ for _ in ()).throw(
                FileNotFoundError("no curated csv")),
            load_features=load_features,
            load_fomc=lambda: [],
            apply_cycle_badges=lambda *_a, **_k: None,
            technical_snapshot=lambda _closes: {},
            technical_summary_line=lambda _tech: "",
            ladder_cards=__import__(
                "options_researcher.attractiveness", fromlist=["x"]).ladder_cards,
            put_card_rows=__import__(
                "options_researcher.attractiveness", fromlist=["x"]).put_card_rows,
            cc_card_rows=__import__(
                "options_researcher.attractiveness", fromlist=["x"]).cc_card_rows,
            pmcc_card_rows=__import__(
                "options_researcher.attractiveness", fromlist=["x"]).pmcc_card_rows,
            leaps_card_rows=__import__(
                "options_researcher.attractiveness", fromlist=["x"]).leaps_card_rows,
            long_call_card_rows=__import__(
                "options_researcher.attractiveness",
                fromlist=["x"]).long_call_card_rows,
            attach_oi_change=lambda *_a, **_k: None,
            date_cls=date,
            pd=pd,
            config=config,
        )
        kwargs.update(overrides)
        section, rv21 = ad._gather_symbol("NVDA", None, DAY, **kwargs)
        return section, rv21, calls

    def test_fresh_section_uses_the_receipt_spot_as_its_price(self):
        section, _rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=0.4960)

        self.assertEqual(section["chain_source"], "schwab_preclose")
        self.assertAlmostEqual(section["close"], SPOT)
        self.assertEqual(section["close_kind"], "preclose_mid_1545")
        self.assertEqual(section["close_as_of"], DAY)
        # The closes store is FAR behind the chain session; pairing them would
        # misprice moneyness. Both facts stay visible on the section.
        self.assertEqual(section["closes_as_of"], "2026-08-04")
        self.assertEqual(section["technicals_as_of"], "2026-08-04")

    def test_fresh_section_never_reads_the_registered_feature_store(self):
        # audit B4: .tmp/research/attractiveness is H5 entry_watch's input.
        section, _rv21, calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=0.4960)
        self.assertEqual(calls["load_features"], 0)
        self.assertEqual(section["features_source"], "schwab_preclose_session")
        self.assertEqual(section["features_as_of"], DAY)
        self.assertFalse(section["features_stale"])

    def test_fresh_section_writes_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                self._gather(chain_frame=_display_chain(),
                             chain_source=view.CHAIN_SOURCE,
                             preclose_spot=SPOT, iv_rank_preview=0.4960)
                created = sorted(p.name for p in Path(tmp).iterdir())
            finally:
                os.chdir(previous)
        self.assertEqual(created, [])

    def test_session_atm_iv_is_the_decimal_from_the_fresh_chain(self):
        section, _rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=0.4960)
        self.assertAlmostEqual(section["atm_iv"], ATM_PUT_IV, places=6)
        self.assertLess(section["atm_iv"], 1.0)

    def test_uncomputable_features_are_null_and_named(self):
        section, rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=0.4960)
        self.assertNotEqual(rv21, rv21)                     # NaN, not 0.0
        self.assertAlmostEqual(section["iv_rank"], 0.4960)
        self.assertEqual(section["iv_rank_label"],
                         "preview (capture-lane calibration)")
        fields = {item["field"] for item in section["feature_unavailable"]}
        self.assertEqual(fields, {"rv21", "iv_minus_rv"})
        for item in section["feature_unavailable"]:
            self.assertIn("2026-08-04", item["reason"])

    def test_missing_iv_rank_preview_is_unavailable_not_zero(self):
        section, _rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=None)
        self.assertNotEqual(section["iv_rank"], section["iv_rank"])
        self.assertIn("iv_rank",
                      {item["field"] for item in section["feature_unavailable"]})

    def test_cards_built_on_a_fresh_session_grade_unknown_not_green(self):
        section, _rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=0.4960)
        puts = [group for group in section["groups"]
                if group["kind"] == "put"][0]["cards"]
        self.assertTrue(puts)
        grades = puts[0]["grades"]
        self.assertEqual(grades["cushion"], "UNKNOWN")       # needs rv21
        self.assertEqual(grades["vrp_for_seller"], "UNKNOWN")  # needs iv_minus_rv
        self.assertNotIn("GREEN", (grades["cushion"], grades["vrp_for_seller"]))
        self.assertIn("UNAVAILABLE", puts[0]["verdict"])

    def test_long_call_iv_for_buyer_is_unknown_without_an_iv_rank(self):
        section, _rv21, _calls = self._gather(
            chain_frame=_display_chain(), chain_source=view.CHAIN_SOURCE,
            preclose_spot=SPOT, iv_rank_preview=None)
        calls = [group for group in section["groups"]
                 if group["kind"] == "long_call"][0]["cards"]
        self.assertTrue(calls)
        self.assertEqual(calls[0]["grades"]["iv_for_buyer"], "UNKNOWN")

    def test_thetadata_section_keeps_the_store_and_the_close(self):
        features = pd.DataFrame(
            {"close": [211.94], "rv21": [0.45], "atm_iv": [0.50],
             "iv_minus_rv": [0.05], "monthly_dte": [35.0], "iv_rank": [0.61],
             "earnings_week": [False]},
            index=pd.Index(["2026-08-04"], name="date"))
        seen: list[str] = []

        def load_features(symbol):
            seen.append(symbol)
            return features

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "NVDA_2026-08-04.parquet"
            _display_chain().to_parquet(path)
            section, rv21 = ad._gather_symbol(
                "NVDA", str(path), "2026-08-04",
                holdings=pd.DataFrame({"symbol": pd.Series(dtype="str"),
                                       "shares": pd.Series(dtype="int"),
                                       "cost_basis": pd.Series(dtype="float")}),
                held_leaps={}, csp_open_count=0, bucket_room=5000.0,
                v3_assertions=None, known_now=datetime.now(timezone.utc),
                load_closes=lambda *_a, **_k: _closes(),
                load_closes_adjusted=lambda *_a, **_k: _closes(),
                load_earnings=lambda _s: (_ for _ in ()).throw(
                    FileNotFoundError("none")),
                load_features=load_features,
                load_fomc=lambda: [],
                apply_cycle_badges=lambda *_a, **_k: None,
                technical_snapshot=lambda _c: {},
                technical_summary_line=lambda _t: "",
                ladder_cards=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).ladder_cards,
                put_card_rows=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).put_card_rows,
                cc_card_rows=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).cc_card_rows,
                pmcc_card_rows=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).pmcc_card_rows,
                leaps_card_rows=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).leaps_card_rows,
                long_call_card_rows=__import__(
                    "options_researcher.attractiveness",
                    fromlist=["x"]).long_call_card_rows,
                attach_oi_change=lambda *_a, **_k: None,
                date_cls=date, pd=pd, config=config)

        self.assertEqual(seen, ["NVDA"])
        self.assertEqual(section["chain_source"], "thetadata_eod")
        self.assertEqual(section["close_kind"], "eod_close")
        self.assertAlmostEqual(section["close"], 211.94)
        self.assertAlmostEqual(rv21, 0.45)
        self.assertAlmostEqual(section["iv_rank"], 0.61)
        self.assertEqual(section["feature_unavailable"], [])


class ThetadataFailClosedTests(unittest.TestCase):
    """D4a: the frozen-cache path must not coerce a null feature either."""

    def _gather_with(self, features: pd.DataFrame):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"NVDA_{DAY}.parquet"
            _display_chain().to_parquet(path)
            attractiveness = __import__("options_researcher.attractiveness",
                                        fromlist=["x"])
            return ad._gather_symbol(
                "NVDA", str(path), DAY,
                holdings=pd.DataFrame({"symbol": pd.Series(dtype="str"),
                                       "shares": pd.Series(dtype="int"),
                                       "cost_basis": pd.Series(dtype="float")}),
                held_leaps={}, csp_open_count=0, bucket_room=5000.0,
                v3_assertions=None, known_now=datetime.now(timezone.utc),
                load_closes=lambda *_a, **_k: _closes(),
                load_closes_adjusted=lambda *_a, **_k: _closes(),
                load_earnings=lambda _s: (_ for _ in ()).throw(
                    FileNotFoundError("none")),
                load_features=lambda _s: features,
                load_fomc=lambda: [],
                apply_cycle_badges=lambda *_a, **_k: None,
                technical_snapshot=lambda _c: {},
                technical_summary_line=lambda _t: "",
                ladder_cards=attractiveness.ladder_cards,
                put_card_rows=attractiveness.put_card_rows,
                cc_card_rows=attractiveness.cc_card_rows,
                pmcc_card_rows=attractiveness.pmcc_card_rows,
                leaps_card_rows=attractiveness.leaps_card_rows,
                long_call_card_rows=attractiveness.long_call_card_rows,
                attach_oi_change=lambda *_a, **_k: None,
                date_cls=date, pd=pd, config=config)

    def test_a_null_feature_row_stays_null_and_is_named(self):
        nan = float("nan")
        features = pd.DataFrame(
            {"close": [211.94], "rv21": [nan], "atm_iv": [nan],
             "iv_minus_rv": [nan], "monthly_dte": [35.0], "iv_rank": [nan],
             "earnings_week": [False]},
            index=pd.Index([DAY], name="date"))
        section, rv21 = self._gather_with(features)

        self.assertNotEqual(section["iv_rank"], section["iv_rank"])
        self.assertNotEqual(rv21, rv21)
        self.assertEqual(
            {item["field"] for item in section["feature_unavailable"]},
            {"rv21", "iv_rank", "iv_minus_rv"})
        for item in section["feature_unavailable"]:
            self.assertIn(f"{DAY} feature row", item["reason"])

    def test_a_null_feature_row_grades_unknown_not_green(self):
        nan = float("nan")
        features = pd.DataFrame(
            {"close": [211.94], "rv21": [nan], "atm_iv": [nan],
             "iv_minus_rv": [nan], "monthly_dte": [35.0], "iv_rank": [nan],
             "earnings_week": [False]},
            index=pd.Index([DAY], name="date"))
        section, _rv21 = self._gather_with(features)
        grades = {group["kind"]: group["cards"][0]["grades"]
                  for group in section["groups"] if group["cards"]}
        self.assertEqual(grades["put"]["iv_for_seller"], "UNKNOWN")
        self.assertEqual(grades["put"]["vrp_for_seller"], "UNKNOWN")
        self.assertEqual(grades["put"]["cushion"], "UNKNOWN")
        self.assertEqual(grades["long_call"]["iv_for_buyer"], "UNKNOWN")


class GatherAllSourceSelectionTests(unittest.TestCase):
    """The newer of (frozen cache, verified pre-close) wins -- with a spot."""

    def setUp(self):
        view._reset_memo_for_tests()
        self.addCleanup(view._reset_memo_for_tests)

    def _run(self, root: Path, universe: list[str]):
        seen: list[dict] = []

        def spy(symbol, chain_path, day, **kwargs):
            seen.append({"symbol": symbol, "day": day,
                         "chain_path": chain_path,
                         "chain_source": kwargs.get("chain_source"),
                         "preclose_spot": kwargs.get("preclose_spot"),
                         "has_frame": kwargs.get("chain_frame") is not None,
                         "refusal": kwargs.get("fresh_refusal_reason")})
            return ({"symbol": symbol, "as_of": day, "close": 1.0,
                     "iv_rank": 0.5, "groups": []}, 1.0)

        (root / "data" / "positions").mkdir(parents=True, exist_ok=True)
        from options_researcher.portfolio import _FIELDS

        (root / "data" / "positions" / "positions.csv").write_text(
            ",".join(_FIELDS) + "\n")
        previous = os.getcwd()
        os.chdir(root)
        try:
            with (
                mock.patch.object(config, "ATTRACTIVENESS_UNIVERSE", universe),
                mock.patch.object(config, "ATTRACTIVENESS_EXTRA_NAMES", []),
                mock.patch.object(ad, "_gather_symbol", side_effect=spy),
            ):
                sections, _rv21, blocked, state = ad._gather_all()
        finally:
            os.chdir(previous)
        return seen, sections, blocked, state

    def test_verified_fresh_session_beats_the_frozen_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_schwab_store(root, ["NVDA"])
            write_intraday_receipt(root, {"NVDA": {"symbol": "NVDA",
                                                   "status": "ok",
                                                   "spot_mid": SPOT,
                                                   "spot_source": "stock_snapshot",
                                                   "spot_ts": f"{SESSION}T19:45:15Z",
                                                   "iv_rank_preview": 0.31}})
            cache = root / ".cache" / "chains"
            cache.mkdir(parents=True, exist_ok=True)
            _display_chain().to_parquet(cache / "NVDA_2026-07-27.parquet")
            seen, sections, blocked, state = self._run(root, ["NVDA"])

        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["day"], SESSION)
        self.assertEqual(seen[0]["chain_source"], "schwab_preclose")
        self.assertTrue(seen[0]["has_frame"])
        self.assertIsNone(seen[0]["chain_path"])
        self.assertAlmostEqual(seen[0]["preclose_spot"], SPOT)
        self.assertEqual(state["verified_sessions"], [SESSION])
        self.assertEqual(blocked, [])

    def test_owner_excluded_names_never_take_the_fresh_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_schwab_store(root, ["ET", "NVDA", "USAR"])
            write_intraday_receipt(root, {
                name: {"symbol": name, "status": "ok", "spot_mid": SPOT,
                       "spot_source": "stock_snapshot",
                       "spot_ts": f"{SESSION}T19:45:15Z"}
                for name in ("ET", "NVDA", "USAR")})
            cache = root / ".cache" / "chains"
            cache.mkdir(parents=True, exist_ok=True)
            for name in ("ET", "NVDA", "USAR"):
                _display_chain().to_parquet(cache / f"{name}_2026-07-27.parquet")
            seen, _sections, blocked, _state = self._run(
                root, ["ET", "NVDA", "USAR"])

        by_symbol = {item["symbol"]: item for item in seen}
        self.assertEqual(by_symbol["NVDA"]["chain_source"], "schwab_preclose")
        # Excluded from the FRESH path only -- still rendered, from the frozen
        # cache, with its own honest older date. Never silently dropped.
        for name in ("ET", "USAR"):
            self.assertEqual(by_symbol[name]["chain_source"], "thetadata_eod")
            self.assertEqual(by_symbol[name]["day"], "2026-07-27")
        self.assertEqual(blocked, [])

    def test_a_fresh_chain_without_a_verified_spot_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_schwab_store(root, ["NVDA"])
            write_intraday_receipt(root, {"NVDA": {"symbol": "NVDA",
                                                   "status": "ok",
                                                   "spot_mid": SPOT,
                                                   "spot_source": "parity",
                                                   "spot_ts": ""}})
            cache = root / ".cache" / "chains"
            cache.mkdir(parents=True, exist_ok=True)
            _display_chain().to_parquet(cache / "NVDA_2026-07-27.parquet")
            seen, _sections, blocked, _state = self._run(root, ["NVDA"])

        self.assertEqual(seen[0]["chain_source"], "thetadata_eod")
        self.assertEqual(seen[0]["day"], "2026-07-27")
        self.assertIn("no verified 15:45 spot", seen[0]["refusal"])
        self.assertEqual(blocked, [])

    def test_an_unverifiable_session_is_reported_and_unused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_schwab_store(root, ["NVDA"], force=True)
            write_intraday_receipt(root, {"NVDA": {"symbol": "NVDA",
                                                   "status": "ok",
                                                   "spot_mid": SPOT,
                                                   "spot_source": "stock_snapshot",
                                                   "spot_ts": ""}})
            cache = root / ".cache" / "chains"
            cache.mkdir(parents=True, exist_ok=True)
            _display_chain().to_parquet(cache / "NVDA_2026-07-27.parquet")
            seen, _sections, _blocked, state = self._run(root, ["NVDA"])

        self.assertEqual(seen[0]["chain_source"], "thetadata_eod")
        self.assertEqual(state["verified_sessions"], [])
        self.assertEqual(len(state["failures"]), 1)
        self.assertEqual(state["failures"][0]["session"], SESSION)
        self.assertTrue(state["receipts_found"])

    def test_no_receipts_at_all_is_recorded_as_such(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / ".cache" / "chains"
            cache.mkdir(parents=True, exist_ok=True)
            _display_chain().to_parquet(cache / "NVDA_2026-07-27.parquet")
            _seen, _sections, _blocked, state = self._run(root, ["NVDA"])
        self.assertFalse(state["receipts_found"])
        self.assertEqual(state["failures"], [])

    def test_a_name_with_neither_source_is_blocked_visibly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_schwab_store(root, ["NVDA"])
            write_intraday_receipt(root, {"NVDA": {"symbol": "NVDA",
                                                   "status": "ok",
                                                   "spot_mid": SPOT,
                                                   "spot_source": "stock_snapshot",
                                                   "spot_ts": ""}})
            _seen, _sections, blocked, _state = self._run(root, ["NVDA", "MSFT"])
        self.assertEqual([rec["symbol"] for rec in blocked], ["MSFT"])
        self.assertEqual(blocked[0]["reason_code"], "NO_CACHED_CHAINS")


class FixtureSelfCheck(unittest.TestCase):
    def test_fixture_chain_has_a_real_monthly_in_the_dte_band(self):
        from options_researcher.chains import nearest_monthly

        self.assertEqual(
            nearest_monthly(_display_chain(), date.fromisoformat(DAY)),
            date.fromisoformat(EXPIRATION))

    def test_receipt_fixture_matches_the_reader_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_intraday_receipt(root, {"NVDA": {"symbol": "NVDA",
                                                   "status": "ok",
                                                   "spot_mid": SPOT,
                                                   "spot_source": "stock_snapshot",
                                                   "spot_ts": ""}})
            payload = json.loads(
                (root / "reports" / "intraday_capture" / SESSION
                 / "preclose.json").read_text())
        self.assertEqual(payload["receipt_kind"], "intraday_capture/v1")
        self.assertIs(payload["force"], False)


if __name__ == "__main__":
    unittest.main()

"""Offline tests for the verified-only Schwab display view (brief 12 D1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from options_researcher import schwab_chain_view as view
from tools.schwab_chain_manifest import build_manifest, write_manifest

SESSION = "2026-08-14"
CAPTURED_AT = f"{SESSION}T15:45:10.701024-04:00"

# Real magnitudes measured in the ops store (NVDA/AMD 2026-08-14): the stored
# ``iv`` is already a decimal fraction, so 0.57530 means 57.53% implied vol.
REAL_IV = 0.57530
DEEP_ITM_IV = 59.57637   # a real garbage IV on a delta-1.0, zero-vega contract


def _chain_frame(*, iv: float = REAL_IV, rows: int = 4) -> pd.DataFrame:
    base = {
        "expiration": ["2026-09-18", "2026-09-18", "2026-10-16", "2026-10-16"],
        "strike": [100.0, 100.0, 110.0, 110.0],
        "right": ["C", "P", "C", "P"],
        "contract_symbol": ["A1", "A2", "A3", "A4"],
        "bid": [5.0, 4.0, 3.0, 2.0],
        "ask": [5.2, 4.2, 3.2, 2.2],
        "open_interest": [500, 400, 300, 200],
        "iv": [iv, iv + 0.01, iv + 0.02, iv + 0.03],
        "delta": [0.5, -0.5, 0.4, -0.4],
        "gamma": [0.01, 0.01, 0.02, 0.02],
        "theta": [-0.05, -0.05, -0.04, -0.04],
        "vega": [0.20, 0.20, 0.18, 0.18],
        "multiplier": [100.0] * 4,
        "non_standard": [False] * 4,
        "mini": [False] * 4,
        "timestamp": pd.to_datetime([f"{SESSION}T19:45:32Z"] * 4),
        "trade_timestamp": pd.to_datetime([f"{SESSION}T19:40:00Z"] * 4),
    }
    frame = pd.DataFrame(base)
    return frame.head(rows)


def _write_store(root: Path, symbols: list[str], *, session: str = SESSION,
                 force: bool = False,
                 frames: dict[str, pd.DataFrame] | None = None) -> None:
    """Write a byte-consistent capture package exactly as the writer does."""
    chain_dir = root / ".cache" / "schwab_chains"
    chain_dir.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        frame = (frames or {}).get(symbol)
        if frame is None:
            frame = _chain_frame()
        frame.to_parquet(chain_dir / f"{symbol}_{session}.parquet")

    reports = root / "reports" / "schwab_chains" / session
    reports.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(session, sorted(symbols), chain_dir)
    write_manifest(manifest, reports / "manifest.json")

    names = {
        symbol: {
            "status": "ok",
            "row_count": manifest["files"][symbol]["row_count"],
            "expiration_count": manifest["files"][symbol]["expiration_count"],
            "sha256": manifest["files"][symbol]["sha256"],
            "size_bytes": manifest["files"][symbol]["size_bytes"],
            "path": str(chain_dir / f"{symbol}_{session}.parquet"),
        }
        for symbol in sorted(symbols)
    }
    receipt = {
        "receipt_kind": "schwab_chain_capture/v1",
        "session": session,
        "session_chain_convention": "preclose_snapshot_v1",
        "captured_at_et": f"{session}T15:45:10.701024-04:00",
        "scheduled_session_tag": "preclose",
        "force": force,
        "universe": sorted(symbols),
        "overall_status": "ok",
        "names": names,
        "manifest_hash": manifest["manifest_hash"],
    }
    (reports / "preclose.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n")


def _write_intraday_receipt(root: Path, records: dict[str, dict], *,
                            session: str = SESSION, force: bool = False) -> None:
    reports = root / "reports" / "intraday_capture" / session
    reports.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_kind": "intraday_capture/v1",
        "session_tag": "preclose",
        "scheduled_et": "15:45",
        "force": force,
        "captured_at_et": CAPTURED_AT,
        "universe": sorted(records),
        "names": records,
    }
    (reports / "preclose.json").write_text(json.dumps(receipt, indent=2) + "\n")


def _spot_record(symbol: str, spot: float = 101.25, **overrides) -> dict:
    record = {
        "symbol": symbol,
        "status": "ok",
        "spot_mid": spot,
        "spot_bid": spot - 0.02,
        "spot_ask": spot + 0.02,
        "spot_source": "stock_snapshot",
        "spot_ts": f"{SESSION}T19:45:15.866000+00:00",
        "iv_rank_preview": 0.4960,
    }
    record.update(overrides)
    return record


class SchwabChainViewTests(unittest.TestCase):
    def setUp(self):
        view._reset_memo_for_tests()
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.chain_dir = self.root / ".cache" / "schwab_chains"
        self.reports_dir = self.root / "reports" / "schwab_chains"
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(view._reset_memo_for_tests)

    def _dirs(self) -> dict:
        return {"chain_dir": self.chain_dir, "reports_dir": self.reports_dir}

    # --- verification ----------------------------------------------------
    def test_verified_session_is_listed_with_its_manifest_universe(self):
        _write_store(self.root, ["ET", "NVDA", "VST"])
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, [SESSION])
        self.assertEqual(failures, [])
        self.assertEqual(
            view.session_symbols(SESSION, **self._dirs()), ["ET", "NVDA", "VST"])

    def test_no_receipts_is_distinguishable_from_a_failure(self):
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual((sessions, failures), ([], []))

    def test_tampered_chain_bytes_make_the_session_absent_and_loud(self):
        _write_store(self.root, ["NVDA"])
        target = self.chain_dir / f"NVDA_{SESSION}.parquet"
        _chain_frame(iv=REAL_IV + 0.05).to_parquet(target)
        view._reset_memo_for_tests()

        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, [])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0][0], SESSION)
        self.assertIn("hash mismatch", failures[0][1])
        self.assertIsNone(view.newest_chain("NVDA", **self._dirs()))

    def test_forced_receipt_is_refused(self):
        _write_store(self.root, ["NVDA"], force=True)
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, [])
        self.assertIn("force must be false", failures[0][1])
        self.assertIsNone(view.newest_chain("NVDA", **self._dirs()))

    def test_verification_uses_the_manifests_own_universe_not_a_fixed_list(self):
        # A session captured with a universe unlike today's watchlist must
        # still verify on its own terms, else the whole path is a silent no-op.
        _write_store(self.root, ["AAAA", "BBBB"])
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual((sessions, failures), ([SESSION], []))
        self.assertIsNotNone(view.newest_chain("AAAA", **self._dirs()))

    def test_unreadable_manifest_is_a_visible_failure(self):
        _write_store(self.root, ["NVDA"])
        (self.reports_dir / SESSION / "manifest.json").write_text("{not json")
        view._reset_memo_for_tests()
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, [])
        self.assertEqual(failures[0][0], SESSION)

    def test_non_canonical_session_directory_is_not_a_session(self):
        _write_store(self.root, ["NVDA"])
        stray = self.reports_dir / "latest"
        stray.mkdir(parents=True, exist_ok=True)
        (stray / "preclose.json").write_text("{}")
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual((sessions, failures), ([SESSION], []))

    # --- chain frame -----------------------------------------------------
    def test_iv_is_passed_through_as_the_decimal_it_already_is(self):
        # data/schwab_adapter.py:148-154 already divides Schwab's percentage
        # points by 100 at capture. A second conversion here would render a
        # 57.5% implied vol as 0.575% and corrupt every IV badge.
        _write_store(self.root, ["NVDA"])
        frame, session = view.newest_chain("NVDA", **self._dirs())
        self.assertEqual(session, SESSION)
        self.assertAlmostEqual(float(frame["iv"].iloc[0]), REAL_IV, places=9)
        self.assertGreater(float(frame["iv"].median()), 0.05)
        self.assertLess(float(frame["iv"].median()), 5.0)

    def test_a_deep_itm_garbage_iv_is_not_evidence_of_percent_units(self):
        frame = _chain_frame()
        frame.loc[0, "iv"] = DEEP_ITM_IV
        _write_store(self.root, ["NVDA"], frames={"NVDA": frame})
        loaded, _session = view.newest_chain("NVDA", **self._dirs())
        self.assertAlmostEqual(float(loaded["iv"].iloc[0]), DEEP_ITM_IV, places=6)
        self.assertAlmostEqual(float(loaded["iv"].iloc[1]), REAL_IV + 0.01, places=9)

    def test_non_standard_and_mini_rows_are_dropped(self):
        frame = _chain_frame()
        frame.loc[0, "non_standard"] = True
        frame.loc[1, "mini"] = True
        _write_store(self.root, ["NVDA"], frames={"NVDA": frame})
        loaded, _session = view.newest_chain("NVDA", **self._dirs())
        self.assertEqual(len(loaded), 2)
        self.assertEqual(sorted(loaded["strike"].unique().tolist()), [110.0])

    def test_display_schema_keeps_the_full_greek_set(self):
        _write_store(self.root, ["NVDA"])
        loaded, _session = view.newest_chain("NVDA", **self._dirs())
        self.assertEqual(list(loaded.columns), view.DISPLAY_COLUMNS)
        for column in ("gamma", "theta", "vega", "delta"):
            self.assertIn(column, loaded.columns)
        self.assertEqual(loaded["open_interest"].dtype.kind, "i")

    def test_thetadata_column_parity(self):
        # The frame stands in for a .cache/chains frame; every column the
        # display path reads from ThetaData must be present.
        _write_store(self.root, ["NVDA"])
        loaded, _session = view.newest_chain("NVDA", **self._dirs())
        thetadata_columns = ["expiration", "strike", "right", "bid", "ask",
                             "open_interest", "iv", "delta", "gamma", "theta",
                             "vega"]
        self.assertEqual([c for c in loaded.columns if c in thetadata_columns],
                         thetadata_columns)

    # --- owner name scope ------------------------------------------------
    def test_display_excluded_names_have_no_fresh_path(self):
        _write_store(self.root, ["ET", "NVDA", "USAR"])
        self.assertEqual(view.DISPLAY_EXCLUDED_SYMBOLS, frozenset({"ET", "USAR"}))
        self.assertIsNone(view.newest_chain("ET", **self._dirs()))
        self.assertIsNone(view.newest_chain("USAR", **self._dirs()))
        self.assertIsNotNone(view.newest_chain("NVDA", **self._dirs()))

    def test_exclusion_applies_after_verification_not_before(self):
        # ET is part of the captured universe; excluding it must not make the
        # session unverifiable for everyone else.
        _write_store(self.root, ["ET", "NVDA"])
        sessions, _failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, [SESSION])
        self.assertIn("ET", view.session_symbols(SESSION, **self._dirs()))

    def test_symbol_absent_from_the_session_has_no_fresh_chain(self):
        _write_store(self.root, ["NVDA"])
        self.assertIsNone(view.newest_chain("MSFT", **self._dirs()))

    def test_newest_verified_session_wins(self):
        _write_store(self.root, ["NVDA"], session="2026-08-13")
        _write_store(self.root, ["NVDA"], session=SESSION)
        _frame, session = view.newest_chain("NVDA", **self._dirs())
        self.assertEqual(session, SESSION)

    def test_newest_session_that_fails_verification_falls_back_to_nothing(self):
        # An unverifiable newer session must not silently promote an older one
        # while the page still claims the newer date; the failure is reported
        # and the older verified session is used with its own honest date.
        _write_store(self.root, ["NVDA"], session="2026-08-13")
        _write_store(self.root, ["NVDA"], session=SESSION, force=True)
        sessions, failures = view.verified_sessions(**self._dirs())
        self.assertEqual(sessions, ["2026-08-13"])
        self.assertEqual([f[0] for f in failures], [SESSION])
        _frame, session = view.newest_chain("NVDA", **self._dirs())
        self.assertEqual(session, "2026-08-13")

    # --- spot ------------------------------------------------------------
    def test_preclose_spot_reads_the_intraday_receipt(self):
        _write_intraday_receipt(self.root, {"NVDA": _spot_record("NVDA", 225.08)})
        spot, timestamp = view.load_preclose_spot(
            "NVDA", SESSION, reports_dir=self.root / "reports" / "intraday_capture")
        self.assertAlmostEqual(spot, 225.08)
        self.assertTrue(timestamp.startswith(SESSION))

    def test_preclose_spot_refuses_parity_fallback_and_failed_names(self):
        _write_intraday_receipt(self.root, {
            "AAA": _spot_record("AAA", spot_source="parity"),
            "BBB": _spot_record("BBB", status="failed"),
            "CCC": _spot_record("CCC", spot_mid=None),
            "DDD": _spot_record("DDD", spot_mid=0.0),
        })
        reports = self.root / "reports" / "intraday_capture"
        for symbol in ("AAA", "BBB", "CCC", "DDD"):
            self.assertIsNone(
                view.load_preclose_spot(symbol, SESSION, reports_dir=reports),
                symbol)

    def test_preclose_spot_refuses_a_forced_receipt(self):
        _write_intraday_receipt(
            self.root, {"NVDA": _spot_record("NVDA")}, force=True)
        self.assertIsNone(view.load_preclose_spot(
            "NVDA", SESSION,
            reports_dir=self.root / "reports" / "intraday_capture"))

    def test_preclose_spot_is_absent_for_a_session_with_no_receipt(self):
        self.assertIsNone(view.load_preclose_spot(
            "NVDA", "2026-08-13",
            reports_dir=self.root / "reports" / "intraday_capture"))

    def test_iv_rank_preview_is_read_only_when_in_range(self):
        _write_intraday_receipt(self.root, {
            "AAA": _spot_record("AAA"),
            "BBB": _spot_record("BBB", iv_rank_preview=None),
            "CCC": _spot_record("CCC", iv_rank_preview=1.4),
        })
        reports = self.root / "reports" / "intraday_capture"
        self.assertAlmostEqual(
            view.preclose_iv_rank_preview("AAA", SESSION, reports_dir=reports),
            0.4960)
        self.assertIsNone(
            view.preclose_iv_rank_preview("BBB", SESSION, reports_dir=reports))
        self.assertIsNone(
            view.preclose_iv_rank_preview("CCC", SESSION, reports_dir=reports))

    # --- labels ----------------------------------------------------------
    def test_convention_label_is_never_a_close(self):
        self.assertEqual(view.CONVENTION_LABEL, "15:45 pre-close (Schwab)")
        self.assertEqual(view.as_of_label(SESSION),
                         f"{SESSION} · 15:45 pre-close (Schwab)")
        self.assertNotIn("close —", view.as_of_label(SESSION))
        self.assertEqual(view.CLOSE_KIND, "preclose_mid_1545")

    def test_memo_does_not_leak_across_a_cwd_change(self):
        _write_store(self.root, ["NVDA"])
        self.assertEqual(view.verified_sessions(**self._dirs())[0], [SESSION])
        with tempfile.TemporaryDirectory() as other:
            import os

            previous = os.getcwd()
            os.chdir(other)
            try:
                relative = view.verified_sessions(
                    chain_dir=Path(".cache/schwab_chains"),
                    reports_dir=Path("reports/schwab_chains"))
            finally:
                os.chdir(previous)
        self.assertEqual(relative, ([], []))


if __name__ == "__main__":
    unittest.main()

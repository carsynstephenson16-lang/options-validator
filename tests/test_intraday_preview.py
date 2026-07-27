"""Offline tests for receipt-backed descriptive dashboard previews."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from options_researcher import intraday_preview
from research.hashing import config_hash

NY = ZoneInfo("America/New_York")


def _receipt(now_ny: datetime, tag: str, *, force: bool = False) -> dict:
    captured_utc = now_ny.astimezone(ZoneInfo("UTC"))
    names = {
        symbol: {
            "symbol": symbol,
            "status": "ok",
            "spot_mid": 100.0 + index,
            "spot_source": "parity_fallback",
            "atm_iv": 0.4,
            "iv_rank_preview": None,
            "iv_label": "solver-derived, not rank-comparable",
        }
        for index, symbol in enumerate(config.ATTRACTIVENESS_UNIVERSE)
    }
    return {
        "receipt_kind": "intraday_capture/v1",
        "session_tag": tag,
        "scheduled_et": config.INTRADAY_CAPTURE_TIMES[tag],
        "captured_at_et": now_ny.isoformat(),
        "captured_at_utc": captured_utc.isoformat(),
        "force": force,
        "universe": list(config.ATTRACTIVENESS_UNIVERSE),
        "config_hash": config_hash(),
        "names": names,
    }


def _write_receipt(root: Path, receipt: dict) -> Path:
    day = receipt["captured_at_et"][:10]
    path = root / day / f"{receipt['session_tag']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt), encoding="utf-8")
    return path


def _off_payload() -> dict:
    return {
        "generated_at_utc": "2026-07-27T17:20:00+00:00",
        "session_state": "open",
        "probe": {"ok": False, "reason": "greeks endpoint not entitled"},
        "symbols": {
            "VST": {"status": "off", "note": "probe unavailable"},
        },
    }


class CurrentReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 7, 27, 13, 20, tzinfo=NY)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_newest_required_slot_is_loaded(self):
        receipt = _receipt(
            datetime(2026, 7, 27, 13, 0, 19, tzinfo=NY), "midday"
        )
        path = _write_receipt(self.root, receipt)

        actual, actual_path, reason = intraday_preview.load_current_receipt(
            now_ny=self.now, receipt_dir=self.root
        )

        self.assertEqual(reason, "ok")
        self.assertEqual(actual, receipt)
        self.assertEqual(actual_path, path)

    def test_older_slot_is_rejected_after_latest_grace_window(self):
        _write_receipt(
            self.root,
            _receipt(
                datetime(2026, 7, 27, 11, 0, 12, tzinfo=NY),
                "midmorning",
            ),
        )

        actual, path, reason = intraday_preview.load_current_receipt(
            now_ny=self.now, receipt_dir=self.root
        )

        self.assertIsNone(actual)
        self.assertIsNone(path)
        self.assertIn("latest required slot midday is missing", reason)

    def test_forced_receipt_is_not_eligible(self):
        _write_receipt(
            self.root,
            _receipt(
                datetime(2026, 7, 27, 13, 0, 19, tzinfo=NY),
                "midday",
                force=True,
            ),
        )

        actual, path, reason = intraday_preview.load_current_receipt(
            now_ny=self.now, receipt_dir=self.root
        )

        self.assertIsNone(actual)
        self.assertIsNone(path)
        self.assertIn("forced receipts are not eligible", reason)

    def test_stale_config_identity_is_rejected(self):
        receipt = _receipt(
            datetime(2026, 7, 27, 13, 0, 19, tzinfo=NY), "midday"
        )
        receipt["config_hash"] = "0" * 64
        _write_receipt(self.root, receipt)

        actual, path, reason = intraday_preview.load_current_receipt(
            now_ny=self.now, receipt_dir=self.root
        )

        self.assertIsNone(actual)
        self.assertIsNone(path)
        self.assertIn("config identity is stale", reason)


class FallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 7, 27, 13, 20, tzinfo=NY)
        self.receipt = _receipt(
            datetime(2026, 7, 27, 13, 0, 19, tzinfo=NY), "midday"
        )
        _write_receipt(self.root, self.receipt)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_receipt_fallback_is_descriptive_and_current_day(self):
        payload = intraday_preview.refresh_with_receipt_fallback(
            live_refresh=_off_payload,
            now_ny=self.now,
            receipt_dir=self.root,
        )

        self.assertEqual(payload["freshness"]["status"], "CURRENT")
        self.assertEqual(
            payload["freshness"]["source"], "intraday_capture/v1"
        )
        self.assertTrue(payload["freshness"]["descriptive_only"])
        self.assertEqual(payload["freshness"]["session_tag"], "midday")
        self.assertEqual(
            set(payload["symbols"]), set(config.ATTRACTIVENESS_UNIVERSE)
        )
        vst = payload["symbols"]["VST"]
        self.assertEqual(vst["status"], "ok")
        self.assertEqual(vst["spot_source"], "option-parity estimate")
        for forbidden in ("trigger", "armed", "gates", "verdict"):
            self.assertNotIn(forbidden, vst)

    def test_healthy_direct_adapter_remains_preferred(self):
        primary = {
            "generated_at_utc": "2026-07-27T17:20:00+00:00",
            "session_state": "open",
            "probe": {"ok": True, "reason": "ok"},
            "symbols": {"VST": {"status": "ok", "spot": 160.0}},
        }

        payload = intraday_preview.refresh_with_receipt_fallback(
            live_refresh=lambda: primary,
            now_ny=self.now,
            receipt_dir=self.root,
        )

        self.assertIs(payload, primary)
        self.assertEqual(
            payload["freshness"]["source"], "direct_live_adapter"
        )

    def test_missing_current_receipt_keeps_live_adapter_off(self):
        empty = Path(self.temp.name) / "empty"
        payload = intraday_preview.refresh_with_receipt_fallback(
            live_refresh=_off_payload,
            now_ny=self.now,
            receipt_dir=empty,
        )

        self.assertEqual(payload["symbols"]["VST"]["status"], "off")
        self.assertEqual(payload["freshness"]["status"], "UNAVAILABLE")
        self.assertIn("no current-day", payload["receipt_fallback"]["reason"])


if __name__ == "__main__":
    unittest.main()

"""Brief 36 WP-E absolute quote-age gate tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from data.cache_runner import session_close_utc
from options_researcher import h7_schwab_data_gate as data_gate
from options_researcher import h7_schwab_quote_age_gate as gate
from options_researcher import schwab_quote_age_report as quote_age_report
from research.hashing import sha256_file
from tools import schwab_chain_manifest as manifest

SESSION = "2026-08-10"
SYMBOLS = ("AAA", "BBB")


def _chain_frame(timestamp: object, *, trade_timestamp: object = "not-used") -> pd.DataFrame:
    """A two-expiration liquid package with one selectable timestamp per row."""
    return pd.DataFrame(
        [
            {
                "expiration": expiration,
                "strike": 100.0,
                "right": "C",
                "bid": 1.0,
                "ask": 1.05,
                "open_interest": 100,
                "delta": 0.40,
                "timestamp": timestamp,
                "trade_timestamp": trade_timestamp,
            }
            for expiration in ("2026-08-21", "2026-09-18")
        ]
    )


class SchwabQuoteAgeGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.chain_dir = self.root / "chains"
        self.report_dir = self.root / "reports" / SESSION
        self.chain_dir.mkdir()
        self.report_dir.mkdir(parents=True)
        self.reference = pd.Timestamp(session_close_utc(SESSION))
        self._replace_package({"AAA": 5.0, "BBB": 16.0})

    @property
    def manifest_path(self) -> Path:
        return self.report_dir / "manifest.json"

    @property
    def receipt_path(self) -> Path:
        return self.report_dir / "preclose.json"

    @property
    def sidecar_path(self) -> Path:
        return self.report_dir / "preclose.quote_age.json"

    def _replace_package(
        self,
        ages: dict[str, float],
        *,
        timestamps: dict[str, object] | None = None,
    ) -> None:
        """Create a complete freshly manifest-bound package in the temp fixture."""
        for path in (self.manifest_path, self.receipt_path):
            if path.exists():
                path.unlink()
        for symbol in SYMBOLS:
            value = (
                timestamps[symbol]
                if timestamps is not None
                else self.reference - pd.Timedelta(minutes=ages[symbol])
            )
            _chain_frame(value).to_parquet(self.chain_dir / f"{symbol}_{SESSION}.parquet")
        built = manifest.build_manifest(SESSION, list(SYMBOLS), self.chain_dir)
        manifest.write_manifest(built, self.manifest_path)
        names = {}
        for symbol in SYMBOLS:
            path = self.chain_dir / f"{symbol}_{SESSION}.parquet"
            frame = pd.read_parquet(path)
            names[symbol] = {
                "status": "ok",
                "row_count": len(frame),
                "expiration_count": int(frame["expiration"].nunique()),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        self.receipt_path.write_text(
            json.dumps(
                {
                    "receipt_kind": "schwab_chain_capture/v1",
                    "session": SESSION,
                    "session_chain_convention": "preclose_snapshot_v1",
                    "captured_at_et": "2026-08-10T15:45:00-04:00",
                    "scheduled_session_tag": "preclose",
                    "force": False,
                    "universe": list(SYMBOLS),
                    "overall_status": "ok",
                    "names": names,
                    "manifest_hash": built["manifest_hash"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        package = manifest.verify_session(
            SESSION,
            list(SYMBOLS),
            self.chain_dir,
            self.manifest_path,
            self.receipt_path,
        )
        self.data_gate_receipt = {
            "receipt_type": "data_gate",
            "evidence_mode": data_gate.EVIDENCE_MODE,
            "evaluation_session": SESSION,
            "universe": list(SYMBOLS),
            "symbols": {
                symbol: {
                    "chain": {
                        "expected_path": str(self.chain_dir / f"{symbol}_{SESSION}.parquet"),
                        "audit_receipt": {"valid": True, **package},
                    }
                }
                for symbol in SYMBOLS
            },
        }

    def _write_sidecar(
        self,
        *,
        manifest_hash: str | None = None,
        session: str = SESSION,
        schema_version: str = quote_age_report.SCHEMA_VERSION,
        dispersion_age: float = 0.0,
    ) -> None:
        self.sidecar_path.write_text(
            json.dumps(
                {
                    "schema_version": schema_version,
                    "session": session,
                    "manifest_hash": (
                        manifest_hash
                        if manifest_hash is not None
                        else self.data_gate_receipt["symbols"]["AAA"]["chain"]["audit_receipt"][
                            "manifest_hash"
                        ]
                    ),
                    "symbols_requested": list(SYMBOLS),
                    "symbols": {
                        symbol: {
                            "columns": {
                                "timestamp": {
                                    "selectable": {"age_minutes": {"max": dispersion_age}}
                                }
                            }
                        }
                        for symbol in SYMBOLS
                    },
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    def evaluate(self) -> dict:
        return gate.evaluate_schwab_quote_age(
            data_gate_receipt=self.data_gate_receipt,
            included_symbols=SYMBOLS,
        )

    def _with_owner_absolute_threshold(self):
        return mock.patch.object(
            gate.config,
            "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES",
            20.0,
            create=True,
        )

    def test_absent_owner_threshold_reports_absolute_ages_without_banning_names(self):
        result = self.evaluate()

        self.assertFalse(hasattr(config, "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES"))
        self.assertEqual(result["whole_universe_verdict"], gate.QUOTE_AGE_AWAITING_OWNER_THRESHOLD)
        self.assertEqual(
            result["dispersion_reference_minutes"],
            config.H7_SCHWAB_QUOTE_AGE_DISPERSION_REFERENCE_MINUTES,
        )
        self.assertIsNone(result["absolute_threshold_minutes"])
        self.assertEqual(
            result["symbols"]["AAA"]["worst_absolute_selectable_quote_age_minutes"], 5.0
        )
        self.assertEqual(
            result["symbols"]["BBB"]["worst_absolute_selectable_quote_age_minutes"], 16.0
        )
        self.assertEqual(result["entry_banned_symbols"], [])
        self.assertTrue(all(not row["entry_banned"] for row in result["symbols"].values()))
        self.assertEqual(
            result["sidecar_diagnostic"]["reason_codes"], [gate.QUOTE_AGE_SIDECAR_MISSING]
        )

    def test_owner_absolute_threshold_bans_only_the_over_threshold_name(self):
        self._replace_package({"AAA": 5.0, "BBB": 21.0})

        with self._with_owner_absolute_threshold():
            result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "NO_GO")
        self.assertEqual(result["absolute_threshold_minutes"], 20.0)
        self.assertEqual(result["symbols"]["AAA"]["verdict"], "GO")
        self.assertFalse(result["symbols"]["AAA"]["entry_banned"])
        self.assertEqual(result["symbols"]["BBB"]["reason_codes"], [gate.QUOTE_AGE_OVER_THRESHOLD])
        self.assertTrue(result["symbols"]["BBB"]["entry_banned"])
        self.assertEqual(result["entry_banned_symbols"], ["BBB"])

    def test_manifest_bound_absolute_age_controls_banning_not_a_fresh_sidecar_value(self):
        self._replace_package({"AAA": 21.0, "BBB": 5.0})
        self._write_sidecar(dispersion_age=0.0)

        with self._with_owner_absolute_threshold():
            result = self.evaluate()

        self.assertTrue(result["symbols"]["AAA"]["entry_banned"])
        self.assertEqual(
            result["symbols"]["AAA"]["worst_absolute_selectable_quote_age_minutes"],
            21.0,
        )
        self.assertEqual(result["sidecar_diagnostic"]["reason_codes"], [])

    def test_missing_or_stale_sidecar_is_reported_but_does_not_block_a_fresh_package(self):
        self._write_sidecar(manifest_hash="a" * 64)

        with self._with_owner_absolute_threshold():
            result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "GO")
        self.assertEqual(result["entry_banned_symbols"], [])
        self.assertEqual(
            result["sidecar_diagnostic"]["reason_codes"],
            [gate.QUOTE_AGE_SIDECAR_IDENTITY_MISMATCH],
        )

    def test_null_selectable_timestamp_is_evidence_invalid_and_not_banned_while_unarmed(self):
        self._replace_package(
            {"AAA": 5.0, "BBB": 5.0}, timestamps={"AAA": None, "BBB": self.reference}
        )

        result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertEqual(result["entry_banned_symbols"], [])
        self.assertIn("null", result["error"])

    def test_garbage_selectable_timestamp_is_evidence_invalid_and_banned_in_owner_threshold_mode(
        self,
    ):
        self._replace_package(
            {"AAA": 5.0, "BBB": 5.0},
            timestamps={"AAA": "not-a-timestamp", "BBB": self.reference},
        )

        with self._with_owner_absolute_threshold():
            result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertEqual(result["entry_banned_symbols"], list(SYMBOLS))
        self.assertIn("timestamp", result["error"])

    def test_post_close_selectable_timestamp_is_never_a_negative_age_pass(self):
        self._replace_package(
            {"AAA": 5.0, "BBB": 5.0},
            timestamps={"AAA": self.reference + pd.Timedelta(minutes=1), "BBB": self.reference},
        )

        with self._with_owner_absolute_threshold():
            result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertIn("post-reference", result["error"])
        self.assertEqual(result["entry_banned_symbols"], list(SYMBOLS))

    def test_missing_manifest_bound_chain_bytes_are_visible_evidence_invalid_in_both_modes(self):
        (self.chain_dir / f"AAA_{SESSION}.parquet").unlink()

        unarmed = self.evaluate()
        with self._with_owner_absolute_threshold():
            armed = self.evaluate()

        self.assertEqual(unarmed["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertEqual(unarmed["entry_banned_symbols"], [])
        self.assertEqual(armed["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertEqual(armed["entry_banned_symbols"], list(SYMBOLS))

    def test_malformed_mixed_type_universe_fails_closed_instead_of_raising(self):
        self.data_gate_receipt["universe"] = ["AAA", 1]

        result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertEqual(result["entry_banned_symbols"], [])
        self.assertIn("closed", result["error"])


if __name__ == "__main__":
    unittest.main()

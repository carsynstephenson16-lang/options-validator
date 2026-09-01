"""Brief 36 WP-E quote-age arming gate tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from options_researcher import h7_schwab_quote_age_gate as gate

SESSION = "2026-08-10"
SYMBOLS = ("AAA", "BBB")


class SchwabQuoteAgeGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.receipt_path = self.root / SESSION / "preclose.json"
        self.receipt_path.parent.mkdir(parents=True)
        self.receipt_path.write_text("{}\n", encoding="utf-8")
        self.data_gate_receipt = {
            "receipt_type": "data_gate",
            "evidence_mode": "REAL-H7-SCHWAB-PRECLOSE-AUDIT",
            "evaluation_session": SESSION,
            "universe": list(SYMBOLS),
            "symbols": {
                symbol: {
                    "chain": {
                        "audit_receipt": {
                            "valid": True,
                            "receipt_path": str(self.receipt_path),
                        }
                    }
                }
                for symbol in SYMBOLS
            },
        }

    @property
    def sidecar_path(self) -> Path:
        return self.receipt_path.with_name("preclose.quote_age.json")

    def write_sidecar(
        self,
        *,
        quote_ages: dict[str, float],
        trade_age: float = 999999.0,
    ) -> None:
        report = {
            "schema_version": "schwab_quote_age_report/v1",
            "session": SESSION,
            "symbols_requested": list(SYMBOLS),
            "symbols": {
                symbol: {
                    "columns": {
                        "timestamp": {
                            "selectable": {
                                "age_minutes": {
                                    "max": quote_ages[symbol]
                                }
                            }
                        },
                        "trade_timestamp": {
                            "selectable": {
                                "age_minutes": {"max": trade_age}
                            }
                        },
                    }
                }
                for symbol in SYMBOLS
            },
        }
        self.sidecar_path.write_text(
            json.dumps(report), encoding="utf-8"
        )

    def evaluate(self):
        return gate.evaluate_schwab_quote_age(
            data_gate_receipt=self.data_gate_receipt,
            included_symbols=SYMBOLS,
        )

    def test_under_and_exact_threshold_pass_trade_age_is_ignored(self):
        self.write_sidecar(quote_ages={"AAA": 59.9, "BBB": 60.0})

        result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "GO")
        self.assertEqual(result["go_count"], 2)
        self.assertEqual(result["threshold_minutes"], 60)
        self.assertEqual(
            result["symbols"]["BBB"]["worst_selectable_quote_age_minutes"],
            60.0,
        )

    def test_over_threshold_name_is_banned_and_visible(self):
        self.write_sidecar(quote_ages={"AAA": 10.0, "BBB": 60.0001})

        result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "NO_GO")
        self.assertEqual(result["symbols"]["AAA"]["verdict"], "GO")
        self.assertEqual(result["symbols"]["BBB"]["verdict"], "NO_GO")
        self.assertEqual(
            result["symbols"]["BBB"]["reason_codes"],
            [gate.QUOTE_AGE_OVER_THRESHOLD],
        )

    def test_missing_sidecar_fails_closed_for_every_name(self):
        result = self.evaluate()

        self.assertEqual(result["whole_universe_verdict"], "NO_GO")
        self.assertEqual(result["go_count"], 0)
        self.assertIn("not found", result["error"])
        self.assertTrue(
            all(
                row["reason_codes"] == [gate.QUOTE_AGE_EVIDENCE_INVALID]
                for row in result["symbols"].values()
            )
        )

    def test_threshold_is_read_from_config_single_source(self):
        self.write_sidecar(quote_ages={"AAA": 6.0, "BBB": 6.0})
        with mock.patch.object(
            gate.config,
            "H7_SCHWAB_MAX_SELECTABLE_QUOTE_AGE_MINUTES",
            5,
        ):
            result = self.evaluate()
        self.assertEqual(result["threshold_minutes"], 5)
        self.assertEqual(result["whole_universe_verdict"], "NO_GO")


if __name__ == "__main__":
    unittest.main()

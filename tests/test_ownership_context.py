"""Contracts for immutable, display-only ownership context inputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from options_researcher.ownership_context import (
    OWNERSHIP_CONTEXT_UNIVERSE,
    OwnershipContextValidationError,
    load_ownership_context,
)


class OwnershipContextTests(unittest.TestCase):
    def _payload(self) -> dict[str, object]:
        rows = []
        for symbol in OWNERSHIP_CONTEXT_UNIVERSE:
            rows.append(
                {
                    "symbol": symbol,
                    "capitaliq_id": "1",
                    "display_only_extra": symbol in {"NBIS", "AMAT", "CLSK"},
                    "insider": {
                        "coverage": "NO_VISIBLE_ROWS",
                        "eligible_purchase_count": None,
                        "events": [],
                    },
                    "fund": {
                        "coverage": "DATA_GAP",
                        "eligible_product_count": None,
                        "events": [],
                    },
                    "institutional": {
                        "coverage": "PARTIAL",
                        "active_buyer_count": 0,
                        "events": [],
                    },
                }
            )
        return {
            "schema_version": "ownership-context/v1",
            "as_of": "2026-08-10",
            "retrieved_at": "2026-08-10T23:30:00-04:00",
            "display_only": True,
            "verdict_eligible": False,
            "universe": list(OWNERSHIP_CONTEXT_UNIVERSE),
            "symbols": rows,
            "limitations": ["No composite score or rank is emitted."],
        }

    def _load(self, payload: dict[str, object]):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ownership.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_ownership_context(path)

    def test_loads_exact_universe_as_deeply_immutable_context(self) -> None:
        snapshot = self._load(self._payload())

        self.assertEqual(snapshot.symbols, OWNERSHIP_CONTEXT_UNIVERSE)
        self.assertEqual(snapshot.as_of.isoformat(), "2026-08-10")
        self.assertIsInstance(snapshot.rows, MappingProxyType)
        self.assertIsNone(snapshot.rows["CRWV"]["insider"]["eligible_purchase_count"])
        with self.assertRaises(TypeError):
            snapshot.rows["CRWV"]["insider"]["coverage"] = "COMPLETE"

    def test_rejects_verdict_or_ranking_fields_at_any_depth(self) -> None:
        payload = self._payload()
        payload["symbols"][0]["institutional"]["score"] = 0.9

        with self.assertRaisesRegex(OwnershipContextValidationError, "forbidden_field"):
            self._load(payload)

    def test_rejects_universe_drift_or_reordering(self) -> None:
        payload = self._payload()
        payload["universe"][0], payload["universe"][1] = (
            payload["universe"][1],
            payload["universe"][0],
        )

        with self.assertRaisesRegex(OwnershipContextValidationError, "universe_mismatch"):
            self._load(payload)

    def test_rejects_success_shaped_eligibility_flags(self) -> None:
        payload = self._payload()
        payload["verdict_eligible"] = True

        with self.assertRaisesRegex(OwnershipContextValidationError, "display_only_required"):
            self._load(payload)

    def test_rejects_naive_retrieval_timestamp(self) -> None:
        payload = self._payload()
        payload["retrieved_at"] = "2026-08-10T23:30:00"

        with self.assertRaisesRegex(OwnershipContextValidationError, "timezone_required"):
            self._load(payload)

    def test_repository_snapshot_is_loadable_and_keeps_data_gaps(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "reports"
            / "ownership_context"
            / "2026-08-10.json"
        )

        snapshot = load_ownership_context(path)

        self.assertEqual(len(snapshot.rows), 18)
        self.assertEqual(
            sum(row["institutional"]["active_buyer_count"] for row in snapshot.rows.values()),
            54,
        )
        self.assertIsNone(snapshot.rows["CRWV"]["insider"]["eligible_purchase_count"])
        self.assertEqual(snapshot.rows["VST"]["insider"]["eligible_purchase_count"], 0)


if __name__ == "__main__":
    unittest.main()

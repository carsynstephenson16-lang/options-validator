"""Offline tests for the cached-only H7 Schwab feasibility receipt."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import h7_schwab_feasibility as feasibility


class ArithmeticTests(unittest.TestCase):
    def test_hand_derived_counts_and_projection(self):
        report = feasibility.summarize_counts(
            sessions=["2026-08-03", "2026-08-04", "2026-08-05"],
            symbols=["AAA", "BBB"],
            passing_symbol_days={
                ("2026-08-03", "AAA"),
                ("2026-08-05", "BBB"),
            },
            window_sessions=70,
            code_sha="a" * 40,
            stack_version="fixture-stack/v1",
            errors=[],
        )
        self.assertEqual(report["symbol_days"], 6)
        self.assertEqual(report["full_stack_passes"], 2)
        self.assertAlmostEqual(report["base_rate"], 2 / 6)
        self.assertAlmostEqual(report["expected_entries"], (2 / 6) * 70 * 2)
        self.assertEqual(report["provenance"], "LLM/tool-computed")
        self.assertNotIn("pass", report)
        self.assertNotIn("decision", report)

    def test_receipt_hash_detects_tampering(self):
        report = feasibility.summarize_counts(
            sessions=["2026-08-03"],
            symbols=["AAA"],
            passing_symbol_days=set(),
            window_sessions=70,
            code_sha="a" * 40,
            stack_version="fixture-stack/v1",
            errors=[],
        )
        self.assertTrue(feasibility.verify_receipt(report))
        report["full_stack_passes"] = 1
        self.assertFalse(feasibility.verify_receipt(report))


class NoNetworkSurfaceTests(unittest.TestCase):
    def test_tool_has_no_provider_or_client_surface(self):
        source = Path(feasibility.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "SchwabMarketData",
            "LockedReadOnlySchwabClient",
            "thetadata_adapter",
            "schwab_adapter",
            "requests.",
            "httpx.",
        ):
            self.assertNotIn(forbidden, source)

    def test_write_once_receipt_refuses_drift(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "receipt.json"
            report = feasibility.summarize_counts(
                sessions=["2026-08-03"],
                symbols=["AAA"],
                passing_symbol_days=set(),
                window_sessions=70,
                code_sha="a" * 40,
                stack_version="fixture-stack/v1",
                errors=[],
            )
            feasibility.write_receipt(report, path)
            feasibility.write_receipt(report, path)
            drifted = feasibility.summarize_counts(
                sessions=["2026-08-03"],
                symbols=["AAA"],
                passing_symbol_days={("2026-08-03", "AAA")},
                window_sessions=70,
                code_sha="a" * 40,
                stack_version="fixture-stack/v1",
                errors=[],
            )
            with self.assertRaises(FileExistsError):
                feasibility.write_receipt(drifted, path)


if __name__ == "__main__":
    unittest.main()

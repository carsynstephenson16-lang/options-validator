"""Offline tests for the cached-only H7 Schwab feasibility receipt."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from options_researcher import h7_schwab_window_registration as registration
from tools import h7_schwab_feasibility as feasibility
from tools.h7_entry_variant_menu import OCCUPANCY_LOCKOUT_SESSIONS


def _sessions(count: int = 70) -> list[str]:
    first = date(2026, 5, 1)
    return [(first + timedelta(days=offset)).isoformat() for offset in range(count)]


class ArithmeticTests(unittest.TestCase):
    def _report(self, *, passes: set[tuple[str, str]] | None = None) -> dict:
        sessions = _sessions()
        return feasibility.summarize_counts(
            sessions=sessions,
            symbols=["AAA", "BBB"],
            passing_symbol_days=(
                {(sessions[0], "AAA"), (sessions[10], "BBB")} if passes is None else passes
            ),
            window_sessions=70,
            code_sha="a" * 40,
            stack_version=feasibility.STACK_VERSION,
            errors=[],
        )

    def test_raw_occupancy_count_is_not_scaled_and_is_labeled_upper_bound(self):
        report = self._report()
        self.assertEqual(report["symbol_days"], 140)
        self.assertEqual(report["full_stack_passes"], 2)
        self.assertAlmostEqual(report["base_rate"], 2 / 140)
        self.assertAlmostEqual(report["expected_entries"], 2.0)
        self.assertEqual(report["occupancy_constrained_count"], 2)
        self.assertEqual(report["occupancy_constrained_expected_entries"], 2)
        self.assertEqual(report["occupancy_lockout_sessions"], OCCUPANCY_LOCKOUT_SESSIONS[0])
        self.assertIs(report["occupancy_upper_bound"], True)
        self.assertEqual(report["lookback_sessions"], report["window_sessions"])
        self.assertEqual(report["provenance"], "LLM/tool-computed")
        self.assertNotIn("pass", report)
        self.assertNotIn("decision", report)

    def test_mismatched_lookback_and_window_refuses_without_scaling(self):
        with self.assertRaisesRegex(ValueError, "must equal"):
            feasibility.summarize_counts(
                sessions=_sessions(3),
                symbols=["AAA"],
                passing_symbol_days=set(),
                window_sessions=70,
                code_sha="a" * 40,
                stack_version=feasibility.STACK_VERSION,
                errors=[],
            )

    def test_receipt_hash_detects_tampering(self):
        report = self._report(passes=set())
        self.assertTrue(feasibility.verify_receipt(report))
        report["full_stack_passes"] = 1
        self.assertFalse(feasibility.verify_receipt(report))

    def test_receipt_records_verifiable_input_files(self):
        path = Path("pyproject.toml")
        report = feasibility.summarize_counts(
            sessions=["2026-08-03"],
            symbols=["AAA"],
            passing_symbol_days=set(),
            window_sessions=1,
            code_sha="a" * 40,
            stack_version=feasibility.STACK_VERSION,
            errors=[],
            input_paths={"project": path},
        )
        self.assertEqual(report["input_files"]["project"]["path"], str(path))
        self.assertEqual(len(report["input_files"]["project"]["sha256"]), 64)

    def test_cli_requires_explicit_cohort_and_commensurate_panel(self):
        with self.assertRaises(SystemExit):
            feasibility.main(["--lookback-sessions", "1"])
        with self.assertRaises(SystemExit):
            feasibility.main(
                [
                    "--lookback-sessions",
                    "1",
                    "--window-sessions",
                    "2",
                    "--symbols",
                    "AAA",
                ]
            )

    def test_stack_tool_and_source_surface_have_one_definition(self):
        self.assertIs(feasibility.STACK_VERSION, registration.FEASIBILITY_STACK_VERSION)
        self.assertIs(feasibility.TOOL_LABEL, registration.FEASIBILITY_TOOL_LABEL)
        self.assertIs(feasibility.RECEIPT_KIND, registration.FEASIBILITY_RECEIPT_KIND)
        report = self._report()
        self.assertEqual(report["source_paths"], list(registration.FEASIBILITY_SOURCE_PATHS))
        self.assertEqual(len(report["source_hash"]), 64)


class NoNetworkSurfaceTests(unittest.TestCase):
    def test_direct_script_help_resolves_repo_imports(self):
        root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, "tools/h7_schwab_feasibility.py", "--help"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("cached-only H7 full-stack base rate", completed.stdout)

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
            report = ArithmeticTests()._report(passes=set())
            feasibility.write_receipt(report, path)
            feasibility.write_receipt(report, path)
            drifted = ArithmeticTests()._report(passes={(_sessions()[0], "AAA")})
            with self.assertRaises(FileExistsError):
                feasibility.write_receipt(drifted, path)


if __name__ == "__main__":
    unittest.main()

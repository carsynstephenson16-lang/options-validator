"""Offline tests for the cached-only H7 Schwab feasibility receipt."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import config
from options_researcher import h7_schwab_window_registration as registration
from tools import h7_schwab_feasibility as feasibility
from tools.h7_entry_variant_menu import OCCUPANCY_LOCKOUT_SESSIONS


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
        self.assertAlmostEqual(
            report["occupancy_constrained_expected_entries"],
            2 / 3 * 70,
        )
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

    def test_cli_requires_explicit_cohort(self):
        with self.assertRaises(SystemExit):
            feasibility.main(["--lookback-sessions", "1"])

    def test_occupancy_inputs_are_recorded_for_independent_rederivation(self):
        """Round-1 F6: the validator must not have to trust this number."""
        report = feasibility.summarize_counts(
            sessions=["2026-08-03", "2026-08-04", "2026-08-05"],
            symbols=["AAA", "BBB"],
            passing_symbol_days={("2026-08-03", "AAA"), ("2026-08-05", "BBB")},
            window_sessions=70,
            code_sha="a" * 40,
            stack_version="fixture-stack/v1",
            errors=[],
        )
        self.assertEqual(report["occupancy_constrained_count"], 2)
        self.assertEqual(report["lookback_sessions"], 3)
        self.assertEqual(
            report["occupancy_lockout_sessions"],
            config.H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS,
        )
        self.assertAlmostEqual(
            report["occupancy_constrained_expected_entries"],
            report["occupancy_constrained_count"]
            * report["window_sessions"]
            / report["lookback_sessions"],
        )

    def test_registered_lockout_constant_matches_the_menu_derivation(self):
        """One definition: config.py mirrors the schedule-derived long-lane value."""
        self.assertEqual(
            config.H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS,
            OCCUPANCY_LOCKOUT_SESSIONS[0],
        )

    def test_stack_and_tool_identity_have_one_definition(self):
        """Round-1 F7: the tool and the validator must not drift apart."""
        self.assertIs(feasibility.STACK_VERSION, registration.FEASIBILITY_STACK_VERSION)
        self.assertIs(feasibility.TOOL_LABEL, registration.FEASIBILITY_TOOL_LABEL)
        self.assertIs(feasibility.RECEIPT_KIND, registration.FEASIBILITY_RECEIPT_KIND)


class ToolReceiptPassesTheRegistrationValidatorTests(unittest.TestCase):
    """Round-1 F7: a tool-produced receipt must clear WP-A end to end."""

    def _receipt(self, **overrides):
        sessions = [f"2026-08-{day:02d}" for day in range(3, 3 + 70)]
        symbols = list(config.H7_SCHWAB_REGISTERED_COHORT)
        passing = {(sessions[0], symbols[0]), (sessions[35], symbols[1])}
        report = feasibility.summarize_counts(
            sessions=sessions,
            symbols=symbols,
            passing_symbol_days=passing,
            window_sessions=70,
            code_sha="a" * 40,
            stack_version=feasibility.STACK_VERSION,
            errors=[],
            input_paths={"project": Path("pyproject.toml")},
        )
        if overrides:
            report.update(overrides)
            report["receipt_hash"] = feasibility._receipt_hash(report)
        return report

    def test_tool_receipt_validates(self):
        receipt = self._receipt()
        self.assertEqual(
            registration._validate_feasibility(receipt, receipt["receipt_hash"]),
            receipt["occupancy_constrained_expected_entries"],
        )

    def test_validator_refuses_a_forged_occupancy_projection(self):
        receipt = self._receipt(occupancy_constrained_expected_entries=1.0)
        with self.assertRaisesRegex(
            registration.RegistrationInputError, "occupancy"
        ):
            registration._validate_feasibility(receipt, receipt["receipt_hash"])

    def test_validator_refuses_an_unregistered_lockout(self):
        receipt = self._receipt(
            occupancy_lockout_sessions=(
                config.H7_SCHWAB_REGISTERED_OCCUPANCY_LOCKOUT_SESSIONS + 1
            )
        )
        with self.assertRaisesRegex(
            registration.RegistrationInputError, "lockout"
        ):
            registration._validate_feasibility(receipt, receipt["receipt_hash"])


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

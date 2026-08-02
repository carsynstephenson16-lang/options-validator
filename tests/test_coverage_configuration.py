"""Contract tests for the measured, local-only coverage gate."""

from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCES = {"data", "harness", "options_researcher", "research", "strategies"}
EXPECTED_OMISSIONS = {
    "tests/*",
    "tools/*",
    "reports/*",
    "results/*",
    ".cache/*",
    ".tmp/*",
}


class TestCoverageConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configuration = tomllib.loads((ROOT / "pyproject.toml").read_text())

    def test_coverage_is_a_pinned_development_dependency(self) -> None:
        project_dependencies = self.configuration["project"]["dependencies"]
        development_dependencies = self.configuration["dependency-groups"]["dev"]

        self.assertNotIn("coverage==7.15.2", project_dependencies)
        self.assertIn("coverage==7.15.2", development_dependencies)

    def test_run_configuration_measures_branches_and_explicit_sources(self) -> None:
        run_configuration = self.configuration["tool"]["coverage"]["run"]

        self.assertIs(run_configuration["branch"], True)
        self.assertEqual(set(run_configuration["source"]), EXPECTED_SOURCES)
        self.assertEqual(set(run_configuration["omit"]), EXPECTED_OMISSIONS)

    def test_report_gate_is_derived_from_the_complete_baseline(self) -> None:
        report_configuration = self.configuration["tool"]["coverage"]["report"]

        self.assertIs(report_configuration["show_missing"], True)
        self.assertIs(report_configuration["skip_empty"], True)
        self.assertEqual(report_configuration["fail_under"], 79)

    def test_json_report_stays_local(self) -> None:
        json_configuration = self.configuration["tool"]["coverage"]["json"]

        self.assertEqual(json_configuration["output"], "coverage.json")
        self.assertIs(json_configuration["pretty_print"], True)


if __name__ == "__main__":
    unittest.main()

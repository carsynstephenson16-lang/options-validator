"""Isolation boundaries for the short-positioning subsystem.

These are the tests that keep a display-only lane from quietly becoming a
signal: no strategy or ranking import, no network at render time, and no
licensed or provider row in Git.
"""

from __future__ import annotations

import ast
import socket
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path

import config
from data.short_positioning.audit import audit_normalized_partition
from options_researcher import exp_short_positioning as lane
from options_researcher.short_positioning_context import build_short_positioning_context

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "short_positioning"

# The only tracked modules allowed to import short-positioning code.
ALLOWED_IMPORTERS = {
    "options_researcher/short_positioning_context.py",
    "options_researcher/exp_short_positioning.py",
    "options_researcher/experiments_dashboard.py",
    "tools/short_positioning_capture.py",
    "tools/short_positioning_audit.py",
}

SCANNED_DIRS = ("options_researcher", "strategies", "data", "tools", "harness", "research")

SYNTHETIC_SYMBOLS = {"ZQXA", "TRNVQ", "HLGRD"}

IGNORED_DATA_PATHS = (
    ".cache/short_positioning/",
    ".local/short_positioning/",
    "data/short_positioning/raw/",
    "data/short_positioning/licensed/",
    "somewhere/example.spglobal.csv",
    "somewhere/example.securities-finance.csv",
)


def _tracked_python_files() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [REPO_ROOT / name for name in output]


class ImportBoundaryTests(unittest.TestCase):
    def test_only_display_and_capture_modules_import_short_positioning(self):
        offenders = []
        for path in _tracked_python_files():
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative.startswith(("tests/", "data/short_positioning/")):
                continue
            if not relative.startswith(tuple(f"{d}/" for d in SCANNED_DIRS)):
                continue
            try:
                tree = ast.parse(path.read_text())
            except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                if any("short_positioning" in name for name in names):
                    if relative not in ALLOWED_IMPORTERS:
                        offenders.append(relative)
        self.assertEqual(sorted(set(offenders)), [])

    def test_the_display_modules_never_import_an_acquisition_module(self):
        for relative in (
            "options_researcher/short_positioning_context.py",
            "options_researcher/exp_short_positioning.py",
        ):
            tree = ast.parse((REPO_ROOT / relative).read_text())
            imported = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported += [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
            for banned in ("providers", "raw_store", "provider"):
                self.assertFalse(
                    any(name.endswith(f".{banned}") or f".{banned}." in name for name in imported),
                    f"{relative} must not import the acquisition module {banned}",
                )

    def test_ranking_and_book_modules_do_not_reference_short_positioning(self):
        for relative in (
            "options_researcher/attractiveness_dashboard.py",
            "options_researcher/dashboard.py",
        ):
            path = REPO_ROOT / relative
            if path.exists():
                self.assertNotIn("short_positioning", path.read_text())


class _NoNetwork:
    """Any socket construction inside this block is a test failure."""

    def __enter__(self):
        self._original = socket.socket

        def _blocked(*args, **kwargs):
            raise AssertionError("network access attempted in an offline path")

        socket.socket = _blocked  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info):
        socket.socket = self._original  # type: ignore[assignment]
        return False


class NetworkIsolationTests(unittest.TestCase):
    def test_building_and_rendering_the_lane_opens_no_socket(self):
        with _NoNetwork():
            cards = lane.build_exp_short_board(["MSFT", "AMZN"], asof="2026-07-21")
            for card in cards:
                lane.render_short_positioning_card(card)
        self.assertEqual(len(cards), 2)

    def test_building_context_directly_opens_no_socket(self):
        with _NoNetwork():
            cards = build_short_positioning_context(
                ["MSFT"],
                asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc),
                root=Path(config.SHORT_POSITIONING_ROOT),
            )
        self.assertEqual(len(cards), 1)

    def test_the_audit_opens_no_socket(self):
        with _NoNetwork():
            report = audit_normalized_partition(
                Path(config.SHORT_POSITIONING_ROOT),
                provider="finra",
                dataset="consolidated-short-interest",
                publication_date=datetime(2026, 7, 17, tzinfo=timezone.utc).date(),
                asof=datetime(2026, 7, 21, 20, 0, tzinfo=timezone.utc),
            )
        self.assertIn(report["status"], {"PASS", "WARN", "BLOCK"})


class GitPolicyTests(unittest.TestCase):
    def test_every_local_data_path_is_ignored_by_git(self):
        for path in IGNORED_DATA_PATHS:
            with self.subTest(path=path):
                result = subprocess.run(
                    ["git", "check-ignore", "-q", "--no-index", path],
                    cwd=REPO_ROOT,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, f"{path} is not gitignored")

    def test_no_raw_or_normalized_provider_data_is_tracked(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        for name in tracked:
            self.assertNotIn("short_positioning/raw/", name)
            self.assertNotIn("short_positioning/licensed/", name)
            self.assertFalse(name.endswith(".spglobal.csv"))
            self.assertFalse(name.endswith(".securities-finance.csv"))

    def test_no_licensed_vendor_material_is_tracked_anywhere(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.split()
        for name in tracked:
            lowered = name.lower()
            self.assertNotIn("sp_global", lowered)
            self.assertNotIn("spglobal", lowered)
            self.assertNotIn("securities-finance", lowered)

    def test_tracked_fixtures_use_invented_symbols_only(self):
        import json

        for fixture in sorted(FIXTURES.glob("*.json")):
            with self.subTest(fixture=fixture.name):
                for row in json.loads(fixture.read_text()):
                    self.assertIn(row["symbolCode"], SYNTHETIC_SYMBOLS)


if __name__ == "__main__":
    unittest.main()

"""H9 CLI gate — refuses before touching any data."""
import tempfile
import unittest
from pathlib import Path

from tools import h9_run_study as cli


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        (self.base / "facts.log").write_text("")
        self.addCleanup(self.tmp.cleanup)

    def fact(self, text):
        with open(self.base / "facts.log", "a") as f:
            f.write(f"2026-07-16T00:00:00+00:00\t{text}\n")

    def test_refuses_without_registration_fact(self):
        msg = cli.h9_prereg_gate(base_dir=self.base)
        self.assertIsNotNone(msg)
        self.assertIn("H9_REGISTERED", msg)

    def test_clears_with_registration_fact(self):
        self.fact("H9_REGISTERED 2026-07-XX: spec sha256 abc at commit def")
        self.assertIsNone(cli.h9_prereg_gate(base_dir=self.base))

    def test_run_refuses_after_result_exists(self):
        self.fact("H9_REGISTERED 2026-07-XX: spec sha256 abc at commit def")
        self.fact("H9_RESULT 2026-07-XX: outcome REJECTED receipt xyz")
        msg = cli.h9_one_run_gate(base_dir=self.base)
        self.assertIsNotNone(msg)
        self.assertIn("one-run contract", msg)

    def test_cli_census_refuses_unregistered_exit_2(self):
        rc = cli.main(["census", "--ledger-dir", str(self.base)])
        self.assertEqual(rc, 2)

    def test_cli_run_refuses_unregistered_exit_2(self):
        rc = cli.main(["run", "--ledger-dir", str(self.base)])
        self.assertEqual(rc, 2)

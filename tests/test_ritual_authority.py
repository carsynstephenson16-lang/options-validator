"""Read-only authority contract for the stateful daily ritual."""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path

from data import ritual_authority

AUTHORITY = Path(__file__).resolve().parents[1] / "data" / "ritual_authority.py"


class RitualAuthorityContractTests(unittest.TestCase):
    def test_tracked_authority_module_exists(self):
        self.assertTrue(AUTHORITY.is_file())

    def test_module_exposes_readiness_and_cli_interfaces(self):
        self.assertTrue(hasattr(ritual_authority, "evaluate_full_ritual"))
        self.assertTrue(hasattr(ritual_authority, "main"))

    def test_full_ritual_is_blocked_without_source_and_h7_authority(self):
        readiness = ritual_authority.evaluate_full_ritual()

        self.assertFalse(readiness.ready)
        joined = " ".join(readiness.blockers)
        self.assertIn("exact-session", joined)
        self.assertIn("H7", joined)
        self.assertIn("ThetaData", joined)

    def test_status_succeeds_but_require_full_refuses(self):
        status_out = io.StringIO()
        with contextlib.redirect_stdout(status_out):
            status_rc = ritual_authority.main(["status"])
        status = json.loads(status_out.getvalue())

        require_out = io.StringIO()
        with contextlib.redirect_stdout(require_out):
            require_rc = ritual_authority.main(["require-full"])
        required = json.loads(require_out.getvalue())

        self.assertEqual(status_rc, 0)
        self.assertEqual(require_rc, 1)
        self.assertFalse(status["ready"])
        self.assertEqual(required, status)


if __name__ == "__main__":
    unittest.main()

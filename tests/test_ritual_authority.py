"""Read-only authority contract for the stateful daily ritual.

Three flags, three tiers (brief 11 §5). Every behavioral assertion below runs
against an EXPLICITLY CONSTRUCTED ``RitualAuthority`` passed through the
``main(argv, authority=...)`` injection seam: no test may read
``CURRENT_AUTHORITY`` and assert a specific flip state, or the owner's
switch-on flip commit would break the suite.
"""

from __future__ import annotations

import contextlib
import io
import itertools
import json
import unittest
from dataclasses import asdict
from pathlib import Path

from data import ritual_authority
from data.ritual_authority import RitualAuthority

AUTHORITY = Path(__file__).resolve().parents[1] / "data" / "ritual_authority.py"
REPO = Path(__file__).resolve().parents[1]


def _authority(*, data: bool, source: bool, h7: bool) -> RitualAuthority:
    return RitualAuthority(
        h7_active=h7,
        exact_session_source_active=source,
        ritual_data_phase_active=data,
    )


def _run(mode: str, authority: RitualAuthority) -> tuple[int, dict]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = ritual_authority.main([mode], authority=authority)
    return rc, json.loads(out.getvalue())


class RitualAuthorityContractTests(unittest.TestCase):
    def test_tracked_authority_module_exists(self):
        self.assertTrue(AUTHORITY.is_file())

    def test_module_exposes_readiness_and_cli_interfaces(self):
        self.assertTrue(hasattr(ritual_authority, "evaluate_data_phase"))
        self.assertTrue(hasattr(ritual_authority, "evaluate_full_ritual"))
        self.assertTrue(hasattr(ritual_authority, "main"))

    def test_tier_matrix_over_all_flag_combinations(self):
        for data, source, h7 in itertools.product((False, True), repeat=3):
            with self.subTest(data=data, source=source, h7=h7):
                authority = _authority(data=data, source=source, h7=h7)
                self.assertEqual(
                    ritual_authority.evaluate_data_phase(authority).ready, data
                )
                self.assertEqual(
                    ritual_authority.evaluate_full_ritual(authority).ready,
                    data and source and h7,
                )

    def test_full_tier_implies_data_tier(self):
        for data, source, h7 in itertools.product((False, True), repeat=3):
            with self.subTest(data=data, source=source, h7=h7):
                authority = _authority(data=data, source=source, h7=h7)
                if ritual_authority.evaluate_full_ritual(authority).ready:
                    self.assertTrue(
                        ritual_authority.evaluate_data_phase(authority).ready
                    )

    def test_full_tier_blocker_wording_is_preserved(self):
        # Downstream operators read these lines; the substrings are the
        # contract, not the exact sentence order.
        readiness = ritual_authority.evaluate_full_ritual(
            _authority(data=True, source=False, h7=False)
        )
        self.assertFalse(readiness.ready)
        joined = " ".join(readiness.blockers)
        self.assertIn("exact-session", joined)
        self.assertIn("H7", joined)
        self.assertIn("ThetaData", joined)

    def test_data_phase_blocker_is_reported_on_both_tiers(self):
        blocked = _authority(data=False, source=True, h7=True)
        self.assertIn(
            "Ritual data phase is not authorized.",
            ritual_authority.evaluate_data_phase(blocked).blockers,
        )
        self.assertIn(
            "Ritual data phase is not authorized.",
            ritual_authority.evaluate_full_ritual(blocked).blockers,
        )

    def test_status_succeeds_but_require_modes_refuse(self):
        cases = (
            (_authority(data=False, source=False, h7=False), 0, 1, 1),
            (_authority(data=True, source=False, h7=False), 0, 0, 1),
            (_authority(data=True, source=True, h7=True), 0, 0, 0),
        )
        for authority, status_rc, data_rc, full_rc in cases:
            with self.subTest(authority=authority):
                got_status_rc, status = _run("status", authority)
                got_data_rc, _ = _run("require-data", authority)
                got_full_rc, _ = _run("require-full", authority)

                self.assertEqual(got_status_rc, status_rc)
                self.assertEqual(got_data_rc, data_rc)
                self.assertEqual(got_full_rc, full_rc)
                self.assertEqual(set(status), {"data_phase", "flags", "full_ritual"})
                self.assertEqual(status["flags"], asdict(authority))
                self.assertEqual(
                    set(status["flags"]),
                    {
                        "exact_session_source_active",
                        "h7_active",
                        "ritual_data_phase_active",
                    },
                )

    def test_require_mode_stdout_matches_status_sub_objects(self):
        for data, source, h7 in itertools.product((False, True), repeat=3):
            with self.subTest(data=data, source=source, h7=h7):
                authority = _authority(data=data, source=source, h7=h7)
                _, status = _run("status", authority)
                _, data_out = _run("require-data", authority)
                _, full_out = _run("require-full", authority)

                self.assertEqual(data_out, status["data_phase"])
                self.assertEqual(full_out, status["full_ritual"])

    def test_all_modes_are_side_effect_free(self):
        authority = _authority(data=True, source=True, h7=True)
        watched = (
            REPO / "reports",
            REPO / "ledger",
            REPO / ".tmp" / "daily_ritual",
        )
        before = tuple(
            sorted(
                (str(item), item.stat().st_mtime_ns)
                for path in watched
                if path.exists()
                for item in path.rglob("*")
            )
        )
        for mode in ("status", "require-data", "require-full"):
            _run(mode, authority)
        after = tuple(
            sorted(
                (str(item), item.stat().st_mtime_ns)
                for path in watched
                if path.exists()
                for item in path.rglob("*")
            )
        )
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()

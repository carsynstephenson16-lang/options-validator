"""Offline tests for the target/outcome-column horizon registry.

`options_researcher.flow.horizons.required_horizon_for` is the shared parser
used by both `options_researcher.flow.study` (purge-window enforcement) and
`options_researcher.flow.analogs` (per-column outcome knowability masking)
to close the Codex PR #19 point-in-time leakage findings.
"""

import unittest

from options_researcher.flow.horizons import required_horizon_for


class RequiredHorizonForTests(unittest.TestCase):
    def test_parses_the_trailing_integer_convention(self):
        self.assertEqual(required_horizon_for("return_1"), 1)
        self.assertEqual(required_horizon_for("return_5"), 5)
        self.assertEqual(required_horizon_for("return_21"), 21)
        self.assertEqual(required_horizon_for("excess_return_5"), 5)
        self.assertEqual(required_horizon_for("iv_change_5"), 5)
        self.assertEqual(required_horizon_for("skew_change_5"), 5)
        # no underscore before the digits -- still a trailing-integer horizon
        self.assertEqual(required_horizon_for("future_rv21"), 21)

    def test_unknown_naming_convention_fails_loudly(self):
        with self.assertRaisesRegex(ValueError, "does not encode a forward-looking horizon"):
            required_horizon_for("baseline_validator_output")
        with self.assertRaisesRegex(ValueError, "does not encode a forward-looking horizon"):
            required_horizon_for("target")


if __name__ == "__main__":
    unittest.main()

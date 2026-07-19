import tempfile
import unittest
from pathlib import Path

from research.ledger import append, current_trial_count, verify
from tools.register_h10 import REGISTRATIONS


class TestH10Registrations(unittest.TestCase):
    def test_three_bodies_valid_and_count_three_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for body in REGISTRATIONS:
                append(dict(body), base_dir=base)
            verify(base_dir=base)
            self.assertEqual(current_trial_count(base), 3)

    def test_h10_lanes_are_separate_records(self):
        ids = [b["hypothesis_id"] for b in REGISTRATIONS]
        self.assertIn("H10a", ids)
        self.assertIn("H10b", ids)
        self.assertEqual(len(ids), len(set(ids)))

    def test_owner_locked_values_present_in_reason(self):
        text = " ".join(b["reason"] for b in REGISTRATIONS)
        for needle in ("0.40-0.60", "30-60 DTE", ">=7 losses", "$2,000/month",
                       "2026-10-06", "2027-01-06"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()

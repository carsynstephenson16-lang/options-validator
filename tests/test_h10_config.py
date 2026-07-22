import json
import unittest

import config


def _load_registration(seq):
    with open("ledger/experiments.jsonl", encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec.get("seq") == seq:
                return rec
    raise AssertionError(f"seq {seq} not found")


class H10ConfigMatchesRegistration(unittest.TestCase):
    def test_constants_exist(self):
        for name in (
            "H10_MAX_PREMIUM_PER_TRADE",
            "H10_MONTHLY_PREMIUM_CAP",
            "H10_DELTA_MIN",
            "H10_DELTA_MAX",
            "H10_STRIKE_BAND_PCT",
            "H10_DTE_MIN",
            "H10_DTE_MAX",
            "H10_PROFIT_TARGET_PCT",
            "H10_TIME_EXIT_SESSIONS",
            "H10_DTE_EXIT",
            "H10_MIN_LOSSES_FOR_VERDICT",
            "H10A_WINDOW_END",
            "H10B_WINDOW_END",
        ):
            self.assertTrue(hasattr(config, name), name)

    def test_values_match_registration_text(self):
        reg_a = json.dumps(_load_registration(15))
        reg_b = json.dumps(_load_registration(16))
        self.assertEqual(config.H10_MAX_PREMIUM_PER_TRADE, 600)
        self.assertEqual(config.H10_MONTHLY_PREMIUM_CAP, 2000)
        self.assertEqual((config.H10_DELTA_MIN, config.H10_DELTA_MAX), (0.40, 0.60))
        self.assertEqual(config.H10_STRIKE_BAND_PCT, 0.10)
        self.assertEqual((config.H10_DTE_MIN, config.H10_DTE_MAX), (30, 60))
        self.assertEqual(config.H10_PROFIT_TARGET_PCT, 1.00)
        self.assertEqual(config.H10_TIME_EXIT_SESSIONS, 20)
        self.assertEqual(config.H10_DTE_EXIT, 21)
        self.assertEqual(config.H10_MIN_LOSSES_FOR_VERDICT, 7)
        self.assertEqual(config.H10A_WINDOW_END, "2026-10-06")
        self.assertEqual(config.H10B_WINDOW_END, "2027-01-06")
        # anchor: the registration text must actually contain the key numbers
        self.assertIn("2026-10-06", reg_a)
        self.assertIn("2027-01-06", reg_b)

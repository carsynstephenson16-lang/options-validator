import unittest

import config


class ConfigKnobTests(unittest.TestCase):
    def test_oos_look_budget_is_three(self):
        self.assertEqual(config.OOS_LOOK_BUDGET, 3)

    def test_block_exponent_is_one_third(self):
        self.assertAlmostEqual(config.BOOTSTRAP_BLOCK_EXPONENT, 1.0 / 3.0)

    def test_block_constants_are_the_frozen_envelope(self):
        self.assertEqual(list(config.BOOTSTRAP_BLOCK_CONSTANTS), [0.5, 1, 2, 4])

    def test_cohort_granularity_is_week(self):
        self.assertEqual(config.COHORT_GRANULARITY, "week")

    def test_fill_model_id_is_versioned_string(self):
        self.assertEqual(config.FILL_MODEL_ID, "conservative_mid_minus_haircut_v1")


if __name__ == "__main__":
    unittest.main()

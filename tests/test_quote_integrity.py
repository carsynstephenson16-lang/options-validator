import unittest

import config


class TestDetectorConfig(unittest.TestCase):
    def test_frozen_detector_tolerances(self):
        self.assertEqual(config.BS_DELTA_EPS, 0.02)
        self.assertEqual(config.BS_NOARB_TOL, 0.02)
        self.assertEqual(config.BS_IV_EXTREME_LOW, 0.02)
        self.assertEqual(config.BS_IV_EXTREME_HIGH, 5.0)


if __name__ == "__main__":
    unittest.main()

import unittest

import config


class H5ConfigTests(unittest.TestCase):
    def test_thresholds_frozen(self):
        self.assertEqual(config.H5_PUT_YIELD_GREEN, 0.010)
        self.assertEqual(config.H5_PUT_YIELD_AMBER, 0.006)
        self.assertEqual(config.H5_CUSHION_GREEN, 0.8)
        self.assertEqual(config.H5_CUSHION_AMBER, 0.5)
        self.assertEqual(config.H5_CC_YIELD_GREEN, 0.008)
        self.assertEqual(config.H5_CC_YIELD_AMBER, 0.004)
        self.assertEqual(config.H5_CC_UPSIDE_GREEN, 0.03)
        self.assertEqual(config.H5_IVR_SELL_GREEN, 0.5)
        self.assertEqual(config.H5_IVR_BUY_GREEN, 0.3)
        self.assertEqual(config.H5_IVR_BUY_RED, 0.7)
        self.assertEqual(config.H5_INCOME_DELTA, 0.20)


if __name__ == "__main__":
    unittest.main()

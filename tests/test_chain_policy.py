import importlib
import unittest

from data import thetadata_adapter


class ChainPolicyCompatibilityTests(unittest.TestCase):
    def test_thetadata_adapter_reexports_chain_policy_helpers(self):
        try:
            chain_policy = importlib.import_module("data.chain_policy")
        except ModuleNotFoundError:
            self.fail("data.chain_policy must define the provider-neutral helpers")

        for name in (
            "mid_price",
            "passes_liquidity",
            "_pick_col",
            "_normalize_contract_keys",
        ):
            with self.subTest(name=name):
                self.assertIs(
                    getattr(thetadata_adapter, name),
                    getattr(chain_policy, name),
                )


if __name__ == "__main__":
    unittest.main()

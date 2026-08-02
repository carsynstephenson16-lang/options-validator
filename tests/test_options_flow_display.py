"""Descriptive options-flow display contract tests."""

import unittest

import pandas as pd

from options_researcher.flow.display import (
    DISPLAY_AUTHORITY,
    DISPLAY_COLUMNS,
    DISPLAY_DISCLAIMER,
    descriptive_flow_view,
)


class DisplayTests(unittest.TestCase):
    def test_view_attaches_noncausal_authority_and_disclaimer(self):
        features = pd.DataFrame(
            {
                column: [
                    "MSFT"
                    if column == "symbol"
                    else "2025-01-02"
                    if column == "session"
                    else "SPARSE_BASELINE"
                    if column == "baseline_status"
                    else "AGGRESSOR_SIGNED_NOT_CUSTOMER_OR_DEALER_INTENT"
                    if column == "direction_label"
                    else 1.0
                ]
                for column in DISPLAY_COLUMNS
            }
        )

        output = descriptive_flow_view(features)

        self.assertEqual(list(output.columns), [*DISPLAY_COLUMNS, "authority", "disclaimer"])
        self.assertEqual(output.loc[0, "authority"], DISPLAY_AUTHORITY)
        self.assertEqual(output.loc[0, "disclaimer"], DISPLAY_DISCLAIMER)

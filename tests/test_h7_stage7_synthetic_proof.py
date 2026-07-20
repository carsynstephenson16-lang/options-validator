"""Stage 7 deterministic fixture rehearsal of H7 roadmap Stages 1-6."""

import tempfile
import unittest
from pathlib import Path

from options_researcher import h7_event_ledger as ledger
from options_researcher.h7_paper_lifecycle import (
    REAL_FORWARD_STORE,
    ActivationBoundaryError,
)
from options_researcher.h7_synthetic_proof import run_synthetic_proof


class TestStage7SyntheticProof(unittest.TestCase):
    def test_full_receipt_proves_every_stage_and_required_refusal(self):
        before = ledger.verify(REAL_FORWARD_STORE)
        with tempfile.TemporaryDirectory() as tmp:
            receipt = run_synthetic_proof(Path(tmp) / "proof")
        after = ledger.verify(REAL_FORWARD_STORE)

        self.assertEqual(receipt["boundary"], "BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE")
        self.assertEqual(receipt["fixture_id"], "h7-stage7-v1")
        self.assertEqual(receipt["source_health"]["healthy"], 15)  # +ET (V1_8)
        self.assertEqual(receipt["data_gate"]["verdict"], "GO")
        self.assertEqual(receipt["data_gate"]["go_count"], 15)  # +ET (V1_8)
        self.assertTrue(receipt["ledger"]["valid"])
        self.assertGreater(receipt["ledger"]["event_count"], 8)
        self.assertEqual(receipt["lifecycle"]["decision_session"], "2026-07-10")
        self.assertEqual(receipt["lifecycle"]["entry_session"], "2026-07-13")
        self.assertEqual(receipt["lifecycle"]["exit_session"], "2026-07-15")
        self.assertEqual(receipt["book"]["rejected_reason"], "sleeve_exhausted")
        self.assertGreater(receipt["book"]["month_actual_risk_after_close"], 0)
        self.assertEqual(receipt["scoring"]["n_trades"], 1)
        self.assertEqual(receipt["scoring"]["overall_verdict"], "INCONCLUSIVE")
        self.assertEqual(receipt["scoring"]["lane_a_verdict"], "INCONCLUSIVE")
        self.assertEqual(receipt["scoring"]["underlying_move"], 8.0)
        self.assertTrue(all(receipt["refusals"].values()))
        # Phase-aware: after Stage 8 activation the real store correctly has
        # seq-0. This synthetic-only proof must leave it valid and untouched,
        # not require it to be empty.
        self.assertTrue(before.valid)
        self.assertEqual(after, before)

    def test_receipt_is_independent_of_physical_temp_path(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            one = run_synthetic_proof(Path(left) / "proof")
            two = run_synthetic_proof(Path(right) / "proof")
        self.assertEqual(one, two)

    def test_real_forward_store_and_descendants_are_refused_untouched(self):
        real = Path(REAL_FORWARD_STORE)
        before = tuple(sorted(path.name for path in real.iterdir()))
        for path in (real, real / "stage7-looking-child"):
            with self.subTest(path=path):
                with self.assertRaises(ActivationBoundaryError):
                    run_synthetic_proof(path)
        self.assertEqual(tuple(sorted(path.name for path in real.iterdir())), before)

    def test_nonempty_fixture_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proof"
            root.mkdir()
            (root / "foreign.txt").write_text("do not overwrite")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                run_synthetic_proof(root)
            self.assertEqual((root / "foreign.txt").read_text(), "do not overwrite")


if __name__ == "__main__":
    unittest.main()

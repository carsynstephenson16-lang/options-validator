"""retrospective_result: a trial-counting chained record for publishing a
result whose inputs already exist (no new run). Tests use a TEMP ledger dir --
never the real ledger/."""
import tempfile
import unittest
from pathlib import Path

from research.ledger import (
    RETROSPECTIVE_REQUIRED_LABELS,
    LedgerError,
    append,
    current_trial_count,
    verify,
)

SHA = "a" * 64
GITSHA = "b" * 40


def rr_body(**over):
    body = {
        "entry_type": "retrospective_result",
        "timestamp": "2026-07-18T12:00:00+00:00",
        "subject": "QM base-rates study attempt publication",
        "hypothesis_id": None,
        "report_sha256": SHA,
        "context_sha256": SHA,
        "prereg_ref_sha256": SHA,
        "source_commit": GITSHA,
        "labels": list(RETROSPECTIVE_REQUIRED_LABELS),
        "result": {"parabolic_5d_excess": 0.0268},
    }
    body.update(over)
    return body


class TestRetrospectiveResult(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_appends_and_verifies(self):
        append(rr_body(), base_dir=self.base)
        verify(base_dir=self.base)  # must not raise

    def test_increments_trial_count(self):
        self.assertEqual(current_trial_count(self.base), 0)
        append(rr_body(), base_dir=self.base)
        self.assertEqual(current_trial_count(self.base), 1)
        append({"entry_type": "trial_intent",
                "timestamp": "2026-07-18T12:01:00+00:00",
                "reason": "H10a registration", "hypothesis_id": "H10a"},
               base_dir=self.base)
        self.assertEqual(current_trial_count(self.base), 2)

    def test_missing_required_label_rejected(self):
        labels = [x for x in RETROSPECTIVE_REQUIRED_LABELS if x != "no-verdict"]
        with self.assertRaises(LedgerError):
            append(rr_body(labels=labels), base_dir=self.base)

    def test_unknown_field_rejected(self):
        with self.assertRaises(LedgerError):
            append(rr_body(verdict="PASS"), base_dir=self.base)

    def test_bad_report_sha_rejected(self):
        with self.assertRaises(LedgerError):
            append(rr_body(report_sha256="deadbeef"), base_dir=self.base)

    def test_result_must_be_dict(self):
        with self.assertRaises(LedgerError):
            append(rr_body(result="looked fine"), base_dir=self.base)


if __name__ == "__main__":
    unittest.main()

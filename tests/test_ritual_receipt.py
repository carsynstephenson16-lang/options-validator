import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from options_researcher import ritual_receipt

AS_OF = "2026-07-21"
RUN_DATE = "2026-07-22"
STALE_AS_OF = "2026-07-20"
SCOPE_ID = "h7-forward-15-v1"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_complete_artifacts(root: Path) -> None:
    h5 = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
    h5.parent.mkdir(parents=True, exist_ok=True)
    h5.write_text(
        "H5 LEAPS ENTRY TRIGGER WATCH "
        f"evaluation_session={AS_OF}\n"
        f"VST: FIRE close $100.00 (as of {AS_OF}); "
        f"feature as of {AS_OF}; chain as of {AS_OF}\n"
        f"AMZN: WAIT close $230.00 (as of {AS_OF}); "
        f"feature as of {AS_OF}; chain as of {AS_OF}\n",
        encoding="utf-8",
    )

    _write_json(
        root / "reports/h6_forward" / f"{AS_OF}.json",
        {
            "snapshot": {
                "evaluation_session": AS_OF,
                "entries": [{"status": "BLOCKED"}],
                "exits": [],
            }
        },
    )
    _write_json(
        root / "reports/h7_data_gate" / SCOPE_ID / "receipts" / f"{AS_OF}.json",
        {"evaluation_session": AS_OF, "whole_universe_verdict": "GO"},
    )
    _write_json(
        root / "reports/h7_receipts" / SCOPE_ID / "watcher" / f"{AS_OF}.json",
        {"evaluation_session": AS_OF, "errors": [], "actionable_count": 0},
    )
    preflight = root / "reports/h7_receipts" / SCOPE_ID / "preflight" / f"{AS_OF}.txt"
    preflight.parent.mkdir(parents=True, exist_ok=True)
    preflight.write_text("H7 PREFLIGHT OK\nexit_code=0\n", encoding="utf-8")

    _write_json(
        root / "reports/h8_forward" / f"{AS_OF}.json",
        {
            "evaluation_session": AS_OF,
            "entries": [],
            "exits": [],
            "errors": [],
        },
    )
    receipt_path = root / "reports/h10/receipts" / f"h10_watch_{RUN_DATE}.json"
    _write_json(
        receipt_path,
        {
            "as_of": RUN_DATE,
            "evaluation_session": AS_OF,
            "evaluations": [
                {
                    "status": "NO_SIGNAL",
                    "signals": {"H10a": False, "H10b": False},
                }
            ],
        },
    )
    observations = root / "reports/h10/observations.jsonl"
    observations.parent.mkdir(parents=True, exist_ok=True)
    observations.write_text(
        json.dumps(
            {
                "as_of": RUN_DATE,
                "receipt": f"reports/h10/receipts/h10_watch_{RUN_DATE}.json",
                "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _run(root: Path) -> tuple[int, dict]:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        rc = ritual_receipt.main(
            ["--as-of", AS_OF, "--run-date", RUN_DATE],
            root=root,
            scope_id=SCOPE_ID,
        )
    receipt_path = root / "reports/ritual" / f"capture_receipt_{AS_OF}.json"
    return rc, json.loads(receipt_path.read_text(encoding="utf-8"))


class RitualReceiptTests(unittest.TestCase):
    def test_all_present_writes_five_captured_or_no_signal_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            rc, receipt = _run(root)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["as_of"], AS_OF)
        self.assertEqual(receipt["run_date"], RUN_DATE)
        self.assertEqual(set(receipt["hypotheses"]), {"H5", "H6", "H7", "H8", "H10"})
        statuses = {
            hypothesis: result["status"] for hypothesis, result in receipt["hypotheses"].items()
        }
        self.assertEqual(statuses["H5"], "CAPTURED")
        self.assertTrue(all(status in {"CAPTURED", "NO_SIGNAL"} for status in statuses.values()))

    def test_missing_artifact_exits_one_and_records_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            (root / "reports/h8_forward" / f"{AS_OF}.json").unlink()
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        self.assertEqual(receipt["hypotheses"]["H8"]["status"], "MISSING")
        self.assertIsNone(receipt["hypotheses"]["H8"]["evidence"])

    def test_yesterday_dated_artifact_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            expected = root / "reports/h6_forward" / f"{AS_OF}.json"
            expected.unlink()
            _write_json(
                root / "reports/h6_forward" / f"{STALE_AS_OF}.json",
                {"snapshot": {"evaluation_session": STALE_AS_OF}},
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H6"]
        self.assertEqual(result["status"], "MISSING")
        self.assertEqual(result["detail"], "stale")

    def test_h10_session_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            receipt_path = root / "reports/h10/receipts" / f"h10_watch_{RUN_DATE}.json"
            payload = json.loads(receipt_path.read_text(encoding="utf-8"))
            payload["evaluation_session"] = STALE_AS_OF
            _write_json(receipt_path, payload)
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H10"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "session mismatch")

    def test_h5_session_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace(AS_OF, STALE_AS_OF),
                encoding="utf-8",
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "session mismatch")

    def test_h5_data_gap_is_refused_not_no_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            artifact.write_text(
                "H5 LEAPS ENTRY TRIGGER WATCH "
                f"evaluation_session={AS_OF}\n"
                f"VST: DATA_GAP (needs exact session {AS_OF})\n"
                f"AMZN: WAIT close $230.00 (as of {AS_OF}); "
                f"feature as of {AS_OF}; chain as of {AS_OF}\n",
                encoding="utf-8",
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "data gap")

    def test_h5_omitted_tracked_name_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            artifact.write_text(
                "H5 LEAPS ENTRY TRIGGER WATCH "
                f"evaluation_session={AS_OF}\n"
                f"VST: WAIT close $170.00 (as of {AS_OF}); "
                f"feature as of {AS_OF}; chain as of {AS_OF}\n",
                encoding="utf-8",
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "tracked-name coverage mismatch")

    def test_empty_or_unparseable_json_is_missing(self):
        for malformed in ("", "{"):
            with self.subTest(malformed=repr(malformed)):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    _write_complete_artifacts(root)
                    artifact = root / "reports/h8_forward" / f"{AS_OF}.json"
                    artifact.write_text(malformed, encoding="utf-8")
                    rc, receipt = _run(root)

                self.assertEqual(rc, 1)
                self.assertEqual(receipt["hypotheses"]["H8"]["status"], "MISSING")

    def test_h8_blocked_entry_and_out_of_window_entry_are_no_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            _write_json(
                root / "reports/h8_forward" / f"{AS_OF}.json",
                {
                    "evaluation_session": AS_OF,
                    "entries": [
                        {"symbol": "PLTR", "status": "BLOCKED"},
                        {"symbol": "AMZN", "status": "OUT_OF_WINDOW"},
                    ],
                    "exits": [],
                    "errors": [],
                },
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 0)
        self.assertEqual(receipt["hypotheses"]["H8"]["status"], "NO_SIGNAL")


if __name__ == "__main__":
    unittest.main()

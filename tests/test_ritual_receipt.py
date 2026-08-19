import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import pandas as pd
from test_entry_watch import _h5_chain, _next_session
from test_schwab_chain_view import _write_store

import config
from options_researcher import entry_watch, ritual_receipt, schwab_chain_view
from options_researcher.h7_watch import evaluation_session
from options_researcher.h10_watch import MIXED_TIMING_CONVENTION

# Both lanes' floors are derived, never hardcoded (T1-3): the resume-floor
# constants are mechanical (seq 28/29 clause 5) and are updated at merge.
AS_OF = max(config.H10B_RESUME_FLOOR_SESSION, config.H5_RESUME_FLOOR_SESSION)
RUN_DATE = _next_session(AS_OF)
STALE_AS_OF = evaluation_session(date.fromisoformat(AS_OF)).isoformat()
_WALL_CLOCK = datetime.fromisoformat(f"{_next_session(RUN_DATE)}T12:00:00+00:00")
SCOPE_ID = "h7-forward-15-v1"
# H10b's four pre-starvation runs. These ARE frozen history (ledger seq 28
# clause 3), so they are correctly literal.
LEGACY_H10B_SESSIONS = {
    "2026-07-23": "2026-07-22",
    "2026-07-24": "2026-07-23",
    "2026-07-27": "2026-07-24",
    "2026-07-28": "2026-07-27",
}


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_real_h5_observer_report(root: Path, *, symbols: list[str] | None = None) -> Path:
    """Generate reports/h5/entry_watch_<AS_OF>.txt with the REAL observer.

    The H5 fixture is NOT hand-written prose. It used to be, and it drifted:
    the pinned text still spoke the retired WAIT/FIRE vocabulary long after the
    observer stopped emitting it, so every consumer test passed against a
    report shape that no longer existed. Generating it from
    `entry_watch.main()` makes that class of drift impossible.
    """
    captured = sorted(config.H5_ENTRY_TRIGGERS) if symbols is None else symbols
    _write_store(root, captured, session=AS_OF,
                 frames={symbol: _h5_chain() for symbol in captured})
    out = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    schwab_chain_view._reset_memo_for_tests()
    try:
        with (
            mock.patch.object(
                schwab_chain_view, "_dirs",
                return_value=(root / ".cache" / "schwab_chains",
                              root / "reports" / "schwab_chains")),
            mock.patch("data.underlying_closes.load_closes",
                       return_value=pd.Series([100.0], index=[AS_OF])),
            mock.patch.object(entry_watch, "datetime") as clock,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            clock.now.return_value = _WALL_CLOCK
            entry_watch.main(as_of=RUN_DATE, out=out)
    finally:
        schwab_chain_view._reset_memo_for_tests()
    return out


def _write_complete_artifacts(root: Path, *, h5_symbols: list[str] | None = None) -> None:
    _write_real_h5_observer_report(root, symbols=h5_symbols)

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
                    "signals": {"H10a": None, "H10b": False},
                    "h10a_status": "ADJUDICATED",
                }
            ],
        },
    )
    legacy_rows = []
    for legacy_run_date, legacy_evaluation_session in LEGACY_H10B_SESSIONS.items():
        legacy_receipt = root / "reports/h10/receipts" / f"h10_watch_{legacy_run_date}.json"
        _write_json(
            legacy_receipt,
            {
                "as_of": legacy_run_date,
                "evaluation_session": legacy_evaluation_session,
                "evaluations": [],
                "book_action_required": False,
            },
        )
        legacy_rows.append(
            {
                "as_of": legacy_run_date,
                "receipt": str(legacy_receipt.relative_to(root)),
                "receipt_sha256": hashlib.sha256(legacy_receipt.read_bytes()).hexdigest(),
                "summary": {"fired": [], "no_signal": [], "skipped": {}},
                "open_positions": 0,
            }
        )
    legacy_observations = root / "reports/h10/observations.jsonl"
    legacy_observations.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in legacy_rows),
        encoding="utf-8",
    )
    observations = root / "reports/h10/h10b_observations.jsonl"
    observations.parent.mkdir(parents=True, exist_ok=True)
    observations.write_text(
        json.dumps(
            {
                "as_of": RUN_DATE,
                "evaluation_session": AS_OF,
                "hypothesis": "H10b",
                "receipt": f"reports/h10/receipts/h10_watch_{RUN_DATE}.json",
                "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                "summary": {"fired": [], "no_signal": ["PLTR"], "skipped": {}},
                "open_positions": 0,
                "mixed_timing_convention": MIXED_TIMING_CONVENTION,
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


def _capture_stdout(root: Path) -> str:
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        ritual_receipt.main(
            ["--as-of", AS_OF, "--run-date", RUN_DATE],
            root=root,
            scope_id=SCOPE_ID,
        )
    return stdout.getvalue()


class H5ObserverEndToEndTests(unittest.TestCase):
    """F-1/F-2: the REAL observer's file, read by the REAL receipt builder."""

    def test_real_observer_output_renders_as_observe_mode_not_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = _write_real_h5_observer_report(root)
            text = artifact.read_text(encoding="utf-8")
            result = ritual_receipt.build_capture_receipt(
                as_of=AS_OF, run_date=RUN_DATE, root=root, scope_id=SCOPE_ID
            )["hypotheses"]["H5"]

        # The report really is the observer's own vocabulary...
        self.assertIn("H5 SCHWAB OBSERVER", text)
        self.assertIn("observational / non-verdict-bearing", text)
        self.assertIn("VST: OBSERVED", text)
        self.assertIn("AMZN: OBSERVED", text)
        self.assertNotIn("WAIT", text)
        self.assertNotIn("FIRE", text)
        # ...and the consumer reads it without refusing or claiming a signal.
        self.assertEqual(result["status"], "CAPTURED")
        self.assertIn("observe mode", result["detail"])
        self.assertIn("trigger retired", result["detail"])
        self.assertNotIn("signal", result["detail"])
        self.assertEqual(result["evidence"], f"reports/h5/entry_watch_{AS_OF}.txt")

    def test_real_observer_output_renders_as_observe_mode_on_the_evidence_board(self):
        """Same real file, second consumer: the per-symbol evidence gatherer."""
        from options_researcher.h7_cohort import CohortUnavailableError
        from options_researcher.hypothesis_evidence import gather_hypothesis_evidence

        def _no_cohort(_path):
            raise CohortUnavailableError("no cohort in this fixture")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            _run(root)  # writes reports/ritual/capture_receipt_<AS_OF>.json
            evidence = gather_hypothesis_evidence(
                ("AMZN",), root=root, cohort_loader=_no_cohort
            )

        row = next(item for item in evidence["AMZN"].hypotheses if item.family == "H5")
        self.assertEqual(row.symbol_states[0].state, "OBSERVING (trigger retired seq 29)")
        self.assertNotEqual(row.family_state, "REFUSED")
        self.assertNotIn("UNKNOWN", [state.state for state in row.symbol_states])
        self.assertIn("entry trigger retired", row.membership)
        self.assertEqual(row.evaluation_session, AS_OF)
        self.assertTrue(row.descriptive_only)


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
        self.assertIn("observe mode", receipt["hypotheses"]["H5"]["detail"])
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

    def test_h5_data_gap_is_refused_not_captured(self):
        """A REAL partial-capture observer report, not hand-written prose."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root, h5_symbols=["VST"])
            text = (root / "reports/h5" / f"entry_watch_{AS_OF}.txt").read_text(
                encoding="utf-8")
            rc, receipt = _run(root)

        self.assertIn("VST: OBSERVED", text)
        self.assertIn("AMZN: DATA_GAP", text)
        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "data gap")

    def test_h5_omitted_tracked_name_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            kept = [
                line
                for line in artifact.read_text(encoding="utf-8").splitlines()
                if not line.startswith("AMZN:")
            ]
            artifact.write_text("\n".join(kept) + "\n", encoding="utf-8")
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "tracked-name coverage mismatch")

    def test_h5_refuses_the_retired_trigger_vocabulary(self):
        """seq 29 clause 1: a report that says WAIT/FIRE is drift, not a signal.

        This is the guard that would have caught the 2026-08 defect where the
        receipt builder still DEMANDED `WAIT|FIRE` rows from a lane that had
        stopped emitting them.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            artifact.write_text(
                artifact.read_text(encoding="utf-8").replace("VST: OBSERVED", "VST: WAIT"),
                encoding="utf-8",
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "retired trigger vocabulary")

    def test_h5_observer_refusal_is_refused_not_captured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            artifact = root / "reports/h5" / f"entry_watch_{AS_OF}.txt"
            artifact.write_text(
                "H5 SCHWAB OBSERVER REFUSED max_asof_session=NONE "
                "observational / non-verdict-bearing "
                f"evaluation_session={AS_OF} is before resume floor\n",
                encoding="utf-8",
            )
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H5"]
        self.assertEqual(result["status"], "REFUSED")
        self.assertEqual(result["detail"], "observer refused")

    def test_h10_result_discloses_the_permanent_unobserved_session_hole(self):
        """T1-2: the union reader's hole reaches the persisted receipt."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            rc, receipt = _run(root)
            output = _capture_stdout(root)

        self.assertEqual(rc, 0)
        self.assertEqual(
            receipt["hypotheses"]["H10"]["unobserved_evaluation_sessions"],
            {
                "after_evaluation_session": "2026-07-27",
                "before_evaluation_session": config.H10B_RESUME_FLOOR_SESSION,
            },
        )
        # No other family invents one.
        for family in ("H5", "H6", "H7", "H8"):
            with self.subTest(family=family):
                self.assertNotIn(
                    "unobserved_evaluation_sessions", receipt["hypotheses"][family]
                )
        self.assertIn("permanently unobserved evaluation sessions after", output)

    def test_the_hole_is_disclosed_even_when_todays_observation_is_missing(self):
        """The hole is a property of the RECORD, not of a good day."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_complete_artifacts(root)
            (root / "reports/h10/h10b_observations.jsonl").unlink()
            rc, receipt = _run(root)

        self.assertEqual(rc, 1)
        result = receipt["hypotheses"]["H10"]
        self.assertEqual(result["status"], "MISSING")
        self.assertIn("unobserved_evaluation_sessions", result)

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

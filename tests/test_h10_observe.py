import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import config
from options_researcher import h10_observe, schwab_chain_capture
from options_researcher.h10_watch import H10A_ADJUDICATED, MIXED_TIMING_CONVENTION

AS_OF = "2026-08-20"
RECEIPT_REFERENCE = f"reports/h10/receipts/h10_watch_{AS_OF}.json"
BOOK_HEADER = (
    "id,symbol,strike,expiration,contracts,entry_date,entry_cost,"
    "entry_receipt_hash,exit_date,exit_proceeds,exit_reason,exit_receipt_hash\n"
)


def _evaluation(
    symbol: str,
    status: str,
    *,
    reason: str | None = None,
    action: bool = False,
) -> dict:
    return {
        "symbol": symbol,
        "signals": {
            "H10a": None,
            "H10b": status == "FIRED",
        },
        "h10a_status": H10A_ADJUDICATED,
        "window_status": {"H10b": "OPEN"},
        "status": status,
        "reason": reason,
        "admitted_contracts": 5 if status != "NO_SIGNAL" else 0,
        "candidate_contract": {"symbol": symbol} if status != "NO_SIGNAL" else None,
        "book_action_required": action,
        "chain_session": "2026-08-19" if status != "NO_SIGNAL" else None,
        "chain_timing_convention": MIXED_TIMING_CONVENTION,
    }


def _receipt() -> dict:
    return {
        "as_of": AS_OF,
        "evaluation_session": "2026-08-19",
        "evaluations": [
            _evaluation("PLTR", "FIRED", action=True),
            _evaluation("NVDA", "NO_SIGNAL"),
            _evaluation("AMD", "SKIPPED", reason="CAP"),
            _evaluation("TEM", "SKIPPED", reason="EARNINGS"),
        ],
        "book_action_required": True,
    }


def _write_receipt(path: Path, payload: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_receipt() if payload is None else payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_book(path: Path) -> None:
    path.write_text(
        BOOK_HEADER
        + f"h10-1,PLTR,100,2026-08-21,1,2026-07-01,500,{'a' * 64},,,,\n"
        + f"h10-2,NVDA,100,2026-08-21,1,2026-07-02,500,{'b' * 64},,,,\n"
        + (
            "h10-3,AMD,100,2026-08-21,1,2026-07-03,500,"
            f"{'c' * 64},2026-07-15,700,take_profit,{'d' * 64}\n"
        ),
        encoding="utf-8",
    )


def _run(root: Path):
    receipt = root / "h10_watch.json"
    observations = root / "h10b_observations.jsonl"
    legacy = root / "observations.jsonl"
    book = root / "h10_positions.csv"
    if not receipt.exists():
        _write_receipt(receipt)
    if not book.exists():
        _write_book(book)
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        rc = h10_observe.main(
            ["--as-of", AS_OF],
            receipt_path=receipt,
            observations_path=observations,
            legacy_observations_path=legacy,
            book_path=book,
        )
    return rc, stdout.getvalue(), receipt, observations, legacy, book


class AppendTests(unittest.TestCase):
    def test_appends_namespaced_h10b_record_and_counts_open_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, _, receipt, observations, legacy, _ = _run(root)
            lines = observations.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            expected_hash = hashlib.sha256(receipt.read_bytes()).hexdigest()

        self.assertEqual(rc, 0)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            set(record),
            {
                "hypothesis",
                "as_of",
                "evaluation_session",
                "receipt",
                "receipt_sha256",
                "summary",
                "open_positions",
                "mixed_timing_convention",
            },
        )
        self.assertEqual(record["hypothesis"], "H10b")
        self.assertEqual(record["as_of"], AS_OF)
        self.assertEqual(record["evaluation_session"], config.H10B_RESUME_FLOOR_SESSION)
        self.assertEqual(record["receipt"], RECEIPT_REFERENCE)
        self.assertEqual(record["receipt_sha256"], expected_hash)
        self.assertEqual(
            record["summary"],
            {
                "fired": ["PLTR"],
                "no_signal": ["NVDA"],
                "skipped": {"AMD": "CAP", "TEM": "EARNINGS"},
            },
        )
        self.assertEqual(record["open_positions"], 2)
        self.assertEqual(record["mixed_timing_convention"], MIXED_TIMING_CONVENTION)
        self.assertFalse(legacy.exists())

    def test_post_floor_recording_leaves_legacy_history_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "observations.jsonl"
            legacy.write_bytes(
                b'{"as_of":"2026-07-23","open_positions":0,"receipt":"legacy","receipt_sha256":"'
                + b"a" * 64
                + b'","summary":{"fired":[],"no_signal":[],"skipped":{}}}\n'
            )
            before = legacy.read_bytes()
            rc, _, _, observations, actual_legacy, _ = _run(root)
            observations_exist = observations.is_file()
            after = actual_legacy.read_bytes()

        self.assertEqual(rc, 0)
        self.assertTrue(observations_exist)
        self.assertEqual(before, after)


class IdempotenceTests(unittest.TestCase):
    def test_same_as_of_and_receipt_hash_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_rc, _, _, observations, _, _ = _run(root)
            first_bytes = observations.read_bytes()
            second_rc, output, _, _, _, _ = _run(root)
            second_bytes = observations.read_bytes()

        self.assertEqual((first_rc, second_rc), (0, 0))
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(len(second_bytes.splitlines()), 1)
        self.assertIn("already recorded", output)

    def test_same_as_of_and_different_receipt_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_rc, _, receipt, observations, _, _ = _run(root)
            before = observations.read_bytes()
            changed = _receipt()
            changed["evaluation_session"] = "2026-08-20"
            _write_receipt(receipt, changed)
            second_rc, output, _, _, _, _ = _run(root)
            after = observations.read_bytes()

        self.assertEqual(first_rc, 0)
        self.assertNotEqual(second_rc, 0)
        self.assertIn("CONFLICT", output)
        self.assertEqual(before, after)


class MalformedLogTests(unittest.TestCase):
    def test_malformed_existing_line_refuses_and_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observations = root / "h10b_observations.jsonl"
            observations.write_bytes(b'{"as_of": "broken"\n')
            before = observations.read_bytes()
            rc, output, _, _, _, _ = _run(root)
            after = observations.read_bytes()

        self.assertNotEqual(rc, 0)
        self.assertIn("MALFORMED", output)
        self.assertEqual(before, after)


class UnionTests(unittest.TestCase):
    def test_union_returns_legacy_and_h10b_rows_with_session_axis_hole(self):
        legacy_runs = {
            "2026-07-23": "2026-07-22",
            "2026-07-24": "2026-07-23",
            "2026-07-27": "2026-07-24",
            "2026-07-28": "2026-07-27",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "reports/h10/observations.jsonl"
            legacy.parent.mkdir(parents=True)
            legacy_rows = []
            for run_date, evaluation_session in legacy_runs.items():
                receipt_path = root / "reports/h10/receipts" / f"h10_watch_{run_date}.json"
                payload = _receipt()
                payload["as_of"] = run_date
                payload["evaluation_session"] = evaluation_session
                _write_receipt(receipt_path, payload)
                legacy_rows.append(
                    {
                        "as_of": run_date,
                        "receipt": str(receipt_path.relative_to(root)),
                        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
                        "summary": {"fired": [], "no_signal": ["NVDA"], "skipped": {}},
                        "open_positions": 0,
                    }
                )
            legacy.write_text(
                "".join(json.dumps(row, sort_keys=True) + "\n" for row in legacy_rows),
                encoding="utf-8",
            )
            h10b = root / "reports/h10/h10b_observations.jsonl"
            h10b.write_text(
                json.dumps(
                    {
                        "hypothesis": "H10b",
                        "as_of": AS_OF,
                        "evaluation_session": config.H10B_RESUME_FLOOR_SESSION,
                        "receipt": RECEIPT_REFERENCE,
                        "receipt_sha256": "b" * 64,
                        "summary": {"fired": [], "no_signal": ["NVDA"], "skipped": {}},
                        "open_positions": 0,
                        "mixed_timing_convention": MIXED_TIMING_CONVENTION,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            union = h10_observe.read_h10b_observation_union(
                root=root,
                legacy_observations_path=legacy,
                h10b_observations_path=h10b,
            )

        self.assertEqual(len(union["observations"]), 5)
        self.assertEqual(
            [row["evaluation_session"] for row in union["observations"]],
            ["2026-07-22", "2026-07-23", "2026-07-24", "2026-07-27", "2026-08-19"],
        )
        self.assertEqual(
            union["unobserved_evaluation_sessions"],
            {
                "after_evaluation_session": "2026-07-27",
                "before_evaluation_session": config.H10B_RESUME_FLOOR_SESSION,
            },
        )

    def test_h7_watchlist_is_covered_by_the_schwab_capture_universe(self):
        self.assertTrue(
            set(config.H7_WATCHLIST).issubset(set(schwab_chain_capture.watch_universe()))
        )


if __name__ == "__main__":
    unittest.main()

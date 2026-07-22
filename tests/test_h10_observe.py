import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from options_researcher import h10_observe

AS_OF = "2026-07-22"
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
            "H10a": status == "FIRED",
            "H10b": False,
        },
        "status": status,
        "reason": reason,
        "admitted_contracts": 5 if status != "NO_SIGNAL" else 0,
        "candidate_contract": {"symbol": symbol} if status != "NO_SIGNAL" else None,
        "book_action_required": action,
    }


def _receipt() -> dict:
    return {
        "as_of": AS_OF,
        "evaluation_session": "2026-07-21",
        "evaluations": [
            _evaluation("PLTR", "FIRED", action=True),
            _evaluation("NVDA", "NO_SIGNAL"),
            _evaluation("AMD", "SKIPPED", reason="CAP"),
            _evaluation("TEM", "SKIPPED", reason="EARNINGS"),
        ],
        "book_action_required": True,
    }


def _write_receipt(path: Path, payload: dict | None = None) -> None:
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
    observations = root / "observations.jsonl"
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
            book_path=book,
        )
    return rc, stdout.getvalue(), receipt, observations, book


class AppendTests(unittest.TestCase):
    def test_appends_exact_record_and_counts_open_positions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rc, _, receipt, observations, _ = _run(root)
            lines = observations.read_text(encoding="utf-8").splitlines()
            record = json.loads(lines[0])
            expected_hash = hashlib.sha256(receipt.read_bytes()).hexdigest()

        self.assertEqual(rc, 0)
        self.assertEqual(len(lines), 1)
        self.assertEqual(
            set(record),
            {"as_of", "receipt", "receipt_sha256", "summary", "open_positions"},
        )
        self.assertEqual(record["as_of"], AS_OF)
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


class IdempotenceTests(unittest.TestCase):
    def test_same_as_of_and_receipt_hash_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_rc, _, _, observations, _ = _run(root)
            first_bytes = observations.read_bytes()
            second_rc, output, _, _, _ = _run(root)
            second_bytes = observations.read_bytes()

        self.assertEqual((first_rc, second_rc), (0, 0))
        self.assertEqual(first_bytes, second_bytes)
        self.assertEqual(len(second_bytes.splitlines()), 1)
        self.assertIn("already recorded", output)

    def test_same_as_of_and_different_receipt_hash_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_rc, _, receipt, observations, _ = _run(root)
            before = observations.read_bytes()
            changed = _receipt()
            changed["evaluation_session"] = "2026-07-20"
            _write_receipt(receipt, changed)
            second_rc, output, _, _, _ = _run(root)
            after = observations.read_bytes()

        self.assertEqual(first_rc, 0)
        self.assertNotEqual(second_rc, 0)
        self.assertIn("CONFLICT", output)
        self.assertEqual(before, after)


class MalformedLogTests(unittest.TestCase):
    def test_malformed_existing_line_refuses_and_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            observations = root / "observations.jsonl"
            observations.write_bytes(b'{"as_of": "broken"\n')
            before = observations.read_bytes()
            rc, output, _, _, _ = _run(root)
            after = observations.read_bytes()

        self.assertNotEqual(rc, 0)
        self.assertIn("MALFORMED", output)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

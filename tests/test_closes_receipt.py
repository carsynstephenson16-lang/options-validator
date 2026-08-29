"""Offline tests for the closes-refresh provenance receipt (brief 33, DATA-03).

Every test here is offline: the close "fetcher" is a synthetic ``fetch_fn``
that writes parquet rows, exactly as the existing guarded-refresh tests do.
No provider endpoint is contacted and no real receipt directory is written.

The receipt binds the STORED file's sha256 -- see the honesty constraint above
``data.recent_topup.CLOSES_RECEIPT_DIR``. These tests assert that binding and
never assert anything about raw provider bytes, which the fetcher discards.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data import recent_topup, underlying_closes

REPO = Path(__file__).resolve().parents[1]
RITUAL = REPO / "tools" / "daily_ritual.sh"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ClosesReceiptTestCase(unittest.TestCase):
    """Isolated cache, ledger and receipt roots; nothing touches the repo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.cache_dir = root / "underlying"
        self.cache_dir.mkdir()
        self.ledger_dir = root / "ledger"
        self.receipts_dir = root / "closes_receipts"
        patch = mock.patch.object(underlying_closes, "CACHE_DIR", str(self.cache_dir))
        patch.start()
        self.addCleanup(patch.stop)

    def _store(self, symbol: str, rows) -> None:
        underlying_closes.store_closes(symbol, pd.DataFrame(rows, columns=["date", "close"]))

    def _path(self, symbol: str) -> Path:
        return self.cache_dir / f"{symbol}.parquet"

    def _facts(self) -> str:
        return (self.ledger_dir / "facts.log").read_text()

    def _guarded(self, *, today: str, fetch_fn) -> dict:
        return recent_topup.refresh_closes_guarded(
            today=today,
            ledger_dir=str(self.ledger_dir),
            fetch_fn=fetch_fn,
            receipts_dir=self.receipts_dir,
        )

    def _receipt(self, today: str, scope: str = recent_topup.GUARDED_CLOSES_SCOPE) -> dict:
        return json.loads((self.receipts_dir / today / f"{scope}.json").read_text())

    def _run_main(self, argv) -> tuple[int, str]:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = recent_topup.main(argv)
        return code, buffer.getvalue()


# --- scenario 1 -------------------------------------------------------------
class GuardedRefreshReceiptTests(ClosesReceiptTestCase):
    def _clean_run(self, today="2026-07-30"):
        self._store("AMZN", [("2026-07-28", 200.0)])
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch(symbol):
            close = 100.0 if symbol == "MSFT" else 200.0
            self._store(symbol, [("2026-07-28", close), ("2026-07-29", close + 1)])
            return str(self._path(symbol))

        return self._guarded(today=today, fetch_fn=fetch)

    def test_receipt_is_written_with_per_symbol_hashes_and_max_sessions(self):
        result = self._clean_run()
        path = self.receipts_dir / "2026-07-30" / "guarded-all-cached.json"
        self.assertTrue(path.is_file(), "guarded refresh must emit a dated, scoped receipt")
        self.assertEqual(result["receipt"], str(path))

        payload = json.loads(path.read_text())
        self.assertEqual(payload["schema"], "closes_refresh_receipt/v1")
        self.assertEqual(payload["producer"], "data.recent_topup.refresh_closes_guarded")
        self.assertEqual(payload["scope"], "guarded-all-cached")
        self.assertEqual(payload["run_date"], "2026-07-30")
        self.assertEqual(payload["requested_symbols"], ["AMZN", "MSFT"])
        self.assertRegex(payload["retrieved_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertIn("fetch", payload["provider"])

        for symbol in ("AMZN", "MSFT"):
            with self.subTest(symbol=symbol):
                entry = payload["symbols"][symbol]
                self.assertEqual(entry["outcome"], "refreshed")
                self.assertNotIn("stage", entry)
                self.assertEqual(entry["max_session"], "2026-07-29")
                self.assertEqual(entry["stored_file"], str(self._path(symbol)))
                self.assertEqual(entry["stored_file_sha256"], _sha256(self._path(symbol)))

    def test_the_hash_field_is_labelled_a_stored_file_binding_not_provider_bytes(self):
        """The schema must not claim provenance the fetcher cannot supply."""
        self._clean_run()
        payload = self._receipt("2026-07-30")
        self.assertIn("stored_file_sha256", payload["symbols"]["MSFT"])
        self.assertIn("NOT a hash", payload["hash_binding"])
        flat = json.dumps(payload)
        for forbidden in ("fetched_frame_sha256", "response_sha256", "raw_bytes_sha256"):
            with self.subTest(field=forbidden):
                self.assertNotIn(forbidden, flat)

    def test_the_data_pull_fact_names_the_receipt(self):
        self._clean_run()
        fact = self._facts()
        self.assertIn("Yahoo closes guarded refresh", fact)
        self.assertIn(
            f"receipt={self.receipts_dir / '2026-07-30' / 'guarded-all-cached.json'}", fact
        )

    def test_plain_refresh_uses_its_cli_scope_verbatim(self):
        def fetch(symbol):
            self._store(symbol, [("2026-07-29", 10.0)])
            return str(self._path(symbol))

        recent_topup.refresh_closes(
            ["MSFT", "AMZN"],
            today="2026-07-30",
            ledger_dir=str(self.ledger_dir),
            fetch_fn=fetch,
            scope="h7",
            receipts_dir=self.receipts_dir,
        )
        payload = self._receipt("2026-07-30", scope="h7")
        self.assertEqual(payload["producer"], "data.recent_topup.refresh_closes")
        self.assertEqual(payload["scope"], "h7")
        self.assertEqual(sorted(payload["symbols"]), ["AMZN", "MSFT"])
        self.assertEqual(
            payload["symbols"]["MSFT"]["stored_file_sha256"], _sha256(self._path("MSFT"))
        )
        self.assertIn("receipt=", self._facts())

    def test_receipt_directory_is_committed_in_tree(self):
        """A missing directory pathspec-fails `git add` and kills the whole
        evidence commit (tools/daily_ritual.sh:570 discards stderr and :571-573
        reports it as a mere note), so the directory must exist in-tree."""
        gitkeep = REPO / "reports" / "closes_receipts" / ".gitkeep"
        self.assertTrue(gitkeep.is_file(), f"{gitkeep} must exist so the directory is committable")
        git = shutil.which("git")
        if git is None or not (REPO / ".git").exists():
            self.skipTest("git checkout required")
        tracked = subprocess.run(
            [git, "-C", str(REPO), "ls-files", "--error-unmatch",
             "reports/closes_receipts/.gitkeep"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(tracked.returncode, 0, tracked.stdout + tracked.stderr)

    def test_ritual_stages_the_receipt_directory_at_the_data_tier(self):
        source = RITUAL.read_text(encoding="utf-8")
        array = [line for line in source.split("\n") if "DATA_TIER_PATHS=(" in line]
        self.assertEqual(len(array), 1)
        block = source[source.index("DATA_TIER_PATHS=(") : source.index("GIT_ADD_PATHS=")]
        self.assertIn("reports/closes_receipts", block)
        # ...and before the full-tier branch, so it is staged on data-tier days.
        durability = source[source.index("# Step 8 — DURABILITY") :]
        self.assertLess(
            durability.index("reports/closes_receipts"),
            durability.index('if [ "$FULL_AUTHORITY_RC" -eq 0 ]; then'),
        )


# --- scenario 2 -------------------------------------------------------------
class VerifyMutatedStoredFileTests(ClosesReceiptTestCase):
    def _one_symbol_run(self, today="2026-07-30"):
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch(symbol):
            self._store(symbol, [("2026-07-28", 100.0), ("2026-07-29", 101.0)])

        self._guarded(today=today, fetch_fn=fetch)
        return self.receipts_dir / today / "guarded-all-cached.json"

    def test_unmutated_stored_file_verifies_clean(self):
        receipt = self._one_symbol_run()
        code, output = self._run_main(["--verify-closes-receipt", str(receipt)])
        self.assertEqual(code, 0, output)
        report = json.loads(output)
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(report["symbols"]["MSFT"]["status"], "match")

    def test_mutated_stored_file_with_no_newer_receipt_exits_one_naming_the_symbol(self):
        receipt = self._one_symbol_run()
        self._store("MSFT", [("2026-07-28", 100.0), ("2026-07-29", 999.0)])
        code, output = self._run_main(["--verify-closes-receipt", str(receipt)])
        self.assertEqual(code, 1, output)
        self.assertIn("MSFT", output)
        report = json.loads(output)
        self.assertEqual(report["status"], "MISMATCH")
        self.assertEqual(report["mismatches"], ["MSFT"])
        self.assertEqual(report["symbols"]["MSFT"]["status"], "mismatch")
        self.assertNotEqual(
            report["symbols"]["MSFT"]["actual_sha256"],
            report["symbols"]["MSFT"]["expected_sha256"],
        )

    def test_a_deleted_stored_file_is_also_a_mismatch(self):
        receipt = self._one_symbol_run()
        self._path("MSFT").unlink()
        code, output = self._run_main(["--verify-closes-receipt", str(receipt)])
        self.assertEqual(code, 1, output)
        self.assertIsNone(json.loads(output)["symbols"]["MSFT"]["actual_sha256"])


# --- scenario 3 -------------------------------------------------------------
class RestoredOutcomeTests(ClosesReceiptTestCase):
    def test_restored_symbol_records_the_restored_pre_fetch_hash(self):
        self._store("MSFT", [("2026-07-28", 100.0)])
        self._store("AMZN", [("2026-07-28", 200.0)])
        pre_fetch_msft = _sha256(self._path("MSFT"))

        def fetch(symbol):
            if symbol == "MSFT":  # retroactive change -> guard rolls back
                self._store(symbol, [("2026-07-28", 101.0), ("2026-07-29", 102.0)])
            else:
                self._store(symbol, [("2026-07-28", 200.0), ("2026-07-29", 201.0)])

        result = self._guarded(today="2026-07-30", fetch_fn=fetch)
        self.assertEqual(result["restored_symbols"], {"MSFT": "2026-07-28"})

        entry = self._receipt("2026-07-30")["symbols"]["MSFT"]
        self.assertEqual(entry["outcome"], "restored")
        self.assertEqual(entry["retroactive_change_session"], "2026-07-28")
        self.assertEqual(entry["max_session"], "2026-07-28")
        # The hash is the true post-run state: the restored (pre-fetch) file.
        self.assertEqual(entry["stored_file_sha256"], _sha256(self._path("MSFT")))
        self.assertEqual(entry["stored_file_sha256"], pre_fetch_msft)
        self.assertEqual(self._receipt("2026-07-30")["symbols"]["AMZN"]["outcome"], "refreshed")

    def test_a_failed_rollback_is_not_labelled_restored(self):
        """The bytes on disk are the CHANGED ones, so `restored` would lie."""
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch(symbol):
            pd.DataFrame(
                [("2026-07-28", 101.0), ("2026-07-29", 102.0)], columns=["date", "close"]
            ).to_parquet(self._path(symbol), index=False)

        def failing_store(symbol, frame):
            raise OSError("disk full")

        with mock.patch.object(underlying_closes, "store_closes", failing_store):
            result = self._guarded(today="2026-07-30", fetch_fn=fetch)
        self.assertIn("MSFT", result["restore_failed"])

        entry = self._receipt("2026-07-30")["symbols"]["MSFT"]
        self.assertEqual(entry["outcome"], "failed")
        self.assertEqual(entry["stage"], "post_read")
        self.assertIn("disk full", entry["error"])
        self.assertEqual(entry["stored_file_sha256"], _sha256(self._path("MSFT")))


# --- scenario 4 -------------------------------------------------------------
class SupersededReceiptTests(ClosesReceiptTestCase):
    def test_an_older_receipt_reports_superseded_and_exits_zero(self):
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch_day_one(symbol):
            self._store(symbol, [("2026-07-28", 100.0), ("2026-07-29", 101.0)])

        def fetch_day_two(symbol):
            self._store(
                symbol,
                [("2026-07-28", 100.0), ("2026-07-29", 101.0), ("2026-07-30", 102.0)],
            )

        self._guarded(today="2026-07-30", fetch_fn=fetch_day_one)
        old = self.receipts_dir / "2026-07-30" / "guarded-all-cached.json"
        old_bytes = old.read_bytes()
        self._guarded(today="2026-07-31", fetch_fn=fetch_day_two)

        code, output = self._run_main(["--verify-closes-receipt", str(old)])
        self.assertEqual(code, 0, output)
        report = json.loads(output)
        self.assertEqual(report["status"], "OK")
        self.assertEqual(report["mismatches"], [])
        self.assertEqual(report["superseded"], ["MSFT"])
        self.assertEqual(report["symbols"]["MSFT"]["status"], "superseded")
        self.assertIn("2026-07-31", report["symbols"]["MSFT"]["superseded_by"])
        # Verification is read-only: the older receipt is untouched.
        self.assertEqual(old.read_bytes(), old_bytes)

        newest = self.receipts_dir / "2026-07-31" / "guarded-all-cached.json"
        code, output = self._run_main(["--verify-closes-receipt", str(newest)])
        self.assertEqual(code, 0, output)
        self.assertEqual(json.loads(output)["symbols"]["MSFT"]["status"], "match")

    def test_the_latest_receipt_still_alarms_when_its_bytes_change(self):
        """Supersession must not be a blanket amnesty for the newest receipt."""
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch(symbol):
            self._store(symbol, [("2026-07-28", 100.0), ("2026-07-29", 101.0)])

        self._guarded(today="2026-07-30", fetch_fn=fetch)
        self._guarded(today="2026-07-31", fetch_fn=fetch)
        newest = self.receipts_dir / "2026-07-31" / "guarded-all-cached.json"
        self._store("MSFT", [("2026-07-28", 100.0), ("2026-07-29", 999.0)])
        code, output = self._run_main(["--verify-closes-receipt", str(newest)])
        self.assertEqual(code, 1, output)
        self.assertEqual(json.loads(output)["mismatches"], ["MSFT"])


# --- scenario 5 -------------------------------------------------------------
class AllFetchesFailTests(ClosesReceiptTestCase):
    def test_every_fetch_failing_still_emits_a_receipt(self):
        self._store("MSFT", [("2026-07-28", 100.0)])
        self._store("AMZN", [("2026-07-28", 200.0)])
        hashes = {symbol: _sha256(self._path(symbol)) for symbol in ("MSFT", "AMZN")}

        def fetch(symbol):
            raise RuntimeError(f"simulated outage for {symbol}")

        result = self._guarded(today="2026-07-30", fetch_fn=fetch)
        self.assertEqual(sorted(result["fetch_errors"]), ["AMZN", "MSFT"])

        payload = self._receipt("2026-07-30")
        for symbol in ("AMZN", "MSFT"):
            with self.subTest(symbol=symbol):
                entry = payload["symbols"][symbol]
                self.assertEqual(entry["outcome"], "failed")
                self.assertEqual(entry["stage"], "fetch")
                self.assertIn("simulated outage", entry["error"])
                self.assertEqual(entry["max_session"], "2026-07-28")
                self.assertEqual(entry["stored_file_sha256"], hashes[symbol])
        self.assertIn("receipt=", self._facts())

    def test_pre_and_post_read_failures_carry_their_own_stage(self):
        (self.cache_dir / "BAD.parquet").write_bytes(b"not parquet")
        self._store("POST", [("2026-07-28", 300.0)])

        def fetch(symbol):
            if symbol == "POST":
                pd.DataFrame({"wrong": [1]}).to_parquet(self._path("POST"), index=False)
                return
            raise AssertionError("pre-read failure must skip fetch")

        self._guarded(today="2026-07-30", fetch_fn=fetch)
        payload = self._receipt("2026-07-30")
        self.assertEqual(payload["symbols"]["BAD"]["stage"], "pre_read")
        self.assertEqual(payload["symbols"]["POST"]["stage"], "post_read")
        for symbol in ("BAD", "POST"):
            with self.subTest(symbol=symbol):
                self.assertEqual(payload["symbols"][symbol]["outcome"], "failed")
        # No symbol is ever reported as skipped: every globbed name is attempted.
        outcomes = {entry["outcome"] for entry in payload["symbols"].values()}
        self.assertTrue(outcomes <= set(recent_topup.CLOSES_OUTCOMES), outcomes)

    def test_the_frozen_vocabulary_refuses_an_unknown_outcome_or_stage(self):
        with self.assertRaises(ValueError):
            recent_topup._closes_entry("skipped", None, None)
        with self.assertRaises(ValueError):
            recent_topup._closes_entry("failed", None, None, stage="restore")
        with self.assertRaises(ValueError):
            recent_topup._closes_entry("refreshed", None, None, stage="fetch")


# --- scenario 7 -------------------------------------------------------------
class OverwriteGuardTests(ClosesReceiptTestCase):
    def test_same_day_rerun_with_a_differing_payload_refuses(self):
        self._store("MSFT", [("2026-07-28", 100.0)])

        def fetch_first(symbol):
            self._store(symbol, [("2026-07-28", 100.0), ("2026-07-29", 101.0)])

        def fetch_second(symbol):
            self._store(
                symbol,
                [("2026-07-28", 100.0), ("2026-07-29", 101.0), ("2026-07-30", 102.0)],
            )

        self._guarded(today="2026-07-30", fetch_fn=fetch_first)
        receipt = self.receipts_dir / "2026-07-30" / "guarded-all-cached.json"
        first_bytes = receipt.read_bytes()

        with self.assertRaises(FileExistsError):
            self._guarded(today="2026-07-30", fetch_fn=fetch_second)

        self.assertEqual(receipt.read_bytes(), first_bytes, "the first receipt must survive")
        # The refresh really happened, so the run is still recorded -- with an
        # honest UNWRITTEN marker rather than a path that does not describe it.
        self.assertIn("receipt=UNWRITTEN (FileExistsError", self._facts())

    def test_a_byte_identical_replay_is_a_no_op(self):
        payload = recent_topup._closes_receipt_payload(
            producer="data.recent_topup.refresh_closes_guarded",
            scope=recent_topup.GUARDED_CLOSES_SCOPE,
            run_date="2026-07-30",
            provider="tests.synthetic",
            requested_symbols=["MSFT"],
            symbols={"MSFT": recent_topup._closes_entry("refreshed", None, "2026-07-29")},
        )
        first = recent_topup.write_closes_receipt(payload, receipts_dir=self.receipts_dir)
        before = first.read_bytes()
        second = recent_topup.write_closes_receipt(payload, receipts_dir=self.receipts_dir)
        self.assertEqual(first, second)
        self.assertEqual(second.read_bytes(), before)

    def test_no_stray_temp_file_survives_a_refusal(self):
        payload = recent_topup._closes_receipt_payload(
            producer="data.recent_topup.refresh_closes",
            scope="core",
            run_date="2026-07-30",
            provider="tests.synthetic",
            requested_symbols=["MSFT"],
            symbols={"MSFT": recent_topup._closes_entry("refreshed", None, "2026-07-29")},
        )
        recent_topup.write_closes_receipt(payload, receipts_dir=self.receipts_dir)
        other = dict(payload, retrieved_utc="2999-01-01T00:00:00Z")
        with self.assertRaises(FileExistsError):
            recent_topup.write_closes_receipt(other, receipts_dir=self.receipts_dir)
        dated = self.receipts_dir / "2026-07-30"
        self.assertEqual([p.name for p in sorted(dated.iterdir())], ["core.json"])


if __name__ == "__main__":
    unittest.main()

"""Fixture-only tests for the Schwab H7 durable data-gate receipt command."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from options_researcher import h7_data_gate, h7_schwab_data_gate, h7_schwab_quote_age_gate
from options_researcher.h7_cohort import RegisteredCohort
from options_researcher.h7_scope import scope_identity, watch_universe
from research.hashing import canonical_json, sha256_file
from research.receipts import load_receipt, make_receipt, write_immutable_receipt
from tools import h7_forward_backup, h7_schwab_manual_activate, schwab_chain_manifest
from tools import h7_schwab_data_gate_receipt as cli

SESSION = "2026-08-10"
AS_OF = "2026-08-11"
SYMBOLS = sorted(watch_universe())


def _chain_frame() -> pd.DataFrame:
    rows = []
    timestamp = pd.Timestamp("2026-08-10T19:59:00Z")
    for expiration in ("2026-08-21", "2026-09-18"):
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "bid": 1.0,
                    "ask": 1.1,
                    "open_interest": 100,
                    "iv": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                    "timestamp": timestamp,
                }
            )
    return pd.DataFrame(rows)


class SchwabDataGateReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.chain_dir = self.root / "chains"
        self.close_dir = self.root / "closes"
        self.reports_root = self.root / "reports" / "schwab_chains"
        self.package_dir = self.reports_root / SESSION
        self.output_root = self.root / "reports" / "h7_data_gate_schwab"
        self.legacy_root = self.root / "reports" / "h7_data_gate"
        self.chain_dir.mkdir(parents=True)
        self.close_dir.mkdir(parents=True)
        self.package_dir.mkdir(parents=True)
        for symbol in SYMBOLS:
            _chain_frame().to_parquet(self.chain_dir / f"{symbol}_{SESSION}.parquet")
            pd.DataFrame({"date": [SESSION], "close": [100.0]}).to_parquet(
                self.close_dir / f"{symbol}.parquet"
            )
        self._write_package()
        self.source_path = self.root / "source-health.json"
        self.source_receipt = self._write_source(self.source_path)

    @property
    def manifest_path(self) -> Path:
        return self.package_dir / "manifest.json"

    @property
    def capture_receipt_path(self) -> Path:
        return self.package_dir / "preclose.json"

    @property
    def artifact_path(self) -> Path:
        return self.output_root / scope_identity()["scope_id"] / f"{SESSION}.json"

    @property
    def data_receipt_path(self) -> Path:
        return self.output_root / scope_identity()["scope_id"] / "receipts" / f"{SESSION}.json"

    def _write_package(self) -> None:
        manifest = schwab_chain_manifest.build_manifest(SESSION, SYMBOLS, self.chain_dir)
        schwab_chain_manifest.write_manifest(manifest, self.manifest_path)
        names = {}
        for symbol in SYMBOLS:
            path = self.chain_dir / f"{symbol}_{SESSION}.parquet"
            frame = pd.read_parquet(path)
            names[symbol] = {
                "status": "ok",
                "row_count": len(frame),
                "expiration_count": int(frame["expiration"].nunique()),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        self.capture_receipt_path.write_text(
            json.dumps(
                {
                    "receipt_kind": "schwab_chain_capture/v1",
                    "session": SESSION,
                    "session_chain_convention": "preclose_snapshot_v1",
                    "captured_at_et": "2026-08-10T15:45:00-04:00",
                    "scheduled_session_tag": "preclose",
                    "force": False,
                    "universe": SYMBOLS,
                    "overall_status": "ok",
                    "names": names,
                    "manifest_hash": manifest["manifest_hash"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _write_source(
        self,
        path: Path,
        *,
        session: str = SESSION,
        scope: dict | None = None,
        input_files: dict | None = None,
    ) -> dict:
        receipt = make_receipt(
            "source_health",
            {
                "evaluation_session": session,
                "scope": scope_identity() if scope is None else scope,
                "symbols": {symbol: {"healthy": True, "gate": "CLEAR"} for symbol in SYMBOLS},
                **({"input_files": input_files} if input_files is not None else {}),
            },
        )
        write_immutable_receipt(receipt, path)
        return receipt

    def _cohort(self) -> RegisteredCohort:
        included = tuple(SYMBOLS[:9])
        return RegisteredCohort(
            included=included,
            excluded={symbol: "fixture exclusion" for symbol in SYMBOLS[9:]},
            event_id="fixture-seq-0",
        )

    def _args(
        self,
        *,
        as_of: str = AS_OF,
        source_path: Path | None = None,
        reports_root: Path | None = None,
    ) -> list[str]:
        return [
            "--as-of",
            as_of,
            "--source-health-receipt",
            str(source_path or self.source_path),
            "--chain-dir",
            str(self.chain_dir),
            "--reports-root",
            str(reports_root or self.reports_root),
            "--close-dir",
            str(self.close_dir),
            "--output-root",
            str(self.output_root),
        ]

    def _run(self, args: list[str] | None = None) -> tuple[int, str]:
        def load_fixture_cohort() -> RegisteredCohort:
            return self._cohort()

        output = io.StringIO()
        with (
            mock.patch.object(cli, "load_registered_cohort", new=load_fixture_cohort),
            contextlib.redirect_stdout(output),
        ):
            status = cli.main(self._args() if args is None else args)
        return status, output.getvalue()

    def _evaluate_raw(self) -> dict:
        return h7_schwab_data_gate.evaluate(
            date.fromisoformat(AS_OF),
            close_dir=self.close_dir,
            chain_dir=self.chain_dir,
            manifest_path=self.manifest_path,
            receipt_path=self.capture_receipt_path,
        )

    def test_happy_path_writes_only_the_schwab_namespace_and_closes_receipt_chain(
        self,
    ) -> None:
        status, output = self._run()

        self.assertEqual(status, 0, output)
        self.assertTrue(self.artifact_path.is_file())
        self.assertTrue(self.data_receipt_path.is_file())
        self.assertFalse(self.legacy_root.exists())
        receipt = load_receipt(self.data_receipt_path, expected_type="data_gate")
        self.assertEqual(receipt["evidence_mode"], h7_schwab_data_gate.EVIDENCE_MODE)
        self.assertEqual(
            receipt["source_health_receipt_hash"],
            self.source_receipt["receipt_hash"],
        )
        self.assertEqual(receipt["source_health_receipt_path"], str(self.source_path))
        self.assertEqual(h7_data_gate.validate_durable_receipt(receipt), SYMBOLS)
        backup_path = self.root / "backup-restore.json"
        write_immutable_receipt(
            make_receipt(
                "backup_restore",
                {
                    "scope": scope_identity(),
                    "completed_session": SESSION,
                    "verification": {"ok": True},
                },
            ),
            backup_path,
        )
        h7_schwab_manual_activate._validate_receipt_chain(
            source_health_path=self.source_path,
            data_gate_path=self.data_receipt_path,
            backup_restore_path=backup_path,
            completed_session=SESSION,
        )
        self.assertIn(f"immutable receipt {self.data_receipt_path}", output)
        self.assertIn("whole_universe_verdict=GO", output)
        self.assertIn("included_subset_verdict=GO", output)
        self.assertIn("AWAITING_OWNER_THRESHOLD", output)

    def test_source_session_and_scope_mismatches_refuse_before_output(self) -> None:
        cases = (
            ("wrong-session.json", "2026-08-07", scope_identity()),
            ("wrong-scope.json", SESSION, scope_identity(SYMBOLS[:-1])),
        )
        for filename, session, scope in cases:
            with self.subTest(filename=filename):
                path = self.root / filename
                self._write_source(path, session=session, scope=scope)
                status, output = self._run(self._args(source_path=path))
                self.assertEqual(status, 2, output)
                self.assertFalse(self.output_root.exists())

    def test_missing_package_refuses_for_the_strictly_prior_session(self) -> None:
        missing_reports = self.root / "missing-reports"

        status, output = self._run(self._args(as_of="2026-09-08", reports_root=missing_reports))

        self.assertEqual(status, 2, output)
        self.assertIn("NO_PACKAGE_FOR_SESSION 2026-09-04", output)
        self.assertFalse(self.output_root.exists())

    def test_tampered_manifest_refuses_without_writing(self) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        manifest["manifest_hash"] = "0" * 64
        self.manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")

        status, output = self._run()

        self.assertEqual(status, 2, output)
        self.assertIn(h7_schwab_data_gate.SCHWAB_PACKAGE_INVALID, output)
        self.assertFalse(self.output_root.exists())

    def test_missing_manifest_bound_parquet_refuses_without_writing(self) -> None:
        (self.chain_dir / f"{SYMBOLS[0]}_{SESSION}.parquet").unlink()

        status, output = self._run()

        self.assertEqual(status, 2, output)
        self.assertIn(h7_schwab_data_gate.SCHWAB_PACKAGE_INVALID, output)
        self.assertFalse(self.output_root.exists())

    def test_included_no_go_exits_one_but_excluded_no_go_exits_zero(self) -> None:
        cohort = self._cohort()
        cases = ((cohort.included[0], 1), (next(iter(cohort.excluded)), 0))
        for symbol, expected_status in cases:
            with self.subTest(symbol=symbol):
                close_path = self.close_dir / f"{symbol}.parquet"
                original = close_path.read_bytes()
                close_path.unlink()
                status, output = self._run()
                self.assertEqual(status, expected_status, output)
                self.assertTrue(self.data_receipt_path.is_file())
                self.assertIn(
                    "included_subset_verdict=" + ("NO_GO" if expected_status else "GO"),
                    output,
                )
                close_path.write_bytes(original)
                if self.output_root.exists():
                    for path in sorted(self.output_root.rglob("*"), reverse=True):
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            path.rmdir()

    def test_quote_age_rejects_raw_result_then_accepts_built_receipt_in_mode_a(
        self,
    ) -> None:
        raw = self._evaluate_raw()
        included = self._cohort().included

        invalid = h7_schwab_quote_age_gate.evaluate_schwab_quote_age(
            data_gate_receipt=raw,
            included_symbols=included,
        )
        status, output = self._run()

        self.assertEqual(invalid["whole_universe_verdict"], "EVIDENCE_INVALID")
        self.assertTrue(
            all(
                row["reason_codes"] == [h7_schwab_quote_age_gate.QUOTE_AGE_EVIDENCE_INVALID]
                for row in invalid["symbols"].values()
            )
        )
        self.assertEqual(status, 0, output)
        self.assertIn("quote_age_verdict=AWAITING_OWNER_THRESHOLD", output)

    def test_mode_b_over_threshold_exits_three_without_changing_receipt_bytes(
        self,
    ) -> None:
        with mock.patch.object(
            config, "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES", 0.0, create=True
        ):
            expected = h7_data_gate.build_receipt(
                self._evaluate_raw(),
                source_health_receipt=self.source_receipt,
                source_health_receipt_path=self.source_path,
            )
            before_quote = canonical_json(expected) + "\n"
            status, output = self._run()
        self.assertEqual(status, 3, output)
        self.assertIn(h7_schwab_quote_age_gate.QUOTE_AGE_OVER_THRESHOLD, output)
        self.assertEqual(self.data_receipt_path.read_text(), before_quote)

    def test_mode_b_invalid_threshold_is_not_reported_as_over_threshold(self):
        with mock.patch.object(
            config, "H7_SCHWAB_QUOTE_AGE_ABSOLUTE_MAX_MINUTES", -1.0, create=True
        ):
            status, output = self._run()
        self.assertEqual(status, 0, output)
        self.assertIn("EVIDENCE_INVALID", output)
        self.assertIn("absolute quote-age threshold is invalid", output)
        self.assertTrue(self.data_receipt_path.is_file())

    def test_direct_command_help_without_pythonpath(self):
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        completed = subprocess.run(
            [sys.executable, "tools/h7_schwab_data_gate_receipt.py", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--source-health-receipt", completed.stdout)

    def test_legacy_output_namespace_is_refused_before_any_write(self):
        for root in (h7_data_gate.DEFAULT_REPORTS_DIR, h7_data_gate.DEFAULT_REPORTS_DIR / "nested"):
            with self.subTest(root=str(root)):
                args = self._args()
                args[args.index("--output-root") + 1] = str(root)
                with contextlib.chdir(self.root):
                    status, output = self._run(args)
                self.assertEqual(status, 2, output)
                self.assertIn("legacy", output.lower())
                self.assertFalse(self.output_root.exists())

    def test_conflicting_receipt_refuses_before_creating_artifact(self) -> None:
        write_immutable_receipt(
            make_receipt("data_gate", {"fixture": "conflict"}),
            self.data_receipt_path,
        )

        status, output = self._run()

        self.assertEqual(status, 2, output)
        self.assertIn("refusing to overwrite", output)
        self.assertFalse(self.artifact_path.exists())

    def test_changed_source_input_refuses_before_creating_outputs(self) -> None:
        bound = self.root / "source-input.txt"
        bound.write_text("sealed\n", encoding="utf-8")
        source_path = self.root / "source-with-input.json"
        self._write_source(
            source_path,
            input_files={
                "earnings:fixture": {
                    "path": str(bound),
                    "exists": True,
                    "sha256": sha256_file(bound),
                }
            },
        )
        bound.write_text("changed\n", encoding="utf-8")

        status, output = self._run(self._args(source_path=source_path))

        self.assertEqual(status, 2, output)
        self.assertIn("source-health inputs changed", output)
        self.assertFalse(self.output_root.exists())


class BackupSchwabNamespaceTests(unittest.TestCase):
    def test_restore_scan_counts_whole_go_receipt_in_schwab_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chain = root / ".cache/chains/one.parquet"
            chain.parent.mkdir(parents=True)
            chain.write_bytes(b"chain")
            digest = hashlib.sha256(b"chain").hexdigest()
            manifest = root / "data/chain_cache_manifest.txt"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(f"{digest}  5  one.parquet\n", encoding="utf-8")
            receipt_path = (
                root
                / "reports/h7_data_gate_schwab"
                / scope_identity()["scope_id"]
                / "receipts"
                / f"{SESSION}.json"
            )
            receipt = make_receipt(
                "data_gate",
                {
                    "scope": scope_identity(),
                    "whole_universe_verdict": "GO",
                    "go_count": len(SYMBOLS),
                    "input_files": {
                        "chain": {
                            "path": ".cache/chains/one.parquet",
                            "exists": True,
                            "sha256": digest,
                        }
                    },
                },
            )
            write_immutable_receipt(receipt, receipt_path)

            result = h7_forward_backup.verify_restored_tree(root)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["data_gates"], 1)
            self.assertIn(
                Path("reports/h7_data_gate_schwab"),
                h7_forward_backup.BACKUP_PATHS,
            )


if __name__ == "__main__":
    unittest.main()

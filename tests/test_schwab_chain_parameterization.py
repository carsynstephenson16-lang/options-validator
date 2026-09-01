"""Characterization tests for Schwab chain capture core parameterization.

Brief 32 adds the two capture-flow tests at the bottom of this file: they reuse
this module's `_isolated_capture()` harness to prove the descriptive quote-age
sidecar cannot alter the capture's bytes, exit code, or `verify_session`'s
output.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

from options_researcher import schwab_chain_capture as capture
from options_researcher import schwab_quote_age_report as quote_age
from tools import schwab_chain_manifest as manifest

NY = ZoneInfo("America/New_York")
PRECLOSE = pd.Timestamp("2026-08-10T15:45:00", tz=NY).to_pydatetime()
MIDDAY = pd.Timestamp("2026-08-10T13:00:00", tz=NY).to_pydatetime()


def full_frame() -> pd.DataFrame:
    rows = []
    for expiration in ("2026-08-21", "2026-09-18"):
        for right, delta in (("C", 0.4), ("P", -0.4)):
            rows.append(
                {
                    "expiration": expiration,
                    "strike": 100.0,
                    "right": right,
                    "contract_symbol": f"AAA-{expiration}-{right}-100",
                    "bid": 1.0,
                    "ask": 1.2,
                    "open_interest": 100,
                    "implied_vol": 0.30,
                    "delta": delta,
                    "gamma": 0.02,
                    "theta": -0.03,
                    "vega": 0.10,
                    "multiplier": 100.0,
                    "non_standard": False,
                    "mini": False,
                    "timestamp": pd.Timestamp("2026-08-10T19:44:30Z"),
                    "trade_timestamp": pd.Timestamp("2026-08-10T19:44:20Z"),
                }
            )
    return pd.DataFrame(rows)


class FakeClient:
    provider_name = "schwab"
    provider_version = "test"

    def option_full_chain(self, symbol: str) -> pd.DataFrame:
        if symbol != "AAA":
            raise AssertionError(f"unexpected symbol: {symbol}")
        return full_frame()


class SchwabChainParameterizationTests(unittest.TestCase):
    @contextmanager
    def _isolated_capture(self):
        with tempfile.TemporaryDirectory() as tmp:
            prior_cwd = Path.cwd()
            os.chdir(tmp)
            try:
                with (
                    mock.patch.object(capture, "FACTS_DIR", Path("ledger")),
                    mock.patch.object(
                        capture,
                        "_write_parquet_once",
                        side_effect=self._write_golden_chain,
                    ),
                    mock.patch.object(
                        manifest.pd,
                        "read_parquet",
                        side_effect=self._read_golden_chain,
                    ),
                    mock.patch.object(capture, "_code_sha", return_value="golden-code-sha"),
                    mock.patch.object(capture, "config_hash", return_value="golden-config-hash"),
                    mock.patch.object(capture, "resolve_invocation_source", return_value="manual"),
                ):
                    yield
            finally:
                os.chdir(prior_cwd)

    @staticmethod
    def _write_golden_chain(frame: pd.DataFrame, path: Path) -> None:
        del frame
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"golden-chain\n")

    @staticmethod
    def _read_golden_chain(path: Path) -> pd.DataFrame:
        del path
        return (
            full_frame()
            .rename(columns={"implied_vol": "iv"})
            .reindex(columns=capture.H7_CHAIN_COLUMNS)
        )

    def test_default_capture_manifest_and_receipt_match_pre_parameterization_bytes(self):
        expected_manifest = """{
  "files": {
    "AAA": {
      "expiration_count": 2,
      "path": "AAA_2026-08-10.parquet",
      "row_count": 4,
      "sha256": "f0893fc4aedbfd89f0dca0593bfe7f74508bc2aed4b85f796969854dd12620c3",
      "size_bytes": 13
    }
  },
  "manifest_hash": "a1667c3e89511d76882aa4afc2953ce48a47799ed334f1be38a438efd8e8a9f0",
  "provider": "schwab",
  "schema_version": "schwab-chain-manifest/v1",
  "session": "2026-08-10",
  "session_chain_convention": "preclose_snapshot_v1",
  "symbols": [
    "AAA"
  ]
}
"""
        expected_receipt = """{
  "captured_at_et": "2026-08-10T15:45:00-04:00",
  "captured_at_utc": "2026-08-10T19:45:00+00:00",
  "code_sha": "golden-code-sha",
  "config_hash": "golden-config-hash",
  "force": false,
  "invocation_source": "manual",
  "manifest_hash": "a1667c3e89511d76882aa4afc2953ce48a47799ed334f1be38a438efd8e8a9f0",
  "manifest_path": "reports/2026-08-10/manifest.json",
  "names": {
    "AAA": {
      "expiration_count": 2,
      "path": "chains/AAA_2026-08-10.parquet",
      "row_count": 4,
      "sha256": "f0893fc4aedbfd89f0dca0593bfe7f74508bc2aed4b85f796969854dd12620c3",
      "size_bytes": 13,
      "status": "ok"
    }
  },
  "overall_status": "ok",
  "provider": "schwab",
  "provider_version": "test",
  "receipt_kind": "schwab_chain_capture/v1",
  "scheduled_session_tag": "preclose",
  "session": "2026-08-10",
  "session_chain_convention": "preclose_snapshot_v1",
  "timing_validation": "within 10min of the scheduled time",
  "universe": [
    "AAA"
  ]
}
"""

        with self._isolated_capture():
            exit_code, receipt = capture.capture(
                client=FakeClient(),
                now_ny=PRECLOSE,
                universe=["AAA"],
                chain_dir=Path("chains"),
                reports_dir=Path("reports"),
                force=False,
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(receipt["receipt_kind"], "schwab_chain_capture/v1")
            self.assertEqual(receipt["session_chain_convention"], "preclose_snapshot_v1")
            self.assertEqual(
                Path("reports/2026-08-10/manifest.json").read_text(),
                expected_manifest,
            )
            self.assertEqual(
                Path("reports/2026-08-10/preclose.json").read_text(),
                expected_receipt,
            )

    def test_capture_identity_parameters_are_keyword_only_with_legacy_defaults(self):
        parameters = inspect.signature(capture.capture).parameters
        expected = {
            "session_tag": "preclose",
            "receipt_filename": "preclose.json",
            "fact_prefix": "SCHWAB_CHAIN_CAPTURE",
            "receipt_kind": "schwab_chain_capture/v1",
            "convention": manifest.SESSION_CHAIN_CONVENTION,
        }

        self.assertEqual(
            {
                name: (parameters[name].default if name in parameters else inspect.Parameter.empty)
                for name in expected
            },
            expected,
        )
        self.assertTrue(
            all(
                name in parameters and parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
                for name in expected
            )
        )

    def test_manifest_core_accepts_isolated_lane_identity_keywords(self):
        expected_by_function = {
            manifest.build_manifest: {
                "convention": manifest.SESSION_CHAIN_CONVENTION,
                "receipt_filename": "preclose.json",
                "session_tag": "preclose",
            },
            manifest.verify_session: {
                "convention": manifest.SESSION_CHAIN_CONVENTION,
                "receipt_filename": "preclose.json",
                "session_tag": "preclose",
                "receipt_kind": "schwab_chain_capture/v1",
            },
        }
        for function, expected in expected_by_function.items():
            with self.subTest(function=function.__name__):
                parameters = inspect.signature(function).parameters
                self.assertEqual(
                    {
                        name: (
                            parameters[name].default
                            if name in parameters
                            else inspect.Parameter.empty
                        )
                        for name in expected
                    },
                    expected,
                )
                self.assertTrue(
                    all(
                        parameters[name].kind is inspect.Parameter.KEYWORD_ONLY for name in expected
                    )
                )

    def test_manifest_core_retains_pre_existing_positional_call_compatibility(self):
        with self._isolated_capture():
            exit_code, _ = capture.capture(
                client=FakeClient(),
                now_ny=PRECLOSE,
                universe=["AAA"],
                chain_dir=Path("chains"),
                reports_dir=Path("reports"),
                force=False,
            )
            self.assertEqual(exit_code, 0)

            rebuilt = manifest.build_manifest("2026-08-10", ["AAA"], Path("chains"))
            verified = manifest.verify_session(
                "2026-08-10",
                ["AAA"],
                Path("chains"),
                Path("reports/2026-08-10/manifest.json"),
                Path("reports/2026-08-10/preclose.json"),
            )

            self.assertEqual(rebuilt["manifest_hash"], verified["manifest_hash"])
            self.assertEqual(verified["session_chain_convention"], "preclose_snapshot_v1")

    def test_custom_identity_is_threaded_through_capture_manifest_verify_and_fact(self):
        with self._isolated_capture():
            try:
                exit_code, receipt = capture.capture(
                    client=FakeClient(),
                    now_ny=MIDDAY,
                    universe=["AAA"],
                    chain_dir=Path("chains"),
                    reports_dir=Path("reports"),
                    force=False,
                    session_tag="midday",
                    receipt_filename="midday.json",
                    fact_prefix="SCHWAB_CHAIN_MIDDAY",
                    receipt_kind="schwab_chain_midday/v1",
                    convention="midday_snapshot_v1",
                )
            except TypeError as exc:
                self.fail(f"capture identity is not parameterized: {exc}")

            self.assertEqual(exit_code, 0)
            self.assertEqual(receipt["scheduled_session_tag"], "midday")
            self.assertEqual(receipt["receipt_kind"], "schwab_chain_midday/v1")
            self.assertEqual(receipt["session_chain_convention"], "midday_snapshot_v1")
            self.assertFalse(Path("reports/2026-08-10/preclose.json").exists())
            receipt_path = Path("reports/2026-08-10/midday.json")
            self.assertTrue(receipt_path.is_file())
            stored_manifest = json.loads(Path("reports/2026-08-10/manifest.json").read_text())
            self.assertEqual(
                stored_manifest["session_chain_convention"],
                "midday_snapshot_v1",
            )
            _, fact = Path("ledger/facts.log").read_text().strip().split("\t", 1)
            self.assertTrue(fact.startswith("SCHWAB_CHAIN_MIDDAY session=2026-08-10 "))

    def test_preclose_declared_receipt_cannot_verify_as_midday(self):
        with self._isolated_capture():
            exit_code, _ = capture.capture(
                client=FakeClient(),
                now_ny=MIDDAY,
                universe=["AAA"],
                chain_dir=Path("chains"),
                reports_dir=Path("reports"),
                force=False,
                session_tag="midday",
                receipt_filename="midday.json",
                fact_prefix="SCHWAB_CHAIN_MIDDAY",
                receipt_kind="schwab_chain_midday/v1",
                convention="midday_snapshot_v1",
            )
            self.assertEqual(exit_code, 0)
            receipt_path = Path("reports/2026-08-10/midday.json")
            receipt = json.loads(receipt_path.read_text())
            receipt["scheduled_session_tag"] = "preclose"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

            with self.assertRaisesRegex(
                manifest.SchwabChainManifestError,
                "scheduled session tag does not match",
            ):
                manifest.verify_session(
                    "2026-08-10",
                    ["AAA"],
                    Path("chains"),
                    Path("reports/2026-08-10/manifest.json"),
                    receipt_path,
                    convention="midday_snapshot_v1",
                    receipt_filename="midday.json",
                    session_tag="midday",
                    receipt_kind="schwab_chain_midday/v1",
                )

    def test_midday_declared_receipt_cannot_verify_as_preclose(self):
        with self._isolated_capture():
            exit_code, _ = capture.capture(
                client=FakeClient(),
                now_ny=PRECLOSE,
                universe=["AAA"],
                chain_dir=Path("chains"),
                reports_dir=Path("reports"),
                force=False,
            )
            self.assertEqual(exit_code, 0)
            receipt_path = Path("reports/2026-08-10/preclose.json")
            receipt = json.loads(receipt_path.read_text())
            receipt["scheduled_session_tag"] = "midday"
            receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

            with self.assertRaisesRegex(
                manifest.SchwabChainManifestError,
                "scheduled session tag does not match",
            ):
                manifest.verify_session(
                    "2026-08-10",
                    ["AAA"],
                    Path("chains"),
                    Path("reports/2026-08-10/manifest.json"),
                    receipt_path,
                )

    def test_cli_with_no_identity_arguments_resolves_preclose_defaults(self):
        observed = {}
        signature = inspect.signature(capture.capture)

        def fake_capture(**kwargs):
            observed.update(kwargs)
            return 0, None

        with mock.patch.object(capture, "capture", side_effect=fake_capture):
            self.assertEqual(capture.main([]), 0)

        resolved = signature.bind_partial(**observed)
        resolved.apply_defaults()
        self.assertEqual(
            {
                name: resolved.arguments.get(name)
                for name in (
                    "session_tag",
                    "receipt_filename",
                    "fact_prefix",
                    "receipt_kind",
                    "convention",
                )
            },
            {
                "session_tag": "preclose",
                "receipt_filename": "preclose.json",
                "fact_prefix": "SCHWAB_CHAIN_CAPTURE",
                "receipt_kind": "schwab_chain_capture/v1",
                "convention": manifest.SESSION_CHAIN_CONVENTION,
            },
        )

    # --- brief 32: the quote-age sidecar is incapable of touching capture ---
    #
    # Within-run A/B rather than a stored pre-change artifact: the receipt
    # embeds the landing's own code_sha, so it can never match a pre-change
    # golden file. Lane A runs the real sidecar writer; lane B forces it to
    # raise. Everything the capture is responsible for must be identical.
    #
    # HARNESS DEPENDENCY (keep this in mind before touching _isolated_capture):
    # the working lane only produces a real sidecar because the harness's
    # `mock.patch.object(manifest.pd, "read_parquet", ...)` patches the GLOBAL
    # pandas, so the report module's own read returns the golden frame instead
    # of the `b"golden-chain\n"` placeholder the mocked writer puts on disk. If
    # that patch is ever narrowed to the manifest module alone, lane A silently
    # falls through to fail-soft for an unrelated reason and stops proving the
    # success path -- the assertion that lane A wrote a sidecar is what would
    # fail, so the breakage is loud rather than silent.

    def _run_capture_lane(
        self, *, break_report: bool, break_marker: bool = False
    ):
        stdout = io.StringIO()
        with self._isolated_capture(), contextlib.ExitStack() as stack:
            if break_report:
                stack.enter_context(
                    mock.patch.object(
                        capture,
                        "write_quote_age_report",
                        side_effect=RuntimeError(
                            "forced sidecar failure"
                        ),
                    )
                )
            if break_marker:
                stack.enter_context(
                    mock.patch.object(
                        capture,
                        "_write_quote_age_skip_marker",
                        side_effect=OSError("forced marker failure"),
                    )
                )
            with contextlib.redirect_stdout(stdout):
                exit_code, receipt = capture.capture(
                    client=FakeClient(),
                    now_ny=PRECLOSE,
                    universe=["AAA"],
                    chain_dir=Path("chains"),
                    reports_dir=Path("reports"),
                    force=False,
                )
            sidecar = Path("reports/2026-08-10/preclose.quote_age.json")
            marker = Path(
                "reports/2026-08-10/preclose.quote_age_skip.txt"
            )
            return {
                "exit_code": exit_code,
                "receipt": receipt,
                "manifest_bytes": Path("reports/2026-08-10/manifest.json").read_bytes(),
                "receipt_bytes": Path("reports/2026-08-10/preclose.json").read_bytes(),
                "verified": manifest.verify_session(
                    "2026-08-10",
                    ["AAA"],
                    Path("chains"),
                    Path("reports/2026-08-10/manifest.json"),
                    Path("reports/2026-08-10/preclose.json"),
                ),
                "sidecar_text": sidecar.read_text() if sidecar.is_file() else None,
                "marker_text": marker.read_text() if marker.is_file() else None,
                "stdout": stdout.getvalue(),
            }

    def test_quote_age_sidecar_failure_cannot_change_capture_bytes_or_exit_code(self):
        working = self._run_capture_lane(break_report=False)
        broken = self._run_capture_lane(break_report=True)

        self.assertEqual(working["exit_code"], 0)
        self.assertEqual(broken["exit_code"], working["exit_code"])
        self.assertEqual(broken["manifest_bytes"], working["manifest_bytes"])
        self.assertEqual(broken["receipt_bytes"], working["receipt_bytes"])
        self.assertEqual(broken["receipt"], working["receipt"])
        self.assertEqual(broken["verified"], working["verified"])

        # The working lane really did write a sidecar; the broken lane wrote
        # nothing and said so with the distinct, greppable prefix.
        self.assertIsNotNone(working["sidecar_text"])
        assert working["sidecar_text"] is not None
        written = json.loads(working["sidecar_text"])
        self.assertIs(written["display_only"], True)
        self.assertIs(written["verdict_eligible"], False)
        self.assertEqual(written["session"], "2026-08-10")
        self.assertIsNone(broken["sidecar_text"])
        self.assertIsNotNone(broken["marker_text"])
        self.assertIn("forced sidecar failure", broken["marker_text"])
        self.assertIn(quote_age.SKIP_NOTE_PREFIX, broken["stdout"])
        self.assertIn("forced sidecar failure", broken["stdout"])
        self.assertNotIn(quote_age.SKIP_NOTE_PREFIX, working["stdout"])

        # The fail-soft note must not be mistakable for one of the four
        # anchored capture classifications the ops wrapper greps for.
        for label in ("auth EXPIRED", "refused", "receipt CONFLICT", "failed"):
            self.assertNotIn(f"schwab_chain_capture {label}:", broken["stdout"])
        for lane in (working, broken):
            self.assertIn("schwab_chain_capture complete: 1/1", lane["stdout"])

    def test_quote_age_marker_failure_is_also_fail_soft(self):
        broken = self._run_capture_lane(
            break_report=True, break_marker=True
        )

        self.assertEqual(broken["exit_code"], 0)
        self.assertIsNone(broken["sidecar_text"])
        self.assertIsNone(broken["marker_text"])
        self.assertIn("forced sidecar failure", broken["stdout"])
        self.assertIn(
            "schwab_chain_capture complete: 1/1", broken["stdout"]
        )

    def test_verify_session_output_is_unchanged_by_the_sidecar(self):
        """No-coupling regression: verify_session's return is byte-identical
        to its pre-change value, with and without the sidecar present."""
        expected = {
            "provider": "schwab",
            "session": "2026-08-10",
            "session_chain_convention": "preclose_snapshot_v1",
            "manifest_hash": "a1667c3e89511d76882aa4afc2953ce48a47799ed334f1be38a438efd8e8a9f0",
            "manifest_path": "reports/2026-08-10/manifest.json",
            "receipt_path": "reports/2026-08-10/preclose.json",
        }
        expected_bytes = json.dumps(expected, indent=2, sort_keys=True).encode()

        def verified_bytes() -> bytes:
            return json.dumps(
                manifest.verify_session(
                    "2026-08-10",
                    ["AAA"],
                    Path("chains"),
                    Path("reports/2026-08-10/manifest.json"),
                    Path("reports/2026-08-10/preclose.json"),
                ),
                indent=2,
                sort_keys=True,
            ).encode()

        with self._isolated_capture():
            exit_code, _ = capture.capture(
                client=FakeClient(),
                now_ny=PRECLOSE,
                universe=["AAA"],
                chain_dir=Path("chains"),
                reports_dir=Path("reports"),
                force=False,
            )
            self.assertEqual(exit_code, 0)

            sidecar = Path("reports/2026-08-10/preclose.quote_age.json")
            self.assertTrue(sidecar.is_file())
            with_sidecar = verified_bytes()
            sidecar.unlink()
            without_sidecar = verified_bytes()

        self.assertEqual(with_sidecar, expected_bytes)
        self.assertEqual(without_sidecar, expected_bytes)


if __name__ == "__main__":
    unittest.main()

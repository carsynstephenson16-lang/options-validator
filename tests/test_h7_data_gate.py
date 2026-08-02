"""Stage 2 whole-universe daily data gate (BUILD-ONLY). The gate is
read-only w.r.t. every market-data store: it reads fixture parquet caches
and never fetches. GO requires all 14 names to have an adjusted close AND an
EOD chain for the EXACT evaluation session; anything else is a fail-closed
NO_GO. These tests inject tiny fixture caches via close_dir/chain_dir and
prove no fetch path is ever touched and no input byte changes."""

import hashlib
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pandas as pd

from data.cache_runner import trading_days
from data.cache_schema import validate_v2_synthetic_audit_receipt
from options_researcher import h7_data_gate as gate
from options_researcher.h7_scope import scope_identity, watch_universe
from options_researcher.h7_synthetic_proof import (
    _write_synthetic_full_audit_receipt,
)
from options_researcher.h7_watch import evaluation_session
from research.hashing import DIAGNOSTIC_SOURCE_HASH_VERSION
from research.receipts import load_receipt, make_receipt, write_immutable_receipt

REQ = date(2026, 7, 12)  # Sunday (today) -> evaluation session Fri 2026-07-10


def _good_chain() -> pd.DataFrame:
    """One clean, selectable, audit-PASS contract (OI>=100, tight spread,
    |delta| in the selectable band, valid iv/greeks, unique key)."""
    return pd.DataFrame(
        [
            {
                "expiration": "2026-08-21",
                "strike": 100.0,
                "right": "C",
                "bid": 5.0,
                "ask": 5.2,
                "open_interest": 500,
                "iv": 0.5,
                "delta": 0.55,
                "gamma": 0.02,
                "theta": -0.03,
                "vega": 0.10,
                "timestamp": pd.Timestamp("2026-07-10 17:15:00", tz="America/New_York"),
                "bid_size": 17,
                "bid_condition": 50,
                "ask_size": 23,
                "ask_condition": 50,
                "iv_error": 0.001,
                "underlying_timestamp": pd.Timestamp("2026-07-10 16:00:00", tz="America/New_York"),
                "underlying_price": 100.0,
                "thetadata_client_version": "1.0.9",
            }
        ]
    )


def _write_close(close_dir: Path, symbol: str, rows: list[tuple[str, float]]):
    pd.DataFrame(rows, columns=["date", "close"]).to_parquet(
        close_dir / f"{symbol}.parquet", index=False
    )


def _write_chain(chain_dir: Path, symbol: str, iso: str, df: pd.DataFrame):
    df.to_parquet(chain_dir / f"{symbol}_{iso}.parquet", index=False)


class GateBase(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.close_dir = Path(tmp.name) / "underlying"
        self.chain_dir = Path(tmp.name) / "chains"
        self.reports = Path(tmp.name) / "reports"
        self.close_dir.mkdir()
        self.chain_dir.mkdir()
        self.eval = evaluation_session(REQ)
        self.eval_iso = self.eval.isoformat()
        # a valid GO fixture for every one of the 14 names
        for sym in watch_universe():
            _write_close(
                self.close_dir,
                sym,
                [("2026-07-08", 90.0), ("2026-07-09", 95.0), (self.eval_iso, 100.0)],
            )
            _write_chain(self.chain_dir, sym, self.eval_iso, _good_chain())
        _write_synthetic_full_audit_receipt(self.chain_dir)
        validator_patch = mock.patch.object(
            gate,
            "validate_v2_audit_receipt",
            validate_v2_synthetic_audit_receipt,
        )
        validator_patch.start()
        self.addCleanup(validator_patch.stop)
        scope = scope_identity(watch_universe())
        self.eval_scope_id = scope["scope_id"]
        self.source_health = make_receipt(
            "source_health",
            {
                "evaluation_session": self.eval_iso,
                "scope": scope,
                "symbols": {sym: {"healthy": True, "gate": "CLEAR"} for sym in watch_universe()},
            },
        )
        self.source_health_path = Path(tmp.name) / "source_health.json"
        write_immutable_receipt(self.source_health, self.source_health_path)

    def _eval(self):
        _write_synthetic_full_audit_receipt(self.chain_dir)
        return gate.evaluate(REQ, close_dir=self.close_dir, chain_dir=self.chain_dir)

    def _run(self, argv_extra=()):
        _write_synthetic_full_audit_receipt(self.chain_dir)
        return gate.main(
            [
                "--as-of",
                REQ.isoformat(),
                "--close-dir",
                str(self.close_dir),
                "--chain-dir",
                str(self.chain_dir),
                "--reports-dir",
                str(self.reports),
                "--source-health-receipt",
                str(self.source_health_path),
                *argv_extra,
            ]
        )


class TestWholeUniverseGo(GateBase):
    def test_all_valid_is_go_exit_0(self):
        res = self._eval()
        self.assertEqual(res["evaluation_session"], self.eval_iso)
        self.assertEqual(res["whole_universe_verdict"], "GO")
        self.assertEqual(res["go_count"], 15)  # +ET (H7_AMENDMENT_V1_8)
        self.assertEqual(res["no_go_count"], 0)
        for sym in watch_universe():
            self.assertEqual(res["symbols"][sym]["verdict"], "GO")
            self.assertEqual(res["symbols"][sym]["reason_codes"], ["EXACT_SESSION_GO"])
        self.assertEqual(self._run(), 0)


class TestCloseFailures(GateBase):
    def test_missing_close_forces_universe_no_go(self):
        (self.close_dir / "NVDA.parquet").unlink()
        res = self._eval()
        self.assertEqual(res["symbols"]["NVDA"]["verdict"], "NO_GO")
        self.assertIn("CLOSE_FILE_MISSING", res["symbols"]["NVDA"]["reason_codes"])
        self.assertEqual(res["whole_universe_verdict"], "NO_GO")
        self.assertEqual(self._run(), 1)

    def test_stale_close_forces_no_go(self):
        _write_close(self.close_dir, "AMD", [("2026-07-08", 90.0), ("2026-07-09", 95.0)])
        res = self._eval()
        self.assertIn("CLOSE_STALE", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")
        self.assertEqual(self._run(), 1)

    def test_future_close_rows_excluded_during_replay(self):
        nxt = [d for d in trading_days(self.eval_iso, "2026-07-31") if d > self.eval_iso][0]
        _write_close(
            self.close_dir, "AMD", [("2026-07-09", 95.0), (self.eval_iso, 100.0), (nxt, 999.0)]
        )
        res = self._eval()
        c = res["symbols"]["AMD"]["close"]
        self.assertEqual(c["latest_date_at_or_before_session"], self.eval_iso)
        self.assertTrue(c["session_row_exists"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "GO")

    def test_eval_row_absent_but_later_rows_present_is_no_go_no_lookahead(self):
        nxt = [d for d in trading_days(self.eval_iso, "2026-07-31") if d > self.eval_iso][0]
        _write_close(self.close_dir, "AMD", [(nxt, 999.0)])
        res = self._eval()
        rc = res["symbols"]["AMD"]["reason_codes"]
        self.assertIn("CLOSE_SESSION_MISSING", rc)
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")
        self.assertIsNone(res["symbols"]["AMD"]["close"]["latest_date_at_or_before_session"])

    def test_nonfinite_close_is_no_go(self):
        _write_close(self.close_dir, "AMD", [("2026-07-09", 95.0), (self.eval_iso, float("nan"))])
        res = self._eval()
        self.assertIn("CLOSE_NONFINITE", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_duplicate_close_date_is_no_go(self):
        _write_close(self.close_dir, "AMD", [(self.eval_iso, 100.0), (self.eval_iso, 101.0)])
        res = self._eval()
        self.assertIn("CLOSE_DUPLICATE_DATE", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")


class TestChainFailures(GateBase):
    def test_missing_chain_forces_no_go(self):
        (self.chain_dir / f"NVDA_{self.eval_iso}.parquet").unlink()
        res = self._eval()
        self.assertIn("CHAIN_SESSION_MISSING", res["symbols"]["NVDA"]["reason_codes"])
        self.assertEqual(res["symbols"]["NVDA"]["verdict"], "NO_GO")
        self.assertEqual(self._run(), 1)

    def test_stale_chain_forces_no_go(self):
        (self.chain_dir / f"AMD_{self.eval_iso}.parquet").unlink()
        _write_chain(self.chain_dir, "AMD", "2026-07-08", _good_chain())
        res = self._eval()
        rc = res["symbols"]["AMD"]["reason_codes"]
        self.assertIn("CHAIN_SESSION_MISSING", rc)
        self.assertIn("CHAIN_STALE", rc)
        self.assertEqual(
            res["symbols"]["AMD"]["chain"]["newest_date_at_or_before_session"], "2026-07-08"
        )

    def test_later_chain_files_ignored_during_replay(self):
        nxt = [d for d in trading_days(self.eval_iso, "2026-07-31") if d > self.eval_iso][0]
        _write_chain(self.chain_dir, "AMD", nxt, _good_chain())
        res = self._eval()
        self.assertEqual(
            res["symbols"]["AMD"]["chain"]["newest_date_at_or_before_session"], self.eval_iso
        )
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "GO")

    def test_future_only_chain_is_not_substituted_beyond_edge(self):
        (self.chain_dir / f"AMD_{self.eval_iso}.parquet").unlink()
        nxt = [d for d in trading_days(self.eval_iso, "2026-07-31") if d > self.eval_iso][0]
        _write_chain(self.chain_dir, "AMD", nxt, _good_chain())
        res = self._eval()
        chain = res["symbols"]["AMD"]["chain"]
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")
        self.assertIn("CHAIN_SESSION_MISSING", res["symbols"]["AMD"]["reason_codes"])
        self.assertIsNone(chain["newest_date_at_or_before_session"])

    def test_missing_required_column_is_no_go(self):
        _write_chain(self.chain_dir, "AMD", self.eval_iso, _good_chain().drop(columns=["vega"]))
        res = self._eval()
        self.assertIn("CHAIN_SCHEMA_MISSING", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_nonfinite_numeric_field_is_no_go(self):
        df = _good_chain()
        df.loc[0, "delta"] = float("inf")
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        res = self._eval()
        self.assertIn("CHAIN_NONFINITE", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_duplicate_contract_is_no_go(self):
        df = pd.concat([_good_chain(), _good_chain()], ignore_index=True)
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        res = self._eval()
        self.assertIn("CHAIN_DUPLICATE_CONTRACT", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_negative_liquidity_field_is_no_go(self):
        df = _good_chain()
        df.loc[0, "open_interest"] = -1
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        res = self._eval()
        self.assertIn("CHAIN_NEGATIVE_LIQUIDITY_FIELD", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_crossed_market_is_no_go(self):
        df = _good_chain()
        df.loc[0, "bid"] = 9.0  # bid > ask
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        res = self._eval()
        self.assertIn("CHAIN_CROSSED_MARKET", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_audit_block_is_no_go(self):
        df = _good_chain()
        df.loc[0, "iv"] = 0.0  # iv<=0 on a SELECTABLE contract -> BLOCK
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        res = self._eval()
        self.assertIn("CHAIN_AUDIT_BLOCK", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["chain"]["audit"]["verdict"], "BLOCK")
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")

    def test_empty_chain_is_no_go(self):
        # a schema-correct but ZERO-ROW chain is not a chain -- it must not
        # audit-PASS into a spurious GO (fail-closed on an absent chain).
        _write_chain(self.chain_dir, "AMD", self.eval_iso, _good_chain().iloc[0:0])
        res = self._eval()
        self.assertIn("CHAIN_EMPTY", res["symbols"]["AMD"]["reason_codes"])
        self.assertEqual(res["symbols"]["AMD"]["chain"]["row_count"], 0)
        self.assertEqual(res["symbols"]["AMD"]["verdict"], "NO_GO")
        self.assertEqual(self._run(), 1)


class TestSourceHealthLinkRequired(GateBase):
    """An UNLINKED gate receipt is immutable and permanently revokes that
    session's real-entry authority (h7_session refuses a receipt chain with
    no source-health link). The gate must therefore refuse to write one at
    all rather than silently stamping nulls."""

    def test_omitted_source_health_receipt_is_exit_2_and_writes_nothing(self):
        rc = gate.main(
            [
                "--as-of",
                REQ.isoformat(),
                "--close-dir",
                str(self.close_dir),
                "--chain-dir",
                str(self.chain_dir),
                "--reports-dir",
                str(self.reports),
            ]
        )
        self.assertEqual(rc, 2)
        self.assertFalse(self.reports.exists() and any(self.reports.rglob("*.json")))

    def test_linked_receipt_records_the_source_health_path_and_hash(self):
        self.assertEqual(self._run(), 0)
        receipt = load_receipt(
            self.reports / self.eval_scope_id / "receipts" / f"{self.eval_iso}.json",
            expected_type="data_gate",
        )
        self.assertEqual(receipt["source_health_receipt_path"], str(self.source_health_path))
        self.assertEqual(receipt["source_health_receipt_hash"], self.source_health["receipt_hash"])
        self.assertEqual(
            receipt["source_hash_contract"],
            DIAGNOSTIC_SOURCE_HASH_VERSION,
        )


class TestCliContract(GateBase):
    def test_malformed_as_of_is_exit_2_no_traceback(self):
        rc = gate.main(
            [
                "--as-of",
                "not-a-date",
                "--close-dir",
                str(self.close_dir),
                "--chain-dir",
                str(self.chain_dir),
                "--reports-dir",
                str(self.reports),
            ]
        )
        self.assertEqual(rc, 2)

    def test_unreadable_store_is_exit_2_and_writes_no_artifact(self):
        def boom(path):
            raise OSError(f"corrupt parquet: {path}")

        with mock.patch.object(gate, "_read_parquet", side_effect=boom):
            rc = self._run()
        self.assertEqual(rc, 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_malformed_close_schema_is_exit_2_no_artifact(self):
        # a present, pandas-readable parquet with the WRONG shape (no
        # date/close) must fail the invocation (exit 2), not crash on column
        # access -- symmetric with the corrupt-parquet path.
        pd.DataFrame({"wrong": [1, 2]}).to_parquet(self.close_dir / "AMD.parquet", index=False)
        with self.assertRaises(gate.GateStoreError):
            self._eval()
        rc = self._run()
        self.assertEqual(rc, 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_malformed_chain_dtype_is_exit_2_no_artifact(self):
        # a readable chain whose numeric column is stored as object/string is
        # a store-integrity failure, not an honest data gap: exit 2 (symmetric
        # with the closes-schema guard), never a traceback + exit 1.
        df = _good_chain()
        df["bid"] = df["bid"].astype(str)  # numeric col with object dtype
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        with self.assertRaises(gate.GateStoreError):
            self._eval()
        rc = self._run()
        self.assertEqual(rc, 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_boolean_chain_dtype_is_exit_2_no_artifact(self):
        # pandas classifies bool as numeric, but True/False are not valid
        # market prices. The store boundary must reject them explicitly.
        df = _good_chain()
        df["bid"] = True
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        with self.assertRaises(gate.GateStoreError):
            self._eval()
        self.assertEqual(self._run(), 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_empty_chain_with_malformed_dtype_is_exit_2(self):
        # a ZERO-ROW store with a malformed stored dtype is a store-integrity
        # failure (exit 2), not a spurious CHAIN_EMPTY NO_GO: the dtype guard
        # runs BEFORE the empty short-circuit. (A valid empty store -- clean
        # dtypes -- still yields CHAIN_EMPTY; see test_empty_chain_is_no_go.)
        df = _good_chain().iloc[0:0].copy()
        df["bid"] = df["bid"].astype(bool)  # 0 rows, but bool is not a price
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        with self.assertRaises(gate.GateStoreError):
            self._eval()
        self.assertEqual(self._run(), 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_invalid_chain_domain_field_is_exit_2_no_artifact(self):
        for column, value in (("right", "X"), ("expiration", "not-a-date")):
            with self.subTest(column=column):
                df = _good_chain()
                df[column] = value
                _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
                with self.assertRaises(gate.GateStoreError):
                    self._eval()
                self.assertEqual(self._run(), 2)
                self.assertFalse(
                    self.reports.exists() and any(self.reports.iterdir())
                    if self.reports.exists()
                    else False
                )

    def test_unhashable_right_value_is_exit_2_no_artifact(self):
        df = _good_chain()
        df.at[0, "right"] = ["P"]
        _write_chain(self.chain_dir, "AMD", self.eval_iso, df)
        with self.assertRaises(gate.GateStoreError):
            self._eval()
        self.assertEqual(self._run(), 2)
        self.assertFalse(
            self.reports.exists() and any(self.reports.iterdir())
            if self.reports.exists()
            else False
        )

    def test_one_name_failure_forces_universe_no_go(self):
        (self.chain_dir / f"AMZN_{self.eval_iso}.parquet").unlink()
        res = self._eval()
        self.assertEqual(
            sum(1 for s in res["symbols"].values() if s["verdict"] == "GO"), 14
        )  # 15 - 1 (ET added)
        self.assertEqual(res["whole_universe_verdict"], "NO_GO")
        self.assertEqual(self._run(), 1)


class TestArtifactDeterminism(GateBase):
    def test_byte_identical_artifact_for_identical_inputs(self):
        res = self._eval()
        a = gate.to_artifact(res)
        b = gate.to_artifact(res)
        self.assertEqual(a, b)
        self.assertTrue(a.endswith("\n"))
        self.assertNotIn("generated_at", a)
        # round-trips and is sorted-deterministic
        again = gate.to_artifact(
            gate.evaluate(REQ, close_dir=self.close_dir, chain_dir=self.chain_dir)
        )
        self.assertEqual(a, again)

    def test_write_artifact_filename_is_evaluation_session(self):
        res = self._eval()
        path = gate.write_artifact(res, reports_dir=self.reports)
        self.assertEqual(path.name, f"{self.eval_iso}.json")
        self.assertEqual(path.read_text(), gate.to_artifact(res))


class TestFailClosedBoundary(GateBase):
    def test_no_fetch_path_is_called_and_inputs_unchanged(self):
        import data.recent_topup as rt
        import data.thetadata_adapter as ta
        import data.underlying_closes as uc

        def snapshot():
            out = {}
            for p in sorted([*self.close_dir.rglob("*"), *self.chain_dir.rglob("*")]):
                if not p.is_file():
                    continue
                st = p.stat()
                out[str(p.relative_to(p.parents[1]))] = (
                    st.st_size,
                    st.st_mtime,
                    hashlib.sha256(p.read_bytes()).hexdigest(),
                )
            return out

        before = snapshot()
        # Patch every FETCH/WRITE path the gate must never reach to raise.
        # (audit_chain is deliberately NOT patched -- the gate legitimately
        # calls it; audit_day IS a fetch-then-audit wrapper the gate must
        # not use.)
        with (
            mock.patch.object(
                ta, "get_eod_chain", side_effect=AssertionError("get_eod_chain called")
            ),
            mock.patch.object(
                ta, "blind_cache_chain", side_effect=AssertionError("blind_cache_chain called")
            ),
            mock.patch.object(
                uc, "fetch_underlying_eod_av", side_effect=AssertionError("fetch_av called")
            ),
            mock.patch.object(
                uc, "fetch_underlying_eod_yahoo", side_effect=AssertionError("fetch_yahoo called")
            ),
            mock.patch.object(
                uc, "store_closes", side_effect=AssertionError("store_closes called")
            ),
            mock.patch.object(
                rt, "audit_day", side_effect=AssertionError("recent_topup.audit_day called")
            ),
        ):
            res = self._eval()
        self.assertEqual(res["whole_universe_verdict"], "GO")
        self.assertEqual(snapshot(), before)  # bytes + mtimes unchanged


if __name__ == "__main__":
    unittest.main()

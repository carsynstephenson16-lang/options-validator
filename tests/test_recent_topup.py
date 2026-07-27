"""tests/test_recent_topup.py -- offline TDD coverage for data/recent_topup.py.

Pure functions only (no network): topup_days picks which recent trading days
to fetch, and freshness/repair tests use isolated cache and ledger directories
with provider calls forbidden.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data import recent_topup, thetadata_adapter
from research import facts


def _row(strike, right, bid, ask, oi, iv, delta, *, expiration="2026-08-21"):
    return {"expiration": expiration, "strike": strike, "right": right,
            "bid": bid, "ask": ask, "open_interest": oi, "iv": iv,
            "delta": delta, "gamma": 0.01, "theta": -0.05, "vega": 0.1}


class TopupDaysTests(unittest.TestCase):
    def _fake_cal(self, _start, _end):
        # A fixed window spanning the 2026 July 4th holiday; the function under
        # test must do the endpoint filtering itself.
        return ["2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-06"]

    def test_excludes_last_cached_boundary_and_today(self):
        days = recent_topup.topup_days(
            "2026-06-30", "2026-07-06", trading_days_fn=self._fake_cal)
        self.assertEqual(days, ["2026-07-01", "2026-07-02", "2026-07-03"])

    def test_empty_when_no_days_between(self):
        days = recent_topup.topup_days(
            "2026-07-03", "2026-07-06", trading_days_fn=self._fake_cal)
        self.assertEqual(days, [])

    def test_real_calendar_drops_holiday_and_today(self):
        # 2026-07-04 is Saturday -> observed Independence Day is Fri 2026-07-03,
        # market closed; today (2026-07-06) excluded because its EOD is not final.
        days = recent_topup.topup_days("2026-06-30", "2026-07-06")
        self.assertEqual(days, ["2026-07-01", "2026-07-02"])


class LatestCachedDateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _touch(self, symbol, date):
        (self.cache_dir / f"{symbol}_{date}.parquet").touch()

    def test_returns_min_of_per_symbol_max(self):
        # MSFT current to 07-02, AMZN lags at 07-01 -> cohort pulled from 07-01
        # so the lagging name is not left behind.
        self._touch("MSFT", "2026-06-30")
        self._touch("MSFT", "2026-07-02")
        self._touch("AMZN", "2026-07-01")
        got = recent_topup.latest_cached_date(
            ["MSFT", "AMZN"], cache_dir=self.cache_dir)
        self.assertEqual(got, "2026-07-01")

    def test_none_when_a_symbol_has_no_cache(self):
        self._touch("MSFT", "2026-07-02")
        got = recent_topup.latest_cached_date(
            ["MSFT", "AMZN"], cache_dir=self.cache_dir)
        self.assertIsNone(got)


class LatestCompleteSessionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.cache_dir = self.root / "chains"
        self.cache_dir.mkdir()
        self.facts_path = self.root / "ledger" / "facts.log"

    def tearDown(self):
        self._tmp.cleanup()

    def _file(self, symbol, session, payload=b"chain"):
        path = self.cache_dir / f"{symbol}_{session}.parquet"
        path.write_bytes(payload)
        return path

    def _fact(self, symbol, session, path):
        facts.append_fact(
            f"BLIND_CACHE symbol={symbol} date={session} rows=1 "
            f"sha256={hashlib.sha256(path.read_bytes()).hexdigest()} "
            f"already_cached=false path={path}",
            base_dir=self.facts_path.parent,
        )

    def test_latest_file_without_fact_is_not_current(self):
        older = self._file("NVDA", "2026-07-23", b"older")
        self._fact("NVDA", "2026-07-23", older)
        self._file("NVDA", "2026-07-24", b"orphan")

        self.assertEqual(
            recent_topup.latest_complete_session(
                ["NVDA"],
                cache_dir=self.cache_dir,
                facts_path=self.facts_path,
            ),
            "2026-07-23",
        )

    def test_one_hash_mismatch_prevents_complete_cohort(self):
        nvda = self._file("NVDA", "2026-07-24", b"nvda")
        pltr = self._file("PLTR", "2026-07-24", b"pltr")
        self._fact("NVDA", "2026-07-24", nvda)
        self._fact("PLTR", "2026-07-24", pltr)
        pltr.write_bytes(b"tampered")

        self.assertIsNone(
            recent_topup.latest_complete_session(
                ["NVDA", "PLTR"],
                cache_dir=self.cache_dir,
                facts_path=self.facts_path,
            )
        )

    def test_requires_an_exact_common_session_not_minimum_of_latest_dates(self):
        nvda_24 = self._file("NVDA", "2026-07-24", b"nvda-24")
        pltr_23 = self._file("PLTR", "2026-07-23", b"pltr-23")
        pltr_25 = self._file("PLTR", "2026-07-25", b"pltr-25")
        self._fact("NVDA", "2026-07-24", nvda_24)
        self._fact("PLTR", "2026-07-23", pltr_23)
        self._fact("PLTR", "2026-07-25", pltr_25)

        self.assertIsNone(
            recent_topup.latest_complete_session(
                ["NVDA", "PLTR"],
                cache_dir=self.cache_dir,
                facts_path=self.facts_path,
            )
        )

    def test_cohort_preflight_reports_exact_orphan(self):
        path = self._file("NVDA", "2026-07-24")
        with self.assertRaisesRegex(RuntimeError, "NVDA@2026-07-24"):
            recent_topup.verify_cohort_provenance(
                ["NVDA"],
                "2026-07-24",
                cache_dir=self.cache_dir,
                facts_path=self.facts_path,
            )
        self.assertTrue(path.exists())


class RepairManifestTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.cache_dir = self.root / "chains"
        self.ledger_dir = self.root / "ledger"
        self.cache_dir.mkdir()
        self._old_cache = thetadata_adapter.CACHE_DIR
        self._old_guard = thetadata_adapter._require_cache_publisher
        self._old_fetch = thetadata_adapter._fetch_merged_chain
        thetadata_adapter.CACHE_DIR = self.cache_dir
        thetadata_adapter._require_cache_publisher = lambda: None
        thetadata_adapter._fetch_merged_chain = (
            lambda *_: (_ for _ in ()).throw(
                AssertionError("repair must never call provider")
            )
        )

    def tearDown(self):
        thetadata_adapter.CACHE_DIR = self._old_cache
        thetadata_adapter._require_cache_publisher = self._old_guard
        thetadata_adapter._fetch_merged_chain = self._old_fetch
        self._tmp.cleanup()

    def _manifest(self, *, sha_override=None):
        session = "2026-07-24"
        symbol = "NVDA"
        frame = pd.DataFrame([_row(200, "C", 5.0, 5.2, 500, 0.3, 0.5)])
        path = thetadata_adapter._cache_path(symbol, session)
        frame.to_parquet(path, index=False)
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest = {
            "schema": "cache_recovery/v1",
            "incident_id": "test",
            "review": {"status": "approved_for_operational_recovery"},
            "session": session,
            "symbols": [symbol],
            "source_evidence": "fixture",
            "entries": [{
                "symbol": symbol,
                "path": str(path),
                "rows": 1,
                "columns": list(frame.columns),
                "sha256": sha_override or sha256,
            }],
        }
        manifest_path = self.root / "repair.json"
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path, path, sha256

    def test_accepts_the_reviewed_operational_incident_manifest_shape(self):
        manifest, cache_path, sha256 = self._manifest()
        payload = json.loads(manifest.read_text())
        payload["evaluation_session"] = payload.pop("session")
        payload["files"] = payload.pop("entries")
        payload.pop("symbols")
        payload["files"][0]["columns"] = len(payload["files"][0]["columns"])
        manifest.write_text(json.dumps(payload))

        result = recent_topup.repair_from_manifest(
            manifest,
            symbols=["NVDA"],
            as_of="2026-07-24",
            ledger_dir=str(self.ledger_dir),
        )

        self.assertEqual(
            result["results"][0]["attestation_status"],
            "REPAIRED_ATTESTATION",
        )
        self.assertEqual(result["results"][0]["sha256"], sha256)
        self.assertTrue(cache_path.exists())

    def test_unreviewed_manifest_is_refused_before_any_fact(self):
        manifest, _cache_path, _sha256 = self._manifest()
        payload = json.loads(manifest.read_text())
        payload.pop("review")
        manifest.write_text(json.dumps(payload))

        with self.assertRaisesRegex(ValueError, "reviewed and approved"):
            recent_topup.repair_from_manifest(
                manifest,
                symbols=["NVDA"],
                as_of="2026-07-24",
                ledger_dir=str(self.ledger_dir),
            )

        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_approved_orphan_repair_is_network_free_and_idempotent(self):
        manifest, cache_path, sha256 = self._manifest()
        before_mtime = cache_path.stat().st_mtime_ns

        first = recent_topup.repair_from_manifest(
            manifest,
            symbols=["NVDA"],
            as_of="2026-07-24",
            ledger_dir=str(self.ledger_dir),
        )
        second = recent_topup.repair_from_manifest(
            manifest,
            symbols=["NVDA"],
            as_of="2026-07-24",
            ledger_dir=str(self.ledger_dir),
        )

        self.assertEqual(
            first["results"][0]["attestation_status"],
            "REPAIRED_ATTESTATION",
        )
        self.assertEqual(
            second["results"][0]["attestation_status"], "VERIFIED_NOOP"
        )
        self.assertEqual(cache_path.stat().st_mtime_ns, before_mtime)
        self.assertEqual(first["results"][0]["sha256"], sha256)
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 1)

    def test_manifest_hash_mismatch_refuses_before_any_fact(self):
        manifest, cache_path, _sha256 = self._manifest(sha_override="0" * 64)
        before_mtime = cache_path.stat().st_mtime_ns

        with self.assertRaisesRegex(RuntimeError, "manifest sha256 mismatch"):
            recent_topup.repair_from_manifest(
                manifest,
                symbols=["NVDA"],
                as_of="2026-07-24",
                ledger_dir=str(self.ledger_dir),
            )

        self.assertEqual(cache_path.stat().st_mtime_ns, before_mtime)
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_normal_topup_refuses_unapproved_orphan_instead_of_skipping(self):
        _manifest, _orphan, _sha256 = self._manifest()
        frame = pd.DataFrame([_row(200, "C", 5.0, 5.2, 500, 0.3, 0.5)])
        older = thetadata_adapter._cache_path("NVDA", "2026-07-23")
        frame.to_parquet(older, index=False)
        facts.append_fact(
            "BLIND_CACHE symbol=NVDA date=2026-07-23 rows=1 "
            f"sha256={hashlib.sha256(older.read_bytes()).hexdigest()} "
            f"already_cached=false path={older}",
            base_dir=self.ledger_dir,
        )

        with self.assertRaisesRegex(
            thetadata_adapter.CacheProvenanceError, "orphaned cache file"
        ):
            recent_topup.run_topup(
                symbols=["NVDA"],
                today="2026-07-27",
                ledger_dir=str(self.ledger_dir),
                do_audit=False,
                trading_days_fn=lambda _start, _end: [
                    "2026-07-23", "2026-07-24", "2026-07-27"
                ],
            )


class ScopeTests(unittest.TestCase):
    def test_core_scope_preserves_existing_four_name_default(self):
        self.assertEqual(
            recent_topup.scope_symbols("core"),
            ["MSFT", "AMZN", "VST", "CEG"],
        )

    def test_h7_scope_is_the_exact_forward_watch_universe(self):
        # IREN ACTIVATED 2026-07-15, USAR ACTIVATED 2026-07-15 (base chain
        # caches built) -- both now in the active forward-watch scope. See
        # IREN_ACTIVATION + USAR_ACTIVATION in facts.log.
        self.assertEqual(
            recent_topup.scope_symbols("h7"),
            [
                "CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA",
                "AMD", "AVGO", "IREN", "USAR", "ET", "VST", "CEG", "MSFT", "AMZN",
            ],
        )

    def test_unknown_scope_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unknown top-up scope"):
            recent_topup.scope_symbols("everything")


class RefreshClosesTests(unittest.TestCase):
    def test_refreshes_every_selected_symbol_and_logs_scope(self):
        calls = []
        with tempfile.TemporaryDirectory() as ledger_dir:
            result = recent_topup.refresh_closes(
                ["MSFT", "AMZN"],
                today="2026-07-29",
                ledger_dir=ledger_dir,
                fetch_fn=lambda symbol: calls.append(symbol) or f"{symbol}.parquet",
            )
            fact = (Path(ledger_dir) / "facts.log").read_text()
        self.assertEqual(calls, ["MSFT", "AMZN"])
        self.assertEqual(result, {"MSFT": "MSFT.parquet", "AMZN": "AMZN.parquet"})
        self.assertIn("Yahoo closes refresh", fact)
        self.assertIn("MSFT/AMZN", fact)


class AuditChainTests(unittest.TestCase):
    def test_clean_selectable_chain_passes(self):
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.30, 0.50),
            _row(200, "P", 4.80, 5.00, 400, 0.31, -0.50),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "PASS")
        self.assertEqual(result["block"], [])
        self.assertEqual(result["warn"], [])

    def test_zero_iv_on_selectable_contract_blocks(self):
        # A near-ATM, liquid contract with IV=0 is a genuine defect (unlike the
        # benign deep-ITM case below) -> BLOCK.
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.00, 0.50),
            _row(200, "P", 4.80, 5.00, 400, 0.31, -0.50),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "BLOCK")
        self.assertTrue(any("iv" in r.lower() for r in result["block"]))

    def test_deep_itm_zero_iv_is_warning_not_block(self):
        # |delta|=1 deep-ITM contract with IV=0 is a solver artifact the
        # strategy never selects -> warning, never a block.
        df = pd.DataFrame([
            _row(200, "C", 5.00, 5.20, 500, 0.30, 0.50),
            _row(50, "C", 150.0, 150.4, 800, 0.00, 1.00),
        ])
        result = recent_topup.audit_chain(df)
        self.assertEqual(result["verdict"], "PASS WITH WARNINGS")
        self.assertEqual(result["block"], [])
        self.assertTrue(result["warn"])


if __name__ == "__main__":
    unittest.main()

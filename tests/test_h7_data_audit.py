"""7b-2 C2 / 7b-2R finding 3: the formal H7 data audit v2 -- one canonical
manifest, tiered provenance with NO mtime fallback, UNKNOWN-vs-DATA_GAP
earnings split, lane-aware puts, and a receipt that binds (and --verify
recomputes) EVERY verdict input."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

from data.audit_exceptions import excluded
from research.hashing import sha256_file
from tools import h7_data_audit as audit

SESSIONS = ["2022-06-01", "2022-06-02", "2022-06-03", "2022-06-06",
            "2022-06-07"]
NO_EXCLUSIONS: tuple = ()
TRACKED_CTX = {"commit": "deadbeef", "committed": "2026-07-10T09:12:06-04:00",
               "adapter_endpoint_ok": True}


def clear_assertions(sym="NVDA"):
    ts = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    return [{"symbol": sym, "event_id": f"{sym}-E1", "fiscal_period": "FYX",
             "expected_date": datetime(2022, 12, 15).date(),
             "session_timing": "amc", "status": "confirmed",
             "source_url": "https://example.test/ir",
             "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}]


def chain_frame(rows=None):
    base = rows or [
        ("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55),
        ("2022-07-15", 100.0, "P", 1.0, 1.1, 500, -0.30),
    ]
    return pd.DataFrame([
        {"expiration": e, "strike": float(k), "right": r, "bid": float(b),
         "ask": float(a), "open_interest": int(oi), "iv": 0.5,
         "delta": float(d), "gamma": 0.0, "theta": 0.0, "vega": 0.0}
        for (e, k, r, b, a, oi, d) in base
    ])


def build_cache(tmp, sym="NVDA", days=SESSIONS, frame=None):
    chain_dir = Path(tmp) / "chains"
    closes_dir = Path(tmp) / "underlying"
    chain_dir.mkdir(exist_ok=True)
    closes_dir.mkdir(exist_ok=True)
    for d in days:
        (frame if frame is not None else chain_frame()).to_parquet(
            chain_dir / f"{sym}_{d}.parquet")
    pd.DataFrame({"date": days, "close": [100.0] * len(days)}).to_parquet(
        closes_dir / f"{sym}.parquet")
    return chain_dir, closes_dir


def good_facts(chain_dir, sym="NVDA"):
    """Ledger-fact provenance for every file: post-close fetch + real sha."""
    facts = {}
    for p in Path(chain_dir).glob(f"{sym}_*.parquet"):
        day = p.name[len(sym) + 1:-8]
        facts[(sym, day)] = {
            "fetched": datetime.fromisoformat(f"{day}T23:00:00+00:00"),
            "sha256": sha256_file(p),
        }
    return facts


def run(tmp_dirs, sym="NVDA", assertions=None, fetch_facts=None,
        sessions=SESSIONS, registry=NO_EXCLUSIONS, coverage_decls=(),
        tracked_manifest=None, tracked_context=TRACKED_CTX):
    chain_dir, closes_dir = tmp_dirs
    with mock.patch.object(audit, "continuity_breaks", lambda s, d: []):
        return audit.run_audit(
            symbols=[sym], start=sessions[0], end=sessions[-1],
            chain_dir=chain_dir, closes_dir=closes_dir, sessions=sessions,
            assertions=(assertions if assertions is not None
                        else clear_assertions(sym)),
            fetch_facts=(good_facts(chain_dir, sym)
                         if fetch_facts is None else fetch_facts),
            registry=registry, coverage_decls=list(coverage_decls),
            tracked_manifest=tracked_manifest or {},
            tracked_context=tracked_context)


class TestManifestAndExceptions(unittest.TestCase):
    def test_registry_covers_the_smci_untradable_interval(self):
        self.assertIsNotNone(excluded("SMCI", "2019-06-03"))
        self.assertIsNone(excluded("SMCI", "2020-05-05"))
        self.assertIsNone(excluded("NVDA", "2019-06-03"))

    def test_registry_separates_listing_status_from_options_coverage(self):
        self.assertEqual(excluded("SMCI", "2018-08-23")["kind"],
                         "underlying_suspended")
        self.assertEqual(excluded("SMCI", "2019-06-03")["kind"], "delisted")
        self.assertEqual(excluded("SMCI", "2020-03-02")["kind"],
                         "options_coverage_gap")
        self.assertEqual(excluded("SMCI", "2020-03-02")["basis"],
                         "data_coverage")
        for e in (excluded("SMCI", "2018-08-23"),
                  excluded("PLTR", "2019-06-03"),
                  excluded("CEG", "2021-06-03")):
            self.assertEqual(e["basis"], "official")
            self.assertTrue(e["source_urls"])   # cited, not asserted

    def test_unratified_coverage_entries_surface(self):
        from data.audit_exceptions import unratified_coverage_entries
        syms = sorted({e["symbol"] for e in unratified_coverage_entries()})
        self.assertEqual(syms, ["CEG", "PLTR", "SMCI"])

    def test_manifest_counts_expected_and_excluded(self):
        m = audit.expected_manifest(
            symbols=["SMCI"], start="2018-08-20", end="2018-08-27",
            sessions=["2018-08-20", "2018-08-21", "2018-08-22",
                      "2018-08-23", "2018-08-24", "2018-08-27"])
        self.assertEqual(len(m["SMCI"]["expected"]), 3)   # 20th..22nd
        self.assertEqual(len(m["SMCI"]["excluded"]), 3)   # 23rd onward
        self.assertEqual(m["SMCI"]["excluded"]["2018-08-23"],
                         "underlying_suspended")


class TestAuditVerdicts(unittest.TestCase):
    def test_clean_cache_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["counts"]["present"], 5)
        self.assertEqual(report["counts"]["missing"], 0)
        self.assertEqual(report["provenance_tiers"]["ledger_fact"], 5)

    def test_missing_session_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            (dirs[0] / "NVDA_2022-06-03.parquet").unlink()
            report = run(dirs)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["missing_sessions"], 1)
        self.assertEqual(report["missing_days"]["NVDA"], ["2022-06-03"])

    def test_duplicate_rows_block(self):
        frame = chain_frame([
            ("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55),
            ("2022-07-15", 100.0, "C", 2.0, 2.2, 500, 0.55),   # dup key
            ("2022-07-15", 100.0, "P", 1.0, 1.1, 500, -0.30),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["duplicate_rows"], 5)

    def test_missing_raw_close_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            pd.DataFrame({"date": SESSIONS[1:],
                          "close": [100.0] * 4}).to_parquet(
                dirs[1] / "NVDA.parquet")
            report = run(dirs)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["missing_raw_close"], 1)

    def test_crossed_and_one_sided_books_warn_not_block(self):
        frame = chain_frame([
            ("2022-07-15", 100.0, "C", 2.5, 2.1, 500, 0.55),   # crossed
            ("2022-07-15", 105.0, "C", 0.0, 2.1, 500, 0.40),   # one-sided
            ("2022-07-15", 100.0, "P", 1.0, 1.1, 500, -0.30),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["warn_findings"]["crossed_books"], 5)
        self.assertEqual(report["warn_findings"]["one_sided_books"], 5)


class TestProvenanceTiers(unittest.TestCase):
    """NO mtime fallback (7b-2R finding 3): a file is ledger_fact,
    legacy_manifest, or unproven -- and unproven BLOCKS."""

    def test_intraday_fetch_fact_contaminates(self):
        from zoneinfo import ZoneInfo
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            facts = good_facts(dirs[0])
            facts[("NVDA", "2022-06-02")] = {
                "fetched": datetime(2022, 6, 2, 14, 30,
                                    tzinfo=ZoneInfo("America/New_York")),
                "sha256": facts[("NVDA", "2022-06-02")]["sha256"],
            }
            report = run(dirs, fetch_facts=facts)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["intraday_fetch_contamination"], 1)
        self.assertEqual(report["contaminated_days"][0]["day"], "2022-06-02")

    def test_fact_sha_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            facts = good_facts(dirs[0])
            facts[("NVDA", "2022-06-02")]["sha256"] = "0" * 64
            report = run(dirs, fetch_facts=facts)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["provenance_sha_mismatch"], 1)
        self.assertEqual(report["provenance_sha_mismatch_files"],
                         ["NVDA_2022-06-02"])

    def test_no_fact_no_manifest_is_unproven_and_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp), fetch_facts={})
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["unproven_provenance"], 5)
        self.assertEqual(report["provenance_tiers"]["unproven"], 5)

    def test_legacy_manifest_tier_passes_with_all_three_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            tracked = {p.name: sha256_file(p)
                       for p in dirs[0].glob("*.parquet")}
            report = run(dirs, fetch_facts={}, tracked_manifest=tracked)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["provenance_tiers"]["legacy_manifest"], 5)
        self.assertIn("assumption", report["legacy_provenance_assumption"])

    def test_legacy_tier_refused_without_adapter_endpoint_proof(self):
        ctx = dict(TRACKED_CTX, adapter_endpoint_ok=False)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            tracked = {p.name: sha256_file(p)
                       for p in dirs[0].glob("*.parquet")}
            report = run(dirs, fetch_facts={}, tracked_manifest=tracked,
                         tracked_context=ctx)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["provenance_tiers"]["unproven"], 5)

    def test_legacy_tier_refused_when_session_postdates_manifest(self):
        ctx = dict(TRACKED_CTX, committed="2022-06-03T00:00:00+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            tracked = {p.name: sha256_file(p)
                       for p in dirs[0].glob("*.parquet")}
            report = run(dirs, fetch_facts={}, tracked_manifest=tracked,
                         tracked_context=ctx)
        self.assertEqual(report["verdict"], "BLOCK")
        # 06-01 and 06-02 predate the manifest; 06-03 onward cannot
        self.assertEqual(report["provenance_tiers"]["legacy_manifest"], 2)
        self.assertEqual(report["provenance_tiers"]["unproven"], 3)


class TestEarningsSplit(unittest.TestCase):
    """UNKNOWN-vs-DATA_GAP (owner decision H7_7B2R_DECISIONS): both keep
    the trading gate closed; only DATA_GAP blocks the audit."""

    def test_unknown_without_coverage_declaration_is_data_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp), assertions=[])
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["earnings_data_gap_sessions"], 5)
        self.assertEqual(report["earnings_data_gap_by_symbol"]["NVDA"], 5)
        self.assertEqual(len(report["earnings_data_gap_days"]["NVDA"]), 5)

    def test_unknown_inside_declared_coverage_is_proven_unknown(self):
        decls = [{"symbol": "NVDA", "start": "2022-01-01",
                  "end": "2022-12-31", "basis": "sec_full_text",
                  "source_urls": ["https://efts.sec.gov/"]}]
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp), assertions=[],
                         coverage_decls=decls)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(
            report["warn_findings"]["earnings_proven_unknown_sessions"], 5)
        self.assertEqual(
            report["earnings_proven_unknown_by_symbol"]["NVDA"], 5)


class TestLaneAwareAndRegistry(unittest.TestCase):
    def test_missing_puts_warn_for_put_lane_symbol(self):
        frame = chain_frame([("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55)])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["warn_findings"]["missing_puts"], 5)

    def test_missing_puts_inapplicable_for_core_long_only_symbol(self):
        # VST is H7c-ineligible: its diagnostic never trades puts, so the
        # 2018-04-23..26-style missing-put days are inapplicable identities
        frame = chain_frame([("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55)])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, sym="VST", frame=frame), sym="VST")
        self.assertEqual(report["verdict"], "PASS")
        self.assertNotIn("missing_puts", report["warn_findings"])
        self.assertEqual(report["warn_findings"]["missing_puts_inapplicable"], 5)
        self.assertEqual(len(report["missing_puts_inapplicable"]), 5)

    def test_unratified_data_coverage_exclusion_blocks(self):
        registry = ({"symbol": "NVDA", "start": "2022-06-02",
                     "end": "2022-06-03", "kind": "options_coverage_gap",
                     "basis": "data_coverage", "source_urls": ()},)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp, days=["2022-06-01", "2022-06-06",
                                          "2022-06-07"])
            report = run(dirs, registry=registry)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["unratified_coverage_exclusions"], 1)
        self.assertEqual(report["unratified_coverage_exclusions"][0]["symbol"],
                         "NVDA")

    def test_ratified_data_coverage_exclusion_does_not_block(self):
        registry = ({"symbol": "NVDA", "start": "2022-06-02",
                     "end": "2022-06-03", "kind": "options_coverage_gap",
                     "basis": "data_coverage", "source_urls": (),
                     "ratified_by": "H7_AMENDMENT_EXAMPLE"},)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp, days=["2022-06-01", "2022-06-06",
                                          "2022-06-07"])
            report = run(dirs, registry=registry)
        self.assertEqual(report["verdict"], "PASS")

    def test_present_but_excluded_and_unexpected_are_reported(self):
        registry = ({"symbol": "NVDA", "start": "2022-06-02",
                     "end": "2022-06-03", "kind": "x", "basis": "official",
                     "source_urls": ("https://x",)},)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)   # files exist for ALL 5 sessions
            chain_frame().to_parquet(dirs[0] / "NVDA_2022-05-31.parquet")
            report = run(dirs, registry=registry)
        self.assertEqual(report["counts"]["present_but_excluded"], 2)
        self.assertEqual(report["cache_classification"]["present_but_excluded"],
                         ["NVDA_2022-06-02", "NVDA_2022-06-03"])
        self.assertEqual(report["cache_classification"]["unexpected"],
                         ["NVDA_2022-05-31"])
        # quarantined files are sha-bound in the receipt inputs
        self.assertEqual(len(report["quarantined_file_hashes"]), 3)


class TestContinuity(unittest.TestCase):
    def test_split_sized_jump_in_adjusted_closes_blocks(self):
        from data import underlying_closes
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            closes = pd.DataFrame({
                "date": SESSIONS,
                "close": [100.0, 100.0, 10.0, 10.0, 10.0],   # unregistered 10:1
            })
            cdir = Path(tmp) / "adjcache"
            cdir.mkdir()
            closes.to_parquet(cdir / "NVDA.parquet")
            with mock.patch.object(underlying_closes, "CACHE_DIR", str(cdir)):
                report = audit.run_audit(
                    symbols=["NVDA"], start=SESSIONS[0], end=SESSIONS[-1],
                    chain_dir=dirs[0], closes_dir=dirs[1], sessions=SESSIONS,
                    assertions=clear_assertions(),
                    fetch_facts=good_facts(dirs[0]),
                    registry=NO_EXCLUSIONS, coverage_decls=[],
                    tracked_manifest={}, tracked_context=TRACKED_CTX)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["adjusted_continuity_breaks"], 1)


class TestReceiptV2(unittest.TestCase):
    """--verify recomputes every bound input class; one mutation test per
    class (7b-2R finding 3)."""

    def _receipt(self, tmp):
        dirs = build_cache(tmp)
        report = run(dirs)
        earnings = Path(tmp) / "assertions_v2.csv"
        earnings.write_text("synthetic-store\n")
        coverage = Path(tmp) / "coverage.json"
        coverage.write_text("[]\n")
        receipt_path = Path(tmp) / "receipt_v2.json"
        audit.write_receipt(report, path=receipt_path,
                            earnings_path=earnings, coverage_path=coverage)
        return dirs, earnings, coverage, receipt_path

    def _verify(self, dirs, earnings, coverage, receipt_path, registry=None):
        return audit.verify_receipt(
            receipt_path, chain_dir=dirs[0], closes_dir=dirs[1],
            earnings_path=earnings, coverage_path=coverage,
            registry=NO_EXCLUSIONS if registry is None else registry)

    def test_roundtrip_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            ok, failures = self._verify(*args)
        self.assertEqual(failures, [])
        self.assertTrue(ok)

    def test_chain_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            chain_frame([("2022-07-15", 100.0, "C", 9.9, 9.99, 500, 0.55)]
                        ).to_parquet(args[0][0] / "NVDA_2022-06-02.parquet")
            ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertTrue(any(f.startswith("chain:") for f in failures))

    def test_closes_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            pd.DataFrame({"date": SESSIONS, "close": [1.0] * 5}).to_parquet(
                args[0][1] / "NVDA.parquet")
            ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("closes:NVDA", failures)

    def test_earnings_store_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            args[1].write_text("tampered\n")
            ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("earnings_store_hash", failures)

    def test_coverage_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            args[2].write_text('[{"symbol": "NVDA"}]\n')
            ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("earnings_coverage_hash", failures)

    def test_exception_registry_change_invalidates(self):
        other = ({"symbol": "NVDA", "start": "2022-06-02",
                  "end": "2022-06-02", "kind": "x", "basis": "official",
                  "source_urls": ("https://x",)},)
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            ok, failures = self._verify(*args, registry=other)
        self.assertFalse(ok)
        self.assertIn("exception_registry_hash", failures)

    def test_config_change_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            with mock.patch.object(audit, "config_hash", lambda: "0" * 64):
                ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("config_hash", failures)

    def test_source_surface_change_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            with mock.patch.object(audit, "diagnostic_source_hash",
                                   lambda: "0" * 64):
                ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("diagnostic_source_hash", failures)

    def test_receipt_field_tamper_invalidates(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            args = self._receipt(tmp)
            receipt = json.loads(args[3].read_text())
            receipt["verdict"] = "PASS-TAMPERED"
            args[3].write_text(json.dumps(receipt))
            ok, failures = self._verify(*args)
        self.assertFalse(ok)
        self.assertIn("receipt_hash", failures)

    def test_quarantined_file_mutation_invalidates(self):
        registry = ({"symbol": "NVDA", "start": "2022-06-02",
                     "end": "2022-06-03", "kind": "x", "basis": "official",
                     "source_urls": ("https://x",)},)
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            report = run(dirs, registry=registry)
            earnings = Path(tmp) / "assertions_v2.csv"
            earnings.write_text("synthetic-store\n")
            coverage = Path(tmp) / "coverage.json"
            coverage.write_text("[]\n")
            receipt_path = Path(tmp) / "receipt_v2.json"
            audit.write_receipt(report, path=receipt_path,
                                earnings_path=earnings,
                                coverage_path=coverage)
            chain_frame([("2022-07-15", 1.0, "C", 1.0, 1.1, 5, 0.5)]
                        ).to_parquet(dirs[0] / "NVDA_2022-06-02.parquet")
            ok, failures = audit.verify_receipt(
                receipt_path, chain_dir=dirs[0], closes_dir=dirs[1],
                earnings_path=earnings, coverage_path=coverage,
                registry=registry)
        self.assertFalse(ok)
        self.assertTrue(any(f.startswith("quarantined:") for f in failures))

    def test_v1_receipt_is_never_the_verify_target(self):
        self.assertNotEqual(audit.RECEIPT_PATH, audit.V1_RECEIPT_PATH)
        self.assertTrue(str(audit.RECEIPT_PATH).endswith("receipt_v2.json"))

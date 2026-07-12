"""7b-2R.2: the formal H7 data audit v4 -- one canonical manifest, tiered
provenance with NO mtime fallback, the BLIND_CACHE evidence itself (sha +
fetch timestamp) bound per fact-tier file so a post-close -> post-close
timestamp mutation invalidates, NO coverage-declaration escape hatch
(every UNKNOWN earnings session is a blocking DATA_GAP with a reason
breakdown), exact-amendment mechanical ratification of data_coverage
exclusions (chain-verified ledger, exact payload in the exact record),
unreadable/warn findings with identities, and a receipt whose --verify
RECOMPUTES the whole audit instead of self-hashing stored maps."""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pandas as pd

import config
from data.audit_exceptions import excluded, unratified_coverage_entries
from research import ledger
from research.hashing import sha256_file
from tools import h7_data_audit as audit

SESSIONS = ["2022-06-01", "2022-06-02", "2022-06-03", "2022-06-06",
            "2022-06-07"]
NO_EXCLUSIONS: tuple = ()
TRACKED_CTX = {"commit": "deadbeef", "committed": "2026-07-10T09:12:06-04:00",
               "adapter_blob": None, "adapter_endpoint_ok": True}


def clear_assertions(sym="NVDA"):
    ts = datetime.fromisoformat("2020-01-01T00:00:00+00:00")
    return [{"symbol": sym, "event_id": f"{sym}-E1", "fiscal_period": "FYX",
             "event_class": "actual_quarterly_earnings",
             "expected_date": datetime(2022, 12, 15).date(),
             "session_timing": "amc", "status": "confirmed",
             "source_url": "https://example.test/ir",
             "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}]


def stale_occurred_assertions(sym="NVDA"):
    """One realized report far outside the post-report grace window: the
    gate is UNKNOWN with the grace_expired reason on every June session."""
    ts = datetime.fromisoformat("2022-01-06T00:00:00+00:00")
    return [{"symbol": sym, "event_id": f"{sym}-E0", "fiscal_period": "FY22Q4",
             "event_class": "actual_quarterly_earnings",
             "expected_date": datetime(2022, 1, 5).date(),
             "occurred_date": datetime(2022, 1, 5).date(),
             "session_timing": "amc", "status": "occurred",
             "source_url": "https://example.test/ir",
             "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}]


def conflicting_assertions(sym="NVDA"):
    """Two unresolved schedule assertions for one fiscal period."""
    ts = datetime.fromisoformat("2022-01-01T00:00:00+00:00")
    base = {"symbol": sym, "fiscal_period": "FY23Q1",
            "event_class": "actual_quarterly_earnings",
            "session_timing": "amc", "status": "confirmed",
            "source_url": "https://example.test/ir",
            "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}
    return [dict(base, event_id=f"{sym}-C1",
                 expected_date=datetime(2022, 7, 1).date()),
            dict(base, event_id=f"{sym}-C2",
                 expected_date=datetime(2022, 7, 15).date())]


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


# the exact ratified exclusion payload for coverage_entry() below
PAYLOAD = "NVDA 2022-06-02..2022-06-03"


def seed_h7_intent(base, reason=f"synthetic H7 amendment ratifying "
                                f"{PAYLOAD} as an archive gap") -> str:
    """A tmp ledger with one H7 trial_intent; returns its record_hash
    (mirrors tests/test_ledger_diagnostics.py's _seed_h7_registration).
    The default reason carries the exact exclusion payload the 7b-2R.2
    exact-amendment rule requires."""
    return ledger.append({
        "entry_type": "trial_intent",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis_id": "H7",
        "reason": reason,
    }, base_dir=base)


def coverage_entry(ratified_by=None) -> tuple:
    e = {"symbol": "NVDA", "start": "2022-06-02", "end": "2022-06-03",
         "kind": "options_coverage_gap", "basis": "data_coverage",
         "source_urls": ()}
    if ratified_by is not None:
        e["ratified_by"] = ratified_by
    return (e,)


def run(tmp_dirs, sym="NVDA", assertions=None, fetch_facts=None,
        sessions=SESSIONS, registry=NO_EXCLUSIONS, tracked_manifest=None,
        tracked_context=TRACKED_CTX, ledger_records=()):
    chain_dir, closes_dir = tmp_dirs
    with mock.patch.object(audit, "continuity_breaks", lambda s, d: []):
        return audit.run_audit(
            symbols=[sym], start=sessions[0], end=sessions[-1],
            chain_dir=chain_dir, closes_dir=closes_dir, sessions=sessions,
            assertions=(assertions if assertions is not None
                        else clear_assertions(sym)),
            fetch_facts=(good_facts(chain_dir, sym)
                         if fetch_facts is None else fetch_facts),
            registry=registry, tracked_manifest=tracked_manifest or {},
            tracked_context=tracked_context, ledger_records=ledger_records)


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

    def test_current_registry_coverage_entries_are_ratified_by_v1_3(self):
        # H7_AMENDMENT_V1_3 (2026-07-11): the three data_coverage entries
        # carry the amendment's real record_hash, its reason carries each
        # entry's EXACT exclusion payload (7b-2R.2 finding 8), and the
        # whole thing verifies against the REAL chain-verified ledger --
        # against any other ledger they must still block
        self.assertEqual(unratified_coverage_entries(), ())
        from data.audit_exceptions import H7_AUDIT_EXCEPTIONS
        coverage = [e for e in H7_AUDIT_EXCEPTIONS
                    if e["basis"] == "data_coverage"]
        self.assertEqual(len(coverage), 3)
        hashes = {e["ratified_by"] for e in coverage}
        self.assertEqual(len(hashes), 1)          # one amendment covers all
        (amendment_hash,) = hashes
        self.assertEqual(amendment_hash,
                         config.H7_HISTORICAL_WITHDRAWAL_HASH)
        amendment = next(r for r in ledger.read_all("ledger")
                         if r.get("record_hash") == amendment_hash)
        self.assertEqual(amendment["entry_type"], "trial_intent")
        self.assertEqual(amendment["hypothesis_id"], "H7")
        for e in coverage:
            self.assertIn(f"{e['symbol']} {e['start']}..{e['end']}",
                          amendment["reason"])
        blocked = unratified_coverage_entries(ledger_records=[])
        self.assertEqual(len(blocked), 3)         # foreign ledger: refused

    def test_manifest_counts_expected_and_excluded(self):
        m = audit.expected_manifest(
            symbols=["SMCI"], start="2018-08-20", end="2018-08-27",
            sessions=["2018-08-20", "2018-08-21", "2018-08-22",
                      "2018-08-23", "2018-08-24", "2018-08-27"])
        self.assertEqual(len(m["SMCI"]["expected"]), 3)   # 20th..22nd
        self.assertEqual(len(m["SMCI"]["excluded"]), 3)   # 23rd onward
        self.assertEqual(m["SMCI"]["excluded"]["2018-08-23"],
                         "underlying_suspended")


class TestMechanicalRatification(unittest.TestCase):
    """7b-2R.1 finding D, hardened 7b-2R.2 finding 8: ratified_by must be
    the record_hash of an H7 trial_intent whose reason carries the EXACT
    ratified exclusion payload -- a truthy label is NOT ratification, and
    neither is an arbitrary H7 trial record that merely hash-matches."""

    def test_h7_intent_with_exact_payload_ratifies(self):
        with tempfile.TemporaryDirectory() as base:
            rec_hash = seed_h7_intent(base)   # reason contains PAYLOAD
            records = ledger.read_all(base)
            with mock.patch.object(config, "H7_HISTORICAL_WITHDRAWAL_HASH",
                                   rec_hash):
                self.assertEqual(unratified_coverage_entries(
                    coverage_entry(rec_hash), ledger_records=records), ())

    def test_h7_intent_without_payload_does_not_ratify(self):
        # 7b-2R.2 finding 8: the hash matches a real H7 trial_intent, but
        # that record never ratified THIS exclusion -- rejected
        with tempfile.TemporaryDirectory() as base:
            rec_hash = seed_h7_intent(
                base, reason="an H7 trial_intent with no exclusion payload")
            records = ledger.read_all(base)
            with mock.patch.object(config, "H7_HISTORICAL_WITHDRAWAL_HASH",
                                   rec_hash):
                ents = unratified_coverage_entries(
                    coverage_entry(rec_hash), ledger_records=records)
            self.assertEqual(len(ents), 1)

    def test_later_h7_intent_repeating_payload_is_not_exact_amendment(self):
        with tempfile.TemporaryDirectory() as base:
            amendment_hash = seed_h7_intent(base)
            later_hash = ledger.append({
                "entry_type": "trial_intent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hypothesis_id": "H7",
                "reason": f"later unrelated intent repeating {PAYLOAD}",
            }, base_dir=base)
            records = ledger.read_all(base)
            with mock.patch.object(config, "H7_HISTORICAL_WITHDRAWAL_HASH",
                                   amendment_hash):
                entries = unratified_coverage_entries(
                    coverage_entry(later_hash), ledger_records=records)
            self.assertEqual(len(entries), 1)

    def test_chain_is_verified_before_real_ledger_is_trusted(self):
        # ledger_records=None must verify the chain FIRST; a tampered
        # chain propagates instead of being silently trusted
        with mock.patch.object(
                ledger, "verify",
                side_effect=ledger.LedgerError("prev_hash break at seq 3")):
            with self.assertRaises(ledger.LedgerError):
                unratified_coverage_entries(coverage_entry("f" * 64))

    def test_random_hex_and_labels_do_not_ratify(self):
        with tempfile.TemporaryDirectory() as base:
            seed_h7_intent(base)
            records = ledger.read_all(base)
            for bogus in ("f" * 64, "H7_AMENDMENT_EXAMPLE", "", None):
                ents = unratified_coverage_entries(
                    coverage_entry(bogus), ledger_records=records)
                self.assertEqual(len(ents), 1, bogus)

    def test_non_h7_intent_hash_does_not_ratify(self):
        with tempfile.TemporaryDirectory() as base:
            h6_hash = ledger.append({
                "entry_type": "trial_intent",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hypothesis_id": "H6",
                # carries the payload, but is NOT an H7 registration
                "reason": f"not an H7 registration, though it says {PAYLOAD}",
            }, base_dir=base)
            records = ledger.read_all(base)
            ents = unratified_coverage_entries(
                coverage_entry(h6_hash), ledger_records=records)
            self.assertEqual(len(ents), 1)

    def test_non_trial_intent_record_does_not_ratify(self):
        # right hypothesis, right payload, wrong entry_type -> rejected
        fake = [{"entry_type": "diagnostic_attempt", "hypothesis_id": "H7",
                 "reason": f"carries {PAYLOAD} but is not a trial_intent",
                 "record_hash": "a" * 64}]
        ents = unratified_coverage_entries(
            coverage_entry("a" * 64), ledger_records=fake)
        self.assertEqual(len(ents), 1)

    def test_unratified_data_coverage_exclusion_blocks_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp, days=["2022-06-01", "2022-06-06",
                                          "2022-06-07"])
            report = run(dirs, registry=coverage_entry("f" * 64))
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["unratified_coverage_exclusions"], 1)
        self.assertEqual(report["unratified_coverage_exclusions"][0]["symbol"],
                         "NVDA")

    def test_ledger_ratified_data_coverage_exclusion_does_not_block(self):
        with tempfile.TemporaryDirectory() as base:
            rec_hash = seed_h7_intent(base)
            records = ledger.read_all(base)
            with mock.patch.object(config, "H7_HISTORICAL_WITHDRAWAL_HASH",
                                   rec_hash), tempfile.TemporaryDirectory() as tmp:
                dirs = build_cache(tmp, days=["2022-06-01", "2022-06-06",
                                              "2022-06-07"])
                report = run(dirs, registry=coverage_entry(rec_hash),
                             ledger_records=records)
        self.assertEqual(report["verdict"], "PASS")


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

    def test_unreadable_file_blocks_with_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            (dirs[0] / "NVDA_2022-06-02.parquet").write_bytes(
                b"not a parquet file")
            report = run(dirs)
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(report["block_findings"]["unreadable_files"], 1)
        (identity,) = report["unreadable_file_identities"]
        self.assertEqual(identity["file"], "NVDA_2022-06-02")
        self.assertTrue(identity["error"])          # exception type name
        self.assertLessEqual(len(identity["message"]), 200)

    def test_warn_detail_carries_per_day_identities(self):
        frame = chain_frame([
            ("2022-07-15", 100.0, "C", 2.5, 2.1, 500, 0.55),   # crossed
            ("2022-07-15", 100.0, "P", 1.0, 1.1, 500, -0.30),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["warn_detail"]["crossed_books"],
                         {f"NVDA_{d}": 1 for d in SESSIONS})
        self.assertEqual(report["warn_detail"]["missing_calls"], {})
        self.assertEqual(len(report["warn_detail_hash"]), 64)


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

    def test_evidence_bound_exactly_for_the_fact_tier_files(self):
        # 7b-2R.2 finding 3: the report carries the fact's own sha AND
        # fetch timestamp per ledger_fact file -- and ONLY for those
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            facts = good_facts(dirs[0])
            for day in ("2022-06-06", "2022-06-07"):
                del facts[("NVDA", day)]        # legacy-manifest tier
            tracked = {p.name: sha256_file(p)
                       for p in dirs[0].glob("*.parquet")}
            report = run(dirs, fetch_facts=facts, tracked_manifest=tracked)
            self.assertEqual(report["verdict"], "PASS")
            self.assertEqual(report["provenance_tiers"],
                             {"ledger_fact": 3, "legacy_manifest": 2,
                              "unproven": 0})
            self.assertEqual(
                sorted(report["provenance_evidence"]),
                [f"NVDA_{d}" for d in SESSIONS[:3]])
            ev = report["provenance_evidence"]["NVDA_2022-06-02"]
            self.assertEqual(
                ev, {"sha256": facts[("NVDA", "2022-06-02")]["sha256"],
                     "fetched": facts[("NVDA", "2022-06-02")]
                     ["fetched"].isoformat()})
            self.assertEqual(len(report["provenance_evidence_hash"]), 64)


class TestEarningsDataGap(unittest.TestCase):
    """Coverage declarations are REJECTED (owner decision 2026-07-11):
    there is no proven_unknown tier. EVERY UNKNOWN-gate session is a
    blocking DATA_GAP, with per-symbol identities and a reason breakdown
    keyed to the exported gate-reason constants."""

    def test_empty_archive_blocks_with_no_assertions_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp), assertions=[])
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["earnings_data_gap_sessions"], 5)
        self.assertEqual(report["earnings_data_gap_by_symbol"]["NVDA"], 5)
        self.assertEqual(report["earnings_data_gap_days"]["NVDA"], SESSIONS)
        self.assertEqual(report["earnings_data_gap_reasons"]["NVDA"],
                         {"no_assertions": 5, "grace_expired": 0,
                          "conflict": 0, "other": 0})

    def test_grace_expired_unknown_is_still_a_blocking_data_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp),
                         assertions=stale_occurred_assertions())
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["earnings_data_gap_sessions"], 5)
        self.assertEqual(
            report["earnings_data_gap_reasons"]["NVDA"]["grace_expired"], 5)

    def test_conflicting_assertions_are_a_data_gap_with_conflict_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp),
                         assertions=conflicting_assertions())
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["earnings_data_gap_reasons"]["NVDA"]["conflict"], 5)

    def test_coverage_declaration_mechanism_is_gone(self):
        self.assertFalse(hasattr(audit, "load_coverage_declarations"))
        self.assertFalse(hasattr(audit, "COVERAGE_PATH"))
        self.assertFalse(hasattr(audit, "_covered"))


class TestLaneAwareAndClassification(unittest.TestCase):
    def test_missing_puts_warn_for_put_lane_symbol(self):
        frame = chain_frame([("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55)])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["warn_findings"]["missing_puts"], 5)
        self.assertEqual(len(report["warn_detail"]["missing_puts"]), 5)

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
                    registry=NO_EXCLUSIONS, tracked_manifest={},
                    tracked_context=TRACKED_CTX, ledger_records=())
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["adjusted_continuity_breaks"], 1)


class TestSessionCalendarIdentity(unittest.TestCase):
    def test_binds_actual_close_timestamps(self):
        ident = audit.session_calendar_identity(SESSIONS)
        self.assertEqual(len(ident["session_closes_hash"]), 64)
        # dropping a session changes the bound closes, not just the list
        other = audit.session_calendar_identity(SESSIONS[:-1])
        self.assertNotEqual(ident["session_closes_hash"],
                            other["session_closes_hash"])
        self.assertNotEqual(ident["sessions_hash"], other["sessions_hash"])


class TestReceiptV4(unittest.TestCase):
    """--verify RECOMPUTES the audit (7b-2R.1 finding B): one mutation test
    per input class, each failing by a named key. v4 additionally binds the
    BLIND_CACHE evidence itself (7b-2R.2 finding 3), so mutating a bound
    fact's sha OR fetch timestamp invalidates."""

    def _write(self, tmp, registry=NO_EXCLUSIONS):
        dirs = build_cache(tmp)
        facts = good_facts(dirs[0])
        report = run(dirs, fetch_facts=facts, registry=registry)
        gating = Path(tmp) / "gating_v3.csv"
        gating.write_text("synthetic-gating-store\n")
        raw = Path(tmp) / "assertions_v2.csv"
        raw.write_text("synthetic-raw-store\n")
        receipt_path = Path(tmp) / "receipt_v4.json"
        audit.write_receipt(report, path=receipt_path,
                            earnings_gating_path=gating,
                            earnings_raw_path=raw)
        return {"dirs": dirs, "facts": facts, "gating": gating, "raw": raw,
                "path": receipt_path, "registry": registry}

    def _verify(self, ctx, **over):
        kw = dict(chain_dir=ctx["dirs"][0], closes_dir=ctx["dirs"][1],
                  sessions=SESSIONS, assertions=clear_assertions(),
                  fetch_facts=ctx["facts"], registry=ctx["registry"],
                  tracked_manifest={}, tracked_context=TRACKED_CTX,
                  ledger_records=(), earnings_gating_path=ctx["gating"],
                  earnings_raw_path=ctx["raw"])
        kw.update(over)
        with mock.patch.object(audit, "continuity_breaks", lambda s, d: []):
            return audit.verify_receipt(ctx["path"], **kw)

    def test_roundtrip_with_identical_inputs_is_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            ok, failures = self._verify(ctx)
        self.assertEqual(failures, [])
        self.assertTrue(ok)

    def test_chain_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            chain_frame([("2022-07-15", 100.0, "C", 9.9, 9.99, 500, 0.55)]
                        ).to_parquet(ctx["dirs"][0] / "NVDA_2022-06-02.parquet")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("files_hash", failures)

    def test_new_unexpected_file_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            chain_frame().to_parquet(ctx["dirs"][0] /
                                     "NVDA_2022-05-31.parquet")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("cache_classification", failures)
        self.assertIn("counts", failures)

    def test_changed_fetch_fact_sha_invalidates(self):
        # the FILE is unchanged; only the fact's sha drifted -- caught both
        # by the recomputed provenance_sha_mismatch block finding and by
        # the bound evidence itself
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            facts = {k: dict(v) for k, v in ctx["facts"].items()}
            facts[("NVDA", "2022-06-02")]["sha256"] = "0" * 64
            ok, failures = self._verify(ctx, fetch_facts=facts)
        self.assertFalse(ok)
        self.assertIn("block_findings", failures)
        self.assertIn("verdict", failures)
        self.assertIn("provenance_evidence_hash", failures)

    def test_post_close_timestamp_mutation_invalidates(self):
        # 7b-2R.2 finding 3: 23:00 UTC -> 22:00 UTC same day is still
        # post-close, so the v3 tier binding recomputed IDENTICALLY (no
        # contamination, no sha mismatch, verdict unchanged); only the
        # bound evidence catches it
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            facts = {k: dict(v) for k, v in ctx["facts"].items()}
            facts[("NVDA", "2022-06-02")]["fetched"] = (
                datetime.fromisoformat("2022-06-02T22:00:00+00:00"))
            ok, failures = self._verify(ctx, fetch_facts=facts)
        self.assertFalse(ok)
        self.assertIn("provenance_evidence_hash", failures)
        self.assertNotIn("verdict", failures)         # v3 would stay VALID
        self.assertNotIn("block_findings", failures)
        self.assertNotIn("provenance_map_hash", failures)

    def test_irrelevant_extra_facts_never_invalidate(self):
        # unrelated facts.log lines -- a foreign symbol and an NVDA day
        # outside the manifest -- are NOT part of the canonical relevant
        # subset and leave the receipt VALID
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            facts = dict(ctx["facts"])
            facts[("ZZZZ", "2022-06-02")] = {
                "fetched": datetime.fromisoformat(
                    "2022-06-02T23:00:00+00:00"),
                "sha256": "b" * 64}
            facts[("NVDA", "2021-01-04")] = {
                "fetched": datetime.fromisoformat(
                    "2021-01-04T14:30:00+00:00"),   # even intraday: ignored
                "sha256": "c" * 64}
            ok, failures = self._verify(ctx, fetch_facts=facts)
        self.assertEqual(failures, [])
        self.assertTrue(ok)

    def test_receipt_carries_evidence_for_exactly_the_fact_tier_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            receipt = json.loads(ctx["path"].read_text())
        self.assertEqual(sorted(receipt["provenance_evidence"]),
                         [f"NVDA_{d}" for d in SESSIONS])
        for key, ev in receipt["provenance_evidence"].items():
            self.assertEqual(set(ev), {"sha256", "fetched"})
        self.assertEqual(len(receipt["provenance_evidence_hash"]), 64)

    def test_tracked_manifest_context_change_invalidates(self):
        drift = dict(TRACKED_CTX, adapter_blob="a" * 40,
                     adapter_endpoint_ok=False)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            ok, failures = self._verify(ctx, tracked_context=drift)
        self.assertFalse(ok)
        self.assertIn("tracked_manifest", failures)
        self.assertIn("tracked_manifest.adapter_blob", failures)
        self.assertIn("tracked_manifest.adapter_endpoint_ok", failures)

    def test_closes_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            pd.DataFrame({"date": SESSIONS, "close": [1.0] * 5}).to_parquet(
                ctx["dirs"][1] / "NVDA.parquet")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("closes_hashes", failures)

    def test_earnings_gating_store_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            ctx["gating"].write_text("tampered\n")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("earnings_gating_hash", failures)

    def test_earnings_raw_store_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            ctx["raw"].write_text("tampered\n")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("earnings_raw_hash", failures)

    def test_exception_registry_change_invalidates(self):
        other = ({"symbol": "NVDA", "start": "2022-06-02",
                  "end": "2022-06-02", "kind": "x", "basis": "official",
                  "source_urls": ("https://x",)},)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            ok, failures = self._verify(ctx, registry=other)
        self.assertFalse(ok)
        self.assertIn("exception_registry_hash", failures)

    def test_config_change_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            with mock.patch.object(audit, "config_hash", lambda: "0" * 64):
                ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("config_hash", failures)

    def test_source_surface_change_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            with mock.patch.object(audit, "diagnostic_source_hash",
                                   lambda: "0" * 64):
                ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("diagnostic_source_hash", failures)

    def test_receipt_field_tamper_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp)
            receipt = json.loads(ctx["path"].read_text())
            receipt["verdict"] = "PASS-TAMPERED"
            ctx["path"].write_text(json.dumps(receipt))
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("receipt_hash", failures)

    def test_quarantined_file_mutation_invalidates(self):
        registry = ({"symbol": "NVDA", "start": "2022-06-02",
                     "end": "2022-06-03", "kind": "x", "basis": "official",
                     "source_urls": ("https://x",)},)
        with tempfile.TemporaryDirectory() as tmp:
            ctx = self._write(tmp, registry=registry)
            chain_frame([("2022-07-15", 1.0, "C", 1.0, 1.1, 5, 0.5)]
                        ).to_parquet(ctx["dirs"][0] / "NVDA_2022-06-02.parquet")
            ok, failures = self._verify(ctx)
        self.assertFalse(ok)
        self.assertIn("quarantined_files_hash", failures)

    def test_v4_is_the_verify_target_and_v1_v2_v3_are_blocked(self):
        self.assertTrue(str(audit.RECEIPT_PATH).endswith("receipt_v4.json"))
        historical = {audit.V1_RECEIPT_PATH, audit.V2_RECEIPT_PATH,
                      audit.V3_RECEIPT_PATH}
        self.assertEqual(len(historical), 3)      # all distinct
        self.assertNotIn(audit.RECEIPT_PATH, historical)
        self.assertEqual(audit.AUDIT_VERSION, "h7-data-audit/4")

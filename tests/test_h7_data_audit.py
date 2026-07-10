"""7b-2 C2: the formal H7 data audit -- independent manifest, reviewed
exceptions, fail-closed findings, content-addressed receipt."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import pandas as pd

from data.audit_exceptions import excluded
from tools import h7_data_audit as audit

SESSIONS = ["2022-06-01", "2022-06-02", "2022-06-03", "2022-06-06",
            "2022-06-07"]


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
    chain_dir.mkdir()
    closes_dir.mkdir()
    for d in days:
        (frame if frame is not None else chain_frame()).to_parquet(
            chain_dir / f"{sym}_{d}.parquet")
    pd.DataFrame({"date": days, "close": [100.0] * len(days)}).to_parquet(
        closes_dir / f"{sym}.parquet")
    return chain_dir, closes_dir


def run(tmp_dirs, sym="NVDA", assertions=None, fetch_times=None,
        sessions=SESSIONS):
    chain_dir, closes_dir = tmp_dirs
    with mock.patch.object(audit, "continuity_breaks", lambda s, d: []):
        return audit.run_audit(
            symbols=[sym], start=sessions[0], end=sessions[-1],
            chain_dir=chain_dir, closes_dir=closes_dir, sessions=sessions,
            assertions=(assertions if assertions is not None
                        else clear_assertions(sym)),
            fetch_times=fetch_times or {})


class TestManifestAndExceptions(unittest.TestCase):
    def test_registry_covers_the_smci_suspension(self):
        self.assertIsNotNone(excluded("SMCI", "2019-06-03"))
        self.assertIsNone(excluded("SMCI", "2020-05-05"))
        self.assertIsNone(excluded("NVDA", "2019-06-03"))

    def test_manifest_counts_expected_and_excluded(self):
        m = audit.expected_manifest(
            symbols=["SMCI"], start="2018-08-20", end="2018-08-27",
            sessions=["2018-08-20", "2018-08-21", "2018-08-22",
                      "2018-08-23", "2018-08-24", "2018-08-27"])
        self.assertEqual(len(m["SMCI"]["expected"]), 3)   # 20th..22nd
        self.assertEqual(len(m["SMCI"]["excluded"]), 3)   # 23rd onward
        self.assertEqual(m["SMCI"]["excluded"]["2018-08-23"], "suspension")


class TestAuditVerdicts(unittest.TestCase):
    def test_clean_cache_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp))
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["counts"]["present"], 5)
        self.assertEqual(report["counts"]["missing"], 0)

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

    def test_intraday_fetch_contaminates(self):
        with tempfile.TemporaryDirectory() as tmp:
            fetched = datetime(2022, 6, 2, 14, 30,
                               tzinfo=ZoneInfo("America/New_York"))
            report = run(build_cache(tmp),
                         fetch_times={("NVDA", "2022-06-02"): fetched})
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["intraday_fetch_contamination"], 1)
        self.assertEqual(report["contaminated_days"][0]["day"], "2022-06-02")

    def test_unknown_earnings_gate_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp), assertions=[])
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["earnings_gate_unknown_sessions"], 5)
        self.assertEqual(report["earnings_unknown_by_symbol"]["NVDA"], 5)

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

    def test_missing_rights_warn(self):
        frame = chain_frame([
            ("2022-07-15", 100.0, "C", 2.0, 2.1, 500, 0.55),
        ])
        with tempfile.TemporaryDirectory() as tmp:
            report = run(build_cache(tmp, frame=frame))
        self.assertEqual(report["warn_findings"]["missing_puts"], 5)


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
                    assertions=clear_assertions(), fetch_times={})
        self.assertEqual(report["verdict"], "BLOCK")
        self.assertEqual(
            report["block_findings"]["adjusted_continuity_breaks"], 1)


class TestReceipt(unittest.TestCase):
    def test_receipt_roundtrip_and_mutation_invalidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = build_cache(tmp)
            report = run(dirs)
            receipt_path = Path(tmp) / "receipt.json"
            audit.write_receipt(report, path=receipt_path)
            self.assertTrue(audit.verify_receipt(receipt_path,
                                                 chain_dir=dirs[0]))
            # mutate one audited input -> receipt invalid
            chain_frame([
                ("2022-07-15", 100.0, "C", 9.9, 9.99, 500, 0.55),
            ]).to_parquet(dirs[0] / "NVDA_2022-06-02.parquet")
            self.assertFalse(audit.verify_receipt(receipt_path,
                                                  chain_dir=dirs[0]))

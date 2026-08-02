"""Blind-cache mode (pre-registration decision doc, section 4): post-
IN_SAMPLE_END chains may be fetched and written to parquet during the paid
month, but their VALUES must never surface before the OOS reveal. Only safe
metadata escapes (symbol, date, row count, schema names, file hash and
attestation state), writes are single-publisher/idempotent, and reading the
cached values stays gated by the existing OOS reveal path."""
import hashlib
import multiprocessing
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from data import provider_policy, thetadata_adapter
from data.atomic_io import stage_parquet_write
from data.cache_provenance import load_blind_cache_facts
from research import facts

OOS_DATE = "2023-06-01"       # inside the extended OOS window
IN_SAMPLE_DATE = "2022-06-01"


def _frames(n=3):
    base = {
        "expiration": ["2023-07-21"] * n,
        "strike": [380.0 + 5 * i for i in range(n)],
        "right": ["PUT"] * n,
    }
    greeks = pd.DataFrame({**base,
                           "bid": [1.00 + i for i in range(n)],
                           "ask": [1.10 + i for i in range(n)],
                           "delta": [-0.30] * n, "gamma": [0.02] * n,
                           "theta": [-0.04] * n, "vega": [0.12] * n,
                           "implied_vol": [0.25] * n})
    oi = pd.DataFrame({**base, "open_interest": [500] * n})
    return greeks, oi


def _concurrent_publisher(
    cache_dir: str,
    ledger_dir: str,
    label: str,
    start,
    results,
) -> None:
    """Process target for the real cross-process publisher-lock regression."""
    policy_patch = mock.patch.object(
        provider_policy, "require_thetadata_acquisition", return_value=None
    )
    policy_patch.start()
    thetadata_adapter.CACHE_DIR = Path(cache_dir)
    thetadata_adapter._require_cache_publisher = lambda: None
    greeks, oi = _frames()
    if label == "B":
        greeks = greeks.copy()
        oi = oi.copy()
        greeks["strike"] = greeks["strike"] + 100
        oi["strike"] = oi["strike"] + 100
    thetadata_adapter._fetch_raw = lambda _symbol, _date: (greeks, oi)
    start.wait(10)
    try:
        result = thetadata_adapter.blind_cache_chain(
            "SPY",
            OOS_DATE,
            ledger_dir=ledger_dir,
        )
    except BaseException as exc:
        results.put(("ERROR", f"{type(exc).__name__}: {exc}"))
        return
    results.put((result["attestation_status"], result["sha256"]))


class BlindCacheTests(unittest.TestCase):
    def setUp(self):
        self._policy_patch = mock.patch.object(
            provider_policy, "require_thetadata_acquisition", return_value=None
        )
        self._policy_patch.start()
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        self._old_cache = thetadata_adapter.CACHE_DIR
        thetadata_adapter.CACHE_DIR = tmp / "chains"
        thetadata_adapter.CACHE_DIR.mkdir(parents=True)
        self.ledger_dir = str(tmp / "ledger")

        self._old_fetch_raw = thetadata_adapter._fetch_raw
        self._old_client = thetadata_adapter._client
        self._old_publisher_guard = thetadata_adapter._require_cache_publisher
        self.fetch_calls = []
        thetadata_adapter._require_cache_publisher = lambda: None

        def fake_fetch_raw(symbol, date):
            self.fetch_calls.append((symbol, date))
            return _frames()

        thetadata_adapter._fetch_raw = fake_fetch_raw

        def _client_forbidden():
            raise AssertionError("no test should construct a real ThetaClient")

        thetadata_adapter._client = _client_forbidden

    def tearDown(self):
        thetadata_adapter._fetch_raw = self._old_fetch_raw
        thetadata_adapter._client = self._old_client
        thetadata_adapter._require_cache_publisher = self._old_publisher_guard
        thetadata_adapter.CACHE_DIR = self._old_cache
        self._tmp.cleanup()
        self._policy_patch.stop()

    def _forbid_network(self):
        def raiser(*args, **kwargs):
            raise AssertionError("network fetch must not happen here")
        thetadata_adapter._fetch_raw = raiser
        thetadata_adapter._client = raiser

    def test_refuses_in_sample_dates(self):
        with self.assertRaises(ValueError):
            thetadata_adapter.blind_cache_chain(
                "SPY", IN_SAMPLE_DATE, ledger_dir=self.ledger_dir)
        self.assertFalse(
            thetadata_adapter._cache_path("SPY", IN_SAMPLE_DATE).exists())
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_writes_parquet_and_returns_only_safe_metadata(self):
        meta = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        self.assertEqual(set(meta), set(thetadata_adapter.BLIND_CACHE_METADATA_KEYS))
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        self.assertTrue(path.exists())
        self.assertEqual(meta["symbol"], "SPY")
        self.assertEqual(meta["date"], OOS_DATE)
        self.assertEqual(meta["rows"], 3)
        self.assertEqual(meta["columns"], thetadata_adapter.CHAIN_COLUMNS)
        self.assertEqual(meta["sha256"],
                         hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertFalse(meta["already_cached"])
        # nothing frame-like or price-like may escape: scalar/list types only
        for value in meta.values():
            self.assertNotIsInstance(value, (pd.DataFrame, pd.Series))

    def test_first_invocation_appends_an_auditable_fact(self):
        meta = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        lines = facts.read_facts(self.ledger_dir)
        self.assertEqual(len(lines), 1)
        for token in ("BLIND_CACHE", "symbol=SPY", f"date={OOS_DATE}",
                      "rows=3", f"sha256={meta['sha256']}"):
            self.assertIn(token, lines[0])

    def test_blind_cached_values_stay_gated_by_the_reveal_path(self):
        thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)
        self._forbid_network()

        # the cached file exists, but the gate must still refuse a plain read
        with self.assertRaises(thetadata_adapter.OOSDataTouchError):
            thetadata_adapter.get_eod_chain("SPY", OOS_DATE)

        # the reveal seam reads the blind cache without touching the network
        chain = thetadata_adapter.get_eod_chain("SPY", OOS_DATE, allow_oos=True)
        self.assertEqual(len(chain), 3)
        self.assertEqual(list(chain.columns), thetadata_adapter.CHAIN_COLUMNS)

    def test_empty_merge_is_a_gap_not_an_empty_cache_file(self):
        # Observed live (QQQ 2023-12-27): greeks and OI reports both populated
        # but sharing ZERO contract keys (strike-adjustment mismatch) -> the
        # inner join is empty. That must surface as the gap RuntimeError
        # ("returned no rows" token), never be written as a zero-row parquet.
        def disjoint_fetch_raw(symbol, date):
            greeks, oi = _frames()
            oi = oi.copy()
            oi["strike"] = oi["strike"] + 0.22  # no key overlap
            return greeks, oi

        thetadata_adapter._fetch_raw = disjoint_fetch_raw

        with self.assertRaisesRegex(RuntimeError, "returned no rows"):
            thetadata_adapter.blind_cache_chain(
                "QQQ", OOS_DATE, ledger_dir=self.ledger_dir)
        self.assertFalse(thetadata_adapter._cache_path("QQQ", OOS_DATE).exists())

    def test_already_cached_file_is_not_refetched_and_still_audited(self):
        first = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)
        self._forbid_network()

        second = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir)

        self.assertTrue(second["already_cached"])
        self.assertEqual(second["rows"], first["rows"])
        self.assertEqual(second["sha256"], first["sha256"])
        self.assertEqual(second["columns"], first["columns"])
        self.assertEqual(second["attestation_status"], "VERIFIED_NOOP")
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 1)

    def test_two_process_publishers_leave_one_canonical_fact_and_hash(self):
        context = multiprocessing.get_context("fork")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_concurrent_publisher,
                args=(
                    str(thetadata_adapter.CACHE_DIR),
                    self.ledger_dir,
                    label,
                    start,
                    results,
                ),
            )
            for label in ("A", "B")
        ]
        for process in processes:
            process.start()
        start.set()
        for process in processes:
            process.join(15)
            if process.is_alive():
                process.terminate()
                process.join()
        self.assertEqual([process.exitcode for process in processes], [0, 0])

        outcomes = [results.get(timeout=2), results.get(timeout=2)]
        self.assertEqual(
            sorted(status for status, _sha256 in outcomes),
            ["FETCHED_ATTESTED", "VERIFIED_NOOP"],
        )
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        file_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        canonical = load_blind_cache_facts(
            Path(self.ledger_dir) / "facts.log"
        )[("SPY", OOS_DATE)]
        self.assertEqual(canonical["sha256"], file_sha256)
        self.assertEqual(
            sum(
                "BLIND_CACHE symbol=SPY date=2023-06-01" in line
                for line in facts.read_facts(self.ledger_dir)
            ),
            1,
        )

    def test_consumer_cannot_fetch_or_append(self):
        thetadata_adapter._require_cache_publisher = self._old_publisher_guard
        old_role = os.environ.pop("OPTIONS_VALIDATOR_CACHE_ROLE", None)
        try:
            with self.assertRaisesRegex(
                thetadata_adapter.CacheWriteRefused, "cache mutation refused"
            ):
                thetadata_adapter.blind_cache_chain(
                    "SPY", OOS_DATE, ledger_dir=self.ledger_dir
                )
        finally:
            if old_role is not None:
                os.environ["OPTIONS_VALIDATOR_CACHE_ROLE"] = old_role
        self.assertFalse(thetadata_adapter._cache_path("SPY", OOS_DATE).exists())
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_arbitrary_orphan_refuses_without_network(self):
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        greeks, oi = _frames()
        chain = thetadata_adapter._merge_chain_frames(greeks, oi)
        chain.to_parquet(path, index=False)
        self._forbid_network()

        with self.assertRaisesRegex(
            thetadata_adapter.CacheProvenanceError, "orphaned cache file"
        ):
            thetadata_adapter.blind_cache_chain(
                "SPY", OOS_DATE, ledger_dir=self.ledger_dir
            )
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_approved_orphan_repairs_without_network_or_mtime_change(self):
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        greeks, oi = _frames()
        chain = thetadata_adapter._merge_chain_frames(greeks, oi)
        chain.to_parquet(path, index=False)
        approved = hashlib.sha256(path.read_bytes()).hexdigest()
        before_mtime = path.stat().st_mtime_ns
        self._forbid_network()

        result = thetadata_adapter.blind_cache_chain(
            "SPY",
            OOS_DATE,
            ledger_dir=self.ledger_dir,
            approved_sha256=approved,
        )

        self.assertEqual(result["attestation_status"], "REPAIRED_ATTESTATION")
        self.assertEqual(path.stat().st_mtime_ns, before_mtime)
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 1)

    def test_recorded_pending_attestation_recovers_after_interruption(self):
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        greeks, oi = _frames()
        chain = thetadata_adapter._merge_chain_frames(greeks, oi)
        chain.to_parquet(path, index=False)
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        meta = {
            "symbol": "SPY",
            "date": OOS_DATE,
            "rows": len(chain),
            "columns": list(chain.columns),
            "sha256": sha256,
            "path": str(path),
            "already_cached": True,
            "attestation_status": "",
            "identity": f"SPY:{OOS_DATE}:{sha256}",
        }
        thetadata_adapter._write_attestation(meta, status="PENDING_FACT")
        self._forbid_network()

        result = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir
        )

        self.assertEqual(result["attestation_status"], "REPAIRED_ATTESTATION")
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 1)

    def test_recorded_staged_file_recovers_without_provider_call(self):
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        greeks, oi = _frames()
        chain = thetadata_adapter._merge_chain_frames(greeks, oi)
        staged = stage_parquet_write(chain, path)
        sha256 = hashlib.sha256(staged.read_bytes()).hexdigest()
        meta = {
            "symbol": "SPY",
            "date": OOS_DATE,
            "rows": len(chain),
            "columns": list(chain.columns),
            "sha256": sha256,
            "path": str(path),
            "identity": f"SPY:{OOS_DATE}:{sha256}",
        }
        thetadata_adapter._write_attestation(
            meta,
            status="PENDING_FILE",
            staged_path=staged,
        )
        self._forbid_network()

        result = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir
        )

        self.assertTrue(path.is_file())
        self.assertFalse(staged.exists())
        self.assertEqual(result["attestation_status"], "REPAIRED_ATTESTATION")
        self.assertEqual(result["sha256"], sha256)
        self.assertEqual(len(facts.read_facts(self.ledger_dir)), 1)

    def test_missing_recorded_staged_bytes_refuse_without_network(self):
        path = thetadata_adapter._cache_path("SPY", OOS_DATE)
        staged = path.with_name(f".{path.name}.123.tmp")
        meta = {
            "symbol": "SPY",
            "date": OOS_DATE,
            "rows": 3,
            "columns": thetadata_adapter.CHAIN_COLUMNS,
            "sha256": "a" * 64,
            "path": str(path),
            "identity": f"SPY:{OOS_DATE}:{'a' * 64}",
        }
        thetadata_adapter._write_attestation(
            meta,
            status="PENDING_FILE",
            staged_path=staged,
        )
        self._forbid_network()

        with self.assertRaisesRegex(
            thetadata_adapter.CacheProvenanceError,
            "recorded staged cache bytes are missing",
        ):
            thetadata_adapter.blind_cache_chain(
                "SPY", OOS_DATE, ledger_dir=self.ledger_dir
            )

        self.assertFalse(path.exists())
        self.assertEqual(facts.read_facts(self.ledger_dir), [])

    def test_existing_fact_hash_mismatch_refuses(self):
        first = thetadata_adapter.blind_cache_chain(
            "SPY", OOS_DATE, ledger_dir=self.ledger_dir
        )
        facts.append_fact(
            "BLIND_CACHE symbol=SPY date=2023-06-01 rows=3 "
            f"sha256={'0' * 64} already_cached=true path=ignored",
            base_dir=self.ledger_dir,
        )
        self._forbid_network()

        with self.assertRaisesRegex(
            thetadata_adapter.CacheProvenanceError, "sha256 mismatch"
        ):
            thetadata_adapter.blind_cache_chain(
                "SPY",
                OOS_DATE,
                ledger_dir=self.ledger_dir,
                approved_sha256=first["sha256"],
            )

    def test_oos_consumer_never_fetches_on_cache_miss(self):
        self._forbid_network()
        with self.assertRaisesRegex(FileNotFoundError, "cache-only"):
            thetadata_adapter.get_eod_chain(
                "SPY", OOS_DATE, allow_oos=True
            )


if __name__ == "__main__":
    unittest.main()

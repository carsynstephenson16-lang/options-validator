"""7b-2R finding 2: one canonical eligible-session manifest for audit AND
runner; the runner refuses cache files the manifest does not name."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from data import h7_manifest, pandas_feed
from data import thetadata_adapter

SESSIONS = ["2022-06-01", "2022-06-02", "2022-06-03", "2022-06-06"]

REGISTRY = (
    {"symbol": "SMCI", "start": "2022-06-02", "end": "2022-06-03",
     "kind": "test_exclusion", "basis": "official", "source_urls": []},
)


def manifest(symbols=("SMCI", "NVDA")):
    return h7_manifest.eligible_manifest(
        symbols=list(symbols), start=SESSIONS[0], end=SESSIONS[-1],
        sessions=SESSIONS, registry=REGISTRY)


class TestEligibleManifest(unittest.TestCase):
    def test_eligible_and_excluded_split(self):
        m = manifest()
        self.assertEqual(m["SMCI"]["eligible"], ["2022-06-01", "2022-06-06"])
        self.assertEqual(m["SMCI"]["excluded"],
                         {"2022-06-02": "test_exclusion",
                          "2022-06-03": "test_exclusion"})
        self.assertEqual(m["NVDA"]["eligible"], SESSIONS)

    def test_enumeration_ignores_disk(self):
        # identical result whether or not any file exists
        with tempfile.TemporaryDirectory():
            self.assertEqual(manifest(), manifest())


class TestClassifyCache(unittest.TestCase):
    def test_every_file_class_is_reported_by_identity(self):
        m = manifest()
        names = [
            "SMCI_2022-06-01.parquet",     # eligible + present
            "SMCI_2022-06-02.parquet",     # PRESENT BUT EXCLUDED
            "SMCI_2022-05-31.parquet",     # outside window -> unexpected
            "NVDA_2022-06-01.parquet",
            "NVDA_2022-06-02.parquet",
            "NVDA_2022-06-03.parquet",
            "NVDA_2022-06-06.parquet",
            "SPY_2022-06-01.parquet",      # not a manifested symbol: ignored
            "not-a-chain.txt",
        ]
        c = h7_manifest.classify_cache(m, "unused", names=names)
        self.assertEqual(c["present"],
                         ["NVDA_2022-06-01", "NVDA_2022-06-02",
                          "NVDA_2022-06-03", "NVDA_2022-06-06",
                          "SMCI_2022-06-01"])
        self.assertEqual(c["missing"], ["SMCI_2022-06-06"])
        self.assertEqual(c["present_but_excluded"], ["SMCI_2022-06-02"])
        self.assertEqual(c["unexpected"], ["SMCI_2022-05-31"])
        self.assertEqual(c["duplicates"], [])

    def test_case_variant_files_collide_into_one_duplicate_identity(self):
        c = h7_manifest.classify_cache(
            manifest(), "unused",
            names=["NVDA_2022-06-01.parquet", "nvda_2022-06-01.parquet"])
        self.assertEqual(c["duplicates"], ["NVDA_2022-06-01"])

    def test_reads_directory_when_names_not_injected(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "NVDA_2022-06-01.parquet").touch()
            c = h7_manifest.classify_cache(manifest(), tmp)
        self.assertIn("NVDA_2022-06-01", c["present"])


class TestRunnerRefusesUnmanifestedFiles(unittest.TestCase):
    def test_loader_never_parses_a_file_outside_the_eligible_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            for day in SESSIONS:
                pd.DataFrame({"x": [1]}).to_parquet(
                    Path(tmp) / f"SMCI_{day}.parquet")
            orig = thetadata_adapter._cache_path
            calls: list[str] = []

            def spy_get(symbol, day, *, allow_oos=False):
                calls.append(day)
                return pd.DataFrame({"x": [1]})

            from unittest import mock
            with mock.patch.object(
                    thetadata_adapter, "_cache_path",
                    lambda sym, d: Path(tmp) / f"{sym}_{d}.parquet"), \
                 mock.patch.object(thetadata_adapter, "get_eod_chain",
                                   spy_get):
                refused: list[str] = []
                chains = pandas_feed.load_cached_chains(
                    "SMCI", SESSIONS[0], SESSIONS[-1],
                    eligible={"2022-06-01", "2022-06-06"}, refused=refused)
            self.assertEqual(orig.__name__, "_cache_path")  # sanity
        self.assertEqual(sorted(chains), ["2022-06-01", "2022-06-06"])
        self.assertEqual(sorted(calls), ["2022-06-01", "2022-06-06"])
        self.assertEqual(refused, ["2022-06-02", "2022-06-03"])

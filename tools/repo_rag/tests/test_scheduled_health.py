from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from repo_rag.chunking import ChunkSettings
from repo_rag.config import CorpusPolicy
from repo_rag.indexing import build_index
from repo_rag.scheduled_health import (
    SearchFilters,
    evaluate,
    load_golden_set,
    run_health,
    search,
)
from repo_rag.writer import WriteRefusedError, Writer


class ScheduledHealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.app = self.root / "tools" / "repo_rag"
        self.index = self.app / ".index"
        self.golden = self.app / "eval" / "golden.jsonl"
        (self.root / "docs").mkdir()
        self.app.mkdir(parents=True)
        (self.root / "docs" / "h7_hypothesis.md").write_text(
            "H7 ledger hash chain verification uses append-only records.\n", encoding="utf-8"
        )
        (self.root / "docs" / "fills.md").write_text(
            "Conservative fills use quote mid or worse with slippage.\n", encoding="utf-8"
        )
        self.policy = CorpusPolicy(
            application="test-rag",
            repository="test-repo",
            read_only=True,
            tracked_files_only=True,
            corpus_roots=("docs",),
            denied_segments=(),
            supported_suffixes=(".md",),
            source_classes={"canonical": ("docs/",)},
            bounded_writes=True,
        )
        build_index(
            self.root,
            self.policy,
            self.index,
            ChunkSettings(),
            tracked_paths=frozenset({"docs/h7_hypothesis.md", "docs/fills.md"}),
        )
        self.golden.parent.mkdir()
        self.golden.write_text(
            json.dumps(
                {
                    "id": "g001",
                    "question": "H7 ledger hash chain verification",
                    "expect_paths": ["docs/h7_hypothesis.md"],
                    "expect_any": True,
                    "note": "positive",
                }
            )
            + "\n"
            + json.dumps(
                {
                    "id": "g002",
                    "question": "qxzv absent recipe",
                    "expect_paths": [],
                    "expect_any": True,
                    "note": "negative",
                }
            )
            + "\n",
            encoding="utf-8",
        )

    def test_search_is_passage_only_and_filters_by_hypothesis_doc_type_and_date(self) -> None:
        hits = search(
            self.index,
            "H7 ledger hash chain",
            filters=SearchFilters(hypothesis="h7", doc_type="hypothesis"),
        )

        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].repo_path, "docs/h7_hypothesis.md")
        self.assertEqual(hits[0].source_tier, "canonical")
        self.assertIn("L1-L1", hits[0].locator)

    def test_evaluation_scores_retrieval_and_negative_abstention(self) -> None:
        report = evaluate(load_golden_set(self.golden), self.index)

        self.assertEqual(report.hit_at_k, 1.0)
        self.assertEqual(report.mrr, 1.0)
        self.assertEqual(report.abstention_correct, 1.0)
        self.assertEqual(report.false_hit_rate, 0.0)

    def test_health_writes_only_owned_artifacts(self) -> None:
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        self._git("add", "docs")
        self._git("commit", "-qm", "seed")

        report_path, report, verdict = run_health(
            repository_root=self.root,
            application_root=self.app,
            policy=self.policy,
            index_dir=self.index,
            golden_path=self.golden,
            now=datetime(2026, 7, 20, 7, tzinfo=timezone.utc),
        )

        self.assertEqual(report.hit_at_k, 1.0)
        self.assertFalse(verdict.regressed)
        self.assertTrue(report_path.is_file())
        self.assertTrue((self.app / "eval" / "history.csv").is_file())
        journal = (self.app / "logs" / "writes.jsonl").read_text(encoding="utf-8")
        self.assertIn("tools/repo_rag/eval/history.csv", journal)
        self.assertFalse((self.root / "ledger" / "writes.jsonl").exists())

    def test_writer_refuses_raw_wiki_and_model_paths(self) -> None:
        (self.root / "wiki" / "raw").mkdir(parents=True)
        writer = Writer(self.root, self.app)
        with self.assertRaises(WriteRefusedError):
            writer.write_wiki_page("raw", "source", "no", trigger="test", chunk_ids=())
        with self.assertRaises(WriteRefusedError):
            writer.write_model_supplied_path("ledger/h7_forward/x", "no")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()

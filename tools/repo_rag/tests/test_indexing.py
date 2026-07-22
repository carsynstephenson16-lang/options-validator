from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from repo_rag.chunking import ChunkSettings
from repo_rag.config import CorpusPolicy
from repo_rag.indexing import build_index, classify_doc_type, load_index

FIXED_NOW = datetime(2026, 7, 19, 12, 0, 0, tzinfo=timezone.utc)


def _policy() -> CorpusPolicy:
    return CorpusPolicy(
        application="test-rag",
        repository="test-repo",
        read_only=True,
        tracked_files_only=True,
        corpus_roots=("docs",),
        denied_segments=(),
        supported_suffixes=(".md",),
        source_classes={"derived": ("docs/",)},
    )


class IndexingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.index_dir = self.root / ".index"
        (self.root / "docs").mkdir()
        (self.root / "docs" / "a.md").write_text("alpha content\n", encoding="utf-8")
        (self.root / "docs" / "b.md").write_text("beta content\n", encoding="utf-8")
        self.tracked = frozenset({"docs/a.md", "docs/b.md"})

    def _build(self, tracked: frozenset[str]):
        return build_index(
            repository_root=self.root,
            policy=_policy(),
            index_dir=self.index_dir,
            chunk_settings=ChunkSettings(),
            tracked_paths=tracked,
            now=lambda: FIXED_NOW,
        )

    def test_build_writes_manifest_and_chunks(self) -> None:
        report = self._build(self.tracked)
        self.assertEqual(report.sources_indexed, 2)
        self.assertTrue((self.index_dir / "manifest.json").exists())
        self.assertTrue((self.index_dir / "chunks.jsonl").exists())
        self.assertTrue((self.index_dir / "search.sqlite3").exists())
        manifest = json.loads((self.index_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["built_at_utc"], "2026-07-19T12:00:00+00:00")
        self.assertIn("policy_sha256", manifest)

    def test_rebuild_unchanged_is_idempotent(self) -> None:
        self._build(self.tracked)
        first = (self.index_dir / "chunks.jsonl").read_bytes()
        report = self._build(self.tracked)
        self.assertEqual(report.sources_unchanged, 2)
        self.assertEqual((self.index_dir / "chunks.jsonl").read_bytes(), first)

    def test_changed_source_replaces_stale_chunks(self) -> None:
        self._build(self.tracked)
        (self.root / "docs" / "a.md").write_text("alpha rewritten\n", encoding="utf-8")
        report = self._build(self.tracked)
        self.assertEqual(report.sources_updated, 1)
        index = load_index(self.index_dir)
        texts = [record.text for record in index.chunks if record.source_path == "docs/a.md"]
        self.assertEqual(texts, ["alpha rewritten"])

    def test_deleted_source_chunks_are_removed(self) -> None:
        self._build(self.tracked)
        (self.root / "docs" / "b.md").unlink()
        report = self._build(frozenset({"docs/a.md"}))
        self.assertEqual(report.sources_removed, 1)
        index = load_index(self.index_dir)
        self.assertEqual({record.source_path for record in index.chunks}, {"docs/a.md"})

    def test_load_index_round_trips_provenance(self) -> None:
        self._build(self.tracked)
        index = load_index(self.index_dir)
        record = index.chunks[0]
        self.assertEqual(record.source_class, "derived")
        self.assertEqual(record.parser, "line-chunker-v1")
        self.assertEqual(record.embedding_model, "deterministic-hash-offline")
        self.assertEqual(len(record.embedding), 64)
        self.assertEqual(index.policy_sha256, _policy().digest())

    def test_load_missing_index_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_index(self.index_dir)

    def test_rebuild_with_empty_source_does_not_crash(self) -> None:
        (self.root / "docs" / "empty.md").write_text("", encoding="utf-8")
        tracked = frozenset({"docs/a.md", "docs/b.md", "docs/empty.md"})
        self._build(tracked)
        report = self._build(tracked)
        self.assertEqual(report.sources_unchanged, 3)
        index = load_index(self.index_dir)
        self.assertEqual(
            {record.source_path for record in index.chunks}, {"docs/a.md", "docs/b.md"}
        )

    def test_manifest_key_set_is_pinned(self) -> None:
        self._build(self.tracked)
        manifest = json.loads((self.index_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(manifest),
            {
                "policy_sha256",
                "index_version",
                "generation",
                "embedding_model",
                "embedding_dimensions",
                "chunk_max_chars",
                "chunk_overlap_lines",
                "parser",
                "source_hashes",
                "built_at_utc",
            },
        )

    def test_h7_report_and_frozen_parameter_paths_use_their_path_owned_types(self) -> None:
        self.assertEqual(
            classify_doc_type("reports/2026-07-20-h7-backtest.md"), "backtest_run"
        )
        self.assertEqual(
            classify_doc_type("options_researcher/h7_scope.py"), "frozen_params"
        )

    def test_chunk_row_key_set_is_pinned(self) -> None:
        self._build(self.tracked)
        first_row = json.loads(
            (self.index_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()[0]
        )
        self.assertEqual(
            set(first_row),
            {
                "chunk_id",
                "source_path",
                "source_class",
                "start_line",
                "end_line",
                "text",
                "content_sha256",
                "embedding",
                "parser",
                "embedding_model",
            },
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from repo_rag.chunking import ChunkSettings
from repo_rag.config import CorpusPolicy
from repo_rag.indexing import build_index, load_index

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


if __name__ == "__main__":
    unittest.main()

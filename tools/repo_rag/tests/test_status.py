from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_rag.config import CorpusPolicy
from repo_rag.status import build_status


class StatusTests(unittest.TestCase):
    def _policy(self) -> CorpusPolicy:
        return CorpusPolicy(
            application="test-rag",
            repository="test-repo",
            read_only=True,
            tracked_files_only=True,
            corpus_roots=("README.md", "docs"),
            denied_segments=(".env",),
            supported_suffixes=(".md",),
            source_classes={"canonical": ("README.md",)},
        )

    def test_ready_when_all_roots_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("test", encoding="utf-8")
            (root / "docs").mkdir()
            report = build_status(root, self._policy())
            self.assertEqual(report.status, "READY_OFFLINE")
            self.assertTrue(report.read_only)
            self.assertFalse(report.network_enabled)

    def test_incomplete_when_corpus_root_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = build_status(Path(directory), self._policy())
            self.assertEqual(report.status, "CONFIGURATION_INCOMPLETE")
            self.assertEqual(report.missing_corpus_roots, ("README.md", "docs"))

    def test_status_reports_corrupt_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("test", encoding="utf-8")
            (root / "docs").mkdir()
            index_dir = root / ".index"
            index_dir.mkdir()
            (index_dir / "manifest.json").write_text("{not json", encoding="utf-8")
            (index_dir / "chunks.jsonl").write_text("", encoding="utf-8")
            report = build_status(root, self._policy(), index_dir=index_dir)
            self.assertEqual(report.status, "READY_OFFLINE")
            self.assertFalse(report.index_present)
            self.assertIsNotNone(report.index_error)

    def test_status_reports_missing_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("test", encoding="utf-8")
            (root / "docs").mkdir()
            report = build_status(root, self._policy(), index_dir=root / ".index")
            self.assertEqual(report.status, "READY_OFFLINE")
            self.assertFalse(report.index_present)
            self.assertEqual(report.index_chunk_count, 0)
            self.assertIsNone(report.index_error)

    def test_status_reports_index_counts(self) -> None:
        from datetime import datetime, timezone

        from repo_rag.chunking import ChunkSettings
        from repo_rag.indexing import build_index

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("readme body", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "a.md").write_text("alpha\n", encoding="utf-8")
            policy = self._policy()
            build_index(
                repository_root=root,
                policy=policy,
                index_dir=root / ".index",
                chunk_settings=ChunkSettings(),
                tracked_paths=frozenset({"README.md", "docs/a.md"}),
                now=lambda: datetime(2026, 7, 19, tzinfo=timezone.utc),
            )
            report = build_status(root, policy, index_dir=root / ".index")
            self.assertTrue(report.index_present)
            self.assertEqual(report.index_chunk_count, 2)
            self.assertEqual(report.phase, "retrieval-online")


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

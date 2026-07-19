from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from repo_rag.config import CorpusPolicy
from repo_rag.corpus import discover_sources


def _policy() -> CorpusPolicy:
    return CorpusPolicy(
        application="test-rag",
        repository="test-repo",
        read_only=True,
        tracked_files_only=True,
        corpus_roots=("README.md", "docs", "notes"),
        denied_segments=(".env", "docs/private"),
        supported_suffixes=(".md", ".py"),
        source_classes={"canonical": ("README.md",), "derived": ("docs/", "notes/")},
    )


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class DiscoverSourcesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        _write(self.root, "README.md", "# Readme\nbody\n")
        _write(self.root, "docs/a.md", "alpha\n")
        _write(self.root, "docs/private/secret.md", "hidden\n")
        _write(self.root, "docs/img.png", "binary")
        _write(self.root, "notes/b.py", "x = 1\n")
        _write(self.root, "outside/c.md", "outside corpus roots\n")
        _write(self.root, "docs/untracked.md", "not in git\n")
        self.tracked = frozenset(
            {
                "README.md",
                "docs/a.md",
                "docs/private/secret.md",
                "docs/img.png",
                "notes/b.py",
                "outside/c.md",
            }
        )

    def _paths(self) -> list[str]:
        sources = discover_sources(self.root, _policy(), tracked_paths=self.tracked)
        return [source.path for source in sources]

    def test_includes_only_tracked_supported_files_under_corpus_roots(self) -> None:
        self.assertEqual(self._paths(), ["README.md", "docs/a.md", "notes/b.py"])

    def test_denied_segment_excluded(self) -> None:
        self.assertNotIn("docs/private/secret.md", self._paths())

    def test_untracked_file_excluded(self) -> None:
        self.assertNotIn("docs/untracked.md", self._paths())

    def test_source_class_and_hash_recorded(self) -> None:
        sources = discover_sources(self.root, _policy(), tracked_paths=self.tracked)
        by_path = {source.path: source for source in sources}
        self.assertEqual(by_path["README.md"].source_class, "canonical")
        self.assertEqual(by_path["docs/a.md"].source_class, "derived")
        self.assertEqual(len(by_path["README.md"].content_sha256), 64)

    def test_unclassified_path_gets_unclassified_label(self) -> None:
        policy = CorpusPolicy(
            application="t",
            repository="t",
            read_only=True,
            tracked_files_only=True,
            corpus_roots=("README.md",),
            denied_segments=(),
            supported_suffixes=(".md",),
            source_classes={"canonical": ("docs/",)},
        )
        sources = discover_sources(self.root, policy, tracked_paths=frozenset({"README.md"}))
        self.assertEqual(sources[0].source_class, "unclassified")

    def test_ordering_is_stable_sorted(self) -> None:
        first = self._paths()
        second = self._paths()
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))


if __name__ == "__main__":
    unittest.main()

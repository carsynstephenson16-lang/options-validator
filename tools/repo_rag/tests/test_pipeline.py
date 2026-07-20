from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from repo_rag.chunking import ChunkSettings
from repo_rag.config import CorpusPolicy
from repo_rag.indexing import build_index
from repo_rag.pipeline import answer_query
from repo_rag.retrieval import RetrievalSettings

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


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.index_dir = self.root / ".index"
        (self.root / "docs").mkdir()
        (self.root / "docs" / "fills.md").write_text(
            "Fills execute at quote mid or worse with a slippage haircut.\n",
            encoding="utf-8",
        )
        build_index(
            repository_root=self.root,
            policy=_policy(),
            index_dir=self.index_dir,
            chunk_settings=ChunkSettings(),
            tracked_paths=frozenset({"docs/fills.md"}),
            now=lambda: FIXED_NOW,
        )

    def _ask(self, query: str, settings: RetrievalSettings | None = None):
        return answer_query(
            query=query,
            index_dir=self.index_dir,
            settings=settings or RetrievalSettings(),
            now=lambda: FIXED_NOW,
        )

    def test_grounded_answer_with_verified_citation(self) -> None:
        result = self._ask("how do fills execute")
        self.assertEqual(result.outcome, "ANSWERED")
        self.assertIn("docs/fills.md:L1-L1", result.citations)
        self.assertIn("[docs/fills.md:L1-L1]", result.answer)
        self.assertTrue(result.citations_verified)

    def test_abstains_when_no_evidence(self) -> None:
        # "zzqx totally unrelated question" scores 0.1387 against the fixture text
        # under the deterministic hash embedding (a hash collision, not semantic
        # similarity) -- above the default min_score=0.12, so it would not abstain.
        # This query scores 0.0 (no cosine or lexical overlap) and reliably abstains.
        result = self._ask("purple giraffe kayak festival")
        self.assertEqual(result.outcome, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(result.citations, ())
        self.assertIn("Insufficient repository evidence", result.answer)

    def test_empty_query_rejected(self) -> None:
        result = self._ask("   ")
        self.assertEqual(result.outcome, "EMPTY_QUERY")

    def test_missing_index_reported(self) -> None:
        result = answer_query(
            query="anything",
            index_dir=self.root / "nope",
            settings=RetrievalSettings(),
            now=lambda: FIXED_NOW,
        )
        self.assertEqual(result.outcome, "INDEX_MISSING")

    def test_event_log_appends_hash_not_query_text(self) -> None:
        self._ask("how do fills execute")
        self._ask("zzqx totally unrelated question")
        lines = (self.index_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertEqual(first["outcome"], "ANSWERED")
        self.assertEqual(len(first["query_sha256"]), 64)
        self.assertNotIn("fills", json.dumps(first))
        self.assertEqual(first["retrieval_mode"], "exact-brute-force")

    def test_context_budget_truncates_hits(self) -> None:
        for name in ("a", "b", "c"):
            (self.root / "docs" / f"{name}.md").write_text(
                f"fills note {name}: fills execute at mid or worse\n", encoding="utf-8"
            )
        build_index(
            repository_root=self.root,
            policy=_policy(),
            index_dir=self.index_dir,
            chunk_settings=ChunkSettings(),
            tracked_paths=frozenset(
                {"docs/fills.md", "docs/a.md", "docs/b.md", "docs/c.md"}
            ),
            now=lambda: FIXED_NOW,
        )
        result = answer_query(
            query="fills execute",
            index_dir=self.index_dir,
            settings=RetrievalSettings(min_score=0.0),
            max_context_chars=80,
            now=lambda: FIXED_NOW,
        )
        self.assertEqual(result.outcome, "ANSWERED")
        self.assertEqual(len(result.citations), 1)

    def test_corrupt_index_reported_not_raised(self) -> None:
        (self.index_dir / "manifest.json").write_text("{not json", encoding="utf-8")
        result = self._ask("anything at all")
        self.assertEqual(result.outcome, "INDEX_CORRUPT")
        self.assertEqual(result.citations, ())


if __name__ == "__main__":
    unittest.main()

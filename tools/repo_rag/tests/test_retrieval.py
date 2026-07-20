from __future__ import annotations

import unittest

from repo_rag.indexing import ChunkRecord
from repo_rag.providers import DeterministicHashEmbedding
from repo_rag.retrieval import RetrievalSettings, retrieve


def _record(chunk_id: str, path: str, text: str, source_class: str = "derived") -> ChunkRecord:
    embedder = DeterministicHashEmbedding()
    return ChunkRecord(
        chunk_id=chunk_id,
        source_path=path,
        source_class=source_class,
        start_line=1,
        end_line=1,
        text=text,
        content_sha256="0" * 64,
        embedding=embedder.embed(text),
        parser="line-chunker-v1",
        embedding_model=embedder.name,
    )


CHUNKS = (
    _record("c1", "docs/slippage.md", "slippage haircut applies on top of quote mid fills"),
    _record("c2", "docs/liquidity.md", "liquidity gates check open interest and spread"),
    _record("c3", "docs/verdict.md", "verdicts gate on losses not win rate", "canonical"),
)


class RetrievalTests(unittest.TestCase):
    def test_relevant_chunk_ranks_first(self) -> None:
        hits = retrieve("slippage haircut on fills", CHUNKS, RetrievalSettings())
        self.assertEqual(hits[0].record.chunk_id, "c1")
        self.assertGreater(hits[0].score, 0.0)

    def test_top_k_limits_results(self) -> None:
        hits = retrieve("gates", CHUNKS, RetrievalSettings(top_k=1, min_score=0.0))
        self.assertEqual(len(hits), 1)

    def test_min_score_filters_unrelated(self) -> None:
        hits = retrieve(
            "zzqx unrelated nonsense tokens",
            CHUNKS,
            RetrievalSettings(min_score=0.2),
        )
        self.assertEqual(hits, ())

    def test_source_class_filter(self) -> None:
        hits = retrieve(
            "verdicts gate on losses",
            CHUNKS,
            RetrievalSettings(min_score=0.0, source_classes=("canonical",)),
        )
        self.assertTrue(hits)
        for hit in hits:
            self.assertEqual(hit.record.source_class, "canonical")

    def test_deterministic_ordering_with_tie_break(self) -> None:
        first = retrieve("gates", CHUNKS, RetrievalSettings(min_score=0.0))
        second = retrieve("gates", CHUNKS, RetrievalSettings(min_score=0.0))
        self.assertEqual(
            [hit.record.chunk_id for hit in first],
            [hit.record.chunk_id for hit in second],
        )

    def test_invalid_settings_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RetrievalSettings(top_k=0)
        with self.assertRaises(ValueError):
            RetrievalSettings(vector_weight=0.8, lexical_weight=0.1)


if __name__ == "__main__":
    unittest.main()

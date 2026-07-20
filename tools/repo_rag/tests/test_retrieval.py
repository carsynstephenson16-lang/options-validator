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

    def test_embedding_dimension_mismatch_raises(self) -> None:
        bad = _record("cx", "docs/bad.md", "some text")
        object.__setattr__(bad, "embedding", bad.embedding[:32])
        with self.assertRaises(ValueError):
            retrieve("query text", (bad,), RetrievalSettings(min_score=0.0))

    def test_empty_source_classes_returns_all_classes(self) -> None:
        # "gates" (plural) lexically overlaps c2's "gates"; "gate" (singular)
        # overlaps c3's "gate" — both real words already in the fixture text,
        # needed post-Option-B since require_lexical_overlap now drops chunks
        # with zero token overlap with the query.
        hits = retrieve("gates gate", CHUNKS, RetrievalSettings(min_score=0.0))
        classes = {hit.record.source_class for hit in hits}
        self.assertIn("derived", classes)
        self.assertIn("canonical", classes)

    def test_equal_score_tie_break_orders_by_path_then_id(self) -> None:
        twin_a = _record("id-b", "docs/z.md", "identical text twin")
        twin_b = _record("id-a", "docs/a.md", "identical text twin")
        hits = retrieve("identical text twin", (twin_a, twin_b), RetrievalSettings(min_score=0.0))
        self.assertEqual(
            [(hit.record.source_path, hit.record.chunk_id) for hit in hits],
            [("docs/a.md", "id-a"), ("docs/z.md", "id-b")],
        )

    def test_component_scores_populated(self) -> None:
        hits = retrieve("slippage haircut on fills", CHUNKS, RetrievalSettings(min_score=0.0))
        self.assertGreater(hits[0].vector_score, 0.0)
        self.assertGreater(hits[0].lexical_score, 0.0)

    def test_stopwords_excluded_from_lexical_tokens(self) -> None:
        from repo_rag.retrieval import _tokens

        self.assertEqual(
            _tokens("the of and to a in recipe for dough"),
            frozenset({"recipe", "dough"}),
        )

    def test_zero_lexical_overlap_dropped_when_required(self) -> None:
        hits = retrieve(
            "qqzv zxqj sourdough hydration",
            CHUNKS,
            RetrievalSettings(min_score=0.0),
        )
        self.assertEqual(hits, ())

    def test_zero_lexical_overlap_kept_when_not_required(self) -> None:
        hits = retrieve(
            "qqzv zxqj sourdough hydration",
            CHUNKS,
            RetrievalSettings(min_score=0.0, require_lexical_overlap=False),
        )
        self.assertGreater(len(hits), 0)


if __name__ == "__main__":
    unittest.main()

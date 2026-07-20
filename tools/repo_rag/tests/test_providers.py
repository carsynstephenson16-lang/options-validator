from __future__ import annotations

import unittest

from repo_rag.providers import (
    DeterministicHashEmbedding,
    ExtractiveGenerator,
    RetrievedContext,
)


class ProviderTests(unittest.TestCase):
    def test_hash_embedding_is_deterministic_and_normalized(self) -> None:
        provider = DeterministicHashEmbedding(dimensions=16)
        first = provider.embed("retrieval augmented generation")
        second = provider.embed("retrieval augmented generation")
        self.assertEqual(first, second)
        self.assertAlmostEqual(sum(value * value for value in first), 1.0)

    def test_extractive_generator_refuses_without_context(self) -> None:
        generator = ExtractiveGenerator()
        self.assertEqual(generator.generate("question", []), "Insufficient repository evidence.")

    def test_extractive_generator_preserves_citation(self) -> None:
        generator = ExtractiveGenerator()
        result = generator.generate(
            "question",
            [RetrievedContext(text="Repository evidence", citation="README.md:10")],
        )
        self.assertIn("Repository evidence", result)
        self.assertIn("[README.md:10]", result)


if __name__ == "__main__":
    unittest.main()

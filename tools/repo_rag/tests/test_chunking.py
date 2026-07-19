from __future__ import annotations

import unittest

from repo_rag.chunking import ChunkSettings, chunk_text


class ChunkingTests(unittest.TestCase):
    def test_short_text_is_single_chunk_with_full_span(self) -> None:
        chunks = chunk_text("path.md", "one\ntwo\nthree\n", ChunkSettings())
        self.assertEqual(len(chunks), 1)
        self.assertEqual((chunks[0].start_line, chunks[0].end_line), (1, 3))
        self.assertEqual(chunks[0].text, "one\ntwo\nthree")

    def test_long_text_splits_with_overlap(self) -> None:
        lines = "\n".join(f"line {i:03d} " + "x" * 40 for i in range(1, 41))
        settings = ChunkSettings(max_chars=400, overlap_lines=2)
        chunks = chunk_text("path.md", lines, settings)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), settings.max_chars)
        for previous, current in zip(chunks, chunks[1:]):
            self.assertEqual(current.start_line, previous.end_line - 1)

    def test_spans_cover_every_line_without_gaps(self) -> None:
        lines = "\n".join(f"line {i}" for i in range(1, 30))
        chunks = chunk_text("p.md", lines, ChunkSettings(max_chars=80, overlap_lines=1))
        covered: set[int] = set()
        for chunk in chunks:
            covered.update(range(chunk.start_line, chunk.end_line + 1))
        self.assertEqual(covered, set(range(1, 30)))

    def test_chunk_id_is_deterministic_and_span_sensitive(self) -> None:
        first = chunk_text("p.md", "alpha\nbeta", ChunkSettings())
        second = chunk_text("p.md", "alpha\nbeta", ChunkSettings())
        other = chunk_text("q.md", "alpha\nbeta", ChunkSettings())
        self.assertEqual(first[0].chunk_id, second[0].chunk_id)
        self.assertNotEqual(first[0].chunk_id, other[0].chunk_id)
        self.assertEqual(len(first[0].chunk_id), 16)

    def test_oversized_single_line_is_hard_split(self) -> None:
        text = "y" * 1000
        chunks = chunk_text("p.md", text, ChunkSettings(max_chars=300, overlap_lines=0))
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), 300)
            self.assertEqual((chunk.start_line, chunk.end_line), (1, 1))

    def test_empty_text_yields_no_chunks(self) -> None:
        self.assertEqual(chunk_text("p.md", "", ChunkSettings()), ())

    def test_citation_property(self) -> None:
        chunk = chunk_text("docs/a.md", "alpha\nbeta", ChunkSettings())[0]
        self.assertEqual(chunk.citation, "docs/a.md:L1-L2")


if __name__ == "__main__":
    unittest.main()

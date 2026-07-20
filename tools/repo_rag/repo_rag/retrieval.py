from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Sequence

from .indexing import ChunkRecord
from .providers import DeterministicHashEmbedding

RETRIEVAL_MODE = "exact-brute-force"


@dataclass(frozen=True)
class RetrievalSettings:
    top_k: int = 5
    min_score: float = 0.12
    vector_weight: float = 0.5
    lexical_weight: float = 0.5
    source_classes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not 0.0 <= self.min_score <= 1.0:
            raise ValueError("min_score must be within [0, 1]")
        if abs(self.vector_weight + self.lexical_weight - 1.0) > 1e-9:
            raise ValueError("vector_weight + lexical_weight must equal 1.0")


@dataclass(frozen=True)
class RetrievedHit:
    record: ChunkRecord
    score: float
    vector_score: float
    lexical_score: float


def _tokens(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9_]+", text.casefold()))


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def retrieve(
    query: str,
    chunks: Sequence[ChunkRecord],
    settings: RetrievalSettings,
) -> tuple[RetrievedHit, ...]:
    embedder = DeterministicHashEmbedding()
    query_embedding = embedder.embed(query)
    query_tokens = _tokens(query)
    hits: list[RetrievedHit] = []
    for record in chunks:
        if settings.source_classes and record.source_class not in settings.source_classes:
            continue
        if len(record.embedding) != len(query_embedding):
            raise ValueError(
                f"embedding dimension mismatch: query {len(query_embedding)} "
                f"vs chunk {len(record.embedding)} ({record.chunk_id})"
            )
        vector_score = max(0.0, _cosine(query_embedding, record.embedding))
        lexical_score = _jaccard(query_tokens, _tokens(record.text))
        score = settings.vector_weight * vector_score + settings.lexical_weight * lexical_score
        if score < settings.min_score:
            continue
        hits.append(
            RetrievedHit(
                record=record,
                score=score,
                vector_score=vector_score,
                lexical_score=lexical_score,
            )
        )
    hits.sort(key=lambda hit: (-hit.score, hit.record.source_path, hit.record.chunk_id))
    return tuple(hits[: settings.top_k])

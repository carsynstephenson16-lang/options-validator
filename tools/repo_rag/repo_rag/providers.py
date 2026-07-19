from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Protocol, Sequence


class EmbeddingProvider(Protocol):
    name: str

    def embed(self, text: str) -> tuple[float, ...]: ...


class GeneratorProvider(Protocol):
    name: str

    def generate(self, question: str, contexts: Sequence[RetrievedContext]) -> str: ...


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    citation: str


class DeterministicHashEmbedding:
    """Offline test embedding; not a production semantic model."""

    name = "deterministic-hash-offline"

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self.dimensions = dimensions

    def embed(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self.dimensions
        for token in re.findall(r"[A-Za-z0-9_]+", text.casefold()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0:
            return tuple(values)
        return tuple(value / norm for value in values)


class ExtractiveGenerator:
    """Offline generator that exposes evidence without inventing a synthesis."""

    name = "extractive-offline"

    def generate(self, question: str, contexts: Sequence[RetrievedContext]) -> str:
        del question
        if not contexts:
            return "Insufficient repository evidence."
        lines = ["Offline evidence preview:"]
        for context in contexts:
            compact = " ".join(context.text.split())
            lines.append(f"- {compact[:240]} [{context.citation}]")
        return "\n".join(lines)

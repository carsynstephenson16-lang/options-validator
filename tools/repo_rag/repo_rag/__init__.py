"""Read-only repository RAG application."""

from .config import CorpusPolicy, load_policy
from .providers import DeterministicHashEmbedding, ExtractiveGenerator

__all__ = [
    "CorpusPolicy",
    "DeterministicHashEmbedding",
    "ExtractiveGenerator",
    "load_policy",
]

__version__ = "0.1.0"

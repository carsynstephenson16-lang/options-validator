from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import CorpusPolicy
from .providers import DeterministicHashEmbedding, ExtractiveGenerator


@dataclass(frozen=True)
class StatusReport:
    status: str
    phase: str
    application: str
    repository: str
    repository_root: str
    read_only: bool
    bounded_writes: bool
    network_enabled: bool
    tracked_files_only: bool
    policy_sha256: str
    embedding_provider: str
    generator_provider: str
    configured_corpus_roots: int
    existing_corpus_roots: int
    missing_corpus_roots: tuple[str, ...]
    index_present: bool
    index_chunk_count: int
    index_built_at_utc: str | None
    index_error: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def build_status(
    repository_root: Path,
    policy: CorpusPolicy,
    index_dir: Path | None = None,
) -> StatusReport:
    root = repository_root.resolve()
    missing = tuple(path for path in policy.corpus_roots if not (root / path).exists())
    healthy = root.is_dir() and policy.read_only and not missing

    index_present = False
    index_chunk_count = 0
    index_built_at: str | None = None
    index_error: str | None = None
    if index_dir is not None:
        try:
            from .indexing import load_index

            index = load_index(index_dir)
            index_present = True
            index_chunk_count = len(index.chunks)
            index_built_at = index.built_at_utc
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, KeyError, ValueError, UnicodeDecodeError) as exc:
            index_error = f"corrupt: {type(exc).__name__}"

    return StatusReport(
        status="READY_OFFLINE" if healthy else "CONFIGURATION_INCOMPLETE",
        phase="retrieval-online" if index_present else "isolated-skeleton",
        application=policy.application,
        repository=policy.repository,
        repository_root=str(root),
        read_only=policy.read_only,
        bounded_writes=policy.bounded_writes,
        network_enabled=False,
        tracked_files_only=policy.tracked_files_only,
        policy_sha256=policy.digest(),
        embedding_provider=DeterministicHashEmbedding.name,
        generator_provider=ExtractiveGenerator.name,
        configured_corpus_roots=len(policy.corpus_roots),
        existing_corpus_roots=len(policy.corpus_roots) - len(missing),
        missing_corpus_roots=missing,
        index_present=index_present,
        index_chunk_count=index_chunk_count,
        index_built_at_utc=index_built_at,
        index_error=index_error,
    )

from __future__ import annotations

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
    network_enabled: bool
    tracked_files_only: bool
    policy_sha256: str
    embedding_provider: str
    generator_provider: str
    configured_corpus_roots: int
    existing_corpus_roots: int
    missing_corpus_roots: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


def build_status(repository_root: Path, policy: CorpusPolicy) -> StatusReport:
    root = repository_root.resolve()
    missing = tuple(path for path in policy.corpus_roots if not (root / path).exists())
    healthy = root.is_dir() and policy.read_only and not missing
    return StatusReport(
        status="READY_OFFLINE" if healthy else "CONFIGURATION_INCOMPLETE",
        phase="isolated-skeleton",
        application=policy.application,
        repository=policy.repository,
        repository_root=str(root),
        read_only=policy.read_only,
        network_enabled=False,
        tracked_files_only=policy.tracked_files_only,
        policy_sha256=policy.digest(),
        embedding_provider=DeterministicHashEmbedding.name,
        generator_provider=ExtractiveGenerator.name,
        configured_corpus_roots=len(policy.corpus_roots),
        existing_corpus_roots=len(policy.corpus_roots) - len(missing),
        missing_corpus_roots=missing,
    )

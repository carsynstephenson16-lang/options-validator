from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import CorpusPolicy


@dataclass(frozen=True)
class SourceFile:
    path: str
    source_class: str
    content_sha256: str
    line_count: int


def git_tracked_paths(repository_root: Path) -> frozenset[str]:
    """Ask git for tracked paths. Callers in tests inject tracked_paths instead."""
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository_root,
        capture_output=True,
        check=True,
    )
    entries = completed.stdout.decode("utf-8").split("\0")
    return frozenset(entry for entry in entries if entry)


def _under_corpus_roots(path: str, policy: CorpusPolicy) -> bool:
    return any(path == root or path.startswith(root + "/") for root in policy.corpus_roots)


def _denied(path: str, policy: CorpusPolicy) -> bool:
    segments = path.split("/")
    for denied in policy.denied_segments:
        if "/" in denied:
            if path == denied or path.startswith(denied + "/"):
                return True
        elif denied in segments:
            return True
    return False


def classify_source(path: str, policy: CorpusPolicy) -> str:
    for name in sorted(policy.source_classes):
        for prefix in policy.source_classes[name]:
            if path == prefix or path.startswith(prefix):
                return name
    return "unclassified"


def discover_sources(
    repository_root: Path,
    policy: CorpusPolicy,
    tracked_paths: frozenset[str] | None = None,
) -> tuple[SourceFile, ...]:
    if tracked_paths is None:
        tracked_paths = git_tracked_paths(repository_root)
    selected: list[SourceFile] = []
    for path in sorted(tracked_paths):
        if not _under_corpus_roots(path, policy):
            continue
        if _denied(path, policy):
            continue
        if not any(path.endswith(suffix) for suffix in policy.supported_suffixes):
            continue
        absolute = repository_root / path
        if not absolute.is_file():
            continue
        raw = absolute.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        selected.append(
            SourceFile(
                path=path,
                source_class=classify_source(path, policy),
                content_sha256=hashlib.sha256(raw).hexdigest(),
                line_count=text.count("\n") + (0 if text.endswith("\n") or not text else 1),
            )
        )
    return tuple(selected)

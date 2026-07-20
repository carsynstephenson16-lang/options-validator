from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CorpusPolicy:
    application: str
    repository: str
    read_only: bool
    tracked_files_only: bool
    corpus_roots: tuple[str, ...]
    denied_segments: tuple[str, ...]
    supported_suffixes: tuple[str, ...]
    source_classes: dict[str, tuple[str, ...]]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> CorpusPolicy:
        required = {
            "application",
            "repository",
            "read_only",
            "tracked_files_only",
            "corpus_roots",
            "denied_segments",
            "supported_suffixes",
            "source_classes",
        }
        missing = sorted(required - raw.keys())
        if missing:
            raise ValueError(f"policy missing required fields: {', '.join(missing)}")

        source_classes = {
            str(name): tuple(str(prefix) for prefix in prefixes)
            for name, prefixes in dict(raw["source_classes"]).items()
        }
        return cls(
            application=str(raw["application"]),
            repository=str(raw["repository"]),
            read_only=bool(raw["read_only"]),
            tracked_files_only=bool(raw["tracked_files_only"]),
            corpus_roots=tuple(str(item) for item in raw["corpus_roots"]),
            denied_segments=tuple(str(item) for item in raw["denied_segments"]),
            supported_suffixes=tuple(str(item) for item in raw["supported_suffixes"]),
            source_classes=source_classes,
        )

    def digest(self) -> str:
        payload = json.dumps(
            {
                "application": self.application,
                "repository": self.repository,
                "read_only": self.read_only,
                "tracked_files_only": self.tracked_files_only,
                "corpus_roots": self.corpus_roots,
                "denied_segments": self.denied_segments,
                "supported_suffixes": self.supported_suffixes,
                "source_classes": self.source_classes,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def load_policy(path: Path) -> CorpusPolicy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("policy root must be a JSON object")
    return CorpusPolicy.from_mapping(raw)

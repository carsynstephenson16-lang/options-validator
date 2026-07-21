"""Fail-closed writer for options-validator RAG-owned reports and wiki pages."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_STEM_RE = re.compile(r"[A-Za-z0-9._-]+\Z")


class WriteRefusedError(ValueError):
    """The target is outside this repository's owner-approved write boundary."""


class Writer:
    """Build paths from code-owned directories, never retrieved/model text."""

    def __init__(self, repository_root: Path, application_root: Path) -> None:
        self.repository_root = repository_root.resolve()
        self.application_root = application_root.resolve()
        if not self.application_root.is_relative_to(self.repository_root):
            raise WriteRefusedError("application root must stay inside repository root")

    @staticmethod
    def _stem(stem: str) -> str:
        normalized = stem.removesuffix(".md")
        if not normalized or normalized.startswith(".") or not _STEM_RE.fullmatch(normalized):
            raise WriteRefusedError("invalid filename stem")
        return normalized

    def _resolve(self, target: Path, allowed: Path) -> Path:
        resolved = target.resolve()
        allowed_resolved = allowed.resolve()
        if not resolved.is_relative_to(self.repository_root):
            raise WriteRefusedError("target escapes repository root")
        if not resolved.is_relative_to(allowed_resolved):
            raise WriteRefusedError("target is not allowlisted")
        return resolved

    def _journal(self, target: Path, content: str, trigger: str, chunk_ids: tuple[str, ...]) -> None:
        journal = self._resolve(
            self.application_root / "logs" / "writes.jsonl", self.application_root / "logs"
        )
        journal.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "target_path": target.relative_to(self.repository_root).as_posix(),
            "byte_count": len(content.encode("utf-8")),
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "trigger": trigger,
            "chunk_ids": list(chunk_ids),
        }
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    @staticmethod
    def _version(target: Path) -> Path:
        if not target.exists():
            return target
        for suffix in range(2, 10_000):
            candidate = target.with_name(f"{target.stem}_{suffix}{target.suffix}")
            if not candidate.exists():
                return candidate
        raise WriteRefusedError("cannot allocate versioned target")

    def write_report(
        self, stem: str, content: str, *, trigger: str, chunk_ids: tuple[str, ...]
    ) -> Path:
        directory = self.application_root / "reports"
        target = self._resolve(directory / f"{self._stem(stem)}.md", directory)
        target = self._resolve(self._version(target), directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._journal(target, content, trigger, chunk_ids)
        return target

    def journal_evaluation_history(self, *, trigger: str) -> None:
        """Record the append-only evaluation history write in the audit journal."""
        history = self._resolve(
            self.application_root / "eval" / "history.csv", self.application_root / "eval"
        )
        if not history.is_file():
            raise WriteRefusedError("evaluation history must exist before it can be journaled")
        self._journal(history, history.read_text(encoding="utf-8"), trigger, ())

    def write_wiki_page(
        self,
        section: str,
        stem: str,
        content: str,
        *,
        trigger: str,
        chunk_ids: tuple[str, ...],
    ) -> Path:
        if section not in {"entities", "concepts", "sources", "workflows"}:
            raise WriteRefusedError("wiki section is not allowlisted")
        directory = self.repository_root / "wiki" / section
        target = self._resolve(directory / f"{self._stem(stem)}.md", directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._journal(target, content, trigger, chunk_ids)
        return target

    def write_model_supplied_path(self, _path: str, _content: str) -> None:
        raise WriteRefusedError("model-supplied paths are never honored")

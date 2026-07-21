"""Fail-closed writer for options-validator RAG-owned reports and wiki pages."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from csv import DictReader, DictWriter
from datetime import datetime, timezone
from pathlib import Path

_STEM_RE = re.compile(r"[A-Za-z0-9._-]+\Z")


class WriteRefusedError(ValueError):
    """The target is outside this repository's owner-approved write boundary."""


class Writer:
    """Build paths from code-owned directories, never retrieved/model text."""

    def __init__(self, repository_root: Path, application_root: Path, *, bounded_writes: bool) -> None:
        self.repository_root = repository_root.resolve()
        self.application_root = application_root.resolve()
        self.bounded_writes = bounded_writes
        if not self.application_root.is_relative_to(self.repository_root):
            raise WriteRefusedError("application root must stay inside repository root")

    def _require_bounded_writes(self) -> None:
        if not self.bounded_writes:
            raise WriteRefusedError("policy does not authorize bounded RAG writes")

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
        self._require_bounded_writes()
        directory = self.application_root / "reports"
        target = self._resolve(directory / f"{self._stem(stem)}.md", directory)
        target = self._resolve(self._version(target), directory)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=target.parent, delete=False
            ) as handle:
                temporary_name = handle.name
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
        except OSError:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
            raise
        self._journal(target, content, trigger, chunk_ids)
        return target

    def evaluation_history_path(self) -> Path:
        """Resolve the RAG-owned history target before any caller can create it."""
        self._require_bounded_writes()
        return self._resolve(
            self.application_root / "eval" / "history.csv", self.application_root / "eval"
        )

    def append_evaluation_history(
        self, row: dict[str, str], fieldnames: tuple[str, ...], *, trigger: str
    ) -> None:
        """Append a schema-pinned evaluation row only inside the approved app root."""
        target = self.evaluation_history_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        needs_header = not target.exists() or target.stat().st_size == 0
        if not needs_header:
            with target.open(encoding="utf-8", newline="") as handle:
                reader = DictReader(handle)
                existing_rows = list(reader)
                existing_fields = tuple(reader.fieldnames or ())
            if existing_fields != fieldnames:
                expected_legacy = tuple(field for field in fieldnames if field != "index_version")
                if existing_fields != expected_legacy:
                    raise WriteRefusedError("evaluation history has an unsupported schema")
                temporary_name: str | None = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", encoding="utf-8", dir=target.parent, delete=False, newline=""
                    ) as handle:
                        temporary_name = handle.name
                        migrated = DictWriter(handle, fieldnames=fieldnames)
                        migrated.writeheader()
                        for existing in existing_rows:
                            migrated.writerow({"index_version": "legacy", **existing})
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary_name, target)
                except OSError:
                    if temporary_name is not None:
                        Path(temporary_name).unlink(missing_ok=True)
                    raise
        with target.open("a", encoding="utf-8", newline="") as handle:
            writer = DictWriter(handle, fieldnames=fieldnames)
            if needs_header:
                writer.writeheader()
            writer.writerow(row)
        self._journal(target, target.read_text(encoding="utf-8"), trigger, ())

    def journal_evaluation_history(self, *, trigger: str) -> None:
        """Record the append-only evaluation history write in the audit journal."""
        self._require_bounded_writes()
        history = self.evaluation_history_path()
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
        self._require_bounded_writes()
        if section not in {"entities", "concepts", "sources", "workflows"}:
            raise WriteRefusedError("wiki section is not allowlisted")
        directory = self.repository_root / "wiki" / section
        target = self._resolve(directory / f"{self._stem(stem)}.md", directory)
        if target.exists():
            raise WriteRefusedError("refusing to overwrite an existing wiki page")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._journal(target, content, trigger, chunk_ids)
        return target

    def append_wiki_log(
        self,
        operation: str,
        title: str,
        body: str,
        *,
        trigger: str,
        occurred_at: datetime | None = None,
    ) -> None:
        """Append the required wiki audit event without allowing arbitrary wiki overwrites."""
        self._require_bounded_writes()
        if operation not in {"ingest", "lint", "query"}:
            raise WriteRefusedError("wiki-log operation is not allowlisted")
        if not title or "\n" in title or not body:
            raise WriteRefusedError("wiki-log title and body must be non-empty single-line/title content")
        target = self._resolve(self.repository_root / "wiki" / "log.md", self.repository_root / "wiki")
        event_date = (occurred_at or datetime.now(timezone.utc)).astimezone(timezone.utc).date().isoformat()
        entry = (
            f"\n\n## [{event_date}] {operation} | {title}\n\n"
            f"{body.strip()}\n"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("# Wiki Log" + entry, encoding="utf-8")
        else:
            with target.open("a", encoding="utf-8") as handle:
                handle.write(entry)
        content = target.read_text(encoding="utf-8")
        self._journal(target, content, trigger, ())

    def write_model_supplied_path(self, _path: str, _content: str) -> None:
        raise WriteRefusedError("model-supplied paths are never honored")

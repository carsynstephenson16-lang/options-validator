from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .chunking import ChunkSettings, chunk_text
from .config import CorpusPolicy
from .corpus import SourceFile, discover_sources
from .providers import DeterministicHashEmbedding

PARSER_NAME = "line-chunker-v1"


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    source_path: str
    source_class: str
    start_line: int
    end_line: int
    text: str
    content_sha256: str
    embedding: tuple[float, ...]
    parser: str
    embedding_model: str

    @property
    def citation(self) -> str:
        return f"{self.source_path}:L{self.start_line}-L{self.end_line}"


@dataclass(frozen=True)
class IndexReport:
    sources_indexed: int
    sources_unchanged: int
    sources_updated: int
    sources_removed: int
    chunk_count: int


@dataclass(frozen=True)
class LoadedIndex:
    policy_sha256: str
    embedding_model: str
    built_at_utc: str
    chunks: tuple[ChunkRecord, ...]


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


def _chunk_records(source: SourceFile, text: str, settings: ChunkSettings,
                   embedder: DeterministicHashEmbedding) -> list[ChunkRecord]:
    records = []
    for chunk in chunk_text(source.path, text, settings):
        records.append(
            ChunkRecord(
                chunk_id=chunk.chunk_id,
                source_path=source.path,
                source_class=source.source_class,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                text=chunk.text,
                content_sha256=source.content_sha256,
                embedding=embedder.embed(chunk.text),
                parser=PARSER_NAME,
                embedding_model=embedder.name,
            )
        )
    return records


def build_index(
    repository_root: Path,
    policy: CorpusPolicy,
    index_dir: Path,
    chunk_settings: ChunkSettings,
    tracked_paths: frozenset[str] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> IndexReport:
    embedder = DeterministicHashEmbedding()
    sources = discover_sources(repository_root, policy, tracked_paths=tracked_paths)
    previous_hashes: dict[str, str] = {}
    previous_records: dict[str, list[dict]] = {}
    manifest_path = index_dir / "manifest.json"
    chunks_path = index_dir / "chunks.jsonl"
    if manifest_path.exists() and chunks_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("policy_sha256") == policy.digest():
            previous_hashes = dict(manifest.get("source_hashes", {}))
            for line in chunks_path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                previous_records.setdefault(record["source_path"], []).append(record)

    unchanged = updated = 0
    all_rows: list[dict] = []
    source_hashes: dict[str, str] = {}
    for source in sources:
        source_hashes[source.path] = source.content_sha256
        if previous_hashes.get(source.path) == source.content_sha256:
            unchanged += 1
            all_rows.extend(previous_records.get(source.path, []))
            continue
        if source.path in previous_hashes:
            updated += 1
        text = (repository_root / source.path).read_text(encoding="utf-8")
        for record in _chunk_records(source, text, chunk_settings, embedder):
            row = {
                "chunk_id": record.chunk_id,
                "source_path": record.source_path,
                "source_class": record.source_class,
                "start_line": record.start_line,
                "end_line": record.end_line,
                "text": record.text,
                "content_sha256": record.content_sha256,
                "embedding": list(record.embedding),
                "parser": record.parser,
                "embedding_model": record.embedding_model,
            }
            all_rows.append(row)

    removed = len(set(previous_hashes) - set(source_hashes))
    all_rows.sort(key=lambda row: (row["source_path"], row["start_line"], row["chunk_id"]))

    index_dir.mkdir(parents=True, exist_ok=True)
    with chunks_path.open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    manifest = {
        "policy_sha256": policy.digest(),
        "embedding_model": embedder.name,
        "embedding_dimensions": embedder.dimensions,
        "chunk_max_chars": chunk_settings.max_chars,
        "chunk_overlap_lines": chunk_settings.overlap_lines,
        "parser": PARSER_NAME,
        "source_hashes": dict(sorted(source_hashes.items())),
        "built_at_utc": now().isoformat(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return IndexReport(
        sources_indexed=len(sources),
        sources_unchanged=unchanged,
        sources_updated=updated,
        sources_removed=removed,
        chunk_count=len(all_rows),
    )


def load_index(index_dir: Path) -> LoadedIndex:
    manifest_path = index_dir / "manifest.json"
    chunks_path = index_dir / "chunks.jsonl"
    if not manifest_path.exists() or not chunks_path.exists():
        raise FileNotFoundError(f"index not found under {index_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[ChunkRecord] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        raw = json.loads(line)
        records.append(
            ChunkRecord(
                chunk_id=raw["chunk_id"],
                source_path=raw["source_path"],
                source_class=raw["source_class"],
                start_line=int(raw["start_line"]),
                end_line=int(raw["end_line"]),
                text=raw["text"],
                content_sha256=raw["content_sha256"],
                embedding=tuple(float(v) for v in raw["embedding"]),
                parser=raw["parser"],
                embedding_model=raw["embedding_model"],
            )
        )
    return LoadedIndex(
        policy_sha256=str(manifest["policy_sha256"]),
        embedding_model=str(manifest["embedding_model"]),
        built_at_utc=str(manifest["built_at_utc"]),
        chunks=tuple(records),
    )

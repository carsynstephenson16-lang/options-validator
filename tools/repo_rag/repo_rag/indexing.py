from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .chunking import ChunkSettings, chunk_text
from .config import CorpusPolicy
from .corpus import DiscoveryFailure, SourceFile, discover_sources_with_failures
from .providers import DeterministicHashEmbedding

PARSER_NAME = "line-chunker-v1"
INDEX_VERSION = 2
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_TICKER_RE = re.compile(r"(?:^|[/_.-])([A-Z]{1,5})(?=$|[/_.-])")
_HYPOTHESIS_RE = re.compile(r"(?:^|[/_.-])(H\d+)(?=$|[/_.-])", re.IGNORECASE)


class Fts5UnavailableError(RuntimeError):
    """Raised when the local SQLite build cannot provide the required FTS5 search."""


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
    failed_paths: tuple[str, ...] = ()


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


def classify_doc_type(path: str) -> str:
    """Re-derived options-validator metadata for the advisory FTS index."""
    lower = path.casefold()
    if lower.startswith("reports/"):
        return "backtest_run"
    if path in {
        "config.py",
        "options_researcher/config.py",
        "options_researcher/h7_scope.py",
        "options_researcher/h7_window_registration.py",
    } or "frozen" in lower:
        return "frozen_params"
    if lower.startswith("ledger/"):
        return "ledger"
    if "hypothesis" in lower or "/h7_" in lower or lower.endswith("h7.md"):
        return "hypothesis"
    if lower.startswith("research/") or lower.startswith("wiki/"):
        return "notebook"
    if path.endswith(".py") or path in {"README.md", "AGENTS.md", "CLAUDE.md"}:
        return "workflow"
    return "source"


def _as_of_date(path: str) -> str | None:
    match = _DATE_RE.search(Path(path).name)
    return match.group(0) if match else None


def _extract_ticker(path: str) -> str | None:
    for match in _TICKER_RE.finditer(path):
        candidate = match.group(1)
        if candidate != "H":
            return candidate
    return None


def _extract_hypothesis(path: str) -> str | None:
    match = _HYPOTHESIS_RE.search(path)
    return None if match is None else match.group(1).upper()


def _temporary_text_file(directory: Path, content: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        return Path(handle.name)


def _build_fts_index(index_dir: Path, rows: list[dict[str, object]], generation: str) -> Path:
    """Stage an isolated FTS5/BM25 index for publication with a generation marker."""
    temporary = index_dir / f"search.sqlite3.{generation}.tmp"
    connection = sqlite3.connect(temporary)
    try:
        connection.execute(
            "CREATE TABLE chunks ("
            "id INTEGER PRIMARY KEY, chunk_id TEXT NOT NULL, repo_path TEXT NOT NULL, "
            "source_tier TEXT NOT NULL, ticker TEXT, hypothesis TEXT, doc_type TEXT NOT NULL, "
            "filing_or_asof_date TEXT, locator TEXT NOT NULL, text TEXT NOT NULL)"
        )
        connection.execute("CREATE INDEX chunks_metadata ON chunks(source_tier, doc_type, ticker, hypothesis, filing_or_asof_date)")
        connection.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(text)")
        connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("BEGIN")
        connection.execute("INSERT INTO meta(key, value) VALUES ('generation', ?)", (generation,))
        for row in rows:
            path = str(row["source_path"])
            cursor = connection.execute(
                "INSERT INTO chunks(chunk_id, repo_path, source_tier, ticker, hypothesis, doc_type, filing_or_asof_date, locator, text) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["chunk_id"],
                    path,
                    row["source_class"],
                    _extract_ticker(path),
                    _extract_hypothesis(path),
                    classify_doc_type(path),
                    _as_of_date(path),
                    f"{path}:L{row['start_line']}-L{row['end_line']}",
                    row["text"],
                ),
            )
            connection.execute("INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)", (cursor.lastrowid, row["text"]))
        connection.execute("COMMIT")
    except sqlite3.OperationalError as exc:
        try:
            connection.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        if "fts5" in str(exc).casefold():
            raise Fts5UnavailableError("sqlite3 build lacks FTS5 support") from exc
        raise
    finally:
        connection.close()
    return temporary


def build_index(
    repository_root: Path,
    policy: CorpusPolicy,
    index_dir: Path,
    chunk_settings: ChunkSettings,
    tracked_paths: frozenset[str] | None = None,
    now: Callable[[], datetime] = _default_now,
) -> IndexReport:
    embedder = DeterministicHashEmbedding()
    sources, discovery_failures = discover_sources_with_failures(
        repository_root, policy, tracked_paths=tracked_paths
    )
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
    failures: list[DiscoveryFailure] = list(discovery_failures)
    for source in sources:
        try:
            text = (repository_root / source.path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(DiscoveryFailure(source.path, f"unreadable during indexing ({exc.__class__.__name__})"))
            continue
        source_hashes[source.path] = source.content_sha256
        if previous_hashes.get(source.path) == source.content_sha256:
            unchanged += 1
            all_rows.extend(previous_records.get(source.path, []))
            continue
        if source.path in previous_hashes:
            updated += 1
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

    failed_source_paths = {failure.path for failure in failures}
    for failed_path in sorted(failed_source_paths):
        if failed_path in previous_hashes and failed_path not in source_hashes:
            source_hashes[failed_path] = previous_hashes[failed_path]
            all_rows.extend(previous_records.get(failed_path, []))
    removed = len((set(previous_hashes) - set(source_hashes)) - failed_source_paths)
    all_rows.sort(key=lambda row: (row["source_path"], row["start_line"], row["chunk_id"]))

    index_dir.mkdir(parents=True, exist_ok=True)
    generation = uuid.uuid4().hex
    fts_temporary = _build_fts_index(index_dir, all_rows, generation)
    chunks_temporary = _temporary_text_file(
        index_dir, "".join(json.dumps(row, sort_keys=True) + "\n" for row in all_rows)
    )
    manifest = {
        "index_version": INDEX_VERSION,
        "generation": generation,
        "policy_sha256": policy.digest(),
        "embedding_model": embedder.name,
        "embedding_dimensions": embedder.dimensions,
        "chunk_max_chars": chunk_settings.max_chars,
        "chunk_overlap_lines": chunk_settings.overlap_lines,
        "parser": PARSER_NAME,
        "source_hashes": dict(sorted(source_hashes.items())),
        "built_at_utc": now().isoformat(),
    }
    manifest_temporary = _temporary_text_file(
        index_dir, json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    try:
        os.replace(chunks_temporary, chunks_path)
        os.replace(fts_temporary, index_dir / "search.sqlite3")
        os.replace(manifest_temporary, manifest_path)
    except OSError:
        for temporary in (chunks_temporary, fts_temporary, manifest_temporary):
            temporary.unlink(missing_ok=True)
        raise
    return IndexReport(
        sources_indexed=len(source_hashes),
        sources_unchanged=unchanged,
        sources_updated=updated,
        sources_removed=removed,
        chunk_count=len(all_rows),
        failed_paths=tuple(f"{failure.path}: {failure.reason}" for failure in failures),
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

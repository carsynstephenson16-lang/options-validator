from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkSettings:
    max_chars: int = 1200
    overlap_lines: int = 2

    def __post_init__(self) -> None:
        if self.max_chars < 50:
            raise ValueError("max_chars must be at least 50")
        if self.overlap_lines < 0:
            raise ValueError("overlap_lines must be non-negative")


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_path: str
    start_line: int
    end_line: int
    text: str

    @property
    def citation(self) -> str:
        return f"{self.source_path}:L{self.start_line}-L{self.end_line}"


def _make_chunk(source_path: str, start_line: int, end_line: int, text: str) -> Chunk:
    identity = f"{source_path}\0{start_line}\0{end_line}\0{text}".encode("utf-8")
    return Chunk(
        chunk_id=hashlib.sha256(identity).hexdigest()[:16],
        source_path=source_path,
        start_line=start_line,
        end_line=end_line,
        text=text,
    )


def _split_oversized_line(source_path: str, line_number: int, line: str, max_chars: int) -> list[Chunk]:
    pieces: list[Chunk] = []
    for offset in range(0, len(line), max_chars):
        piece = line[offset : offset + max_chars]
        pieces.append(_make_chunk(source_path, line_number, line_number, piece))
    return pieces


def chunk_text(source_path: str, text: str, settings: ChunkSettings) -> tuple[Chunk, ...]:
    stripped = text.rstrip("\n")
    if not stripped:
        return ()
    lines = stripped.split("\n")
    chunks: list[Chunk] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if len(line) > settings.max_chars:
            chunks.extend(_split_oversized_line(source_path, index + 1, line, settings.max_chars))
            index += 1
            continue
        start = index
        size = 0
        while index < len(lines) and len(lines[index]) <= settings.max_chars:
            candidate = size + len(lines[index]) + (1 if size else 0)
            if candidate > settings.max_chars:
                break
            size = candidate
            index += 1
        body = "\n".join(lines[start:index])
        chunks.append(_make_chunk(source_path, start + 1, index, body))
        if index < len(lines) and len(lines[index]) <= settings.max_chars and settings.overlap_lines:
            index = max(start + 1, index - settings.overlap_lines)
    return tuple(chunks)

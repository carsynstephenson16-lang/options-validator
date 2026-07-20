from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .indexing import load_index
from .providers import ExtractiveGenerator, RetrievedContext
from .retrieval import RETRIEVAL_MODE, RetrievalSettings, retrieve

DEFAULT_MAX_CONTEXT_CHARS = 4000
_CITATION_PATTERN = re.compile(r"\[([^\[\]]+:L\d+-L\d+)\]")


@dataclass(frozen=True)
class QueryResult:
    outcome: str
    answer: str
    citations: tuple[str, ...]
    citations_verified: bool
    retrieved: tuple[tuple[str, float], ...]
    request_id: str


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


def _append_event(index_dir: Path, payload: dict) -> None:
    events_path = index_dir / "events.jsonl"
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def answer_query(
    query: str,
    index_dir: Path,
    settings: RetrievalSettings,
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    now: Callable[[], datetime] = _default_now,
) -> QueryResult:
    started = time.perf_counter()
    query_sha256 = hashlib.sha256(query.encode("utf-8")).hexdigest()
    request_id = query_sha256[:12]

    def finish(outcome: str, answer: str, citations: tuple[str, ...],
               verified: bool, retrieved: tuple[tuple[str, float], ...]) -> QueryResult:
        if index_dir.is_dir():
            _append_event(
                index_dir,
                {
                    "request_id": request_id,
                    "query_sha256": query_sha256,
                    "outcome": outcome,
                    "retrieved": [
                        {"chunk_id": chunk_id, "score": round(score, 6)}
                        for chunk_id, score in retrieved
                    ],
                    "retrieval_mode": RETRIEVAL_MODE,
                    "settings": {
                        "top_k": settings.top_k,
                        "min_score": settings.min_score,
                        "vector_weight": settings.vector_weight,
                        "lexical_weight": settings.lexical_weight,
                        "source_classes": list(settings.source_classes),
                        "max_context_chars": max_context_chars,
                    },
                    "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
                    "timestamp_utc": now().isoformat(),
                },
            )
        return QueryResult(
            outcome=outcome,
            answer=answer,
            citations=citations,
            citations_verified=verified,
            retrieved=retrieved,
            request_id=request_id,
        )

    if not query.strip():
        return finish(
            outcome="EMPTY_QUERY", answer="Query is empty.", citations=(),
            verified=False, retrieved=(),
        )
    try:
        index = load_index(index_dir)
    except FileNotFoundError:
        return finish(
            outcome="INDEX_MISSING",
            answer="No index found. Run: python3 -m repo_rag ingest",
            citations=(),
            verified=False,
            retrieved=(),
        )
    except (json.JSONDecodeError, KeyError, ValueError, UnicodeDecodeError):
        return finish(
            outcome="INDEX_CORRUPT",
            answer=(
                "Index is unreadable. Delete the .index directory and run: "
                "python3 -m repo_rag ingest"
            ),
            citations=(),
            verified=False,
            retrieved=(),
        )

    hits = retrieve(query, index.chunks, settings)
    retrieved = tuple((hit.record.chunk_id, hit.score) for hit in hits)
    if not hits:
        return finish(
            outcome="INSUFFICIENT_EVIDENCE",
            answer="Insufficient repository evidence.",
            citations=(),
            verified=True,
            retrieved=retrieved,
        )

    budgeted = []
    used = 0
    for hit in hits:
        cost = len(hit.record.text)
        if budgeted and used + cost > max_context_chars:
            break
        budgeted.append(hit)
        used += cost

    contexts = [
        RetrievedContext(text=hit.record.text, citation=hit.record.citation)
        for hit in budgeted
    ]
    answer = ExtractiveGenerator().generate(query, contexts)
    cited = tuple(dict.fromkeys(_CITATION_PATTERN.findall(answer)))
    allowed = {hit.record.citation for hit in budgeted}
    verified = bool(cited) and all(citation in allowed for citation in cited)
    if not verified:
        return finish(
            outcome="CITATION_MISMATCH", answer=answer, citations=cited,
            verified=False, retrieved=retrieved,
        )
    return finish(
        outcome="ANSWERED", answer=answer, citations=cited,
        verified=True, retrieved=retrieved,
    )

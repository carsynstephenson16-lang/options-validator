from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .chunking import ChunkSettings
from .config import load_policy
from .indexing import build_index
from .pipeline import DEFAULT_MAX_CONTEXT_CHARS, answer_query
from .retrieval import RetrievalSettings
from .status import build_status


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_index_dir() -> Path:
    return _project_root() / ".index"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only repository RAG")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="show machine-readable application status")
    status.add_argument("--policy", type=Path, default=_project_root() / "policy.json")
    status.add_argument("--repo-root", type=Path, default=_repository_root())
    status.add_argument("--index-dir", type=Path, default=_default_index_dir())

    ingest = subparsers.add_parser("ingest", help="build or refresh the offline index")
    ingest.add_argument("--policy", type=Path, default=_project_root() / "policy.json")
    ingest.add_argument("--repo-root", type=Path, default=_repository_root())
    ingest.add_argument("--index-dir", type=Path, default=_default_index_dir())
    ingest.add_argument("--max-chars", type=int, default=ChunkSettings().max_chars)
    ingest.add_argument("--overlap-lines", type=int, default=ChunkSettings().overlap_lines)
    ingest.add_argument(
        "--no-git",
        action="store_true",
        help="treat every file under the corpus roots as tracked (tests only)",
    )

    query = subparsers.add_parser("query", help="ask a grounded question against the index")
    query.add_argument("question")
    query.add_argument("--index-dir", type=Path, default=_default_index_dir())
    query.add_argument("--top-k", type=int, default=RetrievalSettings().top_k)
    query.add_argument("--min-score", type=float, default=RetrievalSettings().min_score)
    query.add_argument("--source-class", action="append", default=None)
    query.add_argument("--max-context-chars", type=int, default=DEFAULT_MAX_CONTEXT_CHARS)
    return parser


def _walk_all_files(repo_root: Path) -> frozenset[str]:
    return frozenset(
        str(path.relative_to(repo_root))
        for path in repo_root.rglob("*")
        if path.is_file()
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "status":
        policy = load_policy(args.policy)
        report = build_status(args.repo_root, policy, index_dir=args.index_dir)
        print(json.dumps(report.to_mapping(), indent=2, sort_keys=True))
        return 0 if report.status.startswith("READY") else 2
    if args.command == "ingest":
        policy = load_policy(args.policy)
        tracked = _walk_all_files(args.repo_root) if args.no_git else None
        report = build_index(
            repository_root=args.repo_root,
            policy=policy,
            index_dir=args.index_dir,
            chunk_settings=ChunkSettings(
                max_chars=args.max_chars, overlap_lines=args.overlap_lines
            ),
            tracked_paths=tracked,
        )
        print(json.dumps(report.__dict__, indent=2, sort_keys=True))
        return 0
    if args.command == "query":
        settings = RetrievalSettings(
            top_k=args.top_k,
            min_score=args.min_score,
            source_classes=tuple(args.source_class or ()),
        )
        result = answer_query(
            query=args.question,
            index_dir=args.index_dir,
            settings=settings,
            max_context_chars=args.max_context_chars,
        )
        payload = {
            "outcome": result.outcome,
            "answer": result.answer,
            "citations": list(result.citations),
            "citations_verified": result.citations_verified,
            "retrieved": [
                {"chunk_id": chunk_id, "score": round(score, 6)}
                for chunk_id, score in result.retrieved
            ],
            "request_id": result.request_id,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        codes = {"ANSWERED": 0, "INDEX_MISSING": 2, "INSUFFICIENT_EVIDENCE": 3}
        return codes.get(result.outcome, 4)
    raise AssertionError(f"unhandled command: {args.command}")

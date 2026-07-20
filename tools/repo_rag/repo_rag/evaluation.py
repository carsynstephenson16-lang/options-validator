from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from .pipeline import answer_query
from .retrieval import RetrievalSettings


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    query: str
    kind: str
    expected_source_paths: tuple[str, ...]
    forbidden_source_paths: tuple[str, ...]


@dataclass(frozen=True)
class CaseFailure:
    case_id: str
    reason: str


@dataclass(frozen=True)
class EvaluationReport:
    total: int
    passed: int
    hit_rate: float
    failures: tuple[CaseFailure, ...]

    def to_mapping(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "hit_rate": self.hit_rate,
            "failures": [
                {"case_id": failure.case_id, "reason": failure.reason}
                for failure in self.failures
            ],
        }


def load_golden_set(path: Path) -> tuple[GoldenCase, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases = []
    for entry in raw["cases"]:
        kind = str(entry["kind"])
        if kind not in {"positive", "abstain"}:
            raise ValueError(f"unknown case kind: {kind}")
        cases.append(
            GoldenCase(
                case_id=str(entry["case_id"]),
                query=str(entry["query"]),
                kind=kind,
                expected_source_paths=tuple(entry.get("expected_source_paths", ())),
                forbidden_source_paths=tuple(entry.get("forbidden_source_paths", ())),
            )
        )
    return tuple(cases)


def _citation_source(citation: str) -> str:
    return citation.rsplit(":", 1)[0]


def evaluate(
    golden_set: tuple[GoldenCase, ...],
    index_dir: Path,
    settings: RetrievalSettings,
    now: Callable[[], datetime] | None = None,
) -> EvaluationReport:
    failures: list[CaseFailure] = []
    for case in golden_set:
        kwargs = {"query": case.query, "index_dir": index_dir, "settings": settings}
        if now is not None:
            kwargs["now"] = now
        result = answer_query(**kwargs)
        cited_sources = {_citation_source(citation) for citation in result.citations}
        if case.kind == "abstain":
            if result.outcome != "INSUFFICIENT_EVIDENCE":
                failures.append(
                    CaseFailure(case.case_id, f"expected abstention, got {result.outcome}")
                )
            continue
        if result.outcome != "ANSWERED":
            failures.append(CaseFailure(case.case_id, f"expected answer, got {result.outcome}"))
            continue
        if case.expected_source_paths and not (
            cited_sources & set(case.expected_source_paths)
        ):
            failures.append(
                CaseFailure(
                    case.case_id,
                    f"no expected source cited; cited {sorted(cited_sources)}",
                )
            )
            continue
        forbidden_hit = cited_sources & set(case.forbidden_source_paths)
        if forbidden_hit:
            failures.append(
                CaseFailure(case.case_id, f"forbidden source cited: {sorted(forbidden_hit)}")
            )
    passed = len(golden_set) - len(failures)
    hit_rate = passed / len(golden_set) if golden_set else 0.0
    return EvaluationReport(
        total=len(golden_set),
        passed=passed,
        hit_rate=hit_rate,
        failures=tuple(failures),
    )

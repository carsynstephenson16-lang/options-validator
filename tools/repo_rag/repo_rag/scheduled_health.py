"""Pure retrieval search plus scheduled corpus/evaluation health reporting."""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .chunking import ChunkSettings
from .config import CorpusPolicy
from .indexing import ChunkRecord, build_index, load_index
from .retrieval import RetrievalSettings, retrieve
from .writer import Writer

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_DOC_TYPES = frozenset(
    {"hypothesis", "backtest_run", "ledger", "frozen_params", "notebook", "workflow", "source"}
)
_HISTORY_COLUMNS = (
    "run_at_utc",
    "policy_sha256",
    "chunk_count",
    "golden_cases",
    "k",
    "positive_total",
    "negative_total",
    "hit_at_k",
    "mrr",
    "abstention_correct",
    "false_hit_rate",
    "latency_ms_p50",
    "latency_ms_p95",
    "verdict",
)
_DOCTRINE_PATHS = frozenset({"AGENTS.md", "CLAUDE.md", "README.md"})


@dataclass(frozen=True)
class SearchFilters:
    ticker: str | None = None
    hypothesis: str | None = None
    source_tier: str | None = None
    doc_type: str | None = None
    since: str | None = None


@dataclass(frozen=True)
class SearchHit:
    repo_path: str
    source_tier: str
    locator: str
    filing_or_asof_date: str | None
    doc_type: str
    snippet: str
    score: float


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    question: str
    expect_paths: tuple[str, ...]
    expect_any: bool
    note: str

    @property
    def negative(self) -> bool:
        return not self.expect_paths


@dataclass(frozen=True)
class EvaluationFailure:
    case_id: str
    question: str
    returned_paths: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class EvaluationReport:
    positive_total: int
    negative_total: int
    hit_at_k: float
    mrr: float
    abstention_correct: float
    false_hit_rate: float
    latency_ms_p50: float
    latency_ms_p95: float
    failures: tuple[EvaluationFailure, ...]

    @property
    def total(self) -> int:
        return self.positive_total + self.negative_total

    def to_mapping(self) -> dict[str, object]:
        return {
            "total": self.total,
            "positive_total": self.positive_total,
            "negative_total": self.negative_total,
            "hit_at_k": self.hit_at_k,
            "mrr": self.mrr,
            "abstention_correct": self.abstention_correct,
            "false_hit_rate": self.false_hit_rate,
            "latency_ms_p50": self.latency_ms_p50,
            "latency_ms_p95": self.latency_ms_p95,
            "failures": [
                {
                    "id": failure.case_id,
                    "question": failure.question,
                    "returned_paths": list(failure.returned_paths),
                    "reason": failure.reason,
                }
                for failure in self.failures
            ],
        }


@dataclass(frozen=True)
class RegressionVerdict:
    regressed: bool
    prior_hit_at_k_median: float | None
    prior_false_hit_rate_median: float | None
    reasons: tuple[str, ...]


def classify_doc_type(path: str) -> str:
    lower = path.casefold()
    if lower.startswith("ledger/"):
        return "ledger"
    if "hypothesis" in lower or "/h7_" in lower or lower.endswith("h7.md"):
        return "hypothesis"
    if lower.startswith("reports/"):
        return "backtest_run"
    if lower.startswith("research/"):
        return "notebook"
    if path in {"config.py", "options_researcher/config.py"} or "frozen" in lower:
        return "frozen_params"
    if path.endswith(".py") or path in {"README.md", "AGENTS.md", "CLAUDE.md"}:
        return "workflow"
    return "source"


def _as_of_date(path: str) -> str | None:
    match = _DATE_RE.search(Path(path).name)
    return match.group(0) if match else None


def _matches(record: ChunkRecord, filters: SearchFilters) -> bool:
    if filters.source_tier is not None and record.source_class != filters.source_tier:
        return False
    if filters.doc_type is not None and classify_doc_type(record.source_path) != filters.doc_type:
        return False
    if filters.ticker is not None and f"/{filters.ticker.upper()}/" not in f"/{record.source_path.upper()}/":
        return False
    if filters.hypothesis is not None and filters.hypothesis.casefold() not in record.source_path.casefold():
        return False
    if filters.since is not None:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", filters.since):
            raise ValueError("since must use YYYY-MM-DD")
        as_of = _as_of_date(record.source_path)
        if as_of is None or as_of < filters.since:
            return False
    return True


def _snippet(text: str, limit: int = 320) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def search(index_dir: Path, query: str, limit: int = 5, filters: SearchFilters | None = None) -> tuple[SearchHit, ...]:
    """Return advisory passages only; no generator or trading decision path."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    filters = filters or SearchFilters()
    index = load_index(index_dir)
    candidates = tuple(record for record in index.chunks if _matches(record, filters))
    settings = RetrievalSettings(top_k=limit)
    hits = retrieve(query, candidates, settings)
    return tuple(
        SearchHit(
            repo_path=hit.record.source_path,
            source_tier=hit.record.source_class,
            locator=hit.record.citation,
            filing_or_asof_date=_as_of_date(hit.record.source_path),
            doc_type=classify_doc_type(hit.record.source_path),
            snippet=_snippet(hit.record.text),
            score=hit.score,
        )
        for hit in hits
    )


def load_golden_set(path: Path) -> tuple[GoldenCase, ...]:
    cases: list[GoldenCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"golden set line {line_number}: invalid JSON") from exc
        required = {"id", "question", "expect_paths", "expect_any", "note"}
        if not isinstance(raw, dict) or required - raw.keys():
            raise ValueError(f"golden set line {line_number}: invalid schema")
        case_id = str(raw["id"])
        paths = tuple(str(item) for item in raw["expect_paths"])
        expect_any = raw["expect_any"]
        if not case_id or case_id in seen or not str(raw["question"]).strip():
            raise ValueError(f"golden set line {line_number}: invalid id or question")
        if not isinstance(expect_any, bool) or (not paths and not expect_any):
            raise ValueError(f"golden set line {line_number}: invalid control semantics")
        seen.add(case_id)
        cases.append(GoldenCase(case_id, str(raw["question"]), paths, expect_any, str(raw["note"])))
    if not cases:
        raise ValueError("golden set is empty")
    return tuple(cases)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(1, math.ceil(percentile * len(ordered))) - 1]


def evaluate(golden_set: Iterable[GoldenCase], index_dir: Path, k: int = 5) -> EvaluationReport:
    cases = tuple(golden_set)
    positives = [case for case in cases if not case.negative]
    negatives = [case for case in cases if case.negative]
    hits = abstentions = false_hits = 0
    reciprocal_rank_sum = 0.0
    latencies: list[float] = []
    failures: list[EvaluationFailure] = []
    for case in cases:
        started = time.perf_counter()
        results = search(index_dir, case.question, limit=k)
        latencies.append((time.perf_counter() - started) * 1000.0)
        paths = tuple(result.repo_path for result in results)
        if case.negative:
            if paths:
                false_hits += 1
                failures.append(EvaluationFailure(case.case_id, case.question, paths, "expected abstention"))
            else:
                abstentions += 1
            continue
        expected = set(case.expect_paths)
        present = expected & set(paths)
        passed = bool(present) if case.expect_any else expected <= set(paths)
        rank = next((number + 1 for number, path in enumerate(paths) if path in expected), None)
        if passed:
            hits += 1
            if rank is not None:
                reciprocal_rank_sum += 1.0 / rank
        else:
            failures.append(EvaluationFailure(case.case_id, case.question, paths, "expected path absent"))
    return EvaluationReport(
        len(positives),
        len(negatives),
        hits / len(positives) if positives else 0.0,
        reciprocal_rank_sum / len(positives) if positives else 0.0,
        abstentions / len(negatives) if negatives else 1.0,
        false_hits / len(negatives) if negatives else 0.0,
        _percentile(latencies, 0.50),
        _percentile(latencies, 0.95),
        tuple(failures),
    )


def _read_history(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def regression_verdict(report: EvaluationReport, prior_rows: Iterable[dict[str, str]]) -> RegressionVerdict:
    prior = list(prior_rows)[-4:]
    if not prior:
        return RegressionVerdict(False, None, None, ())
    hit_median = statistics.median(float(row["hit_at_k"]) for row in prior)
    false_median = statistics.median(float(row["false_hit_rate"]) for row in prior)
    reasons: list[str] = []
    if report.hit_at_k < hit_median - 0.05:
        reasons.append("hit@k fell by more than 5 percentage points below the trailing median")
    if report.false_hit_rate > false_median:
        reasons.append("false-hit rate rose above the trailing median")
    return RegressionVerdict(bool(reasons), hit_median, false_median, tuple(reasons))


def _append_history(
    path: Path,
    report: EvaluationReport,
    policy: CorpusPolicy,
    chunks: int,
    verdict: str,
    now: datetime,
    k: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    row = {
        "run_at_utc": now.astimezone(timezone.utc).isoformat(),
        "policy_sha256": policy.digest(),
        "chunk_count": str(chunks),
        "golden_cases": str(report.total),
        "k": str(k),
        "positive_total": str(report.positive_total),
        "negative_total": str(report.negative_total),
        "hit_at_k": f"{report.hit_at_k:.6f}",
        "mrr": f"{report.mrr:.6f}",
        "abstention_correct": f"{report.abstention_correct:.6f}",
        "false_hit_rate": f"{report.false_hit_rate:.6f}",
        "latency_ms_p50": f"{report.latency_ms_p50:.3f}",
        "latency_ms_p95": f"{report.latency_ms_p95:.3f}",
        "verdict": verdict,
    }
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_HISTORY_COLUMNS)
        if needs_header:
            writer.writeheader()
        writer.writerow(row)


def record_evaluation_history(
    repository_root: Path,
    application_root: Path,
    report: EvaluationReport,
    policy: CorpusPolicy,
    index_dir: Path,
    now: datetime | None = None,
    k: int = 5,
) -> RegressionVerdict:
    """Append one evaluation observation without changing retrieval settings."""
    run_at = now or datetime.now(timezone.utc)
    history = application_root / "eval" / "history.csv"
    verdict = regression_verdict(report, _read_history(history))
    _append_history(
        history,
        report,
        policy,
        len(load_index(index_dir).chunks),
        "REGRESSED" if verdict.regressed else "OK",
        run_at,
        k,
    )
    Writer(repository_root, application_root).journal_evaluation_history(trigger="evaluation")
    return verdict


def _manifest_hashes(index_dir: Path) -> dict[str, str]:
    manifest = index_dir / "manifest.json"
    if not manifest.exists():
        return {}
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    return {str(path): str(digest) for path, digest in dict(raw.get("source_hashes", {})).items()}


def _render_report(now: datetime, delta: dict[str, list[str]], report: EvaluationReport, verdict: RegressionVerdict) -> str:
    prior = "n/a" if verdict.prior_hit_at_k_median is None else f"{verdict.prior_hit_at_k_median:.2f}"
    failed = [
        f"- {item.case_id}: {item.question} — returned {', '.join(item.returned_paths) or 'nothing'}"
        for item in report.failures
    ] or ["- No regressed questions."]
    proposals = [f"- Investigate regression: {reason}." for reason in verdict.reasons]
    if not proposals:
        proposals = ["- No changes proposed. Continue observing; nothing was applied."]
    lines = [f"# RAG Health — {now.date().isoformat()}", "", "## Verdict", f"Index: OK | Evaluation: {'REGRESSED' if verdict.regressed else 'OK'}", "", "## Corpus change since prior run"]
    for label, key in (("Added", "added"), ("Changed", "changed"), ("Removed", "removed"), ("Failed to index", "failed")):
        lines.append(f"{label}: {len(delta[key])} files")
        lines.extend(
            f"- {path}"
            for path in sorted(delta[key], key=lambda path: (path not in _DOCTRINE_PATHS, path))
        )
        if not delta[key]:
            lines.append("- None")
    lines.extend([
        "",
        "## Retrieval evaluation",
        f"hit@5 {report.hit_at_k:.2f} (prior median {prior}) | MRR {report.mrr:.2f} | abstention {round(report.abstention_correct * report.negative_total)}/{report.negative_total} | false hits {round(report.false_hit_rate * report.negative_total)} | latency p50/p95 {report.latency_ms_p50:.1f}/{report.latency_ms_p95:.1f} ms",
        *failed,
        "",
        "## Staleness",
        "- Not applicable: this repository has no macro/sector-cycle freshness contract.",
        "",
        "## Proposals — REQUIRE YOUR APPROVAL, NOTHING APPLIED",
        *proposals,
        "",
    ])
    return "\n".join(lines)


def rotate_artifacts(application_root: Path, keep: int = 12) -> None:
    """Retain only app-owned report and launcher-log history."""
    if keep < 1:
        raise ValueError("keep must be at least 1")
    root = application_root.resolve()
    for directory_name, pattern in (("reports", "rag_health_*.md"), ("logs", "repo_rag_health_*.log")):
        directory = (root / directory_name).resolve()
        if not directory.is_relative_to(root) or not directory.is_dir():
            continue
        artifacts = sorted(
            (path for path in directory.glob(pattern) if path.is_file()),
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        for obsolete in artifacts[keep:]:
            obsolete.unlink()


def run_health(
    *, repository_root: Path, application_root: Path, policy: CorpusPolicy, index_dir: Path, golden_path: Path, now: datetime | None = None
) -> tuple[Path, EvaluationReport, RegressionVerdict]:
    run_at = now or datetime.now(timezone.utc)
    before = _manifest_hashes(index_dir)
    build_index(repository_root, policy, index_dir, ChunkSettings())
    after = _manifest_hashes(index_dir)
    delta = {
        "added": sorted(set(after) - set(before)),
        "changed": sorted(path for path in after if path in before and after[path] != before[path]),
        "removed": sorted(set(before) - set(after)),
        "failed": [],
    }
    report = evaluate(load_golden_set(golden_path), index_dir)
    verdict = record_evaluation_history(
        repository_root, application_root, report, policy, index_dir, run_at, k=5
    )
    writer = Writer(repository_root, application_root)
    report_path = writer.write_report(
        f"rag_health_{run_at.date().isoformat()}",
        _render_report(run_at, delta, report, verdict),
        trigger="scheduled health",
        chunk_ids=(),
    )
    rotate_artifacts(application_root)
    return report_path, report, verdict

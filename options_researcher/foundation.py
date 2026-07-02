"""Filesystem manifest for the local options researcher foundation.

The foundation is deliberately small and offline. It documents the project
scaffold that helps capture hypotheses, source notes, and review checklists
without introducing paid APIs, broker execution, or live-trading behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FoundationPath:
    """A required repository path and the reason it exists."""

    path: str
    purpose: str


FORBIDDEN_CAPABILITIES = (
    "paid_api_integration",
    "live_trading",
    "broker_order_placement",
    "hardcoded_secrets",
)

REQUIRED_DIRECTORIES = (
    FoundationPath("options_researcher", "importable local researcher package"),
    FoundationPath("scripts", "offline helper scripts"),
    FoundationPath(".obsidian/templates", "tracked Obsidian templates"),
    FoundationPath("docs/notebooklm/templates", "NotebookLM source and prompt templates"),
    FoundationPath("docs/research-notes", "local generated research notes"),
)

REQUIRED_FILES = (
    FoundationPath("AGENTS.md", "repository operating instructions"),
    FoundationPath("README.md", "project overview and commands"),
    FoundationPath("scripts/validate_foundation.py", "offline scaffold validator"),
    FoundationPath("scripts/new_research_note.py", "offline note generator"),
    FoundationPath(".obsidian/templates/research-hypothesis.md", "hypothesis note template"),
    FoundationPath(".obsidian/templates/experiment-log.md", "experiment log template"),
    FoundationPath(".obsidian/templates/data-source-audit.md", "data source audit template"),
    FoundationPath(".obsidian/templates/oos-reveal-checklist.md", "OOS reveal checklist"),
    FoundationPath("docs/notebooklm/templates/source-upload-checklist.md", "NotebookLM intake checklist"),
    FoundationPath("docs/notebooklm/templates/research-brief.md", "NotebookLM brief template"),
    FoundationPath("docs/notebooklm/templates/evidence-audit.md", "NotebookLM evidence audit"),
    FoundationPath("docs/notebooklm/templates/question-bank.md", "NotebookLM question bank"),
)


def project_root(start: Path | None = None) -> Path:
    """Return the repository root containing pyproject.toml."""

    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate

    raise FileNotFoundError("could not find repository root from foundation package")


def _exists(root: Path, item: FoundationPath) -> bool:
    return (root / item.path).exists()


def missing_required_paths(root: Path | None = None) -> list[str]:
    """Return missing required scaffold paths relative to the repository root."""

    repo = project_root() if root is None else Path(root)
    expected = (*REQUIRED_DIRECTORIES, *REQUIRED_FILES)
    return [item.path for item in expected if not _exists(repo, item)]


def foundation_summary(root: Path | None = None) -> dict[str, list[str]]:
    """Return present/missing path groups for scripts and tests."""

    repo = project_root() if root is None else Path(root)
    expected = (*REQUIRED_DIRECTORIES, *REQUIRED_FILES)
    present = [item.path for item in expected if _exists(repo, item)]
    missing = [item.path for item in expected if not _exists(repo, item)]
    return {"present": present, "missing": missing}

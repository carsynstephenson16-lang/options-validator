# Five-Source Checklist Standards Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the canonical, source-faithful catalog and deterministic snapshot that the four portfolio repositories will consume through local profiles.

**Architecture:** A standalone Python 3.12 repository acquires five allowlisted public sources, binds each review to a source hash, normalizes enumerated and narrative controls, validates crosswalks, and publishes a deterministic JSON snapshot. The four portfolio repositories do not import this code; they receive only a versioned, hash-pinned data snapshot after Phase 0 is complete.

**Tech Stack:** Python 3.12 standard library, `unittest`, JSON/JSONL, SHA-256, Git, and uv for environment orchestration only.

## Global Constraints

- Repository path: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards`.
- Python requirement: `>=3.12,<3.13`.
- Runtime dependencies: none.
- Source refresh may access only the five exact allowlisted public URLs in the approved design.
- Normal verification, tests, catalog publication, and project audits must be offline.
- Store source URLs, hashes, locators, reviewer paraphrases, and review receipts; do not commit full copyrighted source documents.
- RML and MLTS are enumerated sources and require exact count reconciliation.
- DVM, HTD, and EYT are narrative sources and require complete section-disposition ledgers.
- EYT remains practitioner guidance and cannot override primary research or repository policy.
- Published item IDs are stable and never reassigned.
- Published catalog records are append-only; semantic changes supersede rather than silently rewrite.
- JSON is data only: no `eval`, dynamic import, plugin discovery, or shell-string execution.
- Generated output is ordered and serialized with UTF-8, `sort_keys=True`, compact separators, and a final newline.
- Every meaningful implementation step follows red-green-refactor and ends in a focused commit.

---

## File map

### Repository and packaging

- `AGENTS.md`: local safety, source-authority, and TDD instructions.
- `README.md`: purpose, commands, non-goals, and publication workflow.
- `pyproject.toml`: Python floor, package metadata, and no dependencies.
- `.gitignore`: source cache, bytecode, test cache, and generated candidate files.

### Runtime package

- `src/portfolio_reliability/__init__.py`: public version.
- `src/portfolio_reliability/model.py`: typed immutable source, item, locator, crosswalk, and receipt records.
- `src/portfolio_reliability/jsonio.py`: strict JSON/JSONL loading and deterministic serialization.
- `src/portfolio_reliability/source_registry.py`: exact source definitions and allowlist.
- `src/portfolio_reliability/acquire.py`: explicit network fetch and SHA-256 receipt generation.
- `src/portfolio_reliability/enumerated.py`: source-specific RML heading extraction and reviewed MLTS enumeration loading.
- `src/portfolio_reliability/narrative.py`: section-disposition and derived-control validation.
- `src/portfolio_reliability/catalog.py`: catalog invariants, crosswalk resolution, and source-native score metadata.
- `src/portfolio_reliability/snapshot.py`: deterministic snapshot assembly and digest publication.
- `src/portfolio_reliability/cli.py`: `fetch`, `verify`, and `publish` command dispatch.

### Reviewed data

- `catalog/source-definitions.json`: exact static source authority and URL definitions.
- `catalog/sources.json`: reviewed retrieval identities and hashes.
- `catalog/items.jsonl`: normalized published catalog items.
- `catalog/crosswalks.json`: deduplication groups and semantic differences.
- `catalog/catalog-manifest.json`: version, counts, hashes, and review receipt.
- `reviews/rml-controls.json`: reviewer paraphrase and locator for every extracted RML ordinal.
- `reviews/mlts-controls.json`: 28 reviewed MLTS controls in four seven-item categories.
- `reviews/narrative-section-coverage.json`: complete DVM, HTD, and EYT section disposition.
- `reviews/source-review-receipts.jsonl`: append-only review receipts.

### Schemas and publication

- `schemas/source.schema.json`: documented source manifest contract.
- `schemas/item.schema.json`: documented normalized item contract.
- `schemas/profile.schema.json`: downstream profile contract.
- `schemas/receipt.schema.json`: command and review receipt contract.
- `schemas/report.schema.json`: downstream report contract.
- `vendor/portfolio-reliability-catalog-v1.json`: deterministic published snapshot.
- `vendor/portfolio-reliability-catalog-v1.sha256`: digest plus newline.

### Tests and fixtures

- `tests/test_jsonio.py`: strict parsing and deterministic bytes.
- `tests/test_source_registry.py`: five-source allowlist and authority rules.
- `tests/test_acquire.py`: redirect, media type, size, timeout, and receipt behavior.
- `tests/test_enumerated.py`: count reconciliation and ordinal stability.
- `tests/test_narrative.py`: complete section dispositions and derived-control provenance.
- `tests/test_catalog.py`: item IDs, locators, crosswalks, scoring metadata, and append-only rules.
- `tests/test_snapshot.py`: deterministic publication and hash verification.
- `tests/test_cli.py`: offline verify/publish and explicit network fetch boundaries.
- `tests/fixtures/`: small synthetic HTML, manifests, controls, and invalid records; no third-party paper copies.

## Task 1: Create the standalone repository and deterministic JSON foundation

**Files:**
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/AGENTS.md`
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/README.md`
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/pyproject.toml`
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/.gitignore`
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/src/portfolio_reliability/__init__.py`
- Create: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/src/portfolio_reliability/jsonio.py`
- Test: `/Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards/tests/test_jsonio.py`

**Interfaces:**
- Consumes: no earlier implementation.
- Produces: `load_json(path: Path) -> object`, `load_jsonl(path: Path) -> tuple[dict[str, object], ...]`, `canonical_json_bytes(value: object) -> bytes`, and `write_bytes_atomic(path: Path, payload: bytes) -> None`.

- [ ] **Step 1: Initialize an isolated Git repository**

Run:

```bash
mkdir -p /Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards
cd /Users/carsynstephenson/Documents/Codex/portfolio-reliability-standards
git init -b main
```

Expected: a new repository whose root is exactly the declared standards path.

- [ ] **Step 2: Write the failing deterministic-JSON tests**

Create `tests/test_jsonio.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from portfolio_reliability.jsonio import (
    canonical_json_bytes,
    load_json,
    load_jsonl,
    write_bytes_atomic,
)


class JsonIoTests(unittest.TestCase):
    def test_canonical_json_is_sorted_compact_utf8_and_newline_terminated(self) -> None:
        value = {"z": 1, "a": "caf\u00e9"}
        self.assertEqual(canonical_json_bytes(value), b'{"a":"caf\xc3\xa9","z":1}\n')

    def test_load_json_rejects_trailing_content(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"ok": true}\n{"extra": true}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "single JSON value"):
                load_json(path)

    def test_load_jsonl_rejects_non_object_lines(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text('{"ok": true}\n[]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "line 2 must be an object"):
                load_jsonl(path)

    def test_atomic_write_replaces_complete_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            write_bytes_atomic(path, b"first\n")
            write_bytes_atomic(path, b"second\n")
            self.assertEqual(path.read_bytes(), b"second\n")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the test to prove the module is missing**

Run:

```bash
uv run python -m unittest tests.test_jsonio -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'portfolio_reliability'`.

- [ ] **Step 4: Add package metadata and deterministic JSON implementation**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "portfolio-reliability-standards"
version = "0.1.0"
description = "Offline standards catalog for portfolio research reliability"
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = []

[project.scripts]
portfolio-reliability = "portfolio_reliability.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/portfolio_reliability"]
```

Create `src/portfolio_reliability/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/portfolio_reliability/jsonio.py`:

```python
from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def canonical_json_bytes(value: object) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def load_json(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    first_value_index = len(text) - len(text.lstrip())
    try:
        value, end = decoder.raw_decode(text, idx=first_value_index)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if text[end:].strip():
        raise ValueError(f"{path}: expected a single JSON value")
    return value


def load_jsonl(path: Path) -> tuple[dict[str, object], ...]:
    records: list[dict[str, object]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}: line {line_number} must be an object")
        records.append(value)
    return tuple(records)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
```

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.source-cache/
.candidates/
dist/
```

Create `AGENTS.md` with the Global Constraints from this plan and create
`README.md` with the objective, non-goals, repository layout, and the commands
`portfolio-reliability fetch`, `portfolio-reliability verify`, and
`portfolio-reliability publish`.

- [ ] **Step 5: Run the focused and complete tests**

Run:

```bash
uv run python -m unittest tests.test_jsonio -v
uv run python -m unittest discover -s tests -v
```

Expected: 4 focused tests pass and the complete current suite passes.

- [ ] **Step 6: Commit the deterministic foundation**

Run:

```bash
git add AGENTS.md README.md pyproject.toml .gitignore src tests
git commit -m "build: create reliability standards foundation"
```

Expected: one commit containing only the new repository foundation.

## Task 2: Define immutable records and the five-source allowlist

**Files:**
- Create: `src/portfolio_reliability/model.py`
- Create: `src/portfolio_reliability/source_registry.py`
- Create: `catalog/source-definitions.json`
- Create: `schemas/source.schema.json`
- Test: `tests/test_source_registry.py`

**Interfaces:**
- Consumes: `load_json(path)` from Task 1.
- Produces: `SourceDefinition`, `SourceIdentity`, `SourceLocator`, `CatalogItem`, `Crosswalk`, `ReviewReceipt`, and `SOURCE_DEFINITIONS`.

- [ ] **Step 1: Write failing allowlist and immutable-record tests**

Create `tests/test_source_registry.py`:

```python
from dataclasses import FrozenInstanceError
import unittest

from portfolio_reliability.model import SourceLocator
from portfolio_reliability.source_registry import SOURCE_DEFINITIONS


class SourceRegistryTests(unittest.TestCase):
    def test_exactly_five_approved_sources_are_registered(self) -> None:
        self.assertEqual(
            tuple(source.source_id for source in SOURCE_DEFINITIONS),
            ("RML", "DVM", "MLTS", "HTD", "EYT"),
        )

    def test_only_https_canonical_urls_are_allowed(self) -> None:
        for source in SOURCE_DEFINITIONS:
            self.assertTrue(source.canonical_url.startswith("https://"))
            self.assertFalse(source.canonical_url.endswith("/search"))

    def test_eyt_is_practitioner_guidance(self) -> None:
        source = next(item for item in SOURCE_DEFINITIONS if item.source_id == "EYT")
        self.assertEqual(source.authority_class, "practitioner_guidance")

    def test_locator_is_immutable(self) -> None:
        locator = SourceLocator(section="Monitoring", page=8, ordinal=4, anchor=None)
        with self.assertRaises(FrozenInstanceError):
            locator.page = 9


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test and observe the missing types**

Run:

```bash
uv run python -m unittest tests.test_source_registry -v
```

Expected: FAIL because `model` and `source_registry` do not exist.

- [ ] **Step 3: Implement frozen records and exact source definitions**

Implement `src/portfolio_reliability/model.py` with frozen, slotted dataclasses:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    source_id: str
    title: str
    authority_class: str
    canonical_url: str
    content_url: str
    media_type: str
    extraction_model: str
    expected_enumerated_count: int | None


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    definition: SourceDefinition
    retrieved_at: str
    retrieved_sha256: str
    byte_count: int
    final_url: str


@dataclass(frozen=True, slots=True)
class SourceLocator:
    section: str
    page: int | None
    ordinal: int | None
    anchor: str | None


@dataclass(frozen=True, slots=True)
class CatalogItem:
    schema_version: int
    item_id: str
    source_id: str
    item_kind: str
    source_locator: SourceLocator
    title: str
    control: str
    evidence_expected: tuple[str, ...]
    domains: tuple[str, ...]
    risk_tags: tuple[str, ...]
    source_native_scoring: str | None
    crosswalk_group: str | None
    review_receipt_id: str


@dataclass(frozen=True, slots=True)
class Crosswalk:
    crosswalk_id: str
    item_ids: tuple[str, ...]
    shared_intent: str
    differences: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewReceipt:
    receipt_id: str
    source_ids: tuple[str, ...]
    source_hashes: tuple[str, ...]
    reviewer: str
    reviewed_at: str
    candidate_sha256: str
    decision: str
```

Implement `src/portfolio_reliability/source_registry.py` with the exact five
definitions:

```python
from portfolio_reliability.model import SourceDefinition


SOURCE_DEFINITIONS = (
    SourceDefinition(
        "RML",
        "Rules of Machine Learning",
        "publisher_primary_guidance",
        "https://developers.google.com/machine-learning/guides/rules-of-ml",
        "https://developers.google.com/machine-learning/guides/rules-of-ml",
        "text/html",
        "enumerated",
        43,
    ),
    SourceDefinition(
        "DVM",
        "Data Validation for Machine Learning",
        "peer_reviewed_primary",
        "https://proceedings.mlsys.org/paper_files/paper/2019/hash/928f1160e52192e3e0017fb63ab65391-Abstract.html",
        "https://proceedings.mlsys.org/paper_files/paper/2019/file/928f1160e52192e3e0017fb63ab65391-Paper.pdf",
        "application/pdf",
        "narrative",
        None,
    ),
    SourceDefinition(
        "MLTS",
        "What's Your ML Test Score?",
        "peer_reviewed_primary",
        "https://research.google/pubs/whats-your-ml-test-score-a-rubric-for-ml-production-systems/",
        "https://research.google.com/pubs/archive/45742.pdf",
        "application/pdf",
        "enumerated",
        28,
    ),
    SourceDefinition(
        "HTD",
        "Hidden Technical Debt in Machine Learning Systems",
        "peer_reviewed_primary",
        "https://research.google/pubs/hidden-technical-debt-in-machine-learning-systems/",
        "https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf",
        "application/pdf",
        "narrative",
        None,
    ),
    SourceDefinition(
        "EYT",
        "How to Test Machine Learning Code and Systems",
        "practitioner_guidance",
        "https://eugeneyan.com/writing/testing-ml/",
        "https://eugeneyan.com/writing/testing-ml/",
        "text/html",
        "narrative",
        None,
    ),
)
```

Generate `catalog/source-definitions.json` from these records using canonical
JSON and write `schemas/source.schema.json` as the documentation contract with
`additionalProperties: false`, the eight required definition fields, and the
three allowed authority classes.

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
uv run python -m unittest tests.test_source_registry -v
uv run python -m unittest discover -s tests -v
```

Expected: all source-registry tests and the complete suite pass.

- [ ] **Step 5: Commit the source contract**

Run:

```bash
git add src/portfolio_reliability/model.py src/portfolio_reliability/source_registry.py catalog/source-definitions.json schemas/source.schema.json tests/test_source_registry.py
git commit -m "feat: define five-source reliability contract"
```

## Task 3: Implement explicit, bounded source acquisition

**Files:**
- Create: `src/portfolio_reliability/acquire.py`
- Create: `src/portfolio_reliability/cli.py`
- Create: `tests/test_acquire.py`
- Create: `tests/fixtures/rml-small.html`

**Interfaces:**
- Consumes: `SourceDefinition` and `canonical_json_bytes`.
- Produces: `fetch_source(source: SourceDefinition, cache_root: Path, *, now: Callable[[], datetime], opener: Callable[..., ContextManager[BinaryIO]]) -> SourceIdentity`, `identity_to_dict(identity: SourceIdentity) -> dict[str, object]`, and a fetch-only `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write failing acquisition-boundary tests**

Create `tests/test_acquire.py` with a fake response object and these cases:

```python
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from portfolio_reliability.acquire import fetch_source
from portfolio_reliability.cli import main
from portfolio_reliability.source_registry import SOURCE_DEFINITIONS


class FakeResponse(BytesIO):
    def __init__(self, payload: bytes, final_url: str, content_type: str) -> None:
        super().__init__(payload)
        self._final_url = final_url
        self.headers = {"Content-Type": content_type}

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class AcquireTests(unittest.TestCase):
    def test_fetch_hashes_bytes_and_uses_utc_timestamp(self) -> None:
        source = SOURCE_DEFINITIONS[0]
        payload = b"<html>rules</html>"
        with TemporaryDirectory() as tmp:
            identity = fetch_source(
                source,
                Path(tmp),
                now=lambda: datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc),
                opener=lambda request, timeout: FakeResponse(
                    payload, source.content_url, "text/html; charset=utf-8"
                ),
            )
        self.assertEqual(identity.byte_count, len(payload))
        self.assertEqual(identity.retrieved_at, "2026-08-02T12:00:00Z")
        self.assertEqual(len(identity.retrieved_sha256), 64)

    def test_fetch_rejects_redirect_to_unapproved_host(self) -> None:
        source = SOURCE_DEFINITIONS[0]
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "redirected to unapproved host"):
                fetch_source(
                    source,
                    Path(tmp),
                    now=lambda: datetime.now(timezone.utc),
                    opener=lambda request, timeout: FakeResponse(
                        b"bad", "https://example.invalid/copy", "text/html"
                    ),
                )

    def test_fetch_rejects_wrong_media_type(self) -> None:
        source = SOURCE_DEFINITIONS[2]
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "media type"):
                fetch_source(
                    source,
                    Path(tmp),
                    now=lambda: datetime.now(timezone.utc),
                    opener=lambda request, timeout: FakeResponse(
                        b"not pdf", source.content_url, "text/html"
                    ),
                )

    def test_cli_rejects_unknown_source_before_network(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            main(["fetch", "--source", "UNKNOWN"])
        self.assertEqual(raised.exception.code, 2)
```

- [ ] **Step 2: Run the tests and confirm the acquisition module is absent**

Run:

```bash
uv run python -m unittest tests.test_acquire -v
```

Expected: FAIL importing `portfolio_reliability.acquire`.

- [ ] **Step 3: Implement the bounded fetcher**

Implement `acquire.py` using `urllib.request.Request` and `urlopen` with:

- fixed user agent `portfolio-reliability-standards/0.1`;
- 30-second timeout;
- 20 MiB maximum response size;
- `https` only;
- redirect host restricted to the canonical or content URL host;
- expected media-type prefix check;
- streaming SHA-256 and byte count;
- cache path `.source-cache/<source_id>/<sha256>.bin`;
- atomic write; and
- RFC 3339 UTC timestamps rendered with `Z`.

The core read loop must be:

```python
digest = hashlib.sha256()
payload = bytearray()
while True:
    chunk = response.read(64 * 1024)
    if not chunk:
        break
    payload.extend(chunk)
    if len(payload) > MAX_SOURCE_BYTES:
        raise ValueError(f"{source.source_id}: source exceeds 20 MiB limit")
    digest.update(chunk)
```

The default opener must use `ProxyHandler({})` so environment proxy values are
not inherited, and a custom `HTTPRedirectHandler` must reject an unapproved
redirect before following it. Do not disable TLS verification, accept arbitrary
redirects, or read proxy or credential configuration from catalog data.

`identity_to_dict` returns the static source-definition fields plus
`retrieved_at`, `retrieved_sha256`, `byte_count`, and `final_url`; it must not
include the cache path or response headers.

Create `cli.py` with an `argparse` `fetch` subcommand. Restrict every `--source`
value through `choices=tuple(source.source_id for source in
SOURCE_DEFINITIONS)`. Write each successful identity atomically to
`.candidates/source-identities/<source_id>.json`. The CLI returns 0 only when
every requested source is fetched and recorded; acquisition errors return 1.

- [ ] **Step 4: Run focused and complete tests**

Run:

```bash
uv run python -m unittest tests.test_acquire -v
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass without network access.

- [ ] **Step 5: Commit source acquisition**

Run:

```bash
git add src/portfolio_reliability/acquire.py src/portfolio_reliability/cli.py tests/test_acquire.py tests/fixtures/rml-small.html
git commit -m "feat: add bounded source acquisition"
```

## Task 4: Reconcile enumerated RML and MLTS controls

**Files:**
- Create: `src/portfolio_reliability/enumerated.py`
- Create: `reviews/rml-controls.json`
- Create: `reviews/mlts-controls.json`
- Create: `tests/test_enumerated.py`
- Create: `tests/fixtures/rml-numbered-headings.html`
- Create: `tests/fixtures/mlts-controls-valid.json`

**Interfaces:**
- Consumes: source definitions and reviewed JSON records.
- Produces: `extract_rml_ordinals(html: str) -> tuple[tuple[int, str, str], ...]`, `validate_rml_controls(extracted, reviewed) -> tuple[CatalogItem, ...]`, and `validate_mlts_controls(reviewed) -> tuple[CatalogItem, ...]`.

- [ ] **Step 1: Write failing enumeration and reconciliation tests**

Create `tests/test_enumerated.py`:

```python
import unittest

from portfolio_reliability.enumerated import (
    extract_rml_ordinals,
    validate_mlts_controls,
    validate_rml_controls,
)


class EnumeratedTests(unittest.TestCase):
    def test_rml_extracts_numbered_rules_in_source_order(self) -> None:
        html = """
        <h3 id="rule-1">Rule #1: Start with data</h3>
        <p>Body.</p>
        <h3 id="rule-2">Rule #2: Design metrics first</h3>
        """
        self.assertEqual(
            extract_rml_ordinals(html),
            ((1, "Start with data", "rule-1"), (2, "Design metrics first", "rule-2")),
        )

    def test_rml_rejects_missing_reviewed_ordinal(self) -> None:
        extracted = ((1, "One", "rule-1"), (2, "Two", "rule-2"))
        reviewed = [{"ordinal": 1, "control": "Use data before ML."}]
        with self.assertRaisesRegex(ValueError, "missing reviewed ordinals: 2"):
            validate_rml_controls(extracted, reviewed)

    def test_mlts_requires_four_categories_of_seven(self) -> None:
        reviewed = [
            {"category": "data", "ordinal": number, "control": f"data {number}"}
            for number in range(1, 8)
        ]
        with self.assertRaisesRegex(ValueError, "model: expected 7, found 0"):
            validate_mlts_controls(reviewed)

    def test_control_text_rejects_source_copy_markers(self) -> None:
        extracted = ((1, "One", "rule-1"),)
        reviewed = [{"ordinal": 1, "control": "\u201cverbatim source quotation\u201d"}]
        with self.assertRaisesRegex(ValueError, "reviewer paraphrase"):
            validate_rml_controls(extracted, reviewed)
```

- [ ] **Step 2: Run the focused test and prove the module is absent**

Run:

```bash
uv run python -m unittest tests.test_enumerated -v
```

Expected: FAIL importing `portfolio_reliability.enumerated`.

- [ ] **Step 3: Implement strict enumerated-source validation**

Use `html.parser.HTMLParser` to capture `h2`, `h3`, and `h4` content whose
normalized text matches `^Rule\s*#(\d+):\s*(.+)$`. Reject duplicate ordinals,
nonpositive ordinals, missing anchors, and noncontiguous sequences.

`validate_rml_controls` must require exactly the extracted ordinal set and emit
IDs `RML-001` through `RML-043` for the current reviewed source.

`validate_mlts_controls` must require exactly these category keys and ranges:

```python
MLTS_CATEGORIES = {
    "data": "MLTS-DATA",
    "model": "MLTS-MODEL",
    "infrastructure": "MLTS-INFRA",
    "monitoring": "MLTS-MONITOR",
}
EXPECTED_MLTS_ORDINALS = tuple(range(1, 8))
```

Each reviewed control record contains `category`, `ordinal`, `page`, `title`,
`control`, `evidence_expected`, `domains`, and `risk_tags`. Reject quotation
marks at the start and end of a control and require a nonempty reviewer
paraphrase distinct from the source heading.

- [ ] **Step 4: Acquire and review the current official sources**

Run the explicit network command:

```bash
uv run portfolio-reliability fetch --source RML --source MLTS
```

Expected: two ignored source-cache files plus candidate identity records; no
published catalog file changes.

Generate the RML candidate from the captured HTML, then create
`reviews/rml-controls.json` with one reviewer-authored control for every
extracted ordinal. Reconcile the count against `expected_enumerated_count=43`.

Create `reviews/mlts-controls.json` from the official PDF with exactly seven
reviewed records in each of the four categories. Verify every record against
its PDF page. The records must paraphrase the source and include the expected
evidence types; they must not contain full copied paragraphs.

- [ ] **Step 5: Run enumerated verification and the complete suite**

Run:

```bash
uv run python -m unittest tests.test_enumerated -v
uv run python -m unittest discover -s tests -v
```

The focused test module must load the committed reviewed control files in
addition to its synthetic fixtures and prove ordinals/counts against the static
source definitions. Expected: 43 RML and 28 MLTS records reconcile; all tests
pass.

- [ ] **Step 6: Commit reviewed enumerated controls**

Run:

```bash
git add src/portfolio_reliability/enumerated.py reviews/rml-controls.json reviews/mlts-controls.json tests/test_enumerated.py tests/fixtures
git commit -m "feat: reconcile enumerated reliability controls"
```

## Task 5: Derive narrative controls through complete section coverage

**Files:**
- Create: `src/portfolio_reliability/narrative.py`
- Create: `reviews/narrative-section-coverage.json`
- Create: `tests/test_narrative.py`
- Create: `tests/fixtures/narrative-coverage-valid.json`

**Interfaces:**
- Consumes: narrative section coverage records and reviewed source identities.
- Produces: `validate_section_coverage(value: object, source_ids: tuple[str, ...]) -> tuple[dict[str, object], ...]` and `derive_narrative_items(records) -> tuple[CatalogItem, ...]`.

- [ ] **Step 1: Write failing narrative-coverage tests**

Create `tests/test_narrative.py`:

```python
import unittest

from portfolio_reliability.narrative import (
    derive_narrative_items,
    validate_section_coverage,
)


class NarrativeCoverageTests(unittest.TestCase):
    def test_all_three_narrative_sources_are_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing source coverage: HTD, EYT"):
            validate_section_coverage(
                [{"source_id": "DVM", "section_id": "2", "disposition": "CONTEXT_ONLY"}],
                ("DVM", "HTD", "EYT"),
            )

    def test_control_derived_requires_locator_and_control(self) -> None:
        record = {
            "source_id": "DVM",
            "section_id": "3.1",
            "section_title": "Single batch validation",
            "disposition": "CONTROL_DERIVED",
        }
        with self.assertRaisesRegex(ValueError, "locator and derived control"):
            derive_narrative_items((record,))

    def test_duplicate_requires_existing_target_item(self) -> None:
        record = {
            "source_id": "HTD",
            "section_id": "2.3",
            "section_title": "Data dependencies",
            "disposition": "DUPLICATE_OF",
            "duplicate_of": "DVM-NOT-REAL-01",
        }
        with self.assertRaisesRegex(ValueError, "unresolved duplicate target"):
            derive_narrative_items((record,))

    def test_out_of_scope_requires_specific_reason(self) -> None:
        record = {
            "source_id": "EYT",
            "section_id": "introduction",
            "section_title": "Introduction",
            "disposition": "OUT_OF_SCOPE_WITH_REASON",
            "reason": "n/a",
        }
        with self.assertRaisesRegex(ValueError, "specific reason"):
            validate_section_coverage((record,), ("EYT",))
```

- [ ] **Step 2: Run the focused test and prove the module is absent**

Run:

```bash
uv run python -m unittest tests.test_narrative -v
```

Expected: FAIL importing `portfolio_reliability.narrative`.

- [ ] **Step 3: Implement coverage-ledger validation**

Allow exactly these dispositions:

```python
DISPOSITIONS = {
    "CONTROL_DERIVED",
    "CONTEXT_ONLY",
    "DUPLICATE_OF",
    "OUT_OF_SCOPE_WITH_REASON",
}
```

Require unique `(source_id, section_id)` keys. A derived control requires page
or stable heading, item ID, title, reviewer paraphrase, evidence expectations,
domains, risk tags, and review receipt ID. A context-only section requires a
substantive explanation. A duplicate requires a resolvable catalog item. An
out-of-scope reason must contain at least 20 non-whitespace characters.

Derived IDs must match:

```text
^(DVM|HTD)-[A-Z0-9-]+-[0-9]{2}$
^EYT-(PRETRAIN|POSTTRAIN|EVALUATION)-[0-9]{2}$
```

- [ ] **Step 4: Acquire and review DVM, HTD, and EYT**

Run:

```bash
uv run portfolio-reliability fetch --source DVM --source HTD --source EYT
```

Expected: three ignored cached sources with recorded hashes.

Create `reviews/narrative-section-coverage.json` by walking every in-scope
heading in each source from start to end. Record a disposition for every
heading. DVM controls must cover single-batch validation, inter-batch skew and
drift, schema/model assumptions, type/presence/value/domain constraints,
actionable alerts, approved versioned schemas, synthetic tests, and slice-level
issues. HTD controls must cover entanglement, correction cascades, undeclared
consumers, unstable and underused dependencies, feedback loops, glue and
pipeline debt, configuration debt, monitoring, reproducibility, and process
debt. EYT controls must retain the pre-training, post-training, and evaluation
phase distinction.

- [ ] **Step 5: Verify complete coverage and run all tests**

Run:

```bash
uv run python -m unittest tests.test_narrative -v
uv run python -m unittest discover -s tests -v
```

The focused test module must load the committed narrative coverage ledger in
addition to its synthetic fixtures. Expected: every reviewed section has
exactly one disposition, every derived item resolves, and all tests pass.

- [ ] **Step 6: Commit narrative coverage**

Run:

```bash
git add src/portfolio_reliability/narrative.py reviews/narrative-section-coverage.json tests/test_narrative.py tests/fixtures/narrative-coverage-valid.json
git commit -m "feat: derive narrative reliability controls"
```

## Task 6: Validate catalog items, review receipts, and crosswalks

**Files:**
- Create: `src/portfolio_reliability/catalog.py`
- Create: `catalog/sources.json`
- Create: `catalog/items.jsonl`
- Create: `catalog/crosswalks.json`
- Create: `reviews/source-review-receipts.jsonl`
- Create: `schemas/item.schema.json`
- Create: `schemas/receipt.schema.json`
- Create: `tests/test_catalog.py`

**Interfaces:**
- Consumes: `CatalogItem`, reviewed enumerated/narrative records, source identities, and review receipts.
- Produces: `validate_catalog(items: tuple[CatalogItem, ...], sources: tuple[SourceIdentity, ...], receipts: tuple[ReviewReceipt, ...], crosswalks: tuple[Crosswalk, ...]) -> CatalogValidation`, `score_mlts(items: tuple[CatalogItem, ...], statuses: dict[str, int]) -> MltsScore`, and `build_catalog_records(rml_items: tuple[CatalogItem, ...], mlts_items: tuple[CatalogItem, ...], narrative_items: tuple[CatalogItem, ...]) -> tuple[CatalogItem, ...]`.

- [ ] **Step 1: Write failing catalog-invariant tests**

Create `tests/test_catalog.py` with concrete frozen-record fixtures:

```python
import unittest

from portfolio_reliability.catalog import score_mlts, validate_catalog
from portfolio_reliability.model import (
    CatalogItem,
    Crosswalk,
    ReviewReceipt,
    SourceDefinition,
    SourceIdentity,
    SourceLocator,
)


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        definition = SourceDefinition(
            "RML", "Rules", "publisher_primary_guidance",
            "https://developers.google.com/machine-learning/guides/rules-of-ml",
            "https://developers.google.com/machine-learning/guides/rules-of-ml",
            "text/html", "enumerated", 43,
        )
        self.sources = (
            SourceIdentity(definition, "2026-08-02T12:00:00Z", "a" * 64, 100, definition.content_url),
        )
        self.receipts = (
            ReviewReceipt(
                "review-rml-1", ("RML",), ("a" * 64,), "reviewer",
                "2026-08-02T13:00:00Z", "b" * 64, "APPROVED",
            ),
        )

    def item(self, item_id: str, *, section: str = "Rules", ordinal: int = 1) -> CatalogItem:
        return CatalogItem(
            1, item_id, "RML", "enumerated",
            SourceLocator(section, None, ordinal, f"rule-{ordinal}"),
            "Reviewed title", "Reviewer paraphrase.", ("test receipt",),
            ("data",), ("reproducibility",), None, None, "review-rml-1",
        )

    def mlts_fixture(self) -> tuple[CatalogItem, ...]:
        items = []
        for category in ("DATA", "MODEL", "INFRA", "MONITOR"):
            for ordinal in range(1, 8):
                items.append(
                    CatalogItem(
                        1, f"MLTS-{category}-{ordinal:02d}", "MLTS", "enumerated",
                        SourceLocator(category, 8, ordinal, None), "Reviewed title",
                        "Reviewer paraphrase.", ("test receipt",), ("testing",),
                        ("regression",), "mlts_0_1_2", None, "review-mlts-1",
                    )
                )
        return tuple(items)

    def test_duplicate_item_ids_are_rejected(self) -> None:
        item = self.item("RML-001")
        with self.assertRaisesRegex(ValueError, "duplicate item_id RML-001"):
            validate_catalog((item, item), self.sources, self.receipts, ())

    def test_empty_locator_is_rejected(self) -> None:
        item = self.item("RML-001", section="")
        with self.assertRaisesRegex(ValueError, "source locator"):
            validate_catalog((item,), self.sources, self.receipts, ())

    def test_unknown_crosswalk_member_is_rejected(self) -> None:
        crosswalk = Crosswalk(
            "point-in-time", ("RML-029", "MISSING-001"),
            "Prevent mutable evidence.", ("Sources emphasize different stages.",),
        )
        with self.assertRaisesRegex(ValueError, "unknown item MISSING-001"):
            validate_catalog(
                (self.item("RML-029", ordinal=29), self.item("RML-030", ordinal=30)),
                self.sources, self.receipts, (crosswalk,),
            )

    def test_mlts_score_uses_minimum_category(self) -> None:
        items = self.mlts_fixture()
        statuses = {item.item_id: 2 for item in items}
        statuses["MLTS-MODEL-01"] = 1
        statuses["MLTS-INFRA-01"] = 0
        score = score_mlts(items, statuses)
        self.assertEqual(dict(score.category_scores)["infrastructure"], 12)
        self.assertEqual(score.final_score, 12)
```

- [ ] **Step 2: Run the focused test and prove catalog validation is absent**

Run:

```bash
uv run python -m unittest tests.test_catalog -v
```

Expected: FAIL importing `portfolio_reliability.catalog`.

- [ ] **Step 3: Implement fail-closed catalog validation**

Add frozen result records:

```python
@dataclass(frozen=True, slots=True)
class CatalogValidation:
    item_count: int
    source_counts: tuple[tuple[str, int], ...]
    crosswalk_count: int
    receipt_count: int


@dataclass(frozen=True, slots=True)
class MltsScore:
    category_scores: tuple[tuple[str, int], ...]
    final_score: int
    modified_applicability: bool
```

Validate stable ID regexes, locator prerequisites, source membership, receipt
source-hash binding, nonempty evidence types, sorted unique tags, known
crosswalk members, at least two items per crosswalk, and explicit semantic
differences. Reject NaN/Infinity through canonical serialization.

`score_mlts` accepts only integer values 0, 1, or 2. It totals each seven-item
category and returns the minimum category total. It must not silently exclude
missing items.

- [ ] **Step 4: Generate reviewed catalog, crosswalk, and receipt records**

Promote the five reviewed candidate identities into `catalog/sources.json`
only after comparing each hash, media type, final URL, byte count, and source
locator against the reviewed source. Build `catalog/items.jsonl` from Tasks 4
and 5 in stable item-ID order. Create crosswalks for overlapping controls
including point-in-time data, schema and
drift, simpler baselines, training/serving consistency, source/dependency
ownership, slice testing, monitoring, reproducibility, and rollback.

Append one review receipt per source hash. Each receipt contains exact source
IDs and hashes, reviewer name `carsynstephenson`, UTC review time, candidate
SHA-256, and decision `APPROVED`.

- [ ] **Step 5: Run focused and complete verification**

Run:

```bash
uv run python -m unittest tests.test_catalog -v
uv run python -m unittest discover -s tests -v
```

Expected: zero orphan items, zero unresolved crosswalks, five bound review
receipts, and a green complete suite.

- [ ] **Step 6: Commit the verified catalog**

Run:

```bash
git add src/portfolio_reliability/catalog.py catalog/sources.json catalog/items.jsonl catalog/crosswalks.json reviews/source-review-receipts.jsonl schemas/item.schema.json schemas/receipt.schema.json tests/test_catalog.py
git commit -m "feat: validate reviewed reliability catalog"
```

## Task 7: Publish a deterministic downstream snapshot

**Files:**
- Create: `src/portfolio_reliability/snapshot.py`
- Modify: `src/portfolio_reliability/cli.py`
- Create: `catalog/catalog-manifest.json`
- Create: `schemas/profile.schema.json`
- Create: `schemas/report.schema.json`
- Create: `vendor/portfolio-reliability-catalog-v1.json`
- Create: `vendor/portfolio-reliability-catalog-v1.sha256`
- Create: `tests/test_snapshot.py`
- Create: `tests/test_cli.py`
- Create: `tests/fixtures/valid-catalog/`

**Interfaces:**
- Consumes: validated sources, items, crosswalks, and receipts.
- Produces: `build_snapshot(root: Path) -> dict[str, object]`, `publish_snapshot(root: Path, version: int) -> tuple[Path, Path]`, `verify_snapshot(snapshot_path: Path, digest_path: Path) -> None`, and `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write failing snapshot and CLI tests**

Create `tests/test_snapshot.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import shutil
import unittest

from portfolio_reliability.snapshot import publish_snapshot, verify_snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

    def copy_valid_fixture(self) -> Path:
        source = Path(__file__).parent / "fixtures" / "valid-catalog"
        destination = Path(self.temporary_directory.name) / "catalog-root"
        shutil.copytree(source, destination)
        return destination

    def test_publication_is_byte_deterministic(self) -> None:
        root = self.copy_valid_fixture()
        first, first_digest = publish_snapshot(root, 1)
        first_bytes = first.read_bytes()
        second, second_digest = publish_snapshot(root, 1)
        self.assertEqual(first_bytes, second.read_bytes())
        self.assertEqual(first_digest.read_bytes(), second_digest.read_bytes())

    def test_digest_matches_snapshot_bytes(self) -> None:
        root = self.copy_valid_fixture()
        snapshot, digest_path = publish_snapshot(root, 1)
        expected = hashlib.sha256(snapshot.read_bytes()).hexdigest() + "\n"
        self.assertEqual(digest_path.read_text(encoding="ascii"), expected)

    def test_verifier_rejects_changed_snapshot(self) -> None:
        root = self.copy_valid_fixture()
        snapshot, digest_path = publish_snapshot(root, 1)
        snapshot.write_bytes(snapshot.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "snapshot digest mismatch"):
            verify_snapshot(snapshot, digest_path)
```

Create `tests/test_cli.py` with `unittest.mock.patch` asserting that `verify`
and `publish` never call the acquisition function, while `fetch` calls it only
for requested allowlisted source IDs. Assert invalid source IDs exit 2.

- [ ] **Step 2: Run focused tests and prove publication is absent**

Run:

```bash
uv run python -m unittest tests.test_snapshot tests.test_cli -v
```

Expected: FAIL importing `snapshot` and `cli`.

- [ ] **Step 3: Implement deterministic snapshot assembly**

The snapshot top-level object is exactly:

```python
snapshot = {
    "schema_version": 1,
    "catalog_version": version,
    "source_identities": source_identity_records,
    "items": item_records,
    "crosswalks": crosswalk_records,
    "review_receipts": receipt_records,
    "catalog_manifest": catalog_manifest,
}
```

Sort sources by source ID, items by item ID, crosswalks by crosswalk ID, and
receipts by receipt ID before canonical serialization. Publication first runs
the complete catalog validator, writes the snapshot atomically, computes SHA-256
over the exact bytes, and writes the lowercase digest plus newline.

The CLI subcommands are:

```text
portfolio-reliability fetch --source SOURCE [--source SOURCE ...]
portfolio-reliability verify [--sources CSV]
portfolio-reliability publish --version 1
```

`verify` and `publish` are offline. `fetch` is the only command that imports and
calls `fetch_source`.

- [ ] **Step 4: Add downstream schema documents**

`profile.schema.json` defines the exact statuses `ENFORCED`, `MANUAL`,
`ADVISORY`, `GAP`, `NOT_APPLICABLE`, and `SUPERSEDED`; `STALE` is computed and
cannot be authored. Require `item_id`, `status`, `local_control_id`, evidence,
owner, reviewed commit, review time, enforcement mode, and notes.

`report.schema.json` requires catalog digest, repository SHA, dirty-state
disclosure, source/status counts, stale findings, gaps, crosswalk
consolidations, and the advisory boundary string.

- [ ] **Step 5: Publish and reproduce version 1**

Run:

```bash
uv run portfolio-reliability verify
uv run portfolio-reliability publish --version 1
cp vendor/portfolio-reliability-catalog-v1.json /tmp/catalog-first.json
cp vendor/portfolio-reliability-catalog-v1.sha256 /tmp/catalog-first.sha256
uv run portfolio-reliability publish --version 1
cmp /tmp/catalog-first.json vendor/portfolio-reliability-catalog-v1.json
cmp /tmp/catalog-first.sha256 vendor/portfolio-reliability-catalog-v1.sha256
```

Expected: verify succeeds; both `cmp` commands exit 0.

- [ ] **Step 6: Run the complete standards suite**

Run:

```bash
uv run python -m unittest discover -s tests -v
```

Expected: all tests pass with no network activity.

- [ ] **Step 7: Commit the published snapshot**

Run:

```bash
git add src/portfolio_reliability/snapshot.py src/portfolio_reliability/cli.py catalog/catalog-manifest.json schemas/profile.schema.json schemas/report.schema.json vendor tests/test_snapshot.py tests/test_cli.py
git commit -m "feat: publish deterministic checklist snapshot"
```

## Task 8: Run the Phase 0 completion audit and hand off exact integration inputs

**Files:**
- Modify: `README.md`
- Create: `docs/source-method.md`
- Create: `docs/status-semantics.md`
- Create: `docs/reviewer-runbook.md`
- Create: `docs/phase0-completion-audit.md`

**Interfaces:**
- Consumes: the committed version-1 snapshot and all verification commands.
- Produces: an evidence-backed Phase 0 audit plus the exact snapshot path, SHA-256, item IDs, and schemas needed to write the four repository integration plans.

- [ ] **Step 1: Write the completion-audit checklist before claiming completion**

Create `docs/phase0-completion-audit.md` with one row for each requirement:

```markdown
| Requirement | Authoritative evidence | Result | Notes |
|---|---|---|---|
| Five source identities | `catalog/sources.json` plus source validator | NOT YET VERIFIED | Filled after command run |
| 43 RML ordinals | enumerated verifier output | NOT YET VERIFIED | Filled after command run |
| 28 MLTS tests | enumerated verifier output | NOT YET VERIFIED | Filled after command run |
| Narrative section coverage | narrative verifier output | NOT YET VERIFIED | Filled after command run |
| Crosswalk resolution | catalog verifier output | NOT YET VERIFIED | Filled after command run |
| Deterministic snapshot | two-run `cmp` receipts | NOT YET VERIFIED | Filled after command run |
| Offline complete tests | unittest receipt | NOT YET VERIFIED | Filled after command run |
| No runtime dependencies | `pyproject.toml` inspection | NOT YET VERIFIED | Filled after command run |
```

This initial file truthfully starts red. Do not prefill PASS.

- [ ] **Step 2: Run final verification from a clean tree**

Run:

```bash
git status --short
uv run portfolio-reliability verify
uv run python -m unittest discover -s tests -v
uv run portfolio-reliability publish --version 1
git diff --exit-code -- vendor/portfolio-reliability-catalog-v1.json vendor/portfolio-reliability-catalog-v1.sha256
```

Expected: the tree is clean before generated verification, every command exits
0, and publication produces no tracked diff.

- [ ] **Step 3: Replace each audit result with current evidence**

For each audit row, record `PROVED`, `CONTRADICTED`, or `MISSING`; include the
exact command, Git SHA, count, and digest. A failed or missing row remains open
and prevents Phase 0 completion.

Resolve the dynamic handoff values with:

```bash
git rev-parse HEAD
cat vendor/portfolio-reliability-catalog-v1.sha256
```

Record the first command's exact output as `standards_git_sha`, the second
command's exact output as `catalog_sha256`, and record the literal stable fields
`catalog_version=1`,
`catalog_snapshot=vendor/portfolio-reliability-catalog-v1.json`,
`profile_schema=schemas/profile.schema.json`, and
`report_schema=schemas/report.schema.json`. Values are copied from command
output, never typed from memory.

- [ ] **Step 4: Complete operating documentation**

Document:

- source acquisition and hash-change review;
- enumerated count and narrative section reconciliation;
- authority classes and conflict resolution;
- status evidence prerequisites and computed staleness;
- copyright-safe publication;
- offline verification;
- downstream catalog locking; and
- rollback to the previous catalog version.

- [ ] **Step 5: Commit the completion audit and documentation**

Run:

```bash
git add README.md docs
git commit -m "docs: record checklist catalog completion audit"
```

- [ ] **Step 6: Verify the final committed state**

Run:

```bash
git status --short
git log --oneline --decorate -8
uv run portfolio-reliability verify
uv run python -m unittest discover -s tests -v
```

Expected: clean tree, focused commit history, green catalog verification, and a
green complete test suite.

## Program checkpoint after this plan

Do not begin repository integration from remembered or proposed IDs. Generate
four repository-specific plans from the committed version-1 snapshot and its
verified item IDs:

1. Kalshi profile and advisory reporter.
2. Options Validator profile and advisory reporter.
3. Equity Research profile and advisory reporter.
4. Sunwest profile and advisory CLI subcommand.

Each plan must first run the repository's native baseline, map existing controls
without implementing gaps, and preserve the exact local dirty-state disclosure.
Only then may it add a profile, reporter, and contract tests.

## Plan self-review record

| Approved design requirement | Implementing task | Review result |
|---|---|---|
| Standalone federated standards repository | Tasks 1 and 7 | Covered |
| Five allowlisted source identities | Tasks 2, 3, and 6 | Covered |
| Enumerated RML and MLTS reconciliation | Task 4 | Covered |
| DVM, HTD, and EYT section disposition | Task 5 | Covered |
| Authority distinction and copyright-safe handling | Tasks 2, 4, 5, and 8 | Covered |
| Stable normalized items and crosswalk deduplication | Task 6 | Covered |
| Source-native MLTS scoring | Task 6 | Covered |
| Offline deterministic snapshot and digest | Task 7 | Covered |
| Downstream profile/report contracts | Task 7 | Covered |
| Security and data-egress constraints | Tasks 2, 3, 6, and 7 | Covered |
| Evidence-backed completion audit | Task 8 | Covered |
| Four repository integrations | Program checkpoint and subsequent plans | Sequenced after verified IDs; not removed from scope |

The placeholder scan found no `TODO`, `TBD`, undefined future function, or
unresolved dynamic hash in an implementation instruction. Dynamic Git and
snapshot hashes are resolved by exact commands in Task 8. Type review confirmed
that later tasks use the record and function names defined by earlier tasks.

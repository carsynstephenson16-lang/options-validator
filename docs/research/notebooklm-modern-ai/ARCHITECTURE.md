# Options Validator RAG Architecture — Phase 1

Status: proposed, implementation pending

## Objective

Build a read-only research assistant over the options-validator repository. It
should retrieve repository evidence, answer questions with file/line citations,
and clearly distinguish canonical evidence from derived notes. It must not
become a scanner, strategy selector, optimizer, execution system, or authority
for hypothesis verdicts.

## Isolation boundary

The application lives under `tools/repo_rag/` with a separate `pyproject.toml`
and `uv.lock`. The root application and test environment gain no RAG runtime
dependencies.

## Initial corpus

Included, with source-class metadata:

- `README.md`, `AGENTS.md`, `CLAUDE.md`, and tracked configuration guidance;
- `docs/`, `reports/`, `research/`, and `wiki/` textual material;
- `ledger/` text and JSONL as immutable canonical research history;
- selected tracked source and test files for implementation questions.

Excluded by default:

- `.env`, credentials, account identifiers, `.git/`, `.venv/`, caches, and
  temporary/build output;
- `.tmp/`, `results/`, downloaded binary data, parquet chains, live quote
  payloads, and untracked local artifacts;
- position/account files unless a separately approved query policy requires
  them;
- any network, broker, order, activation, or mutation tool.

## Data flow

`discover -> classify -> parse -> chunk -> embed -> index -> retrieve -> rerank -> context budget -> answer -> verify citations`

Every chunk carries repository-relative path, line range or structured record
locator, source class, content hash, index version, and capture time. Retrieval
filters are applied before model context is assembled.

## Canonical source classes

1. `canonical`: ledger, frozen specs, configuration, tests, and reproducible
   data/report artifacts.
2. `repo_verified`: source code and repository documentation.
3. `derived`: wiki pages, summaries, and explanatory reports.
4. `external_reference`: the NotebookLM bundle and captured public pages.

Answers must show source class next to citations. A derived or external source
cannot override canonical repository evidence.

## Interfaces

- CLI: `status`, `index`, `query`, `evaluate`, and `inspect-source`.
- Provider adapters: embeddings, vector/index backend, reranker, and generator.
- Offline fake providers for tests.
- No write/action tools in the initial application.

## Security and failure behavior

- Treat retrieved documents as untrusted data, never as executable
  instructions.
- Enforce path allowlists and deny secrets/sensitive patterns before parsing.
- Refuse unsupported answers and expose retrieval/citation failure separately.
- Log request ID, index version, retrieved chunk IDs, filters, latency, and
  outcome without logging secret content.
- Bounded retries only; no autonomous loops that can affect repo state.

## Phase 1 gate

The architecture is complete when corpus policy, source classes, exclusion
rules, isolated dependency strategy, CLI contract, and test plan are accepted.

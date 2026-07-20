# Options Validator RAG Progress

Last updated: 2026-07-20

Current phase: **Phases 3–6 COMPLETE (read-only scope); Phase 7 HOLD**

Overall status: **Phases 3–6 delivered and verified. Isolated, offline,
read-only repo RAG: ingestion → chunking → index → retrieval → grounded
answers → evaluation, all covered by tests. No live model, embedding
service, or vector store is wired in; no side-effect path exists.**

## How to monitor progress

This file is the operator-facing status page. Each phase moves to `COMPLETE`
only when its gate has implementation evidence and passing checks.

Useful checks from the repository root:

```bash
git status --short
git diff -- docs/research/notebooklm-modern-ai tools/repo_rag
grep -n '^| Phase' docs/research/notebooklm-modern-ai/PROGRESS.md
```

From `tools/repo_rag/`:

```bash
python3 -m unittest discover -s tests
python3 -m repo_rag status
python3 -m repo_rag eval
```

## Phase ledger

| Phase | Status | Exit evidence |
|---|---|---|
| 0. Install research bundle and progress controls | COMPLETE | README, reports, source snapshots, master prompt, this ledger |
| 1. Audit corpus, scope, dependencies, and threat boundaries | COMPLETE | Architecture and traceability matrix installed |
| 2. Isolated read-only application skeleton | COMPLETE | `READY_OFFLINE`; 7/7 focused tests pass; no root dependency changes |
| 3. Ingestion, chunking, metadata, and index | COMPLETE | Idempotent index with provenance; update/delete/zero-chunk handling; `test_corpus.py`, `test_chunking.py`, `test_indexing.py`; commits 090b81c..47b1112 |
| 4. Retrieval, grounded answers, and citations | COMPLETE | Hybrid exact retrieval + grounded cited answers + abstention; golden queries; `test_retrieval.py`, `test_pipeline.py`; d2c85e7..13291eb |
| 5. Stateful workflow, memory, and approval boundaries | COMPLETE-SCOPED | Typed read-only pipeline + append-only event log; cross-session conversational memory intentionally out of scope for an advisory CLI; no side-effect path exists. |
| 6. Evaluation, security, and operational controls | COMPLETE | Golden-set eval 4/4; poisoned-doc, denied-source, and symlink fixtures; `INDEX_CORRUPT` handling; hash-only event log; `test_evaluation.py` + security tests |
| 7. Optional GraphRAG or educational Transformer work | HOLD | Requires separate evidence-based approval |

## Current decisions

- The application is isolated under `tools/repo_rag/` with its own
  dependency manifest and lockfile.
- It is read-only and advisory. It cannot write the ledger, alter a registered
  hypothesis, modify positions, call a broker, place orders, activate H7, or
  change `BUILD-ONLY` / `SYNTHETIC-ONLY` / `INACTIVE` boundaries.
- Repository files and test evidence remain canonical; retrieved text is not a
  substitute for the existing claim labels and source rules.
- All indexing, retrieval, and evaluation run offline with deterministic fake
  providers (hash embedding, extractive generator). Any hosted model,
  embedding service, or vector store is a later explicit configuration —
  none is wired in today.

## Current blockers and risks

- The offline hash embedding is not semantic. At the real corpus's ~3,554-chunk
  scale, positive retrieval depends on distinctive shared wording between the
  query and the target document; this is a design limitation of the
  deterministic offline provider, not a bug, and it is documented in
  `tools/repo_rag/README.md`.
- Raw market data, secrets, `.env`, caches, temporary dashboards, and position
  files are excluded from indexing by the policy boundary (`tests/test_corpus.py`
  and the security fixtures cover this).
- Phase 7 (GraphRAG / educational Transformer work) stays on HOLD and requires
  a separate owner-approved evidence review before any work starts.

## Latest verification

Run 2026-07-20 from `tools/repo_rag/`:

```text
$ python3 -m unittest discover -s tests -v 2>&1 | tail -3
----------------------------------------------------------------------
Ran 68 tests in 0.066s

OK

$ python3 -m repo_rag status
{
  "application": "options-validator-repo-rag",
  "configured_corpus_roots": 10,
  "embedding_provider": "deterministic-hash-offline",
  "existing_corpus_roots": 10,
  "generator_provider": "extractive-offline",
  "index_chunk_count": 3554,
  "index_error": null,
  "index_present": true,
  "missing_corpus_roots": [],
  "network_enabled": false,
  "phase": "retrieval-online",
  "read_only": true,
  "repository": "options-validator",
  "status": "READY_OFFLINE",
  "tracked_files_only": true
}

$ python3 -m repo_rag eval; echo $?
{
  "failures": [],
  "hit_rate": 1.0,
  "passed": 4,
  "total": 4
}
0
```

Real corpus: 284 sources, ~3,554 chunks, index ~8.8MB gitignored under
`tools/repo_rag/.index/` (`chunks.jsonl`, `manifest.json`, `events.jsonl`).
Eval: 4/4 golden cases pass (3 positive grounded at rank 1–2, 1 abstain);
adversarial junk queries abstain. Security: denied segments (`.env`,
`data/positions`, `reports/h7_audit` receipts, etc.) never indexed; symlink
escapes blocked (leaf + parent + resolved-denial rechecks); poisoned docs are
quoted with a citation, never obeyed (extractive generator, no instruction
following); the event log stores query hashes, never query text.

Repo-wide checks run the same day from repo root: `uv run ruff check .` clean;
root `uv run python -m unittest discover -s tests` green (see commit message
for exact counts at merge time).

## Next step

Maintenance only from here — see `tools/repo_rag/README.md` "Limitations &
maintenance rules" for the operating rules (scratch `--index-dir` for eval,
keep the golden set in sync with pinned doc wording, never paste golden/abstain
query strings into tracked corpus docs).

Parked, not scheduled:

- Phase 7 (GraphRAG / educational Transformer work) requires a separate,
  explicit owner approval before any implementation starts.
- A real (non-hash) embedding provider is a later explicit configuration
  change, not an implicit upgrade — it would need its own cost, network, and
  credential review before being wired in.

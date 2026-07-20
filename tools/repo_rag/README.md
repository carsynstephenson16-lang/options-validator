# Repository RAG

Isolated, read-only RAG (retrieval-augmented generation) application for this
repository. It indexes approved tracked source text, retrieves evidence for a
query, and answers with file:line citations or abstains — all offline, with
deterministic providers (a hash-based embedding and an extractive generator).
It does not modify the parent repository, call the network, or require
credentials.

## Commands

```bash
python3 -m repo_rag status                        # index + policy summary as JSON
python3 -m repo_rag ingest                         # build/refresh the local index
python3 -m repo_rag query "some question about the repo"
python3 -m repo_rag eval                           # run the golden-set evaluation
```

### Exit codes

`status`:

| Exit | Meaning |
|---|---|
| 0 | `READY_OFFLINE` or another ready status |
| 2 | Not ready (index missing/corrupt, corpus roots missing, etc.) |

`query`:

| Exit | Outcome |
|---|---|
| 0 | `ANSWERED` |
| 2 | `INDEX_MISSING` or `INDEX_CORRUPT` |
| 3 | `INSUFFICIENT_EVIDENCE` (abstained — no sufficiently grounded/overlapping evidence) |
| 4 | Other typed failure (`CITATION_MISMATCH`, `EMPTY_QUERY`) |

`ingest`:

| Exit | Meaning |
|---|---|
| 0 | Ingest completed (build, update, or no-op) |

`eval`:

| Exit | Meaning |
|---|---|
| 0 | All golden cases passed |
| 5 | One or more golden cases failed |

## `.index/` layout

The index lives under `tools/repo_rag/.index/` (gitignored, disposable):

- `chunks.jsonl` — one JSON record per indexed chunk (source path, line range,
  text, source class, hash).
- `manifest.json` — per-source ingest state used for idempotent
  update/delete/zero-chunk handling.
- `events.jsonl` — append-only event log; stores query **hashes**, never query
  text, and outcome/timing metadata.

If the index looks wrong (`INDEX_CORRUPT`, unexpected chunk counts, stale
answers), delete `.index/` and re-run `ingest` rather than hand-editing any of
these files.

## Limitations & maintenance rules

1. **The offline hash embedding is not semantic.** It has no notion of
   meaning or synonymy. At the real corpus's scale (~3,554 chunks), a query
   only retrieves a target document at a useful rank if it shares distinctive
   wording with that document — generic phrasing is not enough. A real
   (non-hash) embedding provider would relax this, but that is a later,
   explicit configuration change, not an implicit upgrade.
2. **`eval` appends events to the target index's `events.jsonl`.** Running
   `eval` against your working index will mix evaluation events into your
   operator log. Point `--index-dir` at a scratch copy of the index if you
   want a clean operator event log.
3. **The golden set pins source wording.** Golden queries are written to
   match specific, distinctive phrasing in specific pinned documents. If you
   reword a pinned doc, update its golden query in the same commit, or the
   golden case will silently start failing (or passing for the wrong reason).
4. **Never paste literal golden or abstain query strings into tracked corpus
   docs.** Doing so causes in-corpus contamination — a query can end up
   matching the plan or doc that quotes it, rather than the intended target,
   which invalidates the evaluation.
5. **`eval`'s `hit_rate` is a pass rate, including abstentions.** A case where
   the golden expectation is "abstain" and the system abstains counts as a
   pass toward `hit_rate`; it is not a raw positive-retrieval hit rate.

## Tests

```bash
python3 -m unittest discover -s tests
```

68 tests, offline, stdlib-only (no network, no paid API calls).

## Boundary

This application is advisory. Retrieved material remains subject to the parent
repository's canonical-source, validation, and safety rules. No write or action
tools are present.

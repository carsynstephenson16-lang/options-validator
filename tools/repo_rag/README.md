# Repository RAG

Isolated, read-only RAG (retrieval-augmented generation) application for this
repository. It indexes approved tracked source text, retrieves evidence for a
query, and answers with file:line citations or abstains — all offline, with
deterministic providers (a hash-based embedding and an extractive generator).
It does not call the network or require credentials. Its only permitted writes
are app-owned health artifacts and non-raw wiki pages, enforced by a
fail-closed allowlist; it cannot touch trading, H7, positions, ledgers,
hypotheses, or execution state.

## Commands

```bash
python3 -m repo_rag status                        # index + policy summary as JSON
python3 -m repo_rag ingest                         # build/refresh the local index
python3 -m repo_rag query "some question about the repo"
python3 -m repo_rag eval                           # run the golden-set evaluation
python3 -m repo_rag search "H7 event ledger" --hypothesis h7 --json
python3 -m repo_rag evaluate --golden eval/golden.jsonl --json
python3 -m repo_rag health --golden eval/golden.jsonl
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

`search`, `evaluate`, and `health` return zero on explicit abstention or a
retrieval regression. `health` returns non-zero only for a broken index,
missing/corrupt golden set, or another infrastructure failure.

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

## Scheduled health

The raw-passage `search` command keeps retrieval separate from answer
generation. It returns tier-labelled file/line passages and supports ticker,
hypothesis, tier, document-type, and as-of-date filters. The `evaluate`
command measures hit@5, MRR, negative-control abstention, false-hit rate, and
latency against `eval/golden.jsonl`; each observation is appended to the
gitignored `eval/history.csv`. A regression creates a proposal in the report,
never a code, policy, threshold, or H7 change.

`scripts/run_repo_rag_health.sh` and the launchd template under `launchd/`
are prepared for Sunday and Wednesday at 07:00 local time. They are not
installed yet: the migrated seed has four owner-curated legacy cases, and the
owner must expand/freeze the scheduled set to 15–25 questions (including at
least three negative controls) before scheduling it.

## Tests

```bash
python3 -m unittest discover -s tests
```

The test suite is offline and stdlib-only (no network, no paid API calls).

## Boundary

This application is advisory. Retrieved material remains subject to the parent
repository's canonical-source, validation, and safety rules. The bounded writer
cannot honor a model-supplied path, overwrites reports by versioning, journals
every autonomous write, and refuses `wiki/raw/` as well as every research and
trading artifact.

# Options Validator RAG Requirements Traceability

| ID | Notebook finding | Repo adaptation | Status | Required evidence |
|---|---|---|---|---|
| OVR-001 | Specialized knowledge base | Index approved tracked research text with source classes | COMPLETE | `tests/test_corpus.py`: policy boundary, deny rules, tracked-only, symlink guards |
| OVR-002 | Parsing and semantic chunking | Preserve file lines, headings, JSONL record identity, and hashes | COMPLETE | `tests/test_chunking.py`: line-aware chunks, CRLF handling, chunk ids, coverage invariants |
| OVR-003 | Embeddings and vector retrieval | Replaceable adapter in isolated environment; offline fake first | COMPLETE | `tests/test_providers.py` + `tests/test_retrieval.py`: deterministic adapter, dimension guard |
| OVR-004 | Metadata filtering | Filter by source class, path, hypothesis, date, and sensitivity | PARTIAL | Source-class and path filtering implemented and tested; hypothesis/date/sensitivity filters not needed yet — open |
| OVR-005 | Retrieval and augmentation | Retrieve evidence before grounded generation | COMPLETE | `tests/test_retrieval.py` + golden set: hit-rate 4/4 |
| OVR-006 | Citations and transparency | File/line or record citations with source-class labels | COMPLETE | file:line citations with source-class provenance; citation verification in pipeline; `tests/test_pipeline.py` |
| OVR-007 | Abstention | Refuse when evidence is absent, stale, conflicting, or unauthorized | COMPLETE | Abstention via `INSUFFICIENT_EVIDENCE` + `require_lexical_overlap` gate; golden abstain case and adversarial junk queries verified |
| OVR-008 | Stateful workflow | Typed, bounded read-only query workflow | COMPLETE | Typed outcomes including `INDEX_CORRUPT`; exit-code contract; `tests/test_pipeline.py` + `tests/test_cli.py` |
| OVR-009 | Long-term memory | Persist index/checkpoints, not unapproved model reflections | PARTIAL | Durable index and event log persist and reload; deletion via re-ingest is tested; retention/expiry is N/A for a local gitignored directory |
| OVR-010 | Human-in-the-loop | No side-effect tools; future mutations require a separate approval design | BOUNDARY SET | Poisoned-doc, denied-source, and symlink-escape tests; no side-effect tools exist |
| OVR-011 | Self-reflection | Evaluation produces lesson candidates only | OPEN | Evaluation produces reports only; no lesson promotion — deliberate |
| OVR-012 | Evaluation | Groundedness, citation accuracy, abstention, retrieval, latency, cost | COMPLETE | `tests/test_evaluation.py` + `golden/golden_set.json` + `eval` CLI; known offline-embedding limitation noted in README |
| OVR-013 | GraphRAG | Add only if relationship queries fail ordinary/hybrid RAG | HOLD | Baseline comparison and approval |
| OVR-014 | Transformer lab | Educational and unrelated to repository RAG behavior | OUT OF SCOPE | Separate owner request |

No row is `COMPLETE` until both implementation and listed evidence exist.
